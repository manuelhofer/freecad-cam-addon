# Vorstellung im FreeCAD-Forum – Entwurf

Manuel, 2026-10-10: „wir sollten das addon langsam mal ins freecad forum reinschreiben … den text
noch etwas verschönern sozusagen als aushängeschild … und nach meinungen dazu fragen oder nach
bedienern die eben die bedienung verbessern wollen“. Hier der Entwurf – deutsch für das deutsche
Unterforum, darunter englisch für das Unterforum „Path/CAM“. Vor dem Posten: Repo öffentlich
(T-005), die Installationszeile aus dem README einmal in einem frischen FreeCAD ausprobiert.

## Deutsch

**Betreff:** CAM-Addon für FreeCAD 1.1 – Werkzeugverwaltung, Maschinen-Baukasten, Drehen mit
Y, 4-Achs-Bearbeitung – Meinungen und Tester gesucht

Hallo zusammen,

ich fräse und drehe an einer DMG CLX 550 mit Y-Achse und an ein paar 3-Achs-Fräsen und wollte
den Weg vom Teil zum Programm in FreeCAD bequemer haben – weniger Dialoge, mehr Vorschläge,
die man einfach annehmen kann. Daraus ist ein Addon geworden, das ich hier gern vorstelle und
zur Diskussion stelle.

Zur Einordnung, bevor jemand den Code liest: Ich habe das Addon **erdacht und getestet, aber
nicht selbst programmiert** – der Code ist mit KI-Unterstützung entstanden („vibe coded“, wenn
man so will). Ich habe jede Funktion an meinen Maschinen und an Beispielteilen geprüft, aber ich
bin Zerspaner, kein Programmierer. Genau deshalb interessiert mich eure Meinung: zur Bedienung,
zu den Bahnen, zu dem, was fehlt.

Was drin ist (Stand heute, Version 0.209):

- **Werkzeugverwaltung** mit Schnittwerten je Werkstoffklasse und Einsatz (Schruppen, Vollnut,
  Schlichten, Bohren …), Haltern und Magazinen; Übergabe an FreeCAD CAM und zurück. Dazu eine
  vorgefüllte **Werkzeugkiste** mit echten Herstellerdaten (Ceratizit, Gühring, Jongen, HOLEX,
  GARANT) und einem JSON-Import, falls jemand eigene Reihen einpflegen will – mit Prüfung, ob
  ein Werkzeug schon da ist.
- **Maschinen-Baukasten**: Beispielmaschinen (3-Achs-Fräse, 5-Achs-Fräsen Tisch/Tisch, Kopf/Tisch,
  Kopf/Kopf, Drehmaschine mit Revolver und Y) als Assembly, eigene Maschinen aus einer
  Baugruppe, Verfahrwege und Anschläge, Kollisionsprüfung der Bahnen auf der Maschine.
- **Assistent „Bearbeitung“** für Teile im Quader: Flächen anklicken, das Addon schlägt
  Strategien vor (Planfräsen, Räumen, Kontur, Bohren, Gewinde, Entgraten, 3D-Schruppen und
  -Schlichten, Bleistift …), zeigt Zeit und Ergebnis vorab, und ein Klick legt die Operationen
  an.
- **4-Achs-Bearbeitung** am runden Rohteil (Drehmaschine mit angetriebenen Werkzeugen oder
  Fräse mit Rundachse): Rundum schruppen und schlichten, Plan indexiert mit der Y-Achse,
  Querbohrungen, Nuten, Entgraten.
- **3+2 und 5 Achsen simultan**: geschwenkte Ebenen, Flankenfräsen, Entgraten im Raum, ein
  Vergleich von Werkzeugen und Anstellungen fürs 3D-Schlichten – gerechnet und in der
  Kollisionsprüfung geprüft, aber **nicht an einer echten 5-Achs-Maschine gefahren**.
- **Postprozessor** für Siemens (CYCLE800, Bohrzyklen) und gerechnete Rundachsen, Programm je
  Maschine, Einrichtblatt.
- Deutsch und Englisch, Hilfe im Addon, Beispiele dabei.

