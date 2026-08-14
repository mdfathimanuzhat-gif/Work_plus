# Remove the development Startup shortcut created by register-dev-startup.ps1.
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "WorkPulseAgent-Dev.lnk"
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "Removed $shortcutPath"
} else {
    Write-Host "No development shortcut at $shortcutPath"
}
