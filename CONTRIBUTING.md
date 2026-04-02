# Contributing to uitag

uitag exists to answer one question accurately: _what UI elements are on this screen?_ Every contribution should improve the answer — better detection coverage, fewer false positives, faster inference, or clearer documentation of what the pipeline does and where it falls short.

The project runs entirely on-device. There are no cloud APIs, no network calls during inference, and no dependencies that require an internet connection at runtime. Contributions that introduce network dependencies at detection time do not fit the architecture. The pipeline targets macOS and Apple Vision as the primary detection layer, with YOLO as an opt-in second pass. Anything that lands in the default path needs to run in under two seconds on an M-series Mac.

Test coverage matters here because the pipeline has multiple stages that interact — a change to merge behavior can surface as a regression in annotation rendering. If a contribution touches detection or merging logic, it should include tests that exercise the changed behavior.

All contributions must be MIT-compatible. If you are porting logic from another project, check the license before opening a PR.

## Development Setup

```bash
git clone https://github.com/swaylenhayes/uitag.git
cd uitag
uv pip install -e ".[dev,yolo]"

# Run tests
uv run pytest

# Set up pre-commit (optional but recommended)
pip install pre-commit
pre-commit install
```

## Architecture

uitag runs a multi-stage detection pipeline:

```
Screenshot → [1] Apple Vision → [2] Merge → [3] OCR Correction → [4] Text Grouping → [5] Annotate → [6] Manifest
                              ↘ [opt] YOLO tiled detection ↗ (--yolo)
                              ↘ [legacy] Tiling → Florence-2 ↗ (--florence)
```

| Module | What it does |
|--------|-------------|
| `uitag/vision.py` | Apple Vision via Swift subprocess (text + rectangles) |
| `uitag/yolo.py` | YOLO tiled detection (640x640 tiles, cross-tile NMS) |
| `uitag/merge.py` | IoU-based deduplication with source priority |
| `uitag/correct.py` | OCR correction (Cyrillic homoglyphs, invisible Unicode, NFC) |
| `uitag/group.py` | Text block grouping (adjacent lines to paragraphs) |
| `uitag/annotate.py` | SoM numbered overlay rendering |
| `uitag/manifest.py` | JSON manifest generation |
| `uitag/run.py` | Pipeline orchestrator |
| `uitag/rescan.py` | Multi-crop OCR rescan for low-confidence text |
| `uitag/filter.py` | Florence-2 detection filtering (legacy) |
| `uitag/quadrants.py` | Object-aware image tiling for Florence-2 (legacy) |
| `uitag/florence.py` | Florence-2 detection token parsing (legacy) |
| `uitag/backends/` | `DetectionBackend` protocol + MLX/CoreML implementations |

## Making Changes

1. Create a branch: `git checkout -b feat/your-feature` or `fix/your-fix`
2. Write tests first when possible
3. Run the linter: `uv run ruff check .`
4. Run tests: `uv run pytest`
5. Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
6. Open a PR against `main`

### Test Split

Fast tests (`uv run pytest`) cover 134 cases without loading any model. Slow tests (`uv run pytest --run-slow`) load Florence-2 and require macOS with Apple Vision. CI runs fast tests only. Tests marked `@pytest.mark.slow` fall into the slow category.

## What's Welcome

Bug fixes around detection merging, tiling, and cross-tile NMS are the highest-value contributions right now. New detection backends are welcome — implement the `DetectionBackend` protocol in `uitag/backends/base.py`. Additional test coverage for edge cases in IoU merging and YOLO tile boundary handling helps catch regressions early. Documentation improvements, examples, and tutorials are always useful.

See [open issues](https://github.com/swaylenhayes/uitag/issues) for specific ideas.
