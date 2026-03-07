#!/usr/bin/env python3
"""uitag — CLI entry point.

Usage:
    uitag <image-path> [--output-dir <dir>]
    python detect.py <image-path> [--output-dir <dir>]
"""

import argparse
import json
import sys
import time
from pathlib import Path

from uitag.run import run_pipeline


def main():
    # Smart dispatch: subcommands handled before argparse
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        from uitag.batch_cli import batch_main

        batch_main(sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        from uitag.bench_cli import benchmark_main

        benchmark_main(sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "patch":
        from uitag.patch_cli import patch_main

        patch_main(sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "render":
        from uitag.patch_cli import render_main

        render_main(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(description="uitag Detection Pipeline")
    parser.add_argument("image", help="Path to screenshot")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    parser.add_argument("--task", default="<OD>", help="Florence-2 task token")
    parser.add_argument(
        "--overlap", type=int, default=50, help="Quadrant overlap pixels"
    )
    parser.add_argument("--iou", type=float, default=0.5, help="IoU dedup threshold")
    parser.add_argument(
        "--fast", action="store_true", help="Use fast OCR (less accurate, ~2-3x faster)"
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "coreml", "mlx"],
        default="auto",
        help="Detection backend: auto (default, uses MLX), coreml (ANE offload), mlx",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show element list and timing"
    )
    parser.add_argument(
        "--rescan",
        nargs="?",
        const=True,
        default=False,
        help="Re-scan low-confidence text at higher resolution (optionally specify som_ids: --rescan 7,27)",
    )
    args = parser.parse_args()

    image_path = args.image

    # Directory hint: suggest batch command
    if Path(image_path).is_dir():
        print(f"Error: {image_path} is a directory.", file=sys.stderr)
        print(f"  Did you mean: uitag batch {image_path}", file=sys.stderr)
        sys.exit(1)

    if not Path(image_path).exists():
        print(f"Error: Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from uitag.backends.selector import BackendPreference, select_backend

    preference = BackendPreference(args.backend)
    backend = select_backend(preference=preference)
    # Warm the backend import (mlx_vlm ~3s first import) before starting timer
    info = backend.info()
    ocr_mode = "fast" if args.fast else "fine"
    img_parent = str(Path(image_path).parent)
    if img_parent == ".":
        img_parent = ""
    else:
        img_parent = f" in {img_parent}/"
    print(f"Running pipeline on: {Path(image_path).name}{img_parent}")
    print(f"Backend: {info.name} ({info.device}) | OCR mode: {ocr_mode}")
    t0 = time.perf_counter()

    # Parse rescan ids if provided
    rescan_ids = None
    if args.rescan and args.rescan is not True:
        rescan_ids = [int(x) for x in str(args.rescan).split(",")]

    result, annotated, manifest = run_pipeline(
        image_path,
        florence_task=args.task,
        overlap_px=args.overlap,
        iou_threshold=args.iou,
        recognition_level="fast" if args.fast else "accurate",
        backend=backend,
        rescan=bool(args.rescan),
        rescan_threshold=0.8,
        rescan_ids=rescan_ids,
    )

    total_ms = (time.perf_counter() - t0) * 1000
    total_s = total_ms / 1000

    # Save outputs
    stem = Path(image_path).stem
    annotated_path = out_dir / f"{stem}-uitag.png"
    manifest_path = out_dir / f"{stem}-uitag-manifest.json"

    annotated.save(annotated_path)
    with open(manifest_path, "w") as f:
        f.write(manifest)

    # Punchline
    count = len(result.detections)
    done_line = f"Done: {count} detections in {total_s:.1f}s"
    if sys.stdout.isatty():
        print(f"\n\033[1;32m{done_line}\033[0m")  # bold green
    else:
        print(f"\n{done_line}")

    print(f"Output: 1 image, 1 manifest in {out_dir.resolve()}/")

    # Low-confidence callout
    from uitag.rescan import find_low_confidence

    low_conf = find_low_confidence(result.detections, threshold=0.8)
    if low_conf and not args.rescan:
        print(f"\n! {len(low_conf)} low-confidence detection(s):")
        for d in low_conf[:5]:
            print(f'  [{d.som_id}]  "{d.label}"  conf: {d.confidence:.2f}')
        if len(low_conf) > 5:
            print(f"  ... and {len(low_conf) - 5} more")
        print("\nTip: run with --rescan to re-check at higher resolution")

    # Dark mode hint (Option A: only when dark mode + low-confidence)
    if low_conf:
        from PIL import Image as _Image

        _img = _Image.open(image_path).convert("L")
        avg_brightness = sum(_img.getdata()) / (_img.width * _img.height)
        if avg_brightness < 100:
            print(
                "Note: dark background detected — light mode screenshots"
                " typically produce more accurate OCR for code and special characters."
            )

    if args.verbose:
        print(f"\nTiming: {json.dumps(result.timing_ms)}")
        print(f"\nElements ({count}):")
        show_limit = 10
        for d in result.detections[:show_limit]:
            print(
                f"  [{d.som_id}] {d.label} at ({d.x},{d.y}) {d.width}x{d.height} [{d.source}]"
            )
        remaining = count - show_limit
        if remaining > 0:
            print(f"  ... and {remaining} more (see manifest for full list)")


if __name__ == "__main__":
    main()
