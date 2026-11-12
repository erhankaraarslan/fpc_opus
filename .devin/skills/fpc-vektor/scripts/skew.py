"""Parça kırpımındaki gümüş hatların eksenlerden sapma açısını ölçer (deskew öncesi).

Kullanım: python skew.py <ad>        (parts/<ad>.json kirpim_px kullanılır, aci_derece yok sayılır)
Çıktı: prep.py için "aci_derece" önerisi. Hough doğrularının eksene göre ağırlıklı ortalama sapması.
Pozitif değer: hatlar saat yönünde dönük -> aci_derece = +değer ile düzeltilir.
"""
import sys

import cv2
import numpy as np

import cfg
from prep import crop, masks


def measure(im):
    _, gray = masks(im)
    m = cv2.morphologyEx((gray * 255).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    L = cv2.HoughLinesP(m, 1, np.pi / 3600, 200, minLineLength=300, maxLineGap=10)
    a = []
    for xa, ya, xb, yb in (L[:, 0] if L is not None else []):
        t = np.degrees(np.arctan2(yb - ya, xb - xa))
        d = ((t + 45) % 90) - 45
        if abs(d) < 5:
            a.append((d, np.hypot(xb - xa, yb - ya)))
    a = np.array(a)
    return len(a), float(np.average(a[:, 0], weights=a[:, 1])), float(np.median(a[:, 0]))


if __name__ == "__main__":
    n, wavg, med = measure(crop(cfg.load(sys.argv[1])))
    print(f"cizgi={n} agirlikli={wavg:.3f} medyan={med:.3f}  -> onerilen aci_derece={wavg:.2f}")
