import sys
import cv2, numpy as np
sys.path.insert(0, ".devin/skills/fpc-vektor/scripts")
from measure import edges
T = np.load("work/p4/_T.npy", mmap_mode="r")
y0, y1, st, x0, x1 = map(int, sys.argv[1:6])
thr = float(sys.argv[6]) if len(sys.argv) > 6 else 40
for y in range(y0, y1, st):
    p = cv2.GaussianBlur(np.asarray(T[y:y + 40, x0:x1]).mean(0).reshape(1, -1), (0, 0), 1.0).ravel()
    e = [(x + x0, s) for x, s in edges(p, thr)]
    segs = [(e[i][0], e[i + 1][0]) for i in range(len(e) - 1) if e[i][1] == "-" and e[i + 1][1] == "+"]
    print(y + 20, " ".join(f"{(a + b) / 2:.1f}/{b - a:.0f}" for a, b in segs))
