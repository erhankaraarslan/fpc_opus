"""Otomatik kalibrasyon: periyodik yapıdan ölçek (Fourier), film bükülmesi kestirimi.

Kullanım (fpc.py üzerinden):
  fpc.py olcek <ad> x0 y0 x1 y1 [adim_mm=1.0] [yon=x]
        ROI içindeki periyodik yapının (konnektör kontakları, tarak parmakları) adımını alt-piksel bulur.
        yon=x: sütunlar boyunca (dikey hatlar, yatay adım); yon=y: satırlar boyunca. -> px/mm = adım_px / adim_mm
  fpc.py bukulme <ad> [adim_px=300]
        Döndürülmüş (bükülme düzeltmesiz) kırpımda uzun dikey yapıların yanal kaymasını dx(y) olarak kestirir;
        parts/<ad>.json "bukulme" için {xc, dx_noktalar} önerisi + kalan doğrusal eğim (açı düzeltmesi) verir.
Yöntem (ölçek): profil (L ve T kanallarından varyansı büyük olan) → doğrusal eğilim çıkarılır → Hann pencere →
  nominal adımın ±%15'inde DTFT genliği ince ızgarada taranır, tepe parabolle inceltilir (çözünürlük ≈ 0.001 px).
Yöntem (bükülme): 200 px yüksekliğinde, 100 px örtüşmeli bantlarda yatay gradyan profili; komşu bantlar arası
  alt-piksel çapraz korelasyon kaymaları toplanır (dx(y)), aykırılar medyanla bastırılır, yumuşatılır.
"""
import json
import math
import sys

import cv2
import numpy as np

import cfg


def _kanal(im, x0, y0, x1, y1, yon):
    f = im[y0:y1, x0:x1].astype(np.float32)
    ch = [f.mean(2), f[:, :, 1] - f[:, :, 2]]
    pr = [c.mean(0) if yon == "x" else c.mean(1) for c in ch]
    return max(pr, key=lambda p: np.var(p - cv2.blur(p.reshape(1, -1), (101, 1)).ravel()))


def adim_bul(p, nominal_px, aralik=0.08):
    """1-B profilde nominal_px civarındaki periyot (px).
    1) DTFT ile kaba periyot + faz, 2) her beklenen hat konumunda alt-piksel tepe (parabol),
    3) merkez = x0 + k·P doğrusal fiti (boş/dummy pozisyonlar indeksle atlanır).
    Dönüş: (periyot px, kullanılan hat sayısı, fit artığı RMS px)"""
    p = np.asarray(p, float)
    x = np.arange(len(p))
    p = p - cv2.blur(p.reshape(1, -1), (int(nominal_px * 2) | 1, 1), borderType=cv2.BORDER_REFLECT).ravel()
    P = np.linspace(nominal_px * (1 - aralik), nominal_px * (1 + aralik), 1501)
    E = np.exp(-2j * np.pi * x[None, :] / P[:, None])
    z = E @ p
    i = int(np.argmax(np.abs(z)))
    per, ph = P[i], np.angle(z[i])
    x0 = (-ph / (2 * np.pi)) * per % per  # z = Σp·e^{-iωx}, p ≈ cos(ωx − θ) -> angle(z) = −θ; tepe x = θ/ω
    ps = cv2.GaussianBlur(p.reshape(1, -1), (0, 0), 1.5).ravel()
    xs = np.arange(len(ps), dtype=float)
    sol = np.array([x0, per])
    for tur in range(3):  # pencereler her turda fit edilen merkezlere yeniden ortalanır (kesik plato yanlılığı)
        ks, cs, amp = [], [], []
        for k in range(-1, int(len(p) / per) + 2):
            xc = sol[0] + k * sol[1]
            a, b = xc - sol[1] / 2, xc + sol[1] / 2
            if a < 0 or b > len(p) - 1:
                continue
            m = (xs >= a) & (xs < b)
            seg = ps[m]
            w = np.clip(seg - 0.5 * (seg.max() + seg.min()), 0, None)  # yarı-yükseklik üstü ağırlıklı merkez
            if w.sum() <= 0:
                continue
            ks.append(k)
            cs.append(float((w * xs[m]).sum() / w.sum()))
            amp.append(float(seg.max() - seg.min()))
        if len(cs) < 3:
            return float(per), len(cs), float("nan")
        ks, cs, amp = np.array(ks), np.array(cs), np.array(amp)
        keep = amp > 0.35 * np.median(amp)
        for _ in range(3):
            A = np.c_[np.ones(keep.sum()), ks[keep]]
            sol = np.linalg.lstsq(A, cs[keep], rcond=None)[0]
            r = cs - (sol[0] + sol[1] * ks)
            mad = np.median(np.abs(r[keep] - np.median(r[keep])))
            keep &= np.abs(r) < max(3 * 1.4826 * mad, 1.0)  # MAD: tek aykırı (kısmi/dummy pozisyon) eşiği şişirmez
    return float(sol[1]), int(keep.sum()), float(np.sqrt(np.mean(r[keep] ** 2)))


