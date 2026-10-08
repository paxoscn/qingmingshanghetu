# -*- coding: utf-8 -*-
"""《清明上河图》城门楼 —— 总装脚本。

用法：
    Blender --background --python scripts/build_gate.py

产出：
    out/城门楼.blend     可继续编辑的工程文件
    out/城门楼.glb       通用三维格式
    out/城门楼.obj
    out/构件清单.txt     各构件数量与关键标高（供 docs/构造拆解.md 引用）

装配顺序（自下而上）：
    城台 → 平坐 → 楼身（柱/额/窗/门）→ 铺作 → 屋顶
各层的标高全部由下一层的实际成果推出（例如屋顶檐口标高取自铺作层顶），
因此改动尺寸参数后整栋楼会自动重新对位，不需要手填任何一个 z 值。
"""
import os
import sys
import time

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts import common as C          # noqa: E402
from scripts import materials as M       # noqa: E402
from scripts.parts import base as BASE   # noqa: E402
from scripts.parts import bracket as BR  # noqa: E402
from scripts.parts import frame as FR    # noqa: E402
from scripts.parts import railing as RL  # noqa: E402
from scripts.parts import roof as RF     # noqa: E402

OUT = os.path.join(ROOT, "out")


# --------------------------------------------------------------------------- #
#  材质指派：按构件名归入材质
# --------------------------------------------------------------------------- #
def material_key(name):
    tile = ("前坡", "后坡", "撒头", "瓦当", "滴水")
    ridge = ("正脊", "鸱吻", "垂脊", "戗脊", "蹲兽")
    gable = ("山花", "博风板", "悬鱼", "角梁")
    if name.startswith(tile):
        return "tile"
    if name.startswith(ridge):
        return "ridge"
    if name.startswith(gable):
        return "wood"
    if name.startswith("勾栏") or "勾栏" in name or name.startswith("望柱") \
            or name.startswith("蜀柱") or name.startswith("云栱"):
        return "railing"
    if name.startswith("窗"):
        return "window"
    if name.startswith("门扉") or name.startswith("门扇"):
        return "door"
    if name.startswith("门钉") or name.startswith("铺首") or name.startswith("钉") \
            or name.startswith("门簪"):
        return "bronze"
    if name.startswith("门额匾"):
        return "plaque"
    if name.startswith("柱础") or name.startswith("踏道基础") or name.startswith("踏步"):
        return "stone"
    if name.startswith("城台") or name.startswith("角垛") or name.startswith("门侧竖带"):
        return "wall"
    return "wood"


def assign(objs, mats):
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mats[material_key(o.name)])
    return objs


# --------------------------------------------------------------------------- #
#  铺作布列
# --------------------------------------------------------------------------- #
def shuzuo_rows(pupai_z):
    """沿檐柱一圈布置柱头铺作与补间铺作。

    返回对象列表；每攒按所在檐面旋转，使其局部 +X（出跳方向）指向室外。
    """
    import math
    T = C.Tower
    xs, ys = T.col_x(), T.col_y()
    hw, hd = T.total_w() / 2.0, T.total_d() / 2.0
    objs = []

    def emit(x, y, rot_z, zhu_tou, tag):
        for o in BR.build_shuzuo(f"铺作_{tag}", zhu_tou=zhu_tou):
            if rot_z:
                o.rotation_euler = (0.0, 0.0, rot_z)
            o.location = (x, y, pupai_z)
            objs.append(o)

    # 前后檐：向外为 ∓Y
    for y, rot in ((ys[0], -math.pi / 2), (ys[-1], math.pi / 2)):
        for i, x in enumerate(xs):
            emit(x, y, rot, True, f"柱头_{x:.1f}_{y:.1f}")
            if i < len(xs) - 1:
                # 补间铺作：每间一朵（明间两朵，与原画的疏密相合）
                n_mid = 2 if i == 1 else 1
                for k in range(n_mid):
                    t = (k + 1) / (n_mid + 1)
                    emit(x + (xs[i + 1] - x) * t, y, rot, False,
                         f"补间_{x:.1f}_{y:.1f}_{k}")

    # 两山：向外为 ∓X
    for x, rot in ((xs[0], math.pi), (xs[-1], 0.0)):
        for j, y in enumerate(ys):
            if y in (ys[0], ys[-1]):
                continue                      # 角柱已由前后檐布置
            emit(x, y, rot, True, f"柱头山_{x:.1f}_{y:.1f}")
            if j < len(ys) - 1:
                for k in range(1):
                    t = 0.5
                    emit(x, y + (ys[j + 1] - y) * t, rot, False,
                         f"补间山_{x:.1f}_{y:.1f}_{k}")
    return objs


