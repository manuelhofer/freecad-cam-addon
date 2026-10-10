# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

4. **Geht in deinem FreeCAD 26.3.0RC1 unter Windows die zweite Installationszeile aus dem
   README, die über Python (urllib)?** – *Warum nur Manuel:* Nur dieses FreeCAD zeigt es; hier
   gibt es weder Windows noch diesen Build, und dort scheitert die erste Zeile über Qt (B-017). –
   *Was die Antwort ändert:* Kommt „CAM-Addon … ist installiert“, ist B-017 mit dem README
   erledigt. Sonst sagt die Meldung, warum: `unknown url type: https` – dieser Build kann gar kein
   HTTPS, weder Python noch Qt; `getaddrinfo failed` oder ein Timeout – das Netz sperrt GitHub. In
   beiden Fällen braucht es einen dritten Weg ohne FreeCADs Netz (ZIP von GitHub von Hand nach
   `Mod/freecad-cam-addon`) als Anleitung im README. – seit 2026-10-10 (P-2026-10-10-35).

(Die Fragen 1–3 hat Manuel beantwortet, P-2026-10-10-08 – siehe Verlauf.)
