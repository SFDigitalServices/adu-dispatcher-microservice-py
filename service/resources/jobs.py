"""Supports schedule and dispatching jobs"""

import os
import time
import json
import requests
from redis import Redis
from rq import Queue
from service.resources.db_session import create_session

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

def schedule(submission_obj, systems_dict):
    """
        queues jobs to send data to external systems
        returns array of jobs which were scheduled
    """
    if systems_dict is None:
        systems_dict = EXTERNAL_SYSTEMS

    systems_todo = systems_dict.keys()
    systems_done = [external_id.external_system for external_id in submission_obj.external_ids]
    q = get_queue() # pylint: disable=invalid-name
    jobs = []
    for todo in systems_todo:
        if todo not in systems_done:
            # data needs to be sent to external system
            print("schedule:submission_id - " + str(submission_obj.id) + ":system - " + todo)

            job = q.enqueue(dispatch, args=(todo, systems_dict[todo], submission_obj))
            jobs.append(job)
        elif systems_dict[todo]["dependants"] and len(systems_dict[todo]["dependants"]) > 0:
            # external system already done, check dependants
            jobs = jobs + schedule(submission_obj, systems_dict[todo]["dependants"])
    return jobs

def get_queue():
    """gets the queue"""
    return Queue(connection=Redis()) # pragma: no cover

def generate_payload(submission_obj, payload_template):
    # pylint: disable=unused-argument
    """generate payload from template"""
    # TODO: implement this # pylint: disable=fixme
    return {"foo": "bar"}

def dispatch(external_code, external_system, submission_obj):
    """ does the work to send data to external system
        records successes
        retry failures"""
    print("dispatch:" + external_code + ":" + str(submission_obj.id))

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
        # TODO: do this in a forked process so that it's not blocking # pylint: disable=fixme
        # something went wrong, wait and put back in queue

        timeout = external_system.get("timeout", 300)
        max_retry = external_system.get("max_retry", False)

        if max_retry:
            if external_code in submission_obj.dispatch_count:
                submission_obj.dispatch_count[external_code] += 1
            else:
                submission_obj.dispatch_count[external_code] = 1

            if submission_obj.dispatch_count[external_code] >= max_retry:
                print("hit max number of retries.  i give up.")
                return

        print("something went wrong, waiting " + str(timeout) + " secs before retrying")
        print("{0}".format(err))
        time.sleep(int(timeout))
        q = get_queue() # pylint: disable=invalid-name
        q.enqueue(dispatch, args=(external_code, external_system, submission_obj))
