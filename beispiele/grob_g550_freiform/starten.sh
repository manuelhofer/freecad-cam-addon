#!/bin/sh
# Öffnet den Simultanjob mit seiner Beispielbibliothek in einem eigenen Profil.
# Die persönliche Werkzeugverwaltung wird weder geladen noch ersetzt.
set -eu
beispiel="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo="$(CDPATH= cd -- "$beispiel/../.." && pwd)"
profil="$(mktemp -d)"
trap 'rm -rf "$profil"' 0
mkdir -p "$profil/Mod"
ln -s "$repo" "$profil/Mod/freecad-cam-addon"
export FREECAD_USER_HOME="$profil"
export CAMADDON_GROB_BEISPIEL="$beispiel"
export CAMADDON_OHNE_UPDATE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
if command -v systemd-run >/dev/null 2>&1; then
    systemd-run --user --scope -q -p MemoryMax=16G -p MemorySwapMax=0 \
        freecad "$beispiel/anzeigen.FCMacro"
else
    freecad "$beispiel/anzeigen.FCMacro"
fi
