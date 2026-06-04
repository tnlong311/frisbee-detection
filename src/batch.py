from __future__ import annotations

from pathlib import Path

from src.api import run_detection_workflow
from src.centering import center_frisbee_image
from src.config import load_api_settings
from src.image_io import find_image_files, prepared_image_file
from src.paths import build_batch_output_path, resolve_existing_input_path


def center_frisbee_images_from_api(
    input_dir: str | Path,
    output_dir: str | Path | None = None,
) -> list[str]:
    source_dir = resolve_existing_input_path(input_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {source_dir}")

    image_files = find_image_files(source_dir)
    if not image_files:
        raise ValueError(f"No supported images found in {source_dir}.")

    settings = load_api_settings()
    output_files: list[str] = []
    for image_file in image_files:
        print(f"Processing: {image_file}")
        try:
            image_output_path = build_batch_output_path(image_file, output_dir)
            with prepared_image_file(image_file, settings.auto_resize) as processing_file:
                centered_files = center_frisbee_image(
                    str(processing_file),
                    run_detection_workflow(
                        str(processing_file),
                        settings.api_key,
                        settings.workspace_name,
                        settings.workflow_id,
                    ),
                    str(image_output_path) if image_output_path else None,
                    settings.gen_box,
                    settings.disc_line,
                    settings.save_source,
                )
            if not centered_files:
                continue

            output_files.extend(centered_files)
        except Exception as exc:
            print(f"Failed: {image_file} ({exc})")
            continue

        print(f"Success: {image_file}")

    return output_files
