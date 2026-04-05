# CLAUDE CODE — pms-integration-services (Webhook / API)
> Instrucciones para Claude Code CLI. Ejecutar en orden. No omitir pasos.
> Proyecto: TravelHub — Grupo 9 | Curso: MISW4501 — Uniandes

---

## 1. Resumen del Servicio

**pms-integration-services** es el microservicio que expone un webhook HTTP para recibir eventos de sincronización desde los sistemas PMS (Property Management Systems) de los hoteles asociados a TravelHub. Su responsabilidad es:

1. Recibir webhooks de sistemas PMS externos (Hotelbeds, TravelClick, RoomRaccoon, etc.)
2. Validar el payload y verificar idempotencia
3. Publicar un comando de sincronización en la cola Kafka `pms-sync-queue`
4. Responder `202 Accepted` inmediatamente (no procesa — delega al worker)
5. Exponer endpoints CRUD para registrar/consultar propiedades PMS y su estado de sincronización
6. Exponer endpoints para consultar disponibilidad de habitaciones

**Patrones aplicados:**
- **Facade** (GoF): `pms-webhook` encapsula validación + idempotencia + publicación en cola
- **Command** (GoF): Cada evento de sincronización se encapsula como comando serializable
- **Circuit Breaker**: Protección ante fallos de PMS externos (para llamadas outbound si las hubiera)
- **Chain of Responsibility**: Middleware de seguridad (RBAC, rate limit, JWT)

**ASR:** AH004 — Sincronizar 1,200 propiedades en ≤ 2 minutos con reintentos e idempotencia.

---

## 2. Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Framework | Python 3.11 + FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| BD | PostgreSQL 15 (Cloud SQL) |
| Cola | Apache Kafka (confluent-kafka-python) |
| Validación | Pydantic v2 |
| Tests | pytest + pytest-asyncio + httpx |
| Container | Docker → Cloud Run |
| Puerto | 8000 |

---

## 3. Estructura de Archivos

```
pms-integration-services/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app + lifespan + routers
│   ├── config.py                        # Settings con Pydantic BaseSettings
│   ├── database.py                      # Engine + SessionLocal + Base
│   │
│   ├── models/                          # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── hotel.py                     # Hotel
│   │   ├── room.py                      # Habitacion (Room)
│   │   ├── availability.py              # Disponibilidad
│   │   ├── tariff.py                    # Tarifa
│   │   ├── pms_property.py             # Registro de propiedad PMS
│   │   └── sync_event.py               # Evento de sincronización (idempotencia)
│   │
│   ├── schemas/                         # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── webhook.py                   # WebhookPayload, SyncCommand
│   │   ├── pms_property.py             # PMSPropertyCreate, PMSPropertyResponse
│   │   ├── availability.py              # AvailabilityResponse, AvailabilityQuery
│   │   └── common.py                    # HealthResponse, ErrorResponse
│   │
│   ├── api/                             # Routers
│   │   ├── __init__.py
│   │   ├── webhook.py                   # POST /api/v1/pms/webhook
│   │   ├── properties.py               # CRUD /api/v1/pms/properties
│   │   ├── availability.py              # GET /api/v1/pms/availability
│   │   └── health.py                    # GET /health
│   │
│   ├── services/                        # Business logic
│   │   ├── __init__.py
│   │   ├── webhook_facade.py            # Facade: validate → idempotency → enqueue
│   │   ├── kafka_producer.py            # Kafka producer wrapper
│   │   ├── idempotency_service.py       # Verifica duplicados por event_id
│   │   └── property_service.py          # CRUD de propiedades PMS
│   │
│   ├── middleware/                       # Chain of Responsibility
│   │   ├── __init__.py
│   │   ├── auth_middleware.py           # JWT decode (sin verificar firma, gateway ya lo hizo)
│   │   ├── rbac_filter.py              # Valida role vs ruta
│   │   ├── rate_limit_filter.py         # 60 req/min por usuario/IP
│   │   └── ip_validation_filter.py      # Placeholder geolocalización
│   │
│   └── commands/                        # Command pattern
│       ├── __init__.py
│       └── sync_command.py              # SyncCommand dataclass serializable a JSON
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Fixtures: test client, test db, mock kafka
│   ├── test_webhook.py                  # Tests del webhook endpoint
│   ├── test_idempotency.py              # Tests de idempotencia
│   ├── test_properties.py              # Tests CRUD propiedades
│   ├── test_availability.py             # Tests consulta disponibilidad
│   └── test_middleware.py               # Tests Chain of Responsibility
│
├── Dockerfile
├── requirements.txt
├── .env.example
├── deploy.sh                            # Script deploy a Cloud Run
└── README.md
```

