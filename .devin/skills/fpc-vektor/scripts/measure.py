"""Yatay/dikey yoğunluk profillerinden kenar konumlarını alt-piksel hassasiyette ölçer.

Kullanım:
  python measure.py <ad> h <y0> <y1> <x0> <x1>   # satırlar boyunca ortalama al, x kenarlarını bul
  python measure.py <ad> v <x0> <x1> <y0> <y1>   # sütunlar boyunca ortalama al, y kenarlarını bul
"""
import sys
import cv2
import numpy as np


def channels(im):
    f = im.astype(float)
    b, g, r = f[:, :, 0], f[:, :, 1], f[:, :, 2]
    return {"L": f.mean(2), "T": g - r}


def edges(p, thr):
    s = p > thr
    out = []
    for i in range(1, len(p)):
        if s[i] != s[i - 1]:
            x = i - 1 + (thr - p[i - 1]) / (p[i] - p[i - 1])
            out.append((round(x, 1), "+" if s[i] else "-"))
    return out


def main():
    name, mode = sys.argv[1], sys.argv[2]
    a0, a1, b0, b1 = map(int, sys.argv[3:7])
    ch = channels(cv2.imread(f"work/{name}/{name}_deskew.png"))
    for k, c in ch.items():
        reg = c[a0:a1, b0:b1] if mode == "h" else c[b0:b1, a0:a1].T
        p = cv2.GaussianBlur(reg.mean(0).reshape(1, -1), (0, 0), 1.0).ravel()
        lo, hi = np.percentile(p, 5), np.percentile(p, 95)
        thr = (lo + hi) / 2
        e = [(round(x + b0, 1), s) for x, s in edges(p, thr)]
        print(f"{k}: lo={lo:.0f} hi={hi:.0f} thr={thr:.0f} edges={e}")


if __name__ == "__main__":
    main()
