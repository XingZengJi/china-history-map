"""Build curated per-period GeoJSON frames for the China historical map.
Source polygons: historical-basemaps (GPL-3.0). Coastline/rivers: Natural Earth (public domain).
Usage: python3 -I build.py <historical-basemaps/geojson dir> <ne dir> <out dir>
"""
import json, sys, os
from shapely.geometry import shape, box, mapping, Polygon, Point, LineString, MultiPolygon
from shapely.ops import unary_union, polylabel
from shapely.validation import make_valid

SRC, NE, OUT = sys.argv[1:4]
WIN = box(58, 6, 156, 64)          # data clip window
VIEW = box(72, 17, 138, 54)        # label placement window

_cache = {}
def load(src):
    if src not in _cache:
        g = json.load(open(f"{SRC}/world_{src}.geojson"))
        d = {}
        for ft in g["features"]:
            nm = ft["properties"].get("NAME")
            if not nm or not ft["geometry"]:
                continue
            try:
                s = make_valid(shape(ft["geometry"])).intersection(WIN)
            except Exception:
                continue
            if s.is_empty:
                continue
            d.setdefault(nm, []).append(s)
        _cache[src] = {k: polys(unary_union(v)) for k, v in d.items()}
    return _cache[src]

def polys(g):
    """keep only polygonal parts"""
    if g.is_empty:
        return g
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    parts = [x for x in getattr(g, "geoms", []) if x.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(parts) if parts else Polygon()

def get(src, *names):
    d = load(src)
    out = []
    for n in names:
        if n not in d:
            raise KeyError(f"{src}: {n} not found; have {sorted(d)}")
        out.append(d[n])
    return polys(unary_union(out))

# ---------- basemap ----------
land_fc = json.load(open(f"{NE}/land.geojson"))
land_all = make_valid(shape(land_fc["geometry"] if "geometry" in land_fc else land_fc["features"][0]["geometry"]))
land = polys(land_all.intersection(WIN))

def island(lon, lat):
    p = Point(lon, lat)
    for g in land.geoms:
        if g.contains(p):
            return g
    raise RuntimeError("island not found")

TAIWAN = island(121.0, 23.7)
HAINAN = island(109.7, 19.2)
TW_BOX = box(119.9, 21.7, 122.2, 25.5)
HN_BOX = box(108.4, 18.0, 111.3, 20.25)

# hand-drawn schematic zones --------------------------------------------------
XIYU = Polygon([(74.2, 39.6), (76, 41.2), (80, 42.2), (84, 43.2), (87.5, 44.6), (91.5, 44.6),
                (94.8, 43.2), (95.6, 41.2), (93.5, 39.2), (90, 37.6), (85, 36.4), (80, 36.0),
                (76.5, 36.9), (74.6, 38.2)])
# Shu-Han: Hanzhong, Sichuan basin, Nanzhong
SHU = Polygon([(90, 33.4), (104, 33.4), (106, 33.3), (108, 32.7), (109.8, 32.0), (110.3, 31.0),
               (109.5, 29.5), (109.2, 28), (108.5, 26.5), (107.3, 25), (106, 24), (105, 23),
               (104, 22.3), (90, 20)])
def south_of(line, floor=0):
    pts = list(line) + [(line[-1][0], floor), (line[0][0], floor)]
    return Polygon(pts)
WEI_WU = [(60, 31.0), (110.3, 31.0), (111.5, 31.2), (113, 31.2), (114.5, 31.1), (116, 31.0),
          (117.5, 31.4), (118.5, 32.3), (119.5, 32.6), (150, 32.6)]
QINLING_HUAI = [(60, 34.3), (104, 34.3), (106.5, 34.2), (108, 33.9), (110, 33.6), (112, 33.0),
                (113.5, 32.5), (115, 32.4), (117, 32.9), (118.5, 33.4), (120, 34.0), (150, 34.3)]
NE_BULGE = box(125.2, 39.5, 150, 60)   # exaggerated north-east of the 200 BC Han polygon

han200 = get("200", "Han")
shu_g = polys(han200.intersection(SHU))
wu_g = polys(han200.intersection(south_of(WEI_WU)).difference(SHU))
wei_g = polys(han200.difference(SHU).difference(south_of(WEI_WU)))

song1200 = get("1200", "Song Empire")
ssong_g = polys(song1200.intersection(south_of(QINLING_HUAI)))
jin_g = polys(unary_union([song1200.difference(south_of(QINLING_HUAI)), get("1200", "Liao")]))

big1492 = get("1492", "Chagatai Khanate")
moghul_g = polys(big1492.intersection(box(58, 0, 96, 70)))
tatar_g = polys(big1492.intersection(box(96, 0, 120.5, 70)))
jurchen_g = polys(big1492.intersection(box(120.5, 0, 160, 70)))

hanbc200 = polys(get("bc200", "Han Empire").difference(NE_BULGE))
qin_g = polys(unary_union([hanbc200, get("bc200", "Nan-Yue"), get("bc200", "Min-Yue")]))

# ---------- frames ----------
# feature spec: (geometry, st, opts)   st = [[fromYear, polityKey|None, labelOverride?], ...]
def F(geom, *st, **o):
    return (geom, [list(s) for s in st], o)

frames = []
def frame(y0, y1, snap, feats, texts=None, hainan=True, taiwan=None):
    frames.append(dict(y0=y0, y1=y1, snap=snap, feats=feats, texts=texts or [], hainan=hainan, taiwan=taiwan))

G = get
frame(-2070, -1601, "约公元前 2000 年", [
    F(G("bc2000", "Xia"), [-2070, "xia"]),
], hainan=False)
frame(-1600, -1047, "约公元前 1500 年", [
    F(G("bc1500", "Zhoa"), [-1600, "shang"]),
], hainan=False)
frame(-1046, -771, "约公元前 1000 年", [
    F(G("bc1000", "Zhoa"), [-1046, "wzhou"]),
], hainan=False)
frame(-770, -476, "约公元前 500 年", [
    F(G("bc500", "Zhou states"), [-770, "chunqiu"]),
], texts=[["晋", 111.6, 36.6], ["齐", 118.4, 36.8], ["楚", 112.2, 30.6], ["秦", 107.3, 34.6],
          ["吴", 120.4, 31.5], ["越", 120.7, 29.6], ["宋", 115.7, 34.3], ["鲁", 117.0, 35.5],
          ["燕", 116.3, 39.6], ["郑", 113.6, 34.2]], hainan=False)
frame(-475, -222, "约公元前 300 年", [
    F(G("bc400", "Xiongnu"), [-475, "xiongnu", "匈奴诸部"]),
    F(G("bc400", "Donghu tribes"), [-475, "donghu"]),
    F(G("bc400", "Gojoseon"), [-475, "gojoseon"]),
    F(G("bc300", "Yue"), [-475, "yue"], [-306, "zhanguo", "楚"]),
    F(G("bc300", "Zhou states"), [-475, "zhanguo"]),
    F(G("bc300", "Qin"), [-475, "qinstate"]),
], texts=[["齐", 118.4, 36.8], ["楚", 113.2, 30.6], ["燕", 116.3, 39.7], ["赵", 114.0, 37.6],
          ["魏", 114.6, 35.1], ["韩", 112.9, 34.2]], hainan=False)
frame(-221, -207, "秦统一后（约公元前 214 年）", [
    F(G("bc200", "Xiongnu"), [-221, "xiongnu"]),
    F(G("bc200", "Yuezhi"), [-221, "yuezhi"]),
    F(G("bc200", "Tungus"), [-221, "donghu"]),
    F(G("bc400", "Gojoseon"), [-221, "gojoseon"]),
    F(qin_g, [-221, "qin"]),
])
frame(-206, -112, "约公元前 200 年", [
    F(G("bc200", "Xiongnu"), [-206, "xiongnu"]),
    F(G("bc200", "Yuezhi"), [-206, "yuezhi"], [-176, "xiongnu", "匈奴（据河西、西域）"]),
    F(G("bc200", "Tungus"), [-206, "wuhuan"]),
    F(G("bc400", "Gojoseon"), [-206, "gojoseon"], [-194, "gojoseon", "卫满朝鲜"]),
    F(G("bc200", "Nan-Yue"), [-206, "nanyue"]),
    F(G("bc200", "Min-Yue"), [-206, "minyue"]),
    F(hanbc200, [-206, "whan"]),
], hainan=False)
frame(-111, 24, "约公元前 1 年", [
    F(G("bc1", "Xiongnu"), [-111, "xiongnu"]),
    F(G("bc1", "Koguryo"), [-111, None], [-37, "koguryo"]),
    F(G("bc1", "Han"), [-111, "whan"], [9, "xin"]),
    F(XIYU, [-111, None], [-60, "whan", "西域都护府"], [9, "xin", "西域都护府"], [16, None], loose=1),
])
frame(25, 219, "约公元 100 年", [
    F(G("bc1", "Xiongnu"), [25, "xiongnu", "北匈奴"], [91, "xianbei"]),
    F(G("100", "Kushan Empire"), [25, "kushan"]),
    F(G("100", "Koguryo"), [25, "koguryo"]),
    F(G("100", "Paekche"), [25, "baekje"]),
    F(G("100", "Silla"), [25, "silla"]),
    F(G("100", "Gaya"), [25, "gaya"]),
    F(G("100", "Yayoi"), [25, "wa"]),
    F(G("100", "Han"), [25, "ehan"]),
    F(G("100", "Southern Xiongnu"), [25, None], [50, "sxiongnu"]),
    F(XIYU, [25, None], [74, "ehan", "西域都护府"], [107, None], [123, "ehan", "西域长史府"], [190, None], loose=1),
])
frame(220, 279, "约公元 230 年（分界为示意）", [
    F(G("bc1", "Xiongnu"), [220, "xianbei"]),
    F(G("200", "Koguryo"), [220, "koguryo"]),
    F(G("200", "Paekche"), [220, "baekje"]),
    F(G("200", "Silla"), [220, "silla"]),
    F(G("200", "Gaya"), [220, "gaya"]),
    F(wei_g, [220, "wei"], [266, "wjin"]),
    F(G("200", "Southern Xiongnu"), [220, "sxiongnu", "南匈奴（附魏）"], [266, "sxiongnu", "匈奴五部（附晋）"]),
    F(shu_g, [220, "shu", "刘备（蜀）"], [221, "shu"], [263, "wei"], [266, "wjin"]),
    F(wu_g, [220, "wu", "孙权（吴）"], [229, "wu"]),
])
frame(280, 303, "约公元 300 年", [
    F(G("bc1", "Xiongnu"), [280, "xianbei"]),
    F(G("300", "Koguryo"), [280, "koguryo"]),
    F(G("300", "Paekche"), [280, "baekje"]),
    F(G("300", "Silla"), [280, "silla"]),
    F(G("300", "Gaya"), [280, "gaya"]),
    F(G("300", "Jin", "Han Zhao"), [280, "wjin"]),
])
frame(304, 316, "约公元 300 年", [
    F(G("bc1", "Xiongnu"), [304, "xianbei"]),
    F(G("300", "Koguryo"), [304, "koguryo"]),
    F(G("300", "Paekche"), [304, "baekje"]),
    F(G("300", "Silla"), [304, "silla"]),
    F(G("300", "Gaya"), [304, "gaya"]),
    F(G("300", "Jin"), [304, "wjin"]),
    F(G("300", "Han Zhao"), [304, "hanzhao"]),
])
frame(317, 419, "约公元 400 年", [
    F(G("400", "Ruanruan"), [317, "steppe_misc", "鲜卑、敕勒诸部"], [402, "rouran"]),
    F(G("400", "Koguryo"), [317, "koguryo"]),
    F(G("400", "Paekche"), [317, "baekje"]),
    F(G("400", "Silla"), [317, "silla"]),
    F(G("400", "Gaya"), [317, "gaya"]),
    F(G("400", "Sixteen Kingdoms"), [317, "s16"]),
    F(G("400", "Northern Liang"), [317, "s16", "河西诸凉"]),
    F(G("400", "Jin"), [317, "ejin"]),
])
frame(420, 588, "约公元 500 年", [
    F(G("500", "Ruanruan"), [420, "rouran"], [552, "tujue"]),
    F(G("500", "Koguryo"), [420, "koguryo"]),
    F(G("500", "Paekche"), [420, "baekje"]),
    F(G("500", "Silla"), [420, "silla"]),
    F(G("500", "Yamato"), [420, "wa", "倭（大和）"]),
    F(G("500", "Toba Wei"), [420, "nwei"], [534, "nwei", "东魏 · 西魏"], [550, "nwei", "北齐 · 北周"],
      [577, "nwei", "北周"], [581, "sui"]),
    F(G("500", "Jin Empire"), [420, "nan", "宋（刘宋）"], [479, "nan", "齐"], [502, "nan", "梁"], [557, "nan", "陈"]),
])
frame(589, 617, "约公元 600 年", [
    F(G("600", "Göktürks"), [589, "tujue", "东、西突厥"]),
    F(G("600", "Koguryo"), [589, "koguryo"]),
    F(G("600", "Paekche"), [589, "baekje"]),
    F(G("600", "Silla"), [589, "silla"]),
    F(G("600", "Yamato"), [589, "wa", "倭（大和）"]),
    F(G("600", "Sui Empire"), [589, "sui"]),
])
frame(618, 762, "约公元 700 年", [
    F(G("700", "Göktürks"), [618, "tujue", "东突厥"], [630, "tang", "漠北羁縻府州", 1], [682, "tujue", "后突厥"], [744, "huihe"]),
    F(G("700", "Western Gokturk Khaganate"), [618, "tujue", "西突厥"], [657, "tang", "西突厥故地（羁縻）", 1], [699, "turgesh"]),
    F(G("700", "Karluks"), [618, "tujue", "西突厥"], [657, "karluk"]),
    F(G("700", "Tungus"), [618, "mohe"]),
    F(G("700", "Tufan Empire"), [618, "tubo"]),
    F(G("700", "Nan-Zhao"), [618, "liuzhao"], [738, "nanzhao"]),
    F(G("700", "Koguryo"), [618, "koguryo"], [668, "tang", "安东都护府", 1], [698, "bohai"]),
    F(G("700", "Paekche"), [618, "baekje"], [660, "tang", "熊津都督府", 1], [676, "silla"]),
    F(G("700", "Silla"), [618, "silla"]),
    F(G("700", "Yamato"), [618, "wa", "倭"], [701, "japan"]),
    F(G("700", "Sui Empire"), [618, "tang"], [690, "tang", "周（武则天）"], [705, "tang"]),
    F(polys(G("700", "Uyghurs").intersection(box(93.5, 0, 160, 70))), [618, "tang", ""]),
    F(polys(G("700", "Uyghurs").intersection(box(58, 0, 93.5, 70))), [618, "tujue", "高昌 · 西突厥属部"], [640, "tang", "安西 · 北庭都护府", 1]),
    F(XIYU.difference(G("700", "Uyghurs")).difference(G("700", "Tufan Empire")), [618, None], [640, "tang", "安西 · 北庭都护府"], loose=1),
])
frame(763, 842, "约公元 800 年", [
    F(G("800", "Abbasid Caliphate"), [763, "abbasid"]),
    F(G("800", "Uyghurs"), [763, "huihe"], [788, "huihe", "回鹘"], [840, "kirghiz"]),
    F(G("800", "Tungus"), [763, "mohe", "靺鞨、室韦"]),
    F(G("800", "Tibetan Empire"), [763, "tubo"]),
    F(G("800", "Nan Chao"), [763, "nanzhao"]),
    F(G("800", "Parhae"), [763, "bohai"]),
    F(G("800", "Silia"), [763, "silla"]),
    F(G("800", "Japan"), [763, "japan"]),
    F(G("800", "Tang Empire"), [763, "tang"]),
])
frame(843, 959, "约公元 900 年", [
    F(G("900", "Karluks"), [843, "karluk"], [940, "karakhan"]),
    F(G("900", "Uyghurs"), [843, "kirghiz", "黠戛斯、鞑靼诸部"], [924, "liao", "阻卜诸部（附辽）", 1]),
    F(G("900", "Tungus"), [843, "mohe", "女真（黑水靺鞨）"]),
    F(G("900", "Tibetan Empire"), [843, "tubofrag"]),
    F(G("900", "Nan Chao"), [843, "nanzhao"], [902, "nanzhao", "大长和等"], [937, "dali"]),
    F(G("900", "Balhae"), [843, "bohai"], [926, "liao", "东丹（辽）"]),
    F(G("900", "Khitans"), [843, "khitan"], [916, "liao", "契丹（辽）"]),
    F(G("900", "Silla"), [843, "silla"], [901, "silla", "后三国"], [936, "goryeo"]),
    F(G("900", "Yamato"), [843, "japan"]),
    F(G("900", "Tang Empire"), [843, "tang"], [907, "wudai"]),
])
frame(960, 1050, "约公元 1000 年", [
    F(G("1000", "Tibet"), [960, "tubofrag"]),
    F(G("1000", "Nan Chao"), [960, "dali"]),
    F(G("1000", "Annam"), [960, "dayue", "交趾（静海军）"], [968, "dayue", "大瞿越"]),
    F(G("1000", "Korea"), [960, "goryeo"]),
    F(G("1000", "Imperial Japan (Fujiwara)"), [960, "japan"]),
    F(G("1000", "Liao"), [960, "liao"]),
    F(G("1000", "Xixia"), [960, "xixia", "党项（定难军）"], [1038, "xixia"]),
    F(G("1000", "Song Empire"), [960, "nsong"]),
])
frame(1051, 1126, "约公元 1100 年", [
    F(G("1100", "Karkhanids"), [1051, "karakhan"]),
    F(G("1100", "Mongols"), [1051, "liao", "阻卜等漠北诸部（附辽）", 1], [1125, "mongoltribes"]),
    F(G("1100", "Tibet"), [1051, "tubofrag"]),
    F(G("1100", "Nan Chao"), [1051, "dali"]),
    F(G("1100", "Đại Việt"), [1051, "dayue", "大越（李朝）"]),
    F(G("1100", "Korea"), [1051, "goryeo"]),
    F(G("1100", "Imperial Japan (Fujiwara)"), [1051, "japan"]),
    F(G("1100", "Liao"), [1051, "liao"], [1125, "jin"]),
    F(G("1100", "Xixia"), [1051, "xixia"]),
    F(G("1100", "Song Empire"), [1051, "nsong"]),
])
frame(1127, 1278, "约公元 1200 年（宋金分界为示意）", [
    F(G("1200", "Kara Khitai Khaganate"), [1127, "xiliao"], [1218, "mongol"], [1227, "chagatai"]),
    F(G("1200", "Mongol Empire"), [1127, "mongoltribes"], [1206, "mongol"], [1271, "yuan"]),
    F(G("1200", "Tibet"), [1127, "tubofrag"], [1247, "mongol", "吐蕃（归附蒙古）"], [1271, "yuan", "吐蕃（宣政院辖地）"]),
    F(G("1200", "Nan Chao"), [1127, "dali"], [1253, "mongol"], [1271, "yuan"]),
    F(G("1200", "Đại Việt"), [1127, "dayue", "大越（李朝）"], [1225, "dayue", "大越（陈朝）"]),
    F(G("1200", "Goryeo"), [1127, "goryeo"], [1259, "goryeo", "高丽（臣服蒙古）"]),
    F(G("1200", "Imperial Japan (Fujiwara)"), [1127, "japan"], [1185, "japan", "日本（镰仓幕府）"]),
    F(G("1200", "Xixia"), [1127, "xixia"], [1227, "mongol"], [1271, "yuan"]),
    F(jin_g, [1127, "jin"], [1234, "mongol"], [1271, "yuan"]),
    F(ssong_g, [1127, "ssong"]),
])
frame(1279, 1367, "约公元 1300 年", [
    F(G("1300", "Khanate of the Golden Horde"), [1279, "golden"]),
    F(G("1300", "Ilkhanate"), [1279, "ilkhan"]),
    F(G("1300", "Chagatai Khanate"), [1279, "chagatai"]),
    F(G("1300", "Sultanate of Delhi"), [1279, "delhi"]),
    F(G("1300", "Đại Việt"), [1279, "dayue", "大越（陈朝）"]),
    F(G("1300", "Champa"), [1279, "champa"]),
    F(G("1300", "Shogun Japan (Kamakura)"), [1279, "japan", "日本（镰仓幕府）"], [1336, "japan", "日本（室町幕府）"]),
    F(G("1300", "Great Khanate").difference(G("1200", "Goryeo").buffer(0.15)), [1279, "yuan"]),
    F(G("1200", "Goryeo"), [1279, "goryeo", "高丽（元之藩属）"]),
    F(G("1300", "Tibet"), [1279, "yuan", "吐蕃（宣政院辖地）"]),
])
frame(1368, 1643, "约公元 1500 年", [
    F(G("1492", "Timurid Emirates"), [1368, None], [1370, "timurid"], [1507, "centralasia", "布哈拉等汗国"]),
    F(G("1492", "Sultanate of Delhi"), [1368, "delhi"], [1526, "mughal"]),
    F(G("1492", "Oirat Confederation"), [1368, "oirat"]),
    F(moghul_g, [1368, "moghul"], [1514, "moghul", "叶尔羌汗国"]),
    F(tatar_g, [1368, "nyuan"], [1402, "nyuan", "鞑靼"]),
    F(jurchen_g, [1368, "nyuan", "北元 · 女真诸部"], [1409, "ming", "奴儿干都司", 1], [1435, "jurchen"],
      [1616, "houjin"], [1636, "qing"]),
    F(G("1492", "Tibet"), [1368, "ming", "乌斯藏（明封授）", 1], [1642, "khoshut"]),
    F(G("1492", "Đại Việt"), [1368, "dayue", "大越（陈朝）"], [1407, "ming", "交趾（明）"], [1428, "dayue", "大越（后黎朝）"]),
    F(G("1492", "Korea"), [1368, "goryeo"], [1392, "joseon"]),
    F(G("1492", "Japan"), [1368, "japan", "日本（室町幕府）"], [1573, "japan", "日本（安土桃山）"], [1603, "japan", "日本（江户幕府）"]),
    F(G("1492", "Ming Empire"), [1368, "ming"]),
], taiwan=[[1368, None], [1624, "dutch", "台湾（荷兰据南部）"]])
frame(1644, 1683, "约公元 1650 年", [
    F(G("1650", "Tsardom of Muscovy"), [1644, "russia", "沙皇俄国"]),
    F(G("1650", "Quazaq Khanate"), [1644, "kazakh"]),
    F(G("1650", "Mughal Empire"), [1644, "mughal"]),
    F(G("1650", "central Asian khanates"), [1644, "dzungar", "喀尔喀 · 准噶尔等蒙古诸部"]),
    F(G("1650", "Tibet"), [1644, "khoshut"]),
    F(G("1650", "Đại Việt"), [1644, "dayue", "大越（后黎朝）"]),
    F(G("1650", "Korea"), [1644, "joseon"]),
    F(G("1650", "Tokugawa shogunate"), [1644, "japan", "日本（江户幕府）"]),
    F(G("1650", "Manchu Empire"), [1644, "qing"]),
    F(G("1650", "Post-Ming Warlords"), [1644, "nanming"], [1662, "qing", "清（三藩镇守）"], [1673, "sanfan"], [1681, "qing", ""]),
], taiwan=[[1644, "dutch", "台湾（荷兰据南部）"], [1662, "zheng", "台湾（明郑）"], [1683, "qing", "台湾"]])
frame(1684, 1696, "约公元 1700 年", [
    F(G("1700", "Tsardom of Muscovy"), [1684, "russia", "沙皇俄国"]),
    F(G("1700", "Quazaq Khanate"), [1684, "kazakh"]),
    F(G("1700", "Mughal Empire"), [1684, "mughal"]),
    F(G("1700", "central Asian khanates"), [1684, "dzungar", "喀尔喀 · 准噶尔"], [1688, "dzungar"]),
    F(G("1700", "Tibet"), [1684, "khoshut"]),
    F(G("1700", "Đại Việt"), [1684, "dayue", "大越（后黎朝）"]),
    F(G("1700", "Korea"), [1684, "joseon"]),
    F(G("1700", "Tokugawa shogunate"), [1684, "japan", "日本（江户幕府）"]),
    F(G("1700", "Manchu Empire", "Post-Ming Warlords"), [1684, "qing"]),
], taiwan=[[1684, "qing", "台湾府"]])
frame(1697, 1758, "约公元 1715 年", [
    F(G("1715", "Tsardom of Muscovy"), [1697, "russia", "沙皇俄国"], [1721, "russia"]),
    F(G("1715", "Quazaq Khanate"), [1697, "kazakh"]),
    F(G("1715", "Mughal Empire"), [1697, "mughal"]),
    F(G("1715", "central Asian khanates"), [1697, "dzungar"], [1757, "qing", "准部 · 回部（平定中）"]),
    F(G("1715", "Tibet"), [1697, "khoshut"], [1717, "dzungar", "西藏（准噶尔占据）"], [1720, "qing", "西藏"]),
    F(G("1715", "Đại Việt"), [1697, "dayue", "大越（后黎朝）"]),
    F(G("1715", "Korea"), [1697, "joseon"]),
    F(G("1715", "Tokugawa shogunate"), [1697, "japan", "日本（江户幕府）"]),
    F(G("1715", "Manchu Empire"), [1697, "qing"]),
], taiwan=[[1697, "qing", "台湾府"]])
frame(1759, 1859, "约公元 1800 年", [
    F(G("1800", "Russian Empire"), [1759, "russia"]),
    F(G("1800", "central Asian khanates"), [1759, "centralasia", "哈萨克 · 浩罕等"]),
    F(G("1800", "Afghanistan"), [1759, "afghan"]),
    F(G("1800", "Maratha Confederacy"), [1759, "maratha"], [1818, "britind", "英属印度"]),
    F(G("1800", "Nepal"), [1759, None], [1768, "nepal"]),
    F(G("1800", "Burma"), [1759, "burma"]),
    F(G("1800", "Siam", "Rattanakosin Kingdom"), [1759, "siam"]),
    F(G("1800", "Đại Việt"), [1759, "dayue", "大越（后黎朝）"], [1802, "dayue", "越南（阮朝）"]),
    F(G("1800", "Korea"), [1759, "joseon"]),
    F(G("1800", "Japan"), [1759, "japan", "日本（江户幕府）"]),
    F(G("1800", "Qing Empire"), [1759, "qing"]),
], taiwan=[[1759, "qing", "台湾府"]])
frame(1860, 1894, "约公元 1880 年", [
    F(G("1880", "Russian Empire"), [1860, "russia"]),
    F(G("1880", "central Asian khanates"), [1860, "centralasia", "浩罕 · 布哈拉等"], [1876, "russia", "俄属中亚"]),
    F(G("1880", "Afghanistan"), [1860, "afghan"]),
    F(G("1880", "British Raj"), [1860, "britind"]),
    F(G("1880", "Nepal"), [1860, "nepal"]),
    F(G("1880", "Bhutan"), [1860, "bhutan"]),
    F(G("1880", "Rattanakosin Kingdom"), [1860, "siam"]),
    F(G("1880", "French Indochina"), [1860, "frind"]),
    F(G("1880", "Annam"), [1860, "dayue", "越南（阮朝）"], [1885, "frind"]),
    F(G("1880", "Korea"), [1860, "joseon"]),
    F(G("1880", "Imperial Japan"), [1860, "japan", "日本（江户幕府）"], [1868, "japan", "日本（明治）"]),
    F(G("1880", "Manchu Empire"), [1860, "qing"]),
], taiwan=[[1860, "qing", "台湾府"], [1885, "qing", "台湾省"]])
frame(1895, 1911, "约公元 1900 年", [
    F(G("1900", "Russian Empire"), [1895, "russia"]),
    F(G("1900", "central Asian khanates"), [1895, "russia", "俄属中亚"]),
    F(G("1900", "Afghanistan"), [1895, "afghan"]),
    F(G("1900", "British Raj"), [1895, "britind"]),
    F(G("1900", "Nepal"), [1895, "nepal"]),
    F(G("1900", "Bhutan"), [1895, "bhutan"]),
    F(G("1900", "Rattanakosin Kingdom"), [1895, "siam"]),
    F(G("1900", "French Indochina"), [1895, "frind"]),
    F(G("1900", "Korea"), [1895, "joseon"], [1897, "joseon", "大韩帝国"], [1910, "japan", "朝鲜（日本吞并）"]),
    F(G("1900", "Imperial Japan"), [1895, "japan", "日本（明治）"]),
    F(G("1900", "Manchu Empire"), [1895, "qing"]),
], taiwan=[[1895, "japan", "台湾（日本占据）"]])


# ---------- modern era (1912-2026): Natural Earth country outlines + year tables ----------
NEC = json.load(open(f"{NE}/countries.geojson"))
def ne(*names):
    out = []
    for n in names:
        hit = [f for f in NEC["features"] if f["properties"]["name"] == n]
        if not hit:
            raise KeyError(n)
        out.append(polys(make_valid(shape(hit[0]["geometry"])).intersection(WIN)))
    return polys(unary_union(out))
def parts(g):
    return [] if g.is_empty else ([g] if g.geom_type == "Polygon" else list(g.geoms))

CN = ne("China"); MN = ne("Mongolia")
assert CN.contains(Point(79.5, 35.2)) and ne("India").contains(Point(94.0, 28.0))
CNm = polys(CN.difference(HN_BOX))
tib = polys(get("1945", "Tibet").intersection(CNm))
xj = polys(get("1945", "Xinjiang").intersection(CNm).difference(tib))
man = polys(get("1945", "Manchuria").intersection(CNm))
core = polys(CNm.difference(unary_union([tib, xj, man])))
core_open = polys(core.buffer(-0.3).buffer(0.32).intersection(core))
pc = {"core": core_open, "tib": tib, "xj": xj, "man": man}
for comp in parts(polys(core.difference(core_open))):
    best = max(pc, key=lambda k: comp.buffer(0.15).intersection(pc[k]).area)
    pc[best] = polys(unary_union([pc[best], comp]))
# keep only the main body of each inner piece; strays go back to the core
for k in ("tib", "xj", "man"):
    ps = sorted(parts(pc[k]), key=lambda p: -p.area)
    pc[k] = ps[0]
    if len(ps) > 1:
        pc["core"] = polys(unary_union([pc["core"]] + ps[1:]))
print("modern pieces", {k: round(v.area, 1) for k, v in pc.items()})

qing1900 = get("1900", "Manchu Empire")
tuva_c = [p for p in parts(polys(qing1900.difference(unary_union([CN, MN]).buffer(0.06))))
          if p.area > 1.0 and box(88, 49.3, 100.5, 54.5).contains(p.centroid)]
RUS = ne("Russia")
tuva = polys(unary_union(tuva_c).intersection(RUS)) if tuva_c else Polygon()
print("tuva area", round(tuva.area, 1))
SSAKH = polys(RUS.intersection(box(141.5, 45.8, 145.5, 50.0)))
rus = polys(RUS.difference(SSAKH).difference(tuva))

OCC = Polygon([(109.5, 41.8), (110.5, 39.5), (111.0, 37.5), (111.2, 35.8), (110.9, 34.7), (113.2, 34.6),
               (113.5, 33.0), (113.2, 31.5), (112.5, 30.5), (113.2, 29.6), (115.0, 29.3), (116.5, 29.8),
               (118.2, 29.9), (119.6, 29.3), (121.9, 29.5), (126, 29.5), (126, 43.5), (109.5, 43.5)])
OCC2 = Polygon([(112.3, 23.6), (114.6, 23.6), (115.0, 22.4), (112.6, 21.6)])   # Guangzhou area
occ = polys(unary_union([OCC, OCC2]).intersection(pc["core"]))
AKSAI = Polygon([(77.9, 35.5), (78.3, 34.7), (79.0, 34.35), (79.6, 34.5), (80.2, 35.3), (80.3, 35.9), (79.4, 36.0), (78.4, 35.95)])
ARUN = Polygon([(91.6, 27.8), (91.7, 26.9), (92.6, 26.9), (93.9, 27.05), (95.2, 27.75), (96.0, 27.9), (97.0, 27.75),
                (97.35, 28.25), (97.0, 28.6), (96.2, 29.3), (95.2, 29.2), (94.2, 29.0), (93.3, 28.4), (92.5, 27.85)])
IND = ne("India")
frame(1912, 2026, "以今日国界为底，按年份标注实际管辖", [
    F(rus, [1912, "russia"], [1917, "russia", "苏俄"], [1922, "ussr"], [1992, "ru"]),
    F(SSAKH, [1912, "jpemp", "南库页岛（日本）"], [1945, "ussr", ""], [1992, "ru", ""]),
    F(ne("Kazakhstan"), [1912, "russia", ""], [1922, "ussr", ""], [1992, "kaz"]),
    F(ne("Kyrgyzstan"), [1912, "russia", ""], [1922, "ussr", ""], [1992, "kgz"]),
    F(ne("Tajikistan"), [1912, "russia", ""], [1922, "ussr", ""], [1992, "tjk"]),
    F(ne("Uzbekistan"), [1912, "russia", ""], [1922, "ussr", ""], [1992, "uzb"]),
    F(ne("Turkmenistan"), [1912, "russia", ""], [1922, "ussr", ""], [1992, "tkm"]),
    F(ne("Afghanistan"), [1912, "afghan"]),
    F(IND, [1912, "britind"], [1947, "india"]),
    F(ne("Pakistan"), [1912, "britind", ""], [1947, "pakistan"]),
    F(ne("Bangladesh"), [1912, "britind", ""], [1947, "pakistan", "东巴基斯坦"], [1971, "bangladesh"]),
    F(ne("Nepal"), [1912, "nepal", "尼泊尔"]),
    F(ne("Bhutan"), [1912, "bhutan"]),
    F(ne("Myanmar"), [1912, "britind", "英属缅甸"], [1948, "mm"]),
    F(ne("Thailand"), [1912, "th", "暹罗"], [1939, "th"]),
    F(ne("Vietnam"), [1912, "frind"], [1954, "vn", "越南（南北分治）"], [1976, "vn"]),
    F(ne("Laos"), [1912, "frind", ""], [1953, "la"]),
    F(ne("Cambodia"), [1912, "frind", ""], [1953, "kh"]),
    F(ne("Philippines"), [1912, "ph", "菲律宾（美国统治）"], [1946, "ph"]),
    F(ne("North Korea"), [1912, "jpemp", "朝鲜（日本统治）"], [1945, "korea_n", "朝鲜半岛北部（苏军占领）"], [1948, "korea_n"]),
    F(ne("South Korea"), [1912, "jpemp", ""], [1945, "korea_s", "朝鲜半岛南部（美军占领）"], [1948, "korea_s"]),
    F(ne("Japan"), [1912, "jpemp"], [1945, "japan", "日本（盟军占领）"], [1952, "japan"]),
    F(MN, [1912, "mongolia", "外蒙古（博克多汗政权）"], [1915, "roc", "外蒙古（自治，中国宗主权）", 1], [1919, "roc", "外蒙古（自治被取消）"],
      [1921, "mongolia", "蒙古（苏俄支持下独立）"], [1924, "mongolia", "蒙古人民共和国"], [1992, "mongolia", "蒙古国"]),
    F(tuva, [1912, "roc", "唐努乌梁海", 1], [1914, "russia", "唐努乌梁海（俄国保护）"], [1921, "ussr", "图瓦（苏联扶植）"], [1944, "ussr", ""], [1992, "ru", ""]),
    F(pc["core"], [1912, "roc"], [1949, "prc"]),
    F(pc["man"], [1912, "roc", ""], [1931, "jpemp", "东北（日军占领）"], [1932, "manchukuo"], [1945, "roc", "东北（苏军进驻，次年移交）"], [1946, "roc", ""], [1949, "prc", ""]),
    F(pc["xj"], [1912, "roc", "新疆"], [1949, "prc", "新疆"], [1955, "prc", ""]),
    F(pc["tib"], [1912, "tibet"], [1951, "prc", "西藏"], [1965, "prc", ""]),
    F(HAINAN, [1912, "roc", ""], [1949, "roc", "海南（国民政府控制至1950年）"], [1950, "prc", ""]),
    F(ne("Hong Kong"), [1912, "uk", "香港（英国管治）"], [1941, "jpemp", "香港（日军占领）"], [1945, "uk", "香港（英国管治）"], [1997, "prc", "香港特别行政区"]),
    F(ne("Macao"), [1912, "portugal", "澳门（葡萄牙管治）"], [1999, "prc", "澳门特别行政区"]),
    F(occ, [1912, None], [1937, "jpemp", "日军占领区", 1], [1945, None], loose=1),
    F(ne("Siachen Glacier"), [1912, "britind", ""], [1947, "dispute", "锡亚琴冰川（印巴争议）"], loose=1),
    F(polys(AKSAI.intersection(CN)), [1912, None], [1950, "dispute", "阿克赛钦（中国控制，印度主张）"], loose=1),
    F(polys(ARUN.intersection(IND)), [1912, None], [1950, "dispute", "藏南／阿鲁纳恰尔（印度控制，中国主张）"], loose=1),
], hainan=False, taiwan=[[1912, "jpemp", "台湾（日本占据）"], [1945, "roc", "台湾"], [1949, "rocT", "台湾（中华民国政府治理）"]])

# ---------- emit ----------
def label_pt(g):
    v = polys(g.intersection(VIEW))
    if v.is_empty:
        return None
    big = max(v.geoms, key=lambda p: p.area) if v.geom_type == "MultiPolygon" else v
    try:
        p = polylabel(big, tolerance=0.2)
    except Exception:
        p = big.representative_point()
    return [round(p.x, 2), round(p.y, 2), round(big.area, 1)]

os.makedirs(OUT, exist_ok=True)
meta = []
for i, fr in enumerate(frames):
    feats = []
    used = []
    geoms = []
    for geom, st, o in fr["feats"]:
        g = polys(geom.difference(TW_BOX))
        if fr["hainan"]:
            g = polys(g.difference(HN_BOX))
        geoms.append([g, st, o])
    # Hainan follows whichever feature covers the Leizhou peninsula
    if fr["hainan"]:
        probe = Point(110.2, 21.4)
        best = None
        for item in geoms:
            if item[2].get("loose"):
                continue
            if item[0].buffer(0.6).contains(probe):
                best = item
        if best is not None:
            best[0] = polys(unary_union([best[0], HAINAN]))
        else:
            print("frame", fr["y0"], "no Hainan owner")
    if fr["taiwan"]:
        geoms.append([TAIWAN, [list(s) for s in fr["taiwan"]], {}])
    for g, st, o in geoms:
        if g.is_empty:
            print("EMPTY", fr["y0"], st); continue
        feats.append({"type": "Feature", "geometry": mapping(g),
                      "properties": {"st": st, "lp": label_pt(g), "loose": o.get("loose", 0)}})
    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{OUT}/frame_{i}.geojson", "w"))
    meta.append({"y0": fr["y0"], "y1": fr["y1"], "snap": fr["snap"], "texts": fr["texts"], "n": len(feats)})
json.dump(meta, open(f"{OUT}/frames_meta.json", "w"), ensure_ascii=False)

# basemap
json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": mapping(land), "properties": {}}]},
          open(f"{OUT}/land.geojson", "w"))
