import logging
from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)

class FalconSyncHostsJob(BaseJob):
    """RF-015: Sincronizar hosts desde CrowdStrike."""
    def __init__(self, stop_flag=None, multiprocess=False):
        super().__init__(name="RF-015 - Sync Hosts", stop_flag=stop_flag, multiprocess=multiprocess)

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 Cancelado antes de iniciar.")
            return
        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            hosts = await self._run_callable(adapter.list_hosts)
            logger.info(f"[{tenant.name}] ✅ {len(hosts)} hosts sincronizados.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-015: {ex}")
