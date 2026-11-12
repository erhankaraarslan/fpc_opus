"""P4 - uzun tus devresi (3 tuslu membran anahtar katmani) parametrik tasarimi.

Tum olculer mm. Orijin: kart (bas kismi) sol ust kosesi, y asagi.
Degerler K.pdf taramasindan (1199 dpi, egiklik 1.07 derece + bukulme duzeltmesi, bkz. parts/p4.json
"bukulme") olculup 0.05 mm'ye yuvarlanmistir. Olcek, setin ortak kalibrasyonu 47.17 px/mm
(P1/P2 konnektor adimi 1.00 mm) olarak alinmistir.

Kullanim: python .devin/skills/fpc-vektor/scripts/fpc.py build p4
"""
import math
import os
import sys

sys.path.insert(0, os.path.abspath(".devin/skills/fpc-vektor/scripts"))
import cfg  # noqa: E402,F401
import fpcvec as fv  # noqa: E402

# ------------------------------------------------------------------ ana olculer
W = 36.7            # bas genisligi
H = 141.5           # bas yuksekligi
R = 0.3             # bas kose yaricapi (taramada 0.2-0.4)
XC = W / 2          # kuyruk / konnektor ekseni (18.35)
TAIL_NECK = 11.35   # yariklar arasinda ve bas altinda kuyruk genisligi
TAIL_W = 11.8       # kuyruk genisligi (TAPER1'den uca)
TAPER0 = 137.5     # kuyruk genislemesinin basladigi y (yarik bolgesi icinde)
TAPER1 = 157.5     # kuyruk genislemesinin bittigi y
TAIL_END = 266.25   # toplam boy
SLOT_W = 2.0        # kuyruk yanindaki yarik genisligi (tam yuvarlak uc)
SLOT_TOP = 125.65   # yarik ust ucu
PITCH = 1.0         # konnektor adimi
N_POS = 11          # konnektor pozisyon sayisi
TRACE_W = 0.5       # bas bolgesi hat genisligi
TAIL_TRACE_W = 0.6  # kuyruk hat / kontak genisligi
DIEL_W = 2.0        # hat uzerindeki dielektrik serit genisligi
BLOCK_TOP = 125.65  # kuyruk baglanti blogu ust kenari
NOTCH_TOP = 127.05  # blok altinda hatlarin ayrildigi seviye
DIEL_TOP = 124.4    # kuyruk dielektrik blogu ust kenari
DIEL_TAIL_W = 13.0  # kuyruk dielektrik blogu genisligi (kontura kirpilir)
DUMMY_TOP = 258.35  # 7-8. pozisyon dummy kontak baslangici
STIFF_TOP = 258.25  # arka takviye baslangici
DIEL_END = 259.05   # kuyruk dielektrik bitisi (kontak bolgesi acik)

# Dielektrik baskisinin gumuse gore olculen kaymasi (baski kaymasi, uretim toleransi).
# Cizim ideal (merkezli) yapilir; dogrulama bu kayma ile telafi edilir.
DIEL_KAYMA = (0.15, -0.15)

# Tuslar: 5.0 x 5.0 mm tarak ped, tus ekseni x = 19.2 (P2 ile ayni yerlesim)
KEY_X = 19.2
PAD = 5.0
BAR = 0.55
FING = 0.6
FGAP = 0.5
TIP_GAP = 0.5
RING_OFF = 0.75
RING_LW = 0.2
PADS = {            # ad: (x0, y0, ust tarakta 3 parmak mi?)
    "Ped_A": (KEY_X - PAD / 2, 38.1, True),
    "Ped_B": (KEY_X - 5.8 - PAD / 2, 53.55, False),
    "Ped_C": (KEY_X + 5.8 - PAD / 2, 53.55, False),
}

# Oval pencereler 3.3 x 6.1 mm; satirlar 12.75 mm adimli (4. ile 5. satir arasi 1.5 adim)
OV_W, OV_H = 3.3, 6.1
OV_PITCH = 12.75
OV_ROWS = [round(32.15 + k * OV_PITCH, 3) for k in (0, 1, 2, 3, 4.5, 5.5, 6.5, 7.5)]
OV_COLS = [XC - 13.35, XC + 13.35]
OV_CENTER = [(KEY_X, 47.9), (KEY_X - 6.45, 63.4), (KEY_X, 63.4), (KEY_X + 6.45, 63.4)]

