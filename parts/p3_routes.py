"""P3 kaba hat rotaları (deskew px). refine.py ile m_dark maskesindeki merkez çizgisine oturtulur.

Okuma: work/p3/_hp.png (yüksek geçiren) ızgaralı kırpımlar + m_dark segment listesi + yama içi renk
profilleri (work/p3/_patchcols.py). Yamalarda hangi hattın üstten (köprü) geçtiği tasarımda renkten
otomatik seçilir; burada yalnızca hatların izlediği yol verilir.
flag=True: taramadan kesin okunamayan (bulanık / leke / uç boşluğu belirsiz) ve yorumlanan rotalar.
Kuyruk pozisyonları (px): TX[i] = 964.3 + (i - 5) * 47.17   (i = 0..10, 1.0 mm adım)
"""

TX = [964.3 + (i - 5) * 47.17 for i in range(11)]
TAIL_Y = 5900  # kuyruk dielektriğinin başladığı / düz kontak hatlarının başladığı seviye

# LED site merkezleri (yeşil çip + (3, 5) px) ve ped uçları (site ± 95 px)
LED = {"L1": (335, 1584), "L2": (336, 2177), "L3": (335, 2773), "L4": (334, 3371), "L5": (340, 4284),
       "L6": (337, 4882), "L7": (338, 5483), "L8": (336, 6083),
       "R1": (1591, 1575), "R2": (1593, 2177), "R3": (1592, 2773), "R4": (1594, 3376), "R5": (1600, 4281),
       "R6": (1595, 4877), "R7": (1594, 5479), "R8": (1595, 6080),
       "C1": (1005, 2322), "B1": (703, 3048), "B2": (1010, 3050), "B3": (1311, 3051)}
PE = 95


def top(n):
    x, y = LED[n]
    return (x, y - PE)


def bot(n):
    x, y = LED[n]
    return (x, y + PE)


def tail(i):
    return (TX[i], TAIL_Y)


XL, XNA, XNB, XR = 202, 251, 1680, 1728     # sol dış / sol iç / sağ iç / sağ dış dikeyler
YT = 1398                                   # üst yatay

