# Hikvision Doorbell Lite

Unreleased experimental bridge for DS-KV6113-WPE1(B) and DS-KH6320-WTE1 only.

Retains ring events, call state, outdoor Unlock, availability/recovery and Stop ringing. Camera media belongs in Frigate; notifications belong in Home Assistant automations.

This directory is the complete native add-on build context: manifest, Dockerfile, runtime, SDK bundles and tests. Supervisor builds it locally; no prebuilt image or separate bridge service is required. The October6 passive HA pilot is running with both stations online and six discovered MQTT entities. It remains experimental and manual-start; physical ring/phone, call and recovery acceptance is still pending.

Bundled SDK: amd64 6.1.9.48; ARM64 6.1.8.101. See [configuration and pilot requirements](DOCS.md), [SDK inventory](SDK.md), [offline development](DEVELOPMENT.md), and the [fork overview](../README.md). Durable operating constraints and recovery are in the root [MEMORY](../MEMORY.md).