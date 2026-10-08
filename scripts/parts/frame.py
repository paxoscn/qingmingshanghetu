# -*- coding: utf-8 -*-
"""楼身 —— 檐柱、柱础、阑额、普拍枋、破子棂窗、门、平坐。

对应原画 crops/B_dougong.png：
    下层为通面阔三间的楼身，明间开门，两次间装破子棂窗；
    柱头以阑额相连，阑额上压普拍枋，普拍枋上坐铺作（见 bracket.py）；
    楼身立于平坐之上，平坐外沿围勾栏（见 railing.py）。

破子棂窗：棂条由方木对角破开而成，断面为直角三角形，故正看为密排细线，
侧看有棱 —— 这是宋式窗的典型做法，也是原画中那一片细密竖线的来由。
"""
import math

from .. import common as C

T = C.Tower

COL_H = T.col_h
COL_D = T.col_d


# --------------------------------------------------------------------------- #
#  柱
# --------------------------------------------------------------------------- #
def column(name, h, d_bottom, d_top, offset_top=(0.0, 0.0), samples=14, rings=10):
    """檐柱：带卷杀（上收）与侧脚（柱头向内微倾）。"""
    rows = []
    ox, oy = offset_top
    for ri in range(rings + 1):
        t = ri / rings
        z = h * t
        # 卷杀：柱身下段近直，上段渐收（指数 > 1 使收缩集中在柱头附近）
        rr = (d_bottom + (d_top - d_bottom) * (t ** 2.4)) / 2.0
        row = []
        for si in range(samples):
            a = si * 2 * math.pi / samples
            row.append((ox * t + math.cos(a) * rr, oy * t + math.sin(a) * rr, z))
        rows.append(row)
    return C.grid_obj(name, rows, close_u=True, cap_first=True, cap_last=True,
                      collection="GateTower")


def plinth(name, r, h):
    """柱础：覆盆式，上小下大。"""
    return C.frustum(name, r * 2 * 0.82, r * 2 * 0.82, r * 2, r * 2, h)


def build_columns(z0=0.0):
    """按柱网布置檐柱与柱础，返回 (柱列表, 柱头坐标表)。

    侧脚：柱头沿面阔、进深两方向各向内收 side_splay×柱高，角柱最多。
    生起：自明间向角柱，柱高逐渐加大。
    """
    cols, tops = [], {}
    hw = T.total_w() / 2.0
    hd = T.total_d() / 2.0
    for x in T.col_x():
        for y in T.col_y():
            kx = abs(x) / hw if hw else 0.0
            ky = abs(y) / hd if hd else 0.0
            rise = T.rise * COL_H * max(kx, ky)
            h = COL_H + rise
            ox = -math.copysign(1.0, x) * T.side_splay * COL_H * kx if x else 0.0
            oy = -math.copysign(1.0, y) * T.side_splay * COL_H * ky if y else 0.0
            d_top = COL_D * T.col_taper
            ob = column(f"檐柱_{x:.1f}_{y:.1f}", h, COL_D, d_top, (ox, oy))
            ob.location = (x, y, z0)
            cols.append(ob)
            p = C.prism(f"柱础_{x:.1f}_{y:.1f}",
                        [(math.cos(a) * T.plinth_r, math.sin(a) * T.plinth_r)
                         for a in [k * math.pi / 8 for k in range(16)]],
                        T.plinth_h, axis="Z")
            p.location = (x, y, z0 - T.plinth_h / 2 + T.plinth_h / 2 - T.plinth_h / 2)
            p.location = (x, y, z0 - T.plinth_h / 2)
            cols.append(p)
            tops[(round(x, 3), round(y, 3))] = (x + ox, y + oy, z0 + h)
    return cols, tops


