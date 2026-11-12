---
name: fpc-vektor
description: Taranmış (raster PDF) esnek baskılı devre / membran devre parçalarını CorelDRAW'da düzenlenebilir, mm ölçekli, katmanlı vektör çizime (SVG + PDF) dönüştürür; taramaya bindirerek sayısal doğrular ve MD/HTML/PDF rapor üretir.
argument-hint: "[parça adı veya PDF yolu]"
allowed-tools:
  - read
  - grep
  - glob
triggers:
  - user
  - model
---

# fpc-vektor — Taramadan kusursuz FPC vektör çizimi

Bu skill, bir PDF içindeki tarama görüntüsünde bulunan FPC (gümüş mürekkep baskılı PET membran
devre) parçalarını **ölçülmüş, temizlenmiş, parametrik** vektör çizime çevirir. Çıktı bir "iz
sürme" (trace) değil, tasarım niyetini yansıtan temiz geometridir: hatlar sabit genişlikte merkez
çizgileri, köşeler 0/45/90°, pedler ölçülü dikdörtgenler, kesim konturu gerçek yaylarla.

Kaliteyi model değil **betikler ve sayısal kabul eşikleri** belirler. Bu dosyadaki adımları sırayla,
atlamadan uygula. Her adımın bir *kabul kapısı* vardır; kapıyı geçmeden sonraki adıma geçme.

## Dosya düzeni

```
.devin/skills/fpc-vektor/
  SKILL.md                 bu dosya (iş akışı + kurallar)
  scripts/                 tüm araçlar (proje kökünden çalıştırılır)
    fpc.py                 TEK GİRİŞ NOKTASI: skew|prep|segment|ovals|build|verify|report|all <ad>
    inspect_scan.py        PDF analizi + parça tespiti
    fpcvec.py              geometri modeli (Design) + SVG/PDF yazıcılar
    measure.py gridview.py ovals.py traces.py refine.py routes_view.py segfind.py seglist.py polyvec.py
    segment.py (tuş) segment_led.py (LED) verify.py report.py cfg.py prep.py skew.py
  references/              AYRINTILAR — ilgili adımda oku (aşağıda hangi adımda hangisi)
  templates/               parca.json + çalışan tuş/LED tasarım örnekleri
Proje tarafı:
  parts/<ad>.json          parça yapılandırması      parts/<ad>_design.py   parametrik tasarım
  parts/<ad>_routes.py     (LED tipi) kaba rotalar   work/<ad>/             ara dosyalar + analiz görselleri
  parts/<ad>_analiz.json   analiz kaydı (süreç, bulgular, kararlar, görsel açıklamaları, yönlendirme)
  output/                  <AD>_duzenlenebilir.svg, <AD>_uretim.svg, <AD>_uretim.pdf,
                           <AD>_kontrol_taramali.svg, <AD>_rapor.{md,html,pdf}
```

Komut kısaltması: `FPC="python .devin/skills/fpc-vektor/scripts/fpc.py"` (proje kökünde).

## Altın kurallar (ihlal etme)

1. **Ölçmeden çizme.** Her sayı bir ölçüme (profil, fit, sayım) dayanmalı. Görselden "göz kararı"
   okunan değer yalnızca *kaba başlangıç* içindir; refine/ölçüm araçlarıyla kesinleştirilir.
2. **Görsel okuma sınırı:** büyük görüntüleri tek seferde okuma; `gridview.py` ile ızgaralı, en fazla
   ~1000 px kenarlı kırpımlar üret. Koordinatı ızgara etiketinden oku, sonra `measure.py` ile doğrula.
3. **Gölge kopyası tuzağı:** film camda düz yatmıyorsa her gümüş kenarın ~0.4–0.6 mm *üstüne* koyu,
   pürüzsüz bir gölge kopyası düşer. Bunu ikinci hat/ped sanma (references/02).
4. **Tasarım niyeti:** ölçülen değerleri 0.05 mm'ye yuvarla; simetri, ortak adım (ör. 1.0 mm konnektör,
   1.1 mm tarak adımı), ortak eksen gibi niyetleri ara ve uygula. Ölçüm ile niyet çelişirse ölçümü
   koru ve rapordaki *varsayımlar* listesine yaz.
