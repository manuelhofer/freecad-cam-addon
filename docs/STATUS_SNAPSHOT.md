# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **IN ARBEIT** – W-001, Stufen 1 bis 3, 3b (schräge Achse, „Neue Maschine …“, Punkt 11 unten) und 4a (Auf der Maschine prüfen, Punkt 13) fertig und automatisch geprüft; warten auf Manuels Test. Stufe 4b (Abfahren, Punkt 13; Manuel: „bau das mit der Maschine“): fertig und automatisch geprüft (P-2026-09-26-89 bis -91, 0.23.0). Stufe 4c (Kollision) mit Manuels Entscheidungen (P-2026-09-26-93): fertig und automatisch geprüft (P-2026-09-26-97 bis -99, 0.24.0). Beim Durchsehen nachgebessert (P-2026-09-27-02 bis -04): die Schneide von Nutenfräser (Schneidenbreite) und Lollipop (Kugel) in Abfahren und Kollision, kein Fehler mehr bei nur „,“ oder „-“ in einem Zahlenfeld, die Spaltenköpfe im Fenster „Halter“ ganz lesbar. Verfahrwege im Fenster „Maschine bearbeiten“ änderbar (P-2026-09-29-03, 0.26.1). Stufe 4e: Werkzeugspitze an einer Stelle gerechnet (`kinematik.py`), im Abspieler und an Überschreitungen (P-2026-09-29-10, 0.27.0); TCPM wählbar zurückgestellt (Frage an Manuel, ob seine Steuerung TRAORI/RTCP nutzt).
- **IN ARBEIT** – W-002, Spezifikation als Entwurf (Entscheidungen von Claude, zur Besprechung); Stufen 1 bis 3 fertig und automatisch geprüft (Werkzeugverwaltung, Übergabe an CAM und in den Job, Schruppwerte planen), dazu die 26 Werkzeugarten (Plan-Stufe C); wartet auf Manuels Test. Stufe D (Halter, für W-001 4c) mit Manuels Entscheidungen ([spezifikation_halter.md](spezifikation_halter.md), P-2026-09-26-93) fertig und automatisch geprüft (P-2026-09-26-94 bis -96). Stufe E (die Richtung des Werkzeugs am Halter – gerade, angetrieben radial, Winkelkopf; Manuel 2026-09-30) fertig und automatisch geprüft (P-2026-09-30-10 bis -16, 0.29.0): Datenmodell und Vorlagen, Fenster „Halter“ mit Richtung und Bild, Reichweite/Abfahren/Kollision mit der Lage aus dem Halter, der Halterkopf vor dem Futter (Rundum), Beispiel-Drehmaschine mit Aufnahmen, gelber Satz im 4-Achs-Assistenten; wartet auf Manuels Test.
- **IN ARBEIT** – W-003 4-Achs-Bearbeitung am runden Rohteil: Spezifikation mit Manuels Entscheidungen (P-2026-09-26-78), Stufe V1 „Teil in die Stange“ (P-2026-09-26-79), V2a „Achse von der Maschine“ und V2c (P-2026-09-27-37, -38), V3 „Rundum schruppen“ – Hüllfläche, Bahn, Operation, Schritt 2 „Was willst du machen?“, Prüffenster ohne TCPM (P-2026-09-27-45 bis -54, 0.26.0), nachträglich ändern per Doppelklick (V3h, P-2026-09-29-04, -06, 0.26.1/0.27.0), Überlauf und Ausspannlänge, Kugel-/Torus-Hinweis, Maschine zuerst (V3f, P-2026-09-29-07 bis -09), Rohteil/Fertigteil in der Simulation (V3g, -11, 0.27.0) – fertig und automatisch geprüft; wartet auf Manuels Test. Dabei die Kollisionsprüfung beschleunigt (über 20 Minuten → Sekunden, -50, -53) und der Rückzug im Eilgang kein Befund mehr (-51). V5 „Rundum schlichten“ mit Manuels Entscheidungen (2026-09-30: Spirale, jeder Fräser mit seiner Form, Schrittweite aus der Werkzeugtabelle, Abstände einmal für beide): Fräserform und Hüllfläche, Bahn, Operation, Assistent, Stufen, wo das Schruppen mehr stehen ließ, Abtrag und Schneide mit der Form (V5a–V5e, P-2026-09-30-01 bis -08, 0.28.0) – fertig und automatisch geprüft; wartet auf Manuels Test. Nach Manuel (2026-09-30: „mit den Grundvoraussetzungen anfangen“) die Richtung des Werkzeugs am Halter und die Beispiel-Drehmaschine mit Aufnahmen gebaut (W-002 Stufe E, 0.29.0): Schruppen T1 und Schlichten T2 mit radialem Halter gehen dort zusammen – Prüfen, Abspielen, Kollision, Farben (`szenario_rundum_drehmaschine`). Dabei gefunden: hinter einem Absatz zum Futter hin bleibt bei manchen Winkeln mehr stehen (Vorschlag „Ringgang an Absätzen“ in der Spezifikation). Als Nächstes: alles auf Bedienbarkeit und Logik prüfen; danach V4 Flächen wählen (abheben und sicher wieder einsetzen, mehrere Strategien je nach Werkzeug, Entgraten). Offen danach: V2b (Drehteile), V6, V7.
- **Zuletzt geprüfte FreeCAD-Versionen:** 1.1.3 (stabil) und Wochen-Build
  26.3.0 dev (2026-09-16) – alle Prüfungen und Szenarien grün; in 1.1.3 ist
  der Export übersprungen (gibt es dort nicht). **1.1.4** (Manuel nutzt sie
  seit 2026-09-29): Quelltext gegen 1.1.3 verglichen – nichts in CAM,
  Assembly, PartDesign oder den Python-Schnittstellen des Addons
  (P-2026-09-29-01); der volle Lauf (Arbeitsregeln, Abschnitt 9) folgt, sobald
  conda-forge 1.1.4 hat.

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

