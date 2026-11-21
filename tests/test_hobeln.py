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
    # Die Klinge: 2,6 breit, 1,6 hinter der Schneide geht (R 10); 2 und 3 lang nicht (mit dem
    # Schwenk eines halben Satzschritts und WINKEL_FEHLER); zu breit nicht.
    pruefe(
        not hb.klinge_pruefen(n, 2.6, 1.6), f"Klinge 2,6 × 1,6: {hb.klinge_pruefen(n, 2.6, 1.6)}"
    )
    pruefe("Radius" in hb.klinge_pruefen(n, 2.6, 2.0), "Klinge 2,6 × 2 geht noch")
    pruefe(
        "Radius" in hb.klinge_pruefen(n, 2.6, 3.0),
        f"Klinge 2,6 × 3: {hb.klinge_pruefen(n, 2.6, 3.0)!r}",
    )
    pruefe(
        "breiter" in hb.klinge_pruefen(n, 3.0, 1.0),
        f"Klinge 3,0: {hb.klinge_pruefen(n, 3.0, 1.0)!r}",
    )
    pruefe("Breite" in hb.klinge_pruefen(n, 0.0, 1.0), "Klinge ohne Breite")
    # Die Formel: bei genau dem nötigen Radius ragt die Klinge (geschwenkt) bis SPIEL vor die Wand.
    r_n = hb.kleinster_radius_fuer(B, 2.6, 1.6)
    ueber = max(hb._ueberstand(r_n, 2.6, 1.6, hb.SCHRITT))
    pruefe(abs(ueber - (0.2 - hb.SPIEL)) < 1e-6 and 6.0 < r_n < 10.0, f"nötiger Radius {r_n}")
    # Ohne Schwenk und Winkelfehler wäre es die alte Formel: √((R + b/2)² + L²) ≤ R + B/2 − SPIEL.
    alt = (1.6**2 - 0.195**2) / (2 * 0.195) - 1.3
    pruefe(r_n > alt + 0.5, f"Schwenk nicht mitgerechnet: {r_n} statt mehr als {alt}")

