# Prüft „Dichtnut hobeln“, Schritt 1 (hobeln_bahn; Spezifikation Strategien 13.10): die Nut und ihre
# Mittellinie. Manuel, 2026-11-14: „form muss egal sein wenn ich in einem teil eine nut zeichne soll
# diese nachgefahren werden ... (natürlich wenn man spitze ecken hat geht das nicht man braucht schon
# rundungen sonst klappt das nicht)“.
# Deckel 100 × 80 × 10, darin je eine umlaufende Nut 3 breit, 2 tief: ein Rechteck 70 × 50 mit R 10
# (Mittellinie), ein Kreis R 28, eine Freiform (Ellipse) – und, was nicht gehen darf: ein Rechteck
# mit spitzen Ecken, eine Nut mit wechselnder Breite. Ein Absatz und eine Tasche sind keine Nut.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part

from camaddon import hobeln_bahn as hb
from camaddon import sprache

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector
B, T = 3.0, 2.0


def deckel(nutflaeche, tiefe=T):
    """Der Deckel (Oberseite z 10) mit der Nut `nutflaeche` (eine Fläche in z = 0) eingelassen."""
    nut = nutflaeche.extrude(V(0, 0, tiefe))
    nut.translate(V(0, 0, 10.0 - tiefe))
    return Part.makeBox(100, 80, 10, V(-50, -40, 0)).cut(nut).removeSplitter()


def ring_um(draht, breite=B):
    """Die Fläche zwischen dem Versatz von `draht` um ±breite/2 – eine Nut längs des Drahts."""
    aussen = Part.Face(draht.makeOffset2D(breite / 2.0, 0, False, False, False))
    innen = Part.Face(draht.makeOffset2D(-breite / 2.0, 0, False, False, False))
    return aussen.cut(innen)


def rechteck(a, b, r):
    """Ein Rechteck a × b um den Ursprung mit Eckradius r (r = 0: spitze Ecken)."""
    if r <= 0:
        ecken = [V(-a / 2, -b / 2, 0), V(a / 2, -b / 2, 0), V(a / 2, b / 2, 0), V(-a / 2, b / 2, 0)]
        return Part.makePolygon(ecken + ecken[:1])
    return Part.Wire(
        Part.makePlane(a - 2 * r, b - 2 * r, V(-a / 2 + r, -b / 2 + r, 0)).Wires[0]
    ).makeOffset2D(r, 0, False, False, False)


# --- Rechteck mit Radien ------------------------------------------------------------------------
teil = deckel(ring_um(rechteck(70, 50, 10)))
nuten = hb.hobelnuten(teil)
pruefe(
    len(nuten) == 1, f"Rechteck mit Radien: {[(n.name, n.grund) for n in hb.alle_hobelnuten(teil)]}"
)
if nuten:
    n = nuten[0]
    soll = 2 * (50 + 30) + 2 * math.pi * 10
    print(ascii(f"Rechteck R 10: {n.text()}; {len(n.segmente)} Stücke, {len(n.flaechen)} Flächen"))
    pruefe(abs(n.breite - B) < 0.01 and abs(n.tiefe - T) < 1e-6, f"Maße: {n.breite} × {n.tiefe}")
    pruefe(abs(n.laenge - soll) < 0.05, f"Länge {n.laenge:.3f} statt {soll:.3f}")
    pruefe(abs(n.r_min - 10.0) < 0.01, f"kleinster Radius {n.r_min}")
    pruefe(n.geschlossen and abs(n.z_boden - 8.0) < 1e-6 and abs(n.z_oben - 10.0) < 1e-6, "Höhen")
    boegen = [s for s in n.segmente if s.bogen is not None]
    pruefe(len(boegen) == 4 and all(not s.uhr for s in boegen), f"Bögen: {len(boegen)}, Umlaufsinn")
    # Ein Zug ohne Lücke und ohne Knick, gegen den Uhrzeigersinn.
    for a, b in zip(n.segmente, n.segmente[1:] + n.segmente[:1], strict=True):
        pruefe(math.dist(a.nach, b.von) < 1e-6, f"Lücke bei {a.nach}")
        pruefe(
            hb._knick(a, b) < 1e-6, f"Knick bei {a.nach}: {math.degrees(hb._knick(a, b)):.3f} Grad"
        )
    # Der Grund und seine Wände (2 × (4 Geraden + 4 Rundungen)) gehören dazu.
    pruefe(len(n.flaechen) == 17, f"Flächen: {len(n.flaechen)}")
    pruefe(hb.hobelnuten(teil, [n.flaechen[3]]) == nuten, "eine Wand bringt die Nut nicht mit")
    pruefe(not hb.hobelnuten(teil, ["Face1"]), "eine fremde Fläche bringt die Nut mit")
    # Die Klinge: 2,6 breit, 2 hinter der Schneide geht (R 10); 3 lang nicht; zu breit nicht.
    pruefe(not hb.klinge_pruefen(n, 2.6, 2.0), f"Klinge 2,6 × 2: {hb.klinge_pruefen(n, 2.6, 2.0)}")
    pruefe(
        "Radius" in hb.klinge_pruefen(n, 2.6, 3.0),
        f"Klinge 2,6 × 3: {hb.klinge_pruefen(n, 2.6, 3.0)!r}",
    )
    pruefe(
        "breiter" in hb.klinge_pruefen(n, 3.0, 1.0),
        f"Klinge 3,0: {hb.klinge_pruefen(n, 3.0, 1.0)!r}",
    )
    pruefe("Breite" in hb.klinge_pruefen(n, 0.0, 1.0), "Klinge ohne Breite")
    # Die Formel: bei genau dem nötigen Radius liegt die hintere äußere Ecke SPIEL vor der Wand.
    r_n = hb.kleinster_radius_fuer(B, 2.6, 2.0)
    ecke = math.hypot(r_n + 1.3, 2.0)
    pruefe(abs(ecke - (r_n + 1.5 - hb.SPIEL)) < 1e-9 and 8.0 < r_n < 10.0, f"nötiger Radius {r_n}")

