import cv2
import numpy as np
from insightface.app import FaceAnalysis


class InsightFaceService:
    def __init__(self):
        self.app = FaceAnalysis(name="buffalo_l")
        self.app.prepare(ctx_id=-1, det_size=(640, 640))  # CPU — cambiar a ctx_id=0 para GPU

    def get_embedding_from_bytes(self, image_bytes: bytes) -> list[float]:
        image_array = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("No se pudo leer la imagen")

        faces = self.app.get(image)

        if len(faces) == 0:
            raise ValueError("No se detectó ningún rostro en la imagen")

        if len(faces) > 1:
            raise ValueError("Se detectó más de un rostro en la imagen")

        embedding = faces[0].embedding

        if embedding.shape[0] != 512:
            raise ValueError("El embedding generado no tiene 512 dimensiones")

        return embedding.astype(float).tolist()


insightface_service = InsightFaceService()
