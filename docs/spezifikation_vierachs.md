# Spezifikation W-003: 4-Achs-Bearbeitung am runden Rohteil

Stand: **Entwurf von Claude mit Manuels Entscheidungen** vom 2026-09-26
(P-2026-09-26-78, am Ende unter „Entschieden“). Die Vorschläge in
Abschnitt 15 hat Claude getroffen; sie sind zur Besprechung da. Gebaut wird
Stufe für Stufe (Abschnitt 13), jede ein Patch mit Klickweg – V1, V2a, V2c
und V3 („Rundum schruppen“ mit V3f–V3h) sind gebaut, als Nächstes V5 „Rundum
schlichten“ (Manuel, 2026-09-30).

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

**FreeCADs Postprozessoren** (P-2026-09-30-36, auf Manuels Frage „Funktionieren
die so wie wir das hier bauen??“; geprüft mit 1.1.3 und 26.3, dieselbe
Operation durch jeden): LinuxCNC, Mach3/Mach4, Masso G3, Generic (26.3),
KineticNC/Beamicon2, Estlcam, Dynapath 4060 – G93, G94, C und F in jedem
Vorschubsatz, Werte wie in der Bahn (grbl, Marlin, RRF, JTech geben es auch so
aus, deren Steuerungen kennen meist weder C noch G93). Fanuc und UCCNC lassen
ein F weg, das gleich dem vorigen ist (rund 380 von 5 482 Sätzen) – deshalb
folgen nie zwei gleiche aufeinander: Das zweite bekommt eine Einheit der 6.
Nachkommastelle mehr, so genau speichert FreeCAD die Bahn (P-2026-09-30-39,
Manuel: „Es muss ja für alle funktionieren“); `test_vierachs_operation` prüft
LinuxCNC, Mach3/Mach4, Fanuc und UCCNC ohne Optionen. Centroid, Smoothie, Fablin, Philips lassen C weg, Fangling F;
Heidenhain bricht in beiden Versionen ab (FreeCAD-Fehler), OpenSBP kennt G93
erst neu in 26.3. **Drehmaschine:** Die Postprozessoren schreiben `M3 S…` –
das ist dort die Hauptspindel; angetriebenes Werkzeug und C-Achsbetrieb
gehören in den Programmkopf (Siemens `SETMS(…)`). Bei Fanuc-Drehmaschinen im
G-Code-System A ist G94 ein Plandrehzyklus, Vorschub je Minute heißt G98 –
offen, ob die Operation das je Maschine anders schreiben soll (Frage an
Manuel, welche Steuerung er hat).

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
  (Achse steht, eben gefräst: Taschen) – eine spätere Stufe. Querbohrungen und
  Passfedernuten fräst inzwischen „Plan indexiert“ (W-006, P-2026-10-02-05/-07); mit einem
  Bohrer ihres Durchmessers bohrt es die Querbohrungen radial (P-2026-10-02-08), Nuten auf
  dem Mantel fräst es mit drehender Rundachse (P-2026-10-02-09).
  Im Wochen-Build helfen dafür FreeCADs Arbeitsebenen. Ebene Abflachungen
  parallel zur Achse fräst V4c („Plan indexiert“).
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
  vor dem Teil schneidet es die Lage. ~~Der Achse kommt die Spitze nicht näher
  als der Fräserradius.~~ Seit P-2026-10-03-07 folgt sie der Hüllfläche auch
  über die Drehmitte hinaus (r < 0, auf der Drehmaschine X unter null;
  `Schruppwerte.r_tiefste` begrenzt es für eine Maschine, die das nicht kann),
  und die Hüllfläche sieht auch das Teil hinter der Achse (vierachs_huelle:
  die Filter „x > 0“ an Kanten, Ecken und Dreiecken sind weg). Trifft die
  Stirn rundum nichts, reicht die Spitze bis zur Achse (hinter dem Teil bleibt
  sie oben). Ein Fräser mit runder Stirn rechnet mit seiner Form (`form`),
  nicht mehr wie ein Schaftfräser – der ließ auf einer schrägen Fläche bis
  0,6 R stehen. Grund: Manuels Teil (`beispiele/test4achsbearbeitung.FCStd`),
  das neben der Achse liegt: Um die Achse blieb ein Kern Ø 2 R („Hubbel“), auf
  der Fläche unter der Mitte eine Wulst; das Schlichten holte beides in sieben
  Vorstufen mit 0,2 mm je Umdrehung (135 min, mittig beginnend). Jetzt:
  Schruppen 9 Lagen bis −4,7, 30,6 min (statt 7 Lagen, 24,9), Rest überall
  ≤ 0,7 mm außer in den Keilen des Rasters; Schlichten 90 min, beginnt vorne.
  Zwischen den Lagen radial hinaus auf Stangenradius
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
  *Gebaut (P-2026-09-29-09):* gleich unter „Teil“ die Liste „Maschine“ –
  offene Maschinen (vorgewählt die erste mit einer Rundachse für die Stange),
  die zuletzt benutzte als „„…“ öffnen (zuletzt benutzt)“ (öffnet sich beim
  Wählen, die Ansicht bleibt beim Teil), eine ohne passende Rundachse grau,
  „ohne Maschine“. Darunter „Linearachsen X1, Y1, Z1 · Rundachse für die
  Stange: C · 12 Werkzeugplätze“; die Liste „Rundachse“ zeigt nur die
  Achsen der gewählten Maschine (eine: nicht wählbar), ohne Maschine A, B, C.
  Der Job merkt sich die Maschine (wie D-20), „Auf der Maschine prüfen“ nimmt
  sie. Beim Ändern steht die Maschine gewählt, deren Achse die Operation
  hat.
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
  *Nachtrag (P-2026-09-30-14, W-002 Stufe E3a):* Reicht der Halter seitlich
  weiter über die Werkzeugachse als der Fräser (der Kopf von „VDI30 angetrieben
  radial“: 27,5 mm), zählt zum Futter hin er – in Ausspannlänge („Halter über
  die Werkzeugachse 27,5“) und Bahn; die Operationen merken es sich als
  „HalterZumFutter“.
- **Kugel- und Torusfräser** (Manuel testete 2026-09-29 einen „Rundfräser“):
  „Rundum schruppen“ rechnet mit der Stirn als flacher Scheibe – für diese
  Fräser sicher, das Teil wird nicht verletzt. Ein grauer Satz sagt, wie hoch
  zwischen den Bahnen Rillen stehen bleiben (Rundung gegen halben Vorschub je
  Umdrehung). *Gebaut (P-2026-09-29-08).*
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
- *Gebaut (P-2026-09-29-11):* `restmaterial.py` – `Stange` (Radien über
  a × φ, 0,5 mm × 1°; ein Strahl aus der Achse trifft den radialen Fräser ab
  r / cos Δ, solange er seitlich in ihm bleibt; zwischen zwei Punkten
  Schritte von 0,5 mm am Umfang), `Abtrag` (aus der Abfahrt: die Spitze am
  gedrehten Teil je Station, nur Stationen von „Rundum schruppen“),
  `vergleiche()` (Radien des Teils im selben Raster, Farben). Im Prüffenster
  ersetzt die abgetragene Stange das durchscheinende Rohteil; an der letzten
  Station verschwindet die Bahn, die Stange steht in Farben, und unter dem
  Abspieler steht der Satz mit den Farben. Welle Ø 40 aus Ø 50 (Test): 0,2 s
  Abtrag, 0,1 s Vergleich, Rest 0,325 … 0,331 mm, alles grün.

**V4 – Flächen wählen** (bisher V3)

- Schritt „Flächen“ mit Punkt-Hüllfläche, Erreichbarkeit und Farben; ohne
  Auswahl gilt das ganze Teil.
