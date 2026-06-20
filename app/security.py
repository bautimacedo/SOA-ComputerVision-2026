import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

import app.config

# tokenUrl es solo informativo para el botón "Authorize" de Swagger, no se llama automáticamente.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_jwks_client = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{app.config.settings.keycloak_url}/realms/{app.config.settings.keycloak_realm}/protocol/openid-connect/certs"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)  # cachea las public keys por 1h
    return _jwks_client


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    issuer = f"{app.config.settings.keycloak_url}/realms/{app.config.settings.keycloak_realm}"
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},  # Keycloak usa aud="account" por defecto; validamos azp en su lugar
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    if claims.get("azp") != app.config.settings.keycloak_client_id:
        raise HTTPException(status_code=401, detail="Token no emitido para este client")

    return claims


def require_role(role: str):
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        roles = current_user.get("realm_access", {}).get("roles", [])
        if role not in roles:
            raise HTTPException(status_code=403, detail="No tenés permisos para esta acción")
        return current_user

    return checker
