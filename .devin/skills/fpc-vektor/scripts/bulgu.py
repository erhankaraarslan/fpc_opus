"""Kontrol bulguları (ağ, tutarlılık, doğrulama) için ortak yapı.

Bulgu: dict(seviye, kod, id, mesaj, konum, bilinen, gerekce)
  seviye  HATA (kabul kalır) | UYARI (incelenmeli) | BILGI
  id      kararlı kimlik "kod:anahtar" (ör. "pinsiz_ag:LED_L5.alt,LED_R5.alt"); parçalar arası tekrar
          çalıştırmada değişmez, regresyon ve kullanıcı onayı bu kimlikle yapılır
  konum   [x, y] mm (kart koordinatı) veya None
Kullanıcının bilerek kabul ettiği bulgular parts/<ad>.json "kabul_edilen_bulgular": {"<id veya glob>": "gerekçe"}
ile "bilinen" işaretlenir; bilinen HATA kabul kapısını düşürmez ama raporda ayrıca listelenir.
"""
import fnmatch

SEVIYE_SIRA = {"HATA": 0, "UYARI": 1, "BILGI": 2}


def yeni(seviye, kod, anahtar, mesaj, konum=None):
    k = None if konum is None else [round(float(konum[0]), 2), round(float(konum[1]), 2)]
    return dict(seviye=seviye, kod=kod, id=f"{kod}:{anahtar}", mesaj=mesaj, konum=k, bilinen=False, gerekce="")


def kabul_uygula(bulgular, kabul):
    for b in bulgular:
        for pat, ger in (kabul or {}).items():
            if b["id"] == pat or fnmatch.fnmatchcase(b["id"], pat):
                b["bilinen"], b["gerekce"] = True, ger
                break
    return bulgular


def sirala(bulgular):
    return sorted(bulgular, key=lambda b: (SEVIYE_SIRA.get(b["seviye"], 9), b["kod"], b["id"]))


def sayim(bulgular):
    s = {"HATA": 0, "UYARI": 0, "BILGI": 0, "bilinen": 0}
    for b in bulgular:
        if b["bilinen"]:
            s["bilinen"] += 1
        else:
            s[b["seviye"]] += 1
    return s


def ozet_yaz(bulgular, en_cok=40):
    s = sayim(bulgular)
    print(f"Bulgular: HATA {s['HATA']}, UYARI {s['UYARI']}, BILGI {s['BILGI']}, bilinen {s['bilinen']}")
    for b in sirala(bulgular)[:en_cok]:
        if b["seviye"] == "BILGI":
            continue
        k = f" @({b['konum'][0]}, {b['konum'][1]}) mm" if b["konum"] else ""
        print(f"  [{'bilinen ' if b['bilinen'] else ''}{b['seviye']}] {b['id']}: {b['mesaj']}{k}")
