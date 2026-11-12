"""Parça raporunu Markdown, HTML (etkileşimli) ve PDF olarak üretir.

Kullanım: python report.py <ad>
Python içinden: run(ad, D=None, M=None)

İçerik kaynakları (hepsi otomatik birleştirilir):
  parts/<ad>.json             kaynak, kırpım, açı, ölçek
  parts/<ad>_design.py        build() -> Design (ölçüler, sayılar, katmanlar, Kontrol rotaları) + RAPOR sözlüğü
  parts/<ad>_analiz.json      analiz kaydı: süreç, bulgular, karar noktaları, görsel açıklamaları,
                              kullanıcı yönlendirmeleri (references/06 §Analiz kaydı)
  work/<ad>/metrikler.json    doğrulama metrikleri + kabul
  work/<ad>/*.png, work/_tarama/*.png   tüm analiz görselleri (açıklamasızlara dosya adından otomatik açıklama)
Çıktılar:
  output/<AD>_rapor.html      tek sayfa, yan menü, filtrelenebilir galeri, yakınlaştırmalı görüntüleyici,
                              işaretlenebilir kontrol listesi (tarayıcıda saklanır)
  output/<AD>_rapor.md        aynı içerik, Markdown
  output/<AD>_rapor.pdf       basılabilir sürüm (açıklamalı görseller + karar kanıtları)
  output/<AD>_rapor_gorseller/  rapor görselleri (JPEG, küçültülmüş). HTML/MD bu klasörü göreli kullanır.
"""
import datetime
import glob
import html
import importlib
import json
import os
import sys

import cv2
import pymupdf

import cfg

E = html.escape
KAT_SIRA = ["Kaynak", "Ön işleme", "Maskeler", "Ölçüm", "Topoloji", "Karar kanıtı", "Doğrulama",
            "Çıktı kontrolü", "Çalışma görüntüleri"]
HARIC = ("_t.png", "rapor_s1.png", "rapor_son.png")
LEJANT = ("Bindirme renkleri: <b style='color:#d00'>kırmızı</b> gümüş (alt baskı), <b style='color:#00f'>mavi</b> "
          "köprü (2. baskı), <b style='color:#090'>yeşil</b> dielektrik, <b style='color:#c0c'>mor</b> kesim/oval, "
          "<b style='color:#e90'>turuncu</b> taramada olup çizimde karşılığı olmayan gümüş.")

GENEL_REHBER = [
    ("Önce durum kartlarına bakın", "Kabul durumu GEÇTİ ise kenar sapmaları eşik içindedir. Belirsiz rota sayısı 0 değilse "
     "'Fiziksel kontrol' bölümündeki maddeler doğrulanmadan çizim üretime verilmemelidir."),
    ("Karar noktalarını okuyun", "Ölçümün yetmediği her yerde hangi seçeneğin neden seçildiği ve kanıt görselleri verilmiştir. "
     "Katılmadığınız karar varsa numarasıyla bildirin (ör. 'K4: koyu bantlar gerçek bar')."),
    ("Galeride inceleyin", "Görsellere tıklayınca büyük açılır; fare tekerleğiyle yakınlaştırıp sürükleyebilirsiniz. "
     "Kategori düğmeleri ve arama kutusuyla filtreleyin."),
    ("Kontrol taramalı SVG'yi açın", "<code>_kontrol_taramali.svg</code> dosyasında çizim, hizalanmış taramanın üstündedir. "
     "CorelDRAW'da tarama katmanını kilitleyip katmanları tek tek açıp kapatarak karşılaştırın."),
]
CORELDRAW = [
    "Dosya &gt; Aç (veya İçe Aktar) ile SVG'yi açın; ölçek 1:1 mm'dir, sayfa her yanda 5 mm boşlukludur.",
    "Katmanlar üst seviye gruplar olarak gelir (Nesne Yöneticisi). Düzenlemeden önce 'Kesim' ve 'Tarama' gruplarını kilitleyin.",
    "Düzenlenebilir sürümde hatlar kalınlıklı çizgidir: düğüm taşıyarak rota değiştirin, kalınlığı Kontur penceresinden değiştirin.",
    "Üretim için dolgu sürümünü (<code>_uretim.svg</code> / <code>.pdf</code>) kullanın; her baskı katmanı ayrı film/elektir.",
    "Kalıcı değişiklik istiyorsanız ölçüyü <code>parts/&lt;ad&gt;_design.py</code> içinde değiştirip "
    "<code>fpc.py all &lt;ad&gt;</code> çalıştırın; böylece doğrulama ve rapor da güncellenir.",
]


# ------------------------------------------------------------------ veri toplama
def _otomatik(ad):
    """Analiz kaydında açıklaması olmayan görseller için dosya adından kategori/açıklama."""
    n = ad.lower()
    if n.startswith("kontrol_"):
        return "Doğrulama", f"Rapor kontrol kırpımı: {n[8:-4].replace('_', ' ')}", "Doğrulama bindirmesinden kırpım. " + LEJANT
    if n.startswith(("ov_", "overlay")):
        return "Doğrulama", "Taramaya bindirme", "Çizim geometrisi taramanın üstüne çizildi. " + LEJANT
    if n.startswith(("seg", "m_", "silver", "edge", "comp", "fanmask", "polyvec")) or "mask" in n:
        return "Maskeler", "Maske / segmentasyon görseli", "Renk ve doku eşikleriyle elde edilen malzeme maskesi."
    if n.startswith(("r_", "pdf_")):
        return "Çıktı kontrolü", "Çıktı render kontrolü", "Üretilen SVG/PDF dosyasının rasterleştirilmiş önizlemesi."
    if n.endswith(("_deskew.png", "_full.png")) or n.startswith(("genel", "parca_")):
        return "Kaynak", "Kaynak görüntü", "Taramadan kırpılan / incelenen ham görüntü."
    if n.startswith("routes"):
        return "Topoloji", "Rota bindirmesi", "Kaba rotaların refine sonrası taramaya bindirilmiş hali."
    return "Çalışma görüntüleri", "Izgaralı yakın çekim", "Ölçüm ve okuma için üretilmiş ızgaralı kırpım (ızgara etiketleri tarama pikseli)."


