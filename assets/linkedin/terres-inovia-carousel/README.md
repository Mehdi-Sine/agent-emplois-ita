# Carrousel LinkedIn — Terres Inovia — 3 offres récentes

Ce dossier contient un carrousel PDF carré prêt à publier sur LinkedIn :

- `terres-inovia-3-offres-linkedin-2026-06-10.pdf` : PDF final en 4 pages carrées, dont une couverture et une page par offre.
- `generate_carousel.py` : générateur Python autonome, sans dépendance externe, permettant de reconstruire le PDF et de vérifier l’encodage CP1252 / WinAnsi des textes accentués.

## Offres mises en avant

Les offres retenues correspondent aux trois dernières offres visibles sur la page officielle des carrières Terres Inovia consultée le 10 juin 2026 :

1. **Ingénieur·e de développement “lutte ravageurs” — Châlons-en-Champagne (51)**, CDD 16 mois, publié le 26 mai 2026.
2. **Ingénieur·e de développement “lutte ravageurs” — Le Subdray (18)**, CDD 16 mois, publié le 26 mai 2026.
3. **Stage M1 / césure — nectar extrafloral de la féverole**, stage 4 mois, publié le 21 mai 2026 et mis à jour le 29 mai 2026.

## Direction artistique

Le carrousel reprend une palette inspirée des codes visuels Terres Inovia : verts agricoles, accent jaune tournesol / oléagineux, orange chaleureux, fonds crème et typographie sans-serif très lisible. Chaque offre dispose d'une illustration vectorielle adaptée : ravageurs et parcelles expérimentales, réseau d'essais terrain, féverole et laboratoire.

## Encodage des textes

Le générateur encode les textes du PDF sous forme de chaînes hexadécimales CP1252 / WinAnsi afin de conserver les caractères latins accentués et la ponctuation française (`é`, `â`, `€`, `•`, `–`, guillemets typographiques). Une validation intégrée échoue si les libellés accentués clés ne sont pas présents dans le PDF généré.

## Régénération

Depuis la racine du dépôt :

```bash
python assets/linkedin/terres-inovia-carousel/generate_carousel.py
```
