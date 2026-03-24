# Workflow Overview

[English](workflow-overview.md) | [简体中文](workflow-overview.zh-CN.md)

## Why the Repository Has Two Skills

The subtitle workflow and the delivery workflow optimize for different constraints:

- subtitle production needs repeatable ASR, translation, QA, retry, and timing recovery
- delivery needs deterministic packaging, styling, burn-in, and handoff artifacts

Keeping them separate reduces rerun cost, keeps QA boundaries clear, and avoids coupling subtitle generation to packaging decisions.

## Stage Map

1. `video-target-subtitles`
   Produces multilingual subtitle assets, stage-by-stage JSON, `srt`, `vtt`, run summaries, and batch summaries.
2. Human QA or language review
   Approves subtitle text, timing, terminology, and readability.
3. `video-subtitle-delivery`
   Converts approved subtitles into styled `ASS`, burned videos, manifests, and delivery packages.
4. Downstream multilingual dubbing
   Consumes reviewed subtitles and delivery metadata as stable upstream inputs for speech synthesis, mixing, or mastering.

## Current Capability Matrix

| Capability | `video-target-subtitles` | `video-subtitle-delivery` |
| --- | --- | --- |
| Single video subtitle generation | Yes | No |
| Existing timed subtitle translation | Yes | No |
| Batch folder subtitle runs | Yes | No |
| Timing repair and subtitle lint | Yes | No |
| Styled `ASS` generation | No | Yes |
| Hard-burned subtitle video | No | Yes |
| Delivery manifest and zip | No | Yes |
| Speech synthesis dubbing | No | No |

## Dubbing Boundary

This repository now explicitly documents a multilingual dubbing handoff, but it does not pretend subtitle packaging is the same thing as dubbing.

Use this repository to prepare:

- approved multilingual subtitles
- machine-readable timing JSON
- batch summaries for reruns and traceability
- delivery manifests and burned reference videos

Use a separate dubbing system to produce:

- generated speech
- voice casting and speaker mapping
- mix stems and final dubbed masters

## Recommended Operator Rule

If the user says "generate subtitles," stay in `video-target-subtitles`.

If the user says "package reviewed subtitles" or "burn them in," switch to `video-subtitle-delivery`.

If the user says "dub this video," use the subtitle skill first, finish QA, and hand the approved assets to a dedicated dubbing workflow instead of mixing those stages together inside one skill.
