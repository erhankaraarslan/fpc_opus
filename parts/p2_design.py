"""P2 - kisa tus devresi (3 tuslu membran anahtar katmani) parametrik tasarimi.

Tum olculer mm. Orijin: kart (bas kismi) sol ust kosesi, y asagi.
Degerler K.pdf taramasindan (1199 dpi, egiklik 0.76 derece duzeltilmis) olculup
0.05 mm'ye yuvarlanmistir. Olcek, kuyruk konnektor adimi = 1.00 mm alinarak
kalibre edilmistir (47.17 px/mm; tarayici nominali 47.21 px/mm).

Kullanim: python .devin/skills/fpc-vektor/scripts/fpc.py build p2
"""
import math
import os
import sys

sys.path.insert(0, os.path.abspath(".devin/skills/fpc-vektor/scripts"))
import cfg  # noqa: E402,F401
import fpcvec as fv  # noqa: E402

# ------------------------------------------------------------------ ana olculer
W = 36.7            # bas genisligi
H = 87.4            # bas yuksekligi
R = 1.0             # bas kose yaricapi
XC = W / 2          # kuyruk / konnektor ekseni (18.35)
TAIL_W = 12.1       # kuyruk genisligi
TAIL_END = 171.9    # toplam boy
SLOT_W = 2.0        # kuyruk yanindaki yarik genisligi (tam yuvarlak uc)
SLOT_TOP = 71.55    # yarik ust ucu
PITCH = 1.0         # konnektor adimi
N_POS = 11          # konnektor pozisyon sayisi
TRACE_W = 0.5       # bas bolgesi hat genisligi
TAIL_TRACE_W = 0.6  # kuyruk hat / kontak genisligi
DIEL_W = 2.0        # hat uzerindeki dielektrik serit genisligi
BLOCK_TOP = 71.1    # kuyruk baglanti blogu ust kenari
NOTCH_TOP = 72.35   # blok altinda hatlarin ayrildigi seviye
DUMMY_TOP = 158.95  # 7-8. pozisyon dummy kontak baslangici
DIEL_END = 163.9    # kuyruk dielektrik bitisi (kontak bolgesi acik)
STIFF_TOP = 164.0   # arka takviye baslangici

# Tuslar: 5.0 x 5.0 mm tarak ped, tus ekseni x = 19.2
KEY_X = 19.2
PAD = 5.0
BAR = 0.55
FING = 0.6
FGAP = 0.5
TIP_GAP = 0.5
RING_OFF = 0.75     # dielektrik ped cercevesi (cizgi merkezi) ofseti
RING_LW = 0.2
PADS = {            # ad: (x0, y0, ust tarakta 3 parmak mi?)
    "Ped_A": (KEY_X - PAD / 2, 37.8, True),
    "Ped_B": (KEY_X - 5.8 - PAD / 2, 53.25, False),
    "Ped_C": (KEY_X + 5.8 - PAD / 2, 53.25, False),
}

# Oval pencereler 3.2 x 6.1 mm
OV_W, OV_H = 3.2, 6.1
OV_ROWS = [34.0, 46.7, 59.4, 72.1]
OV_COLS = [XC - 13.35, XC + 13.35]
OV_CENTER = [(KEY_X, 47.7), (KEY_X - 6.45, 63.65), (KEY_X, 63.65), (KEY_X + 6.45, 63.65)]

# Tarama hizalama (dogrulama icin): deskew px -> mm
SCAN = dict(s=47.17, px0=921.5, py0=213.0, mm0=(XC, 0.0))


def mm(px, py):
    return ((px - SCAN["px0"]) / SCAN["s"] + XC, (py - SCAN["py0"]) / SCAN["s"])


def line_x(p, ang_deg, x):
    """p noktasindan ang (y asagi, derece) acili dogrunun x'teki noktasi."""
    t = math.tan(math.radians(ang_deg))
    return (x, p[1] + (x - p[0]) * t)


def line_y(p, ang_deg, y):
    t = math.tan(math.radians(ang_deg))
    return (p[0] + (y - p[1]) / t, y)


def r2(p):
    return (round(p[0], 3), round(p[1], 3))


def pos_x(i):
    return XC + (i - (N_POS - 1) / 2) * PITCH


def comb(name, x0, y0, top3):
    rects = [(name, x0, y0, PAD, BAR), (name, x0, y0 + PAD - BAR, PAD, BAR)]
    flen = PAD - 2 * BAR - TIP_GAP
    for k in range(5):
        fx = x0 + k * (FING + FGAP)
        from_top = (k % 2 == 0) == top3
        fy = y0 + BAR if from_top else y0 + BAR + TIP_GAP
        rects.append((name, fx, fy, FING, flen))
    return rects


