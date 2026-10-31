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

1. **Messen und korrigieren: Welches Werkzeug-Register soll der Zyklus korrigieren?** Die
   Konturprogrammierung steht (0.333.0: Schlichtkreis mit G41/G42, Radius aus der Werkzeugtabelle).
   Damit der Messzyklus den nächsten Gang selbst korrigiert, muss er den Radius-Verschleiß des
   Schlichtwerkzeugs ändern. Mein Vorschlag, wie es die meisten Werkstätten einrichten:
   **Siemens:** CYCLE977 mit „Werkzeugkorrektur“ auf D1 des Schlichtwerkzeugs (S_KNUM1 = 1,
   Radius-Verschleiß) – mit Werkzeugverwaltung über den Namen (`T="…"`), ohne über die T-Nummer;
   **Fanuc/Haas mit Renishaw:** `T` = die Nummer des D-Registers = Werkzeugnummer (Haas: D gleich
   T). Ist das so üblich, oder macht man es anders (eigene D-Nummer, nur Warnung statt Korrektur)?
   – *Warum nur Manuel:* wie es an den Maschinen eingerichtet wird. – *Was die Antwort ändert:*
   ob und wie der Zyklus nach dem Messen selbst korrigiert. – 2026-10-31.

Manuel, 2026-10-31 abends: Stufe 2 „1.b“ (Konturprogrammierung);
Bohrfräsen – „man muss klären wie die bohrfräsen definieren“ (Recherche läuft, siehe
konzept_schritt_assistent.md, Teil C).