def liaoyanfang_ring(z):
    """撩檐枋：檐下一圈通长枋，把各攒铺作连成整体。"""
    T = C.Tower
    xs, ys = T.col_x(), T.col_y()
    hw, hd = T.total_w() / 2.0, T.total_d() / 2.0
    L = BR.LIAOYAN_T
    H = BR.LIAOYAN_H
    out = []
    out.append(C.box("撩檐枋前", T.total_w() + 1.2, L, H, loc=(0, ys[0], z + H / 2)))
    out.append(C.box("撩檐枋后", T.total_w() + 1.2, L, H, loc=(0, ys[-1], z + H / 2)))
    out.append(C.box("撩檐枋左", L, T.total_d() + 1.2, H, loc=(xs[0], 0, z + H / 2)))
    out.append(C.box("撩檐枋右", L, T.total_d() + 1.2, H, loc=(xs[-1], 0, z + H / 2)))
    return out


# --------------------------------------------------------------------------- #
#  总装
# --------------------------------------------------------------------------- #
def build():
    log = []
    t0 = time.time()
    C.scene_reset()
    mats = M.build_all()

    # ---- 1. 城台 ------------------------------------------------------ #
    base_objs, top_z = BASE.build_all(out=log)
    platform = base_objs[0]                    # 城台本体自带内/外两种材质
    platform.data.materials.clear()
    platform.data.materials.append(mats["wall"])
    platform.data.materials.append(mats["wall_in"])
    rest = assign(base_objs[1:], mats)

    # ---- 2. 平坐（自城台顶向上叠置，楼板面标高由它返回） --------------- #
    pingzuo, floor_z = FR.build_pingzuo(top_z)
    assign(pingzuo, mats)

    # ---- 3. 楼身 ------------------------------------------------------ #
    frame_objs, pupai_z, tops = FR.build_all(floor_z, out=log)
    assign(frame_objs, mats)

    # ---- 4. 铺作 ------------------------------------------------------ #
    shuzuo = shuzuo_rows(pupai_z)
    assign(shuzuo, mats)
    shuzuo += assign(liaoyanfang_ring(BR.Z_LIAOYAN + pupai_z), mats)
    log.append(f"  铺作构件 {len(shuzuo)} 件，层高 {BR.shuzuo_top():.2f}"
               f"（普拍枋上皮 {pupai_z:.2f}）")

    # ---- 5. 屋顶 ------------------------------------------------------ #
    eave_z = pupai_z + BR.shuzuo_top() + 0.10
    roof_objs = RF.build_all(eave_z=eave_z, out=log)
    assign(roof_objs, mats)
    log.append(f"  檐口标高 {eave_z:.2f}   正脊标高 {eave_z + C.Roof.rise_total:.2f}")

    # ---- 6. 平坐勾栏（坐在楼板面上） ---------------------------------- #
    T = C.Tower
    hwx = T.total_w() / 2.0 + T.plinth_over - 0.14
    hdy = T.total_d() / 2.0 + T.plinth_over - 0.14
    pg = RL.rect("平坐勾栏", -hwx, -hdy, hwx, hdy, floor_z, closed=True)
    assign(pg, mats)

    # ---- 合并与收尾 --------------------------------------------------- #
    everything = rest + pingzuo + frame_objs + shuzuo + roof_objs + pg
    for o in everything:
        C.apply_all_modifiers(o)
    body = C.join(everything + [platform], "城门楼上善门")

    # 轻微的手绘抖动，避免轮廓线过于 CAD
    C.hand_drawn_wobble(body, amount=0.008, scale=0.9)

    log.append(f"  合模后 {len(body.data.vertices)} 顶点 / {len(body.data.polygons)} 面")
    log.append(f"  总耗时 {time.time() - t0:.1f} s")
    return body, log


def export(body):
    os.makedirs(OUT, exist_ok=True)
    paths = {}
    paths["blend"] = os.path.join(OUT, "城门楼.blend")
    bpy.ops.wm.save_as_mainfile(filepath=paths["blend"])

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body

    paths["glb"] = os.path.join(OUT, "城门楼.glb")
    bpy.ops.export_scene.gltf(filepath=paths["glb"], export_format="GLB",
                              use_selection=True, export_apply=True)

    paths["obj"] = os.path.join(OUT, "城门楼.obj")
    try:
        bpy.ops.wm.obj_export(filepath=paths["obj"], export_selected_objects=True,
                              export_materials=True)
    except AttributeError:
        bpy.ops.export_scene.obj(filepath=paths["obj"], use_selection=True)
    return paths


def main():
    body, log = build()
    paths = export(body)
    report = ["《清明上河图》城门楼 —— 构件清单", "=" * 46] + log + ["", "导出："]
    report += [f"  {k}: {v}" for k, v in paths.items()]
    text = "\n".join(report)
    print(text)
    with open(os.path.join(OUT, "构件清单.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    return body


if __name__ == "__main__":
    main()
