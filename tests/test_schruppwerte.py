# Prüft den Planer für Schruppwerte (schruppwerte.py) an Manuels Schaftfräser
# Ø 12, 3 Schneiden: Spandickenausgleich je ae, Vorschlag an der ae-Grenze,
# an der Leistungsgrenze der Spindel, mit begrenzter Drehzahl und begrenztem
# Vorschub – und die Grenzen einer Maschine aus W-001.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)
sys.path.insert(0, os.path.join(ADDON, "tests"))

import FreeCAD

from camaddon import schnittdaten as sd
from camaddon import schruppwerte as sw
from camaddon import werkzeuge as wz

fehler = []


def ungefaehr(wert, soll, text, genau=0.05):
    if abs(wert - soll) > genau:
        fehler.append(f"{text}: {wert:.4f} statt {soll}")


fraeser = wz.Werkzeug(durchmesser=12, schneiden=3, schneidenlaenge=26)
c45 = type("W", (), {"kc11": 2220.0, "mc": 0.14})()

# Ohne Maschine: Vorschlag an der Grenze 10 % von D, der Span überall 0,05 mm.
plan = sw.plane(fraeser, 120, 0.05, 24, sw.Grenzen())
ungefaehr(plan.n, 3183.1, "n")
if plan.vorschlag is None or abs(plan.vorschlag.ae - 1.2) > 1e-9:
    fehler.append(f"Vorschlag ohne Maschine: {plan.vorschlag}")
else:
    ungefaehr(plan.vorschlag.fz, 0.0833, "fz bei 10 %", 1e-4)
    ungefaehr(plan.vorschlag.vf, 795.8, "vf bei 10 %", 0.1)
    ungefaehr(plan.vorschlag.q, 22.92, "Q bei 10 %", 0.01)
if plan.grund != sw.GRUND_AE:
    fehler.append(f"Grund ohne Maschine: {plan.grund}")
if any(abs(s.spandicke - 0.05) > 1e-9 for s in plan.stufen):
    fehler.append("Spandicke nicht überall 0,05 mm")
if any(b.q <= a.q for a, b in zip(plan.stufen, plan.stufen[1:], strict=False)):
    fehler.append("Q wächst nicht mit ae")
if [s.prozent for s in plan.stufen if not s.ueber_ae][-1] != 10:
    fehler.append("ae-Grenze 10 % nicht eingehalten")
# Bei D/2 kein Ausgleich mehr: fz = Spandicke.
ungefaehr(plan.stufen[-1].fz, 0.05, "fz bei 50 %", 1e-9)

# Übernommen wird als dynamischer Einsatz, abgerundet.
einsatz = sw.als_einsatz(plan, plan.vorschlag, 24)
if (einsatz.art, einsatz.ae, einsatz.ap, einsatz.vc, einsatz.fz) != (
    wz.DYNAMISCH,
    1.2,
    24,
    120.0,
    0.083,
):
    fehler.append(f"Einsatz: {einsatz}")

# Eine Grenze zwischen den Stufen wird selbst eine Stufe.
plan = sw.plane(fraeser, 120, 0.05, 24, sw.Grenzen(ae_prozent=11))
if plan.vorschlag is None or abs(plan.vorschlag.ae - 1.32) > 1e-9:
    fehler.append(f"Vorschlag bei 11 %: {plan.vorschlag}")

# Ohne ae-Grenze bis D/2 – breiter ist kein dynamisches Fräsen mehr.
plan = sw.plane(fraeser, 120, 0.05, 24, sw.Grenzen(ae_prozent=0))
if plan.vorschlag is None or plan.vorschlag.prozent != 50 or plan.grund != sw.GRUND_ENDE:
    fehler.append(f"ohne ae-Grenze: {plan.vorschlag}, {plan.grund}")

# Drehzahl begrenzt: n = Höchstdrehzahl, vc kleiner; der Einsatz bleibt darunter.
plan = sw.plane(fraeser, 120, 0.05, 24, sw.Grenzen(drehzahl=3000))
if not plan.drehzahl_begrenzt or plan.n != 3000:
    fehler.append(f"Drehzahlgrenze: n {plan.n}")
