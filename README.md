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

The manifest builds locally in Supervisor instead of referencing an unpublished image. It remains experimental and manual-start. Repository preparation is not deployment approval; nothing has been installed in HA by this refactor.

Standalone deployment files and stale upstream IDE/issue/funding metadata are removed. Local credentials, options, caches and backups stay ignored; SDK runtime files remain tracked with their original notices.

## Verified State

Repository checks: 110 offline tests and focused Python lint pass. Fresh amd64 and ARM64 images build and pass version, callback, error-lookup and cleanup checks with networking disabled. These are local results, not a claim of completed GitHub CI or HA installation.

On 2026-10-06, read-only SDK checks passed for outdoor firmware **V2.2.53 build 220816** and indoor firmware **V2.2.2 build 221129**. Both devices report their exact supported model, advertise reject, and permit passive event subscription. The outdoor station advertises one relay.

The now-bundled amd64 **6.1.9.48 build20230410** passed a supervised native ring/dismiss cycle: one local notification intent, 17 historical callbacks ignored, indoor ringing then idle, and successful session/SDK cleanup. Temporary indoor mute was restored with exact API readback, and the user confirmed quiet during the press. No MQTT publication or physical call-control command was part of that observation.

Outdoor polling stayed idle during the call. Use the outdoor event for notifications and the indoor Call state for progress. ARM64 retains **6.1.8.101** and has container-level, not device-level, verification. See [SDK details](doorbell/SDK.md).

## Remaining Acceptance

1. Separately authorize installation, then verify Supervisor build/start and MQTT discovery on the actual HA host.
2. Verify the outdoor event reaches a real HA notification and normal answered-call state/audio works.
3. Exercise broker/device outage recovery without replaying events or stale commands.
4. Separately authorize physical Unlock and Stop ringing tests with someone present at the door.
5. Resolve remaining release licensing and SDK maintenance gaps described below.

## Attribution And Distribution

Protocol work derives from the upstream contributors. The retained [hikcli example license](doorbell/licenses/hikcli-LICENSE) applies to that contribution, not the whole application or SDK. No project-wide upstream application license was found; no new license is asserted here.

The user confirmed permission to redistribute the downloaded SDK on 2026-10-06. Its complete runtime and original third-party notices are included on that basis; this is not a claim that Hikvision's general website terms grant redistribution rights. No release image is published. Application licensing, old vendor dependencies and an unacquired newer ARM SDK remain explicit release considerations.