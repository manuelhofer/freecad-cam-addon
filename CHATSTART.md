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

**Vier Festlegungen, die alles andere bestimmen:**

- **Bedienbarkeit geht vor allem.** Auf dem Bildschirm darf keine Frage
  aufkommen: Alles ist selbsterklärend, wo nötig mit einer kleinen Animation
  erklärt, und hinter jedem Hilfe-Knopf steht ein ausführlicher Text.
  Oberfläche auf Deutsch und Englisch, weitere Sprachen über eine einfache
  Übersetzungsdatei. Details: `docs/arbeitsregeln.md`, Abschnitt 8.
- **Zwei FreeCAD-Versionen:** die aktuelle **stabile** (derzeit 1.1.3, die
  Manuel installiert hat) **und** der aktuelle **Wochen-Build**. Beide werden
  vor jedem Push geprüft (`scripts/alle_tests.sh`). Was es nur im
  Wochen-Build gibt (z. B. die CAM-Maschinendefinition für „An CAM
  übergeben“), erklärt das Addon in der stabilen Version in einem Satz,
  statt einen Fehler zu zeigen. Ältere Versionen werden nicht unterstützt.
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
| Code allgemein: welches Modul was tut, wie die Daten fließen, Stolpersteine | [docs/aufbau.md](docs/aufbau.md) |
| W-001 Maschine aus Baugruppe (Achsen, Betriebsarten, Export) | [docs/spezifikation_maschine_aus_baugruppe.md](docs/spezifikation_maschine_aus_baugruppe.md); Code: `camaddon/kette.py` (Baugruppe lesen), `camaddon/maschine.py` (Maschinenobjekt), `camaddon/gui_maschine.py` (Dialog; dazu `gui_details.py`, `gui_hilfe.py`, `gui_verteilhilfe.py`, `gui_bericht.py`, `gui_zeigen.py`), `camaddon/export.py` (Übergabe an CAM), `camaddon/verfahren.py` und `camaddon/gui_verfahren.py` (von Hand verfahren), `camaddon/schraege_achse.py` (schräge Achse, Abschnitt 7c), `camaddon/gui_neue_maschine.py` (Neue Maschine), Beispiele: `camaddon/beispielmaschine.py`, `tests/beispielmaschinen.py` |
| W-001 Stufe 4: Werkzeugbahn auf der Maschine abfahren | [docs/spezifikation_simulation.md](docs/spezifikation_simulation.md) – 4a (Reichweite prüfen) gebaut; 4b (Abfahren) gebaut (Schritte in Abschnitt 5); 4c–4d Entwurf |
| W-002 Werkzeugverwaltung (Werkstoffe, Werkzeuge, Schnittwerte, Strategien) | [docs/spezifikation_werkzeugverwaltung.md](docs/spezifikation_werkzeugverwaltung.md), die Werkzeugarten (Stufe C) in [docs/spezifikation_werkzeugarten.md](docs/spezifikation_werkzeugarten.md); Code: `camaddon/werkstoffe.py` (Liste aus `daten/werkstoffe.json`), `camaddon/werkzeuge.py` (Bibliothek, Schnittwerte), `camaddon/schnittdaten.py` (Rechnen), `camaddon/gui_werkzeuge.py` (Dialog), `camaddon/gui_schnittwerte.py` (Tabelle), `camaddon/gui_eingriff.py` (Bild), `camaddon/gui_strategie.py` (Vergleich), `camaddon/schruppwerte.py` und `camaddon/gui_schruppwerte.py` (Schruppwerte planen), `camaddon/gui_werkstoffe.py` (Werkstoffliste, eigene), `camaddon/uebergabe_werkzeuge.py` (an CAM), `camaddon/werkzeuge_aus_cam.py` (aus CAM), `camaddon/job_schnittwerte.py` und `camaddon/gui_job_schnittwerte.py` (in den Job) |
| W-003 4-Achs-Bearbeitung am runden Rohteil (Entwurf mit Manuels Entscheidungen) | [docs/spezifikation_vierachs.md](docs/spezifikation_vierachs.md) – Stufen V1–V9 in Abschnitt 13, Claudes Vorschläge in Abschnitt 15; Code: `camaddon/vierachs_rohteil.py` (Teil in die Stange, Job), `camaddon/gui_vierachs.py` (Assistent) |
| Installieren und Update-Suche | `installieren.py` (eine Zeile, ohne Git), `camaddon/aktualisierung.py` und `camaddon/gui_aktualisierung.py` (per Git oder, ohne Git, per HTTPS) |
| Ausführliche Hilfetexte | `help/<sprache>/*.html`, Themen in `camaddon/hilfe.py` |
| Texte der Oberfläche, Übersetzungen | `camaddon/sprache.py` (Kopfkommentar), [translations/README.md](translations/README.md) |
| Oberfläche testen, Screenshots | `scripts/oberflaeche_testen.sh` (Kopfkommentar), Beispiel: `tests/gui/szenario_erster_start.py` |
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
