# Maintenance du dépôt public

Ce dépôt (`Inserer-Pseudo/m5dial-kitchen-timer-firmware`) publie les binaires signés du Minuteur M5Dial.
Son contenu est versionné dans le dépôt privé `Inserer-Pseudo/m5dial-kitchen-timer`, dossier
`public_repo/` ; les modifications passent par une pull request ici (ruleset de `main`).

Principes (ADR-13 et ADR-14 du dépôt privé) :

- **ce qui est signé vient de `main`** : un tag `v*` du dépôt privé ne fait que déclencher
  `publish.yml` ici. Le job `build` de ce dépôt résout le tag en commit, refuse un commit absent de la
  branche `main` privée, compile à ce SHA dans l'image ESP-IDF épinglée par digest, sans cache, et
  publie l'empreinte SHA-256 du binaire dans son résumé ;
- **build et signature séparés** : le job `sign` ne s'exécute qu'après validation manuelle (environment
  `release`), n'exécute aucun code du dépôt privé ni aucun script de dépôt (espsecure épinglé et shell
  seulement) et ne signe que le binaire dont l'empreinte a été affichée ;
- **moindre privilège** : chaque jeton n'a que le droit nécessaire et ne vit que dans le job qui s'en
  sert ; la clé privée n'existe qu'à deux endroits, le PC de Benjamin (plus une sauvegarde hors ligne)
  et le secret de l'environment `release` ;
- **tout est épinglé** : actions par SHA de commit, image de build par digest, esptool et ses
  dépendances par version et empreinte, ESP Web Tools vendorisé avec ses SHA-256, outils de manifeste
  copiés dans [`tools/`](tools/) (revus ici par pull request, jamais téléchargés du dépôt privé).

Ce qui est public, comme tout ce que produisent les workflows d'un dépôt public :

- le **journal du build** : la sortie normale d'`idf.py` (noms de fichiers, aucun extrait de source : le
  firmware compile avec `-Werror`, un commit taggé n'affiche donc aucun avertissement) ;
- le **résumé** du job `build` : tag, SHA et titre du commit, version, taille et empreinte du binaire ;
- les **artefacts** : binaires uniquement (application non signée puis signée, bootloader, table de
  partitions, `ota_data_initial`, `flasher_args.json`, notes de version). Jamais l'ELF, la map ni une
  source.

Les builds tournent ici : un dépôt public ne consomme aucune minute Actions, et la CI privée ne
dépense plus qu'environ une minute par tag (le déclenchement).

## Mise en place (une seule fois)

Prérequis : `gh` connecté au compte `Inserer-Pseudo` (`gh auth status`), une PowerShell ESP-IDF v6.1
(pour `espsecure`) et Git Bash. Les étapes sont dans l'ordre où elles dépendent les unes des autres :
dépôt, environments, réglages Actions, push initial, Pages, ruleset, secrets. Les commandes en Git Bash
utilisent :

```sh
repo=repos/Inserer-Pseudo/m5dial-kitchen-timer-firmware
```

### 1. Générer la clé de signature (sur le PC, jamais dans un dépôt)

Dans une PowerShell ESP-IDF, vers un emplacement **hors de tout dépôt Git** (support chiffré) :

```powershell
espsecure generate-signing-key --version 2 --scheme rsa3072 D:\cles\m5dial_signing_key.pem
```

