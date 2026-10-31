# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Kataloge der Hersteller als eigener Download (Manuel, 2026-10-31: „ja sollte man jetzt schon
planen und einbauen das man sagt nach der installation "hey sollen wir die kataloginhalte
downloaden um einfach deutlich bessere vorhersagen machen zu können" oder sowas .. und dann ja
nein vll“).

Die drei Ordner `werkzeugkiste_daten`, `halter_daten`, `spannmittel_daten` kommen nicht mehr mit
dem Update-Paket (.gitattributes: export-ignore) – in einem Git-Klon stehen sie weiter im Addon.
`ordner(name)`: der Ordner im Addon, wenn dort Dateien liegen, sonst der im FreeCAD-Profil
(`CamAddon/kataloge/<name>`), wohin `laden()` sie holt – dort überstehen sie jedes Update.

`INDEX` (`kataloge_index.json`, kommt mit dem Addon) nennt je Datei Größe und SHA-256; `laden()`
holt von GitHub (raw, gepackt) nur, was im Profil fehlt oder anders ist, und prüft die Summe.
`scripts/kataloge_index.py` schreibt den Index neu, wenn sich ein Katalog ändert (die Prüfung
test_kataloge merkt, wenn er nicht passt).

Läuft ohne Oberfläche; die Frage nach dem Start steht in gui_kataloge.py.
"""

import gzip
import hashlib
import json
import os
import urllib.error
import urllib.request

from . import ADDON_ORDNER

NAMEN = ("werkzeugkiste_daten", "halter_daten", "spannmittel_daten")
PAKET = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(PAKET, "kataloge_index.json")
ZWEIG = "main"
ADRESSE = f"https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/{ZWEIG}/camaddon/"
ZEITLIMIT_S = 60
FRAGE = "KatalogeFrage"  # Parameter: "" (fragen), "spaeter", "nein", "ja"
JA, NEIN, SPAETER = "ja", "nein", "spaeter"


def profil(name=""):
    """Der Ordner der Kataloge im FreeCAD-Profil (mit `name` der eines Katalogs)."""
    import FreeCAD

    basis = os.path.join(FreeCAD.getUserAppDataDir(), "CamAddon", "kataloge")
    return os.path.join(basis, name) if name else basis


def _hat_dateien(pfad):
    return os.path.isdir(pfad) and any(n.endswith(".json") for n in os.listdir(pfad))


def ordner(name):
    """Wo der Katalog `name` liegt: im Addon (Git-Klon, Entwicklung), sonst im Profil – auch,
    wenn es dort (noch) nichts gibt."""
    im_addon = os.path.join(PAKET, name)
    if _hat_dateien(im_addon):
        return im_addon
    return profil(name)


def vorhanden():
    """Liegt wenigstens ein Katalog vor (im Addon oder im Profil)?"""
    return any(_hat_dateien(ordner(n)) for n in NAMEN)


def im_addon():
    """Kommen die Kataloge mit dem Addon (Git-Klon)? Dann gibt es nichts zu laden."""
    return all(_hat_dateien(os.path.join(PAKET, n)) for n in NAMEN)


def index():
    """{„halter_daten/hersteller.json“: {"groesse", "sha256"}} – leer, wenn der Index fehlt."""
    try:
        with open(INDEX, encoding="utf-8") as datei:
            return dict(json.load(datei).get("dateien", {}))
    except (OSError, ValueError):
        return {}


def summe(pfad):
    h = hashlib.sha256()
    with open(pfad, "rb") as datei:
        for stueck in iter(lambda: datei.read(1 << 20), b""):
            h.update(stueck)
    return h.hexdigest()


def fehlend():
    """[(Pfad im Index, Eintrag)] – was im Profil fehlt oder anders ist als im Index."""
    ergebnis = []
    for pfad, eintrag in sorted(index().items()):
        ziel = os.path.join(profil(), *pfad.split("/"))
        if not os.path.isfile(ziel) or summe(ziel) != eintrag.get("sha256"):
            ergebnis.append((pfad, eintrag))
    return ergebnis


def groesse_text(byte):
    """„1,2 MB“."""
    return f"{byte / 1e6:.1f} MB".replace(".", ",")


def _hole(adresse):
    """Die Bytes von `adresse` – gepackt angefragt (GitHub liefert gzip); ohne Pythons ssl über
    installieren.hole (Qt oder curl), dann ungepackt."""
    anfrage = urllib.request.Request(adresse, headers={"Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT_S) as antwort:
            daten = antwort.read()
            if antwort.headers.get("Content-Encoding", "").lower() == "gzip":
                daten = gzip.decompress(daten)
            return daten
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError):
        from .aktualisierung import _installierer

        return _installierer(ADDON_ORDNER).hole(adresse, ZEITLIMIT_S)


def laden(fortschritt=None, adresse=None, abbrechen=None):
    """Holt, was im Profil fehlt oder anders ist (fehlend()), prüft die Summe und legt es ab –
    jede Datei erst unter .neu, dann umbenannt. `fortschritt(fertig, alle, pfad)` je Datei;
    `abbrechen()` → True hört auf. Gibt die Zahl der geholten Dateien zurück; OSError, wenn eine
    nicht geht (die bis dahin geholten bleiben). Ohne `adresse`: ADRESSE."""
    adresse = adresse or ADRESSE
    offen = fehlend()
    for nummer, (pfad, eintrag) in enumerate(offen):
        if abbrechen is not None and abbrechen():
            return nummer
        if fortschritt is not None:
            fortschritt(nummer, len(offen), pfad)
        daten = _hole(adresse + pfad)
        if hashlib.sha256(daten).hexdigest() != eintrag.get("sha256"):
            raise OSError(f"{pfad}: Prüfsumme stimmt nicht")
        ziel = os.path.join(profil(), *pfad.split("/"))
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel + ".neu", "wb") as datei:
            datei.write(daten)
        os.replace(ziel + ".neu", ziel)
    if fortschritt is not None:
        fortschritt(len(offen), len(offen), "")
    _alte_weg()
    geaendert()
    return len(offen)


def _alte_weg():
    """Dateien im Profil, die der Index nicht mehr nennt (umbenannt, zusammengelegt), weg."""
    bekannt = set(index())
    for name in NAMEN:
        pfad = profil(name)
        if not os.path.isdir(pfad):
            continue
        for datei in os.listdir(pfad):
            if datei.endswith(".json") and f"{name}/{datei}" not in bekannt:
                os.remove(os.path.join(pfad, datei))


def geaendert():
    """Was aus den Katalogen gemerkt ist, gilt nicht mehr (werkzeugwahl, empfehlung, die geprüften
    Reihen der Werkzeugkiste)."""
    from . import empfehlung, werkzeugkiste_datei, werkzeugwahl

    werkzeugwahl._KATALOG.clear()
    empfehlung._KATALOG.clear()
    werkzeugkiste_datei._mitgeliefert = None  # beim nächsten Mal neu (und neu zwischengespeichert)


def index_schreiben(ziel=INDEX):
    """Den Index aus den Katalogen im Addon (für scripts/kataloge_index.py und die Prüfung)."""
    dateien = {}
    for name in NAMEN:
        pfad = os.path.join(PAKET, name)
        for datei in sorted(os.listdir(pfad)) if os.path.isdir(pfad) else []:
            if datei.endswith(".json"):
                voll = os.path.join(pfad, datei)
                dateien[f"{name}/{datei}"] = {
                    "groesse": os.path.getsize(voll),
                    "sha256": summe(voll),
                }
    with open(ziel, "w", encoding="utf-8") as datei:
        json.dump({"dateien": dateien}, datei, ensure_ascii=False, indent=1, sort_keys=True)
        datei.write("\n")
    return dateien
