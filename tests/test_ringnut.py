# Prüft „Ringnut fräsen“ (ringnut_bahn, ringnut; Spezifikation Strategien 13.8) an einer Platte
# 90 × 90 × 30 wie beispiele/ringnut_lagersitz.FCStd: Lagersitz Ø 62 × 20 tief mit der
# Sicherungsringnut Ø 65 × 2,15 (Oberkante 4 mm unter der Oberfläche), darunter Ø 50 durch; dazu
# eine Bohrung Ø 20 (durch) mit O-Ring-Nut Ø 24 × 3. Erkannt (auch ein geteilter Zylinder wie aus
# einem STEP, die Nut am Grund, durchgehend; eine Nase im Weg: nicht angeboten), keine andere
# Strategie nimmt die Nutflächen; das Werkzeug (zu groß, Hals zu dick, Scheibe zu breit, Hals zu
# kurz – je der Grund; der größte, der passt; ohne passenden der Vorschlag); die Bahn (Gleichlauf
# G3, tangential an und ab, Stufen und Kreis auf Maß, die breite Nut in zwei Höhen, zwei Nuten in
# einer Bohrung ohne Herausfahren, Vorschub der Mitte); unabhängig nachgerechnet am Teil
# (OpenCascade: nirgends ins fertige Teil; Dreiecksnetz: Abstand Hals – Rand; die Nut auf Maß,
# Rest ≤ 0,01 mm); Operation angelegt, gerechnet, geändert, gespeichert, geladen; Materialstand
# unverändert; Programm mit Vollkreisen (LinuxCNC). Ohne Oberfläche, etwa 1 min.
import math
import os
import sys
import tempfile
from dataclasses import replace
from types import SimpleNamespace

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import numpy as np
import Part

from camaddon import bahn as bn
from camaddon import bohrung_bahn as bb
from camaddon import kollision as kl
from camaddon import netzabstand as na
from camaddon import reichweite as rw
from camaddon import ringnut as rnop
from camaddon import ringnut_bahn as rn
from camaddon import sprache
from camaddon import werkzeuge as wz
from camaddon import zugang as zg

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


V = FreeCAD.Vector
sprache.setze_sprache("de")


def zyl(r, h, z0, m=30.0):
    return Part.makeCylinder(r, h, V(m, m, z0))


def platte():
    teil = Part.makeBox(90, 90, 30)
    teil = teil.cut(Part.makeCylinder(31.0, 20.0, V(35, 35, 10)))  # Lagersitz Ø 62, 20 tief
    teil = teil.cut(Part.makeCylinder(25.0, 10.0, V(35, 35, 0)))  # Durchgang Ø 50
    teil = teil.cut(Part.makeCylinder(32.5, 2.15, V(35, 35, 26.0 - 2.15)))  # Nut Ø 65 × 2,15
    teil = teil.cut(Part.makeCylinder(10.0, 30.0, V(72, 72, 0)))  # Bohrung Ø 20, durch
    teil = teil.cut(Part.makeCylinder(12.0, 3.0, V(72, 72, 22.0 - 3.0)))  # O-Ring-Nut Ø 24 × 3
    return teil.removeSplitter()


def nut_mit(form, radius):
    return next(n for n in rn.alle_ringnuten(form) if abs(n.radius - radius) < 1e-6)


teil = platte()
# --- Erkennen -------------------------------------------------------------------------------------
pruefe(len(rn.ringnuten(teil)) == 2, f"Ringnuten: {[n.name for n in rn.ringnuten(teil)]}")
lager, oring = nut_mit(teil, 32.5), nut_mit(teil, 12.0)
pruefe(
    abs(lager.z_unten - 23.85) < 1e-6 and abs(lager.z_oben - 26.0) < 1e-6,
    f"Lagernut: z {lager.z_unten} … {lager.z_oben}",
)
pruefe(abs(lager.r_zugang - 31.0) < 1e-6 and abs(lager.tiefe - 1.5) < 1e-6, f"Zugang {lager}")
pruefe(abs(lager.z_kante - 30.0) < 1e-6 and lager.unten == rn.DURCH, f"Kante, unten: {lager}")
pruefe(len(lager.ringe) == 2 and len(lager.flaechen) == 3, f"Flächen: {lager.flaechen}")
pruefe(oring.unten == rn.DURCH and abs(oring.breite - 3.0) < 1e-6, f"O-Ring-Nut: {oring}")
pruefe(
    lager.text() in ("Ø 65 × 2,15, 1,5 tief", "Ø 65 × 2.15, 1.5 tief"), f"Text: {lager.text()}"
)  # das Dezimalzeichen, wie eingestellt
bohrungen = {b.name for b in bb.bohrungen(teil)}
pruefe(
    not (bohrungen & {lager.name, oring.name}),
    f"„Bohrung fräsen“ nimmt die Nut: {sorted(bohrungen)}",
)
pruefe(
    all(bb.bohrung_ueber_boden(teil, f) is None for f in oring.ringe),
    "der Boden der O-Ring-Nut meint eine Bohrung",
)
# Keine andere Strategie des Assistenten nimmt eine Nutfläche; „Ringnut fräsen“ jede.
from camaddon import gui_bearbeitung as ba  # noqa: E402

for klasse in ba.STRATEGIEN:
    s = klasse()
    for f in lager.flaechen + oring.flaechen:
        if s.passt(teil, f) != (klasse is ba._Ringnut):
            fehler.append(f"{klasse.__name__}.passt({f}) = {s.passt(teil, f)}")
pruefe(
    ba.STRATEGIEN.index(ba._Ringnut) == ba.STRATEGIEN.index(ba._Reiben) + 1
    and ba.SCHRUPPEN_ZUERST["ringnut"] == 2,
    "Reihenfolge: Ringnut nach dem Reiben, im Abschnitt Schlichten",
)
pruefe(
    ba._Ringnut().flaechen_fuer(teil, list(lager.ringe)) == [lager.name],
    "eine Ringfläche meint die Nut",
)
# Von oben erreichbar (zugang): die Nutflächen in der Richtung von oben, nicht „unerreichbar“.
z = zg.ohne_schwenken(zg.zugang(teil, spannflaeche=zg.spannflaeche_unten(teil)))
oben = set(z.richtungen[0].flaechen) if z.richtungen else set()
pruefe(
    set(lager.flaechen + oring.flaechen) <= oben and not set(z.unerreichbar) & oben,
    f"Zugang: unerreichbar {sorted(set(z.unerreichbar) & set(lager.flaechen + oring.flaechen))}",
)

