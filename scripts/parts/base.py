# -*- coding: utf-8 -*-
"""城台、门洞、门扉、门额、踏道。

对应原画 crops/C_gate.png（门洞）、crops/D_stairs.png（踏道）、crops/4_base_wall.png（城台墙面）：
    城台为夯土包砖的方台，四面明显收分（下大上小）；
    门洞是「圭形过梁式」—— 两壁向上斜收，顶上压一道木过梁，不是券顶；
    过梁之上安四枚门簪，再上悬门额匾；
    门扉两扇向内敞开，贴靠门洞两壁（原画中门洞内那两条深色竖带即此）；
    城台侧面附踏道，两侧围勾栏，转折登城。

墙面那一片斜向排线即原画的城砖画法，由 materials.py 的 hatch 层复现。
"""
import math

from .. import common as C
from . import railing as RL

B = C.Base
G = C.Gate
S = C.Stair


# --------------------------------------------------------------------------- #
#  城台
# --------------------------------------------------------------------------- #
def build_platform():
    """城台本体：带收分的方台，中间挖出圭形门洞。"""
    ob = C.frustum("城台", B.width, B.depth, B.top_width(), B.top_depth(), B.height,
                   z0=0.0)

    # ---- 门洞挖切体：圭形断面沿进深方向拉通 --------------------------- #
    wb, wt, h = G.w_bottom, G.w_top, G.h_clear
    prof = [(-wb / 2, -1.2), (wb / 2, -1.2), (wb / 2, 0.0),
            (wt / 2, h), (-wt / 2, h), (-wb / 2, 0.0)]
    cutter = C.prism("门洞挖切", prof, B.depth + 4.0, axis="Y", offset=0.0)
    C.boolean_diff(ob, cutter)

    # ---- 门洞内壁换用暗墨材质 ----------------------------------------- #
    me = ob.data
    me.materials.append(bpy_mat("城台外"))
    me.materials.append(bpy_mat("门洞内"))
    for p in me.polygons:
        c = p.center
        n = p.normal
        inside = (abs(c.x) < wt / 2 + 0.10 and -0.15 < c.z < h + 0.15
                  and abs(c.y) < B.depth / 2 - 0.15)
        if inside and abs(n.y) < 0.85:
            p.material_index = 1
    return ob


def bpy_mat(name):
    import bpy
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    return m


def platform_top():
    return B.height


# --------------------------------------------------------------------------- #
#  门洞细部：过梁、门簪、门额匾、门扉
# --------------------------------------------------------------------------- #
def gate_details(top_z):
    objs = []
    wb, wt, h = G.w_bottom, G.w_top, G.h_clear
    y_front = -B.depth / 2.0

    # ---- 过梁（木大梁，压在两壁收分之上） ----------------------------- #
    lintel = C.box("过梁", wt + 1.6, G.lintel_d, G.lintel_h,
                   loc=(0, y_front + 0.45, h + G.lintel_h / 2))
    objs.append(lintel)

    # ---- 门簪（过梁上前挑的四枚木栓） --------------------------------- #
    for i in range(G.stud_n):
        x = (i - (G.stud_n - 1) / 2) * (G.plaque_w * 0.72 / max(1, G.stud_n - 1))
        ob = C.prism(f"门簪{i}",
                     [(math.cos(a) * G.stud_d / 2, math.sin(a) * G.stud_d / 2)
                      for a in [k * math.pi / 4 for k in range(8)]],
                     G.stud_l, axis="Y", offset=y_front + G.stud_l / 2)
        ob.location = (x, 0, h + G.lintel_h + G.stud_d / 2)
        objs.append(ob)

    # ---- 门额匾：上缘外倾（宋式匾额悬于门额，向外仰） ---------------- #
    z0 = h + G.lintel_h + 0.30
    plaque_parts = []
    fw = 0.20
    plaque_parts.append(C.box("匾心", G.plaque_w, 0.10, G.plaque_h, loc=(0, 0, 0)))
    for sx in (-1, 1):
        plaque_parts.append(C.box(f"匾框{sx}", fw, 0.16, G.plaque_h + 2 * fw,
                                  loc=(sx * (G.plaque_w / 2 + fw / 2), 0, 0)))
    for sz in (-1, 1):
        plaque_parts.append(C.box(f"匾框{'上下'[sz > 0]}", G.plaque_w + 2 * fw, 0.16, fw,
                                  loc=(0, 0, sz * (G.plaque_h / 2 + fw / 2))))
    plaque = C.join(plaque_parts, "门额匾")
    plaque.rotation_euler = (G.plaque_tilt, 0.0, 0.0)
    plaque.location = (0, y_front + 0.42, z0 + G.plaque_h / 2)
    objs.append(plaque)

    # ---- 门扉：两扇向内敞开、贴靠门洞两壁 ----------------------------- #
    leaf_w, leaf_h, leaf_t = G.leaf_w, G.leaf_h, G.leaf_t
    for s in (-1, 1):
        hinge_x = s * (wb / 2 - 0.22)
        parts = [C.box("扉板", leaf_w, leaf_t, leaf_h, loc=(leaf_w / 2, 0, 0)),
                 C.box("门轴", 0.12, leaf_t * 1.5, leaf_h, loc=(0.03, 0, 0))]
        for ri in range(4):
            for ci in range(3):
                parts.append(C.prism(f"钉{ri}{ci}",
                                     [(math.cos(a) * 0.055, math.sin(a) * 0.055)
                                      for a in [k * math.pi / 4 for k in range(8)]],
                                     0.06, axis="Y", offset=-leaf_t / 2 - 0.03))
                parts[-1].location = (leaf_w * (0.22 + ci * 0.28), 0, (ri - 1.5) * leaf_h * 0.2)
        # 铺首衔环
        parts.append(C.box("铺首", 0.30, 0.06, 0.30,
                           loc=(leaf_w * 0.5, -leaf_t / 2 - 0.06, -leaf_h * 0.18)))
        leaf = C.join(parts, f"门扉{s}")
        # 内开约 100°，与门洞壁近平行
        leaf.rotation_euler = (0.0, 0.0, math.radians(-s * 102.0))
        leaf.location = (hinge_x, y_front + 0.30, leaf_h / 2)
        objs.append(leaf)
    return objs


