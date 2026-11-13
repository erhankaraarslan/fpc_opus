"""Gölge kopyası modeli: yerel gölge ofseti δ(x, y), tahmini gölge maskesi ve film kalkıklık haritası.

Kullanım: python golge.py <ad>      (fpc.py segment sonrası otomatik; tek başına: fpc.py golge <ad>)
Çıktılar (work/<ad>/):
  m_golge.npy      gölge olarak açıklanan pikseller (gümüşün δ yukarı kopyası, gümüş dışı, koyu)
  golge.json       karo ızgarası: δ (px), örnek sayısı, genel medyan; kalkık (δ büyük) bölgeler
  golge_haritasi.png  δ ısı haritası (mm) taramanın üstünde

Fizik: film camdan kalkıksa opak gümüşün kopyası tarayıcı kapağına düşer; tarama yönünde ışık eğik
geldiği için kopya hep gerçek şeklin δ px YUKARISINDADIR. δ kalkma yüksekliğiyle orantılıdır; büyük δ =
o bölgede kenarlar daha bulanık ve gölge daha geniş (ölçüm güvenilirliği düşük).
Kestirim: dokulu gümüş (S) yatay hatlarının (dikey koşu 14–40 px) üst kenarında, hemen üstteki koyu ve
dokusuz bandın (D, ≤ 4 px parlak boşluk toleranslı) kalınlığı ölçülür; karo başına medyan = δ.
"""
import json
import sys

import cv2
import numpy as np

import cfg

KARO = 500
MIN_ORNEK = 40


