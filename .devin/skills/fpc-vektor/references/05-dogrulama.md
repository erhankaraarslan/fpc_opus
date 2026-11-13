# 05 — Doğrulama ve kabul

## 5.1 Komutlar
- `fpc.py check <ad>`: taramaya bakmadan **ağ + tasarım tutarlılığı** (saniyeler). Rota/tasarım düzeltirken
  her değişiklikten sonra çalıştır → `work/<ad>/kontroller.json`, `ag_haritasi.png`.
- `fpc.py verify <ad>`: kenar metrikleri + ağ/tutarlılık + kabul → `work/<ad>/metrikler.json`,
  `eleman_sapma.json`, `overlay.png`, `ov_sapma.png`, `kontrol_<k>.png`, `kontrol_sapma_<k>.png`, `ag_haritasi.png`.
- `fpc.py regress <ad|all>` / `fpc.py altin <ad>`: onaylı durumla karşılaştırma (§5.6).
- `fpc.py selftest`: araçların sentetik doğruluk testleri (algoritma değişikliğinden sonra).
ROI: `parts/<ad>.json` `dogrulama_roi_y` (boş film ve kuyruk ucunun dokusu bozuk kısmı dışarıda).

## 5.2 Kenar metriği (alt-piksel, `kenar.py`)
Çizim kenarı boyunca ~3 px (0.06 mm) aralıkla örnek; köşelere 4 px yaklaşılmaz. Her örnekte dış normal boyunca
ölçüm maskesi (σ=1 yumuşatılmış) alt-piksel örneklenir; 0.5 düzeyini içeriden dışarı kesen en yakın nokta =
ölçülen kenar. **sapma d > 0: çizim dışarı taşıyor (geniş), d < 0: içeride (dar).** ±12 px içinde kenar yoksa
örnek "eşleşmedi". Eleman bazında `d = a + n·s` uydurulur: **a = her yandan ofset** (hat genişliği farkı ≈ 2a),
**s = kayma vektörü**. Sentetik testte ofset/kayma ±0.05 px içinde geri bulunur (`selftest`).
Eski tam-piksel Canny metriği `piksel` alanında bilgi olarak durur (tam piksele kuantizeydi: medyan hep 2 px).
Dış tarafı gölge maskesine (`m_golge.npy`) düşen örnekler metrik dışıdır (`golge_orani`).

## 5.2a Yoğunluk kenarı (maskeden bağımsız, `profil.py`)
Aynı örneklerde renkli görüntünün normal profili alınır; iç/dış plato (çizim kenarından ∓4–8 px) arasındaki renk
farkı yönüne izdüşüm → 0..1 profil → yarı-yükseklik (0.5) geçişi = malzeme sınırı (eşik seçimi yok). Ayrıca
bulanıklık σ (Gauss PSF varsayımı). Sentetik testte ofset/kayma ±0.04 px, σ ±0.1 px.
- **Kullanım:** sistematik ofset/kayma ve genişlik kestirimi (`oneri`), maske yanlılığı tespiti.
- **Kapı değildir:** ±6 px'ten büyük sapmayı ölçemez (kapsama dışı kalır) → %90 iyimser olur; kapılar maske
  metriğindedir. İkisi farklıysa (`maske_yanliligi`, |fark| > 0.02 mm) maske eşiği düzeltilir.
- K.pdf: P2/P4 maske ve yoğunluk ofseti ±0.002 mm içinde uyumlu (maske düzeltmesinden sonra); P3 yoğunluk
  0.045/0.090 mm vs maske (m_band) 0.064/0.170 mm → P3 maskesi gürültülü, çizim sanıldığından iyi.

## 5.2b Düzeltme önerileri (`fpc.py oneri`, verify sonunda otomatik → `oneriler.json`, raporda bölüm)
Yoğunluk eleman tablosundan: genel hizalama (parametrik elemanlar için SCAN px0/py0), dielektrik kayma telafisi,
hat genişliği (aynı genişlikteki hatların medyan ofseti), tek eleman taşıma/daraltma. Otomatik uygulanmaz.

