from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path

CROP_WIDTH_TO_TARGET_DISC_LINE = 3
CROP_ASPECT_WIDTH = 9
CROP_ASPECT_HEIGHT = 16

DEFAULT_GEN_BOX = False
BOX_OUTLINE_COLOR = "red"
BOX_OUTLINE_WIDTH = 2

BD_OUTPUT_SUFFIX = "bd"
AC_OUTPUT_SUFFIX = "ac"

SUPPORTED_IMAGE_SUFFIXES = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
    }
)

ROBOFLOW_API_URL = "https://serverless.roboflow.com"
ROBOFLOW_IMAGE_KEY = "image"
ROBOFLOW_USE_CACHE = True

ROBOFLOW_API_KEY_ENV = "ROBOFLOW_API_KEY"
ROBOFLOW_WORKSPACE_NAME_ENV = "ROBOFLOW_WORKSPACE_NAME"
ROBOFLOW_WORKFLOW_ID_ENV = "ROBOFLOW_WORKFLOW_ID"
GEN_BOX_ENV = "GEN_BOX"
SAVE_SOURCE_ENV = "SAVE_SOURCE"
AUTO_RESIZE_ENV = "AUTO_RESIZE"
DISC_LINE_ENV = "DISC_LINE"

DEFAULT_OUTPUT_DIR = Path("data/output")
BOX_OUTPUT_DIR = Path("data/output-with-box")
SAVED_INPUT_DIR = Path("data/saved-input")
DEFAULT_VIDEO_OUTPUT_PATH = Path("data/output/video.mp4")

MAX_AUTO_RESIZE_BYTES = 10 * 1024 * 1024
DEFAULT_DISC_LINES = ("BD", "AC")
VALID_DISC_LINES = ("AB", "BC", "CD", "AD", "AC", "BD")


@dataclass(frozen=True)
class ApiSettings:
    api_key: str
    workspace_name: str
    workflow_id: str
    gen_box: bool
    disc_line: str | None
    save_source: bool
    auto_resize: bool


def load_api_settings() -> ApiSettings:
    _load_env()
    return ApiSettings(
        api_key=_load_required_env(ROBOFLOW_API_KEY_ENV),
        workspace_name=_load_required_env(ROBOFLOW_WORKSPACE_NAME_ENV),
        workflow_id=_load_required_env(ROBOFLOW_WORKFLOW_ID_ENV),
        gen_box=_load_gen_box(),
        disc_line=_load_disc_line(),
        save_source=_load_save_source(),
        auto_resize=_load_auto_resize(),
    )


def normalize_disc_line(disc_line: str | None) -> str | None:
    if disc_line is None or not disc_line.strip():
        return None

    normalized_disc_line = disc_line.strip().upper()
    if normalized_disc_line in VALID_DISC_LINES:
        return normalized_disc_line

    valid_values = ", ".join(VALID_DISC_LINES)
    raise ValueError(
        f"Invalid {DISC_LINE_ENV} value: {disc_line!r}. Expected one of: {valid_values}."
    )


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False

    raise argparse.ArgumentTypeError("Expected true or false.")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError(
            "python-dotenv is required. Install dependencies with: pip3 install -r requirements.txt"
        ) from exc

    load_dotenv(Path.cwd() / ".env")


def _load_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")

    return value.strip()


def _load_gen_box() -> bool:
    return parse_bool(_load_required_env(GEN_BOX_ENV))


def _load_disc_line() -> str | None:
    return normalize_disc_line(os.getenv(DISC_LINE_ENV))


def _load_save_source() -> bool:
    value = os.getenv(SAVE_SOURCE_ENV)
    if value is None or not value.strip():
        return False

    return parse_bool(value)


def _load_auto_resize() -> bool:
    value = os.getenv(AUTO_RESIZE_ENV)
    if value is None or not value.strip():
        return False

    return parse_bool(value)
