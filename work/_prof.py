"""Hizli profil: python work/_prof.py <ad> h|v a0 a1 b0 b1 [L|T] [adim]
h: satir a0..a1 ortalamasi, x=b0..b1 profili; v: sutun a0..a1 ortalamasi, y=b0..b1 profili."""
import os, sys
import cv2, numpy as np
ad, mode = sys.argv[1], sys.argv[2]
a0, a1, b0, b1 = map(int, sys.argv[3:7])
ch = sys.argv[7] if len(sys.argv) > 7 else "L"
st = int(sys.argv[8]) if len(sys.argv) > 8 else 2
f = f"work/{ad}/_{ch}.npy"
if not os.path.exists(f):
    im = cv2.imread(f"work/{ad}/{ad}_deskew.png").astype(float)
    np.save(f"work/{ad}/_L.npy", im.mean(2).astype(np.float32))
    np.save(f"work/{ad}/_T.npy", (im[:, :, 1] - im[:, :, 2]).astype(np.float32))
A = np.load(f, mmap_mode="r")
p = A[a0:a1, b0:b1].mean(0) if mode == "h" else A[b0:b1, a0:a1].mean(1)
print(" ".join(f"{b0 + i}:{int(v)}" for i, v in enumerate(p) if i % st == 0))
i = int(np.argmin(p)); print("min", b0 + i, int(p[i]))
