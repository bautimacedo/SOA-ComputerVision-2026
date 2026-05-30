import io
import boto3
from botocore.exceptions import ClientError
from PIL import Image
from app.config import settings

_s3 = None


class StorageError(Exception):
    pass


def get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
    return _s3


def upload_frame(frame_id: str, image_bytes: bytes, content_type: str = "image/jpeg") -> str:
    """Sube una imagen a S3 y devuelve la key."""
    key = f"frames/{frame_id}.jpg"
    try:
        get_s3().put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=image_bytes,
            ContentType=content_type,
        )
    except ClientError as e:
        raise StorageError(f"S3 upload failed: {e}") from e
    return key


def get_frame_image(path: str, thumbnail: bool = False):
    """Descarga una imagen de S3. Devuelve (stream, content_type) o (None, None)."""
    try:
        response = get_s3().get_object(Bucket=settings.s3_bucket_name, Key=path)
        image_bytes = response["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None, None
        raise StorageError(f"S3 download failed: {e}") from e

    if thumbnail:
        image_bytes = _make_thumbnail(image_bytes)

    return io.BytesIO(image_bytes), "image/jpeg"


def _make_thumbnail(image_bytes: bytes, max_size: tuple = (320, 320)) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img:
        img.thumbnail(max_size)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
