from __future__ import annotations

import time
from pathlib import Path

from src.config import BOX_OUTPUT_DIR, DEFAULT_OUTPUT_DIR, SAVED_INPUT_DIR


def resolve_existing_input_path(input_path: str | Path) -> Path:
    path = Path(input_path)
    if path.exists():
        return path

    if path.is_absolute():
        repo_relative_path = Path.cwd() / str(path).lstrip("/")
        if repo_relative_path.exists():
            return repo_relative_path

    return path


def resolve_output_dir(output_dir: str | Path) -> Path:
    output_path = Path(output_dir)
    if output_path.is_absolute() and not output_path.exists():
        return Path.cwd() / str(output_path).lstrip("/")

    return output_path


def build_batch_output_path(
    image_file: Path,
    output_dir: str | Path | None,
) -> Path | None:
    if output_dir is None:
        return None

    return resolve_output_dir(output_dir) / f"{image_file.stem}-boxed{image_file.suffix}"


def default_centered_output_path(image_file: Path) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{image_file.stem}-boxed{image_file.suffix}"


def variant_output_paths(base_output_file: Path, suffixes: tuple[str, ...]) -> tuple[Path, ...]:
    return tuple(add_output_suffix(base_output_file, suffix) for suffix in suffixes)


def source_with_box_output_path(image_file: Path) -> Path:
    return BOX_OUTPUT_DIR / f"{image_file.stem}-boxed{image_file.suffix}"


def saved_source_output_path(image_file: Path) -> Path:
    return SAVED_INPUT_DIR / image_file.name


def add_output_suffix(output_file: Path, suffix: str) -> Path:
    return output_file.with_name(f"{output_file.stem}-{suffix}{output_file.suffix}")


def add_output_timestamp(output_file: Path, timestamp: str) -> Path:
    return output_file.with_name(f"{output_file.stem}-{timestamp}{output_file.suffix}")


def current_output_timestamp() -> str:
    return str(int(time.time()))
