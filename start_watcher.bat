@echo off
:: LoL Tracker — Watcher auto-start
:: Place ce fichier à la racine du repo.
:: Lance-le une première fois manuellement pour installer les dépendances.
:: Ensuite le Task Scheduler le relance automatiquement.

set REPO=%~dp0
cd /d %REPO%

:: Crée le venv si absent
if not exist ".venv\Scripts\pythonw.exe" (
    echo [LoL Tracker] Creating virtual environment...
    python -m venv .venv
)

:: Active le venv
call .venv\Scripts\activate.bat

:: Installe / met à jour les dépendances silencieusement
pip install -r requirements.txt --quiet

:: Lance le watcher sans fenêtre console
echo [LoL Tracker] Starting watcher...
start /B pythonw -m collector.watcher

echo [LoL Tracker] Watcher started. Logs in logs\watcher.log