def collect_images(ad, A, imgdir):
    import shutil
    shutil.rmtree(imgdir, ignore_errors=True)
    os.makedirs(imgdir, exist_ok=True)
    meta = A.get("gorseller", {})
    files = sorted(glob.glob(os.path.join("work", ad, "*.png"))) + sorted(glob.glob(os.path.join("work", "_tarama", "*.png")))
    out = []
    for p in files:
        b = os.path.basename(p)
        if b in HARIC or b.startswith("_") or b.endswith("_t.png"):  # geçici çalışma görüntüleri
            continue
        key = b if "_tarama" not in p else f"_tarama/{b}"
        m = meta.get(key) or meta.get(b)
        kat, bas, acik = (m.get("kategori"), m.get("baslik"), m.get("aciklama")) if m else _otomatik(b)
        im = cv2.imread(p)
        if im is None:
            continue
        h, w = im.shape[:2]
        s = min(1.0, 1800.0 / max(h, w))
        big = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else im
        t = min(1.0, 420.0 / max(h, w))
        th = cv2.resize(im, None, fx=t, fy=t, interpolation=cv2.INTER_AREA)
        stem = key.replace("/", "_")[:-4]
        cv2.imwrite(os.path.join(imgdir, stem + ".jpg"), big, [cv2.IMWRITE_JPEG_QUALITY, 84])
        cv2.imwrite(os.path.join(imgdir, stem + "_k.jpg"), th, [cv2.IMWRITE_JPEG_QUALITY, 80])
        out.append(dict(key=key, stem=stem, kategori=kat or "Çalışma görüntüleri", baslik=bas, aciklama=acik,
                        olcum=(m or {}).get("olcum", ""), karar=(m or {}).get("karar", ""), aciklamali=bool(m),
                        sira=(m or {}).get("sira", 999), w=big.shape[1], h=big.shape[0], orj=[w, h]))
    out.sort(key=lambda g: (KAT_SIRA.index(g["kategori"]) if g["kategori"] in KAT_SIRA else 99, g["sira"], g["key"]))
    return out


def collect(ad, D, M):
    c = cfg.load(ad)
    mod = importlib.import_module(c.get("tasarim_modulu", f"{ad}_design"))
    R = getattr(mod, "RAPOR", {}) or {}
    ap = f"parts/{ad}_analiz.json"
    A = json.load(open(ap, encoding="utf-8")) if os.path.exists(ap) else {}
    P = ad.upper()
    olp = D.outline_poly()
    x0, y0, x1, y1 = olp.bounds
    auto = [("Kart sınır kutusu", f"{x1 - x0:.2f} × {y1 - y0:.2f} mm", "Kesim konturu"),
            ("Kart alanı", f"{olp.area:.1f} mm²", ""),
            ("Gümüş alanı (alt baskı)", f"{D.silver_geom().area:.1f} mm²", ""),
            ("Dielektrik alanı", f"{D.diel_geom().area:.1f} mm²", "")]
    if D.bridges:
        auto.append(("Köprü alanı (2. gümüş baskı)", f"{D.bridge_geom().area:.2f} mm²", f"{len(D.bridges)} köprü"))
    counts = [("Hat (polyline)", len(D.traces)), ("Gümüş dikdörtgen (ped/blok/parmak)", len(D.silver_rects)),
              ("Oval pencere", len(D.holes)), ("LED", len(D.leds)), ("Dielektrik yama", len(D.diel_polys)),
              ("Köprü", len(D.bridges)), ("Kontrol (belirsiz) rota", len(D.check))]
    files = [(f"output/{P}_duzenlenebilir.svg", "CorelDRAW'da düzenleme (hatlar kalınlıklı çizgi, pedler dikdörtgen)"),
             (f"output/{P}_uretim.svg", "Üretim: her katman tek kapalı dolgu"),
             (f"output/{P}_uretim.pdf", "Üretim: katmanlı vektör PDF"),
             (f"output/{P}_kontrol_taramali.svg", "Kontrol: çizim + altta hizalı tarama")]
    pdfp = f"output/{P}_uretim.pdf"
    layers = [v["name"] for v in pymupdf.open(pdfp).get_ocgs().values()] if os.path.exists(pdfp) else []
    kl = list(R.get("kontrol_listesi", [])) + [f"Kontrol katmanı: '{n}' rotası taramadan kesin okunamadı" for n, _ in D.check]
    return dict(P=P, ad=ad, c=c, R=R, A=A, D=D, M=M, auto=auto, counts=counts, files=files, layers=layers, kl=kl)


def metric_rows(M):
    Es = M["esik"]
    rows = []
    for key, lbl in (("dielektrik", "Dielektrik"), ("gumus", "Gümüş")):
        if key not in M:
            continue
        m = M[key]
        rows.append((f"{lbl} kenar sapması medyan", f"{m['kenar_medyan_mm']:.3f} mm", f"≤ {Es['kenar_medyan_mm']} mm",
                     m["kenar_medyan_mm"] <= Es["kenar_medyan_mm"]))
        rows.append((f"{lbl} kenar sapması %90", f"{m['kenar_p90_mm']:.3f} mm", f"≤ {Es['kenar_p90_mm']} mm",
                     m["kenar_p90_mm"] <= Es["kenar_p90_mm"]))
        if key == "dielektrik":
            rows.append(("Dielektrik IoU", f"{m['iou']:.3f}", f"≥ {Es['dielektrik_iou_min']}", m["iou"] >= Es["dielektrik_iou_min"]))
        else:
            rows.append(("Gümüş IoU", f"{m['iou']:.3f}", "bilgi", None))
            led = M["tip"] == "led"
            rows.append(("Taramada karşılıksız gümüş", f"{m['karsiliksiz_oran']:.3f}", f"≤ {Es['karsiliksiz_max']}" if led else "bilgi",
                         (m["karsiliksiz_oran"] <= Es["karsiliksiz_max"]) if led else None))
    return rows


