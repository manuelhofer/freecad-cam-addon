# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **IN ARBEIT** – W-001, Stufe 1 fertig und automatisch geprüft; wartet auf Manuels Test. Danach Stufe 2 (Export).
- **Zuletzt geprüfte FreeCAD-Version:** 26.3.0 dev (Build 2026-09-16, conda-forge)
  – Prüfungen ohne Fenster und Oberflächen-Szenario grün.

## Nächster Schritt (konkret)

**W-001, Stufe 1 ist fertig:** Der Dialog „Maschine bearbeiten“ mit Zeigen in
der 3D-Ansicht und Hilfe ist automatisch geprüft. Er wartet jetzt auf
**Manuels Test in seinem FreeCAD** (README, „Installieren“; Baugruppe öffnen,
Knopf „Maschine bearbeiten“) – vor allem: Kommt beim Bedienen irgendwo eine
Frage auf?

Danach Stufe 2: Export in die CAM-Maschinendefinition (`.fcm`).

## Wunschliste

Ein Satz je Wunsch, W-ID fortlaufend.

- **W-001 Maschine aus Baugruppe** – die Maschine als grobes 3D-Modell in
  einer Assembly aufbauen, Slider- und Revolute-Gelenke als Achsen benennen
  und mit Kenndaten versehen (Eilgang, Drehzahl, Schwenkbereich …), daraus
  die CAM-Maschinendefinition von FreeCAD erzeugen; später Grundlage für
  Simulation und Kollisionsprüfung. Spezifikation im Entwurf.

## Offene Bugs

Keine bekannten.

## Offene Tasks

- **T-004** Fehler an FreeCAD melden: `Machine.from_dict` liest bei
  Linearachsen einen Ursprung ≠ (0,0,0) als Richtung (Befund und Beleg in
  P-2026-09-25-20). Solange er besteht, übergibt das Addon Linearachsen mit
  Ursprung 0.
