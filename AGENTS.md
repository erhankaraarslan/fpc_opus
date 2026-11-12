# FPC_OPUS — taramadan vektör FPC çizimi

Kaynak: `docs/K.pdf` (tek sayfa, 10192x14016 px JPEG, ~1199 dpi). Üzerinde 4 FPC var:
P1 (kısa LED), P2 (kısa 3 tuşlu membran), P3 (uzun LED), P4 (uzun 3 tuşlu membran).
P1/P2 ve P3/P4 üst üste binen setlerdir (LED'ler tuş katmanındaki oval pencerelerin altında).

## Yöntem: `fpc-vektor` skill'i
Tüm iş akışı, araçlar ve kurallar `.devin/skills/fpc-vektor/` altında:
- `SKILL.md` iş akışı + kabul kapıları, `references/` ayrıntılar, `scripts/` araçlar, `templates/` örnekler.
- Tek giriş noktası (proje kökünden): `python .devin/skills/fpc-vektor/scripts/fpc.py <komut> <ad>`
  komutlar: `skew | prep | segment | ovals | build | verify | report | all`
- Parça tanımları: `parts/<ad>.json` (kırpım, açı, tip, ROI, rapor kırpımları),
  `parts/<ad>_design.py` (build() + RAPOR), LED tipinde `parts/<ad>_routes.py`.
- Ara dosyalar `work/<ad>/`, çıktılar `output/<AD>_{duzenlenebilir,uretim}.svg`, `_uretim.pdf`,
  `_kontrol_taramali.svg`, `_rapor.{md,html,pdf}`.

## Durum
- P2: tamam (`fpc.py all p2` -> KABUL GECTI).
- P1: tamam, 12 rota "Kontrol" katmanında işaretli (fiziksel doğrulama bekliyor; bkz. output/P1_rapor.md).
- P4: tamam (KABUL GECTI). Film bükük -> `parts/p4.json` "bukulme" (satır bazlı düzeltme); dielektrik baskı
  kayması `DIEL_KAYMA` (çizim ideal, doğrulama telafili).
- P3: çizildi, KABUL KALDI yalnız "karşılıksız gümüş" 0.207 (kaplama + bulanıklık; kullanıcı "devam et, işaretle"
  seçti). 10 rota Kontrol katmanında; L5/R5 alt pedleri pinsiz görünüyor, pin 1 = pin 8 (multimetre bekliyor).
  Maskeler: rota `m_dark`, doğrulama `m_band` (parts/p3.json `rota_maskesi` / `dogrulama_maskesi`).

## Python bağımlılıkları (kullanıcı dizinine kurulu, sürümler sabit)
opencv-python-headless==4.10.0.84, scipy==1.16.2, scikit-image==0.25.2, shapely==2.1.1,
tifffile==2025.6.11, imageio==2.37.0, lazy-loader==0.4 (pymupdf, numpy, networkx mevcut).
Yeni yayınlanmış (<7 gün) bağımlılık sürümlerini kullanma.

## Notlar
- Ölçek konnektör adımı 1.00 mm ile kalibre: 47.17 px/mm (tarayıcı nominal 47.21).
- IDE'de açık bir PDF kilitliyse yazıcı `<ad>_yeni.pdf` üretir; dosyayı kapatıp tekrar çalıştır.
