from ctypes import sizeof, string_at
from datetime import datetime
from queue import Full
from time import monotonic

from loguru import logger
from sdk.hcnetsdk import COMM_ALARM_VIDEO_INTERCOM, NET_DVR_VIDEO_INTERCOM_ALARM, fMessageCallBack
from sdk.utils import SDKError


class EventManager:
    def __init__(self, sdk, inbox, devices):
        self.sdk = sdk
        self.inbox = inbox
        self.devices = devices
        self.callback = fMessageCallBack(self.receive)

    def start(self):
        if not self.sdk.NET_DVR_SetDVRMessageCallBack_V50(0, self.callback, None):
            raise SDKError(self.sdk, "Cannot subscribe to SDK events")

    def receive(self, command, device_pointer, alarm_pointer, length, user_pointer):
        if command != COMM_ALARM_VIDEO_INTERCOM or not device_pointer or not alarm_pointer:
            return True
        if length < sizeof(NET_DVR_VIDEO_INTERCOM_ALARM):
            return True
        try:
            device = device_pointer.contents
            if not device.byUserIDValid:
                return True
            alarm = NET_DVR_VIDEO_INTERCOM_ALARM.from_buffer_copy(
                string_at(alarm_pointer, sizeof(NET_DVR_VIDEO_INTERCOM_ALARM)))
            state = {17: "ringing", 18: "idle"}.get(alarm.byAlarmType)
            if state:
                serial = bytes(device.sSerialNumber).split(b"\0", 1)[0].decode("ascii")
                owner = next((item for item in self.devices if item.user_id == device.lUserID
                              and item.sdk_serial == serial), None)
                if owner is None or owner.alarm_since is None:
                    return True
                stamp = alarm.struTime
                occurred = datetime(stamp.wYear, stamp.byMonth, stamp.byDay, stamp.byHour, stamp.byMinute, stamp.bySecond)
                if occurred < owner.alarm_since:
                    logger.debug("Ignoring replayed alarm from {}", owner.config.name)
                    return True
                self.inbox.put_nowait(("alarm", int(device.lUserID), serial, state, monotonic()))
        except (Full, UnicodeError, ValueError):
            logger.warning("Discarded an invalid or overflowing SDK event")
        except Exception:
            logger.error("SDK event decoding failed")
        return True