import json
import ssl
import threading
import time
import logging
import paho.mqtt.client as mqtt
from . import config

logger = logging.getLogger("router-telef-service.mqtt")


class MqttPublisher:
    def __init__(self) -> None:
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.MQTT_CLIENT_ID)
        self._client.username_pw_set(config.MQTT_BROKER_USERNAME, config.MQTT_BROKER_PASSWORD)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        if config.MQTT_BROKER_USE_TLS:
            context = ssl.create_default_context()
            if config.MQTT_BROKER_CA_CERT:
                context.load_verify_locations(cafile=config.MQTT_BROKER_CA_CERT)
            if config.MQTT_CLIENT_CERTFILE and config.MQTT_CLIENT_KEYFILE:
                context.load_cert_chain(config.MQTT_CLIENT_CERTFILE, config.MQTT_CLIENT_KEYFILE)
            if config.MQTT_TLS_INSECURE:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            self._client.tls_set_context(context)

        self._lock = threading.RLock()
        self._connected = False
        self._connected_event = threading.Event()
        self._stopping = False
        self._reconnect_lock = threading.Lock()
        self._client.loop_start()
        self._connect()

    def _connect(self) -> None:
        backoff = 2
        while True:
            try:
                self._client.connect(
                    config.MQTT_BROKER_HOST,
                    config.MQTT_BROKER_PORT,
                    keepalive=config.MQTT_BROKER_KEEPALIVE,
                )
                return
            except Exception as exc:
                logger.error("Conexion MQTT fallida: %s", exc)
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)

    def _on_connect(self, _client, _userdata, _flags, rc, _properties=None):
        self._connected = (rc == 0)
        if self._connected:
            logger.info("MQTT conectado (rc=%s)", rc)
            self._connected_event.set()
        else:
            logger.error("MQTT no pudo conectar (rc=%s)", rc)
            self._connected_event.clear()

    def _on_disconnect(self, _client, _userdata, rc, _properties=None):
        self._connected = False
        logger.warning("MQTT desconectado (rc=%s)", rc)
        self._connected_event.clear()
        if not self._stopping:
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        if self._reconnect_lock.acquire(blocking=False):
            def _reconnect():
                try:
                    self._connect()
                finally:
                    self._reconnect_lock.release()
            threading.Thread(target=_reconnect, daemon=True).start()

    def publish_state(self, state: str) -> bool:
        payload = {
            "estado": state,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        data = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            if not self._connected_event.wait(timeout=5):
                logger.error("No hay conexion MQTT disponible para publicar estado %s", state)
                self._schedule_reconnect()
                return False
            try:
                result = self._client.publish(
                    config.STATUS_TOPIC,
                    data,
                    qos=config.MQTT_QOS,
                    retain=config.MQTT_RETAIN,
                )
                result.wait_for_publish()
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(f"publicacion MQTT fallo rc={result.rc}")
                logger.info("Publicado estado %s en %s", state, config.STATUS_TOPIC)
                return True
            except Exception as exc:
                logger.error("Fallo publicando estado %s: %s", state, exc)
                self._schedule_reconnect()
                return False

    def stop(self) -> None:
        self._stopping = True
        try:
            self._client.loop_stop()
        finally:
            self._client.disconnect()
