from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import shutil
from typing import Any

from src.api import run_detection_workflow
from src.config import (
    AC_OUTPUT_SUFFIX,
    BD_OUTPUT_SUFFIX,
    BOX_OUTLINE_COLOR,
    BOX_OUTLINE_WIDTH,
    CROP_ASPECT_HEIGHT,
    CROP_ASPECT_WIDTH,
    CROP_WIDTH_TO_TARGET_DISC_LINE,
    DEFAULT_DISC_LINES,
    DEFAULT_GEN_BOX,
    load_api_settings,
    normalize_disc_line,
)
from src.image_io import load_pillow, prepared_image_file
from src.paths import (
    add_output_timestamp,
    current_output_timestamp,
    default_centered_output_path,
    resolve_existing_input_path,
    saved_source_output_path,
    source_with_box_output_path,
    variant_output_paths,
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
class CenteringGeometry:
    angle: float
    scale: float
    center: Point
    crop_size: tuple[int, int]
    affine: tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class CenteringVariant:
    suffix: str
    angle: float
    line_length: float


def center_frisbee_image(
    image_path: str,
    detections: dict | list,
    output_path: str | None = None,
    gen_box: bool = DEFAULT_GEN_BOX,
    disc_line: str | None = None,
    save_source: bool = False,
) -> list[str]:
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file does not exist: {image_file}")

    selected_box = _extract_selected_box(detections)
    if selected_box is None:
        print(f"Skipped: {image_file} (no frisbee detected)")
        return []

    variants = _build_centering_variants(selected_box, normalize_disc_line(disc_line))
    output_timestamp = current_output_timestamp()
    base_output_file = add_output_timestamp(
        Path(output_path) if output_path else default_centered_output_path(image_file),
        output_timestamp,
    )
    output_files = variant_output_paths(
        base_output_file,
        tuple(variant.suffix for variant in variants),
    )
    boxed_output_files = (
        (source_with_box_output_path(image_file),)
        if gen_box
        else ()
    )
    saved_source_files = (
        (saved_source_output_path(image_file),)
        if save_source
        else ()
    )

    Image, ImageDraw = load_pillow()
    with Image.open(image_file) as image:
        render_jobs = [
            (
                output_file,
                *_render_centered_variant(Image, image, selected_box, variant),
            )
            for output_file, variant in zip(output_files, variants)
        ]

        for output_file in (*output_files, *boxed_output_files):
            output_file.parent.mkdir(parents=True, exist_ok=True)

        for output_file, centered_image, _centered_box in render_jobs:
            centered_image.save(output_file)

        if gen_box:
            boxed_image = image.copy()
            source_box = _box_corners(selected_box)
            draw = ImageDraw.Draw(boxed_image)
            draw.line(
                (*source_box, source_box[0]),
                fill=BOX_OUTLINE_COLOR,
                width=BOX_OUTLINE_WIDTH,
            )
            boxed_image.save(boxed_output_files[0])

    if save_source:
        saved_source_files[0].parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_file, saved_source_files[0])

    return [
        str(output_file)
        for output_file in (*output_files, *boxed_output_files, *saved_source_files)
    ]


def center_frisbee_image_from_api(
    image_path: str,
    output_path: str | None = None,
) -> list[str]:
    image_file = resolve_existing_input_path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file does not exist: {image_file}")
    if not image_file.is_file():
        raise FileNotFoundError(f"Input path is not an image file: {image_file}")

    settings = load_api_settings()
    with prepared_image_file(image_file, settings.auto_resize) as processing_file:
        detections = run_detection_workflow(
            str(processing_file),
            settings.api_key,
            settings.workspace_name,
            settings.workflow_id,
        )
        return center_frisbee_image(
            str(processing_file),
            detections,
            output_path,
            settings.gen_box,
            settings.disc_line,
            settings.save_source,
        )


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


def _render_centered_variant(
    Image: Any,
    image: Any,
    box: DetectionBox,
    variant: CenteringVariant,
) -> tuple[Any, Polygon]:
    geometry = _build_centering_geometry(box, variant.angle, variant.line_length)
    _validate_crop_bounds(geometry, image.size)

    transform_enum = getattr(Image, "Transform", None)
    affine_method = transform_enum.AFFINE if transform_enum else Image.AFFINE
    resampling_enum = getattr(Image, "Resampling", None)
    resample = resampling_enum.BICUBIC if resampling_enum else Image.BICUBIC

    centered_image = image.transform(
        geometry.crop_size,
        affine_method,
        geometry.affine,
        resample=resample,
    )
    return centered_image, _map_polygon_to_output(_box_corners(box), geometry)


