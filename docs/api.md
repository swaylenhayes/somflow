# API Reference

The pipeline produces two core types. A `Detection` represents a single UI element — its bounding box, label, confidence score, and source (Apple Vision text, Vision rectangles, YOLO, or Florence-2). `PipelineResult` collects all merged detections for an image along with dimensions and per-stage timing data. The entry point, `run_pipeline()`, takes a screenshot path, runs detection through all enabled stages, and returns a `PipelineResult`, an annotated PIL image, and a JSON manifest string.

---

## Quick Start

```python
from uitag import run_pipeline

result, annotated_image, manifest_json = run_pipeline("screenshot.png")

for det in result.detections:
    print(f"[{det.som_id}] {det.label} at ({det.x},{det.y}) {det.width}x{det.height}")
```

See [`examples/use_as_library.py`](../examples/use_as_library.py) for a complete working example.

---

## `run_pipeline()`

```python
from uitag import run_pipeline

result, annotated_image, manifest_json = run_pipeline(
    image_path,
    florence_task="<OD>",
    overlap_px=50,
    iou_threshold=0.5,
    recognition_level="accurate",
    backend=None,
    use_yolo=False,
)
```

Runs the detection pipeline: Apple Vision (text + rectangles), optional YOLO tiled detection (if `use_yolo=True`), optional Florence-2 inference (if `backend` provided or `--florence` used), merge/dedup, OCR correction, text block grouping, SoM annotation, and manifest generation.

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `image_path` | `str \| Path` | *(required)* | Path to the input screenshot (PNG, JPEG, etc.). |
| `florence_task` | `str` | `"<OD>"` | Florence-2 task token. `"<OD>"` for object detection. |
| `overlap_px` | `int` | `50` | Pixels of overlap padding between quadrant tiles. |
| `iou_threshold` | `float` | `0.5` | IoU threshold for duplicate suppression during merge. |
| `recognition_level` | `str` | `"accurate"` | Apple Vision OCR mode: `"accurate"` or `"fast"`. |
| `backend` | `DetectionBackend \| None` | `None` | Florence-2 inference backend. When `None`, uses `MLXBackend`. |
| `use_yolo` | `bool` | `False` | Enable YOLO tiled detection. Adds ~2s, closes icon gap. Requires `ultralytics`. |

### Return Value

Returns a 3-tuple: `tuple[PipelineResult, Image.Image, str]`

| Position | Type | Description |
|----------|------|-------------|
| `result` | `PipelineResult` | Structured detection results with timing data. |
| `annotated_image` | `PIL.Image.Image` | Copy of the input image with SoM numbered overlays drawn on it. |
| `manifest_json` | `str` | JSON string of the detection manifest (2-space indented). |

### Raises

| Exception | Condition |
|-----------|-----------|
| `FileNotFoundError` | The input image does not exist, or the Swift Vision tool cannot be found. |
| `RuntimeError` | The Apple Vision subprocess fails (e.g., not on macOS, corrupt image). |

When `use_yolo=True`, a `FileNotFoundError` is raised if the YOLO model weights are not found. An `ImportError` propagates if `ultralytics` is not installed (`pip install uitag[yolo]`). Florence-2 exceptions propagate from `mlx_vlm`.

### Example

```python
from uitag import run_pipeline

result, annotated_image, manifest_json = run_pipeline(
    "screenshot.png",
    recognition_level="fast",
    iou_threshold=0.4,
)

print(f"Found {len(result.detections)} elements in {result.timing_ms.get('vision_ms', 0):.0f}ms")
annotated_image.save("annotated.png")
```

---

## Data Types

### `Detection`

```python
from uitag import Detection
```

A single detected UI element. Defined as a dataclass in `uitag/types.py`.

| Field | Type | Description |
|-------|------|-------------|
| `label` | `str` | Element label — text content (for Vision text), class name (for Florence-2), or grouped text (for text blocks). |
| `x` | `int` | Left edge of bounding box in pixels. |
| `y` | `int` | Top edge of bounding box in pixels. |
| `width` | `int` | Bounding box width in pixels. |
| `height` | `int` | Bounding box height in pixels. |
| `confidence` | `float` | Detection confidence score (0.0--1.0). Vision provides real scores; YOLO provides model confidence; Florence-2 detections default to `0.5`. |
| `source` | `str` | Detection source identifier. One of: `"vision_text"`, `"vision_rect"`, `"vision_text_block"`, `"yolo"`, `"florence2"`. |
| `som_id` | `int \| None` | SoM marker number (1-indexed). `None` until `merge_detections()` assigns sequential IDs sorted by position (top-to-bottom, left-to-right). |

