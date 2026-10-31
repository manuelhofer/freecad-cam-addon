# Prüft spannmittel (W-042): Sammlung speichern und laden, die Aufspannung am Job, den Körper
# mit anliegenden Backen und den Nullpunkt-Vorschlag.
# 1. Sammlung: zwei Spannmittel speichern, laden – gleich; ein gleicher Name bekommt „(2)“.
# 2. Schraubstock, Backenhöhe 40, Höhe 115, 10 mm gespannt, Rohteil 100 × 60 × 30: Unterseite auf
#    105 mm, die feste Backe an y 0 des Rohteils (im Job an YMin), die bewegliche an YMax; um 90°
#    gedreht spannen die Backen in X.
# 3. Zentrischspanner auf einem Nullpunktmodul (Höhe 40) bei X 50, Y −20: Rohteilmitte bei
#    X 50, Y −20, Unterseite 40 + 100 − 3.
# 4. Hinweise: 200 mm breit in 160 mm Spannweite; Pratzen, Rohteil höher als ihre Spannhöhe.
# 5. Am Job: setze/aufspannung, spannung.schraubstock nimmt den Körper, der Nullpunkt-Vorschlag
#    folgt, spannung.gespannt ist die Spanntiefe, entfernen räumt auf.
# 6. Halter aus dem Katalog (halter_katalog): Schrumpffutter an HSK-A63, A 100, Nase Ø 24, Körper
#    Ø 32 – der Flansch der Aufnahme, die Länge A, vorn Ø 24; ohne Maße geschätzt und so benannt.
# 7. Die mitgelieferten Kataloge: genug Reihen, jede Größe gibt ein Spannmittel bzw. einen Halter
#    mit Maßen über 0.
import os
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from camaddon import reichweite as rw  # noqa: E402
from camaddon import spannmittel as sm  # noqa: E402
from camaddon import spannung  # noqa: E402

V = FreeCAD.Vector
fehler = []


def nah(a, b, was, genau=1e-6):
    if abs(a - b) > genau:
        fehler.append(f"{was}: {a} statt {b}")


# 1. Sammlung
sammlung = sm.Sammlung()
schraubstock = sammlung.dazu(sm.neu(sm.SCHRAUBSTOCK))
schraubstock.name = "Gressel C2 125"
schraubstock.hersteller = "Gressel"
zentrisch = sammlung.dazu(sm.neu(sm.ZENTRISCH))
nochmal = sammlung.dazu(sm.Spannmittel.aus_dict(zentrisch.als_dict()))
if not nochmal.name.endswith("(2)"):
    fehler.append(f"zweiter Name: {nochmal.name}")
pfad = os.path.join(tempfile.mkdtemp(), "spannmittel.json")
sammlung.speichern(pfad)
if not sm.Sammlung.laden(pfad).gleich(sammlung):
    fehler.append("geladen ist nicht gleich gespeichert")

# 2. Schraubstock
box = Part.makeBox(100, 60, 30, V(-50, -30, 0)).BoundBox
auf = sm.Aufspannung(schraubstock, spanntiefe=10.0)
nah(sm.auflage(auf, box), 105.0, "Auflage Schraubstock")
form = sm.koerper(auf, box)
backen = sorted(
    (s for s in form.Solids if abs(s.BoundBox.ZMax - 115.0) < 1e-6), key=lambda s: s.BoundBox.YMin
)
if len(backen) != 2:
    fehler.append(f"Schraubstock: {len(backen)} Backen")
else:
    nah(backen[0].BoundBox.YMax, 0.0, "feste Backe")
    nah(backen[1].BoundBox.YMin, 60.0, "bewegliche Backe")
nah(sm.nullpunkt_vorschlag(auf, box)[2], 105.0, "Nullpunkt Z")
nah(
    sm.nullpunkt_vorschlag(auf, box)[1],
    30.0,
    "Nullpunkt Y (Rohteilmitte 30 hinter der festen Backe)",
)
gedreht = sm.Aufspannung(schraubstock, drehung=90, spanntiefe=10.0)
form = sm.koerper(gedreht, box)
bewegliche = max(form.Solids, key=lambda s: s.BoundBox.YMin)
nah(bewegliche.BoundBox.YMin, 100.0, "um 90° gedreht: Spannweite = Länge in X")

# 3. Zentrischspanner auf Nullpunkt
modul = sm.neu(sm.NULLPUNKT)
auf = sm.Aufspannung(zentrisch, modul, 50.0, -20.0)
x, y, z = sm.nullpunkt_vorschlag(auf, box)
nah(x, 50.0, "Zentrisch X")
nah(y, -20.0, "Zentrisch Y")
nah(z, 40.0 + 100.0 - 3.0, "Zentrisch Z")
form = sm.koerper(auf, box)
nah(form.BoundBox.ZMax, 140.0, "Zentrisch oben")
nah(form.BoundBox.ZMin, 0.0, "Nullpunktmodul unten")

# 4. Hinweise
breit = Part.makeBox(100, 200, 30).BoundBox
if not sm.hinweise(sm.Aufspannung(schraubstock), breit):
    fehler.append("200 mm breit in 160 mm Spannweite: kein Hinweis")
if sm.hinweise(sm.Aufspannung(schraubstock), box):
    fehler.append(f"passt, trotzdem: {sm.hinweise(sm.Aufspannung(schraubstock), box)}")
