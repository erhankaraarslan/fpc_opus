"""Tasarım tutarlılık kontrolleri: çizimin kendi içinde doğru ve CorelDRAW'da temiz düzenlenebilir olması.

Kullanım: python tutarlilik.py <ad>      (veya fpc.py check <ad>)
Python içinden: kontrol(D, A=None, esik=None) -> [bulgu]   (A = netlist.analiz(D))

Üretim DRC'si değildir; taramadan çizim çıkarırken tipik hataları yakalar. Eşikler ESIK sözlüğünde,
parts/<ad>.json "tutarlilik": {...} ile parça bazında değiştirilebilir.
  yakin_bosluk      farklı ağlardaki gümüşler arası 0 < mesafe < min_aralik  (değmesi gereken uç kısa kalmış
                    ya da iki hat fazla yakın)                                                   UYARI
  ince_bolge        katmanda min_genislik altında kalan parça (refine kırığı, sivri köşe)          UYARI
  kopru_*           köprü bindirmesi < kopru_bindirme_min, ucu yalıtkan üstünde / alt gümüşe değmiyor,
                    köprü yalıtkan dışına çıkıyor                                                UYARI
  yalitimsiz_kesisim köprü başka bir alt gümüşü yalıtkan DIŞINDA kesiyor (kısa devre)            HATA
  yalitim_payi      köprü altı kesişmenin yalıtkan kenarına uzaklığı < yalitim_payi              UYARI
  mikro_segment     hat/köprü çizgisinde < mikro_segment uzunlukta parça                          UYARI
  dar_donus         yön değişimi > 90° (mitre sivriliği)                                          UYARI
  gereksiz_dugum    neredeyse doğrusal ardışık parçalar (< 1°)                                    BILGI
  aci_45_disi       0/45/90 katı olmayan uzun parça (ölçülmüş olabilir; kontrol için)            BILGI
  kontur_disi / kesim_payi / pencere   gümüş kart dışında, kesim kenarına çok yakın, oval pencereyle kesişiyor
  ust_uste_hat      iki hat çizgisi uzun boyunca üst üste (CorelDRAW'da yinelenen nesne)          UYARI
"""
import math
import sys

from shapely import STRtree
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, unary_union

import bulgu
import netlist

ESIK = dict(min_aralik_mm=0.2, min_genislik_mm={"Gumus": 0.3, "Kopru": 0.3, "Dielektrik": 0.15},
            kopru_bindirme_min_mm=0.2, yalitim_payi_mm=0.15, mikro_segment_mm=0.1, kesim_payi_mm=0.2,
            ince_alan_min_mm2=0.01, aci_tol_derece=0.5)


def _mid(a, b):
    p, q = nearest_points(a, b)
    return ((p.x + q.x) / 2, (p.y + q.y) / 2)


def _ince(g, r, amin):
    if g.is_empty:
        return []
    o = g.buffer(-r, join_style="mitre").buffer(r, join_style="mitre")
    return [p for p in netlist.parts(g.difference(o)) if p.area > amin]


def _segment_kontrol(name, pts, E, B):
    P = [tuple(p) for p in pts]
    dirs = []
    for i, (a, b) in enumerate(zip(P[:-1], P[1:])):
        L = math.dist(a, b)
        if L < E["mikro_segment_mm"]:
            B.append(bulgu.yeni("UYARI", "mikro_segment", f"{name}:{i}", f"'{name}' {i}. parçası {L * 1000:.0f} µm "
                                                                          f"(düzenlemede fazladan düğüm)", a))
        dirs.append((math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), L, a))
    tuhaf = []
    for i in range(1, len(dirs)):
        t = (dirs[i][0] - dirs[i - 1][0] + 180) % 360 - 180
        if abs(t) > 90 + 1e-6:
            B.append(bulgu.yeni("UYARI", "dar_donus", f"{name}:{i}", f"'{name}' köşesinde {abs(t):.0f}° yön değişimi "
                                                                       f"(sivri mitre köşe)", P[i]))
        elif 1e-9 < abs(t) < 1.0 and dirs[i][1] > 0 and dirs[i - 1][1] > 0:
            B.append(bulgu.yeni("BILGI", "gereksiz_dugum", f"{name}:{i}", f"'{name}' {i}. düğüm neredeyse doğrusal "
                                                                            f"({abs(t):.2f}°)", P[i]))
    for a, L, p in dirs:
        dev = abs(((a % 45) + 22.5) % 45 - 22.5)
        if dev > E["aci_tol_derece"] and L > 0.3:
            tuhaf.append(f"{a % 180:.1f}°")
    if tuhaf:
        B.append(bulgu.yeni("BILGI", "aci_45_disi", name, f"'{name}' 0/45/90 dışı açılar: {', '.join(tuhaf)}", P[0]))