ROUTES = [
    # --- R1 ortak: üst yatay + sol dış dikey + sağ üst iniş (R2 üst ped) ---
    dict(name="R1_ortak", pts=[(XL, 6300), (XL, YT), (1692, YT), (1692, 1830), (1590, 1932), top("R2")]),
    dict(name="L1_ust", pts=[(333, YT), top("L1")]),
    dict(name="R1_ust", pts=[(1590, YT), top("R1")]),
    # --- X ağı: L1 alt, L2 üst, L3 alt, R3 alt, R4 üst -> poz 6 ---
    dict(name="X_hat", pts=[(222, 2000), (1120, 2000), (1120, 3676), (1013, 3676), (1013, 5880), tail(6)], raw_from=4,
         flag=True),
    dict(name="L1_alt", pts=[bot("L1"), (333, 2000)]),
    dict(name="L2_ust", pts=[(333, 2000), top("L2")]),
    dict(name="X_L3", pts=[(457, 2000), (457, 2915), (333, 2915), bot("L3")]),
    dict(name="X_R3R4", pts=[(1120, 3200), (1592, 3200)]),
    dict(name="R3_alt", pts=[bot("R3"), (1592, 3200)]),
    dict(name="R4_ust", pts=[(1592, 3200), top("R4")]),
    # --- Y ağı: L2 alt, L4 alt, R4 alt, V465 -> poz 7 ---
    dict(name="L2_alt", pts=[bot("L2"), (333, 2340), (581, 2340), (581, 3866)]),
    dict(name="Y_hat", pts=[bot("L4"), (334, 3866), (1594, 3866)]),
    dict(name="R4_alt", pts=[bot("R4"), (1594, 3866)]),
    dict(name="Poz7", pts=[(1060, 3866), (1060, 5880), tail(7)], raw_from=1),
    dict(name="V465", pts=[(1060, 4830), (465, 4830), (465, 6140)], flag=True),
    # --- Na (sol iç): L3..L7 üst pedleri -> sol yelpaze -> poz 2 ---
    dict(name="Na", pts=[(XNA, 2630), (XNA, 5740), (752, 5740), (822, 5810), tail(2)], raw_from=3, flag=True),
    dict(name="L3_ust", pts=[(XNA, 2630), (333, 2630), top("L3")]),
    dict(name="L4_ust", pts=[(XNA, 3200), (333, 3200), top("L4")]),
    dict(name="L5_ust", pts=[(XNA, 4140), (337, 4140), top("L5")]),
    dict(name="L6_ust", pts=[(XNA, 4720), (337, 4720), top("L6")]),
    dict(name="L7_ust", pts=[(XNA, 5340), (337, 5340), top("L7")]),
    # --- Nb (sağ iç): R3, R5, R6, R7 üst pedleri -> y5345 -> poz 4 (alt kısım) ---
    dict(name="Nb", pts=[(XNB, 2614), (XNB, 5240), (1620, 5340), (920, 5340), (920, 5880), tail(4)], raw_from=4),
    dict(name="R3_ust", pts=[(XNB, 2614), (1592, 2614), top("R3")]),
    dict(name="R5_ust", pts=[(XNB, 4160), (1600, 4160), top("R5")]),
    dict(name="R6_ust", pts=[(XNB, 4740), (1595, 4740), top("R6")]),
    dict(name="R7_ust", pts=[(1594, 5340), top("R7")]),
    # --- R1 katodu (x1418) + C1 alt -> y4050 -> poz 8 ---
    dict(name="R1_alt", pts=[bot("R1"), (1422, 1997), (1418, 2010), (1418, 4050), (1108, 4050), (1108, 5880), tail(8)],
         raw=True),
    dict(name="C1_alt", pts=[bot("C1"), (1005, 2470), (1418, 2470)]),
    # --- R2 katodu (sağ dış x1728) -> y4100 -> poz 9 ; R6 alt -> poz 9 ---
    dict(name="R2_alt", pts=[bot("R2"), (1593, 2350), (1680, 2437), (1728, 2485), (XR, 4060), (1700, 4100), (1155, 4100),
                             (1155, 5880), tail(9)], raw_from=7),
    dict(name="R6_alt", pts=[bot("R6"), (1595, 5058), (1155, 5058)]),
    # --- Z ağı: C1 üst + B1/B2/B3 üst -> x870 -> çapraz -> x918 (poz 4 üst parçası) ---
    dict(name="Z_C1", pts=[top("C1"), (1003, 2120), (870, 2120), (870, 3110), (936, 3330), (936, 3440), (918, 3480),
                           (918, 5140)], raw_from=3, flag=True),
    dict(name="Z_hat", pts=[(660, 2868), (1300, 2868)]),
    dict(name="B1_ust", pts=[(703, 2868), top("B1")]),
    dict(name="B2_ust", pts=[(1008, 2868), top("B2")]),
    dict(name="B3_ust", pts=[(1300, 2868), (1308, 2868), top("B3")]),
    # --- B2 alt -> x992 -> poz 6 (x967); Z poz 4 üst parçasına devam eder (L6 alt, Q) ---
    dict(name="B2_alt", pts=[bot("B2"), (992, 3180), (992, 3500), (967, 3530), (967, 5880), tail(5)], raw=True, flag=True),
    dict(name="L6_alt", pts=[bot("L6"), (337, 5068), (918, 5068)]),
    # --- Q: sağ dış alt (R8 üst) -> y5110 -> poz 3 ---
    dict(name="Q_R8", pts=[top("R8"), (1612, 5955), (1736, 5555), (1736, 5146), (1700, 5110), (880, 5110),
                           (873, 5117), (873, 5880), tail(3)], raw=True, flag=True),
    # --- L5 / R5 alt: yama altında birleşik, pine ulaşmıyor görünüyor ---
    dict(name="L5R5_alt", pts=[bot("L5"), (340, 4487), (1600, 4487), bot("R5")], raw=True, flag=True),
    # --- B1 alt -> Y (x581) ; B3 alt -> X (y3200) ---
    dict(name="B1_alt", pts=[bot("B1"), (703, 3195), (581, 3195)], raw=True),
    dict(name="B3_alt", pts=[bot("B3"), (1311, 3200)], raw=True),
    # --- L7 / R7 / R8 alt -> y5640 -> poz 10 ---
    dict(name="L7R7_alt", pts=[bot("L7"), (338, 5640), (1594, 5640), bot("R7")], raw=True),
    dict(name="Poz10", pts=[(1204, 5640), (1204, 5880), tail(10)], raw_from=1),
    dict(name="R8_alt", pts=[bot("R8"), (1595, 6262), (1492, 6262), (1492, 5640)], raw=True, flag=True),
    # --- L8 ve sol yelpaze (bulanık bölge) ---
    dict(name="L8_ust", pts=[top("L8"), (336, 5786), (727, 5786), (775, 5834), tail(1)], raw_from=2, flag=True),
    dict(name="R1_sol_alt", pts=[(XL, 6300), (472, 6300), (472, 6140), (528, 6140), (528, 5838), (709, 5838), (728, 5857),
                                 tail(0)], raw=True, flag=True),
    dict(name="L8_alt", pts=[bot("L8"), (336, 6230), (472, 6230)], raw=True, flag=True),
]