# --- Die Hobelbahn (Schritt 2) ------------------------------------------------------------------
# Klinge 2,6 breit, 1,6 lang hinter der Schneide, Versatz 30° (bei Spindel 30° zeigt die Schneide
# nach +X), 0,05 je Umlauf, nach dem Fräsen stehen 0,2 über dem Grund, eine Leerfahrt.
L_KLINGE = 1.6
if nuten:
    n = nuten[0]
    hw = hb.Hobelwerte(breite=2.6, laenge=L_KLINGE, versatz=30.0, zustellung=0.05, rest=0.2,
                       sicher=15.0, vorschub=3000.0, leerumlaeufe=1)  # fmt: skip
    hbahn = hb.planen(n, hw)
    schnitt = [(p, w) for p, w in zip(hbahn.punkte, hbahn.winkel, strict=True) if not p.eilgang]
    # Die Umläufe selbst (ohne Einfahren und Wechsel der Spur): je Punkt Spur und Stelle.
    umlauf = [(p, w, sp, st) for p, w, sp, st in
              zip(hbahn.punkte, hbahn.winkel, hbahn.spur, hbahn.stelle, strict=True)
              if sp is not None]  # fmt: skip
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
    pruefe(max(p.z for p, *_r in umlauf) <= n.z_boden + 0.2 + 1e-9, "über dem Rest")
    pruefe(
        max(p.z for p, _w in schnitt) <= n.z_boden + 0.2 + hb.UEBER_MATERIAL + 1e-9,
        "im Vorschub höher als 0,3 über dem Material",
    )
    # Der Winkel folgt der Fahrt: Richtung von Satz zu Satz + Versatz (± ein Schritt auf dem Bogen).
    abweichung = 0.0
    for (a, _wa, sa, _x), (b, wb, sb, _y) in zip(umlauf, umlauf[1:], strict=False):
        d = math.hypot(b.x - a.x, b.y - a.y)
        if sa != sb or d < 0.1:
            continue  # zwischen zwei Spuren zählt nicht
        soll = math.degrees(math.atan2(b.y - a.y, b.x - a.x)) + 30.0
        abweichung = max(abweichung, abs((wb - soll + 180.0) % 360.0 - 180.0))
    print(f"Winkel: größte Abweichung zur Fahrtrichtung {abweichung:.2f} Grad")
    pruefe(abweichung < 3.0, f"Spindelwinkel folgt der Fahrt nicht: {abweichung:.2f} Grad")
    sprung = max(abs(b[1] - a[1]) for a, b in zip(schnitt, schnitt[1:], strict=False))
    pruefe(sprung < 10.0, f"Spindelwinkel springt um {sprung:.1f} Grad")
    # Nur vorwärts: in jedem Umlauf gegen den Uhrzeigersinn (die Klinge schneidet nur nach vorn).
    rueckwaerts = [
        (a.x, a.y)
        for (a, _w, sa, _i), (b, _v, sb, _j) in zip(umlauf, umlauf[1:], strict=False)
        if sa == sb and math.atan2(a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y) < -1e-9
    ]
    pruefe(not rueckwaerts, f"die Bahn läuft rückwärts bei {rueckwaerts[:3]}")
    # Manuel, 2026-11-14: „0.3 mm vor Oberkante anfangen und in Richtung der Nut fahren“ – „ein
    # stetiges gefallen durch die Nut“. Kein Satz hinab unter Oberkante + 0,3 außer in
    # Fahrtrichtung; senkrecht hinab endet jeder 0,3 über dem Material dort; im Material fällt die
    # Bahn gleichmäßig um die Zustellung je Umlauf.
    z_top = n.z_boden + 0.2
    tiefste = {}  # (x, y) gerundet → tiefstes z bisher
    fehler_ein, fehler_rampe, gefaelle = [], [], {}
    for (a, _wa), (b, wb) in zip(schnitt, schnitt[1:], strict=False):
        d = math.hypot(b.x - a.x, b.y - a.y)
        if b.z < a.z - 1e-9 and b.z < z_top + hb.UEBER_MATERIAL - 1e-9:
            if d < 1e-6:
                material = tiefste.get((round(b.x, 3), round(b.y, 3)), z_top)
                if b.z < material + hb.UEBER_MATERIAL - 1e-6:
                    fehler_ein.append((b.x, b.y, b.z, material))
            else:
                fahrt = math.degrees(math.atan2(b.y - a.y, b.x - a.x)) + 30.0
                if abs((wb - fahrt + 180.0) % 360.0 - 180.0) > 3.0:
                    fehler_rampe.append((b.x, b.y, b.z))
        schluessel = (round(b.x, 3), round(b.y, 3))
        tiefste[schluessel] = min(tiefste.get(schluessel, math.inf), b.z)
    pruefe(not fehler_ein, f"senkrecht ins Material: {fehler_ein[:3]}")
    pruefe(not fehler_rampe, f"hinab, aber nicht in Fahrtrichtung: {fehler_rampe[:3]}")
    for (a, _wa, sa, _i), (b, _wb, sb, _j) in zip(umlauf, umlauf[1:], strict=False):
        d = math.hypot(b.x - a.x, b.y - a.y)
        if sa == sb and d > 1e-6 and min(a.z, b.z) > n.z_boden + 1e-9:
            gefaelle.setdefault(sa, []).append((a.z - b.z) / d)
    for sp, liste in gefaelle.items():
        soll = 0.05 / n.laenge  # Zustellung ÷ Länge eines Umlaufs (Spur ± 0,2 neben der Mitte)
        pruefe(
            min(liste) > 0.97 * soll and max(liste) < 1.03 * soll,
            f"Spur {sp}: Gefälle {min(liste):.6f} … {max(liste):.6f} statt {soll:.6f} je mm",
        )
    pruefe(hbahn.gerade, "nicht auf dem geraden Stück angefangen")
    # Ins Material (z unter die Oberkante) kommt die Klinge auf einem geraden Stück: Der Winkel
    # steht dort fest.
    for k, (p, _w) in enumerate(schnitt):
        if p.z < z_top - 1e-9:
            davor = [v for _q, v in schnitt[max(k - 4, 0) : k + 1]]
            pruefe(max(davor) - min(davor) < 1e-6, f"ins Material in der Kurve bei {p.x}, {p.y}")
            break
    # Ist die Klinge schmaler als die Nut, fährt jede Spur eine eigene schmale Nut von oben bis
    # unten (Manuel, 2026-11-14: „das man die schmale Nut fährt auf der einen Seite und dann wieder
    # oben anfängt und dann an der anderen Seite entlang die selbe Nut fährt“): Spur 1 ganz, dann
    # Spur 2 ganz; jede beginnt oben (die Prüfung oben: nie senkrecht ins Material). Dazwischen
    # bleibt nichts stehen: Nebeneinander liegen die Spuren auf Endtiefe weniger als eine
    # Klingenbreite auseinander (sie überlappen).
    reihenfolge = [sp for _p, _w, sp, _s in umlauf]
    wechsel = sum(1 for a, b in zip(reihenfolge, reihenfolge[1:], strict=False) if a != b)
    pruefe(wechsel == hbahn.spuren - 1, f"Spuren nicht nacheinander: {wechsel} Wechsel")
    unten = {(sp, st): (p.x, p.y) for p, _w, sp, st in umlauf if p.z < n.z_boden + 1e-9}
    abstand_max = max(
        math.dist(unten[(sp, st)], unten[(sp + 1, st)])
        for (sp, st) in unten
        if (sp + 1, st) in unten
    )
    print(f"Spuren: größter Abstand nebeneinander {abstand_max:.3f} mm (Klinge 2,6)")
    pruefe(abstand_max < 2.6 - 0.01, f"zwischen den Spuren bleibt etwas stehen: {abstand_max:.3f}")
    # Unabhängig: die Klinge als Rechteck (Schneide vorn auf dem Punkt, Körper `laenge` dahinter,
    # quer 2,6) muss in jeder Stellung ganz im Grund der Nut liegen.
    grund_flaeche = next(
        f for f in teil.Faces if abs(f.BoundBox.ZMin - 8.0) < 1e-6 and len(f.Wires) == 2
    )
    draussen = 0.0
    for p, w in schnitt[:: max(1, len(schnitt) // 400)]:
        a = math.radians(w - 30.0)
        c, s = math.cos(a), math.sin(a)
        ecken = [(0.0, -1.3), (0.0, 1.3), (-L_KLINGE, 1.3), (-L_KLINGE, -1.3)]
        pts = [V(p.x + c * u - s * v, p.y + s * u + c * v, 8.0) for u, v in ecken]
        klinge = Part.Face(Part.makePolygon(pts + pts[:1]))
        draussen = max(draussen, klinge.Area - klinge.common(grund_flaeche).Area)
    print(f"Klinge außerhalb des Grunds: höchstens {draussen:.5f} mm2")
    pruefe(draussen < 1e-3, f"die Klinge ragt {draussen:.4f} mm2 aus der Nut")
    # Eine Klinge, die die Nut füllt: eine Spur; 0,1 schmaler: zwei, bis an die Wände (sonst
    # bliebe je Seite ein Streifen am Grund stehen). Werte 0: Satz.
    voll = hb.planen(
        n, hw.__class__(**{**hw.__dict__, "breite": 2.989, "laenge": 0.0, "schritt": 0.1})
    )
    pruefe(voll.spuren == 1, f"Spuren bei voller Klinge: {voll.spuren}")
    fast = hb.planen(n, hw.__class__(**{**hw.__dict__, "breite": 2.9, "laenge": 0.7}))
    pruefe(fast.spuren == 2, f"Spuren bei 2,9 in 3: {fast.spuren}")
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
# Das Räumen (Ø 1,5) lässt am Grund der Nut den Rest 0,2 stehen (boden_rest, Schritt 4 im Assistenten),
# dann ein Messstopp, dann das Hobeln. Die Spindel steht beim Hobeln (kein M3, kein S – auch nicht
# nach dem Messstopp); vor jedem Satz der Winkel – Siemens SPOS=DC im Satz, Heidenhain Zyklus 13
# mit M19, LinuxCNC M19 R; GRBL kann es nicht und sagt das.
import re  # noqa: E402

import Path.Main.Job as PathJob  # noqa: E402

from camaddon import fraeserform as ff  # noqa: E402
from camaddon import hobeln as hop  # noqa: E402
from camaddon import job_schnittwerte as js  # noqa: E402
from camaddon import kontur as ko  # noqa: E402
from camaddon import messstopp as ms  # noqa: E402
from camaddon import postprozessor as pp  # noqa: E402
from camaddon import raeumen as ra  # noqa: E402
from camaddon import uebergabe_werkzeuge as ue  # noqa: E402
from camaddon import werkzeuge as wz  # noqa: E402

profil_ordner = os.environ.get("FREECAD_USER_HOME", "")
if not profil_ordner or not FreeCAD.getUserAppDataDir().startswith(profil_ordner):
    raise AssertionError("Kein Testprofil – die Werkzeugverwaltung würde überschrieben.")
stoss = wz.Werkzeug(nummer=9, art=wz.STOSSWERKZEUG, name="Hobel 2,6", schneidenbreite=2.6,
                    klingenlaenge=L_KLINGE, spindelwinkel=30.0, stechtiefe=4.0)  # fmt: skip
fraeser = wz.Werkzeug(nummer=2, name="VHM 1,5", durchmesser=1.5, schneiden=2, schneidenlaenge=6.0,
                      eintauchwinkel=3.0)  # fmt: skip
einsatz = wz.Einsatz(art=wz.SCHRUPPEN, ae=0.3, ap=2.0, vc=60.0, fz=0.02)
fraeser.schnittwerte[wz.ALLE] = [einsatz]
bibliothek = wz.Bibliothek([fraeser, stoss])
bibliothek.speichern()
ue.uebergeben(bibliothek)
doc = FreeCAD.newDocument("Hobeln")
doc.UndoMode = 1
objekt = doc.addObject("Part::Feature", "Deckel")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
doc.recompute()
nut = hb.hobelnuten(objekt.Shape)[0]
grund, waende = nut.name, [f for f in nut.flaechen if f != nut.name]


def tiefste(bahn):
    return min(p.z for p in bahn.punkte if not p.eilgang)


# Räumen und Kontur ohne Rest wie bisher; mit Rest nur am Grund der Nut 0,2 höher; ein Rest für eine
# andere Fläche ändert keinen Satz. Genau gerechnet: Die grobe Vorschau des Räumens findet in der
# 3 mm breiten Nut keinen Platz (ihr Raster), auch nicht mit Ø 2.
form = ff.von_werkzeug(fraeser)
ohne = ra.bahn_fuer(job, job.Model.Group, form, 2.0, 0.3, 0.0, [grund])
mit = ra.bahn_fuer(job, job.Model.Group, form, 2.0, 0.3, 0.0, [grund], boden_rest=((grund, 0.2),))
fremd = ra.bahn_fuer(job, job.Model.Group, form, 2.0, 0.3, 0.0, [grund],
                    boden_rest=(("Face1", 0.2),))  # fmt: skip
print(f"Räumen: tiefste Spitze ohne Rest {tiefste(ohne):.3f}, mit Rest {tiefste(mit):.3f}")
pruefe(abs(tiefste(ohne) - 8.0) < 1e-6, f"Räumen ohne Rest: {tiefste(ohne)}")
pruefe(abs(tiefste(mit) - 8.2) < 1e-6, f"Räumen mit Rest: {tiefste(mit)}")
pruefe(
    [(p.x, p.y, p.z, p.eilgang) for p in fremd.punkte]
    == [(p.x, p.y, p.z, p.eilgang) for p in ohne.punkte],
    "ein Rest auf einer anderen Fläche ändert das Räumen",
)
k_ohne = ko.vorschau(job, job.Model.Group, form, 2.0, 0.3, 0.1, True, waende, breite=0.1)
k_mit = ko.vorschau(job, job.Model.Group, form, 2.0, 0.3, 0.1, True, waende, breite=0.1,
                    waende_rest=tuple((w, 0.2) for w in waende))  # fmt: skip
print(f"Kontur: tiefste Spitze ohne Rest {tiefste(k_ohne):.3f}, mit Rest {tiefste(k_mit):.3f}")
pruefe(abs(tiefste(k_ohne) - 8.0) < 1e-6, f"Kontur ohne Rest: {tiefste(k_ohne)}")
pruefe(abs(tiefste(k_mit) - 8.2) < 1e-6, f"Kontur mit Rest: {tiefste(k_mit)}")

# Die Vorschau im Assistenten, aus dem Vollen (die Vorgabe; Manuel, 2026-11-14: „Also das ja Sinn
# der Sache das man es nicht fräst“): ab der Oberkante (hier das Teil, 10) bis zum Grund (8), je
# Umlauf 0,05 – 40 Umläufe, ein ebener, ein Leerumlauf; zwei Spuren.
hv = hop.vorschau(job, stoss, [waende[0]], zustellung=0.05, vorschub=6000.0, oben=10.0)
pruefe(hv.namen == [grund] and len(hv.je_nut) == 1 and not hv.nicht_passend, f"Vorschau: {hv}")
pruefe(
    hv.je_nut[0]["umlaeufe"] == 40 + 1 + 1 and hv.je_nut[0]["spuren"] == 2,
    f"aus dem Vollen: {hv.je_nut[0]['umlaeufe']} Umläufe, {hv.je_nut[0]['spuren']} Spuren",
)
z_schnitt = [p.z for p in hv.punkte if not p.eilgang]
pruefe(max(z_schnitt) <= 10.3 + 1e-9 and min(z_schnitt) >= 8.0 - 1e-9, "aus dem Vollen: Höhen")
print(f"Aus dem Vollen: {hv.zeit:.1f} min, {len(hv.punkte)} Sätze")
# Die Klinge muss so tief reichen wie die Nut ab der Oberkante (+ 0,5): sonst stieße der Schaft
# ans Teil. Das Stoßwerkzeug reicht 4 – mit dem Rohteil 3 mm über der Nut (11 − 8 = 3 + 0,5) geht
# es, 4 über (12) nicht.
pruefe(not hop.klinge_grund(nut, stoss, 0.0, 3.0), "Stechtiefe 4 für 3 tief")
pruefe("Schaft" in hop.klinge_grund(nut, stoss, 0.0, 4.0), "Stechtiefe 4 für 4 tief geht")
try:
    hop.vorschau(job, stoss, [grund], oben=12.0)
    pruefe(False, "Klinge zu kurz für 4 mm")
except ValueError as satz:
    pruefe("Schaft" in str(satz), f"zu kurz: {satz}")
# Mit „Vorher fräsen, Rest hobeln“: nur der Rest. Stehen die Wände noch 0,3 vor, nicht – ein Satz,
# der „Schlichten danach“ anbietet.
hv_rest = hop.vorschau(job, stoss, [grund], aus_dem_vollen=False, oben=10.0)
pruefe(hv_rest.je_nut[0]["umlaeufe"] == 3 + 1 + 1, f"Rest: {hv_rest.je_nut[0]['umlaeufe']}")
try:
    hop.vorschau(job, stoss, [grund], wand_aufmass=0.3, aus_dem_vollen=False)
    pruefe(False, "Klinge 2,6 zwischen Wänden mit 0,3 Aufmaß")
except ValueError as satz:
    print(ascii(f"Wände mit Aufmaß: {satz}"))
    pruefe(getattr(satz, "daten", {}).get("waende"), f"ohne Hinweis auf die Wände: {satz}")
# Auch 0,1 nicht: Gehobelt wird erst zwischen fertigen Wänden (die äußeren Spuren führen sonst
# seitlich ins Aufmaß, Zweifler 14.11.).
try:
    hop.vorschau(job, stoss, [grund], wand_aufmass=0.1, aus_dem_vollen=False)
    pruefe(False, "Klinge zwischen Wänden mit 0,1 Aufmaß")
except ValueError as satz:
    pruefe(getattr(satz, "daten", {}).get("waende"), f"0,1: ohne Hinweis auf die Wände: {satz}")
# Nicht vorgefräst (Räumen fehlt oder sein Fräser passt nicht hinein): nicht hobeln.
try:
    hop.vorschau(job, stoss, [grund], vorgefraest=set(), aus_dem_vollen=False)
    pruefe(False, "gehobelt, ohne dass die Nut vorgefräst ist")
except ValueError as satz:
    pruefe("Material" in str(satz), f"nicht vorgefräst: {satz}")
pruefe(
    hop.vorschau(job, stoss, [grund], vorgefraest={grund}, aus_dem_vollen=False).namen == [grund],
    "vorgefräst",
)
# Das vorgeschlagene Stoßwerkzeug: die Schneide 3 − 2 · (0,005 + 0,02) auf 0,1 abgerundet, die
# Klinge so lang, dass sie R 10 fährt, geschwenkt – seit den kürzeren Sätzen in Bögen 0,8 (vorher 0,7).
vorschlag = hop.werkzeug_vorschlag([nut])
tief = hop.werkzeug_vorschlag([nut], 3.0)
pruefe(tief.stechtiefe == 4.0 and vorschlag.stechtiefe == 3.0, f"Stechtiefe {tief.stechtiefe}")
print(
    ascii(f"Vorschlag: {vorschlag.name} b {vorschlag.schneidenbreite} L {vorschlag.klingenlaenge}")
)
pruefe(
    vorschlag.art == wz.STOSSWERKZEUG
    and abs(vorschlag.schneidenbreite - 2.9) < 1e-9
    and abs(vorschlag.klingenlaenge - 0.8) < 1e-9
    and not hb.klinge_pruefen(nut, vorschlag.schneidenbreite, vorschlag.klingenlaenge),
    f"Vorschlag: {vorschlag}",
)

tc_fraeser = js.controller_ohne_transaktion(doc, job, fraeser, einsatz)
raeumen = ra.lege_an(job, tc_fraeser, 2.0, 0.3, 0.0, flaechen=[grund], boden_rest=((grund, 0.2),))
doc.recompute()
z_raeumen = min(
    float(c.Parameters["Z"])
    for c in raeumen.Path.Commands
    if c.Name in ("G1", "G01", "G2", "G02", "G3", "G03") and "Z" in c.Parameters
)
pruefe(
    list(raeumen.RestFlaechen) == [grund]
    and abs(float(raeumen.RestBoden) - 0.2) < 1e-9
    and abs(float(raeumen.FinalDepth) - 8.2) < 1e-6
    and abs(z_raeumen - 8.2) < 1e-6,
    f"Räumen: {list(raeumen.RestFlaechen)}, {raeumen.RestBoden}, {raeumen.FinalDepth}, {z_raeumen}",
)
# Das Räumen (Raster) fährt in den Bögen der 3 mm breiten Nut nicht bis unten (dort nur seine
# Eintauchstellen) – die Wände fährt eine Kontur nach, bis 0,2 über den Grund (wie „Schlichten
# danach“ im Assistenten). Erst dann ist die Nut überall bis auf den Rest gefräst
# (_nicht_vorgefraest).
wand_op = ko.lege_an(job, tc_fraeser, 2.0, 0.1, 0.0, True, 0.1, flaechen=waende,
                     waende_rest=tuple((w, 0.2) for w in waende))  # fmt: skip
doc.recompute()
tc = hop.controller(doc, job, stoss)
stopp = ms.lege_an(job, tc_fraeser, tc)
op = hop.lege_an(job, tc)
doc.recompute()
pruefe(hop.ist_hobeln(op) and op.Nuten == 1, f"Operation: {op.Label}, {op.Nuten} Nuten")
print(f"Operation aus dem Vollen ab {float(op.StartDepth):.2f}, {len(op.Path.Commands)} Befehle")
pruefe(str(tc.SpindleDir) == "None" and float(tc.SpindleSpeed) == 0.0, "die Spindel dreht")
pruefe(tc.HorizFeed.getValueAs("mm/min").Value == 6000.0, f"Hub {tc.HorizFeed}")
pruefe("Hobeln" in tc.Label, f"Controller {tc.Label}")
# Der Einsatz „Hobeln“: Richtwerte, Drehzahl 0, Vorschub = Hub.
from camaddon import schnittdaten as sd  # noqa: E402
from camaddon import werkzeugkiste as wk  # noqa: E402

mit_werten = wz.Werkzeug.aus_dict(stoss.als_dict())
wk.richtwerte_eintragen(mit_werten)
hobeln_p1 = [e for e in mit_werten.einsaetze("P1") if e.art == wz.HOBELN]
pruefe(len(hobeln_p1) == 1 and hobeln_p1[0].ap == 0.08, f"Richtwerte: {mit_werten.schnittwerte}")
# Die Zustellung je Werkstoffklasse mit dem fz-Faktor der Klasse (Manuel: „Die Zustellung ist ja
# Werkzeug abhängig“): Edelstahl M 0,08 · 0,7, gehärtet H 0,08 · 0,5.
for klasse, soll in (("M", 0.06), ("H", 0.04)):
    ap_k = [e.ap for e in mit_werten.einsaetze(klasse) if e.art == wz.HOBELN]
    pruefe(ap_k == [soll], f"Richtwert {klasse}: {ap_k} statt {soll}")
pruefe(hop.zustellung_fuer(stoss) == hop.ZUSTELLUNG == 0.08, "ohne Wert nicht 0,08")
pruefe(abs(float(op.Zustellung) - 0.08) < 1e-9, f"Operation ohne Wert: {float(op.Zustellung)}")
eigen = wz.Werkzeug.aus_dict(stoss.als_dict())
eigen.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.HOBELN, ap=0.04, vc=6.0)]
pruefe(hop.zustellung_fuer(eigen) == 0.04, "die Zustellung des Werkzeugs gilt nicht")
# Die Übergabe an FreeCAD mit Werten „Hobeln“ für alle Werkstoffe (KeyError 'hobeln' bis 14.11.)
# – jede Einsatzart hat dort einen Eintrag.
pruefe(all(a in ue.BEARBEITUNGSARTEN for a in wz.EINSATZARTEN), "Einsatzart ohne Übergabe")
try:
    ue.uebergeben(wz.Bibliothek([fraeser, eigen]))