## 5.3 Kabul kapıları (`verify.ESIK`, parça bazında `parts/<ad>.json "esik"` ile değiştirilebilir)
| Kapı | Eşik | Tip |
|---|---|---|
| Gümüş kenar \|sapma\| medyan / %90 | ≤ 0.06 / ≤ 0.15 mm | hepsi |
| Gümüş kenar kapsaması | ≥ 0.80 | hepsi |
| Dielektrik IoU, kenar medyan / %90 | ≥ 0.95, ≤ 0.06 / 0.15 mm | tuş |
| Karşılıksız tarama gümüşü, gölge hariç (ham değer de raporlanır) | ≤ 0.15 (tuşta yalnız uyarı) | LED |
| Bilinmeyen ağ/tutarlılık HATA'sı | 0 | hepsi |
Uyarılar (kapı değil): \|ofset\| > 0.03 mm (`kenar_ofset`), eleman medyanı > 0.10 mm (`eleman_sapma`), ince hatta
kapsama < 0.5 (`eleman_eslesmedi`; ped/blok/LED pedinde bilgi — referans maske geniş alanda genelde eksik).

## 5.4 Ağ ve tutarlılık kontrolleri (`netlist.py`, `tutarlilik.py`; bulgu yapısı `bulgu.py`)
Ağ modeli: alt gümüş (köprü kesimli hatlar + dikdörtgenler) bileşenleri 1 µm toleransla birleştirilir; köprü
yalnız dielektrik DIŞINDA değdiği bileşenleri bağlar. Pin = `Kontak_<no>` (`_dummy`), cihaz = LED (`<led>_ped_*`)
ve tuş pedi (`Ped_*` grubunun ayrık tarakları) — ya da `Design.pins` / `Design.devices` (references/06 §6.3).
| Kod | Seviye | Anlam / tipik neden |
|---|---|---|
| kisa_devre, tarak_sayisi | HATA | cihazın iki ucu aynı ağda |
| pinsiz_ag | HATA | uç hiçbir pine ulaşmıyor: **çoğunlukla ped ile boyun hattı arasında birkaç 0.01 mm boşluk** (yakin_bosluk ile birlikte görünür) veya köprü ucu yalıtkanda |
| yalitimsiz_kesisim | HATA | köprü yalıtkan dışında başka alt gümüşe değiyor |
| ayrik_pinler | UYARI | bitişik olmayan pinler aynı ağda (bitişik blok = bilgi) |
| yakin_bosluk | UYARI | farklı ağlar < 0.2 mm: uç kısa kalmış ya da aralık dar |
| serbest_uc, yuzen_gumus, bos_pin, dummy_bagli | UYARI | açık uç / bağlantısız gümüş / boş pin |
| kopru_ucu_yalitkanda, kopru_bindirme, kopru_ucu_bosta, yalitim_payi | UYARI | köprü yerleşimi (T-bağlantı yama içinde kalmışsa köprü ucu yalıtkanda biter = bağlantı yok) |
| ince_bolge, mikro_segment, dar_donus, ust_uste_hat, kontur_disi, kesim_payi, pencere | UYARI | CorelDRAW'da temiz düzenleme / geometri hatası |
| gereksiz_dugum, aci_45_disi, bitisik_pinler | BILGI | gözden geçirme |
Bulgu kimliği kararlıdır (`kod:anahtar`). Kullanıcının bilerek kabul ettiği HATA/UYARI'lar
`parts/<ad>.json "kabul_edilen_bulgular": {"<kimlik veya glob>": "gerekçe"}` ile "bilinen" olur: kapıyı
düşürmez, raporda gerekçesiyle kalır. **Kullanıcı onayı olmadan kabul listesine ekleme.**

