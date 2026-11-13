"""Ön + arka yüz taramalarını çakıştırma (arka tarama -> ön deskew koordinatları).

Kullanım: python kayit.py <ad>     (veya fpc.py kayit <ad>; önce fpc.py prep <ad>)
parts/<ad>.json:
  "arka": {"pdf": "docs/K_arka.pdf", "sayfa": 0, "goruntu_indeksi": 0, "kirpim_px": [x0, y0, x1, y1],
           "ayna": "yatay",          # film ters çevrilip tarandıysa: "yatay" (sol-sağ) | "dikey" | null
           "aci_derece": 0.0}        # isteğe bağlı kaba döndürme (ön taramadaki gibi; ECC kalanı bulur)
Çıktılar (work/<ad>/):
  <ad>_arka.png       ön deskew görüntüsüyle piksel piksel hizalı arka görüntü (aynalanmış)
  kayit.json          afin matris, ölçek, dönme, ECC korelasyonu, yerel artık (karo bazında, px)
  kayit_kontrol.png   kırmızı = ön, yeşil = arka yapı haritası (sarı = örtüşme)
Neden: PET saydamdır; arkadan bakınca 1. gümüş baskı dielektrik ve köprüler tarafından örtülmeden görünür.
Köprü (üst/alt) kararları, dielektrik altı hatlar ve LED kaplaması altındaki pedler arka görüntüden okunur.
Yöntem: yapı haritası = Gauss yumuşatılmış parlaklığın gradyan genliği (iki yüzde kontrast/renk farklı olduğu için
yoğunluk değil yapı eşleştirilir) -> 1/4 ölçekte faz korelasyonu (kaba öteleme) -> 1/4, 1/2, 1/1 ölçek ECC afin
(cv2.findTransformECC) -> karo bazında ECC öteleme artığı (film iki tarama arasında yerel olarak deforme olmuş mu?).
"""
import json
import math
import sys

import cv2
import numpy as np

import cfg


