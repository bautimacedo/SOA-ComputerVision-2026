from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.person import Person
from app.models.embedding import Embedding
from app.schemas.person import PersonCreate, PersonResponse, EmbeddingRequest, EmbeddingResponse
from app.services.insightface_service import insightface_service

router = APIRouter(prefix="/persons", tags=["S5 - Personas y Embeddings"])


@router.post("", response_model=PersonResponse, status_code=201)
def create_person(body: PersonCreate, db: Session = Depends(get_db)):
    existing_person = db.query(Person).filter(Person.email == body.email).first()

    if existing_person:
        raise HTTPException(status_code=409, detail="Ya existe una persona con ese email")

    person = Person(
        nombre=body.nombre,
        apellido=body.apellido,
        email=body.email,
        extra=body.extra
    )

    db.add(person)
    db.commit()
    db.refresh(person)

    return person


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: UUID, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()

    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    return person


@router.post("/{person_id}/embeddings", response_model=EmbeddingResponse)
def generate_embeddings(
    person_id: UUID,
    body: EmbeddingRequest,
    db: Session = Depends(get_db)
):
    person = db.query(Person).filter(Person.id == person_id).first()

    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    processed_images = 0
    valid_embeddings = 0
    rejected_images = 0

    for image_base64 in body.images:
        processed_images += 1

        try:
            embedding_vector = insightface_service.get_embedding_from_base64(image_base64)

            embedding = Embedding(
                person_id=person.id,
                vector=embedding_vector
            )

            db.add(embedding)
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