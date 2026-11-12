"""P1 - kisa LED devresi (12 LED, 2 gumus baski + dielektrik kopru yamalari) tasarimi.

Tum olculer mm. Orijin: kart bas kismi sol ust kosesi, y asagi.
Hat rotalari tools/p1_routes.py (tarama px) -> refine -> mm. Dielektrik yamalari tarama
maskesinden otomatik (0/45/90 oturtmali) cikarilir; kopru (ust gumus) secimi her kesisimde
ust/alt gumus orneklemesiyle yapilir.

Kullanim: python .devin/skills/fpc-vektor/scripts/fpc.py build p1
"""
import json
import os
import sys

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import LineString, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.abspath(".devin/skills/fpc-vektor/scripts"))
import cfg  # noqa: E402,F401
import fpcvec as fv  # noqa: E402
import p1_routes as pr  # noqa: E402
from polyvec import mask_to_polys  # noqa: E402
from routes_view import refine_all  # noqa: E402

W, H, R = 36.5, 87.1, 1.0
XC = W / 2
TAIL_W, TAIL_END = 12.0, 170.9
SLOT_W, SLOT_TOP = 2.1, 69.9
TRACE_W, TAIL_TRACE_W = 0.5, 0.6
LED_PAD_W, LED_PAD_H, LED_GAP = 1.65, 1.6, 0.85
LED_BODY = (0.5, 1.0)
PLUS_L, PLUS_W = 0.8, 0.15
BRIDGE_OVL = 0.4

SCAN = dict(s=47.17, px0=983.2, py0=175.0, mm0=(XC, 0.0))
S = SCAN["s"]

LEDS = {  # ad: yesil cip merkezi (px), arti isareti ofseti (px)
    "LED_L1": ((347, 1748), (59, 119)), "LED_L2": ((353, 2354), (59, 119)),
    "LED_L3": ((348, 2959), (59, 119)), "LED_L4": ((351, 3545), (59, 119)),
    "LED_R1": ((1610, 1755), (-47, 113)), "LED_R2": ((1612, 2356), (-47, 113)),
    "LED_R3": ((1610, 2950), (-47, 113)), "LED_R4": ((1611, 3553), (-47, 113)),
    "LED_C1": ((1021, 2430), (-47, 113)), "LED_B1": ((720, 3163), (-47, 110)),
    "LED_B2": ((1022, 3161), (-47, 110)), "LED_B3": ((1320, 3167), (-47, 110)),
}
TAIL_DIEL_PX = (688, 1238, 3527, 7900)
STIFF_TOP_PX, DUMMY_TOP_PX = 7925, 7785
STICKER_PX = (4249, 5330)


def mm(px, py):
    return (round((px - SCAN["px0"]) / S + XC, 3), round((py - SCAN["py0"]) / S, 3))


def to_mm_geom(g):
    g = affinity.translate(g, -SCAN["px0"], -SCAN["py0"])
    g = affinity.scale(g, 1 / S, 1 / S, origin=(0, 0))
    return affinity.translate(g, XC, 0)


def build_outline():
    tl, tr = XC - TAIL_W / 2, XC + TAIL_W / 2
    sc = SLOT_TOP + SLOT_W / 2
    return [
        ("M", R, 0), ("L", W - R, 0), ("A", R, 1, W, R), ("L", W, H - R), ("A", R, 1, W - R, H),
        ("L", tr + SLOT_W, H), ("L", tr + SLOT_W, sc), ("A", SLOT_W / 2, 0, tr, sc),
        ("L", tr, TAIL_END), ("L", tl, TAIL_END), ("L", tl, sc), ("A", SLOT_W / 2, 0, tl - SLOT_W, sc),
        ("L", tl - SLOT_W, H), ("L", R, H), ("A", R, 1, 0, H - R), ("L", 0, R), ("A", R, 1, R, 0), ("Z",),
    ]


def patch_polys():
    teal = np.load("work/p1/m_teal.npy")
    und = np.load("work/p1/m_under.npy")
    m = (teal | und).astype(np.uint8)
    m[:1500] = 0
    m[3520:] = 0
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
    """Her izin yamalar icindeki surekli parcalarini ust (kopru) / alt olarak siniflandirir."""
    top = np.load("work/p1/m_top.npy")
    und = np.load("work/p1/m_under.npy")
    U = unary_union(patches_px).buffer(-6)
    res = []
    for name, pts in traces_px:
        inter = LineString(pts).intersection(U)
        pieces = [inter] if inter.geom_type == "LineString" else list(getattr(inter, "geoms", []))
        for piece in pieces:
            if piece.is_empty or piece.length < 15:
                continue
            nt = nu = 0
            for d in np.arange(0, piece.length, 3):
                q = piece.interpolate(d)
                x, y = int(round(q.x)), int(round(q.y))
                nt += top[y - 3:y + 4, x - 3:x + 4].sum()
                nu += und[y - 3:y + 4, x - 3:x + 4].sum()
            res.append(dict(name=name, top=bool(nt > nu), nt=int(nt), nu=int(nu),
                            pts=[(round(a, 1), round(b, 1)) for a, b in piece.coords]))
    return res


