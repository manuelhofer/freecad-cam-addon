# Aufträge für Fable

Geschrieben am 2026-10-17 von Claude (Opus 5.5) auf Manuels Wunsch („schreib du mal das für fable
auf bitte“). Fünf Optimierungen, bei denen viel gleichzeitig stimmen muss. Manuels Linie dazu:
„grosse Aufgaben für Fable sind optimierungsaufgaben! perfektion ist wichtig!“

**Zuerst lesen:** `CHATSTART.md` (Einstieg), `CLAUDE.md` (Pushen, Prüfen, Screenshots) und
`docs/arbeitsregeln.md`, Abschnitt 5 (Prüfen). Die Erinnerungen dieses Projekts
(`~/.claude/projects/…freecad-cam-addon/memory/MEMORY.md`) gelten auch für dich.

## Was für alle fünf gilt

- **Strategie erst zeigen, dann bauen.** Was das Addon ohne Vorgabe wählt oder wie eine Bahn
  grundsätzlich fährt, ändert sich nur mit Manuels Ja. Zuerst ein Bild mit Zahlen (heute gegen
  Vorschlag: Zeit, Luft, Eingriff in ae, Kehren). Die Frage kommt mit Grund in
  `docs/OFFENE_FRAGEN.md`.
- **Unnötiges darf ohne Rückfrage weg:** Luftfräsen, überflüssige Rampen, Zickzack, langsame
  Freiwege. Im Freien fährt die Maschine im Eilgang.
- **Prüfen – Manuel ist davon gerade genervt** (2026-10-17: „das mit dem prüfen ne .. geht mir
  langsam auf die nerven“):
  - Je Änderung **eine** Prüfdatei und **ein** Szenario zum geänderten Teil, im neuesten
    Wochen-Build.
  - Ein voller Lauf höchstens einmal am Tag. Ein rotes Szenario erst im Code verstehen, nicht
    mehrfach laufen lassen.
  - Wie die Läufe auf Manuels Rechner gehen, steht in der Erinnerung
    `lokal-pruefen-auf-manuels-rechner`: eigenes Profil, gamescope, Speichergrenze, höchstens zwei
    schwere Läufe gleichzeitig.
- **Manuels Dateien nie ändern:** `~/freecad_cam/testteile/…` nur als Kopie benutzen. Dasselbe
  gilt für die Beispiele in `beispiele/`.
- **Alle Kerne nutzen, das Fenster darf nie stehen.** Rechnungen von Anfang an in Stücke für die
  Nebenrechner zerlegen (`camaddon/nebenrechner.py`), lange Rechnungen in Dialogen nie synchron.
- **Bahnen ohne Manuel vermessen:** Wie das geht, steht in der Erinnerung
  `bahnen-pruefen-ohne-manuel`.
  - Den Weg immer mit allen Achsen zählen, auch q, die Querachse.
  - Abstände zu den Strecken messen, nicht nur zu den Punkten.
  - 3-Achs-Bahnen misst der Prüfstand (`camaddon/pruefstand.py`, `messen`, `zeile`).
  - 4-Achs-Bahnen fährt `camaddon/voxelstange.py` nach.
- **Je Patch:** ein Verlaufseintrag in `docs/archiv/DEV_PROMPT_HISTORY.md` mit einer höheren
  Version in `package.xml`. Danach pushen und mit `git ls-remote` bei GitHub nachsehen.

---

## 1. Rundum schruppen: die tiefen Lagen kreisen durch Luft (Manuels Ring)

**Manuel (2026-10-12)** zu seinem Ring: „warum fährt der da in der luft ??? … komplette anarchie“.

**Das Teil:** `beispiele/ring_4achs_planbearbeitung.FCStd`, Job „Body – 4 Achsen“. Das Original
liegt unter `~/freecad_cam/testteile/4_achs_planbearbeitung_testteil.FCStd` und wird nicht
geändert.
- Ein Ring Ø 65 × 8 aus drei Segmenten mit Schlitzen bis zur Bohrung, dazu Ringnuten.
- Rohteil: Stange Ø 70.
- Werkzeug: T4 Ø 4.

