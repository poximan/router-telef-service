import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import config
from .tcp_probe import TcpProbe
from .mqtt_publisher import MqttPublisher

logging.basicConfig(format="[%(asctime)s] %(levelname)s %(name)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("router-telef-service")

app = FastAPI(title="router-telef-service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"]
)

_probe = TcpProbe(
    base_url=config.CHECK_HOST_BASE_URL,
    max_nodes=config.CHECK_HOST_MAX_NODES,
    success_latency=config.CHECK_HOST_SUCCESS_LATENCY_SECONDS,
    result_timeout=config.CHECK_HOST_RESULT_TIMEOUT_SECONDS,
    poll_interval=config.CHECK_HOST_POLL_INTERVAL_SECONDS,
    request_timeout=config.CHECK_HOST_REQUEST_TIMEOUT_SECONDS,
)
_publisher: MqttPublisher | None = None
_monitor_task: asyncio.Task | None = None
_state_lock = asyncio.Lock()
_current_state = {
    "ip": config.TARGET_IP,
    "port": config.TARGET_PORT,
    "state": "desconocido",
}
_last_published = None


async def _monitor_loop():
    global _last_published
    while True:
        try:
            state = await asyncio.to_thread(_probe.check, config.TARGET_IP, config.TARGET_PORT)
            if state not in {"abierto", "cerrado", "desconocido"}:
                state = "desconocido"
            async with _state_lock:
                _current_state["state"] = state
            if _publisher and state != _last_published:
                published = _publisher.publish_state(state)
                if published:
                    _last_published = state
                else:
                    logger.warning("No se pudo publicar estado %s, se reintentara tras el siguiente ciclo", state)
        except Exception as exc:
            logger.exception("Error en monitor TCP: %s", exc)
        await asyncio.sleep(config.PROBE_INTERVAL_SECONDS)


@app.on_event("startup")
async def on_startup():
    global _publisher, _monitor_task
    logger.info("Iniciando router-telef-service para %s:%s", config.TARGET_IP, config.TARGET_PORT)
    _publisher = MqttPublisher()
    _monitor_task = asyncio.create_task(_monitor_loop())


@app.on_event("shutdown")
async def on_shutdown():
    global _publisher, _monitor_task
    if _monitor_task:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
        _monitor_task = None
    if _publisher:
        _publisher.stop()
        _publisher = None
    logger.info("router-telef-service finalizado")


@app.get("/status")
async def get_status():
    async with _state_lock:
        return dict(_current_state)
