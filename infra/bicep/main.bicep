targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short project identifier used in resource naming.')
param projectName string = 'mras'

@description('Environment suffix used in resource naming.')
param environmentName string = 'prod'

@description('Short region code used in resource naming.')
param regionCode string = 'eaus2'

@description('Azure Container Registry SKU.')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param acrSku string = 'Basic'

@description('Backend container image hosted in Azure Container Registry.')
param backendContainerImage string

@description('BERT service container image hosted in Azure Container Registry.')
param bertContainerImage string

@description('Frontend origin allowed by backend CORS settings.')
param frontendOrigin string = 'https://placeholder.invalid'

@description('Azure SQL administrator username.')
param sqlAdminLogin string

@secure()
@description('Azure SQL administrator password.')
param sqlAdminPassword string

@description('Azure SQL database SKU name.')
param sqlDatabaseSkuName string = 'S0'

@description('Azure SQL database SKU tier.')
param sqlDatabaseSkuTier string = 'Standard'

@description('Linux App Service Plan SKU name.')
param appServicePlanSkuName string = 'B1'

@description('Linux App Service Plan SKU tier.')
param appServicePlanSkuTier string = 'Basic'

@description('Requested CPU cores for the BERT Container App.')
param bertCpu int = 1

@description('Requested memory for the BERT Container App.')
param bertMemory string = '2Gi'

var acrName = 'acr${projectName}${environmentName}${regionCode}'
var logAnalyticsName = 'log-${projectName}-${environmentName}-${regionCode}'
var appInsightsName = 'appi-${projectName}-${environmentName}-${regionCode}'
var sqlServerName = 'sql-${projectName}-${environmentName}-${regionCode}'
var sqlDatabaseName = 'sqldb-${projectName}-${environmentName}'
var appServicePlanName = 'asp-${projectName}-${environmentName}-${regionCode}'
var backendWebAppName = 'app-${projectName}-api-${environmentName}-${regionCode}'
var containerAppsEnvironmentName = 'cae-${projectName}-${environmentName}-${regionCode}'
var bertContainerAppName = 'ca-${projectName}-bert-${environmentName}-${regionCode}'

module acr './modules/acr.bicep' = {
  name: 'acr'
  params: {
    name: acrName
    location: location
    skuName: acrSku
  }
}

module logging './modules/logging.bicep' = {
  name: 'logging'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsName
    appInsightsName: appInsightsName
  }
}

module sql './modules/sql.bicep' = {
  name: 'sql'
  params: {
    location: location
    serverName: sqlServerName
    databaseName: sqlDatabaseName
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    databaseSkuName: sqlDatabaseSkuName
    databaseSkuTier: sqlDatabaseSkuTier
  }
}

module appServicePlan './modules/appservice-plan.bicep' = {
  name: 'appservice-plan'
  params: {
    location: location
    name: appServicePlanName
    skuName: appServicePlanSkuName
    skuTier: appServicePlanSkuTier
  }
}

module containerAppsEnv './modules/containerapps-env.bicep' = {
  name: 'containerapps-env'
  params: {
    location: location
    name: containerAppsEnvironmentName
    logAnalyticsCustomerId: logging.outputs.logAnalyticsCustomerId
    logAnalyticsSharedKey: logging.outputs.logAnalyticsSharedKey
  }
}

var sqlConnectionString = 'Server=tcp:${sql.outputs.fullyQualifiedDomainName},1433;Initial Catalog=${sql.outputs.databaseName};Persist Security Info=False;User ID=${sqlAdminLogin};Password=${sqlAdminPassword};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'

module bertContainerApp './modules/containerapp-bert.bicep' = {
  name: 'containerapp-bert'
  params: {
    name: bertContainerAppName
    location: location
    environmentId: containerAppsEnv.outputs.id
    containerImage: bertContainerImage
    cpu: bertCpu
    memory: bertMemory
    registryServer: acr.outputs.loginServer
    registryUsername: acr.outputs.adminUsername
    registryPassword: acr.outputs.adminPassword
    appInsightsConnectionString: logging.outputs.appInsightsConnectionString
  }
}

module backendWebApp './modules/appservice-backend.bicep' = {
  name: 'appservice-backend'
  params: {
    name: backendWebAppName
    location: location
    serverFarmId: appServicePlan.outputs.id
    containerImage: backendContainerImage
    registryServer: acr.outputs.loginServer
    registryUsername: acr.outputs.adminUsername
    registryPassword: acr.outputs.adminPassword
    bertServiceUrl: bertContainerApp.outputs.serviceUrl
    sqlConnectionString: sqlConnectionString
    appInsightsConnectionString: logging.outputs.appInsightsConnectionString
    frontendOrigin: frontendOrigin
  }
}

output backendHostname string = backendWebApp.outputs.hostName
output bertServiceUrl string = bertContainerApp.outputs.serviceUrl
output sqlServerName string = sql.outputs.serverName
output appInsightsConnectionString string = logging.outputs.appInsightsConnectionString
