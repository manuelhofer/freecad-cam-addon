# Vorstellung im FreeCAD-Forum – Entwurf

Manuel, 2026-10-10: „wir sollten das addon langsam mal ins freecad forum reinschreiben … den text
noch etwas verschönern sozusagen als aushängeschild … und nach meinungen dazu fragen oder nach
bedienern die eben die bedienung verbessern wollen“; „bau so standart antworten gleich mit ein
vonwegen lizenz usw“. Hier der Entwurf – englisch für das Unterforum „Path/CAM“ (die größere
Leserschaft), deutsch für das deutsche Unterforum mit Verweis auf den englischen Thread. Vor dem
Posten erledigt (2026-10-10): das Repo ist öffentlich (GitHub ohne Anmeldung: public, LGPL-2.1),
die Installation aus einem leeren Profil geprüft (`installieren.py` holt 0.209.0, trägt das Repo im
Addon-Manager ein, der nächste Start lädt das Addon). Die Bilder zum Anhängen liegen in
`docs/bilder/forum/`: `bearbeitung_vorschlaege.png` (Assistent „Bearbeitung“, Schritt 2 mit
Vorschlägen und Zeiten), `vierachs_welle.png` (Rundum schruppen an der Welle), `maschine_pruefen.png`
(„Auf der Maschine prüfen“ an der 5-Achs-Fräse, geschwenkte Ebene).

## Deutsch

**Betreff:** CAM-Addon für FreeCAD 1.1 – Werkzeugverwaltung, Maschinen-Baukasten, Drehen mit
Y, 4-Achs-Bearbeitung – Meinungen und Tester gesucht

Hallo zusammen,

ich fräse und drehe an einer DMG CLX 550 mit Y-Achse und an ein paar 3-Achs-Fräsen und wollte
den Weg vom Teil zum Programm in FreeCAD bequemer haben: weniger Dialoge, mehr Vorschläge, die
man einfach annehmen kann. Daraus ist über die letzten Wochen ein Addon geworden, das ich hier
vorstellen und zur Diskussion stellen möchte.

Vorweg, damit es keine Überraschung gibt: Entworfen und an der Maschine geprüft habe ich das
Addon selbst; geschrieben ist der Code mit KI-Unterstützung nach meinen Vorgaben. Ich beurteile
es über das Ergebnis am Werkstück, nicht über Codezeilen. Wer in den Code schaut, darf gern
kritisieren – und wer die Dialoge nicht versteht, hat recht. Genau das will ich hören.

**Was drin ist** (Stand heute, Version 0.209):

- **Werkzeugverwaltung** mit Schnittwerten je Werkstoffklasse und Einsatz (Schruppen, Vollnut,
  Schlichten, Bohren …), Haltern und Magazinen; Übergabe an FreeCAD CAM und zurück. Dazu eine
  vorgefüllte **Werkzeugkiste** mit echten Herstellerdaten (Ceratizit, Gühring, Jongen, HOLEX,
  GARANT) und einem JSON-Import für eigene Reihen, der Doppeltes erkennt.
- **Maschinen-Baukasten**: Beispielmaschinen (3-Achs-Fräse, 5-Achs-Fräsen Tisch/Tisch,
  Kopf/Tisch, Kopf/Kopf, Drehmaschine mit Revolver und Y) als Assembly, eigene Maschinen aus
  einer Baugruppe, Verfahrwege und Anschläge, Kollisionsprüfung der Bahnen auf der Maschine.
- **Assistent „Bearbeitung“** für Teile im Quader: Flächen anklicken, das Addon schlägt
  Strategien vor (Planfräsen, Räumen, Kontur, Bohren, Gewinde, Entgraten, 3D-Schruppen und
  -Schlichten, Bleistift …), zeigt Zeit und Ergebnis vorab; ein Klick legt die Operationen an.
- **4-Achs-Bearbeitung** am runden Rohteil (Drehmaschine mit angetriebenen Werkzeugen oder
  Fräse mit Rundachse): Rundum schruppen und schlichten, Plan indexiert mit der Y-Achse,
  Querbohrungen, Nuten, Entgraten.