except Exception as fehler_ue:  # noqa: BLE001
    pruefe(False, f"Übergabe mit Hobeln für alle: {fehler_ue!r}")
ue.uebergeben(bibliothek)
if hobeln_p1:
    pruefe(sd.rechne(mit_werten, hobeln_p1[0])[:2] == (0.0, 6000.0), "n, vf beim Hobeln")
pruefe(abs(float(op.FinalDepth) - 8.0) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
notizen = [b.Name for b in op.Path.Commands if b.Name.startswith("(SPINDEL ")]
pruefe(len(notizen) > 100, f"nur {len(notizen)} Spindelwinkel")
programme = {}
for kennung in ("siemens", "heidenhain", "linuxcnc", "grbl", "fanuc", "mach", "mazak"):
    programme[kennung] = pp.programm(pp.abschnitte(job), pp.steuerung(kennung), None, "Hobeln")
    zeilen = programme[kennung].zeilen
    notiz = [z for z in zeilen if "(SPINDEL " in z.upper()]  # nicht „SPINDELNASE“ im Kopf
    pruefe(not notiz, f"{kennung}: Notiz im Programm: {notiz[:3]}")
    # Nach dem Halt des Messstopps (M0) kommt nur noch das Hobeln: keine Spindel an, kein S.
    halt = [i for i, z in enumerate(zeilen) if {"M0", "M00"} & set(z.split())]
    pruefe(halt, f"{kennung}: kein Halt")
    danach = zeilen[halt[-1] + 1 :] if halt else zeilen
    m3 = [z for z in danach if {"M3", "M03", "M4", "M04"} & set(z.split())]
    # „M19 S…“ (Fanuc, Mach) ist der Winkel der stehenden Spindel, keine Drehzahl.
    s_wort = [z for z in danach if re.search(r"(^|\s)S\d", z) and "M19" not in z.split()]
    pruefe(not m3 and not s_wort, f"{kennung}: Spindel nach dem Messstopp: {(m3 + s_wort)[:3]}")
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
halt_si = max(i for i, z in enumerate(si) if {"M0", "M00"} & set(z.split()))
unten = next(
    i
    for i, z in enumerate(si)
    if i > halt_si and "Z" in z and z.startswith("G") and float(z.split("Z")[1].split()[0]) < 10.5
)
pruefe(si[erster].startswith("G0") and erster < unten, f"erster Winkel: {si[erster]}, {si[unten]}")
# Steuerungen, die vor dem Satz drehen, drehen am alten Punkt: auf die Mitte zwischen dem Winkel
# davor und dem des Satzes (LinuxCNC M19 R) – Siemens dreht im Satz (SPOS), auf den Winkel selbst.
si_w = [float(z.split("SPOS=DC(")[1].split(")")[0]) for z in si if "SPOS=DC(" in z]
lc_w = [float(z.split("M19 R")[1].split()[0]) for z in programme["linuxcnc"].zeilen
        if z.startswith("M19 R")]  # fmt: skip
pruefe(
    len(si_w) == len(lc_w) and len(si_w) > 100, f"Winkel: Siemens {len(si_w)}, LinuxCNC {len(lc_w)}"
)
mitte_abw = 0.0
for k in range(1, min(len(si_w), len(lc_w))):
    d = (si_w[k] - si_w[k - 1] + 180.0) % 360.0 - 180.0
    soll = (si_w[k - 1] + d / 2.0) % 360.0
    mitte_abw = max(mitte_abw, abs((lc_w[k] - soll + 180.0) % 360.0 - 180.0))
pruefe(mitte_abw < 0.002, f"LinuxCNC nicht auf der Mitte zweier Winkel: {mitte_abw:.4f} Grad")

# „Spindel als Rundachse mitführen (ohne Halt je Satz)“ – der Haken, vorbelegt aus (Manuel,
# 2026-11-14: die Funktionen „als option beim generieren des programs“). Siemens: M70, je Satz
# „C=DC(w)“ statt SPOS, M5 danach; Fanuc: Cs-Achse „C“ fortlaufend, F so, dass X, Y, Z im Hub
# fahren, Ein/Aus trägt man ein (Maschinenhersteller); ohne Eintrag, an Heidenhain und GRBL: der
# Grundweg.
pruefe(not any(s0.spindel_achse for s0 in pp.STEUERUNGEN.values()), "Spindel als Achse vorbelegt")
roh_w = [float(b.Name.strip("()").split()[1]) for b in op.Path.Commands
         if b.Name.startswith("(SPINDEL ")]  # fmt: skip
achse = {}
for kennung in ("siemens", "fanuc", "linuxcnc", "heidenhain", "grbl"):
    s_a = pp.steuerung(kennung).ersetzt(spindel_achse=True)
    achse[kennung] = pp.programm(pp.abschnitte(job), s_a, None, "Hobeln")
si_a = achse["siemens"].zeilen
halt_a = max(i for i, z in enumerate(si_a) if {"M0", "M00"} & set(z.split()))
c_si = [(i, z) for i, z in enumerate(si_a) if "C=DC(" in z]
pruefe(len(c_si) == len(spos) and not any("SPOS" in z for z in si_a[halt_a:]),
       f"Siemens mit Achse: {len(c_si)} Sätze mit C, {len(spos)} mit SPOS")  # fmt: skip
m70 = [i for i, z in enumerate(si_a) if z == "M70"]
m5_nach = [i for i, z in enumerate(si_a) if z == "M5" and c_si and i > c_si[-1][0]]
zwischen = si_a[c_si[-1][0] + 1 : m5_nach[0]] if m5_nach else ["?"]
pruefe(
    len(m70) == 1
    and halt_a < m70[0] < c_si[0][0]
    and m5_nach
    and all(z.startswith("G0 ") for z in zwischen),
    f"Siemens M70/M5: {m70}, {m5_nach[:1]}, C {c_si[0][0]}…{c_si[-1][0]}, dazwischen {zwischen}",
)
m3_a = [z for z in si_a[halt_a:] if {"M3", "M03", "M4", "M04"} & set(z.split())]
pruefe(not m3_a, f"Siemens mit Achse: Spindel dreht {m3_a[:2]}")
# Der Winkel fortlaufend: DC fährt den kürzesten Weg (höchstens 180°) – Satz für Satz genau die
# Drehung der Bahn, nie ein Sprung um 360°; je Satz der Winkel der Notiz (modulo 360), nicht die
# Mitte.
dc_w = [float(z.split("C=DC(")[1].split(")")[0]) for _i, z in c_si]
pruefe(all(0.0 <= w < 360.0 for w in dc_w), f"DC außerhalb 0 … 360: {min(dc_w)} {max(dc_w)}")
pruefe(len(dc_w) == len(roh_w), f"Winkel: {len(dc_w)} Sätze, {len(roh_w)} Notizen")
abw_mod = max(
    abs((a - b % 360.0 + 180.0) % 360.0 - 180.0) for a, b in zip(dc_w, roh_w, strict=False)
)
abw_weg = max(
    abs((dc_w[k] - dc_w[k - 1] + 180.0) % 360.0 - 180.0 - (roh_w[k] - roh_w[k - 1]))
    for k in range(1, min(len(dc_w), len(roh_w)))
)
groesster = max(abs(roh_w[k] - roh_w[k - 1]) for k in range(1, len(roh_w)))
print(
    f"Achse Siemens: {len(dc_w)} Sätze, Abweichung {abw_mod:.4f}°, Weg {abw_weg:.4f}°, größte"
    f" Drehung je Satz {groesster:.2f}°, {roh_w[-1] - roh_w[0]:.0f}° gesamt"
)
pruefe(abw_mod < 0.0006 and abw_weg < 0.0012 and groesster < 90.0, "Winkel nicht fortlaufend")
pruefe(
    any("Spindel als Achse im Satz" in h for h in achse["siemens"].hinweise),
    f"Siemens ohne Hinweis zum Achsnamen: {achse['siemens'].hinweise[:3]}",
)
# Fanuc ohne eingetragenes „Ein“, LinuxCNC ohne belegten Satz: der Grundweg und ein Satz dazu.
for kennung in ("fanuc", "linuxcnc"):
    pruefe(achse[kennung].zeilen == programme[kennung].zeilen, f"{kennung}: ohne Ein anders")
    pruefe(
        any("fehlt" in h and "Spindel als Achse ein" in h for h in achse[kennung].hinweise),
        f"{kennung}: kein Hinweis {achse[kennung].hinweise[:3]}",
    )
for kennung, wort in (("heidenhain", "291"), ("grbl", "Winkel")):
    pruefe(achse[kennung].zeilen == programme[kennung].zeilen, f"{kennung}: mit Haken anders")
    pruefe(any(wort in h for h in achse[kennung].hinweise), f"{kennung}: {achse[kennung].hinweise}")
# Fanuc mit eingetragenem Ein/Aus (Beispiel M-Befehle): C fortlaufend wie die Notiz, kein M19, und
# F so, dass X, Y, Z mit dem Hub (6000 mm/min) fahren – F zählt C in Grad mit.
s_f = pp.steuerung("fanuc").ersetzt(
    spindel_achse=True, spindel_achse_ein="M199", spindel_achse_aus="M198"
)
fa = pp.programm(pp.abschnitte(job), s_f, None, "Hobeln").zeilen
halt_f = max(i for i, z in enumerate(fa) if {"M0", "M00"} & set(z.split()))
c_fa = [z for z in fa[halt_f:] if z.startswith("G") and re.search(r"\sC-?\d", z)]
pruefe(fa.count("M199") == 1 and fa.count("M198") == 1, "Fanuc: Ein/Aus nicht je einmal")
pruefe(not any(z.startswith("M19 ") for z in fa), "Fanuc mit Achse: noch M19")
cf_w = [float(re.search(r"(?:^|\s)C(-?[\d.]+)", z).group(1)) for z in c_fa]
pruefe(
    len(cf_w) == len(roh_w) and max(abs(a - b) for a, b in zip(cf_w, roh_w, strict=False)) < 6e-4,
    f"Fanuc: C nicht fortlaufend wie die Notiz ({len(cf_w)}, {len(roh_w)})",
)
stand_f, c_davor, f_fehler, f_saetze = {}, None, 0.0, 0
eintauchen_f = tc.VertFeed.getValueAs("mm/min").Value
f_faktor = 1.0
for i_f, z in enumerate(fa):
    if not z.startswith("G") or z.startswith("G53"):
        continue  # nur Sätze im Werkstück
    werte_f = dict(re.findall(r"(?:^|\s)([XYZCF])(-?[\d.]+)", z))
    werte_f = {k: float(v) for k, v in werte_f.items()}
    if i_f > halt_f and z.startswith("G1") and "C" in werte_f and c_davor is not None:
        weg_xyz = math.dist([stand_f.get(a, 0.0) for a in "XYZ"],
                            [werte_f.get(a, stand_f.get(a, 0.0)) for a in "XYZ"])  # fmt: skip
        if weg_xyz > 1e-6:
            gesamt_f = math.hypot(weg_xyz, werte_f["C"] - c_davor)
            v_xyz = werte_f["F"] * weg_xyz / gesamt_f  # Hub oder Eintauchen (senkrecht)
            f_fehler = max(f_fehler, min(abs(v_xyz - 6000.0), abs(v_xyz - eintauchen_f)))
            f_saetze += 1
            f_faktor = max(f_faktor, gesamt_f / weg_xyz)
    stand_f.update({a: werte_f[a] for a in "XYZ" if a in werte_f})
    c_davor = werte_f.get("C", c_davor)
print(
    f"Fanuc: {f_saetze} Sätze geprüft, X/Y/Z-Vorschub höchstens {f_fehler:.2f} mm/min daneben,"
    f" F bis {f_faktor:.2f}-mal so groß"
)
pruefe(f_saetze > 100 and f_fehler < 0.05, f"Fanuc: F zählt C nicht mit ({f_fehler:.2f})")
# Am Deckel steigt der Winkel nur. Ein nach innen gewölbtes Stück der Nut (Bahn im Uhrzeigersinn
# um R 10) lässt ihn fallen – hier von 365° über 360° auf 355°, je Satz 0,5°: Fanuc schreibt C
# fortlaufend fallend, ohne Sprung, und sagt (Fenster und Programm), dass Roll-over nur mit
# RABx = 0 und RAAx = 0 geht – mit RAAx = 1 drehte jeder fallende Satz +359,5° in der Nut
# (B-63534EN/02, 20.2.2, S. 531). Siemens DC je Satz 0 … 360, über 0 hinweg auf 359,5.
bogen_w = [365.0 - 0.5 * k for k in range(21)]
befehle_k = [("G0", {"Z": 15.0})]
for k, w_k in enumerate(bogen_w):
    lage = math.radians(w_k - 360.0 + 90.0)  # im Uhrzeigersinn: Fahrtrichtung = Lage − 90°
    punkt = {"X": 10.0 * math.cos(lage), "Y": 10.0 * math.sin(lage)}
    befehle_k.append((f"({pp.SPINDEL_NOTIZ}{w_k:.3f})", {}))
    if k == 0:
        befehle_k += [("G0", punkt), ("G1", {"Z": 9.0, "F": 33.0})]
    else:
        befehle_k.append(("G1", dict(punkt, Z=9.0, F=100.0)))
befehle_k.append(("G0", {"Z": 15.0}))
konkav = [pp.Abschnitt("Hobeln konkav", 5, 0.0, False, befehle=befehle_k)]
pk = pp.programm(konkav, s_f, None, "Konkav")
c_k = [float(re.search(r"(?:^|\s)C(-?[\d.]+)", z).group(1)) for z in pk.zeilen
       if z.startswith("G") and re.search(r"\sC-?\d", z)]  # fmt: skip
pruefe(
    len(c_k) == len(bogen_w) and max(abs(a - b) for a, b in zip(c_k, bogen_w, strict=False)) < 6e-4,
    f"Fanuc konkav: C {c_k[:3]} … {c_k[-3:]} statt {bogen_w[0]} … {bogen_w[-1]} fallend",
)
pruefe(
    all(-0.5 - 1e-6 <= b - a < 0 for a, b in zip(c_k, c_k[1:], strict=False)),
    f"Fanuc konkav: C nicht stetig fallend {c_k}",
)
rollover = [h for h in pk.hinweise if "RAAx = 0" in h and "RABx = 0" in h]
pruefe(rollover, f"Fanuc konkav: kein Satz zu Roll-over {pk.hinweise}")
pruefe(
    any("RAAX = 0" in z.upper() for z in pk.zeilen if z.startswith("(")),
    "Fanuc konkav: Roll-over nicht im Programm",
)
pruefe(fa.count("M199") == 1 and any("RAAX" in z.upper() for z in fa), "Fanuc Deckel: Roll-over")
s_si_k = pp.steuerung("siemens").ersetzt(spindel_achse=True)
dc_k = [float(z.split("C=DC(")[1].split(")")[0])
        for z in pp.programm(konkav, s_si_k, None, "Konkav").zeilen if "C=DC(" in z]  # fmt: skip
pruefe(
    len(dc_k) == len(bogen_w)
    and all(0.0 <= w < 360.0 for w in dc_k)
    and max(
        abs((a - b % 360.0 + 180.0) % 360.0 - 180.0) for a, b in zip(dc_k, bogen_w, strict=False)
    )
    < 6e-4
    and dc_k[10:12] == [0.0, 359.5],
    f"Siemens konkav: DC {dc_k}",
)
pruefe(
    not any("RAA" in h for h in pp.programm(konkav, s_si_k, None, "Konkav").hinweise),
    "Siemens: Satz zu Roll-over (gilt nur für Fanuc)",
)

# Zwei Nuten, die Klinge passt nur in die eine (der Kreis R 5 ist zu eng): Die Operation hobelt die,
# die geht (bis 14.11. brach sie ganz ab, und am Grund der passenden blieb der Rest des Räumens).
# Ohne Räumen davor hobelt sie nichts – die Klinge stieße in volles Material.
zwei = deckel(ring_um(rechteck(70, 50, 10)).fuse(ring_um(Part.Wire([Part.makeCircle(5.0)]))))
doc2 = FreeCAD.newDocument("HobelnZwei")
obj2 = doc2.addObject("Part::Feature", "Deckel")
obj2.Shape = zwei
doc2.recompute()
job2 = PathJob.Create("Job", [obj2])
doc2.recompute()
nuten2 = hb.hobelnuten(obj2.Shape)
pruefe(
    len(nuten2) == 2, f"zwei Nuten: {[(x.name, x.grund) for x in hb.alle_hobelnuten(obj2.Shape)]}"
)
gruende2 = [x.name for x in nuten2]
tc2 = hop.controller(doc2, job2, stoss)
ohne_raeumen = hop.lege_an(job2, tc2, gruende2, vorgefraest=True)
doc2.recompute()
pruefe(ohne_raeumen.Nuten == 0, f"ohne Räumen gehobelt: {ohne_raeumen.Nuten}")
tc2_f = js.controller_ohne_transaktion(doc2, job2, fraeser, einsatz)
ra.lege_an(job2, tc2_f, 2.0, 0.3, 0.0, flaechen=gruende2,
           boden_rest=tuple((g, 0.2) for g in gruende2))  # fmt: skip
waende2 = [w for x in nuten2 for w in x.flaechen if w != x.name]
ko.lege_an(job2, tc2_f, 2.0, 0.1, 0.0, True, 0.1, flaechen=waende2,
           waende_rest=tuple((w, 0.2) for w in waende2))  # fmt: skip
doc2.recompute()
mit_raeumen = hop.lege_an(job2, tc2, gruende2, vorgefraest=True)
doc2.recompute()
g1 = [c for c in mit_raeumen.Path.Commands if c.Name in ("G1", "G01")]
pruefe(mit_raeumen.Nuten == 1 and len(g1) > 100, f"zwei Nuten: {mit_raeumen.Nuten}, {len(g1)} G1")
# Aus dem Vollen braucht es kein Räumen: die passende Nut ja, der Kreis R 5 nicht.
voll2 = hop.lege_an(job2, tc2, gruende2, oben=10.0)
doc2.recompute()
pruefe(voll2.Nuten == 1 and not voll2.Vorgefraest, f"aus dem Vollen, zwei Nuten: {voll2.Nuten}")
FreeCAD.closeDocument(doc2.Name)

# Frage 2 (Manuel, 2026-11-14: „C und D“): (d) kürzere Sätze in Bögen – höchstens BOGEN_WINKEL halber
# Schritt, nicht unter SCHRITT_MIN; (c) seitlicher Freiwinkel – die hintere Ecke schwenkt weniger aus.
pruefe(hb.schritt_im_bogen(math.inf) == hb.SCHRITT, "Gerade: Satzlänge")
pruefe(
    abs(hb.schritt_im_bogen(12.0) - 2 * 12 * math.tan(hb.BOGEN_WINKEL)) < 1e-12, "R 12: Satzlänge"
)
pruefe(hb.schritt_im_bogen(1.0) == hb.SCHRITT_MIN, "R 1: nicht kürzer als SCHRITT_MIN")
st_r12 = list(hb._stellen_je_stueck(hb.hobelnuten(teil)[0], hb.SCHRITT))
abstaende = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(st_r12, st_r12[1:], strict=False)]
pruefe(min(abstaende) < 0.11 and max(abstaende) <= hb.SCHRITT + 1e-9, f"Sätze {min(abstaende)}")
rechteck_a = hb._ueberstand(10.0, 2.6, 1.4, hb.SCHRITT)
trapez_a = hb._ueberstand(10.0, 2.6, 1.4, hb.SCHRITT, None, 2.0)
pruefe(trapez_a[0] < rechteck_a[0], f"Freiwinkel: außen {trapez_a[0]} gegen {rechteck_a[0]}")
pruefe(
    hb.kleinster_radius_fuer(3.6, 2.6, 2.0, freiwinkel=2.0)
    < hb.kleinster_radius_fuer(3.6, 2.6, 2.0),
    "Freiwinkel: kleinerer Radius möglich",
)
print(ascii(f"Ueberstand R10 2.6x1.4: Rechteck {rechteck_a[0]:.4f}, 2 Grad {trapez_a[0]:.4f}"))

