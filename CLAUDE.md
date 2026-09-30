# CLAUDE.md

**Lies zuerst [CHATSTART.md](CHATSTART.md).** Dort steht, was das Projekt ist,
wie gearbeitet wird und welche Datei zu welcher Aufgabe gehört. Diese Datei
enthält nur, was ausschließlich für Claude Code gilt – alles andere steht
werkzeugneutral in `CHATSTART.md`, damit keine zweite, driftende Fassung
entsteht.

- **Pushen:** Manuel hat am 2026-09-25 dauerhaft freigegeben zu pushen,
  sobald die Prüfungen grün sind, die Claude für nötig hält (Manuel,
  2026-09-30: „wenn DU sie für nötig hältst … Ich persönlich benötige keine
  Tests solange alles funktioniert“) – welche das sind, steht in
  `docs/arbeitsregeln.md`, Abschnitt 5; reine Doku-Änderungen ohne Testlauf.
  Ohne grüne Prüfungen nur auf ausdrückliche Ansage. Lokal committen ist
  immer in Ordnung.
- **„Pusch jetzt“ heißt sofort** (Manuel, 2026-09-27: „wenn ich sage pusch
  jetzt dann auch puschen !!“): was committet ist, gleich pushen – ohne auf
  laufende Prüfungen zu warten; sie laufen danach, und was sie finden, wird
  sofort behoben. Soll Manuel etwas ausprobieren, braucht der Push eine **höhere
  Version** in `package.xml`: „Nach Updates schauen“ bietet nur eine neue
  Version an – alles seit 0.24.0 lag auf GitHub, kam bei ihm aber nicht an.
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
