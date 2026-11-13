# FPC_OPUS — Taramadan vektör FPC / membran devre çizimi

Taranmış (raster PDF) esnek baskılı devre ve membran devre parçalarını **CorelDRAW'da düzenlenebilir, mm ölçekli,
katmanlı vektör çizime** (SVG + PDF) dönüştüren, çizimi taramaya bindirerek sayısal olarak doğrulayan ve
MD/HTML/PDF rapor üreten bir araç seti. Hedef: düzenlenebilir çizim + dokümantasyon (doğrudan üretim değil).

Bütün iş akışı bir Devin skill'i olarak paketlenmiştir: `.devin/skills/fpc-vektor/` (bkz. `SKILL.md`).
Araçlar parçaya özel değildir; yeni taramalarda ve yeni parçalarda aynı komutlar kullanılır.

---

## İçindekiler
1. [Kaynak ve parçalar](#1-kaynak-ve-parçalar)
2. [Kurulum](#2-kurulum)
3. [Hızlı başlangıç](#3-hızlı-başlangıç)
4. [Dizin yapısı](#4-dizin-yapısı)
5. [Komutlar](#5-komutlar)
6. [Çıktılar ve CorelDRAW](#6-çıktılar-ve-coreldraw)
7. [Doğrulama ve kabul](#7-doğrulama-ve-kabul)
8. [Ağ ve tasarım tutarlılığı kontrolleri](#8-ağ-ve-tasarım-tutarlılığı-kontrolleri)
9. [Gelişmiş ölçüm araçları (Faz 2)](#9-gelişmiş-ölçüm-araçları-faz-2)
10. [Öğrenen segmentasyon ve otomatik rota önerisi (Faz 3)](#10-öğrenen-segmentasyon-ve-otomatik-rota-önerisi-faz-3)
11. [Regresyon ve testler](#11-regresyon-ve-testler)
12. [Repoda olmayan dosyalar](#12-repoda-olmayan-dosyalar)
13. [Bilinen durum ve bekleyen işler](#13-bilinen-durum-ve-bekleyen-işler)
14. [Sorun giderme](#14-sorun-giderme)

---

## 1. Kaynak ve parçalar

Kaynak: `docs/K.pdf` — tek sayfa, 10192 × 14016 px JPEG, ~1199 dpi. Ölçek konnektör adımı 1.00 mm ile kalibre
edilmiştir: **47.17 px/mm** (tarayıcı nominali 47.21).

| Parça | Tip | Açıklama | Set |
|---|---|---|---|
| P1 | LED (`led`) | kısa LED devresi, 12 LED, iki gümüş baskı + köprü yamaları | P2 ile üst üste |
| P2 | Tuş (`tus`) | kısa 3 tuşlu membran, tarak pedler, 12 oval pencere | P1 ile |
| P3 | LED (`led`) | uzun LED devresi, 20 LED | P4 ile |
| P4 | Tuş (`tus`) | uzun 3 tuşlu membran, 20 oval pencere | P3 ile |

LED'ler tuş katmanındaki oval pencerelerin altına denk gelir (çapraz doğrulama: x farkı ≤ 0.11 mm).

## 2. Kurulum

Python 3.10+ (3.12.4 ile doğrulandı). Sürümler sabitlenmiştir; daha yenisini kullanacaksanız **en az 7 gün önce
yayınlanmış** sürüm seçin (tedarik zinciri güvenliği).

```
pip install --user pymupdf numpy networkx opencv-python-headless==4.10.0.84 scipy==1.16.2 \
    scikit-image==0.25.2 shapely==2.1.1 tifffile==2025.6.11 imageio==2.37.0 lazy-loader==0.4
```
Kontrol: `python -c "import pymupdf,cv2,scipy,skimage,shapely,networkx"`

GPU, PyTorch veya scikit-learn gerekmez: öğrenen sınıflandırıcı OpenCV'nin `cv2.ml` modülünü, optimizasyon
`scipy.optimize.milp` (HiGHS) kullanır.

Windows konsolunda Türkçe çıktı için: `set PYTHONIOENCODING=utf-8` (Git Bash: `export PYTHONIOENCODING=utf-8`).

## 3. Hızlı başlangıç

Tüm komutlar **proje kökünden** çalıştırılır. Tek giriş noktası:

```
python .devin/skills/fpc-vektor/scripts/fpc.py <komut> <ad>
```

Mevcut bir parçayı baştan sona yeniden üretmek:
```
python .devin/skills/fpc-vektor/scripts/fpc.py all p2        # prep -> gölge -> segment -> build -> verify -> report
```

Yeni bir parça için sıra (ayrıntılar `SKILL.md`):
```
python .devin/skills/fpc-vektor/scripts/inspect_scan.py docs/<dosya>.pdf   # parça tespiti, kırpım önerisi
# parts/<ad>.json oluştur (şablon: .devin/skills/fpc-vektor/templates/parca.json)
fpc.py skew <ad>          # eğiklik -> aci_derece
fpc.py prep <ad>          # kırp + döndür
fpc.py bukulme <ad>       # uzun parçada film bükülmesi gerekli mi?
fpc.py segment <ad>       # gölge modeli + maskeler
fpc.py olcek <ad> x0 y0 x1 y1     # konnektör adımından ölçek
# (LED tipi) fpc.py ogren uygula <ad> ; fpc.py topoloji <ad>   -> rota önerisi
# parts/<ad>_design.py (+ LED tipinde parts/<ad>_routes.py) yaz
fpc.py check <ad>         # ağ + tutarlılık (hızlı, taramasız) — her tasarım değişikliğinden sonra
fpc.py build <ad>         # SVG/PDF çıktılar
fpc.py verify <ad>        # metrikler + kabul + öneriler
fpc.py report <ad>        # rapor
fpc.py altin <ad>         # onaylı durumu regresyon için kaydet
```

## 4. Dizin yapısı

```
docs/K.pdf                         kaynak tarama
.devin/skills/fpc-vektor/
  SKILL.md                         iş akışı + kabul kapıları (önce bunu okuyun)
  references/01..09-*.md           ayrıntılı yöntem, maskeler, tuş/LED devresi, doğrulama, çıktılar, örnek değerler,
                                   hatalar ve dersler, araç referansı
  scripts/                         tüm araçlar (aşağıda)
  templates/                       parça yapılandırması + çalışan tuş/LED tasarım örnekleri
parts/
  <ad>.json                        parça yapılandırması (kırpım, açı, tip, ROI, rapor kırpımları, maskeler, eşikler)
  <ad>_design.py                   parametrik tasarım: build() -> fpcvec.Design + RAPOR sözlüğü
  <ad>_routes.py                   (LED tipi) kaba hat rotaları, tarama px
  <ad>_analiz.json                 analiz kaydı: süreç, bulgular, karar noktaları, görsel açıklamaları (rapor buradan beslenir)
  <ad>_altin.json                  regresyon için onaylı durum
work/<ad>/                         ara dosyalar: deskew görüntü, maskeler (.npy), analiz görselleri, metrikler.json,
                                   eleman_sapma.json, kontroller.json, oneriler.json, golge.json, rota_onerisi.*
work/_ogren/                       öğrenen sınıflandırıcı (meta.json, dene.json; model .yml dosyaları repoda değil)
output/                            <AD>_duzenlenebilir.svg, <AD>_uretim.svg, <AD>_uretim.pdf, <AD>_kontrol_taramali.svg,
                                   <AD>_rapor.{md,html,pdf} + <AD>_rapor_gorseller/
AGENTS.md                          proje durumu ve ajan notları
```

Betikler (`scripts/`):

| Betik | Görev |
|---|---|
| `fpc.py` | tek giriş noktası (tüm komutlar) |
| `inspect_scan.py`, `skew.py`, `prep.py` | PDF analizi, eğiklik, kırpım/döndürme/bükülme düzeltme |
| `segment.py`, `segment_led.py` | tuş / LED tipi renk-doku maskeleri |
| `golge.py` | gölge kopyası modeli (yerel ofset δ, gölge maskesi, kalkıklık haritası) |
| `measure.py`, `gridview.py`, `traces.py`, `segfind.py`, `seglist.py`, `polyvec.py`, `ovals.py` | ölçüm / okuma araçları |
| `refine.py`, `routes_view.py` | kaba rotaları gerçek merkez çizgisine oturtma (maske veya profil yöntemi) |
| `fpcvec.py` | geometri modeli (`Design`) + SVG/PDF yazıcılar |
| `onar.py` | genel çizim onarımları: ağ-güvenli uç kenetleme, köprü uç kuralı |
| `verify.py`, `kenar.py`, `profil.py` | doğrulama: alt-piksel maske kenarı, yoğunluk kenarı, kabul kapıları |
| `netlist.py`, `tutarlilik.py`, `bulgu.py` | çizimden ağ çıkarımı, tasarım tutarlılığı, bulgu yapısı |
| `oneri.py`, `kalibre.py`, `kayit.py` | düzeltme önerileri, ölçek/bükülme kalibrasyonu, ön+arka tarama çakıştırma |
| `ogren.py`, `topoloji.py` | öğrenen piksel sınıflandırıcı, otomatik rota önerisi |
| `report.py` | MD / HTML / PDF rapor |
| `regress.py`, `selftest.py` | regresyon (altın durum), sentetik doğruluk testleri |

## 5. Komutlar

`fpc.py <komut> <ad>`:

| Komut | Ne yapar |
|---|---|
| `skew` / `prep` | eğiklik ölçümü / kırp + döndür (+ `bukulme`) → `work/<ad>/<ad>_deskew.png` |
| `segment` | gölge modeli + tipine göre maskeler |
| `golge` | yalnız gölge modeli: `m_golge.npy`, `golge.json`, `golge_haritasi.png` |
| `ovals` | oval pencereleri ölç (tuş tipi) |
| `build` | tasarım → 4 çizim dosyası + otomatik dosya/katman kontrolü |
| `check` | taramaya bakmadan ağ (netlist) + tasarım tutarlılığı (saniyeler) |
| `verify` | taramaya bindir: kenar metrikleri + ağ/tutarlılık + kabul + öneriler |
| `report` | `output/<AD>_rapor.{md,html,pdf}` |
| `all` | prep → gölge → segment → build → verify → report |
| `oneri` | ölçümden düzeltme önerileri (`oneriler.json`) |
| `olcek <ad> x0 y0 x1 y1 [adim_mm] [x\|y]` | periyodik yapıdan alt-piksel adım / px/mm |
| `bukulme <ad> [adim_px]` | film bükülmesi kestirimi → `bukulme_onerisi.json` |
| `refine_dene` | maske ve profil refine yöntemlerini karşılaştır (dosya yazmaz) |
| `kayit` | arka yüz taramasını ön görüntüye çakıştır (`parts/<ad>.json "arka"`) |
| `topoloji <ad> [y0 y1]` | otomatik rota önerisi → `rota_onerisi.py/.png/.json` |
| `altin` / `regress <ad\|all>` | onaylı durumu kaydet / verify + karşılaştır |

Ad gerektirmeyenler: `fpc.py selftest`, `fpc.py ogren egit <ad,..|all>`, `fpc.py ogren uygula <ad>`,
`fpc.py ogren dene [ad,..]`.

## 6. Çıktılar ve CorelDRAW

| Dosya | İçerik |
|---|---|
| `<AD>_duzenlenebilir.svg` | hatlar kalınlıklı `<polyline>`, pedler `<rect>`; CorelDRAW'da düğüm düzenleme |
| `<AD>_uretim.svg` / `.pdf` | her katman tek kapalı dolgu; PDF'te OCG katmanları, kesim yayları Bézier |
| `<AD>_kontrol_taramali.svg` | üretim katmanları + altta hizalı tarama (görsel kontrol) |
| `<AD>_rapor.html` | etkileşimli rapor: durum kartları, karar noktaları, metrikler, ağ tablosu, bulgular, öneriler, galeri |

Katmanlar (alttan üste): Takviye, Gümüş, Dielektrik, Gümüş köprü (2. baskı), LED, Etiket, **Kontrol** (taramadan
kesin okunamayan rotalar, mor kesikli — teslimde açık kalsın), Kesim. SVG'yi CorelDRAW'da Dosya > Aç ile 1:1 mm açın;
opaklık nesne bazındadır (grup opaklığı CorelDRAW'da kaybolabilir). HTML raporu klasörüyle (`<AD>_rapor_gorseller/`)
birlikte taşıyın. Kalıcı değişiklik `parts/<ad>_design.py` içinde yapılıp `fpc.py all <ad>` ile yeniden üretilir.

## 7. Doğrulama ve kabul

`fpc.py verify <ad>` çizimi taramaya bindirir. Ana metrikler:

- **Alt-piksel kenar sapması (maske)**: çizim kenarı boyunca ~0.06 mm aralıkla örnek; normal doğrultusunda ölçüm
  maskesinin kenarı alt-piksel bulunur. İşaret: + çizim geniş/dışarıda, − dar/içeride. Eleman bazında
  `sapma = ofset + n·kayma` modeli → her eleman için ofset (genişlik yanlılığı) ve kayma vektörü.
  (Önceki tam-piksel metrik her parçada 2 px = 0.042 mm veriyordu; bilgi olarak raporda duruyor.)
- **Yoğunluk kenarı (maskeden bağımsız)**: renkli görüntüde yarı-yükseklik geçişi; maske eşiği yanlıysa
  `maske_yanliligi` uyarısı verir. ±6 px'ten büyük sapmayı ölçemediği için kabul kapısı değildir.
- **Gölge hariç karşılıksız gümüş**: taramada olup çizimde olmayan gümüş (gölge modeliyle açıklananlar çıkarılır).

Kabul kapıları (`verify.ESIK`, parça bazında `parts/<ad>.json "esik"` ile değiştirilebilir):

| Kapı | Eşik | Tip |
|---|---|---|
| Gümüş kenar \|sapma\| medyan / %90 | ≤ 0.06 / ≤ 0.15 mm | hepsi |
| Gümüş kenar kapsaması | ≥ 0.80 | hepsi |
| Dielektrik IoU, kenar medyan / %90 | ≥ 0.95, ≤ 0.06 / 0.15 mm | tuş |
| Karşılıksız gümüş (gölge hariç) | ≤ 0.15 (tuşta yalnız uyarı) | LED |
| Bilinmeyen ağ/tutarlılık HATA'sı | 0 | hepsi |

Görseller (`work/<ad>/`): `overlay.png` (kırmızı gümüş, mavi köprü, yeşil dielektrik, mor kesim, turuncu karşılıksız,
gri gölgeyle açıklanan), `ov_sapma.png` / `kontrol_sapma_*` (sapma ısı haritası), `ag_haritasi.png`,
`golge_haritasi.png`.

## 8. Ağ ve tasarım tutarlılığı kontrolleri

`fpc.py check <ad>` (taramasız) çizim geometrisinden elektrik ağlarını çıkarır: alt gümüş bileşenleri birleştirilir,
köprü yalnız dielektrik dışında değdiği parçaları bağlar. Pin = `Kontak_<no>` hatları, cihaz = LED pedleri
(`<led>_ped_ust/alt`) ve tuş pedlerinin tarakları (`Ped_<ad>`). Bu adlandırma kurallarına uyun ya da `Design.pins` /
`Design.devices` ile açıkça tanımlayın.

- **HATA** (kabulü düşürür): `kisa_devre`, `pinsiz_ag`, `tarak_sayisi`, `yalitimsiz_kesisim`, `led_uclari`
- **UYARI**: `yakin_bosluk` (değmesi gereken uç kısa ya da aralık dar), `serbest_uc`, `ayrik_pinler`, köprü bindirmesi
  / ucu yalıtkanda, `ince_bolge`, `mikro_segment`, `dar_donus`, `kontur_disi`, `kesim_payi`, `ust_uste_hat` …
- **BİLGİ**: `bitisik_pinler`, `gereksiz_dugum`, `aci_45_disi`

Bulgu kimlikleri kararlıdır (`kod:anahtar`). Kullanıcının bilerek kabul ettiği bulgular
`parts/<ad>.json "kabul_edilen_bulgular": {"<kimlik veya glob>": "gerekçe"}` ile "bilinen" yapılır (kapıyı düşürmez,
raporda gerekçesiyle kalır) — yalnız kullanıcı onayıyla.

Genel onarımlar (`onar.py`, tasarım modülünden çağrılır):
- `uc_kenetle(D)`: kısa kalan hat uçlarını pede/hatta uzatır; kısa devre yaratacak veya iki ayrı pinli ağı
  birleştirecek uzatmayı **reddeder** (taramadaki gerçek boşluk korunur).
- `kopru_uc_kurali(sel, traces_px)`: rotanın ucunu yama içinde bitiren parça köprü olamaz → alt baskı.

## 9. Gelişmiş ölçüm araçları (Faz 2)

- **Gölge modeli** (`golge.py`): film camdan kalkıksa her gümüş şeklin koyu kopyası δ kadar yukarı düşer. Karo bazında
  δ kestirilir (K.pdf: 0.30–0.36 mm genel, P3 sağ üstte 0.3–0.5 mm = kalkık/bulanık bölge). Gölge maskesi doğrulamadan,
  tuş tipi referans maskesinden ve profil refine'dan çıkarılır.
- **Kalibrasyon** (`kalibre.py`): `olcek` — DTFT kaba periyot + yarı-yükseklik ağırlıklı merkezler + MAD ayıklamalı fit
  (P2 1.0019 mm, P3 1.0003 mm @47.17); artık RMS > 1 px ise ROI kötüdür. `bukulme` — film bükülmesi (P4'te elle
  ölçülenle korelasyon 0.982).
- **Öneriler** (`oneri.py`, verify sonunda otomatik): hizalama, dielektrik kayma telafisi, hat genişliği, eleman
  taşıma/daraltma. Otomatik uygulanmaz.
- **Profil refine** (isteğe bağlı, `parts/<ad>.json "refine_yontemi": "profil"`): rota merkezleri yoğunluk kenarıyla
  inceltilir, gölgeli kenar atlanır. Önce `fpc.py refine_dene <ad>`. P1/P3'te açık değildir.
- **Ön + arka tarama çakıştırma** (`kayit.py`): arka yüz görüntüsü aynalanıp yapı haritası (gradyan) üzerinden faz
  korelasyonu + ECC afin ile ön görüntüye hizalanır; yerel artık (film deformasyonu) raporlanır. PET saydam olduğundan
  arkadan 1. gümüş baskı dielektrik/köprü örtüsü olmadan görünür → köprü üst/alt kararları ve kaplama altı pedler
  arka görüntüden okunur. Yapılandırma:
  ```json
  "arka": {"pdf": "docs/K_arka.pdf", "sayfa": 0, "goruntu_indeksi": 0, "kirpim_px": [x0, y0, x1, y1],
           "ayna": "yatay", "aci_derece": 0.0}
  ```

## 10. Öğrenen segmentasyon ve otomatik rota önerisi (Faz 3)

**Öğrenen piksel sınıflandırıcı** (`ogren.py`): onaylı çizimler taramaya bindirilerek her piksele malzeme etiketi
verilir (film, gümüş, yalıtkan altı gümüş, köprü, dielektrik, gölge; sınırlar, LED kaplaması ve Kontrol rotaları
etiket dışı). 17 renk/doku özelliğiyle `cv2.ml.RTrees` eğitilir; parça tipine göre ayrı modeller
(`model_tus.yml`, `model_led.yml`) + hepsi için `model.yml`.

```
fpc.py ogren dene p1,p2,p3,p4     # bırak-birini-dışarı: bu tarayıcıda öğrenen maske el maskesinden iyi mi?
fpc.py ogren egit all             # modelleri eğit (~10 dk, 12 çekirdek CPU)
fpc.py ogren uygula <ad>          # m_ogren_*.npy, m_ogren_gumus_hepsi.npy, ogren_siniflar.png (~3–4 dk / parça)
```

Bırak-birini-dışarı sonucu (`work/_ogren/dene.json`; her parça yalnız aynı tipteki diğer parçayla eğitildi;
gümüş IoU, çizimden etiketlere göre; öğrenen / mevcut el maskesi):

| Parça | Eğitim | Öğrenen | El maskesi | Piksel doğruluğu |
|---|---|---|---|---|
| P1 | P3 | **0.79** | 0.76 | 0.80 |
| P2 | P4 | **0.89** | 0.87 | 0.93 |
| P3 | P1 | **0.76** | 0.70 | 0.92 |
| P4 | P2 | 0.61 | **0.80** | 0.71 |

Üç tüm parçayla eğitildiğinde P3 0.81'e çıkar (tip karışık eğitim). P4'te el maskesi açıkça daha iyidir: öğrenen
maske her yeni parçada/tarayıcıda önce `ogren dene` ile doğrulanmadan kullanılmamalıdır.

**Otomatik rota önerisi** (`topoloji.py`): maskeden 0/45/90/135° aday segmentler → ped/leke ve sahte çaprazların
elenmesi → MILP (`scipy.optimize.milp`) ile paralel/örtüşen çift algılamalardan biri → doğrusal birleştirme → graf →
rotalar (`work/<ad>/rota_onerisi.py`, düşük güvenliler `flag=True`). Öğrenen maske varsa onu kullanır.
Mevcut elle yazılmış rotalarla kıyas (geri çağırma / kesinlik): P1 0.69 / 0.80, P3 0.73 / 0.74 (el maskesiyle P3
0.27 / 0.43). Öneri bir **başlangıçtır**; elektrik mantığını bilmez, `fpc.py check` şarttır.

## 11. Regresyon ve testler

- `fpc.py selftest`: 30 sentetik test (kenar metriği ofset/kayma geri kazanımı, yoğunluk kenarı ve bulanıklık,
  gölge kestirimi, ölçek ve bükülme, ön+arka çakıştırma, ağ çıkarımı, köprü/tutarlılık kuralları, onarımlar).
  Skill betikleri değiştirildiğinde hepsi `TAMAM` olmalı.
- `fpc.py altin <ad>`: mevcut doğrulama sonucunu `parts/<ad>_altin.json` olarak onaylar (metrikler, ağ imzası, bulgu
  kimlikleri).
- `fpc.py regress all`: her parça için verify + altınla karşılaştırma; metrik kötüleşmesi, ağ imzası değişikliği veya
  yeni HATA → çıkış kodu 1. Bilinçli iyileşme `altin` ile onaylanır.

## 12. Repoda olmayan dosyalar

`.gitignore` ile dışarıda tutulanlar ve yeniden üretimi:

| Dosyalar | Neden | Yeniden üretim |
|---|---|---|
| `work/_ogren/*.yml` (öğrenen modeller: `model.yml` ~254 MB, `model_led.yml` ~175 MB, `model_tus.yml` ~100 MB) | GitHub 100 MB üstü dosyaları reddeder | `python .devin/skills/fpc-vektor/scripts/fpc.py ogren egit all` (~10 dk) |
| `work/**/*.npy` (maskeler, doku/gölge haritaları) | büyük ara dosyalar | `fpc.py prep <ad>` + `fpc.py segment <ad>` (+ `fpc.py ogren uygula <ad>`) |
| `work/**/*.png`, `*.jpg` (deskew görüntü, analiz görselleri) | büyük ara dosyalar | `fpc.py prep/segment/verify <ad>`; rapor kopyaları `output/<AD>_rapor_gorseller/` içinde repodadır |
| `__pycache__/`, `*.pyc`, `output/*_yeni.pdf` | geçici | — |

`work/_ogren/meta.json` (hangi parçalarla eğitildi) ve `dene.json` (değerlendirme) repodadır. Temiz bir klonda
`fpc.py all <ad>` önce `prep` ve `segment` ile ara dosyaları kendisi üretir.

## 13. Bilinen durum ve bekleyen işler

| Parça | Kabul | Not |
|---|---|---|
| P2 | GEÇTİ | ağ tablosu RAPOR pin eşlemesiyle birebir; kenar 0.021 / 0.067 mm |
| P4 | GEÇTİ | film bükük (`bukulme`), dielektrik baskı kayması telafili; karşılıksız gümüş uyarısı |
| P1 | KALDI | 4 HATA: B1/R3/R4, B2, B3, C1 üst pedleri pinsiz (leke bölgesi, taramadan çözülemedi); pin 6 ile 9 aynı ağda |
| P3 | KALDI | 2 HATA: L5/R5 alt ve R6 alt pinsiz; kenar (maske) 0.064 / 0.171 mm — yoğunluk kenarı 0.045 / 0.090 mm |

Bekleyenler (ayrıntı `AGENTS.md`):
- **Arka yüz taraması** (P1–P4, film ters çevrilmiş, aynı dpi, kayıpsız TIFF/PNG tercih) → `fpc.py kayit` ile
  kalan HATA'ların çoğu (köprü üst/alt, leke altı pedler) çözülür.
- **Cetvel / mm ızgara** aynı camda: y yönü ölçeği (`fpc.py olcek ... y`).
- **Multimetre** (P3): pin 1–8, L5/R5 alt pedleri, B2 alt / Z bağlantıları.
- Rota önerisinin ağ kısıtlarıyla (her ped bir pine, kısa devre yok) birleştirilmesi.

## 14. Sorun giderme

- **Açık PDF kilidi**: IDE/görüntüleyicide açık PDF'in üzerine yazılamazsa `<ad>_yeni.pdf` üretilir; dosyayı kapatıp
  tekrar çalıştırın.
- **Konsolda bozuk Türkçe karakter / UnicodeEncodeError**: `PYTHONIOENCODING=utf-8`.
- **`git push` SSL hatası** (`unable to get local issuer certificate`, kurumsal ağ): Windows sertifika deposunu kullanın —
  tek seferlik `git -c http.sslBackend=schannel push`, kalıcı `git config --global http.sslBackend schannel`.
  Sertifika doğrulamasını kapatmayın.
- **Kabul kaldı**: `references/05-dogrulama.md` §5.6 — önce `check` HATA'ları, sonra `elemanlar_en_kotu` ve
  `kontrol_sapma_*`, sistematik ofsette önce maske yanlılığını kontrol edin.
