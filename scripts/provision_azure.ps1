<#
.SYNOPSIS
    Provision the Azure infrastructure this project runs on.

.DESCRIPTION
    One-time setup, separate from scripts/deploy_azure.ps1, which only rolls out
    container images. Everything here is idempotent, so re-running it after a
    partial failure is safe.

    Creates:
      - a resource group
      - a Container Apps environment (no Log Analytics workspace, so no log bill)
      - an Azure SQL server and a database on the free serverless tier, set to
        pause rather than bill when the monthly free allocation is exhausted
      - a firewall rule permitting Azure services to reach the database
      - the connection string, stored as a Container App secret

    The SQL admin password is generated unless supplied and is printed once. It is
    not needed again: the connection string it produces is written straight into a
    Container App secret. Record it anyway if you want to reach the database with
    other tools.

    Two things this cannot do on the subscription it was written for:
    Static Web Apps is refused, because every region it operates in is blocked by
    the subscription's region policy, so the frontend runs as a Container App
    instead. And no service principal can be created for CI to deploy with, since
    the tenant sets allowedToCreateApps to false, which is why deployment is a
    manual script rather than a workflow.

.EXAMPLE
    .\scripts\provision_azure.ps1
#>
[CmdletBinding()]
param(
    [string]$ResourceGroup = "rg-mras-student",
    [string]$Location = "australiaeast",
    [string]$Environment = "mras-env",
    [string]$SqlServer = "",
    [string]$SqlDatabase = "mrasdb",
    [string]$SqlAdminUser = "mrasadmin",
    [string]$SqlAdminPassword = "",
    [string]$BackendApp = "mras-backend",
    [string]$SubscriptionId = "0faf8200-a54e-47ec-bcb8-63fcec991a5a"
)

$ErrorActionPreference = "Stop"

function Invoke-Az {
    param([string[]]$Arguments)

    $output = & az @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "az $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
    return $output
}

function New-SqlPassword {
    # Starts with a letter so the CLI cannot mistake it for an argument, and
    # avoids characters that need shell quoting.
    $body = [char[]]("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%@")
    $first = [char[]]("ABCDEFGHIJKLMNOPQRSTUVWXYZ") | Get-Random
    $rest = -join (1..27 | ForEach-Object { $body | Get-Random })
    return "$first$rest"
}

Invoke-Az @("account", "set", "--subscription", $SubscriptionId) | Out-Null
Write-Host "Subscription: $(Invoke-Az @('account','show','--query','name','-o','tsv'))"

# Providers are not registered on a fresh subscription and registration is async.
foreach ($provider in @("Microsoft.App", "Microsoft.OperationalInsights", "Microsoft.Sql")) {
    $state = Invoke-Az @("provider", "show", "--namespace", $provider, "--query", "registrationState", "-o", "tsv")
    if ($state -ne "Registered") {
        Write-Host "Registering $provider (this can take a few minutes) ..."
        Invoke-Az @("provider", "register", "--namespace", $provider, "--wait") | Out-Null
    }
}

Write-Host "Resource group $ResourceGroup ..."
Invoke-Az @("group", "create", "--name", $ResourceGroup, "--location", $Location) | Out-Null

$envs = Invoke-Az @("containerapp", "env", "list", "--resource-group", $ResourceGroup, "--query", "[].name", "-o", "tsv")
if ($envs -contains $Environment) {
    Write-Host "Container Apps environment $Environment already exists."
}
else {
    Write-Host "Creating Container Apps environment $Environment ..."
    # No Log Analytics workspace: it is the only part of this that would bill by
    # default, and container logs remain readable with 'az containerapp logs show'.
    Invoke-Az @(
        "containerapp", "env", "create",
        "--name", $Environment,
        "--resource-group", $ResourceGroup,
        "--location", $Location,
        "--logs-destination", "none"
    ) | Out-Null
}

# A SQL server name is globally unique, so reuse whatever is already in the group
# rather than failing on a name that is taken.
if (-not $SqlServer) {
    $existing = Invoke-Az @("sql", "server", "list", "--resource-group", $ResourceGroup, "--query", "[0].name", "-o", "tsv")
    $SqlServer = if ($existing) { $existing } else { "sql-mras-$(Get-Random -Minimum 10000 -Maximum 99999)" }
}

$servers = Invoke-Az @("sql", "server", "list", "--resource-group", $ResourceGroup, "--query", "[].name", "-o", "tsv")
$passwordWasGenerated = $false

