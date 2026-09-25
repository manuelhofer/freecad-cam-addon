# Einstieg für KI-Assistenten

Startpunkt für **jede KI und jedes Werkzeug** an diesem Projekt – Claude Code,
Cursor, Copilot, Aider oder ein beliebiger Chat.

**Lies diese Datei ganz. Danach nur das, was zu deiner Aufgabe passt – nicht
alles.**

---

## 1. Was das Projekt ist

Ein **FreeCAD-Addon**, das die **CAM-Oberfläche** bedienbarer macht. Manuel
beschreibt, was ihn stört und wie er es gern hätte („das hätte ich gern so und
so"), die KI setzt es um, Manuel testet es in FreeCAD.

Reines Python mit PySide (Qt), aufgesetzt auf die Python-API von FreeCAD und
der CAM-Workbench. Kein eigener C++-Code.

**Drei Festlegungen, die alles andere bestimmen:**

- **Immer der aktuelle Wochen-Build von FreeCAD** (Entwicklerversion, nicht
  die letzte stabile). Keine Rücksicht auf ältere Versionen, keine
  Kompatibilitätsschichten.
- **Betriebssystem egal.** Der Code läuft überall, wo FreeCAD läuft – keine
  Pfade, Shell-Aufrufe oder Bibliotheken, die an ein System gebunden sind.
- **Maschine egal.** Das Addon verbessert die Bedienung, es kennt keine
  bestimmte Fräse und keinen bestimmten Postprozessor.

## 2. Die vier Regeln, die immer gelten

**Verbindlich und vollständig ist [docs/arbeitsregeln.md](docs/arbeitsregeln.md)**
– lies die, bevor du etwas änderst; besprechbar ist jede davon, und der
Arbeitsweg überhaupt (Abschnitt 0).
Hier stehen nur die vier, bei denen ein Verstoß nicht mehr zu reparieren ist:

- **1 Patch = 1 Thema** mit **einem** Akzeptanzkriterium in einem Satz.
- **Patch-ID im Commit-Betreff** (`P-YYYY-MM-DD-XX kurzbeschreibung`), dazu ein
  Eintrag in `docs/archiv/DEV_PROMPT_HISTORY.md` im **selben** Commit.
- **Keine Refactors nebenbei.** Was auffällt, wird notiert, nicht mitgemacht.
- **Gepusht wird nur auf ausdrückliche Ansage.**

## 3. Lesekarte – was liest du wann?

**Immer, vor jeder Änderung – diese drei Zeilen, mehr nicht:**

| Datei | Wofür |
| --- | --- |
| [docs/arbeitsregeln.md](docs/arbeitsregeln.md) | Wie gearbeitet wird |
| [docs/STATUS_SNAPSHOT.md](docs/STATUS_SNAPSHOT.md) | Der ganze Stand: nächster Schritt, Wunschliste, offene Bugs |
| `git log --oneline -20` | Was zuletzt passiert ist |

**Je nach Thema – nur das Passende:** Die Tabelle wächst mit dem Projekt. Jede
neue Spezifikation unter `docs/` bekommt hier eine Zeile.

| Du arbeitest an … | Dann lies |
| --- | --- |
| W-001 Maschine aus Baugruppe (Achsen, Betriebsarten, Export) | [docs/spezifikation_maschine_aus_baugruppe.md](docs/spezifikation_maschine_aus_baugruppe.md) |
| Prüfungen ohne Fenster, Testumgebung | `scripts/testumgebung_einrichten.sh`, dann `scripts/tests_ausfuehren.sh` – Aufbau einer Prüfung: `tests/test_umgebung.py` |

`docs/archiv/DEV_PROMPT_HISTORY.md` ist **keine Startlektüre** – ein Eintrag je
Patch. Nur gezielt aufschlagen (`grep -n "P-2026-09-25-01"`), nie am Stück.

## 4. Was du nicht lesen musst

Diese Dinge stehen im Code und sind dort **immer** aktuell – frag lieber das
Repository als eine Dokumentation:

- **Welche Patches es gab** → `git log --oneline`
- **Welche Befehle das Addon anmeldet** → `grep -rn "addCommand" .`
- **Wie FreeCAD selbst etwas macht** → der Quelltext der CAM-Workbench im
  FreeCAD-Repository (`src/Mod/CAM/`), nicht die Erinnerung an ältere Versionen.