# ------------------------------------------------------------------ HTML
CSS = """
:root{--ana:#1f4e79;--acik:#eef4fa;--yesil:#1a7f37;--kirmizi:#c62828;--turuncu:#e67e00;--gri:#666;--kenar:#d7dde4}
*{box-sizing:border-box} body{margin:0;font-family:"Segoe UI",Arial,sans-serif;color:#1d2733;background:#f6f8fa;font-size:14.5px;line-height:1.5}
a{color:var(--ana)} code{background:#eef1f4;padding:1px 5px;border-radius:4px;font-size:90%}
nav{position:fixed;top:0;left:0;bottom:0;width:250px;background:#16324f;color:#fff;overflow-y:auto;padding:18px 14px}
nav h2{font-size:15px;margin:0 0 4px} nav .alt{font-size:12px;color:#b9c8d8;margin-bottom:14px}
nav a{display:block;color:#dfe8f1;text-decoration:none;padding:5px 8px;border-radius:6px;font-size:13.5px}
nav a:hover{background:#244a70}
main{margin-left:250px;padding:26px 34px 80px;max-width:1350px}
header.ust{background:linear-gradient(120deg,#1f4e79,#2e75b6);color:#fff;border-radius:14px;padding:22px 26px;margin-bottom:20px}
header.ust h1{margin:0 0 6px;font-size:24px} header.ust p{margin:0;color:#dce9f6}
.kartlar{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;margin:16px 0}
.kart{background:#fff;border:1px solid var(--kenar);border-radius:12px;padding:12px 14px}
.kart .e{font-size:12px;color:var(--gri);text-transform:uppercase;letter-spacing:.4px} .kart .d{font-size:21px;font-weight:600;margin-top:2px}
.ok{color:var(--yesil)} .bad{color:var(--kirmizi)} .warn{color:var(--turuncu)}
section{background:#fff;border:1px solid var(--kenar);border-radius:14px;padding:18px 22px;margin:18px 0}
section h2{margin:0 0 12px;font-size:19px;color:var(--ana)} h3{font-size:15.5px;margin:16px 0 6px}
table{border-collapse:collapse;width:100%;margin:6px 0 4px} th,td{border-bottom:1px solid #e6eaee;padding:7px 9px;text-align:left;vertical-align:top}
th{background:var(--acik);font-weight:600;font-size:13px}
.rozet{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:600}
.r-ok{background:#e3f4e8;color:var(--yesil)} .r-bad{background:#fdecea;color:var(--kirmizi)} .r-bilgi{background:#eef1f4;color:#555}
.zaman{border-left:3px solid #2e75b6;margin-left:8px;padding-left:18px}
.zaman .adim{position:relative;margin:0 0 14px} .zaman .adim:before{content:"";position:absolute;left:-26px;top:5px;width:13px;height:13px;border-radius:50%;background:#2e75b6;border:2px solid #fff;box-shadow:0 0 0 2px #2e75b6}
.zaman .adim b{display:block}
.karar{border:1px solid var(--kenar);border-left:5px solid #2e75b6;border-radius:10px;padding:12px 16px;margin:12px 0;background:#fbfcfe}
.karar .no{font-weight:700;color:#2e75b6;margin-right:6px} .karar ul{margin:6px 0 6px 18px;padding:0}
.karar .secilen{background:#e3f4e8;border-radius:6px;padding:6px 10px;margin:6px 0}
.karar .kanit{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px} .karar .kanit img{height:110px;border-radius:6px;border:1px solid var(--kenar);cursor:zoom-in}
.not{background:#fff8e6;border:1px solid #f1d58a;border-radius:10px;padding:10px 14px;margin:10px 0}
.bilgi{background:var(--acik);border:1px solid #c9dbee;border-radius:10px;padding:10px 14px;margin:10px 0}
.kl label{display:block;padding:7px 10px;border:1px solid #e3e7eb;border-radius:8px;margin:6px 0;cursor:pointer;background:#fff}
.kl input{margin-right:8px;transform:scale(1.2)} .kl label.tik{background:#eef8f1;text-decoration:line-through;color:#4a6;}
.arac{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.arac button{border:1px solid var(--kenar);background:#fff;border-radius:20px;padding:5px 12px;cursor:pointer;font-size:13px}
.arac button.aktif{background:var(--ana);color:#fff;border-color:var(--ana)} .arac input{flex:1;min-width:200px;padding:7px 10px;border:1px solid var(--kenar);border-radius:8px}
.galeri{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.gk{border:1px solid var(--kenar);border-radius:10px;overflow:hidden;background:#fff;display:flex;flex-direction:column}
.gk .res{height:190px;background:#f0f2f4 center/contain no-repeat;cursor:zoom-in;border-bottom:1px solid #eee}
.gk .m{padding:9px 11px;font-size:13px} .gk .m b{display:block;font-size:13.5px;margin-bottom:3px}
.gk .k{font-size:11px;color:#2e75b6;font-weight:600;text-transform:uppercase} .gk .o{color:#1a7f37;font-size:12.5px;margin-top:4px}
.gk .dosya{color:#999;font-size:11px;margin-top:4px;font-family:Consolas,monospace}
#lb{position:fixed;inset:0;background:rgba(10,18,28,.93);display:none;z-index:99;color:#fff}
#lb .alan{position:absolute;inset:0 0 120px 0;overflow:hidden;cursor:grab} #lb img{position:absolute;transform-origin:0 0;max-width:none;user-select:none}
#lb .alt{position:absolute;left:0;right:0;bottom:0;height:120px;padding:10px 22px;background:#0d1a27;overflow:auto;font-size:13.5px}
#lb .kapat{position:absolute;top:10px;right:18px;font-size:28px;cursor:pointer;z-index:3} #lb .ok-btn{position:absolute;top:45%;font-size:40px;cursor:pointer;z-index:3;padding:0 14px;user-select:none}
#lb .sol{left:6px} #lb .sag{right:6px}
@media print{nav,#lb,.arac{display:none} main{margin:0;padding:0} section{break-inside:avoid}}
"""

