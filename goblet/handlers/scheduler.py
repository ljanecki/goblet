import logging
import os

from goblet.handlers.handler import Handler
from goblet_gcp_client.client import get_default_project, get_default_location

from goblet.common_cloud_actions import get_cloudrun_url
from goblet.permissions import gcp_generic_resource_permissions, add_binding

from googleapiclient.errors import HttpError

log = logging.getLogger("goblet.deployer")
log.setLevel(logging.getLevelName(os.getenv("GOBLET_LOG_LEVEL", "INFO")))


class Scheduler(Handler):
    """Cloud Scheduler job which calls http endpoint
    https://cloud.google.com/scheduler/docs
    """

    resource_type = "scheduler"
    valid_backends = ["cloudfunction", "cloudfunctionv2", "cloudrun"]
    can_sync = True
    required_apis = ["cloudscheduler"]
    permissions = [
        *gcp_generic_resource_permissions("cloudscheduler", "jobs"),
    ]

    def register(self, name, func, kwargs):
        schedule = kwargs["schedule"]
        timezone = kwargs["timezone"]
        kwargs = kwargs.pop("kwargs")
        description = kwargs.get("description", "Created by goblet")
        headers = kwargs.get("headers", {})
        httpMethod = kwargs.get("httpMethod", "GET")
        retry_config = kwargs.get("retryConfig")
        body = kwargs.get("body")
        uri = kwargs.get("uri")
        attempt_deadline = kwargs.get("attemptDeadline")
        authMethod = kwargs.get("authMethod", "oidcToken")

        job_num = 1
        if self.resources.get(name):
            # increment job_num if there is already a scheduled job for this func
            job_num = self.resources[name]["job_num"] + 1
            self.resources[name]["job_num"] = job_num
            name = f"{name}-{job_num}"
        self.resources[name] = {
            "job_num": job_num,
            "job_json": {
                "name": f"projects/{get_default_project()}/locations/{get_default_location()}/jobs/{self.name}-{name}",
                "schedule": schedule,
                "timeZone": timezone,
                "description": description,
                "retry_config": retry_config,
                "attemptDeadline": attempt_deadline,
                "httpTarget": {
                    # "uri": ADDED AT runtime,
                    "headers": {
                        "X-Goblet-Type": "schedule",
                        "X-Goblet-Name": name,
                        **headers,
                    },
                    "body": body,
                    "httpMethod": httpMethod,
                    authMethod: {
                        # "serviceAccountEmail": ADDED AT runtime
                    },
                },
            },
            "authMethod": authMethod,
            "uri": uri,
            "func": func,
        }

    def __call__(self, request, context=None):
        headers = request.headers
        func_name = headers.get("X-Goblet-Name")
        if not func_name:
            raise ValueError("No X-Goblet-Name header found")

        job = self.resources[func_name]
        if not job:
            raise ValueError(f"Function {func_name} not found")
        return job["func"]()

    def _deploy(self, source=None, entrypoint=None):
        if not self.resources:
            return

        if self.backend.resource_type.startswith("cloudfunction"):
            resp = self.versioned_clients.cloudfunctions.execute(
                "get", parent_key="name", parent_schema=self.cloudfunction
            )
            if not resp:
                raise ValueError(f"Function {self.cloudfunction} not found")
            try:
                target = resp["httpsTrigger"]["url"]
                service_account = resp["serviceAccountEmail"]
            except KeyError:
                target = resp["serviceConfig"]["uri"]
                service_account = resp["serviceConfig"]["serviceAccountEmail"]

        if self.backend.resource_type == "cloudrun":
            # dont get target in scheduler is needed only for jobs
            cloudrun_target = None
            if self.config.cloudrun and self.config.cloudrun.get("service-account"):
                service_account = self.config.cloudrun.get("service-account")
            elif self.config.scheduler and self.config.scheduler.get("serviceAccount"):
                service_account = self.config.scheduler.get("serviceAccount")
            elif self.config.job and self.config.job.get("serviceAccount"):
                service_account = self.config.job.get("serviceAccount")
            else:
                raise ValueError(
                    "Service account not found in cloudrun. You can set `serviceAccount` field in config.json under `scheduler`"
                )

        self.service_accounts = [service_account]

        log.info("deploying scheduled jobs......")
        for job_name, job in self.resources.items():
            if job["uri"]:
                target = job["uri"]
            elif self.backend.resource_type.startswith("cloudfunction"):
                target = target
            else:
                # only run once
                if not cloudrun_target:
                    cloudrun_target = get_cloudrun_url(
                        self.versioned_clients.run, self.name
                    )
                target = cloudrun_target
            job["job_json"]["httpTarget"]["uri"] = target
            job["job_json"]["httpTarget"][job["authMethod"]][
                "serviceAccountEmail"
            ] = service_account

            self.deploy_job(job_name, job["job_json"])
            triggered_resource = f"{self.name}-{job_name.split('schedule-job-')[-1]}"
            # Set invoker permission on cloudrun job
            if "jobs/" in target:
                add_binding(
                    self.versioned_clients.run_job,
                    "projects/{project_id}/locations/{location_id}/jobs/"
                    + triggered_resource,
                    "roles/run.invoker",
                    [f"serviceAccount:{service_account}"],
                )

    def _sync(self, dryrun=False):
        jobs = self.versioned_clients.cloudscheduler.execute("list").get("jobs", [])
        filtered_jobs = list(
            filter(lambda job: f"jobs/{self.name}-" in job["name"], jobs)
        )
        for filtered_job in filtered_jobs:
            split_name = filtered_job["name"].split("/")[-1].split(f"{self.name}-")
            filtered_name = split_name[-1]
            if not self.resources.get(filtered_name):
                log.info(f'Detected unused job in GCP {filtered_job["name"]}')
                if not dryrun:
                    # TODO: Handle deleting multiple jobs with same name
                    self._destroy_job(filtered_name)

    def deploy_job(self, job_name, job):
        try:
            self.versioned_clients.cloudscheduler.execute(
                "create", params={"body": job}
            )
            log.info(f"created scheduled job: {job_name} for {self.name}")
        except HttpError as e:
            if e.resp.status == 409:
                log.info(f"updated scheduled job: {job_name} for {self.name}")
                self.versioned_clients.cloudscheduler.execute(
                    "patch",
                    parent_key="name",
                    parent_schema=job["name"],
                    params={"body": job},
                )
            else:
                raise e

    def destroy(self):
        if not self.resources:
            return
        for job_name in self.resources.keys():
            self._destroy_job(job_name)

    def _destroy_job(self, job_name):
        try:
            self.versioned_clients.cloudscheduler.execute(
                "delete",
                parent_key="name",
                parent_schema="projects/{project_id}/locations/{location_id}/jobs/"
                + self.name
                + "-"
                + job_name,
            )
            log.info(f"Destroying scheduled job {job_name}......")
        except HttpError as e:
            if e.resp.status == 404:
                log.info("Scheduled jobs already destroyed")
            else:
                raise e
