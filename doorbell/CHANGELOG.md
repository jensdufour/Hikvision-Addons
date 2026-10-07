# Changelog

## 0.1.1-dev - Unreleased

- Read the alarm replay cutoff from the native SDK clock so it uses the same time basis as SDK event timestamps.
- Reject missing, incomplete or invalid clock responses before subscribing; retain existing replay and command guards.
- Cover native/ISAPI clock differences and the clock getter ABI in offline and network-disabled smoke checks.

## 0.1.0-dev - Unreleased

- Restrict the bridge to DS-KV6113-WPE1(B) and DS-KH6320-WTE1.
- Retain ring events, call state, outdoor Unlock, availability/recovery and Stop ringing.
- Replace per-entity MQTT clients and duplicate command handlers with one Paho client and native discovery.
- Add identity guards, non-retained/epoch-scoped commands, bounded queue age, safe callback copying and explicit cleanup.
- Remove media/audio features, scenes/alarms, raw ISAPI input, stdin, beta packaging and publishing workflows.
- Separate development requirements from the three direct runtime dependencies.
- Consolidate manifest, Dockerfile, source, tests and SDKs into one locally built HA add-on.
- Include the complete amd64 6.1.9.48 runtime and original notices; retain ARM64 6.1.8.101.
- Fix firmware ring normalization, native callback/pointer ABI, historical replay and outdoor poll deduplication.
- Correct optional Supervisor MQTT discovery for external brokers and require actual callback registration in native smoke checks.
- New configuration, slug and entity IDs require deliberate migration.

Upstream history remains at commit `8f8b97c6b5731e9979eee28d011db6b860b826e1`.