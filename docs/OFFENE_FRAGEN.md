# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

**3. Ist ein Absatz, der zu einer Seite offen ist, Planfräsen oder Räumen?**
Seit 0.260.11 nimmt Planfräsen keine Böden von Taschen und Nuten mehr (an mindestens drei
Vierteln des Rands steht eine Wand). Die räumt Räumen oder die Nut, wie Manuel am C-Ring sagte:
„planfräsen ist auf z0 bringen würde ich behaupten oder seitlich eine seite auf 0 bringen“.
Offen ist der Absatz: eine Stufe unter der Oberseite mit einer Wand und drei offenen Seiten. Im
Prüfstand (`absatz/planfraesen`) gewinnt dort Planfräsen mit 2,1 min. Die Zickzack-Rampe dort ist
seit 0.260.22 eine Helix (P-2026-10-16-25) – unabhängig von dieser Frage.
*Warum nur Manuel:* Was Planfräsen heißt, entscheidet er; „Absätze“ hat er nicht genannt.
*Was die Antwort ändert:* Bei „Räumen“ tritt Planfräsen nur noch für die Oberseite an (z0),
bei „Planfräsen“ bleibt es so. Dann ließe sich noch die Helix sparen: Die erste Zeile jeder Lage
beginnt an der Stufe (x 16, im Material) und läuft nach außen; andersherum, vom offenen Ende
(x 61, Luft), käme sie ohne Eintauchen hinein (die Richtung legt
`planfraesen_bahn._zellenfahrten` fest). – seit 2026-10-16
Testteil zum Anschauen (Manuel, 2026-10-17: „versth ich nicht gib mir ein testteil zum öffnen!“):
`~/freecad_cam/testteile/frage3_absatz.FCStd` – den tieferen Boden rechts (Face5) anklicken,
„Bearbeitung“ → „Weiter“: angehakt ist Planfräsen.
