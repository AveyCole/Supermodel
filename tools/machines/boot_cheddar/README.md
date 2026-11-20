# Cheddar Butt au démarrage de Supermodel 3.06

`cheddar-portrait.lcd` reprend le portrait de Cheddar Butt qui baille parmi les feuilles
de chêne. C'est le fichier OLED 128 × 64 `menu-parity656/redux-cat-splash.lcd` de
Supermodel Redux, repris pixel pour pixel avec sa polarité d'origine.

La tâche de démarrage native est à `0x40053a6c`. Son remplaçant tient dans le
même emplacement de 1 032 octets et conserve le minuteur de 20 ms, les 90 ticks
et le sémaphore de fin. Les 32 premières images dévoilent le portrait quatre
colonnes à la fois. Le portrait reste affiché jusqu'à la fin de la tâche.

Le flasheur applique ce remplacement à l'image 3.06 vérifiée, après le choix
de l'édition et des machines. La case est cochée par défaut. La décocher
conserve l'écran de démarrage SUPERMODEL de l'édition choisie.

Depuis la racine, `python3 tools/gen_boot_cheddar.py --check` vérifie le code
embarqué. `python3 tools/emu/test_boot_cheddar.py original.syx cheddar.syx`
compare les deux OS et rejoue les écritures de l'écran. Pour une édition
Machine Optional qui utilise les pilotes du runtime, fournir les captures
`--original-capture` et `--patched-capture` de `capture_rebuild300_boot.py`.
