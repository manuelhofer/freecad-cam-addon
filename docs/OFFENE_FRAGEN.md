# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

## 1. Soll „Weiter bearbeiten“ das letzte Aufmaß in zwei gleichen Schnitten nehmen – mit Messen dazwischen?

**Die Frage:** „Weiter bearbeiten“ schlägt je Gang 1 mm weniger Aufmaß vor (3 → 2 → 1 → 0, dein Beispiel vom
31.10.). Nach dem Schruppen mit 0,3 heißt das: gleich auf 0. Gemessen wird davor am geschruppten Maß, und
der Fertiggang nimmt die 0,3 auf einmal. Für eine Passung lässt man an der Maschine die Hälfte stehen:
0,3 → 0,15 → 0, beide Gänge mit demselben Fräser, derselben Tiefe, demselben Vorschub. Der Fräser wird dann
beide Male gleich weit abgedrängt – was der Taster (oder du) nach dem ersten Gang misst, ist genau das, was
der zweite ausgleichen muss. Das kostet den Wandzug ein zweites Mal (am Testteil „Kontur T1“: 0,41 min,
gemessen am 12.11.) und das Messen (nicht gemessen).

- **a)** Als Haken in „Weiter bearbeiten“: „in zwei gleichen Schnitten“ – angehakt, sobald das Aufmaß davor
  1 mm oder weniger ist. Dann steht 0,15 im Feld statt 0, der Messstopp kommt vor den Fertiggang.
  *Claudes Vorschlag.*
- **b)** Derselbe Haken, aber nicht angehakt.
- **c)** Bleibt wie heute (0,3 → 0); wer vorschlichten will, tippt 0,15 selbst ein.

*Warum nur Manuel:* Es ist dein Vorgehen an der Maschine, und es kostet je Wand einen Schlichtgang.
*Was die Antwort ändert:* bei a) und b) kommt der Haken, bei a) ändert sich, was das Fenster nach dem
Schruppen vorschlägt. Später möglich: Messen in zwei Höhen (oben und knapp über dem Boden), damit eine Wand
gerade wird. Seit 2026-11-12.

## 2. Soll der Planfräser eigene Ringe von außen bekommen – ae 35, eingerollt, ohne Rampe?

**Die Frage:** Deine Platte (200 × 200, 20 mm ab bis auf die Oberseite, Zapfen Ø 20), am 12.11. im Prüfstand
gerechnet und auf zweitem Weg nachgerechnet. Bild:
[frage2_planfraeser_ringe_platte.png](bilder/vorschlaege/frage2_planfraeser_ringe_platte.png).

- alles mit dem Ø 12 (Räumen): **33,4 min**
- Plan 50 in Zeilen (ae 35, ap 2, zehn Lagen) 24,6 min + Wechsel 10 s + Ø 12 für den Rest am Zapfen 1,4 min =
  **26,1 min** – seit 0.365.2 ohne das Eintauchen neben dem Zapfen 23,7 min, zusammen rund **25,2 min** (der
  Rest für den Ø 12 dabei nicht neu gemessen; Bild:
  [planfraesen_zeilen_aus_der_luft.png](bilder/vorschlaege/planfraesen_zeilen_aus_der_luft.png))
- Plan 50 in Ringen vom Rand, mit dem Räumen, wie es heute ist: 27,3 min + Wechsel + Ø 12 Rest 0,8 min =
  **28,3 min**
- Untergrenze des Plan 50 mit ae 35: 11,9 min

Alle drei nehmen dasselbe weg, nichts geht ins Teil. Die Ringe sind heute **langsamer** als die Zeilen: Das
Räumen lässt höchstens ae = R zu (25 statt 35), die Quadratringe überlappen sich, um den Zapfen läuft ein
eigener Kreisring mit 8 Rampen – 24 m Vorschub, wo 16 m reichten. Die Zeilen fahren jede zweite im
Gegenlauf. (Sie tauchten dazu 20-mal senkrecht ins Material, links und rechts neben dem Zapfen – das ist
seit 0.365.2 heraus: Jedes Stück neben dem Zapfen beginnt in der Luft; seit 0.366.1 auch, wenn
das Rohteil über die Fläche hinaussteht.)

