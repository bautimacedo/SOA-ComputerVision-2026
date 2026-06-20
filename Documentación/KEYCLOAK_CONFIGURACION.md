# Keycloak — Configuración realizada

Este documento detalla, paso a paso, todo lo que se configuró para incorporar Keycloak al proyecto, y la razón de cada decisión. Para entender los términos usados (realm, client, role, etc.) ver [`KEYCLOAK_CURSO.md`](KEYCLOAK_CURSO.md).

Estado: configuración de Keycloak completa y validada en entorno local (`localhost`). Pendiente: escribir el código de FastAPI que la use (ver [`KEYCLOAK_LOGIN_FLUJO.md`](KEYCLOAK_LOGIN_FLUJO.md)).

---

## 1. Infraestructura — `docker-compose.yml`

Se agregaron dos servicios nuevos:

```yaml
keycloak_db:
  image: postgres:16-alpine
  ...

keycloak:
  image: quay.io/keycloak/keycloak:latest
  command: start-dev
  environment:
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://keycloak_db:5432/${KEYCLOAK_DB_NAME:-keycloak}
    ...
  ports:
    - "8080:8080"
```

**Por qué una base de datos separada (`keycloak_db`) en vez de reusar la `db` existente (la de pgvector):**

- Keycloak crea su propio esquema (decenas de tablas: `USER_ENTITY`, `REALM`, `CLIENT`, `CREDENTIAL`, etc.) que no tiene relación con nuestras tablas de negocio (`persons`, `frames`, `embeddings`).
- Mezclar ambos esquemas en la misma base dificulta backups selectivos y hace más riesgoso un upgrade de Keycloak (sus propias migraciones de schema correrían contra la misma base que usa la app en producción).
- Aislar las credenciales: el usuario de la base de Keycloak no tiene ni puede tener acceso a las tablas de negocio, y viceversa.
- Es la práctica estándar documentada por el propio proyecto Keycloak.

**Por qué `start-dev` y no `start`:** `start-dev` es el modo de desarrollo de Keycloak — no exige HTTPS ni hostname fijo, ideal para probar en `localhost`. Antes de desplegar a la VPS con dominio real, hay que migrar a `start` (modo producción), que exige configurar `KC_HOSTNAME` y TLS explícitamente. Queda pendiente para cuando se defina el dominio final.

**Variables de entorno agregadas a `.env.example`:**

```
KEYCLOAK_DB_USER=keycloak
KEYCLOAK_DB_PASSWORD=keycloak
KEYCLOAK_DB_NAME=keycloak
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=admin
```

Como todavía no existe un `.env` real en el repositorio, Keycloak arrancó usando estos valores como default (sintaxis `${VAR:-default}` en el compose). **Antes de desplegar a la VPS hay que crear un `.env` real con contraseñas fuertes**, no usar estos defaults de ejemplo.

---

## 2. Realm — `soa-realm`

Se creó un realm nuevo en vez de usar `master` (que Keycloak reserva para administrar la instancia misma, no para usuarios de aplicaciones). Todo lo que sigue vive dentro de `soa-realm`.

---

## 3. Client — `soa-client`

Representa a nuestro backend FastAPI ante Keycloak. Configuración aplicada y motivo de cada opción:

| Opción | Valor | Por qué |
|---|---|---|
| Client type | OpenID Connect | Es el protocolo que vamos a usar (no SAML) |
| Client authentication | `On` | Lo convierte en *confidential client* — nuestro backend puede guardar el `client secret` de forma segura en su `.env`, a diferencia de un frontend en el navegador |
| Authorization | `Off` | No necesitamos el módulo de autorización granular (fine-grained) de Keycloak, manejamos roles simples |
| Standard flow | `On` (marcado) | Se deja habilitado para no cerrar la puerta a un login por redirect en el futuro, aunque el plan actual es no usarlo (ver sección de login) |
| Direct access grants | `On` (marcado) | **Es el que vamos a usar realmente**: permite que el backend mande usuario/contraseña directo a Keycloak y reciba el token en la misma respuesta, sin redirects — necesario para tener un formulario de login propio en vez del de Keycloak |
| Implicit flow | `Off` | Flujo obsoleto, no aplica a nuestro caso |
| Service accounts roles | `On` (activado después, ver sección 5) | Necesario para que el backend pueda crear usuarios vía Admin API |

**URLs configuradas (para pruebas en `localhost`):**

```
Root URL:                 http://localhost:8000
Home URL:                 http://localhost:8000/
Valid redirect URIs:      http://localhost:8000/*
Valid post logout URIs:   http://localhost:8000/*
Web origins:              http://localhost:8000
```

Estos valores asumen que FastAPI corre en el puerto 8000 (el mismo que usa el container `app` en el `docker-compose.yml`). **Cuando se despliegue con un dominio real en la VPS, hay que reemplazar estas URLs por las del dominio (`https://tudominio.com/*`)** — mientras tanto no tienen efecto práctico porque no vamos a usar el flujo de redirect (Standard Flow), solo quedaron configuradas por si se necesitan más adelante.

### Client secret

