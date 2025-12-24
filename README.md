# router-telef-service

Microservicio encargado de vigilar la conectividad TCP del router TelefÃ³nica (IP y puerto definidos en `src/config.py`) y distribuir ese estado tanto por HTTP como por MQTT.

## CaracterÃ­sticas

- **Sondeo externo**: delega la verificaciÃ³n a [check-host.net](https://check-host.net) mediante una consulta inicial (`/check-tcp`) y la lectura periÃ³dica de resultados (`/check-result/{request_id}`).
- **DecisiÃ³n de estado**:
  - `abierto`: al menos uno de los nodos remotos se conectÃ³ con latencia â‰¤ 3 s.
  - `cerrado`: todos los nodos respondieron con error dentro del timeout de 20 s.
  - `desconocido`: no hubo respuesta completa en el tiempo disponible o la cadena fallÃ³.
- **PublicaciÃ³n MQTT**: solo emite un mensaje cuando el estado cambia, en JSON `{"estado":"abierto|cerrado|desconocido","ts":"...Z"}` (tÃ³pico configurable, por defecto `exemys/estado/conexion_modem`).
- **API HTTP**: expone `/status` para que otros servicios (p.ej. panelexemys) lean el estado fresco en la LAN dockerizada.
- **Loop no bloqueante**: el monitoreo corre en un `asyncio.Task`, delegando el chequeo a un `ThreadPool` y manteniendo el servidor FastAPI responsivo.

## Estructura

```
src/
 â”œâ”€ app.py            # FastAPI + loop de monitoreo + endpoints
 â”œâ”€ tcp_probe.py      # Cliente HTTP contra check-host.net
 â”œâ”€ mqtt_publisher.py # Wrapper paho-mqtt con reconexiÃ³n
 â”œâ”€ config.py         # Constantes (host objetivo, poll/timeout, broker, etc.)
 â””â”€ __init__.py
requirements.txt      # FastAPI, requests, paho-mqtt, etc.
Dockerfile            # Imagen slim de Python 3.12
```

## ConfiguraciÃ³n

Variables destacadas (ver `src/config.py` para la lista completa):

| Variable | DescripciÃ³n |
|----------|-------------|
| `TARGET_IP` / `TARGET_PORT` | Destino TCP (por defecto 200.63.163.36:40000). |
| `PROBE_INTERVAL_SECONDS` | Intervalo entre chequeos consecutivos. |
| `CHECK_HOST_*` | Base URL, cantidad de nodos, latencia aceptable y timeouts para check-host. |
| `MQTT_*` | Host, credenciales, QoS, retain y TLS para publicar el estado. |
| `STATUS_TOPIC` | TÃ³pico MQTT donde se envÃ­a `{"estado": "...", "ts": "..."}`. |

Los parÃ¡metros sensibles (broker y credenciales) se inyectan vÃ­a variables de entorno (`.env` en el workspace, docker-compose o Kubernetes).

## API HTTP

| MÃ©todo | Ruta     | DescripciÃ³n                                                 |
|--------|----------|-------------------------------------------------------------|
| GET    | `/health`| Probar que el contenedor estÃ¡ vivo (respuesta JSON simple). |
| GET    | `/status`| Devuelve `{"ip": "...", "port": 40000, "state": "abierto"}`.|

## MQTT

- TÃ³pico: `STATUS_TOPIC` (`exemys/estado/conexion_modem` por defecto).
- Payload: `{"estado":"abierto|cerrado|desconocido","ts":"2025-12-16T14:32:09Z"}`.
- QoS / Retain: definidos en `config.py` (retained para que los clientes reciban el Ãºltimo snapshot al suscribirse).

## EjecuciÃ³n local

```bash
# Requisitos: Python 3.12 y pip
cd monimonitor/router-telef-service
python -m venv .venv
. .venv/Scripts/activate   # en Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
export MQTT_BROKER_HOST=...
export MQTT_BROKER_PORT=...
# (definir el resto de variables obligatorias)
uvicorn src.app:app --reload --port 8086
```

> Nota: en producciÃ³n el servicio se despliega mediante Docker (`Dockerfile` + `docker-compose.yml` del workspace), que ya copia el cÃ³digo, instala dependencias y expone el puerto `8086`.

## Registro y monitoreo

- Se usa `logging` estÃ¡ndar (configurado en `src/app.py`) para registrar eventos de monitoreo y publicaciÃ³n MQTT.
- El loop imprime advertencias cuando check-host.net entrega errores o latencias fuera de rango.
- En caso de pÃ©rdida de conexiÃ³n con el broker, `mqtt_publisher.py` maneja reconexiones con backoff y reintenta la publicaciÃ³n en el siguiente ciclo.

## Seguridad

- No se almacenan credenciales en el repositorio: todo se lee vÃ­a variables de entorno.
- El servicio HTTP solo ofrece `/health` y `/status`, sin exponer datos sensibles del broker.
- Los certificados TLS (si se usa MQTT seguro) se montan como archivos externos en el contenedor.

## PrÃ³ximos pasos sugeridos

- AÃ±adir mÃ©tricas (Prometheus o logs estructurados) si se desea observar latencias y tasa de fallos de check-host en tiempo real.
- Incorporar pruebas unitarias para `tcp_probe.py` usando mocks de la API externa.
