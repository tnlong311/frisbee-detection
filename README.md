# Frisbee Detection Centering

Detect frisbees with a hosted Roboflow workflow, create centered image outputs, and convert image frames into a vertical video.

For implementation details, see [architecture.md](architecture.md).

## Setup

Create and activate a Python 3.11 virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install dependencies and the local CLI:

```bash
pip3 install -r requirements.txt
pip3 install -e .
```

Install FFmpeg for video creation and make sure `ffmpeg` is available on `PATH`.

## Environment

Create a local `.env` file in the repo root:

```bash
ROBOFLOW_API_KEY=your_api_key_here
ROBOFLOW_WORKSPACE_NAME=your_workspace_name
ROBOFLOW_WORKFLOW_ID=your_workflow_id
GEN_BOX=false
SAVE_SOURCE=false
AUTO_RESIZE=false
DISC_LINE=
```

Settings:

- `ROBOFLOW_API_KEY`: required Roboflow API key.
- `ROBOFLOW_WORKSPACE_NAME`: required Roboflow workspace name.
- `ROBOFLOW_WORKFLOW_ID`: required Roboflow workflow ID.
- `GEN_BOX`: write a copy of the source image with the detected box. Accepts `true`, `false`, `1`, `0`, `yes`, and `no`.
- `SAVE_SOURCE`: copy successfully processed source images to `data/saved-input`. Defaults to `false` when unset or blank.
- `AUTO_RESIZE`: resize source images larger than 10 MB before detection and cropping. Defaults to `false` when unset or blank.
- `DISC_LINE`: optional centering line. Leave blank for the default `BD` and `AC` variants, or set `AB`, `BC`, `CD`, `AD`, `AC`, or `BD`.

## CLI

After `pip3 install -e .`, use the `frisbee` command.

### Center One Image

```bash
frisbee center-image data/image-1.jpg
```

With an explicit output path:

```bash
frisbee center-image data/image-1.jpg --output data/output/image-1-boxed.jpg
```

### Center A Folder Of Images

```bash
frisbee center-images data/images
```

Folder input also accepts a repo-relative path with a leading slash when the matching absolute path does not exist:

```bash
frisbee center-images /data/images
```

With an explicit output folder:

```bash
frisbee center-images data/images --output data/output
```

### Create A Video From Images

Create the default video at `data/output/video.mp4`:

```bash
frisbee images-to-video data/video-input --ips 30
```

Create a video with an explicit output path:

```bash
frisbee images-to-video data/my-frames --ips 5 --output data/output/frisbee.mp4
```

`--ips` means images per second. For example, `5` means five images in one second, and `0.5` means one image every two seconds.

## Supported Image Formats

```text
.jpg, .jpeg, .png, .webp, .bmp, .tif, .tiff
```
