"""Maskeden temiz poligon vektörleştirme: kontur -> sadeleştirme -> kenarları 0/45/90°'ye oturtma.

Python içinden: mask_to_polys(mask, eps=2.5, snap_tol=12, min_area=400) -> [shapely Polygon] (px)
"""
import math

import cv2
import numpy as np
from shapely.geometry import Polygon
from shapely.validation import make_valid


def _snap_ring(pts, snap_tol, min_edge):
    n = len(pts)
    if n < 3:
        return None
    lines = []
    for i in range(n):
        a, b = np.array(pts[i], float), np.array(pts[(i + 1) % n], float)
        d = b - a
        L = math.hypot(*d)
        if L < 1e-6:
            continue
        ang = math.degrees(math.atan2(d[1], d[0]))
        snapped = round(ang / 45.0) * 45.0
        if abs(ang - snapped) < snap_tol:
            ang = snapped
        u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        lines.append(((a + b) / 2, u, L))
    # ardışık aynı yönlü kısa kenarları birleştir
    merged = []
    for c, u, L in lines:
        if merged and abs(abs(np.dot(merged[-1][1], u)) - 1) < 1e-6:
            pc, pu, pL = merged[-1]
            off = np.dot(c - pc, np.array([-pu[1], pu[0]]))
            if abs(off) < 2.5:
                w = pL / (pL + L)
                merged[-1] = (pc * w + c * (1 - w), pu, pL + L)
                continue
        merged.append((c, u, L))
    if len(merged) < 3:
        return None
    out = []
    m = len(merged)
    for i in range(m):
        (p, d, _), (q, e, _) = merged[i - 1], merged[i]
        A = np.array([d, -e]).T
        if abs(np.linalg.det(A)) < 1e-6:
            out.append(tuple((p + q) / 2))
        else:
            t = np.linalg.solve(A, q - p)
            out.append(tuple(p + t[0] * d))
    return out


def mask_to_polys(mask, eps=2.5, snap_tol=12, min_area=400, min_edge=3):
    cs, hier = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return []
    hier = hier[0]
    polys = []
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or cv2.contourArea(c) < min_area:
            continue
        ext = _snap_ring(cv2.approxPolyDP(c, eps, True)[:, 0].tolist(), snap_tol, min_edge)
        if ext is None:
            continue
        holes = []
        j = hier[i][2]
        while j != -1:
            if cv2.contourArea(cs[j]) > min_area / 4:
                h = _snap_ring(cv2.approxPolyDP(cs[j], eps, True)[:, 0].tolist(), snap_tol, min_edge)
                if h:
                    holes.append(h)
            j = hier[j][0]
        p = make_valid(Polygon(ext, holes))
        if p.is_empty:
            continue
        for g in getattr(p, "geoms", [p]):
            if g.geom_type == "Polygon" and g.area > min_area / 2:
                polys.append(g)
    return polys
