import json
import jsend
import falcon
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from sqlalchemy.sql import func

# from pprint import pprint

Base = declarative_base()

class Submission(Base):
    __tablename__ = 'submission'
    id = sa.Column('id', sa.Integer, primary_key=True)
    data = sa.Column('data', sa.Text, nullable=False)
    date_created = sa.Column('date_created', sa.DateTime(timezone=True), server_default=func.now())

class SubmissionResource:
    
    def on_post(self, req, resp):
        # log submission to database
        submission = Submission(data=json.dumps(req.params))
        self.session.add(submission)
        self.session.commit()

        # return adu dispatcher id
        resp.body = json.dumps(jsend.success({
            'submission_id': submission.id
        }))
        resp.status = falcon.HTTP_200
