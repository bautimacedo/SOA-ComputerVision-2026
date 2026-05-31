from fastapi import FastAPI
from app.routers import models, detections, frames, persons, recognition
from app.database import engine, Base
import app.models

Base.metadata.create_all(bind=engine)

description = """
Sistema backend para procesamiento de imágenes mediante modelos de inferencia YOLO,
con soporte de almacenamiento en AWS S3, base de datos relacional/vectorial (PostgreSQL + pgvector)
y reconocimiento facial mediante InsightFace.

## Flujo principal

1. Consultá los modelos disponibles con **S1**.
2. Enviá un fotograma junto con metadatos geográficos y el modelo a usar con **S2**.
3. El sistema corre la inferencia, almacena la imagen en S3 y persiste los resultados en la BD.
4. Consultá fotogramas procesados filtrando por ubicación y clases con **S4**.
5. Recuperá la imagen original o en thumbnail con **S3**.

## Reconocimiento facial

6. Registrá personas con **S5.1**.
7. Cargá imágenes para generar sus embeddings faciales con **S5.2**.
8. Identificá personas en nuevas imágenes con **S5.3**.

## Notas

- Todos los recursos se identifican mediante UUIDs.
- Los metadatos de los fotogramas son flexibles (JSONB): se requiere `lat` y `lon`, el resto es libre.
- La inferencia YOLO se ejecuta en una PC local con GPU, conectada al servidor vía Tailscale.
- La documentación interactiva permite probar todos los endpoints directamente desde el navegador.
"""

tags_metadata = [
    {
        "name": "S1 - Modelos",
        "description": "Lista los modelos de detección disponibles en el servicio de inferencia.",
    },
    {
        "name": "S2 - Detección",
        "description": "Recibe fotogramas, ejecuta inferencia YOLO y persiste imagen, metadatos y detecciones.",
    },
    {
        "name": "S3/S4 - Fotogramas",
        "description": "Recuperación de imágenes por ID (original o thumbnail) y consulta filtrada por ubicación y clases.",
    },
    {
        "name": "S5 - Personas y Embeddings",
        "description": "Registro de personas y generación de embeddings faciales mediante InsightFace.",
    },
    {
        "name": "S5.3 - Reconocimiento facial",
        "description": "Identifica personas en imágenes comparando embeddings contra la base de datos vectorial.",
    },
]

app = FastAPI(
    title="SOA 2026 — Sistema de análisis de fotogramas",
    description=description,
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={"name": "Repositorio", "url": "https://github.com/bautimacedo/SOA-ComputerVision-2026"},
)

app.include_router(models.router)
app.include_router(detections.router)
app.include_router(frames.router)
app.include_router(persons.router)
app.include_router(recognition.router)


@app.get("/health", tags=["Estado"], summary="Health check")
def health():
    """Verifica que el servidor está en funcionamiento."""
    return {"status": "ok"}
