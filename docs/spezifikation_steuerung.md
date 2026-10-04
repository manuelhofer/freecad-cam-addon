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
- **E8 – Bohrzyklen an Siemens (2026-10-03 Nacht):** Heute schreibt der
  Postprozessor für jede Steuerung FreeCADs Bohrzyklen als `G81`/`G82`/`G83`/`G73`/`G85` mit
  X, Y, Z, R (und Q, P). Eine 840D liest im SINUMERIK-Sprachmodus `G290` – dem Standard – keine
  G81 ff.; die gibt es nur im ISO-Sprachmodus `G291` (Grundlagen 03/2010, S. 535, Gruppe 47;
  in der Liste der G-Funktionen fehlt G81). Ein Siemens-Programm mit Bohren bliebe also mit
  Alarm stehen. Vorschlag – je Bohrung über dem Loch (`G0 X… Y…`), dann der Zyklus
  (Arbeitsvorbereitung 10/2015, S. 651–663):
  - `G81` → `CYCLE81(RTP, RFP, 0, DP)`, `G82` → `CYCLE82(RTP, RFP, 0, DP, , DTB)`;
  - `G83` → `CYCLE83(RTP, RFP, 0, DP, , FDEP, , 0, 0, 0, 1, 1)` – Entspanen (VARI 1), erste
    Tiefe FDEP = R − Q, gleiche Zustellung (Degression 0); `G73` ebenso mit VARI 0
    (Spänebrechen);
  - `G85` → `CYCLE85(RTP, RFP, 0, DP, , 0, F, F)` – hinein und heraus im Vorschub;
  - dabei RTP (Rückzugsebene) = die Höhe vor dem Zyklus bei G98, R bei G99; RFP (Bezugspunkt) = R;
    Sicherheitsabstand SDIS 0 (R enthält ihn schon); DP = Z absolut; F vorher im Satz `F…`.
  Die Befehle stehen unter „Befehle …“ zum Ändern wie die anderen. **Entschieden** durch
  Manuels Regel vom 2026-10-03 abends („Die Befehle bleiben nach dem Siemens-Handbuch; vor dem
  ersten Lauf das Programm in der Simulation der Steuerung ansehen“) – G81 ff. stehen dort nur im
  ISO-Teil. **Gebaut (P-2026-10-03-53):** `Steuerung.bohren`, `bohren_verweilen`, `tiefbohren`,
  `spaenebrechen`, `reiben` (leer: der G-Code bleibt – LinuxCNC, Fanuc, Haas, Mach); bei Siemens
  vorbelegt wie oben, G80/G98/G99 entfallen dort; an der Drehmaschine bleibt es bei G81 ff.
  (CYCLE83 bohrte ohne `_AXN` entlang Z). Gruppe „Bohrzyklen“ im Fenster, Hilfe „Programm
  schreiben“ (Anker `bohren`). Dazu: `G0 … F0` (aus FreeCADs Bohren) schreibt der Postprozessor
  ohne F – modal hielte F0 einen folgenden G1 ohne F an. Seit P-2026-10-04-15 schreibt er einen
  Eilgang, der wörtlich gleich dem Satz davor ist, nicht noch einmal (absolut: nichts zu fahren),
  und am Ende keinen Satz des Programmfußes, der gleich dem davor ist (`M5` nach `M5`).

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
- **P-2026-10-03-26 – SUPA nachgeprüft, F_HOME und G75 als Weg zum Wechselpunkt:** Manuel
  (2026-10-03, mit dem Link auf das Programmierhandbuch Arbeitsvorbereitung 10/2015): „das mit
  dem SUPA … ist das noch aktuell?“ – und „aber was ist mit F_HOME?“. Nachgelesen:
  - Arbeitsvorbereitung 10/2015 (840D sl/828D), S. 109, Werkzeugwechselroutine:
    `G0 G40 G60 G90 SUPA X450 Y300 Z300 D0` – „Werkzeugwechselpunkt anfahren“; S. 766 SUPA in
    der Befehlsliste, nichts davon, dass es abgelöst wäre. Grundlagen 03/2010, S. 382: G53 <
    G153 (dazu Basisframe) < SUPA (dazu DRF, überlagerte Bewegung, externe NV, PRESET).
    Dazu S. 513: `SPCON(2)`, `SPOS[2]=…` – die Schreibweise aus P-2026-10-03-25 stimmt.
  - G75 „Festpunkt anfahren“ (Grundlagen 03/2010, S. 406–408): `G75 X0 Z0 FP=1` fährt auf
    Festpunkte aus MD30600 (MKS); die Werte hinter den Achsen zählen nicht; nicht mit
    Radiuskorrektur oder aktiver Transformation.
  - F_HOME steht in keinem der beiden Handbücher: der ShopTurn-Zyklus, der vor jedem
    Werkzeugwechsel zum Werkzeugwechselpunkt fährt (Forum Practical Machinist, 2023, eine
    Y-Drehmaschine mit ShopTurn: der Zyklus ist nicht einsehbar; die Hersteller-Haken in
    CUST_TECHCYC.SPF laufen nur in ShopTurn-Programmen, nicht in G-Code; der Fragende ruft
    F_HOME am Anfang eines G-Code-Programms aus Fusion 360 selbst auf und schreibt vor M6
    `G0 SUPA Y0 D0`). Ob F_HOME ohne ShopTurn-Programmkopf den eingestellten Punkt kennt, ist
    nicht nachgeprüft.
  - Gebaut: Ein Befehl „Zum Wechselpunkt“ ohne `{achsen}` (F_HOME, M-Befehle) steht einmal vor
    jedem Werkzeugwechsel und am Ende – auch ohne Wechselpunkt an der Maschine (bis -25 stand er
    zweimal da: erst X allein, dann alle). Vorbelegt bleibt `G0 SUPA D0 {achsen}`: Es geht an
    jeder 840D, auch ohne ShopTurn. Hilfe „Programm schreiben“ nennt beide anderen Wege.