# Tarama hizalama (dogrulama icin): deskew px -> mm
SCAN = dict(s=47.17, px0=1040.0, py0=183.0, mm0=(XC, 0.0), diel_kayma_mm=DIEL_KAYMA)


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
    D = fv.Design(name="P4", title="P4 - Uzun tuş devresi (3 tuş, 11 pin 1.0 mm)", width=W, height=TAIL_END)
    D.scan = SCAN

    # ---------------------------------------------------------------- kesim
    nl, nr = XC - TAIL_NECK / 2, XC + TAIL_NECK / 2
    tl, tr = XC - TAIL_W / 2, XC + TAIL_W / 2
    sc = SLOT_TOP + SLOT_W / 2
    D.outline = [
        ("M", R, 0), ("L", W - R, 0), ("A", R, 1, W, R), ("L", W, H - R), ("A", R, 1, W - R, H),
        ("L", nr + SLOT_W, H), ("L", nr + SLOT_W, sc), ("A", SLOT_W / 2, 0, nr, sc),
        ("L", nr, TAPER0), ("L", tr, TAPER1), ("L", tr, TAIL_END), ("L", tl, TAIL_END), ("L", tl, TAPER1),
        ("L", nl, TAPER0), ("L", nl, sc), ("A", SLOT_W / 2, 0, nl - SLOT_W, sc),
        ("L", nl - SLOT_W, H), ("L", R, H), ("A", R, 1, 0, H - R), ("L", 0, R), ("A", R, 1, R, 0), ("Z",),
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
    xl = 7.75
    ltop_p, ltop_a = mm(580.55, 2062.15), 120.07
    ldia_p, ldia_a = mm(681.95, 3847.2), 67.08
    xn1 = 13.8
    v1 = line_y(ltop_p, ltop_a, ya)
    v2 = line_x(ltop_p, ltop_a, xl)
    v3 = line_x(ldia_p, ldia_a, xl)
    v4 = line_x(ldia_p, ldia_a, xn1)
    D.traces.append(("Hat_Net1_A_ust", [r2(p) for p in [(ax0 + ov, ya), v1, v2, v3, v4, (xn1, BLOCK_TOP + ov)]], TRACE_W))

    # Net 4 (ortak): A alt tarak -> sag hat -> poz 9-11 ; B/C ust tarak bus
    yr = ay0 + PAD - 0.25
    xr = 28.95
    c1 = 1.15
    rdia4_p, rdia4_a = mm(1383.1, 3840.75), 114.77
    xn4 = 22.3
    u1 = line_x(rdia4_p, rdia4_a, xr)
    u2 = line_x(rdia4_p, rdia4_a, xn4)
    D.traces.append(("Hat_Net4_Ortak", [r2(p) for p in [
        (ax0 + PAD - ov, yr), (xr - c1, yr), (xr, yr + c1), u1, u2, (xn4, BLOCK_TOP + ov)]], TRACE_W))
    ybus = by0 + 0.25
    D.traces.append(("Hat_Net4_Bus_BC", [(bx0 + PAD - ov, ybus), (xr, ybus)], TRACE_W))

    # Net 2: B alt tarak (sag dis parmak) -> hafif kaydirma -> poz 3-4
    xb = bx0 + PAD - FING / 2
    xn2 = 15.8
    D.traces.append(("Hat_Net2_B_alt", [(xb, by0 + PAD - ov), (xb, 79.45), (xn2, 87.9), (xn2, BLOCK_TOP + ov)], TRACE_W))

    # Net 3: C alt tarak (sol dis parmak) -> capraz -> poz 5-6
    xc = 22.75
    rdia3_p, rdia3_a = mm(1130.4, 3928.55), 115.7
    xn3 = 17.8
    w1 = line_x(rdia3_p, rdia3_a, xc)
    w2 = line_x(rdia3_p, rdia3_a, xn3)
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
    D.diel_rects.append((XC - DIEL_TAIL_W / 2, DIEL_TOP, DIEL_TAIL_W, DIEL_END - DIEL_TOP))
    for name, (x0, y0, _) in PADS.items():
        D.diel_rings.append((x0 - RING_OFF, y0 - RING_OFF, PAD + 2 * RING_OFF, PAD + 2 * RING_OFF, RING_LW))

    # ---------------------------------------------------------------- takviye
    D.stiff_rects.append((tl, STIFF_TOP, TAIL_W, TAIL_END - STIFF_TOP))
    return D


RAPOR = dict(
    ozet="3 tuşlu membran anahtar katmanı (tarak tipi pedler), 20 oval LED ışık penceresi, 11 pinlik 1.0 mm "
         "ZIF kuyruğu. Tek gümüş baskı + dielektrik şerit/çerçeve. P3 uzun LED devresiyle üst üste biner; "
         "tuş grubu ve kuyruk yerleşimi P2 ile aynıdır, baş 54 mm, kuyruk 46 mm daha uzundur.",
    olculer=[
        ("Baş (genişlik × yükseklik)", f"{W} × {H} mm", f"köşe R{R}"),
        ("Toplam boy", f"{TAIL_END} mm", ""),
        ("Kuyruk genişliği", f"{TAIL_NECK} → {TAIL_W} mm", f"y={TAPER0}–{TAPER1} arasında genişler"),
        ("Yarık", f"{SLOT_W} mm", f"üst ucu y={SLOT_TOP}"),
        ("Konnektör", f"{N_POS} poz × {PITCH} mm", f"kontak {TAIL_TRACE_W} mm, 7-8 dummy"),
        ("Hat genişliği (baş)", f"{TRACE_W} mm", f"dielektrik şerit {DIEL_W} mm"),
        ("Tuş pedi", f"{PAD} × {PAD} mm", f"bar {BAR}, parmak {FING}, boşluk {FGAP}, uç boşluğu {TIP_GAP} mm"),
        ("Oval pencere", f"{OV_W} × {OV_H} mm", f"20 adet, satır adımı {OV_PITCH} mm"),
        ("Dielektrik bitişi / takviye", f"y={DIEL_END} / y={STIFF_TOP} mm", ""),
        ("Dielektrik baskı kayması (ölçülen)", f"x {DIEL_KAYMA[0]:+.2f} / y {DIEL_KAYMA[1]:+.2f} mm", "çizimde ideal"),
    ],
    varsayimlar=[
        "Ölçek setin ortak kalibrasyonu 47.17 px/mm (P1/P2 konnektör adımı 1.00 mm); P4 kuyruğunda adım 1.003 mm ölçüldü.",
        "Film taramada düzlemde bükük: baş baskısı kuyruğa göre 0.445° dönük, kuyruk ±4 px yay. Ön işlemede "
        "satır bazlı bükülme düzeltmesi uygulandı (parts/p4.json 'bukulme').",
        "Kesim deseni baskıya göre ~0.22° dönük ölçüldü; çizimde ideal hizalı ve simetrik alındı.",
        "Dielektrik baskısı gümüşe göre ~0.2 mm sağa, ~0.15 mm yukarı kayık; çizimde gümüşe merkezli alındı.",
        "Baş köşe yarıçapı R0.3 mm (taramada 0.2–0.4 mm).",
        "Tüm ovaller 3.3 × 6.1 mm (ölçülen genişlik 3.16–3.40, boy 5.8–6.4 mm).",
        "Ped çevresindeki ince turkuaz çerçeve dielektrik baskı kabul edildi.",
        "Yatay gümüş kenarların ~0.4 mm üstündeki koyu bantlar tarayıcı gölgesi sayıldı, çizilmedi.",
    ],
    kontrol_listesi=[
        "Kuyruk genişliği: baş altında ~11.35 mm, y≈163 mm'den sonra ~11.8 mm ölçüldü (kumpasla iki noktada ölçün).",
        "Köşe yarıçapı (R0.3 mm varsayıldı)",
        "Ped çerçevesi: dielektrik mi, spacer/yapışkan kenarı mı?",
        "Kuyruk ucundaki ~8 mm bölge arka yüz takviyesi mi?",
        "Baş üst sağındaki üçgen gri bölge ve pedler çevresindeki daire/kanal izleri: ayrı katman (spacer/yapışkan) mı?",
    ],
    pin_eslemesi=[("1-2", "Net1: A üst tarak (sol dış hat)"), ("3-4", "Net2: B alt tarak"),
                  ("5-6", "Net3: C alt tarak"), ("7-8", "dummy"), ("9-11", "Net4 ortak: A alt + B/C üst tarak")],
)


def main():
    import subprocess
    subprocess.run([sys.executable, ".devin/skills/fpc-vektor/scripts/fpc.py", "build", "p4"], check=True)


if __name__ == "__main__":
    main()
