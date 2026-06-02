from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from constants import (
    BOX_OUTLINE_COLOR,
    BOX_OUTLINE_WIDTH,
    CROP_HEIGHT_PX,
    CROP_WIDTH_PX,
    DEFAULT_HAS_BOX,
    TARGET_BOX_DIAGONAL_PX,
)

Point = tuple[float, float]
Polygon = tuple[Point, Point, Point, Point]


@dataclass(frozen=True)
class DetectionBox:
    x: float
    y: float
    width: float
    height: float
    confidence: float
    order: int


@dataclass(frozen=True)
class TransformGeometry:
    angle: float
    scale: float
    center: Point
    affine: tuple[float, float, float, float, float, float]


def draw_frisbee_box(
    image_path: str,
    detections: dict | list,
    output_path: str | None = None,
    has_box: bool = DEFAULT_HAS_BOX,
) -> str:
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file does not exist: {image_file}")

    selected_box = _extract_selected_box(detections)
    if selected_box is None:
        raise ValueError("No usable frisbee predictions found in detection JSON.")

    output_file = Path(output_path) if output_path else _default_output_path(image_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    Image, ImageDraw = _load_pillow()
    with Image.open(image_file) as image:
        transformed, transformed_box = _transform_image(Image, image, selected_box)
        if has_box:
            draw = ImageDraw.Draw(transformed)
            draw.line(
                (*transformed_box, transformed_box[0]),
                fill=BOX_OUTLINE_COLOR,
                width=BOX_OUTLINE_WIDTH,
            )
        transformed.save(output_file)

    return str(output_file)


def _load_pillow() -> tuple[Any, Any]:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required. Install dependencies with: pip3 install -r requirements.txt"
        ) from exc

    return Image, ImageDraw


def draw_frisbee_box_from_file(
    image_path: str,
    json_path: str,
    output_path: str | None = None,
    has_box: bool = DEFAULT_HAS_BOX,
) -> str:
    detections = _load_detection_json_file(json_path)
    return draw_frisbee_box(image_path, detections, output_path, has_box)


def _extract_selected_box(detections: dict | list) -> DetectionBox | None:
    prediction_items = _extract_prediction_items(detections)
    boxes: list[DetectionBox] = []

    for order, prediction in enumerate(prediction_items):
        if not isinstance(prediction, dict):
            continue

        has_class = "class" in prediction
        if has_class and prediction.get("class") != "frisbee":
            continue

        if not all(key in prediction for key in ("x", "y", "width", "height")):
            continue

        x = float(prediction["x"])
        y = float(prediction["y"])
        width = float(prediction["width"])
        height = float(prediction["height"])
        confidence = _extract_confidence(prediction)
        boxes.append(DetectionBox(x, y, width, height, confidence, order))

    if not boxes:
        return None

    return max(boxes, key=lambda box: (box.confidence, -box.order))


def _extract_confidence(prediction: dict) -> float:
    if "confidence" not in prediction:
        return 0

    try:
        return float(prediction["confidence"])
    except (TypeError, ValueError):
        return 0


def _extract_prediction_items(detections: dict | list) -> list[Any]:
    entries = detections if isinstance(detections, list) else [detections]
    prediction_items: list[Any] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        predictions = entry.get("predictions", entry)
        if isinstance(predictions, dict):
            nested_predictions = predictions.get("predictions")
            if isinstance(nested_predictions, list):
                prediction_items.extend(nested_predictions)
            elif _looks_like_prediction(predictions):
                prediction_items.append(predictions)
        elif isinstance(predictions, list):
            prediction_items.extend(predictions)

    return prediction_items


def _looks_like_prediction(value: dict) -> bool:
    return all(key in value for key in ("x", "y", "width", "height"))


def _transform_image(Image: Any, image: Any, box: DetectionBox) -> tuple[Any, Polygon]:
    geometry = _build_transform_geometry(box)
    _validate_crop_bounds(geometry, image.size)

    transform_enum = getattr(Image, "Transform", None)
    affine_method = transform_enum.AFFINE if transform_enum else Image.AFFINE
    resampling_enum = getattr(Image, "Resampling", None)
    resample = resampling_enum.BICUBIC if resampling_enum else Image.BICUBIC

    transformed = image.transform(
        (CROP_WIDTH_PX, CROP_HEIGHT_PX),
        affine_method,
        geometry.affine,
        resample=resample,
    )
    return transformed, _transform_polygon(_box_corners(box), geometry)


