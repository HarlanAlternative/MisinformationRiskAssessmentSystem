param location string
param logAnalyticsWorkspaceName string
param appInsightsName string

resource workspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  sku: {
    name: 'PerGB2018'
  }
  properties: {
    retentionInDays: 30
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

var workspaceKeys = listKeys(workspace.id, '2022-10-01')

output logAnalyticsWorkspaceId string = workspace.id
output logAnalyticsCustomerId string = workspace.properties.customerId
@secure()
output logAnalyticsSharedKey string = workspaceKeys.primarySharedKey
output appInsightsId string = applicationInsights.id
output appInsightsConnectionString string = applicationInsights.properties.ConnectionString
