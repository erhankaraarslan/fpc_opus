"""Otomatik rota önerisi: gümüş maskesinden 0/45/90° aday segmentler -> çakışma çözümü (MILP) -> graf -> rotalar.

Kullanım: python topoloji.py <ad> [y0 y1]     (veya fpc.py topoloji <ad> [y0 y1])
Maske önceliği: work/<ad>/m_ogren_gumus_hepsi.npy (fpc.py ogren uygula) > parts/<ad>.json rota_maskesi > m_top|m_under
Çıktılar (work/<ad>/):
  rota_onerisi.py    ROUTES = [dict(name, pts, guven, flag)] (px; parts/<ad>_routes.py başlangıcı olarak kullanılır)
  rota_onerisi.png   öneri bindirmesi (yeşil = güvenli, turuncu = düşük güven / flag)
  rota_onerisi.json  aday/seçilen sayıları, mevcut tasarım varsa kıyas (geri çağırma / kesinlik)
Yöntem
  1) yönlü morfolojik açma (0/45/90/135°, uzunluk ≥ Lmin) -> bileşen başına merkez doğrusu, genişlik, uzunluk
  2) genişliği hat genişliğine uymayan (ped, leke) adaylar elenir; kanıt skoru = merkez boyunca maske oranı ×
     genişlik tutarlılığı × log(uzunluk)
  3) MILP (scipy.optimize.milp): skor toplamını en büyükle; aynı yönde, örtüşen ve merkezleri birbirine hat
     genişliğinden yakın iki aday (gölge/çift algılama) birlikte seçilemez
  4) seçilenlerin uçları, en yakın başka segmentin merkez doğrusuna ≤ uzat px ise kesişime uzatılır; düğümler
     birleştirilir; derece-2 düğümlerden geçen zincirler tek rota olur
Öneri bir başlangıçtır: belirsiz/düşük güvenli rotalar flag=True; ağ mantığı yine fpc.py check ile denetlenir.
"""
import json
import math
import os
import sys

import cv2
import networkx as nx
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

import cfg

YONLER = (0, 90, 45, 135)


def _cekirdek(L, a):
    L = int(L) | 1
    k = np.zeros((L, L), np.uint8)
    c = L // 2
    dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
    for t in np.linspace(-c, c, 4 * L):
        k[int(round(c + t * dy)), int(round(c + t * dx))] = 1
    return k


def adaylar(M, w_nom, Lmin=40):
    out = []
    m8 = M.astype(np.uint8)
    for a in YONLER:
        o = cv2.morphologyEx(m8, cv2.MORPH_OPEN, _cekirdek(Lmin, a))
        n, lab, st, _ = cv2.connectedComponentsWithStats(o, 8)
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
        nr = np.array([-d[1], d[0]])
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < Lmin * 4:
                continue
            ys, xs = np.nonzero(lab == i)
            P = np.c_[xs, ys].astype(float)
            t, s = P @ d, P @ nr
            tb = np.round(t / 3).astype(int)
            order = np.argsort(tb)
            tb, s_ = tb[order], s[order]
            cut = np.flatnonzero(np.diff(tb)) + 1
            ws, cs = [], []
            for g in np.split(s_, cut):
                ws.append(g.max() - g.min() + 1)
                cs.append((g.max() + g.min()) / 2)
            w, c = float(np.median(ws)), float(np.median(cs))
            L = float(t.max() - t.min())
            if L < Lmin or not (0.55 * w_nom <= w <= 1.6 * w_nom):
                continue
            p0, p1 = d * t.min() + nr * c, d * t.max() + nr * c
            tutarlilik = float(np.mean(np.abs(np.array(ws) - w) < 0.25 * w_nom))
            out.append(dict(a=a, p0=p0, p1=p1, w=w, L=L, tut=tutarlilik))
    return out


