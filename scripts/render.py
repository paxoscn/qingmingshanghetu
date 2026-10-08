# -*- coding: utf-8 -*-
"""渲染管线：水墨渲染 + Freestyle 毛笔描边 + 绢本合成。

一笔墨线的三个层次（与原画“白描+皴染”的画法对应）：
    主轮廓  粗，silhouette / border / external contour
    结构线  中，crease / ridge-valley（斗拱、勾栏、瓦垄的转折）
    材质界  细，material boundary（不同构件的分界）
三层各挂一张毛笔笔触位图并各自调粗细，
再叠 Calligraphy / AlongStroke / Noise 三个粗细修饰器，
得到有起收、有顿挫、有飞白的笔触，而不是等宽黑线。
"""
import math
import os

import bpy
from mathutils import Vector

from . import brush as BR
from . import materials as M

OUT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "out"))


# --------------------------------------------------------------------------- #
#  基础渲染设置
# --------------------------------------------------------------------------- #
def setup_render(scene, res=(1500, 1200), samples=64, engine="EEVEE"):
    r = scene.render
    r.engine = "BLENDER_EEVEE" if engine.upper() == "EEVEE" else "CYCLES"
    r.resolution_x, r.resolution_y = res
    r.resolution_percentage = 100
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.image_settings.color_depth = "8"
    # Freestyle 由 setup_freestyle() 开启 —— 未配置 lineset 就打开会崩溃
    r.use_freestyle = False
    if engine.upper() == "EEVEE":
        e = scene.eevee
        e.taa_render_samples = samples
        e.use_gtao = True
        e.gtao_distance = 1.4
        e.gtao_factor = 1.0
        e.use_soft_shadows = True
        e.shadow_cube_size = "2048"
        e.shadow_cascade_size = "2048"
        e.use_shadows = True
    else:
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.02       # 压住朝上的大面，免得过曝成白块
    return scene


def setup_world(scene, color=None, strength=0.95):
    """世界背景 = 绢本底色，兼作环境光，使画面整体平、不立体 —— 水墨要的就是平。"""
    world = bpy.data.worlds.get("GateWorld") or bpy.data.worlds.new("GateWorld")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = M.srgb(color or M.PAPER) + (1.0,)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world


def setup_lights(scene):
    """一盏大面光 + 一盏弱补光。角度低、光比小，避免出现写实立体感。"""
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o, do_unlink=True)

    def area(name, loc, target, size, energy, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, type="AREA")
        d.size = size
        d.energy = energy
        d.color = color
        ob = bpy.data.objects.new(name, d)
        scene.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return ob

    # 光比压得很小：水墨画面靠墨色分层，不靠明暗。主光只用来交代一点方向感
    area("主光", (-26, -32, 30), (0, 0, 11), 44.0, 28000, (1.0, 0.97, 0.90))
    area("补光", (32, -20, 14), (0, 0, 10), 50.0, 9000, (0.88, 0.91, 1.0))


# --------------------------------------------------------------------------- #
#  Freestyle 毛笔描边
# --------------------------------------------------------------------------- #
# NOTE: 三个粗细修饰器的 thickness_min/max、value_min/max、amplitude
#       都是**绝对线宽**（与 linestyle.thickness 同单位），不是倍率。
#       若直接填倍率会把线宽压到亚像素，笔画会被整片丢弃
#       （渲染日志表现为 “strokes set empty”）。故一律乘基准线宽。
def _mod_calligraphy(ls, orient_deg, base, tmin_r, tmax_r, influence=1.0):
    m = ls.thickness_modifiers.new("笔锋", "CALLIGRAPHY")
    m.orientation = math.radians(orient_deg)
    m.thickness_min = tmin_r * base
    m.thickness_max = tmax_r * base
    m.influence = influence
    m.blend = "MIX"
    return m


