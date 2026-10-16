from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app

client = TestClient(app)


class TestEndpoint:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello Hoodwinked!"}

    def test_docs_require_credentials(self):
        assert client.get("/docs").status_code == 401
        assert client.get("/openapi.json").status_code == 401

    def test_docs_reject_wrong_credentials(self):
        response = client.get("/openapi.json", auth=("nobody", "wrong"))
        assert response.status_code == 401

    def test_docs_open_with_the_configured_credentials(self):
        auth = (settings.DOCS_USERNAME, settings.DOCS_PASSWORD)
        assert client.get("/docs", auth=auth).status_code == 200
        response = client.get("/openapi.json", auth=auth)
        assert response.status_code == 200
        assert response.json()["info"]["title"] == "Hoodwinked API"
