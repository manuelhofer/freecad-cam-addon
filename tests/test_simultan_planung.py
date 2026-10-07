"""Freiform mit Mulde, Sattel und Erhebung: große Kugeln abweisen, passende Bahn prüfen.

Der Vergleich bleibt ohne Dokumentänderung; Übernahme, Rückgängig und Ablehnung
einer nach der Prüfung geänderten Operation werden an echten CAM-Objekten geprüft.
"""

import os
import pathlib
import runpy
import sys
import tempfile

ADDON = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON))

import FreeCAD as App
from Path.Tool.camassets import user_asset_store

from camaddon import angestellt as an
from camaddon import reichweite as rw
from camaddon import simultan_planung as sp
from camaddon import sprache


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
    for aktueller_plan, variante in sp.vergleichen(
        op, p, bib, richtungen=("x",), anstellungen=("frei",)
    ):
        plan = aktueller_plan
        print("VARIANTE", variante.werkzeug.ToolNumber, variante.grund, flush=True)
    assert plan is not None and plan.beste is not None, "Keine geprüfte Freiformbahn"
    assert plan.beste.werkzeug.ToolNumber == 4, "Zu großer Fräser nicht ausgeschlossen"
    assert plan.beste.kollision_geprueft and not plan.beste.befunde
    assert plan.beste.rest <= float(op.Grathoehe) + sp.GENAU
    assert plan.beste.schnittwinkel >= float(op.Anstellwinkel) - 0.05
    assert sp._zustand(op) == vorher, "Vergleich hat Eingaben des Jobs geändert"
    try:
        sp.uebernehmen(op, sp.Planung())
    except ValueError:
        pass
    else:
        raise AssertionError("Ungeprüfte Variante übernommen")
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


pruefung()
print("OK", os.path.basename(__file__))
