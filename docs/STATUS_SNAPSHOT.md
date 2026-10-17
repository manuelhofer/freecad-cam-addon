# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks. Was fertig ist, steht nicht mehr hier, sondern im
Verlauf ([archiv/DEV_PROMPT_HISTORY.md](archiv/DEV_PROMPT_HISTORY.md), ein Eintrag je
Patch mit dem, was man sehen muss) und je Thema in seiner Spezifikation (Lesekarte in
`CHATSTART.md`). Fragen, die nur Manuel beantworten kann, stehen mit Grund in
[OFFENE_FRAGEN.md](OFFENE_FRAGEN.md).

## Projektstatus

**Im FreeCAD-Forum vorgestellt (2026-10-10):** Unterforum „CAM“,
https://forum.freecad.org/viewtopic.php?t=107889. Antworten dort sind Eingang für Wünsche und
Fehler – sie kommen hierher; die Beiträge selbst liegen nur bei Manuel (Manuel, 2026-10-11: „alles
was mit posts zutun hat … einfach nicht auf github … auser es werden bilder benötigt“; die Bilder
im Zweig „forum“ des Repos, je Beitrag ein Ordner – nicht in `main`; ältere in `docs/bilder/forum/`).
Dieselbe Vorstellung auf Deutsch im „Forum in Deutsch“: https://forum.freecad.org/viewtopic.php?t=107911.

**Manuels Antworten am 17.10. früh (auf die Fragen 1–9) – Aufträge:**
- Frage 1 (kleinerer Fräser, wenn der gewählte nicht hineinpasst): „ein hinweis an den anwender
  .. und dann mit einem klick kleinen fräser übernehmen klar !!“ – nicht mehr selbst tauschen,
  sondern rot melden, welcher passt, mit Knopf „übernehmen“.
- Frage 2 (privates Repository): „kann alles in der repo bleiben .. nur eben nicht verbreiten auf
  die pcs“ – so ist es seit P-2026-10-16-08 (das Update lädt `docs/`, `tests/`, `scripts/` nicht);
  erledigt.
- Frage 4 (C-Ring, Bohrung und Schlitz): „Ja, Räumen tritt an“ – an durchgehenden Wänden tritt
  Räumen bis durch gegen die Kontur an, die Zeit entscheidet; „Schlichten danach“ macht die Wände.
- Frage 5 (Boden eines Lochs bis Ø 40 → Bohrung fräsen): ja, bleibt.
- Frage 6 (3D-Schruppen nur über der Auswahl): „ja als hacken ist gut, aber vll auch so als
  vorschlag .. "hey schau mal du das rohteil ist dort noch komplett voll mit material .. wir
  müssen erst die schräge fläche wegplanen und dann können wir die tasche fräsen oder ist rohteil
  schon fertig so das nurnoch die tasche zu fräsen ist" … versuch mal dir da was auszudenken“.
- Frage 7 (G550 von oben): „das A=0 bedeutet das der tisch so steht das man von oben aufs teil
  schaut ... also das der tisch … zur spindel schaut und man das teil wenns flach auf dem tisch
  montiert ist von oben bearbeiten kann .. du kannst veruchen herrauszufinden wie es wirklich ist
  aber nur so machts sinn !!“ – die Beispiel-G550 steht bei A = 0 anders (Tisch waagerecht).
- Frage 8 (Wandfahrt des Planfräsens): (b) ein Zug an der Wand am Ende der Lage.
- Frage 9 (Rundachsen im Namen der Ebene): „Ja, wie an der Maschine“ – Name, „Ebene schwenken“
  und „Alles aus dieser Aufspannung“ zeigen die Werte der Steuerung (A−60), gerechnet wird weiter
  mit dem Gelenk.
- Frage 3 (später beantwortet): Planfräsen nur für Flächen, deren Rand rundum offen ist; ein Absatz
  geht an Räumen und Kontur (P-2026-10-17-18).
- Dazu: „Beispiele laden“ bekam „Öffnen“ (P-2026-10-17-16).

**Umgesetzt am 17.10. (0.260.80 → 0.260.89):**
- P-17 Frage 9: Name der Ebene wie an der Steuerung („A−60 B0“).
- P-18 Frage 3: Planfräsen nur offen; der Absatz → Räumen/Kontur.
- P-19 Frage 1: roter Satz, welcher Fräser passt, mit Knopf „„T3 …“ übernehmen“.
- P-20 Frage 8: Planfräsen mit einem Zug an der Wand am Ende (Absatz 14 → 0 Wendepunkte).
- P-21 Frage 7: An einer Maschine mit waagerechter Spindel (G550, `Eintrag.spindel_quer`) kommt auch
  „von oben“ in eine Ebene („… Ebene von oben (A−90 B0)“); das Programm schwenkt davor und am Ende
  zurück. Szenario `szenario_g550_von_oben`.
- P-22 Frage 6: 3D-Schruppen-Haken „Nur über den gewählten Flächen – drumherum ist schon gefräst“
  (nicht angehakt – angehakt führe der Fräser bei vollem Rohteil drumherum ins Volle) und der
  Satz „Rings um die gewählten Flächen steht laut Rohteil noch … cm³ …“. Kuppel 6,1 → 3,9 min.
- P-23 Frage 4: Räumen bis durch an Wänden, die durch das Teil gehen (nur Wände gewählt, das
  Gebiet nur von gewählten Wänden begrenzt, nicht ein einzelnes rundes Loch) – gegen die Kontur,
  ein Schlichtzug zählt beim Räumen dazu; gewinnt es, ist „Schlichten danach“ angehakt. C-Ring
  Ø 12: 2,7 statt 5,3 min. Szenario `szenario_raeumen_durch`.
- Damit sind alle neun Fragen vom 16./17.10. umgesetzt.
- **Fable, 17.10. ab 7 Uhr (P-2026-10-17-26 bis -30, 0.260.90 → 0.260.94),** nach
  `docs/auftraege_fable.md`: Auftrag 1 ohne Querachse gebaut (Rundum schruppen: Zeilen in den
  Sektoren, Manuels Ring 100 → 11 km; mit Querachse Frage 1 in OFFENE_FRAGEN), Auftrag 3
  gemessen (Zwickel verstanden, Materialstand-Ringe bringen nichts), Auftrag 4 gebaut (gerechnete
  Schlichtzeit), Auftrag 5: Vollnut-Rampe einweg, Flanke war ein Zählfehler.
- **Fable, nachmittags (P-2026-10-17-31 bis -38, → 0.260.102):** Durchsicht P-26 (Zusatzzeilen nur
  in den Sektoren), Zeilen unter der Achse, Stirnseite → Verweis in „Bearbeitung“, am Ring die
  Luftzeile vor der Stange weg (12,4 → 11 km, 10 % Luft), Gegenleser-Funde (RichText-Fehlertexte,
  `;` in NC-Kommentaren), der Zwickel am 3D-Schruppen ist der Biss jedes Ringschritts (nur der
  Prüfstand sieht ihn an einer Stelle), die übrigen Kehren nachgemessen mit Bildern – die Kontur
  wendelt nicht mehr auf einer Schleife kleiner als ein Zehntel des Fräserdurchmessers.
  Dazu (P-36 bis -38, → 0.260.102): das Volumen eines STL-Körpers aus dem Netz (am Geist 0,8 s →
  2 ms je Vorschau), „Seiten mit dem Schaft“ rechnen mit Schneide + Hals (Auskragung N), und die
  Einfahrten der Zeilen gehen für Hundertstel senkrecht statt in die Rampe – der Helix-Kreis darf
  neben der Zeile das Spiel beim Schruppen höher sehen (Passfedernut: Helix statt Rampe).
- Voller Szenario-Lauf auf 0.260.87 (Worktree, Wochen-Build): 152 von 154 grün. Rot waren
  `szenario_entgraten3d` – ein echter Fehler aus P-21 (die Variable `quer` von der inneren Funktion
  verdeckt; P-24) – und `szenario_rundum_drehmaschine` (das Szenario prüfte „Anlegen“, bevor die
  Anzeige „rechnet …“ ihren nächsten Takt hatte; jetzt wartet es darauf). Die Durchsicht durch
  einen zweiten Agenten fand drei weitere Fehler (P-25). Alle betroffenen Szenarien wieder grün.

**Die Nacht 16./17.10. (P-2026-10-16-48 bis P-2026-10-17-16, 0.260.45 → 0.260.80):** (dazu T-015: G550 ohne Grundstellung)
- Zickzack-Durchsicht (Manuel: „das auch wirklich alle zickzack fahrten weg sind“):
  - Der Prüfstand zählt Kehren; alle 2,5D-Strategien dort 0.
  - Die Kontur fährt geschlossene Umläufe als Wendel hinab (P-51).
  - Jedes Szenario schreibt `kehren.txt` (P-52, mit Ort und Programm, wo eine Kehre ist).
  - 4-Achs „Plan indexiert“ fährt über eine Helix hinein, 30 → 9 Kehren (P-53), an der schrägen
    Fläche senkrecht, wo kaum etwas darüber steht (→ 7, P-68). Übrig sind Nuten, die so breit
    sind wie der Fräser (wie die Vollnut in 3 Achsen), und eine Ecke neben einem Stift.
  - 4-Achs-Schruppen mit gewählten Flächen: in die erste Zeile einer Lage über eine Helix statt
    über die Rampe hin und her (P-2026-10-17-04; mit „nur Gleichlauf“ 2 → 0 Kehren). Grün auch
    `szenario_vierachs_flaechen`, `_nocke`, `_schruppen`, `_nut`, `_mantelnut`.
  - Im vollen Szenario-Lauf übrig:
    - Testteil, Kontur T1: in der dreieckigen Tasche passt Ø 12 gerade so; die Mittelbahn ist ein
      Dreieck von 1 mm Umfang, dort wendelt er eng hinab – kein Hin und Her.
    - Geist (STL), 3D-Schlichten: Die „Kehren“ sind winzige Schleifen in engen Mulden, kein
      Hin und Her. Dabei gefunden: Zwischen nahen Stücken hob es 394-mal senkrecht im Vorschub an
      (2,8 m) – jetzt im Eilgang, etwa 62 → 55 min (P-58).
- Schräge Flächen ohne Umweg (P-54, Manuel am Schwenkteil auf der G550):
  - An der 5-Achs-Fräse legt „Anlegen“ die Ebene selbst an und macht dort weiter.
  - An der 3-Achs-Fräse gibt es den Haken „Bahnen dafür anlegen und im Einrichtblatt notieren“
    (bis P-2026-10-17-08 „Schräg gespannt fräsen“): eine Aufspannung, das Teil
    gekippt; das Einrichtblatt nennt Winkel und Achse.
  - Der Taschenboden heißt „Boden einer Tasche – Räumen“.
  - Der Boden eines Lochs bis Ø 40 meint das Loch (Frage 5).
- Weiter:
  - Werkzeugkiste mit Hoffmann-Daten (77 Reihen, P-48).
  - Gleiche Rundungen und Fasen auf einmal anwählen (P-49).
  - Die Vorschau-Schruppbahn wird wiederverwendet (P-50; Geist 702 → 571 s).
  - „Beispiele laden“ beginnt leer, mit „Alle anhaken/abhaken“ (P-55).
- Rote Szenarien aus dem vollen Lauf:
  - Behoben: `szenario_loch_schraeg`, `szenario_lagerbock`, `szenario_platte` (seit P-12/-13, in
    P-54); `szenario_schwenkteil` (Wechselpunkt Z 150 lag seit P-01 im Teil, P-56).
  - B-026 (`szenario_vierachs_drehteil`) behoben in P-57.
  - `szenario_mausrad` prüft „mit Fokus“ nur noch, wenn die Rasten ankommen (P-62); grün. Das
    Mausrad-Szenario
    scheint am Prüfaufbau zu liegen: Rasten über XTest kommen in gamescope nicht an, die Nummer
    mit Fokus rollt nicht.
- 3D-Schruppen nur über den gewählten Flächen: gebaut und zurückgenommen (Frage 6, mit Bild).
- Nachgezogen (P-59 … P-66):
  - „Anlegen“ an der G550 nachgespielt (Ebene A60, keine Berührung, ohne falschen Hinweis
    „Werkzeug quer“).
  - Beim Anstellen sagt der Tooltip, warum es nur mit dem Kugelfräser geht.
  - Die Zeilen von „Alles aus dieser Aufspannung“ haben keinen Knopf „Ebene schwenken“ mehr.
  - Wände und Ecken einer Tasche in der Schräge kommen mit ihrem Boden in dieselbe Ebene.
  - In der Ebene eines Lochs hakt sich das Räumen nicht mehr an (es räumte die ganze Schräge).
  - B-026 (Drehteil) samt Folgefehler im Modell der Stange (P-61).
  - Formularzeilen werden erst später gelöscht (der Absatz in „Maschine bearbeiten“).
  - Im Freivorschub kein Ausflug hin und zurück mehr (P-67).
  - In einer gekippten Aufspannung zeigt das Fenster das gekippte Teil (P-69). Das Einrichtblatt
    nennt Winkel, Achse und den Nullpunkt dieser Aufspannung (P-70).
  - Manuels Klotz mit 45°-Fase (`schrägemitklotz.FCStd`, Kopie): 5 Achsen → Ebene A−45 → Räumen;
    3 Achsen → gekippt 45° → Räumen.
- Der zweite volle Lauf (nach P-62): 149 von 151 grün. `szenario_maschine_bearbeiten` stürzte ab
  (behoben in P-63, danach zweimal grün); `szenario_rundum_drehmaschine` lief allein grün – im Lauf
  rechneten nebenher weitere Szenarien.
- Die Patches der Nacht noch einmal am Code durchgesehen (P-2026-10-17-01 bis -03):
  - Ein Eilgang hinab endet nie im Material vor der Operation (das 3D-Schlichten fuhr bis 2 mm
    über das fertige Teil hinab – über Treppen vom Schruppen hinweg).
  - Die Helix im Planfräsen 4 Achsen drehte im Gleichlauf falsch herum; an einer schrägen Fläche
    keine Helix mehr, wo die Fläche höher liegt.
  - Schräge Flächen je Lage gemerkt („unten“ geändert); neue Ebenen und gekippte Aufspannungen
    kommen vorn in eine laufende Kette (N-Eck), statt sie zu ersetzen; mit einer Kante dazu kein
    Planfräsen der ganzen Oberseite; ein Zapfen im Lochboden macht eine Tasche; nur Wände über
    der Schräge gehen mit in ihre Ebene.
- Der dritte volle Lauf (Stand P-2026-10-17-03): 151 von 151 grün. In `kehren.txt` fiel das
  Planfräsen am Block auf (4 Kehren, seit P-67): Das Bügeln von Hin-und-zurück nahm Höhen bis
  0,05 mm als gleich und griff die flache Rampe an ihrer Wende an – behoben in P-2026-10-17-06,
  zusammen mit dem, was eine zweite Durchsicht fand (Eilgang-Schutz mit der Fräserform und am
  Rand, Helix im 4-Achs-Schruppen nur über Gefrästem, Taschenwände gegen jede angrenzende Fläche).
- Danach (Stand P-2026-10-17-07): alle 121 Prüfdateien im Wochen-Build grün; in der Release 1.1.4
  die Prüfdateien und Szenarien der Nacht (`test_freiwege`, `_vierachs_bahn`, `_vierachs_plan`,
  `_bohrung`, `_gleiche_flaechen`, `_schlichten3d`; `szenario_schraeg_anlegen`, `_schraeg_g550`,
  `_gleiche_flaechen`, `_beispiele`, `_loch_schraeg`, `_vierachs_plan`) grün. Geist, 3D-Schlichten:
  58,3 min (55,4 nach P-58) – der Eilgang-Schutz nimmt 42 Eilgänge hinab ins Treppen-Restmaterial
  am Rand des Rohteils (P-2026-10-17-07). Neu gefragt: Frage 8 (Wandfahrt des Planfräsens).
- Das Fenster steht nicht mehr (Pausen aus `pausen.txt` des vollen Laufs, P-2026-10-17-09/-10):
  Geist (STL) 21,9 → 1,0 s und N-Eck-Kette 15,4 → 1,2 s (die Lochboden-Erkennung von P-54 holte
  jedes Dreieck mit `getElement`; das STL-Modell wird beim Umschalten der Aufspannung als Netz
  gezeigt); Öffnen am Testteil 3,2 → 1,3 s, Zielzeit 3,0 → 0,5 s (Punkt-in-Fläche für alle Zellen
  auf einmal, dieselben Ergebnisse); „Anlegen“ mit Wegkippen 6,2 → 0,8 s (die Rechnung atmet,
  P-2026-10-17-11); Simultan-Planen je Schritt 1,7 → 0,9 s (P-2026-10-17-14). Übrig über 1,5 s:
  das Restbild im Prüffenster (5 Achsen simultan, ein Schritt 1,7 s), das Anlegen eines Jobs in
  FreeCAD (1,7 s).
- In der Flächenliste „(siehe unten)“ statt „(unten)“ (P-2026-10-17-13).
- Vierter voller Lauf (Stand P-2026-10-17-10): 150 von 151 grün; `szenario_vierachs_schruppen`
  fand „Anlegen“ unter Volllast noch gesperrt (die Vorschau rechnete) und lief allein grün. Kehren
  wie im Lauf davor, nur das Planfräsen am Block wieder 0.
- Dritte Durchsicht (P-2026-10-17-12): Eilgang-Schutz wieder mit der halben Zelle, ein leerer
  Schnitt und offene Drähte fallen in `eingeschlossen` auf die alte Rechnung zurück, die
  Netz-Eigenschaft der STL-Anzeige markiert nichts mehr als geändert. Alle 121 Prüfdateien auch
  in 1.1.4 grün.
- Der 3-Achs-Hinweis wie von Manuel vorgeschlagen (P-2026-10-17-08); neu gefragt: 8 (Wandfahrt),
  9 (Rundachsen im Namen der Ebene wie an der Steuerung?).
- Der Knopf „Ebene schwenken (3+2) …“ im Assistenten ist weg (war seit P-54 immer versteckt), die
  Hilfe beschreibt den neuen Weg (P-2026-10-17-05). Der Befehl in der Werkzeugleiste bleibt.

**Der 16.10. abends (P-2026-10-16-36 bis -47, 0.260.33 → 0.260.44):**
- Einrichtblatt: Das Fenster öffnet sofort, die Bilder kommen nach und nach; beim Halter ein Link
  „im Katalog“.
- B-025 (Querachse, Schaftgrenze auf dem falschen Strahl) behoben, danach beschleunigt.
- W-022 Punkt 3:
  - Die Halter sind nach den öffentlichen Katalogzeichnungen nachgebaut (SK40, BT40, HSK-A63,
    VDI30); gegen eine STEP-Datei geprüft: auf 0,1 mm gleich.
  - Jede Vorlage verlinkt ihr Vorbild; ohne Link sucht der Knopf im Katalog.
  - „Halter aus Datei (STEP, STL) …“ liest die Kontur des eigenen Halters.
- B-020: Ein Teil als Link in der Maschine landet jetzt im eigenen Dokument, in beiden Assistenten.
- Der volle Szenario-Lauf im Wochen-Build lief unterbrochen weiter. Rot waren nur
  `szenario_erster_start` (18 Menüeinträge, behoben) und `szenario_vierachs_stl` (702 s;
  `# ZEITLIMIT:` je Szenario).

**Der 11.10. ab Mittag (P-2026-10-11-42 bis -58, 0.213.48 → 0.213.64):** Manuels Antworten zu
Frage 10 und 11 gebaut („Plan indexiert“ rundum vorbelegt mit dem Schruppfräser, auch Face8 zur
Achse; Seiten mit dem Schaft als Haken; „C dreht nicht zurück“ beim Schruppen); der 4-Achs-
Assistent sagt vor dem Anlegen, mit wie viel ap × ae die Kugel nach dem Schruppen eingreift und ob
Halter oder Schaft anstoßen („bräuchte mindestens … mm“); „Folgelagen nur, wo nötig“ (Haken,
vorbelegt an): am Nasen-Testteil Schruppen 15,3 → 11,1 min, mit 5 mm Zustellung 64 → 37 min.
Kein Stehen: „Programm schreiben“ auf einem Nebenrechner (2,3 → 0,2 s), Flanke, Restschlichten und
3D-Schlichten mit Wegkippen im Hintergrund, Materialstand im Takt, die Kopie für die Arbeiter ohne
Vorschaubild (0,58 → 0,16 s). Das Voxelmodell (`camaddon/voxelstange.py`) rechnet auf allen Kernen
und füllt das Teil übers Netz in 0,1 s. Berichtigt: die „408 mm³ je mm“ vom Morgen (Messfehler).

**Der 11.10. nachmittags (P-2026-10-11-59 bis -72, 0.213.65 → 0.213.77):** Mit Flächen ist der
Haken „Querachse“ beim Schlichten grau und sagt warum (Frage 12 an Manuel). Der Abspieler im
Prüffenster rechnet weite Sprünge im Takt (ans Ende: 3 s → höchstens 0,19 s am Stück). **Die
Schlichtbahn mit der Querachse schnitt an der Nase bis 0,1 mm ins Teil** (nachgemessen: Kugelmitte
gegen ein feines Netz, die schlimmsten mit OpenCascade) – das Zusammenfassen maß seit „C dreht
nicht zurück“ gegen die falsche Normale, weite Sprünge fuhren schräg an Seitenflächen entlang.
Behoben (-61): höchstens 0,004 mm (die Vernetzung). Rundum ohne Querachse, mit Flächen und „Plan
indexiert“ nachgemessen: sauber. „Kollision prüfen“ mit der CLX550 156 s – der größere Teil ist
Python je Station, nicht OpenCascade; nicht weiter verfolgt. 3-Achs-Schlichten und Restmaterial am
3-Achs-Testteil nachgemessen: höchstens 0,003 mm ins Teil; die 5-Achs-Flanke an zwei Kegeln (auch
zwischen den Stellen): höchstens 0,007 mm. **Stößt ein Halter an, bieten die Assistenten
und das Prüffenster „T1 auf … mm ausspannen“ an** (-63 bis -65): ein Klick setzt die Länge ab Spindelnase in
der Werkzeugverwaltung; „bräuchte mindestens“ gilt im Prüffenster jetzt für die ganze Operation
(Nase: T1 49, T2 53 mm mit dem Kopf des gewinkelten Halters). **Lag-Sonde im Szenario-Lauf**
(-66): jedes Szenario schreibt `pausen.txt` – wo das Fenster wie lange stand und was dabei rechnete.
Damit gefunden und behoben (-66 bis -69): Fläche anklicken im Assistenten 7,3 → 2,0 s (passt je
Fläche gemerkt), „Anlegen“ bis 26 → 1,7–3,9 s (Abstandsfeld des Räumens bitgleich ~200× schneller,
das Fenster zeichnet beim Rechnen neu), der Materialstand-Beobachter am 5-Achs-Job 18 s → nichts
(5-Achs-Programm je Inhalt gemerkt), „Kollision prüfen“ an der Nocke 5,9 → 0,9 s (gemeinsame Daten
einmal gepickelt), Neu berechnen am Schwenkteil 84 → 44,5 s (Strahlenschnitt auf den Nebenrechnern).
Das erste 5-Achs-Programm rechnen beim Öffnen des Prüffensters jetzt die Nebenrechner (-70: 12 →
1,3 s am Stück; dabei zwei Fehler aus -60 im Abspieler behoben); beim Anlegen atmet die Oberfläche
auch im Materialstand und in den Hüllflächen, die Bleistift-Vorschau rechnet auf einem Nebenrechner
(-71: Platte 5,3 → 0,7 s, Bleistift 4,3 → 1,3 s), auch beim Ändern im Assistenten (-72: Entgraten 3D
3,5 → 0,7 s). Alle 131 Szenarien liefen mit der Sonde; fast alles bleibt unter 1 s.
3-Achs-Testteil nachgemessen (Luft im Vorschub je Satz im Materialstand, Zappler): keine Zappler;
echte Luft nur Räumen T1 7 s (ein Ring 1 mm vor einer schon freien Wand) und 3D-Schruppen 6 s (die
letzten 2 mm des Eintauchens) – nicht der Rede wert; was das 0,5-mm-Raster sonst als Luft zeigt, ist
die 0,3-mm-Haut an den Wänden, die es nicht auflöst (genau nachgerechnet: die Kontur nimmt sie).

