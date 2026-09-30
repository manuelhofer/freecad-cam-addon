# Prüft die Fräserform und die Hüllfläche jedes Fräsers (W-003 Stufe V5a): das Profil von
# Kugel-, Torus-, Konik-, Fasen- und Radienfräser gegen die Formel, das Aufmaß, die Kammhöhe,
# die Form aus der Werkzeugverwaltung. Dann die Hüllfläche gegen eine Rechnung, die nichts
# auslassen kann: Bei einem Drehteil (Welle mit Absatz, Kugel) und einem Sechskant liegt die
# Berührung im Schnitt durch die Werkzeugachse – dort wird der Umriss sehr dicht abgetastet
# und jeder Punkt gegen das Profil gerechnet. Dazu eine Zeitgrenze.
import math
import os
import sys
import time

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import fraeserform as ff
from camaddon import vierachs_huelle as vh
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nah(a, b, genau=1e-9):
    return bool(np.all(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)) < genau))


V = FreeCAD.Vector
TOL = 0.02  # Vernetzung: das Netz liegt höchstens so weit innerhalb der Oberfläche
LAENGS, RADIAL = (0, 0, 1), (1, 0, 0)

# --- Das Profil -----------------------------------------------------------------------------
rho = np.array([0.0, 0.5, 1.7, 2.9, 3.0])
kugel = ff.kugel(3.0)
pruefe(nah(kugel.hoehe(rho), 3.0 - np.sqrt(9.0 - rho * rho)), f"Kugel: {kugel.hoehe(rho)}")
pruefe(kugel.hoehe(3.01) == math.inf, "neben der Kugel")
torus = ff.torus(3.0, 1.0)
soll = np.where(rho <= 2.0, 0.0, 1.0 - np.sqrt(np.maximum(1.0 - (rho - 2.0) ** 2, 0.0)))
pruefe(nah(torus.hoehe(rho), soll), f"Torus: {torus.hoehe(rho)}")
pruefe(ff.torus(3.0, 0.0).eben and ff.torus(3.0, 3.0).nur_kugel, "Torus mit rc 0 bzw. R")
# Konik: Kugel r 2, Kegel 10° je Seite; die Kugel geht bei ρ = r · cos 10° in den Kegel über.
oben = 2.0 / math.cos(math.radians(10)) + 10.0 * math.tan(math.radians(10))
konik = ff.konik(2.0, 10.0, 12.0, oben)
uebergang = 2.0 * math.cos(math.radians(10))
pruefe(nah(konik.hoehe(uebergang), 2.0 * (1 - math.sin(math.radians(10)))), "Konik am Übergang")
pruefe(nah(konik.hoehe(oben), 12.0), f"Konik oben: {konik.hoehe(oben)}")
pruefe(konik.kugel == 2.0 and not konik.nur_kugel and konik.konvex, "Konik: Kugel an der Spitze")
fase = ff.kegel(0.5, 4.0, 3.5)
pruefe(nah(fase.hoehe([0.3, 0.5, 2.25, 4.0]), [0.0, 0.0, 1.75, 3.5]), "Fase")
radien = ff.radien(2.0, 2.0, 4.0)
pruefe(nah(radien.hoehe([1.0, 2.0, 3.0, 4.0]), [0.0, 0.0, math.sqrt(3.0), 2.0]), "Radienfräser")
pruefe(not radien.konvex, "Radienfräser hohl")
# Die Hüllfläche rechnet ihn mit der Sehne: sie liegt unter der Kehle.
sehne = radien.aussen()
pruefe(sehne.konvex and nah(sehne.hoehe([1.0, 3.0]), [0.0, 1.0]), "Radienfräser mit der Sehne")
pruefe(
    bool(np.all(sehne.hoehe(np.linspace(0, 4, 41)) <= radien.hoehe(np.linspace(0, 4, 41)))),
    "Sehne unter der Kehle",
)

