# SPDX-License-Identifier: LGPL-2.1-or-later
"""Aktuelle Schwenkgrenzen lassen Bereiche in NC und räumlichem Material gemeinsam aus."""

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

from camaddon import beispielmaschine as bm
from camaddon import job_schnittwerte as js
from camaddon import maschinenzugang as mz
from camaddon import materialstand as ms
from camaddon import postprozessor as pp
from camaddon import raum_material as rm3
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz


def gegenprobe(profil, behalten=False):
    user_asset_store.set_dir(profil / "assets")
    w = wz.standardwerkzeug()
    w.gesamtlaenge = 85
    bib = wz.Bibliothek([w])
    bib.speichern()
    ue.uebergeben(bib)
    einsatz = next(e for e in w.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    asm, ma = bm.lade(bm.TISCH_TISCH)
    datei = str(profil / "maschine.FCStd")
    ma.Document.saveAs(datei)
    p = rw.Pruefung(asm, ma)
    m = sw.Maschine(p, p.werkzeugaufnahme(1), 85, App.Vector())
    doc = App.newDocument("AusgelasseneEbene")
    stock = Part.makeBox(60, 26, 20).cut(Part.makeBox(20, 26, 8, App.Vector(20, 0, 6)))
    obj = doc.addObject("Part::Feature", "Teil")
    obj.Shape = stock.cut(Part.makeCylinder(6, 22, App.Vector(-1, 13, 10), App.Vector(1, 0, 0)))
    grund = PathJob.Create("Job", [obj])
    doc.recompute()
    roh = doc.addObject("Part::Feature", "Rohteil")
    roh.Shape = stock
    grund.Stock = roh
    rw.merke_maschine(grund, datei)
    doc.recompute()
    erster = sw.lege_an(grund, "", m, winkel=(90, 180))
    tc = js.controller_ohne_transaktion(doc, erster, w, einsatz)
    doc.recompute()
    op = doc.addObject("Path::Feature", "Seitenschnitt")
    op.addProperty("App::PropertyLink", "ToolController")
    op.ToolController = tc
    op.addProperty("App::PropertyBool", "Active")
    op.Active = True
    # Geometrische Gegenprobe; diese einzelne Gerade ist kein lastgeprüfter Bearbeitungsvorschlag.
    inv = erster.Ebene.inverse()
    a, b = inv.multVec(App.Vector(21, -8, 10)), inv.multVec(App.Vector(21, 13, 10))
    op.Path = Path.Path(
        [
            Path.Command("G0", dict(zip("XYZ", a, strict=True))),
            Path.Command("G1", dict(zip("XYZ", b, strict=True))),
        ]
    )
    erster.Operations.Group = [op]
    # Eine andere, weiterhin erreichbare Ebene enthält eine gewöhnliche Operation.
    erreichbar = sw.lege_an(grund, "", m, winkel=(0, 0))
    tc2 = js.controller_ohne_transaktion(doc, erreichbar, w, einsatz)
    doc.recompute()
    op2 = doc.addObject("Path::Feature", "AndereFlaeche")
    op2.addProperty("App::PropertyLink", "ToolController")
    op2.ToolController = tc2
    op2.addProperty("App::PropertyBool", "Active")
    op2.Active = True
    op2.Path = Path.Path(
        [
            Path.Command("G0", {"X": 50, "Y": 13, "Z": 25}),
            Path.Command("G1", {"X": 51, "Y": 13, "Z": 25, "F": float(tc2.HorizFeed)}),
        ]
    )
    erreichbar.Operations.Group = [op2]
    naechster = sw.lege_an(grund, "", m, winkel=(90, 180))
    doc.recompute()
    assert mz.ebene_erreichbar(erster, op) is True
    gefraest = rm3.fuer_ebene(naechster)
    assert not gefraest.belegt([[10, 13, 10]]).any()
    assert not gefraest.ausgelassen
    key = ms.kennung_vor(naechster, None)
    gespeicherte_bahn = [c.toGCode() for c in op.Path.Commands]
    gespeicherte_stellung = sw.rundachsen_von(erster)
    achse = next(a for a in m.rundachsen if a.buchstabe == "A")
    gelenk = achse.achse.gelenk
    gelenk.EnableAngleMin = True
    gelenk.AngleMin = -10
    gelenk.EnableAngleMax = True
    gelenk.AngleMax = 10
    neu = sw.Maschine(rw.Pruefung(asm, ma), m.aufnahme, 85, App.Vector())
    assert sw.passende_rundachsen(neu, erster.Ebene, gespeicherte_stellung) is None
    assert mz.ebene_erreichbar(erster, op) is False
    assert mz.ebene_erreichbar(erreichbar, op2) is True
    assert ms.kennung_vor(naechster, None) != key, "Geänderter Anschlag fehlt im Materialcache"
    ungefraest = rm3.fuer_ebene(naechster)
    assert ungefraest.belegt(
        [[10, 13, 10]]
    ).all(), "Ausgelassene Bearbeitung wird als entfernt gerechnet"
    assert ungefraest.volumen > gefraest.volumen + 2000
    assert ungefraest.ausgelassen == ((op.Label, erster.Label),)
    stand = ms.fuer(naechster)
    punkt = naechster.Ebene.inverse().multVec(App.Vector(20, 13, 10))
    h = stand.hoehen_an([punkt.x], [punkt.y], naechste=True)[0, 0]
    assert h >= punkt.z, "Projizierter Rest verliert die unbearbeitete erste Wand"
    abschnitte = pp.abschnitte(grund, neu)
    assert len(abschnitte) == 2
    bad = next(a for a in abschnitte if a.name == op.Label)
    good = next(a for a in abschnitte if a.name == op2.Label)
    assert not bad.befehle and bad.schwenkung is None and "unbearbeitet" in bad.hinweis
    assert good.befehle and not good.hinweis
    for steuerung in ("siemens", "linuxcnc"):
        s = pp.steuerung(steuerung)
        info = pp.maschineninfo_dokument(ma.Document)
        prog = pp.programm(abschnitte, s, info, "BEREICHE")
        assert any("unbearbeitet" in h for h in prog.hinweise)
        befunde, _saetze = pp.nachlesen(prog, s, info)
        assert not befunde, befunde
    assert gespeicherte_bahn == [c.toGCode() for c in op.Path.Commands]
    # Andere Anschläge bleiben wirksam; die alte Stellung wird wieder zulässig.
    gelenk.AngleMin = -110
    gelenk.AngleMax = 110
    wieder = rm3.fuer_ebene(naechster)
    assert abs(wieder.volumen - gefraest.volumen) < 1e-8 and not wieder.ausgelassen
    # Eine nicht mehr lesbare tatsächliche Zuordnung darf keine Ersatzmaschine verwenden.
    for ebene in (erster, erreichbar, naechster):
        rw.merke_maschine(ebene, str(profil / "fehlt.FCStd"))
    komplett = rm3.fuer_ebene(naechster)
    assert komplett.belegt([[10, 13, 10]]).all()
    assert len(komplett.ausgelassen) == 2
    result = {
        "gefraest_mm3": gefraest.volumen,
        "ausgelassen_mm3": ungefraest.volumen,
        "stehen_geblieben_mm3": ungefraest.volumen - gefraest.volumen,
        "ausgelassene_bereiche": ungefraest.ausgelassen,
        "erste_wand_hoehe": float(h),
    }
    if behalten:
        for ebene in (erster, erreichbar, naechster):
            rw.merke_maschine(ebene, datei)
        gelenk.AngleMin, gelenk.AngleMax = -10, 10
        return result, (doc, ma, grund, gefraest, ungefraest)
    App.closeDocument(doc.Name)
    App.closeDocument(ma.Document.Name)
    return result


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    start = time.perf_counter()
    tracemalloc.start()
    result = gegenprobe(profil)
    result["sekunden"] = time.perf_counter() - start
    result["python_mib"] = tracemalloc.get_traced_memory()[1] / 1024**2
    tracemalloc.stop()
    # Die Sekunden sind Information (AUSLASSUNG unten), keine Prüfung: Sie hängen am Rechner
    # und an der Last (1.1.3-Prüfrechner unter Last: 173 s). Der Speicher bleibt geprüft.
    assert result["python_mib"] < 250, result
    print("AUSLASSUNG", json.dumps(result, ensure_ascii=False), flush=True)
    if out := os.environ.get("CAMADDON_PRUEFAUSGABE"):
        pathlib.Path(out, "ergebnis.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False)
        )


# FreeCADCmd führt eine Datei unter ihrem eigenen Namen aus, nicht als "__main__"
# (P-2026-10-10-44) – sonst lief die Prüfung dort nie.
if __name__ in ("__main__", pathlib.Path(__file__).stem):
    pruefen()
    print("OK", pathlib.Path(__file__).name, flush=True)