JS = r"""
const G=window.GORSELLER;let cur=-1,sc=1,tx=0,ty=0;
function goster(i){cur=i;const g=G[i];const lb=document.getElementById('lb');const im=document.getElementById('lbimg');
 im.onload=()=>{const a=document.querySelector('#lb .alan').getBoundingClientRect();sc=Math.min(a.width/im.naturalWidth,a.height/im.naturalHeight,1.5);
 tx=(a.width-im.naturalWidth*sc)/2;ty=(a.height-im.naturalHeight*sc)/2;uyg();};im.src=g.src;
 document.getElementById('lbalt').innerHTML='<b>'+g.baslik+'</b> <span style="color:#9bb">['+g.kategori+'] '+g.key+'</span><br>'+g.aciklama+(g.olcum?'<br><span style="color:#7ed69a">Ölçüm: '+g.olcum+'</span>':'');
 lb.style.display='block';}
function uyg(){document.getElementById('lbimg').style.transform=`translate(${tx}px,${ty}px) scale(${sc})`;}
function kapat(){document.getElementById('lb').style.display='none';}
function ileri(d){goster((cur+d+G.length)%G.length);}
document.addEventListener('keydown',e=>{if(document.getElementById('lb').style.display!=='block')return;if(e.key==='Escape')kapat();if(e.key==='ArrowRight')ileri(1);if(e.key==='ArrowLeft')ileri(-1);});
window.addEventListener('load',()=>{const al=document.querySelector('#lb .alan');let dr=null;
 al.addEventListener('wheel',e=>{e.preventDefault();const r=al.getBoundingClientRect();const mx=e.clientX-r.left,my=e.clientY-r.top;const f=e.deltaY<0?1.2:1/1.2;tx=mx-(mx-tx)*f;ty=my-(my-ty)*f;sc*=f;uyg();},{passive:false});
 al.addEventListener('mousedown',e=>{dr=[e.clientX-tx,e.clientY-ty];al.style.cursor='grabbing';});
 window.addEventListener('mouseup',()=>{dr=null;al.style.cursor='grab';});
 window.addEventListener('mousemove',e=>{if(dr){tx=e.clientX-dr[0];ty=e.clientY-dr[1];uyg();}});
 document.querySelectorAll('.kl input').forEach(cb=>{const k='kl_'+document.body.dataset.parca+'_'+cb.dataset.i;cb.checked=localStorage.getItem(k)==='1';
  cb.parentElement.classList.toggle('tik',cb.checked);cb.addEventListener('change',()=>{localStorage.setItem(k,cb.checked?'1':'0');cb.parentElement.classList.toggle('tik',cb.checked);});});
 filtrele();});
let aktifKat='Tümü';
function kat(b){aktifKat=b.dataset.k;document.querySelectorAll('.arac button').forEach(x=>x.classList.toggle('aktif',x===b));filtrele();}
function filtrele(){const q=(document.getElementById('ara').value||'').toLowerCase();let n=0;
 document.querySelectorAll('.gk').forEach(el=>{const g=G[+el.dataset.i];const ok=(aktifKat==='Tümü'||g.kategori===aktifKat)&&(!q||(g.baslik+' '+g.aciklama+' '+g.key+' '+g.olcum).toLowerCase().includes(q));
 el.style.display=ok?'':'none';if(ok)n++;});document.getElementById('sayi').textContent=n+' görsel';}
"""


def _tbl(head, rows):
    s = "<table><tr>" + "".join(f"<th>{E(h)}</th>" for h in head) + "</tr>"
    for r in rows:
        s += "<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>"
    return s + "</table>"


def _rozet(ok):
    return "<span class='rozet r-bilgi'>bilgi</span>" if ok is None else (
        "<span class='rozet r-ok'>✔ geçti</span>" if ok else "<span class='rozet r-bad'>✘ kaldı</span>")


