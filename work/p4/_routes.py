import sys
import numpy as np
sys.path.insert(0, ".devin/skills/fpc-vektor/scripts")
from refine import refine_route
m = np.load("work/p4/sil_teal.npy")
S, PX0, PY0, XC = 47.17, 1040.0, 184.0, 18.35
R = {
    "Net1": [(930, 1992), (622, 1990), (541, 2128), (540, 3515), (822, 4170), (824.5, 6100)],
    "Net4": [(1243, 2202), (1480, 2202), (1539, 2258), (1539, 3500), (1227, 4170), (1226, 6100)],
    "Net2a": [(908, 2950), (910, 3900)],
    "Net2b": [(920, 4330), (920, 6100)],
    "Net2": [(908, 2950), (910, 4000), (920, 4300), (920, 6100)],
    "Net3": [(1249, 2950), (1246, 3682), (1015, 4180), (1013, 6100)],
    "Bus": [(925, 2716), (1232, 2716)],
    "BusR": [(1475, 2716), (1539, 2716)],
}
for k, pts in R.items():
    v, w, a = refine_route(m, pts, search=22)
    mm = [(round((x - PX0) / S + XC, 3), round((y - PY0) / S, 3)) for x, y in v]
    print(k, "px", [(round(x, 1), round(y, 1)) for x, y in v])
    print("   mm", mm)
    print("   w", [None if x is None else round(x, 1) for x in w], "aci", [round(x, 2) for x in a])
