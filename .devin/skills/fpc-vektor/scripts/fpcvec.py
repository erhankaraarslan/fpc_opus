"""FPC / membran devre vektör çizim kütüphanesi.

Tasarım mm cinsinden tanımlanır (orijin: kartın sol üst köşesi, y aşağı doğru).
Çıktılar:
  * düzenlenebilir SVG  : hatlar kalınlıklı çizgi (stroke), pedler dikdörtgen, ovaller köşesi yuvarlatılmış dikdörtgen
  * üretim SVG          : her katman tek parça kapalı dolgu (compound path)
  * kontrol SVG         : üretim katmanları + altta hizalanmış tarama görüntüsü
  * vektör PDF          : üretim katmanları, PDF katmanları (OCG) ile
"""
from __future__ import annotations

import base64
import math
from dataclasses import dataclass, field

import cv2
import numpy as np
import pymupdf
from shapely import affinity
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, box
from shapely.ops import unary_union

MITRE = dict(cap_style="flat", join_style="mitre", mitre_limit=5.0)

COL = {
    "Kesim": "#E3001B",
    "Gumus": "#7F7F7F",
    "Dielektrik": "#2BB5A0",
    "Takviye": "#C9B37E",
    "Bilgi": "#000000",
    "Kopru": "#3F3F3F",
    "LED": "#F2F2F2",
    "Etiket": "#7A5C00",
    "Kontrol": "#FF00FF",
}
DIEL_OPACITY = 0.55
CUT_W = 0.1


