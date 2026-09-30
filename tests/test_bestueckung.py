# Prüft die Bestückung je Job (W-002 Stufe G, bestueckung.py) an einem echten CAM-Job: Der
# Platz eines Werkzeugs ist die Nummer seiner Controller. Ein neues Werkzeug bekommt seinen
# Platz im Job, sonst seine Nummer, wenn frei, sonst den ersten freien; FreeCADs unbenutzter
# „TC: …“ zählt nicht. Umlegen tauscht mit dem Werkzeug, das dort steckt, und benennt die
# Controller um; zwei Werkzeuge auf einem Platz findet doppelt(). Ohne Revolver gilt die
# Nummer aus der Werkzeugverwaltung, sind alle Plätze belegt: None.
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part  # noqa: F401 – lädt das Part-Modul für „Part::Box“
from Path.Main import Job
from Path.Tool.camassets import user_asset_store

from camaddon import bestueckung as bs
from camaddon import job_schnittwerte as js
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


vorher_sprache = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
fraeser = wz.Werkzeug(nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26)
fraeser.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15)]
bohrer = wz.Werkzeug(nummer=3, art=wz.BOHRER, durchmesser=8.5, schneiden=2)  # auch Nummer 3
bohrer.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=80, fz=0.1)]
kugel = wz.Werkzeug(nummer=0, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)  # ohne Nummer
kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.DYNAMISCH, ae=0.5, ap=5, vc=100, fz=0.05)]
bibliothek = wz.Bibliothek([fraeser, bohrer, kugel])
ue.uebergeben(bibliothek)

dok = FreeCAD.newDocument("Bestueckung")
quader = dok.addObject("Part::Box", "Quader")
dok.recompute()
job = Job.Create("Job", [quader])
PLAETZE = list(range(1, 7))  # ein Revolver mit sechs Plätzen


def einsatz(werkzeug):
    return werkzeug.schnittwerte[wz.ALLE][0]


def auf():
    """{Nummer: [Kennung …]} – was im Job wo steckt."""
    return {
        n: sorted(e.werkzeug.kennung for e in es)
        for n, es in bs.auf_plaetzen(job, bibliothek).items()
    }


# FreeCADs „TC: …“ – kein Werkzeug aus der Werkzeugverwaltung, von keiner Operation benutzt.
pruefe(len(js.werkzeug_controller(job)) == 1, "der Job hat keinen eigenen Controller")
pruefe(bs.eintraege(job, bibliothek) == [], f"fremder Controller zählt: {auf()}")

# Der Fräser (T3) bekommt P3; im Job steht er dann dort.
pruefe(bs.platz_fuer(job, fraeser, bibliothek, PLAETZE) == 3, "Fräser nicht auf P3")
tc_fraeser = js.controller_ohne_transaktion(dok, job, fraeser, einsatz(fraeser), nummer=3)
pruefe(tc_fraeser.ToolNumber == 3 and tc_fraeser.Label.startswith("T3 "), tc_fraeser.Label)
pruefe(auf() == {3: [fraeser.kennung]}, f"Fräser auf P3: {auf()}")
pruefe(bs.platz_fuer(job, fraeser, bibliothek, PLAETZE) == 3, "Fräser im Job nicht auf P3")
# Der Bohrer hat auch die Nummer 3 – belegt: der erste freie Platz, P1 (den hat FreeCADs
# „TC: …“, aber der zählt nicht). Ist P1 für ein anderes Werkzeug vorgemerkt: P2.
pruefe(bs.platz_fuer(job, bohrer, bibliothek, PLAETZE) == 1, "Bohrer nicht auf P1")
vorgemerkt = {1: kugel.kennung}
pruefe(bs.platz_fuer(job, bohrer, bibliothek, PLAETZE, vorgemerkt) == 2, "vorgemerkt: nicht P2")
pruefe(
    bs.platz_fuer(job, bohrer, bibliothek, PLAETZE, {1: bohrer.kennung}) == 1,
    "für sich selbst vorgemerkt",
)
tc_bohrer = js.controller_ohne_transaktion(dok, job, bohrer, einsatz(bohrer), nummer=1)
# Ein zweiter Controller für den Fräser (anderer Einsatz) steckt auf demselben Platz.
tc_fraeser2 = js.controller_ohne_transaktion(dok, job, fraeser, einsatz(fraeser), nummer=3)
eintraege = bs.eintraege(job, bibliothek)
pruefe(
    [(e.werkzeug.kennung, len(e.controller), e.nummer) for e in eintraege]
    == [(fraeser.kennung, 2, 3), (bohrer.kennung, 1, 1)],
    f"Einträge: {[(e.schluessel, len(e.controller), e.nummern) for e in eintraege]}",
)
pruefe(bs.doppelt(job, bibliothek) == [], "doppelt ohne Grund")
pruefe(bs.text(eintraege[0]) == "Schaftfräser Ø 12 · z 3 · VHM", f"Text: {bs.text(eintraege[0])}")
pruefe(bs.kurz(eintraege[1]) == "Bohrer Ø 8.5", f"Kurz: {bs.kurz(eintraege[1])}")

