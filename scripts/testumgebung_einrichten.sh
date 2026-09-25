#!/bin/sh
# Installiert FreeCAD ohne Oberflaeche aus conda-forge, damit die Pruefungen
# unter tests/ mit FreeCADCmd laufen koennen. Gedacht fuer Linux-Container
# (Cloud-Sitzung, CI); auf dem eigenen Rechner reicht das normale FreeCAD.
#
# Ziel: $FC_UMGEBUNG (Standard: ~/.cache/freecad-cam-addon/fcenv)
set -eu

basis="${FC_BASIS:-$HOME/.cache/freecad-cam-addon}"
umgebung="${FC_UMGEBUNG:-$basis/fcenv}"
micromamba_version="2.9.0-0"

mkdir -p "$basis/mm"
if [ ! -x "$basis/mm/bin/micromamba" ]; then
    curl -sSL "https://conda.anaconda.org/conda-forge/linux-64/micromamba-$micromamba_version.tar.bz2" \
        | tar -xj -C "$basis/mm" bin/micromamba
fi

export MAMBA_ROOT_PREFIX="$basis/mmroot"
if [ -x "$umgebung/bin/freecadcmd" ]; then
    "$basis/mm/bin/micromamba" update -y -q -p "$umgebung" -c conda-forge freecad
else
    "$basis/mm/bin/micromamba" create -y -q -p "$umgebung" -c conda-forge freecad "python=3.12"
fi

echo "FreeCAD bereit: $umgebung/bin/freecadcmd"
