# Spezifikation W-002 Stufe C: Werkzeugarten wie in InventorCAM

Stand: Entwurf von Claude, 2026-09-26. Grundlage ist Manuels Screenshot der
Werkzeugarten aus InventorCAM (26 Arten, Verlauf P-2026-09-26-31) und der
Plan in `docs/STATUS_SNAPSHOT.md`, Punkt 10. Die Entscheidungen in
Abschnitt 9 hat Claude getroffen; sie sind zur Besprechung da.

## 1. Ziel

Die Werkzeugverwaltung kennt heute fünf Arten (Schaft-, Torus-, „Radius“-,
Fasenfräser, Bohrer). Manuel will die Arten aus InventorCAM – jede mit
**ihren Maßen, ihrem Bild, ihren Einsätzen**, und so an CAM übergeben, wie
FreeCAD sie kennt. Wie bisher gilt: Auf dem Bildschirm darf keine Frage
aufkommen – jede Art zeigt nur die Felder, die sie hat, und ihr Bild zeigt
beim Tippen, ob die Maße zusammenpassen.

Achtung Name: Das heutige „Radiusfräser“ ist ein **Kugelfräser**. Ein
**Radienfräser** ist eine andere Art – er verrundet Kanten (Viertelkreis-
Profil, konkav).

## 2. Die Arten

Gespeichert wird das feste Wort in der ersten Spalte (wie bisher ASCII,
klein). D ist bei allen Fräsern und Bohrern der Nenndurchmesser, aus dem die
Drehzahl gerechnet wird.

### Fräsen

| Gespeichert | Name (de / en) | Maße außer D, z, Schneidenlänge, Gesamtlänge, Schaft | CAM-Form |
| --- | --- | --- | --- |
| `schaftfraeser` | Schaftfräser / End mill | – | endmill |
| `kugelfraeser` | Kugelfräser / Ball end mill | – (Radius = D/2) | ballend |
| `torusfraeser` | Torusfräser / Bull nose mill | Eckradius | bullnose |
| `konikfraeser` | Konikfräser / Tapered mill | Kegelwinkel je Seite; D = Spitzen-Ø (Kugel an der Spitze) | taperedballnose |
| `schwalbenschwanzfraeser` | Schwalbenschwanzfräser / Dovetail cutter | Flankenwinkel, Hals-Ø | dovetail |
| `lollipopfraeser` | Lollipopfräser / Lollipop cutter | Hals-Ø, Halslänge; D = Kugel-Ø | ballend ≈ |
| `fasenfraeser` | Fasenfräser / Chamfer mill | Spitzenwinkel, Spitzen-Ø | chamfer |
| `radienfraeser` | Radienfräser / Corner rounding cutter | Profilradius, Spitzen-Ø (Führung) | radius |
| `planfraeser` | Planfräser / Face mill | Einstellwinkel; Schneidenlänge = größtes ap | endmill ≈ |
| `nutenfraeser` | Nutenfräser (Scheibenfräser) / Slot cutter | Schneidenbreite, Hals-Ø | slittingsaw |
| `formfraeser` | Formfräser / Form cutter | – (das Profil ist frei) | endmill ≈ |
| `gewindefraeser` | Gewindefräser / Thread mill | Steigung, Flankenwinkel, Hals-Ø, Halslänge | threadmill |

### Bohren

| Gespeichert | Name (de / en) | Maße außer D, z, Schneidenlänge, Gesamtlänge, Schaft | CAM-Form |
| --- | --- | --- | --- |
| `bohrer` | Bohrer / Drill | Spitzenwinkel (leer 118°) | drill |
| `zentrierbohrer` | Zentrierbohrer / Center drill | Spitzenwinkel (60°); D = Zapfen-Ø, Schaft = Körper-Ø | drill ≈ |
| `nc_anbohrer` | NC-Anbohrer / Spot drill | Spitzenwinkel (90°) | drill |
| `gewindebohrer_rechts` | Gewindebohrer rechts / Tap, right hand | Steigung; Schneidenlänge = Gewindelänge | tap (Forward) |
| `gewindebohrer_links` | Gewindebohrer links / Tap, left hand | wie rechts | tap (Reverse) |
| `kegelsenker` | Kegelsenker / Countersink | Spitzenwinkel (90°), Spitzen-Ø | chamfer |
| `flachsenker` | Flachsenker / Counterbore | Spitzen-Ø (Führungszapfen) | endmill ≈ |
| `reibahle` | Reibahle / Reamer | – | reamer |
| `bohrstange` | Bohrstange / Boring bar | D = kleinster Bohrungs-Ø, Schneidenlänge = Ausladung | endmill ≈ |
| `ausspindelwerkzeug` | Ausspindelwerkzeug / Fine boring tool | wie Bohrstange | endmill ≈ |

