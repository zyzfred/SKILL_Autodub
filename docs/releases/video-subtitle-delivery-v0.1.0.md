# Release Notes: video-subtitle-delivery v0.1.0

## English

`video-subtitle-delivery v0.1.0` is the first repository-tracked release of the subtitle delivery skill.

### What This Release Ships

- a deployable `video-subtitle-delivery/` skill folder
- deterministic delivery layout documentation
- fixed subtitle style presets
- font resolution policy and licensing notes
- scripts for `ASS` generation, burn-in, package validation, and zip packaging

### Intended Use

Use this skill only after subtitle QA is complete and the reviewed subtitle files are already approved.

### Explicit Non-Goals

- ASR
- translation
- subtitle text rewriting
- timing recovery for bad subtitle files
- speech synthesis dubbing

### Why It Exists Separately

Delivery is a downstream packaging concern. Keeping it separate from subtitle generation lowers rerun cost and avoids reopening translation decisions during export.

## 简体中文

`video-subtitle-delivery v0.1.0` 是这个仓库第一次正式纳入管理的字幕交付 skill 版本。

### 本次发布内容

- 一个可部署的 `video-subtitle-delivery/` skill 目录
- 确定性的 delivery 目录结构文档
- 固定的字幕样式预设
- 字体解析策略与授权说明
- 用于 `ASS` 生成、压制、交付校验和 zip 打包的脚本

### 适用场景

只有在字幕 QA 已经完成、审核后的字幕文件已经确认可交付时，才使用这个 skill。

### 明确的非目标

- ASR
- 翻译
- 字幕文本重写
- 坏字幕文件的时间轴修复
- 语音合成配音

### 为什么要单独拆出来

交付本质上是下游封装问题。把它和字幕生成分离，可以降低重跑成本，也避免在导出阶段重新打开翻译决策。