# --------------------------------------------------------------------------- #
#  壁柱
# --------------------------------------------------------------------------- #
def pilasters():
    """城台四角及门洞两侧的竖向砖垛（原画中那几条明显的竖向明暗带）。"""
    objs = []
    out = 0.16
    for sx in (-1, 1):
        for sy in (-1, 1):
            # 角垛：沿收分斜面贴一条竖带
            rows = []
            n = 10
            for i in range(n + 1):
                t = i / n
                z = t * B.height
                xo = sx * (B.width / 2 - B.batter * z) + sx * out
                yo = sy * (B.depth / 2 - B.batter * z) + sy * out
                rows.append([(xo - sx * 0.30, yo, z), (xo, yo - sy * 0.30, z),
                             (xo, yo, z)])
            ob = C.grid_obj(f"角垛{sx}{sy}", rows, collection="GateTower")
            objs.append(ob)
    # 门洞两侧的竖带
    for s in (-1, 1):
        x0 = s * (G.w_bottom / 2 + 0.35)
        w = 0.85
        rows = []
        n = 10
        for i in range(n + 1):
            t = i / n
            z = t * G.h_clear * 0.92
            yo = -(B.depth / 2 - B.batter * z) - 0.14
            rows.append([(x0 - s * w / 2, yo, z), (x0, yo - 0.16, z),
                         (x0 + s * w / 2, yo, z)])
        objs.append(C.grid_obj(f"门侧竖带{s}", rows, collection="GateTower"))
    return objs


# --------------------------------------------------------------------------- #
#  踏道
# --------------------------------------------------------------------------- #
def stairs(side=-1):
    """城台侧面踏道：自前檐下起，沿进深方向登至城台顶。"""
    objs = []
    top = B.height
    n = int(math.ceil(top / S.riser))
    y0 = -B.depth / 2.0 + 0.4
    objs_steps = []
    for i in range(n):
        z = (i + 1) * S.riser
        ya = y0 + i * S.tread
        yb = ya + S.tread
        if yb > B.depth / 2.0:
            break
        # 内侧随城台收分后退，外侧保持铅直
        x_in = side * (B.width / 2 - B.batter * z)
        objs_steps.append(C.box(f"踏步{i}", S.width, S.tread, z,
                                loc=(x_in + side * S.width / 2,
                                     (ya + yb) / 2, z / 2)))
    objs += objs_steps
    steps = len(objs_steps)
    z_top = steps * S.riser
    y_top = y0 + steps * S.tread

    # ---- 勾栏（两侧斜跑） --------------------------------------------- #
    for e in (0, 1):
        xr = side * (B.width / 2) + side * (S.railing_inset + 0.14)
        if e == 1:
            xr = side * (B.width / 2 + S.width) - side * S.railing_inset
        objs += RL.run(f"踏道勾栏{e}", (xr, y0 - 0.6), (xr, y_top + 0.3),
                       0.0, z1=z_top + 0.3, scale=0.95)
    # ---- 顶部平台勾栏 ------------------------------------------------ #
    x_out = side * (B.width / 2 + S.width)
    objs += RL.run("踏道平台勾栏",
                   (side * (B.width / 2) + side * S.railing_inset, y_top),
                   (x_out - side * S.railing_inset, y_top),
                   z_top, scale=0.95)
    # ---- 踏道地基 ---------------------------------------------------- #
    objs.append(C.frustum("踏道基础", S.width + 0.5, steps * S.tread,
                          S.width + 0.3, steps * S.tread, 0.25,
                          z0=-0.25, loc=(side * (B.width / 2 + S.width / 2),
                                         y0 + steps * S.tread / 2)))
    return objs


# --------------------------------------------------------------------------- #
#  汇总
# --------------------------------------------------------------------------- #
def build_all(out=None):
    log = out.append if out is not None else (lambda s: None)
    top = platform_top()
    objs = [build_platform()]
    objs += pilasters()
    objs += gate_details(top)
    objs += stairs(side=-1)
    log(f"  城台 {B.width:.1f}×{B.depth:.1f}×{B.height:.1f}"
        f"（收分后顶面 {B.top_width():.1f}×{B.top_depth():.1f}）")
    log(f"  门洞 圭形过梁式 下宽 {G.w_bottom} 上宽 {G.w_top} 净高 {G.h_clear}")
    return objs, top
