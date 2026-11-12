# P1 - Kısa LED devresi (12 LED, 11 pin 1.0 mm)

*11.11.2026 22:17 — fpc-vektor skill · etkileşimli sürüm: `P1_rapor.html`*

**Kabul:** GEÇTİ · **Belirsiz rota:** 12 · **Kontrol maddesi:** 17 · **Karar noktası:** 10

## Özet

12 LED'li arka aydınlatma katmanı (0402 LED, iletken yapıştırıcıyla montaj). İki gümüş baskı (alt hatlar + dielektrik üstü köprüler), dielektrik köprü yamaları, 11 pinlik 1.0 mm ZIF kuyruğu. LED konumları P2'nin oval pencereleriyle 0.1 mm içinde örtüşür.

## Analiz süreci

1. **Kırpım ve eğiklik** — Kırpımda eğiklik 0.108° ölçüldü ve 0.1° ile düzeltildi. Hatlar, P2 ile aynı ölçekte (47.17 px/mm) ölçüldü.
2. **İlk segmentasyon ve sorunların tespiti** — Basit renk eşiği LED kaplama damlalarını ve gölgeleri de gümüş saydı. Dielektrik yamaların altında kalan gümüşün koyu turkuaz (R &lt; 82) olduğu bulundu.
3. **Gölge kopyasının çözülmesi** — Film camda düz yatmadığı için her hattın ~0.5 mm üstüne pürüzsüz bir gölge kopyası düşüyor. Gümüş tanecikli (dokulu), gölge pürüzsüz; doku eşiği (tex &gt; 3.2) ile ayrıldı.
4. **Başarısız deneme: otomatik iskelet** — Tam otomatik iskelet-graf yöntemi 736 sahte kenar üretti; yalnızca kaba yön bulmak için kullanılabilir.
5. **Topolojinin okunması** — Yama içinde alt gümüşün kesik bırakıldığı bileşen haritası ve birleşik poligon görünümü, ağların en verimli okunduğu görüntüler oldu.
6. **Köprü kümelerinin çözümlenmesi** — Sağ üst kümede R1L katodu hattı dikeyde üstten geçip 45° ile yatay hatta dönüyor; yatay hat yamaların altından geçiyor. Her kesişmede üst/alt ayrımı renkle yapıldı.
7. **Kritik bağlantı kontrolleri** — LED2'nin katot hattının (V466) alt ucunda parlak bir boşluk ve ardından gölge bandı bulundu: R1'e bağlı değil. Bağlı sanılsaydı LED2 kısa devre olurdu.
8. **Konnektöre toplanma bölgesi** — Konnektörün üstünde yapışkan bir leke var. Yüksek geçiren filtre ve uyarlamalı eşikle hatlar görünür hale getirildi. Pin sırası, hatların düzlemsel sırası ve ölçülen 45° çaprazlarla belirlendi.
9. **Rotalar ve LED şablonu** — 39 rota kaba olarak yazıldı ve gerçek merkez çizgisine oturtuldu. 12 LED yeşil çipten konumlandı; pedler şablondan çizildi.
10. **Doğrulama** — Gümüş kenar sapması medyan 0.042 mm, %90 0.136 mm. Taramadaki gümüşün %14'ünün çizimde karşılığı yok; bunun büyük kısmı kaplama, leke ve gölge.

## Bulgular

- Yapı: alt gümüş + dielektrik yamalar + üst gümüş köprüler; kuyrukta dielektrik, konnektör ucunda arka takviye, kuyrukta yapıştırma etiket.
- Ortak anot hattı R1 kartın çevresini dolaşıyor ve LED'lerin üst pedlerini besliyor.
- LED'ler kısmen seri bağlı. Örnek: LED2'nin katodu LED4'ün anoduna gidiyor. L1, L3, B2 ve B3 katotları ortak bir hatta toplanıyor.
- Konnektörde 11 pozisyonun 8'i kullanılıyor; 2, 4 ve 11. pozisyonlar uçta dummy kontak.
- Kesim ile baskı arasında kuyrukta ~0.26° dönüklük var; kuyruk dielektriği kesime göre asimetrik.
- 12 LED, P2'nin oval pencereleriyle x'te 0.1 mm içinde örtüşüyor; iki parçanın ölçümleri birbirini doğruluyor.

## Karar noktaları

### K1. Mevcut taramayla mı devam edilsin?

- Seçenek: Yeni tarama (düz, arkadan aydınlatmalı)
- Seçenek: Mevcut taramayla devam, belirsizleri işaretle
- Seçenek: Devam + multimetre ile doğrulama
- Seçenek: Önce P3/P4
- **Seçilen:** Mevcut taramayla devam; belirsiz noktalar işaretlenecek
- Risk: Leke ve kaplama altındaki bağlantılar yorum.

