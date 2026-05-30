import json
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.frame import Frame
from app.models.detection import Detection
from app.models.file import File as FileRecord
from app.schemas.detection import DetectionResponse
from app.services.storage import upload_frame, StorageError
from app.services.yolo import run_inference, get_available_models

router = APIRouter(prefix="/detections", tags=["S2 - Detección"])


@router.post("", response_model=DetectionResponse, status_code=201)
def run_detection(
    image: UploadFile = File(...),
    model_id: str = Form(...),
    metadata: str = Form(..., description='JSON con al menos {"lat": ..., "lon": ...}'),
    db: Session = Depends(get_db),
):
    """S2 — Ejecuta YOLO sobre el fotograma y persiste imagen, metadatos y detecciones."""
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    try:
        available = get_available_models()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if model_id not in available:
        raise HTTPException(status_code=400, detail=f"Modelo '{model_id}' no disponible")

    try:
        meta = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="metadata debe ser un JSON válido")

    if "lat" not in meta or "lon" not in meta:
        raise HTTPException(status_code=400, detail="metadata debe incluir 'lat' y 'lon'")

    image_bytes = image.file.read()

    # 1. Inferencia primero — si falla, no se persiste nada
    try:
        detected_objects = run_inference(model_id, image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 2. Subir imagen a S3
    frame_id = uuid.uuid4()
    try:
        s3_key = upload_frame(str(frame_id), image_bytes, image.content_type or "image/jpeg")
    except StorageError as e:
        raise HTTPException(status_code=503, detail=f"Error al guardar imagen: {e}")

    # 3. Persistir en BD — rollback si falla
    try:
        frame = Frame(
            id=frame_id,
            metadata_=meta,
        )
        db.add(frame)
        file = FileRecord(
            frame_id=frame_id,
            path=s3_key,
        )
        db.add(file)
        detection = Detection(
            frame_id=frame_id,
            model_id=model_id,
            detections={"objects": detected_objects},
        )
        db.add(detection)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al persistir resultados")

    return DetectionResponse(
        frameId=frame_id,
        modelId=model_id,
        detections=detected_objects,
    )
