"""Submission Data Model"""

import json
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

BASE = declarative_base()

class Submission(BASE):
    # pylint: disable=too-few-public-methods
    """Map Submission object to db"""

    __tablename__ = 'submission'
    id = sa.Column('id', sa.Integer, primary_key=True)
    data = sa.Column('data', sa.Text, nullable=False)
    date_created = sa.Column('date_created', sa.DateTime(timezone=True), server_default=func.now())
    csv_date_processed = sa.Column('csv_date_processed', sa.DateTime(timezone=True))
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

def create_submission(db_session, json_data):
    '''helper function for creating a submission'''
    submission = Submission(data=json.dumps(json_data))
    db_session.add(submission)
    db_session.commit()
    return submission