def _mod_along_stroke(ls, base, vmin_r, vmax_r, influence=0.6, invert=False):
    m = ls.thickness_modifiers.new("起收", "ALONG_STROKE")
    m.mapping = "LINEAR"
    m.value_min = vmin_r * base
    m.value_max = vmax_r * base
    m.influence = influence
    m.invert = invert
    m.blend = "MIX"
    return m


def _mod_noise(ls, base, amp_r, period=0.55, influence=0.34, seed=1, asym=False):
    m = ls.thickness_modifiers.new("顿挫", "NOISE")
    m.amplitude = amp_r * base
    m.period = period
    m.seed = seed
    m.use_asymmetric = asym
    m.influence = influence
    m.blend = "MIX"
    return m


def _attach_brush(ls, tex, spacing=0.9, blend="MULTIPLY", alpha=1.0, scale=1.0):
    """把笔触位图挂到线型上。"""
    try:
        slot = ls.texture_slots.new()
    except (AttributeError, TypeError):
        try:
            slot = ls.texture_slots.add()
        except Exception:
            return None
    slot.texture = tex
    slot.texture_coords = "ALONG_STROKE"
    slot.blend_type = blend
    slot.alpha_factor = alpha
    slot.use_map_color_diffuse = False
    slot.use_map_alpha = True
    slot.scale = (scale, scale, scale)
    slot.offset = (0.0, 0.0, 0.0)
    ls.use_texture = True
    ls.texture_spacing = spacing
    return slot


def setup_freestyle(scene, brush_path, thickness=2.6, color=None, paper_path=None):
    vl = scene.view_layers[0]
    fs = vl.freestyle_settings
    # 默认 lineset 的 linestyle 为 None；若残留会使 Freestyle 渲染崩溃，先补上
    for lset in fs.linesets:
        if lset.linestyle is None:
            lset.linestyle = bpy.data.linestyles.new("占位线型")
    # 总开关在 scene.render 上，逐视图层的开关在 view_layer 上 —— 两个都要开
    scene.render.use_freestyle = True
    vl.use_freestyle = True
    fs.mode = "EDITOR"
    # 折角阈值：大于此角度才算「折边」。152° 会把瓦垄每道棱都画成线，
    # 屋面糊成一片黑；122° 只留构件交接的硬边。
    fs.crease_angle = math.radians(122.0)
    fs.use_smoothness = True
    fs.use_culling = False
    fs.as_render_pass = False          # 线并入 Combined，才能被合成器统一处理
    fs.use_material_boundaries = True
    # 关掉山脊/山谷检测：瓦垄的每道垄脊都会被判为 ridge，屋面会糊成一张网
    fs.use_ridges_and_valleys = False
    fs.use_suggestive_contours = True

    while len(fs.linesets):
        fs.linesets.remove(fs.linesets[-1])

    tex = BR.get_brush_texture(brush_path)
    ink = M.srgb(color or M.INK_DEEP)

    specs = [
        # (名称, 选取, 线宽, 笔锋参数, 沿笔画, 噪声, 墨色浓度)
        dict(name="主轮廓", thick=thickness * 1.35, tmin=0.35, tmax=1.0,
             along=(0.55, 1.0, 0.45), noise=(0.55, 0.42, 0.30), tone=0.0,
             sel=dict(select_silhouette=True, select_border=True,
                      select_external_contour=True, select_contour=True)),
        # 不选 suggestive contour：它在瓦垄这类连续起伏上会满屏触发
        dict(name="结构线", thick=thickness * 0.62, tmin=0.30, tmax=0.95,
             along=(0.65, 1.0, 0.40), noise=(0.70, 0.33, 0.34), tone=0.06,
             sel=dict(select_crease=True)),
        dict(name="材质界", thick=thickness * 0.34, tmin=0.25, tmax=0.85,
             along=(0.70, 1.0, 0.35), noise=(0.85, 0.28, 0.38), tone=0.14,
             sel=dict(select_material_boundary=True)),
    ]

    for i, sp in enumerate(specs):
        ls_set = fs.linesets.new(sp["name"])
        for k in ("select_silhouette", "select_border", "select_crease",
                  "select_ridge_valley", "select_suggestive_contour",
                  "select_material_boundary", "select_contour",
                  "select_external_contour", "select_edge_mark"):
            setattr(ls_set, k, False)
        for k, v in sp["sel"].items():
            setattr(ls_set, k, v)
        ls_set.select_by_visibility = True
        ls_set.visibility = "VISIBLE"
        ls_set.select_by_edge_types = True
        # 网格上没有 face mark 时，开启此项会把所有边排除干净（笔画全空）
        ls_set.select_by_face_marks = False
        ls_set.select_by_collection = False
        ls_set.select_by_image_border = False

        ls = ls_set.linestyle
        if ls is None:
            ls = bpy.data.linestyles.new("墨线_" + sp["name"])
            ls_set.linestyle = ls
        else:
            ls.name = "墨线_" + sp["name"]
        c = tuple(min(1.0, v + sp["tone"] * 0.25) for v in ink)
        ls.color = c
        ls.alpha = 1.0
        ls.thickness = sp["thick"]
        ls.thickness_position = "CENTER"
        ls.caps = "ROUND"
        _mod_calligraphy(ls, 132.0, sp["thick"], sp["tmin"], sp["tmax"])
        _mod_along_stroke(ls, sp["thick"], sp["along"][0], sp["along"][1], sp["along"][2])
        _mod_noise(ls, sp["thick"], sp["noise"][0], sp["noise"][1], sp["noise"][2],
                   seed=1 + i, asym=True)
        _attach_brush(ls, tex, spacing=0.85, blend="MULTIPLY", alpha=1.0,
                      scale=1.0 + 0.15 * i)
    return fs


