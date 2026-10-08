# SPDX-License-Identifier: LGPL-2.1-or-later
"""Schruppvergleich nach Rampen/Freiwegen; der Freiformjob muss weniger leer fahren."""

import os
import pathlib
import sys
from dataclasses import replace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
from Path.Tool.camassets import user_asset_store

from camaddon import bahn as bn
from camaddon import raeumen_bahn as rb
from camaddon import restmaterial as rm
from camaddon import schruppen3d as r3
from camaddon import schruppen3d_bahn as sr
from camaddon import simultan_abtrag as sa
from camaddon import sprache
from camaddon import vierachs_schlichten as vs
from camaddon import werkzeuge as wz


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    out = ROOT / "beispiele/grob_g550_freiform"
    user_asset_store.set_dir(out / "assets")
    wz.Bibliothek.laden(str(out / "beispiel_werkzeuge.json")).speichern()
    doc = App.openDocument(str(out / "freiform_5achs.FCStd"))
    op = doc.Schruppen3D
    form = vs.form_des_controllers(op.ToolController)
    vf, ve = float(op.ToolController.HorizFeed) * 60, float(op.ToolController.VertFeed) * 60
    op.Zustellung, op.Zwischenlagen = 25, 3.5
    bahn = r3.rechne(op, doc.Job, doc.Job.Model.Group, vf, ve)
    assert bahn.zeit == min(bahn.zeiten.values()), "Vergleich enthält nicht die gefahrene Zeit"
    assert abs(bahn.zeit - bn.zeit(bahn.punkte, vf, ve)) < 1e-10
    assert bahn.zeit < 3.0, f"Schruppzeit {bahn.zeit:.3f} statt weniger als 3 min"
    assert (
        sum(not b.eilgang and a.eilgang for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False))
        <= 30
    ), "Zu viele getrennte Schnittzüge"
    q = rm.Quader(0, 50, 0, 40, 0, 30, schritt=0.1)
    m = sa.fahren(q, bahn.punkte, form, 1.5, 25, eintauchwinkel=2.5)
    assert not m.gruende, m.gruende
    assert m.luftanteil < 0.2, f"Luftanteil {m.luftanteil:.3f}"
    # 3,5 mm verlagert rund 837 mm³ vom Schruppen in das vollständig geprüfte
    # Schlichten. Die alte 15.000-mm³-Grenze galt nur für die 3-mm-Schruppfolge.
    assert m.volumen > 14000, "Schneller durch ausgelassenes Material"
    print("FREIFORM", bahn.zeit, bahn.zeiten, m.last_max, m.luftanteil, flush=True)

    # Gegenbeispiel zur früheren Auswahl vor dem Anlauf: zwei echte Varianten,
    # die nach zusätzlichem Rückzug ihre Reihenfolge tauschen müssen.
    w = rb.Raeumwerte(
        form=form,
        zustellung=5,
        zeilenabstand=1.5,
        aufmass=0.3,
        oben=30,
        sicher=float(op.SafeHeight),
        rohteil=(0, 50, 0, 40),
        schneidenlaenge=25,
        eintauchwinkel=2.5,
        vorschub=vf,
        eintauchen=ve,
    )
    teil = vs._teil(doc.Job.Model.Group)
    roh = sr.planen(teil, list(op.Flaechen), w)
    assert len(roh.zeiten) >= 2
    gesehen = []

    def rueckzug(b):
        gesehen.append(b.variante)
        if b.variante == roh.variante:
            p = b.punkte[-1]
            b.punkte += [replace(p, eilgang=True, z=p.z + 10000), p]
        b.zeit = bn.zeit(b.punkte, vf, ve)

    fertig = sr.planen(teil, list(op.Flaechen), w, nachbereiten=rueckzug)
    assert set(gesehen) == set(roh.zeiten), "Nur der ursprüngliche Sieger nachbereitet"
    assert fertig.variante != roh.variante, "Sieger vor dem Anlauf ausgewählt"
    assert fertig.zeit == min(fertig.zeiten.values())
    App.closeDocument(doc.Name)


pruefen()
print("OK", pathlib.Path(__file__).name)
