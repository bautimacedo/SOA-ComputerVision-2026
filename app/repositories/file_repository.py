from sqlalchemy.orm import Session
from uuid import UUID

from app.entities.file import File


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_frame_id(self, frame_id: UUID) -> File | None:
        return self.db.query(File).filter(File.frame_id == frame_id).first()

    def create(self, frame_id: UUID, path: str) -> File:
        file = File(frame_id=frame_id, path=path)
        self.db.add(file)
        return file
