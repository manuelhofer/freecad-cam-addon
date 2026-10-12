# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

(Die Fragen 1–3 hat Manuel in P-2026-10-10-08 beantwortet, Frage 4 in P-2026-10-10-36, 5 und 7–9
in P-2026-10-11-30, 6 in P-2026-10-11-40, 10 und 11 in P-2026-10-11-46, 12 in P-2026-10-11-86, 13 in P-2026-10-11-99, 14 in P-2026-10-11-93, 15 in der Spezifikation 4 Achsen, Abschnitt 17 – siehe Verlauf.)

**16. Brauchst du für die N-Eck-Stange ein Einrichtblatt?** Heute steht je Aufspannung ein Satz im
Kopf ihres Programms und im Fenster „Programm“, etwa: „Aufspannung 3 von 8: Stange um 90° gegen
die erste gedreht, die Flächen 3 und 7 an den Backen. Nullpunkt: X an der Stirn, Y und Z in der
Mitte der Stange.“ Möglich wäre zusätzlich ein Blatt (zum Ausdrucken) mit allen Aufspannungen:
der Querschnitt mit den Nummern der Flächen, je Aufspannung welche oben ist und welche an den
Backen liegen, Werkzeuge und Zeiten. – *Warum nur Manuel:* Ob du an der Maschine mit dem Satz im
Programm auskommst oder die Flächen an der Stange anzeichnest und ein Blatt brauchst, weißt nur
du aus der Werkstatt. – *Was die Antwort ändert:* Ja: Ich baue das Blatt (W-018, Spezifikation
4 Achsen, Abschnitt 17). Nein: Der Punkt fällt weg. – seit 2026-10-12.

**17. Vorschlichten: was soll die Kugel an den gelben Stellen entlasten?** Du hattest gefragt
(2026-10-12, am Geist und an der Nase): „kannst du nicht ein ‚Vorschlichten‘ … an die Stellen …
auf das Schlichtaufmaß vorarbeiten“, „vll vorschruppen bauen?“. Ich habe nachgemessen, was das
bringt – die Last der Kugel beim Schlichten je mm Weg, nach dem Schruppen und mit Vorläufen
(Bild: [geist_vorschlichten_kugel_eingriff.png](bilder/vorschlaege/geist_vorschlichten_kugel_eingriff.png)):

| Geist (T1 Schaftfräser Ø 8, T2 Kugel Ø 4, Schlichten 103 min) | Zeit dazu | Kugel höchstens | gelb auf |
|---|---|---|---|
| nach dem Schruppen | – | 75,7 mm² | 562 mm |
| Vorschlichten mit T1 aufs Aufmaß 0,3 (Spirale, Schritt 2) | 18 min | 75,7 mm² | 505 mm |
| Vorschlichten mit der Kugel, Aufmaß 1,0 (Schritt 1) | 57 min | 18,8 mm² | 104 mm |
| Kugel Aufmaß 1,5, dann 0,6 | 128 min | 18,8 mm² | 67 mm |

Gelb ist ab 2,4 mm² (2 × Aufmaß 0,3 × Ø 4). Was ich daraus lese:
- Der **Schaftfräser vom Schruppen hilft nicht**: Er kommt nicht hin, wo er schon beim Schruppen
  nicht hinkam – die beiden Taschen zwischen Armen und Körper (X −55 und −24) sind enger als Ø 8.
- Die **Kugel mit Aufmaß** nimmt viel weg, fährt dafür aber die ganze Spirale noch einmal (eine
  Stunde) und lässt gerade die Taschen stehen: Dort nimmt sie danach noch 17–19 mm², also über 4 mm
  tief in einem Zug.
- Die hohen Spitzen an den Enden (X −80 und 0, 50–75 mm²) halte ich für die Rechnung in Würfeln von
  1 mm an den Rändern, nicht für Material – die Warnung im Assistenten nannte X −29 … −17.
- An der **Nase** steht mit den gleichen Lagen (P-135) fast nichts mehr: 4,83 gegen 4,80 mm² auf
  1 mm; Vorschlichten ändert dort nichts.

Möglich wären:
- **A – Restschruppen in Lagen:** eine neue Operation „Rundum restschruppen“ mit einem kleineren
  Fräser (der Kugel oder z. B. einem Schaftfräser Ø 4), in Lagen wie das Schruppen, aber nur dort,
  wo danach noch Material steht – über dem Übrigen hebt sie ab. Am meisten Arbeit, nimmt die Taschen
  wirklich vor.
- **B – Vorschlichten mit der Kugel nur an den Stellen:** wie in der Tabelle, aber nur über den
  gelben Abschnitten längs (am Geist zweimal etwa 6 mm), in Stufen des Aufmaßes (z. B. 3 – 2 – 1 –
  0,3). Weniger Zeit als die ganze Spirale; die Kugel taucht trotzdem in die Tasche.
- **C – Vorschub senken, wo die Kugel mehr nimmt:** keine Bahn dazu, nur an den gelben Stellen
  langsamer (etwa im Verhältnis des Eingriffs, mit einer Untergrenze). Kostet die wenigsten Minuten.
- **D – so lassen:** die Warnung bleibt, du entscheidest an der Maschine.

