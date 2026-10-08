# -*- coding: utf-8 -*-
"""屋顶 —— 单檐歇山顶。

原画 crops/A_roof.png / E_topleft.png / F_roofright.png 所示：
正脊两端鸱吻，垂脊沿山花边缘下行，戗脊自收山点斜下至翼角，
翼角明显起翘冲出，屋面布满筒瓦垄，檐口一线瓦当滴水，
山花面装博风板、悬鱼，各脊均列蹲兽。

几何构成（歇山顶 = 庑殿顶被两个竖直山花面截断）：
    前后坡   主坡面，平面为「矩形 + 下接梯形」
    撒头     两端小坡面，自山花下缘斜下至端部檐口
    山花     两片竖直三角形，位于 x = ±正脊长/2
四片曲面两两共边，标高统一由举折曲线 R(d) 给出，天然连续。

标高由檐口起算：z = H_eave + R(d)，d 为自檐口沿坡向上的水平距离。
檐口标高取自铺作层顶（撩檐枋上皮），故屋顶与斗拱自动对位。
"""
import math

from .. import common as C

R = C.Roof


# --------------------------------------------------------------------------- #
#  控制曲线
# --------------------------------------------------------------------------- #
def half_w():
    return R.plan_w() / 2.0


def half_d():
    return R.plan_d() / 2.0


def half_ridge():
    return R.ridge_len / 2.0


def y_shou():
    """收山：垂脊下端在进深方向的位置。"""
    return R.shoushan * half_d()


def rise(d):
    """举折曲线。d 自檐口沿坡向上量；至 d = half_d() 处举足 rise_total。

    指数 > 1 使屋面凹曲（脊部陡、檐部缓），即《营造法式》「举折」之形。
    """
    t = min(1.0, max(0.0, d / half_d()))
    return R.rise_total * (t ** R.juzhe)


def z_eave():
    return R.eave_z


def z_at(y):
    """前后坡在进深坐标 y 处的标高。"""
    return z_eave() + rise(y + half_d())


def hip_x(y):
    """戗脊在进深 y 处的平面横向位置（自收山点连至翼角）。"""
    yg = y_shou()
    if y >= -yg:
        return half_ridge()
    k = (-y - yg) / (half_d() - yg)
    return half_ridge() + (half_w() - half_ridge()) * k


def corner_lift(t):
    """翼角起翘系数。t 为自檐口中部量向角部的比例（0 中部，1 角部）。"""
    a = max(0.0, (t - (1.0 - R.corner_span)) / R.corner_span)
    return C.smoothstep(a)


def eave_mod(x, y, t_corner):
    """对檐口附近的点做「起翘 + 冲出」。返回 (dx, dy, dz)。"""
    k = corner_lift(t_corner)
    if k <= 0.0:
        return 0.0, 0.0, 0.0
    sx = math.copysign(1.0, x) if x else 1.0
    sy = math.copysign(1.0, y) if y else 1.0
    return sx * R.tilt_out * k, sy * R.tilt_out * k * 0.4, R.tilt_lift * k


# --------------------------------------------------------------------------- #
#  瓦垄
# --------------------------------------------------------------------------- #
def tile_dz(phase_coord, pitch=None, radius=None):
    """筒瓦垄剖面：一个周期内 58% 为半圆筒瓦，其余为板瓦平段。"""
    p = R.tile_pitch if pitch is None else pitch
    r = R.tile_r if radius is None else radius
    s = (phase_coord / p) % 1.0
    if s < 0.58:
        u = (s / 0.58) * 2.0 - 1.0          # -1..1
        return r * math.sqrt(max(0.0, 1.0 - u * u))
    # 板瓦：略微下凹
    return -0.16 * r


