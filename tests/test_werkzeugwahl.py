# Prüft werkzeugwahl (Plan C2): eine Tasche 60 × 40, 15 tief, senkrechte Ecken R 5, Boden eben.
# 1. masse: Tiefe 15, freier Kreis Ø ≈ 40, kleinster Innenradius 5.
# 2. vorschlaege mit eigenen Werkzeugen (Bohrer Ø 10/20/38, 38 nur 10 mm Schneide; Fräser Ø 12/28)
#    und einem kleinen Katalog: vorbohren der eigene Ø 20 (Ø 38 ist zu kurz), aus dem Katalog der
#    größere Ø 36; schruppen der eigene Ø 28 (bis 80 % des freien Kreises); ecken (bis Ø 10) nichts Eigenes, aus dem Katalog Ø 10
#    und Ø 8; bohrfraesen nur der Fräser, der laut Hersteller helikal ins Volle darf (Ø 25, Fenster
#    Ø 30–45 um den freien Kreis; der mit Fenster ab Ø 50 nicht); tauchfraesen nur der Tauchfräser
#    (Ø 32 im Katalog, kein eigener; der Ø 50 passt nicht in den freien Kreis).
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from camaddon import werkzeuge as wz  # noqa: E402
from camaddon import werkzeugwahl as ww  # noqa: E402

V = FreeCAD.Vector
fehler = []

tasche = Part.makeBox(60, 40, 15, V(20, 20, 25))
senkrecht = [e for e in tasche.Edges if abs(e.BoundBox.ZLength - 15) < 1e-6]
tasche = tasche.makeFillet(5, senkrecht)
form = Part.makeBox(100, 80, 40).cut(tasche)
namen = [
    f"Face{i + 1}"
    for i, f in enumerate(form.Faces)
    if f.BoundBox.XMin >= 20 - 1e-6 and f.BoundBox.XMax <= 80 + 1e-6 and f.BoundBox.ZMax <= 40
    and f.BoundBox.YMin >= 20 - 1e-6 and f.BoundBox.YMax <= 60 + 1e-6 and f.BoundBox.ZMin >= 25 - 1e-6
]  # fmt: skip
m = ww.masse(form, namen)
if abs(m.tiefe - 15) > 1e-6:
    fehler.append(f"Tiefe {m.tiefe}")
if not 38 <= m.frei <= 40 + 1e-6:
    fehler.append(f"freier Kreis {m.frei}")
if abs(m.innenradius - 5) > 1e-6:
    fehler.append(f"Innenradius {m.innenradius}")


def werkzeug(art, d, schneide=30.0, **faehig):
    w = wz.Werkzeug(art=art, durchmesser=d, schneidenlaenge=schneide, gesamtlaenge=80.0)
    w.faehigkeiten = dict(faehig)
    return w


eigene = [
    werkzeug(wz.BOHRER, 10),
    werkzeug(wz.BOHRER, 20),
    werkzeug(wz.BOHRER, 38, schneide=10),
    werkzeug(wz.SCHAFTFRAESER, 12),
    werkzeug(wz.SCHAFTFRAESER, 28),
]
katalog = [
    werkzeug(wz.BOHRER, 36),
    werkzeug(wz.BOHRER, 30, wendeplatten=True, bohrverwendung=["brillenbohrung"]),
    werkzeug(wz.SCHAFTFRAESER, 25, bohrfraesen=True, helix_d_min=30.0, helix_d_max=45.0),
    werkzeug(wz.SCHAFTFRAESER, 26, bohrfraesen=True, helix_d_min=50.0, helix_d_max=60.0),
    werkzeug(wz.BOHRER, 25, wendeplatten=True),
    werkzeug(wz.SCHAFTFRAESER, 10),
    werkzeug(wz.KUGELFRAESER, 8),
    werkzeug(wz.SCHAFTFRAESER, 32, tauchfraesen=True),
    werkzeug(wz.SCHAFTFRAESER, 50, tauchfraesen=True),
]
v = {x.weg: x for x in ww.vorschlaege(m, eigene, katalog)}
vb = v.get("vorbohren")
if vb is None or vb.eigenes.durchmesser != 20 or [w.durchmesser for w in vb.katalog] != [36]:
    fehler.append(f"vorbohren: {vb}")
sr = v.get("schruppen")
if sr is None or sr.eigenes.durchmesser != 28:
    fehler.append(f"schruppen: {sr}")
ec = v.get("ecken")
if ec is None or ec.eigenes is not None or [w.durchmesser for w in ec.katalog] != [10, 8]:
    fehler.append(f"ecken: {ec}")
bf = v.get("bohrfraesen")
if bf is None or [w.durchmesser for w in bf.katalog] != [25]:
    fehler.append(f"bohrfraesen: {bf}")
tf = v.get("tauchfraesen")
if tf is None or tf.eigenes is not None or [w.durchmesser for w in tf.katalog] != [32]:
    fehler.append(f"tauchfraesen: {tf}")

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
