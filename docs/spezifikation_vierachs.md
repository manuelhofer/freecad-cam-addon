# Spezifikation W-003: 4-Achs-Bearbeitung am runden Rohteil

Stand: **Entwurf von Claude mit Manuels Entscheidungen** vom 2026-09-26
(P-2026-09-26-78, am Ende unter „Entschieden“). Die Vorschläge in
Abschnitt 15 hat Claude getroffen; sie sind zur Besprechung da. Gebaut wird
Stufe für Stufe (Abschnitt 13), jede ein Patch mit Klickweg – V1, V2a und
V2c sind gebaut, als Nächstes V3 „Rundum schruppen“ (Manuels Rückmeldung vom
2026-09-27).

Grundlage: [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
(W-001: Maschine, Achsen, Aufnahmen),
[spezifikation_werkzeugverwaltung.md](spezifikation_werkzeugverwaltung.md)
(W-002: Werkzeuge, Einsätze, Schnittwerte),
[spezifikation_simulation.md](spezifikation_simulation.md) (W-001 Stufe 4:
Bahn auf der Maschine abfahren).

## 1. Zielbild

Manuel (2026-09-26): „Ich habe ein Bauteil, das ich an ein rundes Rohteil im
CAM befestigen kann … sagen wir mal eine Stange rund Durchmesser 80. Und ich
nehme das Bauteil und wähle eine Fläche; diese Fläche soll sozusagen vorne an
das Rohteil … zentrisch, dass versucht wird, das komplette Bauteil in das
Rohteil zu bekommen. Dann klickt man die Flächen an, sagen wir alle
Mantelflächen oder einen Zylinder, der nicht mittig ist, und dann wird aus
Kombination Fräser und Rohteil eine Schrupp- und danach eine
Schlicht-Strategie erstellt. Maximal bedienerfreundlich das Ganze.“ Dabei soll
es egal sein, ob die Rundachse C, B oder A heißt – es soll auch auf einer
Drehmaschine wie der CLX 550 mit Y-Achse gehen.

**Klickweg, wenn alles gebaut ist:**

1. Teil anklicken, dann seine Stirnfläche → Werkzeugleiste „CAM-Addon“ →
   **„4-Achs-Bearbeitung“**.
2. **Rohteil:** Stange Ø 80 eintragen – das Teil fährt in die Stange und
   dreht sich einmal um die Achse; das Fenster sagt „Passt – rundum
   mindestens 4,0 mm“.
3. **Flächen:** „Alle Mantelflächen“ – oder nur den außermittigen Zylinder
   anklicken.
4. **Werkzeuge:** Schruppfräser und Schlichtfräser wählen; Drehzahl,
   Vorschub, Zustellung und Schrittweite kommen aus der Werkzeugverwaltung.
5. **Anlegen:** Es entstehen ein Job mit der Stange, zwei
   Werkzeug-Controller und die Operationen „Rundum schruppen T1“ und „Rundum
   schlichten T2“ – ein Strg+Z nimmt alles zurück. Die Bahnen liegen in der
   3D-Ansicht sichtbar um das Teil, der Postprozessor schreibt Sätze mit C
   (bzw. A oder B).

## 2. Was es schon gibt

**In FreeCAD** (Quelltext 1.1.3 und `main` gelesen, P-2026-09-26-78):

| Baustein | 1.1.3 (Manuels Version) | Wochen-Build | Taugt für W-003? |
| --- | --- | --- | --- |
| 3D-Oberfläche „Rotational“ (`Path/Op/Surface.py`) | nur mit OpenCamLib und dem Schalter „advanced OCL features“ | ja | nein: nur A oder B, die erste Lage beginnt an der Ecke der Hüllbox statt an der Stange |
| Dressup „Axis Map“ | ja | ja | nein: wickelt eine 2D-Bahn auf einen **festen** Radius – Mantelflächen haben keinen |
| „Rotary Surface“ (`Path/Op/RotarySurface.py`: Spirale, Ringe, Linien, Lagen ab dem Stangenradius) | **fehlt** | nur mit Experimentier-Schalter, OpenCamLib und CAM-Maschine im Job; Achse nur entlang X oder Y („Rotary axis along world Z is not supported in v1“); Aufmaß nur radial | nein: nicht in 1.1.3, nicht für die C-Achse einer Drehmaschine |
| Arbeitsebenen (Workplanes: normale Operationen 3+2 angestellt) | fehlt | ja | später, für „indexiert“ (Abschnitt 12) |
| Bahnanzeige mit A/B/C (`App/PathSegmentWalker.cpp`: A dreht um X, B um Y, C um Z, um `Path.Center`) | ja | ja | **ja** – wenn die Rundachse durch den Nullpunkt des Jobs geht; `Job.setCenterOfRotation` wirkt nicht zuverlässig (setzt den Mittelpunkt an einer Kopie) |
| `Path.Main.Job.Create`, `Path.Main.Stock.CreateCylinder` | ja, im **aktiven** Dokument | ja | **ja** |
| Eigene Operation als Unterklasse von `Path.Op.Base.ObjectOp`, angelegt mit `DoNotSetDefaultValues` | ja | ja (dazu Workplane-Logik) | **ja** – so baut FreeCAD jede seiner Operationen |
| numpy | feste Abhängigkeit von FreeCAD (numpy 2.4 in 1.1.3) | ja (2.5) | **ja** |
| OpenCamLib | **keine** feste Abhängigkeit – in beiden Testumgebungen nicht vorhanden | ebenso | nicht voraussetzen |

**Im Addon:**

| Baustein | Wo | Nutzen |
| --- | --- | --- |
| Werkzeuge, Einsätze, Schnittwerte je Werkstoff | `werkzeuge.py` (`mass`, `reichweite`), `schnittdaten.py` | Schrupp- und Schlichtwerte, Länge des Fräsers |
| Werkzeuge an CAM, Controller, Werkstoff am Rohteil | `uebergabe_werkzeuge.uebergeben`, `job_schnittwerte.lege_controller_an`, `werkstoff_des_jobs`, `setze_werkstoff_am_rohteil` | Controller in den Job |
| Maschine mit Achsen, Aufnahmen, Rollen, schräger Achse | `maschine.py` (`rollen`, `programmname`), `kette.py`, `verfahren.plusrichtung`, `schraege_achse.programmrichtung` | welche Achse dreht, woher das Werkzeug kommt |
| Hervorheben, Wackeln, Widgets, Zahlen, Einheiten, Hilfe | `gui_zeigen.py`, `gui_teile.py`, `gui_zahlen.py`, `einheiten.py`, `gui_hilfe.kopfzeile` | Bedienung |

**Was fehlt ganz:** Flächen in der 3D-Ansicht anklicken, Job und Rohteil
anlegen, Bahnen erzeugen. Deshalb (Manuels Entscheidung 1) ein **eigener
Rechenkern**: Er läuft in 1.1.3 und im Wochen-Build, mit A, B oder C, auch
auf der Drehmaschine mit radialem Werkzeug.

## 3. Begriffe

- **Rundachse** – die Achse, die das Werkstück dreht (A, B oder C).
- **Stange** – das runde Rohteil; ihre Mittellinie ist die Rundachse.
- **Vorne** – das freie Ende der Stange, weg vom Futter.
- **Stirnfläche** – die ebene Fläche des Teils, die vorne an der Stange
  liegen soll. **Mantelfläche** – jede Fläche, die zur Seite schaut (nicht
  nach vorne oder hinten).
- **Planaufmaß** – so viel steht die Stange vorne über das Teil hinaus.
  **Abstechbreite** – Platz hinter dem Teil fürs Abstechen oder Absägen.
  **Spannlänge** – so lang steckt die Stange im Futter.
- **Schlichtaufmaß** – so viel lässt das Schruppen für das Schlichten stehen.
- **Hüllfläche** – wie tief die Werkzeugspitze an jeder Stelle kommt, ohne das
  Teil zu verletzen.
- **Rundachs-Koordinaten** – so rechnet das Addon, egal wie die Maschine
  aussieht:

```
                 r (Werkzeugspitze bis Achse)
                 ↓  Werkzeug kommt von außen
  Futter │       ┃
  ███████│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ███████│   Stange          Teil              ┃ vorne
  ███████│─────────────────── Rundachse ───────╂──────► a (längs)
  ███████│                                     ┃
  ███████│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
         │← Spannlänge →│← Abstich →│← Teil →│← Planaufmaß
                                    a ≤ 0     a = 0 an der Stirnfläche
  φ = Drehwinkel um die Achse, q = seitlich (in W-003 immer 0)
```

  a = 0 liegt in der gewählten Stirnfläche, das Teil bei a ≤ 0 – wie Z0 an
  der Drehmaschine.

## 4. Achsen – von der Maschine oder zugewiesen

Manuel: „Am besten von der Maschine, ansonsten dreht sich das Rohteil … und
so auch das Bauteil, und dem muss man eine Achse zuweisen.“

**Mit einer Maschine aus W-001** (in einem offenen Dokument):

- **Rundachse** = die Betriebsart „Positionieren“, die `maschine.rollen()`
  dem Tisch zuordnet – bei der Beispiel-Drehmaschine C1.
- **Längs** („vorne“) = Z des LCS der Werkstückaufnahme (zeigt vom Futter
  weg). **Radial** = Z des LCS der gewählten **radialen** Werkzeugaufnahme,
  etwa Revolverplatz P1. **Quer** = längs × radial.
- Welche Programmachse das jeweils ist, sagt der Vergleich mit den
  Linearachsen (größter Betrag des Kosinus, mit Vorzeichen;
  `verfahren.plusrichtung`, Tischachsen umgekehrt; eine schräge Achse über
  `schraege_achse.programmrichtung`). Die Buchstaben kommen aus den Namen:
  `maschine.programmname()` macht aus C1 ein C.
- So ist egal, dass beim Schrägbett die Welt-Achsen nicht die der Maschine
  sind. Gibt es mehrere Möglichkeiten (zwei Rundachsen, mehrere radiale
  Plätze), fragt der Assistent in Schritt 1 nach. An der Maschine wird nichts
  gespeichert: Die Drehrichtung kommt aus dem Gelenk.

**Ohne Maschine** dreht die Stange mit dem Teil um ihre eigene Achse, und
man weist ihr den Buchstaben zu:

| Rundachse | Stange liegt längs (vorne) | Werkzeug kommt aus | quer |
| --- | --- | --- | --- |
| A | +X | +Z (von oben) | Y |
| B | +Y | +Z (von oben) | X |
| C | +Z | +X (wie an der Drehmaschine) | Y |

Die zuletzt gewählte gilt beim nächsten Mal als Vorschlag.

**Lage im Job:** Die Stange liegt so, dass die Rundachse durch den Nullpunkt
des Jobs geht – bei A entlang X, bei B entlang Y, bei C entlang Z. Dann legt
FreeCADs Bahnanzeige die Bahn ohne weiteres Zutun richtig um das Teil. X (bzw.
der radiale Buchstabe) ist der **Radius**, der Abstand zur Achse.

## 5. Schritt 1: Rohteil

**Rechnung:**

- Die angeklickte Fläche muss eben sein. Ihre **Außennormale** wird zur
  Stangenachse nach vorne; a = 0 liegt in der Fläche.
- **Mitte** – zwei Möglichkeiten, jede mit dem Ø, den die Stange dann
  mindestens braucht:
  - „**Mitte der runden Fläche**“: Ist die Außenkante der Fläche ein Kreis
    (auch aus mehreren Bögen mit gleicher Mitte), sitzt dessen Mitte auf der
    Achse; sonst der Schwerpunkt der Fläche.
  - „**Ganzes Teil möglichst mittig**“: der kleinste Kreis um alle Punkte
    des Teils, in Achsrichtung gesehen (Punkte aus der Tessellierung, erst die
    konvexe Hülle, dann Welzl).
  - **Vorschlag:** die runde Fläche, wenn es eine ist und das Teil so in die
    Stange passt – sonst das ganze Teil. Beispiel: Welle Ø 60 mit einem
    Nocken, der bis 36 mm von der Wellenachse reicht → mittig auf der
    Welle braucht Ø 72,0, das ganze Teil möglichst mittig nur Ø 66,0; bei
    einer Stange Ø 80 bleibt die Welle mittig, mit 4,0 mm Aufmaß rundum.
- **Drehlage** um die Achse: Feld in Grad und Knopf „+90°“.
- **Stange Ø:** Vorschlag grau – der nächste 5-mm-Schritt (Zoll: 1/8") mit
  mindestens 1 mm am Radius. Passt das Teil, sagt eine grüne Zeile „Passt –
  rundum mindestens … mm“, sonst eine rote „Passt nicht: Das Teil braucht
  Ø … – etwa eine Stange Ø …“.
- **Länge** = Planaufmaß (Vorschlag 1 mm) + Teil + Abstechbreite (3 mm) +
  Spannlänge (30 mm) – grau angezeigt.

**Wirkung im Dokument** (alles in der Transaktion des Assistenten):

- ein **neuer Job** (`Path.Main.Job.Create` – nicht FreeCADs Befehl, der
  öffnet eine eigene Transaktion), mit der Anzeige des Jobs wie bei FreeCADs
  Befehl;
- das Teil liegt im **Modell-Klon** des Jobs an seiner Stelle: Klon-Lage =
  T · Lage beim Anlegen, gerechnet immer vom Original aus, damit sich
  Änderungen nicht aufhäufen; das Original bleibt, wo es ist;
- das Standard-Rohteil wird durch einen **Zylinder** ersetzt
  (`CreateCylinder`), von vorne bis ans Ende der Spannlänge.

**Zeigen statt beschreiben:** Das Teil fährt von seiner alten Lage in die
Stange und dreht sich dann einmal um die Achse – eine kurze Animation ohne
Text. Während der Assistent offen ist, ist die Stange durchscheinend und nicht
anklickbar; das Original ist verborgen.

```
[ Anlegen ]  [ Abbrechen ]                                    (FreeCAD)
─────────────────────────────────────────────────────────────────────
4-Achs-Bearbeitung – Schritt 1 von 4: Rohteil                    (?)
Klick die Fläche an, die vorne an der Stange liegen soll.

  Teil           Welle, Fläche 3 (eben, rund Ø 60)
  Stange Ø       [ 80       ] mm
  Mitte          (•) Mitte der runden Fläche      braucht Ø 72,0
                 ( ) ganzes Teil möglichst mittig  braucht Ø 66,0
  Drehlage       [ 0        ] °    [ +90° ]
  Planaufmaß     [ 1        ] mm   (grau: Vorschlag)
  Abstechbreite  [ 3        ] mm
  Spannlänge     [ 30       ] mm   Stange 134 mm lang
  Rundachse      [ Maschine „Drehmaschine“: C1, Werkzeug P1 radial ▾ ]
                   ohne Maschine: A – Stange in X, Werkzeug von oben
                                  B – Stange in Y, Werkzeug von oben
                                  C – Stange in Z, Werkzeug aus X
  ✔ Passt – rundum mindestens 4,0 mm Aufmaß.                  (grün)
                                              [ Zurück ] [ Weiter ]
```

## 6. Schritt 2: Flächen

- Flächen in der 3D-Ansicht anklicken (noch einmal klicken nimmt sie heraus).
  Nur Flächen des Teils lassen sich wählen; die Stange nicht.
- „**Alle Mantelflächen**“ wählt jede Fläche, die zur Seite schaut.
  „Auswahl leeren“ fängt von vorne an.
- Die Liste nennt die Art („Zylinder Ø 20, 15 mm außermittig“) und die
  **Erreichbarkeit**: Ein Werkzeug, das von außen zur Achse zeigt, kommt nur
  an Stellen, über denen – nach außen – kein Material liegt. Das rechnet die
  Hüllfläche mit einem punktförmigen Werkzeug (Abschnitt 9).
  Stirnflächen sind „nicht radial bearbeitbar“.
- In der Ansicht: erreichbar grün, teilweise gelb, nicht erreichbar rot – nur
  die Anzeige, danach wieder wie vorher.

```
4-Achs-Bearbeitung – Schritt 2 von 4: Flächen                    (?)
Klick die Flächen an, die gefräst werden sollen.
  [ Alle Mantelflächen ]  [ Auswahl leeren ]
  ┌───────────────────────────────────────────────────────────┐
  │ ✔ Fläche 1   Zylinder Ø 60, mittig             erreichbar  │
  │ ✔ Fläche 5   Zylinder Ø 20, 26 mm außermittig  erreichbar  │
  │ ◐ Fläche 8   Freiform                 zu 80 % erreichbar   │
  │ ✘ Fläche 11  Ebene, unter einem Überhang  nicht erreichbar │
  └───────────────────────────────────────────────────────────┘
  ✘ Fläche 11 liegt unter einem Überhang – ein Werkzeug, das von
    außen zur Achse zeigt, kommt dort nicht hin.               (rot)
                                              [ Zurück ] [ Weiter ]
```

## 7. Schritt 3: Werkzeuge

- **Werkstoff** vom Rohteil (wie in „Schnittwerte in den Job“), sonst wählbar.
- **Schruppen:** Schaft- oder Torusfräser aus der Werkzeugverwaltung, Einsatz
  „Schruppen“ → **ap = Zustellung je Lage** (radial), **ae = Vorschub je
  Umdrehung** der Spirale, n und vf; Schlichtaufmaß (Vorschlag 0,3 mm); dazu
  die Zahl der Lagen.
- **Schlichten:** Kugel- oder Torusfräser, Einsatz „Schlichten“ →
  Schrittweite, daneben die Kammhöhe, die sie hinterlässt.
- **Muster:** Spirale (Vorschlag), Ringe oder Linien längs.
- **Rote Hinweise:** Reichweite des Fräsers (`werkzeuge.reichweite`) kleiner
  als die Tiefe (Stangenradius minus kleinster Radius im gewählten Bereich);
  zu wenig Platz zum Futter; eine Stelle enger als der Fräser. Schaft und
  Halter prüft erst W-001 Stufe 4.
- Ohne passendes Werkzeug in der Werkzeugverwaltung: ein Satz und der Knopf
  „Werkzeugverwaltung öffnen“.

```
4-Achs-Bearbeitung – Schritt 3 von 4: Werkzeuge                  (?)
  Werkstoff      [ 1.0503 C45 ▾ ]                    (vom Rohteil)
Schruppen
  Werkzeug       [ T1 Schaftfräser VHM D12 ▾ ]
  Einsatz        [ Schruppen ▾ ]     n 3183 1/min   vf 1528 mm/min
  Zustellung je Lage ap   [ 2     ] mm   → 5 Lagen (Ø 80 → Ø 60,6)
  Vorschub je Umdrehung   [ 4,8   ] mm   (40 % von D)
  Schlichtaufmaß          [ 0,3   ] mm
Schlichten
  Werkzeug       [ T2 Kugelfräser VHM D6 ▾ ]
  Einsatz        [ Schlichten ▾ ]    n 7958 1/min   vf 955 mm/min
  Schrittweite   [ 0,35  ] mm   → Kammhöhe 5 µm
  Muster         [ Spirale ▾ ]
▸ Mehr …   (Toleranz, Glättung, Vorschub, Richtung, Sicherheitsabstand)
  ✘ Fläche 8 ist enger als T1 (Ø 12) – dort bleibt Material für T2. (rot)
                                              [ Zurück ] [ Weiter ]
```

## 8. Schritt 4: Anlegen

Eine Zusammenfassung mit einer eigenen Zeitschätzung (CAMs Schätzung kennt
keine Rundachse). „Anlegen“ legt alles in **einer** Transaktion an: Job,
Stange, Controller, Operationen. „Abbrechen“ verwirft auch Job und Stange.

```
4-Achs-Bearbeitung – Schritt 4 von 4: Anlegen                    (?)
Es wird angelegt:
  • Job „Welle – 4 Achsen“, Stange Ø 80 × 134 mm, Rundachse C
  • T1 Schaftfräser VHM D12 – Schruppen
  • T2 Kugelfräser VHM D6 – Schlichten
  • Rundum schruppen T1     5 Lagen     etwa 12 min
  • Rundum schlichten T2                etwa 18 min
Ein Strg+Z nimmt alles zusammen zurück.
                                    [ Zurück ]  (oben: [ Anlegen ])
```

## 9. Rechenkern

Zwei Module ohne Oberfläche: `camaddon/vierachs_huelle.py` (Hüllfläche) und
`camaddon/vierachs_bahn.py` (Bahnen). Sie laufen in FreeCADCmd und werden
dort geprüft.

**Werkzeug:** ein Modell für alle drei Fräser – ein Torus mit Radius R und
Eckradius rc: rc = 0 ist der Schaftfräser, rc = R der Kugelfräser.
**Aufmaß δ** exakt, auch an steilen Wänden: mit (R + δ, rc + δ) rechnen und
δ zur Spitze addieren.

**Hüllfläche R(a, φ):** Für jeden Winkel φ werden die Punkte des Teils einmal
so gedreht, dass das Werkzeug von außen kommt. Übrig bleiben nur die Dreiecke
im Streifen |seitlich| ≤ R + δ; gegen sie fällt das Werkzeug an allen
Längsstellen a zugleich (numpy). Ecke und Dreiecksfläche lassen sich
geschlossen rechnen, die Kante beim Kugel- und Schaftfräser auch; beim
Torusfräser werden die Kanten unterteilt.

- Gerechnet wird immer gegen das **ganze** Teil – die gewählten Flächen
  sind nur die Maske, in der gefräst wird.
- Schruppen reicht ein grobes Raster (etwa 2° × 0,5 mm; der Rasterfehler
  geht ins Aufmaß), Schlichten braucht ein feines.
- Ergebnisse werden zwischengespeichert, und der Assistent zeigt den
  Fortschritt. Ziel: ein Teil Ø 80 × 100 mm in Sekunden, nicht in Minuten.

**Fallstricke:**

- Nahe der Achse (Radius kleiner als der Werkzeugradius) wird gesperrt.
- „Kein Treffer“ hinter dem Teil (Abstich, Futter) heißt: Das Material
  bleibt – nicht Radius 0.
- Die Naht bei 0/360° wird periodisch gerechnet.
- Längs bleibt die Werkzeugmitte zwischen Planaufmaß und Hinterkante des
  Teils.

**Schruppen:** Lagen r_k = R_Stange − k · ap, bis zur Hüllfläche plus
Schlichtaufmaß; die Bahn folgt max(r_k, Hüllfläche) in der Maske.

- Die Spirale läuft von vorne Richtung Futter.
- Eingefahren wird von vorne außerhalb der Stange, sonst schraubenförmig mit
  dem Eintauchwinkel aus der Werkzeugverwaltung.
- Ringe bekommen eine Rampe.
- Zahl der Lagen = ⌈(R_Stange − r_min − δ) ÷ ap⌉.

**Schlichten:** eine Bahn auf der Hüllfläche.

- Spirale mit der Steigung = Schrittweite s, oder Linien längs im
  Winkelabstand Δφ = s ÷ r_max.
- Kammhöhe beim Kugelfräser: h = R − √(R² − (s/2)²).

**Rückzug:** zwischen zwei Abschnitten auf Stangenradius plus
Sicherheitsabstand; längs nie in den Bereich des Futters; am Ende radial
hinaus.

**Winkel:** fortlaufend (0 … 3600°), wenn die Rundachse endlos dreht (W-001
„Endlos“, ohne Maschine angenommen); sonst hin und her statt Spirale.

**Ausgabe – Achskoordinaten, für jede Maschine gleich** (Manuel: „Es gibt
Achsen, und die Punkte müssen halt via Koordinate im G-Code 0,001 mm nach und
nach angefahren werden … oder halt mit einem Glättungsfilter“):

- Punkt für Punkt als G1 mit den Buchstaben der Maschine, etwa X Z C, auf
  0,001 mm bzw. 0,001° – keine Bögen, keine Zyklen.
- Der Punktabstand folgt der Toleranz: Schruppen 0,02 mm, Schlichten
  0,005 mm Sehnenfehler.
- Ein **Glättungsfilter** im Addon nimmt die Rasterstufen der Rechnung
  heraus, ohne die Toleranz zu verlassen.
- Die Glättung der Steuerung (etwa Siemens CYCLE832, Fanuc AICC) kann
  zusätzlich laufen. Sie wird im Programmkopf eingeschaltet, nicht vom Addon.

**Vorschub:** Dreht sich vor allem die Rundachse, rechnen Steuerungen F
verschieden. Damit der Fräser am Werkstück trotzdem mit vf fährt, steht vor
der Bahn **G93**: Jeder Satz trägt als F die Zahl 1 ÷ Zeit, danach kommt
G94. Die Zeit ist der Weg am Werkstück durch vf:

```
t = √(Δa² + Δr² + (r · Δφ)²) ÷ vf
```

Siemens, Fanuc, Haas und LinuxCNC verstehen G93 gleich. Eine Steuerung ohne
G93 hält mit Alarm an, statt mit falschem Vorschub zu fahren. Die
Drehzahlgrenze der Rundachse kommt aus W-001. Achtung: CAM führt F intern in
mm/s, der Postprozessor rechnet ×60.

## 10. Die CAM-Operation

- `camaddon/vierachs_operation.py`: ein `Path::FeaturePython`, dessen Proxy
  `Path.Op.Base.ObjectOp` erbt. Die Anzeige liegt in
  `gui_vierachs_operation.py`: Doppelklick öffnet den Assistenten bei
  Schritt 3.
- **Merkmale** nur die, die es in beiden Versionen gibt:
  `FeatureTool | FeatureBaseFaces | FeatureCoolant`. Keine Höhen und Tiefen
  in Z – sonst hängt die Basis ein „G0 Z Sicherheitshöhe“ an, und das hieße
  bei C: längs zum Futter.
- **Anlegen** mit `DoNotSetDefaultValues` = True und `parentJob`. Ohne das
  fragt FreeCAD nach Job und Controller, sobald es mehrere gibt – in
  FreeCADCmd ein Fehler. Danach setzt der Assistent selbst:
  `job.Proxy.addOperation`, `ToolController`, `OpToolDiameter`,
  `CoolantMode`, `Active`.
- **Wochen-Build:** `Workplane` = None und ausgeblendet. Das Modell kommt
  direkt aus `job.Model.Group` (die Basis würde `self.model` sonst drehen).
- Die Operation merkt sich die Lage des Modell-Klons, mit der sie gerechnet
  hat, und warnt, wenn sie im Job-Dialog verändert wurde.
- Modul- und Klassenname sind von Anfang an endgültig – sie stehen in jeder
  gespeicherten Datei. Im Operationsmodul steht kein Qt. Speichern, Laden und
  Neuberechnen werden geprüft.
- `job_schnittwerte.EINSATZ_NACH_OPERATION` lernt die Operation, damit
  „Schnittwerte in den Job“ sie kennt.

## 11. Bedienung: Vorschläge, „Mehr …“, Hilfe

- **Alles einstellbar, Vorschläge als Standard** (Manuel): Jeder Wert steht
  als Vorschlag im Feld – grau und gültig, wenn man nichts einträgt, wie in
  der Werkzeugverwaltung.
- Was man einträgt, merkt sich das Addon als nächsten Vorschlag. Ausnahme:
  Werte, die am Teil hängen, wie der Stangen-Ø. „Vorschläge zurücksetzen“
  steht in den Einstellungen des Addons.
- **„Mehr …“** je Schritt, zum Aufklappen: Toleranzen, Glättung,
  Vorschubart, Raster, Sicherheitsabstand, Richtung, Gleich- oder Gegenlauf.
  So bleibt der Assistent schlicht.
- **Hilfe:** ein (?) je Schritt öffnet `help/<sprache>/vierachs.html` –
  mit Bildern der Begriffe aus Abschnitt 3, den Grenzen aus Abschnitt 12 und
  einem Beispiel Schritt für Schritt. Texte in `translations/*.json` unter
  `va.*`.
- **Zeigen:** Animationen ohne Text in der 3D-Ansicht. Das Teil fährt in die
  Stange, und die Stange dreht sich einmal, wenn man die Rundachse wählt.
  Gewählte Flächen leuchten kurz auf.

## 12. Nicht Teil davon

- **Drehen**, Planen der Stirnseite, **Abstechen** – das macht die Maschine
  (FreeCAD dreht nicht).
- **Axiales Werkzeug** auf der Stirnseite (TRANSMIT) und **indexiert 3+1**
  (Achse steht, eben gefräst: Abflachungen, Taschen, Querbohrungen) – eine
  spätere Stufe. Im Wochen-Build helfen dafür FreeCADs Arbeitsebenen.
- **Hinterschnitte:** Was ein radiales Werkzeug nicht erreicht, bleibt stehen
  und wird gemeldet.
- **Kollision** von Halter, Schaft oder Futter: nur Hinweise; die Prüfung ist
  W-001 Stufe 4.
- **Rohr** (hohle Stange), **Reitstock**.
- **Maschinenspezifisch** bleiben nur Kopf- und Fußzeilen des Programms:
  C-Achsbetrieb ein und aus, das angetriebene Werkzeug, die Glättung, bei
  Drehmaschinen „X als Radius“ (Siemens `DIAMOF`). Die trägt man in FreeCADs
  Postprozessor als Programmkopf und -fuß ein (Preamble/Postamble); das Addon
  schreibt sie nicht.
- FreeCADs CAM-Simulator zeigt Rundachsbahnen vermutlich nicht – in V1
  prüfen und in der Hilfe sagen.

## 13. Stufen

Jede Stufe ist ein Patch mit einem Klickweg als Akzeptanzkriterium; jede
bringt Prüfungen, ein Szenario mit Screenshots, Texte in de/en und ihren Teil
der Hilfe mit.

**V1 – Teil in die Stange**

- Befehl mit Symbol; Assistent mit Schritt 1 und der Buchstaben-Liste.
- Neu: `camaddon/vierachs_rohteil.py` (Rechnung), `camaddon/gui_vierachs.py`.
- Prüfung: Quader, Sechskant, Welle mit Nocken (runde Fläche gegen ganzes
  Teil), A/B/C, Job mit Zylinder-Rohteil, ein Rückgängig; numpy vorhanden.
- *Klickweg:* Welle öffnen, Stirnfläche anklicken → „4-Achs-Bearbeitung“ →
  Stange Ø 80, Rundachse C → das Teil liegt mittig in einer durchsichtigen
  Stange längs Z, die Fläche 1 mm hinter der Stangenstirn, „Passt – rundum
  mindestens 4,0 mm“; Abbrechen hinterlässt nichts, „Anlegen“ nimmt ein
  Strg+Z zurück.
- *Gebaut (P-2026-09-26-79):* Befehl mit Symbol in der Werkzeugleiste
  „CAM-Addon“, Schritt Rohteil mit allen Feldern aus der Skizze, Animation,
  Hilfeseite; Rundachse ohne Maschine (A/B/C). Der Kopf zeigt nur
  „Rohteil“, solange es die anderen Schritte noch nicht gibt.

**V2 – Achse von der Maschine**

Manuels Test (2026-09-27, siehe „Entschieden“): Mit der vorgewählten Rundachse
A lag die Stange im Job längs X – auf seiner Drehmaschine „CLX 550“ stand sie
im Prüffenster quer im Futter. Das Prüffenster rechnet in den Achsen der
Werkstückaufnahme; an der Drehmaschine ist deren Z die Spindelachse, die
Stange muss also längs Z liegen. Deshalb in drei Schritten:

- **V2a – die Maschine gibt die Achse vor.** Neu: `camaddon/vierachs_achsen.py`.
  Ist eine W-001-Maschine offen, stehen ihre Rundachsen im Tisch (Betriebsart
  „Positionieren“) oben in der Liste „Rundachse“ und sind vorgewählt; längs =
  die Richtung der Rundachse in den Achsen der Werkstückaufnahme (= des Jobs),
  vorne = vom Futter weg (Z des LCS). Die Buchstaben A/B/C bleiben für „ohne
  Maschine“.
  *Klickweg:* Beispiel-Drehmaschine laden, im Dokument der Welle
  „4-Achs-Bearbeitung“ → unter Rundachse steht „Maschine „Drehmaschine“: C –
  Stange längs Z“, vorgewählt, und die Stange liegt längs Z; mit „A – Stange
  in X“ liegt sie längs X.
  *Gebaut (P-2026-09-27-37):* `vierachs_achsen.py`, die Liste mit den
  Maschinen oben, A/B/C mit „(ohne Maschine)“; im Prüffenster liegt die Stange
  parallel zur C-Achse (`szenario_vierachs_maschine`).
- **V2b – Drehteile.** Ein Klick auf eine runde Fläche (Zylinder, Kegel,
  Kugel, Torus) nimmt deren Achse als Stangenachse, die Mitte liegt auf ihr –
  heute sagt der Assistent dort „nicht eben“. Vorne ist das Ende des Teils,
  an dem man geklickt hat; „Umdrehen“ tauscht die Enden.
  *Klickweg:* Welle, Klick auf den Mantel nahe dem rechten Ende → das rechte
  Ende liegt vorne an der Stange, mittig; „Umdrehen“ → das linke.
- **V2c – das Prüffenster.** Dreht ein Programm um eine Achse, die die
  Maschine nicht hat (A auf der Drehmaschine mit C), sagt es ein Hinweis statt
  eines schiefen Bildes. Der Vorschlag für den Nullpunkt steckt eine Stange
  aus dem Assistenten mit ihrer Spannlänge ins Futter, statt sie davor zu
  stellen.
  *Klickweg:* Job mit Rundachse A auf der Beispiel-Drehmaschine prüfen → „…
  dreht um A – die Maschine hat keine Rundachse A“; Job mit C → die Stange
  steckt 30 mm im Futter.
  *Gebaut (P-2026-09-27-38):* Hinweis `rw.rundachse_fehlt(_andere)`; die
  Spannlänge steht ausgeblendet am Job (`CamAddonSpannlaenge`); eine Stange
  längs Z sitzt im Vorschlag genau auf ihrer Achse (die Hüllbox lag 0,043 mm
  daneben).
- Wenn gewünscht später: Beispielmaschine „4-Achs-Fräse mit A“.

**V3 – Rundum schruppen**

Manuels Test (2026-09-27): Nach „Anlegen“ „passiert ja weiter nichts ...
keinerlei abfrage vonwegen welches werkzeug .. und keine generierung der
werkzeugwege .. also wäre cool wenn dann einfach ein fenster aufgeht .. was
willste machen .. schruppen“. Deshalb kommt die Bahn vor dem Flächenwählen:
Nach dem Rohteil fragt der Assistent, was man machen will, und „Rundum
schruppen“ nimmt das ganze Teil bis aufs Schlichtaufmaß – ohne Flächen zu
wählen. Die bisherigen Stufen V4 (Controller ohne Transaktion) und V5
(Werkzeuge) gehen darin auf; die übrigen rücken nach (V4 bis V7).

- **V3a – Hüllfläche** (`camaddon/vierachs_huelle.py`): für den Schaftfräser
  genau gegen das vernetzte Teil – je Kante der Schnitt mit dem Kreis der
  Stirn, je Dreieck die höchste Stelle dieses Kreises auf seiner Ebene –, im
  Raster 1° × 0,25 mm, mit numpy. Zwischen den Rasterpunkten gilt der höchste
  Nachbar, dazu die Toleranz der Vernetzung: Der Fehler geht ins Aufmaß, nie
  ins Teil. Das Aufmaß δ rechnet mit dem Radius R + δ und hebt die Spitze um δ.
  Prüfung: Zylinder, Exzenter, Sechskant und Welle mit Absatz gegen die
  Formel, dazu eine Zeitgrenze. *Gebaut (P-2026-09-27-46).*
- **V3b – Bahn** (`camaddon/vierachs_bahn.py`): Lagen r_k = R_Stange − k · ap
  bis zur Hüllfläche plus Aufmaß. Je Lage eine Spirale mit der Steigung
  „Vorschub je Umdrehung“ von vorne – das Werkzeug ganz vor der Stange – bis
  vor das Futter: Der Rand des Fräsers bleibt 2 mm vor der Spannfläche (bis
  V3e 1 mm – so knapp wie der Warnabstand der Kollisionsprüfung). Trifft
  das Werkzeug hinter dem Teil nichts, bleibt es oben (das Material bleibt);
  vor dem Teil schneidet es die Lage. Der Achse kommt die Spitze nicht näher
  als der Fräserradius. Zwischen den Lagen radial hinaus auf Stangenradius
  plus Sicherheitsabstand und im Eilgang nach vorne. Ausgabe: G1 mit X als
  Radius, Z und C (bzw. A oder B) auf 0,001, zwischen G93 und G94, F = 1 ÷
  Zeit. Liegen Punkte in (a, r, φ) auf einer Geraden, bleibt nur der letzte.
  *Gebaut (P-2026-09-27-47):* höchstens 90° je Satz – FreeCAD 1.1.3 zeigt
  einen Satz über mehr als eine Umdrehung als Gerade.
- **V3c – Operation** (`camaddon/vierachs_operation.py`): „Rundum schruppen“,
  eine CAM-Operation mit Controller und Kühlmittel. Sie rechnet ihre Bahn beim
  Neuberechnen aus Modell und Stange des Jobs, ihre Werte stehen als
  Eigenschaften in der Gruppe „4-Achs“. Die Bahn beginnt mit einem Kommentar:
  X ist der Radius (Drehmaschine: im Programmkopf auf Radius stellen, Siemens
  `DIAMOF`). Prüfung: in beiden Versionen anlegen, Speichern und Laden,
  Postprozessor-Ausgabe. *Gebaut (P-2026-09-27-48).*
- **V3d – Assistent:** „Weiter“ führt zu Schritt 2 „Was willst du machen?“ mit
  „Rundum schruppen“. Darunter: der Fräser aus der Werkzeugverwaltung
  (Schaftfräser), sein Einsatz „Schruppen“ mit n und vf, Zustellung je Lage
  ap, Vorschub je Umdrehung (ae) und Schlichtaufmaß, dazu grau „→ 5 Lagen
  (Ø 80 → Ø 60,6)“. „Anlegen“ legt Job, Stange, Controller und Operation in
  einer Transaktion an; dafür wird `lege_controller_an` in Kern und
  Transaktion geteilt.
  *Gebaut (P-2026-09-27-49):* Schritt 2 wie beschrieben, dazu Werkstoff,
  „Zurück“ und „Werkzeugverwaltung …“. Abweichung: **zwei** Schritte
  Rückgängig – zuerst Controller und Operation, dann Job und Stange. FreeCAD
  1.1 schließt die offene Transaktion, wenn CAM ein Werkzeug (ToolBit)
  anlegt; nur in einem Befehl, in dem sie geöffnet wurde, bleibt sie – für den
  Controller also eine eigene. Den Vorgabe-Controller jedes neuen Jobs nimmt
  der Assistent heraus.
- **V3e – Prüffenster:** Rundachsen wie an einer Steuerung ohne TCPM: X, Y
  und Z bleiben im Rahmen der Maschine, die Rundachse dreht das Teil darunter.
  Genau so zeigt FreeCAD die Bahn (`PathSegmentWalker`: der Punkt um −C
  gedreht). Bisher rechnete das Prüffenster die Punkte am mitgedrehten Teil
  (wie mit TCPM). G93 zählt für die Zeit. Sitzt das Werkzeug einer
  4-Achs-Operation längs Z, sagt es ein Hinweis.
  *Gebaut (P-2026-09-27-50 bis -54):* Linearachsen einmal je Werkzeug mit den
  Rundachsen auf 0 gelöst; G93: ein Satz dauert 1 ÷ F Minuten; die Bahn im
  Bild am Werkstück, um das Teil herum (der Punkt um −C gedreht, wie in
  FreeCAD). Hinweis, wenn das Werkzeug nicht radial aus der Richtung kommt,
  für die „Rundum schruppen“ rechnet („… radial aus +X zur Achse zeigt – T2
  sitzt auf P2 aber anders …“). Dazu, gefunden an der Rundum-Bahn: Die
  Kollisionsprüfung rechnete jede Drehung mit der Größe der ganzen Maschine
  und lief über 20 Minuten – jetzt je Paar und nur genau, wo nötig, zwei Lagen
  in 5 s (-50, -53); der Rückzug im Eilgang nach einem Vorschub ist kein
  Befund mehr (-51); die Beispiel-Drehmaschine fährt Z bis −220 mm, ihr
  Revolver trägt keine Fräser mehr, die das Teil „berührt“ hätten (-52); der
  Fräser bleibt 2 mm vor dem Futter statt 1 mm (so knapp wie der
  Warnabstand). Die Frage an Manuel, wie weit das Teil aus dem Futter ragen
  soll, ist beantwortet (2026-09-29): V3f.
- *Klickweg:* Beispiel-Drehmaschine laden, Welle → Stirnfläche →
  „4-Achs-Bearbeitung“ → Stange Ø 80 → „Weiter“ → „Rundum schruppen“, T1
  Schaftfräser D12 → „Anlegen“ → im Job stehen T1 und „Rundum schruppen T1“,
  die Bahn läuft in Lagen um das Teil. „Auf der Maschine prüfen“: C dreht, das
  Werkzeug auf P1 läuft außen am Teil entlang; „Kollision prüfen“ meldet
  nichts im Teil.

**V3h – Nachträglich ändern** (Manuel, 2026-09-29, siehe „Entschieden“)

- Doppelklick auf „Rundum schruppen“ (oder Kontextmenü „Bearbeiten“, oder
  Operation bzw. Job wählen und „4-Achs-Bearbeitung“) öffnet den Assistenten
  in Schritt 2 mit Fräser, Einsatz und Werten der Operation; Felder, die dem
  Vorschlag gleichen, bleiben leer und folgen ihm. „Übernehmen“ ändert die
  Operation als einen Schritt Rückgängig: Ihr Controller bleibt, wenn der
  Fräser derselbe ist und keine andere Operation ihn benutzt (Drehzahl,
  Vorschub und Name aus dem Einsatz), sonst kommt ein neuer, und der alte geht,
  wenn ihn keine Operation mehr benutzt. Der Name „Rundum schruppen T1“ folgt
  dem Werkzeug. „Abbrechen“ ändert nichts.
  *Gebaut (P-2026-09-29-04):* Schritt 2. *(P-2026-09-29-06):* „Zurück“ zu
  Schritt 1 – Stange, Mitte, Drehlage, Längen und Rundachse, wie sie im Job
  stehen. Gemerkt wird dafür nichts Neues: `vierachs_rohteil.einstellung()`
  rechnet es aus dem Job zurück (Klon = Lage · Original, Stirnfläche bei
  a = 0, Zylinder vom Futter bis vor das Planaufmaß) – so geht es auch mit
  Jobs aus 0.26.0. Eine geänderte Stange ist ein eigener Schritt Rückgängig
  („Stange ändern“) vor „Rundum schruppen ändern“; die Rundachse aller
  „Rundum schruppen“ des Jobs zieht mit. Sieht der Job nicht mehr aus, wie der
  Assistent ihn anlegt, bleibt Schritt 1 zu, mit einem Satz.
- *Klickweg:* Operation doppelklicken → Kopf „„Rundum schruppen T1“ ändern“,
  T1 gewählt → T2 wählen, Aufmaß 0,5 → „Übernehmen“: „Rundum schruppen T2“ mit
  „T2 Schruppen“, „T1 Schruppen“ ist weg; ein Strg+Z bringt T1 zurück. Noch
  einmal doppelklicken → „Zurück“: Stange 80, Rundachse A wie im Job → Ø 90 →
  „Weiter“, „Übernehmen“: die Stange ist Ø 90, die Bahn hat mehr Lagen.

**V3f – Maschine zuerst, Ausspannlänge, Abstände** (Manuel, 2026-09-29, siehe
„Entschieden“)

- **Maschine zuerst:** Schritt 1 fragt als Erstes „Welche Maschine?“ – die
  offenen Maschinen, die gemerkte (D-20, wird geöffnet) oder „ohne Maschine“.
  Die Rundachse folgt daraus; darunter ein Satz, was die Maschine kann
  („Rundachse C, Y-Achse, Revolver mit 12 Plätzen“).
- **Überlauf:** Die Spirale läuft hinter das Teil, bis der Fräser es ganz
  verlassen hat: Überlauf = Fräserradius + 0,5 mm (Vorschlag). Im Überlauf
  bleibt die Spitze auf der Tiefe des letzten Stücks Kontur – die Kante hinten
  am Teil wird fertig. Nie näher ans Futter als der Abstand zum Futter.
- **Abstände einstellbar, mit Vorschlag:** Überlauf, Abstand zum Futter
  (Vorschlag 5 mm, vom Rand des Fräsers bis zur Spannfläche) und
  Sicherheitsabstand (2 mm über der Stange) in Schritt 2 und als Eigenschaften
  der Operation.
- **Ausspannlänge:** Die Stange ragt so weit aus dem Futter, dass Teil,
  Überlauf, Fräser und Abstand zum Futter Platz haben: Planaufmaß + Teil +
  größeres von Abstechbreite und (Überlauf + Fräserradius + Abstand zum
  Futter) – der Überlauf zählt bis zur Mitte des Fräsers, zum Futter hin kommt
  sein Radius dazu (Manuel: „bauteil + fräser + sicherheitsabstand“). Schritt 2
  sagt es als Satz („Die Stange muss 78,5 mm aus dem Futter ragen: …“) und
  legt die Stange so lang an; der Nullpunkt folgt wie bisher aus der
  Spannlänge.
  *Gebaut (P-2026-09-29-07):* Überlauf, Abstand zum Futter,
  Sicherheitsabstand und Ausspannlänge. Die Stange zieht nach, wenn Fräser
  oder Abstände sich ändern (ein kleinerer Fräser: kürzer); ohne „Rundum
  schruppen“ reicht die Abstechbreite. Die Abstechbreite steht dafür am Job
  (`CamAddonAbstechbreite`, ausgeblendet), damit „Ändern“ sie von der Lücke
  unterscheiden kann. Operationen aus 0.26 bekommen beim Laden Überlauf
  Radius + 0,5 und Abstand 2 mm – ihre Bahn bleibt, wie sie war.
- *Klickweg:* Welle 60 mm lang, „4-Achs-Bearbeitung“ → oben „Maschine“:
  Beispiel-Drehmaschine → „Weiter“ → T1 D12: grau „Überlauf 6,5“, „Abstand zum
  Futter 5“, darunter „Die Stange muss 78,5 mm aus dem Futter ragen …“ →
  „Anlegen“: Die Bahn endet 6,5 mm hinter dem Teil, die Stange ist 108,5 mm
  lang (30 im Futter).

**V3g – Rohteil und Fertigteil in der Simulation** (Manuel, 2026-09-29)

- Im Prüffenster wird die Stange beim Abspielen abgetragen: ein Zylinder aus
  Radien über (Länge, Winkel), 0,5 mm × 1°; je Station nimmt der Fräser weg,
  was in seiner Stirn liegt (`restmaterial.py`, numpy). Vor- und
  Zurückspringen rechnet ab dem Anfang neu.
- Am Ende der Vergleich mit dem fertigen Teil in Farben: grün bis Aufmaß
  + 0,1 mm, gelb darüber, rot ab 1 mm zu viel, blau im Teil (mehr als
  0,05 mm). Dazu ein Satz: „Am Ende bleiben 0,30 … 0,45 mm auf dem Teil,
  nirgends ins Teil.“
- Nur für Jobs mit runder Stange und Rundachse; für 3-Achs-Jobs bleibt der
  CAM-Simulator von FreeCAD.
- *Klickweg:* Job aus V3f → „Auf der Maschine prüfen“ → Abspielen: Die Stange
  wird unter dem Werkzeug dünner; am Ende grün mit dem Satz.

**V4 – Flächen wählen** (bisher V3)

- Schritt „Flächen“ mit Punkt-Hüllfläche, Erreichbarkeit und Farben; ohne
  Auswahl gilt das ganze Teil.
- *Klickweg:* „Flächen …“ → „Alle Mantelflächen“ → die Flächen rundum sind
  markiert und grün, die Stirnflächen nicht; eine Fläche unter einem Überhang
  steht rot mit „nicht erreichbar“; ein Klick nimmt eine Fläche heraus.

**V5 – Schlichten** (bisher V7)

- Hüllfläche für Kugel- und Torusfräser, zweite Operation, Kammhöhe, Linien
  längs.
- *Klickweg:* dazu „Rundum schlichten T2“ – die Bahn liegt dicht auf der
  Oberfläche, und Schrittweite 0,35 mm zeigt „Kammhöhe 5 µm“.

**V6 – Glatte Bahn** (bisher V8)

- Glättungsfilter, Punktabstand nach Toleranz.
- *Klickweg:* „Mehr …“ → Glättung aus und an: Mit Glättung hat die
  Schlichtbahn deutlich weniger Sätze und keine Stufen; die Abweichung bleibt
  unter 0,005 mm.

**V7 – Feinschliff** (bisher V9)

- Luftschnitte überspringen, Zeit je Operation, zweiter Durchlauf auf
  demselben Job, Warnung „Modell im Job verändert“, Gleich- oder Gegenlauf.
- *Klickweg:* Schritt 4 zeigt die Zeiten; ein zweiter Durchlauf auf dem Job
  beginnt bei Schritt 2.

## 14. Prüfbarkeit

- **Rechnung ohne Fenster** (FreeCADCmd, beide Versionen):
  - Körper, deren Ergebnis man ausrechnen kann: Quader, Sechskant, Zylinder,
    Exzenter, Kugel.
  - Die Hüllfläche je Fräser gegen die Formel, die Zahl der Lagen, die
    Kammhöhe.
  - Eine Zeitgrenze für die Rechnung.
  - Die Operation im Job: Speichern, Laden, Neuberechnen, Ausgabe des
    Postprozessors.
- **Oberfläche:** Szenarien klicken den Assistenten durch und machen
  Screenshots. Ob man ihn ohne Erklärung versteht, prüft Manuel.

## 15. Vorschläge (Claude, zur Besprechung)

1. **a = 0 an der gewählten Stirnfläche**, das Teil bei a ≤ 0 – wie Z0 an der
   Drehmaschine.
2. **Vorschläge:** Planaufmaß 1 mm, Abstechbreite 3 mm, Spannlänge 30 mm,
   Schlichtaufmaß 0,3 mm; Toleranz 0,02 mm beim Schruppen und 0,005 mm beim
   Schlichten; Glättung an. Alles einstellbar.
3. **Mitte:** die runde Fläche, wenn das Teil so passt – sonst das ganze
   Teil (Abschnitt 5).
4. **Spirale von vorne Richtung Futter, Gleichlauf** – das Teil bleibt am
   Futter am längsten steif.
5. **numpy statt OpenCamLib** – numpy ist in jeder FreeCAD-Version dabei,
   OpenCamLib nicht.
6. **Vorschub G93** (Abschnitt 9), umstellbar unter „Mehr …“.
7. **Winkel fortlaufend**, nur bei endloser Rundachse.
8. **Drehrichtung** wie FreeCADs Anzeige (das Werkstück dreht,
   Rechte-Hand-Regel) bzw. wie das Gelenk der W-001-Maschine.
9. **X als Radius**; Durchmesser nur über den Programmkopf (Abschnitt 12).
10. **Jeder Durchlauf legt einen neuen Job an**; ein zweiter Durchlauf auf
    einem Job des Assistenten beginnt bei Schritt 2 (V9).

## Entschieden

Alle von Manuel, 2026-09-26, P-2026-09-26-78 – aus Fragen mit Optionen bzw.
als Rückmeldung zum Plan:

- **Rechenweg:** eigener Rechenkern im Addon – nicht FreeCADs „Rotary
  Surface“ (nur Wochen-Build, experimentell, nur A/B) und nicht beides.
- **Erster Umfang:** rundum simultan (Schruppen und Schlichten der gewählten
  Mantelflächen bei drehender Rundachse); indexiert 3+1 später.
- **Achse:** „am besten von der Maschine, ansonsten dreht sich das Rohteil …
  und so auch das Bauteil, und dem muss man eine Achse zuweisen“ → aus der
  W-001-Maschine, sonst weist man der Stange A, B oder C zu (Abschnitt 4).
- **Aufbau:** Assistent in vier Schritten in einem Aufgabenfenster; ein
  zweiter Durchlauf auf demselben Job überspringt das Rohteil.
- **Maschine egal:** „Es gibt Achsen, und die Punkte müssen halt via
  Koordinate im G-Code 0,001 mm nach und nach angefahren werden … oder halt
  mit einem Glättungsfilter.“ → Ausgabe als reine Achskoordinaten, keine
  Frage nach der Steuerung (Abschnitt 9).
- **Alles einstellbar, Vorschläge als Standard:** „Abstechbreite kann man ja
  einstellen … so dass alles einstellbar ist, aber mit Vorschlägen als
  Standard“ (Abschnitt 11).
- **Reihenfolge:** V1 gleich nach dieser Spezifikation; Schritt 7 der schrägen
  Achse (Vorlage) danach.
- **Rückmeldung zum Test (2026-09-27):** „effektiv werden runde Teile immer so
  eingespannt das der Mantel paralell zum Futter ist und nicht so wie das
  koordinaten system vom rohteil ist … oder irgendwie dem benutzer beim
  erstellen des rohteils mit inbegriffenen bauteil die möglichkeit geben
  „klick auf die fläche wo z senkrecht drauf steht“ … wenns eine
  rotatiosn geometrie ist beim 4 achs bearbeiten … irgendwie sinnvoll“ →
  V2 in drei Schritten V2a–V2c (Abschnitt 13), als Nächstes.
- **Nach dem Rohteil gleich die Bahn (2026-09-27):** „wäre cool wenn dann
  einfach ein fenster aufgeht .. was willste machen .. schruppen .. wir haben
  ja extra einen 4achs job erstellt .. also geht man ja davon aus das man 4
  achsen bearbeiten will“ → V3 „Rundum schruppen“ vor dem Flächenwählen
  (Abschnitt 13). Dazu: „hier bewegt sich nun in der simulation das werkzeug
  das zur z achse senkrecht steht mittig am pfad entlang .. und kollision wird
  hier auch nicht erkannt da er komplett durchs werstück fährt“ → Hinweis zur
  Werkzeuglage (P-2026-09-27-43), Kollision „ins fertige Teil“
  (P-2026-09-27-41), Prüffenster ohne TCPM (V3e).
- **Ausspannlänge und Abstände (2026-09-29):** „wenn das bauteil 30 mm lang
  ist .. und du sagst ‚ja maximal bis 33 mm in z minus darfst du fahren mit
  deinem 12er fräser‘ dann ist das nicht schlau .. weil dann wird dein bauteil
  nicht fertig bearbeitet werden ... da muss man schon mindestens mal 6.5
  drüber fahren damit es kontur fertig ist ... und dann braucht man noch einen
  sicherheits abstand zum futter ... also am sinnvolsten ist .. man macht das
  bauteil + fräser + sicherheitsabstand .. und sagt dem benutzer auch ‚hey so
  lange muss es ausgespannt sein das rohteil‘“ – „alle abstände zu was auch
  immer müssen einstellbar sein aber mit einem standartwert der sinnvoll ist
  gefüllt werden“ → V3f.
- **Maschine zuerst (2026-09-29):** „vll sollte man als erstes die abfrage
  machen ‚hey was hast du für ne maschine‘ nachdem man ausgewählt hat was man
  bearbeiten will … der prozess soll extrem einfach werden“ → V3f.
- **Rohteil und Fertigteil (2026-09-29):** „haben wir eine rohteil und
  fertigteil vergleich in der ‚simualtion‘“ → V3g.
- **Nachträglich ändern (2026-09-29):** „so wenn ich jetzt hier nochmal
  schnittwerte ändern will oder anders werkzeug komme ich nicht mehr in die
  maske rein ... das ist auch nicht optimal muss irgendwie gelöst werden das
  man im nachhinein noch sachen ändern kann“ → V3h.
- **Y-Achse (2026-09-29):** „bei einer maschine mit y achse kann man ja auch
  diese verfahren um eventuelle stellen besser zu erreichen“ → mit V4/V5:
  Flächen, die ein Werkzeug durch die Achse nicht erreicht (ebene Flächen,
  Hinterschnitte seitlich), fährt es mit Y versetzt; bis dahin gilt Y = 0.
