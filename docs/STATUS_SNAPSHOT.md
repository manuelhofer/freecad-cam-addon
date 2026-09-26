# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **IN ARBEIT** – W-001, Stufen 1 bis 3 fertig und automatisch geprüft; warten auf Manuels Test. Jetzt Stufe 3b (schräge Achse, Punkt 11 unten), danach Stufe 4 (Werkzeugbahn abfahren, Kollision – eigene Spezifikation).
- **IN ARBEIT** – W-002, Spezifikation als Entwurf (Entscheidungen von Claude, zur Besprechung); Stufen 1 bis 3 fertig und automatisch geprüft (Werkzeugverwaltung, Übergabe an CAM und in den Job, Schruppwerte planen), dazu die 26 Werkzeugarten (Plan-Stufe C); wartet auf Manuels Test.
- **Zuletzt geprüfte FreeCAD-Versionen:** 1.1.3 (stabil, Manuels Version)
  und Wochen-Build 26.3.0 dev (2026-09-16) – alle Prüfungen und Szenarien
  grün; in 1.1.3 ist der Export übersprungen (gibt es dort nicht).

## Nächster Schritt (konkret)

**Geplant nach Manuels erstem Test (2026-09-26) – Reihenfolge A → B → C, Stufe A in Arbeit:**

*Stufe A – Werkzeugverwaltung verfeinern*
1. **Werkzeugname** neben der Nummer (Option A): frei, wie an der
   Maschine (Leerzeichen bleiben). Leer gilt ein Name aus den Angaben,
   grau gezeigt: „Schaftfräser T1 VHM D12 L30“ (Zahlen mit Punkt). Name in
   Liste, Suche, als Werkzeugname in CAM, im Namen des Werkzeug-Controllers
   („T1 Fräser VHM 12 – Schruppen“); „Aus CAM übernehmen“ füllt ihn;
   doppelte Namen: Hinweis, erlaubt. NC-Aufruf `T="…"` nur mit eigenem
   Postprozessor (FreeCADs rufen per Nummer). – *Fertig, 0.12.0
   (P-2026-09-26-33).*
2. **Neues Werkzeug mit Beispielwerten:** grau gezeigt, aber gültig
   (Manuel: wer Ø 12 stehen lässt, will Ø 12), Durchmesser 12; das Bild
   zeigt gleich die Form, beim Durchblättern immer. – *Fertig
   (P-2026-09-26-37), mit grauen Beispielen für vc und Spandicke im
   Planer.*
3. **Planer:** Warngrenze ae 10 % von D bleibt Vorgabe (fest, egal wie
   viele Schneiden, Manuel), am Werkzeug änderbar; Zeilen darüber rot
   „mehr als deine Warngrenze“, aber wählbar; % je Zeile sichtbar. –
   *Fertig (P-2026-09-26-40).*
4. **Eingriffsbild:** Überschriften „ae – seitliche Zustellung (von
   oben)“ / „ap – Zustelltiefe (von der Seite)“, Text je Größe eine Zeile.
   – *Fertig (P-2026-09-26-41).*
5. **ae und ap wahlweise in mm oder % von D** (ein Umschalter über der
   Tabelle, intern mm, Wahl gemerkt). – *Fertig (P-2026-09-26-42).*
6. **Bohrer: Spitzenwinkel** (fehlt, Manuel) – Feld, Bild, an CAM als
   Spitzenwinkel des Bohrers; die Schneidenzahl bleibt (f je Umdrehung).
   – *Fertig (P-2026-09-26-43). Stufe A damit komplett.*

*Zwischendurch – zum Ausprobieren (nach A2, vor A3)*
7. **Beispielmaschine laden:** Die Meldung „Hier gibt es noch keine
   Baugruppe“ in „Maschine bearbeiten“ und „Maschine verfahren“ bekommt
   den Knopf „Beispielmaschine laden“ (Manuel: wer das Addon ausprobiert,
   soll nicht erst eine Maschine bauen müssen). Er öffnet ein neues
   Dokument mit einer fertig eingerichteten Maschine und gleich danach den
   Dialog. Grundlage: der Baukasten aus `tests/beispielmaschinen.py`. –
   *Fertig (P-2026-09-26-38): Dreiachs-Fräsmaschine, Baukasten jetzt in
   `camaddon/beispielmaschine.py`.*
