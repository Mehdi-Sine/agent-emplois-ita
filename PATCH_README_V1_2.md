# Patch V1.2 – 6 nouvelles sources + schedule quotidien

## Ce patch contient
- 6 nouveaux connecteurs :
  - `agent/app/connectors/acta.py`
  - `agent/app/connectors/armeflhor.py`
  - `agent/app/connectors/astredhor.py`
  - `agent/app/connectors/ceva.py`
  - `agent/app/connectors/inov3pt.py`
  - `agent/app/connectors/cnpf.py`
- 1 script SQL d’ajout des sources :
  - `SQL_V1_2_ADD_SOURCES.sql`
- 1 script de test local :
  - `agent/scripts/test_v1_2_sources.ps1`
- 1 script de backfill ciblé :
  - `agent/scripts/backfill_v1_2_sources.ps1`
- 1 snippet registry si votre registre est explicite :
  - `PATCH_REGISTRY_SNIPPET_V1_2.txt`
- 1 snippet de schedule GitHub Actions :
  - `PATCH_WORKFLOW_SCHEDULE_V1_2.yml.snippet`

## Webapp
Aucune modification de code webapp n’est incluse dans ce patch V1.2.
Raison : les pages V1.1 sont déjà pilotées par les données Supabase (`sources`, vues de monitoring, offres actives/archivées).
Après insertion SQL + premier run, les nouvelles sources doivent remonter automatiquement dans l’app.

## Analyse retenue par source
### ACTA
Source : Welcome to the Jungle.
Le connecteur suit les vraies URLs détail des offres et exclut la candidature spontanée.

### ARMEFLHOR
Source : catégorie WordPress `recrutement`.
Le connecteur récupère les articles de recrutement et parse la fiche détail.
Heuristique d’archivage immédiat :
- si la fiche mentionne explicitement `offre pourvue` ou `recrutement terminé`
- ou si la publication a plus de 180 jours (page d’archives durable)

### ASTREDHOR
Source : page `Nous rejoindre`.
À date, la page expose une candidature spontanée et un bloc “Toutes nos offres” mais aucune offre exploitable n’est visible dans le HTML parsé.
Le connecteur est donc volontairement conservateur : il retourne 0 offre active tant qu’aucune vraie fiche distincte n’est détectée.

### CEVA
Source : page recrutement unique.
À date, la page expose une seule offre en cours directement sur la page.

### inov3PT
Source : page unique `Recrutements`.
Les offres visibles sont marquées `Logo offre pourvue` ou `Recrutement terminé`.
Le connecteur les remonte donc immédiatement en `is_filled = true`.

### CNPF
Source : page liste + PDFs de fiches.
Le connecteur parse la page liste, associe chaque résumé à son PDF, et archive immédiatement les offres dont la date limite de candidature est dépassée.

## Installation
1. Placez-vous à la racine du repo :
```powershell
Set-Location C:\dev\agent-emplois-ita
```

2. Copiez les fichiers du zip dans le repo en respectant l’arborescence.

3. Si votre registry est explicite, appliquez `PATCH_REGISTRY_SNIPPET_V1_2.txt`.

4. Ajoutez les 6 sources en base :
```sql
-- exécuter SQL_V1_2_ADD_SOURCES.sql
```

## Test unitaire local
```powershell
Set-Location C:\dev\agent-emplois-ita\agent
.\scripts\test_v1_2_sources.ps1
```

## Backfill source par source
```powershell
Set-Location C:\dev\agent-emplois-ita\agent
.\scripts\backfill_v1_2_sources.ps1
```

Ou manuellement :
```powershell
.\.venv\Scripts\python.exe -m app.main_backfill_sources --source acta
.\.venv\Scripts\python.exe -m app.main_backfill_sources --source armeflhor
.\.venv\Scripts\python.exe -m app.main_backfill_sources --source astredhor
.\.venv\Scripts\python.exe -m app.main_backfill_sources --source ceva
.\.venv\Scripts\python.exe -m app.main_backfill_sources --source inov3pt
.\.venv\Scripts\python.exe -m app.main_backfill_sources --source cnpf
```

## Contrôle SQL après backfill
```sql
select
  s.slug,
  count(*) filter (where o.is_active = true) as active_offers,
  count(*) filter (where o.is_active = false) as archived_offers
from sources s
left join offers o on o.source_id = s.id
where s.slug in ('acta','armeflhor','astredhor','ceva','inov3pt','cnpf')
group by s.slug
order by s.slug;
```

## Git – création de la V1.2
```powershell
Set-Location C:\dev\agent-emplois-ita
git fetch --all --prune
git switch -c v1.2
git status
```

Ajout des fichiers :
```powershell
git add agent/app/connectors/acta.py
git add agent/app/connectors/armeflhor.py
git add agent/app/connectors/astredhor.py
git add agent/app/connectors/ceva.py
git add agent/app/connectors/inov3pt.py
git add agent/app/connectors/cnpf.py
git add agent/scripts/test_v1_2_sources.ps1
git add agent/scripts/backfill_v1_2_sources.ps1
git add SQL_V1_2_ADD_SOURCES.sql
git add PATCH_REGISTRY_SNIPPET_V1_2.txt
git add PATCH_WORKFLOW_SCHEDULE_V1_2.yml.snippet
git add PATCH_README_V1_2.md
```

Commit/push :
```powershell
git commit -m "V1.2 add 6 sources: ACTA, ARMEFLHOR, ASTREDHOR, CEVA, inov3PT, CNPF"
git push -u origin v1.2
```

## Mise en prod
Après validation :
```powershell
git switch main
git pull origin main
git merge --no-ff v1.2
git push origin main
```

## Workflow quotidien
GitHub Actions supporte désormais un `timezone`.
Le bloc recommandé est dans `PATCH_WORKFLOW_SCHEDULE_V1_2.yml.snippet` :

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '1 0 * * *'
      timezone: 'Europe/Paris'
```

Cela exécute la moisson chaque nuit à **00:01 heure de Paris**, sans dérive DST.
