from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Any
from uuid import UUID


class PersonCreate(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    extra: dict[str, Any] | None = None


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    personId: UUID = Field(alias="id")
    nombre: str
    apellido: str
    email: str
    extra: dict[str, Any] | None = None


class EmbeddingRequest(BaseModel):
    images: list[str]   # base64 o URLs


class EmbeddingResponse(BaseModel):
    personId: UUID
    processedImages: int
    validEmbeddings: int
    rejectedImages: int


class RecognitionRequest(BaseModel):
    image: str          # base64
    threshold: float = 0.8


class RecognitionResponse(BaseModel):
    personId: UUID | None
    nombre: str | None = None
    apellido: str | None = None
    confidence: float
