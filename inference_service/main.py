from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from services.yolo import run_inference, get_available_models

app = FastAPI(title="Inference Service", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/models", response_model=list[str])
def list_models():
    return get_available_models()


@app.post("/infer")
def infer(
    image: UploadFile = File(...),
    model_id: str = Form(...),
):
    if model_id not in get_available_models():
        raise HTTPException(status_code=400, detail=f"Modelo '{model_id}' no disponible")

    image_bytes = image.file.read()

    try:
        objects = run_inference(model_id, image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"objects": objects}
