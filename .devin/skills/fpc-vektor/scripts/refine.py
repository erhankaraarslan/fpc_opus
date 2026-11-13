"""Kaba hat rotalarını (px) gümüş maskesindeki gerçek merkez çizgisine oturtur.

Her segment için segment boyunca dik profillerde en yakın gümüş koşusunun merkezi alınır,
doğru oturtulur (0/45/90° yakınsa açı sabitlenir), köşeler komşu doğruların kesişimidir.

Python içinden: refine_route(mask, pts, search=25) -> (verts, widths, angles)
"""
import math

import numpy as np

SNAP = [0, 45, 90, 135, 180]


def _runs(v):
    out, s = [], None
    for i, x in enumerate(v):
        if x and s is None:
            s = i
        elif not x and s is not None:
            out.append((s, i))
            s = None
    if s is not None:
        out.append((s, len(v)))
    return out


def _sample(mask, p, n, search):
    H, W = mask.shape
    ts = np.arange(-search, search + 1)
    xs = np.clip(np.round(p[0] + ts * n[0]).astype(int), 0, W - 1)
    ys = np.clip(np.round(p[1] + ts * n[1]).astype(int), 0, H - 1)
    v = mask[ys, xs]
    best = None
    for a, b in _runs(v):
        c = (ts[a] + ts[b - 1]) / 2
        if best is None or abs(c) < abs(best[0]):
            best = (c, b - a)
    return best


def _profil_merkez(img, golge, P, n, ws, w_nom):
    """Maske koşusundan bulunan merkez/genişliği yoğunluk kenarıyla (profil.offsets) inceltir.
    Her iki kenar ayrı ölçülür; dış tarafı gölgeye düşen kenar atılır ve karşı kenar ± w_nom/2 kullanılır."""
    import kenar
    import profil
    P, ws = np.asarray(P, float), np.asarray(ws, float)
    N = np.repeat([n], len(P), 0)
    e1, e2 = P - (ws / 2)[:, None] * n, P + (ws / 2)[:, None] * n
    q = np.r_[e1, e2]
    m = np.r_[-N, N]
    dd, _, _ = profil.offsets(img, q, m)
    gl = kenar.golge_ornekleri(q, m, golge)
    dd[gl] = np.nan
    d1, d2 = dd[:len(P)], dd[len(P):]
    t1, t2 = -ws / 2 + d1, ws / 2 - d2  # gerçek kenar konumları (n yönünde, merkeze göre)
    both = np.isfinite(t1) & np.isfinite(t2)
    w = w_nom if w_nom else (float(np.median((t2 - t1)[both])) if both.any() else float(np.median(ws)))
    c = np.where(np.isfinite(t1) & np.isfinite(t2), (t1 + t2) / 2,
                 np.where(np.isfinite(t2), t2 - w / 2, np.where(np.isfinite(t1), t1 + w / 2, np.nan)))
    wid = np.where(np.isfinite(t1) & np.isfinite(t2), t2 - t1, ws)
    ok = np.isfinite(c)
    return P[ok] + c[ok, None] * n, wid[ok]


def fit_segment(mask, a, b, search=25, snap_tol=5.0, frac=(0.15, 0.85), step=4, img=None, golge=None, w_nom=None):
    a, b = np.array(a, float), np.array(b, float)
    d = b - a
    L = np.hypot(*d)
    d /= L
    n = np.array([-d[1], d[0]])
    pts, ws = [], []
    for t in np.arange(frac[0] * L, frac[1] * L, step):
        p = a + t * d
        r = _sample(mask, p, n, search)
        if r is not None and r[1] > 6:
            pts.append(p + r[0] * n)
            ws.append(r[1])
    if img is not None and len(pts) >= 3:
        pts, ws = _profil_merkez(img, golge, pts, n, ws, w_nom)
        pts, ws = list(pts), list(ws)
    if len(pts) < 3:
        return a, d, None, 0
    P = np.array(pts)
    ws = np.array(ws)
    # aykırı değerleri ele
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c)
    dd = vt[0]
    off = (P - c) @ np.array([-dd[1], dd[0]])
    keep = np.abs(off - np.median(off)) < 4
    P, ws = P[keep], ws[keep]
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c)
    dd = vt[0]
    ang = math.degrees(math.atan2(dd[1], dd[0])) % 180
    if L < 150:
        snap_tol = max(snap_tol, 12.0)
    for sa in SNAP:
        if abs(ang - sa) < snap_tol:
            ang = sa % 180
            dd = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
            c = P.mean(0)
            break
    return c, dd, float(np.median(ws)), ang


def _intersect(p, d, q, e):
    A = np.array([d, -e]).T
    if abs(np.linalg.det(A)) < 1e-6:
        return (p + q) / 2
    t = np.linalg.solve(A, q - p)
    return p + t[0] * d


def _project(p, c, d):
    p = np.asarray(p, float)
    return c + ((p - c) @ d) * d


def refine_route(mask, pts, search=25, fixed=None, img=None, golge=None, w_nom=None):
    """fixed: {segment_index: (c, d)} ile bazı segmentler elle verilebilir.
    img verilirse (BGR tarama) merkezler yoğunluk kenarıyla inceltilir ("profil" yöntemi; golge maskesi ve
    nominal genişlik w_nom px ile gölgeli kenar atlanır)."""
    lines = []
    for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        if fixed and i in fixed:
            c, d = map(np.asarray, fixed[i])
            lines.append((c, d / np.hypot(*d), None, math.degrees(math.atan2(d[1], d[0])) % 180))
        else:
            lines.append(fit_segment(mask, a, b, search, img=img, golge=golge, w_nom=w_nom))
    verts = [_project(pts[0], lines[0][0], lines[0][1])]
    for (c1, d1, _, _), (c2, d2, _, _) in zip(lines[:-1], lines[1:]):
        verts.append(_intersect(c1, d1, c2, d2))
    verts.append(_project(pts[-1], lines[-1][0], lines[-1][1]))
    return np.array(verts), [l[2] for l in lines], [l[3] for l in lines]
