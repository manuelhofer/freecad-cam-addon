# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

(Die Fragen 1–3 hat Manuel in P-2026-10-10-08 beantwortet, Frage 4 in P-2026-10-10-36, 5 und 7–9
in P-2026-10-11-30 – siehe Verlauf.)

### 6. Die Schrittweite der Kugel aus der Kammhöhe – welche Kammhöhe ohne Vorgabe?

Manuel (11.10.): Die Stange Ø 90 bleibt; die Schrittweite soll von der Kammhöhe abhängen (0,035 mm
ist für ihn beim Kugelschlichten in Ordnung); dazu eine eigene Spalte „ae höchstens“ in der
Werkzeugtabelle (Wahl c) – „wenn wir mit dem kugelfäser angestellt fahren .. sind die 0,4
hinfällig .. ich denke die 0.4 beziehen sich nur wenn du mit der spitze fährst“.

Nachgesehen (11.10., Herstellerseiten): T2 ist der HOLEX-Vollradiusfräser 207125-8 (Ø 8, Z2);
Hoffmann nennt „Eingriffsbreite max. ae = 0,05 × D“ und „Schnitttiefe max. 0,4“ zu seiner
vc-Tabelle – zur Rautiefe und zum Anstellen sagt die Seite nichts. Andere: Gühring GF 500 B
(gleiche Art) 0,1 × D in Stahl und Alu (0,8 mm, Kammhöhe ≈ 0,02), 0,05 × D erst ab 54 HRC;
GARANT 207028 für Alu 0,03 × D; Sandvik zum Feinstschlichten 10–15° anstellen (wegen vc = 0 in der
Mitte), Mitsubishi iMX 0,25 × D. Kein Hersteller sagt, dass Anstellen ein größeres ae erlaubt –
es verbessert Schnitt und Standzeit; die Kammhöhe auf einer Ebene hängt nur von R und ae ab. Das
Katalog-ae ist der Eingriff, für den vc und fz gelten (Gühring: weniger ae, mehr vc), keine
Grenze der Oberfläche. Üblich sind 0,01–0,02 mm Kammhöhe (Gühring ≈ 0,02 bei Ø 8), 0,005 mm nur
vor dem Polieren.

| Kammhöhe | Schrittweite (R 4) | Zeit am Nasen-Testteil (vor P-2026-10-11-37) |
| --- | --- | --- |
| 0,005 mm (heute, ae 0,4) | 0,40 mm | 187,5 min |
| 0,010 mm | 0,57 mm | 132,5 min |
| 0,020 mm | 0,80 mm | 94,4 min |
| 0,035 mm | 1,06 mm | 71,7 min |

**Die Frage:** Welche Kammhöhe soll der Assistent ohne Vorgabe nehmen – deine 0,035 mm oder 0,02
mm wie bei Gühring? (Gebaut wird: Feld „Kammhöhe“ im Schritt 2, die Schrittweite daraus, höchstens
„ae höchstens“ aus der neuen Spalte der Werkzeugtabelle, wenn dort etwas steht.)
*Warum nur Manuel:* der Vorschlag ohne Vorgabe (Strategiewahl).
*Was die Antwort ändert:* die Vorgabe des neuen Felds.
Seit 2026-10-10, neu gefasst 2026-10-11.

### 10. Die Nase mit dem Schaftfräser fertig – so, wie im Bild?

![Nase mit dem Schaftfräser](bilder/vorschlaege/testteil_4achs_nase_schaftfraeser.png)

Manuels Antwort auf Frage 5 (11.10.): C so, dass die flache Seite der Nase zur Mitte (Face8) quer
zum Schaftfräser steht, mit Y abzeilen – „auch wenn das unter 0 ist“ –, die Seiten Face4/Face6
ebenso mit dem Schaftfräser, die Kugel dann nur noch Face9 (und Face5). Durchgerechnet am
Nasen-Testteil (Prototyp, 11.10. morgens): „Plan indexiert“ mit T1 Ø 12 (Stirn), C fest, Zeilen
längs mit Y –
- Face8: X bis −5,5 (5,5 mm unter der Mitte), zwei Zeilen bei Y ±4, die Mitte des Fräsers längs
  ab 6,2 mm vor der Stirn des Schafts (sonst stieße er in den Schaft) – 0,55 min; die roten
  Linien nach außen sind das Planaufmaß vorne an der Stange (1 mm), das dort mitfällt;
- Face4/Face6: X 10, Y bis ±36,7 – 0,94 min;
- die Kugel T2 ohne diese drei Flächen: 157,8 statt 187,5 min (sie lässt dort auch die Luft aus).
Zusammen **159,3 statt 187,5 min** (gerechnet vor „C dreht nicht zurück“, P-2026-10-11-37 – damit
sind beide Zeiten kürzer, heute 177,8 min). Die Seiten mit der Stirn (Fräserachse quer zur Fläche) gibt es
schon („Plan indexiert“); neu ist nur, dass eine Fläche, die zur Achse schaut, auch geht, wenn der
Weg von außen frei ist – bis zur Grenze von X der Maschine (das prüft „Auf der Maschine prüfen“).
**Die Frage:** So bauen – im 4-Achs-Assistenten ein Haken „Ebene Flächen mit dem Schaftfräser
fertig“, vorbelegt an, der „Plan indexiert“ mit dem Schruppfräser für die ebenen Flächen anlegt
(auch die zur Mitte) und die Kugel diese Flächen auslassen lässt? Und die Seiten mit der Stirn
(wie im Bild) – oder angestellt mit dem Schaft, wie du es auch beschrieben hast?
*Warum nur Manuel:* eine neue Wahl ohne Vorgabe (Strategiewahl), und wie weit X unter 0 an seiner
CLX550 darf, weiß er.
*Was die Antwort ändert:* der Haken im Schritt 2, `vierachs_planbahn.ebenen` mit Flächen zur
Achse, die Flächen der Kugel ohne die fertigen.
Seit 2026-10-11.
