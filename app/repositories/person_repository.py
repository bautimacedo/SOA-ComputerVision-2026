from sqlalchemy.orm import Session
from uuid import UUID
from typing import Any

import app.entities.person


class PersonRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, person_id: UUID) -> app.entities.person.Person | None:
        return self.db.query(app.entities.person.Person).filter(app.entities.person.Person.id == person_id).first()

    def get_by_email(self, email: str) -> app.entities.person.Person | None:
        return self.db.query(app.entities.person.Person).filter(app.entities.person.Person.email == email).first()

    def create(self, nombre: str, apellido: str, email: str, extra: dict[str, Any] | None) -> app.entities.person.Person:
        person = app.entities.person.Person(nombre=nombre, apellido=apellido, email=email, extra=extra)
        self.db.add(person)
        self.db.commit()
        self.db.refresh(person)
        return person
