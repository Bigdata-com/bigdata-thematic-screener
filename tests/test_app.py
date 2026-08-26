import io

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


def test_screen_companies_rejects_watchlist_string(client):
    response = client.post(
        "/thematic-screener",
        json={
            "theme": "Supply Chain Reshaping",
            "companies": "44118802-9104-4265-b97a-2e6d88d74893",
            "start_date": "2025-06-01",
            "end_date": "2025-08-01",
        },
    )
    assert response.status_code == 422
    assert "Watchlist is not supported" in response.text


def test_screen_companies_upload_rejects_bad_csv(client):
    bad_csv = io.BytesIO(b"NOT_AN_ID,NOT_A_NAME\nfoo,bar\n")
    response = client.post(
        "/thematic-screener/upload",
        files={"file": ("universe.csv", bad_csv, "text/csv")},
        data={
            "request": (
                '{"theme": "Theme", "start_date": "2025-06-01", "end_date": "2025-08-01"}'
            )
        },
    )
    assert response.status_code == 400


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
