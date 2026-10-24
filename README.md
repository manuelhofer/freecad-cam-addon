# FreeCAD CAM-Addon

Macht CAM in FreeCAD leichter – vom Teil bis zum fertigen NC-Programm.

Ein **Werkstatt-Addon auf FreeCAD CAM**, gebaut für eine Werkstatt (Drehfräsen auf einer DMG CLX 550
mit Siemens 840D, 3- und 5-Achs-Fräsen) und offen für alle, die es ausprobieren wollen – ohne
Geld, ohne Spendenlink. Es ersetzt CAM nicht, es setzt darauf auf: Jeder Job ist ein CAM-Job,
jede Operation eine Path-Operation, die Werkzeuge sind ToolBits, das Räumen rechnet mit dem
Adaptive-Kern von CAM, die Maschine ist eine Baugruppe (Assembly). Das Addon kommt **nicht** von
den CAM-Entwicklern von FreeCAD und ist nicht mit ihrer Planung abgestimmt – Fragen und Fehler
zum Addon bitte hier stellen (siehe [Testen und Fehler melden](#testen-und-fehler-melden)), nicht
bei FreeCAD.

Für FreeCAD 1.1 und den Wochen-Build. **Geprüft wird unter Linux**; Windows und macOS sollten
gehen, sind aber nicht geprüft – Rückmeldungen von dort sind besonders willkommen.

## Was es kann

- **Maschine** – als Baugruppe beschreiben (Achsen, Spindeln, Revolver, Aufnahmen) oder
  fertig anlegen: Drehmaschine mit Y-Achse, 3-Achs-Fräse, 5-Achs-Fräsen. Achsen von Hand
  verfahren, an CAM übergeben.
- **Werkzeuge** – Werkzeugverwaltung mit 26 Werkzeugarten, Haltern, Werkstoffen und
  Schnittwerten je Werkstoff; Magazine je Maschine mit Rüstliste.
- **Bearbeitung im Quader** – ein Assistent für Planfräsen, Räumen, Kontur, Taschen, Nuten,
  Bohren, Gewinde, Entgraten, 3D-Schruppen und 3D-Schlichten. Er rechnet die Strategien durch
  und schlägt die schnellste vor.
- **4 Achsen** – das Teil in eine runde Stange legen, rundum schruppen und schlichten, nur
  gewählte Flächen, Abflachungen, Querbohrungen, Nuten, Entgraten. An der Stirnseite fährt Y,
  solange es reicht, danach hilft C.
- **5 Achsen** – geschwenkte Ebenen (3+2) und simultan: Kugelfräser angestellt, Flanke,
  Wegkippen.
- **Prüfen** – reichen die Verfahrwege? Die Maschine fährt die Bahn in 3D ab, trägt das
  Rohteil ab und zeigt Kollisionen von Werkzeug, Halter und Maschine.
- **Programm** – ein eigener Postprozessor für LinuxCNC, Siemens 840D, Fanuc, Haas, Mach und
  Heidenhain (iTNC 530, TNC 640). Rundachsen nach DIN 66217, einstellbar je Maschine.

**Der Einstieg:** Menü **CAM-Addon → So geht’s** – der Weg vom Teil zum Programm in sechs
Schritten. Jedes Fenster hat ein **?** mit Hilfe. Beispielteile liegen in
[beispiele/](beispiele/). Das Update lädt sie nicht mit; **CAM-Addon → Beispiele laden …** holt
sie, wenn du sie willst.

## Installieren

1. In FreeCAD **Ansicht → Fenster → Python-Konsole** öffnen.
2. Die Zeile für dein System hineinkopieren und Enter drücken. Alle drei tun dasselbe, nur der
   Weg zu GitHub ist ein anderer.

   **Windows** – lädt mit dem curl, das Windows 10/11 mitbringt. Geht auch, wenn FreeCAD selbst
   nicht ins Netz kommt (etwa FreeCAD 26.3.0RC1):

   ```
   import subprocess as s; exec(s.run(["curl", "-sSfL", "https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py"], capture_output=True, check=True).stdout)
   ```

   **Linux und macOS** – über den Netzzugang des Addon-Managers (Qt), bis FreeCAD 1.1 (in 26.3 lädt
   der Addon-Manager aus der Python-Konsole grundsätzlich nicht – dann die Zeile darunter):

   ```
   import NetworkManager as n; n.InitializeNetworkManager(); exec(n.AM_NETWORK_MANAGER.blocking_get("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").data())
   ```

   **Ausweichen über Python (urllib)** – wenn die Zeile oben `'NoneType' object has no attribute
   'data'` meldet:

   ```
   import urllib.request as u; exec(u.urlopen("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").read())
   ```

   Meldet diese `unknown url type: https`, fehlt Pythons SSL – dann die curl-Zeile von oben; die
   geht auch unter Linux und macOS, wo curl installiert ist.

3. FreeCAD neu starten. Beim ersten Start fragt das Addon nach der Sprache. Das Menü
   **CAM-Addon** und seine Werkzeugleiste erscheinen in den Arbeitsbereichen **Assembly** und
   **CAM**.

Was die Zeilen tun, steht oben in [installieren.py](installieren.py). Sie brauchen weder Git
noch GitHub Desktop.

**Geht keine der drei Zeilen** – etwa ohne curl in einem FreeCAD, das selbst nicht ins Netz
kommt –, dann von Hand:

1. Auf dieser Seite **Code → Download ZIP**.
2. In FreeCADs Python-Konsole `FreeCAD.getUserAppDataDir()` eingeben. Im angezeigten Ordner liegt
   `Mod` – fehlt er, anlegen.
3. Den Ordner `freecad-cam-addon-main` aus dem ZIP nach `Mod` ziehen und in `freecad-cam-addon`
   umbenennen. `InitGui.py` muss direkt darin liegen, nicht eine Ebene tiefer.
4. FreeCAD neu starten.

In so einem FreeCAD geht auch das Aktualisieren nur von Hand: den Ordner `freecad-cam-addon` durch
den aus einem neuen ZIP ersetzen. Die Einstellungen des Addons bleiben dabei erhalten.

**Oder über den Addon-Manager:** **Bearbeiten → Einstellungen → Addon-Manager → Eigene
Repositories**, dort `https://github.com/manuelhofer/freecad-cam-addon` mit dem Branch `main`
eintragen. Dann **Werkzeuge → Addon-Manager**, **freecad-cam-addon** suchen, installieren,
FreeCAD neu starten. Über den Addon-Manager lässt es sich auch wieder entfernen.

## Aktualisieren

Menü **CAM-Addon → Nach Updates suchen**: Gibt es eine neue Version, fragt das Addon „Jetzt
aktualisieren?“. Automatisch beim Start suchen lässt es sich unter **Bearbeiten →
Einstellungen → CAM-Addon** einschalten.

## Gut zu wissen

- **Dokumente mit Operationen des Addons** („Nut“, „Fase“, „Räumen“, „Rundum schruppen“ …)
  lassen sich nur mit dem Addon bearbeiten und neu rechnen. Das NC-Programm, das daraus entsteht,
  braucht es nicht.
- **Alle Kerne:** Vorschau, Hüllflächen, Kollision und Abtrag rechnen in eigenen Prozessen
  (FreeCADCmd neben FreeCAD), einer je Kern; das Fenster bleibt bedienbar. Wie viele es sein
  dürfen, steht unter **Bearbeiten → Einstellungen → CAM-Addon** (0 = so viele wie Kerne); reicht
  der Speicher nicht, bekommt ein weiterer Prozess erst Arbeit, wenn wieder genug frei ist.
- **Daten Dritter:** Die Herstellerwerkzeuge der Werkzeugverwaltung („Herstellerwerkzeuge …“) –
  Hoffmann Group (HOLEX, GARANT), Ceratizit, Gühring, Jongen, Sandvik Coromant – sind Maße und
  Schnittwerte als **Richtwerte** aus öffentlich zugänglichen Produktseiten und Datenblättern;
  die Quelle steht je Eintrag dabei. Die Namen sind Marken ihrer Inhaber; das Addon hat mit den
  Herstellern nichts zu tun. Vor dem Fräsen mit den Angaben des Herstellers vergleichen. Wer als
  Rechteinhaber einen Eintrag nicht hier sehen möchte, meldet sich – er kommt dann heraus. Das
  Testteil „Geist“ (`beispiele/geist_stl`) ist gemeinfrei (CC0), siehe dort.

## Testen und Fehler melden

Wer es ausprobiert, hilft am meisten mit einem Fehlerbericht, der sich nachstellen lässt:

1. **Issues → New issue** auf dieser Seite (oder im Forum, siehe unten).
2. Dazu: die FreeCAD-Version (**Hilfe → Über FreeCAD → In die Zwischenablage kopieren**), die
   Version des Addons (**CAM-Addon → Nach Updates suchen** zeigt sie), das Betriebssystem.
3. Was du angeklickt hast und was du erwartet hättest; ein Bildschirmfoto; wenn möglich die Datei
   (`.FCStd`, auch nur ein Ausschnitt des Teils).
4. Steht im **Bericht** (Ansicht → Fenster → Ausgabefenster) etwas Rotes, das bitte mitschicken.

Besonders gesucht: Tests unter **Windows und macOS** und an anderen Maschinen und Steuerungen
(Heidenhain, Fanuc, Haas, LinuxCNC). Vorstellung und Austausch im FreeCAD-Forum:
[englisch](https://forum.freecad.org/viewtopic.php?t=107889),
[deutsch](https://forum.freecad.org/viewtopic.php?t=107911).

## Für Mitarbeitende

Aktueller Stand und nächste Schritte: [docs/STATUS_SNAPSHOT.md](docs/STATUS_SNAPSHOT.md).
Arbeitsweise und Aufbau: [CHATSTART.md](CHATSTART.md).

## Lizenz

LGPL-2.1-or-later, wie FreeCAD selbst – siehe [LICENSE](LICENSE). Die Herstellerdaten sind davon
ausgenommen (siehe „Daten Dritter“ oben).

## English

**A workshop add-on built on top of FreeCAD CAM** – made for one shop (mill-turning on a DMG CLX 550
with Siemens 840D, 3- and 5-axis mills) and open to anyone who wants to try it; no money, no
donation link. It does not replace CAM, it builds on it: every job is a CAM job, every operation a
Path operation, tools are ToolBits, clearing runs on CAM's Adaptive kernel, the machine is an
Assembly. It is **not** made by FreeCAD's CAM developers and not coordinated with their roadmap –
please report problems with the add-on here, not to FreeCAD.

What it does: machines as assemblies (lathe with Y, 3- and 5-axis mills), a tool manager with
holders, magazines and cutting data per material, assistants for 2.5D, 3D, 4-axis and 5-axis
milling, a machine simulation with stock removal and collision check, and post processors for
LinuxCNC, Siemens 840D, Fanuc, Haas, Mach and Heidenhain. Heavy computations run in separate
FreeCADCmd processes, one per core, so the window stays responsive.

**Install:** paste one of the lines from “Installieren” above into FreeCAD's Python console
(View → Panels → Python console) and restart FreeCAD; the language can be set to English at the
first start. **Tested on Linux only** (FreeCAD 1.1.4 and the weekly build) – reports from Windows
and macOS are very welcome. To report a bug, open an issue with the FreeCAD version
(Help → About → Copy to clipboard), the add-on version, your OS, what you clicked, a screenshot and,
if possible, the `.FCStd` file. Manufacturer tool data (dimensions and cutting data from public
product pages and data sheets, source given per entry) are reference values only; brand names
belong to their owners. Discussion: [FreeCAD forum](https://forum.freecad.org/viewtopic.php?t=107889).