- Manuel, 2026-09-30: „Es wäre schön, wenn ich nur Flächen am Mantel anklicken
  könnte, die ich bearbeiten will … und wenn ich alle anklicke, dann wird
  komplett rings um bearbeitet.“ Dazu seine Antworten:
  - Wo keine gewählte Fläche ist: „je nach Rohteil abheben und irgendwo wieder
    einsetzen, so dass er nicht kaputt geht“ – abheben über das, was noch
    steht, und dort wieder hinein, wo es sicher ist (nicht voll ins Material).
  - Flächen, die nicht rundum gehen (Abflachung, außermittiger Zylinder):
    „mehrere Strategien, je nach Werkzeug kann das anders ausfallen“.
  - „Und Entgraten nicht vergessen.“
- Vorher (Manuel): die Richtung des Werkzeugs am Halter, die Beispielmaschinen
  und eine Durchsicht (spezifikation_halter.md, Abschnitt 11).
- *Klickweg:* „Flächen …“ → „Alle Mantelflächen“ → die Flächen rundum sind
  markiert und grün, die Stirnflächen nicht; eine Fläche unter einem Überhang
  steht rot mit „nicht erreichbar“; ein Klick nimmt eine Fläche heraus.

*Plan (Claude, 2026-09-30, nach der Durchsicht 2 – Manuel: „Egal, du musst alles
bauen“):*

- **Grundsatz:** Gerechnet wird weiter gegen das ganze Teil (Hüllfläche); die
  gewählten Flächen sind die **Maske** in (a, φ): die Stellen, an denen der
  Strahl von außen zuerst eine gewählte Fläche trifft. Ohne Auswahl oder mit
  allen Mantelflächen ist die Maske überall – rundum wie heute.
- **V4a – Flächen im Assistenten:** In Schritt 2 oben „Flächen“: „Alle
  Mantelflächen (rundum)“ vorgewählt, daneben „Im 3D anklicken …“; die Liste
  der gewählten mit Art und Erreichbarkeit (erreichbar grün, teilweise gelb,
  nicht rot – aus der Maske mit einem punktförmigen Werkzeug). Die Operationen
  merken sich die Flächen (Verweis auf das Modell des Jobs, wie CAMs „Base“).
  - *Wie gebaut* (P-2026-09-30-27): Ohne Wahl steht grau „Rundum – alle
    Mantelflächen …“. Ein Klick auf eine Fläche des Teils im Job nimmt sie dazu,
    ein zweiter heraus; danach ist FreeCADs Auswahl wieder leer, die gewählten
    Flächen stehen im 3D grün, gelb oder rot (nur die Anzeige). Die Liste: „Face3
    Ebene – erreichbar“ in derselben Farbe, Doppelklick nimmt heraus. „Alle
    Mantelflächen“ und „Auswahl leeren“ – alle gewählt ist rundum, wie keine. Die
    Operationen merken sich die Namen („Flaechen“, Liste von „FaceN“ des Modells im
    Job); die Vorschau rechnet mit ihnen, beim Ändern stehen sie wieder in der
    Liste. Der Eintauchwinkel kommt vom Fräser der Werkzeugverwaltung.
- **V4b – Maske in der Bahn, abheben und sicher wieder einsetzen** (gebaut,
  P-2026-09-30-26, mit dem Rechenkern `vierachs_flaechen`): Schruppen
  und Schlichten fräsen nur, wo die Mitte des Fräsers über der Maske steht;
  dazwischen hebt er ab – über das, was dort noch steht (anfangs der
  Stangenradius, sonst der Rest der Lagen davor) plus Sicherheitsabstand – und
  fährt in der Luft weiter. Wieder hinein geht es **nicht senkrecht ins volle
  Material**, sondern schräg längs der Bahn mit dem Eintauchwinkel aus der
  Werkzeugverwaltung (ohne Angabe 5°), so wie die Spirale ohnehin schneidet
  (Manuel: „je nach Rohteil abheben und irgendwo wieder einsetzen, so dass er
  nicht kaputt geht“).
  - *Wie gebaut:* Der Bereich ist jede Stelle, an der die Stirn des Fräsers (Scheibe
    mit seinem Radius) eine gewählte Fläche berührt – so kommt er an ihre Kanten.
    Gefräst wird in **Zeilen hin und her** (P-2026-09-30-28, Manuel zum Bild der
    ersten Fassung, einer Spirale mit Eilgängen rundum: „man kann ja auch einfach
    zurück drehen für so eine Fläche“): Jede Zeile liegt bei festem a und fährt nur
    über ihr Stück im Bereich; am Ende geht es in der Tiefe einen Schritt längs zur
    nächsten, und die Rundachse dreht zurück. Endet die nächste Zeile früher, fährt er
    auf der alten zurück bis über ihren Anfang, reicht sie weiter, erst hinüber und
    dann ganz hindurch. Abgehoben wird nur, wo die nächste Zeile nicht dort
    weitergeht (zwei getrennte Stücke). Schruppen: Zeilen im Abstand „Vorschub je
    Umdrehung“, Schlichten im Abstand der Schrittweite, vor jeder Wand eine Zeile als
    Ring. Alle Lagen fahren dieselben Zeilen: Über jeder Stelle steht dann höchstens
    die Tiefe der Lage davor, der Eilgang hinab geht bis knapp darüber. Hinein geht es
    über die Rampe mit dem Eintauchwinkel längs der ersten Zeile, hin und her, bis er
    unten ist, und auf der Zeile zurück zum Anfang – so bleibt unter der Rampe nichts
    stehen; senkrecht nur, wo nichts zu fräsen ist oder die Zeile davor dort schon
    fräste. Schlichten taucht senkrecht ein, knapp über dem Rest nach dem Schruppen.
    Die Hüllfläche rechnet das Schruppen nur über dem Bereich.
  - *Grenze:* Eine Abflachung mit der Spirale: Wo der Fräser nicht senkrecht über ihr
    steht, steht seine Stirn schräg zu ihr – an ihrem Rand bleibt etwas mehr stehen, in
    den Ecken an ihren Wänden gut 1 mm (mit Ringgang). Eben fräst sie erst „Plan
    indexiert“ (V4c).
- **V4c+ – Plan indexiert schräg und rundum angeboten** (P-2026-10-03-09; Manuel,
  2026-10-03: „die Maschine hat eine Y-Achse … man kann doch dann für dieses Stück den Winkel
  richtig stellen und die Y-Achse verfahren … dass sie im Flow eine schöne Gerade fahren kann“,
  „die Geschichte mit der Y-Achse hast du gar nicht verfolgt?“): `vierachs_planbahn.ebenen`
  nimmt Ebenen, die längs bis 30° fallen (`Ebene.steigung`, `hoehe(a)`); die Zeilen folgen der
  Fläche längs, auch unter die Drehmitte; die Spitze steht um das höher, was die schräge Stirn
  bergauf braucht (`_anheben`: R · tan α beim Schaftfräser). Ohne Schwenkachse steht die ebene
  Stirn um α schräg zur Fläche – zwischen Zeilen bleibt (R − √(R² − (s/2)²)) · tan α; darum
  zuletzt eine Schlichtlage mit `grat_zeilenabstand` (≤ 0,01 mm). Die Lagen fahren nur, wo
  über ihnen noch Material steht (`_oben_je_zeile` aus dem Rest nach dem Schruppen) – vorher
  zählte der höchste Rest im ganzen Winkelfenster, an Manuels Teil 21 Lagen durch Luft. Im
  Assistenten bietet „Plan indexiert“ rundum (alle Mantelflächen) mit Querachse die ebenen
  Mantelflächen an, ohne Haken; gesetzt, lässt „Rundum schlichten“ sie aus
  (`_schlicht_flaechen`). Manuels Teil (Kugel Ø 10 schruppt, Ø 12 plant Face4 8,5° schräg,
  Kugel schlichtet den Rest mit 0,2): Plan 9,3 min + Schlichten 52 min statt 88 min Spirale
  rundum – und die flache Seite eben bis auf 0,01 mm statt mit der Kugelspitze gefahren.
  *Für 5 Achsen und „ausweichen“:* Mit Y allein ändert sich die Richtung des Werkzeugs zum
  Teil nur mit C, also quer zur Stange; eine längs geneigte Fläche bräuchte eine Schwenkachse
  (B). Mit Y lässt sich aber der Winkel von Werkzeug und Fläche quer wählen – C auf φ_Normale
  + δ, das Y bringt das Werkzeug wieder auf den Punkt –, so schneidet eine Kugel nicht mit der
  Spitze (Schnittgeschwindigkeit 0): der Vorläufer des Anstellwinkels beim 5-Achs-Fräsen.
  Offen, als eigene Stufe zu planen.
