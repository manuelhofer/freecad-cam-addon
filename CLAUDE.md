# CLAUDE.md

**Lies zuerst [CHATSTART.md](CHATSTART.md).** Dort steht, was das Projekt ist,
wie gearbeitet wird und welche Datei zu welcher Aufgabe gehört. Diese Datei
enthält nur, was ausschließlich für Claude Code gilt – alles andere steht
werkzeugneutral in `CHATSTART.md`, damit keine zweite, driftende Fassung
entsteht.

- **Nicht pushen** ohne ausdrückliche Ansage. Lokal committen ist in Ordnung.
- **Nach jedem Push bei GitHub selbst nachsehen:**
  `git ls-remote https://github.com/manuelhofer/freecad-cam-addon main` muss
  den eigenen Commit zeigen. `origin` zu fragen reicht nicht: Zeigt `origin`
  versehentlich auf einen Ordner, meldet Git „Everything up-to-date“, obwohl
  nichts angekommen ist – so blieben P-2026-09-25-23 bis -28 unbemerkt lokal.
- **Die Oberfläche siehst du nur als Screenshot.** `scripts/oberflaeche_testen.sh`
  startet FreeCAD unsichtbar (Xvfb) und spielt ein Szenario aus `tests/gui/`
  durch; die Screenshots schaust du dir an und zeigst sie Manuel. Ob ein
  Dialog **verständlich** ist und sich gut bedient, prüft trotzdem nur
  Manuel in seinem FreeCAD. Schreib nie „funktioniert“, wenn du es nicht
  gesehen hast – schreib, was er klicken soll und was er dann sehen muss.