def olcek(ad, x0, y0, x1, y1, adim_mm=1.0, yon="x"):
    c = cfg.load(ad)
    im = cv2.imread(cfg.deskew_png(ad))
    s0 = c.get("olcek_px_mm", 47.17)
    per, n, rms = adim_bul(_kanal(im, x0, y0, x1, y1, yon), s0 * adim_mm)
    s = per / adim_mm
    sig = rms / max(n, 1) ** 1.5 * math.sqrt(12)  # doğrusal fit eğim belirsizliği (yaklaşık)
    print(f"{ad}: adım {per:.3f} ± {sig:.3f} px ({yon} yönü, {n} hat, artık RMS {rms:.2f} px) -> {s:.3f} px/mm "
          f"(yapılandırma {s0}, fark %{100 * (s - s0) / s0:+.2f}); {s0} px/mm ile adım {per / s0:.4f} mm")
    if n < 5 or rms > 1.0:
        print("  UYARI: az hat / büyük artık; ROI'yi yalnız periyodik bölgeye daraltın")
    return dict(adim_px=per, px_mm=s, hat=n, rms_px=rms)


def _bant_profil(g, y0, y1):
    return g[y0:y1].mean(0)


def kayma_1d(a, b, maks=12):
    """b'nin a'ya göre alt-piksel yanal kayması (px)."""
    a = (a - a.mean()) / (a.std() + 1e-6)
    b = (b - b.mean()) / (b.std() + 1e-6)
    ks = np.arange(-maks, maks + 1)
    n = len(a)
    cc = np.array([np.dot(a[max(0, -k):n - max(0, k)], b[max(0, k):n - max(0, -k)]) / (n - abs(k)) for k in ks])
    i = int(np.argmax(cc))
    if 0 < i < len(cc) - 1:
        d = 0.5 * (cc[i - 1] - cc[i + 1]) / (cc[i - 1] - 2 * cc[i] + cc[i + 1])
    else:
        d = 0.0
    return float(ks[i] + d), float(cc[i])


def bukulme_kestir(im, adim=100, bant=200, maks=12):
    L = im.astype(np.float32).mean(2)
    g = np.abs(cv2.Sobel(cv2.GaussianBlur(L, (0, 0), 1.5), cv2.CV_32F, 1, 0, ksize=3))
    H = g.shape[0]
    ys = list(range(0, H - bant, adim))
    prof = [_bant_profil(g, y, y + bant) for y in ys]
    dd, cc = [0.0], [1.0]
    for a, b in zip(prof[:-1], prof[1:]):
        d, c_ = kayma_1d(a, b, maks)
        dd.append(d)
        cc.append(c_)
    dd, cc = np.array(dd), np.array(cc)
    bad = cc < 0.5
    med = np.median(dd[~bad]) if (~bad).any() else 0
    dd[bad] = med
    x = np.cumsum(dd)  # yapının yanal konumu (bant merkezi y'de)
    yc = np.array(ys) + bant / 2
    return yc, x, cc


def bukulme(ad, adim_px=300):
    import prep
    c = cfg.load(ad)
    im = prep.crop(c)
    h, w = im.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), float(c["aci_derece"]), 1.0)
    im = cv2.warpAffine(im, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    yc, x, cc = bukulme_kestir(im)
    k = np.polyfit(yc, x, 1)
    resid = x - np.polyval(k, yc)
    aci = math.degrees(math.atan(k[0]))
    ref = np.interp(h * 0.75, yc, x)  # kuyruk (konnektör, kalibrasyon bölgesi) civarında dx = 0
    dx = x - ref
    pts = [[int(y), round(float(np.interp(y, yc, dx)), 2)] for y in range(0, h, adim_px)] + [[h - 1, round(float(dx[-1]), 2)]]
    out = dict(xc=int(w / 2), dx_noktalar=pts, kalan_egim_derece=round(aci, 4),
               dogrusal_olmayan_px=round(float(np.ptp(resid)), 2), guvenilmez_bant=int((cc < 0.5).sum()))
    json.dump(out, open(cfg.work(ad, "bukulme_onerisi.json"), "w"), indent=0)
    print(f"{ad}: kalan eğim {aci:+.4f}° (aci_derece'ye {'+' if aci > 0 else ''}{-aci:.3f} ekle -> pozitif = saat yönünün tersine), "
          f"doğrusal olmayan bükülme genliği {np.ptp(resid):.1f} px, güvenilmez bant {out['guvenilmez_bant']}")
    print(f"  öneri -> work/{ad}/bukulme_onerisi.json  (parts/{ad}.json \"bukulme\"; genlik < 3 px ise gerek yok)")
    if c.get("bukulme"):
        p = np.array(c["bukulme"]["dx_noktalar"], float)
        mine = np.interp(p[:, 0], yc, dx)
        a = p[:, 1] - p[:, 1].mean()
        b = mine - mine.mean()
        print(f"  mevcut 'bukulme' ile karşılaştırma (sabit fark çıkarılmış): RMS fark {np.sqrt(np.mean((a - b) ** 2)):.2f} px, "
              f"korelasyon {np.corrcoef(a, b)[0, 1]:.3f}")
    return out


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "olcek":
        olcek(a[2], *map(int, a[3:7]), *(float(a[7]),) if len(a) > 7 else (), *(a[8:9]))
    else:
        bukulme(a[2], *(int(v) for v in a[3:4]))