ungefaehr(plan.vc, 113.1, "vc bei 3000 U/min")
einsatz = sw.als_einsatz(plan, plan.vorschlag, 24)
if sd.drehzahl(einsatz.vc, 12) > 3000:
    fehler.append(f"Einsatz über der Höchstdrehzahl: vc {einsatz.vc}")

# Vorschub begrenzt: vf höchstens 1000 mm/min, der Span wird dort dünner.
plan = sw.plane(fraeser, 120, 0.05, 24, sw.Grenzen(vorschub=1000))
begrenzt = [s for s in plan.stufen if s.vorschub_begrenzt]
if [s.prozent for s in begrenzt] != [2, 3, 4, 5, 6]:
    fehler.append(f"Vorschub begrenzt bei: {[s.prozent for s in begrenzt]}")
if any(abs(s.vf - 1000) > 1e-9 or s.spandicke >= 0.05 for s in begrenzt):
    fehler.append("begrenzte Stufen: vf nicht 1000 oder Span nicht dünner")
if any(s.vf > 1000 + 1e-9 for s in plan.stufen):
    fehler.append("vf über der Grenze")

# Leistung: 1,5 kW Spindel, davon 80 % an der Schneide (1,2 kW). In C45 liegt die
# Grenze zwischen 6 % und 8 % – der Planer sucht sie auf 0,01 mm genau.
plan = sw.plane(fraeser, 120, 0.05, 24, sw.Grenzen(leistung=1.5), c45)
grenze = [s for s in plan.stufen if s.an_grenze]
if len(grenze) != 1 or plan.vorschlag is not grenze[0] or plan.grund != sw.GRUND_LEISTUNG:
    fehler.append(f"Leistungsgrenze: {grenze}, Vorschlag {plan.vorschlag}, {plan.grund}")
else:
    s = grenze[0]
    if not (0.72 < s.ae < 0.96) or s.leistung > 1.2 + 1e-9:
        fehler.append(f"Stufe an der Leistungsgrenze: ae {s.ae}, {s.leistung} kW")
    mehr = sw._stufe(fraeser, s.ae + 0.01, 24, 0.05, plan.n, sw.Grenzen(leistung=1.5), c45)
    if not mehr.ueber_leistung:
        fehler.append("0,01 mm mehr ae wäre auch noch gegangen")
# Ohne kc1.1 zählt die Leistung nicht.
plan = sw.plane(fraeser, 120, 0.05, 24, sw.Grenzen(leistung=1.5))
if plan.vorschlag is None or plan.vorschlag.ae != 1.2 or plan.vorschlag.leistung:
    fehler.append(f"Leistung ohne kc1.1: {plan.vorschlag}")
# Reicht die Leistung nicht einmal für 2 %, gibt es keinen Vorschlag.
plan = sw.plane(fraeser, 120, 0.05, 24, sw.Grenzen(leistung=0.5), c45)
if plan.vorschlag is not None or plan.grund != sw.GRUND_LEISTUNG:
    fehler.append(f"zu wenig Leistung: {plan.vorschlag}, {plan.grund}")

# Nur für Schaft- und Torusfräser mit D und z; fehlt etwas, bleibt der Plan leer.
for werkzeug, soll in (
    (fraeser, True),
    (wz.Werkzeug(art=wz.TORUSFRAESER, durchmesser=10, schneiden=4), True),
    (wz.Werkzeug(art=wz.RADIUSFRAESER, durchmesser=10), False),
    (wz.Werkzeug(art=wz.BOHRER, durchmesser=10, schneiden=2), False),
    (wz.Werkzeug(durchmesser=0), False),
):
    if sw.moeglich(werkzeug) != soll:
        fehler.append(f"möglich({werkzeug.art}, D {werkzeug.durchmesser}) != {soll}")
if sw.plane(fraeser, 0, 0.05, 24, sw.Grenzen()).stufen:
    fehler.append("Plan ohne vc")
