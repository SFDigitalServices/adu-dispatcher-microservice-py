"""defining celery task for background processing of adu-dispatcher"""

# import sys
# import traceback
import os
import json
from datetime import datetime
import celery
import requests
from kombu import serialization
import celeryconfig
from service.resources.external_systems import MAP
from service.resources.db_session import create_session
from service.resources.submission_model import Submission

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
        if not "env_var" in external_system:
            raise ValueError('env_var required in mapping for external api calls')
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

def schedule(submission_obj, systems_dict):
    """
        queues jobs to send data to external systems
        returns array of jobs which were scheduled
    """

    systems_todo = systems_dict.keys()
    systems_done = [external_id.external_system for external_id in submission_obj.external_ids]
    jobs = []

    for todo in systems_todo:
        if todo not in systems_done and 'type' in systems_dict[todo]\
                and systems_dict[todo]['type'] == 'api':
            print("schedule:submission_id - " + str(submission_obj.id) + ":system - " + todo)

            # determine if send csv or making api call
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
        elif "dependants" in systems_dict[todo] and len(systems_dict[todo]["dependants"]) > 0:
            # external system already done, check dependants
            jobs = jobs + schedule(submission_obj, systems_dict[todo]["dependants"])
    return jobs


@celery_app.task(name="tasks.outbound-csv", bind=True)
def outbound_csv(self):
    # pylint: disable=unused-argument
    """
        creates csvs and puts them on an ftp server
    """
    print("outbound_csv started:" + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    session = create_session()
    db_session = session()
    new_submissions = db_session.query(Submission).filter(Submission.csv_date_processed.is_(None))

    # create csvs
    for external_code in MAP:
        if "type" in MAP[external_code] and MAP[external_code]["type"] == "csv":
            file_path = create_csv(new_submissions, MAP[external_code]["template"])
            print("file created: " + file_path)

            # ftp it

            # archive csv file in the cloud

            # mark csv processed
            now = datetime.utcnow()
            for submission in new_submissions:
                submission.csv_date_processed = now
            db_session.commit()

    db_session.close()
    print("outbound_csv finished:" + datetime.now().strftime("%Y/%m/%d, %H:%M:%S"))

@celery_app.task(name="tasks.inbound-csv", bind=True)
def inbound_csv(self):
    # pylint: disable=unused-argument
    """
        process csv from dbi
    """
    print("inbound_csv:submission")
    print("TODO: this isn't implemented yet")

def create_csv(submissions, template):
    # pylint: disable=unused-argument
    """
        creates csv and returns filepath
    """
    file_path = os.path.join(CSV_DIR, datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")

    with open(file_path, "w+") as csv_file:
        # generate field names and ids
        field_names = ['adu_id']  # first field is adu db unique identifier
        ids = []
        for item in template:
            print(json.dumps(item))
            # loop through a group object
            if "type" in item and item["type"] == "grouping":
                for i in range(item["count"]): # zero-based
                    for nested_item in item["template"]:
                        field_names.append(\
                                nested_item["name"].replace(GROUP_COUNTER_REPLACEMENT_STRING,\
                                str(i+1)))
                        ids.append(\
                                nested_item["id"].replace(GROUP_COUNTER_REPLACEMENT_STRING,\
                                str(i+1)))
            else:
                field_names.append(item["name"])
                ids.append(item["id"])
        csv_file.write('|'.join(field_names) + '\n')

        for submission in submissions:
            # generate data
            data = [submission.id]
            data_json = json.loads(submission.data)
            for form_id in ids:
                if form_id in data_json:
                    data.append(data_json[form_id])
                else:
                    data.append(None)
            quoted_data = [quote_strings(val) for val in data]
            csv_file.write('|'.join(str(val) for val in quoted_data) + '\n')

    return file_path

def quote_strings(val):
    """
        wraps double quotes around strings
        None is converted to empty string
        Passes everything else through
    """
    if val is None:
        return ""
    if isinstance(val, str):
        return '"{0}"'.format(val)
    return val
