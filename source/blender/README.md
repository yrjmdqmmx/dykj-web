# 鼎熠真空系统 Blender 源场景

`dingyi-vacuum-system.blend` 是官网五幕开场动画的统一源场景。它是用于表达鼎熠系统集成、精密工程、运维与交付能力的工程示意，不对应、复刻或宣称任何具体品牌及型号的内部结构。

## 可复现构建

当前资产管线锁定并验证于 Blender 5.1.x（本机为 5.1.1）。Blender 6.0 尚未纳入兼容承诺。仓库内的 `.blend` 由 Git LFS 管理；Python、预览图及最终 WebP 帧使用普通 Git。

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --factory-startup -b --python source/blender/build_dingyi_scene.py

/Applications/Blender.app/Contents/MacOS/Blender \
  --factory-startup -b source/blender/dingyi-vacuum-system.blend \
  --python tests/blender_scene_test.py
```

## 三道质量关口

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --factory-startup -b source/blender/dingyi-vacuum-system.blend \
  --python source/blender/render_previews.py

python3 -m pip install -r source/blender/requirements-preview.txt
python3 source/blender/assemble_animatic.py
python3 tests/blender_preview_test.py

/Applications/Blender.app/Contents/MacOS/Blender \
  --factory-startup -b source/blender/dingyi-vacuum-system.blend \
  --python tests/blender_preview_runtime_test.py
```

该命令在 `source/blender/previews/` 生成：

- `graybox-desktop.webp`：只检查构图、比例、轮廓和文字安全区；
- `lookdev-desktop.webp`、`mobile-lookdev.webp`：检查喷涂金属、不锈钢、橡胶、铜件、灯光与移动端独立构图；
- `act01` 至 `act05`：逐幕检查启动、流路、剖切、机械轴向拆解与完整重组；
- `five-act-animatic.webp`：由 24 个真实 Cycles 采样姿态组成、贯穿完整 96 帧时间轴的约 6 fps 低清五幕动画预览。

静帧预览默认使用 24 samples + 降噪，低清动画使用 8 samples；源场景和最终序列固定为 Cycles、AgX、64 samples + 降噪。可通过 `DINGYI_PREVIEW_SAMPLES=32` 提高静帧预览采样。

预览静帧先写临时文件，动画姿态先写临时目录；只有整套文件完成并匹配清单后才替换上一版。可捕获的异常会立即回滚；断电或 `SIGKILL` 若恰好发生在目录切换窗口，下一次运行会先自动恢复隐藏备份。脚本退出前还会恢复场景原有的相机、帧、分辨率、采样、输出路径与材质覆盖状态。

## 场景语义

所有可见对象归入 `SYSTEM_ROOT` 下的语义分组：`SKID`、`PIPELINE`、`CHAMBER`、`PUMP_ASSEMBLY`、`INTERNALS`、`FASTENERS`、`FX` 与 `LIGHTS_CAMERA`。时间轴 1–96 帧包含五幕标记；第 96 帧必须与第 1 帧的可拆解部件变换完全一致。

不要直接在网页中加载 `.blend`。浏览器只消费 `assets/scrolly/v2/manifest.json` 声明的预渲染桌面/移动序列与海报。
