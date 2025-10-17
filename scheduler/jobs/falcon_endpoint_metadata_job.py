import logging

from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)


class FalconEndpointMetadataJob(BaseJob):
    """RF-015 – Obtener información de endpoints."""

    def __init__(self, stop_flag=None, multiprocess=False):
        super().__init__(name="RF-015 - Endpoint metadata", stop_flag=stop_flag, multiprocess=multiprocess)

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 RF-015 cancelado antes de iniciar.")
            return

        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            hosts = await self._run_callable(adapter.list_hosts)
            host_ids: list[str] = []
            if isinstance(hosts, list):
                host_ids = [h.get("device_id") or h.get("id") for h in hosts if isinstance(h, dict)]
            metadata = await self._run_callable(adapter.get_device_metadata, host_ids[:50])
            logger.info(f"[{tenant.name}] ✅ RF-015 retornó {len(metadata)} endpoints.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-015: {ex}")
