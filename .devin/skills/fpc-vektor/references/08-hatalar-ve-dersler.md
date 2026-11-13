# 08 — Bilinen hatalar, başarısız yöntemler, dersler

## Yapma
1. **Tam otomatik iskelet grafiği ile hat çıkarma** (skeletonize → graf → sadeleştirme): LED
   damlaları, gölgeler ve lekeler yüzünden yüzlerce sahte kenar üretti. Yalnızca kaba yön bulmak için.
2. **Morfolojik çizgi açmasıyla otomatik segment listesi** (segfind) tek başına: iyi bir *ölçüm
   tablosu*dur ama rota değildir; gölge ve yama kenarları sahte segment verir (w > 36 veya L < 80 ele).
3. **Global eşikle gümüş maskesi**: gölgeleri ve kaplamayı da yakalar. Doku eşiği (tex) şart.
4. **Gölge bantlarını ped barı / ikinci hat saymak** (P2'de ilk okumada bar 0.95 mm sanıldı; doğrusu
   0.55 mm). Kontrol: bant hep üstte mi, dokusuz mu, gerçek şeklin 20–28 px üstünde mi?
5. **Birleşik yamada tek ust/alt kararı**: bitişik yamalar tek bileşen olunca bir hattın bir kısmı
   üstte bir kısmı altta olabilir → karar hat-yama-parça bazında verilir.
6. **Düzenlenebilir sürümde köprülü hattı bütün bırakmak**: alt baskıda kısa devre anlamına gelir.
7. **Grup opaklığı** (SVG `<g opacity>`): CorelDRAW içe aktarmada kaybolabilir → nesne bazında.
8. **Metrikleri iyi göstermek için ROI daraltmak**: yapma; sorunlu bölgeyi rapora yaz.
9. **Yeni yayınlanmış bağımlılık sürümü**: pip geçişli bağımlılığı (ör. tifffile 3 günlük) çekerse
   kur yarıda kes, eski sürümü sabitle.
10. **Açık PDF'in üzerine yazmak**: Windows kilidi → yazıcı `_yeni.pdf` üretir; kullanıcıyı uyar.

## Yap
1. Her bölgede önce **sayısal profil** (`measure.py`, ham `L/T/tex` değerleri 3–6 px adımla), sonra görsel.
2. Görüntüleri küçük, ızgaralı ve tek tek oku; mozaiklerle sayıyı azalt.
3. Kaba rota → refine → bindirme → düzelt döngüsünü **küçük partilerle** yap (bölge bölge).
4. Refine çıktısında açı ve genişlik listesini mutlaka kontrol et (45'in katı değilse veya genişlik
   hat genişliğinden ±%40 farklıysa o segment yanlış).
5. Ağ mantığı: LED iki pedi farklı ağ, her ağ bir pine, ortak hat pine ulaşıyor.
6. Belirsiz → `flag=True` + RAPOR kontrol maddesi + kullanıcıya özet.
7. Pilot parça → kullanıcı onayı → kalan parçalar.
8. Kesim ile baskı arasındaki dönüklüğü/kaymayı ölç ve rapora yaz; çizimde ideal hizala.

## Zaman / bağlam bütçesi
- Tuş tipi parça: ~40–60 araç çağrısı. LED tipi: ~120–180 (rota okuma ağırlıklı).
- LED tipinde birleşik poligon görünümü (`polyvec` konturları tarama üstünde, 0.42 ölçek) topolojiyi
  okumanın en ucuz yoludur; büyük bölgeleri tek tek zoomlamadan önce bunu üret.

## P3/P4'ten dersler
1. **Uzun parçada tek açı yetmez**: bölge bazında `skew.measure` ve hat izleme (x(y)) yap; baş ile kuyruk
   farklı eğimdeyse `parts/<ad>.json` "bukulme" (dx_noktalar) ile satır bazlı düzelt (prep.py `unbend`).
2. **Katman kayması**: dielektrik şeridi gümüşe göre asimetrikse kaydırma taraması yap (IoU maks.);
   çizimi ideal bırak, `SCAN["diel_kayma_mm"]` ile doğrulamada telafi et.
3. **Bulanık (kalkık) film**: doku eşiği (m_top) dikey hatları kaybeder → `m_dark` (koyuluk) ile rota,
   `m_band` ile doğrulama (`rota_maskesi`, `dogrulama_maskesi`). m_dark gölgeyi içerir: yatayları alt
   kenardan düzelt (p3_design `fix_horizontals`).
