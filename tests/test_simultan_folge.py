# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gemeinsame Materialfolge, tatsächlicher Export, unverändernder Vergleich und ein Undo."""

import hashlib
import json
import os
import sys
import time
import tracemalloc
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import angestellt as an
from camaddon import halter as hl
from camaddon import job_schnittwerte as js
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schlichten3d as s3
from camaddon import schruppen3d as r3
from camaddon import schwenken as sw
from camaddon import simultan_abtrag as sa
from camaddon import simultan_folge as sf
from camaddon import simultan_planung as sp
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_schlichten as vs
from camaddon import werkzeuge as wz


def aufbauen(profil):
    """Kleine erreichbare Kuppel mit Manuels Standardfräser und separater Kugel."""
    user_asset_store.set_dir(profil / "assets")
    w = wz.standardwerkzeug()
    w.gesamtlaenge = 85
    holder = hl.aus_vorlage("er25")
    w.halter = holder.kennung
    kugel = wz.Werkzeug.aus_dict(w.als_dict())
    kugel.kennung, kugel.nummer, kugel.name = "folge_kugel4", 4, "Kugel 4"
    kugel.art, kugel.durchmesser, kugel.eckradius = wz.KUGELFRAESER, 4, 2
    bib = wz.Bibliothek([w, kugel])
    bib.halter = [holder]
    bib.speichern()
    ue.uebergeben(bib)
    doc = App.newDocument("Gesamtfolge")
    doc.UndoMode = 1
    obj = doc.addObject("Part::Feature", "Kuppel")
    kappe = Part.makeSphere(40, App.Vector(10, 8, -25)).common(
        Part.makeBox(20, 16, 20, App.Vector(0, 0, 6))
    )
    obj.Shape = Part.makeBox(20, 16, 6).fuse(kappe).removeSplitter()
    doc.recompute()
    job = PathJob.Create("Job", [obj])
    alt = job.Stock
    stock = doc.addObject("Part::Feature", "Rohteil")
    stock.Shape = Part.makeBox(20, 16, 18)
    job.Stock = stock
    doc.removeObject(alt.Name)
    faces = [
        f"Face{i + 1}" for i, f in enumerate(obj.Shape.Faces) if isinstance(f.Surface, Part.Sphere)
    ]
    t1 = js.controller_ohne_transaktion(doc, job, w, w.schnittwerte[wz.ALLE][1])
    t4 = js.controller_ohne_transaktion(doc, job, kugel, kugel.schnittwerte[wz.ALLE][2])
    grob = r3.lege_an(job, t1, 25, 1.5, aufmass=0.3, flaechen=faces, zwischen=1)
    grob.Rampenanlauf, grob.Eintauchwinkel = True, 2.5
    op = s3.lege_an(job, t4, 0.02, flaechen=faces)
    doc.recompute()
    return doc, bib, grob, op