def yapi(im):
    L = im.astype(np.float32).mean(2) if im.ndim == 3 else im.astype(np.float32)
    Ls = cv2.GaussianBlur(L, (0, 0), 1.5)
    g = cv2.magnitude(cv2.Sobel(Ls, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(Ls, cv2.CV_32F, 0, 1, ksize=3))
    return g / (np.percentile(g, 99) + 1e-6)


def _pad(a, H, W):
    out = np.zeros((H, W), np.float32)
    out[:a.shape[0], :a.shape[1]] = a[:H, :W]
    return out


def kaydet_goruntu(on, arka, ayna=None, aci=0.0, olcekler=(0.25, 0.5, 1.0), iter_=(200, 100, 40)):
    """arka -> on afin hizalama. Dönüş: dict(warp (2x3, on koordinatından arka koordinatına), hizali, ecc)."""
    if ayna == "yatay":
        arka = cv2.flip(arka, 1)
    elif ayna == "dikey":
        arka = cv2.flip(arka, 0)
    if aci:
        h, w = arka.shape[:2]
        arka = cv2.warpAffine(arka, cv2.getRotationMatrix2D((w / 2, h / 2), aci, 1.0), (w, h), flags=cv2.INTER_CUBIC,
                              borderValue=(255, 255, 255) if arka.ndim == 3 else 255)
    H, W = on.shape[:2]
    A, B = yapi(on), _pad(yapi(arka), H, W)
    f0 = olcekler[0]
    a0 = cv2.resize(A, None, fx=f0, fy=f0, interpolation=cv2.INTER_AREA)
    b0 = cv2.resize(B, None, fx=f0, fy=f0, interpolation=cv2.INTER_AREA)
    win = cv2.createHanningWindow(a0.shape[::-1], cv2.CV_32F)
    (dx, dy), _ = cv2.phaseCorrelate(a0, b0, win)
    warp = np.array([[1, 0, dx / f0], [0, 1, dy / f0]], np.float32)
    ecc = 0.0
    for f, it in zip(olcekler, iter_):
        a = cv2.resize(A, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f != 1 else A
        b = cv2.resize(B, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f != 1 else B
        w = warp.copy()
        w[:, 2] *= f
        try:
            ecc, w = cv2.findTransformECC(a, b, w, cv2.MOTION_AFFINE,
                                          (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, it, 1e-6), None, 5)
        except cv2.error:
            break
        w[:, 2] /= f
        warp = w
    full = np.full((H, W, 3) if arka.ndim == 3 else (H, W), 255, arka.dtype)
    full[:min(H, arka.shape[0]), :min(W, arka.shape[1])] = arka[:H, :W]
    hiz = cv2.warpAffine(full, warp, (W, H), flags=cv2.INTER_CUBIC + cv2.WARP_INVERSE_MAP,
                         borderValue=(255, 255, 255) if full.ndim == 3 else 255)
    return dict(warp=warp, hizali=hiz, ecc=float(ecc), A=A, B=yapi(hiz))


def yerel_artik(A, B, karo=600):
    """Karo bazında kalan öteleme (px): hizalama sonrası yerel deformasyon."""
    out = []
    H, W = A.shape
    for y in range(0, H - karo + 1, karo):
        for x in range(0, W - karo + 1, karo):
            a, b = A[y:y + karo, x:x + karo], B[y:y + karo, x:x + karo]
            if a.std() < 0.05 or b.std() < 0.05:
                continue
            (dx, dy), r = cv2.phaseCorrelate(a, b, cv2.createHanningWindow((karo, karo), cv2.CV_32F))
            if r > 0.05:
                out.append([x, y, round(float(dx), 2), round(float(dy), 2), round(float(r), 3)])
    return out


def run(ad):
    import prep
    c = cfg.load(ad)
    a = c.get("arka")
    if not a:
        raise SystemExit(f"parts/{ad}.json içinde 'arka' tanımı yok (kayit.py belgesine bakın)")
    x0, y0, x1, y1 = a["kirpim_px"]
    arka = prep.load_scan(a["pdf"], a.get("sayfa", 0), a.get("goruntu_indeksi", 0))[y0:y1, x0:x1]
    on = cv2.imread(cfg.deskew_png(ad))
    R = kaydet_goruntu(on, arka, a.get("ayna", "yatay"), float(a.get("aci_derece", 0.0)))
    w = R["warp"]
    olc = math.sqrt(abs(np.linalg.det(w[:, :2])))
    don = math.degrees(math.atan2(w[1, 0], w[0, 0]))
    art = yerel_artik(R["A"], R["B"])
    mag = [math.hypot(r[2], r[3]) for r in art]
    J = dict(warp=w.tolist(), olcek=olc, donme_derece=don, ecc=R["ecc"], yerel_artik=art,
             yerel_artik_medyan_px=float(np.median(mag)) if mag else None, yerel_artik_maks_px=float(max(mag)) if mag else None)
    cv2.imwrite(cfg.work(ad, f"{ad}_arka.png"), R["hizali"])
    json.dump(J, open(cfg.work(ad, "kayit.json"), "w"), indent=1)
    f = min(1.0, 2400.0 / max(on.shape[:2]))
    k = np.zeros((*on.shape[:2], 3), np.uint8)
    k[..., 2] = np.clip(R["A"] * 255, 0, 255)
    k[..., 1] = np.clip(R["B"] * 255, 0, 255)
    cv2.imwrite(cfg.work(ad, "kayit_kontrol.png"), cv2.resize(k, None, fx=f, fy=f, interpolation=cv2.INTER_AREA))
    print(f"{ad} kayit: ECC {R['ecc']:.3f}, ölçek {olc:.5f}, dönme {don:+.3f}°, yerel artık medyan "
          f"{J['yerel_artik_medyan_px']} / maks {J['yerel_artik_maks_px']} px ({len(art)} karo)")
    if olc and abs(olc - 1) > 0.003:
        print("  UYARI: iki tarama arasında ölçek farkı > %0.3 (tarayıcı/film genleşmesi); ölçeği iki yüzde ayrı kalibre edin")
    return J


if __name__ == "__main__":
    run(sys.argv[1])
