# 《清明上河图》城门楼 · 三维重建

把 `gate.jpg`（《清明上河图》城门楼局部）用 Blender 脚本重建成三维模型，
保留宋代官式城门的构造细节，并以程序化水墨渲染保住毛笔质感。

## 快速开始

```bash
./run.sh          # 建模 + 导出 + 出全部效果图（快档）
./run.sh 高        # 高画质出图
./run.sh 建模      # 只建模与导出
```

需要 Blender（默认 `/Applications/Blender.app/Contents/MacOS/Blender`，
可用环境变量 `BLENDER` 指定）。

## 产物

| 路径 | 内容 |
|---|---|
| `out/城门楼.blend` `.glb` `.obj` | 模型文件（84092 顶点 / 69374 面） |
| `out/效果图/` | 七张成品渲染（原画视角 / 正视 / 三分 / 铺作细部 / 俯瞰 / 门洞 / 侧后） |
| `out/构件清单.txt` | 各层标高与构件数量 |
| `docs/构造拆解.md` | **逐构件的考证、尺寸依据与实现说明（先读这份）** |
| `crops/` | 原图放大件，考证依据 |

## 形制

单檐歇山顶城楼 · 面阔三间 · 五铺作单抄单下昂 · 平坐勾栏 ·
圭形过梁式门洞 · 带收分的城台 · 侧附踏道。详见 `docs/构造拆解.md`。

## 水墨质感的实现

- **材质层**：墨量 = AO 聚墨 + 轮廓积墨 + 皴法 + 飞白（+ 城台斜向排线），
  再在绢本底色与墨色之间插值，只有最浓处压焦墨。
- **描边层**：Freestyle 分主轮廓 / 结构线 / 材质界三层，
  各挂一张程序化生成的毛笔笔触位图，再叠 Calligraphy（笔锋）、
  AlongStroke（起收）、Noise（顿挫）三个线宽修饰器。
- **合成层**：绢本底纹 + 四角压暗 + 轻微暖调。

## 代码结构

```
scripts/common.py     全局参数（材份制）与几何工具
scripts/materials.py  水墨材质工厂
scripts/brush.py      程序化笔触图 / 绢本底纹 / 暗角图
scripts/render.py     渲染、Freestyle 描边、合成、机位
scripts/build_gate.py 总装与导出
scripts/parts/        base / bracket / frame / railing / roof
tools/img_tools.py    在原图上量坐标、裁切放大、取色
```
