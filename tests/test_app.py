import pytest
from fastapi.testclient import TestClient

from bigdata_thematic_screener.api import app as app_module
from bigdata_thematic_screener.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "version" in data
    assert isinstance(data["version"], str)


def test_etf_exposure_returns_503_without_fmp_key(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "settings",
        app_module.settings.model_copy(update={"FMP_API_KEY": ""}),
    )
    body = {
        "theme_scoring": {"X": {"ticker": "AAPL", "composite_score": 1}},
        "top_n": 1,
        "top_k": 5,
        "extra_tickers": [],
        "tickers_mode": "merge",
        "etf_symbols_filter": None,
    }
    response = client.post("/api/etf-exposure", json=body)
    assert response.status_code == 503
    assert "FMP" in response.json()["detail"]
