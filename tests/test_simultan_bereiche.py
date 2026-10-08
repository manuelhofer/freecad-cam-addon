# SPDX-License-Identifier: LGPL-2.1-or-later
"""Native Teilbahn: unerreichbarer mittlerer Zug, echte NC, Rest und gesperrte Verbindung."""

import hashlib
import json
import os
import pathlib
import sys
import time
import tracemalloc

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part
import Path
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import angestellt as an
from camaddon import beispielmaschine as bm
from camaddon import halter as hl
from camaddon import job_schnittwerte as js
from camaddon import kollision as kb
from camaddon import maschinenzugang as mz
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schlichten3d as s3
from camaddon import schwenken as sw
from camaddon import simultan_abtrag as sa
from camaddon import simultan_bereiche as sb
from camaddon import simultan_operation as so
from camaddon import simultan_restbild as sr
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_schlichten as vs
from camaddon import werkzeuge as wz


def aufbauen(profil):
    """Drei getrennte Kugel-Schlichtzüge; Standard D12 bleibt der Werkzeugmaßstab."""
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    user_asset_store.set_dir(profil / "assets")
    w = wz.standardwerkzeug()
    w.gesamtlaenge = 85
    holder = hl.aus_vorlage("er25")
    w.halter = holder.kennung
    kugel = wz.Werkzeug.aus_dict(w.als_dict())
    kugel.kennung, kugel.art, kugel.eckradius = "bereiche_kugel12", wz.KUGELFRAESER, 6
    bib = wz.Bibliothek([w, kugel])
    bib.halter = [holder]
    bib.speichern()
    ue.uebergeben(bib)
    asm, ma = bm.lade(bm.FRAESE_3)
    doc = App.newDocument("SimultanTeilbereiche")
    obj = doc.addObject("Part::Feature", "Teil")
    obj.Shape = Part.makeBox(40, 60, 10)
    job = PathJob.Create("Job", [obj])
    doc.recompute()
    alt = job.Stock
    stock = doc.addObject("Part::Feature", "Rohteil")
    stock.Shape = Part.makeBox(40, 60, 11.2)
    job.Stock = stock
    doc.removeObject(alt.Name)
    einsatz = next(e for e in kugel.schnittwerte[wz.ALLE] if e.art == wz.SCHLICHTEN)
    tc = js.controller_ohne_transaktion(doc, job, kugel, einsatz)
    doc.recompute()
    op = s3.lege_an(job, tc, 0.02, flaechen=["Face6"])
    doc.recompute()
    op.Anstellen = True
    op.BahnGrathoehe = 0.02
    # Die Maschine ist fest: nur die mittlere gespeicherte Richtung ist unmöglich.
    p = rw.Pruefung(asm, ma)
    m = sw.Maschine(p, p.werkzeugaufnahme(1), rw.einspannung(tc, bib), App.Vector())
    cmds, axes = [], []
    for y in (10, 30, 50):
        for name, x, z in (("G0", -8, 30), ("G1", -8, 10), ("G1", 48, 10), ("G0", 48, 30)):
            vals = {"X": x, "Y": y, "Z": z}
            if name == "G1":
                vals["F"] = float(tc.HorizFeed)
            cmds.append(Path.Command(name, vals))
            axes.append(App.Vector(1, 0, 1) if y == 30 and name == "G1" else App.Vector(0, 0, 1))
            axes[-1].normalize()
    op.Path, op.Werkzeugachsen = Path.Path(cmds), axes
    # Keine Nachrechnung: hier prüfen wir gespeicherte native Bahndaten und ihre Adapter.
    return doc, job, op, bib, m


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    doc, job, op, bib, m = aufbauen(profil)
    start = time.perf_counter()
    tracemalloc.start()
    source = [c.toGCode() for c in op.Path.Commands]
    axes = [tuple(a) for a in op.Werkzeugachsen]
    try:
        an.befehle(op, m)
    except ValueError:
        print("GEGENPROBE: bisheriger Adapter verwirft alle drei Schnittzüge", flush=True)
    else:
        raise AssertionError("Gegenprobe benötigt unerreichbaren mittleren Zug")
    result = so.programm(op, m)
    assert [n for n, _ in result.ausgelassen] == [2], result.hinweis
    assert "unbearbeitet" in result.hinweis
    assert not mz.bahn_grund(m, result.befehle)
    nc = pp.programm(
        pp.abschnitte(job, m), pp.steuerung("linuxcnc"), pp.Maschineninfo(), "TEILBEREICHE"
    )
    befunde, saetze = pp.nachlesen(nc, pp.steuerung("linuxcnc"), pp.Maschineninfo())
    assert not befunde, befunde
    assert "unbearbeitet" in " ".join(nc.hinweise)
    grenzen = m.pruefung.pruefe_job(job, App.Vector(), bib)
    assert any("Schnittzug 2" in str(h) for h in grenzen.hinweise), grenzen.hinweise
    f = ab.abfahrt(m.pruefung, job, App.Vector(), bib)
    assert len(f.operationen) == 1 and any("Schnittzug 2" in s for s in f.hinweise)
    bild = sr.fuer(f, job, f.am_werkstueck())
    assert bild is not None
    bild.bis_station(bild.letzte())
    q = bild.quader
    ix = abs(q.x - 20).argmin()
    h = [float(q.h[ix, abs(q.y - y).argmin()]) for y in (10, 30, 50)]
    assert h[0] < 11.2 and h[1] == 11.2 and h[2] < 11.2, h
    # Unabhängige Materialmessung der tatsächlichen NC; weder Einschnitt noch G0-Abtrag.
    actual = sa.maschinenbahn(f, 0, 6)
    from camaddon import restmaterial as rm

    fein = rm.Quader(0, 40, 0, 60, 0, 11.2, 0.05)
    einsatz = sa.einsatz_von(op.ToolController, bib)
    messung = sa.fahren(
        fein, actual, vs.form_des_controllers(op.ToolController), einsatz.ae, einsatz.ap
    )
    assert messung.eilgang_abtrag == 0 and messung.schnell_abtrag == 0, vars(messung)
    assert messung.last_max <= einsatz.ae * einsatz.ap, vars(messung)
    assert sa.einschnitt(job.Model.Group[0].Shape, actual, 6) >= -1e-7
    collision = kb.kollision(f, job, App.Vector(), bib)
    assert not (
        collision.abgebrochen or collision.hinweise or collision.befunde
    ), collision.hinweise
    # Ein modaler Vorschubwechsel im ausgelassenen Zug gilt auch im nächsten Zug.
    modal = list(op.Path.Commands)
    modal[5] = Path.Command(
        "G1", {**modal[5].Parameters, "F": float(op.ToolController.HorizFeed) / 2}
    )
    for i in (6, 9, 10):
        modal[i] = Path.Command("G1", {k: v for k, v in modal[i].Parameters.items() if k != "F"})
    pts, _ = sb._punkte(sb._Ansicht(op, Path=Path.Path(modal)))
    assert pts[9].vorschub == float(op.ToolController.HorizFeed) / 2
    # Alle sechs tatsächlichen Kinematiken, einschließlich drehender Verbindungen.
    maschinen = {}
    for art in bm.ARTEN:
        if art == bm.GROB_G550:
            # Vorhandene qualifizierte Winkelaufnahme; die flache Aufspannung
            # kollidiert am G550-Modell bei dieser Rückfahrt (B-015).
            md = App.openDocument(
                str(ROOT / "beispiele/grob_g550_simultan/g550_winkelaufnahme.FCStd")
            )
            asm, ma = md.Assembly, md.Maschine
        else:
            asm, ma = bm.lade(art)
        p = rw.Pruefung(asm, ma)
        real = sw.Maschine(
            p, p.werkzeugaufnahme(1), rw.einspannung(op.ToolController, bib), App.Vector()
        )
        original = list(op.Path.Commands)
        orientations = []
        if len(real.rundachsen) >= 2:
            ar = next(
                a
                for a in real.rundachsen
                if (real.richtung({a.buchstabe: 30}) - real.richtung({})).Length > 0.1
            )
            for t in (3, 30, -3):
                orientations.extend([real.richtung({ar.buchstabe: t})] * 4)
            ar.achse.gelenk.EnableAngleMin = ar.achse.gelenk.EnableAngleMax = True
            ar.achse.gelenk.AngleMin, ar.achse.gelenk.AngleMax = -5, 5
            real = sw.Maschine(
                rw.Pruefung(asm, ma), p.werkzeugaufnahme(1), real.laenge, App.Vector()
            )
        else:
            orientations = [real.richtung({})] * len(original)
            original[6] = Path.Command("G1", {**original[6].Parameters, "X": 10000})
        view = sb._Ansicht(op, Path=Path.Path(original), Werkzeugachsen=orientations)
        teil = so.programm(view, real)
        assert [n for n, _ in teil.ausgelassen] == [2], (art, teil.hinweis)
        assert not mz.bahn_grund(real, teil.befehle)
        if real.rundachsen:
            try:
                so.programm(view, real, tcpm=True)
            except ValueError:
                pass
            else:
                raise AssertionError("TCPM gibt ausgelassene Bereiche wieder aus")
        maschinen[art] = len(teil.befehle)
        print("TEILMASCHINE", art, len(teil.befehle), flush=True)
        App.closeDocument(ma.Document.Name)
    # Eine Wand nur im übersprungenen Zwischenraum sperrt die neu entstandene Verbindung.
    alt = job.Stock.Shape
    job.Stock.Shape = alt.fuse(Part.makeBox(56, 8, 50, App.Vector(-8, 27, 0)))
    blocked, hint = pp._simultan(op, m)
    assert not blocked and "unbearbeitet" in hint, hint
    job.Stock.Shape = alt
    assert source == [c.toGCode() for c in op.Path.Commands]
    assert axes == [tuple(a) for a in op.Werkzeugachsen]
    # Keine Trennung mitten im Schnitt, auch wenn einzelne Endpunkte erreichbar wären.
    view = sb._Ansicht(
        op, Path=Path.Path(op.Path.Commands[1:3]), Werkzeugachsen=op.Werkzeugachsen[1:3]
    )
    try:
        sb.teilen(view, m, "nicht trennbar")
    except ValueError:
        pass
    else:
        raise AssertionError("Ungeprüfte Einfahrt mitten im Material")
    bild.bis_station(0)
    assert (q.h == 11.2).all(), "Zurückspulen verliert ursprüngliches Rohteil"
    bild.bis_station(bild.letzte())
    seconds = time.perf_counter() - start
    memory = tracemalloc.get_traced_memory()[1] / 1024**2
    tracemalloc.stop()
    assert seconds < 120 and memory < 250, (seconds, memory)
    report = {
        "nc_saetze": saetze,
        "sha256": hashlib.sha256(nc.text.encode()).hexdigest(),
        "resthoehen": h,
        "sekunden": seconds,
        "python_mib": memory,
        "bearbeitung_s": f.dauer,
        "maschinen": maschinen,
    }
    referenz = json.loads((ROOT / "tests/golden/simultan_bereiche.json").read_text())
    for key in ("nc_saetze", "sha256", "maschinen"):
        assert report[key] == referenz[key], f"Teilbahn-Referenz verändert: {key}"
    assert all(abs(a - b) < 1e-8 for a, b in zip(h, referenz["resthoehen"], strict=True))
    assert f.dauer <= referenz["bearbeitung_s"] * 1.005
    assert seconds <= referenz["sekunden"] * 2 and memory <= referenz["python_mib"] * 2
    if out := os.environ.get("CAMADDON_PRUEFAUSGABE"):
        pathlib.Path(out, "teilbereiche.json").write_text(json.dumps(report, indent=2))
        pathlib.Path(out, "teilbereiche.ngc").write_text(nc.text)
    print("TEILBEREICHE", report, flush=True)
    App.closeDocument(doc.Name)
    App.closeDocument(m.pruefung.maschine.Document.Name)


if __name__ != "teilbereiche_fixture":
    pruefen()
    print("OK", pathlib.Path(__file__).name, flush=True)
