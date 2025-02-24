.. _infrastructure:

================
Infrastructure
================

You can now provision infrastructure within your Goblet code.

Alerts
^^^^^^

You can deploy alerts related to your application by using the alert method. Each alert takes a name and a list of conditions. Notification channels
can be added to the `alerts.notification_channel` key in `config.json` or explicity in the alert. The base `AlertCondition` class allows you to 
fully customize your alert based on the fields privided by the `GCP Alert Resource <https://cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.alertPolicies#conditionhttps://cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.alertPolicies#condition>`_

If you do not need a fully customized alert you can use the built in classes for `MetricCondition`, `LogMatchCondition`, and `CustomMetricCondition`. These come with 
defaults in terms of duration and aggregations, but can be overriden as needed. The `CustomMetricCondition` creates a custom metric based on the filter provided and then 
creates an alert using that metric.  

.. code:: python

    from goblet.infrastructures.alerts import MetricCondition,LogMatchCondition,CustomMetricCondition
    app = Goblet()
    
    # Example Metric Alert for the cloudfunction metric execution_count with a threshold of 10
    app.alert("metric",conditions=[MetricCondition("test", metric="cloudfunctions.googleapis.com/function/execution_count", value=10)])

    # Example Log Match metric that will trigger an incendent off of any Error logs
    app.alert("error",conditions=[LogMatchCondition("error", "severity>=ERROR")])

    # Example Metric Alert that creates a custom metric for severe errors with http code in the 500's and creates an alert with a threshold of 10
    app.alert("custom",conditions=[CustomMetricCondition("custom", metric_filter='severity=(ERROR OR CRITICAL OR ALERT OR EMERGENCY) httpRequest.status=(500 OR 501 OR 502 OR 503 OR 504)', value=10)])

.. _redis:

Redis
^^^^^

.. code:: python

    app = Goblet()
    app.redis("redis-example")

When deploying a backend, the environment variables will automatically be updated to include the `REDIS_INSTANCE_NAME`, `REDIS_HOST` and `REDIS_PORT`. 
To further configure your Redis Instance within Goblet, specify the **`redis`** key in your `config.json`. 
You can reference `Redis Instance Resource <https://cloud.google.com/memorystore/docs/redis/reference/rest/v1/projects.locations.instances#Instance>`_ for more information on available fields.

VPC Connector
^^^^^^^^^^^^^
.. code:: python

    app = Goblet()
    app.vpcconnector("vpcconnector")

When deploying a backend, the vpc access configuration will be updated to include the specified vpc connector.
To further configure your VPC Connector within Goblet, specify the **`vpcconnector`** key in your `config.json`. 
You can reference `Connector Resource <https://cloud.google.com/vpc/docs/reference/vpcaccess/rest/v1/projects.locations.connectors#Connector>`_  for more information on available fields.

.. note::
    * In order to ensure proper configuration of the VPC Connector, the `ipCidrRange` key is required to be set within `vpcconnector` of your `config.json`.

.. _apigateway:

Api Gateway
^^^^^^^^^^^^^

.. code:: python

    app = Goblet(function_name="openapi-existing")
    
    filename = "openapi_spec.yml"
    app.apigateway("openapi-existing", "BACKEND_URL", filename=filename)

.. code:: python 

    app = Goblet(function_name="openapi-existing-dict")

    openapi_dict = {
            "swagger": "2.0",
            "info": {
                "title": "media-serving-service",
                "description": "Goblet Autogenerated Spec",
                "version": "1.0.0",
            },
            "schemes": ["https"],
            "produces": ["application/json"],
            "paths": {
                "/": {
                    "get": {
                        "operationId": "get_main",
                        "responses": {"200": {"description": "A successful response"}},
                    }
                }
            },
            "definitions": {},
        }
    app.apigateway("openapi-existing-from-dict", "BACKEND_URL", openapi_dict=openapi_dict)

You can deploy an Api Gateway and all related resources (Api, Api Config, Gateway) with an existing openapi spec using the apigateway decorator. The decorator can take in a filename or the 
spec as a dictionary. If you dont need to deploy any other Goblet resources you can deploy just the Api Gateway using 
`goblet deploy -p PROJECT --skip-backend --skip-resources`

By default there is a timeout on Api Gateway of 15 seconds. This can be overriden by setting `"api_gateway": {"deadline": 45}` in `config.json`. 

.. note::
    
    * API Gateway only supports swagger 2.0. 

CloudTask Queue
^^^^^^^^^^^^^^^
.. code:: python

    app = Goblet()
    config = { ... }
    client = app.cloudtaskqueue("queue", config=config)

To further configure your CloudTaskQueue within Goblet, provide the config parameter base on the documentation. `CloudTask Queue Resource <https://cloud.google.com/tasks/docs/reference/rest/v2/projects.locations.queues#Queue>`_.
The configuration can be provided inline when declaring the queue, or in your config.json under the **cloudtaskqueue** key.

.. code::

    {
        "cloudtaskqueue": {
            "queue": { ... }
        }
    }

PubSub Topics
^^^^^^^^^^^^^

.. code:: python

    app = Goblet()
    config = { ... }
    app.pubsub_topic("topic", config=config)

To further configure your PubSub topic within Goblet, provide the config parameter base on the documentation. `Topic Resource <https://cloud.google.com/pubsub/docs/reference/rest/v1/projects.topic>`_.