*4-Achs-Bearbeitung (W-003, Manuel 2026-09-26)*
12. **Teil in eine runde Stange, rundum schruppen und schlichten:**
   Stirnfläche anklicken → das Teil sitzt mittig vorne in der Stange (z. B.
   Ø 80); Flächen anklicken („alle Mantelflächen“, ein außermittiger
   Zylinder); aus Fräser und Stange entstehen Schrupp- und Schlichtbahn –
   egal ob A, B oder C, auch auf einer Drehmaschine mit C und Y. Assistent in
   vier Schritten, eigener Rechenkern (1.1.3 und Wochen-Build), Ausgabe als
   reine Achskoordinaten, alles einstellbar mit Vorschlägen. –
   *Spezifikation: [spezifikation_vierachs.md](spezifikation_vierachs.md)
   (P-2026-09-26-78), Stufen in Abschnitt 13. V1 „Teil in die Stange“, V2a,
   V2c und V3 „Rundum schruppen“ fertig (P-2026-09-26-79, P-2026-09-27-37,
   -38, -45 bis -54); nach Manuels Test V2b „Drehteile“ und V4 „Flächen
   wählen“.*

*Werkzeugbahn auf der Maschine (W-001 Stufe 4a, Manuel 2026-09-26)*
13. **Reicht der Verfahrweg?** Job wählen → „Auf der Maschine prüfen“ →
   „Alle Achsen bleiben in ihren Grenzen.“ oder je Überschreitung ein Satz
   („X1 fährt in *Tasche* bis 312,00 mm, die Grenze ist 250,00 mm“); ein
   Klick fährt die Maschine dorthin. Manuels Entscheidungen: die Bahn im
   Job, Nullpunkt am LCS der Werkstückaufnahme plus Verschiebung je Job,
   eigenes Feld „Länge ab Spindelnase“, 4a zuerst. – *Spezifikation:
   [spezifikation_simulation.md](spezifikation_simulation.md), Abschnitte
   5, 6 und 10 (P-2026-09-26-83), vier Schritte: Rechenkern, Fenster,
   Länge ab Spindelnase, Version. Schritt 1 fertig (P-2026-09-26-84:
   `reichweite.py`, an allen Beispielmaschinen nachgemessen), Schritt 2
   fertig (-85: Befehl und Fenster, Klick fährt hin), Schritt 3 fertig
   (-86: „Länge ab Spindelnase“ in der Werkzeugverwaltung), Version 0.22.0
   (-87). Stufe 4a damit komplett. **4b „Abfahren“** – die Maschine fährt
   die Bahn sichtbar ab, mit Werkzeug, Rohteil und Bahn – spezifiziert
   (P-2026-09-26-88, Entscheidungen von Claude zur Besprechung); Schritt 1
   fertig (-89: `abfahren.py`, Zeiten gegen Handrechnung), Schritt 2 fertig
   (-90: Abspieler im Fenster, Körper in der 3D-Ansicht der Maschine),
   Version 0.23.0 (-91). Stufe 4b damit komplett. **4c „Kollision“** –
   Manuels Entscheidungen (P-2026-09-26-93): eigene Halter-Verwaltung
   ([spezifikation_halter.md](spezifikation_halter.md): Kontur aus
   Zylindern und Kegeln, eigenes Fenster, Länge ab Spindelnase gemessen,
   sonst geschätzt), geprüft gegen fertiges Teil und Spannmittel, gemeldet
   Berührung und Warnabstand. Halter fertig (P-2026-09-26-94 bis -96:
   Datenmodell, Fenster „Halter“, Länge und Anzeige), 4c fertig (-97:
   `kollision.py`, -98: Bereich „Kollision“ im Fenster), Version 0.24.0
   (-99). Stufe 4c damit komplett; 4d (Bearbeitungszeit mit Beschleunigung)
   bleibt Entwurf.*

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
6. **4-Achs-Bearbeitung, Teil in die Stange** (P-2026-09-26-79): ein Teil mit
   ebener Stirnfläche öffnen (etwa eine Welle), die Stirnfläche anklicken →
   Werkzeugleiste „CAM-Addon“ → **4-Achs-Bearbeitung** → das Teil fährt in
   eine durchscheinende Stange und dreht sich einmal; Ø 80 eintragen →
   „Passt – rundum mindestens … mm“; „ganzes Teil möglichst mittig“ und
   Rundachse A/B/C umschalten (die Stange liegt in X, Y oder Z); „+90°“;
   „Anlegen“ → Job „… – 4 Achsen“ mit Zylinder-Rohteil, ein Strg+Z nimmt
   alles zurück. Versteht man das Fenster ohne Erklärung?
