"""P3 okuma maskesi: yerel arka plana gore koyu + turkuaz olmayan (bulanik bolgelerde doku esigi calismiyor)."""
import cv2
import numpy as np
from skimage import morphology
L = np.load("work/p3/_L.npy")
T = np.load("work/p3/_T.npy")
im = cv2.imread("work/p3/p3_deskew.png")
sat = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.int16)
bg = cv2.GaussianBlur(cv2.dilate(L, np.ones((61, 61), np.uint8)), (0, 0), 15)
d = bg - L
m = (d > 30) & (T < 15) & (sat < 45)
m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))).astype(bool)
m = morphology.remove_small_objects(m, 600)
und = np.load("work/p3/m_under.npy")
np.save("work/p3/m_dark.npy", m | und)
for y0 in (1350, 3150, 4950):
    v = np.full((1850, 1700, 3), 255, np.uint8)
    v[m[y0:y0 + 1850, 120:1820]] = (70, 70, 70)
    v[und[y0:y0 + 1850, 120:1820]] = (140, 90, 0)
    for g in range(0, 1850, 100):
        cv2.line(v, (0, g), (1699, g), (200, 200, 255), 1); cv2.putText(v, str(y0 + g), (2, g + 14), 0, 0.5, (0, 0, 255), 1)
    for g in range(0, 1700, 100):
        cv2.line(v, (g, 0), (g, 1849), (200, 200, 255), 1); cv2.putText(v, str(120 + g), (g + 2, 14), 0, 0.5, (0, 0, 255), 1)
    cv2.imwrite(f"work/p3/m_dark_{y0}.png", cv2.resize(v, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
