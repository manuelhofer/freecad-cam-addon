# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **PLANUNG** – Regelwerk steht, noch kein Addon-Code.
- **Zuletzt geprüfte FreeCAD-Version:** 26.3.0 dev (Build 2026-09-16, conda-forge)
  – bisher nur die Testumgebung selbst, noch kein Addon-Code.

## Nächster Schritt (konkret)

Manuel liest den Entwurf
[spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
und gibt ihn frei. Danach beginnen das Grundgerüst des Addons (T-001), das
Sprachsystem (T-003) und Stufe 1.

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

- **T-001** Grundgerüst des Addons (`package.xml`, `InitGui.py`, leere
  Workbench oder Werkzeugleiste) – kommt mit dem ersten Wunsch, nicht vorher.
- **T-003** Sprachsystem nach `arbeitsregeln.md` Abschnitt 8: JSON-Dateien je
  Sprache, Sprachwahl beim ersten Start (Englisch vorbelegt), Prüfung auf
  gleiche Schlüssel – gleich nach T-001, vor dem ersten Dialog.
