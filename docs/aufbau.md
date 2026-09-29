# Aufbau des Codes

Für alle, die am Addon programmieren. Was das Addon für den Benutzer tut,
steht in der [Spezifikation](spezifikation_maschine_aus_baugruppe.md), wie
gearbeitet wird, in den [Arbeitsregeln](arbeitsregeln.md).

Verweise wie „P-2026-09-25-17“ in Kommentaren führen in den
[Verlauf](archiv/DEV_PROMPT_HISTORY.md). Dort steht, wie ein Befund gefunden
und belegt wurde.

## Vom Modell zur CAM-Maschine

```
Assembly in FreeCAD                         Kette (kette.py)
  Körper, Parts mit LCS      lies_kette()     Glieder: was sich gemeinsam bewegt
  Gelenke: Fixed, Slider,  ─────────────▶     Achsen: Baum vom Bett aus
  Revolute                                    Meldungen
                                                   │
                                                   ▼
Maschinenobjekt (maschine.py)          Dialog „Maschine bearbeiten“
  Betriebsarten: NC-Name, Kennwerte ◀──  (gui_maschine.py), Prüfung mit
  Aufnahmen: LCS, Revolverplatz          maschine.pruefe()
                                                   │  „An CAM übergeben“
                                                   ▼
                                       export.py: Machine der CAM-Maschinen-
                                       definition, gespeichert als .fcm
```

1. **Die Assembly beschreibt die Bewegung – und nur sie.** Das Addon liest
   sie (`kette.py`), verändert sie aber nie. Die Kette wird bei jedem Öffnen
   des Dialogs neu gelesen und nirgends gespeichert.
2. **Was FreeCAD nicht weiß, steht im Maschinenobjekt:** NC-Namen,
   Kennwerte, Werkzeug- und Werkstückaufnahmen. Es ist eine Gruppe in der
   Assembly mit je einem Objekt pro Betriebsart und Aufnahme. Die Verweise
   auf Gelenke und LCS sind echte FreeCAD-Verweise: Umbenennen schadet nicht,
   Löschen hinterlässt einen leeren Verweis, und die Prüfung meldet ihn.
3. **Die Übergabe** baut daraus eine `Machine` der CAM-Maschinendefinition
   und speichert sie dort, wo CAM seine Maschinen sucht. Was CAM nicht kennt
   (Beschleunigung, Revolver …), bleibt im Dokument; der Bericht sagt das.

## Module

