# Hikvision Doorbell Lite

An unreleased, reduced fork of [pergolafabio/Hikvision-Addons](https://github.com/pergolafabio/Hikvision-Addons), based on `8f8b97c6b5731e9979eee28d011db6b860b826e1`.

Targets **DS-KV6113-WPE1(B)** outdoor stations and **DS-KH6320-WTE1** indoor stations only. Read-only firmware checks and a supervised native ring/dismiss cycle have passed. MQTT/phone delivery, answered-call behavior, recovery and physical unlock/reject effects remain unverified. No image is published by this fork's CI.

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

Outdoor notification episodes are tracked separately from displayed call state. Routine outdoor polls can update that sensor but cannot emit a press event or reset ring deduplication. An accepted SDK dismissal re-arms the next episode, even when a newer poll already updated the display; older SDK events cannot rewind the episode tracker. A new session seeds its baseline without replaying a ring, and indoor polling is unchanged. If an SDK dismissal is missed, subsequent rings remain suppressed until an accepted dismissal or a new session baseline; an unreliable idle poll is not a safe substitute. No arbitrary debounce timeout is used.

The callback header uses a signed 32-bit user ID on both architectures; Linux's 64-bit `long` shifts the serial field and breaks device matching. Subscription options are passed by pointer. The tested outdoor firmware uploads historical alarms even when realtime mode is requested. Each subscription therefore reads the device-local clock and rejects invalid timestamps and alarms older than that session before updating state or notifications. If the clock moves behind that baseline, reconnect after correcting the clock rather than weakening the guard.

Native error-message lookup also uses a pointer to the SDK's 32-bit `LONG`, as declared in the official header, rather than the host's `long`. The binding is checked against both existing SDK architectures and the isolated Linux64 6.1.9.48 candidate.

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

## Supervised Ring Test

On 2026-10-06 the user pressed the outdoor button once and confirmed the indoor station stayed quiet. A guarded local observer ran the actual SDK callback and state logic with all unlock/reject/answer calls blocked and no MQTT client.

- One current outdoor SDK ring event and its later dismissal decoded with matching identity; 30 historical callbacks were discarded.
- Exactly one local notification intent was produced, with no MQTT publication or phone notification.
- The indoor station reported ringing and returned to idle naturally after about 31 seconds. The outdoor poll returned idle during the call, so it is not a reliable standalone source of call progress on this firmware; use the indoor state for call progress and the outdoor event for notifications.
- Both native event-channel closes and logouts succeeded, and the observer exited.
- Indoor output volume was backed up, temporarily changed from 7 to 0, and restored to 7 with exact semantic readback after idle. Conversation volume stayed 7 throughout. No native intercom routing, Frigate or HA configuration was changed.

The initial no-button runs are not acceptance evidence: they exposed the native layout and historical-replay defects fixed before the real press. The temporary audio helper used the upstream write-only `type=audioOutput` field; replaying the GET XML without it was rejected without changing volume. Private raw receipts and rollback XML remain outside Git.

## Before A Device Pilot

The checked devices return the exact configured model strings, including `(B)` outdoors. Recheck after firmware updates or replacement. A device reporting the KV6113 model without that revision suffix remains deliberately rejected; no speculative model alias was added.

Next separately authorize a reversible deployment and validate actual MQTT/HA notification delivery, answered-call state/audio, and broker/device recovery. The local ring/dismiss observation above does not replace those gates. Unlock and Stop ringing tests require separate explicit consent and someone at the door.

## SDK Upgrade Rehearsal

The user-downloaded official Linux64 **6.1.9.48 build20230410** bundle passed isolated startup and read-only device checks, followed by a separate local ring/dismiss observation using the deduplication fix. The candidate produced one notification intent, ignored historical callbacks, and passed native cleanup; temporary indoor mute was restored with exact readback. No MQTT or physical call-control commands were used. Actual acoustic silence was not separately user-confirmed in the candidate run. It remains staged outside Git, not installed or published; bundled amd64 **6.1.6.45** and ARM64 **6.1.8.101** are unchanged. See [candidate evidence and promotion gates](hikvision-doorbell/sdkversions.md#candidate-ring-observation---2026-10-06). The newer 6.1.11.30 packages have not been acquired; MQTT, answered-call, control-effect and recovery acceptance remain pending.

## Attribution And Distribution

The protocol work and bundled Hikvision SDK come from the upstream project and its contributors. No project-wide upstream license was found during the audit. The retained example's Apache license is not a license for the whole application or the vendor SDK. Clarify modified-application and SDK redistribution rights before publishing a release image or distributing the modified application. No new license is asserted here.