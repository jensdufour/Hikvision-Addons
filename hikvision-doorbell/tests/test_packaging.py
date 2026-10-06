import ast
import json
from pathlib import Path

import yaml

from config import AppConfig


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "hikvision-doorbell"


def test_example_config_matches_runtime():
    AppConfig.model_validate(json.loads((APP / "default_config.json").read_text()))


def test_manifest_is_experimental_and_has_no_extra_access():
    manifest = yaml.safe_load((ROOT / "doorbell/config.yaml").read_text())
    assert manifest["image"] == "ghcr.io/jensdufour/hikvision-doorbell-lite"
    assert manifest["stage"] == "experimental"
    assert manifest["boot"] == "manual"
    assert set(manifest["arch"]) == {"amd64", "aarch64"}
    assert not any(manifest.get(key) for key in ("stdin", "homeassistant_api", "full_access", "map", "host_network"))
    assert set(manifest["schema"]["doorbells"][0]) == set(AppConfig.Doorbell.model_fields)
    assert set(manifest["schema"]["system"]) == set(AppConfig.System.model_fields)


def test_runtime_has_only_three_direct_dependencies():
    requirements = (APP / "requirements.txt").read_text().splitlines()
    assert {line.split("==")[0] for line in requirements} == {"pydantic", "paho-mqtt", "loguru"}
    assert "ffmpeg" not in (APP / "Dockerfile").read_text()
    assert 'io.hass.type="addon"' in (APP / "Dockerfile").read_text()
    assert "io.hass.arch=${BUILD_ARCH}" in (APP / "Dockerfile").read_text()
    assert "io.hass.version=${BUILD_VERSION}" in (APP / "Dockerfile").read_text()
    for path in (APP / "src").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"))


def test_ci_never_publishes_or_uses_device_credentials():
    workflows = list((ROOT / ".github/workflows").glob("*.yml"))
    assert len(workflows) == 1
    workflow = yaml.safe_load(workflows[0].read_text())
    assert workflow["permissions"] == {"contents": "read"}
    text = workflows[0].read_text()
    assert "--network none" in text
    assert "secrets." not in text
    assert "docker push" not in text


def test_only_one_addon_and_no_retired_commands():
    assert list(ROOT.glob("*/config.yaml")) == [ROOT / "doorbell/config.yaml"]
    assert not list(ROOT.rglob("*.next"))
    assert not (APP / "src/input.py").exists()
    assert not (APP / "src/mqtt_input.py").exists()