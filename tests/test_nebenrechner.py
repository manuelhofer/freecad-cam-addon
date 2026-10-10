# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Nebenrechner (T-006): Arbeiter starten, rechnen auf mehreren Kernen, lösen die
Platzhalter auf (Form, Dokument, Gemeinsam, Fortschritt), melden Fehler als Traceback, lassen
sich abbrechen und enden mit dem Pool. Rechnet nur Kleinigkeiten – Sekunden, nicht Minuten."""

import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import FreeCAD
import Part

from camaddon import nebenrechner as nr

assert nr.freecadcmd_pfad(), "FreeCADCmd nicht gefunden – neben FreeCAD muss es liegen"
pool = nr.Nebenrechner(anzahl=3)
assert pool.verfuegbar()

# Ein Auftrag, blockierend gewartet.
assert pool.warten([pool.auftrag("nebenrechner", "_probe", 7)]) == [49]
assert pool.arbeiter == 1 and pool.in_arbeit == 1

# Drei Aufträge zugleich: drei Arbeiter, und die Zeit ist die eines Auftrags, nicht dreier.
beginn = time.monotonic()
auftraege = [pool.auftrag("nebenrechner", "_probe", i, dauer=1.0) for i in range(3)]
assert pool.warten(auftraege) == [0, 1, 4]
dauer = time.monotonic() - beginn
assert pool.arbeiter == 3, pool.arbeiter
assert dauer < 2.5, f"drei Aufträge je 1 s brauchten {dauer:.1f} s – nicht parallel"

# Eine Gruppe mit höchstens zwei zugleich (P-2026-10-10-63): drei Aufträge je 1 s brauchen zwei
# Runden, obwohl drei Arbeiter frei sind.
beginn = time.monotonic()
with pool.gruppe("probe", 2):
    auftraege = [pool.auftrag("nebenrechner", "_probe", i, dauer=1.0) for i in range(3)]
assert all(a.gruppe == "probe" and a.gleichzeitig == 2 for a in auftraege)
assert pool.warten(auftraege) == [0, 1, 4]
dauer = time.monotonic() - beginn
assert 1.9 < dauer < 3.5, f"höchstens zwei zugleich: {dauer:.1f} s"
assert nr.physische_kerne() >= 1

# Fortschritt: die Funktion meldet ihn, der Auftrag kennt ihn, der Rückruf kommt.
gemeldet = []
auftrag = pool.auftrag("nebenrechner", "_probe", 3, dauer=0.6, fortschritt=nr.Fortschritt())
auftrag.bei_fortschritt = lambda a: gemeldet.append(a.fortschritt)
fertig = []
auftrag.bei_fertig = fertig.append
assert pool.warten([auftrag]) == [9]
assert gemeldet and gemeldet[-1] == 1.0 and fertig == [auftrag], (gemeldet, fertig)
assert nr.fortschritt_von([auftrag]) == 1.0

# Eine Form kommt als BREP-Text hin und als Form an.
kasten = Part.makeBox(2, 3, 4)
(volumen,) = pool.warten([pool.auftrag("nebenrechner", "_probe_form", nr.Form.von(kasten))])
assert abs(volumen - 24.0) < 1e-9, volumen

# Eine Dokumentkopie: der Arbeiter öffnet sie – auch von einem nie gespeicherten Dokument.
doc = FreeCAD.newDocument("NebenrechnerProbe")
objekt = doc.addObject("Part::Feature", "Kasten")
objekt.Shape = Part.makeBox(1, 2, 5)
doc.recompute()
kopie = pool.kopie(doc)
assert os.path.isfile(kopie.pfad)
(volumen,) = pool.warten([pool.auftrag("nebenrechner", "_probe_dokument", kopie, "Kasten")])
assert abs(volumen - 10.0) < 1e-9, volumen
# Dieselbe Kopie noch einmal: bleibt offen (schnell), eine neue Kopie nach einer Änderung zählt.
objekt.Shape = Part.makeBox(1, 2, 6)
doc.recompute()
kopie2 = pool.kopie(doc)
assert kopie2.pfad != kopie.pfad
ergebnisse = pool.warten(
    [
        pool.auftrag("nebenrechner", "_probe_dokument", kopie, "Kasten"),
        pool.auftrag("nebenrechner", "_probe_dokument", kopie2, "Kasten"),
    ]
)
assert [round(v, 9) for v in ergebnisse] == [10.0, 12.0], ergebnisse
FreeCAD.closeDocument(doc.Name)

# Gemeinsame Daten: einmal je Arbeiter, in Argumenten auch verschachtelt.
zahlen = pool.gemeinsam("zahlen", list(range(1000)))
auftraege = [pool.auftrag("nebenrechner", "_probe_summe", zahlen, faktor=k) for k in (1, 2, 3)]
assert pool.warten(auftraege) == [499500, 999000, 1498500]
auftraege = [pool.auftrag("nebenrechner", "_probe_summe", [nr.Gemeinsam("zahlen")][0], 1)]
assert pool.warten(auftraege) == [499500]
# Derselbe Schlüssel noch einmal: der alte Wert bleibt, nichts geht noch einmal hin.
assert pool.gemeinsam("zahlen", []) == nr.Gemeinsam("zahlen")
assert pool.warten([pool.auftrag("nebenrechner", "_probe_summe", zahlen, 1)]) == [499500]
# Vergessen: die Arbeiter geben die Daten frei, ein Auftrag damit bekommt sie wieder.
pool.vergessen("zahlen")
zahlen = pool.gemeinsam("zahlen", list(range(10)))
assert pool.warten([pool.auftrag("nebenrechner", "_probe_summe", zahlen, 1)]) == [45]
# Unteraufträge (P-2026-10-11-07): Ein Arbeiter verteilt selbst – über diesen Pool. Drei je 1 s
# auf drei Arbeitern brauchen eine Sekunde, nicht drei.
assert pool.warten([pool.auftrag("nebenrechner", "_probe_verfuegbar")]) == [True]
beginn = time.monotonic()
(summe,) = pool.warten([pool.auftrag("nebenrechner", "_probe_verschachtelt", [1, 2, 3], dauer=1.0)])
dauer = time.monotonic() - beginn
assert summe == 14 and dauer < 2.5, (summe, f"{dauer:.1f} s – Unteraufträge nicht parallel")
# Alle Arbeiter warten auf ihre Unteraufträge: Jeder rechnet seine selbst – nichts hängt.
auftraege = [
    pool.auftrag("nebenrechner", "_probe_verschachtelt", [k, k], dauer=0.3) for k in range(3)
]
assert pool.warten(auftraege) == [0, 2, 8]
assert pool.warten([pool.auftrag("nebenrechner", "_probe_tief", 4)]) == [16]
# Gemeinsame Daten, die der Arbeiter angelegt hat.
auftrag = pool.auftrag("nebenrechner", "_probe_gemeinsam_verschachtelt", list(range(100)))
assert pool.warten([auftrag]) == [[4950, 9900]]
# Ein Fehler im Unterauftrag scheitert beim Besteller – mit dem Traceback von dort.
try:
    pool.warten([pool.auftrag("nebenrechner", "_probe_verschachtelt", [1], fehler=True)])
except nr.Fehler as fehler:
    assert "ValueError: absichtlich" in str(fehler), str(fehler)
else:
    raise AssertionError("Fehler im Unterauftrag nicht gemeldet")
# Abbrechen: Was er bestellt hat, fällt mit; danach rechnet der Pool weiter.
lang = pool.auftrag("nebenrechner", "_probe_verschachtelt", list(range(12)), dauer=1.0)
beginn = time.monotonic()
while not any(a.eltern is lang for a in pool._warteschlange) and time.monotonic() - beginn < 30:
    pool.abfragen()
    time.sleep(0.02)
assert any(a.eltern is lang for a in pool._warteschlange), "keine Unteraufträge bestellt"
lang.abbrechen()
assert not any(a.eltern is not None for a in pool._warteschlange), pool._warteschlange
assert pool.warten([pool.auftrag("nebenrechner", "_probe", 6)]) == [36]

# Ein Fehler im Arbeiter kommt als Traceback – der Arbeiter lebt weiter.
try:
    pool.warten([pool.auftrag("nebenrechner", "_probe_fehler")])
except nr.Fehler as fehler:
    assert "ValueError: absichtlich" in str(fehler), str(fehler)
    assert (fehler.art, fehler.satz) == ("ValueError", "absichtlich"), (fehler.art, fehler.satz)
else:
    raise AssertionError("Fehler im Arbeiter nicht gemeldet")
assert pool.warten([pool.auftrag("nebenrechner", "_probe", 2)]) == [4]

# Abbrechen: ein langer Auftrag endet sofort, sein Arbeiter ist weg, ein neuer rechnet weiter.
lang = pool.auftrag("nebenrechner", "_probe", 1, dauer=60.0)
kurz = pool.auftrag("nebenrechner", "_probe", 5)
pool.warten([kurz])
beginn = time.monotonic()
lang.abbrechen()
assert lang.abgebrochen and lang.erledigt
try:
    pool.warten([lang])
except nr.Abgebrochen:
    pass
else:
    raise AssertionError("abgebrochener Auftrag gilt als fertig")
assert pool.warten([pool.auftrag("nebenrechner", "_probe", 6)]) == [36]
assert time.monotonic() - beginn < 10

# warten() mit `zwischendurch`: wird gerufen; False bricht ab.
rufe = []


def zwischendurch():
    rufe.append(1)
    return len(rufe) < 5


try:
    pool.warten([pool.auftrag("nebenrechner", "_probe", 1, dauer=30.0)], zwischendurch)
except nr.Abgebrochen:
    pass
else:
    raise AssertionError("zwischendurch=False hat nicht abgebrochen")
assert len(rufe) == 5, rufe

# Beenden: keine Arbeiter mehr, der Ordner ist weg; danach geht es wieder.
ordner = pool._ordner
pids = [a.prozess for a in pool._arbeiter]
pool.beenden()
assert pool.arbeiter == 0 and not os.path.exists(ordner)
assert all(p.poll() is not None for p in pids), "ein Arbeiter lebt nach beenden() weiter"
assert pool.warten([pool.auftrag("nebenrechner", "_probe", 8)]) == [64]
pool.beenden()
print("OK", os.path.basename(__file__))
