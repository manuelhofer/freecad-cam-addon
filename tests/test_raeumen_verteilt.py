# Prüft das Räumen auf den Nebenrechnern (raeumen_bahn._Verteilt): Alle Varianten rechnen dort,
# auch der Adaptiv-Kern und feiner(); der Merker des Kerns (_ADAPTIV) geht mit und kommt zurück.
# Je Schritt ist die verteilte Bahn Satz für Satz die, die der Hauptprozess mit seinem Merker
# rechnet – ohne den Kern noch einmal zu fragen (er rechnet nie zweimal dasselbe): an einer Platte
# mit Zapfen und Tasche, mit geänderten Werten, mit einem Merker, den nur der Hauptprozess kennt,
# nach geleertem Merker (die Arbeiter behalten ihren) und an einer engen Nut, an der feiner() die
# Ringe nachrechnet. „adaptiv“ geht als Erstes hinaus (die längste zuerst). Und ein Arbeiter, der
# vorgewärmt ist wie im Assistenten (gui_bearbeitung._vorwaermen), lädt beim Rechnen kein Modul
# des Addons mehr nach (mit nur raeumen_bahn vorgewärmt wartete feiner() an der Nut 0,17 s darauf).
import dataclasses
import hashlib
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import fraeserform as ff
from camaddon import gui_bearbeitung as ba
from camaddon import hoehenfeld as hf
from camaddon import nebenrechner as nr
from camaddon import raeumen as ra
from camaddon import raeumen_bahn as rb
from camaddon import sprache
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
werkzeug = wz.standardwerkzeug()
R = werkzeug.durchmesser / 2
schruppen = next(e for e in werkzeug.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
VF = 902.0

pool = nr.pool()
assert pool.verfuegbar(), "keine Nebenrechner"


def kennung(bahn):
    """Fingerabdruck der ganzen Raeumbahn – jedes Feld, jeder Satz."""
    felder = []
    for f in dataclasses.fields(bahn):
        wert = getattr(bahn, f.name)
        if f.name == "punkte":
            h = hashlib.sha256()
            for p in wert:
                h.update(repr(dataclasses.astuple(p)).encode())
            wert = (len(wert), h.hexdigest())
        felder.append((f.name, repr(wert)))
    return hashlib.sha256(repr(felder).encode()).hexdigest()[:16]


# Wie oft der Kern hier gefragt wird (im Arbeiter zählt es nicht) und was hinausgeht.
kern = [0]
bestellt = []
_kern = rb.adaptiv_kern
_auftrag = rb._Verteilt.auftrag
_anlegen = rb._Verteilt.anlegen


def gezaehlt(*a, **k):
    kern[0] += 1
    return _kern(*a, **k)


def mitgeschrieben(self, funktion, w, ebenen, schritt, *weiter, gemerkt=None):
    variante = weiter[0] if funktion == "variante_rechnen" else weiter[1]
    bestellt.append((funktion, variante))
    return _auftrag(self, funktion, w, ebenen, schritt, *weiter, gemerkt=gemerkt)


rb.adaptiv_kern = gezaehlt
rb._Verteilt.auftrag = mitgeschrieben


class Fall:
    def __init__(self, teil, rohteil, oben, hoehen):
        self.rohteil, self.oben = rohteil, oben
        self.ebenen = [e for z in hoehen for e in hf.ebenen_oben(teil) if abs(e.z - z) < 1e-6]
        self.netz = hf.netze_je_hoehe(teil, self.ebenen)
        konturen = ra.konturen_des_teils(teil)
        self.konturen = konturen + ra.taschen_unter_oeffnungen(teil, self.ebenen, konturen)

    def werte(self, **anders):
        werte = {"ap": schruppen.ap, "ae": schruppen.ae, "aufmass": 0.3}
        werte.update(anders)
        ap, ae, aufmass = werte.pop("ap"), werte.pop("ae"), werte.pop("aufmass")
        return rb.Raeumwerte(
            ff.scheibe(R), ap, ae, aufmass, self.oben, self.oben + 5.0, self.rohteil,
            schneidenlaenge=werkzeug.schneidenlaenge, eintauchwinkel=werkzeug.eintauchwinkel,
            vorschub=VF, eintauchen=VF * 0.3, **werte,
        )  # fmt: skip

    def verteilt(self, w):
        return rb.planen(self.netz, w, self.ebenen, self.konturen)

    def hier(self, w):
        rb._Verteilt.anlegen = classmethod(lambda cls, *a: None)
        try:
            return rb.planen(self.netz, w, self.ebenen, self.konturen)
        finally:
            rb._Verteilt.anlegen = _anlegen


def gleich(fall, w, name, kern_hier=0):
    """Verteilt, dann hier mit dem Merker: dieselbe Bahn, der Kern hier `kern_hier` Mal."""
    kern[0] = 0
    del bestellt[:]
    verteilt = fall.verteilt(w)
    beim_verteilen = kern[0]
    reihe = list(bestellt)
    hier = fall.hier(w)
    pruefe(
        kennung(verteilt) == kennung(hier),
        f"{name}: verteilt {kennung(verteilt)} ≠ hier {kennung(hier)} ({hier.variante})",
    )
    pruefe(
        beim_verteilen == kern_hier and kern[0] == kern_hier,
        f"{name}: Kern hier {beim_verteilen} Mal verteilt, {kern[0]} Mal gesamt",
    )
    return verteilt, reihe


# Platte 120 × 120 mit Zapfen und Tasche: alle vier Varianten, „adaptiv“ geht als Erstes hinaus.
platte = Part.makeBox(120, 120, 30, V(-60, -60, -30))
platte = platte.fuse(Part.makeCylinder(8, 20, V(25, 25, 0)))
platte = platte.cut(Part.makeCylinder(15, 20, V(-25, -25, -20))).removeSplitter()
fall = Fall(platte, (-60.0, 60.0, -60.0, 60.0), 20.0, (0.0,))
rb._ADAPTIV.clear()
bahn, reihe = gleich(fall, fall.werte(), "Platte")
pruefe(len(reihe) > 1 and reihe[0] == ("variante_rechnen", "adaptiv"), f"bestellt: {reihe}")
pruefe(len(rb._ADAPTIV) > 0, "der Merker hier ist nach dem verteilten Rechnen leer")
print(ascii(f"Platte: {bahn.variante}, {len(bahn.punkte)} Saetze, bestellt {reihe}"))

# Geänderte Werte, dann zurück auf die alten.
gleich(fall, fall.werte(ae=schruppen.ae * 0.7), "Platte ae 0,7")
gleich(fall, fall.werte(variante="adaptiv"), "Platte nur adaptiv")
gleich(fall, fall.werte(), "Platte zurück")

# Merker hier → Arbeiter: hier gerechnet (der Kern hier), verteilt danach dieselbe Bahn ohne ihn.
w = fall.werte(aufmass=0.5)
kern[0] = 0
hier = fall.hier(w)
pruefe(kern[0] > 0, "Aufmaß 0,5: hier ohne Kern gerechnet")
kern[0] = 0
verteilt = fall.verteilt(w)
pruefe(
    kennung(verteilt) == kennung(hier) and kern[0] == 0,
    f"Aufmaß 0,5: hier {kennung(hier)}, verteilt {kennung(verteilt)}, Kern {kern[0]} Mal",
)

# Merker hier geleert – die Arbeiter behalten ihren: Was sie davon nehmen, kommt zurück.
rb._ADAPTIV.clear()
gleich(fall, fall.werte(), "Platte nach geleertem Merker")

# Enge Nut (Tasche): „inseln“ und „adaptiv“; feiner() rechnet die Ringe auf einem Nebenrechner nach.
breite = 2.0 * R + 0.6 * schruppen.ae
nut = Part.makeBox(120, 60, 20, V(-60, -30, -20))
nut = nut.cut(Part.makeBox(70, breite, 12, V(-35, -breite / 2, -12))).removeSplitter()
fall_nut = Fall(nut, (-60.0, 60.0, -30.0, 30.0), 0.0, (-12.0,))
bahn, reihe = gleich(fall_nut, fall_nut.werte(), "Nut")
pruefe(("feiner_rechnen", "inseln") in reihe, f"Nut: feiner nicht verteilt, bestellt {reihe}")
gleich(fall_nut, fall_nut.werte(variante="inseln"), "Nut nur inseln")

# Vorgewärmt wie im Assistenten: Ein Arbeiter lädt für variante_rechnen und feiner_rechnen kein
# Modul des Addons mehr nach.
gewaermt = []
_vorwaermen = nr.Nebenrechner.vorwaermen
nr.Nebenrechner.vorwaermen = lambda self, module: gewaermt.extend(module)
try:
    ba._vorwaermen()
finally:
    nr.Nebenrechner.vorwaermen = _vorwaermen
pruefe(set(rb.NEBENRECHNER_MODULE) <= set(gewaermt), f"der Assistent wärmt {gewaermt}")
namen = sorted(
    n[:-3] for n in os.listdir(os.path.join(ADDON, "camaddon")) if n.endswith(".py") and n[0] != "_"
)
einer = nr.Nebenrechner(anzahl=1)
try:
    einer.vorwaermen(gewaermt)

    def geladen():
        antworten = einer.warten(
            [einer.auftrag("nebenrechner", "_probe_geladen", n) for n in namen]
        )
        return {n for n, ja in zip(namen, antworten, strict=True) if ja}

    vorher = geladen()
    w = fall_nut.werte()
    folge = rb._folge(fall_nut.ebenen, fall_nut.konturen)
    huellen = {}
    rb._huellen_vorab(fall_nut.netz, w, folge, R, rb.SCHRITT, huellen)
    verpackt = rb._konturen_verpackt(fall_nut.konturen, nr)
    st = rb.variante_rechnen(
        fall_nut.netz, w, fall_nut.ebenen, verpackt, rb.SCHRITT, None, "inseln", True, huellen
    )[0][1]
    orte = []
    rb.last(st, w, None, orte)
    pruefe(orte, "Nut: keine Stelle für feiner()")
    gemeinsam = (fall_nut.netz, w, fall_nut.ebenen, verpackt, rb.SCHRITT, None)
    einer.warten(
        [
            einer.auftrag("raeumen_bahn", "variante_rechnen", *gemeinsam, v, True, huellen)
            for v in ("adaptiv", "inseln")
        ]
        + [
            einer.auftrag(
                "raeumen_bahn", "feiner_rechnen", *gemeinsam, huellen, "inseln", True, orte, st.eng
            )
        ]
    )
    nachgeladen = sorted(geladen() - vorher)
    pruefe(not nachgeladen, f"nachgeladen (in NEBENRECHNER_MODULE aufnehmen): {nachgeladen}")
finally:
    einer.beenden()

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
