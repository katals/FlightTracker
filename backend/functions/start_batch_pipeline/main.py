import os

import functions_framework
from google.api_core import exceptions as google_exceptions
from google.cloud import dataproc_v1


PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "flighttracker-505314")
REGION = os.environ.get("GCP_REGION", "us-east1")
JOB_URI = "gs://flighttracker-scripts/bts_etl.py"
ZONE = "us-east1-c"
BATCH_JOB_LABEL = "bts-etl"
BATCH_CLUSTER_NAME = "bts-prod-active"
ACTIVE_CLUSTER_STATES = {
    dataproc_v1.ClusterStatus.State.CREATING,
    dataproc_v1.ClusterStatus.State.RUNNING,
}

for optional_state in ("RECONCILING", "UPDATING", "REPAIRING"):
    state_value = getattr(dataproc_v1.ClusterStatus.State, optional_state, None)
    if state_value is not None:
        ACTIVE_CLUSTER_STATES.add(state_value)


def _find_active_batch_cluster(cluster_client):
    """Return the active batch cluster, if one already exists."""
    for cluster in cluster_client.list_clusters(project_id=PROJECT_ID, region=REGION):
        labels = dict(cluster.labels or {})
        if labels.get("job") == BATCH_JOB_LABEL and cluster.status.state in ACTIVE_CLUSTER_STATES:
            return cluster
    return None


@functions_framework.http
def start_batch_pipeline(request):
    cluster_client = dataproc_v1.ClusterControllerClient(
        client_options={"api_endpoint": f"{REGION}-dataproc.googleapis.com"}
    )
    job_client = dataproc_v1.JobControllerClient(
        client_options={"api_endpoint": f"{REGION}-dataproc.googleapis.com"}
    )

    try:
        active_cluster = _find_active_batch_cluster(cluster_client)
        if active_cluster:
            state_name = dataproc_v1.ClusterStatus.State(active_cluster.status.state).name
            message = (
                "Batch pipeline already has an active cluster: "
                f"{active_cluster.cluster_name} ({state_name}). "
                "Skipping duplicate execution."
            )
            print(message)
            return message, 200

        cluster_name = BATCH_CLUSTER_NAME
        print(f"Starting orchestration for cluster: {cluster_name}")

        # Dataproc single-node mode must explicitly disable workers; otherwise
        # the API uses its default worker pool and exceeds the current quota.
        cluster = {
            "cluster_name": cluster_name,
            "config": {
                "master_config": {
                    "machine_type_uri": "e2-standard-2",
                    "num_instances": 1,
                    "disk_config": {
                        "boot_disk_type": "pd-standard",
                        "boot_disk_size_gb": 30,
                    },
                },
                "worker_config": {
                    "num_instances": 0,
                },
                "software_config": {
                    "image_version": "2.0-debian10",
                    "properties": {
                        "dataproc:dataproc.allow.zero.workers": "true",
                    },
                },
                "gce_cluster_config": {
                    "zone_uri": ZONE,
                },
                "lifecycle_config": {
                    "idle_delete_ttl": "600s",
                },
            },
            "labels": {"job": BATCH_JOB_LABEL, "environment": "production"},
        }

        print(f"Creating cluster {cluster_name}...")
        try:
            create_operation = cluster_client.create_cluster(
                project_id=PROJECT_ID,
                region=REGION,
                cluster=cluster,
            )
            create_operation.result()
        except (google_exceptions.AlreadyExists, google_exceptions.Conflict):
            message = (
                f"Batch cluster {cluster_name} is already being created. "
                "Skipping duplicate execution."
            )
            print(message)
            return message, 200
        print(f"Cluster {cluster_name} created.")

        job = {
            "placement": {"cluster_name": cluster_name},
            "pyspark_job": {"main_python_file_uri": JOB_URI},
        }

        print(f"Submitting job to {cluster_name}...")
        submit_response = job_client.submit_job(
            project_id=PROJECT_ID,
            region=REGION,
            job=job,
        )
        job_id = submit_response.reference.job_id
        print(f"Job submitted successfully. Job ID: {job_id}")

        return (
            f"Success: Job {job_id} submitted on cluster {cluster_name}. "
            f"Cluster will auto-terminate.",
            200,
        )

    except Exception as e:
        error_msg = f"Orchestration failed: {str(e)}"
        print(error_msg)
        return error_msg, 500
