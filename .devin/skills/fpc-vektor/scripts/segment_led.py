"""LED devreleri (P1/P3 tipi) maskeleri: üst gümüş, alt gümüş (dielektrik altında), dielektrik.

Kullanım: python segment_led.py <ad>
Çıktılar (work/<ad>/):
  m_top.npy    dokulu gümüş (dielektrik dışı ve dielektrik üstü köprüler). Gölge kopyaları
               pürüzsüz olduğu için doku (yüksek frekans) eşiğiyle elenir.
  m_under.npy  dielektrik altında kalan gümüş (turkuaz içinde koyu, R < 82)
  m_teal.npy   dielektrik (g - r > 35)
  tex.npy      doku haritası (teşhis için)
  seg_led.png  görsel
"""
import sys

import cv2
import numpy as np
from skimage import morphology

import cfg


def ell(k):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))


def clean(m, close_k, open_k, hole, obj):
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, ell(close_k)).astype(bool)
    m = morphology.remove_small_holes(m, hole)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, ell(open_k)).astype(bool)
    return morphology.remove_small_objects(m, obj)


def run(ad):
    im = cv2.imread(cfg.deskew_png(ad))
    f = im.astype(float)
    b, g, r = f[:, :, 0], f[:, :, 1], f[:, :, 2]
    L = f.mean(2)
    T = g - r
    sat = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[:, :, 1].astype(int)
    hp = np.abs(L - cv2.GaussianBlur(L, (0, 0), 2.0))
    tex = cv2.blur(hp, (9, 9))
    teal = clean(T > 35, 7, 7, 400, 2500)
    under = clean(teal & (r < 82), 5, 7, 200, 600)
    top = clean((L > 185) & (L < 208) & (T < 15) & (sat < 45) & (tex > 3.2), 5, 7, 200, 400)
    # Koyuluk maskesi: film kalkık/bulanık bölgelerde doku eşiği çalışmaz; yerel arka plana göre koyu,
    # turkuaz olmayan pikseller (gölge kopyalarını da içerir; okuma, refine ve doğrulama için seçilebilir)
    bg = cv2.GaussianBlur(cv2.dilate(L.astype(np.float32), np.ones((61, 61), np.uint8)), (0, 0), 15)
    dark = (bg - L > 30) & (T < 15) & (sat < 45)
    dark = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_OPEN, ell(7)).astype(bool)
    dark = morphology.remove_small_objects(dark, 600) | under
    # Bant maskesi: koyuluk maskesinden gölge çekirdeği (L < 178) ve koyu kenarlar ayıklanmış (doğrulama için)
    band = dark & (L >= 178) & (L <= 218) & (T < 15)
    band = cv2.morphologyEx(band.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool) | under
    for k, v in dict(teal=teal, under=under, top=top, dark=dark, band=band).items():
        np.save(cfg.work(ad, f"m_{k}.npy"), v)
    np.save(cfg.work(ad, "tex.npy"), tex.astype(np.float32))
    vis = np.full_like(im, 255)
    vis[teal] = (210, 210, 60)
    vis[under] = (90, 60, 0)
    vis[top] = (70, 70, 70)
    cv2.imwrite(cfg.work(ad, "seg_led.png"), vis)
    print(ad, "LED maskeleri yazildi")


if __name__ == "__main__":
    run(sys.argv[1])