if sw.plane(fraeser, 120, 0, 24, sw.Grenzen()).stufen:
    fehler.append("Plan ohne Spandicke")

# Vorbelegt aus der gewählten Zeile: vc, die Spandicke, die sie ergibt, und ap.
vollnut = wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05)
dynamisch = wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15)
if sw.vorgaben(fraeser, vollnut) != (120, 0.05, 24):
    fehler.append(f"Vorgaben Vollnut: {sw.vorgaben(fraeser, vollnut)}")
if sw.vorgaben(fraeser, dynamisch) != (120, 0.09, 25):
    fehler.append(f"Vorgaben dynamisch: {sw.vorgaben(fraeser, dynamisch)}")

# Ausgang ist die gewählte Zeile, wenn sie schruppt – sonst dynamisch vor Vollnut.
schlichten = wz.Einsatz(art=wz.SCHLICHTEN, ae=0.2, ap=25, vc=150, fz=0.04)
ohne_werte = wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25)
tabelle = [vollnut, schlichten, ohne_werte, dynamisch]
for gewaehlt, soll in (
    (vollnut, vollnut),
    (schlichten, dynamisch),
    (ohne_werte, dynamisch),
    (None, dynamisch),
):
    if sw.ausgangszeile(tabelle, gewaehlt) is not soll:
        fehler.append(f"Ausgangszeile für {gewaehlt}: {sw.ausgangszeile(tabelle, gewaehlt)}")
if sw.ausgangszeile([vollnut, schlichten], schlichten) is not vollnut:
    fehler.append("Ausgangszeile ohne dynamische Zeile")
if sw.ausgangszeile([schlichten], schlichten) is not schlichten:
    fehler.append("Ausgangszeile, wenn nichts schruppt")

# Grenzen einer Maschine aus W-001: Drehzahl der Spindel, die das Werkzeug
# antreibt (nicht die Hauptspindel der Drehmaschine), kleinster Höchstvorschub.
import beispielmaschinen  # noqa: E402

from camaddon import maschine as m  # noqa: E402

asm, ma = beispielmaschinen.drehmaschine_komplett()
if sw.grenzen_der_maschine(ma) != (4000, 0):
    fehler.append(f"ohne Antrieb und Vorschub: {sw.grenzen_der_maschine(ma)}")
dok = asm.Document
angetrieben = m.neue_betriebsart(ma, dok.getObject("Revolverachse"), m.ART_SPINDEL, "S5")
angetrieben.Drehzahl = 3000
aufnahme = next(a for a in m.aufnahmen(ma) if a.Art == m.AUFNAHME_WERKZEUG)
aufnahme.Spindel = angetrieben
for achse, vorschub in zip(
    [b for b in m.betriebsarten(ma) if b.Art == m.ART_LINEAR], (8000, 6000), strict=True
):
    achse.VorschubMax = vorschub
if sw.grenzen_der_maschine(ma) != (3000, 6000):
    fehler.append(f"mit Antrieb und Vorschub: {sw.grenzen_der_maschine(ma)}")
if ("Testdrehmaschine", 3000, 6000) not in sw.maschinen():
    fehler.append(f"Maschinen: {sw.maschinen()}")
FreeCAD.closeDocument(dok.Name)

# Vorbelegen: nur, wenn beide Felder leer sind, und nur bei genau einer Maschine.
eine = [("Fräse", 24000.0, 8000.0)]
for leer in (-1, 0):
    if sw.vorbelegung(leer, leer, eine) != (24000.0, 8000.0, "Fräse"):
        fehler.append(f"Vorbelegung: {sw.vorbelegung(leer, leer, eine)}")
if sw.vorbelegung(12000, 0, eine) != (12000, 0, ""):
    fehler.append("eingetragene Drehzahl überschrieben")
if sw.vorbelegung(-1, -1, eine * 2) != (0, 0, ""):
    fehler.append("bei zwei Maschinen vorbelegt")
if sw.vorbelegung(12000, -1, []) != (12000, 0, ""):
    fehler.append("gemerkte Drehzahl verloren")

if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
