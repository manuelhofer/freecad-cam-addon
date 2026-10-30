# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

Zu „Bearbeitung in Schritten“ (Beta, 0.315.0) – ausprobieren: Einstellungen → CAM-Addon → „Beta-Funktionen
zeigen“; die Bilder und alle Vorschläge in [konzept_schritt_assistent.md](konzept_schritt_assistent.md).

1. **Zwei Wände einer Tasche angeklickt: ein dritter Knopf „Ganze Tasche schruppen, nur diese Wände
   schlichten“?** Bisher: „Ganze Tasche nehmen“ oder „Nur diese Flächen – der Rest ist schon frei“
   ([Bild](bilder/beta/2_flaechen_tasche.png)). – *Warum nur Manuel:* wie man so eine Tasche in der
   Werkstatt angeht. – *Was die Antwort ändert:* das Schruppen bekäme die ganze Tasche, das Schlichten
   nur die gewählten Wände. – 2026-10-30.
2. **Schruppen als Frage „Wie soll das Material raus?“ (eine Zeile je Weg mit Zeit und Vorschau,
   vorbelegt der schnellste) statt der Haken?** Wege: Räumen schraubend, vorbohren + räumen, Bohrfräsen,
   3D-Schruppen in Lagen, „Flanke grob“ – und neu **Tauchfräsen** (senkrecht, Stoß an Stoß) für tiefe
   Taschen? – *Warum nur Manuel:* ändert, wie das Addon die Strategie wählt. – *Was die Antwort ändert:*
   den Schritt „Schruppen“ der Beta; Tauchfräsen wäre neu zu bauen. – 2026-10-30.
3. **Nach „Anlegen“ im Schruppen: (a) ein kleines Fenster „Weiter mit Schlichten?“ oder (b) das Fenster
   bleibt offen, „Schruppen anlegen“, dann „Weiter“ zum Schlichten?** Heute: Fenster zu, dann Job
   anklicken → „Weiter bearbeiten (Beta)“. – *Warum nur Manuel:* der Arbeitsablauf. – *Was die Antwort
   ändert:* (b) braucht einen Umbau beim Anlegen (Operationen schrittweise in den Job). – 2026-10-30.
4. **Umspannen: ein Knopf „Teil umspannen …“ im letzten Schritt**, der einen neuen Job für dasselbe Teil
   anlegt und bei der Aufspannung beginnt – vorgewählt die Flächen, die in der ersten Aufspannung nicht
   gingen? – *Warum nur Manuel:* wie er umspannt. – *Was die Antwort ändert:* ein neuer Knopf und der
   Weg dorthin. – 2026-10-30.
