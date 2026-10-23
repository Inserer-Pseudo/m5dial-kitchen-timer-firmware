# Clé publique de signature

`signing_pubkey.pem` est la **clé publique** RSA-3072 (Secure Boot v2) qui vérifie les applications
publiées dans ce dépôt. Elle est ajoutée lors de la mise en place
([MAINTAINERS.md](../MAINTAINERS.md), étape 1), extraite de la clé privée par :

```sh
espsecure extract-public-key --version 2 --keyfile <clé privée> keys/signing_pubkey.pem
```

Elle sert à trois choses :

- le workflow de publication vérifie chaque image juste après l'avoir signée, de nouveau avant de créer
  la release, puis avant de déployer l'installateur web, et refuse de publier si la signature ne
  correspond pas à cette clé ;
- chacun peut vérifier un binaire téléchargé
  ([README](../README.md#vérifier-un-binaire)) :
  `espsecure verify-signature --version 2 --keyfile keys/signing_pubkey.pem <fichier.bin>` ;
- dans le dépôt privé, `tools/release/sign_local.ps1` contrôle qu'une signature locale a été faite avec
  la bonne clé, et `tools/flash.ps1 -Release` refuse de flasher une image que cette clé ne vérifie pas
  (sauf `-AllowForeignKey`, réservé aux répétitions avec une clé jetable).

La **clé privée** correspondante n'est jamais dans un dépôt : elle est sur le PC du mainteneur (avec une
sauvegarde hors ligne) et dans le secret `SIGNING_KEY_PEM` de l'environment protégé `release`.

Changer ce fichier revient à changer de clé : les Dial déjà installés n'accepteront plus les mises à
jour Wi-Fi et devront être réinstallés par USB (voir « Perte ou fuite de la clé » dans MAINTAINERS.md).
