import pytest

from bigdata_thematic_screener import openai_utils
from bigdata_thematic_screener.settings import UNSET


def test_build_client_uses_key_from_settings_not_process_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        openai_utils,
        "settings",
        openai_utils.settings.model_copy(update={"OPENAI_API_KEY": "settings-key"}),
    )

    client = openai_utils.build_client()

    assert client.api_key == "settings-key"


def test_build_client_raises_when_key_is_unset(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        openai_utils,
        "settings",
        openai_utils.settings.model_copy(update={"OPENAI_API_KEY": UNSET}),
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY is not configured"):
        openai_utils.build_client()
