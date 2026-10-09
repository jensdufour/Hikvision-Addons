import json
from datetime import datetime
from ctypes import POINTER, cast, sizeof
from unittest.mock import Mock

import pytest

from config import AppConfig
from doorbell import Doorbell
from sdk.utils import SDKError
from sdk.hcnetsdk import DWORD, NET_DVR_SETUPALARM_PARAM_V50


@pytest.fixture
def device():
    config = AppConfig.Doorbell(name="Front door", model="DS-KV6113-WPE1(B)",
                                ip="127.0.0.1", username="test", password="test")
    sdk = Mock()
    sdk.NET_DVR_GetLastError.return_value = 23
    sdk.NET_DVR_GetErrorMsg.return_value = b"test error"

    def read_clock(user_id, command, channel, output, length, returned):
        assert command == 118 and channel == -1 and length == 24
        values = cast(output, POINTER(DWORD))
        for index, value in enumerate((2026, 10, 6, 12, 0, 0)):
            values[index] = value
        cast(returned, POINTER(DWORD))[0] = 24
        return True

    sdk.NET_DVR_GetDVRConfig.side_effect = read_clock
    doorbell = Doorbell(config, sdk)
    doorbell.online = True
    doorbell.user_id = 7
    return doorbell


@pytest.mark.parametrize("state", ["idle", "oncall", "unknown"])
def test_stop_ringing_ignores_non_ringing(device, mocker, state):
    request = mocker.patch.object(device, "_call_isapi")
    assert device.stop_ringing(state) is False
    request.assert_not_called()


def test_stop_ringing_rejects(device, mocker):
    request = mocker.patch.object(device, "_call_isapi")
    assert device.stop_ringing("ringing") is True
    assert json.loads(request.call_args.args[2]) == {"CallSignal": {"cmdType": "reject"}}


def test_subscription_sends_realtime_options_by_pointer(device, mocker):
    device.sdk.NET_DVR_SetupAlarmChan_V50.return_value = 9
    mocker.patch.object(device, "_call_isapi", return_value='<Time><localTime>2026-10-06T12:00:00+02:00</localTime></Time>')

    def subscribe(user_id, options_pointer, subscription, length):
        options = cast(options_pointer, POINTER(NET_DVR_SETUPALARM_PARAM_V50)).contents
        assert user_id == 7
        assert options.dwSize == sizeof(NET_DVR_SETUPALARM_PARAM_V50)
        assert options.byDeployType == 1
        assert subscription is None and length == 0
        return 9

    device.sdk.NET_DVR_SetupAlarmChan_V50.side_effect = subscribe
    device.setup_alarm()
    assert device.alarm_handle == 9
    assert device.alarm_since == datetime(2026, 10, 6, 12)


def test_subscription_uses_sdk_clock_not_isapi_wall_time(device, mocker):
    request = mocker.patch.object(device, "_call_isapi", return_value='<Time><localTime>2025-06-01T11:00:00+01:00</localTime></Time>')

    def read_clock(user_id, command, channel, output, length, returned):
        assert user_id == 7 and command == 118 and channel == -1 and length == 24
        values = cast(output, POINTER(DWORD))
        for index, value in enumerate((2025, 6, 1, 12, 0, 0)):
            values[index] = value
        cast(returned, POINTER(DWORD))[0] = 24
        return True

    device.sdk.NET_DVR_GetDVRConfig.side_effect = read_clock
    device.sdk.NET_DVR_SetupAlarmChan_V50.return_value = 9
    device.setup_alarm()
    assert device.alarm_since == datetime(2025, 6, 1, 12)
    request.assert_not_called()


def test_subscription_requires_device_clock(device, mocker):
    device.sdk.NET_DVR_GetDVRConfig.side_effect = None
    device.sdk.NET_DVR_GetDVRConfig.return_value = False
    with pytest.raises(SDKError, match="clock"):
        device.setup_alarm()
    device.sdk.NET_DVR_SetupAlarmChan_V50.assert_not_called()


