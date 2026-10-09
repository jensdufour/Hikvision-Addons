import hashlib
import json
import secrets
from queue import Full
from time import monotonic

from loguru import logger
from paho.mqtt.client import CallbackAPIVersion, Client


class MQTTBridge:
    def __init__(self, config, devices, inbox):
        self.config = config
        self.devices = devices
        self.inbox = inbox
        self.connected = False
        self.connected_at = 0.0
        self.refresh_needed = False
        self.epoch = ""
        self.commands = {}
        identity = ",".join(sorted(self.base(device) for device in devices))
        instance = hashlib.sha256(identity.encode()).hexdigest()[:12]
        self.availability = f"hikvision_lite/bridge/{instance}/availability"
        self.client = Client(CallbackAPIVersion.VERSION2, client_id=f"hikvision_lite_{instance}", clean_session=True)
        self.client.max_queued_messages_set(128)
        self.client.reconnect_delay_set(1, 30)
        if config.username:
            password = config.password.get_secret_value() if config.password else None
            self.client.username_pw_set(config.username, password)
        if config.ssl:
            self.client.tls_set()
        self.client.will_set(self.availability, "offline", qos=1, retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    @staticmethod
    def base(device):
        identity = f"{device.config.ip}:{device.config.port}"
        address = hashlib.sha256(identity.encode()).hexdigest()[:12]
        return f"hikvision_lite/{address}"

    def start(self):
        self.client.connect_async(self.config.host, self.config.port, keepalive=30)
        self.client.loop_start()

    def stop(self):
        if self.connected:
            self.client.publish(self.availability, "offline", qos=1, retain=True).wait_for_publish(timeout=2)
        self.client.disconnect()
        self.client.loop_stop()
        self.connected = False
        self.epoch = ""

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            return
        self.epoch = secrets.token_hex(12)
        self.connected_at = monotonic()
        self.connected = True
        self.commands = {}
        self.refresh_needed = True
        client.subscribe("homeassistant/status", qos=0)

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        self.epoch = ""
        self.commands = {}

    def on_message(self, client, userdata, message):
        if message.topic == "homeassistant/status" and message.payload == b"online":
            self.refresh_needed = True
            return
        target = self.commands.get(message.topic)
        if not self.connected or not target or message.retain or message.payload != b"PRESS":
            return
        device, action, epoch, generation = target
        if not device.online or epoch != self.epoch or generation != device.generation:
            return
        try:
            self.inbox.put_nowait(("command", device, action, epoch, generation, monotonic()))
        except Full:
            logger.warning("Command queue full; command discarded")

    def refresh(self):
        if not self.connected:
            return
        self.refresh_needed = False
        previous = self.commands
        self.commands = {}
        for topic in previous:
            self.client.unsubscribe(topic)
        for device in self.devices:
            self.publish_state(device)
            if device.serial:
                self.discover(device)
        self.client.publish(self.availability, "online", qos=1, retain=True)

    def publish_state(self, device):
        if self.connected:
            base = self.base(device)
            self.client.publish(f"{base}/state", device.state, qos=1, retain=True)
            self.client.publish(f"{base}/availability", "online" if device.online else "offline", qos=1, retain=True)

    def ring(self, device):
        if self.connected and device.online and device.outdoor:
            self.client.publish(f"{self.base(device)}/ring", json.dumps({"event_type": "ring"}), qos=0, retain=False)

    def card(self, device, kind, card_number, occurred):
        if self.connected and device.online and device.outdoor:
            self.client.publish(f"{self.base(device)}/card", json.dumps({
                "event_type": kind, "card_number": card_number, "device_time": occurred.isoformat()
            }), qos=0, retain=False)

    def discover(self, device):
        base = self.base(device)
        epoch = self.epoch
        identifier = hashlib.sha256(device.serial.encode()).hexdigest()[:16]
        metadata = {"identifiers": [device.serial], "name": device.config.name, "manufacturer": "Hikvision",
                    "model": device.config.model, "sw_version": device.firmware}
        common = {"device": metadata, "availability_mode": "all", "availability": [
            {"topic": self.availability}, {"topic": f"{base}/availability"}]}
        entities = [("sensor", "call_state", {"name": "Call state", "state_topic": f"{base}/state", "icon": "mdi:phone"}),
                    ("button", "stop_ringing", {"name": "Stop ringing", "icon": "mdi:phone-cancel"})]
        if device.outdoor:
            entities += [("event", "ring", {"name": "Doorbell", "state_topic": f"{base}/ring", "event_types": ["ring"], "device_class": "doorbell"}),
                         ("event", "card", {"name": "Card access", "state_topic": f"{base}/card", "event_types": ["card_unlock", "card_rejected"], "icon": "mdi:card-account-details-outline"}),
                         ("button", "unlock", {"name": "Unlock", "icon": "mdi:door-open"})]
        for domain, key, options in entities:
            payload = {**common, **options, "unique_id": f"hikvision_lite_{identifier}_{key}"}
            if domain == "button":
                topic = f"{base}/command/{epoch}/{device.generation}/{key}"
                payload.update(command_topic=topic, payload_press="PRESS", retain=False, qos=0)
                self.commands[topic] = (device, key, epoch, device.generation)
                self.client.subscribe(topic, qos=0)
            self.client.publish(f"homeassistant/{domain}/hikvision_lite_{identifier}/{key}/config",
                                json.dumps(payload), qos=1, retain=True)