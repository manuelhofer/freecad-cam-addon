# Spezifikation W-016: Eckige Teile auf der Drehmaschine fräsen (C und Y)

Stand: **nur aufgeschrieben, noch nicht gebaut** – Wunsch von Manuel vom 2026-10-06, dazu
Claudes Befund zum Code (Stand 0.194.12) und Vorschläge zum Besprechen. Gebaut wird erst, wenn
Manuel es sagt („demnächst, noch nichts bearbeiten – nur dokumentieren“).

Grundlage: [spezifikation_strategien.md](spezifikation_strategien.md) (W-006, Assistent
„Bearbeitung (Fräsen)“), [spezifikation_vierachs.md](spezifikation_vierachs.md) (W-003,
4-Achs-Assistent, Plan indexiert), [spezifikation_steuerung.md](spezifikation_steuerung.md)
(W-005, Postprozessor), [spezifikation_simulation.md](spezifikation_simulation.md) (Prüffenster,
Kollision).

## 1. Der Wunsch

Manuel, 2026-10-06, an seiner CLX 550 (Siemens; Drehmaschine mit C an der Hauptspindel, Y und
angetriebenen Werkzeugen; seine Maschinendatei `~/freecad/maschinen/clx550.FCStd`, C4 an der
Hauptspindel):

> „Ich wollte jetzt mit der CLX 550 etwas fräsen – jetzt steht hier, dass das nicht geht, da es
> eine Drehmaschine ist … Ich kann aber auch vierkantige Teile auf der Drehmaschine einspannen –
> Vierbackenfutter beispielsweise – und ich kann auch mit der C- und Y-Achse fräsen … Klar kann
> ich jetzt eine neue Maschine erstellen, aber wofür – und die kann dann auch die Geschichte mit
> der C-Achse, die sich bewegt, um die Limits der Y-Achse auszugleichen, nicht.“

Also: Ein Teil im **Quader** (ein Vierkant, eine Platte, ein Gussteil) wird im Futter der
Drehmaschine gespannt – Dreibacken-, Vierbacken- oder Spannzangenfutter – und mit den
angetriebenen Werkzeugen gefräst:

- **an der Stirnseite** mit axialem Werkzeug (Planfräsen, Taschen, Konturen, Nuten, Zapfen,
  Bohrungen, Gravur): Y fährt, so weit es reicht, danach hilft C (wie seit 0.194.0 für die
  Stirnseite gebaut, Manuel 2026-10-05: „immer wenn es möglich ist, sollte die Y-Achse benutzt
  werden, bis zu 85 % … danach muss die C-Achse arbeiten“);
- **an den Seitenflächen** mit radialem Werkzeug: C stellt die Seite zum Werkzeug, Y fährt quer,
  Z längs, X ist die Tiefe.

Eine Hilfs-„Fräse“ als zweite Maschine ist kein Ausweg: Ihr fehlen C an der Hauptspindel, der
Ausgleich der Y-Grenzen mit C, der Revolver, die echten Wege und die Kollision mit Futter und
Revolver.

## 2. Heute (0.194.12)

- **Assistent „Bearbeitung (Fräsen)“:** Wählt man in Schritt 1 eine Drehmaschine, steht rot
  „Auf der Drehmaschine ist das Rohteil eine Stange, kein Quader“, „Weiter“ und „Anlegen“ gehen
  nicht; angeboten wird nur „Weiter im 4-Achs-Assistenten“. Im Code: `gui_bearbeitung.py`,
  `nur_vierachs()` (Maschinenart `maschinenspeicher.DREHMASCHINE`), dazu `accept()` und
  `_maschine_gewaehlt` mit `ba.maschine.drehmaschine`; `STANGE_ARTEN`.
- **4-Achs-Assistent:** Das Rohteil ist immer eine Stange (Zylinder, `vierachs_rohteil.py`);
  ein Vierkant lässt sich nicht als Rohteil angeben.

## 3. Was schon da ist und trägt

Der wichtigste Befund: **Hinter dem Assistenten ist das meiste schon fertig.**