**Befund aus dem Snapshot (2026-10-12, noch einmal nachmessen):**
- 7 Lagen zu je ~5,9 mm, über den Segmenten stehen aber nur 2,5 mm.
- Die tieferen Lagen fahren die ganze Spirale über den fertigen Ring, nur um in die Schlitze zu
  kommen.
- „Folgelagen nur, wo nötig“ (`nur_noetig`) kürzt die Spirale nur längs der Achse, nicht im
  Winkel.
- Die Stellen, an denen schon alles weg ist, markiert `_Rest.leer` als frei.

**Code:** `camaddon/vierachs_bahn.py`
- `schruppen()`: die Lagen-Schleife mit `nur_noetig`, `_rest_neu`/`_Rest`, `_frei`.
- `_schruppen_quer()`: dasselbe mit der Querachse.
- `_zeilen`/`_schruppen_zeilen`: Zeilen hin und her für gewählte Flächen (V4).

**Idee (noch ohne Manuels Ja):** Eine Lage, die nur noch in schmalen Winkelbereichen Material
findet, fährt dort Zeilen (wie V4) statt einer ganzen Umdrehung je Steigung.

**Fertig, wenn:**
- Die Luft im Vorschub der tiefen Lagen ist gemessen, und zwar vorher und nachher.
- Manuel hat das Bild mit den Zahlen gesehen und Ja gesagt.
- Danach ist es gebaut.
- An der Nase (`beispiele/testteil_4achs_nase.FCStd`), an der Nocke und am Ring wird es nirgends
  schlechter: Zeit, Rest, kein Schnitt ins Teil.

**Stand 2026-10-17 (P-2026-10-17-26):** Ohne Querachse gebaut – Zeilen in den Sektoren ab der
Lage, über der weniger als die Hälfte des Umfangs steht (`vierachs_bahn.SEKTOREN_AB`): am Ring
100 → 15 km, Bild `docs/bilder/vorschlaege/ring_sektoren.png`; nach P-32/P-34 11 km mit 10 %
Luft (die Zeile rundum, deren Flanke die Stangenstirn nur streifte, ist weg). Was an Luft bleibt:
die Einfahrten von vorn und in Lage 13 die Zeilen unter der Achse, wo die Lage davor schon alles
nahm (0,1 km). **Offen:** mit Querachse. Zeilen
mit dem radialen Fräser ließen der Kugel an der Nase das Doppelte (22 statt 12 cm³, bis 58 mm² je
mm) – die Zeilen müssten wie die Spirale durch `_quer_plan` → `vierachs_quer.stellungen` →
`_heben_vor_drehen` → `_nachsehen` → `_quer_ausgeben` (in `_schruppen_quer.lage_rechnen`), mit
Einfahrten, die C nicht zurückdrehen (eine Rampe längs der Stange statt Helix). Am Ring mit
Querachse: 151 km, 88 % Luft. Dazu: Die Zeilen lassen an den Schlitzwänden Späne von einem
Winkelschritt (0,48 cm³ am Ring); die Spirale nahm sie beim schrägen Aufstieg am Schlitzrand mit.

**Stand 2026-10-17 (P-2026-10-17-48, W-026, Manuels Antwort zu Frage 1):** Mit Querachse gebaut –
„Sektoren in Zeilen mit Y – C steht“ (Spezifikation V3j): am Ring 151 → 11,4 km, 88 → 12 % Luft,
105,6 → 11,4 min, nichts ins Teil; Y begrenzt (±5): 11,6 min mit C-Schritten. An der Nase gleich
schnell, aber die Kugel hat mehr Rest (20,7 statt 14,2 cm³) – dort den Haken abwählen (Tooltip).
Bild `docs/bilder/vorschlaege/ring_sektoren_y.png`. Schlichten bleibt die Spirale (Manuel: „c und
x oder nur y“).

