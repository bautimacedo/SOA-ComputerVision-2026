import json
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dtos.detection import DetectionResponse
from app.business.storage import upload_frame, StorageError
from app.business.yolo import run_inference, get_available_models
from app.repositories.frame_repository import FrameRepository
from app.repositories.file_repository import FileRepository
from app.repositories.detection_repository import DetectionRepository

router = APIRouter(prefix="/detections", tags=["S2 - Detección"])


@router.post(
    "",
    response_model=DetectionResponse,
    status_code=201,
    summary="Ejecutar detección sobre un fotograma",
    description="""
Recibe una imagen junto con metadatos geográficos y el modelo a utilizar.

**Flujo interno:**
1. Valida que el modelo exista y que los metadatos incluyan `lat` y `lon`.
2. Envía la imagen al servicio de inferencia en la PC local (vía Tailscale) para ejecutar YOLO.
3. Sube la imagen a AWS S3.
4. Persiste en la base de datos: el fotograma (`frames`), la ubicación del archivo (`files`) y los resultados de detección (`detections`).

Los metadatos son flexibles: además de `lat` y `lon` se puede incluir cualquier campo adicional
(nombre de cámara, piso, fecha, etc.) y quedará almacenado en la base de datos.

El campo `bbox` en cada detección representa las coordenadas del bounding box en valores **relativos de 0 a 1** respecto al tamaño de la imagen: `[x1, y1, x2, y2]`. Son independientes de la resolución — el mismo objeto en una imagen de 640×480 y en una de 1920×1080 tiene el mismo bbox.
""",
    response_description="frameId asignado, modelo usado y lista de objetos detectados.",
    responses={
        400: {"description": "Modelo no disponible, metadata inválida, faltan `lat`/`lon`, o el archivo no es una imagen."},
        503: {"description": "El servicio de inferencia no está accesible, o error al subir a S3."},
        500: {"description": "Error al persistir en base de datos."},
    },
)
def run_detection(
    image: UploadFile = File(..., description="Imagen a procesar (JPEG, PNG, etc.)"),
    model_id: str = Form(..., description="Nombre del modelo a usar. Debe existir en GET /models."),
    metadata: str = Form(..., description="""JSON con al menos `lat` y `lon` (obligatorios). El resto de los campos es completamente libre y se almacena tal cual en la base de datos.

Ejemplos de campos adicionales: `camara`, `piso`, `zona`, `fecha`, `resolucion`, `dispositivo`, o cualquier otro atributo relevante para el caso de uso.

Ejemplo mínimo: `{"lat": -34.6037, "lon": -58.3816}`

Ejemplo completo: `{"lat": -34.6037, "lon": -58.3816, "camara": "cam_01", "piso": 3, "zona": "acceso_norte", "resolucion": "1080p"}`
"""),
    db: Session = Depends(get_db),
):
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

    try:
        detected_objects = run_inference(model_id, image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    frame_id = uuid.uuid4()
    try:
        s3_key = upload_frame(str(frame_id), image_bytes, image.content_type or "image/jpeg")
    except StorageError as e:
        raise HTTPException(status_code=503, detail=f"Error al guardar imagen: {e}")

    try:
        frame_repo = FrameRepository(db)
        file_repo = FileRepository(db)
        detection_repo = DetectionRepository(db)

        frame_repo.create(frame_id, meta)
        file_repo.create(frame_id, s3_key)
        detection_repo.create(frame_id, model_id, {"objects": detected_objects})
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al persistir resultados")

    return DetectionResponse(frameId=frame_id, modelId=model_id, detections=detected_objects)
