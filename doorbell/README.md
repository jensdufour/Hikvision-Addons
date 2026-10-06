# Hikvision Doorbell Lite

Unreleased experimental bridge for DS-KV6113-WPE1(B) and DS-KH6320-WTE1 only.

Retains ring events, call state, outdoor Unlock, availability/recovery and Stop ringing. Camera media belongs in Frigate; notifications belong in Home Assistant automations.

This directory is the complete native add-on build context: manifest, Dockerfile, runtime, SDK bundles and tests. Supervisor builds it locally; no prebuilt image or separate bridge service is required. The add-on is experimental and defaults to manual startup.

Bundled SDK: amd64 6.1.9.48; ARM64 6.1.8.101. See [configuration and migration](DOCS.md), [SDK inventory](SDK.md), [offline development](DEVELOPMENT.md), and the [fork overview](../README.md). Reusable engineering constraints are in the root [MEMORY](../MEMORY.md).