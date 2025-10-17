import logging
import time
from typing import Iterable

from falconpy import APIHarness, Hosts, Detects, APIError  # requiere `pip install falconpy`
from falcon_app.infrastructure.falcon_auth_manager import FalconAuthManager

logger = logging.getLogger(__name__)

class FalconPyAdapter:
    """Adapter de integración con CrowdStrike Falcon SDK (bloqueante)."""

    BASE_URL = "https://api.crowdstrike.com"

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

    def _client_harness(self):
        token = self.auth_manager.get_token()
        return APIHarness(base_url=self.BASE_URL, bearer_token=token)

    # HTTP helpers
    def _sdk_request(self, method: str, path: str, params: dict | None = None):
        retries = 3
        delay = 2
        for attempt in range(retries):
            client = self._client_harness()
            try:
                result = client.service_request(method=method, endpoint=path, params=params)
            except APIError as error:
                code = getattr(error, "code", None)
                message = str(error)
                if code == 401 or "Unauthorized" in message:
                    logger.warning(f"[{self.tenant_id}] 🔐 Token expirado. Renovando...")
                    self.auth_manager.refresh_after_401()
                    continue
                if code == 429:
                    wait = delay * (attempt + 1)
                    logger.warning(f"[{self.tenant_id}] ⏳ Rate limit. Esperando {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"[{self.tenant_id}] ❌ APIError SDK {method} {path}: {error}")
                raise
            except Exception as ex:
                if "401" in str(ex) or "Unauthorized" in str(ex):
                    logger.warning(f"[{self.tenant_id}] 🔐 Token expirado. Renovando...")
                    self.auth_manager.refresh_after_401()
                    continue
                logger.error(f"[{self.tenant_id}] ❌ Error inesperado SDK {method} {path}: {ex}")
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                raise

            status_code = result.get("status_code") if isinstance(result, dict) else None
            if status_code == 401:
                logger.warning(f"[{self.tenant_id}] 🔐 Token expirado. Renovando...")
                self.auth_manager.refresh_after_401()
                continue
            if status_code == 429:
                wait = delay * (attempt + 1)
                logger.warning(f"[{self.tenant_id}] ⏳ Rate limit. Esperando {wait}s...")
                time.sleep(wait)
                continue
            if status_code and status_code >= 400:
                logger.error(
                    f"[{self.tenant_id}] ❌ Error {status_code} al invocar {path}: {result.get('body')}"
                )
                raise RuntimeError(result.get("body"))

            return result.get("body", result)

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

    # Nuevos endpoints
    def get_device_metadata(self, device_ids: Iterable[str]):
        ids = [i for i in (device_ids or []) if i]
        if not ids:
            logger.info(f"[{self.tenant_id}] ℹ️ Sin device_ids para RF-015.")
            return []
        params = {"ids": ",".join(ids)}
        data = self._sdk_request("GET", "/devices/entities/devices/v1", params=params)
        resources = data.get("resources", []) if isinstance(data, dict) else []
        logger.info(f"[{self.tenant_id}] 💻 {len(resources)} endpoints consultados (RF-015).")
        return resources

    def search_devices_by_ip(self, filter_query: str):
        params = {"filter": filter_query}
        data = self._sdk_request("GET", "/devices/queries/devices/v1", params=params)
        resources = data.get("resources", []) if isinstance(data, dict) else []
        logger.info(f"[{self.tenant_id}] 🌐 {len(resources)} endpoints filtrados por red (RF-016).")
        return resources

    def search_processes_by_hash(self, sha256_hash: str):
        filter_query = f"sha256:'{sha256_hash}'"
        params = {"filter": filter_query}
        data = self._sdk_request("GET", "/queries/processes/v1", params=params)
        resources = data.get("resources", []) if isinstance(data, dict) else []
        logger.info(f"[{self.tenant_id}] 🧬 {len(resources)} procesos encontrados por hash (RF-017).")
        return resources

    def search_files_by_path(self, path_pattern: str):
        filter_query = f"path:{path_pattern}"
        params = {"filter": filter_query}
        data = self._sdk_request("GET", "/queries/files/v1", params=params)
        resources = data.get("resources", []) if isinstance(data, dict) else []
        logger.info(f"[{self.tenant_id}] 📁 {len(resources)} archivos encontrados por ruta (RF-019).")
        return resources

    def search_network_contacts(self, remote_ip_filter: str):
        filter_query = f"remote_ip:'{remote_ip_filter}'"
        params = {"filter": filter_query}
        data = self._sdk_request("GET", "/queries/network-events/v1", params=params)
        resources = data.get("resources", []) if isinstance(data, dict) else []
        logger.info(f"[{self.tenant_id}] 🔌 {len(resources)} contactos de red encontrados (RF-021).")
        return resources

    def search_domain_contacts(self, domain_name: str):
        filter_query = f"domain_name:'{domain_name}'"
        params = {"filter": filter_query}
        data = self._sdk_request("GET", "/queries/dns-events/v1", params=params)
        resources = data.get("resources", []) if isinstance(data, dict) else []
        logger.info(f"[{self.tenant_id}] 🌍 {len(resources)} eventos DNS encontrados (RF-022).")
        return resources

    def search_processes_by_cmdline(self, cmdline_pattern: str):
        filter_query = f"cmdline:'{cmdline_pattern}'"
        params = {"filter": filter_query}
        data = self._sdk_request("GET", "/queries/processes/v1", params=params)
        resources = data.get("resources", []) if isinstance(data, dict) else []
        logger.info(f"[{self.tenant_id}] 💻 {len(resources)} procesos por cmdline (RF-024).")
        return resources

    def get_process_tree(self, process_id: str):
        process_detail = self._sdk_request("GET", "/entities/processes/v1", params={"ids": process_id})
        children = self._sdk_request("GET", "/entities/processes/children/v1", params={"ids": process_id})
        detail_resources = process_detail.get("resources", []) if isinstance(process_detail, dict) else []
        child_resources = children.get("resources", []) if isinstance(children, dict) else []
        logger.info(
            f"[{self.tenant_id}] 🌳 Proceso {process_id}: detalle {len(detail_resources)} / hijos {len(child_resources)} (RF-025)."
        )
        return {"process": detail_resources, "children": child_resources}
