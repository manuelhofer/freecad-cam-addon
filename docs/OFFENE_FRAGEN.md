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

## 2. Welchen seitlichen Freiwinkel haben deine Hobelklingen? (seit 2026-11-14)

**Die Frage:** Am Stoßwerkzeug gibt es jetzt das Maß „Seitlicher Freiwinkel“ (deine Antwort auf die
vorige Frage: „C und D“). Mit 2° wird die Nut am Deckel je Seite nur noch im Mittel 0,006 mm (höchstens
0,015) schmaler statt 0,025 (0,047); mit einer langen Klinge 2,6 × 1,4 0,007 (0,046) statt 0,034 (0,095).
Steht nichts am Werkzeug, rechnet das Addon die Klinge als Rechteck (0°) – sicher, aber schmaler.
Welchen Winkel haben deine Klingen üblicherweise? Dann belegt der Knopf „Stoßwerkzeug … anlegen“ ihn vor.
*Warum nur Manuel:* Wie seine Klingen hinten geschliffen sind, steht in keinem Modell.
*Was die Antwort ändert:* die Vorgabe beim Anlegen eines Stoßwerkzeugs (bis dahin 0° – ein Rechteck).

## 3. Bohrung in zwei Schnitten: wo kommen Messstopp und zweiter Schnitt hin? (seit 2026-11-14)

**Die Frage:** „Weiter bearbeiten“ → „Löcher“ legt jetzt mit „In zwei gleichen Schnitten“ an: Bohrung
fräsen (Wand 0,15) → Leerfahrt → Messstopp (Ø 29,7) → Bohrung auf Maß → Leerfahrt. Diese Folge hängt
heute **hinten am Job**, also nach Senken und Gewinde aus demselben Schritt (wie beim Schlichten).
(a) so lassen – weniger Werkzeugwechsel; oder (b) direkt hinter „Bohrung fräsen“ – die Bohrung ist fertig
und gemessen, bevor gesenkt wird, dafür ein Werkzeugwechsel mehr. Empfehlung: (b).
*Warum nur Manuel:* Reihenfolge an der Maschine ist Werkstattpraxis.
*Was die Antwort ändert:* wo „Anlegen“ die Folge einsortiert. Bis zur Antwort: (a).

## 4. Rest an der Unterkante: Restschlichten von selbst anhaken? (seit 2026-11-15)

**Die Frage:** Seit 0.382.0 sagt die Übersicht nach dem 3D-Schlichten „An der Unterkante bleibt ein Rest bis
1,3 mm hoch“ (rot im Teil) und bietet „Restschlichten mit T5 anhaken“ an (Kuppel R 20, Kugel Ø 6 → mit
Ø 2 bleiben 0,3 mm). Soll das Restschlichten in diesem Fall **von selbst angehakt** sein, wenn eine
passende kleinere Kugel da ist (abwählbar)? Heute muss man den Verweis anklicken.
*Warum nur Manuel:* Was das Addon ohne Vorgabe wählt, entscheidet er.
*Was die Antwort ändert:* die Vorgabe des Hakens „Restschlichten“ bei Rest an der Unterkante.

## 5. Hobeln ohne Halt je Satz: wie heißt die Frässpindel deiner 840D als Achse? (seit 2026-11-15)

**Die Frage:** Seit 0.383.0 gibt es in „Programm schreiben“ beim Hobeln den Haken „Spindel als Rundachse
mitführen (ohne Halt je Satz)“ (Vorgabe aus). Für Siemens schreibt er `M70`, dann je Satz `C=DC(w)` in der
Bahn, am Ende `M5`. Ob deine 840D (powerline) M70 annimmt und die Spindel als Achse „C“ heißt (oder SP1,
C1 …), steht in den Maschinendaten. Probe im MDA **ohne Werkzeug im Eingriff**: „M70“, dann
„G1 X10 C=DC(90) F500“, dann „M5“ – fährt die Spindel mit X auf 90° und kommt kein Alarm, passt die Vorgabe.
*Warum nur Manuel:* Nur die Maschine zeigt es.
*Was die Antwort ändert:* den vorbelegten Achsnamen (änderbar unter „Befehle“).
Dazu, falls es geht: Hast du eine Heidenhain mit Option 96 (Zyklus 291), an der man in der Luft probieren
kann, wohin Q336 die Schneide stellt? Dann ließe sich Interpolationsdrehen der runden Nut auch für
Heidenhain einbauen.