@pytest.mark.parametrize("length,year", [(20, 2026), (24, 0)])
def test_subscription_rejects_incomplete_or_invalid_native_clock(device, length, year):
    original = device.sdk.NET_DVR_GetDVRConfig.side_effect

    def read_clock(user_id, command, channel, output, size, returned):
        original(user_id, command, channel, output, size, returned)
        cast(output, POINTER(DWORD))[0] = year
        cast(returned, POINTER(DWORD))[0] = length
        return True

    device.sdk.NET_DVR_GetDVRConfig.side_effect = read_clock
    with pytest.raises(ValueError):
        device.setup_alarm()
    device.sdk.NET_DVR_SetupAlarmChan_V50.assert_not_called()


@pytest.mark.parametrize("error_code", [23, 10])
def test_stop_ringing_fallback_is_only_for_unsupported(device, mocker, error_code):
    device.sdk.NET_DVR_GetLastError.return_value = error_code
    mocker.patch.object(device, "_call_isapi", side_effect=SDKError(device.sdk, "test failure"))
    fallback = mocker.patch.object(device, "callsignal")
    if error_code == 23:
        assert device.stop_ringing("ringing") is True
        fallback.assert_called_once_with(3)
    else:
        with pytest.raises(SDKError):
            device.stop_ringing("ringing")
        fallback.assert_not_called()


@pytest.mark.parametrize("online,outdoor", [(False, True), (True, False)])
def test_unlock_fails_closed(device, online, outdoor):
    device.online = online
    if not outdoor:
        device.config.model = "DS-KH6320-WTE1"
    with pytest.raises(ValueError):
        device.unlock_door()
    device.sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.mark.parametrize("error_code", [10, 23])
def test_unlock_never_retries_ambiguous_failure(device, mocker, error_code):
    device.sdk.NET_DVR_RemoteControl.return_value = False
    device.sdk.NET_DVR_GetLastError.return_value = error_code
    request = mocker.patch.object(device, "_call_isapi")
    if error_code == 23:
        device.unlock_door()
        request.assert_called_once()
    else:
        with pytest.raises(SDKError):
            device.unlock_door()
        request.assert_not_called()
    device.sdk.NET_DVR_RemoteControl.assert_called_once()


@pytest.mark.parametrize("model,serial", [("DS-KV6113-WPE1", "serial"), ("OTHER", "serial"), ("DS-KV6113-WPE1(B)", "../bad")])
def test_identity_rejects_other_models_and_invalid_serials(device, mocker, model, serial):
    mocker.patch.object(device, "_call_isapi", return_value=f"<DeviceInfo><model>{model}</model><serialNumber>{serial}</serialNumber></DeviceInfo>")
    with pytest.raises(ValueError):
        device.check_identity()


def test_identity_accepts_namespace_and_whitespace(device, mocker):
    mocker.patch.object(device, "_call_isapi", return_value='<DeviceInfo xmlns="urn:hikvision"><model>DS-KV6113-WPE1 (B)</model><serialNumber>serial1</serialNumber></DeviceInfo>')
    device.check_identity()
    assert device.serial == "serial1"


def test_identity_accepts_model_revision_in_serial(device, mocker):
    serial = "DS-KV6113-WPE1(B)-ABC123"
    mocker.patch.object(device, "_call_isapi", return_value=f"<DeviceInfo><model>DS-KV6113-WPE1(B)</model><serialNumber>{serial}</serialNumber></DeviceInfo>")
    device.check_identity()
    assert device.serial == serial


def test_identity_refuses_replacement_device(device, mocker):
    device.serial = "original"
    mocker.patch.object(device, "_call_isapi", return_value='<DeviceInfo><model>DS-KV6113-WPE1(B)</model><serialNumber>replacement</serialNumber></DeviceInfo>')
    with pytest.raises(ValueError):
        device.check_identity()


