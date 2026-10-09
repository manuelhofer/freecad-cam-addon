# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ein Simultanzug mit innerer Sperre: echte NC, materialfreie Grenzen und unverändertes Reststück."""

import hashlib
import json
import os
import pathlib
import runpy
import sys
import time
import tracemalloc

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part
import Path

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import kollision as kb
from camaddon import maschinenzugang as mz
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import simultan_abtrag as sa
from camaddon import simultan_bereiche as sb
from camaddon import simultan_operation as so
from camaddon import simultan_restbild as sr
from camaddon import simultan_schnittbereiche as ss
from camaddon import vierachs_schlichten as vs


def aufbauen(profil):
    """Die vorhandene D12-Kugelgegenprobe als einzelner zusammenhängender Vorschubzug."""
    fixture = runpy.run_path(
        str(ROOT / "tests/test_simultan_bereiche.py"), run_name="teilbereiche_fixture"
    )
    doc, job, op, bib, m = fixture["aufbauen"](profil)
    # Die neue Einfahrt wird ausdrücklich mit bekannten Maßen qualifiziert;
    # die gewöhnliche Vorschau schätzt beim Standardwerkzeug sonst den Schaft.
    for werkzeug in bib.werkzeuge:
        werkzeug.schaft = werkzeug.durchmesser
    bib.speichern()
    cmds = list(op.Path.Commands)
    for i in range(1, len(cmds) - 1):
        cmds[i] = Path.Command("G1", dict(cmds[i].Parameters))
    op.Path = Path.Path(cmds)
    return doc, job, op, bib, m