@dataclass
class Design:
    name: str
    title: str
    width: float
    height: float
    margin: float = 5.0
    # Kesim: dış kontur [('M',x,y) | ('L',x,y) | ('A',r,sweep,x,y) | ('Z',)] ve stadium delikler
    outline: list = field(default_factory=list)
    holes: list = field(default_factory=list)          # (cx, cy, w, h)
    # Gümüş
    traces: list = field(default_factory=list)         # (ad, [(x,y)...], genişlik)
    silver_rects: list = field(default_factory=list)   # (grup, x, y, w, h)
    # Dielektrik
    diel_lines: list = field(default_factory=list)     # ([(x,y)...], genişlik)
    diel_rects: list = field(default_factory=list)     # (x, y, w, h)
    diel_rings: list = field(default_factory=list)     # (x, y, w, h, çizgi)  -> çizgi merkezi kutusu
    diel_polys: list = field(default_factory=list)     # shapely Polygon (mm) - yama vb.
    # İkinci gümüş baskı (dielektrik üstünden geçen köprüler)
    bridges: list = field(default_factory=list)        # (ad, [(x,y)...], genişlik)
    bridge_cut: list = field(default_factory=list)     # (iz_adı, shapely geom) alt gümüşten çıkarılacak bölge
    # LED / işaretler
    leds: list = field(default_factory=list)           # (ad, cx, cy, w, h)
    marks: list = field(default_factory=list)          # (ad, [(x,y)...], genişlik) gümüş işaret çizgileri
    # Etiket (yapıştırma)
    stickers: list = field(default_factory=list)       # (x, y, w, h, r)
    # Kontrol (belirsiz) rotalar
    check: list = field(default_factory=list)          # (ad, [(x,y)...])
    # Takviye (arka yüz)
    stiff_rects: list = field(default_factory=list)    # (x, y, w, h)
    # Ağ kontrolü için isteğe bağlı açık tanımlar (yoksa adlandırma kuralından çıkarılır, bkz. netlist.py)
    pins: list = field(default_factory=list)           # (ad, shapely geom mm, dummy mu)
    devices: list = field(default_factory=list)        # (ad, [(uç_adı, shapely geom mm), ...])
    # Tarama hizalama: deskew px -> mm   (mm = (px - px0) / s + mm0)
    scan: dict | None = None

    # ------------------------------------------------------------ geometri
    def outline_poly(self, n=24) -> Polygon:
        pts, cur = [], None
        for seg in self.outline:
            if seg[0] in "ML":
                cur = (seg[1], seg[2])
                pts.append(cur)
            elif seg[0] == "A":
                _, r, sweep, x, y = seg
                pts.extend(arc_points(cur, (x, y), r, sweep, n)[1:])
                cur = (x, y)
        return Polygon(pts)

    def holes_polys(self):
        return [stadium_poly(*h) for h in self.holes]

    def window_boxes(self):
        return [box(x + lw / 2, y + lw / 2, x + w - lw / 2, y + h - lw / 2) for x, y, w, h, lw in self.diel_rings]

    def ring_outer_boxes(self):
        return [box(x - lw / 2, y - lw / 2, x + w + lw / 2, y + h + lw / 2) for x, y, w, h, lw in self.diel_rings]

    def silver_geom(self):
        cut = {}
        for n, g in self.bridge_cut:
            cut.setdefault(n, []).append(g)
        g = []
        for n, p, w in self.traces:
            t = LineString(p).buffer(w / 2, **MITRE)
            if n in cut:
                t = t.difference(unary_union(cut[n]))
            g.append(t)
        g += [box(x, y, x + w, y + h) for _, x, y, w, h in self.silver_rects]
        g += [LineString(p).buffer(w / 2, cap_style="flat") for _, p, w in self.marks]
        return unary_union(g)

    def silver_elements(self):
        """Alt gümüş elemanları: [(ad, tür, Polygon|MultiPolygon mm)]. Tür: hat | kontak | led_ped | tus_ped |
        dikdortgen | isaret. Hatlarda köprü kesimleri çıkarılmıştır; dikdörtgenler grup adına göre birleşiktir."""
        cut = {}
        for n, g in self.bridge_cut:
            cut.setdefault(n, []).append(g)
        out = []
        for n, p, w in self.traces:
            t = LineString(p).buffer(w / 2, **MITRE)
            if n in cut:
                t = t.difference(unary_union(cut[n]))
            out.append((n, "kontak" if n.startswith("Kontak_") else "hat", t))
        groups = {}
        for g, x, y, w, h in self.silver_rects:
            groups.setdefault(g, []).append(box(x, y, x + w, y + h))
        for g, rs in groups.items():
            kind = "led_ped" if g.startswith("LED_") else "tus_ped" if g.startswith("Ped_") else "dikdortgen"
            out.append((g, kind, unary_union(rs)))
        out += [(n, "isaret", LineString(p).buffer(w / 2, cap_style="flat")) for n, p, w in self.marks]
        return out

    def bridge_elements(self):
        return [(n, "kopru", LineString(p).buffer(w / 2, **MITRE)) for n, p, w in self.bridges]

    def bridge_geom(self):
        return unary_union([LineString(p).buffer(w / 2, **MITRE) for _, p, w in self.bridges])

    def led_geom(self):
        return unary_union([box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2) for _, cx, cy, w, h in self.leds])

    def diel_area_geom(self, clip=True):
        """Dielektrik dolgu alanları, kart konturu ile kırpılmış (clip=False: kırpılmamış)."""
        g = unary_union([box(x, y, x + w, y + h) for x, y, w, h in self.diel_rects] + list(self.diel_polys))
        return g.intersection(self.outline_poly()) if clip else g

    def diel_geom(self, clip=True):
        g = [LineString(p).buffer(w / 2, **MITRE) for p, w in self.diel_lines]
        g += [self.diel_area_geom(clip)]
        g += [o.difference(i) for o, i in zip(self.ring_outer_boxes(), self.window_boxes())]
        g = unary_union(g).difference(unary_union(self.window_boxes()))
        return g.intersection(self.outline_poly()) if clip else g

    def diel_lines_clipped(self):
        """Düzenlenebilir sürüm için: çizgileri ped pencerelerinin dış halkasında kırp."""
        cut = unary_union(self.ring_outer_boxes())
        out = []
        for p, w in self.diel_lines:
            r = LineString(p).difference(cut)
            parts = [r] if isinstance(r, LineString) else list(getattr(r, "geoms", []))
            out += [(list(q.coords), w) for q in parts if not q.is_empty and q.length > 1e-6]
        return out

    def stiff_geom(self):
        return unary_union([box(x, y, x + w, y + h) for x, y, w, h in self.stiff_rects])


