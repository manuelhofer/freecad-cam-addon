# Spezifikation W-001 Stufe 4: Werkzeugbahn auf der Maschine abfahren

Stand: Entwurf von Claude (P-2026-09-25-70). **Manuel hat am 2026-09-26 die
Fragen zu 4a entschieden** (Abschnitt 9, P-2026-09-26-83). 4a wird in vier
Schritten gebaut (Abschnitt 5). 4b bis 4d bleiben Entwurf; die Fragen 4 und 5
kommen vor 4c.

Grundlage: [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
(Stufen 1–3: Maschine beschreiben, an CAM übergeben, von Hand verfahren; 3b:
schräge Achse).

## 1. Zielbild

Der CAM-Job ist fertig. Bevor das Programm an die Maschine geht, will man
wissen:

1. **Reicht der Verfahrweg?** Bleibt jede Achse in ihren Grenzen – oder
   fährt X1 in *Tasche* auf 212 mm, obwohl bei 200 Schluss ist?
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
| Achsen verfahren | W-001 Stufe 3 (`verfahren.py`) | die Maschine in jede Stellung bringen; Revolverplätze in Arbeitsstellung |
| Schräge Achse | W-001 Stufe 3b (`schraege_achse.py`) | Höchstvorschub; dieselben Zahlen wie „wie im Programm“ |
| Bahn der Operationen | CAM: `op.Path.Commands` (G0/G1/G2/G3 mit X Y Z, bei 4. Achse A/B/C) – so, wie der Postprozessor sie liest | was abgefahren wird |
| Werkzeug je Operation | Werkzeug-Controller → ToolBit mit Durchmesser, Länge, Schaft; das Werkzeug der Werkzeugverwaltung dazu (`job_schnittwerte.werkzeug_von`) | Werkzeuglänge, Werkzeug als Körper |
| Rohteil und Modell | `job.Stock`, `job.Model` | Vorschlag für den Nullpunkt; Werkstück als Körper |
| Materialabtrag | CAM-Simulator (`SimulatorGL`) | bleibt, wie er ist |

## 3. Begriffe

- **Bahnpunkt** – ein Punkt der Werkzeugbahn in den Koordinaten des Jobs,
  dazu bei 4/5-Achsbahnen die Winkel A/B/C.
- **Werkstücknullpunkt** – wo der Nullpunkt des Jobs auf der Maschine liegt:
  am LCS der Werkstückaufnahme, verschoben um den **Nullpunkt des Jobs** (wie
  G54), gemessen in den Achsen dieses LCS. **Das LCS ist das
  Koordinatensystem des Jobs:** Z aus der Spannfläche heraus, X so, wie X im
  Job zum eingespannten Teil liegt – auf der Drehmaschine von der
  Spindelachse zum Werkzeug hin.
- **Werkzeugspitze** – der Ursprung der Werkzeugaufnahme (ihr LCS), um die
  Länge ab Spindelnase gegen die Z-Achse des LCS versetzt. Die Z-Achse einer
  Werkzeugaufnahme zeigt von der Spitze zur Aufnahme – wie +Z der Maschine,
  das das Werkzeug vom Werkstück wegfährt.
- **Länge ab Spindelnase** – von der Werkzeugaufnahme (Spindelnase, Platz
  im Revolver) bis zur Spitze, mit Halter; so, wie sie das Voreinstellgerät
  misst.
- **Achsstellungen** – die Werte aller Achsen, bei denen die Werkzeugspitze
  (relativ zum Werkstück) auf dem Bahnpunkt steht; gezählt wie im Fenster
  „Maschine verfahren“ und wie die Grenzen am Gelenk.

## 4. Achsstellungen aus der Bahn

Die Bahn beschreibt, wo die Werkzeugspitze **relativ zum Werkstück** sein
soll. Die Maschine erreicht das, indem Achsen im Tisch das Werkstück und
Achsen im Kopf das Werkzeug bewegen. Gerechnet wird wie beim Verfahren
(Stufe 3) – die Lage jedes Glieds ist das Produkt der Achsbewegungen vom Bett
nach außen –, aber ohne die Bauteile zu bewegen.

- **Drehachsen zuerst:** Rundachsen stehen, wie die Bahn sagt – A, B und C
  über ihren Namen im Programm (NC-Name ohne Ziffern am Ende: C1 → C), ohne
  Angabe auf 0. Der **Revolver** steht mit dem Platz des Werkzeugs (T3 → P3)
  in Arbeitsstellung, dort, wo P1 beim Öffnen stand. Spindeln ohne
  Betriebsart „Positionieren“ bleiben, wie sie stehen – sie drehen das
  Werkzeug um seine eigene Achse.
- **Dann die Linearachsen:** Stehen die Drehachsen, hängt der Abstand
  zwischen Werkzeugspitze und Bahnpunkt linear an den Wegen der
  Linearachsen zwischen Werkzeug- und Werkstückaufnahme – drei Gleichungen,
  einmal gelöst für alle Punkte mit derselben Stellung der Drehachsen. Das
  gilt für Tisch- und Kopfachsen, für schiefe Achsen und für die **schräge
  Achse** (Stufe 3b): Die Bahn ist rechtwinklig, die Lösung liefert die
  Stellungen der Schlitten – dieselben Zahlen wie beim Verfahren „wie im
  Programm“ (`schraege_achse.Programm`). Geprüft werden die Grenzen der
  Schlitten; die Meldung nennt beides, den Punkt im Programm und den
  Schlitten: „X 140, Y −40 in *Kontur* braucht X1 = 163 mm, die Grenze ist
  150 mm“ (bei 30°).
- **Weniger als drei Linearachsen** (Drehmaschine ohne Y): Punkte außerhalb
  der Ebene, in der das Werkzeug fahren kann, meldet die Prüfung als nicht
  erreichbar. **Mehr als drei** (Pinole und Z): meldet sie als noch nicht
  prüfbar.
- **Welche Punkte:** die Enden von G0 und G1; Kreise (G2/G3, auch als
  Schraube) zusätzlich genau dort, wo eine Achse umkehrt; Bohrzyklen (G73,
  G81 … G89) über dem Loch, auf der R-Ebene und auf dem Grund. Ändert sich
  eine Rundachse im Satz, kommt alle 1° ein Punkt dazu. Rundachsen werden
  gegen ihre Grenzen gehalten, wenn sie nicht endlos sind.
- Für 4d gilt der Höchstvorschub der schrägen Achse
  (`schraege_achse.hoechstwert`).

## 5. Stufen

**4a – Reichweite prüfen** (zuerst, weil schnell und sofort nützlich) – in
vier Schritten:

1. **Rechenkern** (`reichweite.py`, ohne Oberfläche): für einen Job die
   Achsstellungen aller Bahnpunkte (Abschnitt 4); je Achse der gebrauchte
   Bereich; je Operation und Achse die größte Überschreitung mit dem Punkt im
   Programm und allen Achsstellungen dort; Hinweise in Sätzen – Länge des
   Werkzeugs angenommen, Platz fehlt am Revolver, Punkt nicht erreichbar,
   Z-Achse einer Werkzeugaufnahme zeigt zum Werkstück, Befehl übergangen.
   Dazu: Beispiel-Drehmaschine mit X des LCS am Futter wie X der Maschine;
   Hilfe „Aufnahmen“ mit den Richtungen der LCS wie in Abschnitt 3.
   *Gebaut (P-2026-09-26-84).*
2. **Fenster „Auf der Maschine prüfen“** (Abschnitt 6) mit Befehl, Hilfe
   und Szenario.
3. **Länge ab Spindelnase** als Feld der Werkzeugverwaltung (alle Arten,
   leer gilt die Gesamtlänge); die Prüfung findet das Werkzeug zum
   Werkzeug-Controller wie „Schnittwerte in den Job“, sonst gilt die Länge
   des CAM-Werkzeugs – mit Hinweis.
4. Version, voller Lauf, Push.

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
- Ergebnis wie 4a: „In *Kontur* (bei X …, Y …, Z …) berührt *Spindelkopf*
  den *Schraubstock*.“ Ein Klick fährt dorthin und hebt beide Teile hervor.

**4d – Bearbeitungszeit**
- Je Satz die Zeit mit Eilgang bzw. Vorschub, begrenzt durch die
  Achsgrenzen und mit Beschleunigung (Trapezprofil; Ruck später). Summe je
  Operation und gesamt – daneben FreeCADs eigene Schätzung zum Vergleich.

## 6. Oberfläche

Befehl **„Auf der Maschine prüfen“** in der Werkzeugleiste „CAM-Addon“. Er
braucht einen Job im aktiven Dokument; ist einer gewählt, gilt der. Er
öffnet ein Aufgabenfenster:

- **Job** – die Jobs des Dokuments. **Maschine** – alle Baugruppen mit
  Maschinenobjekt in allen offenen Dokumenten, vorgewählt die im Dokument
  des Jobs, sonst die erste. **Werkstückaufnahme** – nur, wenn es mehrere
  gibt.
- **Nullpunkt des Jobs, von der Werkstückaufnahme aus:** X, Y, Z. Leer gilt
  der Vorschlag, grau im Feld: das Rohteil mittig auf der Aufnahme, mit der
  Unterseite auf der Spannfläche. Eingetragene Werte speichert der Job.
- **Ergebnis:** „Alle Achsen bleiben in ihren Grenzen.“ – oder je
  Überschreitung ein Satz: „X1 fährt in *Tasche* bis 312,00 mm, die Grenze
  ist 250,00 mm (bei X 450, Y 0, Z −5).“ Ein Klick fährt die Maschine
  (Stufe 3) in diese Stellung, die Achse am Anschlag, und zeigt ihr
  Dokument. Darunter je Achse, was die Bahn braucht und was die Grenzen
  erlauben; Hinweise in Grau.
- Gerechnet wird beim Öffnen und nach jeder Änderung. **Schließen** fährt
  die Maschine zurück, wie sie beim Öffnen stand.

4b bis 4d kommen als weitere Bereiche in dasselbe Fenster.

## 7. Grenzen dieses Entwurfs

- Kein Materialabtrag – dafür gibt es den CAM-Simulator.
- Werkzeughalter als einfacher Zylinder (Durchmesser und Länge je Werkzeug,
  vorbelegt), bis es eine Halter-Verwaltung gibt.
- Die Werkzeugspitze liegt auf der Werkzeugachse (eine Länge). Drehwerkzeuge
  mit Versatz in X und Z kommen mit einer Verwaltung für Drehwerkzeuge.
- Der Nullpunkt des Jobs ist eine reine Verschiebung, keine Drehung (G68).
- Bahnen mit Werkzeugrichtung (5-Achs-simultan) erst, wenn FreeCAD sie
  erzeugt – der Weg über A/B/C reicht für 3+2 und 4. Achse.

## 8. Prüfbarkeit

- Beispielmaschinen aus `camaddon/beispielmaschine.py` und
  `tests/beispielmaschinen.py`, dazu Jobs mit eigener Bahn: FreeCADs
  Operation „Eigene“ (Custom) nimmt G-Code als Text – in 1.1.3 und im
  Wochen-Build ausprobiert. Achsstellungen für bekannte Punkte, eine Bahn
  über die Grenze für 4a, ein zu kurzes Werkzeug neben einem hohen
  Spannmittel für 4c, Zeiten gegen Handrechnung für 4d.
- Die Oberfläche wie bisher mit Szenarien und Screenshots; ob es sich
  verständlich bedient, prüft Manuel.

## 9. Entscheidungen

1. **Was wird abgefahren?** – *Entschieden (Manuel, 2026-09-26):* die Bahn
   im Job. Sie gibt es in beiden FreeCAD-Versionen, sie braucht keinen
   Postprozessor. Das fertige NC-Programm (Zyklen, Werkzeugwechsel) kann
   eine spätere Stufe werden.
2. **Wo liegt der Werkstücknullpunkt?** – *Entschieden:* am LCS der
   Werkstückaufnahme, dazu eine Verschiebung je Job im Fenster.
3. **Werkzeuglänge** – *Entschieden:* ein eigenes Feld „Länge ab
   Spindelnase“ je Werkzeug (mit Halter, wie am Voreinstellgerät); leer gilt
   die Gesamtlänge.
4. **Halter:** einfacher Zylinder je Werkzeug reicht für den Anfang? –
   *offen, vor 4c.*
5. **Mindestabstand** für eine Warnung (z. B. 1 mm) – oder nur echte
   Berührung? – *offen, vor 4c.*
6. **Reihenfolge** – *Entschieden:* 4a zuerst.

## 10. Akzeptanzkriterien 4a

- 3-Achs-Beispielfräse, ein Job mit einer Bahn innerhalb der Grenzen →
  „Alle Achsen bleiben in ihren Grenzen.“, darunter je Achse, was die Bahn
  braucht und was die Grenzen erlauben.
- Dieselbe Bahn weit in X verschoben → „X1 fährt in *…* bis … mm, die
  Grenze ist … mm (bei X …, Y …, Z …).“ → Klick → die Maschine steht dort,
  X1 am Anschlag. Schließen → alles steht wie vorher.
- Beispiel-Drehmaschine mit Y schräg um 30°: Eine Bahn, bei der X im
  Programm in seinen Grenzen bliebe, X1 zum Ausgleichen aber darüber müsste →
  die Meldung nennt X1 und den Punkt im Programm.
- Ein Werkzeug ohne Länge ab Spindelnase → gerechnet mit der Gesamtlänge,
  der Hinweis sagt es („ohne Halter“).
- Manuel versteht das Fenster ohne Erklärung.
