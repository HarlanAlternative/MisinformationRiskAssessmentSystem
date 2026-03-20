param name string
param location string
param environmentId string
param containerImage string
param registryServer string
param registryUsername string

@secure()
param registryPassword string

param appInsightsConnectionString string
param cpu int = 1
param memory string = '2Gi'

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: name
  location: location
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8001
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: registryPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'bert-service'
          image: containerImage
          env: [
            {
              name: 'BERT_MODEL_DIR'
              value: '/app/models/distilbert-liar'
            }
            {
              name: 'BERT_MAX_LENGTH'
              value: '256'
            }
            {
              name: 'HF_HOME'
              value: '/app/.cache/huggingface'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsightsConnectionString
            }
          ]
          resources: {
            cpu: cpu
            memory: memory
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8001
              }
              initialDelaySeconds: 30
              periodSeconds: 15
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8001
              }
              initialDelaySeconds: 15
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output id string = containerApp.id
output fqdn string = containerApp.properties.configuration.ingress.fqdn
output serviceUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
