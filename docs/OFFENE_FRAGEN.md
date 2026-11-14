# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

Die Fragen 1 bis 4 und die Frage zur Dichtnut hat Manuel am 2026-11-14 beantwortet (Verlauf
P-2026-11-14-06 und P-2026-11-14-10).

## 1. Rohr im Futter auf dem Rundtisch: wie richtest du den Nullpunkt ein? (seit 2026-11-14)

**Die Frage:** An der Tisch/Tisch steht das Rohr jetzt im Dreibackenfutter auf C, das Programm schwenkt A
auf −90 und dreht C. Gebaut ist: **Nullpunkt nach dem Schwenken** – A auf −90, C auf 0, dann Mitte Rohr
und Stirn antasten (G54; steht im Programmkopf und im Einrichtblatt). Im Programm steht dann nur die
Drehung, und es ist egal, wie hoch das Futter ist oder wie tief das Rohr steckt. Oder willst du lieber
**ungeschwenkt einmessen** (Rohr senkrecht) und die Steuerung schwenken lassen (Siemens CYCLE800/TRAORI,
Heidenhain PLANE/M128)? Dann rechnet die Steuerung den Abstand zur Schwenkachse aus ihrer eigenen
Kinematik – das hängt aber daran, dass sie richtig eingerichtet ist.
*Warum nur Manuel:* Wie man an seiner Maschine einrichtet, ist Werkstattpraxis.
*Was die Antwort ändert:* ob das Programm für diese Lage einen Schwenkzyklus schreibt oder A als einfache
Achse mit Koordinaten nach dem Schwenken. Bis zur Antwort bleibt es beim Nullpunkt nach dem Schwenken.

## 2. Dichtnut aus dem Vollen gehobelt: Darf die Nut ein paar Hundertstel schmaler werden? (seit 2026-11-14)

**Die Frage:** Die Klinge ist im Addon ein Rechteck (Breite × Länge hinter der Schneide). In der Kurve
schwenkt ihre hintere Ecke nach außen; dazu stellen Heidenhain, LinuxCNC, Haas, Fanuc und Mach den
Spindelwinkel vor dem Satz (die Klinge dreht einen halben Satzschritt voraus), Fanuc in ganzen Grad. Damit
die Ecke nie in die fertige Wand geht, bleibt die Spur dort etwas weiter weg – **die Nut wird je Seite
schmaler**: am Beispieldeckel (Nut 3,6, R 12, Klinge 3,5 × 0,8) im Mittel 0,023, höchstens 0,048 mm; mit
einer langen Klinge 2,6 × 1,4 bis 0,11 mm; Rechteck R 3 mit 2,6 × 1,0 bis 0,17 mm. Was ist dir lieber?
(a) so lassen und im Block die Abweichung zeigen; (b) einen Fräser die Wände danach nachfahren lassen (dann
ist es nicht mehr „ohne Fräsen“); (c) die Klinge mit seitlichem Freiwinkel rechnen (echte Hobelklingen
sind hinter der Schneide schmaler – dann schwenkt die Ecke kaum aus; dafür ein Maß am Werkzeug); (d) in
Kurven kürzere Sätze.
*Warum nur Manuel:* Welche Toleranz die Nut braucht und wie seine Klingen hinten aussehen, weiß nur er.
*Was die Antwort ändert:* wie breit die Nut wirklich wird; ob am Werkzeug ein Freiwinkel dazukommt.
Bis zur Antwort: (a) – die Klinge geht nie in die Wand, die Nut ist höchstens so viel schmaler.
