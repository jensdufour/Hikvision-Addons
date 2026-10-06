import sys
from pathlib import Path
from queue import Queue

sys.path.insert(0, str(Path.cwd()))

from event import EventManager
from sdk.hcnetsdk import LONG
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
        assert sdk.NET_DVR_GetErrorMsg(LONG(23)), "SDK error lookup failed"
        print(f"PASS: SDK {actual}, callback registration and error lookup")
    finally:
        assert sdk.NET_DVR_Cleanup(), "SDK cleanup failed"
        print("PASS: native SDK cleanup")