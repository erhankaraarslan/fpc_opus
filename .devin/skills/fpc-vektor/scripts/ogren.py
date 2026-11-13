"""Öğrenen piksel sınıflandırıcı: kabul edilmiş çizimlerden etiket üretir, rastgele orman (cv2.ml.RTrees) eğitir.

Kullanım (fpc.py üzerinden):
  fpc.py ogren egit <ad1,ad2,...|all>   etiketli parçalardan model -> work/_ogren/model.yml + meta.json
  fpc.py ogren uygula <ad>             modelle sınıf haritası -> work/<ad>/m_ogren_*.npy, p_gumus.npy, ogren_siniflar.png
  fpc.py ogren dene [ad1,ad2,...]      bırak-birini-dışarı değerlendirme (her parça diğerleriyle eğitilip test edilir)
Neden: sabit eşikli maskeler (references/02) tarayıcı/ışık değişince bozulur ve gölge/kaplama/leke ayrımı elle
kurallarla yapılır. Onaylı çizim taramaya bindirildiğinde her piksel için malzeme etiketi verir; bu etiketlerle
eğitilen sınıflandırıcı yeni parçada (aynı tarayıcı/malzeme) olasılık haritası üretir.
Sınıflar: 0 film, 1 gümüş (yalıtkan dışı), 2 gümüş yalıtkan altında, 3 köprü (yalıtkan üstü gümüş),
          4 dielektrik (gümüşsüz), 5 gölge
Etiket dışı (öğretilmez): sınıf sınırlarında 3 px bant, LED gövdesi/pedleri çevresi (kaplama), Kontrol katmanı
rotaları çevresi (belirsiz), ROI dışı, kart konturunun 0.5 mm dışı.
Özellikler (17): B, G, R, L, G−R, doygunluk, Lab a/b, Gauss L σ1/σ3, DoG L(1−4), yerel std 5/11, doku (hp),
gradyan σ1.5, L − yerel arka plan, yumuşatılmış G−R.
"""
import json
import os
import sys
import time

import cv2
import numpy as np

import cfg
import fpcvec as fv

SINIFLAR = ["film", "gumus", "gumus_yalitkan_alti", "kopru", "dielektrik", "golge"]
RENK = [(245, 245, 245), (60, 60, 200), (140, 40, 0), (220, 0, 0), (200, 200, 60), (180, 0, 180)]
OZELLIK = ["B", "G", "R", "L", "T", "sat", "a", "b", "L1", "L3", "DoG", "std5", "std11", "tex", "grad", "Lbg", "Ts"]
MODEL_DIR = os.path.join("work", "_ogren")
MARJ = 64


def ozellikler(im):
    f = im.astype(np.float32)
    B, G, R = f[..., 0], f[..., 1], f[..., 2]
    L = f.mean(2)
    T = G - R
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
    L1 = cv2.GaussianBlur(L, (0, 0), 1)
    L3 = cv2.GaussianBlur(L, (0, 0), 3)
    L4 = cv2.GaussianBlur(L, (0, 0), 4)

    def std(k):
        m = cv2.blur(L, (k, k))
        return np.sqrt(np.maximum(cv2.blur(L * L, (k, k)) - m * m, 0))
    tex = cv2.blur(np.abs(L - cv2.GaussianBlur(L, (0, 0), 2)), (9, 9))
    Ls = cv2.GaussianBlur(L, (0, 0), 1.5)
    grad = cv2.magnitude(cv2.Sobel(Ls, cv2.CV_32F, 1, 0), cv2.Sobel(Ls, cv2.CV_32F, 0, 1))
    bg = cv2.GaussianBlur(cv2.dilate(L, np.ones((61, 61), np.uint8)), (0, 0), 15)
    X = [B, G, R, L, T, hsv[..., 1].astype(np.float32), lab[..., 1], lab[..., 2], L1, L3, L1 - L4, std(5), std(11), tex,
         grad, L - bg, cv2.GaussianBlur(T, (0, 0), 2)]
    return np.stack(X, -1).astype(np.float32)


