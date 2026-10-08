#!/usr/bin/env bash
# 《清明上河图》城门楼 —— 一键重建
#
#   ./run.sh            # 建模 + 导出 + 出全部效果图（快档）
#   ./run.sh 高          # 高画质出图
#   ./run.sh 建模        # 只建模与导出，不出图
#
set -euo pipefail

BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if [ ! -x "$BLENDER" ]; then
  echo "找不到 Blender：$BLENDER" >&2
  echo "可用环境变量 BLENDER 指定路径。" >&2
  exit 1
fi

MODE="${1:-快}"

echo "==> 建模与导出"
"$BLENDER" --background --python scripts/build_gate.py 2>&1 | grep -vE \
  "keymap_items|fake_module|mod\.unregister|for kmi|^Blender|^Read prefs|^$" || true

if [ "$MODE" != "建模" ]; then
  echo "==> 出图（$MODE）"
  if [ "$MODE" = "高" ]; then RES="2000 1450"; else RES="1200 900"; fi
  "$BLENDER" --background --python scripts/render_views.py -- "$MODE" $RES 2>&1 | grep -vE \
    "keymap_items|fake_module|mod\.unregister|for kmi|^Blender|^Read prefs|^$" || true
fi

echo "==> 完成，产物在 out/"
ls -1 out/
