# Agent Python ITA Jobs

## Installation locale

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variables d'environnement

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
JOBS_ARCHIVE_MISSED_THRESHOLD=2
USER_AGENT=ITA Jobs Bot/1.0 (+https://example.org)
```

## Lancement local

### Tous les connecteurs activés
```bash
python -m app.main_collect_daily --skip-paris-guard
```

### Un seul connecteur
```bash
python -m app.main_backfill_sources --source arvalis
```

### Healthcheck
```bash
python -m app.main_healthcheck
```
