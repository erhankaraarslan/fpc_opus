# 04 — LED devresi (P1/P3 tipi) yöntemi

Yapı: **iki gümüş baskı** (1: alt hatlar, 2: dielektrik yamanın üstünden geçen köprüler),
dikdörtgen dielektrik **köprü yamaları**, SMD LED'ler (0402, iletken yapıştırıcı), "+" polarite
işaretleri (gümüş), kuyrukta dielektrik + konnektör + takviye, kuyrukta yapıştırma etiket.
Çalışan örnek: `templates/led_design_ornegi.py` + `templates/led_rotalar_ornegi.py` (P1).

## 4.1 Sıra
1. Ölçek + kontur (references/01). Kuyruk pozisyonları `TX[i] = x0 + i*s` (i=0..N-1); kullanılan /
   dummy pozisyonları T kanalı profilinden (dummy'ler sadece konnektör ucunda kısa kontak).
2. `fpc.py segment <ad>` → m_top / m_under / m_teal.
3. **LED merkezleri** (yeşil çip, T>45, alan 150–2500 px, ≤80×70 px bileşenler):
   ```python
   m=(T>45); connectedComponentsWithStats → (cx, cy)
   ```
   12 LED bekleniyorsa 12 bulunmalı; fazlası (ince uzun turkuaz) eleniyor mu kontrol et.
4. **LED şablonu**: 2–3 LED'de dikey (pedin sol/sağ çeyreğinde) ve yatay profil → ped genişliği,
   ped yüksekliği, ped arası boşluk, site merkezinin çip merkezine ofseti (P1: +4, +8 px).
   Kaplama damlası kenarları bozar → şablon (P1: ped 1.65 × 1.6 mm, boşluk 0.85, gövde 0.5 × 1.0).
5. **"+" işaretleri**: şablon eşleştirme (`matchTemplate`, 60×60 koyu artı), her LED için alt-sol ve
   alt-sağ aramaları; tutarlı ofsetleri sütun bazında kullan (P1: sol sütun (+59,+119) px, diğerleri
   (−47,+113) px). Skor < 0.45 ise ofseti komşu LED'den al.
6. **Hat bilgisi toplama** (görsel okumadan ÖNCE sayısal):
   - `python .../segfind.py <ad> work/<ad>/m_top.npy y0 y1 61` + `seglist.py <ad> 14 36` →
     tüm yatay/dikey/45° hat parçaları (konum, genişlik, uzunluk). Kısa (< 80 px) ve w>36 olanlar
     çoğunlukla gürültü/ped kenarı.
   - Birleşik görünüm: `polyvec.mask_to_polys(m_top|m_under temizlenmiş)` konturlarını tarama üzerine
     çiz (0.42 ölçek, 100 px ızgara) → ağ topolojisini bu görüntüden oku. Bu, en verimli tek görüntü.
7. **Kaba rotalar** (`parts/<ad>_routes.py`): her hat bir `dict(name, pts=[(x,y),...])`. Köşeleri
   yaklaşık ver (±15 px); pahlar ayrı köşe. Kuralar:
   - Seg listesindeki kesin x/y değerlerini kullan (ör. dikey x=1450 → tüm köşelerde 1450).
   - LED boyunları: üst ped üstünden yukarı, alt ped altından aşağı; x = ped merkezi.
   - T-bağlantı: dal hattı ana hattın merkez çizgisinde başlar.
   - Görünmeyen/belirsiz kısım: `flag=True`; refine'ın bozduğu kısım: `raw=True` veya
     `raw_from=k` (k. köşeden sonrası elle).
8. **Refine**: `routes_view.py <rota_mod> <ad> x0 y0 x1 y1 0.42` → her segment, dik profillerde en
   yakın gümüş koşusuna oturtulur; açı 0/45/90/135'e ±5° (kısa segment ±12°) içinde ise kilitlenir.
   Çıktıdaki açı listesinde 45'in katı olmayan değer = hatalı kaba köşe → düzelt. Genişlik listesi
   hat genişliğinden (P1 ~23 px) çok farklıysa (≤12 veya ≥34) segment yanlış hatta oturmuştur.
9. **Konnektör toplama bölgesi (fan)**: genelde leke altında. Kural: kuyruğa giren hatlar
   **düzlemsel sıradadır** (kesişmez): soldan gelenler (alttaki en sola) sol pinlere, yukarıdan
   gelenler x sırasıyla, sağdan gelenler sağ pinlere. 45° çaprazları ölçülen doğrulara uydur
   (`x+y=c` veya `x−y=c`; seglist 45/135 kayıtları). Sayım: hat sayısı = kullanılan pin sayısı olmalı;
   değilse bir hat yanlış okunmuştur. Tamamı `flag=True` + RAPOR pin eşlemesi tablosu.
10. **Yamalar**: `m_teal|m_under` → yatay/dikey 31 px kapama (köprülerin bıraktığı boşlukları kapatır)
    → 11 px açma → `mask_to_polys` (eps 4, snap 15) → dolgu oranı > 0.9 ise zarf dikdörtgen.
    Bitişik yamalar birleşik çokgen olarak kalabilir; sorun değil (köprü seçimi parça bazlıdır).
11. **Köprü seçimi (otomatik)**: her hat ∩ (yamalar −6 px) → sürekli parçalar; her parça boyunca 3 px
    adımla 7×7 pencerede m_top ve m_under sayılır; `m_top > m_under` → köprü (2. baskı). Kararsız
    (ikisi de > 0 ve oran < 3) parçaları elle karar ver: **aynı yamada dikeyler üstten ise yatay alttan**
    (veya tersi). Köprü = hat ∩ (parça + 0.7 mm tampon); alt gümüşten kesilen = parça tamponu ∩ yama.
    Sonuç: köprü uçları yama kenarından 0.4 mm dışarı taşar (alt gümüşle bindirme = elektriksel bağ).
12. Kuyruk dielektriği: T kanalı kenarları (baskı çerçevesinde; kesimle asimetrik olabilir — ölçüleni
    koru). Takviye, dummy kontak başlangıcı, etiket (T kanalının kaybolduğu y aralığı) ölçülür.

## 4.2 Ağ mantığı (kısa devre / kopukluk kontrolü — ZORUNLU)
- Ortak hat (R1) çevreyi dolaşır ve bir pine ulaşmalıdır (P1: sol-alt dönüş → pin 1).
- Her LED'in iki pedi farklı ağlarda olmalı. Bir okumada LED'in iki pedi aynı ağa düşüyorsa okuma
  yanlıştır: hatlar arasında gerçekte boşluk olan bir yer vardır (dikey profil: parlak boşluk +
  ardından gölge bandı = bağlantı yok).
- Seri LED çiftleri olabilir (P1: L2 → L4, L1/L3 katot ortak). Bir ağın birden fazla pine gitmesi
  şüphelidir → tekrar ölç.
- Bağlantı kararı için sütun/satır profili: `L` ve `tex` değerlerini 4–6 px adımla yazdır; silver
  L 185–205 & tex > 4; boşluk L > 215; gölge L 160–185 & tex < 3.

## 4.3 Doğrulama beklentisi (P1)
Gümüş kenar medyan 0.042 / %90 0.136 mm; karşılıksız tarama gümüşü 0.14 (kaplama + leke + gölge).
Gümüş IoU (~0.63) şablon pedler ve damlalar yüzünden düşüktür; kabul ölçütü değildir.