#### Source values

| Value | Origin |
|-------|--------|
| `"vision_text"` | Apple Vision text recognition |
| `"vision_rect"` | Apple Vision rectangle detection |
| `"vision_text_block"` | Grouped adjacent text lines (paragraph-level) |
| `"yolo"` | YOLO tiled detection (only with `--yolo`) |
| `"florence2"` | Florence-2 object detection via MLX (only with `--florence`, legacy) |

### `PipelineResult`

```python
from uitag import PipelineResult
```

Output of the full detection pipeline. Defined as a dataclass in `uitag/types.py`.

| Field | Type | Description |
|-------|------|-------------|
| `detections` | `list[Detection]` | All merged detections, sorted by position with `som_id` assigned. |
| `image_width` | `int` | Width of the input image in pixels. |
| `image_height` | `int` | Height of the input image in pixels. |
| `timing_ms` | `dict` | Pipeline timing breakdown. Defaults to an empty dict. |

#### `timing_ms` keys

Populated by `run_pipeline`:

| Key | Type | Description |
|-----|------|-------------|
| `vision_ms` | `float` | Total Apple Vision stage wall time. |
| `yolo_ms` | `float` | Total YOLO tiled inference time (only with `--yolo`). |
| `yolo_tiles` | `int` | Number of 640x640 tiles processed (only with `--yolo`). |
| `yolo_raw_dets` | `int` | Raw detections before cross-tile NMS (only with `--yolo`). |
| `yolo_nms_dets` | `int` | Detections after NMS (only with `--yolo`). |
| `merge_ms` | `float` | Merge and deduplication stage time. |
| `correct_ms` | `float` | OCR correction stage time. |
| `corrections` | `int` | Number of labels corrected. |
| `group_ms` | `float` | Text block grouping stage time. |
| `groups_formed` | `int` | Number of text blocks formed. |
| `annotate_ms` | `float` | SoM annotation rendering time. |
| `manifest_ms` | `float` | JSON manifest generation time. |
| `florence_total_ms` | `float` | Total Florence-2 inference time (only with `--florence`). |
| `florence_backend` | `str` | Backend used for Florence-2 (only with `--florence`). |

---

## Stage Functions

For fine-grained control, you can call individual pipeline stages directly.

### `run_vision_detect()`

```python
from uitag.vision import run_vision_detect
```

Runs Apple Vision text + rectangle detection via a compiled Swift subprocess.

```python
run_vision_detect(
    image_path,
    recognition_level="accurate",
) -> tuple[list[Detection], dict]
```

#### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `image_path` | `str \| Path` | *(required)* | Path to the input image. Resolved to an absolute path internally. |
| `recognition_level` | `str` | `"accurate"` | `"accurate"` for high-quality OCR, `"fast"` for ~5x faster but noisier text. |

#### Returns

A 2-tuple:

| Position | Type | Description |
|----------|------|-------------|
| `detections` | `list[Detection]` | Detected text spans and rectangles. Source is `"vision_text"` or `"vision_rect"`. |
| `timing` | `dict` | Timing and metadata from the Swift subprocess. Keys include `image_width`, `image_height`, `vision_time_ms`, `text_count`, `rect_count`. |

#### Raises

| Exception | Condition |
|-----------|-----------|
| `FileNotFoundError` | The input image does not exist, or the Swift tool binary/source cannot be found. |
| `RuntimeError` | The Swift subprocess exits with a non-zero return code. |

#### Example

```python
from uitag.vision import run_vision_detect

detections, timing = run_vision_detect("screenshot.png", recognition_level="fast")
text_elements = [d for d in detections if d.source == "vision_text"]
print(f"Found {len(text_elements)} text elements in {timing.get('vision_time_ms', 0)}ms")
```

---

### `detect_on_quadrant()`

```python
from uitag.florence import detect_on_quadrant
```