# ---------------------------------------------------------------- yardımcılar
def arc_points(p0, p1, r, sweep, n=24):
    (x0, y0), (x1, y1) = p0, p1
    cx, cy = arc_center(p0, p1, r, sweep)
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    da = a1 - a0
    if sweep:
        while da <= 0:
            da += 2 * math.pi
    else:
        while da >= 0:
            da -= 2 * math.pi
    return [(cx + r * math.cos(a0 + da * t / n), cy + r * math.sin(a0 + da * t / n)) for t in range(n + 1)]


def arc_center(p0, p1, r, sweep):
    """SVG küçük yay (large-arc=0) merkezini döndürür (y aşağı koordinat)."""
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy)
    h = math.sqrt(max(r * r - (d / 2) ** 2, 0))
    ux, uy = -dy / d, dx / d
    # sweep=1 -> saat yönü (ekranda); merkez hareket yönünün sağında
    s = 1 if sweep else -1
    return mx + s * h * ux, my + s * h * uy


def stadium_poly(cx, cy, w, h, n=24):
    r = w / 2
    return LineString([(cx, cy - h / 2 + r), (cx, cy + h / 2 - r)]).buffer(r, quad_segs=n)


def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pts_attr(pts, ox, oy):
    return " ".join(f"{f(x + ox)},{f(y + oy)}" for x, y in pts)


def outline_d(segs, ox, oy):
    d = []
    for s in segs:
        if s[0] in "ML":
            d.append(f"{s[0]}{f(s[1] + ox)},{f(s[2] + oy)}")
        elif s[0] == "A":
            _, r, sw, x, y = s
            d.append(f"A{f(r)},{f(r)} 0 0 {sw} {f(x + ox)},{f(y + oy)}")
        elif s[0] == "Z":
            d.append("Z")
    return " ".join(d)


def poly_d(geom, ox, oy):
    polys = [geom] if isinstance(geom, Polygon) else list(getattr(geom, "geoms", []))
    d = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            c = list(ring.coords)[:-1]
            d.append("M" + " L".join(f"{f(x + ox)},{f(y + oy)}" for x, y in c) + " Z")
    return " ".join(d)


def layer_open(lid, label):
    return f'<g id="{lid}" inkscape:groupmode="layer" inkscape:label="{label}">'


def svg_head(D: Design):
    W, H = D.width + 2 * D.margin, D.height + 2 * D.margin
    return [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'width="{f(W)}mm" height="{f(H)}mm" viewBox="0 0 {f(W)} {f(H)}" version="1.1">',
        f"<title>{D.title}</title>",
    ]


def cut_layer(D: Design, ox, oy):
    st = f'fill="none" stroke="{COL["Kesim"]}" stroke-width="{CUT_W}"'
    out = [layer_open("Kesim", "Kesim (dis kontur + pencereler)")]
    out.append(f'<path id="Kesim_Dis_Kontur" {st} d="{outline_d(D.outline, ox, oy)}"/>')
    out.append('<g id="Kesim_Oval_Pencereler">')
    for i, (cx, cy, w, h) in enumerate(D.holes, 1):
        out.append(
            f'<rect id="Oval_{i:02d}" {st} x="{f(cx - w / 2 + ox)}" y="{f(cy - h / 2 + oy)}" '
            f'width="{f(w)}" height="{f(h)}" rx="{f(w / 2)}" ry="{f(w / 2)}"/>'
        )
    out += ["</g>", "</g>"]
    return out


def stiff_layer(D: Design, ox, oy, editable):
    if not D.stiff_rects:
        return []
    out = [layer_open("Takviye", "Takviye (arka yuz, ZIF)")]
    if editable:
        for i, (x, y, w, h) in enumerate(D.stiff_rects, 1):
            out.append(f'<rect id="Takviye_{i}" fill="{COL["Takviye"]}" x="{f(x + ox)}" y="{f(y + oy)}" width="{f(w)}" height="{f(h)}"/>')
    else:
        out.append(f'<path id="Takviye_Dolgu" fill="{COL["Takviye"]}" d="{poly_d(D.stiff_geom(), ox, oy)}"/>')
    out.append("</g>")
    return out


