# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

**Frage 1 – Ein eigener Name fürs Addon?** „CAM-Addon“ (im Addon-Manager „CAM Addon“, das Menü
„CAM-Addon“) klingt nach einem Teil von FreeCAD CAM – genau das stört die CAM-Entwickler (Discord,
2026-10-23: „at least 3 forks or addons competing“). Ein eigener Name machte von selbst klar, dass
es ein Werkstatt-Addon neben CAM ist. Umbenannt würde nur, was man sieht (Name im Addon-Manager,
Menü, Fenstertitel, Hilfe); die Adresse auf GitHub, der Ordner und die Module bleiben – sonst
fänden „Nach Updates suchen“ und gespeicherte Dateien nichts mehr. Vorschläge:
1. **Werkstatt-CAM** (englisch „Shop Floor CAM“) – sagt, wofür es ist.
2. **CAM-Werkstatt** („CAM Workshop“).
3. **Zerspaner-Assistent** („Machinist's Assistant“) – sagt, für wen.
4. Ein Name, den du dir ausdenkst.
5. So lassen.
*Warum nur Manuel:* Es ist dein Addon und dein Name nach außen. *Was die Antwort ändert:* Name im
Addon-Manager, Menü und Hilfe (de/en), README; nichts an Bahnen oder Dateien. – seit 2026-10-24.


**Frage 4 – Ganze Abfolgen vorschlagen, damit es schneller geht?** Manuel, 2026-10-25, an seiner
tiefen Tasche: „man könnte nun hier auch damit es schneller geht erstmal bohren .. oder
rausschruppen mit nem größeren fräser gerade .. oder oder oder es gibt ja viele möglichkeiten“ –
„lass uns mal drüber reden“. Heute empfiehlt das Addon nur Halter und Auskragung (und einen Fräser
für die Ecken). Eine Stufe höher hieße: ganze Abfolgen nach Zeit vergleichen und die schnellste
vorschlagen, auch mit Werkzeugen, die man nicht hat. Mein Vorschlag zum Anfangen, an deiner Tasche,
mit Bild und Zahlen:
1. **Räumen T1** wie jetzt (Ringe von innen, 2 min),
2. **erst bohren** (ein Bohrer Ø 30 … 40 in die Mitte, dann Räumen),
3. **erst ein großer Schaftfräser** (Ø 25 … 32, kurz und steif), dann T1 nur, was er stehen lässt,
4. du nennst, welche Wege du in der Werkstatt gehst.
**Gemessen (0.283.3, deine Tasche an der G550, Kopie):** Räumen T1 von oben ≈ 2 min, Flanke T1
≈ 6 min (4 Umläufe je Wand für den Keil 6,5 mm bei „quer“ 2,4, in 2 Lagen; seit 0.283.4 oben nur
die nötigen: 48 statt 64 Umläufe, gut ein Fünftel weniger), 3D-Schlichten T3 der
Rundungen ≈ 5 min (Grathöhe 0,01; mit 0,02 4 min), Restschlichten der Ecken Ø 6 ≈ 1 min –
zusammen ≈ 14 min. Vorbohren und ein größerer Fräser sparen nur am Räumen (2 von 14 min); mehr
brächte die Flanke (weniger Umläufe am Keil).
*Warum nur Manuel:* Welche Abfolgen in Frage kommen und was „schneller“ wert ist (Werkzeugwechsel,
Rüsten, Kauf), ist deine Werkstatt. Nach der Regel „Strategiewahl erst besprechen“ wähle ich nichts
davon selbst vor. *Was die Antwort ändert:* Welche Abfolgen das Addon rechnet und als Empfehlung
zeigt (wie „So einrichten“). – seit 2026-10-25.
