# Prüft das Maschinenobjekt: Anlegen in der Assembly, Betriebsarten (auch zwei
# an einem Gelenk: S4/C4), Aufnahmen, Tisch/Kopf-Zuordnung, die Prüf-
# meldungen, Speichern/Laden und Rückgängig.
import math
import os
import sys
import tempfile
from types import SimpleNamespace

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))
sys.path.insert(0, HIER)

import beispielmaschinen
import FreeCAD as App

from camaddon import kette
from camaddon import maschine as m

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
pruefe(
    schluessel(m.pruefe(ma))
    == ["maschine.keine_werkstueckaufnahme", "maschine.keine_werkzeugaufnahme"],
    f"leere Maschine: {schluessel(m.pruefe(ma))}",
)

z1 = m.neue_betriebsart(ma, obj("Z"), m.ART_LINEAR, "Z1")
x1 = m.neue_betriebsart(ma, obj("X"), m.ART_LINEAR, "X1")
s4 = m.neue_betriebsart(ma, obj("Spindel"), m.ART_SPINDEL, "S4")
c4 = m.neue_betriebsart(ma, obj("Spindel"), m.ART_POSITIONIEREN, "C4")
z1.Eilgang = 30000
x1.Eilgang = 24000
s4.Drehzahl = 4000
c4.Geschwindigkeit = 100
futter = m.neue_aufnahme(ma, obj("Spannflaeche"), m.AUFNAHME_WERKSTUECK, "Futter", spindel=s4)
pruefe(m.name_von(futter) == "Futter", f"Aufnahme heißt nicht „Futter“: {m.name_von(futter)}")
rev = m.neue_betriebsart(ma, obj("Revolverachse"), m.ART_REVOLVER, "T")
k = kette.lies_kette(asm)
pruefe(
    "maschine.revolver_ohne_plaetze" in schluessel(m.pruefe(ma, k)),
    "Revolver ohne Plätze nicht gemeldet",
)

# Verteilhilfe: 12 Plätze um die Revolverachse, P1 = der vorhandene Werkzeugplatz.
lcs_vorher = len([o for o in doc.Objects if o.isDerivedFrom("App::LocalCoordinateSystem")])
liste = m.verteile_plaetze(ma, k, rev, obj("Werkzeugplatz"), 12)
doc.recompute()
pruefe(
    [a.Bezeichnung for a in liste] == [f"P{i}" for i in range(1, 13)],
    f"Platznamen: {[a.Bezeichnung for a in liste]}",
)
pruefe(
    [a.Bezeichnung for a in m.plaetze(ma, k, rev)] == [f"P{i}" for i in range(1, 13)],
    "plaetze() findet nicht alle 12",
)
achse = k.achse_von(obj("Revolverachse"))
punkte = [m.globale_platzierung(a.Lcs).Base for a in liste]


def radius(p):
    return (p - achse.ursprung).cross(achse.richtung).Length


pruefe(
    all(abs(radius(p) - radius(punkte[0])) < 1e-6 for p in punkte) and radius(punkte[0]) > 1,
    f"Plätze nicht auf einem Kreis um die Revolverachse: {[round(radius(p), 3) for p in punkte]}",
)
pruefe(
    abs((punkte[1] - punkte[0]).Length - 2 * radius(punkte[0]) * math.sin(math.pi / 12)) < 1e-6,
    "Plätze nicht im 30°-Abstand",
)
# Nochmal verteilen (6 statt 12) ersetzt die alten Plätze und LCS restlos.
liste = m.verteile_plaetze(ma, k, rev, obj("Werkzeugplatz"), 6)
doc.recompute()
lcs_nachher = len([o for o in doc.Objects if o.isDerivedFrom("App::LocalCoordinateSystem")])
pruefe(
    len(m.plaetze(ma, k, rev)) == 6 and lcs_nachher == lcs_vorher + 5,
    f"Neu verteilen: {len(m.plaetze(ma, k, rev))} Plätze, {lcs_nachher - lcs_vorher} neue LCS",
)
doc.recompute()

pruefe(m.pruefe(ma) == [], f"vollständige Drehmaschine: {[x.text for x in m.pruefe(ma)]}")
rollen, _ = m.rollen(kette.lies_kette(asm), ma)
pruefe(rollen.get(obj("Spindel")) == m.TISCH, "Hauptspindel sitzt nicht im Tisch")
pruefe(
    rollen.get(obj("X")) == m.KOPF and rollen.get(obj("Z")) == m.KOPF, "X/Z sitzen nicht im Kopf"
)
pruefe(rollen.get(obj("Revolverachse")) == m.KOPF, "Revolverachse sitzt nicht im Kopf")

# Sichtbarkeit im Eigenschaften-Editor folgt der Art.
pruefe(
    s4.getEditorMode("Drehzahl") == [] and "Hidden" in s4.getEditorMode("Eilgang"),
    f"Spindel zeigt falsche Werte: {s4.getEditorMode('Drehzahl')}, {s4.getEditorMode('Eilgang')}",
)

