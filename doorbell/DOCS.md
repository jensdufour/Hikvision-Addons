# Configuration And Pilot Requirements

## Status

This fork is an offline-tested prototype with successful read-only SDK checks on both target devices, not a fully hardware-verified release. The [firmware results](../README.md#read-only-firmware-checks) record exact versions and limits. The manifest is experimental, manual-start, and points to the fork's own image namespace. CI never publishes that image.

## Options

Configure each device with `name`, `model`, literal `ip`, `username`, `password` and optional SDK `port` (default `8000`). The only accepted models are `DS-KV6113-WPE1(B)` and `DS-KH6320-WTE1`.

`system.log_level` accepts `ERROR`, `WARNING`, `INFO`, or `DEBUG`. `system.poll_seconds` is 2-60 seconds, default 5. Missing, unsupported, mismatched or changed device identity keeps controls unavailable. Passwords are masked in configuration representations.

`mqtt: {}` requests the Supervisor MQTT service. A manual broker uses `host`, optional `port` (default 1883), `ssl`, `username` and `password`. Set both `ssl: true` and the broker's TLS port when needed; TLS uses normal certificate and hostname verification. An invalid manual configuration fails instead of silently switching brokers.

The standalone [JSON example](../hikvision-doorbell/default_config.json) uses documentation-only IP addresses, not real device details. Home Assistant supplies `/data/options.json`; `CONFIG_FILE_PATH` can select another JSON file outside Supervisor. The previous dotenv, YAML, `DOORBELLS` and nested environment-variable loaders are not supported.

## Entities

| Device | Entities |
| --- | --- |
| Outdoor | Doorbell event, Call state, Unlock button, Stop ringing button |
| Indoor | Call state, Stop ringing button |

Availability combines broker/bridge connectivity and that device's health. The indoor station does not emit a second ring notification. Use the outdoor event entity's `ring` event in a Home Assistant automation; add Frigate imagery there if desired. SDK events and polling for the same ringing episode are deduplicated. Events are not retained or replayed when the broker returns.

Call states are `idle`, `ringing`, `oncall`, and `unknown`. Both checked firmwares advertise `ring`, which is normalized to `ringing`. Offline entities become unavailable. No timer pretends that a call has ended. When status polling is unsupported, SDK events remain usable and stale state becomes `unknown` after 120 seconds. Stop ringing intentionally does nothing if current ringing cannot be confirmed.

Unlock controls the outdoor station's first relay through the existing SDK command, with ISAPI fallback only on error 23. It does not expose an indoor duplicate unlock control. Stop ringing rejects a current incoming call; it does not hang up an established conversation.

## Future Migration

Before any pilot, record actual firmware and model readback; confirm outdoor ring events, status polling, and the intended relay. Some firmware may omit the `(B)` suffix. That currently fails closed and needs evidence before adding an explicit mapping.

Back up the existing add-on configuration and MQTT entity/automation references. Stop the upstream bridge before starting this one. New entity IDs and a new slug prevent a silent in-place takeover; rebind automations deliberately. Removed upstream discovery topics are not deleted automatically, and existing retained command topics are never subscribed to by this bridge.

Do not send commands merely to test connectivity. First validate passive ring/state behavior and normal indoor audio. Authorize physical unlock and rejection tests separately. To roll back, stop this bridge and restore the prior add-on and automation references; no device configuration is rewritten by the fork.

No Home Assistant Core API permission, writable config/media mount, host networking, stdin access or full access is requested by the manifest.