# Prüft das Auslesen der kinematischen Kette an den Beispielmaschinen:
# Glieder, Baum vom Bett aus, Achsrichtungen, Grenzen, zweites Lager einer
# Schwenkbrücke und die Warnungen.
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))
sys.path.insert(0, HIER)

import beispielmaschinen
import FreeCAD as App

from camaddon import kette

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def parallel(vektor, x, y, z):
    return abs(abs(vektor.dot(App.Vector(x, y, z))) - 1) < 1e-6


def achse(k, gelenk_name):
    return next((a for a in k.achsen if a.gelenk.Name == gelenk_name), None)


def achsnamen(k):
    return sorted(a.gelenk.Name for a in k.achsen)


def glied(k, bauteil_name):
    return k.glied_von(App.ActiveDocument.getObject(bauteil_name))


def schluessel(k):
    return sorted(m.schluessel for m in k.meldungen)


# --- Drehmaschine ---------------------------------------------------------
k = kette.lies_kette(beispielmaschinen.drehmaschine())
pruefe(len(k.glieder) == 5, f"Drehmaschine: 5 Glieder erwartet, {len(k.glieder)} gefunden")
pruefe(len(k.achsen) == 4, f"Drehmaschine: 4 Achsen erwartet, {len(k.achsen)}")
pruefe(
    k.meldungen == [], f"Drehmaschine: keine Meldungen erwartet: {[m.text for m in k.meldungen]}"
)
pruefe(glied(k, "Spindelstock") is k.bett(), "Spindelstock gehört nicht zum Bett")
pruefe(glied(k, "Futter") is glied(k, "Hauptspindel"), "Futter bildet kein Glied mit der Spindel")
spindel, z, x = achse(k, "Spindel"), achse(k, "Z"), achse(k, "X")
pruefe(
    spindel and spindel.art == kette.DREH and parallel(spindel.richtung, 0, 0, 1),
    "Spindel: Drehachse entlang Z erwartet",
)
pruefe(z and z.art == kette.LINEAR and parallel(z.richtung, 0, 0, 1), "Z: Richtung Z erwartet")
pruefe(x and parallel(x.richtung, 1, 0, 0), "X: Richtung X erwartet")
pruefe(
    x and (x.minimum, x.maximum) == (0, 200),
    f"X: Grenzen 0/200 erwartet, {x and (x.minimum, x.maximum)}",
)
pruefe(z and (z.minimum, z.maximum) == (None, None), "Z: ohne Grenzen erwartet")
pruefe(x and x.eltern is glied(k, "ZSchlitten"), "X hängt nicht am Z-Schlitten")
pruefe(
    [a.gelenk.Name for a in k.pfad_zum_bett(glied(k, "Revolver"))] == ["Revolverachse", "X", "Z"],
    "Pfad Revolver → Bett nicht Revolverachse, X, Z",
)
pruefe(
    glied(k, "Werkzeugplatz") is glied(k, "Revolver"),
    "LCS im Revolver-Part nicht dem Revolver zugeordnet",
)
App.closeDocument(App.ActiveDocument.Name)

# --- Fünfachser mit Schwenkbrücke, Wiege in einem Drehgelenk --------------
k = kette.lies_kette(beispielmaschinen.fuenfachser(zweites_lager=False))
wiege = glied(k, "Wiege")
pruefe(
    wiege is glied(k, "SchenkelLinks") is glied(k, "SchenkelRechts"),
    "Schenkel bilden kein Glied mit der Wiege",
)
pruefe(glied(k, "LagerbockRechts") is k.bett(), "Lagerbock rechts gehört nicht zum Bett")
a = achse(k, "A")
pruefe(
    a and a.eltern is k.bett() and parallel(a.richtung, 1, 0, 0),
    "A: am Bett, Drehachse entlang X erwartet",
)
c = achse(k, "C")
pruefe(
    c and c.eltern is wiege and parallel(c.richtung, 0, 0, 1), "C: auf der Wiege, Achse Z erwartet"
)
pruefe(
    achsnamen(k) == ["A", "C", "S", "Z"], f"Fünfachser: Achsen A, C, S, Z erwartet, {achsnamen(k)}"
)
erwartet = sorted(
    [
        "kette.gelenkart_nicht_unterstuetzt",
        "kette.koerper_lose",
        "kette.glied_haengt_nicht_am_bett",
    ]
)
pruefe(schluessel(k) == erwartet, f"Fünfachser: Meldungen {schluessel(k)}, erwartet {erwartet}")
App.closeDocument(App.ActiveDocument.Name)

# --- dieselbe Maschine, Wiege zusätzlich im zweiten Lagerbock gelagert ----
# Die Assembly kann das nicht lösen; das Addon muss es erkennen und erklären.
k = kette.lies_kette(beispielmaschinen.fuenfachser(zweites_lager=True))
pruefe(
    "kette.doppelt_gelagert" in schluessel(k), f"doppelte Lagerung nicht gemeldet: {schluessel(k)}"
)
pruefe(
    achsnamen(k) == ["A", "C", "S", "Z"],
    "doppelte Lagerung: A_Lager2 darf keine eigene Achse werden",
)
App.closeDocument(App.ActiveDocument.Name)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