## 2. Manuels Weg für die Nase (Schaft an der Flanke, Front quer)

**Manuels Bild und Worte (2026-10-12, im Snapshot unter „Nächster Schritt“):**
- Die Flanke:
  - Der Schaftfräser beginnt seitlich neben der Stange hinten.
  - Er schwenkt im Bogen an die Flosse und fährt mit dem Umfang an ihr entlang nach vorn und
    vorn hinaus.
  - Manuel: „einfach von außen einfahren und sozusagen mit dem schaft plan an der flosse vorbei
    fahren“.
- Die Front:
  - Der Fräser kommt von oben, seitlich neben der Stange, und fährt quer in Y ganz hindurch.
  - Manuel: „fährt im ap und mit dem ae einfach da plan entlang“.
- Danach drehen und mit derselben Stellung „vorne die spitze … oben und unten fertig machen“.

**Das Teil:** `beispiele/testteil_4achs_nase.FCStd`. Laut README lässt das Schruppen dort heute
bis 47,6 mm stehen, und die ebenen Flächen der Nase schlichtet die Kugel mit.

**Code:**
- `camaddon/vierachs_plan.py` und `camaddon/vierachs_planbahn.py` („Plan indexiert“). `Schaft`
  für die Seiten gibt es dort schon; es fehlt die Einfahrt im Bogen von der Seite.
- Die Front quer mit dem Umfang ist neu.

**Fertig, wenn:**
- Manuel hat zuerst ein Bild mit Zahlen gesehen und Ja gesagt: heute gegen seinen Weg, mit Zeit,
  Rest an der Nase und Eingriff.
- Danach ist es gebaut und an der Nase nachgemessen.

**Stand 2026-10-17:** Bild mit Zahlen als Frage 2 in `docs/OFFENE_FRAGEN.md`
(`docs/bilder/vorschlaege/nase_flosse_weg.png`): heute 12,2 + 114,7 min (Kugel-Spirale über die
ganze Welle); mit dem, was das Addon kann – Plan indexiert Seiten + Spitze 4,6 min, Kugel in
Linien nur auf den schrägen Flächen 21,8 min – 39 min. Gemessen mit `vierachs_plan.bahn_fuer`
(Face4, Face6, Face8), `vierachs_schlichten.rechne` mit `Flaechen` und `Muster = Linien`.
`mit_dem_schaft` greift am Beispiel nicht: 40 mm Flossenhöhe, 26 mm Schneide. Nicht gebaut.
*P-2026-10-17-47 (W-027):* Der Assistent macht es jetzt von selbst – die fünf Flächen der Flosse
angeklickt: „Plan indexiert“ für Seiten und Spitze, „Rundum schlichten“ mit der Kugel nur auf
den schrägen Flächen in Linien (der Satz darunter sagt, welche); Plan indexiert allein, wenn
nichts für die Kugel bleibt. Offen bleibt der Rest nach dem Schruppen an der Flosse (4 mm²). *P-2026-10-17-37:* Es zählt jetzt Schneide + Hals (die Auskragung N) – die Lagen darüber hat die Schneide schon fertig; mit einem Hals ≥ 14 mm an T1 ginge die Flosse mit dem Schaft.