7b. **Beispielmaschinen zur Auswahl** (Manuel nach dem ersten Ausprobieren,
   2026-09-26): „Beispielmaschine laden“ bietet die üblichen Sorten an –
   Schrägbett-Drehmaschine mit Y-Achse (CLX-ähnlich; Z = Hauptspindel;
   Revolver mit zwei angetriebenen Fräswerkzeugen: axial, bearbeitet in
   Z-Richtung, und radial, 90° dazu), 3-Achs-Fräse, 5-Achs Tisch/Tisch
   (A/C, Schwenkbrücke mit Rundtisch), 5-Achs Kopf/Kopf (A/B), 5-Achs
   Kopf/Tisch (B am Kopf, C am Tisch). Nach Stufe B. – *Fertig
   (P-2026-09-26-62): „Beispielmaschine laden …“ bietet die fünf Bauarten
   mit je einem Satz dazu an; die Auswahl merkt sich die zuletzt geladene.*
7c. **Update auf Knopfdruck** (Manuel: nicht jedes Addon soll beim Start
   suchen): Knopf „Nach Updates suchen“ in der Werkzeugleiste; die Suche
   beim Start ist ab Werk aus, in den Einstellungen einschaltbar. –
   *Fertig (P-2026-09-26-50).*

*Stufe B – Einheiten und Zahlenformat*
8. Beim ersten Start (mit der Sprache) und in den Einstellungen des
   Addons: **Maßsystem** mm oder inch und **Dezimaltrennzeichen** , oder
   . – mit Beispielzahlen, vorbelegt aus FreeCADs Einstellungen
   (Einheitensystem, Zahlenformat). – *Fertig (Dezimalzeichen
   P-2026-09-26-45, Maßsystem P-2026-09-26-48).*
9. Überall in der gewählten Einheit anzeigen und eingeben (mm/inch,
   m/min/SFM, mm/min/ipm, cm³/min/in³/min), Umschalter in der
   Werkzeugverwaltung; intern metrisch – verlustfrei, 1 in = 25,4 mm, 1/2"
   bleibt 0,5 in. Eingabe nimmt Punkt und Komma (*fertig,
   P-2026-09-26-45*). – *Fertig (P-2026-09-26-48); Beschleunigung, Ruck
   und Werkstoffdaten bleiben metrisch.*

*Stufe C – Werkzeugarten wie in InventorCAM (eigene Spezifikation zuerst)*
10. Arten: Schaft-, Kugel-, Torus-, Konik-, Schwalbenschwanz-,
   Lollipop-, Fasen-, Radien-, Plan-, Nuten-, Form-, Gewindefräser;
   Bohren, Zentrierbohrer, NC-Anbohrer, Gewinde rechts/links, konische
   und zylindrische Senkung, Reibahle, Bohrstange, Ausbohren/Spindeln;
   Universal-Drehen, Einstechen, Gewinde (Drehen); Antasten. Drehwerkzeuge
   gleich mit (Schnittwerte für später – FreeCAD 1.1.3 dreht nicht). Je Art: Maße,
   Bild, Einsätze, was CAM davon kennt. Achtung: Das heutige
   „Radiusfräser“ ist ein Kugelfräser – umbenennen; „Radienfräser“ ist eine
   andere Art. – *Spezifikation: `docs/spezifikation_werkzeugarten.md`
   (P-2026-09-26-53), sechs Stufen, Abschnitt 8. Auf Manuels Wunsch vor
   Punkt 7b („ne, mach mal Werkzeugarten weiter“); 7b liegt fast fertig
   im Stash „WIP Beispielmaschinen zur Auswahl“.* – *Fertig
   (P-2026-09-26-54 bis -60): Kugelfräser statt „Radiusfräser“, alle 26
   Arten mit ihren Feldern, Bilder (auch in der Auswahl), Einsätze und
   Rechnen je Art, Übergabe an und Übernahme aus CAM für alle Arten (CAM
   baut denselben Körper wie das Bild), die neuen Einsätze auf die
   passenden Operationen im Job.*

