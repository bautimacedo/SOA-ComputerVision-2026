# Diagramas de secuencia — Flujo de datos entre servicios

Muestra exactamente cómo viajan los datos entre cada componente del sistema para cada endpoint.

**Componentes:**
- **Cliente** — Postman, curl, cualquier HTTP client
- **nginx** — reverse proxy en el VPS, puerto 80/443
- **FastAPI** — aplicación Python, contenedor Docker en el VPS, puerto 8000 interno
- **PostgreSQL** — base de datos, contenedor Docker en el VPS, puerto 5432 interno
- **AWS S3** — almacenamiento de objetos, internet
- **PC local** — servicio de inferencia YOLO, conectado vía Tailscale, puerto 8001

---

## GET /health

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI

    C->>N: GET /health<br/>HTTPS :443
    N->>F: GET /health<br/>HTTP :8000 (proxy pass)
    F-->>N: 200 OK<br/>{"status": "ok"}
    N-->>C: 200 OK<br/>{"status": "ok"}
```

---

## S1 — GET /models

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI
    participant PC as PC local (Tailscale)

    C->>N: GET /models<br/>HTTPS :443
    N->>F: GET /models<br/>HTTP :8000

    F->>PC: GET /models<br/>HTTP 100.x.x.x:8001<br/>via Tailscale WireGuard
    Note over PC: Lee carpeta models/<br/>Lista archivos .pt

    alt Servicio de inferencia caído
        PC-->>F: ConnectionError
        F-->>N: 503 Inference service unreachable
        N-->>C: 503 Inference service unreachable
    else OK
        PC-->>F: 200 ["yolo11n.pt", "best.pt"]
        F-->>N: 200 ["yolo11n.pt", "best.pt"]
        N-->>C: 200 ["yolo11n.pt", "best.pt"]
    end
```

---

## S2 — POST /detections

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI
    participant PC as PC local (Tailscale)
    participant S3 as AWS S3
    participant DB as PostgreSQL

    C->>N: POST /detections<br/>multipart: image + model_id + metadata<br/>HTTPS :443
    N->>F: POST /detections<br/>HTTP :8000<br/>max body: 50MB

    Note over F: Validar content_type
    Note over F: Parsear metadata JSON<br/>Verificar lat y lon

    F->>PC: GET /models<br/>HTTP 100.x.x.x:8001<br/>Validar que model_id existe

    alt Servicio de inferencia caído
        PC-->>F: ConnectionError
        F-->>N: 503 Inference service unreachable
        N-->>C: 503
    else model_id no existe
        PC-->>F: 200 [lista de modelos]
        F-->>N: 400 Modelo no disponible
        N-->>C: 400
    else OK
        PC-->>F: 200 [lista de modelos]

        F->>PC: POST /infer<br/>multipart: image bytes + model_id<br/>HTTP 100.x.x.x:8001<br/>timeout: 60s

        Note over PC: Carga modelo .pt (o usa caché)<br/>Abre imagen con Pillow<br/>Ejecuta YOLO en GPU<br/>Extrae clases, confianzas y bboxes<br/>normalizados [0-1]

        PC-->>F: 200<br/>{"objects": [<br/>  {"class":"person","confidence":0.91,"bbox":[...]},<br/>  {"class":"zebra","confidence":0.87,"bbox":[...]}<br/>]}

        Note over F: Genera frame_id = uuid.uuid4()

        F->>S3: PUT frames/{frame_id}.jpg<br/>Body: bytes de la imagen<br/>Content-Type: image/jpeg
        S3-->>F: 200 OK<br/>ETag: "abc123..."

        F->>DB: BEGIN TRANSACTION<br/>INSERT INTO frames<br/>(id, metadata, created_at)
        F->>DB: INSERT INTO files<br/>(id, frame_id, path)<br/>path = "frames/{frame_id}.jpg"
        F->>DB: INSERT INTO detections<br/>(id, frame_id, model_id, detections)<br/>detections = {"objects": [...]}
        DB-->>F: COMMIT OK

        F-->>N: 201 Created<br/>{<br/>  "frameId": "uuid",<br/>  "modelId": "yolo11n.pt",<br/>  "detections": [...]<br/>}
        N-->>C: 201 Created<br/>{frameId, modelId, detections}
    end
