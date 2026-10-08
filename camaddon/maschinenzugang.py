# SPDX-License-Identifier: LGPL-2.1-or-later
"""Maschinenzuordnung für den geometrischen Materialentwurf, ohne Dialog oder Ersatzmaschine."""

import os

import FreeCAD

from . import maschine as mm
from . import reichweite as rw
from . import schwenken as sw
from . import werkzeuge as wz


def ebene_erreichbar(job, operation):
    """True/False für die Ebene mit dem realen Werkzeug, None bei rein geometrischem Entwurf.

    Ohne zugewiesene Maschine bleibt die bisherige geometrische Vorschau erhalten.
    Eine fehlende/unlesbare tatsächliche Zuordnung bedeutet dagegen keinen Abtrag.
    Bereits geöffnete Maschinen liefern ihre aktuellen, auch ungespeicherten Anschläge.
    """
    if not sw.ist_ebene(job):
        return None
    datei = getattr(job, rw.EIGENSCHAFT_MASCHINE, "") or getattr(
        job.Grundjob, rw.EIGENSCHAFT_MASCHINE, ""
    )
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
        m = sw.Maschine(p, aufnahme, ein, rw.nullpunkt(job.Grundjob))
        return sw.passende_rundachsen(m, job.Ebene, sw.rundachsen_von(job)) is not None
    except Exception as fehler:
        FreeCAD.Console.PrintLog(f"CAM-Addon: Ebenenzugang: {fehler}\n")
        return False
