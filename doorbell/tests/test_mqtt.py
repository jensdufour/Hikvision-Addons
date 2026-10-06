import json
from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from config import AppConfig
from doorbell import Doorbell
from mqtt import MQTTBridge


@pytest.fixture
def bridge(mocker):
    mocker.patch("mqtt.Client")
    device = Doorbell(AppConfig.Doorbell(name="Front door", model="DS-KV6113-WPE1(B)",
                     ip="127.0.0.1", username="test", password="test"), Mock())
    device.serial = "serial1"
    device.online = True
    instance = MQTTBridge(AppConfig.MQTT(host="localhost"), [device], Queue(maxsize=2))
    instance.on_connect(instance.client, None, None, SimpleNamespace(is_failure=False), None)
    instance.refresh()
    return instance


def test_discovery_has_only_scoped_entities(bridge):
    configs = [json.loads(call.args[1]) for call in bridge.client.publish.call_args_list if call.args[0].endswith("/config")]
    assert {item["name"] for item in configs} == {"Call state", "Doorbell", "Unlock", "Stop ringing"}
    for config in configs:
        assert config["availability_mode"] == "all"
        if "command_topic" in config:
            assert config["retain"] is False
            assert config["qos"] == 0


@pytest.mark.parametrize("retained,payload,online", [(True, b"PRESS", True), (False, b"ON", True), (False, b"PRESS", False)])
def test_rejects_unsafe_messages(bridge, retained, payload, online):
    topic = next(topic for topic in bridge.commands if topic.endswith("/unlock"))
    bridge.devices[0].online = online
    bridge.on_message(None, None, SimpleNamespace(topic=topic, payload=payload, retain=retained))
    assert bridge.inbox.empty()


def test_accepts_fresh_command_once(bridge):
    topic = next(topic for topic in bridge.commands if topic.endswith("/unlock"))
    bridge.on_message(None, None, SimpleNamespace(topic=topic, payload=b"PRESS", retain=False))
    message = bridge.inbox.get_nowait()
    assert message[:3] == ("command", bridge.devices[0], "unlock")
    assert message[3] == bridge.epoch
    assert bridge.inbox.empty()


def test_reconnect_rotates_topics_and_rejects_old_command(bridge):
    old_topic = next(iter(bridge.commands))
    bridge.on_disconnect(None, None, None, None, None)
    bridge.on_connect(bridge.client, None, None, SimpleNamespace(is_failure=False), None)
    bridge.refresh()
    assert old_topic not in bridge.commands
    bridge.on_message(None, None, SimpleNamespace(topic=old_topic, payload=b"PRESS", retain=False))
    assert bridge.inbox.empty()


def test_ring_is_never_retained_or_replayed(bridge):
    bridge.client.publish.reset_mock()
    bridge.ring(bridge.devices[0])
    assert bridge.client.publish.call_args.kwargs == {"qos": 0, "retain": False}
    bridge.connected = False
    bridge.ring(bridge.devices[0])
    bridge.client.publish.assert_called_once()


def test_indoor_does_not_emit_duplicate_ring_or_unlock(bridge):
    bridge.devices[0].config.model = "DS-KH6320-WTE1"
    bridge.client.publish.reset_mock()
    bridge.ring(bridge.devices[0])
    bridge.client.publish.assert_not_called()
    bridge.discover(bridge.devices[0])
    assert bridge.client.publish.call_count == 2


def test_birth_requests_discovery(bridge):
    bridge.on_message(None, None, SimpleNamespace(topic="homeassistant/status", payload=b"online"))
    assert bridge.refresh_needed


def test_old_registration_cannot_cross_connection_epoch(bridge):
    topic, target = next(iter(bridge.commands.items()))
    bridge.epoch = "new-connection"
    bridge.commands[topic] = target
    bridge.on_message(None, None, SimpleNamespace(topic=topic, payload=b"PRESS", retain=False))
    assert bridge.inbox.empty()


def test_device_recovery_rejects_previous_command_topic(bridge):
    old_topic = next(iter(bridge.commands))
    bridge.devices[0].generation += 1
    bridge.on_message(None, None, SimpleNamespace(topic=old_topic, payload=b"PRESS", retain=False))
    assert bridge.inbox.empty()
    bridge.refresh()
    assert old_topic not in bridge.commands
    bridge.client.unsubscribe.assert_any_call(old_topic)


def test_discovery_topics_do_not_embed_raw_serial(bridge):
    bridge.devices[0].serial = "DS-KV6113-WPE1(B)-ABC123"
    bridge.client.publish.reset_mock()
    bridge.discover(bridge.devices[0])
    for call in bridge.client.publish.call_args_list:
        assert "(" not in call.args[0]
        assert ")" not in call.args[0]