- **Postprozessor und Prüffenster rechnen die Stirnseite schon für jede Bahn ohne Rundachse.**
  `stirnseite.ist_stirn(op, befehle)` ist wahr für jede Operation mit X, Y, Z ohne A/B/C, die
  keine Rundum- oder Simultan-Operation ist. An einer Drehmaschine mit C an der Hauptspindel
  (`stirnseite.rahmen`, `postprozessor.maschineninfo` → `info.stirn`) macht `stirnseite.befehle`
  daraus X, Y, C: Y bis „Y an der Stirnseite nutzen bis … %“ (`YNutzen` an der Y-Achse,
  vorbelegt 85), weiter hinaus C – „mit“ oder „Schritte“ (`StirnModus` am Job). Das Prüffenster
  (`reichweite.py`, Haken `st.ist_stirn` in `befehle`) fährt es genauso ab. Ein Job im Quader,
  dessen Z längs der Spindelachse aus dem Futter zeigt, würde also schon heute richtig
  geschrieben und abgefahren.
- **Das Koordinatensystem passt:** Die Werkstückaufnahme der Drehmaschine ist das LCS an der
  Spannfläche des Futters – Z aus der Spannfläche heraus (Spindelachse), X von der Spindelachse
  zum Werkzeug (`beispielmaschine.py`, „Spannflaeche“). Der Vorschlag für den Nullpunkt im
  Prüffenster – „das Rohteil mittig auf der Aufnahme, mit der Unterseite auf der Spannfläche“ –
  legt einen Quader richtig ins Futter: Seine Oberseite zeigt zum Revolver.
- **Ein Teil außermittig** (im Vierbackenfutter versetzt gespannt) kennt der Rahmen schon:
  `Rahmen.mitte` ist die Drehachse in X, Y des Programms.
- **Werkzeugrichtung:** Das Prüffenster meldet schon, wenn eine Bahn längs Z mit einem radial
  sitzenden Werkzeug gefahren würde (`rw.werkzeug_quer`). Wie ein Werkzeug steht, sagt sein
  Halter in der Werkzeugverwaltung (gerader Halter in der Stirn der Scheibe = axial, „VDI30
  angetrieben radial“ = radial; Winkelkopf am Sternrevolver = axial).
- **Alle Strategien des Assistenten** rechnen im Job von oben (Hüllfläche, Materialstand,
  Abtrag im Prüffenster von oben) – an der Stirnseite gilt dasselbe, „oben“ ist dort „vorne“.
- **Schwenken mit einer Rundachse:** `schwenken.Maschine.loese(normale)` löst mit beliebig vielen
  Rundachsen, also auch mit C allein – eine Seitenfläche des Quaders wäre eine „Ebene“, auf die
  C dreht.
- **Plan indexiert** (`vierachs_planbahn.py`) fräst ebene Flächen längs der Stange mit stehendem
  C und Y quer – genau die Seiten eines Vierkants; Querbohrungen und Nuten auf dem Mantel
  ebenso.
- **Spannen:** „Von unten gespannt“ (`spannung.py`) prüft Bahnen gegen die Spanntiefe und baut
  die Backen eines Schraubstocks fürs Bild und die Kollision.

## 4. Was fehlt – Teilaufgaben mit Ideen

### Q1 Der Assistent „Bearbeitung“ lässt die Drehmaschine zu (Stirnseite)

- Statt des roten Satzes in Schritt 1 eine Wahl, was im Futter steckt: **„Quader im Futter –
  gefräst an der Stirnseite“** oder **„Stange – weiter im 4-Achs-Assistenten“** (der Knopf von
  heute). Vorschlag: Quader vorgewählt, wenn das angeklickte Teil kein Drehteil ist.
- `nur_vierachs()` gilt dann nur noch für die Wahl „Stange“; `accept()` und „Weiter“ gehen.
- **Aufspannung:** „Unten liegt“ heißt an der Drehmaschine „im Futter liegt“ – die Fläche, die an
  der Spannfläche anliegt; die Oberseite zeigt zum Revolver. Die Beschriftungen in Schritt 1
  sagen es so („Fläche an der Spannfläche“, „Stirnseite“).
- **Nullpunkt:** vorgewählt „Mitte oben“ – an der Drehmaschine die Drehmitte auf der Stirnseite,
  wie Z0 beim Drehen. Liegt das Teil außermittig (siehe Q2), bleibt X0 Y0 auf der Drehachse.
