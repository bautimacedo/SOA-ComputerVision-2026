import requests
import boto3
import app.config
from botocore.exceptions import ClientError

_s3 = None


class StorageError(Exception):
    pass


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            aws_access_key_id=app.config.settings.aws_access_key_id,
            aws_secret_access_key=app.config.settings.aws_secret_access_key,
            region_name=app.config.settings.aws_region,
        )
    return _s3

#requests arma el body así:
#files= → campos binarios del multipart. El valor es una tupla (nombre_archivo, bytes, content_type)
#data= → campos de texto del multipart (equivalente a Form)
def run_inference(model_id: str, image_bytes: bytes) -> list[dict]:
    try:
        response = requests.post(
            f"{app.config.settings.inference_service_url}/infer",
            files={"image": ("image.jpg", image_bytes, "image/jpeg")},
            data={"model_id": model_id},
            timeout=60,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Inference service unreachable")

    if response.status_code == 400:
        raise ValueError(response.json().get("detail", "Bad request"))

    response.raise_for_status()
    return response.json()["objects"]

#S3 no tiene carpetas reales — frames/uuid.jpg es simplemente un string que actúa como path.
# put_object es un HTTP PUT al API de AWS S3. Si falla, boto3 lanza ClientError, que nosotros
# convertimos en StorageError para que el controller lo atrape y devuelva 503.
def upload_frame(frame_id: str, image_bytes: bytes, content_type: str = "image/jpeg") -> str:
    key = f"frames/{frame_id}.jpg"
    try:
        _get_s3().put_object(
            Bucket=app.config.settings.s3_bucket_name,
            Key=key,
            Body=image_bytes,
            ContentType=content_type,
        )
    except ClientError as e:
        raise StorageError(f"S3 upload failed: {e}") from e
    return key
