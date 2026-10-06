# Hikvision Doorbell Lite

One experimental **Home Assistant add-on** for **DS-KV6113-WPE1(B)** outdoor stations and **DS-KH6320-WTE1** indoor stations. Reuses the existing MQTT broker and Frigate installation; no companion integration or separate bridge deployment.

Reduced from [pergolafabio/Hikvision-Addons](https://github.com/pergolafabio/Hikvision-Addons), upstream base `8f8b97c6b5731e9979eee28d011db6b860b826e1`.

## Scope

| Function | Behavior |
| --- | --- |
| Doorbell event | One outdoor `ring` event for HA automations |
| Call state | Per-device `idle`, `ringing`, `oncall`, or `unknown` |
| Unlock | Momentary outdoor first-relay button |
| Availability | Broker/device health and automatic recovery |
| Stop ringing | Reject a confirmed incoming call; never answer or hang up |

Frigate owns video, snapshots and recordings. Home Assistant owns notifications. No media handling, audio broadcast, arbitrary ISAPI, stdin commands, or support for other models.

## Repository

- [doorbell/README.md](doorbell/README.md): the complete add-on and its local Docker build context.
- [doorbell/DOCS.md](doorbell/DOCS.md): configuration, entities, safety and migration.
- [doorbell/SDK.md](doorbell/SDK.md): bundled SDK versions, provenance and limitations.
- [doorbell/DEVELOPMENT.md](doorbell/DEVELOPMENT.md): offline checks and architecture.
- [MEMORY.md](MEMORY.md): durable constraints, verified evidence and recovery.

The manifest builds locally in Supervisor instead of referencing an unpublished image. It remains experimental and manual-start. The user-authorized passive pilot was installed and started on 2026-10-06; automatic updates and watchdog are off while acceptance continues.

Standalone deployment files and stale upstream IDE/issue/funding metadata are removed. Local credentials, options, caches and backups stay ignored; SDK runtime files remain tracked with their original notices.

## Verified State

The HA pilot runs `0.1.0-dev` from reviewed source `1a1ada8`, with protection enabled and no extra host/Core permissions. Both target stations are online and idle. HA discovered exactly six MQTT entities across two devices; buttons and the event remain `unknown` until used or triggered, which is not an availability failure.

All 32 installed Python/amd64 SDK files match Git, and the running process mapped the bundled SDK and crypto libraries. Supervisor is healthy, both connections are logged, and no add-on errors were present. All 47 existing integration preferences, 1,756 entity preferences, 108 device preferences, 27 automation enablements, three dashboards, six configuration hashes and three prior add-on states/versions were preserved. Core was not restarted. No notification automation was changed and no physical control was tested.

Repository checks: 110 offline tests and focused Python lint pass. Fresh amd64 and ARM64 images build and pass version, callback, error-lookup and cleanup checks with networking disabled. These development checks do not establish completed GitHub CI or physical-device acceptance; installation is verified separately by the native pilot above.

The deployment review corrected two preparation gaps: MQTT service discovery is optional for external brokers, and the native smoke script explicitly starts callback registration before reporting success. Earlier smoke results proved loading/version/error lookup/cleanup only; the separate supervised ring test did exercise actual callbacks.

On 2026-10-06, read-only SDK checks passed for outdoor firmware **V2.2.53 build 220816** and indoor firmware **V2.2.2 build 221129**. Both devices report their exact supported model, advertise reject, and permit passive event subscription. The outdoor station advertises one relay.

The now-bundled amd64 **6.1.9.48 build20230410** passed a supervised native ring/dismiss cycle: one local notification intent, 17 historical callbacks ignored, indoor ringing then idle, and successful session/SDK cleanup. Temporary indoor mute was restored with exact API readback, and the user confirmed quiet during the press. No MQTT publication or physical call-control command was part of that observation.

Outdoor polling stayed idle during the call. Use the outdoor event for notifications and the indoor Call state for progress. ARM64 retains **6.1.8.101** and has container-level, not device-level, verification. See [SDK details](doorbell/SDK.md).

## Remaining Acceptance

1. Verify a real outdoor ring reaches the HA event and an intended phone notification; no notification automation was changed by deployment. Also verify normal answered-call state/audio.
2. Exercise broker/device outage recovery without replaying events or stale commands.
3. Separately authorize physical Unlock and Stop ringing tests with someone present at the door.
4. Choose permanent boot/watchdog settings after pilot acceptance; current startup remains manual.
5. Resolve remaining release licensing and SDK maintenance gaps described below.

The pilot reuses the existing LAN-only anonymous MQTT policy. It adds no public port, but any client able to publish to that broker can issue the door-control commands. Connection epochs prevent stale replay, not unauthorized publishers; topic authentication/ACLs are a separate hardening decision.

## Attribution And Distribution

Protocol work derives from the upstream contributors. The retained [hikcli example license](doorbell/licenses/hikcli-LICENSE) applies to that contribution, not the whole application or SDK. No project-wide upstream application license was found; no new license is asserted here.

The user confirmed permission to redistribute the downloaded SDK on 2026-10-06. Its complete runtime and original third-party notices are included on that basis; this is not a claim that Hikvision's general website terms grant redistribution rights. No release image is published. Application licensing, old vendor dependencies and an unacquired newer ARM SDK remain explicit release considerations.