# Delivery Layout

[English](delivery-layout.md) | [简体中文](delivery-layout.zh-CN.md)

The delivery skill must produce a deterministic package layout.

## Required Structure

```text
delivery-root/
├── original_videos/
├── subtitles/
├── styled_ass/
├── burned_videos/
├── manifest.json
└── README.md
```

Optional extras:

- `fonts/` when the chosen font is copied into the package
- `<delivery-root>.zip` when packaging is requested

## Manifest Expectations

`manifest.json` should record:

- `delivery_root`
- `style_preset`
- resolved font metadata
- one entry per video with:
  - `stem`
  - `source_video`
  - copied subtitle paths
  - styled `ASS` path
  - burned video path
  - output resolution
  - applied style values

The manifest is for traceability, not for subtitle production recovery.
