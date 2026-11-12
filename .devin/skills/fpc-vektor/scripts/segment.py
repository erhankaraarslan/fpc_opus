"""Tuş devresi (P2/P4 tipi) maskeleri: gümüş, dielektrik ve doğrulama referansları.

Kullanım: python segment.py <ad>
Çıktılar (work/<ad>/):
  silver.npy        yerel arka plana göre koyu + düşük doygunluk (ped/kontak bölgeleri)
  tealm.npy         dielektrik (g - r > 30)
  teal_closed.npy   dielektrik + altındaki gümüş (45 px kapama) -> doğrulama referansı
  sil_teal.npy      dielektrik şeritleri içindeki gümüş (hat merkez çizgisi ölçümü için)
  silver_ref.npy    gümüş doğrulama referansı
  seg3.png          görsel
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
    bg = cv2.dilate(cv2.GaussianBlur(L, (0, 0), 3), ell(81))
    silver = clean((L < bg - 22) & (sat < 45), 5, 7, 250, 2000)
    teal = clean(T > 30, 7, 7, 300, 3000)
    tc = cv2.morphologyEx(teal.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((45, 45), np.uint8)).astype(bool)
    st = tc & (T < 22) & (~teal)
    st = cv2.morphologyEx(st.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8)).astype(bool)
    st = morphology.remove_small_objects(st, 1500)
    a = tc & (T < 20) & (~teal)
    bb = (~tc) & (L < bg - 22) & (L > bg - 48) & (sat < 45)
    ref = cv2.morphologyEx((a | bb).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    ref = morphology.remove_small_objects(morphology.remove_small_holes(ref, 150), 800)
    for k, v in dict(silver=silver, tealm=teal, teal_closed=tc, sil_teal=st, silver_ref=ref).items():
        np.save(cfg.work(ad, f"{k}.npy"), v)
    vis = np.full_like(im, 255)
    vis[teal] = (200, 200, 0)
    vis[ref] = (80, 80, 80)
    cv2.imwrite(cfg.work(ad, "seg3.png"), vis)
    print(ad, "maskeler yazildi")


if __name__ == "__main__":
    run(sys.argv[1])
