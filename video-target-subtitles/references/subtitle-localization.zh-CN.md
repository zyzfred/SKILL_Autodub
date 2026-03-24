# Subtitle Localization Reference

[English](subtitle-localization.md) | [简体中文](subtitle-localization.zh-CN.md)

## 内容

- JSON 结构
- 翻译原则
- 时间轴启发式
- 复核清单

## JSON 结构

可以使用纯列表，或使用顶层带 `segments` 数组的对象。每个 segment 至少包含：

```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.48,
      "text": "原始文本或目标语言文本"
    }
  ]
}
```

`id`、`speaker`、`source_text`、`target_text`、`notes` 等可选字段都可以保留，但 `scripts/segments_to_subtitles.py` 实际读取的只有 `start`、`end` 与 `text`。

推荐的中间文件：

- source transcript：`<stem>.source.segments.json`
- 目标语言字幕 segments：`<stem>.<target>.segments.json`

## 翻译原则

- 除非用户明确要求重排时间轴，否则保持时间戳不变
- 优先自然、可读的字幕表达，而不是逐词直译
- 保留原意、说话者态度和语体
- 专有名词和术语要保持一致
- 默认采用最小标点，除非标点确实提升理解
- 只有在语气足够强时才保留问号和感叹号
- 尽量用空格代替弱标点停顿
- 当 cue 过长时，默认优先语义换行，而不是额外拆 cue
- 语气词、口头禅只在影响语气、迟疑或剧情时保留
- 方括号音效提示只有在有助理解或无障碍时才保留

一个有用的翻译提示词骨架：

```text
Return JSON only.
Keep every segment in the same order.
Keep `start` and `end` unchanged.
Translate `text` into <target language>.
Optimize for subtitle readability rather than literal translation.
Prefer concise subtitle phrasing with minimal punctuation.
Do not insert hard line breaks.
Do not drop meaningful speaker labels or forced-caption cues.
```

## 时间轴启发式

以下规则是默认值，不是绝对值：

- 字幕时长尽量保持在 0.8 s 到 7.0 s 之间
- 避免时间重叠
- 手工调整时间轴时，gap 尽量不低于约 0.08 s
- 常规情况下优先一到两行 wrapped lines
- 拉丁文字每行尽量不超过约 42 个字符
- CJK 每行尽量不超过约 18 到 22 个字
- 大多数内容的阅读速度尽量低于约 20 字符每秒
- 如果语义完整的换行仍然超过理想行数，可以保留，并按 warning 处理

平台、受众和文字系统都可能需要覆盖这些阈值。若放宽限制，应明确记录。

## 复核清单

- 确认目标语言、locale 与语气
- 确认歌曲、屏幕文字、背景对白是否需要翻译
- 抽查重复人名、地名、术语是否一致
- 确认弱标点已经去掉，除非它确实提升清晰度
- 确认换行后的语义保持完整，即使 cue 超过理想行数
- 抽查首分钟、中间和最后一分钟是否存在 timing drift
- 对导出的字幕运行 `scripts/lint_subtitles.py`
- 在交付前，把字幕文件和视频并排打开复核一次
