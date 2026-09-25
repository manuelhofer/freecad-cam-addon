# FreeCAD CAM-Addon

Ein Addon, das die CAM-Oberfläche von FreeCAD bedienbarer macht.

- Für den **aktuellen Wochen-Build** von FreeCAD, auf jedem Betriebssystem.
- Unabhängig von Maschine und Postprozessor.

Stand und nächste Schritte: [docs/STATUS_SNAPSHOT.md](docs/STATUS_SNAPSHOT.md).
Für KI-Assistenten: [CHATSTART.md](CHATSTART.md).

## Installieren, solange das Repository privat ist (empfohlen)

Das Repository ist privat. FreeCADs Addon-Manager kann sich nicht bei GitHub
anmelden – er hilft deshalb erst, wenn es öffentlich ist (siehe unten). Bis
dahin holt man das Addon mit **GitHub Desktop** (oder Git) direkt in den
Addon-Ordner von FreeCAD:

1. In FreeCAD die Python-Konsole öffnen (Ansicht → Ansichten →
   Python-Konsole) und eingeben:
   `App.getUserAppDataDir() + "Mod"`
   Das ist der Ordner für Addons – auf jedem Betriebssystem ein anderer, die
   Konsole nennt den richtigen.
2. In GitHub Desktop: **File → Clone repository** →
   `manuelhofer/freecad-cam-addon`, als **Local path** den Mod-Ordner aus
   Schritt 1 wählen. Es entsteht der Ordner `freecad-cam-addon`.
   (Mit Git: `git clone https://github.com/manuelhofer/freecad-cam-addon`
   im Mod-Ordner.)
3. FreeCAD neu starten. Beim ersten Start fragt das Addon nach der Sprache.
   Seine Werkzeugleiste erscheint in den Arbeitsbereichen **Assembly** und
   **CAM**.

**Aktualisieren:** Das Addon schaut beim Start von FreeCAD selbst nach (per
Git, mit der Anmeldung von GitHub Desktop bzw. Git) und fragt „Jetzt
aktualisieren?“. Abschalten und „Jetzt nach Updates suchen“: Bearbeiten →
Einstellungen → CAM-Addon. Von Hand: in GitHub Desktop **Fetch origin**, dann
**Pull origin** (bzw. `git pull` im Ordner) und FreeCAD neu starten.

## Installieren über den Addon-Manager (erst wenn das Repository öffentlich ist)

Dann meldet FreeCAD neue Versionen selbst und installiert sie auf Knopfdruck.

1. **Bearbeiten → Einstellungen → Addon-Manager**, unter
   **Eigene Repositories** eine Zeile: URL
   `https://github.com/manuelhofer/freecad-cam-addon`, Branch `main`.
2. **Werkzeuge → Addon-Manager**, nach **freecad-cam-addon** suchen,
   **Installieren**, FreeCAD neu starten.

Ausprobiert (P-2026-09-25-23): Einen **lokalen Ordner** als eigenes
Repository installiert der Addon-Manager zwar, erkennt dort aber keine
Updates – für die private Phase bringt er deshalb nichts.

## Lizenz

LGPL-2.1-or-later, wie FreeCAD selbst – siehe [LICENSE](LICENSE).
