# SPDX-License-Identifier: LGPL-2.1-or-later
"""Richtungsplanung muss dieselbe reale Einspannung wie die Vorwärtskinematik verwenden."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import FreeCAD as App

from camaddon import beispielmaschine as bm
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import werkzeuge as wz
from camaddon.kinematik import Kinematik


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    standard = wz.standardwerkzeug()
    for art in bm.ARTEN:
        asm, ma = bm.lade(art)
        p = rw.Pruefung(asm, ma)
        auf = p.werkzeugaufnahme(1)
        for winkel in (0, 45, 90):
            lage = App.Placement(App.Vector(15, -3, 8), App.Rotation(App.Vector(0, 1, 0), winkel))
            ein = rw.Einspannung(standard.gesamtlaenge, lage)
            m = sw.Maschine(p, auf, ein, App.Vector())
            kin = Kinematik(p, auf, ein, App.Vector())
            lang = Kinematik(p, auf, rw.Einspannung(ein.laenge + 1, lage), App.Vector())
            for wert in (0, 20):
                rund = {a.buchstabe: wert for a in m.rundachsen}
                wege = p._dreh_wege(auf, m.drehachsen, rund)
                stellungen = {a: p.verfahren.stellung_bei(a, w) for a, w in wege.items()}
                wahr = App.Vector(*kin.am_werkstueck(stellungen)) - App.Vector(
                    *lang.am_werkstueck(stellungen)
                )
                wahr.normalize()
                assert (m.richtung(rund) - wahr).Length < 1e-8, (art, winkel, rund)
                if not m.rundachsen and wert == 0:
                    assert m.loese(wahr) == [{}]
                    quer = wahr.cross(App.Vector(0, 0, 1))
                    if quer.Length < 0.1:
                        quer = wahr.cross(App.Vector(1, 0, 0))
                    assert not m.loese(quer)
        print("WERKZEUGRICHTUNG", art, "OK", flush=True)
        App.closeDocument(ma.Document.Name)


pruefen()
print("OK", pathlib.Path(__file__).name)