---

## 4. Variables de Entorno

```bash
# .env.example
DATABASE_HOST=10.100.0.3
DATABASE_PORT=5432
DATABASE_NAME=travelhub
DATABASE_USER=travelhub_app
DATABASE_PASSWORD=lALk8rAOj1TSltRQzGavZdBCrSu67ZJg

KAFKA_BOOTSTRAP_SERVERS=10.100.0.5:9092
KAFKA_TOPIC_PMS_SYNC=pms-sync-queue

JWT_ISSUER=https://auth.travelhub.app
JWT_AUDIENCE=travelhub-api

SERVICE_NAME=pms-integration-services
SERVICE_PORT=8000
```

---

## 5. Modelos SQLAlchemy

### 5.1 Hotel (tabla `hotels`)
> NOTA: Esta tabla puede ya existir si otro servicio la creó. Usar `CREATE TABLE IF NOT EXISTS`.

```python
class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), nullable=False)
    direccion = Column(String(500))
    ciudad = Column(String(100), nullable=False)
    pais = Column(String(5), nullable=False)           # ISO code: CO, PE, MX, CL, AR, EC
    latitud = Column(Float)
    longitud = Column(Float)
    estrellas = Column(Integer)
    pms_proveedor = Column(String(100))                 # Hotelbeds, TravelClick, RoomRaccoon
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    rooms = relationship("Room", back_populates="hotel")
    pms_properties = relationship("PMSProperty", back_populates="hotel")
```

### 5.2 Room / Habitacion (tabla `rooms`)

```python
class Room(Base):
    __tablename__ = "rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hotel_id = Column(UUID(as_uuid=True), ForeignKey("hotels.id"), nullable=False)
    tipo = Column(String(100), nullable=False)          # "Suite", "Standard", "Deluxe"
    categoria = Column(String(100))
    capacidad_maxima = Column(Integer, nullable=False)
    descripcion = Column(Text)
    imagenes = Column(JSON, default=[])                  # List[str] URLs
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    hotel = relationship("Hotel", back_populates="rooms")
    availability = relationship("Availability", back_populates="room")
    tariffs = relationship("Tariff", back_populates="room")
```

### 5.3 Availability / Disponibilidad (tabla `availability`)

```python
class Availability(Base):
    __tablename__ = "availability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    unidades_disponibles = Column(Integer, nullable=False, default=0)
    unidades_reservadas = Column(Integer, nullable=False, default=0)
    ultima_actualizacion = Column(DateTime, default=func.now())
    fuente_actualizacion = Column(String(50))           # "pms_webhook", "manual", "booking"

    room = relationship("Room", back_populates="availability")

    __table_args__ = (
        UniqueConstraint("room_id", "fecha", name="uq_room_date"),
    )
```

### 5.4 Tariff / Tarifa (tabla `tariffs`)

```python
class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    precio_base = Column(Numeric(12, 2), nullable=False)
    moneda = Column(String(3), nullable=False, default="USD")
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    descuento = Column(Numeric(5, 2), default=0)
    created_at = Column(DateTime, default=func.now())

    room = relationship("Room", back_populates="tariffs")
```

### 5.5 PMSProperty (tabla `pms_properties`) — Registro de integración PMS

```python
class PMSProperty(Base):
    __tablename__ = "pms_properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hotel_id = Column(UUID(as_uuid=True), ForeignKey("hotels.id"), nullable=False)
    pms_provider = Column(String(100), nullable=False)  # "hotelbeds", "travelclick", "roomraccoon"
    pms_property_id = Column(String(255), nullable=False)  # ID en el sistema PMS externo
    api_key_hash = Column(String(255))                   # Hash de la API key del PMS
    webhook_secret_hash = Column(String(255))            # Hash del secret para validar webhooks
    status = Column(String(20), default="active")        # active, inactive, error
    last_sync_at = Column(DateTime)
    sync_error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    hotel = relationship("Hotel", back_populates="pms_properties")

    __table_args__ = (
        UniqueConstraint("pms_provider", "pms_property_id", name="uq_pms_provider_property"),
    )
```

### 5.6 SyncEvent (tabla `sync_events`) — Idempotencia

```python
class SyncEvent(Base):
    __tablename__ = "sync_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), unique=True, nullable=False)   # ID único del evento PMS
    pms_provider = Column(String(100), nullable=False)
    hotel_id = Column(UUID(as_uuid=True), ForeignKey("hotels.id"))
    event_type = Column(String(50), nullable=False)      # "availability_update", "rate_update", "property_sync"
    payload_hash = Column(String(64))                     # SHA-256 del payload
    status = Column(String(20), default="received")      # received, queued, processing, completed, failed
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)
```

