# Frisbee Detection Centering MVP

Minimal Python 3.11 project for detecting a frisbee with a hosted Roboflow workflow, centering the image around the detected disc, and turning image frames into a video.

## Scripts

```text
center_frisbee_image.py  Detect a frisbee, center the source image, and save image variants.
center_frisbee_images.py Detect frisbees in every image in a folder and save image variants.
images_to_video.py   Turn images in data/video-input into a 1440x2560 vertical H.264 MP4 video.
```

`center_frisbee_image.py` takes one source image, calls the `long-truong/detect-frisbees` Roboflow Serverless Hosted API workflow, then creates normalized output images centered on the selected frisbee box. `center_frisbee_images.py` applies the same processing to every supported image in a folder. When `GEN_BOX=true`, centered scripts also write boxed copies to `data/output-with-box`.

## Input

1. Image path or image folder path relative to this repo, for example:

   ```bash
   data/image-1.jpg
   data/images
   ```

2. A local `.env` file with the Roboflow API key and boxed-copy setting.

The script treats `x` and `y` as the center of the box:

```text
left = x - width / 2
top = y - height / 2
right = x + width / 2
bottom = y + height / 2
```

When multiple frisbee predictions exist, the highest-confidence prediction controls the image centering. Missing confidence is treated as `0`.

## Centering

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

If the required centered crop exceeds the source image bounds, the script returns an error instead of padding the output.

## Output

Centered images are saved to:

```bash
data/output/
```

By default, the unboxed output files are:

```bash
data/output/<image-stem>-boxed-bd.<ext>
data/output/<image-stem>-boxed-ac.<ext>
```

When `GEN_BOX=true`, boxed copies are also saved to:

```bash
data/output-with-box/<image-stem>-boxed-bd.<ext>
data/output-with-box/<image-stem>-boxed-ac.<ext>
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

Install FFmpeg for the video script and make sure `ffmpeg` is available on `PATH`.

Create a local `.env` file:

```bash
ROBOFLOW_API_KEY=your_api_key_here
GEN_BOX=false
```

`GEN_BOX` accepts values such as `true`, `false`, `1`, `0`, `yes`, and `no`.

## Run Detection Centering

Run the hosted detection workflow and center the image:

```bash
python3.11 center_frisbee_image.py data/image-1.jpg
```

Run with an explicit output path:

```bash
python3.11 center_frisbee_image.py data/image-1.jpg --output data/output/image-1-boxed.jpg
```

This writes:

```bash
data/output/image-1-boxed-bd.jpg
data/output/image-1-boxed-ac.jpg
```

Run against every supported image in a folder:

```bash
python3.11 center_frisbee_images.py data/images
```

Folder input also accepts a repo-relative path with a leading slash when the matching absolute path does not exist:

```bash
python3.11 center_frisbee_images.py /data/images
```

For folder input, `--output` is treated as an output folder:

```bash
python3.11 center_frisbee_images.py data/images --output data/output
```

## Run Images To Video

Place source frames in:

```bash
data/video-input/
```

Supported image formats:

```text
.jpg, .jpeg, .png, .webp, .bmp, .tif, .tiff
```

Create the default video at `data/output/video.mp4`:

```bash
python3.11 images_to_video.py --ips 30
```

Create a video with an explicit output path:

```bash
python3.11 images_to_video.py --ips 5 --output data/output/frisbee.mp4
```

Images are sorted by filename, resized with object-fill behavior, and center-cropped to `1440x2560` for vertical video.

`--ips` means images per second:

```text
--ips 5    = 5 images in 1 second
--ips 0.5  = 1 image in 2 seconds
```

The video output uses MP4 with H.264:

```text
codec = libx264
CRF = 20
preset = medium
pixel format = yuv420p
movflags = +faststart
```

This format is the default because it balances playback compatibility, encoding performance, visual quality, and file size.

## Notes

- The script draws a thin red outline only. It does not fill the box.
- The script centers around the highest-confidence prediction with `"class": "frisbee"`.
- If a prediction has no `class` field, it is usable when it includes `x`, `y`, `width`, and `height`.
- Detection runs through the Roboflow hosted workflow before centering starts.
- `images_to_video.py` returns an error if `data/video-input` has no supported images.
