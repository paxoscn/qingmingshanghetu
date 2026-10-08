# -*- coding: utf-8 -*-
"""程序化生成毛笔笔触位图，供 Freestyle 描边使用。

Freestyle 的线纹理沿笔画方向平铺：图像 X 轴 = 沿笔画方向，Y 轴 = 横跨笔画宽度。
因此生成一张“中间浓、两侧枯、纵向带飞白”的笔触图，
描出来的就不是一条均匀的 CAD 线，而是一笔有起收、有干湿的墨线。
"""
import math
import os

import bpy
import numpy as np


def _value_noise(shape, freq, seed):
    """双线性插值的值噪声（无外部依赖，确定性）。"""
    rng = np.random.RandomState(seed)
    h, w = shape
    gh, gw = max(2, int(h * freq)), max(2, int(w * freq))
    grid = rng.rand(gh, gw).astype(np.float32)
    ys = np.linspace(0, gh - 1, h, dtype=np.float32)
    xs = np.linspace(0, gw - 1, w, dtype=np.float32)
    y0 = np.floor(ys).astype(np.int32)
    x0 = np.floor(xs).astype(np.int32)
    y1 = np.minimum(y0 + 1, gh - 1)
    x1 = np.minimum(x0 + 1, gw - 1)
    fy = (ys - y0)[:, None]
    fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = grid[np.ix_(y0, x0)]
    b = grid[np.ix_(y0, x1)]
    c = grid[np.ix_(y1, x0)]
    d = grid[np.ix_(y1, x1)]
    top = a + (b - a) * fx
    bot = c + (d - c) * fx
    return top + (bot - top) * fy


def brush_stroke_bitmap(size=(56, 768), seed=7, feibai=0.55, feather=0.62,
                        taper=True):
    """生成笔触图。返回 (H, W, 4) 的 float32 RGBA。"""
    h, w = size
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]

    # 笔锋截面：中间实、两侧虚
    core = np.exp(-(yy / feather) ** 2).astype(np.float32)
    core = np.clip((core - 0.10) / 0.90, 0.0, 1.0)

    # 沿笔画的纵向抖动：行笔时压力不匀
    press = _value_noise((1, w), 0.010, seed)[0]
    press = 0.72 + 0.28 * press

    # 飞白：拉长的纵向条痕，越靠笔画边缘越枯
    streak = _value_noise((h, w), 0.004, seed + 31)
    streak = np.clip(streak * 1.25 - 0.25, 0.0, 1.0)
    edge_w = np.clip(np.abs(yy) / feather, 0.0, 1.0) ** 1.2
    gaps = 1.0 - feibai * streak * (0.35 + 0.65 * edge_w)

    alpha = core * press * gaps

    if taper:
        # 起笔略顿、收笔渐尖
        tt = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
        end = np.clip(np.minimum(tt / 0.045, (1.0 - tt) / 0.10), 0.0, 1.0)
        alpha = alpha * (0.55 + 0.45 * end)

    alpha = np.clip(alpha, 0.0, 1.0)
    ink = np.clip(alpha * 1.15, 0.0, 1.0)

    rgba = np.zeros((h, w, 4), dtype=np.float32)
    rgba[..., 0] = ink
    rgba[..., 1] = ink
    rgba[..., 2] = ink
    rgba[..., 3] = alpha
    return rgba


def save_bitmap(rgba, path):
    h, w, _ = rgba.shape
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=True)
    img.pixels = rgba[::-1].ravel().tolist()      # Blender 图像自下而上
    img.filepath_raw = os.path.abspath(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def paper_bitmap(size=(1024, 1024), seed=3, weave_px=3.0):
    """绢本底纹：细密经纬交织 + 大块陈年色斑 + 零星纤维。"""
    h, w = size
    xx = np.arange(w, dtype=np.float32)[None, :]
    yy = np.arange(h, dtype=np.float32)[:, None]
    weft = 0.5 + 0.5 * np.sin(2 * np.pi * xx / weave_px)
    warp = 0.5 + 0.5 * np.sin(2 * np.pi * yy / weave_px)
    weave = 0.5 * (weft + warp)

    blotch = _value_noise(size, 0.006, seed)
    blotch = 0.62 + 0.38 * blotch

    fiber = _value_noise(size, 0.0015, seed + 17)
    fiber = np.clip(fiber * 1.4 - 0.45, 0.0, 1.0)

    v = weave * blotch
    v = v * (1.0 - 0.28 * fiber)
    v = np.clip(v, 0.0, 1.0)

    rgba = np.zeros((h, w, 4), dtype=np.float32)
    rgba[..., 0] = v
    rgba[..., 1] = v * 0.97
    rgba[..., 2] = v * 0.90
    rgba[..., 3] = 1.0
    return rgba


def vignette_bitmap(size=(512, 512), power=1.9, floor=0.62):
    """旧绢暗角的径向渐变图（替代合成器里难用的 Blur+Mask 组合）。"""
    w, h = size
    xx = (np.arange(w, dtype=np.float32) / (w - 1)) * 2.0 - 1.0
    yy = (np.arange(h, dtype=np.float32) / (h - 1)) * 2.0 - 1.0
    r = np.sqrt(xx[None, :] ** 2 + yy[:, None] ** 2) / math.sqrt(2.0)
    v = floor + (1.0 - floor) * (1.0 - np.clip(r, 0.0, 1.0)) ** power
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    rgba[..., 0] = v
    rgba[..., 1] = v
    rgba[..., 2] = v
    rgba[..., 3] = 1.0
    return rgba


def get_paper_texture(path, name="绢本"):
    if not os.path.exists(path):
        save_bitmap(paper_bitmap(), path)
    tex = bpy.data.textures.get(name)
    if tex is None:
        tex = bpy.data.textures.new(name, type="IMAGE")
    tex.image = bpy.data.images.load(os.path.abspath(path), check_existing=True)
    tex.extension = "REPEAT"
    tex.use_alpha = True
    return tex


def get_brush_texture(path, name="毛笔笔触"):
    """生成（或复用）笔触位图，并包成 Blender 纹理数据块。"""
    if not os.path.exists(path):
        save_bitmap(brush_stroke_bitmap(), path)
    tex = bpy.data.textures.get(name)
    if tex is None:
        tex = bpy.data.textures.new(name, type="IMAGE")
    tex.image = bpy.data.images.load(os.path.abspath(path), check_existing=True)
    tex.extension = "REPEAT"
    tex.use_alpha = True
    tex.use_interpolation = True
    return tex
