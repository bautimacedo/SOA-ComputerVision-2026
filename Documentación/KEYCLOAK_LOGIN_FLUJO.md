# Login con Keycloak — Diseño del flujo (pendiente de implementación)

Este documento describe **cómo va a funcionar** el login personalizado del sistema, usando Keycloak como backend de identidad pero con pantallas y endpoints propios (no la UI default de Keycloak). Es un documento de diseño: **nada de esto está implementado en código todavía** — primero se completó y validó la configuración de Keycloak (ver [`KEYCLOAK_CONFIGURACION.md`](KEYCLOAK_CONFIGURACION.md)).

Para entender los términos usados (realm, client, JWT, claims, grant types, etc.), ver [`KEYCLOAK_CURSO.md`](KEYCLOAK_CURSO.md). Este documento no vuelve a explicar esos conceptos, los da por leídos.

---

## 1. Decisión de diseño: por qué Direct Access Grant

Existían dos caminos posibles:

- **(A) Direct Access Grant**: formulario de login propio, que manda usuario/contraseña a *nuestro* backend, y el backend reenvía esas credenciales a Keycloak.
- **(B) Authorization Code Flow con tema personalizado**: seguir usando el flujo estándar (redirect a Keycloak), pero "vistiendo" la pantalla de login de Keycloak con un tema custom (HTML/CSS propio) para que no se note que es Keycloak.

Se eligió **(A)**, porque el requerimiento explícito fue no usar la interfaz de Keycloak en absoluto, ni siquiera personalizada. La contrapartida de esta elección (documentada para no perderla de vista): el MFA nativo de Keycloak (TOTP) no se obtiene gratis con este flujo — si se quiere agregar más adelante, hay que implementarlo como un paso extra propio.

---

## 2. Cambio necesario en la base de datos

La tabla `persons` (entidad existente del sistema, usada hoy para el reconocimiento facial) necesita una columna nueva:

```sql
ALTER TABLE persons ADD COLUMN keycloak_id UUID UNIQUE;
```

**Qué guarda esta columna**: el `sub` (subject) que Keycloak le asigna a cada usuario — es un UUID único que Keycloak genera al crear el usuario y que viaja como claim dentro de todo JWT que ese usuario obtenga después. Es el "puente" entre la identidad gestionada por Keycloak y el registro de negocio que ya tenemos en nuestra base.

**Por qué `UNIQUE` y no `PRIMARY KEY` ni reemplaza al `id` existente de `persons`**: `persons.id` sigue siendo el identificador interno de nuestro sistema (usado en `embeddings`, etc.); `keycloak_id` es simplemente una referencia externa a la identidad en Keycloak, no reemplaza nuestro modelo de datos.

**Nullable o no**: se deja nullable, porque pueden existir personas en el sistema (cargadas para reconocimiento facial) que nunca tengan una cuenta de login — son dos cosas distintas: "estar en el sistema de reconocimiento" no implica "tener acceso a la API".

---

## 3. Endpoints nuevos a construir

Todos viven en el backend FastAPI (no en Keycloak):

| Endpoint | Función |
|---|---|
| `POST /auth/register` | Crea un usuario nuevo: en Keycloak y en `persons` |
| `POST /auth/login` | Autentica contra Keycloak y devuelve los tokens |
| `POST /auth/refresh` | Renueva el access token usando el refresh token, sin pedir contraseña de nuevo |

Además, una **dependency** reutilizable (no es un endpoint, es una función que otros endpoints van a usar vía `Depends`):

| Dependency | Función |
|---|---|
| `get_current_user` | Valida el JWT recibido en cada request protegida y extrae los datos del usuario |
| `require_role("ADMIN")` | Sobre la anterior, además verifica que el usuario tenga el rol indicado, sino devuelve 403 |

---

## 4. Flujo de registro — paso a paso

Disparado por: `POST /auth/register` con body `{ nombre, apellido, email, password }`.

