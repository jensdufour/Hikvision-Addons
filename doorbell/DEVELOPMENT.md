# Development

Use Python 3.10 or later in an isolated environment. From `doorbell/`:

```sh
pip install -r requirements-dev.txt
pytest -q
flake8 src tests --select=E9,F63,F7,F82 --show-source
```

Tests block network connections and vendor-library loading. Keep those guards enabled. Runtime images install only the three production requirements.

## Native Smoke Check

From the repository root on a Linux Docker host:

```sh
docker build --build-arg BUILD_ARCH=amd64 -t hikvision-doorbell-lite:test doorbell
docker run --rm --network none --mount type=bind,src="$PWD/doorbell/tests/smoke_sdk.py",dst=/smoke_sdk.py,readonly --entrypoint python3 hikvision-doorbell-lite:test /smoke_sdk.py 6.1.9.48
```

For ARM64, use an ARM host or emulation, `--platform linux/arm64`, `BUILD_ARCH=aarch64`, and expected version `6.1.8.101`. CI uses native architecture runners. These containers are disposable development tools, not another installation option. Never pass real device options to a smoke test.

## Code Ownership

| File | Responsibility |
| --- | --- |
| `src/config.py` | Strict options validation and Supervisor MQTT lookup |
| `src/doorbell.py` | Device identity, status and the two permitted commands |
| `src/event.py` | Native callback copying, identity and replay filtering |
| `src/main.py` | Serialized SDK operations, queues, state and recovery |
| `src/mqtt.py` | One Paho client, native discovery and guarded command topics |

`src/sdk/` owns the native bindings. Retain the full layout of used structures/unions and the 32-bit SDK LONG. Do not turn the reduced bridge back into a generic entity or command framework.

The build context is allowlisted to source, runtime requirements, matched SDK bundles and license notices. Local options, secrets, caches, tests and documentation are excluded from the image. Local examples use documentation-only addresses.

CI runs offline tests, focused lint and network-disabled native checks; it has read-only repository permissions and no image publishing or device credentials. Successful CI is not evidence of HA installation or physical command effects. See the root README for remaining acceptance gates.