def _build_centering_variants(
    box: DetectionBox,
    disc_line: str | None,
) -> tuple[CenteringVariant, ...]:
    if box.width <= 0 or box.height <= 0:
        raise ValueError("Detection box width and height must be positive.")

    angle = math.atan(box.height / box.width)
    diagonal = math.hypot(box.width, box.height)
    angles_by_disc_line = {
        "AB": 0.0,
        "BC": -math.pi / 2,
        "CD": 0.0,
        "AD": -math.pi / 2,
        "AC": -angle,
        "BD": angle,
    }
    lengths_by_disc_line = {
        "AB": box.width,
        "BC": box.height,
        "CD": box.width,
        "AD": box.height,
        "AC": diagonal,
        "BD": diagonal,
    }
    selected_disc_lines = (disc_line,) if disc_line else DEFAULT_DISC_LINES

    return tuple(
        CenteringVariant(
            _disc_line_output_suffix(selected_disc_line),
            angles_by_disc_line[selected_disc_line],
            lengths_by_disc_line[selected_disc_line],
        )
        for selected_disc_line in selected_disc_lines
    )


def _disc_line_output_suffix(disc_line: str) -> str:
    if disc_line == "AC":
        return AC_OUTPUT_SUFFIX
    if disc_line == "BD":
        return BD_OUTPUT_SUFFIX

    return disc_line.lower()


def _build_centering_geometry(
    box: DetectionBox,
    angle: float,
    disc_line_length: float,
) -> CenteringGeometry:
    if box.width <= 0 or box.height <= 0:
        raise ValueError("Detection box width and height must be positive.")
    if disc_line_length <= 0:
        raise ValueError("Detection disc line length must be positive.")

    crop_width = round(disc_line_length * CROP_WIDTH_TO_TARGET_DISC_LINE)
    crop_height = round(crop_width * CROP_ASPECT_HEIGHT / CROP_ASPECT_WIDTH)
    crop_size = (crop_width, crop_height)
    scale = 1.0
    source_center = (box.x, box.y)
    output_center = (crop_width / 2, crop_height / 2)
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

    return CenteringGeometry(angle, scale, source_center, crop_size, (a, b, c, d, e, f))


def _validate_crop_bounds(
    geometry: CenteringGeometry,
    image_size: tuple[int, int],
) -> None:
    image_width, image_height = image_size
    crop_width, crop_height = geometry.crop_size
    output_corners = (
        (0, 0),
        (crop_width, 0),
        (crop_width, crop_height),
        (0, crop_height),
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
                "Centered crop exceeds image bounds at source point "
                f"({source_x:.2f}, {source_y:.2f}) for image size "
                f"{image_width}x{image_height}."
            )


def _map_output_to_source(point: Point, geometry: CenteringGeometry) -> Point:
    a, b, c, d, e, f = geometry.affine
    x, y = point
    return a * x + b * y + c, d * x + e * y + f


def _box_corners(box: DetectionBox) -> Polygon:
    left = box.x - box.width / 2
    top = box.y - box.height / 2
    right = box.x + box.width / 2
    bottom = box.y + box.height / 2
    return (left, top), (right, top), (right, bottom), (left, bottom)


def _map_polygon_to_output(polygon: Polygon, geometry: CenteringGeometry) -> Polygon:
    cos_angle = math.cos(geometry.angle)
    sin_angle = math.sin(geometry.angle)
    crop_width, crop_height = geometry.crop_size
    output_center = (crop_width / 2, crop_height / 2)

    output_points: list[Point] = []
    for x, y in polygon:
        dx = x - geometry.center[0]
        dy = y - geometry.center[1]
        output_points.append(
            (
                output_center[0]
                + geometry.scale * (cos_angle * dx - sin_angle * dy),
                output_center[1]
                + geometry.scale * (sin_angle * dx + cos_angle * dy),
            )
        )

    return (
        output_points[0],
        output_points[1],
        output_points[2],
        output_points[3],
    )
