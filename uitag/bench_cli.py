"""uitag benchmark — CLI subcommand for pipeline performance measurement."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
from pathlib import Path

# Maps timing_ms keys to human-readable names, in display order.
STAGE_DISPLAY = [
    ("vision_ms", "Vision"),
    ("tiling_ms", "Tiling"),
    ("florence_total_ms", "Florence-2"),
    ("merge_ms", "Merge + dedup"),
    ("annotate_ms", "Annotation"),
    ("manifest_ms", "Manifest"),
]


def compute_stats(timings: list[dict]) -> dict[str, dict[str, float]]:
    """Compute mean and stddev per timing key across runs.

    Args:
        timings: List of timing_ms dicts, one per run.

    Returns:
        Dict mapping key -> {"mean": float, "stddev": float}.
    """
    all_keys: set[str] = set()
    for t in timings:
        all_keys.update(k for k, v in t.items() if isinstance(v, (int, float)))

    result = {}
    for key in all_keys:
        values = [
            t[key] for t in timings if key in t and isinstance(t[key], (int, float))
        ]
        if not values:
            continue
        mean = statistics.mean(values)
        stddev = statistics.stdev(values) if len(values) > 1 else 0.0
        result[key] = {"mean": round(mean, 1), "stddev": round(stddev, 1)}
    return result


def format_table(
    *,
    stats: dict[str, dict[str, float]],
    machine_info: dict[str, str],
    image_name: str,
    image_size: str,
    runs: int,
    warmup: int,
    detection_count: int,
    ocr_mode: str,
) -> str:
    """Render human-readable benchmark table."""
    lines = []
    chip = machine_info.get("chip", "unknown")
    macos = machine_info.get("macos", "unknown")
    lines.append(f"uitag benchmark \u2014 {chip}, macOS {macos}")
    lines.append(f"Image: {image_name} ({image_size})")
    lines.append(f"Runs:  {runs} ({warmup} warmup), OCR: {ocr_mode}")
    lines.append("")

    header = f"{'Stage':<24} {'Mean':>10} {'Stdev':>10}"
    sep = "\u2500" * len(header)
    lines.append(header)
    lines.append(sep)

    total_mean = 0.0
    total_var = 0.0
    for key, label in STAGE_DISPLAY:
        if key not in stats:
            continue
        mean = stats[key]["mean"]
        stddev = stats[key]["stddev"]
        total_mean += mean
        total_var += stddev**2
        lines.append(f"{label:<24} {mean:>8.1f}ms \u00b1{stddev:>7.1f}ms")

    lines.append(sep)
    total_stddev = total_var**0.5
    lines.append(f"{'Total':<24} {total_mean:>8.1f}ms \u00b1{total_stddev:>7.1f}ms")
    lines.append(f"Detections: {detection_count}")

    return "\n".join(lines)


def build_json_report(
    *,
    stats: dict[str, dict[str, float]],
    machine_info: dict[str, str],
    image_name: str,
    image_size: str,
    runs: int,
    warmup: int,
    detection_count: int,
    ocr_mode: str,
) -> str:
    """Build JSON benchmark report."""
    stages = {}
    total_mean = 0.0
    for key, label in STAGE_DISPLAY:
        if key not in stats:
            continue
        stages[key] = {
            "label": label,
            "mean_ms": stats[key]["mean"],
            "stddev_ms": stats[key]["stddev"],
        }
        total_mean += stats[key]["mean"]

    report = {
        "machine": machine_info,
        "image": {"name": image_name, "size": image_size},
        "config": {"runs": runs, "warmup": warmup, "ocr_mode": ocr_mode},
        "stages": stages,
        "summary": {
            "total_mean_ms": round(total_mean, 1),
            "detection_count": detection_count,
        },
    }
    return json.dumps(report, indent=2)


def get_machine_info() -> dict[str, str]:
    """Collect machine info for benchmark report."""
    import uitag

    chip = "unknown"
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            chip = result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    return {
        "chip": chip,
        "macos": platform.mac_ver()[0],
        "python": platform.python_version(),
        "uitag_version": getattr(uitag, "__version__", "unknown"),
    }


def benchmark_main(argv: list[str] | None = None) -> None:
    """Entry point for ``uitag benchmark``."""
    parser = argparse.ArgumentParser(
        prog="uitag benchmark",
        description="Benchmark the uitag detection pipeline",
    )
    parser.add_argument("image", nargs="?", help="Path to screenshot (required)")
    parser.add_argument(
        "--runs", type=int, default=3, help="Measured runs (default: 3)"
    )
    parser.add_argument(
        "--warmup", type=int, default=1, help="Warmup runs (default: 1)"
    )
    parser.add_argument("--fast", action="store_true", help="Use fast OCR mode")
    parser.add_argument(
        "--json", action="store_true", dest="json_only", help="JSON-only output"
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "coreml", "mlx"],
        default="auto",
        help="Detection backend",
    )

    args = parser.parse_args(argv)

    if args.image is None:
        print(
            "Usage: uitag benchmark <image.png> [--runs N] [--fast] [--json]",
            file=sys.stderr,
        )
        print(
            "\nNo bundled reference image yet. Provide your own screenshot.",
            file=sys.stderr,
        )
        sys.exit(1)

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    from PIL import Image

    from uitag.backends.selector import BackendPreference, select_backend

    img = Image.open(image_path)
    image_size = f"{img.size[0]}x{img.size[1]}"
    ocr_mode = "fast" if args.fast else "accurate"

    preference = BackendPreference(args.backend)
    backend = select_backend(preference=preference)

    if not args.json_only:
        print(f"Benchmarking: {image_path.name} ({image_size})")
        print(f"Backend: {backend.info().name} | OCR: {ocr_mode}")
        print(f"Runs: {args.runs} + {args.warmup} warmup\n")

    from uitag.run import run_pipeline

    # Warmup runs
    for i in range(args.warmup):
        if not args.json_only:
            print(f"  warmup {i + 1}/{args.warmup}...", end="\r")
        run_pipeline(
            str(image_path),
            recognition_level=ocr_mode,
            backend=backend,
        )
    if not args.json_only and args.warmup:
        print(f"  warmup done ({args.warmup} run{'s' if args.warmup != 1 else ''})")

    # Measured runs
    timings = []
    detection_count = 0
    for i in range(args.runs):
        if not args.json_only:
            print(f"  run {i + 1}/{args.runs}...", end="\r")
        result, _, _ = run_pipeline(
            str(image_path),
            recognition_level=ocr_mode,
            backend=backend,
        )
        timings.append(result.timing_ms)
        detection_count = len(result.detections)

    if not args.json_only:
        print(f"  {args.runs} runs complete\n")

    # Compute and display
    stats = compute_stats(timings)
    machine = get_machine_info()

    if args.json_only:
        print(
            build_json_report(
                stats=stats,
                machine_info=machine,
                image_name=image_path.name,
                image_size=image_size,
                runs=args.runs,
                warmup=args.warmup,
                detection_count=detection_count,
                ocr_mode=ocr_mode,
            )
        )
    else:
        table = format_table(
            stats=stats,
            machine_info=machine,
            image_name=image_path.name,
            image_size=image_size,
            runs=args.runs,
            warmup=args.warmup,
            detection_count=detection_count,
            ocr_mode=ocr_mode,
        )
        print(table)
        print("\nRun with --json for machine-readable output.")
