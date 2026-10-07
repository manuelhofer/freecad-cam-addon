"""Freiform mit Mulde, Sattel und Erhebung: große Kugeln abweisen, passende Bahn prüfen.

Der Vergleich bleibt ohne Dokumentänderung; Übernahme, Rückgängig und Ablehnung
einer nach der Prüfung geänderten Operation werden an echten CAM-Objekten geprüft.
"""

import hashlib
import json
import os
import pathlib
import runpy
import sys
import tempfile
import time
import tracemalloc
from dataclasses import asdict

import numpy as np

ADDON = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON))

import FreeCAD as App
from Path.Tool.camassets import user_asset_store

from camaddon import angestellt as an
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import simultan_abtrag as sa
from camaddon import simultan_operation as so
from camaddon import simultan_planung as sp
from camaddon import sprache
from camaddon import vierachs_schlichten as vs


def pruefung():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    ordner = pathlib.Path(tempfile.mkdtemp())
    bauen = runpy.run_path(str(ADDON / "beispiele/grob_g550_freiform/erstellen.py"))["erstellen"]
    doc, bib = bauen(ordner)
    user_asset_store.set_dir(ordner / "assets")
    md = App.openDocument(str(ADDON / "beispiele/grob_g550_simultan/g550_winkelaufnahme.FCStd"))
    p = rw.Pruefung(md.Assembly, md.Maschine)
    op = doc.Schlichten3D
    vorher = sp._zustand(op)
    plan = None
    schreiben = os.environ.get("GOLDENE_BAHNEN_SCHREIBEN") == "1"
    speicher_messen = os.environ.get("SIMULTAN_SPEICHER_MESSEN") == "1"
    if speicher_messen:
        tracemalloc.start()
    beginn = time.monotonic()
    letztes = beginn

    def fortschritt(anteil):
        nonlocal letztes
        jetzt = time.monotonic()
        if jetzt - letztes > 30:
            print(
                "FORTSCHRITT",
                (
                    sys._getframe(2)
                    if sys._getframe(1).f_code.co_name == "_meldung"
                    else sys._getframe(1)
                ).f_code.co_name,
                f"{anteil*100:.0f} %",
                flush=True,
            )
            letztes = jetzt
        return True

    for aktueller_plan, variante in sp.vergleichen(
        op, p, bib, richtungen=("flaeche",), anstellungen=("frei",), fortschritt=fortschritt
    ):
        plan = aktueller_plan
        print("VARIANTE", variante.werkzeug.ToolNumber, variante.grund, flush=True)
    assert plan is not None and plan.beste is not None, "Keine geprüfte Freiformbahn"
    assert plan.beste.werkzeug.ToolNumber == 4, "Zu großer Fräser nicht ausgeschlossen"
    assert plan.beste.kollision_geprueft and not plan.beste.befunde
    assert plan.beste.rest <= float(op.Grathoehe)
    assert plan.beste.material_geprueft and not plan.beste.material.gruende
    assert plan.beste.material.ungedeckt == 0
    rechenzeit = time.monotonic() - beginn
    spitze_mb = tracemalloc.get_traced_memory()[1] / 1024**2 if speicher_messen else None
    if speicher_messen:
        tracemalloc.stop()
    print(
        "MESSUNG",
        json.dumps(
            {
                "material": asdict(plan.beste.material),
                "rechenzeit_s": rechenzeit,
                "spitzenspeicher_python_mb": spitze_mb,
            }
        ),
        flush=True,
    )
    assert plan.beste.schnittwinkel >= float(op.Anstellwinkel) - 1e-6
    assert sp._zustand(op) == vorher, "Vergleich hat Eingaben des Jobs geändert"
    try:
        sp.uebernehmen(op, sp.Planung())
    except ValueError:
        pass
    else:
        raise AssertionError("Ungeprüfte Variante übernommen")
    # Geänderte Halterdaten müssen die Übernahme ebenfalls sperren.
    original = bib.halter[0].name
    bib.halter[0].name += " geändert"
    bib.speichern()
    try:
        sp.uebernehmen(op, plan)
    except ValueError:
        pass
    else:
        raise AssertionError("Geänderte Halterbibliothek übernommen")
    bib.halter[0].name = original
    bib.speichern()
    sp.uebernehmen(op, plan)
    assert op.ToolController.ToolNumber == 4 and str(op.Kippachse) == "frei"
    assert op.Randgang and op.Anstellen and len(op.Werkzeugachsen) == len(op.Path.Commands)
    # Die übernommene und neu gerechnete Operation führt dieselbe Kugelmitte wie die geprüfte.
    aktuell = an.punkte(list(op.Path.Commands), [tuple(a) for a in op.Werkzeugachsen], 2.0)
    erwartet = an.punkte(
        list(plan.beste.operation.Path.Commands),
        [tuple(a) for a in plan.beste.operation.Werkzeugachsen],
        2.0,
    )
    assert len(aktuell) == len(erwartet), "Andere Bahn nach Übernahme"
    for a, b in zip(aktuell, erwartet, strict=True):
        assert max(abs(x - y) for x, y in zip(a.spitze, b.spitze, strict=True)) < 1e-6
        assert max(abs(x - y) for x, y in zip(a.achse, b.achse, strict=True)) < 1e-6
    maschine = sw.Maschine(
        p, p.werkzeugaufnahme(4), rw.einspannung(op.ToolController, bib), rw.nullpunkt(doc.Job)
    )
    befehle = so.befehle(op, maschine)

    def saetze(commands):
        return [
            (c.Name, sorted((k, round(float(v), 6)) for k, v in c.Parameters.items()))
            for c in commands
        ]

    assert saetze(befehle) == saetze(
        plan.beste.operation._pruefprogramm[1]
    ), "Anderes Maschinenprogramm nach Übernahme"
    werte = np.round(np.array([(*p.spitze, *p.achse, int(p.eilgang)) for p in aktuell]), 6)
    golden = ADDON / "tests/golden/freiform_simultan.json"
    ist = {
        "punkte": len(werte),
        "sha256": hashlib.sha256(werte.astype("<f8").tobytes()).hexdigest(),
        "zeit_s": plan.beste.sekunden,
        "rest_mm": plan.beste.rest,
        "befehle": len(befehle),
        "befehle_sha256": hashlib.sha256(json.dumps(saetze(befehle)).encode()).hexdigest(),
        "stichprobe": werte[::97].tolist(),
        "rechenzeit_s": rechenzeit,
        "spitzenspeicher_python_mb": spitze_mb,
    }
    if not schreiben:
        soll = json.loads(golden.read_text())
        assert ist["sha256"] == soll["sha256"], "Gespeicherte Referenzbahn verändert"
        assert (
            ist["befehle_sha256"] == soll["befehle_sha256"]
        ), "Gespeicherte Referenzbefehle verändert"
        assert ist["zeit_s"] <= soll["zeit_s"] * 1.005, "Zeitbestmarke überschritten"
        assert rechenzeit <= soll["rechenzeit_s"] * 2, "Laufbudget überschritten"
        if speicher_messen:
            assert (
                spitze_mb <= soll["spitzenspeicher_python_mb"] * 2
            ), "Speicherbudget überschritten"
    else:
        assert rechenzeit < 2400, "Erster Qualitätslauf überschreitet 40 Minuten"
    # Feinere Materialauflösung muss die Qualitätsgrenze ebenfalls halten.
    q = sa.Pruefstand(doc.Job, op, bib, raster=0.05)
    m = q.messen(
        sa._pfad(op),
        vs.form_des_controllers(op.ToolController),
        sa.einsatz_von(op.ToolController, bib),
        float(op.Grathoehe),
    )
    assert not m.gruende, m.gruende
    assert abs(m.rest + m.unsicherheit - plan.beste.rest) < 0.002, "Materialraster nicht konvergent"
    doc.undo()
    doc.recompute()
    assert op.ToolController.ToolNumber == 2 and not op.Anstellen and not op.Randgang
    op.Grathoehe = 0.03
    try:
        sp.uebernehmen(op, plan)
    except ValueError as grund:
        assert "geändert" in str(grund)
    else:
        raise AssertionError("Veraltete Prüfung übernommen")
    App.closeDocument(doc.Name)
    App.closeDocument(md.Name)
    if schreiben:
        golden.write_text(json.dumps(ist, indent=2) + "\n")


pruefung()
print("OK", os.path.basename(__file__))
