========
Backends
========

Cloudfunction
^^^^^^^^^^^^^



Goblet's default backend is first-generation cloud functions. However, Goblet supports both first- and second-generation cloud functions.

* For first-generation:

.. code:: python

    app = Goblet()
    or
    app = Goblet(backend="cloudfunction")

* For second-generation:

.. code:: python

    app = Goblet(backend="cloudfunctionv2")

* You can use config.json to further customize the function you wish to create. Goblet uses the `CloudFunction resource <https://cloud.google.com/functions/docs/reference/rest/v1/projects.locations.functions#resource:-cloudfunction>`_
  for first-gen cloudfunctions and the `Function resource <https://cloud.google.com/functions/docs/reference/rest/v2/projects.locations.functions#resource:-function>`_ for cloudfunctionv2. You may add any additional fields in config.json under "cloudfunction"

* For cloudfunctions v1, python version must be at least python3.7, and for cloudfunctionv2, python version must be at least python3.8.
  To specify a python version for your cloudfunction, you can set the runtime field in config.json as such:

{"cloudfunction": {"runtime": "python38"}}

* Goblet does not currently support eventarc triggers for cloudfunctions

Cloudrun
^^^^^^^^

You can deploy your function to cloudrun updating the backend parameter to main Goblet class.

.. code:: python

    app = Goblet(backend="cloudrun")

.. note::
    The function name for cloudrun must use only lowercase alphanumeric characters and dashes, cannot begin or end with a dash, and cannot be longer than 63 characters

You can pass in configurations to your cloudrun deployment in the `cloudrun` section in your `config.json`. 

Supported configurations include:

- traffic: assigns a custom amount of traffic to the latest revision and decreases previous revisions' traffic proportionally. If the service is brand new, the traffic will always default to 100%.

.. code:: json 

    {
        "cloudrun":{
            "traffic": 25
        }
    }

Deploying to cloudrun requires either a Dockerfile or Procfile in the directory you are looking to deploy your goblet app. If neither
of those files are found, then goblet will create a default Dockerfile that allows the app to be build, deployed, and run correctly. 
Having a custom Dockerfile if only needed if you would like to customize you container at all. 

For `revision configurations <https://cloud.google.com/run/docs/reference/rest/v2/projects.locations.services#RevisionTemplate>`__, pass values into `cloudrun_revision` section in your `config.json`. If you're using a service account, this is where to put it.

.. code:: json 

    {
        "cloudrun_revision":{
            "serviceAccount": "service-account@project.iam.gserviceaccount.com"
        }
    }


For `Container configurations <https://cloud.google.com/run/docs/reference/rest/v2/Container>`__, pass values into `cloudrun_container`

Pass in environment variables here. Secrets will also be passed in as environment variables.

.. code:: json 

    "cloudrun_container": {
        "env": [
            {
                "name": "env-variable-name",
                "value": "env-variable-value"
            },
            {
                "name": "env-variable-name",
                "valueSource": {
                    "secretKeyRef" : {
                        "secret": "secret-name",
                        "version": "secret-version"
                    }
                }
            }
        ]
    }


For `Cloud Build configurations <https://cloud.google.com/build/docs/api/reference/rest/v1/projects.builds>`__, pass values into `cloudbuild`

In order to set a custom artifact registry, use the `artifact_registry` configuration. If you would like to use an artifact registry from a different project, a service account with storage permissions in the current project's bucket and read + write in the other project's artifact registry will be necessary.

.. code:: json 

    {
        "cloudbuild":{
            "artifact_registry": "location-docker.pkg.dev/gcp_project/artifact/image"
            "serviceAccount": "service-account@project.iam.gserviceaccount.com"
        }
    }

To install packages from Artifact Registry ensure `roles/artifactregistry.reader` role has been added to cloudbuild service account and the artifact registry keyring backend install has been enabled within the Dockerfile

.. code:: python
    
    RUN pip install keyrings.google-artifactregistry-auth==1.1.1


To use a previously built artifact, use the `artifact_tag` configuration. When using the `artifact_tag`, cloudbuild will not be called with the source code. `artifact_tag` can be any existing tag or digest in the default registry or the configured `artifact_registry`.

.. code:: json

    {
        "cloudbuild":{
            "artifact_tag": "latest",
            "serviceAccount": "service-account@project.iam.gserviceaccount.com"
        }
    }

To deploy an artifact from `project_a` into a CloudRun Revision on `project_b` (with `project_b_id`) additional roles have to be granted in `project_a`.

The Google managed service account service-project_b_id@serverless-robot-prod.iam.gserviceaccount.com must have `roles/artifactregistry.reader` in `project_a`

This can be done by running:

.. code:: bash

    gcloud projects add-iam-policy-binding project_a \
    --member="serviceAccount:service-project_b_id@serverless-robot-prod.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.reader"
