"""Alt-piksel, işaretli kenar sapması (normal profili) ve eleman bazlı ofset / kayma kestirimi.

Yöntem
  Çizim geometrisinin (tarama px) her kenarı boyunca `adim` px aralıkla örnek alınır; dönüşü > 25° olan
  köşelere `kose` px yaklaşılmaz. Her örnekte dış normal boyunca ölçüm haritası F alt-piksel (çift doğrusal)
  örneklenir. F: ikili maske ise σ=1 px Gauss ile yumuşatılır; [0,1] olasılık haritası doğrudan kullanılır.
  F'nin 0.5 düzeyini içeriden dışarı AZALARAK kestiği, örneğe en yakın nokta ölçülen kenardır.
      sapma d = −t_kesişim (px):   d > 0  çizim ölçülen kenarın dışına taşıyor (geniş / dışarıda)
                                   d < 0  çizim ölçülen kenarın içinde kalıyor (dar / içeride)
  ±bant içinde kesişim yoksa örnek "eşleşmedi" (kapsama dışı) sayılır.
Eleman modeli
  Her eleman için d_i = a + n_i·s en küçük kareler (2 tur 3·MAD aykırı ayıklama):
      a  düzgün ofset: çizim her yandan a kadar geniş (hat genişliği farkı ≈ 2a)
      s  kayma vektörü: çizim s kadar kaymış (gözlenemeyen yön, ör. yatay hatta x, 0 kalır)
  Düzeltme önerisi: elemanı a kadar daralt, −s kadar kaydır.
"""
import cv2
import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry.polygon import orient

import netlist


def boundary_samples(geom, adim=3.0, kose=4.0, donus=25.0):
    """Kenar örnekleri: (N,2) nokta, (N,2) dış normal. Halka yönü orient() ile sabitlenir (dış normal = sağ)."""
    P, Nn = [], []
    for poly in netlist.parts(geom):
        poly = orient(poly, 1.0)
        for ring in [poly.exterior, *poly.interiors]:
            c = np.asarray(ring.coords)[:-1]
            if len(c) < 3:
                continue
            nxt = np.roll(c, -1, 0)
            e = nxt - c
            L = np.hypot(e[:, 0], e[:, 1])
            ok = L > 1e-9
            c, e, L = c[ok], e[ok], L[ok]
            u = e / L[:, None]
            prev = np.roll(u, 1, 0)
            ang = np.degrees(np.arccos(np.clip((u * prev).sum(1), -1, 1)))  # köşe i'deki dönüş
            m0 = np.where(ang > donus, kose, 0.0)
            m1 = np.roll(m0, -1)
            for i in range(len(c)):
                t = np.arange(m0[i] + adim / 2, L[i] - m1[i], adim)
                if not len(t):
                    continue
                P.append(c[i] + t[:, None] * u[i])
                Nn.append(np.repeat([[u[i, 1], -u[i, 0]]], len(t), 0))
    if not P:
        return np.zeros((0, 2)), np.zeros((0, 2))
    return np.concatenate(P), np.concatenate(Nn)


def harita(meas):
    """Ölçüm maskesi/haritası -> F (float32, [0,1])."""
    F = meas.astype(np.float32)
    if meas.dtype == bool or set(np.unique(meas[:: 50, :: 50]).tolist()) <= {0, 1}:
        F = cv2.GaussianBlur(F, (0, 0), 1.0)
    return F


