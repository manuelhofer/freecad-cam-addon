# Prüft den Anlauf der 3D-Schnitte (schlicht_anlauf, W-035 „kein Zickzack“): Reicht die erste
# Schnittstrecke für die Rampe nicht, kehrt _rampe um (das Zickzack) – _helix fährt stattdessen
# auf einem Kreis durch den Anfang hinab: tangential in die erste Strecke, gegen den
# Uhrzeigersinn, nie unter der Hüllfläche plus dem Aufmaß des Zugs, je Umlauf höchstens so tief,
# wie der Winkel erlaubt, zum Schluss eine Runde auf Tiefe und am Anfang zu Ende. Ohne
# Hüllfläche (oder ohne Strecke) None. Eine schräge Hüllfläche trägt die Helix mit.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import bahn as bn
from camaddon import fraeserform as ff
from camaddon import schlicht_anlauf as sa

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


class _Huelle:
    """Eine Hüllfläche zum Prüfen: eben bei z0, oder geneigt (z0 + steigung · x)."""

    def __init__(self, z0=0.0, steigung=0.0, scheitern=False):
        self.z0, self.steigung, self.scheitern = z0, steigung, scheitern

    def fenster(self, x, y, halb):
        if self.scheitern:
            raise RuntimeError("kein Netz")
        return lambda px, py: self.z0 + self.steigung * px


R = 3.0
form = ff.kugel(R)
winkel = 3.0
tan = math.tan(math.radians(winkel))
aufmass = 0.2
# Ein Zug von 2 mm in +x, 0,2 über der Hüllfläche (das Aufmaß); 1 mm Material darüber.
zug = [bn.Punkt(False, 0.0, 0.0, aufmass), bn.Punkt(False, 2.0, 0.0, aufmass)]
hoch = 1.0
pruefe(not sa._rampe_reicht(zug, hoch, winkel), "2 mm reichen nicht für 1 mm bei 3°")
pruefe(sa._rampe_reicht(zug, 0.1, winkel), "2 mm reichen für 0,1 mm bei 3°")
helix = sa._helix(zug, hoch, winkel, form, _Huelle())
pruefe(helix is not None and len(helix) > 10, f"keine Helix: {helix}")
if helix:
    rho = sa.HELIX_ANTEIL * R
    mitte = (0.0, rho)  # links der Fahrt in +x
    letzter = helix[-1]
    pruefe(
        abs(letzter.x) < 1e-9 and abs(letzter.y) < 1e-9 and abs(letzter.z - aufmass) < 1e-9,
        f"endet nicht am Anfang: {letzter}",
    )
    pruefe(
        all(abs(math.hypot(p.x - mitte[0], p.y - mitte[1]) - rho) < 1e-6 for p in helix),
        "nicht auf dem Kreis durch den Anfang",
    )
    pruefe(all(p.z >= aufmass - 1e-9 for p in helix), "unter Hüllfläche plus Aufmaß")
    pruefe(abs(helix[0].z - (aufmass + hoch)) < 0.05, f"beginnt nicht oben: {helix[0].z}")
    # Gegen den Uhrzeigersinn, nie zurück; je Bogen höchstens tan(Winkel) · Weg tiefer.
    vorher = (0.0, 0.0, aufmass + hoch)
    winkel_vorher = math.atan2(vorher[1] - mitte[1], vorher[0] - mitte[0])
    umlauf = 0.0
    for p in helix:
        w = math.atan2(p.y - mitte[1], p.x - mitte[0])
        d = (w - winkel_vorher) % (2 * math.pi)
        pruefe(d < math.pi, "dreht zurück")
        umlauf += d
        weg = math.hypot(p.x - vorher[0], p.y - vorher[1])
        pruefe(vorher[2] - p.z <= tan * weg + 1e-9, f"zu steil bei {p}")
        vorher, winkel_vorher = (p.x, p.y, p.z), w
    umlaeufe = math.ceil(hoch / (2 * math.pi * rho * tan) - 1e-9)
    pruefe(
        abs(umlauf - 2 * math.pi * (umlaeufe + 1)) < 1e-6,
        f"{umlauf / (2 * math.pi):.2f} Umläufe statt {umlaeufe + 1}",
    )
    # Die letzte Runde auf Tiefe.
    rest = [p for p in helix if abs(p.z - aufmass) < 1e-9]
    pruefe(len(rest) >= len(helix) / (umlaeufe + 1) - 2, f"keine Runde auf Tiefe: {len(rest)}")
    # Am Ende tangential in die erste Strecke (+x).
    vor_ende = helix[-2]
    richtung = math.atan2(letzter.y - vor_ende.y, letzter.x - vor_ende.x)
    pruefe(abs(richtung) < math.radians(10.0), f"mündet nicht in +x: {math.degrees(richtung)}°")

# Eine geneigte Hüllfläche: Die Helix folgt ihr, nie darunter.
geneigt = _Huelle(z0=0.0, steigung=0.1)
zug_g = [bn.Punkt(False, 0.0, 0.0, aufmass), bn.Punkt(False, 1.0, 0.0, aufmass + 0.1)]
helix_g = sa._helix(zug_g, 0.5, winkel, form, geneigt)
pruefe(helix_g is not None, "geneigt: keine Helix")
if helix_g:
    pruefe(all(p.z >= 0.1 * p.x + aufmass - 1e-9 for p in helix_g), "geneigt: unter der Fläche")

# Ohne Hüllfläche oder ohne Strecke: None (dann das Zickzack wie bisher).
pruefe(sa._helix(zug, hoch, winkel, form, _Huelle(scheitern=True)) is None, "ohne Hüllfläche")
punkt = [bn.Punkt(False, 0.0, 0.0, 0.0), bn.Punkt(False, 0.0, 0.0, 0.0)]
pruefe(sa._helix(punkt, hoch, winkel, form, _Huelle()) is None, "ohne Strecke")

# Die echte Hüllfläche aus dem Teil des Jobs (_hueller): ein Quader 20 × 20 × 10, die Kugel R 3 –
# mitten darüber steht die Spitze auf 10, weit daneben trifft sie nichts; die Helix bleibt über 10.
import Part  # noqa: E402


class _Ding:
    def __init__(self, **werte):
        self.__dict__.update(werte)


quader = Part.makeBox(20, 20, 10)
job = _Ding(Model=_Ding(Group=[_Ding(Shape=quader, PathResource="")]))
hueller = sa._hueller(job, form)
bei = hueller.fenster(10.0, 10.0, 4.0)
pruefe(abs(bei(10.0, 10.0) - 10.0) < 0.05, f"Hüllfläche mitten: {bei(10.0, 10.0)}")
weit = hueller.fenster(40.0, 40.0, 1.0)
pruefe(not math.isfinite(weit(40.0, 40.0)), f"weit daneben: {weit(40.0, 40.0)}")
zug_q = [bn.Punkt(False, 10.0, 10.0, 10.0), bn.Punkt(False, 11.0, 10.0, 10.0)]
helix_q = sa._helix(zug_q, 0.8, winkel, form, hueller)
pruefe(helix_q is not None and all(p.z >= 10.0 - 0.05 for p in helix_q), "Quader: unter 10")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
