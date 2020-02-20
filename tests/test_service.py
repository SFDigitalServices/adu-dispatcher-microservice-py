# pylint: disable=redefined-outer-name
"""Tests for microservice"""
import os
import json
from urllib.parse import urlencode
from unittest.mock import patch
# import time
# import pprint
import jsend
import pytest
from falcon import testing
import tasks
import service.microservice
import service.resources.submission as submission
from service.resources.db_session import create_session
from tasks import celery_app as queue, dispatch

CLIENT_HEADERS = {
    "ACCESS_KEY": "1234567"
}

EXTERNAL_RESPONSE = """{
    "status": "success",
    "data": {
        "id": 100
    }
}"""

HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

# shortening the timeout
MOCK_EXTERNAL_SYSTEMS = {
    "dbi":{
        "env_var": "DBI_SYSTEM_URL",
        "dependants": {
            "fire": {
                "env_var": "FIRE_SYSTEM_URL",
                "template": {
                    "name": "fire template"
                },
                "timeout": 3,
                "max_retry": 3
            }
        },
        "template": {
            "name": "dbi template"
        },
        "timeout": 3,
        "max_retry": 3
    },
    "planning": {
        "env_var": "PLANNING_SYSTEM_URL",
        "template": {
            "name": "planning template"
        },
        "timeout": 3,
        "max_retry": 3
    }
}

@pytest.fixture()
def client():
    """ client fixture """
    return testing.TestClient(app=service.microservice.start_service(), headers=CLIENT_HEADERS)

@pytest.fixture(scope='session')
def celery_config():
    """ config for celery worker """
    return {
        'broker_url': os.environ['REDIS_URL'],
        'task_serializer': 'pickle',
        'accept_content': ['pickle', 'application/x-python-serialize', 'json', 'application/json']
    }

@pytest.fixture
def mock_env_access_key(monkeypatch):
    """ mock environment access key """
    monkeypatch.setenv("ACCESS_KEY", CLIENT_HEADERS["ACCESS_KEY"])

@pytest.fixture
def mock_env_no_access_key(monkeypatch):
    """ mock environment with no access key """
    monkeypatch.delenv("ACCESS_KEY", raising=False)

@pytest.fixture
def mock_external_system_env(monkeypatch):
    """ fixture to set external system urls """
    monkeypatch.setenv("DBI_SYSTEM_URL", "http://dbi.com")
    monkeypatch.setenv("FIRE_SYSTEM_URL", "http://fire.com")
    monkeypatch.setenv("PLANNING_SYSTEM_URL", "http://planning.com")

def test_welcome(client, mock_env_access_key):
    # pylint: disable=unused-argument
    # mock_env_access_key is a fixture and creates a false positive for pylint
    """Test welcome message response"""
    response = client.simulate_get('/welcome')
    assert response.status_code == 200

    expected_msg = jsend.success({'message': 'Welcome'})
    assert json.loads(response.content) == expected_msg

    # Test welcome request with no ACCESS_KEY in header
    client_no_access_key = testing.TestClient(service.microservice.start_service())
    response = client_no_access_key.simulate_get('/welcome')
    assert response.status_code == 403

def test_welcome_no_access_key(client, mock_env_no_access_key):
    # pylint: disable=unused-argument
    # mock_env_no_access_key is a fixture and creates a false positive for pylint
    """Test welcome request with no ACCESS_key environment var set"""
    response = client.simulate_get('/welcome')
    assert response.status_code == 403


def test_default_error(client, mock_env_access_key):
    # pylint: disable=unused-argument
    """Test default error response"""
    response = client.simulate_get('/some_page_that_does_not_exist')

    assert response.status_code == 404

    expected_msg_error = jsend.error('404 - Not Found')
    assert json.loads(response.content) == expected_msg_error