### Drehen

FreeCAD-CAM dreht nicht (1.1.3 und Wochen-Build). Drehwerkzeuge bekommen
Maße und Bild, aber noch keine Schnittwerte und gehen nicht an CAM – der
Dialog sagt das in einem Satz.

| Gespeichert | Name (de / en) | Maße | CAM-Form |
| --- | --- | --- | --- |
| `drehwerkzeug` | Drehwerkzeug (universal) / Turning tool | Eckenradius, Einstellwinkel, Plattenwinkel, Ausführung (rechts/links/neutral) | – |
| `einstechwerkzeug` | Einstechwerkzeug / Grooving tool | Schneidenbreite, Eckenradius, Stechtiefe | – |
| `gewindedrehwerkzeug` | Gewindedrehwerkzeug / Threading tool | Steigung, Flankenwinkel, Ausführung | – |

### Antasten

| Gespeichert | Name (de / en) | Maße | CAM-Form |
| --- | --- | --- | --- |
| `taster` | Taster / Probe | D = Kugel-Ø, Schaft = Taststift-Ø, Gesamtlänge | probe |

„≈“: CAM kennt die Form nicht; übergeben wird die nächstliegende, und der
Bericht nach der Übergabe sagt das je Werkzeug in einem Satz („T7
Lollipopfräser: in CAM als Kugelfräser – eine eigene Form gibt es dort
nicht“).

## 3. Felder

Neue Felder am Werkzeug, alle metrisch gespeichert, 0 = unbekannt bzw. hat
die Art nicht. Beschriftung und Tooltip je Art (ein Kegelwinkel ist kein
Flankenwinkel), die Einheit daneben wie bisher.

| Feld | Einheit | Arten |
| --- | --- | --- |
| `spitzenwinkel` (gibt es) | ° | Bohrer, Zentrierbohrer, NC-Anbohrer, Fasenfräser, Kegelsenker |
| `eckradius` (gibt es) | mm | Torusfräser, Drehwerkzeug, Einstechwerkzeug |
| `spitzen_d` | mm | Fasenfräser, Radienfräser, Kegelsenker, Flachsenker |
| `kegelwinkel` | ° je Seite | Konikfräser |
| `flankenwinkel` | ° | Schwalbenschwanzfräser, Gewindefräser, Gewindedrehwerkzeug |
| `hals_d`, `hals_laenge` | mm | Schwalbenschwanz- (nur Ø), Lollipop-, Nuten- (nur Ø), Gewindefräser |
| `profilradius` | mm | Radienfräser |
| `steigung` | mm (inch: Gänge je Zoll) | Gewindebohrer, Gewindefräser, Gewindedrehwerkzeug |
| `schneidenbreite` | mm | Nutenfräser, Einstechwerkzeug |
| `einstellwinkel` | ° | Planfräser, Drehwerkzeug |
| `plattenwinkel` | ° | Drehwerkzeug |
| `stechtiefe` | mm | Einstechwerkzeug |
| `ausfuehrung` | rechts/links/neutral | Drehwerkzeug, Gewindedrehwerkzeug |

Pflicht (fett) ist je Art, was man zum Rechnen braucht: D und z bei Fräsern
und Bohrern, dazu die Steigung beim Gewindebohrer; Drehwerkzeuge und Taster
haben keine Pflichtfelder. Der Schneidstoff bekommt **HM-Wendeplatte**
dazu (Plan-, Drehwerkzeuge, Bohrstange); an CAM geht sie als „Carbide“.

Der **Eintauchwinkel** bleibt bei den Fräsern, die eintauchen können
(Schaft, Kugel, Torus, Konik, Form).

## 4. Auswahl der Art und Bild

- Die Auswahl „Art“ ist nach **Fräsen, Bohren, Drehen, Antasten**
  gegliedert (Überschriften, nicht wählbar) und zeigt vor jedem Namen ein
  kleines Bild der Art – dieselbe Zeichnung wie groß neben den Feldern.
- Das Bild neben den Feldern zeichnet jede Art maßstäblich aus ihren
  Maßen: Hals und Kugel beim Lollipop, Scheibe am Hals beim Nutenfräser,
  Gewindeprofil beim Gewindebohrer und -fräser, Wendeplatte am Halter bei
  den Drehwerkzeugen, Kugel am Taststift beim Taster. Was geschätzt oder
  noch Beispiel ist, bleibt gestrichelt; ohne D zeigt es die Beispielmaße
  der Art (wie seit P-2026-09-26-37).
