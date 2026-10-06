from ctypes import POINTER, c_char_p, cast, sizeof
from struct import pack_into
from unittest.mock import Mock

from sdk.utils import call_ISAPI, setupSDK, setupFunctionTypes
from sdk.hcnetsdk import LONG, NET_DVR_ALARMER, NET_DVR_SETUPALARM_PARAM_V50


def test_alarm_header_uses_wire_32bit_user_id():
    assert sizeof(LONG) == 4
    assert NET_DVR_ALARMER.lUserID.offset == 8
    assert NET_DVR_ALARMER.sSerialNumber.offset == 12
    payload = bytearray(sizeof(NET_DVR_ALARMER))
    payload[0] = 1
    pack_into("<i", payload, 8, 7)
    serial = b"TEST-SDK-SERIAL"
    payload[12:12 + len(serial)] = serial
    alarm = NET_DVR_ALARMER.from_buffer_copy(payload)
    assert alarm.lUserID == 7
    assert bytes(alarm.sSerialNumber).split(b"\0", 1)[0] == serial


def test_subscription_signature_takes_a_pointer():
    sdk = Mock()
    setupFunctionTypes(sdk)
    assert sdk.NET_DVR_SetupAlarmChan_V50.argtypes[1] == POINTER(NET_DVR_SETUPALARM_PARAM_V50)


def test_isapi_request_length_timeout_and_buffer_lifetime():
    sdk = Mock()
    response = call_ISAPI(sdk, 7, "GET", "/ISAPI/System/deviceInfo")
    request = sdk.NET_DVR_STDXMLConfig.call_args.args[1]
    assert request.dwRequestUrlLen == len(b"GET /ISAPI/System/deviceInfo")
    assert request.dwRecvTimeOut == 2000
    assert cast(request.lpRequestUrl, c_char_p).value == b"GET /ISAPI/System/deviceInfo"
    assert len(response._buffers) == 4
    assert "lpOutBuffer" not in (response._objects or {})


def test_sdk_connection_attempts_are_bounded():
    sdk = Mock()
    setupSDK(sdk)
    sdk.NET_DVR_SetConnectTime.assert_called_once_with(2000, 1)
    sdk.NET_DVR_SetReconnect.assert_called_once_with(10000, True)