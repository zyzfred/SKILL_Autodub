# Subtitle Style Presets

[English](subtitle-style-presets.md) | [简体中文](subtitle-style-presets.zh-CN.md)

The delivery skill uses fixed preset names instead of free-form styling.

## Presets

### `default-english-burnin`

- intended for standard landscape video delivery
- preferred font candidates: `Arial`, `Helvetica`, `Verdana`, `Trebuchet MS`, `Noto Sans`, `Liberation Sans`, `Source Sans 3`, `Inter`
- font size: `max(36, round(video_height * 0.05))`
- outline: `max(3.0, video_height * 0.004)`
- bottom margin: `round(video_height * 0.06)`
- character spacing: `3`
- shadow distance: `5`
- shadow angle: `-45°`

### `vertical-short-drama`

- intended for denser vertical drama framing
- slightly larger type and margin than the default preset
- outline and shadow remain deterministic

### `cinematic-wide`

- intended for wider cinematic framing
- slightly smaller type ratio than the default preset
- keeps the same contrast strategy with gentler spacing

## Renderer Notes

- text opacity is modeled through ASS alpha values
- outline opacity is kept fully opaque
- shadow opacity is approximated through ASS `BackColour` alpha and explicit shadow offsets
- line spacing is not directly controllable through libass style fields