Gebaut würden Ringe nur für den Planfräser: ae bis 0,7 D, an jeder Stelle im Bogen eingerollt, immer
Gleichlauf, zusammenhängend, keine Rampe – was nur über eine Rampe ginge, bleibt dem Ø 12. Wie schnell das
wird, ist **nicht gemessen**; die Untergrenze sinkt von 16,6 auf 11,9 min.

- **a)** Bauen, als Haken beim Planfräsen „in Ringen von außen“, angehakt – bleibt nur drin, wenn es an deiner
  Platte gemessen unter den 23,7 min der Zeilen liegt. *Claudes Vorschlag.*
- **b)** Nein, Zeilen und der Ø 12 für den Rest reichen.

*Warum nur Manuel:* Es geht darum, wie dein Messerkopf fahren soll – in Ringen mit 0,7 D umlaufen statt in
Zeilen hin und her –, und es ändert, was das Addon für ihn vorschlägt. Am Zapfen bleiben die Ringe nur 0,7 mm
frei; das geht mit 45°-Platten, mit 90°-Platten nicht – welche du fährst, weiß nur die Werkstatt.
*Was die Antwort ändert:* bei a) baue und messe ich die Ringe, bei b) bleibt es bei den Zeilen. Seit 2026-11-12.

## 3. Soll das Addon dir die Drehkontur geben und dann nur noch fräsen, was nicht rund ist?

**Die Frage:** Am Ring (Ø 65 aus der Stange Ø 70, Planzugabe 1 mm) fräst „Rundum schruppen“ heute alles mit
dem Ø 4: **12,9 min**, 11,0 km (vf 859, ohne Eilgang). Zwei Dinge davon würdest du an der CLX drehen. Bild:
[frage3_vorgedreht_ring.png](bilder/vorschlaege/frage3_vorgedreht_ring.png).

- **Stirn:** Die 0,7 mm vorn fräst er heute mit – 3,8 km Weg vor dem Teil und rund 130 Umdrehungen der
  C-Achse im Eilgang für 1,9 cm³. Plan gedreht: **9,8 min**.
- **Durchmesser:** dazu längs Ø 65,6 gedreht (Hülle des Teils + 0,3): **6,9 min**, 5,5 km.

Mit dem Antrieb der Beispielmaschine (4000 1/min, vf 360): 30,7 → 23,3 → 15,8 min. Gedreht werden zusammen
9,2 cm³; die Drehzeit ist nicht gerechnet. Nichts geht ins Teil. Die Kontur ist am Ring ein Durchmesser, an
einer Welle mit Absätzen wäre sie eine Maßliste (Ø … von Z … bis Z …). Innen ist nicht gerechnet: Durch die
Bohrung fährt er heute 3,4 km und nimmt 8 cm³ – bohrst du vorher, fällt davon auch etwas weg.

- **a)** Ein Haken „vorgedreht“ im 4-Achs-Assistenten, angehakt, wenn das Teil auf der Drehmaschine liegt:
  Das Einrichtblatt nennt die Kontur als Maße, das Fräsen rechnet mit der gedrehten Stange. Du drehst wie
  gewohnt in ShopTurn. *Claudes Vorschlag.*
- **b)** Derselbe Haken, nicht angehakt.
- **c)** Nur die Stirn: Das Addon nimmt an, dass plan gedreht ist (so steht es in der Spezifikation), den
  Durchmesser fräst es weiter.
- **d)** Bleibt wie heute.

*Warum nur Manuel:* Es setzt voraus, dass du vorher drehst, und es ändert, was das Addon ohne Vorgabe fräst.
*Was die Antwort ändert:* bei a) bis c) der Haken, die Maße im Einrichtblatt und ein Materialstand
„vorgedreht“; dabei fährt die oberste Lage nicht mehr im Freivorschub auf dem gedrehten Ø entlang (ist er ein
paar Hundertstel dicker, schnitte der Ø 4 dort mit 5000 mm/min). Drehzyklen im Programm bleiben draußen. Seit
2026-11-12.
