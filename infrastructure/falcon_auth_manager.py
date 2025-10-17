import requests
import time
import logging
from falcon_app.infrastructure.services.token_cache import get_token_cache

logger = logging.getLogger(__name__)

class FalconAuthManager:
    TOKEN_URL = "https://api.crowdstrike.com/oauth2/token"

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret

    def get_token(self) -> str:
        """Obtiene un token válido desde cache o solicitando uno nuevo."""
        cache = get_token_cache()
        token = cache.get(self.tenant_id)
        if token:
            logger.debug(f"[{self.tenant_id}] Token obtenido desde cache.")
            return token

        return self._request_new_token()

    def _request_new_token(self) -> str:
        """Solicita un nuevo token a Falcon OAuth2 y lo guarda en cache."""
        cache = get_token_cache()
        logger.info(f"[{self.tenant_id}] 🔑 Solicitando nuevo token a Falcon OAuth...")

        try:
            response = requests.post(self.TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"[{self.tenant_id}] ❌ Error al solicitar token: {e}")
            raise

        token = data["access_token"]
        expires_in = data["expires_in"]
        expires_at = time.time() + expires_in - 60  # margen de 1 min

        cache.set(self.tenant_id, token, expires_at)
        logger.info(f"[{self.tenant_id}] 💾 Token guardado (expira en {expires_in}s).")
        return token

    def invalidate(self):
        """Elimina el token en cache (por ejemplo tras un 401)."""
        cache = get_token_cache()
        cache.invalidate(self.tenant_id)
        logger.info(f"[{self.tenant_id}] 🧹 Token invalidado manualmente.")

    def refresh_after_401(self) -> str:
        """Invalida el token y solicita uno nuevo tras error 401."""
        logger.warning(f"[{self.tenant_id}] Token expirado o inválido. Renovando...")
        self.invalidate()
        return self._request_new_token()