1. El usuario completa el formulario propio (frontend, fuera del alcance de este documento) y lo manda a nuestro backend.
2. **Validación local primero**: el backend chequea contra la tabla `persons` si ya existe una persona con ese `email` (igual que hace hoy `S5.1 — Registrar persona`). Si existe, se corta ahí con `409 Conflict` — no tiene sentido llamar a Keycloak si ya sabemos que va a fallar por nuestro lado.
3. **Obtener un token de servicio**: el backend pide un token usando el **Client Credentials Grant** (el `client_id` + `client_secret` de `soa-client`, sin usuario humano involucrado):
   ```
   POST /realms/soa-realm/protocol/openid-connect/token
   grant_type=client_credentials&client_id=soa-client&client_secret=<secret>
   ```
   Keycloak responde con un access token que representa "soy la aplicación soa-client", con el permiso `manage-users` que le asignamos al service account (ver `KEYCLOAK_CONFIGURACION.md`, sección 5).
4. **Crear el usuario en Keycloak**: con ese token de servicio, el backend llama a la Admin REST API:
   ```
   POST /admin/realms/soa-realm/users
   Authorization: Bearer <token de servicio>
   { "username": email, "email": email, "enabled": true,
     "credentials": [{ "type": "password", "value": password, "temporary": false }] }
   ```
   Keycloak crea el usuario, le asigna automáticamente el rol `OPERATOR` (por el `default-roles-soa-realm` configurado), y devuelve en la respuesta (header `Location`) la URL del usuario creado, de la cual se extrae su `id` (el UUID que será el `keycloak_id`).
5. **Crear el registro de negocio**: el backend hace `INSERT INTO persons (nombre, apellido, email, keycloak_id) VALUES (...)`, usando el UUID obtenido en el paso anterior.
6. **Manejo de fallos (consideración de diseño, sin transacción distribuida real)**: si el paso 5 falla (ej. error de base de datos) después de que el paso 4 ya creó el usuario en Keycloak, queda un usuario "huérfano" en Keycloak sin contraparte en `persons`. Como los dos sistemas son independientes, no hay una transacción que abarque a ambos. La compensación a implementar: si falla el insert local, el backend debe llamar a `DELETE /admin/realms/soa-realm/users/{id}` para revertir la creación en Keycloak antes de devolver el error al cliente.
7. Se devuelve `201 Created` con los datos de la persona registrada (sin incluir tokens — el registro no implica loguearse automáticamente, en este diseño el usuario debe luego loguearse por separado en el paso siguiente; esto se puede revisar si se prefiere loguear automáticamente tras registrar).

---

## 5. Flujo de login — paso a paso

Disparado por: `POST /auth/login` con body `{ email, password }`.

1. El backend recibe las credenciales del formulario propio.
2. El backend hace la llamada de **Direct Access Grant** a Keycloak, reenviando esas credenciales:
   ```
   POST /realms/soa-realm/protocol/openid-connect/token
   grant_type=password&client_id=soa-client&client_secret=<secret>&username=<email>&password=<password>
   ```
3. **Si Keycloak responde 400/401** (`invalid_grant`, credenciales incorrectas): el backend traduce eso a un `401 Unauthorized` propio hacia el cliente, sin revelar detalles internos de Keycloak.
4. **Si Keycloak responde 200**: el backend recibe `access_token` + `refresh_token`.
5. El backend decodifica el `access_token` (sin necesidad de verificar la firma en este punto, ya que confiamos en la respuesta directa de Keycloak en una llamada que nosotros mismos iniciamos) para extraer el claim `sub`.
6. El backend busca en `persons` el registro con `keycloak_id = sub`, para tener a mano los datos de negocio asociados (nombre, si tiene embeddings cargados, etc.) — útil para devolver un perfil completo al frontend en la misma respuesta del login.
7. Se devuelve al cliente: `{ access_token, refresh_token, expires_in, person: {...} }`.
8. El frontend guarda esos tokens (en memoria, o en un storage seguro) y a partir de ahora los manda en el header `Authorization: Bearer <access_token>` en cada request a endpoints protegidos.

---

## 6. Flujo de una request a un endpoint protegido — paso a paso

Ejemplo: el frontend llama a un endpoint cualquiera de nuestra API que requiere estar logueado (a definir cuáles — hoy ninguno lo exige, esto se agrega cuando se proteja cada endpoint con la dependency).