# Geteilt wie aus einem STEP: jede Wand aus zwei Halbzylindern.
geteilt = Part.makeBox(60, 60, 20)
for radius, h, z0 in ((15.0, 20.0, 0.0), (17.0, 2.0, 12.0)):
    for winkel in (0.0, 180.0):
        halb = Part.makeCylinder(radius, h, V(30, 30, z0), V(0, 0, 1), 180.0)
        halb.rotate(V(30, 30, 0), V(0, 0, 1), winkel)
        geteilt = geteilt.cut(halb)
nuten = rn.ringnuten(geteilt)
pruefe(
    len(nuten) == 1 and len(nuten[0].zylinder) == 2 and abs(nuten[0].radius - 17.0) < 1e-6,
    f"geteilt: {[(n.zylinder, n.radius) for n in nuten]}",
)
# Die Nut am Grund einer Sackbohrung (Freistich): unten der Boden.
grund = Part.makeBox(40, 40, 20).cut(Part.makeCylinder(10.0, 12.0, V(20, 20, 8)))
grund = grund.cut(Part.makeCylinder(12.0, 2.0, V(20, 20, 8))).removeSplitter()
nuten = rn.ringnuten(grund)
pruefe(
    len(nuten) == 1 and nuten[0].unten == rn.GRUND and abs(nuten[0].z_boden - 8.0) < 1e-6,
    f"am Grund: {[(n.unten, n.z_boden) for n in nuten]}",
)
pruefe(len(nuten[0].ringe) == 2 if nuten else False, "am Grund: Ringfläche und Boden")
# Eine Nase in der Bohrung über der Nut: erkannt, aber nicht angeboten – mit Grund.
nase = Part.makeBox(60, 60, 20).cut(Part.makeCylinder(15.0, 20.0, V(30, 30, 0)))
nase = nase.cut(Part.makeCylinder(17.0, 2.0, V(30, 30, 10)))
nase = nase.fuse(Part.makeBox(3.0, 4.0, 4.0, V(30 + 13.0, 28.0, 14.0))).removeSplitter()
gesperrt = [n for n in rn.alle_ringnuten(nase) if abs(n.radius - 17.0) < 1e-6]
pruefe(
    not rn.ringnuten(nase) and len(gesperrt) == 1 and "Nase" in gesperrt[0].grund,
    f"Nase: {[(n.name, n.grund) for n in gesperrt]}",
)
# Nach unten offen (Gegenbohrung, Senkung, Lagersitz von unten): keine Ringnut – die breite Wand
# bleibt „unerreichbar“ (Umspannen) und eine Bohrung für „Bohrung fräsen“, wie bis 0.371
# (Zweifler 14.11.: dort hieß sie Ringnut, die Unterseite des Teils ihre Ringfläche).
for name_, t, r_gross in (
    ("Gegenbohrung", Part.makeBox(60, 60, 30).cut(zyl(5, 30, 0)).cut(zyl(10, 12, 0)), 10.0),
    ("Senkung", Part.makeBox(40, 40, 30).cut(zyl(5, 30, 0, 20)).cut(zyl(10, 20, 0, 20)), 10.0),
    ("Lagersitz", Part.makeBox(90, 90, 30).cut(zyl(25, 30, 0, 45)).cut(zyl(31, 20, 0, 45)), 31.0),
):
    t = t.removeSplitter()
    breit = next(
        f"Face{i + 1}"
        for i, f in enumerate(t.Faces)
        if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - r_gross) < 1e-6
    )
    z_ = zg.zugang(t, spannflaeche=zg.spannflaeche_unten(t))
    pruefe(
        not rn.alle_ringnuten(t)
        and breit in z_.unerreichbar
        and breit in {b.name for b in bb.bohrungen(t)},
        f"{name_} von unten: {[n.flaechen for n in rn.alle_ringnuten(t)]}, "
        f"{sorted(z_.unerreichbar)}",
    )
# Eine Querbohrung Ø 6 kreuzt die Nut: ihre Wand in zwei Stücken, in der Lücke ist Luft – eine
# Ringnut, und keine Strategie von oben bekommt ihre Flächen.
quer = Part.makeBox(60, 60, 30).cut(zyl(10, 30, 0)).cut(zyl(12, 2, 22))
quer = quer.cut(Part.makeCylinder(3.0, 60.0, V(0, 30, 23), V(1, 0, 0))).removeSplitter()
quernut = rn.ringnuten(quer)
pruefe(
    len(quernut) == 1 and len(quernut[0].zylinder) == 2 and len(quernut[0].ringe) == 4,
    f"Querbohrung: {[(n.zylinder, n.ringe) for n in quernut]}",
)
for klasse in ba.STRATEGIEN:
    for f in quernut[0].flaechen if quernut else ():
        if klasse().passt(quer, f) != (klasse is ba._Ringnut):
            fehler.append(f"Querbohrung: {klasse.__name__}.passt({f})")
# Ein Steg steht im Ring der Nut: keine Ringnut.
steg = Part.makeBox(60, 60, 30).cut(zyl(10, 30, 0)).cut(zyl(12, 2, 22))
steg = steg.fuse(Part.makeBox(3, 1, 2, V(39.5, 29.5, 22))).removeSplitter()
pruefe(not rn.ringnuten(steg), f"Steg im Ring: {[n.name for n in rn.ringnuten(steg)]}")
# Die Ringflächen liegen ganz im Kreis R – nie eine Außenfläche des Teils.
for t in (teil, grund, quer):
    for n in rn.alle_ringnuten(t):
        for f in n.ringe:
            bb_ = t.Faces[int(f[4:]) - 1].BoundBox
            if max(bb_.XMax - n.mitte[0], n.mitte[0] - bb_.XMin) > n.radius + 1e-3:
                fehler.append(f"{f} ist keine Ringfläche von {n.name}")
# Am Grund: „Bohrung fräsen“ nimmt die Wand darüber als Sackbohrung bis auf den Boden der Nut –
# sonst bliebe der Kern bis z 9,5 stehen, und die Ringnut wartete auf die Bohrung (Sackgasse).
im_grund = bb.bohrungen(grund)
pruefe(
    len(im_grund) == 1 and not im_grund[0].durch and abs(im_grund[0].z_unten - 8.0) < 1e-6,
    f"am Grund, die Bohrung: {[(b.name, b.durch, b.z_unten) for b in im_grund]}",
)
print("Erkennen ok")


