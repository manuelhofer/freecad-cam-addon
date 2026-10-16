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

**4. Soll Räumen Bohrung und Schlitz bis durch räumen, statt die Kontur sie ausfahren zu lassen?**
Manuel am C-Ring: „bis zuur mitte die D's noch weiter fahren und dann mit den reisen rausfahren“.
Bild mit Zahlen: [cring_schlitz_bohrung.png](bilder/vorschlaege/cring_schlitz_bohrung.png)
(Beispiel-C-Ring, Mantel, Bohrung und Schlitz gewählt, Schaftfräser Ø 8, ap 16, ae 1).
- Heute fährt dort die Kontur. Sie räumt die Bohrung allein aus: 7,1 min, Last bis 8,1 ae, 63 mm
  im Vollschnitt, 27 Rampen, 42 % Luft.
- Räumen bis durch (adaptiv, der Boden 0,5 mm unter dem Teil) fährt genau seinen Weg: D-Bögen
  von außen durch den Schlitz, in der Bohrung von der Mündung aus größer werdende Bögen, nirgends
  eintauchen. 4,2 min, Last bis 2,5 ae, kein Vollschnitt.
- Mit Ø 12 passt kein Fräser durch den 11,7 mm breiten Schlitz; Räumen taucht dann in der Bohrung
  mit der Helix ein (2,8 statt 5,35 min).

*Warum nur Manuel:* Für Wände, die durch das Teil gehen, trat bisher nur die Kontur an. Räumen dort
antreten zu lassen ist eine neue Strategiewahl.
*Was die Antwort ändert:* Bei „ja“ tritt an gewählten durchgehenden Wänden Räumen bis durch gegen
die Kontur an (die Zeit entscheidet), und „Schlichten danach“ macht die Wände fertig. Bei „nein“
bleibt die Kontur, und ihre Last in der Bohrung bleibt ein eigener Punkt. – seit 2026-10-16

**5. Soll ein angeklickter Boden eines Lochs „Bohrung fräsen“ meinen (bis Ø 40)?**
Seit P-2026-10-16-13 nimmt das Planfräsen keine Taschenböden mehr; das Räumen passt in ein Loch,
das nur wenig größer ist als der Fräser, nicht hinein (FreeCADs Adaptiv-Kern: „Start point not
found“; Ø 16 mit Ø 12, auch Ø 16 mit Ø 10 und 0,3 Aufmaß). Dann ging am Loch in der Schräge
(`szenario_loch_schraeg`, Manuels „Ich will nur dass Loch da fräsen“) und am Lagerbock (Gründe der
Senkungen Ø 14) gar nichts mehr. Seit P-2026-10-16-54 meint der Boden eines Lochs bis Ø 40 das Loch:
„Bohrung fräsen“ nimmt ihn, das Räumen nicht. Größere runde Taschen (die Platte, Ø 45) räumt das
Räumen wie bisher.
*Warum nur Manuel:* Was das Addon ohne Vorgabe wählt, entscheidet er; die Grenze Ø 40 ist von mir.
*Was die Antwort ändert:* Eine andere Grenze – oder die Grenze aus dem Fräser (z. B. Loch kleiner
als 2 × Fräser-Ø: Bohrung fräsen, sonst Räumen). – seit 2026-10-17

**6. Soll „3D-Schruppen“ nur über den gewählten Flächen schruppen (als Haken)?**
Manuel am Schwenkteil: „dann wird ausen alles mit bearbeitet ... vll hab ich ausen das schon in
einem anderen job und will einfach wirklich nur das was ich ausgewählt habe“ – zugleich „ich weis
nicht klar soll das auch gemacht werden“. Am Schwenkteil selbst ist es seit P-2026-10-16-54 gelöst:
Die schräge Tasche kommt in der geschwenkten Ebene dran, und dort räumt das Räumen nur sie. Für
echte Freiform (eine Kuppel auf einer Platte) habe ich es gebaut und wieder zurückgenommen: Nur
über der Kuppel ist der Bereich ringsum von Rohteil umgeben, wie eine Tasche. Die Ringe des
3D-Schruppens kommen vom Rand her und gehen dort voll hinein (Eingriff bis 5 ae, 10 × senkrecht
eintauchen; ganz: 1,9 ae). Richtig wäre es wie beim Räumen einer Tasche: in der Mitte per Helix
hinein und von innen nach außen.
Bild mit Zahlen: [frage6_schruppen3d_nur_ueber.png](bilder/vorschlaege/frage6_schruppen3d_nur_ueber.png)
(links heute, rechts der Versuch: die Ecken bleiben stehen, 6,1 → 4,3 min, aber Eingriff bis 5 ae). Der Stand liegt in `~/freecad_cam/wip/nacht_2026-10-16/r3_nur_ueber.patch`.
*Warum nur Manuel:* Was das 3D-Schruppen ohne Vorgabe wegnimmt, ist eine Strategiewahl.
*Was die Antwort ändert:* Bei „ja“ baue ich es mit Helix und Ringen von innen, als Haken
„Nur über den gewählten Flächen“ (vorbelegt an). Bei „nein“ bleibt es beim ganzen Rohteil. – seit 2026-10-17