def _tile_offsets(rows, phase_of, normals=None):
    """按曲面法线把瓦垄起伏加到网格点上。phase_of(i, j) 给出平面坐标。"""
    nv = len(rows)
    nu = len(rows[0])
    out = []
    for j in range(nv):
        row = []
        for i in range(nu):
            p = rows[j][i]
            # 用相邻点做差分求法线
            p_u = rows[j][min(i + 1, nu - 1)]
            p_um = rows[j][max(i - 1, 0)]
            p_v = rows[min(j + 1, nv - 1)][i]
            p_vm = rows[max(j - 1, 0)][i]
            du = _sub(p_u, p_um)
            dv = _sub(p_v, p_vm)
            n = _cross(dv, du)          # 向上/向外
            ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
            if ln < 1e-9:
                n = (0.0, 0.0, 1.0)
            else:
                n = (n[0] / ln, n[1] / ln, n[2] / ln)
            if n[2] < 0:
                n = (-n[0], -n[1], -n[2])
            dz = tile_dz(phase_of(p[0], p[1]))
            row.append((p[0] + n[0] * dz, p[1] + n[1] * dz, p[2] + n[2] * dz))
        out.append(row)
    return out


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


# --------------------------------------------------------------------------- #
#  主体曲面
# --------------------------------------------------------------------------- #
NU_TILES = 6          # 每个瓦垄周期的采样点数


def _main_slope(front=True, nv=34):
    """前后坡：v 自檐口(0)到正脊(1)。"""
    sgn = -1.0 if front else 1.0        # 前坡在 -Y 一侧
    hd, hw, hr = half_d(), half_w(), half_ridge()
    yg = y_shou()
    nu = int(2 * hw / R.tile_pitch * NU_TILES) + 1
    vg = (hd - yg) / hd            # 收山点所在的 v

    vs = sorted(set([i / (nv - 1) for i in range(nv)] + [vg]))
    rows = []
    total_v = len(vs) - 1
    for vi, v in enumerate(vs):
        y = sgn * (hd - v * hd)    # v=0 -> 檐口, v=1 -> 正脊
        # 自檐口向收山点线性内插半宽，保证与撒头共边
        if v <= vg and vg > 0:
            hwid = hw + (hr - hw) * (v / vg)
        else:
            hwid = hr
        z0 = z_eave() + rise(v * hd)
        row = []
        for i in range(nu):
            u = i / (nu - 1)
            x = -hwid + 2 * hwid * u
            # 翼角：只作用于靠近檐口、且靠近角部的区域
            tc = abs(x) / hw
            decay = max(0.0, 1.0 - v / max(1e-6, vg * 0.85))
            dx, dy, dz = eave_mod(x, y, tc)
            row.append((x + dx * decay, y + dy * decay, z0 + dz * decay))
        rows.append(row)

    def phase(x, y):
        return x                    # 瓦垄平行于正脊方向排列

    return _tile_offsets(rows, phase), vs, hw, hr, vg


def _saotou(side=1, nt=20, nw=None):
    """撒头：两端的坡面，自山花下缘斜降至端部檐口。

    注意镜像轴是 X —— 两个撒头分居 ±X 两端；进深方向始终铺满。
    进深采样需按瓦垄周期取够点数，否则瓦垄欠采样会糊成乱纹。
    """
    hd, hw, hr = half_d(), half_w(), half_ridge()
    yg = y_shou()
    if nw is None:
        nw = int(2 * hd / R.tile_pitch * NU_TILES)
    rows = []
    for ti in range(nt + 1):
        t = ti / nt
        x = side * (hr + (hw - hr) * t)
        yd = yg + (hd - yg) * t
        row = []
        for wi in range(nw + 1):
            w = wi / nw
            y = -yd + 2 * yd * w
            z0 = z_eave() + rise(y + hd) * (1.0 - t)
            # 翼角只在角部起翘 —— 此处靠近角部的程度由 |y|/hd 决定，与 t 无关
            tc = abs(y) / hd
            dx, dy, dz = eave_mod(x, y, tc)
            decay = 1.0 - t * 0.15
            row.append((x + dx * decay, y + dy * decay, z0 + dz * decay))
        rows.append(row)

    def phase(x, y):
        return y                    # 撒头的瓦垄平行于端部檐口

    return _tile_offsets(rows, phase)


