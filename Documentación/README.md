# SOA 2026 — Sistema de análisis de fotogramas con detección y reconocimiento facial

La consigna completa del trabajo práctico se encuentra en [`Consigna.pdf`](Consigna.pdf).

---

## Descripción

Sistema backend orientado al procesamiento de imágenes mediante modelos de inferencia. Una organización puede capturar imágenes desde distintas fuentes (cámaras fijas, dispositivos móviles, sistemas embebidos), enviarlas al sistema vía API REST, y obtener detecciones de objetos almacenadas junto con metadatos. Adicionalmente, el sistema permite registrar personas, generar representaciones faciales (embeddings) y reconocer individuos en nuevas imágenes.

En esta primera etapa no existe interfaz gráfica. Toda la interacción se realiza mediante clientes genéricos como Postman o curl.

---

## Estado del proyecto

### Fase 1 — Entrega: 9/6/2026

| Servicio | Endpoint | Estado |
|----------|----------|--------|
| S1 — Listado de modelos | `GET /models` | ✅ Implementado |
| S2 — Ejecución de detección | `POST /detections` | ✅ Implementado |
| S3 — Obtención de fotograma | `GET /frames/{id}` | ✅ Implementado |
| S4 — Consulta y filtrado | `GET /frames/search` | ✅ Implementado |
| S5.1 — Gestión de personas | `POST /persons`, `GET /persons/{id}` | ✅ Implementado |
| S5.2 — Generación de embeddings | `POST /persons/{id}/embeddings` | ✅ Implementado |
| S5.3 — Reconocimiento facial | `POST /face-recognition` | ✅ Implementado |

### Fase 2 — Pendiente

- Interfaz gráfica (frontend)
- Autenticación y autorización con Keycloak (OAuth2 / JWT)
- Autenticación biométrica opcional (login por reconocimiento facial)
- Monitoreo con Telegraf + Grafana + InfluxDB

---

## Despliegue

### Requisitos previos

- Git
- Docker y Docker Compose
- Cuenta de AWS con acceso a S3
- Cuenta de Tailscale (para conectar el servicio de inferencia)

### VPS — servidor principal

```bash
# 1. Clonar el repositorio
git clone https://github.com/bautimacedo/SOA-ComputerVision-2026
cd SOA-ComputerVision-2026

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con las credenciales reales de AWS y la IP Tailscale de la PC local

# 3. Instalar Tailscale en el HOST del servidor (no dentro de Docker)
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up

# 4. Crear el bucket S3 y configurar variables en .env

# 5. Obtener certificado SSL (solo la primera vez)
sudo apt install certbot
sudo certbot certonly --standalone -d dominio

# 6. Levantar los contenedores
docker compose up -d

# 7. Verificar que todo levantó
curl https://soagmr.mooo.com/health
```

Para actualizar el sistema después de cambios en el código:

```bash
git pull
docker compose up --build -d
```

### PC local — servicio de inferencia

La inferencia con YOLO corre en la PC local porque tiene GPU. El servidor delega este procesamiento a través de la red privada de Tailscale.

```bash
# 1. Instalar Tailscale en la PC local
# Linux:
curl -fsSL https://tailscale.com/install.sh | sh && tailscale up
# Windows/Mac: instalar el cliente de escritorio desde tailscale.com

# 2. Clonar el repositorio (o hacer git pull si ya lo tenés)
git clone https://github.com/bautimacedo/SOA-ComputerVision-2026
cd SOA-ComputerVision-2026/inference_service

# 3. Instalar Python 3.11 recomendado ya que versiones posteriores tuvimos problemas.
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv

# 4. Crear entorno virtual e instalar dependencias
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# requirements.txt incluye --extra-index-url para PyTorch con CUDA para ejecutar las inferencias con GPU nvidia.

# 5. Poner los modelos .pt en inference_service/models/
# (se pueden agregar como symlinks a donde ya estén descargados, es nuestro caso) POR EJEMPLO:
ln -s /ruta/al/modelo/yolo11n.pt models/yolo11n.pt

# 6. Levantar el servicio
uvicorn main:app --host 0.0.0.0 --port 8001

# 7. Verificar
curl http://localhost:8001/health
curl http://localhost:8001/models
```

