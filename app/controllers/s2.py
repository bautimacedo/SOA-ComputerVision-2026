import json
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

import app.database
import app.dtos.detection
import app.business.s1
import app.business.s2
import app.repositories.frame_repository
import app.repositories.file_repository
import app.repositories.detection_repository

router = APIRouter(prefix="/detections", tags=["S2 - Detección"])

# Responde a POST /detections
@router.post(
    "",
    response_model=app.dtos.detection.DetectionResponse, #Respondemos con el dto.
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


#File(...) → FastAPI lee el archivo del multipart
#Form(...) → FastAPI lee un campo de texto del multipart
#Depends(get_db) → FastAPI ejecuta get_db() y le inyecta la sesión de BD. Es el equivalente a @Autowired en Spring. El ... significa obligatorio (sin default).
# Qué es uploadfile? Tipo de FastApi para representar un archivo que viene en una request multipart.
# FastApi envuelve los datos que se mandan en el multipart asi:
# image.filename	-> nombre del archivo "foto.png"
# image.content_type -> tipo de archivo "image/jpeg"
# image.file -> stream de bytes del archivo
# image.file.read() -> leemos todos los bytes.
def run_detection(
    image: UploadFile = File(..., description="Imagen a procesar (JPEG, PNG, etc.)"),
    model_id: str = Form(..., description="Nombre del modelo a usar. Debe existir en GET /models."),
    metadata: str = Form(..., description="""JSON con al menos `lat` y `lon` (obligatorios). El resto de los campos es completamente libre y se almacena tal cual en la base de datos.

Ejemplos de campos adicionales: `camara`, `piso`, `zona`, `fecha`, `resolucion`, `dispositivo`, o cualquier otro atributo relevante para el caso de uso.

Ejemplo mínimo: `{"lat": -34.6037, "lon": -58.3816}`

Ejemplo completo: `{"lat": -34.6037, "lon": -58.3816, "camara": "cam_01", "piso": 3, "zona": "acceso_norte", "resolucion": "1080p"}`
"""),
    db: Session = Depends(app.database.get_db),
):
    
    # validación debe ser una imagen
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    try:
        available = app.business.s1.get_available_models() # traemos los modelos disponibles de la pc local
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if model_id not in available: # vemos si el modelo de la pc local existe o no
        raise HTTPException(status_code=400, detail=f"Modelo '{model_id}' no disponible")

    try:
        #Parseamos la metadata a diccionario de python. String -> python
        meta = json.loads(metadata) 
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="metadata debe ser un JSON válido")

    # comprobamos que latitud y longitud vengan obligatoriamente en la metadata
    if "lat" not in meta or "lon" not in meta:
        raise HTTPException(status_code=400, detail="metadata debe incluir 'lat' y 'lon'")

    image_bytes = image.file.read() #image es un UploadFile , .read() lee todos los bytes de la imagen y los guarda en la variable.

    try:
        # hacemos el post a la pc local para hacer la inferencia. Le pasamos la imagen y el modelo a usar.
        # No levanta otro hilo, se clava en el mismo hilo que FastApi asigno a esta request. Ya esta función esta corriendo en un hilo.
        detected_objects = app.business.s2.run_inference(model_id, image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    #GENERAMOS EL UUID ALEATORIO. LO USAMOS COMO ID EN LA BD Y COMO NOMBRE EN S3
    frame_id = uuid.uuid4()
    try:
        # subimos a s3 la foto original
        s3_key = app.business.s2.upload_frame(str(frame_id), image_bytes, image.content_type or "image/jpeg")
    except app.business.s2.StorageError as e:
        raise HTTPException(status_code=503, detail=f"Error al guardar imagen: {e}")

    try:
        frame_repo = app.repositories.frame_repository.FrameRepository(db)
        file_repo = app.repositories.file_repository.FileRepository(db)
        detection_repo = app.repositories.detection_repository.DetectionRepository(db)

        frame_repo.create(frame_id, meta)
        file_repo.create(frame_id, s3_key)
        detection_repo.create(frame_id, model_id, {"objects": detected_objects})
        db.commit() # EJECUTAMOS INSERT EN LA BD.
    except Exception:
        db.rollback() # Se entrega todo o se entrega nada.
        raise HTTPException(status_code=500, detail="Error al persistir resultados")

    return app.dtos.detection.DetectionResponse(frameId=frame_id, modelId=model_id, detections=detected_objects) #Respondemos con el DTO.
