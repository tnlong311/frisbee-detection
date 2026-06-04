from __future__ import annotations

from src.config import (
    ROBOFLOW_API_URL,
    ROBOFLOW_IMAGE_KEY,
    ROBOFLOW_USE_CACHE,
)


def run_detection_workflow(
    image_path: str,
    api_key: str,
    workspace_name: str,
    workflow_id: str,
) -> dict | list:
    try:
        from inference_sdk import InferenceHTTPClient
    except ImportError as exc:
        raise RuntimeError(
            "inference-sdk is required. Install dependencies with: pip3 install -r requirements.txt"
        ) from exc

    client = InferenceHTTPClient(
        api_url=ROBOFLOW_API_URL,
        api_key=api_key,
    )
    result = client.run_workflow(
        workspace_name=workspace_name,
        workflow_id=workflow_id,
        images={ROBOFLOW_IMAGE_KEY: image_path},
        use_cache=ROBOFLOW_USE_CACHE,
    )
    if not isinstance(result, (dict, list)):
        raise ValueError("Roboflow workflow result must be an object or array.")

    return result