Finalmente, en el `.env` del servidor poner la IP Tailscale de la PC local ==> Todo se configura desde la web (recomendado):

```
INFERENCE_SERVICE_URL=http://100.x.x.x:8001
```

---

## Ejemplos de uso (curl)

Todos los ejemplos usan el dominio de producción. 

### S1 — Listar modelos disponibles

```bash
curl https://soagmr.mooo.com/models
# ["yolo26n.pt","yolo26x.pt"]
```

### S2 — Enviar fotograma y ejecutar detección

El campo `metadata` es un JSON libre. Los únicos campos obligatorios son `lat` y `lon`.
Todo lo demás es opcional y se almacena tal cual en la base de datos — se puede incluir
cualquier atributo relevante para el caso de uso:

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `lat` | Sí | Latitud de donde se capturó la imagen |
| `lon` | Sí | Longitud de donde se capturó la imagen |
| `camara` | No | Identificador de la cámara |
| `piso` | No | Piso o nivel del edificio |
| `zona` | No | Zona o sector |
| `fecha` | No | Fecha/hora de captura |
| `resolucion` | No | Resolución del dispositivo |
| `...` | No | Cualquier otro campo adicional |

```bash
# Mínimo requerido
curl -X POST https://soagmr.mooo.com/detections \
  -F "image=@foto.jpg" \
  -F "model_id=yolo11n.pt" \
  -F 'metadata={"lat":-34.6037,"lon":-58.3816}'

# Con campos adicionales
curl -X POST https://soagmr.mooo.com/detections \
  -F "image=@foto.jpg" \
  -F "model_id=yolo11n.pt" \
  -F 'metadata={"lat":-34.6037,"lon":-58.3816,"camara":"cam_01","piso":3,"zona":"acceso_norte"}'

# {
#   "frameId": "550e8400-e29b-41d4-a716-446655440000",
#   "modelId": "yolo11n.pt",
#   "detections": [
#     {"class": "person", "confidence": 0.91, "bbox": [0.0531, 0.0937, 0.3375, 0.6833]},
#     {"class": "zebra",  "confidence": 0.87, "bbox": [0.0, 0.0250, 0.7500, 0.7500]}
#   ]
# }
```

### S3 — Recuperar imagen por ID

```bash
# Imagen original
curl -o imagen.jpg https://soagmr.mooo.com/frames/550e8400-e29b-41d4-a716-446655440000

# Thumbnail (máx 320x320)
curl -o thumb.jpg "https://soagmr.mooo.com/frames/550e8400-e29b-41d4-a716-446655440000?thumbnail=true"
```

### S4 — Buscar fotogramas por ubicación, modelo, clase y metadatos

Todos los filtros se aplican en conjunto (AND): solo se retornan fotogramas que cumplan todos los filtros activos.

**Parámetros:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `lat_min` | float | Sí | Latitud mínima |
| `lat_max` | float | Sí | Latitud máxima |
| `lon_min` | float | Sí | Longitud mínima |
| `lon_max` | float | Sí | Longitud máxima |
| `model_id` | string | No | Modelo YOLO usado. Ej: `best.pt`, `yolo11n.pt` |
| `classes` | string (repetible) | No | Clases detectadas. Al menos una debe estar presente |
| `metadata` | JSON string | No | Campos del fotograma. Coincidencia exacta. Si el campo no existe en un fotograma, ese fotograma no aparece |

**Comportamiento del filtro de metadatos:**
- Coincidencia exacta de valor.
- Se pueden combinar múltiples campos en el mismo JSON (todos deben coincidir).
- Si ningún fotograma tiene el campo indicado, devuelve lista vacía — no es un error.

