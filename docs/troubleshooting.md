# Troubleshooting

Practical fixes for common issues when installing and running uitag.

---

## Requirements Checklist

Before troubleshooting, verify your environment meets these requirements:

| Requirement | Details |
|---|---|
| **macOS** | Required. Apple Vision Framework is macOS-only. |
| **Apple Silicon** | Required. MLX requires Metal GPU (M1/M2/M3/M4). Intel Macs are not supported. |
| **Python 3.10+** | Minimum version. Tested on 3.10, 3.11, 3.12, 3.13. |
| **Florence-2 model** | ~159MB, downloads automatically on first run. No manual setup needed. |

---

## Common Errors

| Error Message | Cause | Fix |
|---|---|---|
| `FileNotFoundError: Swift tool not found at .../vision-detect or .../vision-detect.swift` | The compiled Swift binary and Swift source are both missing. Package was not installed correctly, or the `uitag/tools/` directory was not included. | Reinstall the package: `uv pip install --force-reinstall uitag` (or `uv pip install -e ".[dev]"` for dev installs). |
| `FileNotFoundError: Image not found: <path>` | The image path passed to `uitag` does not exist on disk. Often caused by relative paths that resolve to the wrong directory. | Use an absolute path to the image. Verify the file exists with `ls <path>`. |
| `RuntimeError: vision-detect.swift failed (exit <code>): <stderr>` | The Swift subprocess that runs Apple Vision crashed or returned an error. Common causes: running on Linux/Windows, running on Intel Mac, corrupt image file, or missing macOS frameworks. | Verify you are on macOS with Apple Silicon. Check the image file is a valid PNG or JPEG. The stderr output in the error message contains details from the Swift process. |
| `ImportError: No module named 'mlx_vlm'` | The `mlx_vlm` dependency is not installed. This happens when running from source without installing dependencies. | Install uitag properly: `uv pip install uitag` or `uv pip install -e ".[dev]"`. The `mlx_vlm` package is a required dependency and installs automatically. |
| `RuntimeError: CoreML model not available at .../davit_encoder.mlpackage. Run: python tools/convert_davit_coreml.py` | The CoreML backend was explicitly requested (`--backend coreml`) but the converted CoreML model file does not exist. | Either run `python tools/convert_davit_coreml.py` to convert the model, or use the default MLX backend instead (`--backend mlx` or omit the flag entirely). CoreML is optional; the default MLX backend works without any conversion step. |
| `ImportError: No module named 'coremltools'` | The `coremltools` package is not installed. This only matters if you are using the CoreML backend. | Install the CoreML extras: `uv pip install uitag[coreml]`. This is optional -- the default MLX backend does not require coremltools. |
| `subprocess.TimeoutExpired` (after ~60 seconds) | The Apple Vision Swift subprocess has a 60-second timeout. This usually means the image is extremely large, corrupt, or the system is under heavy load. | Check the image file is not corrupt (`file <image.png>` should show valid PNG/JPEG). Try a smaller image. If the system is under load, wait and retry. |
| Model download hangs or fails on first run | Network issue, proxy, or Hugging Face rate limit. The Florence-2 model (~159MB) downloads from Hugging Face on first use. | Check network connectivity. If behind a proxy, set `HTTPS_PROXY`. To clear a partial download: `rm -rf ~/.cache/huggingface/hub/models--mlx-community--Florence-2-base-ft-4bit` and retry. |

---

## Model FAQ

### Why Florence-2-base, not Florence-2-large?

Florence-2-large produces degenerate output at 4-bit quantization -- specifically, repeated `<s>` tokens with no actual detections. The base model (`Florence-2-base-ft-4bit`) works correctly at 4-bit and provides good detection quality at ~159MB.

### Why is confidence fixed at 0.5 for Florence-2 detections?

Florence-2 does not emit per-box confidence scores. All Florence-2 detections are assigned a fixed `confidence=0.5`. Apple Vision detections have real confidence values from the framework.

### Can I use a different model?

Yes. Implement the `DetectionBackend` protocol defined in `uitag/backends/base.py`. Your backend needs three methods: `info()`, `warmup()`, and `detect_quadrants()`. See `examples/custom_backend.py` for a working example.

### How big is the model?

The Florence-2-base-ft-4bit model is approximately 159MB. It downloads automatically from Hugging Face on first run and is cached locally by the `transformers` library. Subsequent runs use the cached model with no network access.

---

## Performance

### Slow first run

The first invocation downloads the Florence-2 model (~159MB) from Hugging Face. This is a one-time cost. Subsequent runs use the cached model from `~/.cache/huggingface/`. If the first run takes 30+ seconds, this is the model downloading -- not a pipeline issue.

### Slow subsequent runs

If warm runs are significantly slower than expected (~2.5s accurate, ~1.7s fast on M2 Max), the GPU may be contended by other workloads. Try:

- `--backend coreml` to offload the vision encoder to the Apple Neural Engine
- `--fast` to cut Vision time from ~1s to ~213ms
- Close GPU-heavy applications (rendering, ML training)

For detailed timing breakdowns, see [Performance Benchmarks](performance.md).

---

## Detection Quality

### Few or no detections on a complex screenshot

This should not happen under normal conditions. The object-aware tiling system splits complex screenshots into quadrants to keep each tile within Florence-2's detection capacity. If you are seeing missing detections:

- Verify the image is a valid PNG or JPEG (not a PDF, TIFF, or WebP).
- Check that the image loaded correctly by inspecting the annotated SoM output.
- Try running with `--task "<OD>"` explicitly (the default).

### Duplicate detections

The pipeline deduplicates using IoU (Intersection over Union). The default threshold is 0.5. If you are seeing duplicates, the overlapping boxes may not overlap enough to trigger dedup. Lower the threshold:

```bash
uitag screenshot.png --iou 0.3
```

Lower values are more aggressive at merging overlapping boxes.

### Missing text elements

Apple Vision handles text detection. If text elements are missing:

- Try switching OCR modes. If you used `--fast`, remove it for the more thorough accurate mode. If you used accurate mode, try `--fast` -- in rare cases it captures elements the accurate pass misses.
- Very small text (under ~8px) may fall below Apple Vision's detection threshold.

### Florence-2 detections have generic labels like "computer monitor"

This is expected behavior. Florence-2 uses open-vocabulary object detection, which produces descriptive category labels rather than UI-specific labels. Labels like "computer monitor", "keyboard", or "icon" are normal. The labels describe what the model sees, not the semantic role of the UI element. The spatial coordinates (bounding boxes) are what matter for Set-of-Mark annotation.

---

## Platform Limitations

- **macOS only.** The pipeline depends on Apple Vision Framework for text and rectangle detection. There is no Linux or Windows equivalent.
- **Apple Silicon only.** MLX requires Metal GPU support, which is only available on Apple Silicon (M1 and later). Intel Macs cannot run MLX.
- **No Linux or Windows support.** Both the Apple Vision stage and the MLX inference stage are macOS/Apple Silicon-specific.
- **No iOS or iPadOS.** While Apple Vision Framework exists on iOS, the API surface differs and the Swift subprocess model does not apply to mobile platforms.
