# Patch V1.1 – Monitoring + déclenchement manuel des runs

Ce patch fait trois choses :

1. **corrige la page Monitoring** pour lire les **comptes live** depuis `offers` au lieu de se reposer uniquement sur `v_source_latest_status` ;
2. ajoute un bouton **"Lancer un run"** pour déclencher une moisson globale via **GitHub Actions** ;
3. ajoute un bouton **"Mettre à jour"** dans chaque carte ITA pour déclencher une moisson ciblée sur une seule source.

## Fichiers inclus

- `.github/workflows/manual-collect.yml`
- `webapp/app/monitoring/page.tsx`
- `webapp/app/api/collect/route.ts`
- `webapp/app/api/collect/[slug]/route.ts`
- `webapp/components/RunTriggerButton.tsx`
- `webapp/lib/supabase-admin.ts`
- `webapp/lib/monitoring-data.ts`
- `webapp/lib/github-dispatch.ts`

## Hypothèses

- le repo contient bien un dossier `agent/` et un dossier `webapp/`
- le front est un **Next.js 15 App Router**
- la page monitoring est dans `webapp/app/monitoring/page.tsx`
- les dépendances `@supabase/supabase-js` sont déjà présentes
- les secrets GitHub Actions `SUPABASE_URL` et `SUPABASE_SERVICE_KEY` existent déjà
- Vercel a accès à des variables d'environnement serveur

## Variables à ajouter sur Vercel

Ajoutez **dans le projet Vercel** :

- `GITHUB_TOKEN` = token GitHub avec droit `Actions: Read and write` + accès au repo
- `GITHUB_OWNER` = propriétaire du repo
- `GITHUB_REPO` = nom du repo
- `GITHUB_REF` = `main` (ou votre branche de prod)
- `GITHUB_WORKFLOW_FILE` = `manual-collect.yml`

Les variables suivantes doivent déjà exister côté webapp :

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

## Ce que corrige ce patch

Le doc projet indique que :

- `v_active_offers` alimente l’accueil ;
- `v_source_latest_status` est une vue de monitoring basée sur le **dernier `source_run` connu** ;
- la webapp s’appuie sur les **vues et tables Supabase**.

Le symptôme vu dans l’UI venait probablement du fait que la carte Monitoring affichait des métriques issues du **dernier `source_run`**, mais pas le **nombre courant d’offres actives** en base.  
Le nouveau code recalcule donc les compteurs "Offres" et "Archivées" directement depuis `offers`, source par source.

## Important

Le bouton **"Lancer un run"** et les boutons **"Mettre à jour"** déclenchent un **workflow GitHub Actions asynchrone**.  
L’UI confirme le dispatch immédiat, mais les données visibles se mettront à jour une fois le workflow terminé.

## Si votre page d’accueil reste cachée

Le même problème de cache peut exister ailleurs.  
Le nouveau `app/monitoring/page.tsx` force le rendu dynamique avec :

```ts
export const dynamic = "force-dynamic";
export const revalidate = 0;
```

Si vous observez le même comportement sur `app/page.tsx` ou `app/archives/page.tsx`, appliquez la même règle.