def pruefen():
    profil = Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    assert sf.zwischenlagen(2, 4, 1, 1.5) == (1.5, 2, 3, 4)
    for werte in [(0, 4, 1, 3), (2, 1, 1, 3), (1, 4, 0, 3), (1, 4, float("nan"), 3)]:
        try:
            sf.zwischenlagen(*werte)
        except ValueError:
            pass
        else:
            raise AssertionError("Ungültiger Suchbereich akzeptiert")
    doc, bib, grob, op = aufbauen(profil)
    md = App.openDocument(str(ROOT / "beispiele/grob_g550_simultan/g550_winkelaufnahme.FCStd"))
    p = rw.Pruefung(md.Assembly, md.Maschine)
    vorher = sp._zustand(op)
    originale_lage = float(grob.Zwischenlagen)
    plan = None
    beginn, letztes = time.monotonic(), time.monotonic()

    def fortschritt(anteil):
        nonlocal letztes
        jetzt = time.monotonic()
        if jetzt - letztes > 25:
            print("FORTSCHRITT", f"{anteil * 100:.0f} %", flush=True)
            letztes = jetzt
        return True

    tracemalloc.start()
    for aktueller_plan, v in sf.vergleichen(
        op, p, bib, (1, 2, 3), richtungen=("x",), fortschritt=fortschritt
    ):
        plan = aktueller_plan
        print("FOLGE", v.zwischenlagen, v.richtung, v.anstellung, v.grund or v.sekunden, flush=True)
    laufzeit = time.monotonic() - beginn
    spitze = tracemalloc.get_traced_memory()[1] / 1024**2
    tracemalloc.stop()
    assert plan is not None and plan.vollstaendig and plan.beste is not None
    assert sp._zustand(op) == vorher, "Vergleich verändert den Ausgangsjob"
    assert {v.zwischenlagen for v in plan.varianten} == {1, 2, 3}
    beste = plan.beste
    assert beste.material_geprueft and beste.kollision_geprueft and not beste.material.gruende
    assert beste.sekunden == min(v.sekunden for v in plan.varianten if not v.grund)
    # Auch ein schon geprüfter früher Zweig ist erst nach Abschluss der Suche übernehmbar.
    try:
        sp.uebernehmen(op, replace(plan, vollstaendig=False))
    except ValueError:
        pass
    else:
        raise AssertionError("Unvollständige Gesamtplanung übernommen")
    # Geänderte Schruppwerte ohne Neuberechnung: der alte Pfad allein wäre kein Schutz.
    grob.Zwischenlagen = originale_lage + 0.125
    try:
        sp.uebernehmen(op, plan)
    except ValueError:
        pass
    else:
        raise AssertionError("Geänderte Schrupp-Eingaben übernommen")
    grob.Zwischenlagen = originale_lage
    # Fehler nach dem Schreiben beider Einstellungen muss den ganzen Klick zurückrollen.
    kaputt = sp._Ansicht(beste.schruppoperation, Path=type(grob.Path)([]))
    falscher_plan = replace(plan, beste=replace(beste, schruppoperation=kaputt))
    try:
        sp.uebernehmen(op, falscher_plan)
    except ValueError:
        pass
    else:
        raise AssertionError("Abweichende Schruppbahn übernommen")
    assert sp._zustand(op) == vorher, "Abbruch lässt einen halb geänderten Job zurück"
    sp.uebernehmen(op, plan)
    assert abs(float(grob.Zwischenlagen) - beste.zwischenlagen) < 1e-9
    assert grob.Rampenanlauf and op.Anstellen and op.Randgang

    def maschine(operation):
        tc = operation.ToolController
        return sw.Maschine(
            p, p.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, bib), rw.nullpunkt(doc.Job)
        )

    steuerung, info = pp.steuerung("siemens"), pp.maschineninfo_dokument(md)
    wirklich = pp.programm(pp.abschnitte(doc.Job, maschine), steuerung, info, "GESAMTFOLGE")
    erwartet = pp.programm(pp.abschnitte(beste.job, maschine), steuerung, info, "GESAMTFOLGE")
    assert wirklich.text == erwartet.text, "Tatsächlicher Export weicht von der geprüften Folge ab"
    befunde, saetze = pp.nachlesen(wirklich, steuerung, info)
    assert not befunde, befunde
    # Material unabhängig am echten, neu berechneten Job und mit feinerem Raster prüfen.
    q = sa.Pruefstand(doc.Job, op, bib, raster=0.05)
    assert not any(m.gruende for _name, m in q.vorher)
    m = q.messen(
        sa._pfad(op),
        vs.form_des_controllers(op.ToolController),
        sa.einsatz_von(op.ToolController, bib),
        float(op.Grathoehe) - sa.NC_RESERVE,
    )
    assert not m.gruende, m.gruende
    aktuell = an.punkte(list(op.Path.Commands), [tuple(a) for a in op.Werkzeugachsen], 2)
    ist = {
        "zwischenlagen_mm": beste.zwischenlagen,
        "richtung": beste.richtung,
        "anstellung": beste.anstellung,
        "sekunden": beste.sekunden,
        "punkte": len(aktuell),
        "nc_sha256": hashlib.sha256(wirklich.text.encode()).hexdigest(),
        "nc_saetze": saetze,
        "laufzeit_s": laufzeit,
        "spitzenspeicher_python_mb": spitze,
    }
    golden = ROOT / "tests/golden/simultan_folge.json"
    if os.environ.get("FOLGE_GOLDEN_SCHREIBEN") == "1":
        assert laufzeit < 600 and spitze < 500
        golden.write_text(json.dumps(ist, indent=2) + "\n")
    else:
        soll = json.loads(golden.read_text())
        for name in (
            "zwischenlagen_mm",
            "richtung",
            "anstellung",
            "punkte",
            "nc_sha256",
            "nc_saetze",
        ):
            assert ist[name] == soll[name], f"Referenz verändert: {name}"
        assert beste.sekunden <= soll["sekunden"] * 1.005
        # Die Laufzeit ist Information (MESSUNG unten), keine Prüfung: Sie hängt am Rechner
        # und an der Last. Der Speicher bleibt geprüft.
        assert spitze <= soll["spitzenspeicher_python_mb"] * 2
    print("MESSUNG", json.dumps(ist), flush=True)
    (profil / "folge.mpf").write_text(wirklich.text)
    doc.saveAs(str(profil / "folge.FCStd"))
    doc.undo()
    doc.recompute()
    assert float(grob.Zwischenlagen) == originale_lage and not op.Anstellen and not op.Randgang
    assert sp._zustand(op) == vorher, "Einmal Rückgängig stellt nicht beide Operationen wieder her"
    try:
        next(sf.vergleichen(op, p, bib, (1, 2, 3), fortschritt=lambda _anteil: False))
    except ValueError:
        pass
    else:
        raise AssertionError("Abbrechen ignoriert")
    assert sp._zustand(op) == vorher
    App.closeDocument(doc.Name)
    App.closeDocument(md.Name)


pruefen()
print("OK", Path(__file__).name)
