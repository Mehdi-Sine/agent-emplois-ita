# Patch correctif V1.2.1

Sources corrigées :
- ACTA
- ARMEFLHOR
- CEVA
- inov3PT
- CNPF

## Objectif
Corriger la qualité de collecte observée après V1.2 :
- ACTA : ville/location mal mappées sur Welcome to the Jungle
- ARMEFLHOR : city tronquée (`Saint` au lieu de `Saint-Pierre`), titres génériques et bruit métier
- CEVA : aucune offre collectée malgré une offre visible sur la page recrutement
- inov3PT : lignes génériques `Offre de stage` / `Stages` remontées à tort, offres pourvues non archivées
- CNPF : meilleure gestion des villes multiples (`Orléans ou Paris`)

## Fichiers à écraser
- agent/app/connectors/acta.py
- agent/app/connectors/armeflhor.py
- agent/app/connectors/ceva.py
- agent/app/connectors/inov3pt.py
- agent/app/connectors/cnpf.py

## Ordre recommandé
1. Copier-coller les fichiers Python
2. Lancer le test unitaire source par source
3. Prévisualiser le nettoyage SQL
4. Supprimer les anciennes lignes des sources corrigées
5. Relancer le backfill ciblé
6. Vérifier en base
7. Commit / push
