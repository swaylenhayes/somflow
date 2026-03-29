---
title: performance
type: note
permalink: uitag/docs/performance
---

# Performance Benchmarks

Timing characteristics of the uitag detection pipeline. All numbers measured on real screenshots with warm caches.

---

## TL;DR

| Mode                                   | End-to-End | Detections | Coverage (ScreenSpot-Pro) | Best For                         |
| -------------------------------------- | ---------- | ---------- | ------------------------- | -------------------------------- |
| __Vision + YOLO__ (`--yolo`)           | ~5s        | ~300       | 90.8%                     | Full coverage including icons    |
| __Vision-only__ (default)              | ~1.0s      | ~150       | 57.3%                     | Fast, no model download needed   |
| __Vision + Florence-2__ (`--florence`) | ~2.5s      | ~230       | —                         | Legacy, superseded by `--yolo`   |
| __Fast OCR__ (`--fast`)                | ~0.4s      | ~140       | —                         | Interactive use, rapid iteration |

Vision-only is the default. YOLO is opt-in via `--yolo` (requires `pip install uitag[yolo]`). Florence-2 is legacy opt-in via `--florence`.

---

## ScreenSpot-Pro Detection Coverage

Evaluated on [ScreenSpot-Pro](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro) — 1,581 targets across 26 professional applications on macOS, Windows, and Linux. Center-hit: does any detection's bounding box contain the center of the ground-truth target?

### All Platforms (1,581 targets, 26 apps)

| Mode | Text (n=977) | Icon (n=604) | Overall | Zero Detection |
| ---- | ------------ | ------------ | ------- | -------------- |
| __Vision + YOLO__ (`--yolo`) | 92.7% | 87.6% | __90.8%__ | 5.8% |
| Vision-only (default) | 66.4% | 42.5% | 57.3% | 32.9% |

### macOS Subset (604 targets, 9 apps)

| Mode | Text (n=398) | Icon (n=206) | Overall |
| ---- | ------------ | ------------ | ------- |
| Vision + YOLO | 93.7% | 87.9% | 91.7% |
| Vision-only | 71.1% | 46.6% | 62.7% |

The YOLO model closes the icon detection gap: 42.5% → 87.6% (+45.1 percentage points) across all platforms. Vision-only struggles most on Windows applications where UI conventions differ from macOS.

### Per-Application Results (Vision + YOLO, selected)

| Application | Overall | Text | Icon | Vision-only |
| ----------- | ------- | ---- | ---- | ----------- |
| Blender | 99% | 100% | 93% | 56% |
| EViews | 100% | 100% | 100% | 100% |
| Inventor | 97% | 97% | 100% | 40% |
| Linux common | 98% | 97% | 100% | 60% |
| Photoshop | 94% | 96% | 92% | 51% |
| Word | 98% | 99% | 93% | 75% |
| AutoCAD | 68% | 63% | 86% | 47% |
| FL Studio | 79% | 92% | 68% | 44% |
| VS Code | 87% | 91% | 82% | 71% |

AutoCAD (68%) and FL Studio (79%) remain the weakest — applications with highly specialized UI patterns.

### Detection Coverage vs Grounding

These numbers measure detection _coverage_ — whether any detection found the target element. The ScreenSpot-Pro leaderboard measures _grounding accuracy_ — whether a model can follow a natural language instruction to locate a specific target. Detection coverage is the ceiling for any grounding system built on uitag's SoM annotations.

---

## VLM Crop Classification (Validated, planned for v0.6.0)

Selective VLM classification of non-text UI elements using MAI-UI-2B-bf16-v2 (5.3 GB, Apache 2.0).

### Accuracy

| Configuration                | Strict | Relaxed | Parse Rate | Speed      |
| ---------------------------- | ------ | ------- | ---------- | ---------- |
| Speed (10 types, 25% pad)    | 96.1%  | 96.1%   | 100.0%     | 0.32s/crop |
| Accuracy (17 types, 25% pad) | 96.1%  | 99.0%   | 99.5%      | 0.49s/crop |

Tested on 206 icon targets from ScreenSpot-Pro macOS subset.

### Reproducibility (2026-03-23)

Both configurations were run 3 times each on the full 206 icon crops at temperature=0:

| Config   | Run 1 | Run 2 | Run 3 | Flips    |
| -------- | ----- | ----- | ----- | -------- |
| Speed    | 96.1% | 96.1% | 96.1% | 0 (0.0%) |
| Accuracy | 96.1% | 96.1% | 96.1% | 0 (0.0%) |

__Result: Zero flips across 1,236 total classifications.__ The 96.1% is a hard number — perfectly deterministic at temperature=0 on M2 Max.

