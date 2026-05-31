from fastapi import APIRouter, HTTPException
from app.services.yolo import get_available_models

router = APIRouter(prefix="/models", tags=["S1 - Modelos"])


@router.get(
    "",
    response_model=list[str],
    summary="Listar modelos disponibles",
    description="""
Retorna la lista de modelos de detección disponibles en el servicio de inferencia (PC local).

Los modelos son archivos `.pt` ubicados en la carpeta `models/` del servicio de inferencia.
El nombre retornado es el mismo que se debe usar como `model_id` al enviar un fotograma a **S2**.
""",
    response_description="Lista de nombres de archivos `.pt` disponibles.",
    responses={
        503: {"description": "El servicio de inferencia no está accesible (PC local apagada o Tailscale caído)."},
    },
)
def list_models():
    try:
        return get_available_models()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
