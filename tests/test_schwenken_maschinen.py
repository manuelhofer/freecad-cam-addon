# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tatsächliche Achsen aller Beispielmaschinen, feste Richtung und NC ohne erfundene Achsen."""

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import beispielmaschine as bm
from camaddon import job_schnittwerte as js
from camaddon import postprozessor as pp
from camaddon import raeumen as ra
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    w = wz.standardwerkzeug()
    bib = wz.Bibliothek([w])
    bib.speichern()
    user_asset_store.set_dir(profil / "assets")
    ue.uebergeben(bib)
    einsatz = next(e for e in w.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    for art in bm.ARTEN:
        asm, ma = bm.lade(art)
        p = rw.Pruefung(asm, ma)
        aufnahme = p.werkzeugaufnahme(1)
        assert aufnahme is not None
        m = sw.Maschine(p, aufnahme, w.gesamtlaenge, App.Vector())
        richtung = m.richtung({})
        loesungen = m.loese(richtung)
        erlaubt = [r for r in loesungen if all(a.erlaubt(r[a.buchstabe]) for a in m.rundachsen)]
        assert erlaubt, (art, richtung, loesungen)
        assert all(set(r) == {a.buchstabe for a in m.rundachsen} for r in erlaubt)
        print("MASCHINE", art, len(m.rundachsen), erlaubt[0], flush=True)
        if art == bm.FRAESE_3:
            assert erlaubt == [{}]
            quer = richtung.cross(App.Vector(1, 0, 0))
            if quer.Length < 0.01:
                quer = richtung.cross(App.Vector(0, 1, 0))
            assert not m.loese(quer), "Feste Spindel erfindet eine Schwenkmöglichkeit"
            doc = App.newDocument("FesteSpindel")
            obj = doc.addObject("Part::Feature", "Teil")
            obj.Shape = Part.makeBox(20, 20, 10)
            grund = PathJob.Create("Job", [obj])
            grund.Stock.ExtZpos = 1
            doc.recompute()
            face = next(
                f"Face{i+1}"
                for i, f in enumerate(vr.modell(grund).Shape.Faces)
                if (n := sw.aussennormale(f)) is not None and n.dot(richtung) > 1 - 1e-8
            )
            ebene = sw.lege_an(grund, face, m)
            tc = js.controller_ohne_transaktion(doc, ebene, w, einsatz)
            doc.recompute()
            op = ra.lege_an(ebene, tc, einsatz.ap, einsatz.ae, flaechen=[face])
            doc.recompute()
            m = sw.Maschine(p, aufnahme, rw.einspannung(tc, bib), rw.nullpunkt(grund))
            abschnitte = pp.abschnitte(grund, m)
            assert abschnitte and all(a.schwenkung is None for a in abschnitte)
            original = list(op.Path.Commands)
            erwartet = sw.befehle_ohne_zyklus(
                original, sw.schwenkung_fuer(ebene, m), schon_oben=True
            )
            assert [c.toGCode() for c in abschnitte[0].befehle] == [c.toGCode() for c in erwartet]
            assert not any(set(c.Parameters) & set("ABC") for c in abschnitte[0].befehle)
            for steuerung in ("siemens", "linuxcnc"):
                s = pp.steuerung(steuerung)
                info = pp.maschineninfo_dokument(ma.Document)
                programm = pp.programm(abschnitte, s, info, "FESTE_SPINDEL")
                assert "CYCLE800" not in programm.text
                befunde, _saetze = pp.nachlesen(programm, s, info)
                assert not befunde, befunde
            App.closeDocument(doc.Name)
        if art == bm.TISCH_TISCH:
            a = m.rundachsen[0]
            rund = {r.buchstabe: 0.0 for r in m.rundachsen}
            rund[a.buchstabe] = 30
            geneigt = m.richtung(rund)
            gelenk = a.achse.gelenk
            gelenk.EnableAngleMin, gelenk.AngleMin = True, -10
            gelenk.EnableAngleMax, gelenk.AngleMax = True, 10
            frisch = sw.Maschine(rw.Pruefung(asm, ma), aufnahme, w.gesamtlaenge, App.Vector())
            aa = next(r for r in frisch.rundachsen if r.buchstabe == a.buchstabe)
            assert (aa.minimum, aa.maximum) == (-10, 10)
            assert not any(
                all(r.erlaubt(k[r.buchstabe]) for r in frisch.rundachsen)
                for k in frisch.loese(geneigt)
            ), "Geänderten Anschlag nicht aus der Maschine gelesen"
        App.closeDocument(ma.Document.Name)


pruefen()
print("OK", pathlib.Path(__file__).name)
