import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import app.database
import app.dtos.frame
import app.repositories.frame_repository

router = APIRouter(prefix="/frames", tags=["S4 - Búsqueda"])


@router.get(
    "/search",
    response_model=list[app.dtos.frame.FrameSearchResult],
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
#query --> viene en el string
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
    db: Session = Depends(app.database.get_db),
):
    if lat_min > lat_max:
        raise HTTPException(status_code=400, detail="lat_min debe ser <= lat_max")
    if lon_min > lon_max:
        raise HTTPException(status_code=400, detail="lon_min debe ser <= lon_max")

    extra_metadata = None
    if metadata:
        try:
            #parseamos
            extra_metadata = json.loads(metadata)
            if not isinstance(extra_metadata, dict):
                raise HTTPException(status_code=400, detail="metadata debe ser un objeto JSON")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="metadata debe ser un JSON válido")

    return app.repositories.frame_repository.FrameRepository(db).search(lat_min, lat_max, lon_min, lon_max, classes, extra_metadata, model_id) # se filtra en la db
