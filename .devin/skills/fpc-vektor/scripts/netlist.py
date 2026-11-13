"""Çizim geometrisinden ağ (net) çıkarımı ve elektrik mantığı kontrolleri (taramaya bakmaz).

Kullanım: python netlist.py <ad>      (veya fpc.py check <ad>)
Python içinden: analiz(D) -> dict(aglar, bulgular, ozet)

Model (parçaya özel değildir; adlandırma kuralı veya Design.pins / Design.devices ile çalışır):
  alt gümüş  hatlar (köprü kesimleri çıkarılmış) + gümüş dikdörtgenler; "+" işaretleri (marks) ağ dışıdır.
  köprü      2. gümüş baskı; yalnızca dielektrik DIŞINDA değdiği alt gümüş parçalarını birleştirir.
  pin        adı "Kontak_<no>" olan hat ("_dummy" soneki = dummy) + Design.pins [(ad, geom, dummy)].
  cihaz      LED: Design.leds adı + "_ped_*" dikdörtgen grupları uçlardır.
             Tuş pedi: "Ped_*" grubunun birbirine değmeyen bileşenleri (taraklar) uçlardır.
             Design.devices [(ad, [(uç, geom), ...])] ile başka tipler eklenir.
Kontroller (bulgu.py): kisa_devre, pinsiz_ag, tarak_sayisi, led_uclari (HATA); ayrik_pinler, bos_pin,
  dummy_bagli, yuzen_gumus, serbest_uc (UYARI); bitisik_pinler (BILGI).
"""
import re
import sys

from shapely import STRtree
from shapely.geometry import Point
from shapely.ops import unary_union

import bulgu

TOL = 1e-3  # mm: değme toleransı


def parts(g):
    if g.is_empty:
        return []
    return [g] if g.geom_type == "Polygon" else [x for x in getattr(g, "geoms", []) if x.geom_type == "Polygon"]


def _pt(g):
    p = g.representative_point()
    return (p.x, p.y)


def clusters(geoms, tol=TOL):
    """Birbirine tol içinde değen çokgen parçalarını kümeler (kayan nokta boşluklarına dayanıklı bileşenler)."""
    ps = [p for g in geoms for p in parts(g)]
    if not ps:
        return []
    uf = _UF(len(ps))
    tr = STRtree(ps)
    a, b = tr.query(ps, predicate="dwithin", distance=tol)
    for i, j in zip(a.tolist(), b.tolist()):
        if i < j:
            uf.union(i, j)
    out = {}
    for i, p in enumerate(ps):
        out.setdefault(uf.find(i), []).append(p)
    return [unary_union(v) for v in out.values()]


class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def _pins(D, el):
    out = []
    for n, kind, g in el:
        m = re.match(r"Kontak_(\d+)", n)
        if kind == "kontak" and m:
            out.append(dict(ad=n, no=int(m.group(1)), dummy=n.endswith("_dummy"), geom=g))
    for i, (n, g, dummy) in enumerate(D.pins, 1):
        m = re.search(r"(\d+)", n)
        out.append(dict(ad=n, no=int(m.group(1)) if m else 1000 + i, dummy=bool(dummy), geom=g))
    return sorted(out, key=lambda p: p["no"])


def _devices(D, el, B):
    groups = {n: g for n, k, g in el if k in ("led_ped", "tus_ped", "dikdortgen")}
    devs = []
    for led in D.leds:
        n = led[0]
        uc = [(g[len(n) + 1:].replace("ped_", ""), geom) for g, geom in groups.items() if g.startswith(n + "_ped")]
        if len(uc) != 2:
            B.append(bulgu.yeni("HATA", "led_uclari", n, f"{n}: {len(uc)} ped grubu bulundu (beklenen 2: '{n}_ped_ust/alt')",
                                (led[1], led[2])))
        devs.append(dict(ad=n, uclar=uc))
    for g, geom in groups.items():
        if not g.startswith("Ped_"):
            continue
        ps = sorted(clusters([geom]), key=lambda p: (p.centroid.y, p.centroid.x))
        if len(ps) != 2:
            B.append(bulgu.yeni("HATA", "tarak_sayisi", g, f"{g}: {len(ps)} ayrık tarak (beklenen 2; 1 ise taraklar "
                                                              f"birbirine değiyor = kısa devre)", _pt(geom)))
        names = ["ust", "alt"] if len(ps) == 2 else [f"t{i}" for i in range(1, len(ps) + 1)]
        devs.append(dict(ad=g, uclar=list(zip(names, ps))))
    devs += [dict(ad=n, uclar=list(u)) for n, u in D.devices]
    return devs


