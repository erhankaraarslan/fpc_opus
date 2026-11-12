"""Gümüş maskesinde yatay / dikey / 45° hat segmentlerini morfolojik açma ile bulur.

Kullanım: python segfind.py <ad> <maske.npy>[,..] <y0> <y1> [min_uzunluk]
Çıktı: konsol listesi + work/<ad>/segs.json + work/<ad>/segs_vis.png
"""
import json
import sys

import cv2
import numpy as np


def line_kernel(L, ang):
    L = L | 1
    k = np.zeros((L, L), np.uint8)
    c = L // 2
    dx, dy = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    for t in np.linspace(-c, c, 4 * L):
        k[int(round(c + t * dy)), int(round(c + t * dx))] = 1
    return k


def main():
    name = sys.argv[1]
    m = None
    for p in sys.argv[2].split(","):
        a = np.load(p)
        m = a if m is None else (m | a)
    y0, y1 = int(sys.argv[3]), int(sys.argv[4])
    Lmin = int(sys.argv[5]) if len(sys.argv) > 5 else 45
    m = m.copy()
    m[:y0] = False
    m[y1:] = False
    m8 = m.astype(np.uint8)
    segs = []
    vis = cv2.imread(f"work/{name}/{name}_deskew.png")
    cols = {0: (0, 0, 255), 90: (255, 0, 0), 45: (0, 160, 0), 135: (0, 160, 160)}
    for ang in (0, 90, 45, 135):
        o = cv2.morphologyEx(m8, cv2.MORPH_OPEN, line_kernel(Lmin, ang))
        n, lab, st, _ = cv2.connectedComponentsWithStats(o, 8)
        d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        nrm = np.array([-d[1], d[0]])
        for i in range(1, n):
            ys, xs = np.nonzero(lab == i)
            P = np.c_[xs, ys].astype(float)
            t = P @ d
            s = P @ nrm
            # yalnızca hat kalınlığında olanlar
            length = t.max() - t.min()
            # genişlik: her t dilimindeki s yayılımı
            tb = np.round(t / 3).astype(int)
            ws = []
            cs = []
            for k in np.unique(tb):
                ss = s[tb == k]
                ws.append(ss.max() - ss.min() + 1)
                cs.append((ss.max() + ss.min()) / 2)
            w = float(np.median(ws))
            if length < Lmin or w > 70:
                continue
            c = float(np.median(cs))
            p0 = d * t.min() + nrm * c
            p1 = d * t.max() + nrm * c
            segs.append(dict(ang=ang, p0=p0.round(1).tolist(), p1=p1.round(1).tolist(), w=round(w, 1), len=round(float(length), 1)))
            cv2.line(vis, tuple(p0.astype(int)), tuple(p1.astype(int)), cols[ang], 3)
    for i, s in enumerate(segs):
        s["id"] = i
        mid = ((np.array(s["p0"]) + np.array(s["p1"])) / 2).astype(int)
        cv2.putText(vis, str(i), tuple(mid + 4), cv2.FONT_HERSHEY_PLAIN, 1.6, (0, 0, 0), 2)
        print(f'{i:3d} a={s["ang"]:3d} p0=({s["p0"][0]:7.1f},{s["p0"][1]:7.1f}) p1=({s["p1"][0]:7.1f},{s["p1"][1]:7.1f}) w={s["w"]:5.1f} L={s["len"]:6.1f}')
    json.dump(segs, open(f"work/{name}/segs.json", "w"))
    cv2.imwrite(f"work/{name}/segs_vis.png", vis)


if __name__ == "__main__":
    main()
