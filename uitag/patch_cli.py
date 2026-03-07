"""uitag patch / uitag render -- CLI subcommands for re-annotation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from uitag.annotate import render_som
from uitag.manifest import generate_manifest
from uitag.patch import apply_patch, load_manifest, validate_patch
from uitag.types import PipelineResult


def patch_main(argv: list[str] | None = None) -> None:
    """Entry point for ``uitag patch``."""
    parser = argparse.ArgumentParser(
        prog="uitag patch",
        description="Re-annotate an image using a manifest and patch file",
    )
    parser.add_argument("image", help="Path to original screenshot")
    parser.add_argument("--manifest", "-m", required=True, help="Path to manifest JSON")
    parser.add_argument("--patch", "-p", required=True, help="Path to patch JSON")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory")

    args = parser.parse_args(argv)

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"Error: Image not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    patch_path = Path(args.patch)
    if not patch_path.exists():
        print(f"Error: Patch not found: {patch_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load inputs
    image = Image.open(img_path)
    manifest = json.loads(manifest_path.read_text())
    patch_data = json.loads(patch_path.read_text())

    try:
        validate_patch(patch_data)
    except ValueError as e:
        print(f"Error: Invalid patch file: {e}", file=sys.stderr)
        sys.exit(1)

    # Apply patch
    detections, img_w, img_h = load_manifest(manifest)
    patched = apply_patch(detections, patch_data)

    # Render
    annotated = render_som(image, patched)

    # Generate updated manifest
    result = PipelineResult(
        detections=patched,
        image_width=img_w,
        image_height=img_h,
    )
    manifest_json = generate_manifest(result)

    # Save
    stem = img_path.stem
    annotated.save(out_dir / f"{stem}-uitag.png")
    (out_dir / f"{stem}-uitag-manifest.json").write_text(manifest_json)

    count = len(patched)
    patch_count = len(patch_data["patches"])
    print(f"Patched: {patch_count} modification(s) applied to {count} elements")
    print(f"Output: 1 image, 1 manifest in {out_dir.resolve()}/")


def render_main(argv: list[str] | None = None) -> None:
    """Entry point for ``uitag render``."""
    parser = argparse.ArgumentParser(
        prog="uitag render",
        description="Render annotations on an image from an existing manifest",
    )
    parser.add_argument("image", help="Path to original screenshot")
    parser.add_argument("--manifest", "-m", required=True, help="Path to manifest JSON")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory")

    args = parser.parse_args(argv)

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"Error: Image not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load
    image = Image.open(img_path)
    manifest = json.loads(manifest_path.read_text())
    detections, img_w, img_h = load_manifest(manifest)

    # Render
    annotated = render_som(image, detections)

    # Save
    stem = img_path.stem
    annotated.save(out_dir / f"{stem}-uitag.png")

    count = len(detections)
    print(f"Rendered: {count} elements from manifest")
    print(f"Output: 1 image in {out_dir.resolve()}/")
