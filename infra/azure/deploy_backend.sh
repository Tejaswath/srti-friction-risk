#!/usr/bin/env bash
set -euo pipefail

# Usage:
# ./infra/azure/deploy_backend.sh \
#   <subscription-id-or-name> <resource-group> <region> <app-service-plan> <webapp-name>

SUBSCRIPTION="${1:?subscription required}"
RESOURCE_GROUP="${2:?resource group required}"
REGION="${3:?region required}"
PLAN_NAME="${4:?plan name required}"
WEBAPP_NAME="${5:?webapp name required}"

RUNTIME="PYTHON|3.12"

az account set --subscription "$SUBSCRIPTION"

az group create \
  --name "$RESOURCE_GROUP" \
  --location "$REGION"

az appservice plan create \
  --name "$PLAN_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --sku B1 \
  --is-linux

az webapp create \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$PLAN_NAME" \
  --name "$WEBAPP_NAME" \
  --runtime "$RUNTIME"

az webapp config set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --startup-file "gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind=0.0.0.0:\$PORT --access-logfile '-' --error-logfile '-'"

echo "Set app settings manually or via az webapp config appsettings set:"
echo "TRAFIKVERKET_API_KEY, ADMIN_TOKEN, ALLOWED_ORIGINS, CACHE_TTL_SECONDS"
