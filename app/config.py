from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://soa:soa@db:5432/soatp"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "soa-frames"

    # Models
    models_dir: str = "/app/models"

    # App
    base_url: str = "http://localhost:8000"

    # Inference service (corre en PC local vía Tailscale)
    inference_service_url: str = "http://localhost:8001"

    class Config:
        env_file = ".env"


settings = Settings()
