"""Skill araçlarının sentetik doğruluk testleri (taramaya ve parçalara bağlı değil).

Kullanım: python selftest.py      (veya fpc.py selftest)
Algoritma değiştirildiğinde çalıştır; hepsi "TAMAM" olmalı.
  kenar   bilinen ofset/kayma ile çizilmiş şekilde alt-piksel sapma, ofset ve kayma geri bulunuyor mu
  ag      kısa devre, pinsiz ağ, tarak sayısı, köprü bağlantısı (yalıtkan altı geçiş bağlamaz)
  tutarlilik  yakın boşluk, mikro segment, köprü ucu yalıtkanda, yalıtımsız kesişim
"""
import sys

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Polygon, box

import cfg  # noqa: F401
import fpcvec as fv
import kenar
import netlist
import tutarlilik

HATA = []


def ok(kosul, ad):
    print(("  TAMAM  " if kosul else "  HATALI ") + ad)
    if not kosul:
        HATA.append(ad)


def coverage(geom, shape, ss=8):
    """Alt-örneklemeli kapsama haritası [0,1] (piksel merkezi = tamsayı koordinat)."""
    H, W = shape
    m = np.zeros((H * ss, W * ss), np.uint8)
    for p in netlist.parts(geom.buffer(-0.5 / ss, join_style="mitre")):  # fillPoly sınır pikselini de doldurur
        for r, v in [(p.exterior, 1), *[(i, 0) for i in p.interiors]]:
            q = (np.asarray(r.coords) + 0.5) * ss - 0.5
            cv2.fillPoly(m, [np.round(q * 16).astype(np.int32)], v, shift=4)
    return m.reshape(H, ss, W, ss).mean((1, 3)).astype(np.float32)


def test_kenar():
    print("kenar")
    gercek = box(60.3, 50.7, 260.3, 90.7).union(LineString([(80, 150), (300, 150), (340, 190)]).buffer(11.8, cap_style="flat", join_style="mitre"))
    F = coverage(gercek, (260, 400))
    for a0, s0 in ((0.0, (0, 0)), (0.7, (0.4, -0.3)), (-1.2, (-0.5, 0.8))):
        ciz = affinity.translate(gercek.buffer(a0, join_style="mitre"), *s0)
        oz, _, _ = kenar.olc(ciz, F, 1.0)
        ok(abs(oz["ofset_mm"] - a0) < 0.08 and abs(oz["kayma_mm"][0] - s0[0]) < 0.08 and abs(oz["kayma_mm"][1] - s0[1]) < 0.08
           and oz["kapsama"] > 0.99, f"ofset {a0:+.1f} kayma {s0}: ölçülen {oz['ofset_mm']:+.3f} "
                                     f"({oz['kayma_mm'][0]:+.3f}, {oz['kayma_mm'][1]:+.3f}), kapsama {oz['kapsama']:.3f}")
    ikili = F >= 0.5
    oz, _, _ = kenar.olc(affinity.translate(gercek, 0.3, 0), ikili, 1.0)
    ok(abs(oz["kayma_mm"][0] - 0.3) < 0.25, f"ikili maske, kayma 0.3 px: ölçülen {oz['kayma_mm'][0]:+.3f} (±0.25)")
    ciz = gercek.buffer(0)
    els = [("kutu", "dikdortgen", box(60.3, 50.7, 260.3, 90.7)),
           ("hat", "hat", LineString([(80, 150), (300, 150), (340, 190)]).buffer(11.8, cap_style="flat", join_style="mitre"))]
    els[1] = ("hat", "hat", affinity.translate(els[1][2], 0, 1.0))
    ciz = els[0][2].union(els[1][2])
    _, tab, _ = kenar.olc(ciz, F, 1.0, elemanlar=els)
    t = {r["ad"]: r for r in tab}
    ok(abs(t["kutu"]["ofset_mm"]) < 0.08 and abs(t["hat"]["kayma_mm"][1] - 1.0) < 0.1,
       f"eleman bazlı: kutu ofset {t['kutu']['ofset_mm']:+.3f}, hat y kayması {t['hat']['kayma_mm'][1]:+.3f} (beklenen +1.0)")


