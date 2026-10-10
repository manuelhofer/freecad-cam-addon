# FreeCAD CAM-Addon

Macht CAM in FreeCAD leichter – vom Teil bis zum fertigen NC-Programm.
Für FreeCAD 1.1 und den Wochen-Build, auf jedem Betriebssystem.

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
Schritten. Jedes Fenster hat ein **?** mit Hilfe. Ein Beispielteil liegt in
[beispiele/](beispiele/).

## Installieren

1. In FreeCAD **Ansicht → Fenster → Python-Konsole** öffnen.
2. Die Zeile für dein System hineinkopieren und Enter drücken. Alle drei tun dasselbe, nur der
   Weg zu GitHub ist ein anderer.

   **Windows** – lädt mit dem curl, das Windows 10/11 mitbringt. Geht auch, wenn FreeCAD selbst
   nicht ins Netz kommt (etwa FreeCAD 26.3.0RC1):

   ```
   import subprocess as s; exec(s.run(["curl", "-sSfL", "https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py"], capture_output=True, check=True).stdout)
   ```

   **Linux und macOS** – über den Netzzugang des Addon-Managers (Qt):

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

## Für Mitarbeitende

Aktueller Stand und nächste Schritte: [docs/STATUS_SNAPSHOT.md](docs/STATUS_SNAPSHOT.md).
Arbeitsweise und Aufbau: [CHATSTART.md](CHATSTART.md).

## Lizenz

LGPL-2.1-or-later, wie FreeCAD selbst – siehe [LICENSE](LICENSE).
