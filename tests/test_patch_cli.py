"""Tests for patch and render CLI subcommands."""

import json
from PIL import Image

from uitag.types import Detection


def _write_manifest(tmp_path, dets, img_w=1920, img_h=1080):
    """Helper to write a test manifest file."""
    manifest = {
        "image_width": img_w,
        "image_height": img_h,
        "element_count": len(dets),
        "elements": [
            {
                "som_id": d.som_id,
                "label": d.label,
                "bbox": {"x": d.x, "y": d.y, "width": d.width, "height": d.height},
                "confidence": d.confidence,
                "source": d.source,
            }
            for d in dets
        ],
        "timing_ms": {},
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def _write_patch(tmp_path, patches):
    """Helper to write a test patch file."""
    path = tmp_path / "patch.json"
    path.write_text(json.dumps({"patches": patches}))
    return path


def test_smart_dispatch_routes_patch(monkeypatch):
    """cli.main() routes 'patch' to patch_cli."""
    import uitag.cli

    called_with = []

    def fake_patch_main(argv):
        called_with.append(argv)

    monkeypatch.setattr("uitag.patch_cli.patch_main", fake_patch_main)
    monkeypatch.setattr(
        "sys.argv",
        ["uitag", "patch", "img.png", "--manifest", "m.json", "--patch", "p.json"],
    )
    uitag.cli.main()
    assert called_with == [["img.png", "--manifest", "m.json", "--patch", "p.json"]]


def test_smart_dispatch_routes_render(monkeypatch):
    """cli.main() routes 'render' to patch_cli render mode."""
    import uitag.cli

    called_with = []

    def fake_render_main(argv):
        called_with.append(argv)

    monkeypatch.setattr("uitag.patch_cli.render_main", fake_render_main)
    monkeypatch.setattr(
        "sys.argv",
        ["uitag", "render", "img.png", "--manifest", "m.json"],
    )
    uitag.cli.main()
    assert called_with == [["img.png", "--manifest", "m.json"]]


def test_patch_cli_produces_output(tmp_path):
    """uitag patch generates re-annotated image."""
    from uitag.patch_cli import patch_main

    # Create test image
    img = Image.new("RGB", (200, 200), (200, 200, 200))
    img_path = tmp_path / "test.png"
    img.save(img_path)

    # Create manifest + patch
    dets = [Detection("old", 10, 10, 50, 20, 0.5, "vision_text", som_id=1)]
    manifest_path = _write_manifest(tmp_path, dets, 200, 200)
    patch_path = _write_patch(tmp_path, [{"som_id": 1, "label": "new"}])

    out_dir = tmp_path / "out"
    patch_main(
        [
            str(img_path),
            "--manifest",
            str(manifest_path),
            "--patch",
            str(patch_path),
            "-o",
            str(out_dir),
        ]
    )

    assert (out_dir / "test-uitag.png").exists()
    assert (out_dir / "test-uitag-manifest.json").exists()


def test_render_cli_produces_output(tmp_path):
    """uitag render generates annotated image from manifest only."""
    from uitag.patch_cli import render_main

    img = Image.new("RGB", (200, 200), (200, 200, 200))
    img_path = tmp_path / "test.png"
    img.save(img_path)

    dets = [Detection("Submit", 10, 10, 50, 20, 0.95, "vision_text", som_id=1)]
    manifest_path = _write_manifest(tmp_path, dets, 200, 200)

    out_dir = tmp_path / "out"
    render_main(
        [
            str(img_path),
            "--manifest",
            str(manifest_path),
            "-o",
            str(out_dir),
        ]
    )

    assert (out_dir / "test-uitag.png").exists()
