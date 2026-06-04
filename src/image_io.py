from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import tempfile
from pathlib import Path
from typing import Any

from src.config import MAX_AUTO_RESIZE_BYTES, SUPPORTED_IMAGE_SUFFIXES


def load_pillow() -> tuple[Any, Any]:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required. Install dependencies with: pip3 install -r requirements.txt"
        ) from exc

    return Image, ImageDraw


@contextmanager
def prepared_image_file(image_file: Path, auto_resize: bool) -> Iterator[Path]:
    if not auto_resize or image_file.stat().st_size <= MAX_AUTO_RESIZE_BYTES:
        yield image_file
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        resized_file = Path(temp_dir) / image_file.name
        original_size = image_file.stat().st_size
        resized_size = _resize_image_under_size(
            image_file,
            resized_file,
            MAX_AUTO_RESIZE_BYTES,
        )
        print(
            "Auto-resized: "
            f"{image_file} ({format_file_size(original_size)}) -> "
            f"{format_file_size(resized_size)}"
        )
        yield resized_file


def find_image_files(input_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ),
        key=lambda path: (path.name.lower(), path.name),
    )


def format_file_size(size: int) -> str:
    return f"{size / (1024 * 1024):.2f} MB"


def _resize_image_under_size(
    image_file: Path,
    output_file: Path,
    max_bytes: int,
) -> int:
    Image, _ImageDraw = load_pillow()
    resampling_enum = getattr(Image, "Resampling", None)
    resample = resampling_enum.LANCZOS if resampling_enum else Image.LANCZOS
    with Image.open(image_file) as image:
        image.load()
        save_format = _image_save_format(image, image_file)
        low_scale = 0.01
        high_scale = 1.0
        best_size: int | None = None
        best_dimensions: tuple[int, int] | None = None

        for _attempt in range(18):
            scale = (low_scale + high_scale) / 2
            dimensions = _scaled_image_dimensions(image.size, scale)
            candidate_size = _save_resized_candidate(
                image,
                output_file,
                dimensions,
                save_format,
                resample,
            )

            if candidate_size < max_bytes:
                best_size = candidate_size
                best_dimensions = dimensions
                low_scale = scale
            else:
                high_scale = scale

        if best_dimensions is None:
            best_dimensions = _scaled_image_dimensions(image.size, low_scale)
            best_size = _save_resized_candidate(
                image,
                output_file,
                best_dimensions,
                save_format,
                resample,
            )

        if best_size >= max_bytes:
            raise ValueError(
                "Auto-resized image is still at or above "
                f"{format_file_size(max_bytes)}."
            )

        final_size = _save_resized_candidate(
            image,
            output_file,
            best_dimensions,
            save_format,
            resample,
        )
        if final_size >= max_bytes:
            raise ValueError(
                "Auto-resized image is still at or above "
                f"{format_file_size(max_bytes)}."
            )

        return final_size


def _save_resized_candidate(
    image: Any,
    output_file: Path,
    dimensions: tuple[int, int],
    save_format: str,
    resample: Any,
) -> int:
    resized_image = image.resize(dimensions, resample=resample)
    if save_format == "JPEG" and resized_image.mode not in {"RGB", "L"}:
        resized_image = resized_image.convert("RGB")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    resized_image.save(
        output_file,
        format=save_format,
        **_image_save_options(save_format),
    )
    return output_file.stat().st_size


def _scaled_image_dimensions(
    image_size: tuple[int, int],
    scale: float,
) -> tuple[int, int]:
    width, height = image_size
    return max(1, round(width * scale)), max(1, round(height * scale))


def _image_save_format(image: Any, image_file: Path) -> str:
    image_format = image.format or _image_format_from_suffix(image_file.suffix)
    normalized_format = image_format.upper()
    if normalized_format == "JPG":
        return "JPEG"
    if normalized_format == "TIF":
        return "TIFF"

    return normalized_format


def _image_format_from_suffix(suffix: str) -> str:
    formats_by_suffix = {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
        ".bmp": "BMP",
        ".tif": "TIFF",
        ".tiff": "TIFF",
    }
    return formats_by_suffix.get(suffix.lower(), suffix.lstrip("."))


def _image_save_options(save_format: str) -> dict[str, Any]:
    if save_format == "JPEG":
        return {"optimize": True, "progressive": True, "quality": 95}
    if save_format == "WEBP":
        return {"method": 6, "quality": 95}
    if save_format == "PNG":
        return {"optimize": True}

    return {}