- **P-2026-10-03-27 – die Einstellungen als Haken, Glätten (S4), Vorschub ohne G93 (S5):**
  Manuel (2026-10-03): „ja, mach das alles mal, vor allem die Optionen im Postprozessor besser
  beschreiben, darstellen, mit Haken machen“. Gebaut, nach Abschnitt 7 und 8 (aber im Fenster
  „Programm schreiben“, je Steuerung gemerkt – S2, an der Maschine, bleibt offen):
  - Links die Einstellungen in Gruppen (Programm, Werkzeugwechsel, Spindel und Kühlung, C-Achse,
    Vorschub, Vorausschau und Glätten), jede mit „?“ an ihre Stelle der Hilfe (`kopfzeile` mit
    Anker); jeder Haken und jeder Befehl mit einem Satz Erklärung, fett geändert, gelb vom
    Hersteller; gezeigt nur, was an der gewählten Maschine gilt; ist ein Haken aus, sind die
    Befehle darunter grau. Rechts die Vorschau. „Zum Wechselpunkt (MKS)“ als Auswahl mit
    freiem Text (Siemens: SUPA, F_HOME, G75).
  - Haken in `Steuerung`: `kommentare`, `satznummern` (N10 … nicht vor %, O-Nummer, Kommentar),
    `kuehlung`, `wechselpunkt`, `c_achse`, `g93`; dazu `glaetten` (Kennungen) und `toleranz`
    (0,001 … 1 mm). `gueltige_aenderungen` nimmt nur, was passt.
  - Glätten je Steuerung (`Glaetten`): Siemens G64, G642, CTOL={toleranz}, SOFT an, COMPCAD aus
    (Option – gelb im Fenster und als Hinweis über der Vorschau); LinuxCNC `G64 P Q` an;
    Mach `G64` an; Fanuc `G08 P1`, `G05.1 Q1` aus (Optionen, nicht nachgeprüft); Haas
    `G187 P3` aus. Siemens nachgelesen: Arbeitsvorbereitung 10/2015, S. 470–471 (CTOL), dazu die
    Befehlsliste. Das `G64` stand bis -26 fest im Siemens-Kopf.
  - S5: ohne G93 F in mm/min = Weg ÷ Zeit des Satzes, der Weg aus X, Y, Z, A, B, C (Rundachsen
    in Grad, X als Radius, ein Bogen als Sehne); G93 und G94 entfallen dann. Geprüft: X42 Z3 C0 →
    X38 Z0 C90 in ⅓ min gibt F270.416.
- **P-2026-10-04-38 – Sprungmarken und Kopf (D-4):** Manuel (2026-10-04): „um es später im
  Programm leichter zu finden … zumindest (für Siemens) Sprungpunkte setzen … die lassen sich ja
  bei Siemens immer mit GOTO anspringen … oben im Kommentar des Programms schon gut Infos, was man
  anspringen kann“; in den Kopf „Werkzeuge mit deren Ausspannlängen zum Halter, Halter … wenn's
  knapp wird, muss darauf hingewiesen werden“; jede Marke ein vollständiger Einstieg („Ja, jede
  Marke vollständig“).
  - Haken „Sprungmarke je Bearbeitung“ (`marken`, an) und der Befehl „Sprungmarke“ (`marke`):
    Siemens `{marke}:` (Name aus der Bearbeitung: groß, Umlaute ausgeschrieben, nur Buchstaben,
    Ziffern und „_“, zwei Buchstaben vorn, höchstens 32 Zeichen, eindeutig – `markenname`), Fanuc
    und Haas `N{n}` für die Satzsuche, LinuxCNC und Mach nur der Kommentar. Marken bekommen keine
    Satznummer.
  - Hinter jeder Marke ein vollständiger Einstieg: Spindel aus, zum Wechselpunkt, `T… M6`,
    Spindel, Kühlung, die Ebene (CYCLE800) neu – auch mit demselben Werkzeug wie davor; ein
    Messstopp nicht. „Auf der Maschine prüfen“ fährt ebenso vor jeder Bearbeitung zum
    Wechselpunkt (die Wechselzeit zählt nur, wo sich das Werkzeug ändert).
  - Der Kopf (mit „Kommentare“): die Marken mit ihrer Bearbeitung; je Werkzeug „T3 Kugel 6 –
    Auskragung 27 mm, Schrumpffutter Ø6 · SK40“ (wie „Auf der Maschine prüfen“ sie rechnet,
    `wegkippen.einspannung`; der vorgeschlagene Halter mit „vorgeschlagen, keiner gewählt“; ohne
    Werkzeug aus der Werkzeugverwaltung nur der Name); „ACHTUNG – knapp: T3 in „Tief“ fräst 26.0 mm
    tief und steht nur 27.0 mm heraus“, wenn eine Bearbeitung ohne Rundachse und Ebene tiefer
    fräst (Oberkante Rohteil bis zur tiefsten Stelle im Vorschub) als die Auskragung weniger 2 mm.