def analiz(D):
    B = []
    el_all = D.silver_elements()
    el = [e for e in el_all if e[1] != "isaret"]
    comps = clusters([g for _, _, g in el])
    tree = STRtree(comps)

    def comps_of(g):
        return set(tree.query(g, predicate="dwithin", distance=TOL).tolist()) if not g.is_empty else set()

    uf = _UF(len(comps))
    diel = D.diel_geom(clip=False)
    kop = []
    for n, _, g in D.bridge_elements():
        out = g.difference(diel) if not diel.is_empty else g
        hit = sorted(comps_of(out))
        for a in hit[1:]:
            uf.union(a, hit[0])
        kop.append((n, hit))

    pins = _pins(D, el)
    devs = _devices(D, el, B)
    nets = {}

    def net(r):
        return nets.setdefault(r, dict(pinler=[], dummy=[], uclar=[], elemanlar=[], kok=r))

    for i in range(len(comps)):
        net(uf.find(i))
    for p in pins:
        rs = {uf.find(i) for i in comps_of(p["geom"])}
        p["aglar"] = rs
        for r in rs:
            net(r)["dummy" if p["dummy"] else "pinler"].append(p["no"])
    for d in devs:
        d["ag"] = []
        for u, g in d["uclar"]:
            rs = {uf.find(i) for i in comps_of(g)}
            d["ag"].append(rs)
            for r in rs:
                net(r)["uclar"].append(f"{d['ad']}.{u}")
    for n, kind, g in el:
        if kind != "kontak":
            for r in {uf.find(i) for i in comps_of(g)}:
                net(r)["elemanlar"].append(n)

    # --- kontroller ---
    for d in devs:
        if len(d["uclar"]) >= 2:
            ag = [frozenset(a) for a in d["ag"]]
            for i in range(len(ag)):
                for j in range(i + 1, len(ag)):
                    if ag[i] & ag[j]:
                        B.append(bulgu.yeni("HATA", "kisa_devre", d["ad"],
                                            f"{d['ad']}: '{d['uclar'][i][0]}' ve '{d['uclar'][j][0]}' uçları aynı ağda",
                                            _pt(d["uclar"][i][1])))
    term_geom = {f"{d['ad']}.{u}": g for d in devs for u, g in d["uclar"]}
    for r, N in nets.items():
        u = sorted(set(N["uclar"]))
        pn = sorted(set(N["pinler"]))
        el_g = [g for n, k, g in el if n in N["elemanlar"]]
        konum = _pt(term_geom[u[0]]) if u else (_pt(el_g[0]) if el_g else None)
        if u and not pn:
            B.append(bulgu.yeni("HATA", "pinsiz_ag", ",".join(u),
                                f"Hiçbir pine ulaşmayan ağ: {', '.join(u)} (kopukluk veya eksik hat)", konum))
        if not u and not pn and not N["dummy"]:
            B.append(bulgu.yeni("UYARI", "yuzen_gumus", ",".join(sorted(set(N["elemanlar"]))) or f"bilesen{r}",
                                f"Ne pine ne cihaza bağlı gümüş: {', '.join(sorted(set(N['elemanlar']))) or '?'}", konum))
        if len(pn) > 1:
            bit = pn[-1] - pn[0] + 1 == len(pn)
            B.append(bulgu.yeni("BILGI" if bit else "UYARI", "bitisik_pinler" if bit else "ayrik_pinler",
                                ",".join(map(str, pn)),
                                f"Pinler {', '.join(map(str, pn))} aynı ağda" + ("" if bit else " (bitişik değil: şüpheli)"),
                                konum))
        if N["dummy"] and (u or pn):
            B.append(bulgu.yeni("UYARI", "dummy_bagli", ",".join(map(str, sorted(set(N["dummy"])))),
                                f"Dummy pin {sorted(set(N['dummy']))} bir ağa bağlı: {', '.join(u + [str(p) for p in pn])}", konum))
    for p in pins:
        if not p["dummy"] and all(not nets[r]["uclar"] for r in p["aglar"]):
            B.append(bulgu.yeni("UYARI", "bos_pin", str(p["no"]), f"Pin {p['no']} hiçbir cihaza bağlı değil",
                                (p["geom"].centroid.x, p["geom"].bounds[3])))
    # serbest uç: hattın ucu kendisi dışında hiçbir gümüş elemana değmiyor
    others = [(n, g) for n, k, g in el] + [(n, g) for n, _, g in D.bridge_elements()]
    otree = STRtree([g for _, g in others])
    for n, p, w in D.traces:
        if n.startswith("Kontak_"):
            continue
        for tag, q in (("bas", p[0]), ("son", p[-1])):
            reg = Point(q).buffer(w * 0.55)
            hit = [others[i][0] for i in otree.query(reg, predicate="intersects")]
            if not [h for h in hit if h != n and not (h.startswith("Kopru_") and h.endswith("_" + n))]:
                B.append(bulgu.yeni("UYARI", "serbest_uc", f"{n}:{tag}",
                                    f"'{n}' hattının {'başı' if tag == 'bas' else 'sonu'} hiçbir gümüşe değmiyor (açık uç)", q))

    aglar = []
    for N in nets.values():
        if not (N["pinler"] or N["uclar"] or N["dummy"]):
            continue
        aglar.append(dict(pinler=sorted(set(N["pinler"])), dummy=sorted(set(N["dummy"])), uclar=sorted(set(N["uclar"])),
                          hatlar=sorted(set(N["elemanlar"]))))
    aglar.sort(key=lambda a: (a["pinler"][0] if a["pinler"] else 999, a["uclar"]))
    for i, a in enumerate(aglar, 1):
        a["no"] = i
    ozet = dict(ag=len(aglar), pin=len([p for p in pins if not p["dummy"]]), dummy=len([p for p in pins if p["dummy"]]),
                cihaz=len(devs), bilesen=len(comps), kopru=len(kop))
    tek = {}
    for b in B:
        tek.setdefault(b["id"], b)
    # "_ic": tutarlılık kontrolleri için iç veri (JSON'a yazılmaz)
    eleman_ag = {n: {uf.find(i) for i in comps_of(g)} for n, k, g in el}
    pin_ag = {p["no"]: p["aglar"] for p in pins if not p["dummy"]}
    cihaz_ag = {d["ad"]: [set(a) for a in d["ag"]] for d in devs}
    return dict(aglar=aglar, bulgular=list(tek.values()), ozet=ozet,
                _ic=dict(comps=comps, kok=[uf.find(i) for i in range(len(comps))], diel=diel,
                         eleman_ag=eleman_ag, pin_ag=pin_ag, cihaz_ag=cihaz_ag))


