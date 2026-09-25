# FreeCAD CAM-Addon

Ein Addon, das die CAM-Oberfläche von FreeCAD bedienbarer macht.

- Für den **aktuellen Wochen-Build** von FreeCAD, auf jedem Betriebssystem.
- Unabhängig von Maschine und Postprozessor.

Stand und nächste Schritte: [docs/STATUS_SNAPSHOT.md](docs/STATUS_SNAPSHOT.md).
Für KI-Assistenten: [CHATSTART.md](CHATSTART.md).

## Installieren mit automatischen Updates (empfohlen)

Über den Addon-Manager von FreeCAD – dann meldet FreeCAD neue Versionen selbst
und installiert sie auf Knopfdruck.

1. **Bearbeiten → Einstellungen → Addon-Manager**, dort unter
   **Eigene Repositories** eine Zeile hinzufügen:
   - Repository-URL: `https://github.com/manuelhofer/freecad-cam-addon`
   - Branch: `main`
2. **Werkzeuge → Addon-Manager** öffnen, nach **freecad-cam-addon** suchen,
   **Installieren**.
3. FreeCAD neu starten. Beim ersten Start fragt das Addon nach der Sprache.
   Seine Werkzeugleiste erscheint in den Arbeitsbereichen **Assembly** und
   **CAM**.

Updates: Der Addon-Manager zeigt verfügbare Updates an (auch beim Start von
FreeCAD, wenn in seinen Einstellungen die automatische Prüfung eingeschaltet
ist); **Aktualisieren**, FreeCAD neu starten.

## Installieren von Hand

Ohne Addon-Manager, z. B. zum Ausprobieren eines bestimmten Stands:

1. In FreeCAD die Python-Konsole öffnen (Ansicht → Ansichten →
   Python-Konsole) und eingeben:
   `App.getUserAppDataDir() + "Mod"`
   Das ist der Ordner für Addons – auf jedem Betriebssystem ein anderer, die
   Konsole nennt den richtigen.
2. Dieses Repository dort hinein legen, als Ordner `freecad-cam-addon`:
   - mit Git: `git clone https://github.com/manuelhofer/freecad-cam-addon`
     im Mod-Ordner, oder
   - auf GitHub **Code → Download ZIP**, entpacken und den Ordner in
     `freecad-cam-addon` umbenennen.
3. FreeCAD neu starten. Beim ersten Start fragt das Addon nach der Sprache.
   Seine Werkzeugleiste erscheint in den Arbeitsbereichen **Assembly** und
   **CAM**.

Aktualisieren von Hand: mit Git `git pull` im Ordner, sonst ZIP neu laden und
den Ordner ersetzen.

## Lizenz

LGPL-2.1-or-later, wie FreeCAD selbst – siehe [LICENSE](LICENSE).
