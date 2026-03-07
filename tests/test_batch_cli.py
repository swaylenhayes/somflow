"""Tests for batch CLI image discovery and formatting."""

import pytest


def test_discover_images_finds_png(tmp_path):
    """Discovers .png files in a directory."""
    from uitag.batch_cli import discover_images

    (tmp_path / "a.png").write_bytes(b"fake")
    (tmp_path / "b.jpg").write_bytes(b"fake")
    (tmp_path / "readme.txt").write_bytes(b"ignore")

    images = discover_images(tmp_path)
    names = [p.name for p in images]
    assert "a.png" in names
    assert "b.jpg" in names
    assert "readme.txt" not in names


def test_discover_images_case_insensitive(tmp_path):
    """Discovers images regardless of extension case."""
    from uitag.batch_cli import discover_images

    (tmp_path / "SCREEN.PNG").write_bytes(b"fake")
    (tmp_path / "photo.JPG").write_bytes(b"fake")

    images = discover_images(tmp_path)
    assert len(images) == 2


def test_discover_images_sorted(tmp_path):
    """Results are sorted alphabetically."""
    from uitag.batch_cli import discover_images

    (tmp_path / "c.png").write_bytes(b"fake")
    (tmp_path / "a.png").write_bytes(b"fake")
    (tmp_path / "b.png").write_bytes(b"fake")

    images = discover_images(tmp_path)
    names = [p.name for p in images]
    assert names == ["a.png", "b.png", "c.png"]


def test_discover_images_empty_dir(tmp_path):
    """Empty directory returns empty list."""
    from uitag.batch_cli import discover_images

    images = discover_images(tmp_path)
    assert images == []


def test_discover_images_not_recursive(tmp_path):
    """Does not descend into subdirectories."""
    from uitag.batch_cli import discover_images

    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.png").write_bytes(b"fake")
    (tmp_path / "top.png").write_bytes(b"fake")

    images = discover_images(tmp_path)
    names = [p.name for p in images]
    assert names == ["top.png"]


# --- Progress formatting ---


def test_format_progress_success():
    """Progress line for a successful image."""
    from uitag.batch_cli import format_progress

    line = format_progress(
        index=0, total=5, name="desktop1.png", elapsed_s=1.8, count=151
    )
    assert "[1/5]" in line
    assert "desktop1.png" in line
    assert "1.8s" in line
    assert "151" in line


def test_format_progress_failure():
    """Progress line for a failed image."""
    from uitag.batch_cli import format_progress

    line = format_progress(
        index=2, total=5, name="corrupt.png", error="not a valid image"
    )
    assert "[3/5]" in line
    assert "FAILED" in line
    assert "not a valid image" in line


def test_format_summary():
    """Summary line with counts and total time."""
    from uitag.batch_cli import format_summary

    summary = format_summary(
        succeeded=4,
        failed=1,
        total_detections=42,
        total_seconds=9.5,
        output_dir="output/",
    )
    assert "42 detections" in summary
    assert "1 failed" in summary
    assert "9.5s" in summary
    assert "4 images" in summary


def test_format_summary_no_failures():
    """Summary omits failure count when all succeed."""
    from uitag.batch_cli import format_summary

    summary = format_summary(
        succeeded=3,
        failed=0,
        total_detections=30,
        total_seconds=5.2,
        output_dir="out/",
    )
    assert "30 detections" in summary
    assert "3 images" in summary
    assert "failed" not in summary


def test_batch_main_no_args_exits():
    """batch_main with no image path prints usage and exits."""
    from uitag.batch_cli import batch_main

    with pytest.raises(SystemExit) as exc:
        batch_main([])
    assert exc.value.code != 0


def test_batch_main_nonexistent_path_exits():
    """batch_main with nonexistent path exits with error."""
    from uitag.batch_cli import batch_main

    with pytest.raises(SystemExit):
        batch_main(["/nonexistent/path"])


# --- CLI dispatch ---


def test_smart_dispatch_routes_batch(monkeypatch):
    """cli.main() routes 'batch' to batch_cli.batch_main."""
    import uitag.cli

    called_with = []

    def fake_batch_main(argv):
        called_with.append(argv)

    monkeypatch.setattr("uitag.batch_cli.batch_main", fake_batch_main)
    monkeypatch.setattr("sys.argv", ["uitag", "batch", "screenshots/", "-o", "out/"])

    uitag.cli.main()
    assert called_with == [["screenshots/", "-o", "out/"]]


def test_directory_hint_when_given_dir(tmp_path, monkeypatch, capsys):
    """Passing a directory to `uitag <dir>` prints a helpful hint."""
    import uitag.cli

    monkeypatch.setattr("sys.argv", ["uitag", str(tmp_path)])

    with pytest.raises(SystemExit):
        uitag.cli.main()

    captured = capsys.readouterr()
    assert "uitag batch" in captured.err
