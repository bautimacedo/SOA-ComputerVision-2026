# Keycloak — Curso introductorio

Este documento explica, desde cero, qué es Keycloak y los conceptos que hacen falta para entenderlo. No se asume conocimiento previo de ningún término: cada concepto se define antes de usarse.

---

## 1. El problema que resuelve

Cualquier sistema que tenga usuarios necesita resolver tres preguntas:

1. **¿Quién es esta persona?** (autenticación — *authentication*, a veces se abrevia "authn")
2. **¿Qué puede hacer?** (autorización — *authorization*, "authz")
3. **¿Cómo guardo y protejo sus credenciales** (contraseñas, tokens de sesión, etc.) **sin filtrarlas?**

La forma "casera" de resolver esto es que cada aplicación tenga su propia tabla de usuarios, su propio hash de contraseñas, su propia lógica de sesiones, etc. Esto funciona, pero tiene problemas cuando:

- Tenés **más de una aplicación** (API, frontend, app móvil) y todas necesitan saber quién está logueado — duplicar la lógica de auth en cada una es trabajo repetido y cada copia es una superficie de ataque distinta.
- Necesitás features de seguridad "serias" (doble factor, políticas de contraseñas, bloqueo por intentos fallidos, recuperación de cuenta) — implementarlas bien a mano es difícil y fácil de hacer mal.
- Querés que el usuario inicie sesión una vez y quede logueado en varias aplicaciones relacionadas (esto se llama **Single Sign-On**, SSO).

Un **IAM** (Identity and Access Management — Gestión de Identidad y Accesos) es un sistema centralizado que resuelve estos tres puntos por vos, una sola vez, para todas tus aplicaciones.

---

## 2. ¿Qué es Keycloak?

Keycloak es un **IAM de código abierto** (lo desarrolla Red Hat). Se instala como un servicio aparte (en nuestro caso, un container Docker más, igual que `db` o `nginx`), y tus aplicaciones le **delegan** la autenticación: en vez de que tu API reciba una contraseña y la compare contra su propia base de datos, le pregunta a Keycloak "¿este usuario es quién dice ser?", y Keycloak responde con un **token** que certifica la identidad.

Alternativas a Keycloak que existen en el mercado: **Auth0** (SaaS, de pago a partir de cierto uso, no requiere que vos hostees nada) y **Authentik** (open source, similar filosofía a Keycloak). Elegimos Keycloak porque es gratuito, se audodespliega con Docker (igual que el resto de nuestra infraestructura) y es el estándar de facto en proyectos Java/Spring — aunque nuestro backend es FastAPI, no Spring, los conceptos y el protocolo son los mismos.

---

## 3. Conceptos fundamentales de Keycloak

### Realm

Un **realm** ("reino") es un espacio aislado dentro de Keycloak que agrupa usuarios, roles, clients y toda su configuración de seguridad. Es la unidad de aislamiento más alta: un usuario de un realm no existe ni puede loguearse en otro realm, aunque estén en la misma instancia de Keycloak.

Keycloak viene con un realm llamado `master` por defecto, pero ese realm es para administrar **el propio Keycloak** (crear otros realms, gestionar la instancia), no para los usuarios de tu aplicación. Por eso creamos un realm propio: `soa-realm`.

Analogía: un realm es como una base de datos separada — todo lo que pase dentro de `soa-realm` (usuarios, roles, configuración) no se mezcla con `master` ni con cualquier otro realm que crees en el futuro.

### Client

Un **client** es el registro, dentro de un realm, de una aplicación que va a usar a Keycloak para autenticar usuarios. No es un usuario — es la app misma. En nuestro caso, el client es `soa-client`, y representa a nuestro backend FastAPI.

Hay dos tipos de client según si pueden guardar un secreto de forma segura:

