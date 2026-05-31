from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, cast, Float, exists

from app.models.frame import Frame
from app.models.detection import Detection
from app.schemas.frame import FrameSearchResult
from app.config import settings


def search_frames(
    db: Session,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    classes: list[str],
    extra_metadata: dict | None,
    model_id: str | None,
) -> list[FrameSearchResult]:
    query = (
        db.query(Frame)
        .options(selectinload(Frame.detections))
        .filter(
            and_(
                cast(Frame.metadata_["lat"].astext, Float) >= lat_min,
                cast(Frame.metadata_["lat"].astext, Float) <= lat_max,
                cast(Frame.metadata_["lon"].astext, Float) >= lon_min,
                cast(Frame.metadata_["lon"].astext, Float) <= lon_max,
            )
        )
    )

    if extra_metadata:
        for key, value in extra_metadata.items():
            query = query.filter(
                Frame.metadata_[key].astext == str(value)
            )

    if model_id:
        query = query.filter(
            exists().where(
                Detection.frame_id == Frame.id,
                Detection.model_id == model_id,
            )
        )

    frames = query.all()

    results = []
    for frame in frames:
        detection_list = [d.detections for d in frame.detections]

        if classes:
            detected_classes = {
                obj["class"]
                for det in detection_list
                for obj in det.get("objects", [])
            }
            if not any(c in detected_classes for c in classes):
                continue

        results.append(
            FrameSearchResult(
                frameId=frame.id,
                imageURL=f"{settings.base_url}/frames/{frame.id}",
                metadata=frame.metadata_,
                detections=detection_list,
            )
        )

    return results