```bash
# Solo por coordenadas
curl "https://soagmr.mooo.com/frames/search?lat_min=-35&lat_max=-34&lon_min=-59&lon_max=-58"

# Filtrando por modelo
curl "https://soagmr.mooo.com/frames/search?lat_min=-35&lat_max=-34&lon_min=-59&lon_max=-58&model_id=best.pt"

# Filtrando por clase detectada
curl "https://soagmr.mooo.com/frames/search?lat_min=-35&lat_max=-34&lon_min=-59&lon_max=-58&classes=person"

# Múltiples clases (retorna frames que tengan al menos una)
curl "https://soagmr.mooo.com/frames/search?lat_min=-35&lat_max=-34&lon_min=-59&lon_max=-58&classes=person&classes=zebra"

# Filtrando por metadato (solo fotogramas de la cámara cam_01)
curl "https://soagmr.mooo.com/frames/search?lat_min=-35&lat_max=-34&lon_min=-59&lon_max=-58&metadata=%7B%22camara%22%3A%22cam_01%22%7D"

# Múltiples campos de metadatos
curl "https://soagmr.mooo.com/frames/search?lat_min=-35&lat_max=-34&lon_min=-59&lon_max=-58&metadata=%7B%22camara%22%3A%22cam_01%22%2C%22piso%22%3A3%7D"

# Todo combinado: coordenadas + modelo + clase + metadato
curl "https://soagmr.mooo.com/frames/search?lat_min=-35&lat_max=-34&lon_min=-59&lon_max=-58&model_id=best.pt&classes=person&metadata=%7B%22zona%22%3A%22acceso_norte%22%7D"
```

> Los valores de `metadata` están URL-encoded en curl. `{"camara":"cam_01"}` → `%7B%22camara%22%3A%22cam_01%22%7D`.
> Desde Postman o el Swagger en `/docs` se puede escribir el JSON directamente sin encodear.

## S5.1 — Gestión de personas

Esta parte permite registrar personas dentro del sistema para luego poder reconocerlas en imágenes nuevas.

El endpoint principal es:

```http
POST /persons
```

Con este servicio se cargan los datos básicos de una persona, como nombre, apellido, email y un campo extra opcional para guardar información adicional.

Ejemplo de uso:

```bash
BASE_URL="https://soagmr.mooo.com"

curl -k -X POST "$BASE_URL/persons" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Persona",
    "apellido": "Prueba",
    "email": "persona.prueba.prod@test.com",
    "extra": {
      "rol": "test_s5_prod"
    }
  }'
```

Ejemplo de respuesta:

```json
{
  "id": "ba2d51e1-f412-488f-a650-06a9aaed625e",
  "nombre": "Persona",
  "apellido": "Prueba",
  "email": "persona.prueba.prod@test.com",
  "extra": {
    "rol": "test_s5_prod"
  }
}
```

Cuando se recibe esta información, el backend verifica si ya existe una persona con ese email. Si no existe, crea el registro en la tabla `persons` de PostgreSQL.

También se implementó el endpoint:

```http
GET /persons/{person_id}
```

Este permite consultar los datos de una persona a partir de su identificador único.

```bash
BASE_URL="https://soagmr.mooo.com"
PERSON_ID="ba2d51e1-f412-488f-a650-06a9aaed625e"

curl -k "$BASE_URL/persons/$PERSON_ID"
```
Ejemplo de respuesta:
```json
{
  "id": "ba2d51e1-f412-488f-a650-06a9aaed625e",
  "nombre": "Persona",
  "apellido": "Prueba",
  "email": "persona.prueba.prod@test.com",
  "extra": {
    "rol": "test_s5_prod"
  }
}
```
En resumen, S5.1 se encarga de mantener el registro de personas que después podrán tener imágenes asociadas para reconocimiento facial.

---

## S5.2 — Generación de embeddings faciales

Esta parte permite asociar imágenes a una persona registrada y generar sus embeddings faciales.

El endpoint es:

```http
POST /persons/{person_id}/embeddings
```

Este servicio recibe una o más imágenes como `multipart/form-data`. Cada imagen se procesa con InsightFace para detectar el rostro y generar un embedding.

Un embedding es una representación matemática del rostro. En vez de guardar o comparar la imagen pixel por pixel, el modelo transforma la cara en un vector de 512 números. Ese vector resume características del rostro y permite comparar caras entre sí.

El flujo interno es:

