# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gemeinsamer Export: fremde Rundachsen, echte Grenzen und innere Bogenextrema."""

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part
import Path
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import job_schnittwerte as js
from camaddon import maschinenzugang as mz
from camaddon import materialstand as ms
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz
from camaddon.kinematik import Kinematik


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    w = wz.standardwerkzeug()
    w.gesamtlaenge = 85
    bib = wz.Bibliothek([w])
    bib.speichern()
    user_asset_store.set_dir(profil / "assets")
    ue.uebergeben(bib)
    e = next(e for e in w.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    doc = App.newDocument("Bahnzugang")
    obj = doc.addObject("Part::Feature", "Teil")
    obj.Shape = Part.makeBox(20, 20, 10)
    job = PathJob.Create("Job", [obj])
    doc.recompute()
    tc = js.controller_ohne_transaktion(doc, job, w, e)
    doc.recompute()
    op = doc.addObject("Path::Feature", "Bahn")
    op.addProperty("App::PropertyLink", "ToolController")
    op.ToolController = tc
    op.addProperty("App::PropertyBool", "Active")
    op.Active = True
    job.Operations.Group = [op]
    source = [
        Path.Command("G0", {"X": -8, "Y": 10, "Z": 11}),
        Path.Command("G1", {"X": 28, "Y": 10, "Z": 11, "F": float(tc.HorizFeed)}),
    ]
    op.Path = Path.Path(source)
    for art in bm.ARTEN:
        asm, ma = bm.lade(art)
        p = rw.Pruefung(asm, ma)
        m = sw.Maschine(p, p.werkzeugaufnahme(1), rw.einspannung(tc, bib), App.Vector())
        valid = pp.abschnitte(job, m)[0]
        assert not valid.hinweis and [c.toGCode() for c in valid.befehle] == [
            c.toGCode() for c in source
        ], (art, valid.hinweis)
        foreign = next(a for a in "ABC" if a not in {r.buchstabe for r in m.rundachsen})
        bad = [source[0], Path.Command("G1", {**source[1].Parameters, foreign: 30})]
        op.Path = Path.Path(bad)
        out = pp.abschnitte(job, m)[0]
        assert not out.befehle and "unbearbeitet" in out.hinweis and foreign in out.hinweis
        fahrt = ab.abfahrt(p, job, App.Vector(), bib)
        assert (
            not fahrt.operationen
            and not fahrt.stationen
            and any("unbearbeitet" in h for h in fahrt.hinweise)
        ), "Abspieler fährt eine im Export ausgelassene Operation"
        op.Path = Path.Path(source)
        if art == bm.FRAESE_3:
            kin = Kinematik(p, m.aufnahme, m.laenge, m.nullpunkt)
            states = {
                a: (
                    (a.minimum + a.maximum) / 2
                    if a.minimum is not None and a.maximum is not None
                    else 0
                )
                for a in m.linear
            }
            ix = next(
                i
                for i, a in enumerate(m.linear)
                if abs(p.loeser(m.aufnahme, m.laenge, m.nullpunkt)({})[0].s[i][0]) > 0.9
            )
            ax = m.linear[ix]
            states[ax] = ax.maximum - 5
            center = kin.programm(states)
            solved, _ = kin._loesung({})
            turn = "G3" if solved.s[ix][0] > 0 else "G2"
            arc = [
                Path.Command("G0", {"X": center[0], "Y": center[1] - 10, "Z": center[2]}),
                Path.Command(
                    turn,
                    {
                        "X": center[0],
                        "Y": center[1] + 10,
                        "Z": center[2],
                        "I": 0,
                        "J": 10,
                        "F": float(tc.HorizFeed),
                    },
                ),
            ]
            assert not mz.bahn_grund(m, [arc[0]])
            assert not mz.bahn_grund(
                m,
                [
                    Path.Command(
                        "G0", dict(zip("XYZ", (center[0], center[1] + 10, center[2]), strict=True))
                    )
                ],
            )
            assert mz.bahn_grund(m, arc), "Innere Kreisextrema nicht geprüft"
            datei = str(profil / "maschine3.FCStd")
            ma.Document.saveAs(datei)
            rw.merke_maschine(job, datei)
            # Eine ungültige vorangehende Bahn darf keine Materialhöhe senken.
            op.Path = Path.Path(
                [
                    source[0],
                    Path.Command(
                        "G1", {"X": 28, "Y": 10, "Z": 9, "A": 30, "F": float(tc.HorizFeed)}
                    ),
                ]
            )
            before = ms.fuer(job)
            assert before is not None
            automatisch = pp.abschnitte(job)[0]
            assert not automatisch.befehle and "unbearbeitet" in automatisch.hinweis
            assert before.quader.h.min() >= job.Stock.Shape.BoundBox.ZMax - 1e-8
            key = ms.kennung_vor(job, None)
            op.Path = Path.Path(
                [
                    source[0],
                    Path.Command("G1", {"X": 28, "Y": 10, "Z": 9, "F": float(tc.HorizFeed)}),
                ]
            )
            after = ms.fuer(job)
            assert after.quader.h.min() < before.quader.h.min() - 1
            assert ms.kennung_vor(job, None) != key
            rw.merke_maschine(job, str(profil / "fehlt.FCStd"))
            fehlend = pp.abschnitte(job)[0]
            assert not fehlend.befehle and "unbearbeitet" in fehlend.hinweis
            job.CamAddonMaschine = ""
            op.Path = Path.Path(source)
        if art == bm.DREHMASCHINE:
            r = m.rundachsen[0]
            r.achse.gelenk.EnableAngleMin = True
            r.achse.gelenk.AngleMin = -10
            r.achse.gelenk.EnableAngleMax = True
            r.achse.gelenk.AngleMax = 10
            from camaddon import maschine as mm

            for mode in mm.betriebsarten(ma):
                if mode.Gelenk == r.achse.gelenk and mode.Art == mm.ART_POSITIONIEREN:
                    mode.Endlos = False
            limited = sw.Maschine(rw.Pruefung(asm, ma), m.aufnahme, m.laenge, m.nullpunkt)
            assert mz.bahn_grund(
                limited, [Path.Command("G0", {"C": 30})]
            ), "Schwenken vor bekannter XYZ-Lage ignoriert die Grenze"
            assert mz.bahn_grund(
                limited,
                [Path.Command("G91"), Path.Command("G0", {"C": 6}), Path.Command("G0", {"C": 6})],
            ), "Relative Schwenkbewegungen überschreiten unbemerkt die Grenze"
            op.Path = Path.Path([source[0], Path.Command("G1", {**source[1].Parameters, "C": 30})])
            out = pp.abschnitte(job, limited)[0]
            assert not out.befehle and "unbearbeitet" in out.hinweis
            op.Path = Path.Path(source)
        print("BAHNZUGANG", art, "OK", flush=True)
        App.closeDocument(ma.Document.Name)
    App.closeDocument(doc.Name)


pruefen()
print("OK", pathlib.Path(__file__).name, flush=True)
