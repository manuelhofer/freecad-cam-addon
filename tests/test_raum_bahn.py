# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tatsächliche räumliche NC, unabhängige FK-/Körperprobe und Rest über Simultanvorgänger."""

import hashlib
import json
import math
import os
import pathlib
import runpy
import sys
import time
import tracemalloc

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import numpy as np
import Part
import Path

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import flanke as fl
from camaddon import job_schnittwerte as js
from camaddon import maschinenzugang as mz
from camaddon import raum_bahn as rb
from camaddon import raum_material as rm
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import simultan_bereiche as sb
from camaddon import simultan_operation as so
from camaddon import vierachs_schlichten as vs
from camaddon import werkzeuge as wz
from camaddon.kinematik import Kinematik


def innen_pruefen(f, sweeps, length):
    """Erodierte Randpunkte mit unabhängiger tatsächlicher FK auf dem ganzen Sweep prüfen."""
    kin = f.kinematik(0)
    lang = Kinematik(
        f.pruefung,
        kin.aufnahme,
        rw.Einspannung(kin.laenge.laenge + 1, kin.laenge.lage),
        kin.nullpunkt,
    )
    # Unabhängige FK: jedes innere Sweep-Randstück muss im wirklichen Zylinder liegen.
    for s in sweeps:
        e = s.schaftfehler
        radial = np.cross(s.achse, (0, 0, 1))
        if np.linalg.norm(radial) < 0.1:
            radial = np.cross(s.achse, (0, 1, 0))
        radial /= np.linalg.norm(radial)
        quer = np.cross(s.achse, radial)
        for t in np.linspace(0, 1, 9):
            states = {
                ax: val + (s.stellungen_nach[ax] - val) * t for ax, val in s.stellungen_von.items()
            }
            tip = np.asarray(kin.am_werkstueck(states))
            axis = tip - np.asarray(lang.am_werkstueck(states))
            axis /= np.linalg.norm(axis)
            middle = s.von + t * (s.nach - s.von)
            kugelmitte = s.mitte_von + t * (s.mitte_nach - s.mitte_von)
            assert np.linalg.norm(kugelmitte - tip - 6 * axis) <= s.kugelfehler + 1e-7
            for height in (e, length - e):
                for phi in np.linspace(0, 2 * np.pi, 9):
                    point = (
                        middle
                        + height * s.achse
                        + (6 - e) * (math.cos(phi) * radial + math.sin(phi) * quer)
                    )
                    diff = point - tip
                    h = float(diff @ axis)
                    assert -1e-7 <= h <= length + 1e-7, (h, length, e)
                    assert np.linalg.norm(diff - h * axis) <= 6 + 1e-7
            # Umgekehrt muss die äußere Hülle den wirklichen Körper einschließen;
            # genau diese wird auf möglichen Eilgangabtrag geprüft.
            radial_echt = np.cross(axis, (0, 0, 1))
            if np.linalg.norm(radial_echt) < 0.1:
                radial_echt = np.cross(axis, (0, 1, 0))
            radial_echt /= np.linalg.norm(radial_echt)
            quer_echt = np.cross(axis, radial_echt)
            for height in (0, length):
                for phi in np.linspace(0, 2 * np.pi, 9):
                    point = (
                        tip
                        + height * axis
                        + 6 * (math.cos(phi) * radial_echt + math.sin(phi) * quer_echt)
                    )
                    diff = point - middle
                    h = float(diff @ s.achse)
                    assert -e - 1e-7 <= h <= length + e + 1e-7
                    assert np.linalg.norm(diff - h * s.achse) <= 6 + e + 1e-7
    return kin, lang


