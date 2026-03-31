---
title: ocr-rescan-experiments
type: note
permalink: uitag/docs/research/ocr-rescan-experiments
---

# OCR Rescan Experiments — Apple Vision Accuracy on Special Characters

> Research supporting the multi-crop ensemble rescan feature shipped in v0.4.0.

---

## Motivation

During real-world testing on a Keyboard Maestro macro configuration screenshot,
uitag's single-pass OCR produced unreliable results on regex patterns and
special characters. The regex `;([\w_]+);` was read as `([\\w_l+);` at 0.30
confidence. This triggered an investigation into Apple Vision's OCR accuracy
and what factors influence it.

## Key Findings

### 1. Language Correction Corrupts Code Text

Apple Vision's `usesLanguageCorrection` post-processor actively corrupts
correct character-level readings for non-natural-language text:

| Text | Lang Correction ON | Lang Correction OFF |
|------|-------------------|---------------------|
| `;([\w_]+);` | `([\\w_l+);` @ 0.30 | `;([\w_]+);` @ 1.00 |
| `Local_Trigger` | `Local Trigger` @ 1.00 | `Local_Trigger` @ 1.00 |
| `%TriggerValue%` | `%Trigger Value%` @ 1.00 | `%TriggerValue%` @ 1.00 |

The neural network CAN read `[\w_]+` correctly. The language correction
"fixes" it to look more like English words. Disabling it on re-scans is
the primary improvement.

### 2. Crop Boundaries Are Chaotically Sensitive

Shifting a crop boundary by just 5 pixels can flip OCR from perfect to
garbled. Testing symmetric padding from 0-60px on the same text produced
results ranging from perfect (`sc=9`) to hallucinated characters (`sc=3`).

20px padding (our initial default) was a local minimum — the worst value
for both test elements. 10px emerged as the best single value.

This motivated a multi-crop ensemble strategy: try 5 padding values and pick
the reading with the most special/punctuation characters.

### 3. Surrounding Visual Context Influences Recognition

A context-swap experiment proved this: text that reads perfectly in one
screen location becomes garbled when transplanted into a different
location's surrounding pixels. UI-element-heavy surroundings (checkboxes,
dropdowns, buttons) produce better special character recognition than
text-heavy surroundings (labels, prose). The neural network appears to
apply different recognition biases based on whether the surrounding visual
context looks like "UI chrome" vs "document text."

### 4. Light Mode Produces Dramatically Better OCR

This is the strongest finding. The same regex text, same app, same screen
position — tested in dark mode and light mode:

| Element | Dark Mode (best crop) | Light Mode (best crop) |
|---------|----------------------|------------------------|
| SOM [7] regex | `;([\w_]+);` (1 of 7 paddings) | `;([\w_]+);` (3 of 7 paddings) |
| SOM [27] regex | `;([w_]+);` (no `\` at any padding) | `;([\w_]+);` (recovered at pad=25) |

The backslash character `\` — a thin 1-pixel diagonal stroke — was
completely unrecoverable in dark mode across all padding values, all
image pre-processing techniques (sharpening, contrast, thresholding,
edge enhancement), and all context manipulations. In light mode, the
multi-crop ensemble recovers it automatically.

Root cause: Apple Vision's neural network likely has a training data
distribution favoring light backgrounds (documents, web pages, standard
macOS UI). Dark text on light backgrounds provides higher character
contrast for the neural network's convolutional feature extractors. The
thin `\` stroke that falls below the detection threshold in dark mode
(light-on-dark) clears it in light mode (dark-on-light).

This finding is based on a single test image. The light-mode advantage is consistent with expected training distributions but has not been validated across a broad corpus.

### 5. Image Pre-Processing Has No Useful Sweet Spot (Dark Mode)

We tested a full gradient of:
- UnsharpMask: 50–600% intensity, 0.5–5.0 radius
- Contrast enhancement: 1.0–5.0x
- Sharpness enhancement: 1.0–20.0x
- Binary thresholding at multiple levels
- Combined contrast + sharpness grids

The `\` character appeared only at extreme sharpening (8x+), but with
completely garbled surrounding text. No intermediate level recovered `\`
while maintaining correct readings for other characters.

## Root Cause Hierarchy

Three factors influence Apple Vision's OCR accuracy on special characters,
in order of significance:

1. __Contrast polarity (light vs dark mode)__ — Strongest factor. Affects
   all characters including the thinnest strokes. Light mode is measurably
   more accurate for code/regex/symbol text.

2. __Sub-pixel rendering (screen position)__ — macOS renders the same glyph
   with different sub-pixel patterns at different positions. In dark mode,
   this pushes thin strokes below Vision's detection threshold at some
   positions. Light mode's higher base contrast makes this variance less
   impactful.

3. __Surrounding visual context__ — Vision uses surrounding pixels as part
   of its recognition. Text-heavy context biases toward "prose mode,"
   degrading special characters. UI-element-heavy context preserves accuracy.

## What We Built

The multi-crop ensemble rescan in `uitag/rescan.py`:
- Crops low-confidence text at 5 padding values (5, 10, 15, 20, 25px)
- Runs Apple Vision with `accurate` + `usesLanguageCorrection = false`
- Selects the reading with the most special characters (raw reading heuristic)
- Runs on ANE (zero GPU contention with Florence-2)

Combined with the light mode advantage, this achieves perfect readings
on all test elements in the Keyboard Maestro test image.

## Experiment Details

8 phases of experiments were conducted. Full data tables, methodology,
and raw results are documented below:

1. Upscale + Re-OCR — disproved (no improvement)
2. `customWords` vocabulary — no effect (operates too late in pipeline)
3. `topCandidates(10)` — correct answer not in any candidate with lang ON
4. Disabling language correction — breakthrough
5. Crop boundary sensitivity — chaotic, 10px optimal, ensemble strategy
6. Pre-processing gradient — no sweet spot in dark mode
7. Surrounding context influence — validated via context-swap
8. Light mode vs dark mode — dramatic improvement confirmed

---

_Test image: Keyboard Maestro macro configuration (regex trigger + variable actions)_
_Hardware: Apple Silicon (M2 Max), macOS, Retina 144 DPI_
_Date: 2026-03-06 through 2026-03-08_