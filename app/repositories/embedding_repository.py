from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID

import app.entities.embedding


class EmbeddingRepository:
    def __init__(self, db: Session):
        self.db = db

    # por cada foto que mandas, se agrega un embeding nuevo en la tabla, no se reemplaza.
    def add(self, person_id: UUID, vector: list[float]) -> app.entities.embedding.Embedding:
        embedding = app.entities.embedding.Embedding(person_id=person_id, vector=vector)
        self.db.add(embedding) #.add es un insert.
        return embedding

    def find_nearest(self, vector: list[float]) -> dict | None:
        embedding_literal = "[" + ",".join(str(v) for v in vector) + "]" # vector es una lista de 512 floats de Python. 
                                                                        #PostgreSQL espera recibirlo como string con formato
                                                                        #  [0.12,-0.34,0.87,...]. Esta línea arma ese string
                                                                        #  manualmente:[0.12, -0.34, 0.87]  →  "[0.12,-0.34,0.87]"

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

# e.vector <=> CAST(:embedding AS vector(512)) operador de pgvector que calcula la distancia entre 2 vectores. resultado entre 0 y 2. 0 = identicos
# ORDER BY ordena de menor a mayor las distancias
# con limit 1 trae el mas chico (osea el mas cercano de la tabla.)
# mappings().first() convierte el resultado {"person_id": ..., "nombre": ..., "distance": ...} y toma el primero, si es none no hay resukltados.