### K2. Gölge kopyalarının ayıklanması

- Seçenek: Parlaklık eşiği
- Seçenek: Doku (yüksek frekans) eşiği
- **Seçilen:** Doku eşiği tex &gt; 3.2 ve 185 &lt; L &lt; 208
- Gerekçe: Gölge ve gümüş benzer parlaklıkta; gölge pürüzsüz (tex 2–3), gümüş tanecikli (tex 4–8).
- Kanıt: [seg_led.png](P1_rapor_gorseller/seg_led.jpg), [v_seg.png](P1_rapor_gorseller/v_seg.jpg)

### K3. İki gümüş baskının modellenmesi

- Seçenek: Köprü geçen hattın tamamı 2. baskıda
- Seçenek: Sadece köprü parçası 2. baskıda (yama + 0.4 mm bindirme)
- **Seçilen:** Sadece köprü parçası; alt baskıda yama içinden kesilir
- Gerekçe: Serigrafi pratiğine uygun, düzenlemesi kolay; elektriksel bağlantı bindirme ile sağlanıyor.
- Kanıt: [v_x1.png](P1_rapor_gorseller/v_x1.jpg), [zx3.png](P1_rapor_gorseller/zx3.jpg)

### K4. Köprü üst/alt seçimi

- Seçenek: Her kesişmeyi elle okumak
- Seçenek: Maske örneklemesiyle otomatik (parça bazında)
- **Seçilen:** Otomatik örnekleme; B2/B3 altındaki yatay hat elle 'alt' ayarlandı
- Gerekçe: 29 kesişmenin 28'inde örnekleme kesin sonuç verdi (bir tarafta 0 piksel). Kararsız tek kesişmede aynı yamadaki dikeyler üstten geçtiği için yatay alttan geçiyor kabul edildi.
- Kanıt: [zo_c1.png](P1_rapor_gorseller/zo_c1.jpg), [zo_c2.png](P1_rapor_gorseller/zo_c2.jpg), [zr3.png](P1_rapor_gorseller/zr3.jpg)

### K5. LED2 katot hattının (V466) alt ucu

- Seçenek: R1 alt hattına bağlı
- Seçenek: Bağlı değil, LED4 alt pedine gidiyor
- **Seçilen:** Bağlı değil: V466 → LED4 alt pedi (seri)
- Gerekçe: Sütun profilinde 3730–3742 px arası parlak boşluk ve ardından gölge bandı var. Bağlı olsaydı LED2 kısa devre olurdu.
- Kanıt: [zj466.png](P1_rapor_gorseller/zj466.jpg), [z_v462.png](P1_rapor_gorseller/z_v462.jpg), [v_bot.png](P1_rapor_gorseller/v_bot.jpg)

### K6. R1'in konnektöre ulaşması

- Seçenek: R1 alttan döner, x≈11 mm dikeyle pin 1'e gider
- Seçenek: Başka bir yol
- **Seçilen:** Alttan dönüş, pin 1 (Kontrol katmanında)
- Gerekçe: Ortak hat bir pine ulaşmak zorunda; görülebilen tek yol bu. Dikey hat kaplama damlası altında, dokusu zayıf.
- Risk: Yanlışsa LED'lerin besleme pini farklıdır.
- Kanıt: [z_bl.png](P1_rapor_gorseller/z_bl.jpg), [zs_bl.png](P1_rapor_gorseller/zs_bl.jpg), [zled4.png](P1_rapor_gorseller/zled4.jpg)

### K7. Konnektör pin eşlemesi

- Seçenek: Lekenin altını tahmin etmeden çizmemek
- Seçenek: Düzlemsel sıra + ölçülen çaprazlarla eşlemek
- **Seçilen:** Düzlemsel sıra: soldan gelen 3 hat → pin 1/3/5, yukarıdan gelenler x sırasıyla → pin 6–9, sağdan gelen → pin 10
- Gerekçe: Tek baskı katmanında hatlar kesişemez. Hat sayısı (8) kullanılan pin sayısına eşit. Ölçülen 135° çaprazlar (x+y = 4485 / 4556 / 4633) pin 7/8/9 ile uyumlu.
- Risk: Tüm toplanma bölgesi Kontrol katmanında.
- Kanıt: [zfan_hp2.png](P1_rapor_gorseller/zfan_hp2.jpg), [zfan_m.png](P1_rapor_gorseller/zfan_m.jpg), [zfan_o.png](P1_rapor_gorseller/zfan_o.jpg)

### K8. LED pedleri

