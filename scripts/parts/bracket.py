# -*- coding: utf-8 -*-
"""铺作（斗拱）—— 五铺作单抄单下昂。

依《营造法式》，五铺作 = 出跳两跳（一跳华拱、二跳下昂），
自栌斗起共铺叠五层，故名“五铺作”。

构件一览（原画 crops/B_dougong.png、E_topleft.png 中可逐一辨认）：
    栌斗    —— 坐于普拍枋上，全攒之底
    华拱    —— 第一跳，向外挑出；足材
    泥道拱  —— 与华拱同层，横向（沿墙面）出跳，承瓜子拱
    交互斗  —— 坐于华拱外端，承昂
    昂      —— 第二跳，斜向下出，昂尖作“批竹昂”（劈竹状斜削）
    瓜子拱  —— 泥道拱之上，横向
    慢拱    —— 瓜子拱之上，最长的一道横拱
    令拱    —— 昂外端之横拱，承撩檐枋
    散斗/齐心斗 —— 各拱端及拱心之小斗
    耍头    —— 昂背向外挑出的“蚂蚱头”
    撩檐枋  —— 檐下通长枋，屋面由此起坡

局部坐标：原点在柱心（或补间中）之普拍枋上皮，
         +X 为出跳方向（向建筑外），+Y 沿墙面，+Z 向上。

竖向定位全部由 出跳(30分) 与 跳高(足材21分) 推导，
昂的斜率、令拱与撩檐枋的标高均沿昂背反算，不做手填，避免累积错位。
"""
import math

from .. import common as C

FEN = C.FEN

# ---- 材份尺寸（《营造法式》卷四·斗拱） ------------------------------------ #
LU_DOU_W = 32 * FEN          # 栌斗方 32 分
LU_DOU_H = 20 * FEN          # 栌斗高 20 分
JIAO_DOU_L, JIAO_DOU_H, JIAO_DOU_W = 18 * FEN, 10 * FEN, 16 * FEN   # 交互斗
SAN_DOU_L, SAN_DOU_H, SAN_DOU_W = 16 * FEN, 10 * FEN, 14 * FEN      # 散斗
QI_XIN_L, QI_XIN_H, QI_XIN_W = 16 * FEN, 10 * FEN, 14 * FEN         # 齐心斗

GONG_T = 10 * FEN            # 拱厚 10 分
HUAGONG_L = 72 * FEN         # 华拱长 72 分
NIDAO_L = 62 * FEN           # 泥道拱长 62 分
GUAZI_L = 62 * FEN           # 瓜子拱长 62 分
MANGONG_L = 92 * FEN         # 慢拱长 92 分
LINGGONG_L = 72 * FEN        # 令拱长 72 分

ZUCAI_H = 21 * FEN           # 足材高 0.378
DANCAI_H = 15 * FEN          # 单材高 0.270

CHU_TIAO = 30 * FEN          # 出跳 30 分
ANG_TAN = math.tan(math.radians(19.0))   # 下昂斜度
ANG_H = 0.26                 # 昂的竖直材高
ANG_TAIL_X = -0.92           # 昂尾（伸入屋内）
SHUATOU_L = 0.86
LIAOYAN_H = 0.30
LIAOYAN_T = 0.26

# ---- 竖向标高（自普拍枋上皮起算） ----------------------------------------- #
Z_HUAGONG = LU_DOU_H                       # 华拱底   0.360
Z_HUAGONG_TOP = Z_HUAGONG + ZUCAI_H        # 华拱顶   0.738
Z_JIAO_DOU = Z_HUAGONG_TOP                 # 交互斗底 0.738
Z_JIAO_DOU_TOP = Z_JIAO_DOU + JIAO_DOU_H   # 交互斗顶 0.918

Z_NIDAO = LU_DOU_H                         # 泥道拱与华拱同层
Z_SAN_DOU_NIDAO = Z_NIDAO + DANCAI_H
Z_GUAZI = Z_SAN_DOU_NIDAO + SAN_DOU_H
Z_SAN_DOU_GUAZI = Z_GUAZI + DANCAI_H
Z_MANGONG = Z_SAN_DOU_GUAZI + SAN_DOU_H
Z_SAN_DOU_MAN = Z_MANGONG + DANCAI_H
Z_ZUTOUFANG = Z_SAN_DOU_MAN + SAN_DOU_H    # 柱头枋（内檐）

