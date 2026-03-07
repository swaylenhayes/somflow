"""Tests for multi-scale OCR rescan."""

from unittest.mock import patch
from PIL import Image

from uitag.types import Detection


def _make_det(label, x, y, w, h, conf, source="vision_text", som_id=1):
    return Detection(label, x, y, w, h, conf, source, som_id=som_id)


def test_rescan_skips_high_confidence():
    """Detections above threshold are not rescanned."""
    from uitag.rescan import rescan_low_confidence

    img = Image.new("RGB", (1920, 1080))
    dets = [_make_det("Submit", 100, 100, 80, 30, 0.95, som_id=1)]

    result = rescan_low_confidence(dets, img, threshold=0.8)
    assert result[0].label == "Submit"
    assert result[0].confidence == 0.95


def test_rescan_skips_non_text_sources():
    """Only vision_text detections are rescanned."""
    from uitag.rescan import rescan_low_confidence

    img = Image.new("RGB", (1920, 1080))
    dets = [
        _make_det("rectangle", 100, 100, 80, 30, 0.5, source="vision_rect", som_id=1),
        _make_det("monitor", 100, 100, 80, 30, 0.5, source="florence2", som_id=2),
    ]

    with patch("uitag.rescan._rescan_single") as mock:
        rescan_low_confidence(dets, img, threshold=0.8)
        mock.assert_not_called()


def test_rescan_replaces_when_confidence_improves():
    """If rescan produces higher confidence, replace label and confidence."""
    from uitag.rescan import rescan_low_confidence

    img = Image.new("RGB", (1920, 1080), color=(255, 255, 255))
    det = _make_det("([\\w_l+);", 200, 200, 120, 30, 0.30, som_id=7)

    with patch("uitag.rescan._rescan_single") as mock:
        mock.return_value = (";([\\w_]+);", 0.92)
        result = rescan_low_confidence([det], img, threshold=0.8)

    assert result[0].label == ";([\\w_]+);"
    assert result[0].confidence == 0.92
    assert result[0].som_id == 7  # preserved


def test_rescan_keeps_original_when_no_improvement():
    """If rescan doesn't improve confidence, keep original."""
    from uitag.rescan import rescan_low_confidence

    img = Image.new("RGB", (1920, 1080))
    det = _make_det("xmi-wrap", 100, 50, 120, 30, 0.85, som_id=4)

    with patch("uitag.rescan._rescan_single") as mock:
        mock.return_value = ("xmi-wrap", 0.80)  # worse
        result = rescan_low_confidence([det], img, threshold=0.9)

    assert result[0].label == "xmi-wrap"
    assert result[0].confidence == 0.85  # original kept


def test_rescan_returns_stats():
    """rescan_low_confidence returns stats dict."""
    from uitag.rescan import rescan_low_confidence

    img = Image.new("RGB", (1920, 1080))
    dets = [
        _make_det("good", 100, 100, 80, 30, 0.95, som_id=1),
        _make_det("bad", 200, 200, 80, 30, 0.30, som_id=2),
    ]

    with patch("uitag.rescan._rescan_single") as mock:
        mock.return_value = ("fixed", 0.90)
        result, stats = rescan_low_confidence(
            dets, img, threshold=0.8, return_stats=True
        )

    assert stats["total"] == 2
    assert stats["rescanned"] == 1
    assert stats["improved"] == 1


def test_find_low_confidence():
    """find_low_confidence filters correctly."""
    from uitag.rescan import find_low_confidence

    dets = [
        _make_det("good", 100, 100, 80, 30, 0.95, som_id=1),
        _make_det("bad", 200, 200, 80, 30, 0.30, som_id=2),
        _make_det("rect", 300, 300, 80, 30, 0.40, source="vision_rect", som_id=3),
    ]

    low = find_low_confidence(dets, threshold=0.8)
    assert len(low) == 1
    assert low[0].som_id == 2


def test_run_pipeline_accepts_rescan_params():
    """run_pipeline accepts rescan kwargs without error."""
    from uitag.run import run_pipeline

    import inspect
    sig = inspect.signature(run_pipeline)
    assert "rescan" in sig.parameters
    assert "rescan_threshold" in sig.parameters
    assert "rescan_ids" in sig.parameters
