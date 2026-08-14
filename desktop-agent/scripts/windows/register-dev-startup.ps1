# Development-only: add a current-user Startup shortcut. Reversible.
# Does NOT install a Windows Service.
# Usage (PowerShell):
#   .\scripts\windows\register-dev-startup.ps1
#   .\scripts\windows\unregister-dev-startup.ps1

$ErrorActionPreference = "Stop"
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "WorkPulseAgent-Dev.lnk"
$agentRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Error "python was not found on PATH"
}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $python
$shortcut.Arguments = "main.py"
$shortcut.WorkingDirectory = $agentRoot.Path
$shortcut.WindowStyle = 7
$shortcut.Description = "WorkPulse desktop agent (development)"
$shortcut.Save()
Write-Host "Created $shortcutPath"
Write-Host "Remove it with unregister-dev-startup.ps1 or delete the shortcut."
