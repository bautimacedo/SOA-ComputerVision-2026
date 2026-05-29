import os
from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/models", tags=["S1 - Modelos"])


@router.get("", response_model=list[str])
def list_models():
    """S1 — Lista los modelos .pt disponibles en la carpeta de modelos."""
    if not os.path.isdir(settings.models_dir):
        return []
    return [f for f in os.listdir(settings.models_dir) if f.endswith(".pt")]
