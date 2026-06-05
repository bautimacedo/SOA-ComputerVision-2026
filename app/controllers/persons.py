from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.dtos.person import PersonCreate, PersonResponse, EmbeddingResponse
from app.business.insightface_service import insightface_service
from app.repositories.person_repository import PersonRepository
from app.repositories.embedding_repository import EmbeddingRepository

router = APIRouter(prefix="/persons", tags=["S5 - Personas y Embeddings"])


@router.post(
    "",
    response_model=PersonResponse,
    status_code=201,
    summary="Registrar una persona",
    description=(
        "Crea un nuevo registro de persona en el sistema. "
        "El email debe ser único — devuelve 409 si ya existe una persona con ese email. "
        "El campo `extra` es libre (JSONB): puede incluir legajo, sector, rol, u otros atributos."
    ),
)
def create_person(body: PersonCreate, db: Session = Depends(get_db)):
    repo = PersonRepository(db)

    if repo.get_by_email(body.email):
        raise HTTPException(status_code=409, detail="Ya existe una persona con ese email")

    return repo.create(body.nombre, body.apellido, body.email, body.extra)


@router.get(
    "/{person_id}",
    response_model=PersonResponse,
    summary="Obtener una persona",
    description="Devuelve los datos de una persona a partir de su UUID. Retorna 404 si no existe.",
)
def get_person(person_id: UUID, db: Session = Depends(get_db)):
    person = PersonRepository(db).get_by_id(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return person


@router.post(
    "/{person_id}/embeddings",
    response_model=EmbeddingResponse,
    summary="Generar embeddings faciales",
    description=(
        "Recibe una o más imágenes (multipart/form-data) y genera un embedding facial de 512 dimensiones "
        "por cada imagen usando InsightFace (modelo buffalo_l). "
        "Cada imagen debe contener **exactamente un rostro** — las que tienen cero o más de uno se rechazan "
        "y se contabilizan en `rejectedImages`, sin interrumpir el procesamiento del resto. "
        "Los embeddings válidos se almacenan en PostgreSQL con pgvector asociados a la persona."
    ),
)
async def generate_embeddings(
    person_id: UUID,
    images: List[UploadFile] = File(..., description="Una o más imágenes JPG/PNG, una por campo 'images'"),
    db: Session = Depends(get_db)
):
    person_repo = PersonRepository(db)
    embedding_repo = EmbeddingRepository(db)

    person = person_repo.get_by_id(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    processed_images = 0
    valid_embeddings = 0
    rejected_images = 0

    for image_file in images:
        processed_images += 1
        try:
            image_bytes = await image_file.read()
            vector = insightface_service.get_embedding_from_bytes(image_bytes)
            embedding_repo.add(person.id, vector)
            valid_embeddings += 1
        except Exception as e:
            print(f"Error procesando imagen: {e}")
            rejected_images += 1

    db.commit()

    return EmbeddingResponse(
        personId=person.id,
        processedImages=processed_images,
        validEmbeddings=valid_embeddings,
        rejectedImages=rejected_images
    )
