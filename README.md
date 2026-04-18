# ITA Jobs V1

Monorepo V1 pour :

- un agent Python de moisson des offres des ITA
- une base Supabase pour la persistance, l'historique et le monitoring
- une webapp Next.js responsive pour desktop et mobile

## Contenu

- `agent/` : collecte, normalisation, persistance, archivage, monitoring
- `supabase/` : migration SQL V1
- `webapp/` : interface de consultation et monitoring

## Principe

Deux moissons quotidiennes prévues via GitHub Actions :

- 00h01 Europe/Paris
- 12h01 Europe/Paris

Le workflow est protégé par un garde-fou horaire dans le script Python pour gérer correctement les décalages CET/CEST.

## V1 incluse

La V1 contient 7 connecteurs activables et faciles à étendre :

- ARVALIS
- CTIFL
- Idele
- IFIP
- ITEIPMAI
- ITAVI
- Terres Inovia

## Variables d'environnement principales

### Agent

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `JOBS_ARCHIVE_MISSED_THRESHOLD` facultatif, défaut `2`
- `USER_AGENT` facultatif

### Webapp

- `NEXT_PUBLIC_APP_NAME`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

## Déploiement conseillé

1. créer le projet Supabase
2. appliquer `supabase/migrations/001_init.sql`
3. créer le repo GitHub pour l'agent
4. configurer les secrets GitHub
5. déployer `webapp/` sur Vercel avec les variables d'environnement

## Important

Les sélecteurs HTML fournis sont une base V1 crédible et modulaire, mais certains sites peuvent nécessiter un ajustement fin après les premiers tests réels. Le socle applicatif, la persistance, l'archivage et la webapp sont complets.
