"""Main application module"""
import os
import json
import jsend
import sentry_sdk
import falcon
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from .resources.welcome import Welcome
from .resources.submission import SubmissionResource

def start_service():
    """Start this service
    set SENTRY_DSN environmental variable to enable logging with Sentry
    """
    # Initialize Sentry
    sentry_sdk.init(os.environ.get('SENTRY_DSN'))
    # Database
    db_engine = sa.create_engine(os.environ.get('DATABASE_URL'), echo=True)
    session = sessionmaker(bind=db_engine)

    # Initialize Falcon
    api = falcon.API(middleware=[SQLAlchemySessionManager(session)])
    api.req_options.auto_parse_form_urlencoded = True
    api.req_options.strip_url_path_trailing_slash = True

    api.add_route('/welcome', Welcome())
    api.add_route('/submissions', SubmissionResource())
    api.add_sink(default_error, '')
    return api

def default_error(_req, resp):
    """Handle default error"""
    resp.status = falcon.HTTP_404
    msg_error = jsend.error('404 - Not Found')

    sentry_sdk.capture_message(msg_error)
    resp.body = json.dumps(msg_error)

class SQLAlchemySessionManager:
    """
    Create a session for every request and close it when the request ends.
    """

    def __init__(self, Session):
        self.Session = Session

    def process_resource(self, req, resp, resource, params):
        resource.session = self.Session()

    def process_response(self, req, resp, resource, req_succeeded):
        if hasattr(resource, 'session'):
            resource.session.close()
