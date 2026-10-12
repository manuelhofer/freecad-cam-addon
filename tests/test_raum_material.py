# SPDX-License-Identifier: LGPL-2.1-or-later
"""Getrennte Materialschichten, kontinuierliche gerichtete Sweeps und echte 3+2-Übernahme."""

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
import numpy as np
import Part
import Path
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import job_schnittwerte as js
from camaddon import materialstand as ms
from camaddon import raum_material as raum
from camaddon import schwenken as sw
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    beginn = time.monotonic()
    tracemalloc.start()
    v = App.Vector
    stock = Part.makeBox(60, 26, 20).cut(Part.makeBox(20, 26, 8, v(20, 0, 6)))
    ursprung = stock.exportBrepToString()
    q = raum.Material(stock, 0.5)
    for schritt, meldung in ((0, "geometrie"), (0.0001, "raster")):
        try:
            raum.Material(stock, schritt)
        except ValueError:
            pass
        else:
            raise AssertionError(meldung)
    try:
        raum.Material(stock, 0.5, fortschritt=lambda _p: False)
    except ValueError:
        pass
    else:
        raise AssertionError("Abbruch veröffentlicht einen unvollständigen Materialstand")
    assert abs(q.volumen - stock.Volume) < 1e-8
    assert q.belegt([[30, 13, 2], [30, 13, 18], [30, 13, 10]]).tolist() == [True, True, False]
    kopie = q.kopie()
    weg = q.schaft((-1, 13, 10), (21, 13, 10), (-1, 0, 0), 6, 25)
    assert weg > 2000
    assert q.belegt([[10, 13, 10], [10, 13, 2], [10, 13, 18]]).tolist() == [False, True, True]
    assert kopie.belegt([[10, 13, 10]]).all(), "Materialzweige teilen veränderliche Schichten"
    assert q.schaft((-1, 13, 10), (21, 13, 10), (-1, 0, 0), 6, 25) < 1e-9
    assert stock.exportBrepToString() == ursprung, "Materialprüfung ändert den CAD-Körper"
    soll = raum.Material(stock.cut(Part.makeCylinder(6, 47, v(-26, 13, 10), v(1, 0, 0))), 0.5)
    assert abs(q.volumen - soll.volumen) < 1e-8, "Schaftabtrag weicht vom nativen BRep-Sweep ab"

    # Dünne, beliebig gerichtete Gerade: Die Endkugeln allein lassen die Mitte stehen.
    voll = raum.Material(Part.makeBox(16, 16, 16), 0.5)
    voll.kugel((2, 2, 2), (14, 14, 14), 2)
    assert not voll.belegt([[8, 8, 8]]).any()
    assert voll.belegt([[8, 8, 1], [8, 1, 8]]).all()
    assert np.max(np.sum(np.isfinite(voll.grenzen[..., 0]), axis=2)) >= 2
    a, b = v(2, 2, 2), v(14, 14, 14)
    kapsel = Part.makeSphere(2, a).fuse(Part.makeCylinder(2, (b - a).Length, a, b - a))
    kapsel = kapsel.fuse(Part.makeSphere(2, b))
    soll = raum.Material(Part.makeBox(16, 16, 16).cut(kapsel), 0.5)
    assert abs(voll.volumen - soll.volumen) < 1e-8, "Kugelabtrag weicht vom nativen BRep-Sweep ab"

    # Unabhängige dichte (z,t)-Machbarkeitsprobe; auch horizontale/axiale Degenerationen.
    rng = np.random.default_rng(71)
    with np.errstate(invalid="raise"):
        lo, hi = raum.schaftschnitt(
            np.array([10.0]), np.array([10.0]), (0, 0, 0), (0, 0, 0), (0, 0, 1), 1, 25
        )
        assert np.isinf(lo).all() and np.isinf(hi).all()
    for achse in ((0, 0, 1), (1, 0, 0), (0, 1, 0), (0.6, 0, 0.8), *rng.normal(size=(5, 3))):
        u = np.asarray(achse, dtype=float)
        u /= np.linalg.norm(u)
        a, b = rng.uniform(-3, 3, (2, 3))
        xs, ys = rng.uniform(-2, 2, (2, 7))
        lo, hi = raum.schaftschnitt(xs, ys, a, b, u, 2, 5)
        t = np.linspace(0, 1, 6001)
        mitte = a + t[:, None] * (b - a)
        for x, y, unten, oben in zip(xs, ys, lo, hi, strict=True):
            # Statische Zylinder schneiden die Strahlen nach unabhängigen quadratischen
            # Ray/Zylinder-Schnitten, dicht über die Zeit. Der kontinuierliche Sweep darf
            # enger werden, aber keine dieser tatsächlichen Stellungen verlieren.
            w = np.column_stack([x - mitte[:, 0], y - mitte[:, 1], -mitte[:, 2]])
            h = w @ u
            radial = w - h[:, None] * u
            ez = np.array([0, 0, 1]) - u[2] * u
            aa, bb = float(ez @ ez), 2 * (radial @ ez)
            cc = np.sum(radial * radial, axis=1) - 4
            if aa > 1e-12:
                dis = bb * bb - 4 * aa * cc
                low = (-bb - np.sqrt(np.maximum(0, dis))) / (2 * aa)
                high = (-bb + np.sqrt(np.maximum(0, dis))) / (2 * aa)
                gut = dis >= 0
            else:
                low, high = np.full(len(t), -np.inf), np.full(len(t), np.inf)
                gut = cc <= 0
            if abs(u[2]) > 1e-12:
                ha, hb = -h / u[2], (5 - h) / u[2]
                low, high = np.maximum(low, np.minimum(ha, hb)), np.minimum(
                    high, np.maximum(ha, hb)
                )
            else:
                gut &= (h >= 0) & (h <= 5)
            gut &= low <= high
            if gut.any():
                dl, dr = low[gut].min(), high[gut].max()
                assert unten <= dl + 1e-8 and oben >= dr - 1e-8
                assert max(dl - unten, oben - dr) < 0.003
            else:
                assert np.isinf(unten) and np.isinf(oben)

    # Native Jobs und Manuels Standardwerkzeug. Diese Gerade ist eine Gegenprobe
    # des Materialkerns, kein lastgeprüfter Bearbeitungsvorschlag.
    user_asset_store.set_dir(profil / "assets")
    standard = wz.standardwerkzeug()
    bib = wz.Bibliothek([standard])
    ue.uebergeben(bib)
    einsatz = next(e for e in standard.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    doc = App.newDocument("Raummaterial")
    obj = doc.addObject("Part::Feature", "Teil")
    cutter = Part.makeCylinder(6, 22, v(-1, 13, 10), v(1, 0, 0))
    obj.Shape = stock.cut(cutter)
    roh = doc.addObject("Part::Feature", "Rohteil")
    roh.Shape = stock
    grund = PathJob.Create("Job", [obj])
    grund.Stock = roh
    doc.recompute()
    erster = sw.lege_an(grund, "", winkel=(90, 180))
    tc = js.controller_ohne_transaktion(doc, erster, standard, einsatz)
    doc.recompute()
    assert float(tc.Tool.CuttingEdgeHeight) == standard.schneidenlaenge
    op = doc.addObject("Path::Feature", "Seitenschnitt")
    op.addProperty("App::PropertyLink", "ToolController")
    op.ToolController = tc
    op.addProperty("App::PropertyBool", "Active")
    op.Active = True
    inv = erster.Ebene.inverse()
    a, b = inv.multVec(v(21, -8, 10)), inv.multVec(v(21, 13, 10))
    op.Path = Path.Path(
        [
            Path.Command("G0", dict(zip("XYZ", a, strict=True))),
            Path.Command("G1", dict(zip("XYZ", b, strict=True))),
        ]
    )
    erster.Operations.Group = [op]
    naechster = sw.lege_an(grund, "", winkel=(90, 180))
    doc.recompute()
    stand = ms.fuer(naechster)
    punkt = naechster.Ebene.inverse().multVec(v(40, 13, 10))
    h = stand.hoehen_an([punkt.x], [punkt.y], naechste=True)[0, 0]
    assert punkt.z <= h <= punkt.z + ms.EBENE_SCHRITT + ms.SCHRITT + 1e-7, (h, punkt.z)
    assert raum.fuer_ebene(naechster) is raum.fuer_ebene(naechster)
    vorher = ms.kennung_vor(naechster, None)
    tc.Tool.CuttingEdgeHeight = 5
    assert ms.kennung_vor(naechster, None) != vorher, "Schneidenlänge fehlt in der Kennung"
    kurz = raum.fuer_ebene(naechster)
    assert kurz.belegt([[5, 13, 10]]).all(), "Kurze Schneide räumt bis zum unendlich langen Schaft"
    tc.Tool.CuttingEdgeHeight = standard.schneidenlaenge
    doc.recompute()
    s = ms.fuer(naechster)
    assert s.hoehen_an([punkt.x], [punkt.y], naechste=True)[0, 0] == h
    # Ohne Änderung des Pfads muss eine neue Rohteilgeometrie die Kennung ändern.
    vorher = ms.kennung_vor(naechster, None)
    roh.Shape = Part.makeBox(60, 26, 20).cut(Part.makeBox(20, 26, 8, v(21, 0, 6)))
    assert ms.kennung_vor(naechster, None) != vorher
    roh.Shape = stock
    doc.recompute()
    op.Active = False
    ungefraest = raum.fuer_ebene(naechster)
    assert ungefraest.belegt([[10, 13, 10]]).all()
    op.Active = True
    doc.recompute()
    # In Streifen auf den Nebenrechnern (2026-10-12) dasselbe wie allein – erzwungen schon ab
    # einer Bewegung; bis auf Rundung in der letzten Stelle gleich.
    from camaddon import nebenrechner as nr

    allein = raum.fuer_ebene(naechster).grenzen
    ab = raum.VERTEILT_AB_BEWEGUNGEN
    raum.VERTEILT_AB_BEWEGUNGEN = 1
    raum._GEMERKT.clear()
    try:
        verteilt = raum.fuer_ebene(naechster).grenzen
        assert nr.pool().arbeiter > 0, "nicht auf den Nebenrechnern gerechnet"
    finally:
        raum.VERTEILT_AB_BEWEGUNGEN = ab
        raum._GEMERKT.clear()
        nr.pool().beenden()
    k = max(allein.shape[2], verteilt.shape[2])

    def aufgefuellt(g):
        h = np.full(g.shape[:2] + (k, 2), np.nan)
        h[:, :, : g.shape[2]] = g
        return h

    a, b = aufgefuellt(allein), aufgefuellt(verteilt)
    assert np.array_equal(np.isnan(a), np.isnan(b)), "andere Abschnitte in Streifen"
    assert np.nanmax(np.abs(a - b), initial=0.0) < 1e-9, "Streifen rechnen anders"

    # Jede Schneide als Kugeln und Zylinder (koerperteile, P-2026-10-11-90): innen ganz im
    # Fräser, die Treppe höchstens eine halbe Zelle neben seinem Profil; außen um ihn herum.
    from camaddon import fraeserform as ff

    formen = (
        ff.torus(6, 2),
        ff.konik(1.5, 5, 20, 3.0),
        ff.kegel(0.5, 6, 5.5),
        ff.radien(1, 3, 4),
        ff.kugel(3),
        ff.scheibe(5),
    )
    for form in formen:
        innen, aussen = raum.koerperteile(form, 20, 0.5)
        for teil in innen:
            if teil[0] == "kugel":
                _art, z, rad = teil
                rho = np.linspace(0, rad, 50)
                assert np.all(z - np.sqrt(rad**2 - rho**2) >= form.hoehe(rho) - 1e-9), teil
            else:
                _art, z, rad, lang = teil
                assert rad <= form.radius + 1e-9 and z >= float(form.hoehe(rad)) - 1e-9, teil
                assert z + lang <= 20 + 1e-9, teil
        for rho in np.linspace(0, form.radius - 1e-6, 200):
            z = float(form.hoehe(rho))
            assert any(
                (t_[0] == "schaft" and t_[2] >= rho - 0.5 and t_[1] <= z + 0.5)
                or (t_[0] == "kugel" and rho <= t_[2] + 1e-9)
                for t_ in innen
            ), (form, rho)
        if not (form.eben or form.nur_kugel):
            assert aussen == [("schaft", 0.0, form.radius, 20)], aussen
    # Ein Torusfräser Ø 12, R 2, 3 mm tief durch einen Block: Was innen abträgt, liegt zwischen
    # dem flachen Kern (Ø 8) und dem vollen Zylinder (außen). Dem Torus fehlen gegen den Zylinder
    # die Ecken – längs 20 mm je 4 − π mm², an den Enden eine halbe Drehung: zusammen 64 mm³; die
    # Treppe lässt bei 0,5 mm Stufen 14 mm³ mehr stehen (78).
    innen, aussen = raum.koerperteile(ff.torus(6, 2), 20, 0.5)
    weg = {}
    for name, teile in (("kern", [("schaft", 0.0, 4.0, 20)]), ("innen", innen), ("aussen", aussen)):
        block = raum.Material(Part.makeBox(40, 20, 20), 0.5)
        weg[name] = raum.teile_abtragen(block, (10, 10, 17), (30, 10, 17), (0, 0, 1), teile)
    assert weg["kern"] < weg["innen"] < weg["aussen"], weg
    assert 60 < weg["aussen"] - weg["innen"] < 90, weg
    # Eine Ebene nach einem Torusfräser bekommt einen räumlichen Materialstand (vorher keinen).
    torus = wz.Werkzeug(
        nummer=2, name="Torus 12", art=wz.TORUSFRAESER, durchmesser=12.0, schneiden=4,
        schneidenlaenge=26.0, eckradius=2.0,
    )  # fmt: skip
    torus.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=1.5, ap=10, vc=85, fz=0.1)]
    ue.uebergeben(wz.Bibliothek([standard, torus]))
    tc_torus = js.controller_ohne_transaktion(doc, erster, torus, torus.schnittwerte[wz.ALLE][0])
    op.ToolController = tc_torus
    doc.recompute()
    mit_torus = raum.fuer_ebene(naechster)
    assert mit_torus is not None, "nach einem Torusfräser kein räumlicher Materialstand"
    assert not mit_torus.belegt([[10, 13, 10]]).any(), "der Torusfräser hat nichts abgetragen"
    op.ToolController = tc
    doc.recompute()
    doc.saveAs(str(profil / "raeumlicher_materialstand.FCStd"))
    info = {
        "restvolumen_mm3": q.volumen,
        "abschnitte_sha256": hashlib.sha256(q.grenzen.astype("<f8").tobytes()).hexdigest(),
        "seitenmaterial_hoehe_mm": float(h),
        "laufzeit_s": time.monotonic() - beginn,
        "spitzenspeicher_python_mb": tracemalloc.get_traced_memory()[1] / 1024**2,
    }
    # Die Laufzeit ist Information, keine Prüfung: Sie hängt am Rechner und an der Last.
    assert info["spitzenspeicher_python_mb"] < 250
    golden = ROOT / "tests/golden/raum_material.json"
    if os.environ.get("RAUM_GOLDEN_SCHREIBEN") == "1":
        golden.write_text(json.dumps(info, indent=2) + "\n")
    else:
        soll = json.loads(golden.read_text())
        for name in ("restvolumen_mm3", "abschnitte_sha256", "seitenmaterial_hoehe_mm"):
            assert info[name] == soll[name], name
        # Die Laufzeit gegen die Referenz ist Information, keine Prüfung (Rechner, Last).
        assert info["spitzenspeicher_python_mb"] < max(50, 2 * soll["spitzenspeicher_python_mb"])
    print("MESSUNG", json.dumps(info), flush=True)
    App.closeDocument(doc.Name)
    tracemalloc.stop()


pruefen()
print("OK", pathlib.Path(__file__).name)