def build():
    D = fv.Design(name="P2", title="P2 - Kısa tuş devresi (3 tuş, 11 pin 1.0 mm)", width=W, height=TAIL_END)
    D.scan = SCAN

    # ---------------------------------------------------------------- kesim
    tl, tr = XC - TAIL_W / 2, XC + TAIL_W / 2
    sc = SLOT_TOP + SLOT_W / 2
    D.outline = [
        ("M", R, 0), ("L", W - R, 0), ("A", R, 1, W, R), ("L", W, H - R), ("A", R, 1, W - R, H),
        ("L", tr + SLOT_W, H), ("L", tr + SLOT_W, sc), ("A", SLOT_W / 2, 0, tr, sc),
        ("L", tr, TAIL_END), ("L", tl, TAIL_END), ("L", tl, sc), ("A", SLOT_W / 2, 0, tl - SLOT_W, sc),
        ("L", tl - SLOT_W, H), ("L", R, H), ("A", R, 1, 0, H - R), ("L", 0, R), ("A", R, 1, R, 0), ("Z",),
    ]
    D.holes = [(x, y, OV_W, OV_H) for y in OV_ROWS for x in OV_COLS] + [(x, y, OV_W, OV_H) for x, y in OV_CENTER]
    D.holes.sort(key=lambda h: (round(h[1], 1), h[0]))

    # ---------------------------------------------------------------- pedler
    for name, (x0, y0, top3) in PADS.items():
        D.silver_rects += comb(name, x0, y0, top3)
    ax0, ay0, _ = PADS["Ped_A"]
    bx0, by0, _ = PADS["Ped_B"]
    cx0, cy0, _ = PADS["Ped_C"]

    # ---------------------------------------------------------------- hatlar
    ov = 0.3  # ped / blok icine bindirme
    # Net 1: A ust tarak -> sol dis hat -> poz 1-2
    ya = ay0 + 0.25
    xl = 7.7
    ltop_p, ltop_a = mm(460.0, 2075.1), 120.02
    ldia_p, ldia_a = mm(560.2, 3354.2), 51.44
    xn1 = 13.75
    v1 = line_y(ltop_p, ltop_a, ya)
    v2 = line_x(ltop_p, ltop_a, xl)
    v3 = line_x(ldia_p, ldia_a, xl)
    v4 = line_x(ldia_p, ldia_a, xn1)
    D.traces.append(("Hat_Net1_A_ust", [r2(p) for p in [(ax0 + ov, ya), v1, v2, v3, v4, (xn1, BLOCK_TOP + ov)]], TRACE_W))

    # Net 4 (ortak): A alt tarak -> sag hat -> poz 9-11 ; B/C ust tarak bus
    yr = ay0 + PAD - 0.25
    xr = 28.9
    c1, c2, c3 = 1.15, 0.75, 0.9
    ybot = 69.55
    xn4 = 22.25
    D.traces.append(("Hat_Net4_Ortak", [r2(p) for p in [
        (ax0 + PAD - ov, yr), (xr - c1, yr), (xr, yr + c1), (xr, ybot - c2), (xr - c2, ybot),
        (xn4 + c3, ybot), (xn4, ybot + c3), (xn4, BLOCK_TOP + ov)]], TRACE_W))
    ybus = by0 + 0.25
    D.traces.append(("Hat_Net4_Bus_BC", [(bx0 + PAD - ov, ybus), (xr, ybus)], TRACE_W))

    # Net 2: B alt tarak -> poz 3-4
    xb = bx0 + PAD - FING / 2
    D.traces.append(("Hat_Net2_B_alt", [(xb, by0 + PAD - ov), (xb, BLOCK_TOP + ov)], TRACE_W))

    # Net 3: C alt tarak -> capraz -> poz 5-6
    xc = cx0 + FING / 2
    rdia_p, rdia_a = mm(1013.1, 3392.8), 129.79
    xn3 = 17.7
    w1 = line_x(rdia_p, rdia_a, xc)
    w2 = line_x(rdia_p, rdia_a, xn3)
    D.traces.append(("Hat_Net3_C_alt", [r2(p) for p in [(xc, cy0 + PAD - ov), w1, w2, (xn3, BLOCK_TOP + ov)]], TRACE_W))

    # ---------------------------------------------------------------- kuyruk
    half = TAIL_TRACE_W / 2
    for gname, (i0, i1) in {"Blok_Net1": (0, 1), "Blok_Net2": (2, 3), "Blok_Net3": (4, 5), "Blok_Net4": (8, 10)}.items():
        x0, x1 = pos_x(i0) - half, pos_x(i1) + half
        D.silver_rects.append((gname, x0, BLOCK_TOP, x1 - x0, NOTCH_TOP - BLOCK_TOP))
    for i in range(N_POS):
        top = DUMMY_TOP if i in (6, 7) else BLOCK_TOP
        name = f"Kontak_{i + 1:02d}" + ("_dummy" if i in (6, 7) else "")
        D.traces.append((name, [(pos_x(i), top), (pos_x(i), TAIL_END)], TAIL_TRACE_W))

    # ---------------------------------------------------------------- dielektrik
    for _, pts, w in D.traces:
        if w == TRACE_W:
            D.diel_lines.append((pts, DIEL_W))
    D.diel_rects.append((XC - 6.7, 70.75, 13.4, DIEL_END - 70.75))
    for name, (x0, y0, _) in PADS.items():
        D.diel_rings.append((x0 - RING_OFF, y0 - RING_OFF, PAD + 2 * RING_OFF, PAD + 2 * RING_OFF, RING_LW))

    # ---------------------------------------------------------------- takviye
    D.stiff_rects.append((tl, STIFF_TOP, TAIL_W, TAIL_END - STIFF_TOP))
    return D