**Der 11.10. abends (P-2026-10-11-73 bis -84, 0.213.77 → 0.213.88):** Hilfe zu den Neuerungen
nachgezogen. Bohrungen beim Anklicken je Form und Fläche gemerkt (Deckel 1102 → 8 Fragen, 3,4 →
1,6 s). Der räumliche Rest vor einer 3+2-Ebene trägt gesammelt ab und fängt beim Stand der vorigen
Ebene an (Schwenkteil, beide Ebenen 18,6 → 3,7 s, derselbe Rest); FreeCADs Adaptiv-Kern rechnet
mit Oberfläche auf einem Nebenrechner – Schwenkteil längste Pause 14,8 → 1,05 s. **Gefunden:
FreeCADs Adaptiv-Kern (libarea) liefert bei gleicher Eingabe nicht dieselbe Bahn** (sechs Aufrufe,
sechs Bahnen) – „Räumen“ mit Adaptiv hat darum je Sitzung ein paar Sätze mehr oder weniger; das
liegt in FreeCAD. Das Räumen rechnet ohne Vorgabe die Ringvarianten gleichzeitig auf den
Nebenrechnern, „adaptiv“ derweil im Hauptprozess (-77: Testteil 6,0 → 4,1 s mit warmen
Arbeitern). Alle Operationen atmen bei jedem Neuberechnen, nicht nur beim Anlegen; die übrigen
Uhren und die Rückrufe angeklickter Flächen laufen dafür nie mitten in einer Rechnung (-78:
3D-Schlichten umstellen 2,25 → 0,62 s). **In RC1 (Manuels Version) nachgeprüft:** P-74 bis -78
grün; Flächen anklicken stand dort doppelt so lange wie in 1.1.4 – `form.Faces` ist in 26.3
viermal so teuer, die Analyse einer Fläche holt jetzt nur diese (-79, `formteile.py`: RC1,
18 Klicks am Testteil 3,8 → 1,4 s). 29 bedienintensive Szenarien in RC1: sonst nahe an 1.1.4;
ein Absturz unter Volllast im Neuberechnen gleich nach dem Schließen des 4-Achs-Assistenten –
dort wird jetzt ohne Ereignisse gerechnet (-80, `uhren.still`). Die Wandhöhe über der Unterkante
ohne einen Schnitt je Millimeter (-81: RC1, Deckel anklicken 2,8 → 0,6 s, Testteil 4,7 → 1,3 s),
„Auf der Maschine prüfen“ atmet beim Rechnen am Stück (-82: RC1, Nocke 2,7 → 0,8 s). Danach alle
113 Prüfdateien in 1.1.4 und RC1: grün (in RC1 bis auf `test_goldene_bahnen` – Umgebung, eine
Koordinate in der sechsten Stelle; in 1.1.4 überspringt sich `test_export`). Das Räumen rechnet die
Hüllflächen einmal vor dem Verteilen (-83: Testteil 9,7 → 6,8 s, Rechenzeit 81 → 28 s). **B-019
gefunden und behoben (-84):** Der Adaptiv-Kern lässt an der Platte des Prüfstands in jedem Lauf eine
Nadel stehen (bis 0,04 mm², 20 mm hoch), die das Raster nicht sah – jetzt gesucht, genau
nachgesehen und am Ende der Lage von der Seite nachgeholt (+0,03 min je Nadel).
`test_pruefstand` bleibt gelegentlich rot an „platte/raeumen oben+tasche“ (35,6 statt höchstens
35,27 min): die Streuung des Kerns selbst.

**WEITERARBEIT an der allgemeinen Gesamtplanung (Manuel, 2026-10-08).**
**Auf GitHub veröffentlicht:** Version 0.203.1 auf `main`, einschließlich aller
22 zuvor lokalen Addon-Patches; Veröffentlichung auf Manuels ausdrücklichen Wunsch
am 2026-10-08 direkt bei GitHub bestätigt (P-2026-10-08-14).
**Programmfenster (0.203.1):** Einstellungsbereich übernimmt den aktiven Dialoghintergrund
auch bei dunkler Systempalette; helles/dunkles FreeCAD-Theme und Steuerungswechsel
auf Bildschirm 2 geprüft (Steuerung 13).
**Verbindliche Maschinenwahl (0.200.1):** Schwenkdialog behält die Jobmaschine auch
mit 0/1 Rundachsen, zeigt reale Anschläge und liest sie vor OK erneut. Alle sechs
Beispielmaschinen, neuer/bisheriger Dialog auf DP-1 und NC ohne fiktive Achsen geprüft
(Strategien 16.13).
**Werkzeugzugang (0.201.0):** Schwenkdialog wählt das tatsächliche Jobwerkzeug;
T-Nummer, Länge und Halterachse gehen in die Kinematik ein, vor OK frisch gelesen
(Strategien 16.14). Simultanausgabe (0.201.1) nutzt auch feste/einzelne reale Achsen und lässt
unerreichbare Operationen ausdrücklich unbearbeitet aus; keine senkrechte Ersatzbahn
(Strategien 16.15). Ebenenbereiche (0.201.2) werden auch nach geänderten Anschlägen
im gemeinsamen Export ausgelassen und im räumlichen Rest erhalten (Strategien 16.16).
**Gemeinsamer Maschinenzugang (0.201.3):** Alle Bahnachsen aus der tatsächlichen
Maschine für Export, Abspieler und Materialstand; sechs Maschinen, Kreisextrema,
absolute/relative Rundbewegung, Materialnachrechnen und goldene Gesamtfolge samt
Zeit/Speicher geprüft (Strategien 16.17). **Simultanteilbereiche (0.202.0):**
erreichbare vollständige Schnittzüge zwischen vorhandenen Rückzügen bleiben erhalten;
neue Verbindungen gegen Rohteil/Werkzeug/Halter/Spannung/Maschinenmodell geprüft,
ausgelassene Züge mit Grund und unverändertem Materialrest (Strategien 16.18).
Sechs Maschinen und DP-1 geprüft; goldene Gesamtfolge unverändert.
**Bewegter räumlicher Rest (0.203.0):** Wirkliche NC-Achsbewegungen nach Simultan-
operationen werden in die nächste 3+2-Ebene übernommen, für Kugel und endliche
zylindrische Schneide mit konservativer Bewegungsschranke. Ausgelassene Züge bleiben
stehen; unbekannte/unsichere Bewegung fällt auf das ursprüngliche Rohteil zurück
(Strategien 16.19). Sechs gelesene Kinematiken und DP-1 geprüft.
Nächster Schritt: qualifizierte Ein-/Ausfahrten innerhalb eines zusammenhängenden
Schnittzugs, weitere Schneidenformen und automatische Aufspannungswahl.
Maschinenweite Vorgabe: Richtungen und Grenzen aus der tatsächlich gewählten
Maschine; unerreichbare Bereiche mit Grund auslassen und als unbearbeitet kennzeichnen.

**Räumlicher Rest zwischen 3+2-Ebenen (0.200.0):** Mehrere BRep-Abschnitte je Strahl
und endliche Fräser mit beliebiger fester Richtung; native Gegenprobe am Hohlraum,
Referenz-/Zeit-/Speicher- und vorhandene 3+2-Prüfungen bestanden. Sichtprüfung auf DP-1.
Für Kugel und endliche zylindrische Schneide ist kontinuierliches Umorientieren
über tatsächliche NC gebaut (16.19); seit P-2026-10-11-90 jede Schneide (Torus, Konik, Fase,
Radien) als Kugeln und Zylinder, innen eine Treppe in der Schneide, außen der volle Zylinder –
vorher gab es nach einem Torusfräser in einer Ebene davor keinen räumlichen Stand, die nächste
Ebene fing beim Rohteil an. Offen bleibt die automatische Zugänglichkeits-/Aufspannungswahl
(Strategien 16.12) – sie ändert, was das Addon wählt: erst als Bild mit Zahlen an Manuel.

Der gemeinsame Schrupp-/Schlichtvergleich ist gebaut und qualifiziert (P-2026-10-08-03, Strategien 16.10).
Er wählt innerhalb eines angegebenen Zwischenlagenbereichs und der eingerichteten
Schlichtwerkzeuge/-bahnen; tatsächlicher Export, gemeinsame Übernahme, Rücknahme und
Referenz-/Zeit-/Speicherprüfungen sowie Bildschirm 2 geprüft. Manuels Sichtprüfung steht aus.
Der räumliche Rest ist für 3+2-Übergänge und tatsächliche Simultanbewegungen mit
Kugel/endlichem Zylinder gebaut; weitere Schneidenformen und automatische
Aufspannungen fehlen weiterhin. Die G550 ist ausschließlich ein zusätzlicher
Beispiel- und Gegenprüffall; Strategien verwenden die tatsächlich gewählte Maschine.

**G550-Freiformbeispiel 0.199.1:** gemeinsame Folge mit
3,5-mm-Zwischenlagen, 316,63 statt 357,52 s; 60 Schlichtkombinationen, beide freien
Richtungsfolgen, feines Raster einschließlich Vorbearbeitung und geschriebene NC-Geometrie
geprüft. Beispiel und vier Referenzen aktualisiert; frischer Export ohne Schreibflag exakt,
1066,58 s instrumentierte Qualitätsprüfung und 401,22 MiB Python-Spitze. Einzelheiten in
Strategien 16.11 und Beispiel-README; vorherige Referenzen im lokalen Prüfarchiv.
Dauerhafte Prüfdaten: `../../ergebnisse/gesamtplanung-2026-10-08/`.

**5-Achs-Materialansicht:** Gleicher farbiger Rohteil-/Sollteil-Vergleich wie bei 4 Achsen;
Kugelmitte aus tatsächlicher Kinematik, senkrechte Vorbearbeitung, Teil/Bahn und Zurückspulen.
Vorschau mit 0,5-mm-Raster; genaue Qualitätszulassung im Simultanvergleich (P-2026-10-07-04).

**G550-Simultanbeispiel:** fertiger Flanken-Schlichtjob mit D12 auf Winkelaufnahme unter
`beispiele/grob_g550_simultan/`; 252 Vorschubbewegungen ändern X/Y/Z/A/B gemeinsam,
Modellprüfung ohne Kollisionen oder Grenzüberschreitungen, etwa 14 s gerechnet (auf der neu
gebauten Maschine nachgemessen, P-2026-10-10-20). Startskript öffnet Maschine, Job und
Prüffenster im eigenen Profil auf dem zweiten Bildschirm (P-2026-10-06-05).

**GROB G550 als Beispielmaschine:** am 2026-10-11 zum dritten Mal gebaut, jetzt nach der
Kinematik der GROB G-Serie (P-2026-10-11-91; Manuel: „da ist nur ein Ständer, an dem der Tisch
befestigt ist … der Tisch fährt hoch, runter und schwenken … mach das richtig“; GROB: „X- und
Z-Achse auf der Werkzeugseite, Y-Achse und A/B werkstückseitig, auskragend“): die waagerechte
Spindel fährt nur X und Z und zieht sich ganz in ihren Spindelschacht zurück, der Tisch hängt
an einer Säule – Y hebt und senkt ihn, A schwenkt (einseitig gelagert), B dreht. Der Bau vom
10.10. (alle drei Linearachsen an der Spindel, Tisch zwischen zwei Lagerböcken) war falsch.
„Neue Maschine …“ → GROB G550 oder `beispiele/grob_g550.FCStd` direkt öffnen; Achsbewegungen,
Grenzen, Freiräume in allen Endlagen und Oberfläche in 1.1.4 geprüft (`test_beispielmaschine`,
`szenario_grob_g550`). Die beiden Beispieljobs `grob_g550_simultan/` und `grob_g550_freiform/`
tragen seit P-2026-10-11-96 dieselbe Maschine (T-014 erledigt): auf ihr ohne Grenzüberschreitung
und Kollision, die NC-Referenzen der Simultanprüfungen neu.
(Quellen: [spezifikation_grob_g550.md](spezifikation_grob_g550.md)).

**Zusätzliche Räumwahl:** Schritt 3 → Räumen → Bahnerzeugung → „Adaptiv – schneller
Freivorschub“, mit einstellbarer Obergrenze und gespeicherter Auswahl; bisherige Bahnerzeugung
bleibt Standard, alte Jobs und andere Bearbeitungen rechnen wie zuvor (P-2026-10-04-26).
Am Testteil modelliert 9,59 statt 10,28 min; die 8 min Zielzeit sind noch nicht erreicht.
Manuels Klickprüfung steht aus.

Stand 0.203.5 (P-2026-10-09-06). Alles, was hier als gebaut steht,
ist automatisch geprüft und vom jeweiligen Assistenten als Screenshot gesehen. **Manuels Test steht
aus** für alles seit 0.100.0; zuletzt hat er am 2026-10-02 die Schritte des Assistenten
„Bearbeitung“ gesehen („die Menüführung ist gut“).

- **W-001 Maschine aus Baugruppe** – gebaut bis Stufe 4e: Maschine bearbeiten und verfahren,
  schräge Achse, „Neue Maschine …“, Auf der Maschine prüfen, Abfahren, Kollision, Zeit mit
  Beschleunigung (`fahrzeit.py`), Werkzeugspitze (`kinematik.py`). Offen: TCPM wählbar –
  Frage an Manuel, ob seine Steuerung TRAORI/RTCP nutzt.
- **W-002 Werkzeugverwaltung** – gebaut bis Stufe G: Werkzeuge mit Einsätzen je Werkstoff,
  Schruppwerte planen, 26 Werkzeugarten, Halter mit Richtung, Bestückung an der Maschine
  und je Job, Drehrichtung M3/M4, Richtwerte eintragen, eigene Werte je Werkstoff, die Nummer
  am Werkzeug freiwillig (F2, P-2026-10-04-35; geladen und entladen nur über die Magazine,
  P-2026-10-12-114), je Werkzeug „Schaut aus dem Halter“ (P-2026-10-12-113); Magazine je Maschine in der
  Werkzeugverwaltung (Stufe H1, P-2026-10-05-04), die Nummern im Job aus dem Magazin (H2,
  P-2026-10-05-05: Listen mit dem Magazin vorn, gelb „nicht im Magazin“ mit „Ins Magazin
  übernehmen“), Rüstliste im Fenster „Bestückung“ und im Programmkopf mit „Nummern aus dem
  Magazin“ (H3) und die Kollision mit allem, was im Revolver steckt (H4; beides
  P-2026-10-05-06) – Stufe H fertig.
- **W-003 4-Achs-Bearbeitung** – gebaut: V1 Teil in die Stange, V2a/V2c Achse von der
  Maschine, V3 Rundum schruppen, V4 Flächen wählen (Linien längs, Plan indexiert mit
  Passfedernut, Mantelnut, Querbohrungen und Radial bohren, Rundum entgraten), V5 Rundum
  schlichten, Gleichlauf über C; die Spitze fährt über die Drehmitte hinaus, Kugel und Torus
  rechnen mit ihrer Form (P-2026-10-03-07, Manuels Teil neben der Achse); V5e die Spirale
  mit der Querachse (P-2026-10-03-18, Manuels Y-Gedanke: auf ebenen Flächen hält C, Y fährt
  die Gerade – seit P-2026-10-03-22 mit jedem Fräser, seit -23 auch beim Schruppen); die Bahnen
  auch zwischen den Punkten nicht im Teil (Spirale -22, Zeilen -24); die Kugel mit der Querachse
  15° angestellt, nicht mit der Spitze (P-2026-10-04-50, Haken, angehakt). Offen:
  V6, V7 (V2b Drehteile gebaut: P-2026-10-04-01); das Prüffenster malt Fahrten über die Mitte noch nicht (mit dem Kugelfräser seit
  P-2026-10-04-49 schon) – an Manuels
  Teil ohne Folgen gemessen (P-2026-10-03-25: alles grün, nirgends blau), erst für Teile weit
  neben der Achse (Spezifikation Vierachs, V5b „Offen“).
- **W-004 Bedienung** – D-01 bis D-13, D-20, D-21, D-25, D-26, D-28 bis D-30, D-40 bis D-47
  und D-50 bis D-57 erledigt, D-24 mit „Richtwerte eintragen“ und den Werkstoffklassen.
  Entschieden ([Durchsicht](durchsicht_bedienbarkeit.md), Abschnitt 6; Manuel, 2026-10-03):
  D-22 bleibt auf Klick; D-23, D-27 (0.139.0) und D-14 (0.140.0) gebaut; D-20 fertig
  (P-2026-10-04-09: Spindelleistung, „Schruppwerte planen“ mit der gemerkten Maschine). Rest
  von D-26: Tischgröße (die 5-Achs-Fräsen mit Wegen und Schwenkbereichen: P-2026-10-04-08).
- **W-005 Programm für jede Steuerung** – E1–E7 entschieden (je Empfehlung, Manuel
  2026-10-03); gebaut: der eigene Postprozessor mit dem Fenster „Programm schreiben …“ (S1, S3,
  Teile von S2/S4; P-2026-10-03-10); der Wechselpunkt der Maschine in MKS oder WKS, vor jedem
  Werkzeugwechsel und am Ende angefahren (P-2026-10-03-19); Hauptspindel und angetriebene
  Werkzeuge je mit S und C, die Maschine im Fenster wählbar, auch ungespeichert
  (P-2026-10-03-25: Manuels S4/C4 und S1/C1 → `SPOS[4]=0`, `C4=…`, `M1=3 S1=…`); SUPA im
  Siemens-Handbuch nachgeprüft, F_HOME (ShopTurn) und G75 als eintragbarer Weg zum Wechselpunkt
  (-26); die Einstellungen als Haken mit Erklärung in Gruppen, Glätten je Steuerung (S4),
  Vorschub ohne G93 (S5), Satznummern (-27); die Werkzeuglänge `G43 H` nach dem Wechsel an
  LinuxCNC, Fanuc, Haas und Mach (P-2026-10-04-51 – fehlte bis dahin), an Siemens `D1` nach
  `SUPA D0`, wenn kein Wechsel folgt (-52); das Programm nach dem Speichern nachgelesen wie an
  der Steuerung (Länge, Spindel, F, Kreise – -53), an der Drehmaschine LinuxCNC mit G43 und
  Fanuc/Haas ohne G90/G49 im Kopf (-53); TCPM als Haken für 5 Achsen simultan (TRAORI,
  G43.4, G234 – aus; -55); über der Höchstdrehzahl der Maschine n und F im selben Maß
  kleiner – beim Setzen der Werte und im Programm (-56); an der Drehmaschine G7/G8 bzw.
  DIAMON/DIAMOF im Kopf passend zur Maschine (-57); Kommentare in ASCII außer an Siemens
  (-60); Heidenhain iTNC 530 und TNC 640/620/320 im Klartext mit eigenem Nachlesen (Manuel,
  2026-10-05: „Heidenhain muss mit rein“; P-2026-10-05-01), 3+2 dort mit PLANE SPATIAL
  (P-2026-10-05-24). Offen: Steuerung an der Maschine
  (S2), Transformationen (S6), Wochen-Build (S7); die Rundachse
  zwischen zwei Operationen nicht über viele Umdrehungen auf 0 zurückdrehen (Manuel probiert,
  was seine Maschine macht).
- **W-006 Frässtrategien** – 2,5D komplett (Planfräsen, Räumen mit Ringen, Morph, Inseln,
  adaptiv und – nur auf Wahl – Manuels Räumen „stiche“ (P-2026-10-03-31 bis -33: Stiche von
  außen nach innen und Ringe, an Insel wie Wand; Manuel: „wir lassen adaptiv“ – Spezifikation
  Strategien 14),
  Kontur, Nut offen und geschlossen, Bohrung fräsen, Bohren, Zentrieren, Senken,
  Reiben, Gewinde bohren und fräsen, Entgraten mit Fase und Rundung, Restmaterial), 3D
  komplett (Schruppen, Restschruppen, Schlichten in fünf Richtungen mit Steil/Flach,
  Bleistift, Restschlichten), Materialstand in jeder Schrupp-Operation, Prüfstand mit
  Bestmarken, Zielzeit und „× Ziel“, Wettbewerb der Strategien im Assistenten. Offen: siehe
  „Danach“ unten.
- **W-007 Werkzeugkiste** – gebaut (88 Werkzeuge); Jongen 494W und Garant 208165 nach
  Katalog und Datenblatt (P-2026-10-02-91), Gühring 5596 mit Shop-Link (-92), Ceratizit
  CoreLine WPC UNI nach Manuels Link mit Nummer und Maßen je Größe (P-2026-10-03-02). Gühring
  und Sandvik bleiben geschätzt. Werkstoffklassen in der Tabelle, die Liste und die Kiste als
  Baum je Werkzeugart, Mehrfachauswahl zum Löschen, einzelne Größen aus der Kiste (-02). Neun
  Arten (Kugel, Torus, Lollipop, Gewindefräser, Zentrier-, NC-Anbohrer, Gewindebohrer links,
  Kegelsenker, Reibahle) sind echte GARANT-Werkzeuge der Hoffmann Group mit Artikel und Link
  (-11).
- **W-008 bis W-012** – gebaut: Home- und Wechselpunkt; der Assistent in drei Schritten mit
  Aufspannung, Maschine zuerst, Rohteil aus dem Dokument, ein Teil – ein Job; Messstopp
  (jetzt im Block „Schlichten danach“); Maschinen-Speicher; Materialstand mit wählbarer
  Eintauchstelle.
