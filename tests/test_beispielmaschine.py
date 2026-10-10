# Prüft die Beispielmaschinen zum Ausprobieren (W-001): Der Löser lässt alle
# Teile, wo sie gebaut sind; X1, Y1, Z1, S1 und beide Aufnahmen sind
# eingerichtet, ohne Warnung; Verfahren bewegt Tisch, Sattel und Kopf in
# Achsrichtung und hält die Grenzen ein. Dann alle Bauarten zur Auswahl
# (Drehmaschine, 3-Achs, drei senkrechte 5-Achs, G550): jede mit ihren Achsen, ohne Warnung,
# jede Achse fährt, und die Auswahl merkt sich die zuletzt geladene. Zuletzt
# die Drehmaschine mit eigenen Maßen („Neue Maschine …“): Name, Wege,
# Bettneigung, Plätze, Drehzahl und die schräge Achse – ebenso die 3-Achs-Fräse
# mit Wegen, Drehzahl und Name (D-26), die 5-Achs-Fräsen dazu mit Schwenkbereichen – und
# ungültige Maße. X und Z der Drehmaschine
# zählen wie an der Maschine: ab Spindelachse und Spindelnase bis zur Mitte von P1.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD as App

from camaddon import PARAMETER_PFAD, beispielmaschine, schraege_achse, schwenken, sprache
from camaddon import halter as hl
from camaddon import kette as kette_modul
from camaddon import maschine as m
from camaddon import reichweite as rw
from camaddon import schruppwerte as sw
from camaddon import verfahren as vf
from camaddon.kette import HINWEIS, LINEAR

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def weg(name):
    """Wie weit ein Teil seit dem Bauen verschoben ist."""
    return doc.getObject(name).Placement.Base - gebaut[name].Base


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")

asm, ma = beispielmaschine.fraesmaschine()
doc = asm.Document
TEILE = ("Bett", "Staender", "Sattel", "Tisch", "Fraeskopf", "Spindel")
gebaut = {n: App.Placement(doc.getObject(n).Placement) for n in TEILE}
for teil in TEILE:
    doc.getObject(teil).touch()
doc.recompute()
for teil in TEILE:
    pruefe(doc.getObject(teil).Placement.isSame(gebaut[teil], 1e-6), f"{teil} verschoben")
pruefe(doc.Label == "Beispiel 3-Achs-Fräse" and ma.Label == "3-Achs-Fräse", "Namen")

# Eingerichtet und ohne Warnung.
namen = sorted(b.NcName for b in m.betriebsarten(ma))
pruefe(namen == ["S1", "X1", "Y1", "Z1"], f"Betriebsarten: {namen}")
warnungen = [x.text for x in m.pruefe(ma) if x.schwere != HINWEIS]
pruefe(not warnungen, f"Warnungen: {warnungen}")
aufnahmen = {a.Art: a for a in m.aufnahmen(ma)}
werkstueck = m.globale_platzierung(aufnahmen[m.AUFNAHME_WERKSTUECK].Lcs).Base
werkzeug = m.globale_platzierung(aufnahmen[m.AUFNAHME_WERKZEUG].Lcs).Base
pruefe(werkstueck.isEqual(App.Vector(400, 350, 250), 1e-6), f"Werkstückaufnahme {werkstueck}")
pruefe(werkzeug.isEqual(App.Vector(400, 350, 380), 1e-6), f"Werkzeugaufnahme {werkzeug}")
pruefe(sw.grenzen_der_maschine(ma) == (12000, 10000), f"Grenzen {sw.grenzen_der_maschine(ma)}")

# Verfahren: alle Achsen stehen auf 0; X bewegt den Tisch, Y Sattel und
# Tisch, Z Kopf und Spindel – jeweils in Achsrichtung.
v = vf.Verfahren(asm)
achse = {a.gelenk.Name: a for a in v.achsen}
pruefe(sorted(achse) == ["Spindelachse", "X", "Y", "Z"], f"Achsen: {sorted(achse)}")
for name in ("X", "Y", "Z"):
    pruefe(abs(v.stellung(achse[name])) < 1e-9, f"{name} steht nicht auf 0")
