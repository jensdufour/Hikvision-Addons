# Bundled SDK

| Architecture | Runtime version after Init | Directory |
| --- | --- | --- |
| amd64 | 6.1.9.48 build20230410 | `lib-amd64/` |
| aarch64 | 6.1.8.101, upstream build20211210 | `lib-aarch64/` |

These are pinned dependency versions, not a claim that they are the latest vendor releases.

## amd64 Provenance

- Official [listing](https://www.hikvision.com/en/support/tools/hitools/clf4633a00e385d6ea/) and [linked ZIP](https://assets.hikvision.com/prd/normal/all/files/202605/EN-HCNetSDKV6.1.9.48_build20230410_linux64.zip).
- Archive: `EN-HCNetSDKV6.1.9.48_build20230410_linux64.zip`, 67,235,848 bytes.
- SHA256: `8de553fb2e8dbb0ac441ee1bd73c5ecb73d720c1359396750479a6e169abf93f`.
- The hash identifies the source archive, not a vendor signature or published checksum. The website posting date is not the package build date.
- `lib-amd64/` contains all25files from the archive's `lib/`. Keep the matched bundle intact; do not mix core, component or crypto versions.

Original notices are retained in `licenses/amd64/` and copied into the image's `/licenses/`. The example's license remains separately in `licenses/hikcli-LICENSE`. Each notice applies only to its covered component; no blanket application or SDK license is asserted here.

## Compatibility Limits

The bundle includes OpenSSL **1.1.1u, 30 May2023**, an old dependency rather than a current security baseline. Do not replace its OpenSSL major version without vendor support and native verification. No standalone6.1.9.48 release note is included in the source archive.

SDK upgrades do not replace callback ABI, historical replay or ring-deduplication guards. See [configuration and behavior](DOCS.md).

## Native Checks

Use the [network-disabled SDK smoke check](DEVELOPMENT.md) to verify the initialized version, callback registration, error lookup and cleanup on each architecture. Calling GetSDKBuildVersion before Init can return zero. Native smoke checks are not substitutes for acceptance on an installation's actual devices.