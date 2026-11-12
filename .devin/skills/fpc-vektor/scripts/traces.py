"""Bir gümüş maskesinin iskeletinden hat merkez çizgilerini çıkarır.

Her bileşen için en uzun yol bulunur, Douglas-Peucker ile sadeleştirilir, ardından
her doğru parçası en küçük kareler ile yeniden oturtulur ve köşeler komşu doğruların
kesişimi olarak hesaplanır.

Kullanım: python traces.py <maske.npy> <y0> <y1> [x0 x1]
"""
import sys
import cv2
import numpy as np
import networkx as nx
from skimage.morphology import skeletonize


def longest_path(sk):
    ys, xs = np.nonzero(sk)
    G = nx.Graph()
    idx = {(y, x): i for i, (y, x) in enumerate(zip(ys, xs))}
    for (y, x), i in idx.items():
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                j = idx.get((y + dy, x + dx))
                if j is not None and j != i:
                    G.add_edge(i, j, weight=np.hypot(dy, dx))
    paths = []
    for comp in nx.connected_components(G):
        if len(comp) < 60:
            continue
        H = G.subgraph(comp)
        a = next(iter(comp))
        d = nx.single_source_dijkstra_path_length(H, a)
        a = max(d, key=d.get)
        d, p = nx.single_source_dijkstra(H, a)
        b = max(d, key=d.get)
        paths.append(np.array([(xs[k], ys[k]) for k in p[b]], float))
    return paths


def fit_line(pts):
    c = pts.mean(0)
    u, s, vt = np.linalg.svd(pts - c)
    return c, vt[0]


def intersect(l1, l2):
    (p, d), (q, e) = l1, l2
    A = np.array([d, -e]).T
    if abs(np.linalg.det(A)) < 1e-6:
        return (p + q) / 2
    t = np.linalg.solve(A, q - p)
    return p + t[0] * d


def refine(path, eps=3.0, trim=12):
    approx = cv2.approxPolyDP(path.astype(np.float32).reshape(-1, 1, 2), eps, False)[:, 0]
    # her köşeye path üzerindeki en yakın indeksi bul
    ids = [int(np.argmin(np.hypot(*(path - v).T))) for v in approx]
    lines = []
    for a, b in zip(ids[:-1], ids[1:]):
        seg = path[min(a, b) + trim: max(a, b) - trim]
        if len(seg) < 5:
            seg = path[min(a, b): max(a, b) + 1]
        lines.append(fit_line(seg))
    verts = [path[ids[0]]]
    for l1, l2 in zip(lines[:-1], lines[1:]):
        verts.append(intersect(l1, l2))
    verts.append(path[ids[-1]])
    angs = [np.degrees(np.arctan2(-d[1], d[0])) % 180 for _, d in lines]
    return np.array(verts), angs


def main():
    m = np.load(sys.argv[1])
    y0, y1 = int(sys.argv[2]), int(sys.argv[3])
    x0, x1 = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (0, m.shape[1])
    sub = m[y0:y1, x0:x1]
    sk = skeletonize(sub)
    for path in longest_path(sk):
        path += (x0, y0)
        v, a = refine(path)
        print("PATH len=%d" % len(path))
        print("  verts:", [(round(x, 1), round(y, 1)) for x, y in v])
        print("  angles:", [round(x, 2) for x in a])


if __name__ == "__main__":
    main()