# --- Kreis ---------------------------------------------------------------------------------------
kreis = deckel(ring_um(Part.Wire([Part.makeCircle(28.0)])))
nk = hb.hobelnuten(kreis)
pruefe(len(nk) == 1, f"Kreis: {[(n.name, n.grund) for n in hb.alle_hobelnuten(kreis)]}")
if nk:
    print(ascii(f"Kreis R 28: {nk[0].text()}"))
    pruefe(abs(nk[0].r_min - 28.0) < 0.01 and abs(nk[0].laenge - 2 * math.pi * 28) < 0.05, "Kreis")
    pruefe(all(s.bogen is not None and not s.uhr for s in nk[0].segmente), "Kreis: Umlaufsinn")

# --- Freiform: eine Ellipse 60 × 40 --------------------------------------------------------------
ellipse = Part.Wire([Part.Ellipse(V(0, 0, 0), 30.0, 20.0).toShape()])
ne = hb.hobelnuten(deckel(ring_um(ellipse)))
pruefe(len(ne) == 1, "Ellipse nicht erkannt")
if ne:
    print(ascii(f"Ellipse: {ne[0].text()}"))
    # Die Scheitel der Ellipse haben den Krümmungsradius b² ÷ a = 13,3.
    pruefe(abs(ne[0].breite - B) < 0.02 and 11.0 < ne[0].r_min < 15.0, f"Ellipse: {ne[0].r_min}")

# --- Was nicht geht -------------------------------------------------------------------------------
spitz = deckel(ring_um(rechteck(70, 50, 0)))
gruende = [n.grund for n in hb.alle_hobelnuten(spitz)]
print(ascii(f"spitze Ecken: {gruende}"))
pruefe(not hb.hobelnuten(spitz) and len(gruende) == 1 and gruende[0], f"spitze Ecken: {gruende}")
ungleich = Part.Face(rechteck(73, 53, 11.5)).cut(Part.Face(Part.Wire([Part.makeCircle(20.0)])))
gruende = [n.grund for n in hb.alle_hobelnuten(deckel(ungleich))]
pruefe(len(gruende) == 1 and "gleich breit" in gruende[0], f"wechselnde Breite: {gruende}")
# Ein Zapfen auf einem Absatz (der Grund hat zwei Ränder, aber außen keine Wand) und eine Tasche.
absatz = Part.makeBox(100, 80, 8, V(-50, -40, 0)).fuse(Part.makeCylinder(20, 2, V(0, 0, 8)))
pruefe(not hb.alle_hobelnuten(absatz.removeSplitter()), "ein Absatz gilt als Nut")
tasche = Part.makeBox(100, 80, 10, V(-50, -40, 0)).cut(Part.makeBox(40, 30, 3, V(-20, -15, 7)))
pruefe(not hb.alle_hobelnuten(tasche), "eine Tasche gilt als Nut")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