def _gable(side=1, n=22):
    """山花：x = ±正脊长/2 处的竖直三角形面板（略向内收，遮住接缝）。

    分成左右两半各铺一列四边形，避免退化成细长三角被 Freestyle 画成一团碎线。
    """
    hr, yg = half_ridge(), y_shou()
    x = side * hr * 0.995
    z_apex = z_eave() + R.rise_total
    z_base = z_eave() + rise(half_d() - yg)

    def pt(t, yy):
        return (x, yy * yg, z_base + (z_apex - z_base) * t)

    verts = [(x, 0.0, z_apex), (x, -yg, z_base), (x, yg, z_base)]
    faces = [[0, 1, 2]]
    return C.new_obj(f"山花{'右' if side > 0 else '左'}", verts, faces,
                     collection="GateTower")


# --------------------------------------------------------------------------- #
#  脊与脊饰
# --------------------------------------------------------------------------- #
def bar_along(name, pts, w, h, col="GateTower", taper_top=0.62):
    """沿折线放样一根带收分的脊（正脊、垂脊、戗脊通用）。"""
    rows = []
    n = len(pts)
    for i in range(n):
        p = pts[i]
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        d = _sub(b, a)
        ln = math.sqrt(d[0] ** 2 + d[1] ** 2)
        if ln < 1e-9:
            sx, sy = 1.0, 0.0
        else:
            sx, sy = -d[1] / ln, d[0] / ln     # 水平法向
        rows.append([
            (p[0] - sx * w / 2, p[1] - sy * w / 2, p[2]),
            (p[0] + sx * w / 2, p[1] + sy * w / 2, p[2]),
            (p[0] + sx * w * taper_top / 2, p[1] + sy * w * taper_top / 2, p[2] + h * 0.55),
            (p[0] - sx * w * taper_top / 2, p[1] - sy * w * taper_top / 2, p[2] + h * 0.55),
            (p[0], p[1], p[2] + h),
        ])
    return C.grid_obj(name, rows, cap_first=True, cap_last=True, collection=col)


def chiwen_profile():
    """鸱吻侧视轮廓：自吻座升起，头向内卷曲。坐标 (沿脊向内的距离, 高出正脊)。"""
    return [
        (0.00, 0.00), (0.10, 0.21), (0.14, 0.46), (0.08, 0.74),
        (-0.06, 0.92), (-0.32, 1.04), (-0.50, 0.94), (-0.40, 0.80),
        (-0.56, 0.67), (-0.52, 0.48), (-0.58, 0.30), (-0.48, 0.09),
        (-0.50, 0.00),
    ]


