#!/bin/bash

# 1. Nastavení názvu souboru (opraveno na přesný název)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="samba_control_center.py"
URL="http://127.0.0.1:5000"

# 2. Kontrola, zda soubor existuje, než začneme
if [ ! -f "$DIR/$PYTHON_SCRIPT" ]; then
    # Pokud neběží v terminálu, pošle grafické upozornění
    notify-send "Samba Control" "Chyba: $PYTHON_SCRIPT nebyl nalezen v $DIR" || echo "Soubor nenalezen!"
    exit 1
fi

# 3. Spuštění prohlížeče na pozadí se zpožděním
(
    sleep 2
    # Pokusí se otevřít URL v defaultním prohlížeči
    xdg-open "$URL" || firefox "$URL" || google-chrome "$URL"
) &

# 4. Spuštění Pythonu s právy roota (přes grafické okno pro heslo)
pkexec python3 "$DIR/$PYTHON_SCRIPT"
