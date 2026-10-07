# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Beispiel vollständig vergleichen, geprüft übernehmen und mit Bericht neu speichern.

Mit FreeCADCmd in einem vorher angelegten eigenen FREECAD_USER_HOME ausführen.
Die Bibliothek wird dort gespeichert; die Beispieldateien liegen neben diesem Skript.
"""

import json
import math
import os
import runpy
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def pruefen():
    """45 Varianten, Gewinner, Maschinenprogramm und reproduzierbare Beispieldateien."""
    import FreeCAD as App

    from camaddon import postprozessor as pp
    from camaddon import reichweite as rw
    from camaddon import schwenken as sw
    from camaddon import simultan_planung as sp
    from camaddon import sprache

    profil = Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    out = Path(__file__).resolve().parent
    doc, bib = runpy.run_path(str(out / "erstellen.py"))["erstellen"](out)
    md = App.openDocument(str(out / "g550_winkelaufnahme.FCStd"))
    p = rw.Pruefung(md.Assembly, md.Maschine)
    op = doc.Schlichten3D
    rw.merke_maschine(doc.Job, md.FileName)
    start = time.monotonic()
    plan = None
    for aktueller_plan, variante in sp.vergleichen(op, p, bib):
        plan = aktueller_plan
        print(
            "VARIANTE",
            variante.werkzeug.ToolNumber,
            variante.richtung,
            variante.anstellung,
            variante.grund or f"{variante.sekunden:.3f} s",
            flush=True,
        )
    assert (
        plan is not None and plan.beste is not None
    ), "Keine material- und kollisionsgeprüfte Bahn"
    beste = plan.beste
    assert len(plan.varianten) == 45
    assert beste.sekunden == min(
        v.sekunden for v in plan.varianten if not v.grund and math.isfinite(v.sekunden)
    )
    daten = [
        {
            "werkzeug": v.werkzeug.ToolNumber,
            "richtung": v.richtung,
            "anstellung": v.anstellung,
            "sekunden": v.sekunden if math.isfinite(v.sekunden) else None,
            "rest_mm": v.rest if math.isfinite(v.rest) else None,
            "kontaktwinkel_grad": v.schnittwinkel,
            "material_geprueft": v.material_geprueft,
            "kollision_geprueft": v.kollision_geprueft,
            "grund": v.grund,
        }
        for v in plan.varianten
    ]
    sp.uebernehmen(op, plan)

    def maschine(operation):
        tc = operation.ToolController
        return sw.Maschine(
            p, p.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, bib), rw.nullpunkt(doc.Job)
        )

    abschnitte = pp.abschnitte(beste.job, maschine)
    steuerung = pp.steuerung("siemens")
    info = pp.maschineninfo_dokument(md)
    programm = pp.programm(abschnitte, steuerung, info, "G550_FREIFORM")
    befunde, saetze = pp.nachlesen(programm, steuerung, info)
    assert not befunde, befunde
    bericht = {
        "varianten": daten,
        "werkzeug": beste.werkzeug.ToolNumber,
        "richtung": beste.richtung,
        "anstellung": beste.anstellung,
        "sekunden": beste.sekunden,
        "rest_mm": beste.rest,
        "kontaktwinkel_grad": beste.schnittwinkel,
        "flaechenzellen": beste.material.flaechenzellen,
        "ungedeckte_zellen": beste.material.ungedeckt,
        "luftanteil": beste.material.luftanteil,
        "last_max_mm2": beste.material.last_max,
        "material": asdict(beste.material),
        "nc_saetze": saetze,
        "laufzeit_s": time.monotonic() - start,
    }
    (out / "vergleich.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n")
    (out / "beispiel_werkzeuge.json").write_text(
        json.dumps(bib.als_dict(), ensure_ascii=False, indent=2) + "\n"
    )
    (out / "freiform_5achs.mpf").write_text(programm.text)
    doc.recompute()
    doc.saveAs(str(out / "freiform_5achs.FCStd"))
    App.closeDocument(doc.Name)
    App.closeDocument(md.Name)
    print(
        "OK pruefen.py",
        json.dumps(bericht | {"varianten": len(daten)}, ensure_ascii=False),
        flush=True,
    )


pruefen()
