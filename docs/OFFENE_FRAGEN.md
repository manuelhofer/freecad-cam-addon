# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

**1. Eine eigene Länge je Platz im Magazin?** Seit 0.273.0 steht in den Fräserlisten jeder Platz
des Magazins für sich (Manuel, 2026-10-18: „ich kann ja den fräser auch … mal kaufen und an …
verschiedenen plätzen einsetzen“). Jeder Platz hat seine Nummer und seinen Halter, die Länge kommt
aber noch aus der Werkzeugverwaltung: Länge ab Spindelnase des Werkzeugs, oder Halter des Platzes
plus „Schaut aus dem Halter“ des Werkzeugs. Zwei Exemplare desselben Fräsers schauen an der
Maschine meist verschieden weit heraus. Vorschlag: im Fenster „Magazine“ eine Spalte „Schaut
heraus“ je Platz (leer: wie in der Werkzeugverwaltung); Reichweite, Kollision, Ausspann-Hinweis und
Einrichtblatt rechnen dann mit ihr. – *Warum nur Manuel:* Ob er die Länge je Platz pflegen will
oder sie lieber an der Steuerung misst und das Addon mit einer Länge je Werkzeug rechnet, ist
seine Arbeitsweise. – *Was die Antwort ändert:* eine Spalte mehr im Magazin, und überall, wo das
Addon die Länge eines Werkzeugs braucht, die des Platzes. – seit 2026-10-18.
