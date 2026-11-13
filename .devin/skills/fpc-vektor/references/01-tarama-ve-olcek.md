# 01 — Tarama analizi, kırpım, eğiklik, ölçek, kesim konturu

## 1.1 Kaynak PDF
- `inspect_scan.py <pdf>`: metin yoksa ve tek gömülü görüntü varsa kaynak bir taramadır.
- Efektif dpi = görüntü genişliği px / (sayfa genişliği pt / 72). Örnek K.pdf: 10192 px / 8.5 in =
  **1199.06 dpi → 47.207 px/mm**. Görüntü JPEG ise sıkıştırma kenarları ~1 px yumuşatır (önemsiz).
- `read` aracı PDF okuyamaz; görüntüyü PyMuPDF ile çıkar (`extract_image`), PNG kırpımlarla bak.
- Genel görünüm ~60 dpi; parça önizlemesi ~150 dpi; ölçüm her zaman tam çözünürlükte.

## 1.2 Parça tipini tanıma
| Görünüm | Tip | Not |
|---|---|---|
| Tarak (interdigitated) pedler, oval delikler, hatlar 2 mm turkuaz şerit içinde | `tus` | P2/P4 |
| Küçük SMD LED'ler (yeşil "T" çip), turkuaz dikdörtgen yamalar, hat kesişmeleri | `led` | P1/P3 |
- Set eşleşmesi: tuş katmanındaki oval pencere konumları = LED katmanındaki LED konumları
  (P1↔P2 farkı x'te ≤ 0.1 mm). Bu, ölçümlerin çapraz doğrulamasıdır; raporda belirt.

## 1.3 Kırpım ve eğiklik
- `kirpim_px`: parça + 120 px pay (inspect_scan.py otomatik ekler; film kenarı soluk olduğundan dar kutu kenarı kesebilir). Komşu parçaya taşmamalı (eğiklik ölçümünü bozar).
- `fpc.py skew <ad>`: Hough doğrularının eksenden ağırlıklı sapması. P2: 0.76°, P1: 0.10°.
- Doğrulama: deskew sonrası uzun bir dikey hattın merkezi baş/son farkı ≤ 2 px
  (`measure.py <ad> h y-10 y+10 x0 x1` iki farklı y'de).
- **Bükülme otomatik kestirimi**: `fpc.py bukulme <ad>` → döndürülmüş kırpımda 200 px bantların yatay gradyan
  profilleri komşu bantlarla alt-piksel korele edilir, kaymalar toplanır → `work/<ad>/bukulme_onerisi.json`
  (`xc`, `dx_noktalar`, kalan eğim). Doğrusal olmayan genlik < 3 px ise bükülme düzeltmesine gerek yok.
  P4'te elle ölçülen bükülmeyle korelasyon 0.982 (RMS fark 4.6 px); P3 genlik 4.2 px.
- **Kesim deseni baskıya göre ayrıca dönük olabilir** (P2 ~0.2°, P1 kuyrukta ~0.26°). Baskı (hatlar)
  referans alınır; kesim ideal hizalı/simetrik çizilir ve fark rapora "varsayım" olarak yazılır.

## 1.4 Ölçek kalibrasyonu
1. Kuyrukta 3 farklı y'de (`measure.py <ad> h y0 y1 x0 x1`) T kanalı kenarlarından hat merkezleri.
   T kanalında `-` (turkuaz biter = gümüş başlar) ile `+` arası gümüştür.
2. Merkezlerin pozisyon indeksine doğrusal fiti → adım px. Boş pozisyonları (2 adım atlayan aralık)
   indeksle dikkate al.
3. Adım = 1.00 mm kabul → `olcek_px_mm`. K.pdf: 47.17 (nominal 47.21, fark %0.08).
   **Otomatik**: `fpc.py olcek <ad> x0 y0 x1 y1 [adim_mm] [x|y]` (ROI yalnız kontakları içersin, takviye/etiket
   kenarı değil): DTFT kaba periyot + faz → her pozisyonda yarı-yükseklik ağırlıklı merkez → MAD ayıklamalı
   doğrusal fit (dummy pozisyonlar indeksle atlanır). Çıktıda hat sayısı ve artık RMS: RMS > 1 px = ROI kötü.
   K.pdf: P2 1.0019 mm (8 hat, RMS 0.13 px), P3 1.0003 mm (10 hat, RMS 0.30 px) @ 47.17 px/mm.
4. **y ölçeği** konnektörden ölçülemez (adım x yönünde). Yeni taramalarda aynı camda bir çelik cetvel / mm
   ızgara tara ve `olcek ... y` ile ayrıca ölç; x ile y farkı > %0.1 ise tarayıcı motor yönü hatası var.
5. px→mm: `mm_x = (px - eksen_px) / s + W/2`, `mm_y = (py - ust_kenar_px) / s`. Orijin baş sol üst köşe,
   y aşağı. `SCAN = dict(s=..., px0=eksen_px, py0=ust_kenar_px, mm0=(W/2, 0))` tasarımda tutulur.

## 1.5 Kesim konturu ölçümü
- Film kenarı = koyu ince çizgi (gölge). `measure.py <ad> h y0 y1 x0 x1` (L kanalı) veya ham profil:
  `L[y0:y1, x0:x1].mean(0)` minimumu.
- **Üst kenarlar**: gölge bandı (~20 px) kenarın *üstünde*; gerçek kenar = bandın alt ucu.
  **Alt/yan kenarlar**: koyu çizginin kendisi.
- Ölçülecekler: baş sol/sağ (en az 2 y'de), üst, alt (en az 2 x'te); kuyruk sol/sağ (3 y'de);
  yarık dış kenarları ve üst yay (yay tepe y'si = yay kenarının merkezden dx uzaklıktaki y'sinden
  `r - sqrt(r²-dx²)` düzeltmesiyle); kuyruk ucu; köşe yarıçapları (ızgaralı 1.5× kırpım, 20 px ızgara).
- Değerleri 0.05 mm'ye yuvarla. Köşe yarıçapı belirsizse R1.0 ve rapora varsayım.

## 1.6 Kontur yolu (fpcvec outline sözleşmesi)
Komutlar: `("M",x,y)`, `("L",x,y)`, `("A", r, sweep, x, y)` (SVG küçük yay; sweep=1 ekranda saat
yönü), `("Z",)`. Yarık üst yayı: dış kenardan iç kenara giderken `sweep=0` (tepe y'si küçük).
Köşe: `("L", W-R, 0), ("A", R, 1, W, R)`. Ovaller `holes=(cx, cy, w, h)` (stadium, rx = w/2).
