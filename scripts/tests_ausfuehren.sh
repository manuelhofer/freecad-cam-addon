#!/bin/sh
# Fuehrt alle Pruefungen tests/test_*.py mit FreeCADCmd aus (ohne Fenster).
# FreeCADCmd liefert bei einer Ausnahme im Skript nicht zuverlaessig einen
# Fehlercode; deshalb schreibt jede Pruefung am Ende "OK" und das Skript
# wertet genau diese Zeile aus.
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
    else
        echo "FEHLER $(basename "$test")"
        printf '%s\n' "$ausgabe" | tail -20
        fehler=1
    fi
done
exit $fehler
