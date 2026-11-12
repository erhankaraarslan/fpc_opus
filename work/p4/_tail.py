import cv2, numpy as np, sys
sys.path.insert(0, ".devin/skills/fpc-vektor/scripts")
from measure import edges
im = cv2.imread("work/p4/p4_deskew.png").astype(float)
np.save("work/p4/_L.npy", im.mean(2).astype(np.float32))
np.save("work/p4/_T.npy", (im[:, :, 1] - im[:, :, 2]).astype(np.float32))
T = im[:, :, 1] - im[:, :, 2]
for y in range(7000, 12400, 400):
    p = cv2.GaussianBlur(T[y:y + 60, 740:1340].mean(0).reshape(1, -1), (0, 0), 1.0).ravel()
    e = [(x + 740, s) for x, s in edges(p, 43)]
    segs = [(e[i][0], e[i + 1][0]) for i in range(len(e) - 1) if e[i][1] == "-" and e[i + 1][1] == "+"]
    c = [round((a + b) / 2, 1) for a, b in segs]
    w = [round(b - a, 1) for a, b in segs]
    print(y, "kenar", e[0][0] if e else None, e[-1][0] if e else None, "merkez", c, "gen", w)
