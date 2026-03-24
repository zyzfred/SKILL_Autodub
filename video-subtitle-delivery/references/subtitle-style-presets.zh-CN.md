# Subtitle Style Presets

[English](subtitle-style-presets.md) | [简体中文](subtitle-style-presets.zh-CN.md)

delivery skill 使用固定 preset 名称，而不是自由输入样式参数。

## Presets

### `default-english-burnin`

- 面向标准横屏视频交付
- 推荐字体候选：`Arial`、`Helvetica`、`Verdana`、`Trebuchet MS`、`Noto Sans`、`Liberation Sans`、`Source Sans 3`、`Inter`
- 字号：`max(36, round(video_height * 0.05))`
- 描边：`max(3.0, video_height * 0.004)`
- 底边距：`round(video_height * 0.06)`
- 字间距：`3`
- 阴影距离：`5`
- 阴影角度：`-45°`

### `vertical-short-drama`

- 面向更密集的竖屏短剧画面
- 相比默认 preset，字号和边距略大
- 描边和阴影仍保持确定性

### `cinematic-wide`

- 面向更宽的电影感画幅
- 字号比例略小于默认 preset
- 保持同样的高对比度策略，但间距更柔和

## 渲染器说明

- 文本透明度通过 ASS alpha 建模
- 描边透明度保持完全不透明
- 阴影透明度通过 ASS `BackColour` alpha 与明确的 shadow offset 近似
- 行距无法通过 libass 样式字段直接控制