7. **Auf der Maschine prüfen** (P-2026-09-26-84 bis -86): „Neue Maschine …“
   → 3-Achs-Fräse bauen; ein Teil mit CAM-Job öffnen (etwa eine Tasche),
   den Job im Baum wählen → Werkzeugleiste „CAM-Addon“ → **Auf der
   Maschine prüfen** → das Fenster öffnet sich bei der Maschine, grün „Alle
   Achsen bleiben in ihren Grenzen.“; unter „Nullpunkt des Jobs“ bei X 300
   eintragen → rot eine Überschreitung von X1; draufklicken → der Tisch
   fährt an den Anschlag; Schließen → alles zurück, das Teil ist wieder
   vorn. In der Werkzeugverwaltung beim Werkzeug „Länge ab Spindelnase“
   eintragen (mit Halter) → der Hinweis zur Länge verschwindet, Z rechnet
   damit. Versteht man das Fenster ohne Erklärung, passt der Vorschlag für
   den Nullpunkt? **Abfahren** (P-2026-09-26-89, -90): im selben Fenster
   unter „Abfahren“ → in der Maschine liegen Rohteil (durchscheinend) und
   Teil auf dem Tisch, darauf die Bahn (Vorschub blau, Eilgang rot), das
   Werkzeug steckt in der Spindel; die **Lupe** neben dem Tempo holt
   Werkstück und Werkzeug heran (P-2026-09-26-92);
   **Abspielen** → die Maschine fährt, die Werkzeugspitze läuft die blaue
   Linie entlang, Satz, Zeit und Achswerte laufen mit; Tempo ×20; den
   Schieber ziehen; „einen Punkt zurück/weiter“; oben eine Operation wählen
   → Sprung an ihren Anfang. Mit X 300 auf die Überschreitung klicken → der
   Abspieler steht dort, X1 rot „am Anschlag“. Schließen → Werkzeug, Rohteil
   und Bahn sind weg, die Maschine steht wie vorher. Passen Zeit und Tempo,
   sieht man genug? **Halter** (P-2026-09-26-94 bis -96): Werkzeugverwaltung →
   ein Werkzeug → „Halter …“ → „Neu“ → „Spannzangenfutter ER32 · SK40“ → Liste,
   Kontur-Tabelle und Bild im Schnitt → OK → beim Werkzeug steht der Halter,
   die leere Länge ab Spindelnase zeigt grau „leer: … mit Halter“; im Abfahren
   steckt das Werkzeug in diesem Halter. **Kollision** (-97, -98): Die
   3-Achs-Fräse hat jetzt zwei Spanneisen. Ein kurzes Werkzeug (Gesamtlänge
   25 mm, ohne Halter) und eine Bahn dicht neben einem Spanneisen in die Tiefe
   → „Kollision prüfen“ → rot „Es stößt etwas an:“, „In „…“ berühren sich
   „Spindel“ und „Spanneisen_rechts“ …“ → Klick → die Maschine steht dort,
   eine rote Kugel zeigt die Stelle. Warnabstand 10 → gelbe Sätze dazu.
   Versteht man die Sätze, stimmen die Stellen?
