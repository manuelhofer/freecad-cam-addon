# Arbeitsregeln

Wie in diesem Projekt gearbeitet wird – unabhängig davon, welches Werkzeug oder
Modell gerade eingesetzt wird. Diese Datei gilt für **jede** Änderung.

---

## 0. Verhandelbar ist alles davon

Jede Regel hier ist besprechbar – sie steht nicht da, weil sie unantastbar
wäre, sondern weil sie sich bewährt hat. Steht eine im Weg oder ist sie falsch:
**sagen**, mit Begründung. Was nicht geht, ist Stillschweigen in beide
Richtungen: eine Regel kommentarlos umgehen, oder ihr sehenden Auges in ein
schlechtes Ergebnis folgen. Geändert wird sie als eigener Patch mit Begründung
im Verlauf.

Das gilt für den ganzen Arbeitsweg, nicht nur für diese Liste: Was am Ablauf
stört, wird **angesprochen**, nicht ausgehalten.

**Entscheidungen kommen als Auswahl.** Was zu entscheiden ist – ein Umfang, ein
Standardwert, der Aufbau eines Dialogs, die Reihenfolge zweier Wege –, wird als
Frage mit **Optionen** gestellt, je mit einem Satz dazu, was die Option bedeutet
und was sie kostet, und mit einer Empfehlung. Nicht als Fließtext in einem Plan.
Die Freigabe eines Vorhabens ist **keine** Zustimmung zu einer Vorgabe, die
darin mitgelaufen ist.

**Fragen nur, wenn die Antwort etwas ändert.** Was durch die drei Festlegungen
in `CHATSTART.md` schon entschieden ist (stabile Version und Wochen-Build, jedes
Betriebssystem, keine bestimmte Maschine), wird nicht noch einmal gefragt.

## 1. Wann überhaupt gearbeitet wird

Ob gerade gearbeitet wird, entscheidet der **Projektstatus** in
[STATUS_SNAPSHOT.md](STATUS_SNAPSHOT.md).

Ein Wunsch wird **zuerst beschrieben**, bevor er gebaut wird: was heute stört,
wie es sein soll, woran man erkennt, dass es fertig ist. Bei einer Änderung an
der Oberfläche gehört eine Skizze dazu – ein Screenshot mit Markierungen oder
ein ASCII-Entwurf des Dialogs reicht.

## 2. Vor der Änderung: Pre-Flight-Gate (Pflicht)

1. **Lesen:** die drei Immer-Zeilen und die passende Themenzeile aus der
   Lesekarte in `CHATSTART.md` – nicht mehr.
2. **Duplicate-Check:** Prüfen, ob das Ziel schon erledigt ist – im Verlauf
   **und** im Git-Verlauf (`git log --oneline`, `git log -S"<begriff>"`).
   Wenn ja: **nicht erneut bauen**, sondern nachfragen.
3. **FreeCAD-Check:** Prüfen, ob FreeCAD das schon kann – eine Einstellung, ein
   vorhandener Befehl, eine Vorlage. Dann ist die Antwort ein Hinweis, kein Code.
4. **Task-Disziplin:** Umgesetzt wird nur, was im Snapshot steht oder
   ausdrücklich beauftragt wurde.

## 3. Zuschnitt einer Änderung

- **1 Patch = 1 Thema = 1 sichtbarer Effekt.** Keine Misch-Patches.
- Jeder Patch braucht **ein Akzeptanzkriterium in genau einem Satz** – ein
  konkreter Klickweg mit Erwartung, den Manuel in FreeCAD nachmachen kann:
  „Job öffnen, auf *Tasche* klicken → der Dialog zeigt nur Werkzeug, Tiefe und
  Zustellung."
- **Keine Refactors nebenbei.** Fällt etwas auf, wird es notiert und als
  eigener Patch abgearbeitet, möglichst gleich danach.
- Kein hartes Dateilimit – aber viele Dateien in einem Patch sind ein
  Warnsignal für zwei vermischte Themen.

## 4. Ergebnis ist ein Commit

- Geändert wird **direkt in der Arbeitskopie**; das Repository ist die Quelle
  der Wahrheit. Keine ZIP-Pakete, keine Datei-Dumps im Chat.
- **Patch-ID** `P-YYYY-MM-DD-XX` (Datum Europe/Berlin, `XX` fortlaufend am Tag)
  im **Commit-Betreff**, gefolgt von einer kurzen Beschreibung in `kebab-case`:

  ```
  P-2026-09-25-01 projektregeln
  ```

- Zu jeder Patch-ID gehört ein Eintrag in `docs/archiv/DEV_PROMPT_HISTORY.md`
  – im **selben Commit**.