```

---

## S3 — GET /frames/{frameId}

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI
    participant DB as PostgreSQL
    participant S3 as AWS S3

    C->>N: GET /frames/{frameId}?thumbnail=false<br/>HTTPS :443
    N->>F: GET /frames/{frameId}<br/>HTTP :8000

    Note over F: Valida formato UUID

    F->>DB: SELECT path FROM files<br/>WHERE frame_id = {frameId}

    alt Frame no existe
        DB-->>F: 0 rows
        F-->>N: 404 Frame not found
        N-->>C: 404
    else Frame existe
        DB-->>F: path = "frames/{frameId}.jpg"

        F->>S3: GET frames/{frameId}.jpg<br/>Bucket: soa-frames-tp
        S3-->>F: 200 OK<br/>Body: bytes JPEG completos

        alt thumbnail=true
            Note over F: Pillow abre la imagen en memoria<br/>img.thumbnail((320, 320))<br/>Reencoda a JPEG
            F-->>N: 200 OK<br/>Content-Type: image/jpeg<br/>Content-Length: N bytes reducidos<br/>Body: JPEG reducido (máx 320×320)
        else thumbnail=false o ausente
            F-->>N: 200 OK<br/>Content-Type: image/jpeg<br/>Content-Length: N bytes originales<br/>Body: JPEG original completo
        end

        N-->>C: 200 OK<br/>Body: bytes JPEG
    end
```

---

## S4 — GET /frames/search

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI
    participant DB as PostgreSQL

    C->>N: GET /frames/search<br/>?lat_min=-35&lat_max=-34<br/>&lon_min=-59&lon_max=-58<br/>&model_id=best.pt<br/>&classes=person<br/>&metadata={"camara":"cam_01"}<br/>HTTPS :443

    N->>F: GET /frames/search<br/>HTTP :8000

    Note over F: Validar lat_min <= lat_max<br/>Validar lon_min <= lon_max<br/>Parsear y validar metadata JSON

    F->>DB: SELECT frames.* FROM frames<br/>WHERE metadata->>'lat' BETWEEN -35 AND -34<br/>AND metadata->>'lon' BETWEEN -59 AND -58<br/>AND EXISTS (<br/>  SELECT 1 FROM detections<br/>  WHERE frame_id = frames.id<br/>  AND model_id = 'best.pt'<br/>)<br/>AND metadata->>'camara' = 'cam_01'<br/>(carga detections con selectinload)

    DB-->>F: Lista de frames con sus detections

    Note over F: Filtro Python por classes:<br/>Para cada frame, revisa si algún<br/>objeto detectado es "person".<br/>Descarta los que no matchean.

    Note over F: Construye respuesta:<br/>frameId, imageURL, metadata, detections

    F-->>N: 200 OK<br/>[<br/>  {<br/>    "frameId": "uuid",<br/>    "imageURL": "https://soagmr.mooo.com/frames/uuid",<br/>    "metadata": {"lat":-34.6,"lon":-58.3,"camara":"cam_01"},<br/>    "detections": [{"objects":[...]}]<br/>  }<br/>]
    N-->>C: 200 OK<br/>Lista de resultados (puede ser [])
```

---

## S5.1 — POST /persons

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI
    participant DB as PostgreSQL

    C->>N: POST /persons<br/>{"nombre":"Juan","apellido":"Pérez",<br/>"email":"juan@mail.com","extra":{...}}<br/>HTTPS :443
    N->>F: POST /persons<br/>HTTP :8000

    F->>DB: SELECT * FROM persons<br/>WHERE email = 'juan@mail.com'

    alt Email ya registrado
        DB-->>F: 1 row
        F-->>N: 409 Ya existe una persona con ese email
        N-->>C: 409
    else Email disponible
        DB-->>F: 0 rows
        F->>DB: INSERT INTO persons<br/>(id, nombre, apellido, email, extra, created_at)
        DB-->>F: COMMIT OK
        F-->>N: 201 Created<br/>{"personId":"uuid","nombre":"Juan",<br/>"apellido":"Pérez","email":"juan@mail.com","extra":{...}}
        N-->>C: 201 Created<br/>{personId, nombre, apellido, email, extra}
    end
```

---

