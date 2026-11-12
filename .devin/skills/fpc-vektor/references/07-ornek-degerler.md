# 07 — Örnek değerler (K.pdf, 1199 dpi tarama)

Yeni bir parçada başlangıç değeri ve "makul mü?" kontrolü için kullan. Ölçmeden kopyalama.

## Ortak
| Parametre | Değer |
|---|---|
| Ölçek | 47.17 px/mm (konnektör 1.00 mm kalibre; tarayıcı 47.21) |
| Konnektör | 11 poz × 1.00 mm, kontak 0.6 mm, ZIF, arka takviye ~7.8–8 mm |
| Baş hat genişliği | 0.50 mm |
| Kuyruk genişliği | 12.0–12.1 mm, yanlarda 2.0–2.1 mm yarık (tam yuvarlak uç) |
| Baş köşe yarıçapı | ~R1.0 (0.5–1.0 ölçüldü) |
| Gölge kopyası ofseti | 20–28 px (0.4–0.6 mm) yukarı |

## P2 — kısa tuş devresi (`parts/p2_design.py`)
| | |
|---|---|
| Kırpım / açı | [2557, 199, 4516, 8633] / 0.76° |
| Baş | 36.7 × 87.4 mm, toplam 171.9 mm, eksen x=18.35 |
| Yarık üst ucu | 71.55 mm |
| Dielektrik şerit | 2.0 mm (hat ±0.75 mm bindirme), ped çerçevesi ofset 0.75 / çizgi 0.2 |
| Tarak ped | 5.0 × 5.0, bar 0.55, parmak 0.6, boşluk 0.5, uç boşluğu 0.5; tuş ekseni x=19.2 |
| Pedler | A (16.7, 37.8) top3; B (10.9, 53.25); C (22.5, 53.25) |
| Ovaller | 12 × 3.2 × 6.1; sütun x = 5.0 / 31.7, satır 34.0 + k·12.7; orta 19.2 @47.7; alt sıra 12.75/19.2/25.65 @63.65 |
| Kuyruk | blok üst 71.1, çentik 72.35, dummy 7-8 başlangıç 158.95, dielektrik sonu 163.9, takviye 164.0 |
| Çaprazlar | sol üst 60.02°, sol alt 51.44°, sağ alt 50.21° (45 değil — ölçüldü) |
| Metrik | diel IoU 0.968, kenar 0.042/0.127; gümüş 0.042/0.085 |

## P1 — kısa LED devresi (`parts/p1_design.py`, `parts/p1_routes.py`)
| | |
|---|---|
| Kırpım / açı | [599, 199, 2557, 8633] / 0.10° |
| Baş | 36.5 × 87.1 mm, toplam 170.9, eksen px 983.2 (= konnektör pozisyon 6 merkezi), üst kenar px 175 |
| Yarık | 2.1 mm, üst ucu 69.9 |
| Konnektör x | TX[i] = 747.3 + i·47.17 px; kullanılan 0,2,4–9; dummy 1,3,10 (kontak başlangıcı px 7785) |
| Kuyruk dielektriği | px x 688–1238, y 3527–7900 (kesime göre asimetrik, ölçüldüğü gibi) |
| Takviye / etiket | takviye px 7925→uç; etiket px y 4249–5330 |
| LED | 12 × 0402; ped 1.65 × 1.6, boşluk 0.85; site = çip + (4, 8) px |
| "+" | 0.8 mm / 0.15 mm; sol sütun ofset (+59,+119) px, diğerleri (−47,+113) px |
| Yamalar / köprüler | 10 yama (birleşik kümeler dahil), 20 köprü, bindirme 0.4 mm |
| Metrik | gümüş kenar 0.042/0.136, karşılıksız 0.140 |
| Set kontrolü | LED ↔ P2 oval: x farkı ≤ 0.11 mm, y farkı ortalama +0.27 mm |

## P4 — uzun tuş devresi (`parts/p4_design.py`)
| | |
|---|---|
| Kırpım / açı | [6900, 780, 9070, 13710] / 1.07° + `bukulme` (baş baskısı kuyruğa göre 0.445° dönük, kuyruk ±4 px yay) |
| Baş | 36.7 × 141.5 mm, R0.3, toplam 266.25, eksen px 1040, üst kenar px 183 |
| Kuyruk | 11.35 mm (baş altı) → 11.8 mm (y 137.5–157.5), yarık 2.0 mm / üst ucu 125.65 |
| Tuş grubu | P2 ile aynı: KEY_X 19.2, ±5.8, pedler 5.0; A y=38.1, B/C y=53.55 |
| Ovaller | 20 × 3.3 × 6.1; sütun XC ± 13.35; satır 32.15 + k·12.75 (k = 0,1,2,3,4.5,5.5,6.5,7.5) |
| Dielektrik kayması | x +0.15 / y −0.15 mm (çizim ideal, doğrulamada telafi) |
| Metrik | diel IoU 0.979, kenar 0.021/0.085; gümüş 0.042/0.064 |

## P3 — uzun LED devresi (`parts/p3_design.py`, `parts/p3_routes.py`)
| | |
|---|---|
| Kırpım / açı | [4530, 220, 6620, 13010] / 0.68° (bükülme yok) |
| Baş | 36.6 × 138.55 mm (sağ üstü numunede kesik), toplam 263.4, eksen px 964.3, üst kenar px 180 |
| Kuyruk | P4 ile aynı biçim: 11.35 → 11.8 mm; yarık 2.1 mm, üst ucu 122.6; 11 kontak, dummy yok |
| LED | 20 × 0402, site = çip + (3, 5) px; "+" sol sütun (+57,+111), sağ/orta (−47,+113)/(−48,+99) |
| Yamalar / köprüler | 16 yama, 45 köprü; köprü seçimi renkten (gri üst / koyu turkuaz alt) |
| Metrik | gümüş kenar 0.042/0.131 (m_band), karşılıksız 0.207 (kaplama 0.088) |
| Set kontrolü | LED ↔ P4 oval: x ≤ 0.11 mm, y sabit −2.6 mm kayma dışında ≤ 0.21 mm |
