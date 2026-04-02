import pytest

from clipturbo_core.version import APP_NAME, APP_VERSION

fastapi = pytest.importorskip("fastapi")
TestClient = pytest.importorskip("fastapi.testclient").TestClient
create_app = pytest.importorskip("app.main").create_app


def test_health_endpoint_returns_expected_payload() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
    }
