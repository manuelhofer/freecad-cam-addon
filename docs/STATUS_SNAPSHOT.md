# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks.

## Projektstatus
- **IN ARBEIT** – W-001, Stufen 1 bis 3, 3b (schräge Achse, „Neue Maschine …“, Punkt 11 unten) und 4a (Auf der Maschine prüfen, Punkt 13) fertig und automatisch geprüft; warten auf Manuels Test. Stufe 4b (Abfahren, Punkt 13; Manuel: „bau das mit der Maschine“): fertig und automatisch geprüft (P-2026-09-26-89 bis -91, 0.23.0). Stufe 4c (Kollision) mit Manuels Entscheidungen (P-2026-09-26-93): fertig und automatisch geprüft (P-2026-09-26-97 bis -99, 0.24.0). Beim Durchsehen nachgebessert (P-2026-09-27-02 bis -04): die Schneide von Nutenfräser (Schneidenbreite) und Lollipop (Kugel) in Abfahren und Kollision, kein Fehler mehr bei nur „,“ oder „-“ in einem Zahlenfeld, die Spaltenköpfe im Fenster „Halter“ ganz lesbar. Verfahrwege im Fenster „Maschine bearbeiten“ änderbar (P-2026-09-29-03, 0.26.1). Stufe 4e: Werkzeugspitze an einer Stelle gerechnet (`kinematik.py`), im Abspieler und an Überschreitungen (P-2026-09-29-10, 0.27.0); TCPM wählbar zurückgestellt (Frage an Manuel, ob seine Steuerung TRAORI/RTCP nutzt).
- **IN ARBEIT** – W-002, Spezifikation als Entwurf (Entscheidungen von Claude, zur Besprechung); Stufen 1 bis 3 fertig und automatisch geprüft (Werkzeugverwaltung, Übergabe an CAM und in den Job, Schruppwerte planen), dazu die 26 Werkzeugarten (Plan-Stufe C); wartet auf Manuels Test. Stufe D (Halter, für W-001 4c) mit Manuels Entscheidungen ([spezifikation_halter.md](spezifikation_halter.md), P-2026-09-26-93) fertig und automatisch geprüft (P-2026-09-26-94 bis -96). Stufe E (die Richtung des Werkzeugs am Halter – gerade, angetrieben radial, Winkelkopf; Manuel 2026-09-30) fertig und automatisch geprüft (P-2026-09-30-10 bis -16, 0.29.0): Datenmodell und Vorlagen, Fenster „Halter“ mit Richtung und Bild, Reichweite/Abfahren/Kollision mit der Lage aus dem Halter, der Halterkopf vor dem Futter (Rundum), Beispiel-Drehmaschine mit Aufnahmen, gelber Satz im 4-Achs-Assistenten; wartet auf Manuels Test.
- **IN ARBEIT** – W-003 4-Achs-Bearbeitung am runden Rohteil: Spezifikation mit Manuels Entscheidungen (P-2026-09-26-78), Stufe V1 „Teil in die Stange“ (P-2026-09-26-79), V2a „Achse von der Maschine“ und V2c (P-2026-09-27-37, -38), V3 „Rundum schruppen“ – Hüllfläche, Bahn, Operation, Schritt 2 „Was willst du machen?“, Prüffenster ohne TCPM (P-2026-09-27-45 bis -54, 0.26.0), nachträglich ändern per Doppelklick (V3h, P-2026-09-29-04, -06, 0.26.1/0.27.0), Überlauf und Ausspannlänge, Kugel-/Torus-Hinweis, Maschine zuerst (V3f, P-2026-09-29-07 bis -09), Rohteil/Fertigteil in der Simulation (V3g, -11, 0.27.0) – fertig und automatisch geprüft; wartet auf Manuels Test. Dabei die Kollisionsprüfung beschleunigt (über 20 Minuten → Sekunden, -50, -53) und der Rückzug im Eilgang kein Befund mehr (-51). V5 „Rundum schlichten“ mit Manuels Entscheidungen (2026-09-30: Spirale, jeder Fräser mit seiner Form, Schrittweite aus der Werkzeugtabelle, Abstände einmal für beide): Fräserform und Hüllfläche, Bahn, Operation, Assistent, Stufen, wo das Schruppen mehr stehen ließ, Abtrag und Schneide mit der Form (V5a–V5e, P-2026-09-30-01 bis -08, 0.28.0) – fertig und automatisch geprüft; wartet auf Manuels Test. Nach Manuel (2026-09-30: „mit den Grundvoraussetzungen anfangen“) die Richtung des Werkzeugs am Halter und die Beispiel-Drehmaschine mit Aufnahmen gebaut (W-002 Stufe E, 0.29.0): Schruppen T1 und Schlichten T2 mit radialem Halter gehen dort zusammen – Prüfen, Abspielen, Kollision, Farben (`szenario_rundum_drehmaschine`). Durchsicht 2 auf Bedienbarkeit und Logik ([durchsicht_bedienbarkeit.md](durchsicht_bedienbarkeit.md), Abschnitt 7, D-40 bis D-47): Ringgang vor jeder Wand (hinter einem Absatz blieben bis 6,4 mm, jetzt höchstens 0,33), „T3 öffnen …“ im gelben Satz, Stationen am Revolver, Drehung 0, Längen-Texte; keine versteckten Ausnahmen mehr (P-2026-09-30-17, -19 bis -23, 0.29.1) – fertig und automatisch geprüft; D-45 so gelassen (Empfehlung A). V4 „Flächen wählen“ (Plan P-2026-09-30-25): Rechenkern `vierachs_flaechen` und Bahnen nur im Bereich der gewählten Flächen (V4b, -26), Flächen im Assistenten mit Liste, Erreichbarkeit und Farben (V4a, -27), in Zeilen hin und her statt Spirale mit Eilgängen rundum (Manuel: „man kann ja auch einfach zurück drehen“, -28), 0.30.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Getrennte Flächen nacheinander, Rampe längs der ganzen Fahrt (-31), V4e Prüfen nur auf den gewählten Flächen (-32); auf Manuels Fragen: Installation ohne Pythons SSL über den Netzzugang des Addon-Managers (-33, -35), der Fräser steckt im Prüffenster im Halter (-34, -37), Postprozessoren von FreeCAD geprüft und in der Hilfe (-36); 0.31.0 – fertig und automatisch geprüft; wartet auf Manuels Test. F in jedem G93-Satz für jeden Postprozessor, auch Fanuc und UCCNC ohne Optionen (Manuel: „Es muss ja für alle funktionieren“, -39); neue Testregel (-40); 0.31.1. An Manuels Testteil (Loft, D-Profil, hinten neben der Achse): kein Fehlalarm Blau mehr, wo das Teil nicht rund um die Achse liegt (-44), das fertige Teil am Ende ausgeblendet (-45); Wege in „Neue Maschine“ bis 10 m (-46); 0.31.2. Haken „Bahn“ im Abspieler (-48); 0.31.3. X und Z der Drehmaschine zählen wie an der Maschine: bis zur Mitte der VDI-Aufnahme, X ab der Spindelachse, Z ab der Spindelnase (-50); 0.31.4. Revolverart in „Neue Maschine“: VDI in der Stirn oder am Umfang, Scheiben-Ø, VDI-Größe (-52); 0.31.5. X im Durchmesser oder Radius: Haken „zählt im Durchmesser (Ø)“ an der Betriebsart, „X als“ in „Neue Maschine“, alle Fenster zeigen X dann mit „Ø“ (-54); 0.31.6. Bestückung an der Maschine (W-002 Stufe F, Manuel: „passt“): Abschnitt „Bestückung“ in „Maschine bearbeiten“, der 4-Achs-Assistent gibt dem Controller die Nummer des Platzes, das Prüffenster meldet einen anders bestückten Platz (-56); 0.32.0; der Platz vorn in der Fräserliste (-58); 0.32.1. Auf Manuels Bilder: Höchstdrehzahl der Hauptspindel und der angetriebenen Werkzeuge getrennt (-60), Planaufmaß 0 grau als „0“ (-61), der Ordner „Operations“ öffnet „Rundum schruppen“ zum Ändern (-62); 0.32.2. Bestückung je Job (W-002 Stufe G; Manuel, 2026-09-30: „die bestückung sollte je nach job funktionieren … wird nicht dargestellt auf der maschine“, „jeder job hat seine eigene bestückung“): Rechenkern `bestueckung.py` – der Platz ist die Nummer der Controller –, Fenster „Bestückung“ mit dem Revolver und den Werkzeugen des Jobs in der 3D-Ansicht, beim Abfahren alle Werkzeuge des Jobs im Revolver, „Maschine bearbeiten“ ohne Bestückung (-65); 0.33.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Auf Manuels Wunsch (2026-09-30: „bessere frässtrategien … als in freecad“, „einfach solls sein gut erklärt“): Plan W-006 Frässtrategien ([spezifikation_strategien.md](spezifikation_strategien.md), Stufen S1–S7, E1–E7 zur Besprechung, -66) und Durchsicht 3 Bedienbarkeit (D-50 bis D-58, -67). Die kleinen Punkte der Durchsicht 3 (D-50 bis D-53, D-55 bis D-57, -69), VDI-Halter ohne Größe (Manuel: „also reicht VDI halter aus“, -70), Messung der Bahnrechnung mit Zahlen in W-006 und goldene Bahnen (S1, -71, -73), die Messung in zwei Durchgängen mit richtigen Zeiten (-75, -76), der Rest nach dem Schruppen blockweise, damit der Speicher nicht mit der Bahn wächst (-77); 0.33.1. Manuels Entscheidungen (2026-10-01, „Also ja“): W-006 E1–E7 je (a), D-54 (a), D-56 bleibt (P-2026-10-01-01). Haken „Teil“ im Abspieler – am Ende das fertige Teil grau unter der halb durchsichtigen Stange (-02); 0.33.2. Hilfeseite „So geht’s“ – der Weg vom Teil zum Programm in sechs Schritten, oben im Menü, mit Verweisen auf alle Seiten (D-54, -04); 0.33.3. Linien längs (V4c, W-006 S2): das Muster an „Rundum schlichten“ – Spirale oder Linien längs der Achse bei festem Winkel, gegenläufig, nur über den gewählten Flächen –, der Assistent schlägt es nach den Flächen vor, mit Grund (-06); 0.34.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Plan indexiert (V4c, W-006 S2): eigene Operation – die Rundachse steht, ein Fräser mit ebener Stirn fährt Zeilen längs und rückt mit dem Y quer, in Lagen bis auf die ebene Fläche; die Bahn trägt den Versatz quer, die Befehle das Y, der Abtrag rechnet den versetzten Fräser; im Assistenten ein dritter Haken mit Vorschlag und Grund (-08); über das Ende der Fläche hinaus fräst die Stirn nur, wo nichts höher steht als die Fläche (-10); Testregel nach Manuel („weniger testest mehr Produktivität“): nur die Prüfung und das Szenario zum geänderten Teil, in 1.1.3 (-09); 0.35.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Rundum entgraten (V4d, W-006 S2 damit fertig): eigene Operation – an den Außenkanten der gewählten Flächen fährt der Fasenfräser entlang (oder die Kugel bricht sie rund), die Rundachse dreht mit, die Spitze um die Fasenbreite unter der Kante; Innenkanten, Rundungen und Stirnen bleiben; der Abtrag lässt die Fase durch; im Assistenten der vierte Haken mit Vorschlag und Grund (-12); 0.36.0 – fertig und automatisch geprüft; wartet auf Manuels Test. W-006 S3 (2,5D) begonnen: der Plan S3a–S3g in der Spezifikation, die Hüllfläche von oben je Zeile (`hoehenfeld`), die Bahn mit Bögen G2/G3 (`bahn`) und „Planfräsen“ als Operation (`planfraesen`: Zeilen hin und her in Lagen, Überlauf, Halbkreise, Zeilen halten vor Absätzen, beim Austritt langsamer; FreeCADs Tiefen und Höhen) – automatisch geprüft, noch ohne Assistent (-14). Der Assistent „Bearbeitung (Fräsen)“ für den Quader (S3c, E4): eine Fläche anklicken, der Job mit dem Rohteil (Aufmaß je Seite) entsteht sofort, Flächen (ohne Wahl die Oberseite), Fräser und Einsatz aus der Werkzeugverwaltung, „→ 3 Lagen, 30 Zeilen, etwa 3 min“, Anlegen, Ändern per Doppelklick, Hilfe, Szenario (-15); 0.37.0. Prüffenster 2,5D (S3d): das Rohteil im Quader als Höhenfeld, jede Operation trägt mit der Form ihres Fräsers ab (auch FreeCADs eigene), am Ende der Vergleich mit der Oberseite des Teils in Farben, mit gewählten Flächen nur auf ihnen – die Simulation fand dabei die Reste des Planfräsens an Wänden (zwischen den Zeilen und in den Ecken), jetzt fährt der Fräser dort an der Wand entlang (-16); 0.38.0. Auf Manuels Punkte (2026-10-01): der Werkstoff steht je Zeile in der Schnittwert-Tabelle statt oben im Fenster (Auswahl je Zeile, „Alle Werkstoffe“ als Rückfall, keine „Eigene Werte anlegen/löschen“ mehr), in „Neue Maschine“ steht bei „von“ das Minus fest vor dem Feld, die Spanneisen der Beispiel-Fräse sehen aus wie Spanneisen (Eisen, Schraube, Mutter) (-17); 0.39.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Sein Testteil (Loft, D-Profil; am 2026-09-30 hochgeladen) liegt jetzt unter `beispiele/test4achsbearbeitung.FCStd`; eine über „Neue Maschine“ gebaute 3-Achs-Fräse hat keine Spanneisen mehr auf dem Tisch (nur die Beispiel-Fräse der Prüfungen), eigene Werkstoffe stehen in der Werkstoff-Spalte (-18); 0.39.1. Kontur (S3e): Wände anklicken – ihre Unterkanten werden Konturen, außen um einen Zapfen oder innen in einer Tasche –, Schruppen in Lagen mit Aufmaß so breit, wie Rohteil neben der Wand steht, Schlichten in einem Zug, tangentiales Ein- und Ausfahren, Gleichlauf, Bögen in den Ecken; im Assistenten je Strategie ein Block mit Haken (Planfräsen, Kontur), „Anlegen“ legt alle angehakten an (-19); 0.40.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Manuels Maßstab (Platte 200 × 200 mit Zapfen und Tasche, Ø 12 mit ae 1,5 / ap 25): die Zeiten je Strategie in der Spezifikation Abschnitt 11 (heute 79 min, mit ganzer Schneide 44, Untergrenze 31) – S3f wird „Räumen mit Versätzen“ (Spirale bei vollem ap, einmal hinein); dabei die Starttiefe auf das Rohteil gelegt (FreeCADs Vorgabe lag 1 mm über dem Modell: eine Lage Luft) (-20); 0.40.1. Der Nullpunkt frei setzbar (S3h, Manuel): im Assistenten die 22 Punkte des Rohteil-Quaders zur Wahl, um X, Y, Z verschiebbar, Teil und Rohteil rücken sofort (-21); 0.41.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Eilgang und Beschleunigung festgesetzt (W-001 4d, Manuel: „dauerhaft festsetzen“): 10 m/min, 1 m/s² je Linearachse, 1 U/s² je Rundachse, wo die Maschine nichts sagt; `fahrzeit.py` rechnet jeden Satz mit dem Trapezprofil, fährt durch Bögen und Rampen durch, hält an Ecken, um Eilgänge und am Ende – im Prüffenster (`abfahren`) und in der Schätzung des Assistenten „Bearbeitung“ (`bahn.zeit`); die Platte neu gerechnet (80 / 44 / ≈ 35 / 31 min) (-22); 0.42.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Manuels Standardfräser als die eine Definition (`werkzeuge.standardwerkzeug()`: Ø 12, ae 1,5 / ap 25 / fz 0,1 / vc 85, Rampe 3°; Manuel: „generell sollte dann jede Strategie und Szenario mit diesem Fräser und den Werten gerechnet und geprüft werden“): Regel in den Arbeitsregeln, alle 2,5D-Prüfungen und -Szenarien damit gerechnet – dabei gefunden und behoben, dass das Einfahren der Kontur in der Tasche bis in die gegenüberliegende Wand schwenkte (mit Ø 12 1,8 mm; die Hüllfläche blendet die eigenen Wände aus, jetzt hält das Ein- und Ausfahren den Abstand der Bahn), Ergebniszeile in Einzahl („→ 1 Lage, 23 Zeilen“) (-23); 0.42.1. Grundsatz 0 „Die Zeit entscheidet“ (Manuel: „immer den schnellsten Weg für das gewählte Werkzeug … immer die schnellste Strategie“) genau gefasst in der Spezifikation Strategien, Abschnitt 5: Varianten rechnen statt Regeln, alle Strategien treten mit derselben Zeit an, der Maßstab ist die Platte; erstes Stück gebaut: das Planfräsen rechnet beide Zeilenrichtungen und nimmt die schnellere, die Ergebniszeile sagt, wie viel langsamer die andere wäre, die Operation zeigt die Richtung (-24); 0.43.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Räumen (W-006 S3f; Manuel, 2026-10-01: „Bei so einem Teil erwarte ich sozusagen einen HSM-Werkzeugweg … von außen kreisend zur Mitte, immer volle Tiefe mit ae-Zustellung … Gleichlauf/Gegenlauf nicht vergessen“): `raeumen_bahn.py` räumt ebene Flächen und Taschenböden mit Ringen aus einem Abstandsfeld im Raster – volle Zustellung, schmales ae, ohne Wenden, Bögen in den Ecken, von außen nach innen (Oberseite: der erste Ring in der Luft neben dem Rohteil) oder einmal über die Rampe rundum und von innen nach außen (Tasche), eingetaucht nur im Freien, sonst tangential oder quer aus dem Freien hinein, Gleichlauf oder Gegenlauf; zwei Varianten gerechnet, die schnellere zählt; Operation `raeumen.Raeumen`; im Assistenten der Block „Räumen“ und der erste Wettbewerb der Strategien (Grundsatz 0): Planfräsen und Räumen rechnen beide, die schnellere bekommt den Haken, beide Zeilen sagen, um wie viel. Gemessen mit dem Standardfräser: Manuels 50 × 50 mit Zapfen 2,8 min statt 4,8 (Planfräsen), die Platte 33,3 statt 39,3, die Tasche 0,75 statt 3,0 (Kontur), Rechenzeit etwa eine Sekunde; die Simulation im Quader findet nichts im Teil und nichts stehen geblieben (-25); 0.44.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Der Prüfstand für Werkzeugwege (Manuel: „die Werkzeugwege müssen sinnvoll sein und immer zum kürzesten Bearbeitungsergebnis führen … Finde einen Weg, das sicherzustellen“): `pruefstand.py` und `tests/test_pruefstand.py` rechnen jede 2,5D-Strategie in jeder Variante mit dem Standardfräser an vier Maßstabsteilen, fahren sie im Quader ab und urteilen – nirgends ins Teil, nichts stehen geblieben, im Eilgang nichts abgetragen, nicht zu viel Luft –, keine Bahn darf langsamer werden als ihre Bestmarke (`tests/bestmarken.json`); er fand gleich drei Fehler, alle behoben (die Wandfahrt des Planfräsens quer durch den Zapfen, Abtrag im Eilgang beim Einfahren, Zwickel ohne Eingang) (-26). Die Morph-Spirale (Manuel: „im Viereck fahren anfangen, aber immer runder werden, so dass er am Ende nur um den Zapfen fährt“): ein harmonisches Feld zwischen Rohteil und Insel gibt die Ringe, ihr Abstand folgt dem Eingriff (nirgends mehr Material unter dem Fräser als beim geraden Schnitt mit ae), der letzte Ring ist der genaue Kreis um den Zapfen, alle Ringe eine Spirale ohne Absetzen – auf Manuels 50 × 50 2,69 min (Ringe um den Rest 2,75, Planfräsen 4,8), eine Einfahrt, keine Rampe. Der Prüfstand fand dabei, dass Oberseite und Taschenboden in einer Operation 20 mm ins Teil fuhren (jetzt eine Hüllfläche je Höhe, auch im Planfräsen). Im Assistenten rechnet er bei Oberseite und Taschenwand die Folgen – Planfräsen und Räumen der Böden gegen Räumen über alles – und die Kontur fährt nach dem Räumen nur noch das Aufmaß an der Wand; die Platte gesamt 34,7 min (Untergrenze 31) (-27); 0.45.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Gleichlauf richtig herum: Bei rechtsdrehender Spindel (M3) liegt im Gleichlauf das Material rechts der Fahrtrichtung (wie G41) – um einen Zapfen im Uhrzeigersinn, in einer Tasche gegen ihn; Kontur und Räumen fuhren bisher andersherum, also im Gegenlauf; jetzt richtig, Hilfe, Tooltips und Spezifikation (Grundsatz 4) nachgezogen; dabei den Ring um die Insel des Räumens in dieselbe Richtung gedreht (-28). Bohrung fräsen (W-006 S3g): zylindrische Bohrungen mit einem Schaftfräser, kleiner als sie – Helix hinab mit G2/G3 und Z, große Bohrungen in Lagen mit Ringen nach außen, die Wand in einem Zug mit Halbkreisen aus der Mitte, durchgehende 0,5 mm tiefer; Operation, Block im Assistenten mit „Bohrung Ø 20, durchgehend“ in der Liste und dem Wettbewerb gegen die Kontur (am Block mit zwei Bohrungen 1,33 min gegen 5,05); Räumt das Räumen den Boden schon (Platte), tritt sie nicht an. Der Prüfstand bekam das Bohrungsteil und fand gleich einen alten Fehler der Kontur (der Eilgang hinab streifte in kleinen runden Bohrungen Material) (-29); 0.46.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Bohren aus dem Assistenten (S3g): FreeCADs Bohr-Operation mit dem Bohrer aus der Werkzeugverwaltung, der den Durchmesser der Bohrung hat – nur durchgehende Bohrungen (eine Sackbohrung mit ebenem Grund kann ein Bohrer nicht), die Spitze unter den Grund, G81 oder in Hüben G83; im Assistenten der Block „Bohren“ (nur Bohrer zur Auswahl, der passende vorgewählt) und der Wettbewerb zu dritt: Bohren, Bohrung fräsen und Kontur auf denselben Bohrungen, die schnellste bekommt den Haken (-30); 0.47.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Gewinde bohren aus dem Assistenten (S3g): FreeCADs Gewinde-Operation (G84, links G74) mit dem Gewindebohrer, dessen Kernloch die Bohrung hat (M10 × 1,5 in Ø 8,5) – durchgehend um den Anschnitt hinaus, in einer Sackbohrung eine Steigung über dem Grund, je Tiefe eine Operation (FreeCAD fährt alle Löcher einer Operation gleich tief; beim Bohren jetzt genauso); den Haken setzt man selbst, das Kernloch macht der Wettbewerb davor. Dabei: Hübe beim Bohren erst ab 3 × D im Material (die Luft über dem Rohteil zählte mit – Ø 8,5 durch 20 mm bohrte in Hüben), ein roter Block verliert seinen Haken, wenn eine andere Strategie die Bohrung kann, rote Sätze mit Komma („Ø 8,5“ statt „Ø 8.50“) (-31); 0.48.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Entgraten im Quader (W-006 4.1 Punkt 8): eine eigene Operation mit dem Fasenfräser – die Oberkanten gewählter Wände, oder bei einer gewählten Fläche oben ihre Kanten, an denen eine Wand hinab geht (Außenkanten, Ränder von Taschen und Bohrungen); die Bahn so weit neben der Wand, dass der Kegel die Fase genau so breit schneidet (wie FreeCADs Deburr), im Gleichlauf, tangential hinein und heraus, vor Absätzen angehalten; im Assistenten der Block „Entgraten“ (Haken von Hand); das Prüffenster lässt die Fase durch (-32); 0.49.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Alle 51 Szenarien in 1.1.3 durchlaufen, alle grün – sechs waren veraltet (Werkstoff je Zeile seit 0.39.0, neue Vorschläge im 4-Achs-Assistenten, neun Befehle in der Leiste) und sind nachgezogen (-33). Zentrieren (NC-Anbohrer, oben Ø Bohrung + 0,4) und Senken (Kegelsenker in die Senkungen des Modells, in der Liste „Senkung Ø 12,4, 90°“) aus dem Assistenten; die Namen der Operationen bleiben eindeutig („Bohren T2 (2)“ statt FreeCADs „Bohren T001“); das Prüffenster rechnet Bohrer, Anbohrer und Senker als Kegel und die Zeit von G93-Spiralen ohne Anhalten je Satz – sie war siebenmal zu lang (-34); 0.50.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Restmaterial an Wänden: ein kleinerer Fräser fährt nur, wo sein Kreis aus dem Weg des großen ragt (Ecken innen, enge Stellen) – nach Ø 12 bleibt in einer scharfen Ecke R 6, nach Ø 4 R 2; im Assistenten der Block „Restmaterial“, der Ø davor von der Kontur (-35); 0.51.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Gewinde fräsen: eine eigene Operation mit dem Gewindefräser – welches Gewinde, sagen Kernloch und Steigung (ISO 965, 6H: Ø 8,5 mit 1,5 → M10 × 1,5), auf die Mitte der Toleranz gefräst, Halbkreis hinein, Helix, Halbkreis heraus, Gleichlauf; der Vorschub gilt an der Schneide (FreeCADs Gewindefräsen fährt ihn mit der Mitte – an der Schneide fast das Fünffache); ein Fräser mit zehn Zähnen braucht einen Umlauf statt neun; im Assistenten der Block „Gewinde fräsen“, er und „Gewinde bohren“ schließen sich aus; das Prüffenster lässt das Gewinde in seinem Ring durch. Dabei: Der Satz der Kontur hing seit 0.51.0 auch am Restmaterial (-36); 0.52.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Sackbohrungen mit Bohrspitze: Die Erkennung hielt Senkungen für Zylinderkopfschrauben und jede Sackbohrung aus FreeCADs „Bohrung“ (118°-Spitze) für durchgehend – „Bohrung fräsen“ und „Gewinde fräsen“ wären dort unter den Grund gefahren; jetzt mit Boden, der Winkel der Spitze gemerkt, und „Bohren“ bohrt solche Sackbohrungen mit einem Bohrer ihres Winkels bis genau zur Spitze des Modells (-37); 0.53.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Gezeichnete Fasen: Hat das Modell die Fase schon (FreeCADs „Fase“), fräst „Entgraten“ sie mit dem Fasenfräser genau – Breite und Winkel aus dem Modell, der Kegel liegt auf ihr; die Fläche oben anklicken genügt, der Haken ist vorgeschlagen (-38); 0.54.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Verrunden: Entgraten nimmt auch den Radienfräser – er rundet scharfe Kanten mit seinem Radius und fräst gezeichnete Rundungen (FreeCADs „Verrundung“) genau, der passende Fräser ist vorgewählt; „entgraten“ darf jetzt in der Kollisionsprüfung ins fertige Teil (-39); 0.55.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Alle 57 Szenarien auf 0.55.0 grün. Nut (W-006 4.1 Punkt 6): Langlöcher, eine Wand oder den Grund anklicken – nie in voller Breite mit ganzer Schneide: Helix, dann Kreise mit ae vorrückend (Trochoide, von Kreis zu Kreis hinten im Freien weiter), in einer kaum breiteren Nut eine Zickzack-Rampe mit höchstens D/2 in voller Breite und dem Vorschub für den dicken Span; zuletzt die Wand rundum; im Assistenten gegen Räumen (am Grund, Räumen meist schneller) und Kontur (an den Wänden, die Nut schneller); in der Liste „Nut 20 × 50, Grund 10“. Dabei gefunden, offen: Räumen lässt in Nuten 0,75 statt 0,3 mm an der Wand (-40); 0.56.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Reiben: FreeCADs Bohren mit G85 und der Reibahle im Ø der Bohrung, durchgehend 1 mm unter den Grund, mit Bohrspitze bis zum Grund der Wand; mit dem Haken bohrt „Bohren“ 0,15 bis 0,5 mm kleiner vor, „Bohrung fräsen“ und Kontur treten dort nicht an (-41); 0.57.0 – fertig und automatisch geprüft; wartet auf Manuels Test. 3D-Schlichten (W-006 4.2 Punkt 3, die erste 3D-Strategie): Freiformflächen in parallelen Zeilen mit dem Kugelfräser, die Spitze auf der Hüllfläche des ganzen Teils, gefräst nur, wo die gewählten Flächen die Höhe bestimmen, der Zeilenabstand aus der Grathöhe, längs X und Y gerechnet, die schnellere zählt; an einer Kuppel im Quader auf 0,02 mm fertig, nichts ins Teil (-42); 0.58.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Steil/Flach im 3D-Schlichten (W-006 4.2 Punkt 4): wo die Fläche steiler ist als 45°, Höhenlinien von oben nach unten im Gleichlauf statt Zeilen – an der Flanke einer Halbkugel 0,026 statt 0,056 mm Grat (-43); 0.59.0 – fertig und automatisch geprüft; wartet auf Manuels Test. Räumen lässt an Taschenwänden genau das Aufmaß stehen (0,3 statt 0,75 mm – der letzte Ring an der Wand genau, wie schon um Inseln); die Tasche des Prüfstands 0,1 min länger, die alte Bestmarke war zu schnell, weil Material stehen blieb (-44); 0.59.1 – fertig und automatisch geprüft; wartet auf Manuels Test. **3D-Schruppen** (W-006 4.2
Punkt 1): das Rohteil über Freiformflächen in Lagen mit vollem ap wie das Räumen, dazwischen
Zwischenlagen (1 mm) nur, wo über der Fläche noch Material steht – an der Kuppel Ø 40 1 Lage und
9 Zwischenlagen, 5,4 min, auf der Kuppel 0,4 … 1,6 mm stehen (-45); 0.60.0 – fertig und
automatisch geprüft; wartet auf Manuels Test. **Bleistift** (W-006 4.2 Punkt 6): die Kehlen
nachfahren, wo die Kugel zwei Flächen zugleich berührt – aus dem Knick der Hüllfläche; an der
Kuppel ein Ring bei r 21,45, 0,2 min (-46); 0.61.0 – fertig und automatisch geprüft; wartet auf
Manuels Test. **Offene Nuten**: zum Rand hin offen (an einem oder beiden Enden), von außen in
der Luft hinein ohne Helix, die Wände im Gleichlauf – Nut 16 × 60, 8 tief, 0,85 min (Kontur 2,2);
dabei gefunden: Räumen schnitt auf dem Grund einer Nut zuerst in voller Breite (nur scheinbar
schneller) – an Nutgründen treten Räumen und Planfräsen nicht mehr an (-47); 0.62.0 – fertig
und automatisch geprüft; wartet auf Manuels Test. **3D-Schlichten als Spirale**: von der Mitte
nach außen ohne Wenden, neben Zeilen längs X und Y gerechnet (nur mit Steil/Flach, sonst wären
die Grate an Flanken höher) – die Kuppel 3,97 statt 4,51 min (-48); 0.63.0 – fertig und
automatisch geprüft; wartet auf Manuels Test. **Nie in voller Breite**: Der Prüfstand misst jetzt
den Eingriff je Satz (Breite aus Abtrag und Tiefe) und lässt eine Bahn durchfallen, die mehr als
5 mm in voller Breite schneidet – er fand, dass mehrere Bestmarken darauf standen: Räumen biss
mit dem Rechteck in Inseln (Platte 120 mm, 20 tief; jetzt Ringe aus dem Weg um die Inseln
herum), sein letzter Ring lief am Absatz voll an der Wand, die erste Zeile des Planfräsens griff
0,8 · Ø breit (jetzt höchstens so breit, dass Breite · Tiefe nicht über ae · ap liegt; vor einer
Wand flachere Lagen), das 3D-Schruppen erbte den Biss in die Kuppel (4,8 ae, jetzt 1,6). Ehrlich
gerechnet etwas langsamer: Platte gesamt 35,6 statt 34,8 min (-49); 0.64.0 – fertig und
automatisch geprüft; wartet auf Manuels Test. **Restschlichten** (W-006 4.2 Punkt 8): mit dem
kleineren Kugelfräser nur dort, wo der große davor nicht hinkam – aus den Flächen, die beide
stehen lassen; an der Kuppel nach Ø 6 mit Ø 2 3,8 min statt 9,1 für alles, in der Kehle 0,18 statt
0,44 mm (P-2026-10-02-01); 0.65.0 – fertig und automatisch geprüft; wartet auf Manuels Test.
**Restschruppen** (W-006 4.2 Punkt 2): mit dem kleineren Fräser nur, was der große beim
3D-Schruppen stehen ließ – aus seiner Hüllfläche; zwischen zwei Kuppeln 0,28 min, das Tal 62 statt
138 mm³; dabei der Morph des Räumens bei zwei Inseln nicht mehr fast endlos (P-2026-10-02-02);
0.66.0 – fertig und automatisch geprüft; wartet auf Manuels Test. **Fläche entlang**
(Flowline, W-006 4.2 Punkt 7): die vierte Richtung des 3D-Schlichtens – die Bahnen folgen den
Kurven der Fläche, im Raum überall einen Zeilenabstand auseinander; an der Kuppel 4,29 statt
4,93 min (Spirale), an einer Walze 7,2 statt 10,3 (Zeilen). Dabei behoben: An der Außenkante
eines Teils schnitten Höhenlinien und Spirale 0,05 mm in die Seite – jetzt fährt das
3D-Schlichten nur, wo der Fräser die Flächen berührt (P-2026-10-02-03); 0.67.0 – fertig und
automatisch geprüft; wartet auf Manuels Test. **Äquidistant** (W-006 4.2 Punkt 5): die fünfte
Richtung – Ringe vom Rand nach innen, im Raum überall einen Zeilenabstand auseinander, über alle
gewählten Flächen, mit einem Gang über flache Grate; an der Kuppel der feinste Rest (0,017 statt
0,020 mm), die Zeit gewinnt dort weiter die Fläche entlang (P-2026-10-02-04); 0.68.0 – fertig
und automatisch geprüft; wartet auf Manuels Test. **Passfedernut** auf der Drehmaschine mit C
und Y: Der Grund einer Nut auf der Welle bekam mit „Plan indexiert“ mit dem Fräser in Nutbreite
gar keine Bahn, mit einem schmaleren blieben die Enden 4 mm stehen – jetzt fräst es sie wie die
„Nut“ im Quader (Rampe in voller Breite oder Trochoide, die Wand rundum) bis an die Enden; „Auf
der Maschine prüfen“ meldet am Nutgrund nicht mehr fälschlich „im Teil“ (P-2026-10-02-05);
0.69.0 – fertig und automatisch geprüft; wartet auf Manuels Test. **Querbohrungen** auf der
Drehmaschine: eine Bohrung quer zur Stange anklicken – „Plan indexiert“ fräst sie in der Helix,
quer versetzt mit dem Y, durchgehende von beiden Seiten (P-2026-10-02-07); 0.70.0 – fertig und
automatisch geprüft; wartet auf Manuels Test. **Radial bohren**: Gibt es einen Bohrer mit dem
Durchmesser der gewählten Querbohrungen, wählt „Plan indexiert“ ihn vor und bohrt sie radial
(tiefer als 3 × D in Hüben; durchgehende von beiden Seiten je mit der Spitze über die Mitte,
Sackbohrungen nur mit gezeichneter Spitze) – „Radial bohren T2“; „Auf der Maschine prüfen“ kennt
die Spitze als Grund (P-2026-10-02-08); 0.71.0 – fertig und automatisch geprüft; wartet auf
Manuels Test. **Nut auf dem Mantel**: den Grund einer Nut um die Stange anklicken – „Plan
indexiert“ fräst sie mit drehender Rundachse, in voller Breite mit der Rampe, breiter in Zeilen
(„Rundum schruppen“ kam mit dem Fräser in Nutbreite gar nicht hinein; P-2026-10-02-09); 0.72.0
– fertig und automatisch geprüft; wartet auf Manuels Test. **Fräser und Bohrer zugleich**: Sind
neben Flächen oder Nuten auch Querbohrungen gewählt und gibt es einen Bohrer ihres
Durchmessers, legt „Plan indexiert“ zwei Operationen in denselben Job an („Plan indexiert T1“,
„Radial bohren T2“; P-2026-10-02-11); 0.73.0 – fertig und automatisch geprüft; wartet auf Manuels
Test. **Flansch**: Bohrungen verschiedener Durchmesser zugleich – „Bohren“ nimmt, was sein
Bohrer bohrt, „Bohrung fräsen“ den Rest (vorher ging „Anlegen“ gar nicht; P-2026-10-02-12);
0.74.0 – fertig und automatisch geprüft; wartet auf Manuels Test. **Deckel**: Ein roter Block
(„Bohrung fräsen“ an Bohrungen, die der Bohrer bohrt) verliert jetzt auch dann den Haken, wenn
die Kontur andere Wände hat – „Anlegen“ ging sonst nicht (P-2026-10-02-13); 0.75.0 – fertig und
automatisch geprüft; wartet auf Manuels Test. **Formplatte**: Freiformflächen neben Oberseite und
Bohrungen bekommen jetzt 3D-Schruppen und 3D-Schlichten (vorher keine Operation;
P-2026-10-02-14); 0.76.0 – fertig und automatisch geprüft; wartet auf Manuels Test.
**Lagerbock**: Die Kontur fährt gebohrte Bohrungen nicht mehr mit (P-2026-10-02-15); 0.77.0 –
fertig und automatisch geprüft; wartet auf Manuels Test. **Höhe 0** statt „-5,6e-18“ in der Flächenliste (P-2026-10-02-16); 0.78.0. **Absatz**: Die Kontur fährt nur den Rest, den das
Planfräsen an der Wand lässt, statt 12 Bahnen durch Luft (P-2026-10-02-17); 0.79.0 – fertig und
automatisch geprüft; wartet auf Manuels Test. **Planfräsen bis an die Wand**: An einer Wand längs
der Zeilen blieben 0,5 mm stehen, jetzt fährt eine Zeile an ihr entlang (P-2026-10-02-18); 0.80.0
– fertig und automatisch geprüft; wartet auf Manuels Test. **Restmaterial von selbst** (Manuel:
„Ja“): Sind gezeichnete Rundungen innen kleiner als der Fräser der Kontur und ist ein kleinerer da,
hakt der Assistent „Restmaterial“ an (P-2026-10-02-19); 0.81.0 – fertig und automatisch geprüft;
wartet auf Manuels Test. **M3 und M4** (Manuel: „Die kann beide Richtungen“): Steht der
Werkzeug-Controller auf „Reverse“, fräsen alle 2,5D- und 3D-Bahnen mit Gleichlauf weiter im
Gleichlauf – gespiegelt (P-2026-10-02-20); 0.82.0 – fertig und automatisch geprüft; wartet auf
Manuels Test. **Planfräsen übereinander**: Die obere Fläche fräst nicht mehr die ganze Platte ab,
wo der Boden derselben Operation ohnehin am Rohteil beginnt – Zapfen 15,6 → 13,5 min, Absatz
5,1 → 4,3 min (P-2026-10-02-21); 0.83.0 – fertig und automatisch geprüft; wartet auf Manuels
Test. **Offene Nut in Bögen** (Manuels Halbkreis): je Schritt ein Halbkreis im Gleichlauf von Wand
zu Wand, quer zurück im Schnellvorschub, am Anfang Morph-Bögen vom geraden Rand; der Schritt so
klein, dass der Fräser die Delle nicht weiter umschlingt als eine gerade Wand mit ae; offene Nuten
jeder Breite (P-2026-10-02-22); 0.84.0 – fertig und automatisch geprüft; wartet auf Manuels Test.
**4-Achs-Gleichlauf über C** (Manuel: „es geht um alle Maschinen“): im Rahmen des Teils aus
Werkzeugachse, Fahrt und Materialseite gerechnet (`spindel.ist_gleichlauf`); Spiralen,
Mantelnut-Wände, Querbohrung und Passfedernut drehen φ mit M3 und M4 richtig, C über den Drehsinn
der Maschine (P-2026-10-02-23); 0.85.0 – fertig und automatisch geprüft; wartet auf Manuels Test.
**Nur im Gleichlauf** (Manuel: „auswählbar, ob er abhebt und wieder von vorne anfängt“): Haken bei
Planfräsen und Plan indexiert – jede Zeile im Gleichlauf, abheben, von vorne (P-2026-10-02-24);
0.86.0 – fertig und automatisch geprüft; wartet auf Manuels Test. **Rundum entgraten im
Gleichlauf**: je Kante die Seite des Materials aus den beiden Flächen, die Richtung jedes Stücks
danach (P-2026-10-02-25); 0.87.0 – fertig und automatisch geprüft; wartet auf Manuels Test.
Den Haken „nur im Gleichlauf“ auch bei „Rundum schruppen“ mit gewählten Flächen
(P-2026-10-02-26); 0.88.0 – fertig und automatisch geprüft; wartet auf Manuels Test.
**Geschlossene Nut**: hinten, wo jeder Kreis durch schon freie Luft läuft, im Schnellvorschub –
1,84 → 1,69 min an der Prüfplatte (P-2026-10-02-27); 0.89.0 – fertig und automatisch geprüft;
wartet auf Manuels Test.
Als Nächstes: der Einstieg (Rampe/Helix/senkrecht) nach Zeit, Startstelle und Reihenfolge der Bereiche, Spannhöhe; die Bahnrechnung weiter beschleunigen (Rest über Stücke, mit neuen goldenen Bahnen); F2 (Nummer am Werkzeug freiwillig); W-005 Programm für jede Steuerung (Plan P-2026-09-30-42/-43, wartet auf seine E1–E7). Offen danach: V2b (Drehteile), V6, V7.
- **Zuletzt geprüfte FreeCAD-Versionen:** 1.1.3 (stabil) und Wochen-Build
  26.3.0 dev (2026-09-16) – alle Prüfungen und Szenarien grün; in 1.1.3 ist
  der Export übersprungen (gibt es dort nicht). Im Lauf zu 0.33.1 stürzte 26.3
  einmal beim Schließen des 4-Achs-Fensters ab (`closeDialog`, FreeCAD selbst);
  zweimal wiederholt ohne Befund – bleibt im Blick. **1.1.4** (Manuel nutzt sie
  seit 2026-09-29): Quelltext gegen 1.1.3 verglichen – nichts in CAM,
  Assembly, PartDesign oder den Python-Schnittstellen des Addons
  (P-2026-09-29-01); der volle Lauf (Arbeitsregeln, Abschnitt 9) folgt, sobald
  conda-forge 1.1.4 hat.

