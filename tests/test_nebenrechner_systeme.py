# Prüft, was die Nebenrechner vom Betriebssystem lesen (nebenrechner, nebenrechner_arbeiter): Unter
# Linux den Speicher eines Prozesses und den freien Speicher aus /proc; die Wege für Windows
# (Working Set, GlobalMemoryStatusEx, der Griff des Hauptprozesses für den Wachhund) und macOS
# (libproc, sysctl, vm_stat) scheitern hier still mit None – auf ihrem System lesen sie dasselbe.
# Die Ausgabe von vm_stat (macOS) wird richtig gelesen: frei + inaktiv + spekulativ + löschbar,
# mal der Seitengröße aus der Kopfzeile.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import nebenrechner as nr
from camaddon import nebenrechner_arbeiter as na

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


if sys.platform.startswith("linux"):
    belegt = nr._belegt_von(os.getpid())
    pruefe(belegt is not None and belegt > 10 * 2**20, f"belegt: {belegt}")
    pruefe(nr.belegt_mb() is not None and nr.belegt_mb() > 10, f"belegt_mb: {nr.belegt_mb()}")
    pruefe(nr.speicher_frei() is not None, "speicher_frei: None unter Linux")
    pruefe(nr._belegt_windows(os.getpid()) is None, "Windows-Weg liefert unter Linux etwas")
    pruefe(nr._belegt_mac(os.getpid()) is None, "macOS-Weg liefert unter Linux etwas")
    pruefe(nr._speicher_windows() is None, "GlobalMemoryStatusEx unter Linux")
    pruefe(nr._speicher_mac() is None, "vm_stat unter Linux")
    pruefe(na._eltern_lebt_windows(os.getppid()) is None, "Wachhund-Griff unter Linux")

AUSGABE = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               12000.
Pages active:                            400000.
Pages inactive:                           30000.
Pages speculative:                         5000.
Pages throttled:                              0.
Pages wired down:                        150000.
Pages purgeable:                           3000.
"""
pruefe(
    nr._vm_stat_verfuegbar(AUSGABE) == (12000 + 30000 + 5000 + 3000) * 16384,
    f"vm_stat: {nr._vm_stat_verfuegbar(AUSGABE)}",
)
pruefe(nr._vm_stat_verfuegbar("kaputt") is None, "vm_stat ohne Kopfzeile")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
