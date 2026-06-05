from sqlalchemy.orm import Session
from uuid import UUID

import app.entities.file


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_frame_id(self, frame_id: UUID) -> app.entities.file.File | None:
        
        #SQLAlchemy --> el ORM
        #self.db.query(app.entities.file.File)           # SELECT * FROM files
        #.filter(app.entities.file.File.frame_id == frame_id)  # WHERE frame_id = ?
        #.first()                                     # LIMIT 1, devuelve None si no hay
        return self.db.query(app.entities.file.File).filter(app.entities.file.File.frame_id == frame_id).first()

    def create(self, frame_id: UUID, path: str) -> app.entities.file.File:
        file = app.entities.file.File(frame_id=frame_id, path=path)
        self.db.add(file)
        return file
