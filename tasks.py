"""defining celery task for background processing of adu-dispatcher"""

# import sys
# import traceback
import os
import json
import csv
import celery
import requests
from kombu import serialization
import celeryconfig
from service.resources.db_session import create_session
from service.resources.external_systems import MAP

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_INTERVAL = 0
CSV_DIR = "csv/"
GROUP_COUNTER_REPLACEMENT_STRING = "%#%"

serialization.register_pickle()
serialization.enable_insecure_serializers()

# pylint: disable=invalid-name
celery_app = celery.Celery('adu-dispatcher')
celery_app.config_from_object(celeryconfig)
# pylint: enable=invalid-name

@celery_app.task(name="tasks.dispatch", bind=True)
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
            raise SystemError("Received " + str(response.status_code) +\
                    " error from " + url + ":" + response.text)

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

@celery_app.task(name="tasks.send-csv", bind=True)
def send_csv(self, external_code, external_system, submission_obj):
    # pylint: disable=unused-argument
    """
        does the work to create a csv and email it
        records csv in database
    """
    print("send_csv:submission_id - " + str(submission_obj.id) + ":system - " + external_code)
    # create csv
    file_path = create_csv(submission_obj, external_system["template"])
    print("file created: " + file_path)

    # email it

def create_csv(submission_obj, template):
    # pylint: disable=unused-argument
    """
        creates csv and returns filepath
    """
    file_path = os.path.join(CSV_DIR, str(submission_obj.id) + ".csv")

    # generate field names and ids
    field_names = []
    ids = []
    for item in template:
        print(json.dumps(item))
        # loop through a group object
        if "type" in item and item["type"] == "grouping":
            for i in range(item["count"]): # zero-based
                for nested_item in item["template"]:
                    new_name = nested_item["name"]
                    new_id = nested_item["id"]
                    field_names.append(new_name.replace(GROUP_COUNTER_REPLACEMENT_STRING, str(i+1)))
                    ids.append(new_id.replace(GROUP_COUNTER_REPLACEMENT_STRING, str(i+1)))
        else:
            field_names.append(item["name"])
            ids.append(item["id"])

    # generate data
    data = []
    data_json = json.loads(submission_obj.data)
    for form_id in ids:
        if form_id in data_json:
            data.append(data_json[form_id])
        else:
            data.append(None)

    with open(file_path, "w+") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(field_names)
        csv_writer.writerow(data)

    return file_path

def schedule(submission_obj, systems_dict):
    """
        queues jobs to send data to external systems
        returns array of jobs which were scheduled
    """
    if systems_dict is None:
        systems_dict = MAP

    systems_todo = systems_dict.keys()
    systems_done = [external_id.external_system for external_id in submission_obj.external_ids]
    jobs = []
    for todo in systems_todo:
        if todo not in systems_done:
            print("schedule:submission_id - " + str(submission_obj.id) + ":system - " + todo)

            # determine if send csv or making api call
            if systems_dict[todo]['type'] == 'csv':
                print("scheduling csv")
                # csv
                job = send_csv.apply_async((todo, systems_dict[todo], submission_obj),\
                        serializer='pickle',\
                        retry=True,\
                        retry_policy={
                            'max_retries': systems_dict.get('max_retries', DEFAULT_MAX_RETRIES),
                            'interval_start': systems_dict.get('timeout', DEFAULT_RETRY_INTERVAL)
                        })
            else:
                print("scheduling external api call")
                # data needs to be sent to external system api
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
