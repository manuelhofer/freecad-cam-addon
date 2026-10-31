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

1. **Messen: Soll das Programm die Korrektur selbst eintragen oder nur anhalten?** Was gebaut
   ist: Nach „Weiter bearbeiten“ mit Messstopp weiß das Programm, was zu messen ist – z. B. Tasche
   60 × 40 nach einem Gang mit 0,3 Aufmaß: Soll 59,4 × 39,4 (auf halber Wandhöhe; auch Zapfen,
   Bohrung, Welle). Ohne Taster hält es mit „Messstopp: Tasche 59,4 × 39,4 mm ±0,02 messen, dann
   NC-Start“; mit Taster misst der Zyklus der Steuerung und hält nur, wenn es außerhalb liegt.
   Die Frage: Ist die Tasche 0,04 zu klein, trägt man von Hand beim Schlichtwerkzeug den Radius-
   Verschleiß −0,02 ein. **Soll das der Messzyklus selbst tun** (spart den Halt; misst der Taster
   falsch, verstellt er das Werkzeug), **oder nur anhalten** und der Bediener trägt ein? Mein
   Vorschlag: erst nur anhalten (wie jetzt), Selbst-Eintragen später als Haken, aus vorbelegt.
   (Manuel, 2026-10-31, zur ersten Fassung: „ich hab keine ahnung was du damit überhaupt meinst“ –
   neu gefasst.) – *Warum nur Manuel:* Werkstattpraxis. – *Was die Antwort ändert:* ob der Zyklus
   nach dem Messen korrigiert. – 2026-10-31.

Manuel, 2026-10-31 abends: Stufe 2 „1.b“ (Konturprogrammierung);
Bohrfräsen – „man muss klären wie die bohrfräsen definieren“ (Recherche läuft, siehe
konzept_schritt_assistent.md, Teil C).