v.setze(achse["X"], 100)
v.setze(achse["Y"], 50)
v.setze(achse["Z"], -50)
for teil, soll in (
    ("Tisch", App.Vector(100, 50, 0)),
    ("Sattel", App.Vector(0, 50, 0)),
    ("Fraeskopf", App.Vector(0, 0, -50)),
    ("Spindel", App.Vector(0, 0, -50)),
    ("Staender", App.Vector()),
):
    pruefe(weg(teil).isEqual(soll, 1e-6), f"{teil} um {weg(teil)} statt {soll}")
pruefe(abs(vf.gelenkstellung(achse["Z"].gelenk, LINEAR) + 50) < 1e-6, "Z steht nicht auf −50")
# Grenzen: X ±250, Y −150 … 120, Z −100 … 250.
for name, soll, grenze in (("X", 400, 250), ("Y", -400, -150), ("Z", 400, 250)):
    pruefe(v.setze(achse[name], soll) == grenze, f"{name} fährt über die Grenze {grenze}")
v.grundstellung()
pruefe(all(weg(t).Length < 1e-6 for t in TEILE), "Grundstellung")

App.closeDocument(doc.Name)

# Alle Bauarten zur Auswahl.
ACHSEN = {
    beispielmaschine.DREHMASCHINE: ["C1", "C3", "S1", "S3", "T", "X1", "Y1", "Z1"],
    beispielmaschine.FRAESE_3: ["S1", "X1", "Y1", "Z1"],
    beispielmaschine.TISCH_TISCH: ["A1", "C1", "S1", "X1", "Y1", "Z1"],
    beispielmaschine.KOPF_KOPF: ["A1", "B1", "S1", "X1", "Y1", "Z1"],
    beispielmaschine.KOPF_TISCH: ["B1", "C1", "S1", "X1", "Y1", "Z1"],
    beispielmaschine.GROB_G550: ["A1", "B1", "S1", "X1", "Y1", "Z1"],
}
pruefe(list(ACHSEN) == list(beispielmaschine.ARTEN), f"Bauarten {beispielmaschine.ARTEN}")
# lade() merkt sich die Bauart in den Einstellungen – danach wie vorher.
einstellungen = App.ParamGet(PARAMETER_PFAD)
zuletzt_vorher = einstellungen.GetString(beispielmaschine._ZULETZT, "")
KOERPER = ("Part::Box", "Part::Cylinder", "App::Part")
for art in beispielmaschine.ARTEN:
    asm, ma = beispielmaschine.lade(art)
    doc = asm.Document
    pruefe(beispielmaschine.zuletzt_gewaehlt() == art, f"{art}: nicht gemerkt")
    pruefe(ma.Label == beispielmaschine.titel(art), f"{art}: Maschine heißt {ma.Label}")
    namen = sorted(b.NcName for b in m.betriebsarten(ma))
    pruefe(namen == ACHSEN[art], f"{art}: Betriebsarten {namen}")
    warnungen = [x.text for x in m.pruefe(ma) if x.schwere != HINWEIS]
    pruefe(not warnungen, f"{art}: Warnungen {warnungen}")
    arten = sorted(a.Art for a in m.aufnahmen(ma))
    pruefe(m.AUFNAHME_WERKSTUECK in arten and m.AUFNAHME_WERKZEUG in arten, f"{art}: {arten}")
    # Der Löser lässt jedes Teil, wo es gebaut ist.
    teile = [o for o in doc.Objects if o.TypeId in KOERPER]
    gebaut = {o.Name: App.Placement(o.Placement) for o in teile}
    for o in teile:
        o.touch()
    doc.recompute()
    verschoben = [o.Name for o in teile if not o.Placement.isSame(gebaut[o.Name], 1e-6)]
    pruefe(not verschoben, f"{art}: verschoben {verschoben}")
    # Jede Achse fährt (30 mm oder 30°, höchstens bis zur Grenze), Grundstellung zurück.
    v = vf.Verfahren(asm)
    for achse in v.achsen:
        erreicht = v.setze(achse, 30)
        ist = vf.gelenkstellung(achse.gelenk, achse.art)
        pruefe(
            abs(erreicht) > 1 and abs(v.stellung(achse) - erreicht) < 1e-6,
            f"{art}: {achse.gelenk.Name} auf {erreicht}, steht auf {v.stellung(achse)} ({ist})",
        )
    v.grundstellung()
    zurueck = [o.Name for o in teile if not o.Placement.isSame(gebaut[o.Name], 1e-6)]
    pruefe(not zurueck, f"{art}: nach der Grundstellung nicht zurück: {zurueck}")
    if art == beispielmaschine.DREHMASCHINE:
        # Zwölf Revolverplätze, alle am Werkzeugantrieb S3 – die Halter kommen mit den
        # Werkzeugen (W-002 Stufe E); keiner ist fest eingebaut.
        plaetze = [a for a in m.aufnahmen(ma) if a.Art == m.AUFNAHME_WERKZEUG]
        angetrieben = sorted(a.Label for a in plaetze if getattr(a.Spindel, "NcName", "") == "S3")
        pruefe(len(plaetze) == 12, f"Revolverplätze: {len(plaetze)}")
        pruefe(len(angetrieben) == 12, f"angetrieben: {angetrieben}")
        # Je ein S und ein C (Manuel, 2026-10-03): S1/C1 die Hauptspindel, S3/C3 der Antrieb –
        # maschine.spindeln() weiß, welche was tut.
        sp = m.spindeln(ma)
        rollen_ = (
            sp.haupt.NcName,
            sp.haupt_c.NcName,
            [(s.NcName, c.NcName if c else None) for s, c in sp.antriebe],
        )
        pruefe(rollen_ == ("S1", "C1", [("S3", "C3")]), f"Spindeln: {rollen_}")
        namen = {o.Label for o in doc.Objects}
        pruefe(not {"HalterRadial", "HalterAxial"} & namen, "fester Halter am Revolver")
        pruefe({"Aufnahme01", "Aufnahme12"} <= namen, "Aufnahmen an der Stirn fehlen")
        # Am Umfang nichts: So ein Revolver hat dort keine Stationen, und die angedeuteten
        # stießen ans Teil (Manuel, 2026-09-30, P-2026-09-30-52; vorher D-46).
        pruefe(not any(n.startswith("Station") for n in namen), "Stationen am Umfang")
        # X und Z zählen wie an der Maschine (Manuel, 2026-09-30, P-2026-09-30-50): gebaut
        # steht sie bei X 275 und Z 220; auf X 0 steht die Mitte von P1 auf der Spindelachse,
        # auf Z 0 ihre Stirn in der Ebene der Spindelnase.
        achse = {a.gelenk.Label: a for a in v.achsen}
        gebaut_xz = (v.stellung(achse["X"]), v.stellung(achse["Z"]))
        pruefe(
            abs(gebaut_xz[0] - 275) < 1e-6 and abs(gebaut_xz[1] - 220) < 1e-6,
            f"gebaut X, Z: {gebaut_xz}",
        )
        pruefe(
            (achse["X"].minimum, achse["X"].maximum) == (-25.0, 425.0)
            and (achse["Z"].minimum, achse["Z"].maximum) == (0.0, 520.0),
            f"Wege X {achse['X'].minimum} … {achse['X'].maximum}, "
            f"Z {achse['Z'].minimum} … {achse['Z'].maximum}",
        )
        v.setze_alle({achse["X"]: 0.0, achse["Z"]: 0.0})
        p1 = next(a for a in plaetze if a.Platz == 1)
        spindel = achse["Hauptspindel"]
        abstand = m.globale_platzierung(p1.Lcs).Base - spindel.ursprung
        laengs = abstand.dot(spindel.richtung)
        quer = (abstand - spindel.richtung * laengs).Length
        pruefe(quer < 1e-6 and abs(laengs) < 1e-6, f"P1 auf X 0, Z 0: quer {quer}, längs {laengs}")
        v.grundstellung()
    App.closeDocument(doc.Name)

