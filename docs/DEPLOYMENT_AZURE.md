# Azure Deployment Guide

## Architecture Overview

This project supports two different deployment modes:

- `Local Docker deployment`: for local development and integration testing with `docker compose`
- `Azure production-style deployment`: for cloud-hosted services on Azure

This document covers the Azure production-style deployment.

### Target Azure Architecture

- `frontend` -> Azure Static Web Apps
- `backend` -> Azure App Service for Containers
- `bert_service` -> Azure Container Apps
- `database` -> Azure SQL Database
- `images` -> Azure Container Registry
- `logs / metrics / traces` -> Application Insights + Log Analytics

### Service Flow

1. Users access the React frontend through Azure Static Web Apps.
2. The frontend calls the backend over HTTPS.
3. The backend runs in Azure App Service as a Linux custom container.
4. The backend calls `bert_service` through its Azure Container Apps ingress URL.
5. The backend writes analysis records to Azure SQL Database through EF Core.
6. Container images are stored in Azure Container Registry.
7. Logs, traces, and service diagnostics are sent to Azure Monitor through Application Insights and Log Analytics.

### Local Docker vs Azure Production-Style

| Area | Local Docker Deployment | Azure Production-Style Deployment |
| --- | --- | --- |
| Frontend | nginx container | Azure Static Web Apps |
| Backend | Docker container | Azure App Service for Containers |
| BERT Service | Docker container | Azure Container Apps |
| Database | InMemory or local SQL substitute | Azure SQL Database |
| Image registry | local Docker daemon | Azure Container Registry |
| Logging | local container logs | App Insights + Log Analytics |
| Service discovery | docker compose service names | Azure public/internal service URLs |

## Azure Resource Naming Convention

Use one consistent naming scheme across all resources.

### Recommended Pattern

```text
<resource-type>-mras-<environment>-<region>
```

Where:

- `mras` = Misinformation Risk Assessment System
- `environment` = `prod`, `staging`, `dev`
- `region` = Azure short region label such as `eaus2`

### Recommended Names

| Resource | Example Name |
| --- | --- |
| Resource Group | `rg-mras-prod-eaus2` |
| Azure Container Registry | `acrmrasprodeaus2` |
| Static Web App | `swa-mras-prod-eaus2` |
| App Service Plan | `asp-mras-prod-eaus2` |
| Backend Web App | `app-mras-api-prod-eaus2` |
| Container Apps Environment | `cae-mras-prod-eaus2` |
| BERT Container App | `ca-mras-bert-prod-eaus2` |
| Azure SQL Server | `sql-mras-prod-eaus2` |
| Azure SQL Database | `sqldb-mras-prod` |
| Log Analytics Workspace | `log-mras-prod-eaus2` |
| Application Insights | `appi-mras-prod-eaus2` |

## Required Azure Resources

Create the following resources before full deployment:

1. Resource Group
2. Azure Container Registry
3. Log Analytics Workspace
4. Application Insights
5. Azure SQL Server
6. Azure SQL Database
7. App Service Plan
8. Azure App Service for backend
9. Azure Container Apps Environment
10. Azure Container App for `bert_service`
11. Azure Static Web App for frontend

## Environment Variables

### Frontend

The frontend is built at deploy time, so `VITE_*` values are build-time configuration.

| Variable | Example |
| --- | --- |
| `VITE_API_BASE_URL` | `https://app-mras-api-prod-eaus2.azurewebsites.net` |

### Backend

These must be configured in Azure App Service application settings.

| Variable | Example |
| --- | --- |
| `ASPNETCORE_ENVIRONMENT` | `Production` |
| `WEBSITES_PORT` | `5000` |
| `ASPNETCORE_URLS` | `http://+:5000` |
| `BertService__Url` | `https://ca-mras-bert-prod-eaus2.<region>.azurecontainerapps.io` |
| `MachineLearning__PythonExecutable` | `/opt/backend-venv/bin/python` |
| `MachineLearning__ClassicalPredictScriptPath` | `Services/Ml/classical_predict.py` |
| `MachineLearning__ClassicalModelDirectory` | `/app/Services/Ml/artifacts` |
| `MachineLearning__MediumRiskThreshold` | `0.35` |
| `MachineLearning__HighRiskThreshold` | `0.70` |
| `Cors__AllowedOrigins__0` | `https://<your-static-web-app-domain>` |
| `ConnectionStrings__DefaultConnection` | Azure SQL connection string |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights connection string |

