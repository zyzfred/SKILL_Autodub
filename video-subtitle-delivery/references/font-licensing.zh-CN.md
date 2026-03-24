# Font Licensing

[English](font-licensing.md) | [简体中文](font-licensing.zh-CN.md)

字体选择必须既可确定复现，又能满足授权边界。

## 优先级顺序

1. `assets/fonts/` 下自带的字体
2. 系统字体
3. 只有明确允许时才使用在线回退

## 推荐实践

- 将可自由再分发的字体放在 `assets/fonts/`
- 字体文件名尽量接近实际 family name
- 不要默认认为专有系统字体可以再分发
- 如果使用的是系统字体，记录到 manifest 中，而不是直接复制进交付包

## 当前状态

这个 skill 当前只提供一个空的 `assets/fonts/` 占位目录。如果项目需要保证某个字体存在，就把可再分发字体放进这里，并把授权说明与字体一起保存。
