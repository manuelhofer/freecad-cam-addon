# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **IN ARBEIT** – W-001, Stufen 1 und 2 fertig und automatisch geprüft; warten auf Manuels Test. Danach Stufe 3.
- **Zuletzt geprüfte FreeCAD-Version:** 26.3.0 dev (Build 2026-09-16, conda-forge)
  – Prüfungen ohne Fenster und Oberflächen-Szenario grün.

## Nächster Schritt (konkret)

**W-001, Stufen 1 und 2 sind fertig und automatisch geprüft:** Maschine im
Dialog beschreiben (mit Zeigen in 3D und Hilfe) und mit „An CAM übergeben“
als `.fcm` in CAM bereitstellen. Beides wartet auf **Manuels Test in seinem
FreeCAD** (README, „Installieren“) – vor allem: Kommt beim Bedienen irgendwo
eine Frage auf? Und: Steht die Maschine danach im CAM-Job zur Auswahl?

Danach Stufe 3: Maschine von Hand verfahren (je Betriebsart ein Regler).

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

- **T-005** Das Repo bleibt vorerst privat (Manuel). Wird es öffentlich
  (Settings → Danger Zone → Change visibility), funktionieren die Updates
  über den Addon-Manager (README); bis dahin Installation und Update mit
  GitHub Desktop.

- **T-004** Fehler an FreeCAD melden: `Machine.from_dict` liest bei
  Linearachsen einen Ursprung ≠ (0,0,0) als Richtung (Befund und Beleg in
  P-2026-09-25-20). Solange er besteht, übergibt das Addon Linearachsen mit
  Ursprung 0.