- **W-014 5 Achsen** – begonnen in der Nacht zum 2026-10-04 (Spezifikation Strategien 15): 3+2
  als Job je geschwenkter Ebene. F1 Rechenkern, F2 Ebene als Job, F3 Programm (Siemens CYCLE800,
  sonst ohne Zyklus), F4 auf der Maschine prüfen, F5 Befehl „Ebene schwenken (3+2) …“, F6 Materialstand über Ebenen gebaut.
  Nachgezogen bis P-2026-10-03-46: Schwenkhöhe, schräge Bohrungen, Programm mit der Maschine,
  Bohren am Schwenkkopf, Knopf im Assistenten, Bestückung je Aufspannung.
  D-1 … D-5 entschieden (2026-10-04); gebaut D-1, D-2 (P-2026-10-04-37), D-5 (-36), D-4 (-38: Sprungmarken,
  vollständiger Einstieg, Kopf mit Werkzeugen und „knapp“).
- **W-015 5 Achsen simultan** – (Spezifikation Strategien 16) Kern S1 ohne TCPM (`simultan.py`,
  Verdichten auf 0,005 mm). **S2 Kugelfräser angestellt** (Manuel, 2026-10-04: „Ja, so bauen“ –
  E-2 und E-3 entschieden): P-2026-10-04-21 – „3D-Schlichten“ mit der Eigenschaft „Anstellen“
  (`angestellt.py`): nur so viel wie nötig, mindestens 15° zwischen Achse und Normale, eine
  Rundachse; Prüfen, Kollision und Programm mit den Rundachsen je Punkt (G93). An der Kuppel 6 %
  länger, nirgends mit der Spitze. Ohne den Haken bleibt alles wie bisher. Im Assistenten
  (P-2026-10-04-22): beim 3D-Schlichten der Haken „Anstellen (5 Achsen simultan)“, frei an einer
  5-Achs-Maschine mit Kugelfräser. Nachgerechnet auf allen drei 5-Achs-Beispielen (Tisch/Tisch
  um X, Kopf/Tisch um Y, Kopf/Kopf um X): eine Rundachse kippt bis 29,4°, die andere steht.
  **S3 Flanke** (Manuel, 2026-10-04: „Ja, so bauen“, „selbst anhaken, wenn schneller“):
  P-2026-10-04-24 – die Operation „Flanke“ (`flanke_bahn.py`, `flanke.py`): schräge Wände aus
  Geraden mit dem Mantel eines Schaftfräsers in einem Umlauf; an der Tasche mit 10° Formschräge
  0,69 min auf der Maschine statt 4,26 min Kugel in Höhenlinien. Im Assistenten
  (P-2026-10-04-25): der Block „Flanke (5 Achsen simultan)“ an einer 5-Achs-Maschine, im
  Wettbewerb mit dem 3D-Schlichten – die schnellere hat den Haken. **Zum Ausprobieren:**
  `beispiele/tasche_formschraege.FCStd`, „Beispielmaschine laden …“ → 5-Achs Tisch/Tisch, die
  acht schrägen Wände anklicken → Bearbeitung. **S4 Wegkippen** (Manuel: „Ja, bauen“): P-2026-10-04-30
  – beim 3D-Schlichten der Haken „Wegkippen (5 Achsen simultan)“: die Achse kippt von der Wand weg,
  nur wo der Halter mit der Auskragung sonst anstieße; darunter, wie weit der Fräser mindestens
  herausstehen muss. Kavität 30 tief, Schrumpffutter Ø 21: 26 statt 32 mm (2 mm Spiel am Halter,
  0,5 am Schaft, einstellbar: „SpielHalter“, „SpielSchaft“; P-2026-10-04-31). Auf der
  Tisch/Tisch-Maschine dreht C dabei rundherum – die Zeit kam vom Programm (1° wie 1 mm
  beim Schnittvorschub), seit P-2026-10-04-42 mit der halben Geschwindigkeit der Rundachse:
  rechte Kavitätenseite 3,00 → 1,52 min; seit P-2026-10-04-47 drehende Eilgänge als G1 im G93 und
  das Schwenken in einem Zug: 1,09 min (senkrecht 1,03). **S5 Entgraten in 3D – Prototyp zum
  Besprechen** (Spezifikation Strategien 16.3 S5, Bild an Manuel 2026-10-04): am Schwenkteil 24
  Kanten neu mit 5 Achsen (Fase 0,5 auf beiden Flächen), 10 bräuchten einen kleineren Fräser,
  1,7 min. **Gebaut (P-2026-10-04-65)** auf Manuels Antwort („nicht das Werkstück beschädigen“,
  „nicht nur auf den 45-Grad-Fräser“, „auch auf einer Dreiachs-Maschine“): Operation „Entgraten
  3D“ – 5 Achsen mit Fasenfräser oder Fräser mit ebener Stirn, 3 Achsen mit Fasenfräser senkrecht;
  im Assistenten der Block „Entgraten 3D“ (P-2026-10-04-66).
- **W-013 Manuels Testteil** – T1, T1b, T2, T3, T4 und T5 gebaut: das Räumen aller Höhen
  10,3 min (vorher 26,3), adaptiv, wo Ringe die Last nicht halten, dünne Lagen breit, „Rest
  räumen“ mit dem Ø 6, „Schlichten danach“; der Job sechs Arbeitsschritte mit drei
  Werkzeugen. Offen: T5d (unten); die 1,5 × Ziel zeigt der Assistent fürs Räumen (1,48 vor
  T2), für den ganzen Job ist sie nicht gemessen. Seit P-2026-10-04-59 hebt die Bahn nur so weit
  ab, wie das Material es verlangt (3D-Schruppen: Hub 315 → 37 mm), seit -61 geht der Eilgang
  vor dem Eintauchen bis 2 mm über das Material (Platte: Eintauchen durch Luft 133 → 89 mm). **Befund 2026-10-04 nachts (zum Besprechen,
  nichts geändert):** Das Räumen T1 fährt 3,5 m im Vorschub ohne Material (Materialstand Satz
  für Satz nachgefahren, Fräser genau) – davon 2,9 m die Verbindungen des Adaptiv-Kerns „durchs
  Freie“, die schon mit RUECKWEG 3 × Vorschub fahren (2 706 mm/min), 0,5 m mit dem
  Schnittvorschub; zusammen etwa 1,6 min von 10. Die anderen fünf Arbeitsschritte fahren keine
  Läufe über 20 mm durch die Luft. **Seit P-2026-10-04-39 im Freien mit dem Freivorschub** (alle
  Strategien, `freiwege`): Räumen T1 10,27 → 9,59 min. **Ebenso (zum Besprechen):** In der dreieckigen Tasche passt der
  Adaptiv-Kern mit dem Ø 6 nicht; das Räumen fällt auf Ringe zurück und nimmt über 16 mm am
  Stück bis 4,5 ae (Prüfstand: Eingriff bis 5,1 ae) – gegen „die Last im Rahmen“. **Seit
  P-2026-10-04-32 gemeldet** (Manuel: „dass keine Werkzeugbrüche entstehen“): gemessen auch ohne
  den Adaptiv-Kern, im Assistenten an der genauen Bahn („… keine Bahn hält hier die Last (bis 3,7
  ae): zu eng für diesen Fräser, Bruchgefahr …“), beim Neuberechnen eine Warnung im Bericht.
  **Seit P-2026-10-04-33 vermieden** (Spezifikation Strategien T5e): feiner gerechnet, wo es
  reicht, sonst mit gesenktem Vorschub in den Sätzen, die die Last sprengen – am Testteil die
  Ringe mit 29 Sätzen bis 0,3 × F, Last 1,49 ae. Manuels D-Bahnen (Bild 2026-10-04) an seiner
  Skizze geprüft: adaptiv ist dort schneller und hält die Last – zurückgelegt (Spezifikation
  Strategien T5e).
- **FreeCAD-Versionen (2026-10-12):** geprüft wird nur gegen die aktuelle Release (1.1.4 vom 28.09.)
  und den neuesten Wochen-Build (26.3 RC1 vom 08.10. – Manuels Version); immer wieder nachsehen
  (Arbeitsregeln, Abschnitt 9). Voller Lauf zuletzt am 2026-10-12 in 26.3 RC1 mit 0.255.3: 117 von
  117 Prüfdateien und alle Szenarien grün (nach P-141 bis -145). Der Wochen-Build vom 16.09. in
  `fcenv` ist veraltet und wird nicht mehr geprüft.
- Frühere Stände: 1.1.4 auf Manuels Rechner (Arch-Paket, Python 3.14) – alle 71
  Prüfungen und 98 Szenarien grün mit P-2026-10-02-85, seither je die Prüfung und das Szenario
  zum geänderten Teil. **1.1.3 (stabil):** mit 0.203.1 waren 19 von 110 Prüfungen und 25 von
  125 Szenarien rot (eine Regression im Abspieler, Umlaute ohne UTF-8-Locale, Wanduhr-Zeiten,
  zweiter Bildschirm, veraltete Erwartungen, elf Szenarien am Zeitlimit von 180 s auf dem
  ausgelasteten 4-Kern-Prüfrechner) – mit P-2026-10-09-01 (0.203.2) alles grün, die schweren
  Szenarien einzeln mit `CAMADDON_ZEITLIMIT=900`. Wochen-Build 26.3.0 dev (2026-09-16) zuletzt
  voll grün mit 0.96.0; auf Manuels Rechner gibt es beide nicht (Einrichten lädt mehrere GB –
  vorher fragen). Im Wochen-Build stürzte 26.3 einmal beim Schließen des 4-Achs-Fensters ab
  (`closeDialog`, FreeCAD selbst) – bleibt im Blick.

## Nächster Schritt (konkret)

**Manuels Bilder vom 2026-10-12 spät (zu 0.259.6, Nase):**
- „das sind in version 259.6 ja noch mehr zickzack fahrten geworden“ – die Pakete saßen hinten an
  den Zeilen dicht an der Flosse (vorn verdeckt sie die breitere Nase). *Erledigt:* P-2026-10-12-165
  (Plan indexiert: je Zeile offen nach vorn, sonst quer aus der geräumten Zeile daneben – am
  Nasen-Testteil 18 → 0 Rampen), P-2026-10-12-164 (Rundum schruppen mit Flächen: 14 → 0).
- **Sein Weg für die Nase** (Bild, von oben aus dem Revolver gesehen): der Schaftfräser beginnt
  seitlich neben der Stange hinten (rot), schwenkt im Bogen an die Flosse, fährt mit dem Umfang
  an ihr entlang nach vorn und vorn hinaus (gelb) – „einfach von außen einfahren und sozusagen mit
  dem schaft plan an der flosse vorbei fahren“. Dazu **die Front**: Fräser von oben, seitlich
  neben der Stange (grün), quer in Y ganz hindurch (gelb) – „fährt im ap und mit dem ae einfach da
  plan entlang“. Dann **drehen**, dass das Dreieck zur Seite zeigt, und mit derselben Stellung
  „vorne die spitze … oben und unten fertig machen“. Das ist Auftrag 1 in seiner Form: Flanke
  (Schaft, `Schaft` in Plan indexiert gibt es für die Seiten schon – Einfahrt im Bogen von der
  Seite fehlt) und die Front quer mit dem Umfang (neu). Erst als Bild mit Zahlen zeigen.
- **Werkzeugverwaltung, rote Zeile** „„494W D6“ heißt auch T3 – gewollt (Schwesterwerkzeug)?“ –
  Manuel: „was heißt hier t3 ?? versteh die rote ansage da unten nicht“. Gemeint: T4 (Ø 4, beim
  Kopieren von T3 entstanden) trägt denselben Namen wie T3 (Ø 6). Klarer sagen, etwa: „Diesen Namen
  hat schon T3 (Ø 6) – der Name passt nicht zu Ø 4. Umbenennen, oder ist es dasselbe Werkzeug
  zweimal im Magazin?“ – und den Widerspruch Name „D6“ ↔ Ø 4 selbst erkennen. *Erledigt:*
  P-2026-10-12-166 („Diesen Namen hat schon T3 (…)“, dazu „nennt einen anderen Durchmesser“).

**Manuels Ring-Teil (2026-10-12, 19:46, mit drei Bildern):** `~/freecad_cam/testteile/4_achs_planbearbeitung_testteil.FCStd`
– ein Ring Ø 65 × 8 mm (PartDesign: drei Segmente mit Schlitzen bis zur Bohrung, je eine Bohrung,
Ringnuten), Job „Body – 4 Achsen“: Stange Ø 70 von z −86,5 bis 1 (das Teil z −8 … 0), T4 Ø 4,
„Rundum schruppen“ 9 Lagen, 26.098 Befehle. Manuel: „ich wollte das teil eigentlich normal fräsen …
aber da es rund ist .. sagt mir der assistent .. hey das wird auf der 4 achs maschine bearbeitet ..
hab ich zwar nicht verstanden“; „warum fährt der da in der luft ??? warum in dem bauteil … komplette
anarchie“; „die nuten in dem bauteil werden garnicht bearbeitet face 28 face 6 face 17“. Zu tun
(nach den Werkzeugwegen, Manuel: „aufschreiben, erstmal weitermachen“):
- Der Assistent: Eine flache runde Scheibe (dünn längs, die Flächen stirnseitig) ist kein Teil für
  „Rundum“ – 3-Achs von vorn vorschlagen (oder beide, mit dem Grund in einem Satz).
  *Teilweise erledigt:* Zum 4-Achs-Assistenten schickt „Bearbeitung“ nur, wenn die gewählte
  Maschine eine Drehmaschine ist (Manuel hatte damals nur die CLX550). Ein rundes Teil geht auf
  der Fräse als „Zylinder mit Aufmaß“ im Dreibackenfutter (W-021). Der Satz an der Drehmaschine
  nennt jetzt beide Wege (P-2026-10-16-31). Offen: Fräsen an der Stirnseite der Drehmaschine
  (W-016).
- Die Bahn nachstellen: wo sie durch Luft fährt (hinter dem dünnen Teil die ganze Stange bis zum
  Futter?) und wo sie ins Teil geht (Bilder: Bahnen quer durch die Mitte, durch die Schlitze zur
  Bohrung; das Werkzeug steht im Teil) – mit „Bahn prüfen“ am Teil messen, dann beheben.
  *Ins Teil – erledigt:* P-2026-10-12-170 (Schaft und Halter in der Hüllfläche; vorher bis r −17,2,
  52 mm tief bei N 19). *Luft – offen:* 7 Lagen à ~5,9 mm, über den Segmenten aber nur 2,5 mm –
  die tieferen Lagen kreisen über dem fertigen Ring, nur um in die Schlitze zu gehen („nur nötig“
  greift da nicht); Idee: Lagen, die nur noch in schmalen Bereichen fräsen, als Zeilen dort (V4)
  statt der ganzen Spirale. *Erledigt ohne Querachse:* P-2026-10-17-26/-32 (Sektoren, am Ring
  100 → 11 km); mit Querachse Frage 1 in OFFENE_FRAGEN. „Bahn prüfen“ ist am Ring blind (das
  Strahlenmodell sieht die Bohrung nicht, wie Hinterschnitte).
- Face28, Face6, Face17 (die Nuten, stirnseitig): radial nicht erreichbar – das muss gesagt werden
  (nicht still weglassen) und eine Bearbeitung von vorn angeboten werden. *Erledigt:*
  P-2026-10-17-33 (der Satz nennt sie, „„Bearbeitung“ von vorn öffnen …“ als Verweis).

**Manuel am Ring-Teil in „Bearbeitung“ (3-Achs-Fräse, 2026-10-12 ~20:00, mit Bildern) – aufschreiben:**
1. **Kreise nach unten außerhalb des Rohteils**: „du bist hier auserhalb vom rohteil ... warum
   zirkulierst du da nach unten ?!?!?!?“ – rechts neben dem Rohteil eine Helix hinab (und daneben
   dichte Zickzack-Pakete). Verdacht: die Helix aus P-2026-10-12-162/163 (Kontur/Räumen) hält das
   Freie für Material. Nachstellen am Ring (Kopie in `~/freecad_cam/testteile/…`), beheben.
   *Erledigt:* es war die Kontur (Manuels Job hat kein Räumen) – P-2026-10-12-171: am Ring
   62 → 0 Rampen, keine Helix mehr außerhalb des Rohteils; dazu P-2026-10-12-169 (Räumen am Rand).
2. **Z −30 bei der Grenze −10**: „Z1 fährt in „Kontur T4“ bis −30,00 mm, die Grenze ist −10,00 mm“ –
   Manuel: „z kann nicht in -30 fahren weil z0 sollte eigentlich tisch oberkante sein .. also wenn
   die spindelnase auf dem tisch aufliegt ist z=0 ... wird wohl vom fräser aus gerechnet bitte schau
   da bei allen maschinen nach das dies nicht der fall ist“. Prüfen: wie Z der Maschine (Grenzen,
   „Was die Bahn braucht“) gerechnet wird – Spindelnase gegen Tisch, nicht die Spitze –, an allen
   Beispielmaschinen (3-Achs-Fräse, CLX550, 5-Achs, G550).
   *Erledigt:* P-2026-10-12-173 (3-Achs- und Portalfräse), P-2026-10-16-01 (die 5-Achs-Fräsen und
   die G550; Z = 0: Nase auf dem Tisch). Offen nur noch: Manuels gespeicherte „3-Achs-Fräse“ neu
   bauen (gespeicherte Maschinen behalten ihre Gelenke). Der Entwurf lag in `~/freecad_cam/wip/fuenfachs_z_null_entwurf.diff`
   (`_fuenfachs_wege` setzt Z gebaut auf die Nasenhöhe über der Spannfläche: Tisch/Tisch 300,
   Kopf/Kopf 280, Kopf/Tisch 300, G550 500 längs der Werkzeugachse; `stellung_setzen` verschiebt
   Offset1 längs der Gelenkachse; Vorgaben Z verschoben). Nachgemessen: Teile bleiben, +Z fährt weg.
   Noch rot: `test_beispielmaschine` (G550 fährt Z auf alte Relativwerte 100/485 – auf 600/985
   umstellen) und `test_raum_bahn` (Prüfsumme der Grenzen anders, Maschinen/Stücke/Intervalle gleich –
   prüfen, ob nur Rundung, dann die Referenz neu). Manuels gespeicherte „3-Achs-Fräse“ neu bauen.
   Der Rest dieses Absatzes ist die Herleitung.
   *Ursache (nachgesehen):* Gerechnet wird mit der Werkzeuglänge ab Spindelnase (reichweite), aber
   Z = 0 jeder Bauart ist die Stellung, in der sie gebaut ist – an der 3-Achs-Fräse die Spindelnase
   130 mm über dem Tisch (`test_reichweite`: „Werkzeug 50 mm … Z1 = −80 für Z 0“), an der Portalfräse
   175 mm; die Wege im Dialog „Neue Maschine“ zählen von dort. Manuels Grenze −10 meint „Nase auf dem
   Tisch“. Umstellen: Z = 0 = Spindelnase auf der Tischoberkante (Fräsen; die Drehmaschine zählt Z
   ab der Spindelnase des Futters – eigens prüfen) – im Bau (`beispielmaschine`, die Gelenke von Z),
   in den Wegen des Dialogs (mit einem Satz, was Z 0 ist) und in den Prüfungen (`test_reichweite`,
   `test_beispielmaschine`, Szenarien); gespeicherte Maschinen behalten ihre Wege – beim Öffnen
   umrechnen oder fragen.
3. *Zusammenhang (nachgemessen):* Weil Z dort die Grenze überschreitet, gilt jede Operation als
   nicht erreichbar, und der Materialstand lässt sie aus – die Kontur nach dem Planfräsen hielt
   die Nuten für voll (47 % Luft, 1,9 m Helix durch Geräumtes). Der Z-Nullpunkt behebt beides.
   **Planfräsen fährt „km in der Luft“** (Bild: T4 Ø 4 weit über dem Teil; „Planfräsen T4“ 20 min,
   Kontur 9,1 min am kleinen Ring) – die Luftwege messen (Bahnen prüfen ohne Manuel) und beseitigen.
   *Gemessen (2026-10-16, Kopie seines Jobs, frische 3-Achs-Fräse):* Planfräsen nur 8 % Luft – die
   19 min kommen vom Einsatz „Planen“ (ap 0,4) in den 4 mm tiefen Nuten (zehn Lagen); ob dort
   Räumen oder „Nut“ schneller wäre, erst messen und mit Bild zeigen (Strategiewahl). Kontur 46 %
   Luft – *erledigt:* P-2026-10-16-02 (Materialstand je Wandzug: 8,6 → 5,5 min, 22 % Luft). Die 115 von
   1088 Wandproben mit Material (die Schlitzenden ohne Schlichtzug) – *erledigt:* P-2026-10-16-03
   (Außenecken in `ohne_flaechen`): 0 von 1088.
4. ~~**B-020** „Konnte nicht anlegen: PropertyLink does not support external object“~~ – behoben in
   P-2026-10-16-42 (nachgestellt mit einem Link auf das Teil im Dokument der Maschine; der
   Assistent arbeitet jetzt im Dokument des Teils).
5. **Das Werkzeug passt nicht in die Nuten** (gefunden 2026-10-16, Kopie seines Jobs, seine
   Werkzeugverwaltung): Die drei Nutgründe (Face6, Face17, Face28) sind 10,05 mm breit. Planfräsen
   und Räumen nehmen T1 Ø 12 – der kommt nicht hinein. Planfräsen lässt 97 % des Nutgrunds stehen
   (bis 4 mm hoch), gewinnt den Zeitvergleich aber trotzdem, ohne rote Meldung. „Passt nicht“ gibt es
   bisher nur beim Räumen geschlossener Taschen. Mit T4 Ø 4: Räumen schruppen 5,4 min,
   Planfräsen 21,9 min. Plan: je Fläche die Reichweite des Fräsers prüfen (`zielzeit._schliessung`
   auf dem Raster von `_ziel_material`). Bleibt mehr als die Hälfte unerreicht, den größten
   passenden Fräser nehmen, wie `_nutfraeser_waehlen` es bei der Nut tut, mit einem Satz dazu. Die
   Fläche gilt dann nicht als fertig (`_fertige_flaechen`). Ob das Addon den Fräser selbst wechseln
   darf, ist eine Strategiewahl: erst in `OFFENE_FRAGEN.md`, mit Bild und Zahlen.
   *Erledigt:* P-2026-10-16-05. Passt der Fräser nicht hinein, nehmen Planfräsen und Räumen den
   größten passenden und sagen es in einem Satz (Frage 1 in `OFFENE_FRAGEN.md`). Erreicht eine
   Bahn ihre Fläche nicht, steht sie rot als „Nicht fertig“ mit Anteil und tritt im Zeitvergleich
   nicht an.
