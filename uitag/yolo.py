"""YOLO tiled inference for UI element detection.

Pipeline stage: runs after Apple Vision, before merge.
Tiles the input image to 640x640 with 20% overlap (matching training),
runs YOLO inference on each tile, maps detections back to full-image
coordinates, and applies cross-tile NMS.

The model (XMIL-YOLO2C, 18MB) is expected at:
  uitag/models/yolo-ui.pt

If not found, raises FileNotFoundError with download instructions.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image

from uitag.types import Detection

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL_NAME = "yolo-ui.pt"
DEFAULT_MODEL_PATH = MODEL_DIR / DEFAULT_MODEL_NAME

# Fallback: dev location (before model is bundled)
_DEV_MODEL_PATH = (
    Path(__file__).parent.parent
    / "_docs"
    / "training"
    / "runs"
    / "XMIL-YOLO2C"
    / "best.pt"
)

YOLO_CATEGORY_NAMES = [
    "Button",
    "Menu",
    "Input_Elements",
    "Navigation",
    "Information_Display",
    "Sidebar",
    "Visual_Elements",
    "Others",
    "Unknown",
]

# Tile parameters matching training
TILE_SIZE = 640
OVERLAP_RATIO = 0.2


def _find_model() -> Path:
    """Locate the YOLO model weights."""
    if DEFAULT_MODEL_PATH.exists():
        return DEFAULT_MODEL_PATH
    if _DEV_MODEL_PATH.exists():
        return _DEV_MODEL_PATH
    raise FileNotFoundError(
        f"YOLO model not found at {DEFAULT_MODEL_PATH} or {_DEV_MODEL_PATH}.\n"
        f"Place yolo-ui.pt in {MODEL_DIR}/ or run from the dev tree."
    )


def _compute_tiles(
    img_width: int,
    img_height: int,
    tile_size: int = TILE_SIZE,
    overlap_ratio: float = OVERLAP_RATIO,
) -> list[tuple[int, int, int, int]]:
    """Compute tile positions with overlap — matches training tiling exactly."""
    step = int(tile_size * (1 - overlap_ratio))
    tiles = []

    y = 0
    while y < img_height:
        x = 0
        while x < img_width:
            x2 = min(x + tile_size, img_width)
            y2 = min(y + tile_size, img_height)
            x1 = max(0, x2 - tile_size)
            y1 = max(0, y2 - tile_size)
            tiles.append((x1, y1, x2, y2))
            if x2 >= img_width:
                break
            x += step
        if y2 >= img_height:
            break
        y += step

    return tiles


def _nms_boxes(
    boxes: np.ndarray,
    iou_threshold: float = 0.5,
) -> np.ndarray:
    """Cross-tile NMS. Input: Nx6 [x1, y1, x2, y2, conf, cls]. Returns filtered array."""
    if len(boxes) == 0:
        return boxes

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    scores = boxes[:, 4]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while len(order) > 0:
        i = order[0]
        keep.append(i)

        if len(order) == 1:
            break

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        union = areas[i] + areas[order[1:]] - inter
        iou = np.where(union > 0, inter / union, 0.0)

        mask = iou <= iou_threshold
        order = order[1:][mask]

    return boxes[keep]


# Module-level model cache (lazy-loaded)
_model = None


def _get_model():
    """Lazy-load the YOLO model (cached across calls)."""
    global _model
    if _model is None:
        from ultralytics import YOLO

        model_path = _find_model()
        logger.info("Loading YOLO model from %s", model_path)
        _model = YOLO(str(model_path))
    return _model


def run_yolo_detect(
    image_path: str,
    conf_threshold: float = 0.25,
    nms_iou_threshold: float = 0.5,
) -> tuple[list[Detection], dict]:
    """Run YOLO tiled inference on a screenshot.

    Args:
        image_path: Path to the input image.
        conf_threshold: Minimum confidence for detections.
        nms_iou_threshold: IoU threshold for cross-tile NMS.

    Returns:
        (detections, timing_dict) where detections have source="yolo"
        and timing_dict contains yolo_tiles, yolo_raw_dets, yolo_nms_dets.
    """
    model = _get_model()
    img = Image.open(image_path)
    img_width, img_height = img.size

    tiles = _compute_tiles(img_width, img_height)
    logger.info("YOLO: %dx%d image -> %d tiles", img_width, img_height, len(tiles))

    all_boxes: list[list[float]] = []

    for tx1, ty1, tx2, ty2 in tiles:
        tile_img = img.crop((tx1, ty1, tx2, ty2))

        results = model(
            tile_img,
            imgsz=TILE_SIZE,
            conf=conf_threshold,
            verbose=False,
        )

        r = results[0]
        if len(r.boxes) == 0:
            continue

        for box in r.boxes:
            xyxy = box.xyxy[0].tolist()
            conf = box.conf[0].item()
            cls_id = int(box.cls[0].item())

            # Translate tile-local to full-image coords
            fx1 = max(0, min(xyxy[0] + tx1, img_width))
            fy1 = max(0, min(xyxy[1] + ty1, img_height))
            fx2 = max(0, min(xyxy[2] + tx1, img_width))
            fy2 = max(0, min(xyxy[3] + ty1, img_height))

            if fx2 > fx1 and fy2 > fy1:
                all_boxes.append([fx1, fy1, fx2, fy2, conf, cls_id])

    raw_count = len(all_boxes)

    # Cross-tile NMS
    if all_boxes:
        boxes_arr = np.array(all_boxes)
        filtered = _nms_boxes(boxes_arr, nms_iou_threshold)
    else:
        filtered = np.array([]).reshape(0, 6)

    # Convert to Detection objects
    detections: list[Detection] = []
    names = model.names

    for row in filtered:
        x1, y1, x2, y2, conf, cls_id = row
        label = names.get(int(cls_id), "Unknown")
        detections.append(
            Detection(
                label=label,
                x=round(x1),
                y=round(y1),
                width=round(x2 - x1),
                height=round(y2 - y1),
                confidence=round(float(conf), 4),
                source="yolo",
            )
        )

    timing = {
        "yolo_tiles": len(tiles),
        "yolo_raw_dets": raw_count,
        "yolo_nms_dets": len(detections),
    }

    return detections, timing
