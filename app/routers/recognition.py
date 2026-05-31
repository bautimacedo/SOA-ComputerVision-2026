from fastapi import APIRouter, HTTPException

from app.schemas.person import RecognitionRequest, RecognitionResponse

router = APIRouter(prefix="/face-recognition", tags=["S5.3 - Reconocimiento facial"])


@router.post(
    "",
    response_model=RecognitionResponse,
    summary="Identificar persona en una imagen",
    description="""
Recibe una imagen e intenta identificar a la persona comparando su rostro
contra todos los embeddings almacenados en la base de datos.

**Proceso:**
1. Se detecta el rostro en la imagen recibida.
2. Se genera su embedding (vector de 512 dimensiones) con InsightFace.
3. Se compara contra todos los embeddings en la BD usando similitud vectorial (pgvector).
4. Si el mejor match supera el `threshold`, se retorna la persona identificada.
5. Si ninguno supera el umbral, se retorna `personId: null`.

**Threshold:** valor entre 0 y 1 que define qué tan similar debe ser el rostro para considerarse
un match válido. Un valor alto (0.9) es más estricto; uno bajo (0.6) es más permisivo.
El valor por defecto es `0.8`.

La imagen se envía en formato **base64**.
""",
    response_description="Persona identificada con su nivel de confianza, o `personId: null` si no se reconoció a nadie.",
    responses={
        400: {"description": "No se detectó ningún rostro en la imagen."},
        422: {"description": "Request mal formado."},
        501: {"description": "No implementado aún."},
    },
)
def recognize_face(body: RecognitionRequest):
    raise HTTPException(status_code=501, detail="Not implemented yet")
