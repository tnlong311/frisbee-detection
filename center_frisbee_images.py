from __future__ import annotations

import argparse
import sys
from pathlib import Path

from center_frisbee_image import (
    center_frisbee_image,
    load_api_settings,
    resolve_existing_input_path,
    run_detection_workflow,
)
from constants import SUPPORTED_IMAGE_SUFFIXES


def center_frisbee_images_from_api(
    input_dir: str | Path,
    output_dir: str | Path | None = None,
) -> list[str]:
    source_dir = resolve_existing_input_path(input_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {source_dir}")

    image_files = _find_image_files(source_dir)
    if not image_files:
        raise ValueError(f"No supported images found in {source_dir}.")

    api_key, gen_box, disc_line = load_api_settings()
    output_files: list[str] = []
    for image_file in image_files:
        print(f"Processing: {image_file}")
        try:
            image_output_path = _build_batch_output_path(image_file, output_dir)
            centered_files = center_frisbee_image(
                str(image_file),
                run_detection_workflow(str(image_file), api_key),
                str(image_output_path) if image_output_path else None,
                gen_box,
                disc_line,
            )
            output_files.extend(centered_files)
        except Exception as exc:
            print(f"Failed: {image_file} ({exc})")
            continue

        print(f"Success: {image_file}")

    return output_files


def _find_image_files(input_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ),
        key=lambda path: (path.name.lower(), path.name),
    )


def _build_batch_output_path(
    image_file: Path,
    output_dir: str | Path | None,
) -> Path | None:
    if output_dir is None:
        return None

    resolved_output_dir = _resolve_output_dir(output_dir)
    return resolved_output_dir / f"{image_file.stem}-boxed{image_file.suffix}"


def _resolve_output_dir(output_dir: str | Path) -> Path:
    output_path = Path(output_dir)
    if output_path.is_absolute() and not output_path.exists():
        return Path.cwd() / str(output_path).lstrip("/")

    return output_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect frisbees via Roboflow and center every image in a folder."
    )
    parser.add_argument(
        "input_dir",
        help=(
            "Relative or absolute path to an image folder. A leading slash can be "
            "used for repo-relative input, for example /data/images."
        ),
    )
    parser.add_argument(
        "--output",
        help="Optional output folder for centered images.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        output_files = center_frisbee_images_from_api(args.input_dir, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Saved centered images to:")
    for output_file in output_files:
        print(f"- {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