rv = json.load(open(f"{NE}/rivers.geojson"))
RN = {"Huang": "黄河", "Chang Jiang": "长江", "Yangtze": "长江", "Jinsha": "长江", "Tongtian": "长江", "Tuotuo": "长江",
      "Xi": "珠江", "Xun": "珠江", "Hongshui": "珠江", "Heilong Jiang": "黑龙江", "Amur": "黑龙江", "Songhua": "松花江",
      "Liao": "辽河", "Xiliao": "辽河", "Tarim": "塔里木河", "Yarlung": "雅鲁藏布江", "Brahmaputra": "雅鲁藏布江",
      "Dihang": "雅鲁藏布江", "Lancang": "澜沧江", "Mekong": "澜沧江", "Nu": "怒江", "Salween": "怒江", "Han": "汉水",
      "Indus": "印度河", "Ganges": "恒河", "Ayeyarwady": "伊洛瓦底江", "Hong": "红河", "Selenge (Selenga)": "色楞格河",
      "Ertix": "额尔齐斯河", "Syr Darya": "锡尔河", "Argun’": "额尔古纳河", "Hailar": "额尔古纳河"}
rf = []
for f in rv["features"]:
    n = f["properties"].get("name")
    if n in RN and f["geometry"]:
        g = shape(f["geometry"]).intersection(WIN)
        if not g.is_empty and g.geom_type in ("LineString", "MultiLineString"):
            rf.append({"type": "Feature", "geometry": mapping(g), "properties": {"n": RN[n], "w": 2 if RN[n] in ("黄河", "长江") else 1}})
json.dump({"type": "FeatureCollection", "features": rf}, open(f"{OUT}/rivers.geojson", "w"), ensure_ascii=False)
lk = json.load(open(f"{NE}/lakes.geojson"))
lf = []
for f in lk["features"]:
    if not f["geometry"]:
        continue
    g = make_valid(shape(f["geometry"])).intersection(WIN)
    if not g.is_empty and g.area > 0.15:
        lf.append({"type": "Feature", "geometry": mapping(polys(g)), "properties": {}})
json.dump({"type": "FeatureCollection", "features": lf}, open(f"{OUT}/lakes.geojson", "w"))
print("frames", len(frames), "rivers", len(rf), "lakes", len(lf))
