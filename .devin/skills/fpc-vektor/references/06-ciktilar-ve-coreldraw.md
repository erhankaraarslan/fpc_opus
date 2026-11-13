# 06 — Çıktılar, katmanlar, CorelDRAW notları, RAPOR sözleşmesi

## 6.1 Dosyalar (`fpc.py build <ad>`, `<AD>` = büyük harf ad)
| Dosya | İçerik | Amaç |
|---|---|---|
| `<AD>_duzenlenebilir.svg` | hatlar `<polyline>` (stroke = hat genişliği, miter, butt), pedler/bloklar/parmaklar `<rect>`, ovaller `<rect rx>`, dielektrik şeritleri stroke, yamalar `<rect>` | CorelDRAW'da düzenleme |
| `<AD>_uretim.svg` | her katman tek kapalı dolgu yol (evenodd), kesim çizgi | film/serigrafi |
| `<AD>_uretim.pdf` | üretim katmanları, PDF OCG katmanları, kesim yayları Bézier | baskı/onay |
| `<AD>_kontrol_taramali.svg` | üretim katmanları yarı saydam + altta hizalı tarama (JPEG gömülü, 600 dpi) | görsel kontrol |
| `<AD>_rapor.{md,html,pdf}` + `<AD>_rapor_gorseller/` | rapor | dokümantasyon |

Birim: mm, `width/height="...mm"`, `viewBox` mm; her yanda 5 mm sayfa boşluğu (`Design.margin`).

## 6.2 Katmanlar (alttan üste) ve renkler
| id | Etiket | Renk | Not |
|---|---|---|---|
| Takviye | Takviye (arka yuz, ZIF) | #C9B37E | arka yüz |
| Gumus | Gumus iletken | #7F7F7F | alt baskı; köprü bölgeleri kesilmiş |
| Dielektrik | Dielektrik (yalitkan) | #2BB5A0, opaklık 0.55 | nesne bazında opaklık (grup opaklığı değil) |
| Gumus_Kopru | Gumus kopru (2. baski) | #3F3F3F | yalnızca LED tipi |
| LED | LED (montaj) | #F2F2F2 | gövde konturu |
| Etiket | Etiket (yapistirma) | #7A5C00 kesikli | baskı değil |
| Kontrol | Kontrol (taramadan kesin okunamayan) | #FF00FF kesikli | teslimde açık kalsın |
| Kesim | Kesim (dis kontur + pencereler) | #E3001B, 0.1 mm | en üstte |

SVG katmanları `<g id=... inkscape:groupmode="layer" inkscape:label=...>`. CorelDRAW SVG'yi
Dosya > Aç / İçe Aktar ile 1:1 mm açar; üst seviye gruplar nesne yöneticisinde ayrı gruplar olarak
görünür. Grup opaklığı CorelDRAW'da düşebileceği için opaklık her nesneye ayrı verilir.
**Elektriksel tutarlılık:** düzenlenebilir sürümde köprü geçen hat alt katmanda yama içinde
bölünür (`_trace_pieces`), aksi halde alt baskıda kısa devre görünür.

## 6.3 Tasarım modülü sözleşmesi (`parts/<ad>_design.py`)
- `build() -> fpcvec.Design`; `Design.scan = dict(s, px0, py0, mm0)` (doğrulama için zorunlu).
- Elemanlar: `outline`, `holes`, `traces (ad, pts, w)`, `silver_rects (grup, x, y, w, h)`,
  `diel_lines (pts, w)`, `diel_rects`, `diel_rings (x,y,w,h,lw)`, `diel_polys`, `bridges`,
  `bridge_cut (iz_adı, geom)`, `leds (ad, cx, cy, w, h)`, `marks (ad, pts, w)`,
  `stickers (x,y,w,h,r)`, `check (ad, pts)`, `stiff_rects`.
- Ağ kontrolü (references/05 §5.4) adlandırmadan çalışır; **bu kurallara uy**:
  konnektör kontağı `Kontak_<no>` (dummy ise `Kontak_<no>_dummy`), LED `D.leds` adı `X` ise pedleri
  `X_ped_ust` / `X_ped_alt` grupları, tuş pedi grubu `Ped_<ad>` (iki tarak birbirine değmez), köprü adı
  `Kopru_<no>_<iz_adı>`. Başka tip pin/cihaz için `D.pins = [(ad, geom_mm, dummy)]`,
  `D.devices = [(ad, [(uç_adı, geom_mm), ...])]`.
- Hat ucu pede/hatta **bindirilmeli** (≥ hat genişliğinin yarısı); "kenara kadar" bırakılan uç refine sonrası
  birkaç 0.01 mm kısa kalıp çizimde kopukluk olur (`check` → pinsiz_ag + yakin_bosluk).
