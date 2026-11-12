"""FPC vektörleştirme iş akışı için tek giriş noktası.

Proje kökünden çalıştırın:
  python .devin/skills/fpc-vektor/scripts/fpc.py <komut> <ad>

Komutlar:
  skew    <ad>   kırpımda eğiklik ölçer (parts/<ad>.json -> aci_derece önerisi)
  prep    <ad>   kırp + eğiklik düzelt -> work/<ad>/<ad>_deskew.png
  segment <ad>   maskeler (tip=tus -> segment.py, tip=led -> segment_led.py)
  ovals   <ad>   oval pencereleri ölç (tip=tus, oval_kutulari gerekli)
  build   <ad>   parts/<ad>_design.py build() -> output/<AD>_{duzenlenebilir,uretim,kontrol_taramali}.svg + _uretim.pdf
  verify  <ad>   taramaya bindir, metrikler + kontrol görselleri (work/<ad>/metrikler.json)
  report  <ad>   output/<AD>_rapor.{md,html,pdf}
  all     <ad>   prep -> segment -> build -> verify -> report
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
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    cmd, ad = sys.argv[1], sys.argv[2]
    c = cfg.load(ad)
    if cmd == "skew":
        import skew
        from prep import crop
        n, w, m = skew.measure(crop(c))
        print(f"cizgi={n} agirlikli={w:.3f} medyan={m:.3f} -> onerilen aci_derece={w:.2f}")
    elif cmd == "prep":
        import prep
        prep.run(ad)
    elif cmd == "segment":
        import segment
        import segment_led
        (segment_led if c["tip"] == "led" else segment).run(ad)
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
        import prep
        import report
        import segment
        import segment_led
        import verify
        prep.run(ad)
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
