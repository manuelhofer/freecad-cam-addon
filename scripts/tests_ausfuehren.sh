#!/bin/sh
# Fuehrt alle Pruefungen tests/test_*.py mit FreeCADCmd aus (ohne Fenster).
# FreeCADCmd liefert bei einer Ausnahme im Skript nicht zuverlaessig einen
# Fehlercode; deshalb schreibt jede Pruefung am Ende "OK <datei>" und das
# Skript wertet genau diese Zeile aus. "UEBERSPRUNGEN <datei>: Grund" ist nur
# fuer Funktionen erlaubt, die es in der geprueften FreeCAD-Version nicht gibt.
set -u

repo="$(cd "$(dirname "$0")/.." && pwd)"
fc="${FREECADCMD:-${FC_UMGEBUNG:-$HOME/.cache/freecad-cam-addon/fcenv}/bin/freecadcmd}"
if [ ! -x "$fc" ]; then
    echo "FreeCADCmd nicht gefunden ($fc) - erst scripts/testumgebung_einrichten.sh" >&2
    exit 2
fi

fehler=0
for test in "$repo"/tests/test_*.py; do
    ausgabe="$(QT_QPA_PLATFORM=offscreen "$fc" "$test" 2>&1)"
    if printf '%s\n' "$ausgabe" | grep -qx "OK $(basename "$test")"; then
        echo "ok     $(basename "$test")"
    elif printf '%s\n' "$ausgabe" | grep -q "^UEBERSPRUNGEN $(basename "$test"):"; then
        # Nur fuer Funktionen, die es in dieser FreeCAD-Version nicht gibt.
        grund="$(printf '%s\n' "$ausgabe" | grep "^UEBERSPRUNGEN" | head -1 | cut -d: -f2-)"
        echo "skip   $(basename "$test") ($grund )"
    else
        echo "FEHLER $(basename "$test")"
        printf '%s\n' "$ausgabe" | tail -20
        fehler=1
    fi
done
exit $fehler
