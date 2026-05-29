from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Frame(Base):
    __tablename__ = "frames"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    object_key = Column(String, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=False)
    model_id = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    detections = relationship("Detection", back_populates="frame", lazy="select")