def maskeler(im):
    f = im.astype(np.float32)
    L, T = f.mean(2), f[:, :, 1] - f[:, :, 2]
    sat = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[:, :, 1]
    tex = cv2.blur(np.abs(L - cv2.GaussianBlur(L, (0, 0), 2)), (9, 9))
    bg = cv2.GaussianBlur(cv2.dilate(L, np.ones((61, 61), np.uint8)), (0, 0), 15)
    dark = (bg - L > 15) & (sat < 50) & (T < 15)
    # doku yalnız kenar dışında: yumuşatılmış gradyanı büyük pikseller (malzeme/gölge geçişi) doku sayılmaz
    Ls = cv2.GaussianBlur(L, (0, 0), 2.5)
    gm = np.hypot(cv2.Sobel(Ls, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(Ls, cv2.CV_32F, 0, 1, ksize=3)) / 8
    S = cv2.morphologyEx((dark & (tex > 3.2) & (gm < 2.5)).astype(np.uint8), cv2.MORPH_OPEN,
                         np.ones((5, 5), np.uint8)).astype(bool)
    S = cv2.dilate(S.astype(np.uint8), np.ones((5, 1), np.uint8)).astype(bool) & dark  # kenara geri büyüt (dikey)
    D = dark & ~S  # kenar geçişleri de yüksek "doku" verdiği için bantta doku şartı aranmaz
    # gölge pürüzsüzdür: kenar dışında dokulu (gümüş içi) pikseller asla gölge sayılmaz
    dark &= ~(dark & (tex > 3.2) & (gm < 2.5))
    return S, D, dark


def bant_olc(S, D, hmin=14, hmax=40, bosluk=4):
    """Yatay gümüş üst kenarları: (y, x, bant kalınlığı px)."""
    H, W = S.shape
    up = np.zeros((H, W), np.int16)
    dn = np.zeros((H, W), np.int16)
    for y in range(1, H):
        up[y] = (up[y - 1] + 1) * D[y]
    for y in range(H - 2, -1, -1):
        dn[y] = (dn[y + 1] + 1) * S[y]
    top = np.zeros_like(S)
    top[1:] = S[1:] & ~S[:-1]
    ys, xs = np.nonzero(top)
    h = dn[ys, xs]
    ok = (h >= hmin) & (h <= hmax) & (ys > bosluk + 2)
    ys, xs = ys[ok], xs[ok]
    band = np.zeros(len(ys), int)
    for g in range(bosluk + 1):
        band = np.maximum(band, np.where(up[ys - 1 - g, xs] > 0, up[ys - 1 - g, xs] + g, 0))
    v = (band > 4) & (band < 60)
    return ys[v], xs[v], band[v]


def kestir(im):
    S, D, dark = maskeler(im)
    H, W = S.shape
    ys, xs, b = bant_olc(S, D)
    ny, nx = (H + KARO - 1) // KARO, (W + KARO - 1) // KARO
    dl = np.full((ny, nx), np.nan)
    n = np.zeros((ny, nx), int)
    iy, ix = ys // KARO, xs // KARO
    for i in range(ny):
        for j in range(nx):
            m = (iy == i) & (ix == j)
            n[i, j] = int(m.sum())
            if n[i, j] >= MIN_ORNEK:
                dl[i, j] = float(np.median(b[m]))
    genel = float(np.median(b)) if len(b) else float("nan")
    dolu = dl.copy()
    if np.isfinite(dl).any():  # boş karoları en yakın dolu karodan doldur
        from scipy.ndimage import distance_transform_edt
        idx = distance_transform_edt(~np.isfinite(dl), return_distances=False, return_indices=True)
        dolu = dl[tuple(idx)]
    else:
        dolu[:] = genel
    G = np.zeros_like(S)
    Sd = cv2.dilate(S.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    for i in range(ny):
        for j in range(nx):
            d = int(round(dolu[i, j])) if np.isfinite(dolu[i, j]) else 0
            if d <= 0:
                continue
            y0, y1, x0, x1 = i * KARO, min(H, (i + 1) * KARO), j * KARO, min(W, (j + 1) * KARO)
            src = S[y0 + d:min(H, y1 + d), x0:x1]
            G[y0:y0 + src.shape[0], x0:x1] |= src
    G &= ~Sd & dark
    return dict(G=G, dl=dl, dolu=dolu, n=n, genel=genel, ornek=int(len(b)))


def run(ad):
    im = cv2.imread(cfg.deskew_png(ad))
    s = cfg.load(ad).get("olcek_px_mm", 47.17)
    R = kestir(im)
    np.save(cfg.work(ad, "m_golge.npy"), R["G"])
    kalkik = [[int(i * KARO), int(j * KARO), float(R["dl"][i, j])] for i, j in zip(*np.nonzero(R["dl"] > 1.6 * R["genel"]))]
    J = dict(karo_px=KARO, genel_delta_px=R["genel"], genel_delta_mm=R["genel"] / s, ornek=R["ornek"],
             delta_px=[[None if not np.isfinite(v) else round(v, 1) for v in r] for r in R["dl"]],
             ornek_sayisi=R["n"].tolist(), kalkik_karolar=kalkik, golge_orani=float(R["G"].mean()))
    json.dump(J, open(cfg.work(ad, "golge.json"), "w", encoding="utf-8"), indent=0)
    # harita
    H, W = im.shape[:2]
    f = min(1.0, 2400.0 / max(H, W))
    sm = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    ov = sm.copy()
    vmax = max(30.0, np.nanmax(R["dl"]) if np.isfinite(R["dl"]).any() else 30)
    for i in range(R["dl"].shape[0]):
        for j in range(R["dl"].shape[1]):
            v = R["dl"][i, j]
            p0, p1 = (int(j * KARO * f), int(i * KARO * f)), (int(min(W, (j + 1) * KARO) * f) - 1, int(min(H, (i + 1) * KARO) * f) - 1)
            if not np.isfinite(v):
                cv2.rectangle(ov, p0, p1, (200, 200, 200), 1)
                continue
            c = cv2.applyColorMap(np.uint8([[min(255, int(255 * v / vmax))]]), cv2.COLORMAP_JET)[0, 0].tolist()
            cv2.rectangle(ov, p0, p1, c, -1)
            cv2.putText(sm, f"{v / s:.2f}", (p0[0] + 3, p0[1] + 14), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 0, 0), 1)
    out = cv2.addWeighted(ov, 0.35, sm, 0.65, 0)
    out[cv2.resize(R["G"].astype(np.uint8), (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_AREA) > 0] = (200, 0, 200)
    cv2.imwrite(cfg.work(ad, "golge_haritasi.png"), out)
    print(f"{ad} golge: genel delta {R['genel']:.1f} px ({R['genel'] / s:.2f} mm), {R['ornek']} ust kenar, "
          f"golge pikseli %{100 * J['golge_orani']:.2f}, kalkik karo {len(kalkik)}")
    return J


if __name__ == "__main__":
    run(sys.argv[1])
