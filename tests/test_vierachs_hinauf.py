# Rundum-Bahnen: hinauf längs der Werkzeugachse im Freivorschub (vierachs_bahn._hinauf_frei). Am
# Geist (STL) fuhr „Rundum schlichten“ 78 Stücke, zusammen gut 1 m, im Schnittvorschub nur längs
# der Werkzeugachse hinauf. Frei wird ein solches Stück, wenn es mindestens freiwege.MINDEST lang ist
# oder in ein freies übergeht – nie hinab, nie mit Drehen oder Querachse dabei, und nur, wenn über
# der Schneide nichts schmaler wird (vierachs_operation.oben_nicht_schmaler). Dazu der Zähler der
# Kehren: Dreht die Rundachse, während die Spitze quer versetzt steht, zählt als Sinken nur, was sie
# gegen das Teil längs der Werkzeugachse sinkt (Δr − q · Δφ) – der Schwenk um den Berührpunkt am
# Anfang des Schlichtens ist keine Einfahrt, ein Zickzack mit Querachse bleibt eine Kehre.
import os
import sys
from types import SimpleNamespace

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import freiwege as fw
from camaddon import vierachs_bahn as vb
from camaddon import vierachs_operation as vo
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


P = vb.Punkt
# Schneiden auf r 10, hinauf auf 30 (20 mm, frei), drehen oben im Vorschub, hinab auf 10 (nicht frei).
punkte = [
    P(True, 5.0, 40.0, 0.0, q=3.0),
    P(False, 5.0, 10.0, 0.0, q=3.0),
    P(False, 5.0, 10.0, 10.0, q=3.0),
    P(False, 5.0, 30.0, 10.0, q=3.0),
    P(False, 5.0, 30.0, 20.0, q=3.0),
    P(False, 5.0, 10.0, 20.0, q=3.0),
    # kurz hinauf (1 mm), danach im Vorschub weiter: bleibt
    P(False, 5.0, 11.0, 20.0, q=3.0),
    P(False, 5.0, 11.0, 25.0, q=3.0),
    # kurz hinauf, danach frei: wird frei
    P(False, 5.0, 12.0, 25.0, q=3.0),
    P(False, 5.0, 12.0, 60.0, q=3.0, frei=True),
    # hinauf und dabei gedreht oder quer: bleibt
    P(False, 5.0, 30.0, 61.0, q=3.0),
    P(False, 5.0, 40.0, 61.0, q=4.0),
    P(True, 5.0, 45.0, 61.0, q=4.0),
]
bahn = SimpleNamespace(punkte=list(punkte))
werte = SimpleNamespace(a_stange_vorne=100.0, form=None, fraeser_radius=2.0, hinauf_frei=False)
ohne = vb._ohne_luft_hinab(lambda netz, laengs, radial, w: bahn)
ohne(None, (1, 0, 0), (0, 0, 1), werte)
pruefe(
    [p.frei for p in bahn.punkte] == [p.frei for p in punkte], "ohne hinauf_frei: etwas geändert"
)
werte.hinauf_frei = True
ohne(None, (1, 0, 0), (0, 0, 1), werte)
frei = [p.frei for p in bahn.punkte]
soll = [False, False, False, True, False, False, False, False, True, True, False, False, False]
pruefe(frei == soll, f"frei: {frei}")
pruefe(
    all(
        (p.a, p.r, p.phi, p.q, p.eilgang) == (o.a, o.r, o.phi, o.q, o.eilgang)
        for p, o in zip(bahn.punkte, punkte, strict=True)
    ),
    "Punkte verschoben",
)
pruefe(20.0 >= fw.MINDEST > 1.0, f"MINDEST {fw.MINDEST}")
# Der Freivorschub steht im Programm: 20 mm hinauf mit 10 m/min statt 600 mm/min.
befehle = vb.befehle(bahn, (1, 0, 0), (0, 0, 1), "A", 1, 600.0, freivorschub=10000.0)
saetze = [b for b in befehle if b.Name == "G1"]
hinauf = saetze[2]  # der dritte Vorschubsatz: r 10 → 30
dauer = 1.0 / hinauf.Parameters["F"]  # s (G93, F ÷ 60)
pruefe(abs(dauer - 20.0 / (10000.0 / 60.0)) < 1e-6, f"hinauf {dauer:.3f} s")
print(ascii(f"hinauf frei: {sum(frei)} von {len(frei)} Punkten"))

