# Architecture

This project has one installed CLI, `frisbee`, backed by a small `src/` package. The CLI exposes subcommands for single-image centering, batch centering, and video creation.

## Module Layout

```text
src/
  api.py        Roboflow workflow integration
  batch.py      Folder validation and per-image centering orchestration
  centering.py  Detection parsing, selected-box choice, geometry, and rendering
  cli.py        argparse command surface
  config.py     Constants, env names, .env loading, and env parsing
  image_io.py   Pillow loading, image discovery, and auto-resize helpers
  paths.py      Repo-relative input resolution and output path helpers
  video.py      Image-frame to vertical MP4 generation
```

## Roboflow Integration

`src.api.run_detection_workflow` calls the hosted Roboflow Serverless workflow configured in `.env`:

```text
ROBOFLOW_WORKSPACE_NAME=<workspace>
ROBOFLOW_WORKFLOW_ID=<workflow>
image key: ROBOFLOW_IMAGE_KEY
```

The API key is loaded from `ROBOFLOW_API_KEY` in `.env`. The image key remains the internal constant `image`.

## Detection Parsing

The centering flow accepts Roboflow responses that are either an object or an array. It extracts prediction dictionaries from these shapes:

- top-level `predictions` list
- nested `predictions.predictions` list
- a dictionary that directly looks like one prediction

A valid prediction must have `x`, `y`, `width`, and `height`. If a `class` key exists, only `class == "frisbee"` is used. When multiple frisbees are present, the highest-confidence prediction is selected; missing or invalid confidence is treated as `0`.

## Box Model

The detection box uses center coordinates:

```text
left   = x - width / 2
top    = y - height / 2
right  = x + width / 2
bottom = y + height / 2
```

Corners are named:

```text
A = top-left
B = top-right
C = bottom-right
D = bottom-left
```

## Centering Geometry

The output is a vertical 9:16 crop centered on the selected box center. The selected disc line controls the crop width and rotation:

```text
output width  = selected line length * 3
output height = output width * 16 / 9
```

When `DISC_LINE` is unset or blank, two diagonal variants are written:

```text
BD variant: rotate by  atan(height / width)
AC variant: rotate by -atan(height / width)
```

When `DISC_LINE` is set, one variant is written:

```text
AB or CD: rotate by 0
BC or AD: rotate by -pi / 2
AC:       rotate by -atan(height / width)
BD:       rotate by  atan(height / width)
```

The selected line is aligned horizontally in the output. If the required crop extends outside the source image, the operation fails instead of padding.

## Output Paths

Centered images are saved under `data/output/` by default. Each centered output includes a timestamp and variant suffix.

Default diagonal variants:

```text
data/output/<image-stem>-boxed-<timestamp>-bd.<ext>
data/output/<image-stem>-boxed-<timestamp>-ac.<ext>
```

When `DISC_LINE` is set, only that line is written:

```text
data/output/<image-stem>-boxed-<timestamp>-<disc-line>.<ext>
```

When `GEN_BOX=true`, the source image with the selected detection box is saved to:

```text
data/output-with-box/<image-stem>-boxed.<ext>
```

When `SAVE_SOURCE=true`, the processed source image is copied to:

```text
data/saved-input/<image-name>
```

If `AUTO_RESIZE=true` resizes the image, the resized working image is the one used for centering and optional source saving.

## Auto-Resize

When `AUTO_RESIZE=true`, files larger than 10 MB are resized before detection. The resize flow binary-searches for the largest dimensions that save below the 10 MB limit while preserving the input image format where possible.

## Video Generation

`src.video.images_to_video` loads supported images from a folder, sorts them by filename, object-fills each frame to `1440x2560`, and streams raw RGB frames to FFmpeg. The output uses H.264 with `yuv420p` pixel format and defaults to:

```text
data/output/video.mp4
```

## Failure Behavior

- Missing input file or folder raises an error.
- A folder with no supported images raises an error.
- A single image with no detected frisbee prints a skip message and saves nothing.
- Batch processing continues after per-image failures and prints the failed image path.
- Crop requests outside the source image bounds raise an error.
- Missing Python dependencies or FFmpeg raise installation-focused errors.
