"""m_dark + LED etiketli okuma karolari: python work/p3/_tiles.py x0 y0 x1 y1 olcek izgara cikti [rota]"""
import importlib
import sys
import cv2
import numpy as np
sys.path.insert(0, "parts")
LEDS = {f"L{i + 1}": (x, y) for i, (x, y) in enumerate([(332.0, 1578.6), (333.0, 2172.0), (332.4, 2768.3), (330.8, 3366.4),
                                                        (337.4, 4279.3), (334.1, 4877.1), (334.7, 5477.7), (333.3, 6078.1)])}
LEDS.update({f"R{i + 1}": (x, y) for i, (x, y) in enumerate([(1587.8, 1570.1), (1589.8, 2171.6), (1589.0, 2768.4), (1590.6, 3371.3),
                                                             (1596.9, 4275.5), (1592.3, 4872.3), (1591.4, 5473.5), (1591.6, 6074.7)])})
LEDS.update({"C1": (1002.3, 2316.5), "B1": (700.2, 3042.9), "B2": (1006.7, 3045.1), "B3": (1307.6, 3046.3)})
x0, y0, x1, y1 = map(int, sys.argv[1:5])
s, g, out = float(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
im = cv2.imread("work/p3/p3_deskew.png")[y0:y1, x0:x1].copy()
m = np.load("work/p3/m_dark.npy", mmap_mode="r")[y0:y1, x0:x1]
und = np.load("work/p3/m_under.npy", mmap_mode="r")[y0:y1, x0:x1]
v = (im * 0.35 + 165).astype(np.uint8)
v[np.asarray(m)] = (v[np.asarray(m)] * 0.45).astype(np.uint8)
v[np.asarray(und)] = (150, 90, 20)
v = cv2.resize(v, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
for gx in range((x0 // g + 1) * g, x1, g):
    X = int((gx - x0) * s); cv2.line(v, (X, 0), (X, v.shape[0]), (180, 180, 255), 1)
    if gx % (2 * g) == 0:
        cv2.putText(v, str(gx), (X + 2, 12), 0, 0.38, (0, 0, 200), 1)
for gy in range((y0 // g + 1) * g, y1, g):
    Y = int((gy - y0) * s); cv2.line(v, (0, Y), (v.shape[1], Y), (180, 180, 255), 1)
    if gy % (2 * g) == 0:
        cv2.putText(v, str(gy), (2, Y - 2), 0, 0.38, (0, 0, 200), 1)
for n, (cx, cy) in LEDS.items():
    if x0 <= cx < x1 and y0 <= cy < y1:
        P = (int((cx - x0) * s), int((cy - y0) * s))
        cv2.circle(v, P, 4, (0, 0, 255), -1); cv2.putText(v, n, (P[0] + 5, P[1] - 5), 0, 0.5, (0, 0, 255), 1)
if len(sys.argv) > 8:
    import json
    ref = json.load(open("work/p3/routes_refined.json"))
    for k, r in ref.items():
        p = (np.array(r["pts"]) - [x0, y0]) * s
        cv2.polylines(v, [np.round(p).astype(np.int32)], False, (0, 160, 0), 2)
        mp = p[len(p) // 2]
        if 0 <= mp[0] < v.shape[1] and 0 <= mp[1] < v.shape[0]:
            cv2.putText(v, k, (int(mp[0]) + 3, int(mp[1]) + 12), 0, 0.42, (0, 110, 0), 1)
cv2.imwrite(out, v)
