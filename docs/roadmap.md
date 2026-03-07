# uitag — Roadmap

_Last updated: 2026-03-07_
_Status: v0.4.1 current. Roadmap reframed around downstream integration quality (see Reframe Notes below)._

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Detection pipeline | Stable | 1920x1080 → 151 detections in ~2.5s accurate, ~1.7s fast |
| CLI | v0.4.1 | `uitag`, `uitag batch`, `uitag benchmark`, `uitag patch`, `uitag render` |
| OCR rescan | Shipped | Multi-crop ensemble, interactive prompt, `-rescan` suffix, special-char guard |
| Backend abstraction | Complete | MLX default + CoreML option, `--backend` flag |
| JSON manifest | Stable | Schema frozen through v0.4.x — public API contract for downstream tools |
| Python library API | Exported | `from uitag import run_pipeline` — supports rescan, backend selection |
| Annotation rendering | v0.4.1 | Markers outside bboxes, contrast-aware text, dark gold replaces yellow |
| Test suite | 81 passing | 1 pre-existing failure (`test_batch_cli.py`) |
| MIT license | Done | No AGPL contamination |

---

## Reframe Notes (2026-03-07)

> **Why the roadmap changed:** A downstream integration audit revealed three findings that shifted priorities:
>
> 1. **Label accuracy is the highest-leverage improvement.** Downstream tools that consume the manifest render every `label` field directly into prompts. OCR errors in labels propagate through every downstream step. The OCR correction baseline — previously equal-weighted with README polish — is now the top priority because it directly improves the data that flows through every downstream module.
>
> 2. **The manifest schema is sufficient and frozen.** Downstream consumers use `image_width`, `image_height`, `element_count`, `som_id`, `label`, `bbox`, and `source`. No new fields are needed. This means uitag's roadmap should focus on making existing fields more accurate (especially `label`), not on schema expansion.
>
> 3. **Repeated-call performance matters.** Automated workflows that call uitag after each interaction step accumulate overhead quickly. At 15 steps × ~2.5s = ~37.5s detection overhead. The ~600ms temp file I/O waste per call (mlx_vlm API limitation) becomes 9 seconds of pure waste over a session. This moves I/O optimization from "parked" to "do when repeated-call use cases emerge."
>
> 4. **Rescan has no downstream consumer yet.** No downstream tool currently branches on `confidence`. The rescan feature is currently CLI-only quality-of-life. Further rescan investment is deferred until downstream tools begin using confidence values.
>
> The reframe prioritizes: **detect accurately → test confidently → optimize for repeated calls**. README polish and validation edge cases are deferred.

---

## Tier 1 — Do Now

_Theme: improve what downstream tools actually consume, build detection quality confidence._

- [ ] **Broader screenshot testing** — Run pipeline on IDE, settings UIs, web apps in both light/dark mode. Establish a detection quality baseline with documented expected vs. actual element counts. The v0.4.1 spot-check found detection inconsistencies across different captures of the same UI — we need to understand the variance before the next feature cycle.
- [ ] **OCR correction baseline** — Minimal deterministic heuristics for common OCR confusions in UI text (`l`→`I`, Cyrillic `Т`→`T`, `w`→`W`). The v0.4.1 spot-check and rescan testing surfaced exactly these failure modes. This directly improves the `label` field that downstream tools feed into prompts. See `docs/ocr-correction-strategy.md`.
- [ ] **Fix `test_batch_cli.py`** — `test_format_summary` and `test_format_summary_no_failures` fail due to missing `total_detections` parameter. Pre-existing, straightforward fix. Broken tests erode suite confidence.

---

## Tier 2 — Do When Repeated-Call Use Cases Emerge

_Theme: prepare for repeated-call integration._

- [ ] **Temp file I/O optimization** — Eliminate ~600ms overhead from mlx_vlm's file-based API (save 4 temp PNGs, load them back). Over 15 repeated verification calls, this wastes ~9 seconds. Evaluate: can mlx_vlm accept PIL images directly? Can we memory-map the temp files? Is there a streaming interface?
- [ ] **`crop_region` parameter** — Add optional `crop_region` tuple to `run_pipeline()` for sub-image detection with automatic coordinate offset. Useful when callers outgrow the caller-side PIL crop workaround. Not building proactively — wait for demand.
- [ ] **Manifest stability doc** — Explicitly document the schema freeze for v0.4.x in `docs/api.md`. Downstream consumers depend on this contract. Any breaking change requires a versioned migration.

---

## Tier 3 — Defer

_Not blocking anything. Resume when triggered._

