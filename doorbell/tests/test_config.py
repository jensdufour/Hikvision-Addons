import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from config import AppConfig, load_config


def options():
    return {"doorbells": [{"name": "Front door", "model": "DS-KV6113-WPE1(B)", "ip": "127.0.0.1",
                           "username": "test", "password": "private-test-value"}], "mqtt": {"host": "localhost"}}


def test_json_config_loads_without_network(tmp_path, mocker):
    request = mocker.patch("config.urlopen")
    path = tmp_path / "options.json"
    path.write_text(json.dumps(options()))
    config = load_config(str(path))
    assert config.system.poll_seconds == 5
    assert config.mqtt.host == "localhost"
    assert "private-test-value" not in repr(config)
    request.assert_not_called()


@pytest.mark.parametrize("change", [{"model": "OTHER"}, {"port": 0}, {"ip": "http://example.com"}, {"snapshot": True}, {"password": ""}])
def test_invalid_or_removed_options_rejected(change):
    data = options()
    data["doorbells"][0].update(change)
    with pytest.raises(ValidationError):
        AppConfig.model_validate(data)


def test_duplicate_device_rejected():
    data = options()
    data["doorbells"] *= 2
    with pytest.raises(ValidationError):
        AppConfig.model_validate(data)


def test_missing_mqtt_fails_closed(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    data = options()
    data["mqtt"] = {}
    path = tmp_path / "options.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Configure MQTT"):
        load_config(str(path))


def test_supervisor_fallback_once(tmp_path, monkeypatch, mocker):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "fake")
    data = options()
    data.pop("mqtt")
    path = tmp_path / "options.json"
    path.write_text(json.dumps(data))
    response = MagicMock()
    response.read.return_value = json.dumps({"result": "ok", "data": {"host": "broker", "port": 1883, "ssl": False, "addon": "unused"}})
    request = mocker.patch("config.urlopen")
    request.return_value.__enter__.return_value = response
    assert load_config(str(path)).mqtt.host == "broker"
    request.assert_called_once()