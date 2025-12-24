import os

TARGET_IP = "2.6.1.3"
TARGET_PORT = 4
PROBE_INTERVAL_SECONDS = 300
CHECK_HOST_BASE_URL = "https://check-host.net"
CHECK_HOST_MAX_NODES = 3
CHECK_HOST_SUCCESS_LATENCY_SECONDS = 3.0
CHECK_HOST_RESULT_TIMEOUT_SECONDS = 20.0
CHECK_HOST_POLL_INTERVAL_SECONDS = 2.0
CHECK_HOST_REQUEST_TIMEOUT_SECONDS = 5.0
STATUS_TOPIC = os.getenv("MQTT_TOPIC_MODEM_CONEXION", "exemys/estado/conexion_modem")
MQTT_QOS = int(os.getenv("MQTT_PUBLISH_QOS_STATE", "1"))
MQTT_RETAIN = os.getenv("MQTT_PUBLISH_RETAIN_STATE", "true").lower() in {"1", "true", "yes", "on"}
MQTT_CLIENT_ID = os.getenv("MQTT_ROUTER_CLIENT_ID", "router-telef-service")

def _req_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise EnvironmentError(f"Falta variable de entorno obligatoria: {name}")
    return value.strip()

MQTT_BROKER_HOST = _req_env("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(_req_env("MQTT_BROKER_PORT"))
MQTT_BROKER_USERNAME = _req_env("MQTT_BROKER_USERNAME")
MQTT_BROKER_PASSWORD = _req_env("MQTT_BROKER_PASSWORD")
MQTT_BROKER_KEEPALIVE = int(os.getenv("MQTT_BROKER_KEEPALIVE", "60"))
MQTT_BROKER_USE_TLS = os.getenv("MQTT_BROKER_USE_TLS", "false").lower() in {"1", "true", "yes", "on"}
MQTT_TLS_INSECURE = os.getenv("MQTT_TLS_INSECURE", "false").lower() in {"1", "true", "yes", "on"}
MQTT_BROKER_CA_CERT = os.getenv("MQTT_BROKER_CA_CERT")
MQTT_CLIENT_CERTFILE = os.getenv("MQTT_CLIENT_CERTFILE")
MQTT_CLIENT_KEYFILE = os.getenv("MQTT_CLIENT_KEYFILE")
