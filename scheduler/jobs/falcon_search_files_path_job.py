import logging

from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)


class FalconSearchFilesByPathJob(BaseJob):
    """RF-019 – Buscar archivos por patrón de ruta."""

    def __init__(self, stop_flag=None, multiprocess=False, path_pattern: str | None = None):
        super().__init__(name="RF-019 - Buscar archivos por ruta", stop_flag=stop_flag, multiprocess=multiprocess)
        self.path_pattern = path_pattern or "*System32*.exe"

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 RF-019 cancelado antes de iniciar.")
            return

        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            results = await self._run_callable(adapter.search_files_by_path, self.path_pattern)
            logger.info(f"[{tenant.name}] ✅ RF-019 retornó {len(results)} rutas.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-019: {ex}")
