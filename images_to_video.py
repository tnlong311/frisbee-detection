from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

INPUT_DIR = Path("data/video-input")
DEFAULT_OUTPUT_PATH = Path("data/output/video.mp4")

TARGET_WIDTH_PX = 1440
TARGET_HEIGHT_PX = 2560
TARGET_SIZE = f"{TARGET_WIDTH_PX}x{TARGET_HEIGHT_PX}"

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

FFMPEG_VIDEO_CODEC = "libx264"
FFMPEG_PRESET = "medium"
FFMPEG_CRF = "20"
FFMPEG_PIXEL_FORMAT = "yuv420p"


def images_to_video(
    ips: float,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    input_dir: str | Path = INPUT_DIR,
) -> Path:
    _validate_ips(ips)

    image_files = _find_image_files(Path(input_dir))
    if not image_files:
        raise ValueError(f"No supported images found in {input_dir}.")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    Image = _load_pillow()
    ffmpeg_path = _load_ffmpeg()
    command = _build_ffmpeg_command(ffmpeg_path, ips, output_file)
    _write_video_frames(command, image_files, Image)

    return output_file


def _validate_ips(ips: float) -> None:
    if ips <= 0:
        raise ValueError("IPS must be greater than 0.")


def _find_image_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    return sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ),
        key=lambda path: (path.name.lower(), path.name),
    )


def _load_pillow() -> Any:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required. Install dependencies with: pip3 install -r requirements.txt"
        ) from exc

    return Image


def _load_ffmpeg() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise RuntimeError("FFmpeg is required. Install it and make sure ffmpeg is on PATH.")

    return ffmpeg_path


def _build_ffmpeg_command(ffmpeg_path: str, ips: float, output_file: Path) -> list[str]:
    return [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        TARGET_SIZE,
        "-r",
        _format_ips(ips),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        FFMPEG_VIDEO_CODEC,
        "-preset",
        FFMPEG_PRESET,
        "-crf",
        FFMPEG_CRF,
        "-pix_fmt",
        FFMPEG_PIXEL_FORMAT,
        "-movflags",
        "+faststart",
        str(output_file),
    ]


def _format_ips(ips: float) -> str:
    if ips.is_integer():
        return str(int(ips))

    return f"{ips:g}"


def _write_video_frames(command: list[str], image_files: list[Path], Image: Any) -> None:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if process.stdin is None:
        process.kill()
        raise RuntimeError("Could not open FFmpeg stdin.")

    try:
        for image_file in image_files:
            process.stdin.write(_build_video_frame(image_file, Image))
        process.stdin.close()
    except BrokenPipeError as exc:
        stderr = _read_stderr(process)
        process.wait()
        raise RuntimeError(_format_ffmpeg_error(stderr)) from exc
    except Exception:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
        process.kill()
        process.wait()
        raise

    stderr = _read_stderr(process)
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(_format_ffmpeg_error(stderr))


def _build_video_frame(image_file: Path, Image: Any) -> bytes:
    try:
        with Image.open(image_file) as image:
            frame = _object_fill(image.convert("RGB"), Image)
            return frame.tobytes()
    except Exception as exc:
        raise RuntimeError(f"Could not process image {image_file}: {exc}") from exc


def _object_fill(image: Any, Image: Any) -> Any:
    source_width, source_height = image.size
    if source_width <= 0 or source_height <= 0:
        raise ValueError("Image dimensions must be positive.")

    scale = max(TARGET_WIDTH_PX / source_width, TARGET_HEIGHT_PX / source_height)
    resized_width = max(TARGET_WIDTH_PX, round(source_width * scale))
    resized_height = max(TARGET_HEIGHT_PX, round(source_height * scale))

    resampling_enum = getattr(Image, "Resampling", None)
    resample = resampling_enum.LANCZOS if resampling_enum else Image.LANCZOS
    resized = image.resize((resized_width, resized_height), resample=resample)

    left = (resized_width - TARGET_WIDTH_PX) // 2
    top = (resized_height - TARGET_HEIGHT_PX) // 2
    return resized.crop(
        (
            left,
            top,
            left + TARGET_WIDTH_PX,
            top + TARGET_HEIGHT_PX,
        )
    )


def _read_stderr(process: subprocess.Popen[bytes]) -> str:
    if process.stderr is None:
        return ""

    return process.stderr.read().decode("utf-8", errors="replace").strip()


def _format_ffmpeg_error(stderr: str) -> str:
    if not stderr:
        return "FFmpeg failed without error output."

    return f"FFmpeg failed: {stderr}"


def _parse_ips(value: str) -> float:
    try:
        ips = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("IPS must be a number.") from exc

    if ips <= 0:
        raise argparse.ArgumentTypeError("IPS must be greater than 0.")

    return ips


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a 1440x2560 vertical H.264 MP4 video from images in data/video-input."
    )
    parser.add_argument(
        "--ips",
        required=True,
        type=_parse_ips,
        help="Images per second. Example: 5 means 5 images in 1 second; 0.5 means 1 image in 2 seconds.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help=f"Output video path. Defaults to {DEFAULT_OUTPUT_PATH}.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        output_file = images_to_video(args.ips, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved video to: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