- **Gepusht wird nur auf ausdrückliche Ansage.**
- **Was auf `main` liegt, kommt als Update an.** Der Addon-Manager von
  FreeCAD bietet jeden neuen Stand auf `main` als Update an – gepusht wird
  deshalb nur, was alle Prüfungen bestanden hat. Ändert ein Push etwas
  Sichtbares, zählt er die Version in `package.xml` hoch (`<version>`, dazu
  `<date>`): neue Funktion → mittlere Stelle (0.3.0), Korrektur → letzte
  Stelle (0.2.1). Die Version steht **nur** dort; das Addon liest sie von
  da.
- Erklärungen im Chat: kurz, sachlich, deutsch – was geändert wurde, warum,
  was bewusst **nicht** gemacht wurde, und **wie Manuel es testet**.

## 5. Nach der Änderung: Pflichtprüfung

- **Einheitlich und ohne Befund:** `black .` formatiert, `ruff check .` meldet
  nichts (Einstellungen in `pyproject.toml`, wie bei FreeCAD: Zeilenlänge
  100). Ein `# noqa` braucht eine Begründung in derselben Zeile.
  `scripts/alle_tests.sh` prüft das als Erstes.
- **Nur prüfen, was nötig ist.** Jeder Lauf kostet Rechenzeit und Strom
  (Manuel, P-2026-09-25-42). Deshalb:
  - Während der Arbeit läuft nur die Prüfung zum geänderten Teil, in einer
    FreeCAD-Version.
  - Vor einem Push läuft einmal alles, **in beiden FreeCAD-Versionen**:
    `scripts/alle_tests.sh`. Das gilt für alle Patches seit dem letzten Push
    zusammen, nicht für jeden einzeln. In einer frischen Cloud-Sitzung vorher
    einmal `scripts/testumgebung_einrichten.sh`.
  - Solange `scripts/alle_tests.sh` läuft, startet nichts anderes FreeCAD –
    auch kein kurzer Versuch mit `freecadcmd`. FreeCAD sperrt beim Schreiben
    von `user.cfg` eine Datei in `/tmp`, deren Name nur die Sekunde trägt
    (`user.<Unix-Zeit>.cfg.lock`). Starten zwei FreeCAD in derselben Sekunde,
    schreibt eines seine Einstellungen nicht („Failed to access file for
    writing“), und etwa `szenario_erster_start` scheitert – mit dem Code hat
    das nichts zu tun, der Lauf zählt trotzdem nicht (P-2026-09-27-33).
  - Reine Doku-Änderungen brauchen keinen Testlauf.
- **Neue Prüfungen** gibt es für behobene Fehler, damit sie nicht
  wiederkommen, und für neue Funktionen. Reines Aufräumen braucht keine
  neuen, das decken die vorhandenen ab. Was sich ohne Oberfläche prüfen
  lässt, prüft eine Datei unter `tests/` mit `FreeCADCmd`. Bei einem
  behobenen Fehler zeigt eine Gegenprobe einmal, dass die Prüfung mit dem
  alten Code fehlschlägt.
- Gibt es eine Funktion in einer Version nicht, meldet die Prüfung
  `UEBERSPRUNGEN <datei>: Grund` statt `OK` – nur dafür, nie um einen Fehler
  zu verstecken. Das Szenario prüft in dieser Version stattdessen die
  Erklärung, die der Benutzer sieht.
- Eine **neue Oberfläche** bekommt ein **Szenario** unter `tests/gui/`, das
  sie in einer unsichtbaren FreeCAD-Oberfläche durchklickt und prüft
  (`scripts/oberflaeche_testen.sh`). Ändert sich eine Oberfläche sichtbar,
  gehört ein Screenshot in die Rückmeldung an Manuel.
- **Im Chat** genügt „Tests grün“; Einzelheiten nur, wenn etwas auffällt.
- Die Oberfläche prüft **Manuel** in FreeCAD. Der Patch nennt ihm den Klickweg
  aus dem Akzeptanzkriterium. Gilt er erst nach seiner Rückmeldung als getestet,
  steht das so im Verlauf.
- Auf **Meldungsfreiheit** achten: keine Fehler oder Warnungen im
  Report-Fenster bzw. der Python-Konsole von FreeCAD beim Laden des Addons.

## 6. Zwei Dateien, zwei Aufgaben

Bei **jedem** Patch werden beide gepflegt, im selben Commit:

**`docs/STATUS_SNAPSHOT.md` – der Stand.** Die einzige Stelle für
Projektstatus, nächsten Schritt, Wunschliste (W-IDs), offene Bugs (B-IDs) und
Tasks (T-IDs). Erledigtes wird hier **entfernt**, nicht abgehakt.

