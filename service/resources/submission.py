"""Submission Endpoint"""

# import sys, traceback
import json
import jsend
import falcon
import tasks
from service.resources.external_systems import MAP
from service.resources.submission_model import create_submission
from .hooks import validate_access

# from pprint import pprint

@falcon.before(validate_access)
class SubmissionResource:
    # pylint: disable=too-few-public-methods
    """Integrate Submission Data Object to Falcon Framework """

    def on_post(self, req, resp):
        """Handle Submission POST requests"""
        submission = None
        try:
            json_params = req.media
            validate(json_params)
            # log submission to database
            submission = create_submission(self.session, json_params) # pylint: disable=no-member
            # schedule dispatch to external systems
            jobs_scheduled = tasks.schedule(submission_obj=submission,\
                systems_dict=MAP)

            # return adu dispatcher id
            resp.body = json.dumps(jsend.success({
                'submission_id': submission.id,
                'job_ids': [job.id for job in jobs_scheduled],
                'params': json.dumps(req.media)
            }))
            resp.status = falcon.HTTP_200
        except Exception as err: # pylint: disable=broad-except
            if (submission is not None
                    and hasattr(submission, 'id')
                    and isinstance(submission.id, int)):
                self.session.delete(submission) # pylint: disable=no-member
                self.session.commit() # pylint: disable=no-member
            # print("caught error in submission on_post")
            # print("traceback:")
            # traceback.print_exc(file=sys.stdout)
            print("error:")
            print("{0}".format(err))
            resp.body = json.dumps(jsend.error("{0}".format(err)))
            resp.status = falcon.HTTP_500

def validate(json_data):
    '''enforce validation rules'''
    if "block" not in json_data or not json_data["block"] or\
                "lot" not in json_data or not json_data["lot"]:
        raise Exception("Block and lot are required fields")
