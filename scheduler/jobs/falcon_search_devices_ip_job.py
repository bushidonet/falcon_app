import logging

from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)


class FalconSearchDevicesByIpJob(BaseJob):
    """RF-016 – Filtrar endpoints por IP/CIDR."""

    def __init__(self, stop_flag=None, multiprocess=False, filter_query: str | None = None):
        super().__init__(name="RF-016 - Buscar hosts por red", stop_flag=stop_flag, multiprocess=multiprocess)
        self.filter_query = filter_query or "local_ip_address:*192.168.*"

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 RF-016 cancelado antes de iniciar.")
            return

        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            results = await self._run_callable(adapter.search_devices_by_ip, self.filter_query)
            logger.info(f"[{tenant.name}] ✅ RF-016 retornó {len(results)} hosts.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-016: {ex}")
