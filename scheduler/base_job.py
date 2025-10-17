import asyncio
import logging
from abc import ABC, abstractmethod
from falcon_app.infrastructure.repositories.tenant_repository import TenantRepository

logger = logging.getLogger(__name__)

class BaseJob(ABC):
    """Clase base para jobs Falcon multitenant."""
    def __init__(self, name: str, stop_flag: asyncio.Event | None = None, multiprocess: bool = False):
        self.name = name
        self.stop_flag = stop_flag or asyncio.Event()
        self.multiprocess = multiprocess
        self._executor = None
        if self.multiprocess:
            from concurrent.futures import ProcessPoolExecutor
            self._executor = ProcessPoolExecutor(max_workers=4)

    async def execute(self):
        tenants = TenantRepository().get_active_tenants()
        logger.info(f"🚀 {self.name}: ejecutando para {len(tenants)} tenants.")
        tasks = [self._process_tenant(t) for t in tenants]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_callable(self, func, *args):
        loop = asyncio.get_running_loop()
        if self._executor:
            return await loop.run_in_executor(self._executor, func, *args)
        return await asyncio.to_thread(func, *args)

    async def cancel(self):
        if self._executor:
            self._executor.shutdown(cancel_futures=True)
            logger.info(f"{self.name}: procesos cancelados.")

    @abstractmethod
    async def _process_tenant(self, tenant):
        ...