| Modul | Aufgabe |
| --- | --- |
| `__init__.py` | Grunddaten: Addon-Ordner, Version aus `package.xml`, Parameterpfad, `symbol()` |
| `sprache.py` | Texte aus `translations/*.json`: `tr()` |
| `einheiten.py` | Zahlen (Stufe B): Maßsystem mm/inch mit Umrechnung je Größe (Länge, Span, vc, Vorschub, Abtrag, Volumen), Dezimalzeichen, Eingaben mit Punkt oder Komma lesen; Einheiten-Platzhalter für `tr()` |
| `hilfe.py` | Hilfeseiten `help/<sprache>/<thema>.html` finden |
| `kette.py` | Assembly lesen: Glieder, Achsen, Meldungen |
| `maschine.py` | Maschinenobjekt: Objektarten, Anlegen, Revolverplätze, Prüfung, Tisch/Kopf |
| `verfahren.py` | Maschine von Hand verfahren: Stellung wie am Gelenk, Grenzen, Bauteile hinter der Achse bewegen |
| `schraege_achse.py` | Schräge Achse (Transformation der Steuerung): Winkel aus der Baugruppe messen, Programm ↔ Schlitten umrechnen, Vorschlag, Prüfung |
| `abfahren.py` | Die Maschine fährt die Bahn ab (W-001 Stufe 4b), Rechenkern: Stationen mit Zeit (Vorschub aus der Bahn, nach G93 1 ÷ F; Eilgang aus der Maschine), Operation, Satz, Stellungen; Stellungen zu jeder Zeit; die Punkte am Werkstück (mit Rundachsen gedreht) |
| `kinematik.py` | Achsstellungen und Werkzeugspitze, die eine Stelle dafür (W-001 4e): `Kinematik` für ein Werkzeug auf einer Maschine – rückwärts `stellungen()` (Punkt im Programm → Achsen), vorwärts `programm()` (Achsen → Spitze im Programm, etwa an einer Grenze) und `am_werkstueck()` (am gedrehten Teil); ohne TCPM, gerechnet mit der Kette aus `reichweite.Pruefung` |
| `reichweite.py` | Reicht der Verfahrweg? (W-001 Stufe 4a): Stellungen aller Achsen für die Bahn eines CAM-Jobs – Drehachsen aus der Bahn, Linearachsen als Gleichungssystem wie an einer Steuerung ohne TCPM (mit den Rundachsen auf 0) –, gebrauchter Bereich, Überschreitungen und Hinweise in Sätzen; Nullpunkt des Jobs |
| `kollision.py` | Stößt beim Abfahren etwas an? (W-001 Stufe 4c): Werkzeug (Schneide, Hals, Schaft, Halter), Teil und Bauteile der Maschine als Körper an ihrer Lage zur Zeit t; Werkzeugseite gegen Werkstückseite und Rest, Werkstückseite gegen Rest, Schneide gegen Teil nur im Eilgang; Schritte je Paar nach Abstand und Weg gegeneinander (Drehachse: Abstand des Körpers von ihr); `distToShape` nur, wo es nötig ist, sonst Schranken (Hüllquader, zuletzt gerechnet minus Weg); Berührung und Warnabstand als Sätze |
| `beispielmaschine.py` | Beispielmaschinen zum Ausprobieren: Baukasten für Assemblies und fünf Bauarten (Drehmaschine mit Y-Achse und Revolver, 3-Achs-, drei 5-Achs-Fräsen) – auch für die Maschinen der Prüfungen; die Drehmaschine mit eintragbaren Maßen (`DrehmaschinenMasse`) |
| `export.py` | Übergabe an CAM mit Bericht |
| `aktualisierung.py` | Update-Suche per Git, ohne Git per HTTPS (package.xml) und Update mit `installieren.py` |
| `werkstoffe.py` | Werkstoffliste (W-002): mitgelieferte aus `daten/werkstoffe.json`, Anzeige, Suche |
| `werkzeuge.py` | Werkzeugbibliothek (W-002): Werkzeuge, Einsätze und Schnittwerte je Werkstoff, eigene Werkstoffe, Speichern als JSON; Maße eingetragen oder geschätzt (`mass`, `reichweite`) – für Bild und CAM gleich |
| `halter.py` | Werkzeughalter (W-002 Stufe D): Kontur aus Abschnitten (Länge, Ø oben, Ø unten) ab der Spindelnase, Länge, Radius, Spanntiefe, Vorlagen; die Halter stehen in der Bibliothek, das Werkzeug nennt seinen (`werkzeuge.laenge_mit_halter`) |
| `werkzeugform.py` | Umriss jeder der 26 Werkzeugarten aus ihren Maßen (Vielecke in mm) – fürs Bild; die zusammengesetzten Maße (Kegel, Konus, Radienprofil) auch für CAM |
| `schnittdaten.py` | Rechnen mit Schnittwerten: n, vf, Zeitspanvolumen, Eingriffswinkel, Spandicke; Kennzahlen und Urteil für den Strategievergleich |
| `uebergabe_werkzeuge.py` | Werkzeuge an CAM übergeben: ToolBits und Bibliothek „CAM-Addon“ über `cam_assets`, jede Art mit ihrer Form und deren Parametern (Näherungen im Bericht), Schnittwerte als Presets |
| `werkzeuge_aus_cam.py` | Werkzeuge aus einer FreeCAD-Werkzeugbibliothek übernehmen: jede Form → Art, Maße, Nummern ohne Verschieben |
| `schruppwerte.py` | Schruppwerte planen: fz je ae mit Spandickenausgleich, Grenzen von Werkzeug und Maschine (auch aus W-001), Vorschlag mit größtem Q |
| `job_schnittwerte.py` | Schnittwerte in die Werkzeug-Controller eines Jobs: Werkstoff vom Rohteil, Werkzeug zum TC, Einsatz vorschlagen, dazu Schrittweite und Zustelltiefe der passenden Operationen; setzen in einer Transaktion |
| `vierachs_rohteil.py` | 4-Achs-Bearbeitung, Teil in die Stange (W-003 V1): Stirnfläche vermessen (Normale, runde Kante, kleinster Kreis um das Teil), Lage für A/B/C, Vorschlag für den Stangen-Ø, Job mit Modell-Klon an der Stelle und Zylinder-Rohteil; `einstellung()` rechnet all das aus einem Job zurück (zum Ändern, V3h); hinter dem Teil bis zum Futter die Lücke `Stange.luecke` – Abstechbreite oder mehr, wenn der Fräser Platz braucht (V3f), `ausspannlaenge()` |
| `vierachs_achsen.py` | 4-Achs-Bearbeitung, Stangenachse (W-003 V2a): von der Maschine (Rundachsen im Tisch, Betriebsart „Positionieren“) oder zugewiesen (A/B/C), mit Drehsinn und der Richtung, aus der das Werkzeug radial kommt; `maschinen()` – die offenen Maschinen zur Wahl im Assistenten mit Rundachsen, Linearachsen und Werkzeugplätzen (V3f) |
| `vierachs_huelle.py` | 4-Achs-Bearbeitung, Hüllfläche (W-003 V3a): wie nah die Spitze eines radialen Schaftfräsers der Stangenachse kommt, ohne das Teil zu verletzen – je Stelle a und Winkel φ, genau gegen das vernetzte Teil (Kanten und Dreiecke), mit numpy; sicheres Raster für die Bahn |
| `vierachs_bahn.py` | 4-Achs-Bearbeitung, Schruppbahn rundum (W-003 V3b): Lagen bis zur Hüllfläche plus Aufmaß, je Lage eine Spirale von vorne bis um den Überlauf hinter das Teil (dort auf der Tiefe der letzten Kontur), nie näher ans Futter als der Abstand zum Futter, Rückzug; Path-Befehle mit X/Y/Z im Rahmen der Maschine, der Rundachse (−drehsinn · φ) und F nach G93 |
| `vierachs_operation.py` | 4-Achs-Bearbeitung, CAM-Operation „Rundum schruppen“ (W-003 V3c): Proxy `RundumSchruppen` (erbt FreeCADs `ObjectOp`, Controller und Kühlmittel, keine Höhen in Z), Eigenschaften in der Gruppe „4-Achs“, rechnet die Bahn aus Modell, Stange und Spannlänge des Jobs; `lege_an()` ohne eigene Transaktion und ohne Rückfrage, `aendere()` für „Übernehmen“ beim Ändern (V3h) |
| `gui_start.py` | Anmeldung in FreeCAD: Befehle, Werkzeugleiste (Arbeitsbefehle) und Menü „CAM-Addon“ (alle Befehle); ruft die anderen `gui_*` auf |
| `gui_maschine.py` | Befehl und Aufgabenfenster „Maschine bearbeiten“; ohne Baugruppe der Weg zu den Beispielmaschinen |
| `gui_neue_maschine.py` | Befehl und Dialog „Neue Maschine …“: Bauart wählen, bei der Drehmaschine Maße eintragen, bauen – auch hinter „Beispielmaschine laden …“ |
| `gui_verfahren.py` | Befehl und Aufgabenfenster „Maschine verfahren“: ein Regler je Achse |
| `gui_reichweite.py` | Befehl und Aufgabenfenster „Auf der Maschine prüfen“ (W-001 Stufe 4a): Job, Nullpunkt, Ergebnis in Sätzen; ein Klick fährt die Maschine an die Überschreitung; öffnet im Dokument der Maschine |
| `gui_abfahren.py` | Abfahren (W-001 Stufe 4b): Werkzeug, Rohteil, Modell und Bahn als Coin-Knoten in der 3D-Ansicht der Maschine (nichts im Dokument), folgen der Maschine; der Abspieler als Bereich im Fenster „Auf der Maschine prüfen“ |
| `gui_kollision.py` | Bereich „Kollision“ im Fenster „Auf der Maschine prüfen“ (W-001 Stufe 4c): Warnabstand, „Kollision prüfen“ mit Fortschritt und Abbrechen, Urteil und Sätze rot/gelb; ein Klick stellt den Abspieler hin, eine rote Kugel zeigt die Stelle |
| `gui_details.py` | Felder der gewählten Betriebsart, Aufnahme oder schrägen Achse |
| `gui_winkelbild.py` | Bild zur schrägen Achse: ausgleichende Achse, rechter Winkel, schräge Achse mit α |
| `gui_zahlen.py` | Zahlenfelder für alle Dialoge: Format mit dem gewählten Dezimalzeichen ohne Tausenderpunkte, Prüfung (Punkt und Komma), Lesen, Zeigen; Dezimalzeichen in Texten |
| `gui_teile.py` | Kleine Bausteine der Werkzeugverwaltung: fette Beschriftung, Knopf, Feld mit Einheit, rote Hinweiszeile, Grau |
| `gui_zeigen.py` | Hervorheben und kurzes Hin-und-her-Bewegen in der 3D-Ansicht |
| `gui_hilfe.py` | Knopf (?) und Hilfefenster |
| `gui_verteilhilfe.py` | Dialog „Revolverplätze verteilen“ |
| `gui_bericht.py` | Bericht nach „An CAM übergeben“ |
| `gui_sprachwahl.py` | Sprachwahl beim ersten Start, Einstellungsseite |
| `gui_aktualisierung.py` | Befehl „Nach Updates suchen“, Update-Hinweis, Gruppe „Updates“ in den Einstellungen (Suche beim Start ab Werk aus) |
| `gui_werkzeuge.py` | Befehl und Dialog „Werkzeugverwaltung“ |
| `gui_halter.py` | Fenster „Halter“ (W-002 Stufe D) aus der Werkzeugverwaltung: Liste mit Suche, Neu (leer oder Vorlage), Kopieren, Löschen; Name, Bezeichnung, Spanntiefe, Kontur als Tabelle, Bild im Schnitt; arbeitet an einer Kopie, OK gibt dem Werkzeug den gewählten Halter |
| `gui_werkzeugbild.py` | Bild des Werkzeugs neben seinen Feldern (malt `werkzeugform`), Symbol je Art in der Auswahl |
| `gui_schnittwerte.py` | Schnittwert-Tabelle in der Werkzeugverwaltung |
| `gui_eingriff.py` | Bild des Eingriffs (Draufsicht und Seitenansicht) zur gewählten Zeile |
| `gui_strategie.py` | Dialog „Strategien vergleichen“: zwei Einsätze mit Balken und Urteil |
| `gui_schruppwerte.py` | Dialog „Schruppwerte planen“: Eingaben, Tabelle je ae, Vorschlag, als Einsatz übernehmen |
| `gui_werkstoffe.py` | Fenster „Werkstoffe“: ganze Liste mit Suche und Filter, eigene Werkstoffe |
| `gui_job_schnittwerte.py` | Befehl und Dialog „Schnittwerte in den Job“ |
| `gui_vierachs.py` | Befehl und Assistent „4-Achs-Bearbeitung“ in zwei Schritten: Rohteil (Fläche im 3D anklicken, Maschine zuerst, Rundachse, Stange, Mitte, Drehlage, Animation) und „Was willst du machen?“ (Rundum schruppen: Werkstoff, Fräser und Einsatz aus der Werkzeugverwaltung, Zustellung, Vorschub je Umdrehung, Aufmaß, Vorschau der Lagen); „Anlegen“: Job und Stange ein Schritt Rückgängig, Controller und Operation ein zweiter. Mit `operation=` zum Ändern (V3h): Schritt 2 mit den Werten der Operation, „Übernehmen“ ein Schritt Rückgängig (`job_schnittwerte.controller_fuer`) |
| `gui_vierachs_operation.py` | Anzeige der Operation „Rundum schruppen“ im Baum: Symbol; Doppelklick und Kontextmenü „Bearbeiten“ öffnen den Assistenten zum Ändern (V3h) |

