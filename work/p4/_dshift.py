"""Dielektrik baski kaymasi: cizim dielektrigini kaydirarak teal_closed ile IoU / kenar sapmasi taramasi."""
import sys
import numpy as np
sys.path.insert(0, ".devin/skills/fpc-vektor/scripts")
import cfg  # noqa
import fpcvec as fv
from shapely import affinity
from verify import edge_dev, iou, load_design
ad = sys.argv[1] if len(sys.argv) > 1 else "p4"
c = cfg.load(ad)
D = load_design(ad)
sc = dict(D.scan)
y0, y1 = c["dogrulama_roi_y"]
tm0 = np.load(cfg.work(ad, "teal_closed.npy"))
H, W = tm0.shape
out = fv.raster(fv.to_px(D.outline_poly(), sc), (H, W))
roi = np.zeros((H, W), bool); roi[y0:y1] = True
# bas bolgesi ayri (kuyruk blogu baskin olmasin)
yb = int(sc["py0"] + 124 * sc["s"])
for name, (a, b) in {"bas": (y0, yb), "tum": (y0, y1)}.items():
    r = np.zeros((H, W), bool); r[a:b] = True
    tm = tm0 & r & out
    g = D.diel_geom(clip=False); og = D.outline_poly()
    best = []
    for dx in np.arange(0.0, 0.31, 0.05):
        for dy in np.arange(-0.3, 0.06, 0.05):
            die = fv.raster(fv.to_px(affinity.translate(g, dx, dy).intersection(og), sc), (H, W)) & r
            md, p90, _ = edge_dev(die, tm)
            best.append((iou(die, tm), dx, dy, md / sc["s"], p90 / sc["s"]))
    best.sort(reverse=True)
    print(name, [tuple(round(v, 3) for v in b) for b in best[:6]])