- **3+2 und 5 Achsen simultan**: geschwenkte Ebenen, Flankenfräsen, Entgraten im Raum, ein
  Vergleich von Werkzeugen und Anstellungen fürs 3D-Schlichten – gerechnet und in der
  Kollisionsprüfung geprüft, aber bisher nicht an einer echten 5-Achs-Maschine gefahren.
- **Postprozessor** für Siemens (CYCLE800, Bohrzyklen) und gerechnete Rundachsen, Programm je
  Maschine, Einrichtblatt.
- Oberfläche und Hilfe auf Deutsch und Englisch, Beispiele dabei.

**Was geprüft ist:** 3-Achs- und 4-Achs-Kinematik, an meiner CLX mit Y und an 3-Achs-Fräsen.
Alles mit 5 Achsen ist bisher gerechnet und simuliert. Es wird laufend weiter daran gearbeitet;
jeder Schritt ist im Repo nachvollziehbar.

**Was ich mir wünsche:**

1. Meinungen – ist der Weg sinnvoll, was fehlt, was ist umständlich?
2. Tester – wer eine 5-Achs-Maschine oder eine andere Steuerung hat und ein Beispielteil einmal
   durchspielen mag.
3. Bediener-Feedback – Screenshot, ein Satz, was unklar war. Das reicht mir.

**Installation:** FreeCAD 1.1 (geprüft mit 1.1.4). Am einfachsten die eine Zeile für die
Python-Konsole aus dem README des Repos; oder Addon-Manager → Einstellungen → eigenes Repository
`https://github.com/manuelhofer/freecad-cam-addon` (Branch `main`) eintragen und dort
installieren. Im Menü erscheint „CAM-Addon“, der erste Punkt „So geht’s“ führt durch.

**Vorab beantwortet:**

- *Lizenz?* LGPL 2.1 oder neuer, wie FreeCAD selbst.
- *Betriebssystem?* Reines Python und PySide, keine Abhängigkeiten außer FreeCAD. Entwickelt und
  geprüft auf Linux; Windows und macOS sollten laufen, sind aber ungeprüft – Rückmeldung
  willkommen.
- *FreeCAD-Version?* 1.1 (stabil) und der aktuelle Wochen-Build; 1.0 geht nicht (Assembly,
  CAM-API).
- *Warum ein Addon und nicht ins CAM-Modul?* Weil es eigene Dinge mitbringt, die im Modul nicht
  da sind: Werkzeugverwaltung mit Schnittwerten, Maschine als Assembly mit Kinematik und
  Kollisionsprüfung, Assistenten, die Operationen vorschlagen. Es setzt auf CAM auf: Der Job ist
  ein CAM-Job, die Operationen sind Path-Operationen, Werkzeuge gehen in beide Richtungen.
  Nichts davon ersetzt das CAM-Modul.
- *KI-Code – ist das sicher?* Offen gesagt: Der Code ist so entstanden. Dafür gibt es über hundert
  Prüfdateien und über hundert Oberflächen-Szenarien, die bei jeder Änderung laufen, und die
  Bahnen prüfe ich an der Maschine. Fehler gibt es trotzdem, und ich will sie wissen.
- *Welche Steuerungen?* Siemens (840D/828D) mit CYCLE800 und Bohrzyklen; für andere Steuerungen
  schreibt der Postprozessor die Rundachsen gerechnet aus. Wer eine andere Steuerung hat und
  testen mag: gern.
- *Sprache?* Oberfläche und Hilfe deutsch und englisch. Der Code und die Entwickler-Doku sind
  auf Deutsch – wer mitprogrammieren will, sagt Bescheid, dann gibt es einen englischen Einstieg.
- *Telemetrie?* Keine. Die Update-Prüfung fragt GitHub nur, wenn man sie einschaltet.
- *Fehler melden?* Am liebsten als Issue auf GitHub, mit Datei und Screenshot; hier im Thread
  geht auch.

Danke fürs Lesen – und für jede Kritik.
Manuel

## English

**Subject:** CAM add-on for FreeCAD 1.1 – tool manager, machine builder, turning with Y, 4-axis
machining – looking for opinions and testers

Hi all,

I mill and turn on a DMG CLX 550 with Y axis and on a few 3-axis mills, and I wanted the way
from part to program in FreeCAD to be more convenient: fewer dialogs, more proposals you can
simply accept. Over the last weeks this has grown into an add-on that I would like to present
here and put up for discussion.

