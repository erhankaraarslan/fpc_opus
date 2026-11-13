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
| `fpc.py check <ad>` | ağ + tasarım tutarlılığı (taramasız, hızlı) | work/<ad>/kontroller.json, ag_haritasi.png |
| `fpc.py verify <ad>` | alt-piksel kenar metrikleri + check + kabul | work/<ad>/metrikler.json, eleman_sapma.json, overlay.png, ov_sapma.png, kontrol_*.png, kontrol_sapma_*.png |
| `fpc.py report <ad>` | rapor | output/<AD>_rapor.{md,html,pdf} |
| `fpc.py all <ad>` | prep→segment→build→verify→report | hepsi |
| `fpc.py golge <ad>` | gölge modeli (segment içinde otomatik) | m_golge.npy, golge.json, golge_haritasi.png |
| `fpc.py oneri <ad>` | ölçümden düzeltme önerileri (verify sonunda otomatik) | work/<ad>/oneriler.json |
| `fpc.py olcek <ad> x0 y0 x1 y1 [adim_mm] [x\|y]` | periyodik yapıdan alt-piksel adım / px/mm | konsol (hat sayısı, artık RMS) |
| `fpc.py bukulme <ad> [adim_px]` | film bükülmesi kestirimi | work/<ad>/bukulme_onerisi.json |
| `fpc.py refine_dene <ad>` | maske vs profil refine karşılaştırması (dosya yazmaz) | konsol |
| `fpc.py kayit <ad>` | arka yüz taramasını ön deskew'e çakıştır (`arka` yapılandırması) | <ad>_arka.png, kayit.json, kayit_kontrol.png |
| `fpc.py ogren egit <ad,..\|all>` | onaylı çizimlerden etiket + RTrees (tip bazlı: model_tus/model_led + model) | work/_ogren/*.yml, meta.json |
| `fpc.py ogren uygula <ad>` | sınıf haritası (parça tipinin modeli) | m_ogren_*.npy, m_ogren_gumus_hepsi.npy, p_gumus.npy, ogren_siniflar.png |
| `fpc.py ogren dene [ad,..]` | bırak-birini-dışarı (aynı tip eğitimi) | work/_ogren/dene.json |
| `fpc.py topoloji <ad> [y0 y1]` | otomatik rota önerisi (aday + MILP + graf), mevcut rotalarla kıyas | rota_onerisi.py/.png/.json |
| `fpc.py altin <ad>` | onaylı durumu kaydet | parts/<ad>_altin.json |
| `fpc.py regress <ad\|all>` | verify + altınla karşılaştır | konsol; çıkış 1 = gerileme / ağ değişti / yeni HATA |
| `fpc.py selftest` | sentetik doğruluk testleri | konsol; hepsi TAMAM olmalı |

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
- `Design.silver_elements()` → [(ad, tür, geom)] (hat | kontak | led_ped | tus_ped | dikdortgen | isaret),
  `Design.bridge_elements()`; isteğe bağlı `Design.pins`, `Design.devices`.
- `cfg.load(ad)`, `cfg.work(ad, dosya)`, `cfg.deskew_png(ad)`.
- `verify.verify(ad, D=None) -> dict`, `verify.check(ad)`, `verify.ESIK`.
- `kenar.olc(geom_px, maske, s, roi_y, elemanlar) -> (özet, eleman tablosu, örnekler)`; `kenar.boundary_samples`,
  `kenar.offsets`, `kenar.fit` (d = a + n·s), `kenar.ciz` (ısı haritası).
- `netlist.analiz(D) -> {aglar, bulgular, ozet}`, `netlist.imza(aglar)`, `netlist.harita(D, A, bulgular, yol)`.
- `tutarlilik.kontrol(D, A=None, esik=None) -> [bulgu]`, `tutarlilik.ESIK`.
- `bulgu.yeni / kabul_uygula / sayim / ozet_yaz`; `regress.altin / karsilastir`.
- `profil.olc(geom_px, bgr, s, roi_y, elemanlar, golge)` / `profil.offsets(bgr, pts, nrm)` -> (d, σ, kontrast).
- `golge.kestir(bgr) -> {G, dl, genel}`; `kenar.golge_ornekleri(pts, nrm, G)`.
- `kalibre.adim_bul(profil, nominal_px) -> (adım, hat, rms)`, `kalibre.bukulme_kestir(bgr)`.
- `kayit.kaydet_goruntu(on, arka, ayna, aci) -> {warp, hizali, ecc}`, `kayit.yerel_artik(A, B)`.
- `onar.uc_kenetle(D, maks_bosluk=0.2)` (kısa uçları pede/hatta uzat; kısa devre / iki pinli ağ birleşmesi
  reddedilir) ve `onar.kopru_uc_kurali(sel, traces_px, hedef=False)` (rota ucu yama içindeki parça köprü olamaz) —
  tasarım modülünde `build()` sonunda / köprü seçiminden sonra çağrılır; sonuç `D.onarimlar`, `D.kopru_kurali`.
- `ogren.etiketler(ad)`, `ogren.ozellikler(bgr)`, `ogren.tahmin(model, bgr)`; `topoloji.adaylar/ele/sec/graf/zincirler`.
- `refine.refine_route(..., img, golge, w_nom)`; `routes_view.AYAR` (verify.load_design doldurur);
  `verify.load_design(ad, refine_yontemi)`, `verify.degerlendir(ad, D)`, `verify.refine_dene(ad)`; `oneri.uret(ad)`.
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
| `esik: {...}` | verify.ESIK değerlerini parça için değiştirir (gerekçesini analiz kaydına yaz) |
| `tutarlilik: {...}` | tutarlilik.ESIK değerlerini değiştirir (ör. `{"min_aralik_mm": 0.15}`) |
| `kabul_edilen_bulgular: {"<id/glob>": "gerekçe"}` | kullanıcının bilerek kabul ettiği bulgular (yalnız kullanıcı onayıyla) |
| `refine_yontemi: "profil"` | rota refine'da merkezleri yoğunluk kenarıyla incelt (gölgeli kenarı atla); önce `refine_dene` |
| `refine_hat_mm: 0.5` | profil refine'da tek kenar kaldığında kullanılacak nominal genişlik (yoksa ölçülen medyan) |
| `arka: {pdf, sayfa, goruntu_indeksi, kirpim_px, ayna, aci_derece}` | arka yüz taraması (kayit.py) |
segment_led.py artık `m_dark.npy` (koyuluk) ve `m_band.npy` (gölge çekirdeği ayıklanmış) da yazar.
`Design.diel_geom(clip=False)` kontura kırpılmamış dielektrik verir.
