from fastapi import APIRouter, HTTPException
import app.business.s1

# Todos los endpoint de este router van a vivir bajo /models (igual tenemos uno solo)
router = APIRouter(prefix="/models", tags=["S1 - Modelos"])

# Responde a /models
# Es asincronico. Levanta un hilo por cada request que se realice.
# Flask por otro lado, es un hilo por request y el server se clava hasta que la request termine.
@router.get(
    "",
    response_model=list[str], # la respuesta es una lista de strings ["yolo1","yolo2"]
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
        return app.business.s1.get_available_models()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
