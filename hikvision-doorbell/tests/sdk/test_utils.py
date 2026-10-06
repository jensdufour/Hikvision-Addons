from ctypes import c_char_p, cast
from unittest.mock import Mock

from sdk.utils import call_ISAPI, setupSDK


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