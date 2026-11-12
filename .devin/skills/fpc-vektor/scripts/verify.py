"""Vektör tasarımı taramaya bindirir, sapma metriklerini hesaplar ve kontrol görselleri üretir.

Kullanım: python verify.py <ad>
Python içinden: verify(ad, D=None) -> metrik sözlüğü

Metrikler (parts/<ad>.json "dogrulama_roi_y": [y0, y1] deskew px aralığında):
  tus tipi : dielektrik IoU + kenar sapması (teal_closed referansı), gümüş IoU + kenar sapması (silver_ref)
  led tipi : gümüş (alt + köprü) IoU + kenar sapması (m_top | m_under), karşılıksız tarama gümüşü oranı
Kenar sapması: çizim kenarından ölçülen maske kenarına mesafe; medyan ve %90 (mm).
Görseller: work/<ad>/overlay.png (kırmızı=gümüş, mavi=köprü, yeşil=dielektrik, mor=kesim,
turuncu=çizimde karşılığı olmayan tarama gümüşü), work/<ad>/kontrol_*.png (rapor kırpımları).
"""
import importlib
import json
import sys

import cv2
import numpy as np

import cfg
import fpcvec as fv

ESIK = {  # kabul eşikleri (mm / oran)
    "kenar_medyan_mm": 0.06,
    "kenar_p90_mm": 0.15,
    "dielektrik_iou_min": 0.95,
    "karsiliksiz_max": 0.15,
}


def edge_dev(pred, meas, band=12):
    """Tahmin kenarından ölçülen maskenin en yakın kenarına mesafe (px): medyan, %90, kapsama."""
    pe = cv2.Canny(pred.astype(np.uint8) * 255, 50, 150) > 0
    me = cv2.Canny(meas.astype(np.uint8) * 255, 50, 150) > 0
    dt = cv2.distanceTransform((~me).astype(np.uint8), cv2.DIST_L2, 5)
    d = dt[pe]
    d = d[d < band]
    if len(d) == 0:
        return 99.0, 99.0, 0.0
    return float(np.median(d)), float(np.percentile(d, 90)), len(d) / max(pe.sum(), 1)


def iou(a, b):
    return float((a & b).sum() / max((a | b).sum(), 1))


def load_design(ad):
    c = cfg.load(ad)
    mod = importlib.import_module(c.get("tasarim_modulu", f"{ad}_design"))
    return mod.build()


def _edges(g):
    return cv2.morphologyEx(g.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0


def verify(ad, D=None):
    c = cfg.load(ad)
    D = D or load_design(ad)
    sc, s = D.scan, D.scan["s"]
    im = cv2.imread(cfg.deskew_png(ad))
    H, W = im.shape[:2]
    alt = fv.raster(fv.to_px(D.silver_geom(), sc), (H, W))
    kop = fv.raster(fv.to_px(D.bridge_geom(), sc), (H, W)) if D.bridges else np.zeros_like(alt)
    dg = D.diel_geom()
    if sc.get("diel_kayma_mm"):  # ölçülen dielektrik baskı kayması: çizim ideal, karşılaştırma kaydırılmış
        from shapely import affinity
        dg = affinity.translate(D.diel_geom(clip=False), *sc["diel_kayma_mm"]).intersection(D.outline_poly())
    die = fv.raster(fv.to_px(dg, sc), (H, W))
    out = fv.raster(fv.to_px(D.outline_poly(), sc), (H, W))
    y0, y1 = c.get("dogrulama_roi_y", [0, H])
    roi = np.zeros_like(alt)
    roi[y0:y1] = True
    M = {"tip": c["tip"], "roi_y_px": [y0, y1], "esik": ESIK}
    if sc.get("diel_kayma_mm"):
        M["diel_kayma_mm"] = list(sc["diel_kayma_mm"])
    sil = (alt | kop) & roi
    if c["tip"] == "led":
        meas = None
        for n in c.get("dogrulama_maskesi") or ["m_top.npy", "m_under.npy"]:
            a = np.load(cfg.work(ad, n))
            meas = a if meas is None else (meas | a)
        meas &= roi
    else:
        meas = np.load(cfg.work(ad, "silver_ref.npy")) & roi
        tm = np.load(cfg.work(ad, "teal_closed.npy")) & roi & out
        md, p90, cov = edge_dev(die & roi, tm)
        M["dielektrik"] = dict(iou=iou(die & roi, tm), kenar_medyan_mm=md / s, kenar_p90_mm=p90 / s, kapsama=cov)
    md, p90, cov = edge_dev(sil, meas)
    miss = meas & ~cv2.dilate(sil.astype(np.uint8), np.ones((9, 9))).astype(bool)
    M["gumus"] = dict(iou=iou(sil, meas), kenar_medyan_mm=md / s, kenar_p90_mm=p90 / s, kapsama=cov,
                      karsiliksiz_oran=float(miss.sum() / max(meas.sum(), 1)))
    gec = M["gumus"]["kenar_medyan_mm"] <= ESIK["kenar_medyan_mm"] and M["gumus"]["kenar_p90_mm"] <= ESIK["kenar_p90_mm"]
    if "dielektrik" in M:
        d = M["dielektrik"]
        gec &= d["iou"] >= ESIK["dielektrik_iou_min"] and d["kenar_medyan_mm"] <= ESIK["kenar_medyan_mm"] \
            and d["kenar_p90_mm"] <= ESIK["kenar_p90_mm"]
    if c["tip"] == "led":
        gec &= M["gumus"]["karsiliksiz_oran"] <= ESIK["karsiliksiz_max"]
    M["gecti"] = bool(gec)

    ov = im.copy()
    for g, col in [(die, (0, 160, 0)), (alt, (0, 0, 255)), (kop, (255, 0, 0)), (out, (255, 0, 255))]:
        ov[_edges(g)] = col
    for cx, cy, w, h in D.holes:
        g = fv.to_px(fv.stadium_poly(cx, cy, w, h), sc)
        cv2.polylines(ov, [np.round(np.array(g.exterior.coords)).astype(np.int32)], True, (255, 0, 255), 2)
    ov[miss] = (0, 200, 255)
    cv2.imwrite(cfg.work(ad, "overlay.png"), ov)
    crops = c.get("rapor_kirpimlari") or {"genel": [0, 0, W, H, 0.12]}
    M["gorseller"] = {}
    for k, (x0, yy0, x1, yy1, sk) in crops.items():
        p = cfg.work(ad, f"kontrol_{k}.png")
        cv2.imwrite(p, cv2.resize(ov[yy0:yy1, x0:x1], None, fx=sk, fy=sk, interpolation=cv2.INTER_AREA))
        M["gorseller"][k] = p
    json.dump(M, open(cfg.work(ad, "metrikler.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return M


def print_metrics(M):
    if "dielektrik" in M:
        d = M["dielektrik"]
        print(f"Dielektrik: IoU {d['iou']:.3f}, kenar medyan {d['kenar_medyan_mm']:.3f} mm, %90 {d['kenar_p90_mm']:.3f} mm")
    g = M["gumus"]
    print(f"Gumus: IoU {g['iou']:.3f}, kenar medyan {g['kenar_medyan_mm']:.3f} mm, %90 {g['kenar_p90_mm']:.3f} mm, "
          f"karsiliksiz {g['karsiliksiz_oran']:.3f}")
    print("KABUL:", "GECTI" if M["gecti"] else "KALDI (references/05-dogrulama.md)")


if __name__ == "__main__":
    print_metrics(verify(sys.argv[1]))