# --------------------------------------------------------------------------- #
#  阑额 / 普拍枋
# --------------------------------------------------------------------------- #
def lane_and_pupai(tops, z_extra=0.0):
    """阑额（柱头间联系梁）与普拍枋（阑额上的通长扁枋）。

    沿檐柱四周一圈：先铺阑额，再在其上压普拍枋。
    """
    objs = []
    xs, ys = T.col_x(), T.col_y()
    hw, hd = T.total_w() / 2.0, T.total_d() / 2.0

    def z_of(x, y):
        return tops[(round(x, 3), round(y, 3))][2]

    # ---- 前后檐（沿 X 向，逐间一段） ---------------------------------- #
    for y in (ys[0], ys[-1]):
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            z0 = min(z_of(x0, y), z_of(x1, y)) - T.lane_h
            L = (x1 - x0) - COL_D * 0.95
            cx = (x0 + x1) / 2
            objs.append(C.box(f"阑额_{y:.1f}_{i}", L, T.lane_t, T.lane_h,
                              loc=(cx, y, z0 + T.lane_h / 2)))
            objs.append(C.box(f"普拍枋_{y:.1f}_{i}", L + COL_D * 0.9, T.pupai_t,
                              T.pupai_h, loc=(cx, y, z0 + T.lane_h + T.pupai_h / 2)))

    # ---- 两山（沿 Y 向） ---------------------------------------------- #
    for x in (xs[0], xs[-1]):
        for j in range(len(ys) - 1):
            y0, y1 = ys[j], ys[j + 1]
            z0 = min(z_of(x, y0), z_of(x, y1)) - T.lane_h
            L = (y1 - y0) - COL_D * 0.95
            cy = (y0 + y1) / 2
            objs.append(C.box(f"阑额山_{x:.1f}_{j}", T.lane_t, L, T.lane_h,
                              loc=(x, cy, z0 + T.lane_h / 2)))
            objs.append(C.box(f"普拍枋山_{x:.1f}_{j}", T.pupai_t, L + COL_D * 0.9,
                              T.pupai_h, loc=(x, cy, z0 + T.lane_h + T.pupai_h / 2)))
    return objs


def pupai_z(tops):
    """普拍枋上皮标高 —— 铺作就坐在这个面上。"""
    z = max(t[2] for t in tops.values())
    return z - T.lane_h + T.lane_h + T.pupai_h


# --------------------------------------------------------------------------- #
#  破子棂窗
# --------------------------------------------------------------------------- #
def _slat_prism(name, length, w, h):
    """破子棂：方木对角破开，断面为直角三角形。"""
    return C.prism(name, [(-w / 2, 0.0), (w / 2, -h), (w / 2, 0.0)],
                   length, axis="Z")


def chuang(name, x0, x1, z_bot, z_top, y, depth=0.12):
    """破子棂窗：外框 + 上下串 + 密排破子棂。"""
    objs = []
    w = x1 - x0
    cx = (x0 + x1) / 2
    hgt = z_top - z_bot
    fr = 0.14
    # 外框
    objs.append(C.box(f"{name}_框下", w, depth, fr, loc=(cx, y, z_bot + fr / 2)))
    objs.append(C.box(f"{name}_框上", w, depth, fr, loc=(cx, y, z_top - fr / 2)))
    objs.append(C.box(f"{name}_框左", fr, depth, hgt, loc=(x0 + fr / 2, y, z_bot + hgt / 2)))
    objs.append(C.box(f"{name}_框右", fr, depth, hgt, loc=(x1 - fr / 2, y, z_bot + hgt / 2)))
    # 腰串（中横木）
    objs.append(C.box(f"{name}_腰串", w, depth * 0.9, 0.10,
                      loc=(cx, y, z_bot + hgt * 0.52)))
    # 棂条
    pitch = T.slat_w + T.slat_gap
    n = max(1, int((w - 2 * fr) / pitch))
    span = (n - 1) * pitch
    x_start = cx - span / 2
    for k in range(n):
        objs.append(C.box(f"{name}_棂{k}", T.slat_w, depth * 0.7, hgt - 2 * fr,
                          loc=(x_start + k * pitch, y, z_bot + hgt / 2)))
    return C.join(objs, name)


def chuang_side(name, y0, y1, z_bot, z_top, x, depth=0.12):
    """两山的破子棂窗（沿 Y 向）。"""
    objs = []
    w = y1 - y0
    cy = (y0 + y1) / 2
    hgt = z_top - z_bot
    fr = 0.14
    objs.append(C.box(f"{name}_框下", depth, w, fr, loc=(x, cy, z_bot + fr / 2)))
    objs.append(C.box(f"{name}_框上", depth, w, fr, loc=(x, cy, z_top - fr / 2)))
    objs.append(C.box(f"{name}_框左", depth, fr, hgt, loc=(x, y0 + fr / 2, z_bot + hgt / 2)))
    objs.append(C.box(f"{name}_框右", depth, fr, hgt, loc=(x, y1 - fr / 2, z_bot + hgt / 2)))
    objs.append(C.box(f"{name}_腰串", depth * 0.9, w, 0.10, loc=(x, cy, z_bot + hgt * 0.52)))
    pitch = T.slat_w + T.slat_gap
    n = max(1, int((w - 2 * fr) / pitch))
    span = (n - 1) * pitch
    y_start = cy - span / 2
    for k in range(n):
        objs.append(C.box(f"{name}_棂{k}", depth * 0.7, T.slat_w, hgt - 2 * fr,
                          loc=(x, y_start + k * pitch, z_bot + hgt / 2)))
    return C.join(objs, name)


