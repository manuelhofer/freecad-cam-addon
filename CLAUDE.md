# CLAUDE.md

**Lies zuerst [CHATSTART.md](CHATSTART.md).** Dort steht, was das Projekt ist,
wie gearbeitet wird und welche Datei zu welcher Aufgabe gehört. Diese Datei
enthält nur, was ausschließlich für Claude Code gilt – alles andere steht
werkzeugneutral in `CHATSTART.md`, damit keine zweite, driftende Fassung
entsteht.

- **Nicht pushen** ohne ausdrückliche Ansage. Lokal committen ist in Ordnung.
- **Die Oberfläche siehst du nur als Screenshot.** `scripts/oberflaeche_testen.sh`
  startet FreeCAD unsichtbar (Xvfb) und spielt ein Szenario aus `tests/gui/`
  durch; die Screenshots schaust du dir an und zeigst sie Manuel. Ob ein
  Dialog **verständlich** ist und sich gut bedient, prüft trotzdem nur
  Manuel in seinem FreeCAD. Schreib nie „funktioniert“, wenn du es nicht
  gesehen hast – schreib, was er klicken soll und was er dann sehen muss.