# Umlegen: der Fräser auf P1 – der Bohrer bekommt P3, die Namen folgen.
dok.openTransaction("umlegen")
geaendert = bs.lege_um(job, eintraege[0], 1, bibliothek)
dok.commitTransaction()
pruefe(auf() == {1: [fraeser.kennung], 3: [bohrer.kennung]}, f"getauscht: {auf()}")
pruefe(len(geaendert) == 3, f"geändert: {[tc.Label for tc in geaendert]}")
pruefe(
    tc_fraeser.Label.startswith("T1 ") and tc_bohrer.Label.startswith("T3 "),
    f"Namen: {tc_fraeser.Label}, {tc_bohrer.Label}",
)
# Auf einen freien Platz: nur der Bohrer zieht um.
bs.lege_um(job, bs.eintrag_von(job, bohrer, bibliothek), 5, bibliothek)
pruefe(auf() == {1: [fraeser.kennung], 5: [bohrer.kennung]}, f"auf P5: {auf()}")

# Zwei Werkzeuge auf einem Platz (von Hand gesetzt): doppelt() findet es.
tc_bohrer.ToolNumber = 1
doppelt = [(n, sorted(e.werkzeug.kennung for e in es)) for n, es in bs.doppelt(job, bibliothek)]
pruefe(doppelt == [(1, sorted([fraeser.kennung, bohrer.kennung]))], f"doppelt: {doppelt}")
tc_bohrer.ToolNumber = 5

# Ohne Revolver die Nummer aus der Werkzeugverwaltung; alle Plätze belegt: None.
pruefe(bs.platz_fuer(job, kugel, bibliothek, []) == 0, "ohne Revolver nicht die Nummer")
pruefe(bs.platz_fuer(job, kugel, bibliothek, [1, 5]) is None, "voll, aber ein Platz")
pruefe(bs.platz_fuer(job, kugel, bibliothek, [1, 5, 6]) == 6, "nicht der freie P6")
pruefe(bs.platz_fuer(None, bohrer, bibliothek, PLAETZE) == 3, "ohne Job nicht die Nummer")

# Umbenennen nur, wo der Name mit der Nummer beginnt.
pruefe(bs.umbenannt("T3 Schruppen", 3, 5) == "T5 Schruppen", "T3 → T5")
pruefe(bs.umbenannt("T33 Schruppen", 3, 5) == "T33 Schruppen", "T33 umbenannt")
pruefe(bs.umbenannt("T3", 3, 5) == "T5", "nur „T3“")
pruefe(bs.umbenannt("TC: 5mm Endmill", 1, 5) == "TC: 5mm Endmill", "fremder Name umbenannt")

FreeCAD.closeDocument(dok.Name)
sprache.setze_sprache(vorher_sprache)
if fehler:
    raise AssertionError("\n".join(fehler))
# FreeCADCmd 1.1.3 schreibt beim Neuberechnen einen Fortschrittsbalken ohne
# Zeilenende – „OK“ muss auf einer eigenen Zeile stehen (scripts/tests_ausfuehren.sh).
print()
print("OK", os.path.basename(__file__))
