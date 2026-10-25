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

**Frage 3 – Deine tiefe Tasche (testteil5achstief): Wie soll die Flanke den Keil unter dem Rand
nehmen?** Bild: [`bilder/vorschlaege/tiefe_tasche_hinterschnitt.png`](bilder/vorschlaege/tiefe_tasche_hinterschnitt.png).
Deine Tasche ist unten weiter als oben: Die Wände hängen 8,5° über (oben Y ±30, unten ±36,5),
50 mm tief. Von oben räumt das Räumen nur bis unter den Rand (3 Lagen, etwa 3 min). Unter dem Rand
bleibt ein Keil stehen, oben 0, unten 6,5 mm dick. Die Flanke kann die Wand mit dem um 8,5°
gekippten T1 Ø 12 fräsen (gebaut, auf einem Zweig, noch nicht bei dir): 16 Umläufe in 2 Lagen,
etwa 2 min. Dein „Extra lang“ bleibt dabei 11 mm über dem Rand, mit 54 statt 48 mm ausgespannt
(das bietet der Assistent als Link an). Nur nähme sie den Keil heute **in einem Umlauf**: unten
bis 6,5 mm seitlich (55 % vom Ø), je Lage gut 20 mm tief, mit 54 mm draußen.
1. **A – erst Umläufe davor, je ae deines Schruppeinsatzes, von innen nach außen, dann einer auf
   Maß** (im Bild gestrichelt 4 und 2 mm davor). Etwa 3–4 statt 1 Umlauf je Lage. Mein Vorschlag.
2. **B – ein Umlauf, aber mit weniger Vorschub**, so dass die Spandicke stimmt.
3. **C – den Keil mit einem anderen, kürzeren Fräser** (welcher?).
*Warum nur Manuel:* Wie viel ein langer Ø 12 seitlich verträgt, weißt du von deiner Maschine.
*Was die Antwort ändert:* wie die Flanke an Hinterschnitten zustellt. Erst danach kommt sie auf
main. – seit 2026-10-25.
Dazu, ohne Frage: An deiner G550 (Spindel waagerecht) käme die Flanke im Programm **vor** dem
Räumen der Ebene „von oben“. Das ist ein Fehler, auch bei normalen Formschrägen, und den behebe
ich. Die Rundungen R 7 am Boden unter dem Rand erreicht die Flanke nicht. Dafür baue ich danach
etwas.

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
An deinem Testteil ändert A nichts: Dort ist Adaptiv mit 10,35 min ohnehin am schnellsten (die
Ringe 11,63 min). A liegt fertig und geprüft auf dem Zweig `frage2-a` (nur bei mir, nicht auf
GitHub).
*Warum nur Manuel:* Es ändert, was das Addon in jeder Tasche von sich aus wählt. *Was die Antwort
ändert:* die Wahl der Variante beim Räumen (`raeumen_bahn.planen`), mit B auch die Morph-Spirale
(`_ringe_morph_tasche`, bis dahin aus). – seit 2026-10-24.
