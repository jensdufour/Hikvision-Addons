# Engineering Constraints

## Documentation Boundary

Keep deployment records, site-specific test results, approvals, network policies,
backup locations and operational task lists in private operations documentation.
Public documentation describes the software, supported models, configuration,
generic security limits, development checks and SDK provenance only.

## Scope And Packaging

- One Supervisor-managed add-on for DS-KV6113-WPE1(B) and DS-KH6320-WTE1. MQTT carries events/state/commands; HA owns notifications and camera media stays outside the bridge.
- Runtime, tests, manifest, Dockerfile and architecture bundles live in `doorbell/`. Supervisor builds locally; do not add another standalone production path.
- One Paho client, native MQTT discovery and three direct runtime dependencies. Manual broker options are supported; optional Supervisor discovery uses `mqtt:want` and fails closed if needed but unavailable.
- Keep credentials, local options, caches and backups out of Git and images. Preserve vendor bytes and original notices. The bundled SDK does not license the whole application.

## Protocol And Safety

- Verify exact model and stable serial before enabling controls. Do not add speculative model aliases, including omission of `(B)`. Device replacement at an existing address requires deliberate reviewed restart.
- Commands are non-retained, broker-epoch/device-generation scoped, expire after three seconds and are not retried after ambiguous failures. Fallback is allowed only on SDK error23. Unlock is outdoor-only; Stop ringing requires fresh ringing state and sends reject, never answer/hang-up.
- Epochs are not publisher authentication. Restrict broker access and command-topic publishing according to the installation's trust boundary.
- Callbacks copy values before returning. Keep separate bounded alarm/command queues and drain alarms before committing a newer poll snapshot.
- Outdoor SDK events own notification episodes independently of displayed state. Routine outdoor polls cannot emit a press or clear the latch. Accepted SDK dismissal re-arms it; older events cannot rewind the episode. Startup/reconnect seeds state without replay. A missed dismissal favors suppression until dismissal/new-session evidence, not a guessed timeout.
- Devices may upload historical events in realtime mode. Capture the native SDK clock at subscription (GetDVRConfig118, six32-bit DWORDs) and reject invalid/older timestamps. ISAPI localTime can use a different DST representation and must not set this cutoff. Reject truncated/invalid native reads; correct clock regression and reconnect rather than weakening replay protection.
- SDK LONG is signed32-bit, callback serial offset is12, V50 setup takes a pointer, and GetErrorMsg takes LONG*. Do not substitute host c_long or truncate ABI structures/unions.
- Cleanup attempts both channel close and logout, retaining failed handles. Unresolved cleanup blocks relogin and keeps controls unavailable while the30-second recovery path retries. SDK/bridge shutdown must still be attempted.
- Unsupported polling falls back to events; stale event-only state becomes unknown after120seconds. It cannot authorize Stop ringing.

## Validation

- Keep socket and native-library guards enabled in offline tests. Native smoke checks run with networking disabled and must call EventManager.start() before reporting callback registration.
- SDK version is meaningful only after Init. Check version, callback registration, error lookup and cleanup on each architecture; these checks do not establish physical-device acceptance.
- Use the matched SDK bundle and its crypto libraries. See `doorbell/SDK.md` for versions and dependency limitations; do not replace an OpenSSL major version blindly.
- For mounted Python scripts, set the source import path explicitly. PYTHONPATH does not outrank cwd when using `python -c`.