- **P-2026-10-04-51 – die Werkzeuglänge (G43):** Gefunden beim Durchsehen für TCPM: Der Kopf
  hebt die Längenkorrektur mit `G49` auf, der Wechsel schrieb nur `T1 M6` – an LinuxCNC, Fanuc,
  Haas und Mach stünde die Spitze danach um die ganze Werkzeuglänge tiefer als programmiert
  (FreeCADs `linuxcnc_post` schreibt `G43 H` nach dem Wechsel; im Programm des Testteils fehlte
  es). Jetzt der Befehl „Werkzeuglänge ein (Fräse)“ (`laenge_ein`, vorbelegt `G43 H{t}`, an
  Siemens leer: D1 kommt mit dem Wechsel) im ersten Satz nach dem Wechsel, der Z fährt – `G0 G43
  H1 Z15.000`; allein in einer Zeile führe eine Fanuc am Wechselpunkt oben um die Länge hinauf.
  Ist der erste Satz mit Z ein Bohrzyklus, steht die Länge in der Zeile davor. Nicht an der
  Drehmaschine (dort trägt T0101 die Korrektur).
  Ebenso an Siemens: Der Wechselpunkt `G0 SUPA D0 …` schaltet mit D0 die Korrektur ab – folgte
  kein Wechsel (Messstopp; eine andere Ebene ohne Zyklus; Sprungmarken aus), fräste das Programm
  ohne Länge weiter. Jetzt „Werkzeuglänge nach dem Wechselpunkt“ (`laenge_wieder`, an Siemens
  `D1`) im nächsten Satz mit Z (an der Drehmaschine im nächsten Fahrsatz).
- **P-2026-10-04-53 – das Programm nachlesen; die Drehmaschine an LinuxCNC, Fanuc und Haas:**
  - `camaddon/programm_pruefen.py`: liest den Text des Programms wie eine Steuerung – modal
    Bewegungsart, F, Spindel (auch `M1=3`, Haas `M133`), Werkzeug und seine Länge (G43/G49, M6,
    Siemens D0/D1, an der Drehmaschine T0101), Ebene, G93/G94 – und meldet: Bewegung in Z (an der
    Drehmaschine jede) ohne Länge, Vorschub bei stehender Spindel, ohne F oder F0, Kreise mit
    verschiedenen Radien am Anfang und Ende (über 0,002 mm), doppelte Sätze, kein M30.
    `postprozessor.nachlesen` und `nachgelesen_text`; „Programm schreiben“ zeigt es nach dem
    Speichern unter „Gespeichert …“ (rot mit Zeilen, wenn etwas gefunden ist). Am alten
    LinuxCNC-Programm des Testteils (vor -51): 12 271 Sätze ohne Länge; mit -51 bis -53 an
    Testteil, Platte und Schwenkteil (3+2) an allen fünf Steuerungen, mit und ohne Sprungmarken:
    nichts.
  - LinuxCNC übernimmt die Korrektur auch an der Drehmaschine erst mit G43:
    `laenge_ein_drehen` (vorbelegt `G43 H{t}` nur an LinuxCNC), im ersten Fahrsatz nach dem
    Wechsel.
  - An Fanuc (G-Code-System A) und Haas ist G90 an der Drehmaschine der Längsdrehzyklus, G49
    gibt es dort nicht – der Kopf der Fräse (`G17 G21 G40 G49 G80 G90`) stand bis hier auch an
    der Drehmaschine. Jetzt `kopf_drehmaschine` (statt `kopf` an der Drehmaschine), an Fanuc und
    Haas `G21 G40 G80 G97 G98`. Nicht an einer echten Steuerung nachgeprüft – vor dem ersten
    Lauf in der Simulation ansehen.
