"""Patch application and manifest loading for re-annotation."""

from __future__ import annotations

import copy
from typing import Any

from uitag.types import Detection


def validate_patch(patch: dict) -> None:
    """Validate patch structure. Raises ValueError on invalid input."""
    if "patches" not in patch:
        raise ValueError("Patch must contain a 'patches' key")

    for entry in patch["patches"]:
        if "som_id" not in entry:
            raise ValueError(f"Patch entry missing 'som_id': {entry}")


def load_manifest(manifest: dict) -> tuple[list[Detection], int, int]:
    """Parse a manifest dict into Detection objects.

    Returns:
        (detections, image_width, image_height)
    """
    dets = []
    for elem in manifest.get("elements", []):
        bbox = elem["bbox"]
        det = Detection(
            label=elem["label"],
            x=bbox["x"],
            y=bbox["y"],
            width=bbox["width"],
            height=bbox["height"],
            confidence=elem.get("confidence", 1.0),
            source=elem.get("source", "manifest"),
            som_id=elem.get("som_id"),
        )
        dets.append(det)

    return dets, manifest.get("image_width", 0), manifest.get("image_height", 0)


def apply_patch(
    detections: list[Detection],
    patch: dict,
) -> list[Detection]:
    """Apply a patch to a list of detections.

    Supports: label, confidence, hide.
    """
    validate_patch(patch)

    patch_map: dict[int, dict[str, Any]] = {}
    for entry in patch["patches"]:
        patch_map[entry["som_id"]] = entry

    result = []
    for det in detections:
        if det.som_id in patch_map:
            entry = patch_map[det.som_id]

            if entry.get("hide", False):
                continue

            updated = copy.copy(det)
            if "label" in entry:
                updated.label = entry["label"]
            if "confidence" in entry:
                updated.confidence = entry["confidence"]

            result.append(updated)
        else:
            result.append(det)

    return result