def _polyline(eid, p, w, col, ox, oy, extra=""):
    return (f'<polyline id="{eid}" fill="none" stroke="{col}" stroke-width="{f(w)}" {extra}'
            f'stroke-linejoin="miter" stroke-miterlimit="5" stroke-linecap="butt" points="{pts_attr(p, ox, oy)}"/>')


def _trace_pieces(D: Design):
    """Köprü bölgeleri çıkarılmış alt gümüş hat parçaları (ad, nokta listesi, genişlik)."""
    cut = {}
    for n, g in D.bridge_cut:
        cut.setdefault(n, []).append(g)
    out = []
    for n, p, w in D.traces:
        if n not in cut:
            out.append((n, p, w))
            continue
        r = LineString(p).difference(unary_union(cut[n]))
        parts = [r] if isinstance(r, LineString) else list(getattr(r, "geoms", []))
        parts = [q for q in parts if not q.is_empty and q.length > 1e-6]
        for k, q in enumerate(parts, 1):
            out.append((f"{n}_p{k}", list(q.coords), w))
    return out


def extra_layers(D: Design, ox, oy, editable):
    out = []
    if D.bridges:
        out.append(layer_open("Gumus_Kopru", "Gumus kopru (2. baski, dielektrik ustu)"))
        if editable:
            for n, p, w in D.bridges:
                out.append(_polyline(n, p, w, COL["Kopru"], ox, oy))
        else:
            out.append(f'<path id="Kopru_Dolgu" fill="{COL["Kopru"]}" fill-rule="evenodd" d="{poly_d(D.bridge_geom(), ox, oy)}"/>')
        out.append("</g>")
    if D.leds:
        out.append(layer_open("LED", "LED (montaj)"))
        for n, cx, cy, w, h in D.leds:
            out.append(f'<rect id="{n}" fill="{COL["LED"]}" fill-opacity="0.85" stroke="#000000" stroke-width="0.03" '
                       f'x="{f(cx - w / 2 + ox)}" y="{f(cy - h / 2 + oy)}" width="{f(w)}" height="{f(h)}"/>')
        out.append("</g>")
    if D.stickers:
        out.append(layer_open("Etiket", "Etiket (yapistirma)"))
        for i, (x, y, w, h, r) in enumerate(D.stickers, 1):
            out.append(f'<rect id="Etiket_{i}" fill="none" stroke="{COL["Etiket"]}" stroke-width="0.1" stroke-dasharray="0.6,0.4" '
                       f'x="{f(x + ox)}" y="{f(y + oy)}" width="{f(w)}" height="{f(h)}" rx="{f(r)}" ry="{f(r)}"/>')
        out.append("</g>")
    if D.check:
        out.append(layer_open("Kontrol", "Kontrol (taramadan kesin okunamayan)"))
        for n, p in D.check:
            out.append(f'<polyline id="Kontrol_{n}" fill="none" stroke="{COL["Kontrol"]}" stroke-width="0.12" '
                       f'stroke-dasharray="0.5,0.3" points="{pts_attr(p, ox, oy)}"/>')
        out.append("</g>")
    return out