# Die G550 nach dem GROB-Konzept (P-2026-10-10-19): X, Y und Z auf der Werkzeugseite, der Tisch
# hat nur A und B. Welt-Z ist die Höhe; NC-Y hebt die Spindel, NC-Z fährt sie zurück (Welt −Y).
asm, ma = beispielmaschine.grob_g550()
doc = asm.Document
kette = kette_modul.lies_kette(asm)
rollen, _ = m.rollen(kette, ma)
achsen = {a.gelenk.Label: a for a in kette.achsen}
pruefe(
    {n: rollen.get(achsen[n].gelenk) for n in ("X", "Y", "Z", "A", "B")}
    == {"X": m.KOPF, "Y": m.KOPF, "Z": m.KOPF, "A": m.TISCH, "B": m.TISCH},
    "G550: Achsen auf der falschen Seite",
)
v = vf.Verfahren(asm, kette)
gebaut = {
    n: App.Placement(doc.getObject(n).Placement)
    for n in (
        "XSattel",
        "YSchlitten",
        "ZSchlitten",
        "Spindel",
        "Tischstaender",
        "Wiege",
        "Rundtisch",
    )
}
v.setze_alle({achsen["X"]: 60, achsen["Z"]: 100, achsen["Y"]: 40})
for teil, soll in (
    ("XSattel", App.Vector(60, 0, 0)),
    ("YSchlitten", App.Vector(60, 0, 40)),
    ("Spindel", App.Vector(60, -100, 40)),
    ("Rundtisch", App.Vector()),
    ("Wiege", App.Vector()),
    ("Tischstaender", App.Vector()),
):
    pruefe(weg(teil).isEqual(soll, 1e-6), f"G550 {teil}: {weg(teil)} statt {soll}")
