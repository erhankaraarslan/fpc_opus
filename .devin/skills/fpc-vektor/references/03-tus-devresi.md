# 03 — Tuş devresi (P2/P4 tipi) yöntemi

Yapı: tek gümüş baskı; hatların üzerinde ~2.0 mm turkuaz dielektrik şerit; tarak (interdigitated)
tuş pedleri dielektriksiz pencerede, çevresinde ince (0.2 mm) dielektrik çerçeve; kuyrukta tam
genişlik dielektrik; konnektör ucunda açık kontaklar + arka takviye; oval ışık pencereleri (kesim).
Çalışan örnek: `templates/tus_design_ornegi.py` (P2). Yeni parça için kopyala, sayıları ölç ve değiştir.

## 3.1 Sıra
1. Ölçek + kontur (references/01).
2. Kuyruk: hat merkezleri (adım), hat genişliği (T kanalı gümüş aralığı, P2: 0.60 mm), boş/dummy
   pozisyonlar, dielektrik bitişi (T kanalı dikey profil), takviye başlangıcı (parlak çizgi + doku
   değişimi), dummy kontak başlangıcı, kuyruk ucu.
3. Kuyruk bağlantı blokları: baştan gelen her hat bir bloğa (komşu 2–3 pozisyonu birleştiren dikdörtgen)
   girer, blok altından ayrı hatlar iner. Blok üst y'si ve "çentik" (hatların ayrıldığı) y'si ölçülür.
4. Hat merkez çizgileri: `segment.py` sonrası `sil_teal.npy` üzerinde
   `traces.py work/<ad>/sil_teal.npy y0 y1` → köşe listesi + açılar. Uzun doğruları bant içinde
   SVD ile yeniden oturt (her doğru için merkez, açı); köşeleri komşu doğruların kesişiminden hesapla.
   Açı ≤ 0.3° ise tam yatay/dikey kabul et. Pahlar (45°) ayrı segment olarak verilir.
   Yatay hatların merkezi için T kanalı profilindeki `-`/`+` kenarlarını kullan (gölge yalnızca üstte).
5. Hat genişliği: T kanalında gümüş aralığı (P2 baş: 0.50 mm); şerit genişliği: turkuaz dış kenarları
   (P2: 2.0 mm → `DIEL_W`). Şerit = hat merkezinin ±1.0 mm mitre ofseti.
6. Tarak pedleri (her ped için):
   - Yatay profil (pedin ortası, 80 px yükseklik): parmak kenarları → parmak genişliği, boşluk, adım.
     P2: parmak 0.58 → 0.6, boşluk 0.53 → 0.5, 5 parmak = 5.0 mm.
   - Dikey profil (parmak sütunu ve boşluk sütunu ayrı): bar kalınlıkları, parmak uç boşlukları,
     hangi parmağın hangi bara bağlı olduğu (üst barla arasında parlak boşluk yoksa üst bara bağlı).
   - Gölge bantlarını bar sanma (references/02 §2.3). Doğru sonuç: bar ≈ parmak ≈ 0.55–0.6 mm,
     uç boşluğu ≈ yan boşluk ≈ 0.5 mm, ped 5.0 × 5.0 mm.
   - Yön: `top3=True` → üst tarakta dış 3 parmak; `False` → üst tarakta iç 2 parmak.
   - Ped grubunun eksenini bul (P2: tuş ekseni x = 19.2, kart ekseni 18.35'ten +0.85).
7. Ped çerçevesi: T kanalında ped çevresindeki ince tepe (genişlik ~10 px) → çerçeve merkez ofseti
   (P2: ped kenarından 0.75 mm, çizgi 0.2 mm). Dielektrik = şeritler ∪ çerçeveler ∪ kuyruk alanı −
   ped pencereleri (çerçeve iç kutusu), kontura kırpılmış.
8. Ovaller: `parts/<ad>.json` `oval_kutulari` (gridview ile kaba kutular, ±15 px) → `fpc.py ovals <ad>`
   (stadium robust fit; genişlik güvenilir, boy uçlardaki gölge yüzünden ±10 px oynar). Sütun x'lerini
   ortala, satır adımını düzenle (P2: 12.7 mm), aynı boyutta kullan (P2: 3.2 × 6.1).
9. Takviye: kuyruk ucundan takviye başlangıcına tam genişlik dikdörtgen (arka yüz katmanı).

## 3.2 Ağ (net) mantığı kontrolü
- Her pedin iki tarağı farklı ağda olmalı. P2: A üst tarak = Net1; A alt + B/C üst = Net4 (ortak);
  B alt = Net2; C alt = Net3. Ortak ağ 3 pine, diğerleri 2'şer pine; 7–8 dummy.
- Bir hat bir pedin dış parmağından çıkıyorsa (B sağ parmak, C sol parmak), hat x'i = parmak merkezi.

## 3.3 Doğrulama beklentisi (P2)
Dielektrik IoU 0.968, kenar medyan 0.042 / %90 0.127 mm; gümüş kenar medyan 0.042 / %90 0.085 mm.
Gümüş IoU (~0.73) referans maskenin dokulu ped içi boşlukları yüzünden düşüktür; kabul ölçütü değildir.