# Rund geschliffene Klinge (Manuel, 2026-11-21, Horn Supermini 105: Schneide 3 breit, „auf eine seite
# rund … ein radius von 5mm“): so breit wie die Nut, die runde Seite zeigt zur Außenwand – daraus die
# Fahrtrichtung. Als Rechteck geht dieselbe Klinge nicht.
nut_r10 = hb.hobelnuten(teil)[0]
umriss = hb.klingen_umriss(3.0, 7.0, 1.0, rund=-5.0)
pruefe(
    max(v for _u, v in umriss) == 1.5 and min(v for _u, v in umriss) == -1.5
    and min(u for u, _v in umriss) > -4.6,
    f"Umriss der runden Klinge: {umriss}",
)  # fmt: skip
pruefe(
    hb.klinge_pruefen(nut_r10, 3.0, 7.0) != "", "Rechteck 3 × 7 in der Nut 3: muss abgelehnt sein"
)
pruefe(
    "Freiwinkel" in hb.klinge_pruefen(nut_r10, 3.0, 7.0, rund=-5.0),
    "runde Klinge ohne Freiwinkel: " + hb.klinge_pruefen(nut_r10, 3.0, 7.0, rund=-5.0),
)
pruefe(
    hb.klinge_pruefen(nut_r10, 3.0, 7.0, freiwinkel=1.0, rund=-5.0) == "",
    "runde Klinge: " + hb.klinge_pruefen(nut_r10, 3.0, 7.0, freiwinkel=1.0, rund=-5.0),
)
import dataclasses