Runs Florence-2 object detection on a single PIL Image quadrant and translates coordinates back to full-image space.

```python
detect_on_quadrant(
    quadrant_image,
    offset_x,
    offset_y,
    task="<OD>",
) -> list[Detection]
```

#### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `quadrant_image` | `PIL.Image.Image` | *(required)* | A cropped quadrant of the full screenshot. |
| `offset_x` | `int` | *(required)* | Horizontal offset of this quadrant in the full image (pixels). Added to each detection's `x`. |
| `offset_y` | `int` | *(required)* | Vertical offset of this quadrant in the full image (pixels). Added to each detection's `y`. |
| `task` | `str` | `"<OD>"` | Florence-2 task token. |

#### Returns

`list[Detection]` -- Detections with coordinates translated to full-image space. All have `source="florence2"` and `confidence=0.5`.

This function saves the PIL Image to a temporary file (mlx_vlm requires a file path), runs inference, then deletes the temp file. The model is lazy-loaded as a singleton on the first call to any Florence-2 detection function.

#### Example

```python
from PIL import Image
from uitag.florence import detect_on_quadrant

img = Image.open("screenshot.png")
w, h = img.size

# Detect on the top-left quadrant
quadrant = img.crop((0, 0, w // 2, h // 2))
detections = detect_on_quadrant(quadrant, offset_x=0, offset_y=0)
print(f"Found {len(detections)} elements in top-left quadrant")
```

---

### `merge_detections()`

```python
from uitag.merge import merge_detections
```

Merges and deduplicates detections from multiple sources using IoU-based suppression with source priority.

```python
merge_detections(
    detections,
    iou_threshold=0.5,
) -> list[Detection]
```

#### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `detections` | `list[Detection]` | *(required)* | All detections from all sources (Vision + YOLO + Florence-2), unmerged. |
| `iou_threshold` | `float` | `0.5` | When two detections overlap above this IoU threshold, the lower-priority one is discarded. |

#### Source Priority

When overlapping detections are found, the higher-priority source is kept:

| Source | Priority | Rationale |
|--------|----------|-----------|
| `"vision_text"` | 3 (highest) | Apple Vision text has OCR content — most useful for labeling. |
| `"vision_text_block"` | 3 (highest) | Grouped text inherits Vision text priority. |
| `"vision_rect"` | 2 | Apple Vision rectangles are accurate but lack semantic labels. |
| `"yolo"` | 2 | YOLO detections have class labels (Button, Menu, etc.) but no OCR. |
| `"florence2"` | 1 (lowest) | Florence-2 detections fill gaps (legacy, superseded by YOLO). |

#### Returns

`list[Detection]` -- Deduplicated detections sorted by position (top-to-bottom, left-to-right) with `som_id` assigned sequentially starting at 1.

#### Example

```python
from uitag.vision import run_vision_detect
from uitag.florence import detect_on_quadrant
from uitag.merge import merge_detections

vision_dets, _ = run_vision_detect("screenshot.png")
# ... run florence on quadrants, collect florence_dets ...

all_dets = vision_dets + florence_dets
merged = merge_detections(all_dets, iou_threshold=0.4)
print(f"Merged {len(all_dets)} raw -> {len(merged)} unique detections")
```

---

### `render_som()`

```python
from uitag.annotate import render_som
```

Renders Set-of-Mark numbered annotations on an image. Each detection gets a colored bounding box and a numbered circle marker.

```python
render_som(
    image,
    detections,
    marker_size=20,
) -> Image.Image
```

#### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `image` | `PIL.Image.Image` | *(required)* | The original screenshot to annotate. |
| `detections` | `list[Detection]` | *(required)* | Detections with `som_id` assigned (detections with `som_id=None` are skipped). |
| `marker_size` | `int` | `20` | Diameter in pixels of the numbered circle markers. |

#### Returns

`PIL.Image.Image` -- A copy of the input image (converted to RGB) with bounding boxes and numbered markers drawn. The original image is not modified.

Colors cycle through 8 values in `SOM_COLORS`: red, green, blue, orange, purple, cyan, yellow, pink. The color for each detection is determined by `(som_id - 1) % 8`.

#### Example

```python
from PIL import Image
from uitag.annotate import render_som
from uitag.merge import merge_detections

# Assuming you have merged detections with som_ids assigned
img = Image.open("screenshot.png")
annotated = render_som(img, merged_detections, marker_size=24)
annotated.save("annotated.png")
```

