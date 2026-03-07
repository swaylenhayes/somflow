"""Tests for patch JSON application."""

import json
import pytest
from PIL import Image

from uitag.types import Detection


def _make_det(som_id, label, conf=1.0, source="vision_text"):
    return Detection(label, 100, 100, 80, 30, conf, source, som_id=som_id)


def test_apply_patch_updates_label():
    """Patch replaces label for matching som_id."""
    from uitag.patch import apply_patch

    dets = [_make_det(7, "old_label"), _make_det(8, "unchanged")]
    patch = {"patches": [{"som_id": 7, "label": "new_label"}]}

    result = apply_patch(dets, patch)
    assert result[0].label == "new_label"
    assert result[1].label == "unchanged"


def test_apply_patch_preserves_unpatched():
    """Detections not in patch remain unchanged."""
    from uitag.patch import apply_patch

    dets = [_make_det(1, "keep"), _make_det(2, "also_keep")]
    patch = {"patches": []}

    result = apply_patch(dets, patch)
    assert result[0].label == "keep"
    assert result[1].label == "also_keep"


def test_apply_patch_hides_element():
    """Patch with hide=true removes element from result."""
    from uitag.patch import apply_patch

    dets = [_make_det(1, "visible"), _make_det(2, "hidden")]
    patch = {"patches": [{"som_id": 2, "hide": True}]}

    result = apply_patch(dets, patch)
    assert len(result) == 1
    assert result[0].som_id == 1


def test_apply_patch_multiple_fields():
    """Patch can update label and confidence."""
    from uitag.patch import apply_patch

    dets = [_make_det(7, "old", conf=0.3)]
    patch = {"patches": [{"som_id": 7, "label": "new", "confidence": 0.95}]}

    result = apply_patch(dets, patch)
    assert result[0].label == "new"
    assert result[0].confidence == 0.95


def test_apply_patch_unknown_som_id_ignored():
    """Patch entries for non-existent som_ids are silently ignored."""
    from uitag.patch import apply_patch

    dets = [_make_det(1, "existing")]
    patch = {"patches": [{"som_id": 999, "label": "ghost"}]}

    result = apply_patch(dets, patch)
    assert len(result) == 1
    assert result[0].label == "existing"


def test_load_manifest_returns_detections():
    """load_manifest parses JSON manifest into Detection list."""
    from uitag.patch import load_manifest

    manifest = {
        "image_width": 1920,
        "image_height": 1080,
        "element_count": 2,
        "elements": [
            {
                "som_id": 1,
                "label": "Submit",
                "bbox": {"x": 100, "y": 200, "width": 80, "height": 30},
                "confidence": 0.95,
                "source": "vision_text",
            },
            {
                "som_id": 2,
                "label": "rectangle",
                "bbox": {"x": 300, "y": 400, "width": 200, "height": 100},
                "confidence": 1.0,
                "source": "vision_rect",
            },
        ],
    }

    dets, width, height = load_manifest(manifest)
    assert len(dets) == 2
    assert dets[0].label == "Submit"
    assert dets[0].som_id == 1
    assert dets[0].x == 100
    assert dets[1].source == "vision_rect"
    assert width == 1920
    assert height == 1080


def test_validate_patch_schema():
    """validate_patch rejects malformed patches."""
    from uitag.patch import validate_patch

    # Missing patches key
    with pytest.raises(ValueError):
        validate_patch({"not_patches": []})

    # Patch entry missing som_id
    with pytest.raises(ValueError):
        validate_patch({"patches": [{"label": "no_id"}]})

    # Valid patch passes
    validate_patch({"patches": [{"som_id": 1, "label": "ok"}]})