- **V5e – Die Spirale mit der Querachse** (P-2026-10-03-18; Manuel, 2026-10-03: „mein Gedanke
  war eigentlich ein anderer: das Spiralisieren um das Bauteil herum nicht nur mit X und Z
  und C, sondern eben auch Y mitnehmen … berechnet man Drehung und Koordinaten so, dass die
  Drehung und X so passt, dass die lange Gerade exakt vom Winkel her zur Y-Achse steht, und
  man mit der Y-Achse fährt, ohne C zu bewegen, und dann wieder mit der C-Drehung anfängt …
  nur in Bereichen, wo es vom Weg her unters Drehzentrum geht … schon eine Spiralisierung,
  aber halt mit allen Achsen … ich denke, die Mitte wird's uns danken“; „das aktuell
  Vorhandene eben für Maschinen, die keine Y-Achse haben, kann man ja lassen“): Die
  Schlichtspirale wird wie bisher gerechnet (die Spitze auf dem Strahl φ, `_spirale_rechnen`)
  und dann je Punkt umgerechnet (`vierachs_bahn.normale_quer`): Die Mitte der Kugel liegt bei
  ρ = r + R auf dem Strahl; die Normale der Kurve ρ(φ) im Querschnitt hat den Winkel ψ = φ −
  atan(ρ′ ÷ ρ). Steht das Werkzeug unter ψ zum Teil (Rundachse auf ψ), liegt die Mitte quer um
  ρ · sin(φ − ψ) neben der Werkzeugachse (`Punkt.q`, das Y) und längs bei ρ · cos(φ − ψ) – die
  Spitze um R darunter (`Punkt.r`, das X). Auf dem Zylinder ist ψ = φ: die Spirale wie bisher.
  Auf einer ebenen Fläche in der Tiefe d ist ψ ihre Normale – die Rundachse hält –, die Spitze
  steht bei d, das Y läuft als (d + R) · tan(φ − ψ) über die Fläche: genau Manuels Gerade, auch
  unter die Drehmitte (an seinem Teil: die Spitze bleibt bei X = d, nichts fährt über die
  Mitte). Die Kugelmitte liegt dabei für jedes ψ genau auf der Hüllfläche – ψ bestimmt nur,
  wie das Werkzeug steht; darum geht es nur mit dem Kugelfräser (Torus und Scheibe bräuchten
  die Hüllfläche je Stellung – offen, siehe unten). ρ′ kommt aus vier Nachbarn (Fehler h⁴),
  ψ wird über ±8 Punkte geglättet (das Netz ist facettiert; die Normale einer Facettenkante
  springt um Zehntelgrad, und die Rundachse liefe zurück) – jede Glättung ist eine gültige
  Stellung. An einer Innenecke springt ψ (die Kugel liegt in der Ecke): das Werkzeug dreht
  dort um die ruhende Kugelmitte in 0,5°-Schritten. Je Ring (das Ende, vor Wänden) wird für
  sich abgeleitet; der Ring am Ende fährt das Profil des Teilendes gerade weiter wie die
  Spirale (nicht die Kugel hinter der Kante hinab – auch beim Schruppen). Zusammengefasst
  wird im Rahmen des Teils (`_zusammen_quer`): Die Maschine fährt X, Y und C zugleich
  geradlinig, die Kugelmitte läuft dabei auf Rot(ψ(t)) · (x(t) + R, q(t)) – auf der Ebene eine
  Gerade, auf dem Zylinder ein Bogen, beides genau; ein Punkt kann weg, wenn diese Kurve an
  ihm längs der Normalen höchstens 0,002 mm außen (0,0005 innen) und quer höchstens 0,5 mm
  (eine andere Stelle derselben Bahn) liegt – je Lauf das längste Stück (verdoppeln,
  halbieren). Der Weg für G93 (`_weg`) ist jetzt die Sehne im Rahmen des Teils, zum Bogen
  gestreckt, so weit die Rundachse dreht – dreht nur sie, der Bogen; fährt nur das Y, die
  Gerade (vorher: Radius · Winkel plus Komponenten, als wären sie unabhängig – bei X, Y und C
  zugleich bis sechsfach zu lang). D-Profil Ø 40, Abflachung bei 6, Kugel Ø 10, 1 mm: 19 220
  Punkte (radial 23 196), 9,3 min (radial 8,4), die Mitte überall 5,005 … 5,18 vom Teil, auf
  der Ebene ψ auf 0,000°, Spitze X = 6,005, C dreht nie zurück. Im Assistenten der Haken
  „Mit der Querachse (Y)“ unter dem Muster – vorgeschlagen, wenn die Maschine die Achse quer
  hat (`Stangenachse.quer`), das Muster die Spirale ist und ein Kugelfräser schlichtet; sonst
  gesperrt mit Grund. An der Operation die Eigenschaft `Querachse`; ohne Kugel spiralisiert
  sie wie ohne und sagt es im Ausgabefenster. „Plan indexiert“ bleibt für Maschinen, die so
  fräsen wollen. Das Prüffenster trägt den Abtrag mit dem Versatz quer ab (`restmaterial`
  kennt q seit V4c).
  *Jeder Fräser (P-2026-10-03-22; Manuel: „ja, mach weiter“):* `vierachs_quer.stellungen` – der
  Plan bleibt der der Kugel mit dem Radius des Fräsers; ein Schaft- oder Torusfräser steht mit
  seiner Achse durch dieselbe Mitte (auf einer Ebene liegt die Stirn dann flach auf, um eine
  Außenkante dreht er sich um die Kante), ψ rastet auf 0,25° ein (die Mitte bleibt, der Versatz
  folgt), die Höhe der Spitze rechnet die Hüllfläche des Fräsers in genau dieser Stellung:
  `vierachs_huelle.je_stellung` – die Kerne nehmen dafür beliebige Stellen längs (statt eines
  Rasters) und einen Versatz quer je Stelle, je Richtung rechnet ein Aufruf alle Stellungen eines
  Bands quer (2 R breit). Gleich wie `je_versatz` (Abweichung 0), an Manuels Teil 57 000
  Stellungen in 4,4 s (einzeln je Spalte waren es 57 s). Der Schaftfräser mit Aufmaß rechnet als
  Scheibe mit Radius + Aufmaß (sonst ein Torus mit Eckradius 0,005 – der teure Weg). Seitlich
  fasst `_zusammen_quer` bei ihnen nur 0,02 mm zusammen (eine verschobene Stirn läge in einer
  Kehle tiefer). Wo die Mitte im Plan springt – weiter als das Dreifache der Schritte um sie
  herum (nach einer Drehung um eine Innenecke, wo das Teil unter die Drehmitte geht) –, setzt
  `_uebergaenge` Zwischenstellungen auf die Gerade zwischen den Mitten, alle 0,05 mm, ihre Höhe
  aus der Hüllfläche (auch für die Kugel; ihre Planpunkte liegen ohnehin auf ihr). Geprüft an
  Manuels Teil mit der genauen Hüllfläche zwischen den Punkten der fertigen Bahn: Kugel R 5 bis
  0,0048 mm unter ihr (vorher 0,047), Scheibe R 6 0,0073, Torus R 5 r 1 0,0086 (mit der
  Netztoleranz 0,005 als Zugabe – ins wahre Teil wenige Tausendstel); Rechenzeit 11 / 8 / 20 s.
  D-Profil (`test_vierachs_schlichten`): Scheibe und Torus auf der Ebene C steht, Spitze 6,005,
  nirgends ins Teil. *Dabei gefunden und behoben – das Schlichten ohne Querachse:* Von der Achse
  aus gesehen steigt die Hüllfläche an den Kanten von Manuels ebener Seite um 3–4 mm je Grad
  und biegt dabei; die Gerade zwischen zwei Punkten 0,5° auseinander lag bis 0,22 mm (Kugel)
  und 0,38 mm (Scheibe) unter ihr – der Fräser schnitt ins Teil (der Sehnenfehler hob höchstens
  0,02). `vierachs_bahn._verfeinert` rechnet dort Zwischenpunkte (bis 32 je Schritt, bis
  dreimal), `_spirale`, `_zusammengefasst`, `_sehnenfehler` und `_a_knicke` rechnen mit
  ungleichen Abständen: danach 0,0024 / 0,0033 mm.
  *Schruppen (P-2026-10-03-23):* `Schruppwerte.querachse`, `vierachs_bahn._schruppen_quer` – je
  Lage der Plan der Kugel mit dem Fräserradius auf ihrer Hüllfläche mit Aufmaß (Raster 1°,
  `_hinten_gerade`, die Ringe wie rundum), die Stellungen und Höhen des Fräsers aus seiner
  Hüllfläche (`vierachs_quer.stellungen`), je Lage x ≥ `vierachs_quer.lagen_grenze`: die
  höchste Stelle der Stange unter der Stirn (quer von |q| − R) minus Lage · Zustellung – so
  schneidet keine Lage mehr als die Zustellung, auch quer versetzt (gerechnet mit der Stange,
  nicht mit dem Rest der Lage davor; die Stellungen jeder Lage liegen um den Versatz der Spirale
  anders). Mehr Lagen als rundum, solange die Grenze die letzte noch über dem Teil hält
  (höchstens 3). `vierachs_schlichten.rest_nach` rechnet den Versatz quer mit (die Stirn von
  q − R bis q + R). Manuels Teil, Ø 12, 22,2 / 5,4 / 0,3: 2 Lagen, 5,1 min (rundum 4,9), die Spitze
  überall mindestens 0,302 über der Fläche (genaue Hüllfläche zwischen den Punkten), danach
  steht fürs Schlichten höchstens 7,7 statt 11,5 mm (die Stellen unter der Drehmitte), 3,6 s
  gerechnet. Im Assistenten der Haken „Mit der Querachse (Y)“ auch unter „Rundum schruppen“ –
  nur rundum (mit Flächen fährt es Zeilen); die Vorschau rechnet ohne Querachse.
