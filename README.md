# Frisbee Detection Centering MVP

Minimal Python 3.11 project for detecting a frisbee with a hosted Roboflow workflow, centering the image around the detected disc, and turning image frames into a video.

## Scripts

```text
center_frisbee_image.py  Detect a frisbee, center the source image, and save image variants.
center_frisbee_images.py Detect frisbees in every image in a folder and save image variants.
images_to_video.py   Turn images in a folder into a 1440x2560 vertical H.264 MP4 video.
```

`center_frisbee_image.py` takes one source image, calls the `long-truong/detect-frisbees` Roboflow Serverless Hosted API workflow, then creates normalized output images centered on the selected frisbee box. `center_frisbee_images.py` applies the same processing to every supported image in a folder. When `GEN_BOX=true`, centered scripts also write one boxed original image to `data/output-with-box`. When `SAVE_SOURCE=true`, successfully processed source images are copied to `data/saved-input`. When `AUTO_RESIZE=true`, source images over 10 MB are resized before detection and cropping.

## Input

1. Image path or image folder path relative to this repo, for example:

   ```bash
   data/image-1.jpg
   data/images
   ```

2. A local `.env` file with the Roboflow API key, boxed-copy setting, and optional disc-line setting.

The script treats `x` and `y` as the center of the box:

```text
left = x - width / 2
top = y - height / 2
right = x + width / 2
bottom = y + height / 2
```

When multiple frisbee predictions exist, the highest-confidence prediction controls the image centering. Missing confidence is treated as `0`.

## Centering

The output image size is generated relative to the selected disc line:

```text
output aspect ratio = 9:16
target disc line = selected disc line length
output width = target disc line * 4
output height = output width * 16 / 9
```

For the selected rectangle:

```text
A = top-left
B = top-right
C = bottom-right
D = bottom-left
```

The selected disc line controls the crop size and rotation. By default, when `DISC_LINE` is unset or blank, it writes two diagonal variants:

```text
BD variant: rotate by  atan(height / width)
AC variant: rotate by -atan(height / width)
```

This aligns diagonal `BD` with the horizontal line in one output image, and diagonal `AC` with the horizontal line in the other. To generate one image for a known disc line, set `DISC_LINE` to one of:

```text
AB or CD: rotate by 0
BC or AD: rotate by -pi / 2
AC:       rotate by -atan(height / width)
BD:       rotate by  atan(height / width)
```

`DISC_LINE` is case-insensitive and accepts `AB`, `BC`, `CD`, `AD`, `AC`, or `BD`. The selected line is aligned with the horizontal line in the output image. The intersection of the box diagonals is placed at the exact center of each output image.

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

When `DISC_LINE` is set, only that line's output file is written:

```bash
data/output/<image-stem>-boxed-<disc-line>.<ext>
```

When `GEN_BOX=true`, one original source image with the detected box is also saved to:

```bash
data/output-with-box/<image-stem>-boxed.<ext>
```

When `SAVE_SOURCE=true`, each source image with a detected box and successful centered crop is copied to:

```bash
data/saved-input/<image-name>.<ext>
```

If `AUTO_RESIZE=true` resized the image, `SAVE_SOURCE=true` saves that resized working image instead of the original.

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
SAVE_SOURCE=false
AUTO_RESIZE=false
DISC_LINE=
```

`GEN_BOX` accepts values such as `true`, `false`, `1`, `0`, `yes`, and `no`.

`SAVE_SOURCE` accepts the same boolean values as `GEN_BOX`. It defaults to `false` when unset or blank.

`AUTO_RESIZE` accepts the same boolean values as `GEN_BOX`. It defaults to `false` when unset or blank. When enabled, images larger than 10 MB are resized to the largest generated size under 10 MB before being sent to Roboflow.

`DISC_LINE` is optional. Leave it blank to generate the default `bd` and `ac` variants, or set it to `AB`, `BC`, `CD`, `AD`, `AC`, or `BD` to generate only that variant.

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

Use a source frames folder, for example:

```bash
data/video-input/
```

Supported image formats:

```text
.jpg, .jpeg, .png, .webp, .bmp, .tif, .tiff
```

Create the default video at `data/output/video.mp4`:

```bash
python3.11 images_to_video.py data/video-input --ips 30
```

Create a video with an explicit output path:

```bash
python3.11 images_to_video.py data/my-frames --ips 5 --output data/output/frisbee.mp4
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
- `images_to_video.py` returns an error if the input folder has no supported images.