- **Public client**: usado por apps que corren en el navegador o el dispositivo del usuario (SPA, app móvil) donde cualquiera podría inspeccionar el código y encontrar cualquier secreto que pusieras ahí. No tiene `client secret`.
- **Confidential client**: usado por aplicaciones backend, que corren en un servidor que el usuario no puede inspeccionar. Sí tiene un `client secret` — básicamente una contraseña que identifica a la aplicación (no al usuario) ante Keycloak.

Nuestro `soa-client` es confidential, porque es nuestro backend FastAPI el que va a hablar con Keycloak server-to-server.

### Client secret

Es la "contraseña" del client. Cuando tu backend le pide un token a Keycloak, tiene que mandar `client_id` + `client_secret` para probar que es realmente tu backend (y no cualquier otra app) quien está pidiendo el token. Se guarda en el `.env` del servidor, nunca en el código ni en git.

### User

Un usuario dentro de un realm. Keycloak guarda su username, email, password (hasheada — Keycloak nunca guarda contraseñas en texto plano), y queda identificado internamente con un **ID único (UUID)**. Ese UUID es clave: es el dato que vamos a usar para conectar un usuario de Keycloak con un registro en nuestra propia base de datos (tabla `persons`).

### Role

Un **role** es una etiqueta que se le asigna a un usuario para representar qué puede hacer. Hay dos tipos:

- **Realm role**: global dentro del realm, aplicable a cualquier client. Nosotros creamos `ADMIN` y `OPERATOR` como realm roles.
- **Client role**: específico de un client — solo tiene sentido dentro de esa aplicación particular. No los usamos en este proyecto por ahora, pero existen para casos donde distintas apps dentro del mismo realm necesitan roles distintos entre sí.

### Default roles

Keycloak crea automáticamente, por cada realm, un rol compuesto llamado `default-roles-<nombre-del-realm>` (en nuestro caso, `default-roles-soa-realm`). Cualquier rol que agregues como "asociado" (associated role) dentro de ese rol compuesto, se le asigna **automáticamente a todo usuario nuevo**, sin que nadie tenga que asignarlo a mano. Nosotros agregamos `OPERATOR` ahí, para que todo el que se registre sea operador por defecto, y reservamos `ADMIN` para asignación manual.

### Service account

Cuando activás la opción "Service accounts roles" en un client, Keycloak crea automáticamente un usuario especial (`service-account-<client-id>`) que representa **a la aplicación misma**, no a una persona. Sirve para que tu backend pueda autenticarse ante Keycloak como "soy la aplicación" y hacer operaciones administrativas (como crear usuarios nuevos) sin necesitar las credenciales de un admin humano. Es el mecanismo que usamos para que FastAPI pueda crear usuarios en Keycloak durante el registro.

---

## 4. Estándares: OAuth 2.0 y OpenID Connect

Keycloak no inventa su propio protocolo: implementa dos estándares de la industria.

### OAuth 2.0

Es un protocolo de **autorización** (no de autenticación). Define cómo una aplicación puede obtener permiso para acceder a un recurso **en nombre de** un usuario, sin que la aplicación necesite manejar la contraseña real del usuario. Sus actores son:

- **Resource Owner**: el usuario dueño del recurso (la persona).
- **Client**: la aplicación que quiere acceder al recurso (nuestro backend).
- **Authorization Server**: quien autentica al usuario y emite los tokens (Keycloak).
- **Resource Server**: quien posee el recurso protegido y acepta el token como prueba de acceso (también nuestro backend, en este caso — la misma API que protege sus propios endpoints).

OAuth2 por sí solo solo dice "este token te da permiso para X cosa" — no te dice **quién es** el usuario. Para eso existe OIDC.

### OpenID Connect (OIDC)

Es una capa construida **sobre** OAuth 2.0 que agrega el concepto de **identidad**: además del token de acceso, el Authorization Server también puede emitir un token que dice específicamente quién es el usuario (nombre, email, roles). Es lo que realmente usamos para "loguear" gente, no solo para autorizar acceso a un recurso.

---

