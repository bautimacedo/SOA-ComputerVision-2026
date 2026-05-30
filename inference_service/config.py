from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    models_dir: str = "./models"

    class Config:
        env_file = ".env"


settings = Settings()