def to_html(X, imgs, rel):
    c, R, A, M, D = X["c"], X["R"], X["A"], X["M"], X["D"]
    gidx = {g["key"]: i for i, g in enumerate(imgs)}
    js_data = [dict(key=g["key"], src=f"{rel}/{g['stem']}.jpg", baslik=g["baslik"], aciklama=g["aciklama"],
                    kategori=g["kategori"], olcum=g["olcum"]) for g in imgs]
    nav = [("ozet", "Özet"), ("rehber", "Nasıl incelenir?"), ("surec", "Süreç"), ("bulgular", "Bulgular"),
           ("kararlar", "Karar noktaları"), ("olculer", "Ölçüler"), ("dogrulama", "Doğrulama"), ("pinler", "Pin eşlemesi"),
           ("kontrol", "Fiziksel kontrol"), ("yonlendirme", "Daha iyi sonuç için"), ("galeri", "Analiz görselleri"),
           ("ciktilar", "Çıktılar ve CorelDRAW"), ("ek", "Ek: parametreler")]
    H = [f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
         f"<title>{E(D.title)} — Rapor</title><style>{CSS}</style></head><body data-parca='{X['ad']}'>"]
    H.append(f"<nav><h2>{E(X['P'])} raporu</h2><div class='alt'>{E(D.title)}</div>"
             + "".join(f"<a href='#{a}'>{E(b)}</a>" for a, b in nav) + "</nav><main>")
    st = M["gecti"]
    H.append(f"<header class='ust'><h1>{E(D.title)}</h1><p>Oluşturma: {datetime.datetime.now():%d.%m.%Y %H:%M} · "
             f"Kaynak: {E(c['pdf'])} · fpc-vektor skill</p></header>")
    g = M["gumus"]
    cards = [("Kabul durumu", f"<span class='{'ok' if st else 'bad'}'>{'GEÇTİ' if st else 'KALDI'}</span>"),
             ("Gümüş kenar sapması (medyan / %90)", f"{g['kenar_medyan_mm']:.3f} / {g['kenar_p90_mm']:.3f} mm")]
    if "dielektrik" in M:
        cards.append(("Dielektrik IoU", f"{M['dielektrik']['iou']:.3f}"))
    cards += [("Belirsiz (Kontrol) rota", f"<span class='{'warn' if D.check else 'ok'}'>{len(D.check)}</span>"),
              ("Fiziksel kontrol maddesi", f"<span class='{'warn' if X['kl'] else 'ok'}'>{len(X['kl'])}</span>"),
              ("Karar noktası", str(len(A.get("karar_noktalari", [])))),
              ("Analiz görseli", str(len(imgs)))]
    H.append("<div class='kartlar'>" + "".join(f"<div class='kart'><div class='e'>{E(a)}</div><div class='d'>{b}</div></div>"
                                                for a, b in cards) + "</div>")
    # Özet
    H.append("<section id='ozet'><h2>Özet</h2>")
    if R.get("ozet"):
        H.append(f"<p>{E(R['ozet'])}</p>")
    if A.get("ozet_notu"):
        H.append(f"<div class='bilgi'>{A['ozet_notu']}</div>")
    if D.check:
        H.append("<div class='not'><b>Dikkat:</b> Bu parçada taramadan kesin okunamayan bağlantılar var. Çizimde mor kesikli "
                 "'Kontrol' katmanında işaretlidir. Fiziksel kontrol listesi tamamlanmadan üretime vermeyin.</div>")
    H.append("</section>")
    # Rehber
    H.append("<section id='rehber'><h2>Bu rapor nasıl incelenir?</h2><div class='zaman'>"
             + "".join(f"<div class='adim'><b>{i}. {E(a)}</b>{b}</div>" for i, (a, b) in enumerate(GENEL_REHBER, 1))
             + f"</div><div class='bilgi'>{LEJANT}</div></section>")
    # Süreç
    if A.get("surec"):
        H.append("<section id='surec'><h2>Analiz süreci</h2><div class='zaman'>")
        for i, s in enumerate(A["surec"], 1):
            kan = "".join(_thumb(k, gidx, imgs, rel) for k in s.get("gorseller", []))
            H.append(f"<div class='adim'><b>{i}. {E(s['baslik'])}</b>{s['aciklama']}"
                     + (f"<div class='karar' style='border:none;padding:0;background:none'><div class='kanit'>{kan}</div></div>" if kan else "")
                     + "</div>")
        H.append("</div></section>")
    # Bulgular
    if A.get("bulgular"):
        H.append("<section id='bulgular'><h2>Bulgular</h2><ul>" + "".join(f"<li>{b}</li>" for b in A["bulgular"]) + "</ul></section>")
    # Kararlar
    if A.get("karar_noktalari"):
        H.append("<section id='kararlar'><h2>Karar noktaları</h2><p class='small'>Ölçümün tek başına yetmediği, yorum veya "
                 "kullanıcı tercihi gerektiren noktalar. Katılmadığınız kararı numarasıyla bildirin.</p>")
        for i, k in enumerate(A["karar_noktalari"], 1):
            kan = "".join(_thumb(x, gidx, imgs, rel) for x in k.get("kanit", []))
            sec = "".join(f"<li>{E(s)}</li>" for s in k.get("secenekler", []))
            H.append(f"<div class='karar' id='K{i}'><div><span class='no'>K{i}</span><b>{E(k['baslik'])}</b> "
                     f"<span class='rozet r-bilgi'>{E(k.get('karar_veren', 'analiz'))}</span></div>"
                     + (f"<div>{k['soru']}</div>" if k.get("soru") else "")
                     + (f"<ul>{sec}</ul>" if sec else "")
                     + f"<div class='secilen'><b>Seçilen:</b> {k['secilen']}</div>"
                     + (f"<div><b>Gerekçe:</b> {k['gerekce']}</div>" if k.get("gerekce") else "")
                     + (f"<div class='warn'><b>Etki/risk:</b> {k['risk']}</div>" if k.get("risk") else "")
                     + (f"<div class='kanit'>{kan}</div>" if kan else "") + "</div>")
        H.append("</section>")
    # Ölçüler
    H.append("<section id='olculer'><h2>Ölçüler ve eleman sayıları</h2>"
             + _tbl(["Ölçü", "Değer", "Not"], [tuple(E(str(v)) for v in r) for r in list(R.get("olculer", [])) + X["auto"]])
             + "<h3>Eleman sayıları</h3>" + _tbl(["Eleman", "Adet"], [(E(a), b) for a, b in X["counts"]]))
    if R.get("varsayimlar"):
        H.append("<h3>Varsayımlar</h3><ul>" + "".join(f"<li>{E(v)}</li>" for v in R["varsayimlar"]) + "</ul>")
    H.append("</section>")
    # Doğrulama
    rows = [(E(a), b, E(t), _rozet(ok)) for a, b, t, ok in metric_rows(M)]
    kan = "".join(_thumb(k, gidx, imgs, rel, h=150) for k in [x["key"] for x in imgs if x["kategori"] == "Doğrulama"])
    H.append(f"<section id='dogrulama'><h2>Doğrulama (taramaya bindirme)</h2><p>Kabul durumu: "
             f"{'<span class=\"rozet r-ok\">GEÇTİ</span>' if st else '<span class=\"rozet r-bad\">KALDI</span>'} · ROI y = "
             f"{M['roi_y_px']} px</p>" + _tbl(["Metrik", "Değer", "Eşik", "Sonuç"], rows)
             + "<div class='bilgi'>Kenar sapması: çizimin her kenar pikselinden taramada ölçülen malzeme kenarına mesafe. "
               "IoU (örtüşme oranı) gümüşte bilgi amaçlıdır: dokulu ped içleri, LED kaplama damlaları ve gölgeler referans "
               "maskeyi bozar. " + LEJANT + "</div>" + f"<div class='karar' style='border:none;padding:0;background:none'><div class='kanit'>{kan}</div></div></section>")
    # Pinler
    if R.get("pin_eslemesi"):
        H.append("<section id='pinler'><h2>Konnektör pin eşlemesi</h2>" + _tbl(["Pin", "Bağlantı"], [(E(a), E(b)) for a, b in R["pin_eslemesi"]])
                 + "</section>")
    # Kontrol listesi
    H.append("<section id='kontrol'><h2>Fiziksel parçada kontrol edilecekler</h2>")
    if X["kl"]:
        H.append("<p>İşaretledikleriniz bu tarayıcıda saklanır. Multimetre süreklilik testiyle doğrulayıp sonucu "
                 "'Pin 5 ↔ LED B1 üst ped: süreklilik VAR' biçiminde iletin.</p><div class='kl'>"
                 + "".join(f"<label><input type='checkbox' data-i='{i}'>{E(v)}</label>" for i, v in enumerate(X["kl"])) + "</div>")
    else:
        H.append("<p class='ok'>Bu parça için açık kontrol maddesi yok.</p>")
    H.append("</section>")
    # Yönlendirme
    yon = A.get("kullanici_yonlendirme", [])
    H.append("<section id='yonlendirme'><h2>Daha iyi sonuç için yapabilecekleriniz</h2>")
    if yon:
        H.append("<div class='zaman'>" + "".join(f"<div class='adim'><b>{E(y['baslik'])}</b>{y['aciklama']}</div>" for y in yon) + "</div>")
    H.append("</section>")
    # Galeri
    kats = ["Tümü"] + [k for k in KAT_SIRA if any(g["kategori"] == k for g in imgs)]
    H.append("<section id='galeri'><h2>Analiz görselleri</h2><p>Analiz sırasında üretilen tüm görseller. Açıklamalı olanlar "
             "analiz kaydından, diğerleri dosya adından otomatik açıklanmıştır. Izgara etiketleri tarama pikseli "
             f"(1 mm = {D.scan['s']} px).</p><div class='arac'>"
             + "".join(f"<button data-k='{E(k)}' class='{'aktif' if k == 'Tümü' else ''}' onclick='kat(this)'>{E(k)}</button>" for k in kats)
             + "<input id='ara' placeholder='Ara: ped, köprü, gölge, kuyruk…' oninput='filtrele()'><span id='sayi'></span></div><div class='galeri'>")
    for i, g in enumerate(imgs):
        H.append(f"<div class='gk' data-i='{i}'><div class='res' style=\"background-image:url('{rel}/{g['stem']}_k.jpg')\" onclick='goster({i})'></div>"
                 f"<div class='m'><span class='k'>{E(g['kategori'])}</span><b>{E(g['baslik'])}</b>{g['aciklama']}"
                 + (f"<div class='o'>Ölçüm: {E(g['olcum'])}</div>" if g["olcum"] else "")
                 + (f"<div><a href='#{g['karar']}'>→ {g['karar']}</a></div>" if g["karar"] else "")
                 + f"<div class='dosya'>{E(g['key'])} · {g['orj'][0]}×{g['orj'][1]} px</div></div></div>")
    H.append("</div></section>")
    # Çıktılar
    H.append("<section id='ciktilar'><h2>Çıktılar ve CorelDRAW</h2>" + _tbl(["Dosya", "Amaç"], [(f"<code>{E(a)}</code>", E(b)) for a, b in X["files"]])
             + (f"<p><b>Katmanlar:</b> {E(', '.join(X['layers']))}</p>" if X["layers"] else "")
             + "<h3>CorelDRAW'da kullanım</h3><ul>" + "".join(f"<li>{x}</li>" for x in CORELDRAW) + "</ul></section>")
    # Ek
    H.append("<section id='ek'><h2>Ek: parametreler</h2>" + _tbl(["Alan", "Değer"], [
        ("Kaynak", E(f"{c['pdf']} sayfa {c['sayfa'] + 1}")), ("Kırpım (tarama px)", E(str(c["kirpim_px"]))),
        ("Eğiklik düzeltmesi", f"{c['aci_derece']}°"), ("Ölçek", f"{D.scan['s']} px/mm"), ("Parça tipi", E(c["tip"])),
        ("Tasarım dosyası", f"<code>parts/{E(c.get('tasarim_modulu', ''))}.py</code>"),
        ("Yeniden üretim", f"<code>python .devin/skills/fpc-vektor/scripts/fpc.py all {E(X['ad'])}</code>")]) + "</section>")
    H.append("</main><div id='lb'><span class='kapat' onclick='kapat()'>×</span><span class='ok-btn sol' onclick='ileri(-1)'>‹</span>"
             "<span class='ok-btn sag' onclick='ileri(1)'>›</span><div class='alan'><img id='lbimg'></div><div class='alt' id='lbalt'></div></div>")
    H.append(f"<script>window.GORSELLER={json.dumps(js_data, ensure_ascii=False)};{JS}</script></body></html>")
    return "\n".join(H)


