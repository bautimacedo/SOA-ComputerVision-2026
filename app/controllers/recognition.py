from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.dtos.person import RecognitionResponse
from app.business.insightface_service import insightface_service
from app.repositories.embedding_repository import EmbeddingRepository

router = APIRouter(prefix="/face-recognition", tags=["S5.3 - Reconocimiento facial"])


@router.post(
    "",
    response_model=RecognitionResponse,
    summary="Reconocer una persona en una imagen",
    description=(
        "Recibe una imagen (multipart/form-data) y un umbral de confianza opcional. "
        "Genera el embedding facial con InsightFace y lo compara contra todos los embeddings "
        "almacenados usando distancia coseno (pgvector). "
        "Si el embedding más cercano supera el `threshold`, devuelve los datos de la persona reconocida. "
        "Si no hay match o la confianza es insuficiente, devuelve `personId: null` con el valor de confianza obtenido. "
        "La confianza se calcula como `1 - distancia_coseno` (rango 0.0–1.0)."
    ),
)
async def recognize_face(
    image: UploadFile = File(..., description="Imagen JPG/PNG con exactamente un rostro visible"),
    threshold: float = Form(default=0.8, ge=0.0, le=1.0, description="Umbral mínimo de confianza. Rango: 0.0–1.0"),
    db: Session = Depends(get_db)
):
    try:
        image_bytes = await image.read()
        vector = insightface_service.get_embedding_from_bytes(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = EmbeddingRepository(db).find_nearest(vector)

    if result is None:
        return RecognitionResponse(personId=None, nombre=None, apellido=None, confidence=0.0)

    confidence = 1.0 - float(result["distance"])

    if confidence < threshold:
        return RecognitionResponse(personId=None, nombre=None, apellido=None, confidence=confidence)

    return RecognitionResponse(
        personId=result["person_id"],
        nombre=result["nombre"],
        apellido=result["apellido"],
        confidence=confidence
    )
