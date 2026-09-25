---
project: freecad_cam_addon
language: de
timezone: Europe/Berlin
status: planung
stack: Python, PySide (Qt), FreeCAD-API (CAM-Workbench)
zielsystem: neueste FreeCAD-Version, jedes Betriebssystem, keine bestimmte Maschine
patch_naming:
  pattern: "P-YYYY-MM-DD-XX <kurzbeschreibung>"   # im Commit-Betreff
  example: "P-2026-09-25-01 projektregeln"
---

# Verlauf (LOG/ARCHIV)

## P-2026-09-25-01 projektregeln

### EINGELESEN
- Regelwerk des Projekts `zeiterfassung` (`CLAUDE.md`, `CHATSTART.md`,
  `docs/arbeitsregeln.md`, `docs/STATUS_SNAPSHOT.md`, Kopf des Verlaufs) als
  Vorlage.

### DATEIEN
- `CLAUDE.md`, `CHATSTART.md`, `README.md`
- `docs/arbeitsregeln.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein neuer Chat, der `CLAUDE.md` liest, weiß danach, was das Projekt ist, nach
welchen Regeln gearbeitet wird und dass der nächste Schritt Manuels
Wunschliste ist.

### DONE
Regeln aus `zeiterfassung` übernommen und auf ein FreeCAD-Addon umgestellt:

- Die drei Festlegungen von Manuel stehen vorn in `CHATSTART.md`: **neueste
  FreeCAD-Version, Betriebssystem egal, Maschine egal**. Deshalb wird danach
  auch nicht mehr gefragt.
- Aus PHP/MariaDB/Apache wurde Python/PySide/FreeCAD-API; Prüfung per
  `python -m py_compile` statt `php -l`.
- Neu gegenüber `zeiterfassung`: Das Akzeptanzkriterium ist ein **Klickweg**,
  den Manuel nachmachen kann. Die KI sieht die Oberfläche nicht, deshalb steht
  im Verlauf, wer was getestet hat.
- Neu: **FreeCAD-Check** im Pre-Flight-Gate. Kann FreeCAD es schon, gibt es
  einen Hinweis statt Code.
- Neu: **Wunschliste** (W-IDs) im Snapshot als Eingang für „das hätte ich gern
  so und so".
- Weggelassen, weil es hier nichts gibt: Datenbank, SQL im Chat,
  Fachregel-Dateien. Die Lesekarte ist leer und wächst mit.

Bewusst **nicht** gemacht: noch kein Addon-Code (T-001 kommt mit dem ersten
Wunsch).

### TEST
- Links zwischen den Dateien per Hand gegengeprüft.

### NEXT
- Manuel füllt die Wunschliste.
