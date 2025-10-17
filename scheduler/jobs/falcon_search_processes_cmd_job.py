import logging

from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)


class FalconSearchProcessesByCmdJob(BaseJob):
    """RF-024 – Buscar procesos por línea de comandos."""

    def __init__(self, stop_flag=None, multiprocess=False, cmdline_pattern: str | None = None):
        super().__init__(name="RF-024 - Procesos por cmdline", stop_flag=stop_flag, multiprocess=multiprocess)
        self.cmdline_pattern = cmdline_pattern or "powershell"

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 RF-024 cancelado antes de iniciar.")
            return

        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            results = await self._run_callable(adapter.search_processes_by_cmdline, self.cmdline_pattern)
            logger.info(f"[{tenant.name}] ✅ RF-024 retornó {len(results)} procesos.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-024: {ex}")