4. **Yama geçişleri**: sütun bazlı renk profili (`work/p3/_patchcols.py` kalıbı) en güvenilir okuma.
   Köprü seçiminde kesişen hatların üstündeki pikseller örneklenmemeli (gri köprü yatayı "üst" gösterir).
5. **Ağ mantığını geometriden çıkar** (`work/p3/_netlist.py` kalıbı): pinsiz ped / iki pinli ağ / kısa
   devre listesi kontrol maddesine dönüşür.
6. Geçici görseller `_` önekli veya `_t.png` sonekli olmalı (rapor bunları dışlar).

## Faz 1 (dürüst metrikler + ağ/tutarlılık) dersleri
1. **Tam-piksel metrik saklıyordu**: eski Canny + mesafe dönüşümü medyanı dört parçada da tam 2 px (0.042 mm)
   verdi. Alt-piksel normal-profil metriği P3'te medyan 0.064 / %90 0.172 mm gösterdi (eşik dışı).
2. **Sistematik ofset önce maskeden şüphelen**: P2/P4 gümüşü "+0.032 mm her yandan geniş" çıktı; T kanalı
   yarı-yükseklik genişliği 0.514 mm (çizim 0.50) iken `silver_ref` (T<20) 0.424 mm idi → maske eşiği yerel
   orta eşiğe çevrildi, ofset −0.009 mm'ye indi. Ofset uyarısında önce hat profilini ölç.
3. **Görsel olarak "değen" uç çizimde kopuk olabilir**: P1'de 8 LED üst pedi boyun hattından 0.07–0.16 mm
   ayrıktı (kaba rota ped kenarında başlıyordu, refine kısalttı). Uçları pede bindir; her değişiklikten sonra `check`.
4. **Yama içindeki T-bağlantı**: dikey hat yatay hatla yama içinde birleşiyorsa ve dikey "köprü" seçilirse
   bağlantı çizimde kaybolur (P3 R6_alt, Poz7, Poz10: `kopru_ucu_yalitkanda`). Birleşme noktası yamanın dışında
   olmalı ya da o parça alt baskıda kalmalı.
5. Ağ tablosunu RAPOR pin eşlemesiyle karşılaştır; P2/P4'te birebir aynı çıktı (doğrulanmış kural seti).

## Faz 2 (gölge modeli, yoğunluk kenarı, kalibrasyon, arka tarama) dersleri
1. **Doku eşiği kenarı da "doku" sayar**: 9×9 bulanık yüksek-geçiren, malzeme/gölge geçişinde yüksektir; gölge
   bandının ilk kestirimi bu yüzden δ'yı yarı değerde buldu. Gümüş = doku yüksek **ve** yumuşatılmış gradyan küçük.
2. **Gölge maskesi gümüş içine taşmamalı**: dokulu (kenar dışı) pikseller asla gölge değildir; aksi halde tarak
   parmakları referans maskeden düşer (P2 ped kapsaması).
3. **Yoğunluk kenarı kapı olamaz**: plato pencereleri çizim kenarına görelidir; ±6 px üstü sapma ölçülmez,
   kapsama dışı kalır → %90 iyimser. Kapılar maskede; yoğunluk ofset/kayma ve maske yanlılığı için.
4. **Periyot ölçümünde tepe değil merkez**: düz tepeli plato maksimumu gürültülü; yarı-yükseklik ağırlıklı merkez +
   MAD ayıklama (tek kısmi/dummy pozisyon std ile ayıklanamaz). ROI kötüyse artık RMS > 1 px.
5. **Faz işareti**: z = Σp·e^{−iωx} için p ≈ cos(ωx − θ) ise angle(z) = −θ; tepe θ/ω'dadır.
6. **Arka/ön yüz farklı kontrast**: yoğunluk değil yapı (gradyan genliği) eşleştir; ters kontrastta ECC ~0.89
   iken hizalama hatası < 0.5 px olabilir — ECC değerini değil hizalı fark/yerel artığı ölç.
8. **Ölçü hatası da tutarlılıktan çıkar**: P1 `kontur_disi` (R2L_alt yarık üstüne taşıyor) aslında yarık üst
   ucunun yanlış ölçüldüğünü gösterdi (69.9 → 70.7 mm, yarık merkezinde dikey profil). Kontur uyarısında önce konturu ölç.
7. Profil refine P1/P3'te küçük iyileşme verdi (medyan −0.002 mm); kalan büyük sapmalar şablon LED pedleri ve
   kaplama bölgelerinde — merkez çizgisi değil, ped ölçüsü/konumu sorunu (`oneri` eleman listesi).
