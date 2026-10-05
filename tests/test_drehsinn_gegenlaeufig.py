# Prüft den Haken „gegenläufig“ an einer Rundachse (Manuel, 2026-10-05, am 4-Achs-Testteil: „die
# Gerade wird richtig gefahren … aber nachdem er die Gerade gefahren hat, dreht er an der Maschine
# definitiv in die falsche Richtung … und macht gegenüber von der Geraden ein Loch“). Die
# Beispiel-Drehmaschine, eine Welle Ø 30 mit einer Abflachung, „Rundum schruppen“ mit T1 radial:
# Mit dem Haken an C1 dreht C andersherum – der Drehsinn der Achse wechselt, +90° drehen das Futter
# andersherum. Rechnet die Operation noch mit dem alten Drehsinn, sagen es das Prüffenster und
# „Programm schreiben“ (auch als Kommentar im Programm), und
# abgefahren läge die Bahn gespiegelt am Teil. Mit dem neuen Drehsinn übernommen: kein Hinweis,
# im Programm jedes C mit dem anderen Vorzeichen, und abgefahren steht die Spitze an jeder Station
# dort am Teil, wo sie ohne Haken stand.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import abfahren as ab
from camaddon import beispielmaschine as bm
from camaddon import halter as hl
from camaddon import maschine as m
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import sprache
from camaddon import verfahren as vf
from camaddon import vierachs_achsen as va
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
X, Y = V(1, 0, 0), V(0, 1, 0)
sprache.setze_sprache("de")

asm, ma = bm.drehmaschine()
achse = va.von_maschine(asm, ma)[0]
verfahren = vf.Verfahren(asm)
c1 = next(a for a in verfahren.kette.achsen if vf.namen(ma, a) == "C1")
# An C1 hängen zwei Betriebsarten: Spindel (Drehen) und Positionieren (C-Achse) – der Haken
# gehört zum Positionieren.
betriebsart = next(
    b for b in m.betriebsarten(ma) if b.Gelenk == c1.gelenk and b.Art == m.ART_POSITIONIEREN
)
pruefe(not betriebsart.Gegenlaeufig, "Haken von Anfang an gesetzt")
aufnahme = next(a for a in m.aufnahmen(ma) if a.Art == m.AUFNAHME_WERKSTUECK)


def x_nach_plus_90():
    """Wohin X des Futters zeigt, wenn C1 auf +90° fährt."""
    verfahren = vf.Verfahren(asm)
    c1 = next(a for a in verfahren.kette.achsen if vf.namen(ma, a) == "C1")
    verfahren.setze(c1, verfahren.stellung(c1) + 90, grenzen=False)
    x = m.globale_platzierung(aufnahme.Lcs).Rotation.multVec(X)
    verfahren.grundstellung()
    return x


x_ohne = x_nach_plus_90()

# Die Welle Ø 30 × 20 längs X mit einer Abflachung auf 10 über der Achse.
doc = FreeCAD.newDocument("Abflachung")
welle = doc.addObject("Part::Feature", "Welle")
form = Part.makeCylinder(15, 20, V(), X).cut(Part.makeBox(30, 40, 10, V(-5, -20, 10)))
welle.Shape = form.removeSplitter()
doc.recompute()
stirn = next(
    f for f in welle.Shape.Faces if vr.ist_eben(f) and (vr.aussennormale(f) - X).Length < 1e-9
)
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=40)
job = vr.richte_ein(doc, welle, lage, vr.Stange(40.0, frei_hinten=40.0), achse)
tc = job.Tools.Group[0]
tc.Tool.Diameter = 10
tc.HorizFeed = "1000 mm/min"
tc.ToolNumber = 1
bib = wz.Bibliothek()
halter = bib.neuer_halter("vdi30_radial")
t1 = bib.neues_werkzeug()
t1.nummer, t1.durchmesser, t1.laenge_spindelnase, t1.halter = 1, 10.0, 125.0, halter.kennung
op = vo.lege_an(
    job, tc, achse, zustellung=3.0, steigung=5.0, aufmass=0.3, halter=hl.seitlich(halter)
)
doc.recompute()
nullpunkt = rw.vorschlag_nullpunkt(job)


def c_werte():
    return [c.Parameters["C"] for c in op.Path.Commands if "C" in c.Parameters]


def abgefahren():
    """(Hinweise des Prüffensters und von „Programm schreiben“, die Spitze am Teil je Station)."""
    pruefung = rw.Pruefung(asm, ma)
    hinweise = pruefung.pruefe_job(job, nullpunkt, bib).hinweise
    programm = pp.programm(
        pp.abschnitte(job), pp.steuerung("siemens"), pp.maschineninfo_dokument(asm.Document), "W"
    )
    hinweise = " | ".join(hinweise + programm.hinweise + programm.zeilen)
    return hinweise, ab.abfahrt(pruefung, job, nullpunkt, bib).am_werkstueck()


c_ohne = c_werte()
hinweise, am_teil_ohne = abgefahren()
pruefe("andersherum" not in hinweise, f"Hinweis ohne Haken: {hinweise}")
pruefe(len(c_ohne) > 100 and max(c_ohne) - min(c_ohne) > 300, f"C: {len(c_ohne)} Werte")

# Der Haken: C dreht andersherum.
betriebsart.Gegenlaeufig = True
gegen = va.von_maschine(asm, ma)[0]
pruefe(gegen.drehsinn == -achse.drehsinn, f"Drehsinn {achse.drehsinn} → {gegen.drehsinn}")
x_mit = x_nach_plus_90()
pruefe((x_mit + x_ohne).Length < 1e-6, f"+90° ohne Haken {x_ohne}, mit {x_mit}")

# Die Operation rechnet noch mit dem alten Drehsinn: Hinweis, die Bahn läge gespiegelt am Teil.
hinweise, am_teil_alt = abgefahren()
pruefe(
    "„" + op.Label + "“ dreht C andersherum als die Rundachse C" in hinweise,
    f"kein Hinweis zum Drehsinn im Prüffenster: {hinweise[:300]}",
)
pruefe(
    hinweise.count("„" + op.Label + "“ rechnet C andersherum, als C an dieser Maschine") == 2,
    f"kein Hinweis zum Drehsinn im Programm (Fenster und Kommentar): {hinweise[:300]}",
)
abweichung = max(math.dist(p, q) for p, q in zip(am_teil_alt, am_teil_ohne, strict=True))
pruefe(abweichung > 5.0, f"mit altem Drehsinn nur {abweichung:.3f} mm daneben")

# Übernommen mit dem neuen Drehsinn: kein Hinweis, C umgekehrt, die Spitze am Teil wie vorher.
vo.setze_achse(op, gegen)
doc.recompute()
c_mit = c_werte()
pruefe(
    len(c_mit) == len(c_ohne)
    and all(abs(a + b) < 1e-9 for a, b in zip(c_mit, c_ohne, strict=True)),
    f"C nicht umgekehrt: {c_ohne[:5]} → {c_mit[:5]}",
)
hinweise, am_teil_mit = abgefahren()
pruefe("andersherum" not in hinweise, f"Hinweis nach dem Übernehmen: {hinweise}")
abweichung = max(math.dist(p, q) for p, q in zip(am_teil_mit, am_teil_ohne, strict=True))
pruefe(abweichung < 1e-6, f"am Teil {abweichung:.6f} mm anders als ohne Haken")
print(ascii(f"{len(c_ohne)} C-Werte, {len(am_teil_ohne)} Stationen"))

FreeCAD.closeDocument(doc.Name)
FreeCAD.closeDocument(asm.Document.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
