from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, cast, Float, exists
from uuid import UUID

from app.entities.frame import Frame
from app.entities.detection import Detection
from app.dtos.frame import FrameSearchResult
from app.config import settings


class FrameRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, frame_id: UUID, metadata: dict) -> Frame:
        frame = Frame(id=frame_id, metadata_=metadata)
        self.db.add(frame)
        return frame

    def search(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        classes: list[str],
        extra_metadata: dict | None,
        model_id: str | None,
    ) -> list[FrameSearchResult]:
        query = (
            self.db.query(Frame)
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
                query = query.filter(Frame.metadata_[key].astext == str(value))

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