6. **Der Tisch fährt durch den Ständer** (Manuel, 2026-10-16, mit Bild: „wenn man die verfahrwege
   auf ein reales mass einstellt was die beispielsweise kao ming fähren kann .. fährt der tisch
   durch den ständer .. eher uncool“): 3-Achs-Fräse mit X ±650, Y −650 … 620, Z 0 … 600. Die
   Körper von `beispielmaschine.fraesmaschine` haben feste Maße (Tisch 700 × 280, Ständer bei
   y 650). Sie müssen mit den Wegen wachsen: Tisch, Sattel, Bett, Ständer und Kopf. Mit den
   Vorgabewegen bleiben die Maße wie heute. *Erledigt für die 3-Achs-Fräse:* P-2026-10-16-04
   (an allen acht Ecken keine Überschneidung). *Nachgemessen (Wege doppelt so lang, Drehachsen
   auf 0):*
   - Tisch/Tisch: Ständer ∩ Kopfschlitten bei Y ganz hinten.
   - Kopf/Tisch: Ständer ∩ Kopfschlitten und Schwenkkopf bei Y ganz hinten, Z unten.
   - G550: Bett ∩ Tisch bei Y ganz hinten, Spindel ∩ Säule bei Z unten.
   - Portalfräse: keine Überschneidung, aber das Portal fährt über das Bett hinaus.
   - Kopf/Kopf: ohne Befund.

   Diese Bauarten müssen genauso mit den Wegen wachsen. Lagerbock ∩ Zapfen (Tisch/Tisch) und
   Gabel ∩ Zapfen (Kopf/Kopf) sind gewollt: Das sind die Lager.
   *Erledigt:* P-2026-10-16-16. Tisch/Tisch, Kopf/Tisch (fahrender Ständer) und die Portalfräse
   wachsen mit den Wegen; mit den Vorgabewegen sind alle 58 Körper gleich. Mit doppelten Wegen
   gibt es keine Überschneidung mehr außer den Lagern. Die G550 bleibt bei den Herstellerwegen
   (800/1.020/970).

**Manuels C-Ring (2026-10-16, mit vier Bildern) – aufschreiben:**
`~/freecad_cam/testteile/3_achs_c_ring_nut_testteil.FCStd`. Manuel hatte es als `fraesteil.FCStd`
gespeichert: „bitte nenn es zu irgendwas sinnvollem um“. Das Teil ist ein Ring Ø 60 × 10 mit
Bohrung Ø 30 und einem Schlitz. Oben liegt eine 5 mm tiefe Ringnut zwischen Ø 35 und Ø 55, also
10 mm breit; ihr Grund ist Face8, sie ist zum Schlitz hin offen. Job „Körper – Fräsen“, Räumen mit
T1 Ø 12.
1. **Die grüne Fläche wird nicht bearbeitet.** Face8 ist gewählt, Räumen ist angehakt („1 Lage,
   adaptiv, etwa 1 min“). Manuel: „wird die grüne fläche bearbeitet ???? neiiinnn“. Die Ursache
   ist dieselbe wie beim Ring, Punkt 5: Ø 12 passt nicht in die 10 mm breite Nut, und das wird
   nicht gesagt. Es steht nur der allgemeine Satz „Ecken und Nuten, enger als er, bleiben für
   einen kleineren“. Damit ist Punkt 5 an zwei Teilen belegt und kommt als Nächstes.
   *Teilweise erledigt:* P-2026-10-16-05. Jetzt nehmen beide T3 Ø 6. Räumen erreicht damit nur
   35 % der Nut (siehe Punkt 7) und tritt nicht an; das Planfräsen erreicht sie, aber im Zickzack.
   Richtig wird es erst mit der Bogennut (Punkt 7).
2. *Nachgemessen (2026-10-16): An runden Wänden ist der letzte Zug des Räumens exakt rund
   (Tasche Ø 40, Zapfen Ø 20). Die eckigen Züge auf Manuels Bild lagen außen im Rohteil; seit
   P-2026-10-16-12 räumt Räumen dort nicht mehr, wenn nur die Nut gewählt ist.*
   **Zickzack an den Rundungen**: „die vorschrupp bahnen sind rund .. und wenns zum fertig
   schruppen kommt ists nen eck ??? … das selbe im inneren kreis“. Beim Räumen ist der letzte Zug
   außen um Ø 60 und innen in der Bohrung Ø 30 eckig und zackig, die Züge davor sind rund.
   Verdacht: Der letzte Zug folgt dem Rand aus dem Raster statt dem Kreis. Nachstellen und messen.
3. **Durch den Schlitz weiter bis zur Mitte**: „wenn du schon in die öffnung reinfährst .. warum
   dann nicht weiter fahren ist für den fräser schonender das auf volle tiefe raus zu arbeiten als
   im kreis einzutauchen .. auch spähnevolumen technisch ists sinnvoller bis zuur mitte die D's
   noch weiter fahren und dann mit den reisen rausfahren“. Heute arbeiten D-Bögen (trochoidal) im
   Schlitz, und die Bohrung wird getrennt mit einer Helix angefahren und in Kreisen geräumt. Sein
   Weg: die D-Bögen auf voller Tiefe durch den Schlitz bis in die Bohrung weiterführen, dann die
   Bohrung von dort aus in Kreisen ausräumen, ohne eigenes Eintauchen. Das ist eine Strategiewahl,
   also erst als Bild mit Zahlen zeigen.
   Manuels Bild dazu („so meinte ich das mit der mitte rausfahren vll war der 12 fräser zu gross
   das kann sein“): D-Bögen von außen durch den Schlitz bis an die Bohrung. In der Bohrung werden
   die Bögen von der Schlitzmündung aus immer größer, bis der Kreis frei ist; die Rückwege laufen
   im Schnellvorschub quer. Unser Räumen fährt so ähnlich (adaptiv), sobald der Fräser durch den
   Schlitz passt: Am C-Ring mit Ø 6 ging es durch den Schlitz in die Bohrung. Mit Ø 12 tauchte es
   in der Mitte mit einer Helix ein. *Nachgerechnet (2026-10-16, Bild und Zahlen: Frage 4 in
   `OFFENE_FRAGEN.md`):* Räumen bis durch fährt mit Ø 8 genau seinen Weg (4,2 min, bis 2,5 ae,
   keine Rampe); heute fährt dort die Kontur (7,1 min, bis 8,1 ae, 63 mm Vollschnitt). Ob Räumen
   an durchgehenden Wänden antreten darf, ist Manuels Entscheidung.
4. **„Anlegen“ schon in Schritt 1** (Bild: „Schritt 1 von 3 – Aufspannung“, oben „Anlegen“
   klickbar): „das anlegen sollte erst frei sein wenn alle angaben gemacht worden sind“.
   *Erledigt im Assistenten „Bearbeitung“:* P-2026-10-16-09. *Nachgesehen (2026-10-16):* Der
   4-Achs-Assistent heißt in Schritt 1 schon „Weiter“ (zwei Schritte, `gui_vierachs`), „Ebene
   schwenken“ (3+2) hat nur einen Schritt und gibt OK erst mit einer gültigen Richtung frei, ein
   eigener Dreh-Assistent existiert nicht – dort ist nichts zu tun. Das
   Prüfen-Fenster des Assistenten „Bearbeitung“ bietet „Anlegen“ in jedem Schritt an. Künftig erst
   ab Schritt 3 (Flächen gewählt, Strategie angehakt), vorher grau. Der Hinweis sagt, was noch
   fehlt („Erst die Flächen wählen – Schritt 2“), so wie „Nächster Schritt als Knopf“ es verlangt:
   nie grau ohne Grund. In den anderen Assistenten (4 Achsen, 3+2, Drehen) dasselbe ansehen.
5. **Mit Aufmaß 0 schlägt er Planfräsen vor** (Bild: Aufmaß oben 0, seitlich 0, unten 6; Face8
   gewählt; angehakt „Planfräsen → 1 Lage, 23 Zeilen, etwa 1 min · 2,27 × Ziel“, Räumen
   „5,09 × Ziel“; „Ziel mit T1 Schaftfräser Ø 12: 0,2 min“). Manuel: „als vorschlag planfäsen ....
   bei 0 aufmass“. Auch hier passt Ø 12 nicht in die 10 mm breite Nut. Planfräsen gewinnt, obwohl es
   den Nutgrund nicht erreicht, und das Ziel rechnet mit einem Fräser, der gar nicht hineinkommt.
   Gehört zu Punkt 1 und zu Ring Punkt 5.
6. **Was Planfräsen ist** (Bild: die Planfräsen-Bahn mit Ø 12 an Face8 – Zickzack-Rampen außen
   an den Ecken des Rohteils und in der Mitte, nichts in der Nut). Manuel: „das sehe ich nicht als
   planfräsen an das gehört schon eher zum raeumen .. planfräsen ist auf z0 bringen würde ich
   behaupten oder seitlich eine seite auf 0 bringen .. aber das is zickzack fahren obwohl wir
   gesagt haben das ist keine sinnvolle strategie !!!“. Daraus folgt zweierlei:
   - Planfräsen tritt nur für Flächen an, die oben offen liegen: die Oberseite auf Z 0, bei 3+2
     die Seite, die zur Spindel zeigt. Einen Nut- oder Taschengrund mit Wänden ringsum räumt das
     Räumen. Absätze, die zu einer Seite offen sind, gehören wohl auch zum Räumen, aber nicht
     raten, sondern als Frage aufschreiben.
     *Erledigt für Taschen- und Nutgründe:* P-2026-10-16-13 (`hoehenfeld.eingeschlossen`: an
     mindestens drei Vierteln des Rands eine Wand). Die Absätze sind Frage 3 in
     `OFFENE_FRAGEN.md`.
   - Die Zickzack-Rampen im Planfräsen: *erledigt* P-2026-10-16-25. Beginnt eine Zeile im
     Material, taucht sie mit der Helix ein (der Kreis auf der Zeile oder um einen Radius nach
     innen versetzt, alles darin geprüft). Die Rampe gibt es nur noch, wo kein Kreis Platz hat.
     Der Entwurf in `~/freecad_cam/wip/planfraesen_helix_entwurf.diff` ist damit überholt.
7. **Zickzack in der offenen Nut** (Bild: Face8 mit kleinerem Fräser, in der ganzen Ringnut dicht
   an dicht Zickzack-Rampen mit Abhebern). Manuel: „hier haben wir wieder zickzack fahren ... in
   etwas was ne offene nut ist .. das geht garnicht .. die offene nut kann man volle tiefe mit D's
   abarbeiten .. oder beide richtungen .. also sollte generell als auswahl vorhanden sein das man
   gleich und gegenlauf fräst... und somit sozusagen wellen da rein fährt“. Daraus:
   - Eine Nut, die zu einer Seite offen ist (hier zum Schlitz), wird vom offenen Ende her auf
     voller Tiefe mit D-Bögen (trochoidal) abgearbeitet. Kein Eintauchen und keine Rampe.
   - Als Auswahl, generell: Gleichlauf, Gegenlauf oder beides. Bei „beides“ fährt das Werkzeug
     hin und zurück und ohne Leerweg, das sind Manuels „Wellen“.

   Der Block „Nut“ kennt offene Nuten, aber nur gerade Langlöcher (`nut_bahn`, `test_nut_offen`).
   Face8 nimmt er nicht an („Keine Nut gewählt“). Nachgemessen am C-Ring mit T3 Ø 6: Räumen
   überstreicht nur 35–64 % des Nutgrunds, in allen Varianten (adaptiv, Ringe). Der erlaubte
   Streifen für die Fräsermitte ist dort etwa 1,4 mm breit und zerfällt im 1-mm-Raster in Stücke.
   Das Planfräsen erreicht ihn, aber im Zickzack. Nötig ist also die Nut entlang einer gebogenen
   Mittellinie (Ringnut, Bogennut), mit D-Bögen von außen.
   Manuels Bild dazu, wie „anständige D's“ aussehen („das gelbe ist schnellvorschub .. und das
   blaue ist barbeitung und das grüne an den ecken ist einfahrt“):
   - blau, schneidend: der D-Bogen, ein Halbkreis mit geradem Rücken;
   - gelb, Schnellvorschub: zurück quer über die freie Seite;
   - grün: an den Ecken der Einfahrt ein Bogen.

   So arbeitet `nut_bahn` die gerade offene Nut schon („Bögen statt Kreisen“). Für die Ringnut
   kommt die Mittellinie als Bogen dazu: Die Bögen stehen quer zur Nut und rücken längs des Bogens
   vor.
   Dazu Manuel mit einem Bild aus einem anderen CAM (Bögen in Lagen längs der Nut: „der ist genau
   so wenig schlau“): „da wo das C offen ist seitlich volle tiefe mit D's rein fahren in die nut
   und dann die volle tiefe erstmal rausarbeiten mit D's in beide schnittrichtungen also in gleich
   und gegenlauf so das man kaum schnellvorschub hat sondarn meist schneidet .. und zum schluss zum
   schlichten kann man dann die ränder abfahren“. „Beide Richtungen“ heißt: Der nächste Bogen
   schneidet zurück, im Gegenlauf, statt quer im Schnellvorschub zurückzufahren. An der Wand geht
   es um einen Schritt vor, dann der nächste Bogen im Gleichlauf. Am Ende werden die Wände
   geschlichtet.
   *Erledigt:* P-2026-10-16-07.
   - Die Nut erkennt die Bogennut: zwei Wände als Bögen um eine Mitte, an beiden Enden offen.
   - Die Bahn wird in einer gestreckten Nut gerechnet und auf den Bogen gelegt.
   - Neu „Gleich- und Gegenlauf (Wellen)“, als Haken, angehakt: Am C-Ring braucht die Nut mit
     Ø 6 2,95 statt 3,84 min, ohne Rückweg im Schnellvorschub.
   - Draußen hinab nur, wo auch im Materialstand Luft ist. Ist der Schlitz noch voll, beginnt die
     Nut mit der Helix im Ende.

   Im Assistenten gewinnt am C-Ring jetzt die Nut (T3 Ø 6, 1,2 min). Räumen tritt nicht an, es
   erreicht nur 43 %.

**Manuel, 2026-10-16 nachmittags – aufschreiben:**
1. **Alle Strategien auf Zickzack durchsehen**: „also so generell was wir hier besprochen haben ...
   solltest du mal bei allen strategien prüfen ..das zickzack fahren is ja beängstigend“.
   Je Strategie an seinen Testteilen (3-Achs-Testteil, Ring, C-Ring, Nase, Geist) zählen: Rampen,
   Eintauchen, Rückwege im Eilgang. Die Regel aus Einfahren Punkt 4 und `spezifikation_strategien.md`
   Abschnitt 5 gilt überall: von außen aus der Luft, sonst Helix, Zickzack nur in der zu schmalen
   geschlossenen Nut. Bekannt sind Planfräsen (Rampe, wo kein Rand offen ist) und
   `schlicht_anlauf`.
   *Gezählt (P-2026-10-16-13, Prüfstandsteile, Einfahrten mit Hin und Her beim Absenken):*
   - Planfräsen: Absatz 1, Tasche 5, Bohrungen 4. Die Taschen- und Bohrungsböden nimmt es seit
     P-13 nicht mehr; am Absatz siehe Frage 3. Seit P-2026-10-16-25 sind Absatz und Tasche Helix
     statt Zickzack; nicht ins Teil, kein Rest. In den Bohrungsböden passt kein Kreis, dort
     bleiben die 4 Rampen.
   - Kontur: Tasche 6, Bohrungen 21, Platte 11. Das ist die Kontur, die eine ganze Tasche allein
     ausräumt (sie verliert dort gegen Räumen): Eine Helix ginge nur mit Vollschnitt danach.
     Offen ist, wie die Kontur dort von einer Helix aus in die erste Bahn kommt.
   - Räumen: 0.

   - Nut (Vollnut): Helix statt Zickzack, wo Platz ist (P-2026-10-16-21).

   - Rundum schruppen und Rundum schlichten an der Nase (Beispiel, neu gerechnet 2026-10-16):
     3 bzw. 1 Einfahrt nach einem Eilgang, keine mit Kehre; die beiden langen Abwärtsläufe mit
     Richtungswechsel sind das Abfahren der Nasenspitze, keine Einfahrt.

   - `schlicht_anlauf` (durchgesehen 2026-10-16): Die Rampe senkt nur um die Resthöhe + 0,1 mm
     (nach dem Schruppen meist unter 1 mm), längs des ersten Schnitts auf der Fläche. Hin und her
     fährt sie nur, wenn dieser Schnitt kürzer ist als die Rampe. Eine Helix geht auf der
     3D-Fläche nicht; so bleibt es.

   - Plan indexiert an der Nase: 0 Rampen seit P-2026-10-12-165 (die 4 von 37 aus P-161 fahren
     quer aus der geräumten Zeile daneben hinein); `test_vierachs_plan` prüft es an Face4 und
     Face6. Eine Rampe bleibt nur im geschlossenen Feld zwischen zwei Wänden, dort im Kreis hinab.

   Damit ist jede Strategie gezählt (2026-10-16). Zickzack bleibt nur, wo für einen Kreis kein
   Platz ist: Vollnut mit weniger als 0,1 R zwischen Fräser und Wand, Planfräsen in engen
   Bohrungsböden (nimmt der Assistent nicht mehr), Räumen in sehr schmalen Streifen. Dazu kommt
   die Kontur, die eine ganze Tasche allein räumt (verliert dort gegen Räumen). Die Nut auf dem Mantel (4 Achsen, `vierachs_planbahn`, Rundachse
   dreht) fährt noch ihre eigene Rampe.
2. **Das Update lädt zu viel**: „die fotos sind ja nicht im main mit dabei .. heist wenn ich addon
   update drücke .. dauert das mitlerweile ganzschön lang … bilder fürs forum usw muss da nicht
   dabei sein“. Nachgesehen: Manuels Addon kam als ZIP von GitHub (`…/archive/main.zip`, kein
   `.git`). Das sind 15,6 MB je Update, davon `beispiele` 8,9 (Nase 5,2, Geist-STL 3,3,
   Freiform-NC 2,8 unkomprimiert), `docs` 3,9, `tests` 1,0 und `camaddon` 1,3 MB.
   *Erledigt:* P-2026-10-16-08 (`.gitattributes`: was zum Laufen nicht gebraucht wird, kommt
   nicht ins ZIP).
3. **Die Besprechungen gehören nicht ins Haupt-Repository**: „unsere konversationen im repo
   [haben] nichts zusuchen … zumindest nicht im main repo .. gibts da einen alternativen weg“.
   Mit P-2026-10-16-08 landen sie nicht mehr auf den Rechnern der Nutzer, auf GitHub stehen sie
   aber weiter öffentlich, samt Verlauf. Ein eigenes privates Repository ist seine
   Entscheidung: Frage 2 in `OFFENE_FRAGEN.md`.
4. **„Anlegen“ heißt in Schritt 1 und 2 „Weiter“** (Bild, 0.260.5, Schritt 1): „auch in der 260.5
   ist der anlegen button schon anklickbar obwohl noch zwei weitere auswahl felder kommen vll
   sollte man das als "weiter" button deklarieren exakt wie den unten rechts“. Siehe C-Ring
   Punkt 4. *Erledigt:* P-2026-10-16-09 (oben „Weiter →“ bis zum letzten Schritt, dann
   „Anlegen“).
5. **„Maschine transparent“ beim Abfahren** (Bild: „Auf der Maschine prüfen“, Abfahren „Räumen
   T2“ am C-Ring; Spindel und Halter verdecken Teil und Bahn): „hier kann man nichs sehen oder
   erkennen .. waäre gut wenn man einen hacken macht mit "maschine transparent"“. Ein Haken neben
   „Bahn“ und „Teil“, der die Körper der Maschine (Spindel, Kopf, Tisch, Spannmittel)
   durchsichtig macht. Dazu: „vll maschine ausblenden ... also beides .. transparent und
   ausblenden so das nur das werkzeug mit halter zu sehen ist“. *Erledigt:* P-2026-10-16-10
   (Auswahl „Maschine zeigen / durchsichtig / ausblenden“ unter den Abspielknöpfen, gemerkt).
6. **Beispiele: alle im Repository, im Update wählbar** (Antwort auf Frage 3): „ich finde es
   sollten alle testteile im repo vorhanden sein ja ... allerdings solte der benutzer auch
   irgendwie die möglichkeit haben sie nicht zu laden .. vll kann man "mit beispiel datein" oder
   "ohne beispiel dateien" ... (maschinen sind immer dabei geht nur um die dateien wie C-ring und
   die von dir aufgeführen .. )“. Plan:
   - C-Ring und Ring kommen nach `beispiele/`; das 5-Achs-Ausweichteil erst, wenn Manuel es fertig
     meldet.
   - `beispiele/` per `export-ignore` aus dem Update-ZIP nehmen.
   - Im Addon ein Befehl „Beispiele laden …“, der sie auf Wunsch von GitHub holt (in einen
     eigenen Ordner, mit Größe vorher).
   - Die Maschinen entstehen im Code und sind immer dabei.

   *Erledigt:* P-2026-10-16-14.
   - Das Update-ZIP ist 1,7 MB groß (vorher 15,6).
   - Die 36 Beispieldateien (13,3 MB, darunter C-Ring und Ring) holt „Beispiele laden …“ nach
     `…/CamAddon/beispiele`, mit Größe, Prüfsumme und „schon da“.
7. **Nur was angeklickt ist, wird bearbeitet** (Bilder: C-Ring, nur Face8 gewählt; die Bahn
   räumt auch außen um den Ring, die Bohrung und den Schlitz; in der Nut kleine Zickzack-Stücke):
   „ich hatte nur den inneren ring ausgewählt warum wird ausenrum alles gefahren und in der mitte
   ich wollte doch nur die nut bearbeitet haben .. da wo eh frei ist druchzufahen ist kein
   problem .. nur das andere muss ja erstmal garnicht sein vll will ich das mit einem anderen
   fräser machen … die nut finde ich so gut so sollte auch wirklich nur die nut bearbeitet
   werden“. Und zur Auswahl (Bild: der Außenmantel grün): „wenn ich den matel haben will ist das
   meine auswahl“; mit Außenmantel, Bohrung und Schlitzwänden grün: „und das wenn ich ausen alles
   bearbeiten will .. also da is halt ausen und innen zu bearbeiten alles was ausgeählt ist“.
   *Nachgestellt (P-2026-10-16-15):*
   - Mit diesen Wänden fuhr die Kontur außen herum, die Bohrung aber still gar nicht. Der Schlitz
     ist außen 11,7 mm breit, Ø 12 mit Aufmaß kommt nicht durch, und von den zwei Schleifen des
     Versatzes blieb nur die äußere.
   - Jetzt fährt sie beide, jede von außen zur Wand. Am Prüfstand Rest 0, nichts ins Teil.
   - Die Last ist hoch (bis 7,8 ae), wie bei jeder Kontur, die eine Tasche allein ausräumt. Das
     gehört zum Zickzack-Punkt der Kontur.
   Daraus:
   - Ein gewählter Boden (Nut, Tasche, Absatz) heißt: das Material über ihm, nicht die ganze
     Ebene bis zum Rand des Rohteils.
   - Außen herum, die Bohrung, der Schlitz: nur, wenn ihre Flächen angeklickt sind (der Mantel
     für außen).
   - Durchfahren, wo schon Luft ist, darf jede Bahn.

   Heute räumt das Räumen eine offene Fläche vom Rand des Rohteils her (`raeumen_bahn`, Variante
   „rohteil“/adaptiv). Das muss auf das Gebiet über den gewählten Flächen begrenzt werden.
   Nachstellen, welcher Block bei ihm lief (Räumen neben der Nut?).
   *Erledigt fürs Räumen:* P-2026-10-16-12. Eine gewählte Fläche unter der Oberseite wird nur
   über ihrem Umriss geräumt (einen Fräserradius darüber hinaus), durch Luft nur, soweit sie mit
   der Fläche zusammenhängt. Am C-Ring: 0 Punkte außen, 0 in der Bohrung (vorher alles bis zum
   Rand des Rohteils). Bei ihm lief „Räumen T2“; seine Werkzeugverwaltung (27.1) hat T1 Ø 12 und
   T2 Ø 6. Planfräsen und Kontur sind noch nicht so durchgesehen.
   Zum Zickzack in der Nut („warum ? fahr doch einfach nen kreis“): Ist die Nut im Quader zu,
   fräst ein Fräser, der kaum schmaler ist als sie (`verfahren` → „vollnut“), mit der
   Zickzack-Rampe. Stattdessen am Ende mit der Helix (Kreis) hinab, dann geradeaus.
   *Erledigt:* P-2026-10-16-21. Nachgemessen am C-Ring (Beispiel, Face8): Mit Ø 6 ist es das
   Räumen – im 1,4 mm breiten Streifen für die Fräsermitte zerfällt der Raster in kleine Ringe,
   jeder mit einer Rampe rundum (13), das sieht aus wie Zickzack. Dort gewinnt seit P-07 die Nut
   (D-Bögen, ohne Rampe). Mit Ø 8 bis 9 und vollem Schlitz ist es die Vollnut: Sie taucht jetzt je
   Lage am Ende mit der Helix ein und fährt dann geradeaus (am C-Ring im Quader mit Ø 13,6:
   1,47 statt 1,77 min). Zickzack nur noch, wo zwischen Fräser und Wand weniger als 0,1 R Platz
   ist.