Zwei Regeln halten das zusammen:

- **Module ohne `gui_` im Namen importieren weder `FreeCADGui` noch Qt.**
  Sie laufen in FreeCADCmd und werden dort ohne Fenster geprüft.
- **Importiert wird nur von `gui_*` zu den übrigen Modulen, nie umgekehrt**,
  und kein Modul importiert ein anderes im Kreis.

## Die Kette (`kette.py`)

- **Bauteil:** was die Assembly als Ganzes bewegt – ein Körper oder ein Part
  mit allem darin (`UtilsAssembly.getMovablePartsWithin(…, partsAsSolid=True)`).
- **Glied:** Bauteile, die starr verbunden sind (Fixed-Gelenke,
  RigidGroups). Alle fixierten Bauteile bilden zusammen das **Bett**.
- **Achse:** ein Slider oder Revolute zwischen zwei Gliedern. Die Achsen
  bilden einen Baum, der beim Bett beginnt; jede kennt ihr Eltern-Glied (zum
  Bett hin) und ihr Kind-Glied (das, was sie bewegt).
- **Abfragen:** `kette.achse_von(gelenk)`, `kette.glied_von(objekt)` – auch
  für ein LCS in einem Part –, `kette.pfad_zum_bett(glied)`.
- **Eine Achse, ein Gelenk.** Eine Wiege, die in zwei Lagerböcken je ein
  Drehgelenk bekommt, kann die Assembly nicht lösen. Die Kette meldet das
  eigens (`kette.doppelt_gelagert`).