def kontrol(D, A=None, esik=None):
    E = dict(ESIK)
    for k, v in (esik or {}).items():
        E[k] = {**E[k], **v} if isinstance(E.get(k), dict) else v
    A = A or netlist.analiz(D)
    comps, kok, diel = A["_ic"]["comps"], A["_ic"]["kok"], A["_ic"]["diel"]
    B = []
    el = [e for e in D.silver_elements() if e[1] != "isaret"]
    ctree = STRtree(comps)
    etree = STRtree([g for _, _, g in el])

    def el_near(g, d):
        return [el[i][0] for i in etree.query(g, predicate="dwithin", distance=d)]

    # 1) yakın boşluk (farklı ağ)
    a, b = ctree.query(comps, predicate="dwithin", distance=E["min_aralik_mm"])
    for i, j in zip(a.tolist(), b.tolist()):
        if i >= j or kok[i] == kok[j]:
            continue
        d = comps[i].distance(comps[j])
        if d <= netlist.TOL:
            continue
        ni = sorted(set(el_near(comps[j], d + 1e-6)) & set(el_near(comps[i], 0)))
        nj = sorted(set(el_near(comps[i], d + 1e-6)) & set(el_near(comps[j], 0)))
        key = "/".join(sorted([",".join(ni[:2]), ",".join(nj[:2])]))
        B.append(bulgu.yeni("UYARI", "yakin_bosluk", key, f"{' / '.join(ni[:2])} ile {' / '.join(nj[:2])} arası "
                                                          f"{d:.3f} mm (değmesi gerekiyorsa uç kısa; değilse aralık dar)",
                            _mid(comps[i], comps[j])))
    # 2) ince bölgeler
    low = unary_union([g for _, _, g in el])
    katman = {"Gumus": low, "Kopru": D.bridge_geom() if D.bridges else None, "Dielektrik": D.diel_geom()}
    for k, g in katman.items():
        if g is None or g.is_empty:
            continue
        for p in _ince(g, E["min_genislik_mm"][k] / 2, E["ince_alan_min_mm2"]):
            c = p.representative_point()
            near = el_near(p, 0) if k == "Gumus" else []
            B.append(bulgu.yeni("UYARI", "ince_bolge", f"{k}:{c.x:.1f},{c.y:.1f}",
                                f"{k} katmanında {E['min_genislik_mm'][k]} mm'den ince bölge ({p.area:.3f} mm²)"
                                + (f": {', '.join(near[:3])}" if near else ""), (c.x, c.y)))
    # 3) köprüler
    for n, p, w in D.bridges:
        line, poly = LineString(p), LineString(p).buffer(w / 2, **{"cap_style": "flat", "join_style": "mitre"})
        if diel.is_empty:
            B.append(bulgu.yeni("UYARI", "kopru_yalitkansiz", n, f"'{n}': çizimde dielektrik yok", p[0]))
            continue
        out_l = line.difference(diel)
        ol = netlist.parts(out_l.buffer(1e-6)) and [q for q in getattr(out_l, "geoms", [out_l]) if not q.is_empty]
        if not ol:
            B.append(bulgu.yeni("UYARI", "kopru_tamamen_yalitkanda", n, f"'{n}' hiç yalıtkan dışına çıkmıyor (bağlantı yok)", p[0]))
            continue
        for tag, q in (("bas", Point(p[0])), ("son", Point(p[-1]))):
            uc = [s for s in ol if s.distance(q) < 1e-6]
            if not uc:
                B.append(bulgu.yeni("UYARI", "kopru_ucu_yalitkanda", f"{n}:{tag}", f"'{n}' {tag} ucu yalıtkan üstünde bitiyor", q.coords[0]))
                continue
            L = uc[0].length
            if L < E["kopru_bindirme_min_mm"]:
                B.append(bulgu.yeni("UYARI", "kopru_bindirme", f"{n}:{tag}", f"'{n}' {tag} ucunda bindirme {L:.2f} mm "
                                                                             f"(< {E['kopru_bindirme_min_mm']})", q.coords[0]))
            if not ctree.query(uc[0].buffer(w / 2, cap_style="flat"), predicate="intersects").size:
                B.append(bulgu.yeni("UYARI", "kopru_ucu_bosta", f"{n}:{tag}", f"'{n}' {tag} ucu alt gümüşe değmiyor", q.coords[0]))
        uclar = [Point(p[0]), Point(p[-1])]
        for s in netlist.parts(poly.difference(diel)):
            uc_mu = min(s.distance(q) for q in uclar) < w
            hit = ctree.query(s, predicate="intersects").tolist()  # köprü öncesi ayrı alt gümüş bileşenleri
            c = s.representative_point()
            if len(hit) > 1 or (hit and not uc_mu):
                B.append(bulgu.yeni("HATA", "yalitimsiz_kesisim", f"{n}:{c.x:.1f},{c.y:.1f}",
                                    f"'{n}' yalıtkan dışındaki kısmı "
                                    + (f"{len(hit)} ayrı alt gümüşe birden değiyor (kısa devre)" if len(hit) > 1
                                       else "ortada alt gümüşle temas ediyor (kısa devre)"), (c.x, c.y)))
            elif not uc_mu:
                B.append(bulgu.yeni("UYARI", "kopru_yalitkan_disi", f"{n}:{c.x:.1f},{c.y:.1f}",
                                    f"'{n}' ortasında yalıtkan dışına çıkıyor ({s.area / w:.2f} mm)", (c.x, c.y)))
        temas = set(ctree.query(poly.difference(diel), predicate="intersects").tolist())
        for i in ctree.query(poly, predicate="intersects").tolist():
            if i in temas:
                continue
            x = poly.intersection(comps[i])
            if x.is_empty:
                continue
            tasan = x.buffer(E["yalitim_payi_mm"]).difference(diel).area
            if tasan > 1e-4:
                c = x.representative_point()
                B.append(bulgu.yeni("UYARI", "yalitim_payi", f"{n}:{c.x:.1f},{c.y:.1f}",
                                    f"'{n}' altındaki kesişmede yalıtkan payı < {E['yalitim_payi_mm']} mm", (c.x, c.y)))
    # 4) çizgi geometrisi
    for n, p, w in list(D.traces) + list(D.bridges):
        _segment_kontrol(n, p, E, B)
    # 5) kontur, kesim payı, pencereler
    olp = D.outline_poly()
    edge = olp.exterior
    holes = unary_union(D.holes_polys()) if D.holes else None
    for n, k, g in el + D.bridge_elements():
        dis = g.difference(olp).area
        if dis > 1e-4:
            c = g.difference(olp).representative_point()
            B.append(bulgu.yeni("UYARI", "kontur_disi", n, f"'{n}' kart konturunun dışına taşıyor ({dis:.3f} mm²)", (c.x, c.y)))
        elif k != "kontak" and g.distance(edge) < E["kesim_payi_mm"]:
            B.append(bulgu.yeni("UYARI", "kesim_payi", n, f"'{n}' kesim kenarına {g.distance(edge):.2f} mm", _mid(g, edge)))
        if holes is not None and g.intersects(holes) and g.intersection(holes).area > 1e-4:
            c = g.intersection(holes).representative_point()
            B.append(bulgu.yeni("UYARI", "pencere", n, f"'{n}' oval pencereyle kesişiyor", (c.x, c.y)))
    # 6) üst üste binen hatlar
    tr = [(n, LineString(p).buffer(w / 2, cap_style="flat", join_style="mitre"), w) for n, p, w in D.traces]
    tt = STRtree([g for _, g, _ in tr])
    a, b = tt.query([g for _, g, _ in tr], predicate="intersects")
    for i, j in zip(a.tolist(), b.tolist()):
        if i >= j:
            continue
        ar = tr[i][1].intersection(tr[j][1]).area
        w = min(tr[i][2], tr[j][2])
        if ar > 2 * w * w:
            c = tr[i][1].intersection(tr[j][1]).representative_point()
            B.append(bulgu.yeni("UYARI", "ust_uste_hat", f"{tr[i][0]}/{tr[j][0]}",
                                f"'{tr[i][0]}' ve '{tr[j][0]}' ~{ar / w:.1f} mm boyunca üst üste", (c.x, c.y)))
    tek = {}
    for x in B:
        tek.setdefault(x["id"], x)
    return list(tek.values())


if __name__ == "__main__":
    import cfg
    from verify import load_design
    ad = sys.argv[1]
    c = cfg.load(ad)
    D = load_design(ad)
    B = bulgu.kabul_uygula(kontrol(D, esik=c.get("tutarlilik")), c.get("kabul_edilen_bulgular"))
    bulgu.ozet_yaz(B, 80)