## Nächster Schritt (konkret)

**Geplant nach Manuels erstem Test (2026-09-26) – Reihenfolge A → B → C, Stufe A in Arbeit:**

*Stufe A – Werkzeugverwaltung verfeinern*
1. **Werkzeugname** neben der Nummer (Option A): frei, wie an der
   Maschine (Leerzeichen bleiben). Leer gilt ein Name aus den Angaben,
   grau gezeigt: „Schaftfräser T1 VHM D12 L30“ (Zahlen mit Punkt). Name in
   Liste, Suche, als Werkzeugname in CAM, im Namen des Werkzeug-Controllers
   („T1 Fräser VHM 12 – Schruppen“); „Aus CAM übernehmen“ füllt ihn;
   doppelte Namen: Hinweis, erlaubt. NC-Aufruf `T="…"` nur mit eigenem
   Postprozessor (FreeCADs rufen per Nummer). – *Fertig, 0.12.0
   (P-2026-09-26-33).*
2. **Neues Werkzeug mit Beispielwerten:** grau gezeigt, aber gültig
   (Manuel: wer Ø 12 stehen lässt, will Ø 12), Durchmesser 12; das Bild
   zeigt gleich die Form, beim Durchblättern immer. – *Fertig
   (P-2026-09-26-37), mit grauen Beispielen für vc und Spandicke im
   Planer.*
