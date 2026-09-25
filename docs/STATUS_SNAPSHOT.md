# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **PLANUNG** – Regelwerk steht, noch kein Addon-Code.
- **Zuletzt geprüfte FreeCAD-Version:** 26.3.0 dev (Build 2026-09-16, conda-forge)
  – bisher nur die Testumgebung selbst, noch kein Addon-Code.

## Nächster Schritt (konkret)

Manuel sammelt die ersten Wünsche: **was an der CAM-Oberfläche stört und wie
es sein soll**, am besten mit Screenshot oder Skizze. Jeder Wunsch kommt als
ein Satz unter „Wunschliste". Danach wird der erste Wunsch beschrieben (siehe
`arbeitsregeln.md`, Abschnitt 1) und zusammen mit dem Grundgerüst des Addons
gebaut.

## Wunschliste

Ein Satz je Wunsch, W-ID fortlaufend.

- **W-001 Maschine aus Baugruppe** – die Maschine als grobes 3D-Modell in
  einer Assembly aufbauen, Slider- und Revolute-Gelenke als Achsen benennen
  und mit Kenndaten versehen (Eilgang, Drehzahl, Schwenkbereich …), daraus
  die CAM-Maschinendefinition von FreeCAD erzeugen; später Grundlage für
  Simulation und Kollisionsprüfung. Erster Schritt: Spezifikation.

## Offene Bugs

Keine bekannten.

## Offene Tasks

- **T-001** Grundgerüst des Addons (`package.xml`, `InitGui.py`, leere
  Workbench oder Werkzeugleiste) – kommt mit dem ersten Wunsch, nicht vorher.
