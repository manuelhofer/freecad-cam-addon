# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

**1. Rundum schruppen mit der Querachse: Wie sollen die Sektoren gefahren werden?**
Seit P-2026-10-17-26 fährt „Rundum schruppen“ **ohne** Querachse eine Lage, über der nur noch
in Sektoren etwas steht (dein Ring: drei Segmente mit Schlitzen), als Zeilen in den Sektoren
statt als Spirale rundum – am Ring 100 → 11 km Weg, 70 → 11 min (bei vf 1000). Bild:
[ring_sektoren.png](bilder/vorschlaege/ring_sektoren.png).
**Mit** Querachse (an der CLX mit Y vorbelegt an) bleibt die Spirale: am Ring 151 km, 88 % Luft,
106 min. Zeilen mit dem radialen Fräser ließen der Kugel an der Nase das Doppelte stehen (22 statt
12 cm³, bis 58 mm² je mm) – die Zeilen müssen also angestellt werden wie die Spirale. Dann gilt
dein „C dreht nicht zurück“ (Frage 11, 2026-10-11): Zwei Wege:
- (a) Zeilen im Schlitz **hin und her** (C dreht je Zeile 40° zurück, wie „Zeilen hin und her“
  mit gewählten Flächen) – am schnellsten, aber C pendelt. So fährt es **ohne** Querachse heute
  schon: Die Zeilen eines Schlitzes hängen als Schlange zusammen (am Ring 482 Umkehrungen von C
  im Vorschub, keine Rampe – die erste Zeile jeder Lage kommt von vorn aus der Luft).
- (b) Jede Zeile in **derselben Richtung**; danach abheben und C im Eilgang 320° **vorwärts** zum
  Anfang drehen – ruhig, kostet je Zeile eine Drehung (am Ring rund 900 Zeilen: bei 30 U/min
  etwa 25 min nur Drehen).
*Warum nur Manuel:* Ob C pendeln darf, hast du mit „C dreht nicht zurück“ entschieden – ob das
auch in einem 40° breiten Schlitz gelten soll, weißt nur du.
*Was die Antwort ändert:* Bei (a) baue ich die Zeilen mit Anstellung und Hin und Her, bei (b)
mit Eilgang-Drehung; dazu Einfahrten, die C nicht zurückdrehen (eine Rampe längs der Stange).
– seit 2026-10-17

**2. Die Nase: Flosse mit Plan indexiert und Kugel nur auf den schrägen Flächen – soll der
Assistent das von sich aus vorschlagen?**
Dein Weg für die Nase (2026-10-12: Schaft an der Flosse entlang, die Front quer) nachgerechnet
am Beispiel `testteil_4achs_nase` mit dem, was das Addon schon kann. Bild mit Zahlen:
[nase_flosse_weg.png](bilder/vorschlaege/nase_flosse_weg.png).
- Heute: Rundum schruppen 12,2 min, dann Rundum schlichten mit der Kugel Ø 8 als Spirale über die
  ganze Welle, Kammhöhe 0,02: **114,7 min** – die Welle Ø 60 wird dabei mitgeschlichtet, die man
  dreht.
- Vorschlag: Schruppen wie heute 12,2; die Seiten (Face4/6) und die Spitze (Face8) der Flosse
  mit „Plan indexiert“, Stirn, T1 Ø 12: 4,6 min; die zwei schrägen Flächen (Face9/Face5) mit der
  Kugel in **Linien längs** statt der Spirale: 21,8 min. **Zusammen 39 min statt 127.**
- Noch nicht möglich: der Schaft an der Flosse entlang (`mit_dem_schaft`) – die Flosse ist 40 mm
  hoch, T1 hat 26 mm Schneide; und die Front quer in Y mit dem Umfang ist nicht gebaut. Die
  schrägen Flächen (Normale schräg zur Achse) kann ohne B-Achse nur die Kugel.
*Warum nur Manuel:* Was der 4-Achs-Assistent ohne Vorgabe anlegt, ist eine Strategiewahl: Soll er
bei einer Flosse von selbst „Plan indexiert“ für die ebenen Flächen anhaken und das Schlichten mit
der Kugel auf die übrigen Flächen in Linien beschränken – und die Welle auslassen?
*Was die Antwort ändert:* Bei Ja: Der Assistent schlägt das vor, wenn gewählte Flächen eben sind;
die Spirale über die ganze Welle nur noch auf Wunsch. Dazu der Schaft an den Seiten in zwei Lagen
(Schneide 26 bei 40 mm Höhe) als nächster Schritt. – seit 2026-10-17

**3. Messstopp: Was soll die Maschine dabei genau tun – und mit welchen Befehlen?**
Heute (seit W-010, P-2026-10-17-41 auch nach der Nut): Z hoch (mit Wechselpunkt dorthin, Siemens
„F_HOME“), M5, M9, M0 – nach dem Start M3 (oder M4) mit der Drehzahl des Schlichtens und M8/M7, wenn
der Job Kühlung hat. Du sagst (2026-10-17): „maschine fährt auf home, macht türen auf, drehzahl aus,
wasser aus … und wenn man weiter drückt wieder alles an“. Für die **Türen** gibt es keinen
allgemeinen Befehl – an deiner Siemens/Heidenhain wäre das ein M-Befehl der Maschine (oder gar
keiner, wenn der Halt M0 reicht und du die Tür von Hand öffnest).
*Warum nur Manuel:* Welche M-Befehle deine Maschinen für Tür auf/zu haben (und ob sie das
überhaupt im Programm wollen), weißt nur du.
*Was die Antwort ändert:* Mit Befehlen schreibe ich sie je Steuerung in den Postprozessor (wie
„F_HOME“), sonst bleibt es bei M5, M9, M0. – seit 2026-10-17

**4. Nut auf der Drehmaschine mit axial angetriebenem Werkzeug: nur mit Y-Achse, oder auch ohne Y
über die C-Achse (polar)?**
Dein C-Ring auf der CLX (2026-10-17): „ich würde die nut da gerne rausfräsen, wie auf der
3-achsigen auch – leider klappt das nicht“. Heute lehnt „Bearbeitung“ Drehmaschinen ab („Weiter
geht auf der Drehmaschine nicht“), und der 4-Achs-Assistent denkt radial. Plan (W-025): „Bearbeitung“
von vorn auf der Drehmaschine – die Stirnfläche ist die Ebene „von oben“, das Werkzeug steht axial
im Revolver (Halter „VDI axial“), Z ist die Spindelachse, C steht; mit **Y-Achse** fährt es die
Bahnen in X/Y wie an der Fräse (deine CLX hat Y). Ohne Y müsste die Steuerung polar interpolieren
(Siemens TRANSMIT, Heidenhain Zyklus 800/polar) – ein eigener Postprozessor-Teil, und die
Reichweite/Kollision rechnet anders.
*Warum nur Manuel:* Ob die CLX das mit Y fahren soll (einfach, exakt wie an der Fräse) oder ob
auch Maschinen ohne Y das können müssen (polar), entscheidet den Umfang.
*Was die Antwort ändert:* „Nur mit Y“: ich baue W-025 so, dass „Bearbeitung“ die Drehmaschine mit
Y und axialem Halter annimmt – alles andere (Räumen, Nut, Kontur, Bohren, Messstopp) läuft dann wie
an der Fräse. „Auch polar“: dazu der Postprozessor-Teil, später. – seit 2026-10-17