### BERT Service

These must be configured in Azure Container Apps environment variables.

| Variable | Example |
| --- | --- |
| `BERT_MODEL_DIR` | `/app/models/distilbert-liar` |
| `BERT_MODEL_NAME` | empty by default |
| `BERT_MAX_LENGTH` | `256` |
| `HF_HOME` | `/app/.cache/huggingface` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights connection string |

## Deployment Order

Deploy in this order:

1. Authenticate to Azure
2. Create the Resource Group
3. Create Log Analytics and Application Insights
4. Create Azure Container Registry
5. Build and push the `backend` image
6. Build and push the `bert_service` image
7. Create Azure SQL Server and Azure SQL Database
8. Create Azure Container Apps Environment
9. Deploy `bert_service` to Azure Container Apps
10. Create App Service Plan
11. Deploy `backend` to Azure App Service for Containers
12. Create Azure Static Web App
13. Deploy the frontend build to Static Web Apps
14. Configure connection strings and application settings
15. Verify health checks
16. Run smoke tests

## Azure CLI Setup

```bash
az login
az account set --subscription "<SUBSCRIPTION_NAME_OR_ID>"
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

## Shared Variables

Use the following variables in Cloud Shell or your local shell:

```bash
RESOURCE_GROUP="rg-mras-prod-eaus2"
LOCATION="eastus2"

ACR_NAME="acrmrasprodeaus2"
BACKEND_IMAGE="$ACR_NAME.azurecr.io/mras/backend:prod"
BERT_IMAGE="$ACR_NAME.azurecr.io/mras/bert-service:prod"

LOG_ANALYTICS_NAME="log-mras-prod-eaus2"
APP_INSIGHTS_NAME="appi-mras-prod-eaus2"

APP_SERVICE_PLAN="asp-mras-prod-eaus2"
BACKEND_APP="app-mras-api-prod-eaus2"

CONTAINERAPPS_ENV="cae-mras-prod-eaus2"
BERT_APP="ca-mras-bert-prod-eaus2"

SQL_SERVER="sql-mras-prod-eaus2"
SQL_DB="sqldb-mras-prod"

SWA_NAME="swa-mras-prod-eaus2"
```

## Create Core Azure Resources

### Resource Group

```bash
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"
```

### Log Analytics Workspace

```bash
az monitor log-analytics workspace create \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_NAME" \
  --location "$LOCATION"
```

### Application Insights

```bash
az monitor app-insights component create \
  --app "$APP_INSIGHTS_NAME" \
  --location "$LOCATION" \
  --resource-group "$RESOURCE_GROUP" \
  --workspace "$LOG_ANALYTICS_NAME"
```

Get the Application Insights connection string:

```bash
APPINSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show \
  --app "$APP_INSIGHTS_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query connectionString \
  -o tsv)
```

### Azure Container Registry

```bash
az acr create \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --sku Basic \
  --admin-enabled true
```

```bash
az acr login --name "$ACR_NAME"
```

## Build and Push Container Images

### Backend Image

```bash
az acr build \
  --registry "$ACR_NAME" \
  --image "mras/backend:prod" \
  --file backend/Dockerfile \
  .
```

### BERT Service Image

```bash
az acr build \
  --registry "$ACR_NAME" \
  --image "mras/bert-service:prod" \
  --file bert_service/Dockerfile \
  .
```

## Azure SQL Configuration

### Create SQL Server

```bash
SQL_ADMIN_USER="mrasadmin"
SQL_ADMIN_PASSWORD="<SET_A_STRONG_PASSWORD>"

az sql server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$SQL_SERVER" \
  --location "$LOCATION" \
  --admin-user "$SQL_ADMIN_USER" \
  --admin-password "$SQL_ADMIN_PASSWORD"
```

### Create SQL Database

```bash
az sql db create \
  --resource-group "$RESOURCE_GROUP" \
  --server "$SQL_SERVER" \
  --name "$SQL_DB" \
  --service-objective S0
```

### Add Firewall Rule

Use this only if your access pattern requires public SQL access during initial setup.

```bash
az sql server firewall-rule create \
  --resource-group "$RESOURCE_GROUP" \
  --server "$SQL_SERVER" \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Backend Connection String Placement