pratzen = sm.neu(sm.PRATZEN)
hoch = Part.makeBox(100, 60, 90).BoundBox
if not sm.hinweise(sm.Aufspannung(pratzen), hoch):
    fehler.append("Pratzen, 90 mm hoch bei 60 mm Spannhöhe: kein Hinweis")
form = sm.koerper(sm.Aufspannung(pratzen), box)
nah(form.BoundBox.ZMin, 0.0, "Pratzen unten")
if form.BoundBox.ZMax <= 30.0 + pratzen.mass("dicke") - 1e-6:
    fehler.append("Pratzen liegen nicht auf dem Rohteil")

# 5. Am Job
dokument = FreeCAD.newDocument("spannmittel")
roh = dokument.addObject("Part::Box", "Rohteil")
roh.Length, roh.Width, roh.Height = 100, 60, 30
job = dokument.addObject("App::FeaturePython", "Job")
job.addProperty("App::PropertyLink", "Stock")
job.Stock = roh
dokument.recompute()
sm.setze(job, sm.Aufspannung(schraubstock, x=10.0, spanntiefe=8.0))
if sm.aufspannung(job) is None or sm.aufspannung(job).spannmittel.name != "Gressel C2 125":
    fehler.append("die Aufspannung steht nicht am Job")
nah(spannung.gespannt(job), 8.0, "gespannt")
backen = spannung.schraubstock(job)
if backen is None:
    fehler.append("spannung.schraubstock ohne Körper")
else:
    feste = min(
        (s for s in backen.Solids if abs(s.BoundBox.ZMax - backen.BoundBox.ZMax) < 1e-6),
        key=lambda s: s.BoundBox.YMin,
    )
    nah(feste.BoundBox.YMax, 0.0, "feste Backe am Rohteil (im Job)")
    nah(backen.BoundBox.ZMax, 8.0, "Oberkante Backen = 8 mm über der Unterseite")
nullpunkt = rw.vorschlag_nullpunkt(job)
nah(nullpunkt.x, 10.0 - 50.0, "Nullpunkt-Vorschlag X")
nah(nullpunkt.z, 115.0 - 8.0, "Nullpunkt-Vorschlag Z")
sm.setze(job, None)
if sm.aufspannung(job) is not None or sm.EIGENSCHAFT in job.PropertiesList:
    fehler.append("entfernen: die Aufspannung bleibt")
FreeCAD.closeDocument(dokument.Name)

# 6. Halter aus dem Katalog
from camaddon import halter as hl  # noqa: E402
from camaddon import halter_katalog as hk  # noqa: E402
from camaddon import katalog  # noqa: E402
from camaddon.sprache import tr  # noqa: E402

reihe = katalog.Reihe("probe:0", "Probe", "Schrumpf", hk.SCHRUMPF, aufnahme="HSK-A63")
groesse = {"name": "d12", "artikel": "", "link": "", "masse": {}}
groesse["masse"] = {"d_spann": 12.0, "a": 100.0, "d_nase": 24.0, "d_koerper": 32.0}
halter = hk.aus_katalog(reihe, groesse)
nah(halter.laenge, 100.0, "Halter: Länge A", 0.02)
nah(halter.abschnitte[0].d_oben, hl.AUFNAHMEN["HSK-A63"][1], "Halter: Flansch")
nah(halter.abschnitte[-1].d_unten, 24.0, "Halter: vorn")
if halter.abschnitte[0].art != hl.FLANSCH or halter.bezeichnung != "Probe":
    fehler.append(f"Halter: {halter.abschnitte[0]} {halter.bezeichnung!r}")
groesse["masse"] = {"d_spann": 12.0}
if hk.aus_katalog(reihe, groesse).bezeichnung != tr("hk.geschaetzt", bezeichnung="Probe"):
    fehler.append("ohne Maße nicht als geschätzt benannt")

# 7. Die mitgelieferten Kataloge
reihen_sm = sm.katalog_reihen()
reihen_hk = hk.katalog_reihen()
if len(reihen_sm) < 10 or len(reihen_hk) < 10:
    fehler.append(f"Kataloge: {len(reihen_sm)} Spannmittel-, {len(reihen_hk)} Halterreihen")
for r in reihen_sm:
    for g in r.groessen:
        s = sm.aus_katalog(r, g)
        if not all(s.mass(f) >= 0 for f, _w in sm.FELDER[s.art]) or not s.name:
            fehler.append(f"Spannmittel {r.kennung} {g['name']}: {s.masse}")
        try:
            sm.koerper(sm.Aufspannung(s), box)
        except Exception as ausnahme:
            fehler.append(f"Körper {r.kennung} {g['name']}: {ausnahme}")
for r in reihen_hk:
    for g in r.groessen:
        h = hk.aus_katalog(r, g)
        if (
            h.laenge <= hl.AUFNAHMEN[r.aufnahme][2]
            or min(min(a.d_oben, a.d_unten) for a in h.abschnitte) <= 0
        ):
            fehler.append(f"Halter {r.kennung} {g['name']}: {h.abschnitte}")

# 8. Vorschläge aus dem Katalog: ein Rohteil 300 breit – die kleinsten, die es nehmen, je Hersteller
breit = Part.makeBox(100, 300, 40).BoundBox
vorschlaege = sm.aus_dem_katalog(breit)
if not vorschlaege or any(sm.passt(v, breit)[0] is None for v in vorschlaege):
    fehler.append(f"Katalog-Vorschläge: {[v.name for v in vorschlaege]}")
if len({v.hersteller for v in vorschlaege}) != len(vorschlaege):
    fehler.append("zwei Vorschläge vom selben Hersteller")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
