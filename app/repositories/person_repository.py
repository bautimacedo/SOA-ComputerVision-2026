from sqlalchemy.orm import Session
from uuid import UUID
from typing import Any

from app.entities.person import Person


class PersonRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, person_id: UUID) -> Person | None:
        return self.db.query(Person).filter(Person.id == person_id).first()

    def get_by_email(self, email: str) -> Person | None:
        return self.db.query(Person).filter(Person.email == email).first()

    def create(self, nombre: str, apellido: str, email: str, extra: dict[str, Any] | None) -> Person:
        person = Person(nombre=nombre, apellido=apellido, email=email, extra=extra)
        self.db.add(person)
        self.db.commit()
        self.db.refresh(person)
        return person
