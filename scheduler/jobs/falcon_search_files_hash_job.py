import logging

from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)


class FalconSearchFilesByHashJob(BaseJob):
    """RF-017 – Buscar procesos/hosts por hash de fichero."""

    def __init__(self, stop_flag=None, multiprocess=False, sha256_hash: str | None = None):
        super().__init__(name="RF-017 - Buscar archivos por hash", stop_flag=stop_flag, multiprocess=multiprocess)
        self.sha256_hash = sha256_hash or "abc123def456"

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 RF-017 cancelado antes de iniciar.")
            return

        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            results = await self._run_callable(adapter.search_processes_by_hash, self.sha256_hash)
            logger.info(f"[{tenant.name}] ✅ RF-017 retornó {len(results)} coincidencias.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-017: {ex}")
