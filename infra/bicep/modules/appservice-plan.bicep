param location string
param name string
param skuName string = 'B1'
param skuTier string = 'Basic'

resource plan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: name
  location: location
  kind: 'linux'
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    reserved: true
  }
}

output id string = plan.id
output name string = plan.name