- Adlandırma: anlamlı ve Türkçe (`Hat_Net1_A_ust`, `Ped_A`, `Kontak_07_dummy`, `LED_L1_ped_ust`).

## 6.4 RAPOR sözlüğü (tasarım modülünde, ZORUNLU)
```python
RAPOR = dict(
    ozet="1-3 cümle: parça ne, yapı, set ilişkisi",
    olculer=[("Ölçü adı", "değer + birim", "not"), ...],     # ana ölçüler, sabitlerden f-string ile
    varsayimlar=["ölçüm yerine kabul edilen her şey", ...],
    kontrol_listesi=["fiziksel parçada doğrulanacak her şey", ...],  # flag'li rotalar otomatik eklenir
    pin_eslemesi=[("pin", "bağlantı"), ...],
)
```
Rapor geri kalanını (kaynak, ölçek, eleman sayıları, alanlar, metrikler + eşik + kabul, katmanlar,
dosyalar, kontrol görselleri) otomatik doldurur. Raporu elle yazma; eksik bilgi varsa RAPOR'a ekle
ve `fpc.py report <ad>` çalıştır.

## 6.5 Analiz kaydı (`parts/<ad>_analiz.json`, ZORUNLU — analiz SIRASINDA doldur)
Şablon: `templates/analiz.json`; dolu örnekler `templates/tus_analiz_ornegi.json`, `led_analiz_ornegi.json`.
Kullanıcıya sohbette verdiğin her bilgilendirme (bulgu, karar, öneri) buraya da yazılır; rapor
yalnızca bu dosyadan beslenir. Alanlar:
- `ozet_notu` — parçanın rolü ve en önemli uyarı (HTML'de vurgulu kutu).
- `surec` — yaptığın adımlar sırasıyla; her adımda bulunan sayı ve kanıt görselleri.
- `bulgular` — ağ yapısı, eksen kaymaları, set ilişkisi, üretim toleransları.
- `karar_noktalari` — ölçümün yetmediği **her** yer: seçenekler, seçilen, gerekçe (sayısal), risk,
  kanıt görselleri; kullanıcıya sorulan sorular `karar_veren: "kullanıcı"`. Rapor K1, K2… diye numaralar.
- `kullanici_yonlendirme` — çıktıyı iyileştirmek için kullanıcının yapabilecekleri (yeni tarama
  yöntemi, kumpas ölçüleri, multimetre testleri, datasheet, CorelDRAW geri bildirimi). Somut ve
  hangi belirsizliği kapattığıyla birlikte.
- `gorseller` — `work/<ad>/` ve `work/_tarama/` altındaki görsellerin açıklaması. Anahtar = dosya adı
  (`_tarama/` öneki tarama klasörü için). Açıklanmayan görseller dosya adından otomatik etiketlenir
  ama "Çalışma görüntüleri" kategorisine düşer — karar/ölçüm/topoloji görsellerinin hepsini açıkla.

## 6.6 Analiz görseli adlandırma (otomatik kategori için)
`kontrol_*` / `ov_*` / `overlay*` → Doğrulama (`kontrol_sapma_*`, `ov_sapma` = sapma ısı haritası) ·
`seg*`, `m_*`, `*mask*`, `edge*`, `comp*`, `polyvec*` → Maskeler · `r_*`, `pdf_*` → Çıktı kontrolü ·
`*_deskew`, `*_full`, `genel`, `parca_*` → Kaynak · `routes*`, `ag_*` → Topoloji · diğerleri → Çalışma görüntüleri. Anlamlı adlar kullan (`v_padA.png`,
`z_kopru_sag_ust.png`), geçici dosyaları `_t.png` adıyla üret (rapora alınmaz).

## 6.7 Rapor çıktıları
- `<AD>_rapor.html`: yan menü, durum kartları, süreç zaman çizelgesi, numaralı karar kartları (kanıt
  küçük resimleriyle), ölçü/metrik tabloları (kabul kapıları, ofset/kayma, en büyük sapmalı elemanlar),
  "Ağ ve tutarlılık" bölümü (bulgu tablosu + çizimden çıkarılan ağ tablosu + ağ haritası),
  işaretlenebilir kontrol listesi (tarayıcıda saklanır),
  kategori + arama filtreli galeri, tekerlekle yakınlaştırılabilen görüntüleyici (← → Esc).
  Görseller `<AD>_rapor_gorseller/` klasöründen göreli yüklenir: HTML'i klasörüyle birlikte taşı.
- `<AD>_rapor.md`: aynı içerik (küçük resimlerle). `<AD>_rapor.pdf`: açıklamalı görseller + karar kanıtları.
- Kontrol: `python -m http.server` ile `output/` sun, tarayıcıda aç; konsolda hata olmamalı.