3. **Planer:** Warngrenze ae 10 % von D bleibt Vorgabe (fest, egal wie
   viele Schneiden, Manuel), am Werkzeug änderbar; Zeilen darüber rot
   „mehr als deine Warngrenze“, aber wählbar; % je Zeile sichtbar. –
   *Fertig (P-2026-09-26-40).*
4. **Eingriffsbild:** Überschriften „ae – seitliche Zustellung (von
   oben)“ / „ap – Zustelltiefe (von der Seite)“, Text je Größe eine Zeile.
   – *Fertig (P-2026-09-26-41).*
5. **ae und ap wahlweise in mm oder % von D** (ein Umschalter über der
   Tabelle, intern mm, Wahl gemerkt). – *Fertig (P-2026-09-26-42).*
6. **Bohrer: Spitzenwinkel** (fehlt, Manuel) – Feld, Bild, an CAM als
   Spitzenwinkel des Bohrers; die Schneidenzahl bleibt (f je Umdrehung).
   – *Fertig (P-2026-09-26-43). Stufe A damit komplett.*

*Zwischendurch – zum Ausprobieren (nach A2, vor A3)*
7. **Beispielmaschine laden:** Die Meldung „Hier gibt es noch keine
   Baugruppe“ in „Maschine bearbeiten“ und „Maschine verfahren“ bekommt
   den Knopf „Beispielmaschine laden“ (Manuel: wer das Addon ausprobiert,
   soll nicht erst eine Maschine bauen müssen). Er öffnet ein neues
   Dokument mit einer fertig eingerichteten Maschine und gleich danach den
   Dialog. Grundlage: der Baukasten aus `tests/beispielmaschinen.py`. –
   *Fertig (P-2026-09-26-38): Dreiachs-Fräsmaschine, Baukasten jetzt in
   `camaddon/beispielmaschine.py`.*