5. **Belirsizliği sakla değil, işaretle:** taramadan kesin okunamayan her bağlantı `flag=True`
   (Kontrol katmanı) + RAPOR["kontrol_listesi"] maddesi olur. Uydurma bağlantıyı "kesin" diye sunma.
6. **Kısa devre/kopukluk kontrolü:** her LED'in iki pedinin farklı ağlarda olduğunu, her ağın bir
   konnektör pinine ulaştığını mantık olarak kontrol et (references/04 §Ağ mantığı).
7. **Bağımlılık:** yeni paket gerekiyorsa en az 7 gün önce yayınlanmış sürümü sabitle
   (`pip install --user paket==sürüm`). Geçişli bağımlılıklar dahil (ör. tifffile).
8. **Analiz kaydını iş yaparken tut:** `parts/<ad>_analiz.json` (şablon `templates/analiz.json`).
   Her anlamlı görseli `work/<ad>/` altına anlamlı adla kaydet ve kayda açıklamasını ekle; her karar
   noktasını (seçenekler, seçilen, gerekçe, kanıt) ve kullanıcıya verdiğin her bilgilendirme ile
   öneriyi yaz. Rapor yalnızca bu kayıttan beslenir; sohbette söylenip kayda girmeyen bilgi kaybolur
   (references/06 §6.5–6.7).
9. **Silme/üzerine yazma:** kullanıcının açık tuttuğu PDF kilitliyse yazıcı `_yeni.pdf` üretir;
   kullanıcıya dosyayı kapatmasını söyle. Kullanıcı dosyalarını sormadan silme.

## İş akışı

### Adım 0 — Ortam (bir kez)
Gerekli: Python 3.10+, `pymupdf numpy opencv-python-headless scipy scikit-image shapely networkx`.
Kontrol: `python -c "import pymupdf,cv2,scipy,skimage,shapely,networkx"`. Eksikse references/09 §Kurulum.

### Adım 1 — Kaynağı incele → references/01
```
python .devin/skills/fpc-vektor/scripts/inspect_scan.py docs/<dosya>.pdf
```
- `work/_tarama/bilgi.json`: efektif dpi, px/mm, metin var mı. Metin yoksa = tarama.
- `work/_tarama/genel.png` ve `parca_<n>.png` dosyalarını oku; her parçayı tanımla (tip: tuş/LED),
  setleri (üst üste binen katmanlar) eşleştir.
- **Kapı 1:** parça listesi ve tipleri kullanıcıyla paylaşıldı; hangi parçanın çizileceği, amaç
  (üretim/dokümantasyon), format ve katmanlar soruldu (ask_user_question). Önerilen: önce tek parça
  ile pilot, onay sonrası diğerleri.

### Adım 2 — Parça yapılandırması
`templates/parca.json` → `parts/<ad>.json`. `kirpim_px` = inspect çıktısı. `tip` = tus|led.
```
$FPC skew <ad>      # önerilen aci_derece -> json'a yaz
$FPC prep <ad>      # work/<ad>/<ad>_deskew.png
```
- **Kapı 2:** deskew sonrası uzun hatlar dikey/yatay: `python .../traces.py` veya `measure.py` ile
  bir uzun dikey hattın x'i baş ve sonda ≤ 2 px fark etmeli. Değilse açıyı ±0.05° ayarla, tekrarla.

### Adım 3 — Maskeler → references/02
`$FPC segment <ad>`  → tuş tipi: `silver/tealm/teal_closed/sil_teal/silver_ref.npy`;
LED tipi: `m_top/m_under/m_teal/tex.npy`. `seg3.png` / `seg_led.png` görselini kırpıp kontrol et.

### Adım 4 — Ölçek kalibrasyonu ve ana ölçüler → references/01, 03, 04
1. Kuyrukta konnektör hatlarının merkezlerini ölç: `measure.py <ad> h y0 y1 x0 x1` (T kanalı
   kenarları). Merkezlere doğru oturt → adım (px). 1.00 mm kabul et → `olcek_px_mm` (tarayıcı
   nominaliyle %0.3 içinde olmalı; değilse nedenini araştır).
2. Kesim konturu: baş sol/sağ/üst/alt, kuyruk kenarları, yarıklar, kuyruk ucu, köşe yarıçapları
   (`measure.py` L kanalı; gölge kuralı: üst kenarlarda gölge *üstte*, gerçek kenar gölgenin altı).
