"""Maske uzerinde dikey hat izleme: track(mask, x, y0, y1, st) -> [(y, x)], egim."""
import numpy as np


def runs(v):
    out, s = [], None
    for i, b in enumerate(v):
        if b and s is None:
            s = i
        elif not b and s is not None:
            out.append((s, i)); s = None
    if s is not None:
        out.append((s, len(v)))
    return out


def track(M, name, x, y0, y1, st=50, win=30, h=40, wmin=12, wmax=40, frac=0.5, quiet=False):
    pts = []
    for y in range(y0, y1, st):
        a = int(x - win)
        p = np.asarray(M[y:y + h, a:int(x + win)]).mean(0) > frac
        c = [(a + (s + e - 1) / 2, e - s) for s, e in runs(p) if wmin <= e - s <= wmax]
        if c:
            cx = min(c, key=lambda v: abs(v[0] - x))[0]
            if abs(cx - x) < 8:
                pts.append((y + h / 2, cx)); x = cx
    A = np.array(pts)
    if len(A) < 3:
        print(name, "yetersiz"); return A
    k, b = np.polyfit(A[:, 0], A[:, 1], 1)
    res = A[:, 1] - (k * A[:, 0] + b)
    if not quiet:
        print(f"{name}: n={len(A)} y {A[0,0]:.0f}-{A[-1,0]:.0f} egim={np.degrees(np.arctan(k)):.3f}  x0={A[0,1]:.1f} x1={A[-1,1]:.1f} "
              f"medyan={np.median(A[:,1]):.1f} art.max={np.abs(res).max():.1f}")
    return A
