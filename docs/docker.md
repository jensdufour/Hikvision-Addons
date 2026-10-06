# Standalone Docker

This is an unreleased offline prototype. Building locally does not establish compatibility with the devices' firmware or authorize deployment.

From the repository root, build for the machine architecture:

```sh
docker build --build-arg BUILD_ARCH=amd64 -t hikvision-doorbell-lite:local hikvision-doorbell
docker run --rm --network none hikvision-doorbell-lite:local -c "from sdk.utils import loadSDK, setupSDK, shutdownSDK; sdk = loadSDK(); setupSDK(sdk); shutdownSDK(sdk)"
```

For ARM, use `--platform linux/arm64 --build-arg BUILD_ARCH=aarch64`. Keep platform and SDK architecture aligned.

If a corporate network requires a public package mirror, pass `--build-arg PIP_INDEX_URL=https://your-public-mirror/simple/`. Do not disable TLS or put credentials into build arguments.

For a separately approved real deployment, provide JSON options at `/data/options.json`, or set `CONFIG_FILE_PATH` to its read-only mounted location. `hikvision-doorbell/default_config.json` is a nonfunctional example using documentation IPs. Local `options.json` is ignored by Git. Never commit credentials.

The compose file uses a read-only options mount, no published ports, and no host network. Its `BUILD_ARCH` defaults to `amd64`; set it to `aarch64` on ARM. It does not mount Home Assistant config or media. Do not run compose during offline validation: a configured runtime intentionally connects to the broker and devices.

Do not run the upstream bridge simultaneously during migration. New entity IDs and exact model guards are documented in [add-on documentation](../doorbell/DOCS.md).