- **V4c – Strategien je Werkzeug und Fläche** (Manuel: „mehrere Strategien, je
  nach Werkzeug kann das anders ausfallen“): für jede Auswahl ein Vorschlag, im
  Assistenten änderbar –
  - *Spirale* (wie heute) – jede Fläche, jeder Fräser;
  - *Linien längs* – Schlichten mit Kugel oder Torus auf Flächen, die nicht
    rundum gehen (Abflachung, Nocke): Bahnen längs der Achse im Winkelabstand
    Schrittweite ÷ Radius, gegenläufig, nur über der Fläche;
  - *Plan indexiert* – eine ebene Fläche parallel zur Achse mit einem Fräser mit
    ebener Stirn: Die Rundachse steht fest (die Fläche zeigt zum Werkzeug), der
    Fräser fährt Zeilen wie beim Planfräsen (Zustellung ap, Zeilenabstand ae
    aus der Werkzeugtabelle).
  - *Stand 2026-09-30 abends:* Gebaut ist „hin und her“ – Zeilen bei festem a
    über den gewählten Flächen (P-2026-09-30-28), für jeden Fräser. Manuel will
    die Strategien mit planen („Wenn dann müssten wir eigene planen“); offen, zur
    Entscheidung mit ihm:
    1. *Plan indexiert* braucht eine Achse quer zur Stange (bei C das Y): Die
       Bahn bekommt dann einen Versatz quer zur Werkzeugachse – bisher steht die
       Spitze immer auf dem Strahl von der Achse (a, r, φ). Abfahren, Kollision
       und Abtrag rechnen dann mit diesem Versatz. Ohne solche Achse bleibt „hin
       und her“. Welche Maschine zuerst: Drehmaschine mit Y oder Fräse mit A?
    2. *Linien längs* – dieselben Zeilen, aber längs der Achse bei festem φ
       (Nut, Abflachung mit dem Kugelfräser): als eigene Wahl neben „hin und her“
       oder von selbst, wenn die Fläche längs schmal ist?
    3. Soll der Assistent je Fläche eine Strategie vorschlagen (Ebene + Schaftfräser
       → Plan indexiert, sonst hin und her), oder eine für alle gewählten Flächen?
  - *Stand 2026-10-01 (P-2026-10-01-06, 0.34.0):* *Linien längs* gebaut – als Muster an
    „Rundum schlichten“ (Eigenschaft „Muster“: Spirale oder Linien), für jeden Fräser;
    Linien im Winkelabstand Schrittweite ÷ größter Radius, gegenläufig, nur über dem
    Bereich, mit den Stufen nach dem Schruppen. Zu 2 und 3 nach W-006 E5 (Vorschlag mit
    Grund, änderbar): Der Assistent schlägt je Auswahl ein Muster vor – Linien längs, wenn
    die gewählten Flächen nicht rundum gehen, sonst die Spirale –, der Grund steht grau
    darunter, eines für alle gewählten Flächen (für andere Strategien je Fläche läuft der
    Assistent noch einmal). Zu 1: Plan indexiert folgt mit dem Versatz quer (Y).
  - *Stand 2026-10-01 (P-2026-10-01-08, 0.35.0):* *Plan indexiert* gebaut – eine eigene
    Operation (`vierachs_plan`, Bahn in `vierachs_planbahn`): Je gewählter ebener Fläche
    längs der Stange (Außennormale quer zur Achse, nach außen) steht die Rundachse auf dem
    Winkel ihrer Normale; Lagen in gleichen Schritten von höchstens der Zustellung von dem,
    was über der Fläche steht (die Stange, nach „Rundum schruppen“ der Rest), bis auf Tiefe
    plus Aufmaß; je Lage Zeilen längs der Achse, quer mit dem Y um höchstens den
    Zeilenabstand versetzt, der ebene Teil der Stirn bis an den Rand (Luft wie beim Ring); die
    Zeilen enden, wo die Hüllfläche gegen das Teil ohne die Fläche
    (`vierachs_huelle.je_versatz`) höher liegt als die Lage – Wände, der Zylinder daneben –,
    und über das Ende der Fläche hinaus ragt die Stirn nur, wo nichts höher steht als die
    Fläche selbst (sonst liefen in der Lage auf dem Zylinderradius die äußeren Zeilen 1,5 mm
    weiter als die mittlere, den Zylinder streifend); hin und her (`_fahrten`); hinein über
    die Rampe oder senkrecht vor der Stange. Der Punkt
    der Bahn trägt den Versatz quer (`Punkt.q`), die Befehle die Querachse, der Weg und die
    Zeit rechnen damit; der Abtrag (`restmaterial`) rechnet den Fräser dort, wo er steht (die
    Werkzeugachse aus dem Winkel der Rundachse, die Spitze quer daneben) – für Scheibe, Kugel
    und jede Stirn. Zu 1: beide Maschinen – ob es eine Querachse gibt, sagt
    `Stangenachse.quer`; ohne bleibt der Haken gesperrt, mit Satz. Der Assistent: dritter
    Haken „Plan indexiert“, vorgeschlagen mit Grund (E5), sobald eine gewählte Fläche eben
    längs der Stange liegt, mit Fräser (ebene Stirn), Einsatz „Planen“, Zustellung je Lage,
    Zeilenabstand, Aufmaß; „→ 2 Lagen, 6 Zeilen, etwa 1 min“; nachträglich ändern wie die
    anderen, „dazu“ beim Ändern von „Rundum schruppen“. Rundum schruppen und schlichten
    arbeiten weiter auf allen gewählten Flächen – auch der ebenen; wer die Ebene nur planen
    will, wählt sie allein. Nicht dabei: der Rest nach „Plan indexiert“ fürs Schlichten (es
    nimmt nur die Schruppbahnen).