w_rechts = hb.Hobelwerte(
    breite=3.0, laenge=7.0, versatz=0.0, zustellung=0.08, rest=2.0, sicher=30.0, vorschub=3000.0,
    freiwinkel=1.0, rund=-5.0,
)  # fmt: skip
w_links = dataclasses.replace(w_rechts, rund=5.0)
bahn_r, bahn_l = hb.planen(nut_r10, w_rechts), hb.planen(nut_r10, w_links)
pruefe(bahn_r.spuren == 1 and bahn_l.spuren == 1, f"runde Klinge: Spuren {bahn_r.spuren}")


def umlaufsinn(b):
    """> 0: gegen den Uhrzeigersinn (Fläche des ersten Umlaufs)."""
    p = [(q.x, q.y) for q, s in zip(b.punkte, b.spur, strict=True) if s is not None][:400]
    return sum(a[0] * c[1] - c[0] * a[1] for a, c in zip(p, p[1:], strict=False))


pruefe(
    umlaufsinn(bahn_r) > 0 > umlaufsinn(bahn_l),
    "runde Seite rechts: links herum; links: rechts herum",
)
# Die runde Seite an der Innenwand (falsche Fahrtrichtung): Die gerade Seite stieße an die Außenwand.
lagen = hb._spurlagen(nut_r10, w_rechts)[4][0]
luft_richtig, _s = hb._klinge_luft(nut_r10, lagen, 3.0, 7.0, 1.0, -5.0)
luft_falsch, _s = hb._klinge_luft(nut_r10, lagen, 3.0, 7.0, 1.0, 5.0)
pruefe(min(luft_richtig) > -1e-4 and min(luft_falsch) < -0.05,
       f"runde Klinge: Luft richtig {min(luft_richtig)}, falsch herum {min(luft_falsch)}")  # fmt: skip
