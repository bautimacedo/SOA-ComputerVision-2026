from fastapi import FastAPI
from app.routers import models, detections, frames, persons, recognition
from app.database import engine, Base
import app.models  # registra todos los modelos antes del create_all

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SOA TP - Análisis de Fotogramas", version="1.0.0")

app.include_router(models.router)
app.include_router(detections.router)
app.include_router(frames.router)
app.include_router(persons.router)
app.include_router(recognition.router)


@app.get("/health")
def health():
    return {"status": "ok"}
