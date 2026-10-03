# Spezifikation W-005: Programm für jede Steuerung

Stand: P-2026-09-30-43. **Manuel hat am 2026-09-30 entschieden:** Option A –
„A sollte unsere option sein“. Davor: „Sollte keine Rolle spielen …. Es muss
ja für alle funktionieren“ (welche Steuerung er selbst hat), passend zur
Festlegung „keine bestimmte Maschine“ in `CHATSTART.md`. Danach (Abschnitte
6 und 7): **beide Wege** an der Drehmaschine – die Transformation der
Steuerung, wo die Maschine sie hat, sonst Punkt für Punkt fein und von der
Steuerung geglättet –, alle Optionen **als Haken, jede erklärt**, „so das man
es beim bedienen lernen kann“, die Einzelheiten hinter eigenen Fenstern oder
Hilfeseiten, damit nichts überladen wirkt. Die Einzelheiten sind Claudes
Vorschläge, zur Besprechung (Abschnitt 11).

**Entschieden am 2026-10-03** (Manuel: „das mit dem Postprozessor – ja, die Spezifikationen
nehmen“; dazu „ich möchte nicht den Postprozessor-Generator von FreeCAD nutzen … ich hätte gern
einen guten Postprozessor-Manager … außerdem funktioniert der mit 4 Achs nicht“ – FreeCADs
„Nachbearbeitung“ brach bei ihm in 1.1.4 mit „Post processor not identified“ ab): E1–E7 je die
Empfehlung (a). **Gebaut (P-2026-10-03-10):** S1 und S3 im eigenen Befehl „Programm schreiben …“
statt über FreeCADs Postprozessor-Liste (E3 entfällt damit vorerst) – Abschnitt 12.

