#!/bin/sh
# Alle Pruefungen - ohne Fenster und mit Oberflaeche - in beiden unterstuetzten
# FreeCAD-Versionen (stabil und Wochen-Build). Das ist die Pflichtpruefung vor
# jedem Push (docs/arbeitsregeln.md, Abschnitt 5).
#
#   scripts/alle_tests.sh            alles
#   OHNE_OBERFLAECHE=1 scripts/...   nur die Pruefungen ohne Fenster (schnell)
#
# Umgebungen aus $FC_BASIS (Standard: ~/.cache/freecad-cam-addon), angelegt mit
# scripts/testumgebung_einrichten.sh.
set -u

repo="$(cd "$(dirname "$0")/.." && pwd)"
basis="${FC_BASIS:-$HOME/.cache/freecad-cam-addon}"

fehler=0
for umgebung in "$basis/fcenv-stabil" "$basis/fcenv"; do
    if [ ! -x "$umgebung/bin/freecadcmd" ]; then
        echo "FEHLT  $umgebung - erst scripts/testumgebung_einrichten.sh" >&2
        fehler=1
        continue
    fi
    echo "== $("$umgebung/bin/freecadcmd" --version 2>/dev/null | head -1) ($(basename "$umgebung"))"
    FC_UMGEBUNG="$umgebung" "$repo/scripts/tests_ausfuehren.sh" || fehler=1
    if [ -z "${OHNE_OBERFLAECHE:-}" ]; then
        AUSGABE="$repo/tests/gui/ausgabe/$(basename "$umgebung")" FC_UMGEBUNG="$umgebung" \
            "$repo/scripts/oberflaeche_testen.sh" || fehler=1
    fi
done
exit $fehler