8. **Besprechen:** Entscheidungen der Werkzeugverwaltung
   ([Spezifikation](spezifikation_werkzeugverwaltung.md), Abschnitt 11,
   Nr. 13–23 sind von dieser Nacht); zu Stufe 4b und 4c Claudes
   Einzelheiten ([Spezifikation](spezifikation_simulation.md), Abschnitt 5)
   und zu den Haltern ([Spezifikation](spezifikation_halter.md),
   Abschnitt 9, Nr. 4–7).

Danach: Manuel testet 4a–4c und die Halter (Punkt 7 oben); offen sind W-001 4d (Bearbeitungszeit mit Beschleunigung) und W-003 V2 (4-Achs: Achse von der Maschine).

Neu (2026-09-27): die Durchsicht **W-004** ([durchsicht_bedienbarkeit.md](durchsicht_bedienbarkeit.md)). Die kleinen Punkte D-01 bis D-08 sind erledigt (P-2026-09-27-09 bis -16), dazu auf Manuels Hinweis der Revolver der Beispiel-Drehmaschine mit Stationen und die Beispielmaschinen ohne Gelenkmarkierungen (P-2026-09-27-07, -08). In der empfohlenen Reihenfolge weiter (Manuel: „Besser weiter“): D-21 Job in allen offenen Dokumenten (-18), D-20 Maschine merken und selbst öffnen, Teil Prüffenster (-19), D-10 drei Urteile oben im Prüffenster (-20, -22), D-11 „T1 öffnen …“ an den Hinweisen (-21), D-25 Betriebsarten vorschlagen (-23), D-26 Maße der 3-Achs-Fräse (-24), D-30 unbenutzte fremde Controller entfernen (-26), D-12 „+ Einsatz“ beim neuen Werkzeug (-27), D-13 Menü „CAM-Addon“ (-28), D-29 „ap … übernehmen“ (-29), D-28 veraltete Schnittwerte im Prüffenster mit „übernehmen“ (-31; dafür merkt sich jeder Controller Einsatz und Werkstoff, -30), D-09 ein Werkzeug je Job statt „… L001“ (-32 Befund, -34). Neue Arbeitsregel: Neben `scripts/alle_tests.sh` läuft kein anderes FreeCAD (-33). Offen ohne Entscheidung: D-23 (wartet auf Manuels Antwort zur Ausspannlänge), Rest von D-20 und D-26; zur Entscheidung (Abschnitt 6 dort): D-14, D-22, D-24, D-27 und Frage 6 zu den Werkzeugnamen (D-09).

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
- **W-003 4-Achs-Bearbeitung am runden Rohteil** – ein Teil mit einer
  Stirnfläche vorne mittig in eine runde Stange legen, Flächen anklicken und
  daraus Schrupp- und Schlichtbahnen für eine Rundachse (A, B oder C, auch
  Drehmaschine mit C und Y) erzeugen lassen. Spezifikation:
  [spezifikation_vierachs.md](spezifikation_vierachs.md).
- **W-004 Bedienung vereinfachen und automatisieren** – Durchsicht aller
  Fenster und Abläufe (2026-09-27, Manuels Auftrag): acht kleine Stellen
  (D-01 bis D-08), einfacher bedienen (D-10 bis D-14), automatisieren (D-20
  bis D-30) – etwa die eigene Maschine merken, Betriebsarten, Halter und
  Richtwerte vorschlagen, CAM und Job von selbst aktuell halten. Befunde,
  Reihenfolge und Fragen: [durchsicht_bedienbarkeit.md](durchsicht_bedienbarkeit.md).
  D-01 bis D-08 erledigt (P-2026-09-27-09 bis -16); D-10, D-11, D-20
  (Prüffenster), D-21, D-25, D-26 (3-Achs-Fräse) erledigt (P-2026-09-27-18
  bis -24); D-09, D-12, D-13, D-28 bis D-30 erledigt (P-2026-09-27-26 bis
  -34).

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
