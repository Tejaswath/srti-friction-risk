# Azure Backend Deploy Runbook

This folder contains a CLI helper script for provisioning Azure App Service.

## Prerequisites

- Azure CLI installed (`az`)
- Logged in: `az login`
- Selected subscription with active credits

## Provisioning

```bash
./infra/azure/deploy_backend.sh \
  "<subscription-id-or-name>" \
  "rg-srti-mvp-weu" \
  "swedencentral" \
  "asp-srti-mvp-b1" \
  "srti-friction-risk-api"
```

## Required app settings

Set in App Service -> Configuration:

- `TRAFIKVERKET_API_KEY`
- `ADMIN_TOKEN`
- `ALLOWED_ORIGINS=https://<your-vercel-domain>`
- `CACHE_TTL_SECONDS=600`

## Validation

- `https://<app>.azurewebsites.net/health`
- `https://<app>.azurewebsites.net/risk/summary`
- `https://<app>.azurewebsites.net/docs`