- Seçenek: Her pedi taramadan ölç
- Seçenek: Ortak şablon
- **Seçilen:** Şablon: ped 1.65 × 1.6 mm, boşluk 0.85 mm, gövde 0402
- Gerekçe: Kaplama damlaları ped kenarlarını örtüyor; 3 LED'den ölçülen değerler tutarlı.
- Kanıt: [z_led1.png](P1_rapor_gorseller/z_led1.jpg), [v_led1e.png](P1_rapor_gorseller/v_led1e.jpg), [v_led2.png](P1_rapor_gorseller/v_led2.jpg)

### K9. Kesim ve kuyruk dielektriği

- Seçenek: Kesim ölçüldüğü gibi (kuyruk 0.4 mm kayık)
- Seçenek: Kesim konnektör eksenine simetrik; dielektrik ölçüldüğü gibi
- **Seçilen:** Kesim simetrik, dielektrik ölçüldüğü gibi
- Gerekçe: Konnektör konumu baskıyla belirlenir; kesim toleransı tasarım niyeti değil.
- Kanıt: [t_tail.png](P1_rapor_gorseller/t_tail.jpg), [t_end.png](P1_rapor_gorseller/t_end.jpg)

### K10. Otomatik iskelet yöntemi

- Seçenek: Otomatik iskelet-graf vektörleştirme
- Seçenek: Kaba rota + gerçek merkeze oturtma
- **Seçilen:** Kaba rota + oturtma
- Gerekçe: İskelet yöntemi kaplama ve leke yüzünden 736 sahte kenar üretti.
- Kanıt: [v_skel.png](P1_rapor_gorseller/v_skel.jpg)

## Ölçüler

| Ölçü | Değer | Not |
|---|---|---|
| Baş (genişlik × yükseklik) | 36.5 × 87.1 mm | köşe R1.0 |
| Toplam boy | 170.9 mm |  |
| Kuyruk genişliği | 12.0 mm | yarık 2.1 mm, üst ucu y=69.9 |
| Konnektör | 11 poz × 1.0 mm | kontak 0.6 mm, 2/4/11 dummy |
| Hat genişliği | 0.5 mm |  |
| LED pedi | 1.65 × 1.6 mm | boşluk 0.85 mm, LED gövdesi 0.5 × 1.0 mm |
| Polarite işareti | + 0.8 mm, çizgi 0.15 mm | gümüş baskı |
| Köprü bindirmesi | 0.4 mm | yama kenarından dışarı |
| Kart sınır kutusu | 36.50 × 170.90 mm | Kesim konturu |
| Kart alanı | 4112.6 mm² |  |
| Gümüş alanı (alt baskı) | 819.0 mm² |  |
| Dielektrik alanı | 1202.5 mm² |  |
| Köprü alanı (2. gümüş baskı) | 43.47 mm² | 20 köprü |

| Eleman | Adet |
|---|---|
| Hat (polyline) | 39 |
| Gümüş dikdörtgen (ped/blok/parmak) | 24 |
| Oval pencere | 0 |
| LED | 12 |
| Dielektrik yama | 10 |
| Köprü | 20 |
| Kontrol (belirsiz) rota | 12 |

### Varsayımlar

- Ölçek 47.17 px/mm (P2 ile aynı tarama).
- Kesim deseni konnektör eksenine göre simetrik çizildi (taramada kuyruk ~0.26° dönük).
- Köprülerde üst/alt seçimi her kesişimde üst-gümüş / alt-gümüş maske örneklemesiyle yapıldı; B2/B3 alt yamasındaki yatay hat elle 'alt' ayarlandı.
- LED ped/gövde ölçüleri şablon: kaplama damlaları ped kenarlarını örtüyor.
- Konnektöre giden hatların pin sırası (leke altında) düzlemsel sıra + görülen 45° çaprazlarla belirlendi.

## Doğrulama

| Metrik | Değer | Eşik | Sonuç |
|---|---|---|---|
| Gümüş kenar sapması medyan | 0.042 mm | ≤ 0.06 mm | ✔ |
| Gümüş kenar sapması %90 | 0.136 mm | ≤ 0.15 mm | ✔ |
| Gümüş IoU | 0.628 | bilgi | — |
| Taramada karşılıksız gümüş | 0.140 | ≤ 0.15 | ✔ |

## Pin eşlemesi

| Pin | Bağlantı |
|---|---|
| 1 | R1 ortak (anot) |
| 2 | dummy |
| 3 | L3/L4 üst |
| 4 | dummy |
| 5 | H3317 hattı |
| 6 | V916 / H2818 |
| 7 | L2 alt düğümü (L2→L4) |
| 8 | R1 LED katodu (+C1) |
| 9 | L1/L3 katodu (+B2/B3) |
| 10 | R2/R3 katodu |
| 11 | dummy |

## Fiziksel kontrol