## Das Maschinenobjekt (`maschine.py`)

- Gruppe „Maschine“ in der Assembly, erkannt an `Typ == "CamAddon::Maschine"`.
- **Betriebsart:** Verweis aufs Gelenk, Art (Linear, Positionieren, Spindel,
  Revolver), NC-Name, Kennwerte. Ein Gelenk kann mehrere haben – die
  Hauptspindel etwa S4 (Spindel) und C4 (Positionieren).
- **Aufnahme:** Verweis aufs LCS (`PropertyLinkGlobal`, weil das LCS in
  einem Part liegt), Art (Werkzeug oder Werkstück), bei Werkzeugen optional
  Antrieb und Revolverplatz.
- **Transformation:** bisher nur die schräge Achse – Verweise auf zwei
  Betriebsarten (Linear: schräg und ausgleichend) und ihre Namen im
  Programm. Der **Winkel steht nur in der Baugruppe** (Richtung der
  Gelenke); `schraege_achse.winkel()` misst ihn, mit der Richtung, in die
  das Werkzeug gegenüber dem Werkstück fährt (Tischachsen andersherum).
- **Kennwert 0 heißt „unbekannt“.** Keiner dieser Werte kann an einer echten
  Maschine 0 sein.
- `pruefe()` liefert Meldungen, erst Warnungen, dann Hinweise. Jede trägt in
  `bezug` das Objekt, um das es geht; ein Klick im Dialog springt dorthin.