# ---- 出跳方向的水平定位 --------------------------------------------------- #
X_HUAGONG_TIP = CHU_TIAO                          # 华拱头 0.540
X_HUAGONG_C = X_HUAGONG_TIP - HUAGONG_L / 2       # 华拱中心 -0.108
X_JIAO_DOU = X_HUAGONG_TIP - 0.05                 # 交互斗中心
X_ANG_TIP = 2 * CHU_TIAO                          # 昂尖 1.080
X_ANG_KNEE = X_ANG_TIP - 0.10                     # 批竹昂斜削起点
X_LINGGONG = 0.86                                 # 令拱中心

GONG_SAMPLES = 16


# ---- 昂背/昂底的标高函数（供令拱、撩檐枋定位） ---------------------------- #
def ang_under(x):
    """昂底面在 x 处的标高。"""
    return Z_JIAO_DOU_TOP - (x - X_JIAO_DOU) * ANG_TAN


def ang_top(x):
    """昂背在 x 处的标高。"""
    return ang_under(x) + ANG_H


Z_LINGGONG = ang_top(X_LINGGONG)                        # 令拱底
Z_LIAOYAN = Z_LINGGONG + DANCAI_H + SAN_DOU_H           # 撩檐枋底


# --------------------------------------------------------------------------- #
#  基本构件
# --------------------------------------------------------------------------- #
def dou(name, w, h, col="GateTower", bottom=0.80, qi=0.58):
    """斗：由斗底、斗欹（内凹腰）、斗平、斗耳四段构成的方台。"""
    hw = w / 2
    bw = hw * bottom
    levels = [
        (0.00, bw),
        (h * qi * 0.50, bw),
        (h * qi * 0.80, hw * 0.87),
        (h * qi, hw * 0.93),
        (h * (qi + (1 - qi) * 0.30), hw),
        (h, hw),
    ]
    rows = [[(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)] for (z, s) in levels]
    return C.grid_obj(name, rows, close_u=True, cap_first=True, cap_last=True,
                      collection=col)


def gong(name, length, height, thickness, axis="Y", col="GateTower", juan=4 * FEN):
    """拱：侧视带卷杀，沿 axis 拉伸厚度。

    axis='Y' —— 拱身沿 X 向外挑出（华拱、令拱）
    axis='X' —— 拱身沿 Y 横出（泥道拱、瓜子拱、慢拱）
    """
    prof = C.gong_profile(length, height, juan=juan, samples=GONG_SAMPLES)
    return C.prism(name, prof, thickness, axis=axis, collection=col)


def ang_profile(x_tip=None, knee=None, tail=ANG_TAIL_X, thick=ANG_H, h=ANG_TAN):
    """批竹昂侧视轮廓：昂背与昂底平行斜下，昂尖斜削成一尖。

    直接按斜率生成多边形，不做物体旋转 —— 免得旋转基准点选错把整根昂甩到别处。
    """
    x_tip = X_ANG_TIP if x_tip is None else x_tip
    knee = X_ANG_KNEE if knee is None else knee
    z_under_tip = ang_under(x_tip)
    return [
        (tail, ang_top(tail)),                  # 昂背·尾
        (knee, ang_top(knee)),                  # 昂背·斜削起点
        (x_tip, z_under_tip + thick * 0.34),    # 昂尖（劈竹状）
        (knee, ang_under(knee)),                # 昂底·斜削起点
        (tail, ang_under(tail)),                # 昂底·尾
    ]


