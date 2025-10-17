import logging

from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)


class FalconSearchDomainContactsJob(BaseJob):
    """RF-022 – Consultar contactos por dominio."""

    def __init__(self, stop_flag=None, multiprocess=False, domain_name: str | None = None):
        super().__init__(name="RF-022 - Contactos por dominio", stop_flag=stop_flag, multiprocess=multiprocess)
        self.domain_name = domain_name or "example.com"

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 RF-022 cancelado antes de iniciar.")
            return

        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            results = await self._run_callable(adapter.search_domain_contacts, self.domain_name)
            logger.info(f"[{tenant.name}] ✅ RF-022 retornó {len(results)} eventos.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-022: {ex}")