- **V4d – Entgraten** (Manuel: „Und Entgraten nicht vergessen“): eigene
  Operation „Rundum entgraten“ – an den Kanten der gewählten Flächen (auch
  zwischen ihnen und dem Rest) eine Fase mit dem Fasenfräser (oder dem
  Kugelfräser als Kantenbruch), Breite einstellbar (Vorschlag 0,3 mm); der
  Fräser folgt der Kante, die Rundachse dreht mit.
  - *Stand 2026-10-01 (P-2026-10-01-12, 0.36.0):* gebaut – Operation
    `vierachs_entgraten`, Bahn in `vierachs_entgratbahn`. Kanten (`kanten()`): jede
    Kante, an der eine gewählte Fläche mit einer anderen um mindestens 10° nach außen
    knickt (Probe neben der Kante im Körper: `isInside`), einmal; keine Innenkante, keine
    Naht, keine tangentiale Rundung, keine Kante auf den Stirnen (vorne nimmt sie das
    Planen, hinten das Abstechen). Bahn: je Punkt der Kante (alle 0,25 mm) steht die
    Rundachse auf ihm, die Spitze sinkt auf dem Strahl bis zur Berührung (Hüllfläche
    `je_winkel` mit der Fräserform gegen das ganze Teil) und um die Eindringtiefe tiefer –
    die Fasenbreite, beim Kugelfräser so viel, dass der Kantenbruch so breit wird;
    liegt die Berührung mehr als 0,05 mm über der Kante (Schatten: Absatz, enge Nut) oder
    die Stelle hinter dem Futterabstand, fällt der Punkt weg, eine Kante ohne Punkte
    zählt als „Ausgelassen“. Stücke werden zum nächsten verkettet, ohne Abheben, wo eines
    beginnt, wo das vorige endet (eine Abflachung mit Wänden: einmal herum); ein Ring
    rundum ist eine Umdrehung; zusammengefasst, höchstens 90° je Satz. Der Abtrag lässt
    der Operation die Fase durch (`Abtrag.fasen`: so tief darf es an den getroffenen
    Zellen ins Teil, ohne blau zu werden); die Kollisionsprüfung erlaubt ihr das Teil
    (`INS_TEIL_ERLAUBT`). Assistent: vierter Haken „Rundum entgraten“ mit Fräser (Fasen-
    oder Kugelfräser), Einsatz „Fasen“, Fasenbreite; vorgeschlagen mit Grund (E5), sobald
    es Außenkanten und einen Fasenfräser gibt – mit nur einer Kugel bleibt der Haken aus,
    der Satz sagt, wie es ginge; „→ 2 Kanten, etwa 1 min“; nachträglich ändern wie die
    anderen, „dazu“ beim Ändern von „Rundum schruppen“. Dabei: „Plan indexiert“ wird nur
    noch vorgeschlagen, wenn es einen Fräser mit ebener Stirn dafür gibt. Offen: Die
    Fase mit dem Fräser auf dem Strahl ist an schrägen Kanten (Flanke einer Nut, 143°
    an der Abflachung) keine gleichschenklige Fase, sondern eine Kerbe von etwa der
    Breite – zum Entgraten genug; für eine maßhaltige Fase bräuchte es die Werkzeugachse
    auf der Winkelhalbierenden (5 Achsen, 4.4).
- **V4e – Prüfen** (Farben gebaut, P-2026-09-30-32 – haben alle Rundum-Operationen
  gewählte Flächen, vergleicht der Abtrag nur auf ihnen, Blau gilt überall; Szenario
  `szenario_flaechen_pruefen`)**:** Farben nur auf den gewählten Flächen; was nicht gewählt ist,
  bleibt Stange und zählt nicht als „zu viel stehen geblieben“. Szenario auf
  der Beispiel-Drehmaschine: Welle mit Abflachung – nur die Abflachung gewählt,
  „Plan indexiert“, Entgraten; alle Mantelflächen gewählt – wie rundum.

**V5 – Rundum schlichten** (bisher V7; Manuel, 2026-09-30, vor V4 – siehe
„Entschieden“)

„Rundum schlichten“ fährt nach dem Schruppen eine Spirale auf dem Teil: Die
Spitze folgt der Hüllfläche des Schlichtfräsers – mit seiner echten Form –
plus Aufmaß (Vorschlag 0). Werkzeug, Einsatz und Schnittwerte kommen wie beim
Schruppen aus der Werkzeugverwaltung, die Schrittweite aus der
Werkzeugtabelle (ae des Einsatzes). Schritt 2 bekommt einen zweiten Haken;
die Abstände gelten für beide.

- **V5a – Fräserform** (`camaddon/fraeserform.py`, neu; Hüllfläche in
  `vierachs_huelle.py`). Jeder Fräser als Drehprofil von der Spitze aus:
  ebene Scheibe (Radius r0), Eckrundung (rc), darüber ein Kegel oder – beim
  Radienfräser – eine hohle Rundung:
  - Schaft-, Nuten-, Plan- und Schwalbenschwanzfräser: Scheibe D/2 (was
    darüber schmaler wird, trifft von außen nichts zuerst).
  - Kugel- und Lollipopfräser: Kugel D/2; Torusfräser: Scheibe D/2 − rc,
    Rundung rc.
  - Konikfräser: Kugel mit dem Spitzen-Ø, darüber der Kegel mit dem
    Kegelwinkel bis zur Schneidenlänge.
  - Fasenfräser: Scheibe mit dem Spitzen-Ø, Kegel mit dem halben
    Spitzenwinkel bis D.
  - Radienfräser: Scheibe mit dem Spitzen-Ø (Führung), darüber die hohle
    Rundung mit dem Profilradius bis D.
  - Form- und Gewindefräser: Die Form kennt das Addon nicht – nicht zur Wahl,
    ein Satz sagt es.

  Hüllfläche gegen das Netz: gegen Ecken genau (Höhe des Profils in ihrem
  Abstand), gegen Dreiecke genau über die konvexe Hülle des Profils (der
  Berührpunkt liegt, wo die Normale des Profils die des Dreiecks trifft),
  gegen Kanten genau für Scheibe und Kugel, sonst die Kante in Punkte
  unterteilt, so fein, dass der Fehler unter der Toleranz bleibt. Gerechnet
  wird je Winkel auf einem beliebigen gleichmäßigen Raster längs – beim
  Schlichten genau an den Stellen, an denen die Spirale vorbeikommt: kein
  Rasterfehler längs. Das Schruppen rechnet weiter mit der Scheibe.
  Prüfung: Zylinder, Kugel, Absatz mit Kugelfräser (die Kehle mit R bleibt),
  Kante, Kegel und Torus gegen die Formel; eine Zeitgrenze.
  *Gebaut (P-2026-09-30-02):* `fraeserform.py` mit Stücken EBEN, BOGEN, HOHL,
  GERADE; Aufmaß als Versatz des Profils (Ecken werden zu Bögen); Kanten für
  Scheibe und Kugel geschlossen, für die anderen der goldene Schnitt (längs
  einer Kante ist die Höhe konkav). Abweichung: Die Hohlkehle des
  Radienfräsers rechnet als Sehne – Unterteilen kostete über 70 s, und
  schlichten soll er nicht; er bleibt höher, das Teil sicher. Geprüft gegen den
  dicht abgetasteten Umriss von Absatz, Kugel und Sechskant (höchstens
  0,002 mm Abweichung); Kugelfräser auf der Welle mit Nocken, 0,5° × 0,35 mm:
  223 200 Punkte in 0,5 s (Torus 2 s, Konik 4 s).
