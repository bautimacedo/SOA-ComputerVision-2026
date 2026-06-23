import jwt
import requests
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

import app.config

# tokenUrl es solo informativo para el botón "Authorize" de Swagger, no se llama automáticamente.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_jwks_client = None
_issuer = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{app.config.settings.keycloak_url}/realms/{app.config.settings.keycloak_realm}/protocol/openid-connect/certs"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)  # cachea las public keys por 1h
    return _jwks_client


def _get_issuer() -> str:
    # No se compone a mano: según KC_HOSTNAME + cómo llegó la conexión, Keycloak
    # puede poner un "iss" con scheme/puerto que no coinciden ni con la URL interna
    # ni con la pública (ej. http://dominio:8080 si el pedido no pasó por nginx).
    # Se le pregunta directamente al endpoint de discovery, por la misma ruta
    # interna que usamos para pedir tokens, así siempre coincide.
    global _issuer
    if _issuer is None:
        url = f"{app.config.settings.keycloak_url}/realms/{app.config.settings.keycloak_realm}/.well-known/openid-configuration"
        _issuer = requests.get(url, timeout=10).json()["issuer"]
    return _issuer


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=_get_issuer(),
            options={"verify_aud": False},  # Keycloak usa aud="account" por defecto; validamos azp en su lugar
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    if claims.get("azp") != app.config.settings.keycloak_client_id:
        raise HTTPException(status_code=401, detail="Token no emitido para este client")

    return claims


def require_role(*allowed_roles: str):
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_roles = current_user.get("realm_access", {}).get("roles", [])
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(status_code=403, detail="No tenés permisos para esta acción")
        return current_user

    return checker