def imza(aglar):
    """Regresyon için sıralı, kararlı ağ imzası."""
    return sorted(f"P{','.join(map(str, a['pinler']))}|{';'.join(a['uclar'])}" for a in aglar)


def harita(D, A, bulgular, path, ppm=12):
    """Ağ haritası: her ağ ayrı renk, pin numaraları, bulgu konumları (kırmızı = HATA, turuncu = UYARI)."""
    import cv2
    import numpy as np
    m = D.margin
    W, H = int((D.width + 2 * m) * ppm), int((D.height + 2 * m) * ppm)
    im = np.full((H, W, 3), 255, np.uint8)

    def P(g):
        return [np.round((np.array(r.coords) + m) * ppm).astype(np.int32) for p in parts(g) for r in [p.exterior]]

    def holes(g):
        return [np.round((np.array(r.coords) + m) * ppm).astype(np.int32) for p in parts(g) for r in p.interiors]

    cv2.polylines(im, P(D.outline_poly()), True, (150, 150, 150), 1)
    d = D.diel_geom()
    if not d.is_empty:
        cv2.fillPoly(im, P(d), (235, 225, 200))
        cv2.fillPoly(im, holes(d), (255, 255, 255))
    pal = [(0, 0, 220), (220, 90, 0), (0, 150, 0), (180, 0, 180), (0, 140, 255), (140, 70, 0), (0, 170, 170),
           (90, 0, 160), (60, 60, 200), (0, 100, 60), (200, 0, 90), (100, 100, 0)]
    el = {n: g for n, k, g in D.silver_elements() if k != "isaret"}
    for i, a in enumerate(A["aglar"]):
        c = pal[i % len(pal)] if a["pinler"] else (190, 190, 190)  # pinsiz ağ: gri dolgu + siyah kontur
        for n in a["hatlar"]:
            if n in el:
                cv2.fillPoly(im, P(el[n]), c)
                if not a["pinler"]:
                    cv2.polylines(im, P(el[n]), True, (0, 0, 0), 1)
    for n, _, g in D.bridge_elements():
        cv2.polylines(im, P(g), True, (40, 40, 40), 1)
    for n, k, g in D.silver_elements():
        if k == "kontak":
            mt = re.match(r"Kontak_(\d+)", n)
            x, y = g.centroid.x, g.bounds[3]
            cv2.putText(im, str(int(mt.group(1))) if mt else "?", (int((x + m) * ppm) - 5, int((y + m) * ppm) + 14),
                        cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 0, 0), 1)
    for b in sorted(bulgular, key=lambda b: (not b["bilinen"], b["seviye"] == "HATA")):  # HATA en üstte
        if b["konum"] and b["seviye"] != "BILGI":
            x, y = (np.array(b["konum"]) + m) * ppm
            hata = b["seviye"] == "HATA" and not b["bilinen"]
            col = (160, 160, 160) if b["bilinen"] else (0, 0, 255) if hata else (0, 150, 255)
            cv2.circle(im, (int(x), int(y)), 12 if hata else 9, col, 3 if hata else 2)
    cv2.imwrite(path, im)
    return path


if __name__ == "__main__":
    import cfg
    from verify import load_design
    ad = sys.argv[1]
    D = load_design(ad)
    A = analiz(D)
    bulgu.kabul_uygula(A["bulgular"], cfg.load(ad).get("kabul_edilen_bulgular"))
    for a in A["aglar"]:
        print(f"Ag {a['no']:2d}: pin {a['pinler'] or '-'} dummy {a['dummy'] or '-'} | {', '.join(a['uclar'])}")
    bulgu.ozet_yaz(A["bulgular"])
