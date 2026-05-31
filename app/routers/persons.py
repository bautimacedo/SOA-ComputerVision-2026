from fastapi import APIRouter, HTTPException
from uuid import UUID

from app.schemas.person import PersonCreate, PersonResponse, EmbeddingRequest, EmbeddingResponse

router = APIRouter(prefix="/persons", tags=["S5 - Personas y Embeddings"])


@router.post(
    "",
    response_model=PersonResponse,
    status_code=201,
    summary="Registrar una nueva persona",
    description="""
Crea un nuevo registro de persona en el sistema.

El campo `extra` es opcional y acepta cualquier estructura JSON adicional
(legajo, sector, fecha de alta, etc.).

El `email` debe ser único — no se pueden registrar dos personas con el mismo email.
""",
    response_description="Datos de la persona creada, incluyendo el `personId` asignado.",
    responses={
        422: {"description": "Falta un campo obligatorio o el email no tiene formato válido."},
        501: {"description": "No implementado aún."},
    },
)
def create_person(body: PersonCreate):
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get(
    "/{person_id}",
    response_model=PersonResponse,
    summary="Obtener datos de una persona",
    description="Retorna la información de una persona registrada a partir de su `personId`.",
    response_description="Datos completos de la persona.",
    responses={
        404: {"description": "No existe una persona con ese ID."},
        422: {"description": "El `personId` no tiene formato UUID válido."},
        501: {"description": "No implementado aún."},
    },
)
def get_person(person_id: UUID):
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post(
    "/{person_id}/embeddings",
    response_model=EmbeddingResponse,
    summary="Generar embeddings faciales",
    description="""
Asocia imágenes a una persona y genera sus representaciones faciales (embeddings) usando **InsightFace**.

Por cada imagen recibida:
1. Se detecta si hay un rostro presente.
2. Si hay rostro, se genera un vector de **512 dimensiones** que codifica sus características.
3. El vector se almacena en la tabla `embeddings` vinculado a la persona.
4. Si no se detecta rostro, la imagen es rechazada.

Una persona puede tener múltiples embeddings. Cuantos más embeddings tenga,
mayor es la precisión del reconocimiento facial (S5.3).

Las imágenes se envían en formato **base64**.
""",
    response_description="Resumen del procesamiento: cuántas imágenes se procesaron, cuántos embeddings fueron generados y cuántas imágenes fueron rechazadas.",
    responses={
        404: {"description": "No existe una persona con ese `personId`."},
        422: {"description": "Request mal formado."},
        501: {"description": "No implementado aún."},
    },
)
def generate_embeddings(person_id: UUID, body: EmbeddingRequest):
    raise HTTPException(status_code=501, detail="Not implemented yet")