def _renkli(F, ic=(150, 205, 140), dis=(245, 248, 250), sigma=1.5, gurultu=3.0, seed=0):
    """Kapsama haritasından renkli, bulanık, gürültülü sentetik tarama (BGR)."""
    rng = np.random.default_rng(seed)
    im = F[..., None] * np.array(ic, np.float32) + (1 - F[..., None]) * np.array(dis, np.float32)
    im = cv2.GaussianBlur(im, (0, 0), sigma) + rng.normal(0, gurultu, im.shape).astype(np.float32)
    return np.clip(im, 0, 255).astype(np.uint8)


def test_profil():
    import profil
    print("profil (yoğunluk kenarı)")
    gercek = box(60.3, 50.7, 260.3, 90.7).union(LineString([(80, 150), (300, 150), (340, 190)]).buffer(11.8, cap_style="flat", join_style="mitre"))
    F = coverage(gercek, (260, 400))
    for ic, ad in (((150, 205, 140), "turkuaz/film"), ((185, 188, 190), "gümüş/film")):
        im = _renkli(F, ic)
        for a0, s0 in ((0.0, (0, 0)), (0.8, (-0.4, 0.5))):
            oz, _, _ = profil.olc(affinity.translate(gercek.buffer(a0, join_style="mitre"), *s0), im, 1.0)
            ok(abs(oz["ofset_mm"] - a0) < 0.12 and abs(oz["kayma_mm"][0] - s0[0]) < 0.12 and abs(oz["kayma_mm"][1] - s0[1]) < 0.12
               and abs(oz["sigma_mm"] - 1.5) < 0.35,
               f"{ad} ofset {a0:+.1f} kayma {s0}: ölçülen {oz['ofset_mm']:+.3f} ({oz['kayma_mm'][0]:+.3f}, "
               f"{oz['kayma_mm'][1]:+.3f}), σ {oz['sigma_mm']:.2f} (beklenen 1.5)")
    # maske yanlılığı: sıkı eşikli maske dar, yoğunluk kenarı doğru
    im = _renkli(F)
    dar = F > 0.5
    dar = cv2.erode(dar.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    om = kenar.olc(gercek, dar, 1.0)[0]["ofset_mm"]
    oy = profil.olc(gercek, im, 1.0)[0]["ofset_mm"]
    ok(om > 0.7 and abs(oy) < 0.12, f"1 px aşınmış maske: maske ofseti {om:+.2f}, yoğunluk ofseti {oy:+.2f} (maske yanlılığı yakalanır)")


def test_golge():
    import golge
    print("golge")
    rng = np.random.default_rng(1)
    H, W = 600, 600
    im = np.full((H, W, 3), 250, np.float32)
    S = np.zeros((H, W), bool)
    for y in range(80, 560, 70):
        S[y:y + 24, 40:560] = True
    d0 = 16
    G = np.zeros_like(S)
    G[:-d0] = S[d0:]
    G &= ~S
    im[G] = 172
    im[S] = 192 + rng.normal(0, 14, (S.sum(), 1))  # dokulu gümüş
    im = np.clip(cv2.GaussianBlur(im, (0, 0), 0.7), 0, 255).astype(np.uint8)
    R = golge.kestir(im)
    ok(abs(R["genel"] - d0) <= 2, f"sentetik gölge ofseti {d0} px: kestirim {R['genel']:.1f} px")
    tp = (R["G"] & G).sum() / G.sum()
    fp = (R["G"] & ~G).sum() / max(R["G"].sum(), 1)
    ok(tp > 0.8 and fp < 0.2, f"gölge maskesi: yakalama {tp:.2f}, yanlış {fp:.2f}")


def test_kalibre():
    import kalibre
    print("kalibre (ölçek, bükülme)")
    rng = np.random.default_rng(2)
    x = np.arange(560.0)
    for P in (47.23, 46.9):
        p = 180 + 38 * (np.mod(x - 13.4, P) < 19)
        p = np.convolve(p, np.ones(3) / 3, "same") + rng.normal(0, 3, len(p))
        p[300:330] = 180  # boş (dummy) pozisyon
        per, n, rms = kalibre.adim_bul(p, 47.17)
        ok(abs(per - P) < 0.03, f"adım {P} px: ölçülen {per:.3f} px ({n} hat, artık {rms:.2f} px)")
    H, W = 3000, 400
    im = np.full((H, W, 3), 250, np.uint8)
    ys = np.arange(H)
    dx = 6 * np.sin(ys / H * np.pi)  # 6 px yay
    for x0 in (60, 150, 230, 330):
        for y in range(H):
            xx = int(round(x0 + dx[y]))
            im[y, xx - 6:xx + 6] = 180
    yc, xs, _ = kalibre.bukulme_kestir(im)
    gercek = np.interp(yc, ys, dx)
    e = (xs - xs.mean()) - (gercek - gercek.mean())
    ok(np.abs(e).max() < 1.0, f"sentetik 6 px yay: bükülme kestirim hatası maks {np.abs(e).max():.2f} px")


def test_kayit():
    import kayit
    print("kayit (ön + arka çakıştırma)")
    rng = np.random.default_rng(3)
    H, W = 700, 500
    on = np.full((H, W, 3), 245, np.uint8)
    for _ in range(40):
        x, y = rng.integers(20, W - 60), rng.integers(20, H - 60)
        if rng.random() < 0.5:
            cv2.rectangle(on, (int(x), int(y)), (int(x + rng.integers(15, 60)), int(y + rng.integers(8, 25))), (185, 188, 190), -1)
        else:
            cv2.line(on, (int(x), int(y)), (int(x), int(y + rng.integers(60, 200))), (150, 205, 140), 9)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0.6, 1.002)
    M[:, 2] += (14.3, -8.6)
    arka = cv2.warpAffine(255 - on, M, (W + 30, H + 30), borderValue=(255, 255, 255))  # ters kontrast (arka yüz rengi farklı)
    arka = cv2.flip(arka, 1)
    R = kayit.kaydet_goruntu(on, arka, "yatay")
    hiz = R["hizali"]
    fark = np.abs(cv2.GaussianBlur((255 - hiz).astype(np.float32), (0, 0), 1) - cv2.GaussianBlur(on.astype(np.float32), (0, 0), 1))
    m = fark[40:-40, 40:-40].mean()
    ok(R["ecc"] > 0.8 and m < 6, f"aynalı + 0.6° + öteleme: ECC {R['ecc']:.3f}, hizalı ortalama fark {m:.1f} gri düzeyi")