# --- Das Werkzeug ---------------------------------------------------------------------------------
def nutenfraeser(d, b, hals, hals_l, schaft=None, kennung=None, gesamt=80.0):
    w = wz.Werkzeug(
        nummer=5,
        art=wz.NUTENFRAESER,
        durchmesser=d,
        schneiden=6,
        schneidenbreite=b,
        hals_d=hals,
        hals_laenge=hals_l,
        schaft=schaft or hals,
        gesamtlaenge=gesamt,
        schneidstoff=wz.VHM,
    )
    if kennung:
        w.kennung = kennung
    return w


ueber = {n.name: rn.ueber_der_kante(teil, n) for n in (lager, oring)}
for w, wort, was in (
    (nutenfraeser(62.0, 2.0, 20.0, 10.0), "passt nicht durch", "zu groß"),
    (nutenfraeser(58.0, 2.0, 56.0, 10.0), "zu dick", "Hals zu dick"),
    (nutenfraeser(40.0, 3.0, 20.0, 10.0), "breiter", "Scheibe zu breit"),
    (nutenfraeser(40.0, 2.15, 20.0, 1.0, schaft=40.0), "zu kurz", "Hals zu kurz"),
    (wz.standardwerkzeug(), "Nutenfräser", "Schaftfräser"),
):
    grund_ = rn.werkzeug_pruefen(lager, w, ueber=ueber[lager.name])
    pruefe(wort in grund_, f"{was}: „{grund_}“")
klein = nutenfraeser(19.0, 2.15, 9.5, 11.0, schaft=10.0, kennung="klein")
gross = nutenfraeser(40.0, 2.15, 20.0, 10.0, schaft=20.0, kennung="gross")
pruefe(not rn.werkzeug_pruefen(lager, klein, ueber=ueber[lager.name]), "Ø 19 in der Lagernut")
pruefe(not rn.werkzeug_pruefen(oring, klein, ueber=ueber[oring.name]), "Ø 19 in der O-Ring-Nut")
wahl, gruende = rn.waehlen([lager], [klein, gross], ueber_von=lambda n: ueber[n.name])
pruefe(wahl is gross, f"eine Nut: der größte, der passt – {wahl and wahl.durchmesser}")
wahl, gruende = rn.waehlen([lager, oring], [klein, gross], ueber_von=lambda n: ueber[n.name])
pruefe(
    wahl is klein and "passt nicht durch" in gruende.get("gross", ""),
    f"beide Nuten: {wahl and wahl.durchmesser}, Gründe {gruende}",
)
# Kein passendes: womit es ginge – und ein Vorschlag, der passt; ein Katalog mit einem passenden.
vorschlag = rn.vorschlag_werkzeug([lager, oring], lambda n: ueber[n.name])
grenzen = rn.grenzen([lager, oring], lambda n: ueber[n.name])
pruefe(
    vorschlag is not None
    and vorschlag.durchmesser == 19.0
    and abs(vorschlag.schneidenbreite - 2.15) < 1e-9
    and all(not rn.werkzeug_pruefen(n, vorschlag, ueber=ueber[n.name]) for n in (lager, oring)),
    f"Vorschlag: {vorschlag}",
)
pruefe(
    grenzen is not None and abs(grenzen.d - 19.4) < 1e-9 and abs(grenzen.b - 2.15) < 1e-9,
    f"Grenzen: {grenzen}",
)
katalog = [
    SimpleNamespace(
        art=wz.NUTENFRAESER, durchmesser=d, schneidenbreite=b, hals_d=h, hals_laenge=0.0,
        schaft=s, gesamtlaenge=60.0, hersteller="X", name=f"T {d}", artikel=f"{d}", link="",
    )  # fmt: skip
    for d, b, h, s in ((21.0, 9.0, 10.0, 12.0), (52.0, 2.0, 22.0, 22.0), (18.0, 2.0, 8.0, 12.0))
]
aus = rn.aus_dem_katalog([lager], katalog, lambda n: ueber[n.name])
pruefe([w.durchmesser for w in aus] == [52.0, 18.0], f"Katalog: {[w.durchmesser for w in aus]}")
# Nur eingetragene Maße: Ein Keyway aus FreeCAD bringt seine Halslänge mit (NeckHeight); ohne
# sie gibt es keinen Hals, der Schaft steht gleich über der Scheibe – geschätzt (0,25 · D = 4,75)
# hieß Ø 19 mit Hals Ø 6 × 3 und Schaft Ø 16 passend, der Schaft lag 1 mm im Rand.
from camaddon import werkzeuge_aus_cam as wac  # noqa: E402

keyteil = Part.makeBox(60, 60, 30).cut(zyl(10, 30, 0)).cut(zyl(13, 2, 24)).removeSplitter()
keynut = rn.ringnuten(keyteil)[0]
bit = SimpleNamespace(
    ShapeType="keyway", Diameter=19.0, LowerCuttingHeight=2.0, CuttingEdgeHeight=2.0,
    NeckDiameter=6.0, NeckHeight=3.0, ShankDiameter=16.0, Length=50.0, Flutes=4, Material="HSS",
)  # fmt: skip
keyway = wac.werkzeug_aus(SimpleNamespace(obj=bit, label="Keyway"), 3)
pruefe(
    (keyway.hals_d, keyway.hals_laenge, keyway.schaft, keyway.schneidenbreite) == (6, 3, 16, 2),
    f"Keyway gelesen: {keyway}",
)
ueber_key = rn.ueber_der_kante(keyteil, keynut)
# Eigene Rechnung: e = 13 − 9,5 = 3,5; der Schaft Ø 16 beginnt 2 + 3 über z 24, also bei 29 – unter
# der Kante 30, und reicht bis 3,5 + 8 = 11,5 > 10: er stößt an.
pruefe("zu kurz" in rn.werkzeug_pruefen(keynut, keyway, ueber=ueber_key), "Keyway: passt")
ohne_laenge = nutenfraeser(19.0, 2.0, 6.0, 0.0, schaft=16.0)
pruefe(
    "Halslänge" in rn.werkzeug_pruefen(keynut, ohne_laenge, ueber=ueber_key),
    f"ohne Halslänge: „{rn.werkzeug_pruefen(keynut, ohne_laenge, ueber=ueber_key)}“",
)
pruefe(
    "Breite" in rn.werkzeug_pruefen(lager, nutenfraeser(19.0, 0.0, 9.5, 11.0, schaft=10.0)),
    "ohne Breite der Scheibe angenommen",
)
pruefe(
    grenzen is not None and "bei Ø 19" in grenzen.text() and "Schaft Ø 10" in grenzen.text(),
    f"Grenzen: Hals zum genannten Ø – {grenzen and grenzen.text()}",
)
print("Werkzeug ok")

