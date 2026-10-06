import json
import os
from pathlib import Path
from typing import Literal
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, SecretStr, model_validator


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    class Doorbell(BaseModel):
        model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
        name: str = Field(min_length=1, max_length=80)
        model: Literal["DS-KV6113-WPE1(B)", "DS-KH6320-WTE1"]
        ip: IPvAnyAddress
        port: int = Field(default=8000, ge=1, le=65535)
        username: str = Field(min_length=1, max_length=63)
        password: SecretStr = Field(min_length=1, max_length=63)

    class MQTT(BaseModel):
        model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
        host: str = Field(min_length=1)
        port: int = Field(default=1883, ge=1, le=65535)
        ssl: bool = False
        username: str | None = None
        password: SecretStr | None = None

    class System(BaseModel):
        model_config = ConfigDict(extra="forbid")
        log_level: Literal["ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
        poll_seconds: int = Field(default=5, ge=2, le=60)

    doorbells: list[Doorbell] = Field(min_length=1, max_length=16)
    mqtt: MQTT | None = None
    system: System = Field(default_factory=System)

    @model_validator(mode="after")
    def unique_addresses(self):
        addresses = [(device.ip, device.port) for device in self.doorbells]
        if len(addresses) != len(set(addresses)):
            raise ValueError("Configure each device address only once")
        return self


def load_config(path: str | None = None) -> AppConfig:
    data = json.loads(Path(path or os.getenv("CONFIG_FILE_PATH", "/data/options.json")).read_text(encoding="utf-8"))
    if data.get("mqtt") == {}:
        data.pop("mqtt")
    config = AppConfig.model_validate(data)
    if config.mqtt is None:
        token = os.getenv("SUPERVISOR_TOKEN")
        if not token:
            raise ValueError("Configure MQTT or provide Supervisor MQTT service access")
        request = Request("http://supervisor/services/mqtt", headers={"Authorization": f"Bearer {token}"})
        with urlopen(request, timeout=5) as response:
            service = json.load(response)
        if service.get("result") != "ok":
            raise ValueError("Supervisor MQTT service is unavailable")
        mqtt = service["data"]
        config.mqtt = AppConfig.MQTT.model_validate({
            key: mqtt[key] for key in ("host", "port", "ssl", "username", "password") if key in mqtt
        })
    return config
