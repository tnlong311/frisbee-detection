from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


Box = tuple[float, float, float, float]


def draw_frisbee_box(
    image_path: str,
    detections: dict | list,
    output_path: str | None = None,
) -> str:
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file does not exist: {image_file}")

    boxes = _extract_boxes(detections)
    if not boxes:
        raise ValueError("No usable frisbee predictions found in detection JSON.")

    output_file = Path(output_path) if output_path else _default_output_path(image_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    Image, ImageDraw = _load_pillow()
    with Image.open(image_file) as image:
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        for box in boxes:
            draw.rectangle(box, outline="red", width=2)
        annotated.save(output_file)

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
) -> str:
    detections = _load_detection_json_file(json_path)
    return draw_frisbee_box(image_path, detections, output_path)


def _extract_boxes(detections: dict | list) -> list[Box]:
    prediction_items = _extract_prediction_items(detections)
    boxes: list[Box] = []

    for prediction in prediction_items:
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
        boxes.append(
            (
                x - width / 2,
                y - height / 2,
                x + width / 2,
                y + height / 2,
            )
        )

    return boxes


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Draw a thin red frisbee detection box onto an image."
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
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        json_file = args.json_file or args.json_path
        if args.json_file and args.json_path:
            raise ValueError("Use either the positional JSON path or --json-file, not both.")

        detections = _load_detection_json(json_file, args.json)
        output_file = draw_frisbee_box(args.image_path, detections, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved annotated image to: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