- `rollen()` ordnet jede Achse dem Tisch oder dem Kopf zu – über die Wege
  von den Aufnahmen zum Bett.

## Der Dialog (`gui_maschine.py`, `gui_details.py`)

- Ein Aufgabenfenster und zugleich eine Transaktion: OK übernimmt alles als
  **einen** Schritt Rückgängig, Abbrechen verwirft alles.
- Jede Eingabe geht sofort ins Dokument (`_setze`), damit Hinweise und
  3D-Ansicht stimmen. Danach werden die Listen nur **aufgefrischt**, nicht
  neu gebaut – ein Neuaufbau nach jeder Eingabe ließ FreeCAD unter PySide6
  abstürzen (P-2026-09-25-17). Neu gebaut wird nur, wenn sich die Gliederung
  ändert (anderes LCS, anderer Platz), und dann zeitversetzt.
- Die **Aktionen** hinter den Knöpfen sind öffentliche Methoden
  (`betriebsart_anlegen`, `uebergeben`, `zeige` …). Die Oberflächen-Szenarien
  benutzen dieselben Methoden oder bedienen Knöpfe, Menüs und Signale direkt.

## Texte, Sprachen, Hilfe

- Jeder Text der Oberfläche steht in `translations/<code>.json`. `de.json`
  ist führend und vollständig. Gesucht wird in der gewählten Sprache, dann
  auf Englisch, dann auf Deutsch; kennt keine Sprache den Schlüssel, erscheint
  der Schlüssel selbst.
- Im Code steht ein Schlüssel **immer als fester Text**: `tr("dialog.titel")`
  oder `meldung("kette.koerper_lose", …)`, nie zusammengesetzt. Nur so findet
  `tests/test_sprache.py` fehlende und überflüssige Schlüssel.
- Gespeicherte Werte sind feste ASCII-Wörter (`"Werkstueck"`); angezeigt
  werden sie über `art_text()`, `wert_text()` und `aufnahmeart_text()`.