v.grundstellung()


def _form(name):
    teil = doc.getObject(name)
    form = teil.Shape.copy()
    form.Placement = teil.getGlobalPlacement()
    return form


# Der Tunnel (Manuel, 2026-10-10: „die z achse fährt komplett aus dem verfahrraum raus, die ist in
# einem loch, da kommt der tisch garnicht hin“): Bei Z ganz zurück steht die Spindelnase nicht
# vor der Ständerfront, und der Y-Schlitten bleibt in jeder Y-Stellung zwischen Sattel und Decke.
v.setze(achsen["Z"], 485)
nase = doc.getObject("Spindelnase").getGlobalPlacement().Base
front = _form("WandLinks").BoundBox.YMax
pruefe(nase.y <= front + 1e-6, f"G550: Spindelnase bei Z +485 vor dem Ständer ({nase.y} > {front})")
v.grundstellung()
for y in (-510, 510):
    v.setze(achsen["Y"], y)
    unten, oben = _form("YUnten").BoundBox.ZMin, _form("YOben").BoundBox.ZMax
    pruefe(
        unten > _form("Sattel").BoundBox.ZMax and oben < _form("Decke").BoundBox.ZMin,
        f"G550: Y-Schlitten bei Y {y} außerhalb des Tunnels ({unten} … {oben})",
    )
v.grundstellung()
pruefe(vf.programm_vorzeichen(achsen["A"], kette) == -1, "G550: A gegen DIN")
# Der Ständer kommt in keiner Endlage an die Lagerböcke oder den Tisch.
for x in (-400, 400):
    for y in (-510, 510):
        for z in (-485, 485):
            v.setze_alle({achsen["X"]: x, achsen["Y"]: y, achsen["Z"]: z})
            for a_name, b_name in (
                ("WandLinks", "LagerRechts"),
                ("WandRechts", "LagerLinks"),
                ("ZSchlitten", "Tischscheibe"),
                ("Spindel", "Tischscheibe"),
            ):
                abstand = _form(a_name).distToShape(_form(b_name))[0]
                pruefe(
                    abstand > 1.0, f"G550: X {x}/Y {y}/Z {z}: {a_name} an {b_name} ({abstand:.1f})"
                )
