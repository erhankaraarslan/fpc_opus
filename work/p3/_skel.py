"""P3 okuma: m_dark iskelet grafi -> sadelestirilmis kenar listesi + etiketli gorseller (yalnizca okuma icin)."""
import json
import sys
import cv2
import numpy as np
from skimage import morphology
from skimage.morphology import skeletonize

Y0, Y1, X0, X1 = 1370, 6320, 150, 1800
m = np.load("work/p3/m_dark.npy")[Y0:Y1, X0:X1]
m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
m = morphology.remove_small_holes(m, 3000)
sk = skeletonize(m)
H, W = sk.shape
ys, xs = np.nonzero(sk)
idx = -np.ones(sk.shape, np.int64)
idx[ys, xs] = np.arange(len(ys))
nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
adj = [[] for _ in range(len(ys))]
for i, (y, x) in enumerate(zip(ys, xs)):
    for dy, dx in nb:
        yy, xx = y + dy, x + dx
        if 0 <= yy < H and 0 <= xx < W and idx[yy, xx] >= 0:
            adj[i].append(int(idx[yy, xx]))
deg = np.array([len(a) for a in adj])
# dugumler: derece != 2; komsu dugum piksellerini kumele
isnode = deg != 2
lab = -np.ones(len(ys), np.int64)
nid = 0
for i in np.nonzero(isnode)[0]:
    if lab[i] >= 0:
        continue
    st = [i]; lab[i] = nid
    while st:
        j = st.pop()
        for k in adj[j]:
            if isnode[k] and lab[k] < 0:
                lab[k] = nid; st.append(k)
    nid += 1
seen = set()
edges = []
for i in np.nonzero(isnode)[0]:
    for k in adj[i]:
        if isnode[k] or (i, k) in seen:
            continue
        path = [i, k]; prev, cur = i, k
        while not isnode[cur]:
            nxt = [q for q in adj[cur] if q != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            path.append(cur)
        seen.add((path[-2], path[-1])); seen.add((i, k))
        a, b = lab[path[0]], lab[path[-1]] if isnode[path[-1]] else -1
        edges.append(dict(a=int(a), b=int(b), px=[(int(xs[p]) + X0, int(ys[p]) + Y0) for p in path]))
# tekrar edenleri ele (her kenar iki yonden bulunur)
uniq = {}
for e in edges:
    key = (min(e["a"], e["b"]), max(e["a"], e["b"]), tuple(sorted([e["px"][0], e["px"][-1]])), len(e["px"]))
    uniq[key] = e
edges = list(uniq.values())
# kisa ucluk dallari (bir ucu serbest dugum) ele
ndeg = {}
for e in edges:
    for n in (e["a"], e["b"]):
        ndeg[n] = ndeg.get(n, 0) + 1
out = []
for e in edges:
    L = len(e["px"])
    free = ndeg.get(e["a"], 0) == 1 or ndeg.get(e["b"], 0) == 1
    if L < 40 and free:
        continue
    if L < 12:
        continue
    c = np.array(e["px"], np.int32).reshape(-1, 1, 2)
    ap = cv2.approxPolyDP(c, 3.0, False).reshape(-1, 2).tolist()
    out.append(dict(id=len(out), n=L, pts=ap))
json.dump(out, open("work/p3/_skel.json", "w"))
im = cv2.imread("work/p3/p3_deskew.png")
for e in out:
    p = np.array(e["pts"], np.int32)
    col = (0, 0, 255) if e["n"] > 120 else (255, 0, 160)
    cv2.polylines(im, [p], False, col, 3)
    mpt = p[len(p) // 2]
    cv2.putText(im, str(e["id"]), (int(mpt[0]) + 4, int(mpt[1]) - 4), cv2.FONT_HERSHEY_PLAIN, 2.0, (200, 0, 0), 2)
for yt in range(Y0, Y1, 1000):
    crop = im[yt:yt + 1050, X0:X1].copy()
    for g in range(0, crop.shape[0], 100):
        cv2.putText(crop, str(yt + g), (2, g + 20), cv2.FONT_HERSHEY_PLAIN, 1.6, (0, 120, 0), 2)
    cv2.imwrite(f"work/p3/_t_skel_{yt}.png", cv2.resize(crop, None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA))
print(len(out), "kenar")
