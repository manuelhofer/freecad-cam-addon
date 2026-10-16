#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Schreibt daten/beispiele.json: die Dateien in beispiele/, die das Update nicht mitlädt
(.gitattributes: export-ignore), mit Größe und Prüfsumme – die Liste für „Beispiele laden …“
(camaddon/beispiele.py). Nach jeder Änderung in beispiele/ laufen lassen; test_beispiele prüft,
dass die Liste stimmt.

    python3 scripts/beispiele_liste.py
"""

import hashlib
import json
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def dateien():
    """[(Pfad, Bytes, sha256)] der Dateien in beispiele/ mit export-ignore, sortiert."""
    alle = subprocess.run(
        ["git", "ls-files", "beispiele"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split("\n")
    alle = [p for p in alle if p]
    attribute = subprocess.run(
        ["git", "check-attr", "export-ignore", "--", *alle],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\n")
    weg = {zeile.split(": ")[0] for zeile in attribute if zeile.endswith(": set")}
    ergebnis = []
    for pfad in sorted(weg):
        with open(os.path.join(REPO, pfad), "rb") as quelle:
            daten = quelle.read()
        ergebnis.append((pfad, len(daten), hashlib.sha256(daten).hexdigest()))
    return ergebnis


def main():
    liste = {
        "hinweis": "geschrieben von scripts/beispiele_liste.py",
        "dateien": [{"pfad": p, "bytes": b, "sha256": s} for p, b, s in dateien()],
    }
    with open(os.path.join(REPO, "daten", "beispiele.json"), "w", encoding="utf-8") as ziel:
        json.dump(liste, ziel, ensure_ascii=False, indent=1)
        ziel.write("\n")
    print(f"{len(liste['dateien'])} Dateien in daten/beispiele.json")


if __name__ == "__main__":
    main()