- Ein Wechsel der Art füllt wie bisher die Beispielfelder und leere Felder
  mit den Beispielen der neuen Art und leert, was die neue Art nicht hat.

Beispielwerte (metrisch; in inch runde Zollmaße):

| Art | Beispiel |
| --- | --- |
| Schaft-, Torus-, Kugelfräser | wie heute (Ø 12) |
| Konikfräser | Ø 4 (R 2), 3° je Seite, z 2, Schneide 20, Schaft 8 |
| Schwalbenschwanzfräser | Ø 20, 60°, z 6, Schneide 6, Hals Ø 8 |
| Lollipopfräser | Kugel Ø 8, z 4, Hals Ø 5 × 20 |
| Fasenfräser | Ø 12, 90°, Spitze Ø 0, z 2 |
| Radienfräser | Ø 14, R 3, Führung Ø 8, z 3 |
| Planfräser | Ø 50, z 5, ap 6, κ 45° |
| Nutenfräser | Ø 50, Breite 5, Hals Ø 16, z 12 |
| Formfräser | Ø 10, z 2, Schneide 15 |
| Gewindefräser | Ø 10, P 1,5, 60°, z 3, Schneide 15, Hals Ø 7 × 20 |
| Bohrer | wie heute (Ø 12, 118°) |
| Zentrierbohrer | Zapfen Ø 2,5, Körper Ø 6,3, 60° |
| NC-Anbohrer | Ø 10, 90°, z 2 |
| Gewindebohrer rechts/links | M10: Ø 10, P 1,5, z 3, Gewindelänge 20 |
| Kegelsenker | Ø 20, 90°, Spitze Ø 4, z 3 |
| Flachsenker | Ø 18, Führung Ø 11, z 3 |
| Reibahle | Ø 10, z 6, Schneide 30 |
| Bohrstange, Ausspindelwerkzeug | Ø 20 bzw. 30, z 1, Ausladung 60 |
| Drehwerkzeug | r 0,8, κ 95°, Platte 80°, rechts |
| Einstechwerkzeug | Breite 3, r 0,2, Tiefe 10 |
| Gewindedrehwerkzeug | P 1,5, 60°, rechts |
| Taster | Kugel Ø 4, Stift Ø 3, Länge 50 |

## 5. Einsätze und Rechnen

„+ Einsatz“ bietet je Art nur die Einsätze an, die zu ihr passen; „eigen“
geht immer (außer bei Drehwerkzeugen und Taster, die keine Tabelle haben).
Neue Einsatzarten: **Planen, Fasen, Verrunden, Zentrieren, Senken, Reiben,
Gewindebohren, Gewindefräsen, Ausdrehen**.

| Arten | Einsätze |
| --- | --- |
| Schaft-, Torusfräser | Vollnut, Schruppen, dynamisch, Schlichten (wie heute) |
| Kugelfräser | Schruppen, Schlichten |
| Konik-, Lollipop-, Formfräser | Schlichten |
| Schwalbenschwanz-, Nutenfräser | Vollnut |
| Fasenfräser | Fasen |
| Radienfräser | Verrunden |
| Planfräser | Planen |
| Gewindefräser | Gewindefräsen |
| Bohrer | Bohren |
| Zentrierbohrer, NC-Anbohrer | Zentrieren |
| Gewindebohrer rechts/links | Gewindebohren |
| Kegel-, Flachsenker | Senken |
| Reibahle | Reiben |
| Bohrstange, Ausspindelwerkzeug | Ausdrehen |

Rechnen wie bisher n = vc · 1000 / (π · D), vf = n · z · fz. Dazu:

- **Bohrende Arten** (alle der Gruppe Bohren) zeigen f je Umdrehung statt
  fz, wie heute der Bohrer; ae und ap sind dort ausgeblendet.
- **Gewindebohrer:** vf = n · P. Man gibt nur vc ein; f steht fest (= P) und
  ist grau. Q gibt es nicht.
- **Zeitspanvolumen Q** nur, wo es etwas sagt: Fräsen mit ae und ap, Bohren
  ins Volle (π · D² / 4 · vf); sonst „–“.
- Der **Planer** (Schruppwerte) bleibt bei Schaft- und Torusfräser.

