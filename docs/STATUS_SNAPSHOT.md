# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **IN ARBEIT** – W-001, Stufen 1 bis 3 fertig und automatisch geprüft; warten auf Manuels Test. Danach Stufe 4 (Werkzeugbahn abfahren, Kollision – eigene Spezifikation).
- **IN ARBEIT** – W-002, Spezifikation als Entwurf (Entscheidungen von Claude, zur Besprechung); Stufen 1 bis 3 fertig und automatisch geprüft (Werkzeugverwaltung, Übergabe an CAM und in den Job, Schruppwerte planen), wartet auf Manuels Test.
- **Zuletzt geprüfte FreeCAD-Versionen:** 1.1.3 (stabil, Manuels Version)
  und Wochen-Build 26.3.0 dev (2026-09-16) – alle Prüfungen und Szenarien
  grün; in 1.1.3 ist der Export übersprungen (gibt es dort nicht).

## Nächster Schritt (konkret)

**Geplant nach Manuels erstem Test (2026-09-26), wartet auf sein OK:**

1. **Werkzeugname** (Manuels Option A): eigenes Feld „Name“ wie in der
   Steuerung (frei, Leerzeichen bleiben – der Bediener schreibt es wie an
   der Maschine), unter Nummer/Art; „Bezeichnung“ bleibt für Hersteller,
   Bestellnummer. Name in Liste und Suche, Hinweis bei doppeltem Namen
   (erlaubt: Schwesterwerkzeuge), als Werkzeugname in CAM, im Namen des
   Werkzeug-Controllers („T1 Fräser VHM 12 – Schruppen“); „Aus CAM
   übernehmen“ füllt ihn. Leer zeigt das Feld grau einen Namen aus den
   Angaben – „Schaftfräser T1 VHM D12 L30“ (Art, T-Nummer, Schneidstoff,
   Durchmesser, Schneidenlänge) – und der gilt, bis man selbst einen
   einträgt. Ins NC-Programm als `T="…"` nur mit eigenem
   Postprozessor – FreeCADs Posts rufen per Nummer (Heidenhain schreibt
   den Namen des Werkzeug-Controllers als Kommentar).
2. **ae in mm oder % von D** umschaltbar über der Einsatz-Tabelle; intern
   weiter mm, Wahl gemerkt. Offen: auch ap umschaltbar (× D oder % der
   Schneidenlänge)?
3. **Dezimalzeichen:** Die Anzeige folgt schon FreeCADs Einstellung
   (Bearbeiten → Einstellungen → Allgemein → Zahlenformat:
   Betriebssystem / Ausgewählte Sprache / C/POSIX). Neu: bei der Eingabe
   Punkt und Komma annehmen. Das NC-Programm betrifft das nicht – das
   Addon übergibt Zahlen, der Postprozessor schreibt immer mit Punkt.
4. **Eingriffsbild beschriften:** über dem linken Bild „ae – seitliche
   Zustellung (von oben)“, über dem rechten „ap – Zustelltiefe (von der
   Seite)“; der Text daneben je Größe eine Zeile (ae mit Eingriff, ap mit
   Anteil der Schneide, Spandicke).
5. **Planer ohne feste 10 %:** Jede Zeile zeigt ae in % von D; eine
   Warngrenze für ae trägt man am Werkzeug ein (aus dem Katalog), der
   Planer übernimmt sie; Zeilen darüber bleiben wählbar, mit dem Satz
   „mehr als deine Warngrenze (… % von D)“. Offen: Was schlägt der Planer
   ohne Warngrenze vor (Q wächst mit ae bis zur Grenze der Maschine)?
6. **Neues Werkzeug mit Beispiel:** Die Felder zeigen grau Beispielwerte
   je Art (etwa Ø 10, z 3, Schneidenlänge 22), das Bild zeichnet die Form
   daraus (gestrichelt), bis echte Werte da sind – auch beim Durchblättern
   der Liste erscheint immer die Form. Offen: grau (Vorschlag Claude) oder
   echte, schon eingetragene Werte?

**Manuel probiert aus** – alles ist in 1.1.3 und im Wochen-Build
automatisch geprüft, aber gesehen hat es nur Claude als Screenshot. Vorher
das Repository öffentlich stellen (T-005), dann installiert die Zeile aus
dem README; oder wie bisher mit GitHub Desktop aktualisieren.

In dieser Reihenfolge (Klickwege in den Verlaufseinträgen):

1. **Werkzeugverwaltung** (Werkzeugleiste „CAM-Addon“): Hilfe (?) →
   „Schritt für Schritt: vom Katalog in den Job“ durchgehen – Werkstoff,
   Werkzeug (oder „Aus CAM übernehmen“), Einsätze, **„Schruppwerte
   planen…“** (P-2026-09-25-60, -73; Vergleich mit der Vollnut
   P-2026-09-26-04), „Strategien vergleichen“ mit allen Einsätzen (-05),
   Suche und Werkzeugbild (P-2026-09-25-71, P-2026-09-26-01), Kopieren
   und anderen Durchmesser eintragen (-06), Eintauchwinkel (-08), **Zeile
   kopieren** für Varianten (-12).
2. **CAM-Job:** „Schnittwerte in den Job“ → „Werkzeug-Controller
   hinzufügen“ (P-2026-09-25-65) → Operation **Adaptiv** auf eine Bohrung → noch einmal
   „Schnittwerte in den Job“ → Schrittweite, Zustelltiefe und Helixwinkel
   (P-2026-09-25-61, P-2026-09-26-08), dazu „Am Rohteil eintragen“
   (P-2026-09-25-72). Das ist der Weg „Loch auffräsen: einmal
   helikal eintauchen, dann ebenenweise mit voller Schneide“. Die Spalte
   zeigt die **Ebenen**; bei FreeCADs Rohteil (1 mm über dem Modell) meist
   „2 Ebenen (25 + 1 mm)“ mit rotem Hinweis, wie die dünne entfällt
   (P-2026-09-26-16). Basisgeometrie des Adaptivs: beim Sackloch der
   Boden, bei der Durchgangsbohrung die untere Kreiskante (Hilfe,
   P-2026-09-26-21); fehlt sie, sagt die Spalte „keine Bahn“ (-22). In der
   Hilfe dazu „Eine Außenkontur schruppen“ (P-2026-09-26-13).
3. **Maschine:** „Maschine bearbeiten“ (W-001 Stufen 1–2) und **„Maschine
   verfahren“** (Stufe 3, P-2026-09-25-67, Revolverplätze -69): Laufen die Achsen richtig
   herum, stimmt der Nullpunkt?
4. **Besprechen:** Entscheidungen der Werkzeugverwaltung
   ([Spezifikation](spezifikation_werkzeugverwaltung.md), Abschnitt 11,
   Nr. 13–23 sind von dieser Nacht) und die sechs Fragen zu Stufe 4
   ([Entwurf](spezifikation_simulation.md), Abschnitt 9).

Danach: W-001 Stufe 4a (Reichweite prüfen), sobald die Fragen beantwortet
sind.

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
  P-2026-09-25-20, im Wochen-Build vom 2026-09-16 noch da). Solange er
  besteht, übergibt das Addon Linearachsen mit Ursprung 0. **Der Bericht ist
  fertig zum Einreichen:** [freecad_fehler_T-004.md](freecad_fehler_T-004.md)
  – einreichen kann nur Manuel (GitHub-Konto).
