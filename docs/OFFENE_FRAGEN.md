# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

**Frage 6 – Am Anfang fragen, wie du vorgehen willst?** Manuel, 2026-10-25, zu Frage 4: „oder vll
generell das system umbauen .. auf "hey wie willst du vorgehen sollen wir erst vorborhren … und dann
weiter machen oder sollen wir alles rausschruppen und dann schlichten usw usw usw..“. Gebaut ist
das Vorbohren als Haken im Räumen (0.286.0). Ein Schritt davor im Assistenten könnte so aussehen –
eine Zeile je Weg, mit der Zeit, die er an deinem Teil braucht, der schnellste vorgewählt:
1. **Wie bisher:** je Strategie die schnellste, du hakst an und ab.
2. **Erst vorbohren, dann räumen, dann schlichten** (wo eingetaucht wird).
3. **Alles schruppen, dann alles schlichten** (erst alle Schrupp-, dann alle Schlichtschritte,
   Werkzeugwechsel in dieser Folge).
4. **Du sagst, welche Wege** in deiner Werkstatt vorkommen – dann baue ich genau die.
*Warum nur Manuel:* Welche Folgen in Frage kommen und wie sie heißen sollen, ist deine Werkstatt;
nach „Strategiewahl erst besprechen“ wähle ich nichts davon selbst vor. *Was die Antwort ändert:*
ob Schritt 2 des Assistenten eine Wahl des Vorgehens bekommt und welche. – seit 2026-10-25.


**Frage 7 – Die Wände der tiefen Tasche: Spirale statt Flanke in zwei Lagen?** Zu Frage 5 hast du
die Spirale beschrieben („mit halt einer spirale nach unten … wenn es ecken gibt … eben anders
anstellen“) – gebaut (0.285.0), Bild `docs/bilder/vorschlaege/spirale_unter_dem_rand.png`. Heute
hakt der Assistent an deiner Tasche weiter die Flanke an (48 Umläufe in 2 Lagen, etwa 5 min) und
danach das 3D-Schlichten als Spirale (etwa 5 min). In der unteren Lage der Flanke liegt der Schaft
von T1 an der schon fertigen Wand an (Kollision prüfen: Satz 7684).
1. **Die Flanke bleibt fürs Grobe** (den Keil unter dem Rand), die Spirale macht die Wand fertig –
   so ist es jetzt; die Flanke dafür mit Aufmaß, damit der Schaft nicht an der fertigen Wand
   reibt (mein Vorschlag).
2. **Ohne Flanke:** den Keil schruppt die Kugel vor (Vorschlichten, wo zu viel steht), dann die
   Spirale.
3. **So lassen.**
*Warum nur Manuel:* Welche Strategie das Addon ohne Vorgabe wählt, entscheidest du
(„Strategiewahl erst besprechen“). *Was die Antwort ändert:* was an überhängenden Wänden
vorgeschlagen und angehakt ist. – seit 2026-10-25.
