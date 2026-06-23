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
    # Valor por defecto sin tailscale definido en env
    inference_service_url: str = "http://localhost:8001"

    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "soa-realm"
    keycloak_client_id: str = "soa-client"
    keycloak_client_secret: str = ""

    # URL pública de Keycloak — la usa Keycloak mismo para el claim "iss" de los
    # tokens (vía KC_HOSTNAME), independientemente de qué URL haya usado el backend
    # para pedirlos. Tiene que coincidir con KC_HOSTNAME para validar el issuer bien.
    keycloak_public_url: str = "http://localhost:8080"

    class Config:
        env_file = ".env"


settings = Settings()
