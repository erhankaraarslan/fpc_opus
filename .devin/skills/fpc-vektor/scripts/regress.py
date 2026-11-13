"""Regresyon: parçanın onaylı ("altın") sonuçlarını saklar ve yeni çalıştırmayı onunla karşılaştırır.

Kullanım (fpc.py üzerinden):
  fpc.py altin <ad>        work/<ad>/metrikler.json -> parts/<ad>_altin.json (onaylı durum; bilerek güncellenir)
  fpc.py regress <ad|all>  verify çalıştırır ve altınla karşılaştırır; GERİLEME / AĞ DEĞİŞTİ / YENİ HATA varsa çıkış 1
Karşılaştırılanlar: kenar metrikleri (toleranslı), IoU, karşılıksız oran, ağ imzası (pin -> uçlar), bulgu kimlikleri.
Algoritma veya tasarım değişikliğinden sonra tüm parçalarda çalıştır; iyileşme varsa `altin` ile yeni durumu onayla.
"""
import datetime
import glob
import json
import os

import cfg

# (yol, yön, tolerans): yön +1 = büyük iyi, -1 = küçük iyi, 0 = mutlak değeri küçük iyi
OLCUTLER = [
    ("gumus.kenar.medyan_mm", -1, 0.005), ("gumus.kenar.p90_mm", -1, 0.01), ("gumus.kenar.kapsama", 1, 0.02),
    ("gumus.kenar.ofset_mm", 0, 0.01), ("gumus.iou", 1, 0.01), ("gumus.karsiliksiz_oran", -1, 0.01),
    ("dielektrik.iou", 1, 0.005), ("dielektrik.kenar.medyan_mm", -1, 0.005), ("dielektrik.kenar.p90_mm", -1, 0.01),
    ("dielektrik.kenar.kapsama", 1, 0.02),
]


def _get(M, yol):
    for k in yol.split("."):
        if not isinstance(M, dict) or k not in M:
            return None
        M = M[k]
    return M


def ozet(M):
    return dict(tarih=f"{datetime.datetime.now():%Y-%m-%d %H:%M}", gecti=M["gecti"],
                metrik={y: _get(M, y) for y, _, _ in OLCUTLER if _get(M, y) is not None},
                ag_imza=M["ag"]["imza"],
                bulgular={b["id"]: b["seviye"] for b in M["bulgular"] if b["seviye"] != "BILGI"})


def altin(ad):
    M = json.load(open(cfg.work(ad, "metrikler.json"), encoding="utf-8"))
    p = f"parts/{ad}_altin.json"
    json.dump(ozet(M), open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{ad}: altın kaydedildi -> {p}")


def karsilastir(ad, M):
    p = f"parts/{ad}_altin.json"
    if not os.path.exists(p):
        print(f"{ad}: altın yok (önce: fpc.py altin {ad})")
        return True
    A, Y = json.load(open(p, encoding="utf-8")), ozet(M)
    kotu = False
    print(f"== {ad} (altın: {A['tarih']})")
    for yol, yon, tol in OLCUTLER:
        a, y = A["metrik"].get(yol), Y["metrik"].get(yol)
        if a is None or y is None:
            continue
        fark = (abs(y) - abs(a)) * -1 if yon == 0 else (y - a) * yon
        durum = "GERILEME" if fark < -tol else "iyilesme" if fark > tol else "ayni"
        kotu |= durum == "GERILEME"
        if durum != "ayni":
            print(f"  {durum:9s} {yol}: {a:.4f} -> {y:.4f}")
    ea, ey = set(A["ag_imza"]), set(Y["ag_imza"])
    if ea != ey:
        kotu = True
        print("  AG DEGISTI:")
        for s in sorted(ea - ey):
            print(f"    - {s}")
        for s in sorted(ey - ea):
            print(f"    + {s}")
    for i, sev in Y["bulgular"].items():
        if i not in A["bulgular"]:
            kotu |= sev == "HATA"
            print(f"  YENI {sev}: {i}")
    for i in A["bulgular"]:
        if i not in Y["bulgular"]:
            print(f"  cozuldu: {i}")
    if A["gecti"] != Y["gecti"]:
        kotu |= not Y["gecti"]
        print(f"  KABUL: {A['gecti']} -> {Y['gecti']}")
    print(f"  SONUC: {'GERILEME / DEGISIKLIK VAR' if kotu else 'TAMAM'}")
    return not kotu


def parcalar():
    return sorted(os.path.basename(p)[:-11] for p in glob.glob("parts/*_altin.json"))