def kanit(M, s, adim=3):
    seg = LineString([s["p0"], s["p1"]])
    n = max(int(seg.length // adim), 2)
    q = np.array([seg.interpolate(i / n, normalized=True).coords[0] for i in range(n + 1)])
    xi = np.clip(np.round(q[:, 0]).astype(int), 0, M.shape[1] - 1)
    yi = np.clip(np.round(q[:, 1]).astype(int), 0, M.shape[0] - 1)
    return float(M[yi, xi].mean())


def _oran(seg, mask_geom_or_arr, adim=3):
    n = max(int(seg.length // adim), 2)
    q = [seg.interpolate(i / n, normalized=True) for i in range(n + 1)]
    if isinstance(mask_geom_or_arr, np.ndarray):
        A = mask_geom_or_arr
        return float(np.mean([A[min(max(int(round(p.y)), 0), A.shape[0] - 1), min(max(int(round(p.x)), 0), A.shape[1] - 1)] for p in q]))
    return float(np.mean([mask_geom_or_arr.contains(p) for p in q]))


def ele(M, cands, w_nom):
    """Sahte adayları ele: kalın bölgede (ped/leke) kalanlar; yatay/dikey adayların üstüne düşen çaprazlar."""
    k = int(1.6 * w_nom) | 1
    kalin = cv2.morphologyEx(M.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(bool)
    kalin = cv2.dilate(kalin.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    out = [c for c in cands if _oran(LineString([c["p0"], c["p1"]]), kalin) < 0.3]
    orto = unary_union([LineString([c["p0"], c["p1"]]).buffer(0.6 * w_nom, cap_style="flat") for c in out if c["a"] in (0, 90)])
    return [c for c in out if c["a"] in (0, 90) or orto.is_empty or _oran(LineString([c["p0"], c["p1"]]), orto) < 0.5]


def sec(M, cands, w_nom):
    """MILP: çakışan (paralel, örtüşen, yakın) adaylardan en fazla biri."""
    n = len(cands)
    if not n:
        return []
    sk = np.array([kanit(M, c) * (0.5 + 0.5 * c["tut"]) * math.log(1 + c["L"]) for c in cands])
    rows = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = cands[i], cands[j]
            if a["a"] != b["a"]:
                continue
            d = np.array([math.cos(math.radians(a["a"])), math.sin(math.radians(a["a"]))])
            nr = np.array([-d[1], d[0]])
            if abs((a["p0"] - b["p0"]) @ nr) > 1.2 * w_nom:
                continue
            ta = sorted([a["p0"] @ d, a["p1"] @ d])
            tb = sorted([b["p0"] @ d, b["p1"] @ d])
            ov = min(ta[1], tb[1]) - max(ta[0], tb[0])
            if ov > 0.3 * min(a["L"], b["L"]):
                r = np.zeros(n)
                r[i] = r[j] = 1
                rows.append(r)
    cons = [LinearConstraint(np.array(rows), -np.inf, 1)] if rows else []
    res = milp(-sk, constraints=cons, integrality=np.ones(n), bounds=Bounds(0, 1))
    x = np.round(res.x).astype(bool) if res.x is not None else sk > 0
    for c, s_, k in zip(cands, sk, x):
        c["skor"], c["secildi"] = float(s_), bool(k)
    return [c for c in cands if c["secildi"] and c["skor"] > 0]


def dogrusal_birlestir(sel, w_nom, bosluk=None):
    """Aynı yönde, merkezleri ≤ 0.4·w ayrık ve uçları ≤ bosluk aralıklı adayları tek segmentte birleştirir
    (köprü/yama ve leke kesintileri maskeyi böler)."""
    bosluk = bosluk if bosluk is not None else 2.5 * w_nom
    S = [dict(s) for s in sel]
    degisti = True
    while degisti:
        degisti = False
        for i in range(len(S)):
            for j in range(i + 1, len(S)):
                a, b = S[i], S[j]
                if a["a"] != b["a"]:
                    continue
                d = np.array([math.cos(math.radians(a["a"])), math.sin(math.radians(a["a"]))])
                nr = np.array([-d[1], d[0]])
                if abs((a["p0"] - b["p0"]) @ nr) > 0.4 * w_nom:
                    continue
                ta, tb = sorted([a["p0"] @ d, a["p1"] @ d]), sorted([b["p0"] @ d, b["p1"] @ d])
                if max(ta[0], tb[0]) - min(ta[1], tb[1]) > bosluk:
                    continue
                c = ((a["p0"] + a["p1"]) / 2 * a["L"] + (b["p0"] + b["p1"]) / 2 * b["L"]) @ nr / (a["L"] + b["L"])
                t0, t1 = min(ta[0], tb[0]), max(ta[1], tb[1])
                S[i] = dict(a=a["a"], p0=d * t0 + nr * c, p1=d * t1 + nr * c, w=(a["w"] + b["w"]) / 2, L=t1 - t0,
                            tut=(a["tut"] + b["tut"]) / 2, skor=a.get("skor", 0) + b.get("skor", 0), secildi=True)
                del S[j]
                degisti = True
                break
            if degisti:
                break
    return S


def graf(sel, w_nom, uzat=None):
    uzat = uzat if uzat is not None else 1.2 * w_nom
    lines = [LineString([s["p0"], s["p1"]]) for s in sel]
    G = nx.Graph()
    pts = {}

    def node(p):
        for k, q in pts.items():
            if math.dist(k, p) < 0.6 * w_nom:
                return k
        k = (round(p[0], 1), round(p[1], 1))
        pts[k] = p
        return k
    kes = [[0.0, l.length] for l in lines]
    for i, l in enumerate(lines):
        for e in (0, 1):
            pe = Point(l.coords[e])
            d = np.array(l.coords[e]) - np.array(l.coords[1 - e])
            d /= np.linalg.norm(d)
            ray = LineString([pe.coords[0], tuple(np.array(pe.coords[0]) + d * uzat)])
            best = None
            for j, m in enumerate(lines):
                if j == i:
                    continue
                x = ray.intersection(m) if ray.intersects(m) else None
                if x is None and m.distance(pe) < 0.6 * w_nom:
                    x = m.interpolate(m.project(pe))
                if x is not None and not x.is_empty:
                    x = x if x.geom_type == "Point" else Point(x.coords[0])
                    dd = pe.distance(x)
                    if best is None or dd < best[0]:
                        best = (dd, j, x)
            if best:
                _, j, x = best
                if e == 0:
                    lines[i] = LineString([x.coords[0], lines[i].coords[1]])
                else:
                    lines[i] = LineString([lines[i].coords[0], x.coords[0]])
                kes[j].append(lines[j].project(x))
    for i, l in enumerate(lines):
        ts = sorted(set(round(t, 1) for t in kes[i] if -1 <= t <= l.length + 1))
        ts = [0.0] + [t for t in ts if 0 < t < l.length] + [l.length]
        for t0, t1 in zip(ts[:-1], ts[1:]):
            if t1 - t0 < 3:
                continue
            a, b = node(l.interpolate(t0).coords[0]), node(l.interpolate(t1).coords[0])
            if a != b:
                G.add_edge(a, b, w=sel[i]["w"], skor=sel[i]["skor"])
    return G


def zincirler(G):
    seen = set()
    rot = []
    for u, v in G.edges():
        if (u, v) in seen or (v, u) in seen:
            continue
        path = [u, v]
        seen.add((u, v))
        for uc in (0, 1):
            while True:
                end = path[-1] if uc == 0 else path[0]
                prev = path[-2] if uc == 0 else path[1]
                if G.degree(end) != 2:
                    break
                nxt = [x for x in G.neighbors(end) if x != prev][0]
                if (end, nxt) in seen or (nxt, end) in seen:
                    break
                seen.add((end, nxt))
                path = path + [nxt] if uc == 0 else [nxt] + path
        rot.append(path)
    out = []
    for p in rot:
        q = [p[0]]
        for a, b, c in zip(p[:-2], p[1:-1], p[2:]):
            d1 = math.atan2(b[1] - a[1], b[0] - a[0])
            d2 = math.atan2(c[1] - b[1], c[0] - b[0])
            if abs((d2 - d1 + math.pi) % (2 * math.pi) - math.pi) > math.radians(5):
                q.append(b)
        q.append(p[-1])
        sk = [G.edges[a, b]["skor"] for a, b in zip(p[:-1], p[1:])]
        out.append(dict(pts=[(round(x, 1), round(y, 1)) for x, y in q], guven=float(np.mean(sk))))
    return out


def _anahtar(p):
    return (round(p[0], 1), round(p[1], 1))


def kiyas(ad, routes, tol=6.0):
    """Mevcut tasarım rotalarıyla geri çağırma / kesinlik (uzunluk ağırlıklı, px)."""
    from verify import load_design
    import fpcvec as fv
    D = load_design(ad)
    ref = [fv.to_px(LineString(p), D.scan) for n, p, w in D.traces if not n.startswith("Kontak_")]
    oner = [LineString(r["pts"]) for r in routes if len(r["pts"]) > 1]
    if not ref or not oner:
        return {}
    R, O = unary_union(ref), unary_union(oner)
    Rb, Ob = R.buffer(tol), O.buffer(tol)
    return dict(geri_cagirma=float(R.intersection(Ob).length / max(R.length, 1)),
                kesinlik=float(O.intersection(Rb).length / max(O.length, 1)),
                mevcut_uzunluk_px=float(R.length), oneri_uzunluk_px=float(O.length))


def maske(ad):
    p = cfg.work(ad, "m_ogren_gumus_hepsi.npy")
    if os.path.exists(p):
        return np.load(p), "m_ogren_gumus_hepsi"
    c = cfg.load(ad)
    names = c.get("rota_maskesi") or (["m_top.npy", "m_under.npy"] if c["tip"] == "led" else ["silver_ref.npy"])
    m = None
    for n in names:
        a = np.load(cfg.work(ad, n))
        m = a if m is None else (m | a)
    return m, "+".join(names)


def run(ad, y0=None, y1=None, w_mm=0.5):
    c = cfg.load(ad)
    s = c.get("olcek_px_mm", 47.17)
    w_nom = w_mm * s
    M, kaynak = maske(ad)
    M = M.copy()
    ya, yb = (y0, y1) if y0 is not None else tuple(c.get("dogrulama_roi_y", [0, M.shape[0]]))
    M[:ya] = False
    M[yb:] = False
    M = cv2.morphologyEx(M.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    cands = adaylar(M, w_nom)
    sel = dogrusal_birlestir(sec(M, ele(M, cands, w_nom), w_nom), w_nom)
    G = graf(sel, w_nom)
    rot = zincirler(G)
    deg = dict(G.degree())
    rot = [r for r in rot if not (LineString(r["pts"]).length < 3 * w_nom
                                  and deg.get(_anahtar(r["pts"][0]), 1) <= 1 and deg.get(_anahtar(r["pts"][-1]), 1) <= 1)]
    guven_esik = float(np.percentile([r["guven"] for r in rot], 25)) if rot else 0
    for i, r in enumerate(rot, 1):
        r["name"], r["flag"] = f"oto_{i:03d}", r["guven"] <= guven_esik
    with open(cfg.work(ad, "rota_onerisi.py"), "w", encoding="utf-8") as f:
        f.write(f'"""Otomatik rota önerisi ({ad}, maske {kaynak}). Gözden geçir, adlandır, parts/{ad}_routes.py\'a taşı."""\n\n')
        f.write("ROUTES = [\n" + "".join(f"    dict(name={r['name']!r}, pts={r['pts']}, guven={r['guven']:.2f}"
                                          + (", flag=True" if r["flag"] else "") + "),\n" for r in rot) + "]\n")
    im = cv2.imread(cfg.deskew_png(ad))
    for r in rot:
        cv2.polylines(im, [np.round(np.array(r["pts"])).astype(np.int32)], False, (0, 140, 255) if r["flag"] else (0, 170, 0), 4)
    f_ = min(1.0, 3000.0 / max(im.shape[:2]))
    cv2.imwrite(cfg.work(ad, "rota_onerisi.png"), cv2.resize(im[ya:yb], None, fx=f_, fy=f_, interpolation=cv2.INTER_AREA))
    K = {}
    if os.path.exists(f"parts/{c.get('tasarim_modulu', ad + '_design')}.py"):
        try:
            K = kiyas(ad, rot)
        except Exception as e:  # tasarım kurulamıyorsa kıyas atlanır
            K = dict(hata=str(e))
    J = dict(maske=kaynak, aday=len(cands), secilen=len(sel), rota=len(rot), dugum=G.number_of_nodes(), kiyas=K)
    json.dump(J, open(cfg.work(ad, "rota_onerisi.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{ad}: {len(cands)} aday -> {len(sel)} seçildi (MILP) -> {len(rot)} rota; maske {kaynak}"
          + (f"; mevcut rotalarla geri çağırma {K['geri_cagirma']:.2f}, kesinlik {K['kesinlik']:.2f}" if "kesinlik" in K else ""))
    return J


if __name__ == "__main__":
    a = sys.argv
    run(a[1], *(int(v) for v in a[2:4]))
