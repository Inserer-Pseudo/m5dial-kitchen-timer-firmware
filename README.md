# Minuteur M5Dial — firmware

Firmware officiel du **Minuteur M5Dial**, un minuteur de cuisine multi-minuteurs pour le
[M5Stack Dial](https://docs.m5stack.com/en/core/M5Dial) (ESP32-S3, écran rond 240 × 240, molette,
écran tactile) : jusqu'à quatre minuteurs en parallèle, préréglages (thé, œufs, pâtes, riz…), alarme
sonore et vibrante, veille et extinction automatiques sur batterie.

Ce dépôt ne contient que les **binaires publiés**, leurs manifestes, l'installateur web et le workflow
qui les produit. Le code source est privé ; chaque version publiée ici est **compilée par le workflow
de ce dépôt** (journal visible dans l'onglet Actions), au commit du tag, qui doit appartenir à la
branche principale du code source, puis **signée** après une validation manuelle.

## Installer

**Installateur web : <https://inserer-pseudo.github.io/m5dial-kitchen-timer-firmware/>**

1. Un ordinateur avec **Google Chrome** ou **Microsoft Edge** (Web Serial ; pas de téléphone, ni Firefox,
   ni Safari).
2. Un câble USB-C **de données**.
3. **Allumez l'écran du Dial, puis branchez-le** : en veille, son port USB n'apparaît pas.
4. Cliquez sur **Installer** et choisissez le port (« USB JTAG/serial debug unit »).
5. Laissez la case **« Erase device »** décochée pour conserver réglages, Wi-Fi et minuteurs ; cochez-la
   seulement pour revenir à l'état d'usine.

L'installateur écrit le bootloader, la table de partitions, l'état OTA et l'application signée, chacun
à son adresse : la zone de réglages (NVS) n'est jamais touchée sans effacement explicite.

## Mises à jour par Wi-Fi

Une fois le Wi-Fi configuré sur le Dial (Réglages › Wi-Fi, avec l'application « ESP BLE Provisioning »),
les mises à jour arrivent par Internet :

- le Dial lit le manifeste de la dernière version stable,
  `https://github.com/Inserer-Pseudo/m5dial-kitchen-timer-firmware/releases/latest/download/manifest.json` ;
- la vérification automatique a lieu au plus une fois par jour, seulement quand l'écran est allumé et
  inutilisé depuis quelques secondes ; elle se désactive dans Réglages › Mises à jour ;
- avant tout téléchargement, le Dial contrôle le manifeste : projet et application, adresse HTTPS de ce
  dépôt, taille, version plus récente que la sienne, version minimale requise, version déjà refusée ;
- l'installation demande toujours une confirmation et n'a jamais lieu pendant une alarme ; le
  redémarrage attend qu'aucun minuteur ne tombe dans les 15 secondes, et les minuteurs en cours sont
  conservés ;
- **une image qui n'est pas signée avec la clé du projet est refusée** ; si la nouvelle version ne
  démarre pas correctement, le Dial revient automatiquement à la précédente.

Les versions candidates (`vX.Y.Z-rc.N`) sont publiées en pré-version : elles ne sont jamais proposées
automatiquement aux appareils.

## Vérifier un binaire

Chaque version contient :

| Fichier | Rôle |
|---|---|
| `m5dial-kitchen-timer-timer-vX.Y.Z.bin` | application signée (installée par l'installateur web et par la mise à jour Wi-Fi) |
| `bootloader.bin`, `partition-table.bin`, `ota_data_initial.bin` | parties écrites par l'installateur web |
| `manifest.json` | manifeste lu par le Dial (version, adresse, taille, SHA-256) |
| `SHA256SUMS` | empreintes SHA-256 de tous les fichiers ci-dessus |

1. **Intégrité** : dans le dossier où vous avez téléchargé les fichiers,

   ```sh
   sha256sum -c --ignore-missing SHA256SUMS
   ```

   Sous Windows (PowerShell) : `Get-FileHash -Algorithm SHA256 <fichier>`, à comparer à la ligne
   correspondante de `SHA256SUMS`.

2. **Authenticité** : la signature (Secure Boot v2, RSA-3072) se vérifie avec la clé publique de ce
   dépôt, [`keys/signing_pubkey.pem`](keys/signing_pubkey.pem), et `espsecure` (fourni avec
   [esptool](https://github.com/espressif/esptool), `pip install esptool`) :

   ```sh
   espsecure verify-signature --version 2 --keyfile keys/signing_pubkey.pem m5dial-kitchen-timer-timer-vX.Y.Z.bin
   ```

   La sortie doit indiquer `Signature block 0 verification successful using the supplied key (RSA)`.

Seule l'application est signée : le bootloader et la table de partitions sont les fichiers standard
produits par ESP-IDF pour ce projet, et leurs empreintes figurent dans `SHA256SUMS`.

## Licence

Le firmware est distribué sous une **licence binaire propriétaire** : téléchargement et installation
gratuits sur vos propres M5Stack Dial pour un usage personnel, sans redistribution ni modification
(voir [`LICENSE`](LICENSE)). Les composants tiers qu'il contient restent sous leurs licences libres :
voir [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) et le dossier [`LICENSES/`](LICENSES/).

M5Stack et M5Dial sont des marques de M5Stack Technology Co., Ltd. Ce projet n'est ni affilié à
M5Stack ni approuvé par cette société.

## Maintenance

La configuration du dépôt, la procédure de publication et la gestion de la clé de signature sont
décrites dans [`MAINTAINERS.md`](MAINTAINERS.md).