**Stand 2026-10-18:** Was Manuel zum Bild bejaht hat, ist gebaut. Zur Front (Frage 2) Manuel, 2026-10-18
früh: „ja auswählbar“, und auf die Nachfrage, welche Fläche: „die nase … hat eine schräge … die
sozusagen hoch ins dreieck geht .. das ist eine fläche dann hat sie seitlich zwei gleiche flächen
… und vorne ganz vorne sozusagen die spitze ist vll auch eine klitzekleine fläche … und dann haben
wir noch eine gerade fläche .. die zur drehmitte schaut .. diese fläche kann man mit der stirn eines
schaftfräsers bearbeiten sozusagen und klar gleichzeitig die stirnseite der welle .. das ist eine
kombination .. ja ..“. Also: Face8 (zeigt zur Drehmitte) mit der Stirn eines radialen Schaftfräsers
und in derselben Stellung mit seinem Umfang die Stirnseite der Welle (Face3, z 120 rund um die Nase,
dort geht Drehen nicht) – quer in Y, im ap längs der Werkzeugachse. Als Wahl, nicht vorbelegt; erst
das Bild mit Zahlen gegen heute.
*Bild mit Zahlen gezeigt (2026-10-18, `docs/bilder/vorschlaege/nase_stirnseite_kombination.png`):*
T1 Ø 12 radial, fünf Züge quer in Y, 0,22 min (heute Face8 allein 0,71 min, die Stirnseite ohne
eigenen Schritt); T1 müsste wegen der außermittigen Welle ≥ 49,3 mm heraus, für die Monde neben der
Nase ≥ 57,6 mm. Manuel: „So bauen, mit Ausspann-Hinweis“ – alle Züge, gelb „T1 auf … mm
ausspannen“, wenn es nicht reicht; „wichtig ist das die züge die ap nicht überschreiten is ja klar
... und halt auch die ae einhalten .. also das muss sich ja immer nach den werten richten die der
fräser kann!“ – je Zug höchstens ap längs der Werkzeugachse, je Lage höchstens ae auf der Stirnseite,
aus den Schnittwerten des Fräsers.

## 3. Ringe vom Rand des Materials: Zwickel und Helix am Rand

**Stand (P-2026-10-17-22):** Das 3D-Schruppen hat den Haken „Nur über den gewählten Flächen –
drumherum ist schon gefräst“.
- Die Hauptlagen fahren dann die Ringe vom Rand dessen, was noch steht
  (`raeumen_bahn._Feld.material_setzen` mit der Variante „rohteil“).
- An der Kuppel (`tests/test_schruppen3d.py`): 3,86 statt 6,08 min.
- Rest des Problems: Am Rand des Bereichs bleibt ein Zwickel mit **2,6 ae auf 8 mm**. Die Prüfung
  erlaubt dort deshalb `< 3.0`, sonst gilt `< 2.0`.

**Dasselbe Muster an anderer Stelle:** Mit Materialstand (`stand`) fährt das 3D-Schruppen jede
Lage wie eine Zwischenlage (`camaddon/schruppen3d_bahn.py`, `_schruppen`, `mit_stand`).
- Eine tiefe Hauptlage geht dann am Rand des Materials per Helix hinab.
- Gemessen an der Kuppel mit `zwischen=0`: als Zwischenlage 3,59 min, mit Ringen vom Rand
  (`material_setzen`) 1,20 min.
- Das gilt also auch für das 3D-Schruppen hinter einem Räumen und lohnt sich mehrfach.

**Fertig, wenn:**
- Der Zwickel ist verstanden und weg, die Grenze in der Prüfung wieder `< 2.0`.
- Mit Materialstand fahren die Hauptlagen die Ringe vom Rand (oder es ist begründet, warum
  nicht).
- `tests/test_schruppen3d.py` und der Prüfstand (`tests/test_pruefstand.py`, Bestmarken) sind
  grün.
- Ändert sich eine Bestmarke, nur diesen einen Schlüssel neu schreiben.

