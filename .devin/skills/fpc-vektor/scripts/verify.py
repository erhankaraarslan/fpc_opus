"""Vektör tasarımı taramaya bindirir; kenar metrikleri, ağ ve tutarlılık kontrolleri, kabul kapısı.

Kullanım: python verify.py <ad>
Python içinden: verify(ad, D=None) -> metrik sözlüğü (work/<ad>/metrikler.json)

Metrikler (ROI = parts/<ad>.json "dogrulama_roi_y": [y0, y1] deskew px):
  kenar (alt-piksel, kenar.py)  çizim kenarı boyunca normal profilinden ölçülen malzeme kenarına işaretli sapma:
        medyan / %90 |sapma|, işaretli medyan, kapsama (eşleşen örnek oranı), ofset (genişlik yanlılığı / 2),
        kayma vektörü; eleman bazlı tablo work/<ad>/eleman_sapma.json
  ters  ölçülen maske kenarlarının çizim kenarına ≤ 3 px olan oranı (taramada olup çizimde kenarı olmayanlar)
  piksel (eski)  tam piksel Canny + mesafe dönüşümü (önceki sürümle süreklilik için; kabul ölçütü değil)
  tus tipi: dielektrik IoU + kenar; led tipi: karşılıksız tarama gümüşü
  ağ + tutarlılık: netlist.py, tutarlilik.py bulguları (bilinmeyen HATA = kabul kalır)
Görseller: overlay.png (kırmızı=gümüş, mavi=köprü, yeşil=dielektrik, mor=kesim, turuncu=karşılıksız gümüş),
  kontrol_<k>.png, kontrol_sapma_<k>.png + ov_sapma.png (sapma ısı haritası), ag_haritasi.png
"""
import importlib
import json
import os
import sys

import cv2
import numpy as np
from shapely.ops import unary_union

import bulgu
import cfg
import fpcvec as fv
import kenar
import netlist
import profil
import tutarlilik

ESIK = {  # kabul eşikleri (mm / oran) ve uyarı eşikleri
    "kenar_medyan_mm": 0.06,
    "kenar_p90_mm": 0.15,
    "kenar_kapsama_min": 0.80,
    "dielektrik_iou_min": 0.95,
    "karsiliksiz_max": 0.15,          # led: kabul; tus: uyarı
    "ofset_uyari_mm": 0.03,           # |sistematik ofset| üstü -> uyarı
    "maske_yanlilik_uyari_mm": 0.02,  # |maske ofseti − yoğunluk ofseti| üstü -> uyarı
    "eleman_medyan_uyari_mm": 0.10,
    "eleman_kapsama_uyari": 0.50,
    "eleman_min_ornek": 20,
}


def edge_dev(pred, meas, band=12):
    """(eski) Tahmin kenarından ölçülen maskenin en yakın kenarına mesafe (px): medyan, %90, kapsama."""
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


def load_design(ad, refine_yontemi=None):
    """Tasarımı kurar. refine_yontemi (veya parts/<ad>.json "refine_yontemi"): None/"maske" | "profil"."""
    import routes_view
    c = cfg.load(ad)
    y = refine_yontemi or c.get("refine_yontemi", "maske")
    routes_view.AYAR.clear()
    if y == "profil" and os.path.exists(cfg.deskew_png(ad)):
        gp = cfg.work(ad, "m_golge.npy")
        routes_view.AYAR.update(img=cv2.imread(cfg.deskew_png(ad)), golge=np.load(gp) if os.path.exists(gp) else None,
                                w_nom=c["refine_hat_mm"] * c["olcek_px_mm"] if c.get("refine_hat_mm") else None)
    mod = importlib.import_module(c.get("tasarim_modulu", f"{ad}_design"))
    try:
        return mod.build()
    finally:
        routes_view.AYAR.clear()


