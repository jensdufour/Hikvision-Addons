# Hikvision Doorbell Lite

An unreleased, reduced fork of [pergolafabio/Hikvision-Addons](https://github.com/pergolafabio/Hikvision-Addons), based on `8f8b97c6b5731e9979eee28d011db6b860b826e1`.

Targets **DS-KV6113-WPE1(B)** outdoor stations and **DS-KH6320-WTE1** indoor stations only. Read-only SDK identity, call-status, capability and passive event-subscription checks have passed on both physical devices; ring delivery and physical control effects remain unverified. No image is published by this fork's CI.

## Scope

- Outdoor doorbell ring events for Home Assistant automations.
- Per-device call state: `idle`, `ringing`, `oncall`, or `unknown`.
- A momentary outdoor Unlock button, using the first door relay.
- Device availability and automatic connection recovery.
- Stop ringing: reject an incoming call; do not answer or end an established call.

Frigate owns video, snapshots and recordings. Home Assistant owns notifications. The bridge does not change the devices' native intercom configuration.

No audio broadcast, video preview, snapshots, scene/alarm controls, arbitrary ISAPI commands, stdin commands, or support for other models. Native SDK libraries and ABI declarations are retained.

## Safety

Device model and serial are checked before entities become available. Unknown models fail closed. A device replacement at an existing address is refused until the process is deliberately restarted with reviewed configuration.

Unlock is never a retained switch state. MQTT command topics change on each broker connection, commands expire after three seconds in the queue, and reconnects invalidate queued commands. Ambiguous command failures are not retried. The existing SDK/ISAPI fallback is used only for the explicit unsupported-operation error `23`.

State polling defaults to five seconds because the existing SDK event path does not establish every call transition. Unsupported polling falls back to events; stale event-only state becomes `unknown`, not a guessed `idle`. Stop ringing is a no-op if a fresh status query cannot confirm ringing.

SDK alarms use a separate bounded queue from commands. Pending alarms are handled before publishing a newer poll snapshot, so a short ring is not erased by a later idle/on-call sample. Repeated ringing reports remain deduplicated, and an event newer than the poll still owns the displayed state.

Cleanup checks both native close results and clears a handle only after success. Failed handles remain tracked, are reported as cleanup errors, and block a new login until cleanup succeeds. The device stays unavailable while the normal 30-second recovery cycle retries cleanup; other devices continue running. Shutdown still attempts MQTT and SDK cleanup even if a device close fails. Clearing a Python field alone is not evidence of successful native cleanup.

## Configuration And Migration

See [add-on documentation](doorbell/DOCS.md) and [standalone Docker instructions](docs/docker.md).

This is not a drop-in upgrade. It has a new add-on slug, new MQTT entity unique IDs, and a strict JSON configuration. Removed options are rejected instead of silently ignored. Do not run it alongside the upstream bridge during a future migration. Nothing here removes existing MQTT discovery, entities, automations, or device configuration.

## Offline Checks

From `hikvision-doorbell`, in an isolated Python environment:

```sh
pip install -r requirements-dev.txt
pytest -q
flake8 src tests --select=E9,F63,F7,F82 --show-source
```

Every test blocks network connections and vendor-library loading. Separate Docker smoke tests load the SDK with `--network none`; they are not doorbell acceptance tests. CI checks amd64 and aarch64 without publishing images or using device credentials.

## Read-Only Firmware Checks

Verified on 2026-10-06 using the fork's Linux SDK login and GET path. Initial probes blocked control and event-subscription functions; a separate idle-gated probe allowed only passive event subscription while physical control functions stayed blocked:

| Model | Firmware | Verified read-only behavior |
| --- | --- | --- |
| DS-KV6113-WPE1(B) | V2.2.53 build 220816 | Exact identity accepted, call state reads idle, one door relay advertised, reject advertised, passive event channel opens |
| DS-KH6320-WTE1 | V2.2.2 build 221129 | Exact identity accepted, call state reads idle, reject advertised, passive event channel opens |

Both firmwares advertise call states `idle`, `ring`, and `onCall`. The parser now normalizes `ring` to `ringing`, with regressions for both models and the Stop ringing path. Previously it produced `unknown`, preventing rejection of a ringing call.

The passive probe immediately invoked alarm-channel cleanup and logout; local handles were cleared on both devices. It did not wait for or verify a real event. No ring was injected, no MQTT state was published and no unlock/reject command was sent. Advertised support is not proof of the physical command effect. Device credentials, addresses, serials and raw private exports are not included in these findings.

## Before A Device Pilot

The checked devices return the exact configured model strings, including `(B)` outdoors. Recheck after firmware updates or replacement. A device reporting the KV6113 model without that revision suffix remains deliberately rejected; no speculative model alias was added.

Then separately authorize a reversible deployment and observe real ring, answer, dismissal, broker/device recovery and native indoor audio. Unlock and Stop ringing tests require separate explicit consent and someone at the door. Linux SDK loading alone does not prove firmware compatibility.

## Attribution And Distribution

The protocol work and bundled Hikvision SDK come from the upstream project and its contributors. No project-wide upstream license was found during the audit. The retained example's Apache license is not a license for the whole application or the vendor SDK. Clarify modified-application and SDK redistribution rights before publishing a release image or distributing the modified application. No new license is asserted here.