def _led_design(kisa=False, kopuk=False):
    D = fv.Design(name="T", title="test", width=30, height=40)
    D.outline = [("M", 0, 0), ("L", 30, 0), ("L", 30, 40), ("L", 0, 40), ("Z",)]
    D.leds.append(("LED_A", 10, 10, 0.5, 1.0))
    D.silver_rects += [("LED_A_ped_ust", 9, 8, 2, 1.5), ("LED_A_ped_alt", 9, 10.5, 2, 1.5)]
    D.traces.append(("A_ust", [(10, 8.2), (10, 5), (5, 5), (5, 40)], 0.5))
    D.traces.append(("Kontak_01", [(5, 35), (5, 40)], 0.6))
    alt_bas = (10, 11.8 + (0.3 if kopuk else 0))
    D.traces.append(("A_alt", [alt_bas, (10, 20), (15, 20), (15, 40)], 0.5))
    D.traces.append(("Kontak_02", [(15, 35), (15, 40)], 0.6))
    if kisa:
        D.traces.append(("Kisa", [(10, 9), (10, 11)], 0.3))
    return D


def test_ag():
    print("ag")
    A = netlist.analiz(_led_design())
    hk = {b["kod"] for b in A["bulgular"] if b["seviye"] == "HATA"}
    ok(not hk and len(A["aglar"]) == 2, f"temiz LED devresi: {len(A['aglar'])} ağ, HATA {sorted(hk)}")
    A = netlist.analiz(_led_design(kisa=True))
    ok(any(b["kod"] == "kisa_devre" for b in A["bulgular"]), "iki pedi birleştiren hat -> kisa_devre")
    A = netlist.analiz(_led_design(kopuk=True))
    ok(any(b["kod"] == "pinsiz_ag" for b in A["bulgular"]), "pede 0.3 mm değmeyen hat -> pinsiz_ag")
    ok(any(b["kod"] == "yakin_bosluk" for b in tutarlilik.kontrol(_led_design(kopuk=True))), "aynı durum -> yakin_bosluk")
    # tuş pedi: iki tarak
    D = fv.Design(name="T", title="t", width=20, height=20)
    D.outline = [("M", 0, 0), ("L", 20, 0), ("L", 20, 20), ("L", 0, 20), ("Z",)]
    D.silver_rects += [("Ped_X", 5, 5, 5, 0.5), ("Ped_X", 5, 9.5, 5, 0.5), ("Ped_X", 5, 5.5, 0.6, 3.5), ("Ped_X", 6.1, 6.0, 0.6, 3.5)]
    D.traces += [("Kontak_01", [(5.3, 5), (5.3, 20)], 0.6)]
    A = netlist.analiz(D)
    ok(not any(b["kod"] == "tarak_sayisi" for b in A["bulgular"]), "parmak barla tam değiyor -> 2 tarak")
    # köprü: yalıtkan altından geçen hatla bağlanmamalı
    D = _led_design()
    D.traces.append(("Capraz", [(2, 25), (12, 25)], 0.5))
    D.traces.append(("Kontak_03", [(2, 25), (2, 40)], 0.6))
    D.diel_polys.append(box(4, 23, 6, 27))
    D.bridge_cut.append(("A_ust", box(4.2, 23.2, 5.8, 26.8)))
    D.bridges.append(("Kopru_01_A_ust", [(5, 22.5), (5, 27.5)], 0.5))
    A = netlist.analiz(D)
    p1 = next(a for a in A["aglar"] if 1 in a["pinler"])
    ok(3 not in p1["pinler"], f"köprü altındaki hat bağlanmıyor (pin1 ağı pinleri {p1['pinler']})")
    B = tutarlilik.kontrol(D)
    ok(not any(b["kod"] in ("yalitimsiz_kesisim", "kopru_ucu_yalitkanda") for b in B), "doğru köprü -> köprü bulgusu yok")
    D.bridges[0] = ("Kopru_01_A_ust", [(5, 22.5), (5, 26.0)], 0.5)
    ok(any(b["kod"] == "kopru_ucu_yalitkanda" for b in tutarlilik.kontrol(D)), "yalıtkanda biten köprü -> kopru_ucu_yalitkanda")
    D.diel_polys[0] = box(4, 26, 6, 28)
    D.bridges[0] = ("Kopru_01_A_ust", [(5, 22.5), (5, 28.5)], 0.5)
    ok(any(b["kod"] == "yalitimsiz_kesisim" for b in tutarlilik.kontrol(D)), "yalıtkan dışında kesişen köprü -> yalitimsiz_kesisim")
    D = _led_design()
    D.traces[0] = ("A_ust", [(10, 8.2), (10, 5), (9.95, 5), (5, 5), (5, 40)], 0.5)
    ok(any(b["kod"] == "mikro_segment" for b in tutarlilik.kontrol(D)), "0.05 mm parça -> mikro_segment")