Up front, so there is no surprise: I designed the add-on and verified it on the machine myself;
the code was written with AI assistance, to my specification. I judge it by the result on the
workpiece, not by lines of code. Anyone who looks at the code is welcome to criticise it – and
anyone who does not understand a dialog is right. That is exactly what I want to hear.

**What is in it** (as of today, version 0.209):

- **Tool manager** with cutting data per material class and application (roughing, slotting,
  finishing, drilling …), holders and magazines; hand-over to FreeCAD CAM and back. Plus a
  pre-filled **tool box** with real manufacturer data (Ceratizit, Gühring, Jongen, HOLEX,
  GARANT) and a JSON import for your own series that recognises duplicates.
- **Machine builder**: example machines (3-axis mill, 5-axis mills table/table, head/table,
  head/head, lathe with turret and Y) as assemblies, your own machines from an assembly, travel
  limits and stops, collision check of the paths on the machine.
- **“Machining” assistant** for parts in a block: click faces, the add-on proposes strategies
  (facing, clearing, contour, drilling, threads, deburring, 3D roughing and finishing, pencil …),
  shows time and result in advance; one click creates the operations.
- **4-axis machining** on round stock (lathe with live tooling or mill with a rotary axis):
  all-round roughing and finishing, indexed facing with the Y axis, cross holes, slots,
  deburring.
- **3+2 and 5-axis simultaneous**: swivelled planes, flank milling, deburring in 3D, a comparison
  of tools and tilts for 3D finishing – computed and checked in the collision check, but not yet
  run on a real 5-axis machine.
- **Post-processor** for Siemens (CYCLE800, drilling cycles) and computed rotary axes, program
  per machine, setup sheet.
- Interface and help in English and German, examples included.

**What is verified:** 3-axis and 4-axis kinematics, on my CLX with Y and on 3-axis mills.
Everything with 5 axes is so far computed and simulated. Work continues; every step is traceable
in the repository.

**What I am looking for:**

1. Opinions – does the approach make sense, what is missing, what is awkward?
2. Testers – anyone with a 5-axis machine or another control who would run an example part once.
3. Operator feedback – a screenshot and one sentence about what was unclear. That is enough.

**Installation:** FreeCAD 1.1 (verified with 1.1.4). Easiest is the one line for the Python
console from the README of the repository; or Addon Manager → preferences → custom repository
`https://github.com/manuelhofer/freecad-cam-addon` (branch `main`) and install from there. A
menu “CAM-Addon” appears; its first entry “How it works” walks you through.

**Answered in advance:**

- *Licence?* LGPL 2.1 or later, like FreeCAD itself.
- *Operating system?* Pure Python and PySide, no dependencies beyond FreeCAD. Developed and
  verified on Linux; Windows and macOS should work but are unverified – feedback welcome.
- *FreeCAD version?* 1.1 (stable) and the current weekly build; 1.0 does not work (Assembly,
  CAM API).
- *Why an add-on and not part of the CAM workbench?* Because it brings things of its own that the
  workbench does not have: a tool manager with cutting data, the machine as an assembly with
  kinematics and collision check, assistants that propose operations. It builds on CAM: the job is
  a CAM job, the operations are Path operations, tools go both ways. None of it replaces the CAM
  workbench.
- *AI-written code – is that safe?* Frankly: that is how the code came to be. In return there are
  over a hundred test files and over a hundred GUI scenarios that run on every change, and I
  verify the paths on the machine. There are bugs anyway, and I want to know about them.
- *Which controls?* Siemens (840D/828D) with CYCLE800 and drilling cycles; for other controls the
  post-processor writes the rotary axes computed. If you have another control and want to test:
  please do.
- *Language?* Interface and help in English and German. The code and the developer documentation
  are in German – if you want to contribute code, say so and there will be an English entry
  point.
- *Telemetry?* None. The update check only contacts GitHub if you switch it on.
- *Reporting bugs?* Preferably as a GitHub issue with file and screenshot; here in the thread is
  fine too.

Thanks for reading – and for every bit of criticism.
Manuel