### Prompt Sensitivity

Prompt choice significantly affects measured accuracy — a finding relevant to the broader VLM benchmarking community:

| Prompt                             | Types  | Strict    | Notes                |
| ---------------------------------- | ------ | --------- | -------------------- |
| Binary ("text or visual?")         | 2      | 84.3%     | False dichotomy      |
| Baseline (17 types + description)  | 17     | 93.2%     | Original prompt      |
| Context-aware (17 types + framing) | 17     | 94.2%     | +1pp from context    |
| __Constrained (10 types)__         | __10__ | __96.1%__ | __Shipping default__ |

Prompt choice alone swings accuracy by 12 percentage points on the same model. See [Standard Prompt Research](research/standard-prompt-investigation.md).

### Model Comparison

| Model                 | Strict    | Relaxed   | Speed     | Memory                   |
| --------------------- | --------- | --------- | --------- | ------------------------ |
| __MAI-UI-2B-bf16-v2__ | __96.1%__ | __99.0%__ | __0.49s__ | __5.3 GB__               |
| MAI-UI-8B-4bit        | 95.6%     | 96.1%     | 0.98s     | 30.5 GB                  |
| UGround-V1-2B         | —         | —         | —         | Dropped (grounding-only) |

The 2B model matches the 8B under relaxed taxonomy while using 6x less memory and being 2x faster. The 8B's 2.4pp strict advantage does not justify the resource cost.

---

## Cross-Benchmark Comparison

uitag was evaluated on three independent benchmarks. All measurements are detection coverage — did uitag find the target element? — not grounding accuracy.

### ScreenSpot-Pro (all platforms, n=1,581)

See the full breakdown in the Detection Coverage section above.

| Config | Text | Icon | Overall |
| ------ | ---- | ---- | ------- |
| Vision + YOLO | 92.7% | 87.6% | 90.8% |
| YOLO only | 82.4% | 75.7% | 80.1% |
| Vision only | 66.4% | 42.5% | 57.3% |

### GroundCUA (desktop, n=500 sample from 55K)

| Config | Recall@0.5 | Precision@0.5 | F1 | PageIoU |
| ------ | ---------- | ------------- | -- | ------- |
| YOLO only | 94.0% | 83.6% | 88.5% | 68.7% |
| Vision + YOLO | 89.9% | 49.0% | 63.5% | 47.2% |
| Vision only | 22.1% | — | — | 32.5% |

YOLO-only scores highest on GroundCUA because the model was trained on that distribution. The combined pipeline scores lower because Vision's text detections have different bounding box boundaries than GroundCUA annotations, hurting IoU matching. Per-category YOLO-only recall: Menu 97.9%, Button 97.2%, Sidebar 95.8%, Input 94.2%, Navigation 91.3%.

### UI-Vision (desktop, n=1,181)

| Config | Recall@0.5 |
| ------ | ---------- |
| YOLO only | 83.5% |
| Vision + YOLO | 82.0% |
| Vision only | 17.0% |

UI-Vision "basic" annotations label 1-3 target elements per image. High recall indicates the target was found; low precision is expected since uitag detects all elements on screen.

---

## YOLO Pipeline Timing

Measured on a 3840x2160 screenshot (32 tiles). M2 Max, warm cache.

| Stage | Time |
| ----- | ---- |
| Apple Vision (text + rectangles) | ~1.0s |
| YOLO tiled inference (32 tiles) | ~2.2s |
| Merge + dedup | <5ms |
| OCR correction + text grouping | <5ms |
| Annotate + manifest | <20ms |
| Total | ~3.5-5s |

Tile count scales with image resolution: 1920x1080 produces ~12 tiles, 3840x2160 produces ~32. The YOLO model runs each tile independently with cross-tile NMS at the end.

---

## Vision-Only Stage Breakdown

Measured on a 1920x1080 VS Code screenshot (~151 UI elements). M2 Max, warm cache.

| Stage                   | Accurate  | Fast (`--fast`) | Notes                                       |
| ----------------------- | --------- | --------------- | ------------------------------------------- |
| Apple Vision            | 977ms     | 213ms           | Text + rectangles via compiled Swift binary |
| OCR correction          | <1ms      | <1ms            | Cyrillic homoglyphs, invisible Unicode, NFC |
| Text block grouping     | <1ms      | <1ms            | Adjacent lines merged into paragraphs       |
| Merge + dedup           | <1ms      | <1ms            | IoU-based overlap removal                   |
| Annotate                | <1ms      | <1ms            | SoM numbered overlay rendering              |
| Manifest                | <1ms      | <1ms            | JSON output generation                      |
| __Total (Vision-only)__ | __~1.0s__ | __~0.3s__       |                                             |

