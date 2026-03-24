# Delivery Layout

[English](delivery-layout.md) | [简体中文](delivery-layout.zh-CN.md)

delivery skill 必须输出一个确定性的目录结构。

## 必需结构

```text
delivery-root/
├── original_videos/
├── subtitles/
├── styled_ass/
├── burned_videos/
├── manifest.json
└── README.md
```

可选附加项：

- 当选择的字体也被复制进包里时，额外包含 `fonts/`
- 当用户要求打包时，额外生成 `<delivery-root>.zip`

## Manifest 预期

`manifest.json` 应记录：

- `delivery_root`
- `style_preset`
- 解析出的字体元数据
- 每个视频一条记录，包含：
  - `stem`
  - `source_video`
  - 复制后的字幕路径
  - 样式化 `ASS` 路径
  - 压制视频路径
  - 输出分辨率
  - 应用的样式值

manifest 的作用是追踪和复现，不是用来做字幕生产恢复。