# Berührt eine Ebene, die um θ geneigt ist: die Kugel bei (R sin θ, R (1 − cos θ)), die
# Scheibe mit dem Rand, die Hohlkehle über ihre konvexe Hülle an Führung oder Rand.
theta = math.radians(35)
rho_s, z_s = kugel.stuetze(theta)
pruefe(
    abs(rho_s - 3 * math.sin(theta)) < 1e-4 and abs(z_s - 3 * (1 - math.cos(theta))) < 1e-4,
    f"Kugel berührt bei {rho_s}, {z_s}",
)
pruefe(nah(ff.scheibe(3.0).stuetze(0.0), (0.0, 0.0)), "Scheibe quer: die Mitte")
pruefe(nah(ff.scheibe(3.0).stuetze(0.2), (3.0, 0.0)), "Scheibe schräg: der Rand")
pruefe(nah(radien.stuetze(math.radians(30)), (2.0, 0.0)), "Radienfräser flach: die Führung")
pruefe(nah(radien.stuetze(math.radians(60)), (4.0, 2.0)), "Radienfräser steil: der Rand")

# Aufmaß: rundum größer, die Spitze wieder bei 0 – die Kugel eine größere Kugel, die Scheibe
# ein Torus mit dem Aufmaß als Eckradius, der Torus einer mit größerem Eckradius.
rho = np.linspace(0.0, 3.3, 34)
pruefe(nah(kugel.mit_aufmass(0.3).hoehe(rho), ff.kugel(3.3).hoehe(rho), 1e-6), "Kugel + 0,3")
pruefe(
    nah(ff.scheibe(3.0).mit_aufmass(0.3).hoehe(rho), ff.torus(3.3, 0.3).hoehe(rho), 1e-6),
    "Scheibe + 0,3",
)
pruefe(nah(torus.mit_aufmass(0.3).hoehe(rho), ff.torus(3.3, 1.3).hoehe(rho), 1e-6), "Torus + 0,3")
fase_auf = fase.mit_aufmass(0.2)
pruefe(abs(fase_auf.radius - (4.0 + 0.2)) < 1e-9, f"Fase + 0,2 bis {fase_auf.radius}")

# Kammhöhe zwischen zwei Bahnen: Kugel R 3 und 0,35 mm – 5,1 µm; unter der Scheibe 0.
pruefe(abs(kugel.kammhoehe(0.35) - (3 - math.sqrt(9 - 0.175**2))) < 1e-12, "Kammhöhe Kugel")
pruefe(torus.kammhoehe(4.0) == 0.0, "Kammhöhe unter der Scheibe")

# Aus der Werkzeugverwaltung, mit denselben Maßen wie das Bild.
for art, durchmesser, erwartet in (
    (wz.SCHAFTFRAESER, 12.0, "eben"),
    (wz.NUTENFRAESER, 30.0, "eben"),
    (wz.KUGELFRAESER, 6.0, "kugel"),
    (wz.LOLLIPOPFRAESER, 8.0, "kugel"),
    (wz.TORUSFRAESER, 12.0, "torus"),
    (wz.KONIKFRAESER, 4.0, "konik"),
    (wz.FASENFRAESER, 12.0, "kegel"),
    (wz.RADIENFRAESER, 14.0, "hohl"),
    (wz.FORMFRAESER, 12.0, None),
    (wz.GEWINDEFRAESER, 12.0, None),
    (wz.BOHRER, 8.0, None),
):
    w = wz.Werkzeug(art=art, durchmesser=durchmesser, kegelwinkel=3.0)
    form = ff.von_werkzeug(w)
    if erwartet is None:
        pruefe(form is None, f"{art}: {form}")
        continue
    ist = (
        "eben"
        if form.eben
        else (
            "kugel"
            if form.nur_kugel
            else (
                "konik"
                if form.kugel
                else (
                    "hohl"
                    if not form.konvex
                    else "torus" if any(s.art == ff.BOGEN for s in form.stuecke) else "kegel"
                )
            )
        )
    )
    pruefe(ist == erwartet, f"{art}: {ist} statt {erwartet}")
    if art != wz.KONIKFRAESER:  # der Kegel des Konikfräsers wird oben breiter
        pruefe(abs(form.radius - durchmesser / 2) < 1e-9, f"{art}: Radius {form.radius}")