## 5.5 Görsel kontrol
- `overlay.png` / `kontrol_*`: kırmızı gümüş, mavi köprü, yeşil dielektrik, mor kesim/oval, turuncu = taramada
  gümüş var çizimde yok. Turuncu: yatay hattın hemen üstünde ince şerit → gölge; LED çevresinde halka → kaplama;
  hat genişliğinde uzun şerit → **çizilmemiş hat** (ekle).
- `ov_sapma.png` / `kontrol_sapma_*`: yeşil ≤ 0.02, sarı ≤ 0.05, turuncu ≤ 0.10, kırmızı > 0.10 mm, mor eşleşmedi.
  Bir kenar boyunca tek renk kırmızı = o kenar kaymış (eleman tablosundaki kayma yönüne bak); hattın iki yanı
  kırmızı = genişlik yanlış; mor = referans maske yok ya da eleman yanlış yerde.
- `ag_haritasi.png`: her ağ ayrı renk, pinsiz ağ gri + siyah kontur; HATA kırmızı, UYARI turuncu halka.
- `golge_haritasi.png`: karo bazında gölge ofseti δ (mm); büyük δ = kalkık film, ölçüm güveni düşük.
- `overlay.png` gri pikseller: gölgeyle açıklanan karşılıksız gümüş (turuncudan ayrıldı).

## 5.6 Kaldıysa
1. Önce `check` HATA'ları: pinsiz ağ → yakin_bosluk konumundaki ucu pede/hatta uzat; köprü ucu yalıtkanda →
   T-bağlantıyı yama dışına taşı veya köprü seçimini düzelt. Her düzeltmeden sonra `check`.
2. Kenar %90 yüksek: `metrikler.json elemanlar_en_kotu` ve `kontrol_sapma_*` ile kötü elemanı bul; kayma yönünde
   rota/ölçüyü düzelt (yanlış oturan refine segmenti, eksik pah, yanlış genişlik).
3. Sistematik ofset uyarısı: çizim genişliği ile maske eşiğini ayır — hat profilinin yarı-yükseklik genişliğini
   ölç (`measure.py`, T kanalı). P2'de ofset maskeden çıktı (T<20 maskesi 0.424 mm, gerçek 0.514 mm); segment.py
   şerit içi eşiği yerel orta eşiğe çevrildi.
4. Dielektrik IoU düşük: şerit genişliği / çerçeve ofseti / kuyruk sınırları; ofset/kayma satırı baskı kaymasını gösterir.
5. Karşılıksız gümüş yüksek: turuncu kümeleri sınıflandır; çizilmemiş hatları ekle; leke/damla bölgelerini ROI
   dışında bırakmak yerine rapora yaz (ROI'yi metrik makyajı için daraltma).
6. İki turda geçmiyorsa kullanıcıya sor (yeni tarama / multimetre / bulguyu kabul).

## 5.7 Regresyon
`fpc.py altin <ad>` onaylı durumu `parts/<ad>_altin.json`'a yazar (metrikler, ağ imzası, bulgu kimlikleri).
`fpc.py regress all`: her parça için verify + karşılaştırma; metrik toleransı aşan kötüleşme, ağ imzası
değişikliği veya yeni HATA → çıkış 1. Skill betiklerini değiştirdikten sonra `selftest` + `regress all` çalıştır;
bilinçli iyileşmeyi `altin` ile onayla.

## 5.8 Çapraz kontroller
- Set eşleşmesi: LED merkezleri ↔ tuş katmanı oval merkezleri (kart eksenine göre) farkı x ≤ 0.15 mm.
- Ağ tablosu ↔ RAPOR `pin_eslemesi`: çizimden çıkan pin → uç listesi yazılan eşlemeyle aynı olmalı.
- `fpc.py build` sonunda dosya kontrolü: üç SVG XML olarak ayrıştırılır ve PyMuPDF ile açılır, PDF'te
  Kesim + Gümüş katmanları vardır. Hata = teslim yok.
