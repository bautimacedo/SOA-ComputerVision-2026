from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

import app.database
import app.dtos.person
import app.business.s5
import app.repositories.person_repository
import app.repositories.embedding_repository

persons_router = APIRouter(prefix="/persons", tags=["S5 - Personas y Reconocimiento Facial"])
recognition_router = APIRouter(prefix="/face-recognition", tags=["S5 - Personas y Reconocimiento Facial"])


# S5.1 — Registrar persona
@persons_router.post(
    "",
    response_model=app.dtos.person.PersonResponse, # respondemos con el DTO.
    status_code=201,
    summary="S5.1 — Registrar una persona",
    description=(
        "Crea un nuevo registro de persona en el sistema. "
        "El email debe ser único — devuelve 409 si ya existe una persona con ese email. "
        "El campo `extra` es libre (JSONB): puede incluir legajo, sector, rol, u otros atributos."
    ),
)
def create_person(body: app.dtos.person.PersonCreate, 
                  db: Session = Depends(app.database.get_db)):
    
    repo = app.repositories.person_repository.PersonRepository(db)
    if repo.get_by_email(body.email):
        raise HTTPException(status_code=409, detail="Ya existe una persona con ese email")
    return repo.create(body.nombre, body.apellido, body.email, body.extra)


# S5.2 — Obtener persona
@persons_router.get(
    "/{person_id}",
    response_model=app.dtos.person.PersonResponse,
    summary="S5.2 — Obtener una persona",
    description="Devuelve los datos de una persona a partir de su UUID. Retorna 404 si no existe.",
)
def get_person(person_id: UUID, db: Session = Depends(app.database.get_db)):
    person = app.repositories.person_repository.PersonRepository(db).get_by_id(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return person


# S5.3 — Generar embeddings faciales
@persons_router.post(
    "/{person_id}/embeddings",
    response_model=app.dtos.person.EmbeddingResponse,
    summary="S5.3 — Generar embeddings faciales",
    description=(
        "Recibe una o más imágenes (multipart/form-data) y genera un embedding facial de 512 dimensiones "
        "por cada imagen usando InsightFace (modelo buffalo_l). "
        "Cada imagen debe contener **exactamente un rostro** — las que tienen cero o más de uno se rechazan "
        "y se contabilizan en `rejectedImages`, sin interrumpir el procesamiento del resto. "
        "Los embeddings válidos se almacenan en PostgreSQL con pgvector asociados a la persona."
    ),
)
# solo podemos usar await si declaramos la función como async.
async def generate_embeddings(
    person_id: UUID,
    images: List[UploadFile] = File(..., description="Una o más imágenes JPG/PNG, una por campo 'images'"),  # pueden venir multiples fotos.
    db: Session = Depends(app.database.get_db)
):
    person_repo = app.repositories.person_repository.PersonRepository(db)
    embedding_repo = app.repositories.embedding_repository.EmbeddingRepository(db)

    person = person_repo.get_by_id(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    processed_images = 0
    valid_embeddings = 0
    rejected_images = 0

    for image_file in images:
        processed_images += 1
        try:
            image_bytes = await image_file.read() #espera que se lean los bytes del archivo sin bloquear el hilo. UploadFile.read() en FastAPI es una corrutina asíncrona
            vector = app.business.s5.insightface_service.get_embedding_from_bytes(image_bytes)
            embedding_repo.add(person.id, vector)
            valid_embeddings += 1
        except Exception as e:
            print(f"Error procesando imagen: {e}")
            rejected_images += 1

    db.commit()

    return app.dtos.person.EmbeddingResponse(
        personId=person.id,
        processedImages=processed_images,
        validEmbeddings=valid_embeddings,
        rejectedImages=rejected_images
    )


# S5.4 — Reconocimiento facial
@recognition_router.post(
    "",
    response_model=app.dtos.person.RecognitionResponse,
    summary="S5.4 — Reconocer una persona en una imagen",
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
    db: Session = Depends(app.database.get_db)
):
    try:
        image_bytes = await image.read()
        vector = app.business.s5.insightface_service.get_embedding_from_bytes(image_bytes) # se obtiene el embedding
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = app.repositories.embedding_repository.EmbeddingRepository(db).find_nearest(vector) # para comparar los embeddings se usa esa función.

    if result is None:
        return app.dtos.person.RecognitionResponse(personId=None, nombre=None, apellido=None, confidence=0.0)

    confidence = 1.0 - float(result["distance"])

    if confidence < threshold:
        return app.dtos.person.RecognitionResponse(personId=None, nombre=None, apellido=None, confidence=confidence)

    return app.dtos.person.RecognitionResponse(
        personId=result["person_id"],
        nombre=result["nombre"],
        apellido=result["apellido"],
        confidence=confidence
    )
