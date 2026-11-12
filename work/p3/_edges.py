import numpy as np
L = np.load("work/p3/_L.npy", mmap_mode="r")


def dark_line(a0, a1, b0, b1, axis):
    A = np.asarray(L[a0:a1, b0:b1]) if axis == "h" else np.asarray(L[b0:b1, a0:a1]).T
    p = A.mean(0)
    i = int(np.argmin(p))
    k = np.arange(max(i - 3, 0), min(i + 4, len(p)))
    wts = (p.max() - p[k])
    return round(b0 + float((k * wts).sum() / wts.sum()), 1), int(p[i])


print("sol kenar:", [(y, dark_line(y, y + 60, 80, 135, "h")) for y in range(300, 6800, 500)])
print("sag kenar:", [(y, dark_line(y, y + 60, 1795, 1870, "h")) for y in range(1500, 6800, 500)])
print("alt kenar:", [(x, dark_line(x - 20, x + 20, 6700, 6950, "v")) for x in (150, 300, 450, 1350, 1500, 1650, 1750)])
print("kuyruk sol:", [(y, dark_line(y, y + 60, 640, 730, "h")) for y in range(6000, 12700, 600)])
print("kuyruk sag:", [(y, dark_line(y, y + 60, 1200, 1290, "h")) for y in range(6000, 12700, 600)])
print("yarik dis sol:", [(y, dark_line(y, y + 60, 540, 640, "h")) for y in range(6000, 6800, 150)])
print("yarik dis sag:", [(y, dark_line(y, y + 60, 1290, 1400, "h")) for y in range(6000, 6800, 150)])