## S5.2 — GET /persons/{person_id}

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI
    participant DB as PostgreSQL

    C->>N: GET /persons/{person_id}<br/>HTTPS :443
    N->>F: GET /persons/{person_id}<br/>HTTP :8000

    Note over F: Valida formato UUID

    F->>DB: SELECT * FROM persons<br/>WHERE id = {person_id}

    alt Persona no existe
        DB-->>F: 0 rows
        F-->>N: 404 Persona no encontrada
        N-->>C: 404
    else Persona existe
        DB-->>F: 1 row
        F-->>N: 200 OK<br/>{"personId":"uuid","nombre":"Juan",<br/>"apellido":"Pérez","email":"juan@mail.com","extra":{...}}
        N-->>C: 200 OK<br/>{personId, nombre, apellido, email, extra}
    end
```

---

## S5.3 — POST /persons/{person_id}/embeddings

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI
    participant IF as InsightFace (buffalo_l)
    participant DB as PostgreSQL

    C->>N: POST /persons/{person_id}/embeddings<br/>multipart/form-data<br/>images=foto1.jpg, images=foto2.jpg, ...<br/>HTTPS :443
    N->>F: POST /persons/{person_id}/embeddings<br/>HTTP :8000

    Note over F: Valida formato UUID

    F->>DB: SELECT * FROM persons<br/>WHERE id = {person_id}

    alt Persona no existe
        DB-->>F: 0 rows
        F-->>N: 404 Persona no encontrada
        N-->>C: 404
    else Persona existe
        DB-->>F: 1 row

        loop Para cada imagen en images
            F->>IF: get_embedding_from_bytes(image_bytes)
            Note over IF: Decodifica bytes → OpenCV<br/>Detecta rostros con RetinaFace<br/>Extrae embedding ArcFace (512 dims)
            alt Error — 0 o más de 1 rostro / imagen inválida
                IF-->>F: ValueError
                Note over F: rejected_images++<br/>Continúa con la siguiente imagen
            else OK
                IF-->>F: embedding: [float x 512]
                F->>DB: INSERT INTO embeddings<br/>(id, person_id, vector)<br/>vector = pgvector(512)
                Note over F: valid_embeddings++
            end
        end

        F->>DB: COMMIT
        DB-->>F: OK
        F-->>N: 200 OK<br/>{"personId":"uuid",<br/>"processedImages":3,<br/>"validEmbeddings":2,<br/>"rejectedImages":1}
        N-->>C: 200 OK<br/>{personId, processedImages, validEmbeddings, rejectedImages}
    end
```

---

## S5.4 — POST /face-recognition

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as nginx
    participant F as FastAPI
    participant IF as InsightFace (buffalo_l)
    participant DB as PostgreSQL

    C->>N: POST /face-recognition<br/>multipart/form-data<br/>image=persona.jpg, threshold=0.8<br/>HTTPS :443
    N->>F: POST /face-recognition<br/>HTTP :8000

    F->>IF: get_embedding_from_bytes(image_bytes)
    Note over IF: Decodifica bytes → OpenCV<br/>Detecta rostros con RetinaFace<br/>Extrae embedding ArcFace (512 dims)

    alt Error — 0 o más de 1 rostro / imagen inválida
        IF-->>F: ValueError
        F-->>N: 400 Mensaje del error
        N-->>C: 400
    else OK
        IF-->>F: embedding: [float x 512]

        F->>DB: SELECT e.person_id, p.nombre, p.apellido,<br/>e.vector <=> CAST(:emb AS vector(512)) AS distance<br/>FROM embeddings e JOIN persons p ON p.id = e.person_id<br/>ORDER BY distance LIMIT 1

        alt Sin embeddings en BD
            DB-->>F: 0 rows
            F-->>N: 200 OK {"personId":null,"confidence":0.0}
            N-->>C: 200 OK (sin identidad)
        else Resultado encontrado
            DB-->>F: {person_id, nombre, apellido, distance}
            Note over F: confidence = 1.0 - distance

            alt confidence < threshold
                F-->>N: 200 OK {"personId":null,"confidence":valor}
                N-->>C: 200 OK (confianza insuficiente)
            else confidence >= threshold
                F-->>N: 200 OK<br/>{"personId":"uuid",<br/>"nombre":"Juan",<br/>"apellido":"Pérez",<br/>"confidence":0.87}
                N-->>C: 200 OK (match encontrado)
            end
        end
    end
```

---


