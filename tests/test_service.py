# pylint: disable=redefined-outer-name
"""Tests for microservice"""
import json
import jsend
import pytest
from falcon import testing
import service.microservice
from urllib.parse import urlencode
from fakeredis import FakeStrictRedis
from redis import Redis
from rq import Queue
from rq.registry import FinishedJobRegistry
from unittest.mock import patch
from service.resources.jobs import schedule
import service.resources.submission as submission
from service.resources.db_session import create_session

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

@pytest.fixture()
def client():
    """ client fixture """
    return testing.TestClient(app=service.microservice.start_service(), headers=CLIENT_HEADERS)

@pytest.fixture()
def queue():
    """ redis queue """
    return Queue(is_async=False, connection=FakeStrictRedis())

@pytest.fixture
def mock_env_access_key(monkeypatch):
    monkeypatch.setenv("ACCESS_KEY", CLIENT_HEADERS["ACCESS_KEY"])

@pytest.fixture
def mock_env_no_access_key(monkeypatch):
    monkeypatch.delenv("ACCESS_KEY", raising=False)

@pytest.fixture
def mock_external_system_env(monkeypatch):
    monkeypatch.setenv("DBI_SYSTEM_URL", "http://dbi.com")
    monkeypatch.setenv("FIRE_SYSTEM_URL", "http://fire.com")
    monkeypatch.setenv("PLANNING_SYSTEM_URL", "http://planning.com")

def test_welcome(client, mock_env_access_key):
    """Test welcome message response"""
    response = client.simulate_get('/welcome')
    assert response.status_code == 200

    expected_msg = jsend.success({'message': 'Welcome'})
    assert json.loads(response.content) == expected_msg

    """Test welcome request with no ACCESS_KEY in header"""
    client_no_access_key = testing.TestClient(service.microservice.start_service())
    response = client_no_access_key.simulate_get('/welcome')
    assert response.status_code == 403

def test_welcome_no_access_key(client, mock_env_no_access_key):
    """Test welcome request with no ACCESS_key environment var set"""
    response = client.simulate_get('/welcome')
    assert response.status_code == 403


def test_default_error(client, mock_env_access_key):
    """Test default error response"""
    response = client.simulate_get('/some_page_that_does_not_exist')

    assert response.status_code == 404

    expected_msg_error = jsend.error('404 - Not Found')
    assert json.loads(response.content) == expected_msg_error

def test_create_submission(client, queue, mock_env_access_key, mock_external_system_env):
    body = {
        'data': '{"foo":"bar"}'
    }

    with patch('service.resources.jobs.get_queue') as mock_queue:
        mock_queue.return_value = queue

        with patch('service.resources.jobs.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = EXTERNAL_RESPONSE
            # mock_post.return_value.json.return_value = json.loads(EXTERNAL_RESPONSE)
            response = client.simulate_post('/submissions', body = urlencode(body), headers = HEADERS)
    assert response.status_code == 200

    response_json = json.loads(response.text)
    assert isinstance(response_json["data"]["submission_id"], int)

    """Test submission request with no ACCESS_KEY in header"""
    client_no_access_key = testing.TestClient(service.microservice.start_service())
    response = client_no_access_key.simulate_post('/submissions', body = urlencode(body), headers = HEADERS)
    assert response.status_code == 403

def test_schedule_submission_continuation(queue, mock_external_system_env):
    # tests the case where a submission already exists in the db and has an outstanding external dispatch
    session = create_session()
    db = session()
    s = submission.create_submission(db_session=db, data={"sample": "12345"})
    submission.create_external_id(db_session=db, submission_id=s.id, external_system="dbi", external_id=123)

    with patch('service.resources.jobs.get_queue') as mock_queue:
        mock_queue.return_value = queue

        with patch('service.resources.jobs.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = EXTERNAL_RESPONSE

            jobs_scheduled = schedule(s)

    # two jobs should be scheduled, planning and fire
    assert len(jobs_scheduled) == 2
    db.close()

def test_external_404(client, queue, mock_env_access_key, mock_external_system_env):
    # test that failed jobs get rescheduled
    body = {
        'data': '{"foo": "foo"}'
    }

    with patch('service.resources.jobs.get_queue') as mock_queue:
        mock_queue.return_value = queue
        mock_external_systems = {
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
        with patch('service.resources.submission.jobs.external_systems', mock_external_systems):
            with patch('service.resources.jobs.requests.post') as mock_post:
                mock_post.return_value.status_code = 404
                response = client.simulate_post('/submissions', body = urlencode(body), headers = HEADERS)

            assert response.status_code == 200

            response_json = json.loads(response.text)
            # top level external systems should have been scheduled
            assert len(response_json["data"]["job_ids"]) == len(mock_external_systems.keys())
