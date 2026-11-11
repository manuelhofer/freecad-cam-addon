# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

## Frage 1 – Die Beispiel-Werkzeuge für neue Nutzer: welche, mit welchen Werten?

Seit 0.352.0 bietet der Assistent „Beispiel-Werkzeuge anlegen“, wenn die Werkzeugverwaltung keinen Fräser hat
(neu installiert): die vier aus `werkzeuge.testkiste()` – Schaftfräser Ø 12 (T1), Planfräser Ø 50 (T2: ae 35,
ap 2, vc 200, fz 0,15), VHM Ø 6 (T3: ae 0,6, ap 12, vc 85, fz 0,05), VHM Ø 20 (T4: ae 2, ap 30, vc 85,
fz 0,12). Die Werte sind angenommen (für die Szenarien gedacht), der Tooltip sagt „vor dem Fräsen anpassen“.

*Warum nur Manuel:* Welche Werkzeuge ein Einsteiger wirklich hat und welche Werte vorsichtig genug sind, ist
Werkstattwissen. *Was die Antwort ändert:* die Liste und die Werte der Beispiel-Werkzeuge (etwa ohne
Planfräser Ø 50, mit einem Bohrer und einer Kugel dazu, vorsichtigere Werte). Seit 2026-11-11.
