"""Yoğunluk tabanlı (maskeden bağımsız) alt-piksel kenar ölçümü: renk izdüşümlü kenar yayılım fonksiyonu.

Kenar.py ölçümü eşiklenmiş maskeye göredir; maskenin eşiği kenarı sistematik kaydırabilir (P2: T<20 maskesi
hattı her yandan 0.045 mm dar gösterdi). Bu modül aynı kenar örneklerinde doğrudan renkli görüntüye bakar:
  1) normal boyunca BGR profili c(t) (t ∈ [−B, B] px, 0.25 px adım, çift doğrusal)
  2) iç / dış plato: c_in = medyan c(t ∈ [−P1, −P0]), c_out = medyan c(t ∈ [P0, P1])   (çizim kenarına göre)
  3) kontrast vektörü v = c_in − c_out; |v| < min_kontrast -> eşleşmedi (malzeme geçişi yok)
  4) normalize profil p(t) = (c(t) − c_out)·v / |v|²  (iç ≈ 1, dış ≈ 0); 0.5'i azalarak kesen en yakın nokta = kenar
     (ESF'nin yarı yüksekliği: malzeme sınırının yanlılıksız kestirimi, eşik seçimi yok)
  5) bulanıklık σ = 1 / (√(2π) · max eğim)  (Gauss PSF varsayımı; px)
Gölge: dış örnek noktası (p + 4n) gölge maskesindeyse (golge.py) dış plato gölgedir -> örnek "gölge" sayılır.
Dönüş biçimi kenar.olc ile aynıdır (sapma d > 0: çizim dışarı taşıyor).
"""
import cv2
import numpy as np
import shapely
from shapely import STRtree

import kenar


def offsets(im, pts, nrm, B=10.0, dt=0.25, P0=4.0, P1=8.0, min_kontrast=12.0, ara=6.0, parca=30000):
    ts = np.arange(-B, B + dt / 2, dt, dtype=np.float32)
    iin = (ts >= -P1) & (ts <= -P0)
    iout = (ts >= P0) & (ts <= P1)
    d = np.full(len(pts), np.nan, np.float32)
    sg = np.full(len(pts), np.nan, np.float32)
    kon = np.zeros(len(pts), np.float32)
    F = im.astype(np.float32)
    for s in range(0, len(pts), parca):
        p, n = pts[s:s + parca].astype(np.float32), nrm[s:s + parca].astype(np.float32)
        mx = p[:, :1] + ts[None] * n[:, :1]
        my = p[:, 1:] + ts[None] * n[:, 1:]
        C = cv2.remap(F, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)  # (n, T, 3)
        cin = np.median(C[:, iin], 1)
        cout = np.median(C[:, iout], 1)
        v = cin - cout
        v2 = (v * v).sum(1)
        k = np.sqrt(v2)
        P = ((C - cout[:, None]) * v[:, None]).sum(2) / np.maximum(v2, 1e-6)[:, None]
        P = cv2.GaussianBlur(P, (5, 1), 0.8)  # profil boyunca hafif yumuşatma
        a, b = P[:, :-1], P[:, 1:]
        cr = (a >= 0.5) & (b < 0.5) & (np.abs(ts[None, :-1]) <= ara)
        with np.errstate(invalid="ignore", divide="ignore"):
            t = ts[None, :-1] + (a - 0.5) / (a - b) * dt
        t = np.where(cr, t, np.nan)
        has = cr.any(1) & (k >= min_kontrast)
        j = np.nanargmin(np.where(has[:, None], np.abs(t), 0), 1)
        r = np.nonzero(has)[0]
        d[s:s + parca][r] = -t[r, j[r]]
        slope = -np.gradient(P, dt, axis=1)
        jj = np.clip(j[r], 1, P.shape[1] - 2)
        m = np.maximum(np.max(np.stack([slope[r, jj - 1], slope[r, jj], slope[r, jj + 1]]), 0), 1e-3)
        sg[s:s + parca][r] = 1.0 / (np.sqrt(2 * np.pi) * m)
        kon[s:s + parca] = k
    return d, sg, kon


def olc(geom_px, im, s, roi_y=None, elemanlar=None, golge=None, adim=3.0):
    pts, nrm = kenar.boundary_samples(geom_px, adim)
    if roi_y is not None and len(pts):
        k = (pts[:, 1] >= roi_y[0]) & (pts[:, 1] < roi_y[1])
        pts, nrm = pts[k], nrm[k]
    d, sg, _ = offsets(im, pts, nrm)
    gl = kenar.golge_ornekleri(pts, nrm, golge)
    d_g = np.where(gl, np.nan, d)
    ok = np.isfinite(d_g)
    oz = dict(ornek=int(len(d)), kapsama=float(np.isfinite(d).mean()) if len(d) else 0.0, golge_orani=float(gl.mean()) if len(d) else 0.0)
    if ok.any():
        a = np.abs(d_g[ok])
        oz.update(medyan_mm=float(np.median(a) / s), p90_mm=float(np.percentile(a, 90) / s),
                  isaretli_medyan_mm=float(np.median(d_g[ok]) / s), sigma_mm=float(np.nanmedian(sg[ok]) / s))
    f = kenar.fit(d_g, nrm)
    if f:
        oz.update(ofset_mm=f[0] / s, kayma_mm=[f[1] / s, f[2] / s])
    tablo = []
    if elemanlar and len(pts):
        tr = STRtree([g.boundary for _, _, g in elemanlar])
        qi, idx = tr.query_nearest(shapely.points(pts), all_matches=False)
        own = np.full(len(pts), -1)
        own[qi] = idx
        for i, (n, kind, _) in enumerate(elemanlar):
            m = own == i
            if not m.any():
                continue
            di = d_g[m]
            oi = np.isfinite(di)
            row = dict(ad=n, tur=kind, ornek=int(m.sum()), kapsama=float(oi.mean()))
            if oi.any():
                row.update(medyan_mm=float(np.median(np.abs(di[oi])) / s), sigma_mm=float(np.nanmedian(sg[m][oi]) / s))
            fi = kenar.fit(di, nrm[m])
            if fi:
                row.update(ofset_mm=fi[0] / s, kayma_mm=[fi[1] / s, fi[2] / s], rms_mm=fi[3] / s)
            tablo.append(row)
    return oz, tablo, dict(pts=pts, nrm=nrm, d=d_g, sigma=sg)
