# Performance Benchmarks

Timing characteristics of the uitag detection pipeline. All numbers measured on real screenshots with warm model cache (not first run).

---

## TL;DR

| Mode | End-to-End | Detections | Best For |
|------|-----------|------------|----------|
| **Accurate** | ~2551ms | ~151 | Production quality, precise text |
| **Fast** (`--fast`) | ~1695ms | ~153 | Interactive use, rapid iteration |

Apple Vision handles text and rectangles. Florence-2 handles non-text UI elements via tiled inference across 4 quadrants.

---

## Benchmark Setup

- **Hardware:** Apple M2 Max, 96 GB unified memory
- **Image:** 1920x1080 VS Code screenshot (~151 UI elements)
- **Model:** Florence-2-base-ft-4bit (~159 MB, MLX backend)
- **Runs:** 3-run average, warm model cache, no other GPU workloads active
- **Variance:** Individual runs varied by +/- 60ms end-to-end (~2-3%)
- **Date:** 2026-03-02

### Reproducing

```bash
# Accurate mode
uitag screenshot.png --output-dir out/

# Fast mode
uitag screenshot.png --output-dir out/ --fast

# Backend comparison (MLX vs CoreML)
uv run python tools/quick_benchmark.py screenshot.png
```

Timing data appears in the CLI output and in the `timing_ms` field of the JSON manifest.

---

## Stage Breakdown

| Stage | Accurate | % | Fast | % | Notes |
|-------|----------|---|------|---|-------|
| Apple Vision | 977ms | 38% | 213ms | 13% | Text recognition + rectangle detection via compiled Swift binary |
| Florence-2 total | 1542ms | 60% | 1452ms | 86% | 4 quadrants + temp file I/O + coordinate translation |
| -- per-quadrant inference | 222ms | | 214ms | | Raw model inference time per tile |
| -- overhead | ~600ms | | ~600ms | | Temp file save/load, coordinate mapping, image prep |
| Quadrant split | <1ms | <1% | <1ms | <1% | Object-aware tiling to avoid splitting UI elements |
| Merge + dedup | <1ms | <1% | <1ms | <1% | IoU-based deduplication across quadrants |
| Annotate | <1ms | <1% | <1ms | <1% | SoM numbered overlay rendering |
| Manifest | <1ms | <1% | <1ms | <1% | JSON output generation |
| **Total** | **~2551ms** | | **~1695ms** | | |

### Detection Counts

| Source | Accurate | Fast |
|--------|----------|------|
| Text (Vision) | 129 | 119 |
| Rectangles (Vision) | 31 | 31 |
| Non-text elements (Florence-2) | remaining | remaining |
| **Total** | **151** | **153** |

Fast mode produces slightly more total detections because the faster OCR pass captures fewer text elements, leaving more regions for Florence-2 to detect as non-text UI elements.

---

## Backend Comparison

uitag supports two Florence-2 backends. The default is MLX.

| Condition | MLX | CoreML | Winner |
|-----------|-----|--------|--------|
| GPU idle (typical) | ~148ms/quad | ~183ms/quad | **MLX** (1.25x faster) |
| GPU contended | ~188ms/quad | ~158ms/quad | **CoreML** (1.18x faster) |

MLX runs on the GPU via Metal. CoreML offloads the DaViT vision encoder to the Apple Neural Engine (ANE), freeing the GPU.

On a model this small (0.23B params), the ANE compute savings do not overcome the data transfer cost (numpy to ANE to numpy to MLX) when the GPU is idle. Under GPU contention from other workloads, CoreML wins by routing compute to the otherwise-idle ANE.

```bash
# Force CoreML backend
uitag screenshot.png --backend coreml

# Explicit MLX (same as default)
uitag screenshot.png --backend mlx
```

CoreML requires a converted model at `models/davit_encoder.mlpackage`. If absent, `--backend coreml` falls back to MLX silently.

```bash
# One-time CoreML model conversion
uv run python tools/convert_davit_coreml.py
```

---

## OCR Mode Comparison

Apple Vision offers two recognition levels. The `--fast` flag selects fast mode.

| | Accurate (default) | Fast (`--fast`) |
|---|---|---|
| Vision time | ~977ms | ~213ms |
| Text quality | High fidelity, better with small/dense text | Noisier, may miss or misread small labels |
| Text count | 129 | 119 |
| Rectangle detection | Identical | Identical |
| Total pipeline | ~2551ms | ~1695ms |
| Speedup | baseline | ~1.5x faster |

**When to use each:**

- **Accurate** (default): When downstream tasks depend on exact text content -- reading labels, matching element names, extracting values from UI fields.
- **Fast** (`--fast`): When you need element locations but not precise text -- click target identification, layout analysis, element counting.

---

## Optimization Notes

### Why sequential quadrants

Florence-2 quadrant inference runs sequentially (one quadrant at a time), not in parallel. This is intentional:

1. MLX models hold GPU memory for the full forward pass. Running 4 quadrants in parallel would require 4x the VRAM.
2. On Apple Silicon with unified memory, sequential inference is fast enough (~222ms/quadrant) that parallelization would add complexity without meaningful throughput gain.
3. Sequential processing keeps peak memory usage predictable.

### What the overhead is

The ~600ms overhead in Florence-2 total time (beyond raw inference) comes from:

- Saving 4 quadrant images to temp files (required by mlx_vlm's file-based API)
- Loading and preprocessing those temp files inside the model
- Coordinate translation from quadrant-local to full-image coordinates
- Image preparation (PIL operations, format conversion)

### First-run cost

The first invocation downloads the Florence-2-base-ft-4bit model (~159 MB) from Hugging Face. This is a one-time cost; subsequent runs use the cached model from `~/.cache/huggingface/`.

The pre-compiled Swift binary for Apple Vision saves ~230ms of JIT startup compared to calling Swift directly. The binary is compiled during `uv pip install` and cached.

---

## Tips

| Situation | Recommendation |
|-----------|---------------|
| General use | Default settings (accurate OCR, MLX backend) |
| Need faster results, text quality not critical | `--fast` |
| GPU busy with other work (ML training, rendering) | `--backend coreml` |
| First run on a new machine | Expect model download; second run will reflect true performance |
| Benchmarking | Use `tools/quick_benchmark.py` for backend comparison; run 3+ times for stable numbers |
