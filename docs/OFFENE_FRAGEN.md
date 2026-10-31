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

1. **Messen und korrigieren (Stufe 2): Wie soll die Radiuskorrektur an die Maschine?** Damit ein
   Messwert den nächsten Schlichtgang korrigiert, muss die Steuerung den Radius ausgleichen
   (G41/G42) – heute schreibt das Addon Mittelpunktbahnen ohne Korrektur. Zwei übliche Wege:
   **(a) Verschleißmodus:** weiter die Mittelpunktbahn, dazu G41/G42 mit einer eigenen D-Nummer
   (z. B. D2), in der an der Maschine Radius 0 steht – nur der Verschleiß wirkt; der Messzyklus
   schreibt die Abweichung in diesen Verschleiß. Vorteil: dieselbe Bahn wie heute; Nachteil: an
   der Maschine je Werkzeug ein zweites D anlegen. **(b) Konturprogrammierung:** die Schlichtgänge
   als Kontur des Teils mit G41/G42 und dem vollen Radius aus der Werkzeugtabelle, wie von Hand
   programmiert; der Zyklus korrigiert den Radius-Verschleiß des Werkzeugs. Vorteil: wie an der
   Maschine gewohnt; Nachteil: falscher Radius in der Tabelle = falsche Kontur. Mein Vorschlag:
   (a) als Haken je Postprozessor, vorbelegt aus, D-Nummer einstellbar. – *Warum nur Manuel:*
   wie die Werkzeugtabellen in der Werkstatt geführt werden. – *Was die Antwort ändert:* wie der
   Postprozessor die Schlichtgänge nach einem Messen schreibt. – 2026-10-31.