def build_windows(tops):
    """两次间装破子棂窗，明间留门。"""
    objs = []
    xs, ys = T.col_x(), T.col_y()
    z_lane = min(t[2] for t in tops.values()) - T.lane_h
    z_top = z_lane - 0.10
    z_bot = z_top - T.win_h

    # 前后檐两次间
    for y in (ys[0], ys[-1]):
        for i in (0, 2):
            x0 = xs[i] + COL_D * 0.6
            x1 = xs[i + 1] - COL_D * 0.6
            objs.append(chuang(f"窗_{y:.1f}_{i}", x0, x1, z_bot, z_top, y))
    # 两山三间
    for x in (xs[0], xs[-1]):
        for j in range(len(ys) - 1):
            y0 = ys[j] + COL_D * 0.6
            y1 = ys[j + 1] - COL_D * 0.6
            if y1 - y0 < 0.8:
                continue
            objs.append(chuang_side(f"窗山_{x:.1f}_{j}", y0, y1, z_bot, z_top, x))
    return objs


# --------------------------------------------------------------------------- #
#  明间门
# --------------------------------------------------------------------------- #
def build_door(tops, open_angle=62.0):
    """明间双扇板门，半开（原画中门内可见人影与内室）。"""
    objs = []
    xs, ys = T.col_x(), T.col_y()
    z_lane = min(t[2] for t in tops.values()) - T.lane_h
    z_top = z_lane - 0.10
    z_bot = z_top - T.win_h - 0.42
    y = ys[0]                      # 前檐

    x0, x1 = xs[1] + COL_D * 0.5, xs[2] - COL_D * 0.5
    w = x1 - x0
    hgt = z_top - z_bot

    # 门框
    fr = 0.20
    objs.append(C.box("门框_下", w, 0.16, fr, loc=((x0 + x1) / 2, y, z_bot + fr / 2)))
    objs.append(C.box("门框_上", w + 0.3, 0.20, fr, loc=((x0 + x1) / 2, y, z_top - fr / 2)))
    objs.append(C.box("门框_左", fr, 0.16, hgt + fr, loc=(x0 + fr / 2, y, z_bot + hgt / 2)))
    objs.append(C.box("门框_右", fr, 0.16, hgt + fr, loc=(x1 - fr / 2, y, z_bot + hgt / 2)))

    # 两扇门扉：先在「铰边在原点、门扇沿 +X 伸出」的局部坐标里建好，
    # 再整体绕 Z 旋转并平移到铰位 —— 免得逐件算旋转后的坐标。
    leaf_w = (w - 2 * fr) / 2
    for s in (-1, 1):
        hinge_x = x0 + fr + (0.0 if s > 0 else leaf_w)
        parts = [C.box("扉板", leaf_w, 0.10, hgt, loc=(leaf_w / 2, 0.0, 0.0)),
                 C.box("门轴", 0.10, 0.17, hgt, loc=(0.02, 0.0, 0.0))]
        for ri in range(5):
            for ci in range(3):
                dx = leaf_w * (0.22 + ci * 0.28)
                dz = (ri - 2) * (hgt * 0.15)
                parts.append(C.prism(f"钉{ri}{ci}",
                                     [(math.cos(a) * 0.048, math.sin(a) * 0.048)
                                      for a in [k * math.pi / 4 for k in range(8)]],
                                     0.055, axis="Y", offset=-0.078))
                parts[-1].location = (dx, 0.0, dz)
        leaf = C.join(parts, f"门扇{s}")
        # 右扇向左开、左扇向右开：都朝室内（-Y）方向敞开
        leaf.rotation_euler = (0.0, 0.0, math.radians(-s * open_angle))
        leaf.location = (hinge_x, y, z_bot + hgt / 2)
        objs.append(leaf)
    return objs


def build_partition(tops, z_floor):
    """室内板壁：横在次间之后，免得从破子棂窗一眼看穿整座楼。

    明间留空 —— 原画中明间门内可见内室与人影，需要透。
    """
    objs = []
    xs, ys = T.col_x(), T.col_y()
    z_top = min(t[2] for t in tops.values()) - T.lane_h - 0.10
    y = 0.0
    for i in (0, 2):
        x0, x1 = xs[i] + COL_D * 0.5, xs[i + 1] - COL_D * 0.5
        objs.append(C.box(f"板壁_{i}", x1 - x0, 0.10, z_top - z_floor,
                          loc=((x0 + x1) / 2, y, (z_floor + z_top) / 2)))
        # 板壁上的竖向拼板线，与原画木壁的画法相合
        n = max(2, int((x1 - x0) / 0.42))
        for k in range(1, n):
            x = x0 + (x1 - x0) * k / n
            objs.append(C.box(f"板壁缝_{i}_{k}", 0.05, 0.13, z_top - z_floor,
                              loc=(x, y, (z_floor + z_top) / 2)))
    # 进深方向的隔断，围出明间的内室
    for x in (xs[1], xs[2]):
        objs.append(C.box(f"内室隔断_{x:.1f}", 0.12, T.dep_bay * 2.0,
                          z_top - z_floor,
                          loc=(x, 0.0, (z_floor + z_top) / 2)))
    return objs