# --- Die Hüllfläche gegen den dicht abgetasteten Umriss ------------------------------------
def abgetastet(umriss, schritt=0.002):
    """Punkte (a, x) dicht auf einem Linienzug [(a, x), …]."""
    teile = []
    for (a1, x1), (a2, x2) in zip(umriss, umriss[1:], strict=False):
        anzahl = max(2, int(math.hypot(a2 - a1, x2 - x1) / schritt) + 1)
        t = np.linspace(0.0, 1.0, anzahl)
        teile.append(np.column_stack([a1 + t * (a2 - a1), x1 + t * (x2 - x1)]))
    return np.concatenate(teile)


def im_schnitt(punkte, form, stellen):
    """Die Hüllfläche aus Punkten (Abstand zur Werkzeugachse, Höhe) im Schnitt durch die
    Werkzeugachse: an jeder Stelle die höchste Stelle x − z(Abstand)."""
    ergebnis = np.full(len(stellen), vh.KEIN_TREFFER)
    for i, stelle in enumerate(stellen):
        abstand = np.abs(punkte[:, 0] - stelle)
        unter = abstand <= form.radius
        if unter.any():
            ergebnis[i] = np.max(punkte[unter, 1] - form.hoehe(abstand[unter]))
    return ergebnis


FORMEN = {
    "Scheibe": ff.scheibe(3.0),
    "Kugel": kugel,
    "Torus": torus,
    "Kugel + 0,3": kugel.mit_aufmass(0.3),
    "Torus + 0,3": torus.mit_aufmass(0.3),
    "Konik": konik,
    "Fase spitz": ff.kegel(0.0, 4.0, 4.0),
    "Fase": fase,
    "Radienfräser (mit der Sehne)": radien.aussen(),
}


def vergleichen(teil, netz, umriss, stellen, phi, darunter):
    """Die Hüllfläche nie über dem Umriss (sie verletzte das Teil nicht) und höchstens
    `darunter` darunter (so weit liegt das Netz innen)."""
    punkte = abgetastet(umriss)
    for form_name, form in FORMEN.items():
        ist = vh.fraeser(netz, LAENGS, RADIAL, form, stellen, phi).r
        soll = im_schnitt(punkte, form, stellen)
        getroffen = np.isfinite(soll)
        for j in range(len(phi)):
            pruefe(
                bool(np.all(np.isfinite(ist[:, j]) == getroffen)),
                f"{teil}, {form_name}: getroffen an anderen Stellen",
            )
            abweichung = soll[getroffen] - ist[getroffen, j]
            # Über dem Umriss nur um das, was das Abtasten zwischen zwei Punkten auslässt.
            if abweichung.size and not (
                abweichung.min() >= -2e-3 and abweichung.max() <= darunter + 1e-4
            ):
                stelle = stellen[getroffen][int(np.argmax(np.abs(abweichung)))]
                fehler.append(
                    f"{teil}, {form_name}, {math.degrees(phi[j]):.0f}°: "
                    f"{abweichung.min():+.4f} … {abweichung.max():+.4f} (bei a = {stelle:.3f})"
                )
                break