def build():
    D = fv.Design(name="P1", title="P1 - Kısa LED devresi (12 LED, 11 pin 1.0 mm)", width=W, height=TAIL_END)
    D.scan = SCAN
    D.outline = build_outline()

    # --- hatlar ---
    mask = np.load("work/p1/m_top.npy") | np.load("work/p1/m_under.npy")
    ref = refine_all(pr.ROUTES, mask)
    traces_px = []
    for r in pr.ROUTES:
        p = [tuple(q) for q in ref[r["name"]]["pts"]]
        traces_px.append((r["name"], p))
        D.traces.append((r["name"], [mm(*q) for q in p], TRACE_W))
        if r.get("flag"):
            D.check.append((r["name"], [mm(*q) for q in p]))
    ty = mm(0, pr.TAIL_Y)[1]
    for i, x in enumerate(pr.TX):
        top_y = mm(0, DUMMY_TOP_PX)[1] if i in (1, 3, 10) else ty
        nm = f"Kontak_{i + 1:02d}" + ("_dummy" if i in (1, 3, 10) else "")
        D.traces.append((nm, [(mm(x, 0)[0], top_y), (mm(x, 0)[0], TAIL_END)], TAIL_TRACE_W))

    # --- LED ---
    for n, ((cx, cy), (pdx, pdy)) in LEDS.items():
        sx, sy = mm(cx + 4, cy + 8)
        g = LED_GAP / 2
        D.silver_rects.append((f"{n}_ped_ust", sx - LED_PAD_W / 2, sy - g - LED_PAD_H, LED_PAD_W, LED_PAD_H))
        D.silver_rects.append((f"{n}_ped_alt", sx - LED_PAD_W / 2, sy + g, LED_PAD_W, LED_PAD_H))
        D.leds.append((n, sx, sy, *LED_BODY))
        px, py = mm(cx + pdx, cy + pdy)
        h = PLUS_L / 2
        D.marks.append((f"{n}_arti_y", [(px - h, py), (px + h, py)], PLUS_W))
        D.marks.append((f"{n}_arti_d", [(px, py - h), (px, py + h)], PLUS_W))

    # --- dielektrik yamalari + kopruler ---
    patches_px = patch_polys()
    D.diel_polys = [to_mm_geom(p) for p in patches_px]
    sel = choose_bridges(traces_px, patches_px)
    for s in sel:  # B2/B3 alt yamasi: yatay h3290 alttan gecer (dikeyler kopru); orneklem kararsiz
        if s["name"] == "L1_alt" and s["pts"][0][1] > 3250:
            s["top"] = False
    json.dump(sel, open("work/p1/bridges.json", "w"))
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
    s0, s1 = mm(0, STICKER_PX[0])[1], mm(0, STICKER_PX[1])[1]
    D.stickers.append((XC - TAIL_W / 2, s0, TAIL_W, s1 - s0, 0.8))
    return D


RAPOR = dict(
    ozet="12 LED'li arka aydınlatma katmanı (0402 LED, iletken yapıştırıcıyla montaj). İki gümüş baskı "
         "(alt hatlar + dielektrik üstü köprüler), dielektrik köprü yamaları, 11 pinlik 1.0 mm ZIF kuyruğu. "
         "LED konumları P2'nin oval pencereleriyle 0.1 mm içinde örtüşür.",
    olculer=[
        ("Baş (genişlik × yükseklik)", f"{W} × {H} mm", f"köşe R{R}"),
        ("Toplam boy", f"{TAIL_END} mm", ""),
        ("Kuyruk genişliği", f"{TAIL_W} mm", f"yarık {SLOT_W} mm, üst ucu y={SLOT_TOP}"),
        ("Konnektör", "11 poz × 1.0 mm", f"kontak {TAIL_TRACE_W} mm, 2/4/11 dummy"),
        ("Hat genişliği", f"{TRACE_W} mm", ""),
        ("LED pedi", f"{LED_PAD_W} × {LED_PAD_H} mm", f"boşluk {LED_GAP} mm, LED gövdesi {LED_BODY[0]} × {LED_BODY[1]} mm"),
        ("Polarite işareti", f"+ {PLUS_L} mm, çizgi {PLUS_W} mm", "gümüş baskı"),
        ("Köprü bindirmesi", f"{BRIDGE_OVL} mm", "yama kenarından dışarı"),
    ],
    varsayimlar=[
        "Ölçek 47.17 px/mm (P2 ile aynı tarama).",
        "Kesim deseni konnektör eksenine göre simetrik çizildi (taramada kuyruk ~0.26° dönük).",
        "Köprülerde üst/alt seçimi her kesişimde üst-gümüş / alt-gümüş maske örneklemesiyle yapıldı; "
        "B2/B3 alt yamasındaki yatay hat elle 'alt' ayarlandı.",
        "LED ped/gövde ölçüleri şablon: kaplama damlaları ped kenarlarını örtüyor.",
        "Konnektöre giden hatların pin sırası (leke altında) düzlemsel sıra + görülen 45° çaprazlarla belirlendi.",
    ],
    kontrol_listesi=[
        "Kuyruk pin eşlemesi (aşağıdaki tablo) - leke altında yorumlandı",
        "R1 sol-alt dönüşü ve x≈11 mm dikeyiyle pin 1 bağlantısı",
        "B1/B2/B3 LED ped bağlantıları (orta-alt leke bölgesi)",
        "R3 üst pedi → T3, R4 üst pedi → T3 alt ucu bağlantıları",
        "y=2818 (V578→V916) ve y=3317 hatlarının uç bağlantıları",
    ],
    pin_eslemesi=[("1", "R1 ortak (anot)"), ("2", "dummy"), ("3", "L3/L4 üst"), ("4", "dummy"),
                  ("5", "H3317 hattı"), ("6", "V916 / H2818"), ("7", "L2 alt düğümü (L2→L4)"),
                  ("8", "R1 LED katodu (+C1)"), ("9", "L1/L3 katodu (+B2/B3)"), ("10", "R2/R3 katodu"), ("11", "dummy")],
)


def main():
    import subprocess
    subprocess.run([sys.executable, ".devin/skills/fpc-vektor/scripts/fpc.py", "build", "p1"], check=True)


if __name__ == "__main__":
    main()
