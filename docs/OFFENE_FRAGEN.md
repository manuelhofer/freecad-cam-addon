# Offene Fragen an Manuel

Hier steht jede Frage, die **nur Manuel** beantworten kann – mit dem Grund, warum Claude sie
nicht selbst beantwortet, und dem, was die Antwort ändert. Beantwortet: Eintrag raus, die Antwort
kommt in den Verlauf (`archiv/DEV_PROMPT_HISTORY.md`) oder in die Spezifikation. Nichts davon wird
durch Prüfläufe ersetzt: Was Manuel entscheiden muss, wird hier gefragt, nicht nachgemessen
(Arbeitsregeln, Abschnitt 0; Manuel, 2026-10-10).

Je Frage: **die Frage** – *Warum nur Manuel* – *Was die Antwort ändert* – seit wann.

**Frage 1 – Fräsen an der CLX550 mit der Transformation der Steuerung?** Heute schreibt der
Postprozessor an der Drehmaschine jede Bahn Punkt für Punkt mit X, Z und C (geht an jeder
Maschine). Die Siemens kann es kürzer: an der Stirnseite `TRANSMIT` (das Programm bleibt in X und
Y), am Mantel `TRACYL(d)` (abgewickelt, Y = Bogenlänge). Hat deine CLX550 TRANSMIT und TRACYL
(steht in der Optionsliste / im Maschinenhandbuch; an der Steuerung im MDA einmal `TRANSMIT` und
`TRAFOOF` eingeben – kommt kein Alarm, ist es da)? Und schreibst du unter TRANSMIT X im Durchmesser
(DIAMON) oder im Radius?
*Warum nur Manuel:* Ob die Option an seiner Maschine freigeschaltet ist und wie sie eingerichtet
ist, steht nirgends sonst; ohne Maschine lässt es sich nicht prüfen.
*Was die Antwort ändert:* Mit ja baut der Postprozessor einen Haken „TRANSMIT/TRACYL“ an der
Maschine (Spezifikation Steuerung 6, S6) – kürzere Programme, die Steuerung führt den Vorschub.
Seit 2026-10-25.

**Frage 2 – Ein Programmierhandbuch für Okuma oder Brother?** Manuel wollte Postprozessoren für
„alle“ Steuerungen (W-041). Gebaut sind LinuxCNC, Siemens, Fanuc, Haas, Mach, Mazak, GRBL,
Heidenhain und woodWOP. Für Okuma (OSP) und Brother (CNC-B00/C00) waren die Handbücher im Netz
nicht erreichbar (Seiten mit Bot-Prüfung, abgelaufenes Zertifikat) – ohne Handbuch rate ich die
Befehle nicht (Gewindebohren, Werkzeuglänge G56 bei Okuma, Rückzugsebene G71 …).
*Warum nur Manuel:* Ein Handbuch hat nur, wer die Maschine hat – vielleicht er, vielleicht
jemand im Forum.
*Was die Antwort ändert:* Mit einem Handbuch (PDF in `~/freecad_cam`) baue ich die Steuerung
danach, wie Mazak heute Nacht.
Seit 2026-10-25.


**Frage 3 – Soll das Programm den Nullpunkt (G54) selbst anwählen?** Neu gibt es den Haken
„Nullpunkt aus dem Job (G54 …)“: Dann steht am Anfang und hinter jeder Sprungmarke der Nullpunkt
des Jobs (Siemens G54–G57, ab dem fünften G505; Heidenhain Zyklus 247). Vorbelegt ist er **aus**
– wie bisher fährt das Programm im Nullpunkt, der an der Maschine aktiv ist. Fusion, Mastercam und
FreeCADs eigene Postprozessoren schreiben G54 von sich aus.
*Warum nur Manuel:* Ob man in seiner Werkstatt den Nullpunkt an der Maschine anwählt oder das
Programm ihn setzen soll, ist Gewohnheit der Bediener – falsch vorbelegt fährt das Programm im
falschen Nullpunkt.
*Was die Antwort ändert:* Mit ja ist der Haken vorbelegt an (je Steuerung oder für alle).
Seit 2026-10-25.

**Frage 4 – Gewindebohren an der CLX550: wie machst du das heute?** An der Drehmaschine schreibt
das Programm seit 0.306.1 jedes Bohren ausgeschrieben (G0/G1 längs Z) – nur Gewindebohren nicht,
dort steht ein Hinweis. Die Siemens kann es auf zwei Arten: in der Mitte mit stehendem
Gewindebohrer und der Hauptspindel in Lageregelung (`SPOS`, dann `G331 Z… K…` / `G332`), oder an
der Stirn mit angetriebenem Werkzeug (`CYCLE84`, die Masterspindel ist dann der Antrieb). Welche
Art nutzt du, und schreibst du sie in ShopTurn oder im G-Code?
*Warum nur Manuel:* Welche Spindel an seiner Maschine Masterspindel ist und wie er Gewinde dort
bohrt, steht nur an der Maschine – falsch geraten bricht der Gewindebohrer.
*Was die Antwort ändert:* Danach schreibt der Postprozessor das Gewinde an der Drehmaschine als
Satz statt als Hinweis.
Seit 2026-10-26.

**Frage 5 – Große Programme an der alten 840D: aus dem NC-Speicher oder „von extern“?** Ein
5-Achs-Simultanprogramm hat schnell Millionen Sätze (du schriebst von „14834834 Zeilen“). Im
NC-Speicher einer älteren 840D ist dafür kein Platz; dort läuft so etwas von der Festplatte oder
vom Netz („Abarbeiten von Extern“ bzw. `EXTCALL`). Wie fährst du große Programme heute? Soll
„Programm schreiben“ auf Wunsch ein Hauptprogramm schreiben, das je Bearbeitung ein Unterprogramm
mit `EXTCALL "…"` aufruft (Werkzeugwechsel im Hauptprogramm, die Bahn in den Unterprogrammen)?
*Warum nur Manuel:* Wie seine Maschine eingerichtet ist (Speicher, PCU mit Festplatte, Pfad für
EXTCALL in den Maschinendaten), sieht man nur an ihr.
*Was die Antwort ändert:* Mit ja ein Haken „Je Bearbeitung ein Unterprogramm (EXTCALL)“ für
Siemens; sonst bleibt es ein Programm.
Seit 2026-10-26.