v.grundstellung()
pruefe(vf.programm_vorzeichen(achsen["B"], kette) == -1, "G550: B gegen DIN")
pruefe(v.grenzen(achsen["A"]) == (-45.0, 185.0), f"G550: A {v.grenzen(achsen['A'])}")
pruefe(v.grenzen(achsen["B"]) == (None, None), "G550: B nicht endlos")
pruefe(doc.getObject("Tischscheibe").Radius == 385, "G550: Tischdurchmesser")
aufnahmen = {a.Art: a for a in m.aufnahmen(ma)}
werkzeug = m.globale_platzierung(aufnahmen[m.AUFNAHME_WERKZEUG].Lcs)
richtung = werkzeug.Rotation.multVec(App.Vector(0, 0, 1))
pruefe(richtung.isEqual(App.Vector(0, -1, 0), 1e-6), f"G550: Spindel {richtung}")
v.setze(achsen["A"], 90)  # An der Steuerung A = −90: Tischoberseite zur Spindel.
v.setze(achsen["B"], 45)
spannplatz = m.globale_platzierung(aufnahmen[m.AUFNAHME_WERKSTUECK].Lcs)
normal = spannplatz.Rotation.multVec(App.Vector(0, 0, 1))
pruefe(normal.isEqual(richtung, 1e-6), f"G550: Spannfläche bei A−90 B−45 {normal}")
v.grundstellung()
# Der gemeinsame 3+2-Kern muss die Tischoberseite zur waagerechten Spindel ausrichten.
p = rw.Pruefung(asm, ma)
sm = schwenken.Maschine(p, p.werkzeugaufnahme(1), 125.0, (0, 0, 0))
loesungen = sm.loese((0, 0, 1))
passend = [r for r in loesungen if all(a.erlaubt(r[a.buchstabe]) for a in sm.rundachsen)]
pruefe(bool(passend), f"G550: 3+2 erreicht die Tischoberseite nicht: {loesungen}")
if passend:
    pruefe(sm.richtung(passend[0]).dot(App.Vector(0, 0, 1)) > 0.999999, "G550: 3+2 falsch")
    pruefe(sm.abbildung(passend[0]) is not None, "G550: keine Abbildung ohne TCPM")
App.closeDocument(doc.Name)

# --- Drehmaschine mit eigenen Maßen („Neue Maschine …“) ----------------------------------
masse = beispielmaschine.DrehmaschinenMasse(
    name="Meine Drehmaschine / 2",
    bettneigung=30,
    y_winkel=30,
    weg_x=(-80, 120),
    weg_y=(-40, 50),
    weg_z=(-50, 400),
    plaetze=8,
    drehzahl=4000,
    drehzahl_werkzeuge=3200,
    x_durchmesser=False,
)
pruefe(not masse.fehler(), f"gültige Maße: {masse.fehler()}")
asm, ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE, masse)
doc = asm.Document
kette = kette_modul.lies_kette(asm)
achsen = {a.gelenk.Label: a for a in kette.achsen}
pruefe(ma.Label == "Meine Drehmaschine / 2", f"Maschine: {ma.Label}")
pruefe(doc.Label == "Meine Drehmaschine - 2", f"Dokument: {doc.Label}")
for gelenk, weg_soll in (("X", (-80, 120)), ("Y", (-40, 50)), ("Z", (-50, 400))):
    ist = (achsen[gelenk].minimum, achsen[gelenk].maximum)
    pruefe(ist == weg_soll, f"Weg {gelenk}: {ist}")
