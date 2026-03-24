# Workflow Overview

[English](workflow-overview.md) | [简体中文](workflow-overview.zh-CN.md)

## 为什么仓库要拆成两个 Skill

字幕生产和最终交付优化的是两类完全不同的约束：

- 字幕生产关注可重复的 ASR、翻译、QA、重试与时间轴修复
- 交付阶段关注确定性的打包、样式、压制和交接产物

把它们拆开可以降低重跑成本，保持 QA 边界清晰，也避免让字幕生成逻辑和打包逻辑高耦合。

## 阶段划分

1. `video-target-subtitles`
   产出多语种字幕资产、分阶段 JSON、`srt`、`vtt`、单文件运行总结和 batch summary。
2. 人工 QA / 语言审核
   审核字幕文本、时间轴、术语和可读性。
3. `video-subtitle-delivery`
   将审核后的字幕转换为样式化 `ASS`、压制视频、manifest 和交付包。
4. 下游多语种配音
   把审核后的字幕和交付元数据作为稳定上游输入，用于语音合成、混流或母版制作。

## 当前能力矩阵

| 能力 | `video-target-subtitles` | `video-subtitle-delivery` |
| --- | --- | --- |
| 单视频字幕生成 | 是 | 否 |
| 现有时间轴字幕翻译 | 是 | 否 |
| 文件夹批量字幕生成 | 是 | 否 |
| 时间轴修复与字幕 lint | 是 | 否 |
| 样式化 `ASS` 生成 | 否 | 是 |
| 硬字幕视频输出 | 否 | 是 |
| Delivery manifest 与 zip | 否 | 是 |
| 语音合成配音 | 否 | 否 |

## 配音边界

这个仓库现在明确说明了“多语种配音交接”这件事，但不会把字幕打包伪装成真正的配音能力。

这个仓库负责准备：

- 审核通过的多语种字幕
- 机器可读的时间轴 JSON
- 便于重跑和追踪的 batch summary
- 交付 manifest 与硬字幕参考视频

独立的配音系统负责生成：

- 合成语音
- 配音角色与 speaker mapping
- 混音 stems 和最终配音母版

## 推荐操作规则

如果用户说“生成字幕”，就停留在 `video-target-subtitles`。

如果用户说“把审核后的字幕打包”或“压进视频里”，就切换到 `video-subtitle-delivery`。

如果用户说“给这个视频做配音”，正确路径是先用字幕 skill 生成并审核字幕，再把确认过的资产交给专门的配音流程，而不是把几个阶段硬塞进一个 skill 里。
