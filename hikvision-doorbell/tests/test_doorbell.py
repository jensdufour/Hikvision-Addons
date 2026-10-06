import json
from unittest.mock import Mock

import pytest

from config import AppConfig
from doorbell import Doorbell
from sdk.utils import SDKError


@pytest.fixture
def device():
    config = AppConfig.Doorbell(name="Front door", model="DS-KV6113-WPE1(B)",
                                ip="127.0.0.1", username="test", password="test")
    sdk = Mock()
    sdk.NET_DVR_GetLastError.return_value = 23
    sdk.NET_DVR_GetErrorMsg.return_value = b"test error"
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
    device.logout()
    device.logout()
    assert device.sdk.method_calls == [
        ("NET_DVR_CloseAlarmChan_V30", (9,), {}), ("NET_DVR_Logout_V30", (7,), {})]
    assert not device.online
    assert device.user_id == -1