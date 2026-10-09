# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Kollision in Stücken auf den Nebenrechnern (T-006, kollision_parallel): dieselben Befunde
wie in einem Lauf – an der Beispiel-Fräse mit dem Taschenteil aus test_kollision, einer Bahn, die
an der Wand entlang, im Eilgang durchs Teil und über das Rohteil fährt; mit Vorlauf (ein Eilgang
auf einem Vorschubweg der Operation ist kein Befund, auch wenn das Stück mitten darin beginnt),
Abbrechen über den Fortschritt und Rückfall ohne Nebenrechner. Kleine Bahn, Sekunden."""

import os
import pathlib
import pickle
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import FreeCAD
import Part
import Path.Main.Job as PathJob
import Path.Op.Custom as PathCustom

from camaddon import abfahren as ab
from camaddon import beispielmaschine, sprache
from camaddon import kollision as kb
from camaddon import nebenrechner as nr
from camaddon import reichweite as rw
from camaddon import werkzeuge as wz

sprache.setze_sprache("de")
asm, ma = beispielmaschine.fraesmaschine()
p = rw.Pruefung(asm, ma)
teil = FreeCAD.newDocument("Teil")
koerper = teil.addObject("Part::Feature", "Taschenteil")
koerper.Shape = Part.makeBox(100, 60, 20).cut(Part.makeBox(40, 30, 15, FreeCAD.Vector(30, 15, 5)))
teil.recompute()
job = PathJob.Create("Job", [koerper])
op = PathCustom.Create("Eigene")
teil.recompute()
nullpunkt = rw.vorschlag_nullpunkt(job)
werkzeug = wz.Werkzeug(
    nummer=1, durchmesser=5.0, schneidenlaenge=5.0, gesamtlaenge=50.0, schaft=4.0
)
bibliothek = wz.Bibliothek([werkzeug])
bibliothek.halter_vorschlagen = False

# Eine Bahn mit mehreren Befunden und einem Eilgang auf dem eigenen Vorschubweg: an der Wand
# (Schaft Ø 4: 0,5 mm Warnung), Eilgang durchs Teil (Berührung), Rückzug vom Boden (keiner),
# Wiedereinstieg auf dem Vorschubweg hinab (keiner), Eilgang über dem Rohteil in die Tasche.
bahn = ["G0 X50 Y30 Z30", "G1 Z8 F10", "G1 X67.5", "G1 X50", "G1 Z5", "G0 Z30", "G0 Z5"]
bahn += [f"G1 X{50 + k * 0.25:.2f} F10" for k in range(1, 60)]  # viele Stationen am Boden
bahn += ["G0 Z30", "G0 X10 Y30", "G0 Z25", "G1 Z19 F10", "G0 X50", "G0 Z30"]
op.Gcode = bahn
teil.recompute()
fahrt = ab.abfahrt(p, job, nullpunkt, bibliothek)
assert len(fahrt.stationen) >= kb.PARALLEL_AB, len(fahrt.stationen)


def gemeldet(ergebnis):
    return sorted(
        (b.operation, b.a, b.b, b.beruehrung, b.eilgang, round(b.abstand, 6), round(b.zeit, 6))
        for b in ergebnis.befunde
    )


# Die Daten lassen sich pickeln – so kommen sie zu den Nebenrechnern.
daten = kb.vorbereiten(fahrt, job, bibliothek, kb.Ergebnis(1.0), nullpunkt)
pickle.dumps(daten.zum_senden())
pickle.dumps(kb.fahrtdaten(fahrt))

einzeln = kb.kollision(fahrt, job, nullpunkt, bibliothek, 1.0, rohteil=True)
assert einzeln.befunde, "die Bahn muss Befunde haben"
pool = nr.Nebenrechner(anzahl=3)
assert pool.verfuegbar()
fortschritte = []
verteilt = kb.kollision_parallel(
    fahrt, job, nullpunkt, bibliothek, 1.0, fortschritte.append, rohteil=True, nebenrechner=pool
)
assert pool.in_arbeit >= 2, f"nur {pool.in_arbeit} Stücke in Arbeitern"
assert gemeldet(verteilt) == gemeldet(einzeln), f"\n{gemeldet(verteilt)}\n!=\n{gemeldet(einzeln)}"
assert [b.text() for b in verteilt.befunde] == [b.text() for b in einzeln.befunde]
assert verteilt.stellen >= einzeln.stellen * 0.9, (verteilt.stellen, einzeln.stellen)
assert sorted(map(str, verteilt.hinweise)) == sorted(map(str, einzeln.hinweise)), (
    verteilt.hinweise,
    einzeln.hinweise,
)
assert all(b.stelle is None or isinstance(b.stelle, FreeCAD.Vector) for b in verteilt.befunde)
assert (
    fortschritte
    and fortschritte[-1] == 1.0
    and all(a <= b + 1e-9 for a, b in zip(fortschritte, fortschritte[1:], strict=False))
), fortschritte

# Kleine Stücke – jede Grenze mitten in der Operation: der Vorlauf kennt die Vorschubwege.
kb_stueck, kb.STUECK_MINDESTENS = kb.STUECK_MINDESTENS, 3
try:
    viele = kb.kollision_parallel(
        fahrt, job, nullpunkt, bibliothek, 1.0, rohteil=True, nebenrechner=pool
    )
finally:
    kb.STUECK_MINDESTENS = kb_stueck
assert gemeldet(viele) == gemeldet(einzeln), f"\n{gemeldet(viele)}\n!=\n{gemeldet(einzeln)}"
assert pool.in_arbeit >= 12, pool.in_arbeit

# Die Maschine darf verfahren sein: Die Kopie geht in der Grundstellung hinaus, danach steht sie
# wieder, wo sie stand.
achse = fahrt.achsen[0]
p.verfahren.setze(achse, p.verfahren.stellung(achse) + 7.0)
stellung = p.verfahren.stellung(achse)
bewegt = kb.kollision_parallel(fahrt, job, nullpunkt, bibliothek, 1.0, nebenrechner=pool)
assert abs(p.verfahren.stellung(achse) - stellung) < 1e-9
p.verfahren.grundstellung()
ohne_rohteil = [b for b in einzeln.befunde if b.ins_rohteil == 0]
assert gemeldet(bewegt) == gemeldet(kb.Ergebnis(1.0, ohne_rohteil)), gemeldet(bewegt)

# Abbrechen über den Fortschritt: ein Ergebnis „abgebrochen“, keine Befunde, keine Arbeiter mehr
# an der Arbeit; danach rechnet der Pool weiter.
abgebrochen = kb.kollision_parallel(
    fahrt, job, nullpunkt, bibliothek, 1.0, lambda anteil: False, nebenrechner=pool
)
assert abgebrochen.abgebrochen and not abgebrochen.befunde
assert not pool.offen()
wieder = kb.kollision_parallel(fahrt, job, nullpunkt, bibliothek, 1.0, nebenrechner=pool)
assert gemeldet(wieder) == gemeldet(kb.Ergebnis(1.0, ohne_rohteil))

# Ohne Nebenrechner (ein Arbeiter) rechnet kollision_parallel im eigenen Prozess – dasselbe.
allein = nr.Nebenrechner(anzahl=1)
selbst = kb.kollision_parallel(
    fahrt, job, nullpunkt, bibliothek, 1.0, rohteil=True, nebenrechner=allein
)
assert allein.in_arbeit == 0 and gemeldet(selbst) == gemeldet(einzeln)
pool.beenden()
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)
print("OK", os.path.basename(__file__))