# --------------------------------------------------------------------------- #
#  相机
# --------------------------------------------------------------------------- #
def add_camera(scene, name, loc, target, lens=52.0, ortho_scale=None):
    cam = bpy.data.cameras.new(name)
    if ortho_scale:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho_scale
    else:
        cam.lens = lens
    cam.clip_start = 0.1
    cam.clip_end = 500.0
    ob = bpy.data.objects.new(name, cam)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


# --------------------------------------------------------------------------- #
#  合成：绢本叠加 + 四角压暗 + 轻微暖调
# --------------------------------------------------------------------------- #
def setup_compositor(scene, paper_path, grain=0.30, vignette=0.38, warm=0.10):
    scene.use_nodes = True
    nt = scene.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    rl = nt.nodes.new("CompositorNodeRLayers")
    rl.location = (-900, 0)

    if not os.path.exists(paper_path):
        os.makedirs(os.path.dirname(paper_path), exist_ok=True)
        BR.save_bitmap(BR.paper_bitmap(), paper_path)
    img = bpy.data.images.load(os.path.abspath(paper_path), check_existing=True)
    tex = nt.nodes.new("CompositorNodeImage")
    tex.image = img
    tex.location = (-900, -400)

    scale = nt.nodes.new("CompositorNodeScale")
    scale.space = "RENDER_SIZE"
    scale.location = (-700, -400)
    nt.links.new(tex.outputs["Image"], scale.inputs["Image"])

    mix = nt.nodes.new("CompositorNodeMixRGB")
    mix.blend_type = "OVERLAY"
    mix.location = (-500, -120)
    mix.inputs[0].default_value = grain
    nt.links.new(rl.outputs["Image"], mix.inputs[1])
    nt.links.new(scale.outputs["Image"], mix.inputs[2])

    # 四角压暗（旧绢的自然暗角）
    vpath = os.path.join(os.path.dirname(paper_path), "vignette.png")
    if not os.path.exists(vpath):
        BR.save_bitmap(BR.vignette_bitmap(), vpath)
    vimg = bpy.data.images.load(os.path.abspath(vpath), check_existing=True)
    vtex = nt.nodes.new("CompositorNodeImage")
    vtex.image = vimg
    vtex.location = (-700, 300)
    vscale = nt.nodes.new("CompositorNodeScale")
    vscale.space = "RENDER_SIZE"
    vscale.location = (-500, 300)
    nt.links.new(vtex.outputs["Image"], vscale.inputs["Image"])

    vin = nt.nodes.new("CompositorNodeMixRGB")
    vin.blend_type = "MULTIPLY"
    vin.location = (-260, -120)
    vin.inputs[0].default_value = vignette
    nt.links.new(mix.outputs["Image"], vin.inputs[1])
    nt.links.new(vscale.outputs["Image"], vin.inputs[2])

    # 暖调（原画是陈年绢本的暖褐色）
    bal = nt.nodes.new("CompositorNodeColorBalance")
    bal.location = (-40, -120)
    bal.correction_method = "LIFT_GAMMA_GAIN"
    bal.gain = (1.02, 1.0 - warm * 0.35, 1.0 - warm)
    bal.lift = (0.012, 0.008, 0.004)
    nt.links.new(vin.outputs["Image"], bal.inputs["Image"])

    comp = nt.nodes.new("CompositorNodeComposite")
    comp.location = (200, -120)
    nt.links.new(bal.outputs["Image"], comp.inputs["Image"])
    return nt


