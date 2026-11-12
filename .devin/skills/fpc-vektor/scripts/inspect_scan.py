"""Kaynak PDF'i inceler: sayfa/görüntü/metin bilgisi, tam çözünürlüklü görüntü, parça tespiti.

Kullanım: python inspect_scan.py <pdf> [sayfa]
Çıktılar (work/_tarama/):
  bilgi.json           sayfa ölçüsü, gömülü görüntü boyutu, efektif dpi, px/mm, metin var mı
  genel.png            ~60 dpi genel görünüm, numaralı parça kutuları
  parca_<n>.png        her parçanın ~150 dpi önizlemesi
Konsola: her parça için önerilen "kirpim_px" (tam çözünürlük, 120 px pay ile).
"""
import json
import os
import sys

import cv2
import numpy as np
import pymupdf


def main():
    pdf = sys.argv[1]
    pno = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    out = os.path.join("work", "_tarama")
    os.makedirs(out, exist_ok=True)
    d = pymupdf.open(pdf)
    p = d[pno]
    imgs = p.get_images()
    text = p.get_text().strip()
    info = dict(sayfa_sayisi=d.page_count, sayfa_pt=[p.rect.width, p.rect.height], metin_karakter=len(text),
                goruntu_sayisi=len(imgs))
    if not imgs:
        info["not"] = "Gomulu goruntu yok: vektor PDF olabilir, bu skill tarama (raster) icindir."
        json.dump(info, open(os.path.join(out, "bilgi.json"), "w"), indent=1)
        print(info)
        return
    x = d.extract_image(imgs[0][0])
    im = cv2.imdecode(np.frombuffer(x["image"], np.uint8), cv2.IMREAD_COLOR)
    H, W = im.shape[:2]
    dpi = W / (p.rect.width / 72.0)
    info.update(goruntu_px=[W, H], efektif_dpi=round(dpi, 2), px_mm=round(dpi / 25.4, 3), format=x["ext"])
    cv2.imwrite(os.path.join(out, "tam." + ("png" if x["ext"] == "png" else "jpg")), im)
    f = 60.0 / dpi
    sm = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
    m = (g < 238).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    # Parçalar genelde yan yana dizilir: sütun izdüşümündeki boş bantlar parçaları ayırır.
    col = m.sum(0)
    occ = col > max(2, 0.004 * m.shape[0])
    bands, s0 = [], None
    for i, v in enumerate(np.r_[occ, False]):
        if v and s0 is None:
            s0 = i
        elif not v and s0 is not None:
            if i - s0 >= 8:
                bands.append((s0, i))
            s0 = None
    parts = []
    for a, c in bands:
        sub = m[:, a:c]
        rows = np.nonzero(sub.sum(1) > 1)[0]
        if len(rows) == 0:
            continue
        # dikeyde de boşlukla ayrılmış parçaları böl (>= 25 px boş satır)
        groups, start, prev = [], rows[0], rows[0]
        for r in rows[1:]:
            if r - prev > 25:
                groups.append((start, prev))
                start = r
            prev = r
        groups.append((start, prev))
        for b, e in groups:
            if e - b < 20:
                continue
            cs = np.nonzero(sub[b:e + 1].sum(0) > 0)[0]
            parts.append([int(a + cs[0]), int(b), int(a + cs[-1] + 1), int(e + 1)])
    parts.sort(key=lambda b: (b[0] // 40, b[1]))
    vis = sm.copy()
    info["parcalar"] = []
    for k, (a, b, c, e) in enumerate(parts, 1):
        cv2.rectangle(vis, (a, b), (c, e), (0, 0, 255), 1)
        cv2.putText(vis, str(k), (a + 2, b + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        box = [max(0, int(a / f) - 120), max(0, int(b / f) - 120), min(W, int(c / f) + 120), min(H, int(e / f) + 120)]
        mm = [(box[2] - box[0]) / (dpi / 25.4), (box[3] - box[1]) / (dpi / 25.4)]
        info["parcalar"].append(dict(no=k, kirpim_px=box, yaklasik_mm=[round(mm[0], 1), round(mm[1], 1)]))
        pv = im[box[1]:box[3], box[0]:box[2]]
        s2 = 150.0 / dpi
        cv2.imwrite(os.path.join(out, f"parca_{k}.png"), cv2.resize(pv, None, fx=s2, fy=s2, interpolation=cv2.INTER_AREA))
        print(f"parca {k}: kirpim_px={box}  ~{mm[0]:.1f} x {mm[1]:.1f} mm")
    cv2.imwrite(os.path.join(out, "genel.png"), vis)
    json.dump(info, open(os.path.join(out, "bilgi.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in info.items() if k != "parcalar"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