**Stand 2026-10-17:**
- *Zwickel verstanden, noch nicht weg:* Es ist der Schritt von einem Ring zum nächsten (1,7 mm
  radial, `raeumen_bahn._Lage._lauf`, „angehängt“ bei einem Weg bis ae + Schritt) am Rand des
  Bereichs, wo das Band innen noch ungeschnitten und 10 mm hoch ist: Die Stirn schiebt sich dort
  über eine Sehne von ~8 mm ins Volle, das 3-mm-Fenster des Prüfstands mittelt das zu 2,6 ae.
  Auf der ganzen Kuppel fällt derselbe Schritt nicht auf (1,9 ae). *Versucht (2026-10-17):* der
  Schritt zum nächsten Ring schräg über zwei Radien entlang des neuen Rings, der dort beginnt
  (`_Lage._lauf`, nur ganze Ringe, nur wenn der gerade Schritt durch Material ginge) – der Zwickel
  blieb bei 2,6 ae an derselben Stelle, und `test_raeumen` zählt beim Morph andere Anschlüsse.
  Zurückgenommen. *Satz für Satz nachgemessen (2026-10-17, nach P-34):* Es ist der Biss beim Schritt
  zum nächsten Ring – die Stirn schiebt sich radial um den Ringabstand ins volle Band, ein
  Kreisabschnitt 1,5 … 1,7 mm hoch (7 … 10 mm², 70 … 85 mm³ bei 9,7 Tiefe) –, und den hat
  **jeder** Ringschritt der Hauptlage gleich (Sätze 43, 82: 68 und 70 mm³; Satz 126: 85 mm³).
  Der Prüfstand sieht ihn nur bei Satz 126, weil davor ein Satz von 1,1 mm steht; bei 43 und 82
  steht davor ein Satz von 5,6 mm, und das 3-mm-Fenster nimmt ganze Sätze – es mittelt den Biss
  dort auf 0,7 ae. Der Zwickel ist also kein Fehler an dieser Stelle, sondern der gewöhnliche
  Ringschritt. Weg bekäme ihn nur ein weicher Anschluss an jedem Ringschritt (Bogen oder die
  Spirale des Morphs) – das ändert alle Ringbahnen und die Anschlüsse in `test_raeumen`; am Satz
  126 kostet er 0,15 s. Nicht gebaut; die Grenze `< 3.0` bleibt mit dieser Begründung im Test.
- *Materialstand, Hauptlagen mit Ringen vom Rand:* gebaut, gemessen, wieder zurückgenommen. Die
  Kuppel nach einem Räumen der Platte (Zwischenlagen 1 mm): alt 2,58 min, 6 % Luft; neu 2,58 min,
  12 % Luft – der erste Ring außerhalb in der Luft kostet, was die Helix kostete. Ohne
  Zwischenlagen kann keine Lage die Kappe nehmen, beide Fassungen finden nichts. Der Gewinn aus
  P-22 (6,1 → 3,9 min) gibt es nur „nur über den Flächen“, wo der Ring um den Fuß im Modell voll
  ist.

## 4. Räumen bis durch gegen die Kontur: fair vergleichen

**Stand (P-2026-10-17-23, Frage 4, Manuel: „Ja, Räumen tritt an“):** An Wänden, die durch das Teil
gehen, tritt das Räumen bis durch gegen die Kontur an (nur Wände gewählt).
- Die Kontur schlichtet dabei schon, das Räumen nicht.
- Deshalb zählt beim Räumen eine **Schätzung** des Schlichtzugs dazu
  (`gui_bearbeitung.BearbeitungPanel._durch_schlichtzug`: Länge der Unterkanten durch den
  Vorschub).
- Gewinnt das Räumen, ist „Schlichten danach“ angehakt.
- Zahlen am C-Ring (`tests/gui/szenario_raeumen_durch.py`, Ø 12):

| Bahn | Zeit |
|---|---|
| Räumen | 2,25 min |
| Schlichten danach, tatsächlich | 0,43 min |
| Schlichten danach, geschätzt | ~0,32 min |
| Kontur | 3,36 min |

**Richtig wäre:** „Räumen + Schlichten danach“ als Folge gegen die Kontur rechnen.
- Vorbild: die Folge Planfräsen + Räumen der Böden (`_folge`, `_nur_boeden`).
- Der Haken darf dabei nicht hin und her springen. Ist das Räumen abgehakt, ist „Schlichten
  danach“ nicht möglich und wird nicht gerechnet. Deshalb heute die Schätzung.

**Code:** `camaddon/gui_bearbeitung.py`: `_wettbewerb_gruppe`, `_durch_schlichtzug`,
`_schlichten_danach_einrichten`, `_schlichten_danach_zusatz`. Dazu `camaddon/raeumen.py`:
`durch_gebiete`.

