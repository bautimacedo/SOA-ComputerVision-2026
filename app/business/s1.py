import requests
import app.config

# GET a la pc local con tailscale.
def get_available_models() -> list[str]:
    try:
        response = requests.get(
            f"{app.config.settings.inference_service_url}/models", # A la ip de tailscale, pc local
            timeout=10,
        )
        response.raise_for_status() #Lanza excepcion para errores, no para 200
        return response.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Inference service unreachable")
