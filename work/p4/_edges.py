"""Kesim kenarlari: ust kenar (golge bandinin alt ucu), alt kenar ve yan kenarlar (koyu cizgi)."""
import numpy as np
L = np.load("work/p4/_L.npy", mmap_mode="r")


def band_bottom(x, y0, y1, w=20):
    p = np.asarray(L[y0:y1, x - w:x + w]).mean(1)
    film = np.median(p[-30:])
    lo = p.min()
    thr = (film + lo) / 2
    i = int(np.argmin(p))
    j = i
    while j < len(p) - 1 and p[j] < thr:
        j += 1
    return y0 + j


def dark_line(a0, a1, b0, b1, axis):
    A = np.asarray(L[a0:a1, b0:b1]) if axis == "h" else np.asarray(L[b0:b1, a0:a1]).T
    p = A.mean(0)
    i = int(np.argmin(p))
    k = np.arange(max(i - 3, 0), min(i + 4, len(p)))
    wts = (p.max() - p[k])
    return b0 + float((k * wts).sum() / wts.sum())


print("ust kenar:", [(x, band_bottom(x, 100, 300)) for x in range(300, 1800, 150)])
print("alt kenar:", [(x, round(dark_line(x - 20, x + 20, 6800, 6920, "v"), 1)) for x in (300, 400, 500, 600, 1450, 1550, 1650, 1750)])
print("sol kenar:", [(y, round(dark_line(y, y + 60, 100, 230, "h"), 1)) for y in range(500, 6800, 500)])
print("sag kenar:", [(y, round(dark_line(y, y + 60, 1840, 1960, "h"), 1)) for y in range(500, 6800, 500)])
