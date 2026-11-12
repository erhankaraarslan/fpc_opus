"""P1 kaba hat rotaları (deskew px). refine.py ile gerçek merkez çizgisine oturtulur.

flag=True: taramadan kesin okunamayan (kaplama damlası / leke altında kalan) ve yorumlanan
rotalar. Çizimde "Kontrol" katmanında işaretlenir.
Kuyruk pozisyonları (px): TX[i] = 747.3 + i * 47.17   (i = 0..10, 1.0 mm adım)
"""

TX = [747.3 + i * 47.17 for i in range(11)]
TAIL_Y = 3545  # kuyruk dielektriği / düz hatların başladığı seviye


def tail(i):
    return (TX[i], TAIL_Y)


ROUTES = [
    # --- R1: ortak hat (çevre) -> poz 0 ---
    dict(name="R1", pts=[(220, 3700), (220, 1651), (265, 1606), (1700, 1604), (1747, 1651), (1747, 2125),
                         (1714, 2158), (1630, 2158), (1614, 2174), (1614, 2272)]),
    dict(name="R1_alt", pts=[(220, 3690), (220, 3745), (251, 3776), (480, 3776), (516, 3740), (516, 3440),
                             (536, 3420), (688, 3420), (TX[0], 3479), tail(0)], flag=True, raw=True),
    # --- sol sütun ---
    dict(name="L1_ust", pts=[(353, 1606), (353, 1662)]),
    dict(name="L1_alt", pts=[(353, 1845), (353, 1955), (380, 1981), (1418, 1981), (1450, 2013), (1450, 3290),
                             (1250, 3290), (1250, 3383), (TX[8], 3508), tail(8)], raw_from=5),
    dict(name="V578", pts=[(578, 1981), (578, 3114), (366, 3114), (366, 3052)], raw_from=2),
    dict(name="H2818", pts=[(578, 2818), (918, 2818), (918, 3281), (TX[5], 3346), tail(5)], flag=True, raw=True),
    dict(name="L2_ust", pts=[(220, 2204), (354, 2204), (354, 2268)]),
    dict(name="L2_alt", pts=[(354, 2452), (354, 2714), (1750, 2714), (1750, 3740), (1612, 3740), (1612, 3648)]),
    dict(name="V466", pts=[(466, 2714), (466, 3715), (356, 3715), (356, 3648)]),
    dict(name="V1143", pts=[(1143, 2714), (1143, 3342), (TX[6], 3455), tail(6)], raw_from=1),
    dict(name="L3_ust", pts=[(352, 2868), (352, 2824), (270, 2824), (270, 3370), (786, 3370), (TX[2], 3426), tail(2)], raw_from=4),
    dict(name="L4_ust", pts=[(356, 3452), (356, 3370)]),
    dict(name="H3317", pts=[(480, 3317), (884, 3317), (TX[4], 3371), tail(4)], flag=True, raw=True),
    # --- orta ---
    dict(name="T3", pts=[(820, 3079), (820, 2060), (850, 2030), (1680, 2030), (1700, 2050), (1700, 3263)]),
    dict(name="T3_R4L", pts=[(1700, 3263), (1700, 3329), (1612, 3417), (1612, 3458)], flag=True, raw=True),
    dict(name="C1_ust", pts=[(1025, 2342), (1025, 2276), (867, 2276), (867, 3064)]),
    dict(name="C1_alt", pts=[(1025, 2518), (1025, 2559), (1194, 2559)], raw=True),
    dict(name="B1_ust", pts=[(820, 3079), (820, 3104), (720, 3104), (720, 3072)], flag=True, raw=True),
    dict(name="B1_alt", pts=[(720, 3252), (720, 3317)], flag=True, raw=True),
    dict(name="B2_ust", pts=[(1020, 3070), (1020, 3000), (918, 3000)], flag=True, raw=True),
    dict(name="B2_alt", pts=[(1020, 3252), (1020, 3290), (1250, 3290)], flag=True, raw=True),
    dict(name="B3_ust", pts=[(1320, 3075), (1320, 3004), (1196, 3004)], flag=True, raw=True),
    dict(name="B3_alt", pts=[(1320, 3255), (1320, 3290)], flag=True, raw=True),
    # --- sağ sütun ---
    dict(name="R1L_ust", pts=[(1602, 1606), (1602, 1662)]),
    dict(name="R1L_alt", pts=[(1614, 1845), (1614, 2098), (1539, 2173), (1214, 2173), (1194, 2193), (1196, 3360),
                              (TX[7], 3478), tail(7)], raw_from=5),
    dict(name="R2L_alt", pts=[(1614, 2452), (1614, 2724), (1507, 2831), (1507, 3468), (1234, 3468),
                              (TX[9], 3530), tail(9)], raw_from=4),
    dict(name="R3L_ust", pts=[(1611, 2868), (1611, 2860), (1700, 2771)], flag=True, raw=True),
    dict(name="R3L_alt", pts=[(1612, 3048), (1612, 3179), (1450, 3179)], flag=True, raw=True),
]

# Refine edilmeyecek (elle sabit) segmentler: fan çaprazları ölçülen doğrulara göre verildi
FIXED_TAILS = True
