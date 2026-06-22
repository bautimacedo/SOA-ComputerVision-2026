import requests
import app.config


class KeycloakService:
    def _token_url(self) -> str:
        return f"{app.config.settings.keycloak_url}/realms/{app.config.settings.keycloak_realm}/protocol/openid-connect/token"

    def _admin_users_url(self) -> str:
        return f"{app.config.settings.keycloak_url}/admin/realms/{app.config.settings.keycloak_realm}/users"

    # Direct Access Grant: intercambia user/password por tokens.
    def login(self, email: str, password: str) -> dict:
        try:
            response = requests.post(
                self._token_url(),
                data={
                    "grant_type": "password",
                    "client_id": app.config.settings.keycloak_client_id,
                    "client_secret": app.config.settings.keycloak_client_secret,
                    "username": email,
                    "password": password,
                },
                timeout=10,
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Keycloak unreachable")

        if response.status_code in (400, 401):
            raise ValueError("Credenciales inválidas")
        response.raise_for_status()
        return response.json()

    # Renueva el access token a partir de un refresh token, sin pedir contraseña de nuevo.
    def refresh(self, refresh_token: str) -> dict:
        try:
            response = requests.post(
                self._token_url(),
                data={
                    "grant_type": "refresh_token",
                    "client_id": app.config.settings.keycloak_client_id,
                    "client_secret": app.config.settings.keycloak_client_secret,
                    "refresh_token": refresh_token,
                },
                timeout=10,
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Keycloak unreachable")

        if response.status_code in (400, 401):
            raise ValueError("Refresh token inválido o expirado")
        response.raise_for_status()
        return response.json()

    # Client Credentials Grant: token que representa a la aplicación (service account), no a un usuario.
    def _get_service_token(self) -> str:
        response = requests.post(
            self._token_url(),
            data={
                "grant_type": "client_credentials",
                "client_id": app.config.settings.keycloak_client_id,
                "client_secret": app.config.settings.keycloak_client_secret,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    # Crea el usuario en Keycloak vía Admin REST API y devuelve su UUID (keycloak_id).
    # firstName/lastName son obligatorios en el User Profile del realm (VERIFY_PROFILE) —
    # sin ellos el login por Direct Access Grant falla con "Account is not fully set up".
    def create_user(self, email: str, password: str, first_name: str, last_name: str) -> str:
        try:
            service_token = self._get_service_token()
            response = requests.post(
                self._admin_users_url(),
                headers={"Authorization": f"Bearer {service_token}"},
                json={
                    "username": email,
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "enabled": True,
                    "emailVerified": True,
                    "credentials": [{"type": "password", "value": password, "temporary": False}],
                },
                timeout=10,
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Keycloak unreachable")

        if response.status_code == 409:
            raise ValueError("Ya existe un usuario con ese email en Keycloak")
        response.raise_for_status()

        location = response.headers["Location"]  # .../users/{id}
        return location.rstrip("/").rsplit("/", 1)[-1]

    # Compensación: revierte la creación en Keycloak si falla el insert en persons.
    def delete_user(self, keycloak_id: str) -> None:
        service_token = self._get_service_token()
        response = requests.delete(
            f"{self._admin_users_url()}/{keycloak_id}",
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=10,
        )
        response.raise_for_status()


keycloak_service = KeycloakService()