# Gebaut stünde X auf 275 – außerhalb des Wegs bis 120: Die Maschine ist hineingefahren.
x_jetzt = vf.gelenkstellung(achsen["X"].gelenk, achsen["X"].art)
pruefe(abs(x_jetzt - 120) < 1e-6, f"X nach dem Bauen: {x_jetzt}")
# Das Bett ist 30° geneigt: X fährt 30° gegen die Waagrechte.
steigung = abs(math.degrees(math.asin(achsen["X"].richtung.z)))
pruefe(abs(steigung - 30) < 1e-6, f"X steigt um {steigung}°")
plaetze = [a for a in m.aufnahmen(ma) if a.Art == m.AUFNAHME_WERKZEUG]
pruefe(len(plaetze) == 8, f"Revolverplätze: {len(plaetze)}")
s1 = next(b for b in m.betriebsarten(ma) if b.NcName == "S1")
pruefe(s1.Drehzahl == 4000, f"S1: {s1.Drehzahl}")
# Die angetriebenen Werkzeuge haben ihre eigene Höchstdrehzahl (Manuel, 2026-09-30).
s3 = next(b for b in m.betriebsarten(ma) if b.NcName == "S3")
pruefe(s3.Drehzahl == 3200, f"S3: {s3.Drehzahl}")
# Der Revolver kennt seine VDI-Größe – die Halter-Vorlagen nehmen sie als Maß (P-2026-09-30-70).
t_ = next(b for b in m.betriebsarten(ma) if b.NcName == "T")
pruefe(t_.Vdi == 30 and m.vdi_groesse(ma) == 30, f"VDI am Revolver: {getattr(t_, 'Vdi', None)}")
# „X als: Radius“ (P-2026-09-30-54): X1 zählt nicht im Durchmesser.
x1 = next(b for b in m.betriebsarten(ma) if b.NcName == "X1")
pruefe(not x1.Durchmesser and not m.x_im_durchmesser(ma), "X im Radius gewählt, X1 im Ø")
trafos = m.transformationen(ma)
pruefe(len(trafos) == 1, f"schräge Achse: {len(trafos)}")
if trafos:
    alpha = schraege_achse.winkel(kette, ma, trafos[0])
    pruefe(alpha is not None and abs(alpha - 30) < 1e-6, f"Y-Winkel: {alpha}")
warnungen = [x.text for x in m.pruefe(ma, kette) if x.schwere != HINWEIS]
pruefe(not warnungen, f"eigene Maße, Warnungen: {warnungen}")
hinweise = [x.schluessel for x in m.pruefe(ma, kette) if x.schluessel.startswith("maschine.trafo")]
pruefe(not hinweise, f"eigene Maße, Hinweise zur schrägen Achse: {hinweise}")
App.closeDocument(doc.Name)

# Revolver mit VDI am Umfang (Sternrevolver, P-2026-09-30-52): acht Plätze auf dem Rand der
# Scheibe Ø 400, radial; ein gerader Halter zeigt zur Spindelachse, ein gewinkelter (X des
# LCS) zum Futter. Gebaut X 195 (405 − 200 − 10), Z 285 (die Mitte der Scheibe); auf X 0 und
# Z 0 steht P1 auf der Spindelachse in der Ebene der Spindelnase.
masse = beispielmaschine.DrehmaschinenMasse(
    revolver=beispielmaschine.REVOLVER_UMFANG, scheibe=400, vdi=40, plaetze=8
)
pruefe(not masse.fehler(), f"Sternrevolver: {masse.fehler()}")
asm, ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE, masse)
doc = asm.Document
kette = kette_modul.lies_kette(asm)
achse = {a.gelenk.Label: a for a in kette.achsen}
plaetze = [a for a in m.aufnahmen(ma) if a.Art == m.AUFNAHME_WERKZEUG]
pruefe(len(plaetze) == 8, f"Sternrevolver, Plätze: {len(plaetze)}")
spindel = achse["Hauptspindel"]
p1 = m.globale_platzierung(next(a for a in plaetze if a.Platz == 1).Lcs)
z_lcs = p1.Rotation.multVec(App.Vector(0, 0, 1))
x_lcs = p1.Rotation.multVec(App.Vector(1, 0, 0))
nach_innen = (spindel.ursprung - p1.Base) - spindel.richtung * (
    (spindel.ursprung - p1.Base).dot(spindel.richtung)
)
nach_innen.normalize()
pruefe(abs(z_lcs.dot(spindel.richtung)) < 1e-9, f"Sternrevolver: Z nicht radial {z_lcs}")
pruefe((z_lcs + nach_innen).Length < 1e-9, f"gerader Halter nicht zur Spindelachse: {z_lcs}")
pruefe((x_lcs + spindel.richtung).Length < 1e-9, f"gewinkelter nicht zum Futter: {x_lcs}")
v = vf.Verfahren(asm, kette)
gebaut_xz = (v.stellung(achse["X"]), v.stellung(achse["Z"]))
pruefe(abs(gebaut_xz[0] - 195) < 1e-6 and abs(gebaut_xz[1] - 285) < 1e-6, f"X, Z: {gebaut_xz}")
v.setze_alle({achse["X"]: 0.0, achse["Z"]: 0.0})
p1 = m.globale_platzierung(next(a for a in plaetze if a.Platz == 1).Lcs)
abstand = p1.Base - spindel.ursprung
laengs = abstand.dot(spindel.richtung)
quer = (abstand - spindel.richtung * laengs).Length
pruefe(quer < 1e-6 and abs(laengs) < 1e-6, f"Sternrevolver P1 auf X 0, Z 0: {quer}, {laengs}")
warnungen = [x.text for x in m.pruefe(ma, kette) if x.schwere != HINWEIS]
pruefe(not warnungen, f"Sternrevolver, Warnungen: {warnungen}")
# Für „Rundum schruppen“ (radial aus +X): ein gerader Halter kommt dort radial, „VDI30
# angetrieben radial“ nicht – der gelbe Satz rät dann zum geraden (P-2026-09-30-52).
v.grundstellung()
pruefung = rw.Pruefung(asm, ma)
# Wie vorgegeben zählt X im Durchmesser (P-2026-09-30-54) – die Texte zeigen es doppelt.
pruefe(
    {a.gelenk for a in pruefung.durchmesser} == {achse["X"].gelenk} and pruefung.x_durchmesser,
    f"im Durchmesser: {[a.gelenk.Label for a in pruefung.durchmesser]}, X {pruefung.x_durchmesser}",
)
_aufnahme, gerade = pruefung.kommt_aus(1, App.Vector(1, 0, 0))
gewinkelt = rw.Einspannung(0.0, hl.lage(hl.aus_vorlage("vdi30_radial")))
_aufnahme, mit_winkel = pruefung.kommt_aus(1, App.Vector(1, 0, 0), gewinkelt)
pruefe(gerade and not mit_winkel, f"Sternrevolver radial: gerade {gerade}, gewinkelt {mit_winkel}")
App.closeDocument(doc.Name)

