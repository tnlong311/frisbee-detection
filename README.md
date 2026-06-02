# Frisbee Detection Box MVP

Minimal Python 3.11 project for drawing a thin red box around a frisbee disc from an existing detection JSON result.

This project does not run object detection itself. It takes a source image and a detection JSON object, then draws the box using the JSON values exactly.

## Input

1. Image path relative to this repo, for example:

   ```bash
   data/image-1.jpg
   ```

2. Detection JSON in Roboflow-style format:

   ```json
   [
     {
       "predictions": {
         "image": {
           "width": 4608,
           "height": 3072
         },
         "predictions": [
           {
             "width": 326,
             "height": 136,
             "x": 2229,
             "y": 1707,
             "confidence": 0.9032697081565857,
             "class": "frisbee"
           }
         ]
       }
     }
   ]
   ```

The script treats `x` and `y` as the center of the box:

```text
left = x - width / 2
top = y - height / 2
right = x + width / 2
bottom = y + height / 2
```

## Output

Annotated images are saved to:

```bash
data/output/
```

By default, the output file is:

```bash
data/output/<image-stem>-boxed.<ext>
```

For example:

```bash
data/output/image-1-boxed.jpg
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

## Run

Run with a JSON file:

```bash
python3.11 draw_frisbee_box.py data/image-1.jpg data/input-1.json
```

Run with an explicit output path:

```bash
python3.11 draw_frisbee_box.py data/image-1.jpg data/input-1.json --output data/output/image-1-boxed.jpg
```

The older named JSON argument also works:

```bash
python3.11 draw_frisbee_box.py data/image-1.jpg --json-file data/input-1.json
```

Run with inline JSON:

```bash
python3.11 draw_frisbee_box.py data/image-1.jpg --json '[{"predictions":{"predictions":[{"x":2229,"y":1707,"width":326,"height":136,"class":"frisbee"}]}}]'
```

## Notes

- The script draws a thin red outline only. It does not fill the box.
- The script draws every prediction with `"class": "frisbee"`.
- If a prediction has no `class` field, it is drawn when it includes `x`, `y`, `width`, and `height`.
- The script does not infer, detect, resize, or adjust the box from image content.
