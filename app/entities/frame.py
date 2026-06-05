from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import app.database


class Frame(app.database.Base):
    __tablename__ = "frames"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metadata_ = Column("metadata", JSONB, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    detections = relationship("Detection", back_populates="frame", lazy="select")
    files = relationship("File", back_populates="frame", lazy="select")
