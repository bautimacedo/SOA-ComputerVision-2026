from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID

from app.entities.embedding import Embedding


class EmbeddingRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, person_id: UUID, vector: list[float]) -> Embedding:
        embedding = Embedding(person_id=person_id, vector=vector)
        self.db.add(embedding)
        return embedding

    def find_nearest(self, vector: list[float]) -> dict | None:
        embedding_literal = "[" + ",".join(str(v) for v in vector) + "]"
        result = self.db.execute(
            text("""
                SELECT
                    e.person_id,
                    p.nombre,
                    p.apellido,
                    p.email,
                    e.vector <=> CAST(:embedding AS vector(512)) AS distance
                FROM embeddings e
                JOIN persons p ON p.id = e.person_id
                ORDER BY e.vector <=> CAST(:embedding AS vector(512))
                LIMIT 1
            """),
            {"embedding": embedding_literal}
        ).mappings().first()
        return dict(result) if result else None