**Aufträge aus Manuels Antworten vom 2026-10-12 abends** (zu den Fragen 16–20; in dieser Reihenfolge):
1. **Die Nase zuerst mit dem Schaftfräser Ø 12** (Frage 18, Manuel: „die nase … wenn man sie … nach
   unten dreht, so dass die fläche der nase zum fräserboden schaut … einfach bearbeiten indem man mit
   einem schaftfräser dort entlang fährt … VOR dem schruppen … vll sogar ohne aufmass“): „Plan
   indexiert“ als erste Operation, „Rundum schruppen“ und „Rundum schlichten“ wissen, was schon weg
   ist (Materialstand), die Kugel fährt dort im Freivorschub drüber und nimmt oben nur die Gerade.
   Die Seiten des Dreiecks so stellen, dass sie parallel zum Schaft stehen, und **mit der ganzen
   Schneide von vorn hineinfahren** (volles ap und ae, „wie wenn es im schraubstock gespannt wäre
   senkrecht“) – nicht im Zickzack eintauchen („da sie die schneide sehr schnell kaputt machen“).
2. **Plan indexiert fräste nur bis zur Mitte, nicht bis zur Nase** (Frage 19, Manuel: „beim
   planindexieren hat der schaftfräser nur bis zu mitte gearbeitet nicht bis zur nase“) – nachstellen
   und beheben. *Nachgemessen (2026-10-12 abends):* im Beispiel-Job (`testteil_4achs_nase.FCStd`,
   T1 Ø 12, 22,2 / 5,4 / 0,3) deckt die Bahn Face4 und Face6 (die Seiten, quer bis ±42,7) und Face8
   (zur Mitte, unter der Drehmitte) ganz ab, Zeilen wie Stiche. Nicht nachgestellt – braucht Manuels
   Job oder ein Bild, wenn es wieder vorkommt (Face8 kommt nur dazu, wenn der Weg vor ihr frei ist,
   `zur_achse`).
   **Manuels Bild dazu (2026-10-12, 19:10):** [nase_plan_zickzack_manuel.png](bilder/vorschlaege/nase_plan_zickzack_manuel.png)
   – „Plan indexiert“ und „Rundum schruppen“ an der Nase: An der Dreiecksfläche (Seite der Nase)
   fahren die Zeilen im Zickzack ein (die Rampe mit dem Eintauchwinkel, weil die Zeile im Material
   beginnt) und kommen nicht bis an die Fläche der Nase – „was kompletter blödsinn ist für was
   ?!?!? … einfach auf volle tiefe ap fahren und an der planfläche entlang fahren … da brauch ich
   kein zickzack fahren … und meine planschneide kaputt machen“. Also: von der freien Seite (vor
   der Stange) mit vollem ap hinein und an der Fläche entlang, bis an die Nase; keine Rampe, wo die
   Zeile aus der Luft kommen kann. Das ist Auftrag 1. *Erledigt für das Einfahren:* P-2026-10-12-161
   (nach dem Schruppen keine Rampe mehr, von der Stange 4 von 37 – davor steht die Nase).
