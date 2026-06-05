from fastapi import FastAPI

import app.controllers.s1
import app.controllers.s2
import app.controllers.s3
import app.controllers.s4
import app.controllers.s5
import app.database
import app.entities

# Guardamos las referencias antes de que 'app' se rebindee a la instancia FastAPI
s1_router        = app.controllers.s1.router
s2_router        = app.controllers.s2.router
s3_router        = app.controllers.s3.router
s4_router        = app.controllers.s4.router
persons_router   = app.controllers.s5.persons_router
recognition_router = app.controllers.s5.recognition_router

app.database.Base.metadata.create_all(bind=app.database.engine)

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
7. Cargá imágenes para generar sus embeddings faciales con **S5.3**.
8. Identificá personas en nuevas imágenes con **S5.4**.

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
        "name": "S3 - Fotogramas",
        "description": "Recuperación de imágenes por ID (original o thumbnail).",
    },
    {
        "name": "S4 - Búsqueda",
        "description": "Consulta filtrada de fotogramas por ubicación, modelo y clases detectadas.",
    },
    {
        "name": "S5 - Personas y Reconocimiento Facial",
        "description": "Registro de personas, generación de embeddings faciales e identificación por similitud vectorial.",
    },
]

# A partir de acá 'app' deja de referenciar el paquete y pasa a ser la instancia FastAPI
app = FastAPI(
    title="SOA 2026 — Sistema de análisis de fotogramas",
    description=description,
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={"name": "Repositorio", "url": "https://github.com/bautimacedo/SOA-ComputerVision-2026"},
)

app.include_router(s1_router)
app.include_router(s2_router)
app.include_router(s4_router)  # /frames/search — debe ir antes que /{frame_id}
app.include_router(s3_router)  # /frames/{frame_id}
app.include_router(persons_router)
app.include_router(recognition_router)


@app.get("/health", tags=["Estado"], summary="Health check")
def health():
    """Verifica que el servidor está en funcionamiento."""
    return {"status": "ok"}
