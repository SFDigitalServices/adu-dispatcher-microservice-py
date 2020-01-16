"""Submission Data Model"""

# import sys, traceback
import json
import jsend
import falcon
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import tasks
from .hooks import validate_access

# from pprint import pprint

BASE = declarative_base()

class Submission(BASE):
    # pylint: disable=too-few-public-methods
    """Map Submission object to db"""

    __tablename__ = 'submission'
    id = sa.Column('id', sa.Integer, primary_key=True)
    data = sa.Column('data', sa.Text, nullable=False)
    date_created = sa.Column('date_created', sa.DateTime(timezone=True), server_default=func.now())
    external_ids = relationship("ExternalId")

    dispatch_count = {}

    def create_external_id(self, db_session, external_system, external_id):
        '''helper function for creating an external id'''
        external_id_obj = ExternalId(submission_id=self.id,\
                external_system=external_system,\
                external_id=external_id)
        db_session.add(external_id_obj)
        db_session.commit()
        return external_id_obj

class ExternalId(BASE):
    # pylint: disable=too-few-public-methods
    """Map ExternalID object to db"""

    __tablename__ = 'external_id'
    id = sa.Column('id', sa.Integer, primary_key=True)
    submission_id = sa.Column('submission_id', sa.Integer, sa.ForeignKey('submission.id'))
    external_id = sa.Column('external_id', sa.Text, nullable=False)
    external_system = sa.Column('external_system', sa.VARCHAR(length=255), nullable=False)
    date_created = sa.Column('date_created', sa.DateTime(timezone=True), server_default=func.now())

@falcon.before(validate_access)
class SubmissionResource:
    # pylint: disable=too-few-public-methods
    """Integrate Submission Data Object to Falcon Framework """

    def on_post(self, req, resp):
        """Handle Submission POST requests"""
        submission = None
        try:
            # log submission to database
            submission = create_submission(self.session, req.params) # pylint: disable=no-member
            # schedule dispatch to external systems
            jobs_scheduled = tasks.schedule(submission_obj=submission,\
                systems_dict=tasks.EXTERNAL_SYSTEMS)

            # return adu dispatcher id
            resp.body = json.dumps(jsend.success({
                'submission_id': submission.id,
                'job_ids': [job.id for job in jobs_scheduled]
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

def create_submission(db_session, data):
    '''helper function for creating a submission'''
    submission = Submission(data=json.dumps(data))
    db_session.add(submission)
    db_session.commit()
    return submission
