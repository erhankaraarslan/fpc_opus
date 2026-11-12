# 05 — Doğrulama ve kabul

## 5.1 Komut
`fpc.py verify <ad>` → `work/<ad>/metrikler.json`, `overlay.png`, `kontrol_<ad>.png` kırpımları.
ROI: `parts/<ad>.json` `dogrulama_roi_y` (boş film ve kuyruk ucunun dokusu bozuk kısmı dışarıda).

## 5.2 Metrikler
| Metrik | Tanım | Eşik | Tip |
|---|---|---|---|
| Kenar sapması medyan | çizim kenar piksellerinden ölçülen maske kenarına mesafe (12 px bant) | ≤ 0.06 mm | hepsi |
| Kenar sapması %90 | aynı dağılımın %90'ı | ≤ 0.15 mm | hepsi |
| Dielektrik IoU | çizim dielektriği vs `teal_closed ∩ kontur` | ≥ 0.95 | tuş |
| Karşılıksız gümüş | ölçülen gümüşün çizimin 9 px dilatasyonu dışında kalan oranı | ≤ 0.15 | LED |
| Gümüş IoU | bilgi amaçlı (dokulu ped içi, şablon ped, damla yüzünden düşük) | — | hepsi |

## 5.3 Görsel kontrol (overlay)
Renkler: kırmızı gümüş, mavi köprü, yeşil dielektrik, mor kesim/oval, turuncu = taramada gümüş var
ama çizimde yok. Her `rapor_kirpimlari` bölgesini oku:
- Hat kenarları taramadaki hatla örtüşüyor mu (1–2 px)?
- Turuncu kümeler: yatay hattın hemen üstünde ince şerit → gölge (normal). LED çevresinde halka →
  kaplama (normal). Uzun, hat genişliğinde turuncu şerit → **çizilmemiş hat** (ekle).
- Köprü (mavi) yalnızca yama üstünde ve 0.4 mm taşıyor mu? Alt gümüş yama içinde kesilmiş mi?
- Kesim konturu film kenarıyla ±0.15 mm içinde mi (kesim dönüklüğü kadar sapma normal)?

## 5.4 Kaldıysa
1. Kenar %90 yüksek: `overlay.png` üzerinde en büyük sapmaların yerini bul
   (`edge_dev` mesafe haritasını kırpımla). Genelde: yanlış oturan refine segmenti (rota düzelt),
   eksik pah, yanlış hat genişliği.
2. Dielektrik IoU düşük: şerit genişliği / çerçeve ofseti / kuyruk dielektrik sınırları yeniden ölç.
3. Karşılıksız gümüş yüksek: turuncu kümeleri sınıflandır; çizilmemiş hatları ekle; leke/damla
   bölgelerini ROI dışında bırakmak yerine rapora yaz (ROI'yi metrik makyajı için daraltma).
4. İki turda geçmiyorsa kullanıcıya sor (yeni tarama / multimetre).

## 5.5 Çapraz kontroller
- Set eşleşmesi: LED merkezleri ↔ tuş katmanı oval merkezleri (kart eksenine göre) farkı x ≤ 0.15 mm.
- Konnektör: kullanılan pin sayısı = kuyruğa giren hat sayısı.
- `fpc.py build` sonunda dosya kontrolü: üç SVG XML olarak ayrıştırılır ve PyMuPDF ile açılır, PDF'te
  Kesim + Gümüş katmanları vardır. Hata = teslim yok.