# --------------------------------------------------------------------------- #
#  平坐
# --------------------------------------------------------------------------- #
def build_pingzuo(platform_top):
    """平坐：自城台顶向上叠置，返回 (构件表, 楼板面标高)。

    叠置次序（自下而上）：平坐斗 → 地栿 → 雁翅板 → 楼板。
    勾栏（railing.py）坐在楼板面上，故本函数必须返回楼板面标高，
    不能反过来由调用方假定 —— 否则勾栏会被埋进城台里。
    """
    objs = []
    hw = T.total_w() / 2.0 + T.plinth_over
    hd = T.total_d() / 2.0 + T.plinth_over
    dou_h, diban_h = 0.22, 0.18
    band = T.plinth_band_h

    z = platform_top
    z_dou = z
    z = z + dou_h
    z_diban = z
    z = z + diban_h
    z_band = z
    z = z + band
    z_floor = z + T.plinth_floor_t

    # 平坐斗（平坐铺作的简化表达）
    n = max(1, int(hw * 2 / 1.05))
    for i in range(n + 1):
        x = -hw + i * (hw * 2 / n)
        for y in (-hd + 0.34, hd - 0.34):
            objs.append(C.frustum(f"平坐斗_{i}_{y:.1f}", 0.30, 0.30, 0.44, 0.44,
                                  dou_h, z0=z_dou, loc=(x, y)))
    m = max(1, int(hd * 2 / 1.05))
    for j in range(m + 1):
        y = -hd + j * (hd * 2 / m)
        for x in (-hw + 0.34, hw - 0.34):
            objs.append(C.frustum(f"平坐斗山_{j}_{x:.1f}", 0.30, 0.30, 0.44, 0.44,
                                  dou_h, z0=z_dou, loc=(x, y)))

    # 地栿 / 雁翅板 / 楼板
    objs += [
        C.box("地平栿前", hw * 2 + 0.2, 0.20, diban_h, loc=(0, -hd, z_diban + diban_h / 2)),
        C.box("地平栿后", hw * 2 + 0.2, 0.20, diban_h, loc=(0, hd, z_diban + diban_h / 2)),
        C.box("地平栿左", 0.20, hd * 2 + 0.2, diban_h, loc=(-hw, 0, z_diban + diban_h / 2)),
        C.box("地平栿右", 0.20, hd * 2 + 0.2, diban_h, loc=(hw, 0, z_diban + diban_h / 2)),
        C.box("雁翅板前", hw * 2, 0.14, band, loc=(0, -hd, z_band + band / 2)),
        C.box("雁翅板后", hw * 2, 0.14, band, loc=(0, hd, z_band + band / 2)),
        C.box("雁翅板左", 0.14, hd * 2, band, loc=(-hw, 0, z_band + band / 2)),
        C.box("雁翅板右", 0.14, hd * 2, band, loc=(hw, 0, z_band + band / 2)),
        C.box("平坐楼板", hw * 2, hd * 2, T.plinth_floor_t,
              loc=(0, 0, z_floor - T.plinth_floor_t / 2)),
    ]
    return objs, z_floor


# --------------------------------------------------------------------------- #
#  汇总
# --------------------------------------------------------------------------- #
def build_all(floor_z, out=None):
    """楼身整体。floor_z 为平坐楼板面标高（= 城台顶 + 平坐高）。"""
    log = out.append if out is not None else (lambda s: None)
    objs = []

    top_z = floor_z + T.plinth_h
    cols, tops = build_columns(z0=top_z)
    objs += cols
    log(f"  檐柱 {len(T.col_x())}×{len(T.col_y())} = {len(cols)//2} 根")

    objs += lane_and_pupai(tops)
    objs += build_windows(tops)
    objs += build_door(tops)
    objs += build_partition(tops, floor_z + T.plinth_h)

    z_pupai = pupai_z(tops)
    log(f"  平坐面 {floor_z:.2f}  柱头 {max(t[2] for t in tops.values()):.2f}"
        f"  普拍枋上皮 {z_pupai:.2f}")
    return objs, z_pupai, tops
