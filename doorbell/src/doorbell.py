import json
import re
from collections import deque
from datetime import datetime
from ctypes import byref, c_byte, c_char_p, cast, sizeof
from xml.etree import ElementTree

from config import AppConfig
from sdk.hcnetsdk import DWORD, NET_DVR_CONTROL_GATEWAY, NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM_V50, NET_DVR_VIDEO_CALL_PARAM
from sdk.utils import SDKError, call_ISAPI


class Doorbell:
    def __init__(self, config: AppConfig.Doorbell, sdk):
        self.config = config
        self.sdk = sdk
        self.user_id = -1
        self.alarm_handle = -1
        self.alarm_since = None
        self.serial = ""
        self.sdk_serial = ""
        self.connected_at = 0.0
        self.firmware = ""
        self.online = False
        self.state = "unknown"
        self.generation = 0
        self.next_check = 0.0
        self.last_event = 0.0
        self.last_state_at = 0.0
        self.last_ring_state_at = 0.0
        self.ring_active = False
        self.poll_supported = True
        self.card_events = deque(maxlen=128)

    @property
    def outdoor(self) -> bool:
        return self.config.model == "DS-KV6113-WPE1(B)"

    def authenticate(self):
        if self.user_id >= 0 or self.alarm_handle >= 0:
            raise RuntimeError("Previous session requires cleanup before login")
        info = NET_DVR_DEVICEINFO_V30()
        self.user_id = self.sdk.NET_DVR_Login_V30(
            str(self.config.ip).encode("ascii"), self.config.port,
            self.config.username.encode("utf-8"), self.config.password.get_secret_value().encode("utf-8"), byref(info))
        if self.user_id < 0:
            raise SDKError(self.sdk, "Login failed")
        self.sdk_serial = bytes(info.sSerialNumber).split(b"\0", 1)[0].decode("ascii")
        self.generation += 1
        try:
            self.check_identity()
        except Exception:
            self.logout()
            raise

    def check_identity(self):
        info = ElementTree.fromstring(self._call_isapi("GET", "/ISAPI/System/deviceInfo"))
        model = "".join(info.findtext("{*}model", "").split())
        serial = info.findtext("{*}serialNumber", "").strip()
        if model != self.config.model or not re.fullmatch(r"[A-Za-z0-9_() -]{1,128}", serial):
            raise ValueError("Device identity does not match the supported configured model")
        if self.serial and serial != self.serial:
            raise ValueError("Device serial changed; refusing commands")
        self.serial = serial
        self.firmware = info.findtext("{*}firmwareVersion", "")

    def get_clock(self):
        clock = (DWORD * 6)()
        returned = DWORD()
        if not self.sdk.NET_DVR_GetDVRConfig(self.user_id, 118, -1, byref(clock), sizeof(clock), byref(returned)):
            raise SDKError(self.sdk, "Device clock is required to reject replayed alarms")
        if returned.value != sizeof(clock):
            raise ValueError("Incomplete device clock response")
        return datetime(*clock)

    def setup_alarm(self):
        self.alarm_since = self.get_clock()
        alarm = NET_DVR_SETUPALARM_PARAM_V50()
        alarm.dwSize = sizeof(alarm)
        alarm.byLevel = 1
        alarm.byAlarmInfoType = 1
        alarm.byDeployType = 1
        self.alarm_handle = self.sdk.NET_DVR_SetupAlarmChan_V50(self.user_id, byref(alarm), None, 0)
        if self.alarm_handle < 0:
            raise SDKError(self.sdk, "Event subscription failed")

    def logout(self):
        self.online = False
        self.state = "unknown"
        self.alarm_since = None
        self.card_events.clear()
        self.generation += 1
        failures = []
        for attribute, close in (
                ("alarm_handle", self.sdk.NET_DVR_CloseAlarmChan_V30),
                ("user_id", self.sdk.NET_DVR_Logout_V30)):
            handle = getattr(self, attribute)
            if handle < 0:
                continue
            try:
                if not close(handle):
                    raise SDKError(self.sdk, f"Failed to close {attribute}")
            except Exception as error:
                failures.append((attribute, error))
            else:
                setattr(self, attribute, -1)
        if failures:
            raise RuntimeError("SDK cleanup failed: " + ", ".join(attribute for attribute, _ in failures)) from failures[0][1]

    def _call_isapi(self, method: str, url: str, body: str = "") -> str:
        response = call_ISAPI(self.sdk, self.user_id, method, url, body)
        return (cast(response.lpOutBuffer, c_char_p).value or b"").decode("utf-8")

    def get_call_state(self) -> str:
        if not self.poll_supported:
            return "unknown"
        try:
            response = json.loads(self._call_isapi("GET", "/ISAPI/VideoIntercom/callStatus?format=json"))
        except SDKError as error:
            if error.args[1] != 23:
                raise
            self.poll_supported = False
            return "unknown"
        state = response.get("CallStatus", {}).get("status", "")
        return {"idle": "idle", "ring": "ringing", "ringing": "ringing", "onCall": "oncall", "oncall": "oncall"}.get(state, "unknown")

    def unlock_door(self):
        if not self.online or not self.outdoor:
            raise ValueError("Only an online, verified outdoor station can unlock")
        gateway = NET_DVR_CONTROL_GATEWAY()
        gateway.dwSize = sizeof(gateway)
        gateway.dwGatewayIndex = 1
        gateway.byCommand = 1
        gateway.wLockID = 0
        gateway.byControlSrc = (c_byte * 32)(97, 98, 99, 100)
        gateway.byControlType = 1
        if not self.sdk.NET_DVR_RemoteControl(self.user_id, 16009, byref(gateway), sizeof(gateway)):
            error = SDKError(self.sdk, "Unlock failed; command will not be retried")
            if error.args[1] != 23:
                raise error
            self._call_isapi("PUT", "/ISAPI/AccessControl/RemoteControl/door/1",
                             "<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>")

    def stop_ringing(self, state: str) -> bool:
        if not self.online or state != "ringing":
            return False
        try:
            self._call_isapi("PUT", "/ISAPI/VideoIntercom/callSignal?format=json",
                             json.dumps({"CallSignal": {"cmdType": "reject"}}))
        except SDKError as error:
            if error.args[1] != 23:
                raise
            self.callsignal(3)
        return True

    def callsignal(self, command: int):
        if command != 3:
            raise ValueError("Only rejecting an incoming call is supported")
        signal = NET_DVR_VIDEO_CALL_PARAM()
        signal.dwSize = sizeof(signal)
        signal.dwCmdType = command
        if not self.sdk.NET_DVR_SetDVRConfig(self.user_id, 16036, 1, byref(signal), sizeof(signal)):
            raise SDKError(self.sdk, "Stop ringing failed; command will not be retried")