- Alles Weitere (Strategien, Materialstand, Zeit, Anlegen) bleibt, wie es ist – der Job liegt im
  Futter, die Programmausgabe macht der Stirnseiten-Teil des Postprozessors.

### Q2 Spannen im Futter

- „Von unten gespannt“ heißt an der Drehmaschine **„im Futter gespannt“**: so tief steckt der
  Quader zwischen den Backen. Dieselbe Prüfung wie heute (`spannung.pruefen`): keine Bahn unter
  das Rohteil, keine neben das Rohteil unterhalb der Spannhöhe.
- **Backen:** statt der zwei Schraubstockbacken (vorn/hinten in Y) die Backen des Futters –
  drei im Abstand von 120° oder vier im Abstand von 90°, an den Seiten des Quaders anliegend, so
  hoch wie gespannt, ein Stück höher als die Spanntiefe nicht. Idee: Backenzahl und Backenmaße
  an der Maschine (Werkstückaufnahme), einmal eingetragen; im Job nur die Spanntiefe.
- **Außermittig:** Im Vierbackenfutter lässt sich ein Teil versetzt spannen (eine Bohrung
  außermittig drehen). Idee: in Schritt 1 „Drehmitte bei X … Y …“ (vorgewählt die Mitte des
  Rohteils); daraus `Rahmen.mitte` und die Lage im Prüffenster.

### Q3 Werkzeuge an der Stirnseite

- Für die Stirnseite gehen nur **axial** stehende Werkzeuge – gerader Halter in der Stirn der
  Revolverscheibe, Winkelkopf am Sternrevolver. Die Fräserliste nennt Platz und Richtung
  („P3 · axial · T5 …“) und warnt gelb wie im 4-Achs-Assistenten (`va.lage.nicht_radial`, hier
  umgekehrt: „sitzt nicht axial – braucht einen geraden Halter“).
- **Drehzahl:** An der Drehmaschine begrenzt der **Werkzeugantrieb** die Drehzahl (in der
  Beispielmaschine S3), nicht die Hauptspindel – Schnittwerte, Zeit und „Schruppwerte planen“
  nehmen dann seine Höchstdrehzahl (`neu.drehzahl.werkzeuge`).
- Bestückung und Magazin wie im 4-Achs-Assistenten: Platz aus der Bestückung, Nummer aus dem
  Magazin.

### Q4 Zeit, Reichweite und Vorschau

- Die Zeit des Assistenten rechnet heute ohne C. An der Stirnseite kommt C dazu: bei „mit“ die
  kurzen Sätze in G93, bei „Schritte“ je Wechsel Hochfahren, C drehen, Eintauchen. Idee: die
  Bahn vor der Zeitrechnung durch `stirnseite.befehle` schicken, wie es der Postprozessor tut.
- Eine Stelle, die die Maschine mit keiner Stellung von C erreicht (`st.nicht_erreichbar`),
  sagt der Assistent schon in Schritt 2/3 rot – nicht erst das Prüffenster.
- Der Modus („C dreht mit“ / „C in Schritten“) ist heute je Job in „Programm schreiben“. Idee:
  ihn auch im Assistenten zeigen, weil er die Zeit ändert.

### Q5 Die Seitenflächen des Quaders (radiales Werkzeug)

Zwei Wege, beide auf Vorhandenem:

- **(a) Ebene schwenken mit C:** Eine Seitenfläche anklicken → „Ebene schwenken“ wie an der
  5-Achs-Fräse: C dreht die Fläche zum radialen Werkzeug, die Ebene wird ein eigener Job, darin
  rechnet jede Strategie wie von oben (Planfräsen, Taschen, Bohrungen quer, Nuten). Im Programm:
  C positionieren, dann X (Tiefe, radial), Y (quer), Z (längs). Dafür nötig:
  - die Werkzeugrichtung aus **Aufnahme und Halter** – heute nimmt `schwenken.Maschine.richtung`
    nur das LCS der Aufnahme; am Revolver bestimmt der Halter, ob das Werkzeug axial oder radial
    steht;
  - erreichbar sind nur Flächen, deren Normale quer zur Spindelachse liegt (C dreht nur um die
    Spindelachse) – und die Stirnseite selbst; schräge Flächen sagt das Fenster rot;
  - **Grenzen von Y:** An einer Seitenfläche hilft C nicht über die Y-Grenze hinweg (die Fläche
    würde kippen) – das Fenster sagt, wie breit Y reicht, und meldet eine zu breite Fläche.
