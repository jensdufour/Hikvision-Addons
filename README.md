# Hikvision Doorbell Lite

An unreleased, reduced fork of [pergolafabio/Hikvision-Addons](https://github.com/pergolafabio/Hikvision-Addons), based on `8f8b97c6b5731e9979eee28d011db6b860b826e1`.

Targets **DS-KV6113-WPE1(B)** outdoor stations and **DS-KH6320-WTE1** indoor stations only. Firmware-specific operation has not been verified on physical devices. No image is published by this fork's CI.

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

## Before A Device Pilot

Confirm firmware versions and the exact model strings returned by `/ISAPI/System/deviceInfo`. A device reporting the KV6113 model without the `(B)` revision suffix is deliberately rejected until that identity can be verified; do not weaken the guard by guessing.

Then separately authorize a reversible deployment and observe real ring, answer, dismissal, broker/device recovery and native indoor audio. Unlock and Stop ringing tests require separate explicit consent and someone at the door. Linux SDK loading alone does not prove firmware compatibility.

## Attribution And Distribution

The protocol work and bundled Hikvision SDK come from the upstream project and its contributors. No project-wide upstream license was found during the audit. The retained example's Apache license is not a license for the whole application or the vendor SDK. Clarify modified-application and SDK redistribution rights before publishing a release image or distributing the modified application. No new license is asserted here.