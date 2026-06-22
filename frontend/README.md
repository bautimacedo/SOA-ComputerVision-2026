# Frontend — SOA 2026

Interfaz grafica del sistema de analisis de fotogramas con deteccion y reconocimiento facial. Cliente desacoplado que consume exclusivamente las APIs REST del backend — no contiene logica de negocio.

## Stack tecnologico

| Tecnologia | Version | Para que |
|---|---|---|
| Vue 3 | 3.x | Framework de UI (Composition API) |
| Vite | 8.x | Bundler y servidor de desarrollo |
| Vue Router | 4.x | Navegacion entre paginas con guards de autenticacion |
| Pinia | 2.x | Store de estado (tokens, sesion del usuario) |
| Bootstrap 5 | 5.x | Estilos y componentes visuales |
| Bootstrap Icons | 1.x | Iconografia |

## Estructura del proyecto

```
frontend/
├── index.html                  Punto de entrada HTML
├── vite.config.js              Config de Vite + proxy al backend
├── package.json
└── src/
    ├── main.js                 Inicializa Vue, Pinia, Router y Bootstrap
    ├── App.vue                 Layout principal (navbar + router-view)
    ├── assets/
    │   └── theme.css           Estilos custom (gradientes, cards, formularios)
    ├── router/
    │   └── index.js            Rutas + guard de autenticacion
    ├── stores/
    │   └── auth.js             Store Pinia — tokens JWT + datos del usuario
    ├── services/
    │   └── api.js              Wrapper de fetch con Bearer token automatico + refresh
    ├── components/
    │   └── Navbar.vue          Barra de navegacion con iconos y logout
    └── views/
        ├── LoginView.vue       Formulario de login (POST /auth/login)
        ├── RegisterView.vue    Formulario de registro (POST /auth/register)
        ├── DetectionView.vue   S1+S2: seleccion de modelo + deteccion YOLO
        ├── SearchView.vue      S4: busqueda de fotogramas con filtros
        ├── PersonsView.vue     S5.1+S5.2+S5.3: gestion de personas y embeddings
        └── RecognitionView.vue S5.4: reconocimiento facial con barra de confianza
```

## Requisitos

- Node.js 18+ y npm

## Instalacion y desarrollo local

```bash
cd frontend
npm install
npm run dev
```

El servidor de desarrollo levanta en `http://localhost:5173`. El proxy de Vite redirige todas las llamadas a `/api/*` al backend (configurable en `vite.config.js`).

### Configurar el backend destino

En `vite.config.js`, cambiar el `target` del proxy segun el entorno:

```js
// Contra la VPS (por defecto)
target: 'https://soagmr.mooo.com'

// Desarrollo local (backend en Docker)
target: 'http://localhost:8000'
```

### Desarrollo local sin Keycloak

Para probar sin autenticacion, se puede levantar el backend local con:

```bash
docker compose -f docker-compose.local.yml up --build -d
```

Esto levanta solo `app` + `db` sin Keycloak. El backend acepta todas las requests sin token cuando `KEYCLOAK_CLIENT_SECRET` esta vacio.

## Build para produccion

```bash
npm run build
```

Genera los archivos estaticos en `dist/`.

## Flujo de autenticacion

El frontend interactua con 3 endpoints de auth (no con Keycloak directamente):

| Accion | Endpoint | Que hace |
|---|---|---|
| Registro | `POST /auth/register` | Crea usuario en Keycloak + persona en BD |
| Login | `POST /auth/login` | Autentica y devuelve `access_token` + `refresh_token` + persona |
| Refresh | `POST /auth/refresh` | Renueva el access token sin pedir contrasena |

### Manejo de tokens

1. Al loguearse, `auth.js` guarda `access_token` y `refresh_token` en `localStorage`.
2. `api.js` agrega `Authorization: Bearer <token>` a cada request automaticamente.
3. Si un endpoint devuelve `401`, `api.js` llama a `/auth/refresh` con el refresh token y reintenta la request.
4. Si el refresh tambien falla, limpia los tokens y redirige al login.

### Guard de rutas

`router/index.js` tiene un `beforeEach` que chequea si el usuario esta logueado antes de permitir el acceso. Las unicas rutas publicas son `/login` y `/register`.

## Diferencia entre Register y Personas

| Vista | Endpoint | Uso |
|---|---|---|
| Register (crear cuenta) | `POST /auth/register` | Crea un usuario que puede loguearse en el sistema |
| Personas (registrar persona) | `POST /persons` | Crea una persona para reconocimiento facial (sin cuenta de login) |

No toda persona registrada para reconocimiento facial necesita una cuenta. Se pueden cargar empleados para que el sistema los reconozca sin darles acceso a la plataforma.

## Paginas

### Login y Registro
Formularios con fondo gradiente. Login llama a `/auth/login`, guarda los tokens y redirige a la home. Registro llama a `/auth/register` y redirige al login (no logea automaticamente).

### Deteccion de objetos (Home)
- Carga los modelos YOLO disponibles desde `GET /models`.
- Formulario: imagen + modelo + latitud/longitud + metadata extra JSON.
- Ejecuta `POST /detections` y muestra los resultados en una tabla con clase, confianza y bounding box.
- Requiere que la PC de inferencia (YOLO) este conectada via Tailscale.

### Busqueda de fotogramas
- Filtros: rango lat/lon (obligatorio), modelo, clases detectadas y metadata JSON (opcionales).
- Llama a `GET /frames/search` y muestra resultados en tabla.
- Boton "Ver" descarga el thumbnail del frame (`GET /frames/{id}?thumbnail=true`) y lo muestra en un modal.

### Gestion de personas
Tres cards:
- **Registrar persona** — `POST /persons` con nombre, apellido, email y extra JSON opcional.
- **Buscar persona** — `GET /persons/{id}` por UUID.
- **Generar embeddings** — `POST /persons/{id}/embeddings` con una o mas fotos. Muestra estadisticas de imagenes procesadas, validas y rechazadas.

### Reconocimiento facial
- Formulario: imagen + threshold (slider 0.0-1.0).
- Llama a `POST /face-recognition`.
- Si reconoce: card verde con nombre, apellido, ID y barra de confianza.
- Si no reconoce: card amarilla explicando que no supero el umbral.
- La barra de progreso cambia de color segun la confianza (verde >= 80%, amarillo >= 50%, rojo < 50%).

## Roles de usuario

El backend define 3 roles gestionados por Keycloak:

| Rol | Permisos | Acceso a Grafana |
|---|---|---|
| `ADMIN` | Todo | Si |
| `OPERATOR` | Todo (default al registrarse) | No |
| `VIEWER` | Solo endpoints GET | No |

El cambio de rol se hace desde la interfaz de Keycloak (no hay endpoint para eso). El frontend no distingue entre roles — la restriccion la aplica el backend.
