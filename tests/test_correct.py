"""Tests for deterministic OCR label corrections."""

from uitag.types import Detection


def _make_det(
    label, x=100, y=100, w=80, h=30, conf=0.9, source="vision_text", som_id=1
):
    return Detection(label, x, y, w, h, conf, source, som_id=som_id)


# --- correct_label tests ---


def test_cyrillic_uppercase_replaced():
    """Cyrillic uppercase homoglyphs are replaced with Latin equivalents."""
    from uitag.correct import correct_label

    # Cyrillic Т (U+0422) → Latin T (U+0054)
    assert correct_label("\u0422est") == "Test"
    # Cyrillic Р (U+0420) → Latin P
    assert correct_label("\u0420ython") == "Python"
    # Cyrillic С (U+0421) → Latin C
    assert correct_label("\u0421ode") == "Code"


def test_cyrillic_lowercase_replaced():
    """Cyrillic lowercase homoglyphs are replaced with Latin equivalents."""
    from uitag.correct import correct_label

    # Cyrillic а (U+0430) → Latin a
    assert correct_label("d\u0430ta") == "data"
    # Cyrillic о (U+043E) → Latin o
    assert correct_label("c\u043ede") == "code"
    # Cyrillic с (U+0441) → Latin c
    assert correct_label("\u0441onfig") == "config"


def test_cyrillic_mixed_string():
    """Multiple Cyrillic substitutions in one label."""
    from uitag.correct import correct_label

    # Cyrillic Т + е → Latin T + e
    assert correct_label("\u0422\u0435st") == "Test"


def test_invisible_chars_stripped():
    """Zero-width and invisible Unicode characters are removed."""
    from uitag.correct import correct_label

    # Zero-width space
    assert correct_label("Sub\u200bmit") == "Submit"
    # BOM
    assert correct_label("\ufeffFile") == "File"
    # Left-to-right mark
    assert correct_label("Save\u200e") == "Save"
    # Soft hyphen
    assert correct_label("set\u00adtings") == "settings"


def test_nfc_normalization():
    """Decomposed Unicode characters are composed (NFC)."""
    from uitag.correct import correct_label

    # e + combining acute (U+0065 U+0301) → é (U+00E9)
    assert correct_label("re\u0301sume\u0301") == "r\u00e9sum\u00e9"


def test_whitespace_trimmed():
    """Leading and trailing whitespace is removed."""
    from uitag.correct import correct_label

    assert correct_label("  Submit  ") == "Submit"
    assert correct_label("\tFile\n") == "File"


def test_clean_label_unchanged():
    """Labels with no issues pass through unchanged."""
    from uitag.correct import correct_label

    assert correct_label("Submit") == "Submit"
    assert correct_label(";([\\w_]+);") == ";([\\w_]+);"
    assert correct_label("") == ""


def test_special_chars_preserved():
    """Regex and special characters are not modified by corrections."""
    from uitag.correct import correct_label

    assert correct_label(";([\\w_]+);") == ";([\\w_]+);"
    assert correct_label("%TriggerValue%") == "%TriggerValue%"
    assert correct_label("xml-wrap-word") == "xml-wrap-word"


# --- correct_detections tests ---


def test_correct_detections_fixes_labels():
    """correct_detections applies fixes and returns count."""
    from uitag.correct import correct_detections

    dets = [
        _make_det("\u0422est", som_id=1),  # Cyrillic T
        _make_det("Submit", som_id=2),  # clean
        _make_det("Sub\u200bmit", som_id=3),  # zero-width space
    ]
    result, count = correct_detections(dets)

    assert count == 2
    assert result[0].label == "Test"
    assert result[1].label == "Submit"
    assert result[2].label == "Submit"


def test_correct_detections_preserves_metadata():
    """Corrected detections keep all non-label fields intact."""
    from uitag.correct import correct_detections

    det = _make_det("\u0422est", x=200, y=300, w=150, h=40, conf=0.85, som_id=7)
    result, _ = correct_detections([det])

    assert result[0].label == "Test"
    assert result[0].x == 200
    assert result[0].y == 300
    assert result[0].width == 150
    assert result[0].height == 40
    assert result[0].confidence == 0.85
    assert result[0].som_id == 7
    assert result[0].source == "vision_text"


def test_correct_detections_no_mutation():
    """Original detection objects are not mutated."""
    from uitag.correct import correct_detections

    original = _make_det("\u0422est", som_id=1)
    original_label = original.label
    correct_detections([original])

    assert original.label == original_label


def test_correct_detections_empty_list():
    """Empty detection list returns empty list and zero count."""
    from uitag.correct import correct_detections

    result, count = correct_detections([])
    assert result == []
    assert count == 0


def test_run_pipeline_has_correct_stage():
    """run_pipeline still has expected signature after integration."""
    import inspect

    from uitag.run import run_pipeline

    sig = inspect.signature(run_pipeline)
    assert "rescan" in sig.parameters
