---
project: freecad_cam_addon
language: de
timezone: Europe/Berlin
status: planung
stack: Python, PySide (Qt), FreeCAD-API (CAM-Workbench)
zielsystem: aktueller Wochen-Build von FreeCAD, jedes Betriebssystem, keine bestimmte Maschine
patch_naming:
  pattern: "P-YYYY-MM-DD-XX <kurzbeschreibung>"   # im Commit-Betreff
  example: "P-2026-09-25-01 projektregeln"
---

# Verlauf (LOG/ARCHIV)

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
