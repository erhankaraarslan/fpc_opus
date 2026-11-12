"""Bir görüntünün bölgesini ızgara ve piksel koordinat etiketleriyle kaydeder.

Kullanım: python gridview.py <girdi> <cikti> <x0> <y0> <x1> <y1> <olcek> <izgara_px>
"""
import sys
import cv2

src, dst = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(int, sys.argv[3:7])
s = float(sys.argv[7])
step = int(sys.argv[8])
im = cv2.imread(src)[y0:y1, x0:x1]
im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_NEAREST)
for gx in range((x0 // step + 1) * step, x1, step):
    X = int((gx - x0) * s)
    cv2.line(im, (X, 0), (X, im.shape[0]), (0, 0, 255), 1)
    cv2.putText(im, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 0, 255), 1)
for gy in range((y0 // step + 1) * step, y1, step):
    Y = int((gy - y0) * s)
    cv2.line(im, (0, Y), (im.shape[1], Y), (255, 0, 0), 1)
    cv2.putText(im, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_PLAIN, 0.8, (255, 0, 0), 1)
cv2.imwrite(dst, im)
