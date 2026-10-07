import sys
from ctypes import byref, sizeof
from pathlib import Path
from queue import Queue

sys.path.insert(0, str(Path.cwd()))

from event import EventManager
from sdk.hcnetsdk import DWORD, LONG
from sdk.utils import loadSDK, setupSDK


if __name__ == "__main__":
    expected = sys.argv[1]
    sdk = loadSDK()
    setupSDK(sdk)
    try:
        version = sdk.NET_DVR_GetSDKBuildVersion()
        actual = ".".join(str((version >> shift) & 255) for shift in (24, 16, 8, 0))
        assert actual == expected, f"Expected SDK {expected}, got {actual}"
        events = EventManager(sdk, Queue(maxsize=1), [])
        events.start()
        clock = (DWORD * 6)()
        returned = DWORD()
        assert sizeof(clock) == 24
        assert not sdk.NET_DVR_GetDVRConfig(-1, 118, -1, byref(clock), sizeof(clock), byref(returned)), "Invalid clock session accepted"
        assert sdk.NET_DVR_GetErrorMsg(LONG(23)), "SDK error lookup failed"
        print(f"PASS: SDK {actual}, callback registration, native clock binding and error lookup")
    finally:
        assert sdk.NET_DVR_Cleanup(), "SDK cleanup failed"
        print("PASS: native SDK cleanup")