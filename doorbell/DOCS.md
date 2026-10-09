# Configuration

## Status

The manifest is experimental and defaults to manual startup. Supervisor builds from this directory; no prebuilt image is required or published by CI. See [development checks](DEVELOPMENT.md) and the [SDK inventory](SDK.md).

Add `https://github.com/jensdufour/Hikvision-Addons` as an add-on repository, select Hikvision Doorbell Lite and let Supervisor build it. Enter the two device configurations and MQTT settings before starting; the blank default addresses/passwords intentionally fail validation. Do not start the upstream bridge concurrently.

## Options

Configure each device with `name`, `model`, literal `ip`, `username`, `password` and optional SDK `port` (default `8000`). The only accepted models are `DS-KV6113-WPE1(B)` and `DS-KH6320-WTE1`.

`system.log_level` accepts `ERROR`, `WARNING`, `INFO`, or `DEBUG`. `system.poll_seconds` is 2-60 seconds, default 5. Missing, unsupported, mismatched or changed device identity keeps controls unavailable. Passwords are masked in configuration representations.

`mqtt: {}` requests the Supervisor MQTT service. A manual broker uses `host`, optional `port` (default 1883), `ssl`, `username` and `password`. Set both `ssl: true` and the broker's TLS port when needed; TLS uses normal certificate and hostname verification. An invalid manual configuration fails instead of silently switching brokers.

Supervisor MQTT discovery is optional (`mqtt:want`), so an external broker does not require a second broker add-on. With an external broker, supply its manual settings; empty MQTT options still require an available Supervisor MQTT service and fail closed without one.

The [test configuration example](default_config.json) uses documentation-only IP addresses, not real device details. Home Assistant supplies `/data/options.json`; `CONFIG_FILE_PATH` is available for isolated development checks only. The previous dotenv, YAML, `DOORBELLS` and nested environment-variable loaders are not supported.

## Entities

| Device | Entities |
| --- | --- |
| Outdoor | Doorbell event, Card access event, Call state, Unlock button, Stop ringing button |
| Indoor | Call state, Stop ringing button |

Availability combines broker/bridge connectivity and that device's health. The indoor station does not emit a second ring notification. Use the outdoor event entity's `ring` event in a Home Assistant automation; add Frigate imagery there if desired. SDK events and polling for the same ringing episode are deduplicated. Events are not retained or replayed when the broker returns.

Call states are `idle`, `ringing`, `oncall`, and `unknown`. Firmware state `ring` is normalized to `ringing`. Offline entities become unavailable. No timer pretends that a call has ended. When status polling is unsupported, SDK events remain usable and stale state becomes `unknown` after 120 seconds. Stop ringing intentionally does nothing if current ringing cannot be confirmed.

Outdoor polling can remain idle while the indoor station is ringing. Use the indoor Call state and Stop ringing control for call progress; use the outdoor Doorbell event for notifications. Historical SDK records are filtered using the native SDK clock captured at subscription, not interpreted as new presses. This avoids differences in ISAPI's DST representation; a failed or incomplete native clock read keeps the device unavailable.

Outdoor polls cannot emit ring events or reset notification deduplication. A current SDK dismissal re-arms the next episode; older SDK events cannot rewind it. A missed dismissal may suppress later notifications until a valid dismissal or new session. Startup suppresses replay, and no arbitrary timeout invents a new press. A clock moving behind the subscription baseline also requires correction and reconnection.

Controls require verified model/serial and a current connection. Command topics rotate with broker/device sessions, retained commands are rejected, and queued commands expire after three seconds. Ambiguous failures are not retried. Failed native cleanup remains tracked and blocks a replacement login while the device stays unavailable.

These guards do not authenticate MQTT publishers. Anyone able to publish to the broker's command topics can request a control action. Use broker authentication and topic ACLs appropriate to the installation's trust boundary. No public listener is added by this add-on.

### Card Access Events

The outdoor **Card access** event entity uses its own non-retained, QoS0 MQTT
topic and does not change call/ring state or send any control command:

| Event Type | Meaning |
| --- | --- |
| `access_granted` | Intercom event type1, unlock method3, local relay0: a card-authorized unlock record, not proof the door physically opened |
| `access_denied` | Intercom event type5: an invalid/rejected card scan, diagnostic only |

Card access uses `mdi:card-account-details-outline`. The earlier
`mdi:card-account` name was invalid and could leave an empty icon; an existing
HA user icon override takes precedence over MQTT discovery's default.

Attributes are `card_number` (a decimal string, preserving leading zeros) and
`device_time` (native device-local time without a UTC offset). Use HA's event
timestamp for HA-side freshness checks, not an assumed UTC interpretation of
`device_time`. Card issuing/enrollment, the SDK's unused authentication record,
external-relay records and password/duress/householder/platform/Bluetooth/QR/face/
fingerprint unlocks are not published as card events.

Callbacks copy identifiers before returning and reject incomplete/malformed
buffers, invalid device/session identity, missing subscription clocks and older
records. The serialized runtime rechecks the native clock: future or older-than-
three-second records are dropped, as are expired queues and records received
before the current device/broker session. The same type/card/device-second is
deduplicated in a bounded128-record cache, cleared on device cleanup. Failed
clock reads or publication are not retried. No native API is called from the
callback; SDK reads remain on the existing processing loop.

This is an event source, not an access-control policy for another lock. An entry
automation must explicitly require `access_granted`, allowlist the intended card
number, check current availability/freshness and reject startup/restored events.
Never use any scan, `access_denied`, or a generic remote-unlock record as approval.
Native card enrollment/validity is managed on the station, not by this add-on.

Card numbers are present on MQTT and may be stored in HA history even though MQTT
events are not retained. Restrict access accordingly. Event freshness and hashes
do not authenticate publishers: before using these events for another lock,
authenticate MQTT clients and restrict publication to the event topics. A card
number alone is not proof against cloning. Firmware-specific event delivery and
physical effects require separate evidence; synthetic tests do not establish them.

Unlock controls the outdoor station's first relay through the existing SDK command, with ISAPI fallback only on error 23. It does not expose an indoor duplicate unlock control. Stop ringing rejects a current incoming call; it does not hang up an established conversation.

## Future Migration

Version0.1.4-dev renames the Doorbell event type `ring` to `pressed` and Card
access types `card_unlock`/`card_rejected` to `access_granted`/`access_denied`.
Update automation event-type filters when upgrading. Entity unique IDs, MQTT
topics, names and attributes are unchanged. Stored history retains old types;
the latest event timestamp is a record of an occurrence, not a held switch.
Call-state values and button commands are unchanged.

Before enabling controls, verify actual firmware and model readback, outdoor ring events, status polling, and the intended relay. Some firmware may omit the `(B)` suffix. That currently fails closed and needs evidence before adding an explicit mapping.

Back up the existing add-on configuration and MQTT entity/automation references. Stop the upstream bridge before starting this one. New entity IDs and a new slug prevent a silent in-place takeover; rebind automations deliberately. Removed upstream discovery topics are not deleted automatically, and existing retained command topics are never subscribed to by this bridge.

Do not send commands merely to test connectivity. First validate passive ring/state behavior and normal indoor audio. Authorize physical unlock and rejection tests separately. To roll back, stop this bridge and restore the prior add-on and automation references; no device configuration is rewritten by the fork.

No Home Assistant Core API permission, writable config/media mount, host networking, stdin access or full access is requested by the manifest.