---

## 6. Schemas Pydantic

### 6.1 Webhook Payload (lo que envía el PMS)

```python
class WebhookPayload(BaseModel):
    event_id: str                           # ID único del evento en el PMS
    event_type: str                         # "availability_update" | "rate_update" | "property_sync"
    pms_provider: str                       # "hotelbeds" | "travelclick" | "roomraccoon"
    pms_property_id: str                    # ID de la propiedad en el PMS
    timestamp: datetime
    data: dict                              # Payload variable según event_type

class AvailabilityUpdateData(BaseModel):
    room_id: str                            # ID de la habitación en el PMS
    room_type: str
    dates: list[AvailabilityDateEntry]

class AvailabilityDateEntry(BaseModel):
    date: date
    available_units: int
    rate: Optional[Decimal] = None
    currency: Optional[str] = "USD"

class RateUpdateData(BaseModel):
    room_id: str
    rates: list[RateEntry]

class RateEntry(BaseModel):
    date_from: date
    date_to: date
    price: Decimal
    currency: str = "USD"
    discount: Optional[Decimal] = 0
```

### 6.2 SyncCommand (lo que se publica en Kafka)

```python
class SyncCommand(BaseModel):
    command_id: str                         # UUID generado
    event_id: str                           # Del webhook
    event_type: str
    pms_provider: str
    hotel_id: str                           # UUID del hotel en TravelHub
    pms_property_id: str
    timestamp: datetime
    data: dict
    retry_count: int = 0
    created_at: datetime
```

---

## 7. Endpoints API

### 7.1 Webhook (acceso: requiere API key o JWT de hotel_admin)

| Método | Ruta | Descripción | Response |
|---|---|---|---|
| POST | `/api/v1/pms/webhook` | Recibe evento del PMS | 202 Accepted |

**Flujo del webhook (Facade pattern):**
```
1. Recibe POST con WebhookPayload
2. Valida schema Pydantic
3. Busca PMSProperty por (pms_provider, pms_property_id) → obtiene hotel_id
4. Verifica idempotencia: busca event_id en sync_events
   - Si existe con status "completed" → retorna 202 (ya procesado)
   - Si existe con status "queued"/"processing" → retorna 202 (en proceso)
5. Inserta registro en sync_events con status "received"
6. Construye SyncCommand
7. Publica en Kafka topic `pms-sync-queue`
8. Actualiza sync_events.status = "queued"
9. Retorna 202 Accepted con { "event_id": "...", "status": "queued" }
```

### 7.2 Properties CRUD (acceso: hotel_admin, platform_admin)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/pms/properties` | Registrar nueva propiedad PMS |
| GET | `/api/v1/pms/properties` | Listar propiedades PMS (filtro por hotel_id) |
| GET | `/api/v1/pms/properties/{id}` | Detalle de propiedad PMS |
| PUT | `/api/v1/pms/properties/{id}` | Actualizar propiedad PMS |
| DELETE | `/api/v1/pms/properties/{id}` | Desactivar propiedad PMS |

### 7.3 Availability (acceso: hotel_admin, platform_admin, traveler)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/pms/availability` | Consultar disponibilidad (query: hotel_id, room_id, date_from, date_to) |
| GET | `/api/v1/pms/sync-status/{event_id}` | Estado de un evento de sincronización |

### 7.4 Health

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Health check (DB + Kafka connectivity) |

---

## 8. Middleware — Chain of Responsibility

Implementar exactamente como en `user-services`. Cada middleware es una clase que recibe el request y decide si pasa al siguiente o retorna error.

```python
# Orden de ejecución:
# 1. AuthMiddleware → decodifica JWT del header (SIN verificar firma, el gateway ya lo hizo)
# 2. RateLimitFilter → 60 req/min por usuario/IP → 429
# 3. IPValidationFilter → placeholder
# 4. RBACFilter → hotel_admin y platform_admin pueden acceder a /api/v1/pms/*
#                  traveler solo puede acceder a GET /api/v1/pms/availability

# EXCEPCIÓN: POST /api/v1/pms/webhook puede recibir llamadas de sistemas PMS externos.
# Implementar validación alternativa para el webhook:
#   - Header X-PMS-Provider + X-PMS-Signature (HMAC del body con webhook_secret)
#   - O bien JWT de un hotel_admin
# Esto permite que los PMS llamen al webhook sin un JWT de usuario.
```

---

## 9. Kafka Producer

