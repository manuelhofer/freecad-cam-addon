# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **IN ARBEIT** – W-001, Stufen 1 bis 3 fertig und automatisch geprüft; warten auf Manuels Test. Danach Stufe 4 (Werkzeugbahn abfahren, Kollision – eigene Spezifikation).
- **IN ARBEIT** – W-002, Spezifikation als Entwurf (Entscheidungen von Claude, zur Besprechung); Stufe 1 fertig und automatisch geprüft, wartet auf Manuels Test. Stufe 2 (Übergabe an CAM, Schnittwerte in den Job) und Stufe 3 (Schruppwerte planen) ebenfalls fertig.
- **Zuletzt geprüfte FreeCAD-Versionen:** 1.1.3 (stabil, Manuels Version)
  und Wochen-Build 26.3.0 dev (2026-09-16) – alle Prüfungen und Szenarien
  grün; in 1.1.3 ist der Export übersprungen (gibt es dort nicht).

## Nächster Schritt (konkret)

**W-001, Stufen 1 und 2 sind fertig und automatisch geprüft:** Maschine im
Dialog beschreiben (mit Zeigen in 3D und Hilfe) und mit „An CAM übergeben“
als `.fcm` in CAM bereitstellen. Beides wartet auf **Manuels Test in seinem
FreeCAD** (README, „Installieren“) – vor
allem: Kommt beim Bedienen irgendwo eine Frage auf? Steht die Maschine danach
im CAM-Job zur Auswahl? Und: Kommt die Update-Suche mit der Anmeldung von
GitHub Desktop an das private Repo?

**Stufe 3 ist ebenfalls fertig** (P-2026-09-25-67): „Maschine verfahren“ –
je Achse ein Regler, die Baugruppe fährt mit, Grenzen aus dem Gelenk.
Danach Stufe 4: Werkzeugbahn abfahren und Kollision prüfen. Der Entwurf
der Spezifikation steht ([spezifikation_simulation.md](spezifikation_simulation.md));
**Manuel beantwortet die Fragen in Abschnitt 9**, dann geht es mit 4a
(Reichweite prüfen) los.

**W-002, Stufen 1 bis 3 sind fertig und automatisch geprüft:**
Werkzeugverwaltung mit Werkstoffliste, Schnittwerten je Werkstoff und
Einsatz, Bild des Eingriffs, Strategievergleich, „Schruppwerte planen“
(größtes Zeitspanvolumen, das Werkzeug und Maschine einhalten), „Speichern
und an CAM übergeben“ und „Schnittwerte in den Job“ (setzt auch in 1.1.3
Drehzahl und Vorschub der Werkzeug-Controller, Schrittweite und
Zustelltiefe der passenden Operationen und legt Werkzeug-Controller an).
Wartet auf **Manuels Test** (Klickwege in den Verlaufseinträgen
P-2026-09-25-46 bis -53 und -60 bis -65; der schnellste Einstieg ist
„Schritt für Schritt“ in der Hilfe der Werkzeugverwaltung) und auf die
Besprechung der Entscheidungen in der Spezifikation (Abschnitt 11).

**Installation:** Nach dem Öffentlichstellen (T-005) die Zeile aus dem
README ausprobieren (P-2026-09-25-43, -57).

## Wunschliste

Ein Satz je Wunsch, W-ID fortlaufend.

- **W-001 Maschine aus Baugruppe** – die Maschine als grobes 3D-Modell in
  einer Assembly aufbauen, Slider- und Revolute-Gelenke als Achsen benennen
  und mit Kenndaten versehen (Eilgang, Drehzahl, Schwenkbereich …), daraus
  die CAM-Maschinendefinition von FreeCAD erzeugen; später Grundlage für
  Simulation und Kollisionsprüfung. Spezifikation im Entwurf.
- **W-002 Werkzeugverwaltung** – Werkstoffliste mit deutschen Bezeichnungen,
  Zusammensetzung und Härte; Werkzeuge mit Schnittwerten (ae, ap, vc, fz) je
  Werkstoff und Einsatz; Strategien vergleichen (Zeitspanvolumen,
  Verschleiß). Spezifikation im Entwurf:
  [spezifikation_werkzeugverwaltung.md](spezifikation_werkzeugverwaltung.md).

## Offene Bugs

Keine bekannten.

## Offene Tasks

- **T-005** Repo öffentlich stellen – Empfehlung Claude (P-2026-09-25-43:
  Verlauf ohne Geheimnisse und ohne private Mail-Adressen, Lizenz LGPL).
  Umstellen kann nur Manuel: GitHub → Settings → Danger Zone → Change
  visibility → Public. Danach die Installationszeile aus dem README einmal
  in FreeCAD ausprobieren.

- **T-004** Fehler an FreeCAD melden: `Machine.from_dict` liest bei
  Linearachsen einen Ursprung ≠ (0,0,0) als Richtung (Befund und Beleg in
  P-2026-09-25-20). Solange er besteht, übergibt das Addon Linearachsen mit
  Ursprung 0.