def _edges(g):
    return cv2.morphologyEx(g.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0


def _ters(geom_px, meas, roi, s, band=12):
    """Ölçülen maske kenar piksellerinin çizim kenarına mesafesi."""
    H, W = meas.shape
    pe = np.zeros((H, W), np.uint8)
    for p in netlist.parts(geom_px):
        for r in [p.exterior, *p.interiors]:
            cv2.polylines(pe, [np.round(np.asarray(r.coords) * 16).astype(np.int32)], True, 1, 1, cv2.LINE_8, 4)
    me = (meas & ~cv2.erode(meas.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)) & roi
    dt = cv2.distanceTransform((1 - pe).astype(np.uint8), cv2.DIST_L2, 5)[me]
    if not len(dt):
        return {}
    w = dt[dt < band]
    return dict(kapsama_3px=float((dt <= 3).mean()), bant_ici=float((dt < band).mean()),
                p90_mm=float(np.percentile(w, 90) / s) if len(w) else None)


def kontroller(ad, D, c=None):
    """Ağ + tutarlılık bulguları (taramasız). -> (netlist sonucu, bulgular)"""
    c = c or cfg.load(ad)
    A = netlist.analiz(D)
    B = A["bulgular"] + tutarlilik.kontrol(D, A, c.get("tutarlilik"))
    return A, B


def _bitir(ad, D, A, B, c):
    bulgu.kabul_uygula(B, c.get("kabul_edilen_bulgular"))
    B = bulgu.sirala(B)
    netlist.harita(D, A, B, cfg.work(ad, "ag_haritasi.png"))
    return dict(aglar=A["aglar"], ozet=A["ozet"], imza=netlist.imza(A["aglar"])), B


def check(ad):
    """fpc.py check: taramaya bakmadan ağ + tutarlılık; work/<ad>/kontroller.json + ag_haritasi.png"""
    c = cfg.load(ad)
    D = load_design(ad)
    A, B = kontroller(ad, D, c)
    ag, B = _bitir(ad, D, A, B, c)
    json.dump(dict(ag=ag, bulgular=B, sayim=bulgu.sayim(B)), open(cfg.work(ad, "kontroller.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    for a in ag["aglar"]:
        print(f"Ag {a['no']:2d}: pin {a['pinler'] or '-'}{' dummy ' + str(a['dummy']) if a['dummy'] else ''} | {', '.join(a['uclar'])}")
    bulgu.ozet_yaz(B, 80)
    return ag, B


def verify(ad, D=None):
    c = cfg.load(ad)
    E = {**ESIK, **(c.get("esik") or {})}
    D = D or load_design(ad)
    sc, s = D.scan, D.scan["s"]
    im = cv2.imread(cfg.deskew_png(ad))
    H, W = im.shape[:2]
    alt_g = fv.to_px(D.silver_geom(), sc)
    kop_g = fv.to_px(D.bridge_geom(), sc) if D.bridges else None
    sil_g = alt_g if kop_g is None else unary_union([alt_g, kop_g])
    alt = fv.raster(alt_g, (H, W))
    kop = fv.raster(kop_g, (H, W)) if kop_g is not None else np.zeros_like(alt)
    dg = D.diel_geom()
    if sc.get("diel_kayma_mm"):  # ölçülen dielektrik baskı kayması: çizim ideal, karşılaştırma kaydırılmış
        from shapely import affinity
        dg = affinity.translate(D.diel_geom(clip=False), *sc["diel_kayma_mm"]).intersection(D.outline_poly())
    dg_px = fv.to_px(dg, sc)
    die = fv.raster(dg_px, (H, W))
    out = fv.raster(fv.to_px(D.outline_poly(), sc), (H, W))
    y0, y1 = c.get("dogrulama_roi_y", [0, H])
    roi = np.zeros_like(alt)
    roi[y0:y1] = True
    M = {"tip": c["tip"], "roi_y_px": [y0, y1], "esik": E}
    if sc.get("diel_kayma_mm"):
        M["diel_kayma_mm"] = list(sc["diel_kayma_mm"])
    sil = (alt | kop) & roi
    if c["tip"] == "led":
        meas = None
        for n in c.get("dogrulama_maskesi") or ["m_top.npy", "m_under.npy"]:
            a = np.load(cfg.work(ad, n))
            meas = a if meas is None else (meas | a)
        meas &= roi
    gp = cfg.work(ad, "m_golge.npy")
    G = np.load(gp) if os.path.exists(gp) and np.load(gp, mmap_mode="r").shape == (H, W) else None
    M["golge_modeli"] = G is not None
    if G is not None and os.path.exists(cfg.work(ad, "golge.json")):
        gj = json.load(open(cfg.work(ad, "golge.json"), encoding="utf-8"))
        M["golge"] = dict(delta_mm=gj["genel_delta_mm"], kalkik_karo=len(gj["kalkik_karolar"]))
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
        dk, _, _ = kenar.olc(dg_px, tm, s, (y0, y1))
        dy, _, _ = profil.olc(dg_px, im, s, (y0, y1))
        M["dielektrik"] = dict(iou=iou(die & roi, tm), kenar=dk, yogunluk=dy, ters=_ters(dg_px, tm, roi, s),
                               piksel=dict(medyan_mm=md / s, p90_mm=p90 / s, kapsama=cov))
    # gümüş: alt-piksel kenar (maske) + yoğunluk kenarı (maskeden bağımsız) + eleman tablosu
    els = [(n, k, fv.to_px(g, sc)) for n, k, g in D.silver_elements() + D.bridge_elements()]
    gk, tablo, ornek = kenar.olc(sil_g, meas, s, (y0, y1), els, golge=G)
    gy, tablo_y, _ = profil.olc(sil_g, im, s, (y0, y1), els, golge=G)
    md, p90, cov = edge_dev(sil, meas)
    miss = meas & ~cv2.dilate(sil.astype(np.uint8), np.ones((9, 9))).astype(bool)
    miss_g = miss & ~cv2.dilate(G.astype(np.uint8), np.ones((5, 5))).astype(bool) if G is not None else miss
    M["gumus"] = dict(iou=iou(sil, meas), kenar=gk, yogunluk=gy, ters=_ters(sil_g, meas, roi, s),
                      karsiliksiz_oran=float(miss.sum() / max(meas.sum(), 1)),
                      karsiliksiz_golge_haric=float(miss_g.sum() / max(meas.sum(), 1)),
                      piksel=dict(medyan_mm=md / s, p90_mm=p90 / s, kapsama=cov))
    cent = {n: g.centroid for n, _, g in D.silver_elements() + D.bridge_elements()}
    yt = {r["ad"]: r for r in tablo_y}
    for r in tablo:
        r["konum"] = [round(cent[r["ad"]].x, 2), round(cent[r["ad"]].y, 2)] if r["ad"] in cent else None
        y = yt.get(r["ad"], {})
        r["yogunluk"] = {k: y[k] for k in ("medyan_mm", "ofset_mm", "kayma_mm", "sigma_mm", "kapsama") if k in y}
    json.dump(tablo, open(cfg.work(ad, "eleman_sapma.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
    sirali = sorted([r for r in tablo if r["ornek"] >= E["eleman_min_ornek"]],
                    key=lambda r: -(r.get("medyan_mm") or 9) * (1 if r["kapsama"] >= E["eleman_kapsama_uyari"] else 10))
    M["elemanlar_en_kotu"] = sirali[:15]

    # bulgular: ağ + tutarlılık + doğrulama uyarıları
    A, B = kontroller(ad, D, c)
    for key, lbl in (("gumus", "Gümüş"), ("dielektrik", "Dielektrik")):
        if key not in M:
            continue
        om, oy = M[key]["kenar"].get("ofset_mm"), M[key]["yogunluk"].get("ofset_mm")
        ref = oy if oy is not None and M[key]["yogunluk"]["kapsama"] >= 0.5 else om  # yoğunluk kenarı öncelikli
        if ref is not None and abs(ref) > E["ofset_uyari_mm"]:
            B.append(bulgu.yeni("UYARI", "kenar_ofset", key,
                                f"{lbl} çizimi taramaya göre sistematik olarak her yandan {ref:+.3f} mm "
                                f"({'geniş' if ref > 0 else 'dar'}); genişlik ≈ {2 * ref:+.3f} mm farklı "
                                f"({'yoğunluk kenarına' if ref is oy else 'maskeye'} göre)", None))
        if om is not None and oy is not None and abs(om - oy) > E["maske_yanlilik_uyari_mm"]:
            B.append(bulgu.yeni("UYARI", "maske_yanliligi", key,
                                f"{lbl} referans maskesi kenarı yoğunluk kenarına göre her yandan {oy - om:+.3f} mm "
                                f"{'dar' if oy > om else 'geniş'} (maske eşiği yanlı): maske ofseti {om:+.3f}, "
                                f"yoğunluk ofseti {oy:+.3f} mm. Kenar kapıları maskeye göredir; maske eşiğini düzeltin.", None))
    for r in tablo:
        if r["ornek"] < E["eleman_min_ornek"]:
            continue
        sev = "BILGI" if r["tur"] in ("led_ped", "isaret") else "UYARI"  # şablon elemanlar (kaplama altı)
        if r["kapsama"] < E["eleman_kapsama_uyari"]:
            # geniş alanlarda (ped/blok) referans maske genelde eksik: doğrulanamadı = bilgi; ince hatta uyarı
            B.append(bulgu.yeni(sev if r["tur"] in ("hat", "kopru") else "BILGI", "eleman_eslesmedi", r["ad"], f"'{r['ad']}' kenar örneklerinin yalnız %{100 * r['kapsama']:.0f}'i "
                                                                  f"taramada karşılık buldu (eleman yanlış yerde ya da referans "
                                                                  f"maske bu bölgede eksik; ısı haritasında mor)", r["konum"]))
        elif r.get("medyan_mm", 0) > E["eleman_medyan_uyari_mm"]:
            k = r.get("kayma_mm", [0, 0])
            B.append(bulgu.yeni(sev, "eleman_sapma", r["ad"],
                                f"'{r['ad']}' medyan sapma {r['medyan_mm']:.3f} mm (ofset {r.get('ofset_mm', 0):+.3f}, "
                                f"kayma {k[0]:+.3f}/{k[1]:+.3f} mm)", r["konum"]))
    if c["tip"] != "led" and M["gumus"]["karsiliksiz_golge_haric"] > E["karsiliksiz_max"]:
        B.append(bulgu.yeni("UYARI", "karsiliksiz_gumus", "gumus",
                            f"Taramadaki gümüşün %{100 * M['gumus']['karsiliksiz_golge_haric']:.0f}'i (gölge hariç) çizimde "
                            f"karşılıksız (turuncu kümeleri inceleyin)", None))
    M["ag"], B = _bitir(ad, D, A, B, c)
    M["bulgular"] = B
    M["bulgu_sayim"] = bulgu.sayim(B)

    # kabul kapıları
    K = []
    g = M["gumus"]["kenar"]
    K.append(("Gümüş kenar sapması medyan", g.get("medyan_mm", 9), "mm", "≤", E["kenar_medyan_mm"]))
    K.append(("Gümüş kenar sapması %90", g.get("p90_mm", 9), "mm", "≤", E["kenar_p90_mm"]))
    K.append(("Gümüş kenar kapsaması", g.get("kapsama", 0), "", "≥", E["kenar_kapsama_min"]))
    if "dielektrik" in M:
        d = M["dielektrik"]
        K.append(("Dielektrik IoU", d["iou"], "", "≥", E["dielektrik_iou_min"]))
        K.append(("Dielektrik kenar sapması medyan", d["kenar"].get("medyan_mm", 9), "mm", "≤", E["kenar_medyan_mm"]))
        K.append(("Dielektrik kenar sapması %90", d["kenar"].get("p90_mm", 9), "mm", "≤", E["kenar_p90_mm"]))
    if c["tip"] == "led":
        K.append(("Taramada karşılıksız gümüş (gölge hariç)", M["gumus"]["karsiliksiz_golge_haric"], "", "≤", E["karsiliksiz_max"]))
    K.append(("Ağ / tutarlılık HATA (bilinmeyen)", M["bulgu_sayim"]["HATA"], "adet", "≤", 0))
    M["kapilar"] = [dict(ad=a, deger=v, birim=u, op=op, esik=t, gecti=bool(v <= t if op == "≤" else v >= t))
                    for a, v, u, op, t in K]
    M["gecti"] = all(k["gecti"] for k in M["kapilar"])

    # görseller
    ov = im.copy()
    for gm, col in [(die, (0, 160, 0)), (alt, (0, 0, 255)), (kop, (255, 0, 0)), (out, (255, 0, 255))]:
        ov[_edges(gm)] = col
    for cx, cy, w, h in D.holes:
        gg = fv.to_px(fv.stadium_poly(cx, cy, w, h), sc)
        cv2.polylines(ov, [np.round(np.array(gg.exterior.coords)).astype(np.int32)], True, (255, 0, 255), 2)
    ov[miss] = (0, 200, 255)
    if G is not None:
        ov[miss & ~miss_g] = (200, 200, 200)  # gölgeyle açıklanan karşılıksız: gri
    cv2.imwrite(cfg.work(ad, "overlay.png"), ov)
    base = cv2.addWeighted(im, 0.55, np.full_like(im, 255), 0.45, 0)
    hm = kenar.ciz(base, ornek, s)
    f = min(1.0, 3000.0 / max(H, W))
    cv2.imwrite(cfg.work(ad, "ov_sapma.png"), cv2.resize(kenar.ciz(base, ornek, s, max(2, int(1.5 / f))), None, fx=f, fy=f,
                                                         interpolation=cv2.INTER_AREA))
    crops = c.get("rapor_kirpimlari") or {"genel": [0, 0, W, H, 0.12]}
    M["gorseller"] = {}
    for k, (x0, yy0, x1, yy1, sk) in crops.items():
        p = cfg.work(ad, f"kontrol_{k}.png")
        cv2.imwrite(p, cv2.resize(ov[yy0:yy1, x0:x1], None, fx=sk, fy=sk, interpolation=cv2.INTER_AREA))
        cv2.imwrite(cfg.work(ad, f"kontrol_sapma_{k}.png"),
                    cv2.resize(hm[yy0:yy1, x0:x1], None, fx=sk, fy=sk, interpolation=cv2.INTER_AREA))
        M["gorseller"][k] = p
    json.dump(M, open(cfg.work(ad, "metrikler.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    import oneri
    oneri.uret(ad, D)  # work/<ad>/oneriler.json
    return M


def degerlendir(ad, D, c=None):
    """Dosya yazmadan özet metrikler (yöntem karşılaştırması için)."""
    c = c or cfg.load(ad)
    sc, s = D.scan, D.scan["s"]
    im = cv2.imread(cfg.deskew_png(ad))
    H, W = im.shape[:2]
    y0, y1 = c.get("dogrulama_roi_y", [0, H])
    gp = cfg.work(ad, "m_golge.npy")
    G = np.load(gp) if os.path.exists(gp) else None
    sil_g = fv.to_px(D.silver_geom(), sc)
    if D.bridges:
        sil_g = unary_union([sil_g, fv.to_px(D.bridge_geom(), sc)])
    if c["tip"] == "led":
        meas = None
        for n in c.get("dogrulama_maskesi") or ["m_top.npy", "m_under.npy"]:
            a = np.load(cfg.work(ad, n))
            meas = a if meas is None else (meas | a)
    else:
        meas = np.load(cfg.work(ad, "silver_ref.npy"))
    gk = kenar.olc(sil_g, meas, s, (y0, y1), golge=G)[0]
    gy = profil.olc(sil_g, im, s, (y0, y1), golge=G)[0]
    A, B = kontroller(ad, D, c)
    bulgu.kabul_uygula(B, c.get("kabul_edilen_bulgular"))
    return dict(kenar=gk, yogunluk=gy, sayim=bulgu.sayim(B), imza=netlist.imza(A["aglar"]))


def refine_dene(ad):
    """fpc.py refine_dene: maske ve profil refine yöntemlerini aynı parçada karşılaştırır (dosya yazmaz)."""
    R = {}
    for y in ("maske", "profil"):
        R[y] = degerlendir(ad, load_design(ad, y))
    print(f"{ad}: refine yöntemi karşılaştırması (mm)")
    for y, r in R.items():
        k, g = r["kenar"], r["yogunluk"]
        print(f"  {y:7s} maske-kenar {k.get('medyan_mm', 9):.3f}/{k.get('p90_mm', 9):.3f} kapsama {k['kapsama']:.3f} | "
              f"yoğunluk-kenar {g.get('medyan_mm', 9):.3f}/{g.get('p90_mm', 9):.3f} ofset {g.get('ofset_mm', 0):+.3f} | "
              f"HATA {r['sayim']['HATA']} UYARI {r['sayim']['UYARI']}")
    deg = set(R["maske"]["imza"]) ^ set(R["profil"]["imza"])
    print("  ağ imzası", "AYNI" if not deg else f"DEĞİŞTİ ({len(deg)} fark): " + "; ".join(sorted(deg)[:6]))
    return R


def print_metrics(M):
    for key, lbl in (("dielektrik", "Dielektrik"), ("gumus", "Gumus")):
        if key not in M:
            continue
        m, k, p = M[key], M[key]["kenar"], M[key]["piksel"]
        ks = k.get("kayma_mm", [0, 0])
        print(f"{lbl}: kenar medyan {k.get('medyan_mm', 9):.3f} / %90 {k.get('p90_mm', 9):.3f} mm, kapsama {k['kapsama']:.3f}, "
              f"isaretli {k.get('isaretli_medyan_mm', 0):+.3f}, ofset {k.get('ofset_mm', 0):+.3f}, "
              f"kayma ({ks[0]:+.3f}, {ks[1]:+.3f}) mm | IoU {m['iou']:.3f} | ters <=3px {m['ters'].get('kapsama_3px', 0):.3f} | "
              f"eski piksel {p['medyan_mm']:.3f}/{p['p90_mm']:.3f}"
              + (f" | karsiliksiz {m['karsiliksiz_oran']:.3f} (golge haric {m['karsiliksiz_golge_haric']:.3f})" if key == "gumus" else ""))
        y = m.get("yogunluk", {})
        if y.get("medyan_mm") is not None:
            ys = y.get("kayma_mm", [0, 0])
            print(f"  yogunluk kenari: medyan {y['medyan_mm']:.3f} / %90 {y['p90_mm']:.3f} mm, kapsama {y['kapsama']:.3f}, "
                  f"ofset {y.get('ofset_mm', 0):+.3f}, kayma ({ys[0]:+.3f}, {ys[1]:+.3f}) mm, bulaniklik sigma {y.get('sigma_mm', 0):.3f} mm, "
                  f"golge orneği %{100 * y.get('golge_orani', 0):.1f}")
    bulgu.ozet_yaz(M["bulgular"], 25)
    for k in M["kapilar"]:
        print(f"  {'OK ' if k['gecti'] else 'XX '} {k['ad']}: {k['deger']:.3f} {k['op']} {k['esik']}")
    print("KABUL:", "GECTI" if M["gecti"] else "KALDI (references/05-dogrulama.md)")


if __name__ == "__main__":
    print_metrics(verify(sys.argv[1]))
