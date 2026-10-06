# Changelog

## 0.1.0-dev - Unreleased

- Restrict the bridge to DS-KV6113-WPE1(B) and DS-KH6320-WTE1.
- Retain ring events, call state, outdoor Unlock, availability/recovery and Stop ringing.
- Replace per-entity MQTT clients and duplicate command handlers with one Paho client and native discovery.
- Add identity guards, non-retained/epoch-scoped commands, bounded queue age, safe callback copying and explicit cleanup.
- Remove media/audio features, scenes/alarms, raw ISAPI input, stdin, beta packaging and publishing workflows.
- Separate development requirements from the three direct runtime dependencies.
- New configuration, slug and entity IDs require deliberate migration. No hardware acceptance or published image yet.

Upstream history remains at commit `8f8b97c6b5731e9979eee28d011db6b860b826e1`.