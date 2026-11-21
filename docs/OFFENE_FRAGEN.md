# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

Die Fragen 1 bis 4 und die Frage zur Dichtnut hat Manuel am 2026-11-14 beantwortet (Verlauf
P-2026-11-14-06 und P-2026-11-14-10).

Die Fragen 1 bis 5 vom 14./15.11. hat Manuel am 2026-11-15 beantwortet (Verlauf P-2026-11-15-21; die
Aufträge daraus stehen im STATUS unter „Nächster Schritt“).

Die Frage 1 vom 15.11. (Hobelklingen: Länge hinter der Schneide) hat Manuel am 2026-11-21 beantwortet
(Verlauf P-2026-11-21-01).

## 1. Rohr im Futter auf dem Rundtisch: dreht deine Steuerung den geschwenkten Rahmen mit, wenn C fährt? (seit 2026-11-21)

**Die Frage:** Seit 0.388.0 gibt es im Fenster „Programm schreiben“ den Haken „Rohr ungeschwenkt
einrichten“ (aus). Mit ihm richtest du ein, wie du es beschrieben hast (X 0 Y 0 mittig im Rohr, Z 0 oben an
der Stirn der Stange), das Programm schwenkt mit CYCLE800 (Heidenhain: PLANE SPATIAL) und dreht danach das
Rohr mit C. Das stimmt nur, wenn die Steuerung den geschwenkten Rahmen dabei **stehen lässt** und nicht mit
C mitdreht. Kannst du das an der 840D einmal ohne Teil ausprobieren, wenn sie frei ist: Programm mit Haken
schreiben, Tisch schwenken lassen, zusehen, ob die Spitze beim Drehen von C an derselben Stelle im Raum
bleibt?
*Warum nur Manuel:* Das zeigt nur die echte Steuerung; in den Handbüchern habe ich es nicht belegt gefunden,
und falsch angenommen fräst jeder Satz um den C-Winkel verdreht ins Teil.
*Was die Antwort ändert:* Bleibt der Rahmen stehen, wird der Haken vorbelegt an (dein Einrichten ist dann
der Standard). Dreht er mit, schreibe ich die C-Sätze unter TRAORI.
*Bis dahin:* Haken aus – es gilt der bisherige Weg „Nullpunkt nach dem Schwenken“.

## 2. 3D-Schlichten: „Zum Schluss eine Runde auf dem Teilboden“ – vorbelegt an? (seit 2026-11-21)

**Die Frage:** Seit 0.389.0 gibt es beim 3D-Schlichten unter „Werte ändern“ den Haken „Zum Schluss eine Runde
auf dem Teilboden“ (aus). Mit ihm fährt die Kugel am Ende einmal um die Unterkante, Spitze auf dem Boden.
Bild mit Zahlen: [unterkante_bodenrunde.png](bilder/vorschlaege/unterkante_bodenrunde.png) – Kuppel R 40,
Kugel Ø 6: Rest am Fuß höchstens 0,82 → 0,53 mm, Zeit 12,08 → 12,42 min (+0,34). Soll der Haken
**vorbelegt an** sein?
*Warum nur Manuel:* Was das Addon ohne Vorgabe wählt, ändere ich nie allein.
*Was die Antwort ändert:* ja → angehakt, sobald die Flächen den Teilboden erreichen; nein → bleibt aus.
