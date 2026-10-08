# -*- coding: utf-8 -*-
"""装配城门楼并输出全部效果图。

用法：
    Blender --background --python scripts/render_views.py
    Blender --background --python scripts/render_views.py -- 快 900 700

参数：低/高（画质）、宽、高。
"""
import os
import sys

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts import build_gate as BG   # noqa: E402
from scripts import render as R        # noqa: E402

OUT = os.path.join(ROOT, "out")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    quality = argv[0] if argv else "高"
    w = int(argv[1]) if len(argv) > 1 else 1500
    h = int(argv[2]) if len(argv) > 2 else 1100
    samples = 20 if quality.startswith("快") else 64

    body, log = BG.build()
    print("\n".join(log))

    sc = bpy.context.scene
    R.setup_all(sc, res=(w, h), samples=samples, thickness=1.6)
    shots = os.path.join(OUT, "效果图")
    paths = R.render_all(sc, shots, res=(w, h))
    print(f"\n共输出 {len(paths)} 张 → {shots}")


if __name__ == "__main__":
    main()