def _thumb(key, gidx, imgs, rel, h=110):
    if key not in gidx:
        return ""
    i = gidx[key]
    g = imgs[i]
    return f"<img src='{rel}/{g['stem']}_k.jpg' style='height:{h}px' title='{E(g['baslik'])}' onclick='goster({i})'>"


# ------------------------------------------------------------------ Markdown
def to_md(X, imgs, rel):
    c, R, A, M, D = X["c"], X["R"], X["A"], X["M"], X["D"]
    L = [f"# {D.title}", "", f"*{datetime.datetime.now():%d.%m.%Y %H:%M} — fpc-vektor skill · etkileşimli sürüm: `{X['P']}_rapor.html`*", ""]
    L += [f"**Kabul:** {'GEÇTİ' if M['gecti'] else 'KALDI'} · **Belirsiz rota:** {len(D.check)} · "
          f"**Kontrol maddesi:** {len(X['kl'])} · **Karar noktası:** {len(A.get('karar_noktalari', []))}", ""]
    if R.get("ozet"):
        L += ["## Özet", "", R["ozet"], ""]
    if A.get("surec"):
        L += ["## Analiz süreci", ""] + [f"{i}. **{s['baslik']}** — {_txt(s['aciklama'])}" for i, s in enumerate(A["surec"], 1)] + [""]
    if A.get("bulgular"):
        L += ["## Bulgular", ""] + [f"- {_txt(b)}" for b in A["bulgular"]] + [""]
    if A.get("karar_noktalari"):
        L += ["## Karar noktaları", ""]
        for i, k in enumerate(A["karar_noktalari"], 1):
            L += [f"### K{i}. {k['baslik']}", ""]
            L += [f"- Seçenek: {s}" for s in k.get("secenekler", [])]
            L += [f"- **Seçilen:** {_txt(k['secilen'])}"] + ([f"- Gerekçe: {_txt(k['gerekce'])}"] if k.get("gerekce") else []) \
                + ([f"- Risk: {_txt(k['risk'])}"] if k.get("risk") else [])
            L += [f"- Kanıt: " + ", ".join(f"[{x}]({rel}/{x.replace('/', '_')[:-4]}.jpg)" for x in k.get("kanit", []))] if k.get("kanit") else []
            L.append("")
    L += ["## Ölçüler", "", "| Ölçü | Değer | Not |", "|---|---|---|"] + [f"| {a} | {b} | {n} |" for a, b, n in list(R.get("olculer", [])) + X["auto"]]
    L += ["", "| Eleman | Adet |", "|---|---|"] + [f"| {a} | {b} |" for a, b in X["counts"]]
    if R.get("varsayimlar"):
        L += ["", "### Varsayımlar", ""] + [f"- {v}" for v in R["varsayimlar"]]
    L += ["", "## Doğrulama", "", "| Metrik | Değer | Eşik | Sonuç |", "|---|---|---|---|"]
    L += [f"| {a} | {b} | {t} | {'—' if ok is None else ('✔' if ok else '✘')} |" for a, b, t, ok in metric_rows(M)]
    if R.get("pin_eslemesi"):
        L += ["", "## Pin eşlemesi", "", "| Pin | Bağlantı |", "|---|---|"] + [f"| {a} | {b} |" for a, b in R["pin_eslemesi"]]
    if X["kl"]:
        L += ["", "## Fiziksel kontrol", ""] + [f"- [ ] {v}" for v in X["kl"]]
    if A.get("kullanici_yonlendirme"):
        L += ["", "## Daha iyi sonuç için", ""] + [f"- **{y['baslik']}:** {_txt(y['aciklama'])}" for y in A["kullanici_yonlendirme"]]
    L += ["", "## Analiz görselleri", ""]
    for g in imgs:
        L += [f"**[{g['kategori']}] {g['baslik']}** — `{g['key']}`  ", _txt(g["aciklama"]) + (f" *Ölçüm: {g['olcum']}*" if g["olcum"] else ""),
              "", f"![{g['baslik']}]({rel}/{g['stem']}_k.jpg)", ""]
    L += ["## Çıktılar", ""] + [f"- `{a}` — {b}" for a, b in X["files"]]
    return "\n".join(L)


