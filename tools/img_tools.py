"""Image utilities that run inside Blender's bundled Python (has numpy).

Usage:
  Blender --background --python tools/img_tools.py -- grid   <src> <out> [step]
  Blender --background --python tools/img_tools.py -- crop   <src> <out> <x> <y> <w> <h> [scale]
  Blender --background --python tools/img_tools.py -- palette <src>
  Blender --background --python tools/img_tools.py -- strips <src> <outdir>
"""
import sys
import os
import numpy as np
import bpy


def load(path):
    img = bpy.data.images.load(os.path.abspath(path))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    # Blender stores images bottom-up; flip to top-down (image/xy convention)
    return px[::-1].copy(), w, h


def save(px, path):
    h, w, _ = px.shape
    img = bpy.data.images.new("out", width=w, height=h, alpha=True)
    img.pixels = px[::-1].ravel().tolist()
    img.filepath_raw = os.path.abspath(path)
    img.file_format = "JPEG" if path.lower().endswith((".jpg", ".jpeg")) else "PNG"
    img.save()
    bpy.data.images.remove(img)


def draw_grid(px, step=100, major=500):
    out = px.copy()
    h, w, _ = out.shape
    for x in range(0, w, step):
        c = np.array([1.0, 0.0, 0.0, 1.0]) if x % major == 0 else np.array([0.0, 0.6, 1.0, 1.0])
        out[:, x] = c
    for y in range(0, h, step):
        c = np.array([1.0, 0.0, 0.0, 1.0]) if y % major == 0 else np.array([0.0, 0.6, 1.0, 1.0])
        out[y, :] = c
    # 7x7 px ticks at every major intersection for readability
    for x in range(0, w, major):
        for y in range(0, h, major):
            out[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = np.array([0.0, 1.0, 0.0, 1.0])
    return out


def crop(px, x, y, w, h, scale=1):
    sub = px[y:y + h, x:x + w]
    if scale > 1:
        sub = np.repeat(np.repeat(sub, scale, axis=0), scale, axis=1)
    return sub


def palette(px, k=12):
    """K-means-ish quick palette via coarse histogram over quantised RGB."""
    rgb = px[..., :3].reshape(-1, 3)
    q = (rgb * 16).astype(np.int32)
    keys, counts = np.unique(q, axis=0, return_counts=True)
    order = np.argsort(-counts)[:k]
    total = counts.sum()
    for i in order:
        c = keys[i] / 16.0 + 1 / 32.0
        print(f"  #{int(c[0]*255):02X}{int(c[1]*255):02X}{int(c[2]*255):02X}  "
              f"lin=({c[0]:.3f},{c[1]:.3f},{c[2]:.3f})  {counts[i]/total*100:5.2f}%")


def strips(px, outdir, n=6):
    """Stack full-width horizontal bands so limb/edge detail can be read at scale."""
    h, w, _ = px.shape
    band = h // n
    for i in range(n):
        sub = px[i * band:(i + 1) * band]
        save(sub, os.path.join(outdir, f"band_{i}_y{i*band}-{(i+1)*band}.png"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    cmd, src = argv[0], argv[1]
    px, w, h = load(src)
    print(f"[img_tools] {src}  {w}x{h}")

    if cmd == "grid":
        out = argv[2]
        step = int(argv[3]) if len(argv) > 3 else 100
        save(draw_grid(px, step), out)
    elif cmd == "crop":
        out = argv[2]
        x, y, cw, ch = (int(v) for v in argv[3:7])
        s = int(argv[7]) if len(argv) > 7 else 1
        save(crop(px, x, y, cw, ch, s), out)
    elif cmd == "palette":
        palette(px)
    elif cmd == "strips":
        os.makedirs(argv[2], exist_ok=True)
        strips(px, argv[2])


main()