# Welche Fräser dürfen?
kugel = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=4.0)
pruefe(vo.oben_nicht_schmaler(kugel), "Kugel ohne Hals")
pruefe(not vo.oben_nicht_schmaler(None), "unbekannt")
for art in (wz.LOLLIPOPFRAESER, wz.SCHWALBENSCHWANZFRAESER):
    pruefe(not vo.oben_nicht_schmaler(wz.Werkzeug(nummer=3, art=art, durchmesser=6.0)), art)
hals = wz.Werkzeug(nummer=4, art=wz.KUGELFRAESER, durchmesser=4.0, hals_d=3.6, hals_laenge=10.0)
pruefe(not vo.oben_nicht_schmaler(hals), "mit Hals")
dick = wz.Werkzeug(nummer=5, art=wz.SCHAFTFRAESER, durchmesser=4.0, schaft=6.0)
pruefe(vo.oben_nicht_schmaler(dick), "Schaft dicker als die Schneide")
duenn = wz.Werkzeug(nummer=6, art=wz.PLANFRAESER, durchmesser=50.0, schaft=22.0)
pruefe(not vo.oben_nicht_schmaler(duenn), "Planfräser auf dünnerem Schaft")

# Kehren: der Schwenk am Anfang des Schlichtens am Geist (Programm, Sätze 8–12) – quer um
# q = −11,5 versetzt, die Rundachse dreht, r fällt, die Spitze bleibt am Teil.
schwenk = [P(True, 3.0, 44.5, 15.0, q=-11.517), P(True, 3.0, 5.88, 15.0, q=-11.517)]
for phi, r in ((15.0, 0.326), (17.5, -0.139), (19.5, -0.515), (21.0, -0.800), (22.5, -1.087)):
    schwenk.append(P(False, 3.0, r, phi, q=-11.517))
kehren, rampen = vb.kehren(schwenk)  # die Rampe: senkrecht hinab (ohne Richtung)
pruefe((kehren, rampen) == (0, 1), f"Schwenk: {kehren} Kehren, {rampen} Rampen")
# Ein Zickzack mit Querachse (Rundachse steht): bleibt eine Kehre.
zickzack = [P(True, 0.0, 30.0, 0.0, q=2.0), P(True, 0.0, 20.0, 0.0, q=2.0)]
zickzack.append(P(False, 0.0, 10.0, 0.0, q=2.0))
for k, a in enumerate((5.0, 0.0, 5.0)):
    zickzack.append(P(False, a, 9.0 - k, 0.0, q=2.0))
kehren, rampen = vb.kehren(zickzack)
pruefe((kehren, rampen) == (1, 1), f"Zickzack: {kehren} Kehren, {rampen} Rampen")
# Dasselbe Zickzack rundum (q = 0, die Rundachse dreht hin und her): auch.
rundum = [P(True, 0.0, 30.0, 0.0), P(True, 0.0, 20.0, 0.0), P(False, 0.0, 10.0, 0.0)]
for k, phi in enumerate((10.0, 0.0, 10.0)):
    rundum.append(P(False, 0.0, 9.0 - k, phi))
kehren, rampen = vb.kehren(rundum)
pruefe((kehren, rampen) == (1, 1), f"Zickzack rundum: {kehren} Kehren, {rampen} Rampen")

if fehler:
    print("FEHLER:")
    for f in fehler:
        print(" -", f)
    sys.exit(1)
print("OK", os.path.basename(__file__))
