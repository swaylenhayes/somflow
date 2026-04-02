# Troubleshooting

## Requirements Checklist

| Requirement | Details |
|---|---|
| macOS | Required. Apple Vision Framework is macOS-only. |
| Python 3.10+ | Minimum version. Tested on 3.10, 3.11, 3.12, 3.13. |
| YOLO (optional) | `pip install uitag[yolo]` for `--yolo` flag. Model weights (18 MB) are bundled. |
| Apple Silicon (optional) | Required only for `--florence` (MLX needs Metal GPU). Vision-only and `--yolo` run on any macOS hardware. |

---

## Common Errors

| Error Message | Cause | Fix |
|---|---|---|
| `FileNotFoundError: Swift tool not found` | Compiled Swift binary and source both missing. Package not installed correctly. | Reinstall: `uv pip install --force-reinstall uitag` |
| `FileNotFoundError: Image not found: <path>` | Image path does not exist. Often a relative path resolving to the wrong directory. | Use an absolute path. Verify with `ls <path>`. |
| `RuntimeError: vision-detect.swift failed` | Swift subprocess crashed. Causes: not on macOS, corrupt image, missing frameworks. | Verify macOS. Check image is valid PNG/JPEG. Stderr in the error message has details. |
| `ImportError: No module named 'ultralytics'` | YOLO dependency not installed. | `pip install uitag[yolo]` or `pip install ultralytics` |
| `FileNotFoundError: YOLO model not found` | Model weights missing from `uitag/models/yolo-ui.pt`. | Reinstall uitag. The model is bundled with the package. |
| `ImportError: No module named 'mlx_vlm'` | Florence-2 dependency not installed. Only needed for `--florence`. | `pip install uitag` includes it. For source installs: `uv pip install -e ".[dev]"` |
| `RuntimeError: CoreML model not available` | CoreML backend requested but model not converted. | Run `python tools/convert_davit_coreml.py` or omit the `--backend coreml` flag. |
| `subprocess.TimeoutExpired` (after ~60s) | Apple Vision subprocess timed out. Image may be extremely large or corrupt. | Check image with `file <image.png>`. Try a smaller image. |

---

## Detection Quality

### Few or no detections on a complex screenshot

Vision-only mode detects text and rectangles. Icons, buttons, and visual controls without text labels are invisible to Vision. This is the expected gap that `--yolo` addresses:

```bash
# Vision-only: ~57% coverage on ScreenSpot-Pro
uitag screenshot.png -o out/

# Vision + YOLO: ~91% coverage
uitag screenshot.png --yolo -o out/
```

If detections are still missing with `--yolo`, the image may contain UI patterns not well-represented in the training data (GroundCUA). CAD applications and audio production software show the lowest coverage.

### Duplicate detections

The pipeline deduplicates using IoU (Intersection over Union). The default threshold is 0.5. If overlapping boxes survive dedup, lower the threshold:

```bash
uitag screenshot.png --iou 0.3
```

### Missing text elements

Apple Vision handles text detection. If text elements are missing, try switching OCR modes first — `--fast` is noisier but occasionally captures elements the accurate pass misses. Very small text (under ~8px) may fall below Apple Vision's detection threshold entirely. Dark mode screenshots also produce noisier OCR, so light mode is more reliable for special characters and code. See [OCR Rescan Research](research/ocr-rescan-experiments.md) for details.

### YOLO detections have class labels instead of text content

This is expected. YOLO detections have class labels (Button, Menu, Input_Elements, etc.) rather than text content. Apple Vision provides the actual text. When both detect the same element, the Vision text label takes priority in the merge step. Elements detected only by YOLO will have class labels.

### Florence-2 detections have generic labels like "computer monitor"

Florence-2 uses open-vocabulary object detection, producing descriptive labels rather than UI-specific labels. Labels like "computer monitor" or "keyboard" are normal. Florence-2 is legacy — use `--yolo` instead for better non-text detection.

---

## Performance

### Slow runs with --yolo

YOLO adds ~2-3 seconds for tiled inference. On a 3840x2160 image, the model processes ~32 tiles. On 1920x1080, ~12 tiles. Total pipeline time with `--yolo` is typically 3-5 seconds.

### Slow first run with --florence

First use of `--florence` downloads the Florence-2 model (~159MB) from Hugging Face. Subsequent runs use the cached model. Vision-only and `--yolo` have no download step.

### Slow subsequent runs

Vision-only should complete in ~1s (accurate) or ~0.3s (fast) on M2 Max. Times may be longer on Intel Macs or earlier Apple Silicon. If runs are significantly slower:

- `--fast` cuts Vision time from ~1s to ~213ms
- Close GPU-heavy applications (rendering, ML training)
- For detailed timing breakdowns, see [Performance Benchmarks](performance.md)

---

## Model FAQ

### Which detection model should I use?

| Flag | Model | Size | When to use |
|------|-------|------|-------------|
| _(none)_ | Apple Vision only | 0 | Fast (~1s), text-heavy UIs |
| `--yolo` | uitag-yolo11s-ui-detect-v1 | 18 MB (bundled) | Need icon/button coverage |
| `--florence` | Florence-2-base-ft-4bit | 159 MB (downloaded) | Legacy, superseded by `--yolo` |

### Can I use a different model?

For Florence-2 style detection: implement the `DetectionBackend` protocol defined in `uitag/backends/base.py`. See `examples/custom_backend.py`.

For YOLO: replace the model weights at `uitag/models/yolo-ui.pt` with any YOLO11-compatible `.pt` file.

---

## Platform Limitations

- macOS only. The pipeline depends on Apple Vision Framework for text and rectangle detection.
- Vision-only and `--yolo` run on any macOS hardware (Intel or Apple Silicon).
- `--florence` requires Apple Silicon (M1+) for MLX inference.
- No Linux, Windows, iOS, or iPadOS support.
