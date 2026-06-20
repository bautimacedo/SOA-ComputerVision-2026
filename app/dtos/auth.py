from pydantic import BaseModel, EmailStr, ConfigDict

import app.dtos.person


class RegisterRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nombre": "Juan",
            "apellido": "Pérez",
            "email": "juan@mail.com",
            "password": "Secreto123!"
        }
    })

    nombre: str
    apellido: str
    email: EmailStr
    password: str


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
