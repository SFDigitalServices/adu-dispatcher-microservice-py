import json
import jsend
import falcon
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .hooks import validate_access
import service.resources.jobs as jobs

# from pprint import pprint

Base = declarative_base()

class Submission(Base):
    __tablename__ = 'submission'
    id = sa.Column('id', sa.Integer, primary_key=True)
    data = sa.Column('data', sa.Text, nullable=False)
    date_created = sa.Column('date_created', sa.DateTime(timezone=True), server_default=func.now())
    external_ids = relationship("ExternalId")

    dispatch_count = {}

class ExternalId(Base):
    __tablename__ = 'external_id'
    id = sa.Column('id', sa.Integer, primary_key=True)
    submission_id = sa.Column('submission_id', sa.Integer, sa.ForeignKey('submission.id'))
    external_id = sa.Column('external_id', sa.Text, nullable=False)
    external_system = sa.Column('external_system', sa.VARCHAR(length=255), nullable=False)
    date_created = sa.Column('date_created', sa.DateTime(timezone=True), server_default=func.now())

@falcon.before(validate_access)
class SubmissionResource:
    
    def on_post(self, req, resp):
        submission = None
        try:
            # log submission to database
            submission = create_submission(self.session, req.params)
            # schedule dispatch to external systems
            jobs_scheduled = jobs.schedule(submission_obj=submission, systems_dict=jobs.external_systems)

            # return adu dispatcher id
            resp.body = json.dumps(jsend.success({
                'submission_id': submission.id,
                'job_ids': [job.id for job in jobs_scheduled]
            }))
            resp.status = falcon.HTTP_200
        except Exception as err:
            if submission is not None and hasattr(submission, 'id') and isinstance(submission.id, int):
                self.session.delete(submission)
                self.session.commit()
            resp.body = json.dumps(jsend.error("{0}".format(err)))
            resp.status = falcon.HTTP_500

def create_submission(db_session, data):
    # helper function for creating a submission
    submission = Submission(data=json.dumps(data))
    db_session.add(submission)
    db_session.commit()
    return submission

def create_external_id(db_session, submission_id, external_system, external_id):
    # helper function for creating an external id
    external_id = ExternalId(submission_id=submission_id, external_system=external_system, external_id=external_id)
    db_session.add(external_id)
    db_session.commit()
    return external_id