def _build_transform_geometry(box: DetectionBox) -> TransformGeometry:
    if box.width <= 0 or box.height <= 0:
        raise ValueError("Detection box width and height must be positive.")

    diagonal = math.hypot(box.width, box.height)
    scale = TARGET_BOX_DIAGONAL_PX / diagonal
    angle = math.atan(box.height / box.width)
    source_center = (box.x, box.y)
    output_center = (CROP_WIDTH_PX / 2, CROP_HEIGHT_PX / 2)
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)

    a = cos_angle / scale
    b = sin_angle / scale
    c = source_center[0] - (
        cos_angle * output_center[0] + sin_angle * output_center[1]
    ) / scale
    d = -sin_angle / scale
    e = cos_angle / scale
    f = source_center[1] - (
        -sin_angle * output_center[0] + cos_angle * output_center[1]
    ) / scale

    return TransformGeometry(angle, scale, source_center, (a, b, c, d, e, f))


def _validate_crop_bounds(
    geometry: TransformGeometry,
    image_size: tuple[int, int],
) -> None:
    image_width, image_height = image_size
    output_corners = (
        (0, 0),
        (CROP_WIDTH_PX, 0),
        (CROP_WIDTH_PX, CROP_HEIGHT_PX),
        (0, CROP_HEIGHT_PX),
    )

    for source_x, source_y in (
        _map_output_to_source(point, geometry) for point in output_corners
    ):
        if (
            source_x < 0
            or source_y < 0
            or source_x > image_width
            or source_y > image_height
        ):
            raise ValueError(
                "Transformed crop exceeds image bounds at source point "
                f"({source_x:.2f}, {source_y:.2f}) for image size "
                f"{image_width}x{image_height}."
            )


def _map_output_to_source(point: Point, geometry: TransformGeometry) -> Point:
    a, b, c, d, e, f = geometry.affine
    x, y = point
    return a * x + b * y + c, d * x + e * y + f


def _box_corners(box: DetectionBox) -> Polygon:
    left = box.x - box.width / 2
    top = box.y - box.height / 2
    right = box.x + box.width / 2
    bottom = box.y + box.height / 2
    return (left, top), (right, top), (right, bottom), (left, bottom)


def _transform_polygon(polygon: Polygon, geometry: TransformGeometry) -> Polygon:
    cos_angle = math.cos(geometry.angle)
    sin_angle = math.sin(geometry.angle)
    output_center = (CROP_WIDTH_PX / 2, CROP_HEIGHT_PX / 2)

    transformed_points: list[Point] = []
    for x, y in polygon:
        dx = x - geometry.center[0]
        dy = y - geometry.center[1]
        transformed_points.append(
            (
                output_center[0]
                + geometry.scale * (cos_angle * dx - sin_angle * dy),
                output_center[1]
                + geometry.scale * (sin_angle * dx + cos_angle * dy),
            )
        )

    return (
        transformed_points[0],
        transformed_points[1],
        transformed_points[2],
        transformed_points[3],
    )


def _default_output_path(image_file: Path) -> Path:
    return image_file.parent / "output" / f"{image_file.stem}-boxed{image_file.suffix}"


def _load_detection_json_file(json_file: str) -> dict | list:
    json_path = Path(json_file)
    if not json_path.exists():
        raise FileNotFoundError(f"Detection JSON file does not exist: {json_path}")

    return _parse_detection_json(json_path.read_text(encoding="utf-8"))


def _load_detection_json(json_file: str | None, json_value: str | None) -> dict | list:
    if bool(json_file) == bool(json_value):
        raise ValueError("Provide exactly one of --json-file or --json.")

    if json_file:
        return _load_detection_json_file(json_file)

    return _parse_detection_json(json_value or "")


def _parse_detection_json(raw_json: str) -> dict | list:
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Detection JSON is invalid: {exc.msg}") from exc

    if not isinstance(parsed, (dict, list)):
        raise ValueError("Detection JSON must be an object or array.")

    return parsed


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False

    raise argparse.ArgumentTypeError("Expected true or false.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transform an image around a frisbee detection box."
    )
    parser.add_argument("image_path", help="Relative or absolute path to the source image.")
    parser.add_argument(
        "json_path",
        nargs="?",
        help="Path to the detection JSON file, for example data/input-1.json.",
    )
    parser.add_argument("--json-file", help="Path to the detection JSON file.")
    parser.add_argument("--json", help="Detection JSON as an inline string.")
    parser.add_argument("--output", help="Optional output image path.")
    parser.add_argument(
        "--has-box",
        type=_parse_bool,
        default=DEFAULT_HAS_BOX,
        metavar="true|false",
        help="Whether to draw the transformed frisbee box. Defaults to true.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        json_file = args.json_file or args.json_path
        if args.json_file and args.json_path:
            raise ValueError("Use either the positional JSON path or --json-file, not both.")

        detections = _load_detection_json(json_file, args.json)
        output_file = draw_frisbee_box(
            args.image_path,
            detections,
            args.output,
            args.has_box,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved transformed image to: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