def offsets(F, pts, nrm, bant=12.0, dt=0.25, parca=40000):
    """Her örnek için alt-piksel sapma d (px); eşleşmeyen NaN."""
    ts = np.arange(-bant, bant + dt / 2, dt, dtype=np.float32)
    out = np.full(len(pts), np.nan, np.float32)
    for s in range(0, len(pts), parca):
        p, n = pts[s:s + parca].astype(np.float32), nrm[s:s + parca].astype(np.float32)
        mx = p[:, :1] + ts[None] * n[:, :1]
        my = p[:, 1:] + ts[None] * n[:, 1:]
        V = np.empty(mx.shape, np.float32)
        for r in range(0, len(mx), 30000):  # cv2.remap kenar sınırı < 32767
            V[r:r + 30000] = cv2.remap(F, mx[r:r + 30000], my[r:r + 30000], cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        a, b = V[:, :-1], V[:, 1:]
        cr = (a >= 0.5) & (b < 0.5)
        with np.errstate(invalid="ignore", divide="ignore"):
            t = ts[None, :-1] + (a - 0.5) / (a - b) * dt
        t = np.where(cr, t, np.nan)
        has = cr.any(1)
        j = np.nanargmin(np.where(has[:, None], np.abs(t), 0), 1)
        out[s:s + parca][has] = -t[has, j[has]]
    return out


def fit(d, n, tur=2):
    """d = a + n·s robust en küçük kareler -> (a, sx, sy, rms, kullanılan)."""
    ok = np.isfinite(d)
    if ok.sum() < 6:
        return None
    d, n = d[ok].astype(float), n[ok].astype(float)
    keep = np.ones(len(d), bool)
    x = np.zeros(3)
    for _ in range(tur + 1):
        A = np.c_[np.ones(keep.sum()), n[keep]]
        x = np.linalg.lstsq(A, d[keep], rcond=None)[0]
        r = d - np.c_[np.ones(len(d)), n] @ x
        mad = np.median(np.abs(r[keep] - np.median(r[keep]))) + 1e-6
        keep = np.abs(r) < max(3 * 1.4826 * mad, 0.5)
    r = d[keep] - np.c_[np.ones(keep.sum()), n[keep]] @ x
    return float(x[0]), float(x[1]), float(x[2]), float(np.sqrt(np.mean(r ** 2))), int(keep.sum())


def golge_ornekleri(pts, nrm, golge, uzak=4.0):
    """Dış tarafı (p + uzak·n) gölge maskesine düşen örnekler (gölge kopyası kenarı bozar)."""
    gl = np.zeros(len(pts), bool)
    if golge is None or not len(pts):
        return gl
    q = np.round(pts + uzak * nrm).astype(int)
    H, W = golge.shape
    ok = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)
    gl[ok] = golge[q[ok, 1], q[ok, 0]]
    return gl


def olc(geom_px, meas, s, roi_y=None, elemanlar=None, bant=12.0, adim=3.0, golge=None):
    """Kenar metrikleri. elemanlar: [(ad, tür, geom_px)] -> eleman bazlı tablo. golge: gölge maskesi
    (dış tarafı gölgeye düşen örnekler metrik dışı, oranı 'golge_orani').
    Dönüş: (özet sözlüğü mm, eleman listesi mm, örnek dizileri {pts, nrm, d})"""
    pts, nrm = boundary_samples(geom_px, adim)
    if roi_y is not None and len(pts):
        k = (pts[:, 1] >= roi_y[0]) & (pts[:, 1] < roi_y[1])
        pts, nrm = pts[k], nrm[k]
    F = harita(meas)
    d = offsets(F, pts, nrm, bant)
    gl = golge_ornekleri(pts, nrm, golge)
    kap = float(np.isfinite(d).mean()) if len(d) else 0.0
    d = np.where(gl, np.nan, d)
    ok = np.isfinite(d)
    a = np.abs(d[ok])
    oz = dict(ornek=int(len(d)), kapsama=kap, golge_orani=float(gl.mean()) if len(d) else 0.0)
    if ok.any():
        oz.update(medyan_mm=float(np.median(a) / s), p90_mm=float(np.percentile(a, 90) / s),
                  isaretli_medyan_mm=float(np.median(d[ok]) / s))
    f = fit(d, nrm)
    if f:
        oz.update(ofset_mm=f[0] / s, kayma_mm=[f[1] / s, f[2] / s])
    tablo = []
    if elemanlar and len(pts):
        tr = STRtree([g.boundary for _, _, g in elemanlar])
        q, idx = tr.query_nearest(shapely.points(pts), all_matches=False)
        own = np.full(len(pts), -1)
        own[q] = idx
        for i, (n, kind, _) in enumerate(elemanlar):
            m = own == i
            if not m.any():
                continue
            di, ni = d[m], nrm[m]
            oi = np.isfinite(di)
            row = dict(ad=n, tur=kind, ornek=int(m.sum()), kapsama=float(oi.mean()))
            if oi.any():
                row.update(medyan_mm=float(np.median(np.abs(di[oi])) / s), p90_mm=float(np.percentile(np.abs(di[oi]), 90) / s))
            fi = fit(di, ni)
            if fi:
                row.update(ofset_mm=fi[0] / s, kayma_mm=[fi[1] / s, fi[2] / s], rms_mm=fi[3] / s)
            tablo.append(row)
    return oz, tablo, dict(pts=pts, nrm=nrm, d=d)


def ciz(im, ornek, s, yaricap=3):
    """Sapma ısı haritası: yeşil ≤ 0.02 mm, sarı ≤ 0.05, turuncu ≤ 0.1, kırmızı > 0.1 mm, mor = eşleşmedi."""
    out = im.copy()
    d = np.abs(ornek["d"]) / s
    renk = [(0.02, (0, 170, 0)), (0.05, (0, 220, 220)), (0.10, (0, 140, 255)), (1e9, (0, 0, 230))]
    for (x, y), v in zip(np.round(ornek["pts"]).astype(int), d):
        c = (200, 0, 200) if not np.isfinite(v) else next(col for t, col in renk if v <= t)
        cv2.circle(out, (int(x), int(y)), yaricap, c, -1)
    return out
