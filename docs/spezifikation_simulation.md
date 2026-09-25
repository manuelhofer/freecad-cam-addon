# Spezifikation W-001 Stufe 4: Werkzeugbahn auf der Maschine abfahren

Stand: **Entwurf von Claude**, zur Besprechung mit Manuel (P-2026-09-25-70).
Die Fragen in Abschnitt 9 entscheidet Manuel; bis dahin wird nichts davon
gebaut.

Grundlage: [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
(Stufen 1–3: Maschine beschreiben, an CAM übergeben, von Hand verfahren).

## 1. Zielbild

Der CAM-Job ist fertig. Bevor das Programm an die Maschine geht, will man
wissen:

1. **Reicht der Verfahrweg?** Bleibt jede Achse in ihren Grenzen – oder
   fährt X1 in Zeile 1234 auf 212 mm, obwohl bei 200 Schluss ist?
2. **Wie sieht das auf der Maschine aus?** Die Maschine aus Stufe 3 fährt
   die Bahn ab, mit Werkzeug und Werkstück, Schritt für Schritt oder am
   Stück.
3. **Stößt etwas an?** Spindelkopf gegen Schraubstock, Werkzeughalter gegen
   Werkstück, Schlitten gegen Schlitten.
4. **Wie lange dauert es wirklich?** Mit Eilgang, Vorschubgrenzen und
   Beschleunigung aus W-001 statt nur Weg durch Vorschub.

Was FreeCAD schon kann und das Addon **nicht** nachbaut: den Materialabtrag
(CAM-Simulator) und die Prüfung der Bahn gegen das Modell (Sanity-Check).

## 2. Was es schon gibt

| Baustein | Wo | Nutzen |
| --- | --- | --- |
| Maschine mit Achsen, Grenzen, Kennwerten, Aufnahmen | W-001 Stufen 1–2 (`maschine.py`, `kette.py`) | Kinematik, Grenzen, Eilgang, Beschleunigung |
| Achsen verfahren | W-001 Stufe 3 (`verfahren.py`) | die Maschine in jede Stellung bringen |
| Bahn der Operationen | CAM: `op.Path.Commands` (G0/G1/G2/G3 mit X Y Z, bei 4. Achse A/B/C) | was abgefahren wird |
| Werkzeug je Operation | Werkzeug-Controller → ToolBit mit Durchmesser, Länge, Schaft | Werkzeug als Körper |
| Rohteil und Modell | `job.Stock`, `job.Model` | Werkstück als Körper |
| Materialabtrag | CAM-Simulator (`SimulatorGL`) | bleibt, wie er ist |

## 3. Begriffe

- **Bahnpunkt** – ein Punkt der Werkzeugbahn in Werkstückkoordinaten (dem
  Koordinatensystem des Jobs), dazu bei 4/5-Achsbahnen die Winkel A/B/C.
- **Werkstücknullpunkt** – wo der Nullpunkt des Jobs auf der Maschine liegt:
  an der Werkstückaufnahme (ihr LCS), verschoben um eine Nullpunktverschiebung
  (G54).
- **Werkzeugspitze** – Werkzeugaufnahme (ihr LCS) plus Werkzeuglänge entlang
  der Werkzeugachse.
- **Achsstellungen** – die Werte aller Achsen, bei denen die Werkzeugspitze
  (relativ zum Werkstück) auf dem Bahnpunkt steht.

## 4. Achsstellungen aus der Bahn

Die Bahn beschreibt, wo die Werkzeugspitze **relativ zum Werkstück** sein
soll. Die Maschine erreicht das, indem Achsen im Tisch das Werkstück und
Achsen im Kopf das Werkzeug bewegen (Tisch/Kopf kennt W-001 schon).

- **3 Linearachsen:** Jede Linearachse verschiebt entweder das Werkstück
  oder das Werkzeug entlang ihrer Richtung. Die Lage der Spitze relativ zum
  Werkstück ist dann eine lineare Funktion der drei Achswerte – drei
  Gleichungen, drei Unbekannte, einmal gelöst für alle Punkte. Das geht auch
  bei schiefen Achsen und bei Maschinen, bei denen der Tisch X und der Kopf Z
  fährt.
- **4/5 Achsen:** Die Drehachsen stehen in der Bahn (A/B/C) oder ergeben
  sich aus der Werkzeugrichtung. Zuerst die Drehachsen setzen, dann wie oben
  die Linearachsen lösen – in der Lage, in der die Drehachsen das Werkstück
  bzw. den Kopf gedreht haben.
- **Drehmaschine:** X und Z der Bahn auf die Linearachsen, C (wenn
  vorhanden) auf die Positionierachse.
- Welcher Buchstabe der Bahn (X, Y, Z, A, B, C) zu welcher Betriebsart
  gehört (X1, C4 …), ergibt sich aus der Richtung der Achse; wo das nicht
  eindeutig ist, fragt das Fenster einmal nach und merkt es sich an der
  Maschine.

## 5. Stufen

**4a – Reichweite prüfen** (zuerst, weil schnell und sofort nützlich)
- Für jeden Bahnpunkt aller Operationen die Achsstellungen rechnen und gegen
  die Grenzen der Gelenke halten.
- Ergebnis als Liste in Worten: „X1 fährt in *Tasche001* bis 212 mm, die
  Grenze ist 200 mm (Zeile 1234).“ Ein Klick fährt die Maschine (Stufe 3)
  genau in diese Stellung.
- *Klickweg:* Job wählen → „Auf der Maschine prüfen“ → Liste der
  Überschreitungen, oder „Alle Achsen bleiben in ihren Grenzen“.

**4b – Abfahren**
- Werkzeug als einfacher Körper (Durchmesser, Schneidenlänge, Schaft,
  Gesamtlänge – die Felder aus der Werkzeugverwaltung) an der
  Werkzeugaufnahme, Rohteil an der Werkstückaufnahme.
- Abspielen, Anhalten, Schritt vor/zurück, Geschwindigkeit, Sprung zu einer
  Operation; die Zeilen von Stufe 3 zeigen die Achswerte mit.

**4c – Kollision**
- Geprüft wird in Abständen entlang der Bahn (z. B. alle 1 mm und an jedem
  Satzende) – nicht nur an den Satzenden, sonst rutscht eine Ecke durch.
- Paare: Schaft, Halter und bewegte Maschinenteile gegen Rohteil,
  Werkstückaufnahme und feste Maschinenteile; bewegte gegen feste
  Maschinenteile. Die Schneide darf ins Rohteil, sonst nirgends hin.
- Ergebnis wie 4a: „In *Kontur* (Zeile 88) berührt *Spindelkopf* den
  *Schraubstock*.“ Ein Klick fährt dorthin und hebt beide Teile hervor.

**4d – Bearbeitungszeit**
- Je Satz die Zeit mit Eilgang bzw. Vorschub, begrenzt durch die
  Achsgrenzen und mit Beschleunigung (Trapezprofil; Ruck später). Summe je
  Operation und gesamt – daneben FreeCADs eigene Schätzung zum Vergleich.

## 6. Oberfläche

Ein Aufgabenfenster wie „Maschine verfahren“, oben der Job, darunter die
Stufen als Bereiche: Reichweite (Liste), Abspielen (Knöpfe, Regler),
Kollision (Liste), Zeit (Tabelle). Jeder Eintrag einer Liste springt beim
Klick an seine Stelle.

## 7. Grenzen dieses Entwurfs

- Kein Materialabtrag – dafür gibt es den CAM-Simulator.
- Werkzeughalter als einfacher Zylinder (Durchmesser und Länge je Werkzeug,
  vorbelegt), bis es eine Halter-Verwaltung gibt.
- Bahnen mit Werkzeugrichtung (5-Achs-simultan) erst, wenn FreeCAD sie
  erzeugt – der Weg über A/B/C reicht für 3+2 und 4. Achse.

## 8. Prüfbarkeit

- Beispielmaschinen aus `tests/beispielmaschinen.py` plus ein kleiner Job
  (Quader mit Tasche) als Skript: Achsstellungen für bekannte Punkte,
  eine absichtlich zu große Tasche für 4a, ein zu kurzes Werkzeug neben
  einem hohen Spannmittel für 4c, Zeiten gegen Handrechnung für 4d.
- Die Oberfläche wie bisher mit Szenarien und Screenshots; ob es sich
  verständlich bedient, prüft Manuel.

## 9. Fragen an Manuel

1. **Was wird abgefahren – die Bahn im Job oder das fertige NC-Programm?**
   Vorschlag: die Bahn im Job (gibt es in beiden FreeCAD-Versionen, braucht
   keinen Postprozessor). Das NC-Programm wäre näher an der Wirklichkeit
   (Zyklen, Werkzeugwechsel), hängt aber von Postprozessor und Steuerung
   ab – als spätere Stufe.
2. **Wo liegt der Werkstücknullpunkt?** Vorschlag: am LCS der
   Werkstückaufnahme, dazu eine Verschiebung (G54) je Job im Fenster.
3. **Werkzeuglänge:** Gesamtlänge aus der Werkzeugverwaltung als Auskragung
   ab Spindelnase – oder ein eigenes Feld „Auskragung“ je Werkzeug?
4. **Halter:** einfacher Zylinder je Werkzeug reicht für den Anfang?
5. **Mindestabstand** für eine Warnung (z. B. 1 mm) – oder nur echte
   Berührung?
6. **Reihenfolge:** 4a zuerst, wie vorgeschlagen?

## 10. Akzeptanzkriterien 4a (Entwurf)

- Beispiel-Fräse mit X 0 … 300, Y 0 … 200, Z −150 … 0; Job mit einer Tasche
  innerhalb der Grenzen → „Alle Achsen bleiben in ihren Grenzen.“
- Dieselbe Tasche 150 mm weiter in X → „X fährt in *Tasche* bis 350 mm, die
  Grenze ist 300 mm (Zeile …).“ → Klick → die Maschine steht in dieser
  Stellung, X am Anschlag.
