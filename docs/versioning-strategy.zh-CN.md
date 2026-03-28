# Versioning Strategy

[English](versioning-strategy.md) | [简体中文](versioning-strategy.zh-CN.md)

## 为什么需要这份文档

这个仓库现在已经是一个多 skill monorepo。只用一个版本号，已经不足以同时表达“仓库整体基线”和“单个 skill 的实现状态”。

## 两层版本

### 1. 仓库级发布版本

仓库级发布统一使用 Git tag，格式为 `vX.Y.Z`。

它表达的是：

- `main` 当前对外发布的基线
- 哪些 skill 与文档共同构成了一次完整发布
- `docs/releases/` 中对应 release notes 的入口

### 2. Skill 级发布版本

每个可部署 skill 保留自己的 `VERSION` 文件。

它表达的是：

- 单个 skill 当前的契约与运行时状态
- 它的 `SKILL.md`、`references/`、脚本与 metadata 已经对齐到哪个版本
- 当只讨论某一个 skill 时，用户应引用的版本

## 映射规则

仓库版本与 skill 版本不要求相同。

读取方式应当是：

- 仓库 tag 回答：“这个 repo 当前公开发布到什么状态？”
- skill 版本回答：“这个 skill 当前公开发布到什么状态？”

当前示例：

- 仓库级发布标签：`v1.1.1`
- `video-target-subtitles`：`v1.1.1`
- `video-subtitle-delivery`：`v0.1.0`

## 什么时候该升哪个版本

在以下情况下提升仓库级 tag：

- `main` 达到了一个可对外发布的完整基线
- 仓库级文档、工作流边界、skill 清单发生了实质变化
- 多个 skill 需要一起作为一次发布对外公布

在以下情况下提升某个 skill 的 `VERSION`：

- 该 skill 的运行时行为发生变化
- 该 skill 的输入/输出契约发生变化
- 该 skill 的脚本、metadata 或 reference docs 出现了值得发布的变更

大多数公开发布里，这两者都会动，但它们不应该被混成同一个概念。

## 发布清单

对于一次仓库级发布：

1. 更新或新增 `docs/releases/vX.Y.Z.md`
2. 确认 README 与贡献文档仍准确描述当前仓库基线
3. 确认每个被改动的 skill 的 `VERSION` 正确
4. 在 `main` 上提交
5. 创建并推送 Git tag

对于仓库内的 skill 级发布：

1. 更新该 skill 的 `VERSION`
2. 更新它的 `SKILL.md`、对应双语文档和相关 `references/`
3. 在需要时更新或新增 skill 专属 release notes
4. 如果这次变更需要对外发布，则把它纳入下一次仓库级发布

## 非目标

- 强迫所有 skill 共享同一个同步版本号
- 用仓库 tag 代替 skill 自己的 `VERSION`
- 把 breaking skill changes 藏进只有仓库文档变化的发布里
