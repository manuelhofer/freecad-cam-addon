# Prüft das Maschinenobjekt: Anlegen in der Assembly, Betriebsarten (auch zwei
# an einem Gelenk: S4/C4), Aufnahmen, Tisch/Kopf-Zuordnung, die Prüf-
# meldungen, Speichern/Laden und Rückgängig.
import os
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))
sys.path.insert(0, HIER)

import FreeCAD as App  # noqa: E402

import beispielmaschinen  # noqa: E402
from camaddon import kette, maschine as m  # noqa: E402

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def schluessel(meldungen):
    return sorted(x.schluessel for x in meldungen)


asm = beispielmaschinen.drehmaschine()
doc = asm.Document
obj = doc.getObject

doc.UndoMode = 1
doc.openTransaction("Maschine anlegen")
ma = m.lege_maschine_an(asm)
doc.commitTransaction()
pruefe(ma in asm.Group, "Maschinenobjekt liegt nicht in der Assembly")
pruefe(m.lege_maschine_an(asm) is ma, "zweites Anlegen erzeugt eine zweite Maschine")
pruefe(asm.solve() == 0, "Assembly löst nicht mehr, seit das Maschinenobjekt drin ist")

# Leere Maschine: nur die zwei Hinweise auf fehlende Aufnahmen.
pruefe(schluessel(m.pruefe(ma)) == ["maschine.keine_werkstueckaufnahme", "maschine.keine_werkzeugaufnahme"],
       f"leere Maschine: {schluessel(m.pruefe(ma))}")

z1 = m.neue_betriebsart(ma, obj("Z"), m.ART_LINEAR, "Z1")
x1 = m.neue_betriebsart(ma, obj("X"), m.ART_LINEAR, "X1")
s4 = m.neue_betriebsart(ma, obj("Spindel"), m.ART_SPINDEL, "S4")
c4 = m.neue_betriebsart(ma, obj("Spindel"), m.ART_POSITIONIEREN, "C4")
for ba, wert in ((z1, ("Eilgang", 30000)), (x1, ("Eilgang", 24000)), (s4, ("Drehzahl", 4000)),
                 (c4, ("Geschwindigkeit", 100))):
    setattr(ba, *wert)
m.neue_aufnahme(ma, obj("Werkzeugplatz"), m.AUFNAHME_WERKZEUG, "Revolver")
m.neue_aufnahme(ma, obj("Spannflaeche"), m.AUFNAHME_WERKSTUECK, "Futter", spindel=s4)
doc.recompute()

pruefe(m.pruefe(ma) == [], f"vollständige Drehmaschine: {[x.text for x in m.pruefe(ma)]}")
rollen, _ = m.rollen(kette.lies_kette(asm), ma)
pruefe(rollen.get(obj("Spindel")) == m.TISCH, "Hauptspindel sitzt nicht im Tisch")
pruefe(rollen.get(obj("X")) == m.KOPF and rollen.get(obj("Z")) == m.KOPF, "X/Z sitzen nicht im Kopf")

# Sichtbarkeit im Eigenschaften-Editor folgt der Art.
pruefe(s4.getEditorMode("Drehzahl") == [] and "Hidden" in s4.getEditorMode("Eilgang"),
       f"Spindel zeigt falsche Werte: {s4.getEditorMode('Drehzahl')}, {s4.getEditorMode('Eilgang')}")

# Fehler, die gemeldet werden müssen.
x1.NcName = "z1"  # doppelt (Groß/Klein egal)
s4.Drehzahl = 0  # Pflichtwert fehlt
falsch = m.neue_betriebsart(ma, obj("X"), m.ART_SPINDEL, "S9")  # Spindel an Schiebegelenk
falsch.Drehzahl = 1
erwartet = ["maschine.art_passt_nicht", "maschine.name_doppelt", "maschine.pflichtwert_fehlt"]
pruefe(schluessel(m.pruefe(ma)) == erwartet, f"Fehlerfälle: {schluessel(m.pruefe(ma))}, erwartet {erwartet}")
texte = " ".join(x.text for x in m.pruefe(ma))
pruefe("{" not in texte, f"Platzhalter nicht gefüllt: {texte}")
doc.removeObject(falsch.Name)
x1.NcName, s4.Drehzahl = "X1", 4000

# Gelenk gelöscht: Betriebsart bleibt, wird gemeldet.
doc.openTransaction("Gelenk löschen")
doc.removeObject("X")
doc.commitTransaction()
pruefe(x1.Gelenk is None and "maschine.gelenk_fehlt" in schluessel(m.pruefe(ma)),
       "gelöschtes Gelenk nicht als fehlend gemeldet")
doc.undo()
pruefe(x1.Gelenk is not None and x1.Gelenk.Name == "X", "Rückgängig stellt den Verweis nicht wieder her")

# Speichern und Laden.
pfad = os.path.join(tempfile.mkdtemp(), "drehmaschine.FCStd")
doc.saveAs(pfad)
App.closeDocument(doc.Name)
doc = App.openDocument(pfad)
ma = m.finde_maschine(doc.getObject("Assembly"))
pruefe(ma is not None, "Maschine nach dem Laden nicht gefunden")
if ma:
    namen = sorted(ba.NcName for ba in m.betriebsarten(ma))
    pruefe(namen == ["C4", "S4", "X1", "Z1"], f"nach dem Laden: {namen}")
    pruefe(m.pruefe(ma) == [], f"nach dem Laden: {[x.text for x in m.pruefe(ma)]}")
    s4 = next(ba for ba in m.betriebsarten(ma) if ba.NcName == "S4")
    pruefe("Hidden" in s4.getEditorMode("Eilgang"), "Sichtbarkeit nach dem Laden verloren")
App.closeDocument(doc.Name)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