def write_svg_editable(D: Design, path):
    ox = oy = D.margin
    out = svg_head(D)
    out += stiff_layer(D, ox, oy, True)
    # Gümüş
    out.append(layer_open("Gumus", "Gumus iletken"))
    out.append('<g id="Gumus_Hatlar">')
    for name, p, w in _trace_pieces(D):
        out.append(_polyline(name, p, w, COL["Gumus"], ox, oy))
    out.append("</g>")
    if D.marks:
        out.append('<g id="Gumus_Isaretler">')
        for name, p, w in D.marks:
            out.append(_polyline(name, p, w, COL["Gumus"], ox, oy))
        out.append("</g>")
    groups = {}
    for g, x, y, w, h in D.silver_rects:
        groups.setdefault(g, []).append((x, y, w, h))
    for g, rects in groups.items():
        out.append(f'<g id="{g}">')
        for i, (x, y, w, h) in enumerate(rects, 1):
            out.append(f'<rect id="{g}_{i}" fill="{COL["Gumus"]}" x="{f(x + ox)}" y="{f(y + oy)}" width="{f(w)}" height="{f(h)}"/>')
        out.append("</g>")
    out.append("</g>")
    # Dielektrik
    c, op = COL["Dielektrik"], DIEL_OPACITY
    out.append(layer_open("Dielektrik", "Dielektrik (yalitkan)"))
    out.append('<g id="Dielektrik_Seritler">')
    for i, (p, w) in enumerate(D.diel_lines_clipped(), 1):
        out.append(
            f'<polyline id="Dielektrik_Serit_{i:02d}" fill="none" stroke="{c}" stroke-opacity="{op}" stroke-width="{f(w)}" '
            f'stroke-linejoin="miter" stroke-miterlimit="5" stroke-linecap="butt" points="{pts_attr(p, ox, oy)}"/>'
        )
    if D.diel_rects and not D.diel_polys:
        out.append(f'<path id="Dielektrik_Alan" fill="{c}" fill-opacity="{op}" d="{poly_d(D.diel_area_geom(), ox, oy)}"/>')
    elif D.diel_rects or D.diel_polys:
        olp = D.outline_poly()
        for i, (x, y, w, h) in enumerate(D.diel_rects, 1):
            g = box(x, y, x + w, y + h).intersection(olp)
            out.append(f'<path id="Dielektrik_Alan_{i}" fill="{c}" fill-opacity="{op}" d="{poly_d(g, ox, oy)}"/>')
        for i, g in enumerate(D.diel_polys, 1):
            if g.geom_type == "Polygon" and len(g.exterior.coords) == 5 and not g.interiors:
                x0, y0, x1, y1 = g.bounds
                out.append(f'<rect id="Dielektrik_Yama_{i:02d}" fill="{c}" fill-opacity="{op}" '
                           f'x="{f(x0 + ox)}" y="{f(y0 + oy)}" width="{f(x1 - x0)}" height="{f(y1 - y0)}"/>')
            else:
                out.append(f'<path id="Dielektrik_Yama_{i:02d}" fill="{c}" fill-opacity="{op}" d="{poly_d(g, ox, oy)}"/>')
    for i, (x, y, w, h, lw) in enumerate(D.diel_rings, 1):
        out.append(
            f'<rect id="Dielektrik_Ped_Cercevesi_{i}" fill="none" stroke="{c}" stroke-opacity="{op}" stroke-width="{f(lw)}" '
            f'x="{f(x + ox)}" y="{f(y + oy)}" width="{f(w)}" height="{f(h)}"/>'
        )
    out += ["</g>", "</g>"]
    out += extra_layers(D, ox, oy, True)
    out += cut_layer(D, ox, oy)
    out.append("</svg>")
    open(path, "w", encoding="utf-8").write("\n".join(out))


def production_layers(D: Design, ox, oy):
    out = stiff_layer(D, ox, oy, False)
    out.append(layer_open("Gumus", "Gumus iletken"))
    out.append(f'<path id="Gumus_Dolgu" fill="{COL["Gumus"]}" fill-rule="evenodd" d="{poly_d(D.silver_geom(), ox, oy)}"/>')
    out.append("</g>")
    out.append(layer_open("Dielektrik", "Dielektrik (yalitkan)"))
    out.append(
        f'<path id="Dielektrik_Dolgu" fill="{COL["Dielektrik"]}" fill-opacity="{DIEL_OPACITY}" fill-rule="evenodd" '
        f'd="{poly_d(D.diel_geom(), ox, oy)}"/>'
    )
    out.append("</g>")
    out += extra_layers(D, ox, oy, False)
    out += cut_layer(D, ox, oy)
    return out


def write_svg_production(D: Design, path):
    out = svg_head(D) + production_layers(D, D.margin, D.margin) + ["</svg>"]
    open(path, "w", encoding="utf-8").write("\n".join(out))


