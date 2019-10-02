# pylint: disable=redefined-outer-name
"""Tests for microservice"""
import json
import jsend
import pytest
from falcon import testing
import service.microservice
from urllib.parse import urlencode

@pytest.fixture()
def client():
    """ client fixture """
    return testing.TestClient(service.microservice.start_service())

def test_welcome(client):
    """Test welcome message response"""
    response = client.simulate_get('/welcome')
    assert response.status_code == 200

    expected_msg = jsend.success({'message': 'Welcome'})
    assert json.loads(response.content) == expected_msg

def test_default_error(client):
    """Test default error response"""
    response = client.simulate_get('/some_page_that_does_not_exist')

    assert response.status_code == 404

    expected_msg_error = jsend.error('404 - Not Found')
    assert json.loads(response.content) == expected_msg_error

def test_create_submission(client):
    body = {
        'data': '{"foo":"bar"}'
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = client.simulate_post('/submissions', body = urlencode(body), headers = headers)
    assert response.status_code == 200

    response_json = json.loads(response.text)
    assert isinstance(response_json["data"]["submission_id"], int)