import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'S3-vibe Local File Host' in response.data

def test_upload_endpoint_without_file(client):
    response = client.post('/upload')
    assert response.status_code == 400
    assert b'No file part' in response.data

def test_upload_endpoint_with_invalid_file(client):
    data = {'file': (b'invalid', 'test.txt')}
    response = client.post('/upload', data=data)
    assert response.status_code == 400
    assert b'File type not allowed' in response.data 