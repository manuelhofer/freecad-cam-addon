# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gespeicherte Werkzeugrichtungen mit 0/1/2 realen Rundachsen, niemals Ersatzbewegung."""

import json
import os
import pathlib
import sys
import time
import tracemalloc
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part
import Path
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import angestellt as an
from camaddon import beispielmaschine as bm
from camaddon import job_schnittwerte as js
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import simultan as si
from camaddon import simultan_operation as so
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz
from camaddon.kinematik import Kinematik


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    standard = wz.standardwerkzeug()
    standard.gesamtlaenge = 85
    # Die Kugel ist hier nötig: ihre Mitte bleibt beim Achswechsel am selben Ort.
    kugel = wz.Werkzeug.aus_dict(standard.als_dict())
    kugel.kennung, kugel.art = "richtungskugel12", wz.KUGELFRAESER
    kugel.eckradius = kugel.durchmesser / 2
    bib = wz.Bibliothek([kugel])
    bib.speichern()
    user_asset_store.set_dir(profil / "assets")
    ue.uebergeben(bib)
    doc = App.newDocument("Richtungsbahn")
    obj = doc.addObject("Part::Feature", "Teil")
    obj.Shape = Part.makeBox(20, 20, 10)
    job = PathJob.Create("Job", [obj])
    doc.recompute()
    einsatz = next(e for e in kugel.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    tc = js.controller_ohne_transaktion(doc, job, kugel, einsatz)
    doc.recompute()
    # Synthetische Richtungsgegenprobe; keine Qualifikation eines Zerspanungsfalls.
    cmds = [
        Path.Command("G0", {"X": 5, "Y": 5, "Z": 30}),
        Path.Command("G1", {"X": 6, "Y": 5, "Z": 25, "F": float(tc.HorizFeed)}),
        Path.Command("G1", {"X": 7, "Y": 5, "Z": 25, "F": float(tc.HorizFeed)}),
        Path.Command("G0", {"X": 7, "Y": 5, "Z": 30}),
    ]
    start = time.perf_counter()
    tracemalloc.start()
    ergebnisse = {}
    for art in bm.ARTEN:
        asm, ma = bm.lade(art)
        p = rw.Pruefung(asm, ma)
        auf = p.werkzeugaufnahme(int(tc.ToolNumber))
        ein = rw.einspannung(tc, bib)
        if art == bm.DREHMASCHINE:
            ein = rw.Einspannung(
                85, App.Placement(App.Vector(), App.Rotation(App.Vector(0, 1, 0), 45))
            )
        m = sw.Maschine(p, auf, ein, App.Vector())
        kin = Kinematik(p, auf, ein, App.Vector())
        lang = Kinematik(p, auf, rw.Einspannung(ein.laenge + 1, ein.lage), App.Vector())
        rund = [{a.buchstabe: t for a in m.rundachsen} for t in (0, 3, 6, 6)]
        achsen = [m.richtung(r) for r in rund]
        op = SimpleNamespace(
            Anstellen=True,
            Wegkippen=False,
            Werkzeugachsen=achsen,
            Path=Path.Path(cmds),
            Label="Richtungsbahn",
            ToolController=tc,
            InList=[],
            BahnGrathoehe=0,
        )
        source = [c.toGCode() for c in op.Path.Commands]
        befehle = so.befehle(op, m)
        soll = an.punkte(cmds, [tuple(a) for a in achsen], an.radius_von(op))
        g = [c for c in befehle if c.Name in ("G0", "G1") and all(k in c.Parameters for k in "XYZ")]
        # Kein Rohteil: keine zusätzlichen An-/Rückfahrten; diese vier Punkte werden gefahren.
        assert len(g) >= len(soll), (art, len(g), len(soll))
        # Verdichtete Zwischenpunkte dürfen vorkommen. Originale müssen in Reihenfolge passen.
        index = 0
        for c in g:
            values = c.Parameters
            r = {a.buchstabe: float(values[a.buchstabe]) for a in m.rundachsen}
            assert all(a.erlaubt(r[a.buchstabe]) for a in m.rundachsen)
            states = kin.stellungen(tuple(float(values[k]) for k in "XYZ"), r)
            assert states is not None, (art, values)
            tip = App.Vector(*kin.am_werkstueck(states))
            axis = tip - App.Vector(*lang.am_werkstueck(states))
            axis.normalize()
            center = tip + axis * an.radius_von(op)
            wanted = App.Vector(*si.bezugspunkt(soll[index], an.radius_von(op)))
            if (center - wanted).Length < 1e-5:
                assert (axis - App.Vector(*soll[index].achse)).Length < 1e-5
                index += 1
                if index == len(soll):
                    break
        assert index == len(soll), (art, index)
        assert not any(
            set(c.Parameters) & (set("ABC") - {a.buchstabe for a in m.rundachsen}) for c in befehle
        )
        if not m.rundachsen:
            assert len(g) == len(soll) and not any(
                c.Name == "G0" and not c.Parameters for c in befehle
            )
            bad = list(achsen)
            bad[1] = App.Vector(1, 0, 0)
            wrong = SimpleNamespace(**vars(op))
            wrong.Werkzeugachsen = bad
            try:
                so.befehle(wrong, m)
            except ValueError:
                pass
            else:
                raise AssertionError("Feste Spindel erfindet Kippung")
            ausgelassen, hinweis = pp._simultan(wrong, m)
            assert not ausgelassen and "unbearbeitet" in hinweis
            without, hint = pp._simultan(op, None)
            assert not without and "unbearbeitet" in hint
            # Auch eine tatsächlich gewinkelte feste Spindel fährt nur ihre realen XYZ.
            winkel = rw.Einspannung(
                85, App.Placement(App.Vector(8, -2, 3), App.Rotation(App.Vector(0, 1, 0), 90))
            )
            angled = sw.Maschine(p, auf, winkel, App.Vector())
            fixed = SimpleNamespace(**vars(op))
            fixed.Werkzeugachsen = [angled.richtung({})] * len(cmds)
            assert so.befehle(fixed, angled, tcpm=True)
        if art == bm.DREHMASCHINE:
            assert len(m.rundachsen) == 1
            c_values = [float(c.Parameters["C"]) for c in g]
            assert max(c_values) - min(c_values) > 1, c_values
            a = m.rundachsen[0]
            a.achse.gelenk.EnableAngleMin = True
            a.achse.gelenk.AngleMin = -2
            a.achse.gelenk.EnableAngleMax = True
            a.achse.gelenk.AngleMax = 2
            # Bei diesem Werkzeug ist C ein Pol; gewinkelte Aufnahme macht den Anschlag wirksam.
            angle = rw.Einspannung(
                85, App.Placement(App.Vector(), App.Rotation(App.Vector(0, 1, 0), 45))
            )
            limited = sw.Maschine(rw.Pruefung(asm, ma), auf, angle, App.Vector())
            requested = limited.richtung({a.buchstabe: 30})
            blocked = SimpleNamespace(**vars(op))
            blocked.Werkzeugachsen = [requested] * len(cmds)
            out, hint = pp._simultan(blocked, limited)
            assert not out and "unbearbeitet" in hint, (art, out, hint)
        assert source == [c.toGCode() for c in op.Path.Commands]
        ergebnisse[art] = {
            "rundachsen": len(m.rundachsen),
            "saetze": len(befehle),
            "punkte": len(soll),
        }
        print("SIMULTAN_MASCHINE", art, ergebnisse[art], flush=True)
        App.closeDocument(ma.Document.Name)
    dauer = time.perf_counter() - start
    speicher = tracemalloc.get_traced_memory()[1] / 1024**2
    tracemalloc.stop()
    assert dauer < 90 and speicher < 150, (dauer, speicher)
    print("ZEIT_S", dauer, "PYTHON_MIB", speicher, flush=True)
    if ausgabe := os.environ.get("CAMADDON_PRUEFAUSGABE"):
        pathlib.Path(ausgabe, "richtungen.json").write_text(
            json.dumps(
                {"maschinen": ergebnisse, "sekunden": dauer, "python_mib": speicher}, indent=2
            )
        )
    App.closeDocument(doc.Name)


pruefen()
print("OK", pathlib.Path(__file__).name, flush=True)
