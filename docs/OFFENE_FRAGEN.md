# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

**1. Darf der Assistent selbst einen kleineren Fräser nehmen, wenn der gewählte nicht hineinpasst?**
Am C-Ring und am Ring kam Ø 12 nicht in die 10 mm breiten Nuten. Seit 0.260.5 nehmen Planfräsen
und Räumen dann von selbst den größten ihrer Fräser, der mit 0,5 mm Luft je Seite hineinkommt (am
C-Ring T3 Ø 6). Über den Strategien steht: „T1 Schaftfräser Ø 12 kommt nicht in Face8 – Planfräsen
und Räumen nehmen T3 Schaftfräser Ø 6.“ Die Nut macht das schon lange so. Die Alternative: den
gewählten Fräser lassen und nur rot melden, dass er nicht hineinkommt.
*Warum nur Manuel:* Was das Addon ohne Vorgabe wählt, entscheidet er. Ein Fräserwechsel kostet
an der Maschine Zeit, und vielleicht will er lieber selbst wählen.
*Was die Antwort ändert:* Bei „nur melden“ bleibt der Fräser, und die rote Zeile sagt, welcher
passen würde, mit einem Knopf zum Übernehmen. – seit 2026-10-16

**2. Sollen die Besprechungen in ein eigenes, privates Repository?**
Seit 0.260.6 (P-2026-10-16-08) lädt das Update nur noch, was das Addon zum Laufen braucht. `docs/`
(Verlauf, Snapshot, diese Fragen, Forumbilder), `tests/` und `scripts/` bleiben draußen, das ZIP
schrumpft von 15,6 auf 9,7 MB. Auf GitHub stehen diese Dateien aber weiter öffentlich, samt
ihrem ganzen Verlauf. Die Alternative ist ein zweites, privates Repository, etwa
`freecad-cam-addon-entwicklung`, mit `docs/archiv`, `STATUS_SNAPSHOT.md`, `OFFENE_FRAGEN.md`,
`CHATSTART.md` und den Bildern; im Addon bleiben Code, Hilfe, Übersetzungen und Prüfungen. Aus
dem alten Verlauf auf GitHub verschwinden sie nur, wenn man die Geschichte umschreibt.
*Warum nur Manuel:* Ein neues Repository legt er an (oder erlaubt es), und den Verlauf auf
GitHub umzuschreiben ist nicht rückgängig zu machen.
*Was die Antwort ändert:* Bei „ja“ zieht alles Besprochene um, und die Arbeitsregeln zeigen
auf das neue Repository. – seit 2026-10-16

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

