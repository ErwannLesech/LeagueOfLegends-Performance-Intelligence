# LoL Tracker

Suivi automatisé des parties League of Legends via l'API Riot Games.  
Pipeline Python → PostgreSQL → Google Sheets → Looker Studio.

---

## Stack

| Composant | Techno |
|-----------|--------|
| Collecte | Python 3.11 + Riot API (MATCH-V5) |
| Base de données | PostgreSQL 16 (Docker) |
| Sync | Google Sheets via service account |
| BI | Looker Studio (connecteur PostgreSQL) |
| Analyse | Jupyter + pandas + seaborn |
| Scheduling (Windows) | Task Scheduler + `schedule` |

---

## Structure

```
lol-tracker/
├── collector/
│   ├── watcher.py          # Polling loop — détecte nouvelles games
│   ├── riot_client.py      # Wrapper Riot API (MATCH-V5, SUMMONER-V4, etc.)
│   ├── models.py           # Pydantic models (ParticipantStats, MatchSummary)
│   └── rate_limiter.py     # Rate limiter 90 req/120s (clé dev)
│
├── pipeline/
│   ├── transform.py        # Raw API response → ParticipantStats
│   ├── load_db.py          # Upsert PostgreSQL (idempotent)
│   ├── load_sheets.py      # Push vers Google Sheets
│   └── patch_meta.py       # Fetch Data Dragon (méta patch)
│
├── analysis/
│   ├── notebooks/
│   │   ├── 01_eda.ipynb              # Vue d'ensemble + winrate trends
│   │   ├── 02_matchup_stats.ipynb    # Heatmap matchups
│   │   └── 03_draft_model_prep.ipynb # Feature engineering + scoring function
│   └── queries/
│       ├── winrate_by_champion.sql   # Pour Looker Studio
│       ├── matchup_matrix.sql
│       └── session_trends.sql
│
├── config/
│   ├── settings.py         # Config centrale (lit .env)
│   └── sheets_schema.py    # Mapping colonnes DB ↔ Google Sheets
│
├── scripts/
│   ├── backfill.py         # Import historique (dernières N games)
│   ├── setup_windows_task.ps1  # Enregistre le watcher au démarrage Windows
│   └── sql/init_schema.sql # Schéma PostgreSQL (auto-chargé par Docker)
│
├── docker-compose.yml      # PostgreSQL + pgAdmin
├── requirements.txt
└── .env.example
```

---

## Installation

### 1. Prérequis

- Python 3.11+
- Docker + Docker Compose
- Un compte Riot Developer : https://developer.riotgames.com
- Un Google Sheet partagé avec un compte de service (voir section Google Sheets)

### 2. Cloner et configurer

```bash
git clone https://github.com/TON_USERNAME/lol-tracker.git
cd lol-tracker

cp .env.example .env
# Éditer .env avec ta clé API, ton summoner name, etc.
```

### 3. Environnement Python

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 4. Démarrer la base de données

```bash
docker-compose up -d
```

PostgreSQL disponible sur `localhost:5432`.  
pgAdmin (interface web) sur `http://localhost:5050` — identifiants dans `docker-compose.yml`.

Le schéma SQL est chargé automatiquement au premier démarrage via `scripts/sql/init_schema.sql`.

### 5. Vérifier la connexion DB

```bash
python -c "from pipeline.load_db import init_db; init_db(); print('DB OK')"
```

---

## Configuration Google Sheets

1. Aller sur [console.cloud.google.com](https://console.cloud.google.com)
2. Créer un projet → activer **Google Sheets API** + **Google Drive API**
3. Créer un compte de service → télécharger le JSON → sauvegarder en `service_account.json` à la racine (fichier ignoré par `.gitignore`)
4. Ouvrir ton Google Sheet → Partager avec l'email du compte de service (rôle : Éditeur)
5. Copier l'ID du sheet (dans l'URL : `/d/<ID>/edit`) dans `.env` → `GOOGLE_SPREADSHEET_ID`