| Item | Why deferred | Resume trigger |
|------|-------------|----------------|
| Pipeline architecture visual | README polish, not functional | User/community request |
| Dense UI testing | Validation edge case | After Tier 1 baseline established |
| Large callout count testing | Validation edge case | After Tier 1 baseline established |
| Long value truncation testing | Validation edge case | After Tier 1 baseline established |
| Further rescan sophistication | No downstream consumer reads confidence yet | Downstream tools begin using confidence values |
| Verbose vs. non-verbose output behavior | Low-priority CLI polish | User request |
| Batch output format for low-confidence elements | Low-priority CLI polish | Batch usage patterns emerge |

---

## Completed Work

### v0.4.1 (2026-03-07)

**Release:** `docs/releases/v0.4.1.md`

- [x] Rescan special-character guard — prevents high-confidence sanitized text from replacing correct low-confidence readings
- [x] CLI UX overhaul — bold orange low-confidence header, `[id] CONF 0.xx "output"` format, interactive rescan prompt
- [x] `-rescan` output filename suffix — preserves standard outputs alongside rescan outputs
- [x] Dark gold bbox color — replaces yellow `(255,255,0)` with `(200,170,0)` for light-mode visibility
- [x] Dark mode detection hint — fires when avg brightness < 100 and low-confidence detections exist
- [x] README reorder — Why This Exists above Quick Start, Output Format after commands
- [x] `__init__.py` version synced to 0.4.1

### v0.4.0 (2026-03-06)

**Release:** `docs/releases/v0.4.0.md`

#### Feature A: Multi-Crop Ensemble OCR Rescan

**Spec:** `docs/specs/multi-scale-ocr-rescan.md` | **Research:** `docs/research/ocr-rescan-experiments.md`

- [x] Implement multi-crop ensemble re-OCR pipeline stage (`uitag/rescan.py`)
- [x] Add `--no-lang-correction` flag to Swift binary
- [x] Add `--rescan` and `--rescan <ids>` CLI flags
- [x] Add low-confidence callout to default CLI output
- [x] Confidence threshold set to 0.8
- [x] 8-phase experiment validating approach (crop sensitivity, context, light/dark mode)
- [x] Light mode OCR advantage documented in README and research

#### Feature B: Patch JSON Input (Re-Annotation)

**Spec:** `docs/specs/patch-json-input.md`

- [x] Define and validate patch JSON schema (`uitag/patch.py`)
- [x] Implement `uitag patch` subcommand (`uitag/patch_cli.py`)
- [x] Implement `uitag render` subcommand (manifest-to-image, no detection)
- [x] Output naming: `{stem}-uitag.png` + `{stem}-uitag-manifest.json`
- [x] Partial patches: unpatched elements pass through unchanged

### v0.3.x Features

- [x] Batch CLI (`uitag batch <dir>`) — v0.3.1
- [x] Benchmark CLI (`uitag benchmark`) — v0.3.1
- [x] Per-stage timing instrumentation — v0.3.1
- [x] API reference docs, performance docs, VHS demo GIF
- [x] Marker repositioning, contrast-aware text, resolved output paths
- [x] Dark mode validation, light mode validation

### Sprints 1-3 (2026-02-27)

- [x] S1: CI + documentation (GitHub Actions, hero image, README, pre-commit)
- [x] S2: Distribution (PyPI, GitHub Release, issue templates)
- [x] S3: Contributor experience (CONTRIBUTING.md, examples, JSON Schema)
- [x] Post-sprint fixes (pip install, `run_pipeline` export, license headers)

---

## Handed Off to Agent Layer

| Item | Why | Handoff doc |
|------|-----|-------------|
| PDF user-guidance generation | Requires contextual judgment, narrative, layout decisions | `docs/specs/pdf-generation-handoff.md` |
| LLM post-correction calls | Requires inference, model selection, cost management | `docs/ocr-correction-strategy.md` |
| Multi-step correction orchestration | Requires decision-making about when to rescan, escalate | `docs/ocr-correction-strategy.md` |

---

## Under Debate

| Item | Question | See |
|------|----------|-----|
| Curated domain dictionaries | UITag core, premium package, or agent layer? | `docs/ocr-correction-strategy.md` |
| Comprehensive regex patterns | Same boundary question | `docs/ocr-correction-strategy.md` |
| Who maintains curated data? | Open-source community, paid service, or agent? | `docs/ocr-correction-strategy.md` |

---

## Parked

| Item | Why parked | Resume trigger |
|------|-----------|----------------|
| CoreML as AUTO default | MLX is faster on idle GPU (benchmarked) | Profiling on M3/M4 shows otherwise |
| GPU load detection in selector | Not needed for single-user CLI | Multi-process use cases |
| Florence-2 task token exploration | Current task tokens work well | Quality issues surface |
| Parallel quadrant inference | Sequential is already ~650ms | User demand |
| Additional model support | Scope creep risk | Community requests |

---

_This is a living document. Update as the project evolves._
