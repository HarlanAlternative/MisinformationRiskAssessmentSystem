<#
.SYNOPSIS
    Deploy the published container images to Azure Container Apps.

.DESCRIPTION
    Deployment is manual rather than part of a workflow. A workflow would need a
    service principal to authenticate to Azure, and the tenant this subscription
    belongs to sets allowedToCreateApps to false, so none can be created. This
    script runs against your own 'az login' instead.

    Images are built and published by the backend-container and
    bert-service-container workflows to GitHub Container Registry. This script
    only points the Container Apps at a tag; it does not build anything.

    Both apps scale to zero, so an idle deployment costs nothing beyond storage.
    The first request after an idle period pays a cold start while the image is
    pulled and DistilBERT is loaded, which takes roughly a minute for the BERT
    service.

.EXAMPLE
    .\scripts\deploy_azure.ps1
    Deploy the 'latest' tag of both images.

.EXAMPLE
    .\scripts\deploy_azure.ps1 -ImageTag 4f2c1ab
    Deploy a specific commit's images.
#>
[CmdletBinding()]
param(
    [string]$ImageTag = "latest",
    [string]$ResourceGroup = "rg-mras-student",
    [string]$Environment = "mras-env",
    [string]$SourceRegistry = "ghcr.io",
    [string]$Owner = "harlanalternative",
    [string]$Registry = "acrmrasstudent",
    [switch]$SkipImport,
    [string]$SubscriptionId = "0faf8200-a54e-47ec-bcb8-63fcec991a5a"
)

$ErrorActionPreference = "Stop"

$RegistryServer = "$Registry.azurecr.io"
$Repositories = @{
    "mras-bert"     = "mras-bert-service"
    "mras-backend"  = "mras-backend"
    "mras-frontend" = "mras-frontend"
}

$BertImage = "$RegistryServer/mras-bert-service:$ImageTag"
$BackendImage = "$RegistryServer/mras-backend:$ImageTag"
$FrontendImage = "$RegistryServer/mras-frontend:$ImageTag"

function Invoke-Az {
    param([string[]]$Arguments)

    $output = & az @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "az $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
    return $output
}

Write-Host "Subscription: $SubscriptionId"
Invoke-Az @("account", "set", "--subscription", $SubscriptionId) | Out-Null

$current = (Invoke-Az @("account", "show", "--query", "name", "-o", "tsv"))
Write-Host "Deploying into '$current' / $ResourceGroup"
Write-Host "  BERT service : $BertImage"
Write-Host "  Backend      : $BackendImage"
Write-Host "  Frontend     : $FrontendImage"
Write-Host ""

# The workflows publish to ghcr, because building in Actions needs no Azure
# credential and none can be issued here. Azure pulls from its own registry, so
# the tags are copied across first. az acr import runs server side, so the images
# never travel through this machine.
if (-not $SkipImport) {
    foreach ($repository in ($Repositories.Values | Sort-Object -Unique)) {
        Write-Host "Importing $repository`:$ImageTag into $Registry ..."
        Invoke-Az @(
            "acr", "import",
            "--name", $Registry,
            "--source", "$SourceRegistry/$Owner/$repository`:$ImageTag",
            "--image", "$repository`:$ImageTag",
            "--force"
        ) | Out-Null
    }
    Write-Host ""
}

# Container Apps authenticates to the registry with admin credentials. A managed
# identity holding AcrPull would be preferable, but creating that role assignment
# is refused on this subscription, whose Microsoft.Authorization endpoint returns
# MissingSubscription even for reads.
$registryUser = Invoke-Az @("acr", "credential", "show", "--name", $Registry, "--query", "username", "-o", "tsv")
$registryPassword = Invoke-Az @("acr", "credential", "show", "--name", $Registry, "--query", "passwords[0].value", "-o", "tsv")

