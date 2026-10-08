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
mkdir -p "$profil/beispiel"
cp -R "$beispiel/assets" "$profil/beispiel/assets"
cp "$beispiel/g550_winkelaufnahme.FCStd" "$beispiel/freiform_5achs.FCStd" \
    "$beispiel/beispiel_werkzeuge.json" "$profil/beispiel/"
export FREECAD_USER_HOME="$profil"
export CAMADDON_GROB_BEISPIEL="$profil/beispiel"
export CAMADDON_OHNE_UPDATE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
# Qt kann unter KDE eine andere primäre Anzeige melden. Für den Linux-Start
# die tatsächliche zweite Anzeige verwenden; eine ausdrückliche Auswahl geht vor.
if [ -z "${CAMADDON_GROB_BILDSCHIRM:-}" ] && command -v xrandr >/dev/null 2>&1; then
    CAMADDON_GROB_BILDSCHIRM="$(xrandr --listmonitors 2>/dev/null | awk 'NR > 1 && $2 !~ /\*/ {print $NF; exit}')"
    export CAMADDON_GROB_BILDSCHIRM
fi
if command -v systemd-run >/dev/null 2>&1; then
    systemd-run --user --scope -q -p MemoryMax=16G -p MemorySwapMax=0 \
        freecad "$beispiel/anzeigen.FCMacro"
else
    freecad "$beispiel/anzeigen.FCMacro"
fi
