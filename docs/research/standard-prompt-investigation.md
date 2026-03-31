---
title: Standard Prompt Investigation — UI Element Classification
type: research
status: in-progress
permalink: uitag/docs/research/standard-prompt-investigation
---

# Standard Prompt Investigation — UI Element Classification

_Status: Research track, in progress_
_Context: Findings from H-series test matrix (2026-03-21) and reproducibility check (2026-03-23)_

---

## The Problem

There is no field-wide standard prompt or type taxonomy for UI element classification. Every published model and benchmark uses its own prompt, making accuracy numbers incomparable. Our own experiments show prompt choice alone swings accuracy by 12 percentage points on the same model — on the single model tested (MAI-UI-2B), a larger effect than type list length.

This makes published accuracy claims in UI element classification unreliable: you can't compare a model evaluated with 10 types against one evaluated with 17 types without accounting for the type list's effect on classification odds.

---

## What We Know (from our experiments)

### Prompt Sensitivity

| Prompt | Types | Strict Accuracy | Notes |
|--------|-------|-----------------|-------|
| Binary | 2 | 84.3% | False dichotomy (text vs visual) |
| Baseline (A) | 17 | 93.2% | Broad taxonomy, recoverable errors |
| Context-aware (B) | 17 | 94.2% | Framing effect (+1pp) |
| Constrained (C) | 10 | 96.1% | Fewer bins = higher odds |

### Type Index Effects

- Fewer types produce higher strict accuracy (10 vs 17: +2.9pp). Fewer classification bins increase the probability of landing in a correct one.
- Type composition determines relaxed recovery. Prompt A includes `menu_item` (relaxable to "correct"); Prompt C uses `menu` (already strict). Same model, same crops — different relaxed scores due to type list design.
- Type list length may affect token probability. Position in the list influences likelihood. Not yet controlled for.

### Reproducibility

Zero flips at temperature=0 across 1,236 classifications confirms that accuracy differences between prompts are purely attributable to prompt design, not measurement noise.

---

## Published Precedents

### Type Taxonomies in the Literature

| Source | Types | Domain | Notes |
|--------|-------|--------|-------|
| Ferret-UI 2 (Apple, 2024) | 13 | Mobile + desktop | Strongest published precedent. Close to our 10-type Prompt C. |
| RICO (Google, 2017) | 25 | Android mobile | Annotation-level, not inference-level. Includes mobile-specific types. |
| ScreenVLM (2024) | 55 | Dense screen parsing | Most comprehensive. 0.592 PageIoU. Too granular for classification prompts. |
| MAI-UI | custom | Desktop + mobile | Model-specific prompt, not published as a standard. |
| GUI-Actor | custom | Desktop + mobile | Model-specific prompt. |
| Apple AX API | ~20 | macOS/iOS | System-level types (AXButton, AXStaticText, etc.). Ground truth reference. |

### The Sweet Spot

Our deep research synthesis (2026-03-22) suggests 13-16 types is the optimal range:
- Below 10: lose relaxed-taxonomy recovery and semantic precision
- Above 20: add mobile/web-specific types rare on desktop macOS
- Ferret-UI 2's 13-class is the strongest published precedent for a general-purpose taxonomy

---

## Research Questions

### RQ1: What is the optimal type list for macOS desktop UI?

- Map the union of Ferret-UI, RICO (desktop subset), and Apple AX types
- Identify the types that appear in 3+ taxonomies
- Test the resulting list on our 206-crop dataset (one VLM run, ~3 min)
- Compare against our Prompt A (17 types) and Prompt C (10 types)

### RQ2: Does type list length independently affect accuracy?

- Hold prompt wording constant, vary only the number of types (8, 10, 13, 17, 20)
- Measure strict accuracy at each level
- Distinguish between "fewer bins = better odds" and "better type names = better accuracy"

### RQ3: Is prompt sensitivity a recognized confound in published benchmarks?

- Survey published VLM papers for acknowledgment of prompt variance
- If unacknowledged, our data is a novel contribution: to our knowledge, the first documented evidence of 12pp prompt swing

### RQ4: Can a standard prompt be model-agnostic?

- Test the reference prompt across 2-3 models (MAI-UI-2B, possibly Qwen2.5-VL-2B, InternVL3-2B)
- If the same prompt produces comparable accuracy rankings, it's a viable standard
- If accuracy rankings flip with different prompts, that's itself a publishable finding

---

## Proposed Deliverables

1. __Standard Prompt v1__ — A reference prompt with documented type list, grounded in published taxonomies. Published on HuggingFace as a dataset card alongside benchmark data.

2. __Benchmark Methodology__ — Exact evaluation protocol: crop extraction, padding, inference parameters, scoring taxonomy. Enables reproduction by others.

3. __Prompt Sensitivity Analysis__ — Write-up of our H3 findings framed as "prompt is the largest unmeasured confounder in UI classification benchmarks."

---

## Timeline

| Phase | Work | Effort | Dependencies |
|-------|------|--------|-------------|
| 1. Taxonomy mapping | Map Ferret-UI, RICO, AX API types | Low (reading) | None |
| 2. Union/intersection | Find the common types | Low (analysis) | Phase 1 |
| 3. Candidate prompt | Draft reference prompt from union | Low | Phase 2 |
| 4. Validation run | Test candidate on 206 crops (~3 min) | Low (compute) | VLM server |
| 5. Cross-model test | Test on 2-3 models | Medium (compute) | Model availability |
| 6. Write-up | Draft the published artifact | Medium (writing) | Phases 1-4 |

Phases 1-3 require no compute and can proceed immediately. Phase 4 is a single 3-minute VLM run. Phase 5 is optional but strengthens the contribution.