# --- Die Bahn -------------------------------------------------------------------------------------
VF = 200.0  # mm/min an der Schneide


def werte(werkzeug, sicher=35.0, **weiter):
    return rn.Ringnutwerte(werkzeug=werkzeug, zustellung=1.9, sicher=sicher, vorschub=VF, **weiter)


bahn = rn.planen(werte(klein), [lager, oring], teil)
pruefe(bahn.nuten == 2 and not bahn.nicht_passend, f"{bahn.nuten} Nuten, {bahn.nicht_passend}")
pruefe(bahn.reserve >= -1e-6, f"eigene Prüfung: {bahn.reserve}")
boegen = [(a, b) for a, b in zip(bahn.punkte, bahn.punkte[1:], strict=False) if b.bogen]
pruefe(
    boegen and not any(b.bogen[2] for _a, b in boegen) and all(not b.eilgang for _a, b in boegen),
    "Gleichlauf: nicht alle Bögen G3",
)
gegen = rn.planen(werte(klein, gleichlauf=False), [lager, oring], teil)
pruefe(all(b.bogen[2] for b in gegen.punkte if b.bogen), "Gegenlauf: nicht alle G2")


def an_achse(p, nut):
    return math.hypot(p.x - nut.mitte[0], p.y - nut.mitte[1])


def parallel(a, b):
    """Gleiche Richtung zweier ebener Vektoren."""
    la, lb = math.hypot(*a), math.hypot(*b)
    return (
        la > 1e-9
        and lb > 1e-9
        and abs(a[0] * b[1] - a[1] * b[0]) < 1e-6 * la * lb
        and (a[0] * b[0] + a[1] * b[1] > 0)
    )


for j in bahn.je_nut:
    nut = j["nut"]
    stueck = bahn.punkte[j["von"] : j["bis"]]
    eigene = [(a, b) for a, b in zip(stueck, stueck[1:], strict=False) if b.bogen]
    hinein = [(a, b) for a, b in eigene if an_achse(a, nut) < 1e-6]
    heraus = [(a, b) for a, b in eigene if an_achse(b, nut) < 1e-6]
    pruefe(
        hinein
        and all(
            parallel((b.x - b.bogen[0], b.y - b.bogen[1]), (b.x - nut.mitte[0], b.y - nut.mitte[1]))
            for _a, b in hinein
        ),
        f"{nut.name}: nicht tangential hinein",
    )
    pruefe(
        heraus
        and len(heraus) == len(hinein)
        and all(
            parallel((a.x - b.bogen[0], a.y - b.bogen[1]), (a.x - nut.mitte[0], a.y - nut.mitte[1]))
            for a, b in heraus
        ),
        f"{nut.name}: nicht tangential heraus",
    )
    kreise = {
        round(an_achse(b, nut), 6)
        for _a, b in eigene
        if math.hypot(b.bogen[0] - nut.mitte[0], b.bogen[1] - nut.mitte[1]) < 1e-6
    }
    soll = {round(nut.radius - 0.1 - 9.5, 6), round(nut.radius - 9.5, 6)}  # eine Stufe, auf Maß
    pruefe(kreise == soll, f"{nut.name}: Kreise bei e {sorted(kreise)} statt {sorted(soll)}")
# Vorschub der Mitte auf dem Kreis: e ÷ (e + D/2) – an der Schneide gilt der des Einsatzes.
kreis = next(
    b
    for _a, b in boegen
    if abs(an_achse(b, lager) - 23.0) < 1e-6
    and math.hypot(b.bogen[0] - lager.mitte[0], b.bogen[1] - lager.mitte[1]) < 1e-6
)
pruefe(abs(kreis.anteil - 23.0 / 32.5) < 1e-9, f"Vorschub auf dem Kreis: {kreis.anteil}")
# Die breite O-Ring-Nut in zwei Höhen, die sich überlappen; die Lagernut in einer.
je = {j["name"]: j for j in bahn.je_nut}
pruefe(je[oring.name]["hoehen"] == 2 and je[lager.name]["hoehen"] == 1, f"Höhen: {je}")
hoehen_oring = sorted({round(b.z, 6) for _a, b in boegen if an_achse(b, oring) < 3.0})
pruefe(hoehen_oring == [19.0, 19.85], f"Höhen der O-Ring-Nut: {hoehen_oring}")
# Eilgänge unter der Oberkante nur auf der Achse; Anfang und Ende oben.
for p in bahn.punkte:
    neben = min(an_achse(p, lager), an_achse(p, oring)) > 1e-6
    if p.eilgang and p.z < 30.0 - 1e-6 and neben:
        fehler.append(f"Eilgang neben der Achse bei z {p.z}")
pruefe(bahn.punkte[0].z == 35.0 and bahn.punkte[-1].z == 35.0, "Anfang und Ende oben")
pruefe(abs(bahn.zeit - bn.zeit(bahn.punkte, VF)) < 1e-9 and bahn.zeit > 0, "Zeit")
# Steht in der Bohrung noch Material (ein volles Rohteil), geht es nicht: erst die Bohrung fräsen.
from camaddon import materialstand as mst  # noqa: E402
from camaddon import restmaterial as rm  # noqa: E402

q_voll = rm.Quader(0.0, 90.0, 0.0, 90.0, 0.0, 31.0, 0.5)
try:
    rn.planen(werte(klein), [lager], teil, mst.Materialstand(q_voll, q_voll.h.copy()))
except ValueError as grund_:
    pruefe("erst die Bohrung" in str(grund_), f"volles Rohteil: {grund_}")
else:
    fehler.append("volles Rohteil: keine Fehlermeldung")
# Die eigene Prüfung schlägt an, wenn das Werkzeug dicker ist, als die Bahn denkt.
dick = nutenfraeser(19.0, 2.15, 18.0, 11.0, schaft=18.0)
reserve, _hals = rn.pruefen(bahn, rn.profil(dick), ueber)
pruefe(reserve < -1.0, f"Prüfung mit dickem Hals: {reserve}")
# Zwei Nuten in einer Bohrung: von oben nach unten, ohne ganz herauszufahren.
zwei = Part.makeBox(60, 60, 40).cut(Part.makeCylinder(15.0, 40.0, V(30, 30, 0)))
for z0 in (30.0, 20.0):
    zwei = zwei.cut(Part.makeCylinder(17.0, 2.0, V(30, 30, z0)))