In den Job (P-2026-09-25-61): Gewindebohren → Operation Gewindebohren,
Zentrieren/Senken/Reiben/Ausdrehen → Bohren, Planen → Fläche, Fasen und
Verrunden → Entgraten, Gewindefräsen → Gewindefräsen – soweit die Operation
in der FreeCAD-Version da ist; sonst bleibt der Controller wie heute.

## 6. An CAM übergeben und aus CAM übernehmen

Übergabe (`uebergabe_werkzeuge.py`): Form wie in Abschnitt 2, die Maße auf
die Parameter der Form (z. B. Konikfräser: Diameter = D, TaperAngle =
2 × Kegelwinkel, TaperDiameter = D + 2 · Schneidenlänge · tan Kegelwinkel;
Gewindebohrer: Pitch, SpindleDirection Forward/Reverse). Drehwerkzeuge
bleiben draußen und werden im Bericht genannt; Näherungen („≈“) ebenso.

Übernahme (`werkzeuge_aus_cam.py`): umgekehrt, wo es eindeutig ist –
endmill → Schaftfräser, ballend → Kugelfräser, bullnose → Torusfräser,
taperedballnose → Konikfräser, dovetail → Schwalbenschwanzfräser, chamfer
und vbit → Fasenfräser, radius → Radienfräser, slittingsaw → Nutenfräser,
threadmill → Gewindefräser, drill → Bohrer, tap → Gewindebohrer rechts oder
links (nach SpindleDirection), reamer → Reibahle, probe → Taster. „custom“
bleibt draußen und wird genannt.

## 7. Umstellung alter Dateien

`radiusfraeser` in einer gespeicherten Bibliothek wird beim Laden zu
`kugelfraeser`; gespeichert wird danach das neue Wort. Neue Felder fehlen in
alten Dateien – sie sind 0 (wie bei jedem Feld bisher). FORMAT bleibt 1:
Eine ältere Version des Addons liest unbekannte Arten als Schaftfräser.

## 8. Stufen (je ein Patch)

1. **Kugelfräser statt „Radiusfräser“** – Name, gespeichertes Wort,
   Umstellung alter Dateien (Abschnitt 7).
2. **Arten als Tabelle im Code** – je Art Gruppe, Felder, Pflichtfelder,
   Beispielwerte, CAM-Form; der Dialog baut seine Felder daraus. Alle 26
   Arten wählbar, gegliedert (Abschnitt 4), mit den neuen Feldern.
3. **Bilder** aller Arten, auch klein in der Auswahl.
4. **Einsätze je Art** und das Rechnen dazu (Abschnitt 5).
5. **CAM:** Übergabe und Übernahme aller Arten (Abschnitt 6).
6. **In den Job:** die neuen Einsätze auf die passenden Operationen.

Jede Stufe: Szenario mit Screenshots, Hilfe „Werkzeuge“ ergänzt.

## 9. Entscheidungen (Claude, zur Besprechung)

1. **26 Arten, vier Gruppen** wie im Screenshot. „Gewinde rechts/links“ sind
   zwei Arten (wie in InventorCAM), nicht eine mit Schalter – so steht die
   Drehrichtung schon in der Liste.
2. **Bohrstange und Ausspindelwerkzeug** stehen im Screenshot getrennt
   („Bohrstange“, „Ausbohren/Spindeln“). Angelegt als Bohrstange
   (einschneidig, fest) und Ausspindelwerkzeug (Feinbohrkopf, einstellbar)
   – beide rechnen gleich. Wenn InventorCAM damit etwas anderes meint, ist
   es nur ein Name.
3. **Nutenfräser = Scheibenfräser** (seitliche Nuten, T-Nuten), wie in
   InventorCAM – für eine Nut mit dem Schaftfräser gibt es den Einsatz
   Vollnut.
4. **Konikfräser mit Kugel an der Spitze** (konischer Kugelfräser, im
   Formenbau üblich) – CAMs einzige konische Fräserform ist genau diese.
5. **Drehwerkzeuge ohne Schnittwerte**, bis FreeCAD dreht; ihre Maße sind
   trotzdem da, damit die Bibliothek vollständig ist.
6. **Winkel je Art einzeln gespeichert** (Spitzen-, Kegel-, Flanken-,
   Einstell-, Plattenwinkel) statt eines Feldes „Winkel“ – die Datei bleibt
   lesbar, und ein Wechsel der Art nimmt keinen falschen Winkel mit.
7. **Steigung in inch als Gänge je Zoll** (1/2"-13 UNC), gespeichert in mm.
