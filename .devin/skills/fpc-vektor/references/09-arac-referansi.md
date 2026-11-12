# 09 — Araç referansı

Tümü proje kökünden: `python .devin/skills/fpc-vektor/scripts/<betik> ...`. `<ad>` = parts/<ad>.json.

## Kurulum
```
pip install --user pymupdf numpy networkx opencv-python-headless==4.10.0.84 scipy==1.16.2 \
    scikit-image==0.25.2 shapely==2.1.1 tifffile==2025.6.11 imageio==2.37.0 lazy-loader==0.4
```
(Sürümler bu projede doğrulandı; daha yenisini kullanacaksan en az 7 günlük olsun.)

## İş akışı
| Komut | Ne yapar | Çıktı |
|---|---|---|
| `inspect_scan.py <pdf> [sayfa]` | PDF bilgisi, parça tespiti | work/_tarama/{bilgi.json, genel.png, parca_n.png} |
| `fpc.py skew <ad>` | eğiklik ölçümü | konsol: önerilen aci_derece |
| `fpc.py prep <ad>` | kırp + döndür | work/<ad>/<ad>_deskew.png, seg_hizli.png |
| `fpc.py segment <ad>` | maskeler (tip'e göre) | *.npy + seg3.png / seg_led.png |
| `fpc.py ovals <ad>` | stadium fit | konsol + ovals.npy |
| `fpc.py build <ad>` | tasarım → 4 çizim dosyası + kontrol | output/<AD>_* |
| `fpc.py verify <ad>` | metrik + overlay | work/<ad>/metrikler.json, overlay.png, kontrol_*.png |
| `fpc.py report <ad>` | rapor | output/<AD>_rapor.{md,html,pdf} |
| `fpc.py all <ad>` | prep→segment→build→verify→report | hepsi |

## Ölçüm / okuma araçları
| Komut | Kullanım |
|---|---|
| `gridview.py <girdi.png> <cikti.png> x0 y0 x1 y1 olcek izgara` | ızgaralı kırpım (etiketler gerçek px) |
| `measure.py <ad> h y0 y1 x0 x1` | satırları ortalayıp x kenarları (L ve T kanalı, alt-piksel) |
| `measure.py <ad> v x0 x1 y0 y1` | sütunları ortalayıp y kenarları |
| `traces.py <maske.npy> y0 y1 [x0 x1]` | iskelet en uzun yolları → köşe + açı (tuş tipi şerit içi gümüş) |
| `segfind.py <ad> <maske.npy>[,..] y0 y1 L` + `seglist.py <ad> wmin wmax` | yatay/dikey/45° hat parçaları tablosu |
| `routes_view.py <rota_mod> <ad> x0 y0 x1 y1 olcek [cikti]` | rotaları refine et, bindir, konsola köşe/genişlik/açı |
| `polyvec.mask_to_polys(mask, eps, snap_tol, min_area)` | maske → 0/45/90 oturtulmuş poligonlar (python) |
| `refine.refine_route(mask, pts, search)` | kaba rota → merkez çizgisi (python) |

## Python modülleri
- `fpcvec.Design` + `write_svg_editable / write_svg_production / write_svg_check / write_pdf`,
  `to_px(geom, scan)`, `raster(geom, shape)`, `stadium_poly`, `arc_points`.
- `cfg.load(ad)`, `cfg.work(ad, dosya)`, `cfg.deskew_png(ad)`.
- `verify.verify(ad, D=None) -> dict`, `verify.ESIK`.
- `report.run(ad, D=None, M=None)`.

## Ham profil kalıbı (en çok kullanılan teşhis)
```python
import cv2, numpy as np
im = cv2.imread("work/<ad>/<ad>_deskew.png").astype(float); L = im.mean(2); T = im[:,:,1] - im[:,:,2]
tex = np.load("work/<ad>/tex.npy")            # LED tipi
p = L[y0:y1, x-6:x+6].mean(1)                  # sütun profili
print(" ".join(f"{y0+i}:{int(v)}" for i, v in enumerate(p) if i % 4 == 0))
```

## Parça yapılandırması ek alanları (P3/P4)
| Alan | Ne yapar |
|---|---|
| `bukulme: {xc, dx_noktalar: [[y, dx], ...]}` | prep.py: döndürmeden sonra satır bazlı bükülme düzeltmesi |
| `rota_maskesi: ["m_dark.npy"]` | routes_view / tasarım refine maskesi (varsayılan m_top + m_under) |
| `dogrulama_maskesi: ["m_band.npy"]` | LED tipi doğrulamada ölçülen gümüş maskesi |
| `SCAN["diel_kayma_mm"] = (dx, dy)` | tasarımda: doğrulamada dielektrik baskı kayması telafisi |
segment_led.py artık `m_dark.npy` (koyuluk) ve `m_band.npy` (gölge çekirdeği ayıklanmış) da yazar.
`Design.diel_geom(clip=False)` kontura kırpılmamış dielektrik verir.