1. La request llega a FastAPI con header `Authorization: Bearer <access_token>`.
2. El endpoint tiene como parámetro `current_user: dict = Depends(get_current_user)`. Antes de ejecutar el código del endpoint, FastAPI ejecuta esa dependency.
3. Dentro de `get_current_user`:
   a. Se extrae el token del header (si no viene, `401`).
   b. Se obtienen las claves públicas de Keycloak desde el endpoint JWKS (`/realms/soa-realm/protocol/openid-connect/certs`) — esto se cachea en memoria (no se pide en cada request, solo cuando el caché expira o no existe todavía).
   c. Se verifica la firma del JWT con esa clave pública. Si no coincide (token alterado o no emitido por este Keycloak), `401`.
   d. Se verifica que `exp` (expiración) no haya pasado. Si el token expiró, `401` — en ese caso el frontend debe usar `/auth/refresh` para obtener uno nuevo, sin pedirle la contraseña de nuevo al usuario.
   e. Se verifica que `iss` (issuer) coincida con `http://<keycloak>/realms/soa-realm` — evita aceptar tokens de otro realm o de otro Keycloak.
   f. Se extraen los claims (`sub`, `email`, `realm_access.roles`, etc.) y se devuelven como el "usuario actual".
4. Si el endpoint además requiere un rol específico (`Depends(require_role("ADMIN"))`), se verifica que `"ADMIN"` esté en `realm_access.roles` — si no está, `403 Forbidden`.
5. Si todo lo anterior pasó, el código del endpoint se ejecuta normalmente, con `current_user` disponible para, por ejemplo, buscar el `Person` asociado vía `keycloak_id`.

**Punto importante**: en ningún paso de este flujo el backend vuelve a llamar a Keycloak por red — toda la validación es criptográfica y local, usando la clave pública cacheada. Keycloak solo se contacta por red en: login, registro, refresh, y la primera vez que se necesita el JWKS (o cuando el caché expira).

---

## 7. Flujo de refresh — paso a paso

Disparado por: `POST /auth/refresh` con body `{ refresh_token }`, cuando el frontend detecta que el access token expiró (por ejemplo, recibió un `401` de algún endpoint).

1. El backend reenvía ese refresh token a Keycloak:
   ```
   POST /realms/soa-realm/protocol/openid-connect/token
   grant_type=refresh_token&client_id=soa-client&client_secret=<secret>&refresh_token=<refresh_token>
   ```
2. Si el refresh token todavía es válido (no expiró, no fue revocado), Keycloak devuelve un `access_token` nuevo (y típicamente un `refresh_token` nuevo también).
3. Si el refresh token ya expiró, Keycloak devuelve error — en ese caso el backend responde `401` y el frontend debe mandar al usuario a loguearse de nuevo con su contraseña.

---

## 8. Resumen visual de los tres flujos

```
REGISTRO
Usuario → [form propio] → Backend → (Client Credentials) → Keycloak: crea usuario → devuelve UUID
                                  → Backend: INSERT persons (..., keycloak_id = UUID)

LOGIN
Usuario → [form propio] → Backend → (Direct Access Grant) → Keycloak: valida user/pass → tokens
                                  → Backend: busca persons WHERE keycloak_id = sub(token)
                                  → Backend → Frontend: { access_token, refresh_token, person }

REQUEST PROTEGIDA
Frontend → Backend (Authorization: Bearer <access_token>)
         → Backend valida JWT localmente (firma + exp + iss, usando JWKS cacheado)
         → si OK: ejecuta el endpoint
         → si rol insuficiente: 403 / si token inválido o expirado: 401
```

---

## 9. Qué falta para implementar esto

- Agregar `keycloak_id` a la entidad `Person` (SQLAlchemy) y su migración.
- Variables de entorno nuevas en `app/config.py`: URL de Keycloak, realm, client_id, client_secret.
- Un módulo de cliente HTTP hacia Keycloak (análogo a como `app/business/s5.py` ya le habla al inference service) para encapsular las llamadas a `/token` y a la Admin API.
- La dependency `get_current_user` y `require_role`, con caché del JWKS.
- Los tres endpoints (`/auth/register`, `/auth/login`, `/auth/refresh`).
- Decidir, endpoint por endpoint del sistema actual (S1 a S5), cuáles quedan públicos y cuáles requieren login y/o un rol específico.