Set the EF Core connection string in Azure App Service application settings using the existing variable name:

```text
ConnectionStrings__DefaultConnection
```

Example:

```text
Server=tcp:sql-mras-prod-eaus2.database.windows.net,1433;Initial Catalog=sqldb-mras-prod;Persist Security Info=False;User ID=mrasadmin;Password=<PASSWORD>;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;
```

## BERT Service Deployment

### Create Container Apps Environment

```bash
az containerapp env create \
  --name "$CONTAINERAPPS_ENV" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --logs-workspace-id "$(az monitor log-analytics workspace show --resource-group "$RESOURCE_GROUP" --workspace-name "$LOG_ANALYTICS_NAME" --query customerId -o tsv)" \
  --logs-workspace-key "$(az monitor log-analytics workspace get-shared-keys --resource-group "$RESOURCE_GROUP" --workspace-name "$LOG_ANALYTICS_NAME" --query primarySharedKey -o tsv)"
```

### Create `bert_service`

```bash
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
```

```bash
az containerapp create \
  --name "$BERT_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINERAPPS_ENV" \
  --image "$BERT_IMAGE" \
  --target-port 8001 \
  --ingress external \
  --registry-server "$ACR_NAME.azurecr.io" \
  --registry-username "$ACR_USERNAME" \
  --registry-password "$ACR_PASSWORD" \
  --env-vars \
    BERT_MODEL_DIR=/app/models/distilbert-liar \
    BERT_MAX_LENGTH=256 \
    HF_HOME=/app/.cache/huggingface \
    APPLICATIONINSIGHTS_CONNECTION_STRING="$APPINSIGHTS_CONNECTION_STRING"
```

Get the BERT service URL:

```bash
BERT_SERVICE_URL="https://$(az containerapp show \
  --name "$BERT_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  -o tsv)"
```

### Update `bert_service`

Use this after publishing a new image:

```bash
az containerapp update \
  --name "$BERT_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$BERT_IMAGE"
```

## Backend Deployment

### Create App Service Plan

```bash
az appservice plan create \
  --name "$APP_SERVICE_PLAN" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --is-linux \
  --sku B1
```

### Create Web App from Container Image

```bash
az webapp create \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$APP_SERVICE_PLAN" \
  --name "$BACKEND_APP" \
  --deployment-container-image-name "$BACKEND_IMAGE"
```

### Configure Container Source

```bash
az webapp config container set \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --docker-custom-image-name "$BACKEND_IMAGE" \
  --docker-registry-server-url "https://$ACR_NAME.azurecr.io" \
  --docker-registry-server-user "$ACR_USERNAME" \
  --docker-registry-server-password "$ACR_PASSWORD"
```

### Configure Backend Application Settings

```bash
SQL_CONNECTION_STRING="Server=tcp:$SQL_SERVER.database.windows.net,1433;Initial Catalog=$SQL_DB;Persist Security Info=False;User ID=$SQL_ADMIN_USER;Password=$SQL_ADMIN_PASSWORD;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
```

```bash
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$BACKEND_APP" \
  --settings \
    WEBSITES_PORT=5000 \
    ASPNETCORE_ENVIRONMENT=Production \
    ASPNETCORE_URLS=http://+:5000 \
    BertService__Url="$BERT_SERVICE_URL" \
    MachineLearning__PythonExecutable=/opt/backend-venv/bin/python \
    MachineLearning__ClassicalPredictScriptPath=Services/Ml/classical_predict.py \
    MachineLearning__ClassicalModelDirectory=/app/Services/Ml/artifacts \
    MachineLearning__MediumRiskThreshold=0.35 \
    MachineLearning__HighRiskThreshold=0.70 \
    ConnectionStrings__DefaultConnection="$SQL_CONNECTION_STRING" \
    APPLICATIONINSIGHTS_CONNECTION_STRING="$APPINSIGHTS_CONNECTION_STRING"
```

### Configure CORS Origin

Update this after the Static Web App hostname is known.

```bash
FRONTEND_ORIGIN="https://<your-static-web-app-domain>"

az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$BACKEND_APP" \
  --settings Cors__AllowedOrigins__0="$FRONTEND_ORIGIN"
```

### Update Backend Image

