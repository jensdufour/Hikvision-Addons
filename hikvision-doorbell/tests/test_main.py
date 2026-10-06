from ctypes import cast, pointer, sizeof
from datetime import datetime
from queue import Queue
from time import monotonic
from unittest.mock import Mock

import pytest

from config import AppConfig
from doorbell import Doorbell
from event import EventManager
from main import check_device, handle_message, report_state
from sdk.hcnetsdk import COMM_ALARM_VIDEO_INTERCOM, NET_DVR_ALARMER, NET_DVR_VIDEO_INTERCOM_ALARM, MessageCallbackAlarmInfoUnion, POINTER


@pytest.fixture
def device():
    config = AppConfig.Doorbell(name="Front door", model="DS-KV6113-WPE1(B)",
                                ip="127.0.0.1", username="test", password="test")
    result = Doorbell(config, Mock())
    result.online = True
    result.serial = "serial"
    result.sdk_serial = "sdkserial"
    result.user_id = 7
    return result


def test_ring_episode_deduplication_and_no_initial_replay(device):
    bridge = Mock()
    for state in ("idle", "ringing", "ringing", "unknown", "ringing"):
        report_state(device, state, bridge)
    bridge.ring.assert_called_once_with(device)
    report_state(device, "idle", bridge)
    report_state(device, "ringing", bridge)
    assert bridge.ring.call_count == 2
    report_state(device, "idle", bridge)
    report_state(device, "ringing", bridge, initial=True)
    assert bridge.ring.call_count == 2


@pytest.mark.parametrize("failure", ["expired", "mqtt_reconnected", "device_reconnected", "offline", "broker_offline"])
def test_stale_command_discarded(device, failure):
    bridge = Mock(connected=True, epoch="current")
    command = ["command", device, "unlock", "current", device.generation, monotonic()]
    if failure == "expired":
        command[5] -= 10
    elif failure == "mqtt_reconnected":
        command[3] = "old"
    elif failure == "device_reconnected":
        command[4] -= 1
    elif failure == "offline":
        device.online = False
    else:
        bridge.connected = False
    handle_message(command, [device], bridge)
    device.sdk.NET_DVR_RemoteControl.assert_not_called()


def test_fresh_unlock_runs_once_and_is_not_retried(device, mocker):
    unlock = mocker.patch.object(device, "unlock_door", side_effect=RuntimeError("ambiguous"))
    bridge = Mock(connected=True, epoch="current")
    command = ("command", device, "unlock", "current", device.generation, monotonic())
    handle_message(command, [device], bridge)
    handle_message(command, [device], bridge)
    unlock.assert_called_once()
    assert not device.online


def test_stop_ringing_checks_current_state(device, mocker):
    mocker.patch.object(device, "get_call_state", return_value="oncall")
    stop = mocker.patch.object(device, "stop_ringing")
    handle_message(("command", device, "stop_ringing", "current", device.generation, monotonic()),
                   [device], Mock(connected=True, epoch="current"))
    stop.assert_called_once_with("oncall")


@pytest.mark.parametrize("model", ["DS-KV6113-WPE1(B)", "DS-KH6320-WTE1"])
def test_stop_ringing_accepts_advertised_ring_status(device, mocker, model):
    device.config.model = model
    request = mocker.patch.object(device, "_call_isapi", side_effect=['{"CallStatus":{"status":"ring"}}', '{}'])
    handle_message(("command", device, "stop_ringing", "current", device.generation, monotonic()),
                   [device], Mock(connected=True, epoch="current"))
    assert request.call_count == 2
    assert request.call_args_list[0].args == ("GET", "/ISAPI/VideoIntercom/callStatus?format=json")
    assert request.call_args_list[1].args == (
        "PUT", "/ISAPI/VideoIntercom/callSignal?format=json", '{"CallSignal": {"cmdType": "reject"}}')
    device.sdk.NET_DVR_SetDVRConfig.assert_not_called()


def test_device_recovery_closes_failed_session(device, mocker):
    device.online = False
    mocker.patch.object(device, "authenticate")
    mocker.patch.object(device, "get_call_state", return_value="idle")
    setup = mocker.patch.object(device, "setup_alarm", side_effect=RuntimeError("offline"))
    bridge = Mock()
    check_device(device, [device], bridge, 5)
    assert not device.online
    assert device.next_check > monotonic() + 20
    setup.side_effect = None
    check_device(device, [device], bridge, 5)
    assert device.online
    assert bridge.refresh_needed


