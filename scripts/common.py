# -*- coding: utf-8 -*-
"""《清明上河图》城门楼 —— 全局参数与几何工具库。

尺寸以米为单位，依《营造法式》材份制折算：
    1 分 = 1.8 cm    材 = 15 分 = 27 cm    足材 = 21 分 = 37.8 cm    栔 = 6 分
原画中的构造按宋代官式城门（上善门）形制还原。

所有构件均以“本构件局部坐标”建模，再由 build_gate.py 统一定位。
局部坐标约定：X = 面阔方向（横向），Y = 进深方向（纵向，+Y 为后），Z = 竖直向上。
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

# --------------------------------------------------------------------------- #
#  材份制
# --------------------------------------------------------------------------- #
FEN = 0.018          # 1 分
CAI = 15 * FEN       # 单材高 0.270
ZUCAI = 21 * FEN     # 足材高 0.378
QI = 6 * FEN         # 栔（斗拱上下两层拱之间的空隙）0.108


# --------------------------------------------------------------------------- #
#  城台
# --------------------------------------------------------------------------- #
class Base:
    width = 30.0            # 面阔方向（沿城墙走向）
    depth = 14.0            # 进深方向（门洞穿行方向）
    height = 10.5
    batter = 0.055          # 收分：每升高 1 m，每侧内收的比例
    corner_pilaster = 0.85  # 壁柱（四角及门洞两侧的竖向砖垛）外凸宽度

    @classmethod
    def top_width(cls):
        return cls.width - 2 * cls.batter * cls.height

    @classmethod
    def top_depth(cls):
        return cls.depth - 2 * cls.batter * cls.height


# --------------------------------------------------------------------------- #
#  门洞（圭形过梁式，非券顶）
# --------------------------------------------------------------------------- #
class Gate:
    w_bottom = 5.2          # 门洞下口宽
    w_top = 4.4             # 门洞上口宽（两侧壁向内斜收）
    h_clear = 6.6           # 门洞净高（至过梁下皮）
    lintel_h = 0.72         # 过梁（木大梁）高
    lintel_d = 0.55         # 过梁厚
    leaf_w = 2.10           # 单扇门扉宽
    leaf_h = 4.80           # 门扉高
    leaf_t = 0.13
    # 门簪（门额上承托匾额的四枚木栓）
    stud_n = 4
    stud_d = 0.20
    stud_l = 0.34
    # 门额匾
    plaque_w = 3.30
    plaque_h = 1.70
    plaque_t = 0.26
    plaque_tilt = math.radians(9.0)   # 匾额上缘外倾


# --------------------------------------------------------------------------- #
#  城楼
# --------------------------------------------------------------------------- #
class Tower:
    bay_mid = 6.00          # 明间面阔
    bay_side = 5.10         # 次间面阔
    dep_bay = 2.80          # 进深每间
    dep_n = 3               # 进深三间
    col_h = 4.50            # 檐柱高
    col_d = 0.42            # 檐柱径
    col_taper = 0.90        # 柱头卷杀后的直径比
    side_splay = 0.012      # 侧脚（柱头向内微倾）
    rise = 0.008            # 生起（角柱略高于平柱）
    plinth_r = 0.60         # 柱础半径
    plinth_h = 0.14

    # 阑额 / 普拍枋
    lane_h = 0.36
    lane_t = 0.18
    pupai_h = 0.15
    pupai_t = 0.26

    # 破子棂窗
    win_h = 2.42
    slat_w = 0.085          # 单根棂条宽（三角棱断面）
    slat_gap = 0.055        # 棂条净距

    # 平坐
    plinth_floor_t = 0.26   # 楼板厚
    plinth_band_h = 0.62    # 雁翅板（平坐外沿挡板）高
    plinth_over = 2.40      # 平坐外挑出檐柱轴线的水平距离

    @classmethod
    def total_w(cls):
        return cls.bay_mid + 2 * cls.bay_side

    @classmethod
    def total_d(cls):
        return cls.dep_n * cls.dep_bay

    @classmethod
    def col_x(cls):
        """檐柱在面阔方向的轴线坐标（对称）。"""
        hw = cls.total_w() / 2
        return [-hw, -cls.bay_side / 2, cls.bay_side / 2, hw]

    @classmethod
    def col_y(cls):
        """檐柱在进深方向的轴线坐标。"""
        hd = cls.total_d() / 2
        ys = []
        for i in range(cls.dep_n + 1):
            ys.append(-hd + i * cls.dep_bay)
        return ys


# --------------------------------------------------------------------------- #
#  屋顶（单檐歇山顶）
# --------------------------------------------------------------------------- #
class Roof:
    eave_out = 2.85         # 出檐：自檐柱轴线向外挑出
    rise_total = 4.60       # 举高：自檐口至正脊（平均坡度约 33°，近原画）
    juzhe = 1.42            # 举折指数（>1 使屋面凹曲，脊部陡、檐部缓）
    ridge_len = 11.0        # 正脊长（决定撒头宽度与收山位置）
    shoushan = 0.45         # 收山：垂脊下端在进深方向的位置（占半进深的比例）
    tile_pitch = 0.33       # 瓦垄间距（筒瓦中距）
    tile_r = 0.105          # 筒瓦半圆半径
    tilt_lift = 1.05        # 翼角起翘高度
    tilt_out = 0.55         # 翼角冲出（平面外挑）
    corner_span = 0.34      # 起翘影响范围（占檐口边长的比例）
    eave_t = 0.16           # 檐口（瓦当滴水）板厚
    ridge_h = 0.52          # 正脊高
    ridge_t = 0.40          # 正脊厚
    wd_h = 0.34             # 垂脊/戗脊高
    wd_t = 0.26
    bofeng_t = 0.09         # 博风板厚
    eave_z = 1.95           # 檐口标高（由 build_all 依铺作层顶覆盖）

    @classmethod
    def plan_w(cls):
        return Tower.total_w() + 2 * cls.eave_out

    @classmethod
    def plan_d(cls):
        return Tower.total_d() + 2 * cls.eave_out


# --------------------------------------------------------------------------- #
#  勾栏
# --------------------------------------------------------------------------- #
class Railing:
    h_xunzhang = 1.02       # 寻杖（扶手）上皮高
    xunzhang_d = 0.11       # 寻杖断面
    wangzhu_d = 0.17        # 望柱（望柱头）径
    wangzhu_h = 1.22        # 望柱高
    wangzhu_gap = 1.90      # 望柱间距
    shuzhu_w = 0.13         # 蜀柱（瘿项）宽
    yungong_w = 0.34        # 云栱宽
    huaban_h = 0.42         # 华版（下段栏板）高
    diban_h = 0.16          # 地栿（下横木）高
    diban_t = 0.14


# --------------------------------------------------------------------------- #
#  踏道
# --------------------------------------------------------------------------- #
class Stair:
    width = 3.60            # 踏道净宽
    tread = 0.27            # 踏面
    riser = 0.19            # 踢面
    railing_inset = 0.10    # 勾栏自踏道边缘内收


# --------------------------------------------------------------------------- #
#  网格工具
# --------------------------------------------------------------------------- #
def scene_reset():
    """清空当前场景（仅保留必要的默认数据块）。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def recalc_normals(ob):
    """把闭合实体的面法线统一朝外。

    prism() 按轮廓点序生成面，点序为顺时针时法线会朝内 —— 用作布尔运算的
    挖切体时会被当成反向实体，DIFFERENCE 不减反增。凡是闭合实体一律调用本函数。
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def get_collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def new_obj(name, verts, faces, collection="GateTower"):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    get_collection(collection).objects.link(ob)
    return ob


def grid_obj(name, rows, close_u=False, cap_first=False, cap_last=False,
             flip=False, collection="GateTower"):
    """rows[v][u] -> 顶点；在相邻行列之间铺四边形。

    close_u   把每行的首尾相接（环形放样，如斗、柱）。
    cap_first / cap_last  以 n 边形封闭第一行 / 最后一行。
    """
    nr = len(rows)
    nc = len(rows[0])
    verts = [p for row in rows for p in row]
    faces = []
    span_u = nc if close_u else nc - 1
    for v in range(nr - 1):
        for u in range(span_u):
            a = v * nc + u
            b = v * nc + (u + 1) % nc
            c = (v + 1) * nc + (u + 1) % nc
            d = (v + 1) * nc + u
            faces.append([a, b, c, d] if not flip else [d, c, b, a])
    if cap_first:
        f = list(range(nc))[::-1]
        faces.append(f[::-1] if flip else f)
    if cap_last:
        o = (nr - 1) * nc
        f = [o + i for i in range(nc)]
        faces.append(f[::-1] if flip else f)
    return new_obj(name, verts, faces, collection)


def prism(name, profile, thickness, axis="Y", offset=0.0, collection="GateTower"):
    """把闭合二维轮廓沿 axis 拉伸 thickness。

    profile 为 (a, b) 点列；axis='Y' 时 a->X, b->Z；axis='Z' 时 a->X, b->Y。
    """
    n = len(profile)
    verts = []
    for (a, b) in profile:
        if axis == "Y":
            verts.append((a, offset - thickness / 2, b))
        elif axis == "Z":
            verts.append((a, b, offset - thickness / 2))
        else:  # X
            verts.append((offset - thickness / 2, a, b))
    for (a, b) in profile:
        if axis == "Y":
            verts.append((a, offset + thickness / 2, b))
        elif axis == "Z":
            verts.append((a, b, offset + thickness / 2))
        else:
            verts.append((offset + thickness / 2, a, b))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, j + n, i + n])
    faces.append(list(range(n))[::-1])
    faces.append(list(range(n, 2 * n)))
    return recalc_normals(new_obj(name, verts, faces, collection))


def box(name, sx, sy, sz, loc=(0, 0, 0), collection="GateTower"):
    x, y, z = loc
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    v = [(x - hx, y - hy, z - hz), (x + hx, y - hy, z - hz),
         (x + hx, y + hy, z - hz), (x - hx, y + hy, z - hz),
         (x - hx, y - hy, z + hz), (x + hx, y - hy, z + hz),
         (x + hx, y + hy, z + hz), (x - hx, y + hy, z + hz)]
    f = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
         [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return recalc_normals(new_obj(name, v, f, collection))


def frustum(name, w0, d0, w1, d1, h, z0=0.0, loc=(0.0, 0.0), collection="GateTower"):
    """上下不同大的方台（用于城台、栌斗、柱础等）。"""
    x, y = loc
    hw0, hd0, hw1, hd1 = w0 / 2, d0 / 2, w1 / 2, d1 / 2
    v = [(x - hw0, y - hd0, z0), (x + hw0, y - hd0, z0),
         (x + hw0, y + hd0, z0), (x - hw0, y + hd0, z0),
         (x - hw1, y - hd1, z0 + h), (x + hw1, y - hd1, z0 + h),
         (x + hw1, y + hd1, z0 + h), (x - hw1, y + hd1, z0 + h)]
    f = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
         [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return recalc_normals(new_obj(name, v, f, collection))


# --------------------------------------------------------------------------- #
#  斗与拱的轮廓
# --------------------------------------------------------------------------- #
def dou_profile(w, h, ear=0.34, qi=0.60, bottom=0.80):
    """斗（栌斗/交互斗/散斗）的侧视轮廓 —— 斗底、斗欹（内凹腰）、斗平、斗耳。"""
    hw = w / 2
    bw = hw * bottom
    return [
        (-bw, 0.0),
        (bw, 0.0),
        (bw, h * qi * 0.55),
        (hw * 0.86, h * qi),          # 斗欹内凹
        (hw, h * qi + h * (1 - qi) * 0.28),
        (hw, h),                       # 斗耳
        (-hw, h),
        (-hw, h * qi + h * (1 - qi) * 0.28),
        (-hw * 0.86, h * qi),
        (-bw, h * qi * 0.55),
    ]


def gong_profile(length, height, juan=4 * FEN, dip=0.52, samples=14):
    """拱的侧视轮廓：两端卷杀（《营造法式》华拱头卷杀四分）。

    顶面自两端向中间升起，端部下沿略收，形成宋式拱头“手”形。
    返回闭合点列（逆时针）。
    """
    hl = length / 2
    juan = min(juan, hl * 0.6)
    top, bot = [], []

    def drop(t):
        """t: 0 在端部，1 在卷杀终点。"""
        return (1.0 - t) ** 1.7

    # 下沿：自左端到右端
    xs = []
    for i in range(samples + 1):
        xs.append(-hl + 2 * hl * i / samples)
    for x in xs:
        d = hl - abs(x)
        t = min(1.0, max(0.0, d / juan)) if juan > 0 else 1.0
        bot.append((x, 0.10 * height * drop(t)))
    for x in reversed(xs):
        d = hl - abs(x)
        t = min(1.0, max(0.0, d / juan)) if juan > 0 else 1.0
        top.append((x, height - (height * (1 - dip)) * drop(t)))
    return bot + top


def column_profile(diameter, height, taper=0.90, samples=16, z0=0.0):
    """檐柱侧视轮廓：柱身带卷杀（上细下粗），柱头圆收。"""
    r = diameter / 2
    rt = r * taper
    left, right = [], []
    for i in range(samples + 1):
        t = i / samples
        z = z0 + height * t
        # 卷杀：柱身上段 38% 起向内圆收至柱头
        rr = r + (rt - r) * max(0.0, (t - 0.62) / 0.38) ** 1.5
        left.append((-rr, z))
        right.append((rr, z))
    return left + list(reversed(right))


# --------------------------------------------------------------------------- #
#  对象操作
# --------------------------------------------------------------------------- #
def bevel(ob, width=0.012, segments=2, angle=None, clamp=True):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = angle if angle is not None else math.radians(38)
    m.use_clamp_overlap = clamp
    m.harden_normals = False
    return m


def boolean_diff(ob, cutter, apply=True):
    m = ob.modifiers.new("Bool", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.object = cutter
    m.solver = "EXACT"
    if apply:
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    return ob


def mirror_x(ob, apply=True):
    m = ob.modifiers.new("Mirror", "MIRROR")
    m.use_axis[0] = True
    if apply:
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def shade_smooth(ob, angle=math.radians(34)):
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def join(objs, name, collection="GateTower"):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob


def apply_all_modifiers(ob):
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except RuntimeError:
            ob.modifiers.remove(m)
    return ob


def hand_drawn_wobble(ob, amount=0.012, scale=1.7, seed=0):
    """给顶点加极轻微的位置扰动，让轮廓线不像 CAD 那样死板 —— 手绘感的关键。"""
    import mathutils.noise as mnoise
    me = ob.data
    for v in me.vertices:
        p = v.co
        n = Vector((
            mnoise.noise(p * scale + Vector((seed, 0, 0))),
            mnoise.noise(p * scale + Vector((0, seed, 100))),
            mnoise.noise(p * scale + Vector((0, 0, seed + 200))),
        ))
        v.co = p + n * amount
    me.update()
    return ob


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)
