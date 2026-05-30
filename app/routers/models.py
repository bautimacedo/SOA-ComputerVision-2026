from fastapi import APIRouter, HTTPException
from app.services.yolo import get_available_models

router = APIRouter(prefix="/models", tags=["S1 - Modelos"])


@router.get("", response_model=list[str])
def list_models():
    """S1 — Lista los modelos .pt disponibles en el servicio de inferencia."""
    try:
        return get_available_models()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
