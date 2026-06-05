import requests
from app.config import settings


def get_available_models() -> list[str]:
    try:
        response = requests.get(
            f"{settings.inference_service_url}/models",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Inference service unreachable")


def run_inference(model_id: str, image_bytes: bytes) -> list[dict]:
    try:
        response = requests.post(
            f"{settings.inference_service_url}/infer",
            files={"image": ("image.jpg", image_bytes, "image/jpeg")},
            data={"model_id": model_id},
            timeout=60,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Inference service unreachable")

    if response.status_code == 400:
        raise ValueError(response.json().get("detail", "Bad request"))

    response.raise_for_status()
    return response.json()["objects"]