def ridge_and_ornaments():
    """正脊 + 鸱吻 + 垂脊 + 戗脊 + 蹲兽 + 博风板 + 悬鱼。"""
    objs = []
    hr, yg = half_ridge(), y_shou()
    hd, hw = half_d(), half_w()
    z_apex = z_eave() + R.rise_total
    z_base = z_eave() + rise(hd - yg)

    # ---- 正脊 --------------------------------------------------------- #
    zr = z_apex + R.ridge_h / 2
    objs.append(bar_along("正脊", [(-hr, 0, zr), (hr, 0, zr)],
                          R.ridge_t, R.ridge_h))

    # ---- 鸱吻（正脊两端，向内卷） ------------------------------------- #
    prof = chiwen_profile()
    for s in (-1, 1):
        pts = [(s * (hr + dx), z_apex + dz) for (dx, dz) in prof]
        objs.append(C.prism(f"鸱吻{'右' if s > 0 else '左'}", pts, 0.38, axis="Y"))

    # ---- 垂脊 / 戗脊 + 蹲兽 ------------------------------------------- #
    for s in (-1, 1):
        # 垂脊：正脊端 -> 收山点（位于山花面内）
        chui = [(s * hr, 0.0, z_apex), (s * hr, s * 0.35 * yg, z_apex - 0.12),
                (s * hr, s * yg, z_base)]
        objs.append(bar_along(f"垂脊{'右' if s > 0 else '左'}", chui,
                              R.wd_t, R.wd_h))
        # 戗脊：收山点 -> 翼角
        x_c = hw
        y_c = s * hd
        _, _, dz_c = eave_mod(hw * 0.999, y_c, 1.0)
        qiang = [(s * hr, s * yg, z_base),
                 (s * (hr + (hw - hr) * 0.42), s * (yg + (hd - yg) * 0.42),
                  z_base + (z_eave() + dz_c - z_base) * 0.42),
                 (s * (hw - 0.35), s * (hd - 0.20), z_eave() + dz_c * 0.86),
                 (s * x_c, y_c, z_eave() + dz_c)]
        objs.append(bar_along(f"戗脊{'右' if s > 0 else '左'}", qiang,
                              R.wd_t, R.wd_h))
        # 蹲兽：沿戗脊排列（原画中戗脊上那一串小兽）
        for k, tt in enumerate((0.30, 0.46, 0.62, 0.78)):
            idx = tt * (len(qiang) - 1)
            i0 = int(idx)
            f = idx - i0
            i1 = min(i0 + 1, len(qiang) - 1)
            p = tuple(qiang[i0][j] + (qiang[i1][j] - qiang[i0][j]) * f for j in range(3))
            objs.append(dunshou(f"蹲兽{s}{k}", p, s))

    # ---- 博风板 + 悬鱼 ------------------------------------------------- #
    for s in (-1, 1):
        xb = s * hr
        # 博风板沿山花两条斜边，板面垂直于进深方向、略外挑
        for side in (-1, 1):
            pts = [(xb + s * 0.10, 0.0, z_apex + 0.06),
                   (xb + s * 0.06, side * yg * 0.5, z_base + (z_apex - z_base) * 0.52),
                   (xb + s * 0.02, side * yg, z_base + 0.02)]
            objs.append(bar_along(f"博风板{s}{side}", pts, R.bofeng_t,
                                  (z_apex - z_base) * 0.30 + 0.26))
        # 悬鱼：悬于山花顶点下方的鱼形饰
        xf = xb + s * 0.20
        top = z_apex - 0.10
        fish = [
            (0.00, top), (0.20, top - 0.22), (0.24, top - 0.58),
            (0.10, top - 0.92), (0.00, top - 1.06), (-0.10, top - 0.92),
            (-0.24, top - 0.58), (-0.20, top - 0.22),
        ]
        objs.append(C.prism(f"悬鱼{'右' if s > 0 else '左'}",
                            [(y, z) for (y, z) in fish], 0.10, axis="X",
                            offset=xf))
    return objs


def dunshou(name, p, side):
    """蹲兽：戗脊上的小兽，由身、头、尾三块概括而成。"""
    x, y, z = p
    s = 0.16
    objs = [
        C.box(f"{name}_身", 2.1 * s, 1.0 * s, 0.9 * s, loc=(x, y, z + 0.9 * s)),
        C.box(f"{name}_头", 1.0 * s, 0.9 * s, 0.9 * s,
              loc=(x + side * 0.9 * s, y, z + 1.75 * s)),
        C.box(f"{name}_尾", 0.8 * s, 0.6 * s, 1.3 * s,
              loc=(x - side * 1.3 * s, y, z + 1.5 * s)),
    ]
    return C.join(objs, name)


# --------------------------------------------------------------------------- #
#  檐口：瓦当 + 滴水
# --------------------------------------------------------------------------- #
def _disc_prof(radius, n=16):
    return [(math.cos(k * 2 * math.pi / n) * radius,
             math.sin(k * 2 * math.pi / n) * radius) for k in range(n)]


def _drip_prof(w=0.09, drop=0.20):
    """滴水：上宽下尖的下垂舌片（局部坐标，顶边在 z=0）。"""
    return [(-w, 0.0), (w, 0.0), (w * 0.55, -drop), (-w * 0.55, -drop)]


