# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Maschinen-Speicher (W-011, Spezifikation Maschine aus Baugruppe, Abschnitt 12): die
Liste der eigenen Maschinen – Manuel, 2026-10-02: „Ich hätte gerne sozusagen einen
Maschinen-Speicher … ich kann ja mehrere Maschinen haben“.

Eine Maschine ist eine FreeCAD-Datei mit einer Baugruppe und dem Maschinenobjekt (Abschnitt 5).
Die Liste merkt sich, wo die Datei liegt – sie kopiert sie nicht: Ändert man die Maschine, gilt
das sofort. Dazu, was das Addon zum Entscheiden braucht, ohne die Datei zu öffnen: die Art
(Drehmaschine, 3-, 4-, 5-Achs-Fräse – aus den Achsen gelesen), die Achsen im Programm, die
Werkzeugplätze und die höchste Drehzahl. Gespeichert als JSON unter
FreeCAD.getUserAppDataDir()/CamAddon/ wie die Werkzeugverwaltung: Neustart und Update
überleben es.

In die Liste kommt eine Maschine von selbst, wenn man ihre Datei speichert (gui_maschinen
beobachtet das Speichern), auf ihr prüft oder sie in einem Assistenten wählt
(reichweite.merke_maschine) – und im Fenster „Maschinen“ mit „Hinzufügen …“. Entfernen nimmt
sie nur aus der Liste, die Datei bleibt.