def fahren(job, op, m, bib):
    """Tatsächliche NC abfahren und Materialendstand aus dieser Ausgabe lesen."""
    f = ab.abfahrt(m.pruefung, job, m.nullpunkt, bib)
    assert f.stationen and len(f.operationen) == 1 and f.hinweise, (
        len(f.stationen),
        len(f.operationen),
        f.hinweise,
    )
    bild = sr.fuer(f, job, f.am_werkstueck())
    assert bild is not None
    bild.bis_station(bild.letzte())
    q = bild.quader
    h = [float(q.h[abs(q.x - 20).argmin(), abs(q.y - y).argmin()]) for y in (10, 30, 50)]
    return f, h, bild


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    start = time.perf_counter()
    tracemalloc.start()
    doc, job, op, bib, m = aufbauen(profil)
    original = list(op.Path.Commands)
    source = [c.toGCode() for c in original]
    axes = list(op.Werkzeugachsen)
    assert len(sb._zuege(sb._punkte(op)[0])) == 1
    result = so.programm(op, m)
    assert result.ausgelassen and "Bahnpunkt 5 und 8" in result.hinweis, result.hinweis
    assert not mz.bahn_grund(m, result.befehle)
    assert len(result.materialdaten) == len(result.befehle)
    assert sum(e for e, _f in result.materialdaten) > 2
    nc = pp.programm(
        pp.abschnitte(job, m), pp.steuerung("linuxcnc"), pp.Maschineninfo(), "SCHNITTBEREICHE"
    )
    befunde, saetze = pp.nachlesen(nc, pp.steuerung("linuxcnc"), pp.Maschineninfo())
    assert not befunde and any("unbearbeitet" in x for x in nc.hinweise), befunde
    f, heights, bild = fahren(job, op, m, bib)
    assert heights[0] < 11.2 and heights[1] == 11.2 and heights[2] < 11.2, heights
    collision = kb.kollision(f, job, App.Vector(), bib)
    assert not (
        collision.abgebrochen or collision.hinweise or collision.befunde
    ), collision.hinweise
    from camaddon import restmaterial as rm

    actual = sa.maschinenbahn(f, 0, 6, materialdaten=result.materialdaten)
    fein = rm.Quader(0, 40, 0, 60, 0, 11.2, 0.05)
    einsatz = sa.einsatz_von(op.ToolController, bib)
    messung = sa.fahren(
        fein, actual, vs.form_des_controllers(op.ToolController), einsatz.ae, einsatz.ap
    )
    assert messung.eilgang_abtrag == 0 and messung.schnell_abtrag == 0, vars(messung)
    assert messung.last_max <= einsatz.ae * einsatz.ap, vars(messung)
    assert sa.einschnitt(job.Model.Group[0].Shape, actual, 6) >= -1e-7
    # Wo die Grenze noch im Material liegt, wird der Schnitt bis zur freien
    # Quellstelle zurückgenommen. Eine bloße Luftfahrt zählt nicht als Teilbereich.
    cs = list(op.Path.Commands)
    for i in (2, 3, 4):
        cs[i] = Path.Command(
            "G1", {"X": 20, "Y": 10, "Z": 10, "F": float(op.ToolController.HorizFeed)}
        )
    for i in (7, 8):
        cs[i] = Path.Command(
            "G1", {"X": 20, "Y": 50, "Z": 10, "F": float(op.ToolController.HorizFeed)}
        )
    op.Path = Path.Path(cs)
    eingeschraenkt = so.programm(op, m)
    _f, begrenzt, _bild = fahren(job, op, m, bib)
    assert begrenzt[0] == 11.2 and begrenzt[1] == 11.2 and begrenzt[2] < 11.2, begrenzt
    assert eingeschraenkt.ausgelassen
    op.Path = Path.Path(original)
    # Vorschub aus einem ausgelassenen Quellabschnitt bleibt modal wirksam,
    # auch wenn dessen Wiedereintrittspunkt nun als Eilgang geschrieben wird.
    modal = list(original)
    feed = float(op.ToolController.HorizFeed) / 2
    modal[5] = Path.Command("G1", {**modal[5].Parameters, "F": feed})
    for i in range(6, 11):
        modal[i] = Path.Command("G1", {k: v for k, v in modal[i].Parameters.items() if k != "F"})
    modalprogramm = so.programm(sb._Ansicht(op, Path=Path.Path(modal)), m)
    werte = [
        data[1]
        for c, data in zip(modalprogramm.befehle, modalprogramm.materialdaten, strict=True)
        if c.Name == "G1" and c.Parameters.get("Y") == 50 and c.Parameters.get("Z") == 10
    ]
    assert werte and all(abs(v - feed) < 1e-10 for v in werte), werte
    # Direkter Weg durch eine Wand ist gesperrt; der nachweislich freie Rückzug
    # darüber wird tatsächlich ausgegeben. Die Wand ist unverändertes Rohteil.
    stock = job.Stock.Shape
    job.Stock.Shape = stock.fuse(Part.makeBox(4, 4, 40, App.Vector(18, 28, 0)))
    oben = so.programm(op, m)
    assert max(c.Parameters.get("Z", 0) for c in oben.befehle) >= 60
    job.Stock.Shape = stock
    # Eine hohe Wand auf der neuen Verbindung verlangt einen Rückzug außerhalb
    # der tatsächlichen Z-Grenze. Es wird kein gekappter oder ungeprüfter Weg ausgegeben.
    job.Stock.Shape = stock.fuse(Part.makeBox(4, 4, 10000, App.Vector(18, 28, 0)))
    try:
        so.programm(op, m)
    except ValueError:
        pass
    else:
        raise AssertionError("Nicht erreichbarer neuer Rückzug freigegeben")
    job.Stock.Shape = stock
    budget = ss.MAX_PUNKTE
    try:
        ss.MAX_PUNKTE = 2
        try:
            so.programm(op, m)
        except ValueError as e:
            assert "Rechenbudget" in str(e), str(e)
        else:
            raise AssertionError("Suchbudget ignoriert")
    finally:
        ss.MAX_PUNKTE = budget
    # Fehlende Haltergeometrie erzeugt keine gedachte materialfreie Einfahrt.
    halter = list(bib.halter)
    bib.halter = []
    bib.speichern()
    try:
        so.programm(op, m)
    except ValueError as e:
        assert "Halterdaten" in str(e), str(e)
    else:
        raise AssertionError("Einfahrt ohne vollständige Haltergeometrie")
    bib.halter = halter
    bib.speichern()
    # Eine angenommene Schneiden-/Schaft-/Gesamtlänge genügt nicht als Nachweis.
    w = next(w for w in bib.werkzeuge if w.kennung != bib.werkzeuge[0].kennung)
    for feld in ("durchmesser", "schneidenlaenge", "schaft", "gesamtlaenge"):
        alt = getattr(w, feld)
        setattr(w, feld, 0)
        bib.speichern()
        try:
            so.programm(op, m)
        except ValueError as e:
            assert "Halterdaten" in str(e), (feld, str(e))
        else:
            raise AssertionError(f"Neue Einfahrt mit unbekanntem {feld}")
        finally:
            setattr(w, feld, alt)
            bib.speichern()
    # Ein gespeicherter Winkelhalter ohne Kopf ist ebenfalls kein vollständiger Körper.
    h = bib.halter[0]
    richtung, versatz, kopf = h.richtung, h.versatz, h.kopf_d
    h.richtung, h.versatz, h.kopf_d = "gewinkelt", 100, 0
    bib.speichern()
    try:
        so.programm(op, m)
    except ValueError as e:
        assert "Halterdaten" in str(e), str(e)
    else:
        raise AssertionError("Neue Einfahrt mit unvollständigem Winkelhalter")
    finally:
        h.richtung, h.versatz, h.kopf_d = richtung, versatz, kopf
        bib.speichern()
    # Auch der unveränderte Standard-Schaftfräser benutzt dieselbe Unterteilung;
    # die Kugel ist nur für den Anstelladapter der ersten Gegenprobe erforderlich.
    from camaddon import flanke as fl
    from camaddon import job_schnittwerte as js
    from camaddon import raum_bahn as rb
    from camaddon import raum_material as raum
    from camaddon import werkzeuge as wz

    standard = next(w for w in bib.werkzeuge if w.art == wz.SCHAFTFRAESER)
    einsatz_schaft = next(e for e in standard.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
    tc = js.controller_ohne_transaktion(doc, job, standard, einsatz_schaft)
    flat = fl.lege_an(job, tc)
    flat.Schneide = float(tc.Tool.CuttingEdgeHeight)
    flat.Path, flat.Werkzeugachsen = Path.Path(original), axes
    op.Path, op.Werkzeugachsen = Path.Path(original), axes
    job.Operations.Group = [flat]
    mf = sw.Maschine(m.pruefung, m.aufnahme, rw.einspannung(tc, bib), m.nullpunkt)
    flatprogramm = so.programm(flat, mf)
    assert flatprogramm.ausgelassen
    ff = ab.abfahrt(m.pruefung, job, mf.nullpunkt, bib)
    assert ff.stationen and len(ff.operationen) == 1 and ff.hinweise, ff.hinweise
    # Ein Flankenjob hat keine Kugel-Höhenvorschau. Die endliche D12-Schneide
    # wird daher durch denselben räumlichen NC-Replay geprüft wie bei 3+2-Folgen.
    form = vs.form_des_controllers(tc)
    rest = raum.Material(stock, 0.5)
    assert rb.abtragen(rest, ff, flatprogramm.materialdaten, form, float(flat.Schneide))
    assert rest.belegt([[20, y, 10.6] for y in (10, 30, 50)]).tolist() == [False, True, False]
    assert rest.belegt([[20, y, 9.9] for y in (10, 30, 50)]).all()
    flatbahn = sa.maschinenbahn(ff, 0, 6, materialdaten=flatprogramm.materialdaten)
    flatfein = rm.Quader(0, 40, 0, 60, 0, 11.2, 0.05)
    flast = sa.fahren(flatfein, flatbahn, form, einsatz_schaft.ae, einsatz_schaft.ap)
    assert flast.eilgang_abtrag == 0 and flast.schnell_abtrag == 0, vars(flast)
    assert flast.last_max <= einsatz_schaft.ae * einsatz_schaft.ap, vars(flast)
    k = kb.kollision(ff, job, mf.nullpunkt, bib)
    assert not (k.abgebrochen or k.hinweise or k.befunde), (
        k.abgebrochen,
        k.hinweise,
        [b.text() for b in k.befunde],
    )
    assert form.eben
    job.Operations.Group = [op]
    maschinen = {}
    for art in bm.ARTEN:
        if art == bm.GROB_G550:
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
        commands = list(op.Path.Commands)
        orientations = []
        if len(real.rundachsen) >= 2:
            ar = next(
                a
                for a in real.rundachsen
                if (real.richtung({a.buchstabe: 30}) - real.richtung({})).Length > 0.1
            )
            orientations = [
                real.richtung({ar.buchstabe: t})
                for t in (3, 3, 3, 3, 3, 30, 30, -3, -3, -3, -3, -3)
            ]
            ar.achse.gelenk.EnableAngleMin = ar.achse.gelenk.EnableAngleMax = True
            ar.achse.gelenk.AngleMin, ar.achse.gelenk.AngleMax = -5, 5
            real = sw.Maschine(
                rw.Pruefung(asm, ma), p.werkzeugaufnahme(1), real.laenge, App.Vector()
            )
        else:
            orientations = [real.richtung({})] * len(commands)
            for i in (5, 6):
                commands[i] = Path.Command("G1", {**commands[i].Parameters, "X": 10000})
        view = sb._Ansicht(op, Path=Path.Path(commands), Werkzeugachsen=orientations)
        teil = so.programm(view, real)
        assert teil.ausgelassen and not mz.bahn_grund(real, teil.befehle), (art, teil.hinweis)
        maschinen[art] = len(teil.befehle)
        print("SCHNITTMASCHINE", art, len(teil.befehle), flush=True)
        App.closeDocument(ma.Document.Name)
    assert source == [c.toGCode() for c in op.Path.Commands] and axes == list(op.Werkzeugachsen)
    bild.bis_station(0)
    assert (bild.quader.h == 11.2).all()
    sekunden = time.perf_counter() - start
    speicher = tracemalloc.get_traced_memory()[1] / 1024**2
    tracemalloc.stop()
    assert sekunden < 180 and speicher < 300, (sekunden, speicher)
    report = {
        "nc_saetze": saetze,
        "sha256": hashlib.sha256(nc.text.encode()).hexdigest(),
        "resthoehen": heights,
        "bearbeitung_s": f.dauer,
        "maschinen": maschinen,
        "sekunden": sekunden,
        "python_mib": speicher,
    }
    ref = ROOT / "tests/golden/simultan_schnittbereiche.json"
    r = json.loads(ref.read_text())
    for key in ("nc_saetze", "sha256", "maschinen", "resthoehen"):
        assert report[key] == r[key], key
    assert sekunden <= r["sekunden"] * 2 and speicher <= r["python_mib"] * 2
    print("SCHNITTBEREICHE", json.dumps(report), flush=True)
    if out := os.environ.get("CAMADDON_PRUEFAUSGABE"):
        pathlib.Path(out, "schnittbereiche.json").write_text(json.dumps(report, indent=2))
    App.closeDocument(doc.Name)
    App.closeDocument(m.pruefung.maschine.Document.Name)


if __name__ != "schnittbereiche_fixture":
    pruefen()
    print("OK", pathlib.Path(__file__).name, flush=True)
