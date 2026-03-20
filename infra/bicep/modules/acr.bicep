param name string
param location string

@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param skuName string = 'Basic'

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  sku: {
    name: skuName
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

var credentials = listCredentials(registry.id, '2023-07-01')

output id string = registry.id
output name string = registry.name
output loginServer string = registry.properties.loginServer
output adminUsername string = credentials.username
@secure()
output adminPassword string = credentials.passwords[0].value
