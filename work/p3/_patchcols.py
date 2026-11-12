"""Yama icinde sutun bazli renk: python work/p3/_patchcols.py x0 x1 y0 y1 [ybant0 ybant1] -> her 4 px icin T/L/R ort."""
import sys
import cv2
import numpy as np
im = cv2.imread("work/p3/p3_deskew.png").astype(float)
x0, x1, y0, y1 = map(int, sys.argv[1:5])
ex = list(map(int, sys.argv[5:7])) if len(sys.argv) > 6 else None
rows = [y for y in range(y0, y1) if not (ex and ex[0] <= y < ex[1])]
sub = im[rows, x0:x1]
b, g, r = sub[:, :, 0].mean(0), sub[:, :, 1].mean(0), sub[:, :, 2].mean(0)
T, L = g - r, sub.mean(2).mean(0)
print(" ".join(f"{x0 + i}:{int(T[i])}/{int(L[i])}/{int(r[i])}" for i in range(0, x1 - x0, 4)))
