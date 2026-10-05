# Status-Snapshot

**Die einzige Stelle für den aktuellen Stand:** Projektstatus, nächster Schritt,
Wunschliste, offene Bugs und Tasks. Was fertig ist, steht nicht mehr hier, sondern im
Verlauf ([archiv/DEV_PROMPT_HISTORY.md](archiv/DEV_PROMPT_HISTORY.md), ein Eintrag je
Patch mit dem, was man sehen muss) und je Thema in seiner Spezifikation (Lesekarte in
`CHATSTART.md`).

## Projektstatus

**Zusätzliche Räumwahl:** Schritt 3 → Räumen → Bahnerzeugung → „Adaptiv – schneller
Freivorschub“, mit einstellbarer Obergrenze und gespeicherter Auswahl; bisherige Bahnerzeugung
bleibt Standard, alte Jobs und andere Bearbeitungen rechnen wie zuvor (P-2026-10-04-26).
Am Testteil modelliert 9,59 statt 10,28 min; die 8 min Zielzeit sind noch nicht erreicht.
Manuels Klickprüfung steht aus.

Stand 0.189.2 (P-2026-10-05-03). Alles, was hier als gebaut steht,
ist automatisch geprüft – gesehen hat es nur Claude als Screenshot. **Manuels Test steht
aus** für alles seit 0.100.0; zuletzt hat er am 2026-10-02 die Schritte des Assistenten
„Bearbeitung“ gesehen („die Menüführung ist gut“).

- **W-001 Maschine aus Baugruppe** – gebaut bis Stufe 4e: Maschine bearbeiten und verfahren,
  schräge Achse, „Neue Maschine …“, Auf der Maschine prüfen, Abfahren, Kollision, Zeit mit
  Beschleunigung (`fahrzeit.py`), Werkzeugspitze (`kinematik.py`). Offen: TCPM wählbar –
  Frage an Manuel, ob seine Steuerung TRAORI/RTCP nutzt.
- **W-002 Werkzeugverwaltung** – gebaut bis Stufe G: Werkzeuge mit Einsätzen je Werkstoff,
  Schruppwerte planen, 26 Werkzeugarten, Halter mit Richtung, Bestückung an der Maschine
  und je Job, Drehrichtung M3/M4, Richtwerte eintragen, eigene Werte je Werkstoff, die Nummer
  am Werkzeug freiwillig („Entladen“, F2, P-2026-10-04-35).
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
  2026-10-05: „Heidenhain muss mit rein“; P-2026-10-05-01). Offen: PLANE SPATIAL für 3+2 an
  Heidenhain, Steuerung an der Maschine
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
- **FreeCAD-Versionen:** 1.1.4 auf Manuels Rechner (Arch-Paket, Python 3.14) – alle 71
  Prüfungen und 98 Szenarien grün mit P-2026-10-02-85, seither je die Prüfung und das Szenario
  zum geänderten Teil. 1.1.3 und Wochen-Build 26.3.0 dev (2026-09-16) zuletzt voll grün mit
  0.96.0 (83 Szenarien); auf Manuels Rechner gibt es beide nicht (Einrichten lädt mehrere GB –
  vorher fragen). Im Wochen-Build stürzte 26.3 einmal beim Schließen des 4-Achs-Fensters ab
  (`closeDialog`, FreeCAD selbst) – bleibt im Blick.

## Nächster Schritt (konkret)

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
- *Siemens WORKPIECE:* Manuel (2026-10-04): „lass es raus“ – nicht gebaut.
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

## Offene Bugs

Keine. B-001 bis B-014 sind behoben (Befunde und Beleg im Verlauf); die nächste freie Nummer
ist B-015.

## Offene Tasks

- **T-006 Alle Kerne nutzen** (Manuel, 2026-10-04: „es rechnen nur maximal 5 von meinen 24 Kernen
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
- **T-007 Werkzeugkiste: Import** nach `docs/werkzeugkiste_json.md` (Format steht, P-2026-10-04-46):
  Ordner `CamAddon/werkzeugkiste/`, „Aus Datei einlesen …“ mit Prüfung, „Vorlage speichern …“.
  Danach weitere Hersteller-Reihen (Manuel: „zum Schluss“).

- **T-005** Repo öffentlich stellen – Empfehlung Claude (P-2026-09-25-43: Verlauf ohne
  Geheimnisse und ohne private Mail-Adressen, Lizenz LGPL). Umstellen kann nur Manuel:
  GitHub → Settings → Danger Zone → Change visibility → Public. Danach die
  Installationszeile aus dem README einmal in FreeCAD ausprobieren.
- **T-004** Fehler an FreeCAD melden: `Machine.from_dict` liest bei Linearachsen einen
  Ursprung ≠ (0,0,0) als Richtung (Befund und Beleg in P-2026-09-25-20, im Wochen-Build vom
  2026-09-16 noch da). Solange er besteht, übergibt das Addon Linearachsen mit Ursprung 0.
  **Der Bericht ist fertig zum Einreichen:** [freecad_fehler_T-004.md](freecad_fehler_T-004.md)
  – einreichen kann nur Manuel (GitHub-Konto).
