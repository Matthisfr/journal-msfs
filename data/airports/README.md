# Mise à jour automatique des aéroports

Déposez **un seul fichier Excel .xlsx** dans ce dossier (`data/airports/`) via « Add file → Upload files » sur GitHub, puis validez le commit.

La publication GitHub Actions démarre automatiquement : import du classeur, contrôle des données, vérification des versions, reconstruction de la carte et des tableaux, puis publication du journal.

Colonnes reconnues (en-têtes, insensibles aux accents et à la casse) :
- `ICAO` (ou `Code ICAO`)
- `Folder` (ou `Dossier`) et/ou `Name` (ou `Nom`)
- `Installed` (ou `Version`, `Version installée`)
- Facultatives : `Publisher`/`Éditeur`, `Region`/`Région`

Chaque ligne représente **une scène**, y compris les scènes partageant le même ICAO. Les versions officielles sont contrôlées séparément. Les anciennes données de vérification sont conservées pour les scènes inchangées ; une version installée modifiée déclenche une nouvelle vérification.

**Important :** le classeur est la source de vérité de l'inventaire. Une scène absente du nouveau fichier disparaît de l'inventaire publié. Ne téléversez pas un export partiel. L'import refuse les lignes incomplètes et les doublons exacts. Si l'import échoue, le site existant reste publié et le workflow signale l'erreur.

Corrections automatiques : BCGB → LXGB, KABK → KABQ ; KLVB fictif exclu de la carte et de l'import. Les identifiants locaux comme 58CA sont acceptés, mais seuls les lieux dont les coordonnées sont vérifiées sont placés sur la carte.

**Remplacement :** supprimer l'ancien fichier Excel du dossier avant d'ajouter le nouveau (dans un même commit si possible). Un seul .xlsx est autorisé.
