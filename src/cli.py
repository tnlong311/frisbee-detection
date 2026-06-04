from __future__ import annotations

import argparse
import logging
import sys

from src.batch import center_frisbee_images_from_api
from src.centering import center_frisbee_image_from_api
from src.config import DEFAULT_VIDEO_OUTPUT_PATH
from src.video import images_to_video


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "images-to-video":
        _configure_logging()

    try:
        return args.handler(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="frisbee",
        description="Detect and center frisbee images, then optionally create video output.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    center_image_parser = subparsers.add_parser(
        "center-image",
        help="Detect and center one image.",
        description="Detect a frisbee via Roboflow and center one image around its box.",
    )
    center_image_parser.add_argument(
        "image_path",
        help="Relative or absolute path to the source image.",
    )
    center_image_parser.add_argument(
        "--output",
        help="Optional output image path.",
    )
    center_image_parser.set_defaults(handler=_center_image_command)

    center_images_parser = subparsers.add_parser(
        "center-images",
        help="Detect and center every supported image in a folder.",
        description="Detect frisbees via Roboflow and center every supported image in a folder.",
    )
    center_images_parser.add_argument(
        "input_dir",
        help=(
            "Relative or absolute path to an image folder. A leading slash can be "
            "used for repo-relative input, for example /data/images."
        ),
    )
    center_images_parser.add_argument(
        "--output",
        help="Optional output folder for centered images.",
    )
    center_images_parser.set_defaults(handler=_center_images_command)

    video_parser = subparsers.add_parser(
        "images-to-video",
        help="Create a vertical H.264 MP4 video from image frames.",
        description="Create a 1440x2560 vertical H.264 MP4 video from images in a folder.",
    )
    video_parser.add_argument(
        "input_dir",
        help=(
            "Relative or absolute path to an image folder. A leading slash can be "
            "used for repo-relative input, for example /data/video-input."
        ),
    )
    video_parser.add_argument(
        "--ips",
        required=True,
        type=_parse_ips,
        help="Images per second. Example: 5 means 5 images in 1 second; 0.5 means 1 image in 2 seconds.",
    )
    video_parser.add_argument(
        "--output",
        default=str(DEFAULT_VIDEO_OUTPUT_PATH),
        help=f"Output video path. Defaults to {DEFAULT_VIDEO_OUTPUT_PATH}.",
    )
    video_parser.set_defaults(handler=_images_to_video_command)

    return parser


def _center_image_command(args: argparse.Namespace) -> int:
    output_files = center_frisbee_image_from_api(args.image_path, args.output)
    _print_centered_outputs(output_files)
    return 0


def _center_images_command(args: argparse.Namespace) -> int:
    output_files = center_frisbee_images_from_api(args.input_dir, args.output)
    _print_centered_outputs(output_files)
    return 0


def _images_to_video_command(args: argparse.Namespace) -> int:
    output_file = images_to_video(args.input_dir, args.ips, args.output)
    print(f"Saved video to: {output_file}")
    return 0


def _print_centered_outputs(output_files: list[str]) -> None:
    if not output_files:
        print("No centered images saved.")
        return

    print("Saved centered images to:")
    for output_file in output_files:
        print(f"- {output_file}")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_ips(value: str) -> float:
    try:
        ips = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("IPS must be a number.") from exc

    if ips <= 0:
        raise argparse.ArgumentTypeError("IPS must be greater than 0.")

    return ips


if __name__ == "__main__":
    raise SystemExit(main())