# Fehler, die gemeldet werden müssen.
x1.NcName = "z1"  # doppelt (Groß/Klein egal)
s4.Drehzahl = 0  # Pflichtwert fehlt
falsch = m.neue_betriebsart(ma, obj("X"), m.ART_SPINDEL, "S9")  # Spindel an Schiebegelenk
falsch.Drehzahl = 1
erwartet = ["maschine.art_passt_nicht", "maschine.name_doppelt", "maschine.pflichtwert_fehlt"]
pruefe(
    schluessel(m.pruefe(ma)) == erwartet,
    f"Fehlerfälle: {schluessel(m.pruefe(ma))}, erwartet {erwartet}",
)
texte = " ".join(x.text for x in m.pruefe(ma))
pruefe("{" not in texte, f"Platzhalter nicht gefüllt: {texte}")
doc.removeObject(falsch.Name)
x1.NcName, s4.Drehzahl = "X1", 4000

# Gelenk gelöscht: Betriebsart bleibt, wird gemeldet.
doc.openTransaction("Gelenk löschen")
doc.removeObject("X")
doc.commitTransaction()
pruefe(
    x1.Gelenk is None and "maschine.gelenk_fehlt" in schluessel(m.pruefe(ma)),
    "gelöschtes Gelenk nicht als fehlend gemeldet",
)
doc.undo()
pruefe(
    x1.Gelenk is not None and x1.Gelenk.Name == "X",
    "Rückgängig stellt den Verweis nicht wieder her",
)

# Speichern und Laden.
pfad = os.path.join(tempfile.mkdtemp(), "drehmaschine.FCStd")
doc.saveAs(pfad)
App.closeDocument(doc.Name)
doc = App.openDocument(pfad)
ma = m.finde_maschine(doc.getObject("Assembly"))
pruefe(ma is not None, "Maschine nach dem Laden nicht gefunden")
if ma:
    namen = sorted(ba.NcName for ba in m.betriebsarten(ma))
    pruefe(namen == ["C4", "S4", "T", "X1", "Z1"], f"nach dem Laden: {namen}")
    pruefe(m.pruefe(ma) == [], f"nach dem Laden: {[x.text for x in m.pruefe(ma)]}")
    s4 = next(ba for ba in m.betriebsarten(ma) if ba.NcName == "S4")
    pruefe("Hidden" in s4.getEditorMode("Eilgang"), "Sichtbarkeit nach dem Laden verloren")
App.closeDocument(doc.Name)

# --- Vorschlag (D-25): Die Testdrehmaschine bekommt S1, Z1, X1 und T ---------------------------
asm = beispielmaschinen.drehmaschine()
ma = m.lege_maschine_an(asm)
k = kette.lies_kette(asm)
paare = sorted((ba.Gelenk.Label, ba.Art, ba.NcName) for ba in m.schlage_betriebsarten_vor(ma, k))
pruefe(
    paare
    == [
        ("Revolverachse", m.ART_REVOLVER, "T"),
        ("Spindel", m.ART_SPINDEL, "S1"),
        ("X", m.ART_LINEAR, "X1"),
        ("Z", m.ART_LINEAR, "Z1"),
    ],
    f"Vorschlag: {paare}",
)
pruefe(m.schlage_betriebsarten_vor(ma, k) == [], "zweiter Vorschlag legt noch etwas an")


def gedachte_achse(name, art, richtung=(1, 0, 0)):
    """Nur, was der Vorschlag braucht: Gelenk mit Namen, Art, Richtung."""
    return SimpleNamespace(
        gelenk=SimpleNamespace(Label=name), art=art, richtung=App.Vector(*richtung)
    )


# Vergebene Namen zählen weiter; der Buchstabe aus dem Namen, sonst aus der Richtung.
for name, art, richtung, betriebsart, erwartet in (
    ("X-Schlitten", kette.LINEAR, (1, 0, 0), m.ART_LINEAR, "X2"),
    ("Schlitten", kette.LINEAR, (0, 0.6, 0.8), m.ART_LINEAR, "Z2"),
    ("Schlitten", kette.LINEAR, (0, -1, 0), m.ART_LINEAR, "Y1"),
    ("Schlitten_Z3", kette.LINEAR, (1, 0, 0), m.ART_LINEAR, "Z3"),
    ("Joint001", kette.DREH, (0, 0, 1), m.ART_POSITIONIEREN, "C1"),
    ("Achse B", kette.DREH, (1, 0, 0), m.ART_POSITIONIEREN, "B1"),
    ("Gegenspindel", kette.DREH, (1, 0, 0), m.ART_SPINDEL, "S2"),
    ("Revolver 2", kette.DREH, (1, 0, 0), m.ART_REVOLVER, "T2"),
):
    vorschlag = m.vorgeschlagener_name(ma, gedachte_achse(name, art, richtung), betriebsart)
    pruefe(vorschlag == erwartet, f"Name für „{name}“: {vorschlag} statt {erwartet}")
for name, art, erwartet in (
    ("Z", kette.LINEAR, m.ART_LINEAR),
    ("Hauptspindel", kette.DREH, m.ART_SPINDEL),
    ("Spindle", kette.DREH, m.ART_SPINDEL),
    ("Revolverachse", kette.DREH, m.ART_REVOLVER),
    ("Turret", kette.DREH, m.ART_REVOLVER),
    ("Schwenkkopf", kette.DREH, m.ART_POSITIONIEREN),
):
    vorschlag = m.vorgeschlagene_art(gedachte_achse(name, art))
    pruefe(vorschlag == erwartet, f"Art für „{name}“: {vorschlag} statt {erwartet}")
App.closeDocument(asm.Document.Name)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