7b. **Beispielmaschinen zur Auswahl** (Manuel nach dem ersten Ausprobieren,
   2026-09-26): „Beispielmaschine laden“ bietet die üblichen Sorten an –
   Schrägbett-Drehmaschine mit Y-Achse (CLX-ähnlich; Z = Hauptspindel;
   Revolver mit zwei angetriebenen Fräswerkzeugen: axial, bearbeitet in
   Z-Richtung, und radial, 90° dazu), 3-Achs-Fräse, 5-Achs Tisch/Tisch
   (A/C, Schwenkbrücke mit Rundtisch), 5-Achs Kopf/Kopf (A/B), 5-Achs
   Kopf/Tisch (B am Kopf, C am Tisch). Nach Stufe B. – *Fertig
   (P-2026-09-26-62): „Beispielmaschine laden …“ bietet die fünf Bauarten
   mit je einem Satz dazu an; die Auswahl merkt sich die zuletzt geladene.*
7c. **Update auf Knopfdruck** (Manuel: nicht jedes Addon soll beim Start
   suchen): Knopf „Nach Updates suchen“ in der Werkzeugleiste; die Suche
   beim Start ist ab Werk aus, in den Einstellungen einschaltbar. –
   *Fertig (P-2026-09-26-50).*

*Stufe B – Einheiten und Zahlenformat*
8. Beim ersten Start (mit der Sprache) und in den Einstellungen des
   Addons: **Maßsystem** mm oder inch und **Dezimaltrennzeichen** , oder
   . – mit Beispielzahlen, vorbelegt aus FreeCADs Einstellungen
   (Einheitensystem, Zahlenformat). – *Fertig (Dezimalzeichen
   P-2026-09-26-45, Maßsystem P-2026-09-26-48).*