**`docs/archiv/DEV_PROMPT_HISTORY.md` – der Verlauf.** Chronologisch
absteigend, ein Eintrag je Patch, **nie** gelöscht: Patch-ID, EINGELESEN,
DATEIEN, AKZEPTANZKRITERIUM, DONE, TEST, NEXT.

Was in den Eintrag gehört und oft vergessen wird:

- **Gefundene Fehler im eigenen Entwurf.**
- **Was bewusst nicht erreicht wurde**, mit Begründung.
- **Was tatsächlich getestet wurde** – und von wem (KI ohne GUI oder Manuel in
  FreeCAD) –, nicht was getestet werden könnte.

## 7. Technik und Stil

**Zielsystem:** die aktuelle **stabile Version** von FreeCAD (derzeit 1.1.3)
**und** der aktuelle **Wochen-Build**, auf jedem Betriebssystem. Fehlt in der
stabilen Version etwas, fragt der Code danach (z. B. `export.verfuegbar()`)
statt nach Versionsnummern – so wird eine Funktion von selbst frei, sobald
die stabile Version sie bekommt. Die mitgelieferten Python- und Qt-Versionen von FreeCAD sind
die Baseline – keine zusätzlichen Pakete, die man mit `pip` nachinstallieren
müsste.

**Plattformneutral:**

- Pfade über `os.path` / `pathlib` und die FreeCAD-Funktionen
  (`FreeCAD.getUserAppDataDir()` u. ä.), nie fest verdrahtet.
- Keine Shell-Aufrufe, keine systemabhängigen Bibliotheken. **Einzige
  Ausnahme:** Git für die Update-Suche in `camaddon/aktualisierung.py`
  (Manuels Entscheidung, P-2026-09-25-24) – nie mit Rückfrage, immer mit
  Zeitlimit, Ausgabe als UTF-8.
- Qt-Import über `from PySide import QtCore, QtGui` – den Shim, den FreeCAD
  selbst mitbringt –, nicht direkt PySide2/PySide6.

**Maschinenneutral:** Keine Annahmen über eine bestimmte Fräse oder einen
Postprozessor. Wo ein Wert maschinenabhängig ist, ist er eine Einstellung mit
vernünftigem Standard.

**Nicht in FreeCAD hineinpfuschen:** Das Addon benutzt die öffentliche
Python-API von FreeCAD und der CAM-Workbench. Kein Überschreiben von
FreeCAD-Dateien, kein Monkey-Patching. Geht etwas nur über interne Funktionen,
wird das **angesprochen** und im Code begründet.

**Strg+Z muss gehen:** Jede Aktion des Addons, die das Dokument ändert, läuft
in **einer** Transaktion (`doc.openTransaction(...)` / `commitTransaction()`,
im Fehlerfall `abortTransaction()`). Ein Klick im Addon = ein Schritt
Rückgängig, nie ein halb geänderter Job.

**Einstellungen in FreeCAD:** Standardwerte und Vorlagen des Addons liegen im
Parameter-System von FreeCAD (`FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/<Addon>")`),
nicht in eigenen Dateien. So überleben sie Updates und brauchen keinen Pfad.
Nur was dafür zu groß ist (z. B. ganze Vorlagensätze), kommt als Datei unter
`FreeCAD.getUserAppDataDir()`.

**Installierbar wie jedes Addon:** Aufbau so, dass der Ordner in `Mod/` bzw.
über den Addon-Manager geladen wird (`package.xml`, `InitGui.py`).

**Stil:**

- Klein und lesbar, sinnvolles OOP ohne Vererbungsbäume. Geschrieben für
  einen Menschen, der den Code zum ersten Mal liest: jedes Modul beginnt mit
  einem Docstring, was es tut und wie es in das Ganze passt; jede
  öffentliche Funktion und Klasse hat einen Docstring. Lieber eine kleine
  Hilfsfunktion mit gutem Namen als dieselben drei Zeilen an drei Stellen.
- **Deutsch:** eigene Bezeichner, Kommentare, Dokumentation. Namen aus
  FreeCAD und Qt bleiben, wie sie sind. Texte der Oberfläche stehen **nie** im
  Code, sondern in den Sprachdateien (Abschnitt 8).
- **Umlaute schreiben, nicht umschreiben:** `ä ö ü ß` überall, wo Text für
  Menschen steht – Oberfläche, Kommentare, Dokumentation, Verlauf. Nie
  `ae oe ue ss`. Ausgenommen bleiben Bezeichner, Dateinamen,
  Einstellungsschlüssel und Commit-Betreffe – dort gilt ASCII, auch wenn sie
  zitiert werden. Im Commit: **Betreff ASCII**, **Text darunter mit Umlauten**.