def eave_tiles():
    """檐口一线：每垄筒瓦端头加瓦当（圆盘），垄间加滴水。"""
    objs = []
    hw, hd = half_w(), half_d()
    z = z_eave()
    r = R.tile_r * 0.92

    # ---- 前后檐 ------------------------------------------------------- #
    n = int(2 * hw / R.tile_pitch)
    for i in range(n + 1):
        x = -hw + i * R.tile_pitch
        for sgn in (-1, 1):
            y = sgn * hd
            dx, dy, dz = eave_mod(x, y, abs(x) / hw)
            px, py, pz = x + dx, y + dy, z + dz
            ob = C.prism(f"瓦当{i}_{sgn}", _disc_prof(r), 0.07, axis="Y")
            ob.location = (px, py + sgn * 0.03, pz + R.tile_r * 0.06)
            objs.append(ob)
            ob2 = C.prism(f"滴水{i}_{sgn}", _drip_prof(), 0.06, axis="Y")
            ob2.location = (px + R.tile_pitch * 0.5, py + sgn * 0.02, pz - 0.01)
            objs.append(ob2)

    # ---- 两山檐口（撒头一侧） ----------------------------------------- #
    n2 = int(2 * hd / R.tile_pitch)
    for i in range(n2 + 1):
        y = -hd + i * R.tile_pitch
        for sgn in (-1, 1):
            x = sgn * hw
            dx, dy, dz = eave_mod(x, y, abs(y) / hd)
            px, py, pz = x + dx, y + dy, z + dz
            ob = C.prism(f"瓦当端{i}_{sgn}", _disc_prof(r), 0.07, axis="X")
            ob.location = (px + sgn * 0.03, py, pz + R.tile_r * 0.06)
            objs.append(ob)
            ob2 = C.prism(f"滴水端{i}_{sgn}", _drip_prof(), 0.06, axis="X")
            ob2.location = (px + sgn * 0.02, py + R.tile_pitch * 0.5, pz - 0.01)
            objs.append(ob2)
    return objs


# --------------------------------------------------------------------------- #
#  角梁
# --------------------------------------------------------------------------- #
def corner_beams():
    """角梁：贴着戗脊下方走，自收山点撑到翼角尖端（原画中檐角下的斜梁）。"""
    objs = []
    hw, hd, hr, yg = half_w(), half_d(), half_ridge(), y_shou()
    z_base = z_eave() + rise(hd - yg)
    _, _, dz_corner = eave_mod(hw, hd, 1.0)
    z_corner = z_eave() + dz_corner
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts = [
                (sx * hr * 0.98, sy * yg * 0.98, z_base - 0.32),
                (sx * (hr + (hw - hr) * 0.45), sy * (yg + (hd - yg) * 0.45),
                 z_base - 0.32 + (z_corner - 0.30 - (z_base - 0.32)) * 0.45),
                (sx * (hw - 0.22), sy * (hd - 0.22), z_corner - 0.30),
            ]
            objs.append(bar_along(f"角梁{sx}{sy}", pts, 0.30, 0.46))
    return objs


# --------------------------------------------------------------------------- #
#  汇总
# --------------------------------------------------------------------------- #
def build_all(eave_z, out=None):
    """生成整座屋顶。eave_z 为檐口标高（来自铺作层顶）。"""
    R.eave_z = eave_z
    log = out.append if out is not None else (lambda s: None)

    objs = []
    for front in (True, False):
        rows, vs, hw, hr, vg = _main_slope(front)
        nm = "前坡" if front else "后坡"
        objs.append(C.grid_obj(nm, rows, collection="GateTower"))
        log(f"  {nm}: {len(rows)}x{len(rows[0])} 点")
    for s in (-1, 1):
        objs.append(C.grid_obj(f"撒头{'右' if s > 0 else '左'}", _saotou(s),
                               flip=(s < 0), collection="GateTower"))
        objs.append(_gable(s))
    objs += ridge_and_ornaments()
    objs += eave_tiles()
    objs += corner_beams()
    log(f"  屋顶构件 {len(objs)} 件")
    return objs
