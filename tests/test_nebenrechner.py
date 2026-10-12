# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Nebenrechner (T-006): Arbeiter starten, rechnen auf mehreren Kernen, lösen die
Platzhalter auf (Form, Dokument, Gemeinsam, Fortschritt), melden Fehler als Traceback, lassen
sich abbrechen und enden mit dem Pool. Rechnet nur Kleinigkeiten – Sekunden, nicht Minuten."""

import contextlib
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
# Wiederverwenden (P-2026-10-11-08): dieselbe Kopie, solange sich das Dokument nicht ändert.
kopie3 = pool.kopie(doc, wiederverwenden=True)
assert pool.kopie(doc, wiederverwenden=True) == kopie3, "unverändert neu gespeichert"
assert pool.kopie(doc) != kopie3, "ohne wiederverwenden nicht neu gespeichert"
kopie4 = pool.kopie(doc, wiederverwenden=True)
objekt.Label = "Umbenannt"
kopie5 = pool.kopie(doc, wiederverwenden=True)
objekt.Shape = Part.makeBox(1, 2, 7)
kopie6 = pool.kopie(doc, wiederverwenden=True)
doc.recompute()
assert kopie5 != kopie4 and kopie6 != kopie5, (kopie4, kopie5, kopie6)
(volumen,) = pool.warten([pool.auftrag("nebenrechner", "_probe_dokument", kopie6, "Kasten")])
assert abs(volumen - 14.0) < 1e-9, volumen
# Speicher (P-2026-10-11-100): Eine große Kopie öffnen nur so viele Arbeiter, wie der Speicher
# trägt – einer hat sie schon offen, der Speicher reicht für einen zweiten; die übrigen Aufträge
# warten auf diese beiden, der dritte Arbeiter öffnet sie nicht.
frei = nr.speicher_frei()
assert frei is None or frei < os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"), frei
groesse = 100 * 2**20
bedarf_vorher = nr.kopie_bedarf
nr.kopie_bedarf = lambda pfad: groesse if pfad == kopie6.pfad else bedarf_vorher(pfad)
pool.speicher = lambda: 1.5 * groesse
try:
    auftraege = [
        pool.auftrag("nebenrechner", "_probe_dokument", kopie6, "Kasten", dauer=0.3)
        for _ in range(6)
    ]
    assert [round(v, 9) for v in pool.warten(auftraege)] == [14.0] * 6
    offen = [a.nummer for a in pool._arbeiter if kopie6.pfad in a.dokumente]
    assert len(offen) == 2, f"die große Kopie öffneten {offen} (von {pool.arbeiter} Arbeitern)"
    # Reicht der Speicher für keinen, rechnet trotzdem einer – sonst rechnete nie einer.
    pool.speicher = lambda: 0
    neu = pool.kopie(doc)
    nr.kopie_bedarf = lambda pfad: groesse
    (volumen,) = pool.warten([pool.auftrag("nebenrechner", "_probe_dokument", neu, "Kasten")])
    assert abs(volumen - 14.0) < 1e-9, volumen
finally:
    nr.kopie_bedarf = bedarf_vorher
    pool.speicher = nr.speicher_frei
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
# Höchstens GEMEINSAM_IM_POOL gemeinsame Daten (P-2026-10-11-19): die ältesten gehen, was ein
# wartender Auftrag braucht, bleibt.
grenze, nr.GEMEINSAM_IM_POOL = nr.GEMEINSAM_IM_POOL, 3
platzhalter = [pool.gemeinsam(f"viele-{k}", [k] * 10) for k in range(5)]
assert list(pool._gemeinsam)[-3:] == ["viele-2", "viele-3", "viele-4"], list(pool._gemeinsam)
assert len(pool._gemeinsam) == 3, list(pool._gemeinsam)
assert pool.warten([pool.auftrag("nebenrechner", "_probe_summe", platzhalter[4], 1)]) == [40]
nr.GEMEINSAM_IM_POOL = grenze
for k in range(5):
    pool.vergessen(f"viele-{k}")

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
# Was sich nicht senden lässt, scheitert im Unterpool wie im Pool – beim Warten, nicht beim
# Bestellen; der Arbeiter bleibt.
assert pool.warten([pool.auftrag("nebenrechner", "_probe_nicht_senden")]) == [True]
arbeiter_vorher = pool.arbeiter
try:
    pool.warten([pool.auftrag("nebenrechner", "_probe", lambda: 1)])
except nr.Fehler as fehler:
    assert "Senden" in str(fehler), str(fehler)
else:
    raise AssertionError("ungepickelt gesendet")
assert pool.arbeiter == arbeiter_vorher, (pool.arbeiter, arbeiter_vorher)
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
# Was die Ausnahme fürs Fachliche mitbringt (ihr Feld „daten“), kommt mit (P-2026-10-11-65).
auftrag = pool.auftrag("nebenrechner", "_probe_fehler", {"ausspannen": (32.0, 42.4)})
with contextlib.suppress(nr.Fehler):
    pool.warten([auftrag])
assert auftrag.fehlerdaten == {"ausspannen": (32.0, 42.4)}, auftrag.fehlerdaten

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

# Vorwärmen (P-2026-10-11-13): Jeder Arbeiter lädt die Module, bevor ein Auftrag sie braucht –
# auch einer, der erst danach startet.
pool.beenden()
pool.vorwaermen(["vierachs_huelle"])
assert pool.arbeiter == pool.anzahl, pool.arbeiter
auftraege = [
    pool.auftrag("nebenrechner", "_probe_geladen", "vierachs_huelle", 0.5) for _ in range(3)
]
assert pool.warten(auftraege) == [True, True, True]

# Speicher zurückgeben (2026-10-12): Nach einem Auftrag, der viel belegt und wieder freigibt,
# gibt der Arbeiter es dem System zurück (glibc behielte es – am Geist 1,8 GB je Arbeiter).
if sys.platform.startswith("linux"):
    einer = nr.Nebenrechner(anzahl=1)
    (danach,) = einer.warten([einer.auftrag("nebenrechner", "_probe_speicher", 1500)])
    (spaeter,) = einer.warten([einer.auftrag("nebenrechner", "_probe_belegt")])
    einer.beenden()
    assert danach > 1000 and spaeter < danach - 800, f"belegt {danach:.0f} → {spaeter:.0f} MB"

# Beenden: keine Arbeiter mehr, der Ordner ist weg; danach geht es wieder.
ordner = pool._ordner
pids = [a.prozess for a in pool._arbeiter]
pool.beenden()
assert pool.arbeiter == 0 and not os.path.exists(ordner)
assert all(p.poll() is not None for p in pids), "ein Arbeiter lebt nach beenden() weiter"
assert pool.warten([pool.auftrag("nebenrechner", "_probe", 8)]) == [64]
pool.beenden()
print("OK", os.path.basename(__file__))
