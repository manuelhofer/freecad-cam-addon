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

Mit einem Messmerkmal (messen.Merkmal, Plan C3b) steht dahinter eine zweite Zeile „(MESSEN …)“:
was nach dem Gang davor zu messen ist – Art, Mitte, Sollmaß, Messhöhe, Toleranz. Ein
Postprozessor, der für die Steuerung einen Messzyklus kennt und einen Taster eingetragen hat,
misst dort statt zu halten; jeder andere hält wie bisher (die Zeile ist nur ein Kommentar).

Läuft ohne Oberfläche.
"""

import FreeCAD

from . import spindel
from .sprache import tr

KOMMENTAR = "(MESSSTOPP)"
MESSEN = "MESSEN"  # die Zeile mit dem Messmerkmal: „(MESSEN tasche X50.000 …)“
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


def zeilen(sicher, drehzahl, rueckwaerts=False, kuehlung=None):
    """Die Zeilen des Messstopps: Kommentar, Z hoch, M5, Kühlung aus (M9), M0 – und mit Drehzahl
    die Spindel wieder an (M3, rückwärts M4), dazu die Kühlung (`kuehlung`: "Flood" M8, "Mist"
    M7 – FreeCADs Postprozessoren schreiben sie nur beim Werkzeugwechsel). Manuel, 2026-10-17:
    „maschine fährt auf home, macht türen auf, drehzahl aus, wasser aus … und wenn man weiter
    drückt wieder alles an“."""
    ergebnis = [KOMMENTAR, f"G0 Z{sicher:.3f}", "M5", "M9", "M0"]
    if drehzahl > 0:
        ergebnis.append(f"{'M4' if rueckwaerts else 'M3'} S{round(drehzahl)}")
    if kuehlung in ("Flood", "Mist"):
        ergebnis.append("M8" if kuehlung == "Flood" else "M7")
    return ergebnis


def merkmal_zeile(m, toleranz, korrigieren=None):
    """„(MESSEN tasche X50.000 Y40.000 LX58.000 LY38.000 Z32.500 OBEN40.000 TOL0.020)“ – rund mit
    D statt LX/LY; mit `korrigieren` (die Werkzeugnummer des Schlichtwerkzeugs danach) dazu
    „KORR3“: Der Messzyklus trägt die Abweichung als dessen Radius-Verschleiß ein."""
    masse = f"D{m.durchmesser:.3f}" if m.rund else f"LX{m.laenge_x:.3f} LY{m.laenge_y:.3f}"
    korr = f" KORR{int(korrigieren)}" if korrigieren else ""
    return (
        f"({MESSEN} {m.art} X{m.x:.3f} Y{m.y:.3f} {masse} Z{m.z_mess:.3f} "
        f"OBEN{m.z_oben:.3f} TOL{toleranz:.3f}{korr})"
    )


def korrektur_von(zeilen_):
    """Die Werkzeugnummer, deren Radius-Verschleiß der Messzyklus korrigiert („KORR3“) – None:
    nur messen."""
    for zeile in zeilen_ or []:
        text = str(zeile).strip()
        if text.startswith(f"({MESSEN} "):
            for wort in text.strip("()").split():
                if wort.startswith("KORR") and wort[4:].isdigit():
                    return int(wort[4:])
    return None


def korrektur_setzen(op, werkzeugnummer):
    """Schreibt „KORR…“ in die Zeile „(MESSEN …)“ des Messstopps `op` (None: weg)."""
    neu = []
    for zeile in list(op.Gcode):
        text = str(zeile)
        if text.strip().startswith(f"({MESSEN} "):
            woerter = [w for w in text.strip().strip("()").split() if not w.startswith("KORR")]
            if werkzeugnummer:
                woerter.append(f"KORR{int(werkzeugnummer)}")
            text = "(" + " ".join(woerter) + ")"
        neu.append(text)
    op.Gcode = neu


def merkmal_von(zeilen_):
    """(messen.Merkmal, Toleranz) aus den Zeilen eines Messstopps – None ohne Zeile „(MESSEN …)“."""
    from . import messen

    for zeile in zeilen_ or []:
        text = str(zeile).strip()
        if not text.startswith(f"({MESSEN} "):
            continue
        teile = text.strip("()").split()[1:]
        art, werte = teile[0], {}
        for teil in teile[1:]:
            name = teil.rstrip("0123456789.-")
            if name == "KORR":
                continue  # korrektur_von
            werte[name] = float(teil[len(name) :])
        if art not in messen.ARTEN:
            return None
        m = messen.Merkmal(
            art,
            werte["X"],
            werte["Y"],
            laenge_x=werte.get("LX", 0.0),
            laenge_y=werte.get("LY", 0.0),
            durchmesser=werte.get("D", 0.0),
            z_oben=werte.get("OBEN", werte["Z"]),
            z_mess=werte["Z"],
        )
        return m, werte.get("TOL", messen.TOLERANZ)
    return None


def lege_an(job, tc, danach, merkmal=None, toleranz=None):
    """Legt den Messstopp im Job an – ohne eigene Transaktion, die hält der Aufrufer – mit dem
    Controller `tc` der Operation davor; `danach`: der Controller, mit dem es weitergeht
    (Drehzahl, Richtung); `merkmal` (messen.Merkmal, schon mit dem Soll): was ein Taster dort
    messen würde. Gibt die Operation zurück."""
    from Path.Op import Custom

    FreeCAD.setActiveDocument(job.Document.Name)
    op = Custom.Create("Messstopp", parentJob=job)
    op.Label = tr("ms.name")
    op.ToolController = tc
    op.Source = "Text"
    drehzahl = float(getattr(danach, "SpindleSpeed", 0.0) or 0.0)
    kuehlung = str(getattr(getattr(job, "SetupSheet", None), "CoolantMode", "") or "")
    gcode = zeilen(sichere_hoehe(job), drehzahl, spindel.rueckwaerts(danach), kuehlung)
    if merkmal is not None:
        from . import messen

        gcode.insert(1, merkmal_zeile(merkmal, messen.TOLERANZ if toleranz is None else toleranz))
    op.Gcode = gcode
    return op


def ist_messstopp(op):
    """Ist `op` ein Messstopp des Addons?"""
    gcode = list(getattr(op, "Gcode", []) or [])
    return bool(gcode) and gcode[0] == KOMMENTAR