1. Se recibe el `person_id`.
2. Se verifica que la persona exista en la base de datos.
3. Se recorren las imágenes recibidas.
4. Se lee cada imagen con OpenCV directamente desde los bytes del archivo.
5. Se procesa con InsightFace.
6. Si se detecta exactamente un rostro, se genera el embedding.
7. El embedding se guarda en la tabla `embeddings` asociado a la persona.
8. Si una imagen no se puede leer, no tiene rostro o tiene más de un rostro, se cuenta como rechazada.

```bash
BASE_URL=”https://soagmr.mooo.com”
PERSON_ID=”ba2d51e1-f412-488f-a650-06a9aaed625e”

# Una imagen
curl -k -X POST “$BASE_URL/persons/$PERSON_ID/embeddings” \
  -F “images=@foto1.jpg”

# Varias imágenes en la misma request
curl -k -X POST “$BASE_URL/persons/$PERSON_ID/embeddings” \
  -F “images=@foto1.jpg” \
  -F “images=@foto2.jpg” \
  -F “images=@foto3.jpg”
```

Ejemplo de respuesta:
```json
{
  “personId”: “ba2d51e1-f412-488f-a650-06a9aaed625e”,
  “processedImages”: 3,
  “validEmbeddings”: 2,
  “rejectedImages”: 1
}
```

Para guardar los embeddings se usa PostgreSQL con la extensión `pgvector`. Esto permite almacenar vectores de 512 dimensiones y luego buscar similitudes directamente desde la base de datos.

En resumen, S5.2 toma fotos de una persona y genera la “huella matemática” de su rostro para que después pueda ser reconocida.

---

## S5.3 — Reconocimiento facial

Esta parte permite identificar si una persona aparece en una imagen nueva.

El endpoint es:

```http
POST /face-recognition
```

Este servicio recibe una imagen como `multipart/form-data` y un `threshold` opcional (campo de formulario), que representa el nivel mínimo de confianza requerido para aceptar un reconocimiento.

El flujo interno es:

1. Se recibe la imagen como archivo.
2. Se lee con OpenCV directamente desde los bytes del archivo.
3. InsightFace detecta el rostro y genera un embedding de 512 dimensiones.
4. Ese embedding se compara contra todos los embeddings guardados en la base de datos.
5. La comparación se hace con `pgvector`, usando distancia coseno.
6. Se selecciona el embedding más parecido.
7. Se calcula una confianza aproximada con `confidence = 1 - distance`.
8. Si la confianza supera el `threshold`, se devuelve la persona reconocida.
9. Si no supera el umbral, se devuelve que no se reconoció ninguna persona.

Consulta principal usada para buscar el embedding más parecido:

```sql
SELECT
    e.id AS embedding_id,
    e.person_id,
    p.nombre,
    p.apellido,
    p.email,
    e.vector <=> CAST(:embedding AS vector(512)) AS distance
FROM embeddings e
JOIN persons p ON p.id = e.person_id
ORDER BY e.vector <=> CAST(:embedding AS vector(512))
LIMIT 1;
```

El operador `<=>` de pgvector calcula distancia coseno. Cuanto menor es la distancia, más parecidos son los rostros.

```bash
BASE_URL="https://soagmr.mooo.com"

# Con threshold por defecto (0.8)
curl -k -X POST "$BASE_URL/face-recognition" \
  -F "image=@persona.jpg"

# Con threshold personalizado
curl -k -X POST "$BASE_URL/face-recognition" \
  -F "image=@persona.jpg" \
  -F "threshold=0.75"
```

Ejemplo de respuesta si reconoce a la persona:

```json
{
  "personId": "ba2d51e1-f412-488f-a650-06a9aaed625e",
  "nombre": "Persona",
  "apellido": "Prueba",
  "confidence": 1.0
}
```
Ejemplo de respuesta si no supera el umbral de reconocimiento:
```json
{
  "personId": null,
  "nombre": null,
  "apellido": null,
  "confidence": 0.45
}
```
En resumen, S5.3 toma una imagen nueva, genera la huella matemática del rostro y la compara contra las huellas guardadas para decidir si corresponde a alguna persona registrada.

> Se recomienda usar imágenes JPG o PNG reales. Si una imagen tiene extensión `.jpg` pero internamente es AVIF u otro formato no compatible con OpenCV dentro del contenedor, puede fallar la lectura.

---

## Arquitectura

