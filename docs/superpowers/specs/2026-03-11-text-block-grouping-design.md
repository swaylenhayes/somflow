---
title: 2026-03-11-text-block-grouping-design
type: note
permalink: uitag/docs/superpowers/specs/2026-03-11-text-block-grouping-design-1
---

# Text Block Grouping — Stage 4d Design

_Date: 2026-03-11_
_Status: Approved_

## Problem

Apple Vision's `VNRecognizeTextRequest` returns one observation per text line. A 4-line paragraph becomes 4 separate `vision_text` detections plus ~9 overlapping `vision_rect` detections for individual word bounding boxes. For downstream consumers, a paragraph is the meaningful unit — not 13 fragments.

Example from `tools-1.png` (Image Interpreter description):

| som_id | y   | label                                         |
|--------|-----|-----------------------------------------------|
| 15     | 189 | "Uses an LLM to analyze the image and"        |
| 19     | 215 | "generate a descriptive prompt. This"          |
| 22     | 237 | "prompt can be refined to help create new"     |
| 25     | 260 | "images with a similar look and feel."         |

Plus som_ids 16-18, 20-21, 23-24, 26-28 as word-level rectangle noise.

## Solution

New always-on pipeline stage (4d) in `uitag/group.py`. Same philosophy as OCR correction (4c) — deterministic, no flags, zero risk of degrading output.

### Algorithm

1. Separate `vision_text` detections from all other sources.
2. Sort text detections by y-position.
3. Walk through sorted list, growing groups when the next line meets **both**:
   - **Vertical proximity**: gap between bottom of current line and top of next line < 1.0x current line height.
   - **Left-alignment**: x-start within 20px of the group's first line.
4. For groups of 2+ lines, emit a single `Detection`:
   - **Label**: space-joined text from all lines.
   - **Bbox**: union of all line bounding boxes.
   - **Source**: `"vision_text_block"`.
   - **Confidence**: minimum of the group's confidences.
5. Single lines pass through unchanged as `"vision_text"`.
6. Remove any `vision_rect` that is >=85% contained within a text block's bounding box.
7. Re-sort all detections by position (y, x) and re-assign SoM IDs.

### Why 1.0x Gap Factor

Testing against both `tools-1.png` and `tools-1-r1.png` manifests:

- Body text lines have gaps of 1-7px with line heights of 16-23px. 1.0x merges them.
- "CLIP Score" header (h=24) to its description body has a gap of 34px. At 1.5x it would merge (36 > 34). At 1.0x it stays separate (24 < 34).
- "Image Interpreter" header (h=26) to body has a gap of 42px. Stays separate at any reasonable factor.

1.0x correctly separates section headers from body text in all tested cases.

### Contained Rectangle Absorption

After text blocks are formed, `vision_rect` detections are checked for containment. A rectangle is absorbed when >=85% of its area falls inside a text block's bounding box. This removes word-level rectangle noise while preserving structural container rectangles (which are larger and extend beyond the text block).

## Pipeline Integration

```
Stage 4c: correct_detections(merged)       -- existing
Stage 4d: group_text_blocks(merged)         -- new
Stage 5:  render_som(img, merged)           -- existing
```

In `uitag/run.py`, call `group_text_blocks()` after `correct_detections()`. Add timing keys `group_ms` (stage duration) and `groups_formed` (number of text blocks created) to the pipeline timing dict.

## File Layout

- `uitag/group.py` — `group_text_blocks()` function
- `tests/test_group.py` — unit tests

## Testing

### Unit Tests (`tests/test_group.py`)

- Groups adjacent left-aligned text lines into a block
- Does NOT group lines with large vertical gaps (header vs body)
- Does NOT group lines with different x-alignment
- Single text lines pass through unchanged
- Space-joined label reads as natural prose
- Contained `vision_rect` detections are absorbed
- Non-contained rects (structural containers) are preserved
- SoM IDs are re-assigned after grouping
- Empty input returns empty
- Florence and other non-text sources are untouched

### Integration Verification

Re-run on `tools-1.png` and `tools-1-r1.png`, confirm:

- Image Interpreter description becomes 1 text block (was 4 lines + ~9 rects)
- CLIP Score description becomes 1 text block (was 4 lines + ~8 rects)
- Section headers remain separate detections
- Total element count drops significantly

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Always-on vs flag | Always-on | Same as OCR correction — deterministic, no false positives |
| Label join | Space | Line breaks are rendering artifacts, not meaningful structure |
| Source value | `"vision_text_block"` | Distinguishes grouped paragraphs from single-line text |
| Gap factor | 1.0x | Separates headers from body text in all tested cases |
| X-alignment tolerance | 20px | Accounts for minor rendering variance across lines |
| Rect absorption threshold | 85% containment | Removes word-level noise, preserves structural containers |
| Parameters | Configurable with defaults | `max_y_gap_factor`, `x_align_tolerance`, `containment_threshold` |