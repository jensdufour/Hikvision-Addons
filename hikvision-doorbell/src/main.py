import signal
import sys
from queue import Empty, Queue
from threading import Event
from time import monotonic

from loguru import logger

from config import load_config
from doorbell import Doorbell
from event import EventManager
from mqtt import MQTTBridge
from sdk.utils import loadSDK, setupSDK, shutdownSDK


def report_state(device, state, bridge, initial=False, observed=None, *, polled=False):
    observed = monotonic() if observed is None else observed
    if (not polled or not device.outdoor or initial) and observed >= device.last_ring_state_at:
        device.last_ring_state_at = observed
        if state == "ringing":
            if not device.ring_active and not initial:
                bridge.ring(device)
            device.ring_active = True
        elif state in ("idle", "oncall"):
            device.ring_active = False
    if observed < device.last_state_at:
        return
    device.last_state_at = observed
    device.state = state
    bridge.publish_state(device)


def drain_alarms(alarms, devices, bridge):
    for _ in range(alarms.qsize()):
        try:
            handle_message(alarms.get_nowait(), devices, bridge)
        except Empty:
            break


def disconnect_device(device, bridge):
    try:
        device.logout()
    except Exception as error:
        logger.error("Cleanup incomplete for {}: {}", device.config.name, error)
    finally:
        device.next_check = monotonic() + 30
        bridge.publish_state(device)


def check_device(device, devices, bridge, poll_seconds, alarms=None):
    initial = not device.online
    observed = monotonic()
    try:
        if initial:
            device.authenticate()
            if any(other is not device and other.serial == device.serial for other in devices):
                raise ValueError("Duplicate device serial")
            device.poll_supported = True
            state = device.get_call_state()
            device.connected_at = monotonic()
            device.setup_alarm()
            device.online = True
            bridge.refresh_needed = True
            logger.info("Connected to {} ({})", device.config.name, device.config.model)
        else:
            device.check_identity()
            state = device.get_call_state()
            if not device.poll_supported:
                observed = device.last_state_at
                if monotonic() - device.last_event < 120:
                    state = device.state
        if alarms is not None:
            drain_alarms(alarms, devices, bridge)
        report_state(device, state, bridge, initial=initial, observed=observed, polled=True)
        device.next_check = monotonic() + poll_seconds
    except Exception as error:
        logger.warning("{} offline: {}; retry in 30 seconds", device.config.name, type(error).__name__)
        disconnect_device(device, bridge)


def handle_message(message, devices, bridge):
    if message[0] == "alarm":
        _, user_id, serial, state, received = message
        for device in devices:
            if (device.online and device.user_id == user_id and device.sdk_serial == serial
                    and received >= device.connected_at):
                device.last_event = received
                report_state(device, state, bridge, observed=received)
                break
        return
    _, device, action, epoch, generation, received = message
    if (not bridge.connected or not device.online or epoch != bridge.epoch
            or generation != device.generation or monotonic() - received > 3):
        return
    try:
        if action == "unlock":
            device.unlock_door()
        elif action == "stop_ringing":
            state = device.get_call_state()
            if not bridge.connected or epoch != bridge.epoch or monotonic() - received > 3:
                return
            device.stop_ringing(state)
        else:
            return
        device.next_check = 0
    except Exception as error:
        logger.error("{} command failed ({}); not retrying", device.config.name, type(error).__name__)
        disconnect_device(device, bridge)


def main():
    config = load_config()
    logger.remove()
    logger.add(sys.stdout, level=config.system.log_level)
    stopping = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stopping.set())
    inbox = Queue(maxsize=128)
    alarms = Queue(maxsize=128)
    sdk = loadSDK()
    devices = [Doorbell(options, sdk) for options in config.doorbells]
    bridge = MQTTBridge(config.mqtt, devices, inbox)
    try:
        setupSDK(sdk)
        events = EventManager(sdk, alarms, devices)
        events.start()
        bridge.start()
        while not stopping.is_set():
            drain_alarms(alarms, devices, bridge)
            if bridge.refresh_needed:
                bridge.refresh()
            for device in devices:
                if stopping.is_set():
                    break
                if monotonic() >= device.next_check:
                    check_device(device, devices, bridge, config.system.poll_seconds, alarms)
            try:
                message = inbox.get(timeout=0.2)
                if not stopping.is_set():
                    handle_message(message, devices, bridge)
            except Empty:
                pass
    finally:
        for device in devices:
            try:
                device.logout()
            except Exception as error:
                logger.error("Device cleanup failed for {}: {}", device.config.name, error)
        try:
            bridge.stop()
        finally:
            shutdownSDK(sdk)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        logger.error("Bridge stopped: {}. Check configuration and connectivity.", type(error).__name__)
        sys.exit(1)