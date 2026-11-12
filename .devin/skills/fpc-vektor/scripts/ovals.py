"""Oval (stadium) delikleri kenar gölge piksellerine robust fit ile ölçer.

Kullanım: python ovals.py <ad>   (kutular parts/<ad>.json "oval_kutulari": [[x0,y0,x1,y1], ...] deskew px)
Çıktı: merkez (x, y), genişlik, yükseklik [px] ve fit hatası
"""
import sys

import cv2
import numpy as np
from scipy.optimize import least_squares

import cfg

def stadium_dist(p, pts):
    cx, cy, w, h = p
    r = w / 2
    half = max(h / 2 - r, 0)
    dx = pts[:, 0] - cx
    dy = np.clip(np.abs(pts[:, 1] - cy) - half, 0, None)
    return np.hypot(dx, dy) - r


def edge_mask(im):
    f = im.astype(float)
    L = f.mean(2)
    T = f[:, :, 1] - f[:, :, 2]
    bg = cv2.dilate(cv2.GaussianBlur(L, (0, 0), 2), np.ones((31, 31)))
    return (L < bg - 30) & (T < 20)


def run(name):
    E = edge_mask(cv2.imread(cfg.deskew_png(name)))
    M = 25
    out = []
    for (x0, y0, x1, y1) in cfg.load(name)["oval_kutulari"]:
        ys, xs = np.nonzero(E[y0 - M:y1 + M, x0 - M:x1 + M])
        pts = np.c_[xs + x0 - M, ys + y0 - M].astype(float)
        p0 = [(x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0]
        # yalnızca başlangıç sınırına yakın pikseller
        pts = pts[np.abs(stadium_dist(p0, pts)) < 20]
        r = least_squares(lambda p: stadium_dist(p, pts), p0, loss="soft_l1", f_scale=2.0)
        res = np.abs(stadium_dist(r.x, pts))
        inl = pts[res < 4]
        r = least_squares(lambda p: stadium_dist(p, inl), r.x, loss="soft_l1", f_scale=1.0)
        cx, cy, w, h = r.x
        rms = np.sqrt(np.mean(stadium_dist(r.x, inl) ** 2))
        out.append((cx, cy, w, h))
        print(f"oval cx={cx:7.1f} cy={cy:7.1f} w={w:6.1f} h={h:6.1f} n={len(inl)} rms={rms:.2f}")
    np.save(cfg.work(name, "ovals.npy"), np.array(out))


if __name__ == "__main__":
    run(sys.argv[1])
