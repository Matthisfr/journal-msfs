# Le Journal MSFS — édition web

Site public destiné à remplacer le journal PDF : [Météo](public/status.json), inventaire de scènes, nouveautés MSFS et matériel Airbus.

## Mise en ligne gratuite

1. Ouvrir **Settings → Pages** sur ce dépôt.
2. Dans **Build and deployment → Source**, sélectionner **GitHub Actions**.
3. Déclencher **Actions → Journal MSFS - actualisation et publication → Run workflow**, ou faire un nouveau commit.
4. Après un déploiement réussi, le site sera accessible à https://matthisfr.github.io/journal-msfs/

## Contenu et fiabilité

- 171 scènes provenant de l'inventaire transmis, 158 codes distincts. Les versions installées sont conservées.
- Les versions serveur non confirmées sont signalées UNKNOWN ; aucune version n'est inventée.
- Le TOP 10 météo est calculé à partir des METAR récents de NOAA Aviation Weather Center ; TAF associés.
- Les annonces officielles MSFS sont collectées depuis le flux RSS du forum officiel.
- Collecte automatique nocturne par GitHub Actions vers 04:17 UTC (05:17 heure d'hiver, 06:17 heure d'été en France), plus actualisation à chaque modification du dépôt.
- Le fichier `public/editorial.json` accueille les analyses éditoriales et les nouveautés matérielles.

**Limite importante :** cette automatisation gratuite ne lance pas ChatGPT en tâche de fond et ne vérifie pas encore les versions serveur de toutes les scènes. Les articles approfondis Fenix, SayIntentions, MobiFlight, GSX, WINCTRL, etc., nécessitent une rédaction/actualisation éditoriale distincte.

## Tests

`python -m unittest discover -s tests -v`

## Confidentialité

Le dépôt et le site sont publics. Ne pas y placer de secrets, de clés API, ni de données personnelles.
