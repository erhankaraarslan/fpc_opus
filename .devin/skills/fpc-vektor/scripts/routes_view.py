"""Kaba rotaları (px) refine edip deskew görüntü üzerine çizer.

Kullanım: python routes_view.py <rota_modulu> <ad> <x0> <y0> <x1> <y1> <olcek> [cikti]
Rota modülü ROUTES = [dict(name=..., pts=[(x,y),...], fixed=False), ...] tanımlar.
Refine sonuçları work/<ad>/routes_refined.json dosyasına yazılır.
"""
import importlib
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import cfg  # noqa: E402,F401  (parts/ yolunu ekler)
from refine import refine_route  # noqa: E402

PALETTE = [(0, 0, 255), (255, 0, 0), (0, 150, 0), (200, 0, 200), (0, 140, 255), (160, 80, 0), (0, 200, 200), (90, 0, 160)]


def route_mask(ad):
    """Refine maskesi: parts/<ad>.json "rota_maskesi" (ör. ["m_dark.npy"]) yoksa m_top | m_under."""
    names = cfg.load(ad).get("rota_maskesi") or ["m_top.npy", "m_under.npy"]
    m = None
    for n in names:
        a = np.load(cfg.work(ad, n))
        m = a if m is None else (m | a)
    return m


# Refine yöntemi: boş = maske koşusu (varsayılan). verify.load_design, parts/<ad>.json "refine_yontemi": "profil"
# ise buraya img (BGR tarama), golge (maske) ve w_nom (px, isteğe bağlı) koyar -> merkezler yoğunluk kenarıyla inceltilir.
AYAR = {}


def refine_all(routes, mask):
    out = {}
    kw = dict(img=AYAR.get("img"), golge=AYAR.get("golge"), w_nom=AYAR.get("w_nom"))
    for r in routes:
        k = r.get("raw_from", 0 if r.get("raw") else None)
        if k == 0:
            out[r["name"]] = dict(pts=[list(map(float, p)) for p in r["pts"]], w=None)
            continue
        if k is not None:
            v, ws, angs = refine_route(mask, r["pts"][:k + 1], search=r.get("search", 22), **kw)
            pts = v.round(1).tolist() + [list(map(float, p)) for p in r["pts"][k + 1:]]
            out[r["name"]] = dict(pts=pts, w=ws, ang=angs)
            continue
        v, ws, angs = refine_route(mask, r["pts"], search=r.get("search", 22), **kw)
        out[r["name"]] = dict(pts=v.round(1).tolist(), w=[None if w is None else round(w, 1) for w in ws],
                              ang=[None if a is None else round(a, 2) for a in angs])
    return out


def main():
    mod = importlib.import_module(sys.argv[1])
    name = sys.argv[2]
    x0, y0, x1, y1 = map(int, sys.argv[3:7])
    s = float(sys.argv[7])
    dst = sys.argv[8] if len(sys.argv) > 8 else f"work/{name}/routes_view.png"
    mask = route_mask(name)
    ref = refine_all(mod.ROUTES, mask)
    json.dump(ref, open(f"work/{name}/routes_refined.json", "w"), indent=0)
    im = cv2.imread(f"work/{name}/{name}_deskew.png")
    for i, r in enumerate(mod.ROUTES):
        c = PALETTE[i % len(PALETTE)]
        p = np.array(ref[r["name"]]["pts"])
        cv2.polylines(im, [np.round(p).astype(np.int32)], False, c, 3)
        for q in p:
            cv2.circle(im, tuple(np.round(q).astype(int)), 5, c, -1)
        m = p[len(p) // 2]
        cv2.putText(im, r["name"], (int(m[0]) + 6, int(m[1]) - 6), cv2.FONT_HERSHEY_PLAIN, 1.3, c, 2)
    crop = im[y0:y1, x0:x1]
    crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(dst, crop)
    for r in mod.ROUTES:
        rr = ref[r["name"]]
        print(r["name"], [tuple(map(lambda v: round(v), q)) for q in rr["pts"]], "w", rr.get("w"), "a", rr.get("ang"))


if __name__ == "__main__":
    main()
