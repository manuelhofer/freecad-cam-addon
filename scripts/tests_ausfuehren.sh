#!/bin/sh
# Fuehrt alle Pruefungen tests/test_*.py mit FreeCADCmd aus (ohne Fenster).
# FreeCADCmd liefert bei einer Ausnahme im Skript nicht zuverlaessig einen
# Fehlercode; deshalb schreibt jede Pruefung am Ende "OK <datei>" und das
# Skript wertet genau diese Meldung aus. Sie steht am Zeilenende, aber nicht
# immer am Zeilenanfang: FreeCADCmd schreibt seinen Fortschritt ("(60 %)" mit
# Tabulatoren und Wagenruecklauf) ohne Zeilenumbruch, und die Meldung kann
# direkt dahinter landen. "UEBERSPRUNGEN <datei>: Grund" ist nur fuer
# Funktionen erlaubt, die es in der geprueften FreeCAD-Version nicht gibt.
set -u
# FreeCADCmd druckt nach der Locale: ohne UTF-8 bricht eine Pruefung beim ersten
# Umlaut in print() ab ('ascii' codec can't encode ...). Dann C.UTF-8 nehmen.
case "$(locale charmap 2>/dev/null)" in UTF-8) ;; *) export LC_ALL=C.UTF-8 ;; esac

repo="$(cd "$(dirname "$0")/.." && pwd)"
fc="${FREECADCMD:-${FC_UMGEBUNG:-$HOME/.cache/freecad-cam-addon/fcenv}/bin/freecadcmd}"
if [ ! -x "$fc" ]; then
    echo "FreeCADCmd nicht gefunden ($fc) - erst scripts/testumgebung_einrichten.sh" >&2
    exit 2
fi

# FREECAD_USER_HOME greift nur bei einem vorhandenen Ordner. Ohne ihn schreiben
# Bibliotheksprüfungen in die echte Werkzeugverwaltung des angemeldeten Benutzers.
profil="$(mktemp -d)" || exit 2
trap 'rm -rf "$profil"' 0
mkdir -p "$profil/Mod"

fehler=0
for test in "$repo"/tests/test_*.py; do
    name="$(basename "$test")"
    ausgabe="$(QT_QPA_PLATFORM=offscreen FREECAD_USER_HOME="$profil" "$fc" "$test" 2>&1)"
    if printf '%s\n' "$ausgabe" | grep -Eq "(^|[[:space:]])OK $name\$"; then
        echo "ok     $name"
    elif printf '%s\n' "$ausgabe" | grep -Eq "(^|[[:space:]])UEBERSPRUNGEN $name:"; then
        # Nur fuer Funktionen, die es in dieser FreeCAD-Version nicht gibt.
        grund="$(printf '%s\n' "$ausgabe" | sed -n "s/.*UEBERSPRUNGEN $name://p" | head -1)"
        echo "skip   $name ($grund )"
    else
        echo "FEHLER $name"
        printf '%s\n' "$ausgabe" | tail -20
        fehler=1
    fi
done
exit $fehler