zwei = zwei.removeSplitter()
beide = rn.ringnuten(zwei)
zb = rn.planen(werte(nutenfraeser(25.0, 2.0, 12.0, 25.0), sicher=45.0), beide, zwei)
oben_punkte = [i for i, p in enumerate(zb.punkte) if p.z >= 45.0 - 1e-6]
pruefe(
    zb.nuten == 2 and oben_punkte == [0, len(zb.punkte) - 1],
    f"zwei in einer Bohrung: {zb.nuten}, oben bei {oben_punkte}",
)
pruefe([j["nut"].z_oben for j in zb.je_nut] == [32.0, 22.0], "zwei: nicht von oben nach unten")


# Mittig hinab (Zweifler 14.11.): im Eilgang nur, wenn der Materialstand die Bohrung offen zeigt
# und rundum mindestens der Warnabstand von „Kollision prüfen“ bleibt; der Eilgang endet
# Sicherheitsabstand über der Nuthöhe, den Rest fährt der Vorschub.
def stand_mit(hoehe_innen, r_innen, z_aussen=30.0, m=30.0, groesse=60.0):
    q = rm.Quader(0.0, groesse, 0.0, groesse, 0.0, z_aussen, 0.5)
    gx, gy = np.meshgrid(q.x, q.y, indexing="ij")
    q.h[np.hypot(gx - m, gy - m) < r_innen] = hoehe_innen
    return mst.Materialstand(q, q.h.copy())


def eilgaenge_unter(b_, z):
    return [(p.x, p.y, p.z) for p in b_.punkte if p.eilgang and p.z < z - 1e-6]


pruefe(rn.EILGANG_LUFT == kl.WARNABSTAND, "Luft im Eilgang ≠ Warnabstand der Kollision")
ref = Part.makeBox(60, 60, 30).cut(zyl(10, 30, 0)).cut(zyl(12, 2, 22)).removeSplitter()
refnut = rn.ringnuten(ref)[0]
eng = nutenfraeser(19.4, 2.0, 9.0, 9.0, schaft=10.0)  # 0,3 mm Luft in Ø 20
weit = nutenfraeser(16.0, 2.0, 8.0, 9.0, schaft=10.0)  # 2 mm Luft
offen = stand_mit(-1.0, 10.0)
sicherheit = rn.Ringnutwerte(None, 0.0, 0.0).sicherheit
try:  # 0,5 mm Wandaufmaß: die Bohrung ist erst bis r 9,5 offen – die Scheibe Ø 19,4 läge darin
    rn.planen(werte(eng), [refnut], ref, stand_mit(-math.inf, 9.5))
except ValueError as grund_:
    pruefe("erst die Bohrung" in str(grund_), f"Wandaufmaß: {grund_}")
else:
    fehler.append("Wandaufmaß 0,5: im Eilgang in die Wand")
for was, b_ in (
    ("ohne Materialstand", rn.planen(werte(weit), [refnut], ref, None)),
    ("0,3 mm Luft", rn.planen(werte(eng), [refnut], ref, offen)),
):
    pruefe(not eilgaenge_unter(b_, 30.0 + sicherheit), f"{was}: Eilgang {eilgaenge_unter(b_, 32)}")
b_ = rn.planen(werte(weit), [refnut], ref, offen)
pruefe(
    min(p.z for p in b_.punkte if p.eilgang) == 22.0 + sicherheit,
    f"2 mm Luft: Eilgang bis z {min(p.z for p in b_.punkte if p.eilgang)}",
)
# Am Grund: nie im Eilgang auf den Boden (z 8); mit dem Stand nach „Bohrung fräsen“ bis auf den
# Boden geht es, mit dem Kern bis z 9,5 (bis 0.371.2 so gefräst) „erst die Bohrung“.
gnut = rn.ringnuten(grund)[0]
gw = rn.Ringnutwerte(werkzeug=weit, zustellung=1.6, sicher=25.0, vorschub=VF)
b_ = rn.planen(gw, [gnut], grund, stand_mit(8.0, 10.0, 20.0, 20.0, 40.0))
pruefe(
    b_.nuten == 1 and not eilgaenge_unter(b_, 8.0 + sicherheit),
    f"am Grund: Eilgang {eilgaenge_unter(b_, 8.0 + sicherheit)}",
)
try:
    rn.planen(gw, [gnut], grund, stand_mit(9.5, 10.0, 20.0, 20.0, 40.0))
except ValueError as grund_:
    pruefe("erst die Bohrung" in str(grund_), f"am Grund, Kern stehend: {grund_}")
else:
    fehler.append("am Grund: Kern bis 9,5 nicht bemerkt")
qbahn = rn.planen(werte(weit), quernut, quer, offen)
pruefe(qbahn.nuten == 1 and qbahn.reserve >= -1e-6, f"Querbohrung: {qbahn.reserve}")
print(f"Bahn ok: {bahn.kreise} Kreise, {bahn.zeit:.2f} min, Hals – Rand {bahn.hals_rand:.2f}")


# --- Unabhängig nachgerechnet: OpenCascade und das Dreiecksnetz -------------------------------
# Nichts aus ringnut_bahn, kollision oder reichweite: das Werkzeug aus den eingetragenen Maßen
# (Scheibe, Hals, Schaft als Zylinder), die Bahn aus dem Programm (G0/G1/G2/G3, Bögen aus I, J),
# Vorschub gegen das fertige Teil (Scheibe) bzw. das Teil vor der Nut (Hals, Schaft), Eilgang
# gegen das Teil vor der Nut.
def programm_stellen(befehle, lin=1.0, grad=15.0):
    """[(x, y, z, eilgang)] entlang der Befehle – eigene Rechnung aus X, Y, Z, I, J."""
    pos, aus = None, []
    for c in befehle:
        if c.Name not in ("G0", "G1", "G2", "G3"):
            continue
        p = c.Parameters
        if pos is None:
            pos = [math.nan, math.nan, p.get("Z", 0.0)]
            continue
        ziel = [p.get("X", pos[0]), p.get("Y", pos[1]), p.get("Z", pos[2])]
        if math.isnan(pos[0]):
            pos = ziel
            continue
        if c.Name in ("G0", "G1"):
            n = max(1, int(math.ceil(math.dist(pos, ziel) / lin)))
            # Ein Eilgang ab seinem Anfang danach: Dort stand das Werkzeug im Vorschub (am Grund auf
            # dem Boden, bevor es mittig heraus fährt).
            for t in np.linspace(0.0, 1.0, n + 1)[1 if c.Name == "G0" else 0 :]:
                aus.append((*(pos[k] + t * (ziel[k] - pos[k]) for k in range(3)), c.Name == "G0"))
        else:
            cx, cy = pos[0] + p["I"], pos[1] + p["J"]
            r = math.hypot(pos[0] - cx, pos[1] - cy)
            a0 = math.atan2(pos[1] - cy, pos[0] - cx)
            a1 = math.atan2(ziel[1] - cy, ziel[0] - cx)
            weg = (a1 - a0) % (2 * math.pi) if c.Name == "G3" else -((a0 - a1) % (2 * math.pi))
            weg = weg or (2 * math.pi if c.Name == "G3" else -2 * math.pi)
            n = max(2, int(math.ceil(abs(math.degrees(weg)) / grad)))
            for t in np.linspace(0.0, 1.0, n + 1):
                a_ = a0 + t * weg
                aus.append((cx + r * math.cos(a_), cy + r * math.sin(a_), pos[2], False))
        pos = ziel
    return aus


