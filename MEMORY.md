# Hikvision Doorbell Lite Decisions

## Scope And Ownership

- 2026-10-06 pilot review: user authorized correcting optional MQTT discovery and the missing smoke-test callback start, rerunning checks, then deploying the add-on. This permits the passive installation/start only, not Unlock/Stop ringing, sound changes or physical-device tests. HA readback was healthy/supported amd64, Core2026.9.4/Supervisor2026.09.3, external MQTT192.168.0.30 loaded, no Hikvision add-on/Core integration and no Supervisor MQTT provider.
- Review fixes: use `mqtt:want` rather than `mqtt:need`; manual broker options remain mandatory without a Supervisor provider. Smoke must call EventManager.start(); its earlier success label did not prove callback registration. Preserve the separate real ring-test evidence and run the corrected native check before deployment.
- Sole production target: one Supervisor-managed HA add-on for DS-KV6113-WPE1(B) and DS-KH6320-WTE1. Reuse existing MQTT and Frigate; HA owns notifications. Local containers are test tools only.
- User authorized refactoring, SDK inclusion and focused commits/pushes on 2026-10-06. No deployment, new device commands, firmware changes or sound changes are authorized by that cleanup request.
- Runtime, tests, manifest, Dockerfile and both architecture bundles live in `doorbell/`. Supervisor builds locally; do not restore the unpublished image reference or a second standalone production path.
- Removed stale upstream IDE/issue/funding metadata. Keep `.env*`, local `options.json`, development environments, caches and backups ignored. Do not restore a blanket `*.so` ignore that hides required SDK files; vendor bytes and notices must remain intact.
- Upstream base is `8f8b97c6b5731e9979eee28d011db6b860b826e1`. Preserve the reduced scope when reviewing upstream changes; do not overwrite it with an upstream sync.

## Safety Constraints

- One Paho client, native MQTT discovery and three direct runtime dependencies. One validated JSON config; omitted MQTT settings use Supervisor service discovery.
- Verify exact model and stable serial before enabling controls. No speculative model aliases, including omission of `(B)`. Replacement at an existing address requires deliberate reviewed restart.
- Commands are non-retained, broker-epoch/device-generation scoped, expire after three seconds and are not retried after ambiguous failures. Fallback is allowed only on SDK error 23. Unlock is outdoor-only; Stop ringing requires fresh ringing state and sends reject, never answer/hang-up.
- SDK callbacks copy values before returning. Keep separate bounded alarm/command queues and drain alarms before committing a newer poll snapshot.
- Outdoor SDK events own notification episodes independently of displayed state. Routine outdoor polls cannot emit a press or clear the latch; accepted SDK dismissal re-arms it. Out-of-order events cannot rewind the episode. Startup/reconnect seeds state without ring replay. A missed dismissal favors suppression until dismissal/new-session evidence, not a guessed timeout.
- Tested firmware uploads historical events even in realtime mode. Read device-local time at subscription and reject invalid/older timestamps. Clock regression can suppress new events; reconnect after correcting the device clock rather than weakening replay protection.
- SDK LONG is signed 32-bit, callback serial offset is 12, V50 setup takes a pointer, and GetErrorMsg takes LONG*. Do not replace these with host c_long or truncate ABI structures/unions.
- Cleanup attempts both channel close and logout, retaining failed handles. Unresolved cleanup blocks relogin and leaves controls unavailable while the 30-second recovery path retries. SDK/bridge shutdown must still be attempted.
- Unsupported polling falls back to events; stale event-only state becomes unknown after 120 seconds. It cannot authorize Stop ringing.

## Verified Evidence

- 2026-10-06 read-only identity/status/capability/passive-subscription checks passed on outdoor V2.2.53 build 220816 and indoor V2.2.2 build 221129. Firmware states `ring` and `onCall` normalize to `ringing` and `oncall`. Physical command effects are not inferred from advertised capabilities.
- Baseline amd64 6.1.6.45 supervised press: one ring/dismiss pair, one local intent, 30 historical callbacks ignored, indoor ringing->idle in about 31 seconds; user confirmed quiet. Outdoor polling stayed idle during the call.
- Promoted amd64 6.1.9.48 was rehearsed with source `6297283`: one ring/dismiss pair about 31 seconds apart, one intent, 17 historical callbacks ignored, both session cleanups and SDK cleanup successful. Observer blocked physical controls/non-GET calls and had no MQTT client. User later confirmed quiet.
- Each authorized mute backed up indoor audio and restored output 7->0->7 after idle, with talk volume 7 unchanged and exact semantic readback. Write-only `type=audioOutput` is required for the temporary audio PUT; raw GET XML alone was rejected without changing volume. All observers stopped.
- Raw evidence stays private under `%LOCALAPPDATA%/PR-Zion/backups/hikvision-ring-20261006/` and `hikvision-sdk-6.1.9.48-20261006/`, especially `candidate-readonly.json` and `ring-test/{ring-observation,restore-result}.json`. Earlier no-button/ABI diagnostic captures are not successful press evidence.
- Consolidation verification: 110 offline pytest checks with socket/vendor-loader guards, focused lint, and fresh amd64/ARM64 builds passed. Both fresh images passed version/callback/error-lookup/cleanup smoke checks with networking disabled. These are local results; no completed GitHub CI run or HA installation is asserted. Device/HA/MQTT acceptance remains listed in README.

## SDK And Recovery

- amd64 now includes the complete verified 6.1.9.48 build20230410 runtime (25 files), not mixed old/new components. Archive hash, notices and dependency age are in `doorbell/SDK.md`. ARM64 remains 6.1.8.101; 6.1.11.30 has not been acquired for either architecture.
- User explicitly confirmed SDK redistribution permission on 2026-10-06. Preserve original notices. This confirmation does not establish a project-wide license for the upstream application; automated image publication remains absent.
- Before consolidation/promotion, fork commit `84991d6` retains the old layout and amd64 6.1.6.45 runtime. Prior local test images remain available; no production rollback is needed because no add-on deployment occurred.
- Future migration uses a new slug and entity IDs. Do not run both bridges concurrently or automatically delete old discovery/automations. Back up references first; stop the candidate and restore the previous add-on/references to roll back. No device configuration is rewritten by the add-on.
- On Windows, Docker/editor handles can prevent directory renames; move the enumerated tracked files individually. Verify deletion on disk because the editor patch tool has sometimes reported success without removing files.
- For `python -c` with mounted source, prepend that source to sys.path: PYTHONPATH does not outrank image cwd `/app`. SDK version is meaningful only after Init. Network-interface warnings are expected with `--network none`.
- Public PyPI wheel downloads previously failed TLS locally; the existing HTTPS package mirror worked without disabling TLS. This is a local build workaround, not a reason to weaken certificate checks.