# Ohne Y-Winkel keine schräge Achse; die Vorgaben sind die des Beispiels.
asm, ma = beispielmaschine.lade(
    beispielmaschine.DREHMASCHINE, beispielmaschine.DrehmaschinenMasse()
)
pruefe(not m.transformationen(ma), "Vorgabe mit schräger Achse")
pruefe(asm.Document.Label == "Beispiel Drehmaschine", f"Vorgabe-Name: {asm.Document.Label}")
App.closeDocument(asm.Document.Name)

# Die 3-Achs-Fräse mit eigenen Maßen (D-26): Grenzen der Gelenke, Drehzahl, Name.
masse = beispielmaschine.FraesenMasse(
    name="Meine Fräse", weg_x=(-300.0, 400.0), weg_y=(-200.0, 180.0), weg_z=(-150.0, 300.0)
)
masse.drehzahl = 8000.0
asm, ma = beispielmaschine.fraesmaschine(masse)
kette = kette_modul.lies_kette(asm)
grenzen = {a.gelenk.Label: (a.minimum, a.maximum) for a in kette.achsen if a.art == LINEAR}
pruefe(
    grenzen == {"X": (-300.0, 400.0), "Y": (-200.0, 180.0), "Z": (-150.0, 300.0)},
    f"Grenzen der Fräse: {grenzen}",
)
s1 = next(b for b in m.betriebsarten(ma) if b.NcName == "S1")
pruefe(s1.Drehzahl == 8000, f"S1 der Fräse: {s1.Drehzahl}")
pruefe(ma.Label == "Meine Fräse" and asm.Document.Label == "Meine Fräse", "Name der Fräse")
App.closeDocument(asm.Document.Name)
pruefe(beispielmaschine.FraesenMasse().fehler() == [], "Vorgabe der Fräse ungültig")
falsch = beispielmaschine.FraesenMasse(weg_y=(0.0, 0.0), drehzahl=0)
felder = [feld for feld, _satz in falsch.fehler()]
pruefe(felder == ["weg_y", "drehzahl"], f"ungültige Maße der Fräse: {felder}")