---

### `generate_manifest()`

```python
from uitag.manifest import generate_manifest
```

Generates a JSON manifest string from a `PipelineResult`.

```python
generate_manifest(
    result,
) -> str
```

#### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `result` | `PipelineResult` | *(required)* | The pipeline result containing detections, image dimensions, and timing. |

#### Returns

`str` -- A JSON string (2-space indented) conforming to the manifest schema. See [Manifest Schema](#manifest-schema) below.

#### Example

```python
from uitag.types import PipelineResult, Detection
from uitag.manifest import generate_manifest

result = PipelineResult(
    detections=[
        Detection("Save", x=100, y=50, width=60, height=20, confidence=0.95, source="vision_text", som_id=1),
    ],
    image_width=1920,
    image_height=1080,
    timing_ms={"vision_ms": 980.0},
)

manifest = generate_manifest(result)
print(manifest)
```

---

## Custom Backends

The `DetectionBackend` protocol lets you replace Florence-2/MLX inference with any detection engine (ONNX, TensorRT, a remote API, etc.) without modifying uitag internals.

### `DetectionBackend` Protocol

```python
from uitag.backends.base import DetectionBackend, BackendInfo
```

Any class that implements these three methods satisfies the protocol (it uses `@runtime_checkable`):

| Method | Signature | Description |
|--------|-----------|-------------|
| `info()` | `-> BackendInfo` | Return backend metadata. |
| `warmup()` | `-> None` | Pre-load model and warm up inference. Must be idempotent. |
| `detect_quadrants()` | `(quadrants, task="<OD>", max_tokens=512) -> list[Detection]` | Run detection on a list of `(image, offset_x, offset_y)` tuples. Must translate coordinates by offset before returning. |

### `BackendInfo` Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Backend identifier (e.g. `"mlx"`, `"coreml"`, `"onnx"`). |
| `version` | `str` | Backend library version string. |
| `device` | `str` | Compute device: `"gpu"`, `"ane"`, `"cpu"`, etc. |
| `available` | `bool` | Whether this backend can run on the current system. |

### Usage

Pass your backend to `run_pipeline()`:

```python
from uitag import run_pipeline

backend = MyCustomBackend()
result, annotated, manifest = run_pipeline("screenshot.png", backend=backend)
```

See [`examples/custom_backend.py`](../examples/custom_backend.py) for a complete working implementation.

---

## Manifest Schema

The JSON manifest output conforms to the schema defined in [`uitag/schema.json`](../uitag/schema.json).

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `image_width` | `integer` | Width of the input image in pixels. |
| `image_height` | `integer` | Height of the input image in pixels. |
| `element_count` | `integer` | Number of detected elements. |
| `elements` | `array` | Array of detected UI elements (see below). |
| `timing_ms` | `object` | Pipeline timing breakdown in milliseconds. |

### Element Fields

Each entry in `elements`:

| Field | Type | Description |
|-------|------|-------------|
| `som_id` | `integer` | Unique SoM identifier (1-indexed). |
| `label` | `string` | Element label (text content or detection class). |
| `bbox` | `object` | Bounding box with `x`, `y`, `width`, `height` (all integers, pixels). |
| `confidence` | `number` | Detection confidence score (0.0--1.0). |
| `source` | `string` | Detection source: `"vision_text"`, `"vision_rect"`, `"vision_text_block"`, `"yolo"`, or `"florence2"`. |

### Example Manifest

```json
{
  "image_width": 1920,
  "image_height": 1080,
  "element_count": 2,
  "elements": [
    {
      "som_id": 1,
      "label": "File",
      "bbox": { "x": 14, "y": 0, "width": 22, "height": 15 },
      "confidence": 0.95,
      "source": "vision_text"
    },
    {
      "som_id": 2,
      "label": "Button",
      "bbox": { "x": 2752, "y": 305, "width": 101, "height": 104 },
      "confidence": 0.87,
      "source": "yolo"
    }
  ],
  "timing_ms": {
    "vision_ms": 980.1,
    "yolo_ms": 2150.3,
    "yolo_tiles": 32,
    "merge_ms": 3.3
  }
}
```
