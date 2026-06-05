from sqlalchemy.orm import Session
from uuid import UUID

from app.entities.detection import Detection


class DetectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, frame_id: UUID, model_id: str, detections: dict) -> Detection:
        detection = Detection(frame_id=frame_id, model_id=model_id, detections=detections)
        self.db.add(detection)
        return detection
