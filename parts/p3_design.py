"""P3 - uzun LED devresi (20 LED, 2 gumus baski + dielektrik kopru yamalari) tasarimi.

Tum olculer mm. Orijin: kart bas kismi sol ust kosesi, y asagi.
Hat rotalari parts/p3_routes.py (tarama px) -> refine (m_dark maskesi) -> yatay hatlarda golge
duzeltmesi (alt kenardan) -> mm. Dielektrik yamalari tarama maskesinden otomatik (0/45/90 oturtmali)
cikarilir; kopru (ust gumus) secimi her yama gecisinde renkten (gri = ust, koyu turkuaz = alt) yapilir.

Kullanim: python .devin/skills/fpc-vektor/scripts/fpc.py build p3
"""
import json
import os
import sys

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import LineString
from shapely.ops import unary_union

sys.path.insert(0, os.path.abspath(".devin/skills/fpc-vektor/scripts"))
import cfg  # noqa: E402,F401
import fpcvec as fv  # noqa: E402
import p3_routes as pr  # noqa: E402
import onar  # noqa: E402
from polyvec import mask_to_polys  # noqa: E402
from routes_view import refine_all, route_mask  # noqa: E402

W, H, R = 36.6, 138.55, 0.3
XC = W / 2
TAIL_NECK, TAIL_W = 11.35, 11.8
TAPER0, TAPER1 = 138.2, 159.4
TAIL_END = 263.4
SLOT_W, SLOT_TOP = 2.1, 122.6
TRACE_W, TAIL_TRACE_W = 0.5, 0.6
LED_PAD_W, LED_PAD_H, LED_GAP = 1.65, 1.6, 0.85
LED_BODY = (0.5, 1.0)
PLUS_L, PLUS_W = 0.8, 0.15
BRIDGE_OVL = 0.4

SCAN = dict(s=47.17, px0=964.3, py0=180.0, mm0=(XC, 0.0))
S = SCAN["s"]

# arti isareti ofseti (cip merkezine gore px): sol sutun alt-sag, sag sutun ve orta LED'ler alt-sol
PLUS = {"L": (57, 111), "R": (-47, 113), "C": (-48, 99), "B": (-48, 99)}
CHIP = {"L1": (332.0, 1578.6), "L2": (333.0, 2172.0), "L3": (332.4, 2768.3), "L4": (330.8, 3366.4),
        "L5": (337.4, 4279.3), "L6": (334.1, 4877.1), "L7": (334.7, 5477.7), "L8": (333.3, 6078.1),
        "R1": (1587.8, 1570.1), "R2": (1589.8, 2171.6), "R3": (1589.0, 2768.4), "R4": (1590.6, 3371.3),
        "R5": (1596.9, 4275.5), "R6": (1592.3, 4872.3), "R7": (1591.4, 5473.5), "R8": (1591.6, 6074.7),
        "C1": (1002.3, 2316.5), "B1": (700.2, 3042.9), "B2": (1006.7, 3045.1), "B3": (1307.6, 3046.3)}
SITE_OFS = (3, 5)
TAIL_DIEL_PX = (660.8, 1273.6, 5890, 12241)
STIFF_TOP_PX = 12219
STICKER_PX = (734, 1202, 6405, 7385)
PATCH_Y = (1350, 5880)

# taramadaki kesik (yirtik) ust kenar: px (x, ilk film y'si + golge bandi 18 px)
TORN_PX = [(105, 178), (150, 177), (210, 184), (240, 208), (270, 243), (300, 276), (330, 336), (360, 386),
           (390, 407), (420, 430), (450, 442), (480, 467), (510, 484), (540, 497), (570, 510), (600, 522),
           (630, 531), (660, 543), (690, 562), (720, 584), (750, 602), (780, 619), (810, 641), (840, 663),
           (870, 674), (900, 676), (930, 687), (975, 718), (1005, 737), (1035, 753), (1065, 765), (1095, 784),
           (1125, 830), (1155, 840), (1185, 862), (1215, 884), (1245, 905), (1275, 929), (1305, 951), (1335, 974),
           (1365, 992), (1395, 1008), (1425, 1026), (1455, 1041), (1485, 1059), (1515, 1073), (1560, 1076),
           (1590, 1110), (1620, 1178), (1650, 1230), (1680, 1284), (1710, 1307), (1740, 1319), (1770, 1336),
           (1800, 1351), (1830, 1378)]


