# ffmpeg Burn-In Notes

[English](ffmpeg-burnin-notes.md) | [简体中文](ffmpeg-burnin-notes.zh-CN.md)

这个 skill 以带 `libass` 的 ffmpeg 为目标环境。

## 约束

- `libass/ffmpeg` 不提供干净的独立行距控制
- `libass/ffmpeg` 没有能和设计稿一一对应的“只模糊阴影”参数
- preset 值是最接近、可复现的近似值，而不是设计稿字段逐项复刻

## 操作说明

- 构造 `ass=` filter 字符串时，需要转义 `:`、`,`、`[`、`]`
- 压制输出 MP4 时，优先使用 `-movflags +faststart`
- 除非用户明确要求转码，否则尽量直接 copy 音频
- 为兼容性考虑，默认优先 `libx264` 与 `yuv420p`
