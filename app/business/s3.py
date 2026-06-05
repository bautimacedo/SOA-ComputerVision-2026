import io
import boto3
import app.config
from botocore.exceptions import ClientError
from PIL import Image

_s3 = None


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

#La función devuelve una tupla, el stream y el content type
def get_frame_image(path: str, thumbnail: bool = False):
    try:
        response = _get_s3().get_object(Bucket=app.config.settings.s3_bucket_name, Key=path)
        image_bytes = response["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None, None
        raise

    if thumbnail:
        image_bytes = _make_thumbnail(image_bytes)

    return io.BytesIO(image_bytes), "image/jpeg"


def _make_thumbnail(image_bytes: bytes, max_size: tuple = (320, 320)) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img: #pillow no puede abrir bytes crudos directamente, necesita un objeto tipo archivo, por eso envolvemos en BytesIO
        img.thumbnail(max_size)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()  # devuelve los bytes 