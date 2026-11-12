# 02 — Renk maskeleri ve tarama artefaktları

## 2.1 Malzeme renkleri (BGR ortalamaları, K.pdf)
| Malzeme | L (ortalama gri) | T = G − R | Not |
|---|---|---|---|
| Boş film / zemin | 225–255 | ~0 | yerel aydınlatma değişir → yerel arka plan (81 px dilate) kullan |
| Gümüş (açık) | 185–200 | < 15 | **dokulu**: yüksek frekans enerjisi (tex) 4–8 |
| Turkuaz dielektrik (film üstü) | 155–215 | 50–90 | R ~ 90–140 |
| Gümüş, dielektrik ALTINDA (LED tipi) | 135–150 | > 100 | R < 82 (koyu turkuaz) |
| Gümüş, dielektrik ÜSTÜNDE (köprü) | ~185 | ~10 | gri, turkuaz zemin üstünde |
| Tuş tipinde şerit içi gümüş | 196–204 | ~0 | şerit yarı saydam; T≈0 |
| Gölge kopyası | 155–185 | ~0 | **pürüzsüz**: tex 2–3 |
| LED kaplama damlası / yapışkan leke | 200–240 | ~0 | dokusuz, yumuşak geçişli büyük leke |

## 2.2 Maske tarifleri (betiklerde sabit; değiştirmeden önce bir bölgede ölç)
- Tuş tipi (`segment.py`): gümüş = `L < bg-22 & sat < 45`; dielektrik = `T > 30`; referans gümüş =
  (şerit içi `T<20`) ∪ (şerit dışı `bg-48 < L < bg-22 & sat<45`).
- LED tipi (`segment_led.py`): `m_top = 185<L<208 & T<15 & sat<45 & tex>3.2`; `m_under = teal & R<82`;
  `m_teal = T>35`. tex = |L − Gauss(L,σ=2)| ortalaması (9×9).
- Leke altındaki bölge (ör. konnektör toplama alanı) için yerel uyarlamalı eşik:
  `adaptiveThreshold(blur(L), MEAN_C, block 61, C 5) & T<20` + 9 px açma (yalnızca okuma amaçlı;
  gölge kopyalarını da yakalar — her yatay hattın ~20 px üstünde ikizini görürsen gölgedir).

## 2.3 Gölge kopyası (EN ÖNEMLİ ARTEFAKT)
- Neden: film camdan kalkık; tarayıcı ışığı eğik; her opak gümüş şeklin kopyası beyaz kapağa düşer.
- Görünüş: şeklin **~20–28 px (0.4–0.6 mm) yukarısında**, aynı genişlikte, daha koyu ve pürüzsüz
  bir bant; arada genelde ince parlak çizgi. Yatay kenarlarda belirgin, dikey hatlarda uçta uzama
  olarak görülür (dikey hattın üst ucu ~25 px uzun görünür).
- Ayırt etme: (1) dokusuz (tex<3.2), (2) L daha düşük, (3) her zaman gerçek şeklin üstünde,
  (4) yatay iki "hat" arasında 20–28 px offset varsa üstteki gölgedir.
- Ölçümde: yatay hatlar için **alt kenar** güvenilir; üst kenar gölgeyle karışabilir. Tarak pedlerinde
  barların üstündeki koyu bantlar gölgedir (P2'de ilk başta bar sanılmıştı).

## 2.4 Diğer artefaktlar
- Kalem/işaret çemberleri (elle çizilmiş daire): yok say, rapora not.
- LED kaplama damlaları: ped kenarlarını gizler → LED pedleri ölçüm yerine şablondan (references/04).
- Yapışkan/koruyucu leke (dikdörtgen, yarı saydam): altındaki hatlar kontrastı düşük; yüksek geçiren
  filtre (`(L - Gauss(L,25))*4+128`, median 5) ile okunur, yine de `flag=True`.
- Etiket (beyaz kâğıt, yuvarlak köşeli): baskı değil; "Etiket" katmanına sadece kontur olarak koy.
- Turkuaz "çerçeve" (ped çevresinde 0.2 mm ince turkuaz kontur): dielektrik baskı kabul edildi,
  rapora kontrol maddesi.

## 2.5 Görsel kontrol pratiği
- `python .../gridview.py <png> <cikti.png> x0 y0 x1 y1 <olcek> <izgara_px>`; ızgara etiketleri
  gerçek px. Okunabilir kırpım: 300–600 px bölge, ölçek 1–3, ızgara 10–50.
- Aynı yanıtta çok sayıda büyük görüntü okuma: bazı araçlar son birkaç görüntüyü gösterir. Gerekirse
  görüntüleri tek tek oku veya `np.hstack` ile tek mozaik yap.
