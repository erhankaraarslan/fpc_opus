"""Parça yapılandırması (parts/<ad>.json) yükleyici ve ortak yollar.

Tüm betikler proje kökünden (cwd) çalıştırılır:
  parts/<ad>.json        parça yapılandırması
  parts/<ad>_design.py   parametrik tasarım modülü (build() -> fpcvec.Design)
  work/<ad>/             ara dosyalar (deskew görüntü, maskeler, kontrol görselleri)
  output/                çizim ve rapor çıktıları
"""
import json
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
if os.path.abspath("parts") not in sys.path:
    sys.path.insert(0, os.path.abspath("parts"))

DEFAULTS = {
    "pdf": "docs/K.pdf",
    "sayfa": 0,
    "goruntu_indeksi": 0,
    "aci_derece": 0.0,
    "olcek_px_mm": 47.17,
    "tip": "tus",
    "oval_kutulari": [],
    "rapor_kirpimlari": {},
}


def load(ad):
    p = f"parts/{ad}.json"
    if not os.path.exists(p):
        raise SystemExit(f"Yapilandirma yok: {p}  (sablon: .devin/skills/fpc-vektor/templates/parca.json)")
    c = dict(DEFAULTS)
    c.update(json.load(open(p, encoding="utf-8")))
    c["ad"] = ad
    return c


def work(ad, *parts):
    d = os.path.join("work", ad)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, *parts)


def deskew_png(ad):
    return work(ad, f"{ad}_deskew.png")