def zylinder_des(w):
    """[(Art, z von, z bis, r)] über der Unterkante der Scheibe, aus den eingetragenen Maßen."""
    b, hl = w.schneidenbreite, w.hals_laenge
    return [
        ("scheibe", 0.0, b, w.durchmesser / 2),
        ("hals", b, b + hl, w.hals_d / 2),
        ("schaft", b + hl, w.gesamtlaenge, w.schaft / 2),
    ]


def vor_der_nut(t, nuten_):
    """Das Teil, wie es vor der Ringnut ist: die Nuten noch voll (Ring r_innen … R)."""
    for n in nuten_:
        ring = zyl(n.radius, n.breite, n.z_unten, 0.0).cut(zyl(n.r_innen, n.breite, n.z_unten, 0.0))
        ring.translate(V(n.mitte[0], n.mitte[1], 0))
        t = t.fuse(ring)
    return t


def nachrechnen(name_, t, nuten_, b_, w, ueber_alles):
    """{Eingriff ins fertige Teil, Eingriff vor der Nut, Eilgang im Teil, Rest, Übermaß} in mm³
    bzw. mm – und prüft sie."""
    befehle_ = bn.befehle(b_.punkte, VF)
    vor = vor_der_nut(t, nuten_)
    stuecke = zylinder_des(w)
    ins_fertige = ins_vor = eilgang = 0.0
    for x, y, zz, eil in programm_stellen(befehle_):
        if zz > ueber_alles:
            continue
        for art, z0, z1, r in stuecke:
            if z1 - z0 <= 1e-9:
                continue
            if eil:
                # Im Eilgang mit 0,2 mm Luft rundum und unten: Berühren zählt (bis 0.371.2 fuhr die
                # Scheibe am Grund im Eilgang auf den Boden – 0 mm³ ohne die Zugabe).
                k = Part.makeCylinder(r + 0.2, z1 - z0 + 0.2, V(x, y, zz + z0 - 0.2))
                eilgang = max(eilgang, vor.common(k).Volume)
                continue
            k = Part.makeCylinder(r, z1 - z0, V(x, y, zz + z0))
            if art == "scheibe":
                ins_fertige = max(ins_fertige, t.common(k).Volume)
            else:
                ins_vor = max(ins_vor, vor.common(k).Volume)
    pruefe(ins_fertige < 1e-4, f"{name_}: Scheibe ins fertige Teil {ins_fertige:.6f} mm³")
    pruefe(ins_vor < 1e-4, f"{name_}: Hals/Schaft ins Teil {ins_vor:.6f} mm³")
    pruefe(eilgang < 1e-6, f"{name_}: Eilgang ins Teil vor der Nut {eilgang:.6f} mm³")
    # Auf Maß: jeder Punkt der Nutflächen liegt in der Hülle der Scheibe (Rest ≤ 0,01 mm), keine
    # Scheibe reicht über R oder die Ringflächen hinaus (Übermaß ≤ 0,01 mm).
    r_s, b_s = w.durchmesser / 2, w.schneidenbreite
    scheiben = np.array([s_[:3] for s_ in programm_stellen(befehle_, 0.2, 1.0) if not s_[3]])
    for n in nuten_:
        punkte_ = []
        for f in n.flaechen:
            knoten, _dreiecke = t.Faces[int(f[4:]) - 1].tessellate(0.01)
            punkte_ += [(q.x, q.y, q.z) for q in knoten]
        q_ = np.array(punkte_)
        e_s = np.hypot(scheiben[:, 0] - n.mitte[0], scheiben[:, 1] - n.mitte[1])
        nah = scheiben[e_s < n.radius]
        rest_mm = 0.0
        for start in range(0, len(q_), 200):
            q = q_[start : start + 200]
            rho = np.hypot(q[:, None, 0] - nah[None, :, 0], q[:, None, 1] - nah[None, :, 1])
            dz = np.maximum(nah[None, :, 2] - q[:, None, 2], q[:, None, 2] - nah[None, :, 2] - b_s)
            d = np.hypot(np.maximum(rho - r_s, 0.0), np.maximum(dz, 0.0)).min(axis=1)
            rest_mm = max(rest_mm, float(d.max()))
        schneidet = scheiben[(e_s < n.radius) & (e_s + r_s > n.r_zugang + 1e-6)]
        aussen = float((np.hypot(schneidet[:, 0] - n.mitte[0], schneidet[:, 1] - n.mitte[1])).max())
        uebermass = max(
            aussen + r_s - n.radius,
            n.z_unten - float(schneidet[:, 2].min()),
            float(schneidet[:, 2].max()) + b_s - n.z_oben,
        )
        pruefe(rest_mm <= 0.01, f"{name_} {n.name}: Rest {rest_mm:.4f} mm")
        pruefe(uebermass <= 0.01, f"{name_} {n.name}: Übermaß {uebermass:.4f} mm")
    print(f"{name_}: ins Teil {max(ins_fertige, ins_vor):.6f} mm³, Eilgang {eilgang:.6f} mm³")