Grundlage: [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
(Maschine, Betriebsarten, Aufnahmen), [spezifikation_vierachs.md](spezifikation_vierachs.md)
(Rundum-Operationen, G93, Postprozessoren von FreeCAD geprüft: P-2026-09-30-36).

## 1. Wozu

Die Postprozessoren von FreeCAD sind für Fräsmaschinen gebaut. Unsere
Rundum-Operationen laufen aber auch an Drehmaschinen mit C-Achse und
angetriebenem Werkzeug, und dort erwartet jede Steuerung anderes:

- **X im Durchmesser** – Siemens, Fanuc und Haas zählen X an der
  Drehmaschine von Haus aus als Durchmesser; unsere Bahn rechnet den Radius.
- **Drehzahl des angetriebenen Werkzeugs** – `M3 S…` dreht an der
  Drehmaschine die Hauptspindel, also das Teil. Haas schreibt
  `M133 P<Drehzahl>` (aus: `M135`), Siemens spricht die Spindel mit ihrer
  Nummer an (`M3=3 S3=…` oder `SETMS(3)`), bei Fanuc legt der
  Maschinenhersteller die M-Befehle fest.
- **C-Achse ein und aus** – Haas `M154`/`M155`, Siemens positioniert die
  Hauptspindel (`SPOS`), Fanuc: M-Befehl des Herstellers.
- **Vorschub** – G93 (1 ÷ Zeit) gibt es an Fräsmaschinen fast überall, an
  Drehmaschinen nicht immer. Bei Fanuc-Drehmaschinen im G-Code-System A ist
  **G94 ein Plandrehzyklus**, Vorschub je Minute heißt dort **G98**.
- **Werkzeugwechsel** – an der Drehmaschine `T0101` (Fanuc) bzw. `T1 D1`
  (Siemens) statt `T1 M6`.

Mantel- und Stirnfräsen mit Transformation (Fanuc G07.1/G12.1, Siemens
TRACYL/TRANSMIT) gibt es auch; unsere Operationen fahren X, Z und C direkt
(Abschnitt 6).

## 2. Was es schon gibt

- **Unser Maschinenmodell** (W-001) kennt die Betriebsarten – Hauptspindel
  S1, C1 (Positionieren der Hauptspindel), Werkzeugantrieb S3 – und je
  Aufnahme die Spindel, die das Werkzeug dreht. Daraus weiß der
  Postprozessor, ob ein Werkzeug angetrieben ist, welche Nummer sein Antrieb
  hat (S3 → 3) und dass C die Hauptspindel positioniert.
- **Der Job merkt sich seine Maschine** (Pfad der Datei, D-20).
- **Wochen-Build:** Die CAM-Maschinendefinition hat einen Postprozessor mit
  eigenen Eigenschaften, Ausgabeoptionen und einen Umbruch für Rundachsen
  (fortlaufend, 0–360°, neu nullen). Addons melden Postprozessoren über
  `package.xml` (Inhalt „Postprocessor“) oder `Path.Preferences.addAddonPostPath`
  an. **1.1.x** kennt nur den Makro-Ordner und FreeCADs eigene Ordner.

## 3. Die Steuerung an der Maschine

In **„Maschine bearbeiten“** eine Zeile **Steuerung** mit Auswahl:
LinuxCNC, Siemens 840D, Fanuc, Haas, Mach3/Mach4, „Eigene“. Je Wahl sind die
**Befehle** vorbelegt; jeder lässt sich ändern, weil manches der
Maschinenhersteller festlegt. Ein gelber Satz sagt das dazu.

| Befehl | LinuxCNC | Siemens 840D | Fanuc | Haas |
|---|---|---|---|---|
| Werkzeugwechsel Fräsen | `T1 M6` | `T1 M6` | `T1 M6` | `T1 M6` |
| Werkzeugwechsel Drehen | `T1 M6` | `T1 D1` | `T0101` | `T101` |
| Hauptspindel | `M3 S…` | `M3 S…` | `M3 S…` | `M3 S…` |
| Angetriebenes Werkzeug | `M3 $1 S…` | `M3=3 S3=…` | vom Hersteller | `M133 P…` |
| … aus | `M5 $1` | `M5=3` | vom Hersteller | `M135` |
| C-Achse ein / aus | – | `SPOS=0` / `M5` | vom Hersteller | `M154` / `M155` |
| X an der Drehmaschine | Radius (`G8`) | Durchmesser | Durchmesser | Durchmesser |
| Vorschub 1 ÷ Zeit | `G93` | `G93` | `G93` | `G93` |
| Vorschub je Minute | `G94` | `G94` | `G94` (Fräsen), `G98` (Drehen) | `G94` (Fräsen), `G98` (Drehen) |

Die Nummer des Antriebs (hier 3) kommt aus der Maschine. Werte, die nicht
aus einer Herstelleranleitung nachgeprüft sind, stehen in der Tabelle der
Prüfungen als „vorbelegt, bitte vergleichen“ und im Fenster mit demselben
Hinweis.

## 4. Der Postprozessor des Addons

- Heißt **„camaddon“** und steht in der Liste der Postprozessoren des Jobs.
  Der Kern liegt in `camaddon/postprozessor.py` (ohne Oberfläche, prüfbar),
  eine dünne Datei `posts/camaddon_post.py` meldet ihn bei FreeCAD an.
- Er schreibt **alle** Operationen des Jobs, nicht nur unsere: G0, G1, G2,
  G3, Bohrzyklen, Werkzeugwechsel, Spindel, Kühlmittel, Kommentare – mit den
  Befehlen der Steuerung. Für jedes Werkzeug fragt er die Maschine, ob es
  angetrieben ist.
- Unsere Rundum-Bahnen: X als Durchmesser, wo die Steuerung es so zählt;
  vor der Bahn C-Achse ein, danach aus; G93 … Vorschub je Minute mit dem
  Befehl der Steuerung; F in jedem Satz.
- **Ohne Steuerung am Job** schreibt er wie LinuxCNC – dann ist nichts
  schlechter als heute.
- Programmkopf und -fuß bleiben frei eintragbar wie bei FreeCAD.

## 5. Vorschub ohne G93

Kennt eine Steuerung G93 in dieser Betriebsart nicht, rechnet der
Postprozessor F so, dass die Zeit stimmt: F = √(ΔX² + ΔZ² + ΔC²) ÷ Zeit, mit
C in Grad – so zählen Steuerungen wie Fanuc den Weg, wenn Linear- und
Rundachsen zusammen fahren. Die Zeit kommt aus unserer Bahn (dieselbe wie
für G93). Das ist E5 in Abschnitt 11.

## 6. Zwei Wege an der Drehmaschine

Manuel (2026-09-30): „ob das irgendwie geht, dass man sagt, man hat ein
Werkzeug, das 90 Grad zur Maschinen-Z steht … und dreht dann die C-Achse …
oder ob das wirklich in Einzelsätzen mit C-Angabe gemacht werden muss … oder
eben beide Optionen“. Es gibt beide:

- **Transformation (die Steuerung rechnet C):** Das Programm beschreibt die
  Bahn, als wäre das Teil abgewickelt bzw. als gäbe es eine Y-Achse; die
  Steuerung macht daraus C-Bewegungen. Am Mantel die
  **Zylinder-Transformation** (Siemens `TRACYL`, Fanuc `G07.1`/`G107`,
  Haas `G107`), an der Stirn die **Polar-Transformation** (Siemens
  `TRANSMIT`, Fanuc `G12.1`/`G112`, Haas `G112`) – so fräst man mit C statt
  mit Y. Kurze Programme, die Steuerung führt den Vorschub selbst. Aber: Die
  Zylinder-Transformation rechnet auf **einem** Radius; sie passt zu Nuten,
  Taschen und Beschriftungen auf einem Zylinder, zu „Linien längs“ und „Plan
  indexiert“ (V4c) – nicht zu einer Fläche, deren Radius sich ständig ändert
  wie bei „Rundum schruppen“. Und sie ist bei vielen Maschinen eine Option,
  die gekauft sein muss.
- **Punkt für Punkt (heute):** Jeder Satz hat X, Z und C; der Punktabstand
  folgt der Toleranz (Schlichten 0,005 mm), der Vorschub steht mit G93 bzw.
  wie in Abschnitt 5. Das geht an jeder Maschine, die X, Z und C gemeinsam
  fahren kann – auch ohne Transformation. Damit die vielen kurzen Sätze nicht
  ruckeln, schaltet der Programmkopf die **Vorausschau und das Glätten** der
  Steuerung ein (Abschnitt 7).

An der Maschine sagt ein Haken je Transformation, ob sie da ist. Die Operation
nimmt die Transformation, wo sie passt und die Maschine sie hat, sonst Punkt
für Punkt – und sagt, was sie genommen hat („Deine Maschine hat keine
Zylinder-Transformation – gefräst wird Punkt für Punkt auf 0,005 mm, die
Steuerung glättet“).

## 7. Vorausschau und Glätten

Bei tausenden kurzen Sätzen bremst eine Steuerung ohne Vorausschau an jedem
Satzende. Jede Steuerung hat dafür Befehle; sie kommen als **Haken** an der
Maschine, **jeder mit einem Satz dazu, was er tut und wofür er gut ist**, und
einem „?“, das die Hilfeseite der Steuerung an dieser Stelle öffnet. Beispiel
Siemens 840D (Manuel, 2026-09-30, aus dem Programmierhandbuch
PGsl_1015_de_de-DE):

- ☑ **`G64` – Bahnsteuerbetrieb:** schaltet die Vorausschau (LookAhead) ein;
  die Steuerung plant Beschleunigen und Bremsen über mehrere Sätze, statt an
  jedem Satzübergang abzubremsen.
- ☑ **`G642` – Überschleifen mit Toleranz:** verschleift die Satzübergänge
  innerhalb einer Toleranz (Feld daneben, vorbelegt mit der Toleranz der
  Bahn); für CAM-Bahnen die übliche Wahl. (`G641` verschleift über einen Weg,
  `ADIS`.)
- ☐ **`COMPCAD` / `COMPSURF` / `COMPCURV` – Satzkompressor:** macht aus vielen
  kleinen G1-Sätzen intern glatte Bahnabschnitte; bei langen CAM-Programmen
  wichtig. Siemens empfiehlt dazu `G642` und `SOFT`.
- ☑ **`SOFT` – ruckbegrenzt beschleunigen:** Die Achsen werden bei
  Richtungswechseln nicht hart beschleunigt.

Vorbelegt ist, was bei der Steuerung üblich ist; was nicht jede Maschine hat
(Satzkompressor), ist aus und sagt, dass es eine Option sein kann. Für Fanuc
(etwa AI-Konturregelung `G05.1 Q1`, Vorausschau `G08 P1`), Haas (`G187`),
LinuxCNC (`G64 P… Q…`) und Mach3/4 folgt dasselbe, jeweils aus der Anleitung
der Steuerung nachgeprüft (Quelle im Hilfetext).

## 8. Einfach bedienen

- Im Fenster „Maschine bearbeiten“ steht nur **eine Zeile**: Steuerung
  (Auswahl) und daneben „Einstellungen …“. Alles Weitere öffnet sich in einem
  eigenen Fenster, in Gruppen: Programm (Kopf, Ende, Werkzeugwechsel),
  Spindeln (Haupt, angetrieben), C-Achse, Vorschub, Transformationen,
  Vorausschau und Glätten.
- Jede Zeile hat einen kurzen Namen, einen Satz Erklärung und ein „?“ zur
  Hilfeseite der Steuerung (`help/de/steuerung_siemens.html` …), die erklärt,
  **wann** man es braucht und was es kostet – so lernt man beim Bedienen.
- Die Vorbelegung ist so, dass man nichts ändern muss, um anzufangen; was
  der Maschinenhersteller festlegt, ist gelb markiert: „bitte mit der
  Anleitung deiner Maschine vergleichen“.
- Unten im Fenster eine Vorschau: die ersten Sätze des Programms mit diesen
  Einstellungen.

## 9. Prüfen

- Je Voreinstellung eine **Musterausgabe**: derselbe Job (Welle an der
  Beispiel-Drehmaschine, Rundum schruppen mit angetriebenem Werkzeug; eine
  Tasche an der 3-Achs-Fräse) ergibt Satz für Satz das erwartete Programm
  (`tests/daten/programm_*.nc`).
- Das Prüffenster sagt, welcher Postprozessor und welche Steuerung gelten,
  und warnt, wenn der Job einen anderen Postprozessor nimmt, obwohl die
  Maschine eine Steuerung hat.

## 10. Stufen

- **S1** – Postprozessor „camaddon“ mit dem Verhalten von LinuxCNC (Fräsen),
  angemeldet in 1.1.x und im Wochen-Build. Prüfung: gleiche Sätze wie
  `linuxcnc_post` für einen 3-Achs-Job und für Rundum schruppen.
- **S2** – Steuerung und Befehle an der Maschine („Maschine bearbeiten“),
  der Job bekommt sie beim Anlegen (4-Achs-Assistent) und beim Prüfen auf der
  Maschine. Szenario.
- **S3** – Drehmaschine: Durchmesser, angetriebenes Werkzeug, C-Achse ein
  und aus, Werkzeugwechsel, Vorschub je Minute je Steuerung; Musterausgaben
  für LinuxCNC, Siemens, Fanuc, Haas.
- **S4** – Vorausschau und Glätten als Haken mit Erklärung (Abschnitt 7),
  das Fenster „Einstellungen …“ mit Gruppen und Vorschau (Abschnitt 8),
  Hilfeseite je Steuerung.
- **S5** – Vorschub ohne G93 (Abschnitt 5).
- **S6** – Transformationen: Haken an der Maschine; Operationen, die auf
  einem Radius fräsen, schreiben dann `TRACYL`/`G07.1`/`G107` bzw.
  `TRANSMIT`/`G12.1`/`G112` (mit V4c).
- **S7** – Wochen-Build: „An CAM übergeben“ trägt Postprozessor und Steuerung
  in die CAM-Maschine ein.
- **S8** – Hilfe, Beispiel-Drehmaschine mit Steuerung, Szenario mit dem
  fertigen Programm; Manuels Testteil (Loft, D-Profil) als Prüfteil.

## 11. Entscheidungen (zur Besprechung)

- **E1 – Welche Steuerungen zuerst?**
  (a) LinuxCNC, Siemens 840D, Fanuc, Haas, Mach3/Mach4 und „Eigene“ –
  **Empfehlung**, die häufigsten, alles Weitere über „Eigene“;
  (b) dazu Heidenhain (DIN/ISO), Mazak, Okuma – mehr Arbeit, jede braucht
  Musterausgaben; (c) nur „Eigene“ mit leeren Feldern – schnell, aber jeder
  muss alles selbst wissen.
- **E2 – Wo steht die Steuerung?**
  (a) an der Maschine, der Job bekommt beim Verbinden eine Kopie –
  **Empfehlung**: Das Programm lässt sich auch schreiben, wenn die
  Maschinendatei gerade nicht offen ist; (b) nur am Job – jeder Job einzeln
  einstellen; (c) der Postprozessor öffnet jedes Mal die Maschinendatei –
  langsam, und ohne die Datei geht nichts.
- **E3 – Anmelden in FreeCAD 1.1.x:**
  (a) beim Start den Suchpfad von CAM um den Ordner des Addons erweitern –
  **Empfehlung**, es wird nichts kopiert; (b) die Datei in den Makro-Ordner
  kopieren – sichtbar für den Benutzer, bleibt beim Entfernen des Addons
  liegen.
- **E4 – X an der Drehmaschine:**
  (a) wie die Steuerung von Haus aus zählt (Siemens, Fanuc, Haas:
  Durchmesser; LinuxCNC: wie eingestellt) – **Empfehlung**, der Bediener
  liest, was er gewohnt ist; (b) immer Radius und im Programm umschalten
  (`DIAMOF`, `G8`) – ein Befehl mehr, der vergessen werden kann.
  Manuel (2026-09-30) zum Umschalter Ø/Radius an der Maschine: „Ja mit
  Umschalter wichtig ist ja nur was dann beim Postprozess raus kommt“. Die
  Maschine merkt es sich jetzt je Linearachse (P-2026-09-30-54,
  `maschine.x_im_durchmesser`); der Postprozessor schreibt X danach – das
  passt zu (a).
- **Achsnamen mit Nummer** (Manuel, 2026-09-30, an seiner Maschine: C4/S4 die
  Hauptspindel drehen und positionieren, C1/S1 die angetriebenen Werkzeuge): „es
  muss die zahl schon mit bei sonst weis die maschine ja nicht welches c
  verfahren wird“. Der Postprozessor schreibt also den ganzen NC-Namen aus
  „Maschine bearbeiten“ (C4, nicht C) – bei Siemens mit „=“ (`C4=90`), wie dort
  jede Adresse mit Zahl; an seiner Steuerung nachprüfen. Die Bahn aus CAM kennt
  nur A, B, C; welche C-Achse gemeint ist, sagt die Maschine (die Rundachse,
  die das Teil dreht). `maschine.programmname` lässt die Nummer weg – das bleibt
  für CAM so.
- **E5 – Steuerungen ohne G93:**
  (a) Vorschub wie in Abschnitt 5 – **Empfehlung**, dann geht es auch dort;
  (b) nur Steuerungen mit G93 – einfacher, aber nicht für alle.
- **E6 – Reihenfolge der zwei Wege (Abschnitt 6):**
  (a) erst Punkt für Punkt mit Vorausschau und Glätten (S1–S5), dann die
  Transformationen zusammen mit V4c (S6) – **Empfehlung**: Punkt für Punkt
  geht für jede Fläche und jede Maschine mit C, die Transformation nur für
  Flächen auf einem Radius; (b) erst die Transformationen – kürzere Programme,
  aber „Rundum schruppen“ bleibt ohne.
- **E7 – Glätten vorbelegen:**
  (a) was bei der Steuerung üblich ist, an (Siemens `G64`, `G642` mit der
  Toleranz der Bahn, `SOFT`), Optionen wie der Satzkompressor aus –
  **Empfehlung**; (b) alles aus, jeder schaltet selbst ein – nichts
  passiert ungefragt, aber ohne Glätten ruckelt es; (c) alles an – am
  schnellsten, aber eine Maschine ohne die Option bleibt mit Alarm stehen.

## 12. Gebaut

- **P-2026-10-03-10 – „Programm schreiben …“ (S1, S3, Teile von S2 und S4):**
  `camaddon/postprozessor.py` (ohne Oberfläche: `Steuerung` je Steuerung mit allen Befehlen,
  `STEUERUNGEN` LinuxCNC, Siemens 840D, Fanuc, Haas, Mach3/Mach4; `Maschineninfo` – Drehmaschine,
  X im Durchmesser, NC-Name der Rundachse, angetriebene Plätze → Nummer des Antriebs – aus der
  Maschine, die sich der Job gemerkt hat; `programm()` aus `abschnitte(job)`), das Fenster
  `camaddon/gui_programm.py` (Job, Maschine, Steuerung, „Befehle …“ zum Ändern mit
  Zurücksetzen, gelb was der Hersteller festlegt, Vorschau der ersten 300 Sätze, Datei,
  Speichern), Befehl in Werkzeugleiste und Menü, Hilfe `programm.html`.
  - Die Steuerung merkt sich der Job (`CamAddonSteuerung`) und je Maschinendatei der
    Parameter – E2 (a) noch nicht an der Maschine selbst („Maschine bearbeiten“: S2).
  - Siemens: `M{n}={m} S{n}={s}` für den Antrieb (die Spindelnummer vorn: `M3=3` dreht Spindel
    3 rechts; die Tabelle in Abschnitt 3 hatte „M5=3“ fürs Ausschalten – richtig ist `M3=5`),
    C-Achse `SPOS=0` / `SPCOF`, Rundachse mit NC-Namen und „=“ (`C1=90.000`).
  - Fanuc: angetriebenes Werkzeug und C-Achse legt der Hersteller fest – vorbelegt `M3 S…`
    bzw. leer, im Fenster gelb, im Programm ein Kommentar.
  - Noch nicht: Vorausschau und Glätten als Haken (S4), Vorschub ohne G93 (S5),
    Transformationen (S6), Wochen-Build-Eintrag (S7), Musterausgaben als Dateien
    (`tests/daten/programm_*.nc`) – die Prüfung `tests/test_postprozessor.py` prüft die Sätze
    direkt.
- **P-2026-10-03-19 – zum Wechselpunkt:** Vor jedem Werkzeugwechsel und am Ende fährt das
  Programm zum Wechselpunkt der Maschine (Manuel, 2026-10-03: „der Werkzeugwechselpunkt sollte
  MKS, also nicht WKS sein … oder es sollte wechselbar sein“). Er steht je Linearachse an der
  Maschine (Home/Wechsel, Spezifikation Simulation 13; jetzt auch gesammelt unter „Home und
  Werkzeugwechsel“), der Bezug an der Maschine (`WechselBezug`: MKS ab Werk, oder WKS). Die
  Befehle `wechselpunkt_mks` (LinuxCNC, Fanuc, Haas, Mach `G53 G0 {achsen}`, Siemens
  `G0 SUPA D0 {achsen}` – D0: der Punkt gilt für den Werkzeugträger) und `wechselpunkt_wks`
  (`G0 {achsen}`) sind unter „Befehle …“ änderbar; zuerst allein die Achse, die das Werkzeug
  wegzieht (Drehmaschine X, sonst Z), X im Durchmesser wie im Programm. In WKS fahren nur die
  Achsen mit eigenem Wechselpunkt, in MKS gilt ohne ihn der Home-Punkt.
- **P-2026-10-03-25 – Hauptspindel und angetriebene Werkzeuge, die Maschine zur Wahl:** Manuel
  (2026-10-03): „ich habe eine Maschine erstellt, Drehmaschine mit Y-Achse … wenn angetriebene
  Werkzeuge, muss es ein S und ein C für die Hauptspindel geben und ein S und ein C für die
  angetriebenen Werkzeuge … dann muss natürlich der Postprozessor wissen, welche Achse was macht
  – in meinem Beispiel: C4 muss sich positionieren, das ist die Hauptspindel, und S1 muss die
  Drehzahl anmachen“ (seine Maschine: S4/C4 die Hauptspindel, S1/C1 die angetriebenen Werkzeuge,
  Abschnitt 11). Gebaut:
  - `maschine.spindeln()`: der Antrieb ist eine Spindel, an der eine Werkzeugaufnahme hängt
    („Angetrieben von“), die Hauptspindel die erste andere (lieber mit C-Achse am selben
    Gelenk); die C-Achse einer Spindel ist die Betriebsart „Positionieren“ an ihrem Gelenk.
  - `Maschineninfo.hauptspindel` (Nummer), `hauptspindel_name`, `antrieb_c`; die Rundachse der
    Bahn ist die C-Achse der Hauptspindel – die C-Achse eines Antriebs richtet nur das Werkzeug
    aus und ist nie die Rundachse (auch nicht in der Übergabe an FreeCADs Maschinendefinition:
    `export.antrieb_c`). In der Kinematik stört sie nicht: Ihr Gelenk liegt nicht auf dem Weg
    vom Werkzeug zum Teil.
  - Platzhalter `{h}` (Nummer der Hauptspindel, ohne bekannte 1): Siemens „C-Achse ein“
    `SPOS[{h}]=0`, „aus“ `SPCOF({h})` (bis -24 `SPOS=0` / `SPCOF`, die Masterspindel). Mit
    Manuels Maschine: `SPOS[4]=0`, `M1=3 S1=…`, `C4=…`, `M1=5`, `SPCOF(4)`.
  - Die Beispiel-Drehmaschine hat am Werkzeugantrieb jetzt auch die C-Achse (S3/C3); „Neue
    Maschine …“ fragt bei der Drehmaschine nach den Nummern der Spindeln (vorbelegt 1 und 3;
    Manuel trägt 4 und 1 ein).
  - „Programm schreiben“: die Maschine zur Wahl – jede offene, auch ungespeichert, und die
    gemerkten (`postprozessor.maschinen_zur_wahl`); vorgewählt die des Jobs, sonst die erste
    offene; gewählt mit Datei merkt sich der Job sie. Grund: Manuels neue Drehmaschine war
    offen, aber nicht gespeichert – das Fenster schrieb „Keine Maschine am Job“ und das
    Programm wie für eine Fräse (`M3 S5570`, `C-1.000`).
  - Hilfe „Programm schreiben“: Abschnitt „Hauptspindel und angetriebene Werkzeuge“, dazu „vor
    dem ersten Lauf in der Simulation der Steuerung ansehen“ (entschieden 2026-10-03, Abschnitt
    11 „Siemens-Befehle“).
  - Nicht nachgeprüft an einer echten Steuerung: `SPOS[n]`/`SPCOF(n)` nach dem
    Siemens-Programmierhandbuch; Manuel programmiert an der Maschine mit ShopTurn.
