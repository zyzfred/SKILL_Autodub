# ffmpeg Burn-In Notes

[English](ffmpeg-burnin-notes.md) | [简体中文](ffmpeg-burnin-notes.zh-CN.md)

This skill targets ffmpeg with `libass`.

## Constraints

- `libass/ffmpeg` does not expose a clean independent line-spacing control
- `libass/ffmpeg` does not expose a direct "shadow blur only" setting that maps cleanly from design tools
- preset values are the closest reproducible approximation, not a field-for-field clone of a design mock

## Operational Notes

- escape `:` `,` `[` and `]` when building the `ass=` filter string
- prefer `-movflags +faststart` on the burned MP4 output
- keep audio copied through unless the user explicitly requests transcoding
- prefer `libx264` and `yuv420p` for compatibility unless the user requests something else