- **(b) 4-Achs-Assistent mit Quader:** In Schritt 1 „Rohteil: Stange oder Vierkant/Quader“. Dann
  gehen Plan indexiert (die Seiten), Querbohrungen, Nuten auf dem Mantel, Rundum entgraten wie
  heute. Der Abtrag im Prüffenster kennt je Strahl aus der Achse einen Radius – das reicht für
  einen Quader (er ist von der Achse aus „sternförmig“).

Vorschlag Claude: zuerst (a) – dann stehen an den Seiten alle Strategien des Assistenten zur
Wahl, und das Programm ist ein Programm je Aufspannung wie bei 3+2. (b) später, wenn rundum
Bearbeitungen am Vierkant gebraucht werden.

### Q6 Programm schreiben

- Stirnseite: fertig (siehe 3). Zu prüfen beim Bauen: Siemens TRANSMIT/TRACYL schreibt das
  Addon nicht (es rechnet C selbst) – so bleibt es.
- Seitenflächen (Q5a): die Ebene „ohne Schwenkzyklus“ an der Drehmaschine – C positionieren
  (nach DIN 66217, `info.umgekehrt`), C-Achse vorher ein (`SPOS`), X im Durchmesser.
  Heidenhain-Klartext gilt hier nicht (Drehmaschinen sprechen CNC PILOT/MANUALplus).

### Q7 Hilfe und Texte

- „Bearbeitung (Fräsen)“: Abschnitt „Auf der Drehmaschine“ (Futter, Stirnseite, Werkzeuge
  axial, Y und C); Verweis auf „Programm schreiben → Stirnseite“.
- `ba.maschine.drehmaschine` und `ba.maschine.vierachs.tooltip` neu fassen.

## 5. Fragen an Manuel (zu entscheiden, bevor gebaut wird)

- **E1 Seitenflächen:** (a) „Ebene schwenken mit C“ oder (b) „4-Achs-Assistent mit Quader“ zuerst?
  Empfehlung: (a).
- **E2 Nullpunkt an der Drehmaschine:** vorgewählt die Drehmitte auf der Stirnseite? Empfehlung:
  ja.
- **E3 Futter:** Backenzahl und Backenmaße einmal an der Maschine eintragen (Empfehlung) oder je
  Job?
- **E4 Außermittig spannen:** gleich mit anbieten oder erst später? Empfehlung: später – erst
  mittig.
- **E5 C-Modus im Assistenten:** „mit“/„Schritte“ auch im Assistenten zeigen (Empfehlung) oder nur
  in „Programm schreiben“ wie heute?

## 6. Reihenfolge (Vorschlag)

1. **Q1 + Q3** – der kleinste Schritt mit dem größten Nutzen: Quader im Futter, Stirnseite
   fräsen. Postprozessor und Prüffenster gibt es schon.
2. **Q2** – Futterbacken in Bild und Kollision, Spanntiefe.
3. **Q4** – Zeit mit C, Reichweite früh melden.
4. **Q5** – Seitenflächen nach E1.
5. **Q7** – Hilfe mit jedem Schritt.

## 7. Fertig, wenn

An Manuels CLX 550 (seine Maschinendatei), ein Vierkant im Futter:

- Der Assistent „Bearbeitung“ legt den Job an, ohne auf den 4-Achs-Assistenten zu verweisen.
- Eine Tasche an der Stirnseite, breiter als 85 % des Y-Wegs: Das Programm fährt Y bis zur
  Grenze und nimmt dann C dazu; das Prüffenster zeigt dieselben Achsstellungen; keine Achse über
  ihrer Grenze.
- Die Backen stehen im Bild und in der Kollision; keine Bahn fährt hinein.
- Nur axiale Werkzeuge sind vorgewählt; ein radial sitzendes meldet der Assistent gelb.
- (mit Q5) Eine Tasche an einer Seitenfläche: C steht auf 0/90/180/270°, das radiale Werkzeug
  fräst sie, das Programm schreibt C nach DIN 66217.