# Welle mit Absatz (Drehteil): Ø 40 von −30 bis 0, Ø 30 von −42 bis −30. Der Schnitt durch
# die Werkzeugachse zeigt den Umriss – unter jedem Winkel derselbe.
welle = Part.makeCylinder(20, 30, V(0, 0, -30)).fuse(Part.makeCylinder(15, 12, V(0, 0, -42)))
stellen = vh.raster_a(-47.013, 5.0, 0.137)
vergleichen(
    "Absatz",
    vh.vernetze(welle.removeSplitter(), TOL),
    [(0.0, 0.0), (0.0, 20.0), (-30.0, 20.0), (-30.0, 15.0), (-42.0, 15.0), (-42.0, 0.0)],
    stellen,
    np.radians([0.0, 23.0]),
    TOL,
)
# Kugel Ø 24 um a = −25 auf der Achse – nur, wo sie höchstens 37° gegen die Werkzeugachse
# steht: An steilen Flanken liegt das Netz längs der Werkzeugachse weiter innen als TOL.
kreis = [(-25.0 + 12.0 * math.cos(w), 12.0 * math.sin(w)) for w in np.linspace(0.0, math.pi, 4001)]
vergleichen(
    "Kugel",
    vh.vernetze(Part.makeSphere(12, V(0, 0, -25)), TOL),
    kreis,
    vh.raster_a(-34.013, -16.0, 0.137),
    np.radians([0.0, 41.0]),
    TOL,
)

# Sechskant SW 30, 60 mm lang: weit weg von den Enden zählt nur der Querschnitt – ein
# Vieleck; der Schnitt durch die Werkzeugachse ist dort quer zur Achse. Das Netz ist genau.
ecken = [
    (
        10 * math.sqrt(3) * math.cos(math.radians(60 * k)),
        10 * math.sqrt(3) * math.sin(math.radians(60 * k)),
    )
    for k in range(7)
]
sechskant = Part.Face(Part.makePolygon([V(x, y, -60) for x, y in ecken])).extrude(V(0, 0, 60))
netz = vh.vernetze(sechskant, TOL)
vieleck = abgetastet(ecken, 0.0005)
for form_name, form in FORMEN.items():
    phi = np.radians(np.arange(0.0, 60.0, 2.5))
    ist = vh.fraeser(netz, LAENGS, RADIAL, form, [-30.0], phi).r[0]
    for j, winkel in enumerate(phi):
        x = vieleck[:, 0] * math.cos(winkel) + vieleck[:, 1] * math.sin(winkel)
        y = vieleck[:, 1] * math.cos(winkel) - vieleck[:, 0] * math.sin(winkel)
        unter = (np.abs(y) <= form.radius) & (x > 0)
        soll = np.max(x[unter] - form.hoehe(np.abs(y[unter])))
        if not (-1e-3 <= soll - ist[j] <= 1e-6):
            fehler.append(
                f"Sechskant, {form_name}, {math.degrees(winkel):.1f}°: {ist[j]:.5f} statt {soll:.5f}"
            )
            break

# --- Zeitgrenze: Kugelfräser Ø 6 auf der Welle Ø 60 × 100 mit Nocken, fürs Schlichten ------
# Schrittweite 0,35 mm und 0,5° rundum – je Winkel eigene Stellen längs, wie die Spirale.
teil = (
    Part.makeCylinder(30, 100, V(0, 0, -100))
    .fuse(Part.makeCylinder(12, 20, V(24, 0, -40)))
    .cut(Part.makeBox(10, 8, 30, V(25, -4, -90)))
)
netz = vh.vernetze(teil, TOL)
phi = vh.raster_phi(0.5)
anfang = -104.0 + 0.35 * np.arange(len(phi)) / len(phi)
beginn = time.time()
r = vh.je_winkel(netz, LAENGS, RADIAL, kugel, anfang, 0.35, 310, phi)
dauer = time.time() - beginn
print(ascii(f"Kugel auf der Welle mit Nocken: {r.size} Punkte in {dauer:.1f} s"))
pruefe(dauer < 60.0, f"zu langsam: {dauer:.1f} s")
pruefe(36 - TOL <= float(np.max(r)) <= 36, f"höchste Stelle: {np.max(r)}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
