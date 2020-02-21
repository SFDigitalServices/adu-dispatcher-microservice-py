# pylint: disable=redefined-outer-name
"""Tests for microservice"""
import os
import json
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
from tasks import celery_app as queue, dispatch, send_csv

CLIENT_HEADERS = {
    "ACCESS_KEY": "1234567"
}

EXTERNAL_RESPONSE = """{
    "status": "success",
    "data": {
        "id": 100
    }
}"""

HEADERS = {"Content-Type": "application/json"}

# shortening the timeout
MOCK_EXTERNAL_SYSTEMS = {
    "dbi":{
        "type": "csv",
        "email": "csv@fake-email.com",
        "template": [
            {"name": "First name", "id": "first_name"},
            {"name": "Last name", "id": "last_name"},
            {
                "type": "grouping",
                "count": 5,
                "template": [
                    {"name": "ADU %#% type", "id": "current_unit_type_adu_%#%"},
                    {"name": "ADU %#% square footage", "id": "current_sq_ft_adu_%#%"}
                ]
            }
        ],
        "dependants": {
            "fire": {
                "env_var": "FIRE_SYSTEM_URL",
                "template": {
                    "name": "fire template"
                },
                "timeout": 3,
                "max_retry": 3
            }
        }
    },
    "planning": {
        "env_var": "PLANNING_SYSTEM_URL",
        "template": {
            "name": "planning template"
        },
        "timeout": 3,
        "max_retry": 3,
        "dependants": {
            "fake_dependant": {
                "env_var": "FIRE_SYSTEM_URL",
                "template": {
                    "name": "fire template"
                },
                "timeout": 3,
                "max_retry": 3
            }
        }
    }
}

STANDARD_SUBMISSION_JSON = {
    "first_name": "bob",
    "last_name": "smith",
    "block": "1",
    "lot": "2"
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

    with patch('tasks.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = EXTERNAL_RESPONSE

        response = client.simulate_post('/submissions',\
                json=STANDARD_SUBMISSION_JSON,\
                headers=HEADERS)
    assert response.status_code == 200

    response_json = json.loads(response.text)
    assert isinstance(response_json["data"]["submission_id"], int)

    # Test submission request with no ACCESS_KEY in header
    client_no_access_key = testing.TestClient(service.microservice.start_service())
    response = client_no_access_key.simulate_post('/submissions',\
                json=STANDARD_SUBMISSION_JSON,\
                headers=HEADERS)
    assert response.status_code == 403

    # clear out the queue
    queue.control.purge()

def test_create_submission_no_block_lot(client, mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """ Test when there is no block lot """
    body = {
        "data": "hello world"
    }

    with patch('tasks.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = EXTERNAL_RESPONSE

        response = client.simulate_post('/submissions',\
                json=body,\
                headers=HEADERS)
    assert response.status_code == 500

    # only block
    body = {
        "block": "1"
    }

    with patch('tasks.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = EXTERNAL_RESPONSE

        response = client.simulate_post('/submissions',\
                json=body,\
                headers=HEADERS)
    assert response.status_code == 500

    # only lot
    body = {
        "lot": "2"
    }

    with patch('tasks.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = EXTERNAL_RESPONSE

        response = client.simulate_post('/submissions',\
                json=body,\
                headers=HEADERS)
    assert response.status_code == 500

def test_schedule_submission_continuation(mock_external_system_env):
    # pylint: disable=unused-argument
    """
        tests the case where a submission already exists in the db
        and has an outstanding external dispatch
    """
    print("test_schedule_submission_continuation")
    session = create_session()
    db = session() # pylint: disable=invalid-name
    s = submission.create_submission(db_session=db, json_data=STANDARD_SUBMISSION_JSON) # pylint: disable=invalid-name
    s.create_external_id(db_session=db,\
            external_system="dbi",\
            external_id=123)

    with patch('tasks.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = EXTERNAL_RESPONSE

        with patch('service.resources.external_systems.MAP', MOCK_EXTERNAL_SYSTEMS):
            jobs_scheduled = tasks.schedule(s, MOCK_EXTERNAL_SYSTEMS)

    # two jobs should be scheduled, planning and fire
    assert len(jobs_scheduled) == 2
    db.close()

    # clear out the queue
    queue.control.purge()

def test_submission_post_error(client, mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """test when error in submission post"""

    with patch('tasks.schedule') as mock_schedule:
        mock_schedule.side_effect = Exception("Generic Error")

        response = client.simulate_post('/submissions',\
                json=STANDARD_SUBMISSION_JSON,\
                headers=HEADERS)
        assert response.status_code == 500

    # clear out the queue
    queue.control.purge()

def test_tasks(mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """test happy path for queue tasks"""

    session = create_session()
    db = session() # pylint: disable=invalid-name
    s = submission.create_submission(db_session=db, json_data=STANDARD_SUBMISSION_JSON) # pylint: disable=invalid-name

    with patch('service.resources.external_systems.MAP', MOCK_EXTERNAL_SYSTEMS):
        with patch('tasks.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = EXTERNAL_RESPONSE

            external_code = "planning"
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
    assert ext_ids[0].external_system == "planning"

    # clear out the queue
    queue.control.purge()

def test_external_404(mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """test that failed jobs get rescheduled"""

    session = create_session()
    db = session() # pylint: disable=invalid-name
    s = submission.create_submission(db_session=db, json_data=STANDARD_SUBMISSION_JSON) # pylint: disable=invalid-name

    with patch('service.resources.external_systems.MAP', MOCK_EXTERNAL_SYSTEMS):
        with patch('tasks.requests.post') as mock_post:
            mock_post.return_value.status_code = 404

            external_code = "planning"
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

def test_missing_env_var(mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """test that exception is thrown when env_var is missing in the mapping"""

    mapping = {
        "template": {
            "name": "planning template"
        },
        "timeout": 3,
        "max_retry": 3
    }

    session = create_session()
    db = session() # pylint: disable=invalid-name
    s = submission.create_submission(db_session=db, json_data=STANDARD_SUBMISSION_JSON) # pylint: disable=invalid-name
    with patch('tasks.requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = EXTERNAL_RESPONSE

        dispatch.s("planning",\
                external_system=mapping,\
                submission_obj=s).apply()

    # check db that no external requests were recorded
    ext_ids = db.query(submission.ExternalId)\
            .filter(submission.ExternalId.submission_id == s.id).all()
    assert len(ext_ids) == 0

    # cleanup
    db.close()
    queue.control.purge()

def test_create_csv(mock_env_access_key, mock_external_system_env):
    # pylint: disable=unused-argument
    """test creation of csv"""

    session = create_session()
    db = session() # pylint: disable=invalid-name
    s = submission.create_submission(db_session=db, json_data=STANDARD_SUBMISSION_JSON) # pylint: disable=invalid-name

    external_code = "dbi"
    send_csv.s(external_code,\
            external_system=MOCK_EXTERNAL_SYSTEMS[external_code],\
            submission_obj=s).apply()

    file_path = os.path.join(tasks.CSV_DIR, str(s.id) + ".csv")
    assert os.path.exists(file_path) == 1

    # cleanup
    db.close()
    os.remove(file_path)
