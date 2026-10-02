# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Messstopp zwischen Schruppen und Schlichten (W-010; Manuel, 2026-10-02: „dass man zwischen
Schruppen und Schlichten eine Pause setzen kann – sozusagen ein Messstopp … dann kann der Bediener
messen und dann wieder Start drücken, und es geht weiter mit Schlichten“).

Eine FreeCAD-Operation „Benutzerdefiniert“ (Path.Op.Custom) mit G-Code: Z auf die sichere Höhe über
dem Rohteil, Spindel aus (M5), Halt (M0) – nach dem Start läuft die Spindel mit Drehzahl und
Richtung des Controllers, der danach fräst, wieder an (FreeCADs Postprozessoren schreiben M3 nur
beim Werkzeugwechsel). Sie benutzt den Controller der Operation davor: kein Werkzeugwechsel vor dem
Halt.

FreeCADs Befehle kennen nur G- und M-Wörter; ein Unterprogramm der Steuerung wie Siemens „F_HOME“
schreibt erst der Postprozessor des Addons (W-005) – dafür steht vorweg der Kommentar MESSSTOPP.

Läuft ohne Oberfläche.
"""

import FreeCAD

from . import spindel
from .sprache import tr

KOMMENTAR = "(MESSSTOPP)"
ABSTAND = 5.0  # mm über dem Rohteil, wenn der Job keinen Abstand nennt


def sichere_hoehe(job):
    """Z, auf das der Fräser vor dem Halt fährt: über dem Rohteil um den Abstand des Jobs
    (FreeCADs „Clearance Height Offset“), sonst ABSTAND."""
    oben = 0.0
    form = getattr(getattr(job, "Stock", None), "Shape", None)
    if form is not None and not form.isNull():
        oben = form.BoundBox.ZMax
    abstand = ABSTAND
    blatt = getattr(job, "SetupSheet", None)
    wert = getattr(blatt, "ClearanceHeightOffset", None)
    if wert is not None:
        abstand = float(getattr(wert, "Value", wert))
    return oben + max(abstand, 0.0)


def zeilen(sicher, drehzahl, rueckwaerts=False):
    """Die Zeilen des Messstopps: Kommentar, Z hoch, M5, M0 – und mit Drehzahl die Spindel
    wieder an (M3, rückwärts M4)."""
    ergebnis = [KOMMENTAR, f"G0 Z{sicher:.3f}", "M5", "M0"]
    if drehzahl > 0:
        ergebnis.append(f"{'M4' if rueckwaerts else 'M3'} S{round(drehzahl)}")
    return ergebnis


def lege_an(job, tc, danach):
    """Legt den Messstopp im Job an – ohne eigene Transaktion, die hält der Aufrufer – mit dem
    Controller `tc` der Operation davor; `danach`: der Controller, mit dem es weitergeht
    (Drehzahl, Richtung). Gibt die Operation zurück."""
    from Path.Op import Custom

    FreeCAD.setActiveDocument(job.Document.Name)
    op = Custom.Create("Messstopp", parentJob=job)
    op.Label = tr("ms.name")
    op.ToolController = tc
    op.Source = "Text"
    drehzahl = float(getattr(danach, "SpindleSpeed", 0.0) or 0.0)
    op.Gcode = zeilen(sichere_hoehe(job), drehzahl, spindel.rueckwaerts(danach))
    return op


def ist_messstopp(op):
    """Ist `op` ein Messstopp des Addons?"""
    gcode = list(getattr(op, "Gcode", []) or [])
    return bool(gcode) and gcode[0] == KOMMENTAR
