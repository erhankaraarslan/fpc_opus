"""P4 bukulme analizi: hat merkezlerinin y'ye gore x kaymasi."""
import sys
import cv2, numpy as np
sys.path.insert(0, ".devin/skills/fpc-vektor/scripts")
from measure import edges
T = np.load(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".npy") else "work/p4/_T.npy", mmap_mode="r")


def centers(y, x0, x1, thr=40, h=40):
    p = cv2.GaussianBlur(np.asarray(T[y:y + h, x0:x1]).mean(0).reshape(1, -1), (0, 0), 1.0).ravel()
    e = [(x + x0, s) for x, s in edges(p, thr)]
    return [((a + b) / 2, b - a) for (a, sa), (b, sb) in zip(e, e[1:]) if sa == "-" and sb == "+"]


def track(name, x_init, y0, y1, st, win=30, wmax=36):
    pts = []
    x = x_init
    for y in range(y0, y1, st):
        c = [cx for cx, w in centers(y, int(x - win), int(x + win)) if 16 < w < wmax]
        if c:
            cx = min(c, key=lambda v: abs(v - x))
            if abs(cx - x) < 8:
                pts.append((y + 20, cx)); x = cx
    a = np.array(pts)
    k, b = np.polyfit(a[:, 0], a[:, 1], 1)
    res = a[:, 1] - (k * a[:, 0] + b)
    print(f"{name}: n={len(a)} y {a[0,0]:.0f}-{a[-1,0]:.0f} egim={np.degrees(np.arctan(k)):.3f} deg  x@y0={a[0,1]:.1f} x@y1={a[-1,1]:.1f} art.max={np.abs(res).max():.1f}")
    return a


if __name__ == "__main__":
    track("bas_sol", 540, 2250, 3500, 50)
    track("bas_sag", 1538.6, 2250, 3500, 50)
    for x in (824.5, 919, 1014.5, 1222):
        track(f"bas_alt_{x:.0f}", x, 4300, 5960, 50)
    allp = []
    for i, x in enumerate((799, 847, 893, 941, 989, 1036, 1178, 1225, 1273)):
        allp.append(track(f"kuyruk_{i}", x, 6250, 12380, 50))
    # kuyruk ortalama merkez, 300 px bantlarda
    ys = np.arange(6250, 12400, 300)
    print("kuyruk ortalama merkez (9 hat) ve yerel egim:")
    prev = None
    for y in ys:
        v = [np.interp(y, a[:, 0], a[:, 1]) - a[:, 1].mean() for a in allp]
        m = np.mean(v)
        print(f"  y={y} sapma={m:+.2f}" + (f" egim={np.degrees(np.arctan((m - prev) / 300)):+.3f}" if prev is not None else ""))
        prev = m