9. Überall in der gewählten Einheit anzeigen und eingeben (mm/inch,
   m/min/SFM, mm/min/ipm, cm³/min/in³/min), Umschalter in der
   Werkzeugverwaltung; intern metrisch – verlustfrei, 1 in = 25,4 mm, 1/2"
   bleibt 0,5 in. Eingabe nimmt Punkt und Komma (*fertig,
   P-2026-09-26-45*). – *Fertig (P-2026-09-26-48); Beschleunigung, Ruck
   und Werkstoffdaten bleiben metrisch.*

*Stufe C – Werkzeugarten wie in InventorCAM (eigene Spezifikation zuerst)*
10. Arten: Schaft-, Kugel-, Torus-, Konik-, Schwalbenschwanz-,
   Lollipop-, Fasen-, Radien-, Plan-, Nuten-, Form-, Gewindefräser;
   Bohren, Zentrierbohrer, NC-Anbohrer, Gewinde rechts/links, konische
   und zylindrische Senkung, Reibahle, Bohrstange, Ausbohren/Spindeln;
   Universal-Drehen, Einstechen, Gewinde (Drehen); Antasten. Drehwerkzeuge
   gleich mit (Schnittwerte für später – FreeCAD 1.1.3 dreht nicht). Je Art: Maße,
   Bild, Einsätze, was CAM davon kennt. Achtung: Das heutige
   „Radiusfräser“ ist ein Kugelfräser – umbenennen; „Radienfräser“ ist eine
   andere Art. – *Spezifikation: `docs/spezifikation_werkzeugarten.md`
   (P-2026-09-26-53), sechs Stufen, Abschnitt 8. Auf Manuels Wunsch vor
   Punkt 7b („ne, mach mal Werkzeugarten weiter“); 7b liegt fast fertig
   im Stash „WIP Beispielmaschinen zur Auswahl“.* – *Fertig
   (P-2026-09-26-54 bis -60): Kugelfräser statt „Radiusfräser“, alle 26
   Arten mit ihren Feldern, Bilder (auch in der Auswahl), Einsätze und
   Rechnen je Art, Übergabe an und Übernahme aus CAM für alle Arten (CAM
   baut denselben Körper wie das Bild), die neuen Einsätze auf die
   passenden Operationen im Job.*

