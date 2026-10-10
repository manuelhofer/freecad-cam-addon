# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

## Entscheidungen

1. **Soll das Feld „Auflösung“ (Eigenschaft `Raster`) auch bei Plan indexiert, Rundum entgraten,
   Entgraten 3D und Flanke erscheinen?**
   *Warum nur Manuel:* Ihr Schritt sitzt ohne Parameter tief in der Bahn; das Feld dort kostet einen
   Umbau je Strategie. Ob er sich lohnt, hängt allein davon ab, ob Manuel die Auflösung dort braucht.
   *Was die Antwort ändert:* bauen (und bei welchen) oder bleibt wie es ist.
   Seit 2026-10-09 (T-009, P-2026-10-09-18).

2. **Was zuerst: der Werkzeugkiste-Import (T-007; die Hoffmann-Datei `werkzeugkiste_hoffmann_2026-10-07.json`
   passt zum Format) oder die weiteren Rechenhebel (Halter/Spindel mit numpy, „Alle Kombinationen“
   parallel, `fahren` in Stücken)?**
   *Warum nur Manuel:* Beides ist beschrieben und baubar; welches ihm zuerst nützt, ist seine
   Prioritaet, nicht ableitbar.
   *Was die Antwort ändert:* den nächsten Patch.
   Seit 2026-10-09.

## Nur in Manuels FreeCAD zu sehen

3. **4-Achs-Assistent: Ist das Ändern der seitlichen Zustellung jetzt ohne „Lag“?**
   *Warum nur Manuel:* Die Vorschau rechnet seit P-2026-10-09-09 im Hintergrund; ob sich das Fenster
   flüssig anfühlt, zeigt kein Screenshot, nur seine Hand an seinem Rechner.
   *Was die Antwort ändert:* bei „noch Lag“ die Hüllfläche in kleinere Aufträge zerlegen.
   Seit 2026-10-09.

4. **Felder „Auflösung“ (Assistent „Bearbeitung“, 4-Achs-Assistent) und „Bahn gerechnet für“
   (5-Achs-Vergleich): Trägt die Erklärung in Beschriftung, Tooltip und Hilfe?**
   *Warum nur Manuel:* Ob ein Dialog verständlich ist, prüft nur er (CLAUDE.md).
   *Was die Antwort ändert:* Texte nachschärfen.
   Seit 2026-10-09 (P-2026-10-09-14, -17, -18).

## Stand bei Manuel

5. **Ist das 5-Achs-Testteil (`testteil5achsausweichfraesen.FCStd`) fertig?**
   *Warum nur Manuel:* Es ist sein Teil außerhalb des Repos; bis er es fertig meldet, wird es weder
   gemessen noch eingecheckt.
   *Was die Antwort ändert:* Es wird Messbeispiel für 5-Achs-Vergleich und Kollision.
   Seit Anfang Oktober 2026.