# Der Kreis R 5,5 (Außenwand R 7): geht mit der runden Klinge R 5; eine mit R 9 nicht.
pruefe(hb.kleinster_radius_fuer(3.0, 3.0, 7.0, freiwinkel=1.0, rund=5.0) < 5.5, "rund 5 in R 5,5")
pruefe(hb.kleinster_radius_fuer(3.0, 3.0, 7.0, freiwinkel=1.0, rund=9.0) > 5.5, "rund 9 in R 5,5")
print(
    ascii(
        f"runde Klinge: Luft {min(luft_richtig):.4f}, falsch herum {min(luft_falsch):.4f}, "
        f"kleinster Radius {hb.kleinster_radius_fuer(3.0, 3.0, 7.0, freiwinkel=1.0, rund=5.0):.3f}"
    )
)
# Runde Seite ohne Ausführung: nicht raten.
from camaddon import hobeln as _hop_rund
from camaddon import werkzeuge as _wz_rund

_la105 = _wz_rund.Werkzeug(nummer=7, art=_wz_rund.STOSSWERKZEUG, schneidenbreite=3.0, klingenlaenge=7.0,
                           klingenradius=5.0, freiwinkel=1.0, stechtiefe=15.0)  # fmt: skip
pruefe("Ausführung" in _hop_rund.klinge_grund(nut_r10, _la105), "runde Seite ohne Ausführung")
_la105.ausfuehrung = _wz_rund.LINKS
pruefe(
    _hop_rund.klinge_grund(nut_r10, _la105) == "",
    "LA105: " + _hop_rund.klinge_grund(nut_r10, _la105),
)

