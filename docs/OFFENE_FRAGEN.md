# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

Die Fragen 1 bis 4 und die Frage zur Dichtnut hat Manuel am 2026-11-14 beantwortet (Verlauf
P-2026-11-14-06 und P-2026-11-14-10).

Die Fragen 1 bis 5 vom 14./15.11. hat Manuel am 2026-11-15 beantwortet (Verlauf P-2026-11-15-21; die
Aufträge daraus stehen im STATUS unter „Nächster Schritt“).

## 1. Hobelklingen der Hersteller: wie lang ist die Klinge hinter der Schneide? (seit 2026-11-15)

**Die Frage:** Gefunden sind 121 Stoß-/Hobelklingen mit Quellen (Horn Speed-Forming P105 – das einzige
echte Hobeln mit stehender, orientierter Spindel –, Horn S117/N105/N110, WNT SlotCut, GARANT, Iscar; Liste
`~/freecad_cam/wip/strategien/hobelklingen/klingen.json`). Für die Prüfung „Klinge gegen die Wand“ braucht
das Addon die **Länge der Klinge hinter der Schneide in Fahrtrichtung** und den **seitlichen Freiwinkel** –
beides steht in keinem Katalogtext, nur Plattenmaße (z. B. Horn P105: Plattenlänge 45, Rohlingsbreite 7).
Geht es so: (a) Du schaust bei einer Platte, die du hast oder kennst, nach (oder in der DXF aus dem
Horn-eShop, falls du ein Konto hast) und sagst mir, welches Katalogmaß dem entspricht; oder (b) ich nehme
vorsichtig das größte mögliche Maß (die Rohlingsbreite) – sicher, aber dann fährt die Klinge nur große
Radien.
*Warum nur Manuel:* Wie die Platte im Halter sitzt und was hinter der Schneide in der Nut steht, zeigt nur
die Zeichnung oder die Platte selbst; falsch geraten fährt die Klinge in die fertige Wand.
*Was die Antwort ändert:* ob die Klingen mit diesem Maß in die Werkzeugliste kommen.
