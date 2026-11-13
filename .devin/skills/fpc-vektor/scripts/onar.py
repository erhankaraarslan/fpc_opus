"""Genel çizim onarımları (tasarım modülünden çağrılır; parçaya özel değildir).

  uc_kenetle(D, maks_bosluk=0.2)  Kısa kalan hat uçlarını hat doğrultusunda en yakın gümüşe (ped/hat) uzatır.
      Ağ-güvenli: birleştirme bir cihazın iki ucunu aynı ağa düşürecekse (kısa devre) veya iki ayrı pinli ağı
      birleştirecekse REDDEDİLİR (taramadaki gerçek boşluk korunur). Pede bindirme 0.25 mm, hatta merkez çizgisine kadar.
      Dönüş: [dict(hat, uc, bosluk_mm, hedef, durum)] -> RAPOR/analiz kaydına yazılmalı.
  kopru_uc_kurali(sel, traces_px, tol=4)  Köprü seçimi (choose_bridges çıktısı) için: rotanın ucunu (T-bağlantı)
      yama içinde bitiren parça köprü olamaz — köprü ancak iki ucu yalıtkan dışına çıkınca bağlantı kurar.
      O parçaları alt baskıya (top=False) çevirir. Dönüş: değiştirilen parça adları.
"""
import math

from shapely.geometry import LineString, Point

import netlist

PED_BINDIRME = 0.25


def _ag_kumesi(A):
    ic = A["_ic"]
    return ic["eleman_ag"], ic["pin_ag"], ic["cihaz_ag"]


def _guvenli(r1, r2, pin_ag, cihaz_ag, birlesik):
    """r1 ve r2 kümelerinin birleşmesi kısa devre / pinli ağ çakışması yaratır mı?"""
    def kok(r):
        return {birlesik.get(x, x) for x in r}
    a, b = kok(r1), kok(r2)
    if a & b:
        return True, "zaten aynı ağ"
    pa = {p for p, rs in pin_ag.items() if kok(rs) & a}
    pb = {p for p, rs in pin_ag.items() if kok(rs) & b}
    if pa and pb:
        return False, f"iki pinli ağı birleştirir (pin {sorted(pa)} / {sorted(pb)})"
    for d, uclar in cihaz_ag.items():
        ka = [bool(kok(u) & a) for u in uclar]
        kb = [bool(kok(u) & b) for u in uclar]
        for i in range(len(uclar)):
            for j in range(len(uclar)):
                if i != j and ka[i] and kb[j]:
                    return False, f"{d} kısa devre olur"
    return True, ""


def uc_kenetle(D, maks_bosluk=0.2, korunan=()):
    A = netlist.analiz(D)
    eleman_ag, pin_ag, cihaz_ag = _ag_kumesi(A)
    birlesik = {}
    el = {n: g for n, k, g in D.silver_elements() if k != "isaret"}
    rapor = []
    yeni = list(D.traces)
    for ti, (n, p, w) in enumerate(D.traces):
        if n.startswith("Kontak_") or n in korunan or len(p) < 2:
            continue
        pts = [tuple(q) for q in p]
        for tag, (q, onceki) in (("bas", (pts[0], pts[1])), ("son", (pts[-1], pts[-2]))):
            u = (q[0] - onceki[0], q[1] - onceki[1])
            L = math.hypot(*u)
            if L < 1e-9:
                continue
            u = (u[0] / L, u[1] / L)
            uc_geom = el[n].intersection(Point(q).buffer(w * 0.75))  # hattın uç bölgesi (gerçek çokgen)
            if uc_geom.is_empty or any(uc_geom.distance(g) <= netlist.TOL for m, g in el.items() if m != n):
                continue  # zaten değiyor
            ray = LineString([q, (q[0] + u[0] * (maks_bosluk + w), q[1] + u[1] * (maks_bosluk + w))]).buffer(w * 0.45, cap_style="flat")
            best = None
            for m, g in el.items():
                if m == n or not g.intersects(ray):
                    continue
                x = g.intersection(ray)
                t = min(((c[0] - q[0]) * u[0] + (c[1] - q[1]) * u[1]) for c in _coords(x))
                if t <= maks_bosluk and (best is None or t < best[0]):
                    best = (max(t, 0.0), m)
            if best is None:
                continue
            t, m = best
            ok, neden = _guvenli(eleman_ag.get(n, set()), eleman_ag.get(m, set()), pin_ag, cihaz_ag, birlesik)
            if not ok:
                rapor.append(dict(hat=n, uc=tag, bosluk_mm=round(t, 3), hedef=m, durum=f"reddedildi: {neden}"))
                continue
            hedef_w = next((ww for nn, _, ww in D.traces if nn == m), None)
            ov = hedef_w / 2 if hedef_w else PED_BINDIRME
            nq = (round(q[0] + u[0] * (t + ov), 4), round(q[1] + u[1] * (t + ov), 4))
            P = list(yeni[ti][1])
            if tag == "bas":
                P[0] = nq
            else:
                P[-1] = nq
            yeni[ti] = (n, P, w)
            for r in eleman_ag.get(n, set()):  # ağları birleşik say (sonraki kararlar için)
                for s in eleman_ag.get(m, set()):
                    birlesik[r] = s
            rapor.append(dict(hat=n, uc=tag, bosluk_mm=round(t, 3), hedef=m, durum=f"uzatıldı {t + ov:.3f} mm"))
    D.traces = yeni
    return rapor


def _coords(g):
    if g.is_empty:
        return []
    if hasattr(g, "exterior"):
        return list(g.exterior.coords)
    out = []
    for x in getattr(g, "geoms", []):
        out += _coords(x)
    return out or list(getattr(g, "coords", []))


def kopru_uc_kurali(sel, traces_px, tol=4.0, hedef=False, hat_px=24.0):
    """hedef=True: başka bir rotanın ucu bu parçanın üstünde (T-bağlantı yama içinde) bitiyorsa bu parça da alt
    baskıdır. Sonuç `fpc.py check` ile kısa devre açısından mutlaka denetlenmeli."""
    uc = {n: (Point(p[0]), Point(p[-1])) for n, p in traces_px}
    degisen = []
    for s in sel:
        if not s["top"] or s["name"] not in uc:
            continue
        piece = LineString(s["pts"])
        if min(piece.distance(e) for e in uc[s["name"]]) <= tol:
            s["top"], s["kural"] = False, "rota ucu yama içinde: alt baskı"
            degisen.append(s["name"])
        elif hedef:
            for m, es in uc.items():
                if m != s["name"] and min(piece.distance(e) for e in es) <= hat_px / 2 + tol:
                    s["top"], s["kural"] = False, f"'{m}' ucu bu parçada (T-bağlantı yama içinde): alt baskı"
                    degisen.append(f"{s['name']}<-{m}")
                    break
    return degisen


def ozet(rapor):
    return [f"{r['hat']} {r['uc']} ucu: {r['bosluk_mm']} mm boşluk -> '{r['hedef']}' ({r['durum']})" for r in rapor]

