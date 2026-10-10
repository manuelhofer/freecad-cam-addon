# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

## Nur in Manuels FreeCAD zu sehen

1. **Felder „Auflösung“ (Assistent „Bearbeitung“, 4-Achs-Assistent) und „Bahn gerechnet für“
   (5-Achs-Vergleich): Trägt die Erklärung in Beschriftung, Tooltip und Hilfe – samt dem Beispiel,
   wo feiner nichts mehr bringt?**
   *Warum nur Manuel:* Ob ein Dialog verständlich ist, prüft nur er (CLAUDE.md).
   *Was die Antwort ändert:* Texte nachschärfen.
   Seit 2026-10-09 (P-2026-10-09-14, -17, -18, P-2026-10-10-03).

## Entscheidungen

2. **Rundum schlichten mit gewählten Flächen: Sollen die Linien über die Kante der Fläche
   hinauslaufen?** Heute laufen sie um den Fräserradius über die Kante (Bereich der Flächen plus
   Radius, `vierachs_flaechen.bereich_fuer`), damit die Fläche bis zur Kante fertig wird; dahinter
   folgt die Spitze dem Teil plus Aufmaß – auf dem Zylinder nimmt sie dort das Schruppaufmaß weg und
   lässt eine Stufe, wo die Linie endet. Manuel, 2026-10-10 (Screenshot): „er fährt hier auch über die
   ecken drüber … wenn dann mit aufmass aber ist das überhaupt nötig?“
   *Optionen:* (a) wie heute; (b) **an der Kante enden** – die Mitte des Fräsers bleibt über der
   Fläche, die Berührung reicht genau bis zur Kante, der Zylinder bleibt unberührt (Empfehlung:
   keine Stufe, die Kante wird trotzdem fertig); (c) über die Kante, aber dahinter mit dem
   Schruppaufmaß angehoben.
   *Warum nur Manuel:* Wie die Kante am Werkstück aussehen soll, entscheidet der, der es fräst
   (Arbeitsregeln: die Strategiewahl wird besprochen, nicht allein geändert).
   *Was die Antwort ändert:* die Grenze der Linien in `vierachs_bahn` (Muster LINIEN) und die Hilfe.
   Seit 2026-10-10.

## Stand bei Manuel

3. **Ist das 5-Achs-Testteil (`testteil5achsausweichfraesen.FCStd`) fertig?**
   *Warum nur Manuel:* Es ist sein Teil außerhalb des Repos; bis er es fertig meldet, wird es weder
   gemessen noch eingecheckt.
   *Was die Antwort ändert:* Es wird Messbeispiel für 5-Achs-Vergleich und Kollision.
   Seit Anfang Oktober 2026.