*Warum nur Manuel:* Was die Kugel Ø 4 in deinem Werkstoff an 19 mm² aushält, ob du lieber einen
Fräser mehr einwechselst (A) oder langsamer fährst (C), weißt nur du aus der Werkstatt; ohne dein
Ja baue ich keine neue Strategie (Arbeitsregeln, Strategiewahl). – *Was die Antwort ändert:* A baut
„Rundum restschruppen“ als Haken im Assistenten, vorbelegt an, wenn gelb; B die Vorläufe der Kugel
über den gelben Abschnitten; C den Vorschub der Kugel je Stelle; D nichts. – seit 2026-10-12.

**18. „Plan indexiert“: Stiche von der offenen Seite statt Zeilen mit Rampe – als Vorgabe?** Du
hattest gesagt (2026-10-12): „wenn ich nur Plan indexieren mache, fährt mir der Fräser in einem
Zickzack-Eintauch ins Teil … aber für was? außenrum ist alles frei … fahr doch Morph zum Schruppen
mit Auswahl nur Gleichlauf / Gleichlauf und Gegenlauf / nur Gegenlauf … so dass er D's fährt“.
Nachgebaut am Nasen-Testteil (Face4, 6, 8, T1 Ø 12, ap 22,2, ae 5,4, von der Stange): das
3-Achs-Räumen im Rahmen jeder Fläche, auf denselben Streifen begrenzt wie die Zeilen (Bild:
[testteil_4achs_plan_stiche_gegen_zeilen.png](bilder/vorschlaege/testteil_4achs_plan_stiche_gegen_zeilen.png)):

| | Zeit (mit Bremsen) | Vorschubweg | Eintauchen | Weg über 120 mm² Eingriff | weggenommen |
|---|---|---|---|---|---|
| Zeilen heute (hin und her, Rampen) | 3,8 min | 4,3 m | 11 | 116 mm, ungebremst | 133,7 cm³ |
| Stiche von der offenen Seite (D's) | 2,5 min | 1,8 m | 7–8 | 301 mm, auf ~50 % gebremst | 132,8 cm³ |
| Morph | passt hier nicht (fällt auf „Rohteil“, 32-mal eintauchen) | | | | |
| adaptiv | 5,0 min | 5,6 m | 11 | | |

Beide fahren nicht ins Teil. Gleich- und Gegenlauf geben dieselbe Zeit (die Stiche gespiegelt).
Ohne die Begrenzung auf den Streifen räumte es nach 3-Achs-Art die ganze Schicht über der Ebene ab,
bis ans Futter (19 min) – das nimmt ohnehin „Rundum schruppen“.

Gebaut in 0.256.0 (P-2026-10-12-146) als Wahl „Über der Fläche“ in „Plan indexiert“: Zeilen hin
und her (Vorgabe, „beides“), Stiche von der offenen Seite – Gleichlauf, – Gegenlauf. Probier es am
Nasen-Teil: 4-Achs-Bearbeitung, Plan indexiert anhaken, „Über der Fläche“ auf die Stiche, dann
„Auf der Maschine prüfen“ und abspielen. – *Warum nur Manuel:* Ob die Stiche die Vorgabe
werden – sie greifen öfter tief ein (bis 205 mm², das Addon bremst dort), die Zeilen dafür mit
Rampen ins Material –, entscheidest du an der Maschine; ohne dein Ja ändere ich die Vorgabe
nicht (Strategiewahl). Und: „Plan indexiert als Erstes“, damit die anderen die Nase nicht
noch einmal fahren, heißt, dass „Rundum schruppen“ danach weiß, was Plan schon weggenommen hat –
das ist ein eigener, größerer Schritt. – *Was die Antwort ändert:* Ja: die Stiche werden die
Vorgabe; Nein: sie bleiben eine Wahl. – seit 2026-10-12.

**19. Wo war die Nase von unten nicht bearbeitet?** Du hattest geschrieben (2026-10-12): „aber die
Nase von unten ist dennoch nicht bearbeitet“. Im Beispiel-Job (`beispiele/testteil_4achs_nase.FCStd`,
Rundum schruppen T1 + Rundum schlichten T2) habe ich die Bahn selbst vermessen – den Abstand der
Kugel zu Punkten im Inneren jeder Fläche, längs der Strecken zwischen den Sätzen: Auf der
Unterseite (Face5) und allen anderen Flächen der Nase kommt die Kugel bis auf 0,02 mm heran, mit
und ohne Querachse und Anstellen. – *Warum nur Manuel:* Ich weiß nicht, wo du es gesehen hast:
im Abspieler (die Anzeige kennt je Strahl aus der Achse nur einen Radius – an schrägen
Unterseiten und Überhängen zeigt sie Material, das nicht da ist, wie bei den Händen des Geists),
in einem anderen Job (etwa mit „Plan indexiert“, dann lässt das Schlichten dessen Flächen aus)
oder an der Maschine. – *Was die Antwort ändert:* Abspieler: die Anzeige für solche Stellen
genauer machen (3D statt Strahlen). Anderer Job: schick ihn mir, dann suche ich dort. – seit
2026-10-12.