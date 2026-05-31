# Diagramas de flujo — Endpoints

---

## GET /health

```mermaid
flowchart TD
    A([Cliente]) --> B[GET /health]
    B --> C[200 OK\n'status: ok']
```

---

## S1 — GET /models

```mermaid
flowchart TD
    A([Cliente]) --> B[GET /models]
    B --> C[Llamada HTTP al\nservicio de inferencia\nGET /infer-service/models]
    C -- ConnectionError --> D[503\nInference service unreachable]
    C -- OK --> E[200\nLista de archivos .pt\ndisponibles en la PC local]
```

---

## S2 — POST /detections

```mermaid
flowchart TD
    A([Cliente]) --> B[POST /detections\nimage + model_id + metadata]

    B --> C{¿content_type\nes imagen?}
    C -- No --> E1[400\nEl archivo debe ser una imagen]

    C -- Sí --> D[Consulta modelos disponibles\nGET /infer-service/models]
    D -- ConnectionError --> E2[503\nInference service unreachable]

    D -- OK --> F{¿model_id existe\nen la lista?}
    F -- No --> E3[400\nModelo no disponible]

    F -- Sí --> G[Parsear metadata como JSON]
    G -- JSONDecodeError --> E4[400\nmetadata debe ser JSON válido]

    G -- OK --> H{¿metadata tiene\nlat y lon?}
    H -- No --> E5[400\nmetadata debe incluir lat y lon]

    H -- Sí --> I[Leer bytes de la imagen]
    I --> J[POST /infer-service/infer\nEnvía imagen + model_id\npor multipart]

    J -- ValueError\nimagen inválida --> E6[400\nImagen inválida]
    J -- ConnectionError --> E7[503\nInference service unreachable]

    J -- OK\nobjetos detectados --> K[Generar frame_id\nuuid.uuid4]

    K --> L[Subir imagen a AWS S3\nKey: frames/frame_id.jpg]
    L -- StorageError --> E8[503\nError al guardar imagen en S3]

    L -- OK --> M[Guardar en base de datos]
    M --> M1[INSERT frames\nid + metadata]
    M1 --> M2[INSERT files\nframe_id + path S3]
    M2 --> M3[INSERT detections\nframe_id + model_id + resultados]

    M3 -- Exception --> N[Rollback BD]
    N --> E9[500\nError al persistir resultados]

    M3 -- OK --> O[COMMIT]
    O --> P[201\nframeId + modelId + detections]
```

---

## S3 — GET /frames/{frameId}

```mermaid
flowchart TD
    A([Cliente]) --> B[GET /frames/frame_id\n?thumbnail=true/false]

    B --> C{¿frame_id es\nUUID válido?}
    C -- No --> E1[422\nFormato UUID inválido]

    C -- Sí --> D[Consulta tabla files\nWHERE frame_id = frame_id]

    D -- No existe --> E2[404\nFrame not found]

    D -- Existe --> E[Obtener path de S3\ndesde tabla files]

    E --> F[Descargar imagen de S3\nusando el path almacenado]

    F --> G{¿thumbnail=true?}

    G -- Sí --> H[Redimensionar con Pillow\nmáx 320×320 px\nmanteniendo proporción]
    H --> I[200\nJPEG binario reducido\nContent-Type: image/jpeg]

    G -- No --> J[200\nJPEG binario original\nContent-Type: image/jpeg]
```

---

## S4 — GET /frames/search

```mermaid
flowchart TD
    A([Cliente]) --> B[GET /frames/search\nlat_min/max + lon_min/max\n+ model_id? + classes? + metadata?]

    B --> C{¿lat_min\n<= lat_max?}
    C -- No --> E1[400\nlat_min debe ser menor o igual a lat_max]

    C -- Sí --> D{¿lon_min\n<= lon_max?}
    D -- No --> E2[400\nlon_min debe ser menor o igual a lon_max]

    D -- Sí --> F{¿metadata\nfue enviado?}

    F -- Sí --> G[Parsear metadata como JSON]
    G -- JSONDecodeError --> E3[400\nmetadata debe ser JSON válido]
    G -- No es objeto --> E4[400\nmetadata debe ser un objeto JSON]
    G -- OK --> H

    F -- No --> H[Construir query sobre tabla frames]

    H --> H1[Filtrar por rango\nlat y lon en JSONB]

    H1 --> I{¿model_id\nfue enviado?}
    I -- Sí --> I1[Agregar filtro EXISTS\nen tabla detections\npor model_id]
    I1 --> J
    I -- No --> J

    J{¿metadata\nparsed tiene campos?}
    J -- Sí --> J1[Agregar filtro por cada\ncampo del JSON\ncoincidencia exacta]
    J1 --> K
    J -- No --> K

    K[Ejecutar query en BD]
    K --> L[Para cada frame obtenido\ncargar sus detections]

    L --> M{¿classes\nfue enviado?}

    M -- Sí --> N[Filtrar en Python:\n¿alguna clase detectada\ncorresponde a la pedida?]
    N -- No matchea --> O[Descartar ese frame]
    N -- Matchea --> P

    M -- No --> P[Incluir frame en resultado]

    O --> Q{¿Hay más frames?}
    P --> Q

    Q -- Sí --> L
    Q -- No --> R[200\nLista de resultados\npuede ser vacía]
```

---