def mm(px, py):
    return (round((px - SCAN["px0"]) / S + XC, 3), round((py - SCAN["py0"]) / S, 3))


def to_mm_geom(g):
    g = affinity.translate(g, -SCAN["px0"], -SCAN["py0"])
    g = affinity.scale(g, 1 / S, 1 / S, origin=(0, 0))
    return affinity.translate(g, XC, 0)


def build_outline():
    nl, nr = XC - TAIL_NECK / 2, XC + TAIL_NECK / 2
    tl, tr = XC - TAIL_W / 2, XC + TAIL_W / 2
    sc = SLOT_TOP + SLOT_W / 2
    return [
        ("M", R, 0), ("L", W - R, 0), ("A", R, 1, W, R), ("L", W, H - R), ("A", R, 1, W - R, H),
        ("L", nr + SLOT_W, H), ("L", nr + SLOT_W, sc), ("A", SLOT_W / 2, 0, nr, sc),
        ("L", nr, TAPER0), ("L", tr, TAPER1), ("L", tr, TAIL_END), ("L", tl, TAIL_END), ("L", tl, TAPER1),
        ("L", nl, TAPER0), ("L", nl, sc), ("A", SLOT_W / 2, 0, nl - SLOT_W, sc),
        ("L", nl - SLOT_W, H), ("L", R, H), ("A", R, 1, 0, H - R), ("L", 0, R), ("A", R, 1, R, 0), ("Z",),
    ]


def fix_horizontals(pts, L, T):
    """Yatay segmentlerin y'sini golge-bagimsiz alt kenardan yeniden hesaplar (golge kopyasi ustte)."""
    pts = [list(p) for p in pts]
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        if abs(y1 - y0) > 0.5 or abs(x1 - x0) < 60:
            continue
        a, b = sorted((x0, x1))
        edges = []
        for x in np.arange(a + 0.15 * (b - a), b - 0.15 * (b - a), 8):
            xi, yi = int(x), int(round(y0))
            if T[yi - 30:yi + 31, xi - 2:xi + 3].mean() > 30:
                continue
            col = L[yi - 30:yi + 40, xi - 2:xi + 3].mean(1)
            lo, hi = col.min(), np.percentile(col, 95)
            thr = (lo + hi) / 2
            j = int(np.argmin(col))
            while j < len(col) - 1 and col[j] < thr:
                j += 1
            edges.append(yi - 30 + j)
        if len(edges) >= 3:
            y = float(np.median(edges)) - TRACE_W * S / 2
            if abs(y - y0) < 14:
                dy = round(y, 1) - y0
                pts[i][1] = pts[i + 1][1] = round(y, 1)
                # komşu kısa pah (< 60 px, çapraz) bir dikeye bağlanıyorsa pahın dikey tarafındaki ucunu da dy kaydır:
                # pah açısı korunur, yatay düzeltmesi sivri köşe üretmez
                for j, k in ((i - 1, i - 2), (i + 2, i + 3)):
                    if not (0 <= k < len(pts)):
                        continue
                    e = pts[i] if j < i else pts[i + 1]
                    kisa = abs(pts[j][0] - e[0]) < 60 and abs(pts[j][0] - e[0]) > 0.5
                    if kisa and abs(pts[k][0] - pts[j][0]) < 0.5:
                        pts[j][1] = round(pts[j][1] + dy, 1)
    return [tuple(p) for p in pts]