- **V5b – Bahn** (`vierachs_bahn.schlichten`): eine Spirale mit der Steigung
  Schrittweite, von vorne – der Fräser vor der Stange – bis zum Überlauf
  hinter dem Teil; die Spitze auf Hüllfläche plus Aufmaß. Punkte je 0,5°
  rundum; wo die Bahn sich zwischen zwei Punkten nach außen wölbt (an
  Rundungen des Fräsers), hebt sie sich um den Sehnenfehler – er geht ins
  Aufmaß, nie ins Teil. Gerade Stücke fasst sie zusammen.
  - Vor dem Teil bleibt die Spitze auf der Höhe der ersten Kontur, hinten auf
    der letzten (wie beim Schruppen); nie näher ans Futter als der Abstand
    zum Futter.
  - Schutz: Schlichten nimmt höchstens das Aufmaß des Schruppens plus 0,5 mm.
    Wo mehr stehen blieb – eine enge Stelle, in die der Schruppfräser nicht
    kam –, bleibt es stehen, und ein Satz sagt wo und wie viel. Was das
    Schruppen stehen ließ, rechnet es aus den „Rundum schruppen“ des Jobs
    (Hüllfläche ihres Fräsers, rundum und längs um seinen Radius
    ausgebreitet). Ohne „Rundum schruppen“ im Job geht Schlichten nicht –
    mit einem Satz.
  - Kammhöhe aus der Form des Fräsers: h = rc − √(rc² − (s/2)²), solange
    s/2 ≤ rc (beim Kugelfräser rc = R); darüber zählt die Scheibe dazwischen.
  - Prüfung: Welle mit Absatz und Kugel – Rest höchstens Kammhöhe plus
    Toleranz, nirgends ins Teil; enge Nut – bleibt stehen, mit Satz;
    Zeitgrenze.
  - *Gebaut (P-2026-09-30-03):* `vierachs_bahn.schlichten` mit
    `Schlichtwerte` und `Schlichtbahn`. Vernetzt wird fürs Schlichten auf
    0,005 mm, gerechnet mit dem Fräser um Aufmaß und Vernetzung größer (quer zur
    Fläche genau, auch an steilen Flanken). Abweichung vom Plan: Der Schutz
    lässt Schlichten bis zum Radius des Schlichtfräsers tief schneiden
    (mindestens Aufmaß + 0,5 mm) – nach dem Schruppen mit dem Schaftfräser
    stehen auf schrägen Flächen Stufen bis Vorschub je Umdrehung × Steigung
    der Fläche; mit nur Aufmaß + 0,5 mm blieben die auf jedem Kegel stehen.
    Der Sehnenfehler hebt einen Punkt höchstens um 0,02 mm: An einer Wand
    springt die Hüllfläche, dort dringt die Gerade nur um Tausendstel längs
    ein. Welle mit Absatz, Kugel Ø 6, 0,35 mm: 36 966 Punkte in 1,1 s; Welle
    mit Nocken 1,3 s.
  - *Geändert (P-2026-09-30-06):* Was mehr als die Grenze stehen blieb, bleibt
    nicht mehr stehen. Schlichten nimmt es vorher in Stufen ab, von oben nach
    unten – jede höchstens die Grenze unter der davor (die erste unter dem
    Rest) –, bis nur das Schlichten übrig ist. Eine Stufe fährt die Spirale
    nur, wo sie etwas zu tun hat: nötige Stellen, die höchstens eine Umdrehung
    auseinanderliegen, am Stück; dazwischen Eilgang über der Stange, die
    Rundachse dreht nur vorwärts. Eingetaucht wird in der Umdrehung vor der
    ersten nötigen Stelle dort, wo am wenigsten Material steht. Grund: Die
    Schruppspirale lässt in jeder Innenecke Keile bis zur Höhe des Absatzes
    stehen (sie rückt je Umdrehung den Vorschub vor, der Fräser kommt nur
    zwischen zwei Umdrehungen ganz an die Wand) – stehen lassen hieße, an
    jedem Absatz nachzuarbeiten. An der Operation steht „Vorstufen“ statt
    „Bleibt stehen“, ein Satz im Ausgabefenster nennt ihre Zahl. Welle mit
    Nut 8 mm (der Schruppfräser Ø 12 kommt nicht hinein): Kugel Ø 6 fährt
    eine Stufe auf 17,3 mm, nur über dem Grund der Nut, und taucht am Rand
    ein, wo die Wand sie über 18,2 mm hebt; Kugel Ø 2 fährt fünf, 19,3 bis
    15,3 mm. Welle mit Absatz im Assistenten: 3 Stufen, 403 statt 365
    Umdrehungen. *P-2026-10-03-07:* Die Vorstufen fahren mit dem Fräserradius
    je Umdrehung statt mit der Schrittweite (sie sind Schruppen mit dem
    Schlichtfräser; an Manuels Teil 7 Stufen in 70 statt 1400 Umdrehungen),
    die Spirale danach nimmt die Rillen. Der Rest nach dem Schruppen kommt
    nicht mehr aus `restmaterial.Stange` (ein Außenradius je Strahl – der
    kennt keinen Kern an der Achse, der weg ist, und keine Fahrt über die
    Mitte), sondern aus jeder Richtung aus den Schruppbahnen selbst
    (`vierachs_schlichten.rest_nach`: Spitze plus Form zwischen den
    Umdrehungen). Die Keile, die das Raster des Schruppens (1°, höchster
    Nachbar) an steilen Stellen lässt – bis 9 mm, wo die Fläche von der Kante
    gesehen 2–3 mm je Grad fällt –, sind echt; sie nehmen die Vorstufen.
    *Zurückgenommen (P-2026-10-03-17; Manuel, 2026-10-03, an seinem Teil:
    „warum fährt der beim Schlichten … nicht einfach einmal wie beim Schruppen
    auch, sondern (übertrieben) 100 mal dieselbe Bahn … der fährt da einmal
    durch und dann nochmal und fängt mal in der Mitte an … einfach
    spiralisiert, mit einer seitlichen Zustellung von der Angabe … das mit dem
    Mehrfach-Spiralisieren beim Schlichten und mittig anfangen muss raus“):*
    Keine Vorstufen mehr. Schlichten ist eine Spirale von vorne nach hinten
    mit der Schrittweite; was das Schruppen stehen ließ, nimmt sie in einem
    Zug. An der Operation steht „Rest höchstens“ (`Schlichtbahn.rest_ueber`),
    ist es mehr als Aufmaß + 1 mm, sagt es das Ausgabefenster. Die Vorstufen
    an Manuels Teil kamen zudem aus einem Fehler: `rest_nach` kannte nur das
    Längsprofil des Schruppfräsers auf dem Strahl seiner Spitze – der
    Schaftfräser Ø 12 schien auf der ebenen Fläche R · tan δ (bis 6 mm) stehen
    zu lassen, was er längst weg hatte. Jetzt zählt die ganze Stirn, längs und
    quer (je Spalte des Rasters der Radius (r + h) ÷ cos δ, nur zur eigenen
    Seite der Achse – jenseits wäre es ein Kern, den ein Außenradius je Strahl
    nicht kennt). Dasselbe gab „Plan indexiert“ Lagen in der Luft (Manuel: „es
    ist keine ‚Was ist schon bearbeitet‘-Prüfung vorgeschaltet … arbeitet hier
    in der Luft“): Seine Lagen beginnen jetzt an dem, was wirklich über den
    Zeilen steht (`_oben_je_zeile`, längs genau um den Radius), nicht am
    Höchsten im Sektor (den Flanken des Zylinders) – D-Profil, Ø 12 schruppt:
    4 statt 9 Lagen. Außerdem endet jede Spirale (Schruppen je Lage,
    Schlichten) mit einer Umdrehung als Ring an ihrem Ende: Sonst hört sie
    mitten in der Umdrehung auf, und das gerade Stück zum Abstechen (P-08) war
    ein Schraubenstück mit der Steigung der Spirale – die Welle Ø 60 zeigte
    hinten 1,2 mm Rest über dem Schlichten statt 0,3.
    *Offen:* das Schruppen an steilen Stellen feiner rechnen; das Prüffenster malt den
    Abtrag weiter mit `restmaterial.Stange` – es kennt keine Fahrt über die
    Mitte (die Spitze zählt dort als 0); hinten das
    Teilende: der Überlauf fräst die Kante fertig und schneidet dabei neben
    einem dünnen Ende tief ein – Manuel (2026-10-03): „auf ner Drehbank kann
    man das abstechen … das Bauteil ist instabil geworden, weil hinten so viel
    weg ist“. *Gebaut (P-2026-10-03-08), nach Manuels Antwort („nach dem Teil
    einfach noch die Abstechlänge als gerades Stück weiter … wenn da eine Gerade
    ist, wo es mit der kompletten Schneide auftrifft, verläuft das [Stechschwert]
    nicht so extrem“):* Hinter dem Teil fährt die Spitze je Winkel die Tiefe am
    Teilende gerade weiter (Schruppen `_hinten_gerade` wie Schlichten
    `_auffuellen`; eine Kugel rollte dort hinter der Kante bis zu ihrem Radius
    tiefer), und der Überlauf ist jetzt Abstechbreite + 0,5 mm statt
    Fräserradius + 0,5 – das gerade Stück fürs Stechschwert, dahinter bleibt das
    Material, das das Teil hält. Die Kante hinten ist fertig, sobald die Mitte
    das Teilende erreicht.
