"""defining celery task for background processing of adu-dispatcher"""

# import sys
# import traceback
import os
import json
import celery
import requests
from kombu import serialization
import celeryconfig
from service.resources.db_session import create_session

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_INTERVAL = 0
EXTERNAL_SYSTEMS = {
    "dbi":{
        "env_var": "DBI_SYSTEM_URL",
        "dependants": {
            "fire": {
                "env_var": "FIRE_SYSTEM_URL",
                "template": {
                    "name": "fire template"
                }
            }
        },
        "template": {
            "name": "dbi template"
        }
    },
    "planning": {
        "env_var": "PLANNING_SYSTEM_URL",
        "template": {
            "name": "planning template"
        }
    }
}

serialization.register_pickle()
serialization.enable_insecure_serializers()

# pylint: disable=invalid-name
celery_app = celery.Celery('adu-dispatcher')
celery_app.config_from_object(celeryconfig)
# pylint: enable=invalid-name

@celery_app.task(name="tasks", bind=True)
def dispatch(self, external_code, external_system, submission_obj):
    # pylint: disable=unused-argument
    """
        does the work to send data to external system
        records successes
        retry failures
    """
    print("dispatch:submission_id - " + str(submission_obj.id) + ":system - " + external_code)

    try:
        # send payload to external system
        url = os.getenv(external_system["env_var"], None)
        if not url:
            raise ValueError('No url set for ' + external_system["env_var"]) # pragma: no cover
        payload = generate_payload(submission_obj, external_system["template"])
        response = requests.post(url, json=payload)
        print("external system post response:" + str(response.status_code))
        if response.status_code != 200:
            raise SystemError("Received " + str(response.status_code) + " error from " + url)

        # parse out external id and save it to db
        print("response from external system:")
        print(response.text)
        response_json = json.loads(response.text)
        response_id = response_json["data"]["id"]
        session = create_session()
        db_session = session()
        submission_obj.create_external_id(db_session=db_session,\
                            external_system=external_code,\
                            external_id=response_id)
        db_session.close()
        print("external_id saved successfully")

        # queue up dependent systems
        if "dependants" in external_system and len(external_system["dependants"]) > 0:
            schedule(submission_obj, external_system["dependants"])
    except Exception as err: # pylint: disable=broad-except
        print("Oops!  Something went wrong, retrying.  This was the error:")
        print("{0}".format(err))
        # traceback.print_exc(file=sys.stdout)
        self.retry(exc=err)

def generate_payload(submission_obj, payload_template):
    # pylint: disable=unused-argument
    """generate payload from template"""
    # TODO: implement this # pylint: disable=fixme
    return {"foo": "bar"}

def schedule(submission_obj, systems_dict):
    """
        queues jobs to send data to external systems
        returns array of jobs which were scheduled
    """
    if systems_dict is None:
        systems_dict = EXTERNAL_SYSTEMS

    systems_todo = systems_dict.keys()
    systems_done = [external_id.external_system for external_id in submission_obj.external_ids]
    jobs = []
    for todo in systems_todo:
        if todo not in systems_done:
            # data needs to be sent to external system
            print("schedule:submission_id - " + str(submission_obj.id) + ":system - " + todo)

            job = dispatch.apply_async((todo, systems_dict[todo], submission_obj),\
                    serializer='pickle',\
                    retry=True,\
                    retry_policy={
                        'max_retries': systems_dict.get('max_retries', DEFAULT_MAX_RETRIES),
                        'interval_start': systems_dict.get('timeout', DEFAULT_RETRY_INTERVAL)
                    })
            jobs.append(job)
        elif systems_dict[todo]["dependants"] and len(systems_dict[todo]["dependants"]) > 0:
            # external system already done, check dependants
            jobs = jobs + schedule(submission_obj, systems_dict[todo]["dependants"])
    return jobs
