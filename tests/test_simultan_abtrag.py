# SPDX-License-Identifier: LGPL-2.1-or-later
"""Unabhängige Gegenproben: Kugelsweep, Flächenlücke, dünner Einschnitt, Eilgang und Last."""

import os
import pathlib
import sys
from dataclasses import replace
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import FreeCAD as App
import numpy as np
import Part

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import restmaterial as rm
from camaddon import schlicht_rand as sr
from camaddon import simultan_abtrag as sa
from camaddon import simultan_planung as sp
from camaddon import sprache


def pruefung():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    geometrie = Part.makeSphere(3)
    vorher = sp._geometrie(geometrie)
    geometrie.tessellate(0.01)
    assert sp._geometrie(geometrie) == vorher, "Darstellungsnetz wird als CAD-Änderung gewertet"
    assert sp._geometrie(Part.makeSphere(3.01)) != vorher, "Geänderte CAD-Form wird nicht erkannt"
    geometrie.translate(App.Vector(0.01, 0, 0))
    assert sp._geometrie(geometrie) != vorher, "Geänderte CAD-Lage wird nicht erkannt"
    rng = np.random.default_rng(7)
    # Analytisches Minimum gegen dichte, unabhängige Kugelstellungen auf schrägen Strecken.
    for _ in range(12):
        a, b = rng.uniform(-2, 2, (2, 3))
        xy = rng.uniform(-1, 1, (20, 2))
        r = 1.7
        analytisch = sa.kugelschnitt(xy[:, 0], xy[:, 1], a, b, r)
        mitte = a + np.linspace(0, 1, 20001)[:, None] * (b - a)
        rho2 = np.sum((xy[:, None, :] - mitte[None, :, :2]) ** 2, axis=2)
        dicht = np.min(
            np.where(
                rho2 <= r * r, mitte[None, :, 2] - np.sqrt(np.maximum(0, r * r - rho2)), np.inf
            ),
            axis=1,
        )
        endlich = np.isfinite(analytisch) & np.isfinite(dicht)
        assert np.all(analytisch[endlich] <= dicht[endlich] + 1e-10)
        assert np.max(np.abs(analytisch[endlich] - dicht[endlich])) < 1e-4
        assert np.array_equal(np.isfinite(analytisch), np.isfinite(dicht))
    senkrecht = sa.kugelschnitt(np.array([0.0, 3.0]), np.array([0.0, 0.0]), (0, 0, 5), (0, 0, 3), 2)
    assert senkrecht[0] == 1 and np.isinf(senkrecht[1])
    # Der Schaft berührt den Strahl zuerst am Rand seiner Scheibe. Bei konstantem z
    # schneidet er ihn danach innen: die Randlage darf nicht den ganzen Sweep verwerfen.
    flach = sa.schaftschnitt(np.array([0.5, 1.5, 2.5, 3.5]), np.zeros(4), (0, 0, 1), (4, 0, 1), 1)
    assert np.all(flach == 1), "Horizontaler Schaft-Sweep lässt Lücken zwischen Endpunkten"
    schraeg = sa.schaftschnitt(np.array([2.0]), np.array([0.0]), (0, 0, 3), (4, 0, 1), 1)
    assert abs(schraeg[0] - 1.5) < 1e-12

    def p(x, y, z=0, eil=False):
        return bn.Punkt(eil, x, y, z)

    # Alle drei Ecken werden von verschiedenen Bahnen getroffen, die Fläche dazwischen nicht.
    luecke = np.array([[[-0.4, -0.05, 0], [-0.4, 0.05, 0], [0.4, 0, 0]]])
    pk = [p(-0.4, -1), p(-0.4, 1), p(0.4, -1, eil=True), p(0.4, 1)]
    assert sa.deckung(luecke, pk, 2, 0.02) > 0, "Eckenproben haben Flächenlücke verschluckt"
    eng = np.array([[[-0.1, -0.05, 0], [-0.1, 0.05, 0], [0.1, 0, 0]]])
    assert sa.deckung(eng, [p(0, -1), p(0, 1)], 2, 0.02) == 0
    assert sa.deckung(eng, [], 2, 0.02) == 1

    # Der dünne Zapfen liegt zwischen Bahnpunkten und Rasterstrahlen, BRep muss ihn finden.
    nadel = Part.makeBox(0.01, 0.01, 2, App.Vector(0.395, -0.005, 0))
    assert sa.einschnitt(nadel, [p(-1, 0), p(1, 0)], 1) < -0.99
    assert sa.einschnitt(nadel, [p(-1, 0, 3), p(1, 0, 3)], 1) >= 0

    # OCC liefert umgekehrte Randkanten trotzdem in Kurvenrichtung. Die Verbindung
    # quer durch eine konvexe Kugelkappe schnitte tief ins Teil.
    kappe = Part.makeSphere(40, App.Vector(10, 8, -25)).common(
        Part.makeBox(20, 16, 20, App.Vector(0, 0, 6))
    )
    teil = Part.makeBox(20, 16, 6).fuse(kappe).removeSplitter()
    flaechen = [
        f"Face{i+1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)
    ]
    rand = SimpleNamespace(punkte=[], umlaeufe=0)
    sr.ergaenzen(rand, teil, flaechen, 2, 0, 23, 18, 3, 600, 100, schritt=0.05)
    assert all(
        bn.weg(a, b) < 0.06
        for a, b in zip(rand.punkte, rand.punkte[1:], strict=False)
        if not a.eilgang and not b.eilgang
    ), "Randgang verbindet getrennte Kantenenden durch das Teil"
    assert sa.einschnitt(teil, rand.punkte, 2, grenze=-0.001) >= -0.001

    q = rm.Quader(-2, 2, -2, 2, 0, 5, schritt=0.1)
    m = sa.fahren(q, [p(-1, 0, 1), p(1, 0, 1, eil=True)], ff.kugel(1), 0.3, 0.3)
    assert m.eilgang_abtrag > 0 and m.gruende, "Eilgang im Material freigegeben"
    q.zuruecksetzen()
    m = sa.fahren(q, [p(-1, 0, 1), replace(p(1, 0, 1), anteil=3)], ff.kugel(1), 100, 100)
    assert m.schnell_abtrag > 0 and m.gruende, "Freivorschub im Material freigegeben"
    q.zuruecksetzen()
    m = sa.fahren(q, [p(0, 0, 6), p(0, 0, 1)], ff.kugel(1), 0.3, 0.3)
    assert m.eintauchungen == 1 and m.gruende, "Senkrechtes Eintauchen freigegeben"
    q.zuruecksetzen()
    m = sa.fahren(q, [p(-1, 0, 4), p(1, 0, 3)], ff.scheibe(1), 100, 100, eintauchwinkel=3)
    assert m.rampenwinkel_max > 3 and m.gruende, "Werkzeug-Rampenwinkel überschritten"
    q.zuruecksetzen()
    m = sa.fahren(q, [p(-2, 0, 1), p(2, 0, 1)], ff.kugel(1), 0.01, 0.01)
    assert m.last_max > 0.01**2 and m.gruende, "Lastüberschreitung freigegeben"
    q.zuruecksetzen()
    m = sa.fahren(q, [p(-2, 0, 6), p(2, 0, 6)], ff.kugel(1), 1, 1)
    assert m.luftanteil == 1 and m.gruende, "Reine Luftbahn freigegeben"
    q.zuruecksetzen()
    m = sa.fahren(
        q,
        [p(-2, 0, 1), p(2, 0, 1), p(0, 1, 6, eil=True), p(0.1, 1, 6)],
        ff.kugel(1),
        100,
        100,
    )
    assert (
        m.luftanteil < 0.3 and m.luftzuege == 1 and m.gruende
    ), "Kurzer ganzer Luftzug wird im Mittel versteckt"


pruefung()
print("OK", os.path.basename(__file__))