Se generó automáticamente en la pestaña **Credentials** del client. Es el valor que el backend va a usar junto con `client_id` para autenticarse ante Keycloak en cada llamada al endpoint de token.

⚠️ **Nota de seguridad**: el secret generado en esta sesión quedó expuesto en el historial de esta conversación (se pegó en texto plano en el chat). **Hay que regenerarlo desde la consola de Keycloak antes de cualquier uso real / despliegue**, y guardar el nuevo valor únicamente en el `.env` del servidor — nunca en código ni en git.

---

## 4. Roles del realm

Se crearon dos *realm roles*:

- **`ADMIN`**: pensado para acceso administrativo total al sistema.
- **`OPERATOR`**: pensado para el uso normal de la aplicación (cargar fotogramas, consultar, etc.)

### Rol por defecto

Se entró al rol compuesto automático `default-roles-soa-realm` → pestaña **Associated roles** → se agregó `OPERATOR` como rol asociado.

**Efecto**: todo usuario que se cree de ahora en más (manualmente o vía API) recibe el rol `OPERATOR` automáticamente. `ADMIN` **no** se asigna por defecto — queda reservado para asignación manual, evitando que cualquiera que se registre termine con privilegios administrativos.

---

## 5. Service Account del client

Para que el backend pueda crear usuarios en Keycloak (necesario para el registro propio, ver `KEYCLOAK_LOGIN_FLUJO.md`), se activó **Service accounts roles** en `soa-client` (`Settings` → `Capability config`).

Esto generó automáticamente un usuario especial `service-account-soa-client`, visible en la nueva pestaña **Service accounts roles** del client.

Se le asignó el rol de client `manage-users`, perteneciente al client interno `realm-management` (Keycloak expone su propia gestión interna como un client más, con roles granulares como `manage-users`, `manage-clients`, `view-users`, etc.).

**Proceso real seguido** (incluyendo un error y su corrección, documentado para que quede registro): en el primer intento se asignaron por error `create-client` y `manage-clients` (que sirven para gestionar *clients*, no usuarios). Se corrigió:

1. Se asignó el rol correcto: `manage-users` (de `realm-management`).
2. Se removieron (`Unassign`) los roles incorrectos `create-client` y `manage-clients`.

Resultado final, lista de roles del service account:

- `manage-users` (de `realm-management`) — permite crear/editar/eliminar usuarios vía Admin REST API.
- `default-roles-soa-realm` — rol automático, sin efecto relevante para este caso.

Se aplicó **principio de mínimo privilegio**: el service account solo tiene el permiso estrictamente necesario para lo que va a hacer (crear usuarios), no permisos sobre clients, realm completo, etc.

---

## 6. Usuario de prueba

Se creó un usuario manual para validar el flujo de login antes de escribir código:

- **Username**: `marti`
- **Email**: `marti@marti.com`, marcado como `Email verified: On` (se omitió el paso de verificación por mail para simplificar la prueba)
- **Password**: `marti`, con **Temporary: Off** (si se deja en `On`, Keycloak exige cambiar la contraseña en el primer login, lo cual rompe una prueba automatizada por API)

---

## 7. Validación end-to-end (sin tocar FastAPI)

Se probó el flujo de **Direct Access Grant** directamente contra Keycloak, simulando lo que después va a hacer el backend:

```bash
curl -X POST http://localhost:8080/realms/soa-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=soa-client" \
  -d "client_secret=<secret>" \
  -d "username=marti" \
  -d "password=marti"
```

**Resultado**: respuesta `200` con `access_token` + `refresh_token`. Se decodificó el payload del `access_token` (Base64, sin necesidad de la clave — la firma solo se verifica para *validar*, no impide leer el contenido) y se confirmaron los claims relevantes:

```json
{
  "sub": "da3bfca3-4c54-4e67-b530-a7e337313250",
  "iss": "http://localhost:8080/realms/soa-realm",
  "azp": "soa-client",
  "realm_access": {
    "roles": ["default-roles-soa-realm", "OPERATOR", "offline_access", "uma_authorization"]
  },
  "preferred_username": "marti",
  "email": "marti@marti.com"
}
```

Esto confirma:

- El login por Direct Access Grant funciona.
- El rol `OPERATOR` se asignó automáticamente (gracias a la configuración de la sección 4).
- El `sub` (`da3bfca3-...`) es el identificador único que se usará para vincular este usuario de Keycloak con un registro en la tabla `persons` de nuestra base de datos.

---

## 8. Pendientes antes de pasar a producción

- Regenerar el `client secret` (quedó expuesto en el chat de esta sesión).
- Cambiar `start-dev` por `start` en el servicio `keycloak` del compose, configurando `KC_HOSTNAME` y TLS reales.
- Reemplazar las URLs de `localhost:8000` en el client por el dominio real una vez asignado.
- Crear el `.env` real con contraseñas fuertes para `KEYCLOAK_DB_PASSWORD` y `KEYCLOAK_ADMIN_PASSWORD` (no usar los defaults de ejemplo).
- Borrar o deshabilitar el usuario de prueba `marti` antes de ir a producción.
