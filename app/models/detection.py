from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Detection(Base):
    __tablename__ = "detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    frame_id = Column(UUID(as_uuid=True), ForeignKey("frames.id"), nullable=False)
    model_id = Column(String, nullable=False)
    results = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    frame = relationship("Frame", back_populates="detections")
