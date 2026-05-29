from fastapi import APIRouter, HTTPException

from app.schemas.person import RecognitionRequest, RecognitionResponse

router = APIRouter(prefix="/face-recognition", tags=["S5.3 - Reconocimiento facial"])


@router.post("", response_model=RecognitionResponse)
def recognize_face(body: RecognitionRequest):
    """S5.3 — Identifica una persona a partir de una imagen.
    TODO: Rodilla implementa este endpoint.
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")