## BBCode zum Einfügen – Deutsch

Betreff: CAM-Addon für FreeCAD 1.1 – Werkzeugverwaltung, Maschinen-Baukasten, Drehen mit Y, 4-Achs-Bearbeitung – Meinungen und Tester gesucht

```
Hallo zusammen,

ich fräse und drehe an einer DMG CLX 550 mit Y-Achse und an ein paar 3-Achs-Fräsen und wollte den Weg vom Teil zum Programm in FreeCAD bequemer haben: weniger Dialoge, mehr Vorschläge, die man einfach annehmen kann. Daraus ist über die letzten Wochen ein Addon geworden, das ich hier vorstellen und zur Diskussion stellen möchte.

Vorweg, damit es keine Überraschung gibt: Entworfen und an der Maschine geprüft habe ich das Addon selbst; geschrieben ist der Code mit KI-Unterstützung nach meinen Vorgaben. Ich beurteile es über das Ergebnis am Werkstück, nicht über Codezeilen. Wer in den Code schaut, darf gern kritisieren – und wer die Dialoge nicht versteht, hat recht. Genau das will ich hören.

[b]Was drin ist[/b] (Stand heute, Version 0.209):

[list]
[*][b]Werkzeugverwaltung[/b] mit Schnittwerten je Werkstoffklasse und Einsatz (Schruppen, Vollnut, Schlichten, Bohren …), Haltern und Magazinen; Übergabe an FreeCAD CAM und zurück. Dazu eine vorgefüllte [b]Werkzeugkiste[/b] mit echten Herstellerdaten (Ceratizit, Gühring, Jongen, HOLEX, GARANT) und einem JSON-Import für eigene Reihen, der Doppeltes erkennt.
[*][b]Maschinen-Baukasten[/b]: Beispielmaschinen (3-Achs-Fräse, 5-Achs-Fräsen Tisch/Tisch, Kopf/Tisch, Kopf/Kopf, Drehmaschine mit Revolver und Y) als Assembly, eigene Maschinen aus einer Baugruppe, Verfahrwege und Anschläge, Kollisionsprüfung der Bahnen auf der Maschine.
[*][b]Assistent „Bearbeitung“[/b] für Teile im Quader: Flächen anklicken, das Addon schlägt Strategien vor (Planfräsen, Räumen, Kontur, Bohren, Gewinde, Entgraten, 3D-Schruppen und -Schlichten, Bleistift …), zeigt Zeit und Ergebnis vorab; ein Klick legt die Operationen an.
[*][b]4-Achs-Bearbeitung[/b] am runden Rohteil (Drehmaschine mit angetriebenen Werkzeugen oder Fräse mit Rundachse): Rundum schruppen und schlichten, Plan indexiert mit der Y-Achse, Querbohrungen, Nuten, Entgraten.
[*][b]3+2 und 5 Achsen simultan[/b]: geschwenkte Ebenen, Flankenfräsen, Entgraten im Raum, ein Vergleich von Werkzeugen und Anstellungen fürs 3D-Schlichten – gerechnet und in der Kollisionsprüfung geprüft, aber bisher nicht an einer echten 5-Achs-Maschine gefahren.
[*][b]Postprozessor[/b] für Siemens (CYCLE800, Bohrzyklen) und gerechnete Rundachsen, Programm je Maschine, Einrichtblatt.
[*]Oberfläche und Hilfe auf Deutsch und Englisch, Beispiele dabei.
[/list]

[b]Bilder:[/b] der Assistent „Bearbeitung“ mit Vorschlägen und Zeiten, Rundum schruppen an einer Welle, „Auf der Maschine prüfen“ an der 5-Achs-Fräse.

[img]https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/docs/bilder/forum/bearbeitung_vorschlaege.png[/img]
[img]https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/docs/bilder/forum/vierachs_welle.png[/img]
[img]https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/docs/bilder/forum/maschine_pruefen.png[/img]

[b]Was geprüft ist:[/b] 3-Achs- und 4-Achs-Kinematik, an meiner CLX mit Y und an 3-Achs-Fräsen. Alles mit 5 Achsen ist bisher gerechnet und simuliert. Es wird laufend weiter daran gearbeitet; jeder Schritt ist im Repo nachvollziehbar.

[b]Was ich mir wünsche:[/b]

[list=1]
[*]Meinungen – ist der Weg sinnvoll, was fehlt, was ist umständlich?
[*]Tester – wer eine 5-Achs-Maschine oder eine andere Steuerung hat und ein Beispielteil einmal durchspielen mag.
[*]Bediener-Feedback – Screenshot, ein Satz, was unklar war. Das reicht mir.
[/list]

[b]Installation:[/b] FreeCAD 1.1 (geprüft mit 1.1.4). Am einfachsten die eine Zeile für die Python-Konsole aus dem README des Repos; oder Addon-Manager → Einstellungen → eigenes Repository https://github.com/manuelhofer/freecad-cam-addon (Branch main) eintragen und dort installieren. Im Menü erscheint „CAM-Addon“, der erste Punkt „So geht’s“ führt durch.

[b]Vorab beantwortet:[/b]

[list]
[[i]]*Lizenz?[/i] LGPL 2.1 oder neuer, wie FreeCAD selbst.
[[i]]*Betriebssystem?[/i] Reines Python und PySide, keine Abhängigkeiten außer FreeCAD. Entwickelt und geprüft auf Linux; Windows und macOS sollten laufen, sind aber ungeprüft – Rückmeldung willkommen.
[[i]]*FreeCAD-Version?[/i] 1.1 (stabil) und der aktuelle Wochen-Build; 1.0 geht nicht (Assembly, CAM-API).
[[i]]*Warum ein Addon und nicht ins CAM-Modul?[/i] Weil es eigene Dinge mitbringt, die im Modul nicht da sind: Werkzeugverwaltung mit Schnittwerten, Maschine als Assembly mit Kinematik und Kollisionsprüfung, Assistenten, die Operationen vorschlagen. Es setzt auf CAM auf: Der Job ist ein CAM-Job, die Operationen sind Path-Operationen, Werkzeuge gehen in beide Richtungen. Nichts davon ersetzt das CAM-Modul.
[[i]]*KI-Code – ist das sicher?[/i] Offen gesagt: Der Code ist so entstanden. Dafür gibt es über hundert Prüfdateien und über hundert Oberflächen-Szenarien, die bei jeder Änderung laufen, und die Bahnen prüfe ich an der Maschine. Fehler gibt es trotzdem, und ich will sie wissen.
[[i]]*Welche Steuerungen?[/i] Siemens (840D/828D) mit CYCLE800 und Bohrzyklen; für andere Steuerungen schreibt der Postprozessor die Rundachsen gerechnet aus. Wer eine andere Steuerung hat und testen mag: gern.
[[i]]*Sprache?[/i] Oberfläche und Hilfe deutsch und englisch. Der Code und die Entwickler-Doku sind auf Deutsch – wer mitprogrammieren will, sagt Bescheid, dann gibt es einen englischen Einstieg.
[[i]]*Telemetrie?[/i] Keine. Die Update-Prüfung fragt GitHub nur, wenn man sie einschaltet.
[[i]]*Fehler melden?[/i] Am liebsten als Issue auf GitHub, mit Datei und Screenshot; hier im Thread geht auch.
[/list]

Danke fürs Lesen – und für jede Kritik. Manuel
```

