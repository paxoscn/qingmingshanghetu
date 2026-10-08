# -*- coding: utf-8 -*-
"""水墨材质系统。

思路：几何只负责“形”，墨色由着色器生成。每个材质都是一条
    墨量 = AO聚墨 + 轮廓积墨 + 皴法 + 排线（砖纹/瓦垄）
的合成链，再把 墨量 在绢本底色与墨色之间插值。

“毛笔质感”由四层叠加得到：
  1. 聚墨   —— Ambient Occlusion，墨自然沉积在凹处、构件交接处（对应原画的皴染）
  2. 积墨   —— Fresnel 轮廓，形体转折处加浓，模拟毛笔顿笔
  3. 飞白   —— 拉长的高频噪声，模拟干笔擦过绢面的断续
  4. 排线   —— Wave 纹理，复刻原画城台斜向砖纹与瓦垄横向接缝
底色取色自 gate.jpg 的绢本实测色（见 tools/img_tools.py palette）。
"""
import math

import bpy

# --------------------------------------------------------------------------- #
#  色板（sRGB 0-1），取自原画实测
# --------------------------------------------------------------------------- #
PAPER = (0.886, 0.845, 0.752)       # 绢本亮部（比原画实测略去饱和，留给光照加温）
PAPER_WARM = (0.780, 0.640, 0.404)  # 绢本旧色
INK = (0.262, 0.178, 0.114)         # 墨（原画的墨偏暖褐，不是纯黑）
INK_DEEP = (0.128, 0.082, 0.050)    # 浓墨
SEAL = (0.749, 0.153, 0.098)        # 印泥朱红


def srgb(c):
    """sRGB -> linear（Blender 节点颜色为线性空间）。"""
    out = []
    for v in c:
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def _sock(src):
    """节点 -> 其默认输出；已是插槽则原样返回。"""
    if hasattr(src, "outputs"):
        return src.outputs[0]
    return src


def _mix(nt, kind, a, b, fac, loc):
    """建一个 MixRGB 节点并连接。a/b 可为插槽、节点或常量。"""
    n = nt.nodes.new("ShaderNodeMixRGB")
    n.blend_type = kind
    n.location = loc
    n.inputs[0].default_value = fac
    for idx, src in ((1, a), (2, b)):
        if src is None:
            continue
        if isinstance(src, tuple):
            n.inputs[idx].default_value = src
        elif isinstance(src, (int, float)):
            n.inputs[idx].default_value = (src, src, src, 1.0)
        else:
            nt.links.new(_sock(src), n.inputs[idx])
    return n