### With Florence-2 (`--florence`)

| Stage            | Accurate  | Fast      | Notes                                           |
| ---------------- | --------- | --------- | ----------------------------------------------- |
| Apple Vision     | 977ms     | 213ms     | Same as above                                   |
| Florence-2 total | 1542ms    | 1452ms    | 4 quadrants + temp file I/O                     |
| -- per-quadrant  | 222ms     | 214ms     | Raw model inference per tile                    |
| -- overhead      | ~600ms    | ~600ms    | Temp file I/O, coordinate mapping               |
| Post-processing  | <5ms      | <5ms      | Correction, grouping, merge, annotate, manifest |
| __Total__        | __~2.5s__ | __~1.7s__ |                                                 |

### Detection Counts (VS Code screenshot)

| Source                            | Accurate | Fast     |
| --------------------------------- | -------- | -------- |
| Text (Vision)                     | 129      | 119      |
| Rectangles (Vision)               | 31       | 31       |
| Non-text (Florence-2, if enabled) | ~69      | ~72      |
| __Total (Vision-only)__           | __~160__ | __~150__ |
| __Total (with Florence-2)__       | __~229__ | __~222__ |

---

## Florence-2 Backend Comparison

uitag supports two Florence-2 backends. Only relevant when using `--florence`.

| Condition          | MLX         | CoreML      | Winner                    |
| ------------------ | ----------- | ----------- | ------------------------- |
| GPU idle (typical) | ~148ms/quad | ~183ms/quad | __MLX__ (1.25x faster)    |
| GPU contended      | ~188ms/quad | ~158ms/quad | __CoreML__ (1.18x faster) |

MLX runs on the GPU via Metal. CoreML offloads the DaViT vision encoder to the Apple Neural Engine (ANE).

```bash
# Force CoreML backend
uitag screenshot.png --florence --backend coreml

# Explicit MLX (same as default)
uitag screenshot.png --florence --backend mlx
```

CoreML requires a converted model at `models/davit_encoder.mlpackage`. If absent, `--backend coreml` falls back to MLX silently.

```bash
# One-time CoreML model conversion
uv run python tools/convert_davit_coreml.py
```

---

## OCR Mode Comparison

Apple Vision offers two recognition levels. The `--fast` flag selects fast mode.

|                              | Accurate (default)                          | Fast (`--fast`)                           |
| ---------------------------- | ------------------------------------------- | ----------------------------------------- |
| Vision time                  | ~977ms                                      | ~213ms                                    |
| Text quality                 | High fidelity, better with small/dense text | Noisier, may miss or misread small labels |
| Text count                   | 129                                         | 119                                       |
| Rectangle detection          | Identical                                   | Identical                                 |
| Total pipeline (Vision-only) | ~1.0s                                       | ~0.3s                                     |

__When to use each:__

- __Accurate__ (default): When downstream tasks depend on exact text content — reading labels, matching element names, extracting values from UI fields.
- __Fast__ (`--fast`): When you need element locations but not precise text — click target identification, layout analysis, element counting.

---

## Tips

| Situation                                      | Recommendation                                 |
| ---------------------------------------------- | ---------------------------------------------- |
| General use                                    | Default settings (Vision-only, accurate OCR)   |
| Need icon/button detection                     | `--yolo` (91% coverage vs 57% Vision-only)     |
| Need faster results, text quality not critical | `--fast`                                       |
| Legacy Florence-2                              | `--florence` (superseded by `--yolo`)           |
| Benchmarking                                   | Use `uitag benchmark` for full pipeline timing |

---

## Benchmark Setup

- __Hardware:__ Apple M2 Max, 96 GB unified memory
- __Image (timing):__ 1920x1080 VS Code screenshot, 3-run average, warm cache
- __Variance:__ Individual runs varied by +/- 60ms (~2-3%)
- __ScreenSpot-Pro (coverage):__ 1,581 annotations, 26 apps, macOS + Windows + Linux (MIT license)
- __ScreenSpot-Pro (macOS subset):__ 604 annotations, 9 apps
- __VLM server:__ OpenAI-compatible API, temperature=0

### Reproducing

```bash
# Vision-only (default)
uitag screenshot.png -o out/

# With Florence-2
uitag screenshot.png --florence -o out/

# Fast mode
uitag screenshot.png --fast -o out/

# Full pipeline benchmark (per-stage timing)
uitag benchmark screenshot.png --runs 3
```

Timing data appears in the CLI output with `-v` and in the `timing_ms` field of the JSON manifest.
