# Patch V1.2 mis à jour

## Ce patch met à jour
- le script SQL pour coller à votre schéma `public.sources`
- le fichier `agent/app/connectors/registry.py` complet, aligné avec votre repo
- le workflow `.github/workflows/daily.yml` pour une exécution **une fois par jour à 00:01 Europe/Paris**
- les 6 connecteurs déjà fournis dans le patch V1.2 initial
- les scripts PowerShell de test et de backfill

## Fichiers à copier
- `agent/app/connectors/acta.py`
- `agent/app/connectors/armeflhor.py`
- `agent/app/connectors/astredhor.py`
- `agent/app/connectors/ceva.py`
- `agent/app/connectors/inov3pt.py`
- `agent/app/connectors/cnpf.py`
- `agent/app/connectors/registry.py`
- `.github/workflows/daily.yml`
- `SQL_V1_2_ADD_SOURCES.sql`
- `agent/scripts/test_v1_2_sources.ps1`
- `agent/scripts/backfill_v1_2_sources.ps1`
- `PATCH_MANUAL_WORKFLOW_NOTE.txt`

## Important
Votre repo contient déjà `.github/workflows/manual.yml`.
Si votre webapp déclenche un workflow GitHub manuellement, la bonne variable est :

```text
GITHUB_WORKFLOW_FILE=manual.yml
```

## Procédure git
À la racine du repo :

```powershell
Set-Location C:\devgent-emplois-ita

git fetch --all --prune
git switch -c v1.2
```

Copiez ensuite les fichiers du zip dans le repo en respectant l'arborescence.

Puis :

```powershell
git add agent/app/connectors/acta.py
git add agent/app/connectors/armeflhor.py
git add agent/app/connectors/astredhor.py
git add agent/app/connectors/ceva.py
git add agent/app/connectors/inov3pt.py
git add agent/app/connectors/cnpf.py
git add agent/app/connectors/registry.py
git add .github/workflows/daily.yml
git add agent/scripts/test_v1_2_sources.ps1
git add agent/scripts/backfill_v1_2_sources.ps1
git add SQL_V1_2_ADD_SOURCES.sql
git add PATCH_MANUAL_WORKFLOW_NOTE.txt
git add PATCH_README_V1_2_UPDATED.md

git commit -m "V1.2 add 6 sources, update registry, align SQL schema and daily workflow"
git push -u origin v1.2
```

## SQL
Exécutez `SQL_V1_2_ADD_SOURCES.sql` dans Supabase avant le backfill.

## Test local
```powershell
Set-Location C:\devgent-emplois-itagent
.\scripts	est_v1_2_sources.ps1
```

## Backfill source par source
```powershell
Set-Location C:\devgent-emplois-itagent
.\scriptsackfill_v1_2_sources.ps1
```

## Contrôle SQL après backfill
```sql
select
  s.slug,
  count(*) filter (where o.is_active = true) as active_offers,
  count(*) filter (where o.is_active = false) as archived_offers
from public.sources s
left join public.offers o on o.source_id = s.id
where s.slug in ('acta','armeflhor','astredhor','ceva','inov3pt','cnpf')
group by s.slug
order by s.slug;
```