Los diagramas de base de datos y arquitectura se encuentran en los archivos PNG del repositorio.

### Visión general

El sistema está dividido en dos partes que se comunican entre sí:

- **VPS (servidor remoto):** corre la API REST, la base de datos y el proxy. Todo dentro de Docker.
- **PC local:** corre el servicio de inferencia YOLO, aprovechando la GPU local. Se comunica con el servidor a través de Tailscale.

```
Cliente (Postman / curl)
        │ HTTPS
        ▼
      nginx  ← proxy reverso, SSL, enruta por dominio
        │
        ▼
    FastAPI  ← lógica de negocio, validación, persistencia
      │    │
      │    │ Tailscale (red privada cifrada)
      │    ▼
      │  PC local — YOLO inference (GPU)
      │
      ├── PostgreSQL + pgvector  ← metadatos, detecciones, personas, embeddings
      │
      └── AWS S3  ← almacenamiento de imágenes
```

### Por qué FastAPI y no Flask

Flask es un microframework minimalista que fue diseñado en una época donde las APIs REST no eran el caso de uso principal de Python. FastAPI fue diseñado específicamente para construir APIs:

- **Validación automática:** usa Pydantic. Si el cliente manda un JSON mal formado o le falta un campo, FastAPI rechaza el request automáticamente sin escribir código de validación.
- **Documentación automática:** genera un Swagger UI en `/docs` y un ReDoc en `/redoc` sin configuración adicional.
- **Tipado:** al declarar los tipos de los parámetros y respuestas, el código es más claro.
- **Rendimiento:** FastAPI usa ASGI (asíncrono) mientras Flask usa WSGI (sincrónico). Para operaciones que esperan respuestas de red (base de datos, S3, servicio de inferencia), la diferencia es significativa.

FastAPI no es un servidor web por sí solo — necesita un servidor ASGI para correr. Usamos **Uvicorn**, que es el servidor ASGI de referencia para Python. Uvicorn es el que escucha en el puerto 8000, acepta las conexiones HTTP y las pasa a FastAPI para que las procese. En el `Dockerfile` se ve claramente:

