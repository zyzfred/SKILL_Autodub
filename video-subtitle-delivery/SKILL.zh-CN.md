---
name: video-subtitle-delivery
description: Create final subtitle delivery packages from a folder of local videos and matching reviewed subtitles. Generate styled ASS files from fixed presets, burn them into videos with ffmpeg/libass, export a manifest and README, and optionally zip the package. Use when subtitle QA is already complete and the user wants final delivery assets.
---

# Video Subtitle Delivery

[English](SKILL.md) | [简体中文](SKILL.zh-CN.md)

在字幕审核已经完成之后，生成最终交付包。

这个 skill 读取：

- 只包含目标视频的文件夹
- 与视频一一对应、且已经审核通过的 `srt` / `vtt` 字幕目录
- 可选的既有 batch summary 或 manifest，用于记账或追踪

这个 skill 产出：

- `original_videos/`
- `subtitles/`
- `styled_ass/`
- `burned_videos/`
- `manifest.json`
- `README.md`
- 可选 zip 包

这个 skill 不负责：

- ASR
- 翻译
- semantic repair
- 字幕文本重写
- 坏字幕文件的时间轴修复

如果字幕还没有审核通过，就停止并回到 `video-target-subtitles`。
如果用户要的是语音合成、换声或多语种配音母版，也应该停止并把审核后的字幕资产交给独立的配音流程。

## 运行准备

首次使用前先阅读：

- `references/delivery-layout.md`
- `references/subtitle-style-presets.md`
- `references/ffmpeg-burnin-notes.md`
- `references/font-licensing.md`

运行依赖：

- `ffmpeg`
- `ffprobe`
- `ffmpeg` 需要启用 `libass`

默认不需要联网。在线字体下载只在明确允许时启用。

## 工作流

1. 先确认交接契约：
- 视频目录
- 字幕目录
- 文件名使用的目标语言代码
- 字幕是否已经审核并批准

2. 保持边界窄：
- 不重新跑 ASR
- 不重新打开翻译决策
- 不在 delivery skill 内修字幕文案

3. 在 burn-in 前先确定字体和样式 preset：

```bash
python scripts/resolve_font.py \
  --style-preset default-english-burnin
```

字体优先级：

1. skill 自带的 `assets/fonts/`
2. 系统字体
3. 只有明确允许时，才走在线回退

4. 将审核后的字幕转成样式化 `ASS`：

```bash
python scripts/segments_or_srt_to_ass.py \
  output/真人.en.srt \
  delivery/demo/styled_ass/真人.en.ass \
  --video-path data/真人.mp4 \
  --font-name Arial \
  --style-preset default-english-burnin
```

5. 把样式化字幕压进源视频：

```bash
python scripts/burn_subtitles.py \
  data/真人.mp4 \
  delivery/demo/styled_ass/真人.en.ass \
  delivery/demo/burned_videos/真人.en.hardsub.mp4
```

6. 构建完整的 delivery 包：

```bash
python scripts/create_delivery_package.py \
  --input-dir data \
  --subtitle-dir output \
  --delivery-root delivery/20260324_en_delivery \
  --target-code en \
  --style-preset default-english-burnin
```

7. 校验交付包：

```bash
python scripts/validate_delivery.py \
  delivery/20260324_en_delivery
```

8. 只有用户明确要 zip 时才打包：

```bash
python scripts/package_delivery.py \
  delivery/20260324_en_delivery
```

## 文件夹输入语义

当输入是文件夹时，默认假设：

- 文件夹里只放源视频
- 用 stem 将视频与字幕做匹配
- 每个视频必须有对应的 `<stem>.<target>.srt`
- 每个视频必须有对应的 `<stem>.<target>.vtt`
- 每个视频生成一个复制后的源视频、一个样式化 `ASS`、一个压制视频
- 整个 batch 只生成一个统一的 `manifest.json`

如果 stem 无法匹配，直接报清晰错误，不要猜。

## 样式预设

只使用固定 preset 名称，不要每次运行都自由发挥样式值。

当前 preset 名称：

- `default-english-burnin`
- `vertical-short-drama`
- `cinematic-wide`

当前默认 preset 对应的样式方向：

- 优先使用常见英文 UI / 视频字体
- 当前偏好的系统命中：`Arial`
- 字号约为视频高度的 `5%`
- 字间距 `3`
- 白字，完全不透明
- 黑色描边，完全不透明，并按视频高度缩放
- 黑色阴影，约 `90%` 不透明，距离 `5`，角度 `-45°`

渲染器限制见 `references/ffmpeg-burnin-notes.md`。

## 决策规则

- 只有在字幕 QA 完成后才使用这个 skill
- 优先用 `srt` 作为 `ASS` 源，同时把 `vtt` 一起复制到交付目录
- delivery manifest 必须可复现，并且基于 stem
- 当预期字幕缺失时，不要静默切换到其他字幕文件
- 把字体解析视为确定性步骤，而不是开放式设计选择
- 这个 skill 的终点是字幕交付，不是语音合成配音

## 输出约定

如果用户没有指定目标目录，默认写到类似 `delivery/<date>_<target>_delivery/`：

- `original_videos/<stem>.<ext>`
- `subtitles/<stem>.<target>.srt`
- `subtitles/<stem>.<target>.vtt`
- `styled_ass/<stem>.<target>.ass`
- `burned_videos/<stem>.<target>.hardsub.mp4`
- `manifest.json`
- `README.md`
- 可选的 `<delivery-root>.zip`

## 资源

- `scripts/create_delivery_package.py`：完整交付包的 batch 编排器
- `scripts/resolve_font.py`：从资产、系统或允许的在线字体中确定性解析字体
- `scripts/segments_or_srt_to_ass.py`：把审核后的字幕输入转换成样式化 `ASS`
- `scripts/burn_subtitles.py`：对单个视频执行 ffmpeg/libass burn-in
- `scripts/package_delivery.py`：把交付包压缩成 zip
- `scripts/validate_delivery.py`：校验目录结构与 manifest 路径完整性
- `references/delivery-layout.md`：目录契约与 manifest 预期
- `references/subtitle-style-presets.md`：preset 名称与当前映射
- `references/ffmpeg-burnin-notes.md`：渲染限制与转义说明
- `references/font-licensing.md`：字体来源策略与授权边界

## 示例请求

- `Use $video-subtitle-delivery to package all reviewed English subtitles in output/ against the videos in data/.`
- `Use $video-subtitle-delivery to burn approved subtitles into data/动态漫B.mp4 and export a delivery folder.`
- `Use $video-subtitle-delivery to package the reviewed English subtitles into a zip for handoff.`
