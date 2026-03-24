---
name: video-subtitle-delivery
description: Create final subtitle delivery packages from a folder of local videos and matching reviewed subtitles. Generate styled ASS files from fixed presets, burn them into videos with ffmpeg/libass, export a manifest and README, and optionally zip the package. Use when subtitle QA is already complete and the user wants final delivery assets.
---

# Video Subtitle Delivery

[English](SKILL.md) | [简体中文](SKILL.zh-CN.md)

Create final delivery packages after subtitle review is already complete.

This skill consumes:

- a folder containing only target videos
- a subtitle folder containing matching reviewed `srt` and `vtt` files
- optional existing batch summaries or manifests for bookkeeping

This skill produces:

- `original_videos/`
- `subtitles/`
- `styled_ass/`
- `burned_videos/`
- `manifest.json`
- `README.md`
- optional zip packaging

This skill does not do:

- ASR
- translation
- semantic repair
- subtitle text rewriting
- timing recovery for bad subtitle files

If the subtitles are not already approved, stop and go back to `video-target-subtitles`.
If the user wants synthetic voices or multilingual dubbed masters, stop and hand the approved subtitle assets to a separate dubbing workflow.

## Runtime Setup

Read these references before first use:

- `references/delivery-layout.md`
- `references/subtitle-style-presets.md`
- `references/ffmpeg-burnin-notes.md`
- `references/font-licensing.md`

Runtime requirements:

- `ffmpeg`
- `ffprobe`
- `libass` support in ffmpeg

No network access is required by default. Online fallback font download is opt-in only.

## Workflow

1. Confirm the handoff contract:
- video directory
- subtitle directory
- target language code used in filenames
- whether the subtitles are already reviewed and approved

2. Keep the boundary narrow:
- do not rerun ASR
- do not reopen translation decisions
- do not repair subtitle prose inside the delivery skill

3. Resolve the font and preset before burn-in:

```bash
python scripts/resolve_font.py \
  --style-preset default-english-burnin
```

Font priority is:

1. bundled skill fonts under `assets/fonts/`
2. system fonts
3. online fallback only when explicitly allowed

4. Convert reviewed subtitle text into styled `ASS`:

```bash
python scripts/segments_or_srt_to_ass.py \
  output/真人.en.srt \
  delivery/demo/styled_ass/真人.en.ass \
  --video-path data/真人.mp4 \
  --font-name Arial \
  --style-preset default-english-burnin
```

5. Burn the styled subtitles into the source video:

```bash
python scripts/burn_subtitles.py \
  data/真人.mp4 \
  delivery/demo/styled_ass/真人.en.ass \
  delivery/demo/burned_videos/真人.en.hardsub.mp4
```

6. Build the full delivery package:

```bash
python scripts/create_delivery_package.py \
  --input-dir data \
  --subtitle-dir output \
  --delivery-root delivery/20260324_en_delivery \
  --target-code en \
  --style-preset default-english-burnin
```

7. Validate the finished package:

```bash
python scripts/validate_delivery.py \
  delivery/20260324_en_delivery
```

8. Zip the package only if the user asked for it:

```bash
python scripts/package_delivery.py \
  delivery/20260324_en_delivery
```

## Folder Input Semantics

When the input is a folder, the default assumption is:

- the folder contains only source videos
- videos are matched to subtitles by stem
- each video must have a matching `<stem>.<target>.srt`
- each video must have a matching `<stem>.<target>.vtt`
- each video produces one copied source video, one styled `ASS`, and one burned video
- the batch produces one unified `manifest.json`

If stem matching fails, stop with a clear error instead of guessing.

## Style Presets

Use fixed preset names. Do not improvise style values per run.

Current preset names:

- `default-english-burnin`
- `vertical-short-drama`
- `cinematic-wide`

The current default preset maps to the validated style direction:

- common English UI/video fonts first
- current preferred system hit: `Arial`
- font size at roughly `5%` of video height
- character spacing `3`
- white text at full opacity
- black outline at full opacity scaled by video height
- black shadow at about `90%` opacity with distance `5` and angle `-45°`

Known renderer constraints are documented in `references/ffmpeg-burnin-notes.md`.

## Decision Rules

- Only use this skill after subtitle QA is complete.
- Prefer `srt` as the source for `ASS` generation. Copy `vtt` alongside it for delivery.
- Keep the delivery manifest reproducible and stem-based.
- Do not silently switch to a different subtitle file when the expected one is missing.
- Treat font resolution as a deterministic step, not as an open-ended design choice.

## Output Conventions

Unless the user names a different target directory, write outputs under a folder such as `delivery/<date>_<target>_delivery/`:

- `original_videos/<stem>.<ext>`
- `subtitles/<stem>.<target>.srt`
- `subtitles/<stem>.<target>.vtt`
- `styled_ass/<stem>.<target>.ass`
- `burned_videos/<stem>.<target>.hardsub.mp4`
- `manifest.json`
- `README.md`
- optional `<delivery-root>.zip`

## Resources

- `scripts/create_delivery_package.py`: batch orchestrator for the full delivery package
- `scripts/resolve_font.py`: resolve a deterministic font choice using asset, system, or allowed fallback fonts
- `scripts/segments_or_srt_to_ass.py`: convert reviewed subtitle input into styled `ASS`
- `scripts/burn_subtitles.py`: run ffmpeg/libass burn-in for one video
- `scripts/package_delivery.py`: create a zip archive of the finished package
- `scripts/validate_delivery.py`: verify folder layout and manifest path integrity
- `references/delivery-layout.md`: directory contract and manifest expectations
- `references/subtitle-style-presets.md`: preset names and current mappings
- `references/ffmpeg-burnin-notes.md`: renderer limitations and escaping notes
- `references/font-licensing.md`: font sourcing policy and licensing guardrails

## Example Requests

- `Use $video-subtitle-delivery to package all reviewed English subtitles in output/ against the videos in data/.`
- `Use $video-subtitle-delivery to burn approved subtitles into data/动态漫B.mp4 and export a delivery folder.`
- `Use $video-subtitle-delivery to package the reviewed English subtitles into a zip for handoff.`