def test_onar():
    import onar
    print("onar (uç kenetleme, köprü uç kuralı)")
    D = _led_design(kopuk=True)
    R = onar.uc_kenetle(D)
    A = netlist.analiz(D)
    ok(any("uzatıldı" in r["durum"] for r in R) and not any(b["kod"] == "pinsiz_ag" for b in A["bulgular"]),
       f"0.3 mm kısa uç pede uzatıldı: {onar.ozet(R)}")
    D = _led_design()
    # pin 3'e giden ayrı hat, pin 1 hattının (x=5, kenar 5.25) 0.1 mm yanında bitiyor: birleştirme iki pinli ağı birleştirir
    D.traces.append(("Ayri", [(9, 30), (5.35, 30)], 0.5))
    D.traces.append(("Kontak_03", [(9, 30), (9, 40)], 0.6))
    R = onar.uc_kenetle(D)
    ok(any(r["hat"] == "Ayri" and "reddedildi" in r["durum"] for r in R) and not any(r["hat"] == "Ayri" and "uzatıldı" in r["durum"] for r in R),
       f"iki pinli ağı birleştirecek uzatma reddedildi: {onar.ozet(R)}")
    sel = [dict(name="T", top=True, pts=[(0, 0), (10, 0)]), dict(name="T", top=True, pts=[(40, 0), (50, 0)])]
    ch = onar.kopru_uc_kurali(sel, [("T", [(0, 0), (100, 0)])])
    ok(ch == ["T"] and not sel[0]["top"] and sel[1]["top"], "rota ucunu yama içinde bitiren parça alt baskıya alındı")


def main():
    test_kenar()
    test_profil()
    test_golge()
    test_kalibre()
    test_kayit()
    test_ag()
    test_onar()
    print("SONUC:", "TAMAM" if not HATA else f"{len(HATA)} HATALI: {HATA}")
    return not HATA


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