@pytest.mark.parametrize("model", ["DS-KV6113-WPE1(B)", "DS-KH6320-WTE1"])
@pytest.mark.parametrize("reported,expected", [("idle", "idle"), ("ring", "ringing"), ("ringing", "ringing"), ("onCall", "oncall"), ("unexpected", "unknown")])
def test_call_state(device, mocker, model, reported, expected):
    device.config.model = model
    mocker.patch.object(device, "_call_isapi", return_value=json.dumps({"CallStatus": {"status": reported}}))
    assert device.get_call_state() == expected


def test_unsupported_status_becomes_unknown_without_repeated_requests(device, mocker):
    request = mocker.patch.object(device, "_call_isapi", side_effect=SDKError(device.sdk, "unsupported"))
    assert device.get_call_state() == "unknown"
    assert device.get_call_state() == "unknown"
    request.assert_called_once()


def test_logout_closes_alarm_before_login_once(device):
    device.alarm_handle = 9
    device.card_events.append(("access_granted", "0012345678", datetime(2026, 10, 6, 12)))
    device.logout()
    device.logout()
    assert device.sdk.method_calls == [
        ("NET_DVR_CloseAlarmChan_V30", (9,), {}), ("NET_DVR_Logout_V30", (7,), {})]
    assert not device.online
    assert device.user_id == -1
    assert not device.card_events


@pytest.mark.parametrize("alarm_closed,logged_out", [(False, True), (True, False), (False, False)])
def test_logout_reports_failures_and_retains_failed_handles(device, alarm_closed, logged_out):
    device.alarm_handle = 9
    device.sdk.NET_DVR_CloseAlarmChan_V30.return_value = alarm_closed
    device.sdk.NET_DVR_Logout_V30.return_value = logged_out
    generation = device.generation
    with pytest.raises(RuntimeError, match="cleanup failed"):
        device.logout()
    assert device.alarm_handle == (-1 if alarm_closed else 9)
    assert device.user_id == (-1 if logged_out else 7)
    assert not device.online
    assert device.state == "unknown"
    assert device.generation > generation
    device.sdk.NET_DVR_CloseAlarmChan_V30.assert_called_once_with(9)
    device.sdk.NET_DVR_Logout_V30.assert_called_once_with(7)


def test_logout_attempts_login_cleanup_after_channel_exception(device):
    device.alarm_handle = 9
    device.sdk.NET_DVR_CloseAlarmChan_V30.side_effect = OSError("mock failure")
    device.sdk.NET_DVR_Logout_V30.return_value = True
    with pytest.raises(RuntimeError, match="cleanup failed"):
        device.logout()
    assert device.alarm_handle == 9
    assert device.user_id == -1
    device.sdk.NET_DVR_Logout_V30.assert_called_once_with(7)


def test_logout_retry_only_attempts_unresolved_handle(device):
    device.alarm_handle = 9
    device.sdk.NET_DVR_CloseAlarmChan_V30.return_value = False
    device.sdk.NET_DVR_Logout_V30.return_value = True
    with pytest.raises(RuntimeError, match="cleanup failed"):
        device.logout()
    device.sdk.NET_DVR_CloseAlarmChan_V30.return_value = True
    device.logout()
    device.logout()
    assert device.alarm_handle == device.user_id == -1
    assert device.sdk.NET_DVR_CloseAlarmChan_V30.call_count == 2
    device.sdk.NET_DVR_Logout_V30.assert_called_once_with(7)


@pytest.mark.parametrize("user_id,alarm_handle", [(7, -1), (-1, 9), (7, 9)])
def test_authenticate_refuses_unresolved_handles(device, mocker, user_id, alarm_handle):
    device.online = False
    device.user_id = user_id
    device.alarm_handle = alarm_handle
    device.sdk.NET_DVR_Login_V30.return_value = 8
    mocker.patch.object(device, "check_identity")
    with pytest.raises(RuntimeError, match="cleanup"):
        device.authenticate()
    device.sdk.NET_DVR_Login_V30.assert_not_called()