## BBCode zum Einfügen – English

Subject: CAM add-on for FreeCAD 1.1 – tool manager, machine builder, turning with Y, 4-axis machining – looking for opinions and testers

```
Hi all,

I mill and turn on a DMG CLX 550 with Y axis and on a few 3-axis mills, and I wanted the way from part to program in FreeCAD to be more convenient: fewer dialogs, more proposals you can simply accept. Over the last weeks this has grown into an add-on that I would like to present here and put up for discussion.

Up front, so there is no surprise: I designed the add-on and verified it on the machine myself; the code was written with AI assistance, to my specification. I judge it by the result on the workpiece, not by lines of code. Anyone who looks at the code is welcome to criticise it – and anyone who does not understand a dialog is right. That is exactly what I want to hear.

[b]What is in it[/b] (as of today, version 0.209):

[list]
[*][b]Tool manager[/b] with cutting data per material class and application (roughing, slotting, finishing, drilling …), holders and magazines; hand-over to FreeCAD CAM and back. Plus a pre-filled [b]tool box[/b] with real manufacturer data (Ceratizit, Gühring, Jongen, HOLEX, GARANT) and a JSON import for your own series that recognises duplicates.
[*][b]Machine builder[/b]: example machines (3-axis mill, 5-axis mills table/table, head/table, head/head, lathe with turret and Y) as assemblies, your own machines from an assembly, travel limits and stops, collision check of the paths on the machine.
[*][b]“Machining” assistant[/b] for parts in a block: click faces, the add-on proposes strategies (facing, clearing, contour, drilling, threads, deburring, 3D roughing and finishing, pencil …), shows time and result in advance; one click creates the operations.
[*][b]4-axis machining[/b] on round stock (lathe with live tooling or mill with a rotary axis): all-round roughing and finishing, indexed facing with the Y axis, cross holes, slots, deburring.
[*][b]3+2 and 5-axis simultaneous[/b]: swivelled planes, flank milling, deburring in 3D, a comparison of tools and tilts for 3D finishing – computed and checked in the collision check, but not yet run on a real 5-axis machine.
[*][b]Post-processor[/b] for Siemens (CYCLE800, drilling cycles) and computed rotary axes, program per machine, setup sheet.
[*]Interface and help in English and German, examples included.
[/list]

[b]Pictures:[/b] the “Machining” assistant with proposals and times, all-round roughing on a shaft, “Check on machine” on the 5-axis mill.

[img]https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/docs/bilder/forum/bearbeitung_vorschlaege.png[/img]
[img]https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/docs/bilder/forum/vierachs_welle.png[/img]
[img]https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/docs/bilder/forum/maschine_pruefen.png[/img]

[b]What is verified:[/b] 3-axis and 4-axis kinematics, on my CLX with Y and on 3-axis mills. Everything with 5 axes is so far computed and simulated. Work continues; every step is traceable in the repository.

[b]What I am looking for:[/b]

[list=1]
[*]Opinions – does the approach make sense, what is missing, what is awkward?
[*]Testers – anyone with a 5-axis machine or another control who would run an example part once.
[*]Operator feedback – a screenshot and one sentence about what was unclear. That is enough.
[/list]

[b]Installation:[/b] FreeCAD 1.1 (verified with 1.1.4). Easiest is the one line for the Python console from the README of the repository; or Addon Manager → preferences → custom repository https://github.com/manuelhofer/freecad-cam-addon (branch main) and install from there. A menu “CAM-Addon” appears; its first entry “How it works” walks you through.

[b]Answered in advance:[/b]

[list]
[[i]]*Licence?[/i] LGPL 2.1 or later, like FreeCAD itself.
[[i]]*Operating system?[/i] Pure Python and PySide, no dependencies beyond FreeCAD. Developed and verified on Linux; Windows and macOS should work but are unverified – feedback welcome.
[[i]]*FreeCAD version?[/i] 1.1 (stable) and the current weekly build; 1.0 does not work (Assembly, CAM API).
[[i]]*Why an add-on and not part of the CAM workbench?[/i] Because it brings things of its own that the workbench does not have: a tool manager with cutting data, the machine as an assembly with kinematics and collision check, assistants that propose operations. It builds on CAM: the job is a CAM job, the operations are Path operations, tools go both ways. None of it replaces the CAM workbench.
[[i]]*AI-written code – is that safe?[/i] Frankly: that is how the code came to be. In return there are over a hundred test files and over a hundred GUI scenarios that run on every change, and I verify the paths on the machine. There are bugs anyway, and I want to know about them.
[[i]]*Which controls?[/i] Siemens (840D/828D) with CYCLE800 and drilling cycles; for other controls the post-processor writes the rotary axes computed. If you have another control and want to test: please do.
[[i]]*Language?[/i] Interface and help in English and German. The code and the developer documentation are in German – if you want to contribute code, say so and there will be an English entry point.
[[i]]*Telemetry?[/i] None. The update check only contacts GitHub if you switch it on.
[[i]]*Reporting bugs?[/i] Preferably as a GitHub issue with file and screenshot; here in the thread is fine too.
[/list]

Thanks for reading – and for every bit of criticism. Manuel
```
