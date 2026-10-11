# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

(Die Fragen 1–3 hat Manuel in P-2026-10-10-08 beantwortet, Frage 4 in P-2026-10-10-36, 5 und 7–9
in P-2026-10-11-30 – siehe Verlauf.)

### 6. Die Schrittweite der Kugel aus der Kammhöhe – und was gilt, wenn die Werkzeugtabelle weniger sagt?

Manuel (11.10.): „0.005mm kammhöhe ist quatsch … ich finde eine kammhöhe von 0.035 sogar völlig in
ordnung beim schlichten mit kugel … von daher sollten wir den seitlichen vorschub vll an die
kammhöhe koppeln?? ich mein wenn in der werkzeugliste steht das der fräser nicht mehr kann ists
doof … aber ich glaub kammhöhe sollte dennoch unseren vorschlag beeinflussen“. Die Stange Ø 90
bleibt (beantwortet).

Heute: Schrittweite = ae des Einsatzes „Schlichten“ aus der Werkzeugtabelle (Manuel, 2026-09-30) –
bei T2 (Kugel Ø 8) 0,4 mm. Am Nasen-Testteil, „Rundum schlichten T2“ mit Querachse, 408 mm/min,
Freivorschub 10 m/min (11.10. gerechnet):

| Kammhöhe | Schrittweite | Zeit |
| --- | --- | --- |
| 0,005 mm (heute) | 0,40 mm | 187,5 min |
| 0,010 mm | 0,57 mm | 132,5 min |
| 0,020 mm | 0,80 mm | 94,4 min |
| **0,035 mm** | **1,06 mm** | **71,7 min** |

**Die Frage:** Wie sollen Kammhöhe und Tabelle zusammen den Vorschlag machen?
(a) Schrittweite aus der Kammhöhe (Vorgabe 0,035 mm, im Assistenten änderbar), die ae der Tabelle
nur als Obergrenze – bei T2 bliebe es bei 0,4, bis die Tabelle mehr sagt;
(b) Schrittweite aus der Kammhöhe, die ae der Tabelle zählt fürs Schlichten mit Kugel/Torus nicht
mehr – bei T2 1,06 mm;
(c) wie (b), aber eine eigene Spalte „ae höchstens“ in der Werkzeugtabelle, die dann gilt.
*Warum nur Manuel:* Es ändert den Vorschlag ohne Vorgabe (Strategiewahl), und was die Kugel an
seiner Maschine aushält, weiß nur er.
*Was die Antwort ändert:* `vierachs_schlichten.schrittweite_vorschlag` (und das 3D-Schlichten im
3-Achs-Assistenten genauso?), ein Feld „Kammhöhe“ im Schritt 2.
Seit 2026-10-10, neu gefasst 2026-10-11.

### 10. Die Nase mit dem Schaftfräser fertig – so, wie im Bild?

![Nase mit dem Schaftfräser](bilder/vorschlaege/testteil_4achs_nase_schaftfraeser.png)

Manuels Antwort auf Frage 5 (11.10.): C so, dass die flache Seite der Nase zur Mitte (Face8) quer
zum Schaftfräser steht, mit Y abzeilen – „auch wenn das unter 0 ist“ –, die Seiten Face4/Face6
ebenso mit dem Schaftfräser, die Kugel dann nur noch Face9 (und Face5). Durchgerechnet am
Nasen-Testteil (Prototyp, 11.10. morgens): „Plan indexiert“ mit T1 Ø 12 (Stirn), C fest, Zeilen
längs mit Y –
- Face8: X bis −5,5 (5,5 mm unter der Mitte), zwei Zeilen bei Y ±4, die Mitte des Fräsers längs
  ab 6,2 mm vor der Stirn des Schafts (sonst stieße er in den Schaft) – 0,55 min; die roten
  Linien nach außen sind das Planaufmaß vorne an der Stange (1 mm), das dort mitfällt;
- Face4/Face6: X 10, Y bis ±36,7 – 0,94 min;
- die Kugel T2 ohne diese drei Flächen: 157,8 statt 187,5 min (sie lässt dort auch die Luft aus).
Zusammen **159,3 statt 187,5 min**. Die Seiten mit der Stirn (Fräserachse quer zur Fläche) gibt es
schon („Plan indexiert“); neu ist nur, dass eine Fläche, die zur Achse schaut, auch geht, wenn der
Weg von außen frei ist – bis zur Grenze von X der Maschine (das prüft „Auf der Maschine prüfen“).
**Die Frage:** So bauen – im 4-Achs-Assistenten ein Haken „Ebene Flächen mit dem Schaftfräser
fertig“, vorbelegt an, der „Plan indexiert“ mit dem Schruppfräser für die ebenen Flächen anlegt
(auch die zur Mitte) und die Kugel diese Flächen auslassen lässt? Und die Seiten mit der Stirn
(wie im Bild) – oder angestellt mit dem Schaft, wie du es auch beschrieben hast?
*Warum nur Manuel:* eine neue Wahl ohne Vorgabe (Strategiewahl), und wie weit X unter 0 an seiner
CLX550 darf, weiß er.
*Was die Antwort ändert:* der Haken im Schritt 2, `vierachs_planbahn.ebenen` mit Flächen zur
Achse, die Flächen der Kugel ohne die fertigen.
Seit 2026-10-11.