3. Eksen: konnektör merkezi = kart ekseni varsay; baş kenarlarıyla karşılaştır, farkı rapora yaz.

### Adım 5 — Parça tipine göre geometri
- **Tuş devresi (tek gümüş + dielektrik şerit + ovaller):** references/03'ü baştan sona uygula.
  Örnek: `templates/tus_design_ornegi.py` → `parts/<ad>_design.py`.
- **LED devresi (iki gümüş baskı + köprü yamaları + LED):** references/04'ü baştan sona uygula.
  Örnekler: `templates/led_design_ornegi.py`, `templates/led_rotalar_ornegi.py`.
  Rota döngüsü: kaba rota yaz → `routes_view.py` ile bindir → hatalı segmenti düzelt → tekrar.

Tasarım modülü sözleşmesi: `build() -> fpcvec.Design` ve `RAPOR` sözlüğü (references/06 §RAPOR).

### Adım 6 — Üret, doğrula, raporla → references/05, 06
```
$FPC build <ad>     # 4 çizim dosyası + otomatik dosya/katman kontrolü
$FPC verify <ad>    # metrikler + work/<ad>/overlay.png + kontrol_*.png
$FPC report <ad>    # output/<AD>_rapor.md / .html / .pdf
```
- **Kapı 3 (kabul):** `KABUL: GECTI` ve `overlay.png` kırpımlarında her bölge görsel olarak tutarlı.
  Eşikler (verify.py ESIK): kenar sapması medyan ≤ 0.06 mm, %90 ≤ 0.15 mm; tuş tipinde dielektrik
  IoU ≥ 0.95; LED tipinde karşılıksız tarama gümüşü ≤ 0.15. Kalırsa references/05 §Kaldıysa.
- Turuncu (karşılıksız gümüş) kümeleri tek tek incele: gölge/kaplama/leke mi, çizilmemiş hat mı?
  Çizilmemiş hatsa ekle; yorumluysa `flag=True`.

- **Kapı 4 (rapor):** `parts/<ad>_analiz.json` dolu (süreç, bulgular, karar noktaları,
  yönlendirme); `fpc.py report` çıktısında "açıklamalı" görsel sayısı, karar kanıtı ve topoloji/ölçüm
  görsellerinin tamamını kapsıyor; HTML tarayıcıda hatasız açılıyor.

### Adım 7 — Kullanıcıya teslim
Kısa özet: dosyalar (ref_file), katmanlar, metrikler (sayılarla), varsayımlar ve fiziksel kontrol
listesi, sonraki parça önerisi. Raporun yolunu ver. Uzun tablo yazma; rapor dosyası onu taşıyor.

## Kullanıcıya sorulacak durumlar (tahmin etme)
- Hangi parçalar, amaç (üretim/dokümantasyon), formatlar, katmanlar — Adım 1 sonunda.
- Belirsiz bağlantı sayısı > 3 ise: devam / yeni tarama (düz bastırılmış, mümkünse arkadan ışıklı,
  2400 dpi) / multimetre ile doğrulama seçeneklerini sun.
- Ölçek kalibrasyonu tarayıcı nominalinden > %0.3 sapıyorsa.
- Kabul kapısı iki iyileştirme turundan sonra hâlâ geçmiyorsa.

## Hangi referans ne zaman
| Dosya | Ne zaman |
|---|---|
| references/01-tarama-ve-olcek.md | Adım 1, 2, 4 |
| references/02-maskeler-ve-artefaktlar.md | Adım 3 ve her "garip şekil" gördüğünde |
| references/03-tus-devresi.md | Adım 5 (tuş) |
| references/04-led-devresi.md | Adım 5 (LED) |
| references/05-dogrulama.md | Adım 6 |
| references/06-ciktilar-ve-coreldraw.md | Adım 6–7, katman/renk/rapor sözleşmesi |
| references/07-ornek-degerler.md | Benzer parçalarda başlangıç değeri ve kıyas |
| references/08-hatalar-ve-dersler.md | Başlamadan önce bir kez; takıldığında |
| references/09-arac-referansi.md | Her betiğin parametreleri ve çıktıları |
