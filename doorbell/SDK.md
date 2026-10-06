# Bundled SDK

| Architecture | Runtime version after Init | Verification |
| --- | --- | --- |
| amd64 | 6.1.9.48 build20230410 | Offline native smoke, read-only checks and supervised ring/dismiss on both target stations |
| aarch64 | 6.1.8.101 | Existing upstream build20211210; network-disabled container checks only |

The newer Linux64/ArmLinux64 6.1.11.30 packages are listed by Hikvision but have not been acquired. This is the newest amd64 SDK available locally, not the newest worldwide release. No newer ARM bundle is included.

## amd64 Provenance

- Official [listing](https://www.hikvision.com/en/support/tools/hitools/clf4633a00e385d6ea/) and [linked ZIP](https://assets.hikvision.com/prd/normal/all/files/202605/EN-HCNetSDKV6.1.9.48_build20230410_linux64.zip).
- Archive: `EN-HCNetSDKV6.1.9.48_build20230410_linux64.zip`, 67,235,848 bytes.
- SHA256: `8de553fb2e8dbb0ac441ee1bd73c5ecb73d720c1359396750479a6e169abf93f`.
- The hash identifies the user's downloaded archive, not a vendor signature or published checksum. The website posting date is not the package build date.
- `lib-amd64/` contains all 25 files from the archive's `lib/`, copied unchanged and hash-compared. Obsolete baseline files were removed. Keep the matched bundle intact; do not mix core, component or crypto versions.

Original notices are retained in `licenses/amd64/` and copied into the image's `/licenses/`. The user confirmed SDK redistribution permission on 2026-10-06; that is the basis for repository inclusion, not the website's general terms or the third-party notices alone. No blanket upstream-application license is asserted. The old example's license remains separately in `licenses/hikcli-LICENSE`.

## Compatibility Limits

The bundle reports OpenSSL **1.1.1u, 30 May 2023**, an old dependency rather than a current security baseline. Do not replace its OpenSSL major version without vendor support and native verification. No standalone 6.1.9.48 release note was found in the archive.

GET-only probes passed identity, idle state, reject capability and passive subscriptions on DS-KV6113-WPE1(B) V2.2.53 build 220816 and DS-KH6320-WTE1 V2.2.2 build 221129. Outdoor advertises one relay. Loaded-library mappings confirmed the candidate SDK and its own SSL/crypto libraries.

The supervised 6.1.9.48 observation with source `6297283` decoded one current outdoor ring and dismissal, produced exactly one local notification intent, rejected 17 historical callbacks, and completed checked native cleanup. Indoor ringing returned to idle after about 31 seconds; outdoor polling stayed idle. Temporary mute was restored exactly, and the user confirmed quiet. No MQTT client, physical unlock/reject/answer or deployment was involved.

MQTT/HA delivery, answered calls, outage recovery and physical controls remain separate acceptance gates. The SDK upgrade does not replace callback ABI, historical replay or ring-deduplication guards. See [configuration and behavior](DOCS.md).

## Verification And Recovery

Use the [network-disabled SDK smoke check](DEVELOPMENT.md) to verify the initialized version, callback registration, error lookup and cleanup on each architecture. Calling GetSDKBuildVersion before Init can return zero.

Commit `84991d6` retains the old amd64 6.1.6.45 bundle and pre-consolidation layout. The old inventory's 6.1.6.3 label was inaccurate. Private archives and test receipts remain outside Git; no downloaded archive, raw capture or device credential belongs in this repository.