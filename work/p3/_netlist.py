"""P3 cizim geometrisinden ag (net) cikarimi: LED pedleri ve kontaklar hangi aga bagli? (mantik kontrolu)"""
import sys
sys.path.insert(0, ".devin/skills/fpc-vektor/scripts"); sys.path.insert(0, "parts")
import cfg  # noqa
from shapely.geometry import box
from shapely.ops import unary_union
from verify import load_design
D = load_design("p3")
bot = D.silver_geom()
comps = list(bot.geoms) if bot.geom_type == "MultiPolygon" else [bot]
patch = unary_union(D.diel_polys)
parent = list(range(len(comps)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i


from shapely.geometry import LineString
top = unary_union([LineString(p).buffer(w / 2) for _, p, w in D.bridges])
for tg in (list(top.geoms) if top.geom_type == "MultiPolygon" else [top]):
    g = tg.difference(patch)
    hit = [i for i, c in enumerate(comps) if c.intersects(g)]
    for a in hit[1:]:
        parent[find(a)] = find(hit[0])


def net_of(geom):
    s = {find(i) for i, c in enumerate(comps) if c.intersects(geom)}
    return s


pins = {}
for n, p, w in D.traces:
    if n.startswith("Kontak_"):
        x = p[0][0]
        pins[n[-2:]] = net_of(box(x - 0.1, p[-1][1] - 1, x + 0.1, p[-1][1]))
names = {}
for k, v in pins.items():
    for r in v:
        names.setdefault(r, []).append(k)
print("pin agi:", {k: sorted(v) for k, v in pins.items()})
for g, x, y, w, h in D.silver_rects:
    if g.startswith("LED_"):
        r = net_of(box(x + 0.2, y + 0.2, x + w - 0.2, y + h - 0.2))
        print(g, [names.get(i, ["PINSIZ"]) for i in r])
