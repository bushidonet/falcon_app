import logging
from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)

class FalconSyncDetectionsJob(BaseJob):
    """RF-016: Sincronizar detecciones desde CrowdStrike."""
    def __init__(self, stop_flag=None, multiprocess=False):
        super().__init__(name="RF-016 - Sync Detections", stop_flag=stop_flag, multiprocess=multiprocess)

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 Cancelado antes de iniciar.")
            return
        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            detections = await self._run_callable(adapter.list_detections)
            logger.info(f"[{tenant.name}] ⚠️ {len(detections)} detecciones sincronizadas.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-016: {ex}")