if ($servers -contains $SqlServer) {
    Write-Host "SQL server $SqlServer already exists."
    if (-not $SqlAdminPassword) {
        throw "SQL server $SqlServer exists but no -SqlAdminPassword was supplied, so the connection string cannot be rebuilt. Re-run with the password, or drop the server to start clean."
    }
}
else {
    if (-not $SqlAdminPassword) {
        $SqlAdminPassword = New-SqlPassword
        $passwordWasGenerated = $true
    }
    Write-Host "Creating SQL server $SqlServer ..."
    Invoke-Az @(
        "sql", "server", "create",
        "--name", $SqlServer,
        "--resource-group", $ResourceGroup,
        "--location", $Location,
        "--admin-user", $SqlAdminUser,
        "--admin-password", $SqlAdminPassword
    ) | Out-Null
}

# 0.0.0.0 is the special value meaning "Azure services", not the public internet.
$rules = Invoke-Az @("sql", "server", "firewall-rule", "list", "--server", $SqlServer, "--resource-group", $ResourceGroup, "--query", "[].name", "-o", "tsv")
if ($rules -notcontains "AllowAzureServices") {
    Write-Host "Allowing Azure services through the SQL firewall ..."
    Invoke-Az @(
        "sql", "server", "firewall-rule", "create",
        "--name", "AllowAzureServices",
        "--server", $SqlServer,
        "--resource-group", $ResourceGroup,
        "--start-ip-address", "0.0.0.0",
        "--end-ip-address", "0.0.0.0"
    ) | Out-Null
}

$databases = Invoke-Az @("sql", "db", "list", "--server", $SqlServer, "--resource-group", $ResourceGroup, "--query", "[].name", "-o", "tsv")
if ($databases -contains $SqlDatabase) {
    Write-Host "Database $SqlDatabase already exists."
}
else {
    Write-Host "Creating database $SqlDatabase on the free serverless tier ..."
    # AutoPause, not BillOverUsage: exhausting the monthly free allocation should
    # stop the database, never quietly start charging.
    Invoke-Az @(
        "sql", "db", "create",
        "--name", $SqlDatabase,
        "--server", $SqlServer,
        "--resource-group", $ResourceGroup,
        "--edition", "GeneralPurpose",
        "--compute-model", "Serverless",
        "--family", "Gen5",
        "--capacity", "2",
        "--use-free-limit",
        "--free-limit-exhaustion-behavior", "AutoPause",
        "--backup-storage-redundancy", "Local"
    ) | Out-Null
}

$apps = Invoke-Az @("containerapp", "list", "--resource-group", $ResourceGroup, "--query", "[].name", "-o", "tsv")
if ($apps -contains $BackendApp) {
    Write-Host "Storing the connection string as a secret on $BackendApp ..."
    $connection = "Server=tcp:$SqlServer.database.windows.net,1433;Initial Catalog=$SqlDatabase;Persist Security Info=False;User ID=$SqlAdminUser;Password=$SqlAdminPassword;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=60;"
    Invoke-Az @("containerapp", "secret", "set", "--name", $BackendApp, "--resource-group", $ResourceGroup, "--secrets", "sqlconn=$connection") | Out-Null
    Invoke-Az @(
        "containerapp", "update", "--name", $BackendApp, "--resource-group", $ResourceGroup,
        "--set-env-vars", "ConnectionStrings__DefaultConnection=secretref:sqlconn"
    ) | Out-Null
    Write-Host "  Backend now reads the connection string from the 'sqlconn' secret."
}
else {
    Write-Host "Backend app not deployed yet. Run scripts/deploy_azure.ps1, then re-run this with -SqlAdminPassword to attach the database."
}

Write-Host ""
Write-Host "Provisioned."
Write-Host "  Resource group : $ResourceGroup"
Write-Host "  Environment    : $Environment"
Write-Host "  SQL server     : $SqlServer"
Write-Host "  Database       : $SqlDatabase (free tier, pauses instead of billing)"

if ($passwordWasGenerated) {
    Write-Host ""
    Write-Host "SQL admin password (shown once, not stored anywhere in this repository):"
    Write-Host "  $SqlAdminPassword"
    Write-Host "The backend does not need it again; it reads the connection string from the secret above."
}

Write-Host ""
Write-Host "Next: .\scripts\deploy_azure.ps1"