def patch_polys():
    teal = np.load("work/p3/m_teal.npy")
    und = np.load("work/p3/m_under.npy")
    m = (teal | und).astype(np.uint8)
    m[:PATCH_Y[0]] = 0
    m[PATCH_Y[1]:] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((1, 31), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((31, 1), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((11, 11), np.uint8))
    out = []
    for p in mask_to_polys(m.astype(bool), eps=4, snap_tol=15, min_area=2500):
        if p.area / p.envelope.area > 0.9:
            p = p.envelope
        out.append(p)
    return out


def choose_bridges(traces_px, patches_px):
    """Her izin yamalar icindeki parcalarini renkten ust (kopru) / alt olarak siniflandirir.
    Ust gumus yama uzerinde gri (G-R < 25), alt gumus koyu turkuaz (G-R > 90, R < 95)."""
    im = cv2.imread("work/p3/p3_deskew.png").astype(np.int16)
    Tm = im[:, :, 1] - im[:, :, 2]
    Rm = im[:, :, 2]
    from shapely.prepared import prep
    U = unary_union(patches_px).buffer(-6)
    lines = {n: LineString(p) for n, p in traces_px}
    res = []
    for name, pts in traces_px:
        inter = LineString(pts).intersection(U)
        pieces = [inter] if inter.geom_type == "LineString" else list(getattr(inter, "geoms", []))
        # kesişen diğer hatların üstündeki pikseller örneklenmez (köprü grisi yatayı "üst" göstermesin)
        others = prep(unary_union([g for n, g in lines.items() if n != name]).buffer(16))
        for piece in pieces:
            if piece.is_empty or piece.length < 15:
                continue
            nt = nu = 0
            for d in np.arange(0, piece.length, 3):
                q = piece.interpolate(d)
                if others.contains(q):
                    continue
                x, y = int(round(q.x)), int(round(q.y))
                t, r = Tm[y - 3:y + 4, x - 3:x + 4], Rm[y - 3:y + 4, x - 3:x + 4]
                nt += int((t < 25).sum())
                nu += int(((t > 90) & (r < 95)).sum())
            res.append(dict(name=name, top=bool(nt > nu), nt=nt, nu=nu,
                            pts=[(round(a, 1), round(b, 1)) for a, b in piece.coords]))
    return res


def build():
    D = fv.Design(name="P3", title="P3 - Uzun LED devresi (20 LED, 11 pin 1.0 mm)", width=W, height=TAIL_END)
    D.scan = SCAN
    D.outline = build_outline()
    D.check.append(("Taramadaki_kesik_ust_kenar", [mm(*p) for p in TORN_PX]))

    # --- hatlar ---
    L = np.load("work/p3/_L.npy", mmap_mode="r") if os.path.exists("work/p3/_L.npy") else None
    if L is None:
        im = cv2.imread("work/p3/p3_deskew.png").astype(np.float32)
        L, T = im.mean(2), im[:, :, 1] - im[:, :, 2]
    else:
        T = np.load("work/p3/_T.npy", mmap_mode="r")
    ref = refine_all(pr.ROUTES, route_mask("p3"))
    traces_px = []
    for r in pr.ROUTES:
        p = fix_horizontals([tuple(q) for q in ref[r["name"]]["pts"]], L, T)
        traces_px.append((r["name"], p))
        D.traces.append((r["name"], [mm(*q) for q in p], TRACE_W))
        if r.get("flag"):
            D.check.append((r["name"], [mm(*q) for q in p]))
    ty = mm(0, pr.TAIL_Y)[1]
    for i, x in enumerate(pr.TX):
        D.traces.append((f"Kontak_{i + 1:02d}", [(mm(x, 0)[0], ty), (mm(x, 0)[0], TAIL_END)], TAIL_TRACE_W))

    # --- LED ---
    for n, (cx, cy) in CHIP.items():
        sx, sy = mm(cx + SITE_OFS[0], cy + SITE_OFS[1])
        g = LED_GAP / 2
        D.silver_rects.append((f"LED_{n}_ped_ust", sx - LED_PAD_W / 2, sy - g - LED_PAD_H, LED_PAD_W, LED_PAD_H))
        D.silver_rects.append((f"LED_{n}_ped_alt", sx - LED_PAD_W / 2, sy + g, LED_PAD_W, LED_PAD_H))
        D.leds.append((f"LED_{n}", sx, sy, *LED_BODY))
        pdx, pdy = PLUS[n[0]]
        px, py = mm(cx + pdx, cy + pdy)
        h = PLUS_L / 2
        D.marks.append((f"LED_{n}_arti_y", [(px - h, py), (px + h, py)], PLUS_W))
        D.marks.append((f"LED_{n}_arti_d", [(px, py - h), (px, py + h)], PLUS_W))

    # --- dielektrik yamalari + kopruler ---
    patches_px = patch_polys()
    D.diel_polys = [to_mm_geom(p) for p in patches_px]
    sel = choose_bridges(traces_px, patches_px)
    for s in sel:  # x1418 / y3200 yamasi: renk kararsiz (ikisi de alt); Y_hat yamasindaki gibi yatay ustten
        if s["name"] == "X_R3R4" and s["pts"][0][0] > 1300:
            s["top"] = True
        # poz4 ust parcasi (Z) y5090-5140 yama altinda Q yatayina baglaniyor (renk profili: koyu turkuaz)
        if s["name"] == "Z_C1" and s["pts"][0][1] > 4950 and abs(s["pts"][0][0] - 918) < 5:
            s["top"] = False
        if s["name"] == "L6_alt" and s["pts"][0][0] > 800:  # L6 alti yama icinde poz4 ust parcasiyla birlesir
            s["top"] = False
    D.kopru_kurali = onar.kopru_uc_kurali(sel, traces_px)  # T-bağlantısı yama içinde: alt baskı (hedef=True P3te pin 4-10 birleştiriyor: birleşik çift yama)
    json.dump(sel, open("work/p3/bridges.json", "w"))
    Um = unary_union(D.diel_polys)
    for j, s in enumerate(sel, 1):
        if not s["top"]:
            continue
        piece = to_mm_geom(LineString(s["pts"]))
        tr = next(t for t in D.traces if t[0] == s["name"])
        seg = LineString(tr[1]).intersection(piece.buffer(BRIDGE_OVL + 0.3))
        for q in [seg] if seg.geom_type == "LineString" else list(seg.geoms):
            if q.length > 0.2:
                D.bridges.append((f"Kopru_{j:02d}_{s['name']}", list(q.coords), TRACE_W))
        D.bridge_cut.append((s["name"], piece.buffer(TRACE_W).intersection(Um.buffer(-0.05))))

    # --- kuyruk ---
    x0, x1, y0, y1 = TAIL_DIEL_PX
    a, b = mm(x0, y0), mm(x1, y1)
    D.diel_rects.append((a[0], a[1], b[0] - a[0], b[1] - a[1]))
    st = mm(0, STIFF_TOP_PX)[1]
    D.stiff_rects.append((XC - TAIL_W / 2, st, TAIL_W, TAIL_END - st))
    sa, sb = mm(STICKER_PX[0], STICKER_PX[2]), mm(STICKER_PX[1], STICKER_PX[3])
    D.stickers.append((sa[0], sa[1], sb[0] - sa[0], sb[1] - sa[1], 0.8))
    D.onarimlar = onar.uc_kenetle(D)  # kısa kalan uçları pede/hatta uzat (ağ-güvenli)
    return D


RAPOR = dict(
    ozet="20 LED'li arka aydınlatma katmanı (0402 LED). İki gümüş baskı (alt hatlar + dielektrik üstü köprüler), "
         "dielektrik köprü yamaları, 11 pinlik 1.0 mm ZIF kuyruğu; LED'ler matris bağlı (her pin birden çok LED'i "
         "sürüyor). P4 tuş katmanıyla üst üste biner: LED'ler P4'ün 20 oval penceresinin altındadır.",
    olculer=[
        ("Baş (genişlik × yükseklik)", f"{W} × {H} mm", f"köşe R{R}; sağ üst köşe numunede kesik"),
        ("Toplam boy", f"{TAIL_END} mm", ""),
        ("Kuyruk genişliği", f"{TAIL_NECK} → {TAIL_W} mm", f"y={TAPER0}–{TAPER1} arasında genişler"),
        ("Yarık", f"{SLOT_W} mm", f"üst ucu y={SLOT_TOP}"),
        ("Konnektör", "11 poz × 1.0 mm", f"kontak {TAIL_TRACE_W} mm, dummy yok"),
        ("Hat genişliği", f"{TRACE_W} mm", ""),
        ("LED pedi", f"{LED_PAD_W} × {LED_PAD_H} mm", f"boşluk {LED_GAP} mm, LED gövdesi {LED_BODY[0]} × {LED_BODY[1]} mm"),
        ("Polarite işareti", f"+ {PLUS_L} mm, çizgi {PLUS_W} mm", "gümüş baskı, alt ped yanında"),
        ("Köprü bindirmesi", f"{BRIDGE_OVL} mm", "yama kenarından dışarı"),
    ],
    varsayimlar=[
        "Ölçek 47.17 px/mm (setin ortak kalibrasyonu); P3 kuyruğunda adım 0.998 mm ölçüldü.",
        "Baş sağ üst bölgesi numunede çapraz kesik/yırtık; kesim konturu P4 gibi dikdörtgen çizildi, taramadaki "
        "kenar Kontrol katmanında ayrıca verildi.",
        "Film sağ yarıda camdan kalkık (bulanık): hat maskesi doku yerine koyuluktan (m_dark) çıkarıldı; yatay "
        "hatların konumu gölge kopyasından etkilenmeyen alt kenardan alındı.",
        "Köprülerde üst/alt seçimi yama içinde renkten yapıldı (gri = üst baskı, koyu turkuaz = alt baskı).",
        "LED ped/gövde ölçüleri P1 şablonu: kaplama damlaları ped kenarlarını örtüyor.",
        "Kesim deseni baskıya göre ~0.1° dönük; çizimde ideal hizalı alındı.",
    ],
    kontrol_listesi=[
        "Kuyruk pin eşlemesi (aşağıdaki tablo) — sol yelpaze (pin 1-3) ve sol alt döngü bulanık bölgede yorumlandı",
        "Pin 1 ve pin 8 çizimde aynı ağda (R1 ortak = Y): V465 hattının alt ucu sol alt döngüye gerçekten bağlı mı?",
        "L5 ve R5 alt pedleri: y≈4487 px yaması altında birbirine bağlı, hiçbir pine ulaşmıyor görünüyor (multimetre)",
        "L1 alt hattının (X) sol ucu ile sol dış ortak hat arasında boşluk var mı? (birleşikse L1 kısa devre olur)",
        "B2/Z çapraz yaması (y≈3410-3560 px): Z → pin 4, B2 alt → pin 6 olarak yorumlandı (tersi de mümkün)",
        "R8 üst pedi → sağ dış alt hat → pin 4 ve R8 alt pedi → noktalı hat → pin 11 bağlantıları",
        "L8 üst pedi → pin 2, L8 alt pedi → sol alt döngü (ortak) bağlantıları",
    ],
    pin_eslemesi=[("1", "R1 ortak: üst yatay + sol dış hat (sol alt döngü üzerinden); çizimde pin 8 ile aynı ağ"),
                  ("2", "L8 üst pedi"), ("3", "Na: L3–L7 üst pedleri (sol iç hat)"),
                  ("4", "Z + Q: C1/B1/B2/B3 üst, R8 üst, L6 alt"), ("5", "Nb: R3, R5, R6, R7 üst pedleri (sağ iç hat)"),
                  ("6", "B2 alt"), ("7", "X: L1 alt, L2 üst, L3 alt, R3 alt, R4 üst, B3 alt"),
                  ("8", "Y: L2/L4/R4/B1 alt + V465 (+ R1 ortak)"), ("9", "R1 alt + C1 alt"), ("10", "R2 alt + R6 alt"),
                  ("11", "L7/R7/R8 alt")],
)


def main():
    import subprocess
    subprocess.run([sys.executable, ".devin/skills/fpc-vektor/scripts/fpc.py", "build", "p3"], check=True)


if __name__ == "__main__":
    main()
