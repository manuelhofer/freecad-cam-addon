#!/bin/sh
# Startet FreeCAD mit Oberflaeche unsichtbar (Xvfb) und frischem Benutzer-
# profil, laedt das Addon und fuehrt ein Szenario aus tests/gui/ aus.
# Screenshots und ergebnis.txt landen im Ausgabeordner.
#
#   scripts/oberflaeche_testen.sh [szenario.py ...]
#
# Ohne Argument laufen alle tests/gui/szenario_*.py. Ausgabeordner:
# $AUSGABE, sonst tests/gui/ausgabe.
set -u
# FreeCADCmd druckt nach der Locale: ohne UTF-8 bricht eine Pruefung beim ersten
# Umlaut in print() ab ('ascii' codec can't encode ...). Dann C.UTF-8 nehmen.
case "$(locale charmap 2>/dev/null)" in UTF-8) ;; *) export LC_ALL=C.UTF-8 ;; esac

repo="$(cd "$(dirname "$0")/.." && pwd)"
fc="${FREECAD:-${FC_UMGEBUNG:-$HOME/.cache/freecad-cam-addon/fcenv}/bin/freecad}"
[ -x "$fc" ] || { echo "FreeCAD nicht gefunden ($fc)" >&2; exit 2; }
command -v xvfb-run >/dev/null || { echo "xvfb-run fehlt" >&2; exit 2; }

if [ $# -eq 0 ]; then
    set -- "$repo"/tests/gui/szenario_*.py
fi
ausgabe_basis="${AUSGABE:-$repo/tests/gui/ausgabe}"
# Ein Szenario beendet FreeCAD selbst. Laeuft es laenger, haengt etwas.
# CAMADDON_ZEITLIMIT: laenger auf einem langsamen oder ausgelasteten Rechner.
zeitlimit_s="${CAMADDON_ZEITLIMIT:-180}"

fehler=0
for szenario in "$@"; do
    [ -f "$szenario" ] || continue
    name="$(basename "$szenario" .py)"
    ausgabe="$ausgabe_basis/$name"
    profil="$(mktemp -d)"
    rm -rf "$ausgabe"; mkdir -p "$ausgabe" "$profil/Mod"
    ln -s "$repo" "$profil/Mod/freecad-cam-addon"
    ln -s "$repo/tests/gui/_lauf" "$profil/Mod/_camaddon_lauf"
    # CAMADDON_OHNE_UPDATE: keine Update-Suche beim Start (kein Netz im Test).
    CAMADDON_OHNE_UPDATE=1 FREECAD_USER_HOME="$profil" CAMADDON_SZENARIO="$(cd "$(dirname "$szenario")" && pwd)/$(basename "$szenario")" \
        CAMADDON_AUSGABE="$ausgabe" \
        timeout "$zeitlimit_s" xvfb-run -a -s "-screen 0 1280x800x24" "$fc" > "$ausgabe/freecad.log" 2>&1
    rueckgabe=$?
    if [ "$rueckgabe" -eq 124 ]; then
        # Greift das Zeitlimit, haengt etwas (z. B. eine offene Rueckfrage) -
        # auch wenn das Ergebnis OK war.
        echo "FEHLER $name - FreeCAD hat sich nicht beendet (Zeitlimit $zeitlimit_s s)"
        fehler=1
    elif grep -A 30 "^Traceback" "$ausgabe/freecad.log" | grep -q 'File ".*camaddon/'; then
        # Ein Fehler im Addon, den Qt oder FreeCAD nur ins Log schreibt (etwa in
        # getStandardButtons) - das Szenario selbst merkt ihn nicht.
        echo "FEHLER $name - Traceback aus dem Addon im Log:"
        grep -A 30 "^Traceback" "$ausgabe/freecad.log" | head -30
        fehler=1
    elif [ "$(cat "$ausgabe/ergebnis.txt" 2>/dev/null)" = "OK" ]; then
        echo "ok     $name"
    else
        echo "FEHLER $name"
        cat "$ausgabe/ergebnis.txt" 2>/dev/null || tail -20 "$ausgabe/freecad.log"
        [ -s "$ausgabe/absturz.txt" ] && cat "$ausgabe/absturz.txt"
        fehler=1
    fi
    rm -rf "$profil"
done
exit $fehler
