from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, cast, Float, exists
from uuid import UUID

import app.entities.frame
import app.entities.detection
import app.dtos.frame
import app.config


class FrameRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, frame_id: UUID, metadata: dict) -> app.entities.frame.Frame:
        frame = app.entities.frame.Frame(id=frame_id, metadata_=metadata)
        self.db.add(frame)
        return frame

    # función para filtrar en la base de datos.
    def search(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        classes: list[str],
        extra_metadata: dict | None,
        model_id: str | None,
    ) -> list[app.dtos.frame.FrameSearchResult]:
        query = (
            self.db.query(app.entities.frame.Frame)
            .options(selectinload(app.entities.frame.Frame.detections))
            .filter(
                and_(
                    cast(app.entities.frame.Frame.metadata_["lat"].astext, Float) >= lat_min,
                    cast(app.entities.frame.Frame.metadata_["lat"].astext, Float) <= lat_max,
                    cast(app.entities.frame.Frame.metadata_["lon"].astext, Float) >= lon_min,
                    cast(app.entities.frame.Frame.metadata_["lon"].astext, Float) <= lon_max,
                )
            )
        )

        if extra_metadata:
            for key, value in extra_metadata.items():
                query = query.filter(app.entities.frame.Frame.metadata_[key].astext == str(value))

        if model_id:
            query = query.filter(
                exists().where(
                    app.entities.detection.Detection.frame_id == app.entities.frame.Frame.id,
                    app.entities.detection.Detection.model_id == model_id,
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
                app.dtos.frame.FrameSearchResult(
                    frameId=frame.id,
                    imageURL=f"{app.config.settings.base_url}/frames/{frame.id}",
                    metadata=frame.metadata_,
                    detections=detection_list,
                )
            )

        return results
