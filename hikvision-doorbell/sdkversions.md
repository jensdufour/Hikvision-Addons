# SDK Versions And Rehearsal

## Bundled Baseline

| Architecture | Initialized binary reports | Status |
| --- | --- | --- |
| amd64 | 6.1.6.45 | Unchanged, previously supervised ring-tested |
| aarch64 | 6.1.8.101 | Unchanged; build20211210 according to upstream inventory |

Versions were read with `NET_DVR_GetSDKBuildVersion` after initialization in network-disabled containers. The former amd64 note said 6.1.6.3; that did not match the actual binary. SDK version calls before initialization returned zero and are not a valid version check.

## Linux64 Candidate - 2026-10-06

- Official [download listing](https://www.hikvision.com/en/support/tools/hitools/clf4633a00e385d6ea/) and [vendor-linked archive](https://assets.hikvision.com/prd/normal/all/files/202605/EN-HCNetSDKV6.1.9.48_build20230410_linux64.zip).
- User downloaded `EN-HCNetSDKV6.1.9.48_build20230410_linux64.zip`: 67,235,848 bytes; SHA256 `8de553fb2e8dbb0ac441ee1bd73c5ecb73d720c1359396750479a6e169abf93f`.
- This hash identifies the local archive; it is not a vendor signature or a match against a vendor-published checksum. Windows download metadata contained only `about:internet`.
- Complete `lib/` bundle extracted outside Git and mounted read-only over `/app/lib-amd64` in the existing Debian Bookworm image. No old/new SDK component mixing, image overwrite, or repository binary replacement.
- Native initialized version is 6.1.9.48. Initialization, callback registration, error-message lookup and checked cleanup passed with networking disabled. Live process mappings confirmed the candidate SDK components and its `libssl.so.1.1`/`libcrypto.so.1.1` loaded during the device probe.
- Candidate OpenSSL reports `OpenSSL 1.1.1u 30 May 2023`. This is an old runtime dependency, not a current security baseline. Preserve the vendor bundle for compatibility; do not substitute a different OpenSSL major version blindly.

## Read-Only Device Results

| Device | Firmware | Result |
| --- | --- | --- |
| DS-KV6113-WPE1(B) | V2.2.53 | Identity, idle call status, reject capability, one relay, passive subscription and checked close/logout passed |
| DS-KH6320-WTE1 | V2.2.2 | Identity, idle call status, reject capability, passive subscription and checked close/logout passed |

Probe restricted ISAPI to an explicit GET allowlist, blocked physical-control SDK calls, required idle before subscription, and closed sessions immediately. Zero control attempts, no MQTT client, no sound changes, no firmware changes and no deployment. A new supervised ring/replay cycle was not run with this candidate; the baseline's earlier ring result must not be attributed to 6.1.9.48.

The downloaded official header also exposed the remaining `NET_DVR_GetErrorMsg` host-long mismatch, fixed separately with a 32-bit SDK LONG regression. All 97 offline tests pass, as do focused flake8, diagnostics and isolated compatibility checks for the unchanged baseline SDKs.

## Promotion Gate

Keep this candidate staged, not promoted. The archive contains developer guides, a general update-history section and third-party license notices; no standalone 6.1.9.48 release note or blanket SDK redistribution permission was established. Clarify distribution terms before adding new proprietary binaries to the public fork or publishing an image.

After separate approval, repeat the quiet supervised ring test with controls disabled, then validate MQTT delivery and reconnect behavior. Preserve replay protection and resolve the separately identified outdoor-idle/deduplication gap rather than assuming the SDK upgrade fixes it. Unlock/reject effects remain separately authorized tests.

The Chinese portal lists newer Linux64 and ArmLinux64 6.1.11.30 packages, but neither has been acquired. This Linux64 archive does not contain an ARM64 upgrade. Do not relabel it as the latest release or change the ARM baseline.

Private package, helper and result: `%LOCALAPPDATA%/PR-Zion/backups/hikvision-sdk-6.1.9.48-20261006/`. The archive is retained in the user's Downloads. Do not commit raw probes, credentials, archives or captures.