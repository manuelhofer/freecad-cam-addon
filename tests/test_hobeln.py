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

# --- Die Hobelbahn (Schritt 2) ------------------------------------------------------------------
# Klinge 2,6 breit, 2 lang hinter der Schneide, Versatz 30° (bei Spindel 30° zeigt die Schneide nach
# +X), 0,05 je Umlauf, nach dem Fräsen stehen 0,2 über dem Grund, eine Leerfahrt.
if nuten:
    n = nuten[0]
    hw = hb.Hobelwerte(breite=2.6, laenge=2.0, versatz=30.0, zustellung=0.05, rest=0.2,
                       sicher=15.0, vorschub=3000.0, leerumlaeufe=1)  # fmt: skip
    hbahn = hb.planen(n, hw)
    schnitt = [(p, w) for p, w in zip(hbahn.punkte, hbahn.winkel, strict=True) if not p.eilgang]
    print(ascii(f"Hobelbahn: {hbahn.spuren} Spuren, {hbahn.umlaeufe} Umläufe je Spur, "
                f"{len(hbahn.punkte)} Sätze, {hbahn.laenge:.0f} mm, {hbahn.zeit:.2f} min"))  # fmt: skip
    pruefe(
        hbahn.spuren == 2 and hbahn.umlaeufe == 4 + 1 + 1,
        f"Spuren/Umläufe: {hbahn.spuren}/{hbahn.umlaeufe}",
    )
    pruefe(all(w is not None and p.notiz and p.notiz.startswith(hb.SPINDEL) for p, w in schnitt),
           "ein Satz ohne Spindelwinkel")  # fmt: skip
    pruefe(min(p.z for p, _w in schnitt) >= n.z_boden - 1e-9, "unter dem Grund")
    pruefe(abs(min(p.z for p, _w in schnitt) - n.z_boden) < 1e-9, "nicht bis auf den Grund")
    pruefe(max(p.z for p, _w in schnitt) <= n.z_boden + 0.2 + 1e-9, "über dem Rest")
    # Der Winkel folgt der Fahrt: Richtung von Satz zu Satz + Versatz (± ein Schritt auf dem Bogen).
    abweichung = 0.0
    for a, b, wb in zip(hbahn.punkte, hbahn.punkte[1:], hbahn.winkel[1:], strict=False):
        d = math.hypot(b.x - a.x, b.y - a.y)
        if a.eilgang or b.eilgang or d < 0.1:
            continue  # über den Eilgang zwischen zwei Spuren hinweg zählt nicht
        soll = math.degrees(math.atan2(b.y - a.y, b.x - a.x)) + 30.0
        abweichung = max(abweichung, abs((wb - soll + 180.0) % 360.0 - 180.0))
    print(f"Winkel: größte Abweichung zur Fahrtrichtung {abweichung:.2f} Grad")
    pruefe(abweichung < 3.0, f"Spindelwinkel folgt der Fahrt nicht: {abweichung:.2f} Grad")
    sprung = max(abs(b[1] - a[1]) for a, b in zip(schnitt, schnitt[1:], strict=False))
    pruefe(sprung < 10.0, f"Spindelwinkel springt um {sprung:.1f} Grad")
    # Nur vorwärts: gegen den Uhrzeigersinn um die Mitte (die Klinge schneidet nur nach vorn).
    drehung = sum(
        math.atan2(a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y)
        for (a, _w), (b, _v) in zip(schnitt, schnitt[1:], strict=False)
        if math.hypot(b.x - a.x, b.y - a.y) < 1.0
    )
    pruefe(drehung > 0, "die Bahn läuft rückwärts")
    # Unabhängig: die Klinge als Rechteck (Schneide vorn auf dem Punkt, Körper `laenge` dahinter,
    # quer 2,6) muss in jeder Stellung ganz im Grund der Nut liegen.
    grund_flaeche = next(
        f for f in teil.Faces if abs(f.BoundBox.ZMin - 8.0) < 1e-6 and len(f.Wires) == 2
    )
    draussen = 0.0
    for p, w in schnitt[:: max(1, len(schnitt) // 400)]:
        a = math.radians(w - 30.0)
        c, s = math.cos(a), math.sin(a)
        ecken = [(0.0, -1.3), (0.0, 1.3), (-2.0, 1.3), (-2.0, -1.3)]
        pts = [V(p.x + c * u - s * v, p.y + s * u + c * v, 8.0) for u, v in ecken]
        klinge = Part.Face(Part.makePolygon(pts + pts[:1]))
        draussen = max(draussen, klinge.Area - klinge.common(grund_flaeche).Area)
    print(f"Klinge außerhalb des Grunds: höchstens {draussen:.5f} mm2")
    pruefe(draussen < 1e-3, f"die Klinge ragt {draussen:.4f} mm2 aus der Nut")
    # Eine Klinge, die die Nut füllt: eine Spur. Werte 0: Satz.
    voll = hb.planen(n, hw.__class__(**{**hw.__dict__, "breite": 2.9, "laenge": 1.0}))
    pruefe(voll.spuren == 1, f"Spuren bei voller Klinge: {voll.spuren}")
    try:
        hb.planen(n, hw.__class__(**{**hw.__dict__, "zustellung": 0.0}))
        pruefe(False, "Zustellung 0 geht")
    except ValueError:
        pass

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


# --- Die Operation im Job und das Programm (Schritte 4 und 5) -----------------------------------
# Die Spindel steht (kein M3); vor jedem Satz der Winkel – Siemens SPOS=DC im Satz, Heidenhain
# Zyklus 13 mit M19, LinuxCNC M19 R; GRBL kann es nicht und sagt das.
import Path.Main.Job as PathJob  # noqa: E402

from camaddon import hobeln as hop  # noqa: E402
from camaddon import postprozessor as pp  # noqa: E402
from camaddon import uebergabe_werkzeuge as ue  # noqa: E402
from camaddon import werkzeuge as wz  # noqa: E402

profil_ordner = os.environ.get("FREECAD_USER_HOME", "")
if not profil_ordner or not FreeCAD.getUserAppDataDir().startswith(profil_ordner):
    raise AssertionError("Kein Testprofil – die Werkzeugverwaltung würde überschrieben.")
stoss = wz.Werkzeug(nummer=9, art=wz.STOSSWERKZEUG, name="Hobel 2,6", schneidenbreite=2.6,
                    klingenlaenge=2.0, spindelwinkel=30.0, stechtiefe=4.0)  # fmt: skip
# Mit Richtwerten (Einsatz „Hobeln“): Die Übergabe an FreeCAD darf daran nicht scheitern (bis 0.376.0
# KeyError – dann scheiterte das Anlegen für alle Strategien).
from camaddon import werkzeugkiste as wk  # noqa: E402

wk.richtwerte_eintragen(stoss)
stoss.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.HOBELN, ap=0.05, vc=6.0)]
bibliothek = wz.Bibliothek([stoss])
bibliothek.speichern()
ue.uebergeben(bibliothek)
doc = FreeCAD.newDocument("Hobeln")
doc.UndoMode = 1
objekt = doc.addObject("Part::Feature", "Deckel")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
doc.recompute()
tc = hop.controller(doc, job, stoss)
op = hop.lege_an(job, tc)
doc.recompute()
pruefe(hop.ist_hobeln(op) and op.Nuten == 1, f"Operation: {op.Label}, {op.Nuten} Nuten")
pruefe(str(tc.SpindleDir) == "None" and float(tc.SpindleSpeed) == 0.0, "die Spindel dreht")
pruefe(tc.HorizFeed.getValueAs("mm/min").Value == 6000.0, f"Hub {tc.HorizFeed}")
pruefe("Hobeln" in tc.Label, f"Controller {tc.Label}")
# Der Einsatz „Hobeln“: Richtwerte, Drehzahl 0, Vorschub = Hub.
from camaddon import schnittdaten as sd  # noqa: E402
from camaddon import werkzeugkiste as wk  # noqa: E402

