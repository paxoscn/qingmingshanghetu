# -*- coding: utf-8 -*-
"""勾栏 —— 宋式木栏杆。

原画 crops/B_dougong.png（平坐勾栏）、crops/D_stairs.png（踏道勾栏）中，
自下而上可辨认出五件：
    地栿  —— 底部通长横木
    华版  —— 地栿之上的装饰栏板（原画中带云纹）
    蜀柱  —— 短柱，柱身作「瘿项」（中部收细）
    云栱  —— 蜀柱之上的云头小栱，承寻杖
    寻杖  —— 最上通长扶手
每隔一段设望柱（柱头作圆头），望柱比寻杖略高。

本模块沿任意折线布置，故平坐勾栏与踏道斜勾栏共用同一套代码。
"""
import math

from .. import common as C

RG = C.Railing

PI8 = [k * math.pi / 8 for k in range(16)]


def _bar3(name, x0, y0, za, x1, y1, zb, w, h):
    """沿 3D 直线的一段构件，断面 w×h（可倾斜，用于踏道斜勾栏）。"""
    dx, dy, dz = x1 - x0, y1 - y0, zb - za
    horiz = math.hypot(dx, dy)
    ln = math.hypot(horiz, dz)
    ob = C.box(name, ln, w, h, loc=(0, 0, 0))
    # Blender 欧拉序为 XYZ（R = Rz·Ry·Rx）：先绕 Y 抬头，再绕 Z 转向
    ob.rotation_euler = (0.0, -math.atan2(dz, horiz), math.atan2(dy, dx))
    ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, (za + zb) / 2)
    return ob


def _bar(name, p0, p1, w, h, z_off=0.0, z_off1=None):
    """沿 (p0 -> p1) 的一段构件，断面 w×h，中心抬高 z_off。"""
    z1 = z_off if z_off1 is None else z_off1
    return _bar3(name, p0[0], p0[1], z_off, p1[0], p1[1], z1, w, h)


def wangzhu(name, x, y, z0, h=None, d=None):
    """望柱：柱头作圆头，柱身略收。"""
    h = RG.wangzhu_h if h is None else h
    d = RG.wangzhu_d if d is None else d
    parts = [C.box(f"{name}_身", d, d, h * 0.86, loc=(x, y, z0 + h * 0.43))]
    head = C.prism(f"{name}_头",
                   [(math.cos(a) * d * 0.72, math.sin(a) * d * 0.72) for a in PI8],
                   d * 1.1, axis="Z")
    head.location = (x, y, z0 + h * 0.86)
    parts.append(head)
    return C.join(parts, name)


def shuzhu(name, x, y, z0, h, d=None):
    """蜀柱：短柱，中部收细作「瘿项」。"""
    d = RG.shuzhu_w if d is None else d
    rows = []
    for i in range(7):
        t = i / 6
        r = d / 2 * (0.72 + 0.28 * abs(2 * t - 1) ** 0.7)
        rows.append([(x + math.cos(a) * r, y + math.sin(a) * r, z0 + h * t)
                     for a in PI8])
    return C.grid_obj(name, rows, close_u=True, cap_first=True, cap_last=True,
                      collection="GateTower")


def yungong(name, x, y, z0, w=None, h=0.20, along_x=True):
    """云栱：蜀柱之上的云头小栱，两端上卷。"""
    w = RG.yungong_w if w is None else w
    prof = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h * 0.45),
            (w * 0.30, h * 0.62), (w * 0.16, h),
            (-w * 0.16, h), (-w * 0.30, h * 0.62), (-w / 2, h * 0.45)]
    ob = C.prism(name, prof, 0.13, axis="Y" if along_x else "X")
    ob.location = (x, y, z0)
    return ob


def huaban(name, x0, y0, x1, y1, z0, h=None):
    """华版：地栿之上的装饰栏板。"""
    h = RG.huaban_h if h is None else h
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    ob = C.box(name, ln, 0.09, h, loc=(0, 0, 0))
    ob.rotation_euler = (0.0, 0.0, math.atan2(dy, dx))
    ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, z0 + h / 2)
    return ob


def run(name, p0, p1, z0, z1=None, wangzhu_step=None, huaban=True, scale=1.0):
    """沿一条直线段做一跑勾栏。p0/p1 为 (x, y)，z0 为起端地栿底标高。

    z1 给出时该跑勾栏沿长度倾斜（踏道勾栏），否则为水平。
    """
    objs = []
    x0, y0 = p0
    x1, y1 = p1
    z1 = z0 if z1 is None else z1
    ln = math.hypot(x1 - x0, y1 - y0)
    if ln < 0.35:
        return objs
    ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
    dz = z1 - z0

    def zz(t):
        return z0 + dz * t

    step = RG.wangzhu_gap if wangzhu_step is None else wangzhu_step
    step *= scale

    # 地栿
    objs.append(_bar(f"{name}_地栿", p0, p1, RG.diban_t, RG.diban_h,
                     z0 + RG.diban_h / 2, z1 + RG.diban_h / 2))

    # 华版（斜跑时按中段高度放置，避免与地栿脱开）
    if huaban:
        z_hb0 = z0 + RG.diban_h
        z_hb1 = z1 + RG.diban_h
        dx, dy = x1 - x0, y1 - y0
        ln2 = math.hypot(dx, dy)
        ob = C.box(f"{name}_华版", ln2 - 0.24, 0.09, RG.huaban_h * scale, loc=(0, 0, 0))
        ob.rotation_euler = (0.0, -math.atan2(z_hb1 - z_hb0, ln2), math.atan2(dy, dx))
        ob.location = ((x0 + x1) / 2, (y0 + y1) / 2,
                       (z_hb0 + z_hb1) / 2 + RG.huaban_h * scale / 2)
        objs.append(ob)
        z_shu_off = RG.diban_h + RG.huaban_h * scale
    else:
        z_shu_off = RG.diban_h

    h_shu = max(0.18, RG.h_xunzhang * scale - z_shu_off - 0.16 * scale)

    # 蜀柱 + 云栱
    n = max(1, int(ln / (step * 0.5)))
    for k in range(n + 1):
        t = k / n
        x, y = x0 + ux * ln * t, y0 + uy * ln * t
        zs = zz(t) + z_shu_off
        objs.append(shuzhu(f"{name}_蜀柱{k}", x, y, zs, h_shu,
                           d=RG.shuzhu_w * scale))
        objs.append(yungong(f"{name}_云栱{k}", x, y, zs + h_shu,
                            w=RG.yungong_w * scale, h=0.20 * scale,
                            along_x=abs(ux) > abs(uy)))

    # 寻杖（扶手）
    objs.append(_bar(f"{name}_寻杖", p0, p1, RG.xunzhang_d, RG.xunzhang_d,
                     z0 + RG.h_xunzhang * scale, z1 + RG.h_xunzhang * scale))

    # 望柱
    nw = max(1, int(round(ln / step)))
    for k in range(nw + 1):
        t = k / nw
        x, y = x0 + ux * ln * t, y0 + uy * ln * t
        objs.append(wangzhu(f"{name}_望柱{k}", x, y, zz(t),
                            h=RG.wangzhu_h * scale, d=RG.wangzhu_d * scale))
    return objs


def rect(name, x0, y0, x1, y1, z0, closed=True, **kw):
    """矩形一圈勾栏。"""
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    objs = []
    n = len(corners) if closed else len(corners) - 1
    for i in range(n):
        p0 = corners[i]
        p1 = corners[(i + 1) % len(corners)]
        objs += run(f"{name}{i}", p0, p1, z0, **kw)
    return objs
