# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das gespeicherte Simultanbeispiel im vorhandenen Materialbild vorwärts/zurück fahren."""

import json
import os
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import reichweite as rw
from camaddon import restmaterial as rm
from camaddon import simultan_restbild as sb
from camaddon import sprache
from camaddon import werkzeuge as wz


def pruefung():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    out = ROOT / "beispiele/grob_g550_freiform"
    user_asset_store.set_dir(out / "assets")
    bib = wz.Bibliothek.laden(str(out / "beispiel_werkzeuge.json"))
    bib.speichern()
    doc = App.openDocument(str(out / "freiform_5achs.FCStd"))
    md = App.openDocument(str(out / "g550_winkelaufnahme.FCStd"))
    p = rw.Pruefung(md.Assembly, md.Maschine)
    fahrt = ab.abfahrt(p, doc.Job, rw.nullpunkt(doc.Job), bib)
    spitzen = fahrt.am_werkstueck()
    start = time.monotonic()
    bild = sb.fuer(fahrt, doc.Job, spitzen)
    assert isinstance(bild, sb.SimultanRestbild), "Simultanjob hat kein Materialbild"
    assert np.all(bild.quader.h == bild.quader.z_bis)
    bild.bis_station(bild.letzte())
    fertig = bild.quader.h.copy()
    vergleich = bild.vergleich()
    assert vergleich.groesster < 0.05, vergleich.groesster
    assert vergleich.kleinster >= -rm.BLAU_AB, vergleich.kleinster
    assert np.any(vergleich.farbe == rm.GRUEN)
    assert not np.any(vergleich.farbe == rm.BLAU)
    # Gegenprobe: Die Spitze als senkrechte Kugelspitze zu lesen schnitte beim Anstellen
    # um R*(1-cos(Winkel)) tiefer; die Mitte muss tatsächlich an einer anderen Stelle liegen.
    indices = np.flatnonzero(bild.operation == 1)
    assert np.max(np.linalg.norm(bild.punkte[indices] - np.asarray(spitzen)[indices], axis=1)) > 0.5
    bild.bis_station(0)
    assert np.all(bild.quader.h == bild.quader.z_bis), "Rückwärtsfahren lässt Abtrag stehen"
    bild.bis_station(bild.letzte() // 2)
    assert np.any(bild.quader.h < bild.quader.z_bis)
    bild.bis_station(bild.letzte())
    assert np.array_equal(bild.quader.h, fertig), "Vorwärts/Zurück verändert das Materialbild"
    print(
        "RESTBILD",
        json.dumps({"laufzeit_s": time.monotonic() - start, "rest_mm": vergleich.groesster}),
        flush=True,
    )
    App.closeDocument(doc.Name)
    App.closeDocument(md.Name)


pruefung()
print("OK", os.path.basename(__file__))
