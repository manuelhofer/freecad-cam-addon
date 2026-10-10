# SPDX-License-Identifier: LGPL-2.1-or-later
"""Maschinenzuordnung für den geometrischen Materialentwurf, ohne Dialog oder Ersatzmaschine."""

import os

import FreeCAD

from . import maschine as mm
from . import reichweite as rw
from . import schwenken as sw
from . import werkzeuge as wz
from .kinematik import Kinematik
from .sprache import tr


def ebene_erreichbar(job, operation):
    """True/False für die Ebene mit dem realen Werkzeug, None bei rein geometrischem Entwurf.

    Ohne zugewiesene Maschine bleibt die bisherige geometrische Vorschau erhalten.
    Eine fehlende/unlesbare tatsächliche Zuordnung bedeutet dagegen keinen Abtrag.
    Bereits geöffnete Maschinen liefern ihre aktuellen, auch ungespeicherten Anschläge.
    """
    if not sw.ist_ebene(job):
        return None
    m = _maschine(job, operation)
    if m is None or m is False:
        return m
    return sw.passende_rundachsen(m, job.Ebene, sw.rundachsen_von(job)) is not None


def _maschine(job, operation):
    """Tatsächliche Zuordnung: Maschine, None ohne Zuordnung, False wenn unlesbar."""
    grund = rw.grundjob_von(job)
    datei = getattr(job, rw.EIGENSCHAFT_MASCHINE, "") or getattr(grund, rw.EIGENSCHAFT_MASCHINE, "")
    if not datei:
        return None
    if not os.path.isfile(datei):
        return False
    try:
        pfad = os.path.normcase(os.path.abspath(datei))
        doc = next(
            (
                d
                for d in FreeCAD.listDocuments().values()
                if d.FileName and os.path.normcase(os.path.abspath(d.FileName)) == pfad
            ),
            None,
        )
        if doc is None:
            # Verborgen lesen; keine sichtbare Maschine oder persönliche Bibliothek ändern.
            doc = FreeCAD.openDocument(datei, True)
        paar = next(
            (
                (a, m)
                for a in doc.Objects
                if a.TypeId == "Assembly::AssemblyObject"
                and (m := mm.finde_maschine(a)) is not None
            ),
            None,
        )
        tc = getattr(operation, "ToolController", None)
        if paar is None or tc is None:
            return False
        p = rw.Pruefung(*paar)
        aufnahme = p.werkzeugaufnahme(int(tc.ToolNumber))
        if aufnahme is None:
            return False
        ein = rw.einspannung(tc, wz.Bibliothek.laden())
        return sw.Maschine(p, aufnahme, ein, rw.nullpunkt(grund))
    except Exception as fehler:
        FreeCAD.Console.PrintLog(f"CAM-Addon: Ebenenzugang: {fehler}\n")
        return False


def bahn_grund(maschine, befehle, name="", grenzen=True):
    """Grund bei fehlender Achse, unlesbarer Bewegung oder überschrittener Grenze, sonst leer.

    Der bestehende Reichweitenkern prüft auch innere Kreisextrema. Hier werden
    keine Bewegungen begrenzt oder ersetzt; eine ungültige Operation bleibt aus.
    Ohne `grenzen` (der Abspieler) zählt eine überschrittene Grenze nicht als Grund:
    Das Prüffenster zeigt sie rot, jede Überschreitung ist eine Station, und der
    Abspieler hält an der Grenze (Spezifikation Simulation 4a/4b) – nur, was die
    Maschine gar nicht fahren kann (fremde Rundachse, unlesbare Sätze), bleibt aus.
    """
    p = maschine.pruefung
    kin = Kinematik(p, maschine.aufnahme, maschine.laenge, maschine.nullpunkt)
    linear, dreh = p.achsen_fuer(maschine.aufnahme)
    result = rw.Ergebnis()
    sammler = rw._Sammler(p, result)
    sammler.beginne(name, linear, dreh, kin)
    vorhanden = {a.buchstabe for a in maschine.rundachsen}
    fremd = {b for c in befehle for b in c.Parameters if b in rw.RUNDACHSEN} - vorhanden
    if fremd:
        return tr("mz.fehler.achse", achsen=", ".join(sorted(fremd)))
    absolut, rund = True, dict.fromkeys(vorhanden, 0.0)
    for c in befehle:
        if c.Name.upper() in ("G90", "G91"):
            absolut = c.Name.upper() == "G90"
        for a in maschine.rundachsen:
            b = a.buchstabe
            if b in c.Parameters:
                wert = float(c.Parameters[b])
                rund[b] = wert if absolut else rund[b] + wert
                if grenzen and not a.erlaubt(rund[b]):
                    return tr("mz.fehler.rundgrenze", achse=b, wert=f"{rund[b]:g}")
    unbekannt = []
    for s in rw._bahn(befehle, unbekannt.append, rueckzug=True):
        if not grenzen and s.art == "punkt":
            # Der Abspieler fragt nur, was die Maschine gar nicht fahren kann – Punkte sammelt
            # er selbst (am 4-Achs-Testteil 330 000 Punkte umsonst, P-2026-10-11-01).
            continue
        loesung, stellungen = kin._loesung(s.rund)
        if s.art == "punkt":
            sammler.punkt(s.ort, s.rund, loesung, stellungen)
        elif loesung is None:
            return tr("si.fehler.linear")
        elif grenzen:
            for ort in s.ort.punkte(loesung.s):
                sammler.punkt(ort, s.rund, loesung, stellungen)
    sammler.ende_operation()
    sammler.fertig()
    if grenzen and result.ueberschreitungen:
        return result.ueberschreitungen[0].text()
    if unbekannt:
        return tr("mz.fehler.befehle", befehle=", ".join(unbekannt))
    return "; ".join(result.hinweise) if grenzen else ""


def operation_erreichbar(job, operation):
    """Erreichbarkeit der vollständigen tatsächlichen Bahn für den Materialentwurf."""
    m = _maschine(job, operation)
    if m is None or m is False:
        return m
    try:
        befehle = m.pruefung.befehle(
            operation,
            job if sw.ist_ebene(job) else None,
            m.aufnahme,
            m.laenge,
            m.nullpunkt,
        )
        return not bahn_grund(m, befehle, operation.Label)
    except (ValueError, RuntimeError) as fehler:
        FreeCAD.Console.PrintLog(f"CAM-Addon: Bahnzugang: {fehler}\n")
        return False
