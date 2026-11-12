import sys
import numpy as np
sys.path.insert(0, "work/p4")
from _bend import track
L = np.load("work/p4/_L.npy", mmap_mode="r")
idx = [0, 1, 2, 3, 4, 5, 8, 9, 10]
xs = []
for i, x in zip(idx, (803, 851, 897, 945, 993, 1040, 1182, 1229, 1278)):
    a = track(f"poz{i}", x, 7000, 12300, 50)
    xs.append(np.median(a[:, 1]))
k, b = np.polyfit(idx, xs, 1)
print("adim px", round(k, 3), "poz5 merkez", round(b + 5 * k, 2), "artik", np.round(np.array(xs) - (k * np.array(idx) + b), 2))
# kuyruk film kenarlari (L minimumu)
for y in range(7000, 12700, 700):
    pl = np.asarray(L[y:y + 60, 700:800]).mean(0); pr = np.asarray(L[y:y + 60, 1280:1380]).mean(0)
    print("y", y, "sol kenar", 700 + int(np.argmin(pl)), int(pl.min()), "sag kenar", 1280 + int(np.argmin(pr)), int(pr.min()))
