# SPDX-License-Identifier: LGPL-2.1-or-later
"""Räumen und Planfräsen vergleichen ihre Varianten mit Eilgang und Beschleunigung der Maschine des
Jobs (Frage 13; Manuel, 2026-10-11: „Ja, mit der Maschine“): Die Liste der Maschinen kennt den
kleinsten Eilgang und die kleinste Beschleunigung der Linearachsen, `merke_maschine` schreibt sie an
den Job, `dynamik_des_jobs` liest sie (mm/min, mm/s²). Ohne sie rechnet alles wie vorher; mit einer
langsamen Maschine dauert dieselbe Bahn länger, mit einer schnellen kürzer."""

import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD as App
import Part

from camaddon import beispielmaschine as bm
from camaddon import fraeserform as ff
from camaddon import hoehenfeld as hf
from camaddon import maschinenspeicher as msp
from camaddon import planfraesen_bahn as pb
from camaddon import raeumen as ra
from camaddon import raeumen_bahn as rb
from camaddon import sprache
from camaddon import werkzeuge as wz

sprache.setze_sprache("de")
V = App.Vector

# Die Liste: die 3-Achs-Beispielfräse – X, Y 20 m/min, Z 15 m/min, 3 m/s².
asm, ma = bm.fraesmaschine()
eintrag = msp.beschreibe(asm, ma)
assert (eintrag.eilgang, eintrag.beschleunigung) == (15000.0, 3.0), eintrag
App.closeDocument(asm.Document.Name)
asm, ma = bm.portalfraese()
eintrag_portal = msp.beschreibe(asm, ma)
assert (eintrag_portal.eilgang, eintrag_portal.beschleunigung) == (10000.0, 1.0), eintrag_portal
App.closeDocument(asm.Document.Name)

# Am Job: versteckt gemerkt, gelesen in mm/min und mm/s²; ohne Maschine 0.
doc = App.newDocument("Dynamik")
job = doc.addObject("App::FeaturePython", "Job")
assert msp.dynamik_des_jobs(job) == (0.0, 0.0)
assert msp.dynamik_des_jobs(None) == (0.0, 0.0)
msp.dynamik_merken(job, eintrag)
assert msp.dynamik_des_jobs(job) == (15000.0, 3000.0), msp.dynamik_des_jobs(job)
assert job.getEditorMode(msp.EIGENSCHAFT_EILGANG) == ["Hidden"]
msp.dynamik_merken(job, eintrag_portal)
assert msp.dynamik_des_jobs(job) == (10000.0, 1000.0)
App.closeDocument(doc.Name)

# Dieselbe Bahn: langsam länger, schnell kürzer; ohne Werte wie bisher (0 = die Vorgaben).
w = wz.standardwerkzeug()
form = ff.scheibe(w.durchmesser / 2)
einsatz = next(e for e in w.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
teil = Part.makeBox(50, 50, 20).fuse(Part.makeCylinder(5, 10, V(25, 25, 20))).removeSplitter()
ebenen = [e for e in hf.ebenen_oben(teil) if abs(e.z - 20.0) < 1e-6]
netz = hf.netze_je_hoehe(teil, ebenen)
zeiten = {}
for name, (eilgang, beschleunigung) in (
    ("vorgabe", (0.0, 0.0)),
    ("ausdruecklich", (10000.0, 1000.0)),
    ("langsam", (3000.0, 300.0)),
    ("schnell", (40000.0, 6000.0)),
):
    werte = rb.Raeumwerte(
        form, einsatz.ap, einsatz.ae, 0.3, 30.0, 35.0, (-1.0, 51.0, -1.0, 51.0),
        variante="rohteil", schneidenlaenge=w.schneidenlaenge, eintauchwinkel=w.eintauchwinkel,
        vorschub=902.0, eintauchen=270.6, eilgang=eilgang, beschleunigung=beschleunigung,
    )  # fmt: skip
    plan = pb.Planwerte(
        form, einsatz.ap, einsatz.ae, 0.0, 30.0, 35.0, (-1.0, 51.0, -1.0, 51.0), laengs=True,
        vorschub=902.0, eintauchen=270.6, eilgang=eilgang, beschleunigung=beschleunigung,
    )  # fmt: skip
    zeiten[name] = (
        rb.planen(netz, werte, ebenen, ra.konturen_des_teils(teil)).zeit,
        pb.planen(netz, plan, ebenen).zeit,
    )
for k in range(2):
    assert abs(zeiten["vorgabe"][k] - zeiten["ausdruecklich"][k]) < 1e-9, zeiten
    assert zeiten["schnell"][k] < zeiten["vorgabe"][k] < zeiten["langsam"][k], zeiten
print({k: tuple(round(z, 3) for z in v) for k, v in zeiten.items()})
print("OK", os.path.basename(__file__))