## 5. JWT — JSON Web Token

Es el formato concreto que usan los tokens que emite Keycloak. Un JWT es un string con tres partes separadas por puntos: `header.payload.signature`.

- **Header**: metadata, como qué algoritmo de firma se usó.
- **Payload**: el contenido real — un conjunto de **claims** (afirmaciones), por ejemplo `sub` (el ID del usuario), `email`, `realm_access.roles` (lista de roles), `exp` (timestamp de expiración), `iss` (quién lo emitió).
- **Signature**: una firma criptográfica que permite verificar que el token no fue alterado y que realmente lo emitió Keycloak (y no alguien que se inventó un JWT a mano).

Las primeras dos partes (header y payload) están solo en **Base64**, no cifradas — cualquiera puede decodificarlas y leer el contenido (por eso nunca hay que poner datos sensibles, como contraseñas, dentro de un JWT). Lo que garantiza que no fue falsificado es la **firma**.

### Cómo se verifica la firma — JWKS

Keycloak firma los tokens con una clave privada que solo él conoce. Para que cualquier aplicación pueda **verificar** esa firma (sin necesidad de preguntarle a Keycloak en cada request), Keycloak publica su clave pública correspondiente en un endpoint público:

```
http://<keycloak>/realms/<realm>/protocol/openid-connect/certs
```

Esto se llama **JWKS** (JSON Web Key Set). Cualquier aplicación (como nuestro FastAPI) puede descargar esa clave pública (y cachearla, ya que no cambia seguido) y usarla para verificar la firma de cualquier JWT, **localmente, sin red**, sabiendo con certeza que si la firma es válida, el token lo emitió Keycloak y no fue modificado.

---

## 6. Tipos de tokens

Cuando Keycloak autentica a un usuario, devuelve hasta tres tokens distintos:

- **Access Token**: el que se usa para acceder a recursos protegidos. Se manda en cada request como header `Authorization: Bearer <token>`. Tiene una vida corta (en nuestra prueba, 300 segundos / 5 minutos) — esto es intencional: si se filtra, el daño posible está acotado en el tiempo.
- **ID Token**: pensado para que la aplicación sepa quién es el usuario (nombre, email) — más relevante en flujos donde hay un frontend que muestra esos datos.
- **Refresh Token**: tiene una vida más larga (1800 segundos / 30 min en nuestra prueba). Sirve para pedirle a Keycloak un Access Token nuevo cuando el anterior expiró, sin que el usuario tenga que volver a escribir su contraseña.

---

## 7. Flujos de autenticación (Grant Types)

Un "grant type" es la forma concreta en que una aplicación obtiene un token. Keycloak soporta varios; estos son los relevantes para nosotros:

### Authorization Code Flow ("Standard Flow" en Keycloak)

Es el flujo recomendado por el estándar cuando hay un usuario interactuando desde un navegador. Pasos:

1. La app redirige al navegador del usuario a la pantalla de login de Keycloak.
2. El usuario ingresa sus credenciales **directamente en Keycloak** (la app nunca ve la contraseña).
3. Keycloak redirige de vuelta a la app con un **código temporal de un solo uso**.
4. La app (desde su backend, server-to-server) intercambia ese código por los tokens reales.

La ventaja de este flujo es que la contraseña del usuario nunca pasa por las manos de "tu" aplicación, y los tokens nunca aparecen en la URL del navegador (viajan en una llamada server-to-server). Es el más seguro, pero implica que el usuario ve la pantalla de login propia de Keycloak (a menos que se personalice con un "tema").

### Direct Access Grant (también llamado "Resource Owner Password Credentials" o "password grant")

Acá la aplicación (no el usuario) le manda usuario y contraseña directamente a Keycloak en una sola llamada HTTP, sin redirects ni pantallas intermedias, y recibe los tokens en la misma respuesta.

```
POST /realms/<realm>/protocol/openid-connect/token
grant_type=password&client_id=...&client_secret=...&username=...&password=...
```