# Die 5-Achs-Fräsen mit eigenen Maßen (D-26): Wege, Schwenkbereiche, Drehzahl, Name; die
# Vorgaben sind die Beispiele.
for art, schwenk in (
    (beispielmaschine.TISCH_TISCH, (("A", -30.0, 110.0),)),
    (beispielmaschine.KOPF_TISCH, (("B", -90.0, 45.0),)),
    (beispielmaschine.KOPF_KOPF, (("A", -95.0, 95.0), ("B", -15.0, 105.0))),
    (beispielmaschine.GROB_G550, (("A", -30.0, 110.0),)),
):
    vorgabe = beispielmaschine.FuenfachsMasse.vorgabe(art)
    pruefe(vorgabe.fehler() == [], f"Vorgabe {art} ungültig: {vorgabe.fehler()}")
    masse = beispielmaschine.FuenfachsMasse(
        art=art,
        name="Meine 5-Achs",
        weg_x=(-400.0, 410.0),
        weg_y=(-220.0, 230.0),
        weg_z=(-300.0, 120.0),
        schwenk=schwenk,
        drehzahl=12000.0,
    )
    asm, ma = beispielmaschine.lade(art, masse)
    kette = kette_modul.lies_kette(asm)
    # Die Schwenkbereiche zählen wie die Steuerung (DIN 66217): A im Tisch dreht das Gelenk
    # rechtsherum um +X, die Steuerung andersherum – am Gelenk gespiegelt.
    grenzen = {}
    for a in kette.achsen:
        v = vf.programm_vorzeichen(a, kette)
        ende = (a.minimum, a.maximum)
        grenzen[a.gelenk.Label] = ende if v > 0 or None in ende else (-ende[1], -ende[0])
    erwartet = {"X": (-400.0, 410.0), "Y": (-220.0, 230.0), "Z": (-300.0, 120.0)}
    erwartet.update({b: (unten, oben) for b, unten, oben in schwenk})
    pruefe(
        {k: grenzen.get(k) for k in erwartet} == erwartet,
        f"Grenzen {art}: {grenzen}",
    )
    s1 = next(b for b in m.betriebsarten(ma) if b.NcName == "S1")
    pruefe(s1.Drehzahl == 12000, f"S1 {art}: {s1.Drehzahl}")
    pruefe(ma.Label == "Meine 5-Achs" and asm.Document.Label == "Meine 5-Achs", f"Name {art}")
    App.closeDocument(asm.Document.Name)
falsch = beispielmaschine.FuenfachsMasse(
    art=beispielmaschine.KOPF_KOPF,
    weg_x=(-10.0, 10.0),
    weg_y=(-10.0, 10.0),
    weg_z=(5.0, 10.0),
    schwenk=(("A", 10.0, 90.0), ("B", -400.0, 0.0)),
)
felder = [feld for feld, _satz in falsch.fehler()]
pruefe(
    felder == ["weg_z", "schwenk_A", "schwenk_B", "drehzahl"],
    f"ungültige Maße der 5-Achs-Fräse: {felder}",
)

# Ungültige Maße: je Feld ein Satz.
falsch = beispielmaschine.DrehmaschinenMasse(
    bettneigung=70,
    y_winkel=-61,
    weg_x=(10, 100),
    weg_y=(-5, -5),
    weg_z=(-20000, 10),
    plaetze=3,
    drehzahl=0,
    drehzahl_werkzeuge=0,
    revolver="stern",
    scheibe=100,
    vdi=33,
)
felder = [feld for feld, _schluessel in falsch.fehler()]
pruefe(
    felder
    == [
        "bettneigung",
        "y_winkel",
        "weg_x",
        "weg_y",
        "weg_z",
        "plaetze",
        "drehzahl",
        "drehzahl_werkzeuge",
        "revolver",
        "scheibe",
        "vdi",
    ],
    f"ungültige Maße: {felder}",
)

if zuletzt_vorher:
    einstellungen.SetString(beispielmaschine._ZULETZT, zuletzt_vorher)
else:
    einstellungen.RemString(beispielmaschine._ZULETZT)
sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
