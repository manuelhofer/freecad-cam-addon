# SPDX-License-Identifier: LGPL-2.1-or-later
"""Frisch geladener echter Export gegen die bereits geometrisch geprüfte NC-Referenz."""

import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
from Path.Tool.camassets import user_asset_store

from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import sprache
from camaddon import werkzeuge as wz


def pruefen():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    out = ROOT / "beispiele/grob_g550_freiform"
    user_asset_store.set_dir(out / "assets")
    bib = wz.Bibliothek.laden(str(out / "beispiel_werkzeuge.json"))
    bib.speichern()
    doc = App.openDocument(
        os.environ.get("SIMULTAN_NC_DOKUMENT", str(out / "freiform_5achs.FCStd"))
    )
    md = App.openDocument(str(out / "g550_winkelaufnahme.FCStd"))
    p = rw.Pruefung(md.Assembly, md.Maschine)

    def maschine(op):
        tc = op.ToolController
        return sw.Maschine(
            p, p.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, bib), rw.nullpunkt(doc.Job)
        )

    steuerung = pp.steuerung("siemens")
    info = pp.maschineninfo_dokument(md)
    programm = pp.programm(pp.abschnitte(doc.Job, maschine), steuerung, info, "G550_FREIFORM")
    befunde, saetze = pp.nachlesen(programm, steuerung, info)
    assert not befunde, befunde
    suffix = "_gesamt" if str(doc.Schlichten3D.Kippachse) == "frei_gesamt" else ""
    soll = json.loads((ROOT / f"tests/golden/freiform_simultan{suffix}_nc.json").read_text())
    ist = hashlib.sha256(programm.text.encode()).hexdigest()
    assert ist == soll["sha256"], "Tatsächlicher frischer NC-Export verändert"
    assert saetze == soll["nc_saetze"], "Andere NC-Bewegungszahl"
    print("REFERENZ", suffix or "frei", saetze, ist, flush=True)
    App.closeDocument(doc.Name)
    App.closeDocument(md.Name)


pruefen()
print("OK", pathlib.Path(__file__).name)
