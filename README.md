# Módulo S5 - Reconocimiento Facial

Este README explica cómo probar la parte correspondiente a los endpoints **S5.1, S5.2 y S5.3** del Trabajo Integrador SOA.

La implementación utiliza:

- **FastAPI** para los endpoints REST.
- **PostgreSQL + pgvector** para almacenar y comparar embeddings.
- **InsightFace** para detección de rostro y generación de embeddings faciales.
- **ONNX Runtime CPU** como backend de inferencia.
- **Docker Compose** para levantar la API, base de datos y nginx.

---

## Endpoints implementados

| Servicio | Endpoint | Descripción |
|---|---|---|
| S5.1 | `POST /persons` | Crea una persona. |
| S5.1 | `GET /persons/{person_id}` | Obtiene una persona por ID. |
| S5.2 | `POST /persons/{person_id}/embeddings` | Genera embeddings faciales para una persona. |
| S5.3 | `POST /face-recognition` | Reconoce una persona a partir de una imagen. |

---

## Levantar el proyecto

Desde la raíz del repositorio:

```bash
cp .env.example .env
```

Completar las variables necesarias en `.env`, especialmente las de AWS si se quieren probar también los servicios S3/S4.

Luego levantar los contenedores:

```bash
docker compose up --build -d
```

Verificar que estén corriendo:

```bash
docker compose ps
```

La API debería quedar disponible en:

```text
http://127.0.0.1:8000/docs
```

También puede usarse nginx en:

```text
http://127.0.0.1/docs
```

---

## Nota importante sobre imágenes

Los endpoints de embeddings y reconocimiento reciben imágenes en **base64**, según los schemas definidos en el proyecto.

Se recomienda usar imágenes reales `.jpg` o `.png`.

Si una imagen tiene extensión `.jpg` pero internamente es AVIF/WebP u otro formato, puede fallar dentro del contenedor con:

```json
{"detail": "No se pudo leer la imagen"}
```

En ese caso, convertirla a JPG real antes de generar el base64.

Ejemplo para convertir una imagen a JPG real:

```bash
python3 - <<'PY'
from PIL import Image

src = "imagen_original.jpg"
dst = "persona1_real.jpg"

img = Image.open(src)
img = img.convert("RGB")
img.save(dst, "JPEG", quality=95)

print("Imagen convertida a:", dst)
PY
```

Verificar formato:

```bash
file persona1_real.jpg
```

Debería mostrar algo como:

```text
JPEG image data
```

---

## Crear payloads de prueba en base64

Colocar una imagen de rostro en la raíz del proyecto, por ejemplo:

```text
persona1_real.jpg
```

Crear los payloads JSON:

```bash
python3 - <<'PY'
import base64
import json

image_path = "persona1_real.jpg"

with open(image_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

with open("embedding_payload.json", "w") as f:
    json.dump({"images": [b64]}, f)

with open("recognition_payload.json", "w") as f:
    json.dump({"image": b64, "threshold": 0.8}, f)

print("Payloads creados")
print("Base64 empieza con:", b64[:30])
print("Base64 length:", len(b64))
PY
```

Para JPG, el base64 normalmente empieza con:

```text
/9j/
```

---

## Probar S5.1 - Crear persona

```bash
curl -X POST "http://127.0.0.1:8000/persons" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Agustin",
    "apellido": "Rodeyro",
    "email": "agus@test.com",
    "extra": {
      "rol": "alumno"
    }
  }'
```

Respuesta esperada:

```json
{
  "id": "UUID_GENERADO",
  "nombre": "Agustin",
  "apellido": "Rodeyro",
  "email": "agus@test.com",
  "extra": {
    "rol": "alumno"
  }
}
```

Guardar el valor de `id`, porque se usa como `person_id` en el siguiente endpoint.

---

## Probar S5.1 - Obtener persona por ID

Reemplazar `PERSON_ID` por el UUID real devuelto al crear la persona.

```bash
curl "http://127.0.0.1:8000/persons/PERSON_ID"
```

Respuesta esperada:

```json
{
  "id": "PERSON_ID",
  "nombre": "Agustin",
  "apellido": "Rodeyro",
  "email": "agus@test.com",
  "extra": {
    "rol": "alumno"
  }
}
```

---

## Probar S5.2 - Generar embeddings

Reemplazar `PERSON_ID` por el UUID real.

```bash
curl -X POST "http://127.0.0.1:8000/persons/PERSON_ID/embeddings" \
  -H "Content-Type: application/json" \
  --data-binary @embedding_payload.json
```

Respuesta esperada:

```json
{
  "personId": "PERSON_ID",
  "processedImages": 1,
  "validEmbeddings": 1,
  "rejectedImages": 0
}
```

Si `validEmbeddings` queda en `0`, revisar que:

- La imagen sea JPG/PNG real.
- La imagen contenga exactamente un rostro.
- El base64 esté correctamente generado.

---

## Probar S5.3 - Reconocimiento facial

```bash
curl -X POST "http://127.0.0.1:8000/face-recognition" \
  -H "Content-Type: application/json" \
  --data-binary @recognition_payload.json
```

Respuesta esperada si reconoce:

```json
{
  "personId": "PERSON_ID",
  "nombre": "Agustin",
  "apellido": "Rodeyro",
  "confidence": 1.0
}
```

Respuesta esperada si no reconoce:

```json
{
  "personId": null,
  "nombre": null,
  "apellido": null,
  "confidence": 0.45
}
```

El reconocimiento depende del `threshold`. Por defecto se usa:

```json
"threshold": 0.8
```

---

## Verificar embeddings en PostgreSQL

Entrar al contenedor de base de datos:

```bash
docker exec -it soa_db psql -U soa -d soatp
```

Consultar embeddings:

```sql
SELECT id, person_id, vector_dims(vector) AS dims, created_at
FROM embeddings;
```

Se espera que `dims` sea:

```text
512
```

Salir:

```sql
\q
```

---

## Flujo completo esperado

1. Crear una persona con `POST /persons`.
2. Convertir una imagen a JPG real si hace falta.
3. Crear `embedding_payload.json` y `recognition_payload.json`.
4. Generar embedding con `POST /persons/{person_id}/embeddings`.
5. Reconocer la persona con `POST /face-recognition`.

Ejemplo de resultado final válido:

```json
{
  "personId": "b10f9455-aeb9-4fca-95c1-c8e5e7c60434",
  "nombre": "Agustin",
  "apellido": "Rodeyro",
  "confidence": 1.0
}
```

---

## Consideraciones técnicas

- InsightFace genera embeddings de **512 dimensiones**.
- Los embeddings se guardan en PostgreSQL usando `pgvector`.
- La comparación se realiza usando distancia vectorial con pgvector.
- La API corre en CPU mediante ONNX Runtime.
- El warning de CUDA es normal si el entorno no tiene GPU NVIDIA configurada.

