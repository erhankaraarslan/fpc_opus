"""Doğrulama ölçümlerinden somut düzeltme önerileri (yoğunluk kenarı öncelikli; maskeden bağımsız).

Kullanım: python oneri.py <ad>   (veya fpc.py oneri <ad>; önce fpc.py verify <ad>)
Çıktı: work/<ad>/oneriler.json + konsol. Rapor "Önerilen düzeltmeler" bölümünü bundan doldurur.
Öneri türleri:
  hizalama    parametrik (mm ile tanımlı) elemanlar için SCAN px0/py0 düzeltmesi (genel gümüş kayması)
  diel_kayma  tuş tipinde dielektrik baskı kayması telafisinin güncellenmesi (SCAN["diel_kayma_mm"])
  genislik    hat genişliğinin ölçülen değere göre düzeltilmesi (hat türü elemanların medyan ofseti)
  eleman      tek elemanın kaydırılması / daraltılması (kayma veya ofset eşik üstü, artığı küçük)
Kurallar: d = a + n·s modeli (kenar.py); çizim s kadar kaymışsa düzeltme −s, her yandan a genişse genişlik −2a.
Öneriler ölçüme dayalıdır ama otomatik uygulanmaz; tasarım niyetiyle (simetri, ortak adım) çelişiyorsa ölçümü
analiz kaydına yazıp niyeti koruyun.
"""
import json
import sys

import numpy as np

import cfg

ESIK = dict(kayma_mm=0.04, ofset_mm=0.04, genel_kayma_mm=0.02, genislik_mm=0.02, min_ornek=30, min_kapsama=0.6,
            max_rms_mm=0.06)


def _y(r):
    y = r.get("yogunluk") or {}
    return y if y.get("kapsama", 0) >= ESIK["min_kapsama"] and "ofset_mm" in y else r


def uret(ad, D=None):
    from verify import load_design
    c = cfg.load(ad)
    M = json.load(open(cfg.work(ad, "metrikler.json"), encoding="utf-8"))
    T = json.load(open(cfg.work(ad, "eleman_sapma.json"), encoding="utf-8"))
    D = D or load_design(ad)
    sc, S = D.scan, D.scan["s"]
    out = []
    g = M["gumus"].get("yogunluk") or M["gumus"]["kenar"]
    sx, sy = g.get("kayma_mm", [0, 0])
    if max(abs(sx), abs(sy)) > ESIK["genel_kayma_mm"]:
        out.append(dict(tur="hizalama", oncelik=max(abs(sx), abs(sy)),
                        mesaj=f"Gümüş çizimi genel olarak ({sx:+.3f}, {sy:+.3f}) mm kaymış. mm ile tanımlı (parametrik) elemanlar "
                              f"için SCAN px0 {sc['px0']} -> {sc['px0'] - sx * S:.1f}, py0 {sc['py0']} -> {sc['py0'] - sy * S:.1f}. "
                              f"Taramadan px ile okunan rotalar bu değişiklikten etkilenmez.",
                        deger=dict(px0=round(sc["px0"] - sx * S, 1), py0=round(sc["py0"] - sy * S, 1))))
    if "dielektrik" in M:
        d = M["dielektrik"].get("yogunluk") or M["dielektrik"]["kenar"]
        dx, dy = d.get("kayma_mm", [0, 0])
        if max(abs(dx), abs(dy)) > ESIK["genel_kayma_mm"]:
            old = list(sc.get("diel_kayma_mm") or [0.0, 0.0])
            new = [round(old[0] - dx, 3), round(old[1] - dy, 3)]
            out.append(dict(tur="diel_kayma", oncelik=max(abs(dx), abs(dy)),
                            mesaj=f"Dielektrik, telafiden sonra hâlâ ({dx:+.3f}, {dy:+.3f}) mm kayık: SCAN['diel_kayma_mm'] "
                                  f"{old} -> {new} (çizim ideal kalır, yalnız doğrulama telafisi).", deger=new))
    wmap = {n: w for n, _, w in D.traces}
    hat = [(_y(r), wmap.get(r["ad"])) for r in T if r["tur"] == "hat" and r["ornek"] >= ESIK["min_ornek"]]
    hat = [(y["ofset_mm"], w, y.get("rms_mm", 0)) for y, w in hat if "ofset_mm" in y and w]
    by_w = {}
    for a, w, _ in hat:
        by_w.setdefault(round(w, 3), []).append(a)
    for w, a in by_w.items():
        if len(a) >= 3:
            m = float(np.median(a))
            if abs(m) > ESIK["genislik_mm"]:
                out.append(dict(tur="genislik", oncelik=abs(m),
                                mesaj=f"{w} mm hatlar ({len(a)} hat) taramada her yandan {m:+.3f} mm farklı: ölçülen genişlik "
                                      f"≈ {w - 2 * m:.3f} mm -> {round((w - 2 * m) / 0.05) * 0.05:.2f} mm (0.05'e yuvarlı)",
                                deger=round(w - 2 * m, 3)))
    for r in T:
        y = _y(r)
        if r["ornek"] < ESIK["min_ornek"] or "kayma_mm" not in y or y.get("rms_mm", 0) > ESIK["max_rms_mm"]:
            continue
        kx, ky = y["kayma_mm"]
        a = y["ofset_mm"]
        tip = "şablon/tahmin" if r["tur"] in ("led_ped", "isaret") else ""
        if max(abs(kx), abs(ky)) > ESIK["kayma_mm"]:
            out.append(dict(tur="eleman", ad=r["ad"], oncelik=max(abs(kx), abs(ky)), konum=r.get("konum"),
                            mesaj=f"'{r['ad']}' ({r['tur']}{', ' + tip if tip else ''}) taramaya göre ({kx:+.3f}, {ky:+.3f}) mm "
                                  f"kaymış -> ({-kx:+.3f}, {-ky:+.3f}) mm taşı", deger=[round(-kx, 3), round(-ky, 3)]))
        if abs(a) > ESIK["ofset_mm"]:
            w = wmap.get(r["ad"])
            ek = f"; genişlik {w} -> {w - 2 * a:.3f} mm" if w else ""
            out.append(dict(tur="eleman", ad=r["ad"], oncelik=abs(a), konum=r.get("konum"),
                            mesaj=f"'{r['ad']}' ({r['tur']}) her yandan {a:+.3f} mm {'geniş' if a > 0 else 'dar'}{ek}",
                            deger=round(-2 * a, 3)))
    out.sort(key=lambda o: (o["tur"] == "eleman", -o["oncelik"]))
    json.dump(out, open(cfg.work(ad, "oneriler.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return out


def yaz(out, n=25):
    print(f"Öneri sayısı: {len(out)}")
    for o in out[:n]:
        print(f"  [{o['tur']}] {o['mesaj']}")


if __name__ == "__main__":
    yaz(uret(sys.argv[1]))
