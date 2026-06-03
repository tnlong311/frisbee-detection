# Frisbee Detection Transform MVP

Minimal Python 3.11 project for detecting a frisbee with a hosted Roboflow workflow, transforming the image around the detected disc, and turning image frames into a video.

The script takes a source image, calls the `long-truong/detect-frisbees` Roboflow Serverless Hosted API workflow, then creates normalized `1125x2000` output images centered on the selected frisbee box. By default, it draws the transformed box on each output image.

## Input

1. Image path relative to this repo, for example:

   ```bash
   data/image-1.jpg
   ```

2. A local `.env` file with the Roboflow API key and box outline setting.

The script treats `x` and `y` as the center of the box:

```text
left = x - width / 2
top = y - height / 2
right = x + width / 2
bottom = y + height / 2
```

When multiple frisbee predictions exist, the highest-confidence prediction controls the image transform. Missing confidence is treated as `0`.

## Transform

The output image is generated relative to the selected box diagonal:

```text
output aspect ratio = 9:16
target box diagonal = selected box diagonal
output width = target box diagonal * 3
output height = output width * 16 / 9
```

For the selected rectangle:

```text
A = top-left
B = top-right
C = bottom-right
D = bottom-left
```

The image is scaled so the selected box diagonal stays at the target disc length. It writes two variants:

```text
BD variant: rotate by  atan(height / width)
AC variant: rotate by -atan(height / width)
```

This aligns diagonal `BD` with the horizontal line in one output image, and diagonal `AC` with the horizontal line in the other. The intersection of the box diagonals is placed at the exact center of each output image.

If the required transformed crop exceeds the source image bounds, the script returns an error instead of padding the output.

## Output

Transformed images are saved to:

```bash
data/output/
```

By default, the output files are:

```bash
data/output/<image-stem>-boxed-bd.<ext>
data/output/<image-stem>-boxed-ac.<ext>
```

For example:

```bash
data/output/image-1-boxed-bd.jpg
data/output/image-1-boxed-ac.jpg
```

## Setup

Create and activate a Python 3.11 virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install dependencies with `pip3`:

```bash
pip3 install -r requirements.txt
```

Create a local `.env` file:

```bash
ROBOFLOW_API_KEY=your_api_key_here
HAS_BOX=true
```

`HAS_BOX` accepts values such as `true`, `false`, `1`, `0`, `yes`, and `no`.

## Run

Run the hosted detection workflow and transform the image:

```bash
python3.11 draw_frisbee_box.py data/image-1.jpg
```

Run with an explicit output path:

```bash
python3.11 draw_frisbee_box.py data/image-1.jpg --output data/output/image-1-boxed.jpg
```

This writes:

```bash
data/output/image-1-boxed-bd.jpg
data/output/image-1-boxed-ac.jpg
```

## Notes

- The script draws a thin red outline only. It does not fill the box.
- The script transforms around the highest-confidence prediction with `"class": "frisbee"`.
- If a prediction has no `class` field, it is usable when it includes `x`, `y`, `width`, and `height`.
- Detection runs through the Roboflow hosted workflow before the transform starts.
