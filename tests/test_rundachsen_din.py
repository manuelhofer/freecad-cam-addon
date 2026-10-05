# Prüft, dass jedes Programm Rundachsen nach DIN 66217 schreibt (Manuel, 2026-10-05: an seiner
# Drehmaschine drehte C andersherum, die Bahn kam gespiegelt heraus – „ich möchte, dass generell
# solche Fehler nicht vorhanden sind … du musst schauen, ob die Postprozessoren das richtig
# machen“). Nach DIN 66217 beschreibt +A, +B, +C, wie sich das Werkzeug gegenüber dem Werkstück
# dreht: rechtsherum um +X, +Y, +Z. Eine Achse im Kopf dreht das Werkzeug so, eine im Tisch das
# Werkstück andersherum. Unabhängig vom Modell nachgerechnet: An den drei 5-Achs-Beispielen
# schreibt „Programm schreiben“ (3+2 ohne Zyklus) für eine Ebene A/B/C; mit ihnen steht die
# Werkzeugachse nach DIN – R_Tisch⁻¹ · R_Kopf · Z, die Achsen vom Bett aus – auf der Normale. Mit
# Schwenkzyklus nimmt die Vorzugsrichtung (CYCLE800 _DIR) die geschriebene Stellung. Ohne den
# Haken „dreht nach DIN 66217“ zählt die Achse wie ihr Gelenk. Die Drehmaschine: C umgekehrt.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Path

from camaddon import beispielmaschine as bm
from camaddon import maschine as m
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import sprache
from camaddon import verfahren as vf
from camaddon.kette import LINEAR

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")
UM = {"A": V(1, 0, 0), "B": V(0, 1, 0), "C": V(0, 0, 1)}


def din_achse(nc, kopf, tisch):
    """Die Werkzeugachse gegenüber dem Werkstück nach DIN 66217 bei den Programmwerten `nc`:
    `kopf`, `tisch` die Buchstaben vom Bett aus."""
    r_kopf = FreeCAD.Rotation()
    for b in kopf:
        r_kopf = r_kopf.multiply(FreeCAD.Rotation(UM[b], nc[b]))
    r_tisch = FreeCAD.Rotation()
    for b in tisch:
        r_tisch = r_tisch.multiply(FreeCAD.Rotation(UM[b], -nc[b]))
    return r_tisch.inverted().multVec(r_kopf.multVec(V(0, 0, 1)))


def rundachsen_im_programm(zeilen):
    """{Buchstabe: Wert} aus dem ersten Satz, der die Rundachsen fährt."""
    zeile = next(z for z in zeilen if z.startswith("G0 ") and any(f" {b}" in z for b in "ABC"))
    return {w[0]: float(w[1:]) for w in zeile.split()[1:] if w[0] in "ABC"}


NORMALEN = [V(1, 0, 1).normalize(), V(0, 1, 1).normalize(), V(-1, -1, 2).normalize()]
for bauplan in (bm.fuenfachs_tisch_tisch, bm.fuenfachs_kopf_tisch, bm.fuenfachs_kopf_kopf):
    name = bauplan.__name__
    asm, ma = bauplan()
    p = rw.Pruefung(asm, ma)
    maschine = sw.Maschine(p, p.werkzeugaufnahme(1), 60.0, V())
    info = pp.maschineninfo_dokument(asm.Document)
    rollen, _meldungen = m.rollen(p.kette, ma)
    kopf, tisch = [], []
    for achse in p.kette.achsen:  # vom Bett nach außen
        b = p.programmbuchstabe(achse)
        if achse.art == LINEAR or b not in UM:
            continue
        (kopf if rollen.get(achse.gelenk) == m.KOPF else tisch).append(b)
    print(ascii(f"{name}: Kopf {kopf}, Tisch {tisch}, umgekehrt {sorted(info.umgekehrt)}"))
    pruefe(info.umgekehrt == set(tisch), f"{name}: umgekehrt {info.umgekehrt}, Tisch {tisch}")
    for normale in NORMALEN:
        rund = maschine.loese(normale)[0]
        schwenkung = sw.Schwenkung(sw.ebene(normale, V()), rund, maschine.abbildung(rund))
        abschnitt = pp.Abschnitt(
            "Ebene",
            1,
            1000.0,
            False,
            befehle=[Path.Command("G0", {"X": 0.0, "Y": 0.0, "Z": 10.0})],
            schwenkung=schwenkung,
        )
        zeilen = pp.programm([abschnitt], pp.steuerung("linuxcnc"), info, "E").zeilen
        nc = rundachsen_im_programm(zeilen)
        achse = din_achse(nc, kopf, tisch)
        pruefe(
            (achse - normale).Length < 1e-4,  # die Winkel stehen auf 0,001° gerundet
            f"{name}: {nc} gibt nach DIN {achse} statt {normale}",
        )
    # CYCLE800 _DIR: die geschriebene Stellung, gezählt wie an der Steuerung.
    n45 = NORMALEN[0]
    rund = maschine.loese(n45)[0]
    bezug = sw.siemens_reihenfolge(maschine)[0].buchstabe
    richtung = sw.zyklus_richtung(maschine, n45, rund, 1)
    schwenkung = sw.Schwenkung(
        sw.ebene(n45, V()), rund, None, richtung=richtung, richtung_achse=bezug
    )
    abschnitt = pp.Abschnitt("Ebene", 1, 1000.0, False, schwenkung=schwenkung)
    zeilen = pp.programm([abschnitt], pp.steuerung("siemens"), info, "E").zeilen
    zyklus = next(z for z in zeilen if z.startswith("CYCLE800(1"))
    geschrieben = int(zyklus.split(",")[13])
    andere = [r for r in maschine.loese(n45) if any(abs(r[k] - rund[k]) > 1e-3 for k in r)]
    if andere:
        umgekehrt = -1 if bezug in info.umgekehrt else 1
        hier, dort = umgekehrt * rund[bezug], umgekehrt * andere[0][bezug]
        pruefe(
            geschrieben == (-1 if hier < dort else 1),
            f"{name}: _DIR {geschrieben} für {bezug} {hier} (die andere {dort})",
        )
    # Ohne den Haken „dreht nach DIN 66217“: die Achse zählt wie ihr Gelenk.
    if tisch:
        ba = next(
            b
            for b in m.betriebsarten(ma)
            if b.Art == m.ART_POSITIONIEREN and m.programmname(b).upper() == tisch[0]
        )
        ba.NachDin = False
        pruefe(
            tisch[0] not in pp.maschineninfo_dokument(asm.Document).umgekehrt,
            f"{name}: {tisch[0]} ohne Haken noch umgekehrt",
        )
        ba.NachDin = True
    FreeCAD.closeDocument(asm.Document.Name)

# Die Drehmaschine: C dreht das Werkstück – im Programm umgekehrt (C von vorn im Uhrzeigersinn).
asm, ma = bm.drehmaschine()
info = pp.maschineninfo_dokument(asm.Document)
pruefe(info.umgekehrt == {"C"} and info.nach_din == {"C": True}, f"Drehmaschine: {info}")
c1 = next(a for a in vf.Verfahren(asm).kette.achsen if vf.namen(ma, a) == "C1")
pruefe(vf.im_programm_umgekehrt(c1), "Drehmaschine: C1 nicht umgekehrt")
FreeCAD.closeDocument(asm.Document.Name)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
