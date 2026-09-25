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
in `CHATSTART.md` schon entschieden ist (neueste FreeCAD-Version, jedes
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
- Erklärungen im Chat: kurz, sachlich, deutsch – was geändert wurde, warum,
  was bewusst **nicht** gemacht wurde, und **wie Manuel es testet**.

## 5. Nach der Änderung: Pflichtprüfung

- `python -m py_compile` über **alle** geänderten Python-Dateien.
- Was sich ohne Oberfläche prüfen lässt (Berechnungen, Vorlagen, Einlesen von
  Einstellungen, Anlegen von Jobs und Operationen), bekommt eine
  **wiederholbare** Prüfung unter `tests/`, die mit `FreeCADCmd` ohne Fenster
  läuft. Alle Prüfungen laufen vor jedem Commit durch
  (`scripts/tests_ausfuehren.sh`; in einer frischen Cloud-Sitzung vorher
  einmal `scripts/testumgebung_einrichten.sh`).
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

**Zielsystem:** die jeweils **neueste FreeCAD-Version** auf jedem
Betriebssystem. Die mitgelieferten Python- und Qt-Versionen von FreeCAD sind
die Baseline – keine zusätzlichen Pakete, die man mit `pip` nachinstallieren
müsste.

**Plattformneutral:**

- Pfade über `os.path` / `pathlib` und die FreeCAD-Funktionen
  (`FreeCAD.getUserAppDataDir()` u. ä.), nie fest verdrahtet.
- Keine Shell-Aufrufe, keine systemabhängigen Bibliotheken.
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

- Klein und lesbar, sinnvolles OOP ohne Vererbungsbäume.
- **Deutsch:** Oberfläche, eigene Bezeichner, Kommentare. Namen aus FreeCAD
  und Qt bleiben, wie sie sind.
- **Umlaute schreiben, nicht umschreiben:** `ä ö ü ß` überall, wo Text für
  Menschen steht – Oberfläche, Kommentare, Dokumentation, Verlauf. Nie
  `ae oe ue ss`. Ausgenommen bleiben Bezeichner, Dateinamen,
  Einstellungsschlüssel und Commit-Betreffe – dort gilt ASCII, auch wenn sie
  zitiert werden. Im Commit: **Betreff ASCII**, **Text darunter mit Umlauten**.
- Kommentare erklären vor allem das **Warum**.
- Fehler landen im Report-Fenster (`FreeCAD.Console.PrintError` /
  `PrintWarning`), nicht still im Nichts.

## 8. Neue FreeCAD-Version

Weil immer auf die neueste Version gesetzt wird, gehört zu jeder neuen
FreeCAD-Version ein **Versionscheck** als eigener Patch: Testumgebung auf die
neue Version heben, alle Prüfungen unter `tests/` laufen lassen, im
Report-Fenster auf Meldungen achten, und Manuel klickt die Akzeptanzkriterien
der sichtbaren Funktionen einmal durch. Bricht etwas, wird es angepasst – ohne
Rücksicht auf die alte Version. Welche Version zuletzt geprüft wurde, steht im
Snapshot.

## 9. Am Ende: Kaltstart klein halten

Jeder neue Chat liest `CLAUDE.md`, `CHATSTART.md`, diese Datei und den
Snapshot, **bevor** er irgendetwas tun kann. **So kurz wie möglich, aber nicht
kürzer.** Neue Erklärungen gehören in Dateien, die nur bei Bedarf gelesen
werden (Spezifikationen unter `docs/`); der Snapshot bekommt **einen Satz je
Wunsch, Bug und Task**, die Begründung steht im Verlauf.

Zum Abschluss einer Sitzung: Erledigtes aus dem Snapshot **entfernen**, keine
ableitbaren Zahlen pflegen, Links gegenprüfen.
