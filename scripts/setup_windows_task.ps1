# setup_windows_task.ps1
# Enregistre le watcher comme tâche Windows au démarrage de session.
# Lancer en PowerShell administrateur une seule fois.
#
# Usage :
#   powershell -ExecutionPolicy Bypass -File setup_windows_task.ps1

$TaskName = "LoL-Tracker-Watcher"
$RepoPath = "$env:USERPROFILE\lol-tracker"   # <-- Adapter si ton repo est ailleurs
$BatFile  = "$RepoPath\start_watcher.bat"
$LogDir   = "$RepoPath\logs"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Supprimer l'ancienne tâche si elle existe
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Ancienne tâche supprimée."
}

$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatFile`"" `
    -WorkingDirectory $RepoPath

# Démarrage à la connexion de session + redémarrage auto si crash
$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 10 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Description "LoL Tracker — démarre le watcher Riot API au démarrage Windows"

Write-Host ""
Write-Host "Tâche '$TaskName' enregistrée."
Write-Host "Elle démarrera automatiquement à la prochaine connexion Windows."
Write-Host ""
Write-Host "Pour démarrer immédiatement :"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Pour arrêter :"
Write-Host "  Stop-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Logs : $LogDir\watcher.log"