nachrechnen("Platte", teil, [lager, oring], bahn, klein, 34.0)
nachrechnen("Ø 16 offen", ref, [refnut], rn.planen(werte(weit), [refnut], ref, offen), weit, 34.0)
nachrechnen("am Grund", grund, [gnut], rn.planen(gw, [gnut], grund, stand_mit(8.0, 10.0, 20.0,
            20.0, 40.0)), weit, 24.0)  # fmt: skip
nachrechnen("Querbohrung", quer, quernut, qbahn, weit, 34.0)
# Abstand Hals – Rand aus dem Dreiecksnetz des Teils ohne die Nutflächen: Punkte auf dem Hals.
rest = Part.makeCompound(
    [f for i, f in enumerate(teil.Faces) if f"Face{i + 1}" not in lager.flaechen + oring.flaechen]
)
netz = na.Netz(rest, toleranz=0.005, zelle=10.0)
hals_punkte = []
for x, y, zz, _eil in programm_stellen(bn.befehle(bahn.punkte, VF)):
    if zz > 34.0:
        continue
    for w in np.linspace(0, 2 * math.pi, 24, endpoint=False):
        for h in (klein.schneidenbreite + 0.01, klein.schneidenbreite + klein.hals_laenge / 2):
            r = klein.hals_d / 2
            hals_punkte.append((x + r * math.cos(w), y + r * math.sin(w), zz + h))
abstand_hals = float(np.min(netz.abstand(np.array(hals_punkte))))
pruefe(abstand_hals > 0.3 - 0.02, f"Hals – Rand im Netz: {abstand_hals:.3f} mm")
print(f"Netzprüfung ok: Hals – Rand {abstand_hals:.3f} mm")

# --- Kollision: der Kern der Scheibe oben kleiner – nur in „Ringnut fräsen“ ---------------------
masse = rw.masse_des_werkzeugs(klein)
pruefe(not masse.scheibe, "Kern oben: für jeden Nutenfräser, nicht nur die Ringnut")
kapseln = kl.werkzeugkapseln(replace(masse, scheibe=True), 80.0, None)
((k0, k1, _r, _f),) = kapseln[kl.KERN]
((s0, s1, _r, _f),) = kapseln[kl.SCHNEIDE]
pruefe(abs((s1[2] - k1[2]) - kl.EINDRINGEN) < 1e-9, "Kern der Scheibe oben")
((k0, k1, _r, _f),) = kl.werkzeugkapseln(masse, 80.0, None)[kl.KERN]
pruefe(abs(s1[2] - k1[2]) < 1e-9, "Kern oben ohne Ringnut verkleinert")

# --- Die Operation im Job -------------------------------------------------------------------------
import Path.Main.Job as PathJob  # noqa: E402

from camaddon import job_schnittwerte as js  # noqa: E402
from camaddon import postprozessor as pp  # noqa: E402
from camaddon import uebergabe_werkzeuge as ue  # noqa: E402

profil_ordner = os.environ.get("FREECAD_USER_HOME", "")
if not profil_ordner or not FreeCAD.getUserAppDataDir().startswith(profil_ordner):
    raise AssertionError("Kein Testprofil – die Werkzeugverwaltung würde überschrieben.")
from camaddon import werkzeugkiste as wk  # noqa: E402

wk.richtwerte_eintragen(klein)
wk.richtwerte_eintragen(weit)
weit.nummer = 6
schaftfraeser = wz.standardwerkzeug()  # Ø 12, für „Bohrung fräsen“ am Grund
bibliothek = wz.Bibliothek([klein, weit, schaftfraeser])
bibliothek.speichern()
ue.uebergeben(bibliothek)
doc = FreeCAD.newDocument("Ringnut")
doc.UndoMode = 1
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
# Das Rohteil: die Platte mit fertig gefrästen Bohrungen, ohne Nuten, 1 mm Aufmaß oben – die
# Ringnut kommt nach dem Fertigbearbeiten der Bohrung (sonst: „erst die Bohrung fertig fräsen“).
alt = job.Stock
vorgearbeitet = doc.addObject("Part::Feature", "Rohteil")
roh = Part.makeBox(90, 90, 31)
for radius, h, x, z0 in (
    (31.0, 21.0, 35.0, 10.0),
    (25.0, 10.0, 35.0, 0.0),
    (10.0, 31.0, 72.0, 0.0),
):
    roh = roh.cut(Part.makeCylinder(radius, h, V(x, x, z0)))
vorgearbeitet.Shape = roh.removeSplitter()
job.Stock = vorgearbeitet
doc.removeObject(alt.Name)
doc.recompute()
vollnut = next(e for e in klein.einsaetze(wz.ALLE) if e.art == wz.VOLLNUT)
tc = js.controller_ohne_transaktion(doc, job, klein, vollnut)
doc.recompute()
klon = job.Model.Group[0].Shape
im_job = [n.name for n in rn.ringnuten(klon)]
stand_vorher = mst.fuer(job)
op = rnop.lege_an(job, tc, 0.0, flaechen=im_job)
doc.recompute()
pruefe(op.Label == "Ringnut fräsen T5" and rnop.ist_ringnut(op), f"{op.Label}")
pruefe(js.operationsart(op) == "ringnut", f"Art: {js.operationsart(op)}")
pruefe(js.EINSATZ_NACH_OPERATION["ringnut"] == (wz.VOLLNUT,), "Einsatz Vollnut")
pruefe(ba.ist_bearbeitung(op), "ist_bearbeitung")
pruefe((op.Nuten, op.Kreise) == (2, bahn.kreise), f"Operation: {op.Nuten} Nuten, {op.Kreise}")
pruefe(abs(float(op.FinalDepth) - 19.0) < 1e-6, f"Endtiefe {float(op.FinalDepth)}")
befehle = op.Path.Commands
namen = [b.Name for b in befehle]
pruefe(
    "G3" in namen and "G2" not in namen,
    f"Gleichlauf: G3 {namen.count('G3')}, G2 {namen.count('G2')}",
)
pruefe(
    all("I" in b.Parameters and "J" in b.Parameters for b in befehle if b.Name == "G3"),
    "G3 ohne I, J",
)
# Der Materialstand nach der Ringnut ist der davor – von oben nimmt sie nichts weg.
stand_nachher = mst.fuer(job)
pruefe(
    stand_vorher is not None
    and stand_nachher is not None
    and np.array_equal(stand_vorher.quader.h, stand_nachher.quader.h),
    "Materialstand: die Ringnut senkt das Höhenfeld",
)
pruefe(rm._ist_ringnut(job, op.Label), "Abtrag im Quader: nicht als Ringnut erkannt")
# Das Programm: Vollkreise in Vierteln mit I, J (LinuxCNC).
zeilen = pp.programm(pp.abschnitte(job), pp.steuerung("linuxcnc"), None, "Ringnut").zeilen
g3 = [z for z in zeilen if z.startswith("G3") or " G3 " in f" {z} "]
pruefe(
    len(g3) >= 4 * bahn.kreise and all(" I" in z and " J" in z for z in g3), f"Programm: {g3[:3]}"
)
pruefe(not any(z.startswith("G2 ") or " G2 " in f" {z} " for z in zeilen), "Programm: G2")
# Ändern: Gegenlauf – G2 statt G3; Speichern und Laden: dieselbe Bahn.
rnop.aendere(op, tc, 0.0, gleichlauf=False)
doc.recompute()
namen = [b.Name for b in op.Path.Commands]
pruefe("G2" in namen and "G3" not in namen, f"Gegenlauf: G2 {namen.count('G2')}")
rnop.aendere(op, tc, 0.0)
doc.recompute()
anzahl = len(op.Path.Commands)
pfad = os.path.join(tempfile.mkdtemp(), "ringnut.FCStd")
doc.saveAs(pfad)
FreeCAD.closeDocument(doc.Name)
doc = FreeCAD.openDocument(pfad)
op = next(o for o in doc.Objects if rnop.ist_ringnut(o))
op.touch()
doc.recompute()
pruefe(len(op.Path.Commands) == anzahl, f"nach dem Laden {len(op.Path.Commands)} statt {anzahl}")
pruefe(op.getEditorMode("Kreise") == ["ReadOnly"], "Kreise nach dem Laden änderbar")
print(ascii(f"Operation: {anzahl} Befehle"))

