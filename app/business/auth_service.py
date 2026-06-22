import jwt
from sqlalchemy.orm import Session

import app.business.keycloak_service
import app.repositories.person_repository
import app.entities.person


# Crea el usuario en Keycloak y, si falla el alta local, revierte la creación remota (compensación).
def register(db: Session, nombre: str, apellido: str, email: str, password: str) -> app.entities.person.Person:
    repo = app.repositories.person_repository.PersonRepository(db)
    if repo.get_by_email(email):
        raise ValueError("Ya existe una persona con ese email")

    keycloak_id = app.business.keycloak_service.keycloak_service.create_user(email, password, nombre, apellido)

    try:
        return repo.create(nombre, apellido, email, None, keycloak_id)
    except Exception:
        db.rollback()
        app.business.keycloak_service.keycloak_service.delete_user(keycloak_id)
        raise


# Direct Access Grant contra Keycloak + búsqueda del registro de negocio asociado por keycloak_id.
def login(db: Session, email: str, password: str) -> tuple[dict, app.entities.person.Person | None]:
    tokens = app.business.keycloak_service.keycloak_service.login(email, password)

    # No se verifica la firma: el token llegó en una respuesta directa de Keycloak que nosotros mismos iniciamos.
    claims = jwt.decode(tokens["access_token"], options={"verify_signature": False})
    person = app.repositories.person_repository.PersonRepository(db).get_by_keycloak_id(claims["sub"])

    return tokens, person


def refresh(refresh_token: str) -> dict:
    return app.business.keycloak_service.keycloak_service.refresh(refresh_token)