Was ich ehrlich sagen muss: Geprüft ist das alles an **3-Achs- und 4-Achs-Kinematik** (meine
CLX mit Y). Alles mit 5 Achsen ist bisher nur gerechnet und simuliert. Es wird laufend weiter
daran gearbeitet; die Entwicklung ist im Repo nachvollziehbar.

Was ich mir von euch wünsche:

1. **Meinungen** – ist der Weg sinnvoll, was fehlt, was ist umständlich?
2. **Tester** – wer eine 5-Achs-Maschine oder eine andere Steuerung hat und ein Beispielteil
   einmal durchspielen mag.
3. **Bediener-Feedback** – wer die Dialoge nicht versteht, hat recht; genau das will ich hören.

Installation: FreeCAD 1.1 (getestet mit 1.1.4), Addon-Manager → eigenes Repo eintragen:
`https://github.com/manuelhofer/freecad-cam-addon` – oder das Repo nach `Mod/` klonen. Lizenz
LGPL 2.1+.

Danke fürs Lesen – und für jede Kritik.
Manuel

## English

**Subject:** CAM add-on for FreeCAD 1.1 – tool manager, machine builder, turning with Y, 4-axis
machining – looking for opinions and testers

Hi all,

I mill and turn on a DMG CLX 550 with Y axis and on a few 3-axis mills, and I wanted the way
from part to program in FreeCAD to be more convenient – fewer dialogs, more proposals you can
simply accept. The result is an add-on I would like to present here and put up for discussion.

For context, before anyone reads the code: I **designed and tested** the add-on, but did not
write it myself – the code was created with AI assistance (“vibe coded”, if you like). I checked
every function on my machines and on example parts, but I am a machinist, not a programmer.
That is exactly why I am interested in your opinion: on the handling, the paths, and what is
missing.

What is in it (as of today, version 0.209):

- **Tool manager** with cutting data per material class and application (roughing, slotting,
  finishing, drilling …), holders and magazines; hand-over to FreeCAD CAM and back. Plus a
  pre-filled **tool box** with real manufacturer data (Ceratizit, Gühring, Jongen, HOLEX,
  GARANT) and a JSON import for your own series – with a check whether a tool is already there.
- **Machine builder**: example machines (3-axis mill, 5-axis mills table/table, head/table,
  head/head, lathe with turret and Y) as assemblies, your own machines from an assembly, travel
  limits and stops, collision check of the paths on the machine.
- **“Machining” assistant** for parts in a block: click faces, the add-on proposes strategies
  (facing, clearing, contour, drilling, threads, deburring, 3D roughing and finishing, pencil …),
  shows time and result in advance, and one click creates the operations.
- **4-axis machining** on round stock (lathe with live tooling or mill with a rotary axis):
  all-round roughing and finishing, indexed facing with the Y axis, cross holes, slots,
  deburring.
- **3+2 and 5-axis simultaneous**: swivelled planes, flank milling, deburring in 3D, a comparison
  of tools and tilts for 3D finishing – computed and checked in the collision check, but **not
  run on a real 5-axis machine**.
- **Post-processor** for Siemens (CYCLE800, drilling cycles) and computed rotary axes, program
  per machine, setup sheet.
- German and English, help inside the add-on, examples included.

To be honest: all of this is verified on **3-axis and 4-axis kinematics** (my CLX with Y).
Everything with 5 axes is so far only computed and simulated. Work continues; the development is
traceable in the repository.

What I would like from you:

1. **Opinions** – does the approach make sense, what is missing, what is awkward?
2. **Testers** – anyone with a 5-axis machine or another control who would run an example part
   once.
3. **Operator feedback** – if you do not understand a dialog, you are right; that is exactly
   what I want to hear.

Installation: FreeCAD 1.1 (tested with 1.1.4), Addon Manager → custom repository:
`https://github.com/manuelhofer/freecad-cam-addon` – or clone the repository into `Mod/`.
Licence LGPL 2.1+.

Thanks for reading – and for every bit of criticism.
Manuel
