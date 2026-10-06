# Configuration And Pilot Requirements

## Status

This fork has offline tests, successful read-only SDK checks on both target devices and a supervised local ring/dismiss test, not full hardware acceptance. The [verified state](../README.md#verified-state) and [SDK record](SDK.md) describe exact limits. The manifest is experimental and manual-start. Supervisor builds from this directory; no prebuilt image is required or published by CI.

Installation remains a separately authorized pilot. Add `https://github.com/jensdufour/Hikvision-Addons` as an add-on repository, select Hikvision Doorbell Lite and let Supervisor build it. Enter the two device configurations and MQTT settings before starting; the blank default addresses/passwords intentionally fail validation. Do not start the upstream bridge concurrently.

## Options

Configure each device with `name`, `model`, literal `ip`, `username`, `password` and optional SDK `port` (default `8000`). The only accepted models are `DS-KV6113-WPE1(B)` and `DS-KH6320-WTE1`.

`system.log_level` accepts `ERROR`, `WARNING`, `INFO`, or `DEBUG`. `system.poll_seconds` is 2-60 seconds, default 5. Missing, unsupported, mismatched or changed device identity keeps controls unavailable. Passwords are masked in configuration representations.

`mqtt: {}` requests the Supervisor MQTT service. A manual broker uses `host`, optional `port` (default 1883), `ssl`, `username` and `password`. Set both `ssl: true` and the broker's TLS port when needed; TLS uses normal certificate and hostname verification. An invalid manual configuration fails instead of silently switching brokers.

Supervisor MQTT discovery is optional (`mqtt:want`), so an external broker does not require a second broker add-on. With an external broker, supply its manual settings; empty MQTT options still require an available Supervisor MQTT service and fail closed without one.

The [test configuration example](default_config.json) uses documentation-only IP addresses, not real device details. Home Assistant supplies `/data/options.json`; `CONFIG_FILE_PATH` is available for isolated development checks only. The previous dotenv, YAML, `DOORBELLS` and nested environment-variable loaders are not supported.

## Entities

| Device | Entities |
| --- | --- |
| Outdoor | Doorbell event, Call state, Unlock button, Stop ringing button |
| Indoor | Call state, Stop ringing button |

Availability combines broker/bridge connectivity and that device's health. The indoor station does not emit a second ring notification. Use the outdoor event entity's `ring` event in a Home Assistant automation; add Frigate imagery there if desired. SDK events and polling for the same ringing episode are deduplicated. Events are not retained or replayed when the broker returns.

Call states are `idle`, `ringing`, `oncall`, and `unknown`. Both checked firmwares advertise `ring`, which is normalized to `ringing`. Offline entities become unavailable. No timer pretends that a call has ended. When status polling is unsupported, SDK events remain usable and stale state becomes `unknown` after 120 seconds. Stop ringing intentionally does nothing if current ringing cannot be confirmed.

The supervised press showed that outdoor polling can remain idle while the indoor station is ringing. Use the indoor Call state and Stop ringing control for call progress; use the outdoor Doorbell event for notifications. Actual rejection and answered-call behavior still need separate testing. Historical SDK records are filtered using the device clock captured at subscription, not interpreted as new presses.

Outdoor polls cannot emit ring events or reset notification deduplication. A current SDK dismissal re-arms the next episode; older SDK events cannot rewind it. A missed dismissal may suppress later notifications until a valid dismissal or new session. Startup suppresses replay, and no arbitrary timeout invents a new press. A clock moving behind the subscription baseline also requires correction and reconnection.

Controls require verified model/serial and a current connection. Command topics rotate with broker/device sessions, retained commands are rejected, and queued commands expire after three seconds. Ambiguous failures are not retried. Failed native cleanup remains tracked and blocks a replacement login while the device stays unavailable.

Unlock controls the outdoor station's first relay through the existing SDK command, with ISAPI fallback only on error 23. It does not expose an indoor duplicate unlock control. Stop ringing rejects a current incoming call; it does not hang up an established conversation.

## Future Migration

Before any pilot, record actual firmware and model readback; confirm outdoor ring events, status polling, and the intended relay. Some firmware may omit the `(B)` suffix. That currently fails closed and needs evidence before adding an explicit mapping.

Back up the existing add-on configuration and MQTT entity/automation references. Stop the upstream bridge before starting this one. New entity IDs and a new slug prevent a silent in-place takeover; rebind automations deliberately. Removed upstream discovery topics are not deleted automatically, and existing retained command topics are never subscribed to by this bridge.

Do not send commands merely to test connectivity. First validate passive ring/state behavior and normal indoor audio. Authorize physical unlock and rejection tests separately. To roll back, stop this bridge and restore the prior add-on and automation references; no device configuration is rewritten by the fork.

No Home Assistant Core API permission, writable config/media mount, host networking, stdin access or full access is requested by the manifest.