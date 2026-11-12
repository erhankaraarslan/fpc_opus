"""P4 rapor gorselleri: bukulme duzeltmesi, dielektrik kaymasi, kuyruk genisligi."""
import json
import cv2
import numpy as np


def plot(path, series, xlab, ylab, title, size=(900, 420), pad=60, hlines=()):
    img = np.full((size[1], size[0], 3), 255, np.uint8)
    xs = np.concatenate([np.asarray(s[0], float) for s in series])
    ys = np.concatenate([np.asarray(s[1], float) for s in series] + [np.asarray(hlines, float)])
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    y0, y1 = y0 - 0.08 * (y1 - y0 + 1e-6), y1 + 0.08 * (y1 - y0 + 1e-6)
    W, H = size[0] - 2 * pad, size[1] - 2 * pad
    P = lambda x, y: (int(pad + (x - x0) / (x1 - x0) * W), int(pad + H - (y - y0) / (y1 - y0) * H))
    cv2.rectangle(img, (pad, pad), (pad + W, pad + H), (0, 0, 0), 1)
    for k in range(6):
        xv = x0 + k * (x1 - x0) / 5; yv = y0 + k * (y1 - y0) / 5
        cv2.putText(img, f"{xv:.0f}", (P(xv, y0)[0] - 18, pad + H + 18), 0, 0.42, (0, 0, 0), 1)
        cv2.putText(img, f"{yv:.1f}", (4, P(x0, yv)[1] + 4), 0, 0.42, (0, 0, 0), 1)
    for hv in hlines:
        cv2.line(img, P(x0, hv), P(x1, hv), (180, 180, 180), 1)
    for xsr, ysr, col, mode, lab in series:
        pts = [P(a, b) for a, b in zip(xsr, ysr)]
        if mode == "line":
            cv2.polylines(img, [np.array(pts, np.int32)], False, col, 2)
        else:
            for p in pts:
                cv2.circle(img, p, 3, col, -1)
    for i, (_, _, col, _, lab) in enumerate(series):
        cv2.putText(img, lab, (pad + 10, pad + 18 + 18 * i), 0, 0.5, col, 1)
    cv2.putText(img, title, (pad, 30), 0, 0.6, (0, 0, 0), 1)
    cv2.putText(img, xlab, (pad + W // 2 - 40, size[1] - 12), 0, 0.45, (0, 0, 0), 1)
    cv2.putText(img, ylab, (pad + W - 160, pad - 8), 0, 0.45, (0, 0, 0), 1)
    cv2.imwrite(path, img)


c = json.load(open("parts/p4.json", encoding="utf-8"))
b = np.array(c["bukulme"]["dx_noktalar"], float)
# olcum noktalari (duzeltme oncesi, _bend.py): bas hatlari egimi 0.445 derece, kuyruk ortalama sapma
plot("work/p4/bukulme.png",
     [(b[:, 0], b[:, 1], (200, 0, 0), "line", "dx(y) duzeltme profili (px)"),
      (b[2:-1, 0], b[2:-1, 1], (0, 0, 220), "pt", "kuyruk 9 hat ortalama sapmasi (olcum)")],
     "y (deskew px)", "dx (px)", "P4 bukulme: eksen cizgisinin yanal kaymasi (1 px = 0.021 mm)", hlines=[0])

# kuyruk genisligi
L = np.load("work/p4/_L.npy", mmap_mode="r")
ys, ws = [], []
for y in range(6200, 12300, 100):
    pl = np.asarray(L[y:y + 40, 740:800]).mean(0); pr = np.asarray(L[y:y + 40, 1290:1345]).mean(0)
    ys.append(y); ws.append((1290 + np.argmin(pr) - 740 - np.argmin(pl)) / 47.17)
mm_y = [(y - 183) / 47.17 for y in ys]
model = [11.35 if v < 137.5 else 11.8 if v > 157.5 else 11.35 + (v - 137.5) / 20.0 * 0.45 for v in mm_y]
plot("work/p4/kuyruk_genislik.png",
     [(mm_y, ws, (0, 0, 220), "pt", "olculen kuyruk genisligi (mm)"), (mm_y, model, (200, 0, 0), "line", "cizim")],
     "y (mm)", "genislik (mm)", "P4 kuyruk genisligi: bas altinda 11.35, y>157.5 mm'de 11.8 mm")

# dielektrik kaymasi: Net1 dikey serit kesiti (ham goruntu, 4x)
im = cv2.imread("work/p4/p4_deskew.png")
crop = cv2.resize(im[2900:2960, 480:620], None, fx=5, fy=5, interpolation=cv2.INTER_NEAREST)
for x, col in [(538.3, (0, 0, 255)), (549.55, (0, 140, 0)), (503.3, (0, 140, 0)), (595.8, (0, 140, 0))]:
    X = int((x - 480) * 5)
    cv2.line(crop, (X, 0), (X, crop.shape[0]), col, 2)
cv2.putText(crop, "hat merkezi 538.3 (kirmizi) | serit 503.3-595.8, merkez 549.6 (+0.24 mm)",
            (4, 16), 0, 0.42, (0, 0, 0), 1)
cv2.imwrite("work/p4/v_diel_kayma.png", crop)
print("tamam")
