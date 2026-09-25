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