def aufbauen(profil):
    """Native Teilbahn vor einer weiteren Ebene; Quelldaten nach Ebenenrecompute erhalten."""
    fixture = runpy.run_path(
        str(ROOT / "tests/test_simultan_bereiche.py"), run_name="teilbereiche_fixture"
    )
    doc, job, op, bib, m = fixture["aufbauen"](profil)
    cmds, axes = list(op.Path.Commands), list(op.Werkzeugachsen)
    file = str(profil / "maschine.FCStd")
    m.pruefung.maschine.Document.saveAs(file)
    rw.merke_maschine(job, file)
    danach = sw.lege_an(job, "", winkel=(0, 0))
    # sw.lege_an rechnet das Dokument nach. Die Richtungsgegenprobe soll weiterhin
    # dieselbe gespeicherte native Bahn prüfen, keine neu erzeugte ebene Schlichtbahn.
    op.Path, op.Werkzeugachsen = Path.Path(cmds), axes
    return doc, job, op, bib, m, danach


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    start = time.perf_counter()
    tracemalloc.start()
    doc, job, op, bib, m, danach = aufbauen(profil)
    source = [c.toGCode() for c in op.Path.Commands]
    rest = rm.fuer_ebene(danach)
    assert rest is not None, "Erreichbare Simultanvorgänger fehlen im räumlichen Rest"
    assert rest.belegt([[20, 10, 10.6], [20, 30, 10.6], [20, 50, 10.6]]).tolist() == [
        False,
        True,
        False,
    ]
    assert rest.ausgelassen and "2:" in rest.ausgelassen[0][0], rest.ausgelassen
    assert rm.fuer_ebene(danach) is rest
    # Eine unveränderliche Herkunftsliste ohne passenden NC-Cache darf nicht
    # beschrieben werden; die neue Rechnung liefert ihre eigenen Herkunftsdaten.
    view = sb._Ansicht(op, _pruefmaterial=())
    programm = so.programm(view, m)
    assert len(programm.materialdaten) == len(programm.befehle) and programm.ausgelassen
    assert view._pruefmaterial == ()
    # Geänderte Erreichbarkeit innerhalb derselben Operation darf den Cache nicht teilen.
    axes = list(op.Werkzeugachsen)
    op.Werkzeugachsen = [App.Vector(0, 0, 1)] * len(axes)
    fertig = rm.fuer_ebene(danach)
    assert fertig is not rest and not fertig.belegt([[20, 30, 10.6]])[0]
    op.Werkzeugachsen = axes
    assert rm.fuer_ebene(danach).belegt([[20, 30, 10.6]])[0]
    # Testkörper für eine wirklich bewegte endliche Schneide; geometrischer Replay,
    # kein Last-/Rampenzugelassener Zerspanungsvorschlag.
    stock = Part.makeBox(30, 24, 20).cut(Part.makeBox(10, 24, 8, App.Vector(10, 0, 6)))
    job.Stock.Shape = stock
    asm, ma = bm.lade(bm.TISCH_TISCH)
    p = rw.Pruefung(asm, ma)
    standard = next(w for w in bib.werkzeuge if w.art == wz.SCHAFTFRAESER)
    einsatz = next(e for e in standard.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    tc = js.controller_ohne_transaktion(doc, job, standard, einsatz)
    real = sw.Maschine(p, p.werkzeugaufnahme(1), rw.einspannung(tc, bib), App.Vector())
    poses = real.loese(App.Vector(-1, 0, 0))
    a = next(r for r in poses if all(ax.erlaubt(r[ax.buchstabe]) for ax in real.rundachsen))
    b = None
    for ax in real.rundachsen:
        value = a[ax.buchstabe]
        test = {**a, ax.buchstabe: value - np.copysign(10, value)}
        if (real.richtung(test) - real.richtung(a)).Length > 0.1:
            b = test
            break
    assert b is not None
    cmds = []
    for tip, r in (((-1, 12, 10), a), ((21, 12, 10), b)):
        vals = dict(zip("XYZ", real.abbildung(r).punkt(tip), strict=True))
        vals.update(r)
        vals["F"] = float(tc.HorizFeed)
        cmds.append(Path.Command("G1", vals))
    assert not mz.bahn_grund(real, cmds)
    cut = doc.addObject("Path::Feature", "BewegteSchneide")
    cut.addProperty("App::PropertyLink", "ToolController")
    cut.ToolController = tc
    cut.addProperty("App::PropertyBool", "Active")
    cut.Active = True
    cut.Path = Path.Path(cmds)
    job.Operations.Group = [cut]
    f = ab.abfahrt(p, job, App.Vector(), bib)
    assert len(f.operationen) == 1 and f.stationen and not f.hinweise, f.hinweise
    data = [(False, float(tc.HorizFeed))] * len(cmds)
    toolform = vs.form_des_controllers(tc)
    length = float(tc.Tool.CuttingEdgeHeight)
    assert toolform.eben and toolform.radius == 6 and length == standard.schneidenlaenge
    q = rm.Material(stock, 0.5)
    before = q.grenzen.copy()
    sweeps = list(rb.strecken(f, data, 6, length, 0.5 / 8))
    assert len(sweeps) > len(f.stationen) and any(s.schaftfehler > 0 for s in sweeps)
    assert max(s.schaftfehler for s in sweeps) <= 0.5 / 8 + 1e-10
    kin = f.kinematik(0)
    lang = Kinematik(
        p, kin.aufnahme, rw.Einspannung(kin.laenge.laenge + 1, kin.laenge.lage), App.Vector()
    )
    innen_pruefen(f, sweeps, length)
    assert rb.abtragen(q, f, data, toolform, length)
    assert q.volumen < rm.Material(stock, 0.5).volumen
    assert q.belegt(
        [[28, 12, 18], [28, 12, 2]]
    ).all(), "Endliche Schneide entfernt fernes Dach/Boden"
    # Native BRep an tatsächlichen Zwischenstellungen: innerer Sweep bleibt enthalten.
    for s in sweeps[:: max(1, len(sweeps) // 12)]:
        states = {ax: (s.stellungen_von[ax] + s.stellungen_nach[ax]) / 2 for ax in s.stellungen_von}
        tip = np.asarray(kin.am_werkstueck(states))
        axis = tip - np.asarray(lang.am_werkstueck(states))
        body = Part.makeCylinder(6, length, App.Vector(*tip), App.Vector(*axis))
        inner = Part.makeCylinder(
            6 - s.schaftfehler,
            length - 2 * s.schaftfehler,
            App.Vector(*(s.von + s.nach) / 2 + s.schaftfehler * s.achse),
            App.Vector(*s.achse),
        )
        assert inner.cut(body).Volume < 1e-6
    # Die identische Schneidenfahrt als Eilgang darf kein Material freigeben.
    rapid = rm.Material(stock, 0.5)
    assert not rb.abtragen(rapid, f, [(True, 0)] * len(cmds), toolform, length)
    assert np.array_equal(rapid.grenzen, rm.Material(stock, 0.5).grenzen, equal_nan=True)
    try:
        list(rb.strecken(f, data, 6, length, 0.5 / 8, lambda _x: False))
    except ValueError:
        pass
    else:
        raise AssertionError("Abbruch veröffentlicht halbe NC")
    aufrufe = []

    def mitten_abbrechen(anteil):
        aufrufe.append(anteil)
        return len(aufrufe) <= 3

    try:
        list(rb.strecken(f, data, 6, length, 0.5 / 8, mitten_abbrechen))
    except ValueError:
        assert len(aufrufe) == 4 and aufrufe == sorted(aufrufe)
    else:
        raise AssertionError("Ein einzelner großer NC-Schwenk ist nicht abbrechbar")
    budget = rb.MAX_STUECKE
    try:
        rb.MAX_STUECKE = 1
        try:
            list(rb.strecken(f, data, 6, length, 0.5 / 8))
        except ValueError:
            pass
        else:
            raise AssertionError("Rechenbudget wird ignoriert")
    finally:
        rb.MAX_STUECKE = budget
    # Auch der gemeinsame Verbraucher muss eine echte kontinuierliche Simultanoperation übernehmen.
    datei = str(profil / "tisch_tisch.FCStd")
    ma.Document.saveAs(datei)
    rw.merke_maschine(job, datei)
    bewegte_op = fl.lege_an(job, tc)
    bewegte_op.Schneide = length
    cmds_sim, axes_sim = [], []
    for name, tip, round_pose in (
        ("G0", (-40, 12, 10), a),
        ("G1", (-1, 12, 10), a),
        ("G1", (21, 12, 10), b),
        ("G1", (-40, 12, 10), b),
    ):
        vals = dict(zip("XYZ", tip, strict=True))
        if name == "G1":
            vals["F"] = float(tc.HorizFeed)
        cmds_sim.append(Path.Command(name, vals))
        axes_sim.append(real.richtung(round_pose))
    bewegte_op.Path, bewegte_op.Werkzeugachsen = Path.Path(cmds_sim), axes_sim
    job.Operations.Group = [bewegte_op]
    gemeinsam = rm.fuer_ebene(danach)
    assert gemeinsam is not None, "Kontinuierliche Simultanoperation wird nicht räumlich übernommen"
    assert gemeinsam.volumen < rm.Material(stock, 0.5).volumen
    assert gemeinsam.bewegungsfehler > 0
    assert gemeinsam.belegt([[28, 12, 18], [28, 12, 2]]).all()
    job.Operations.Group = [cut]
    # Dieselbe Schranke mit jeder tatsächlich gelesenen Bauart, keine G550-Sonderformel.
    maschinen = {}
    for art in bm.ARTEN:
        aa, mm = bm.lade(art)
        pruef = rw.Pruefung(aa, mm)
        kk = Kinematik(pruef, pruef.werkzeugaufnahme(1), rw.einspannung(tc, bib), App.Vector())
        first = {
            ax: (
                (ax.minimum + ax.maximum) / 2
                if ax.minimum is not None and ax.maximum is not None
                else 0.0
            )
            for ax in kk.linear
        }
        first.update({ax: 0.0 for ax in kk.drehachsen if pruef.programmbuchstabe(ax) is not None})
        last = dict(first)
        for ax in kk.linear:
            last[ax] += 2
        for ax in kk.drehachsen:
            if ax in first:
                last[ax] = 5.0
        commands = []
        for states in (first, last):
            values = dict(zip("XYZ", kk.programm(states), strict=True))
            values.update(kk.rundachsen(states))
            values["F"] = float(tc.HorizFeed)
            commands.append(Path.Command("G1", values))
        cut.Path = Path.Path(commands)
        ff = ab.abfahrt(pruef, job, App.Vector(), bib)
        assert len(ff.operationen) == 1 and ff.stationen
        ss = list(rb.strecken(ff, data, 6, length, 0.5 / 8))
        innen_pruefen(ff, ss, length)
        maschinen[art] = len(ss)
        print("BEWEGUNG_MASCHINE", art, len(ss), flush=True)
        App.closeDocument(mm.Document.Name)
    assert source == [c.toGCode() for c in op.Path.Commands]
    seconds = time.perf_counter() - start
    memory = tracemalloc.get_traced_memory()[1] / 1024**2
    tracemalloc.stop()
    # Die Sekunden sind Information (RAUMBAHN unten), keine Prüfung: Sie hängen am Rechner
    # und an der Last. Der Speicher bleibt geprüft.
    assert memory < 300, (seconds, memory)
    report = {
        "maschinen": maschinen,
        "sekunden": seconds,
        "python_mib": memory,
        "stuecke": len(sweeps),
        "bewegungsfehler_mm": q.bewegungsfehler,
        "rest_mm3": q.volumen,
        "urspruengliche_intervalle": before.shape[2],
        "rest_intervalle": q.grenzen.shape[2],
        "grenzen_sha256": hashlib.sha256(
            np.round(np.nan_to_num(q.grenzen, nan=0), 8).tobytes()
        ).hexdigest(),
    }
    referenzdatei = ROOT / "tests/golden/raum_bahn.json"
    referenz = json.loads(referenzdatei.read_text())
    for key in (
        "maschinen",
        "stuecke",
        "grenzen_sha256",
        "urspruengliche_intervalle",
        "rest_intervalle",
    ):
        assert report[key] == referenz[key], f"Räumliche NC-Referenz verändert: {key}"
    assert abs(q.volumen - referenz["rest_mm3"]) < 1e-6
    assert memory <= referenz["python_mib"] * 2
    print("RAUMBAHN", report, flush=True)
    if out := os.environ.get("CAMADDON_PRUEFAUSGABE"):
        pathlib.Path(out, "raumbahn.json").write_text(json.dumps(report, indent=2))
    np.savez_compressed(
        profil / "raum_bahn_daten.npz",
        x=q.x,
        y=q.y,
        dx=q.dx,
        dy=q.dy,
        vorher=before,
        nachher=q.grenzen,
    )
    for d in (doc, ma.Document, m.pruefung.maschine.Document):
        App.closeDocument(d.Name)


if __name__ != "raumbahn_fixture":
    pruefen()
    print("OK", pathlib.Path(__file__).name, flush=True)
