# Hikvision Doorbell Lite

One experimental **Home Assistant add-on** for **DS-KV6113-WPE1(B)** outdoor stations and **DS-KH6320-WTE1** indoor stations. Connects the devices to Home Assistant through MQTT; no companion integration or separate bridge deployment.

Reduced from [pergolafabio/Hikvision-Addons](https://github.com/pergolafabio/Hikvision-Addons), upstream base `8f8b97c6b5731e9979eee28d011db6b860b826e1`.

## Scope

| Function | Behavior |
| --- | --- |
| Doorbell event | One outdoor `ring` event for HA automations |
| Call state | Per-device `idle`, `ringing`, `oncall`, or `unknown` |
| Unlock | Momentary outdoor first-relay button |
| Availability | Broker/device health and automatic recovery |
| Stop ringing | Reject a confirmed incoming call; never answer or hang up |

Frigate can handle video, snapshots and recordings. Home Assistant owns notifications. No media handling, audio broadcast, arbitrary ISAPI, stdin commands, or support for other models.

## Installation

Add `https://github.com/jensdufour/Hikvision-Addons` to the Supervisor add-on store. Supervisor builds the add-on locally. Configure the devices and MQTT before starting; startup defaults to manual and the release remains experimental.

See [configuration, security and migration](doorbell/DOCS.md). MQTT publishers with access to the command topics can issue controls; use broker authentication and topic ACLs appropriate to your network.

## Development

Replay filtering uses the native SDK clock to match SDK alarm timestamps, including when ISAPI reports a different wall-time representation. A missing or invalid clock fails closed before subscription.

- [doorbell/README.md](doorbell/README.md): complete add-on build context.
- [doorbell/SDK.md](doorbell/SDK.md): bundled SDK versions, provenance and limitations.
- [doorbell/DEVELOPMENT.md](doorbell/DEVELOPMENT.md): offline tests and native smoke checks.
- [MEMORY.md](MEMORY.md): reusable engineering constraints.

## Licenses

Original third-party notices are retained under [doorbell/licenses](doorbell/licenses). Each notice applies only to its covered component; no project-wide license is asserted by this fork.