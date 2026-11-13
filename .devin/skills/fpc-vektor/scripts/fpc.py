"""FPC vektörleştirme iş akışı için tek giriş noktası.

Proje kökünden çalıştırın:
  python .devin/skills/fpc-vektor/scripts/fpc.py <komut> <ad>

Komutlar:
  skew    <ad>   kırpımda eğiklik ölçer (parts/<ad>.json -> aci_derece önerisi)
  prep    <ad>   kırp + eğiklik düzelt -> work/<ad>/<ad>_deskew.png
  segment <ad>   maskeler (tip=tus -> segment.py, tip=led -> segment_led.py) + gölge modeli (golge.py)
  golge   <ad>   yalnız gölge modeli: m_golge.npy, golge.json, golge_haritasi.png
  ovals   <ad>   oval pencereleri ölç (tip=tus, oval_kutulari gerekli)
  build   <ad>   parts/<ad>_design.py build() -> output/<AD>_{duzenlenebilir,uretim,kontrol_taramali}.svg + _uretim.pdf
  check   <ad>   taramaya bakmadan ağ (netlist) + tasarım tutarlılık kontrolleri (hızlı; rota düzeltirken)
  verify  <ad>   taramaya bindir: alt-piksel kenar metrikleri + ağ/tutarlılık + kabul (work/<ad>/metrikler.json)
  report  <ad>   output/<AD>_rapor.{md,html,pdf}
  all     <ad>   prep -> segment -> build -> verify -> report
  altin   <ad>   mevcut doğrulama sonucunu onaylı durum olarak kaydet (parts/<ad>_altin.json)
  regress <ad|all>  verify + altınla karşılaştır (gerileme / ağ değişikliği / yeni HATA -> çıkış 1)
  kayit   <ad>   arka yüz taramasını ön deskew görüntüsüne çakıştır (parts/<ad>.json "arka") -> <ad>_arka.png
  refine_dene <ad>  rotalı (LED) parçada maske ve profil (yoğunluk kenarı) refine yöntemlerini karşılaştırır
  oneri   <ad>   verify ölçümlerinden düzeltme önerileri (hizalama, dielektrik kayması, genişlik, eleman)
  olcek   <ad> x0 y0 x1 y1 [adim_mm] [x|y]   periyodik yapıdan alt-piksel adım / ölçek
  bukulme <ad> [adim_px]   film bükülmesi kestirimi -> work/<ad>/bukulme_onerisi.json
  topoloji <ad> [y0 y1]  otomatik rota önerisi (aday segment + MILP + graf) -> work/<ad>/rota_onerisi.py
  ogren egit <ad,..|all> / ogren uygula <ad> / ogren dene [ad,..]   öğrenen piksel sınıflandırıcı (Faz 3)
  selftest       araçların sentetik doğruluk testleri (ad gerekmez)
"""
import sys

import cfg  # noqa: F401  (yolları ayarlar)


def build(ad):
    import os

    import fpcvec as fv
    from verify import load_design

    D = load_design(ad)
    os.makedirs("output", exist_ok=True)
    P = ad.upper()
    fv.write_svg_editable(D, f"output/{P}_duzenlenebilir.svg")
    fv.write_svg_production(D, f"output/{P}_uretim.svg")
    fv.write_svg_check(D, f"output/{P}_kontrol_taramali.svg", cfg.deskew_png(ad))
    fv.write_pdf(D, f"output/{P}_uretim.pdf")
    check_outputs(ad)
    print(f"{P}: hat {len(D.traces)}, gumus dikdortgen {len(D.silver_rects)}, delik {len(D.holes)}, "
          f"LED {len(D.leds)}, kopru {len(D.bridges)}, yama {len(D.diel_polys)}, kontrol {len(D.check)}")
    return D


