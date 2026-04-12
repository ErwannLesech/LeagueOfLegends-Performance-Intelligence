# LoL Tracker

Suivi automatique des parties League of Legends avec pipeline Python -> PostgreSQL -> Google Sheets.

## Stack

| Composant | Techno |
|-----------|--------|
| Collecte | Python 3.11 + Riot API (MATCH-V5) |
| Base de donnees | PostgreSQL 16 (Docker) |
| Sync | Google Sheets via service account |
| BI | Looker Studio (connecteur PostgreSQL) |
| Analyse | Jupyter + pandas + seaborn |
| Scheduling Windows | Task Scheduler |

## Structure

```text
LeagueOfLegends-Performance-Intelligence/
├── collector/
│   ├── watcher.py
│   ├── riot_client.py
│   ├── models.py
│   └── rate_limiter.py
├── pipeline/
│   ├── transform.py
│   ├── load_db.py
│   ├── load_sheets.py
│   └── patch_meta.py
├── analysis/
│   ├── notebooks/
│   └── queries/
├── config/
│   ├── settings.py
│   └── sheets_schema.py
├── scripts/
│   ├── backfill.py
│   ├── setup_windows_task.ps1
│   └── sql/init_schema.sql
├── docker-compose.yml
├── requirements.txt
├── start_watcher.bat
└── README.md
```

## Prerequis

- Windows 10/11
- Python 3.11+
- Docker Desktop (avec Docker Compose)

## Setup rapide

```powershell
git clone https://github.com/TON_USERNAME/lol-tracker.git
cd lol-tracker
copy .env.example .env # ou cp pour linux
```

Puis editer `.env` avec vos valeurs (Riot API key, summoner, DB, Google Sheet).


Puis editer `.env` avec vos valeurs (Riot API key, summoner, DB, Google Sheet).

## Demarrage de la base PostgreSQL

```powershell
docker compose up -d
```

Le schema est initialise automatiquement via `scripts/sql/init_schema.sql`.

## Lancer le watcher manuellement

### Option A - Avec venv (recommande)

```powershell
cd C:\Users\lesec\Desktop\LeagueOfLegends-Performance-Intelligence

# Creer le venv si absent
python -m venv .venv

# Activer le venv
.\.venv\Scripts\Activate.ps1

# Installer les dependances
python -m pip install -r requirements.txt

# Lancer le watcher au premier plan
python -m collector.watcher
```

### Option B - Sans venv

```powershell
cd C:\Users\lesec\Desktop\LeagueOfLegends-Performance-Intelligence
python -m pip install -r requirements.txt
python -m collector.watcher
```

## Lancer watcher.py en direct (equivalent)

Si vous preferez lancer le fichier plutot que le module :

```powershell
python .\collector\watcher.py
```

## Faire tourner le watcher en continu au demarrage Windows

Le projet inclut :
- `start_watcher.bat` (creee/active le venv si besoin, installe les deps, puis lance `pythonw -m collector.watcher`)
- `scripts/setup_windows_task.ps1` (cree la tache planifiee Windows)

### 1. Executer le script de setup de la tache (une seule fois)

Dans PowerShell en administrateur :

```powershell
cd C:\Users\lesec\Desktop\LeagueOfLegends-Performance-Intelligence
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows_task.ps1
```

### 2. Demarrer la tache immediatement (optionnel)

```powershell
Start-ScheduledTask -TaskName "LoL-Tracker-Watcher"
```

### 3. Verifier et controler la tache

```powershell
# Voir la tache
Get-ScheduledTask -TaskName "LoL-Tracker-Watcher"

# Arreter la tache
Stop-ScheduledTask -TaskName "LoL-Tracker-Watcher"
```

Au prochain logon Windows, le watcher redemarrera automatiquement en arriere-plan.

## Commandes utiles

```powershell
# Backfill des 100 dernieres games
python .\scripts\backfill.py --count 100

# Patch meta actuel
python -m pipeline.patch_meta

# Ouvrir les notebooks
jupyter notebook .\analysis\notebooks\
```

Alternatives Linux:

```bash
# Backfill des 100 dernieres games
python3 ./scripts/backfill.py --count 100

# Patch meta actuel
python3 -m pipeline.patch_meta

# Ouvrir les notebooks
jupyter notebook ./analysis/notebooks/
```

## Licence

MIT