*Schräge Achse (W-001 Stufe 3b, Manuel 2026-09-26)*
11. **Schrägbett mit schräger Y-Achse:** Fährt der Y-Schlitten schräg zum
   X-Schlitten, rechnet die Steuerung ein rechtwinkliges Y auf beide um
   (Siemens TRAANG) – für Y fahren beide. Eintrag „Schräge Achse“ in
   „Maschine bearbeiten“ (Winkel eintragen, die Baugruppe folgt),
   Erkennung, „Maschine verfahren“ wie im Programm, Übergabe an CAM,
   Höchstvorschub; danach eine Vorlage mit Eingabemaske. – *Spezifikation:
   Abschnitt 7c und Stufe 3b in
   [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
   (P-2026-09-26-65), sieben Schritte. Schritt 1 fertig (P-2026-09-26-66:
   Bereich „Transformationen“ mit „+ Schräge Achse“, Winkel aus der
   Baugruppe, Bild, Beispiel), Schritt 2 fertig (-67: Winkel eintragen, die
   Führung dreht sich mit), Schritt 3 fertig (-68: Hinweis „Y1 steht 30,0°
   schräg zu X1“, ein Klick legt an), Schritt 4 fertig (-69: „Maschine
   verfahren“ wie im Programm, am Anschlag eine rote Zeile), Schritt 5
   fertig (-71: an CAM rechtwinklig, Grenzen und Eilgang umgerechnet),
   Schritt 6 fertig (-72: Höchstvorschub beim Planen), Schritt 7 fertig
   (-75: Befehl „Neue Maschine …“, Maße der Drehmaschine). Stufe 3b damit
   komplett.*

*4-Achs-Bearbeitung (W-003, Manuel 2026-09-26)*
12. **Teil in eine runde Stange, rundum schruppen und schlichten:**
   Stirnfläche anklicken → das Teil sitzt mittig vorne in der Stange (z. B.
   Ø 80); Flächen anklicken („alle Mantelflächen“, ein außermittiger
   Zylinder); aus Fräser und Stange entstehen Schrupp- und Schlichtbahn –
   egal ob A, B oder C, auch auf einer Drehmaschine mit C und Y. Assistent in
   vier Schritten, eigener Rechenkern (1.1.3 und Wochen-Build), Ausgabe als
   reine Achskoordinaten, alles einstellbar mit Vorschlägen. –
   *Spezifikation: [spezifikation_vierachs.md](spezifikation_vierachs.md)
   (P-2026-09-26-78), Stufen in Abschnitt 13. V1 „Teil in die Stange“, V2a,
   V2c und V3 „Rundum schruppen“ fertig (P-2026-09-26-79, P-2026-09-27-37,
   -38, -45 bis -54); nach Manuels Test V2b „Drehteile“ und V4 „Flächen
   wählen“.*

*Werkzeugbahn auf der Maschine (W-001 Stufe 4a, Manuel 2026-09-26)*
13. **Reicht der Verfahrweg?** Job wählen → „Auf der Maschine prüfen“ →
   „Alle Achsen bleiben in ihren Grenzen.“ oder je Überschreitung ein Satz
   („X1 fährt in *Tasche* bis 312,00 mm, die Grenze ist 250,00 mm“); ein
   Klick fährt die Maschine dorthin. Manuels Entscheidungen: die Bahn im
   Job, Nullpunkt am LCS der Werkstückaufnahme plus Verschiebung je Job,
   eigenes Feld „Länge ab Spindelnase“, 4a zuerst. – *Spezifikation:
   [spezifikation_simulation.md](spezifikation_simulation.md), Abschnitte
   5, 6 und 10 (P-2026-09-26-83), vier Schritte: Rechenkern, Fenster,
   Länge ab Spindelnase, Version. Schritt 1 fertig (P-2026-09-26-84:
   `reichweite.py`, an allen Beispielmaschinen nachgemessen), Schritt 2
   fertig (-85: Befehl und Fenster, Klick fährt hin), Schritt 3 fertig
   (-86: „Länge ab Spindelnase“ in der Werkzeugverwaltung), Version 0.22.0
   (-87). Stufe 4a damit komplett. **4b „Abfahren“** – die Maschine fährt
   die Bahn sichtbar ab, mit Werkzeug, Rohteil und Bahn – spezifiziert
   (P-2026-09-26-88, Entscheidungen von Claude zur Besprechung); Schritt 1
   fertig (-89: `abfahren.py`, Zeiten gegen Handrechnung), Schritt 2 fertig
   (-90: Abspieler im Fenster, Körper in der 3D-Ansicht der Maschine),
   Version 0.23.0 (-91). Stufe 4b damit komplett. **4c „Kollision“** –
   Manuels Entscheidungen (P-2026-09-26-93): eigene Halter-Verwaltung
   ([spezifikation_halter.md](spezifikation_halter.md): Kontur aus
   Zylindern und Kegeln, eigenes Fenster, Länge ab Spindelnase gemessen,
   sonst geschätzt), geprüft gegen fertiges Teil und Spannmittel, gemeldet
   Berührung und Warnabstand. Halter fertig (P-2026-09-26-94 bis -96:
   Datenmodell, Fenster „Halter“, Länge und Anzeige), 4c fertig (-97:
   `kollision.py`, -98: Bereich „Kollision“ im Fenster), Version 0.24.0
   (-99). Stufe 4c damit komplett; 4d (Bearbeitungszeit mit Beschleunigung)
   bleibt Entwurf.*

**Manuel probiert aus** – alles ist in 1.1.3 und im Wochen-Build
automatisch geprüft, aber gesehen hat es nur Claude als Screenshot. Vorher
das Repository öffentlich stellen (T-005), dann installiert die Zeile aus
dem README; oder wie bisher mit GitHub Desktop aktualisieren.

In dieser Reihenfolge (Klickwege in den Verlaufseinträgen):

1. **Werkzeugverwaltung** (Werkzeugleiste „CAM-Addon“): Hilfe (?) →
   „Schritt für Schritt: vom Katalog in den Job“ durchgehen – Werkstoff,
   Werkzeug (oder „Aus CAM übernehmen“), Einsätze, **„Schruppwerte
   planen…“** (P-2026-09-25-60, -73; Vergleich mit der Vollnut
   P-2026-09-26-04), „Strategien vergleichen“ mit allen Einsätzen (-05),
   Suche und Werkzeugbild (P-2026-09-25-71, P-2026-09-26-01), Kopieren
   und anderen Durchmesser eintragen (-06), Eintauchwinkel (-08), **Zeile
   kopieren** für Varianten (-12).
2. **Werkzeugarten** (P-2026-09-26-53 bis -60): In der Werkzeugverwaltung
   „Neu“ → „Art“ aufklappen: 26 Arten mit kleinen Bildern, gegliedert nach
   Fräsen, Bohren, Drehen, Antasten. Je Art andere Felder und ein anderes
   Bild (Gewindebohrer: Steigung statt Schneidenzahl), „+ Einsatz“ bietet
   nur, was passt. „Speichern und an CAM übergeben“ nennt, was CAM nur
   genähert kennt; in CAM unter Werkzeugbibliothek → „CAM-Addon“ steht jede
   Art mit ihrer Form. „Aus CAM übernehmen“ → „Default“ holt alle 13
   Werkzeuge. Im Job: Planfräser mit „Planen“ in eine Fläche →
   „Schnittwerte in den Job“ setzt Schrittweite und Zustelltiefe.
3. **CAM-Job:** „Schnittwerte in den Job“ → „Werkzeug-Controller
   hinzufügen“ (P-2026-09-25-65) → Operation **Adaptiv** auf eine Bohrung → noch einmal
   „Schnittwerte in den Job“ → Schrittweite, Zustelltiefe und Helixwinkel
   (P-2026-09-25-61, P-2026-09-26-08), dazu „Am Rohteil eintragen“
   (P-2026-09-25-72). Das ist der Weg „Loch auffräsen: einmal
   helikal eintauchen, dann ebenenweise mit voller Schneide“. Die Spalte
   zeigt die **Ebenen**; bei FreeCADs Rohteil (1 mm über dem Modell) meist
   „2 Ebenen (25 + 1 mm)“ mit rotem Hinweis, wie die dünne entfällt
   (P-2026-09-26-16). Basisgeometrie des Adaptivs: beim Sackloch der
   Boden, bei der Durchgangsbohrung die untere Kreiskante (Hilfe,
   P-2026-09-26-21); fehlt sie, sagt die Spalte „keine Bahn“ (-22). In der
   Hilfe dazu „Eine Außenkontur schruppen“ (P-2026-09-26-13).
4. **Maschine:** „Maschine bearbeiten“ (W-001 Stufen 1–2) und **„Maschine
   verfahren“** (Stufe 3, P-2026-09-25-67, Revolverplätze -69): Laufen die Achsen richtig
   herum, stimmt der Nullpunkt? In einem leeren FreeCAD bietet
   „Beispielmaschine laden …“ fünf fertige Maschinen zum Ausprobieren
   (P-2026-09-26-62) – etwa die Drehmaschine mit Revolver: T und C1
   verfahren, P1/P2 angetrieben von S3.
5. **Schräge Achse** (P-2026-09-26-65 bis -72): Beispiel-Drehmaschine →
   „Maschine bearbeiten“ → unter „Transformationen“ „+ Schräge Achse“ →
   Winkel 30 eintragen: In der 3D-Ansicht bleibt alles stehen, die
   Beispielzeile zeigt „Y +10,0 mm → Y1 +11,5 mm, X1 −5,8 mm“; mit der Maus
   auf dem Eintrag verweilen: X- und Y-Schlitten fahren zusammen hin und
   her. OK → „Maschine verfahren“ steht auf „wie im Programm“: Y auf 10 →
   beide Schlitten fahren; X auf 140, dann Y auf −40 → rote Zeile „… X1
   steht an seiner Grenze 150,00 mm“. Im Wochen-Build „An CAM übergeben“:
   der Bericht nennt die schräge Achse. Versteht man den Bereich ohne
   Erklärung? Dann **„Neue Maschine …“** (P-2026-09-26-75): Drehmaschine,
   Bettneigung 30°, Y schräg um 30°, 8 Plätze → „Maschine bauen“ → die
   Maschine steht im neuen Dokument, „Maschine bearbeiten“ zeigt die
   schräge Achse.
6. **4-Achs-Bearbeitung, Teil in die Stange** (P-2026-09-26-79): ein Teil mit
   ebener Stirnfläche öffnen (etwa eine Welle), die Stirnfläche anklicken →
   Werkzeugleiste „CAM-Addon“ → **4-Achs-Bearbeitung** → das Teil fährt in
   eine durchscheinende Stange und dreht sich einmal; Ø 80 eintragen →
   „Passt – rundum mindestens … mm“; „ganzes Teil möglichst mittig“ und
   Rundachse A/B/C umschalten (die Stange liegt in X, Y oder Z); „+90°“;
   „Anlegen“ → Job „… – 4 Achsen“ mit Zylinder-Rohteil, ein Strg+Z nimmt
   alles zurück. Versteht man das Fenster ohne Erklärung?
7. **Auf der Maschine prüfen** (P-2026-09-26-84 bis -86): „Neue Maschine …“
   → 3-Achs-Fräse bauen; ein Teil mit CAM-Job öffnen (etwa eine Tasche),
   den Job im Baum wählen → Werkzeugleiste „CAM-Addon“ → **Auf der
   Maschine prüfen** → das Fenster öffnet sich bei der Maschine, grün „Alle
   Achsen bleiben in ihren Grenzen.“; unter „Nullpunkt des Jobs“ bei X 300
   eintragen → rot eine Überschreitung von X1; draufklicken → der Tisch
   fährt an den Anschlag; Schließen → alles zurück, das Teil ist wieder
   vorn. In der Werkzeugverwaltung beim Werkzeug „Länge ab Spindelnase“
   eintragen (mit Halter) → der Hinweis zur Länge verschwindet, Z rechnet
   damit. Versteht man das Fenster ohne Erklärung, passt der Vorschlag für
   den Nullpunkt? **Abfahren** (P-2026-09-26-89, -90): im selben Fenster
   unter „Abfahren“ → in der Maschine liegen Rohteil (durchscheinend) und
   Teil auf dem Tisch, darauf die Bahn (Vorschub blau, Eilgang rot), das
   Werkzeug steckt in der Spindel; die **Lupe** neben dem Tempo holt
   Werkstück und Werkzeug heran (P-2026-09-26-92);
   **Abspielen** → die Maschine fährt, die Werkzeugspitze läuft die blaue
   Linie entlang, Satz, Zeit und Achswerte laufen mit; Tempo ×20; den
   Schieber ziehen; „einen Punkt zurück/weiter“; oben eine Operation wählen
   → Sprung an ihren Anfang. Mit X 300 auf die Überschreitung klicken → der
   Abspieler steht dort, X1 rot „am Anschlag“. Schließen → Werkzeug, Rohteil
   und Bahn sind weg, die Maschine steht wie vorher. Passen Zeit und Tempo,
   sieht man genug? **Halter** (P-2026-09-26-94 bis -96): Werkzeugverwaltung →
   ein Werkzeug → „Halter …“ → „Neu“ → „Spannzangenfutter ER32 · SK40“ → Liste,
   Kontur-Tabelle und Bild im Schnitt → OK → beim Werkzeug steht der Halter,
   die leere Länge ab Spindelnase zeigt grau „leer: … mit Halter“; im Abfahren
   steckt das Werkzeug in diesem Halter. **Kollision** (-97, -98): Die
   3-Achs-Fräse hat jetzt zwei Spanneisen. Ein kurzes Werkzeug (Gesamtlänge
   25 mm, ohne Halter) und eine Bahn dicht neben einem Spanneisen in die Tiefe
   → „Kollision prüfen“ → rot „Es stößt etwas an:“, „In „…“ berühren sich
   „Spindel“ und „Spanneisen_rechts“ …“ → Klick → die Maschine steht dort,
   eine rote Kugel zeigt die Stelle. Warnabstand 10 → gelbe Sätze dazu.
   Versteht man die Sätze, stimmen die Stellen?
8. **Besprechen:** Entscheidungen der Werkzeugverwaltung
   ([Spezifikation](spezifikation_werkzeugverwaltung.md), Abschnitt 11,
   Nr. 13–23 sind von dieser Nacht); zu Stufe 4b und 4c Claudes
   Einzelheiten ([Spezifikation](spezifikation_simulation.md), Abschnitt 5)
   und zu den Haltern ([Spezifikation](spezifikation_halter.md),
   Abschnitt 9, Nr. 4–7).

Danach: Manuel testet 4a–4c und die Halter (Punkt 7 oben); offen sind W-001 4d (Bearbeitungszeit mit Beschleunigung) und W-003 V2 (4-Achs: Achse von der Maschine).

Neu (2026-09-27): die Durchsicht **W-004** ([durchsicht_bedienbarkeit.md](durchsicht_bedienbarkeit.md)). Die kleinen Punkte D-01 bis D-08 sind erledigt (P-2026-09-27-09 bis -16), dazu auf Manuels Hinweis der Revolver der Beispiel-Drehmaschine mit Stationen und die Beispielmaschinen ohne Gelenkmarkierungen (P-2026-09-27-07, -08). In der empfohlenen Reihenfolge weiter (Manuel: „Besser weiter“): D-21 Job in allen offenen Dokumenten (-18), D-20 Maschine merken und selbst öffnen, Teil Prüffenster (-19), D-10 drei Urteile oben im Prüffenster (-20, -22), D-11 „T1 öffnen …“ an den Hinweisen (-21), D-25 Betriebsarten vorschlagen (-23), D-26 Maße der 3-Achs-Fräse (-24), D-30 unbenutzte fremde Controller entfernen (-26), D-12 „+ Einsatz“ beim neuen Werkzeug (-27), D-13 Menü „CAM-Addon“ (-28), D-29 „ap … übernehmen“ (-29), D-28 veraltete Schnittwerte im Prüffenster mit „übernehmen“ (-31; dafür merkt sich jeder Controller Einsatz und Werkstoff, -30), D-09 ein Werkzeug je Job statt „… L001“ (-32 Befund, -34). Neue Arbeitsregel: Neben `scripts/alle_tests.sh` läuft kein anderes FreeCAD (-33). Offen ohne Entscheidung: D-23 (wartet auf Manuels Antwort zur Ausspannlänge), Rest von D-20 und D-26; zur Entscheidung (Abschnitt 6 dort): D-14, D-22, D-24, D-27 und Frage 6 zu den Werkzeugnamen (D-09).

## Wunschliste

Ein Satz je Wunsch, W-ID fortlaufend.

- **W-001 Maschine aus Baugruppe** – die Maschine als grobes 3D-Modell in
  einer Assembly aufbauen, Slider- und Revolute-Gelenke als Achsen benennen
  und mit Kenndaten versehen (Eilgang, Drehzahl, Schwenkbereich …), daraus
  die CAM-Maschinendefinition von FreeCAD erzeugen; später Grundlage für
  Simulation und Kollisionsprüfung. Spezifikation im Entwurf.
- **W-002 Werkzeugverwaltung** – Werkstoffliste mit deutschen Bezeichnungen,
  Zusammensetzung und Härte; Werkzeuge mit Schnittwerten (ae, ap, vc, fz) je
  Werkstoff und Einsatz; Strategien vergleichen (Zeitspanvolumen,
  Verschleiß). Spezifikation im Entwurf:
  [spezifikation_werkzeugverwaltung.md](spezifikation_werkzeugverwaltung.md).
- **W-003 4-Achs-Bearbeitung am runden Rohteil** – ein Teil mit einer
  Stirnfläche vorne mittig in eine runde Stange legen, Flächen anklicken und
  daraus Schrupp- und Schlichtbahnen für eine Rundachse (A, B oder C, auch
  Drehmaschine mit C und Y) erzeugen lassen. Spezifikation:
  [spezifikation_vierachs.md](spezifikation_vierachs.md).
- **W-005 Programm für jede Steuerung** – die Steuerung einmal an der
  Maschine wählen (LinuxCNC, Siemens, Fanuc, Haas …), die Befehle sind
  vorbelegt und änderbar; ein Postprozessor des Addons schreibt damit das
  Programm, auch an der Drehmaschine: X als Durchmesser, angetriebenes
  Werkzeug, C-Achse ein und aus, Vorschub (Manuel 2026-09-30: „A sollte unsere
  option sein“). Plan mit Entscheidungen E1–E5:
  [spezifikation_steuerung.md](spezifikation_steuerung.md).
- **W-004 Bedienung vereinfachen und automatisieren** – Durchsicht aller
  Fenster und Abläufe (2026-09-27, Manuels Auftrag): acht kleine Stellen
  (D-01 bis D-08), einfacher bedienen (D-10 bis D-14), automatisieren (D-20
  bis D-30) – etwa die eigene Maschine merken, Betriebsarten, Halter und
  Richtwerte vorschlagen, CAM und Job von selbst aktuell halten. Befunde,
  Reihenfolge und Fragen: [durchsicht_bedienbarkeit.md](durchsicht_bedienbarkeit.md).
  D-01 bis D-08 erledigt (P-2026-09-27-09 bis -16); D-10, D-11, D-20
  (Prüffenster), D-21, D-25, D-26 (3-Achs-Fräse) erledigt (P-2026-09-27-18
  bis -24); D-09, D-12, D-13, D-28 bis D-30 erledigt (P-2026-09-27-26 bis
  -34).

## Offene Bugs

Keine bekannten.

## Offene Tasks

- **T-005** Repo öffentlich stellen – Empfehlung Claude (P-2026-09-25-43:
  Verlauf ohne Geheimnisse und ohne private Mail-Adressen, Lizenz LGPL).
  Umstellen kann nur Manuel: GitHub → Settings → Danger Zone → Change
  visibility → Public. Danach die Installationszeile aus dem README einmal
  in FreeCAD ausprobieren.

- **T-004** Fehler an FreeCAD melden: `Machine.from_dict` liest bei
  Linearachsen einen Ursprung ≠ (0,0,0) als Richtung (Befund und Beleg in
  P-2026-09-25-20, im Wochen-Build vom 2026-09-16 noch da). Solange er
  besteht, übergibt das Addon Linearachsen mit Ursprung 0. **Der Bericht ist
  fertig zum Einreichen:** [freecad_fehler_T-004.md](freecad_fehler_T-004.md)
  – einreichen kann nur Manuel (GitHub-Konto).
