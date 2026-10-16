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

**3. Sollen die großen Beispielteile im Update bleiben?**
Von den 9,7 MB sind 8,3 MB Beispiele: die Nase (`testteil_4achs_nase.FCStd`, 5,2 MB), der Geist
(`geist_stl/Geist1_v2.stl`, 3,3 MB) und das Freiform-Beispiel. Ohne sie wären es etwa 1,5 MB.
Sie stehen in `beispiele/README.md` als „Teile zum Ausprobieren“.
*Warum nur Manuel:* Ob Nutzer die Beispiele mitbekommen sollen, ist seine Entscheidung.
*Was die Antwort ändert:* Bei „raus“ bleiben sie auf GitHub zum Herunterladen, und die Hilfe
verweist dorthin. – seit 2026-10-16
