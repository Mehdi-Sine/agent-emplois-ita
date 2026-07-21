# Webapp ITA Jobs

Application Next.js App Router, responsive desktop/mobile.

## Variables d'environnement

```bash
NEXT_PUBLIC_APP_NAME=ITA Jobs
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
ADMIN_PASSWORD=DirectionACTA2026
```

### Mot de passe Administration

La page `/administration` protège l'accès à `/monitoring` avec un mot de passe simple. En production Vercel, définissez `ADMIN_PASSWORD` dans les variables d'environnement du projet pour éviter de modifier le code à chaque changement de mot de passe.

Si `ADMIN_PASSWORD` n'est pas défini, l'application utilise la valeur de secours présente dans `webapp/lib/admin-auth.ts` : `DirectionACTA2026`.

Sur Vercel :

1. ouvrez le projet Vercel ;
2. allez dans **Settings → Environment Variables** ;
3. ajoutez `ADMIN_PASSWORD` avec le mot de passe souhaité ;
4. cochez les environnements à cibler, généralement **Production**, **Preview** et **Development** selon le besoin ;
5. redéployez l'application pour appliquer la nouvelle valeur.

## Lancer localement

```bash
npm install
npm run dev
```
