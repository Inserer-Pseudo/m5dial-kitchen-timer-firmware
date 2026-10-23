# Composants tiers

Le firmware du Minuteur M5Dial et l'installateur web de ce dépôt contiennent des logiciels publiés par
des tiers sous licence libre. Ils restent soumis à leur propre licence, dont le texte complet se trouve
dans le dossier [`LICENSES/`](LICENSES/). La licence du firmware ([`LICENSE`](LICENSE)) ne restreint
aucun des droits que ces licences vous donnent sur ces composants.

## Dans le firmware (images `.bin`)

| Composant | Version | Licence | Texte |
|---|---|---|---|
| [ESP-IDF](https://github.com/espressif/esp-idf) (Espressif Systems) | 6.1.0 | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| ↳ [FreeRTOS Kernel](https://www.freertos.org/) (Amazon.com, Inc. et ses affiliés) | V10.5.1 | MIT | [MIT-FreeRTOS.txt](LICENSES/MIT-FreeRTOS.txt) |
| ↳ [lwIP](https://savannah.nongnu.org/projects/lwip/) (Swedish Institute of Computer Science) | 2.2.0 | BSD-3-Clause | [BSD-3-Clause-lwIP.txt](LICENSES/BSD-3-Clause-lwIP.txt) |
| ↳ [Mbed TLS](https://github.com/Mbed-TLS/mbedtls) et TF-PSA-Crypto (Arm Limited, contributeurs) | 4.1.0 / 1.1.0 | Apache-2.0 (double licence Apache-2.0 OU GPL-2.0-or-later, utilisée sous Apache-2.0) | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| ↳ [Apache Mynewt NimBLE](https://github.com/apache/mynewt-nimble) (Apache Software Foundation, modifications Espressif) | IDF 6.1 | Apache-2.0, avec avis | [Apache-2.0.txt](LICENSES/Apache-2.0.txt), [NOTICE-NimBLE.txt](LICENSES/NOTICE-NimBLE.txt) |
| ↳ [protobuf-c](https://github.com/protobuf-c/protobuf-c) (Dave Benson et les auteurs de protobuf-c) | IDF 6.1 | BSD-2-Clause | [BSD-2-Clause-protobuf-c.txt](LICENSES/BSD-2-Clause-protobuf-c.txt) |
| ↳ [wpa_supplicant](https://w1.fi/wpa_supplicant/) (Jouni Malinen et contributeurs) | IDF 6.1 | BSD-3-Clause | [BSD-3-Clause-wpa_supplicant.txt](LICENSES/BSD-3-Clause-wpa_supplicant.txt) |
| ↳ Allocateur [TLSF](https://github.com/espressif/tlsf) (Matthew Conte) | IDF 6.1 | BSD-3-Clause | [BSD-3-Clause-TLSF.txt](LICENSES/BSD-3-Clause-TLSF.txt) |
| ↳ Bibliothèque C [picolibc](https://github.com/picolibc/picolibc) (dérivée de newlib) | IDF 6.1 | licences de type BSD, détaillées | [picolibc-COPYING.txt](LICENSES/picolibc-COPYING.txt), [newlib-COPYING.txt](LICENSES/newlib-COPYING.txt) |
| [LVGL](https://lvgl.io/) (LVGL Kft) | 9.5.0 | MIT | [MIT-LVGL.txt](LICENSES/MIT-LVGL.txt) |
| [esp_lvgl_port](https://components.espressif.com/components/espressif/esp_lvgl_port) (Espressif) | 2.9.0 | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| [esp_lcd_gc9a01](https://components.espressif.com/components/espressif/esp_lcd_gc9a01) (Espressif) | 2.0.4 | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| [esp_lcd_touch](https://components.espressif.com/components/espressif/esp_lcd_touch) (Espressif) | 1.2.1 | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| [esp_lcd_touch_ft5x06](https://components.espressif.com/components/espressif/esp_lcd_touch_ft5x06) (Espressif) | 1.1.1 | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| [network_provisioning](https://components.espressif.com/components/espressif/network_provisioning) (Espressif) | 1.4.0 | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| [json_generator](https://components.espressif.com/components/espressif/json_generator) (Espressif) | 2.1.0 | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| [jsmn](https://github.com/zserge/jsmn) (Serge Zaitsev) | 1.1.0 | MIT | [MIT-jsmn.txt](LICENSES/MIT-jsmn.txt) |
| Police [Inter](https://rsms.me/inter/) (The Inter Project Authors), sous-ensembles | 4.1 | SIL Open Font License 1.1 | [OFL-1.1-Inter.txt](LICENSES/OFL-1.1-Inter.txt) |
| Icônes [Material Symbols Rounded](https://github.com/google/material-design-icons) (Google), sous-ensemble | commit `49d4db35` | Apache-2.0 | [Apache-2.0-MaterialSymbols.txt](LICENSES/Apache-2.0-MaterialSymbols.txt) |

ESP-IDF contient d'autres composants tiers, dont seuls ceux effectivement liés au firmware sont
inclus dans l'image. Leur liste complète et leurs licences figurent dans la page
[Copyrights and Licenses](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/COPYRIGHT.html)
de la documentation ESP-IDF. Les bibliothèques binaires Wi-Fi, Bluetooth et PHY d'Espressif sont
distribuées avec ESP-IDF selon les conditions de ce dernier.

## Dans l'installateur web (site GitHub Pages)

| Composant | Version | Licence | Texte |
|---|---|---|---|
| [ESP Web Tools](https://github.com/esphome/esp-web-tools) (Open Home Foundation, ESPHome) | 10.4.0 | Apache-2.0 | [site/vendor/esp-web-tools/10.4.0/LICENSE](site/vendor/esp-web-tools/10.4.0/LICENSE) |
| ↳ [esptool-js](https://github.com/espressif/esptool-js) (Espressif), y compris ses stubs de flash | 0.6.x | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| ↳ [Improv Wi-Fi serial SDK](https://github.com/improv-wifi/sdk-serial-js) | 2.8.0 | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| ↳ [Material Web](https://github.com/material-components/material-web) (Google) | 2.x | Apache-2.0 | [Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| ↳ [Lit](https://lit.dev/) (Google LLC) | 3.x | BSD-3-Clause | [BSD-3-Clause-Lit.txt](LICENSES/BSD-3-Clause-Lit.txt) |
| ↳ [pako](https://github.com/nodeca/pako) (Vitaly Puzrin, Andrei Tuputcyn ; zlib : Jean-loup Gailly, Mark Adler) | 2.1.0 | MIT et Zlib | [MIT-pako.txt](LICENSES/MIT-pako.txt), [Zlib-pako.txt](LICENSES/Zlib-pako.txt) |
| ↳ [atob-lite](https://github.com/hughsk/atob-lite) (Hugh Kennedy) | 2.0.0 | MIT | [MIT-atob-lite.txt](LICENSES/MIT-atob-lite.txt) |
| ↳ [tslib](https://github.com/microsoft/tslib) (Microsoft Corporation) | 2.x | 0BSD | [0BSD-tslib.txt](LICENSES/0BSD-tslib.txt) |

ESP Web Tools est copié tel que publié sur npm (`dist/web` du paquet `esp-web-tools@10.4.0`,
intégrité npm `sha512-3pwkeFFm5Fj7UQo8SJNYK5RXrtNCpq6X9QoI6bMT4GBZWgrJqjn0YvM9ihG74BtMoSFYXfmDtkehuxe50PTMPQ==`).
Les empreintes de chaque fichier sont dans
[`site/vendor/esp-web-tools/10.4.0/SHA256SUMS`](site/vendor/esp-web-tools/10.4.0/SHA256SUMS). Les
composants marqués ↳ y sont intégrés par son outil d'assemblage ; leurs versions exactes sont celles
résolues par ce paquet.

## Outils de publication (non distribués)

Le workflow de publication installe [esptool](https://github.com/espressif/esptool) (GPL-2.0-or-later)
et ses dépendances pour signer les images ; ces outils ne sont inclus ni dans le firmware ni sur le site.
