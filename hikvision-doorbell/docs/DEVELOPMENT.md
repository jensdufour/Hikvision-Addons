# Offline Development

Use Python 3.10 or later and an isolated environment. From `hikvision-doorbell`:

```sh
pip install -r requirements-dev.txt
pytest -q
flake8 src tests --select=E9,F63,F7,F82 --show-source
```

Tests use mock devices, block sockets and block vendor-library loading. Do not disable those guards to make a test pass. The production image installs only runtime requirements.

The main thread serializes device operations. SDK callbacks copy the small event fields to a bounded queue; Paho callbacks queue validated commands. Connection generations, broker epochs and a three-second queue limit discard stale commands. The queue is not a durable command store.

Keep protocol calls in `src/doorbell.py`, MQTT discovery/transport in `src/mqtt.py`, callback decoding in `src/event.py`, and lifecycle/state handling in `src/main.py`. Do not recreate an entity framework or a second command surface.

For a Linux smoke test, build the runtime image and load/register/clean up the SDK with networking disabled. Never provide actual device options to that check. CI performs isolated builds on native amd64 and aarch64 runners and has no publishing permission.

See the root README for firmware acceptance, migration and unresolved distribution terms.