"""Kenar sapmasinin y bantlarina dagilimi: python work/_devmap.py <ad> [diel|gumus] [bant_px]"""
import sys
import cv2
import numpy as np
sys.path.insert(0, ".devin/skills/fpc-vektor/scripts")
import cfg  # noqa
import fpcvec as fv
from shapely import affinity
from verify import load_design
ad = sys.argv[1]
kind = sys.argv[2] if len(sys.argv) > 2 else "diel"
bw = int(sys.argv[3]) if len(sys.argv) > 3 else 500
c = cfg.load(ad)
D = load_design(ad)
sc = D.scan
s = sc["s"]
y0, y1 = c["dogrulama_roi_y"]
if kind == "diel":
    g = D.diel_geom()
    if sc.get("diel_kayma_mm"):
        g = affinity.translate(D.diel_geom(clip=False), *sc["diel_kayma_mm"]).intersection(D.outline_poly())
    meas = np.load(cfg.work(ad, "teal_closed.npy"))
    H, W = meas.shape
    meas &= fv.raster(fv.to_px(D.outline_poly(), sc), (H, W))
else:
    g = unary = D.silver_geom()
    meas = np.load(cfg.work(ad, "silver_ref.npy")) if c["tip"] != "led" else \
        (np.load(cfg.work(ad, "m_top.npy")) | np.load(cfg.work(ad, "m_under.npy")))
    H, W = meas.shape
pred = fv.raster(fv.to_px(g, sc), (H, W))
pe = cv2.Canny(pred.astype(np.uint8) * 255, 50, 150) > 0
me = cv2.Canny(meas.astype(np.uint8) * 255, 50, 150) > 0
dt = cv2.distanceTransform((~me).astype(np.uint8), cv2.DIST_L2, 5)
ys, xs = np.nonzero(pe)
d = dt[ys, xs]
k = (d < 12) & (ys >= y0) & (ys < y1)
ys, xs, d = ys[k], xs[k], d[k]
print("toplam medyan %.3f p90 %.3f mm" % (np.median(d) / s, np.percentile(d, 90) / s))
for a in range(y0, y1, bw):
    m = (ys >= a) & (ys < a + bw)
    if m.sum() < 20:
        continue
    dd = d[m]
    big = m & (d > 5)
    xb = np.round(np.percentile(xs[big], [10, 50, 90])) if big.sum() > 10 else ""
    print(f"y {a}-{a + bw}: n={m.sum():6d} med={np.median(dd) / s:.3f} p90={np.percentile(dd, 90) / s:.3f}  >5px x~{xb}")
