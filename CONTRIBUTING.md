---
title: CONTRIBUTING
type: note
permalink: uitag/contributing
---

# Contributing to uitag

## Quick Start

```bash
# Clone and install (includes YOLO dependencies)
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

- `uv run pytest` — fast tests only (134 tests, no model required)
- `uv run pytest --run-slow` — includes tests that load Florence-2 (requires macOS + model download)

Tests marked `@pytest.mark.slow` need the Florence-2 model and a macOS system with Apple Vision. CI runs fast tests only.

## What's Welcome

- Bug fixes, especially around detection merging, tiling, or cross-tile NMS
- New detection backends (implement `DetectionBackend` protocol in `uitag/backends/base.py`)
- Test coverage for edge cases in quadrant splitting, IoU merging, YOLO tile boundary handling
- Documentation improvements, examples, and tutorials

See [open issues](https://github.com/swaylenhayes/uitag/issues) for specific ideas.
