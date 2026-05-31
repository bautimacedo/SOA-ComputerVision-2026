import json
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.file import File
from app.schemas.frame import FrameSearchResult
from app.services.storage import get_frame_image
from app.services.query import search_frames

router = APIRouter(prefix="/frames", tags=["S3/S4 - Fotogramas"])


@router.get(
    "/search",
    response_model=list[FrameSearchResult],
    summary="Buscar fotogramas por ubicación, modelo, clase y metadatos",
    description="""
Consulta fotogramas previamente procesados. Todos los filtros son opcionales excepto las coordenadas,
y se aplican en conjunto (AND): solo se retornan fotogramas que cumplan **todos** los filtros activos.

---

**Filtros disponibles:**

**Ubicación** *(obligatorio)*
Rango de latitud y longitud. Define el área geográfica de búsqueda.

**Modelo** *(opcional)*
Nombre exacto del modelo YOLO con el que se procesó el fotograma.
Útil para comparar resultados entre modelos distintos.
- Ejemplos: `model_id=best.pt`, `model_id=yolo11n.pt`

**Clases detectadas** *(opcional)*
Filtra fotogramas donde YOLO detectó al menos una de las clases indicadas.
Se pueden pasar múltiples clases repitiendo el parámetro.
- Ejemplos: `classes=person`, `classes=person&classes=car`

**Metadatos** *(opcional)*
JSON con cualquier campo enviado al registrar el fotograma. Coincidencia exacta de valor.
Se pueden combinar múltiples campos en el mismo JSON.
Si un fotograma no tiene el campo indicado, no aparece en los resultados — no es un error.
- Ejemplos: `{"camara":"cam_01"}`, `{"piso":3}`, `{"camara":"cam_01","zona":"norte"}`

---

El campo `imageURL` en cada resultado apunta al endpoint S3 para recuperar la imagen.
""",
    response_description="Lista de fotogramas que cumplen todos los filtros. Puede ser lista vacía.",
    responses={
        400: {"description": "`lat_min > lat_max`, `lon_min > lon_max`, o `metadata` no es un JSON válido."},
    },
)
def search(
    lat_min: float = Query(..., description="Latitud mínima del rango.", example=-35.0),
    lat_max: float = Query(..., description="Latitud máxima del rango.", example=-34.0),
    lon_min: float = Query(..., description="Longitud mínima del rango.", example=-59.0),
    lon_max: float = Query(..., description="Longitud máxima del rango.", example=-58.0),
    classes: list[str] = Query(default=[], description="Clases a filtrar. Repetible: `&classes=person&classes=car`."),
    model_id: str = Query(default=None, description="Modelo con el que se procesó el fotograma. Ej: `best.pt`, `yolo11n.pt`."),
    metadata: str = Query(
        default=None,
        description="""JSON con filtros adicionales sobre los metadatos del fotograma. Coincidencia exacta de valor.
Si un fotograma no tiene el campo indicado, no aparece en los resultados.
Ejemplo: `{"camara":"cam_01","piso":3}`""",
    ),
    db: Session = Depends(get_db),
):
    if lat_min > lat_max:
        raise HTTPException(status_code=400, detail="lat_min debe ser <= lat_max")
    if lon_min > lon_max:
        raise HTTPException(status_code=400, detail="lon_min debe ser <= lon_max")

    extra_metadata = None
    if metadata:
        try:
            extra_metadata = json.loads(metadata)
            if not isinstance(extra_metadata, dict):
                raise HTTPException(status_code=400, detail="metadata debe ser un objeto JSON")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="metadata debe ser un JSON válido")

    return search_frames(db, lat_min, lat_max, lon_min, lon_max, classes, extra_metadata, model_id)


@router.get(
    "/{frame_id}",
    summary="Recuperar imagen por ID",
    description="""
Descarga la imagen asociada a un fotograma desde AWS S3 y la devuelve como binario puro JPEG.

El parámetro `thumbnail` permite obtener una versión reducida de la imagen (máximo 320×320 píxeles,
manteniendo la proporción original) útil para previsualizaciones.

La imagen **no se almacena en el servidor** — se descarga de S3 en memoria y se devuelve como binario puro en el body del response HTTP (`Content-Type: image/jpeg`).
""",
    response_description="Imagen en formato JPEG como binario puro.",
    responses={
        404: {"description": "No existe ningún archivo asociado a ese frameId."},
        422: {"description": "El frameId no tiene formato UUID válido."},
    },
)
def get_frame(
    frame_id: UUID,
    thumbnail: bool = Query(default=False, description="Si es `true`, devuelve la imagen reducida a máximo 320×320 px."),
    db: Session = Depends(get_db),
):
    file_record = db.query(File).filter(File.frame_id == frame_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Frame not found")
    image_data, content_type = get_frame_image(file_record.path, thumbnail)
    return Response(content=image_data.read(), media_type=content_type)
