# Failure Recovery

[English](failure-recovery.md) | [简体中文](failure-recovery.zh-CN.md)

字幕生产 skill 应把 batch 恢复能力视作一等路径，而不是附属功能。

## 必需行为

- 每个视频保留一个 `<stem>.run-summary.json`
- batch summary 与重量级中间 `segments.json` 分离
- 运行中断时，保留 `failed_stage` 与错误消息
- 默认支持从较后阶段重启，而不是每次都重跑 ASR

## 重启模式

从已知阶段重跑 batch：

```bash
python scripts/batch_generate_subtitles.py \
  --input-dir data \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en \
  --start-at translation
```

只重试失败项：

```bash
python scripts/retry_failed_translations.py \
  --output-dir output \
  --target-language English \
  --target-locale en-US \
  --target-code en \
  --start-at translation
```

## Summary 预期

每个 run summary 都应足以回答：

- 这份 summary 对应哪个输入文件
- 哪个阶段最后一次成功
- 哪个阶段失败
- 当前已经存在哪些最终字幕文件
- 剩余多少 lint errors 和 warnings

恢复流程不应依赖 delivery 专属文件，也不应依赖最终字幕契约之外的早期 source-stage JSON。
