# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

(Die Fragen 1–3 hat Manuel in P-2026-10-10-08 beantwortet, Frage 4 in P-2026-10-10-36, 5 und 7–9
in P-2026-10-11-30, 6 in P-2026-10-11-40, 10 und 11 in P-2026-10-11-46, 12 in P-2026-10-11-86, 14 in P-2026-10-11-93 – siehe Verlauf.)

## 13. Bahnvarianten nach der gewählten Maschine wählen? (seit 2026-10-11 abends)

**Sollen Räumen und Planfräsen ihre Varianten mit Eilgang und Beschleunigung der im Job gewählten
Maschine vergleichen statt mit den festen Vorgaben (10 m/min, 1 m/s²)?** Manuel fragte (Forum
t=107911, Herbert): „beschleunigungswerte und speeds sollte das addon kennen, um zeiten richtig
berechnen zu können und vll werkzeugwege so zu gestalten, dass sie schön knapp fahren können … auf
der speziellen maschine dann??“ Heute rechnet „Auf der Maschine prüfen“ die Zeit mit den Werten
der Maschine (`abfahren.py`), die Wahl zwischen Bahnvarianten aber mit den Vorgaben
(`bahn.zeit`, aufgerufen in `raeumen_bahn`, `planfraesen_bahn`) – damit sich alle Strategien
gleich vergleichen.

*Warum nur Manuel:* Es ändert, was das Addon ohne Vorgabe wählt (Arbeitsregel „Strategiewahl erst
besprechen“): Auf einer schnellen Maschine gewännen Varianten mit mehr Eilgängen, auf einer
langsamen Portalfräse die mit weniger Richtungswechseln – dieselbe Datei gäbe je Maschine andere
Bahnen.

*Was die Antwort ändert:* Ja – `bahn.zeit` bekommt Eilgang und Beschleunigung der gewählten
Maschine (langsamste Achse), ohne Maschine bleiben die Vorgaben; vorher an seinem Testteil die
Zahlen beider Wege zeigen. Nein – bleibt, wie es ist.