def write_svg_check(D: Design, path, scan_png, downscale=0.5):
    """Üretim katmanlarını, hizalanmış tarama görüntüsünün üzerine yerleştirir."""
    sc = D.scan
    im = cv2.imread(scan_png)
    im = cv2.resize(im, None, fx=downscale, fy=downscale, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    b64 = base64.b64encode(buf.tobytes()).decode()
    ox = oy = D.margin
    x = (0 - sc["px0"]) / sc["s"] + sc["mm0"][0] + ox
    y = (0 - sc["py0"]) / sc["s"] + sc["mm0"][1] + oy
    w = im.shape[1] / downscale / sc["s"]
    h = im.shape[0] / downscale / sc["s"]
    out = svg_head(D)
    out.append(layer_open("Tarama", "Tarama referansi (kilitli)"))
    out.append(
        f'<image id="Tarama_Goruntu" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" '
        f'preserveAspectRatio="none" xlink:href="data:image/jpeg;base64,{b64}"/>'
    )
    out.append("</g>")
    lay = production_layers(D, ox, oy)
    lay = [l.replace(f'fill="{COL["Gumus"]}"', f'fill="{COL["Gumus"]}" fill-opacity="0.45"') for l in lay]
    out += lay + ["</svg>"]
    open(path, "w", encoding="utf-8").write("\n".join(out))


# ---------------------------------------------------------------- PDF
K = 0.5522847498


def _pt(v):
    return v * 72.0 / 25.4


def _arc_beziers(p0, p1, r, sweep):
    """Küçük yayı en fazla 90°'lik kübik Bézier parçalarına böler."""
    cx, cy = arc_center(p0, p1, r, sweep)
    a0 = math.atan2(p0[1] - cy, p0[0] - cx)
    a1 = math.atan2(p1[1] - cy, p1[0] - cx)
    da = a1 - a0
    if sweep:
        while da <= 0:
            da += 2 * math.pi
    else:
        while da >= 0:
            da -= 2 * math.pi
    n = max(1, math.ceil(abs(da) / (math.pi / 2) - 1e-9))
    step = da / n
    k = 4 / 3 * math.tan(step / 4)
    segs = []
    for i in range(n):
        t0, t1 = a0 + i * step, a0 + (i + 1) * step
        q0 = (cx + r * math.cos(t0), cy + r * math.sin(t0))
        q3 = (cx + r * math.cos(t1), cy + r * math.sin(t1))
        q1 = (q0[0] - k * r * math.sin(t0), q0[1] + k * r * math.cos(t0))
        q2 = (q3[0] + k * r * math.sin(t1), q3[1] - k * r * math.cos(t1))
        segs.append((q0, q1, q2, q3))
    return segs


def write_pdf(D: Design, path):
    ox = oy = D.margin
    W, H = D.width + 2 * ox, D.height + 2 * oy
    doc = pymupdf.open()
    page = doc.new_page(width=_pt(W), height=_pt(H))
    layers = [("Takviye", "Takviye (arka yuz, ZIF)"), ("Gumus", "Gumus iletken"),
              ("Dielektrik", "Dielektrik (yalitkan)")]
    if D.bridges:
        layers.append(("Kopru", "Gumus kopru (2. baski, dielektrik ustu)"))
    if D.leds:
        layers.append(("LED", "LED (montaj)"))
    if D.stickers:
        layers.append(("Etiket", "Etiket (yapistirma)"))
    if D.check:
        layers.append(("Kontrol", "Kontrol (taramadan kesin okunamayan)"))
    layers.append(("Kesim", "Kesim (dis kontur + pencereler)"))
    ocg = {k: doc.add_ocg(lbl, on=True) for k, lbl in layers}

    def P(x, y):
        return pymupdf.Point(_pt(x + ox), _pt(y + oy))

    def rgb(hexc):
        return tuple(int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def fill_geom(geom, key, opacity=1.0):
        if geom.is_empty:
            return
        sh = page.new_shape()
        polys = [geom] if isinstance(geom, Polygon) else list(geom.geoms)
        for p in polys:
            for ring in [p.exterior, *p.interiors]:
                c = [P(x, y) for x, y in ring.coords]
                sh.draw_polyline(c)
        sh.finish(color=None, fill=rgb(COL[key]), even_odd=True, closePath=True, fill_opacity=opacity, oc=ocg[key])
        sh.commit()

    fill_geom(D.stiff_geom(), "Takviye")
    fill_geom(D.silver_geom(), "Gumus")
    fill_geom(D.diel_geom(), "Dielektrik", DIEL_OPACITY)
    if D.bridges:
        fill_geom(D.bridge_geom(), "Kopru")
    if D.leds:
        fill_geom(D.led_geom(), "LED", 0.85)
    for key, items in (("Etiket", [(x, y, x + w, y + h) for x, y, w, h, _ in D.stickers]),):
        for x0, y0, x1, y1 in items:
            sh = page.new_shape()
            sh.draw_rect(pymupdf.Rect(P(x0, y0), P(x1, y1)))
            sh.finish(color=rgb(COL[key]), fill=None, width=_pt(0.1), dashes="[2 1] 0", oc=ocg[key])
            sh.commit()
    for n, p in D.check:
        sh = page.new_shape()
        sh.draw_polyline([P(x, y) for x, y in p])
        sh.finish(color=rgb(COL["Kontrol"]), fill=None, width=_pt(0.12), dashes="[1.5 1] 0", closePath=False, oc=ocg["Kontrol"])
        sh.commit()

    # Kesim: gerçek yaylar (Bézier) ile
    sh = page.new_shape()
    cur = None
    for s in D.outline:
        if s[0] == "M":
            cur = (s[1], s[2])
        elif s[0] == "L":
            sh.draw_line(P(*cur), P(s[1], s[2]))
            cur = (s[1], s[2])
        elif s[0] == "A":
            for q0, q1, q2, q3 in _arc_beziers(cur, (s[3], s[4]), s[1], s[2]):
                sh.draw_bezier(P(*q0), P(*q1), P(*q2), P(*q3))
            cur = (s[3], s[4])
    sh.finish(color=rgb(COL["Kesim"]), fill=None, width=_pt(CUT_W), closePath=False, oc=ocg["Kesim"])
    for cx, cy, w, h in D.holes:
        r = w / 2
        a, b = (cx + r, cy - h / 2 + r), (cx + r, cy + h / 2 - r)
        c, d = (cx - r, cy + h / 2 - r), (cx - r, cy - h / 2 + r)
        sh.draw_line(P(*a), P(*b))
        for q in _arc_beziers(b, c, r, 1):
            sh.draw_bezier(*(P(*t) for t in q))
        sh.draw_line(P(*c), P(*d))
        for q in _arc_beziers(d, a, r, 1):
            sh.draw_bezier(*(P(*t) for t in q))
        sh.finish(color=rgb(COL["Kesim"]), fill=None, width=_pt(CUT_W), closePath=False, oc=ocg["Kesim"])
    sh.commit()
    doc.set_metadata({"title": D.title, "creator": "fpcvec.py"})
    try:
        doc.save(path, garbage=3, deflate=True)
    except Exception as e:  # dosya bir görüntüleyicide açık (Windows kilidi)
        alt = path[:-4] + "_yeni.pdf"
        doc.save(alt, garbage=3, deflate=True)
        print(f"UYARI: {path} yazilamadi ({e.__class__.__name__}); {alt} olarak kaydedildi. Dosyayi kapatip tekrar calistirin.")
        return alt
    return path


# ---------------------------------------------------------------- doğrulama
def to_px(geom, sc):
    """mm geometrisini deskew tarama pikseline çevirir."""
    g = affinity.translate(geom, -sc["mm0"][0], -sc["mm0"][1])
    g = affinity.scale(g, sc["s"], sc["s"], origin=(0, 0))
    return affinity.translate(g, sc["px0"], sc["py0"])


def raster(geom, shape):
    m = np.zeros(shape, np.uint8)
    polys = [geom] if isinstance(geom, Polygon) else list(getattr(geom, "geoms", []))
    for p in polys:
        cv2.fillPoly(m, [np.round(np.array(p.exterior.coords)).astype(np.int32)], 1)
        for r in p.interiors:
            cv2.fillPoly(m, [np.round(np.array(r.coords)).astype(np.int32)], 0)
    return m.astype(bool)
