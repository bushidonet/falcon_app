from falcon_app.scheduler.jobs.falcon_endpoint_metadata_job import FalconEndpointMetadataJob
from falcon_app.scheduler.jobs.falcon_search_devices_ip_job import FalconSearchDevicesByIpJob
from falcon_app.scheduler.jobs.falcon_search_files_hash_job import FalconSearchFilesByHashJob
from falcon_app.scheduler.jobs.falcon_search_files_path_job import FalconSearchFilesByPathJob
from falcon_app.scheduler.jobs.falcon_search_network_contacts_job import FalconSearchNetworkContactsJob
from falcon_app.scheduler.jobs.falcon_search_domain_contacts_job import FalconSearchDomainContactsJob
from falcon_app.scheduler.jobs.falcon_search_processes_cmd_job import FalconSearchProcessesByCmdJob
from falcon_app.scheduler.jobs.falcon_process_tree_job import FalconProcessTreeJob

JOB_REGISTRY = {
    "RF-015": FalconEndpointMetadataJob,
    "RF-016": FalconSearchDevicesByIpJob,
    "RF-017": FalconSearchFilesByHashJob,
    "RF-019": FalconSearchFilesByPathJob,
    "RF-021": FalconSearchNetworkContactsJob,
    "RF-022": FalconSearchDomainContactsJob,
    "RF-024": FalconSearchProcessesByCmdJob,
    "RF-025": FalconProcessTreeJob,
}

def get_job(job_code: str):
    job_class = JOB_REGISTRY.get(job_code)
    if not job_class:
        raise ValueError(f"❌ Job no encontrado: {job_code}")
    return job_class
