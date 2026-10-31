# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

Die Antworten vom 2026-10-31 auf die Fragen 1–8 (Beta-Assistent, Spannmittel, Kataloge) und was
daraus folgt, stehen in [konzept_schritt_assistent.md](konzept_schritt_assistent.md), Teil C.

1. **Messtaster: Welche hast du, an welcher Maschine?** (z. B. Renishaw OMP40 an der 840D, Blum TC50
   an der CLX 550; T-Nummer des Tasters; ob die Messzyklen der Steuerung freigeschaltet sind –
   Siemens CYCLE977/978, Heidenhain 420 ff., Renishaw-Makros G65 P9810/P9811). – *Warum nur
   Manuel:* Das steht nur in seiner Werkstatt. – *Was die Antwort ändert:* Plan C3b – statt Halt
   zum Messen von Hand misst die Maschine nach jedem Schlichtgang (Taschenbreite, Wandlage) und
   korrigiert den nächsten Gang; ohne Taster bleibt es beim Messstopp. – 2026-10-31.
2. **Tauchfräsen so – darf es als Weg ins Schruppen?** ([Bild](bilder/tauchfraesen_entwurf.png))
   Tasche 150 × 100, 40 tief, Tauchfräser Ø 32, Aufmaß 0,5: 28 Tauchstellen (Abstand höchstens
   0,7 × D), je **senkrecht** mit Eintauchvorschub auf den Boden, Eilgang hoch, über dem Material
   zur nächsten – kein Zickzack, kein Rampen. Reihenfolge: Stelle 1 in der Mitte (dort vorgebohrt),
   dann nach außen, jede neue Stelle neben schon Offenem (nach Manuels „wieso zickzack bahn ?“ zum
   ersten Bild, das Zeile für Zeile aus der Ecke begann). Bei 400 mm/min 3,2 min, 186 cm³/min. An den Rändern bleiben Zwickel, die das
   Schlichten (oder Restschruppen) nimmt. Gebaut als Entwurf (`camaddon/tauchfraesen.py`), noch nicht
   im Assistenten. – *Warum nur Manuel:* eine neue Strategie (abgemacht: erst Bild, dann sein Ja) –
   und ob Lage und Reihenfolge der Stellen so passen. –
   *Was die Antwort ändert:* Mit Ja kommt „Tauchfräsen“ als Weg in den Schritt „Schruppen“ der Beta
   (mit Zeit und Vorschau), angeboten, wenn ein Tauchfräser da ist oder im Katalog. – 2026-10-31.
3. **Hoffmann sperrt zu viele Abrufe – wie sollen die restlichen Hoffmann-Werkzeuge kommen?**
   hoffmann-group.com hat das Sammeln zweimal gesperrt (429, „aus sicherheitstechnischen Gründen
   nicht verfügbar“ – für deine IP, eine Weile auch im Browser). Drin sind 9 Fräserreihen (191
   Größen) und 225 Bohrerreihen; es fehlen rund 505 Fräser-Artikelgruppen (Kugel, Konik, Fasen,
   Gewinde, Hochvorschub, Wendeplatten, Messerköpfe). Wege: (a) sehr langsam, eine Seite alle 10 s,
   über eine Nacht (~20 h) – aber nur, wenn Hoffmann das nicht sperrt; geht es trotzdem zu, höre ich
   auf und umgehe nichts; (b) Hoffmann um eine Datenlieferung bitten (BMEcat/Excel – Händler geben
   das oft für Kunden heraus); (c) Hoffmann lassen, die Hersteller selbst nehmen (Fraisa, Gühring,
   Sandvik … sind drin bzw. unterwegs). – *Warum nur Manuel:* ob du Hoffmann anschreibst und ob dir
   der langsame Abruf recht ist. – *Was die Antwort ändert:* woher die übrigen Hoffmann-Daten kommen.
   – 2026-10-31.