def _txt(s):
    import re
    return re.sub(r"<[^>]+>", "", s or "")


# ------------------------------------------------------------------ PDF
def to_pdf_html(X, imgs):
    """PDF için sade HTML (Story): açıklamalı görseller + doğrulama; diğer görseller liste."""
    c, R, A, M, D = X["c"], X["R"], X["A"], X["M"], X["D"]
    css = ("body{font-family:sans-serif;font-size:9.5pt;} h1{font-size:16pt;color:#1f4e79;} h2{font-size:12.5pt;color:#1f4e79;"
           "border-bottom:1px solid #999;margin-top:14pt;} h3{font-size:10.5pt;} td,th{border:1px solid #bbb;padding:2pt 4pt;font-size:8.5pt;}"
           "th{background:#e8eef5;} .k{color:#2e75b6;font-weight:bold;} .s{color:#1a7f37;}")
    H = [f"<html><head><style>{css}</style></head><body><h1>{E(D.title)}</h1>",
         f"<p>{datetime.datetime.now():%d.%m.%Y %H:%M} — fpc-vektor skill. Kabul: <b>{'GEÇTİ' if M['gecti'] else 'KALDI'}</b>; "
         f"belirsiz rota {len(D.check)}; kontrol maddesi {len(X['kl'])}. Etkileşimli sürüm: {X['P']}_rapor.html</p>"]
    if R.get("ozet"):
        H.append(f"<h2>Özet</h2><p>{E(R['ozet'])}</p>")
    if A.get("surec"):
        H.append("<h2>Analiz süreci</h2><ol>" + "".join(f"<li><b>{E(s['baslik'])}</b> — {s['aciklama']}</li>" for s in A["surec"]) + "</ol>")
    if A.get("bulgular"):
        H.append("<h2>Bulgular</h2><ul>" + "".join(f"<li>{b}</li>" for b in A["bulgular"]) + "</ul>")
    if A.get("karar_noktalari"):
        H.append("<h2>Karar noktaları</h2>")
        for i, k in enumerate(A["karar_noktalari"], 1):
            H.append(f"<h3>K{i}. {E(k['baslik'])}</h3>" + ("<ul>" + "".join(f"<li>{E(s)}</li>" for s in k.get("secenekler", [])) + "</ul>" if k.get("secenekler") else "")
                     + f"<p class='s'><b>Seçilen:</b> {k['secilen']}</p>" + (f"<p><b>Gerekçe:</b> {k['gerekce']}</p>" if k.get("gerekce") else "")
                     + (f"<p><b>Risk:</b> {k['risk']}</p>" if k.get("risk") else ""))
    H.append("<h2>Ölçüler</h2><table><tr><th>Ölçü</th><th>Değer</th><th>Not</th></tr>"
             + "".join(f"<tr><td>{E(str(a))}</td><td>{E(str(b))}</td><td>{E(str(n))}</td></tr>" for a, b, n in list(R.get("olculer", [])) + X["auto"]) + "</table>")
    H.append("<h2>Doğrulama</h2><table><tr><th>Metrik</th><th>Değer</th><th>Eşik</th><th>Sonuç</th></tr>"
             + "".join(f"<tr><td>{E(a)}</td><td>{b}</td><td>{E(t)}</td><td>{'—' if ok is None else ('✔' if ok else '✘')}</td></tr>" for a, b, t, ok in metric_rows(M)) + "</table>")
    if R.get("pin_eslemesi"):
        H.append("<h2>Pin eşlemesi</h2><table>" + "".join(f"<tr><td>{E(a)}</td><td>{E(b)}</td></tr>" for a, b in R["pin_eslemesi"]) + "</table>")
    if X["kl"]:
        H.append("<h2>Fiziksel kontrol</h2><ul>" + "".join(f"<li>☐ {E(v)}</li>" for v in X["kl"]) + "</ul>")
    if A.get("kullanici_yonlendirme"):
        H.append("<h2>Daha iyi sonuç için</h2><ul>" + "".join(f"<li><b>{E(y['baslik'])}:</b> {y['aciklama']}</li>" for y in A["kullanici_yonlendirme"]) + "</ul>")
    H.append(f"<h2>Analiz görselleri</h2><p>{_txt(LEJANT)}</p>")
    sec = [g for g in imgs if g["aciklamali"] or g["kategori"] == "Doğrulama"]
    for g in sec:
        ar = g["h"] / max(g["w"], 1)
        w = int(min(520, 560 / ar))
        H.append(f"<h3><span class='k'>[{E(g['kategori'])}]</span> {E(g['baslik'])}</h3><p>{g['aciklama']}"
                 + (f" <span class='s'>Ölçüm: {E(g['olcum'])}</span>" if g["olcum"] else "") + f" <i>({E(g['key'])})</i></p>"
                 + f"<img src='{g['stem']}.jpg' width='{w}'/>")
    diger = [g for g in imgs if g not in sec]
    if diger:
        H.append("<h3>Diğer çalışma görselleri (HTML raporda galeride)</h3><p>" + ", ".join(E(g["key"]) for g in diger) + "</p>")
    H.append("</body></html>")
    return "\n".join(H)


