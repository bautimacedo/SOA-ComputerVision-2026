from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.schemas.person import RecognitionRequest, RecognitionResponse
from app.services.insightface_service import insightface_service

router = APIRouter(prefix="/face-recognition", tags=["S5.3 - Reconocimiento facial"])


@router.post("", response_model=RecognitionResponse)
def recognize_face(body: RecognitionRequest, db: Session = Depends(get_db)):
    try:
        embedding_vector = insightface_service.get_embedding_from_base64(body.image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    embedding_literal = "[" + ",".join(str(value) for value in embedding_vector) + "]"

    result = db.execute(
        text("""
            SELECT
                e.id AS embedding_id,
                e.person_id,
                p.nombre,
                p.apellido,
                p.email,
                e.vector <=> CAST(:embedding AS vector(512)) AS distance
            FROM embeddings e
            JOIN persons p ON p.id = e.person_id
            ORDER BY e.vector <=> CAST(:embedding AS vector(512))
            LIMIT 1
        """),
        {
            "embedding": embedding_literal
        }
    ).mappings().first()

    if result is None:
        return RecognitionResponse(
            personId=None,
            nombre=None,
            apellido=None,
            confidence=0.0
        )

    distance = float(result["distance"])
    confidence = 1.0 - distance

    if confidence < body.threshold:
        return RecognitionResponse(
            personId=None,
            nombre=None,
            apellido=None,
            confidence=confidence
        )

    return RecognitionResponse(
        personId=result["person_id"],
        nombre=result["nombre"],
        apellido=result["apellido"],
        confidence=confidence
    )