def etiketler(ad, D=None):
    """Onaylı çizimden piksel etiketleri (−1 = etiket dışı)."""
    from verify import load_design
    c = cfg.load(ad)
    D = D or load_design(ad)
    sc = D.scan
    im = cv2.imread(cfg.deskew_png(ad))
    H, W = im.shape[:2]
    R = lambda g: fv.raster(fv.to_px(g, sc), (H, W)) if not g.is_empty else np.zeros((H, W), bool)  # noqa: E731
    sil = R(D.silver_geom())
    kop = R(D.bridge_geom()) if D.bridges else np.zeros((H, W), bool)
    die = R(D.diel_geom())
    out = R(D.outline_poly().buffer(-0.3))
    gp = cfg.work(ad, "m_golge.npy")
    G = np.load(gp) if os.path.exists(gp) else np.zeros((H, W), bool)
    lab = np.full((H, W), -1, np.int8)
    ciz = sil | kop | die
    ciz_d = cv2.dilate(ciz.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool)
    k3 = np.ones((7, 7), np.uint8)

    def ic(m):
        return cv2.erode(m.astype(np.uint8), k3).astype(bool)
    lab[ic(out & ~ciz_d & ~G)] = 0
    lab[ic(sil & ~die)] = 1
    lab[ic(sil & die & ~kop)] = 2
    lab[ic(kop & die)] = 3
    lab[ic(die & ~sil & ~kop)] = 4
    lab[G & ~ciz_d & out] = 5
    # etiket dışı: LED kaplama, belirsiz rotalar, ROI dışı
    har = np.zeros((H, W), bool)
    from shapely.geometry import LineString, box
    from shapely.ops import unary_union
    led = [box(cx - 1.6, cy - 2.4, cx + 1.6, cy + 2.4) for _, cx, cy, _, _ in D.leds]
    belirsiz = [LineString(p).buffer(0.6) for _, p in D.check if len(p) > 1]
    if led or belirsiz:
        har |= R(unary_union(led + belirsiz))
    lab[har] = -1
    y0, y1 = c.get("dogrulama_roi_y", [0, H])
    lab[:y0] = -1
    lab[y1:] = -1
    return im, lab


def ornekle(lab, n_sinif=6, n=30000, seed=0):
    rng = np.random.default_rng(seed)
    idx = []
    for k in range(n_sinif):
        ys, xs = np.nonzero(lab == k)
        if len(ys):
            s = rng.choice(len(ys), min(n, len(ys)), replace=False)
            idx.append(np.c_[ys[s], xs[s], np.full(len(s), k)])
    return np.concatenate(idx) if idx else np.zeros((0, 3), int)


def ozellik_ornek(im, S, serit=512):
    """Yalnız örnek noktalarında özellik (şerit şerit; tam görüntü özelliği bellekte tutulmaz)."""
    H = im.shape[0]
    X = np.zeros((len(S), len(OZELLIK)), np.float32)
    for y in range(0, H, serit):
        k = (S[:, 0] >= y) & (S[:, 0] < y + serit)
        if not k.any():
            continue
        a, b = max(0, y - MARJ), min(H, y + serit + MARJ)
        F = ozellikler(im[a:b])
        X[k] = F[S[k, 0] - a, S[k, 1]]
    return X


def veri(ad, n=30000):
    im, lab = etiketler(ad)
    S = ornekle(lab, n=n)
    return ozellik_ornek(im, S), S[:, 2].astype(np.int32), lab, im


def egit_model(X, y, agac=60, derinlik=18):
    m = cv2.ml.RTrees_create()
    m.setMaxDepth(derinlik)
    m.setMinSampleCount(10)
    m.setActiveVarCount(5)
    m.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER, agac, 0))
    m.train(X, cv2.ml.ROW_SAMPLE, y)
    return m


def tahmin(m, im, serit=512, oy=True, satir=None):
    """Şerit şerit sınıf + gümüş olasılığı (oy oranı). satir=(y0, y1): yalnız bu aralık."""
    H, W = im.shape[:2]
    cls = np.zeros((H, W), np.uint8)
    pg = np.zeros((H, W), np.float16)
    ya, yb = satir or (0, H)
    for y in range(ya, yb, serit):
        n = min(serit, yb - y)
        a, b = max(0, y - MARJ), min(H, y + n + MARJ)
        F = ozellikler(im[a:b])[y - a:y - a + n].reshape(-1, len(OZELLIK))
        _, r = m.predict(F)
        cls[y:y + n] = r.reshape(-1, W).astype(np.uint8)
        if not oy:
            continue
        v = m.getVotes(F, 0)  # ilk satır sınıf etiketleri, sonra oylar
        lbl = v[0]
        vs = v[1:].astype(np.float32)
        tot = vs.sum(1) + 1e-6
        g = sum(vs[:, list(lbl).index(k)] for k in (1, 2, 3) if k in lbl)
        pg[y:y + n] = (g / tot).reshape(-1, W).astype(np.float16)
    return cls, pg


def egit(parcalar, n=30000):
    """Parça tipine göre ayrı modeller (model_tus.yml, model_led.yml) + hepsi için model.yml."""
    V = {}
    for ad in parcalar:
        X, y, _, _ = veri(ad, n)
        V[ad] = (X, y, cfg.load(ad)["tip"])
        print(f"  {ad} ({V[ad][2]}): {len(y)} örnek, sınıf sayıları {np.bincount(y, minlength=6).tolist()}")
    os.makedirs(MODEL_DIR, exist_ok=True)
    meta = dict(siniflar=SINIFLAR, ozellikler=OZELLIK, modeller={})
    gruplar = {"model": list(parcalar)}
    for t in sorted({v[2] for v in V.values()}):
        gruplar[f"model_{t}"] = [a for a in parcalar if V[a][2] == t]
    for ad_m, lst in gruplar.items():
        t0 = time.time()
        m = egit_model(np.concatenate([V[a][0] for a in lst]), np.concatenate([V[a][1] for a in lst]))
        m.save(os.path.join(MODEL_DIR, f"{ad_m}.yml"))
        meta["modeller"][ad_m] = dict(parcalar=lst, ornek=int(sum(len(V[a][1]) for a in lst)))
        print(f"model: {MODEL_DIR}/{ad_m}.yml ({', '.join(lst)}; {time.time() - t0:.0f} s)")
    json.dump(meta, open(os.path.join(MODEL_DIR, "meta.json"), "w"), indent=1)


