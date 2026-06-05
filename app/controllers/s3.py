from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from uuid import UUID

import app.database
import app.business.s3
import app.repositories.file_repository

router = APIRouter(prefix="/frames", tags=["S3 - Fotogramas"])

# GET /frames/{frame_id}
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
    db: Session = Depends(app.database.get_db),
):
    file_record = app.repositories.file_repository.FileRepository(db).get_by_frame_id(frame_id) #vemos si existe la foto solicitada.
    if not file_record:
        raise HTTPException(status_code=404, detail="Frame not found")
    image_data, content_type = app.business.s3.get_frame_image(file_record.path, thumbnail) #buscamos el frame en el s3
    return Response(content=image_data.read(), media_type=content_type)