- **V5c – Operation** „Rundum schlichten T2“
  (`vierachs_operation.RundumSchlichten`, der Name bleibt in jeder Datei):
  Eigenschaften Schrittweite, Aufmaß, Überlauf, Abstand zum Futter,
  Sicherheitsabstand, dazu Kammhöhe und Umdrehungen zum Lesen. „Schnittwerte in
  den Job“ kennt sie (Einsatz „Schlichten“). Prüfung wie V3c: in beiden
  Versionen anlegen, Speichern und Laden, Ausgabe des Postprozessors.
  *Gebaut (P-2026-09-30-04):* eigenes Modul `vierachs_schlichten.py` – sein
  Name ist die Art für „Schnittwerte in den Job“. Die Form liest sie aus dem
  ToolBit des Controllers (`werkzeuge_aus_cam.vom_controller`), so wie CAM
  fräst; einen Formfräser kennt CAM als Schaftfräser – er rechnet als Scheibe
  (sicher), ein Gewindefräser geht nicht. Den Rest nach dem Schruppen trägt
  sie aus den Bahnen der „Rundum schruppen“ des Jobs ab (`restmaterial`).
  Gefunden: Hinter dem Teil lässt die Schruppspirale an ihrem Ende einen Keil
  stehen (die letzte Umdrehung läuft nicht rundum auf dem Ende); ein Fräser,
  der weiter hinter das Teil reicht, bleibt dort oben – gemeldet wird nur, was
  über dem Teil stehen bleibt. Seit P-2026-09-30-06 nimmt Schlichten auch
  diesen Keil in Stufen ab (V5b).
- **V5d – Assistent:** In Schritt 2 unter „Rundum schruppen“ der Haken
  „Rundum schlichten“: Fräser (alle aus V5a mit Schnittwerten, vorgewählt ein
  Kugelfräser), Einsatz (vorgewählt „Schlichten“), Schrittweite (grau: ae des
  Einsatzes aus der Werkzeugtabelle) mit „→ Kammhöhe …“, Aufmaß (grau 0),
  darunter „→ 290 Umdrehungen, etwa 56 min“. Überlauf, Abstand zum Futter und
  Sicherheitsabstand stehen darunter einmal für beide unter „Abstände“;
  Überlauf leer heißt je Fräser Radius + 0,5 (grau „Radius + 0,5“). Die
  Ausspannlänge rechnet mit dem, der mehr Platz braucht. „Anlegen“ legt
  Schruppen und Schlichten an (je ein Schritt Rückgängig wie bisher).
  Doppelklick auf „Rundum schlichten“ öffnet es zum Ändern; beim Ändern von
  „Rundum schruppen“ lässt sich „Rundum schlichten“ dazunehmen – so bekommt
  ein Job aus 0.27 sein Schlichten.
  *Gebaut (P-2026-09-30-05):* Schritt 2 mit Werkstoff und
  „Werkzeugverwaltung …“ oben (gelten für beide), „Rundum schruppen“, „Rundum
  schlichten“ und „Abstände“; die Beschriftungen aller Blöcke gleich breit.
  „Rundum schlichten“ ist vorgewählt, wenn ein Fräser einen Einsatz
  „Schlichten“ hat – ohne einen bleibt es aus, wie bisher. Die Vorschau des
  Schlichtens rechnet grob (0,05 mm Netz, alle 2° ein Punkt, ohne den Rest
  nach dem Schruppen, also auch ohne Stufen): „→ 365 Umdrehungen, etwa
  1 h 35 min“ in Bruchteilen einer Sekunde; die Operation rechnet dann genau.
  Controller und Operationen
  beider Bearbeitungen sind ein Schritt Rückgängig. Beim Ändern des
  Schlichtens ist das Schruppen ausgeblendet.
