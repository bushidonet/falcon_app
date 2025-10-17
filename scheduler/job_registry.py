from falcon_app.scheduler.jobs.falcon_sync_hosts_job import FalconSyncHostsJob
from falcon_app.scheduler.jobs.falcon_sync_detections_job import FalconSyncDetectionsJob

JOB_REGISTRY = {
    "RF-015": FalconSyncHostsJob,
    "RF-016": FalconSyncDetectionsJob,
}

def get_job(job_code: str):
    job_class = JOB_REGISTRY.get(job_code)
    if not job_class:
        raise ValueError(f"❌ Job no encontrado: {job_code}")
    return job_class