La diferencia clave con el flujo anterior es que acá **tu propia aplicación sí ve la contraseña del usuario** (aunque sea solo de paso, para reenviarla a Keycloak). Por eso el estándar OAuth2 considera este flujo menos recomendable en general — rompe el principio de que solo el Authorization Server debería ver credenciales. Sin embargo, es aceptable cuando la aplicación es **"first-party"**: es decir, cuando la misma organización controla tanto el frontend (el formulario de login) como el backend que llama a Keycloak — que es exactamente nuestro caso. Es el flujo que vamos a usar para tener un formulario de login propio, en vez de la pantalla de Keycloak.

### Client Credentials Grant

Pensado para comunicación **máquina a máquina**, sin ningún usuario humano involucrado. La aplicación se autentica con su propio `client_id` + `client_secret` y recibe un token que representa "a la aplicación misma", no a una persona. Es lo que pasa por detrás cuando activamos el **service account** del client: nuestro backend usa este grant para obtener un token con permiso `manage-users`, y con ese token llama a la Admin REST API de Keycloak para crear usuarios nuevos.

---

## 8. MFA y TOTP (para más adelante)

No lo configuramos todavía, pero vale la pena conocer el concepto: **MFA** (Multi-Factor Authentication) exige más de un "factor" de verificación para loguearse — típicamente algo que sabés (contraseña) más algo que tenés (un código temporal). **TOTP** (Time-based One-Time Password) es el mecanismo más común: una app como Google Authenticator genera un código numérico que cambia cada 30 segundos, sincronizado con el servidor mediante un secreto compartido (que se configura escaneando un QR la primera vez). Keycloak lo soporta nativamente en su pantalla de login — pero como decidimos usar Direct Access Grant con un formulario propio, agregar MFA después va a requerir más trabajo manual (no viene gratis como en el flujo estándar). Quedó como nota para una futura iteración.

---

## 9. Admin REST API

Además del login, Keycloak expone una API REST completa para administrar el realm programáticamente: crear usuarios, asignar roles, modificar configuración, etc. (`/admin/realms/<realm>/...`). Es la que nuestro backend va a usar, autenticado como service account, para crear usuarios nuevos cuando alguien se registra desde nuestro formulario propio — en vez de que un humano los cree a mano desde la consola de Keycloak.

---

## 10. Glosario rápido

| Término | Significado |
|---|---|
| IAM | Sistema centralizado de gestión de identidad y accesos |
| Realm | Espacio aislado de usuarios/roles/config dentro de Keycloak |
| Client | Registro de una aplicación que delega auth en Keycloak |
| Client secret | "Contraseña" que identifica a una aplicación (no a un usuario) |
| Confidential / Public client | Si el client puede o no guardar un secreto de forma segura |
| Role | Etiqueta de permiso asignada a un usuario |
| Default roles | Roles que se asignan automáticamente a todo usuario nuevo |
| Service account | Usuario especial que representa a la aplicación misma, no a una persona |
| OAuth 2.0 | Estándar de autorización (delegar acceso sin compartir contraseña) |
| OIDC | Capa de identidad sobre OAuth2 (saber *quién* es el usuario) |
| JWT | Formato de token: header.payload.signature, en Base64 + firma |
| Claim | Cada dato dentro del payload de un JWT (ej. `sub`, `email`, roles) |
| JWKS | Endpoint público con las claves para verificar la firma de un JWT |
| Access Token | Token de vida corta usado para acceder a recursos protegidos |
| Refresh Token | Token de vida más larga, usado para renovar el access token |
| Authorization Code Flow | Flujo de login vía redirect + pantalla de Keycloak |
| Direct Access Grant | Flujo de login donde la app manda user/password directo |
| Client Credentials Grant | Flujo máquina-a-máquina (sin usuario humano) |
| MFA / TOTP | Segundo factor de autenticación / código temporal numérico |
