"""Taramadan bir parçayı çıkarır, eğikliği düzeltir ve hızlı renk maskelerini kaydeder.

Kullanım: python prep.py <ad>
parts/<ad>.json içindeki "kirpim_px" [x0,y0,x1,y1] (tam çözünürlüklü tarama pikseli) ve
"aci_derece" (pozitif = saat yönünün tersine döndür) kullanılır.
Açıyı bulmak için önce açı 0 ile çalıştırıp skew.py <ad> ile ölçün.
"""
import sys

import cv2
import numpy as np
import pymupdf

import cfg


def load_scan(pdf="docs/K.pdf", page=0, index=0):
    d = pymupdf.open(pdf)
    x = d.extract_image(d[page].get_images()[index][0])
    return cv2.imdecode(np.frombuffer(x["image"], np.uint8), cv2.IMREAD_COLOR)


def masks(im):
    b, g, r = [im[:, :, i].astype(int) for i in range(3)]
    teal = (g - r) > 30
    gray = (np.abs(g - r) < 18) & (np.abs(b - r) < 18) & (r < 205) & (r > 110)
    return teal, gray


def crop(c):
    x0, y0, x1, y1 = c["kirpim_px"]
    return load_scan(c["pdf"], c["sayfa"], c["goruntu_indeksi"])[y0:y1, x0:x1]


def unbend(im, b):
    """Düzlemde bükülmüş (uzun kuyruk) filmi düzeltir. b = {"xc": eksen px, "dx_noktalar": [[y, dx], ...]}:
    dx(y) eksen çizgisinin düz eksenden yanal kayması (deskew px, parçalı doğrusal). Her satır, ekseni
    xc'ye gelecek şekilde kaydırılır ve yerel eğim kadar döndürülür (yatay kenarlar eksene dik kalır)."""
    h, w = im.shape[:2]
    p = np.array(b["dx_noktalar"], float)
    ys = np.arange(h, dtype=float)
    d = np.interp(ys, p[:, 0], p[:, 1])
    s = np.gradient(d)
    X, Y = np.meshgrid(np.arange(w, dtype=np.float32), ys.astype(np.float32))
    u = X - float(b["xc"])
    mx = (X + d[:, None]).astype(np.float32)
    my = (Y - u * s[:, None]).astype(np.float32)
    return cv2.remap(im, mx, my, cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def run(ad):
    c = cfg.load(ad)
    im = crop(c)
    h, w = im.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), float(c["aci_derece"]), 1.0)
    im = cv2.warpAffine(im, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    if c.get("bukulme"):
        im = unbend(im, c["bukulme"])
    cv2.imwrite(cfg.deskew_png(ad), im)
    teal, gray = masks(im)
    vis = np.full_like(im, 255)
    vis[gray] = (120, 120, 120)
    vis[teal] = (200, 200, 0)
    cv2.imwrite(cfg.work(ad, "seg_hizli.png"), vis)
    print(ad, "deskew", im.shape)


if __name__ == "__main__":
    run(sys.argv[1])