- [ ] Kuyruk pin eşlemesi (aşağıdaki tablo) - leke altında yorumlandı
- [ ] R1 sol-alt dönüşü ve x≈11 mm dikeyiyle pin 1 bağlantısı
- [ ] B1/B2/B3 LED ped bağlantıları (orta-alt leke bölgesi)
- [ ] R3 üst pedi → T3, R4 üst pedi → T3 alt ucu bağlantıları
- [ ] y=2818 (V578→V916) ve y=3317 hatlarının uç bağlantıları
- [ ] Kontrol katmanı: 'R1_alt' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'H2818' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'H3317' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'T3_R4L' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'B1_ust' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'B1_alt' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'B2_ust' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'B2_alt' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'B3_ust' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'B3_alt' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'R3L_ust' rotası taramadan kesin okunamadı
- [ ] Kontrol katmanı: 'R3L_alt' rotası taramadan kesin okunamadı

## Daha iyi sonuç için

- **En büyük kazanç: arkadan aydınlatmalı görüntü:** P1'i ışık masası veya cam üstüne konmuş bir tablet ekranı üzerinde, düz bastırarak fotoğraflayın ya da tarayın (2400 dpi). Gümüş opak olduğu için siyah görünür; gölge, kaplama damlası ve leke sorunları neredeyse tamamen ortadan kalkar. Bu görüntüyle Kontrol katmanındaki 12 rota kesinleşir.
- **Multimetre ile 5 dakikalık kontrol:** Süreklilik modunda şunlara bakın: (1) pin 1 ↔ R1 çevre hattı, (2) her pin ↔ hangi LED pedi, (3) LED2 alt pedi ↔ LED4 alt pedi. Sonuçları 'Pin 7 ↔ LED2 alt: VAR' gibi yazmanız yeterli; çizim bir dakikada güncellenir.
- **Konnektör toplama bölgesinin yakın fotoğrafı:** Pinlerin 5–10 mm üstündeki bölgeyi yandan ışıkla veya arkadan aydınlatarak telefonla çekin. Lekenin altındaki 8 hattın sırası bununla kesinleşir.
- **LED bilgisi:** LED kodu veya rengi ve polaritesi ('+' işaretinin anot olduğu) biliniyorsa bildirin. LED katmanına model bilgisi eklenir ve ped boyutu datasheet'e göre düzeltilir.
- **Üretim bilgisi:** İki gümüş baskı mı (köprü modeli), yoksa çift taraflı mı üretiliyor? Üretici farklı bir köprü bindirmesi isterse (varsayılan 0.4 mm) tasarım dosyasında tek parametredir.

## Analiz görselleri

**[Kaynak] Taramanın genel görünümü** — `_tarama/genel.png`  
4 parça: 1 = P1 (bu parça), 2 = P2, 3 = P3, 4 = P4.

![Taramanın genel görünümü](P1_rapor_gorseller/_tarama_genel_k.jpg)

**[Kaynak] P1 önizleme** — `_tarama/parca_1.png`  
12 LED, turkuaz köprü yamaları, kuyrukta beyaz etiket.

![P1 önizleme](P1_rapor_gorseller/_tarama_parca_1_k.jpg)

**[Kaynak] Kaynak görüntü** — `_tarama/parca_2.png`  
Taramadan kırpılan / incelenen ham görüntü.

![Kaynak görüntü](P1_rapor_gorseller/_tarama_parca_2_k.jpg)

**[Kaynak] Kaynak görüntü** — `_tarama/parca_3.png`  
Taramadan kırpılan / incelenen ham görüntü.

![Kaynak görüntü](P1_rapor_gorseller/_tarama_parca_3_k.jpg)

**[Kaynak] Kaynak görüntü** — `_tarama/parca_4.png`  
Taramadan kırpılan / incelenen ham görüntü.

![Kaynak görüntü](P1_rapor_gorseller/_tarama_parca_4_k.jpg)

**[Ön işleme] Eğikliği düzeltilmiş görüntü** — `p1_deskew.png`  
0.1° düzeltilmiş tam çözünürlüklü kırpım; tüm px koordinatları bu görüntüye göre. *Ölçüm: Hough sapması 0.108°*

![Eğikliği düzeltilmiş görüntü](P1_rapor_gorseller/p1_deskew_k.jpg)

**[Ön işleme] Kontrast güçlendirilmiş** — `enh.png`  
Kaplama damlalarının altını görmek için CLAHE uygulandı.

![Kontrast güçlendirilmiş](P1_rapor_gorseller/enh_k.jpg)

**[Ön işleme] Yüksek geçiren filtre (konnektör toplama bölgesi)** — `fan_hp.png`  
Leke, (L − bulanık L) × 4 ile bastırıldı; altındaki çapraz hatlar görünür hale geldi.

