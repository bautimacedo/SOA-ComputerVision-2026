# Plan de pruebas manual — Sistema completo (local)

Checklist para validar el sistema de punta a punta: auth/Keycloak, S1-S5, monitoreo y resiliencia. Pensado para correr con la colección de Postman [`postman/SOA2026.postman_collection.json`](../postman/SOA2026.postman_collection.json) + el environment [`SOA2026-local`](../postman/SOA2026-local.postman_environment.json).

---

## 0. Preparación

Servicios que tienen que estar corriendo antes de empezar:

| Servicio | Cómo se levanta | Verificación |
|---|---|---|
| `db`, `app`, `keycloak`, `keycloak_db`, `influxdb`, `telegraf`, `grafana`, `adminer` | `docker compose up -d` | `docker compose ps` — todos `Up` |
| `inference_service` | `cd inference_service && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001` | `curl http://localhost:8001/health` |

Importar en Postman: la colección + el environment, y completar la variable `keycloak_client_secret` del environment con el secret real de `soa-client` (Keycloak → Clients → soa-client → Credentials).

---

## 1. Auth — flujo de login

- [ ] `POST /auth/register` con datos nuevos → `201`, devuelve la persona creada
- [ ] Repetir el mismo `POST /auth/register` → `409` (email duplicado)
- [ ] `POST /auth/login` con las credenciales correctas → `200`, trae `access_token`, `refresh_token`, `expires_in`, `person`
- [ ] `POST /auth/login` con password incorrecta → `401`
- [ ] `POST /auth/login` con un email que no existe → `401`
- [ ] Decodificar el `access_token` (ej. en [jwt.io](https://jwt.io) o `python3 -c "import jwt,sys;print(jwt.decode(sys.argv[1],options={'verify_signature':False}))" <token>`) y confirmar:
  - `sub` es un UUID
  - `realm_access.roles` incluye `OPERATOR`
  - `azp` es `soa-client`
  - `iss` es `http://keycloak:8080/realms/soa-realm`
- [ ] `POST /auth/refresh` con el `refresh_token` recién obtenido → `200`, tokens nuevos
- [ ] `POST /auth/refresh` con un refresh_token inventado/corrupto → `401`
- [ ] Esperar 5 minutos (vida del access_token) y usar ese token vencido en `GET /models` → `401` → renovar con `/auth/refresh` → reintentar → `200`

---

## 2. Roles (ADMIN / OPERATOR / VIEWER)

⚠️ **Importante, antes de probar esto**: hoy los endpoints solo verifican *"¿hay un token válido?"* (`get_current_user`), no *"¿qué rol tiene ese token?"* (`require_role`). La matriz de permisos del README es el diseño acordado, pero **todavía no está aplicada en el código** — cualquier usuario autenticado, sea `OPERATOR` o `VIEWER`, puede hoy llamar a cualquier endpoint, incluidos los `POST`. Las pruebas de esta sección van a **fallar** (en el sentido de "el viewer sí puede postear") hasta que agreguemos `require_role(...)` a los routers correspondientes. Avisame si querés que lo implementemos antes de seguir.

- [ ] Crear un usuario y, desde la consola de Keycloak (`Users` → el usuario → `Role mapping` → `Assign role`), asignarle `ADMIN`. Loguearse con `/auth/login` y confirmar que el JWT trae `ADMIN` en `realm_access.roles`.
- [ ] Repetir asignando `VIEWER` a otro usuario.
- [ ] (Una vez implementado `require_role`) Con un token de `VIEWER`, intentar `POST /detections` → debería dar `403`.
- [ ] (Una vez implementado) Con un token de `OPERATOR`, intentar lo mismo → debería dar `201` (operator puede cargar).

---

## 3. S1 — Modelos

- [ ] `GET /models` sin header `Authorization` → `401`
- [ ] `GET /models` con token válido → `200`, lista de archivos `.pt`
- [ ] Apagar el `inference_service` (`Ctrl+C` en su terminal) y reintentar `GET /models` → `503 Inference service unreachable`. Volver a levantarlo después.

---

## 4. S2 — Detección

- [ ] `POST /detections` con una imagen real + `model_id` válido (de los que devuelve S1) + `metadata` con `lat`/`lon` → `201`, devuelve `frameId` + `detections`
- [ ] Repetir con un `model_id` que no exista → `400`
- [ ] Repetir sin `lat`/`lon` en `metadata` → `400`
- [ ] Repetir mandando un archivo que no sea imagen (ej. un `.txt` renombrado) → `400`
- [ ] Verificar en Adminer (`Users` → conectar a `db`) que se insertó en `frames`, `files` y `detections` con el mismo `frame_id`
- [ ] Verificar en la consola de AWS S3 (o `aws s3 ls s3://soa-frames-tp/frames/`) que la imagen subió como `frames/{frameId}.jpg`

---

## 5. S3 — Fotogramas

- [ ] `GET /frames/{frameId}` de uno creado en el paso anterior → `200`, imagen JPEG binaria
- [ ] `GET /frames/{frameId}?thumbnail=true` → `200`, imagen más chica (comparar `Content-Length` contra la versión sin thumbnail)
- [ ] `GET /frames/{un-uuid-que-no-existe}` → `404`
- [ ] `GET /frames/no-es-un-uuid` → `422` (formato inválido)

---

## 6. S4 — Búsqueda

- [ ] `GET /frames/search` con el rango de `lat`/`lon` que incluye al frame de S2 → aparece en los resultados
- [ ] Agregar `&classes=<clase-detectada>` → sigue apareciendo
- [ ] Agregar `&classes=clase-que-no-detectó-nadie` → lista vacía
- [ ] Agregar `&model_id=<modelo-que-no-usaste>` → lista vacía
- [ ] `lat_min` mayor que `lat_max` → `400`

---

## 7. S5 — Personas y reconocimiento facial

- [ ] `POST /persons` → `201`
- [ ] Repetir con el mismo email → `409`
- [ ] `GET /persons/{id}` → `200`
- [ ] `GET /persons/{uuid-inexistente}` → `404`
- [ ] `POST /persons/{id}/embeddings` con **una** foto de un rostro claro y único → `validEmbeddings: 1`, `rejectedImages: 0`
- [ ] Repetir con una foto sin rostro o con dos rostros → `rejectedImages: 1`
- [ ] Repetir mandando 3 fotos juntas (3 campos `images`) → `processedImages: 3`
- [ ] `POST /face-recognition` con una foto **de la misma persona** cargada arriba → `personId` coincide, `confidence` alto (>0.8)
- [ ] `POST /face-recognition` con una foto de **otra persona** no cargada → `personId: null`
- [ ] Repetir con `threshold=0.99` sobre un match marginal → `personId: null` por confianza insuficiente, aunque haya match parcial

---

## 8. Monitoreo — Telegraf + InfluxDB + Grafana

Por defecto `influxdb` (8086) y `grafana` (3000) no tienen el puerto publicado al host — si querés inspeccionarlos directo desde el navegador en esta prueba local, agregales `ports:` en `docker-compose.yml` igual que hicimos con `app` (`"8086:8086"` y `"3000:3000"`), y recreá esos dos containers.

- [ ] Generar tráfico: correr varios de los requests anteriores (S1, S2, S5.3, S5.4)
- [ ] Entrar a InfluxDB (`http://localhost:8086`, usuario `admin`/`soa2026admin`) → bucket `metrics` → confirmar que hay datos recientes en las mediciones `http_requests`, `inference`, `embeddings`, `recognition`
- [ ] Entrar a Grafana (`http://localhost:3000`, usuario `admin`/`soa2026`) y armar un panel simple sobre esos datos (ej. `duration_ms` de `http_requests` en el tiempo)
- [ ] El login de Grafana vía Keycloak (botón "Sign in with Keycloak") **no se puede probar completo en este entorno local** — depende del dominio real `soagmr.mooo.com` que está hardcodeado en `GF_SERVER_ROOT_URL` y en el `redirect_uri` de `grafana-client`. Queda para la prueba en la VPS.

---

## 9. Keycloak — chequeo de configuración

- [ ] `Realm settings` → `Default roles` → `OPERATOR` está en la lista
- [ ] `Clients` → `soa-client` → `Settings`: `Standard flow` y `Direct access grants` en `On`, `Service accounts roles` en `On`
- [ ] `Clients` → `soa-client` → `Service accounts roles`: tiene `manage-users` (y nada más, sin `manage-clients` ni `create-client`)
- [ ] `Clients` → `grafana-client` → `Settings`: `Standard flow` en `On`, `Direct access grants` en `Off`
- [ ] `Users` → el usuario de prueba → `Role mapping` → tiene `OPERATOR`

---

## 10. Resiliencia — servicios caídos

- [ ] `docker compose stop keycloak` → `POST /auth/login` debería dar `503 Keycloak unreachable`. Levantar de nuevo con `docker compose start keycloak`.
- [ ] Apagar el `inference_service` (`Ctrl+C`) → `GET /models` y `POST /detections` dan `503`. Volver a levantarlo.
- [ ] Después de cada apagado/encendido, confirmar que `GET /health` sigue respondiendo `200` (no debería verse afectado por la caída de servicios externos).