def _math(nt, op, a, b=None, loc=(0, 0), clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.location = loc
    n.use_clamp = clamp
    for idx, src in ((0, a), (1, b)):
        if src is None:
            continue
        if isinstance(src, (int, float)):
            n.inputs[idx].default_value = src
        else:
            nt.links.new(_sock(src), n.inputs[idx])
    return n


def _map(nt, tex, scale, loc, rot=None):
    n = nt.nodes.new("ShaderNodeMapping")
    n.location = loc
    n.inputs["Scale"].default_value = scale if isinstance(scale, tuple) else (scale,) * 3
    if rot is not None:
        n.inputs["Rotation"].default_value = rot
    nt.links.new(tex, n.inputs["Vector"])
    return n


def _texcoord(nt, loc=(-1600, 0)):
    n = nt.nodes.new("ShaderNodeTexCoord")
    n.location = loc
    return n.outputs["Object"]


def _noise(nt, vec, scale, detail=8.0, rough=0.55, dist=0.0, loc=(0, 0)):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.location = loc
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = dist
    nt.links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def _wave(nt, vec, scale, rot=None, loc=(0, 0), profile="SIN", distortion=0.0,
          detail=0.0, detail_scale=1.0):
    n = nt.nodes.new("ShaderNodeTexWave")
    n.wave_type = "BANDS"
    n.bands_direction = "X"
    n.wave_profile = profile
    n.location = loc
    n.inputs["Scale"].default_value = scale
    n.inputs["Distortion"].default_value = distortion
    n.inputs["Detail"].default_value = detail
    n.inputs["Detail Scale"].default_value = detail_scale
    nt.links.new(vec, n.inputs["Vector"])
    if rot is not None:
        m = nt.nodes.new("ShaderNodeMapping")
        m.location = (loc[0] - 220, loc[1])
        m.inputs["Rotation"].default_value = rot
        nt.links.new(vec, m.inputs["Vector"])
        nt.links.new(m.outputs["Vector"], n.inputs["Vector"])
    return n.outputs["Fac"]


def _ramp(nt, src, stops, loc=(0, 0)):
    n = nt.nodes.new("ShaderNodeValToRGB")
    n.location = loc
    el = n.color_ramp.elements
    while len(el) > 1:
        el.remove(el[-1])
    el[0].position = stops[0][0]
    el[0].color = (stops[0][1],) * 3 + (1,)
    for pos, val in stops[1:]:
        e = el.new(pos)
        e.color = (val,) * 3 + (1,)
    nt.links.new(_sock(src), n.inputs["Fac"])
    return n.outputs["Color"]


# --------------------------------------------------------------------------- #
#  材质工厂
# --------------------------------------------------------------------------- #
def ink_material(name, ink=0.62, paper=PAPER, edge=0.55, ao_dist=0.34, ao_gain=1.15,
                 grain=0.14, feibai=0.30, feibai_dir=(6.0, 46.0, 6.0),
                 hatch=None, hatch_scale=26.0, hatch_strength=0.55, hatch_rot=None,
                 hatch_distort=2.0,
                 rib=None, rib_scale=18.0, rib_strength=0.45,
                 rough=0.86, tone_jitter=0.06, seed=0.0):
    """生成一个水墨材质。

    hatch:      斜向排线（城台砖纹）。给一个角度（度）；None 为不排线。
    rib:        横向接缝（瓦垄分瓦）。给强度或 None。
    feibai:     飞白强度。
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (1400, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (1100, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = rough
    if "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = 0.08
    elif "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.08
    bsdf.inputs["Metallic"].default_value = 0.0

    obj = _texcoord(nt)

    # ---- 1. 聚墨：AO 在凹处、交接处积墨 ---------------------------------- #
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.location = (-1240, 380)
    ao.samples = 16
    ao.inputs["Distance"].default_value = ao_dist
    ao.only_local = False
    # AO 输出在 1 处表示“无遮挡”，取反得到墨量
    ao_inv = _math(nt, "SUBTRACT", 1.0, ao.outputs["AO"], loc=(-1000, 380), clamp=True)
    ao_amt = _math(nt, "MULTIPLY", ao_inv, ao_gain, loc=(-820, 380), clamp=True)

    # ---- 2. 积墨：形体轮廓（Fresnel） ------------------------------------ #
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.location = (-1240, 120)
    lw.inputs["Blend"].default_value = 0.22
    edge_amt = _math(nt, "MULTIPLY", lw.outputs["Facing"], -1.0, loc=(-1000, 120))
    edge_amt = _math(nt, "ADD", edge_amt, 1.0, loc=(-820, 120), clamp=True)
    edge_amt = _math(nt, "MULTIPLY", edge_amt, edge, loc=(-640, 120), clamp=True)

    # ---- 3. 皴法：中频噪声，让墨色不匀 ------------------------------------ #
    cu = _noise(nt, obj, 2.4, detail=7.0, rough=0.62, dist=0.55, loc=(-1240, -160))
    cu_amt = _math(nt, "MULTIPLY", cu, grain, loc=(-640, -160), clamp=True)

    # ---- 4. 飞白：沿一个方向拉长的高频噪声 -------------------------------- #
    fb_vec = _map(nt, obj, feibai_dir, (-1440, -440))
    fb = _noise(nt, fb_vec.outputs["Vector"], 2.2, detail=9.0, rough=0.72, loc=(-1240, -440))
    fb_amt = _math(nt, "MULTIPLY", fb, feibai, loc=(-640, -440), clamp=True)

    # ---- 5. 排线：城台斜向砖纹 ------------------------------------------- #
    layers = [ao_amt, edge_amt, cu_amt, fb_amt]

    if hatch is not None:
        rot = hatch_rot
        if rot is None:
            a = math.radians(hatch)
            rot = (a, 0.0, 0.0) if abs(math.cos(a)) > 0.5 else (0.0, 0.0, a)
        # 在 XZ 平面内斜排：绕 Y 轴旋转
        hw = nt.nodes.new("ShaderNodeTexWave")
        hw.wave_type = "BANDS"
        hw.bands_direction = "X"
        hw.wave_profile = "SAW"
        hw.location = (-1240, -720)
        hw.inputs["Scale"].default_value = hatch_scale
        hw.inputs["Distortion"].default_value = hatch_distort
        hw.inputs["Detail"].default_value = 3.0
        hw.inputs["Detail Scale"].default_value = 1.6
        hm = nt.nodes.new("ShaderNodeMapping")
        hm.location = (-1440, -720)
        hm.inputs["Rotation"].default_value = (
            0.0, math.radians(hatch), 0.0)
        nt.links.new(obj, hm.inputs["Vector"])
        nt.links.new(hm.outputs["Vector"], hw.inputs["Vector"])
        # 排线的疏密变化，模拟手绘排线时轻时不轻
        hbreak = _noise(nt, obj, 1.3, detail=4.0, loc=(-1240, -900))
        hb = _math(nt, "MULTIPLY", hbreak, -1.2, loc=(-1050, -900))
        hb = _math(nt, "ADD", hb, 0.92, loc=(-880, -900), clamp=True)
        hamt = _math(nt, "MULTIPLY", hw.outputs["Fac"], hb, loc=(-880, -720), clamp=True)
        hamt = _math(nt, "MULTIPLY", hamt, hatch_strength, loc=(-700, -720), clamp=True)
        layers.append(hamt)

    # ---- 6. 瓦垄横向接缝 -------------------------------------------------- #
    if rib is not None:
        rw = _wave(nt, obj, rib_scale, loc=(-1240, -1180), profile="SAW")
        ramt = _math(nt, "MULTIPLY", rw, rib_strength, loc=(-880, -1180), clamp=True)
        layers.append(ramt)

    # ---- 合成墨量 --------------------------------------------------------- #
    total = layers[0]
    for i, l in enumerate(layers[1:]):
        total = _math(nt, "ADD", total, l, loc=(-460 + i * 0, 300 - i * 120), clamp=True)

    # 轻微色调抖动，避免整栋建筑一个墨色
    if tone_jitter:
        tj = _noise(nt, obj, 0.55, detail=2.0, loc=(-1240, 640))
        tjm = _math(nt, "MULTIPLY_ADD", tj, tone_jitter * 2, loc=(-1000, 640))
        tjm.inputs[2].default_value = -tone_jitter
        total = _math(nt, "ADD", total, tjm, loc=(-300, 640), clamp=True)

    # 墨量曲线：让淡处更透、浓处更实（对应墨分五色）
    total_c = _ramp(nt, total, [(0.0, 0.0), (0.32, 0.16), (0.66, 0.52), (1.0, 1.0)],
                    loc=(-120, 300))

    # 墨量 -> 颜色
    paper_l = srgb(paper) + (1.0,)
    ink_l = srgb(INK) + (1.0,)
    ink_deep_l = srgb(INK_DEEP) + (1.0,)
    base = _mix(nt, "MIX", paper_l, ink_l, 1.0, (140, 120))
    nt.links.new(total_c, base.inputs[0])
    # 只有最浓的一小片再压一层，得到焦墨；否则整幅会闷黑
    dmask = _ramp(nt, total_c, [(0.0, 0.0), (0.66, 0.0), (1.0, 0.42)], loc=(140, -60))
    deep = _mix(nt, "MULTIPLY", base.outputs["Color"], ink_deep_l, 0.0, (400, -60))
    nt.links.new(dmask, deep.inputs[0])
    nt.links.new(deep.outputs["Color"], bsdf.inputs["Base Color"])

    # 墨浓处略降高光，纸面保持哑光
    rg = _math(nt, "MULTIPLY", total_c, 0.10, loc=(250, -320))
    rg = _math(nt, "ADD", rg, rough, loc=(400, -320))
    nt.links.new(rg.outputs["Value"], bsdf.inputs["Roughness"])

    mat["_ink_total"] = True
    return mat


# --------------------------------------------------------------------------- #
#  预设
# --------------------------------------------------------------------------- #
def build_all():
    """返回整个城门楼用到的材质字典。"""
    m = {}
    m["tile"] = ink_material(
        "瓦垄", ink=0.24, ao_dist=0.07, ao_gain=0.55, edge=0.15,
        feibai=0.22, feibai_dir=(4.0, 30.0, 4.0),
        grain=0.12, rough=0.80,
    )
    m["ridge"] = ink_material(
        "正脊垂脊", ink=0.40, ao_dist=0.15, ao_gain=0.78, edge=0.26,
        feibai=0.26, grain=0.18, rough=0.78,
    )
    m["wood"] = ink_material(
        "木构件", ink=0.42, ao_dist=0.12, ao_gain=0.76, edge=0.32,
        feibai=0.30, feibai_dir=(3.0, 52.0, 3.0), grain=0.13, rough=0.88,
    )
    m["dougong"] = ink_material(
        "铺作", ink=0.60, ao_dist=0.11, ao_gain=1.00, edge=0.46,
        feibai=0.22, grain=0.14, rough=0.86,
    )
    m["railing"] = ink_material(
        "勾栏", ink=0.58, ao_dist=0.11, ao_gain=1.00, edge=0.44,
        feibai=0.24, grain=0.13, rough=0.86,
    )
    m["window"] = ink_material(
        "破子棂窗", ink=0.64, ao_dist=0.09, ao_gain=1.05, edge=0.48,
        feibai=0.20, grain=0.18, rough=0.88,
    )
    m["wall"] = ink_material(
        "城台", ink=0.40, ao_dist=0.26, ao_gain=0.70, edge=0.18,
        feibai=0.22,
        hatch=-38.0, hatch_scale=4.2, hatch_strength=0.62, hatch_distort=1.4,
        grain=0.14, rough=0.92,
    )
    m["wall_in"] = ink_material(
        "门洞内壁", ink=0.78, ao_dist=0.70, ao_gain=1.10, edge=0.18,
        feibai=0.20,
        hatch=-38.0, hatch_scale=7.0, hatch_strength=0.30, hatch_distort=1.6,
        grain=0.18, rough=0.94,
    )
    m["stone"] = ink_material(
        "石作", ink=0.44, ao_dist=0.22, ao_gain=0.85, edge=0.28,
        feibai=0.28, feibai_dir=(8.0, 8.0, 40.0), grain=0.16, rough=0.94,
    )
    m["door"] = ink_material(
        "门扉", ink=0.62, ao_dist=0.14, ao_gain=1.00, edge=0.44,
        feibai=0.20, grain=0.16,
        rib=0.26, rib_scale=22.0, rough=0.88,
    )
    m["bronze"] = ink_material(
        "门钉铺首", ink=0.84, ao_dist=0.18, ao_gain=1.50, edge=0.80,
        feibai=0.16, grain=0.18, rough=0.72,
    )
    m["plaque"] = ink_material(
        "匾额", ink=0.62, ao_dist=0.18, ao_gain=0.95, edge=0.40,
        feibai=0.18, grain=0.20, rough=0.84,
    )
    return m


def outline_material():
    """Freestyle 之外的补充墨线材质（法线外扩描边用）。"""
    mat = bpy.data.materials.new("墨线")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = srgb(INK_DEEP) + (1.0,)
    em.inputs["Strength"].default_value = 1.0
    # 只渲染背面 —— 外扩壳的背面构成轮廓线
    mix = nt.nodes.new("ShaderNodeMixShader")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    g = nt.nodes.new("ShaderNodeNewGeometry")
    nt.links.new(g.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    mat.use_backface_culling = False
    return mat
