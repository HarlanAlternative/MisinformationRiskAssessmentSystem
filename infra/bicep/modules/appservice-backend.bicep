param name string
param location string
param serverFarmId string
param containerImage string
param registryServer string
param registryUsername string

@secure()
param registryPassword string

param bertServiceUrl string

@secure()
param sqlConnectionString string

param appInsightsConnectionString string
param frontendOrigin string

resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: name
  location: location
  kind: 'app,linux,container'
  properties: {
    serverFarmId: serverFarmId
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerImage}'
      alwaysOn: true
      healthCheckPath: '/api/health'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appCommandLine: ''
    }
  }
}

resource appSettings 'Microsoft.Web/sites/config@2022-09-01' = {
  name: '${webApp.name}/appsettings'
  properties: {
    WEBSITES_PORT: '5000'
    ASPNETCORE_ENVIRONMENT: 'Production'
    ASPNETCORE_URLS: 'http://+:5000'
    BertService__Url: bertServiceUrl
    MachineLearning__PythonExecutable: '/opt/backend-venv/bin/python'
    MachineLearning__ClassicalPredictScriptPath: 'Services/Ml/classical_predict.py'
    MachineLearning__ClassicalModelDirectory: '/app/Services/Ml/artifacts'
    MachineLearning__MediumRiskThreshold: '0.35'
    MachineLearning__HighRiskThreshold: '0.70'
    Cors__AllowedOrigins__0: frontendOrigin
    ConnectionStrings__DefaultConnection: sqlConnectionString
    APPLICATIONINSIGHTS_CONNECTION_STRING: appInsightsConnectionString
    DOCKER_REGISTRY_SERVER_URL: 'https://${registryServer}'
    DOCKER_REGISTRY_SERVER_USERNAME: registryUsername
    DOCKER_REGISTRY_SERVER_PASSWORD: registryPassword
  }
  dependsOn: [
    webApp
  ]
}

output hostName string = webApp.properties.defaultHostName
output httpsUrl string = 'https://${webApp.properties.defaultHostName}'
