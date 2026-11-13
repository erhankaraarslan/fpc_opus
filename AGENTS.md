# FPC_OPUS — taramadan vektör FPC çizimi

Kaynak: `docs/K.pdf` (tek sayfa, 10192x14016 px JPEG, ~1199 dpi). Üzerinde 4 FPC var:
P1 (kısa LED), P2 (kısa 3 tuşlu membran), P3 (uzun LED), P4 (uzun 3 tuşlu membran).
P1/P2 ve P3/P4 üst üste binen setlerdir (LED'ler tuş katmanındaki oval pencerelerin altında).

## Yöntem: `fpc-vektor` skill'i
Tüm iş akışı, araçlar ve kurallar `.devin/skills/fpc-vektor/` altında:
- `SKILL.md` iş akışı + kabul kapıları, `references/` ayrıntılar, `scripts/` araçlar, `templates/` örnekler.
- Tek giriş noktası (proje kökünden): `python .devin/skills/fpc-vektor/scripts/fpc.py <komut> <ad>`
  komutlar: `skew | prep | segment | golge | ovals | build | check | verify | report | all | oneri | olcek | bukulme |
  refine_dene | kayit | altin | regress`, `selftest`
- Windows konsolunda Türkçe çıktı için `PYTHONIOENCODING=utf-8` kullan.
- Parça tanımları: `parts/<ad>.json` (kırpım, açı, tip, ROI, rapor kırpımları),
  `parts/<ad>_design.py` (build() + RAPOR), LED tipinde `parts/<ad>_routes.py`.
- Ara dosyalar `work/<ad>/`, çıktılar `output/<AD>_{duzenlenebilir,uretim}.svg`, `_uretim.pdf`,
  `_kontrol_taramali.svg`, `_rapor.{md,html,pdf}`.

## Durum (Faz 1 sonrası: alt-piksel kenar metriği + ağ/tutarlılık kontrolleri + regresyon)
- P2: KABUL GECTI; ağ tablosu RAPOR pin eşlemesiyle birebir. Kenar 0.021/0.070 mm (şerit içi maske eşiği düzeltildi).
- P4: KABUL GECTI. Film bükük -> `parts/p4.json` "bukulme"; dielektrik baskı kayması `DIEL_KAYMA`
  (çizim ideal, doğrulama telafili). Karşılıksız gümüş 0.19 (uyarı).
- P1: KABUL KALDI — kenar metrikleri geçiyor ama çizimde 8 LED üst pedi boyun hattına 0.07–0.16 mm
  değmiyor (pinsiz_ag + yakin_bosluk), R2L_alt kontur dışına taşıyor, C1_ust köprüsü yalıtkanda bitiyor.
  Rota düzeltmesi kullanıcı onayı bekliyor. 12 rota Kontrol katmanında.
- P3: KABUL KALDI — alt-piksel kenar 0.064/0.172 mm (eski piksel metriği 0.042/0.131 gösteriyordu),
  karşılıksız 0.207, HATA: L5/R5 alt ve R6 alt pinsiz (R6_alt köprüsü yalıtkanda bitiyor; Poz7/Poz10 T-bağlantıları
  yama içinde). Pin 1 = pin 8. Maskeler: rota `m_dark`, doğrulama `m_band`.
- Faz 2 (tamam): gölge modeli (golge.py), yoğunluk kenarı (profil.py, maskeden bağımsız), maske yanlılığı uyarısı,
  ölçek/bükülme kalibrasyonu (kalibre.py), düzeltme önerileri (oneri.py), profil refine (isteğe bağlı,
  `refine_yontemi`; P1/P3'te açılmadı — kullanıcı onayı bekliyor), ön+arka çakıştırma (kayit.py; gerçek arka tarama
  bekleniyor), tuş tipi ped referans maskesi (yerel orta eşik). P3 yoğunluk kenarı 0.045/0.090 mm (m_band maskesi
  0.064/0.170 gösteriyor: maske gürültülü).
- Faz 2 sonrası düzeltmeler (kullanıcı onayıyla): P1 uç kenetleme (7 ped ucu; pin 1 ve pin 3 artık RAPOR'la uyumlu),
  yarık üst ucu 69.9 → 70.7 mm (yeniden ölçüm), C1_ust köprü uç kuralı; P3 köprü uç kuralı (Poz7, Poz10, R6_alt), Q_R8
  pah düzeltmesi. Kalan HATA: P1 4 (B1/R3/R4, B2, B3, C1 üst pedleri — leke bölgesi), P3 2 (L5/R5 alt, R6 alt — birleşik
  çift yama). Bunlar arka tarama/multimetre bekliyor.
- Faz 3: `ogren.py` (onaylı çizimlerden etiket, RTrees; tip bazlı modeller work/_ogren/), bırak-birini-dışarı gümüş IoU
  öğrenen/el (aynı tip eğitim, work/_ogren/dene.json): P1 0.79/0.76, P2 0.89/0.87, P3 0.76/0.70, P4 0.61/0.80 (P4'te el maskesi daha iyi — öğrenen maske
  her parçada `ogren dene` ile doğrulanmadan kullanılmaz). `topoloji.py` otomatik rota önerisi (aday + MILP + graf):
  P1 geri çağırma/kesinlik 0.69/0.80, P3 0.73/0.74 (öğrenen maskeyle; el maskesiyle P3 0.27/0.43).
- Altın (regresyon) durumları `parts/<ad>_altin.json` = Faz 3 sonundaki mevcut durum (bilinen hatalar dahil).
- Yol haritası (kullanıcıyla kararlaştırıldı): hedef CorelDRAW'da düzenlenecek çizim + dokümantasyon (üretim değil);
  skill genel olmalı (yalnız K.pdf'e özel değil); kullanıcı bundan sonra **ön ve arka yüz ayrı taramaları** verebilir.
  Faz 3: öğrenen segmentasyon (kabul edilmiş çizimlerden etiketli piksel sınıflandırıcı) + otomatik topoloji önerisi
  (aday segment + MILP) + arka taramayla köprü/katman kararı.

## Bekleyenler (kullanıcı "daha sonra" dedi — unutma)
- **Arka yüz taraması** (kullanıcı verecek): P1–P4'ün arkadan taranmış hali (film ters çevrilmiş, aynı dpi,
  kayıpsız TIFF/PNG tercih). Gelince: `parts/<ad>.json "arka"` → `fpc.py kayit <ad>` → köprü üst/alt kararları,
  P3 L5/R5 ve pin 1=8 belirsizliği, LED pedlerinin kaplama altı ölçüsü arka görüntüden (references/04 §8a).
- **Cetvel / mm ızgara** aynı camda taranacak: y yönü ölçeği (`fpc.py olcek ... y`), x ile fark > %0.1 ise
  tarayıcı motor yönü hatası.
- **Multimetre** (P3): pin 1–8 kısa mı, L5/R5 alt pedleri hangi pine, B2 alt pin 6 / Z pin 4 (p3_analiz.json).

## Python bağımlılıkları (kullanıcı dizinine kurulu, sürümler sabit)
opencv-python-headless==4.10.0.84, scipy==1.16.2, scikit-image==0.25.2, shapely==2.1.1,
tifffile==2025.6.11, imageio==2.37.0, lazy-loader==0.4 (pymupdf, numpy, networkx mevcut).
Yeni yayınlanmış (<7 gün) bağımlılık sürümlerini kullanma.

## Notlar
- Ölçek konnektör adımı 1.00 mm ile kalibre: 47.17 px/mm (tarayıcı nominal 47.21).
- IDE'de açık bir PDF kilitliyse yazıcı `<ad>_yeni.pdf` üretir; dosyayı kapatıp tekrar çalıştır.
