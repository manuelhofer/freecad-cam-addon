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
Räumen wie bisher, ebenso eine runde Tasche mit einem Zapfen im Boden (P-2026-10-17-03); der Boden
einer Senkung über einer kleineren Bohrung meint die Senkung.
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

**7. Waagerechte Spindel (G550): Wie soll ein Job „von oben“ den Tisch anstellen?**
Nachgespielt an deinem Schwenkteil auf der Beispiel-G550 (T-015): Die Tasche oben, „Bearbeitung“,
Räumen T1 – „Auf der Maschine prüfen“ fährt mit A = 0, die waagerechte Spindel kommt von der Seite,
und darunter steht „so gefahren, passt sie nicht zum Teil“. Legt man dieselbe Tasche in eine
Ebene „oben“, stellt die Maschine den Tisch auf A1 −90° (im Programm „A90 B0“), und es passt. Zwei
Wege: (a) An einer Maschine, deren Spindel in Grundstellung nicht längs Z des Jobs steht, kommt
alles „von oben“ in eine solche Ebene – wie seit P-54 die schrägen Flächen (der Grundjob bleibt
leer, das Programm schwenkt einmal). (b) Der Job selbst bekommt eine feste Grundstellung der
Rundachsen (A −90), Prüfung, Programm und Abfahren nehmen sie überall.
Bild: [frage7_g550_oben.png](bilder/vorschlaege/frage7_g550_oben.png) – links der Job „von oben“
(A1 0°, unten der Satz „passt sie nicht zum Teil“), rechts dieselbe Tasche in der Ebene „oben“
(A1 −90°, im Programm „A90 B0“, kein Hinweis).
*Warum nur Manuel:* Es ändert, wie Jobs an einer waagerechten Maschine aussehen und was im
Programm steht; du kennst die GROB und deine 840D.
*Was die Antwort ändert:* (a) ist schnell gebaut (dieselbe Kette wie die Schrägen), (b) ist der
saubere Weg für alle Strategien, aber ein größerer Umbau. – seit 2026-10-17


**8. Soll das Planfräsen an der Wand ohne Hin und Her fahren?**
Bei der Zickzack-Durchsicht gezählt (Programme des vollen Laufs, Rücksprünge unter 2 mm auf einer
Höhe): Das Planfräsen fährt an einer Wand bei jeder zweiten Zeile 1,5 mm zur vorigen Zeile zurück
und wieder vor – die „Wandfahrt“ (seit P-2026-10-01). Am Block 68-mal, an der Platte 17-mal, am
Klotz 22-mal. Sie nimmt den Zwickel, der an der Wand zwischen zwei Zeilen stehen bliebe: beim
Schaftfräser Ø 12 mit ae 1,5 rund ae² ÷ 8R = 0,05 mm (mit Eckenradius mehr). Mit der Kontur
danach ist er ohnehin weg.
Bild: [frage8_wandfahrt.png](bilder/vorschlaege/frage8_wandfahrt.png) – der Absatz, rot die
14 Wendepunkte an der Wand.
Wege: (a) so lassen; (b) statt der vielen kleinen Rückwege ein Zug an der Wand entlang am Ende
der Lage, in einer Richtung; (c) beim Schaftfräser ohne Eckenradius weglassen, wenn die Wand
gewählt ist und die Kontur sie danach fertig macht.
Versuch zu (b), im Prüfstand gemessen (Rest an der Wand in allen Fällen 0):
[frage8_wandzug.png](bilder/vorschlaege/frage8_wandzug.png)
- Absatz (eine Wand): Wendepunkte 14 → 0, Bahn 2,10 → 2,15 min.
- Zwei Wände gegenüber: 28 → 0, 1,92 → 1,97 min (je Wand ein Zug, dazwischen auf der ersten
  Zeile hinüber).
- Zapfen in der Mitte (Insel): unverändert 11 – um eine Insel müsste die Wandfahrt bleiben.
Der Versuch liegt in `~/freecad_cam/wip/nacht_2026-10-17/wandzug_frage8.patch`.
*Warum nur Manuel:* Es ist eine Abwägung zwischen dem Zwickel an der Wand und dem Hin und Her –
P-2026-10-16-67 hat es nur dort weggenommen, wo es durch die Luft ging.
*Was die Antwort ändert:* Bei (b) oder (c) baue ich es um; der Prüfstand misst den Rest an der
Wand mit. – seit 2026-10-17

**9. Soll der Name einer Ebene die Rundachsen so nennen, wie die Steuerung sie zeigt?**
Am Schwenkteil auf der G550 heißt die Ebene „Schwenkteil – Fräsen – Ebene Face27 (A60 B0)“, das
Fenster „Ebene schwenken“ sagt ebenso „→ A60 B0“. Im Programm steht aber „G0 A-60.000 B0.000“
(Kommentar „Ebene geschwenkt: A-60 B0“), und „Auf der Maschine prüfen“ zeigt „A1 −60°“ – so,
wie die Steuerung zählt (DIN 66217; das Gelenk der Beispiel-G550 dreht andersherum). Name und
Schwenk-Fenster zeigen die Stellung des Gelenks im Modell, Prüffenster und Programm die der
Steuerung; die Bahnen sind dieselben.
*Warum nur Manuel:* Du liest den Namen und vergleichst mit dem, was die Maschine anzeigt; seit der
CLX550 gilt „nur der Postprozessor dreht um“ – ob das auch für Namen und Fenster gelten soll,
entscheidest du.
*Was die Antwort ändert:* Bei „ja“ zeigen Name, „Ebene schwenken“ und „Alles aus dieser
Aufspannung“ die Werte der Steuerung (A−60 B0); gerechnet wird weiter mit dem Gelenk. – seit
2026-10-17