def write_pdf(html_text, path, imgdir):
    story = pymupdf.Story(html=html_text, archive=pymupdf.Archive(imgdir))
    writer = pymupdf.DocumentWriter(path)
    rect = pymupdf.paper_rect("a4")
    where = rect + (36, 36, -36, -36)
    more = True
    while more:
        dev = writer.begin_page(rect)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()


def run(ad, D=None, M=None):
    import verify
    D = D or verify.load_design(ad)
    if M is None:
        mp = cfg.work(ad, "metrikler.json")
        M = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else verify.verify(ad, D)
    X = collect(ad, D, M)
    P = X["P"]
    rel = f"{P}_rapor_gorseller"
    imgdir = os.path.join("output", rel)
    imgs = collect_images(ad, X["A"], imgdir)
    open(f"output/{P}_rapor.html", "w", encoding="utf-8").write(to_html(X, imgs, rel))
    open(f"output/{P}_rapor.md", "w", encoding="utf-8").write(to_md(X, imgs, rel))
    try:
        write_pdf(to_pdf_html(X, imgs), f"output/{P}_rapor.pdf", imgdir)
    except Exception as e:  # dosya açık olabilir
        write_pdf(to_pdf_html(X, imgs), f"output/{P}_rapor_yeni.pdf", imgdir)
        print(f"UYARI: rapor PDF'i kilitli ({e.__class__.__name__}); _rapor_yeni.pdf yazildi")
    na = sum(g["aciklamali"] for g in imgs)
    print(f"rapor: output/{P}_rapor.html / .md / .pdf  ({len(imgs)} gorsel, {na} aciklamali, "
          f"{len(X['A'].get('karar_noktalari', []))} karar noktasi)")


if __name__ == "__main__":
    run(sys.argv[1])