**Fertig, wenn:**
- Der Vergleich nimmt die gerechnete Zeit des Schlichtens, ohne Springen.
- `tests/gui/szenario_raeumen_durch.py` ist grün.

**Stand 2026-10-17 (P-2026-10-17-27):** gebaut – `_schlichtzug_zeit` nimmt die Zeit des Blocks
„Schlichten danach“, sobald er seine Vorschau hat (nur Wände, kein Boden dazu), und merkt sie je
Wände, Fräser und Aufmaß; sonst die Schätzung. Am C-Ring: „Kontur wäre 25 % langsamer“ (vorher
31 % aus der Schätzung). Nicht gebaut: die Folge Räumen + Schlichten als Ganzes gegen die Kontur
rechnen wie Planfräsen + Räumen (`_folge`) – die gemerkte Zeit reicht, der Haken springt nicht.

## 5. Die übrigen Zickzacks

**Manuel (2026-10-16):** „das auch wirklich alle zickzack fahrten weg sind“.

**Was noch übrig ist, mit Grund:**
- **Vollnuten:** Ist die Nut kaum breiter als der Fräser, fährt `camaddon/nut_bahn.py` die
  Vollnut mit Rampe (`VOLLNUT_ANTEIL`, `VOLLNUT_HELIX`). Dort geht heute nur Hin und Her.
- **Die schmale Tasche im Schwenkteil** (`beispiele/schwenkteil_5achs.FCStd`): Ø 12 hat dort
  1 mm Platz, also eine schmale Schleife.
- **Winzige Ringe am Geist** (`beispiele/geist_stl/`, 3D-Schlichten): kein echtes Hin und Her.
- **Wendepunkte im Adaptiv-Kern von FreeCAD.** Der Kern rechnet nie zweimal dasselbe (Erinnerung
  `adaptiv-kern-streut`).

**Messen:**
- Der Prüfstand zählt `kehren`.
- Jedes Szenario schreibt `kehren.txt` und je Operation ein `.nc`.
- Eine neue Kehre gegenüber dem Lauf davor ist fast immer eine Regression.

**Fertig, wenn:** Jede Stelle ist weg oder hat ein Bild mit Zahlen und einen Grund, warum es dort
nicht anders geht, und Manuel hat es gesehen.

**Stand 2026-10-17:**
- Vollnut ohne Helix-Platz: Rampe in einer Richtung, wenn die Nut lang genug ist
  (P-2026-10-17-29); sonst Zickzack wie von Manuel erlaubt.
- Flanke: war ein Zählfehler (steiler Abstieg längs der Achse), behoben (P-2026-10-17-30).
- Nachgemessen (`kehren.txt`, nach P-34):
  - Schwenkteil: 0 Kehren. Die schmale Tasche ist eine Schleife 27 × 3 mm, kein Hin und Her
    (Bild `docs/bilder/vorschlaege/schwenkteil_schraege_raeumen.png`).
  - Geist, 3D-Schlichten: 3 Kehren in 58 669 Sätzen, oben am Kopf, wo die Zeilen die steile
    Flanke hinab- und darunter zurücklaufen (0,02 mm neben der Spur) – die Falte der Fläche, kein
    Zickzack (Bild `docs/bilder/vorschlaege/geist_kehren_kopf.png`).
  - Testteil: 1 Kehre, „Kontur T1“ in der Dreieckstasche – die Wendel auf einem Dreieck von
    0,35 mm Seite, 57 Umläufe 5 mm hinab. **Weg (P-2026-10-17-35):** hat die Schleife im Radius
    weniger als ein Zehntel des Fräserdurchmessers, geht die Kontur senkrecht hinab.
  - Wendepunkte des Adaptiv-Kerns: bleiben (Erinnerung `adaptiv-kern-streut`).

---

**Reihenfolge, wenn Manuel nichts anderes sagt:** 1 und 3 zuerst. Beide sind klar umrissen und
messbar (Luft in %, Eingriff in ae). 2 braucht vorher sein Ja zum Bild.