- **V5e – Simulation und Kollision:** Abtrag und Farben (V3g) auch für
  „Rundum schlichten“, mit der Form des Fräsers; verglichen wird mit dem
  Aufmaß der letzten Bearbeitung. Abfahren und Kollision nehmen die Schneide
  als Drehkörper aus derselben Form (bisher Zylinder, beim Lollipop Kugel) –
  sonst stieße ein Kugelfräser in der Kehle „ins fertige Teil“.
  *Gebaut, Abtrag (P-2026-09-30-07):* `restmaterial` trägt mit der Form des
  Fräsers aus dem ToolBit ab (`form_des_controllers`; unbekannt: Schaftfräser
  mit seinem Durchmesser). Der Strahl aus der Achse trifft die Stirn, wo
  ρ · cos Δ = r + z(ℓ), ℓ = √(d² + (ρ · sin Δ)²): Schaftfräser und Kugel
  geschlossen, sonst gesucht – von unten heran, bei gewölbter Stirn mit Newton
  (dann kein Schritt über die erste Lösung). Die Schritte eines Stücks, ja
  aller Stücke einer Operation rechnet es zusammen (`fahre_stuecke`,
  `np.minimum.at`) – weg ist, was irgendein Schritt trifft, die Reihenfolge
  zählt nicht. Verglichen wird mit dem Aufmaß der letzten Bearbeitung; blau nur,
  was genau auf dem Strahl fehlt (Scheibe 0,001 mm) – neben einer Wand sah die
  halbe Rasterweite schon die Wand, und was die Kugel dort weg nahm, fehlte
  scheinbar im Teil. Welle mit Absatz (Ø 60/40 × 100, 365 Umdrehungen):
  Schruppen 1,4 s (vorher 6,3 s, gleiches Ergebnis), Schlichten mit Kugel 1,3 s,
  Torus 2,2 s, Konik 5,5 s; danach 97,9 % grün, nichts blau, rot nur die
  Rundung der Kugel in der Innenecke am Absatz (bis 1,95 mm). Geprüft: Kugel,
  Torus und Konik gegen den fein abgetasteten Strahl (unter 0,002 mm), die
  Kugel-Spirale mit ihrem Kamm, Schruppen und Schlichten auf der
  Beispiel-Drehmaschine (0,006 … 0,024 mm, alles grün).
  *Nachgebessert an Manuels Testteil (P-2026-09-30-44):* Loft 90 mm, D-Profil
  70 × 25, hinten gedreht und neben die Achse versetzt. Das Prüffenster meldete
  „fehlen bis 30,91 mm im Teil“, am Körper nachgemessen drang keine Bahn ein
  (höchstens 0,005 mm). Grund: Hinten liegt das Teil nicht rund um die Achse;
  der Fräser fährt dort bis an die Achse, nimmt auf einem Strahl weg, was
  zwischen Achse und Teil liegt, und für die Stange mit einem Radius je Strahl
  fehlte das Teil dahinter. Jetzt vergleicht es an Stellen nicht, an denen manche
  Strahlen das Teil vor der Achse haben und andere nicht – sie sehen es nur
  dahinter (dort gibt die Hüllfläche einen negativen Radius) oder gar nicht –,
  und sagt, von wo bis wo; ein Rohr hat jeder Strahl vor sich, dort wird
  verglichen. Am Testteil liegt die Achse hinten 0,2 mm neben der flachen Seite
  des D-Profils; „trifft der Strahl das Teil überhaupt“ reichte deshalb nicht.
  Dazu ist an scharfen Kanten und an den Enden erst blau, was tiefer liegt als
  die halbe Änderung zur Nachbarzelle (dort 0,11 bzw. 0,05 mm, kein
  Eindringen). Danach am Testteil: nichts blau, Rest 0 … 2,96 mm.
  *Gebaut, Schneide (P-2026-09-30-08):* `kollision.werkzeugkoerper` baut die
  Schneide als Drehkörper aus der Stirn (`drehkoerper`: Bögen und Geraden der
  Form um Z gedreht, darüber zylindrisch bis zur Schneidenlänge) – bei ebener
  Stirn wie bisher ein Zylinder, der Lollipop eine Kugel. Die Stirn kommt aus
  der Werkzeugverwaltung, sonst aus dem ToolBit (`Werkzeugmasse.stirn`). Der
  Kern: beim Kugelfräser die Kugel, um 0,05 mm kleiner; sonst die höchsten Kreise
  mit 0,05 mm über der Stirn, als Geraden (bis 1 µm zusammengefasst). Geprüft:
  Kugel-, Torus-, Konik-, Fasen-, Radien- und Planfräser – gültig, der Kern darin
  und 0,048 … 0,050 mm innen; ein Kugelfräser, über die Kante einer Tasche
  gerollt, meldet nichts (der Zylinder stäke 0,5 mm im Teil), 0,5 mm tiefer „ins
  fertige Teil“. Dieselbe Prüfung auf einem Job mit Schruppen und Schlichten:
  43 s wie vorher (77 193 Stellen) – der Kern als Kugel kostet nichts mehr.
  Gefunden: An der Beispiel-Drehmaschine sitzt T2 auf P2, dem axialen Halter –
  das Schlichten mit T2 meldet dort zu Recht „nicht radial“ und stößt an. Wie
  zwei radiale Werkzeuge an die Beispiel-Drehmaschine kommen, entscheidet
  Manuel.
  *Entschieden (Manuel, 2026-09-30):* Wie ein Werkzeug steht, sagt sein Halter
  (W-002 Stufe E). *Gebaut (P-2026-09-30-15):* Die Plätze der
  Beispiel-Drehmaschine sind Aufnahmen; T1 und T2 mit „VDI30 angetrieben radial“
  gehen den Klickweg unten ganz (`szenario_rundum_drehmaschine`). Dabei
  gefunden: Hinter einem Absatz, dessen Wand zum Futter zeigt, bleiben bei
  manchen Winkeln bis 6,4 mm stehen (Kugel Ø 6, Schrittweite 1 mm) – die Spirale
  liegt dort 2,5 mm (über die Kante gehoben) und 3,5 mm (erreicht die Wand nicht)
  von der Wand, nur auf dem halben Umfang genau 3; beim Schruppen genauso. Das
  Prüffenster zeigt es richtig rot. *Gebaut (P-2026-09-30-20, Durchsicht 2 D-42):*
  Vor jeder Wand – einer Planfläche des Teils quer zur Achse zwischen seinen Enden
  (`vierachs_operation.waende`) – hält die Spirale eine Umdrehung an (Ringgang):
  beim Schruppen in jeder Lage, beim Schlichten auch in den Stufen. Der Ring steht
  Fräserradius + Aufmaß + Vernetzung + 0,01 mm vor der Wand; die Hüllfläche dort
  genau an seiner Stelle. Im Szenario bleibt am Ende weniger als 1 mm (vorher
  6,4 mm); im Test hinter der Wand beim Schruppen 0,33 statt 7,32 mm, beim
  Schlichten an der Wand die Kehle 1,38 statt 4,78 mm.
- *Klickweg:* Welle mit Absatz, „4-Achs-Bearbeitung“ → Beispiel-Drehmaschine →
  „Weiter“ → „Rundum schruppen“ T1 Schaftfräser Ø 12 und „Rundum schlichten“
  T2 Kugelfräser Ø 6: Schrittweite grau aus der Werkzeugtabelle, daneben die
  Kammhöhe, darunter Umdrehungen und Zeit → „Anlegen“: im Job „Rundum
  schruppen T1“ und „Rundum schlichten T2“. „Auf der Maschine prüfen“ →
  abspielen: Am Ende ist das Teil grün, nur in der Kehle am Absatz bleibt der
  Radius des Kugelfräsers stehen (gelb); „Kollision prüfen“ meldet nichts.

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
   Futter am längsten steif. Der Gleichlauf kommt aus der Drehrichtung der
   Rundachse: mit M3 steigt φ, während die Spirale zum Futter rückt, mit M4
   („Reverse“ am Controller) fällt es (`spindel.ist_gleichlauf`, im Rahmen des
   Teils; P-2026-10-02-23). Linien längs mit dem Haken „nur im Gleichlauf“: jede
   Linie für sich, die Linien mit wachsendem φ – mit M3 vom Futter nach vorne
   (P-2026-10-02-28).
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
- **Schlichten (2026-09-30):** „Und es darf ja nicht nur Schuppen geben auch
  schlichten ist wichtig“ → V5 vor V4. Aus Fragen mit Optionen: Bahn als
  Spirale wie beim Schruppen; Fräser „Mit allen“ (jeder mit seiner Form,
  V5a); Schrittweite „Die Werte aus der Werkzeug Tabelle“ (ae des Einsatzes
  als Vorschlag, änderbar); Überlauf, Abstand zum Futter und
  Sicherheitsabstand einmal für beide.
- **Y-Achse (2026-09-29):** „bei einer maschine mit y achse kann man ja auch
  diese verfahren um eventuelle stellen besser zu erreichen“ → mit V4/V5:
  Flächen, die ein Werkzeug durch die Achse nicht erreicht (ebene Flächen,
  Hinterschnitte seitlich), fährt es mit Y versetzt; bis dahin gilt Y = 0.