def test_create_submission(client, mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """ Test submission post """
    body = {
        'data': '{"foo":"bar"}'
    }

    with patch('tasks.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = EXTERNAL_RESPONSE

        response = client.simulate_post('/submissions',\
                body=urlencode(body),\
                headers=HEADERS)
    assert response.status_code == 200

    response_json = json.loads(response.text)
    assert isinstance(response_json["data"]["submission_id"], int)

    # Test submission request with no ACCESS_KEY in header
    client_no_access_key = testing.TestClient(service.microservice.start_service())
    response = client_no_access_key.simulate_post('/submissions',\
                body=urlencode(body),\
                headers=HEADERS)
    assert response.status_code == 403

    # clear out the queue
    queue.control.purge()

def test_schedule_submission_continuation(mock_external_system_env):
    # pylint: disable=unused-argument
    """
        tests the case where a submission already exists in the db
        and has an outstanding external dispatch
    """
    session = create_session()
    db = session() # pylint: disable=invalid-name
    s = submission.create_submission(db_session=db, json_data={"sample": "12345"}) # pylint: disable=invalid-name
    s.create_external_id(db_session=db,\
            external_system="dbi",\
            external_id=123)

    with patch('tasks.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = EXTERNAL_RESPONSE

        jobs_scheduled = tasks.schedule(s, None)

    # two jobs should be scheduled, planning and fire
    assert len(jobs_scheduled) == 2
    db.close()

    # clear out the queue
    queue.control.purge()

def test_submission_post_error(client, mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """test when error in submission post"""
    body = {
        'data': '{"test": "test_db_down"}'
    }

    with patch('tasks.schedule') as mock_schedule:
        mock_schedule.side_effect = Exception("Generic Error")

        response = client.simulate_post('/submissions', body=urlencode(body), headers=HEADERS)
        assert response.status_code == 500

    # clear out the queue
    queue.control.purge()

def test_tasks(mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """test happy path for queue tasks"""

    session = create_session()
    db = session() # pylint: disable=invalid-name
    s = submission.create_submission(db_session=db, json_data={"sample": "test_tasks"}) # pylint: disable=invalid-name

    with patch('service.resources.external_systems.MAP', MOCK_EXTERNAL_SYSTEMS):
        with patch('tasks.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = EXTERNAL_RESPONSE

            external_code = "dbi"
            dispatch.s(external_code=external_code,\
                    external_system=MOCK_EXTERNAL_SYSTEMS[external_code],\
                    submission_obj=s).apply()

    # verify submission exists in db
    sub = db.query(submission.Submission).filter(submission.Submission.id == s.id)
    assert sub is not None

    # verify external post was recorded in db
    ext_ids = db.query(submission.ExternalId)\
            .filter(submission.ExternalId.submission_id == s.id).all()
    assert len(ext_ids) == 1
    assert ext_ids[0].external_system == "dbi"
    # time.sleep(3)
    # celery_inspect = queue.control.inspect()
    # pprint.pprint(celery_inspect.reserved())
    # pprint.pprint(celery_inspect.registered())
    # pprint.pprint(celery_inspect.scheduled())
    # pprint.pprint(celery_inspect.active())

    # clear out the queue
    queue.control.purge()

def test_external_404(mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """test that failed jobs get rescheduled"""

    session = create_session()
    db = session() # pylint: disable=invalid-name
    s = submission.create_submission(db_session=db, json_data={"sample": "test_external_404"}) # pylint: disable=invalid-name

    with patch('service.resources.external_systems.MAP', MOCK_EXTERNAL_SYSTEMS):
        with patch('tasks.requests.post') as mock_post:
            mock_post.return_value.status_code = 404

            external_code = "dbi"
            # schedule(s, MOCK_EXTERNAL_SYSTEMS)
            # monkeypatch.setattr(queue.task.Context, 'called_directly', False)
            dispatch.s(external_code=external_code,\
                    external_system=MOCK_EXTERNAL_SYSTEMS[external_code],\
                    submission_obj=s).apply()

    celery_inspect = queue.control.inspect()
    jobs_reserved = celery_inspect.reserved()
    # nothing left in the queue since gave up after 3 retries
    if jobs_reserved:
        for worker in jobs_reserved:
            assert not jobs_reserved[worker]
    else:
        assert jobs_reserved is None

    # the submission still exists in the db, but with no
    # associated external ids since external posts were unsuccessful
    sub = db.query(submission.Submission).filter(submission.Submission.id == s.id).first()
    assert sub is not None

    ext_ids = db.query(submission.ExternalId)\
            .filter(submission.ExternalId.submission_id == s.id).all()
    assert len(ext_ids) == 0

    # cleanup
    db.close()
    queue.control.purge()