![Yüksek geçiren filtre (konnektör toplama bölgesi)](P1_rapor_gorseller/fan_hp_k.jpg)

**[Maskeler] İlk segmentasyon (gürültülü)** — `v_seg.png`  
Basit eşik: LED kaplama damlaları ve gölgeler gümüş sayıldı.

![İlk segmentasyon (gürültülü)](P1_rapor_gorseller/v_seg_k.jpg)

**[Maskeler] Alt gümüş ayrımı** — `v_seg2.png`  
Dielektrik altındaki gümüş koyu turkuaz (R &lt; 82) olarak ayrı renkte; üst gümüş gri.

![Alt gümüş ayrımı](P1_rapor_gorseller/v_seg2_k.jpg)

**[Maskeler] Son maskeler: üst gümüş / alt gümüş / dielektrik** — `seg_led.png`  
Doku eşiğiyle gölgeler elendi. Gri = dokulu gümüş, lacivert = dielektrik altı gümüş, açık turkuaz = dielektrik.

![Son maskeler: üst gümüş / alt gümüş / dielektrik](P1_rapor_gorseller/seg_led_k.jpg)

**[Maskeler] Bağlantı bileşenleri (tam ölçek)** — `comp.png`  
Yama içinde yalnızca üst gümüş tutuldu; her renk ayrı iletken bileşen.

![Bağlantı bileşenleri (tam ölçek)](P1_rapor_gorseller/comp_k.jpg)

**[Maskeler] Toplama bölgesi uyarlamalı maske** — `fanmask.png`  
Leke altında yerel eşik. Gölge kopyalarını da yakalar: yatay hatların ~20 px üstündeki ikizleri gölgedir.

![Toplama bölgesi uyarlamalı maske](P1_rapor_gorseller/fanmask_k.jpg)

**[Maskeler] Birleşik gümüş poligonları** — `polyvec_vis.png`  
Temizlenmiş maskeden 0/45/90°'ye oturtulmuş poligon konturları; topoloji okumanın en verimli yolu.

![Birleşik gümüş poligonları](P1_rapor_gorseller/polyvec_vis_k.jpg)

**[Maskeler] Maske / segmentasyon görseli** — `fanmask_full.png`  
Renk ve doku eşikleriyle elde edilen malzeme maskesi.

![Maske / segmentasyon görseli](P1_rapor_gorseller/fanmask_full_k.jpg)

**[Maskeler] Maske / segmentasyon görseli** — `seg.png`  
Renk ve doku eşikleriyle elde edilen malzeme maskesi.

![Maske / segmentasyon görseli](P1_rapor_gorseller/seg_k.jpg)

**[Maskeler] Maske / segmentasyon görseli** — `seg3.png`  
Renk ve doku eşikleriyle elde edilen malzeme maskesi.

![Maske / segmentasyon görseli](P1_rapor_gorseller/seg3_k.jpg)

**[Maskeler] Maske / segmentasyon görseli** — `seg_hizli.png`  
Renk ve doku eşikleriyle elde edilen malzeme maskesi.

![Maske / segmentasyon görseli](P1_rapor_gorseller/seg_hizli_k.jpg)

**[Ölçüm] LED1 yakın çekim** — `z_led1.png`  
0402 LED, iki ped arasındaki boşlukta; yeşil 'T' emitör.

![LED1 yakın çekim](P1_rapor_gorseller/z_led1_k.jpg)

**[Ölçüm] LED1 ped yapısı (kontrast)** — `v_led1e.png`  
Üst ped R1'e bağlı; alt ped boyunla y 1981 hattına iniyor. *Ölçüm: ped 1.65 mm genişlik, boşluk 0.85 mm*

![LED1 ped yapısı (kontrast)](P1_rapor_gorseller/v_led1e_k.jpg)

**[Ölçüm] LED1 (orijinal)** — `v_led1.png`  
Kaplama damlası alt pedin kenarlarını genişletmiş gibi gösteriyor.

![LED1 (orijinal)](P1_rapor_gorseller/v_led1_k.jpg)

**[Ölçüm] LED C1 (orta üst)** — `v_led2.png`  
Ped şablonunun doğrulandığı ikinci LED.

![LED C1 (orta üst)](P1_rapor_gorseller/v_led2_k.jpg)

**[Ölçüm] Kart konturu** — `v_outline.png`  
Baş, yarıklar ve kuyruk. *Ölçüm: 36.5 × 87.1 mm, kuyruk 12.0 mm, yarık 2.1 mm*

![Kart konturu](P1_rapor_gorseller/v_outline_k.jpg)

**[Ölçüm] Kuyruk başlangıcı** — `t_tail.png`  
8 hat 1.0 mm adımla; 2. ve 4. pozisyonlar boş. Dielektrik baskı kesime göre asimetrik.

