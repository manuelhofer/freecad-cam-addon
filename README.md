# FreeCAD CAM-Addon

Ein Addon, das die CAM-Oberfläche von FreeCAD bedienbarer macht.

- Für die **aktuelle stabile Version** von FreeCAD (derzeit 1.1.3) **und**
  den **Wochen-Build**, auf jedem Betriebssystem. „An CAM übergeben“ braucht
  die CAM-Maschinendefinition, die es derzeit nur im Wochen-Build gibt – in
  1.1.3 erklärt das Addon das beim Klick.
- Unabhängig von Maschine und Postprozessor.

## Was es kann

- **Maschine bearbeiten:** eine Maschine als Baugruppe beschreiben –
  Achsen, Spindeln, Werkzeug- und Werkstückaufnahmen – und an CAM übergeben.
- **Werkzeugverwaltung:** Werkstoffliste mit deutschen Bezeichnungen
  („1.4301 X5CrNi18-10 · Edelstahl, austenitisch“), Zusammensetzung und
  Härte; Werkzeuge mit Schnittwerten je Werkstoff und Einsatz – vc und fz
  eingeben, Drehzahl, Vorschub und Zeitspanvolumen rechnet das Addon; ein
  Bild des Eingriffs; zwei Strategien vergleichen (Abtrag, Verschleiß) mit
  einem Urteil in Sätzen.
- **An CAM übergeben:** die Werkzeuge als Werkzeugbibliothek „CAM-Addon“;
  „Schnittwerte in den Job“ setzt Drehzahl und Vorschub der
  Werkzeug-Controller eines Jobs passend zum Werkstoff des Rohteils.

Stand und nächste Schritte: [docs/STATUS_SNAPSHOT.md](docs/STATUS_SNAPSHOT.md).
Für KI-Assistenten: [CHATSTART.md](CHATSTART.md).

## Installieren – eine Zeile, auf jedem Betriebssystem

Geht, sobald das Repository öffentlich ist (siehe unten, wenn es noch privat
ist):

1. In FreeCAD **Ansicht → Fenster → Python-Konsole** öffnen.
2. Diese Zeile hineinkopieren und Enter drücken:

   ```
   import urllib.request as u; exec(u.urlopen("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").read())
   ```

3. FreeCAD neu starten. Beim ersten Start fragt das Addon nach der Sprache.
   Seine Werkzeugleiste erscheint in den Arbeitsbereichen **Assembly** und
   **CAM**.

Die Zeile legt das Addon in den Addon-Ordner von FreeCAD – ohne Git, ohne
GitHub Desktop – und trägt es im Addon-Manager ein. **Aktualisieren:** Das
Addon schaut beim Start selbst nach und fragt bei einer neuen Version
„Jetzt aktualisieren?“ (abschalten: Bearbeiten → Einstellungen →
CAM-Addon). Von Hand: dieselbe Zeile noch einmal, oder **Werkzeuge →
Addon-Manager** – der kann das Addon auch wieder entfernen. Was die Zeile
genau tut, steht oben in [installieren.py](installieren.py).

**Oder ganz über den Addon-Manager:** **Bearbeiten → Einstellungen →
Addon-Manager**, unter **Eigene Repositories** eine Zeile mit der URL
`https://github.com/manuelhofer/freecad-cam-addon` und dem Branch `main`;
dann **Werkzeuge → Addon-Manager**, nach **freecad-cam-addon** suchen,
**Installieren**, FreeCAD neu starten.

## Installieren, solange das Repository privat ist

Ein privates Repository gibt GitHub nur angemeldet heraus – die Zeile oben
und der Addon-Manager kommen dann nicht heran. Dann holt man das Addon mit
**GitHub Desktop** (oder Git) direkt in den Addon-Ordner von FreeCAD:

1. In FreeCAD die Python-Konsole öffnen (**Ansicht → Fenster →
   Python-Konsole**) und eingeben:
   `App.getUserAppDataDir() + "Mod"`
   Das ist der Ordner für Addons – auf jedem Betriebssystem ein anderer, die
   Konsole nennt den richtigen.
2. In GitHub Desktop: **File → Clone repository** →
   `manuelhofer/freecad-cam-addon`, als **Local path** den Mod-Ordner aus
   Schritt 1 wählen. Es entsteht der Ordner `freecad-cam-addon`.
   (Mit Git: `git clone https://github.com/manuelhofer/freecad-cam-addon`
   im Mod-Ordner.)
3. FreeCAD neu starten.

**Aktualisieren:** Das Addon schaut beim Start von FreeCAD selbst nach (per
Git, mit der Anmeldung von GitHub Desktop bzw. Git) und fragt bei einer neuen
Version „Jetzt aktualisieren?“. Abschalten und „Jetzt nach Updates suchen“:
Bearbeiten → Einstellungen → CAM-Addon. Von Hand: in GitHub Desktop **Fetch
origin**, dann **Pull origin** (bzw. `git pull` im Ordner) und FreeCAD neu
starten – so kommen auch kleine Änderungen an, die noch keine neue
Versionsnummer haben. Ein so installierter Git-Klon bleibt es auch, wenn das
Repository öffentlich wird; die Zeile oben lässt ihn in Ruhe.

## Lizenz

LGPL-2.1-or-later, wie FreeCAD selbst – siehe [LICENSE](LICENSE).
