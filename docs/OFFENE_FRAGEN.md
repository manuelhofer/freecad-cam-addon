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

**Frage 2 – Taschen: die schnellste Bahn, die die Last hält – auch fein gerechnet?** Bild:
[`bilder/vorschlaege/tasche_ringe_morph.png`](bilder/vorschlaege/tasche_ringe_morph.png) (Tasche
10 tief, T1 Ø 12, ae 4,8, ap 5; oben ein Rechteck 50 × 30, unten ein L). Heute nimmt das Räumen in
einer Tasche **Adaptiv** (1,79 und 2,32 min): Die Ringe von innen nach außen halten beim ersten
Rechnen die Last nicht (bis 2,35 ae in den Ecken). Fein gerechnet – zwischen zwei Ringe kommen
Teilstücke, nur wo die Last es verlangt – halten sie sie (1,49 und 1,24 ae) und brauchen **0,96
und 0,92 min**, gut die Hälfte. Das Feinrechnen probiert das Addon bisher nur, wenn gar keine
Variante die Last hält. Nach deiner Regel („das was schneller ist ... gewinnt .. wenn man volle
Tiefe fräst muss der ae schon in einem Rahmen bleiben“) müssten die Ringe gewinnen. Deine
**Morph-Spirale** (Helix in der Mitte, dann nach außen bis an die Wand – „wenn man von ausen nicht
rein kommt eine helix fahren und dann morpfspirealen rausfahen“) habe ich gebaut: im Rechteck
1,06 min, Last bis 1,66 ae; in einer lang gestreckten Tasche wie dem L kommt sie nicht bis in die
Enden der Schenkel, dort gäbe es sie nicht.
1. **A – die schnellste, die die Last hält, auch fein gerechnet** (hier die Ringe, halbe Zeit).
   Mein Vorschlag.
2. **B – wie A, dazu in kompakten Taschen die Morph-Spirale:** Sie gewinnt, wo sie schneller ist
   (hier nicht: 1,06 gegen 0,96 min). Ihr Vorteil ist der runde Lauf ohne Ecken.
3. **C – so lassen:** Adaptiv hat den gleichmäßigsten Eingriff (Last unter 1 ae), braucht aber
   etwa doppelt so lange.
*Warum nur Manuel:* Es ändert, was das Addon in jeder Tasche von sich aus wählt. *Was die Antwort
ändert:* die Wahl der Variante beim Räumen (`raeumen_bahn.planen`), mit B auch die Morph-Spirale
(`_ringe_morph_tasche`, bis dahin aus). – seit 2026-10-24.