![Kuyruk başlangıcı](P1_rapor_gorseller/t_tail_k.jpg)

**[Ölçüm] Kuyruk ve etiket** — `t_tail2.png`  
Beyaz yapıştırma etiket (y 4249–5330 px) dielektriği örtüyor; 'Etiket' katmanında yalnızca konturu var.

![Kuyruk ve etiket](P1_rapor_gorseller/t_tail2_k.jpg)

**[Ölçüm] Konnektör ucu** — `t_end.png`  
11 kontak; 2, 4 ve 11 dummy (y 7785 px'ten başlıyor), takviye y 7925 px'ten uca kadar.

![Konnektör ucu](P1_rapor_gorseller/t_end_k.jpg)

**[Ölçüm] Otomatik hat parçası tespiti** — `segs_vis.png`  
Yatay, dikey ve 45° açılı hat parçaları; ölçüm tablosu olarak kullanıldı, tek başına rota değil.

![Otomatik hat parçası tespiti](P1_rapor_gorseller/segs_vis_k.jpg)

**[Ölçüm] Hat parçaları (üst gümüş)** — `segs_top_vis.png`  
Dokulu maske üzerinde; rotalardaki x/y değerleri bu listeden alındı.

![Hat parçaları (üst gümüş)](P1_rapor_gorseller/segs_top_vis_k.jpg)

**[Topoloji] Sol yarı (maske)** — `hl_s.png`  
Sol sütun LED'leri, R1 çevre hattı ve iç döngü.

![Sol yarı (maske)](P1_rapor_gorseller/hl_s_k.jpg)

**[Topoloji] Sağ yarı (maske)** — `hr_s.png`  
Sağ sütun LED'leri ve köprü kümeleri.

![Sağ yarı (maske)](P1_rapor_gorseller/hr_s_k.jpg)

**[Topoloji] Sol yarı (orijinal)** — `hl.png`  
0.5 ölçek, 100 px ızgara.

![Sol yarı (orijinal)](P1_rapor_gorseller/hl_k.jpg)

**[Topoloji] Sağ yarı (orijinal)** — `hr.png`  
0.5 ölçek, 100 px ızgara.

![Sağ yarı (orijinal)](P1_rapor_gorseller/hr_k.jpg)

**[Topoloji] Bileşen haritası** — `v_comp.png`  
Yamalar açık turkuaz; altından geçen hatlar yamada kesik görünüyor. Ağlar bu haritadan okundu.

![Bileşen haritası](P1_rapor_gorseller/v_comp_k.jpg)

**[Topoloji] Birleşik poligon görünümü** — `v_pv.png`  
Kırmızı konturlar: tüm gümüş. Orta-alt bölgede leke nedeniyle düzensizlik var.

![Birleşik poligon görünümü](P1_rapor_gorseller/v_pv_k.jpg)

**[Topoloji] Orta-alt leke bölgesi** — `v_ctr.png`  
B1/B2/B3 LED'lerinin bağlantıları leke altında; maske güvenilmez. Bu rotalar Kontrol katmanında.

![Orta-alt leke bölgesi](P1_rapor_gorseller/v_ctr_k.jpg)

**[Topoloji] Rota bindirmesi** — `routes_view.png`  
Her renk bir rota. Noktalar, gerçek merkez çizgisine oturtulmuş köşeler.

![Rota bindirmesi](P1_rapor_gorseller/routes_view_k.jpg)

**[Karar kanıtı] Köprü yaması örneği** — `v_x1.png`  
Dikey hatlar açık gri (dielektrik üstünde = köprü); yatay hatlar koyu turkuaz (dielektrik altında).

![Köprü yaması örneği](P1_rapor_gorseller/v_x1_k.jpg)

**[Karar kanıtı] Sağ üst köprü kümesi** — `z_x2b.png`  
x 1449 ve 1614'teki dikeyler üstten, y 2030 ve 2173'teki yataylar alttan geçiyor.

![Sağ üst köprü kümesi](P1_rapor_gorseller/z_x2b_k.jpg)

**[Karar kanıtı] R1 köprüsü (y 2158)** — `zx3.png`  
R1 sağ kenardan sola dönüp yamanın üstünden geçiyor; x 1700'deki T3 hattı altından geçiyor.

![R1 köprüsü (y 2158)](P1_rapor_gorseller/zx3_k.jpg)

**[Karar kanıtı] R1L katodu: dikeyden 45° çapraza dönüş** — `zx4.png`  
V2 dikeyi y ≈ 2110'da 45° ile sola dönüp y 2173 hattına bağlanıyor. Dikeyin alt kısmı (LED R2 anodu) R1'den besleniyor; bu ayrım bir kısa devre paradoksunu çözdü.

![R1L katodu: dikeyden 45° çapraza dönüş](P1_rapor_gorseller/zx4_k.jpg)

**[Karar kanıtı] Sağ orta yama kümesi (y 2700)** — `zr3.png`  
y 2714 hattı alttan; x 1614, 1700 dikeyleri ve 45° çapraz üstten geçiyor.

![Sağ orta yama kümesi (y 2700)](P1_rapor_gorseller/zr3_k.jpg)

**[Karar kanıtı] Sol alt yama (y 3050–3185)** — `zo_c1.png`  
Tek yama: x 462 dikeyi altından (koyu turkuaz), y 3115 yatayı üstünden geçiyor. Gri bant yamayı ikiye bölmüş gibi görünüyor ama tek yama.

![Sol alt yama (y 3050–3185)](P1_rapor_gorseller/zo_c1_k.jpg)

**[Karar kanıtı] Sol alt yama (y 3290–3435)** — `zo_c2.png`  
y 3350 yatayı ve x 462 dikeyi altından, y 3376 yatayı üstünden geçiyor.

![Sol alt yama (y 3290–3435)](P1_rapor_gorseller/zo_c2_k.jpg)

**[Karar kanıtı] V466 üst bağlantısı** — `zj466.png`  
LED2 katot hattı y 2714'ten aşağı dikey olarak devam ediyor (L ≈ 190–200: gümüş).

![V466 üst bağlantısı](P1_rapor_gorseller/zj466_k.jpg)

**[Karar kanıtı] V466 dikeyi boyunca** — `z_v462.png`  
Dikey 2714'ten 3728 px'e kadar sürekli; alt ucunda boşluk var.

![V466 dikeyi boyunca](P1_rapor_gorseller/z_v462_k.jpg)

**[Karar kanıtı] Sol alt ve sağ alt (poligon)** — `v_bot.png`  
Poligon görünümünde R1 alt hattı, V466 ve L4 pedi birleşik görünüyor; bunun nedeni gölge. Sayısal profil, V466 ile R1 arasında boşluk olduğunu gösterdi.

![Sol alt ve sağ alt (poligon)](P1_rapor_gorseller/v_bot_k.jpg)

**[Karar kanıtı] R1 sol alt dönüşü** — `z_bl.png`  
R1 x 220'den aşağı iner, y 3776'da sağa döner; ardından pahla x 516 dikeyine bağlanır.

![R1 sol alt dönüşü](P1_rapor_gorseller/z_bl_k.jpg)

**[Karar kanıtı] Sol alt bölge (maske)** — `zs_bl.png`  
LED3/LED4 iç döngüsü ve R1 alt U'su.

![Sol alt bölge (maske)](P1_rapor_gorseller/zs_bl_k.jpg)

**[Karar kanıtı] LED4 çevresi** — `zled4.png`  
Kaplama damlası ped kenarlarını örtüyor.

![LED4 çevresi](P1_rapor_gorseller/zled4_k.jpg)

**[Karar kanıtı] Konnektör toplama bölgesi (orijinal)** — `zfan_o.png`  
Yarı saydam leke kontrastı düşürüyor.

![Konnektör toplama bölgesi (orijinal)](P1_rapor_gorseller/zfan_o_k.jpg)

**[Karar kanıtı] Toplama bölgesi (yüksek geçiren)** — `zfan_hp2.png`  
Soldan 3 çapraz sağ-aşağı, sağdan 3 çapraz sol-aşağı iniyor; 8 hat 8 pine.

![Toplama bölgesi (yüksek geçiren)](P1_rapor_gorseller/zfan_hp2_k.jpg)

**[Karar kanıtı] Toplama bölgesi (uyarlamalı maske)** — `zfan_m.png`  
45° parçaların konumları; pin eşlemesindeki doğru denklemleri buradan.

![Toplama bölgesi (uyarlamalı maske)](P1_rapor_gorseller/zfan_m_k.jpg)

**[Karar kanıtı] Başarısız: otomatik iskelet** — `v_skel.png`  
İskelet grafı 736 sahte kenar üretti; yöntem reddedildi.

![Başarısız: otomatik iskelet](P1_rapor_gorseller/v_skel_k.jpg)

**[Doğrulama] Baş bölgesi bindirme** — `ov_head.png`  
Turuncu kümeler: yatay hatların üstünde ince şerit = gölge; LED çevresinde = kaplama; orta-alt = leke.

![Baş bölgesi bindirme](P1_rapor_gorseller/ov_head_k.jpg)

**[Doğrulama] Rapor kontrol kırpımı: bas bolgesi** — `kontrol_bas_bolgesi.png`  
Doğrulama bindirmesinden kırpım. Bindirme renkleri: kırmızı gümüş (alt baskı), mavi köprü (2. baskı), yeşil dielektrik, mor kesim/oval, turuncu taramada olup çizimde karşılığı olmayan gümüş.

![Rapor kontrol kırpımı: bas bolgesi](P1_rapor_gorseller/kontrol_bas_bolgesi_k.jpg)

**[Doğrulama] Rapor kontrol kırpımı: konnektor toplama** — `kontrol_konnektor_toplama.png`  
Doğrulama bindirmesinden kırpım. Bindirme renkleri: kırmızı gümüş (alt baskı), mavi köprü (2. baskı), yeşil dielektrik, mor kesim/oval, turuncu taramada olup çizimde karşılığı olmayan gümüş.

![Rapor kontrol kırpımı: konnektor toplama](P1_rapor_gorseller/kontrol_konnektor_toplama_k.jpg)

**[Doğrulama] Rapor kontrol kırpımı: konnektor ucu** — `kontrol_konnektor_ucu.png`  
Doğrulama bindirmesinden kırpım. Bindirme renkleri: kırmızı gümüş (alt baskı), mavi köprü (2. baskı), yeşil dielektrik, mor kesim/oval, turuncu taramada olup çizimde karşılığı olmayan gümüş.

![Rapor kontrol kırpımı: konnektor ucu](P1_rapor_gorseller/kontrol_konnektor_ucu_k.jpg)

**[Doğrulama] Rapor kontrol kırpımı: kopru kumesi sag ust** — `kontrol_kopru_kumesi_sag_ust.png`  
Doğrulama bindirmesinden kırpım. Bindirme renkleri: kırmızı gümüş (alt baskı), mavi köprü (2. baskı), yeşil dielektrik, mor kesim/oval, turuncu taramada olup çizimde karşılığı olmayan gümüş.

![Rapor kontrol kırpımı: kopru kumesi sag ust](P1_rapor_gorseller/kontrol_kopru_kumesi_sag_ust_k.jpg)

**[Doğrulama] Taramaya bindirme** — `overlay.png`  
Çizim geometrisi taramanın üstüne çizildi. Bindirme renkleri: kırmızı gümüş (alt baskı), mavi köprü (2. baskı), yeşil dielektrik, mor kesim/oval, turuncu taramada olup çizimde karşılığı olmayan gümüş.

![Taramaya bindirme](P1_rapor_gorseller/overlay_k.jpg)

**[Çıktı kontrolü] Düzenlenebilir SVG önizlemesi** — `r_edit2.png`  
Mor kesikli çizgiler = Kontrol katmanı (yorumlanan rotalar).

![Düzenlenebilir SVG önizlemesi](P1_rapor_gorseller/r_edit2_k.jpg)

**[Çıktı kontrolü] Çıktı render kontrolü** — `r_edit.png`  
Üretilen SVG/PDF dosyasının rasterleştirilmiş önizlemesi.

![Çıktı render kontrolü](P1_rapor_gorseller/r_edit_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z1.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z1_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z10.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z10_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z11.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z11_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z12.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z12_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z13.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z13_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z14.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z14_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z15.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z15_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z16.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z16_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z2.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z2_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z3.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z3_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z4.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z4_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z5.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z5_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z6.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z6_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z7.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z7_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z8.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z8_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `Z9.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/Z9_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `o1.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/o1_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `o2.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/o2_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `o3.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/o3_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `o4.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/o4_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `q1.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/q1_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `q2.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/q2_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `q3.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/q3_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `q4.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/q4_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s11.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s11_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s12.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s12_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s13.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s13_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s21.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s21_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s22.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s22_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s23.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s23_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s31.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s31_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s32.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s32_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `s33.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/s33_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `skel_vis.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/skel_vis_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t11.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t11_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t12.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t12_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t13.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t13_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t21.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t21_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t22.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t22_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t23.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t23_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t31.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t31_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t32.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t32_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `t33.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/t33_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `v_all.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/v_all_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `v_head.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/v_head_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `z_t452.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/z_t452_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `z_x2.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/z_x2_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `zfan.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/zfan_k.jpg)

**[Çalışma görüntüleri] Izgaralı yakın çekim** — `zfan_hp.png`  
Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli).

![Izgaralı yakın çekim](P1_rapor_gorseller/zfan_hp_k.jpg)

## Çıktılar

- `output/P1_duzenlenebilir.svg` — CorelDRAW'da düzenleme (hatlar kalınlıklı çizgi, pedler dikdörtgen)
- `output/P1_uretim.svg` — Üretim: her katman tek kapalı dolgu
- `output/P1_uretim.pdf` — Üretim: katmanlı vektör PDF
- `output/P1_kontrol_taramali.svg` — Kontrol: çizim + altta hizalı tarama