# Gegenprüfung der runden Klinge (2026-11-21), fünf Funde:
# (1) Freiform (Erdnuss, r = 25 + 8·cos 2φ): nie eine Bahn mit NaN – eine endliche Bahn oder ein Satz.
from camaddon import kontur_bahn as _kb_rund

_pts = [
    V((25 + 8 * math.cos(2 * f)) * math.cos(f), (25 + 8 * math.cos(2 * f)) * math.sin(f), 0)
    for f in (2 * math.pi * k / 120 for k in range(120))
]
_bs = Part.BSplineCurve()
_bs.interpolate(_pts, PeriodicFlag=True)
nut_erdnuss = hb.hobelnuten(deckel(ring_um(Part.Wire([_bs.toShape()]))))[0]
for _b, _l, _fw, _rund in ((2.6, 1.6, 0.0, 0.0), (2.0, 4.0, 0.0, -4.0), (2.0, 4.0, 0.0, 4.0)):
    _w = hb.Hobelwerte(breite=_b, laenge=_l, versatz=0.0, zustellung=0.1, rest=0.2, sicher=15.0,
                       vorschub=3000.0, freiwinkel=_fw, rund=_rund)  # fmt: skip
    try:
        _bahn = hb.planen(nut_erdnuss, _w)
        pruefe(
            all(
                math.isfinite(q.x) and math.isfinite(q.y) and math.isfinite(q.z)
                for q in _bahn.punkte
            ),
            f"Erdnuss {_b} × {_l} rund {_rund}: Bahn mit NaN",
        )
        print(
            ascii(
                f"Erdnuss {_b}x{_l} rund {_rund}: {len(_bahn.punkte)} Punkte, {_bahn.spuren} Spuren"
            )
        )
    except ValueError as _f:
        pruefe("inf" not in str(_f) and "nan" not in str(_f), f"Erdnuss: Satz mit inf/nan: {_f}")
        print(ascii(f"Erdnuss {_b}x{_l} rund {_rund}: {_f}"))