⚠️ Le document cible doit être un **Google Sheet natif** (pas un fichier Excel `.xlsx` uploadé dans Drive).

---

## Utilisation

### Backfill — importer l'historique

```bash
# 20 dernières games suivies (ranked solo/duo + ranked flex)
python scripts/backfill.py

# 100 dernières games
python scripts/backfill.py --count 100

# Toutes queues
python scripts/backfill.py --count 50 --queue 0

# Sans push Sheets (DB seulement)
python scripts/backfill.py --db-only
```

### Watcher — surveillance en temps réel

```bash
# Linux (foreground)
python -m collector.watcher

# Windows (background, pas de console)
pythonw -m collector.watcher
```

Le watcher poll toutes les `WATCHER_POLL_INTERVAL` secondes (défaut : 5 min).  
Il détecte automatiquement les nouvelles games et les insère en DB + Sheets.

### Enregistrer le watcher au démarrage Windows

Lancer PowerShell en administrateur puis :

```powershell
# Adapter le chemin repo dans le script d'abord
powershell -ExecutionPolicy Bypass -File scripts\setup_windows_task.ps1
```

Le watcher démarrera automatiquement à chaque ouverture de session Windows.

### Fetch méta patch (Data Dragon)

```bash
# Patch actuel
python -m pipeline.patch_meta

# Patch spécifique
python -m pipeline.patch_meta --patch 14.8
```

### Notebooks

```bash
jupyter notebook analysis/notebooks/
```

- `01_eda.ipynb` — winrate global, CS/min, corrélation mental/résultat
- `02_matchup_stats.ipynb` — heatmap matchups, top matchups difficiles
- `03_draft_model_prep.ipynb` — scoring function + préparation ML

---

## Données collectées automatiquement

Chaque game insérée en DB contient :

| Catégorie | Champs |
|-----------|--------|
| Identification | match_id, game_date, patch, queue, match_type |
| Champion | champion_name, champion_level, role, lane, opponent_champion |
| Résultat | win, result, duration |
| KDA | kills, deaths, assists, kda_ratio, kill_participation |
| Farming | cs_total, cs_per_min, gold_earned, gold_per_min |
| Vision | vision_score, wards_placed, wards_killed, control_wards |
| Combat | damage_dealt, damage_taken, solo_kills, first_blood |
| Objectifs | turrets, inhibitors, dragon_kills, baron_kills |

Les champs manuels (mental_pregame, review, key_takeaway, etc.) restent vides et se remplissent directement dans Google Sheets ou dans le fichier Excel.

`match_type` est normalisé côté pipeline: `ranked_solo_duo`, `ranked_flex`, `other`.

---

## Looker Studio

1. Ouvrir [lookerstudio.google.com](https://lookerstudio.google.com)
2. Créer une source de données → **PostgreSQL**
3. Host : `localhost` (ou IP de la machine qui héberge Docker)
4. Port : `5432`, DB : `lol_tracker`, user/password dans `.env`
5. Utiliser les requêtes SQL dans `analysis/queries/` comme **Custom Query**

Les 3 requêtes disponibles :
- `winrate_by_champion.sql` — stats globales par champion
- `matchup_matrix.sql` — winrate par matchup
- `session_trends.sql` — corrélations session / mental / performance

---

## Roadmap

- [x] Collecte automatique post-game (MATCH-V5)
- [x] Stockage PostgreSQL (idempotent)
- [x] Sync Google Sheets
- [x] Backfill historique
- [x] Notebooks EDA + matchup
- [x] Scoring function draft (heuristique)
- [ ] Scraping lolalytics pour méta counters en temps réel
- [ ] Modèle ML draft recommendation (XGBoost / LogReg)
- [ ] Bot Discord (notifications post-game + commande `/pick`)

---

## Notes clé dev Riot

La clé de développement expire toutes les **24 heures** et est limitée à **100 req/2min**.  
Le rate limiter intégré reste conservativement en dessous de ce seuil.  
Pour un usage continu, soumettre une **Personal App** sur le portail Riot Developer.

---

## Licence

MIT
