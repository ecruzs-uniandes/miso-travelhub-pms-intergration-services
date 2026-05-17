# pms-integration-services

**TravelHub — Grupo 9 | MISW4501 — Uniandes**

Microservicio de integración con sistemas PMS (Property Management Systems). Recibe webhooks de proveedores externos (Hotelbeds, TravelClick, RoomRaccoon), valida idempotencia y publica comandos de sincronización en Kafka.

---

## Tabla de Contenidos

- [Arquitectura](#arquitectura)
- [Stack Tecnológico](#stack-tecnológico)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Variables de Entorno](#variables-de-entorno)
- [Instalación Local](#instalación-local)
- [Ejecutar con Docker](#ejecutar-con-docker)
- [API Reference](#api-reference)
- [Autenticación](#autenticación)
- [Patrones de Diseño](#patrones-de-diseño)
- [Tests](#tests)
- [Deploy a Cloud Run](#deploy-a-cloud-run)

---

## Arquitectura

```
PMS Externo (Hotelbeds / TravelClick / RoomRaccoon)
        │
        │  POST /api/v1/pms/webhook
        ▼
┌─────────────────────────────────────────────────────┐
│            pms-integration-services                 │
│                                                     │
│  Chain of Responsibility (Middleware)               │
│  ┌──────────┐ ┌───────────┐ ┌──────┐ ┌──────────┐ │
│  │   Auth   │→│ RateLimit │→│  IP  │→│   RBAC   │ │
│  └──────────┘ └───────────┘ └──────┘ └──────────┘ │
│                                                     │
│  Facade (WebhookFacade)                             │
│  1. Validar schema (Pydantic)                       │
│  2. Resolver hotel_id desde PMSProperty             │
│  3. Verificar idempotencia (SyncEvent.event_id)     │
│  4. Registrar evento (status: received)             │
│  5. Construir SyncCommand (Command pattern)         │
│  6. Publicar en Kafka → pms-sync-queue              │
│  7. Actualizar status → queued                      │
│  8. Responder 202 Accepted                          │
└─────────────────────────────────────────────────────┘
        │
        │  Kafka topic: pms-sync-queue
        ▼
   pms-sync-worker (servicio separado)
```

**ASR aplicado:** AH004 — Sincronizar 1,200 propiedades en ≤ 2 minutos con reintentos e idempotencia.

---

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Framework | Python 3.11 + FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Base de Datos | PostgreSQL 15 (Cloud SQL) |
| Cola de mensajes | Apache Kafka (confluent-kafka-python) |
| Validación | Pydantic v2 |
| Tests | pytest + pytest-asyncio + httpx |
| Contenedor | Docker → Cloud Run |
| Puerto | 8000 |

---

## Estructura del Proyecto

```
pms-integration-services/
├── app/
│   ├── main.py                     # FastAPI app, lifespan, middleware, routers
│   ├── config.py                   # Configuración vía Pydantic BaseSettings
│   ├── database.py                 # Engine async, SessionLocal, Base, get_db
│   │
│   ├── models/                     # SQLAlchemy ORM models (schema canonical 2026-05-14)
│   │   ├── hotel.py                # tabla: hotel (canonical varchar id)
│   │   ├── habitacion.py           # tabla: habitacion (canonical)
│   │   ├── disponibilidad.py       # tabla: disponibilidad (era availability)
│   │   ├── pms_property.py         # tabla: pms_properties (auxiliar)
│   │   └── sync_event.py           # tabla: sync_events (idempotencia)
│   │
│   ├── schemas/                    # Pydantic schemas (request/response)
│   │   ├── webhook.py              # WebhookPayload, WebhookResponse
│   │   ├── pms_property.py         # PMSPropertyCreate/Update/Response
│   │   ├── availability.py         # DisponibilidadResponse (cols camelCase), SyncStatusResponse
│   │   └── common.py               # HealthResponse, ErrorResponse
│   │
│   ├── api/                        # Routers FastAPI
│   │   ├── webhook.py              # POST /api/v1/pms/webhook
│   │   ├── properties.py           # CRUD /api/v1/pms/properties
│   │   ├── availability.py         # GET /api/v1/pms/availability
│   │   └── health.py               # GET /health
│   │
│   ├── services/                   # Lógica de negocio
│   │   ├── webhook_facade.py       # Facade: orquesta todo el flujo del webhook
│   │   ├── kafka_producer.py       # Wrapper confluent-kafka con delivery callback
│   │   ├── idempotency_service.py  # Deduplicación por event_id + SHA-256
│   │   └── property_service.py     # CRUD de PMSProperty
│   │
│   ├── middleware/                 # Chain of Responsibility
│   │   ├── auth_middleware.py      # Paso 1: Decodifica JWT (sin verificar firma)
│   │   ├── rate_limit_filter.py    # Paso 2: 60 req/min por usuario/IP
│   │   ├── ip_validation_filter.py # Paso 3: Placeholder geolocalización
│   │   └── rbac_filter.py          # Paso 4: Control de acceso por rol
│   │
│   └── commands/
│       └── sync_command.py         # SyncCommand dataclass (Command pattern)
│
├── tests/
│   ├── conftest.py                 # Fixtures: SQLite in-memory, mock Kafka
│   ├── test_webhook.py             # 5 tests del endpoint webhook
│   ├── test_idempotency.py         # 4 tests de idempotencia
│   ├── test_properties.py          # 6 tests CRUD propiedades
│   ├── test_availability.py        # 4 tests consulta disponibilidad
│   └── test_middleware.py          # 5 tests Chain of Responsibility
│
├── Dockerfile
├── requirements.txt
├── pytest.ini
├── .env.example
├── deploy.sh
└── pms-integration-services.postman_collection.json
```

---

## Variables de Entorno

Copia `.env.example` a `.env` y ajusta los valores:

```bash
cp .env.example .env
```

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_HOST` | Host de PostgreSQL | `localhost` |
| `DATABASE_PORT` | Puerto de PostgreSQL | `5432` |
| `DATABASE_NAME` | Nombre de la base de datos | `travelhub` |
| `DATABASE_USER` | Usuario de la base de datos | `travelhub_app` |
| `DATABASE_PASSWORD` | Contraseña de la base de datos | — |
| `KAFKA_BOOTSTRAP_SERVERS` | Servidores Kafka | `localhost:9092` |
| `KAFKA_TOPIC_PMS_SYNC` | Topic de sincronización | `pms-sync-queue` |
| `KAFKA_ENABLED` | Habilita/deshabilita Kafka | `true` |
| `JWT_ISSUER` | Issuer del JWT | `https://auth.travelhub.app` |
| `JWT_AUDIENCE` | Audience del JWT | `travelhub-api` |
| `SERVICE_NAME` | Nombre del servicio | `pms-integration-services` |
| `SERVICE_PORT` | Puerto del servicio | `8000` |

> **Nota:** Con `KAFKA_ENABLED=false`, el servicio funciona en modo degradado: loggea el comando en lugar de publicarlo, pero sigue respondiendo 202.

---

## Instalación Local

### Requisitos

- Python 3.11+
- PostgreSQL 15 (o SQLite para desarrollo/tests)
- Kafka (opcional en dev con `KAFKA_ENABLED=false`)

### Pasos

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd pms-integration-services

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 5. Iniciar el servicio
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

El servicio estará disponible en `http://localhost:8000`.

Documentación interactiva (Swagger): `http://localhost:8000/docs`

---

## Ejecutar con Docker

```bash
# Build de la imagen
docker build -t pms-integration-services .

# Ejecutar con variables de entorno
docker run -p 8000:8000 \
  -e DATABASE_HOST=host.docker.internal \
  -e DATABASE_PORT=5432 \
  -e DATABASE_NAME=travelhub \
  -e DATABASE_USER=travelhub_app \
  -e DATABASE_PASSWORD=tu_password \
  -e KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
  -e KAFKA_ENABLED=true \
  pms-integration-services
```

### Docker Compose (dev rápido)

```yaml
version: "3.9"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_HOST=db
      - DATABASE_NAME=travelhub
      - DATABASE_USER=travelhub_app
      - DATABASE_PASSWORD=secret
      - KAFKA_ENABLED=false
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: travelhub
      POSTGRES_USER: travelhub_app
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
```

---

## API Reference

Base URL: `http://localhost:8000`

### Health

#### `GET /health`

Verifica conectividad con base de datos y Kafka.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "service": "pms-integration-services",
  "database": "ok",
  "kafka": "ok"
}
```

---

### Webhook — única API para actualizar `disponibilidad`, `tarifa` y `hotel`

> **Importante:** este servicio **no expone PUT/POST directos sobre `/availability` ni `/tarifas`**. La única vía para que un PMS externo escriba en esas tablas es enviar un evento al webhook. El flujo es asíncrono:
>
> ```
> PMS externo
>   │ POST /api/v1/pms/webhook  (JWT o HMAC)
>   ▼
> pms-integration-services      ── persiste sync_event (status='received') + publica SyncCommand a Kafka pms-sync-queue
>   │ HTTP 202 (no espera el worker)
>   ▼
> pms-sync-worker               ── consume del topic, ejecuta strategy según event_type, upsert en BD canonical
> ```
>
> Para **leer** disponibilidad ver `GET /api/v1/pms/availability` más abajo. Para revisar el resultado de un evento usar `GET /api/v1/pms/sync-status/{event_id}`.

#### `POST /api/v1/pms/webhook`

Recibe un evento de sincronización desde un PMS externo. Responde inmediatamente `202 Accepted` — el procesamiento real lo realiza `pms-sync-worker`.

**Autenticación:** JWT `hotel_admin` / `platform_admin` **O** HMAC (ver [Autenticación](#autenticación)).

#### Tipos de evento y qué tabla afectan

| `event_type` | Tabla destino (escrita por worker) | Notas |
|---|---|---|
| `availability_update` | `disponibilidad` (canonical, camelCase) | Upsert por `(habitacionId, fecha)`. Sólo toca `unidadesDisponibles` — `unidadesReservadas` lo gestiona booking-service y queda intacto. |
| `rate_update` | `tarifa` (canonical) | Upsert tarifa por habitación + rango de fechas. Requiere `data.room_mappings` (`pms_room_id → habitacion.id`). |
| `property_sync` | `hotel` (canonical) | Actualiza nombre/dirección/ciudad/país. NO sincroniza `habitacion` (la owna search-service). |

#### Request body — schema canonical (post-refactor 2026-05-14)

```json
{
  "event_id": "hotelbeds-evt-2026-08-001",
  "event_type": "availability_update",
  "pms_provider": "hotelbeds",
  "pms_property_id": "HB-BOG-001",
  "hotel_id": "d2e3f4a5-b6c7-8901-def0-234567890abc",
  "timestamp": "2026-08-01T10:00:00Z",
  "data": {
    "habitacion_id": "hab-bogota-001",
    "dates": [
      { "fecha": "2026-08-15", "unidades_disponibles": 3 },
      { "fecha": "2026-08-16", "unidades_disponibles": 0 },
      { "fecha": "2026-08-17", "unidades_disponibles": 5 }
    ]
  }
}
```

| Campo top-level | Tipo | Descripción |
|---|---|---|
| `event_id` | string | ID único del evento en el PMS (clave de idempotencia — un mismo `event_id` no se re-procesa). |
| `event_type` | string | Uno de: `availability_update`, `rate_update`, `property_sync`. |
| `pms_provider` | string | `hotelbeds`, `travelclick`, `roomraccoon`, etc. Combinado con `pms_property_id` debe matchear una fila en `pms_properties`. |
| `pms_property_id` | string | ID de la propiedad en el sistema PMS externo. |
| `hotel_id` | string | UUID/varchar del hotel canonical. NO se usa en validación — el `hotel_id` real se resuelve desde `pms_properties.hotel_id`. Se acepta por compat. |
| `timestamp` | datetime ISO 8601 | Cuándo ocurrió el evento en el PMS. |
| `data` | object | Payload variable según `event_type` — ver tablas debajo. |

#### `data` para `availability_update`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `habitacion_id` | string | ✅ | ID canónico de la habitación (FK a `habitacion.id`). Legacy `room_id` aún se acepta. |
| `dates` | array<object\> | ✅ | Lista de fechas con su disponibilidad. Cada item: |
| `dates[].fecha` | date `YYYY-MM-DD` | ✅ | Fecha de la disponibilidad. Legacy `date` aún se acepta. |
| `dates[].unidades_disponibles` | int | ✅ | Cuántos cuartos del tipo libres en el PMS. Legacy `available_units` / `unidadesDisponibles` aún se aceptan. |
| `dates[].unidades_reservadas` | int | — | Opcional. Default 0. **Solo aplica al INSERT (fila nueva)** — en UPDATE de filas existentes el worker NO lo modifica (lo gestiona booking-service). |

#### `data` para `rate_update`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `room_mappings` | object | ✅ | Mapa `pms_room_id → habitacion.id` canonical. Sin mapping, el rate se omite con warning. |
| `rates` | array<object\> | ✅ | Tarifas a aplicar. Cada item: |
| `rates[].pms_room_id` | string | ✅ | ID del room según el PMS (será resuelto via `room_mappings`). |
| `rates[].fecha_inicio`, `rates[].fecha_fin` | date | ✅ | Rango de validez de la tarifa. |
| `rates[].precio_base` | number | ✅ | Precio antes de descuento. |
| `rates[].moneda` | string | ✅ | ISO 4217 (`COP`, `USD`, etc.). |
| `rates[].descuento` | number | — | Default 0. |

#### `data` para `property_sync`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `nombre` | string | — | Nuevo nombre del hotel. |
| `direccion` | string | — | Nueva dirección. |
| `ciudad` | string | — | Nueva ciudad. |
| `pais` | string | — | Nuevo país (ISO 2-3 chars). |
| `rooms` | array | — | Si presente, se ignora con warning. La sincronización de `habitacion` está deshabilitada (su owner es search-service). |

#### Response `202 Accepted`

```json
{
  "event_id": "hotelbeds-evt-2026-08-001",
  "status": "queued"
}
```

`202` no implica éxito en el upsert — sólo que el evento se aceptó y publicó al broker. Para confirmar resultado:

```bash
curl -s "https://apitravelhubdev.site/api/v1/pms/sync-status/$EVENT_ID" \
  -H "Authorization: Bearer $TOKEN"
# → {"event_id":"...","status":"completed","processed_at":"..."}
```

Status posibles: `received` (recién insertado) → `queued` (publicado a Kafka) → `processing` (worker tomó) → `completed` o `failed`.

#### Curl ejemplo runable (DEV)

```bash
TOKEN=$(curl -sS -X POST https://apitravelhubdev.site/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<tu_email>","password":"<tu_pass>"}' | jq -r .access_token)

EVENT_ID="manual-$(date +%s)"

curl -sS -X POST https://apitravelhubdev.site/api/v1/pms/webhook \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"event_id\": \"$EVENT_ID\",
    \"event_type\": \"availability_update\",
    \"pms_provider\": \"hotelbeds\",
    \"pms_property_id\": \"HB-BOG-001\",
    \"hotel_id\": \"d2e3f4a5-b6c7-8901-def0-234567890abc\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"data\": {
      \"habitacion_id\": \"hab-bogota-001\",
      \"dates\": [
        { \"fecha\": \"2026-05-16\", \"unidades_disponibles\": 3 }
      ]
    }
  }"

# Pre-requisito: existir un row en pms_properties con (pms_provider, pms_property_id)
# = (hotelbeds, HB-BOG-001) cuyo hotel_id apunte a un hotel real en la tabla hotel.
# Para crearlo: POST /api/v1/pms/properties (ver sección siguiente).
```

**Errores:**

| Código | Motivo |
|---|---|
| `401` | Token ausente o firma HMAC inválida |
| `403` | Rol sin permiso |
| `404` | PMS property no registrada — registrarla con `POST /api/v1/pms/properties` antes |
| `422` | Payload inválido (falta campo, tipo equivocado) |
| `500` | Error de BD/Kafka. Confirmar con `GET /sync-status/{event_id}` si quedó algo en `sync_events`. |

---

### Propiedades PMS

#### `POST /api/v1/pms/properties`

Registra una nueva propiedad PMS.

**Roles:** `hotel_admin`, `platform_admin`

**Request Body:**
```json
{
  "hotel_id": "550e8400-e29b-41d4-a716-446655440000",
  "pms_provider": "hotelbeds",
  "pms_property_id": "HB-12345",
  "api_key_hash": "sha256_hash_de_la_api_key",
  "webhook_secret_hash": "sha256_hash_del_secret"
}
```

**Response `201 Created`:**
```json
{
  "id": "a1b2c3d4-...",
  "hotel_id": "550e8400-...",
  "pms_provider": "hotelbeds",
  "pms_property_id": "HB-12345",
  "status": "active",
  "sync_error_count": 0,
  "created_at": "2026-04-02T10:00:00",
  "updated_at": "2026-04-02T10:00:00"
}
```

---

#### `GET /api/v1/pms/properties`

Lista propiedades PMS, opcionalmente filtradas por `hotel_id`.

**Query params:** `hotel_id` (UUID, opcional)

**Response `200 OK`:**
```json
[
  {
    "id": "a1b2c3d4-...",
    "hotel_id": "550e8400-...",
    "pms_provider": "hotelbeds",
    "pms_property_id": "HB-12345",
    "status": "active",
    "last_sync_at": null,
    "sync_error_count": 0,
    "created_at": "2026-04-02T10:00:00",
    "updated_at": "2026-04-02T10:00:00"
  }
]
```

---

#### `GET /api/v1/pms/properties/{id}`

Obtiene el detalle de una propiedad PMS.

**Response `200 OK`:** igual al objeto de `POST`.

**Errores:** `404` si no existe.

---

#### `PUT /api/v1/pms/properties/{id}`

Actualiza una propiedad PMS.

**Request Body (campos opcionales):**
```json
{
  "api_key_hash": "nuevo_hash",
  "webhook_secret_hash": "nuevo_hash",
  "status": "inactive"
}
```

**Response `200 OK`:** objeto actualizado.

---

#### `DELETE /api/v1/pms/properties/{id}`

Desactiva (soft delete) una propiedad PMS. Cambia `status` a `"inactive"`.

**Response `200 OK`:** objeto con `status: "inactive"`.

---

### Disponibilidad

#### `GET /api/v1/pms/availability`

Consulta disponibilidad de habitaciones.

**Roles:** `hotel_admin`, `platform_admin`, `traveler`

**Query params:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `hotel_id` | varchar | Filtrar por hotel canonical |
| `habitacion_id` | varchar | Filtrar por habitación específica canonical |
| `date_from` | date (YYYY-MM-DD) | Fecha inicio del rango |
| `date_to` | date (YYYY-MM-DD) | Fecha fin del rango |

**Response `200 OK`** (lee tabla canonical `disponibilidad`, cols camelCase):
```json
[
  {
    "id": "b2c3d4e5-...",
    "habitacionId": "b1000000-0000-0000-0000-000000000001",
    "fecha": "2026-06-01",
    "unidadesDisponibles": 3,
    "unidadesReservadas": 1,
    "ultimaActualizacion": "2026-04-02T10:00:00Z",
    "fuenteActualizacion": "pms_webhook"
  }
]
```

---

#### `GET /api/v1/pms/sync-status/{event_id}`

Consulta el estado de procesamiento de un evento de sincronización.

**Roles:** `hotel_admin`, `platform_admin`

**Response `200 OK`:**
```json
{
  "event_id": "hotelbeds-evt-2026-001",
  "status": "queued",
  "pms_provider": "hotelbeds",
  "event_type": "availability_update",
  "retry_count": 0,
  "created_at": "2026-04-02T10:00:00",
  "processed_at": null
}
```

**Estados posibles:** `received` → `queued` → `processing` → `completed` / `failed`

**Errores:** `404` si el `event_id` no existe.

---

## Autenticación

El servicio soporta **dos modos de autenticación**:

### 1. JWT (usuarios del sistema)

Enviado por el API Gateway. El servicio **no verifica la firma** — el Gateway ya lo hizo.

```
Authorization: Bearer <jwt_token>
```

El JWT debe contener el claim `role` con uno de los siguientes valores:
- `platform_admin` — acceso total
- `hotel_admin` — acceso total
- `traveler` — solo `GET /api/v1/pms/availability`

### 2. HMAC (sistemas PMS externos)

Para llamadas directas desde sistemas PMS sin JWT de usuario:

```
X-PMS-Provider: hotelbeds
X-PMS-Signature: <hmac_sha256_del_body>
```

El HMAC se calcula como `HMAC-SHA256(body, webhook_secret_hash)` donde `webhook_secret_hash` es el secreto almacenado en `pms_properties`.

### Tabla de permisos por rol

| Endpoint | `platform_admin` | `hotel_admin` | `traveler` | `pms_system` (HMAC) |
|---|:---:|:---:|:---:|:---:|
| `POST /webhook` | ✅ | ✅ | ❌ | ✅ |
| `POST /properties` | ✅ | ✅ | ❌ | ❌ |
| `GET /properties` | ✅ | ✅ | ❌ | ❌ |
| `PUT /properties/{id}` | ✅ | ✅ | ❌ | ❌ |
| `DELETE /properties/{id}` | ✅ | ✅ | ❌ | ❌ |
| `GET /availability` | ✅ | ✅ | ✅ | ❌ |
| `GET /sync-status/{id}` | ✅ | ✅ | ❌ | ❌ |
| `GET /health` | ✅ | ✅ | ✅ | ✅ |

---

## Patrones de Diseño

### Facade (GoF)
`app/services/webhook_facade.py` encapsula el flujo completo del webhook (validación → idempotencia → publicación en Kafka) en una única llamada `handle_webhook()`. Los routers solo invocan el facade sin conocer los detalles internos.

### Command (GoF)
`app/commands/sync_command.py` encapsula cada evento de sincronización como un objeto serializable (`SyncCommand`). Permite encolarlo en Kafka con toda la información necesaria para el worker.

### Chain of Responsibility (GoF)
Los middlewares en `app/middleware/` forman una cadena de procesamiento:
1. `AuthMiddleware` → decodifica JWT
2. `RateLimitFilter` → 60 req/min por usuario/IP
3. `IPValidationFilter` → placeholder de geolocalización
4. `RBACFilter` → valida rol vs ruta

Cada eslabón puede cortar la cadena retornando un error HTTP o pasarla al siguiente.

### Circuit Breaker
El `kafka_producer.py` implementa degradación elegante: si Kafka no está disponible, loggea el comando y retorna `True` para no bloquear el webhook. Combinado con `KAFKA_ENABLED=false` para entornos de dev.

---

## Tests

Los tests usan **SQLite in-memory** — no requieren PostgreSQL ni Kafka.

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=term-missing

# Un archivo específico
pytest tests/test_webhook.py -v
```

### Cobertura de tests

| Archivo | Tests |
|---|---|
| `test_webhook.py` | payload válido, payload inválido, PMS no registrada, idempotencia, Kafka mock |
| `test_idempotency.py` | nuevo evento, duplicado, race condition (UniqueConstraint), update status |
| `test_properties.py` | create, list por hotel, duplicado 409, update, delete (soft), not found |
| `test_availability.py` | con resultados, sin resultados, sync status, not found |
| `test_middleware.py` | hotel_admin permitido, traveler solo availability, sin token 401, rate limit 429 |

**Meta de cobertura: ≥ 70%**

---

## Deploy a Cloud Run

```bash
# Asegúrate de estar autenticado en gcloud
gcloud auth login
gcloud config set project gen-lang-client-0930444414

# Ejecutar deploy
./deploy.sh
```

El script:
1. Construye la imagen Docker con Cloud Build
2. La publica en Container Registry
3. Despliega en Cloud Run (región `us-central1`)
4. Configura VPC connector y variables de entorno

> Tras el deploy, actualiza el archivo `gateway/openapi-spec.yaml` con la nueva URL del servicio.

---

## Modelos de Datos

### Relaciones entre tablas (schema canonical 2026-05-14)

```
hotel (canonical, varchar id)
  │
  ├──< habitacion (varchar id, hotelId FK)
  │       │
  │       └──< disponibilidad   (uq: habitacionId + fecha)
  │
  └──< pms_properties           (uq: pms_provider + pms_property_id)

sync_events                     (uq: event_id, hotel_id FK → hotel canonical)
```

> `tarifa` y `tarifa_history` viven en `inventory-services` (owner). pms-int no las toca.

### Estados de SyncEvent

```
received → queued → processing → completed
                              └→ failed
```
