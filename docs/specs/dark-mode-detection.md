# Proposal: Dark Mode Detection and Light Mode Hint

> **Status:** Draft for discussion. Not yet implemented.

---

## Summary

When uitag detects that a screenshot is in dark mode and low-confidence
text elements are present, optionally suggest that light mode screenshots
may produce better OCR accuracy.

## Background

Research on Apple Vision OCR accuracy ([experiments](../research/ocr-rescan-experiments.md))
found that light mode screenshots produce measurably better results for
special characters, regex patterns, and code text. A backslash character
that was unrecoverable in dark mode across all techniques was correctly
read in light mode.

## Detection Method

Dark mode detection via average brightness of the image:

```python
from PIL import Image

def is_likely_dark_mode(image: Image.Image, threshold: int = 100) -> bool:
    """Estimate if screenshot is dark mode based on average brightness."""
    gray = image.convert("L")
    avg = sum(gray.getdata()) / (gray.width * gray.height)
    return avg < threshold
```

This is a simple heuristic — most dark mode UIs have an average brightness
well below 100 (typically 40-60), while light mode UIs are typically above
150. Edge cases (mixed themes, terminal windows) may produce intermediate
values.

## When to Fire

### Option A: Fire on low confidence only (recommended)

Only show the hint when:
1. The screenshot is detected as dark mode, AND
2. There are low-confidence text detections (below threshold)

This avoids nagging users when dark mode is working fine (e.g., simple
English text reads perfectly in dark mode).

```
Done: 151 detections in 2.4s

! 3 low-confidence detection(s):
  [7]  ";([\w_l+);"  conf: 0.30
  [27] ": (Ow_]+);"  conf: 0.50

Tip: run with --rescan to re-check at higher resolution
Note: dark mode detected — light mode screenshots typically produce
      more accurate OCR for code and special characters.
```

### Option B: Fire always on dark mode

Show a brief note whenever a dark mode screenshot is detected, regardless
of confidence levels.

```
Done: 151 detections in 2.4s
Note: light mode screenshots may improve OCR accuracy for special characters.
```

### Option C: Fire after rescan still has issues

Only show the hint when:
1. `--rescan` was used, AND
2. The screenshot is dark mode, AND
3. Some elements still have low confidence after rescan

This is the least noisy — it only fires when the user has already tried
to improve accuracy and dark mode is likely the remaining bottleneck.

## Suppressibility

The hint should be suppressible:
- `--no-hints` or `--quiet` flag to suppress all hints
- Environment variable `UITAG_NO_HINTS=1`
- Only fires once per invocation (not per element)

## Implementation Scope

- ~15 lines of code in `cli.py`
- One new function in a utility module (`uitag/hints.py` or inline)
- No new dependencies
- No pipeline changes — purely a CLI output enhancement

## Open Questions

1. Should the brightness threshold be configurable?
2. Should this be a `--verbose` only message?
3. Does "dark mode detected" feel presumptuous? Alternative phrasing:
   "Screenshot appears to have a dark background"
4. Should we track this as a manifest field (`dark_mode_detected: true`)?

---

*Created: 2026-03-08*