*Schräge Achse (W-001 Stufe 3b, Manuel 2026-09-26)*
11. **Schrägbett mit schräger Y-Achse:** Fährt der Y-Schlitten schräg zum
   X-Schlitten, rechnet die Steuerung ein rechtwinkliges Y auf beide um
   (Siemens TRAANG) – für Y fahren beide. Eintrag „Schräge Achse“ in
   „Maschine bearbeiten“ (Winkel eintragen, die Baugruppe folgt),
   Erkennung, „Maschine verfahren“ wie im Programm, Übergabe an CAM,
   Höchstvorschub; danach eine Vorlage mit Eingabemaske. – *Spezifikation:
   Abschnitt 7c und Stufe 3b in
   [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
   (P-2026-09-26-65), sieben Schritte. Schritt 1 fertig (P-2026-09-26-66:
   Bereich „Transformationen“ mit „+ Schräge Achse“, Winkel aus der
   Baugruppe, Bild, Beispiel), Schritt 2 fertig (-67: Winkel eintragen, die
   Führung dreht sich mit), Schritt 3 fertig (-68: Hinweis „Y1 steht 30,0°
   schräg zu X1“, ein Klick legt an), Schritt 4 fertig (-69: „Maschine
   verfahren“ wie im Programm, am Anschlag eine rote Zeile), Schritt 5
   fertig (-71: an CAM rechtwinklig, Grenzen und Eilgang umgerechnet),
   Schritt 6 fertig (-72: Höchstvorschub beim Planen), Schritt 7 fertig
   (-75: Befehl „Neue Maschine …“, Maße der Drehmaschine). Stufe 3b damit
   komplett.*

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
2. **Werkzeugarten** (P-2026-09-26-53 bis -60): In der Werkzeugverwaltung
   „Neu“ → „Art“ aufklappen: 26 Arten mit kleinen Bildern, gegliedert nach
   Fräsen, Bohren, Drehen, Antasten. Je Art andere Felder und ein anderes
   Bild (Gewindebohrer: Steigung statt Schneidenzahl), „+ Einsatz“ bietet
   nur, was passt. „Speichern und an CAM übergeben“ nennt, was CAM nur
   genähert kennt; in CAM unter Werkzeugbibliothek → „CAM-Addon“ steht jede
   Art mit ihrer Form. „Aus CAM übernehmen“ → „Default“ holt alle 13
   Werkzeuge. Im Job: Planfräser mit „Planen“ in eine Fläche →
   „Schnittwerte in den Job“ setzt Schrittweite und Zustelltiefe.
3. **CAM-Job:** „Schnittwerte in den Job“ → „Werkzeug-Controller
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
4. **Maschine:** „Maschine bearbeiten“ (W-001 Stufen 1–2) und **„Maschine
   verfahren“** (Stufe 3, P-2026-09-25-67, Revolverplätze -69): Laufen die Achsen richtig
   herum, stimmt der Nullpunkt? In einem leeren FreeCAD bietet
   „Beispielmaschine laden …“ fünf fertige Maschinen zum Ausprobieren
   (P-2026-09-26-62) – etwa die Drehmaschine mit Revolver: T und C1
   verfahren, P1/P2 angetrieben von S3.
5. **Schräge Achse** (P-2026-09-26-65 bis -72): Beispiel-Drehmaschine →
   „Maschine bearbeiten“ → unter „Transformationen“ „+ Schräge Achse“ →
   Winkel 30 eintragen: In der 3D-Ansicht bleibt alles stehen, die
   Beispielzeile zeigt „Y +10,0 mm → Y1 +11,5 mm, X1 −5,8 mm“; mit der Maus
   auf dem Eintrag verweilen: X- und Y-Schlitten fahren zusammen hin und
   her. OK → „Maschine verfahren“ steht auf „wie im Programm“: Y auf 10 →
   beide Schlitten fahren; X auf 140, dann Y auf −40 → rote Zeile „… X1
   steht an seiner Grenze 150,00 mm“. Im Wochen-Build „An CAM übergeben“:
   der Bericht nennt die schräge Achse. Versteht man den Bereich ohne
   Erklärung? Dann **„Neue Maschine …“** (P-2026-09-26-75): Drehmaschine,
   Bettneigung 30°, Y schräg um 30°, 8 Plätze → „Maschine bauen“ → die
   Maschine steht im neuen Dokument, „Maschine bearbeiten“ zeigt die
   schräge Achse.
6. **Besprechen:** Entscheidungen der Werkzeugverwaltung
   ([Spezifikation](spezifikation_werkzeugverwaltung.md), Abschnitt 11,
   Nr. 13–23 sind von dieser Nacht) und die sechs Fragen zu Stufe 4
   ([Entwurf](spezifikation_simulation.md), Abschnitt 9).

Danach: W-001 Stufe 4a (Reichweite prüfen), sobald die schräge Achse
(Punkt 11) steht und die Fragen zu Stufe 4 beantwortet sind.

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
