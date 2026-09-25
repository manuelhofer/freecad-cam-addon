#!/bin/sh
# Startet FreeCAD mit Oberflaeche unsichtbar (Xvfb) und frischem Benutzer-
# profil, laedt das Addon und fuehrt ein Szenario aus tests/gui/ aus.
# Screenshots und ergebnis.txt landen im Ausgabeordner.
#
#   scripts/oberflaeche_testen.sh tests/gui/szenario_erster_start.py [ausgabe]
#
# Ohne Szenario-Argument laufen alle tests/gui/szenario_*.py.
set -u

repo="$(cd "$(dirname "$0")/.." && pwd)"
fc="${FREECAD:-${FC_UMGEBUNG:-$HOME/.cache/freecad-cam-addon/fcenv}/bin/freecad}"
[ -x "$fc" ] || { echo "FreeCAD nicht gefunden ($fc)" >&2; exit 2; }
command -v xvfb-run >/dev/null || { echo "xvfb-run fehlt" >&2; exit 2; }

if [ $# -eq 0 ]; then
    set -- "$repo"/tests/gui/szenario_*.py
fi
ausgabe_basis="${2:-${AUSGABE:-$repo/tests/gui/ausgabe}}"

fehler=0
for szenario in "$@"; do
    [ -f "$szenario" ] || continue
    name="$(basename "$szenario" .py)"
    ausgabe="$ausgabe_basis/$name"
    profil="$(mktemp -d)"
    rm -rf "$ausgabe"; mkdir -p "$ausgabe" "$profil/Mod"
    ln -s "$repo" "$profil/Mod/freecad-cam-addon"
    ln -s "$repo/tests/gui/_lauf" "$profil/Mod/_camaddon_lauf"
    FREECAD_USER_HOME="$profil" CAMADDON_SZENARIO="$(cd "$(dirname "$szenario")" && pwd)/$(basename "$szenario")" \
        CAMADDON_AUSGABE="$ausgabe" \
        timeout 180 xvfb-run -a -s "-screen 0 1280x800x24" "$fc" > "$ausgabe/freecad.log" 2>&1
    if [ "$(cat "$ausgabe/ergebnis.txt" 2>/dev/null)" = "OK" ]; then
        echo "ok     $name"
    else
        echo "FEHLER $name"
        cat "$ausgabe/ergebnis.txt" 2>/dev/null || tail -20 "$ausgabe/freecad.log"
        fehler=1
    fi
    rm -rf "$profil"
done
exit $fehler
