"""segs.json'u açıya ve konuma göre sıralı, filtreli listeler.

Kullanım: python seglist.py <ad> [wmin wmax]
"""
import json
import sys

name = sys.argv[1]
wmin, wmax = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (14, 36)
s = [x for x in json.load(open(f"work/{name}/segs.json")) if wmin <= x["w"] <= wmax]
for a in (0, 90, 45, 135):
    print("== ang", a)
    key = (lambda x: (x["p0"][1], x["p0"][0])) if a == 0 else (lambda x: (x["p0"][0], x["p0"][1]))
    for x in sorted([x for x in s if x["ang"] == a], key=key):
        print(f"  {x['id']:3d} ({x['p0'][0]:6.0f},{x['p0'][1]:6.0f})->({x['p1'][0]:6.0f},{x['p1'][1]:6.0f}) w={x['w']:4.1f} L={x['len']:5.0f}")