- Kommentare erklären vor allem das **Warum**.
- Fehler landen im Report-Fenster (`FreeCAD.Console.PrintError` /
  `PrintWarning`), nicht still im Nichts.

## 8. Bedienbarkeit und Sprache

**Bedienbarkeit ist das oberste Ziel** – vor Funktionsumfang und vor
Eleganz im Code. Der Maßstab: Wer den Bildschirm sieht, hat keine Frage.

- **Selbsterklärend:** Jedes Feld hat eine Beschriftung in Worten (nicht nur
  ein Kürzel), die Einheit steht daneben, sinnvolle Standardwerte sind
  vorbelegt. Ungültiges wird sofort am Feld gezeigt, mit einem Satz, was
  stattdessen gilt – nicht erst beim Speichern.
- **Zeigen statt beschreiben:** Wo ein Begriff ein Bild braucht (welche
  Achse, welche Richtung, was ein Glied ist), erklärt es eine kleine
  Animation – am besten direkt in der 3D-Ansicht (das betroffene Teil wird
  hervorgehoben und bewegt sich kurz), sonst als kurze Animation im Dialog.
  Animationen enthalten **keinen Text**, damit sie in jeder Sprache passen.
- **Drei Stufen Hilfe:** (1) die Beschriftung selbst, (2) ein Tooltip mit einem
  Satz, (3) ein Hilfe-Knopf (?) je Bereich, der einen ausführlichen Text mit
  Beispielen öffnet. Stufe 3 darf lang sein, Stufe 1 und 2 nicht.
- **Jede Abweichung von FreeCAD-Gewohnheiten** (Knopfreihenfolge, Farben,
  Begriffe) braucht einen Grund im Verlauf.
- Das Akzeptanzkriterium einer Oberfläche enthält immer auch: „Manuel versteht
  den Dialog ohne Erklärung“ – das prüft nur er.

**Sprache:**

- Arbeitssprache (Code, Kommentare, Doku, Verlauf) ist **Deutsch**. Die
  deutsche Sprachdatei ist die **führende**: Neue Texte entstehen zuerst dort.
- Die Oberfläche gibt es mindestens auf **Deutsch und Englisch**; jeder Patch,
  der einen Text anlegt oder ändert, pflegt beide.
- **Neu installiert startet das Addon auf Englisch.** Beim ersten Start fragt
  es einmal nach der Sprache; die Wahl lässt sich in den Einstellungen des
  Addons jederzeit ändern (gespeichert im Parameter-System von FreeCAD).
- **Übersetzungen** liegen als eine JSON-Datei je Sprache in
  `translations/` (`de.json`, `en.json`, …): ein fester Schlüssel je Text, der
  Wert ist der Text. Eine neue Sprache heißt: `en.json` kopieren, umbenennen
  (z. B. `it.json`), Werte übersetzen – das Addon bietet sie dann in der
  Auswahl an. Fehlt ein Text in einer Sprache, erscheint der englische.
- Lange Hilfetexte liegen je Sprache als eigene Datei in `help/<sprache>/`.
- Eine automatische Prüfung stellt sicher, dass `de.json` und `en.json`
  dieselben Schlüssel haben und kein Schlüssel im Code fehlt.

## 9. Neue FreeCAD-Version

Zu jedem Wechsel auf eine neuere Version – eine neue stabile Version
(1.1.4, 1.2 …) oder ein neuerer Wochen-Build – gehört ein **Versionscheck**
als eigener Patch, sobald Manuel aktualisiert oder die Testumgebung eine
neuere zieht: Testumgebung heben (`scripts/testumgebung_einrichten.sh`),
`scripts/alle_tests.sh` laufen lassen, im Report-Fenster auf Meldungen achten,
und Manuel klickt die Akzeptanzkriterien der sichtbaren Funktionen einmal
durch. Bricht etwas, wird es angepasst. Ist eine neue stabile Version da,
fällt die vorige heraus (unterstützt werden immer genau die aktuelle stabile
und der Wochen-Build). Welche Versionen zuletzt geprüft wurden, steht im
Snapshot.

## 10. Am Ende: Kaltstart klein halten

Jeder neue Chat liest `CLAUDE.md`, `CHATSTART.md`, diese Datei und den
Snapshot, **bevor** er irgendetwas tun kann. **So kurz wie möglich, aber nicht
kürzer.** Neue Erklärungen gehören in Dateien, die nur bei Bedarf gelesen
werden (Spezifikationen unter `docs/`); der Snapshot bekommt **einen Satz je
Wunsch, Bug und Task**, die Begründung steht im Verlauf.

Zum Abschluss einer Sitzung: Erledigtes aus dem Snapshot **entfernen**, keine
ableitbaren Zahlen pflegen, Links gegenprüfen.
