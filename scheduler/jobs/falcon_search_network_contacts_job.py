import logging

from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)


class FalconSearchNetworkContactsJob(BaseJob):
    """RF-021 – Consultar contactos de red por IP/subred."""

    def __init__(self, stop_flag=None, multiprocess=False, remote_ip: str | None = None):
        super().__init__(name="RF-021 - Contactos de red", stop_flag=stop_flag, multiprocess=multiprocess)
        self.remote_ip = remote_ip or "8.8.8.8"

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 RF-021 cancelado antes de iniciar.")
            return

        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            results = await self._run_callable(adapter.search_network_contacts, self.remote_ip)
            logger.info(f"[{tenant.name}] ✅ RF-021 retornó {len(results)} contactos.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-021: {ex}")
