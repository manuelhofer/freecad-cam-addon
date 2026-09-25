#!/bin/sh
# Installiert die beiden unterstuetzten FreeCAD-Versionen ohne Oberflaeche aus
# conda-forge, damit die Pruefungen unter tests/ darin laufen koennen:
#   fcenv         aktueller Wochen-Build (Entwicklerversion)
#   fcenv-stabil  aktuelle stabile Version (derzeit 1.1.x), mit Python 3.11
#                 wie in den offiziellen Paketen
# Gedacht fuer Linux-Container (Cloud-Sitzung, CI); auf dem eigenen Rechner
# reicht das normale FreeCAD.
#
# Ziel: $FC_BASIS (Standard: ~/.cache/freecad-cam-addon)
set -eu

basis="${FC_BASIS:-$HOME/.cache/freecad-cam-addon}"
micromamba_version="2.9.0-0"

mkdir -p "$basis/mm"
if [ ! -x "$basis/mm/bin/micromamba" ]; then
    curl -sSL "https://conda.anaconda.org/conda-forge/linux-64/micromamba-$micromamba_version.tar.bz2" \
        | tar -xj -C "$basis/mm" bin/micromamba
fi
export MAMBA_ROOT_PREFIX="$basis/mmroot"

einrichten() {
    ziel="$1"; shift
    if [ -x "$ziel/bin/freecadcmd" ]; then
        "$basis/mm/bin/micromamba" update -y -q -p "$ziel" -c conda-forge "$@"
    else
        "$basis/mm/bin/micromamba" create -y -q -p "$ziel" -c conda-forge "$@"
    fi
    echo "FreeCAD bereit: $ziel/bin/freecadcmd"
}

# defusedxml braucht der Addon-Manager von FreeCAD; ohne ihn meldet er beim
# Start einen Fehler.
einrichten "$basis/fcenv" freecad "python=3.12" defusedxml
# Wochen-Builds tragen ein Datum als Versionsnummer (2026.09.16), stabile
# Versionen 1.x - "freecad<2000" ist also die neueste stabile.
einrichten "$basis/fcenv-stabil" "freecad<2000" "python=3.11" defusedxml