```bash
az webapp config container set \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --docker-custom-image-name "$BACKEND_IMAGE" \
  --docker-registry-server-url "https://$ACR_NAME.azurecr.io" \
  --docker-registry-server-user "$ACR_USERNAME" \
  --docker-registry-server-password "$ACR_PASSWORD"
```

## Frontend Deployment

### Create Azure Static Web App

If you want GitHub-connected deployment:

```bash
az staticwebapp create \
  --name "$SWA_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --source "https://github.com/<your-org-or-user>/<your-repo>" \
  --branch "main" \
  --app-location "frontend" \
  --output-location "dist"
```

### Frontend Build-Time Variable

The frontend must use:

```text
VITE_API_BASE_URL
```

Set it in the Static Web Apps GitHub workflow or repository secret/variable so the build points to the backend hostname:

```text
VITE_API_BASE_URL=https://app-mras-api-prod-eaus2.azurewebsites.net
```

### Frontend Deployment Recommendation

Use GitHub Actions for Static Web Apps deployment:

1. push code to GitHub
2. build frontend in workflow
3. inject `VITE_API_BASE_URL`
4. publish `frontend/dist` to Static Web Apps

## Health Checks

### Backend Health

```bash
curl "https://$BACKEND_APP.azurewebsites.net/api/health"
```

Expected:

- HTTP `200`
- JSON response containing service checks

### BERT Service Health

```bash
curl "$BERT_SERVICE_URL/health"
```

Expected:

- HTTP `200`
- JSON payload with model status

### Frontend Reachability

Open the Static Web App URL in a browser and verify:

- the app loads
- clicking `Check System Health` returns backend status
- analyze requests succeed

## Smoke Test

Run this after all services are deployed.

### 1. Backend Health

```bash
curl "https://$BACKEND_APP.azurewebsites.net/api/health"
```

### 2. BERT Health

```bash
curl "$BERT_SERVICE_URL/health"
```

### 3. Analyze Endpoint

```bash
curl -X POST "https://$BACKEND_APP.azurewebsites.net/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The COVID-19 vaccine contains microchips for tracking",
    "content": "A viral post claims governments embedded tracking chips in vaccines.",
    "source": ""
  }'
```

Expected:

- HTTP `200`
- JSON response containing:
  - `riskLevel`
  - `confidenceScore`
  - `explanation`
  - `featureSignals`

### 4. Frontend End-to-End

Verify in the browser:

1. open the Static Web App URL
2. click `Check System Health`
3. submit a real claim
4. confirm result page renders with explainability output

## Troubleshooting

### Backend returns `500` on startup

Check:

- `ConnectionStrings__DefaultConnection`
- `BertService__Url`
- classical artifacts exist in the deployed image or mounted runtime path
- `MachineLearning__PythonExecutable=/opt/backend-venv/bin/python`

### Backend health check fails because BERT is unreachable

Check:

- `BERT_SERVICE_URL` is correct
- Container App ingress is enabled
- `bert_service` is healthy
- no typo in `BertService__Url`

### Frontend loads but API calls fail

Check:

- `VITE_API_BASE_URL` points to the backend public HTTPS URL
- backend CORS allows the Static Web App origin
- frontend build was redeployed after changing `VITE_API_BASE_URL`

### Azure SQL connection fails

Check:

- SQL firewall rules
- server and database names
- username/password in `ConnectionStrings__DefaultConnection`
- backend outbound access to Azure SQL

### App Service container does not start

Check:

- `WEBSITES_PORT=5000`
- `ASPNETCORE_URLS=http://+:5000`
- image tag exists in ACR
- ACR credentials are correct

Inspect logs:

```bash
az webapp log tail \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP"
```

### Container App image pull fails

Check:

- ACR image exists
- registry server is correct
- ACR username/password are valid
- image tag matches the pushed tag

### Application Insights has no data

Check:

- `APPLICATIONINSIGHTS_CONNECTION_STRING` is set in backend and bert_service
- the applications have received live traffic
- logs are flowing into the linked Log Analytics workspace

## Summary

This deployment model is the recommended Azure production-style target for the project:

- frontend on Static Web Apps
- backend on App Service for Containers
- BERT service on Container Apps
- Azure SQL for persistence
- ACR for images
- App Insights + Log Analytics for observability

Use local Docker deployment for local development and integration testing, and use this Azure deployment path for public demo, resume presentation, and production-style architecture discussion.
