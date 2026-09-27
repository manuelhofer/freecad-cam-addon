---
project: freecad_cam_addon
language: de
timezone: Europe/Berlin
status: planung
stack: Python, PySide (Qt), FreeCAD-API (CAM-Workbench)
zielsystem: stabile FreeCAD-Version (1.1.3) und Wochen-Build, jedes Betriebssystem, keine bestimmte Maschine
patch_naming:
  pattern: "P-YYYY-MM-DD-XX <kurzbeschreibung>"   # im Commit-Betreff
  example: "P-2026-09-25-01 projektregeln"
---

# Verlauf (LOG/ARCHIV)

## P-2026-09-27-10 schnittwerte-job-erklaert

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-02; `camaddon/gui_job_schnittwerte.py`
  (Befehl), `camaddon/gui_maschine.py` (so machen es die anderen Befehle),
  `tests/gui/szenario_schnittwerte_job.py`.

### DATEIEN
- `camaddon/gui_job_schnittwerte.py`
- `translations/de.json`, `translations/en.json` (`sj.kein_job`)
- `tests/gui/szenario_schnittwerte_job.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Schnittwerte in den Job“ ist immer bedienbar; ohne Job im aktiven Dokument
sagt ein Satz, was zu tun ist.

### DONE
- `IsActive` immer wahr (wie „Maschine bearbeiten“, „Auf der Maschine
  prüfen“); ohne Job: „Im aktiven Dokument gibt es keinen CAM-Job. Öffne das
  Dokument mit dem Job – dann setzt dieser Befehl Drehzahl und Vorschub seiner
  Werkzeug-Controller aus der Werkzeugverwaltung.“
- Den Job auch in anderen offenen Dokumenten zu suchen ist D-21 (nicht hier).

### TEST
- `szenario_schnittwerte_job` in 1.1.3 ok – ruft den Befehl zuerst ohne
  Dokument auf und erwartet den Satz; `test_sprache` ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-03.

## P-2026-09-27-09 tooltip-pruefen

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-01; `camaddon/gui_reichweite.py`
  (Befehl), `tests/gui/szenario_erster_start.py`.

### DATEIEN
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_erster_start.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Tooltip von „Auf der Maschine prüfen“ nennt alle drei Prüfungen:
Achsgrenzen, Abfahren, Kollision.

### DONE
- „Prüft einen CAM-Job auf einer Maschine: Reichen die Achsen, wie fährt die
  Maschine die Bahn ab, stößt dabei etwas an?“ (englisch entsprechend).

### TEST
- `szenario_erster_start` in 1.1.3 ok – prüft jetzt auch diesen Tooltip.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-02.

## P-2026-09-27-08 gelenke-ausblenden

### EINGELESEN
- Die Bilder zu P-2026-09-27-07: In der Gesamtansicht lagen die
  Gelenkmarkierungen (weiße Scheiben mit Achsen) auf Revolver und Spindel;
  ohne sie war der Revolver zu sehen – Manuel: „Besser weiter“.
- `camaddon/beispielmaschine.py` (lade), die Stellen im Addon, die
  Sichtbarkeit nutzen (keine hängt an den Gelenken).

### DATEIEN
- `camaddon/beispielmaschine.py`
- `help/de/neue_maschine.html`, `help/en/neue_maschine.html`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Beispielmaschinen aus „Neue Maschine …“ und „Beispielmaschine laden …“
erscheinen ohne Gelenkmarkierungen; die Gelenke stehen weiter im Baum und
lassen sich mit der Leertaste zeigen, und die Hilfe sagt wie.

### DONE
- `lade()` blendet die Gelenkgruppe der Baugruppe aus (nur mit Oberfläche).
  Die Prüfungen bauen ihre Maschinen ohne `lade()` – für sie ändert sich
  nichts; eine selbst gebaute Baugruppe fasst das Addon nicht an.
- Hilfe „Neue Maschine“: ein Absatz, wie man die Gelenke zeigt.

### TEST
- Szenarien `beispielmaschine`, `neue_maschine`, `schraege_achse`,
  `verfahren_schraeg`, `mausrad` in 1.1.3 ok; die Übersicht aller fünf
  Beispielmaschinen angesehen – keine Markierungen mehr.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Durchsicht W-004: die kleinen Punkte D-01 bis D-08.

## P-2026-09-27-07 revolver-stationen

### EINGELESEN
- Manuel zum Screenshot der Drehmaschine: „Die Revolver … müsste man anders
  aufbauen, der Revolver ist da nicht sichtbar“; nach den Vorher-/Nachher-
  Bildern des Entwurfs: „Besser weiter“.
- `camaddon/beispielmaschine.py` (Baukasten, drehmaschine),
  `tests/beispielmaschinen.py` (Test-Drehmaschine), die Tests mit der
  Drehmaschine (Plätze, Werkzeugspitzen – sie rechnen aus den LCS, nicht mit
  festen Koordinaten), `help/*/neue_maschine.html`.

### DATEIEN
- `camaddon/beispielmaschine.py`
- `help/de/neue_maschine.html`, `help/en/neue_maschine.html`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Beispiel-Drehmaschine zeigt einen Revolver, den man als solchen erkennt:
rundum je Platz eine Station, die Scheibe heller als Schlitten und Bett;
Gelenk, Plätze und Werkzeuge bleiben, wo sie waren.

### DONE
- Befund in Bildern: Die Revolverscheibe war eine glatte Scheibe in der Farbe
  der Tische (grau wie die Schlitten), nur zwei Halter; von der Seite
  verdeckt, in der Gesamtansicht unter den Gelenkmarkierungen.
- Je Platz ab P2 eine Station (Block außen an der Scheibe, im Teilungswinkel
  gedreht, Breite 60 % der Teilung, höchstens 60 mm – so bleibt auch bei 24
  Plätzen Luft); P1 hat seinen radialen Halter. Die Scheibe bekommt die
  Farbe REVOLVER (hell). `Baukasten.quader(…, gedreht=…)`: eine Drehung im
  Rahmen, hier um die Revolverachse.
- Die Stationen gehören zum Bauteil „Revolver“ – die Kollision prüft sie
  mit (an der Maschine sitzen dort Halter).
- Die Test-Drehmaschine (`tests/beispielmaschinen.py`, ein Würfel als
  Revolver) bleibt: Sie spielt eine grob selbst gebaute Baugruppe, sogar mit
  senkrechter Spindel. Ihre Bilder zeige ich Manuel nicht mehr als „die
  Drehmaschine“.

### TEST
- Die Prüfungen mit der Drehmaschine in 1.1.3 ok (`test_abfahren`,
  `test_beispielmaschine`, `test_kette`, `test_maschine`, `test_reichweite`,
  `test_schraege_achse`); die Szenarien `beispielmaschine`,
  `neue_maschine`, `schraege_achse`, `verfahren_schraeg`, `mausrad` ok;
  Screenshots angesehen (Revolver in „Maschine bearbeiten“, alle fünf
  Beispielmaschinen).
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel schaut sich den Revolver in seinem FreeCAD an („Neue Maschine …“ →
  Drehmaschine mit Y-Achse).

## P-2026-09-27-06 durchsicht-bedienbarkeit

### EINGELESEN
- Manuels Auftrag: „noch einmal schauen, ob alles so benutzer-/bedienerfreundlich
  und einfach ist wie möglich und ob man Sachen noch automatisieren könnte …
  Schreibe diese auf.“
- `docs/arbeitsregeln.md` (Abschnitte 0, 1, 6, 8), `CHATSTART.md`,
  `docs/STATUS_SNAPSHOT.md` (Wunschliste).
- Screenshots aller 30 Szenarien in FreeCAD 1.1.3 (frischer Lauf auf
  5df5005); dazu im Code: `gui_start.py` (Befehle, Werkzeugleiste),
  `gui_reichweite.py` (Job- und Maschinensuche, Aufbau des Fensters),
  `gui_maschine.py` (Meldung ohne Baugruppe, neue Betriebsart),
  `maschine.py` (Kennwerte), `verfahren.py` (Reihenfolge der Achsen),
  `gui_schruppwerte.py` (Maschinengrenzen, Beispielwerte, gemerkte Werte),
  `job_schnittwerte.py`, `gui_aktualisierung.py`, `gui_sprachwahl.py`,
  `sprache.py`.

### DATEIEN
- `docs/durchsicht_bedienbarkeit.md` (neu)
- `docs/STATUS_SNAPSHOT.md` (W-004, Hinweis beim nächsten Schritt)
- `CHATSTART.md` (Zeile in der Lesekarte)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Befunde der Durchsicht stehen je mit Beleg, Vorschlag, „Fertig, wenn“ und
Aufwand in `docs/durchsicht_bedienbarkeit.md`, als W-004 in der Wunschliste,
mit einer Reihenfolge und den offenen Fragen als Auswahl mit Empfehlung.

### DONE
- 24 Befunde: acht kleine Stellen (D-01 bis D-08: veralteter Tooltip, grauer
  Knopf ohne Erklärung, Achsen im Verfahren in Kettenreihenfolge, kein
  „Jetzt neu starten“, Auswahl leuchtet, Rückmeldung ohne den kurzen Weg,
  Spanneisen nicht erwähnt, zwei Namen für dasselbe Fenster), fünf zum
  einfacheren Bedienen (D-10 bis D-14) und elf zum Automatisieren (D-20 bis
  D-30).
- Beim Nachprüfen im Code korrigiert, bevor es ins Dokument kam: Der Planer
  merkt sich Drehzahl, Vorschub und Leistung (nur nicht je Maschine); der
  Platzhalter heißt „bitte eintragen“; „Beispielmaschine laden …“ öffnet
  wirklich das Fenster von „Neue Maschine …“; die Sprache folgt schon der von
  FreeCAD (kein Befund).
- Nicht bestätigt und deshalb kein Befund: der abgeschnittene Text auf der
  Einstellungsseite – das Szenario zwingt die Seite auf 500 × 320 Pixel.

### TEST
- Nur Doku. Die Szenarien liefen für die Screenshots in 1.1.3 alle grün
  (`scripts/oberflaeche_testen.sh`, 30 × ok). Geprüft hat Claude anhand von
  Screenshots; ob die Fenster verständlich sind, prüft Manuel.

### NEXT
- Manuel wählt die Reihenfolge und beantwortet die Fragen in Abschnitt 6;
  D-01 bis D-08 brauchen keine Entscheidung.

## P-2026-09-27-05 snapshot-nachbesserungen

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md` (Projektstatus, W-001).

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot nennt die Nachbesserungen P-2026-09-27-02 bis -04.

### DONE
- Projektstatus W-001, 4c: ein Satz zu den Nachbesserungen (Schneide nach
  Art, halbe Zahl im Feld, Spaltenköpfe im Halter-Fenster).

### TEST
- Nur Doku; der Gesamtlauf für P-2026-09-27-02 bis -05 läuft vor dem Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-27-04 halter-spaltenkoepfe

### EINGELESEN
- Screenshot `szenario_halter/2_er32.png` aus dem Gesamtlauf für 0.24.0: Die
  Überschrift „Ø unten (mm)“ der Kontur-Tabelle war abgeschnitten („(mm]“).
- `camaddon/gui_halter.py` (_bereich_halter, Tabelle).

### DATEIEN
- `camaddon/gui_halter.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Fenster „Halter“ sind alle drei Überschriften der Kontur-Tabelle ganz zu
lesen, auch in der Standardgröße des Fensters; die Breite richtet sich nach
den Überschriften der gewählten Sprache.

### DONE
- Die Spalten bleiben gleich breit (gedehnt); die Tabelle ist mindestens so
  breit, dass die längste Überschrift in jede Spalte passt – gemessen in
  fetter Schrift: Solange eine Zeile gewählt ist, zeigt Qt die Überschriften
  fett (der erste Versuch mit `sectionSizeHint` rechnete mit normaler
  Schrift und reichte nicht). Dazu Rand, Zeilennummern und Rahmen; das
  Fenster wird dadurch etwa 20 Pixel breiter.

### TEST
- `szenario_halter` in 1.1.3 und im Wochen-Build: Screenshot `2_er32.png`
  angesehen – alle drei Überschriften ganz zu lesen, auch „Ø unten (mm)“.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-27-03 halbe-zahl-im-feld

### EINGELESEN
- `camaddon/gui_zahlen.py` (Zahlenpruefer: „,“ und „-“ sind ein Zwischenstand;
  `groesse_lesen` wirft dann ValueError), `camaddon/einheiten.py`
  (zahl_aus_text).
- `camaddon/gui_halter.py` (Spanntiefe, OK), `camaddon/gui_kollision.py`
  (Warnabstand), `camaddon/gui_reichweite.py` (Nullpunkt, Uhr),
  `camaddon/gui_werkzeuge.py` (_zahl_uebernehmen vor dem Speichern),
  `camaddon/gui_werkstoffe.py` (OK: kc, mc); alle übrigen Aufrufe von
  `zahl_lesen`/`groesse_lesen` fangen den Fehler schon ab.
- `tests/gui/_lauf/szenario_lauf.py` (Ausnahmen in Qt-Slots fängt es nicht).

### DATEIEN
- `camaddon/gui_halter.py`, `camaddon/gui_kollision.py`,
  `camaddon/gui_reichweite.py`, `camaddon/gui_werkzeuge.py`,
  `camaddon/gui_werkstoffe.py`
- `tests/gui/szenario_halter.py`, `tests/gui/szenario_kollision.py`,
  `tests/gui/szenario_reichweite.py`, `tests/gui/szenario_werkzeugverwaltung.py`,
  `tests/gui/szenario_werkstoffe.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Feld, in dem noch keine Zahl steht („,“ oder „-“, das der Prüfer beim
Tippen zulässt), führt zu keinem Fehler: Im Halter-Fenster schließt OK, die
Spanntiefe bleibt; „Kollision prüfen“ rechnet mit dem Warnabstand der Vorgabe;
im Nullpunkt zählt „-“ wie ein leeres Feld (der Vorschlag); OK in der
Werkzeugverwaltung und im Werkstoff-Fenster speichert, das Feld behält den
alten Wert.

### DONE
- Beim Durchsehen gefunden: `groesse_lesen(",")` wirft ValueError. Im
  Halter-Fenster schloss OK dann nicht (Traceback im Ausgabefenster);
  „Kollision prüfen“ tat nichts; im Nullpunkt – wer „-50“ tippt und nach dem
  „-“ kurz innehält – warf die Uhr des Fensters einen Traceback, und die
  Anzeige blieb auf dem alten Stand (seit 4a). Ebenso OK in der
  Werkzeugverwaltung (das Zahlenfeld mit dem Fokus wird vor dem Speichern
  gelesen) und im Werkstoff-Fenster (kc, mc): Das Fenster blieb offen.
- Spanntiefe: Unlesbares bleibt, wie es war (wie in der Kontur-Tabelle).
- Warnabstand: `_eingetragen()` – leer oder unlesbar 0, dann die Vorgabe;
  gemerkt wird nur, was lesbar eingetragen ist.
- Nullpunkt: `eingetragen()` lässt ein Feld ohne Zahl weg wie ein leeres.
- Werkzeugverwaltung: ein Feld ohne Zahl zeigt wieder den gespeicherten
  Wert; Werkstoff-Fenster: kc und mc bleiben, wie sie waren.

### TEST
- `szenario_halter`: „,“ in der Spanntiefe, OK → das Fenster ist zu, die
  Spanntiefe 40 (ER32) geblieben.
- `szenario_kollision`: „,“ als Warnabstand, „Kollision prüfen“ → Ergebnis
  mit 1 mm, ein Satz.
- `szenario_reichweite`: X „300“ (rot), dann „-“ → grün wie mit leerem Feld.
- `szenario_werkzeugverwaltung`: „,“ im Eckenradius von T2, OK → zu,
  gespeichert 0,5.
- `szenario_werkstoffe`: neuer Werkstoff „Buche“ mit „,“ in kc, OK → zu,
  kc unbekannt (0).
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-27-02 schneide-nach-art

### EINGELESEN
- `camaddon/kollision.py` (werkzeugkoerper), `camaddon/reichweite.py`
  (Werkzeugmasse, werkzeugmasse), `camaddon/werkzeuge.py` (reichweite, mass,
  ANTEIL_VON_D, Felder je Art), `camaddon/gui_abfahren.py` (_werkzeug).
- `docs/spezifikation_simulation.md`, 4b (Werkzeug) und 4c (Was gegen was).

### DATEIEN
- `camaddon/werkzeuge.py`, `camaddon/reichweite.py`, `camaddon/kollision.py`
- `tests/test_kollision.py`
- `docs/spezifikation_simulation.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Abfahren und Kollision bauen die Schneide wie die Reichweite
(`wz.reichweite`): beim Nutenfräser so hoch wie die Schneidenbreite, beim
Lollipopfräser als Kugel mit D, der Hals ab ihrer Mitte; die übrigen Arten
wie bisher (Schneidenlänge, leer geschätzt). Ein Werkzeug nur aus CAM: die
Schneide aus CuttingEdgeHeight, sonst CuttingEdgeLength, sonst BladeThickness,
erst dann 2 × D.

### DONE
- Beim Durchsehen von 4c gefunden: `werkzeugmasse` nahm immer die
  Schneidenlänge. Nutenfräser und Lollipopfräser haben dieses Feld nicht –
  es galt die Schätzung 2 × D. Ein Nutenfräser Ø 20 war so ein 40 mm hoher
  Zylinder statt einer Scheibe (falsche Berührungen im Eilgang und mit
  Spannmitteln); beim Lollipop saßen Hals und Schaft 1,5 × D zu hoch (eine
  Berührung des Schafts konnte durchrutschen).
- `wz.schneide(werkzeug)`: von der Spitze bis zum Hals – Lollipop D/2,
  Nutenfräser Schneidenbreite, sonst Schneidenlänge; `wz.reichweite` rechnet
  damit (gleiche Werte wie bisher).
- `Werkzeugmasse.kugel` (Lollipop) und `schneide` aus `wz.schneide`;
  `werkzeugkoerper` baut beim Lollipop eine Kugel. Das Bild im Abfahren
  zeigt dieselben Körper.
- Ein Werkzeug nur aus CAM (nicht in der Werkzeugverwaltung): die Schneide
  auch aus CuttingEdgeLength (Gewindebohrer) und BladeThickness
  (Scheibenfräser) – wie beim Übernehmen aus CAM; sonst war eine Säge Ø 50
  ein 100 mm hoher Zylinder.

### TEST
- `tests/test_kollision.py`: Lollipop Ø 5 – Kugel (Volumen, ab Z −60), Hals
  −57,5 … −47,5, Schaft bis −10; Nutenfräser Ø 5 – Scheibe −60 … −59,5,
  Hals −59,5 … −58,25 mit Ø 1,5; eine Säge nur aus CAM (Ø 50, Blatt 3):
  Schneide 3, Schaft 10, Länge 40.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-27-01 ok-meldung-hinter-fortschritt

### EINGELESEN
- `scripts/tests_ausfuehren.sh`, `scripts/alle_tests.sh`, `docs/aufbau.md`
  (Abschnitt Prüfungen).
- Protokoll des Gesamtlaufs für 0.24.0 (P-2026-09-26-99): in 1.1.3
  „FEHLER test_kollision.py“, obwohl die Prüfung durchlief – die Zeile war
  `\t…(60 %)\tOK test_kollision.py`.

### DATEIEN
- `scripts/tests_ausfuehren.sh`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`OK <datei>` zählt auch, wenn FreeCADCmds Fortschritt („(60 %)“ mit
Tabulatoren und Wagenrücklauf, ohne Zeilenumbruch) davor auf derselben Zeile
steht; ebenso `UEBERSPRUNGEN <datei>: Grund`. Eine Ausgabe ohne diese Meldung
am Zeilenende bleibt ein Fehler.

### DONE
- FreeCADCmd schreibt seinen Fortschritt ohne Zeilenumbruch; wann die
  OK-Meldung der Prüfung dazwischenkommt, ist Zufall (ein zweiter Lauf von
  `test_kollision.py` allein hatte sie auf eigener Zeile). Das Skript sucht
  `OK <datei>` jetzt am Zeilenende, am Zeilenanfang oder nach Leerraum statt
  als ganze Zeile; `UEBERSPRUNGEN` ebenso, den Grund liest es mit `sed`.

### TEST
- Mit einem nachgemachten FreeCADCmd: OK hinter Fortschritt → ok,
  UEBERSPRUNGEN hinter Fortschritt → skip mit Grund, `OK <datei>X` und eine
  Ausnahme → FEHLER.
- Die aufgezeichnete Zeile aus dem Protokoll: alte Suche FEHLER, neue ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Push 0.24.0 (P-2026-09-26-94 bis P-2026-09-27-01) nach grünem Gesamtlauf.

## P-2026-09-26-99 version-0-24-0

### EINGELESEN
- Spezifikationen Halter (Schritte 1–3) und 4c (Schritte 1–2), alle gebaut
  (P-2026-09-26-94 bis -98).
- `package.xml`, README, „Über“ (0.23.0, P-2026-09-26-91).

### DATEIEN
- `package.xml` (0.24.0, Beschreibung)
- `README.md` (Kollision unter „Auf der Maschine prüfen“, Halter in der
  Werkzeugverwaltung)
- `translations/de.json`, `translations/en.json` („Über“)
- `docs/STATUS_SNAPSHOT.md`, `docs/spezifikation_simulation.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Version 0.24.0; README, Beschreibung für den Addon-Manager und „Über“ nennen
Halter und Kollisionsprüfung; `scripts/alle_tests.sh` in beiden
FreeCAD-Versionen grün.

### DONE
- Version 0.24.0: Halter (W-002 Stufe D) und Kollision (W-001 Stufe 4c).
- README, Addon-Manager, „Über“: Halter mit Kontur und Vorlagen; die
  Kollisionsprüfung von Werkzeug, Halter und Maschine gegen Teil, Spannmittel
  und Maschine.
- Snapshot: Halter und 4c fertig, Klickweg zum Ausprobieren (Punkt 7);
  danach Manuels Test, offen 4d und W-003 V2.

### TEST
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-26-98 kollision-fenster

### EINGELESEN
- `docs/spezifikation_simulation.md`, 4c, Schritt 2; Abschnitt 12
  (Akzeptanzkriterien 4c).
- `gui_reichweite.py` (Fenster, Abspieler, Bild), `gui_abfahren.py` (Bild,
  Lupe), `kollision.py` (P-2026-09-26-97).

### DATEIEN
- `camaddon/gui_kollision.py` (neu)
- `camaddon/gui_reichweite.py` (Bereich „Kollision“ unter „Abfahren“, Klick
  auf einen Befund, Sperren während der Prüfung, Erklärung oben)
- `camaddon/gui_abfahren.py` (rote Kugel `markiere`, `zeige_stelle`)
- `camaddon/kollision.py` (Fortschritt alle 0,1 s mit Abbrechen, auch mitten
  in langen Wegen; Berührungen zuerst)
- `camaddon/beispielmaschine.py` (Spanneisen immer, 60 mm hoch)
- `translations/de.json`, `translations/en.json` (13 Texte, Erklärung oben)
- `help/de/reichweite.html`, `help/en/reichweite.html` (Abschnitt „Kollision“)
- `tests/test_kollision.py`, `tests/gui/szenario_kollision.py` (neu)
- `docs/spezifikation_simulation.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Fräse, kurzes Werkzeug (25 mm) neben dem rechten Spanneisen in die
Tiefe → „Kollision prüfen“ → rot „Es stößt etwas an:“ und „In „Eigene“
berühren sich „Spindel“ und „Spanneisen_rechts“ (Satz 4, bei X 110, Y 30, Z
34).“ → Klick → die Maschine steht dort, die Ansicht zeigt die Stelle mit
einer roten Kugel.

### DONE
- Bereich „Kollision“: Warnabstand (leer 1 mm, gemerkt), „Kollision prüfen“ –
  während der Prüfung Fortschrittsbalken, der Knopf heißt „Abbrechen“, Job,
  Nullpunkt, Liste und Abspieler sind gesperrt. Urteil grün („Nichts berührt
  sich, nichts kommt näher als 1,00 mm.“), rot („Es stößt etwas an:“) oder
  gelb; je Befund ein Satz in Rot oder Gelb, Berührungen zuerst; Hinweise
  grau. Neuer Job, Nullpunkt oder Aufnahme: „Noch nicht geprüft …“.
- Klick auf einen Satz: Abspieler auf die Zeit der Stelle, rote Kugel (2 mm,
  mit Hof, obenauf gezeichnet), die Ansicht rückt die Stelle in die Mitte.
  Fährt der Abspieler weiter, verschwindet die Kugel.
- Schließen während der Prüfung bricht sie ab, ohne noch etwas zu zeigen.
- Beispiel-Fräse: die zwei Spanneisen immer, 60 mm hoch (mit 30 mm reichte
  die Spindelnase in ihrer tiefsten Stellung genau bis obenauf – anstoßen
  ging nur am Anschlag, im Screenshot gesehen).

### TEST
- `szenario_kollision` (neu) in 1.1.3 und im Wochen-Build grün, Screenshots
  angesehen: Urteil, Satz, Klick → Abspieler, Kugel, Ansicht auf der Stelle;
  Warnabstand 10 → gelbe Sätze dazu; neuer Nullpunkt → „Noch nicht geprüft“;
  Schließen räumt auf. `szenario_abfahren` in beiden grün.
- `test_kollision` (angepasst an die 60-mm-Spanneisen: Spindel setzt bei Z
  34 auf, Satz 4; Eilgang-Fall mit 80 mm Werkzeug, weil mit 50 mm die Spindel
  1 mm über die Spanneisen fährt – zu Recht gemeldet), `test_beispielmaschine`,
  `test_sprache`, `test_hilfe` grün; black, ruff sauber.

### NEXT
- Version 0.24.0, voller Lauf in beiden Versionen, Push, Bericht.

## P-2026-09-26-97 kollision-rechenkern

### EINGELESEN
- `docs/spezifikation_simulation.md`, 4c (P-2026-09-26-93), Schritt 1.
- `abfahren.py` (Stationen, wirksame Stellungen), `reichweite.py`
  (`_glied_lage`, `_lage`, `_job_lage`), `verfahren.py` (Ausgang, Wege,
  Grenzen), `kette.py` (Glieder, Achsen, Eltern und Kind), `halter.py`.
- Messung aus P-2026-09-26-93: `distToShape` 2–3 ms, 0 für „steckt drin“.
- Probe: `Part.getShape(bauteil, transform=False)` gibt die Form in eigenen
  Koordinaten; an ihren Ausgang gesetzt, liegt sie wie im Dokument.

### DATEIEN
- `camaddon/kollision.py` (neu)
- `camaddon/reichweite.py` (`Werkzeugmasse`, `werkzeugmasse`,
  `werkzeughalter` – aus gui_abfahren.py hierher, mit Hals)
- `camaddon/halter.py` (`form`: der Halter als Körper)
- `camaddon/abfahren.py` (`zeit_text` aus gui_abfahren.py hierher)
- `camaddon/gui_abfahren.py` (zeigt dieselben Werkzeugkörper, die geprüft
  werden)
- `camaddon/beispielmaschine.py` (`fraesmaschine(spanneisen=True)`)
- `translations/de.json`, `translations/en.json` (15 Texte)
- `tests/test_kollision.py` (neu)
- `docs/spezifikation_simulation.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
An der Beispiel-Fräse mit Spanneisen meldet die Prüfung für die Bahnen aus
`test_kollision` genau die von Hand nachgerechneten Berührungen und Warnungen
– Schaft an der Taschenwand, Eilgang durchs Teil, Halter zu tief, Spindel auf
dem Spanneisen – und sonst nichts.

### DONE
- Körper: Schneide, Hals, Schaft (bis zur Nase des Halters, ohne Halter bis
  zur Gesamtlänge) und Halter im LCS der Werkzeugaufnahme
  (`werkzeugkoerper`); das fertige Teil (Modelle des Jobs) am Nullpunkt; jedes
  Bauteil der Maschine in eigenen Koordinaten an seinem Glied. Lage zur Zeit t
  = Bewegung des Glieds · Lage im Ausgang, Achsen auf ihre Grenzen gesetzt.
- Paare je Werkzeugglied: Werkzeugseite (Werkzeug und die Glieder, die es
  tragen) gegen Werkstückseite (Teil und die Glieder, die es tragen) und
  Rest, Werkstückseite gegen Rest; die Schneide gegen das Teil nur im Eilgang.
  Paare aus Maschinenteilen oder Teil und Maschinenteil, die sich in der
  Grundstellung berühren, fallen weg – mit Hinweis nur, wenn sie nicht an
  einem gemeinsamen Gelenk hängen.
- Abtasten: je Weg zwischen zwei Stationen Schritte von höchstens (kleinster
  Abstand − Warnabstand) / Weg, mindestens 0,5 mm; Drehachsen zählen mit der
  Diagonale über alles je Grad. Hüllquader weiter als Warnabstand + 5 mm:
  kein genauer Abstand. Höchstens 200 000 Stellen; Fortschritt mit Abbrechen.
- Ergebnis: je Operation und Paar die schlimmste Stelle (bei Gleichstand die
  erste) als Satz – „In „Eigene“ berühren sich der Schaft von T1 und das Teil
  (Satz 5, bei X 67.5, Y 30, Z 8).“, „… kommen sich … auf 0.50 mm nahe …“, mit
  „im Eilgang“; dazu Zeit, Station, Stelle (für Abspieler und Markierung);
  Hinweise (ohne Halter geprüft, kein Modell, nicht rechenbar, abgebrochen).
- Die Beispiel-Fräse kann zwei Spanneisen tragen (am Tisch-Glied).
- Das Abfahren zeigt jetzt genau die Werkzeugkörper, die geprüft werden.

### TEST
- `test_kollision` (neu) in 1.1.3 und im Wochen-Build grün, je rund 4 s:
  frei in der Tasche nichts (unter 200 Stellen); Schaft an der Wand –
  Berührung, Satz 5, Stelle x 402,5 (die Wand unter der Spindel); Schaft Ø 4
  – Warnung 0,50 mm; Eilgang durchs Teil – Schneide und Schaft „im Eilgang“,
  erste Berührung bei X −2,5; derselbe Weg im Vorschub – nur der Schaft;
  Halter ER16 1 mm zu tief – Berührung; Spindel auf dem Spanneisen – bei Z
  knapp unter 4; 4 mm darüber nur mit Warnabstand 5; kein Hinweis zu
  Führungen; Abbrechen.
- `test_abfahren`, `test_reichweite`, `test_halter`, `test_beispielmaschine`,
  `test_sprache` grün; `szenario_abfahren` grün; black, ruff sauber.

### NEXT
- 4c Schritt 2: Bereich „Kollision“ im Fenster „Auf der Maschine prüfen“.

## P-2026-09-26-96 halter-laenge-abfahren

### EINGELESEN
- `docs/spezifikation_halter.md`, Schritt 3 (Abschnitt 7: wo der Halter wirkt).
- `camaddon/reichweite.py` (`werkzeuglaenge`, Hinweise zur Länge),
  `camaddon/gui_abfahren.py` (Bild: Werkzeug, angedeuteter Halter).

### DATEIEN
- `camaddon/reichweite.py` (Quelle LAENGE_HALTER, Hinweis)
- `camaddon/gui_abfahren.py` (`halter_von`, Halter mit Kontur im Bild)
- `translations/de.json`, `translations/en.json` (1 Text)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_reichweite.py`, `tests/gui/szenario_abfahren.py`
- `docs/spezifikation_halter.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Werkzeug der Werkzeugverwaltung mit Halter und ohne gemessene Länge ab
Spindelnase: „Auf der Maschine prüfen“ rechnet mit Halterlänge + Gesamtlänge
− Spanntiefe und sagt es; beim Abfahren steckt das Werkzeug in diesem Halter,
mit seiner Kontur.

### DONE
- `werkzeuglaenge`: gemessen vor Halter; sonst mit dem Halter geschätzt
  (`LAENGE_HALTER`), Hinweis „gerechnet mit 100,00 mm, geschätzt aus Halter und
  Werkzeug (…) – genauer mit der gemessenen Länge ab Spindelnase“; ohne Halter
  wie bisher.
- Abfahren: je Operation der Halter ihres Werkzeugs (`Bild.halter`), je
  Abschnitt ein Zylinder oder Kegel (Part, als Dreiecke) ab der Aufnahme –
  stahlgrau, nicht durchscheinend; ohne Halter wie bisher angedeutet.
- Hilfe „Auf der Maschine prüfen“: Halter im Abfahren und in der Länge.

### TEST
- `test_reichweite` (neu: ER16 70 mm + 50 − 20 = 100 mm, Z1 −38 … −20,
  Hinweis; gemessen geht vor), `test_abfahren`, `test_halter`, `test_hilfe` grün
  in 1.1.3 und im Wochen-Build; `szenario_abfahren` (jetzt mit T1 in der
  Werkzeugverwaltung und Halter ER16: Halter im Bild, Hinweis zur Länge) und
  `szenario_reichweite` grün in beiden Versionen, Screenshot angesehen: Flansch,
  Kegel und Mutter unter der Spindel, darunter Schaft und Schneide.

### NEXT
- 4c Schritt 1: Rechenkern Kollision.

## P-2026-09-26-95 halter-fenster

### EINGELESEN
- `docs/spezifikation_halter.md`, Schritt 2 (Skizze in Abschnitt 5).
- `camaddon/gui_werkstoffe.py` (Fenster aus der Werkzeugverwaltung, Muster),
  `camaddon/gui_werkzeuge.py` (Felder, Anordnung, Platzhalter),
  `camaddon/gui_schnittwerte.py` (Zahlen in Tabellen), `gui_werkzeugbild.py`.

### DATEIEN
- `camaddon/gui_halter.py` (neu)
- `camaddon/gui_werkzeuge.py` (Feld „Halter“ mit „Halter …“, Platzhalter der
  Länge ab Spindelnase mit Halter)
- `camaddon/hilfe.py`, `help/de/halter.html`, `help/en/halter.html` (neu),
  `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `translations/de.json`, `translations/en.json` (38 Texte, 1 geändert)
- `tests/gui/szenario_halter.py` (neu)
- `docs/spezifikation_halter.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Werkzeug mit Gesamtlänge 83 → „Halter …“ → „Neu“ →
„Spannzangenfutter ER32 · SK40“ → Tabelle 16/63/63 und 54/50/50, „Länge 70,00
mm · größter Ø 63,00 mm“, Bild mit Werkzeug → OK → beim Werkzeug ist der
Halter gewählt, das leere Feld „Länge ab Spindelnase“ zeigt grau „leer: 113
mit Halter“.

### DONE
- Fenster „Halter“: links Suche, Liste nach Namen, „Neu“ mit Menü (leer oder
  eine der elf Vorlagen), „Kopieren“, „Löschen“ (Rückfrage nennt die Werkzeuge,
  die ihn benutzen); rechts Name, Bezeichnung, Spanntiefe, die Kontur als
  Tabelle (Länge, Ø oben, Ø unten – nur Zahlen, im gewählten Maßsystem),
  „+ Abschnitt“ (unter dem gewählten, so dick wie dessen Ende) und „−
  Abschnitt“ (einer bleibt), darunter Länge und größter Ø, wer ihn benutzt,
  daneben das Bild: Spindel, Halter im Schnitt, Werkzeug bis zur Spitze.
- Gearbeitet wird an einer Kopie der Bibliothek; über OK steht grau, was OK
  tut („OK: T1 bekommt den Halter …“). OK übernimmt Halter und Zuordnungen,
  Abbrechen verwirft; gespeichert wird mit der Werkzeugverwaltung.
- Werkzeugverwaltung: unter der Länge ab Spindelnase die Zeile „Halter“
  (Auswahl „– ohne –“ und alle Halter, dazu „Halter …“) über die ganze Breite
  – im ersten Screenshot war „SK40 ER32 A70“ abgeschnitten. Der Platzhalter
  der Länge ab Spindelnase rechnet mit dem Halter.
- Hilfeseite „Halter“ (de, en), Verweis aus der Hilfe der Werkzeugverwaltung.

### TEST
- `szenario_halter` (neu), `szenario_werkzeugverwaltung`, `szenario_felder` in
  1.1.3 und im Wochen-Build grün, Screenshots angesehen; `test_sprache`,
  `test_hilfe` grün; black, ruff sauber.

### NEXT
- Schritt 3: Länge in „Auf der Maschine prüfen“, Halter im Abfahren.

## P-2026-09-26-94 halter-datenmodell

### EINGELESEN
- `docs/spezifikation_halter.md` (P-2026-09-26-93), Schritt 1.
- `camaddon/werkzeuge.py` (Werkzeug, Bibliothek, Speicherung, `reichweite`,
  `laenge_fuer_cam`), `tests/test_werkzeuge.py`.

### DATEIEN
- `camaddon/halter.py` (neu)
- `camaddon/werkzeuge.py` (Werkzeug.halter, `laenge_mit_halter`,
  Bibliothek.halter mit Anlegen, Kopieren, Löschen, Suche, Länge ab
  Spindelnase; Speichern und Laden)
- `translations/de.json`, `translations/en.json` (13 Texte)
- `tests/test_halter.py` (neu)
- `docs/spezifikation_halter.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Halter aus der Vorlage „Spannzangenfutter ER32“ hat 70 mm Länge und die
Kontur Flansch Ø63 × 16, Körper Ø50 × 54; einem Werkzeug mit 83 mm
Gesamtlänge zugeordnet, gilt ohne gemessene Länge 113 mm ab Spindelnase;
gespeichert und geladen bleibt alles, wie es war.

### DONE
- `halter.Halter`: Kennung, Name, Bezeichnung, Spanntiefe, Abschnitte
  (Länge, Ø oben, Ø unten); `laenge`, `groesster_durchmesser`,
  `radius_bei(abstand)` (Kegel geradlinig, an Stufen der größere Radius,
  außerhalb 0), `kontur()` als Punkte. Elf Vorlagen mit typischen SK40-Maßen
  (ER16–ER40, Schrumpf Ø6/Ø12, Weldon, Hydrodehn, Aufsteckdorn, Bohrfutter,
  VDI30 axial), Bezeichnung „Beispielmaße – nach Katalog prüfen“.
- Werkzeug: Feld `halter` (Kennung). `laenge_mit_halter`: Halterlänge +
  Gesamtlänge (eingetragen, sonst geschätzt) − Spanntiefe, mindestens
  Halterlänge + Reichweite.
- Bibliothek: `halter`; `halter_von`, `laenge_ab_spindelnase` (gemessen, sonst
  mit Halter, sonst 0), `neuer_halter` (leer oder aus Vorlage, Name mit „(2)“,
  wenn es ihn gibt), `kopiere_halter`, `benutzt_von`, `entferne_halter` (die
  Werkzeuge sind danach ohne), `sortierte_halter`. Gespeichert unter
  `halter`; alte Dateien ohne Halter und Unlesbares gehen.

### TEST
- `test_halter` (neu) in 1.1.3 und im Wochen-Build grün; `test_werkzeuge`,
  `test_sprache` grün; black, ruff sauber.

### NEXT
- Schritt 2: Fenster „Halter“ und das Feld im Werkzeug.

## P-2026-09-26-93 spezifikation-halter-kollision

### EINGELESEN
- Manuels Antworten vom 2026-09-26: Halter „eigene Halter-Verwaltung“
  (nicht der empfohlene Zylinder je Werkzeug), 4c prüft gegen „fertiges Teil
  + Spannmittel“, meldet „Berührung + Warnabstand“, als Nächstes „4c
  Kollision“; dazu „eigenes Fenster“ für die Halter und „Länge gemessen,
  sonst geschätzt“.
- `docs/spezifikation_simulation.md` (4c-Entwurf, Fragen 4 und 5),
  `camaddon/werkzeuge.py` (Bibliothek, Werkzeug, Speicherung),
  `camaddon/gui_werkzeuge.py` (Aufbau des Dialogs), `beispielmaschine.py`.
- FreeCAD-Check: `Mod/CAM/Path/Tool` in 1.1.3 und im Wochen-Build kennt
  keinen Halter. Gemessen: `distToShape` zwischen Werkzeug mit Halter und
  Schraubstock bzw. Teil mit Tasche 2–3 ms, „steckt drin“ gibt 0; kein scipy,
  numpy da.

### DATEIEN
- `docs/spezifikation_halter.md` (neu)
- `docs/spezifikation_simulation.md` (Stand, 4c, Grenzen, Entscheidungen
  4, 5, 7, 8, Akzeptanzkriterien 4c)
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe D verweist)
- `docs/STATUS_SNAPSHOT.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer `docs/spezifikation_halter.md` und Abschnitt 5 (4c) der Simulation liest,
weiß, was ein Halter ist, wie die Werkzeugverwaltung ihn zeigt, wie 4c prüft
und was es meldet – mit Manuels Entscheidungen und den Schritten.

### DONE
- Halter-Spezifikation: Kontur in Abschnitten (Länge, Ø oben, Ø unten) ab der
  Spindelnase, Länge, Spanntiefe, Vorlagen; je Werkzeug ein Halter; Länge ab
  Spindelnase leer → Halterlänge + Gesamtlänge − Spanntiefe; Fenster mit
  ASCII-Skizze; Speicherung; drei Schritte; Entscheidungen (Manuel 1–3,
  Claude 4–7); Akzeptanzkriterien.
- 4c: was gegen was (Werkzeug gegen Teil – Schneide nur im Eilgang –,
  gegen Maschinenteile der anderen Seite; mitfahrende Maschinenteile gegen
  Werkstückseite und Teil; kein Rohteil; Paare, die sich in der
  Grundstellung berühren, nicht), Berührung rot, Warnabstand gelb (1 mm,
  einstellbar), Rechenweg mit `distToShape` und Schritten nach dem Abstand,
  Sätze wie 4a, auf Knopfdruck; zwei Schritte; Akzeptanzkriterien.

### TEST
- Nur Doku.

### NEXT
- Halter Schritt 1: Datenmodell, Speicherung, Vorlagen, geschätzte Länge.

## P-2026-09-26-92 abfahren-lupe

### EINGELESEN
- Screenshots aus `szenario_abfahren` (P-2026-09-26-90): Die Maschine ist
  groß, Teil und Werkzeug klein – fürs Szenario musste die Kamera von Hand
  heran; Manuel müsste das mit dem Mausrad tun.
- `gui_abfahren.py`, `gui_reichweite.py`.

### DATEIEN
- `camaddon/gui_abfahren.py` (`Bild.hinsehen`, Knopf mit Lupe, leere
  Achswert-Zeile ausgeblendet)
- `camaddon/gui_reichweite.py` (`_hinsehen`)
- `translations/de.json`, `translations/en.json` (1 Text)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/gui/szenario_abfahren.py`
- `docs/spezifikation_simulation.md`, `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Knopf im Bereich „Abfahren“ richtet die Ansicht auf Werkstück und
Werkzeug; ohne Stellung auf der Bahn bleibt keine leere Zeile stehen.

### DONE
- Knopf mit FreeCADs Lupe („Auswahl einpassen“) neben dem Tempo:
  `Bild.hinsehen()` richtet die Kamera auf Rohteil, Teil, Bahn und Werkzeug
  (Coin `viewAll` mit etwas Rand) und holt die 3D-Ansicht der Maschine nach
  vorn.
- Die Zeile mit den Achswerten ist ausgeblendet, solange die Maschine nicht
  auf der Bahn steht (vor dem ersten Abspielen) – vorher stand dort eine
  Lücke.
- Hilfe: die Lupe unter „Abfahren“.

### TEST
- `szenario_abfahren` (klickt jetzt die Lupe: Ausschnitt unter einem Drittel
  der ganzen Maschine, Symbol vorhanden) und `szenario_hilfe` in 1.1.3 und im
  Wochen-Build grün, Screenshots angesehen; `test_sprache` grün; black, ruff
  sauber.

### NEXT
- Voller Lauf, Push.

## P-2026-09-26-91 version-0-23-0

### EINGELESEN
- Spezifikation 4b, Schritt 3: Version, voller Lauf, Push.
- `package.xml`, README, „Über“ (0.22.0, P-2026-09-26-87).

### DATEIEN
- `package.xml` (0.23.0, Beschreibung)
- `README.md` (Abfahren unter „Auf der Maschine prüfen“)
- `translations/de.json`, `translations/en.json` („Über“)
- `docs/spezifikation_simulation.md`, `docs/STATUS_SNAPSHOT.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Version 0.23.0; README, Beschreibung für den Addon-Manager und „Über“ nennen
das Abfahren; `scripts/alle_tests.sh` in beiden FreeCAD-Versionen grün.

### DONE
- Version 0.23.0: Stufe 4b „Abfahren“ komplett (P-2026-09-26-88 bis -90).
- README, Addon-Manager und „Über“: Die Maschine fährt die Bahnen eines
  CAM-Jobs ab.
- Snapshot und Spezifikation: 4b fertig; als Nächstes 4c, sobald Halter und
  Mindestabstand entschieden sind.

### TEST
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push-Eintrag
  im Commit dieses Laufs.

### NEXT
- Manuel probiert 4a und 4b aus (Snapshot, „Manuel probiert aus“ Punkt 7).
- 4c (Kollision) nach seinen Entscheidungen zu Halter und Mindestabstand.

## P-2026-09-26-90 abfahren-abspieler

### EINGELESEN
- Spezifikation 4b (P-2026-09-26-88), Schritt 2: Anzeige und Abspieler im
  Fenster „Auf der Maschine prüfen“, Hilfe, Szenario mit Screenshots.
- `gui_reichweite.py` (Fenster, `fahre_hin`, Rückgängig-Schritt beim
  Verfahren), `abfahren.py` (P-2026-09-26-89), `verfahren.py`.

### DATEIEN
- `camaddon/gui_abfahren.py` (neu)
- `camaddon/gui_reichweite.py` (Bereich „Abfahren“, Bild in der 3D-Ansicht,
  Klick auf eine Überschreitung stellt den Abspieler dorthin)
- `camaddon/abfahren.py` (Umkehrstellen auf Kreisen, `station_von`,
  `stellungen_an`, Vorschubsatz nie schneller als der Eilgang)
- `camaddon/reichweite.py` (`_Bogen.anteile`)
- `camaddon/verfahren.py` (`setze_alle`)
- `translations/de.json`, `translations/en.json` (13 Texte, Erklärung oben)
- `help/de/reichweite.html`, `help/en/reichweite.html` (Abschnitt „Abfahren“,
  Werkzeuglänge mit Länge ab Spindelnase)
- `tests/test_abfahren.py`, `tests/gui/szenario_abfahren.py` (neu)
- `docs/spezifikation_simulation.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/aufbau.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Fenster „Auf der Maschine prüfen“ fährt die Maschine die Bahn des Jobs
ab: In ihrer 3D-Ansicht liegen Rohteil, Teil und Bahn, das Werkzeug steckt in
seiner Aufnahme, alles fährt mit; Abspielen, Anhalten, Punkt vor und zurück,
Tempo, Operation und Schieber tun, was sie sagen; eine Achse über der Grenze
steht rot „am Anschlag“; Schließen räumt alles weg und fährt zurück.

### DONE
- `gui_abfahren.Bild`: Werkzeug (Schneide gelb, Schaft grau bis zur
  Gesamtlänge, Halter durchscheinend, wenn die Länge ab Spindelnase länger
  ist – Maße aus der Werkzeugverwaltung, sonst vom CAM-Werkzeug), Rohteil
  durchscheinend, Modell fest, Bahn als Linien (Vorschub blau, Eilgang rot)
  – Coin-Knoten in der 3D-Ansicht der Maschine, nichts im Dokument. `folge()`
  setzt sie nach jeder Bewegung auf die LCS der Aufnahmen (das Werkstück mit
  dem Nullpunkt des Jobs); je Operation ihr Werkzeug an ihrer Aufnahme.
- `gui_abfahren.Abspieler`: Operation, Anfang, Punkt zurück,
  Abspielen/Anhalten, Punkt weiter, Tempo ×1/×5/×20/×100, Schieber über die
  Zeit; darunter „„Kontur“ · Satz 6 von 11 · 0:03,1 von 0:22,4“ und die
  Stellung jeder Achse (Linearachsen zuerst, nach Namen), rot „am Anschlag“.
  Der Satz ist der, der gerade läuft; vor und zurück gehen von Station zu
  Station, auch wenn zwei dieselbe Zeit haben (vorher blieb „zurück“ daran
  hängen – im Szenario gesehen).
- Im Fenster steht „Abfahren“ gleich unter dem Ergebnis, vor den grauen
  Zeilen – ohne Scrollen sichtbar. Ein neuer Nullpunkt rechnet neu und
  fährt die Maschine an dieselbe Zeit; ein Abspielen läuft weiter. Ein Klick
  auf eine Überschreitung stellt den Abspieler auf ihre Station.
- `abfahren.py`: Auf Kreisen auch die Umkehrstellen der Achsen (dort misst
  die Reichweite) – jede Überschreitung ist eine Station (`station_von`).
  Ein Vorschubsatz dauert mindestens so lange wie der Eilgang der Achsen:
  Schwenkt der Revolver in einem Satz ohne Weg, kostet das seine Zeit.
- `Verfahren.setze_alle`: alle Achsen auf einmal, die Bauteile bewegen sich
  einmal; zurück kommen die Achsen, die an einer Grenze halten.
- Hilfe „Auf der Maschine prüfen“: Abschnitt „Abfahren“ (Bedienung, Farben,
  wie die Zeit gerechnet wird); die Werkzeuglänge nennt jetzt die Länge ab
  Spindelnase.

### TEST
- `szenario_abfahren` in 1.1.3 und im Wochen-Build grün, Screenshots
  angesehen: Rohteil und Teil auf dem Tisch, Bahn darauf, Werkzeug in der
  Spindel; mitten auf der zweiten Geraden sitzt die Spitze auf dem Punkt der
  Bahn (auf 1e-6 mm), das Werkzeug im Bild an der Spindel; Abspielen ×100
  läuft bis zum Ende und hält an; Punkt zurück; zweite Operation „Satz 3
  von 7“; X 300 → Klick → X1 −250 rot „am Anschlag“; Schließen beim
  Abspielen → Körper weg, Maschine zurück.
- `szenario_reichweite` in beiden Versionen grün.
- `test_abfahren` (neu: Vollkreis mit vier Umkehrstellen, Station der
  Überschreitung, `stellungen_an`, `setze_alle`, Revolver im Vorschubsatz –
  ohne die Änderung 0 s, geprüft), `test_reichweite`, `test_verfahren`,
  `test_hilfe`, `test_sprache` grün; black, ruff sauber.

### NEXT
- Schritt 3: Version 0.23.0, voller Lauf in beiden Versionen, Push.
- Ob Anzeige und Bedienung verständlich sind, sieht nur Manuel (Snapshot,
  „Manuel probiert aus“ Punkt 7).

## P-2026-09-26-89 abfahren-rechenkern

### EINGELESEN
- Spezifikation 4b (P-2026-09-26-88), Schritt 1: Stationen mit Zeit,
  Stellungen zu jeder Zeit; Zeiten gegen Handrechnung prüfen.
- `reichweite.py`: `_bahn` liefert Punkte und Kreisbögen, `_pruefe_operation`
  rechnet je Operation Werkzeugaufnahme, Länge und die Lösung je Stellung der
  Rundachsen.

### DATEIEN
- `camaddon/abfahren.py` (neu)
- `camaddon/reichweite.py` (`_Schritt`; `achsen_fuer`, `gefahrene_achsen`,
  `loeser` öffentlich; Rückzug nach dem Bohrzyklus auf Wunsch)
- `translations/de.json`, `translations/en.json` (1 Text)
- `tests/test_abfahren.py` (neu)
- `docs/spezifikation_simulation.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Aus der Bahn eines Jobs entstehen Stationen, deren Zeiten der Handrechnung
entsprechen (100 mm mit F 10 = 10 s, Eilgang je Achse aus der Maschine);
zwischen zwei Stationen liefert `stellungen_bei` die geradlinig
dazwischenliegenden Stellungen.

### DONE
- `_bahn` liefert jetzt je Punkt und Kreis einen `_Schritt`: Art, Ort,
  Rundachsen, Eilgang oder Vorschub, das zuletzt gesetzte F, die Satznummer.
  Im Bohrzyklus gehen „über dem Loch“ und „auf R“ im Eilgang, der Grund im
  Vorschub; mit `rueckzug=True` kommt der Rückzug dazu (die Reichweite
  nutzt ihn nicht – ihre Punkte bleiben dieselben).
- Die Rechnung je Operation ist öffentlich: `achsen_fuer`,
  `gefahrene_achsen` (Linearachsen, Revolver, positionierende Rundachsen –
  keine Spindeln), `loeser` (Lösung je Stellung der Rundachsen, mit
  Zwischenspeicher); die Reichweite nutzt dieselben.
- `abfahren.abfahrt(pruefung, job, nullpunkt, bibliothek)`: Stationen mit
  Zeit, Operation, Satz, Punkt, Rundachsen, Stellungen (None, wo der Punkt
  nicht erreichbar ist) und Eilgang; Kreise in Schritten ≤ 5°. Zeit:
  Vorschub = Weg / F (FreeCAD: mm/s), dreht sich nur eine Rundachse, zählt
  ihr Winkel; ohne F 1000 mm/min mit Hinweis. Eilgang: jede Achse mit ihrem
  Eilgang (Linear), ihrer Geschwindigkeit (Positionieren) bzw. 180° je
  Schaltzeit (Revolver), die langsamste bestimmt; fehlt ein Wert, gilt der
  der Übergabe an CAM.
- `Abfahrt`: `dauer`, `index_bei(zeit)`, `wirksam(i)` (wie die Maschine dort
  steht – nicht erreichbar: bleibt stehen), `stellungen_bei(zeit)`
  (geradlinig zwischen zwei Stationen).

### TEST
- `test_abfahren`, 1.1.3 und Wochen-Build grün: Beispiel-Fräse – Achsen
  X1/Y1/Z1 ohne die Spindel; 62 Stationen; Geraden 1,5 s und 10 s; Kreis
  54 Sehnen zu 5°; Eilgang Z 0,06 s; Bohrzyklus 0,21 / 0,028 / 2,2 /
  0,072 s, Rückzug auf die Ausgangshöhe; Dauer; Mitte der Geraden X1 −50;
  vier Stationen gegen `Pruefung.stellungen`; ohne F 0,6 s mit Hinweis.
  5-Achs-Fräse A 90° mit F 10 in 9 s, halb geschwenkt A1 45. Drehmaschine:
  Revolver von P1 auf P2 zwischen zwei Operationen. Drehmaschine ohne Y:
  der Punkt quer daneben lässt die Maschine stehen.
- `test_reichweite`, `test_sprache` in beiden Versionen grün.

### NEXT
- Schritt 2: Anzeige und Abspieler im Fenster „Auf der Maschine prüfen“.

## P-2026-09-26-88 spezifikation-abfahren

### EINGELESEN
- Manuel (2026-09-26): „Ich kann aktuell nicht testen, bau das mit der
  Maschine“ – gemeint ist Stufe 4b (die Maschine fährt die Bahn sichtbar
  ab), die ich erst nach seinem Test von 4a bauen wollte.
- Entwurf 4b: Werkzeug als einfacher Körper, Rohteil an der
  Werkstückaufnahme, Abspielen/Anhalten/Schritt/Geschwindigkeit/Sprung zu
  einer Operation, Achswerte dazu.
- Ausprobiert in 1.1.3 und im Wochen-Build: F steht in den Bahnen in mm/s
  (Werkzeug-Controller 600 mm/min → F 10, 120 mm/min → F 2); der
  Standard-Controller eines neuen Jobs hat Vorschub 0; in der Operation
  „Eigene“ steht F, wie getippt. Eilgang steht nicht in der Bahn.

### DATEIEN
- `docs/spezifikation_simulation.md` (Kopf, 4b, Abschnitt 6, neu
  Abschnitt 11)
- `docs/STATUS_SNAPSHOT.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation sagt genau, was 4b zeigt, wie es rechnet und wie man es
bedient – so, dass danach gebaut werden kann –, und kennzeichnet die
Entscheidungen als Claudes, zur Besprechung.

### DONE
- 4b-Entscheidungen (Claude): nur Coin-Knoten in der 3D-Ansicht der
  Maschine, nichts im Dokument; Werkzeug als Zylinder – Schneide, Schaft,
  Halter angedeutet (Ø 2 × Schaft, mindestens 25 mm), bis Frage 4
  entschieden ist; Rohteil durchscheinend, Modell fest, Bahn als Linie
  (Vorschub blau, Eilgang rot), alles an der Werkstückaufnahme; Zeit aus F
  (mm/s) bzw. 1000 mm/min mit Hinweis, Eilgang je Achse aus der Maschine
  (fehlt: 10 000 mm/min), die langsamste bestimmt; Kreise in Schritten
  ≤ 5°, Rückzug nach dem Bohrzyklus; Bedienung (Operation, Anfang, Punkt
  zurück/vor, Abspielen/Anhalten, Tempo ×1/×5/×20/×100, Schieber) und
  Anzeige (Operation, Satz, Zeit, Achswerte); am Anschlag bleibt die Achse
  stehen, rot; ein Klick auf eine Überschreitung stellt auch den
  Abspieler.
- Drei Schritte: Rechenkern `abfahren.py`, Anzeige und Abspieler, Version.
- Abschnitt 11: Akzeptanzkriterien 4b (Abspielen, Anschlag, Zeiten gegen
  Handrechnung, Schließen ohne Spur).

### TEST
- Reine Doku.

### NEXT
- Schritt 1: Rechenkern `abfahren.py` mit Prüfungen.

## P-2026-09-26-87 version-0-22-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit 0.21.0:
  „Auf der Maschine prüfen“ (W-001 Stufe 4a, P-2026-09-26-83 bis -86).

### DATEIEN
- `package.xml` (0.22.0, Beschreibung)
- `README.md` („Was es kann“)
- `translations/de.json`, `translations/en.json` (Text „Über“)
- `docs/STATUS_SNAPSHOT.md` (Projektstatus, Punkt 13, „Danach“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.22.0 und nennt
das Prüfen der Verfahrwege; die README hat den Punkt „Auf der Maschine
prüfen“.

### DONE
- Version 0.21.0 → 0.22.0; Beschreibung für den Addon-Manager um „check a
  CAM job's paths against its travel limits“ ergänzt.
- README: Punkt „Auf der Maschine prüfen“ nach „Maschine verfahren“.
- „Über“: „… an CAM übergeben und prüfen, ob ihre Verfahrwege für die
  Bahnen eines CAM-Jobs reichen“ (de/en).
- Stand: W-001 bis 4a fertig und geprüft, danach 4b; Punkt 13 komplett.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push nach `main` und in den Branch, bei GitHub nachsehen, Manuel den
  Klickweg und die Screenshots zeigen.

## P-2026-09-26-86 laenge-ab-spindelnase

### EINGELESEN
- Manuel (2026-09-26), Frage 3 zu Stufe 4: „Eigenes Feld, vorbelegt“ – je
  Werkzeug die Länge ab Spindelnase, mit Halter, wie am Voreinstellgerät;
  leer gilt die Gesamtlänge.
- Spezifikation Stufe 4a, Schritt 3. Die Werkzeugverwaltung ordnet die Maße
  je Art an (`_felder_anordnen`); Felder für alle Arten (Bezeichnung) stehen
  darunter.

### DATEIEN
- `camaddon/werkzeuge.py` (Feld `laenge_spindelnase`, speichern und laden)
- `camaddon/gui_werkzeuge.py` (Feld unter den Maßen, grau die Gesamtlänge)
- `camaddon/reichweite.py` (nimmt die Länge ab Spindelnase)
- `translations/de.json`, `translations/en.json` (3 neue Texte, 3 Hinweise
  ergänzt)
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `tests/test_werkzeuge.py`, `tests/test_reichweite.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/spezifikation_simulation.md`, `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In der Werkzeugverwaltung hat jedes Werkzeug das Feld „Länge ab
Spindelnase“; leer steht grau „leer: Gesamtlänge 50“. Eingetragen, rechnet
„Auf der Maschine prüfen“ damit – ohne Hinweis zur Länge.

### DONE
- Werkzeug: `laenge_spindelnase` (mm, 0 = nicht gemessen), gespeichert;
  ältere Dateien ohne das Feld laden mit 0, negative Werte werden 0.
- Werkzeugverwaltung: das Feld bei allen Arten unter den Maßen, über
  „Bezeichnung“, mit Längeneinheit (mm/inch wie die anderen Längen); leer
  grau „leer: Gesamtlänge …“ – eingetragen oder geschätzt; Tooltip: von der
  Spindelnase (im Revolver von der Werkzeugaufnahme) bis zur Spitze, mit
  Halter, wofür es gebraucht wird.
- Prüfung: Ist die Länge ab Spindelnase eingetragen, gilt sie (Quelle
  `LAENGE_SPINDELNASE`, kein Hinweis). Sonst sagen die Hinweise zur
  Gesamtlänge bzw. geschätzten Länge „Genauer mit der „Länge ab
  Spindelnase“ in der Werkzeugverwaltung.“, der zum CAM-Werkzeug, dass es
  nicht in der Werkzeugverwaltung steht.
- Hilfe „Werkzeugverwaltung“: eigener Punkt „Länge ab Spindelnase“.

### TEST
- `test_werkzeuge`: speichern/laden, alte Datei ohne Feld, negativer Wert.
  `test_reichweite`: mit 110 mm Länge ab Spindelnase steht Z1 60 mm höher
  als mit den 50 mm des CAM-Werkzeugs, kein Hinweis zur Länge; die Hinweise
  mit ihrem zweiten Satz. Beide Versionen grün, dazu `test_sprache`,
  `test_hilfe`.
- `szenario_werkzeugverwaltung` (Feld sichtbar, grau „leer: Gesamtlänge
  50“, 115 eintragen und leeren), `szenario_reichweite`, `szenario_hilfe` –
  beide Versionen grün. Screenshot angesehen: das Feld unter den Maßen, über
  „Bezeichnung“.

### NEXT
- Schritt 4: Version 0.22.0, README, voller Lauf, Push.

## P-2026-09-26-85 reichweite-fenster

### EINGELESEN
- Spezifikation Stufe 4a, Schritt 2 und Abschnitt 6: Befehl und
  Aufgabenfenster „Auf der Maschine prüfen“.
- Ausprobiert (Szenario-Proben in beiden Versionen): Die 3D-Ansicht eines
  anderen Dokuments holt `Gui.getMainWindow().setActiveWindow(ansicht)` nach
  vorn. **Im Wochen-Build verschwindet dabei ein offenes Aufgabenfenster** –
  es gehört zu dem Dokument, in dem es aufging; in 1.1.3 bleibt es. Öffnet
  man es erst nach dem Wechsel, bleibt es in beiden. Gleich nach dem Anlegen
  eines Jobs holt 1.1.3 das Dokument des im Baum gewählten Jobs etwa 100 ms
  später zurück nach vorn – bei echter Bedienung (erst wählen, dann klicken)
  nicht, in den Proben auch nicht mit 400 ms Pause oder beim zweiten Mal.

### DATEIEN
- `camaddon/gui_reichweite.py` (neu)
- `camaddon/reichweite.py` (LCS der Aufnahmen beim Anlegen gemerkt)
- `camaddon/gui_start.py` (Befehl, Werkzeugleiste), `camaddon/hilfe.py`
- `resources/icons/reichweite.svg` (neu)
- `help/de/reichweite.html`, `help/en/reichweite.html` (neu)
- `translations/de.json`, `translations/en.json` (20 Texte)
- `tests/gui/szenario_reichweite.py` (neu)
- `docs/spezifikation_simulation.md` (Abschnitte 5 und 6),
  `docs/STATUS_SNAPSHOT.md` (Punkt 13, „Manuel probiert aus“ 7),
  `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job wählen → „Auf der Maschine prüfen“ → das Fenster öffnet sich bei der
Maschine: „Alle Achsen bleiben in ihren Grenzen.“ oder die Überschreitungen
als Sätze; ein Klick fährt die Maschine dorthin, die Achse am Anschlag;
Schließen fährt zurück und merkt sich den Nullpunkt am Job.

### DONE
- Befehl „Auf der Maschine prüfen“ in der Werkzeugleiste (nach „Schnittwerte
  in den Job“), Symbol: eine Bahn zwischen zwei Grenzen, ein Haken. Ohne Job
  im aktiven Dokument oder ohne offene Maschine sagt ein Satz, was fehlt. Der
  gewählte Job gilt (auch über eine Operation). Sind mehrere Maschinen offen,
  fragt der Befehl, welche – die im Dokument des Jobs zuerst. Dann holt er
  das Dokument der Maschine nach vorn und öffnet dort das Fenster; im
  Fenster gibt es deshalb keine Auswahl der Maschine (Spezifikation
  angepasst).
- Das Fenster: Job (Auswahl), Maschine, Werkstückaufnahme (nur bei
  mehreren); Nullpunkt X/Y/Z – leer mit dem Vorschlag grau im Feld,
  eingetragen am Job gemerkt (beim Schließen und beim Wechsel des Jobs, ein
  Schritt Rückgängig im Dokument des Jobs). Ergebnis: grün „Alle Achsen
  bleiben in ihren Grenzen.“, rot „Nicht alle Achsen bleiben in ihren
  Grenzen:“ mit der Liste der Sätze, oder grau „Keine Bahn zum Prüfen …“;
  darunter grau je Achse der gebrauchte Bereich und die Hinweise. Gerechnet
  wird beim Öffnen und 300 ms nach jeder Eingabe.
- Klick auf einen Satz: Die Maschine fährt auf die Stellungen dort (über
  die Grenzen nicht hinaus – die Achse steht am Anschlag), alles in einem
  Schritt, den Schließen verwirft. Schließen fährt zurück und kehrt zum
  Dokument des Jobs zurück.
- Die Liste ist nur so hoch wie ihre Sätze (sonst schob sie Bereiche und
  Hinweise aus dem Aufgabenbereich – im ersten Screenshot gesehen).
- `reichweite.Pruefung` merkt sich die LCS der Aufnahmen beim Anlegen: So
  rechnet es richtig weiter, auch wenn das Fenster die Maschine bewegt hat.
- Hilfeseite „Auf der Maschine prüfen“ (de/en): So geht es, was oben steht,
  das Ergebnis, wie gerechnet wird.

### TEST
- `szenario_reichweite` in 1.1.3 und im Wochen-Build grün: Fenster im
  Dokument der Maschine, grünes Urteil, Vorschlag −50/−30/1 grau in den
  Feldern, Bereiche (7 Punkte), Hinweis zur Länge; X 300 → der Satz „X1
  fährt in „Eigene“ bis −470,00 mm, die Grenze ist −250,00 mm (bei X 170,
  Y 40, Z −5).“; Klick → X1 auf −250, der Tisch bewegt; Schließen → nichts
  bewegt, das Teil vorn, am Job {"X": 300}; wieder öffnen → 300 im Feld,
  leeren → grün, Schließen → Eintrag weg.
- Screenshots angesehen (beide Versionen): Maschine vorn, Fenster rechts,
  Tisch am Anschlag nach dem Klick; die Liste nach der Korrektur kompakt.
- `test_reichweite`, `test_sprache`, `test_hilfe` in beiden Versionen grün.
- Ob das Fenster ohne Erklärung verständlich ist, prüft Manuel.

### NEXT
- Schritt 3: „Länge ab Spindelnase“ in der Werkzeugverwaltung.

## P-2026-09-26-84 reichweite-rechenkern

### EINGELESEN
- Spezifikation Stufe 4a (P-2026-09-26-83), Schritt 1: Rechenkern ohne
  Oberfläche, dazu Beispiel-Drehmaschine und Hilfe „Aufnahmen“.
- `verfahren.py`: Die Lage eines Bauteils ist das Produkt der
  Achsbewegungen vom Bett nach außen – dieselbe Rechnung trägt die Prüfung,
  nur ohne Bauteile zu bewegen. `platzstellungen()` bringt einen
  Revolverplatz in Arbeitsstellung. `job_schnittwerte.werkzeug_von()` findet
  zum Werkzeug-Controller das Werkzeug der Werkzeugverwaltung.

### DATEIEN
- `camaddon/reichweite.py` (neu)
- `camaddon/verfahren.py` (öffentlich: `bewegung`, `pfad`, `weg_bei`,
  `stellung_bei`)
- `camaddon/beispielmaschine.py` (LCS mit X-Richtung; Futter der
  Drehmaschine)
- `translations/de.json`, `translations/en.json` (16 Texte `rw.*`)
- `help/de/aufnahmen.html`, `help/en/aufnahmen.html`
- `tests/test_reichweite.py` (neu)
- `docs/aufbau.md`, `docs/spezifikation_simulation.md`,
  `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Für jeden Punkt einer Bahn liefert die Prüfung die Stellungen aller Achsen;
fährt die Maschine dorthin, steht die Werkzeugspitze genau auf dem Punkt –
an allen Beispielmaschinen. Eine Achse über ihrer Grenze kommt als Satz mit
Operation, Stellung, Grenze und Punkt im Programm.

### DONE
- `Pruefung(assembly, maschine, werkstueckaufnahme)`:
  - Drehachsen zuerst: Rundachsen mit Betriebsart „Positionieren“ über ihren
    Namen im Programm (C1 → C), ohne Angabe 0; der Revolver mit dem Platz
    der Werkzeugnummer in Arbeitsstellung; Spindeln bleiben.
  - Dann die Linearachsen zwischen Werkzeug- und Werkstückaufnahme als
    lineares Gleichungssystem (numpy): einmal je Stellung der Drehachsen
    gelöst, gilt Stellungen = s0 + S · Punkt. Die schräge Achse braucht
    nichts Eigenes – die Lösung rechnet mit den echten Richtungen der
    Schlitten. Weniger als drei Achsen: Was übrig bleibt, heißt „nicht
    erreichbar“; mehr als drei oder abhängige: „noch nicht prüfbar“.
  - `stellungen(punkt, …)` für einen Punkt (auch fürs spätere „dorthin
    fahren“); `pruefe_job(job, nullpunkt, bibliothek)` für alle aktiven
    Operationen aus `job.Operations` (wie der Postprozessor, ohne die Lage
    der Operation).
- Die Bahn: G0/G1-Enden; Kreise G2/G3 in G17/G18/G19 mit I/J/K oder R, auch
  Vollkreis und Schraube – dazu genau die Stellen, an denen eine Achse
  umkehrt (aus S, nicht in Schritten); Bohrzyklen über dem Loch, auf R und
  auf dem Grund, G98/G99; G90/G91; eine Rundachse im Satz in 1°-Schritten.
  Befehle ohne Bewegung werden still übergangen, unbekannte mit Bewegung
  gemeldet.
- Ergebnis: je Operation und Achse die weiteste Überschreitung („X1 fährt in
  „Eigene“ bis −400.00 mm, die Grenze ist −250.00 mm (bei X 400, Y 0,
  Z 10).“) mit allen Stellungen dort; je Achse der gebrauchte Bereich;
  Hinweise: Länge (Gesamtlänge, geschätzt oder die des CAM-Werkzeugs, je
  „ohne Halter“), Platz fehlt, nicht erreichbar, Z der Werkzeugaufnahme zum
  Werkstück, unbekannter Befehl. Rundachsen zählen, wenn sie
  positionieren und nicht endlos sind.
- Nullpunkt des Jobs: Vorschlag (Rohteil mittig, Unterseite auf der
  Spannfläche), eingetragen als Eigenschaft `CamAddonNullpunkt` am Job
  (JSON, einzelne Werte, ausgeblendet), `nullpunkt(job)` nimmt beides.
- `verfahren.py`: Bewegung einer Achse um einen Weg, Pfad zu einem Glied,
  Weg ↔ Stellung als öffentliche Methoden; `_bewege` nutzt sie.
- Beispiel-Drehmaschine: Das LCS am Futter hat jetzt X von der Spindelachse
  zum Werkzeug (vorher zeigte X nach unten, ein X im Programm wäre über Y1
  gefahren). `Baukasten.lcs(…, x_richtung=…)`.
- Hilfe „Aufnahmen“: Z der Werkzeugaufnahme von der Spitze zur Aufnahme; das
  LCS der Werkstückaufnahme ist das Koordinatensystem des Jobs, X wie X im
  Job (Drehmaschine: zum Werkzeug hin).

### TEST
- `tests/test_reichweite.py`, 1.1.3 und Wochen-Build grün:
  - Nachgemessen: Maschine auf die gerechneten Stellungen gefahren, Abstand
    Spitze – Punkt < 1e-6 mm an der 3-Achs-Fräse (mit und ohne Nullpunkt),
    der Drehmaschine (P1 radial, P2 axial), der Drehmaschine mit Y schräg um
    30°, den drei 5-Achs-Fräsen ohne und mit Rundachsen aus der Bahn.
  - Drehmaschine: X im Job fährt nur X1; Revolver auf P2; C ohne Angabe
    auf 0. Schräge Y-Achse: Y 0 → 10 fährt Y1 um 11,547 und X1 um 5,774 –
    wie `schraege_achse.schlitten_aus_programm`.
  - Job mit eigener Bahn: Überschreitung von X1 als Satz, Bereiche (Y bis
    zum Scheitel des Kreises, Z bis zum Grund der Bohrung), 11 Punkte,
    Hinweise; Vollkreis und G18-Halbkreis; Länge aus der Werkzeugverwaltung
    (Z1 10 mm höher) und geschätzt; Z der Spindelnase umgedreht → Hinweis;
    Platz P20 fehlt → Hinweis, keine Punkte; A 130 über 120 in 1°-Schritten
    (261 Punkte); Drehmaschine ohne Y: erreichbarer Punkt mit den
    erwarteten Stellungen, 5 mm quer daneben nicht erreichbar, Hinweis
    „1 von 2 Punkten“; Nullpunkt: Vorschlag, eintragen, Speichern und
    Laden, löschen.
- Alle Prüfungen ohne Oberfläche in beiden Versionen grün (`test_export`
  in 1.1.3 übersprungen wie immer); `test_hilfe` nach der Hilfeänderung.

### NEXT
- Schritt 2: Fenster „Auf der Maschine prüfen“ mit Befehl, Hilfe und
  Szenario.

## P-2026-09-26-83 spezifikation-reichweite

### EINGELESEN
- Manuel (2026-09-26) auf die vier Fragen zu Stufe 4a, jeweils die
  empfohlene Antwort: **Bahn im Job** (nicht das NC-Programm);
  **Nullpunkt = Werkstückaufnahme + Verschiebung** je Job im Fenster;
  **eigenes Feld „Länge ab Spindelnase“**, vorbelegt (leer gilt die
  Gesamtlänge); **4a Reichweite zuerst**. Halter und Mindestabstand (Fragen
  4 und 5) betreffen erst die Kollision und kommen vor 4c.
- Ausprobiert, in 1.1.3 und im Wochen-Build: Job ohne Oberfläche anlegen,
  Operation „Eigene“ (Custom) mit G-Code als Text, `op.Path.Commands`
  lesen (G0/G1/G2 mit X/Y/Z/I/J); der Werkzeug-Controller hat Nummer und
  Länge. Die Postprozessoren lesen `op.Path` ohne die Lage der Operation
  (`Path/Post/UtilsParse.py`). numpy gibt es in beiden Umgebungen.
- Beispielmaschinen: Die Z-Achse der Werkzeugaufnahmen zeigt von der Spitze
  zur Aufnahme (Fräse: Spindelnase, Z nach oben; Drehmaschine: Platz, Z vom
  Werkzeug weg). Die Hilfe sagt nur „in Richtung des Werkzeugs“. Die X-Achse
  des LCS am Futter der Beispiel-Drehmaschine zeigt nach unten, der
  X-Schlitten fährt quer dazu – ein X im Programm käme über Y1 heraus.

### DATEIEN
- `docs/spezifikation_simulation.md`
- `docs/STATUS_SNAPSHOT.md` (Projektstatus, neuer Punkt 13, Besprechen)
- `docs/spezifikation_maschine_aus_baugruppe.md` (Verweis auf Stufe 4)
- `CHATSTART.md` (Lesekarte)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation sagt so genau, was 4a rechnet und zeigt, dass danach
gebaut werden kann: Begriffe mit den Richtungen der LCS, der Rechenweg
(Drehachsen zuerst, dann die Linearachsen als Gleichungssystem), welche
Punkte geprüft werden, das Fenster, vier Schritte, Akzeptanzkriterien.

### DONE
- Kopf: Manuels Entscheidungen vom 2026-09-26; Abschnitt 9 heißt
  „Entscheidungen“ (1, 2, 3, 6 entschieden; 4, 5 offen vor 4c).
- Begriffe: Das LCS der Werkstückaufnahme ist das Koordinatensystem des
  Jobs (Z aus der Spannfläche, X wie X im Job, auf der Drehmaschine zum
  Werkzeug hin); Werkzeugspitze = Ursprung der Werkzeugaufnahme minus Länge
  ab Spindelnase entlang Z; Z der Werkzeugaufnahme zeigt von der Spitze zur
  Aufnahme; „Länge ab Spindelnase“ mit Halter.
- Abschnitt 4 neu: Drehachsen zuerst (A/B/C über den Namen im Programm,
  ohne Angabe 0; Revolver mit dem Platz des Werkzeugs in Arbeitsstellung;
  Spindeln bleiben), dann die Linearachsen als lineares Gleichungssystem –
  das deckt Tisch/Kopf, schiefe Achsen und die schräge Achse ab; weniger
  als drei Linearachsen → „nicht erreichbar“, mehr als drei → „noch nicht
  prüfbar“; geprüfte Punkte: G0/G1-Enden, Umkehrpunkte auf Kreisen,
  Bohrzyklen, 1°-Schritte bei Rundachsen im Satz. Die Frage nach dem
  Buchstaben im Fenster entfällt.
- Abschnitt 5: 4a in vier Schritten – Rechenkern (`reichweite.py`),
  Fenster, Länge ab Spindelnase, Version.
- Abschnitt 6: das Fenster „Auf der Maschine prüfen“ – Job, Maschine aus
  allen offenen Dokumenten, Werkstückaufnahme, Nullpunkt X/Y/Z (leer =
  Vorschlag: Rohteil mittig mit der Unterseite auf der Spannfläche;
  eingetragen = am Job gespeichert), Ergebnis in Sätzen, Klick fährt hin,
  Schließen fährt zurück.
- Abschnitt 10: Akzeptanzkriterien für die Beispielfräse, die
  Drehmaschine mit schräger Y-Achse und ein Werkzeug ohne Länge ab
  Spindelnase. Statt „Zeile 1234“ nennt die Meldung den Punkt im Programm
  – ein NC-Programm gibt es bei der Bahn im Job nicht.

### TEST
- Reine Doku.

### NEXT
- Schritt 1: Rechenkern `reichweite.py` mit Prüfungen; Beispiel-Drehmaschine
  (X des LCS am Futter) und Hilfe „Aufnahmen“.

## P-2026-09-26-82 simulation-schraege-achse

### EINGELESEN
- Stand: „Danach: W-001 Stufe 4a (Reichweite prüfen), sobald die schräge
  Achse (Punkt 11) steht und die Fragen zu Stufe 4 beantwortet sind.“ Die
  schräge Achse steht (Stufe 3b komplett); der Entwurf
  `spezifikation_simulation.md` kannte sie noch nicht.

### DATEIEN
- `docs/spezifikation_simulation.md` (Abschnitt 4)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer den Entwurf zu Stufe 4 liest, sieht, wie eine schräge Achse in die
Reichweitenprüfung eingeht: rechtwinklige Bahn, Grenzen der Schlitten,
Meldung mit Programmpunkt und Schlitten.

### DONE
- Abschnitt 4 um „Schräge Achse“ ergänzt: dieselbe Umrechnung wie „wie im
  Programm“ (`schraege_achse.Programm`), geprüft werden die Grenzen der
  Schlitten; Beispielmeldung „X 140, Y −40 in *Kontur* braucht X1 = 163 mm,
  die Grenze ist 150 mm“ (bei 30°, dieselben Zahlen wie im Szenario
  `szenario_verfahren_schraeg`); für 4d der Höchstvorschub
  (`schraege_achse.hoechstwert`).

### TEST
- Reine Doku.

### NEXT
- Manuel die Fragen zu Stufe 4 stellen, die 4a betreffen (Abschnitt 9,
  Nr. 1, 2, 3, 6); Halter und Mindestabstand erst vor 4c.

## P-2026-09-26-81 readme-maschine

### EINGELESEN
- Manuel: „Da ist ein PR, den man nicht pushen kann – schau es dir an, löse
  die Probleme und integriere das.“ PR #1 (W-003, 4-Achs) war nicht mergebar:
  Beide Sitzungen hatten gleichzeitig an Stand, Verlauf und Sprachdateien
  gearbeitet und dieselben Nummern P-2026-09-26-75/-76 vergeben.
- Beim Nachsehen vor dem Push: Die andere Sitzung hatte den PR auf Manuels
  „pusch das mal alles komplett“ schon selbst auf `main` neu aufgesetzt
  (P-2026-09-26-78 bis -80, 0.21.0, voller Lauf grün) und gepusht; der PR ist
  geschlossen, sein Kopf ist `main`. Mein lokaler Merge kam zu denselben
  Konfliktlösungen – Code, Sprachdateien, Hilfe und Prüfungen gleich – und
  wurde deshalb verworfen, nicht gepusht.
- Übrig blieb: Die Zeile zu W-001 im Projektstatus stand noch auf „Jetzt
  Stufe 3b“; die README kannte „Neue Maschine …“, die schräge Achse und das
  Verfahren „wie im Programm“ nicht; die Beschreibung für den Addon-Manager
  (`package.xml`) nannte keine der neuen Funktionen.

### DATEIEN
- `README.md`
- `docs/STATUS_SNAPSHOT.md` (Projektstatus W-001)
- `package.xml` (Beschreibung)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die README auf GitHub liest, findet „Neue Maschine …“, die schräge
Achse und das Verfahren „wie im Programm“ unter „Was es kann“; der
Projektstatus sagt, dass Stufe 3b fertig ist.

### DONE
- README: neuer Punkt „Neue Maschine …“ (Bauarten, Maße der Drehmaschine);
  bei „Maschine bearbeiten“ die schräge Achse in zwei Sätzen; bei „Maschine
  verfahren“ „wie im Programm“ mit Reglern X und Y.
- Projektstatus W-001: Stufen 1 bis 3 und 3b fertig, danach Stufe 4.
- `package.xml`: „inclined axes“, fertige Maschinen („a lathe with your own
  dimensions, mills“) und „4-axis machining: places a part in round bar
  stock as a CAM job“. Die Version bleibt 0.21.0.

### TEST
- `scripts/alle_tests.sh` in beiden Versionen vor dem Push (wegen
  `package.xml`).

### NEXT
- Push nach `main` und in den Branch, bei GitHub nachsehen.

## P-2026-09-26-80 version-0-21-0

### EINGELESEN
- Manuel (2026-09-26) auf die Frage, ob die 4-Achs-Bearbeitung nach `main`
  soll: „Ja, pusch das mal alles komplett“ – „und dann Stop“.
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit 0.20.0:
  „4-Achs-Bearbeitung“, Teil in die Stange (P-2026-09-26-79), und ihre
  Spezifikation (-78).
- Die beiden hießen auf dem Arbeitszweig `claude/4-achsen-rohrteil-plan-bqz52m`
  zuerst -75 und -76. Diese Nummern hatte inzwischen die andere Sitzung auf
  `main` vergeben (neue-maschine, schraege-achse-lesbarer), dazu 0.20.0 (-77).
  Deshalb auf `main` neu aufgesetzt und umnummeriert.

### DATEIEN
- `package.xml` (0.21.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.21.0.

### DONE
- Version 0.20.0 → 0.21.0.

### TEST
- `scripts/alle_tests.sh` auf dem Stand dieses Commits („Neue Maschine …“
  und 4-Achs-Bearbeitung zusammen): black und ruff sauber; FreeCAD 1.1.3
  grün (48 ok, `test_export.py` übersprungen wie immer); Wochen-Build
  26.3.0 dev (2026-09-16) grün (49 ok).

### NEXT
- Push nach `main`. Danach Schluss, auf Manuels Wort („und dann Stop“);
  W-003 V2 erst auf seine Ansage.

## P-2026-09-26-79 vierachs-teil-in-die-stange

### EINGELESEN
- Manuel (2026-09-26), nach dem Plan: „Gleich V1 bauen“; dazu „so dass
  alles einstellbar ist, aber mit Vorschlägen als Standard“.
- `docs/spezifikation_vierachs.md` (Abschnitte 4, 5, 11, 13),
  `gui_verfahren.py` und `gui_maschine.py` (Aufgabenfenster, Transaktion,
  `_EnterBleibtImDialog`), `gui_start.py`, `gui_zeigen.py` (Wackeln),
  `gui_zahlen.py`, `einheiten.py`, `gui_werkzeuge.py` (graue Vorschläge),
  `tests/gui/_lauf/szenario_lauf.py`.
- FreeCAD 1.1.3 und `main`: `Path/Main/Gui/Job.py` (`Create` hängt die
  Anzeige an und öffnet eine eigene Transaktion; `ViewProvider.attach`
  zeichnet nur das Achsenkreuz), `Path/Main/Job.py` (`createResourceClone`:
  Draft-Klon, unsichtbar, Durchsicht 80), `Path/Main/Stock.py`
  (`SetupStockObject`: Drahtgitter, Durchsicht 90), `Gui/TaskView/TaskView.cpp`
  und `TaskDialogPython.cpp` (`modifyStandardButtons`), `Path/Op/Gui/Base.py`
  (hebt die Knopfleiste auf, nicht den Knopf).

### DATEIEN
- `camaddon/vierachs_rohteil.py` (neu), `camaddon/gui_vierachs.py` (neu),
  `camaddon/gui_start.py`, `camaddon/hilfe.py`
- `resources/icons/vierachs.svg` (neu), `help/de/vierachs.html` und
  `help/en/vierachs.html` (neu)
- `translations/de.json`, `translations/en.json` (42 neue Texte, „Über“)
- `tests/test_vierachs_rohteil.py` (neu),
  `tests/gui/szenario_vierachs_rohteil.py` (neu)
- `docs/spezifikation_vierachs.md` (V1 gebaut), `docs/aufbau.md` (zwei
  Module, sechs Stolpersteine), `README.md`, `CHATSTART.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit außermittigem Zapfen öffnen, ihre Stirnfläche anklicken →
Werkzeugleiste „CAM-Addon“ → „4-Achs-Bearbeitung“ → Stange Ø 80, Rundachse C
→ das Teil liegt mittig in einer durchsichtigen Stange Ø 80 längs Z, die
Fläche 1 mm hinter der Stangenstirn, das Fenster sagt „Passt – rundum
mindestens 4,0 mm Aufmaß“; Abbrechen hinterlässt nichts, „Anlegen“ nimmt ein
Strg+Z zurück – und Manuel versteht das Fenster ohne Erklärung.

### DONE
- Befehl „4-Achs-Bearbeitung“ in der Werkzeugleiste „CAM-Addon“; Symbol:
  Stange mit Teil, Drehpfeil um die Stangenachse, Fräser von oben.
- Rechnung ohne Oberfläche (`vierachs_rohteil.py`):
  - Einmal je Fläche wird vermessen: eben oder nicht, Außennormale, runde
    Außenkante (auch aus Bögen), Punkte aus der Tessellierung, konvexe Hülle
    und kleinster Kreis (Welzl als Schleife).
  - Daraus kommt sofort die Lage für A, B oder C – mit der Mitte „runde
    Fläche“, „ganzes Teil“ oder „auto“ und mit der Drehlage.
  - Vorschlag für den Stangen-Ø: 5-mm- bzw. 1/8"-Schritte, mindestens 1 mm
    am Radius. Dazu Länge und Lage der Stange.
  - `richte_ein` legt Job, Lage des Klons und Zylinder-Rohteil an, ohne
    eigene Transaktion.
- Assistent (`gui_vierachs.py`):
  - Die Fläche wählt man vor dem Befehl oder im offenen Fenster. Beobachter
    und Filter der Auswahl lassen nur Flächen zu, nicht die Stange.
  - Felder mit grauen, gültigen Vorschlägen. Was man einträgt, wird nach
    „Anlegen“ gemerkt – außer dem Stangen-Ø.
  - Mitte mit dem nötigen Ø daneben, Drehlage mit „+90°“, Rundachse A/B/C
    mit einem Satz je Eintrag, eine grüne oder rote Zeile.
  - OK heißt „Anlegen“ und geht erst, wenn eine Fläche gewählt ist.
  - Animation: Das Teil fährt in die Stange und dreht sich einmal – auch
    beim Wechsel der Rundachse.
  - Solange das Fenster offen ist, ist die Stange durchscheinend und nicht
    anklickbar, danach sieht sie aus wie in CAM. Das Original ist
    ausgeblendet.
  - Klickt man ein anderes Teil an, wird der bisherige Job verworfen.
- Gefunden:
  - Die Python-Hülle des OK-Knopfs aus `modifyStandardButtons` verfällt
    mit der Hülle der Knopfleiste. Im Versuchs-Szenario war sie gleich nach
    dem Öffnen „weg“, ohne dass Qt etwas löschte. Jetzt wird die Leiste
    aufgehoben, wie in CAM.
  - 1.1.3 gibt die Beschriftung eines abgebrochenen Jobs nicht wieder frei:
    Der nächste heißt „… 4 Achsen001“.
  - Die Hüllbox gekrümmter Flächen ist nur auf etwa 0,003 mm genau.
- Bewusst offen:
  - Achse von der Maschine (V2).
  - Flächen, Werkzeuge und Bahnen (V3 ff.).
  - „Vorschläge zurücksetzen“ in den Einstellungen – mit V9.
  - Ein Beispielteil zum Ausprobieren – bei Bedarf eigener Patch.

### TEST
- `tests/test_vierachs_rohteil.py` (Claude, ohne Oberfläche, 1.1.3 und
  Wochen-Build):
  - kleinster Kreis: Quadrat, 2000 Zufallspunkte, Punkte auf einer Geraden;
    dazu Sechskant und Quader;
  - Welle mit Nocken: Ø 72 mittig auf der Welle, Ø 66 für das ganze Teil,
    „auto“ bei Ø 80, Ø 70 und ohne Ø;
  - Lage für A, B und C mit beiden Mitten: Normale nach vorne, Stirnfläche
    bei a = 0, Teil bis −100, kein Punkt außerhalb des nötigen Ø;
  - Drehlage, Vorschläge, Länge und Lage der Stange;
  - Job: Zylinder Ø 80 × 134 von −133 bis 1, Klon an seiner Stelle,
    Original unverändert; ein zweiter Aufruf passt das Rohteil an, zwei
    Rückgängig entfernen alles.
- `tests/gui/szenario_vierachs_rohteil.py` (Claude, unsichtbare Oberfläche,
  beide Versionen):
  - Vorschlag Ø 75; Ø 80 → 4,0 mm; ganzes Teil → 7,0 mm; A → Stange in X,
    C → in Z; +90°;
  - eine gewölbte Fläche wird mit einem Satz abgelehnt;
  - Abbrechen hinterlässt nichts, und der zweite Durchlauf hat die
    Rundachse nicht gemerkt;
  - „Anlegen“ ist ein Schritt Rückgängig, Strg+Z räumt alles weg.
  - Screenshots angesehen: Fenster, Stange längs Z und längs X, nach
    „Anlegen“.
- `scripts/alle_tests.sh` auf dem Arbeitszweig, vor dem Zusammenführen mit
  -75 bis -77: black und ruff sauber; FreeCAD 1.1.3 grün (47 ok,
  `test_export.py` übersprungen wie immer); Wochen-Build 26.3.0 dev
  (2026-09-16) grün (48 ok). Der Lauf auf `main` steht in P-2026-09-26-80.
- Das Fenster hat nur Claude als Screenshot gesehen. Ob es sich ohne
  Erklärung versteht, prüft Manuel.

### NEXT
- W-003 V2: Achse von der Maschine (W-001).

## P-2026-09-26-78 spezifikation-vierachs

### EINGELESEN
- Manuel (2026-09-26): „Ich hätte gerne einen Plan gemacht für eine
  4-Achs-Bearbeitung … egal ob es eine C- oder B-Achse ist … auch auf einer
  CLX 550 mit Y-Achse funktionieren. Ich habe ein Bauteil, das ich an ein
  rundes Rohteil im CAM befestigen kann … Stange rund Durchmesser 80 … wähle
  eine Fläche, diese Fläche soll vorne an das Rohteil … zentrisch, dass
  versucht wird, das komplette Bauteil in das Rohteil zu bekommen. Dann
  klickt man die Flächen an, alle Mantelflächen oder einen Zylinder, der
  nicht mittig ist, und dann wird aus Kombination Fräser und Rohteil eine
  Schrupp- und danach eine Schlicht-Strategie erstellt. Maximal
  bedienerfreundlich.“
- Seine Wahl aus vier Fragen mit Optionen: eigener Rechenkern (statt FreeCADs
  „Rotary Surface“ oder beides); zuerst rundum simultan (statt indexiert);
  Achse „am besten von Maschine, ansonsten dreht sich das Rohteil … und dem
  muss man eine Achse zuweisen“; Assistent in vier Schritten. Zum Plan: „Ist
  das egal welche Maschine … Es gibt Achsen, und die Punkte müssen halt via
  Koordinate im G-Code 0,001 mm nach und nach angefahren werden … oder halt
  mit einem Glättungsfilter“ und „Abstechbreite kann man ja einstellen … so
  dass alles einstellbar ist, aber mit Vorschlägen als Standard“. Dann:
  „Gleich V1 bauen“.
- Addon: `job_schnittwerte.py`, `uebergabe_werkzeuge.py`, `werkzeuge.py`,
  `schnittdaten.py`, `schruppwerte.py`, `maschine.py` (`rollen`,
  `programmname`), `kette.py`, `verfahren.py` (`plusrichtung`),
  `schraege_achse.py`, `beispielmaschine.py`, `export.py`, `gui_maschine.py`,
  `gui_verfahren.py`, `gui_zeigen.py`, `gui_start.py`, die drei
  Spezifikationen, `aufbau.md`.
- FreeCAD-Quelltext 1.1.3 und `main` (raw.githubusercontent.com):
  `Path/Op/Surface.py` (Rotational: OCL, nur A/B, Schalter „advanced OCL“),
  `Path/Dressup/Gui/AxisMap.py`, `Path/Op/RotarySurface.py` und
  `Path/Base/Generator/rotary_*.py` (nur `main`, experimentell, OCL, nur
  Achse X/Y), `Path/Main/Workplane.py` (nur `main`), `Path/Op/Base.py`
  (`DoNotSetDefaultValues`, `setDefaultValues` fragt nach Job und
  Controller), `Path/Main/Job.py` (`Create`, `setCenterOfRotation`),
  `Path/Main/Gui/Job.py` (`Create` mit eigener Transaktion),
  `Path/Main/Stock.py` (`CreateCylinder`), `App/PathSegmentWalker.cpp`
  (Anzeige von A/B/C), `Constants.py` (G93 im generischen Postprozessor),
  conda-forge-Rezept von FreeCAD (numpy ja, OpenCamLib nein).
- Gegenprüfung des Entwurfs durch einen Planungs-Agenten.

### DATEIEN
- `docs/spezifikation_vierachs.md` (neu)
- `docs/STATUS_SNAPSHOT.md` (Projektstatus, Punkt 12, W-003)
- `CHATSTART.md` (Lesekarte)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel findet in `docs/spezifikation_vierachs.md` seine Entscheidungen, den
Klickweg durch die vier Schritte mit Skizzen und die Stufen mit je einem
Klickweg wieder.

### DONE
- Spezifikation W-003: Zielbild mit Klickweg, was FreeCAD und das Addon
  schon haben, Begriffe mit Skizze der Rundachs-Koordinaten, Achsen von der
  Maschine oder zugewiesen (Tabelle A/B/C), die vier Schritte mit
  ASCII-Skizzen, Rechenkern (Torus-Modell für alle drei Fräser, exaktes
  Aufmaß, Hüllfläche mit numpy, Lagen, Spirale, Rückzug, Ausgabe als reine
  Achskoordinaten mit Glättung, Vorschub G93), die CAM-Operation mit ihren
  Stolpersteinen, Bedienung, Grenzen, neun Stufen V1–V9, Prüfbarkeit,
  Claudes Vorschläge, Manuels Entscheidungen.
- Gefunden beim Lesen: `Job.setCenterOfRotation` setzt den Mittelpunkt an
  einer Kopie – die Rundachse liegt deshalb durch den Nullpunkt des Jobs.
  Eine Operation, die ohne `DoNotSetDefaultValues` angelegt wird, fragt bei
  mehreren Jobs oder Controllern nach (in FreeCADCmd ein Fehler).
- Versuch (Claude, ohne Oberfläche, 1.1.3 und Wochen-Build): Job anlegen,
  Lage des Modell-Klons setzen, Rohteil durch `CreateCylinder` ersetzen – der
  Klon liegt wie das Original und folgt `T · P0` genau, die Flächennummern
  bleiben, ein Rückgängig entfernt alles. numpy da, OpenCamLib in keiner der
  beiden Testumgebungen.
- Bewusst offen: indexiert 3+1, axiales Werkzeug, Drehen – spätere Stufen
  oder eigene Wünsche; Claudes Vorschläge (Abschnitt 15) zur Besprechung.

### TEST
Reine Doku, kein Testlauf.

### NEXT
- W-003 V1: „Teil in die Stange“ (Befehl, Schritt 1, Prüfung, Szenario).

## P-2026-09-26-77 version-0-20-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit 0.19.0:
  „Neue Maschine …“ mit Maßen der Drehmaschine (P-2026-09-26-75), dazu
  -76 (lesbarer, nichts Sichtbares).

### DATEIEN
- `package.xml` (0.20.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.20.0.

### DONE
- Version 0.19.0 → 0.20.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-26-76 schraege-achse-lesbarer

### EINGELESEN
- Beim Durchsehen von `schraege_achse.py` (P-2026-09-26-66): In
  `schlitten_aus_programm` und `programm_aus_schlitten` hieß eine lokale
  Variable `winkel` – so heißt auch die Funktion des Moduls, die den Winkel
  misst. Richtig gerechnet, aber verwirrend beim Lesen.

### DATEIEN
- `camaddon/schraege_achse.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nichts Sichtbares: `test_schraege_achse.py` bleibt grün.

### DONE
- Lokale Variable `winkel` → `bogen` (der Winkel im Bogenmaß).

### TEST
- Claude ohne Oberfläche: `test_schraege_achse.py` grün (Wochen-Build).

### NEXT
- Version 0.20.0, voller Testlauf, Push.

## P-2026-09-26-75 neue-maschine

### EINGELESEN
- Manuels Wahl (2026-09-26): eigener Befehl „Neue Maschine …“; Maße zum
  Eintragen erst nur für die Drehmaschine. Spezifikation W-001, Abschnitt 7c
  („Vorlage mit Eingabemaske“) und Stufe 3b, Schritt 7.
- `beispielmaschine.py` (Bauplan der Drehmaschine), `gui_maschine.py`
  (Auswahl der Beispielmaschinen), `gui_start.py`, `tests/test_sprache.py`
  (Schlüssel nur als fester Text in tr/meldung).

### DATEIEN
- `camaddon/gui_neue_maschine.py` (neu), `resources/icons/neue_maschine.svg` (neu)
- `camaddon/beispielmaschine.py` (`DrehmaschinenMasse`, `drehmaschine(masse)`,
  `lade(art, masse)`)
- `camaddon/gui_maschine.py` (Auswahl ausgelagert), `camaddon/gui_verfahren.py`,
  `camaddon/gui_start.py`, `camaddon/hilfe.py`
- `help/de/neue_maschine.html`, `help/en/neue_maschine.html` (neu),
  `help/de/achsen.html`, `help/en/achsen.html`
- `translations/de.json`, `translations/en.json`
- `tests/test_beispielmaschine.py`, `tests/gui/szenario_neue_maschine.py` (neu),
  `tests/gui/szenario_beispielmaschine.py`, `tests/gui/szenario_zoll.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/aufbau.md`, `CHATSTART.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugleiste „CAM-Addon“ → „Neue Maschine …“ → Drehmaschine → Name „Meine
Drehmaschine“, Bettneigung 30°, Y schräg um 30°, 8 Revolverplätze →
„Maschine bauen“ → ein neues Dokument „Meine Drehmaschine“, und „Maschine
bearbeiten“ zeigt „Schräge Achse Y1 – gleicht aus: X1, 30,0°“ und
„Revolver T – 8 Plätze“.

### DONE
- `DrehmaschinenMasse`: Name, Bettneigung (0–60°), Y-Winkel (±60°), Wege
  X/Y/Z (0 liegt dazwischen, höchstens 1000 mm je Richtung), Revolverplätze
  (4–24), Höchstdrehzahl; vorbelegt wie das Beispiel; `fehler()` sagt in
  Sätzen, was nicht passt. `drehmaschine(masse)` baut damit – das Bett im
  Rahmen der Neigung, die Wege als Grenzen der Gelenke, die Plätze
  verteilt, S1 mit der Drehzahl, Name für Maschine und Dokument (ohne „/“
  im Dokumentnamen) – und legt bei Y-Winkel ≠ 0 die schräge Achse an
  (`drehe_fuehrung`, der Revolver bleibt gerade).
- Befehl „Neue Maschine …“ (Werkzeugleiste, vor „Maschine bearbeiten“):
  Dialog mit den Bauarten, der Beschreibung und dem Bereich „Maße“ (?): bei
  der Drehmaschine die Felder (Wege in mm bzw. inch), bei den Fräsen der
  Satz „Diese Bauart hat feste Maße …“. „Maschine bauen“ prüft die Maße;
  passt etwas nicht, sagt eine rote Zeile warum, und der Dialog bleibt offen
  (die Zeile verschwindet beim nächsten Ändern). Danach öffnet sich
  „Maschine bearbeiten“.
- „Beispielmaschine laden …“ in „Maschine bearbeiten“ und „Maschine
  verfahren“ öffnet denselben Dialog (Titel „Beispielmaschine laden“), mit
  Maßen bei der Drehmaschine. Knopf jetzt „Maschine bauen“ statt „Laden“.
- Die Beschreibung der Drehmaschine nennt keine feste Platzzahl mehr.
- Hilfe „Neue Maschine“ und ein Absatz in „Achsen“.
- Bewusst noch nicht: Maße für die Fräsen (Manuel: erst die Drehmaschine);
  die Maße werden nicht gemerkt (jedes Mal die des Beispiels).

### TEST
- Claude ohne Oberfläche, beide Versionen: `test_beispielmaschine.py`
  zusätzlich: eigene Maße → Name der Maschine, Dokument „Meine
  Drehmaschine - 2“ (ohne „/“), Wege als Grenzen, X steigt um 30°, 8 Plätze,
  S1 4000, schräge Achse mit 30°, keine Warnung und kein Hinweis zur
  schrägen Achse; Vorgaben ohne schräge Achse; ungültige Maße – je Feld ein
  Satz. `test_sprache`, `test_hilfe` grün.
- Claude mit Oberfläche (Screenshots angesehen), beide Versionen:
  `szenario_neue_maschine` – Knopf in der Werkzeugleiste, Fräse mit festen
  Maßen, Drehmaschine mit Vorbelegung, Weg Y 0 … 0 abgewiesen (roter Satz,
  Dialog bleibt, Satz verschwindet beim Ändern), eigene Maße gebaut,
  „Maschine bearbeiten“ mit schräger Achse 30,0° und 8 Plätzen.
  `szenario_beispielmaschine`, `szenario_zoll` weiter grün.
- Ob der Dialog verständlich ist, prüft Manuel.

### NEXT
- Version 0.20.0, voller Testlauf, Push.

## P-2026-09-26-74 snapshot-schraege-achse-ausprobieren

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md`, Abschnitt „Manuel probiert aus“.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Unter „Manuel probiert aus“ steht als Punkt 5 der Klickweg für die schräge
Achse (anlegen, Winkel eintragen, Verweilen, Verfahren wie im Programm,
Anschlag, Übergabe).

### DONE
- Klickweg ergänzt; „Besprechen“ ist jetzt Punkt 6.

### TEST
- Reine Doku, kein Testlauf.

### NEXT
- Push mit 0.19.0; Schritt 7 (Vorlage) nach Manuels Entscheidung.

## P-2026-09-26-73 version-0-19-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit 0.18.0:
  die schräge Achse (P-2026-09-26-65 bis -72) – Eintrag, Winkel eintragen,
  Erkennung, Verfahren wie im Programm, Übergabe an CAM, Höchstvorschub –
  und das schmalere Verfahrfenster (-70).

### DATEIEN
- `package.xml` (0.19.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.19.0.

### DONE
- Version 0.18.0 → 0.19.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Schritt 7 (Vorlage) nach Manuels Entscheidung zum Aufbau.

## P-2026-09-26-72 schraege-achse-hoechstvorschub

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („Schruppwerte planen“) und Stufe 3b,
  Schritt 6; `schruppwerte.grenzen_der_maschine`.

### DATEIEN
- `camaddon/schruppwerte.py`
- `help/de/schruppwerte.html`, `help/en/schruppwerte.html`
- `tests/test_schraege_achse.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit schräger Achse (30°) offen → Werkzeugverwaltung →
„Schruppwerte planen…“ → „Von der Maschine“ → Vorschub 4330 mm/min statt
5000 (Y1 5000 · cos 30°).

### DONE
- `grenzen_der_maschine()`: Für die schräge Achse zählt der Vorschub, den Y
  im Programm schafft – `schraege_achse.hoechstwert(α, v_Y1, v_X1)`;
  kennt die ausgleichende Achse ihren Vorschub nicht, bremst nur die
  schräge (v_Y1 · cos α). Die übrigen Linearachsen wie bisher; das Kleinste
  gilt.
- Hilfe „Schruppwerte planen“ sagt, woher der Vorschub der Maschine kommt,
  auch bei einer schrägen Achse.

### TEST
- Claude ohne Oberfläche, beide Versionen: `test_schraege_achse.py`
  zusätzlich: ohne Eintrag 5000, 0° 5000, 30° 4330,13, 60° 2500, X1
  unbekannt 2500, Z1 2000 langsamer → 2000. `test_schruppwerte.py`,
  `test_beispielmaschine.py` grün.

### NEXT
- Stufe 3b, Schritt 7 (Vorlage) erst nach Manuels Entscheidung zum Aufbau;
  vorher Push der Schritte 1–6 nach dem vollen Testlauf.

## P-2026-09-26-71 schraege-achse-an-cam

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („An CAM übergeben“) und Stufe 3b,
  Schritt 5; `export.py`; FreeCADs `LinearAxis` (Richtung, Grenzen,
  `max_velocity` – keine Transformation, P-2026-09-26-65).

### DATEIEN
- `camaddon/export.py` (`_schraege_achse`, `_linearachse` mit Richtung und
  Grenzen)
- `camaddon/schraege_achse.py` (`programmrichtung`, `hoechstwert`,
  `gueltige`, `winkel_text` öffentlich)
- `help/de/transformationen.html`, `help/en/transformationen.html`
- `translations/de.json`, `translations/en.json`
- `tests/test_schraege_achse.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit schräger Achse (30°) → „Maschine bearbeiten“ →
„An CAM übergeben“ (Wochen-Build) → der Bericht sagt unter „Bitte prüfen“:
„„Y1“ ist eine schräge Achse (30,0° zu X1). CAM bekommt sie rechtwinklig wie
„Y“ im Programm …“; in CAMs Maschineneditor steht Y1 rechtwinklig zu X1 mit
Weg ±51,96 mm.

### DONE
- Für die schräge Achse bekommt CAM die Richtung der Programmachse:
  rechtwinklig zur ausgleichenden, in der Ebene beider Achsen, auf der Seite
  des Gelenks. Grenzen · cos α, Eilgang
  `hoechstwert(α, Eilgang schräg, Eilgang ausgleichend)` =
  min(v_schräg · cos α, v_ausgleich ÷ |tan α|) – das schaffen beide
  Schlitten zusammen. Name wie bisher (Y1). Fehlt der Eilgang, gilt
  FreeCADs Vorgabe wie bei jeder Achse, mit demselben Satz.
- Ein Satz unter „Bitte prüfen“: schräge Achse, Winkel, rechtwinklig wie Y
  im Programm, Grenzen gelten nur, solange X1 Platz hat – wie weit es geht,
  zeigt „Maschine verfahren“ wie im Programm (die Prüfung auf der Maschine,
  Stufe 4a, gibt es noch nicht; die Spezifikation sagt das jetzt so).
- Ohne Eintrag geht Y1 wie bisher mit seiner schrägen Richtung hinaus.
- `schraege_achse.gueltige()`: die schrägen Achsen, mit denen sich rechnen
  lässt – je Gelenk die erste.

### TEST
- Claude ohne Oberfläche: `test_schraege_achse.py` zusätzlich
  (Wochen-Build): Y1 rechtwinklig zu X1, normiert, zur Seite des Gelenks;
  X1 unverändert; Grenzen ±51,96; Eilgang 12000 · cos 30° = 10392,3;
  Satz im Bericht; ohne Eintrag schräg (X1 · Y1 = 0,5), Grenzen und
  Eilgang wie am Gelenk. `hoechstwert` für 30°, 60°, −30°, 0° (beide
  Versionen). `test_export.py` grün.

### NEXT
- Stufe 3b, Schritt 6: Höchstvorschub beim Planen.

## P-2026-09-26-70 verfahren-schmaler

### EINGELESEN
- Beim Ansehen der Screenshots zu P-2026-09-26-69: „Maschine verfahren“ war
  mit der Beispiel-Drehmaschine breiter als der Aufgabenbereich – in 1.1.3
  abgeschnitten („Werkzeugantr“, „Grenzen: -100,00 … 300,0“), mit der
  schrägen Achse ragte das Fenster rechts hinaus (Knopf (?) nicht zu sehen).
  Gemessen: Mindestbreite 423 Pixel, Aufgabenbereich 374–397 Pixel.

### DATEIEN
- `camaddon/gui_verfahren.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine → „Maschine verfahren“ → das Fenster passt in den
Aufgabenbereich: Namen, Grenzen und der Knopf (?) sind ganz zu sehen, die
Regler sind breit genug zum Ziehen, die Platzauswahl des Revolvers steht
unter seinem Zahlenfeld.

### DONE
- Die grauen Grenzen-Zeilen brechen um und reichen bis zum Rand (vorher eine
  Zeile zwischen Regler und Feld – sie bestimmte die Mindestbreite).
- Die Platzauswahl des Revolvers steht unter dem Zahlenfeld statt in einer
  vierten Spalte: Die kostete jeder Zeile Platz, und die Regler schrumpften
  bis auf den Griff. Mindestbreite jetzt 317 Pixel.

### TEST
- Claude mit Oberfläche (Screenshots angesehen), beide Versionen: gemessene
  Mindestbreite 317 statt 423 Pixel, das Fenster passt, die Regler sind
  etwa 80 (1.1.3) bzw. 190 Pixel (Wochen-Build) breit. `szenario_verfahren`,
  `szenario_verfahren_schraeg`, `szenario_beispielmaschine`,
  `szenario_mausrad` grün.

### NEXT
- Stufe 3b, Schritt 5: An CAM übergeben.

## P-2026-09-26-69 verfahren-wie-im-programm

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („Maschine verfahren“, Manuel: zuerst
  „wie im Programm“) und Stufe 3b, Schritt 4; `gui_verfahren.py`,
  `gui_zeigen.py` (Wackeln).

### DATEIEN
- `camaddon/schraege_achse.py` (`Programm`, `achsen`, `_ueberfahren`)
- `camaddon/gui_verfahren.py` (Umschalter, Programmzeilen, graue Zeile, rote
  Zeile am Anschlag)
- `camaddon/gui_zeigen.py` (`WackelnProgramm`), `camaddon/gui_maschine.py`
- `help/de/verfahren.html`, `help/en/verfahren.html`,
  `help/de/transformationen.html`, `help/en/transformationen.html`
- `translations/de.json`, `translations/en.json` (10 Texte)
- `tests/test_schraege_achse.py`, `tests/gui/szenario_verfahren_schraeg.py` (neu)
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit schräger Achse (Winkel 30° eingetragen) →
„Maschine verfahren“ → oben steht „wie im Programm“, Regler X und Y → Y auf
10 → beide Schlitten fahren, grau darunter „Schlitten: X1 −5,77 mm, Y1
11,55 mm“ → X auf 140, Y auf −40 → Y hält bei −17,32, rot: „Weiter geht Y
hier nicht: X1 steht an seiner Grenze 150,00 mm.“

### DONE
- `schraege_achse.Programm`: X und Y des Programms über einem Verfahren –
  Stellung aus den Schlitten, `setze(x, y)` fährt beide Schlitten auf der
  Geraden zum Ziel und hält an, wo einer an eine Grenze stößt (gibt Achse
  und Grenze zurück), `bereich()` so weit die Achsen überhaupt kommen.
- „Maschine verfahren“: Hat die Maschine eine gültige schräge Achse, steht
  oben „Achsen: (•) wie im Programm ( ) der Maschine“, zuerst „wie im
  Programm“. Dann stehen X und Y (Namen aus dem Eintrag) statt X1 und Y1
  da, mit Grenzen „Höchstens … – wie weit es geht, hängt davon ab, wo X
  steht“; grau darunter die Schlitten. „der Maschine“ baut die Zeilen wie
  bisher, grau darunter das Programm. Am Anschlag eine rote Zeile; jede
  andere Bewegung blendet sie aus. Das Raster wird beim Umschalten neu
  gebaut; die grauen Zeilen brechen um und reichen bis zum Rand, damit sie
  das Fenster nicht verbreitern.
- „Maschine bearbeiten“: Verweilt die Maus auf dem Eintrag, fährt die
  Maschine einmal ein Y des Programms hin und her (`WackelnProgramm`:
  X-Schlitten und Y-Schlitten zusammen), danach steht alles exakt wie
  vorher.
- Hilfe: „Maschine verfahren“ erklärt den Umschalter und den Arbeitsraum als
  Parallelogramm; „Transformationen“ verweist darauf.
- Bewusst so: nur die erste gültige schräge Achse einer Maschine (mehrere
  hat keine bekannte Maschine).
- Gefunden, nicht hier behoben: Das Verfahrfenster ist mit der
  Beispiel-Drehmaschine breiter als der Aufgabenbereich (Mindestbreite 423
  Pixel; die grauen Grenzen-Zeilen brechen nicht um) – schon vor diesem
  Patch; eigener Patch gleich danach.

### TEST
- Claude ohne Oberfläche, 1.1.3 und Wochen-Build: `test_schraege_achse.py`
  zusätzlich: Y 10 → X1 −5,7735, Y1 11,547; Bereich X −200 … 180, Y
  ±51,96; X 140 und Y −40 → Anschlag X1 bei 150, Y −17,3205; Y 70 →
  Anschlag Y1 bei 60 (Y 51,96); zurück, Grundstellung; ohne ausgleichende
  Achse nicht möglich.
- Claude mit Oberfläche (Screenshots angesehen), beide Versionen:
  `szenario_verfahren_schraeg` – Verweilen bewegt beide Schlitten und
  stellt zurück, Umschalter zuerst „wie im Programm“, Achsen C1, T,
  Werkzeugantrieb, Z1 plus X und Y, Y 10, Anschlag mit rotem Satz, „der
  Maschine“ mit grauem Programm, Y1 von Hand auf 0, Grundstellung,
  Abbrechen fährt alles zurück. `szenario_verfahren`,
  `szenario_beispielmaschine`, `szenario_mausrad`, `szenario_schraege_achse`
  laufen weiter grün (Wochen-Build).
- Ob sich „wie im Programm“ verständlich bedient, prüft Manuel.

### NEXT
- Verfahrfenster schmaler (eigener Patch), dann Stufe 3b, Schritt 5: An CAM
  übergeben.

## P-2026-09-26-68 schraege-achse-erkennen

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („Erkennung“) und Stufe 3b, Schritt 3.

### DATEIEN
- `camaddon/schraege_achse.py` (`ohne_eintrag`, `Anlegen`, Hinweis in `pruefe`)
- `camaddon/gui_maschine.py` (Klick auf den Hinweis legt an)
- `translations/de.json`, `translations/en.json`
- `tests/test_schraege_achse.py`, `tests/gui/szenario_schraege_achse.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Eine Baugruppe, deren Y-Führung 30° schräg zu X steht, ohne Eintrag →
„Maschine bearbeiten“ → unter „Hinweise“ steht „Y1 steht 30,0° schräg zu X1.
Rechnet die Steuerung ein rechtwinkliges „Y“ auf beide um …?“ → Klick
darauf → unter „Transformationen“ steht „Schräge Achse Y1 – gleicht aus:
X1, 30,0°“, und der Hinweis ist weg.

### DONE
- `schraege_achse.ohne_eintrag()`: alle Paare von Linearachsen, die weder
  rechtwinklig (unter 0,05° – Rundungsreste; ab da zeigt der Dialog 0,1°)
  noch fast parallel (über 89°) stehen und noch keine schräge Achse haben –
  auch nicht mit vertauschten Rollen. Ausgleichend ist die im Alphabet
  vordere. `vorschlag()` nutzt es.
- `pruefe()` gibt je solches Paar einen **Hinweis** (keine Warnung – eine
  Maschine darf schräge Achsen ohne Umrechnung haben; „An CAM übergeben“
  fragt deshalb nicht nach). Sein Bezug ist `Anlegen(schräg, ausgleich)`;
  ein Klick darauf legt die schräge Achse an – zeitversetzt, weil der
  Neuaufbau auch die angeklickte Zeile ersetzt.
- Der Winkel im Satz mit dem gewählten Dezimalzeichen („30,0°“), ohne
  Oberfläche gerechnet (`_winkel_text`).

### TEST
- Claude ohne Oberfläche, 1.1.3 und Wochen-Build: `test_schraege_achse.py`
  zusätzlich: rechtwinklige Maschine ohne Hinweis; 30° ohne Eintrag – ein
  Hinweis, Text „Y1 steht 30,0° schräg zu X1.“ mit „Y“, Bezug Y1/X1, auch
  über `m.pruefe`; mit Eintrag (auch vertauscht) kein Hinweis.
- Claude mit Oberfläche (Screenshot angesehen), beide Versionen:
  `szenario_schraege_achse` – der Hinweis steht da, ein Klick legt den
  Eintrag mit 30,0° an, der Hinweis verschwindet.

### NEXT
- Stufe 3b, Schritt 4: „Maschine verfahren“ wie im Programm.

## P-2026-09-26-67 schraege-achse-winkel-eintragen

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („Winkel eintragen, die Baugruppe
  folgt“, Manuels Entscheidung) und Stufe 3b, Schritt 2; Versuch aus
  P-2026-09-26-65.

### DATEIEN
- `camaddon/schraege_achse.py` (`drehe_fuehrung`, `_drehe_gelenk`)
- `camaddon/verfahren.py` (`setze(…, grenzen=False)`)
- `camaddon/gui_details.py`, `camaddon/gui_maschine.py`, `camaddon/gui_zahlen.py`
- `help/de/transformationen.html`, `help/en/transformationen.html`
- `translations/de.json`, `translations/en.json`
- `tests/test_schraege_achse.py`, `tests/gui/szenario_schraege_achse.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine → „Maschine bearbeiten“ → „+ Schräge Achse“ → im Feld
„Winkel“ 30 eintragen → in der 3D-Ansicht bleibt alles stehen, der Eintrag
zeigt 30,0° und „Y +10,0 mm → Y1 +11,5 mm, X1 −5,8 mm“; „Maschine verfahren“
fährt Y1 danach schräg; Abbrechen stellt die Führung zurück.

### DONE
- `schraege_achse.drehe_fuehrung()`: dreht beide Koordinatensysteme des
  Y-Schiebegelenks um die Normale der Ebene aus schräger und ausgleichender
  Achse (so, dass α um die Differenz wächst), je um ihren Ursprung, über
  Offset1/Offset2 (global = ohne Versatz · Versatz). Nach jeder Änderung am
  Versatz kommen die Teile zurück (FreeCAD löst vorab und rückt sonst
  Teile). Steht der Schlitten nicht auf 0, fährt er vorher auf 0 und danach
  wieder auf seine Stellung – nun entlang der neuen Richtung, auch außerhalb
  der Grenzen (`Verfahren.setze(…, grenzen=False)`). Über ±89°: ValueError.
- Dialog: Das Feld „Winkel“ (mit „°“, auch negative Zahlen:
  `Zahlenpruefer(mit_minus=True)`) zeigt den Winkel der Baugruppe; ein
  anderer Wert dreht die Führung, danach zeigen Liste, Bild und Beispiel den
  neuen Stand. Leer oder unverändert: nichts passiert. Über ±89° sagt ein
  roter Satz am Feld, warum nicht, und das Feld zeigt wieder den alten
  Winkel. Die Bewegung beim Zeigen (Wackeln) hält vorher an.
- Tooltip und Hilfe erklären das Eintragen; „… – aus der Baugruppe“ als
  Anzeige entfällt (das Feld ersetzt es).

### TEST
- Claude ohne Oberfläche, 1.1.3 und Wochen-Build: `test_schraege_achse.py`
  zusätzlich: 30° eintragen – kein Teil bewegt sich, auch nicht beim
  Neuberechnen; Rückgängig stellt 0° und alle Lagen wieder her,
  Wiederholen 30°; mit Y1 auf 20 mm auf −15° – die Stellung bleibt 20 mm,
  der Schlitten steht 20 mm entlang der neuen Richtung, der Revolver dreht
  sich nicht; zurück auf 0° und Stellung 0 – alles wie gebaut; 89,5°, −90°
  und 120° abgelehnt, ohne etwas zu drehen. Dazu `test_sprache`,
  `test_hilfe`, `test_verfahren`, `test_maschine`.
- Claude mit Oberfläche (Screenshots angesehen), beide Versionen:
  `szenario_schraege_achse` – 30 eintragen (Liste, Feld, Beispiel, keine
  Teile bewegt), 95 abgelehnt mit rotem Satz, Abbrechen stellt die Führung
  zurück (Y wieder rechtwinklig zu X).
- Ob sich das Eintragen verständlich anfühlt, prüft Manuel.

### NEXT
- Stufe 3b, Schritt 3: Erkennung schräg stehender Linearachsen.

## P-2026-09-26-66 schraege-achse-eintrag

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c und Stufe 3b, Schritt 1
  (P-2026-09-26-65). Manuel: „weiter machen mit Sachen, die man verbessern
  kann … bis zu einem sinnvollen Punkt“.
- `maschine.py` (Objektarten, `pruefe`, `rollen`), `gui_maschine.py`,
  `gui_details.py`, `gui_zahlen.py`, `verfahren.py` (`_vorzeichen`),
  `hilfe.py`, `tests/test_hilfe.py`, `tests/test_sprache.py`.

### DATEIEN
- `camaddon/schraege_achse.py` (neu), `camaddon/gui_winkelbild.py` (neu)
- `camaddon/maschine.py`, `camaddon/gui_maschine.py`,
  `camaddon/gui_details.py`, `camaddon/gui_zahlen.py`,
  `camaddon/verfahren.py`, `camaddon/hilfe.py`
- `help/de/transformationen.html`, `help/en/transformationen.html` (neu)
- `translations/de.json`, `translations/en.json` (28 Texte)
- `tests/test_schraege_achse.py` (neu), `tests/beispielmaschinen.py`,
  `tests/gui/szenario_schraege_achse.py` (neu)
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/aufbau.md`, `CHATSTART.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine laden → „Maschine bearbeiten“ → „+ Schräge Achse“ →
unter „Transformationen“ steht „Schräge Achse Y1 – gleicht aus: X1, 0,0°“,
darunter Y1 und X1, die Namen Y und X, „0,0° – aus der Baugruppe“, das Bild
und „Beispiel: Y +10,0 mm → Y1 +10,0 mm, X1 0,0 mm“.

### DONE
- Maschinenobjekt: dritte Art von Eintrag, die **Transformation**
  (`TRAFO_SCHRAEGE_ACHSE`): Verweise `Schraeg` und `Ausgleich` auf
  Betriebsarten (Linear), `NameSchraeg`/`NameAusgleich` – vorbelegt mit dem
  NC-Namen ohne Ziffern am Ende (Y1 → Y). Beschriftung „Y · Schräge Achse“.
  Der Winkel steht bewusst nicht im Objekt, nur in der Baugruppe.
- `schraege_achse.py`: Winkel α aus den Gelenkrichtungen (asin des
  Skalarprodukts der Plus-Richtungen; Tischachsen zählen für das Werkzeug
  andersherum), Rechnung Programm ↔ Schlitten, Vorschlag für eine neue
  schräge Achse (zuerst ein schräges Paar ohne Eintrag, sonst die ersten
  beiden Linearachsen; ausgleichend ist die im Alphabet vordere), Prüfung
  mit vier Meldungen (Achse fehlt, gleiche Achse, keine Linearachse, fast
  parallel über 89°). `verfahren.plusrichtung()` neu (öffentlich statt
  `_vorzeichen` von außen).
- Dialog: Bereich „Transformationen“ unter den Achsen mit Hilfe (?),
  Liste (ohne Eintrag eine graue Zeile „keine – nur nötig, wenn die
  Steuerung umrechnet“), „+ Schräge Achse“ (ohne zwei Linearachsen gesperrt,
  der Tooltip sagt warum) und „Entfernen“. Felder: schräge und
  ausgleichende Achse als Auswahl, Namen im Programm (wandern mit, solange
  sie der Vorschlag sind: Z1 gewählt → Z), Winkel „30,0° – aus der
  Baugruppe“, Bild (`gui_winkelbild.py`: X1, gestrichelt der rechte Winkel
  mit dem Programm-Y, Y1 um α gekippt, Bogen α – ohne Text außer
  Achsnamen) und das Beispiel in mm bzw. inch. Verweilen hebt beide
  Schlitten hervor. Wer eine Betriebsart entfernt, löst ihren Verweis in
  der schrägen Achse (die dann „fehlt eine Achse“ meldet).
- Hilfeseite „Transformationen“ (de/en): was sie sind, Rechnung mit
  Beispiel, was man einträgt, wo der Winkel bei Siemens (TRAANG,
  `TRAANG_ANGLE_1`) und Fanuc („Angular Axis Control“) steht,
  Vorzeichen andersherum möglich, Postprozessor bleibt.
- `gui_zahlen.winkel_zeigen()`: „30,0°“ mit dem gewählten Dezimalzeichen.
- Bewusst noch nicht: den Winkel eintragen (Schritt 2), das
  Hin-und-her-Fahren beim Verweilen (braucht das gekoppelte Verfahren aus
  Schritt 4), Erkennung als Hinweis (Schritt 3).

### TEST
- Claude ohne Oberfläche, 1.1.3 und Wochen-Build: `test_schraege_achse.py`
  – Rechnung (30°: Y +10 → Y1 11,547, X1 −5,774; −30°; 0°; hin und zurück
  für sechs Winkel), Winkel 0° an der Beispiel-Drehmaschine, +30° und −30°
  mit gekippter Y-Führung (Testhilfe `beispielmaschinen.kippe_fuehrung`),
  89,5° → Meldung „parallel“, Vorschlag, Namen, Meldungen, Tisch/Kopf,
  Speichern und Laden. Dazu `test_sprache`, `test_hilfe`, `test_maschine`,
  `test_verfahren`, `test_kette`, `test_export`, `test_beispielmaschine`.
- Claude mit Oberfläche (Screenshots angesehen), 1.1.3 und Wochen-Build:
  `szenario_schraege_achse` – leere Liste, anlegen, Felder, Z1 wählen
  (Name wandert mit), Abbrechen verwirft, 30° gekippt zeigt 30,0° und
  „Y1 +11,5 mm, X1 −5,8 mm“, Entfernen, Hilfe. Die Szenarien
  `maschine_bearbeiten`, `hilfe`, `mausrad`, `beispielmaschine`, `felder`
  laufen weiter grün (Wochen-Build).
- Ob der Bereich verständlich ist, prüft Manuel.

### NEXT
- Stufe 3b, Schritt 2: Winkel eintragen, die Baugruppe folgt.

## P-2026-09-26-65 spezifikation-schraege-achse

### EINGELESEN
- Manuel (2026-09-26): „schrägbett kinematik … eine schräge Achse für X
  und noch eine schräge Achse für Y, und beide müssen verfahren, um Y zu
  bewegen … erstmal nur planen“. Nach dem Plan im Chat: „das sind alles
  wichtige Faktoren, die man eingeben können sollte … oder so, dass es ein
  Leichtes ist, so etwas zu erstellen“.
- Seine Wahl aus vier Fragen mit Optionen: erst Eintrag in „Maschine
  bearbeiten“, danach Vorlage mit Eingabemaske; Winkel eintragen, die
  Baugruppe folgt; „Maschine verfahren“ zuerst wie im Programm. Zur
  Auswahl der Steuerung: „Man hat doch einen Postprozessor??“
- `spezifikation_maschine_aus_baugruppe.md`, `spezifikation_simulation.md`
  (Abschnitt 4 rechnet schon mit schiefen Achsen), `kette.py`,
  `verfahren.py`, `export.py`, `beispielmaschine.py` (Drehmaschine:
  Schrägbett 45°, Y rechtwinklig zu X), `gui_maschine.py`, `maschine.py`,
  `schruppwerte.py` (Höchstvorschub = kleinster aller Linearachsen).
- FreeCADs CAM-Maschinendefinition (Wochen-Build,
  `Mod/CAM/Machine/models/machine.py`): je Linearachse nur Richtung,
  Grenzen, Eilgang; keine Transformation. Für Bahnen nutzt CAM nur die
  Drehachsen (`Path/Base/Generator/rotation.py`); die Maschine trägt einen
  Postprozessor (`postprocessor_file_name`).
- Siemens 840D sl, Funktionshandbuch Sonderfunktionen: TRAANG,
  `TRAANG_ANGLE_1`, −90° < α < 90°. Fanuc: „Angular Axis Control“
  (Parameternummern nicht nachgeprüft, deshalb nicht genannt).

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 7c neu,
  Abschnitt 2 ergänzt, Stufe 3b, Entschieden)
- `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel findet in Abschnitt 7c der Maschinen-Spezifikation seine vier
Entscheidungen, die Rechnung mit Beispiel und die sieben Schritte mit
Klickweg wieder.

### DONE
- Abschnitt 7c „Schräge Achse“: Begriffe (schräge und ausgleichende Achse,
  Winkel α, Programmachsen), Rechnung in beide Richtungen mit Beispiel
  (α = 30°: Y +10 → Y1 +11,547, X1 −5,774), Folgen (Arbeitsraum als
  Parallelogramm, Geschwindigkeit min(vY1 · cos α, vX1 ÷ tan α)),
  Transformation als dritte Art von Eintrag im Maschinenobjekt, Winkel nur
  in der Baugruppe, Erkennung, Skizzen für „Maschine bearbeiten“ und
  „Maschine verfahren“, Übergabe an CAM, Schruppwerte, Stufe 4, Vorlage,
  „Nicht Teil davon“.
- Stufe 3b mit sieben Schritten; Entscheidung unter „Entschieden“ – ohne
  Auswahl der Steuerung, wie Manuels Rückfrage nahelegt: Die Steuerung
  steckt im Postprozessor, und das Programm bleibt rechtwinklig.
- Bewusst offen: Aufbau der Vorlage (eigener Befehl oder in
  „Beispielmaschine laden …“) – wird vor Schritt 7 mit Skizze entschieden;
  das Vorzeichen von α bei Siemens – vor dem Hilfetext im Handbuch prüfen.

### TEST
- Versuch (Claude, ohne Oberfläche, 1.1.3 und Wochen-Build): an der
  Beispiel-Drehmaschine beide Gelenk-Koordinatensysteme des Y-Gelenks um
  30° gedreht (Offset1/Offset2, um die Normale der X/Y-Ebene). Ergebnis in
  beiden Versionen: kein Teil bewegt sich, X/Y stehen danach 120° (Y 30°
  aus dem rechten Winkel), Y1 = 10 fährt den Schlitten genau 10 mm in der
  neuen Richtung, der Revolver dreht sich nicht, die Stellung bleibt beim
  Neuberechnen, die Grundstellung ist exakt, der Winkel bleibt nach
  Speichern und Laden. Damit trägt die Entscheidung „die Baugruppe folgt“.
- Reine Doku, kein Testlauf.

### NEXT
- Stufe 3b, Schritt 1: Eintrag „Schräge Achse“ in „Maschine bearbeiten“.

## P-2026-09-26-64 version-0-18-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.17.0: Beispielmaschinen zur Auswahl (P-2026-09-26-62), ruhiges Mausrad
  (-63).

### DATEIEN
- `package.xml` (0.18.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.18.0.

### DONE
- Version 0.17.0 → 0.18.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Schrägbett-Kinematik planen (Manuel).

## P-2026-09-26-63 ruhiges-mausrad

### EINGELESEN
- #39 und P-2026-09-26-52: Das „P10“ in Manuels Revolverplatz war sehr
  wahrscheinlich das Mausrad beim Blättern im Aufgabenfenster.
- Alle Auswahllisten, Drehfelder und Regler des Addons (`gui_*.py`), Qts
  Weitergabe von Rad-Ereignissen (nur echte, nicht mit sendEvent
  geschickte), FreeCADs eigenes `Gui::WheelEventFilter` (1.1.3 und
  Wochen-Build, dort erweitert).

### DATEIEN
- `camaddon/gui_teile.py` (`ruhiges_mausrad`, `RuhigerRegler`)
- `camaddon/gui_werkzeuge.py`, `gui_job_schnittwerte.py`, `gui_werkstoffe.py`,
  `gui_strategie.py`, `gui_verteilhilfe.py`, `gui_verfahren.py`,
  `gui_details.py`, `gui_maschine.py`, `gui_sprachwahl.py`
- `tests/gui/szenario_mausrad.py` (neu)
- `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Maschine bearbeiten“ an der Beispiel-Drehmaschine → P3 wählen → mit dem
Mausrad über dem Feld „Revolverplatz“ blättern: Das Aufgabenfenster rollt,
der Platz bleibt P3. Erst nach einem Klick ins Feld rollt das Rad den Wert.
Genauso Art und Nummer in der Werkzeugverwaltung, der Einsatz je Zeile in
„Schnittwerte in den Job“, die Regler in „Maschine verfahren“.

### DONE
- Auswahllisten, Drehfelder und Regler aller Dialoge und Aufgabenfenster
  nehmen das Mausrad nur mit Fokus; den Fokus gibt ihnen das Rad auch nicht
  mehr. Ohne Fokus geht die Raste an den nächsten Bereich darüber, der
  rollen kann – Aufgabenfenster oder Tabelle blättern weiter.
- Die Regler in „Maschine verfahren“ lehnen das Rad ohne Fokus selbst ab:
  Im Wochen-Build kommt es im Aufgabenfenster am Filter vorbei.
- Im Wochen-Build schützt FreeCAD Drehfelder im Aufgabenfenster schon
  selbst und schluckt das Rad dabei – dort rollt das Fenster über einem
  Feld nicht weiter (FreeCADs Verhalten); verstellt wird nichts.

### TEST
- Neu `szenario_mausrad`: Rasten über XTest wie von einer Maus; Sprachwahl,
  Art und Nummer (mit Fokus rollt die Nummer T1 → T2), Revolverplatz mit
  Gegenprobe (ein Drehfeld ohne Filter verstellt sich in 1.1.3, das
  Fenster rollt), Regler und Feld beim Verfahren – in 1.1.3 und im
  Wochen-Build. Szenarien `werkzeugverwaltung`, `schnittwerte_job`,
  `verfahren`, `erster_start`, `werkstoffe`, `strategien` im Wochen-Build.

### NEXT
- Schrägbett-Kinematik planen (Manuel): X und Y als schräge Achsen, für
  eine Bewegung in Y fahren beide.

## P-2026-09-26-62 beispielmaschinen-zur-auswahl

### EINGELESEN
- STATUS_SNAPSHOT Punkt 7b (Manuel nach dem ersten Ausprobieren): die
  üblichen Bauarten zur Auswahl – Schrägbett-Drehmaschine mit Y-Achse
  (CLX-ähnlich, Revolver mit radialem und axialem angetriebenem Werkzeug),
  3-Achs-Fräse, 5-Achs Tisch/Tisch (A/C), Kopf/Kopf (A/B), Kopf/Tisch
  (B/C).
- Der geparkte Stand im Stash „WIP Beispielmaschinen zur Auswahl“
  (Baukasten, fünf Bauarten, Auswahldialog), `tests/test_beispielmaschine.py`,
  `tests/gui/szenario_beispielmaschine.py`, `tests/gui/szenario_zoll.py`.

### DATEIEN
- `camaddon/beispielmaschine.py` (Baukasten erweitert: Rahmen, gedrehte
  Zylinder, LCS mit Richtung; fünf Bauarten; `titel`, `beschreibung`,
  `zuletzt_gewaehlt`, `lade(art)`)
- `camaddon/gui_maschine.py` (`beispiel_waehlen`, `BeispielAuswahl`),
  `camaddon/gui_verfahren.py`
- `translations/de.json`, `translations/en.json`
- `help/de/achsen.html`, `help/en/achsen.html`, `help/de/verfahren.html`,
  `help/en/verfahren.html`
- `docs/aufbau.md`, `docs/STATUS_SNAPSHOT.md`
- `tests/test_beispielmaschine.py`, `tests/gui/szenario_beispielmaschine.py`,
  `tests/gui/szenario_zoll.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Leeres FreeCAD → „Maschine bearbeiten“ → „Beispielmaschine laden …“ → die
Auswahl zeigt fünf Bauarten mit je einem Satz dazu; „Drehmaschine mit
Y-Achse“ → Laden: Dokument „Beispiel Drehmaschine“, der Dialog ist offen,
P1 auf dem Revolver hat das Feld „Revolverplatz“. „Maschine verfahren“ in
einem leeren Dokument → 3-Achs-Fräse → X1, Y1, Z1 fahren.

### DONE
- „Beispielmaschine laden …“ bietet fünf Bauarten an, fertig eingerichtet:
  Drehmaschine mit Y-Achse (Schrägbett 45°, Hauptspindel S1/C1, X1, Y1, Z1,
  Revolver T mit zwölf Plätzen, P1 radial und P2 axial angetrieben an S3),
  3-Achs-Fräse (X1, Y1, Z1, S1), 5-Achs Tisch/Tisch (A1, C1), Kopf/Kopf (A1,
  B1), Kopf/Tisch (B1, C1) – je mit Werkzeug- und Werkstückaufnahme.
- Die Auswahl steht beim nächsten Mal auf der zuletzt geladenen; Doppelklick
  lädt.

### TEST
- `test_beispielmaschine` (neu: alle fünf – Achsen, keine Warnung, Teile
  bleiben beim Neuberechnen, jede Achse fährt, Grundstellung, Revolver)
  in 1.1.3 und im Wochen-Build; Szenarien `beispielmaschine` (neu: Auswahl,
  Drehmaschine mit Revolverplatz, Übersicht aller fünf als Bild) und
  `zoll` in beiden. Bilder angesehen.

### NEXT
- #39: Mausrad soll Felder und Auswahllisten nicht verstellen, wenn man
  nur über sie scrollt.

## P-2026-09-26-61 version-0-17-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.16.0: Revolverplatz nur am Revolver (P-2026-09-26-52), die 26
  Werkzeugarten (P-2026-09-26-53 bis -60), Szenario wartet auf die
  Beispielmaschine (-57).

### DATEIEN
- `package.xml` (0.17.0; Beschreibung nennt die 26 Werkzeugarten)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.17.0.

### DONE
- Version 0.16.0 → 0.17.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann die Beispielmaschinen zur Auswahl (Punkt 7b).

## P-2026-09-26-60 einsaetze-in-den-job

### EINGELESEN
- Spezifikation Werkzeugarten, Abschnitt 8 (Stufe 6): die neuen Einsätze
  auf die passenden Operationen.
- `camaddon/job_schnittwerte.py` (`EINSATZ_NACH_OPERATION`,
  `ZUSTELLUNG_NACH_OPERATION`, `vorgeschlagener_einsatz`, `zustellung`),
  die Operationen in 1.1.3 und im Wochen-Build (`Path/Op`: MillFace,
  MillFacing, Deburr, ThreadMilling, Tapping, Drilling, Engrave, Vcarve).

### DATEIEN
- `camaddon/job_schnittwerte.py`
- `translations/de.json`, `translations/en.json` (Tooltip der Zustellung)
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `docs/spezifikation_werkzeugarten.md`, `docs/STATUS_SNAPSHOT.md`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit Fläche (Planfräser, Einsätze „Sonder“ und „Planen“ ae 37,5 ap 2)
und Bohrung (Zentrierbohrer) → „Schnittwerte in den Job“: Der Planfräser
bekommt „Planen“ und „Fläche: 75 % · 2 mm“, der Zentrierbohrer „Zentrieren“
mit n 2546 und vf 255 – senkrecht der volle.

### DONE
- Je Operation die passenden Einsätze, der passendste zuerst: Fläche →
  Planen oder Schruppen, Profil → Schlichten, Verrunden oder Fasen,
  Entgraten → Fasen oder Verrunden, Gravieren und V-Carve → Fasen,
  Gewindefräsen, Gewindebohren, Bohren → Bohren, Zentrieren, Senken,
  Reiben, Ausdrehen, Gewindebohren. Bisherige Zuordnungen bleiben.
- Planen gibt der Fläche (auch dem Planfräsen des Wochen-Builds) ae als
  Schrittweite und ap als Zustelltiefe.
- Stufe C der Werkzeugarten damit fertig; STATUS_SNAPSHOT nachgezogen.

### TEST
- `test_job_schnittwerte` (neu: Fläche, Entgraten, Bohrung; Einsatz aus der
  zweiten und fünften Zeile; Zustellung Planen) in 1.1.3 und im
  Wochen-Build; Szenario `schnittwerte_job` (neu: Planfräser und
  Zentrierbohrer) in beiden. Bild angesehen.

### NEXT
- Version 0.17.0, voller Lauf `scripts/alle_tests.sh` in beiden Versionen,
  Push von P-52 bis P-60.
- Danach Punkt 7b: Beispielmaschinen zur Auswahl (Stash).

## P-2026-09-26-59 cam-alle-werkzeugarten

### EINGELESEN
- Spezifikation Werkzeugarten, Abschnitte 2, 6 und 8 (Stufe 5): CAM-Form je
  Art, Näherungen, Übernahme je Form.
- FreeCAD CAM in 1.1.3 und im Wochen-Build: die Formen (`Path/Tool/shape/
  models`, Skizzen und Ausdrücke in `Tools/Shape/*.fcstd`), die Musterwerkzeuge
  in `Tools/Bit`, `ToolBit.from_dict`/`from_shape`, `ThreadMilling`,
  `Tapping`/`Drilling` (Pitch, SpindleDirection), `FeedsSpeeds` (Chipload je
  Zahn mal Flutes, `vert_feed_ratio`), das Bibliotheksfenster.

### DATEIEN
- `camaddon/uebergabe_werkzeuge.py` (FORMEN aller Arten, NAEHERUNGEN,
  Parameter je Form, Drehrichtung, Chipload, Mindestschaft)
- `camaddon/werkzeuge_aus_cam.py` (jede Form → Art, alle Maße der Art)
- `camaddon/werkzeuge.py` (`mass`, `reichweite`, Gesamtlänge ab Halsende,
  `schaft_fuer_cam` je Art)
- `camaddon/werkzeugform.py` (Schätzungen aus `werkzeuge.mass`; `konus`,
  `kegel`, `radienprofil` auch für CAM; Konikkegel tangential, Radienbogen
  ab dem Spitzen-Ø)
- `camaddon/gui_werkzeuge.py` (Bericht: Näherungen; Schaft-Platzhalter)
- `translations/de.json`, `translations/en.json`
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `docs/spezifikation_werkzeugarten.md`, `docs/aufbau.md`
- `tests/test_cam_formen.py` (neu), `tests/test_uebergabe_werkzeuge.py`,
  `tests/test_werkzeuge_aus_cam.py`, `tests/test_werkzeuge.py`,
  `tests/gui/szenario_an_cam.py`, `tests/gui/szenario_aus_cam.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung mit Gewindebohrer links, Konik-, Lollipop-,
Schwalbenschwanzfräser, Taster und Drehwerkzeug → „Speichern und an CAM
übergeben“: Die Rückmeldung nennt „T9 Lollipopfräser als Kugelfräser“ und
„Drehwerkzeuge bleiben hier: T15 Drehwerkzeug“. In CAM → Werkzeugbibliothek
„CAM-Addon“ steht jedes mit seiner Form (Left Hand tap 1,5 mm, 6° taper,
60° dovetail, probe). „Aus CAM übernehmen“ → „Default“ übernimmt alle 13
Werkzeuge, auch Gravierstichel (Fasenfräser), Säge (Nutenfräser), Taster und
Gewindefräser.

### DONE
- Übergabe: jede der 23 Arten, die nicht drehen, mit ihrer CAM-Form und
  deren Parametern; leere Felder geschätzt wie im Bild, damit CAM denselben
  Körper baut. Näherungen (Lollipop-, Plan-, Formfräser, Zentrierbohrer,
  Flachsenker, Bohrstange, Ausspindelwerkzeug) nennt der Bericht; die
  Drehwerkzeuge bleiben hier.
- Gewindebohrer mit Steigung, links rückwärts drehend, ohne Schneidenzahl
  und ohne Chipload; Taster ohne Drehrichtung und Schneidstoff; Reibahle
  (in CAM ohne Schneidenzahl) mit f je Umdrehung als Chipload; Presets der
  bohrenden Arten mit vollem Eintauchvorschub wie „Schnittwerte in den Job“.
- CAMs Skizzen vertragen keine Kante der Länge 0 und keinen Hals bis ans
  Ende: Säge mit 1 µm Kappe, Gewindebohrer-Schaft = D wird 1 µm dünner, zu
  kurze Gesamtlänge bekommt 1 mm Schaft. Die geschätzte Gesamtlänge zählt
  jetzt ab dem Ende des Halses (beim Gewindefräser brach vorher CAMs Körper).
- Übernahme: jede Form hat ihre Art (vbit → Fasenfräser, tap nach
  Drehrichtung, threadmill mit einem Zahn: Schneidenlänge = Zahnhöhe);
  gesetzt wird nur, was die Art als Feld hat; fehlt die Schneidenzahl, die
  der Beispiele der Art.
- Die Schätzungen für Bild und CAM an einer Stelle (`werkzeuge.mass`); das
  Bild des Radienfräsers nimmt jetzt den Spitzen-Ø, der Konikkegel berührt
  die Kugel.

### TEST
- Neu `test_cam_formen`: alle Arten an CAM, Beispiele, Schaft = D und zu
  kurze Gesamtlänge; CAM baut jeden Körper ohne Klage auf der Konsole, nur
  Parameter der Form, auf 40 Höhen wie das Bild, zurück aus CAM dieselben
  Maße. Gegenprobe: Kappe 0, Schaft = D und halber Kegelwinkel fängt er.
- `test_uebergabe_werkzeuge`, `test_werkzeuge_aus_cam`, `test_werkzeuge`,
  `test_werkzeugform`, `test_sprache`, `test_hilfe` in 1.1.3 und im
  Wochen-Build; Szenarien `an_cam`, `aus_cam` in beiden, `werkzeugbilder`,
  `werkzeugverwaltung` in 1.1.3. Bilder angesehen.

### NEXT
- Stufe C6: die neuen Einsätze auf die passenden Operationen im Job.

## P-2026-09-26-58 einsaetze-je-art

### EINGELESEN
- Spezifikation Werkzeugarten, Abschnitte 5 und 8 (Stufe 4): Einsätze je
  Art, Rechnen für Bohren, Gewindebohren, Drehen, Taster.
- `camaddon/gui_schnittwerte.py` (sechs Stellen „Bohrer oder nicht“),
  `camaddon/schnittdaten.py` (`rechne`), `camaddon/job_schnittwerte.py`
  (Eintauchvorschub), `camaddon/uebergabe_werkzeuge.py` (Presets), die
  Bearbeitungsarten der FreeCAD-Presets (`FeedsSpeeds.types.OP_TYPES`).

### DATEIEN
- `camaddon/werkzeuge.py` (neun Einsatzarten, `EINSAETZE_JE_ART`,
  `einsatzarten`, `bohrend`, `gewindebohrer`, Vorlage Planen)
- `camaddon/schnittdaten.py`, `camaddon/gui_schnittwerte.py`,
  `camaddon/job_schnittwerte.py`, `camaddon/uebergabe_werkzeuge.py`
- `translations/de.json`, `translations/en.json`
- `docs/spezifikation_werkzeugarten.md`
- `tests/test_schnittdaten.py`, `tests/test_werkzeuge.py`,
  `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Gewindebohrer rechts M10 → „+ Einsatz“ bietet nur
„Gewindebohren“ und „Eigener Einsatz“; mit vc 10 zeigt die Zeile f 1,5
(fest), n 318, vf 477. Ein Drehwerkzeug zeigt statt der Tabelle einen Satz.

### DONE
- Neue Einsatzarten: Planen, Fasen, Verrunden, Gewindefräsen, Zentrieren,
  Senken, Reiben, Gewindebohren, Ausdrehen – je Art nur die passenden.
- Bohrende Arten (Gruppe Bohren) wie bisher der Bohrer: f je Umdrehung,
  ohne ae/ap, kein Vergleich, kein Eingriffsbild; im Job tauchen sie mit
  vollem Vorschub ein. Gewindebohrer: vf = n · P, f fest (grau), Hinweis
  nur für vc. Q nur beim Fräsen und beim Bohrer ins Volle.
- Drehwerkzeuge und Taster: ein Satz statt der Tabelle.
- Presets für CAM: neue Einsätze auf FreeCADs sechs Bearbeitungsarten.

### TEST
- `test_schnittdaten` (Gewindebohrer, Reibahle), `test_werkzeuge`
  (Einsätze je Art, Vorlage Planen), `test_sprache`,
  `test_uebergabe_werkzeuge`, `test_job_schnittwerte`, `test_schruppwerte`
  in 1.1.3 und im Wochen-Build; Szenarien `schnittwerte` (neu:
  Gewindebohrer, Drehwerkzeug), `werkzeugverwaltung`, `strategien`,
  `schnittwerte_job` in 1.1.3. Bilder angesehen.

### NEXT
- Stufe C5: Übergabe an CAM und Übernahme aus CAM für alle Arten.

## P-2026-09-26-57 szenario-wartet-auf-beispielmaschine

### EINGELESEN
- `szenario_zoll` scheiterte beim Lauf für P-2026-09-26-56 einmal:
  „Maschine verfahren öffnet sich nicht“, im Protokoll „Cannot access
  attribute 'Document' of deleted object“ in `gui_verfahren.Activated`.
- `tests/gui/_lauf/szenario_lauf.py` (`_ende` schließt Aufgabenfenster und
  Dokumente), `tests/gui/szenario_zoll.py`,
  `tests/gui/szenario_beispielmaschine.py` (feste 2,5 s nach „Beispielmaschine
  laden“).

### DATEIEN
- `tests/gui/_lauf/szenario_lauf.py` (`Helfer.warte_auf`)
- `tests/gui/szenario_zoll.py`, `tests/gui/szenario_beispielmaschine.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Szenarien prüfen den Dialog nach „Beispielmaschine laden“ erst, wenn er
offen ist – auch wenn das Laden länger als 2,5 s dauert.

### DONE
- Ursache: Beim Neuberechnen lässt FreeCADs Fortschrittsbalken Ereignisse
  durch; dauerte das Laden länger als die feste Wartezeit, prüfte das
  Szenario zu früh, endete, und der Lauf schloss das Dokument, während
  `lade()` noch lief – daher das gelöschte Objekt. Am Addon selbst liegt es
  nicht.
- `Helfer.warte_auf(bedingung)`: wartet in Schritten von 250 ms, höchstens
  20 s. Beide Szenarien warten auf ihr Aufgabenfenster.
- Der geparkte Stand „Beispielmaschinen zur Auswahl“ (Stash) wartet noch
  fest 3 s – beim Weitermachen ebenso umstellen.

### TEST
- `szenario_zoll`, `szenario_beispielmaschine` (1.1.3).

### NEXT
- Stufe C4: Einsätze je Art.

## P-2026-09-26-56 werkzeugbilder

### EINGELESEN
- Spezifikation Werkzeugarten, Abschnitt 4 und 8 (Stufe 3): Bilder aller
  Arten, auch klein in der Auswahl.
- Manuel (Screenshot-Rückmeldung zu C2): „die Grafik bei den
  Drehwerkzeugen ist dennoch nicht korrekt … auch der Zentrierbohrer … ist
  eher spitz ;)“.
- `camaddon/gui_werkzeugbild.py` (bisher fünf Arten fest verdrahtet).

### DATEIEN
- `camaddon/werkzeugform.py` (neu: Umriss je Art, ohne Oberfläche)
- `camaddon/gui_werkzeugbild.py` (malt die Teile, Symbol je Art)
- `camaddon/gui_werkzeuge.py` (Symbole in der Auswahl „Art“)
- `tests/test_werkzeugform.py` (neu), `tests/gui/szenario_werkzeugbilder.py`
  (neu)
- `docs/spezifikation_werkzeugarten.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Neu → Art durchblättern: Jede der 26 Arten zeigt
neben den Feldern ihre Form – der Zentrierbohrer spitz mit Senkung, das
Drehwerkzeug als Halter mit Wendeplatte, der Taster mit roter Kugel –, und
in der aufgeklappten Auswahl steht vor jedem Namen ein kleines Bild.

### DONE
- `werkzeugform.teile()`: je Art Teile (Schaft, Schneide, Kugel) als
  Vielecke in mm, mit Wendel rechts/links/gerade; gestrichelt, was
  Beispiel oder geschätzt ist. Zentrierbohrer: Zapfen mit 118°-Spitze, die
  Senkung mit dem Spitzenwinkel (60°) zum Körper-Ø; Gewindebohrer mit
  Zähnen nach der Steigung und Anschnitt, links mit Linkswendel;
  Drehwerkzeug: Hauptschneide im Einstellwinkel zur Vorschubrichtung,
  Plattenwinkel an der Spitze, links gespiegelt, neutral mittig.
- Bild: mittig eingepasst; Symbol in der Auswahl zeigt nur das schneidende
  Ende (sonst wäre ein langer Fräser ein Strich).

### TEST
- `test_werkzeugform` (26 Arten, spitz/flach, Kugel, Spiegelbild,
  Einstellwinkel, Wendel, Tastkugel, gestrichelt) in 1.1.3 und im
  Wochen-Build; `szenario_werkzeugbilder` (Übersicht aller Arten,
  Auswahl mit Bildern, Drehwerkzeug links), `szenario_werkzeugverwaltung`,
  `szenario_schnittwerte` in 1.1.3. Die Übersicht angesehen: jede Art
  erkennbar.
- `szenario_zoll` scheiterte einmal an „Maschine verfahren“: eine feste
  Wartezeit im Szenario – eigener Patch (P-2026-09-26-57).

### NEXT
- Szenarien warten auf die Beispielmaschine statt fester Zeit; dann
  Stufe C4: Einsätze je Art.

## P-2026-09-26-55 werkzeugarten-tabelle

### EINGELESEN
- Spezifikation Werkzeugarten (P-2026-09-26-53), Abschnitte 2–4 und 8
  (Stufe 2): alle 26 Arten wählbar, gegliedert, je Art ihre Felder.
- Manuel während des Bauens: „Gewindebohrer haben keine Schneidenanzahl.“
- `camaddon/werkzeuge.py`, `camaddon/gui_werkzeuge.py`,
  `camaddon/gui_werkzeugbild.py`, `camaddon/uebergabe_werkzeuge.py`.

### DATEIEN
- `camaddon/werkzeuge.py` (26 Arten, `ARTDATEN`, neue Felder, Zeile und
  Name je Art, Steigung in inch als Gänge je Zoll)
- `camaddon/gui_werkzeuge.py` (Felder je Art, Auswahl gegliedert)
- `camaddon/gui_werkzeugbild.py` (kein Bild ohne Durchmesser)
- `camaddon/uebergabe_werkzeuge.py` (Arten ohne CAM-Form bleiben draußen)
- `translations/de.json`, `translations/en.json`
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `docs/spezifikation_werkzeugarten.md`
- `tests/test_werkzeuge.py`, `tests/test_uebergabe_werkzeuge.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Art aufklappen: 26 Arten unter „Fräsen“, „Bohren“,
„Drehen“, „Antasten“; „Gewindebohrer rechts“ zeigt Durchmesser und
Steigung fett, Gewindelänge, Gesamtlänge, Schaft-Ø, Schneidstoff – keine
Schneidenzahl, keinen Eckradius.

### DONE
- `ARTDATEN`: je Art Gruppe, Felder in Anzeigereihenfolge, Pflichtfelder,
  übliche Winkel, Beispiele metrisch und in runden Zollmaßen (`_zoll`).
  Neue Felder: Spitzen-Ø, Kegel-, Flanken-, Einstell-, Plattenwinkel,
  Hals-Ø und -länge, Profilradius, Steigung, Schneidenbreite, Stechtiefe,
  Ausführung. Beschriftung je Art (Zapfen-Ø, Gewindelänge, Eckenradius …).
- Dialog: alle Felder einmal angelegt, `_felder_anordnen()` stellt die der
  Art zu zweit je Reihe auf; leere Winkel zeigen grau den üblichen
  („üblich: 60“ beim Zentrierbohrer). Werte in Feldern, die die neue Art
  nicht hat, bleiben erhalten (Spezifikation, Abschnitt 4 angepasst).
- Gefunden: Hängt eine Beschriftung erst im schon gezeigten Dialog ein,
  setzt FreeCADs Stylesheet (70 KB) ihre Schrift zurück – fett jetzt nach
  dem Einhängen.
- Liste: „T4  Gewindebohrer rechts Ø 10 · P 1.5 · VHM“,
  „T9  Drehwerkzeug r 0.8 · VHM“; in inch „13 Gg/Zoll“.
- „An CAM übergeben“ lässt Arten ohne CAM-Form (noch alle neuen) draußen
  und nennt sie; die Zuordnung kommt mit Stufe 5.
- Bilder: noch die bisherigen; Drehwerkzeuge ohne Bild – Stufe 3 (Manuel:
  „die Grafik bei den Drehwerkzeugen ist nicht korrekt, auch der
  Zentrierbohrer ist eher spitz“).

### TEST
- `test_werkzeuge` (Tabelle, Zeilen, Namen, neue Felder, Gänge je Zoll),
  `test_uebergabe_werkzeuge`, `test_werkzeuge_aus_cam`,
  `test_job_schnittwerte`, `test_sprache`, `test_hilfe` in 1.1.3 und im
  Wochen-Build; Szenarien `werkzeugverwaltung` (neu: Auswahl, Gewindebohrer,
  Zentrierbohrer, Drehwerkzeug, zurück), `schnittwerte`, `zoll`, `an_cam`,
  `aus_cam`, `schruppwerte` in 1.1.3.

### NEXT
- Stufe C3: Bilder aller Arten.

## P-2026-09-26-54 kugelfraeser

### EINGELESEN
- Spezifikation Werkzeugarten (P-2026-09-26-53), Abschnitte 1, 7 und 8
  (Stufe 1): Das heutige „Radiusfräser“ ist ein Kugelfräser; ein
  Radienfräser ist eine andere Art.
- `camaddon/werkzeuge.py`, `gui_werkzeugbild.py`, `uebergabe_werkzeuge.py`,
  `werkzeuge_aus_cam.py`, Hilfe „Werkzeuge“.

### DATEIEN
- `camaddon/werkzeuge.py` (`KUGELFRAESER`, `ALTE_ARTEN`)
- `camaddon/gui_werkzeugbild.py`, `camaddon/uebergabe_werkzeuge.py`,
  `camaddon/werkzeuge_aus_cam.py`
- `translations/de.json`, `translations/en.json` (`wv.art.kugelfraeser`)
- `help/de/werkzeuge.html`, `docs/spezifikation_werkzeugverwaltung.md`
- `tests/test_werkzeuge.py`, `tests/test_werkzeuge_aus_cam.py`,
  `tests/test_schruppwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In der Auswahl „Art“ steht „Kugelfräser“ statt „Radiusfräser“; ein
gespeicherter Radiusfräser öffnet sich als Kugelfräser und wird als
`kugelfraeser` gespeichert.

### DONE
- Gespeichertes Wort `kugelfraeser`; `ALTE_ARTEN` stellt `radiusfraeser`
  beim Laden um. In CAM bleibt es die Form „ballend“, aus CAM wird
  „ballend“ ein Kugelfräser. Englisch hieß er schon „Ball end mill“.

### TEST
- `test_werkzeuge` (neu: alte Datei mit `radiusfraeser`),
  `test_werkzeuge_aus_cam`, `test_schruppwerte`, `test_uebergabe_werkzeuge`,
  `test_sprache`, `test_hilfe` in 1.1.3 und im Wochen-Build;
  `szenario_werkzeugverwaltung` (1.1.3).

### NEXT
- Stufe C2: die Arten als Tabelle im Code, alle 26 wählbar.

## P-2026-09-26-53 spezifikation-werkzeugarten

### EINGELESEN
- Manuel (2026-09-26): „ne, mach mal Werkzeugarten weiter“ – die
  Beispielmaschinen zur Auswahl warten (fast fertig, im Stash).
- Plan Punkt 10 in `docs/STATUS_SNAPSHOT.md` (26 Arten aus Manuels
  InventorCAM-Screenshot, P-2026-09-26-31), `camaddon/werkzeuge.py`,
  `gui_werkzeuge.py`, `gui_werkzeugbild.py`, `schnittdaten.py`,
  `uebergabe_werkzeuge.py`, `werkzeuge_aus_cam.py`; die Werkzeugformen von
  FreeCAD-CAM (`Path/Tool/shape/models`, in 1.1.3 und im Wochen-Build
  dieselben 15).

### DATEIEN
- `docs/spezifikation_werkzeugarten.md` (neu)
- `docs/STATUS_SNAPSHOT.md` (Punkt 10), `CHATSTART.md` (Lesekarte)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation nennt alle 26 Arten mit Maßen, CAM-Form, Einsätzen,
Beispielwerten und die Stufen, in denen sie gebaut werden.

### DONE
- Spezifikation mit neun Abschnitten; Entscheidungen zur Besprechung in
  Abschnitt 9 (u. a. Gewindebohrer rechts/links als zwei Arten, Bohrstange
  und Ausspindelwerkzeug getrennt, Nutenfräser = Scheibenfräser,
  Konikfräser mit Kugel an der Spitze, Drehwerkzeuge ohne Schnittwerte).

### TEST
- Nur Doku.

### NEXT
- Stufe C1: Kugelfräser statt „Radiusfräser“.

## P-2026-09-26-52 revolverplatz-nur-am-revolver

### EINGELESEN
- Manuel (2026-09-26, Screenshot: Beispiel-Fräsmaschine, „+ Werkzeugaufnahme“,
  im Kasten darunter „Revolverplatz: P10“): „hier ist noch kein Revolver zu
  sehen … also wieso Revolverplatz? … keine Ahnung, wie man das sinnvoll
  macht.“
- `camaddon/gui_details.py` (`zeige_aufnahme`, `_platzfeld`),
  `camaddon/gui_maschine.py` (`_details_zeigen`), Spezifikation W-001,
  Abschnitt 7a (Plätze = Werkzeugaufnahmen im Glied des Revolvers).

### DATEIEN
- `camaddon/gui_details.py`, `camaddon/gui_maschine.py`
- `help/de/aufnahmen.html`, `help/en/aufnahmen.html`
- `tests/gui/szenario_maschine_bearbeiten.py`,
  `tests/gui/szenario_beispielmaschine.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Das Feld „Revolverplatz“ steht nur bei einer Werkzeugaufnahme, deren LCS auf
einem Revolver sitzt – im Glied, das ein Gelenk mit der Betriebsart
„Revolver“ dreht. An der Spindel einer Fräse gibt es das Feld nicht mehr.

### DONE
- `MaschinenPanel._auf_revolver()` prüft das Glied des LCS gegen die
  Revolverachsen; `DetailKasten.zeige_aufnahme(…, auf_revolver)` legt das
  Feld nur dann an. Genau diese Aufnahmen zählt das Addon auch als Plätze
  (`m.plaetze`) – Feld und Zählung passen jetzt zusammen.
- Hilfe „Aufnahmen“: Das Feld gibt es nur auf dem Revolver.
- Das „P10“ im Screenshot war sehr wahrscheinlich das Mausrad über dem Feld;
  ohne Revolver ist das Feld jetzt ganz weg.

### TEST
- `szenario_maschine_bearbeiten` (1.1.3): P3 zeigt „Revolverplatz: P3“, das
  Futter hat nur Name und Koordinatensystem. `szenario_beispielmaschine`:
  Die Spindel der Beispiel-Fräse hat drei Felder, kein Revolverplatz.

### NEXT
- Beispielmaschinen zur Auswahl (Punkt 7b).

## P-2026-09-26-51 version-0-16-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.15.0: Maßsystem inch (P-2026-09-26-48), Knopf „Nach Updates suchen“
  (P-2026-09-26-50).

### DATEIEN
- `package.xml` (0.16.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.16.0.

### DONE
- Version 0.15.0 → 0.16.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann die Beispielmaschinen zur Auswahl (Punkt 7b).

## P-2026-09-26-50 update-knopf

### EINGELESEN
- Manuel (2026-09-26): „Update-Prüfung nicht bei Start … wenn das jedes
  Addon machen würde bei Start prüfen, dann würde man am Anfang bei 10
  Addons 10 Updates laden müssen … lieber ein Update-Knopf, dass man
  auswählen kann ‚ok, check nach Update‘ … und dann updaten lassen, wenn man
  auf den Knopf drückt“.
- Plan in `docs/STATUS_SNAPSHOT.md` (Punkt 7c, neu).

### DATEIEN
- `camaddon/gui_aktualisierung.py` (Befehl `BefehlUpdateSuchen`,
  `von_hand_suchen()`, Suche beim Start ab Werk aus)
- `camaddon/gui_start.py` (Befehl in der Werkzeugleiste)
- `resources/icons/update.svg` (neu)
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_update.py`
- `README.md`, `docs/aufbau.md`, `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beim Start von FreeCAD sucht das Addon nicht mehr (ab Werk). Der Knopf
„Nach Updates suchen“ in der Werkzeugleiste sucht im Hintergrund, zeigt
in der Statusleiste „suche nach Updates …“ und sagt danach in jedem Fall,
was herauskam – bei einer neuen Version mit „Jetzt aktualisieren“. In den
Einstellungen lässt sich die Suche beim Start einschalten.

### DONE
- Knopf „Nach Updates suchen“ (Befehl `CamAddon_UpdateSuchen`, Symbol:
  Pfeil im Kreis) in der Werkzeugleiste des Addons; solange eine Suche
  läuft, ist er grau. Derselbe Weg wie „Jetzt nach Updates suchen“ in den
  Einstellungen.
- Suche beim Start ab Werk aus. Neuer Schlüssel `UpdateSucheBeimStart`:
  Unter dem alten (`UpdateBeimStart`) stand bei allen, die die Einstellungen
  einmal gespeichert haben, „an“ – sonst hätte der Wechsel sie nicht
  erreicht.
- README (beide Installationswege), Tooltip und Aufbau beschreiben den
  Knopf.

### TEST
- `scripts/oberflaeche_testen.sh tests/gui/szenario_update.py` (1.1.3):
  Befehl angemeldet; `von_hand_suchen()` findet 9.9.0 im Test-Repo, der
  Hinweis erscheint, „Jetzt aktualisieren“ holt sie; „Beim Start suchen“
  ab Werk aus, an und aus wird gespeichert. `szenario_erster_start`,
  `test_sprache`, `test_aktualisierung`, `test_hilfe` grün. Voller Lauf mit
  dem Versionssprung.

### NEXT
- Version 0.16.0, voller Lauf, Push; dann die Beispielmaschinen zur
  Auswahl (Punkt 7b).

## P-2026-09-26-49 plan-beispielmaschinen-und-update

### EINGELESEN
- Manuel (2026-09-26, nach dem Laden der Beispielmaschine): „ich hätte
  gerne, wenn ich Beispielmaschine laden [drücke,] eine Auswahl von
  Drehbank CLX-mäßig mit Y-Achse, Schrägbett und am Revolver zwei
  Werkzeuge zum Fräsen, eins in Z-Richtung bearbeitend, eins 90 Grad zur
  Z-Richtung … 3-Achs-Fräse, 5-Achs-Fräse Tisch/Tisch (Achsen A/B),
  5-Achs-Fräse Kopf/Kopf auch A/B und … Kopf/Tisch … die üblichen Sorten“.
- Manuel: „Update-Prüfung nicht bei Start … wenn das jedes Addon machen
  würde … bei 10 Addons 10 Updates laden … lieber ein Update-Knopf, dass man
  auswählen kann ‚ok, check nach Update‘ … und dann updaten lassen, wenn man
  auf den Knopf drückt“.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan: Punkt 7b)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Plan nennt die Auswahl der Beispielmaschinen mit Ort in der
Reihenfolge; der Update-Knopf folgt als eigener Patch.

### DONE
- Punkt 7b: Beispielmaschinen zur Auswahl (Schrägbett-Drehmaschine mit
  Y-Achse und zwei angetriebenen Werkzeugen, 3-Achs, 5-Achs Tisch/Tisch
  A/C, Kopf/Kopf A/B, Kopf/Tisch B/C). Achsnamen wie üblich – der Rundtisch
  auf der Wiege heißt fast immer C; umbenennen geht in „Maschine
  bearbeiten“.

### TEST
- Nur Doku.

### NEXT
- Update-Knopf statt Suche beim Start; dann die Beispielmaschinen.

## P-2026-09-26-48 masssystem-inch

### EINGELESEN
- Manuel (2026-09-26): „es sollte bei Installation auswählbar sein …
  welche Einheiten verwendet werden (Standard metrisch, aber inch und so
  sollten möglich sein) … mit Beispielzahlen … und auch in den
  Einstellungen des Addons wieder ändern … bei den Werkzeugen direkt in
  inch bzw. mm umrechnen … und einen Schalter einbauen, wo man zwischen
  inch und mm switcht“.
- Plan im Snapshot (Stufe B, Punkte 8 und 9); alle Dialoge mit Zahlen;
  60 Texte mit festen Einheiten; FreeCADs Einheitensysteme
  (`FreeCAD.Units.listSchemas()`: Imperial, ImperialDecimal,
  ImperialBuilding, ImperialCivil = inch).

### DATEIEN
- `camaddon/einheiten.py` (Maßsystem, Größen mit Umrechnung und Stellen,
  `runden`/`abrunden`, Vergleichsvolumen, Einheiten-Platzhalter)
- `camaddon/sprache.py` (`tr()` setzt `{e_laenge}` … selbst ein)
- `camaddon/gui_zahlen.py` (`groesse_zeigen`, `groesse_lesen`,
  `groesse_fest`), `camaddon/gui_teile.py` (`mit_einheit` merkt die
  Einheit)
- `camaddon/gui_sprachwahl.py` (Maßsystem beim ersten Start und in den
  Einstellungen, mit Beispielen)
- `camaddon/gui_werkzeuge.py` (Umschalter mm/inch, Felder, Platzhalter,
  Hinweise), `camaddon/werkzeuge.py` (Listenzeile, Beispielname,
  Beispielwerte in Zoll, Vorlage), `camaddon/gui_werkzeugbild.py`
- `camaddon/gui_schnittwerte.py` (Tabelle, Köpfe, Eingriff, Ausgleich)
- `camaddon/schruppwerte.py`, `camaddon/gui_schruppwerte.py` (Planer,
  Beispiele in Zoll, Übernehmen gerundet in der gezeigten Einheit)
- `camaddon/schnittdaten.py`, `camaddon/gui_strategie.py`
  (Strategievergleich, „Zeit für 5 in³“)
- `camaddon/gui_job_schnittwerte.py`, `camaddon/gui_details.py`,
  `camaddon/gui_verfahren.py`, `camaddon/export.py`
- `translations/de.json`, `translations/en.json` (Einheiten als
  Platzhalter; neue Texte `zahlen.metrisch|zoll`,
  `einstellungen.zahlen.masssystem`, `wv.masssystem.tooltip`,
  `einheit.je_umdrehung`)
- `help/de|en/werkzeuge.html`, `help/de|en/schnittwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 28),
  `docs/aufbau.md`, `docs/STATUS_SNAPSHOT.md`
- `tests/test_einheiten.py`, `tests/test_werkzeuge.py`,
  `tests/test_schruppwerte.py`, `tests/gui/szenario_zoll.py` (neu)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → rechts neben „Werkstoffe…“ „inch“ wählen: Die Felder
zeigen „in“, der Ø-12-Fräser „0.4724“; „Neu“ → Ø 0.5, Schneide 1, Liste
„Ø 0.5“. Schnittwerte: Köpfe ae/ap in, vc SFM, fz in, vf ipm, Q in³/min;
„400“ in vc und „0.002“ in fz → n und vf in ipm. „Schruppwerte planen…“ →
vc in SFM, Vorschlag in ipm. Zurück auf „mm“ → alles wieder in mm, ½" als
12.7. Bearbeiten → Einstellungen → CAM-Addon → Zahlen: „Maßsystem“ ändert
es ebenso.

### DONE
- Maßsystem wählbar (erster Start, Einstellungen, Umschalter in der
  Werkzeugverwaltung), vorbelegt aus FreeCAD; wer den Dialog schon
  beantwortet hat, wird nicht noch einmal gefragt.
- Überall umgerechnet: Werkzeugverwaltung, Schnittwerte, Eingriff,
  Planer, Strategievergleich, „Schnittwerte in den Job“, Maschine
  (Eilgang, Höchstvorschub, Verfahren, Bericht der Übergabe).
- Gespeichert und an CAM übergeben wird metrisch; gerundet in der
  gezeigten Einheit, damit ½" 0.5 in bleibt.

### TEST
- Alle Prüfungen ohne Oberfläche in 1.1.3 und 26.3.0 grün (neu:
  Maßsystem, Umrechnung, Runden, Texte in Zoll, Listenzeile und
  Beispielwerte in Zoll). `szenario_zoll` in 1.1.3 grün, Screenshots
  angesehen (Werkzeugverwaltung und Planer in Zoll, zurück auf mm,
  Verfahren in inch). Alle Szenarien in 1.1.3; voller Lauf vor dem Push.

### NEXT
- Version 0.16.0, voller Lauf, Push; dann Stufe C (Spezifikation der
  Werkzeugarten zuerst).

## P-2026-09-26-47 tausenderpunkt

### EINGELESEN
- Voller Lauf vor dem Push von 0.15.0: `szenario_felder` rot in beiden
  Versionen – „35.000“ getippt ergab 35 statt 35000. Seit
  P-2026-09-26-45 nehmen die Felder Punkt und Komma als Dezimalzeichen;
  B-004 (P-2026-09-25-31): Auf Deutsch ist „35.000“ fünfunddreißigtausend.
- Im selben Lauf `szenario_erster_start` rot in 1.1.3 („user.cfg“ fehlt):
  FreeCAD meldete schon beim Start „Failed to access file for writing“ –
  genau in den zwei Minuten, in denen nebenher eigene FreeCAD-Versuche
  liefen; einzeln und im nächsten Lauf grün. Künftig keine FreeCAD-Versuche
  neben einem vollen Lauf.

### DATEIEN
- `camaddon/einheiten.py` (`zahl_aus_text` mit dem eingestellten
  Dezimalzeichen)
- `camaddon/gui_zahlen.py` (`zahl_lesen` gibt es mit)
- `tests/test_einheiten.py`, `tests/gui/szenario_felder.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Mit Komma als Dezimalzeichen: „35.000“ im Eilgang ergibt 35000, „2.5“ in
der Beschleunigung 2,5, „0.125“ ergibt 0,125. Mit Punkt: „1,500“ ergibt
1500, „12,5“ ergibt 12,5.

### DONE
- Das eingestellte Dezimalzeichen trennt immer die Nachkommastellen; das
  andere auch – außer die Zahl ist mit Tausendertrennzeichen geschrieben
  (1 bis 3 Ziffern, nicht 0, dann Gruppen zu drei).

### TEST
- `test_einheiten.py` in 1.1.3 und 26.3.0 grün; `szenario_felder`,
  `szenario_erster_start` in 1.1.3 grün. Voller Lauf vor dem Push.

### NEXT
- Push 0.15.0; dann B2 (Maßsystem inch).

## P-2026-09-26-46 version-0-15-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.14.0: Dezimalzeichen wählbar, Eingabe mit Punkt oder Komma
  (P-2026-09-26-45).

### DATEIEN
- `package.xml` (0.15.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.15.0.

### DONE
- Version 0.14.0 → 0.15.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann B2 (Maßsystem inch).

## P-2026-09-26-45 dezimalzeichen

### EINGELESEN
- Manuel (2026-09-26): „die meisten CAM-Programme oder Maschinen arbeiten
  eher mit . … wie ist das in FreeCAD selbst gelöst? … oder auswählbar“;
  später: „es sollte bei Installation auswählbar sein … welche Trennzeichen
  genutzt werden … mit Beispielzahlen … und auch in den Einstellungen des
  Addons wieder ändern kann“.
- Plan im Snapshot (Stufe B, Punkte 8 und 9), `camaddon/gui_zahlen.py`
  (B-004: ohne Tausenderpunkte), `camaddon/gui_sprachwahl.py`.
- FreeCAD 1.1.3 im frischen Profil: Wer schon beim Laden der Oberfläche
  einen Parameter setzt, verhindert, dass `FreeCAD.saveParameter()` die
  `user.cfg` anlegt – deshalb wählen die Szenarien das Komma im Dialog,
  statt es im Testgerüst vorzugeben.

### DATEIEN
- `camaddon/einheiten.py` (neu: gewähltes Dezimalzeichen, `zahl_aus_text`
  mit Punkt oder Komma)
- `camaddon/gui_zahlen.py` (Zahlenformat nach der Wahl, sonst FreeCADs;
  Prüfer nimmt Punkt und Komma; `dezimalzeichen()`)
- `camaddon/gui_sprachwahl.py` (Dialog beim ersten Start und
  Einstellungsseite: Dezimalzeichen mit Beispielzahlen; wer die Sprache
  schon gewählt hat, wird einmal nach dem Dezimalzeichen gefragt)
- `translations/de.json`, `translations/en.json` (`zahlen.*`,
  `einstellungen.zahlen.*`, Titel „Sprache und Zahlen“)
- `help/de|en/werkzeuge.html` (Zahlen mit Punkt oder Komma)
- `docs/aufbau.md`, `docs/STATUS_SNAPSHOT.md`
- `tests/test_einheiten.py` (neu), `tests/gui/szenario_erster_start.py`,
  `tests/gui/szenario_werkzeugverwaltung.py` (Eckradius mit Punkt
  getippt), alle Szenarien mit Sprachwahl (wählen das Komma)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update fragt das Addon beim nächsten Start einmal „Und welches
Dezimalzeichen sollen die Zahlen haben?“ – vorgewählt ist das von FreeCAD
(bei Manuel das Komma), zur Wahl „Komma: 12,5 mm · fz 0,05 mm“ und „Punkt:
12.5 mm · fz 0.05 mm“. Mit „Punkt“ zeigt die Werkzeugverwaltung „Ø 10.5“
und „0.05“. In jedem Zahlenfeld darf man „10,5“ oder „10.5“ tippen.
Bearbeiten → Einstellungen → CAM-Addon → „Zahlen“ ändert es wieder.

### DONE
- Dezimalzeichen wählbar beim ersten Start und in den Einstellungen,
  vorbelegt aus FreeCADs Zahlenformat; ohne Wahl gilt FreeCADs.
- Eingaben nehmen immer Punkt und Komma; weiterhin keine
  Tausendertrennzeichen und keine Zahlen unter 0 in den Feldern.
- Wer die Sprache schon gewählt hat (Manuel), sieht den Dialog noch
  einmal – mit seiner Sprache vorgewählt.

### TEST
- `test_einheiten.py`, `test_sprache.py`, `test_hilfe.py` in 1.1.3 und
  26.3.0 grün; `szenario_erster_start` (Titel, Beispielzahlen,
  `user.cfg`, Einstellungsseite: Punkt und Komma),
  `szenario_werkzeugverwaltung` (Eckradius „0.5“ bei Komma),
  `szenario_schnittwerte` in 1.1.3 grün, Screenshots angesehen. Voller
  Lauf vor dem Push.

### NEXT
- B2: Maßsystem inch mit Umrechnung überall.

## P-2026-09-26-44 version-0-14-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.13.0: Warngrenze im Planer (P-2026-09-26-40), Eingriffsbild
  beschriftet (-41), ae/ap in mm oder % von D (-42), Spitzenwinkel des
  Bohrers (-43). Stufe A des Plans ist damit fertig.

### DATEIEN
- `package.xml` (0.14.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.14.0.

### DONE
- Version 0.13.0 → 0.14.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann Stufe B (Maßsystem und Dezimaltrennzeichen).

## P-2026-09-26-43 bohrer-spitzenwinkel

### EINGELESEN
- Manuel (2026-09-26, Screenshot eines Bohrers in der
  Werkzeugverwaltung): „bei einem Bohrer gibt's … was es gibt, ist ein
  Spitzenwinkel, der ist vergessen worden“; ob es eine Schneidenzahl
  gibt, wusste er nicht – Plan: sie bleibt (f je Umdrehung).
- Plan im Snapshot (Stufe A Punkt 6); bisher fest 118° in
  `uebergabe_werkzeuge.py` (TipAngle) und `gui_werkzeugbild.py`.

### DATEIEN
- `camaddon/werkzeuge.py` (`Werkzeug.spitzenwinkel`, gespeichert;
  `SPITZENWINKEL_BOHRER`, `spitzenwinkel_fuer_cam`)
- `camaddon/gui_werkzeuge.py` (Feld nur beim Bohrer, an der Stelle des
  Eintauchwinkels; grau „üblich: 118“)
- `camaddon/gui_werkzeugbild.py` (Spitze mit dem Winkel des Werkzeugs)
- `camaddon/uebergabe_werkzeuge.py` (TipAngle aus dem Werkzeug)
- `camaddon/werkzeuge_aus_cam.py` (TipAngle wird gelesen)
- `translations/de.json`, `translations/en.json` (`wv.spitzenwinkel*`)
- `help/de|en/werkzeuge.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 27)
- `docs/STATUS_SNAPSHOT.md` (Punkt 6 fertig, Stufe A komplett)
- `tests/test_werkzeuge.py`, `tests/test_uebergabe_werkzeuge.py`,
  `tests/test_werkzeuge_aus_cam.py`, `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Neu“ → Art „Bohrer“: Statt „Eintauchwinkel“ steht
„Spitzenwinkel“, leer grau „üblich: 118“. „130“ eintragen → die Spitze im
Bild wird stumpfer. „Speichern und an CAM übergeben“ → im CAM-Werkzeug
steht der Spitzenwinkel 130°.

### DONE
- Spitzenwinkel je Bohrer (0 = üblich 118°), gespeichert, begrenzt auf
  0 … 180°; ins Bild, als TipAngle an CAM, aus CAM gelesen.
- Das Feld teilt sich die Stelle mit dem Eintauchwinkel – je nach Art ist
  eins von beiden zu sehen, ohne Lücke.

### TEST
- `test_werkzeuge.py`, `test_uebergabe_werkzeuge.py` (TipAngle 130°),
  `test_werkzeuge_aus_cam.py` (Winkel des Beispielbohrers gelesen),
  `test_sprache.py` in 1.1.3 und 26.3.0 grün; `test_hilfe.py` grün;
  `szenario_schnittwerte`, `szenario_werkzeugverwaltung` in 1.1.3 grün,
  Screenshot angesehen. Voller Lauf vor dem Push.

### NEXT
- Version 0.14.0 (A3–A6), voller Lauf, Push; dann Stufe B.

## P-2026-09-26-42 zustellung-in-prozent

### EINGELESEN
- Manuel (2026-09-26, Screenshot der Schnittwerte): „ich hätte hier gerne
  einen Switch zwischen %-Angabe und mm-Angabe … dass man beides
  eintragen kann“. Plan: ein Umschalter über der Tabelle, intern mm, Wahl
  gemerkt (Stufe A Punkt 5).
- `camaddon/gui_schnittwerte.py` (Tabelle, Kopf, Eingabe).

### DATEIEN
- `camaddon/gui_schnittwerte.py` (Auswahl „ae, ap in mm / in % von D“,
  Köpfe, Anzeige, Eingabe in % → mm, gemerkt als
  `SchnittwerteInProzent`)
- `translations/de.json`, `translations/en.json` (`wv.zustellung.*`)
- `help/de|en/schnittwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 26)
- `docs/STATUS_SNAPSHOT.md` (Punkt 5 fertig)
- `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Ø-12-Fräser mit „Schruppen dynamisch“ ae 1,2 / ap 25
→ rechts über der Tabelle „ae, ap in % von D“ wählen → die Köpfe heißen
„ae % D“ und „ap % D“, die Zeile zeigt 10 und 208,3. „20“ ins ae tippen →
darunter „ae 2,4 mm = 20 % von D“. Zurück auf „ae, ap in mm“ → 2,4. Beim
nächsten Öffnen steht die zuletzt gewählte Einheit.

### DONE
- Eine Auswahl für beide Spalten; Prozent mit einer Nachkommastelle;
  gespeichert immer in mm; ohne Durchmesser mm (Auswahl gesperrt), beim
  Bohrer ausgeblendet.
- Nebenbei: Eine unlesbare Eingabe im f-Feld des Bohrers teilte den alten
  Wert noch einmal durch die Schneidenzahl – jetzt bleibt er, wie er war.

### TEST
- `szenario_schnittwerte` in 1.1.3 grün, Screenshot angesehen (Köpfe
  „% D“, 100/25 und 20/208,3); `test_sprache.py`, `test_hilfe.py` grün.
  Voller Lauf mit dem nächsten Push.

### NEXT
- A6: Spitzenwinkel des Bohrers.

## P-2026-09-26-41 eingriffsbild-beschriftet

### EINGELESEN
- Manuel (2026-09-26, Screenshot des Eingriffsbilds unter den
  Schnittwerten): „das Bild find ich gut … allerdings weiß keiner, was ae
  und ap ist … schreib's doch drüber, und der Text ist ziemlich lang, den
  sollte man vll auf zwei Zeilen setzen oder sowas wie Links: ae … Rechts:
  ap …“.
- Plan im Snapshot (Stufe A Punkt 4), `camaddon/gui_eingriff.py` (Bild ohne
  Text, Arbeitsregeln Abschnitt 8), `camaddon/gui_schnittwerte.py`.

### DATEIEN
- `camaddon/gui_schnittwerte.py` (Überschriften über den Bildhälften,
  je Größe eine Zeile)
- `translations/de.json`, `translations/en.json` (neu
  `wv.eingriff.titel.ae|ap`, `wv.eingriff.von_oben|von_der_seite`,
  `wv.eingriff.ae`, `wv.eingriff.ap`, `wv.eingriff.ap_schneide`; entfallen
  `wv.eingriff.ae_ap`, `wv.eingriff.ae_ap_schneide`)
- `help/de|en/schnittwerte.html`
- `docs/STATUS_SNAPSHOT.md` (Punkt 4 fertig)
- `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Fräser → Zeile „Schruppen dynamisch“ wählen: Über der
linken Bildhälfte steht „ae – seitliche Zustellung“, darunter grau „von
oben“; über der rechten „ap – Zustelltiefe“, grau „von der Seite“. Rechts
daneben je eine Zeile „ae 1,2 mm = 10 % von D“, „ap 25 mm = 2,1 × D (96 %
der Schneide)“, dann Eingriff und Spandicke.

### DONE
- Überschriften als Beschriftungen über dem Bild – das Bild selbst bleibt
  ohne Text. Die Ansicht („von oben“, „von der Seite“) grau in einer
  eigenen Zeile, damit sie nicht mitten in der Klammer umbricht.
- Die Werte: erst ae, dann ap, dann der Eingriffswinkel, dann die
  Spandicke – je eine Zeile.

### TEST
- `szenario_schnittwerte` in 1.1.3 grün, Screenshot angesehen;
  `test_sprache.py`, `test_hilfe.py` grün. Voller Lauf mit dem nächsten
  Push.

### NEXT
- A5: ae und ap wahlweise in mm oder % von D.

## P-2026-09-26-40 planer-warngrenze

### EINGELESEN
- Manuel (2026-09-26, Screenshot des Planers): „wer sagt was von 10 % ??
  … sagen ‚hey das sind mehr als deine Warngrenze‘ … welche man irgendwo
  mit eintragen kann“; dann: „ab 10 % ae bei voller Schneidenlänge rote
  Warnung, somit können wir die 10 % lassen, aber auswählbar sollte es
  schon sein“; „10 % ae bei HSM ist ok, egal wie viel Schneiden“.
- Plan im Snapshot (Stufe A Punkt 3), Spezifikation W-002 (Entscheidung
  14), `camaddon/schruppwerte.py`, `camaddon/gui_schruppwerte.py`.

### DATEIEN
- `camaddon/werkzeuge.py` (`Werkzeug.ae_warngrenze`, gespeichert; ältere
  Dateien: 10 %)
- `camaddon/schruppwerte.py` (`AE_GRENZE` = Vorgabe am Werkzeug)
- `camaddon/gui_schruppwerte.py` (Feld aus dem Werkzeug und zurück, Zeilen
  darüber rot, roter Satz unter der Tabelle; nicht mehr in den
  Einstellungen gemerkt)
- `translations/de.json`, `translations/en.json` (`sp.ae_grenze*`,
  `sp.hinweis.ueber_ae`, `sp.grund.ae`, neu `sp.warnung.ueber_ae`)
- `help/de|en/schruppwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 14, Stufe 3)
- `docs/STATUS_SNAPSHOT.md` (Punkt 3 fertig)
- `tests/test_werkzeuge.py`, `tests/gui/szenario_schruppwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Ø-12-Fräser → „Schruppwerte planen…“: Das Feld
heißt „Warngrenze ae“ (10 % von D). Die Zeilen über 10 % sind rot mit
„mehr als deine Warngrenze (10 % von D)“; eine anklicken → darunter ein
roter Satz, „Als Einsatz übernehmen“ bleibt bedienbar. Warngrenze auf 8
ändern, Planer schließen, OK → beim nächsten Öffnen steht bei diesem
Werkzeug 8, bei anderen 10.

### DONE
- Warngrenze je Werkzeug (Vorgabe 10 %, 0 = keine), gespeichert in der
  Werkzeugdatei; der Planer liest und schreibt sie (auch nach Abbrechen,
  wie die Maschinenwerte).
- Zeilen über der Warngrenze rot und wählbar; über der Spindelleistung
  weiter grau. Der Vorschlag bleibt unter der Warngrenze; der Satz dazu
  sagt, dass die roten Zeilen wählbar sind. Die Spalte „ae % D“ gab es
  schon.

### TEST
- `test_werkzeuge.py` (Vorgabe, Speichern, alte Datei, 0 und Begrenzung),
  `test_schruppwerte.py`, `test_sprache.py`, `test_hilfe.py` in 1.1.3
  grün; `szenario_schruppwerte` in 1.1.3 grün, Screenshot angesehen (rote
  Zeile gewählt, roter Satz). Voller Lauf mit dem nächsten Push.

### NEXT
- A4 Eingriffsbild beschriften.

## P-2026-09-26-39 version-0-13-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.12.0: Beispielwerte für neue Werkzeuge und im Planer
  (P-2026-09-26-37), Beispielmaschine (-38).

### DATEIEN
- `package.xml` (0.13.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.13.0.

### DONE
- Version 0.12.0 → 0.13.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann A3 Warngrenze.

## P-2026-09-26-38 beispielmaschine

### EINGELESEN
- Manuel (2026-09-26, Screenshots der Meldung „Hier gibt es noch keine
  Baugruppe“ in „Maschine bearbeiten“ und „Maschine verfahren“): „noch
  einen Knopf ‚Beispiel Maschine laden‘ … wenn er dafür ne Maschine bauen
  muss ist das eine große Hürde … gib dem Benutzer Beispiele wo er sehen
  kann ‚ah so geht das‘“.
- `tests/beispielmaschinen.py` (Baukasten), `camaddon/gui_maschine.py`,
  `camaddon/gui_verfahren.py`, `camaddon/maschine.py`,
  `camaddon/verfahren.py`; FreeCADs `JointObject.py` (1.1.3): Jede
  Änderung an Offset1/Offset2 löst vorab (`preSolve`/`matchJCS`) und
  verschiebt dabei Teile.

### DATEIEN
- `camaddon/beispielmaschine.py` (neu: Baukasten aus den Prüfungen,
  `gelenk_wie_gebaut`, `fraesmaschine`, `lade`)
- `camaddon/gui_maschine.py` (`beispiel_gewuenscht`: Meldung mit Knopf)
- `camaddon/gui_verfahren.py`
- `translations/de.json`, `translations/en.json` (`beispiel.*`,
  `dialog.beispielmaschine*`, Meldung ergänzt)
- `help/de|en/achsen.html`, `help/de|en/verfahren.html`
- `docs/spezifikation_maschine_aus_baugruppe.md` (Entschieden)
- `docs/STATUS_SNAPSHOT.md` (Punkt 7 fertig)
- `tests/beispielmaschinen.py` (Baukasten aus dem Addon),
  `tests/test_beispielmaschine.py` (neu),
  `tests/gui/szenario_beispielmaschine.py` (neu)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
FreeCAD ohne offenes Dokument → CAM → „Maschine bearbeiten“: Die Meldung
hat den Knopf „Beispielmaschine laden“ → Klick → neues Dokument
„Beispielmaschine“ mit Bett, Ständer, Kreuztisch, blauem Fräskopf und
Spindel; der Dialog zeigt Y1, Z1, X1, S1 und die Aufnahmen „Tisch“ und
„Spindel“ mit Haken. Dasselbe über „Maschine verfahren“: X1 auf 200 → der
Tisch fährt nach rechts; Z1 auf −80 → der Kopf senkt sich.

### DONE
- Dreiachs-Fräsmaschine: X ±250, Y −150 … 120, Z −100 … 250 mm; Eilgang
  20/20/15 m/min, Vorschub 10 m/min, S1 12 000 U/min; Werkzeugaufnahme an
  der Spindelnase (angetrieben von S1), Werkstückaufnahme mitten auf dem
  Tisch. Farben: Guss dunkel, Schlitten hell, Kopf blau.
- `gelenk_wie_gebaut`: Nach dem Anlegen und nach dem Setzen der Versätze
  kommen die Teile zurück – mit Oberfläche klappte FreeCADs Vorab-Lösen den
  Fräskopf sonst hinter den Ständer (Screenshot); beide Seiten liegen jetzt
  genau aufeinander.
- Baukasten mit Ansichten für Gelenke und Fixierung, wenn es eine
  Oberfläche gibt; die Beispielmaschinen der Prüfungen bleiben, wie sie
  waren.

### TEST
- `test_beispielmaschine.py` in 1.1.3 und 26.3.0 grün (nichts verschoben,
  keine Warnung, Achsen in Achsrichtung, Grenzen, Aufnahmen, Grenzen für
  den Planer); `test_kette`, `test_verfahren`, `test_maschine`,
  `test_schruppwerte`, `test_hilfe`, `test_sprache` grün.
- `szenario_beispielmaschine` in 1.1.3 grün, Screenshots angesehen
  (Meldung mit Knopf, Maschine mit Dialog, verfahren X 200 / Y −100 /
  Z −80); `szenario_felder`, `_hilfe`, `_maschine_bearbeiten`,
  `_uebergeben`, `_verfahren`, `_zeigen` grün. Voller Lauf vor dem Push.

### NEXT
- Version 0.13.0, voller Lauf, Push; dann A3 Warngrenze.

## P-2026-09-26-37 neues-werkzeug-beispielwerte

### EINGELESEN
- Manuel (2026-09-26): Ein neues Werkzeug soll gleich Beispielwerte haben,
  damit das Bild die Form zeigt („ahh ja ok das ist der Schaftfräser“);
  beim Durchblättern immer ein Bild. „Beispielwerte in grau, aber dennoch
  aktiv … das Beispiel sollte 12 sein beim Durchmesser“. Im Planer: „die
  Spandicke … schreib bitte auch hier Beispiele rein und bei vc auch“.
- `docs/STATUS_SNAPSHOT.md` (Plan, Stufe A Punkt 2), Spezifikation W-002.

### DATEIEN
- `camaddon/werkzeuge.py` (`BEISPIELE`, `beispielwerte_setzen`, Merker
  `Werkzeug.beispiel`, `neues_werkzeug` mit Beispielen)
- `camaddon/gui_werkzeuge.py` (graue Felder, Satz „Grau: Beispielwerte …“,
  Eingabe macht eigen, Wechsel der Art, Durchmesser markiert)
- `camaddon/gui_werkzeugbild.py` (`mit_beispielmassen`: Form auch ohne
  Durchmesser, Beispiele gestrichelt)
- `camaddon/schruppwerte.py` (`BEISPIEL_SCHNITT`, `beispiel_schnitt`)
- `camaddon/gui_schruppwerte.py` (vc und Spandicke grau, wenn die Zeile
  keine hat)
- `translations/de.json`, `translations/en.json` (`wv.beispiel`,
  `sp.beispiel`)
- `help/de|en/werkzeuge.html`, `help/de|en/schruppwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 25)
- `docs/STATUS_SNAPSHOT.md` (Punkte 1 und 2 fertig)
- `tests/test_werkzeuge.py`, `tests/test_schruppwerte.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`,
  `tests/gui/szenario_schruppwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
CAM → Werkzeugverwaltung → „Neu“: Ø 12, 3 Schneiden, Schneidenlänge 26
stehen grau da, darunter „Grau: Beispielwerte – sie gelten, bis du eigene
einträgst.“, rechts das Bild eines Schaftfräsers (gestrichelt). „10“ tippen
→ der Durchmesser ist schwarz. Art „Torusfräser“ → Schneiden 4 und
Eckradius 1 grau. Durchmesser leeren → roter Hinweis, das Bild zeigt
trotzdem die Form. „Schruppwerte planen…“ bei einer Zeile ohne vc und fz →
vc 120 und Spandicke 0,05 grau (HSS: 30 und 0,03), der Plan rechnet damit.

### DONE
- Beispielwerte je Art (alle mit Ø 12): Schaftfräser z 3, L 26; Torus z 4,
  L 26, R 1; Radius z 2, L 24; Fasen z 2, L 6; Bohrer z 2, L 60. Sie
  gelten wie eingetragene; nur der Merker, dass sie Beispiel sind, wird
  nicht gespeichert.
- Wechsel der Art: graue und leere Felder bekommen die Beispiele der neuen
  Art; eigene Werte bleiben. Kopien haben keine Beispiel-Merker.
- Bild: Beispielmaße gestrichelt; ohne Durchmesser die Form der Art mit
  ihren Beispielmaßen.
- Planer: ohne vc bzw. Spandicke aus der Zeile graue Beispiele für Stahl,
  mit Satz; Tippen macht das Feld eigen.

### TEST
- `test_werkzeuge.py`, `test_schruppwerte.py`, `test_sprache.py`,
  `test_hilfe.py` in 1.1.3 grün; `szenario_werkzeugverwaltung` und
  `szenario_schruppwerte` in 1.1.3 grün, Screenshots angesehen (graue
  Werte, Bild ohne Durchmesser, Planer mit HSS-Beispielen). Voller Lauf mit
  dem nächsten Push.

### NEXT
- Beispielmaschine laden (Plan Punkt 7), dann A3 Warngrenze.

## P-2026-09-26-36 test-uebergabe-deutsch

### EINGELESEN
- Voller Lauf vor dem Push von 0.12.0: `test_uebergabe_werkzeuge.py` rot
  in 1.1.3 – „Beispielname in CAM: 'End mill T3 Carbide D12 L26'“. Seit
  P-2026-09-26-27 gilt ohne gespeicherte Wahl FreeCADs Sprache;
  `freecadcmd` 1.1.3 meldet Englisch, der Wochen-Build nicht. Die Prüfung
  aus P-2026-09-26-33 setzte keine Sprache.

### DATEIEN
- `tests/test_uebergabe_werkzeuge.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Prüfung ist in beiden Versionen grün, unabhängig von FreeCADs Sprache.

### DONE
- Die Prüfung setzt Deutsch wie `test_werkzeuge.py` und stellt danach die
  vorige Wahl wieder her.

### TEST
- `test_uebergabe_werkzeuge.py` einzeln in 1.1.3 und 26.3.0 grün; dann
  `scripts/alle_tests.sh`.

### NEXT
- Push 0.12.0.

## P-2026-09-26-35 version-0-12-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.11.2: Plan-Antworten (P-2026-09-26-32), Werkzeugname (-33), Plan
  Beispielmaschine (-34).
- Manuel (2026-09-26): „kannst du das mal puschen soweit und dann es bauen
  anfangen“.

### DATEIEN
- `package.xml` (0.12.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.12.0.

### DONE
- Version 0.11.2 → 0.12.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann A2 (Beispielwerte) fertig, danach die Beispielmaschine.

## P-2026-09-26-34 plan-beispielmaschine

### EINGELESEN
- Manuel (2026-09-26): „Maschine bearbeiten“ und „Maschine verfahren“
  melden ohne Baugruppe nur, dass man erst eine bauen soll – wer das Addon
  ausprobieren will, scheitert daran. Wunsch: ein Knopf
  „Beispielmaschine laden“, damit man sieht, wie es geht.
- `tests/beispielmaschinen.py`: Baukasten für Beispielmaschinen
  (Drehmaschine, Fünfachser) – bisher nur für die Prüfungen.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan: Punkt 7, Nummern von B und C folgen)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Plan im Snapshot nennt die Beispielmaschine mit Ort in der
Reihenfolge (nach A2, vor A3).

### DONE
- Punkt 7 „Beispielmaschine laden“ im Plan; Stufe B jetzt 8–9, C 10
  (vorher doppelte 6).

### TEST
- Nur Doku.

### NEXT
- Version 0.12.0 (Werkzeugname), Lauf, Push; dann A2 fertig, danach die
  Beispielmaschine.

## P-2026-09-26-33 werkzeugname

### EINGELESEN
- Manuel: Moderne Steuerungen rufen Werkzeuge über Namen auf
  (T="Fräser VHM 12"); Option A – Nummer und Name. Leerzeichen nicht
  ersetzen, der Bediener schreibt, was die Maschine will. Beispielname aus
  den Angaben: „Schaftfräser T1 VHM D12 L30“.
- FreeCADs Postprozessoren rufen per Nummer; der Heidenhain-Post schreibt
  den Namen des Werkzeug-Controllers als Kommentar hinter TOOL CALL.

### DATEIEN
- `camaddon/werkzeuge.py` (Feld `name`, `beispielname()`, `anzeigename()`,
  Listenzeile mit Namen, Suche, `Bibliothek.mit_name()`)
- `camaddon/gui_werkzeuge.py` (Feld „Name“ unter Nummer/Art, grau der
  Beispielname, Hinweis bei doppeltem Namen)
- `camaddon/uebergabe_werkzeuge.py` (ToolBit heißt `anzeigename()`)
- `camaddon/job_schnittwerte.py` (Controller „T3 <Name> – <Einsatz>“)
- `camaddon/werkzeuge_aus_cam.py` (Name aus CAM wird der Name, nicht mehr
  die Bezeichnung; „schon da“ erkennt beide)
- `translations/de.json`, `translations/en.json`, `help/de|en/werkzeuge.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 5, Nr. 24)
- `tests/test_werkzeuge.py`, `tests/test_uebergabe_werkzeuge.py`,
  `tests/test_werkzeuge_aus_cam.py`, `tests/test_job_schnittwerte.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Neu → Ø 12, Schneidenlänge 26 → das Feld „Name“ zeigt
grau „… Schaftfräser T1 VHM D12 L26“ → „Fräser VHM 12“ eintragen → die Liste
zeigt „T1  Fräser VHM 12 · Schaftfräser Ø 12 · z 3 · VHM“ → „Speichern und
an CAM übergeben“ → in CAM heißt das Werkzeug „Fräser VHM 12“; „Werkzeug-
Controller hinzufügen“ legt „T1 Fräser VHM 12 – …“ an.

### DONE
- Name mit Beispielname, Liste, Suche, Hinweis, CAM, Controller, Import.

### TEST
- Unit-Tests (beide Versionen): Beispielname mit Punkt, Zeile und Suche mit
  Namen, gleicher Name (groß/klein), Speichern/Laden, alte Datei; ToolBit
  heißt wie eingetragen bzw. nach dem Beispielnamen; Import füllt den
  Namen; Controller-Name mit Werkzeugname, Einsatz wird trotzdem erkannt.
- `szenario_werkzeugverwaltung` (beide Versionen): grauer Beispielname,
  Name tippen, Listenzeile, doppelter Name gemeldet, Name gespeichert;
  `szenario_aus_cam`, `szenario_an_cam`, `szenario_schnittwerte_job` grün.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- A2 Beispielwerte (auch im Planer: vc, Spandicke – Manuel).

## P-2026-09-26-32 plan-antworten

### EINGELESEN
- Manuel: Reihenfolge A → B → C selbstverständlich (die Frage war
  überflüssig); Warngrenze fest 10 % bei HSM, egal wie viele Schneiden; ap
  wie ae in % von D; Drehwerkzeuge gleich mit in Stufe C. Beim Bohrer
  fehlt der Spitzenwinkel.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan: Antworten, Spitzenwinkel als A6)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot enthält Manuels Antworten und den Spitzenwinkel.

### DONE
- Plan vervollständigt, Stufe A beginnt.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- A1 Werkzeugname.

## P-2026-09-26-31 plan-stufen

### EINGELESEN
- Manuels Antworten: Beispielwerte grau, aber gültig (Ø 12);
  Warngrenze 10 % bei voller Schneidenlänge als Vorgabe, darüber rote
  Warnung, aber wählbar; mm/% für ae und ap; Einheiten (mm/inch) und
  Dezimaltrennzeichen beim ersten Start und in den Einstellungen wählbar,
  mit Beispielzahlen; Werkzeuge in inch und mm umschaltbar. Dazu die Liste
  der Werkzeugarten aus InventorCAM (Screenshot, 26 Arten).

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan in drei Stufen)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot nennt die Stufen A (Werkzeugverwaltung), B (Einheiten,
Zahlenformat), C (Werkzeugarten) mit ihren Schritten.

### DONE
- Plan geordnet.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels OK zur Reihenfolge, dann Stufe A.

## P-2026-09-26-30 plan-erweitert

### EINGELESEN
- Manuel (Planung, noch nichts bauen): Namen trägt man selbst ein, ein
  Beispielname aus den Angaben wäre gut („Schaftfräser T1 VHM D12 L30“).
  Planer: „Wer sagt was von 10 %?“ – die Prozente zeigen, eine eigene
  Warngrenze eintragen können, darüber warnen. Neues Werkzeug:
  Beispielwerte, damit das Bild gleich die Form zeigt, auch beim
  Durchblättern der Liste.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan Punkt 1 ergänzt, Punkte 5 und 6)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot nennt die sechs geplanten Schritte mit den offenen Fragen.

### DONE
- Plan ergänzt.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels Antworten, dann bauen.

## P-2026-09-26-29 version-0-11-2

### EINGELESEN
- Arbeitsregeln Abschnitt 4: Korrektur → letzte Stelle. Seit 0.11.1:
  Sprachwahl beim ersten Start (P-2026-09-26-27), Plan im Snapshot (-28).

### DATEIEN
- `package.xml` (0.11.2)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.11.2.

### DONE
- Version 0.11.1 → 0.11.2.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann Manuels Antworten zum Plan.

## P-2026-09-26-28 plan-nach-erstem-test

### EINGELESEN
- Manuels erster Test in FreeCAD 1.1.3 (KDE, dunkles Thema): „sehr gut
  umgesetzt“. Wünsche: Werkzeugname zusätzlich zur Nummer (Option A),
  ae wahlweise in mm oder %, Dezimalzeichen wie FreeCAD („.“ für
  Postprozessoren?), das Eingriffsbild mit „ae“ und „ap“ beschriften und
  den Text daneben aufteilen. Bitte: erst alle Aktionen planen.
- `gui_zahlen.zahlenformat()` nimmt `QLocale()` – das stellt FreeCAD nach
  seiner Einstellung „Zahlenformat“ (Parameter `UseLocaleFormatting`) ein.
- FreeCADs Postprozessoren rufen Werkzeuge per Nummer; der Heidenhain-Post
  schreibt den Namen des Werkzeug-Controllers als Kommentar.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan, wartet auf Manuels OK)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot nennt die vier geplanten Schritte mit den offenen Fragen.

### DONE
- Plan festgehalten.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels OK, dann bauen.

## P-2026-09-26-27 sprachwahl-erster-start

### EINGELESEN
- Manuels erster Start (FreeCAD 1.1.3, KDE, dunkles Thema), Screenshot:
  1. Der Titel „Sprache wählen“ sagt nicht, wofür.
  2. Der Hinweis unter der Auswahl ist abgeschnitten.
  3. Er hat Deutsch gewählt, die Knöpfe des Addons blieben englisch
     („Cutting data into the job“).
  4. Frage: Wird die Sprache gemerkt?
- Ursachen, im Test nachgestellt:
  - Zu 2: Das Fenster entsteht mit dem englischen Text (bei Manuel eine
    Zeile); der deutsche braucht zwei, und das offene Fenster wächst unter
    KDE nicht mit.
  - Zu 3: FreeCAD liest Name und Tooltip eines Befehls nur einmal beim
    Anmelden (vor der Frage) und auch bei FreeCADs eigenem Sprachwechsel
    nicht neu.
  - Zu 4: Gemerkt wird die Sprache (Parameter „Sprache“). Auf die Platte
    schreibt FreeCAD aber erst beim Beenden – nach einem Absturz käme die
    Frage wieder.
- FreeCAD meldet seine eigene Sprache über `getLocale()` („German“),
  `supportedLocales()` übersetzt in den Code („de“) – in beiden Versionen.
- Nebenbei: Die Werkzeugleiste hieß je nach Sprache „CAM-Addon“ oder
  „CAM Addon“; nach einem Sprachwechsel hätte sie doppelt erscheinen können.

### DATEIEN
- `camaddon/sprache.py` (`freecad_sprache()`; ohne Wahl gilt die Sprache
  von FreeCAD, sonst Englisch)
- `camaddon/gui_sprachwahl.py` (Vorwahl = aktuelle Sprache; Platz für die
  Texte jeder Sprache; Wahl sofort speichern; danach `NACH_SPRACHWAHL`)
- `camaddon/gui_start.py` (Befehle gemerkt, `befehle_beschriften()` nach
  einer Sprachwahl und wenn FreeCAD neue Knöpfe anlegt; Werkzeugleiste
  heißt fest „CAM-Addon“)
- `translations/de.json`, `translations/en.json` (Titel mit Addon-Namen;
  `werkzeugleiste.name` entfällt)
- `tests/gui/szenario_erster_start.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Frisches FreeCAD-Profil, FreeCAD auf Deutsch → Start: Das Fenster heißt
„CAM-Addon – Sprache wählen“, Deutsch ist vorgewählt, der Hinweis ist ganz
zu lesen → OK → die Knöpfe der Werkzeugleiste „CAM-Addon“ sind deutsch,
ohne Neustart. Beim nächsten Start kommt keine Frage mehr.

### DONE
- Alle vier Punkte behoben, dazu der feste Name der Werkzeugleiste.

### TEST
- `tests/gui/szenario_erster_start.py` (beide Versionen): Titel auf
  Englisch und Deutsch; Mindesthöhe reicht für den deutschen Text (ohne die
  Korrektur schlägt das an: „zu niedrig: 116 < 130“); die Wahl steht sofort
  in user.cfg; Knopf und Tooltip nach der Wahl deutsch, nach Umstellen in
  den Einstellungen wieder englisch; die Werkzeugleiste nur einmal;
  FreeCAD auf Deutsch → Vorgabe „de“, auf Japanisch → keine (Englisch).
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Manuel: Beim nächsten Start sollte keine Frage mehr kommen; in einem
  frischen FreeCAD-Profil ist Deutsch vorgewählt.

## P-2026-09-26-26 version-0-11-1

### EINGELESEN
- Arbeitsregeln Abschnitt 4: Korrektur → letzte Stelle. Seit 0.11.0:
  „Aus CAM übernehmen“ robust gegen einzelne kaputte Werkzeuge
  (P-2026-09-26-24), Abhilfe im Tooltip „nicht in der Werkzeugverwaltung“
  (-25).

### DATEIEN
- `package.xml` (0.11.1)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.11.1.

### DONE
- Version 0.11.0 → 0.11.1.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-26-25 kein-werkzeug-abhilfe

### EINGELESEN
- Die erste Zeile, die Manuel in seinen Jobs sieht, ist oft „TC: 5mm
  Endmill – nicht in der Werkzeugverwaltung“. Der Tooltip sagte nur, warum,
  nicht, was man tun kann.

### DATEIEN
- `translations/de.json`, `translations/en.json` (`sj.kein_werkzeug.tooltip`)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Schnittwerte in den Job“ → Maus auf „– nicht in der Werkzeugverwaltung“ →
der Tooltip nennt die Abhilfe: „Aus CAM übernehmen“ in der
Werkzeugverwaltung oder hier „Werkzeug-Controller hinzufügen“.

### DONE
- Tooltip um die Abhilfe ergänzt (de/en).

### TEST
- `tests/test_sprache.py` in beiden Versionen.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-24 aus-cam-robust

### EINGELESEN
- „Aus CAM übernehmen“ trifft morgen auf Manuels echte Bibliotheken. Warf
  ein einzelnes Werkzeug beim Lesen einen Fehler, brach `uebernehmen()` ab:
  Der Dialog meldete den Fehler, aber die schon übernommenen Werkzeuge
  standen halb in der (ungespeicherten) Liste, ohne dass sie neu gezeigt
  wurde.

### DATEIEN
- `camaddon/werkzeuge_aus_cam.py` (je Werkzeug abgesichert; Bericht
  `unlesbar`, Meldung im Bericht-Fenster von FreeCAD)
- `camaddon/gui_werkzeuge.py` (Rückmeldung nennt die unlesbaren)
- `translations/de.json`, `translations/en.json`
- `tests/test_werkzeuge_aus_cam.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Aus CAM übernehmen ▾“ → eine Bibliothek, in der ein
Werkzeug kaputt ist → die übrigen erscheinen in der Liste; die Rückmeldung
sagt „Nicht lesbar – … Bericht-Fenster: <Name>“.

### DONE
- Ein Fehler betrifft nur sein Werkzeug; es steht im Bericht, die anderen
  werden übernommen.

### TEST
- `tests/test_werkzeuge_aus_cam.py` (beide Versionen): ein Werkzeug, das
  beim Lesen einen Fehler wirft („5mm Drill“) → `unlesbar`, die übrigen
  fünf bekannten Formen übernommen. `szenario_aus_cam` weiter grün.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-23 version-0-11-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.10.0: „keine Bahn: Basisgeometrie fehlt“ im Job-Dialog
  (P-2026-09-26-22); dazu Bohrer-Kopie (-19), Hilfe zu Ebenen und
  Basisgeometrie (-20, -21), Doku (-18). Der Snapshot nennt jetzt auch die
  Basisgeometrie.

### DATEIEN
- `package.xml` (0.11.0)
- `docs/STATUS_SNAPSHOT.md` (Nächster Schritt, Punkt 2)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.11.0.

### DONE
- Version 0.10.0 → 0.11.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-26-22 ohne-basisgeometrie

### EINGELESEN
- Ausprobiert (FreeCADCmd, 1.1.3 und Wochen-Build): Adaptiv (innen und
  außen), Tasche, Taschenform, Fläche und Nut ohne Basisgeometrie rechnen
  keine Bahn – keine einzige G1/G2/G3-Bewegung.
- „Schnittwerte in den Job“ zeigte für eine solche Operation trotzdem
  Ebenen, gerechnet aus den Vorgabetiefen – als würde sie fahren.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`ohne_bahn()`)
- `camaddon/gui_job_schnittwerte.py` („keine Bahn: Basisgeometrie fehlt“
  statt der Ebenen)
- `translations/de.json`, `translations/en.json`
- `help/de|en/werkzeuge.html`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit einem Adaptiv ohne Basisgeometrie und dem Controller
„T3 Schruppen dynamisch“ → „Schnittwerte in den Job“: In der Spalte steht
„Adaptiv: 10 % · 25 mm · Helix 3° · keine Bahn: Basisgeometrie fehlt“.
Mit Basisgeometrie stehen dort wieder die Ebenen.

### DONE
- Als „ohne Bahn“ gilt eine Operation mit leerer Basisgeometrie und ohne
  Bewegung in ihrer Bahn; dann keine Ebenen und kein Hinweis zu ihnen.

### TEST
- `tests/test_job_schnittwerte.py`: Adaptiv ohne Basisgeometrie → ohne
  Bahn; ein Objekt ohne `Base` zählt nicht.
- `tests/gui/szenario_schnittwerte_job.py` (beide Versionen): der Text in
  der Spalte; `szenario_loch_auffraesen` (mit Basisgeometrie) unverändert
  grün.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-21 hilfe-basisgeometrie

### EINGELESEN
- Hilfe „Ein Loch oder eine Tasche auffräsen“ sagte nur „Adaptiv auf die
  Bohrung legen“. Ausprobiert (FreeCADCmd, 1.1.3 und Wochen-Build,
  Quader 60 × 60 × 30, Bohrung Ø 30):
  - Sackloch, Boden als Basisgeometrie: räumt die Bohrung bis zum Boden
    (P-2026-09-26-16).
  - Durchgangsbohrung, **untere Kreiskante**: räumt nur die Bohrung
    (x, y 17,5 … 42,5 mit Ø 5), von 31 bis 0.
  - obere Kreiskante: nur bis 30, also 1 mm tief.
  - Bohrungswand: keine Bahn.
  - Unterseite des Teils, „Innen“: räumt die ganze Fläche 2,5 … 57,5 ab –
    das Teil wäre weg.

### DATEIEN
- `help/de|en/werkzeuge.html` (Schritt 3: welche Basisgeometrie)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Hilfe der Werkzeugverwaltung → „Ein Loch oder eine Tasche auffräsen“,
Schritt 3 nennt: Sackloch und Tasche → Boden, Durchgangsbohrung → untere
Kreiskante; und warnt vor der Unterseite des Teils und der oberen Kante.

### DONE
- Schritt 3 präzisiert, in beiden Sprachen.

### TEST
- `tests/test_hilfe.py` in beiden Versionen.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-20 hilfe-loch-verweis

### EINGELESEN
- Hilfe „Ein Loch oder eine Tasche auffräsen“, Schritt 4, versprach „taucht
  einmal helikal bis 25 mm ein“ – mit FreeCADs Rohteil sind es meist zwei
  Ebenen (P-2026-09-26-16).
- Ein Kommentar in `job_schnittwerte.py` nannte das Profil noch „Kontur“
  (P-2026-09-26-13).

### DATEIEN
- `help/de|en/werkzeuge.html` (Schritt 4 verweist auf „Eine Ebene oder
  zwei?“)
- `camaddon/job_schnittwerte.py` (nur Kommentar)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Hilfe der Werkzeugverwaltung → „Ein Loch oder eine Tasche auffräsen“,
Schritt 4: kein Versprechen „einmal“ mehr, dafür der Verweis auf „Eine
Ebene oder zwei?“.

### DONE
- Wortlaut angepasst, Kommentar angeglichen.

### TEST
- `tests/test_hilfe.py` in beiden Versionen, black und ruff.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-19 einsatz-kopieren-nachtrag

### EINGELESEN
- P-2026-09-26-12: Die Kopie einer Zeile wählt die Spalte ae – beim Bohrer
  ist sie ausgeblendet; gewählt war dann eine unsichtbare Zelle.
- Die Nummern für doppelte Namen aus „+ Einsatz“ und vom Planer
  (`einsatz_hinzufuegen`) waren nur ohne Oberfläche geprüft.

### DATEIEN
- `camaddon/gui_schnittwerte.py` (Kopie beim Bohrer: Spalte vc)
- `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Bohrer mit einer Zeile „Bohren“ → „+ Einsatz ▾ →
Gewählte Zeile kopieren“ → darunter „Bohren 2“, und die Zelle vc ist
gewählt.

### DONE
- Kopie beim Bohrer wählt vc.

### TEST
- `tests/gui/szenario_schnittwerte.py` (beide Versionen): „+ Einsatz“ und
  `einsatz_hinzufuegen` bei vorhandenem „Schruppen dynamisch“ → „… 2“ und
  „… 3“; Bohrer-Kopie „Bohren 2“ mit gewählter Spalte vc.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-18 stand-fuer-manuel-2

### EINGELESEN
- Arbeitsregeln Abschnitt 10: Snapshot und README auf den Stand bringen;
  Entscheidungen dieser Nacht in die Spezifikation.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` („Nächster Schritt“: Zeile kopieren, Ebenen
  im Job-Dialog, Außenkontur; Entscheidungen 13–23)
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 11, Nr. 21–23)
- `README.md` („Was es kann“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer Snapshot und Spezifikation liest, findet die neuen Klickwege und die
drei neuen Entscheidungen mit Alternative.

### DONE
- Nr. 21: Kopien und doppelte Namen mit Nummer; Nr. 22: Namen wie im
  Menü von FreeCAD; Nr. 23: dünne letzte Ebene nur melden, ap nicht selbst
  ändern.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuel probiert aus und bespricht die Entscheidungen.

## P-2026-09-26-17 version-0-10-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.9.0: Zeile kopieren (P-2026-09-26-12), Ebenen im Job-Dialog (-16); dazu
  Einsatz am Namen (-11), Operationsnamen wie in FreeCAD (-13),
  Fehlerbericht T-004 (-14), Git ohne Konsolenfenster (-15).

### DATEIEN
- `package.xml` (0.10.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.10.0.

### DONE
- Version 0.9.0 → 0.10.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-26-16 ebenen-im-job-dialog

### EINGELESEN
- Manuels „einmal helikal ein Grundloch, dann ebenenweise mit voller
  Schneide“ nachgestellt (FreeCADCmd, beide Versionen): Quader 60 × 60 × 30
  mit Sackloch Ø 30, 25 tief, Adaptiv mit dem Boden als Basisgeometrie,
  Zustelltiefe 25 → **zwei** Ebenen, 25 mm und 1 mm, jede mit eigener
  Helix. Grund: Die Starttiefe ist die Oberkante des Rohteils, und FreeCAD
  legt das Rohteil von sich aus 1 mm über das Modell.
- Die Ebenen rechnet FreeCAD mit `PathUtils.depth_params` (in 1.1.3 und im
  Wochen-Build gleich).
- Ändert man das Rohteil, rechnet FreeCAD die Operation nicht von selbst
  neu – sie behält die alte Starttiefe; eine Neuberechnung der Operation
  genügt (geprüft).
- Beschriftungen im deutschen FreeCAD ausgelesen: „Auftrag bearbeiten →
  Einrichtung → Materialkörper → Erw. Z“ (linkes Feld nach unten, rechtes
  nach oben), im Baum „Objekt neu berechnen“.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`ebenen()`, `duenne_letzte_ebene()`)
- `camaddon/gui_job_schnittwerte.py` (Spalte „Schrittweite ·
  Zustelltiefe“ mit „1 Ebene“ bzw. „2 Ebenen (25 + 1 mm)“; roter Satz unter
  der Tabelle bei einer dünnen letzten Ebene; Fenster breiter)
- `translations/de.json`, `translations/en.json`
- `help/de|en/werkzeuge.html` („Eine Ebene oder zwei?“)
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`,
  `tests/gui/szenario_loch_auffraesen.py` (neu)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Teil mit Sackloch 25 mm tief, Job mit FreeCADs Rohteil, Adaptiv auf den
Boden des Lochs mit dem Controller „T3 Schruppen dynamisch“ (ap 25) →
„Schnittwerte in den Job“ zeigt „… · 2 Ebenen (25 + 1 mm)“ und darunter in
Rot, dass die letzte Ebene nur 1 mm dick ist, mit den zwei Auswegen. Im
Job bei „Erw. Z“ rechts 0, Adaptiv neu berechnen → der Dialog zeigt
„1 Ebene“, kein roter Satz → Übernehmen → das Adaptiv taucht einmal
helikal bis zum Boden ein und räumt nur dort.

### DONE
- Ebenen je Operation in der Spalte, Hinweis bei dünner letzter Ebene
  (dünner als ¼ ap), mit ap-Vorschlag nur, wenn die Schneide reicht.
- Hilfe erklärt die Ursache und beide Auswege.

### TEST
- `tests/test_job_schnittwerte.py`: Ebenen der Tasche (25 + 25 + 11,
  30,5 + 30,5), ohne Tiefen [], dünne letzte Ebene (25 + 1 → ap 26;
  25 + 25 + 2 → ap 26; 11 von 25 und eine Ebene sind kein Rest).
- `tests/gui/szenario_loch_auffraesen.py` (neu, beide Versionen): Controller
  über den Dialog anlegen, 2 Ebenen mit Hinweis, Hinweis weg ohne
  Zustellung, Rohteil bündig → 1 Ebene; nach Übernehmen hat die Bahn genau
  eine Helix bis z = 5 und schneidet danach nur auf z = 5. Bilder
  `1_zwei_ebenen`, `2_eine_ebene` angesehen. (Ein 3D-Bild der Bahn blieb
  leer – eine per Skript angelegte Operation zeichnet ihre Bahn nicht; die
  Bahn wird deshalb nur in Zahlen geprüft.)
- `tests/gui/szenario_schnittwerte_job.py`: „· 1 Ebene“.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Manuel: an einem echten Teil ausprobieren. Stimmt der Satz unter der
  Tabelle mit dem überein, was er in der Simulation sieht?

## P-2026-09-26-15 git-ohne-konsolenfenster

### EINGELESEN
- Die Update-Suche ruft bei jedem Start von FreeCAD bis zu fünfmal Git auf
  (fetch, show, show, status, merge-base). FreeCAD läuft unter Windows ohne
  Konsole; startet es ein Konsolenprogramm wie git.exe, öffnet Windows dafür
  jedes Mal kurz ein schwarzes Fenster – ohne `CREATE_NO_WINDOW`.

### DATEIEN
- `camaddon/aktualisierung.py` (`OHNE_FENSTER`, an `subprocess.run`)
- `tests/test_aktualisierung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Windows: FreeCAD starten und etwa eine halbe Minute warten, bis die
Update-Suche gelaufen ist → kein schwarzes Fenster blitzt auf. Linux und
macOS: unverändert.

### DONE
- Git läuft unter Windows mit `CREATE_NO_WINDOW`; anderswo gibt es den Wert
  nicht, dort bleibt es bei 0.

### TEST
- `tests/test_aktualisierung.py`: Jeder Git-Aufruf der Suche bekommt
  `creationflags` = `CREATE_NO_WINDOW` bzw. 0 (in beiden Versionen).
- Unter Windows nicht selbst gesehen – hier gibt es kein Windows. Das
  Akzeptanzkriterium prüft Manuel, falls er Windows benutzt.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-14 t-004-fehlerbericht

### EINGELESEN
- T-004 im Snapshot: den Fehler in `Machine.from_dict` an FreeCAD melden.
- Wochen-Build 26.3.0 dev vom 2026-09-16, `Mod/CAM/Machine/models/machine.py`:
  `to_dict()` schreibt `[Ursprung, Richtung]`, `from_dict()` nimmt bei
  Linearachsen den ersten Vektor als Richtung, sobald er nicht null ist –
  der Fehler besteht weiter. FreeCAD 1.1.3 hat die Maschinenmodelle nicht.

### DATEIEN
- `docs/freecad_fehler_T-004.md` (neu: Weg zum Einreichen für Manuel, der
  englische Text mit Nachstell-Skript, erwarteter und tatsächlicher Ausgabe
  und einem Vorschlag zur Behebung)
- `docs/STATUS_SNAPSHOT.md` (T-004 verweist darauf)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel öffnet `docs/freecad_fehler_T-004.md`, folgt dem Link zu FreeCADs
Issues und kann Titel und Abschnitte ohne Änderung übernehmen; das Skript
im Text zeigt in der FreeCAD-Python-Konsole des Wochen-Builds genau die
Ausgabe unter „Actual behavior“.

### DONE
- Bericht geschrieben, Skript und Vorschlag geprüft.

### TEST
- Das Skript aus dem Bericht (aus der Datei ausgeschnitten) in FreeCADCmd
  des Wochen-Builds: Ausgabe Zeichen für Zeichen wie unter „Actual
  behavior“.
- Der Vorschlag an einer gepatchten Kopie von `machine.py`: Das Beispiel
  kommt richtig zurück, ein alter Eintrag `[[0, 1, 0], [0, 0, 0]]` weiterhin
  mit Richtung (0, 1, 0).
- Nur Doku, kein Testlauf.

### NEXT
- Manuel reicht den Bericht ein und trägt die Nummer bei T-004 ein.

## P-2026-09-26-13 operationsnamen-wie-freecad

### EINGELESEN
- Hilfe und Tooltip von „Schnittwerte in den Job“ nannten FreeCADs
  Operationen „Kontur“, „Tasche“, „Planfräsen“, „Nut“. Im deutschen FreeCAD
  heißen sie anders – ausgelesen aus den Menüs (Wegwerf-Szenario mit
  `Gui.setLocale`, beide Versionen): Adaptiv, **Profil**, **Taschenform**,
  **Fläche** (Wochen-Build: **Fräsen**), **Nute**, Bohren. Englisch: Adaptive,
  Profile, Pocket Shape, Face (Wochen-Build: Mill Facing), Slot, Drilling.
- Die Felder im Aufgabenfenster des Adaptivs: 1.1.3 „Überlappungs-Prozentsatz“,
  „Schritt runter“, „Wendel-Rampenwinkel“, „Schnittbereich: Außen/Innen“;
  Wochen-Build „Prozedurschritt (Prozent)“, „Schritt runter“, „Maximaler
  Rampenwinkel“, „Fräsbereich“.
- Manuels Beispiel „Außenkonturen schruppen“ stand nur als Satz in
  „Strategien vergleichen“. Geprüft in beiden Versionen (FreeCADCmd,
  Quader 40 × 30 × 20): Adaptiv mit der Unterseite als Basisgeometrie und
  „Außen“ fährt neben dem Rohteil gerade auf Tiefe und schneidet von der
  Seite hinein, ohne Helix; „Innen“ taucht mit Helix ein; ohne
  Basisgeometrie entsteht keine Bahn.

### DATEIEN
- `translations/de.json`, `translations/en.json` (`sj.zustellung.tooltip`)
- `help/de|en/werkzeuge.html` (Namen, Felder des Adaptivs, neuer Abschnitt
  „Eine Außenkontur schruppen“)
- `help/de|en/strategien.html` (Verweis darauf; „Zustelltiefe“ statt
  „Stufentiefe“), `help/de/schruppwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Namen in Abschnitt 10 und 11)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Hilfe (?) → „Eine Außenkontur schruppen“: Die
Schritte nennen genau die Wörter, die im deutschen FreeCAD 1.1.3 im Menü
und im Aufgabenfenster des Adaptivs stehen (Adaptiv, Basisgeometrie,
Bearbeitung, Schnittbereich, Außen), und dem Weg folgend entsteht eine
Bahn rund um das Teil.

### DONE
- Namen angeglichen, Feldnamen genannt, Abschnitt Außenkontur.

### TEST
- `tests/test_sprache.py`, `tests/test_hilfe.py` in beiden Versionen; alle
  Hilfeseiten auf geschlossene Tags geprüft; der Abschnitt im Hilfefenster
  als Screenshot angesehen.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Manuel: Stimmen die Namen in seinem FreeCAD? Nennt er „Nute“ lieber
  „Nut“, bleibt es trotzdem beim Wort aus dem Menü.

## P-2026-09-26-12 einsatz-kopieren

### EINGELESEN
- Manuels „Auswertung der Strategien aus den Werten“: Eine Variante (etwa
  dynamisch mit ae 1,8 statt 1,2) musste man bisher als neue Zeile anlegen
  und alle Werte abtippen. Zwei Zeilen hießen dann gleich – im Vergleich,
  in „Schnittwerte in den Job“ und im Namen eines neuen
  Werkzeug-Controllers nicht zu unterscheiden. Dasselbe passierte, wenn der
  Planer ein zweites „Schruppen dynamisch“ anlegte.

### DATEIEN
- `camaddon/werkzeuge.py` (`name_fuer_neuen()`: frei bleibt frei, sonst
  „… 2“, „… 3“; die Kopie von „… 2“ wird „… 3“)
- `camaddon/gui_schnittwerte.py` (Menü „+ Einsatz“ → „Gewählte Zeile
  kopieren“, Kopie direkt unter der Zeile; neue Zeilen aus dem Menü und
  vom Planer bekommen eine Nummer, wenn es den Namen schon gibt)
- `translations/de.json`, `translations/en.json`
- `help/de|en/schnittwerte.html`, `help/de|en/strategien.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 6.2)
- `tests/test_werkzeuge.py`, `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Fräser mit „Schruppen dynamisch“ (ae 1,2) → Zeile
wählen → „+ Einsatz ▾“ → „Gewählte Zeile kopieren“ → darunter steht
„Schruppen dynamisch 2“ mit denselben Werten, die Kopie ist gewählt → dort
ae 1,8 tippen → das Original behält 1,2 → „Strategien vergleichen…“ zeigt
beide mit ihrem Namen.

### DONE
- Kopieren, Nummern für doppelte Namen, Hilfe (Varianten vergleichen).

### TEST
- `tests/test_werkzeuge.py`: Namen (frei, „… 2“, Kopie der 2, groß/klein,
  „Vollnut 12“ → „Vollnut 13“).
- `tests/gui/szenario_schnittwerte.py`: Vollnut kopieren → „Vollnut 2“
  darunter und gewählt, ap 6 in der Kopie → Q 34,4, Original ap 3; Kopie
  wieder löschen. Bild `1e_kopie`.
- Menü offen und Kopie von „Schruppen dynamisch“ als Screenshot angesehen
  (Wegwerf-Szenario, nicht im Repo).
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Manuel: Varianten anlegen und vergleichen – ist die Nummer im Namen
  verständlich, oder lieber gleich ein eigener Name?

## P-2026-09-26-11 einsatz-am-namen

### EINGELESEN
- `vorgeschlagener_einsatz()` nahm die erste Zeile, deren Name im Namen des
  Werkzeug-Controllers steht. „T3 Schruppen dynamisch“ enthält aber auch
  „Schruppen“ – mit den Zeilen Vollnut, Schruppen, Schruppen dynamisch (die
  übliche Reihenfolge im Menü „+ Einsatz“) schlug der Dialog „Schnittwerte
  in den Job“ also „Schruppen“ vor, auch für den Controller, den
  „Werkzeug-Controller hinzufügen“ selbst so benannt hat. Der Test hatte nur
  Vollnut und dynamisch.

### DATEIEN
- `camaddon/job_schnittwerte.py` (passen mehrere Namen, gewinnt der
  längste)
- `tests/test_job_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung: Fräser T3 mit den Einsätzen Vollnut, Schruppen,
Schruppen dynamisch → im Job einen Controller „T3 Schruppen dynamisch“ →
„Schnittwerte in den Job“ schlägt in seiner Zeile „Schruppen dynamisch“ vor.

### DONE
- Unter den Zeilen, deren Name im Controller steht, zählt die mit dem
  längsten Namen; bei gleich langen die erste.

### TEST
- `tests/test_job_schnittwerte.py`: Vollnut, Schruppen, Schruppen dynamisch
  → Index 2 für „T3 Schruppen dynamisch“.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Zeile kopieren (Varianten für den Vergleich), Namen neuer Zeilen
  unterscheidbar.

## P-2026-09-26-10 version-0-9-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.8.0: Vergleich mit der Vollnut im Planer (P-2026-09-26-04), alle
  Einsätze im Vergleich (-05), Durchmesser umrechnen (-06), kaputte
  Bibliothek (-07), Eintauchwinkel (-08), Doku (-09).

### DATEIEN
- `package.xml` (0.9.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.9.0.

### DONE
- Version 0.8.0 → 0.9.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-26-09 stand-fuer-manuel

### EINGELESEN
- Arbeitsregeln Abschnitt 10: Snapshot auf den Stand bringen; README „Was
  es kann“ nennt, was dazukam.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Projektstatus W-002; „Nächster Schritt“ als
  Reihenfolge zum Ausprobieren mit Verweisen auf die Klickwege)
- `README.md` („Was es kann“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer den Snapshot liest, weiß, in welcher Reihenfolge er was ausprobiert
und wo die Klickwege stehen.

### DONE
- Nächster Schritt: Werkzeugverwaltung → CAM-Job (Loch auffräsen) →
  Maschine verfahren → Besprechen (Entscheidungen 13–20, Fragen zu
  Stufe 4).

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Version 0.9.0, alle Prüfungen, Push.

## P-2026-09-26-08 eintauchwinkel

### EINGELESEN
- Manuels „einmal helikal ein Grundloch“: Das Adaptiv taucht helikal ein,
  mit FreeCADs Vorgabe von 5° – wie steil ein Fräser eintauchen darf, steht
  aber im Katalog und hängt am Werkzeug.
- FreeCAD 1.1.3: `HelixAngle`, Wochen-Build: `HelixMaxRampAngle` (beide
  Grad, Vorgabe 5°).

### DATEIEN
- `camaddon/werkzeuge.py` (Feld `eintauchwinkel`, 0 … 90°),
  `camaddon/gui_werkzeuge.py` (Feld im Formular, beim Bohrer
  ausgeblendet)
- `camaddon/job_schnittwerte.py` (`zustellung()` setzt den Helixwinkel),
  `camaddon/gui_job_schnittwerte.py` („Helix 3°“ in der Spalte)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge.py`, `tests/test_job_schnittwerte.py`,
  `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ø-12-Fräser mit Eintauchwinkel 3° → Job mit Adaptiv und Controller
„T3 Schruppen dynamisch“ → „Schnittwerte in den Job“ → Spalte zeigt
„Adaptiv: 10 % · 25 mm · Helix 3°“ → Übernehmen → im Adaptiv steht der
Eintauchwinkel der Helix auf 3°.

### DONE
- Freiwilliges Feld am Werkzeug; leer bleibt FreeCADs Vorgabe.
- Gesetzt nur im Adaptiv (und nur, wenn der Einsatz dorthin passt, siehe
  Entscheidung 18) – in 1.1.3 als `HelixAngle`, im Wochen-Build als
  `HelixMaxRampAngle`.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` (gespeichert,
  begrenzt), `test_job_schnittwerte` (Helixwinkel im Adaptiv, nicht in der
  Nut) grün.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job`
  (Spalte, gesetzter Winkel) und `szenario_werkzeugverwaltung` grün,
  Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-07 kaputte-bibliothek

### EINGELESEN
- „Aus CAM übernehmen“ (P-2026-09-25-66): Ließ sich eine einzige
  FreeCAD-Werkzeugbibliothek nicht lesen, blieb das ganze Menü leer.

### DATEIEN
- `camaddon/werkzeuge_aus_cam.py` (`bibliotheken()`: je Bibliothek
  abgefangen)
- `tests/test_werkzeuge_aus_cam.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Eine kaputte `.fctl`-Datei neben „Default“ → „Aus CAM übernehmen“ bietet
„Default“ weiter an; im Bericht-Fenster steht, welche Bibliothek nicht ging.

### DONE
- Je Bibliothek abgefangen, Warnung ins Bericht-Fenster, die übrigen
  bleiben wählbar.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge_aus_cam` grün
  (kaputte Bibliothek „kaputt“ neben „Default“).
- Manuel: –

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-06 durchmesser-umrechnen

### EINGELESEN
- Hilfe der Werkzeugverwaltung: „Kopieren – praktisch für denselben Fräser
  in einem anderen Durchmesser“. Nach dem Kopieren standen ae und ap aber
  noch für den alten Durchmesser da (Vollnut Ø 10 mit ae 12 → Hinweis „ae
  größer als D“).

### DATEIEN
- `camaddon/werkzeuge.py` (`hat_zustellungen()`,
  `zustellungen_umrechnen()`), `camaddon/gui_werkzeuge.py` (Frage beim
  neuen Durchmesser)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge.py`, `tests/gui/szenario_durchmesser.py` (neu)
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 20),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ø-12-Fräser mit Vollnut 12 / 6 und Schruppen dynamisch 1,2 / 24 →
Kopieren → Durchmesser 10 → Frage „… von 12 auf 10 mm … umrechnen?“ → Ja →
Vollnut 10 / 5, dynamisch 1 / 20, vc und fz wie vorher, auch in den eigenen
Werten für 1.4301; das Original bleibt Ø 12. Noch einmal auf 8 → Nein →
nur der Durchmesser ändert sich.

### DONE
- Gefragt wird nur, wenn es Einsätze mit ae oder ap gibt und beide
  Durchmesser bekannt sind; umgerechnet wird für alle Werkstoffe, auf
  0,001 mm gerundet.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` grün.
- KI, Oberfläche in **beiden** Versionen: `szenario_durchmesser` (Ja,
  Nein, Original unverändert) und `szenario_werkzeugverwaltung` grün,
  Screenshots angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-05 alle-einsaetze-im-vergleich

### EINGELESEN
- Manuels Wunsch: „Beurteilung für verschiedene Strategien anhand der
  Werte“. „Strategien vergleichen“ (P-2026-09-25-49) stellt zwei Einsätze
  nebeneinander; bei vier oder fünf Zeilen fehlte der Überblick.

### DATEIEN
- `camaddon/gui_strategie.py` (Übersicht unten im Fenster)
- `help/de|en/strategien.html`, `translations/de.json`,
  `translations/en.json`
- `tests/gui/szenario_strategien.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ø-12-Fräser mit Vollnut, Schlichten und Schruppen dynamisch, Werkstoff C45
→ „Strategien vergleichen…“ → unten „Alle Einsätze dieser Tabelle“: drei
Zeilen; bei „Schruppen dynamisch“ sind Q 43,0, Zeit 2,3, Weg 0,29 und
Schneide 25 fett; Vollnut orange, Schruppen dynamisch blau → Klick auf
„Schlichten“ → B ist Schlichten.

### DONE
- Je Einsatz Q, Zeit für 100 cm³, Schneidenweg je cm³, genutzte Schneide,
  Anteil im Material, größte Spandicke, Leistung (nur mit kc1.1). Fett das
  Beste je Spalte, wo „besser“ eindeutig ist; A und B in ihrer Farbe.
- Ein Klick nimmt die Zeile als B (war sie A, tauschen A und B).

### TEST
- KI, Oberfläche in **beiden** Versionen: `szenario_strategien` grün
  (Zeilen, Fettdruck, Klick), Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-04 planer-vergleich-vollnut

### EINGELESEN
- Manuels Beispiel: Ø 12 mit ae 1,2 / ap 25 statt Vollnut mit ap 3 – der
  Planer (P-2026-09-25-60) sagte bisher nur, was er vorschlägt, nicht, was
  das gegenüber der Vollnut bringt.

### DATEIEN
- `camaddon/schruppwerte.py` (`vergleichszeile()`),
  `camaddon/gui_schruppwerte.py` (Satz unter der Tabelle),
  `camaddon/gui_schnittwerte.py` (gibt die Vollnut der Tabelle mit)
- `help/de|en/schruppwerte.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_schruppwerte.py`, `tests/gui/szenario_schruppwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ø-12-Fräser mit Vollnut 12 / 3 / 120 / 0,05 → „Schruppwerte planen…“ → unter
der Tabelle: „Zum Vergleich: Vollnut (ae 12 mm, ap 3 mm) schafft
17,2 cm³/min – der Vorschlag das 1,3-Fache, mit 24 statt 3 mm Schneide.“

### DONE
- Verglichen wird mit der ersten Vollnut der Tabelle, die vc, fz und ap
  hat; ohne eine solche fehlt der Satz.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_schruppwerte` grün.
- KI, Oberfläche in **beiden** Versionen: `szenario_schruppwerte` grün
  (prüft den Satz), Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-03 version-0-8-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.7.0: Revolverplatz wählen (P-2026-09-25-69), Werkzeuge suchen (-71),
  Werkstoff am Rohteil (-72), Planer vorbelegen (-73), Werkzeugbild
  (P-2026-09-26-01) und der Fix gegen die grundlose Rückfrage (-02).

### DATEIEN
- `package.xml` (0.8.0, Datum)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.8.0.

### DONE
- Version 0.7.0 → 0.8.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-26-02 keine-scheinaenderung

### EINGELESEN
- Beim Ansehen der Werkzeugbilder (P-2026-09-26-01) gefunden: Abbrechen
  fragte „Speichern?“, obwohl nichts geändert war.

### DATEIEN
- `camaddon/werkzeuge.py` (`als_dict`: leere Tabelle „für alle“ wie keine)
- `camaddon/gui_werkzeuge.py` (unverändertes Zahlenfeld schreibt nicht
  zurück)
- `camaddon/werkzeuge_aus_cam.py` (Maße auf 0,0001 mm gerundet)
- `tests/test_werkzeuge.py`, `tests/gui/szenario_aus_cam.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Aus CAM übernehmen“ → „Default“ → OK → wieder öffnen →
jedes Werkzeug einmal anklicken → Abbrechen → das Fenster schließt ohne
Rückfrage.

### DONE
- **Ursache 1:** Das Anzeigen legt für ein Werkzeug ohne Schnittwerte eine
  leere Tabelle „für alle Werkstoffe“ an (damit „+ Einsatz“ etwas hat, an
  das es anhängen kann). Die galt beim Vergleich als Änderung. Jetzt
  zählt eine leere Tabelle „für alle“ wie keine – gespeichert wird sie
  nicht.
- **Ursache 2:** Beim Schließen liest der Dialog das Zahlenfeld mit dem
  Fokus zurück. Das Feld zeigt 12 Stellen; ein längerer Wert (FreeCAD
  rechnet den Durchmesser des Fasenfräsers aus: 10,260512242138308) kam
  gekürzt zurück. Jetzt bleibt der Wert, solange im Feld steht, was es
  beim Füllen zeigte; übernommene Maße werden außerdem auf 0,0001 mm
  gerundet.
- Betraf vor allem Werkzeuge, die nicht im Dialog angelegt wurden – also
  genau die aus „Aus CAM übernehmen“.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` (Ansehen ist
  keine Änderung, eine neue Zeile schon), `test_werkzeuge_aus_cam` grün.
- KI, Oberfläche in **beiden** Versionen: `szenario_aus_cam` (wieder
  öffnen, alle ansehen, Abbrechen ohne Rückfrage) und
  `szenario_werkzeugverwaltung` grün. Vor der Korrektur scheiterte das
  Szenario im Wochen-Build genau daran.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-01 werkzeugbild

### EINGELESEN
- Manuels Wunsch nach einer „übersichtlicheren“ Werkzeugverwaltung, „etwa
  wie die alte von InventorCAM“ – die zeigt zu jedem Werkzeug ein Bild.
- Arbeitsregeln Abschnitt 8: Bilder ohne Text, damit sie in jeder Sprache
  passen (wie das Eingriffsbild, P-2026-09-25-48).

### DATEIEN
- `camaddon/gui_werkzeugbild.py` (neu), `camaddon/gui_werkzeuge.py` (Bild
  rechts neben den Feldern)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json` (Tooltip)
- `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → ein Schaftfräser Ø 12, Schneidenlänge 26,
Gesamtlänge 83 → rechts steht er schlank mit kurzer Schneide; Art auf
„Radiusfräser“ → unten rund; „Fasenfräser“ → spitz; Gesamtlänge leeren →
der Schaft ist gestrichelt.

### DONE
- Schaft, Schneide (mit angedeuteten Wendeln) und Spitze je Art: flach,
  Eckradius, Kugel, 90°-Fase, 118°-Bohrerspitze – maßstäblich, geschätzte
  Maße gestrichelt. Folgt jeder Eingabe.
- **Gefundener Fehler im eigenen Entwurf:** Bei Fasenfräser und Bohrer war
  die Spitze schief (ein Eckpunkt fehlte im Umriss) – am Screenshot
  gesehen, behoben.

### TEST
- KI, Oberfläche in **beiden** Versionen: `szenario_werkzeugverwaltung`
  grün; alle fünf Arten und ein Fräser mit dickerem Schaft als Screenshot
  angesehen (Szenario nur zum Ansehen, nicht eingecheckt).
- Manuel: offen.

### NEXT
- Beim Ansehen gefunden: Das bloße Anzeigen eines Werkzeugs ohne
  Schnittwerte gilt als Änderung (falsche Rückfrage „Speichern?“) –
  eigener Patch.

## P-2026-09-25-74 texte-ueber-und-leer

### EINGELESEN
- „Über das CAM-Addon“ nannte noch den Stand vor dieser Nacht; der Hinweis
  bei leerer Werkzeugliste kannte „Aus CAM übernehmen“ (P-66) nicht.

### DATEIEN
- `translations/de.json`, `translations/en.json` (`ueber.text`,
  `wv.leer`)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Über das CAM-Addon“ nennt Verfahren, Schruppwert-Planer und Schrittweite/
Zustelltiefe; eine leere Werkzeugverwaltung nennt „Neu“ und „Aus CAM
übernehmen“.

### DONE
- Beide Texte deutsch und englisch nachgezogen.

### TEST
- KI: `test_sprache` in beiden Versionen grün (Platzhalter unverändert).
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-73 planer-maschine-vorbelegen

### EINGELESEN
- „Schruppwerte planen“ (P-60): Die Grenzen der Maschine kamen nur auf
  Knopfdruck von einer W-001-Maschine.

### DATEIEN
- `camaddon/schruppwerte.py` (`vorbelegung()`),
  `camaddon/gui_schruppwerte.py` (vorbelegen, grauer Satz „Drehzahl und
  Vorschub von …“)
- `help/de|en/schruppwerte.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_schruppwerte.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit Maschinenobjekt offen, Planer noch nie mit
Maschinenwerten benutzt → Werkzeugverwaltung → „Schruppwerte planen…“ →
Höchstdrehzahl und höchster Vorschub stehen schon da, darunter grau
„Drehzahl und Vorschub von „Testdrehmaschine““.

### DONE
- Vorbelegt wird nur, wenn beide Felder leer sind und genau eine Maschine
  offen ist; sonst bleibt es beim Gemerkten bzw. bei „Von der Maschine“.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_schruppwerte` grün (vier
  Fälle der Vorbelegung).
- KI, Oberfläche in **beiden** Versionen: `szenario_schruppwerte` grün
  (ohne Maschine: Felder leer wie bisher).
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-72 werkstoff-am-rohteil

### EINGELESEN
- „Schnittwerte in den Job“ (P-53) liest den Werkstoff vom Rohteil über die
  Werkstoffnummer der FreeCAD-Karte. Hat das Rohteil keinen, wählt man ihn
  jedes Mal neu – und FreeCADs eigener Vorschlag im Wochen-Build findet die
  Presets nicht.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`nummer_am_rohteil()`, `karte_fuer()`,
  `setze_werkstoff_am_rohteil()`)
- `camaddon/gui_job_schnittwerte.py` (Knopf „Am Rohteil eintragen“)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit Rohteil 1.4301 → „Schnittwerte in den Job“ → oben „1.0503 C45“
wählen → „Am Rohteil eintragen“ erscheint → klicken → darunter steht „Vom
Rohteil des Jobs: 1.0503 C45 …“, der Knopf verschwindet; im Rohteil steht
die FreeCAD-Karte C45; Strg+Z bringt 1.4301 zurück.

### DONE
- Der Knopf erscheint nur, wenn es für den gewählten Werkstoff eine
  FreeCAD-Karte mit derselben Nummer gibt und das Rohteil sie noch nicht
  hat. Eintragen in einer Transaktion.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_job_schnittwerte` grün –
  C45 am Rohteil, Werkstoff des Jobs danach C45, Strg+Z, Nummer ohne Karte.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job` grün,
  Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-71 werkzeuge-suchen

### EINGELESEN
- Manuels Wunsch nach einer Werkzeugverwaltung, die „viel übersichtlicher“
  ist. Nach „Aus CAM übernehmen“ (P-66) wird die Liste schnell lang.

### DATEIEN
- `camaddon/werkzeuge.py` (`passt()`), `camaddon/gui_werkzeuge.py`
  (Suchfeld über der Liste)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge.py`, `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung mit T1 Schaftfräser Ø 12 und T2 Torusfräser Ø 10,5 →
„torus“ ins Suchfeld → nur noch T2 in der Liste, rechts seine Werte → Feld
leeren (×) → beide wieder da.

### DONE
- Jedes Wort muss in Zeile oder Bezeichnung vorkommen, ohne Groß/klein;
  Komma und Punkt gelten gleich, das Ø darf fehlen („ø10.5 hoff“).
- Versteckt die Suche das gewählte Werkzeug, wird das erste gezeigte
  gewählt. Ein neues, kopiertes oder übernommenes Werkzeug, das die Suche
  verstecken würde, leert die Suche – nichts wird unsichtbar bearbeitet.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` grün (sieben
  Suchen).
- KI, Oberfläche in **beiden** Versionen: `szenario_werkzeugverwaltung`
  und `szenario_aus_cam` grün, Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-70 entwurf-stufe-4

### EINGELESEN
- Spezifikation W-001, Abschnitt 9: „Stufe 4 – Werkzeugbahn abfahren und
  Kollision prüfen – eigene Spezifikation, wenn Stufe 3 steht.“ Stufe 3
  steht (P-67, P-69).
- FreeCAD: CAM-Simulator (Materialabtrag), Bahn der Operationen
  (`op.Path.Commands`), Maschinendefinition des Wochen-Builds (Kinematik,
  AxisRole).

### DATEIEN
- `docs/spezifikation_simulation.md` (neu, Entwurf)
- `docs/spezifikation_maschine_aus_baugruppe.md` (Verweis),
  `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel liest den Entwurf und beantwortet die sechs Fragen in Abschnitt 9;
danach ist klar, was 4a baut.

### DONE
- Zielbild (Reichweite, Abfahren, Kollision, Zeit), was es schon gibt,
  Achsstellungen aus der Bahn (lineares Gleichungssystem für 3 Achsen,
  Drehachsen zuerst bei 4/5 Achsen), Stufen 4a–4d, Oberfläche, Grenzen,
  Prüfbarkeit, Fragen, Akzeptanzkriterien 4a.
- Vorschlag: 4a „Reichweite prüfen“ zuerst – schnell gebaut, sofort
  nützlich, und es klärt die Achszuordnung, die alle weiteren Stufen
  brauchen.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels Antworten; dann 4a.

## P-2026-09-25-69 revolverplatz-waehlen

### EINGELESEN
- „Maschine verfahren“ (P-2026-09-25-67): Beim Revolver ist ein Winkel in
  Grad umständlich; gedacht wird in Plätzen (Spezifikation W-001,
  Abschnitt 7a: Plätze P1 … Pn als Werkzeugaufnahmen im Glied des
  Revolvers).

### DATEIEN
- `camaddon/verfahren.py` (`platzstellungen()`, Lagen der Plätze beim
  Öffnen)
- `camaddon/gui_verfahren.py` (Auswahl der Plätze in der Zeile des
  Revolvers)
- `help/de|en/verfahren.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_verfahren.py`, `tests/gui/szenario_verfahren.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit 12 verteilten Revolverplätzen → „Maschine
verfahren“ → in der Zeile T steht rechts „P1“ → „P4“ wählen → T steht auf
−90°, P4 steht, wo P1 stand; zieht man T weiter, zeigt die Auswahl „–“.

### DONE
- Je Platz die Stellung der Revolverachse, in der er dort steht, wo beim
  Öffnen P1 stand – aus dem Winkel der Plätze um die Achse, kürzester Weg.
  Gilt für jede Verteilung, nicht nur gleichmäßige.
- Die Auswahl folgt dem Regler: Steht ein Platz an der Stelle von P1
  (±0,05°), zeigt sie ihn, sonst „–“.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_verfahren` grün – 12
  Plätze P1 … P12, P4 = 90° von P1, nach dem Drehen steht P4 auf 1e-6 mm
  genau, wo P1 stand; Linearachse ohne Plätze.
- KI, Oberfläche in **beiden** Versionen: `szenario_verfahren` grün,
  Screenshot angesehen.
- Manuel: offen – vor allem: Ist „an die Stelle von P1“ die richtige
  Arbeitsstellung, oder soll man sie festlegen können?

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-68 version-0-7-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.6.0: Werkzeug-Controller anlegen (P-65), Aus CAM übernehmen (P-66),
  Maschine verfahren (P-67).

### DATEIEN
- `package.xml` (0.7.0, Beschreibung)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.7.0.

### DONE
- Version 0.6.0 → 0.7.0; die Beschreibung nennt Verfahren und Übernehmen.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-25-67 maschine-verfahren

### EINGELESEN
- Spezifikation W-001, Abschnitt 9, Stufe 3: „Ein Fenster mit einem Regler
  je Betriebsart (Name, Wert, Grenzen); die Baugruppe bewegt sich mit.“
  Abschnitt 4: Auch Gelenke ohne Betriebsart setzt man in Stufe 3 von Hand.
- FreeCAD 1.1.3 und Wochen-Build ausprobiert: Schiebe- und Drehgelenke der
  Assembly haben keinen Sollwert – ihre Stellung ist, wo die Teile stehen.
  Bewegt man alle Bauteile hinter einer Achse, lässt die Assembly die
  Stellung beim Lösen und Neuberechnen stehen; bewegt man nur einen Teil,
  zieht sie sie woanders hin. Ihre Grenzen setzt sie beim Lösen nicht durch.

### DATEIEN
- `camaddon/verfahren.py` (neu), `camaddon/gui_verfahren.py` (neu)
- `camaddon/gui_maschine.py` (`gewaehlte_assembly()` öffentlich, damit
  beide Befehle dieselbe Assembly finden)
- `camaddon/gui_start.py` (Befehl, Werkzeugleiste), `camaddon/hilfe.py`
- `resources/icons/verfahren.svg` (neu), `help/de|en/verfahren.html` (neu)
- `translations/de.json`, `translations/en.json`
- `tests/test_verfahren.py`, `tests/gui/szenario_verfahren.py` (neu)
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/aufbau.md`
  (Module, Stolperstein), `CHATSTART.md`, `README.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit Maschinenobjekt (Z1, X1 mit Grenzen 0 … 200 mm,
S4/C4, T) → Assembly wählen → Werkzeugleiste „Maschine verfahren“ → Zeilen
C4, Z1, X1, T → Regler C4 auf 90° → das Futter dreht sich um 90° → X1 auf
500 tippen → bleibt bei 200 mm stehen → Abbrechen → alles steht wie vorher;
noch einmal öffnen, X1 auf 100, OK → X1 bleibt; Strg+Z → zurück.

### DONE
- Je Achse der Kette eine Zeile: Name (NC-Namen der Betriebsarten ohne die
  Spindel, sonst das Gelenk), Regler (0,1 mm bzw. 0,1°), Zahlenfeld mit
  Einheit, darunter grau die Grenzen oder „ohne Grenze“.
- Stellung gezählt wie am Gelenk (Seite 2 gegenüber Seite 1): Linear
  entlang Z von Seite 1, Dreh als Winkel der X-Achsen um Z. Das Vorzeichen
  hängt davon ab, auf welcher Seite das bewegte Teil steht – geprüft mit
  einem Gelenk, dessen bewegtes Teil Seite 1 ist.
- Bewegt werden alle Bauteile hinter der Achse, gerechnet vom Stand beim
  Öffnen aus – mehrere Achsen hintereinander ohne Fehler, die sich
  aufsummieren (C auf der Wiege A bleibt auf 45°, auch bei A = ±30°).
- OK = ein Schritt Rückgängig; Abbrechen und „Grundstellung“ fahren exakt
  zurück.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_verfahren` grün –
  Drehmaschine (Namen, Grenzen 0 … 200, Revolver fährt mit X1, vier Achsen
  zugleich, Futter um 90°, Stellung nach Lösen und Neuberechnen, exakte
  Grundstellung), Fünfachser (A/C), bewegtes Teil auf Seite 1.
- KI, Oberfläche in **beiden** Versionen: `szenario_verfahren` grün,
  Screenshot angesehen (Fenster mit vier Reglern, X1 an der Grenze).
- Manuel: offen – vor allem, ob die Richtung der Achsen und der
  Nullpunkt so sind, wie er sie an seiner Maschine erwartet.

### NEXT
- Alle Prüfungen, Version 0.7.0, Push. Stufe 4 braucht zuerst eine
  eigene Spezifikation.

## P-2026-09-25-66 aus-cam-uebernehmen

### EINGELESEN
- Wer seine Fräser schon in FreeCAD CAM angelegt hat, müsste sie in der
  Werkzeugverwaltung abtippen.
- FreeCAD 1.1.3 und Wochen-Build ausprobiert: Bibliotheken über
  `cam_assets.list_assets(asset_type="toolbitlibrary")`, Werkzeuge über
  `get_bits()` und `get_bit_no_from_bit()`, Maße am ToolBit-Objekt
  (`ShapeType`, `Diameter`, `Flutes`, `CuttingEdgeHeight`, `Length`,
  `ShankDiameter`, `CornerRadius`, `Material`). Ein leerer Speicher bekommt
  wie in CAM selbst erst die mitgelieferte Bibliothek „Default“
  (`ensure_assets_initialized`).

### DATEIEN
- `camaddon/werkzeuge_aus_cam.py` (neu)
- `camaddon/gui_werkzeuge.py` (Knopf „Aus CAM übernehmen“ mit Menü der
  Bibliotheken, Rückmeldung)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge_aus_cam.py`, `tests/gui/szenario_aus_cam.py` (neu)
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe 2, Entscheidung 19),
  `docs/aufbau.md`, `CHATSTART.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Aus CAM übernehmen“ → „Default (13 Werkzeuge)“ → die
Rückmeldung nennt 5 übernommene Werkzeuge, was schon da war und die Formen,
die nicht gehen (V-Bits, Säge, Taster, Gewindefräser) → in der Liste stehen
T2 Schaftfräser Ø 5, T3 Bohrer Ø 5, T4 Radiusfräser Ø 6, T5 Torusfräser
Ø 6, T10 Fasenfräser; T5 hat Eckradius 1,5, Schneidenlänge 40,
Gesamtlänge 50, Schaft 3, HSS → OK speichert.

### DONE
- Formen: Schaftfräser, Torusfräser, Radiusfräser, Fasenfräser, Bohrer.
  Gravierstichel nicht (kein Spitzenwinkel in der Werkzeugverwaltung),
  ebenso Säge, Gewindefräser, Taster – die Rückmeldung nennt sie.
- Schon da ist, was gleiche Art und gleichen Durchmesser hat und gleiche
  Nummer oder gleichen Namen – so wird auch ein beim letzten Mal
  umnummeriertes Werkzeug nicht doppelt geholt; es behält seine
  Schnittwerte. Die eigene Bibliothek „CAM-Addon“ wird nicht angeboten.
- Vergebene Nummer: die kleinste freie, die auch in der Quelle nicht
  vorkommt.
- Gespeichert wird wie sonst mit OK oder Übernehmen.
- **Gefundene Fehler im eigenen Entwurf:** Die erste Fassung vergab „die
  nächste freie Nummer“ – und schob damit T3, T4, T5 … der Quelle jeweils
  eins weiter. Und ein umnummeriertes Werkzeug kam beim zweiten Holen noch
  einmal. Beides mit der Prüfung gefunden und behoben.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge_aus_cam` grün –
  Bibliothek „Default“, „CAM-Addon“ nicht angeboten, 5 übernommen, T1 schon
  da (behält seine Schnittwerte), T2 vergeben → T14, 7 Formen draußen,
  Werte des Torusfräsers, zweites Holen: nichts neu.
- KI, Oberfläche in **beiden** Versionen: `szenario_aus_cam` grün,
  Screenshots angesehen (Rückmeldung, Liste).
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen, Version 0.7.0.

## P-2026-09-25-65 werkzeug-controller-anlegen

### EINGELESEN
- Der Weg „Loch auffräsen“ (P-61) brauchte einen Werkzeug-Controller, den
  man von Hand anlegt und so benennt, dass der Einsatz im Namen steht –
  ein fehleranfälliger Schritt.
- FreeCAD legt Controller mit `Controller.Create` im **aktiven** Dokument an
  (1.1.3 und Wochen-Build); `cam_assets.get()` liefert je Aufruf ein neues
  ToolBit, das sich einmal anhängen lässt.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`controller_name()`,
  `lege_controller_an()`, `_setze_werte()` aus `setze()` gelöst)
- `camaddon/gui_job_schnittwerte.py` (Knopf „Werkzeug-Controller
  hinzufügen“ mit Menü je Werkzeug und Einsatz)
- `help/de|en/werkzeuge.html` (Knopf; „Schritt für Schritt: vom Katalog in
  den Job“ oben auf der Seite; der Weg „Loch auffräsen“ nutzt den Knopf)
- `translations/de.json`, `translations/en.json`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `README.md` („Was es kann“), `docs/spezifikation_werkzeugverwaltung.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
CAM-Job, Rohteil 1.4301, Werkzeugverwaltung mit dem Ø-12-Fräser (Vollnut,
Schruppen dynamisch) → „Schnittwerte in den Job“ → „Werkzeug-Controller
hinzufügen“ → „T3 Schaftfräser Ø 12 · z 3 · VHM“ → „Vollnut“ → in der
Tabelle steht eine neue Zeile „T3 Vollnut“, Einsatz Vollnut, jetzt
eingestellt 2122 U/min · 318 mm/min; im Baum des Jobs steht der Controller
mit dem Fräser; Strg+Z nimmt ihn zurück.

### DONE
- Menü je Werkzeug (nur solche mit D) mit seinen Einsätzen, die vc und fz
  haben – für den gewählten Werkstoff. Ohne solche: ein grauer Eintrag
  „Kein Werkzeug mit vc und fz“.
- Anlegen: erst alle Werkzeuge an CAM übergeben (das Werkzeug soll auf dem
  gespeicherten Stand in der Bibliothek stehen), dann ToolBit anhängen,
  Controller „T<Nummer> <Einsatz>“ mit der T-Nummer, in den Job, n und vf
  setzen – eine Transaktion. Die Zeile erscheint sofort, der Einsatz ist am
  Namen erkannt.
- Hilfe: „Schritt für Schritt: vom Katalog in den Job“ – sieben Schritte
  vom Werkstoff bis zu Schrittweite und Zustelltiefe im Adaptiv.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_job_schnittwerte` grün –
  neuer Controller „T3 Vollnut“, T3, Werkzeug aus der Bibliothek, 2122 U/min
  und 318 mm/min, Einsatz am Namen erkannt, Strg+Z entfernt Controller und
  Werkzeug.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job` grün
  (Menü → „Vollnut“ ausgelöst), Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen, Version 0.6.1 oder höher.

## P-2026-09-25-64 version-0-6-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.5.1: Schruppwerte planen (P-60), Schrittweite und Zustelltiefe in die
  Operationen (P-61), Gesamtlänge und Schaft (P-62), „rpm“ auf Englisch
  (P-63).

### DATEIEN
- `package.xml` (0.6.0, Beschreibung)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.6.0.

### DONE
- Version 0.5.1 → 0.6.0; die Beschreibung nennt den Planer und die
  Übergabe von Schrittweite und Zustelltiefe.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-25-63 englisch-rpm

### EINGELESEN
- Durchsicht der Werkzeugverwaltung auf Englisch (Werkzeugverwaltung,
  Schruppwerte planen, Strategien vergleichen, Werkstoffe) als Screenshots.

### DATEIEN
- `camaddon/gui_schnittwerte.py`, `camaddon/gui_job_schnittwerte.py`,
  `camaddon/gui_schruppwerte.py` (Einheit der Drehzahl aus den Texten)
- `translations/de.json`, `translations/en.json` (`einheit.drehzahl`)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Sprache Englisch → Werkzeugverwaltung → die Spalte n heißt „n rpm“; in
„Plan roughing values…“ steht hinter „Maximum speed“ „rpm“. Auf Deutsch
bleibt es „U/min“.

### DONE
- Die Einheit „U/min“ stand fest im Code (Tabellenköpfe, Planer) und war
  auch auf Englisch zu sehen – jetzt „rpm“. Sonst fiel beim Durchsehen
  nichts auf.

### TEST
- KI, Oberfläche 1.1.3 auf Englisch (Szenario nur zum Ansehen, nicht
  eingecheckt): Screenshots angesehen. `test_sprache` grün.
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.6.0, Push.

## P-2026-09-25-62 gesamtlaenge-und-schaft

### EINGELESEN
- Spezifikation W-002, Entscheidung 10: Gesamtlänge und Schaft wurden bei
  der Übergabe an CAM geschätzt; die Alternative „zwei Felder“ war als
  leicht nachzurüsten vermerkt. CAM braucht beide für Simulation und
  Kollision.

### DATEIEN
- `camaddon/werkzeuge.py` (Felder `gesamtlaenge`, `schaft`;
  `geschaetzte_laenge()`, `laenge_fuer_cam()`, `schaft_fuer_cam()`)
- `camaddon/uebergabe_werkzeuge.py` (nimmt sie)
- `camaddon/gui_werkzeuge.py` (zwei Felder, grau die Schätzung, Hinweis
  bei zu kurzer Gesamtlänge; der Eckradius steht jetzt zuletzt)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge.py`, `tests/test_uebergabe_werkzeuge.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 5, Stufe 2,
  Entscheidung 10), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Neu → Durchmesser 12, Schneidenlänge 26 → in den leeren
Feldern steht grau „geschätzt: 50“ und „wie D: 12“ → Gesamtlänge 20 → rot
„Die Gesamtlänge (20 mm) ist kürzer als die Schneide (26 mm).“ → Gesamtlänge
83, Schaft-Ø 10 → Speichern und an CAM übergeben → im CAM-Job hat das
Werkzeug Länge 83 und Schaft 10.

### DONE
- Zwei freiwillige Felder; leer gilt die Schätzung wie bisher, und sie
  steht grau im Feld. Ältere Dateien ohne die Felder laden unverändert
  (0 = geschätzt), das Dateiformat bleibt 1.
- Der Eckradius (nur Torusfräser) steht jetzt als letztes Feld – so
  hinterlässt er ausgeblendet keine Lücke.
- Der Text nach der Übergabe sagt „wo die Felder leer sind, geschätzt“.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` (speichern,
  alte Datei ohne Felder, Schätzung mit und ohne Schneidenlänge),
  `test_uebergabe_werkzeuge` (eingetragen 72/8, geschätzt 50/12 im
  ToolBit) grün.
- KI, Oberfläche 1.1.3: `szenario_werkzeugverwaltung` grün, Screenshot
  angesehen.
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.6.0, Push.

## P-2026-09-25-61 zustellung-in-die-operationen

### EINGELESEN
- Manuels Wunsch: „wenn ich ein Loch auffräsen will, dann einmal helikal
  ein Grundloch und dann ebenenweise mit voller Schneide“. In FreeCAD CAM
  macht das die Operation Adaptiv (Helix-Eintauchen bis zur Zustelltiefe,
  dann die Ebene ausräumen) – wenn Schrittweite und Zustelltiefe stimmen.
- FreeCAD 1.1.3 und Wochen-Build ausprobiert: Adaptiv hat `StepOver`
  (ganze Prozent) bzw. `StepOverPercent` (Kommazahl), Tasche und
  Planfräsen `StepOver`, alle `StepDown` – an dem eine Formel aus dem
  SetupSheet hängt.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`zustellung()`, `operationen_mit()`,
  `setze(…, job)` → `Gesetzt`; „MillFacing“ des Wochen-Builds im
  Vorschlag)
- `camaddon/gui_job_schnittwerte.py` (Spalte „Schrittweite ·
  Zustelltiefe“, Haken, Meldung; Spalte „Werkzeug“ kürzer benannt)
- `help/de|en/werkzeuge.html` (Abschnitt „Ein Loch oder eine Tasche
  auffräsen“), `help/de|en/strategien.html` (Verweis darauf)
- `translations/de.json`, `translations/en.json` (dazu die englische
  Meldung ohne „1 tool controllers“)
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe 2 erweitert,
  Entscheidung 18), `docs/aufbau.md` (Modul, drei Stolpersteine),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit Werkzeug-Controller „T3 Schruppen dynamisch“ (Ø-12-Fräser aus der
Bibliothek „CAM-Addon“, Einsatz 1,2 / 25 / 120 / 0,15) und einer Operation
Adaptiv mit diesem Controller → „Schnittwerte in den Job“ → in der Spalte
„Schrittweite · Zustelltiefe“ steht „Adaptiv: 10 % · 25 mm“ → Übernehmen →
Meldung „… dazu Schrittweite und Zustelltiefe in: Adaptiv“ → Adaptiv hat
Schrittweite 10 % und Zustelltiefe 25 mm; Strg+Z nimmt alles zurück.

### DONE
- **Welche Operation was bekommt:** Adaptiv ← „Schruppen dynamisch“ und
  „Schruppen“; Tasche, Taschenform, Planfräsen ← „Schruppen“; Nut ←
  „Vollnut“; Kontur ← nichts (mit ihr wird auch ausgeschnitten, in voller
  Nut). Schrittweite = ae in % von D, abgerundet (1.1.3: ganze Prozent),
  Zustelltiefe = ap.
- **Formel entfernt:** Die Zustelltiefe hängt in FreeCAD an „OpToolDiameter“
  aus dem SetupSheet; ohne das Entfernen stand nach dem Neuberechnen wieder
  12 mm da. Strg+Z bringt die Formel zurück (geprüft).
- Im Dialog zeigt eine Spalte vorher, was wohin kommt (Tooltip: der jetzige
  Wert); ein Haken schaltet es ab und wird gemerkt. Die Meldung nennt die
  Operationen beim Namen – ohne „1 Operationen“.
- Der Vorschlag des Einsatzes kennt jetzt auch „MillFacing“, das
  Planfräsen des Wochen-Builds.
- Hilfe: Schritt für Schritt „Ein Loch oder eine Tasche auffräsen“ mit
  Adaptiv.
- **Gefundene Fehler im eigenen Entwurf:** Zustelltiefe nach dem
  Neuberechnen wieder D (Formel, siehe oben); in 1.1.3 scheitert das
  Anlegen einer Operation ohne Oberfläche, wenn der Job mehrere
  Werkzeug-Controller hat – die Prüfung legt sie vorher an (Stolperstein).

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_job_schnittwerte` grün –
  Adaptiv bekommt 10 % bzw. 10,0 % und 25 mm, Tasche, Kontur und Nut
  bleiben, Nut mit Vollnut 3 mm, 0,88 mm → 7 % (1.1.3) bzw. 7,3 %, die
  Formel ist weg und kommt mit Strg+Z zurück, ohne Job bleiben die
  Operationen.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job`
  grün, Screenshots angesehen.
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.6.0, Push.

## P-2026-09-25-60 schruppwerte-planen

### EINGELESEN
- Manuels Wunsch zur Werkzeugverwaltung: „den maximalen Spanvolumen mit
  diesem Fräser erreichen“ – Ø 12 mit ae 1,2 / ap 25 / fz 0,15 statt Vollnut
  mit ap 3 / fz 0,05. Spezifikation W-002, Abschnitt 10, Stufe 3.
- W-001: Kennwerte der Maschine – Spindel „Drehzahl“ (U/min), Linearachse
  „VorschubMax“ (mm/min); die Werkzeugaufnahme verweist auf die Spindel,
  die das Werkzeug antreibt.

### DATEIEN
- `camaddon/schruppwerte.py` (neu: Planen, Grenzen der Maschine)
- `camaddon/gui_schruppwerte.py` (neu: Dialog)
- `camaddon/gui_schnittwerte.py` (Knopf „Schruppwerte planen…“,
  `einsatz_hinzufuegen()`)
- `camaddon/hilfe.py`, `help/de|en/schruppwerte.html` (neu)
- `translations/de.json`, `translations/en.json`
- `tests/test_schruppwerte.py`, `tests/gui/szenario_schruppwerte.py` (neu)
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe 3 gebaut,
  Entscheidungen 13–17), `docs/aufbau.md`, `CHATSTART.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Werkstoff 1.0503 (C45) → Schaftfräser Ø 12, z 3,
Schneidenlänge 26 mit Vollnut 12 / 3 / vc 120 / fz 0,05 → „Schruppwerte
planen…“ → vc 120, Spandicke 0,05, ap 24, ae höchstens 10 % stehen da; die
grüne Zeile ae 1,20 mm hat fz 0,083, vf 796, Q 22,9 und darunter steht,
dass die Grenze von 10 % nicht breiter zulässt → Spindelleistung 1,5 kW →
der Vorschlag rückt auf ae 0,88 mm, „Spindel voll ausgelastet“ → Feld
leeren → „Als Einsatz für 1.0503 übernehmen“ → in der Tabelle steht eine
neue Zeile „Schruppen dynamisch“ 1,2 / 24 / 120 / 0,083, und oben „Eigene
Werte für 1.0503“.

### DONE
- **Rechnen** (`schruppwerte.py`, ohne Oberfläche): je ae von 2 bis 50 % von
  D das fz für die gewünschte Spandicke (fz = h / sin φ), vf, Q, Leistung
  und Drehmoment aus kc1.1. Grenzen: ae in % von D (die Grenze selbst wird
  eine Zeile), Höchstdrehzahl (n gekappt, vc sinkt, wird gesagt),
  Höchstvorschub (vf gekappt, der Span wird dünner, wird gesagt),
  Spindelleistung × 80 % (die Grenze wird auf 0,01 mm gesucht und eine
  Zeile). Vorschlag = größtes Q innerhalb aller Grenzen, dazu der Grund,
  warum nicht breiter.
- **Ausgang** ist die gewählte Zeile, wenn sie schruppt und vc und fz hat,
  sonst dynamisch vor Vollnut vor Schruppen – eine Schlicht-Zeile taugt
  nicht als Spandicke.
- **Maschine:** Knopf „Von der Maschine“ (nur sichtbar, wenn ein offenes
  Dokument eine W-001-Maschine mit Werten hat): Drehzahl der Spindel, die
  ein Werkzeug antreibt (sonst die größte), kleinster Höchstvorschub der
  Linearachsen. Die Grenzen merkt sich der Planer.
- **Übernehmen:** die gewählte Zeile als „Schruppen dynamisch“, abgerundet;
  ohne eigene Werte für den Werkstoff werden sie angelegt (der Knopf sagt
  es: „Als Einsatz für 1.0503 übernehmen“).
- Hilfeseite mit Formel, Feldern, Tabelle, Beispiel und dem, was der Planer
  nicht weiß (Werkzeugsteifigkeit, Drehmoment).
- Entscheidungen 13–17 in der Spezifikation, zur Besprechung.
- **Gefundener Fehler im eigenen Entwurf:** Die Schlüssel der Felder
  standen als Variablen in `tr()` – test_sprache fand sie nicht. Jetzt
  feste Texte beim Aufruf.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_schruppwerte` grün –
  Vorschlag an der ae-Grenze (fz 0,0833, vf 795,8, Q 22,92), Grenze
  zwischen den Stufen (11 %), ohne Grenze bis D/2, Drehzahl-, Vorschub- und
  Leistungsgrenze (C45, 1,5 kW: Zeile an der Grenze, 0,01 mm mehr wäre zu
  viel), ohne kc1.1 keine Leistungsprüfung, Ausgangszeile, Grenzen einer
  Drehmaschine mit angetriebenem Werkzeug.
- KI, Oberfläche in **beiden** Versionen: `szenario_schruppwerte` grün,
  Screenshots angesehen (Vorschlag, Leistungsgrenze, Maschine am Anschlag,
  übernommen).
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.6.0, Push.

## P-2026-09-25-59 stand-nach-der-nacht

### EINGELESEN
- Arbeitsregeln Abschnitt 10: Zum Abschluss den Snapshot auf den Stand
  bringen, Erledigtes heraus, Links prüfen.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Nächster Schritt: W-002 Stufen 1 und 2,
  Installation)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer den Snapshot liest, weiß, was auf Manuels Test wartet und wo die
Klickwege stehen.

### DONE
- Nächster Schritt nennt W-002 Stufen 1 und 2 (Klickwege P-46 bis -53) und
  die Installationszeile nach dem Öffentlichstellen (T-005).
- Stand dieser Nacht: P-2026-09-25-43 bis -59, Version 0.5.1, alle Prüfungen
  in 1.1.3 und im Wochen-Build grün (54 ok, 1 übersprungen: Export gibt es
  in 1.1.3 nicht).

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels Rückmeldung zu W-002 und den Entscheidungen; Repository
  öffentlich stellen (T-005).

## P-2026-09-25-58 version-0-5-1

### EINGELESEN
- Arbeitsregeln Abschnitt 4: Korrektur → letzte Stelle. Neu seit 0.5.0:
  Update-Suche ohne Git (P-57).

### DATEIEN
- `package.xml` (0.5.1)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.5.1.

### DONE
- Version 0.5.0 → 0.5.1.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-25-57 update-ohne-git

### EINGELESEN
- Lücke aus P-2026-09-25-43: Eine mit der Zeile aus dem README (ohne Git)
  installierte Kopie meldete neue Versionen nicht selbst – nur der
  Addon-Manager zeigte sie. Die Update-Suche beim Start sagte bei
  „kein Git-Ordner“ nichts.

### DATEIEN
- `camaddon/aktualisierung.py` (ohne Git: Version per HTTPS aus der
  package.xml auf GitHub, Update per `installieren.py`; `KEIN_GIT_ORDNER`
  entfällt)
- `installieren.py` (`ziel=`: genau dieser Ordner)
- `camaddon/gui_aktualisierung.py` (Zweig „kein Git-Ordner“ entfällt)
- `translations/de.json`, `translations/en.json` (`update.kein_git_ordner`
  entfällt; Tooltip und Fehlertext nennen beide Wege)
- `README.md`, `CHATSTART.md`, `docs/aufbau.md`
- `tests/test_aktualisierung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Mit der Zeile aus dem README installiert (öffentliches Repository): Gibt es
auf GitHub eine höhere Version, fragt FreeCAD beim nächsten Start „Jetzt
aktualisieren?“; nach dem Klick und einem Neustart läuft die neue Version.

### DONE
- Ohne `.git` im Addon-Ordner liest die Suche
  `https://raw.githubusercontent.com/…/main/package.xml` (Zeitlimit wie bei
  Git) und vergleicht die Versionen wie bisher Zahl für Zahl. Fehler (kein
  Netz, privat = 404) ergeben `FEHLER` wie bei Git: beim Start nur eine
  Zeile im Report-Fenster, von Hand ein Fenster.
- „Jetzt aktualisieren“ ohne Git lädt `installieren.py` **aus dem
  Addon-Ordner** und ersetzt den Ordner durch das ZIP von GitHub – dieselbe
  Datei und derselbe sichere Tausch wie bei der Installation.
- Keine neue Ausnahme von „keine Aufrufe externer Programme“: HTTPS läuft
  über Pythons urllib.

### TEST
- KI, FreeCADCmd in beiden Versionen: `test_aktualisierung` (neu: ohne Git
  gleiche Version, neue Version, Update per ZIP, danach aktuell, GitHub
  nicht erreichbar; die Git-Fälle wie bisher), `test_installieren`,
  `test_sprache` grün.
- KI, Oberfläche (Wochen-Build): `szenario_update`, `szenario_erster_start`
  grün.
- Der Weg gegen das echte GitHub geht erst, wenn das Repository öffentlich
  ist (T-005).

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-25-56 entscheidungen-stufe-2

### EINGELESEN
- Manuel: „teil mir deine Entscheidungen mit, die kann man morgen ja nochmal
  besprechen“. Beim Bauen von Stufe 2 (P-52, P-53) sind vier dazugekommen.

### DATEIEN
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 11, Entscheidungen
  9 bis 12)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Alle Entscheidungen zu W-002 stehen mit Alternative in Abschnitt 11 der
Spezifikation.

### DONE
- Eigene Bibliothek „CAM-Addon“, vollständig ersetzt; Gesamtlänge und Schaft
  geschätzt; Eintauchvorschub ⅓; Einsatz-Vorschlag nach Name, dann
  Operation.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-25-55 version-0-5-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.4.0: Übergabe an CAM (P-52), Schnittwerte in den Job (P-53).

### DATEIEN
- `package.xml` (0.5.0, Beschreibung)
- `README.md` („Was es kann“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.5.0.

### DONE
- Version 0.4.0 → 0.5.0 für P-2026-09-25-52 bis -54.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-25-54 gui-teile-gemeinsam

### EINGELESEN
- Beim Bauen von W-002 aufgefallen (Arbeitsregeln: notieren, eigener
  Patch, möglichst gleich danach): `_fett`, `_knopf`, `_mit_einheit`, die
  rote Hinweiszeile und das Grau für gerechnete Werte standen in bis zu
  vier Modulen der Werkzeugverwaltung.

### DATEIEN
- `camaddon/gui_teile.py` (neu)
- `camaddon/gui_werkzeuge.py`, `camaddon/gui_werkstoffe.py`,
  `camaddon/gui_schnittwerte.py`, `camaddon/gui_job_schnittwerte.py`
- `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nichts sichtbar anders: Werkzeugverwaltung, Werkstoffe, Vergleich und
„Schnittwerte in den Job“ sehen aus und verhalten sich wie vorher.

### DONE
- Reines Zusammenlegen. Bewusst nicht angefasst: die ähnlichen Helfer in
  `gui_maschine.py` und `gui_details.py` (W-001) – andere Signaturen, und
  dort gibt es keinen Anlass, etwas zu ändern.
- Gefunden von ruff: Eine Schleifenvariable `knopf` hätte die neue Funktion
  `knopf()` verdeckt – umbenannt.

### TEST
- KI, Oberfläche (Wochen-Build): alle sechs Szenarien der
  Werkzeugverwaltung grün, Screenshot verglichen.

### NEXT
- Version 0.5.0, alle Prüfungen, Push.

## P-2026-09-25-53 schnittwerte-in-den-job

### EINGELESEN
- W-002, Spezifikation Abschnitt 10, Stufe 2, zweiter Teil: In FreeCAD
  1.1.3 – Manuels Version – kommen die Schnittwert-Vorschläge am Werkzeug
  nicht an (P-2026-09-25-52). Damit er die Werte trotzdem in einen Job
  bekommt, setzt das Addon die Werkzeug-Controller selbst.

### DATEIEN
- `camaddon/job_schnittwerte.py` (neu)
- `camaddon/gui_job_schnittwerte.py` (neu: Befehl und Dialog)
- `camaddon/gui_werkzeuge.py` (`werkstoffe_anbieten()` als Funktion, damit
  der neue Dialog dieselbe Werkstoff-Auswahl hat)
- `camaddon/gui_start.py` (Befehl, Werkzeugleiste)
- `resources/icons/schnittwerte_job.svg` (neu)
- `help/de|en/werkzeuge.html` (Abschnitt „Schnittwerte in den Job“)
- `translations/de.json`, `translations/en.json`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
  (neu)
- `docs/spezifikation_werkzeugverwaltung.md`, `docs/aufbau.md`
  (Module, Stolperstein), `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
CAM-Job mit Rohteil-Werkstoff X5CrNi18-10 und einem Werkzeug-Controller
„T3 Schruppen dynamisch“ mit dem Ø-12-Fräser aus der Bibliothek „CAM-Addon“
→ Werkzeugleiste „Schnittwerte in den Job“ → Werkstoff 1.4301 ist gewählt,
der Einsatz „Schruppen dynamisch“ vorgeschlagen, n 3183 und vf 1432 stehen
da → Übernehmen → der Werkzeug-Controller hat diese Werte; Strg+Z nimmt sie
zurück.

### DONE
- **Werkstoff vom Rohteil:** `Stock.ShapeMaterial` (in 1.1.3 und im
  Wochen-Build vorhanden) → Werkstoffnummer → Werkstoff der
  Werkzeugverwaltung; sonst „Alle Werkstoffe“, im Dialog änderbar.
- **Werkzeug zum TC:** über die ToolBit-ID `camaddon_<Kennung>` (steht nach
  der Übergabe im ToolBit, Eigenschaft `ToolBitID`), sonst über T-Nummer
  und Durchmesser. Fremde Werkzeuge: „– nicht in der Werkzeugverwaltung“,
  nicht wählbar, bleiben unberührt.
- **Einsatz vorschlagen:** Name des TC enthält den Namen einer Zeile, sonst
  nach der Operation, die den TC benutzt (Adaptiv → dynamisch, Tasche und
  Planfräsen → Schruppen, Kontur → Schlichten, Nut → Vollnut, Bohren →
  Bohren), sonst die erste Zeile. Zeilen ohne vc/fz werden nicht
  vorgeschlagen („– nicht ändern“).
- **Setzen:** Drehzahl, Vorschub, Eintauchvorschub = ⅓ (wie FreeCADs
  Vorgabe für Presets), beim Bohrer der volle Vorschub; alles in **einer**
  Transaktion (Arbeitsregeln Abschnitt 7: Strg+Z muss gehen). Ohne vc/fz
  wird nichts gesetzt, lieber als 0 U/min.
- Befehl aktiv, sobald das Dokument einen CAM-Job hat.
- **Gefundene Fehler im eigenen Entwurf:** Die Prüfung hing von der
  eingestellten Sprache ab (der TC-Name ist deutsch) – setzt jetzt Deutsch.
  In 1.1.3 stand „OK“ hinter einem Fortschrittsbalken ohne Zeilenende und
  wurde nicht erkannt – Leerzeile davor, als Stolperstein notiert.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_job_schnittwerte` grün –
  echter Job mit Quader, Rohteil-Werkstoff 1.4301, TC mit Werkzeug aus der
  Bibliothek und TC mit fremdem Bohrer (T7, Ø 8,5), Vorschläge, Setzen
  (2122 U/min, 318 und 105 mm/min; Bohrer 2996 U/min, 599 mm/min
  senkrecht), unvollständiger Einsatz übersprungen, Strg+Z.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job` grün.
  Screenshot angesehen.
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.5.0, Push. Dann Manuels Rückmeldung.

## P-2026-09-25-52 werkzeuge-an-cam

### EINGELESEN
- W-002, Spezifikation Abschnitt 10, Stufe 2 (Übergabe an CAM). Manuel:
  „mach so viel fertig wie du kannst“ – ohne Übergabe bleibt die
  Werkzeugverwaltung ein Rechner neben CAM.

### DATEIEN
- `camaddon/uebergabe_werkzeuge.py` (neu)
- `camaddon/gui_werkzeuge.py` (Knopf „Speichern und an CAM übergeben“,
  Rückmeldung)
- `help/de|en/werkzeuge.html` (Abschnitt „An CAM übergeben“)
- `translations/de.json`, `translations/en.json`
- `tests/test_uebergabe_werkzeuge.py`, `tests/gui/szenario_an_cam.py` (neu)
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe 2: was gebaut ist),
  `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Speichern und an CAM übergeben“ → Rückmeldung
„Übergeben: …“; danach in einem CAM-Job „Werkzeug hinzufügen“ → Bibliothek
„CAM-Addon“ zeigt die Werkzeuge mit ihren T-Nummern und Durchmessern. Im
Wochen-Build schlägt der Knopf für Vorschub und Drehzahl im
Werkzeug-Controller bei Rohteil-Werkstoff X5CrNi18-10 unsere Werte für
1.4301 vor.

### DONE
- **FreeCAD-Check:** 1.1.3 und der Wochen-Build haben dieselbe
  Asset-Verwaltung (`Path.Tool.camassets.cam_assets`), dasselbe Format für
  ToolBits (`.fctb`, Version 2) und Bibliotheken (`.fctl`). Nur der
  Wochen-Build kennt „Presets“ und behält unbekannte Schlüssel beim
  Speichern (`_extra_attrs`). FreeCADs Werkstoffkarten findet das Addon
  über die Werkstoffnummer (`PhysicalProperties["MaterialNumber"]`), etwa
  1.4301 → „X5CrNi18-10“.
- **Übergabe:** je Werkzeug ein ToolBit `camaddon_<Kennung>` (Form nach Art:
  Endmill, Bullnose, Ballend, Chamfer, Drill; Diameter, Flutes,
  CuttingEdgeHeight, Material, SpindleDirection, Chipload aus der ersten
  Zeile „für alle“), dazu die Bibliothek „CAM-Addon“ mit den T-Nummern.
  Geschrieben über `cam_assets.add_raw` – dort, wo der Benutzer seine
  CAM-Werkzeuge eingestellt hat.
- **Presets** (je Einsatz mit vc oder fz): Werkstoff-Hinweis mit UUID der
  FreeCAD-Werkstoffkarte gleicher Nummer, sonst mit dem Kurznamen;
  Bearbeitungsart nach Einsatz; Notiz mit ae und ap. „Für alle“ ohne
  Werkstoff-Hinweis = gilt für jeden Werkstoff.
- **Ersetzen statt anhäufen:** Eine neue Übergabe schreibt alle ToolBits neu
  und entfernt `camaddon_…`-Werkzeuge, die es in der Werkzeugverwaltung nicht
  mehr gibt. Fremde Werkzeuge bleiben.
- **Annahmen** (in Rückmeldung und Hilfe genannt): Gesamtlänge =
  Schneidenlänge + 2 × D (mindestens 3 × D), Schaft = D, Eckradius ohne
  Angabe = D/10, Fasenfräser 90°, Bohrer 118°.
- Knopf **„Speichern und an CAM übergeben“** unten links; speichert zuerst
  (die Übergabe zeigt immer den gespeicherten Stand). Rückmeldung je
  Version: Wochen-Build mit Anzahl der Vorschläge und wo man sie findet,
  1.1.3 mit dem Satz, dass Schnittwerte erst mit der nächsten Version
  übernommen werden.
- Bewusst noch nicht: Werkzeug-Controller eines Jobs direkt setzen (für
  1.1.3), Felder für Gesamtlänge und Schaft.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_uebergabe_werkzeuge` grün –
  FreeCAD lädt Bibliothek (T3, T5, T7) und Werkzeuge mit Durchmesser,
  Schneiden, Schneidenlänge, Eckradius, Schneidstoff; ohne Durchmesser
  übersprungen; zweite Übergabe entfernt den gelöschten, das fremde bleibt.
  Im Wochen-Build zusätzlich: vier Presets am Fräser, und FreeCADs eigener
  Vorschlag (`FeedsSpeeds.resolve`) liefert für 1.4301/Nut vc 80 und für
  andere Werkstoffe 120 bei 3183 U/min.
- KI, Oberfläche in beiden Versionen: `szenario_an_cam` grün, Rückmeldungen
  angesehen.
- Manuel: offen – vor allem, ob die Bibliothek im Job so erscheint, wie er
  sie erwartet.

### NEXT
- Werkzeug-Controller eines Jobs aus der Tabelle setzen (1.1.3) – oder
  Manuels Rückmeldung.

## P-2026-09-25-51 version-0-4-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: Ein Push mit neuer Funktion zählt die mittlere
  Stelle der Version hoch. Die Werkzeugverwaltung (P-46 bis P-50) ist neu.

### DATEIEN
- `package.xml` (Version 0.4.0, Beschreibung nennt die Werkzeugverwaltung)
- `README.md` (Abschnitt „Was es kann“)
- `docs/STATUS_SNAPSHOT.md` (nächster Schritt: Manuels Test von W-002)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.4.0, und die
Update-Suche meldet 0.4.0 als neue Version.

### DONE
- Version 0.3.9 → 0.4.0 für alle Patches seit dem letzten Push
  (P-2026-09-25-43 bis -50).
- README: kurze Liste, was das Addon kann – für Tester, sobald das
  Repository öffentlich ist.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen (Ergebnis im
  Bericht an Manuel).

### NEXT
- Push; danach W-002 Stufe 2 oder Manuels Rückmeldung.

## P-2026-09-25-50 werkstoffe-eigene

### EINGELESEN
- W-002, Spezifikation Abschnitt 4: eigene Werkstoffe; mitgelieferte
  schreibgeschützt, „Als eigenen kopieren“.

### DATEIEN
- `camaddon/gui_werkstoffe.py` (neu: Fenster „Werkstoffe“ und
  „Werkstoff bearbeiten“)
- `camaddon/gui_werkzeuge.py` (Knopf „Werkstoffe…“, Wahl übernehmen)
- `help/de|en/werkstoffe.html` (Abschnitt „Die ganze Liste und eigene
  Werkstoffe“)
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_werkstoffe.py` (neu)
- `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Werkstoffe…“ → „Neu…“ → Kurzname „Buche“, Gruppe
„Holz“ tippen, ISO N, OK → „Buche“ steht kursiv oben in der Liste; Fenster
schließen → in der Werkzeugverwaltung ist „Buche · Holz“ gewählt, und nach OK
und Wiederöffnen ist sie noch da.

### DONE
- **Fenster „Werkstoffe“:** alle Werkstoffe als Tabelle (ISO-Kästchen,
  Nummer, Kurzname, Gruppe mit Zustand, Härte, alte Namen), Suche wie in
  der Auswahl, Filter nach ISO-Gruppe, darunter alle Angaben des gewählten
  (mit kc1.1/mc, falls bekannt). Eigene kursiv ganz oben.
- **Eigene Werkstoffe:** Neu…, Als eigenen kopieren, Bearbeiten… (auch
  Doppelklick), Löschen (Rückfrage; nennt die Werkzeuge mit eigenen
  Schnittwerten dafür – die gehen mit). Mitgelieferte schreibgeschützt.
- **Bearbeiten:** Kurzname Pflicht (OK gesperrt, Hinweis am Feld); Gruppe
  und Zustand aus der Liste oder frei getippt – ein Text aus der Liste wird
  als Schlüssel gespeichert und folgt so der Sprache. Zusammensetzung,
  Härte und Zugfestigkeit werden im Format der Oberfläche gezeigt und mit
  Punkt gespeichert, wie in der mitgelieferten Liste.
- Wählt man im Fenster einen Werkstoff und schließt es, ist er auch in der
  Werkzeugverwaltung gewählt. Gespeichert wird mit deren OK/Übernehmen.
- **Gefundene Fehler im eigenen Entwurf:** Die ISO-Spalte zeigte Kästchen
  und Buchstaben doppelt; das Bearbeiten-Feld zeigte „1.45–1.60“ statt
  „1,45–1,60“.

### TEST
- KI, Oberfläche (Wochen-Build): `szenario_werkstoffe` grün – Suche „1.23“
  (6 Treffer), Filter S (3), Kopie, Bearbeiten mit Komma → gespeichert mit
  Punkt, Neu mit Pflichtfeld, Löschen mit Rückfrage samt Schnittwerten,
  Wahl wandert in die Werkzeugverwaltung, OK speichert. Screenshots
  angesehen.
- Manuel: offen.

### NEXT
- Alle Prüfungen in beiden Versionen, Version 0.4.0, Push.

## P-2026-09-25-49 strategien-vergleichen

### EINGELESEN
- W-002, Spezifikation Abschnitt 7 und viertes Akzeptanzkriterium aus
  Abschnitt 12. Manuels Beispiel: Ø 12, ae 1,2 / ap 25 / fz 0,15 statt
  ae 100 % / ap 3 / fz 0,05 – „geht schneller, weniger Verschleiß … dass
  man im Nachhinein mit den Werten auch eine Beurteilung für verschiedene
  Strategien herausziehen kann“.

### DATEIEN
- `camaddon/schnittdaten.py` (Schneidenweg je cm³, spezifische
  Schnittkraft, Schnittleistung, Kennzahlen, Urteil)
- `camaddon/gui_strategie.py` (neu: Dialog mit Balken und Urteil)
- `camaddon/gui_schnittwerte.py` (Knopf „Strategien vergleichen…“,
  Werkstoff für die Leistung)
- `camaddon/gui_werkzeuge.py`, `camaddon/gui_zahlen.py` (`dezimal()` jetzt
  gemeinsam in gui_zahlen – gui_strategie braucht es auch, ein Import aus
  gui_werkzeuge wäre ein Kreis)
- `camaddon/hilfe.py`, `help/de|en/strategien.html` (neu),
  `help/de|en/schnittwerte.html` (Verweis darauf)
- `translations/de.json`, `translations/en.json`
- `tests/test_schnittdaten.py`, `tests/gui/szenario_strategien.py` (neu)
- `docs/aufbau.md` (Module, drei neue Stolpersteine), `CHATSTART.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Ø-12-Fräser mit Vollnut und Schruppen dynamisch →
„Strategien vergleichen…“ → das Urteil sagt, dass dynamisches Schruppen
2,5-mal so viel je Minute abträgt und jede Stelle der Schneide 12,2-mal
weniger Weg durchs Material fährt, und warum (25 statt 3 mm Schneide,
10 statt 50 % der Umdrehung im Material).

### DONE
- **Kennzahlen** je Einsatz: Q, Zeit für 100 cm³, Schneidenweg je cm³,
  genutzte Schneide (ap von der Schneidenlänge), Anteil der Umdrehung im
  Material, größte Spandicke, Schnittleistung und Drehmoment (nur mit
  kc1.1 des Werkstoffs).
- **Schneidenweg je cm³** = D · φ / (2 · ae · ap · fz · z) – Herleitung im
  Docstring und auf der Hilfeseite, ausdrücklich als Faustregel (gleiches
  vc angenommen).
- **Dialog:** A (orange) gegen B (blau), je Kennzahl zwei Balken mit
  Wert; Vorwahl Vollnut gegen Schruppen dynamisch, sonst die ersten beiden.
  Darunter das **Urteil in Sätzen**, die Namen in der Farbe ihres Balkens:
  wer mehr abträgt und um welchen Faktor, wie viel weniger (oder mehr)
  Schneidenweg, warum (genutzte Schneide, Eingriff), Leistung, zu dünner
  Span. Nur Aussagen, die die Zahlen tragen; unter 10 % Unterschied „etwa
  gleich“.
- **Hilfeseite „Strategien vergleichen“:** die Zahlen, warum der
  Schneidenweg, Manuels Beispiel als Tabelle, was daraus folgt
  (Konturen/Taschen dynamisch = „Adaptiv“ in FreeCAD CAM, Löcher: erst
  helikal ein Grundloch, dann ebenenweise mit großem ap; Vollnut nur wo
  nötig; Schlichten mit voller Wandhöhe), Grenzen der Faustregel.
- **Gefundener Fehler im eigenen Entwurf:** Der Kopf des Vergleichs zeigte
  „Werkstoff: 1,0503“ – `dezimal()` hielt die Werkstoffnummer für eine
  Kommazahl. Werkstofftexte laufen jetzt nie durch `dezimal()`; das
  Szenario prüft es. Als Stolperstein in docs/aufbau.md.
- Bewusst nicht: ein Standzeitmodell (Taylor) – dafür fehlen die Werte
  (Entscheidung 6 der Spezifikation).

### TEST
- KI, FreeCADCmd (Wochen-Build): `test_schnittdaten` (Schneidenweg 3,49 und
  0,29 m, Kennzahlen, Urteil mit Faktoren 2,5 und 12,2, unabhängig von der
  Reihenfolge, Leistung mit kc1.1, unvollständige Werte), `test_sprache`,
  `test_hilfe` grün.
- KI, Oberfläche (Wochen-Build): `szenario_strategien` grün – Vorwahl,
  Urteil, Werte, Kopf mit „1.0503“, zweiter Vergleich Schlichten gegen
  Vollnut. `szenario_schnittwerte` weiter grün. Screenshots angesehen.
- Manuel: offen.

### NEXT
- Eigene Werkstoffe anlegen (Spezifikation Abschnitt 4).

## P-2026-09-25-48 eingriff-im-bild

### EINGELESEN
- W-002, Spezifikation Abschnitt 6.2: Bild des Eingriffs, Werte zur
  gewählten Zeile, Spandicke ausgleichen; drittes Akzeptanzkriterium aus
  Abschnitt 12. Arbeitsregeln Abschnitt 8: „Zeigen statt beschreiben“,
  Animationen ohne Text.

### DATEIEN
- `camaddon/schnittdaten.py` (Eingriffswinkel, größte und mittlere
  Spandicke, fz für eine gewünschte Spandicke, Mindestspandicke für den
  Hinweis)
- `camaddon/gui_eingriff.py` (neu: das Bild)
- `camaddon/gui_schnittwerte.py` (Bild, Werte in Worten, Ausgleich,
  Hinweis „Span zu dünn“)
- `help/de|en/schnittwerte.html` (Abschnitt „Eingriff und Spandicke“)
- `translations/de.json`, `translations/en.json`
- `tests/test_schnittdaten.py`, `tests/gui/szenario_schnittwerte.py`
- `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In der Zeile „Schruppen dynamisch“ des Ø-12-Fräsers ae 1,2 tippen → das Bild
zeigt einen schmalen roten Bogen, daneben „Eingriff 37° – jeder Zahn ist
10 % der Umdrehung im Material“; bei „Vollnut“ ist der Bogen ein Halbkreis
und es steht 180° da.

### DONE
- **Bild** (ohne Text): links von oben Fräser, Material und roter
  Eingriffsbogen, Vorschubpfeil; bei der Vollnut Material auf beiden
  Seiten. Rechts von der Seite Schaft, Schneide mit angedeuteten Wendeln,
  Werkstück so hoch wie ap und rot der arbeitende Teil der Schneide.
  Schneidenlänge unbekannt: Schneide gestrichelt.
- **In Worten daneben:** Eingriffswinkel und Anteil der Umdrehung, ae in %
  von D, ap in × D und in % der Schneide, größte und mittlere Spandicke.
- **Spandicke ausgleichen** (nur bei ae < D/2): Feld „gewünscht“ mit der
  jetzigen größten Spandicke vorbelegt, daneben das fz, das die
  gewünschte ergibt, Knopf „fz übernehmen“. Entscheidung: kein Knopf
  „fz ausgleichen“ ohne Zielwert – der würde fz bei jedem Druck weiter
  anheben. Mit Zielwert ist der Knopf beliebig oft ohne Überraschung.
- **Hinweis**, wenn die größte Spandicke unter 0,01 mm liegt (Schneide
  reibt).
- Beim Bohrer kein Bild und keine Eingriffswerte.
- **Gefundener Fehler im eigenen Entwurf:** Das Feld für die Spandicke war
  zu schmal und zeigte „090“ statt „0,090“.

### TEST
- KI, FreeCADCmd (Wochen-Build): `test_schnittdaten` mit Eingriffswinkel
  (180°, 90°, 36,87°), Spandicken und Ausgleich grün.
- KI, Oberfläche (Wochen-Build): `szenario_schnittwerte` grün – Werte im
  Text, Ausgleich 0,1 mm → fz 0,1667, Vollnut ohne Ausgleich. Bilder für
  dynamisch und Vollnut angesehen.
- Manuel: offen.

### NEXT
- Strategien vergleichen (Spezifikation Abschnitt 7).

## P-2026-09-25-47 schnittwerte-je-werkstoff

### EINGELESEN
- W-002, Spezifikation Abschnitt 6 (Schnittwerte je Werkstoff, Einsätze,
  Formeln) und das zweite Akzeptanzkriterium aus Abschnitt 12.
- Manuel: „wenn ich vc eingeben will, vc haben“, „für jeden Werkstoff einzeln
  einstellbar … auch so, dass man für alle die Schnittwerte gleich setzen
  kann“, „ae und ap … als Tabelle“.

### DATEIEN
- `camaddon/werkzeuge.py` (Einsatz, Einsatzarten, Vorlagen, Schnittwerte je
  Werkstoff am Werkzeug, Speichern)
- `camaddon/schnittdaten.py` (neu: n, vf, Q)
- `camaddon/gui_schnittwerte.py` (neu: Tabelle, Zustand, Knöpfe, Hinweise)
- `camaddon/gui_werkzeuge.py` (Formular in zwei Spalten, Tabelle darunter,
  Fenster größer)
- `camaddon/hilfe.py`, `help/de|en/schnittwerte.html` (neu)
- `translations/de.json`, `translations/en.json`
- `tests/test_schnittdaten.py` (neu), `tests/test_werkzeuge.py`,
  `tests/gui/szenario_schnittwerte.py` (neu)
- `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Schaftfräser Ø 12 (3 Schneiden) wählen, Werkstoff
„Alle Werkstoffe“, „+ Einsatz“ → Vollnut, ap 3, vc 120, fz 0,05 eintragen →
grau daneben n 3183, vf 477, Q 17,2; Werkstoff 1.4301 wählen → dieselben
Werte grau und „Eigene Werte für 1.4301 anlegen“; danach vc 80 → n 2122,
und bei C45 stehen weiter 120.

### DONE
- **Tabelle je Einsatz:** Einsatz (Name änderbar), ae, ap, vc, fz
  eingegeben; n, vf, Q gerechnet und grau. Beim Bohrer ohne ae/ap, dafür f je
  Umdrehung (gespeichert wird fz = f / z, damit überall dieselbe Formel
  gilt).
- **„+ Einsatz“** mit Menü: Vollnut (ae = D, ap = D/2), Schruppen (D/2, D/2),
  Schruppen dynamisch (10 % D, Schneidenlänge höchstens 2 × D), Schlichten
  (2 % D, Schneidenlänge), beim Bohrer „Bohren“, immer „Eigener Einsatz“.
  vc und fz bleiben leer (Entscheidung 5 der Spezifikation).
- **Je Werkstoff oder für alle:** „Alle Werkstoffe“ bearbeitet die
  gemeinsame Tabelle. Ein Werkstoff ohne eigene Werte zeigt sie grau und
  nicht änderbar, mit „Eigene Werte für … anlegen“ (Kopie). Mit eigenen
  Werten: „Eigene Werte löschen“ (Rückfrage).
- **Hinweise zur gewählten Zeile:** ae größer als D, ap länger als die
  Schneide, vc/fz fehlen.
- Spaltenköpfe mit Einheit, jeder mit Tooltip samt Formel; Hilfeseite
  „Schnittwerte“ mit Beispiel und Orientierungswerten je ISO-Gruppe (als
  solche gekennzeichnet: „Der Katalog deines Fräsers geht immer vor.“).
- Werkzeugfelder in zwei Spalten, damit die Tabelle Platz hat; das Fenster
  ist jetzt 1100 × 760 Pixel groß.
- **Gefundene Fehler im eigenen Entwurf:** „+ Einsatz“ als QToolButton
  schob den Menüpfeil in den Text; jetzt ein QPushButton mit Menü.
- Bewusst nicht: geerbte Werte beim Tippen automatisch zu eigenen machen –
  das würde still eine zweite Tabelle anlegen. Der Knopf macht es sichtbar.

### TEST
- KI, FreeCADCmd (Wochen-Build): `test_schnittdaten` (Manuels Beispiel,
  Bohren, fehlende Werte), `test_werkzeuge` (Vorlagen, Erben, eigene Werte
  unabhängig, Speichern, Kopie), `test_sprache`, `test_hilfe` grün.
- KI, Oberfläche (Wochen-Build): `szenario_schnittwerte` grün – fz per
  Tastatur mit Komma in die Zelle getippt, Enter schließt den Dialog nicht,
  gerechnete Werte, Hinweis bei ap > Schneide, geerbt grau, eigene Werte,
  C45 unverändert, Bohrer, OK speichert. `szenario_werkzeugverwaltung`
  weiter grün. Screenshots angesehen.
- Manuel: offen.

### NEXT
- Bild des Eingriffs und Spandicke (Abschnitt 6.2).

## P-2026-09-25-46 werkzeugverwaltung-werkzeuge

### EINGELESEN
- W-002, Spezifikation Abschnitte 4, 5, 8, 9 und das erste
  Akzeptanzkriterium aus Abschnitt 12.

### DATEIEN
- `daten/werkstoffe.json` (neu: 51 Werkstoffe aller sechs ISO-Gruppen)
- `camaddon/werkstoffe.py` (neu), `camaddon/werkzeuge.py` (neu),
  `camaddon/gui_werkzeuge.py` (neu)
- `camaddon/gui_start.py` (Befehl, Werkzeugleiste), `camaddon/hilfe.py`
  (Themen „werkstoffe“, „werkzeuge“)
- `resources/icons/werkzeugverwaltung.svg` (neu)
- `help/de|en/werkstoffe.html`, `help/de|en/werkzeuge.html` (neu)
- `translations/de.json`, `translations/en.json` (Texte der
  Werkzeugverwaltung; „Über“ nennt sie)
- `tests/test_werkstoffe.py`, `tests/test_werkzeuge.py`,
  `tests/gui/szenario_werkzeugverwaltung.py` (neu)
- `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
CAM → Werkzeugverwaltung → im Feld „Werkstoff“ „1.43“ tippen und 1.4301
wählen → darunter stehen Zusammensetzung und Härte; „Neu“ → Durchmesser 12,
Schneiden 3, OK → nach erneutem Öffnen steht „T1 Schaftfräser Ø 12 · z 3 ·
VHM“ in der Liste. Manuel versteht das Fenster ohne Erklärung.

### DONE
- **Werkstoffliste:** 51 Einträge (Stahl, Edelstahl, Guss, Aluminium,
  Kupfer, Messing, Bronze, Titan, Nickel, Kunststoffe; Werkzeugstahl
  geglüht und gehärtet als zwei Einträge). Je Eintrag Nummer, Kurzname,
  Gruppe, Zustand, ISO-Gruppe, alte Namen („V2A“, „GG-25“, „Ms 58“,
  „AISI D2“), Zusammensetzung, Härte, Zugfestigkeit; kc1.1 und mc nur, wo
  der Wert aus dem Tabellenbuch sicher ist (sonst 0 = unbekannt).
- **Anzeige** wie in der Werkstatt: „1.4301  X5CrNi18-10 · Edelstahl,
  austenitisch (V2A, AISI 304)“, davor ein Kästchen in der ISO-Farbe.
  Darunter Zusammensetzung, Härte, Zugfestigkeit, ISO-Gruppe; Zahlen im
  Format der Oberfläche (17,5–19,5).
- **Suche** durch Tippen ins Feld (Nummer, Kurzname, Gruppe, alter Name).
- **Werkzeuge:** Liste nach Nummer, Neu / Kopieren / Löschen (mit
  Rückfrage), Felder Nummer, Art, Durchmesser, Schneiden, Schneidenlänge,
  Eckradius (nur Torusfräser), Schneidstoff, Bezeichnung. Hinweise sofort am
  Feld: fehlender Durchmesser, doppelte Nummer.
- **Speichern** wie FreeCADs Einstellungen: OK, Übernehmen, Abbrechen (fragt
  nach). Datei `CamAddon/werkzeugverwaltung.json` im Benutzerordner, erst in
  eine Zwischendatei, die vorige Fassung als `.bak`. Eine unlesbare Datei
  wird beiseitegelegt und gemeldet, nichts gelöscht.
- Zuletzt gewählter Werkstoff und zuletzt gewähltes Werkzeug bleiben
  gemerkt (Parameter `WvWerkstoff`, `WvWerkzeug`).
- **Gefundene Fehler im eigenen Entwurf** (im Szenario):
  - Enter in einem Feld schloss den Dialog: Die Knopfleiste macht OK beim
    Zeigen selbst zum Standardknopf, `setDefault(False)` vorher hilft nicht.
    Der Dialog hält Enter jetzt in `keyPressEvent` an (wie B-005).
  - Doppelte Klammern in der Anzeige („(Ck45 (C45E = 1.1191))“): alte
    Namen vereinfacht, US-Bezeichnungen einheitlich mit „AISI“.
  - Der Hinweis „T1 gibt es schon: T1 …“ nannte die Nummer doppelt; jetzt
    „T1 ist schon vergeben: Schaftfräser Ø 12“.
- Bewusst nicht in diesem Patch: Schnittwerte (nächster Patch), eigene
  Werkstoffe anlegen (eigener Patch; die Bibliothek kann sie schon
  speichern).
- Abweichung von FreeCAD-Gewohnheiten: keine. Die Knöpfe OK / Übernehmen /
  Abbrechen sind die von Qt und erscheinen in der Sprache von FreeCAD.

### TEST
- KI, FreeCADCmd (Wochen-Build): `test_werkstoffe`, `test_werkzeuge`,
  `test_sprache`, `test_hilfe` grün.
- KI, Oberfläche in beiden Versionen (1.1.3 und Wochen-Build):
  `szenario_werkzeugverwaltung` grün – Suche „1.43“ per Tastatur, Wahl aus
  den Vorschlägen, Info mit deutschem Dezimalkomma, zwei Werkzeuge, Enter
  im Feld, doppelte Nummer, OK speichert, Wiederöffnen, Abbrechen mit
  Rückfrage und „Verwerfen“. Screenshots angesehen.
- Manuel: offen.

### NEXT
- Schnittwerte je Werkstoff und Einsatz (Spezifikation Abschnitt 6).

## P-2026-09-25-45 zahlenfelder-gemeinsam

### EINGELESEN
- Die Werkzeugverwaltung (W-002) braucht dieselben Zahlenfelder wie „Maschine
  bearbeiten“: deutsches Format ohne Tausenderpunkte (B-004), leer heißt
  „unbekannt“. Die Helfer lagen privat in `gui_details.py`.

### DATEIEN
- `camaddon/gui_zahlen.py` (neu: `zahlenformat`, `Zahlenpruefer`,
  `zahl_lesen`, `zahl_zeigen`, dazu die zwei Grenzen)
- `camaddon/gui_details.py` (benutzt sie von dort)
- `docs/aufbau.md` (Modultabelle)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nichts sichtbar anders: „Maschine bearbeiten“ zeigt und liest Zahlen wie
vorher („30000“, „2,5“, leeres Feld = unbekannt).

### DONE
- Reines Verschieben, eigener Patch nach Arbeitsregel „keine Refactors
  nebenbei“. Namen ohne Unterstrich, weil jetzt mehrere Module sie
  benutzen.

### TEST
- KI, Wochen-Build: `szenario_felder` und `szenario_maschine_bearbeiten`
  grün (tippen Zahlen im deutschen Format, leeren Felder).

### NEXT
- W-002 Stufe 1: Werkzeugverwaltung mit Werkstoffen und Werkzeugen.

## P-2026-09-25-44 spezifikation-werkzeugverwaltung

### EINGELESEN
- Manuel: eine andere Werkzeugverwaltung ausdenken – bedienerfreundlich,
  übersichtlich, „einfach GENIAL“, etwa wie die alte von InventorCAM.
  Werkstoffliste zuerst, mit deutschen Bezeichnungen („1.4301 (Edelstahl,
  chemische Zusammensetzung)“) und Härte; im Werkzeug Schnittwerte je
  Werkstoff, auch für alle gleich; vc eingeben statt Drehzahl; ae und ap je
  Einsatz, als Tabelle; Schruppstrategie mit größtem Zeitspanvolumen und eine
  Beurteilung verschiedener Strategien (sein Beispiel: Ø 12, ae 1,2 / ap 25 /
  fz 0,15 statt ae 100 % / ap 3 / fz 0,05). „Möglichst einfach und gut
  erklärt.“
- Er schläft; Entscheidungen treffe ich und schreibe sie auf.

### DATEIEN
- `docs/spezifikation_werkzeugverwaltung.md` (neu)
- `docs/STATUS_SNAPSHOT.md` (W-002, Projektstatus)
- `CHATSTART.md` (Lesekarte: W-002; Zeile Installieren/Update)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel liest die Spezifikation und findet seinen Wunsch darin wieder –
Abschnitt 1 in seinen Worten, Abschnitt 11 mit den Entscheidungen zur
Besprechung.

### DONE
- FreeCAD-Check (Arbeitsregeln 2.3), im Quelltext beider Versionen:
  - 1.1.3 hat Werkzeugbibliothek und Werkzeug-Controller, aber keine
    Schnittwerte je Werkstoff.
  - Der Wochen-Build hat neu `Path/Tool/FeedsSpeeds`: „Presets“ am
    Werkzeug mit vc und fz je Werkstoff (UUID oder Name) und
    Bearbeitungsart (profile, pocket, slot, drill, adaptive,
    surface_finish), dazu einen Vorschlagsdialog im Werkzeug-Controller, der
    den Werkstoff des Rohteils nimmt.
  - FreeCADs Werkstoffkarten kennen die Werkstoffnummer
    (`MaterialStandard/MaterialNumber`), aber weder Härte noch
    Zusammensetzung; das Modell `Machinability` (vc HSS/VHM, kc1.1, mc)
    haben nur sechs generische Werkstoffe.
  - ae/ap und eine Beurteilung von Strategien gibt es in keiner Version.
- Daraus die Spezifikation: Werkstoffliste mitgeliefert und erweiterbar,
  Werkzeuge mit einer Tabelle der Einsätze „für alle Werkstoffe“ und je
  Werkstoff, gerechnete Werte, Bild des Eingriffs, Strategievergleich mit
  „Schneidenweg je cm³“ als Maß für den Verschleiß, Übergabe an FreeCADs
  Presets als Stufe 2.
- Manuels Beispiel durchgerechnet (Abschnitt 7): 2,5-faches
  Zeitspanvolumen, ein Zwölftel des Schneidenwegs.
- Acht Entscheidungen mit Alternative und Kosten in Abschnitt 11.

### TEST
- Nur Doku, kein Testlauf. Die Zahlen des Beispiels von Hand nachgerechnet.

### NEXT
- Stufe 1 bauen, Patch für Patch nach Abschnitt 12.

## P-2026-09-25-43 installieren-einfach

### EINGELESEN
- Manuel zur Anleitung „Installieren, solange das Repository privat ist“:
  „ich hätte hierfür gerne ein bash script oder sowas … einfacher“, und:
  „das einfachste wäre die repo öffentlich zu stellen … wenn du denkst, das
  geht zum Testen schon, dass andere es auch testen können, dann mach das“.
- Er schläft, ich entscheide selbst und schreibe die Entscheidungen auf.

### DATEIEN
- `installieren.py` (neu)
- `tests/test_installieren.py` (neu)
- `README.md` (Abschnitte „Installieren“)
- `translations/de.json`, `translations/en.json` (`update.kein_git_ordner`)
- `docs/STATUS_SNAPSHOT.md` (T-005)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Bei öffentlichem Repository: In FreeCAD Ansicht → Fenster → Python-Konsole,
die Zeile aus dem README einfügen, Enter → Meldung „CAM-Addon … ist
installiert. Bitte FreeCAD neu starten.“; nach dem Neustart steht die
Werkzeugleiste in Assembly und CAM.

### DONE
- **Entscheidung 1: Python-Zeile statt Bash-Skript.** Ein Bash-Skript
  liefe nicht unter Windows, und es müsste den Addon-Ordner raten – der
  hängt von Betriebssystem und FreeCAD-Version ab. Eine Zeile in der
  Python-Konsole von FreeCAD kennt ihn (`App.getUserAppDataDir()`), läuft
  überall und braucht weder Git noch GitHub Desktop.
- **Entscheidung 2: öffentlich stellen – empfohlen, aber nicht von mir
  umgestellt.** Geprüft: alle 42 Commits von „Claude <noreply@anthropic.com>“,
  keine Schlüssel, Passwörter oder Mail-Adressen im ganzen Verlauf, keine
  großen Dateien, Lizenz LGPL-2.1-or-later liegt bei, `package.xml` nennt
  Manuel ohne Mail-Adresse. Für andere Tester reicht der Stand als frühe
  Vorabversion. Die Sichtbarkeit eines Repositorys kann ich mit meinen
  Werkzeugen nicht ändern – das ist ein Klick für Manuel (T-005).
- `installieren.py` holt das ZIP von GitHub, packt es außerhalb von `Mod/`
  aus (ein halber Ordner in `Mod/` würde beim nächsten Start als zweites
  Addon geladen) und setzt es an die Stelle von `Mod/freecad-cam-addon`.
  Misslingt das Ersetzen, kommt der alte Stand zurück.
- Dieselbe Zeile noch einmal = aktualisieren. Ein Git-Klon (GitHub Desktop)
  bleibt unberührt.
- Die Zeile trägt das Repository im Addon-Manager ein („Eigene
  Repositories“, Parameter `Addons/CustomRepositories`, Format wie dort:
  „Adresse Zweig“ je Zeile). Nachgelesen im Quelltext des Addon-Managers
  (1.1.3 und Wochen-Build, `addonmanager_workers_startup.py`): Liegt ein
  Ordner mit dem Namen des Repositorys in `Mod/`, gilt das Addon als
  installiert; ohne Git vergleicht er die Version in `package.xml`, mit Git
  macht er aus dem Ordner einen Klon. Er meldet also neue Versionen, auch
  wenn das Addon per ZIP kam.
- Nicht gemacht, mit Absicht: Git in der Installationszeile. Das hätte die
  Ausnahme „Git nur in `aktualisierung.py`“ (Arbeitsregeln, Abschnitt 7)
  erweitert, und unter Windows fehlt Git meist ohnehin.
- Nicht gemacht: die eigene Update-Suche beim Start auch für
  ZIP-Installationen (per HTTPS statt Git). Bis dahin zeigt der
  Addon-Manager die Updates; der Text `update.kein_git_ordner` sagt das
  jetzt, statt nur aufs README zu verweisen.
- Befund im README korrigiert: Die Python-Konsole heißt im deutschen FreeCAD
  **Ansicht → Fenster → Python-Konsole** („&Panels“ → „Fenster“ laut
  `FreeCAD_de.ts`), nicht „Ansicht → Ansichten“.
- Texte von `installieren.py` stehen zweisprachig im Code: Die Datei läuft,
  bevor das Addon und seine Sprachdateien da sind.

### TEST
- `tests/test_installieren.py` (KI, FreeCADCmd, Wochen-Build): frisch
  installieren, noch einmal (ersetzt ganz, alte Dateien weg, kein doppelter
  Eintrag, keine Reste in `Mod/`), kaputter Download, Archiv ohne
  `package.xml` und kein ZIP (Installation bleibt unverändert), Git-Klon
  bleibt unberührt, andere eigene Repositories bleiben, die Zeile im README
  stimmt mit der Datei überein. „GitHub“ ist dabei ein ZIP im Temp-Ordner.
- Echter Lauf gegen GitHub (KI): Das Repository ist noch privat → HTTP 404,
  die Meldung verweist auf die Anleitung mit GitHub Desktop. Der Weg mit
  öffentlichem Repository ist erst nach dem Umstellen prüfbar – von Manuel.

### NEXT
- Manuel stellt das Repository öffentlich und probiert die Zeile aus.

## P-2026-09-25-42 nur-noetige-tests

### EINGELESEN
- Manuel: „du testest zu viel“. Die Tests sollen nur laufen, wenn es
  wirklich nötig ist – sie kosten Ressourcen, auch Rechenzeit und Strom in
  Rechenzentren. Wie viel nötig ist, überlässt er meinem Urteil.
- Bilanz des Tages: Der komplette Lauf (rund 3 Minuten) lief elfmal bei 13
  Patches, zehn Läufe davon einfach grün. Gefunden haben die echten Fehler
  gezielte Proben (B-004, B-005), nicht die Wiederholungen.

### DATEIEN
- `docs/arbeitsregeln.md` (Abschnitt 5)
- `CLAUDE.md` (Regel zum Pushen)
- `CHATSTART.md` (Prüfung vor jedem Push statt bei jeder Änderung)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Regeln verlangen einen kompletten Lauf nur noch einmal vor einem Push,
für alle Patches zusammen. Doku-Änderungen brauchen keinen Lauf.

### DONE
- Neue Regeln:
  - Während der Arbeit läuft nur die Prüfung zum geänderten Teil, in einer
    Version.
  - Vor einem Push läuft einmal `scripts/alle_tests.sh` in beiden
    Versionen, für alle Patches seit dem letzten Push.
  - Reine Doku-Änderungen laufen ohne Test.
  - Neue Prüfungen gibt es nur für behobene Fehler, dann mit einer
    Gegenprobe, und für neue Funktionen.
  - Neue Szenarien gibt es nur für neue Oberflächen.
  - Im Chat genügt „Tests grün“.
- Nicht geändert, mit Absicht: Alle vorhandenen Prüfungen bleiben. Ein Lauf
  kostet rund 3 Minuten; gespart wird vor allem dadurch, dass er seltener
  läuft.

### TEST
- Nur Doku geändert, deshalb nach der neuen Regel kein Testlauf.

### NEXT
- Manuels Test in FreeCAD 1.1.3, danach W-001 Stufe 3.

## P-2026-09-25-41 eine-grenze-fehlt-im-bericht

### EINGELESEN
- B-002 aus P-2026-09-25-29: Hat ein Gelenk nur eine der beiden
  Begrenzungen, bekam die andere Seite bei der Übergabe ohne Hinweis
  ±100000 mm bzw. ±360°. Gemeldet wurde nur, wenn beide fehlten.

### DATEIEN
- `camaddon/export.py` (`_satz_fehlende_grenzen`)
- `translations/de.json`, `translations/en.json` (`export.eine_grenze`)
- `tests/test_export.py`
- `docs/STATUS_SNAPSHOT.md` (B-002 entfernt, keine offenen Bugs mehr)
- `package.xml` (Version 0.3.9)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Fehlt am Gelenk eine Begrenzung oder fehlen beide, steht das unter „Bitte
prüfen“ – außer bei einer endlos drehenden Achse.

### DONE
- Neuer Satz „… hat am Gelenk nur eine Begrenzung (Min oder Max). Für die
  andere Seite bekommt CAM einen sehr großen Bereich …“. Fehlen beide,
  bleibt es beim bisherigen Satz.
- Die Bedingung steht jetzt an einer Stelle:
  `endlos = achse.art != LINEAR and ba.Endlos`. Dazu kommt
  `_satz_fehlende_grenzen()`, das zwischen „keine“ und „nur eine“
  unterscheidet. Die Hilfsvariable `ohne_grenzen`, die an zwei Stellen
  gesetzt wurde, ist weg.
- Version 0.3.9.

### TEST
- Von der KI ausgeführt:
  - Neuer Abschnitt in `test_export.py`: Das Gelenk Z bekommt nur ein
    Maximum (500 mm). Erwartet werden der Satz „nur eine Begrenzung“, nicht
    „keine Begrenzung“, und die Grenzen −100000/500 mm in CAM.
  - Gegenprobe mit dem alten Code: Der Satz fehlt.
  - Mit dem neuen Code ist `alle_tests.sh` in beiden Versionen grün.

### NEXT
- Manuels Test in FreeCAD 1.1.3.
- Danach W-001 Stufe 3: Maschine von Hand verfahren.

## P-2026-09-25-40 pflichtwert-fehlt-im-bericht

### EINGELESEN
- B-001 aus P-2026-09-25-29: Fehlt bei der Übergabe ein Pflichtwert, trägt
  das Addon FreeCADs Vorgabe ein. Der Bericht führte das unter „In CAM
  angekommen“, als wäre alles in Ordnung.
- Dasselbe galt für die Spindel: Ohne Drehzahl stand dort „Spindel S4, bis
  0 U/min“.

### DATEIEN
- `camaddon/export.py`
- `translations/de.json`, `translations/en.json` (vier neue Texte)
- `tests/test_export.py`
- `docs/STATUS_SNAPSHOT.md` (B-001 entfernt)
- `package.xml` (Version 0.3.8)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Fehlt ein Pflichtwert (Eilgang, Geschwindigkeit, Drehzahl), steht unter
„Bitte prüfen“ ein Satz, was fehlt, was CAM stattdessen bekommt und was zu
tun ist.

### DONE
- Linear- und Drehachse: Unter „In CAM angekommen“ steht weiter, was CAM
  bekommen hat, also FreeCADs Vorgabe. Dazu steht jetzt unter „Bitte
  prüfen“, dass der Wert fehlte.
- Spindel ohne Drehzahl: „Spindel S4, ohne größte Drehzahl“ statt „bis
  0 U/min“, dazu unter „Bitte prüfen“: CAM begrenzt die Spindeldrehzahl dann
  nicht. Nachgesehen in FreeCAD: Der Schnittdaten-Rechner begrenzt nur bei
  `max_rpm > 0` (`Path/Tool/FeedsSpeeds/resolver.py`).
- Version 0.3.8.

### TEST
- Von der KI ausgeführt:
  - `test_export.py` hat einen neuen Abschnitt: X1 ohne Eilgang, C4 ohne
    Geschwindigkeit, S4 ohne Drehzahl.
  - Gegenprobe mit dem alten Code: Alle vier Prüfungen schlagen fehl, und im
    Bericht steht „Spindel S4, bis 0 U/min“.
  - Mit dem neuen Code ist `alle_tests.sh` in beiden Versionen grün; in
    1.1.3 wird der Export wie immer übersprungen.

### NEXT
- B-002: nur eine Begrenzung am Gelenk.

## P-2026-09-25-39 push-freigabe-dauerhaft

### EINGELESEN
- Manuels Antwort auf die Frage nach P-2026-09-25-36 bis -38: „Ja, und
  künftig direkt“. Jeder Patch wird gepusht, sobald alle Prüfungen in beiden
  FreeCAD-Versionen grün sind.

### DATEIEN
- `CLAUDE.md` (Regel zum Pushen)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die dauerhafte Freigabe steht in der `CLAUDE.md`, damit auch spätere
Sitzungen sie kennen.

### DONE
- P-2026-09-25-36 bis -38 gepusht (`36fd298..7b0b350`) und bei GitHub selbst
  nachgeprüft.
- In der `CLAUDE.md` steht jetzt: Jeder Patch wird gepusht, sobald
  `scripts/alle_tests.sh` in beiden Versionen vollständig grün ist; alles
  andere nur auf ausdrückliche Ansage. Die Regel, danach bei GitHub selbst
  nachzusehen, bleibt.

### TEST
- Nur Doku geändert. `alle_tests.sh` ohne Oberfläche ist in beiden
  Versionen grün.

### NEXT
- B-001 und B-002 (Bericht der Übergabe).

## P-2026-09-25-38 enter-bestaetigt-nur-das-feld

### EINGELESEN
- Manuels Entscheidung zu B-005: „Nur Feld bestätigen“. Enter übernimmt den
  Wert im Feld; geschlossen wird der Dialog nur mit OK oder Abbrechen.

### DATEIEN
- `camaddon/gui_maschine.py` (`_EnterBleibtImDialog`)
- `tests/gui/szenario_felder.py` (vorher `szenario_zahlen.py`; jetzt mit
  echtem Enter)
- `docs/aufbau.md` (Stolperstein erledigt)
- `docs/STATUS_SNAPSHOT.md` (B-005 entfernt)
- `package.xml` (Version 0.3.7)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Enter in einem Feld übernimmt den Wert, und der Dialog bleibt offen.

### DONE
- Ein Feld verarbeitet Enter und reicht die Taste dann an die Widgets
  darüber weiter; bei FreeCADs Aufgabenfenster angekommen, löste sie „OK“
  aus. Ein Ereignisfilter ganz oben im Dialog hält Enter jetzt an. Das
  Feld hat seinen Wert zu diesem Zeitpunkt schon übernommen. Escape
  (Abbrechen) bleibt, wie es ist.
- Das Szenario heißt jetzt `szenario_felder`, weil es beides prüft:
  Zahlenformat (B-004) und Enter (B-005). Es tippt echtes Enter; die
  Nachbildung `bestaetigen()` aus P-2026-09-25-31 ist weg.
- Version 0.3.7.

### TEST
- Von der KI ausgeführt:
  - Gegenprobe ohne den Filter: „Enter im Feld hat den Dialog geschlossen
    (B-005)“.
  - Mit dem Filter ist `szenario_felder` in beiden Versionen grün, ebenso
    `alle_tests.sh`.

### NEXT
- B-001 und B-002 (Bericht der Übergabe).
- Manuels Test in FreeCAD 1.1.3.

## P-2026-09-25-37 readme-update-suche

### EINGELESEN
- README, Abschnitt „Aktualisieren“: Dort steht, das Addon frage beim Start
  „Jetzt aktualisieren?“. Seit P-2026-09-25-30 fragt es aber nur bei einer
  neuen Version.

### DATEIEN
- `README.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die README beschreibt die Update-Suche so, wie sie sich verhält.

### DONE
- „fragt bei einer neuen Version“. Dazu der Hinweis, dass „Pull“ von Hand
  auch kleine Änderungen ohne neue Versionsnummer holt.

### TEST
- Nur Doku geändert. `alle_tests.sh` ohne Oberfläche ist in beiden
  Versionen grün.

### NEXT
- B-005: Enter bestätigt nur das Feld.

## P-2026-09-25-36 push-bei-github-pruefen

### EINGELESEN
- Manuels Freigabe: P-2026-09-25-30 bis -35 pushen und die Prüfung direkt
  bei GitHub als Regel aufnehmen.
- Befund aus P-2026-09-25-30: P-23 bis P-28 blieben unbemerkt lokal, weil
  `origin` auf den Ordner selbst zeigte.

### DATEIEN
- `CLAUDE.md` (neue Regel)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach jedem Push steht fest, dass GitHub den Commit hat – geprüft bei GitHub
selbst, nicht über `origin`.

### DONE
- P-2026-09-25-30 bis -35 gepusht (`999d46b..36fd298`). Bei GitHub selbst
  nachgeprüft: `main` steht auf `36fd298`.
- Neue Regel in `CLAUDE.md`: Nach jedem Push muss
  `git ls-remote https://github.com/manuelhofer/freecad-cam-addon main` den
  eigenen Commit zeigen. Die Regel steht dort und nicht in
  `docs/arbeitsregeln.md`, weil sie nur die Arbeitsweise von Claude Code
  betrifft.

### TEST
- Nur Doku geändert. `alle_tests.sh` ohne Oberfläche ist in beiden
  Versionen grün.

### NEXT
- README: Beschreibung der Update-Suche an P-2026-09-25-30 anpassen.
- B-005: Enter bestätigt nur das Feld (Manuels Entscheidung).

## P-2026-09-25-35 entwickler-doku

### EINGELESEN
- Manuels Auftrag aus P-2026-09-25-27: Der Code soll für jeden menschlichen
  Programmierer leicht zu lesen sein. Dazu gehört ein Einstieg, der das
  Ganze erklärt, bevor man in einzelne Dateien schaut.

### DATEIEN
- `docs/aufbau.md` (neu)
- `CHATSTART.md` (Lesekarte: Zeile für `docs/aufbau.md`)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer den Code nicht kennt, findet in einer Datei: den Weg von der Assembly
zur CAM-Maschine, welches Modul was tut, die Regeln für Importe und Texte,
wie geprüft wird, und die Stolpersteine von FreeCAD und PySide.

### DONE
- `docs/aufbau.md` mit diesen Abschnitten:
  - Weg der Daten als Bild: Assembly → Kette → Maschinenobjekt → Übergabe.
  - Tabelle aller Module.
  - Zwei Regeln: Kern-Module ohne Qt; Importe nur von `gui_*` zum Kern.
  - Kette, Maschinenobjekt, Dialog, Texte, zwei FreeCAD-Versionen, Prüfen.
  - Stolpersteine, jeder mit seiner Folge im Code.
- Die Regeln sind am Code geprüft: Kein Kern-Modul importiert
  `FreeCADGui`, Qt oder ein `gui_*`-Modul.

### TEST
- Von der KI ausgeführt: Verweise in `docs/aufbau.md` zeigen auf vorhandene
  Dateien; `alle_tests.sh` ohne Oberfläche in beiden Versionen grün (nur
  Doku geändert).

### NEXT
- Manuel: Push-Freigabe (P-2026-09-25-30 bis -35 liegen nur lokal),
  Entscheidung zu B-005, Test in FreeCAD 1.1.3.
- Danach B-001 und B-002 (Bericht der Übergabe).

## P-2026-09-25-34 tests-und-skripte-lesbar

### EINGELESEN
- Durchsicht von Hand: `tests/`, `tests/gui/_lauf/`, `scripts/`.

### DATEIEN
- `tests/test_maschine.py`, `tests/test_export.py`, `tests/beispielmaschinen.py`
- `tests/gui/_lauf/szenario_lauf.py`
- `scripts/oberflaeche_testen.sh`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Tests lesen sich ohne Rätsel: keine `__import__`-Tricks, keine
gleichnamigen Funktionen und Variablen, Lagen der Beispielkörper mit Namen.
Geprüft wird genau dasselbe wie vorher.

### DONE
- **test_maschine.py:** `import math` statt zweimal `__import__("math")`;
  vier Kennwerte als vier Zuweisungen statt einer `setattr`-Schleife.
- **test_export.py:** Die Funktion hieß `pruefen()` und hatte eine lokale
  Variable `pruefen`. Jetzt heißen sie `pruefe_export()` und `zu_pruefen`;
  dazu `uebertragen` und `nicht_uebertragen` statt `nicht`.
- **beispielmaschinen.py:**
  - Lagen mit Namen: `zylinder("Hauptspindel", 60, 80, x=75, y=100, z=300)`
    statt `zylinder("Hauptspindel", 60, 80, 75, 100, 300)`. Dasselbe gilt
    für LCS-Name und -Höhe bei `bauteil()`. Die Zahlen sind unverändert.
  - Der Kommentar zu `Placement` stand zweimal; jetzt steht er einmal in
    `_stelle()`.
  - `Baukasten` hat eine Beschreibung.
- **Szenario-Läufer:** `START_NACH_MS` statt `3000`.
- **oberflaeche_testen.sh:** `zeitlimit_s` statt zweimal `180`.
- Nicht geändert, mit Absicht: Jede Prüfung hat ihr eigenes dreizeiliges
  `pruefe()`. Ein gemeinsames Modul würde keine Zeile der Pfad-Vorbereitung
  sparen; so bleibt jede Prüfung für sich lesbar.

### TEST
- Von der KI ausgeführt: black und ruff sauber; `alle_tests.sh` in beiden
  Versionen grün.

### NEXT
- Entwickler-Doku `docs/aufbau.md`.

## P-2026-09-25-33 oberflaeche-rest-lesbar

### EINGELESEN
- Durchsicht von Hand: `gui_zeigen`, `gui_start`, `gui_sprachwahl`,
  `gui_aktualisierung`.

### DATEIEN
- `camaddon/__init__.py` (`symbol()` und `SYMBOL_ORDNER`, vorher in
  `gui_start`)
- `camaddon/gui_start.py`, `gui_sprachwahl.py`, `gui_aktualisierung.py`,
  `gui_zeigen.py`
- `camaddon/gui_maschine.py` (holt `symbol` aus dem Paket)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Alle Importe stehen oben in der Datei, und kein Modul importiert ein anderes
im Kreis. Wartezeiten und Maße sind benannte Konstanten, jede Klasse sagt,
wozu sie da ist. Das Verhalten bleibt gleich.

### DONE
- **Import-Kreis aufgelöst:** `gui_maschine` holte `symbol()` aus
  `gui_start`, und `gui_start` importierte `gui_maschine`. Deshalb standen
  die Importe in `gui_start` und `gui_sprachwahl` in den Funktionen.
  `symbol()` liegt jetzt beim Paket, neben `ADDON_ORDNER`. Alle Importe
  stehen oben.
- **gui_aktualisierung:**
  - `START_VERZOEGERUNG_MS`, `NACHSEHEN_MS`, `DIALOG_BREITE` statt Zahlen.
  - `ordner` hat den Addon-Ordner als Vorgabe; die Verzweigungen
    `if self.ordner: … else: …` entfallen.
  - Beim Start entfernt `fertig` genau seine Suche aus der Liste; vorher
    räumte ein Tupel-Lambda die ganze Liste leer.
  - Erklärt ist, warum der Such-Thread `daemon` ist und warum die Liste der
    laufenden Suchen nötig ist.
- **gui_zeigen:** `GROESSE_OHNE_FORM` statt `100.0`; die Berechnung des
  Ausschlags steht in `_weite()`.
- **gui_start, gui_sprachwahl:** Docstrings; Kommentar, dass FreeCAD
  `loadSettings` und `saveSettings` aufruft.
- Keine sichtbare Änderung, deshalb bleibt die Version 0.3.6.

### TEST
- Von der KI ausgeführt:
  - black und ruff sauber.
  - `alle_tests.sh` in beiden Versionen grün, 30 von 30. Die geänderten
    Importe beim Start laufen in jedem der sieben Szenarien mit.
  - Protokolle aller 14 Szenario-Läufe: kein Traceback.

### NEXT
- Tests und Skripte durchsehen; Entwickler-Doku `docs/aufbau.md`.

## P-2026-09-25-32 dialog-maschine-aufgeteilt

### EINGELESEN
- Manuels Auftrag aus P-2026-09-25-27 (Code lesbar, „to the max“).
- `gui_maschine.py` hatte 930 Zeilen: Befehl, Hilfe, Zahlenfelder, das
  Aufgabenfenster mit 45 Methoden, Verteilhilfe und Bericht in einer Datei.
- Die Szenarien riefen acht private Methoden des Fensters direkt auf.

### DATEIEN
- `camaddon/gui_maschine.py` (Befehl und Aufgabenfenster, neu gegliedert)
- `camaddon/gui_details.py` (neu: Felder der gewählten Betriebsart oder
  Aufnahme, Zahlenformat)
- `camaddon/gui_hilfe.py` (neu: Knopf (?) und Hilfefenster)
- `camaddon/gui_verteilhilfe.py` (neu: Revolverplätze verteilen)
- `camaddon/gui_bericht.py` (neu: Bericht nach der Übergabe)
- `camaddon/kette.py`, `maschine.py` (nur Trennlinien der Abschnitte)
- `tests/gui/szenario_*.py` (neue Schnittstelle)
- `tests/test_hilfe.py` (sucht in allen `gui_*.py`, Suchmuster repariert)
- `CHATSTART.md` (Lesekarte: neue Module)
- `package.xml` (Version 0.3.6)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Jede Datei hat ein Thema. Das Aufgabenfenster ist in benannte Abschnitte
gegliedert. Die Szenarien benutzen nur öffentliche Methoden oder bedienen
Knöpfe und Signale wie ein Benutzer. Alle Szenarien sind in beiden
FreeCAD-Versionen grün.

### DONE
- **Aufteilung:**
  - `gui_maschine.py`: Befehl, Suche nach der Assembly, Aufgabenfenster.
  - `gui_details.py`: der Kasten mit den Feldern.
  - `gui_hilfe.py`, `gui_verteilhilfe.py`, `gui_bericht.py`: je ein kleines
    Fenster.
- **Aufgabenfenster:**
  - Benannte Abschnitte: Schnittstelle zu FreeCAD, Aufbau, Aktionen,
    Auswahl, Eingaben übernehmen, Listen füllen, Zeigen, Abfragen,
    Rückfragen.
  - `_baue()` ist je Bereich aufgeteilt.
  - Öffentliche „Aktionen“ stehen hinter den Knöpfen und dienen auch den
    Szenarien: `betriebsart_anlegen`, `betriebsart_entfernen`,
    `aufnahme_anlegen`, `aufnahme_entfernen`, `plaetze_verteilen`,
    `uebergeben`, `zeige`, `springe_zu`, `neu_aufbauen`, `alle_lcs`,
    `lcs_im_revolver`.
  - Die Zeilenarten heißen `ZEILE_GELENK`, `ZEILE_BETRIEBSART` usw. statt
    „ba“ und „auf“. `_zeilendaten()` und `_alle_zeilen()` ersetzen je vier
    Wiederholungen.
  - Benannte Konstanten statt Zahlen: `ZEIGEN_NACH_MS`, Mindesthöhen der
    Listen, Fenstergrößen, Anzahl der Revolverplätze.
  - Kein `lambda: x and …`-Trick und kein doppeltes Leeren der Details mehr.
    `self.meldungen` wird in `__init__` angelegt, `IsActive` liest sich als
    `not activeDialog()`.
- **Sichtbar geändert, deshalb Version 0.3.6:**
  - „+ Betriebsart“ ist ein Knopf mit Aufklappmenü, erkennbar am kleinen
    Pfeil. Vorher öffnete der Code ein selbst positioniertes Menü, das bei
    jedem Klick neu entstand und nie freigegeben wurde.
  - „+ Betriebsart“ ist nur bedienbar, wenn zur Auswahl eine Achse gehört.
    Bei einer Betriebsart ohne gültiges Gelenk kam vorher beim Klick einfach
    nichts.
  - Der Bericht zeigt keinen leeren Abschnitt „In CAM angekommen“ mehr.
- **Szenarien:** Sie wählen die Betriebsart jetzt über das Menü des
  Knopfs, legen Aufnahmen per Knopfdruck an und springen per
  `itemClicked` zu einem Hinweis, also wie ein Benutzer.
- Trennlinien der Abschnitte sind in allen Modulen 80 Zeichen breit.
- **Befund in `test_hilfe.py`:** Das Muster für die Knöpfe (?)
  (`_kopfzeile\([^)]*,…`) kam nie an der Klammer von `tr("…")` vorbei. Der
  Test prüfte deshalb nur den Verweis `href="beschleunigung"`, die drei
  Knöpfe nie. Aufgefallen ist das erst, weil nach der Aufteilung beide
  Muster nichts mehr fanden. Jetzt durchsucht der Test alle `gui_*.py` und
  schlägt fehl, wenn eines der beiden Muster nichts findet.

### TEST
- Von der KI ausgeführt:
  - black und ruff sauber.
  - Alle sieben Szenarien in beiden Versionen grün.
  - `alle_tests.sh` in beiden Versionen grün.
  - Screenshot angesehen: „+ Betriebsart“ mit Aufklapp-Pfeil, Felder
    darunter wie vorher.
  - `test_hilfe.py`: Das alte Muster findet im alten Code `set()`. Das neue
    findet die Knöpfe `achsen`, `aufnahmen`, `glieder` und den Verweis
    `beschleunigung`.

### NEXT
- Durchsicht von `gui_zeigen`, `gui_start`, `gui_sprachwahl` und
  `gui_aktualisierung`.

## P-2026-09-25-31 zahlenfelder-eindeutig

### EINGELESEN
- Befund bei der Durchsicht von `gui_maschine.py`: Die Zahlenfelder zeigen
  Werte mit `QLocale()`, lesen sie aber mit „Komma oder Punkt ist das
  Dezimalzeichen“.
- Probe in FreeCAD 1.1.3 und im Wochen-Build mit `LANG=de_DE`: FreeCAD
  stellt für Qt `de_DE` **mit** Tausendertrennzeichen ein. 30000 erscheint
  als „30.000“.

### DATEIEN
- `camaddon/gui_maschine.py` (`_zahlenformat`, `_Zahlenpruefer`,
  `_zahl_lesen`, `_zahl_zeigen`)
- `tests/gui/szenario_zahlen.py` (neu)
- `package.xml` (Version 0.3.5)
- `docs/STATUS_SNAPSHOT.md` (B-005)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im deutschen Zahlenformat zeigt das Eilgang-Feld 30000 als „30000“. Weder
Bestätigen ohne Änderung noch „35.000“ tippen verfälscht den Wert. Ein
geleertes Feld setzt den Wert auf „unbekannt“ (0).

### DONE
- **B-004 behoben**, drei Fehler mit derselben Ursache:
  1. Das Feld zeigte „30.000“. Bestätigte man das ohne Änderung, stand
     danach 30 mm/min im Dokument.
  2. „35.000“ getippt ergab 35 statt 35000.
  3. Ein geleertes Feld wurde nie übernommen, weil `QDoubleValidator` es
     für unfertig hält. Der alte Wert blieb, obwohl das Feld leer war.
- Zahlen stehen jetzt im Format der Oberfläche, aber ohne
  Tausendertrennzeichen. Auf Deutsch ist das Komma das Dezimalzeichen, einen
  Punkt nimmt das Feld nicht an. So ist jede Eingabe eindeutig.
- `_Zahlenpruefer` lässt ein leeres Feld zu, es bedeutet „unbekannt“ (0).
- Version 0.3.5.
- **B-005 gefunden:** Enter in einem Feld schließt den ganzen Dialog mit OK.
  Das ist FreeCADs Verhalten für alle Aufgabenfenster. Ob der Dialog davon
  abweichen soll, entscheidet Manuel; im Snapshot steht ein Vorschlag.

### TEST
- Von der KI ausgeführt:
  - Neues Szenario `szenario_zahlen`: deutsches Zahlenformat wie bei FreeCAD
    auf einem deutschen System, Eingaben Taste für Taste.
  - Gegenprobe mit dem alten Code, alle Fehler einzeln belegt: Anzeige
    „30.000“; nach dem Bestätigen 30.0; „35.000“ ergibt 35.0; das geleerte
    Feld bleibt 35.0; kein Hinweis auf den fehlenden Eilgang.
  - Mit dem neuen Code ist das Szenario in beiden Versionen grün, ebenso
    `alle_tests.sh`.
  - Probe zu B-005: Enter im Feld „NC-Name“ ergibt `geschlossen=True`, ein
    Rückgängig-Schritt, in 1.1.3 und im Wochen-Build.

### NEXT
- Durchsicht der Oberflächen-Module: `gui_maschine.py` aufteilen.

## P-2026-09-25-30 update-nur-bei-neuer-version

### EINGELESEN
- B-003 aus P-2026-09-25-29: Die Update-Suche meldete „neu“, sobald auf
  GitHub ein anderer Commit lag, auch bei gleicher Version. Der Hinweis
  hätte dann gelautet: „neue Version 0.3.3 (installiert ist 0.3.3)“.
- Dringend geworden, weil die nächsten Patches (Durchsicht der Oberfläche,
  Tests, Doku) nichts Sichtbares ändern und deshalb keine neue Version
  bekommen.
- **Befund beim Push von P-2026-09-25-29:** `origin` zeigte im Klon auf den
  Ordner selbst statt auf GitHub. Das hatte der Test mit dem Addon-Manager
  in P-2026-09-25-23 verursacht. P-23 bis P-28 kamen deshalb nie bei GitHub
  an: `git push` meldete „Everything up-to-date“, und die Kontrolle mit
  `git ls-remote origin` fragte nur den Ordner selbst ab. `origin` zeigt
  wieder auf GitHub. P-23 bis P-29 sind nachgeschoben (`b9e4932..999d46b`)
  und bei GitHub selbst nachgeprüft. Weitere Pushes erst nach Manuels
  ausdrücklicher Freigabe.

### DATEIEN
- `camaddon/aktualisierung.py` (`ist_neuer()`, Vergleich der Versionen)
- `tests/test_aktualisierung.py` (neuer Stand ohne neue Version; Vergleich
  Zahl für Zahl)
- `package.xml` (Version 0.3.4)
- `docs/STATUS_SNAPSHOT.md` (B-003 entfernt)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Update-Suche meldet nur eine höhere Version. Ein neuer Stand auf GitHub
mit gleicher Version gilt als „aktuell“.

### DONE
- `ist_neuer(neu, jetzt)` vergleicht Zahl für Zahl, also ist 0.3.10 höher
  als 0.3.9. Ist eine Version unlesbar, gilt „anders ist neu“: lieber einmal
  zu oft fragen als ein Update verschweigen.
- Änderungen ohne neue Version (Tests, Doku, Aufräumen) kommen beim
  Benutzer mit der nächsten Version an. Beim Aktualisieren wird ohnehin bis
  zum neuesten Stand vorgespult.
- Der Vergleich der Commits (`rev-parse`) entfällt; er ist im Vergleich der
  Versionen enthalten.
- Version 0.3.4, weil sich das Verhalten der Update-Suche ändert.

### TEST
- Von der KI ausgeführt:
  - Gegenprobe mit dem alten Code: Der neue Fall ergibt
    `Ergebnis(status='neu', version_neu='9.9.0', version_jetzt='9.9.0')`.
  - Mit dem neuen Code besteht `test_aktualisierung.py`.
  - `alle_tests.sh` in beiden Versionen grün.

### NEXT
- Durchsicht der Oberflächen-Module.

## P-2026-09-25-29 kern-module-lesbar

### EINGELESEN
- Manuels Auftrag aus P-2026-09-25-27: Code gut dokumentiert und
  kommentiert, für jeden menschlichen Programmierer leicht zu lesen, „kein
  AI-Slop“, das Vorhandene „to the max“ optimieren.
- Durchsicht von Hand: alle Module ohne Oberfläche (`kette`, `maschine`,
  `export`, `sprache`, `hilfe`, `aktualisierung`, `__init__`).

### DATEIEN
- `camaddon/kette.py`, `maschine.py`, `export.py`, `sprache.py`, `hilfe.py`,
  `aktualisierung.py`, `__init__.py` (überarbeitet)
- `camaddon/gui_maschine.py`, `gui_zeigen.py` (nur auf die neuen Namen
  umgestellt; die Durchsicht folgt als eigener Patch)
- `tests/test_kette.py`, `test_maschine.py`, `test_aktualisierung.py` (neue
  Namen)
- `docs/STATUS_SNAPSHOT.md` (drei Befunde als B-001 bis B-003)
- `package.xml` (Version 0.3.3)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Jedes Kern-Modul sagt oben, wozu es da ist; Funktionen und Namen sagen, was
gemeint ist; nichts steht doppelt. Das Verhalten bleibt gleich: alle
Prüfungen und Szenarien in beiden FreeCAD-Versionen grün.

### DONE
- **kette.py**
  - `lies_kette()` besteht aus vier benannten Schritten, je eine Funktion:
    Gelenke sortieren, Glieder bilden, Achsen als Baum, Nicht-Angebundenes
    melden.
  - Klarere Namen:
    - `Gelenk` → `Achse`; das Gelenk-Objekt der Assembly steht in
      `achse.gelenk`.
    - `Kette.gelenke` → `achsen`, `festes_glied()` → `bett()`,
      `pfad_zum_festen_glied()` → `pfad_zum_bett()`.
    - `Glied.koerper` → `bauteile`, `Glied.fest` → `ist_bett`.
  - Neu: `Kette.achse_von(gelenk)`. Sie ersetzt die an fünf Stellen
    wiederholte Suche `next(g for g in kette.gelenke if g.objekt == …)`.
  - `Glied.nummer` entfällt, es wurde nie gelesen.
  - Die Zusammenfassung starr verbundener Bauteile (Union-Find) ist erklärt.
- **maschine.py**
  - Die drei Proxys erben `dumps`/`loads` von einer gemeinsamen Grundklasse.
  - Die Eigenschaften stehen als Tabelle, je Gruppe im Eigenschaften-Editor.
  - `ist_betriebsart()`, `ist_aufnahme()` und `aufnahmeart_text()` ersetzen
    wiederholte Ausdrücke, auch in der Oberfläche.
  - `pruefe()` ist in drei Teile zerlegt: Betriebsarten, Aufnahmen,
    Revolver.
  - Das Entfernen einer früheren Platzverteilung ist eine eigene Funktion.
  - Die Editor-Modi heißen `_SICHTBAR` und `_AUSGEBLENDET` statt 0 und 2.
  - Entfernt:
    - Das Nachrüsten der Eigenschaft `Platz` beim Laden. Dateien ohne sie
      gibt es nur aus der Entwicklung; das Addon war nie veröffentlicht.
    - Eine Wächterzeile, deren Fall nie eintritt. Ausprobiert: FreeCAD ruft
      `onChanged` weder beim Anlegen einer Eigenschaft noch beim Laden
      einer Datei auf (1.1.3 und Wochen-Build).
- **export.py**
  - Linear- und Drehachse entstehen in eigenen Funktionen, mit
    Schlüsselwort-Argumenten statt acht Positions-Argumenten.
  - FreeCADs Vorgaben sind benannte Konstanten: `VORGABE_EILGANG`,
    `VORGABE_DREHGESCHWINDIGKEIT`.
  - Die Eltern-Achse wird über `pfad_zum_bett()` gesucht, nicht mehr über
    ein eigenes Wörterbuch.
- **sprache.py, hilfe.py:** `rueckfall_reihe()` ersetzt dreimal dieselbe
  Sprachfolge.
- **__init__.py, aktualisierung.py**
  - `version_aus_xml()` ersetzt zwei Kopien desselben Codes.
  - Der nie genutzte Parameter `git=` entfällt.
  - `pruefe()` ist in benannte Teile zerlegt: `_vergleiche_mit_github`,
    `_ist_vorfahr`.
- **Sichtbar geändert, beides bewusst:**
  - `pruefe()` liefert erst alle Warnungen, dann die Hinweise. Vorher stand
    der Hinweis „keine Werkzeugaufnahme“ zwischen Warnungen.
  - Die Meldungen der Kette folgen den vier Schritten. Ein loser Körper
    steht jetzt nach „doppelt gelagert“, nicht mehr davor.
- Version 0.3.3, weil sich die Reihenfolge der Meldungen sichtbar ändert.
- **Drei Befunde**, als B-001 bis B-003 in den Snapshot aufgenommen. Sie
  sind nicht behoben, weil 1 Patch = 1 Thema:
  - B-001 und B-002: zwei Lücken im Bericht der Übergabe an CAM.
  - B-003: P-2026-09-25-27 und -28 kamen ohne neue Version auf `main`. Die
    Update-Suche hätte „neue Version 0.3.2 (installiert ist 0.3.2)“
    angezeigt. Mit 0.3.3 ist das für diesmal erledigt, die Ursache bleibt.

### TEST
- Von der KI ausgeführt:
  - black und ruff sauber.
  - `alle_tests.sh` in beiden Versionen grün: 8 Prüfungen und 6 Szenarien;
    in 1.1.3 wird der Export übersprungen.
  - Probe in 1.1.3 und im Wochen-Build: Beim Anlegen einer
    Aufzählungs-Eigenschaft und beim Laden einer Datei ruft FreeCAD
    `onChanged` nicht auf, beim Laden nur `onDocumentRestored`.

### NEXT
- Oberflächen-Module: `gui_maschine` aufteilen und aufräumen, danach
  `gui_zeigen`, `gui_start`, `gui_sprachwahl`, `gui_aktualisierung`.

## P-2026-09-25-28 szenarien-sauber-beenden

### EINGELESEN
- Zeitstempel der Ergebnisdateien aus dem Lauf von P-2026-09-25-27: Drei
  Szenarien je Version brauchten genau 180 s, also das Zeitlimit.

### DATEIEN
- `tests/gui/_lauf/szenario_lauf.py` (am Ende Aufgabenfenster und Dokumente
  schließen)
- `scripts/oberflaeche_testen.sh` (Zeitlimit gilt als Fehler)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`scripts/alle_tests.sh` läuft in beiden FreeCAD-Versionen grün durch, in etwa
2 statt 22 Minuten. Ein Szenario, nach dem FreeCAD sich nicht beendet, gilt
als Fehler.

### DONE
- **Ursache:** Nach Szenarien mit geänderten Dokumenten fragte FreeCAD beim
  Beenden „Änderungen speichern?“ und wartete, bis `timeout` nach 180 s
  abbrach. Das Ergebnis war schon vorher geschrieben, deshalb blieb der
  Fehler unsichtbar.
- Der Läufer schließt jetzt vor dem Beenden das Aufgabenfenster und alle
  Dokumente, ohne Rückfrage.
- `oberflaeche_testen.sh` wertet einen Abbruch durch das Zeitlimit
  (Rückgabe 124) als **Fehler**: „FreeCAD hat sich nicht beendet“. So bleibt
  ein Hänger nie wieder unbemerkt.

### TEST
- Von der KI ausgeführt:
  - `alle_tests.sh` in beiden Versionen grün, **130 s** für alles zusammen
    (vorher etwa 22 Minuten).
  - Gegenprobe ohne das Schließen der Dokumente:
    `szenario_uebergeben` ergibt „FEHLER … FreeCAD hat sich nicht beendet
    (Zeitlimit 180 s)“.

### NEXT
- Durchsicht von Hand: Kern-Module.

## P-2026-09-25-27 black-und-ruff

### EINGELESEN
- Manuels Auftrag: Code gut dokumentiert, kommentiert, für jeden menschlichen
  Programmierer leicht lesbar und sauber, „kein AI-Slop“. Das Vorhandene soll
  kontrolliert und „to the max“ optimiert werden. Dieser Patch ist der erste,
  mechanische Schritt dazu. Die Durchsicht von Hand folgt als eigene Patches.

### DATEIEN
- `pyproject.toml` (neu: Einstellungen für black und ruff)
- Alle Python-Dateien (Formatierung, Reihenfolge der Importe)
- Tests: Dateien über `Path.read_text`/`write_text` statt offener `open()`,
  unbenutzte Importe entfernt oder begründet
- `scripts/testumgebung_einrichten.sh` (installiert black und ruff mit),
  `scripts/alle_tests.sh` (prüft sie als Erstes)
- `docs/arbeitsregeln.md` (Abschnitte 5 und 7), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`black --check .` und `ruff check .` melden nichts, und `scripts/alle_tests.sh`
ist in beiden FreeCAD-Versionen grün.

### DONE
- **Werkzeuge wie bei FreeCAD:** black (Zeilenlänge 100) und ruff. Geprüft
  werden Stil, unbenutzte Namen, typische Fehlerquellen, Importreihenfolge,
  veraltete Schreibweisen für Python 3.11 und unnötig umständliche
  Konstrukte. Python 3.11 ist der Stand, den FreeCAD 1.1.x mitbringt.
- **Ausgangslage:**
  - 19 von 30 Dateien waren uneinheitlich formatiert.
  - 23 Befunde, fast alle in den Tests:
    - `open()` ohne `with`
    - unsortierte Importe
    - zwei unbenutzte Importe
- **Behoben:**
  - Dateien lesen die Tests jetzt über `Path(…).read_text("utf-8")`.
  - Der Import von `Part` in `test_umgebung.py` ist nötig, weil er den
    Objekttyp `Part::Box` registriert. Er bleibt, jetzt mit Begründung.
  - Das offen bleibende Absturzprotokoll im Szenario-Läufer ist begründet
    markiert.
  - Die Tests müssen den Suchpfad vor dem Import setzen. Statt sieben
    verstreuter `# noqa: E402` gibt es jetzt eine Ausnahme für `tests/` in
    `pyproject.toml`.
- **Neue Regeln** (Abschnitte 5 und 7):
  - black und ruff ohne Befund
  - jedes `noqa` mit Begründung
  - Docstrings für Module und öffentliche Funktionen
  - Hilfsfunktion statt Wiederholung

### TEST
- Von der KI ausgeführt: `scripts/alle_tests.sh` ergibt „ok black, ruff“,
  in 1.1.3 und im Wochen-Build alle Prüfungen und Szenarien `ok` (Export in
  1.1.3 übersprungen).
- **Aufgefallen:** Drei Szenarien brauchen jeweils genau 180 s, also das
  Zeitlimit. FreeCAD beendet sich nach dem Szenario nicht von selbst. Das
  Ergebnis steht schon vorher fest, deshalb sind sie trotzdem grün. Behoben
  als eigener Patch.

### NEXT
- Szenarien sauber beenden, dann die Durchsicht von Hand: Kern, Oberfläche,
  Tests, Entwickler-Doku.

## P-2026-09-25-26 zwei-freecad-versionen

### EINGELESEN
- FreeCAD 1.1.3 aus conda-forge. Zuerst nur das Paket entpackt und dessen
  Quelltext mit dem Wochen-Build verglichen, dann als volle Testumgebung.
- `Mod/Assembly/UtilsAssembly.py` und `JointObject.py` in 1.1.3: Welche der
  vom Addon genutzten Funktionen und Eigenschaften gibt es dort?

### DATEIEN
- `camaddon/export.py` (`verfuegbar()`), `camaddon/gui_maschine.py`
  (Erklärung statt Fehler)
- `tests/test_export.py` (übersprungen ohne Maschinendefinition),
  `tests/gui/szenario_uebergeben.py` (prüft in 1.1.3 die Erklärung)
- `scripts/testumgebung_einrichten.sh` (beide Versionen),
  `scripts/alle_tests.sh` (neu), `scripts/tests_ausfuehren.sh` (versteht
  „übersprungen“)
- `translations/de.json`, `translations/en.json`
- `CHATSTART.md` (Festlegung), `docs/arbeitsregeln.md` (Abschnitte 0, 5, 7, 9),
  `README.md`, `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 2),
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md` (Kopf)
- `package.xml` (0.3.2)

### AKZEPTANZKRITERIUM
`scripts/alle_tests.sh` läuft in FreeCAD 1.1.3 und im Wochen-Build grün. In
1.1.3 zeigt „An CAM übergeben“ den Satz „Deine FreeCAD-Version (1.1.3) kennt
noch keine Maschinendefinition in CAM …“ statt eines Fehlers.

### DONE
Manuel sitzt am PC und hat **FreeCAD 1.1.3** installiert, nicht den
Wochen-Build. Er fragte, ob dort die 4-Achs-Funktionen fehlen. Das stimmt:
In 1.1.3 fehlen die neuen Rundachs-Strategien (`rotary_*`) und die
CAM-Maschinendefinition. Vorhanden sind nur die alten Hilfen (3D-Oberfläche
„Rotational“, Dressup „Axis Map“).

Die Entscheidung aus P-2026-09-25-05 (nur Wochen-Build) passte damit nicht
mehr zu Manuels Rechner. Aus einer Auswahl hat er **„Beide unterstützen“**
gewählt. Die Alternativen waren „Wochen-Build dazu“ (meine Empfehlung) und
„auf 1.1.3 umstellen“.

- **Befund 1.1.3:**
  - Das Auslesen der Baugruppe, das Maschinenobjekt, der Dialog, das Zeigen,
    die Hilfe und die Update-Suche laufen unverändert.
  - Es fehlen die Eigenschaft `Suppressed` und die RigidGroup-Gelenke. Das
    Addon fragt sie nur mit `getattr`/`hasattr` ab, deshalb schadet das nicht.
  - Einziger echter Ausfall ist der Export, weil `Mod/CAM/Machine` fehlt.
- **Der Export erklärt sich:** `export.verfuegbar()` prüft das Modul und nicht
  eine Versionsnummer. So wird die Übergabe von selbst frei, sobald die
  stabile Version sie bekommt. Der Knopf bleibt bedienbar und zeigt eine
  Erklärung, weil ein grauer Knopf nichts erklärt. Die Erklärung ist nicht
  blockierend (`open()` statt `exec()`).
- **Tests in beiden Versionen:**
  - `testumgebung_einrichten.sh` installiert beide: den Wochen-Build und
    `freecad<2000` mit Python 3.11, wie in den offiziellen Paketen.
    Wochen-Builds tragen ein Datum als Versionsnummer.
  - `alle_tests.sh` lässt alles in beiden laufen.
  - „Übersprungen“ ist nur für fehlende Funktionen einer Version erlaubt.
    Das Szenario prüft dort stattdessen die Erklärung.
- Die Regeln sind angepasst: Festlegung in `CHATSTART.md`, Zielsystem,
  Pflichtprüfung in beiden Versionen, Versionscheck auch für neue stabile
  Versionen. Die vorige stabile Version fällt heraus, sobald eine neue da ist.
- Beim ersten Lauf gegen 1.1.3 kam ein Fehler ans Licht, der beide Versionen
  betraf: Ursprünge wurden als Koordinatensystem angeboten. Er ist als
  eigener Patch behoben (P-2026-09-25-25).

### TEST
- Von der KI ausgeführt, `scripts/alle_tests.sh`:
  - 1.1.3: acht Prüfungen ohne Fenster, davon eine übersprungen (Export),
    alle Szenarien `ok`
  - Wochen-Build: alle Prüfungen `ok`, alle Szenarien `ok`
  - Screenshot der Erklärung in 1.1.3 angesehen
- `testumgebung_einrichten.sh` selbst ist nicht von Grund auf durchgelaufen.
  Die beiden `micromamba create` darin habe ich von Hand mit denselben
  Angaben ausgeführt.
- **Nicht getestet:** Manuels FreeCAD 1.1.3 unter Windows.

### NEXT
- Manuels Test in 1.1.3: Installation mit GitHub Desktop, Dialog, Erklärung
  bei „An CAM übergeben“, Update-Suche.

## P-2026-09-25-25 lcs-auswahl-ohne-ursprung

### EINGELESEN
- `camaddon/gui_maschine.py` (`_alle_lcs`, Verteilhilfe, `_aufnahme_neu`).
- Befund aus dem ersten Lauf der Oberflächentests gegen FreeCAD 1.1.3.

### DATEIEN
- `camaddon/gui_maschine.py`, `tests/gui/szenario_maschine_bearbeiten.py`
- `package.xml` (0.3.1), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In der Auswahl „Koordinatensystem“ einer Aufnahme und in der Verteilhilfe
stehen nur echte Koordinatensysteme (Spannflaeche, Werkzeugplatz), keine
Ursprünge wie „Origin005“.

### DONE
- **Befund:** Der Ursprung eines Parts oder Körpers (`App::Origin`) ist für
  FreeCAD ebenfalls ein `App::LocalCoordinateSystem`. Der Dialog bot deshalb
  „Origin“, „Origin001“ … als Koordinatensystem für Aufnahmen an. Beim
  Anlegen einer Aufnahme ohne Auswahl konnte die Vorauswahl sogar einen
  Ursprung treffen. Aufgefallen ist das im Test gegen 1.1.3, weil dort die
  Reihenfolge anders ist und die Verteilhilfe „Origin005“ statt
  „Werkzeugplatz“ vorwählte. Der Fehler steckte aber in beiden Versionen.
- `_alle_lcs()` lässt Ursprünge weg. Das wirkt auf die Auswahlliste, die
  Vorauswahl bei „+ Aufnahme“ und die Verteilhilfe.
- Das Szenario prüft jetzt, dass die Verteilhilfe **nur** den Werkzeugplatz
  anbietet und dass nirgends ein Ursprung auftaucht.

### TEST
- Von der KI ausgeführt: `szenario_maschine_bearbeiten` `ok`, auf 1.1.3 und
  im Wochen-Build.
- Gegenprobe mit altem Dialog und neuer Prüfung im Wochen-Build: `FEHLER`,
  „Ursprünge als Koordinatensystem angeboten: ['Origin', 'Spannflaeche',
  'Origin001', 'Werkzeugplatz', 'Origin002']“.

### NEXT
- Beide FreeCAD-Versionen fest in Tests und Regeln verankern, Übergabe an CAM
  in 1.1.3 erklären statt Fehler.

## P-2026-09-25-24 update-suche-per-git

### EINGELESEN
- Ergebnis P-2026-09-25-23: Der Addon-Manager aktualisiert private
  Repositories nicht.
- `docs/arbeitsregeln.md` Abschnitt 7 („keine Shell-Aufrufe“).

### DATEIEN
- `camaddon/aktualisierung.py`, `camaddon/gui_aktualisierung.py` (neu)
- `camaddon/gui_start.py` (Suche beim Start), `camaddon/gui_sprachwahl.py`
  (Gruppe „Updates“ auf der Einstellungsseite)
- `translations/de.json`, `translations/en.json`
- `tests/test_aktualisierung.py`, `tests/gui/szenario_update.py` (neu),
  `scripts/oberflaeche_testen.sh` (ohne Update-Suche)
- `package.xml` (0.3.0), `README.md`, `CHATSTART.md`,
  `docs/arbeitsregeln.md` (Ausnahme Git), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Liegt auf GitHub eine neuere Version, fragt das Addon kurz nach dem Start
von FreeCAD „Eine neue Version des CAM-Addons ist da: … Jetzt
aktualisieren?“. Ein Klick holt sie und bittet um einen Neustart.

### DONE
Manuel hat aus einer Auswahl gewählt: Das Addon soll in der privaten Phase
**selbst nach Updates schauen und nachfragen**. Dafür hat er einer Ausnahme
von der Regel „keine Aufrufe externer Programme“ zugestimmt, beschränkt auf
Git.

- **Suche:** Das Addon ruft Git im eigenen Ordner auf (`fetch`, Vergleich mit
  `origin/main`, Version aus `package.xml` auf beiden Seiten). Das passiert
  im Hintergrund und 5 s nach dem Start, damit FreeCAD nicht wartet. Git
  kommt aus dem Suchpfad, sonst aus GitHub Desktop, das sein Git unter
  Windows nicht in den Suchpfad legt. Angemeldet wird mit dem, was auf dem
  Rechner eingerichtet ist. Im Addon liegt kein Schlüssel.
- **Git fragt nie nach**: Es gibt kein Terminal, keinen Credential-Dialog
  und ein Zeitlimit von 30 s. Ohne Fenster würde eine Rückfrage ewig hängen.
- **Aktualisieren:** nur vorwärts (`merge --ff-only`). Gibt es im Ordner
  eigene Änderungen oder eigene Commits, aktualisiert das Addon nicht,
  sondern sagt Bescheid, einmal je neuer Version.
- **Ruhig bleiben:** Kein Git auf dem Rechner meldet das Addon einmal mit
  Anleitung. Kein Netz oder keine Anmeldung führt beim Start nur zu einer
  Zeile im Report-Fenster. Eine ZIP-Installation oder ein aktueller Stand
  bleiben still.
- **Einstellungen:** Schalter „Beim Start von FreeCAD nach Updates suchen“
  (vorbelegt: an) und Knopf „Jetzt nach Updates suchen“. Der Knopf meldet
  auch „Du hast die neueste Version“.
- **Befund:** Die Ausgabe von Git wurde mit der Kodierung des Systems gelesen,
  `package.xml` enthält aber Umlaute. Im Test brach das mit einem
  ASCII-Fehler ab, unter Windows (cp1252) wäre es genauso passiert. Jetzt
  wird immer UTF-8 gelesen.
- Die Oberflächen-Szenarien schalten die Suche beim Start ab
  (`CAMADDON_OHNE_UPDATE`), damit sie kein Netz brauchen.
- Die Version ist jetzt 0.3.0, weil eine neue Funktion dazukam (Regel aus
  P-2026-09-25-22).

### TEST
- Von der KI ausgeführt, mit echten Git-Repos im Temp-Ordner (nacktes Repo
  als „GitHub“):
  - `test_aktualisierung.py` `ok`, mit den Fällen aktuell, neue Version,
    aktualisieren, eigene Änderung, kein Git-Ordner, kein Git und Repo nicht
    erreichbar
  - `szenario_update` `ok`: Der Hinweis erscheint, „Jetzt aktualisieren“ holt
    9.9.0, und das Abschalten in den Einstellungen wird gespeichert.
    Screenshots angesehen.
- Alle Prüfungen ohne Fenster und alle Szenarien `ok`.
- **Nicht getestet:** die Anmeldung über GitHub Desktop auf Manuels
  Windows-Rechner. Ob dessen Git ohne Rückfrage an das private Repo kommt,
  zeigt erst der echte Rechner. Wenn nicht, erscheint beim Start nur eine
  Zeile im Report-Fenster, und „Jetzt nach Updates suchen“ nennt den Grund.

### NEXT
- Manuels Test: Installation mit GitHub Desktop, dann Dialog, Übergabe an
  CAM und Update-Hinweis.

## P-2026-09-25-23 installieren-privat

### EINGELESEN
- `Mod/AddonManager`: `addonmanager_installer.py` (`_determine_install_method`,
  `_install_by_copy`), `addonmanager_utilities.construct_git_url` (lokale
  Pfade), `addonmanager_workers_startup.UpdateChecker`.

### DATEIEN
- `README.md` (Installieren in der privaten Phase mit GitHub Desktop, dazu
  der Addon-Manager-Weg für später)
- `docs/STATUS_SNAPSHOT.md` (T-005), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Das README führt als ersten Weg die Installation mit GitHub Desktop direkt in
den Mod-Ordner; der Addon-Manager-Weg ist als „erst wenn öffentlich“
gekennzeichnet.

### DONE
Manuel will das Repo vorerst **nicht veröffentlichen**. Zum Testen soll es
lokal bleiben. Deshalb habe ich ausprobiert, ob der Addon-Manager mit einem
**lokalen Ordner** als eigenem Repository arbeitet: unsichtbare Oberfläche,
eigenes Profil, lokaler Klon des Repos.

- Die **Installation** klappt. Der Addon-Manager kopiert den Ordner.
  Allerdings liest er `package.xml` aus einem lokalen Pfad nicht und zeigt
  das Addon deshalb ohne Beschreibung an.
- **Updates** erkennt er nicht: Nach einem neuen Commit im lokalen Ordner
  meldet er „No update available“. Der eingebaute Git-Stand zeigt weiter auf
  GitHub, und dort kommt er nicht hin.
- Ergebnis: In der privaten Phase bringt der Addon-Manager nichts. Der
  einfachste Weg ist GitHub Desktop, das Repo direkt in den Mod-Ordner holen
  und zum Aktualisieren „Pull“ drücken. Das README beschreibt das jetzt als
  ersten Weg.
- **Fehler im Testaufbau, gefunden und folgenlos:** Beim ersten Versuch lief
  der Addon-Manager im Profil von `oberflaeche_testen.sh`. Dort ist unser
  Repo als Verknüpfung im Mod-Ordner eingetragen, also kopierte der
  Addon-Manager durch die Verknüpfung **in unser Repo**. Danach geprüft:
  `git status` sauber, `git fsck` ohne Befund. Die Kopie war derselbe Stand.
  Den sauberen Versuch habe ich in einem eigenen Profil ohne die Verknüpfung
  gemacht. Für Tests des Addon-Managers darf dieses Skript nicht benutzt
  werden.
- Die Regel „was auf `main` liegt, kommt als Update an“ (P-2026-09-25-22)
  bleibt, denn mit GitHub Desktop gilt sie genauso.

### TEST
- Von der KI ausgeführt, in einem eigenen Profil unter Xvfb:
  `AddonInstaller.run()` mit lokalem Pfad ergibt `True`, der Ordner liegt im
  Mod-Verzeichnis. `UpdateChecker.check_workbench` ergibt nach einem neuen
  Commit im lokalen Ordner „No update available“.
- Die Installation mit GitHub Desktop auf Manuels Rechner ist nicht
  getestet.

### NEXT
- Manuel entscheidet, ob das Addon für die private Phase selbst nach Updates
  schauen soll (Git im eigenen Ordner).

## P-2026-09-25-22 updates-ueber-addon-manager

### EINGELESEN
- `Mod/AddonManager/addonmanager_workers_startup.py`: `CustomRepositories`
  (eigene Repositories, je Zeile URL und Branch) und `UpdateChecker`. Bei
  Installation per Git wird über den Git-Stand geprüft, sonst über eine
  geänderte `package.xml`.

### DATEIEN
- `camaddon/__init__.py` (Version aus `package.xml`), `package.xml`
  (0.2.0)
- `tests/test_version.py` (neu)
- `README.md` (Installieren mit automatischen Updates),
  `docs/arbeitsregeln.md` (Abschnitt 4)
- `docs/STATUS_SNAPSHOT.md` (T-005), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer das README liest, kann das Addon als eigenes Repository in den
Addon-Manager eintragen und installieren. Das Addon meldet unter „Über“
dieselbe Version wie `package.xml`.

### DONE
Manuel hat gefragt, ob Autoupdate geht. Aus einer Auswahl hat er gewählt:
**Repo öffentlich machen**, Updates über FreeCADs Addon-Manager. Die
Alternativen waren „privat, später öffentlich“ und ein eigener Update-Knopf
mit GitHub-Schlüssel je Rechner, von dem ich abgeraten habe.

- **Kein eigener Update-Code nötig.** Der Addon-Manager prüft und
  installiert selbst, wenn das Repo als „eigenes Repository“ eingetragen ist.
  Voraussetzung: Das Repo ist öffentlich. Das Umschalten kann nur Manuel
  machen (T-005).
- **Version nur noch an einer Stelle:** `package.xml`. `camaddon.VERSION`
  liest sie von dort. Vorher stand 0.1.0 zusätzlich im Code; zwei Angaben
  wären auseinandergelaufen. Die Version ist jetzt 0.2.0, weil seit 0.1.0 der
  Dialog und die Übergabe an CAM dazugekommen sind.
- **Neue Regel** (Abschnitt 4): Was auf `main` liegt, kommt bei Manuel als
  Update an. Gepusht wird nur, was alle Prüfungen bestanden hat. Ein Push mit
  sichtbarer Änderung zählt die Version hoch.
- Vor dem Öffentlichmachen habe ich das Repo durchgesehen: keine
  E-Mail-Adresse, keine Zugangsdaten. Manuel ist darauf hingewiesen, dass
  sein Name in `package.xml` und der Doku steht und dass „zeiterfassung“
  einmal als Vorlage erwähnt wird.

### TEST
- Von der KI ausgeführt: alle sieben Prüfungen ohne Fenster `ok`, die
  Szenarien `erster_start` und `uebergeben` `ok`.
- Gegenprobe: Mit Version „0.2“ schlägt `test_version.py` fehl („hat nicht
  die Form 1.2.3“).
- **Nicht getestet:** Installation und Update über den Addon-Manager. Das
  geht erst, wenn das Repo öffentlich ist, und gehört dann zu Manuels Test.

### NEXT
- T-005 (Manuel), dann Test über den Addon-Manager.

## P-2026-09-25-21 knopf-an-cam-uebergeben

### EINGELESEN
- `camaddon/export.py` (P-2026-09-25-20), Spezifikation W-001, Stufe 2.

### DATEIEN
- `camaddon/gui_maschine.py` (Knopf, Nachfrage, Berichtsfenster)
- `camaddon/export.py` (Bericht in drei Teilen, Drehachsen in U/min)
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_uebergeben.py` (neu), `tests/test_export.py`
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Klick auf „An CAM übergeben“ im Dialog der fertigen Beispiel-Drehmaschine
öffnet ein Fenster „Die Maschine „Testdrehmaschine“ steht jetzt in CAM zur
Auswahl.“ mit den angekommenen Achsen, und CAM listet die Maschine.

### DONE
- Unten im Dialog gibt es den Knopf **„An CAM übergeben“**:
  - Gibt es noch Warnungen, fragt er nach, ob trotzdem übergeben werden soll,
    und nennt die Anzahl.
  - Schlägt das Speichern fehl, erscheint eine Meldung mit dem Grund.
- Das **Berichtsfenster** sagt, wo die Maschine in CAM zu finden ist, und
  gliedert sich in drei Teile:
  - **In CAM angekommen**
  - **Bitte prüfen**: fehlende Grenzen, unklare Tisch/Kopf-Rolle, Fehler in
    der Achsfolge
  - **Nur hier in der Maschine gespeichert**: Beschleunigung, Ruck, Vorschub,
    Revolver
- **Beim Durchsehen des ersten Screenshots verbessert:**
  - Drehachsen standen in °/min im Bericht, eingegeben werden aber U/min.
    Jetzt steht die eingegebene Einheit da.
  - „Keine Begrenzung“ stand unter „Nur hier gespeichert“. Dafür gibt es
    jetzt den eigenen Teil „Bitte prüfen“.
- Beim Schreiben der Texte waren Zeilenumbrüche als `\n`-Zeichen im Text
  gelandet. Das ist korrigiert.

### TEST
- Von der KI ausgeführt: alle Prüfungen ohne Fenster `ok`, alle fünf
  Szenarien `ok`, Screenshot des Berichts angesehen.
- **Nicht geprüft:** Das Szenario prüft nur, dass CAM die Maschine listet.
  Ob sie im Job-Dialog von CAM tatsächlich auswählbar ist und dort richtig
  arbeitet, prüft Manuel.
- Die Nachfrage bei Warnungen erscheint als modaler Dialog und blockiert
  deshalb das Szenario. Sie ist im Test umgangen (`nachfragen=False`) und nicht
  automatisch geprüft.

### NEXT
- Manuels Test von Stufe 1 und 2, danach Stufe 3 (von Hand verfahren).

## P-2026-09-25-20 export-cam-maschine

### EINGELESEN
- Spezifikation W-001, Stufe 2.
- `Mod/CAM/Machine/models/machine.py`: `Machine`, `LinearAxis`,
  `RotaryAxis`, `Toolhead`, `to_dict`/`from_dict`,
  `MachineFactory.save_configuration`/`list_configurations`,
  `validate_kinematic_chain`.

### DATEIEN
- `camaddon/export.py` (neu)
- `tests/test_export.py` (neu), `tests/beispielmaschinen.py`
  (`drehmaschine_komplett`)
- `translations/de.json`, `translations/en.json`
- `CHATSTART.md` (Lesekarte), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die fertig beschriebene Beispiel-Drehmaschine wird als `Testdrehmaschine.fcm`
gespeichert. CAM listet sie danach, und neu geladen hat sie X1 (Richtung X,
0–200 mm, 24000 mm/min, hängt an Z1, im Kopf), Z1, C4 (Tisch, 36000 °/min)
und die Spindel S4.

### DONE
- `baue_cam_maschine()` übersetzt das Maschinenobjekt in FreeCADs `Machine`:
  - Linear → `LinearAxis`, Positionieren → `RotaryAxis` (U/min × 360 =
    °/min), Spindel → `Toolhead`.
  - Tisch/Kopf aus `rollen()`.
  - Die Eltern-Achse ist die nächste NC-Achse zum Bett hin. Gelenke nur mit
    Spindel oder Revolver werden übersprungen.
  - Die Grenzen kommen aus dem Gelenk. Fehlen sie, gibt es einen sehr großen
    Bereich und einen Satz im Bericht.
- `exportiere()` speichert über `MachineFactory.save_configuration` in den
  Maschinenordner von CAM. Der Dateiname kommt aus dem Maschinennamen, ein
  zweiter Export überschreibt dieselbe Datei.
- **Bericht** in ganzen Sätzen: was übertragen wurde, und was CAM nicht kennt
  und deshalb nur im Dokument bleibt (größter Vorschub, Beschleunigung, Ruck,
  Revolver mit Plätzen, fehlende Grenzen, unklare Tisch/Kopf-Rolle, Fehler
  aus `validate_kinematic_chain`).
- **Befund: Fehler in FreeCAD.** `Machine.to_dict` schreibt eine Achse als
  `[Ursprung, Richtung]`. `Machine.from_dict` hält bei Linearachsen aber den
  Ursprung für die Richtung, sobald er nicht (0,0,0) ist. Jede solche
  Linearachse kommt nach Speichern und Laden verdreht zurück; im Test wurde X1
  von (1,0,0) zu (0,95, 0,25, 0,18). Umgangen, indem Linearachsen mit Ursprung
  (0,0,0) übergeben werden. Für eine Linearachse zählt nur die Richtung. Der
  Fehler sollte bei FreeCAD gemeldet werden; das ist ein eigener Punkt im
  Snapshot.
- Der Test schreibt nicht in Manuels echten CAM-Ordner
  (`set_config_directory` auf einen Temp-Ordner) und stellt die Sprache für
  seine Satzprüfungen fest auf Deutsch.

### TEST
- Von der KI ohne Fenster ausgeführt: alle sechs Prüfungen `ok`, volle
  Ausgabe von `test_export.py` ohne Warnungen.
- Ohne den Umweg über Ursprung 0 schlug `test_export.py` fehl: „X1: Richtung X
  erwartet“. So wurde der FreeCAD-Fehler gefunden.

### NEXT
- Knopf „An CAM übergeben“ im Dialog mit Anzeige des Berichts.

## P-2026-09-25-19 hilfe-im-dialog

### EINGELESEN
- Spezifikation W-001, Abschnitte 8 und 11. Die Anleitung „Beschleunigung
  ermitteln“ ist aus Abschnitt 8 übernommen.
- `docs/arbeitsregeln.md`, Abschnitt 8 (drei Stufen Hilfe).

### DATEIEN
- `help/de/*.html`, `help/en/*.html` (je vier Seiten, neu)
- `camaddon/hilfe.py` (neu), `camaddon/gui_maschine.py`
- `translations/de.json`, `translations/en.json`, `translations/README.md`
- `tests/test_hilfe.py`, `tests/gui/szenario_hilfe.py` (neu)
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Klick auf (?) bei „Achsen“ öffnet die Seite „Achsen und Betriebsarten“.
Ihr Verweis führt zu „Beschleunigung ermitteln“, und bei einer linearen
Betriebsart steht unter den Feldern der Verweis „Wie finde ich die
Beschleunigung heraus?“.

### DONE
- **Vier Hilfeseiten** auf Deutsch und Englisch:
  - Achsen und Betriebsarten (mit S4/C4, Gelenken ohne Betriebsart, Kennwerten
    und Zeigen)
  - Beschleunigung ermitteln (Maschinendaten, Datenblatt, Messen mit
    Beispiel)
  - Aufnahmen und Revolver (LCS anlegen, Verteilhilfe)
  - Glieder (Schwenkbrücke, eine Achse ein Gelenk)
- **Knöpfe (?)** rechts neben den Überschriften Achsen, Aufnahmen und
  Glieder. Das Hilfefenster ist nicht modal, damit man lesen und dabei
  weiterarbeiten kann. Verweise zwischen den Seiten funktionieren.
- Bei Betriebsarten mit Beschleunigung steht der Verweis „Wie finde ich die
  Beschleunigung heraus?“ direkt unter den Feldern, also dort, wo die Frage
  aufkommt.
- Für die Hilfe gilt derselbe Rückfall wie für die kurzen Texte: gewählte
  Sprache, Englisch, Deutsch. `translations/README.md` erklärt jetzt auch das
  Übersetzen der Hilfe.
- `test_hilfe.py` prüft:
  - jedes Thema auf de und en vorhanden, mit Überschrift
  - keine toten Verweise zwischen den Seiten
  - keine Seite ohne Thema
  - jedes vom Dialog benutzte Thema existiert
- Die Hilfe zur Beschleunigung sagt ausdrücklich, dass die
  Maschinendaten-Nummern aus allgemeinem Wissen stammen und im Handbuch zu
  prüfen sind. Das Gleiche steht als offener Punkt in P-2026-09-25-07.

### TEST
- Von der KI ausgeführt: alle Prüfungen ohne Fenster `ok` (jetzt fünf),
  alle vier Szenarien `ok`.
- Screenshots beider Hilfeseiten angesehen: gut lesbar, Tabelle und Formel
  werden sauber dargestellt.

### NEXT
- Manuels Test des Dialogs in seinem FreeCAD, danach Stufe 2 (Export).

## P-2026-09-25-18 zeigen-in-3d

### EINGELESEN
- Spezifikation W-001, Abschnitt 11 („Zeigen, welches Teil gemeint ist“).
- `camaddon/gui_maschine.py` (P-2026-09-25-17).

### DATEIEN
- `camaddon/gui_zeigen.py` (neu), `camaddon/gui_maschine.py`
- `tests/gui/szenario_zeigen.py` (neu)
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Fährt man im Dialog über die Achse X der Beispiel-Drehmaschine, werden
X-Schlitten und Revolver hervorgehoben und bewegen sich einmal kurz hin und
her, Bett und Z-Schlitten nicht. Danach steht alles exakt wie vorher, auch
wenn mitten in der Bewegung OK gedrückt wird.

### DONE
- **Überfahren einer Zeile** (nach 250 ms Verweilen, nicht bei jedem
  Überstreichen):
  - **Gelenk oder Betriebsart:** Alle Körper, die sich mit dem Gelenk
    bewegen, auch weiter hinten in der Kette, werden hervorgehoben und
    bewegen sich einmal hin und her. Eine Linearachse fährt 10 % der
    Gliedgröße (5–50 mm), eine Drehachse dreht ±15° um ihre Achse.
  - **Glied:** Seine Körper werden hervorgehoben.
  - **Aufnahme:** Ihr LCS wird hervorgehoben.
  - **Revolvergruppe:** Alle Platz-LCS werden hervorgehoben.
- Das Hervorheben läuft über die Auswahl von FreeCAD, weil die Vorauswahl nur
  ein Objekt kann und ein Glied mehrere Körper hat.
- Die Bewegung verstellt keine Gelenke, sondern nur kurz die Lage der Körper.
  Danach wird die gespeicherte Lage exakt zurückgesetzt. Läuft die Bewegung
  für dasselbe Gelenk schon, beginnt sie nicht neu. OK und Abbrechen halten
  sie zuerst an und setzen zurück, erst danach wird die Transaktion
  abgeschlossen. So kann nichts Verschobenes gespeichert werden.

### TEST
- Von der KI ausgeführt: `szenario_zeigen` `ok`.
  - Beim Zeigen auf X bewegen sich X-Schlitten und Revolver, Bett, Z-Schlitten
    und Hauptspindel nicht.
  - Hervorgehoben sind genau X-Schlitten und Revolver.
  - Nach der Bewegung steht alles auf 1e-12 genau wie vorher.
  - Beim Glied der Spindel sind Hauptspindel und Futter hervorgehoben.
  - OK während der Revolver dreht lässt ihn nicht verdreht zurück.
- Alle Prüfungen ohne Fenster und alle drei Szenarien `ok`.
- **Nicht prüfbar im Test:** das echte Überfahren mit der Maus. Unter Xvfb
  gibt es keine Maus, deshalb ruft das Szenario die Zeige-Funktion direkt auf.
  Ob sich das Verweilen von 250 ms gut anfühlt, prüft Manuel.

### NEXT
- Hilfe-Knöpfe (?) mit den ausführlichen Texten.

## P-2026-09-25-17 dialog-maschine-bearbeiten

### EINGELESEN
- Spezifikation W-001, Abschnitte 7a und 11. Die Skizze des Dialogs hat Manuel
  im Chat mit „ganz ok“ freigegeben.

### DATEIEN
- `camaddon/gui_maschine.py` (neu), `resources/icons/maschine.svg` (neu)
- `camaddon/gui_start.py` (Befehl in der Werkzeugleiste)
- `camaddon/kette.py` (`Meldung.bezug`), `camaddon/maschine.py` (`bezug` an
  den Meldungen, `Bezeichnung`, `name_von`, `beschrifte`)
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_maschine_bearbeiten.py` (neu), `tests/test_maschine.py`
- `tests/gui/_lauf/szenario_lauf.py` (Absturzprotokoll),
  `scripts/oberflaeche_testen.sh` (Fehler bei mehreren Szenarien behoben)
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ablauf: Beispiel-Drehmaschine öffnen → „Maschine bearbeiten“ → Z1, X1, S4
und C4 (an der Spindel) sowie Revolver T anlegen und ausfüllen → Futter als
Werkstückaufnahme → 12 Plätze verteilen. Danach zeigt der Dialog „Alles
vollständig – keine Hinweise.“, OK ergibt genau einen Schritt Rückgängig,
Abbrechen verwirft.

### DONE
- **Befehl „Maschine bearbeiten“** in der Werkzeugleiste des Addons:
  - Die Baugruppe kommt aus der Auswahl, sonst aus der aktiven Assembly,
    sonst aus der einzigen im Dokument. Gibt es mehrere, fragt der Befehl.
  - Gibt es keine, erklärt eine Meldung, was zu tun ist. Der Knopf ist dafür
    nicht ausgegraut, denn ein grauer Knopf erklärt nichts.
- **Aufgabenfenster** nach der freigegebenen Skizze, mit den Bereichen Name,
  Achsen, Details, Aufnahmen, Glieder und Hinweise:
  - Das ganze Fenster ist **eine Transaktion**. OK ergibt einen Schritt
    Rückgängig, Abbrechen verwirft alles.
  - „+ Betriebsart“ bietet nur Arten an, die zum Gelenk passen, jeweils mit
    einem Satz Erklärung.
  - Pflichtfelder sind fett, leere optionale Felder zeigen „unbekannt“, die
    Einheit steht am Feld.
  - Das erste Gelenk ist beim Öffnen gewählt, damit „+ Betriebsart“ sofort
    bedienbar ist.
  - Revolverplätze stehen zugeklappt unter „Revolver T – 12 Plätze“.
  - Der Detailkasten erscheint unter der Liste, in der gerade gewählt ist.
  - Ein Klick auf einen Hinweis springt zur betroffenen Zeile.
  - „Plätze verteilen …“ öffnet einen kleinen Dialog für Revolver, ersten
    Platz und Anzahl.
- **Beim Durchsehen der Screenshots verbessert** (nach unserer Regel „keine
  Frage auf dem Bildschirm“):
  1. „+ Betriebsart“ war beim Öffnen ausgegraut.
  2. „wird von Hand verstellt“ stand anfangs bei jedem Gelenk. Jetzt steht
     dort „noch keine Betriebsart“, die Erklärung ist im Tooltip.
  3. Die Details einer Aufnahme standen oben bei den Achsen.
  4. Zwölf Plätze machten die Liste unübersichtlich.
  5. Der Detailtitel sagte nur „Werkzeug“.
- **Befund, Namen:** Eine Aufnahme „Futter“ hieß plötzlich „Futter001“, weil
  FreeCAD kein Label doppelt erlaubt und das Bauteil schon „Futter“ heißt.
  Deshalb gibt es jetzt `Bezeichnung` für Aufnahmen und `NcName` für
  Betriebsarten als eigentliche Namen. Das Label im Baum wird daraus gebildet
  („Futter · Werkstückaufnahme“, „X1 · Linear“), und die Meldungen nennen
  den Namen, nicht das Label.
- **Befund, Abstürze** (FreeCAD stürzte ab, gefunden mit dem neuen
  Absturzprotokoll):
  1. `int()` auf die Knopf-Konstanten scheitert unter PySide6. Jetzt werden
     die Flags direkt zurückgegeben.
  2. Das zeitversetzte Auffrischen nach einer Eingabe griff auf die Listen
     eines schon geschlossenen Fensters zu. Das konnte auch in der Praxis
     passieren: tippen und sofort OK. Jetzt wird geprüft, ob das Fenster
     geschlossen ist.
  3. Die Listen nach jeder Eingabe mit `clear()` neu aufzubauen, stürzte
     gelegentlich ab. Jetzt werden bei Eingaben nur Texte und Symbole der
     vorhandenen Zeilen erneuert. Neu gebaut wird nur, wenn Zeilen dazukommen
     oder wegfallen.
- **Testwerkzeug:**
  - `szenario_lauf.py` schreibt bei einem Segfault den Python-Stack nach
    `absturz.txt` (faulthandler).
  - `oberflaeche_testen.sh` hielt ohne Argument das zweite Szenario für den
    Ausgabeordner. Der Ordner kommt jetzt nur noch aus `$AUSGABE`.

### TEST
- Von der KI ausgeführt:
  - `tests_ausfuehren.sh`: alle vier Prüfungen `ok`.
  - `oberflaeche_testen.sh`: beide Szenarien, **fünfmal hintereinander**
    `ok`. Das war nötig, weil der Absturz nur ab und zu auftrat.
  - Screenshots angesehen: leer, X1 gewählt, Verteilen, vollständig mit P3
    gewählt, Hinweis angeklickt.
- **Nicht getestet:** Bedienung in Manuels FreeCAD. Die Aufgabenleiste liegt
  im Test über der 3D-Ansicht und nicht links in der Kombiansicht. Das ist
  eine Eigenheit des leeren Testprofils.

### NEXT
- Hervorheben und kurzes Bewegen in der 3D-Ansicht, danach die Hilfetexte.

## P-2026-09-25-16 revolver-plaetze-verteilhilfe

### EINGELESEN
- Spezifikation W-001, Abschnitt 7a (P-2026-09-25-15).
- `App.GeoFeature.getGlobalPlacementOf.__doc__` (Nachfolger der veralteten
  `getGlobalPlacement`).

### DATEIEN
- `camaddon/maschine.py`
- `tests/beispielmaschinen.py` (Revolver drehbar), `tests/test_kette.py`,
  `tests/test_maschine.py`
- `translations/de.json`, `translations/en.json`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
An der Beispiel-Drehmaschine legt `verteile_plaetze` zum Werkzeugplatz 11
weitere an, gleichmäßig im 30°-Abstand um die Revolverachse und benannt als
P1 … P12. Neu verteilt auf 6 Plätze bleiben genau 6, ohne übrig gebliebene
LCS.

### DONE
- Neue Betriebsart **Revolver** (Kennwert: Schaltzeit je Platz). Sie passt
  nur an Drehgelenke und lässt sich mit Positionieren kombinieren.
- Werkzeugaufnahmen haben eine **Platznummer**. `plaetze()` liefert alle
  Werkzeugaufnahmen im Glied hinter dem Revolvergelenk, nach Nummer
  sortiert.
- Die Prüfung meldet einen Revolver ohne Plätze sowie doppelte oder fehlende
  Platznummern.
- **Verteilhilfe** `verteile_plaetze()`: Sie dreht den ersten Platz um die
  Revolverachse (aus der Kette: Ursprung und Richtung) und legt je Platz ein
  LCS neben dem ersten im selben Bauteil an. Wird erneut verteilt, ersetzt
  sie ihre eigenen früheren LCS, erkennbar am Namen `<erstes>_P…`. Von Hand
  angelegte LCS fasst sie nicht an.
- **Drei Befunde aus dem Test**, alle behoben:
  1. Ein einfacher Link vom Maschinenobjekt auf ein LCS in einem Part ist für
     FreeCAD „out of scope“. `Lcs` ist jetzt `PropertyLinkGlobal`, so macht
     es die Assembly bei `ObjectToGround` auch.
  2. `getGlobalPlacement()` ist seit 26.3 veraltet und hätte eine
     Deprecation-Warnung erzeugt. Jetzt gibt es eine eigene Funktion
     `globale_platzierung()` über `Parents` und `getPlacementOf`, wie
     `UtilsAssembly.getGlobalPlacement`.
  3. Beim Löschen alter LCS verschwinden deren Achsen und Ebenen mit. Die
     Schleife arbeitet deshalb mit Namen statt mit Objekten.
- Die Beispiel-Drehmaschine hat jetzt einen drehbaren Revolver
  (`Revolverachse`). Die Erwartungen in `test_kette.py` sind entsprechend
  angepasst: 5 Glieder, 4 Achsen, Pfad Revolver → Revolverachse, X, Z.

### TEST
- Von der KI ohne Fenster ausgeführt: alle vier Prüfungen `ok`.
- Volle Ausgabe aller Prüfungen durchgesehen. Außer den erwarteten
  „Solve failed“-Meldungen des absichtlich doppelt gelagerten Fünfachsers gibt
  es keine Warnungen, auch kein „out of scope“ und keine Deprecation.
- **Nicht geprüft:** ein Revolver als echte Unter-Baugruppe (Assembly in
  Assembly). Dass die LCS darin gefunden werden, ist in P-2026-09-25-15 nur
  von Hand ausprobiert. Eine Beispielmaschine dafür kommt mit dem Dialog.

### NEXT
- Dialog „Maschine bearbeiten“.

## P-2026-09-25-15 spezifikation-revolver-und-beispiele

### EINGELESEN
- Spezifikation W-001, Abschnitte 4 und 7.
- Ausprobiert: Eine Baugruppe in einer Baugruppe zählt in der äußeren als
  **ein** Bauteil (`getMovablePartsWithin`). Die LCS darin findet
  `Kette.glied_von` trotzdem.

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 4, neu 7a und 7b,
  „Entschieden“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die Spezifikation liest, erfährt, wie ein Revolver mit Plätzen P1 … Pn
als eigene Baugruppe eingebunden wird und wie 4. Achse, Gegenspindel und
Reitstock einzurichten sind.

### DONE
Manuels Idee: den Revolver als eigene Baugruppe mit den Plätzen bauen.
Beantwortet hat er es über eine Auswahl:

- **Schalten als Betriebsart „Revolver“:** gewählt. Dazu hat Manuel angemerkt,
  dass ein Revolver wie eine Spindel auch auf Gradzahlen positionierbar sein
  kann. Deshalb darf ein Drehgelenk jetzt allgemein mehrere Betriebsarten
  haben (Revolver + Positionieren), nicht nur Spindel + Positionieren.
- **Plätze:** einzeln als LCS, dazu eine Verteilhilfe. Die Namen sind P1 … Pn.
  Welches Werkzeug auf einem Platz sitzt, kommt laut Manuel aus CAM und nicht
  aus der Maschine.
- Manuels Frage, ob sich Reitstock, Gegenspindel und 4. Achse damit
  einrichten lassen: ja. Neuer Abschnitt 7b zeigt das als Tabelle. Dabei hat
  sich gezeigt: Ein Gelenk **ohne** Betriebsart steht für eine von Hand
  verstellte Achse, z. B. einen Reitstock ohne NC. Das ist jetzt ausdrücklich
  erlaubt und so benannt.

### TEST
- Keiner (nur Spezifikation).

### NEXT
- Betriebsart „Revolver“ und Platznummern im Maschinenobjekt, danach der
  Dialog.

## P-2026-09-25-14 maschinenobjekt

### EINGELESEN
- Spezifikation W-001, Abschnitte 4, 5 und 7.
- `camaddon/kette.py` (P-2026-09-25-13).

### DATEIEN
- `camaddon/maschine.py` (neu)
- `tests/test_maschine.py` (neu), `tests/beispielmaschinen.py` (Revolver und
  Futter als Part mit LCS)
- `translations/de.json`, `translations/en.json`
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`test_maschine.py` legt an der Beispiel-Drehmaschine eine Maschine mit Z1,
X1, S4 und C4 (zwei Betriebsarten an einem Gelenk) sowie Revolver und Futter
an. Die Prüfung meldet dafür nichts, und die Hauptspindel sitzt im Tisch,
X und Z im Kopf.

### DONE
- **Aufbau:** Eine Gruppe „Maschine“ liegt in der Assembly. Jede Betriebsart
  und jede Aufnahme ist ein eigenes Objekt darin, so stehen sie lesbar im
  Baum. Rückgängig geht von selbst, und ein gelöschtes Gelenk hinterlässt nur
  einen leeren Verweis. Die Assembly löst weiterhin und zählt die Gruppe
  nicht als Bauteil (geprüft).
- **Betriebsart:** Gelenk, Art (Linear, Positionieren, Spindel), NC-Name,
  Kennwerte in den Einheiten aus Spezifikation Abschnitt 4. **0 bedeutet
  unbekannt**, denn keiner dieser Werte kann an einer echten Maschine 0 sein.
  Der Eigenschaften-Editor zeigt nur die Werte, die zur Art gehören, auch
  nach dem Laden.
- **Aufnahme:** LCS, Art (Werkzeug/Werkstück), optional die Spindel, die das
  Werkzeug antreibt.
- **Tisch/Kopf:** Ein Gelenk auf dem Weg einer Werkstückaufnahme zum Bett
  sitzt im Tisch, eines auf dem Weg einer Werkzeugaufnahme im Kopf. Liegt es
  auf beiden Wegen, ist es mehrdeutig und wird gemeldet.
- **Prüfung** `pruefe(maschine)` meldet in ganzen Sätzen:
  - NC-Name fehlt oder ist doppelt (Groß/Klein egal)
  - Gelenk gelöscht oder keine Achse
  - Art passt nicht zum Gelenk
  - Art doppelt
  - Pflichtwert fehlt
  - LCS fehlt oder liegt außerhalb
  - Antrieb ist keine Spindel
  - Werkzeug- oder Werkstückaufnahme fehlt (Hinweis)
- Anzeigetexte für Art und Kennwert kommen aus `art_text()`/`wert_text()`
  mit festen Schlüsseln. Mein erster Entwurf setzte die Schlüssel zusammen
  (`"art." + …`), das verbietet Abschnitt 8. Die Sprachprüfung hat außerdem
  einen Eigenschaftstext gefunden, der unübersetzt übergeben wurde. Beides
  ist behoben.
- Die Werte der Eigenschaft „Art“ sind gespeicherte ASCII-Wörter
  (`Positionieren`). Im Eigenschaften-Editor erscheinen sie so, auch auf
  Englisch. Der Dialog zeigt die Übersetzung. Das ist bewusst so, weil
  gespeicherte Werte nicht von der Sprache abhängen dürfen.

### TEST
- Von der KI ohne Fenster ausgeführt: `tests_ausfuehren.sh` ergibt alle
  vier Prüfungen `ok`. `test_maschine.py` deckt ab:
  - Anlegen, auch doppelt
  - Assembly löst weiter
  - leere Maschine
  - vollständige Drehmaschine ohne Meldung
  - Tisch/Kopf-Zuordnung
  - Sichtbarkeit der Kennwerte
  - drei Fehlerfälle, alle Platzhalter gefüllt
  - gelöschtes Gelenk und Rückgängig
  - Speichern und Laden
- Gegenprobe: Erlaubt man Spindel an Schiebegelenken, fehlt
  `maschine.art_passt_nicht`, und die Prüfung schlägt fehl.

### NEXT
- Dialog „Maschine bearbeiten“ (Stufe 1, Oberfläche).

## P-2026-09-25-13 kette-aus-baugruppe-lesen

### EINGELESEN
- Spezifikation W-001, Abschnitte 3, 6 und 7.
- `Mod/Assembly/UtilsAssembly.py` (`getMovablePartsWithin`, `getJointGroup`,
  `getJcsGlobalPlc`, `findPlacement`) und `JointObject.py` (`Joint`,
  `GroundedJoint`, `RigidGroupJoint`, `setJointConnectors`).

### DATEIEN
- `camaddon/kette.py` (neu)
- `tests/beispielmaschinen.py`, `tests/test_kette.py` (neu)
- `tests/test_sprache.py` (findet jetzt auch `meldung("…")`)
- `translations/de.json`, `translations/en.json` (Meldungen)
- `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 6),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`test_kette.py` liest aus den Beispielmaschinen „Drehmaschine“ und
„Fünfachser“ die richtigen Glieder, Achsen, Richtungen und Grenzen und meldet
lose Körper, nicht unterstützte Gelenke und eine doppelt gelagerte Wiege.

### DONE
- `lies_kette(assembly)` liefert eine `Kette`:
  - **Glieder:** Alle Körper, die über Fixed- oder RigidGroup-Gelenke starr
    verbunden sind, werden zu einem Glied zusammengefasst (Union-Find).
    Alle fixierten Körper zusammen bilden das feste Glied, also das Bett.
  - **Achsen:** Slider- und Revolute-Gelenke, als Baum vom Bett aus
    aufgebaut. Jede Achse kennt ihr Eltern- und Kind-Glied, ihre Richtung
    (Z des Gelenk-Koordinatensystems) und ihre Grenzen aus der
    Min/Max-Begrenzung.
  - `glied_von(objekt)` findet das Glied auch für ein LCS in einem Körper.
    `pfad_zum_festen_glied()` ist die Grundlage für die Tisch/Kopf-Zuordnung
    im nächsten Patch.
- **Meldungen** als ganze Sätze auf Deutsch und Englisch:
  - Gelenk ohne zwei Bauteile
  - nicht unterstützte Gelenkart
  - kein fixiertes Teil
  - loser Körper
  - Gelenk innerhalb eines Glieds
  - geschlossene Schleife
  - Glied, das nicht am Bett hängt
  - doppelte Lagerung
- **Befund, doppelte Lagerung:** Eine Wiege mit je einem Drehgelenk in
  beiden Lagerböcken kann der Löser der Assembly nicht lösen
  („Solve failed“), die Teile springen. Ohne das zweite Gelenk stimmen alle
  Richtungen. Mein erster Entwurf hat das zweite Gelenk geometrisch als
  „zweites Lager derselben Achse“ erkannt. Das funktioniert nicht, weil die
  Lage nach dem Scheitern unbrauchbar ist. Jetzt wird strukturell erkannt:
  Ein zweites Gelenk zwischen denselben Gliedern ergibt eine Warnung, die
  sagt, welches Gelenk zu unterdrücken ist. Die Spezifikation (Abschnitt 6)
  schreibt dazu: eine Achse, ein Gelenk.
- **Fallen im Testaufbau** (nicht im Addon, aber für jeden, der weitere
  Beispielmaschinen baut):
  - `Placement.Base = …` ändert nur eine Kopie.
  - Gelenke brauchen neu berechnete Körper.
  - `setJointConnectors` braucht je Seite zwei Namen, das Element und den
    Bezugspunkt. Die Fläche zweimal genannt bedeutet Flächenmitte.
  - Alle drei stehen als Kommentar in `tests/beispielmaschinen.py`.

### TEST
- Von der KI ohne Fenster ausgeführt: `tests_ausfuehren.sh` ergibt
  `ok test_kette.py`, `ok test_sprache.py` und `ok test_umgebung.py`.
- Gegenprobe: Werden Fixed-Gelenke nicht mehr als starr gewertet, schlägt die
  Prüfung mit „Drehmaschine: 4 Glieder erwartet, 7 gefunden“ fehl.
- Die Oberfläche ist nicht betroffen, deshalb gibt es kein Szenario.

### NEXT
- Maschinenobjekt mit Betriebsarten und Aufnahmen, Tisch/Kopf-Zuordnung,
  Befehl „Maschine anlegen“.

## P-2026-09-25-12 grundgeruest-werkzeugleiste-sprachwahl

### EINGELESEN
- `Mod/AddonManager/package.xml` als Vorlage für `package.xml`.
- `Mod/Fem/fempreferencepages/dlg_settings_netgen.py`: Aufbau einer
  Einstellungsseite in Python.
- `Mod/BIM/nativeifc/ifc_status.py`: Beispiel für einen WorkbenchManipulator.

### DATEIEN
- `package.xml`, `InitGui.py`, `resources/icons/camaddon.svg` (neu)
- `camaddon/gui_start.py`, `camaddon/gui_sprachwahl.py` (neu)
- `translations/de.json`, `translations/en.json` (erste Texte)
- `scripts/oberflaeche_testen.sh`, `tests/gui/_lauf/*`,
  `tests/gui/szenario_erster_start.py` (neu), `.gitignore`
- `README.md` (Installieren), `CLAUDE.md`, `CHATSTART.md`,
  `docs/arbeitsregeln.md` (Abschnitt 5), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach der Installation fragt FreeCAD beim ersten Start auf Englisch nach der
Sprache, der Dialog beschriftet sich beim Wählen von Deutsch sofort um, und
danach zeigen Assembly und CAM die Werkzeugleiste „CAM-Addon“ mit dem Knopf
„Über das CAM-Addon“.

### DONE
- **T-001 Grundgerüst:**
  - Das Addon ist in `package.xml` als `workbench` deklariert, damit
    FreeCAD `InitGui.py` lädt. So macht es auch der Addon-Manager von FreeCAD.
    Einen eigenen Arbeitsbereich hat das Addon nicht.
  - Die Werkzeugleiste hängt an **Assembly** und **CAM**, denn dort wird
    die Maschine gebaut und benutzt.
- **Gefundene Falle:** Mein erster Weg war ein `WorkbenchManipulator`
  (`modifyToolBars`). Der hängt nur an vorhandene Leisten an und legt keine
  neue an. Das Szenario hat das aufgedeckt. Jetzt geht es über
  `appendToolbar` des Arbeitsbereichs, sobald er aktiv wird, einmal je
  Arbeitsbereich, und danach `reloadActive()`.
- **T-003, Rest:**
  - Beim ersten Start erscheint die Sprachwahl mit Englisch vorbelegt. Beim
    Blättern durch die Liste beschriftet sie sich sofort in der markierten
    Sprache um, damit auch jemand ohne Englisch sieht, was er wählt.
  - Schließen ohne Wahl zählt als Wahl der Vorauswahl, damit die Frage nicht
    bei jedem Start wiederkommt.
  - Die Einstellungsseite heißt „CAM-Addon → Allgemein“ und bietet die
    Sprache an. Sie sagt dazu, dass die neue Sprache erst nach einem Neustart
    vollständig gilt, weil Befehlstexte beim Laden gelesen werden.
- **Oberflächentests:** `scripts/oberflaeche_testen.sh` startet FreeCAD mit
  Oberfläche unter Xvfb, mit leerem Benutzerprofil (`FREECAD_USER_HOME`) und
  dem Addon als Verknüpfung im Mod-Ordner. Es spielt ein Szenario durch und
  legt Screenshots und `ergebnis.txt` ab. Das Szenario wartet mit `yield`, so
  blockieren modale Dialoge es nicht. Weil FreeCAD `InitGui.py` in einem
  eigenen Namensraum ausführt, in dem sich Funktionen nicht gegenseitig sehen,
  steht die Logik immer im Paket und nie in `InitGui.py`.
- `package.xml` nennt „Manuel Hofer“ als Verantwortlichen, **ohne
  E-Mail-Adresse**. Die trägt Manuel selbst ein, falls er eine angeben will.
- **Neue Regel** in Abschnitt 5: Jede Oberfläche bekommt ein Szenario, und
  die Screenshots gehen an Manuel. `CLAUDE.md` sagt jetzt, dass die KI die
  Oberfläche als Screenshot sieht, die Verständlichkeit aber Manuel prüft.
- Arbeitsname „CAM-Addon“ / „CAM Addon“. Ein richtiger Name ist nicht
  festgelegt.

### TEST
- Von der KI ausgeführt: `tests_ausfuehren.sh` ergibt `ok test_sprache.py`
  und `ok test_umgebung.py`. `oberflaeche_testen.sh` ergibt
  `ok szenario_erster_start`, mit fünf Screenshots (Sprachwahl englisch und
  deutsch, Leiste in Assembly und CAM, Einstellungsseite), alle angesehen.
- **Noch nicht getestet:** Installation und Bedienung in Manuels eigenem
  FreeCAD.

### NEXT
- W-001, Stufe 1: Maschinenobjekt und das Auslesen von Gelenken und Gliedern.

## P-2026-09-25-11 sprachsystem-kern

### EINGELESEN
- `docs/arbeitsregeln.md` Abschnitt 8 (Sprache).

### DATEIEN
- `camaddon/__init__.py`, `camaddon/sprache.py` (neu)
- `translations/de.json`, `translations/en.json`, `translations/README.md` (neu)
- `tests/test_sprache.py` (neu), `.gitignore` (neu)
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`scripts/tests_ausfuehren.sh` meldet `ok test_sprache.py`, und eine
absichtlich eingefügte Leiche in `de.json` lässt die Prüfung scheitern.

### DONE
- `tr(schluessel, **werte)` liefert den Text in der gewählten Sprache. Fehlt
  er dort, kommt Englisch, dann Deutsch und zuletzt der nackte Schlüssel mit
  einer Warnung im Report-Fenster. Die Sprache liegt im Parameter-System unter
  `Mod/CamAddon/Sprache`. Leer heißt „noch nie gewählt“, das braucht die
  Sprachwahl beim ersten Start.
- Eine Sprachdatei ist flach aufgebaut, Schlüssel → Text. `_sprache` enthält
  den Namen der Sprache in der Sprache selbst, so erscheint sie in der
  Auswahl.
- Eine kaputte oder falsch übersetzte Datei (JSON-Fehler, falscher
  Platzhalter) legt das Addon nicht lahm. Es gibt eine Meldung und einen
  Rückfall.
- `translations/README.md` ist die Anleitung für Übersetzer, auf Deutsch
  und Englisch.
- Die Prüfung `test_sprache.py` stellt sicher: de und en haben dieselben
  Schlüssel, andere Sprachen haben keine fremden, die Platzhalter sind gleich,
  jeder `tr("…")` im Code steht in `de.json`, und es gibt keine unbenutzten
  Schlüssel. Deshalb stehen Schlüssel im Code immer als fester Text und werden
  nie zusammengesetzt.
- Außerdem geprüft: Sich Assembly-Gelenke ohne Fenster anlegen und lösen,
  und die FreeCAD-Oberfläche läuft unter Xvfb. Ich kann also Screenshots
  von Dialogen machen. Beides wird in den nächsten Patches genutzt.

### TEST
- Von der KI ohne Fenster ausgeführt: `tests_ausfuehren.sh` ergibt
  `ok test_sprache.py` und `ok test_umgebung.py`.
- Gegenprobe: Ein Schlüssel `test.leiche` nur in `de.json` ergibt `FEHLER` mit
  „nur in de.json“ und „nirgends benutzt“. Danach habe ich ihn wieder entfernt.

### NEXT
- Grundgerüst (T-001) mit Sprachwahl beim ersten Start und Einstellungsseite.

## P-2026-09-25-10 spezifikation-bedienung

### EINGELESEN
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/arbeitsregeln.md`
  Abschnitt 8 (aus P-2026-09-25-09).

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 11 neu,
  „Entschieden“ ergänzt)
- `docs/STATUS_SNAPSHOT.md` (nächster Schritt), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation hat keine offenen Fragen mehr, und Abschnitt 11 beschreibt,
wie der Dialog zeigt, welches Teil der Maschine gemeint ist.

### DONE
- Die offene Frage nach „weiteren Betriebsarten“ ist gestrichen. Ich hatte sie
  unverständlich gestellt, und für Manuel gibt es dort nichts zu
  entscheiden. Sie steht jetzt unter „Entschieden“: vorerst drei, erweiterbar.
- Neuer Abschnitt 11 „Bedienung“ wendet die neue Regel auf diesen Dialog an:
  Beim Überfahren eines Gelenks wird das Teil in der 3D-Ansicht hervorgehoben
  und kurz bewegt. Nicht erlaubte Betriebsarten werden gar nicht erst
  angeboten. Es gibt Hilfe je Bereich und Warnungen in ganzen Sätzen.
- Im Snapshot stand noch „offene Fragen (Abschnitt 9)“. Das war nach dem
  Umnummerieren in P-2026-09-25-08 falsch und ist jetzt korrigiert.

### TEST
- `grep` nach „Offene Fragen“ und nach Abschnittsverweisen in Spezifikation
  und Snapshot.

### NEXT
- Freigabe der Spezifikation durch Manuel.

## P-2026-09-25-09 regel-bedienbarkeit-und-sprache

### EINGELESEN
- `CHATSTART.md` (Festlegungen), `docs/arbeitsregeln.md` Abschnitt 7.

### DATEIEN
- `CHATSTART.md` (vierte Festlegung), `docs/arbeitsregeln.md` (neuer
  Abschnitt 8, Stilregel „Deutsch“ angepasst, folgende Abschnitte umnummeriert)
- `docs/STATUS_SNAPSHOT.md` (T-003), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer `CHATSTART.md` liest, erfährt als erste Festlegung, dass Bedienbarkeit
vor allem geht. Abschnitt 8 der Arbeitsregeln sagt, wie eine neue Sprache
hinzukommt.

### DONE
Manuel: „Das Allerwichtigste ist Bedienbarkeit und Benutzerfreundlichkeit. Es
dürfen bei dem, was auf dem Bildschirm zu sehen ist, keine Fragen aufkommen.“
Dazu selbsterklärend, kleine Animationen, ausführlicher Text hinter dem
Hilfe-Feld, Deutsch und Englisch.

Zur Sprache hatte ich gefragt, ob die Oberflächentexte im Code auf Englisch
(wie bei FreeCAD) oder auf Deutsch stehen sollen. Manuels Antwort ging darüber
hinaus:
- **Deutsch ist die Hauptsprache** für alles, was wir machen.
- **Bei der Erstinstallation gilt Englisch.** Die Sprache wird direkt nach der
  Installation ausgewählt.
- **Weitere Sprachen** soll jemand anderes übersetzen können, über eine
  einfache Datei (JSON oder was üblich ist).

Umsetzung als Regel:
- Die Texte stehen nicht im Code, sondern als Schlüssel in `translations/<sprache>.json`,
  mit `de.json` als führender Datei.
- Eine neue Sprache heißt: `en.json` kopieren und übersetzen.
- Fehlt ein Text in einer Sprache, wird er auf Englisch angezeigt.
- Das Addon fragt beim ersten Start einmal nach der Sprache. Die
  Installation selbst läuft über den Addon-Manager von FreeCAD und bietet
  keinen eigenen Schritt, deshalb ist der erste Start der früheste Zeitpunkt.

Bewusst **nicht** das FreeCAD-übliche Qt-Format (`.ts`/`.qm`): Es braucht
Qt Linguist und einen Übersetzungsschritt, und Manuel wollte ausdrücklich eine
einfache Datei. Nachteil: Die Übersetzungsplattform von FreeCAD (Crowdin)
greift nicht. Wird das später gewünscht, lässt sich JSON in `.ts` umwandeln.

Animationen enthalten keinen Text, damit keine Animation je Sprache
gebraucht wird.

### TEST
- Abschnittsnummern und Verweise nach dem Umnummerieren gegengeprüft.

### NEXT
- Offene Frage in der Spezifikation streichen; Freigabe durch Manuel.

## P-2026-09-25-08 spezifikation-maschinenobjekt-glieder

### EINGELESEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (Entwurf aus P-2026-09-25-07).

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die Spezifikation liest, erfährt, dass die Maschinendaten in einem eigenen
Maschinenobjekt liegen und wie eine Schwenkbrücke aus mehreren Körpern als ein
Glied mitschwenkt.

### DONE
Drei Vorgaben von Manuel:

- **Allgemein, nicht nur die CLX 550.** Die Spezifikation sagt jetzt vorn,
  dass sie für beliebige Maschinen gilt. Die CLX erscheint nur noch als ein
  Beispiel („Drehmaschine“), daneben steht eine Fräse mit Schwenkbrücke.
- **Eigenes Objekt** statt Eigenschaften an den Gelenken (meine Empfehlung war
  A, Manuel hat B gewählt). Neuer Abschnitt 5: Das Objekt verweist auf Gelenke
  und LCS. Gebrochene Verweise gehen nicht verloren, sondern werden gemeldet
  und können neu zugeordnet werden. Das war das Risiko, das ich bei B genannt
  hatte.
- **Schwenkbrücke:** Schenkel und Boden der Wiege sind eigene Körper und
  müssen mitschwenken. Neuer Abschnitt 6 „Glieder“: Das Addon fasst alle über
  Fixed-Gelenke (oder eine Unterbaugruppe) starr verbundenen Körper zu einem
  Glied zusammen. Das Mitschwenken selbst erledigt die Assembly. Für Stufe 4
  ist vorgemerkt, dass Körper eines Glieds und direkt benachbarte Glieder
  nicht gegeneinander geprüft werden.

Die offene Frage nach weiteren Betriebsarten bleibt stehen, ist aber
entschärft: Die Liste lässt sich erweitern.

### TEST
- Abschnittsnummern und Querverweise nach dem Umnummerieren gegengeprüft.

### NEXT
- Freigabe der Spezifikation durch Manuel; dann Stufe 1 plus T-001.

## P-2026-09-25-07 spezifikation-maschine-aus-baugruppe

### EINGELESEN
- `Mod/CAM/Machine/models/machine.py` (Wochen-Build 26.3.0 dev): `LinearAxis`,
  `RotaryAxis`, `ToolheadType`, `MachineFactory` (Ablage als `.fcm`,
  `register_addon_machine_dir`).
- `Mod/Assembly/JointObject.py`: Gelenkarten und Begrenzungen.

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (neu)
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die Spezifikation liest, findet dort für jede Betriebsart (Linear,
Positionieren, Spindel) die Werte mit Einheit und eine Anleitung, wie man die
Beschleunigung ermittelt.

### DONE
Entwurf nach Manuels Vorgaben aus dem Gespräch:

- **Namen immer von Hand.** Mein erster Vorschlag, Namen aus der Baugruppe
  abzuleiten, war falsch. Manuels Gegenbeispiel: An der CLX 550 heißt die
  Hauptspindel S4, wenn sie dreht, und C4, wenn sie positioniert.
- Daraus entstand der Begriff **Betriebsart**: Ein Gelenk hat eine oder
  mehrere Betriebsarten, jede mit eigenem Namen und eigenen Werten.
- **Beschleunigung und Ruck** sind aufgenommen, dazu eine Anleitung, wie man
  sie ermittelt (Maschinendaten Siemens/Fanuc/LinuxCNC, Datenblatt, Messen
  mit a ≈ 4·s/t²).
- Verfahrgrenzen werden **nicht doppelt** erfasst, sie kommen aus der
  Min/Max-Begrenzung der Assembly-Gelenke.
- Der Export geht in die vorhandene CAM-Maschinendefinition (`.fcm`) über
  den offiziellen Addon-Weg. Werte, die FreeCAD dort nicht kennt
  (Beschleunigung, Ruck, Vorschub, Mehrfach-Betriebsarten), bleiben im
  Dokument.
- Aus zwei Stufen wurden vier: beschreiben, exportieren, von Hand
  verfahren, Kollision. Stufe 4 bekommt eine eigene Spezifikation.

Zwei offene Fragen stehen in Abschnitt 9: der Speicherort (Empfehlung: als
Eigenschaften direkt an Gelenken und LCS) und ob drei Betriebsarten reichen.

**Nicht geprüft:** die Maschinendaten-Nummern für Siemens und Fanuc stammen
aus meinem Wissen, nicht aus einem Handbuch. Manuel kann sie an der CLX 550
gegenprüfen.

### TEST
- Links in `CHATSTART.md` und im Snapshot auf die neue Datei geprüft.

### NEXT
- Manuel beantwortet die offenen Fragen; dann Stufe 1 plus T-001.

## P-2026-09-25-06 wunsch-maschine-aus-baugruppe

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md`, Wunschliste.
- FreeCAD-Quelltext (Wochen-Build 26.3.0 dev), um zu prüfen, ob es das schon
  gibt: `Mod/CAM/Machine/models/machine.py` und `Mod/Assembly/JointObject.py`.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Wunschliste im Snapshot enthält W-001 „Maschine aus Baugruppe“.

### DONE
Manuels Vorstellung: Die Maschine wird grob in 3D nachgebaut und in einer
Assembly zusammengesetzt. In die Bauteile gelegte Achsen bestimmen Richtung,
Art (linear/drehend) und Namen, auch für mehrere Werkzeugachsen. Das soll das
erste Addon werden.

Befund aus dem FreeCAD-Check, damit die Spezifikation nicht bei null anfängt:

- **Assembly** hat die passenden Gelenke `Slider` und `Revolute` mit
  Min-/Max-Begrenzung und eine Simulation, die Gelenke antreibt.
- **CAM** hat eine neue Maschinendefinition (`Mod/CAM/Machine/`) mit
  kinematischer Kette (`AxisRole` Tisch/Kopf, `parent`, `joint_origin`),
  Grenzen, `max_velocity` (linear in mm/min, Standard 10000; rotativ in °/min,
  Standard 36000 = 100 U/min), `WrapStrategy` für endlose Rundachsen und
  `tcp_supported`. **Keine Geometrie**, keine Beschleunigung.
- Kollisionsprüfung gibt es nur für Eilgang-Verbindungen gegen Körper
  (`Path/Base/Generator/linking.py`), nicht für Maschine oder Halter.

Daraus ergibt sich die Richtung: Das Addon liest die Assembly aus und füllt
die vorhandene CAM-Maschinendefinition. Es baut kein eigenes Format.

### TEST
- Keiner nötig (nur Snapshot).

### NEXT
- Spezifikation W-001: Achsparameter je Achsart klären.

## P-2026-09-25-05 zielversion-wochen-build

### EINGELESEN
- Alle Stellen mit „neueste“ in der Doku (`grep -rn "neueste"`).

### DATEIEN
- `CHATSTART.md` (Festlegung 1), `README.md`
- `docs/arbeitsregeln.md` (Abschnitte 0, 7 und 8)
- `docs/STATUS_SNAPSHOT.md` (T-002 entfernt), `docs/archiv/DEV_PROMPT_HISTORY.md`
  (Kopfzeile `zielsystem`)

### AKZEPTANZKRITERIUM
Wer `CHATSTART.md` liest, erfährt, dass das Addon für den aktuellen
Wochen-Build von FreeCAD gebaut wird und nicht für die letzte stabile Version.

### DONE
T-002 ist entschieden. Manuel: **Wochen-Build**. Damit gilt dieselbe Version
wie in der Testumgebung, die conda-forge ohnehin liefert.

Folge für Abschnitt 8 (Versionscheck): Ein Wochen-Build erscheint jede Woche.
Ein Versionscheck-Patch für jede Woche wäre Leerlauf. Deshalb fällt er an,
sobald Manuel seinen Build aktualisiert oder die Testumgebung einen neueren
zieht. Die Regel selbst bleibt bestehen, nur ihr Auslöser ist präzisiert.

### TEST
- `grep -rn "neueste"` findet nur noch Verlaufseinträge, die Historie sind.

### NEXT
- W-001 in die Wunschliste.

## P-2026-09-25-04 testumgebung-ohne-fenster

### EINGELESEN
- `docs/arbeitsregeln.md`, Abschnitt 5 (die neue Regel aus P-2026-09-25-02).

### DATEIEN
- `scripts/testumgebung_einrichten.sh`, `scripts/tests_ausfuehren.sh`,
  `tests/test_umgebung.py` (alle neu)
- `CHATSTART.md` (Lesekarte), `docs/arbeitsregeln.md` (Abschnitt 5)
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In einer frischen Cloud-Sitzung laufen `scripts/testumgebung_einrichten.sh`
und danach `scripts/tests_ausfuehren.sh`. Die Ausgabe ist
`ok test_umgebung.py` mit Exit-Code 0.

### DONE
- FreeCAD kommt über **micromamba aus conda-forge**. Das ist der einzige Weg,
  den das Netzwerk der Cloud-Umgebung zulässt: GitHub-Releases (AppImage) und
  gnu.org werden vom Proxy abgewiesen, `apt` kennt kein FreeCAD. micromamba
  selbst wird als conda-forge-Paket geholt, weil `micro.mamba.pm` ebenfalls
  gesperrt ist.
- Die Installation belegt rund **3,7 GB** und dauert einige Minuten. Deshalb
  liegt sie außerhalb des Repos unter `~/.cache/freecad-cam-addon/` und kann
  über `FC_UMGEBUNG` umgelenkt werden.
- **Falle, die ich beim Entwurf gefunden habe:** FreeCADCmd liefert bei einer
  Ausnahme im Skript keinen verlässlichen Fehlercode. Deshalb endet jede
  Prüfung mit der Zeile `OK <dateiname>`, und nur diese Zeile zählt als
  bestanden.
- `tests/test_umgebung.py` prüft das Fundament aller späteren Prüfungen:
  FreeCAD startet, `Path.Main.Job` lässt sich importieren, und
  Transaktion plus Rückgängig entfernt ein angelegtes Objekt wieder (Regel
  „Strg+Z muss gehen").
- Die Skripte sind reine Entwicklerwerkzeuge für Linux-Container. Das Addon
  selbst bleibt plattformneutral.

Bewusst **nicht** gemacht: keine CI auf GitHub (bisher nicht beauftragt), kein
SessionStart-Hook, der die 3,7 GB in jeder Sitzung automatisch lädt.

**Offene Frage (T-002):** conda-forge liefert nur den Wochen-Build
26.3.0 dev (2026-09-16). Ob „neueste Version" stabil oder Wochen-Build meint,
entscheidet Manuel.

### TEST
- Von der KI ohne Fenster ausgeführt: `scripts/tests_ausfuehren.sh` ergibt
  `ok test_umgebung.py`, Exit 0.
- Gegenprobe mit einer absichtlich fehlschlagenden Prüfung: `FEHLER`,
  Ausgabe mit der Ausnahme, Exit 1. Die Prüfung ist danach wieder gelöscht.
- `testumgebung_einrichten.sh` auf der vorhandenen Umgebung ausgeführt
  (Zweig „update"). Den Zweig „create" habe ich mit demselben Befehl von Hand
  ausgeführt, aber nicht über das Skript.
- `sh -n` über beide Skripte, `py_compile` über die Prüfung.

### NEXT
- T-002 entscheiden; Wunschliste füllen.

## P-2026-09-25-03 lizenz-lgpl

### EINGELESEN
- `README.md`.

### DATEIEN
- `LICENSE` (neu), `README.md` (Abschnitt Lizenz)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
GitHub zeigt beim Repo die Lizenz LGPL-2.1 an, und das README nennt sie.

### DONE
Manuel hat LGPL-2.1 wie FreeCAD gewählt (Alternativen waren „keine Lizenz“ und
MIT). Angegeben ist „or-later“, wie bei FreeCAD. Das ist auch die Voraussetzung,
falls das Addon später in den Addon-Manager soll. Der Lizenztext stammt aus
`/usr/share/common-licenses/LGPL-2.1` (Debian), weil gnu.org aus der
Cloud-Umgebung nicht erreichbar war. Der Text ist derselbe.

### TEST
- Kopf von `LICENSE` gelesen: „GNU LESSER GENERAL PUBLIC LICENSE, Version 2.1“.
- Die Anzeige auf GitHub ist erst nach dem Push prüfbar.

### NEXT
- Testumgebung.

## P-2026-09-25-02 regeln-addon-zusatz

### EINGELESEN
- `docs/arbeitsregeln.md`, Abschnitte 5 und 7.

### DATEIEN
- `docs/arbeitsregeln.md` (Abschnitt 5 und 7 ergänzt, neuer Abschnitt 8,
  bisheriger 8 wird 9)
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer `docs/arbeitsregeln.md` liest, findet dort die vier Zusatzregeln
Rückgängig, Einstellungen, Versionscheck und automatische Tests.

### DONE
Manuel hat aus einer Auswahl alle vier vorgeschlagenen Zusatzregeln gewählt:

- **Strg+Z muss gehen:** jede Aktion eine Transaktion.
- **Einstellungen in FreeCAD:** Parameter-System statt eigener Dateien.
- **Neue FreeCAD-Version prüfen:** eigener Patch je Version; die zuletzt
  geprüfte Version steht im Snapshot.
- **Automatische Tests:** Prüfungen unter `tests/`, die ohne Fenster mit
  `FreeCADCmd` laufen. Die Testumgebung selbst ist ein eigener Patch.

### TEST
- Abschnittsnummern und Verweise gegengeprüft.

### NEXT
- Lizenz, dann Testumgebung.

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