def yukle(tip=None):
    for n in ([f"model_{tip}.yml"] if tip else []) + ["model.yml"]:
        p = os.path.join(MODEL_DIR, n)
        if os.path.exists(p):
            return cv2.ml.RTrees_load(p), n
    raise SystemExit("Model yok: önce fpc.py ogren egit all")


def uygula(ad, m=None, oy=False):
    """oy=True: gümüş olasılık haritası da (p_gumus.npy; getVotes ~5× yavaş)."""
    if m is None:
        m, n = yukle(cfg.load(ad)["tip"])
        print(f"{ad}: model {n}")
    im = cv2.imread(cfg.deskew_png(ad))
    t = time.time()
    cls, pg = tahmin(m, im, oy=oy)
    for k, n in enumerate(SINIFLAR):
        np.save(cfg.work(ad, f"m_ogren_{n}.npy"), cls == k)
    np.save(cfg.work(ad, "m_ogren_gumus_hepsi.npy"), np.isin(cls, (1, 2, 3)))
    if oy:
        np.save(cfg.work(ad, "p_gumus.npy"), pg)
    vis = np.zeros_like(im)
    for k, c in enumerate(RENK):
        vis[cls == k] = c
    cv2.imwrite(cfg.work(ad, "ogren_siniflar.png"), vis)
    print(f"{ad}: sınıf haritası ({time.time() - t:.0f} s) -> work/{ad}/m_ogren_*.npy, p_gumus.npy, ogren_siniflar.png")
    return cls, pg


def _iou(a, b):
    return float((a & b).sum() / max((a | b).sum(), 1))


def el_maskesi(ad):
    c = cfg.load(ad)
    if c["tip"] == "led":
        m = None
        for n in c.get("dogrulama_maskesi") or ["m_top.npy", "m_under.npy"]:
            a = np.load(cfg.work(ad, n))
            m = a if m is None else (m | a)
        return m
    return np.load(cfg.work(ad, "silver_ref.npy"))


def _egitim_kumesi(ad, parcalar, tip_ayri=True):
    """Test parçası hariç; tip_ayri ise yalnız aynı tipteki (tus/led) parçalar (yoksa hepsi)."""
    digerleri = [a for a in parcalar if a != ad]
    if tip_ayri:
        t = cfg.load(ad)["tip"]
        ayni = [a for a in digerleri if cfg.load(a)["tip"] == t]
        if ayni:
            return ayni
    return digerleri


def dene(parcalar, tip_ayri=True):
    """Bırak-birini-dışarı: her parça için diğerleriyle (varsayılan: aynı tiptekiler) eğit, onda test et."""
    V = {ad: veri(ad) for ad in parcalar}
    sonuc = {}
    for ad in parcalar:
        eg = _egitim_kumesi(ad, parcalar, tip_ayri)
        X = np.concatenate([V[a][0] for a in eg])
        y = np.concatenate([V[a][1] for a in eg])
        m = egit_model(X, y)
        _, _, lab, im = V[ad]
        rows = np.nonzero((lab >= 0).any(1))[0]
        cls, _ = tahmin(m, im, oy=False, satir=(int(rows.min()), int(rows.max()) + 1))
        ok = lab >= 0
        acc = float((cls[ok] == lab[ok]).mean())
        per = {}
        for k, n in enumerate(SINIFLAR):
            per[n] = _iou((cls == k) & ok, (lab == k) & ok)
        gl = np.isin(lab, (1, 2, 3)) & ok
        gp = np.isin(cls, (1, 2, 3)) & ok
        el = el_maskesi(ad) & ok
        sonuc[ad] = dict(egitim=eg, dogruluk=acc, sinif_iou=per, gumus_iou_ogren=_iou(gp, gl), gumus_iou_el=_iou(el, gl))
        print(f"{ad} (eğitim {','.join(eg)}): doğruluk {acc:.3f} | gümüş IoU öğrenen {sonuc[ad]['gumus_iou_ogren']:.3f} vs elle kurulan maske "
              f"{sonuc[ad]['gumus_iou_el']:.3f} | sınıf IoU " + ", ".join(f"{n} {v:.2f}" for n, v in per.items()))
    os.makedirs(MODEL_DIR, exist_ok=True)
    json.dump(sonuc, open(os.path.join(MODEL_DIR, "dene.json"), "w"), indent=1)
    return sonuc


def tum_parcalar():
    import glob
    return sorted(os.path.basename(p)[:-11] for p in glob.glob("parts/*_altin.json"))


if __name__ == "__main__":
    a = sys.argv
    lst = (tum_parcalar() if len(a) < 3 or a[2] == "all" else a[2].split(","))
    if a[1] == "egit":
        egit(lst)
    elif a[1] == "uygula":
        uygula(a[2])
    else:
        dene(lst)