3. **Vorschlichten** (Frage 17, Manuel: „warum kann die nicht einfach die bereiche die sie beim
   fertig schlichten viel nehmen würde vorher auf 0.3mm aufmass runter fahren“): nur dort, wo die
   Kugel beim Schlichten viel nähme, vorher mit der Kugel auf 0,3 mm Aufmaß – mit den schnellsten
   Wegen (Spiralrampen, D's in Werkzeug-Z …), nicht die ganze Spirale. Kein kleinerer Fräser als die
   Kugel („quatsch … man muss sich mit der kugel die schnellsten strategien zusammen suchen“). An
   der Nase erledigt das Punkt 1.
4. **Einfahren überarbeiten:** „generell … das die entwickelten einfahr strategien nicht die besten
   sind … irgendwie ist da viel zickzack fahren wo keins hin muss“; die Regel steht in
   `spezifikation_strategien.md`, Abschnitt 5 (von außen aus der Luft → Helix → Zickzack nur in der
   zu schmalen geschlossenen Nut). Manuel: „warum nutzt du es dann überall ??“ – die Rampe
   (`vierachs_bahn._rampe`) ist der Einstieg überall, wo eine Bahn im Material beginnt. Noch
   durchzusehen, je mit Zählung an seinen Testteilen (3-Achs-Testteil, Nase, Geist):
   ~~`kontur_bahn._rampe` (Kontur)~~ (Helix, P-2026-10-12-162), ~~`raeumen_bahn` (Ringe/Stiche über `kontur_bahn._rampe`)~~ (Helix, P-2026-10-12-163),
   ~~`planfraesen_bahn` (Rampe, wo kein Rand offen ist)~~ (Helix, P-2026-10-16-25), ~~`vierachs_bahn` (Rundum schruppen zwischen
   gewählten Flächen)~~ (von vorn aus der Luft, P-2026-10-12-164), ~~`vierachs_planbahn` (die 4 übrigen vor der Nase: von der Seite statt von
   vorn)~~ (P-2026-10-12-165), `schlicht_anlauf`. Bleiben darf sie nur in `nut_bahn` (geschlossene Nut, zu schmal für
   eine Helix); überall sonst erst „von außen in der Luft“, dann Helix (`bohrung_bahn._helix` gibt
   es schon).
5. ~~**Einrichtblatt für jede Bearbeitung** (W-019, Frage 16)~~ (P-2026-10-16-20, Rest siehe
   Wunschliste) und **bewegliche Spannmittel** (W-020) – siehe Wunschliste.
6. **„Kollision prüfen“ am Geist braucht über 12 GB** (2026-10-12 abends, 18:58): Geist auf der
   Beispiel-Drehmaschine (Szenario-Werte, 392.634 Stationen) – der Kernel beendete den Lauf an seiner
   12-GB-Grenze (Popup bei Manuel). Speicher der Kollision mit STL-Teil und Pool nachmessen und
   begrenzen (Speicherwächter, `kollision_parallel`); danach die Gegenprobe zu P-160: ob der Fräser
   unter den Armen wirklich nicht ins Teil geht. Der Sprung ans Ende steht jetzt 0,25 statt 1,5 s.
Frage 20 (Bereiche an einem STL wählen) entfällt: Ein STL wird immer rundum bearbeitet, angeklickt wird
nur, wie es liegt (Manuel: „klar soll das immer rundum bearbeitet werden is ja ne stl“).

**Aufträge aus Manuels Antworten vom 2026-10-11 morgens** (Verlauf P-2026-10-11-30; Reihenfolge so
abgearbeitet):
1. ~~**Abtrag im Abspieler auch mit schrägem Werkzeug** (Flanke, 3+2, simultan).~~ Erledigt:
   P-2026-10-11-32 (Höhenfeld – Hinterschnitte zeigt es nicht).
2. ~~**Flanke: der Halter darf nicht ins Teil**~~ – erledigt im Assistenten: P-2026-10-11-33
   (rot mit „mindestens … mm“; anders anstellen hilft bei der Flanke nicht). Die Bahn der Flanke
   rechnet ihre Prüfungen auf den Nebenrechnern: am Kegel 15,5 → 2,7 s (P-2026-10-11-34).
3. **Kollision (Frage 7):** ~~im Abspieler an der Kollision anhalten, Knopf „Zur nächsten
   Kollision“~~ (P-2026-10-11-35); ~~klare Meldung, wenn die Ausspannlänge nicht reicht~~
   („bräuchte mindestens … mm“ im Befund, P-2026-10-11-38; an der Flanke P-2026-10-11-33; im
   4-Achs-Assistenten schon vor dem Anlegen, P-2026-10-11-51; „T1 auf … mm ausspannen“ als Verweis
   im 4-Achs-Assistenten, im Prüffenster und an der Flanke im 3-Achs-Assistenten,
   P-2026-10-11-63 bis -65). Offen: die Bahn weicht aus
   (Anstellung, Y), wo die Form des Teils bleibt – am Nasen-Testteil hilft das nicht (ER32 Ø 50 über
   einer 20 mm breiten Nase, zu kurz eingespannt); die Maschine selbst (Kopf, Revolver) beim Rechnen
   der Bahn.
4. **Querachse nur, wo nötig (Frage 9):** „C dreht nicht zurück“ (P-2026-10-11-37) – die
   Werkzeugachse quer nur, soweit C weiterdreht; am Testteil 187,5 → 177,8 min, keine Umkehr mehr.
   Dasselbe für „Rundum schruppen“ mit der Querachse (Frage 11, Manuel 2026-10-11: „als option
   anbieten … wens ruhiger wird ists gut“): Haken, vorbelegt an – erledigt, P-2026-10-11-47.
5. **Rest nach dem Schruppen (Frage 8)** im Assistenten melden und mehr anbieten: an schrägen
   Wänden zusätzlich in Z abzeilen (Schaftfräser) oder dort am Umfang mit kleinerer Steigung.
   Nachgerechnet (Voxel): die halbe Steigung überall kostet 14 min und nimmt der Kugel nur 10 %.
   Die „408 mm³ je mm an der Nase“ vom Morgen waren ein Messfehler (Weg ohne Y); richtig: höchstens
   4 mm³ je mm, mehr als 1 auf 2,6 von 100 m (P-2026-10-11-44). ~~Die Meldung im Assistenten~~
   steht (P-2026-10-11-44: „Rest für die Kugel …“, gelb ab 4 × Aufmaß × Schrittweite). ~~Die
   Abhilfen als Knopf~~ – gemessen (Voxel, Nase, Querachse, Zustellung 22,2): die halbe Steigung
   15,4 → 29,6 min Schruppen, die Kugel nimmt 12,1 → 10,8 cm³; Zustellung 5 mm 65,4 min, 10,0 cm³;
   der Rest bleibt überall höchstens 4 mm² im Querschnitt. Lohnt nicht als Knopf; die Zustellung
   stellt Manuel schon selbst.
6. **Nase mit dem Schaftfräser (Frage 5):** C so, dass Face8 (zur Mitte) quer zum Fräser steht,
   mit Y abzeilen (X auch unter 0, soweit die Maschine fährt); die Seiten Face4/Face6 mit dem
   Schaftfräser (Plan indexiert oder angestellt mit dem Schaft); die Kugel nur noch Face9 – Bild
   mit Zahlen als Frage 10 (187,5 → 159,3 min). Vorgebaut: „Plan indexiert“ mit `zur_achse`
   (P-2026-10-11-42), im Voxelmodell kein Schnitt ins Teil. **Manuels Antwort (11.10.):** der
   Schruppfräser macht es – die Nase dreht sich so, dass seine Unterkante parallel zu Face8 steht,
   den Rest macht die Kugel rundum; für die Seiten **beide Varianten** anbieten (Stirn wie „Plan
   indexiert“, angestellt mit dem Schaft); X unter 0 ist keine Frage – die Grenze kommt aus der
   Maschine, mit Halter und Werkzeug gerechnet (vom VDI-Halter aus etwa 200 mm ins Minus).
   Erledigt mit der Stirn: P-2026-10-11-48 (rundum vorbelegt, Schruppfräser, Face8 dabei); die
   Seiten mit dem Schaft als Haken (vorbelegt aus – Manuels T1 reicht mit 26 mm Schneide dort
   nicht): P-2026-10-11-49.
7. ~~**Magazin ohne Maschine** sagt das im Fenster (legros).~~ Erledigt: P-2026-10-11-31.
Frage 6 erledigt: Schrittweite aus der Kammhöhe (Vorgabe 0,02 mm), Spalte „ae max“ (P-2026-10-11-40).
Frage 12 erledigt (Manuel, 11.10. abends: (c), angehoben im Freivorschub): die Spirale mit Y rundum, über den Flächen von „Plan indexiert“ 2 mm höher im Freivorschub (P-2026-10-11-86; Nase 162,4 min, Zeilen 157,8, rundum 179,9).

**Die Nacht vom 2026-10-10 auf den 11.** (Manuel: „schau dir die Werkzeugwege nochmal genau an
und deren Generation … auch die Geschichte mit dem Mehrkern-Arbeiten bitte nochmal verbessern“),
an seinem zweiten 4-Achs-Testteil (`beispiele/testteil_4achs_nase.FCStd`, CLX550, seine Werkzeuge
aus RC1) und dem 3-Achs-Testteil, P-2026-10-10-55 bis P-2026-10-11-29 (0.213.8 → 0.213.37):
- **Bahnen:** Rundum schlichten und schruppen mit der Querachse fahren durchs Freie mit dem
  Freivorschub (-56, 11-04); die Meldung „Rest über der Bahn“ misst mit der Querachse dort, wo
  die Kugel steht (-58: 25,3 statt 47,6 mm). **In 3D nachgerechnet (11-27):** freie Läufe des
  Schlichtens schnitten vorne an der Platte Material (das Restmodell sieht die Ecken nicht, die
  das Schruppen dort stehen lässt) – jetzt schnell nur außerhalb der Stange; Schlichten T2 mit
  Querachse 193,6 → 187,5 min statt → 172,2. Prüfung mit Voxeln in `test_vierachs_frei`.
- **Alle Kerne:** Nebenrechner verteilen selbst weiter (Unteraufträge über den Pool der
  Oberfläche, 11-07) – die Vorschau im 4-Achs-Assistenten Schruppen 3,5 → 1,1–1,8 s,
  Schlichten 3,5 → 0,6–1,4 s; die Arbeiter starten und laden beim Öffnen des Assistenten (11-13),
  die Dokumentkopie wird nur nach einer Änderung neu gespeichert (11-08: 0,44 s weniger
  Stillstand je Eingabe); weitere Rechnungen auf den Nebenrechnern: Hüllfläche je Winkel, Rest
  nach dem Schruppen (11-09).
- **Schneller, Ergebnis gleich (bitgleich nachgeprüft):** Neuberechnen beider 4-Achs-Operationen
  22,7 → 5,8 s ohne Fenster, in der Oberfläche 9,5 → 6,2 s (-57, -62, 11-09); Kollision mit seinen
  Haltern 243 → 162 s (-59, -63, 11-10: jedes Dreieck einmal); Prüffenster 13–16 → 6,5 s (-60,
  11-01, 11-05, 11-11, 11-12, 11-26); 3-Achs-Räumen −13 s Rechenzeit (11-02); Programm
  speichern (Siemens, 236 000 Sätze) 3,4 → 2,3 s (11-28), seit P-2026-10-11-50 auf einem
  Nebenrechner: das Fenster steht höchstens 0,2 s.
- **Kein Lag im 3-Achs-Assistenten mehr (11-15, 11-16, 11-23 bis 11-25, 11-29):** Die Vorschau rechnet
  nach einer Eingabe Block für Block, dazwischen nimmt das Fenster Klicks an; Räumen, Planfräsen,
  Kontur, 3D-Schruppen, Restschruppen und 3D-Schlichten rechnen in Nebenrechnern. Am Testteil stand das Fenster 4,0 und 10,4 s
  am Stück, jetzt höchstens 0,8 s (im Fenster 2,2 statt 12,3 s gerechnet).
- **Offen für Manuel:** Fragen 5–9 in `OFFENE_FRAGEN.md` (ebene Flächen mit dem Schaftfräser,
  Schrittweite des Schafts, der Halter stößt ans Teil, Rest vor dem Schlichten, C dreht zurück).
- **Nicht geschafft:** ~~das Prüffenster im Hintergrund~~ (P-2026-10-11-41: im Takt, höchstens 0,5 s am Stück), Hebel 3 (Varianten
  des 5-Achs-Vergleichs parallel); im 3-Achs-Assistenten rechnen nur noch die kleinen Strategien
  im Fenster (je unter 1 s) – Flanke, Restschlichten und 3D-Schlichten mit Wegkippen seit
  P-2026-10-11-53 im Hintergrund.

**Die Nacht vom 2026-10-03 auf den 04.** (Manuel: „bau weiter, fang von mir aus mit
5-Achs-Strategien an … mach einfach weiter, bis ich guten Morgen sage“): 3+2 durchgängig
(P-2026-10-03-36 bis -57, 0.154.0 → 0.158.4) – Ebene aus Fläche, Bohrungswand oder Winkeln,
Knopf im Assistenten, Programm mit der gewählten Maschine (Siemens CYCLE800, sonst gerechnet),
Bohren am Schwenkkopf, Kollision und Abfahren mit Schwenken, Bestückung je Aufspannung;
Siemens-Bohrzyklen CYCLE81/83/85; der Kern für simultan (ohne TCPM, G93); „Auf der Maschine
prüfen“ öffnet schneller. Danach (P-2026-10-04-01 bis -19, → 0.165.2): Drehteil am Mantel (V2b),
Rundachsen-Gleichstand, Messstopp zum Wechselpunkt, Zeit für den Werkzeugwechsel, „Neue
Maschine …“ mit Wegen und Schwenkbereichen der 5-Achs-Fräsen (D-26), Spindelleistung und die
gemerkte Maschine im Planer (D-20), „Von unten gespannt“ mit Urteil und Schraubstock (S3h),
B-013 (3D-Schlichten hob an Höhenlinien ab), der Kern verdichtet ohne TCPM, die Vorschau merkt
sich je Block ihr Ergebnis, das Programm ohne doppelte Sätze, „Kollision prüfen“ mit Eilgängen
durchs Rohteil (Quader und Stange – Entscheidung 4c-7 ergänzt, zur Bestätigung) und „am
Anschlag“ im Befund; ein Versuch an der Kuppel für E-3 (Spezifikation 16.3), der Befund
„Räumen fährt 3,5 m ohne Material“ (W-013). Zu entscheiden: Spezifikation Strategien 15.4 (D-1, D-2, D-4, D-5)
und 16.4 (E-2, E-3). **Zum Ausprobieren (3+2):** `beispiele/schwenkteil_5achs.FCStd`,
„Beispielmaschine laden …“ → 5-Achs Tisch/Tisch; Oberseite anklicken → Bearbeitung → Job;
die 30°-Schräge anklicken → **Ebene schwenken (3+2) …** → grün „Face…: 30° geschwenkt →
A−30 C0“ → OK → der Assistent öffnet in der Ebene → Anlegen; Grundjob → **Programm schreiben**
(Siemens: zweimal `CYCLE800(1,"",0,27,…)`, am Ende `CYCLE800()`); **Auf der Maschine prüfen**
→ im Abspieler „… – Ebene A−30 C0“, der Tisch steht auf A−30. **Drehteil (V2b,
P-2026-10-04-01):** eine Welle, „4-Achs-Bearbeitung“, ihren **Mantel** nahe dem rechten Ende
anklicken → „Welle, Face… (rund Ø …, ihre Achse ist die Stangenachse)“, das rechte Ende vorne;
**Umdrehen** → das linke.

**Die Nacht vom 2026-10-02 auf den 03. ist abgearbeitet** (Manuel: „arbeite die Nacht durch …
so viel wie möglich umsetzen und automatisch pushen“): T4 „Schlichten danach“
(P-2026-10-02-90), die Werkzeugliste nach Katalog (-91, -92), T2 dünne Lagen breit (-93),
die Vorschau schneller (-94: am Testteil 24 → 17 s Rechnen; der Rest sind die Hüllflächen je
Block, `hoehenfeld.je_zeile`, 5,6 s in 68 Aufrufen), dieser Snapshot (P-2026-10-03-01). Um
22:25 hat Linux die Sitzung beendet – ein Prototyp außerhalb des Addons fraß 57 GB; seither
läuft jeder Rechenlauf mit Speicherdeckel (Regeln unten).

**T5d – Taschen, gelassen nach zwei Anläufen** (so stand es im Nachtplan): In der Tasche
40 × 30 halten die Ringe die Last nicht (0,88 min, bis 4,1 ae – nicht in den Taschenecken,
sondern an den scharfen Ecken der kleinen inneren Ringe), adaptiv hält sie (1,49 min).
Anlauf 1, Ringe vom Kern der Tasche nach außen mit geodätischem Abstand (achteckig):
1,44 min, Last 3,2 ae – hält nicht und ist nicht schneller. Anlauf 2, euklidischer Abstand
(Ringe wie ein Stadion), ist am Speicher gescheitert (Fehler im Prototyp). Taschen bleiben
adaptiv – das hält die Last und ist gebaut; der Ansatz steht in der [Spezifikation
Strategien](spezifikation_strategien.md), 13.5 T5d, falls es jemand wieder aufnimmt.

**Jetzt – Manuel testet.** Zuerst das Neue dieser Nacht am Testteil
(`beispiele/testteil_3achs_fraese.FCStd`; Klickwege: Hilfe „So geht’s“):

1. **Räumen adaptiv:** Teil öffnen, Oberseite anklicken → Bearbeitung → Schritt 2 alle
   Flächen anhaken → Schritt 3: beim Block „Räumen“ steht „→ 3 Flächen: … Lagen, adaptiv,
   etwa 10 min · rund 1,5 × Ziel“. Wo Ringe schneller wären, aber den Fräser überlasten, hängt
   „– Ringe wären 41 % schneller, überlasten den Fräser aber (bis 4,1 ae)“ dran (so an einer
   Tasche 40 × 30). Im Prüffenster: nirgends ins Teil, nichts stehen geblieben. Manuels
   Räumen (Stiche) gibt es auf Wahl: Eigenschaft „Variante“ der Operation auf „stiche“.
2. **Schlichten danach:** gleich unter „Räumen“ der Block „Schlichten danach“ mit Fräser,
   Einsatz „Schlichten“, Zustellung an den Wänden, Zeilenabstand am Boden und den Haken
   Boden, Wände, Messstopp davor → „→ … Wände (0,3 mm), etwa …“; mit „Aufmaß am Boden“ 0,5
   beim Räumen und dem Haken „Messstopp davor“: „→ Boden (0,5 mm) und … Wände (0,3 mm), etwa …
   – davor ein Messstopp“. „Anlegen“ → im Job hinter „Räumen T1“: „Messstopp“, „Boden
   schlichten T…“, „Wände schlichten T…“; im Prüffenster ist der Boden am Ende 0,00 mm.
3. **Werkzeugverwaltung (0.129.0):** Die Liste ist nach Art gegliedert („Bohrer (30)“,
   zuklappbar); in der Schnittwert-Tabelle steht je Zeile „M – rostfreier Stahl“ statt
   1.4301 (deine alten Zeilen wandern beim Öffnen von selbst zu den Klassen). Eine Gruppe
   anklicken → „Löschen“ fragt „30 Werkzeuge löschen?“ mit Liste. „Werkzeuge der Hersteller …“
   zeigt Art → Reihe → Größe mit Haken; „Alle abhaken“, dann bei Ceratizit eine Größe
   anhaken → „Hinzufügen“ legt nur die an. Ceratizit Ø 8,5: Artikel 1170308500, „Bestellen“
   öffnet die Produktseite, Nutzlänge 49, Gesamtlänge 103, Schaft 10, 140°. Beim Jongen Ø 12
   (0.131.0): „Hals-Ø d1 11,2“ und „Auskragung N 36“ wie im Katalogblatt, das Bild zeigt den
   Hals.
10. **Programm schreiben (0.136.0):** Job wählen → Werkzeugleiste „Programm schreiben …“
   (letzter Knopf). Oben steht, was der Postprozessor von deiner Drehmaschine weiß
   („Drehmaschine · X im Durchmesser · C heißt C… · angetrieben: T1…T12 → S…“), darunter die
   Steuerung (Siemens 840D wählen) und die Vorschau: „T1 D1“, „SPOS=0“, „M3=3 S3=…“ (Antrieb mit
   seiner Nummer), X doppelt (Durchmesser), „C4=…“. „Befehle …“ zeigt alle Befehle zum Ändern –
   bitte mit deiner Steuerung vergleichen (C-Achse ein/aus, Antrieb, Werkzeugwechsel) und mir
   sagen, was an deiner Maschine anders heißt. „Speichern“ schreibt die .mpf neben dein Dokument.
9. **Die Y-Achse an deinem 4-Achs-Teil (0.135.0):** im 4-Achs-Assistenten mit deiner
   Drehmaschine (mit Y), alle Mantelflächen: unter „Plan indexiert“ steht „Mit der Querachse
   geht Face4 eben in Zeilen … Face4 fällt längs um 8,5° …“, der Haken ist frei, aber nicht
   gesetzt. Setzen, Fräser mit ebener Stirn (Ø 12) → „Anlegen“: „Plan indexiert T…“ fräst die
   flache Seite in geraden Zeilen längs, C steht, Y rückt quer – hinten unter der Drehmitte (X
   unter null); „Rundum schlichten“ lässt Face4 aus. Gerechnet: Plan 9 min + Schlichten 52 min
   statt 88 min Spirale; die flache Seite eben bis 0,01 mm.
8. **Hinten am 4-Achs-Teil (0.134.0):** hinter dem Teil fährt der Fräser das Profil des
   Teilendes 3,5 mm gerade weiter (Abstechbreite 3 + 0,5) und hört dort auf – das Stechschwert
   trifft auf ein gerades Stück, dahinter bleibt das Material. Im Assistenten steht beim
   Überlauf grau „Abstechbreite + 0,5“, die Stange muss 2 mm weniger herausragen.
7. **Dein 4-Achs-Teil (0.133.0):** Job neu anlegen (Rundum schruppen Kugel Ø 10, ap 5,
   5 mm/U, Aufmaß 0,3; Rundum schlichten 0,2) → Prüffenster: der Kern an der Drehmitte und die
   Wulst auf der Fläche sind weg, das Schlichten beginnt vorne, Zeit rechnerisch etwa 2 h statt
   2 h 40 (Schruppen 9 Lagen, 31 min; Schlichten 90 min – die 0,2 mm Schrittweite ist der
   Löwenanteil: 0,5 mm wären 6 µm Kammhöhe und 36 min). Was du im Prüffenster noch siehst,
   stimmt nicht ganz: Fahrten über die Mitte malt es nicht (die Spitze zählt dort als 0).
6. **4-Achs-Assistent und Prüffenster (0.132.0):** In Schritt 1 steht unten rechts „Weiter“,
   in Schritt 2 neben „Zurück“ rechts „Anlegen“ (beim Ändern „Übernehmen“) – wie oben. Im
   Prüffenster unter „Schnittwerte“ die Zeile **Zeit**: „rechnerisch 2 h 40 min – Vorschub …,
   Eilgang … · „Rundum schruppen T1“ … · …“ (an deiner Drehmaschine mit dem 4-Achs-Testteil).
4. **Dünne Lage:** am Testteil ist die obere Stufe (1 mm) im Prüffenster plan und ohne Rest;
   im Räumen fährt diese Lage mit ae = Fräserradius (Hilfe „Bearbeitung“, „Dünne Lagen breit“).
5. **Das Teil muss herauskommen (0.130.0):** in Schritt 3 beim Räumen „Aufmaß am Boden“ 0,5
   eintragen, „Schlichten danach“ abgehakt lassen → unter den Schritten rot: „Ohne genaue Bahn
   am Ende – das Teil wäre dort nicht, wie gezeichnet: Face…. Dafür anhaken: „Planfräsen“,
   „Schlichten danach“.“ Haken bei „Schlichten danach“ → die Zeile ist weg. Ebenso, wenn du
   die Kontur abhakst, solange eine Wand gewählt ist.

**Offen für Manuel (2026-10-04, abends):**

- *S5 Entgraten in 3D:* beantwortet – bauen, mit jedem Fräser mit ebener Stirn und auch mit 3
  Achsen (P-2026-10-04-65).
- *Siemens WORKPIECE:* Manuel (2026-10-04): „lass es raus“; am 2026-10-05: „WORKPIECE muss doch mit rein!“ – gebaut (P-2026-10-05-13), an einer echten Steuerung nicht geprüft.
- *Zum Ausprobieren (0.192.5) – Siemens, Alarm 16830:* den Job mit „Rundum schruppen/schlichten“
  wählen → „Programm schreiben …“ → Siemens 840D → rechts in den Sätzen steht die Rundachse jetzt
  als „C4=ACN(270.000)“ bzw. „ACP(…)“, nie mehr negativ oder über 360. Links unter „Rundachse“ die
  beiden Befehle (leer: fortlaufend wie vorher). An der Maschine das Programm zuerst in der
  Simulation laufen lassen. Dazu: Stange Ø 40 für ein Teil Ø 40 heißt jetzt „Passt“. Seit 0.192.6
  fahren Rundum schruppen und schlichten dort, wo die Stange schon das Maß hat (die Scheibe Ø 40 in
  der Stange Ø 40), mit dem Freivorschub statt im Schnittvorschub durch die Luft.
- *Zum Ausprobieren (0.192.1) – Wege zwischen den Fenstern:* ein Teil mit zwei Jobs (zwei
  Aufspannungen): im zweiten etwas anlegen, dann ohne den Job anzuklicken „Auf der Maschine
  prüfen“ → es zeigt den zweiten Job (bisher immer den ersten). Unter „Zeit“ der Knopf
  „Programm schreiben …“ → das Programm desselben Jobs. Einmal woandershin speichern (etwa auf
  die Freigabe der Maschine) → „Ordner öffnen“ zeigt den Ordner; beim nächsten Mal steht die Datei
  wieder dort, für andere Jobs auf derselben Maschine derselbe Ordner.
- *Zum Ausprobieren (0.191.0) – Magazine:* Werkzeugverwaltung → „Magazine …“ → „Neu“ für
  deine Fräse (sie muss unter „Maschinen …“ stehen) → „Aus den Nummern“, ein paar Nummern so
  ändern, wie sie an der Steuerung heißen, einem „Beladen auf“ geben → OK. Dann ein Teil →
  „Bearbeitung“ mit dieser Fräse → Schritt 3: In „Fräser“ stehen die des Magazins vorn („T5 · P3
  …“), die anderen darunter mit „nicht im Magazin“. Eins von unten wählen: gelber Satz und „Ins
  Magazin übernehmen“ → geklickt: der Satz ist weg. „Anlegen“: Die Controller heißen „T<Nummer
  aus dem Magazin> …“.
  Seit 0.192.0: In der Werkzeugverwaltung die Nummer eines Werkzeugs im Magazin ändern → den Job
  wählen → „Bestückung“ → unten die Rüstliste, rot „im Magazin T…“ → „Nummern aus dem Magazin“ →
  die Controller heißen danach so; „Programm schreiben“: im Kopf hinter jedem Werkzeug „beladen
  auf P…“ bzw. „nicht beladen – einsetzen“.
- *Zum Ausprobieren (0.189.1) – Heidenhain:* einen Job wählen → „Programm schreiben …“ →
  Steuerung „Heidenhain iTNC 530 (Klartext)“ → rechts „0 BEGIN PGM <Datei> MM“, „BLK FORM …“,
  „TOOL CALL 1 Z S…“, „M3“, „L X+… R0 F…“, Kreise „CC …“/„C … DR+“ → „Speichern“ → darunter
  „Nachgelesen … nichts gefunden“. Die .h-Datei an der TNC im Programmtest laufen lassen, bevor
  die Maschine fährt (die Länge kommt dort mit TOOL CALL aus der Werkzeugtabelle).
- *Zum Ausprobieren (0.188.8, Kanten seit 0.189.1) – Entgraten 3D:*
  `beispiele/testteil_3achs_fraese.FCStd` öffnen, die Flächen anklicken, deren Kanten eine Fase
  bekommen sollen – oder einzelne Kanten (grün in der Liste und im Bild) → „Bearbeitung“ → Schritt 2:
  „Entgraten 3D“ anhaken (steht nie von selbst), den Fasenfräser wählen → unten „→ … Kanten mit
  Fase, etwa … min“ und was ohne Fase bleibt, mit Grund – „zu steil für den senkrechten Kegel“
  (senkrechte Kanten), „der Halter stieße an – mit 15 mm Auskragung ginge es“ (so beim
  vorgeschlagenen Halter; mit deinem eigenen in der Werkzeugverwaltung rechnet es damit) →
  „Anlegen“ → „Kollision prüfen“: nichts rot. Die Fase läuft bis in die Ecken und rund um den
  Rand der Kugelmulde (außer, wo die Insel daneben steht). Mit der 5-Achs-Beispielmaschine
  (Schwenkteil): „Angestellt (5 Achsen)“ ist da und angehakt, dicht über dem Tisch kippt der
  Kegel nach oben; was trotzdem nicht geht, heißt „zu nah am Tisch (das Teil höher spannen)“.
- *Zum Ausprobieren (0.187.7):* an deiner Siemens ein Programm schreiben und in ihrer Simulation
  ansehen – neu seit 0.185.1: G43 bzw. D1 nach dem Wechselpunkt, DIAMON im Kopf an der
  Drehmaschine, „Nachgelesen …“ unter „Gespeichert“; TCPM bleibt aus.

**Fragen an Manuel** (gebaut ist je die Empfehlung; ändern ist ein kleiner Patch). Beantwortet
am 2026-10-03: hinten ein gerades Stück der Abstechlänge (gebaut, 0.134.0); W-005 nach den
Empfehlungen der Spezifikation (wird gebaut); Zeilenabstand am Boden bleibt der halbe Ø; der Standardfräser bleibt bei vc 85 /
fz 0,1 / ae 1,5 / ap 25; Ceratizit ist CoreLine WPC UNI (eingetragen), Ø 2 und 2,5 bleiben
weg; die Kiste bleibt nach Werkzeugart mit ein paar realen Werkzeugen je Art – die Hersteller
sind nur die Quelle, keine Erweiterung nötig; „das Teil muss herauskommen“ ist Grundsatz 0.

Beantwortet am 2026-10-03 (abends):

- *Zwei Fräser an einer Wand:* Ist der Absatz, wo Kontur (Ø 12) und Restmaterial (Ø 6) sich
  treffen, im Bereich 0,0005 mm, bleibt es so; ist er mehr, bekommt jede Kontur ihren eigenen
  Fräser. **Gemessen (P-2026-10-03-20):** 0,0000 mm am Übergang, nirgends mehr als nötig – es
  bleibt so (Spezifikation Strategien, T3).
- *Materialstand:* über kurze Lücken fahren, nicht abheben (so gebaut). Idee von Manuel: über
  der Lücke schneller fahren – nur, wenn es trotz Bremsen und Beschleunigen Zeit bringt.
- *TCPM:* bleibt aus. Es soll auf **allen** Maschinen gehen; die G-Sätze ohne TCPM geben
  dasselbe Teil (die Achsstellungen rechnet das Addon). Was eine Maschine kann, stellt man im
  Postprozessor ein (TCPM später als Haken, W-005).
- *Siemens-Befehle:* Manuel programmiert an der Maschine mit ShopTurn, G-Code selten – er kann
  sie nicht prüfen. Die Befehle bleiben nach dem Siemens-Handbuch; vor dem ersten Lauf das
  Programm in der Simulation der Steuerung ansehen (gehört in die Hilfe „Programm schreiben“).
  Kein ShopTurn-Ausgang.
- *Neue Achse (D-14):* graue Standardwerte für Eilgang und Drehzahl (wie beim Werkzeug). Die
  Hilfe „Wie finde ich die Beschleunigung heraus?“ ausbauen: je Steuerung (Siemens, Heidenhain,
  Fanuc, Haas, LinuxCNC), wo Eilgang, Drehzahl und Beschleunigung in den Maschinendaten stehen
  und wie man hinkommt (Zugriffsstufe, Schlüsselzahl – z. B. Heidenhain MOD).
- *Kollision (D-22):* bleibt auf Klick – sonst startet das Abfahren noch träger; das ist bei
  großen Bahnen heute schon langsam (gehört zu „Vorschau beschleunigen“).
- *Halter vorschlagen (D-23):* ja – nach Schaft-Ø ER16/ER25/ER32/ER40, herausstehen
  Auskragung N + 5 mm. Gebaut (0.139.0).
- *An CAM übergeben (D-27):* ja – „OK“ und „Übernehmen“ übergeben mit, sobald einmal
  übergeben wurde. Gebaut (0.139.0).
- *Gewindebohrer:* Gühring 8330 in der Kiste (P-2026-10-03-21, M2–M16 mit Bestell-Nr. und Maßen
  aus dem Gühring-Katalog; der Shop sperrte den Abruf hier mit 403). Gühring 5596 bleibt, wie
  er ist – M2, M2,5 und ab M12 ohne belegte Nummer (Manuel: „effektiv ist's nicht wichtig …
  hauptsache Beispiele mit echten Daten vom Hersteller und ein Link zum Nachlesen“). Jongen
  Ø 3 entfällt.

**Danach, der Reihe nach:**

1. Was Manuels Test ergibt.
2. **W-005 weiter:** die Steuerung an der Maschine („Maschine bearbeiten“, S2) – nach Manuels
   Blick auf die Befehle seiner Steuerung; S4 (Glätten) und S5 (ohne G93) sind gebaut
   (P-2026-10-03-27).
3. ~~Die Vorschau weiter beschleunigen~~ – P-2026-10-03-28: am Testteil (alle Flächen) erster
   Lauf 10,4 s statt 13,7, jeder weitere 4,7 statt 9,3 (Zwischenspeicher für die Hüllflächen
   `hoehenfeld.je_zeile` und die Wände `kontur_bahn.waende`, die Flächen je Strategie einmal je
   Lauf). Bandweise rechnen wie `je_stellung` war hier langsamer (0,15 statt 0,11 s), gelassen.
   Was bleibt: das Räumen (3,9 s, viermal je Lauf), 3D-Schruppen, Planfräsen, Kontur je ~1,3 s.
   P-2026-10-04-03: Die Höhen der Wände (B-010, `_wandkanten`) kosteten seit P-34 1,6 s je
   Lauf – jetzt je Wand gemerkt: warm 5,9 → 4,2 s am Testteil (alle Flächen). P-2026-10-04-14:
   Jeder Block merkt seine Vorschau über die Läufe (Schlüssel: Strategie, Flächen, Werkzeug,
   Einsatz, Werte, Materialstand, Teil und Rohteil) – ein zweiter Lauf ohne Änderung 4,2 → 0,4 s;
   ändert sich ein Feld, rechnet nur, was davon abhängt.
4. ~~Planfräsen Zelle für Zelle~~ – P-2026-10-03-29: Zapfen 5,70 → 4,05 min (13 statt 54
   Rampen), Platte 41,88 → 35,20 min, nirgends in voller Breite (Spezifikation Strategien,
   Abschnitt 11). Der Konturgang um Inseln war dafür nicht nötig.
5. Der Einstieg (Rampe, Helix, senkrecht) nach Zeit; Startstelle und Reihenfolge der
   Bereiche. *Nachgemessen (2026-10-04 nachts):* Planfräsen um den Zapfen (50 × 50, 10 mm über
   der Fläche): 6 Bereiche, jeder mit einer Rampe von 193 mm – 1,3 von 4,8 min; sie beginnen am
   Rand des Rohteils, wo der Fräser nur 4 mm im Material steht (senkrecht daneben hinab und
   seitlich hinein spart fast alles davon). **Gebaut P-2026-10-04-34** (Manuel: „lass sie weg
   … unnötige Bewegungen und Luft fräsen … kannst du auch ohne mich einfach wegbügeln“): am
   Zapfen 4,05 → 3,29 min, keine Rampe mehr.
   Spannhöhe: „Von unten gespannt“ gebaut (P-2026-10-04-10, Prüfung und Urteil; -11 der
   Schraubstock im Bild und in der Kollision).
6. Die Bahnrechnung weiter beschleunigen (Rest über Stücke, mit neuen goldenen Bahnen).
   **Kollision schneller** (gemessen 2026-10-04 nachts, Schwenkteil, 10 799 Stationen): 75 s,
   davon 59 s in OpenCascades `distToShape` (22 389 Aufrufe, 2,6 ms), 15 s Python um die
   Hüllquader (`_stelle.lage`, `_luecke`). Je Paar: **44 s „Kern gegen Teil“** (ins fertige
   Teil, im Vorschub fast an jeder Stelle: 20 771 Aufrufe, 2,1 ms), 14 s Werkzeug gegen
   „Rundtisch“ (790 Aufrufe, 17 ms je Aufruf), der Rest unter 1 s. **Nachgemessen: Je Fläche
   vorfiltern bringt nichts** (am Schwenkteil 2,4 statt 2,1 ms je Abstand – OpenCascade filtert
   selbst); „steckt ganz drin“ (`isInside`) kostet 0,3 ms; eine gröbere Toleranz für
   `distToShape` (1e-3 statt 1e-7) ändert nichts (2026-10-04 nachgemessen). Was bliebe: weniger Abstände rechnen
   (bessere Schranken), nicht billigere. Frühere Idee: je Fläche des Teils
   vorfiltern (Hüllquader,
   näher zuerst, exakt mit Abbruch) – dann aber eigens prüfen, ob ein Werkzeugteil ganz im Teil
   steckt (das sagt `distToShape` zwischen Körpern heute mit 0). Nur mit einem Vergleich aller
   Befunde vorher/nachher; nicht nachts gebaut. „Auf der Maschine prüfen“ öffnet seit
   P-2026-10-03-54 schneller (12 000 Punkte: 1,8 → 1,3 s). An einem großen 4-Achs-Job (Welle Ø 60 × 100,
   Rundum schlichten 0,2 mm: 263 679 Stationen, rechnerisch 3,4 h) öffnet es in etwa 10 s: Prüfen
   1,8, Abfahren 3,9, die Spitze am Werkstück je Station 4 s (Kinematik je Station; seit
   P-2026-10-04-20 einmal gerechnet und gemerkt – die Kollision rechnet sie nicht noch einmal).
7a. W-003 (erledigt mit P-2026-10-12-150): „Rundum schruppen“ fuhr am Nasen-Testteil im Vorschub durch
   Luft, wo die Lagen davor schon alles genommen hatten (mit der Querachse 5,3 von 16,6 m). Jetzt
   führt es den Rest Lage für Lage mit (restmaterial.Stange) und fährt dort im Freivorschub: mit
   der Querachse 14,8 → 12,1 min, ohne 11,2 → 10,5 min; in freien Stücken im Würfelmodell höchstens
   1,4 mm³ (Ränder). Der erste, einfache Weg (frei, wo schon die Lage davor auf der Hüllfläche
   stand) war falsch – die Lagen fahren gegeneinander versetzt. „Plan indexiert zuerst“ spart dem
   Schruppen an der Nase nur etwa 1 min (geschätzt).
7. W-003 (erledigt mit P-2026-10-12-149): Mit der Querachse und gleich tiefen Lagen blieb an einer
   einfachen Welle seitlich ein dünner Rest für eine sechste Lage; jetzt gleich tief so, dass die
   geplanten Lagen reichen (nie tiefer als ap).
   (Erledigt mit P-2026-10-12-148: `vierachs_huelle.je_stellung_stueck` 37 statt 2182 MB je Auftrag,
   Schruppen am Geist 205 statt 666–727 s.)
7. W-002 F2; W-003 V6, V7 (V2b gebaut, P-2026-10-04-01); (das Schruppen rundum an steilen Stellen: gemessen, die Keile
   sind größtenteils echt – P-2026-10-03-30);
   ~~„ausweichen“ mit
   dem Y (Kugel nicht mit der Spitze, Anstellwinkel quer – Spezifikation Vierachs V4c+)~~ –
   P-2026-10-04-50: „Kugel 15° anstellen“ beim Rundum-Schlichten mit der Querachse, angehakt.

**Regeln dafür** (Manuel, 2026-10-02: „du hast zwei stunden damit verbracht sachen zu testen
für was?“; 2026-10-03: „ob das nötig ist oder nicht, musst dennoch du entscheiden … wenn es nötig
ist, etwas zu testen, dann sollte das nicht verboten werden“): so viel prüfen wie nötig, kein
Verbot – die Regel ist die eine Prüfdatei und das eine Szenario zum geänderten Teil, kein Lauf
über alles, nichts im Hintergrund; jeder weitere Lauf beantwortet eine Frage, die Claude hat. Pushen, sobald sie grün sind (Manuel,
2026-10-02 nachts: „so viel wie möglich umsetzen und automatisch pushen“), mit höherer Version
in `package.xml`, wenn er es ausprobieren soll; danach bei GitHub nachsehen. Braucht ein Punkt
seine Entscheidung: die Frage mit Auswahl oben aufschreiben und mit dem nächsten weitermachen.
FreeCADs Adaptiv-Kern rechnet bei gleicher Eingabe nicht immer dieselbe Bahn (±1,5 % Zeit) –
Vergleiche in Prüfungen mit Spielraum. Jeder Rechenlauf und jedes Szenario mit Speicherdeckel:
`systemd-run --user --scope -q -p MemoryMax=16G -p MemorySwapMax=0 …` (ein Lauf am Testteil
braucht 222 MB; wächst einer aus dem Ruder, stirbt nur er, nicht die Sitzung). Am Ende jedes
Laufs ein kurzer Bericht: was Manuel klicken soll und was er dann sehen muss.

## Wunschliste

Ein Satz je Wunsch, W-ID fortlaufend; was davon gebaut ist, steht im Projektstatus.

- **W-001 Maschine aus Baugruppe** – die Maschine als grobes 3D-Modell in einer Assembly
  aufbauen, Gelenke als Achsen mit Kenndaten, daraus FreeCADs Maschinendefinition; Grundlage
  für Prüfen, Abfahren und Kollision:
  [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md),
  [spezifikation_simulation.md](spezifikation_simulation.md).
- **W-002 Werkzeugverwaltung** – Werkstoffe, Werkzeuge mit Schnittwerten je Werkstoff und
  Einsatz, Strategien vergleichen, Halter, Bestückung:
  [spezifikation_werkzeugverwaltung.md](spezifikation_werkzeugverwaltung.md),
  [spezifikation_werkzeugarten.md](spezifikation_werkzeugarten.md),
  [spezifikation_halter.md](spezifikation_halter.md).
- **W-003 4-Achs-Bearbeitung am runden Rohteil** – ein Teil vorne mittig in eine Stange
  legen, Flächen anklicken, Schrupp- und Schlichtbahnen für A, B oder C, auch auf der
  Drehmaschine mit C und Y: [spezifikation_vierachs.md](spezifikation_vierachs.md).
- **W-004 Bedienung vereinfachen und automatisieren** – Durchsicht aller Fenster und Abläufe
  (Manuel, 2026-09-27): [durchsicht_bedienbarkeit.md](durchsicht_bedienbarkeit.md).
- **W-005 Programm für jede Steuerung** – die Steuerung einmal an der Maschine wählen, ein
  Postprozessor des Addons schreibt das Programm, auch an der Drehmaschine (Manuel,
  2026-09-30: „A sollte unsere option sein“): [spezifikation_steuerung.md](spezifikation_steuerung.md).
- **W-006 Frässtrategien** – bessere Strategien als FreeCADs, einfach und gut erklärt; die
  Zeit entscheidet, nie in voller Breite, die Last im Rahmen (Manuel, 2026-09-30 und
  2026-10-01): [spezifikation_strategien.md](spezifikation_strategien.md).
- **W-007 Werkzeugkiste vorgefüllt** – Manuels Werkzeuge mit Artikelnummer, Bestell-Link,
  Katalog und Schnittwerten je Werkstoff, fehlende geschätzt (Manuel, 2026-10-02):
  [spezifikation_werkzeugverwaltung.md](spezifikation_werkzeugverwaltung.md), Abschnitte 13
  und 14.
- **W-008 Home- und Werkzeugwechselpunkt** an der Maschine (Manuel, 2026-10-02):
  [spezifikation_simulation.md](spezifikation_simulation.md), Abschnitt 13.
- **W-009 Assistent „Bearbeitung“ in Schritten** – Aufspannung, Was soll weg, Einstellungen
  (Manuel, 2026-10-02): [spezifikation_strategien.md](spezifikation_strategien.md), 12.5
  und 12.6.
- **W-010 Schlichten nach dem Räumen mit Messstopp** (Manuel, 2026-10-02):
  [spezifikation_strategien.md](spezifikation_strategien.md), 12.4 – gebaut als Block
  „Schlichten danach“.
- **W-011 Maschinen-Speicher und Maschinenzuweisung** – die Maschine ist die erste Frage beim
  Teil, Rohteil auch aus einem konstruierten Teil (Manuel, 2026-10-02):
  [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md),
  Abschnitt 12.
- **W-012 Materialstand** – jede Schrupp-Operation beginnt, wo noch Material steht; die
  geschlossene Nut taucht an einer wählbaren Stelle ein (Manuel, 2026-10-02):
  [spezifikation_strategien.md](spezifikation_strategien.md), 12.7 und 12.8.
- **W-013 Testteil für die 3-Achs-Fräse** – Manuels Teil mit Platte, Insel, Stufe, Tasche und
  Kugelmulde (`beispiele/testteil_3achs_fraese.FCStd`) bearbeitet der Assistent sinnvoll und
  in mehreren Arbeitsschritten (Manuel, 2026-10-02):
  [spezifikation_strategien.md](spezifikation_strategien.md), Abschnitt 13.
- **W-014 5 Achsen, 3+2** – eine schräge Ebene schwenken und darin wie an einer 3-Achs-Maschine
  fräsen; ein Programm je Aufspannung (Manuel, 2026-10-03: „fang von mir aus mit 5-Achs-Strategien
  an“): [spezifikation_strategien.md](spezifikation_strategien.md), Abschnitt 15.
- **W-015 5 Achsen simultan** – die Werkzeugachse entlang der Bahn (Kugel angestellt, Flanke,
  Wegkippen), Entwurf zum Besprechen: [spezifikation_strategien.md](spezifikation_strategien.md),
  Abschnitt 16.
- **W-016 Eckige Teile auf der Drehmaschine fräsen** – ein Quader im Futter (Drei-, Vierbacken),
  gefräst an der Stirnseite (Y, so weit es reicht, dann C) und an den Seiten (C stellt, Y quer);
  der Assistent „Bearbeitung“ weist die Drehmaschine heute ab (Manuel, 2026-10-06: „nur
  dokumentieren und vielleicht schon ein paar Ideen aufschreiben“ – noch nicht bauen):
  [spezifikation_drehmaschine_quader.md](spezifikation_drehmaschine_quader.md).
- **W-017 STL als Teil** – ein STL aus einem Rundstahl fräsen, soweit es geht, auf 4 und später 5
  Achsen (Manuel, 2026-10-11; sein Geist `beispiele/geist_stl/`, CC0). Gebaut P-2026-10-11-100 bis
  -103: Netz anklicken → „4-Achs-Bearbeitung“ oder „Bearbeitung“ → Maßstab → Körper aus genau den
  Dreiecken (Nebenrechner); 4 Achsen: Standfläche ans Futter oder Achse X/Y/Z, Rundum schruppen und
  schlichten, „Auf der Maschine prüfen“ (Kollision über den nahen Ausschnitt); „Bearbeitung“:
  „Alles aus dieser Aufspannung“ wählt die Freiform-Dreiecke je Richtung, 3D-Schruppen und
  3D-Schlichten, an der 5-Achs-Fräse die Kette der geschwenkten Ebenen. Schneller in der Nacht
  zum 2026-10-12 (P-104 bis -112): Rundum schruppen mit Querachse am Geist „Anlegen“ 362 → 127 s
  (Bahn gleich), „Auf der Maschine prüfen“ mit radialem Halter 14 s ohne Befunde; wo ein
  Maschinenteil dem STL-Teil nahe kommt (T1 axial gespannt), 28,7 s statt über 60 min. Die Datei
  hat das Teil nur einmal, die Klone der Jobs holen es beim Öffnen von dort (P-2026-10-12-154,
  Haken in den Einstellungen, vorbelegt an: am Geist mit einem Job Speichern 3,6 statt 6,2 s).
  Körper und Klon zeigt das Addon als Netz (P-2026-10-12-156): am Geist Umwandeln ohne die 2,3 s,
  der erste Klick 0,8 statt 1,9 s; im Baum stehen sie grau. Mit P-157/-158 (Prüffenster aus dem
  Netz, CAMs Tiefen ohne Modell) steht das Fenster im ganzen 4-Achs-Ablauf höchstens 1 s. Bereiche wählen braucht es nicht (Manuel: ein STL immer rundum) –
  [spezifikation_vierachs.md](spezifikation_vierachs.md), Abschnitt 16.
- **W-018 STL aus der N-Eck-Stange im Schraubstock** – Manuels Wunsch vom 2026-10-12: an der
  3-Achs-Fräse eine gerade N-Eck-Stange waagerecht längs X oder Y, ein Ende 20 mm im Schraubstock,
  je Aufspannung um 360°/N weitergedreht, von oben 3D-Schruppen und -Schlichten mit Restmaterial;
  als Kette wie die 5-Achs-Ebenen. Gebaut P-2026-10-12-120 (Kern) und -122 (Assistent
  „Bearbeitung“, Fenster „STL als Teil“); Bild mit Zahlen `docs/bilder/w018_neck_geist.png`.
  Schruppen in der Stange in Zeilen von der Stirn zum Schraubstock, je Lage einmal abheben
  (P-2026-10-12-124; Geist Aufspannung 1: 3 Lagen, 93 Zeilen, ~11 min statt 227 Ringe, ~48 min;
  `docs/bilder/w018_neck_zeilen.png`). Die Backen des Schraubstocks am Ende der Stange in Bild,
  Kollision und Urteil „Spannung“ (P-2026-10-12-126).
  Das Einrichtblatt kommt als allgemeines Feature (W-019) –
  [spezifikation_vierachs.md](spezifikation_vierachs.md), Abschnitt 17.
- **W-019 Einrichtblatt für jede Bearbeitung** – Manuel, 2026-10-12: „eine einrichtblatt zum
  drucken/als pdf … wo drinnen steht 1. fräser und deren ausspannlängen zum halter 2. der halter
  mit abmessungen 3. das spannwerkzeug 4. das rohteil 5. der nullpunkt 6. die einzelnen
  arbeitsschritte“, „generell soll das einrichtblatt für JEDE bearbeitung generiert werden
  können !!!!“ (3 Achsen, 4 Achsen, 3+2, N-Eck-Kette).
  *Erledigt:* P-2026-10-16-20, Menü „CAM-Addon → Einrichtblatt …“ (`einrichtblatt.py`,
  `gui_einrichtblatt.py`): Werkzeuge mit Ausspannlänge, Länge ab Spindelnase und Halter (Ø,
  Länge, Spanntiefe; „(geschätzt)“ ohne eingetragene Länge), je Aufspannung Rohteil, Spannmittel,
  Nullpunkt, ein Bild und die Schritte mit S, F, ap, ae und Zeit; 3+2-Ebenen als Zwischenzeilen in
  der Aufspannung des Grundjobs, jede N-Kant-Aufspannung ein eigener Abschnitt. Als PDF, Drucken,
  HTML. Je Werkzeug mit Halter ein Bild von Halter und Fräser mit der Ausspannlänge
  (P-2026-10-16-22, das Bild der Halterverwaltung). Je Aufspannung ein eigenes Bild mit den
  Backen, die anderen Jobs ausgeblendet (P-2026-10-16-24), je geschwenkte Ebene eins an ihrer
  Zwischenzeile (P-2026-10-16-34). Das Fenster geht sofort auf, die Bilder kommen nach und nach
  (P-2026-10-16-36).
- **W-020 Spannmittel, die am Rohteil anliegen** – Manuel, 2026-10-12: „spannwerkzeuge will ich
  auch noch machen .. aber auch so das sie sich bewegen können und somit immer an das rohteil auch
  wirklich anliegen ... also ein schraubstock der dann mit seinen backen auch wirklich am rohteil
  neck anliegt“.
- **W-021 Runde Rohteile auf der Fräsmaschine (Dreibackenfutter)** – Manuel, 2026-10-12, zu seinem
  Ring-Teil: „ich kann auch auf der fräsmaschine ein dreibacken futter einspannen und somit runde
  rohteile haben .. nur als info .. das sollte unbedingt mit rein“. Im Assistenten „Bearbeitung“
  (3 Achsen) als Rohteil ein Zylinder (Durchmesser, Länge, Aufmaß), als Spannmittel ein
  Dreibackenfutter auf dem Tisch (Backen am Rohteil, wie W-020) – mit Bild, Kollision und
  Einrichtblatt (W-019). Hintergrund: Er hatte nur die CLX550 als Maschine, daher sagte der
  Assistent „Stange → 4-Achs-Assistent“ („achso ich hab keine 3ach maschine drinnen alles gut“).
  Noch einmal am 2026-10-16, mit Bild (Ring im Assistenten „Bearbeitung“ auf der 3-Achs-Fräse;
  angeboten wird nur ein Quader): „wie gesagt es gibt auch runde rohteile auf der fräse“ – erst
  das Laufende fertig machen, dann dies.
  *Stufe 1 erledigt:* P-2026-10-16-17, „Zylinder mit Aufmaß“ in Schritt 1. Der Rohling steht um
  das Teil (kleinster Kreis um den Umriss von oben); „seitlich“ ist das Aufmaß am Umfang. Die
  Strategien räumen über den Materialstand nur, wo Rohteil ist, nicht in den Ecken des Kastens.
  Offen: das Dreibackenfutter als Spannmittel (Backen am Rohling, wie W-020; statt der
  Schraubstockbacken bei „von unten gespannt“), Kollision und Einrichtblatt.
  *Stufe 2 erledigt:* P-2026-10-16-18. Mit „von unten gespannt“ sitzen am runden Rohling drei
  Backen (je 120°) im Bild und in der Kollision. Die Prüfung misst am Kreis statt am Kasten und
  sagt „Dreibackenfutter“.
  *Stufe 3 erledigt:* P-2026-10-16-23. Unter dem Rohling steht das Futter: das kleinste übliche
  (Ø 80 … 315), über das die Backen nicht hinausragen; am C-Ring Ø 125 × 66. Es steht im Bild
  und in der Kollision, und der Nullpunkt-Vorschlag hebt das Teil um seine Höhe (C-Ring: Z 69).
  Das Einrichtblatt nennt „Dreibackenfutter Ø 125 (hebt das Teil um 66 mm), … von unten
  gespannt“. Damit ist W-021 fertig, bis Manuel etwas anderes sieht; offen ist nur noch, ob
  die Futtergröße wählbar sein soll.
- **W-022 Die Werkzeugaufnahme gehört in die Maschine; Halter in ihrer Größe** – Manuel, 2026-10-16,
  mit Bild (Menü „Neu“ im Fenster „Halter“, alle Vorlagen „· SK40“): „warum nur sk40 ?? es gibt auch
  sk64 glaub ich ?? ich denke die aufnahme an der maschine ... sollten wir in die maschine packen !
  … die halter haben dann eine andere größe vll kannst du ja ein paar standarthalter größen
  raussuchen und nachbauen .. und dann je nachdem was in der maschine dann eingestellt ist darstellen
  ... natürlich muss man vorher die vollständigkeit der aufnahmen herstllen also nicht nur sk40 ..
  auch die anderen .. capto“. Heute haben alle Vorlagen in `halter._VORLAGEN` SK40-Maße (Flansch
  Ø 63 × 16). Nur die VDI-Vorlagen wachsen schon mit der Größe der Maschine
  (`maschine.vdi_groesse`). So soll es für alle Aufnahmen gehen:
  1. Die Aufnahme an der Spindel wird ein Feld der Maschine (Dialog „Neue Maschine“ und die
     Eigenschaften der Werkzeugaufnahme).
  2. Vollständige Liste, mit Norm und Größen aus Herstellerkatalogen:
     - SK30/40/50 (DIN 69871, ISO 7388-1);
     - BT30/40/50 (MAS 403, JIS B 6339);
     - CAT40/50;
     - HSK-A/E/F 32 … 100 (DIN 69893, ISO 12164);
     - Capto C3 … C8 (ISO 26623);
     - KM;
     - VDI 20 … 60 (DIN 69880, ISO 10889) und BMT an der Drehmaschine.
     „SK64“ gibt es wohl nicht, gemeint ist vermutlich HSK63 (oder SK50). In der Liste nennen,
     nicht nachfragen.
  3. Die Vorlagen je Aufnahme mit typischen Maßen nachbauen: Flansch, Kegel, Länge bis zur
     Spannzange.
  4. Das Menü „Neu“ zeigt die Vorlagen für die Aufnahme der Maschine, wie heute bei VDI.
  Offen: Was wird aus Haltern in der Werkzeugverwaltung, deren Aufnahme nicht zur Maschine passt?
  Eine Meldung im Assistenten, wie bei der Ausspannlänge.
  *Stufe 1 erledigt (P-2026-10-16-28), Punkte 1, 2 und 4:*
  - Die Spindel hat den Kennwert „Werkzeugaufnahme“ (Kennwerte der Spindel, Dialog „Neue
    Maschine“). Vorbelegt sind 3-Achs-Fräse SK40, Portalfräse HSK-F63, die 5-Achs-Fräsen und die
    G550 HSK-A63.
  - `halter.AUFNAHMEN` nennt 28 Aufnahmen mit Norm: SK30/40/50, BT30/40/50, CAT40/50, HSK-A32 …
    A100, HSK-E32 … E50, HSK-F63, Capto C3 … C8, KM32 … KM80. Jede hat einen typischen Flansch
    (Ø und Länge), keine Katalogwerte.
  - Die Vorlagen an der Spindel bekommen den Flansch der Aufnahme der offenen Maschine und nennen
    sie im Namen. „Neu → Für eine andere Aufnahme“ hat dieselben Vorlagen für jede andere.
  - Der Halter merkt sich seine Aufnahme (`Halter.aufnahme`).

  Offen bleiben Punkt 3 (dem echten Halter nachgebaut: Greiferrille, Kegel, Mutter – dafür die
  CAD-Dateien, siehe unten). *Stufe 2 (P-2026-10-16-38):* Flansch mit Greiferrille (Steilkegel
  spitz, HSK/Capto/KM mit flachem Grund) und Spannmutter mit Fasen, je eine Zeile
  (`Abschnitt.art`), nach Norm und frei sichtbaren Katalogwerten; gerechnet wird weiter mit dem
  vollen Abschnitt. *Stufe 3 (P-2026-10-16-39):* Vorlagen und Flansche nach den öffentlichen
  Katalogzeichnungen bei Hoffmann. Gegen eine STEP-Datei (300470 32) geprüft: auf 0,1 mm gleich.
  Gelesen sind ER16 … ER40, Schrumpf 6/12, Weldon 20, Hydro 20, Messerkopfaufnahme 22 und
  Bohrfutter an SK40, dazu die Flansche BT40 und HSK-A63. Jede Vorlage hat einen Link auf ihr
  Vorbild (an anderen Aufnahmen die Suche). „Neu → Aus Datei (STEP, STL) …“ liest die Kontur
  des eigenen Halters (`halter_datei.py`; die Spindelnase am Ende des Kegels, an 300470 32 auf
  0,9 mm). Offen: Capto/KM-Flansche nach Zeichnung (heute wie HSK), VDI und Winkelkopf weiter
  Beispielmaße. Der vorgeschlagene Halter hat seit P-2026-10-16-30 die Aufnahme der
  geprüften Maschine.
  *Die Meldung bei unpassender Aufnahme ist erledigt* (P-2026-10-16-29): „Auf der Maschine
  prüfen“ sagt „T1: Der Halter „…“ ist für HSK-A63, die Maschine hat SK40 …“.
  Manuel, 2026-10-16, mit Bild (ein HSK-Halter mit Greiferrille, Bund, Körper und Fräser): „wenn
  die halter so ausschauen würden wäre cool .. also dem echten objekt nachempfunden … wenn ich
  mich irgendwo regestrieren soll oder du vom hoffman die login daten benötigst um die cad dateien
  zu bekommen kein problem“. Die Form soll also dem echten Halter folgen: Flansch mit Greiferrille,
  Kegel bzw. HSK-Bund, Körper, Mutter. Heute sind es Abschnitte aus Zylindern und Kegelstümpfen.
  Anmelden mit seinen Zugangsdaten darf Claude nicht. Lädt Manuel die STEP-Dateien selbst herunter
  (etwa nach `~/freecad_cam/halter_cad/`), liest Claude die Maße daraus und baut die Vorlagen nach.
  Manuel ist im eigenen Browser bei Hoffmann angemeldet („weis nicht ob das reich für dich um dort
  die … cad dateien zu besorgen“). Claudes Browser-Fenster in der App ist davon getrennt. Weg:
  Manuel meldet sich dort selbst an, Claude sucht die Halter (HSK63, SK40, BT40, Capto C6 …) und
  fragt vor jedem Download (Datei, Quelle, Größe). Die Dateien kommen in einen eigenen Ordner und
  gelten als fremde Daten.

## Offene Bugs

Zurzeit kein offener Bug. B-001 bis B-019 sind behoben (Belege im Verlauf; B-017 und B-018 in P-2026-10-10-35 bis -39, B-019 – eine Nadel nach dem Adaptiv-Kern – in P-2026-10-11-84);
B-020 (ein Teil als Link in der Maschine angeklickt – der Assistent legte den Job im Dokument der Maschine an: „PropertyLink does not support external object“) behoben in P-2026-10-16-42. B-021 (FreeCADs Assembly ging mit dem Addon nicht mehr: „isInEditMode“, keine Bauteile einlegbar) behoben in P-2026-10-16-11; B-022 (eine Nut quer durch den Klotz galt mit 1 mm Aufmaß als geschlossen und „zu breit“, seit P-2026-10-16-07) behoben in P-2026-10-16-26; B-023 (mit Aufmaß am Boden trat Räumen nicht mehr an – die Bahn lag höher und galt als „Fläche nicht erreicht“, seit P-2026-10-16-05) behoben in P-2026-10-16-27; B-024 (seit P-2026-10-12-170 weicht die Rundum-Schruppbahn dem Halter aus – „Halter stößt an … länger ausspannen“ kam nicht mehr, im 4-Achs-Assistenten wie in „Kollision prüfen“; `szenario_vierachs_ausspannen` und `szenario_pruefen_ausspannen` rot) behoben in P-2026-10-16-33; B-025 (seit P-2026-10-12-170 hielt beim Schruppen mit der Querachse der Schaft die Spitze zu hoch – gerechnet auf dem Strahl durch die Stangenachse statt in der versetzten Stellung des Fräsers; an der Nase blieb für die Kugel bis 16,8 mm² je mm Rest, `test_vierachs_frei` rot) behoben in P-2026-10-16-37; B-026 (am Drehteil meldete die Kollision „Plan indexiert … im Eilgang durch Rohteil, das dort noch steht – bis 1,53 mm tief“: der letzten Lage fehlte am Rand der Fläche ein Stück jeder Zeile, und das Modell der Stange kannte bei Querversatz die Flanke des Fräsers nicht) behoben in P-2026-10-16-57; nächste freie Nummer B-027.

## Offene Tasks

- **T-015 Waagerechte Spindel (GROB G550): Grundstellung für Jobs ohne Ebene** (gefunden
  2026-10-17 nachts, an Manuels Schwenkteil nachgespielt): Ein Job „von oben“ (die Tasche oben,
  Räumen T1) läuft an der G550 mit A = 0 – „Auf der Maschine prüfen“: „Die Bahn ist für ein
  Werkzeug längs Z gerechnet, T1 sitzt auf Spindel aber quer dazu – so gefahren, passt sie nicht
  zum Teil“. Erst eine geschwenkte Ebene (P-54) stellt den Tisch an. Vorschlag: An einer Maschine,
  deren Werkzeug in Grundstellung nicht längs Z des Jobs steht, kommt auch „oben“ in eine Ebene
  (Normale +Z → A −90, `schwenken.lege_an(…, winkel=(0, 0))`), wie die schrägen Flächen – oder der
  Job bekommt eine feste Grundstellung der Rundachsen (Prüfung, Programm, Abfahren). Nachgespielt:
  Dieselbe Tasche in einer Ebene „oben“ (`lege_an` mit der Fläche) heißt „… Ebene Face25 (A90
  B0)“, die Maschine steht dabei auf A1 −90°, der Hinweis „quer“ ist weg. Größerer Umbau (auch
  „Alles aus dieser Aufspannung“ und „ohne Wahl: die Oberseite“), nicht ohne Manuel.
  *Erledigt:* Manuel, 2026-10-17: „Automatisch Ebene A−90“ – P-2026-10-17-21 (die gewählten
  Flächen kommen in die Ebene „von oben“, das Programm schwenkt). Auch „ohne Wahl: die
  Oberseite“ (nichts angeklickt) geht in die Ebene „von oben“ – geprüft in
  `szenario_g550_von_oben` („Nichts angeklickt“). *Erledigt.*

- **T-013 Herbert im deutschen Thread** (Forum t=107911, 2026-10-11, herbk; 26.3.0RC1-AppImage auf
  CachyOS, Addon 0.213.66, dazu CfdOF, Curves, Fasteners, RobotCAD u. a.):
  (a) „eine ganze Liste von Fehlermeldungen“ beim Aufruf von CAM, wieder beim Wechsel nach CAM in
  einer Teile-Datei – nachgespielt im gleichen RC1-AppImage und im Wochen-Build, frisches Profil,
  0.213.66 und 0.213.90, mit Maschine anlegen/speichern, Teil öffnen, Job anlegen: Bericht leer.
  Wortlaut ist angefragt; bis dahin kein Bug. (b) Wie Maschinen- und Teile-Datei zusammenkommen,
  hat er nicht gefunden (Job merkt die Maschine, `reichweite.merke_maschine`) – deutlicher in
  „So geht’s“ und in den Meldungen ohne Maschine. (c) Portalfräse (Router) – gebaut,
  P-2026-10-11-87. (d) Feld „Ausspannlänge“ – Manuel: nein, der Halter gehört in die Kollision,
  darum zählt die Länge ab Spindelnase. (e) Maschinendaten aus der Steuerung einlesen – Manuel:
  nein, zu viele Steuerungen; Eilgang, Vorschub und Beschleunigung trägt man einmal ein (Hilfe
  „Beschleunigung ermitteln“), „Auf der Maschine prüfen“ rechnet die Zeit damit. Die Wahl
  zwischen Bahnvarianten (Räumen, Planfräsen: `bahn.zeit`) rechnet noch mit den Vorgaben
  10 m/min und 1 m/s² – ob sie die gewählte Maschine nehmen soll, ist Manuels Entscheidung. (f) Dialekt: ist schon so
  gebaut (Path-Befehle, Postprozessor übersetzt) – die Vorstellung nannte nur Siemens.
  (b) „So geht’s“ und `ba.maschine.leer` sagen es jetzt (P-2026-10-11-88). Offen bleibt (a).
- **T-012 Schnittstellen zu 26.3** (Forum, 2026-10-11, Connor aus dem CAM-Team): 26.3 hat 3+2 mit
  DRO und TWP, Postprozessoren je Maschine und den Maschineneditor; ein neuer Simulator mit einer
  Bibliothek für Spannmittel (Schraubstöcke, Platten, Spanner) und Kollisionsanzeige ist in Arbeit;
  5-Achs-Simultan scheitert in CAM bisher daran, dass das Werkzeug immer in Z steht. Prüfen, sobald
  es im Wochen-Build steht: 3+2 über TWP statt eigenem CYCLE800/PLANE SPATIAL, die Spannmittel aus
  der Bibliothek in unserer Kollision statt nur Schraubstock und Futter, die Maschine weiter als
  `.fcm` übergeben (`export.py`). Nichts davon ersetzen, ohne Manuel zu fragen. Manuel,
  2026-10-11 abends: Was FreeCAD schon hat, nutzen – aber erst Bahnen und Programme an echten
  Fällen vergleichen, ob sie so gut sind wie die eigenen. Seine Linie: Das Addon rechnet die Bahnen
  aus, die Maschine braucht keine Zyklen, fährt kleinschrittig mit Glättung (heute so bei 4 und 5
  Achsen simultan; 3+2 schreibt für Siemens noch CYCLE800, Bohren die Bohrzyklen). Im RC1: die
  Maschine erklärt DWO (G54.2/G254) oder TWP (G68.2/G268/PLANE SPATIAL), kein CYCLE800;
  POST_TRANSFORM (selbst umrechnen) ist vorgesehen, wird aber noch nicht geschrieben.
- **T-011 Versionscheck 26.3** – Manuel arbeitet mit FreeCAD 26.3.0RC1 (Windows); dort brach schon
  der Adaptiv-Kern (P-2026-10-10-39): voller Lauf im Wochen-Build 26.3, was er findet, sofort
  beheben (Arbeitsregeln, Abschnitt 9). Behoben: Kern-Aufruf (-39), Bohren-Namen (-41), dunkles
  Theme (-42), Räumen mit dem neuen Adaptiv-Kern und Bestmarken je Kern (-43), drei Prüfdateien,
  die in beiden Versionen fielen (-44), Uhren mitten in booleschen Operationen (-45: Absturz im
  Szenario „Ebene schwenken“). `test_goldene_bahnen` hat seit P-2026-10-11-92 eine Referenz je
  OpenCascade-Version (7.9 für 1.1, 8.0 für 26.3 – RC1 und Wochen-Build gleich): in OCC 8.0
  liegen die Linien beim Schlichten anders (12 040 → 12 028 Punkte), keine Rundungsfrage. Im Wochen-Build grün: 13 Szenarien zu Assistent, Bohren, Gewinde, Reiben,
  Räumen, Nut, Programm, Schwenken, 4 Achsen; die übrigen 114 nicht gelaufen.
  **Voller Lauf in 26.3.0RC1 (2026-10-10, Manuels Version, Linux-AppImage von GitHub):** 111
  Prüfdateien und 127 Szenarien. Behoben: dunkles Theme in RC1 (-48: Grund der Aufgabenfenster
  #5a5a5a), Job-Gruppe „Workplanes“ (-49), Qt-Installationszeile in 26.3 grundsätzlich abgelehnt
  – die Update-Suche ohne Git geht (-50), 3D-Flächenfarben im 4-Achs-Assistenten (-51, Folge von
  -42, auch in 1.1), B-016 in RC1 behoben (-52). Danach alles grün außer: `test_goldene_bahnen`
  (Umgebung, wie oben – seit P-2026-10-11-92 grün), `szenario_mausrad` (die Rasten per XTest kommen unter gamescope nicht an –
  auch in 1.1.4 rot; auf diesem Rechner nicht prüfbar), einmal ein Absturz in
  `szenario_vierachs_schlichten` (`munmap_chunk(): invalid pointer` in `doc.recompute()` nach dem
  Schließen, unter Volllast mit fünf anderen Läufen) – siebenmal danach grün, nicht nachgestellt.
  Am 11.10. derselbe Ort in `szenario_vierachs_aendern` („free(): invalid size“, unter Volllast);
  seit P-2026-10-11-80 rechnet das Dokument nach `closeDialog()` ohne Ereignisse (`uhren.still`).
  Nebenbei: `test_simultan_planung` und andere richten den Werkzeugspeicher auf
  `beispiele/grob_g550_freiform/assets`, und RC1 schreibt dort die `.fctb` beim Laden neu
  (sortiert, `"Units": "Metric"`) – nach einem Lauf in 26.3 mit `git checkout` zurücksetzen.
  Offen: Manuel klickt die sichtbaren Funktionen in seinem RC1 einmal durch (Arbeitsregeln,
  Abschnitt 9).
- **T-006 Alle Kerne nutzen** – *Stand 2026-10-17 (Manuel: „bitte immer daran denken das alle
  rechenkerne auch genutzt werden“):* verteilt sind Kollision, Voxelstange, Hüllfläche, die
  Vorschauen beider Assistenten, der senkrechte Abtrag (Streifen) und seit P-2026-10-17-39 der
  schräge Abtrag im Abspieler. **Noch auf einem Kern:** die Reichweite-Prüfung (`reichweite.
  Pruefung.pruefe_job`, am 4-Achs-Testteil 1,2 s beim Öffnen des Prüffensters – im Takt erst ab
  20 000 Sätzen); sie in Stationsstücke zu teilen wie die Kollision braucht ein Zusammenführen
  der `_Sammler`-Befunde je Stück – der nächste Schritt hier. (Manuel, 2026-10-04: „es rechnen nur maximal 5 von meinen 24 Kernen
  … kann man das nicht optimieren, dass alle genommen werden?“). Gemessen (4-Achs-Schruppen):
  das Prüffenster öffnet nach 3,8 s; der lange Teil ist „Kollision prüfen“ – reines Python je
  Station, ein Kern; seit P-2026-10-04-48 27,6 → 16,4 s. Seit P-2026-10-04-74 schätzt sie mit
  den gedrehten Hüllquadern enger nach unten und rechnet seltener genau: am Schwenkteil
  (Entgraten 3D, gekippter Rundtisch) 60 → 25 s, ein 3+2-Job (Räumen und Bohren in zwei Ebenen)
  97 → 83 s. Der Rest ist Werkzeug gegen Teil, wo es nah daran fährt (2,5–3 ms je Rechnung in
  OpenCascade) – am 3+2-Job fast ganz der Kern der Schneide im Vorschub an der fertigen Fläche
  (Abstand 0,05 mm, 22 000-mal). *Verworfen (2026-10-04):* eine Schranke aus einer Punktwolke des
  Teils (wie Entgraten 3D) – sie liegt nie über dem wahren Abstand, entscheidet 0,05 mm aber nie
  und kostet in Python so viel wie OpenCascade: 3+2 83 → 212 s. Weiter geht es nur mit mehreren
  Prozessen (die Stationen in Stücke) – der Kern selbst ist gleich teuer. Nächster Schritt: die Stationen in
  Stücke teilen (mit Vorlauf an jeder Grenze) und parallel prüfen – entweder abgezweigt (fork,
  nur Linux, schnell gebaut, mit Zeitgrenze und Rückfall auf einen Kern) oder in eigenen
  FreeCAD-Prozessen (überall, aufwendiger); danach die Vorschau des 4-Achs-Assistenten messen.
  **5-Achs-Vergleich (2026-10-09, Manuel: „Rechenzeit im Betrieb weniger … oder mehr CPUs“):**
  dieselbe Stelle – an der Kuppel des Szenarios ist die Kollision 51 % einer Variante (12 394
  genaue OpenCascade-Abstände), Höhenfeld 21 %, Material 11 %; eine Ø-4-Variante am
  Freiformbeispiel 30 min auf einem Kern. Hebel und Reihenfolge: Spezifikation Strategien 16.5,
  „Rechenzeit“.
  **Nebenrechner gebaut (P-2026-10-09-07):** `nebenrechner.py` – ein Pool eigener
  FreeCADCmd-Prozesse, je Kern einer, mit Dokumentkopien und gemeinsamen Daten.
  **Kollision in Stücken (P-2026-10-09-08):** Prüffenster und 5-Achs-Zulassung; am
  Freiformbeispiel 307 → 54 s (24 Kerne; 12 Arbeiter genauso schnell – SMT bringt nichts, die
  letzten 10 % der Stationen ein Viertel der Zeit). **Vorschau des 4-Achs-Assistenten im
  Hintergrund (P-2026-10-09-09):** je Bearbeitung ein Auftrag, das Fenster bleibt bedienbar
  (Manuel, 2026-10-09: der „Lag“ beim Ändern der seitlichen Zustellung) – ob es sich so anfühlt,
  prüft Manuel; seine Regel dazu (2026-10-10): generell nichts bauen, was laggt – Arbeitsregeln,
  Abschnitt 7. **Prüfungen eingedampft (P-2026-10-09-10):** `test_simultan_planung` und
  `test_simultan_gesamt` an der Kuppel in je unter drei Minuten (vorher 30 und 70 min). **Hüllfläche in Blöcken und auf allen Kernen
  (P-2026-10-09-11):** der Kuppelvergleich (eine Variante) 131 → 44 s. **Normalen, Kugelschnitt und
  Deckung in Stücken (P-2026-10-09-12):** der Kuppelvergleich 44 → 23 s, `test_simultan_planung`
  36 s. Am Freiformbeispiel eine Variante 670 → 211 s (P-2026-10-09-13:
  Referenzen neu, 4 Punkte weniger durch exaktere Hüllfläche). T-007 Werkzeugkiste-Import gebaut (P-2026-10-10-06, mit exakter Dublettenprüfung). **Netzschranke gebaut (P-2026-10-10-27, Hebel 2):** gezählt war es nicht Halter und Spindel, sondern der Kern der Schneide gegen das Teil (9 246 von 10 374 genauen Abständen an der Kuppel); jetzt Werkzeugteile als Kapseln gegen das vernetzte Teil mit numpy – 10 374 → 841 Aufrufe, 21,4 → 3,7 s in OpenCascade, mit 24 Arbeitern Kollision 7,0 → 5,0 s von 32 s. Gemessen (P-2026-10-10-28): der Aufbau der Welt je Arbeiter kostet nichts (0,03 s), die 5 s sind die Stellen selbst (89 s CPU über 24 Arbeiter mit SMT). **Freiformbeispiel, Phasen mit 24 Arbeitern (376 s):** `schlichten3d.rechne` 181 s (48 % – die Hüllfläche davon nur 4 s, der Rest der Bahnbau in einem Prozess), `deckung` 58 s, `Pruefstand` 48 s, Kollision 18 s, `fahren` 25 s, Normalen 12 s. **Gemerkt statt neu gerechnet (P-2026-10-10-29):** das Netz des Teils, das Soll-Höhenfeld des Prüfstands und die Randzüge je Form/Fräser – Freiform 376 → 243 s, `rechne` 181 → 57 s, derselbe Gewinner. MeshPart als schnellerer Vernetzer (8×) verworfen: ändert Deckungsurteile am Rand (Kuppel: 4 Zellen). **Deckung auf feinem Gitter (P-2026-10-10-30):** 59 → 26 s, Freiform gesamt 243 → 201 s. Stand: `rechne` 55 s (7 Aufrufe – beide freien Anstellungen rechnen dieselbe Bahn), Prüfstand 36 s (Vernetzen zweimal wegen der Dreiecksprobe), Deckung 26 s, Kollision 21 s, `fahren` 26 s in einem Prozess, Normalen 13 s, Einschnitt 9 s. **Je Stufe eine Bahn für beide freien Anstellungen (P-2026-10-10-31):** 201 → 178 s; heute insgesamt 376 → 178 s bei gleichem Gewinner. Was bleibt, ist strukturell: das Vernetzen im Prüfstand (37 s, einmal je Teil), `fahren` in einem Prozess (18 s, der Materialstand ist eine Folge), der Bahnbau je Stufe (9 s: beide Flussrichtungen gerechnet, die schnellere genommen; Douglas-Peucker seit P-2026-10-10-33 vektorisiert), Kollision 18 s. **Netzschranke mit Stirnebene (P-2026-10-10-34):** Schaftfräser entscheidet jetzt auch der Kern am Boden – Manuels 3-Achs-Testteil „Kollision prüfen“ 21,8 → 9,3 s (ein Prozess 146 → 58 s, genaue Abstände 30 769 → 684). Dann die Varianten des Hakens „Alle Kombinationen“ parallel (Hebel 3). **Nacht 10./11.10. (P-2026-10-10-57 bis P-2026-10-11-05), am 4-Achs-Testteil:** Hüllfläche je Stellung, Zusammenfassen der Querachsen-Spirale (Ketten, an gemeinsamen Punkten zusammengesetzt), Rest je Rasterstelle und die Bahn am Werkstück auf den Nebenrechnern, bitgleich; Neuberechnen 22,7 → 6,4 s, Prüffenster 13 → 11 s. Kollision: je Kern ein Arbeiter (Gruppe im Pool, SMT-Zwillinge bremsen OpenCascade), 24 statt 48 Stücke je Arbeiter, Netzschranke auch mit gewinkeltem Halter – 243 → 181 s; der Rest sind die Stellen, an denen der Halter wirklich ans Teil kommt (Frage 7). Hebel 3 bleibt offen. **Später in der Nacht (P-2026-10-11-07 bis -13):** Unteraufträge – ein Arbeiter verteilt über den Pool der Oberfläche weiter, beim Warten rechnet er seine eigenen (die 4-Achs-Vorschau auf allen Kernen: 3,5 → 1,1–1,8 s); Stücke des Zusammenfassens an festen Punkten (die Ketten treffen sich sicher); Hüllfläche je Winkel und Rest nach dem Schruppen verteilt; 4-MiB-Puffer je Verbindung (die Oberfläche wartete beim Senden); QSocketNotifier statt 30-ms-Takt; Dokumentkopie wiederverwenden; Vorwärmen. Arbeiter an Kerne binden geprüft und verworfen (OpenCascade rechnet `distToShape` selbst mit mehreren Fäden; gebunden 184 statt 162 s). GPU verworfen (Manuels Frage, 2026-10-10): OpenCascade
  rechnet nur auf der CPU, der numpy-Anteil läuft schon auf allen Kernen, und je Hersteller
  (NVIDIA, AMD, Intel) bräuchte FreeCADs Python einen eigenen Treiberstapel – zu wenig Gewinn
  für zu viel Abhängigkeit. Die Arbeiterzahl folgt `os.cpu_count()` des Rechners, auf dem FreeCAD
  läuft (sechs Kerne: sechs Arbeiter), änderbar in den Einstellungen.
- **T-009 Auflösung je Strategie einstellbar** (Manuel, 2026-10-09: „die Auflösung bei jeder
  Strategie einstellbar … in mm, immer mit verständlicher Erklärung“). Gebaut (P-2026-10-09-14):
  „Bahn gerechnet für“ im 5-Achs-Vergleich, `BahnGrathoehe` sichtbar. Gebaut (P-2026-10-09-15): der Vergleich
  verfeinert von selbst (75, 50, 25, 12,5 %; die Kuppel besteht bei 75 %: 98 → 74 s, die
  Freiform bei 25 %). Gebaut (P-2026-10-09-17): Feld „Auflösung“ je
  Strategie-Block in „Bearbeitung“ (Planfräsen, Räumen, Kontur, Entgraten, Bleistift, 3D-Schruppen,
  3D-Schlichten), Eigenschaft `Raster` an der Operation. Gebaut (P-2026-10-09-18): im 4-Achs-Assistenten „Auflösung längs“ (mm)
  und „Auflösung rundum“ (°) beim Schruppen, „Auflösung rundum“ beim Schlichten. Nachgezogen (P-2026-10-10-01): der
  Vergleichsdialog zeigt überall dasselbe Dezimalzeichen (Restgrenze, Zwischenlage und Statuszeile
  folgten „gewählt, sonst Punkt“, das Feld „Bahn gerechnet für“ dem Zahlenformat der Oberfläche). Gebaut (P-2026-10-10-03, Manuel: „ich würde es überall einbauen“): auch Plan
  indexiert (Netzfeinheit), Rundum entgraten, Entgraten 3D und Flanke (Schritt auf der Kante);
  jede Erklärung mit Beispiel, wo feiner nichts mehr bringt (gemessen: 3D-Schruppen Freiform
  0,5 → 0,25 mm: 3 → 6,5 s). **T-009 fertig**; die Erklärung trägt (Manuel, 2026-10-10: „das ist gut so“).
- **T-007b Weitere Hersteller-Reihen** in der Kiste (Manuel: „zum Schluss“) – seit P-2026-10-10-06 über
  Dateien („Aus Datei einlesen …“); Manuels Hoffmann-Datei (79 Reihen) liegt in `beispiele/` – die
  vier Tonnenfräser sind raus, die Form hat das Addon nicht (P-2026-10-10-17).

- **T-004** Fehler an FreeCAD melden: `Machine.from_dict` liest bei Linearachsen einen
  Ursprung ≠ (0,0,0) als Richtung. Im Klartext: Speichert CAM eine Maschine und lädt sie wieder,
  kommt jede Linearachse, deren Gelenk nicht im Nullpunkt sitzt, verdreht zurück – beim Lesen
  wird der erste Vektor des Gelenks (der Ursprung) für die Richtung gehalten (Befund und Beleg in
  P-2026-09-25-20). **Nicht behoben** (Manuel, 2026-10-10: „ist das im wochenbuild schon
  behoben“): im Wochen-Build vom 2026-09-16 da, im FreeCAD-Quelltext (main, 2026-10-10)
  unverändert; FreeCAD 1.1.4 hat das Modul `Machine` gar nicht, nur der Wochen-Build. Solange er
  besteht, übergibt das Addon Linearachsen mit Ursprung 0 und ist nicht betroffen.
  **Der Bericht ist fertig zum Einreichen:** [freecad_fehler_T-004.md](freecad_fehler_T-004.md)
  – einreichen kann nur Manuel (GitHub-Konto).
- **T-010** Fehler an FreeCAD melden: `Path.Tool.Controller.Create` – in jedem
  `Path.Main.Job.Create` – schließt die laufende Undo-Transaktion; was ein Skript danach in
  derselben Transaktion anlegt, kennt das Rückgängig nicht. Ursache von B-016 (P-2026-10-08-07,
  eingegrenzt in P-2026-10-10-21 und -23: der Werkzeugkörper entsteht in einem versteckten
  Hilfsdokument, das mit der ersten Änderung der Transaktion beitritt; sein Schließen beendet sie
  für alle Dokumente – mit `UndoMode = 0` am Hilfsdokument nicht). Das Addon räumt seine
  verwaisten Klone nach dem Rückgängig selbst auf. **Der Bericht ist fertig zum Einreichen:**
  [freecad_fehler_T-010.md](freecad_fehler_T-010.md) – einreichen kann nur Manuel.
  **In FreeCAD 26.3.0RC1 behoben** (P-2026-10-10-52): Dasselbe Szenario lässt dort keinen
  verwaisten Klon mehr zurück, in 1.1.4 weiter. Einreichen lohnt also nur noch für 1.1.
