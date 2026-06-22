from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Any

import app.dtos.person


class RegisterRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nombre": "Juan",
            "apellido": "Pérez",
            "email": "juan@mail.com",
            "password": "Secreto123!",
            "extra": {"legajo": "12345", "sector": "seguridad"}
        }
    })

    nombre: str
    apellido: str
    email: EmailStr
    password: str
    extra: dict[str, Any] | None = None


class LoginRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"email": "juan@mail.com", "password": "Secreto123!"}
    })

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    person: app.dtos.person.PersonResponse | None


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
