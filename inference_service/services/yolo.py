import io
import os
from PIL import Image, UnidentifiedImageError
from ultralytics import YOLO
from config import settings

_cache: dict[str, YOLO] = {}


def get_available_models() -> list[str]:
    if not os.path.isdir(settings.models_dir):
        return []
    return [f for f in os.listdir(settings.models_dir) if f.endswith(".pt")]


def run_inference(model_id: str, image_bytes: bytes) -> list[dict]:
    if model_id not in _cache:
        path = os.path.join(settings.models_dir, model_id)
        _cache[model_id] = YOLO(path)

    model = _cache[model_id]

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except (UnidentifiedImageError, Exception):
        raise ValueError("El archivo no es una imagen válida")

    results = model(img, verbose=False)

    objects = []
    for result in results:
        for box in result.boxes:
            objects.append({
                "class": result.names[int(box.cls)],
                "confidence": round(float(box.conf), 4),
                "bbox": [round(v, 2) for v in box.xyxy[0].tolist()],
            })

    return objects