function Set-ContainerApp {
    param(
        [string]$Name,
        [string]$Image,
        [int]$TargetPort,
        [string]$Ingress,
        [string[]]$EnvVars = @(),
        [string]$Cpu = "1.0",
        [string]$Memory = "2.0Gi"
    )

    # Deliberately a list rather than a show. 'az containerapp show' writes to
    # stderr when the app is absent, which PowerShell turns into a terminating
    # error under ErrorActionPreference Stop - so the very check for "does this
    # exist yet" would abort the first run. A list returns empty and exits 0.
    $existing = Invoke-Az @(
        "containerapp", "list", "--resource-group", $ResourceGroup, "--query", "[].name", "-o", "tsv"
    )

    if ($existing -contains $Name) {
        Write-Host "Updating $Name ..."

        # Set before the image is changed, so a first switch to the registry does
        # not roll out a revision that cannot pull.
        Invoke-Az @(
            "containerapp", "registry", "set",
            "--name", $Name,
            "--resource-group", $ResourceGroup,
            "--server", $RegistryServer,
            "--username", $registryUser,
            "--password", $registryPassword
        ) | Out-Null

        $arguments = @(
            "containerapp", "update",
            "--name", $Name,
            "--resource-group", $ResourceGroup,
            "--image", $Image
        )
        if ($EnvVars.Count -gt 0) {
            $arguments += "--set-env-vars"
            $arguments += $EnvVars
        }
        Invoke-Az $arguments | Out-Null
    }
    else {
        Write-Host "Creating $Name ..."
        $arguments = @(
            "containerapp", "create",
            "--name", $Name,
            "--resource-group", $ResourceGroup,
            "--environment", $Environment,
            "--image", $Image,
            "--target-port", $TargetPort,
            "--ingress", $Ingress,
            "--cpu", $Cpu,
            "--memory", $Memory,
            "--min-replicas", "0",
            "--max-replicas", "1",
            "--registry-server", $RegistryServer,
            "--registry-username", $registryUser,
            "--registry-password", $registryPassword
        )
        if ($EnvVars.Count -gt 0) {
            $arguments += "--env-vars"
            $arguments += $EnvVars
        }
        Invoke-Az $arguments | Out-Null
    }
}

# Internal ingress: only the backend calls this, so it never needs a public address.
Set-ContainerApp -Name "mras-bert" -Image $BertImage -TargetPort 8001 -Ingress "internal" `
    -EnvVars @("BERT_MODEL_DIR=/app/models/distilbert-liar", "BERT_MAX_LENGTH=256")

$bertFqdn = Invoke-Az @(
    "containerapp", "show", "--name", "mras-bert", "--resource-group", $ResourceGroup,
    "--query", "properties.configuration.ingress.fqdn", "-o", "tsv"
)
Write-Host "  BERT internal FQDN: $bertFqdn"

# https, not http. Container Apps ingress defaults to allowInsecure false, so an
# http call is answered with a redirect; HttpClient follows it but downgrades the
# POST to a GET, and /predict then returns 405. Health checks still passed because
# a redirected GET is still a GET, so this only surfaced on a real analysis.
Set-ContainerApp -Name "mras-backend" -Image $BackendImage -TargetPort 5000 -Ingress "external" `
    -EnvVars @(
        "BertService__Url=https://$bertFqdn",
        "ASPNETCORE_URLS=http://+:5000",
        "MachineLearning__PythonExecutable=/opt/backend-venv/bin/python"
    )

$backendFqdn = Invoke-Az @(
    "containerapp", "show", "--name", "mras-backend", "--resource-group", $ResourceGroup,
    "--query", "properties.configuration.ingress.fqdn", "-o", "tsv"
)
Write-Host "  Backend FQDN: $backendFqdn"

# nginx proxies /api to the backend, so the browser only ever talks to this
# origin and no CORS configuration is needed. Static Web Apps would have been the
# obvious home for this, but every region it offers is blocked by the region
# policy on this subscription.
Set-ContainerApp -Name "mras-frontend" -Image $FrontendImage -TargetPort 80 -Ingress "external" `
    -EnvVars @("BACKEND_URL=https://$backendFqdn") -Cpu "0.25" -Memory "0.5Gi"

$frontendFqdn = Invoke-Az @(
    "containerapp", "show", "--name", "mras-frontend", "--resource-group", $ResourceGroup,
    "--query", "properties.configuration.ingress.fqdn", "-o", "tsv"
)

Write-Host ""
Write-Host "Deployed."
Write-Host "  App     : https://$frontendFqdn"
Write-Host "  Backend : https://$backendFqdn"
Write-Host "  Health  : https://$backendFqdn/api/health"
Write-Host ""
Write-Host "All apps scale to zero; the first request after idling pays a cold start."