# --------------------------------------------------------------------------- #
#  整攒铺作
# --------------------------------------------------------------------------- #
def build_shuzuo(name="铺作", zhu_tou=True, col="GateTower"):
    """生成一攒五铺作，返回对象列表（局部坐标，未定位）。"""
    objs = []
    s = 1.0 if zhu_tou else 0.93          # 补间略小

    # ---- 栌斗 --------------------------------------------------------- #
    objs.append(dou(f"{name}_栌斗", LU_DOU_W, LU_DOU_H, col))
    objs.append(C.box(f"{name}_斗底", LU_DOU_W * 0.80, LU_DOU_W * 0.80, 6 * FEN,
                      loc=(0, 0, -3 * FEN), collection=col))

    # ---- 华拱（第一跳） ----------------------------------------------- #
    hg = gong(f"{name}_华拱", HUAGONG_L * s, ZUCAI_H, GONG_T, axis="Y", col=col)
    hg.location = (X_HUAGONG_C, 0.0, Z_HUAGONG)
    objs.append(hg)

    # ---- 泥道拱（与华拱同层，横向） ----------------------------------- #
    nd = gong(f"{name}_泥道拱", NIDAO_L * s, DANCAI_H, GONG_T, axis="X", col=col)
    nd.location = (0.0, 0.0, Z_NIDAO)
    objs.append(nd)
    for sg in (-1, 1):
        objs.append(C.box(f"{name}_散斗_泥道{sg}", SAN_DOU_W, SAN_DOU_L, SAN_DOU_H,
                          loc=(0.0, sg * NIDAO_L * s / 2, Z_SAN_DOU_NIDAO + SAN_DOU_H / 2),
                          collection=col))

    # ---- 交互斗（华拱外端，承昂） ------------------------------------- #
    objs.append(C.box(f"{name}_交互斗", JIAO_DOU_W, JIAO_DOU_L, JIAO_DOU_H,
                      loc=(X_JIAO_DOU, 0.0, Z_JIAO_DOU + JIAO_DOU_H / 2),
                      collection=col))

    # ---- 瓜子拱 / 慢拱（横向叠置） ------------------------------------ #
    gz = gong(f"{name}_瓜子拱", GUAZI_L * s, DANCAI_H, GONG_T, axis="X", col=col)
    gz.location = (0.0, 0.0, Z_GUAZI)
    objs.append(gz)
    for sg in (-1, 1):
        objs.append(C.box(f"{name}_散斗_瓜子{sg}", SAN_DOU_W, SAN_DOU_L, SAN_DOU_H,
                          loc=(0.0, sg * GUAZI_L * s / 2, Z_SAN_DOU_GUAZI + SAN_DOU_H / 2),
                          collection=col))

    mg = gong(f"{name}_慢拱", MANGONG_L * s, DANCAI_H, GONG_T, axis="X", col=col)
    mg.location = (0.0, 0.0, Z_MANGONG)
    objs.append(mg)
    for sg in (-1, 1):
        objs.append(C.box(f"{name}_散斗_慢{sg}", SAN_DOU_W, SAN_DOU_L, SAN_DOU_H,
                          loc=(0.0, sg * MANGONG_L * s / 2, Z_SAN_DOU_MAN + SAN_DOU_H / 2),
                          collection=col))
    objs.append(C.box(f"{name}_齐心斗_慢", QI_XIN_W, QI_XIN_L, QI_XIN_H,
                      loc=(0.0, 0.0, Z_SAN_DOU_MAN + QI_XIN_H / 2), collection=col))

    # ---- 昂（第二跳，沿昂背斜率斜下出） ------------------------------- #
    objs.append(C.prism(f"{name}_昂", ang_profile(), GONG_T, axis="Y", collection=col))

    # ---- 令拱（坐于昂背，承撩檐枋） ----------------------------------- #
    lg = gong(f"{name}_令拱", LINGGONG_L * s, DANCAI_H, GONG_T, axis="X", col=col)
    lg.location = (X_LINGGONG, 0.0, Z_LINGGONG)
    objs.append(lg)
    # 令拱下承的交互斗（坐在昂背上）
    objs.append(C.box(f"{name}_交互斗_昂背", JIAO_DOU_W, JIAO_DOU_L, JIAO_DOU_H,
                      loc=(X_LINGGONG, 0.0, Z_LINGGONG - JIAO_DOU_H / 2), collection=col))
    for sg in (-1, 0, 1):
        objs.append(C.box(f"{name}_散斗_令{sg}", SAN_DOU_W, SAN_DOU_L, SAN_DOU_H,
                          loc=(X_LINGGONG, sg * LINGGONG_L * s / 2,
                               Z_LINGGONG + DANCAI_H + SAN_DOU_H / 2),
                          collection=col))

    # ---- 耍头（蚂蚱头，昂背向外挑出） --------------------------------- #
    objs.append(C.box(f"{name}_耍头", SHUATOU_L, GONG_T * 1.05, 13 * FEN,
                      loc=(X_LINGGONG + 0.10, 0.0, Z_LINGGONG + DANCAI_H * 0.55),
                      collection=col))

    # ---- 柱头枋（内檐通长枋） ----------------------------------------- #
    if zhu_tou:
        objs.append(C.box(f"{name}_柱头枋", GONG_T * 1.15, 3.40, 14 * FEN,
                          loc=(-0.02, 0.0, Z_ZUTOUFANG + 7 * FEN), collection=col))
    return objs


def shuzuo_top():
    """铺作层总高（自普拍枋上皮至撩檐枋上皮）—— 供屋面定位。"""
    return Z_LIAOYAN + LIAOYAN_H


def liaoyanfang(name="撩檐枋", length=1.0, col="GateTower", z=None):
    """撩檐枋：檐下通长枋。"""
    zz = Z_LIAOYAN if z is None else z
    return C.box(name, length, LIAOYAN_T, LIAOYAN_H,
                 loc=(0, 0, zz + LIAOYAN_H / 2), collection=col)
