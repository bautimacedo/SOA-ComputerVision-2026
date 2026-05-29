from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, cast, Float

from app.models.frame import Frame
from app.schemas.frame import FrameSearchResult
from app.config import settings


def search_frames(
    db: Session,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    classes: list[str],
    extra_metadata_json: str | None,
) -> list[FrameSearchResult]:
    frames = (
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
        .all()
    )

    results = []
    for frame in frames:
        detection_list = [d.results for d in frame.detections]

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