def check_outputs(ad):
    """Çıktıların açılabildiğini, ölçülerin ve katmanların doğru olduğunu denetler."""
    import xml.dom.minidom as md

    import pymupdf

    P = ad.upper()
    for n in ("duzenlenebilir", "uretim", "kontrol_taramali"):
        p = f"output/{P}_{n}.svg"
        md.parse(p)
        d = pymupdf.open(p)
        assert d.page_count == 1, p
    import os
    pp = f"output/{P}_uretim_yeni.pdf" if os.path.exists(f"output/{P}_uretim_yeni.pdf") else f"output/{P}_uretim.pdf"
    d = pymupdf.open(pp)
    names = [v["name"] for v in d.get_ocgs().values()]
    assert any(n.startswith("Kesim") for n in names) and any(n.startswith("Gumus") for n in names), names
    print("cikti kontrolu tamam; PDF katmanlari:", ", ".join(names))


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        import selftest
        raise SystemExit(0 if selftest.main() else 1)
    if len(sys.argv) >= 3 and sys.argv[1] == "ogren":
        import ogren
        alt, lst = sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "all"
        parcalar = ogren.tum_parcalar() if lst == "all" else lst.split(",")
        {"egit": lambda: ogren.egit(parcalar), "uygula": lambda: ogren.uygula(lst),
         "dene": lambda: ogren.dene(parcalar)}[alt]()
        raise SystemExit(0)
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    cmd, ad = sys.argv[1], sys.argv[2]
    if cmd == "regress":
        import regress
        import verify
        ok = True
        for a in (regress.parcalar() if ad == "all" else [ad]):
            M = verify.verify(a)
            ok &= regress.karsilastir(a, M)
        raise SystemExit(0 if ok else 1)
    c = cfg.load(ad)
    if cmd == "check":
        import verify
        verify.check(ad)
    elif cmd == "altin":
        import regress
        regress.altin(ad)
    elif cmd == "topoloji":
        import topoloji
        topoloji.run(ad, *(int(v) for v in sys.argv[3:5]))
    elif cmd == "kayit":
        import kayit
        kayit.run(ad)
    elif cmd == "refine_dene":
        import verify
        verify.refine_dene(ad)
    elif cmd == "oneri":
        import oneri
        oneri.yaz(oneri.uret(ad))
    elif cmd == "olcek":
        import kalibre
        a = sys.argv[3:]
        kalibre.olcek(ad, *map(int, a[:4]), float(a[4]) if len(a) > 4 else 1.0, a[5] if len(a) > 5 else "x")
    elif cmd == "bukulme":
        import kalibre
        kalibre.bukulme(ad, int(sys.argv[3]) if len(sys.argv) > 3 else 300)
    elif cmd == "skew":
        import skew
        from prep import crop
        n, w, m = skew.measure(crop(c))
        print(f"cizgi={n} agirlikli={w:.3f} medyan={m:.3f} -> onerilen aci_derece={w:.2f}")
    elif cmd == "prep":
        import prep
        prep.run(ad)
    elif cmd == "segment":
        import golge
        import segment
        import segment_led
        golge.run(ad)  # önce gölge: tuş tipi referans maskesi gölgeyi dışlar
        (segment_led if c["tip"] == "led" else segment).run(ad)
    elif cmd == "golge":
        import golge
        golge.run(ad)
    elif cmd == "ovals":
        import ovals
        ovals.run(ad)
    elif cmd == "build":
        build(ad)
    elif cmd == "verify":
        import verify
        verify.print_metrics(verify.verify(ad))
    elif cmd == "report":
        import report
        report.run(ad)
    elif cmd == "all":
        import golge
        import prep
        import report
        import segment
        import segment_led
        import verify
        prep.run(ad)
        golge.run(ad)
        (segment_led if c["tip"] == "led" else segment).run(ad)
        D = build(ad)
        M = verify.verify(ad, D)
        verify.print_metrics(M)
        report.run(ad, D, M)
    else:
        print(__doc__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
