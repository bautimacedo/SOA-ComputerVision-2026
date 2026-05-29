from fastapi import APIRouter, HTTPException
from uuid import UUID

from app.schemas.person import PersonCreate, PersonResponse, EmbeddingRequest, EmbeddingResponse

router = APIRouter(prefix="/persons", tags=["S5 - Personas y Embeddings"])


@router.post("", response_model=PersonResponse, status_code=201)
def create_person(body: PersonCreate):
    """S5.1 — Registra una nueva persona.
    TODO: Rodilla implementa este endpoint.
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: UUID):
    """S5.1 — Obtiene información de una persona.
    TODO: Rodilla implementa este endpoint.
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/{person_id}/embeddings", response_model=EmbeddingResponse)
def generate_embeddings(person_id: UUID, body: EmbeddingRequest):
    """S5.2 — Sube imágenes y genera embeddings faciales para una persona.
    TODO: Rodilla implementa este endpoint.
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")