mit_werten = wz.Werkzeug.aus_dict(stoss.als_dict())
wk.richtwerte_eintragen(mit_werten)
hobeln_p1 = [e for e in mit_werten.einsaetze("P1") if e.art == wz.HOBELN]
pruefe(len(hobeln_p1) == 1 and hobeln_p1[0].ap == 0.05, f"Richtwerte: {mit_werten.schnittwerte}")
if hobeln_p1:
    pruefe(sd.rechne(mit_werten, hobeln_p1[0])[:2] == (0.0, 6000.0), "n, vf beim Hobeln")
pruefe(abs(float(op.FinalDepth) - 8.0) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
notizen = [b.Name for b in op.Path.Commands if b.Name.startswith("(SPINDEL ")]
pruefe(len(notizen) > 100, f"nur {len(notizen)} Spindelwinkel")
programme = {}
for kennung in ("siemens", "heidenhain", "linuxcnc", "grbl", "fanuc", "mach", "mazak"):
    programme[kennung] = pp.programm(pp.abschnitte(job), pp.steuerung(kennung), None, "Hobeln")
    zeilen = programme[kennung].zeilen
    pruefe(not any("SPINDEL" in z for z in zeilen), f"{kennung}: Notiz im Programm")
    pruefe(not any({"M3", "M03", "M4", "M04"} & set(z.split()) for z in zeilen), f"{kennung}: M3")
si = programme["siemens"].zeilen
spos = [z for z in si if "SPOS=DC(" in z]
pruefe(len(spos) > 100 and all(z.split()[0] in ("G0", "G1") for z in spos), f"Siemens: {spos[:3]}")
hh = programme["heidenhain"].zeilen
pruefe(sum("CYCL DEF 13.1 WINKEL " in z for z in hh) > 100, "Heidenhain: kein Zyklus 13")
pruefe(sum("M19 R" in z for z in programme["linuxcnc"].zeilen) > 100, "LinuxCNC: kein M19 R")
hinweise = " ".join(programme["grbl"].hinweise)
pruefe("hobeln geht damit nicht" in hinweise, f"GRBL ohne Hinweis: {hinweise[:200]}")
# Fanuc: M19 S in ganzen Grad davor; Mach4: M19 S; Mazak ohne belegten Satz – der Hinweis.
fanuc = [z for z in programme["fanuc"].zeilen if z.startswith("M19 S")]
pruefe(len(fanuc) > 100 and all(z.split("S")[1].isdigit() for z in fanuc), f"Fanuc: {fanuc[:3]}")
pruefe(sum(z.startswith("M19 S") for z in programme["mach"].zeilen) > 100, "Mach: kein M19 S")
mazak = " ".join(programme["mazak"].hinweise)
pruefe("Befehle" in mazak, f"Mazak ohne Hinweis: {mazak[:200]}")
print(ascii(f"Programm: Siemens {len(si)} Zeilen, {spos[0] if spos else ''}"))
# Die Spindel dreht über der Nut in Richtung, nicht erst beim Eintauchen in die gefräste Nut.
erster = next(i for i, z in enumerate(si) if "SPOS=DC(" in z)
unten = next(
    i
    for i, z in enumerate(si)
    if "Z" in z and z.startswith("G") and float(z.split("Z")[1].split()[0]) < 10.5
)
pruefe(si[erster].startswith("G0") and erster < unten, f"erster Winkel: {si[erster]}, {si[unten]}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
