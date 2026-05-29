from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.schemas.frame import FrameSearchResult
from app.services.storage import get_frame_image
from app.services.query import search_frames

router = APIRouter(prefix="/frames", tags=["S3/S4 - Fotogramas"])


@router.get("/search", response_model=list[FrameSearchResult])
def search(
    lat_min: float = Query(...),
    lat_max: float = Query(...),
    lon_min: float = Query(...),
    lon_max: float = Query(...),
    classes: list[str] = Query(default=[]),
    metadata: str = Query(default=None, description="JSON con filtros adicionales"),
    db: Session = Depends(get_db),
):
    """S4 — Filtra fotogramas por ubicación, clases detectadas y metadatos."""
    if lat_min > lat_max:
        raise HTTPException(status_code=400, detail="lat_min debe ser <= lat_max")
    if lon_min > lon_max:
        raise HTTPException(status_code=400, detail="lon_min debe ser <= lon_max")

    return search_frames(db, lat_min, lat_max, lon_min, lon_max, classes, metadata)


@router.get("/{frame_id}")
def get_frame(
    frame_id: UUID,
    thumbnail: bool = Query(default=False),
):
    """S3 — Devuelve la imagen asociada al frameId (original o thumbnail)."""
    image_data, content_type = get_frame_image(str(frame_id), thumbnail)
    if image_data is None:
        raise HTTPException(status_code=404, detail="Frame not found")
    return StreamingResponse(image_data, media_type=content_type)
