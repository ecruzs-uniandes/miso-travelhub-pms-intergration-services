#!/bin/bash
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
  --set-env-vars "JWT_ISSUER=https://auth.travelhub.app,JWT_AUDIENCE=travelhub-api,DATABASE_HOST=10.100.0.3,DATABASE_PORT=5432,DATABASE_NAME=travelhub,DATABASE_USER=travelhub_app,DATABASE_PASSWORD=lALk8rAOj1TSltRQzGavZdBCrSu67ZJg,KAFKA_BOOTSTRAP_SERVERS=10.100.0.5:9092,KAFKA_TOPIC_PMS_SYNC=pms-sync-queue,KAFKA_ENABLED=true" \
  --allow-unauthenticated \
  --port 8000 \
  --region $REGION \
  --project $PROJECT

echo ">>> Deployed. Update gateway/openapi-spec.yaml with the new URL."