```
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

La relación es: **nginx** recibe la request en el puerto 80/443 → la pasa a **Uvicorn** en el puerto 8000 → Uvicorn se la entrega a **FastAPI** para ejecutar la lógica.

### Estructura de carpetas

```
SOA-ComputerVision-2026/
│
├── app/                    # Código del servidor principal
│   ├── main.py             # Punto de entrada: registra controllers, crea tablas
│   ├── config.py           # Variables de entorno centralizadas (pydantic-settings)
│   ├── database.py         # Conexión SQLAlchemy y función get_db()
│   │
│   ├── entities/           # Clases de dominio — tablas de la base de datos (SQLAlchemy @Entity)
│   │                       # Cada archivo = una tabla. No contienen lógica.
│   │
│   ├── dtos/               # Objetos de transferencia de datos (Pydantic)
│   │                       # Validan lo que entra y serializan lo que sale de la API.
│   │
│   ├── controllers/        # Endpoints HTTP agrupados por servicio (@RestController)
│   │                       # Reciben el request, delegan en repositories y business, devuelven response.
│   │
│   ├── repositories/       # Acceso a datos — queries a PostgreSQL (@Repository)
│   │                       # Cada clase encapsula las operaciones de BD de una entidad.
│   │
│   └── business/           # Lógica de negocio y clientes externos (@Service)
│       ├── yolo.py                 # Cliente HTTP al servicio de inferencia remoto
│       ├── storage.py              # Upload/download de imágenes en AWS S3
│       └── insightface_service.py  # Detección facial y generación de embeddings con InsightFace
│
├── inference_service/      # Servicio de inferencia YOLO — corre en la PC local
│   ├── main.py             # FastAPI con GET /models y POST /infer
│   ├── config.py           # Configuración local (directorio de modelos)
│   ├── services/
│   │   └── yolo.py         # Lógica real de inferencia con ultralytics
│   ├── models/             # Archivos .pt (ignorados por git)
│   └── requirements.txt    # Dependencias incluyendo PyTorch con CUDA
│
├── db/
│   └── init.sql            # Activa la extensión pgvector al iniciar la BD
│
├── nginx/
│   └── nginx.conf          # Reverse proxy, SSL, ruteo a FastAPI y Adminer
│
├── scripts/
│   ├── setup_aws.sh        # Crea el bucket S3 (correr una sola vez)
│   └── test_api.sh         # Prueba el flujo completo S1→S4 con curl
│
├── Dockerfile              # Imagen del servidor (python:3.11-slim)
├── docker-compose.yml      # Define los 4 contenedores del sistema
├── requirements.txt        # Dependencias del servidor
└── .env.example            # Plantilla de configuración
```

La separación en capas no es arbitraria. Cada una tiene una responsabilidad única:

- `entities/` solo describe cómo se guardan los datos en PostgreSQL (equivalente a `@Entity` en Spring).
- `dtos/` solo describe cómo se ven los datos en la API — qué entra y qué sale (equivalente a los DTOs en Spring).
- `repositories/` encapsula todas las queries a la base de datos (equivalente a `@Repository` / JPA en Spring).
- `business/` contiene la lógica de negocio y los clientes a servicios externos (equivalente a `@Service` en Spring).
- `controllers/` recibe el request HTTP, delega en `repositories` y `business`, y devuelve la response (equivalente a `@RestController` en Spring).

Esto hace que un cambio en la BD no rompa la API y viceversa, y que la lógica de acceso a datos quede centralizada en los repositories.

### Base de datos — PostgreSQL con pgvector

Se eligió PostgreSQL porque:

- Soporta **JSONB**, un tipo de dato que permite guardar JSON directamente en una columna y consultarlo con filtros eficientes. Esto es fundamental para los metadatos de los fotogramas, que son variables (cada cámara puede mandar campos distintos).
- Tiene la extensión **pgvector**, que agrega un tipo de dato `vector(N)` y operaciones de similitud (distancia coseno, distancia L2). Esto permite almacenar los embeddings faciales de 512 dimensiones y hacer búsquedas de similitud directamente en SQL, sin necesidad de una base de datos vectorial separada como Pinecone o Milvus.
- Soportado por SQLAlchemy y ampliamente usado en producción.

La imagen Docker usada es `pgvector/pgvector:pg16`, que es PostgreSQL 16 con la extensión pgvector ya incluida.

Las tablas se crean automáticamente al arrancar el servidor mediante `Base.metadata.create_all()` de SQLAlchemy. El único script SQL que existe (`db/init.sql`) activa la extensión:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Tablas de la base de datos

**`frames`** — representa el evento de llegada de una imagen al sistema. Guarda los metadatos asociados (latitud, longitud, y cualquier dato adicional en formato JSON libre). No guarda nada relacionado con dónde está guardada la imagen ni qué modelo se usó — eso es responsabilidad de otras tablas.

**`detections`** — guarda los resultados de la inferencia YOLO sobre un fotograma. Está vinculada a `frames` por `frame_id`. Guarda qué modelo se usó y los objetos detectados en formato JSON (`{"objects": [{class, confidence, bbox}]}`).

**`files`** — representa la relación entre un fotograma y su archivo en AWS S3. Guarda el `path` (la key dentro del bucket) que permite recuperar la imagen. Está separada de `frames` para mantener el concepto del fotograma independiente de dónde se almacena físicamente.

**`persons`** — registra personas en el sistema para el reconocimiento facial. Tiene nombre, apellido, email (único) y un campo `extra` JSONB para atributos adicionales opcionales.

**`embeddings`** — guarda las representaciones faciales de cada persona. Un embedding es un vector de 512 números generado por InsightFace que codifica las características del rostro. Una persona puede tener múltiples embeddings (una por imagen cargada). Cuando llega una imagen nueva para reconocer, se genera su embedding y se compara contra todos los almacenados usando pgvector.

### Tailscale — red privada para la inferencia

El servidor VPS tiene poca capacidad de cómputo y no puede correr YOLO con tiempos aceptables. La PC local tiene una GPU (RTX 3070 Ti) que puede hacer inferencia rápidamente. El problema es que la PC local está detrás de un router doméstico con NAT — no tiene una IP pública accesible desde internet.

**Tailscale** resuelve esto. Es una VPN mesh basada en WireGuard que conecta dispositivos entre sí a través de una red privada cifrada, sin necesidad de abrir puertos en el router ni configurar servidores intermediarios. Cada dispositivo que se une a la red recibe una IP que es accesible desde cualquier otro dispositivo de la misma cuenta, sin importar en qué red física esté cada uno.

Tailscale se instala en el **host del servidor** (no dentro de Docker). Instalado en el host, crea una interfaz de red `tailscale0` que los contenedores Docker pueden alcanzar sin configuración adicional.

El servidor manda las imágenes al servicio de inferencia en la PC local usando requests HTTP normales contra la IP Tailscale con multipart/form-data. La PC recibe la imagen, corre YOLO en la GPU, y devuelve los resultados como JSON. El servidor persiste todo y responde al cliente original.

### Contenedores Docker

El sistema corre con cuatro contenedores definidos en `docker-compose.yml`, todos en la misma red interna `soa_net`:

| Contenedor | Imagen | Puerto interno | Puerto externo | Rol |
|------------|--------|---------------|----------------|-----|
| `soa_app` | build local | 8000 | — | API FastAPI |
| `soa_db` | pgvector/pgvector:pg16 | 5432 | — | Base de datos |
| `soa_nginx` | nginx:alpine | 80, 443 | 80, 443 | Proxy reverso y SSL |
| `soa_adminer` | adminer | 8080 | — | Admin de BD vía web |

Ningún contenedor excepto nginx está expuesto al exterior. La comunicación entre contenedores ocurre por nombre de servicio dentro de `soa_net`.

### SSL y dominio

nginx maneja el SSL con certificados de Let's Encrypt. Todo el tráfico HTTP en el puerto 80 es redirigido automáticamente a HTTPS en el 443. Los certificados están montados desde el host (`/etc/letsencrypt`) al contenedor nginx como volumen de solo lectura.

### Almacenamiento de imágenes — AWS S3

Las imágenes no se guardan en el servidor. Cuando llega un fotograma, se sube a un bucket de S3 con la key `frames/{frameId}.jpg`. La ruta se guarda en la tabla `files`. Cuando un cliente pide una imagen, el servidor la descarga de S3 en memoria y la devuelve como binario puro en el body del response HTTP (`Content-Type: image/jpeg`), con el tamaño total indicado en `Content-Length`.

Esto desacopla el almacenamiento del servidor: el disco del VPS no crece con cada imagen subida, y S3 garantiza durabilidad y disponibilidad sin gestión de infraestructura.

---

## API — descripción de endpoints

| Método | Endpoint | Servicio | Descripción |
|--------|----------|----------|-------------|
| `GET` | `/health` | — | Estado del servidor |
| `GET` | `/models` | S1 | Lista los modelos YOLO disponibles en la PC local |
| `POST` | `/detections` | S2 | Recibe imagen + metadatos, corre YOLO, persiste y devuelve detecciones |
| `GET` | `/frames/{frameId}` | S3 | Devuelve la imagen original asociada al ID |
| `GET` | `/frames/{frameId}?thumbnail=true` | S3 | Devuelve versión reducida (máx 320×320) |
| `GET` | `/frames/search` | S4 | Filtra fotogramas por rango lat/lon y clases detectadas |
| `POST` | `/persons` | S5.1 | Registra una nueva persona |
| `GET` | `/persons/{personId}` | S5.1 | Obtiene datos de una persona |
| `POST` | `/persons/{personId}/embeddings` | S5.2 | Genera y guarda embeddings faciales a partir de imágenes |
| `POST` | `/face-recognition` | S5.3 | Identifica una persona en una imagen por similitud de embeddings |

### Parámetros de S4

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `lat_min` | float | Sí | Latitud mínima del rango |
| `lat_max` | float | Sí | Latitud máxima del rango |
| `lon_min` | float | Sí | Longitud mínima del rango |
| `lon_max` | float | Sí | Longitud máxima del rango |
| `classes` | string (repetible) | No | Clases a filtrar (ej: `&classes=person&classes=car`) |

La documentación interactiva completa está disponible en `https://soagmr.mooo.com/docs`.