# Am Grund im Job: „Bohrung fräsen“ (Ø 12) fräst die Ø 20 bis auf den Boden der Nut, danach fräst
# „Ringnut fräsen“ den Freistich – mit dem Materialstand aus der Bohrung (keine Sackgasse).
from camaddon import bohrung as bo  # noqa: E402

doc2 = FreeCAD.newDocument("RingnutGrund")
objekt2 = doc2.addObject("Part::Feature", "Teil")
objekt2.Shape = grund
doc2.recompute()
job2 = PathJob.Create("Job", [objekt2])
job2.Stock.ExtZpos = 1.0
doc2.recompute()
klon2 = job2.Model.Group[0].Shape
schruppen = next(e for e in schaftfraeser.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
tc_b = js.controller_ohne_transaktion(doc2, job2, schaftfraeser, schruppen)
wand = [b.name for b in bb.bohrungen(klon2)]
op_b = bo.lege_an(job2, tc_b, schruppen.ap, schruppen.ae, flaechen=wand)
vollnut_w = next(e for e in weit.einsaetze(wz.ALLE) if e.art == wz.VOLLNUT)
tc_r = js.controller_ohne_transaktion(doc2, job2, weit, vollnut_w)
op_r = rnop.lege_an(job2, tc_r, 0.0, flaechen=[n.name for n in rn.ringnuten(klon2)])
doc2.recompute()
pruefe(
    abs(float(op_b.FinalDepth) - 8.0) < 1e-6 and op_r.Nuten == 1,
    f"am Grund im Job: Bohrung bis {float(op_b.FinalDepth)}, Ringnut {op_r.Nuten} Nuten "
    f"({[b.Name for b in op_r.Path.Commands][:3]})",
)
z_eil = [b.Parameters["Z"] for b in op_r.Path.Commands if b.Name == "G0" and "Z" in b.Parameters]
pruefe(min(z_eil) >= 8.0 + sicherheit - 1e-6, f"am Grund im Job: Eilgang bis z {min(z_eil)}")

# Ohne Materialstand (davor eine Simultan-Operation, eine gedrehte Achse – materialstand.fuer gibt
# None) sieht niemand, ob die Bohrung fertig ist: Dann rechnet die Ringnut nur, wenn eine aktive
# Operation davor im Job eine Wand der Bohrung über der Nut fräst (Nachprüfung, 2026-11-14 – bis
# dahin fuhr die Scheibe im Vorschub mittig in eine volle Bohrung).
fuer_vorher = mst.fuer
mst.fuer = lambda *a, **k: None
try:
    try:
        rnop.rechne(op_r, job2, job2.Model.Group)
        ohne_stand = ""
    except ValueError as e:
        ohne_stand = str(e)
    pruefe(not ohne_stand, f"ohne Stand, Bohrung davor gefräst: abgelehnt ({ohne_stand})")
    op_b.Active = False
    try:
        rnop.rechne(op_r, job2, job2.Model.Group)
        ohne_bohrung = ""
    except ValueError as e:
        ohne_bohrung = str(e)
    pruefe(
        "Bohrung" in ohne_bohrung and "Materialstand" in ohne_bohrung,
        f"ohne Stand und ohne Bohrung davor: nicht abgelehnt ({ohne_bohrung!r})",
    )
    op_b.Active = True
finally:
    mst.fuer = fuer_vorher
FreeCAD.closeDocument(doc2.Name)

# Fehlt einem Nutenfräser nur ein Maß, sagt mass_fehlt es (der Knopf öffnet dann das Werkzeug);
# passt er oder ist er wirklich zu groß, nicht.
ohne_breite = nutenfraeser(19.0, 0.0, 9.5, 11.0)
ohne_hals = nutenfraeser(19.0, 2.15, 9.5, 0.0, schaft=16.0)
zu_gross = nutenfraeser(70.0, 2.15, 30.0, 11.0)
fehlt = [rn.mass_fehlt(oring, w_) for w_ in (ohne_breite, ohne_hals, zu_gross)]
pruefe("Breite" in fehlt[0], f"ohne Breite: {fehlt[0]!r}")
pruefe("Halslänge" in fehlt[1], f"ohne Hals: {fehlt[1]!r}")
pruefe(not fehlt[2], f"zu groß: {fehlt[2]!r}")

# Der Text im Block: je Nut eine Zeile mit ihrer Fläche.
text = ba._Ringnut().ergebnis_text(bahn, "5,8 min")
pruefe(lager.name in text and oring.name in text and "<br>" in text, f"Ergebnis: {text}")
schmal = replace(bahn, je_nut=bahn.je_nut[:1], nicht_passend=((oring.name, "zu groß"),))
pruefe("zu groß" in ba._Ringnut().ergebnis_text(schmal, "3 min"), "Ergebnis ohne Grund")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
