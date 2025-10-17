import asyncio
import logging
from falcon_app.scheduler.job_registry import get_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("falcon-scheduler")

class FalconScheduler:
    def __init__(self, jobs=None, interval_seconds: int = 600, multiprocess: bool = False):
        self.stop_flag = asyncio.Event()
        self.jobs_to_run = jobs or ["RF-015", "RF-016"]
        self.interval = interval_seconds
        self.multiprocess = multiprocess

    async def _run_all_jobs(self):
        tasks = []
        for code in self.jobs_to_run:
            job_class = get_job(code)
            job = job_class(stop_flag=self.stop_flag, multiprocess=self.multiprocess)
            tasks.append(job.execute())
        logger.info(f"🚀 Ejecutando jobs: {', '.join(self.jobs_to_run)}")
        await asyncio.gather(*tasks, return_exceptions=True)

    async def start(self):
        logger.info(f"🕓 Scheduler iniciado. Intervalo: {self.interval}s. multiprocess={self.multiprocess}")
        while not self.stop_flag.is_set():
            await self._run_all_jobs()
            try:
                await asyncio.wait_for(self.stop_flag.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                continue

    async def stop(self):
        logger.info("🛑 Deteniendo scheduler...")
        self.stop_flag.set()

async def main():
    scheduler = FalconScheduler(interval_seconds=300, multiprocess=True)
    try:
        await scheduler.start()
    except asyncio.CancelledError:
        logger.warning("Cancelado.")
    finally:
        await scheduler.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("⛔ Interrumpido por el usuario (Ctrl+C)")