```python
# Usar confluent-kafka-python
# Config:
#   bootstrap.servers = KAFKA_BOOTSTRAP_SERVERS
#   client.id = "pms-integration-services"
#   acks = "all"  (durabilidad)
#   retries = 3
#   linger.ms = 10 (batching)
#
# Topic: pms-sync-queue
# Key: hotel_id (para particionamiento por hotel)
# Value: SyncCommand serializado a JSON
#
# En caso de error al publicar → marcar sync_events.status = "failed"
# Implementar delivery callback para confirmar publicación
```

---

## 10. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 11. requirements.txt

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
psycopg2-binary==2.9.9
pydantic==2.7.1
pydantic-settings==2.3.1
confluent-kafka==2.4.0
python-jose[cryptography]==3.3.0
httpx==0.27.0
python-multipart==0.0.9
```

---

## 12. Deploy a Cloud Run

```bash
#!/bin/bash
# deploy.sh
set -e

SERVICE_NAME="pms-integration-services"
REGION="us-central1"
PROJECT="gen-lang-client-0930444414"

echo ">>> Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT/$SERVICE_NAME --project $PROJECT

echo ">>> Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT/$SERVICE_NAME \
  --vpc-connector=travelhub-connector \
  --set-env-vars "JWT_ISSUER=https://auth.travelhub.app,JWT_AUDIENCE=travelhub-api,DATABASE_HOST=10.100.0.3,DATABASE_PORT=5432,DATABASE_NAME=travelhub,DATABASE_USER=travelhub_app,DATABASE_PASSWORD=lALk8rAOj1TSltRQzGavZdBCrSu67ZJg,KAFKA_BOOTSTRAP_SERVERS=10.100.0.5:9092,KAFKA_TOPIC_PMS_SYNC=pms-sync-queue" \
  --allow-unauthenticated \
  --port 8000 \
  --region $REGION \
  --project $PROJECT

echo ">>> Deployed. Update gateway/openapi-spec.yaml with the new URL."
```

---

## 13. Tests Requeridos (pytest)

### 13.1 test_webhook.py
- `test_webhook_valid_payload` → 202 Accepted + evento en sync_events
- `test_webhook_invalid_payload` → 422 Unprocessable
- `test_webhook_unknown_pms_property` → 404 Not Found
- `test_webhook_idempotent_duplicate` → 202 (segundo call con mismo event_id no crea duplicado)
- `test_webhook_kafka_publish_called` → Mock Kafka producer, verificar que se llamó con SyncCommand correcto

### 13.2 test_idempotency.py
- `test_new_event_is_recorded` → event_id nuevo → status "received"
- `test_duplicate_event_returns_existing` → event_id existente → retorna sin insertar
- `test_concurrent_duplicate_events` → Simular race condition → solo uno se inserta (usar unique constraint)

### 13.3 test_properties.py
- `test_create_pms_property` → 201 Created
- `test_list_pms_properties_by_hotel` → filtro funciona
- `test_create_duplicate_pms_property` → 409 Conflict
- `test_update_pms_property` → 200 OK
- `test_delete_pms_property` → soft delete (status = "inactive")

### 13.4 test_availability.py
- `test_get_availability_by_hotel_and_dates` → retorna disponibilidad
- `test_get_availability_no_results` → retorna lista vacía
- `test_get_sync_status` → retorna status del evento

### 13.5 test_middleware.py
- `test_rbac_hotel_admin_allowed` → 200
- `test_rbac_traveler_only_get_availability` → GET availability 200, POST webhook 403
- `test_rbac_no_token` → 401
- `test_rate_limit_exceeded` → 429

### 13.6 conftest.py
- Usar SQLite in-memory para tests (no depender de PostgreSQL)
- Mock del Kafka producer (no publicar realmente)
- Fixture para crear hotel + room + pms_property de prueba
- Override de dependencies de FastAPI para inyectar test DB

**Meta de cobertura: ≥ 70%**

---

## 14. Notas Importantes

1. **NO procesar la sincronización aquí.** Este servicio solo recibe, valida, encola y responde. El procesamiento real lo hace `pms-sync-worker`.
2. **Idempotencia es crítica.** Los PMS pueden enviar el mismo webhook múltiples veces. El `event_id` es la clave.
3. **Las tablas deben crearse con `CREATE TABLE IF NOT EXISTS`** porque otros servicios pueden compartir las tablas `hotels`, `rooms`, `availability`, `tariffs`.
4. **El webhook debe soportar dos modos de autenticación:** JWT de hotel_admin (via API Gateway) O firma HMAC (para llamadas directas de PMS).
5. **Usar `Base.metadata.create_all(bind=engine)`** en el startup para crear tablas automáticamente en dev.
6. **Kafka en dev:** Si Kafka no está disponible, loggear el comando y marcarlo como "queued" de todas formas. Implementar un flag `KAFKA_ENABLED=true/false`.
