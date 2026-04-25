# CLAUDE.md — pms-integration-services

Microservicio que recibe webhooks de PMS providers (Hotelbeds, etc.), valida idempotencia,
persiste el evento, y publica un `SyncCommand` en Kafka topic `pms-sync-queue`.

## Stack

Python 3.11 · FastAPI 0.111 · SQLAlchemy 2.0.36 (async + asyncpg 0.30) · Pydantic 2 · confluent-kafka · PostgreSQL

## Comandos

```bash
# Local (con docker-compose en travelhub-local/)
cd ../travelhub-local && docker compose up -d
# Tests
pytest -v
# Lint (no obligatorio, ejecuta || true en CI)
black --check app/ tests/ && isort --check-only app/ tests/ && ruff check app/ tests/
# Build local
docker build -t pms-integration-services:dev .
# Deploy manual a GCP
./deploy/deploy.sh dev    # o prod
```

## Estructura

```
app/
├── main.py                       # FastAPI app + lifespan (create_tables al arranque)
├── config.py                     # pydantic-settings (env vars + URL builders con ssl=disable)
├── database.py                   # AsyncSession, GUID type, Base, create_tables
├── api/
│   ├── webhook.py                # POST /api/v1/pms/webhook (HMAC + JWT modes)
│   ├── availability.py           # GET /api/v1/pms/availability (RBAC traveler+admin)
│   ├── properties.py             # CRUD propiedades PMS
│   └── health.py                 # GET /health (database + kafka status)
├── middleware/
│   ├── auth_middleware.py        # JWT decode no-verify, allowlist /health /docs
│   ├── rate_limit_filter.py      # 60 req/min in-memory por IP/user
│   ├── ip_validation_filter.py   # placeholder
│   └── rbac_filter.py            # role checks por endpoint
├── services/
│   ├── webhook_facade.py         # orquesta idempotencia → publica Kafka
│   ├── idempotency_service.py    # dedup por event_id, payload_hash
│   ├── kafka_producer.py         # confluent-kafka producer
│   └── property_service.py
├── models/                       # SQLAlchemy: hotel, room, availability, tariff, pms_property, sync_event
├── schemas/                      # Pydantic
└── commands/sync_command.py      # mensaje publicado a Kafka
.github/workflows/ci.yml          # WIF + Cloud Run direct VPC
clouddeploy.yaml                  # canary 10→50→100, requireApproval
skaffold.yaml                     # verify health entre fases
k8s/service-prod.yaml             # manifiesto Cloud Run prod
deploy/deploy.sh                  # script manual dev|prod
```

## Despliegue actual

| Ambiente | Project | URL | Estado |
|---|---|---|---|
| **DEV** | `gen-lang-client-0930444414` | https://pms-integration-services-ridyy4wz4q-uc.a.run.app | ✅ Auto-deploy via push a `feature/*` o `develop` |
| **PROD** | `travelhub-prod-492116` | — | ⏸ Pipeline Cloud Deploy creado; deploy se activa con push a `main` (requiere Kafka en prod) |

### Branch de trabajo

`feature/ci-cd-setup` — contiene la config de CI/CD WIF + Cloud Deploy.

## Network setup (gotchas críticos)

1. **Direct VPC egress** (no VPC connector): `--network=travelhub-vpc --subnet=subnet-services --vpc-egress=private-ranges-only`
2. **Switch desde VPC connector** requiere `--clear-vpc-connector` en el deploy command
3. **`?ssl=disable`** en `DATABASE_URL` (asyncpg 0.30 + Cloud SQL private IP ya está en red privada)
4. **Tag `data-layer`** en cualquier VM custom de la VPC para que aplique `fw-allow-services-to-data`

## Secrets en GCP (DEV)

Inyectados por `--set-secrets` en `gcloud run deploy`:

| Env var | Secret name |
|---|---|
| `DATABASE_HOST` | `PMS_DATABASE_HOST` |
| `DATABASE_PORT` | `PMS_DATABASE_PORT` |
| `DATABASE_NAME` | `PMS_DATABASE_NAME` |
| `DATABASE_USER` | `PMS_DATABASE_USER` |
| `DATABASE_PASSWORD` | `PMS_DATABASE_PASSWORD` |
| `KAFKA_BOOTSTRAP_SERVERS` | `KAFKA_BOOTSTRAP_SERVERS` (= `10.10.3.3:9092` en dev) |

## CI/CD

Pipeline en `.github/workflows/ci.yml`. Auth via WIF (sin SA keys).

| Trigger | Acción |
|---|---|
| Push `feature/*`, `develop` | Tests + Lint + Build + Deploy a Cloud Run DEV |
| PR a `main`/`develop` | Tests + Lint + Docker Build (sin deploy) |
| Push `main` | Tests + Lint + Build + **Cloud Deploy canary** (10→50→100, manual approval) |

WIF resources hardcoded en `ci.yml` (no son secretos):

```yaml
DEV_WIF_PROVIDER: projects/154299161799/locations/global/workloadIdentityPools/github-pool/providers/github-provider
DEV_SA: github-deploy-pms-int@gen-lang-client-0930444414.iam.gserviceaccount.com
PROD_WIF_PROVIDER: projects/974898737307/locations/global/workloadIdentityPools/github-pool/providers/github-provider
PROD_SA: github-deploy-pms-int@travelhub-prod-492116.iam.gserviceaccount.com
```

## Reglas de negocio clave

### Webhook
- Auth dual: HMAC (PMS systems) o JWT (admins). Detectado por presencia de `X-PMS-Signature`.
- Idempotencia por `event_id` único. Estados terminales (`completed`, `queued`, `processing`)
  → no re-procesar.
- Persistencia: `payload_hash` (SHA-256 de `data`). Nunca persistir el payload crudo.
- Publicación Kafka: clave = `hotel_id` (orden por hotel garantizado).

### Auth chain (orden fijo)
1. **AuthMiddleware**: JWT decode no-verify (gateway ya verificó). Allowlist `/health`, `/docs`, `/redoc`, `/openapi.json`.
2. **RateLimitFilter**: 60 req/min por user_id o IP.
3. **IPValidationFilter**: placeholder.
4. **RBACFilter**: roles `traveler` (solo GET availability), `hotel_admin` y `platform_admin` (todo).

## Convenciones

- snake_case archivos, PascalCase clases, kebab-case URLs
- Errores: `HTTPException` con `{"detail": "Mensaje en español"}`
- Logging: `logging.getLogger(__name__)` — info (éxito), warning (fallo), error (sistema)

## NO HACER

- Mockear DB en tests si se puede usar SQLite in-memory
- Retornar `payload` raw del webhook en responses (solo `payload_hash`)
- Acceder a tablas `users` (es de user-services)