Läuft ohne Oberfläche.
"""

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field

import FreeCAD

from . import kette as kette_modul
from . import maschine as m
from .sprache import tr

DATEINAME = "maschinen.json"
FORMAT = 1

# Die Arten (gespeichert, deshalb feste ASCII-Wörter; angezeigt wird art_text()).
DREHMASCHINE = "drehmaschine"
FRAESE_3 = "fraese3"
FRAESE_4 = "fraese4"
FRAESE_5 = "fraese5"
UNBEKANNT = "unbekannt"  # die Achsen ließen sich nicht lesen (halb gebaut)
ARTEN = (DREHMASCHINE, FRAESE_3, FRAESE_4, FRAESE_5, UNBEKANNT)
REIHENFOLGE = "XYZUVWABC"  # so stehen die Achsen in der Liste; andere Namen danach


@dataclass
class Eintrag:
    """Eine Maschine in der Liste."""

    name: str
    datei: str
    art: str = UNBEKANNT
    achsen: list = field(default_factory=list)  # im Programm: „X“, „Y“, „Z“, „B“, „C“
    rundachsen: list = field(default_factory=list)  # die Rundachsen, die positionieren
    revolver: bool = False
    plaetze: int = 0  # Werkzeugaufnahmen
    drehzahl: float = 0.0  # 1/min – die höchste aller Spindeln
    # Für „Schruppwerte planen“, wenn die Datei nicht offen ist (Durchsicht D-20): die Spindel,
    # die das Werkzeug antreibt, der kleinste Höchstvorschub, die Nennleistung (kW).
    werkzeugdrehzahl: float = 0.0
    vorschub: float = 0.0
    leistung: float = 0.0

    @property
    def vorhanden(self):
        return bool(self.datei) and os.path.isfile(self.datei)


def datei_pfad():
    """Die Datei der Liste beim Benutzer."""
    return os.path.join(FreeCAD.getUserAppDataDir(), "CamAddon", DATEINAME)


def gleiche_datei(a, b):
    """Ob zwei Pfade dieselbe Datei meinen – unter Windows auch mit / statt \\ und in anderer
    Großschreibung; leere Pfade nie."""
    if not a or not b:
        return False
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def laden(pfad=None):
    """[Eintrag] – leer, wenn es die Datei nicht gibt oder sie nicht lesbar ist."""
    pfad = pfad or datei_pfad()
    try:
        with open(pfad, encoding="utf-8") as datei:
            daten = json.load(datei)
    except (OSError, ValueError):
        return []
    eintraege = []
    for roh in daten.get("maschinen", []) if isinstance(daten, dict) else []:
        try:
            eintrag = Eintrag(**{k: v for k, v in roh.items() if k in Eintrag.__dataclass_fields__})
        except TypeError:
            continue  # ohne Name oder Datei – überspringen statt alles zu verlieren
        if eintrag.art not in ARTEN:
            eintrag.art = UNBEKANNT
        eintraege.append(eintrag)
    return eintraege


def speichern(eintraege, pfad=None):
    """Schreibt die Liste."""
    pfad = pfad or datei_pfad()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    daten = {"format": FORMAT, "maschinen": [asdict(e) for e in eintraege]}
    with open(pfad, "w", encoding="utf-8") as datei:
        json.dump(daten, datei, ensure_ascii=False, indent=2)


def finde(eintraege, datei):
    """Der Eintrag zur Datei – oder None."""
    return next((e for e in eintraege if gleiche_datei(e.datei, datei)), None)


def beschreibe(assembly, maschine):
    """Der Eintrag für die Maschine – Name und Datei, dazu die Art aus ihren Achsen: Eine
    Drehmaschine hat einen Revolver oder eine Spindel im Tisch (das Teil dreht); sonst ist
    sie eine Fräse mit so vielen Achsen, wie sie Rundachsen zum Positionieren hat (zwei und
    mehr: 5-Achs). Lässt sich die Kette nicht lesen, bleibt die Art „unbekannt“."""
    eintrag = Eintrag(maschine.Label, assembly.Document.FileName or "")
    arten = m.betriebsarten(maschine)
    try:
        rollen, _meldungen = m.rollen(kette_modul.lies_kette(assembly), maschine)
    except Exception as fehler:  # eine halb gebaute Maschine soll die Liste nicht stören
        FreeCAD.Console.PrintLog(f"CAM-Addon: Achsen von {maschine.Label}: {fehler}\n")
        rollen = None
    namen = []
    for ba in arten:
        name = m.programmname(ba).upper()
        if ba.Art in (m.ART_LINEAR, m.ART_POSITIONIEREN) and name and name not in namen:
            namen.append(name)
    eintrag.achsen = sorted(namen, key=_reihenfolge)
    eintrag.rundachsen = [n for n in eintrag.achsen if n in ("A", "B", "C")]
    eintrag.revolver = any(ba.Art == m.ART_REVOLVER for ba in arten)
    eintrag.plaetze = sum(1 for a in m.aufnahmen(maschine) if a.Art == m.AUFNAHME_WERKZEUG)
    drehzahlen = [
        float(getattr(ba, "Drehzahl", 0.0) or 0.0) for ba in arten if ba.Art == m.ART_SPINDEL
    ]
    eintrag.drehzahl = max(drehzahlen, default=0.0)
    from . import schruppwerte  # hier: schruppwerte liest die Liste selbst

    try:
        eintrag.werkzeugdrehzahl, eintrag.vorschub = schruppwerte.grenzen_der_maschine(maschine)
        eintrag.leistung = schruppwerte.leistung_der_maschine(maschine)
    except Exception as fehler:  # wie oben: eine halb gebaute Maschine stört die Liste nicht
        FreeCAD.Console.PrintLog(f"CAM-Addon: Grenzen von {maschine.Label}: {fehler}\n")
    if rollen is None:
        return eintrag
    teil_dreht = any(ba.Art == m.ART_SPINDEL and rollen.get(ba.Gelenk) == m.TISCH for ba in arten)
    if eintrag.revolver or teil_dreht:
        eintrag.art = DREHMASCHINE
    else:
        eintrag.art = {0: FRAESE_3, 1: FRAESE_4}.get(len(eintrag.rundachsen), FRAESE_5)
    return eintrag


def _reihenfolge(name):
    stelle = REIHENFOLGE.find(name)
    return (stelle if stelle >= 0 else len(REIHENFOLGE), name)


def merken(assembly, maschine, pfad=None):
    """Nimmt die Maschine in die Liste auf – oder schreibt ihren Eintrag neu (Name und Art
    können sich geändert haben). Eine nie gespeicherte Maschine hat keine Datei: Sie kommt
    erst beim Speichern dazu. Gibt den Eintrag zurück oder None."""
    eintrag = beschreibe(assembly, maschine)
    if not eintrag.datei:
        return None
    eintraege = laden(pfad)
    alt = finde(eintraege, eintrag.datei)
    if alt is None:
        eintraege.append(eintrag)
    elif asdict(alt) == asdict(eintrag):
        return alt  # nichts Neues – die Datei bleibt, wie sie ist
    else:
        eintraege[eintraege.index(alt)] = eintrag
    speichern(eintraege, pfad)
    return eintrag


def merken_dokument(dokument, pfad=None):
    """Alle Maschinen im Dokument in die Liste – beim Speichern. Gibt [Eintrag] zurück."""
    ergebnis = []
    for objekt in dokument.Objects:
        if objekt.TypeId == "Assembly::AssemblyObject":
            maschine = m.finde_maschine(objekt)
            if maschine is not None:
                eintrag = merken(objekt, maschine, pfad)
                if eintrag is not None:
                    ergebnis.append(eintrag)
    return ergebnis


def merken_datei(datei, pfad=None):
    """Die Maschine aus der Datei in die Liste, wenn die Datei offen ist (sie wurde gerade
    zum Prüfen oder im Assistenten benutzt). Gibt [Eintrag] zurück."""
    for dokument in FreeCAD.listDocuments().values():
        if gleiche_datei(dokument.FileName, datei):
            return merken_dokument(dokument, pfad)
    return []


def fluechtig(datei):
    """Liegt die Datei im temporären Ordner des Systems – den das System leert?"""
    if not datei:
        return False
    try:
        ordner = os.path.realpath(tempfile.gettempdir())
        return os.path.commonpath([ordner, os.path.realpath(datei)]) == ordner
    except ValueError:  # andere Laufwerke (Windows)
        return False


def aufraeumen(pfad=None):
    """Nimmt die Einträge aus der Liste, deren Datei im temporären Ordner lag und weg ist –
    von dort kommt sie nicht wieder, „Suchen …“ hätte keinen Sinn (Manuel, 2026-10-10: eine
    Beispielmaschine aus /tmp stand mit „nicht gefunden“ in der Liste). Gibt [Eintrag] zurück,
    die weg sind; die Konsole sagt es je Maschine."""
    eintraege = laden(pfad)
    weg = [e for e in eintraege if not e.vorhanden and fluechtig(e.datei)]
    if weg:
        speichern([e for e in eintraege if e not in weg], pfad)
        for eintrag in weg:
            FreeCAD.Console.PrintWarning(
                tr("ms.fluechtig_weg", name=eintrag.name, datei=eintrag.datei) + "\n"
            )
    return weg


def entfernen(datei, pfad=None):
    """Nimmt die Maschine aus der Liste; die Datei bleibt. Gibt True zurück, wenn sie drin war."""
    eintraege = laden(pfad)
    eintrag = finde(eintraege, datei)
    if eintrag is None:
        return False
    eintraege.remove(eintrag)
    speichern(eintraege, pfad)
    return True


def art_text(eintrag):
    """„Drehmaschine mit Revolver (12 Plätze), C, Y“, „4-Achs-Fräse (A)“ …"""
    if eintrag.art == DREHMASCHINE:
        extra = list(eintrag.rundachsen) + (["Y"] if "Y" in eintrag.achsen else [])
        if eintrag.revolver:
            text = tr("ms.art.drehmaschine_revolver", plaetze=eintrag.plaetze)
        else:
            text = tr("ms.art.drehmaschine")
        return ", ".join([text, *extra])
    if eintrag.art == FRAESE_3:
        return tr("ms.art.fraese3")
    rund = ", ".join(eintrag.rundachsen)
    if eintrag.art == FRAESE_4:
        return tr("ms.art.fraese4", achsen=rund)
    if eintrag.art == FRAESE_5:
        return tr("ms.art.fraese5", achsen=rund)
    return tr("ms.art.unbekannt")
