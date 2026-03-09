"""Deterministic OCR label corrections.

Applies high-confidence, context-free fixes to detection labels.
These corrections are always valid for Latin-script UI text — they fix
OCR artifacts that cannot be correct in any Latin-script UI.
"""

from __future__ import annotations

import copy
import unicodedata

from uitag.types import Detection

# Cyrillic characters visually identical to Latin counterparts.
# OCR engines occasionally produce these — they're never correct
# in English/Latin UI text.
_CYRILLIC_TO_LATIN = {
    "\u0410": "A",  # А
    "\u0412": "B",  # В
    "\u0421": "C",  # С
    "\u0415": "E",  # Е
    "\u041d": "H",  # Н
    "\u041a": "K",  # К
    "\u041c": "M",  # М
    "\u041e": "O",  # О
    "\u0420": "P",  # Р
    "\u0422": "T",  # Т
    "\u0425": "X",  # Х
    "\u0430": "a",  # а
    "\u0435": "e",  # е
    "\u043e": "o",  # о
    "\u0440": "p",  # р
    "\u0441": "c",  # с
    "\u0445": "x",  # х
}

# Zero-width and invisible Unicode characters that OCR may inject.
_INVISIBLE_CHARS = frozenset(
    {
        "\u200b",  # zero-width space
        "\u200c",  # zero-width non-joiner
        "\u200d",  # zero-width joiner
        "\ufeff",  # BOM / zero-width no-break space
        "\u200e",  # left-to-right mark
        "\u200f",  # right-to-left mark
        "\u00ad",  # soft hyphen
    }
)


def correct_label(label: str) -> str:
    """Apply deterministic corrections to a single OCR label."""
    if not label:
        return label

    # 1. Strip invisible Unicode characters
    text = "".join(c for c in label if c not in _INVISIBLE_CHARS)

    # 2. Replace Cyrillic homoglyphs with Latin equivalents
    text = "".join(_CYRILLIC_TO_LATIN.get(c, c) for c in text)

    # 3. Unicode NFC normalization (combine decomposed chars)
    text = unicodedata.normalize("NFC", text)

    # 4. Trim leading/trailing whitespace
    text = text.strip()

    return text


def correct_detections(
    detections: list[Detection],
) -> tuple[list[Detection], int]:
    """Apply deterministic corrections to all detection labels.

    Returns:
        (corrected_detections, correction_count)
    """
    result: list[Detection] = []
    count = 0

    for det in detections:
        new_label = correct_label(det.label)
        if new_label != det.label:
            updated = copy.copy(det)
            updated.label = new_label
            result.append(updated)
            count += 1
        else:
            result.append(det)

    return result, count