- Hilfeseiten liegen in `help/<code>/<thema>.html`, die Themen in
  `hilfe.THEMEN`.

## Zwei FreeCAD-Versionen

Unterstützt werden die stabile Version (1.1.x) und der Wochen-Build. Der
Code fragt nach dem, was es gibt, nicht nach Versionsnummern:
`export.verfuegbar()`, `getattr(gelenk, "Suppressed", False)`,
`hasattr(gelenk, "ObjectsToRigidGroup")`. So wird eine Funktion von selbst
frei, sobald die stabile Version sie bekommt.

## Prüfen

- **Einmal einrichten:** `scripts/testumgebung_einrichten.sh` installiert
  beide FreeCAD-Versionen sowie black und ruff.
- **Vor jedem Push:** `scripts/alle_tests.sh` – black und ruff, dann in beiden
  Versionen die Prüfungen ohne Fenster (`tests/test_*.py`) und die Szenarien
  mit Oberfläche (`tests/gui/szenario_*.py`). Mit `OHNE_OBERFLAECHE=1` laufen
  nur die schnellen Prüfungen.
- **Eine Prüfung ohne Fenster** ist ein Skript für FreeCADCmd. Es endet mit
  der Zeile `OK <datei>`; FreeCADCmd meldet eine Ausnahme nicht zuverlässig
  über den Rückgabewert. `UEBERSPRUNGEN <datei>: Grund` ist nur erlaubt, wenn
  es die Funktion in der geprüften Version nicht gibt.
- **Ein Szenario** ist eine Generator-Funktion `schritte(h)`. `yield ms`
  wartet und lässt FreeCAD dabei weiterlaufen; `h.pruefe()`, `h.bild()` und
  `h.modal()` helfen beim Prüfen. FreeCAD läuft dabei unsichtbar (Xvfb) mit
  frischem Benutzerprofil.
- **Beispielmaschinen** für beide Arten: `tests/beispielmaschinen.py`
  (Drehmaschine mit Revolver, Fünfachser mit Schwenkbrücke).

## Stolpersteine

Alle ausprobiert und im Code an Ort und Stelle kommentiert:

| Stolperstein | Folge im Code |
| --- | --- |
| `objekt.Placement.Base = …` ändert nur eine Kopie | ganzes `Placement` zuweisen |
| Flächen für Gelenke gibt es erst nach `recompute()` | vor dem Anlegen neu berechnen |
| Ein einfacher Link auf ein LCS in einem Part ist „out of scope“ | `PropertyLinkGlobal` |
| `App::Origin` ist auch ein `LocalCoordinateSystem` | beim Anbieten von LCS herausfiltern |
| Beschriftungen sind eindeutig: „Futter“ neben „Futter“ wird „Futter001“ | Beschriftung aus den Daten (`beschrifte`) |
| Beim Laden ruft FreeCAD `onChanged` nicht auf, nur `onDocumentRestored` | Sichtbarkeit dort herstellen |
| Das deutsche Zahlenformat hat Tausenderpunkte: „30.000“ | Zahlenfelder ohne Tausendertrennzeichen |
| Enter in einem Feld löst im Aufgabenfenster „OK“ aus | der Dialog hält Enter an (`_EnterBleibtImDialog`) |
| Beim Beenden fragt FreeCAD „Speichern?“ | Szenarien schließen ihre Dokumente |
| `Machine.from_dict` liest den Ursprung einer Linearachse als Richtung | Ursprung 0 übergeben (T-004) |
| Die Knopfleiste macht OK beim Zeigen selbst zum Standardknopf – Enter in einem Feld schließt dann einen QDialog | `keyPressEvent` hält Enter an (Werkzeugverwaltung) |
| Werkstoffnummern wie „1.0503“ sehen aus wie Kommazahlen | `dezimal()` nur auf Zahlentexte, nie auf Werkstoffnamen |
| QTest tippt nur ASCII | in Szenarien Text ohne Umlaute tippen |
| FreeCADCmd 1.1.3 schreibt beim Neuberechnen einen Fortschrittsbalken ohne Zeilenende | Prüfungen, die neu berechnen, geben vor „OK“ eine Leerzeile aus |
| Die Zustelltiefe (`StepDown`) einer Operation hängt an einer Formel aus dem SetupSheet (Vorgabe: Werkzeugdurchmesser) – ein gesetzter Wert ist nach dem Neuberechnen wieder weg | vor dem Setzen `setExpression("StepDown", None)` |
| Die Schrittweite heißt in 1.1.3 `StepOver` (ganze Prozent), im Adaptive des Wochen-Builds `StepOverPercent` (Kommazahl) | `zustellung()` nimmt, was die Operation hat |
| Die Assembly setzt die Begrenzung eines Gelenks beim Lösen nicht durch; bewegt man nur einen Teil der Bauteile hinter einer Achse, zieht sie die Stellung beim Lösen woanders hin | `verfahren.py` bewegt immer alle Bauteile hinter der Achse und hält die Grenzen selbst ein |
| Eine Operation anlegen, wenn der Job mehrere Werkzeug-Controller hat: FreeCAD fragt welchen – in FreeCADCmd 1.1.3 ein Fehler | Prüfungen legen Operationen an, solange der Job nur einen hat |
| CAMs Werkzeugformen sind Skizzen: eine Kante der Länge 0 (Säge ohne Kappe, Gewindebohrer mit Schaft = D) oder ein Hals bis ans Ende lässt sie klagen oder keinen Körper bauen | `uebergabe_werkzeuge`: 1 µm statt 0, mindestens 1 mm Schaft; `test_cam_formen` fängt die Klagen auf der Konsole ab |
| Den Taster baut CAM von oben nach unten (Spitze bei −Länge) | `test_cam_formen` vergleicht ihn gespiegelt |
| Ein ToolBit, das an ein Dokument gehängt wurde, ist mit dem Dokument weg | vor dem Schließen lesen, was man braucht |
| CAMs Bibliotheksfenster lädt seine Oberfläche erst, wenn die Werkbank CAM einmal aktiv war | Szenario schaltet vorher auf CAM |
| Das Mausrad verstellt Auswahllisten, Drehfelder und Regler auch ohne Fokus – beim Blättern im Aufgabenfenster aus Versehen („P10“ im Revolverplatz) | `gui_teile.ruhiges_mausrad` (Filter, reicht das Rad an den nächsten rollbaren Bereich), Regler als `RuhigerRegler` – im Wochen-Build kommt das Rad dort am Filter vorbei; der schützt Drehfelder selbst (`Gui::WheelEventFilter`) |
| Mit `sendEvent` geschickte Rad-Ereignisse gibt Qt nicht an die Eltern weiter | `szenario_mausrad` dreht das Rad über XTest am virtuellen Bildschirm |
| FreeCADs Befehl „Job“ öffnet eine eigene Transaktion | der Assistent legt den Job mit `Path.Main.Job.Create` an und hängt die Anzeige selbst an (`Path.Main.Gui.Job.ViewProvider`) – alles in seiner Transaktion |
| Der Modell-Klon eines Jobs liegt beim Anlegen genau wie das Original | `vierachs_rohteil.richte_ein`: Klon = Lage · Lage des Originals, immer vom Original aus gerechnet |
| `Job.Create` und `Stock.CreateCylinder` legen im aktiven Dokument an | vorher `FreeCAD.setActiveDocument` |
| Die Python-Hülle eines Knopfs aus `modifyStandardButtons` verfällt mit der Hülle der Knopfleiste | die Knopfleiste aufheben, den Knopf jedes Mal über sie holen (wie CAM) |
| 1.1.3 gibt die Beschriftung eines per Abbrechen verworfenen Objekts nicht wieder frei | der nächste Job heißt „… 001“; Szenario prüft nur den Anfang |
| Legt CAM ein ToolBit an (auch den Vorgabe-Controller jedes neuen Jobs), öffnet und schließt es ein verstecktes Dokument – FreeCAD 1.1 schließt dabei außerhalb eines Befehls die offene Transaktion; der Rest ließe sich nicht mehr rückgängig machen. Der Wochen-Build führt Transaktionen je Dokument, dort nicht | `gui_vierachs._im_befehl`: in 1.1 als FreeCAD-Befehl ausführen und die Transaktion darin öffnen (sie bleibt mit `setActiveTransaction(…, True)` offen); ToolBit in einem eigenen Schritt Rückgängig |
| Die Hüllbox gekrümmter Flächen ist nur auf etwa 0,003 mm genau | Prüfungen vergleichen sie mit 0,01 mm |