# (2) Gerade aus zwei Strecken ohne Knick, runde Seite links (Fahrt andersherum): Die Einfahrt bleibt
# auf dem geraden Stück – der Spindelwinkel steht über Rampe und Eintritt.
_neu = []
for _s in nut_r10.segmente:
    if _s.bogen is None and _s.laenge > 20:
        _m = _s.bei(0.2)
        _neu += [_kb_rund._Strecke(_s.von, _m), _kb_rund._Strecke(_m, _s.nach)]
    else:
        _neu.append(_s)
nut_geteilt = dataclasses.replace(nut_r10, segmente=tuple(_neu))
for _rund in (-5.0, 5.0):
    _w = dataclasses.replace(w_rechts, rund=_rund, rest=0.2)
    _bahn = hb.planen(nut_geteilt, _w)
    _z_mat = nut_geteilt.z_boden + 0.2
    _k = next(i for i, q in enumerate(_bahn.punkte) if not q.eilgang and q.z < _z_mat - 1e-9)
    _ws = [_bahn.winkel[i] for i in range(_k + 1)
           if not _bahn.punkte[i].eilgang and _bahn.winkel[i] is not None]  # fmt: skip
    pruefe(_bahn.gerade and max(_ws) - min(_ws) < 0.01,
           f"geteilte Gerade, rund {_rund}: Winkel dreht in der Einfahrt um {max(_ws) - min(_ws)}")  # fmt: skip
# (3) Niere mit einem nach innen gewölbten Bogen R 10: Die Vorprüfung sagt es, statt „geht“.
_t = math.radians(60)


def _pol(r, a):
    return V(r * math.cos(a), r * math.sin(a), 0)


_c1, _c2 = _pol(20, _t), _pol(20, -_t)
_niere = Part.Wire([
    Part.Arc(_pol(30, -_t), _pol(30, 0), _pol(30, _t)).toShape(),
    Part.Arc(_pol(30, _t), _c1 + _pol(10, _t + math.pi / 2), _pol(10, _t)).toShape(),
    Part.Arc(_pol(10, _t), _pol(10, 0), _pol(10, -_t)).toShape(),
    Part.Arc(_pol(10, -_t), _c2 + _pol(10, -_t - math.pi / 2), _pol(30, -_t)).toShape(),
])  # fmt: skip
nut_niere = hb.hobelnuten(deckel(ring_um(_niere)))[0]
_grund = hb.klinge_pruefen(nut_niere, 3.0, 7.0, freiwinkel=1.0, rund=-5.0)
pruefe("nach innen gewölbt" in _grund, f"Niere, runde Klinge: {_grund!r}")
pruefe(
    hb.klinge_pruefen(nut_r10, 3.0, 7.0, freiwinkel=1.0, rund=-5.0) == "",
    "Rechteck: keine Gegenkurve",
)
# (5) Zwei Spuren, vorgefräst (Rest 0,5): zurück an den Anfang über der Oberkante der Nut, nicht zwischen
# den Wänden.
_w = hb.Hobelwerte(breite=2.9, laenge=7.0, versatz=0.0, zustellung=0.1, rest=0.5, sicher=15.0,
                   vorschub=3000.0, rund=-5.0)  # fmt: skip
_w36 = dataclasses.replace(_w, breite=2.6, laenge=3.0)
for _wk in (_w, _w36):
    try:
        _bahn = hb.planen(nut_r10, _wk)
    except ValueError:
        continue
    if _bahn.spuren < 2:
        continue
    _lang = [
        (a, b) for a, b in zip(_bahn.punkte, _bahn.punkte[1:], strict=False)
        if math.hypot(b.x - a.x, b.y - a.y) > 5.0
    ]  # fmt: skip
    pruefe(_lang and all(b.eilgang and b.z >= nut_r10.z_oben + hb.UEBER_MATERIAL - 1e-9 for _a, b in _lang),
           f"Überfahrt zwischen den Spuren unter der Oberkante: {[round(b.z, 2) for _a, b in _lang]}")  # fmt: skip

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