# --------------------------------------------------------------------------- #
#  出图
# --------------------------------------------------------------------------- #
def render(scene, cam, path, res=None):
    if res:
        scene.render.resolution_x, scene.render.resolution_y = res
    scene.camera = cam
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[render] {path}")
    return path


def default_views():
    """默认出图机位。第一张刻意贴近原画的低视点、左前方透视。"""
    return [
        dict(name="01_原画视角", loc=(-27.0, -52.0, 4.2), target=(3.0, 0.0, 13.5), lens=62.0),
        dict(name="02_正视", loc=(0.0, -100.0, 11.4), target=(0.0, 0.0, 11.4),
             lens=None, ortho=40.0),
        dict(name="03_三分", loc=(-42.0, -48.0, 26.0), target=(0.0, 0.0, 11.0), lens=52.0),
        dict(name="04_铺作细部", loc=(-13.0, -24.0, 15.0), target=(-3.5, -4.4, 17.4), lens=100.0),
        dict(name="05_俯瞰", loc=(-24.0, -32.0, 68.0), target=(0.0, 0.0, 11.0), lens=50.0),
        dict(name="06_门洞", loc=(-1.0, -24.0, 3.6), target=(0.0, 4.0, 5.2), lens=45.0),
        dict(name="07_侧后", loc=(46.0, 32.0, 22.0), target=(0.0, 0.0, 11.0), lens=56.0),
    ]


def setup_all(scene, res=(1500, 1100), samples=48, thickness=1.6, paper_dir=None,
              grain=0.18, vignette=0.30, warm=0.05):
    """一次配好渲染、世界、灯光、描边与合成。"""
    setup_render(scene, res=res, samples=samples)
    setup_world(scene)
    setup_lights(scene)
    base = paper_dir or os.path.join(OUT_ROOT, "tex")
    setup_freestyle(scene, os.path.join(base, "brush.png"), thickness=thickness)
    setup_compositor(scene, os.path.join(base, "paper.png"),
                     grain=grain, vignette=vignette, warm=warm)
    return scene


def render_all(scene, out_dir, views=None, res=(1500, 1100), verbose=True):
    views = default_views() if views is None else views
    paths = []
    for v in views:
        cam = add_camera(scene, v["name"], v["loc"], v["target"],
                         lens=v.get("lens") or 50.0, ortho_scale=v.get("ortho"))
        p = render(scene, cam, os.path.join(out_dir, v["name"] + ".png"), res=res)
        paths.append(p)
        if verbose:
            print(f"[视图] {v['name']}")
    return paths
