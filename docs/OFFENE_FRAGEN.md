# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

Die Antworten vom 2026-10-31 auf die Fragen 1–8 (Beta-Assistent, Spannmittel, Kataloge) und was
daraus folgt, stehen in [konzept_schritt_assistent.md](konzept_schritt_assistent.md), Teil C.

Die Antworten vom 2026-10-31 nachmittags (Messtaster, Tauchfräsen, Hoffmann-Abruf) stehen in
[konzept_schritt_assistent.md](konzept_schritt_assistent.md), Teil C.

Frage 1 (Messen und korrigieren) beantwortet, Manuel, 2026-10-31: „ja mach das so“ (der
Messzyklus korrigiert den Schlichtfräser selbst, als Haken) – gebaut 0.335.0.

**Frage 2 (An FreeCAD CAM angleichen): Die Schnittstellen angleichen – oder auch die Namen im Code?**
Manuel, 2026-11-02: „vll sollten wir ein wenig dann auch unsere variablennamen und sowas anpassen an die
arbeit die die jungs machen … in kleinen schritten könntest du das durchaus umstellen“. Vorschlag:
nicht die über 100 000 Zeilen deutscher Namen umbenennen (viel Aufwand, viel Bruchgefahr, bringt
für die Zusammenarbeit wenig), sondern in kleinen Schritten die Schnittstellen: Spannmittel im Format
von Connors Bibliothek bzw. aus ihr, Prüfen/Kollision über FreeCADs neuen Simulator (Zusage an
Connor), Werkzeuge/Halter in FreeCADs Formaten (ToolBit, Asset-Store), Maschinen als FreeCADs
Maschinendefinition; neue Dateien und öffentliche Funktionen englisch im FreeCAD-Stil. *Warum nur
Manuel:* Es ändert die Richtung des Projekts. *Was die Antwort ändert:* Ob ich ab jetzt neue
Schnittstellen englisch baue und einen Plan zur Angleichung schreibe. – seit 2026-11-02.

**Frage 1 (Hoffmann-Abruf): Täglich einen Lauf bis zur Sperre – oder hier aufhören?** Am 31.10. sperrte
Hoffmann nach 556 Anfragen (15–25 s Abstand), am 01.11. schon nach 93 (40–70 s) – das sieht nach
einem Tageskontingent aus, nicht nach dem Tempo. Es fehlen noch rund 900 Artikelgruppen (etwa 4500
Seiten). Mit einem Lauf je Tag, der bei der ersten Sperre aufhört, wären es grob ein bis zwei
Wochen; im Katalog stehen von Hoffmann schon 225 Bohrer-Reihen (16 234 Größen) und die
Fräser-/Rest-Reihen. *Warum nur Manuel:* Ein täglicher Neustart nach einer Sperre ist ein
Wiederholen nach Sperre – das mache ich nur mit deinem Ja (eine andere IP/VPN o. Ä. nutze ich nicht).
*Was die Antwort ändert:* Ob der Abruf jeden Tag einmal startet. – seit 2026-11-01.

Frage 2 (Brillenbohrung) beantwortet, Manuel, 2026-10-31: „ja wenn das vom hersteller die
genannte methode ist“ – gebaut 0.334.0.

Manuel, 2026-10-31 abends: Stufe 2 „1.b“ (Konturprogrammierung, gebaut 0.333.0).