@pytest.mark.parametrize("failure_path", ["health", "command"])
def test_cleanup_failure_keeps_device_offline_and_retries_bounded(device, mocker, failure_path):
    device.alarm_handle = 9
    device.sdk.NET_DVR_CloseAlarmChan_V30.return_value = False
    device.sdk.NET_DVR_Logout_V30.return_value = False
    mocker.patch.object(device, "check_identity", side_effect=RuntimeError("mock disconnected"))
    mocker.patch.object(device, "unlock_door", side_effect=RuntimeError("mock uncertain result"))
    report_error = mocker.patch("main.logger.error")
    bridge = Mock(connected=True, epoch="current")
    if failure_path == "health":
        check_device(device, [device], bridge, 5)
    else:
        handle_message(("command", device, "unlock", "current", device.generation, monotonic()), [device], bridge)
    assert not device.online
    assert device.state == "unknown"
    assert device.user_id == 7 and device.alarm_handle == 9
    assert device.next_check > monotonic() + 20
    bridge.publish_state.assert_called_with(device)
    report_error.assert_any_call("Cleanup incomplete for {}: {}", device.config.name, mocker.ANY)


def test_recovery_cleans_pending_handles_before_next_login(device, mocker):
    device.online = False
    device.alarm_handle = 9
    device.sdk.NET_DVR_CloseAlarmChan_V30.return_value = True
    device.sdk.NET_DVR_Logout_V30.return_value = True
    device.sdk.NET_DVR_Login_V30.return_value = 8
    mocker.patch.object(device, "check_identity")
    mocker.patch.object(device, "get_call_state", return_value="idle")
    mocker.patch.object(device, "setup_alarm")
    bridge = Mock()
    check_device(device, [device], bridge, 5)
    assert device.user_id == device.alarm_handle == -1
    assert not device.online
    device.sdk.NET_DVR_Login_V30.assert_not_called()
    check_device(device, [device], bridge, 5)
    assert device.online
    device.sdk.NET_DVR_Login_V30.assert_called_once()


def test_old_event_cannot_override_newer_poll(device):
    report_state(device, "oncall", Mock(), observed=20)
    handle_message(("alarm", 7, "sdkserial", "ringing", 19), [device], Mock())
    assert device.state == "oncall"


@pytest.mark.parametrize("polled_state", ["idle", "oncall", "ringing"])
def test_queued_ring_delivered_before_newer_poll(device, mocker, polled_state):
    alarms = Queue()
    alarms.put(("alarm", 7, "sdkserial", "ringing", 19))
    alarms.put(("alarm", 7, "sdkserial", "ringing", 19.5))
    mocker.patch("main.monotonic", return_value=20)
    mocker.patch.object(device, "check_identity")
    mocker.patch.object(device, "get_call_state", return_value=polled_state)
    bridge = Mock()
    check_device(device, [device], bridge, 5, alarms)
    bridge.ring.assert_called_once_with(device)
    assert device.state == polled_state
    assert device.last_state_at == 20
    assert alarms.empty()


def test_queued_ring_episodes_each_delivered_before_poll(device, mocker):
    alarms = Queue()
    for state, observed in [("ringing", 17), ("idle", 18), ("ringing", 19)]:
        alarms.put(("alarm", 7, "sdkserial", state, observed))
    mocker.patch("main.monotonic", return_value=20)
    mocker.patch.object(device, "check_identity")
    mocker.patch.object(device, "get_call_state", return_value="idle")
    bridge = Mock()
    check_device(device, [device], bridge, 5, alarms)
    assert bridge.ring.call_count == 2
    assert device.state == "idle"


def test_event_received_during_poll_keeps_newer_state(device, mocker):
    alarms = Queue()

    def poll_state():
        alarms.put(("alarm", 7, "sdkserial", "ringing", 21))
        return "idle"

    mocker.patch("main.monotonic", return_value=20)
    mocker.patch.object(device, "check_identity")
    mocker.patch.object(device, "get_call_state", side_effect=poll_state)
    bridge = Mock()
    check_device(device, [device], bridge, 5, alarms)
    bridge.ring.assert_called_once_with(device)
    assert device.state == "ringing"
    assert device.last_state_at == 21