RAPOR = dict(
    ozet="3 tuşlu membran anahtar katmanı (tarak tipi pedler), 12 oval LED ışık penceresi, 11 pinlik 1.0 mm "
         "ZIF kuyruğu. Tek gümüş baskı + dielektrik şerit/çerçeve. P1 LED devresiyle üst üste biner.",
    olculer=[
        ("Baş (genişlik × yükseklik)", f"{W} × {H} mm", f"köşe R{R}"),
        ("Toplam boy", f"{TAIL_END} mm", ""),
        ("Kuyruk genişliği", f"{TAIL_W} mm", f"yarık {SLOT_W} mm, üst ucu y={SLOT_TOP}"),
        ("Konnektör", f"{N_POS} poz × {PITCH} mm", f"kontak {TAIL_TRACE_W} mm, 7-8 dummy"),
        ("Hat genişliği (baş)", f"{TRACE_W} mm", f"dielektrik şerit {DIEL_W} mm"),
        ("Tuş pedi", f"{PAD} × {PAD} mm", f"bar {BAR}, parmak {FING}, boşluk {FGAP}, uç boşluğu {TIP_GAP} mm"),
        ("Oval pencere", f"{OV_W} × {OV_H} mm", "12 adet"),
        ("Dielektrik bitişi / takviye", f"y={DIEL_END} / y={STIFF_TOP} mm", ""),
    ],
    varsayimlar=[
        "Ölçek konnektör adımı 1.00 mm alınarak kalibre edildi (47.17 px/mm; tarayıcı nominali 47.21).",
        "Kesim deseni baskıya göre ~0.2° dönük ölçüldü; çizimde ideal hizalı ve simetrik alındı.",
        "Baş köşe yarıçapı R1.0 mm (taramada 0.5–1.0 mm).",
        "Tüm ovaller 3.2 × 6.1 mm (ölçülen boylar 5.8–6.3 mm).",
        "Ped çevresindeki ince turkuaz çerçeve dielektrik baskı kabul edildi.",
        "Yatay gümüş kenarların ~0.4 mm üstündeki koyu bantlar tarayıcı gölgesi sayıldı, çizilmedi.",
    ],
    kontrol_listesi=[
        "Köşe yarıçapı (R1.0 mm varsayıldı)",
        "Ped çerçevesi: dielektrik mi, spacer/yapışkan kenarı mı?",
        "Kuyruk ucundaki 7.9 mm bölge arka yüz takviyesi mi?",
    ],
    pin_eslemesi=[("1-2", "Net1: A üst tarak (sol dış hat)"), ("3-4", "Net2: B alt tarak"),
                  ("5-6", "Net3: C alt tarak"), ("7-8", "dummy"), ("9-11", "Net4 ortak: A alt + B/C üst tarak")],
)


def main():
    import subprocess
    subprocess.run([sys.executable, ".devin/skills/fpc-vektor/scripts/fpc.py", "build", "p2"], check=True)


if __name__ == "__main__":
    main()
