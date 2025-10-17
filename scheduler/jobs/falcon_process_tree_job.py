import logging

from falcon_app.scheduler.base_job import BaseJob
from falcon_app.infrastructure.adapters.falcon_adapter import FalconPyAdapter

logger = logging.getLogger(__name__)


class FalconProcessTreeJob(BaseJob):
    """RF-025 – Reconstruir árbol de procesos."""

    def __init__(self, stop_flag=None, multiprocess=False, process_id: str | None = None):
        super().__init__(name="RF-025 - Árbol de procesos", stop_flag=stop_flag, multiprocess=multiprocess)
        self.process_id = process_id or "process-id-demo"

    async def _process_tenant(self, tenant):
        if self.stop_flag.is_set():
            logger.warning(f"[{tenant.name}] 🛑 RF-025 cancelado antes de iniciar.")
            return

        try:
            adapter = FalconPyAdapter(tenant.id, tenant.client_id, tenant.client_secret)
            tree = await self._run_callable(adapter.get_process_tree, self.process_id)
            children = tree.get("children", []) if isinstance(tree, dict) else []
            logger.info(f"[{tenant.name}] ✅ RF-025 retornó {len(children)} hijos para {self.process_id}.")
        except Exception as ex:
            logger.error(f"[{tenant.name}] ❌ Error RF-025: {ex}")