def test_callback_copies_values_before_vendor_buffer_reused(device):
    inbox = Queue()
    device.alarm_since = datetime(2026, 10, 6, 12)
    manager = EventManager(Mock(), inbox, [device])
    source = NET_DVR_ALARMER()
    source.byUserIDValid = 1
    source.lUserID = 7
    for index, value in enumerate(b"sdkserial"):
        source.sSerialNumber[index] = value
    alarm = NET_DVR_VIDEO_INTERCOM_ALARM()
    alarm.byAlarmType = 17
    alarm.struTime.wYear = 2026
    alarm.struTime.byMonth = 10
    alarm.struTime.byDay = 6
    alarm.struTime.byHour = 12
    alarm_pointer = cast(pointer(alarm), POINTER(MessageCallbackAlarmInfoUnion))
    assert manager.receive(COMM_ALARM_VIDEO_INTERCOM, pointer(source), alarm_pointer, sizeof(alarm), None)
    source.lUserID = 99
    alarm.byAlarmType = 18
    handle_message(inbox.get_nowait(), [device], Mock())
    assert device.state == "ringing"


def test_callback_rejects_truncated_buffers():
    inbox = Queue()
    manager = EventManager(Mock(), inbox, [])
    manager.receive(COMM_ALARM_VIDEO_INTERCOM, pointer(NET_DVR_ALARMER()),
                    cast(pointer(NET_DVR_VIDEO_INTERCOM_ALARM()), POINTER(MessageCallbackAlarmInfoUnion)), 1, None)
    assert inbox.empty()


@pytest.mark.parametrize("day,expected", [(2, False), (6, True), (0, False)])
def test_callback_filters_historical_and_invalid_timestamps(device, day, expected):
    inbox = Queue()
    device.alarm_since = datetime(2026, 10, 6, 12)
    manager = EventManager(Mock(), inbox, [device])
    source = NET_DVR_ALARMER()
    source.byUserIDValid = 1
    source.lUserID = 7
    for index, value in enumerate(b"sdkserial"):
        source.sSerialNumber[index] = value
    alarm = NET_DVR_VIDEO_INTERCOM_ALARM()
    alarm.byAlarmType = 17
    alarm.struTime.wYear = 2026
    alarm.struTime.byMonth = 10
    alarm.struTime.byDay = day
    alarm.struTime.byHour = 12
    manager.receive(COMM_ALARM_VIDEO_INTERCOM, pointer(source),
                    cast(pointer(alarm), POINTER(MessageCallbackAlarmInfoUnion)), sizeof(alarm), None)
    assert (not inbox.empty()) is expected


def test_unsupported_poll_does_not_supersede_queued_sdk_event(device, mocker):
    device.poll_supported = False
    device.last_state_at = 10
    mocker.patch.object(device, "check_identity")
    mocker.patch.object(device, "get_call_state", return_value="unknown")
    check_device(device, [device], Mock(), 5)
    handle_message(("alarm", 7, "sdkserial", "ringing", 11), [device], Mock())
    assert device.state == "ringing"


@pytest.mark.parametrize("cleanup_succeeds", [True, False])
def test_shutdown_drops_waiting_command(device, mocker, cleanup_succeeds):
    import main as application
    from threading import Event

    stopping = Event()
    inbox = Mock()
    device.sdk.NET_DVR_Logout_V30.return_value = cleanup_succeeds

    def stop_during_read(**kwargs):
        stopping.set()
        return ("command", device, "unlock", "current", device.generation, monotonic())

    inbox.get.side_effect = stop_during_read
    device.next_check = float("inf")
    mocker.patch("main.Event", return_value=stopping)
    mocker.patch("main.Queue", side_effect=[inbox, Queue()])
    mocker.patch("main.signal.signal")
    mocker.patch("main.load_config", return_value=AppConfig(doorbells=[device.config], mqtt={"host": "localhost"}))
    mocker.patch("main.loadSDK", return_value=Mock())
    mocker.patch("main.setupSDK")
    cleanup = mocker.patch("main.shutdownSDK")
    mocker.patch("main.Doorbell", return_value=device)
    mocker.patch("main.EventManager")
    bridge = Mock(refresh_needed=False)
    mocker.patch("main.MQTTBridge", return_value=bridge)
    command = mocker.patch("main.handle_message")
    application.main()
    command.assert_not_called()
    bridge.stop.assert_called_once()
    cleanup.assert_called_once()