- **Sauvegarde hors ligne immédiate**, en deux exemplaires : pièce jointe dans le gestionnaire de mots
  de passe, et clé USB rangée à part. Sans sauvegarde, une perte de clé coûte une réinstallation USB de
  chaque Dial (voir [Perte ou fuite de la clé](#perte-ou-fuite-de-la-clé)).
- Ne jamais la copier dans le chat, un ticket, un e-mail ou un dépôt. `pre-commit` (hook
  `detect-private-key`) et le `.gitignore` du dépôt privé (`*.pem`) sont des filets, pas une permission.

Extraire la clé publique, qui, elle, est publiée :

```powershell
espsecure extract-public-key --version 2 --keyfile D:\cles\m5dial_signing_key.pem public_repo\keys\signing_pubkey.pem
```

(commande lancée à la racine du dépôt privé ; committer `public_repo/keys/signing_pubkey.pem` sur `main`
avant le push initial de l'étape 5).

### 2. Créer le dépôt public (vide)

```powershell
gh repo create Inserer-Pseudo/m5dial-kitchen-timer-firmware --public `
  --description "Firmware signé du Minuteur M5Dial (M5Stack Dial) et installateur web" --disable-wiki
```

### 3. Environments `source` et `release`

Deux environments, pour qu'aucun job ne détienne à la fois l'accès au code privé et la clé ; chacun
recevra un seul secret à l'étape 8 :

| Environment | Job | Validation | Branches | Secret (et rien d'autre) |
|---|---|---|---|---|
| `source` | `build` | aucune | `main` seule | `SOURCE_READ_TOKEN` |
| `release` | `sign` | **Benjamin** (*required reviewer*) | `main` seule | `SIGNING_KEY_PEM` |

Settings › Environments › **New environment** :

- **`source`** : *Deployment branches and tags* › *Selected branches and tags*, règle de branche
  **`main`** seule ; pas de *required reviewers* (le build ne fait que lire et compiler).
- **`release`** : *Required reviewers* `Inserer-Pseudo` (*Prevent self-review* décoché : Benjamin est
  seul), *Allow administrators to bypass configured protection rules* **décoché**, *Deployment branches
  and tags* › règle de branche **`main`** seule.

Équivalent (Git Bash) :

```sh
uid=$(gh api users/Inserer-Pseudo --jq .id)
gh api --method PUT $repo/environments/source --input - <<EOF
{"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}
EOF
gh api --method PUT $repo/environments/release --input - <<EOF
{"reviewers":[{"type":"User","id":$uid}], "prevent_self_review":false, "can_admins_bypass":false,
 "deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}
EOF
for env in source release; do
  gh api --method POST $repo/environments/$env/deployment-branch-policies -f name=main -f type=branch
done
```

### 4. Réglages Actions

Settings › Actions › General :

- *Actions permissions* : **Allow select actions** › seulement **les actions créées par GitHub**
  (`actions/*`), sans les *verified creators* : toute autre action est refusée à l'exécution ; et
  **Require actions to be pinned to a full-length commit SHA**. `publish.yml` n'utilise que des actions
  `actions/*` épinglées par SHA (celles qu'elles appellent elles-mêmes aussi).
- *Workflow permissions* : **Read repository contents and packages permissions**, sans autoriser
  GitHub Actions à approuver des pull requests. Chaque job de `publish.yml` demande lui-même les droits
  dont il a besoin (`permissions: {}` par défaut).
- *Approval for running fork pull request workflows from contributors* : **Require approval for all
  external contributors**.

Équivalent :

```sh
gh api --method PUT $repo/actions/permissions -F enabled=true -f allowed_actions=selected -F sha_pinning_required=true
gh api --method PUT $repo/actions/permissions/selected-actions -F github_owned_allowed=true -F verified_allowed=false
gh api --method PUT $repo/actions/permissions/workflow -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
gh api --method PUT $repo/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors
```

### 5. Push initial du contenu

Depuis la racine du dépôt privé, à jour sur `main` (clé publique comprise) :

```powershell
gh repo clone Inserer-Pseudo/m5dial-kitchen-timer-firmware $env:TEMP\fw-public
robocopy public_repo $env:TEMP\fw-public /E
git -C $env:TEMP\fw-public add -A
git -C $env:TEMP\fw-public commit -m "Contenu initial - installateur web, workflow de publication, clé publique"
git -C $env:TEMP\fw-public push origin main
```

C'est le seul push direct : il n'est possible que parce que le ruleset (étape 7) n'existe pas encore.
Ensuite, tout passe par une pull request.

### 6. Pages : source « GitHub Actions »

Settings › Pages › Build and deployment › Source : **GitHub Actions**. Équivalent :

```sh
gh api --method POST $repo/pages -f build_type=workflow
```

L'environment `github-pages` est créé à cette occasion ; il n'accepte que la branche par défaut.

### 7. Ruleset de `main`

Après le push initial, depuis la copie locale du dépôt public (le fichier est
[`.github/rulesets/main.json`](.github/rulesets/main.json)) :

```sh
gh api --method POST $repo/rulesets --input .github/rulesets/main.json
```

Effet : pull request obligatoire pour modifier `main` (aucune approbation exigée, Benjamin étant seul),
ni force-push ni suppression, **liste de contournement vide** (l'administrateur aussi passe par une PR).
Vérification : `gh api $repo/rulesets`.

### 8. Secrets : un par environment, plus le jeton de déclenchement

- **`SOURCE_READ_TOKEN`**, environment `source` : un PAT *fine-grained* (Settings du compte ›
  Developer settings › Fine-grained tokens › Generate new token) avec : *Resource owner*
  `Inserer-Pseudo`, *Repository access* **Only select repositories** › `m5dial-kitchen-timer` (le dépôt
  privé), *Permissions* › Repository › **Contents : Read-only** (Metadata : Read-only est ajouté
  d'office), rien d'autre, expiration ≤ 1 an. Il sert à résoudre le tag, à vérifier que le commit est
  sur `main` (API *compare*) et au checkout. La saisie reste masquée :

  ```sh
  gh secret set SOURCE_READ_TOKEN --env source --repo Inserer-Pseudo/m5dial-kitchen-timer-firmware
  ```

- **`SIGNING_KEY_PEM`**, environment `release` : le contenu du fichier de clé privée. Depuis Git Bash,
  sans que la clé passe par l'écran ni l'historique :

  ```sh
  gh secret set SIGNING_KEY_PEM --env release --repo Inserer-Pseudo/m5dial-kitchen-timer-firmware < /d/cles/m5dial_signing_key.pem
  ```

  Aucun autre secret dans `release` (en particulier pas `SOURCE_READ_TOKEN`), et aucun secret de dépôt
  dans ce dépôt public.

- **`FIRMWARE_DISPATCH_TOKEN`**, secret du **dépôt privé** : PAT *fine-grained*, *Repository access*
  **Only select repositories** › `m5dial-kitchen-timer-firmware`, *Permissions* › Repository ›
  **Actions : Read and write**, rien d'autre (pas de Contents : il ne peut ni pousser de code ni
  modifier les workflows), expiration ≤ 1 an.

  ```sh
  gh secret set FIRMWARE_DISPATCH_TOKEN --repo Inserer-Pseudo/m5dial-kitchen-timer
  ```

Vérification : `gh secret list --env source --repo …`, `gh secret list --env release --repo …` et
`gh secret list --repo Inserer-Pseudo/m5dial-kitchen-timer-firmware` (cette dernière doit être vide).

Noter les dates d'expiration des deux PAT : une publication échoue proprement (job `dispatch` du dépôt
privé, ou étape « Resolve the tag » du job `build` ici) quand l'un d'eux a expiré ; il suffit alors d'en
créer un nouveau et de mettre à jour le secret.

### 9. Répétition

Poser un tag `vX.Y.Z-rc.1` sur un commit de `main` du dépôt privé et dérouler la
[procédure de publication](#publier-une-version) jusqu'au bout : pré-version publique, pas de
déploiement Pages. Vérifier la signature d'après le [README](README.md#vérifier-un-binaire). Pour
vérifier le refus d'un commit hors de `main`, lancer aussi une fois *Run workflow* avec un tag posé sur
une branche : le job `build` doit échouer à « Resolve the tag ».

## Publier une version

1. **Dépôt privé**, sur `main` à jour : section `## [X.Y.Z] - AAAA-MM-JJ` dans `CHANGELOG.md` (ses notes
   deviennent celles de la version), CI de `main` au vert (automatique après la fusion de la PR). Les
   test apps des composants ne sont jamais requises : c'est un outil de développement, lancé à la main
   au besoin (case « test_apps »).
2. Tag annoté et push :

   ```sh
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```

3. `release.yml` (dépôt privé, quelques secondes) vérifie la forme du tag et déclenche `publish.yml`
   ici. Il ne compile rien.
4. **Ici**, job `build` (~15 min, sans validation) : il résout le tag en commit dans le dépôt privé (tag
   annoté déréférencé), **refuse un commit qui n'est pas un ancêtre de `main`**, fait le checkout à ce
   SHA, vérifie le CHANGELOG, compile la variante release dans l'image ESP-IDF épinglée, vérifie que la
   version compilée est exactement le tag (pas de `-dirty`), puis dépose l'artefact `unsigned`.
5. **Validation** : Actions › Publish › le run en attente. Avant *Review deployments*, lire le résumé
   du job `build` et vérifier :
   - le **tag** est celui que vous venez de pousser, et le run a été déclenché par le dépôt privé
     (ou par vous, pour un lancement manuel) ;
   - le **commit** est le bon : dans le dépôt privé, `git fetch --tags` puis
     `git rev-parse vX.Y.Z^{commit}` doit afficher le même SHA, et son **titre** doit être celui
     attendu (personne n'a poussé autre chose sur `main` entre-temps) ;
   - la **version compilée** est égale au tag ;
   - la **taille** est plausible (≤ 2,4 Mo, proche de celle du build release de la CI privée pour ce
     commit) ; noter l'**empreinte SHA-256**, que les jobs suivants contrôlent.

   Puis *Review deployments* › `release` › **Approve and deploy**. En cas de doute : *Reject*.
6. Job `sign` : il vérifie que l'artefact est bien celui mesuré par `build` (SHA-256), signe avec
   l'esptool épinglé, vérifie la signature avec `keys/signing_pubkey.pem` et dépose l'artefact `signed`.
7. Job `publish` : nouvelle vérification de la signature, et que l'image signée commence octet pour
   octet par l'image mesurée ; `tools/make_manifests.py` (copie de ce dépôt) génère `manifest.json`,
   `SHA256SUMS` et le manifeste de l'installateur ; publication de la release : **latest** pour
   `vX.Y.Z`, **pré-version** pour `vX.Y.Z-rc.N` (jamais proposée aux Dial, qui lisent
   `releases/latest`).
8. Pour un tag final, le job `pages` vérifie la signature de l'application de l'installateur et que son
   empreinte est celle de l'asset publié, puis déploie l'installateur web avec cette version.
9. Contrôles : assets de la release, `sha256sum -c SHA256SUMS`, `espsecure verify-signature`, version
   affichée par l'installateur, puis Réglages › Mises à jour › Rechercher sur un Dial connecté.

Cas particuliers :

- **Version minimale** (`min_version`) : pour exiger qu'un Dial soit déjà en vA.B.C avant d'installer
  cette version, rejeter le run déclenché automatiquement et lancer Actions › Publish › *Run workflow*
  avec `tag` et `min_version`.
- **Échec avant la création de la release** : relancer le job (*Re-run failed jobs*). Une release
  publique déjà créée n'est jamais écrasée : corriger, puis publier une version suivante.
- **Validation tardive** : l'artefact `unsigned` est gardé 14 jours. Au-delà, rejeter le run et en
  relancer un (Actions › Publish › *Run workflow*, même tag) : le build est refait au même commit.
- **Tag hors de `main`** (branche, commit jamais fusionné) : le job `build` échoue à l'étape « Resolve
  the tag », sans rien compiler ni signer. Fusionner d'abord, puis poser le tag sur `main`.
- **Signature locale** pour un essai sur un Dial (build release compilé sur le PC) :
  `tools/release/sign_local.ps1 -KeyFile D:\cles\m5dial_signing_key.pem -In build-release\m5dial_kitchen_timer.bin -Out build-release\m5dial_kitchen_timer-signed.bin`
  (dépôt privé ; le script vérifie aussi la signature avec la clé publique de ce dépôt), puis
  `tools/flash.ps1 -Port COMx -Release -AppImage build-release\m5dial_kitchen_timer-signed.bin`, qui
  refuse une image que `keys/signing_pubkey.pem` ne vérifie pas. Une clé jetable de répétition exige
  `-AllowForeignKey` : le Dial n'accepte alors plus que les mises à jour signées par cette clé, jusqu'à
  sa réinstallation par l'installateur web.

## Perte ou fuite de la clé

Sans Secure Boot ni eFuse (ADR-9), un Dial en release n'accepte une mise à jour que si elle est signée
par la clé dont la signature figure dans **l'image qu'il exécute**.

- **Clé perdue** (sans sauvegarde) : plus aucune mise à jour Wi-Fi ne sera acceptée par les Dial
  installés. Il faut générer une nouvelle clé (étape 1), remplacer `keys/signing_pubkey.pem` et
  `SIGNING_KEY_PEM`, publier une version, puis **réinstaller chaque Dial par USB** avec l'installateur
  web (sans effacement : réglages conservés). Les mises à jour Wi-Fi refonctionnent ensuite.
- **Clé divulguée** : un tiers pourrait signer une image acceptée par les Dial, mais il lui faudrait
  aussi la publier dans les releases de ce dépôt (le Dial ne télécharge qu'en HTTPS depuis
  `github.com/Inserer-Pseudo/m5dial-kitchen-timer-firmware/releases/download/`). Réagir quand même tout
  de suite : supprimer le secret `SIGNING_KEY_PEM`, révoquer les PAT, générer une nouvelle clé et
  réinstaller les Dial par USB comme ci-dessus. Il n'existe pas de révocation à distance : la rotation
  sans USB (double signature) est hors périmètre de cette version.
- **Expiration** : la clé RSA n'expire pas ; seuls les PAT expirent.

## Mettre à jour les dépendances épinglées

- **Image de build ESP-IDF** : la même version d'ESP-IDF que le dépôt privé (ADR-1 : v6.1). Lire le
  digest courant du tag, par exemple
  `curl -s https://hub.docker.com/v2/repositories/espressif/idf/tags/v6.1 | python -c "import json,sys; print(json.load(sys.stdin)['digest'])"`
  (ou `docker buildx imagetools inspect espressif/idf:v6.1`), remplacer `container:` et son commentaire
  (date, digest amd64) dans `.github/workflows/publish.yml`, puis faire une répétition `-rc`. Un digest
  ne change jamais de contenu : rien ne bouge tant qu'on ne le remplace pas.
- **Outils de manifeste** (`tools/make_manifests.py`, `tools/versions.py`) : modifiés et testés dans le
  dépôt privé (`tools/release/`), dont la CI vérifie que `public_repo/tools/` en est une copie exacte ;
  ils arrivent ici par la synchronisation habituelle de `public_repo/` (pull request).
- **Actions** : pour chaque action, prendre une version publiée depuis au moins deux semaines, puis
  `gh api repos/<propriétaire>/<action>/git/ref/tags/<tag>` (si `object.type` vaut `tag`, suivre
  `gh api repos/<propriétaire>/<action>/git/tags/<sha>`) et remplacer le SHA et le commentaire
  `# vX.Y.Z`. Dependabot (`.github/dependabot.yml`) propose ces mises à jour chaque mois.
- **esptool** : garder la version installée par l'ESP-IDF utilisé (`python -m pip show esptool` dans
  une PowerShell ESP-IDF). Régénérer `.github/requirements/esptool.txt` et `build.txt` avec toutes
  les empreintes (par exemple `pip-compile --generate-hashes` de pip-tools sous Python 3.12 Linux),
  puis lancer une répétition `-rc`.
- **ESP Web Tools** : `npm view esp-web-tools version`, `npm pack esp-web-tools@<version>`, copier
  `package/dist/web/*.js` et `package/LICENSE` dans `site/vendor/esp-web-tools/<version>/`, y écrire
  `SHA256SUMS` (`sha256sum LICENSE *.js > SHA256SUMS`), mettre à jour le chemin du script dans
  `site/index.html` et la ligne correspondante de `THIRD_PARTY_NOTICES.md` (version et intégrité npm),
  supprimer l'ancien dossier. Vérifier dans les sources de la nouvelle version que
  `new_install_prompt_erase`, `new_install_improv_wait_time` et la famille `ESP32-S3` existent toujours.
