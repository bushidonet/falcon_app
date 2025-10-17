import logging
import time
from falconpy import Hosts, Detects, OAuth2, APIError  # requiere `pip install falconpy`
from falcon_app.infrastructure.falcon_auth_manager import FalconAuthManager

logger = logging.getLogger(__name__)

class FalconPyAdapter:
    """Adapter de integración con CrowdStrike Falcon SDK (bloqueante)."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.auth_manager = FalconAuthManager(tenant_id, client_id, client_secret)

    # Factory cliente
    def _client_hosts(self):
        token = self.auth_manager.get_token()
        return Hosts(bearer_token=token)

    def _client_detects(self):
        token = self.auth_manager.get_token()
        return Detects(bearer_token=token)

    # Jobs
    def list_hosts(self, limit: int = 50):
        retries = 3
        delay = 2
        for attempt in range(retries):
            try:
                api = self._client_hosts()
                resp = api.query_devices_by_filter_scroll(limit=limit)
                resources = resp.get("resources", [])
                logger.info(f"[{self.tenant_id}] 💻 {len(resources)} hosts encontrados.")
                return resources
            except APIError as e:
                code = getattr(e, "code", None)
                msg = str(e)
                if code == 401 or "Unauthorized" in msg:
                    logger.warning(f"[{self.tenant_id}] 🔐 Token expirado. Renovando...")
                    self.auth_manager.refresh_after_401()
                    continue
                if code == 429:
                    wait = delay * (attempt + 1)
                    logger.warning(f"[{self.tenant_id}] ⏳ Rate limit. Esperando {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"[{self.tenant_id}] ❌ APIError hosts: {e}")
                raise
            except Exception as ex:
                if "401" in str(ex) or "Unauthorized" in str(ex):
                    self.auth_manager.refresh_after_401()
                    continue
                logger.error(f"[{self.tenant_id}] ❌ Error inesperado hosts: {ex}")
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                raise

    def list_detections(self, filter_query: str = ""):
        retries = 3
        delay = 2
        for attempt in range(retries):
            try:
                api = self._client_detects()
                resp = api.query_detects(filter=filter_query)
                resources = resp.get("resources", [])
                logger.info(f"[{self.tenant_id}] ⚠️ {len(resources)} detecciones encontradas.")
                return resources
            except APIError as e:
                code = getattr(e, "code", None)
                msg = str(e)
                if code == 401 or "Unauthorized" in msg:
                    logger.warning(f"[{self.tenant_id}] 🔐 Token expirado. Renovando...")
                    self.auth_manager.refresh_after_401()
                    continue
                if code == 429:
                    wait = delay * (attempt + 1)
                    logger.warning(f"[{self.tenant_id}] ⏳ Rate limit. Esperando {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"[{self.tenant_id}] ❌ APIError detections: {e}")
                raise
            except Exception as ex:
                if "401" in str(ex) or "Unauthorized" in str(ex):
                    self.auth_manager.refresh_after_401()
                    continue
                logger.error(f"[{self.tenant_id}] ❌ Error inesperado detections: {ex}")
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                raise
