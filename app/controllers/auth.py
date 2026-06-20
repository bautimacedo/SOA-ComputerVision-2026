from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

import app.database
import app.dtos.auth
import app.dtos.person
import app.business.auth_service

router = APIRouter(prefix="/auth", tags=["Auth - Login y Registro"])


# Auth.1 — Registro
@router.post(
    "/register",
    response_model=app.dtos.person.PersonResponse,
    status_code=201,
    summary="Registrar un usuario nuevo",
    description=(
        "Crea el usuario en Keycloak (Admin REST API) y su registro de negocio asociado en `persons`. "
        "El email debe ser único — devuelve 409 si ya existe. "
        "No inicia sesión automáticamente: hay que loguearse por separado con `POST /auth/login`."
    ),
)
def register(body: app.dtos.auth.RegisterRequest, db: Session = Depends(app.database.get_db)):
    try:
        return app.business.auth_service.register(db, body.nombre, body.apellido, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# Auth.2 — Login
@router.post(
    "/login",
    response_model=app.dtos.auth.LoginResponse,
    summary="Iniciar sesión",
    description=(
        "Autentica contra Keycloak mediante Direct Access Grant (usuario y contraseña directo, sin redirect) "
        "y devuelve los tokens junto con el perfil de la persona asociada."
    ),
)
def login(body: app.dtos.auth.LoginRequest, db: Session = Depends(app.database.get_db)):
    try:
        tokens, person = app.business.auth_service.login(db, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return app.dtos.auth.LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
        person=person,
    )


# Auth.3 — Refresh
@router.post(
    "/refresh",
    response_model=app.dtos.auth.RefreshResponse,
    summary="Renovar el access token",
    description="Cambia un refresh token vigente por un access token nuevo, sin pedir la contraseña de nuevo.",
)
def refresh(body: app.dtos.auth.RefreshRequest):
    try:
        tokens = app.business.auth_service.refresh(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return app.dtos.auth.RefreshResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
    )
