# Spezifikation W-006: Frässtrategien – besser als das CAM-Modul

**Stand:** 2026-09-30, Entwurf (Claude, zur Besprechung). Auslöser, Manuel
(2026-09-30): „ich hätte gerne das du einen plan schreibst für alle fräs
strategien dies so gibt ... das wir am ende mit unserem addon bessere
frässtrategien auf ein bauteil anwenden können als in freecad vom cam modul
vorhanden sind ... auserdem optimierung des codes und schauen das es schneller
und speicher sparender generiert wird der werkzeugweg wenn das irgendwie
möglich ist .. aber hauptziel ist qualität der werkzeugwege und
bedienbarkeit.....“

Dieser Plan sagt, welche Strategien es gibt, was FreeCADs CAM davon kann und
wo es hakt, was das Addon schon hat, und wie wir Strategie für Strategie
besser werden – mit einer Reihenfolge und Entscheidungen für Manuel
(Abschnitt 10). Gebaut wird danach in Stufen wie bei W-003; jede Stufe hat
ihre Prüfung (Abschnitt 9).

## 1. Zielbild

- **Qualität der Bahn zuerst:** Die Maschine soll die Bahn so fahren können,
  wie ein erfahrener Zerspaner sie programmieren würde – tangential ein- und
  ausfahren, Bögen statt Ecken, gleichmäßiger Eingriff, kein Fräsen in der
  Luft, Gleichlauf, wo es geht, und nirgends zu viel oder zu wenig stehen
  lassen.
- **Einfach zu bedienen:** Teil und Rohteil, Flächen anklicken, Werkzeuge
  wählen – die Strategie schlägt das Addon vor und sagt, warum. Alles weitere
  steht hinter „Mehr …“ (spezifikation_vierachs.md, Abschnitt 11). Sätze
  statt Parameter; jeder Vorschlag mit Begründung; die Hilfe erklärt, was die
  Strategie tut.
- **Geprüft, bevor es an die Maschine geht:** Jede Bahn läuft durch Abtrag
  (bleibt zu viel stehen? geht es ins Teil?), Kollision (Halter, Maschine) und
  Reichweite – das haben wir für rundum, das gilt für alle Strategien.
- **Schnell und sparsam:** erst messen, dann die teuersten Stellen. Die Bahn
  darf sich dabei nicht ändern (Abschnitt 8).

## 2. Was FreeCADs CAM kann – und wo es hakt

Stand 1.1.3 (stabil) und Wochen-Build 26.3 (`Path/Op`, angesehen 2026-09-30).

| Operation | Was sie tut | Wo es hakt |
|---|---|---|
| **Profile** (Kontur) | Außen/innen an Kanten oder Flächen, Zustellung, mehrere Passes über „Stepover“, Fräserradiuskorrektur (G41/42) | Kein tangentiales Ein-/Ausfahren in der Operation (nur als Dressup, das wieder vergessen wird); Ecken scharf; keine Schrupp-/Schlichtteilung mit Aufmaß in einem Schritt |
| **Pocket** / **Pocket Shape** (Tasche) | Muster ZigZag, Offset, ZigZagOffset, Line, Grid; Start Mitte/Rand; Restmaterial („UseRestMachining“, 1.1); Werkzeug unten halten | Offsetmuster fährt volle Nutbreite in Ecken (Eingriff springt), keine Bögen zwischen Zeilen, kein Trochoidal; Eintauchen nur senkrecht oder mit Rampen-Dressup |
| **Adaptive** (HSM-Schruppen) | Gleichmäßiger Eingriff je Lage, Helix-Einfahrt, „Clearing“ oder „Profiling“, Aufmaß | Langsam auf großen Teilen (Python-Kern), nur Geraden (Zittern an der Steuerung, viele Sätze), jede Lage von vorn – kein Wissen über die vorige Lage; Restmaterial nur, was die Operation selbst ließ |
| **MillFace** (Planfräsen) / 26.3 **MillFacing** | Muster wie Tasche; Grenze Rohteil/Umriss/Fläche; 26.3: Spirale, Zickzack, gerichtet, beidseitig, Überlauf | Kein Über-/Unterlauf nach Fräser-Ø in 1.1.3, keine Vorschubanpassung beim Ein-/Austritt |
| **Helix**, **Drilling**, **Tapping**, **ThreadMilling** | Zirkularfräsen von Bohrungen, Bohrzyklen (G81/G83/…), Gewinde | Solide – hier gibt es wenig zu gewinnen; Bohren übernehmen wir, wie es ist |
| **Slot** (Nut) | Nut zwischen zwei Bezügen, Zickzack oder Linie, Lagen | Ohne Rampe, ohne Bögen |
| **Deburr** (Entgraten), **Engrave**, **Vcarve** | Fase an Kanten mit Fasenfräser, Gravur an Drähten, V-Gravur | Nur 2D auf Ebenen – keine Kante im Raum, nicht rundum |
| **Surface** (3D, OCL Dropcutter) | Zeilen, Zickzack, Kreise, Offset, Spirale; Schrittweite; ein- oder mehrlagig; Kantenprofil | Braucht **OpenCamLib** (fehlt in manchen Builds); Python-Schleifen – Minuten bei feinem Raster; Grat- (Scallop-)Höhe nicht als Maß, nur als Schrittweite; kein Steil/Flach, kein Restschlichten, kein Bleistift (Kehlen) |
| **Waterline** (Z-konstant) | Höhenlinien, wahlweise mit Muster auf der letzten Lage | OCL oder „Experimental“; auf flachen Bereichen bleiben Rippen; keine Kombination mit Zeilen |
| 26.3 **PlanarSurface** | Ersetzt Surface + Waterline: Strategie wählbar, adaptives Abtasten, Ein-/Ausfahren, Aufmaß, Adaptiv-Muster | Wieder OCL; dieselben Grenzen bei Grat, Steil/Flach, Rest |
| 26.3 **RotarySurface** | 4-Achs-Flächenfräsen mit Dropcutter: parallel, Ringe, Spirale, abgewickelt („wrap“); Start-/Endwinkel, radiales Aufmaß | OCL; kennt keine Maschine – nicht, wo das Werkzeug sitzt, keinen Halter, keine Kollision, kein Abtrag; Muster ohne Rücksicht auf Wände und Absätze |
| 26.3 **Flute** | Kanneluren längs eines Drahts mit Rampen | Sonderfall |
| Dressups | Array, Boundary, Dogbone, Tags (26.3); 1.1.3 dazu Ein-/Ausfahren, Rampe, Achsen-Abbildung, Z-Korrektur | Dressups sind ein zweiter Schritt, den man vergessen kann; sie kennen den Eingriff nicht |

Was **quer durch alle** fehlt: ein Abtragsmodell (was steht nach der letzten
Operation noch?), eine Kollisionsprüfung mit Halter und Maschine, Bögen
(G2/G3) in gerechneten Bahnen, Vorschub nach Eingriff, Zeit- und
Restmaterial-Angaben, und ein Vorschlag, welche Strategie zu welcher Fläche
passt. Genau das haben wir für rundum schon gebaut (Abschnitt 3) – darauf
setzen wir auf.

## 3. Was das Addon schon kann (Stand 0.33.0)

- **Rundum schruppen** (W-003 V3): Hüllfläche um die Achse aus dem Netz
  (`vierachs_huelle`), Lagen radial, Zeilen hin und her mit Ringgang vor jeder
  Wand (D-42), Rampe längs der ganzen Fahrt, Überlauf, Abstände, Bereich der
  gewählten Flächen (V4a/V4b), G93 mit F in jedem Satz, Zeitschätzung.
- **Rundum schlichten** (V5): jeder Fräser mit seiner Form (Kugel, Torus,
  Schaft …), Schrittweite aus der Werkzeugtabelle, Stufen, wo das Schruppen
  mehr stehen ließ, Spirale oder Zeilen.
- **Abtrag** (`restmaterial`): die Stange beim Abspielen, am Ende der
  Vergleich in Farben (grün passt, gelb zu viel, rot zu wenig, blau im Teil).
- **Kollision** (`kollision`): Werkzeug, Halter, Maschine, Teil, Spannmittel –
  je Paar, nur genau, wo nötig; Schneide im Vorschub ins Teil.
- **Maschine**: Kette, Reichweite, Abfahren, Halter mit Richtung, Bestückung
  je Job, Ø/Radius, Höchstdrehzahlen.
- **Werkzeugverwaltung**: Werkstoffe, Einsätze, Schnittwerte, Schruppwerte
  planen, Halter, Übergabe an CAM, Schnittwerte in den Job.
- **Assistent**: Rohteil → Flächen → Werkzeuge → Anlegen, mit Vorschlägen,
  gelben Sätzen und Hilfe.

Das ist mehr, als FreeCADs Rotary-Operation kann – und der Bauplan für alles
Weitere: **Rechenkern ohne OCL, Bahn mit Abtrag und Kollision geprüft, ein
Assistent, der vorschlägt.**

## 4. Der Katalog

Für jede Strategie: wozu, wie FreeCAD es macht, wie wir es besser machen,
Aufwand (klein: Tage, mittel: eine Woche, groß: mehr) und was sie braucht.

### 4.1 2,5D – Ebenen, Taschen, Konturen

1. **Planfräsen** – die Oberseite eben; Zeilen oder Spirale, Überlauf
   Fräser-Ø·0,6 an den Rändern, Schrittweite ae aus der Werkzeugtabelle,
   Vorschub beim Austritt gesenkt (Grat). *Besser:* Überlauf und Schrittweite
   von selbst, Gleichlauf, keine Leerzeile. Aufwand klein.
2. **Tasche adaptiv (HSM)** – gleichmäßiger Eingriff (ae) bei voller
   Schneidenlänge (ap), Helix- oder Rampen-Einfahrt, Trochoiden in Ecken und
   Nuten. *Besser als Adaptive:* Bögen (G2/G3) statt Punktwolke, konstanter
   Eingriff auch in Ecken (Trochoide), Restmaterial aus dem Abtragsmodell
   (nächste Lage weiß, was steht), Vorschub nach Eingriff, viel schneller
   (numpy). Aufwand groß – aber der größte Gewinn: Manuels „Schruppwerte
   planen“ zielt genau darauf (ganze Schneide, schmales ae). Gebaut als S3f
   „Räumen“ (0.44.0): Ringe bei vollem ap und schmalem ae, einmal hinein, in
   der Tasche über die Rampe rundum; Trochoiden in Ecken (E3) erst, wenn die
   Messung sie verlangt.
3. **Tasche Offset / Zeilen** – klassisch, für weiche Werkstoffe und kleine
   Fräser; Bögen zwischen Zeilen, Ecken mit Radius, Restmaterial in Ecken mit
   dem kleineren Fräser (Punkt 5). Aufwand mittel.
4. **Kontur schruppen und schlichten** – außen/innen, mehrere Zustellungen,
   Aufmaß fürs Schlichten, **tangentiales Ein-/Ausfahren** (Bogen + Gerade,
   Länge nach Fräser-Ø), Schlichtschnitt mit vollem ap in einem Zug, Ecken
   wahlweise gerundet. *Besser:* Ein-/Ausfahren gehört zur Operation, nicht
   zum Dressup; Schruppen und Schlichten in einem Schritt aus dem Assistenten.
   Aufwand mittel.
5. **Restmaterial 2,5D** – was der große Fräser in Ecken ließ, holt der kleine:
   aus dem Abtragsmodell, nicht aus einer Formel. Aufwand mittel (braucht das
   Abtragsmodell für Ebenen, Abschnitt 7). Gebaut für Wände (P-2026-10-01-35,
   0.51.0) – ohne Abtragsmodell, aus der Geometrie: Die Bahn des kleinen fährt
   nur, wo sein Kreis aus jedem Kreis des großen ragt (Abstand zu dessen Bahn
   größer als R − r, `kontur_bahn.nur_wo_der_grosse_nicht_hinkam`), um r länger;
   als Kontur mit `RadiusDavor`, im Assistenten der Block „Restmaterial“ (der Ø
   davor von der Kontur oder dem Räumen im Fenster, vorgewählt der größte
   kleinere Fräser). Am Taschenteil mit scharfen Ecken: nach Ø 12 R 6, nach
   Ø 4 R 2, vier Stellen je Lage (`test_rest`, `szenario_rest`). Restmaterial
   auf Böden (Räumen mit dem kleineren) folgt mit dem Abtragsmodell. Den Haken
   setzt der Assistent selbst (Manuel, 2026-10-02: „Ja“; P-2026-10-02-19, 0.81.0),
   wenn die Kontur gezeichnete Rundungen innen fährt, die kleiner sind als ihr
   Fräser, und ein kleinerer da ist (`kontur_bahn.innenrundungen`: Stück Zylinder
   mit senkrechter Achse, keine ganze Bohrung, zur Achse hin frei) – an der Tasche
   mit Ecken R 4 nach dem Ø 12 T3 Ø 6 (`szenario_ecken`). Scharfe Ecken nicht: dort
   kommt kein Fräser ganz hin, wie weit, entscheidet man selbst.
6. **Nut** – mit Rampe oder Trochoide statt Vollschnitt. Aufwand klein bis
   mittel. Gebaut (P-2026-10-01-40, 0.56.0) für geschlossene Langlöcher, mit und
   ohne Grund (S3g, „Nut“). Offene Nuten (P-2026-10-01-47, 0.62.0): an einem Ende
   offen (ein Halbkreis, zwei Geraden bis zum Rand) oder an beiden (zwei parallele
   Wände, die freien Seiten zueinander, der Grund dazwischen; von einer Wand aus über
   den Grund gefunden); hinter jedem offenen Ende wird Luft geprüft (quer über die
   Breite, unten, mittig, oben). Die Trochoide beginnt draußen – hinab in der Luft, der
   erste Kreis nimmt gerade ae, keine Helix –, läuft bis ans andere Ende und dort
   hinaus (am Halbkreis die nächste Lage mit der Helix zurück); die Vollnut in Lagen von
   außen geradeaus; die Wände im Gleichlauf an der einen hinein, außen oder um den
   Halbkreis hinüber, an der anderen heraus. Platte 60 × 40, Nut 16 breit, 8 tief, ganz
   durch, Standardfräser: 0,85 min, 46 Kreise, kein Eintauchen, keine Rampe, im Quader
   leer und die Wände fertig (`test_nut_offen`, `szenario_nut_offen`); die Kontur an den
   Wänden 2,2 min. **Bögen statt Kreisen** (P-2026-10-02-22, Manuel: „im Gleichlauf
   einen Halbkreis fahren, so dass mittig eine Delle entsteht, im Eilgang oder
   Schnellvorschub wieder auf die andere Seite und die nächste Morph-Bahn“): In offenen
   Nuten fährt je Schritt nur noch der Halbkreis, der schneidet – im Gleichlauf (M3: gegen
   den Uhrzeigersinn, G3) von der einen Wand nach vorn durchs Material zur anderen –, dann
   quer über die freie Seite zurück im Schnellvorschub (`RUECKWEG` = 3 × vf als G1: im
   Eilgang fährt nicht jede Steuerung gerade, und G0 auf Tiefe neben der Wand wäre auf
   manchen Maschinen gefährlich), an der Wand ein Stück vor in den nächsten Bogen. Die
   ersten Bögen morphen vom geraden Rand zum Halbkreis (ihre Enden bleiben bei −R an der
   Wand, ihre Mitte rückt je Bogen vor) – keiner schneidet in der Luft. Jede Lage beginnt
   draußen am offenen Ende, ohne Helix; so hat eine offene Nut keine Grenze in der Breite
   mehr („zu breit“ gilt nur noch für geschlossene). **Schonend**: In der Delle umschlingt
   der Fräser das Material weiter als an einer geraden Wand – mit dem Schritt ae wären es
   in der Nut 16 breit mit Ø 12 rund 70° statt 41°, der Span 1,4-mal so dick. Der Schritt
   ist darum so klein, dass der Eingriffswinkel dem auf gerader Bahn mit ae gleicht
   (`_bogenschritt`: s² + 2 (r + R − ae) s = 2 r ae, r der Radius der Bögen): dort 0,40
   statt 1,5 mm, in einer Nut 30 breit 0,95, in breiten fast ae; der Vorschub bleibt voll.
   **Abgelöst** (P-2026-10-02-56, Manuel zu 12.1: „a“): Der Schritt folgt jetzt der Last – im
   Mittel ae je mm Weg, in der Mitte der Bögen kurz bis 1,7 ae (12.1); in der Nut 16 0,58 mm.
   Gemessen (`test_nut_offen`): Nut 16 breit 1,75 min (vorher 0,85 – die Kreise schnitten
   dort zu dick), weiter schneller als die Kontur (2,2 min); dieselben Kreise mit dem
   kleinen Schritt bräuchten etwa ein Viertel mehr. Der Prüfstand misst jetzt auch, was im
   Schnellvorschub abgetragen würde (`schnell_abtrag`, muss 0 sein). Offen: die
   geschlossene Nut (Trochoide) noch mit dem Schritt ae – sie schneidet in schmalen Nuten
   ebenso dick (Frage an Manuel). Ihr Kreis läuft aber hinten durch Luft, die der vorige
   freigefräst hat: Dort und von Kreis zu Kreis jetzt im Schnellvorschub (P-2026-10-02-27,
   `_luft_hinten`: ganz in der Hülle des vorigen Kreises, solange cos θ ≤ −s / (2 r) – in der
   Nut 20 mit Ø 12 je Kreis 2 × 64°); geschnitten wird wie bisher. Prüfplatte (Nut 20 × 50 und
   Vollnut 14) 1,84 → 1,69 min, im Schnellvorschub nichts abgetragen (`test_nut`). **Dabei gefunden**: Auf dem Grund einer Nut ist Räumen nur scheinbar
   schneller – es schneidet zuerst in voller Breite (an der offenen Nut 0,19 min, ein
   Wirkungsgrad von 348 %, dazu 1,5 mm³ im Eilgang). Kann die Nut sie fräsen, treten
   Räumen und Planfräsen an Nutgründen nicht mehr an; ihre Zeile sagt warum (auch an der
   geschlossenen Nut 20 × 50, wo Räumen bisher den Haken bekam).
7. **Bohren, Zirkularfräsen, Gewinde** – FreeCADs Operationen übernehmen; der
   Assistent legt sie mit den Schnittwerten aus der Werkzeugverwaltung an
   (Bohrer, Senker, Reibahle, Gewindebohrer sind schon Werkzeugarten).
   Aufwand klein. Gebaut: Bohren, Bohrung fräsen, Zentrieren, Senken, Gewinde bohren und
   fräsen (S3g) und Reiben (P-2026-10-01-41, 0.57.0). **Flansch** (P-2026-10-02-12, 0.74.0):
   Oberseite, Außenwand, Mittelbohrung Ø 40 und sechs Bohrungen Ø 9 zusammen angeklickt – der
   Assistent bot „Bohren“ gar nicht an (sein Bohrer bohrt die Ø 40 nicht), und „Bohrung fräsen“
   stand rot („Ø 9 kleiner als der Fräser“): „Anlegen“ ging nicht. Jetzt teilen sie sich die
   Bohrungen – „Bohren“ nimmt die, die sein Bohrer bohrt (der Bohrer, der die meisten bohrt, ist
   vorgewählt), „Bohrung fräsen“ den Rest; der Wettbewerb läuft je gleiche Flächen (wer allein
   steht, behält den Haken). Am Block mit Durchgangsbohrung Ø 20 und Sackbohrung Ø 34
   (`szenario_bohren`) bohrt jetzt der Bohrer Ø 20 die durchgehende, statt dass „Bohrung
   fräsen“ beide fräst; `szenario_flansch`. **Deckel** (P-2026-10-02-13, 0.75.0): Platte mit
   Tasche R 6 und vier Bohrungen Ø 6,6, alle Flächen angeklickt – „Bohren“ bohrte die vier, doch
   „Bohrung fräsen“ blieb rot angehakt („Ø 6,6 kleiner als der Fräser“): Den roten Block nahm der
   Wettbewerb nur heraus, wenn alle Gegner der Gruppe dieselben Flächen hatten, und die Kontur
   hatte auch die Wände der Tasche. Jetzt teilt er die Gruppe nach gleichen Flächen, auch die
   nicht angetretenen Blöcke: Wo einer geht und ein anderer rot ist, verliert der rote den Haken
   (`szenario_deckel`: „Räumen T1“, „Bohren T2“, „Kontur T1“). **Formplatte**
   (P-2026-10-02-14, 0.76.0): Oberseite, Kugelmulde und vier Bohrungen angeklickt – die Mulde
   bekam gar keine Operation: 3D-Schruppen und 3D-Schlichten schlugen sich nur vor, wenn allein
   Freiformflächen gewählt waren. Jetzt, sobald eine dabei ist (gefräst werden nur sie);
   `szenario_formplatte`: Planfräsen, Bohren, 3D-Schruppen T1, 3D-Schlichten T3. **Lagerbock**
   (P-2026-10-02-15, 0.77.0): Lagerbohrung Ø 30 und zwei Senkungen Ø 14 × 8,5 über Ø 9 – die
   Kontur hatte die gebohrten Ø 9 in ihrer Liste (mit dem Ø 12 übersprungen, mit einem kleineren
   Fräser wäre doppelt gefräst worden). Jetzt nimmt die Kontur die Flächen jedes anderen
   angehakten Blocks heraus, außer er wetteifert mit ihr um genau dieselben
   (`szenario_lagerbock`). **Absatz** (P-2026-10-02-17, 0.79.0): Block 80 × 50 × 30 mit einem
   Absatz 15 × 10 vorn, Oberseite, Absatzboden und -wand gewählt – die Kontur fuhr 12 Bahnen
   vom Rohteil her (etwa 2 min), durch Luft: Den Boden davor hatte das Planfräsen schon
   gefräst. Jetzt nimmt sie nur den Rest, den es an der Wand lässt (parallel zu seinen Zeilen
   höchstens ein Zeilenabstand, `planfraesen_bahn.rest_an_der_wand`), sobald das Planfräsen
   oder das Räumen die Böden vor allen ihren Wänden fräst (`kontur_bahn.boeden_vor`) – auch
   um einen Zapfen („… den Boden davor räumt das Räumen“: 1 Bahn). Nimmt der Wettbewerb dem
   Räumen den Haken, rechnet die Kontur danach noch einmal – sonst stand „… die Tasche räumt
   das Räumen“ ohne Räumen (`szenario_absatz`, `szenario_zapfen`).
8. **Fasen / Entgraten** – an Kanten in der Ebene mit Fasenfräser oder
   Kugelfräser als Kantenbruch; Breite einstellbar; **auch an Kanten im Raum**
   und rundum (V4d). Aufwand mittel. Gebaut: rundum (V4d, 0.36.0) und im
   Quader mit dem Fasenfräser an Oberkanten (S3g, „Entgraten“, 0.49.0).
9. **Gravieren** – FreeCADs Engrave/Vcarve übernehmen. Aufwand keiner.

### 4.2 3D – Freiformflächen

Grundlage für alles hier: ein **Höhenfeld** (Abschnitt 7) – die Fläche als
Raster z(x, y) aus dem Netz, plus die Hüllfläche des Fräsers darüber
(„Dropcutter“ mit numpy, wie `vierachs_huelle` es um die Achse rechnet, nur
eben). Kein OCL.

1. **Schruppen ebenenweise** – Lagen von oben, jede Lage eine Tasche adaptiv
   (4.1.2) auf der Fläche, die in dieser Höhe frei ist; Restmaterial aus dem
   Abtrag. *Besser:* Adaptive kennt keine 3D-Grenze, Surface kann nicht
   schruppen. Aufwand groß (baut auf 4.1.2). Gebaut als „3D-Schruppen“
   (P-2026-10-01-45, 0.60.0): `schruppen3d_bahn` nimmt den Kern des Räumens über
   dem ganzen Teil – gesperrt, wo die Hüllfläche mit Aufmaß über der Lage liegt –,
   Hauptlagen gleich weit bis zum tiefsten Punkt der Freiformflächen plus Aufmaß, je
   höchstens ap, geräumt in den Varianten des Räumens (die schnellste zählt). Nach
   jeder Hauptlage **Zwischenlagen** (Vorschlag 1 mm) hinauf bis zur vorigen, von oben
   nach unten, nur wo über der Lage Material steht, das der Fräser erreicht: Ein Raster
   merkt sich je Zelle die Materialhöhe (gesenkt, wo die Stirn fuhr); die Ringe dort
   von außen bis an die Fläche, der erste so weit draußen, dass er gerade ae vom
   äußersten Material nimmt, mit weiterem ae (so viel Material je mm wie in der
   Hauptlage, ae · ap gleich, höchstens R – bei Manuels fz ohne Ausdünnung bleibt der
   Span höchstens fz); das Einfahren mit der Schwelle der Hauptlage, der Eilgang hinab
   bis über das höchste Material unter der Stirn; die Ringe aus dem Raster geglättet
   (0,4 Zellen – sonst hielt die Maschine an jeder Zacke). Gemessen mit dem
   Standardfräser (`test_schruppen3d`): Kuppel Ø 40, 10 hoch, auf der Platte 60 × 60 –
   1 Lage und 9 Zwischenlagen, 6,1 min (ohne Zwischenlagen 2,7 min, aber bis 7,6 mm
   Treppe; bis P-2026-10-01-48 5,4 min – die Ringe der Hauptlage bissen in die Kuppel,
   Eingriff bis 4,8 ae, siebenmal senkrecht ins Material; seit P-49 höchstens 1,6 ae); im Quader nirgends ins Teil, im Eilgang nichts, auf der Platte genau 0,3,
   auf der Kuppel senkrecht 0,4 … 1,6 mm. Eine Schale R 25, 10 tief: nur
   Zwischenlagen, je über die Rampe, 1,1 min; in der Höhlung bleibt unter der ebenen
   Stirn bis 2,2 mm (der Bogen unter dem Fräser). Im Assistenten der Block
   „3D-Schruppen“ (vorgeschlagen für Freiformflächen, vor dem 3D-Schlichten;
   `szenario_schlichten3d`). Offen: sind ebene Flächen mitgewählt, räumt danach das
   Räumen ihren Boden noch einmal ganz (es weiß nicht, was schon weg ist); die
   Zwischenlagen mit der Kugel (Restschruppen, Punkt 2).
2. **Restschruppen** – kleiner Fräser nur dort, wo der große nicht hinkam
   (Abtrag). Aufwand mittel. Gebaut (P-2026-10-02-02, 0.66.0) – ohne Abtragsmodell: Was der
   große Fräser (ebene Stirn) stehen ließ, folgt aus seiner Hüllfläche – je Zelle die tiefste
   Lage seiner Stirn über ihr, gleitend über die Scheibe (ohne die Treppe seiner Lagen, die
   nimmt das Schlichten). Damit beginnt das Raster des 3D-Schruppens für den kleinen; jede Lage
   räumt wie eine Zwischenlage, nur wo Material steht, das er erreicht. Als 3D-Schruppen mit
   `DurchmesserDavor`/`EckenradiusDavor` („Restschruppen T5“); im Assistenten der Block
   „Restschruppen“ (Haken von Hand, der größte kleinere Fräser, Ø und Form davor vom
   3D-Schruppen). Gemessen (`test_restschruppen`): zwei Kuppeln R 12 mit 5,2 mm zwischen den
   Füßen, nach Ø 12 (4,2 min) mit Ø 6: 0,28 min, nur im Tal, dort 62 statt 138 mm³ über dem
   Aufmaß (das Höchste 2,2 statt 4,1 mm – auch Ø 6 kommt im Spalt nicht ganz hinunter),
   nirgends ins Teil; eine Kuppel allein: „Kein Rest“ (`szenario_restschruppen`). Dabei
   gefunden: Der Morph des Räumens rechnete an zwei Kuppeln fast endlos – jetzt nur mit einer
   Insel und mit einer Bremse, wenn er nicht vorankommt.
3. **Schlichten Zeilen** (parallel) – Raster in einem Winkel, Zickzack oder
   einseitig, **Grathöhe als Maß** (Schrittweite aus Grathöhe und Fräserform,
   `vierachs_bahn.rillenhoehe` gibt es schon), Zeilen nur über der Fläche,
   Bögen an den Umkehrpunkten. Aufwand mittel. Gebaut als „3D-Schlichten“
   (P-2026-10-01-42, 0.58.0): `schlichten3d_bahn` – Freiformflächen (nach oben,
   weder eben noch senkrecht, keine gezeichnete Fase oder Senkung); die Spitze
   auf der Hüllfläche des ganzen Teils (`hoehenfeld.je_zeile`); gefräst nur, wo
   die Hüllfläche mit den gewählten Flächen höher liegt als ohne sie (zwei
   Rechnungen je Zeile – am Fuß einer Kuppel endet die Zeile, wo die Platte den
   Fräser hält); der Abstand aus der Grathöhe (`Form.kammhoehe`, Kugel Ø 6 bei
   0,01: 0,49); längs X und Y gerechnet, die schnellere zählt; Zickzack, nahe
   Enden 0,1 mm über der Hüllfläche beider Zeilen hinüber, Lücken unter 10 mm
   auf der Hüllfläche durch; Douglas-Peucker (0,002 mm); das Aufmaß senkrecht
   zur Fläche (`Form.mit_aufmass`); im Eilgang nur bis über das Rohteil.
   Gemessen: Kuppel Ø 40, 10 hoch, Kugel Ø 6 – 87 Zeilen, 3,5 min, 1,7 s
   Rechenzeit; im Quader −0,007 … +0,022 mm auf der Kuppel (`test_schlichten3d`,
   `szenario_schlichten3d`). **Im Winkel** (P-2026-10-05-08, nur auf Wahl – Richtung „winkel“,
   Eigenschaft „Winkel“, Vorgabe 45°): das Teil um −Winkel um Z gedreht, längs X gerechnet (mit
   Höhenlinien, Maske und Rest wie sonst), die Bahn zurückgedreht; 0° und 90° sind längs X und
   Y. „auto“ rechnet ihn nicht mit – was ohne Vorgabe gewinnt, bleibt. Kuppel, 30°: 4,39 min, 87
   Zeilen, im Quader −0,008 … 0,020 mm. **Einseitig** (P-2026-10-05-09, nur auf Wahl –
   Eigenschaft „Einseitig“): jede Zeile in dieselbe Richtung, zurück im Eilgang 2 mm über dem
   Höchsten der Hüllfläche zwischen beiden Zeilen, im Eilgang hinab bis 2 mm über den Anfang,
   dann eintauchen. Kuppel längs X ohne Höhenlinien: 5,02 statt 3,58 min im Zickzack (zuerst 6,84
   – der Fräser tauchte von über der Kuppel bis an ihren Fuß im Eintauchvorschub), im Quader
   −0,007 … 0,022 mm. Offen: Bögen an den Umkehrpunkten; „Z-konstant“ für die steilen Stellen
   (Punkt 4).
4. **Z-konstant** (Höhenlinien) für steile Bereiche, **Steil/Flach**: über
   einem Grenzwinkel Höhenlinien, darunter Zeilen – in einer Operation.
   *Besser:* Surface und Waterline getrennt lassen Rippen und Stufen. Aufwand
   mittel bis groß. Gebaut als Steil/Flach im „3D-Schlichten“ (P-2026-10-01-43,
   0.59.0): die Hüllfläche zusätzlich im Raster (0,25 mm), die Neigung aus ihrem
   Gradienten; Zeilen nur, wo es flacher ist als der Grenzwinkel (45°, Eigenschaft
   „Grenzwinkel“, 0: nur Zeilen), Höhenlinien (Marching Squares aus
   `raeumen_bahn`), wo es steiler ist, überlappend um 3°; in z so weit auseinander
   wie die Zeilen in der Ebene, von oben nach unten, im Gleichlauf (das Material –
   die höhere Hüllfläche – rechts), nahe Stücke gleitend verbunden; kurze Lücken der Maske
   (bis R) entlang einer Höhenlinie fährt sie durch (B-013, P-2026-10-04-12: in der Mulde des
   Testteils mit der Kugel Ø 8 65 statt 11 Hübe im Vorschub, 1,01 → 0,92 min). An der
   Halbkugel R 15 (Fuß senkrecht): an der Flanke 0,026 statt 0,056 mm, 4,2 statt
   3,2 min. An der Grenze liegen Zeilen und Höhenlinien im Raum um √2 weiter
   auseinander als in Ebene bzw. Wand – der Grat dort bis zum Doppelten; genau
   hält ihn erst „Äquidistant“ (Punkt 5). Dazu die **Spirale** (P-2026-10-01-48,
   0.63.0): archimedisch von der Mitte der flachen gewählten Stellen nach außen, je
   Umlauf um den Zeilenabstand, die Spitze auf der Hüllfläche aus dem Raster
   (bilinear – zwischen den Knoten an einem Knick höher, nie tiefer), gefräst nur, wo
   die gewählten Flächen die Höhe bestimmen und es flacher ist als der Grenzwinkel;
   ohne Wenden, im Gleichlauf (gegen den Uhrzeigersinn nach außen: das Material
   rechts). Sie rechnet neben längs X und längs Y, die schnellste zählt – aber nur mit
   Steil/Flach: Ihr Abstand liegt in der Ebene, an jeder Flanke einer Kuppel quer zur
   Steigung; ohne Höhenlinien bliebe an der Halbkugel 0,15 statt 0,056 mm stehen, die
   schnellere Zeit wäre nicht dasselbe Ergebnis. Gemessen (`test_schlichten3d`): die
   Kuppel 3,97 statt 4,51 min (45 Umläufe, im Quader −0,007 … 0,024 mm), die Halbkugel
   mit Steil/Flach 3,69 statt 4,2 min bei 0,026 mm an der Flanke.
   **Versuch zum Besprechen (2026-10-05): Höhenlinien als Rampe.** Statt jede Höhe einzeln zu
   umfahren und senkrecht auf die nächste zu setzen (die Absätze liegen übereinander – eine Naht
   an der Wand), sinkt der Fräser im Umlauf stetig von Ring k auf Ring k+1: z gleichmäßig, die
   Lage auf der Strecke zwischen beiden Ringen dort, wo die Hüllfläche genau diese Höhe hat (nie
   darunter); oben ein voller Ring, unten einer. Nur wo jede Höhe ein geschlossener Ring ist
   (Mulde, Zapfen); zerfällt eine Höhe in Stücke, bliebe es dort bei Höhenlinien. Gemessen an der
   Kugelmulde R 12,5 (Kugel Ø 6, Grat 0,01, 45°): 1,06 statt 1,01 min, 1 statt 27 senkrechte
   Absätze, Rest an der Wand gleich (senkrecht gemessen 0,038 … 0,052), am obersten Rand 0,087
   statt 0,068 (dort ist die Hüllfläche unruhig, wo die Kugel die Kante berührt). Bild:
   `rampe_mulde_vergleich.png` (an Manuel). Nicht gebaut – Entscheidung bei Manuel.
5. **Äquidistant** (3D-Offset, gleichbleibende Grathöhe auf jeder Neigung) –
   die feinste Schlichtstrategie. Aufwand groß; nach 3 und 4. Gebaut (P-2026-10-02-04,
   0.68.0) als fünfte Richtung des 3D-Schlichtens („aequidistant“): Auf der Hüllfläche im
   Raster der kürzeste Weg im Raum vom Rand der gewählten Flächen (`_abstandsfeld`: 16
   Nachbarn bis zum Rösselsprung, höchstens 2,7 % zu lang – die Ringe also eher enger; Zeile für
   Zeile hin und zurück, in der Zeile mit der laufenden Summe der Schritte; nur numpy, kein
   SciPy), daraus die Linien gleichen Abstands alle Zeilenabstand (Marching Squares) – Ringe vom
   Rand nach innen, im Raum überall gleich weit, flach wie steil, ohne Höhenlinien; der innerste
   höchstens einen halben Abstand unter dem höchsten Wert. Im Gleichlauf, von Ring zu Ring der
   nächste Anfang. Wo die Ringe beider Seiten an einem flachen Grat enden (die Mitte eines
   Rechtecks), einmal den Grat entlang (`_grate`: der Grat des Abstandsfelds, längs flacher als
   0,5, wo der letzte Ring mehr als einen halben Abstand entfernt liegt; verkettet wie beim
   Bleistift) – an der Welle ohne ihn 0,04 mm in der Mitte. Tritt wie Spirale und Fläche
   entlang nur mit Steil/Flach an. **B-014 (P-2026-10-04-27):** Liegen die vier Rasterpunkte um
   einen Ringpunkt mehr als 5 mm auseinander (eine Stufe der Hüllfläche – die Kugel stößt an eine
   senkrechte Wand), gilt dort die genaue Höhe gegen die Dreiecke im Umkreis, und die Stelle nur,
   wo die gewählten Flächen die Höhe bestimmen – bilinear lag die Kugel in einer Kavität mit
   runden Ecken bis 0,088 mm in der Wand. Gemessen (Kugel Ø 6, Grathöhe 0,01, 796 mm/min): Kuppel – 51
   Ringe, 5,07 min (Fläche entlang 4,29 bleibt), auf der Kuppel höchstens 0,017 statt 0,020;
   Halbkugel 4,91 min, an der Flanke 0,021 mm (Höhenlinien mit Zeilen 0,026, Fläche entlang
   0,034); Welle 6,7 min (Zeilen 6,41 bleiben). Ecken unter 90° ohne eigenen Gang:
   *nachgemessen 2026-10-05* – an der Welle liegt der Rest gleichmäßig verteilt (99 % unter
   0,016 mm), die 0,03 mm sind eine einzelne Zelle bei (56, 4), nicht die Winkelhalbierenden der
   Ecken; ein eigener Gang dort brächte nichts – gelassen.
6. **Bleistift** (Kehlen) – dort, wo zwei Flächen sich treffen und der Fräser
   nicht hinkam. Aufwand mittel (Abtrag: rot/gelb-Stellen als Bahn). Gebaut
   (P-2026-10-01-46, 0.61.0) – nicht aus dem Abtrag, sondern aus der Hüllfläche:
   Wo die Kugel zwei Flächen zugleich berührt, knickt ihre Hüllfläche nach oben
   (V). `bleistift_bahn` rechnet die Hüllfläche im Raster (0,25 mm, wie das
   3D-Schlichten), sucht in vier Richtungen die zweite Differenz durch den Abstand –
   größer als 0,3 (die Steigung springt um mehr als 17°; glatte Flächen bleiben weit
   darunter) –, nimmt nur das Maximum quer zum Knick und nur an den gewählten Flächen,
   legt den Punkt zwischen die Zellen (die Spitze des V aus den Nachbarn), verkettet zu
   Linien, glättet, rechnet die Höhe an jedem Punkt genau (`huelle_an`, alle 0,5 mm) und
   vereinfacht im Raum (0,003 mm). Gemessen (`test_bleistift`): Kuppel R 25 auf der
   Platte, Kugel Ø 6 – ein Ring bei r 21,44 … 21,45 (gerechnet 21,45), z 10,000 …
   10,005, 135 mm, 0,2 min; im Quader am Ring und an der Berührstelle der Kuppel fertig,
   nirgends ins Teil; die Halbkugel R 15 (am Fuß senkrecht) bei r 17,75; eine Kuppel ohne
   Platte: keine Kehle, ein Satz. Im Assistenten der Block „Bleistift“ nach dem
   3D-Schlichten, den Haken setzt man selbst (`szenario_bleistift`). **Mehrere Bahnen**
   (P-2026-10-05-10, nur auf Wahl – Eigenschaft „BahnenJeSeite“, „Seitenabstand“; im Assistenten
   „Breite je Seite“ in mm, daraus die Bahnen aufgerundet): je Seite neben der Kehle, quer im
   Zeilenabstand für 0,01 mm Grat – im Raum gemessen (an einer steilen Seite quer weniger weit:
   ein Schritt mit dem Höhenunterschied, nachgerechnet), die Höhe genau an der geglätteten
   Stelle; von außen zur Kehle, abwechselnd links und rechts, die Kehle zuletzt, dazwischen ein
   kurzer Hub 2 mm über dem Höheren (statt über das Rohteil). Kuppel mit drei je Seite: auf der
   Platte Ringe bei r 21,93 / 22,42 / 22,91, an der Kuppel im Raum 0,49 hinauf, 1,29 min (eine
   Kehle 0,19), nirgends ins Teil (`test_bleistift`, `szenario_bleistift`).
7. **Fläche entlang** (Flowline) – Zeilen folgen den Flächenkurven (UV);
   für Kegel, Rohre, Übergänge. Aufwand mittel bis groß. Gebaut (P-2026-10-02-03, 0.67.0)
   als vierte Richtung des 3D-Schlichtens („flaeche“): je gewählter Fläche die Kurven
   gleicher Parameter, längs u und längs v gerechnet (die schnellere), quer so dicht, dass
   zwei Nachbarn im Raum nirgends weiter als der Zeilenabstand auseinander liegen (an 64
   Stellen je Kurve gemessen, quer vier Schritte je Abstand vorgerechnet); die Spitze dort,
   wo der Fräser die Fläche an der Kurve berührt (die Achse um die Stütze des Fräsers zur
   Seite der Normale – die Kugel: P + r · n), ihre Höhe aus der Hüllfläche im Raster (nie
   ins Teil, auch nicht an Nachbarflächen), gefräst nur, wo die gewählten Flächen die Höhe
   bestimmen. Offene Kurven im Zickzack, geschlossene (ein Kreis um eine Kuppel) immer im
   Gleichlauf, von einem Kreis zum nächsten nur ein Schritt quer. Weil die Abstände im Raum
   liegen, braucht sie keine Höhenlinien; sie tritt wie die Spirale nur mit Steil/Flach an.
   Gemessen (Kugel Ø 6, Grathöhe 0,01, 796 mm/min): Kuppel Ø 40 auf der Platte – 46
   Breitenkreise, 4,29 min (Spirale mit Höhenlinien 4,93, Zeilen 5,57), auf der Kuppel
   −0,006 … 0,020 mm senkrecht zur Fläche; halbe Walze R 15 × 60 – 92 Linien längs der
   Achse, 7,21 min (Zeilen mit Höhenlinien 10,33, Spirale 14,26), −0,003 … 0,017 mm; eine
   Welle (B-Spline) 6,57 min – dort sind Zeilen längs X mit 6,41 schneller und bleiben.
   Dabei gefunden und behoben: Wo die Kugel nur noch über eine Kante rollt (an der
   Außenkante eines Teils, an einem Absatz), fällt die Hüllfläche fast senkrecht; aus dem
   Raster gerechnet schnitten Höhenlinien und Spirale dort 0,05 mm in die Seite (an der
   Kante 0,32 mm senkrecht). Jetzt fahren alle Richtungen nur, wo der Fräser die gewählten
   Flächen innen berührt (`_beruehrt`: ihre Dreiecke um die Stütze verschoben ins Raster
   gelegt, eine Zelle weiter) – die Welle ohne Platte −0,010 mm in jeder Richtung, die
   nutzlose Höhenlinie am Rand fällt weg (`test_schlichten3d`, `szenario_schlichten3d`). In
   der Oberfläche durchgespielt (P-2026-10-02-06): `szenario_schlichten3d_rand` – der Block mit
   der Welle, die Operation auf die Spirale gestellt, „Auf der Maschine prüfen“ auf der
   3-Achs-Fräse: nirgends ins Teil; `szenario_mulde` – eine Kugelmulde R 30 (12 tief) in der
   Platte, 3D-Schruppen in Treppen von oben und 3D-Schlichten (Spirale mit Höhenlinien, 4,6
   min), am Rand der Mulde rollt die Kugel über die Kante zur Oberseite: nirgends ins Teil.
8. **Restschlichten** – kleiner Fräser, nur wo nötig (aus Abtrag). Aufwand
   mittel (nach 6). Gebaut (P-2026-10-02-01, 0.65.0) – nicht aus einem Abtragsmodell,
   sondern aus beiden Fräsern: Die Hüllflächen des großen (davor) und des kleinen im
   Raster, daraus je die Fläche, die der Fräser stehen lässt, wenn seine Spitze überall
   fährt (gleitendes Minimum mit dem Profil der Stirn: je Stelle die tiefste Unterseite
   im Umkreis R); wo die des großen mehr als 0,01 mm höher liegt, ist Rest – nur über dem
   Teil (neben einer Kante rollt der große Fräser höher um sie, in der Luft) und über dem
   Grat, den das Raster selbst unter der kleinen Stirn lässt (Raster² ÷ 4 r; sonst fand die
   grobe Vorschau 0,02 mm „Rest“ an einer Kuppel ohne Kehle). Die Maske um R + Zeilenabstand
   erweitert; dort fährt das 3D-Schlichten wie sonst (Höhenlinien, Zeilen, Spirale, die
   schnellste). Als 3D-Schlichten mit `DurchmesserDavor` und `EckenradiusDavor` („Restschlichten
   T4“); im Assistenten der Block „Restschlichten“ (Haken von Hand, vorgewählt der größte
   kleinere Kugelfräser, Ø und Form davor vom 3D-Schlichten im Fenster). Gemessen
   (`test_restschlichten`): Kuppel Ø 40 auf der Platte, nach Kugel Ø 6 mit Kugel Ø 2 – 3,8 min
   (die ganze Kuppel mit Ø 2: 9,1), in der Kehle am Fuß 0,18 statt 0,44 mm (gerechnet
   0,13 und 0,40), nirgends ins Teil; eine Kuppel ohne Kehle: „Kein Rest“
   (`szenario_restschlichten`). Offen: die Platte daneben fährt es nicht (das 3D-Schlichten
   fährt nur Freiformflächen) – die Kehle selbst nimmt der Bleistift.

### 4.3 Rundum und 4 Achsen (W-003)

Gebaut: Rundum schruppen und schlichten, Flächen wählen, hin und her.
Weiter (spezifikation_vierachs.md, V4c/V4d), in dieser Reihenfolge:

1. **Linien längs** – Zeilen längs der Achse bei festem Winkel: Nut,
   Abflachung, Nocke mit Kugel-/Torusfräser. Aufwand klein bis mittel.
2. **Plan indexiert (3+1)** – Rundachse steht, ebene Fläche parallel zur Achse
   wird wie beim Planfräsen gefräst (braucht Y an der Drehmaschine oder A an
   der Fräse); mit Versatz quer zur Werkzeugachse in Abfahren, Kollision und
   Abtrag. Aufwand mittel. **Passfedernut** (P-2026-10-02-05, 0.69.0): Dabei gefunden –
   der Grund einer Passfedernut (8 breit auf der Welle Ø 30) bekam mit dem Fräser Ø 8 gar
   keine Bahn (die Wände stehen genau am Rand der Stirn, die Zeilen hielten an) und mit Ø 6
   blieben die Enden 4 mm stehen. Jetzt erkennt `vierachs_planbahn.nuten` den Nutgrund im
   Rahmen der Fläche (x längs, z ihre Normale, y = z × x) mit `nut_bahn.nuten` wie im Quader
   und fräst ihn mit der Bahn „Nut“: in voller Breite die Zickzack-Rampe (der Vorschub kleiner,
   `vierachs_bahn.Punkt.anteil`), schmaler die Trochoide, zuletzt die Wand rundum; zurück mit
   a = x, Höhe = z, q = −y, C fest, Bögen in Sehnen (0,005 mm). Eine zu breite „Nut“ (eine
   Abflachung zwischen zwei Wänden) fährt weiter Zeilen. Gemessen (`test_vierachs_plan`):
   Ø 8 in 0,26 min bis an die Enden (die Mitte des Fräsers auf der Mittellinie), Ø 6 als
   Trochoide 0,71 min; `szenario_vierachs_nut` auf der Beispiel-Drehmaschine: am Ende
   „nirgends ins Teil“. **Querbohrungen** (P-2026-10-02-07, 0.70.0): Eine gewählte Bohrung
   quer zur Stange – eine ganze Zylinderfläche, Achse rechtwinklig zur Stange, das Material
   außen (`vierachs_planbahn.bohrungen`) – fräst „Plan indexiert“ mit der Bahn „Bohrung
   fräsen“ (Helix hinab, Ringe, die Wand rundum) im Rahmen der Bohrung: die Rundachse auf ihre
   Öffnung, quer versetzt mit dem Y, wenn sie nicht durch die Mitte geht; eine durchgehende von
   beiden Seiten je bis zur Mitte der Stange. Der Grund jeder Seite als Kreisscheibe für den
   Vergleich auf der Stange (`boden_der_bohrung`). Gemessen (`test_vierachs_plan`): Welle Ø 30
   mit Sackbohrung Ø 10 × 8, einer um 3 mm versetzten und einer durchgehenden Ø 8 – vier Seiten,
   1,34 min mit Ø 6, die Mitte des Fräsers nie weiter als Radius − 3 von der Achse der Bohrung,
   nirgends ins Teil; `szenario_vierachs_querbohrung`. **Radial bohren** (P-2026-10-02-08,
   0.71.0): Ist bei „Plan indexiert“ ein Bohrer gewählt (`vierachs_plan.bohrer_von`), werden die
   Querbohrungen gebohrt statt gefräst (`vierachs_planbahn.gebohrt_punkte`, wie „Bohren“ im
   Quader): auf die Ebene R knapp über dem Material, hinab, tiefer als 3 × D in Hüben von 1 × D;
   eine durchgehende von beiden Seiten, jede mit der Spitze um ihre Länge über die Mitte (so hat
   sie überall den vollen Durchmesser, und X muss nur um die Länge der Spitze unter null – ganz
   durch von einer Seite bräuchte X bis −(R + Spitze)); eine Sackbohrung nur mit der Spitze des
   Bohrers unten (sonst ein Satz: mit ebenem Grund fräst sie ein Fräser). Der Assistent nimmt
   Bohrer in die Auswahl „Fräser“ auf und wählt einen vor, wenn nur Querbohrungen gewählt sind
   und er sie alle bohrt (`vierachs_planbahn.bohrer_passt`) – bohren ist schneller als fräsen;
   die Operation heißt dann „Radial bohren T2“ und trägt die Hübe. **Dabei gefunden**: Der Grund
   einer gebohrten Sackbohrung ist die Spitze, ein Kegel – mit der Scheibe am Ende der Wand als
   Grund meldete „Auf der Maschine prüfen“ bis 14 mm „im Teil“ (im Test −11,7). Jetzt kennt der
   Vergleich die Spitze (`vierachs_planbahn.Kegelgrund`, `restmaterial._kegel_radien`). Gemessen
   (`test_vierachs_plan`): Welle Ø 30 mit einer durchgehenden Ø 8, einer Sackbohrung Ø 8 × 22 und
   einer Ø 8 × 10, beide mit Spitze 118° – drei Bohrungen von vier Seiten, sieben Hübe, 0,21 min
   mit dem Bohrer Ø 8 (gefräst mit Ø 6: 1,34 min für die Querbohrungen oben); nirgends ins Teil;
   `szenario_vierachs_radialbohren`. Ein Tiefbohrzyklus als G83 (statt der Hübe als Sätze) folgt
   mit dem Postprozessor (W-005). **Sechskant** (P-2026-10-02-10, Szenario): SW 24 vorne auf der
   Welle Ø 30, alle sechs Flächen angeklickt, der Standardfräser Ø 12 (Planen mit ae 1,5, ap 25:
   Zeilen 1,5 breit, die 3 mm in einer Lage) – sechs feste Stellungen der Rundachse, nichts
   berührt sich, am Ende nirgends ins Teil (`szenario_vierachs_sechskant`). **Fräser und Bohrer
   zugleich** (P-2026-10-02-11, 0.73.0): Ein zweiter Aufruf des Assistenten am selben Teil legte
   einen zweiten Job an (oder öffnete die Plan-Operation zum Ändern) – Fräser und Bohrer im
   selben Job gingen nicht in einem Durchgang. Jetzt bietet „Plan indexiert“ neben dem Fräser
   einen Haken für den Bohrer an, wenn auch Querbohrungen gewählt sind und ein Bohrer sie alle
   bohrt (angehakt: bohren ist schneller); „Anlegen“ legt dann „Plan indexiert T1“ (ohne die
   Bohrungen) und „Radial bohren T2“ (nur sie) in denselben Job. Der Vorschlag nennt bei
   gemischter Auswahl jede Art (`szenario_vierachs_drehteil`: Abflachung, Mantelnut und
   Querbohrung an einer Welle – nichts berührt sich, am Ende nirgends ins Teil).
3. **Rundum entgraten** (V4d) – Kanten der gewählten Flächen, die Rundachse
   dreht mit. Aufwand mittel.
4. **Taschen und Nuten auf dem Mantel** – die Tasche in der Abwicklung rechnen
   (4.1.2/4.1.3), auf den Zylinder zurückwickeln (wie FreeCADs „wrap“, aber mit
   Abtrag und Kollision). Aufwand mittel. **Nut auf dem Mantel** (P-2026-10-02-09, 0.72.0):
   Gemessen, was es schon gab: An einer Nut 8 breit, 4 tief über 120° (der Grund ein Zylinder
   R 11 um die Stangenachse, die Enden Ebenen durch die Achse – wie mit „Nut“ in PartDesign
   gedreht) kam „Rundum schruppen“ mit dem Fräser Ø 8 gar nicht hinein (4 mm blieben), mit
   Ø 6 im Mittel 0,08 mm Rest in 1,33 min (1000 mm/min). Jetzt erkennt
   `vierachs_planbahn.mantelnuten` einen gewählten Nutgrund (Zylinder um die Achse, Material
   innen, weniger als der ganze Umfang, in der Abwicklung ein Rechteck), und „Plan indexiert“
   fräst ihn mit drehender Rundachse (`_mantelnut_punkte`): in der Mitte in voller Breite die
   Zickzack-Rampe wie die Vollnut im Quader (je Fahrt höchstens ap / 2, Vorschub nach dem
   Span), unten einmal hinüber, ist die Nut breiter, Zeilen zu beiden Seiten in voller Tiefe,
   höchstens ae auseinander. Rundum hält die Stirn vor den Enden so viel Abstand, wie sie am
   Grund breit ist (asin(r ÷ R)) – oben bleibt dort ein Keil stehen: Wände durch die Achse
   schneidet ein Fräser auf der Mitte nicht genau (das ginge nur mit dem Y). Gemessen
   (`test_vierachs_plan`): die Nut 8 × 4 über 120° und eine 12 × 3 über 90° mit Ø 8 – 0,43 min
   (500 mm/min), der Grund ohne Rest, nirgends ins Teil; `szenario_vierachs_mantelnut`. Offen:
   Nuten, die nicht rechteckig abgewickelt sind (Kurvennut, Schmiernut als Wendel), Taschen mit
   Inseln, die Enden mit dem Y genau.
5. **Nockenwellen, Exzenter** – rundum schruppen kann es; schlichten mit
   Linien längs und Grathöhe. Aufwand klein, prüfen. Geprüft (P-2026-10-02-06,
   `szenario_vierachs_nocke`): Welle Ø 30 × 100 mit einem Nocken Ø 44, 6 mm außermittig, auf
   der Beispiel-Drehmaschine – „Rundum schruppen“ (T1 Ø 12) und „Rundum schlichten“ (T2 Kugel
   Ø 6) angehakt und angelegt; „Auf der Maschine prüfen“: alle Achsen in ihren Grenzen,
   „Nichts berührt sich“, am Ende nirgends ins Teil.

### 4.4 5 Achsen

1. **3+2 indexiert** – Kopf oder Tisch schwenken, dann 2,5D/3D aus 4.1/4.2 in
   der geschwenkten Ebene; die Maschine liefert die Stellung, Reichweite und
   Kollision prüfen. Aufwand mittel (die Kette kann es – `reichweite` löst
   Rundachsen aus der Bahn).
2. **Simultan: Flankenfräsen (Swarf)** – die Fräserflanke liegt an einer
   Regelfläche an. Aufwand groß.
3. **Simultan: Schlichten mit Anstellwinkel** – Kugel/Torus mit Vor- und
   Seitenneigung für bessere Schnittbedingungen. Aufwand groß; nach 4.2.5.

Für Manuels Maschine (Drehmaschine mit C und Y) zählen zuerst 4.1, 4.3 und
4.2.3/4.2.4; 4.4 kommt, wenn eine 5-Achs-Fräse gebraucht wird.

## 5. Was überall besser sein soll – die Grundsätze

0. **Die Zeit entscheidet** (Manuel, 2026-10-01: „Natürlich muss man immer
   den schnellsten Weg für das gewählte Werkzeug finden … nur muss halt auch
   immer die schnellste Strategie gefunden werden“). Genau so:
   - *Gegeben* sind die Aufgabe (die gewählten Flächen, Wände und Taschen des
     Teils, das Rohteil) und das gewählte Werkzeug mit seinem Einsatz (ae,
     ap, vc, fz, Eintauchwinkel). Die Einsatzwerte sind die Grenze – mehr
     Eingriff gibt es nicht, weniger nur, wo die Geometrie es verlangt.
   - *Der schnellste Weg für dieses Werkzeug:* Jede Strategie hat
     Freiheitsgrade – Zeilenrichtung, Startstelle, Lagen (volle Schneide:
     so wenige wie möglich), Einstieg (Rampe, Helix, senkrecht), von innen
     oder von außen, Reihenfolge der Bereiche. Der Assistent **rechnet** die
     Varianten mit dem Zeitmodell (Vorschub aus dem Einsatz, Eilgang
     10 m/min, Beschleunigung 1 m/s², anhalten an Ecken – `bahn.zeit`,
     Spezifikation Simulation 4d) und nimmt die schnellste. Eine Regel ohne
     Rechnung gilt nur, wo sie die Zeit nachweislich begründet (Gleichlauf,
     Bögen statt Ecken).
   - *Die schnellste Strategie:* Alle Strategien, die die Aufgabe lösen
     können, treten mit derselben Zeit gegeneinander an. Der Assistent setzt
     den Haken bei der schnellsten und schreibt die anderen mit ihrer Zeit
     daneben – damit man sieht, warum. Keine Strategie wird gewählt, weil
     sie üblich ist.
   - *Der Maßstab fürs Bauen:* Manuels Platte mit dem Standardfräser
     (Abschnitt 11). Jede neue Strategie muss dort für ihre Aufgabe schneller
     sein als die bisherige, sonst kommt sie nicht in den Vorschlag; die
     Prüfung rechnet das nach.
   - *Vor der Zeit* stehen nur Sicherheit (nirgends ins Teil, Aufmaß,
     Kollision, Reichweite) und die Grenzen des Einsatzes – **und das
     Ergebnis** (Manuel, 2026-10-03: „wir haben ja als Spezifikation die Zeit
     als größten Faktor, was nicht ganz richtig ist … die Form des Bauteils
     und eben das Akkurate da schon auch mit reinnehmen … das Teil sollte
     danach schon so ausschauen, wie's ausschauen soll“; auf Nachfrage: „es
     hilft ja nichts, wenn man eine Platte mit einem Ø-20-Zapfen gezeichnet
     hat, aber der Zapfen ist dann nicht rund, weil die Werkzeugwege so
     schneller waren … die Werkzeugwege müssen SINNVOLL und SCHNELL sein,
     aber sie müssen natürlich auch das Bauteil abbilden“). Das heißt:
     Näherungen – das Raster (0,05 mm), die Vielecke des Adaptiv-Kerns, Ringe
     aus dem Abstandsfeld – gibt es nur beim Schruppen und nur hinter dem
     Aufmaß; **die letzte Bahn an jeder Fläche folgt der Zeichnung**: Wände
     und Zapfen die Kontur oder „Schlichten danach“ mit den Bögen und Kanten
     des Modells (G2/G3, kein Vieleck), Böden eben ohne Aufmaß, Bohrungen im
     gezeichneten Durchmesser, Freiformflächen das 3D-Schlichten in der
     gewählten Grathöhe. Nur Bahnen, die das Teil so hinterlassen, treten im
     Wettbewerb an; unter ihnen entscheidet die Zeit. Der Prüfstand
     (Abschnitt 9) hält das für Rest, Schnitt ins Teil, Eilgang im Material
     und Last. **Gebaut (P-2026-10-03-04):** Der Assistent sagt rot unter
     den Schritten, welche gewählte Fläche am Ende keine genaue Bahn hätte
     (`_fertige_flaechen` je Block: Planfräsen und Räumen ohne Aufmaß am
     Boden, Nut/Kontur/Bohrung mit „Schlichten“, „Schlichten danach“ mit
     seinen Haken, Bohren, Reiben, Senken, Gewinde, Entgraten, 3D-Schlichten;
     Schruppen mit Aufmaß zählt nicht), und welche Haken sie fertig machten:
     „Ohne genaue Bahn am Ende – das Teil wäre dort nicht, wie gezeichnet:
     Face3. Dafür anhaken: „Planfräsen“, „Schlichten danach“.“

   Gebaut: die Zeilenrichtung des Planfräsens (beide gerechnet, die
   schnellere; P-2026-10-01-24); die Varianten des Räumens (vom Rohteil her
   oder um die Inseln, beide gerechnet) und der erste Wettbewerb der
   Strategien – Planfräsen gegen Räumen auf denselben Flächen: der Assistent
   rechnet beide, sobald eins angehakt ist, setzt den Haken bei der
   schnelleren und schreibt an beide Zeilen, um wie viel (P-2026-10-01-25,
   0.44.0). Offen: Räumen gegen die Kontur in der Tasche (heute: Räumen für
   Taschenwände anhakbar, die Hilfe nennt die schnellste Folge), der Einstieg
   (Rampe/Helix/senkrecht nach Zeit), die Startstelle (am Ende der vorigen
   Operation), die Reihenfolge der Bereiche nach Eilgangweg.

   *Sichergestellt* wird das mit dem **Prüfstand** (`pruefstand.py`,
   `test_pruefstand.py`, P-2026-10-01-26; Manuel: „Finde einen Weg, das
   sicherzustellen … immer den definierten Fräser mit den definierten Werten
   und verschiedene Bahnen durchfahren“): Jede Strategie in jeder Variante wird
   mit dem Standardfräser an den Maßstabsteilen (Manuels 50 × 50 mit Zapfen,
   der Block mit Absatz, der Block mit Tasche, die Platte) gerechnet und im
   Quader Satz für Satz abgefahren. Gemessen werden Zeit, Vorschub- und
   Eilgangweg, Luft (Vorschub ohne Abtrag), Eintauchen und Rampen im Material,
   Halte, der Rest auf der Fläche, der Einschnitt ins Teil, der Abtrag im
   Eilgang und die Untergrenze – das Volumen durch ae · ap · vf, als wäre der
   Fräser nie aus dem Eingriff; Zeit zu Untergrenze ist der Wirkungsgrad.
   Vier Urteile lassen eine Bahn durchfallen: ins Teil geschnitten, etwas
   stehen geblieben, im Eilgang abgetragen, zu viel Luft. Dazu drei Regeln:
   jede Strategie nimmt von ihren Varianten die schnellste; zwischen den
   Strategien steht fest, welche wo gewinnt (Räumen auf dem Zapfen-Block und
   der Platte, Planfräsen am Absatz, Räumen + Kontur in der Tasche); und keine
   Bahn wird langsamer als ihre Bestmarke (`tests/bestmarken.json`) – schneller
   darf jede, dann werden die Bestmarken neu geschrieben, und der Verlauf sagt,
   warum. Der erste Lauf fand gleich drei Fehler: die Wandfahrt des Planfräsens
   lief vor dem Zapfen quer durch ihn (zum Anfang der vorigen Zeile statt zu
   ihrer nächsten Stelle), der Eilgang des Räumens fuhr beim Einfahren bis
   knapp über die Lage, auch wo unter der Stirn noch ein Rest stand, und die
   Ringe um die Zwickel neben einer Insel fanden keinen Eingang (ein ganzer
   Ring fängt jetzt dort an, wo einer passt). Mit den Messungen an der ganzen
   Platte (P-2026-10-01-27: Oberseite und Tasche in einer Operation, die Kontur
   nach dem Räumen, jede mit `vorher` – gezählt wird nur, was nach den
   vorigen Bahnen noch abgeht) fand er zwei weitere: Oberseite und Taschenboden
   in einem Räumen fuhren 20 mm ins Teil und brauchten 56 statt 34 min – die
   Hüllfläche ließ alle gewählten Flächen weg, auch den Taschenboden unter der
   Oberseite (jetzt eine Hüllfläche je Höhe, `hoehenfeld.netze_je_hoehe`, im
   Planfräsen derselbe Fehler, mit behoben) –, und die Varianten wurden in
   Taschen ungleich verglichen (dort zählt nur „inseln“: von innen nach außen).
   Die Platte gesamt – Räumen Oberseite und Tasche, Kontur Tasche, Kontur
   Zapfen – braucht 34,7 min (Untergrenze 31).

   Seit P-2026-10-01-49 misst er auch den **Eingriff** (Grundsatz 3: nie mehr
   als ae · ap): je Satz der Abtrag im Ausschnitt um ihn und seine größte Tiefe,
   über 3 mm Weg die Breite (Σ Abtrag ÷ Σ Weg · Tiefe; Rampen, Eintauchen und
   Eilgänge zählen für sich). Ein fünftes Urteil: mehr als 5 mm in voller Breite
   (über 0,75 · Ø, und Breite · Tiefe über ae · ap). Es fand, dass mehrere
   Bestmarken auf Vollschnitten standen: Das Räumen „rohteil“ biss mit dem Rechteck
   in die Inseln (auf der Platte 120 mm in voller Breite, 20 tief – jetzt Ringe aus
   dem Weg um die Inseln herum), am Absatz lief sein letzter Ring voll an der Wand
   (jetzt der Ring an der Wand mit dem Rest), die erste Zeile des Planfräsens griff
   0,8 · Ø breit ins Rohteil (auf der Platte 9,6 × 20 mm – jetzt an offenen Seiten
   höchstens so breit, dass Breite · Tiefe nicht über ae · ap liegt; steht vor der
   ersten Zeile eine Wand, wie in einer Tasche, hat sie keine freie Seite: dann je
   Lage höchstens ae · ap ÷ Ø tief), und das 3D-Schruppen erbte den Biss in die
   Kuppel (Eingriff bis 4,8 ae, jetzt 1,6). Ehrlich gerechnet: Platte Räumen 33,9
   statt 33,1 min, Planfräsen 41,9 statt 39,3; Zapfen-Block Planfräsen 5,7 statt
   4,8; Absatz Räumen 2,7 statt 2,0, Planfräsen 2,1 statt 1,7 – die Platte gesamt
   35,6 min. Die Rangfolge bleibt. Nur zum Vergleich gemessen (ohne Urteil über die
   Breite): die Kontur in der Bohrung Ø 34 (ihr Einfahrbogen nach der Rampe läuft
   durch volles Material, 8 mm; Bohrungen fräst „Bohrung fräsen“).
1. **Tangential ein- und ausfahren.** Nie senkrecht in die Wand; Bogen und
   Gerade nach Fräser-Ø; in Taschen Helix oder Rampe mit dem Winkel aus der
   Werkzeugtabelle (Eintauchwinkel gibt es schon).
2. **Bögen statt Ecken.** Zwischen Zeilen, in Ecken, an Umkehrpunkten – G2/G3
   in der Ausgabe, wo die Steuerung es kann (W-005).
3. **Gleichmäßiger Eingriff.** Schruppen mit ae aus „Schruppwerte planen“,
   Trochoiden, wo die Nut voll würde; in Ecken nicht mehr als das geplante ae.
4. **Gleichlauf** als Vorgabe, Gegenlauf wählbar. Gleichlauf heißt bei
   rechtsdrehender Spindel (M3): das Material rechts der Fahrtrichtung, wie
   bei G41 – um einen Zapfen im Uhrzeigersinn, in einer Tasche oder Bohrung
   gegen ihn. (Bis P-2026-10-01-27 stand hier „Material links“ – das war
   Gegenlauf; seit P-2026-10-01-28 richtig herum, Kontur und Räumen.) Steht der
   Werkzeug-Controller auf „Reverse“ (M4, Manuel 2026-10-02: die Spindel kann
   beide Richtungen), spiegeln alle Bahnen mit Gleichlauf die Richtung – das
   Material liegt dann links (`spindel.fuer_m3`; Kontur, Restmaterial,
   Entgraten, 3D-Schlichten, Räumen, Bohrung fräsen, Nut, Gewinde fräsen,
   3D-Schruppen; P-2026-10-02-20). FreeCADs eigene Operationen fragen danach
   nicht. **Allgemein, für jede Maschine** (Manuel: „es geht um alle Maschinen“,
   P-2026-10-02-23): Gleichlauf entsteht aus der Bewegung an der Schneide, nicht
   aus S allein. `spindel.ist_gleichlauf(achse, fahrt, material)` rechnet es im
   Rahmen des Teils: Werkzeugachse vom Halter zur Spitze, die Fahrt gegenüber dem
   Teil, die Seite des Materials – Gleichlauf bei M3, wenn das Material von der
   Spindel aus rechts der Fahrt liegt, (fahrt × −achse) · material > 0. Senkrecht
   über dem Tisch ist das G41; radial am Mantel macht die Rundachse die Fahrt: Die
   Spirale von „Rundum schruppen/schlichten“ dreht φ steigend, wenn sie zum Futter
   vorrückt (M3), fallend mit M4; die Wände der Mantelnut je Seite andersherum
   (vorn fallend, hinten steigend); Helix der Querbohrung und Passfedernut wie im
   Quader im Rahmen der Fläche. In welche Richtung C dafür an der Maschine dreht,
   rechnen die Befehle mit ihrem Drehsinn (C = −Drehsinn · φ) – so stimmt es auf
   jeder Maschine, mit C an der Drehmaschine wie mit A an der Fräse. „Rundum
   entgraten“ (P-2026-10-02-25): je Kante die Seite des Materials aus den beiden
   Flächen daran (wohin sie von ihr weg zeigen), daraus die Richtung jedes Stücks –
   um eine Abflachung herum bleibt es eine Fahrt. Die Zeilen hin und her wählbar
   (P-2026-10-02-24).
5. **Keine Luftschnitte.** Bahn nur dort, wo Material steht (Abtrag) – bei
   Zeilen, Lagen und Restbearbeitung.
6. **Restmaterial kennen.** Ein Abtragsmodell je Job (Abschnitt 7): jede
   Operation weiß, was die vorige ließ; „Rest“ ist eine Strategie, keine
   Schätzung.
7. **Vorschub nach Eingriff.** In Ecken und beim Austritt langsamer, auf der
   Geraden voll – aus der Spandicke, nicht aus dem Bauch.
8. **Grathöhe als Maß.** Schlichten fragt „wie glatt“ (Ra bzw. Grathöhe),
   nicht „welche Schrittweite“; die Schrittweite folgt aus Fräserform und
   Neigung.
9. **Toleranz und Glättung.** Punktabstand nach Sehnenfehler (haben wir:
   `_zusammengefasst`), Glättung ohne Verletzung der Toleranz (V6).
10. **Kurze Wege, ehrliche Zeit.** Reihenfolge der Bereiche nach Weg,
    Eilgänge über sicherer Höhe nur, wo nötig; die Zeit steht im Assistenten
    und im Prüffenster.

Und alles **geprüft**: Abtrag (Farben), Kollision, Reichweite – bevor es an
die Maschine geht.

## 6. Bedienung

- **Ein Assistent „Bearbeitung“** (der heutige „4-Achs-Bearbeitung“ wächst
  dazu): 1 Rohteil (Stange, Quader, aus dem Modell), 2 Flächen/Bereiche
  (anklicken, „alles“, „Oberseite“, „diese Tasche“), 3 Werkzeuge (Schruppen,
  Schlichten, Rest – aus der Werkzeugverwaltung, mit Schnittwerten), 4
  Vorschlag: „Tasche adaptiv mit T1, dann Kontur schlichten mit T2 – 4 min“
  – änderbar, mit Begründung, dann „Anlegen“. Ein Strg+Z nimmt alles zurück.
- **„Was willst du machen?“** bleibt die Frage in Schritt 2; die Antworten
  sind Strategien in Sätzen („Tasche ausräumen“, „Fläche glätten“, „Kanten
  brechen“), nicht Operationsnamen.
- **Vorschläge mit Grund:** „Zeilen längs, weil die Abflachung schmal ist“,
  „Höhenlinien oben, weil die Wand steiler als 60° ist“. Wer anderes will,
  wählt es – und sieht die Zeit beider Wege.
- **„Mehr …“** für Toleranz, Überlauf, Ein-/Ausfahrlänge, Gleich-/Gegenlauf;
  die Vorgaben stehen grau da.
- **Prüfen mit einem Klick** aus dem Assistenten (Abtrag, Kollision, Zeit) –
  vor „Anlegen“ als Vorschau, danach im Prüffenster.
- **Hilfe je Strategie:** was sie tut, wann sie passt, ein Bild.

## 7. Rechenkern

- **Höhenfeld** (`hoehenfeld.py`, neu): das Netz des Teils als Raster z(x, y)
  mit numpy – Auflösung nach Toleranz (0,01–0,05 mm) und Fräser-Ø; dazu die
  Hüllfläche je Fräserform (Kugel, Torus, Schaft, Kegel) als Faltung über dem
  Raster (Dropcutter). Wie `vierachs_huelle`, nur eben. Ohne OCL.
- **Abtragsmodell** (`restmaterial` verallgemeinern): heute die Stange als
  r(a, φ); für 2,5D/3D ein Höhenfeld des Rohteils, das jede Operation
  abträgt (Dexel längs Z); rundum bleibt, wie es ist. Die Farben am Ende
  gelten für beide.
- **Bahn-Datenmodell** (`vierachs_bahn.Bahn` verallgemeinern): Punkte,
  Bögen, Vorschub je Satz, Eilgang, Ein-/Ausfahrt als Typ; daraus die
  Ausgabe mit G1/G2/G3 und F; Glättung und Zusammenfassen nach Toleranz an
  einer Stelle für alle Strategien.
- **Operationen:** wie `RundumSchruppen` – eigene `PathOp.ObjectOp`-Klassen,
  damit Job, Postprozessor und Simulation von FreeCAD weiter gehen; die
  Eigenschaften bleiben in Sätzen erklärt.
- **Prüfen:** Abtrag, Kollision und Reichweite nehmen die Bahn wie heute.

## 8. Schneller und sparsamer rechnen

Erst messen, dann ändern; die Bahn darf sich nicht ändern (Vergleichstest
mit gespeicherten Bahnen, Abschnitt 9).

- **Messen** (`scripts/bahn_messen.py`, neu): Zeit und Spitzen-Speicher
  (`tracemalloc`) je Schritt – Vernetzen, Hüllfläche, Zeilen, Zusammenfassen,
  Befehle, Abtrag, Kollision – auf drei Teilen (Welle Ø 60 × 100, Manuels
  Testteil, ein großes Teil 300 mm). Die Zahlen kommen in diese Datei.
- **Wo es vermutlich kostet:** die Hüllfläche je Winkel (`je_winkel`,
  Dreiecke × Strahlen), die Kollision (distToShape), das Vernetzen
  (`tessellate`), Python-Schleifen in den Zeilen, `Path.Command`-Listen
  (Speicher bei 100 000 Sätzen), doppelt gerechnete Hüllen für Vorschau und
  Operation.
- **Mittel:** numpy statt Schleifen; das Netz und die Hülle je Modell einmal
  rechnen und wiederverwenden (Vorschau, Operation, Abtrag); Raster nach
  Toleranz statt fest; float32, wo die Toleranz es erlaubt; Sätze beim
  Schreiben zusammenfassen statt erst alle Punkte zu halten; Kollision nur
  auf den Bereichen, die sich bewegen (haben wir zum Teil).
- **Gemessen** (P-2026-09-30-71/-75, FreeCAD 1.1.3, `scripts/bahn_messen.py`;
  Schaftfräser Ø 12, Kugel Ø 6, Schrittweite 0,5; Zeit ohne Speichermessung –
  mit `tracemalloc` war alles zwei- bis siebenmal langsamer):

  | Teil | Hülle | Schrupp­bahn | Befehle | Rest nach dem Schruppen | Schlicht­bahn | Befehle | zusammen | Spitze |
  |---|---:|---:|---:|---:|---:|---:|---:|---:|
  | Welle Ø 60 × 100 (500 Dreiecke, 5 500 / 54 000 Punkte) | 0,5 s | 0,4 s | 0,0 s | 1,4 s | 2,3 s | 0,4 s | 5,1 s | 26 MB |
  | Welle mit Absatz und Abflachung (1 136 Dreiecke, 23 000 / 69 000 Punkte) | 0,6 s | 0,7 s | 0,2 s | 2,0 s | 2,3 s | 0,5 s | 6,4 s | 31 MB |
  | Groß Ø 200 × 300 (1 632 Dreiecke, 187 000 / 169 000 Punkte) | 0,6 s | 1,0 s | 1,4 s | 12,3 s | 2,7 s | 1,1 s | 19,0 s | 195 MB |
| … nach P-2026-09-30-77 (Rest blockweise) | 0,7 s | 1,2 s | 1,2 s | 10,6 s | 2,8 s | 1,2 s | 17,9 s | 104 MB |

  Vernetzen, Hülle, Schruppbahn und Befehle sind schnell genug. Was zählt: der
  **Rest nach dem Schruppen** – am großen Teil 12 s und 195 MB
  (`restmaterial.Stange.fahre_stuecke`: jede Fahrt in Teilschritte von 0,5 mm
  zerlegt, alle 1,1 Millionen Stellen auf einmal, je Stelle 50 × 13 Zellen in
  `_block`) – und die **Schlichtbahn** mit 2,3 s auch am kleinen Teil (die
  Hülle je Winkel bei 0,5° auf dem 0,005-mm-Netz: `_kanten_kugel`,
  `_dreiecke_treffen`, dazu `_nicht_tiefer` und `_zusammengefasst`).
- **Ziel** (aus der Messung): die Welle unter 5 s, das große Teil unter 15 s,
  Spitze unter 100 MB – und die goldenen Bahnen bleiben grün
  (`tests/test_goldene_bahnen.py`, P-2026-09-30-73). Der Speicher des Rests
  ist erledigt (P-77: die Fahrten blockweise, 195 → 42 MB, gleiches Ergebnis;
  die Spitze liegt jetzt bei der Schlichtbahn, 104 MB), dann seine Zeit (Stücke statt
  Teilschritte: ändert den Rest um Bruchteile eines Mikrometers – nur mit
  neuen goldenen Bahnen und einem Satz im Verlauf), dann die Schlichtbahn
  (Dreiecke je Winkel vorab auf den Streifen unter dem Fräser eingrenzen).

## 9. Prüfbarkeit

- **Goldene Bahnen:** für jede Strategie eine gespeicherte Bahn zu einem
  Testteil; der Test vergleicht Punkte und Sätze (Toleranz 1 µm) – so
  fällt jede Änderung auf, gewollt oder nicht. Beschleunigen ohne Änderung
  der Bahn heißt: der Test bleibt grün.
- **Abtrag-Vergleich:** nach jeder Strategie die Farben gegen das Modell –
  nirgends rot (zu wenig) oder blau (im Teil), gelb nur unter dem Aufmaß.
- **Kollision:** kein Befund auf den Beispielmaschinen.
- **Grundsätze prüfbar:** kein senkrechter Eintritt in Material (Winkel der
  Bahn beim ersten Kontakt), kein Satz mit Eingriff über dem geplanten ae,
  keine Zeile ganz in der Luft.
- **Zeit- und Speicherbudget** je Testteil im Test, mit Luft (×2).
- **Szenarien** für die Oberfläche: Assistent mit Vorschlag, Ändern, Prüfen.

## 10. Stufen (Vorschlag) und Entscheidungen

Reihenfolge – jede Stufe ist für sich nützlich und geprüft:

- **S1 – Messen und Grundlagen** (klein): `bahn_messen.py`, goldene Bahnen
  für rundum, Bahn-Datenmodell mit Bögen und Ein-/Ausfahrt, Ausgabe G2/G3.
- **S2 – Rundum fertig** (mittel): Linien längs, Plan indexiert, Rundum
  entgraten (4.3.1–3) – auf Manuels Maschine zuerst.
- **S3 – 2,5D Kern** (groß): Höhenfeld und Abtrag für Ebenen; Planfräsen,
  Kontur mit Ein-/Ausfahren, Tasche adaptiv mit Bögen und Trochoiden,
  Restmaterial; Bohren und Gewinde übernommen; der Assistent schlägt vor.
- **S4 – 3D Schlichten** (groß): Zeilen mit Grathöhe, Steil/Flach, Bleistift.
- **S5 – 3D Schruppen und Rest** (groß): ebenenweise adaptiv, Restschruppen.
- **S6 – 3+2 und Feinschliff** (mittel): indexiert schwenken, Glättung (V6),
  Vorschub nach Eingriff, Reihenfolge.
- **S7 – Simultan 5 Achsen** (groß, später).

Entscheidungen (Claude, zur Besprechung):

- **E1 – Womit anfangen?** (a) S1 → S2 → S3 – **Empfehlung**: erst Manuels
  Maschine rundum fertig, dann das, was jeder Fräser täglich braucht; (b)
  gleich S3 (2,5D) – der größte Nutzen für 3-Achs-Fräser, aber rundum bleibt
  halb; (c) gleich 3D – am eindrucksvollsten, aber ohne 2,5D-Grundlagen.
- **E2 – 3D-Kern selbst oder OCL?** (a) selbst mit numpy (Höhenfeld) –
  **Empfehlung**: läuft überall, passt zu Hülle und Abtrag, prüfbar; (b) OCL
  nutzen, wo vorhanden – schneller zu haben, aber fehlt in manchen Builds und
  kennt weder Abtrag noch Halter.
- **E3 – Schruppen: adaptiv oder trochoidal zuerst?** (a) adaptiv mit
  Trochoiden in Ecken – **Empfehlung**, ein Kern für Tasche, Ebene, Lage;
  (b) Offset-Tasche mit Bögen zuerst – einfacher, weniger Gewinn.
- **E4 – Ein Assistent oder ein Befehl je Strategie?** (a) ein Assistent
  „Bearbeitung“ mit Vorschlag – **Empfehlung** („maximal bedienerfreundlich“);
  (b) je Strategie ein Knopf wie in FreeCAD – vertraut, aber wieder Parameter.
- **E5 – Wie stark vorschlagen?** (a) Vorschlag mit Grund, änderbar –
  **Empfehlung**; (b) nur anbieten, nichts vorwählen; (c) fest, ohne Wahl.
- **E6 – Vorschub nach Eingriff:** (a) in Ecken und beim Austritt aus der
  Spandicke gerechnet – **Empfehlung**, das ist die Qualität, die die Maschine
  spürt; (b) ein Vorschub je Operation wie in FreeCAD.
- **E7 – Grathöhe oder Schrittweite beim Schlichten?** (a) Grathöhe
  (Vorgabe 0,005 mm), Schrittweite daraus – **Empfehlung**; (b) Schrittweite
  aus der Werkzeugtabelle wie heute – vertraut; beides zeigen, eines
  eingeben.

**Entschieden** (Manuel, 2026-10-01, auf E1–E7 mit den Empfehlungen: „Egal
Hauptsache du arbeitest weiter??? Also ja“): E1 (a) S1 → S2 → S3, E2 (a)
eigener 3D-Kern mit numpy, E3 (a) adaptiv mit Trochoiden, E4 (a) ein
Assistent „Bearbeitung“ mit Vorschlag, E5 (a) Vorschlag mit Grund, änderbar,
E6 (a) Vorschub nach Eingriff, E7 (a) Grathöhe mit Vorgabe 0,005 mm. S1 ist
gebaut (Messen P-71/-75/-76, goldene Bahnen P-73, Rest blockweise P-77); das
Bahn-Datenmodell mit Bögen kommt mit der ersten Strategie, die Bögen braucht
(S3). S2 ist gebaut (Linien längs P-2026-10-01-06, Plan indexiert P-08/-10,
Rundum entgraten P-12; 0.36.0). Von S3 sind die Hüllfläche von oben, die Bahn
mit Bögen, „Planfräsen“ (P-2026-10-01-14), der Assistent „Bearbeitung
(Fräsen)“ (P-15; 0.37.0), das Prüffenster mit dem Quader (P-16; 0.38.0), die
Kontur (P-19; 0.40.0), der Nullpunkt (P-21; 0.41.0) und das Räumen mit dem
Wettbewerb gegen das Planfräsen (P-25; 0.44.0) gebaut.

**S3 im Einzelnen** (Plan 2026-10-01, Claude; die Reihenfolge nach Nutzen):

- **S3a Hüllfläche eben und Bahn mit Bögen** – `hoehenfeld.py`: die ebenen
  Flächen nach oben, die Oberseite, die Hüllfläche je Zeile gegen das Netz mit
  jeder Fräserform (dieselbe Rechnung wie rundum, `vierachs_huelle._form_treffen`,
  nur senkrecht; ohne OCL); `bahn.py`: Punkte mit Geraden und Bögen (G2/G3),
  Eilgang, Eintauchen, Vorschubanteil je Satz, Befehle und Zeit – die eine Stelle
  für alle 2,5D- und 3D-Strategien.
  Gebaut (P-2026-10-01-14).
- **S3b Planfräsen** – `planfraesen_bahn.py` und die Operation
  `planfraesen.PlanFraesen`: Zeilen hin und her in Lagen vom Rohteil bis auf die
  Fläche plus Aufmaß, Zeilen in der längeren Richtung, Überlauf 0,6 · Ø längs,
  seitlich 0,2 · Ø über den Rand, Zeilenabstand ae, Halbkreise zwischen den
  Zeilen, wo beide frei sind; die Zeilen halten vor Wänden und Absätzen
  (Hüllfläche gegen das Teil ohne die Fläche); keine Zeile ohne Rohteil
  (Grundsatz 5); Rampe ins Material, senkrecht in der Luft; beim Austritt aus
  dem Rohteil halber Vorschub (E6, erster Schritt). FreeCADs Tiefen und Höhen
  (StartDepth folgt dem Rohteil, SafeHeight, ClearanceHeight) wie bei seinen
  Operationen. Gleichlauf durchgehend (Grundsatz 4) kommt mit der Spirale von
  außen nach innen, sobald das Bahnmodell Konturen versetzen kann (S3e).
  Gebaut (P-2026-10-01-14).
- **S3c Assistent „Bearbeitung“ für den Quader** (E4) – Job mit Rohteil aus dem
  Modell (Aufmaß je Seite), die Oberseite vorgeschlagen, Fräser und Einsatz aus
  der Werkzeugverwaltung, „Planfräsen“ mit Grund (E5), Anlegen, Ändern per
  Doppelklick, Hilfe, Szenario.
  Gebaut (P-2026-10-01-15, 0.37.0): `gui_bearbeitung.py`, Szenario `szenario_bearbeitung`.
- **S3d Prüffenster 2,5D** – der Abtrag als Höhenfeld des Rohteils (Dexel längs
  Z), beim Abspielen und am Ende in Farben; Kollision wie gehabt.
  Gebaut (P-2026-10-01-16, 0.38.0): `restmaterial.Quader`, `QuaderAbtrag`,
  `hoehenfeld.hoehen`, die Anzeige in `gui_abfahren`; jede Operation des Jobs
  trägt ab, auch FreeCADs eigene. Die Simulation fand gleich einen Fehler des
  Planfräsens: vor einer Wand blieb zwischen den Zeilen und in den Ecken ein
  Rest (die Zeilen hin und her lassen an der Wand jeden zweiten Zwischenraum
  aus) – jetzt fährt der Fräser dort an der Wand entlang (Wandfahrt). Was
  bleibt: der Sicherheitsabstand (0,25 mm) vor jeder Wand, den die Kontur (S3e)
  wegnimmt – im Raster von 0,5 mm sieht die Simulation ihn nicht. Eine Wand
  **längs** der Zeilen (P-2026-10-02-18, 0.80.0): Die gleich verteilten Zeilen
  ragten dort in die Wand und fielen weg, die letzte freie ließ bis zu einem
  Zeilenabstand stehen (gemessen 0,47 bis 0,58 mm) – jetzt fährt eine Zeile im
  Abstand R + Zugabe an der Wand entlang: 0,025 mm (`test_planfraesen`). Zwei Flächen
  übereinander in derselben Bahn (P-2026-10-02-21, 0.83.0): Die obere griff über ihre offene
  Seite bis an den Rand des Rohteils aus, auch wo dahinter eine tiefere derselben Bahn liegt,
  deren Lage am Rohteil beginnt – am Zapfen 40 × 30 auf der Platte 100 × 80 fräste die
  Oberseite die ganze Platte 1 mm ab, der Boden darum danach noch einmal. Jetzt nicht
  (`planfraesen_bahn._abgedeckt`, die Zustellung dann wie vor einer Wand): am Zapfen 15,6 →
  13,5 min, am Absatz 5,1 → 4,3 min. **Nur im Gleichlauf** (P-2026-10-02-24, Manuel:
  „auswählbar, ob er abhebt und wieder von vorne anfängt“): ein Haken im Block Planfräsen
  (Eigenschaft `NurGleichlauf`). Aus: hin und her wie bisher. An: jede Zeile für sich
  (`vierachs_bahn._einzeln`) in der Richtung, die mit den der Reihe nach folgenden Zeilen
  das Material rechts hat (`_steigend`, `spindel.ist_gleichlauf`, M4 andersherum), danach
  abheben und im Eilgang zurück; neben der eben gefrästen Zeile senkrecht hinein (dort steht
  nur ihr Streifen ae – die Rampe von oben kostete am Block 60 × 40 jedes Mal 70 mm),
  beginnt eine Zeile an einer Wand, erst an ihr zur vorigen und zurück, damit die Ecke der
  Stirn nicht stehen bleibt. Block 60 × 40 mit Absatz: 2,25 statt 1,87 min. Am Block ohne
  Absatz ist Planfräsen so 6 % langsamer als Räumen – der Wettbewerb gibt den Haken dann an
  Räumen (`szenario_plan_gleichlauf`). Ebenso „Plan indexiert“ auf der Drehmaschine: jede
  Zeile von vorne zum Futter, die Zeilen quer in der Folge, die dafür Gleichlauf ist; Haken
  im 4-Achs-Assistenten. Ebenso „Rundum schruppen“ mit gewählten Flächen (P-2026-10-02-26):
  jede Zeile rund um die Stange für sich, der Winkel so, dass das Material bei der nächsten
  Zeile längs auf der Seite des Gleichlaufs liegt. „Linien längs“ (Schlichten) noch hin und her.
- **S3e Kontur** – außen und innen mit tangentialem Ein- und Ausfahren,
  Schruppen mit Aufmaß und Schlichten in einem Schritt; Konturen versetzen im
  Bahnmodell (dann auch die Spirale fürs Planfräsen).
  Gebaut (P-2026-10-01-19, 0.40.0): `kontur_bahn.py` – Wände sind senkrechte
  Flächen mit waagerechter Unterkante (eben, rund, Freiform), ihre Unterkanten
  verbinden sich zu geschlossenen oder offenen Konturen, die freie Seite sagt
  die Außennormale; der Versatz kommt von `Part.Wire.makeOffset2D` (Ecken
  außen als Bögen G2/G3, innen bleibt der Fräserradius); Schruppen bei Radius +
  Aufmaß + k · ae von außen zur Wand hin – so viele Bahnen, wie Rohteil neben
  der Wand steht (eine Tasche ganz) oder die Breite sagt –, in Lagen bis auf die
  Unterkante (plus „Tiefer“), dann Schlichten bei Radius in einem Zug
  (höchstens die Schneidenlänge je Zug); Gleichlauf (Grundsatz 4: Material
  rechts – um einen Zapfen im Uhrzeigersinn, in der Tasche gegen ihn);
  Ein- und Ausfahren als Gerade quer von der Wand weg und Viertelkreis (je
  Fräserradius), kürzer, wo es nicht passt, zuletzt senkrecht; Rampe im
  Material, senkrecht in der Luft; die Hüllfläche im Raster mit zwei Netzen
  (nahe der Wand ohne ihre Böden und Decken – der Fräser berührt ihre Kanten –,
  weiter weg nur ohne die Wände, damit die Oberseite hinter einer einzeln
  gewählten Wand die Bahn anhält); kein Rohteil – keine Bahn (Grundsatz 5),
  beim Austritt halber Vorschub. Operation `kontur.Kontur`, im Assistenten der
  Block „Kontur“ mit Haken (je Strategie ein Block, `_Strategie`/`_Block`);
  Prüfung `test_kontur`, Szenario `szenario_kontur`. Die Spirale fürs
  Planfräsen aus Versätzen steht noch aus.
- **S3f Räumen mit Versätzen** – nach Manuels Maßstab (Abschnitt 11,
  2026-10-01) vor dem Adaptiv: ein Rechenkern für offene Flächen und Taschen.
  Der Bereich (das Rohteil über einer ebenen Fläche oder eine Tasche) wird
  um Radius + k · ae nach innen versetzt (`makeOffset2D` wie bei der Kontur,
  Inseln wie der Zapfen bleiben stehen), eine Spirale von außen nach innen
  bei vollem ap (bis zur Schneidenlänge) und schmalem ae – im Gleichlauf, ohne
  Wenden, mit Bögen in den Ecken. Hinein: bei offenen Flächen von außen in der
  Luft; in Taschen über die Rampe mit dem Eintauchwinkel des Werkzeugs auf
  der längsten Geraden oder die Helix mit seiner Steigung (das Steilere
  gewinnt), nur einmal je Lage – nicht je Versatz wie heute bei der Kontur.
  Der Zapfen bekommt sein Aufmaß und danach die Kontur. Ecken mit zu viel
  Eingriff bekommen später Trochoiden (das Adaptiv, E3 (a)) – erst messen, ob
  es nötig ist. Mit S3f beginnt der Wettbewerb der Strategien (Grundsatz 0):
  Für die Platte rechnet der Assistent Planfräsen und Räumen, für die Tasche
  Kontur und Räumen – mit demselben Zeitmodell –, setzt den Haken bei der
  schnelleren und schreibt die andere Zeit daneben; die Prüfung rechnet an
  der Platte nach, dass Räumen dort gewinnt (≈ 35 min gegen 44).
  Gebaut (P-2026-10-01-25, 0.44.0) – anders als geplant nicht mit Versätzen
  aus `makeOffset2D`, sondern im Raster: `raeumen_bahn.py` legt ein Raster
  (0,5 mm, in der Vorschau 1 mm) über die Fläche, sperrt, wo die Hüllfläche
  des Teils (der Fräser um Aufmaß und Toleranz vergrößert) über der Lage
  liegt, weiß vom Rohteil, wo Material steht, und merkt sich, was schon
  geschnitten ist. Die Ringe sind die Höhenlinien des Abstandsfelds zum
  Gesperrten bei Radius + Aufmaß + k · ae (Marching Squares, verkettet,
  vereinfacht – Inseln wie der Zapfen und Absätze teilen sie von selbst), vom
  Rohteil her analytisch (Rechteck mit runden Ecken, der erste Ring R − ae
  außerhalb in der Luft). Drei Varianten, alle gerechnet, die schnellste zählt
  (P-2026-10-01-26, nach Manuels Bild: „der Weg muss im Viereck anfangen, aber
  immer runder werden, so dass er am Ende nur um den Zapfen fährt“): „rohteil“
  – die Ringe um das, was noch steht: die Höhenlinien des Wegs vom
  Rohteilrand bei m · ae, um Inseln und Wände herum gemessen (geodätisch, im
  Raster mit Zeilen-Durchläufen, P-2026-10-01-49): ohne Hindernis das Rechteck mit
  runden Ecken, hinter einer Insel legt sich der Ring um sie, überall höchstens ae;
  vor der Insel endet er, den letzten Ring an ihrer Wand fahren die Ringe um die
  Inseln mit dem Rest. (Bis P-48 waren es die Höhenlinien von
  F = min(Tiefe + R, D + ae): Wo die Insel den Ring bestimmte, biss das Rechteck in
  sie hinein – mit Material beidseits; der Prüfstand fand auf der Platte 120 mm in
  voller Breite, 20 tief.) –, „morph“ (P-2026-10-01-27) – ein harmonisches Feld u zwischen
  Rohteil und Insel (u = 1 außen am ersten Ring, u = 0 am Zapfen, dazwischen
  gemittelt wie eine gespannte Haut, im Raster gelöst): seine Höhenlinien
  fangen als Rechteck an und werden von Ring zu Ring runder bis zum Kreis um
  den Zapfen. Der Abstand der Ringe folgt dem Eingriff: Die Faltung des noch
  stehenden Rohteils mit der Stirn des Fräsers (FFT) sagt je Punkt, wie viel
  unter dem Fräser ungeschnitten ist; der nächste Ring ist die tiefste
  Höhenlinie, auf der nirgends mehr steht als beim geraden Schnitt mit ae
  (Bisektion über u) – in den Ecken des Rechtecks enger, am runden Zapfen
  weiter (≈ 1,8 mm bei gleicher Last). Der letzte Ring ist der genaue Kreis um
  den Zapfen (Versatz der Kontur, mit Bögen), alle Ringe eine Spirale: von Ring
  zu Ring gleitet die Bahn über 2 R hinüber, ohne Absetzen. Liegt die Insel
  nicht in der Mitte (der schmalste Spalt kleiner als 0,4 des breitesten) oder
  berührt sie den Rand, rechnet der Morph nicht (er würde zu eng, auf der
  Platte 66 min) – ebenso bei mehreren Inseln, und kommt er zwölfmal nacheinander nicht voran,
  endet er (an zwei Kuppeln rechnete er sonst fast endlos, P-2026-10-02-02); dann zählen die anderen Varianten – und „inseln“ (nur die
  Ringe um Wände und Inseln; in der Tasche von innen nach außen; Taschen
  rechnen nur diese Variante). Auf Manuels 50 × 50 mit Zapfen: morph 2,70 min
  (eine Einfahrt, keine Rampe, 7 Halte), rohteil 3,03, inseln 4,49 – der Morph
  gewinnt; am Absatz rohteil 2,66 (bis P-48 2,03 – der letzte Ring lief voll an der
  Wand); auf der Platte rohteil 33,9 (bis P-48 33,1, mit dem Biss in den Zapfen;
  morph gesperrt), inseln 40,5. Je Lauf der Eingang in dieser Reihenfolge: an den vorigen
  anhängen (die Spirale, bis 2 ae, der Weg frei), tangential aus dem Freien
  (das Einfahren der Kontur auf der freien Seite – links im Gleichlauf,
  rechts im Gegenlauf), quer aus dem Freien, das Anfangsstück nachholen, wenn
  dahinter die Insel liegt, zuletzt die Rampe: rundum auf einem ganzen Ring
  (die Tasche: einmal je Lage), sonst längs des Laufs. „Frei“ heißt: unter der
  Stirn höchstens so viel ungeschnittenes Rohteil wie im Streifen ae, den
  jeder Ring ohnehin nimmt. Gleichlauf oder Gegenlauf (das Feld links und
  rechts abgetastet), Bögen in den Ecken, beim Austritt halber Vorschub.
  Ein ganzer Ring, an dessen Anfang kein Eingang passt, fängt dort an, wo
  einer passt; der Eilgang hinab endet über dem Material, wo unter der Stirn
  noch ein Rest steht (beides vom Prüfstand gefunden, P-26). Rechenzeit etwa
  eine Sekunde je Fläche. Gemessen mit dem Standardfräser (`test_pruefstand`,
  Simulation im Quader: nirgends ins Teil, auf der Fläche nichts stehen
  geblieben): Manuels 50 × 50 mit Zapfen 2,69 min (Planfräsen 4,8), der Block
  mit Absatz 2,0 (Planfräsen 1,7 – dort gewinnt das Planfräsen, der Assistent
  zeigt es), die Tasche 40 × 30 0,75 (Kontur ohne Schlichten 3,0), die Platte
  33,1 (Planfräsen 39,3), ihre Tasche 1,2 – Abschnitt 11. Der Zapfen bekommt sein Aufmaß, die Kontur holt es: Räumt das
  Räumen den Boden einer Tasche, deren Wand die Kontur schlichtet, setzt der
  Assistent bei der Kontur „Material neben der Wand“ gleich dem Aufmaß des
  Räumens – sie fährt dann nur noch das Aufmaß (eine Bahn, die Lagen ab der
  Oberkante der Tasche, nicht ab dem Rohteil) und schreibt es dazu.
  Sind ebene Flächen und Taschenböden gewählt, rechnet der Assistent beide
  Folgen – Planfräsen der ebenen Flächen und Räumen nur der Böden gegen Räumen
  über alles – und hakt die schnellere an (auf der Platte: Räumen über alles,
  die Folge wäre langsamer); beide Zeilen sagen, um wie viel. Operation
  `raeumen.Raeumen` (Variante wählbar, „Gerechnet“ zeigt beide Zeiten); im
  Assistenten der Block „Räumen“ – für ebene Flächen vorgeschlagen, für
  gewählte Taschenwände anhakbar (die Kontur bleibt dort der Vorschlag) –
  und der Wettbewerb gegen das Planfräsen (Grundsatz 0). Noch nicht:
  Trochoiden in Ecken (E3), die Spannhöhe. Szenarien `szenario_raeumen`,
  `szenario_platte` (Oberseite und Taschenwand der Platte gewählt: Räumen
  über alles, die Kontur nur mit dem Aufmaß).
- **S3g Bohren, Gewinde** – FreeCADs Operationen aus dem Assistenten mit den
  Schnittwerten. Zuerst gebaut (P-2026-10-01-29, 0.46.0): **Bohrung fräsen** –
  zylindrische Bohrungen mit einem Schaftfräser, der kleiner ist als sie, ohne
  Bohrer. `bohrung_bahn.py` erkennt die Bohrungen (senkrechte Zylinderflächen,
  ganz herum, die Normale zur Achse; durchgehend, wenn unter dem Grund nichts
  ist) und fräst je Bohrung: in einer Helix hinab (G2/G3 mit Z, Radius
  höchstens 0,9 R, Steigung 2π · r · tan Eintauchwinkel), unten einmal herum;
  ist die Bohrung größer als zwei Fräser, in Lagen (ap) mit Ringen nach außen
  (ae, je ein Halbkreis hinüber); zuletzt die Wand bei Radius in einem Zug (je
  Zug höchstens die Schneidenlänge), mit Halbkreisen aus der Mitte hinein und
  heraus; Gleichlauf in der Bohrung gegen den Uhrzeigersinn (G3). Durchgehende
  0,5 mm tiefer; mehrere in der Reihenfolge des kürzesten Wegs. Operation
  `bohrung.BohrungFraesen` („Bohrung fräsen T1“), im Assistenten der Block
  „Bohrung fräsen“ und der zweite Wettbewerb: Bohrung fräsen gegen Kontur auf
  denselben Bohrungen – am Block mit Ø 20 durchgehend und Ø 34 × 10 1,33 min
  gegen 4,6 (die Kontur räumt jeden Versatz mit eigener Rampe); sind dazu
  andere Wände gewählt, fährt die Kontur nur diese. Räumt das Räumen den Boden
  der Bohrung schon (Oberseite und Taschenwand der Platte), tritt Bohrung
  fräsen nicht an – dort ist Räumen und die Kontur mit dem Aufmaß die Folge.
  Prüfung `test_bohrung`, Szenario `szenario_bohrung`, Prüfstand-Teil (e). Der
  Prüfstand fand am neuen Teil einen alten Fehler der Kontur: In einer kleinen
  runden Bohrung biegt das Einfahren zur Wand zurück, und der Eilgang hinab
  streifte den Ring, den die Bahn erst noch nimmt (23,8 mm³ im Eilgang) – jetzt
  zählt der gemessene Abstand der Einfahrstelle zur Wand, auf beiden Seiten
  der Stirn.
  Dann **Bohren** (P-2026-10-01-30, 0.47.0): FreeCADs Bohr-Operation
  (Path.Op.Drilling) aus dem Assistenten mit einem Bohrer aus der
  Werkzeugverwaltung – nur für durchgehende Bohrungen mit seinem Durchmesser
  (eine Sackbohrung mit ebenem Grund kann ein Bohrer nicht). `bohren.py` legt
  sie an (ohne FreeCADs Vorgaben, die bei mehreren Controllern nachfragen):
  die gewählten Bohrungen als Basis, „Drill Tip“ (die Spitze unter den Grund),
  R 3 mm über dem Rohteil, G98, Hübe ab 3 × D je 1 × D (G83), sonst G81 – die
  Tiefe im Material gezählt, ab der Oberkante des Rohteils, nicht ab R; die
  Zeit aus denselben Bewegungen (`planen`). Im Assistenten der Block „Bohren“
  (nur Bohrer zur Auswahl, `_Strategie.werkzeug_passt`; vorgewählt der mit dem
  Durchmesser der Bohrung) und der Wettbewerb in Gruppen (`_gruppen`): Bohren,
  Bohrung fräsen und Kontur auf denselben Bohrungen – die schnellste bekommt
  den Haken (zwei Bohrungen Ø 20: Bohren 0,77 min, Bohrung fräsen 1,09).
  Prüfung `test_bohren`, Szenario `szenario_bohren`.
  Dann **Gewinde bohren** (P-2026-10-01-31, 0.48.0): FreeCADs
  Gewinde-Operation (Path.Op.Tapping) aus dem Assistenten mit einem
  Gewindebohrer aus der Werkzeugverwaltung – in Bohrungen mit seinem Kernloch
  (Gewinde-Ø − Steigung: M10 × 1,5 → Ø 8,5). `gewinde.py`: `passende`
  (Kernloch auf 0,02 mm), `tiefe_fuer` (durchgehend um den Anschnitt 2 ×
  Steigung hinaus, in der Sackbohrung eine Steigung über dem Grund),
  `planen` (hinein und heraus mit Steigung · Drehzahl, für die Zeit),
  `lege_an` – **je Tiefe eine Operation** (`je_tiefe`): FreeCAD fährt alle
  Löcher einer Operation bis zu ihrer einen Endtiefe, ein durchgehendes
  Kernloch und eine Sackbohrung zusammen schnitten die Sackbohrung zu tief;
  dasselbe jetzt beim Bohren (je Tiefe des Grunds). Name „Gewinde M10x1.5 T3“
  nur in ASCII – er steht als Kommentar im Programm. Im Assistenten der Block
  „Gewinde bohren“ (nur Gewindebohrer mit Steigung, vorgewählt der mit dem
  Kernloch der Bohrung): Er tritt gegen keine Strategie an und wird nicht
  vorgeschlagen – den Haken setzt man selbst; das Kernloch macht der
  Wettbewerb Bohren / Bohrung fräsen / Kontur in derselben Bohrung. Dabei:
  Ein Block, der rot ist, verliert seinen Haken, wenn eine andere Strategie
  seiner Gruppe die Flächen kann (`_haken_setzen`) – sonst hielt er „Anlegen“
  auf; das Prüffenster rechnet einen Gewindebohrer mit seinem Kernradius
  (er schneidet nur das Gewinde, nicht das Kernloch). Prüfung
  `test_gewinde`, Szenario `szenario_gewinde` (Bohren T2 G81, dann Gewinde
  T3 G84; im Prüffenster nirgends ins Teil).
  Dann **Entgraten** (4.1 Punkt 8; P-2026-10-01-32, 0.49.0): eine eigene
  Operation statt FreeCADs Deburr – mit Gleichlauf, tangentialem Ein- und
  Ausfahren und der Hüllfläche des Kegels gegen das Teil. `entgrat_bahn.py`:
  die Oberkanten mit Grat (`ketten`: waagerechte Oberkanten gewählter Wände,
  an denen oben eine ebene Fläche nach oben anschließt; eine gewählte ebene
  Fläche gibt die Wände, die an ihren Kanten hinab gehen – Außenkanten,
  Taschen- und Bohrungsränder, nicht der Fuß eines Zapfens), je Höhe zu
  Ketten verbunden wie bei der Kontur; die Fase wie Deburr (Tiefe an der Wand
  b / tan(α/2), die Spitze `tiefer` darunter, die Achse d/2 + tiefer ·
  tan(α/2) neben der Wand – so schneidet der Kegel genau die Fase); die Bahn
  als Versatz der Kette (kontur_bahn), senkrecht hinab in der Luft,
  tangential hinein und heraus, vor Absätzen angehalten; nie unter die
  Unterkante der Wand – ist sie niedriger als die Fase, bleibt die Kette aus
  und die Zeile sagt es. Operation `entgraten.Entgraten` („Entgraten T3“),
  Einsatz „Fasen“; im Assistenten der Block „Entgraten“ (nur Fasenfräser,
  nie vorgeschlagen – welche Kante eine Fase bekommt, sagt die Zeichnung).
  Das Prüffenster lässt die Fase durch (`restmaterial.QuaderAbtrag.fasen`,
  wie bei „Rundum entgraten“: wo die Operation abträgt, darf es so tief ins
  Teil, wie die Spitze steht). Prüfung `test_entgraten` (Zapfen und Tasche:
  Ketten, Lage 0,5 neben der Wand, Gleichlauf, die Fase im Quader auf
  0,05 mm), Szenario `szenario_entgraten`.
  Dann **Zentrieren** und **Senken** (P-2026-10-01-34, 0.50.0): FreeCADs
  Bohr-Operation mit einem Kegel (`senken.py`, über `bohren.bohrzyklus`).
  Zentrieren mit dem NC-Anbohrer vor dem Bohren: oben ein Kreis von Ø Bohrung
  + 0,4 mm (eine kleine Fase, höchstens 0,9 × Ø des Anbohrers), unter einer
  Senkung ab deren Oberkante; den Haken setzt man selbst. Senken mit dem
  Kegelsenker in die Senkungen des Modells (`senkungen`: Kegelflächen ganz
  herum, nach oben offen, Material außen, darunter eine Bohrung – in der
  Liste „Senkung Ø 12,4, 90°“): sein Winkel wie ihrer, sein Ø mindestens
  ihrer, so tief, dass sein Kegel oben ihren Ø hat (die Spitze zählt);
  vorgeschlagen, weil das Modell sie hat. Tiefe (D − d) / 2 / tan(α/2), je
  Tiefe eine Operation. Das Prüffenster rechnet Bohrer, Anbohrer und Senker
  mit ihrem Kegel statt als Zylinder (`restmaterial._kegel`) und lässt die
  Fase des Zentrierens durch (Eigenschaft „Fase“ an der Operation). Dabei:
  Die Namen der Operationen bleiben eindeutig, ohne dass FreeCAD sie umbenennt
  (`namen.eindeutig`: „Bohren T2 (2)“ statt „Bohren T001“), und die Zeit im
  Prüffenster für G93 (Rundum) hält nicht mehr vor jedem Satz an (die Spirale
  dauerte siebenmal so lang). Prüfung `test_senken`, Szenario
  `szenario_senken`.
  Dann **Gewinde fräsen** (P-2026-10-01-36, 0.52.0): eine eigene Operation
  statt FreeCADs ThreadMilling – das fährt den Vorschub des Controllers mit
  der Mitte des Fräsers (in M10 mit Ø 8 an der Schneide fast das Fünffache)
  und mit einem Fräser mit mehreren Zähnen trotzdem Gang für Gang.
  `gewinde_bahn.py`: welches Gewinde, aus Kernloch und Steigung des Fräsers
  über die Tabelle ISO 965 / 6H (`daten/gewinde_6H.csv`, dieselbe wie bei
  FreeCAD: das Kernloch muss in D1 liegen – Ø 8,5 mit 1,5 → M10 × 1,5, Ø 10,2
  mit 1,75 → M12 × 1,75); gefräst auf die Mitte der Toleranz von D2 (die
  Spitze des 60°-Zahns, vorn P/8 breit, bei D2/2 + (P/2 − P/8) / (2 tan 30°)),
  „Korrektur“ für die Lehre. Je Bohrung: Eilgang in die Mitte hinab, Halbkreis
  hinaus mit P/4 in z (so steil wie die Helix), Helix mit P je Umlauf in
  Vierteln (G2/G3 mit Z), Halbkreis zurück; Gleichlauf G3, ein
  Rechtsgewinde damit von unten nach oben (Gegenlauf G2 von oben, Links
  umgekehrt); der Vorschub der Mitte r / (r + R) vom Vorschub an der
  Schneide (`bahn.Punkt.anteil`), in den Halbkreisen mit deren Radius. Unten
  und oben so weit, dass die Lücke des Gangs ganz aus dem Teil reicht (aus
  der Zahnform: halbe Spitze und Zahnhöhe bis zum Hals, mal tan 30°; Ø 8 für
  M10 × 1,5: 1,3 mm unter die Unterseite), in der Sackbohrung 0,2 mm über
  dem Grund. Mehrere Zähne übereinander (Schneidenlänge / Steigung): so
  viele Gänge auf einmal, Umläufe nur bis der oberste Zahn oben ist (zwei
  M10 × 12: 2 statt 18 Umläufe). Fehler mit einem Satz: kein Kernloch für die
  Steigung (mit dem Kernloch, das es bräuchte – auch wenn der Nenn-Ø
  gezeichnet ist), Fräser zu groß, Hals zu dick, Reichweite zu kurz,
  Sackbohrung zu flach. Operation `gewindefraesen.GewindeFraesen`
  („Gewinde fräsen T7“, Steigung und Zähne an der Operation – CAM kennt beim
  Gewindefräser keine Steigung), Einsatz „Gewindefräsen“. Im Assistenten der
  Block „Gewinde fräsen“ (nur Gewindefräser mit Steigung, vorgewählt einer,
  der in alle gewählten Bohrungen passt; nicht vorgeschlagen) – er und
  „Gewinde bohren“ schließen sich aus. Das Prüffenster lässt das Gewinde
  durch (`QuaderAbtrag.ringe`: um jede Bohrung bis zur Spitze des Zahns,
  daneben nicht), die Kollision auch (`INS_TEIL_ERLAUBT`). Dabei: Der Satz
  „nur das Aufmaß an den Wänden …“ der Kontur hing seit 0.51.0 auch am
  Restmaterial – jetzt nur an der Kontur. Prüfung `test_gewindefraesen`,
  Szenario `szenario_gewindefraesen`.
  Dann **Sackbohrungen mit Bohrspitze** (P-2026-10-01-37, 0.53.0): Die
  Erkennung hielt jede Bohrung für durchgehend, unter deren Achse Luft ist –
  auch die Senkung für eine Zylinderkopfschraube (darunter das
  Durchgangsloch) und jede Sackbohrung aus FreeCADs „Bohrung“ (darunter die
  Luft der 118°-Spitze). „Bohrung fräsen“ fuhr dort 0,5 mm unter den Grund,
  „Gewinde fräsen“ eine Steigung – in den Boden der Senkung, in den Kegel der
  Spitze. Jetzt prüft `bohrung_bahn._boden_unter` rundum knapp innerhalb der
  Wand, und `Bohrung.spitze` hat den Winkel eines Kegels darunter. „Bohren“
  bohrt auch Sackbohrungen, deren Spitze der Winkel des Bohrers ist (±1°) –
  ExtraOffset „Drill Tip“ setzt den vollen Durchmesser auf den Grund der Wand,
  die Spitze steht genau dort, wo das Modell sie hat; ein Bohrer mit anderem
  Winkel bekommt einen Satz. In der Liste „Bohrung Ø 8,5, Grund 5, Spitze
  118°“. Prüfung `test_bohren`, `test_bohrung` (Senkung und Spitze), Szenario
  `szenario_sackgewinde` (eine PartDesign-Bohrung M10, 15 tief: Bohren T2 bis
  zur Spitze, Gewinde fräsen T7 0,2 über dem Grund der Wand, im Prüffenster
  nirgends ins Teil).
  Dann **gezeichnete Fasen** (P-2026-10-01-38, 0.54.0): Hat das Modell die
  Fase schon (FreeCADs „Fase“: eine schräge Fläche, eben oder Kegel, unten an
  Wänden, oben an einer ebenen Fläche nach oben), fräst „Entgraten“ genau sie –
  bisher ließen alle Strategien sie stehen. `entgrat_bahn._fase` erkennt sie
  (Winkel zur Senkrechten aus der Normalen, asin n_z), `fasen()` macht aus
  ihren Unterkanten Ketten, auf die Höhe der Oberseite gehoben (dort läge die
  Kante ohne Fase), mit Breite und Winkel aus dem Modell (`Kette.breite`,
  `Kette.winkel`); eine gewählte ebene Fläche nach oben bringt die Fasen an
  ihren Kanten mit. Der Kegel muss ihren Winkel haben (±1°, sonst ein Satz) –
  dann liegt er genau auf ihr. Die Hüllfläche blendet die Fasen und die
  Flächen an ihrer Oberkante aus. Im Assistenten ist Entgraten bei einer
  gezeichneten Fase vorgeschlagen (außer einer Senkung über einer Bohrung –
  die senkt „Senken“). Prüfung `test_fase` (eckiger und runder Zapfen, im
  Quader der Kegel auf 0,06 mm auf der Fase), Szenario `szenario_fase`.
  Dann **Verrunden** (P-2026-10-01-39, 0.55.0): Entgraten nimmt auch den
  Radienfräser (Einsatz „Verrunden“, `entgraten.schneide_des_werkzeugs`: nur mit
  ganzem Viertelkreis – Führung = Ø − 2 R, sonst bliebe oben eine Stufe). Die
  Spitze steht genau einen Radius unter der Kante, die Achse die halbe Führung
  neben der Wand: Die Hohlkehle (Mittelpunkt auf der Höhe der Spitze) liegt dann
  auf dem Viertelkreis. Gezeichnete Rundungen (`_rundung_radius`: Zylinder mit
  waagerechter Achse an geraden Kanten, Torus mit senkrechter an runden; von der
  Wand bis oben genau ein Radius) erkennt `_fase` wie Fasen (`Fase.radius`,
  `Kette.radius`); der Radius des Fräsers muss ihrer sein (±0,02 mm), ein
  Fasenfräser an einer Rundung oder ein Radienfräser an einer Fase bekommt einen
  Satz. Der Assistent wählt den passenden Fräser vor (`_entgratfraeser_waehlen`),
  die Zeile sagt „die Rundung wie gezeichnet: R 2“. Dabei: „entgraten“ steht
  jetzt bei den Operationen, die ins fertige Teil schneiden dürfen
  (`kollision.INS_TEIL_ERLAUBT`) – eine Fase an einer scharfen Kante hätte die
  Kollisionsprüfung als „ins fertige Teil“ gemeldet. Prüfung `test_rundung`
  (Rundung R 2 am eckigen und runden Zapfen, im Quader auf 0,08 mm; die scharfe
  Kante mit R 2 gerundet), Szenario `szenario_rundung`.
  Dann **Nut** (P-2026-10-01-40, 0.56.0; 4.1 Punkt 6): Langlöcher – zwei
  parallele Wände, an den Enden Halbkreise – erkennt `nut_bahn.nuten` an einer
  Wand (die ganze Runde, `_waende_der_nut`) oder am Grund (die Wände an seinem
  Rand); ohne Material knapp innerhalb der Wände unter dem Grund geht sie durch.
  Die Bahn fährt nie mit ganzer Schneide in voller Breite. **Trochoide**, wenn
  die Kreise (r − R − Aufmaß) mindestens ¼ R haben: je Lage (ap) eine Helix am
  Ende hinab, dann Kreise, die je Umlauf um ae vorrücken, von Kreis zu Kreis
  **hinten** weiter – dort ist alles frei, der Eingriff wächst auf jedem Kreis
  bis ae und fällt wieder –, die nächste Lage zurück; über 0,9 R bliebe in der
  Mitte der Kreise ein Kern (zu breit: „Räumen“). Sonst **Vollnut** mit einer
  Zickzack-Rampe längs der Mittellinie: je Fahrt höchstens ap/2 und D/4 tiefer
  (hin und zurück schneidet die Rampe die Stufe zweimal – nie mehr als ap und
  D/2 in voller Breite), der Vorschub mit dem Anteil 2·√(k(1−k)), k = ae/D: der
  Span so dick wie beim Einsatz mit kleinem ae. Zuletzt die Wand rundum, mit
  Halbkreisen aus der Mitte eines Endes hinein und heraus, im Gleichlauf (G3).
  Im Assistenten der Block „Nut“ („Nut 20 × 50, Grund 10“ in der Liste): auf dem
  Grund gegen Räumen und Planfräsen, an den Wänden gegen die Kontur – eine Wand
  meint für beide die ganze Nut (`ganze_nuten`); vorgewählt ein Fräser, der
  passt (der größte für Kreise), mit „Vollnut“ zuerst, wenn er die Nut in voller
  Breite fräst. Gemessen mit dem Standardfräser an einer Nut 20 × 50, 10 tief:
  Räumen 0,3 min, Nut 0,9, Kontur über alle Wände 1,2 – am Grund gewinnt Räumen
  (seine Ringe fahren jede Stelle einmal, die Kreise der Trochoide etwa π-mal;
  das Zeitmodell gibt beiden denselben Vorschub), an der Wand die Nut (Kontur
  27 % langsamer). Die Nut lohnt, wo Räumen nicht hinkommt: ohne Grund und in
  Nuten kaum breiter als der Fräser (eine Nut 14 breit, Ø 12: Räumen „passt
  nicht hinein“). Damit die Nut in zwei Gruppen antreten kann, entscheidet der
  Wettbewerb einer Gruppe mit nur einem Teilnehmer nichts mehr (außer gegen rote
  Blöcke). **Dabei gefunden** und behoben (P-2026-10-01-44, 0.59.1): Räumen
  ließ an Taschenwänden 0,75 mm statt des Aufmaßes 0,3 stehen – der letzte Ring
  kam aus dem Raster, eine Zelle neben dem Gesperrten; um Inseln galt schon der
  genaue Versatz (`inselringe`). Jetzt auch an der Wand einer Tasche, nach dem Ring
  aus dem Raster (direkt statt seiner wäre der Schritt größer als ae – je Lage eine
  Rampe mehr). Die Tasche des Prüfstands braucht 0,88 statt 0,78 min – die alte
  Bestmarke lag mit dem Wirkungsgrad 1,08 über der Untergrenze, also mit
  Material, das stehen blieb; die Platte 34,49 statt 34,38 min. Prüfung
  `test_nut` (Sacknut 20 breit mit Kreisen, Durchgangsnut 14 breit mit Rampe; im
  Quader leer bis zum Grund, daneben nichts angeschnitten), Szenario
  `szenario_nut`.
  Dann **Reiben** (P-2026-10-01-41, 0.57.0; 4.1 Punkt 7): FreeCADs Bohren mit
  G85 (`feedRetractEnabled`, heraus im Vorschub) und der Reibahle im Ø der
  Bohrung (`reiben.py`): durchgehend 1 mm unter den Grund (`ANSCHNITT`),
  Sackbohrungen mit Bohrspitze bis zum Grund der Wand, je Tiefe eine Operation;
  eine Sackbohrung mit ebenem Grund nicht (kein Bohrer bohrt sie vor). Den Haken
  setzt man selbst. Dann bohrt „Bohren“ kleiner vor (`bohren.REIBZUGABE`
  0,15–0,5 mm auf den Ø, `kann(…, reiben=True)`, vorgewählt der größte; die Zeile
  sagt es), „Bohrung fräsen“ und die Kontur treten in geriebenen Bohrungen nicht
  an (sie fräsen auf Maß) und sagen warum; die Kontur lässt sie aus, wenn sie
  weitere Wände hat. Die Operation kommt nach Bohren und Senken. Prüfung
  `test_reiben` (durchgehend und mit Spitze, Vorbohren Ø 9,8 ja, Ø 10 und 9,4
  nicht, G85, Endtiefen), Szenario `szenario_reiben`.
- **S3h Nullpunkt und Spannung** (Manuel, 2026-10-01): Der Nullpunkt des Jobs
  frei setzbar – aus einem Punkteraster des Rohteils (beim Quader 22 Punkte:
  die 8 Ecken, die 12 Kantenmitten, die Mitte oben und unten) und um x, y, z
  mm verschoben; das Teil mit dem Rohteil rückt so, dass der Punkt im
  Ursprung liegt (die Achsen im 3D zeigen ihn). Dazu „von unten gespannt“ in
  der Rohteil-Definition: so viel steckt im Schraubstock – die Prüfung zeigt
  es und meldet jede Bahn darunter.
  Der Nullpunkt ist gebaut (P-2026-10-01-21, 0.41.0): Block „Nullpunkt“ im
  Assistenten mit der Liste der 22 Punkte und drei Versatzfeldern; Teil und
  Rohteil rücken sofort (das Rohteil aus dem Modell merkt sich seine Lage nur
  beim Anlegen – es wird mitgeschoben). **„Von unten gespannt“ gebaut (P-2026-10-04-10):**
  Feld in Schritt 1 unter dem Rohteil, am Grundjob `CamAddonGespannt` (im Eigenschaften-Editor
  änderbar); `spannung.pruefen` meldet je Operation die tiefste Stelle, an der die Spitze unter
  das Rohteil fährt oder unter der Spannhöhe mit dem Fräser über den Umriss des Rohteils
  (Hüllquader) hinausragt – eine Tasche im Teil bleibt still; Ebenen (3+2) im Grundjob
  gerechnet. „Auf der Maschine prüfen“: Urteil „Spannung“ (grün/rot), die Sätze unter den
  Hinweisen. **Der Schraubstock als Körper (P-2026-10-04-11):** `spannung.schraubstock` – zwei
  Backen vorn und hinten (Y) am Rohteil, 20 mm dick, so lang wie es und so hoch wie gespannt; im
  Bild des Prüffensters und in der Kollision auf der Werkstückseite („der Schraubstock“: jedes
  Werkzeugteil, auch die Schneide im Vorschub).

## 11. Maßstab: Manuels Platte (2026-10-01)

Manuels Aufgabe für die Strategien: Platte 200 × 200 (Nullpunkt in der Mitte
der Oberseite), Zapfen Ø 20, 20 hoch bei (50, 50), Tasche Ø 45, 20 tief bei
(−50, −50); Rohteil 50 hoch (oben am Zapfen), 5 mm von unten gespannt.
Werkzeug Ø 12 VHM: ae 1,5 mm (gelesen als mm – 1,5 % von D wären 0,18 mm),
ap 25, fz 0,1, vc 85 m/min, 4 Schneiden angenommen → n 2255, vf 902 mm/min;
Helix 0,7 mm je Umdrehung, Rampe 3°. Gesucht: die kürzeste Zeit. Die Datei:
`beispiele/platte_zapfen_tasche.FCStd`. (Manuel schrieb „Klotz 100 × 100 × 50“
– mit den Lagen bei ±50 geht nur 200 × 200; so ist es gerechnet.)

Weg müssen 825 cm³: 794 über der Platte, 32 in der Tasche. Mit ae 1,5 und
ap 20 (die ganze Tiefe) ist das Zeitspanvolumen 27 cm³/min – die Untergrenze
für jede Strategie, die den Fräser dauernd im Eingriff hält:
**31 min** reine Spanzeit (29 Platte, 1,2 Tasche, 0,3 Schlichten).

| Strategie | Platte | Tasche | Zapfen | Summe |
| --- | --- | --- | --- | --- |
| heute: Planfräsen ap 2, ae 7,8 (0,65 D), Tasche über die Kontur in Lagen, Kontur Zapfen | 74,0 min (10 Lagen, 310 Zeilen, 62 m) | 4,6 min | 0,9 min | **80 min** |
| heute mit ganzer Schneide: Planfräsen ap 20, ae 1,5; Tasche über die Kontur ap 20 (ganz räumen) | 39,3 min (1 Lage, 151 Zeilen, 33 m; seit P-49 41,9 – die erste Zeile griff 9,6 mm breit, 20 tief) | 3,9 min (12 Versätze, je mit Rampe) | 0,9 min | **44 min** |
| S3f Räumen (gebaut, 0.45.0): Ringe ap 20, ae 1,5, hinein von außen in der Luft, zuletzt um den Zapfen; Tasche Rampe 3° einmal rundum, dann Ringe nach außen; Kontur nur mit dem Aufmaß | 33,9 min (1 Lage, gemessen; geschätzt waren ≈ 33; bis P-48 33,1 – das Rechteck biss in den Zapfen, 120 mm in voller Breite) | 1,2 min (gemessen; geschätzt ≈ 1,3) | 0,3 min | **35,6 min** (gemessen, `test_pruefstand`; 34,8 bis P-48, 34,7 bis 0.59.0, als das Räumen in der Tasche 0,45 mm mehr stehen ließ) |
| Untergrenze (Fräser nie aus dem Eingriff) | 29 min | 1,2 min | 0,3 min | **31 min** |

Gemessen mit `scripts`-freiem Rechenlauf (Sonde, 1.1.3): Planfräsen und
Kontur wie gebaut (0.40.1), die Zeit mit `bahn.zeit` (P-2026-10-01-22): vf
902, dazu die **festen Vorgaben** Eilgang 10 m/min und Beschleunigung 1 m/s²
(Manuel, 2026-10-01: „Eilgang und Beschleunigung dauerhaft festsetzen“),
anhalten an jeder Ecke, durch Bögen hindurch. Mit denselben Werten wird
jede Strategie gemessen – sie stehen in `export.VORGABE_…` und gelten im
Prüffenster, wo die Maschine nichts sagt. Die reine Vorschubzeit (ohne
Eilgang und Beschleunigung) liegt 1–2 % darunter (73,5 / 39,1 / 3,6 min):
bei ae 1,5 wiegen die 150 Wenden je Lage wenig, bei ae 7,8 in zehn Lagen
die 300 mehr. Was die Tabelle lehrt: Die ganze Schneide (ap 20 statt 2)
halbiert die Zeit schon mit den heutigen Zeilen; der Rest zur Untergrenze
sind Wenden, Überlauf (0,6 D je Zeilenende: 2,2 m) und – in der Tasche – die
Rampe je Versatz (die Kontur fährt jeden Versatz als eigene Bahn). Beides
nimmt S3f: eine Spirale, einmal hinein. Die Helix mit 0,7 mm je Umdrehung
ist auf Ø 6 nur 2,1° steil und auf Ø 33 0,4° – die Rampe mit 3° ist bei
diesem Werkzeug immer schneller (0,4 min statt 0,6 bis 3,3).

Dabei gefunden (0.40.1): FreeCADs Starttiefe „OpStartDepth“ liegt 1 mm über
dem Modell, nicht auf dem Rohteil – endet das Rohteil oben am Zapfen, wurde
aus einer Lage von 20 zwei von 10,5; die Lagen beginnen jetzt am Rohteil
(`OpStockZMax`), und 0,05 mm Spiel (`hoehenfeld.LAGEN_SPIEL`) geben keine
Lage mehr.

**Der Maßstab (Manuel, 2026-10-01: „generell sollte dann jede Strategie und
Szenario mit diesem Fräser und den Werten gerechnet und geprüft werden, wenn
es um Werkzeugwege geht“):** Der Fräser oben ist `werkzeuge.standardwerkzeug()`
– die eine Definition (Ø 12, 4 Schneiden angenommen, Schneidenlänge 26, Rampe
3°; Schruppen mit ae 1,5 / ap 25 / fz 0,1 / vc 85, Planen seit P-2026-10-02-54 mit
ae 8,4 / ap 1,2 / fz 0,07 / vc 85 – das Planfräsen nimmt den, der für seine Flächen schneller
ist –, Schlichten mit ae 0,3, dem Aufmaß der Kontur). Mit ihm rechnen alle
Prüfungen und Szenarien der 2,5D-Strategien (`test_planfraesen`,
`test_kontur`, `test_raeumen`, `test_quader`, `szenario_bearbeitung`,
`szenario_kontur`, `szenario_raeumen`), mit
ihm und den festen Vorgaben für die Zeit (Eilgang 10 m/min, 1 m/s²) bekommt
jede neue Strategie ihre Zeile in der Tabelle oben (P-2026-10-01-23;
Arbeitsregeln, Abschnitt 5). Das Ziel dahinter ist nicht der Fräser, sondern
Grundsatz 0 (Abschnitt 5): Für das gewählte Werkzeug den schnellsten Weg
rechnen, zwischen den Strategien die schnellste nehmen – die Tabelle oben
ist dieser Wettbewerb, von Hand; der Assistent führt ihn selbst, sobald zwei
Strategien dieselbe Aufgabe lösen (S3f). Beim Umstellen gefunden: In der Tasche schwenkt
das tangentiale Einfahren der innersten Schruppbahn zur Mitte – mit Ø 12
reichte es 1,8 mm in die gegenüberliegende Wand (mit Ø 10 passte es gerade
noch), weil die Hüllfläche die eigenen Wände der Kontur nahe der Bahn
ausblendet; jetzt hält das Ein- und Ausfahren zu jeder Wand der Konturen den
Abstand der Bahn (Radius + Aufmaß), sonst wird es kürzer. Die 4-Achs-Prüfungen
(runde Stange, Manuels Testteil) behalten ihre Werkzeuge: Dort wählt das Teil
den Fräser (Kugel Ø 6 fürs Schlichten, Ø 6 für Plan indexiert) – ob auch sie
auf den Ø 12 sollen, entscheidet Manuel.

**Die Zielzeit (Manuel, 2026-10-02: „Das man erstmal ein Ziel rechnet von der Zeit her …
macht der 12er Fräser überhaupt Sinn für so einen Test oder sollten wir doch noch andere
Fräser definieren … dem Benutzer im Zweifelsfall von seiner Werkzeugkiste den besten Fräser
vorschlagen“; P-2026-10-02-29):** `zielzeit.py` rechnet vor jeder Bahn, wie viel weg muss
(von oben, je Zelle das Material über dem Teil, neben dem Teil bis zu seinem Boden) und wie
lange ein Fräser mit seinen Werten dafür mindestens braucht: je Zelle ceil(T ÷ ap) Lagen,
jede überstreicht die Zelle mit der Breite ae – Zielzeit = Σ Zelle · Lagen ÷ (ae · vf). Das
ap zählt also nur so weit, wie die Stelle es hergibt (Manuels zwei Beispiele, beide in
`test_zielzeit`: 1000 × 1000, 5 mm ab – 739 min mit dem Ø 12, ein Fünftel seines
Zeitspanvolumens; 100 × 100, 25 mm ab – 7,4 min, voll genutzt). Was der Fräser nicht
erreicht (die Schließung des Bodens mit seiner Scheibe: Ecken und Nuten enger als er), ist
sein Rest; `vergleiche()` stellt die Fräser einer Werkzeugkiste nebeneinander, je mit dem
Einsatz, der hier am schnellsten ist (`bestes_angebot`, P-2026-10-02-54: eine dünne Schicht
der Ø 12 mit „Planen“, tiefes Material mit „Schruppen“), und mit dem schnellsten kleineren
für den Rest. Die Werkzeugkiste der Tests ist `werkzeuge.testkiste()`:
T1 Ø 12 (der Standardfräser), T2 Planfräser Ø 50 (z 5, ae 35, ap 2, vc 200, fz 0,15 →
vf 955), T3 Ø 6 (ae 0,6, ap 12, vf 902), T4 Ø 20 (ae 2, ap 30, vf 649) – angenommene Werte.
Der Assistent zeigt die Zielzeit grau über den Strategien, und den schnelleren Fräser aus
der Werkzeugverwaltung, wenn einer um mehr als ein Fünftel schneller wäre. Darunter
„Schnellere Fräser übernehmen“ (P-2026-10-02-51, 0.107.0; Manuel: „Ja, aber man muss nicht –
wenn man es mit einem Fräser fräsen will, ist das so“): Ein Klick setzt einen Planfräser ins
Planfräsen und den für den Rest ins Räumen, einen Schaftfräser ins Räumen und den für den Rest
ins Restmaterial; danach rechnet die Ziel-Zeile mit dem Fräser der angehakten Strategie und
bietet nichts mehr an, was schon angehakt ist. Auf Manuels Platte: Planfräsen mit dem Ø 50
29 min statt Räumen mit dem Ø 12 34 min – das Ziel des Ø 50 ist 14 min (2,17 × Ziel), hier
lohnt die Arbeit an der Bahn.

Die Maßstabsteile des Prüfstands mit dem Ø 12 (`test_zielzeit`; „Ziel“ ohne den Millimeter
über der Oberseite, wo die Strategien danach laufen):

| Teil | weg | Ziel Ø 12 | ap im Mittel | schnellste Bahn | × Ziel | Werkzeugkiste |
| --- | --- | --- | --- | --- | --- | --- |
| 50 × 50 mit Zapfen | 26,2 cm³ | 1,94 min | 10,0 mm | Räumen 2,69 | 1,39 | Plan 50: 0,39 min |
| Block mit Absatz | 13,6 cm³ | 1,63 min (mit 1 mm oben 1,92) | 5,2 mm | Planfräsen 2,08 | 1,28 | Plan 50: 0,21 min |
| Tasche 40 × 30 | 23,8 cm³ | 0,86 min (mit 1 mm oben 4,67) | 3,8 mm | Räumen 0,88 | 1,02 | Plan 50 + Ø 12: 1,05 min |
| Zwei Bohrungen | 15,4 cm³ | 0,67 min (mit 1 mm oben 4,67) | 2,4 mm | Bohrung fräsen 1,33 | 1,99 | Plan 50 + Ø 12: 0,86 min |
| Manuels Platte | 825,2 cm³ | 30,50 min | 20,0 mm | Räumen 33,86 | 1,11 | Plan 50 + Ø 12: 13,0 min |

Was daraus folgt: Wo tief weg muss (die Platte, die Tasche), nutzt der Ø 12 sein ap fast
ganz, und das Räumen liegt nah am Ziel (1,02–1,11). Wo wenig weg muss, ist er der falsche
Fräser: Den Millimeter über der Oberseite (100 × 60) braucht er mit ae 1,5 allein 3,8 min,
der Planfräser 0,18. Das Planfräsen am Zapfen (2,94 × Ziel) und die Kontur (2,84) lassen
am meisten liegen – dort lohnt die nächste Arbeit an der Bahn.

Der Versuch mit der echten Bahn (Planfräsen mit dem Ø 50, ae 35, ap 2 auf Manuels Platte)
fand einen Fehler: Am Ende der Zeile vor dem Zapfen fuhr die Wandfahrt gerade zur vorigen
Zeile zurück, quer durch den Zapfen – geprüft waren nur die Zeilen, nicht der Weg dazwischen
(mit ae 1,5 bleiben dort höchstens 0,05 mm unentdeckt, mit ae 30 und R 25 4,5 mm). Seit
P-2026-10-02-30 prüft das Planfräsen auch zwischen weit auseinanderliegenden Zeilen. Danach:
26,9 min (Ziel 11,9; die Zeilen laufen je 0,6 D über den Rand, zehn Lagen ap 2), dazu bleibt
zwischen den Zeilen um den Zapfen Material für die Kontur. Mit dem Ø 12 räumt das Räumen die
Platte in 33,9 min – der Planfräser lohnt sich hier weniger, als die Zielzeit verspricht.
Plan indexiert hatte dieselben Schritte zwischen den Zeilen: Ein Stift Ø 1,2 zwischen zwei
Zeilen (Ø 6, ae 4) wurde um 0,1 mm gestreift – seit P-2026-10-02-31 prüft auch Plan indexiert
dazwischen (`vierachs_bahn._zwischen`, `_geteilt`, gemeinsam mit dem Planfräsen).

**Nächster Schritt: Planfräsen Zelle für Zelle (Versuch, noch nicht eingebaut).** Am Zapfen
braucht das Planfräsen 2,9 × das Ziel: `vierachs_bahn._fahrten` wechselt hinter einer Insel
nach jeder Zeile die Seite – jede Zeile wird eine neue Fahrt mit Rampe (3° auf 10 mm: 190 mm
lang; 54 Rampen, 187 Halte). Versuch: die Zeilen in Zellen zerlegen (Stücke, die von Zeile zu
Zeile eins zu eins überlappen; bei Teilung oder Vereinigung an der Insel endet die Zelle) und
jede Zelle für sich hin und her fahren, eine neue Zelle vom Ende in der Luft aus:

| Teil | heute | Zellen |
| --- | --- | --- |
| 50 × 50 mit Zapfen | 5,70 min, 54 Rampen | 3,79 min, 9 Rampen |
| Manuels Platte | 41,88 min, 60 Rampen | 35,22 min, keine |
| Platte oben + Tasche | 47,90 min | 41,11 min |

Dabei aber „voll 4 mm“ (vorher 0) und Eingriff bis 6,3 ae (vorher 4,0): Hinter der Insel reicht
jede Zeile ein Stück weiter zu ihr als die vorige – dieses Stück schneidet die Zelle jetzt
waagrecht in voller Tiefe, vorher lag es in einer Rampe. Darum noch nicht eingebaut; fertig wird
es mit einem Konturgang um die Insel vor den Zellen (dann bleibt neben ihr kein Halbmond), oder
die Zellen hinter der Insel laufen auf sie zu statt von ihr weg.

**Gebaut (P-2026-10-03-29; Manuel: „ja, mach das alles mal“)** – ohne Konturgang, mit zwei
Regeln (`planfraesen_bahn._zellenfahrten`):

- *Die Zeilenenden rücken nicht vor* (`_monoton`): Eine Zelle wird dort geteilt, wo ein Ende der
  Zeile – an einer Insel oder Wand – über das der vorigen hinaus vorrücken würde, und in der
  Richtung gefahren, in der es zurückweicht. Neben dem Zapfen: unten bis zum breitesten Punkt
  aufwärts, oben von der Zeile über ihm abwärts – beide auf ihn zu.
- *Eine Zelle beginnt neben Gefrästem* (`_bereit`): Ihre erste Zeile braucht vor sich schon
  Gefrästes oder kein Material. Ohne diese Regel begann die obere Hälfte neben dem Zapfen der
  Platte, bevor die Zeilen darüber gefräst waren – 253 mm in voller Breite. Die Zelle über der
  Insel läuft darum von oben herab, dann die oberen Hälften zu ihr hin.
- Die nächste Zelle: lieber eine, die in der Luft beginnt, sonst die nächstgelegene. Eine Zelle,
  die zur ersten Zeile hin läuft, rechnet auf dem quer gespiegelten Raster
  (`_Raster.gespiegelt`; die Wandfahrten vergleichen in Zählrichtung der Zeilen, `_Raster.vor`).

Prüfstand (Standardfräser, ae 1,5, ap 25):

| Teil | vorher | jetzt |
| --- | --- | --- |
| 50 × 50 mit Zapfen | 5,70 min, 54 Rampen, Eingriff bis 4,0 ae, über 1,25 ae 28 mm am Stück | 4,05 min, 13 Rampen, bis 3,2 ae, 2 mm |
| Manuels Platte | 41,88 min, 60 Rampen, bis 6,0 ae | 35,20 min, keine Rampe, bis 5,8 ae |
| Platte oben + Tasche | 47,77 min | 41,81 min |

Nirgends in voller Breite, nirgends ins Teil, nichts stehen geblieben. Am Zapfen 2,05 × Ziel
(vorher 2,9); an der Platte liegt das Räumen (33,9 min) weiter vorn.



## 12. Manuels Punkte vom 2026-10-02 (früh)

Nach den Bildern der Nacht; jeder Punkt mit dem, was heute ist, was sein soll und woran man
erkennt, dass es fertig ist. Reihenfolge in `STATUS_SNAPSHOT.md`.

### 12.1 ae ist ein Richtwert

Manuel: „Ae 1.5 bedeutet, dass versucht wird, dass immer etwa 1,5 mm vom Material weggenommen
werden … ob das nun 1,5, 1,3 oder 1,7 sind, spielt keine Rolle … von dem Maß können kurzzeitig
auch mal 70 % mehr genommen werden, wenn fürs Einfahren nötig ist … oder eben beim Einfahren
auch sehr wenig … wenn's dadurch dann eine bessere Zeit ergibt und man sich Wege sparen kann“;
dazu: „Die Bahnen schauen auf den Bildern immer sehr eng.“

- **Bis P-2026-10-02-55:** Die Bögen der offenen Nut rücken nur so weit vor, dass der Fräser die Delle nicht
  weiter umschlingt als eine gerade Wand mit ae – in der 16er Nut mit dem Ø 12 0,4 mm statt
  1,5. Der Prüfstand lässt nirgends mehr Querschnitt zu als ae · ap.
- **Warum es eng aussieht:** In der 16er Nut überstreicht jeder Bogen mit der Schneide die
  ganze Breite, 15,4 mm, während die Mitte des Fräsers nur 5,3 mm fährt. Je mm Weg trägt er
  so etwa dreimal den Schritt ab: Mit 0,4 mm Schritt misst der Prüfstand eine Breite im
  Eingriff von 1,5 ae; mit 1,5 mm Schritt wären es über 5 ae – der Fräser hätte fast dreimal
  so viel zu tun wie auf gerader Bahn mit ae 1,5. In breiten Nuten (30) rückt er um fast ae
  vor. Der Schritt ist also nicht zu vorsichtig gezeichnet, sondern folgt der Last.
- **Soll:** ae ist die Last, die der Fräser trägt – im Mittel so viel Material je mm Weg wie
  auf gerader Bahn mit ae, dauernd zwischen 0,85 und 1,15 davon, kurz (beim Einfahren, auf
  höchstens einer Fräserbreite Weg) bis 1,7. Weniger geht immer. So dürfen die Morph-Bögen
  am Anfang einer Nut größer greifen, und der Prüfstand meldet erst über 1,7 ae.
- **Zu entscheiden (Manuel):** (a) so, nach der Last – empfohlen; (b) Schritt wörtlich ae
  (1,5 mm je Bogen) – weniger Bögen, aber die dreifache Last in schmalen Nuten.
- **Fertig, wenn:** der Prüfstand 1,7 ae kurz zulässt, mehr oder länger aber meldet, und die
  Bahnen den Spielraum nutzen, wo er Zeit spart.
- **Entschieden (Manuel, 2026-10-02):** „a: im Mittel würde ich sagen. Sogar 25 %, solange es
  noch über r geht … Also Radius des Durchmessers“. Gelesen als: ae ist die Last im Mittel;
  dauernd bis 25 % mehr; und **nie über r** – der Fräser umschlingt das Material höchstens zur
  Hälfte (Eingriffswinkel 90°, wie eine gerade Wand mit ae = D/2). Kurz bis 1,7 ae bleibt
  (Manuels Satz oben). Ist „über r“ anders gemeint, sagt Manuel es.
- **Gebaut:** P-2026-10-02-56, 0.110.0.
  - `bahn.LAST_DAUERND` = 1,25 und `bahn.LAST_KURZ` = 1,7 (× ae) – die eine Stelle für alle
    Strategien.
  - `nut_bahn._bogenschritt`: im Mittel ae – je Bogen 2 ρ s Fläche auf π r_l + s Weg (ρ = r_l +
    R), s = π r_l ae / (2 ρ − ae); in der Mitte höchstens 1,7 ae (die Breite dort
    s (2 ρ − s) / (2 r_l)); über 1,25 ae höchstens 0,8 Fräserbreiten am Stück gerechnet
    (`UEBER_WEG` – der Fräser greift vor seiner Mitte ein, gemessen wird bis 6 % mehr; erlaubt
    ist eine Fräserbreite); nie über r: s² + 2 r_l s ≤ 2 r_l R. Mit dem Ø 12, ae 1,5 und
    Aufmaß 0,3: Nut 16 0,58 mm (vorher 0,40), Nut 20 0,97 (0,65), Nut 30 1,36 (0,95), Nut 40
    1,44 (1,10) – in breiten Nuten begrenzt die Fräserbreite über 1,25 ae den Schritt, die Last
    im Mittel ist dort 0,85 ae; in sehr breiten wird der Schritt etwas größer als ae.
  - Der Prüfstand misst die Breite im Eingriff auf Bögen **je Sehne** (vorher je Bogen
    gemittelt – er sah die Spitze in der Mitte nicht), auf Wunsch im feineren Raster (`raster`;
    die Bögen rücken kaum mehr als eine Zelle von 0,5 mm vor), und den längsten Weg am Stück
    über 1,25 ae (`last_lang`, in der Zeile).
  - Gemessen (Raster 0,1): in der Mitte der Bögen höchstens 1,6 ae, über 1,25 ae höchstens
    10 mm am Stück. Nut 16 × 60 offen 1,68 → 1,25 min (171 → 118 Bögen), mit Halbkreis
    0,99 → 0,73, Nut 30 offen 3,27 → 2,38, geschlossene Nut 20 × 50 47 → 31 Bögen. An den
    Wänden ist die Nut wieder vorn: die Kontur 28 % langsamer (20 × 50), 21 % (16 × 60 offen).
    `test_nut`, `test_nut_offen` prüfen Schritt und Last.
  - **Offen:** Über 1,7 ae oder länger über 1,25 ae meldet der Prüfstand bisher nur in den
    Prüfungen der Nut, in `urteile()` noch nicht für alle Strategien – Räumen in Ecken,
    Planfräsen beim Einfahren und der Keil unter der Helix zeigen heute bis 8 ae; teils dünne,
    breite Schnitte, die keine Last sind (dort zählt der Querschnitt). Das ist der nächste
    Schritt.
  - **Gemessen (P-2026-10-02-74, Last = Querschnitt ÷ (ae · Lagentiefe)):** Räumen in der
    Tasche 40 × 30 – an den scharfen Ecken der Ringe bis 3,4 ae, 29 mm am Stück über 1,7;
    Räumen am Rohteilrand 1,6 ae (46 mm), um den Zapfen der Platte 1,67 ae (ein ganzer Ring);
    Bohrung fräsen 2 ae (10 mm). FreeCADs Adaptiv-Kern (`area.Adaptive2d`) hält mit 0,9 · ae/D
    als Schritt überall höchstens 1,25 ae; im Offenen ist er schneller (Zapfen 2,0 statt 2,7 min,
    Platte 30 statt 34, Manuels Klotz 9,4 statt 9,8), in Taschen langsamer (+30 bis +100 %).
  - **Entschieden (Manuel, 2026-10-02, Frage 6):** „das was schneller ist ... gewinnt .. wenn
    man volle Tiefe fräst muss der ae schon in einem Rahmen bleiben der nicht das Doppelte ist ..
    bei einem ae von 1.5mm ... sind 3.5mm nicht drinnen ... aber 2mm wären ... vertretbar ..
    solange das nicht ein Dauerzustand ist .. und Ecken kann man ja erstmal gesondert mit Bögen
    rausfahren .. grob vorarbeiten bis man zu den Ecken kommt, diese dann wie eine Nut grob
    vorarbeiten mit Bögen .. und dann wieder die Kontur der Tasche weiter“. Also: Die schnellste
    Variante gewinnt, aber nur, wenn sie die Last hält (dauernd höchstens 1,25 ae, kurz bis
    1,7, nie das Doppelte); Ecken der Tasche vorräumen wie eine Nut in Bögen, dann die Ringe
    weiter; Adaptiv rechnet als weitere Variante mit. Zu Manuels Bild (Klotz, Zapfen am Rand,
    22-mal hoch und runter, weil der Spalt zwischen Zapfen und Rand – 11 mm – schmaler ist als
    der Fräser): „effektiv ist da nur ein Kreis ... nachdem außenrum alles bis auf ae+Aufmaß
    weggeräumt wurde“ – den Spalt ebenso mit Bögen vorräumen statt jeden Ring abreißen zu
    lassen (oder Adaptiv, wenn schneller).

### 12.2 Nuten in Bögen, auch geschlossene – und Konturen von der Seite her

Manuel zu den Bögen der offenen Nut: „So ähnlich mit den Kreisbögen war das gedacht. Frage ist
nur, warum mitten drinnen ein kompletter Kreis gefahren wird … Und generell kann man auf diese
Art viele Konturen herstellen, sodass man sich immer mehr an die nötige Kontur annähert, indem
man immer so seitlich einfährt.“

- **Der volle Kreis** auf dem Bild von 05:13 war nur der Fräser selbst (Ø 12, zum
  Größenvergleich gezeichnet); gefahren wird in der Mitte kein Kreis (Antwort von 05:14).
- **Heute:** Die geschlossene Nut fährt nach der Helix volle Kreise (Trochoide); die hintere
  Hälfte jedes Kreises fährt im Schnellvorschub durch, was schon frei ist.
- **Soll:** Nach der Helix am einen Ende Bögen wie in der offenen Nut – im Gleichlauf vor
  durchs Material von Wand zu Wand, quer zurück über die freie Seite im Schnellvorschub; am
  anderen Ende gehen die Bögen in den Halbkreis über (je Schritt etwa ein Zehntel kürzer).
  Danach das Prinzip auf Taschen und Konturen übertragen: Bögen, die sich von der freien
  Seite her an die Kontur herantasten.
- **Fertig, wenn:** in keiner Nut mehr ein voller Kreis außer der Helix steht und die
  geschlossene Nut nicht langsamer ist als heute.
- **Gebaut:** P-2026-10-02-53, 0.108.0 – die geschlossene Nut in Bögen: je Lage die Helix,
  unten einmal rundum, dann Halbkreise von Wand zu Wand bis in den Halbkreis am anderen Ende
  (`nut_bahn._geschlossene_lagen`, `_boegen` mit `s_anfang`); kein voller Kreis mehr außer
  unten an der Helix (`test_nut`). Mit dem schonenden Schritt (Manuel, 2026-10-02, auf „Soll
  die geschlossene Nut auch den schonenden Schritt bekommen? Dann gewinnt in schmalen Nuten
  öfter die Kontur“: „Ja“) ist sie langsamer als die Kreise von gestern, nicht schneller: in
  der Nut 20 × 50 mit dem Ø 12 0,65 statt 1,5 mm je Schritt, 47 Bögen statt 21 Kreisen,
  1,20 statt 0,80 min – je Schritt sind die Bögen etwa ein Zehntel kürzer als ein Kreis, aber
  es sind mehr als doppelt so viele. An der Wand liegen Nut und Kontur jetzt gleichauf
  (die Kontur knapp vorn, „weniger als 1 % langsamer“). Mit ae als Last (12.1 (a),
  P-2026-10-02-56) ist der Schritt 0,97 mm – 31 Bögen, die Nut wieder vorn (die Kontur 28 %
  langsamer).

### 12.3 Die Zielzeit misst die Wegstrategie

Manuel: „Man benötigt ja irgendeine Zeit, die sinnvoll ist, die man erreichen kann … da geht's
gar nicht um die Anzahl oder Größe an Fräsern, sondern einfach darum zu sehen: Ist diese
Wegestrategie wirklich gut?“

- **Soll:** Je Strategie steht neben ihrer Zeit „× Ziel“ – ihre Zeit geteilt durch die Zielzeit
  desselben Fräsers für dieselben Flächen (Abschnitt 11). Der Prüfstand führt × Ziel je Teil
  und Strategie; wo es groß ist, lohnt die Arbeit an der Bahn.
- **Fertig, wenn:** die Ergebniszeile jedes Blocks „… etwa 34 min – 1,03 × Ziel“ zeigt.
- **Gebaut:** P-2026-10-02-45, 0.101.0 – für Planfräsen und Räumen, gleich hinter der Zeit:
  „→ 1 Lage, 163 Zeilen, etwa 43 min · 1,41 × Ziel – Zeilen längs X …“. Das Ziel rechnet mit
  ihrem Fräser, ihrem ae und ap und dem vf ihres Einsatzes für das Material bis zu ihren Flächen
  (`zielzeit.Material.bis`); räumt das Räumen nach dem Planfräsen nur die Taschenböden, zählt
  nur die Tasche. Noch nicht: Kontur, Nut, Bohrung fräsen (ihr Ziel ist kein Volumen von oben)
  und der Prüfstand.

### 12.4 Schlichten nach dem Räumen, Messstopp dazwischen

Manuel: „Wenn ich jetzt Räumen gemacht habe und habe ein Aufmaß an den Wänden, aber am Boden
nichts … brauch ich noch eine Möglichkeit, das Ganze zu schlichten … Aber was vielleicht
wichtig ist: dass man zwischen Schruppen und Schlichten eine Pause setzen kann – sozusagen ein
Messstopp, gleich in derselben Maske –, um dann im Postprozessor direkt zu wissen, für Siemens
als Beispiel F_HOME; M0 … Dann kann der Bediener messen und dann wieder Start drücken, und es
geht weiter mit Schlichten. Das muss noch rein.“

- **Heute:** Das Aufmaß an den Wänden schlichtet nur die Kontur – und die geht nur, wenn man
  Wände anklickt. Einen Halt im Programm legt das Addon nicht an.
- **Soll:** Im Block „Räumen“ zwei Haken: „Wände danach schlichten“ (die Wände aller gewählten
  Flächen im Aufmaß, mit demselben Fräser oder einem eigenen) und „Messstopp vor dem
  Schlichten“. Der Messstopp ist eine eigene Operation im Job zwischen den beiden (FreeCADs
  „Benutzerdefiniert“ mit G-Code); ihre Zeilen kommen von der Maschine (W-005), vorbelegt:
  Z auf sichere Höhe, M5, M0, danach die Spindel wieder an (M3 S…) – an Manuels Siemens
  „F_HOME“ und „M0“.
- **Fertig, wenn:** Räumen mit beiden Haken drei Operationen anlegt – Räumen, Messstopp,
  Schlichten – und das Programm an der Stelle anhält.
- **Gebaut:** P-2026-10-02-44, 0.100.0 – „F_HOME“ und andere Unterprogramme kann FreeCADs
  G-Code nicht tragen („Badly formatted GCode command“): Sie schreibt erst der Postprozessor des
  Addons (W-005); bis dahin Kommentar (MESSSTOPP), Z hoch, M5, M0, M3 S….
  **Nachgezogen (P-2026-10-04-06):** Der Postprozessor des Addons schreibt im Messstopp statt
  „Z hoch“ den Weg zum Wechselpunkt der Maschine – den Befehl „Zum Wechselpunkt“ der Steuerung
  (Siemens vorbelegt `G0 SUPA D0 Z…`, zur Wahl `F_HOME`); ohne Wechselpunkt bleibt Z hoch. Dann
  M5, M0, M3. „Auf der Maschine prüfen“ fährt denselben Weg.

**Zur Besprechung (Manuel, 2026-10-02: „Das mit dem Wände-danach-Schlichten müssen wir nochmal
besprechen … Wenn ich jetzt Aufmaß Boden 0,5 einstelle, kann ich danach nicht nur Wände
schlichten, da muss er alles nochmal abfräsen … Außerdem will ich die Wände vielleicht mit
anderen Werten schlichten oder mit einem anderen Werkzeug … Aber eins nach dem anderen.“)**

- **Heute:** „Wände danach schlichten“ fährt mit dem Räumfräser (Einsatz „Schlichten“, wenn er
  einen hat) die Wände im Aufmaß nach, bis auf den fertigen Boden. Mit Aufmaß am Boden bleibt
  der Boden 0,5 mm zu hoch – nur ein Streifen an der Wand ist fertig, mit einer Stufe davor.
  Fräser und Werte lassen sich nicht wählen.
- **Option A (Empfehlung) – ein eigener Block „Schlichten danach“** direkt unter „Räumen“, nur
  wählbar, wenn Räumen angehakt ist. Er hat, was jede Strategie hat – Fräser, Einsatz, Felder –,
  dazu die Haken „Boden“, „Wände“ und „Messstopp davor“. „Boden“ ist von selbst an, wenn das
  Räumen Aufmaß am Boden lässt. Vorgewählt: der Räumfräser mit seinem Einsatz „Schlichten“.
  In Schritt 3 steht er als eigener Abschnitt, das Räumen bleibt klein.
- **Option B – alles im Block „Räumen“:** unter dem Haken „Schlichten danach“ ein
  aufklappbarer Bereich mit Fräser, Einsatz, Boden, Wände, Messstopp. Weniger Blöcke, aber das
  Räumen wird wieder groß – das, was Manuel am Assistenten „erschlägt“.
- **Option C – mit den Strategien, die es gibt:** Räumen (Aufmaß 0) und Kontur (Aufmaß 0) ein
  zweites Mal anhaken, jede mit ihrem Fräser. Kein neues Fenster, aber man muss wissen, wie;
  der Haken „Wände danach schlichten“ fiele weg – gegen „gleich in derselben Maske“.

```
 Schritt 2 von 3 – Was soll weg?
 ☑ Räumen             → 1 Lage, 73 Ringe, etwa 34 min · 1,14 × Ziel
 ☑ Schlichten danach  → Boden 0,5 + Wände 0,3: 2 Bahnen, etwa 3 min

 Schritt 3 von 3 – Einstellungen
 Räumen
   Fräser  [T1 VHM 12 ▾]   Einsatz [Schruppen ▾]
   Zustellung 25 · Zeilenabstand 1,5 · Aufmaß Wand 0,3 · Aufmaß Boden 0,5
 Schlichten danach
   Fräser  [T3 VHM 10 ▾]   Einsatz [Schlichten ▾]
   ☑ Boden (0,5 mm)   ☑ Wände (0,3 mm)   ☑ Messstopp davor
   Zustellung [ leer: aus dem Einsatz ]   Zeilenabstand [ leer: aus dem Einsatz ]
                                              [← Zurück]  [Anlegen]
```

- **Dazu zu entscheiden** (je mit Empfehlung):
  1. Der Boden fährt (a) die Ringe des Räumens in einer Lage auf dem fertigen Boden mit dem ae
     des Einsatzes – ohne Wenden, im Gleichlauf – oder (b) Zeilen wie das Planfräsen.
     Empfehlung (a).
  2. Die Wände fahren (a) mit dem ap des Einsatzes, eine Wand bis zu dieser Höhe in einem Zug,
     höhere in Lagen, oder (b) immer in einem Zug über die ganze Schneide. Empfehlung (a).
  3. Reihenfolge (a) erst Boden, dann Wände – der Boden lässt das Aufmaß an der Wand stehen,
     die Wand fährt bis auf den fertigen Boden, unten bleibt keine Stufe – oder (b) erst Wände.
     Empfehlung (a).
  4. Ein anderer Fräser als der Räumfräser bekommt einen eigenen Controller; der Messstopp
     steht vor dem ersten Schlichten. Ohne Wunsch keine Frage.
- **Fertig, wenn:** Räumen mit Aufmaß 0,3 an den Wänden und 0,5 am Boden, „Schlichten danach“
  mit einem anderen Fräser und Boden und Wänden angehakt, im Prüffenster ein Teil ohne Rest und
  ohne Stufe am Boden ergibt.
- **Entschieden (Manuel, 2026-10-02):** **A** „genau so“ – der eigene Block „Schlichten danach“;
  dazu je die Empfehlung (Boden mit den Ringen des Räumens, Wände in Lagen mit dem ap des
  Einsatzes, erst Boden, dann Wände).
- **Gebaut (P-2026-10-02-90, 0.127.0):** der Block „Schlichten danach“ (`gui_bearbeitung.
  _SchlichtenDanach`) gleich unter „Rest räumen“, wählbar, sobald das Räumen angehakt ist,
  angehakt nur von Hand; die zwei Haken im Räumen sind weg. Fräser und Einsatz vorgewählt: der
  des Räumens mit „Schlichten“. Haken „Boden“ (an; ohne Aufmaß am Boden gibt es dort nichts zu
  tun), „Wände“ (an), „Messstopp davor“. Der Boden: ein Räumen ohne Aufmaß am Boden auf dem
  Materialstand nach dem Räumen – eine Lage, die Variante nach Zeit und Last wie beim Räumen –,
  mit dem Aufmaß des Räumens an den Wänden. Nicht ganz die Empfehlung (a): Der Zeilenabstand
  am Boden ist nicht das ae des Einsatzes „Schlichten“ (0,3 mm – das Aufmaß der Wand, am Boden
  über 300 Ringe auf 100 mm), sondern ein eigenes Feld, leer der halbe Fräserdurchmesser. Die
  Wände: eine Kontur mit Breite = Aufmaß bis auf den fertigen Boden, in Lagen mit dem ap des
  Einsatzes (Feld „Zustellung an den Wänden“) – ohne die Wände, die die Kontur fährt. Am Block
  50 × 50 mit Zapfen, 0,5 am Boden: Räumen, Messstopp, Boden schlichten, Wände schlichten; im
  Prüffenster auf dem Boden bis an den Zapfen nichts stehen geblieben
  (`szenario_raeumen_schlichten`). Dabei behoben: Mit einem Messstopp im Job trug das
  Prüffenster das Rohteil nicht ab (`restmaterial.fuer_quader` hielt die Operation ohne
  Bewegung für ein Werkzeug „nicht von oben“).

### 12.5 Der Assistent in Schritten

Manuel zum Bild des Assistenten: „Das erschlägt einen … Du musst das irgendwie sinnvoll
aufteilen. Das ist viel zu viel … Funktionen sollten alle da sein, aber das zu viel muss
einfacher werden“, „so kannst du das keinem vorsetzen“; „Oder man macht für die Strategien
einzelne Knöpfe, oder man fragt es in Schritten ab!“; „Rohteil und Nullpunkt können auch
einfach als extra Fenster gesetzt werden, wo man auf Weiter klicken kann, wenn's fertig ist.“

- **Heute:** eine Seite mit allem – Teil, Rohteil, Nullpunkt, Flächen, Werkstoff, Ziel, je
  Strategie ein Block mit Feldern; eingeklappt immer noch 771 Pixel.
- **Soll:** drei Seiten wie im 4-Achs-Assistenten, unten „Zurück“ und „Weiter“:

```
 Schritt 1 von 3 – Aufspannung            Schritt 2 von 3 – Was soll weg?
 ┌──────────────────────────────────┐     ┌────────────────────────────────────┐
 │ Teil        Platte               │     │ Flächen  Face3 eben, Höhe 0        │
 │ Unten liegt [Fläche anklicken]   │     │          [Oberseite] [leeren]      │
 │ X zeigt     [↺ 90°] [↻ 90°]      │     │ Weg 906 cm³ – Ziel 33 min mit T1   │
 │ Rohteil     1 mm rundum   ▸      │     │ ☑ Räumen        34 min  1,03 × Ziel│
 │ Nullpunkt   Oben Mitte ▾  ▸      │     │ ☐ Planfräsen    43 min  1,30 × Ziel│
 │                                  │     │ ▸ Passt nicht zur Auswahl (16)     │
 │                     [Weiter →]   │     │          [← Zurück]  [Weiter →]    │
 └──────────────────────────────────┘     └────────────────────────────────────┘
 Schritt 3 von 3 – Einstellungen
 ┌────────────────────────────────────────────────┐
 │ Räumen – T1 VHM 12 · Schruppen                 │
 │   Zustellung 25 · Zeilenabstand 1,5 · Aufmaß 0,3 │
 │   ☑ Wände danach schlichten  ☑ Messstopp davor │
 │   ▸ mehr (Boden, Gleichlauf …)                 │
 │                       [← Zurück]  [Anlegen]    │
 └────────────────────────────────────────────────┘
```

- **Fertig, wenn:** keine Seite rollen muss (Aufgabenbereich 800 Pixel hoch), alles von heute
  erreichbar bleibt und Manuel den Assistenten ohne Erklärung bedient.
- **Gebaut:** P-2026-10-02-42, 0.98.0 – drei Seiten mit „Zurück“ und „Weiter“, „Anlegen“ aus
  jedem Schritt.
- **Nachgebessert** (Manuel, 2026-10-02: „Also die Menüführung ist gut“; der Satz zu Schritt 1
  „Keine Ahnung, was das sagen soll … Wenn dann: Klick die Fläche an, die du bearbeiten willst“;
  „als Auswahl für den Nullpunkt ist Standard erstmal oben mittig“; „als Mensch erwartet man
  dann den Button unten, wo der Weiter-Button war“): P-2026-10-02-49, 0.105.0 – Schritt 1 sagt
  vor dem Klick „Klick die Fläche an, die du bearbeiten willst – dann legt das Addon den Job mit
  dem Rohteil an“, danach, was jetzt zu tun ist; der Nullpunkt ist beim ersten Mal „Mitte
  oben“, danach der des letzten „Anlegen“; im letzten Schritt steht „Anlegen“ unten rechts
  (beim Ändern „Übernehmen“), dasselbe wie „OK“ der Aufgabe.

### 12.6 Aufspannung: welche Fläche unten liegt, wohin X zeigt

Manuel: „Das Koordinatensystem, also wo ist X- und Y-Achse, sollte sich drehen lassen. Oder man
macht's so, dass man auf eine Fläche klickt, welche dann sozusagen unten ist, und man da dann
ein Rohteil rausbekommt. Fehlt somit nur noch die X- und Y-Achse – aber das muss sein.“

- **Heute:** Das Teil liegt im Job so, wie es modelliert ist; Z zeigt nach oben im Modell.
- **Soll:** Schritt 1: „Unten liegt:“ eine Fläche anklicken – der Job dreht das Teil so, dass
  sie nach unten zeigt (FreeCADs Job kann das Modell selbst drehen); „X zeigt:“ ↺ 90° / ↻ 90°
  oder eine Kante anklicken, ein Pfeil im 3D zeigt X und Y. Rohteil und Nullpunkt folgen.
- **Fertig, wenn:** Manuels Platte, auf die Seite gelegt, mit einem Klick auf die Fläche wieder
  richtig im Job liegt und sich X um 90° drehen lässt – die Bahnen rechnen in der neuen Lage.
- **Gebaut:** P-2026-10-02-43, 0.99.0 – „Unten liegt“ mit „Fläche anklicken …“ und „X zeigt“
  mit ↺ 90° / ↻ 90°; Rohteil und Nullpunkt folgen.

### 12.7 Materialstand: Jede Schrupp-Operation beginnt, wo noch Material ist (W-012)

Manuel: „Sagen wir mal, wir wollen erst mal ein komplexes Teil durch Anklicken verschiedener
Flächen bearbeiten … Dann muss natürlich vor jeder neuen Schrupp-Aktion auch geschaut werden …
Was muss ich überhaupt machen … Ist überhaupt noch viel Material vorhanden, was ich wegmachen
muss … Als Beispiel ein Klotz 100 × 100, es ist ein Zapfen, der 10 tief ist, bei x25 y25, und
eine Nut, die 15 tief von Oberkante Zapfen ist … bei x −10 y 0 … Dann würde er, wenn ich erst
die Nut anklicke, von z 0 bis z −15 die Nut herstellen … Und wenn ich dann den Zapfen will,
denke ich, dass er die Nut ebenfalls mit bearbeiten würde … Oder andersherum … erst den Zapfen
rausfahren … und wenn ich die Nut anklicke, von z 0 anfangen???“

```
 Schnitt durch Manuels Klotz (Nullpunkt Mitte oben; als Beispiel eine Nut 20 × 60 längs X)

             Nut bei x −10                  Zapfen bei x 25
 z   0 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┌─────────┐ ─ ─ ─ ─   Rohteil oben = Zapfen oben
                                        │ Zapfen  │
 z −10 ────────┐           ┌────────────┘         └──────   Boden um den Zapfen
               │    Nut    │
 z −15         └───────────┘
       x −50                                          x 50
```

- **Heute:**
  - Jede Strategie rechnet vom Rohteil aus: Die Lagen beginnen an seiner Oberkante
    (Starttiefe „OpStockZMax“), die Bahn deckt seinen Umriss ab. Was eine Operation davor schon
    weggenommen hat, weiß sie nicht.
  - **Zapfen zuerst, dann die Nut:** Das Räumen nimmt rundum 0 → −10. Die Nut beginnt trotzdem
    bei z 0: Ihre Helix dreht sich 10 mm durch Luft – mit dem Standardfräser Ø 12 und 3° in der
    Nut 20 gut acht Umläufe, rund 190 mm Weg im Vorschub, ohne einen Span.
  - **Nut zuerst, dann der Zapfen:** Die Nut 0 → −15 ist richtig – das Material muss weg. Das
    Räumen um den Zapfen fährt danach seine Ringe auch über die Nut, wo zwischen z 0 und −10
    nichts mehr ist.
  - Jeder Lauf des Assistenten legt einen **neuen Job** an, auch am selben Teil: Wer erst die
    Nut anlegt und dann den Boden um den Zapfen anklickt, hat zwei Jobs mit je eigenem Rohteil,
    keiner weiß vom anderen. In einem Lauf weiß das Räumen schon ein wenig (eine Tasche unter
    einer Fläche, die es selbst geräumt hat, beginnt an ihrer Oberkante, 0.45.0; die
    Kontur nimmt nur den Rest, den das Planfräsen lässt, P-2026-10-02-17) – über Operationen
    hinweg nichts.
  - FreeCAD 1.1.3 kann es nur für seine eigene „Tasche“ (Haken „UseRestMachining“: Bereiche
    auslassen, die Operationen davor schon geräumt haben; im Wochen-Build auch „Adaptiv“), nicht
    für die Strategien des Addons. Grundsatz 5 und 6 (Abschnitt 5) verlangen es schon: „Keine
    Luftschnitte“, „ein Abtragsmodell je Job: jede Operation weiß, was die vorige ließ“.
- **Soll:**
  - **Der Materialstand vor jeder Bahn:** das Rohteil – der Quader oder der Körper aus dem
    Dokument (W-011 S4; damit ist S4b erledigt) –, abgetragen um jede Operation, die im Job
    davor steht: auch FreeCADs eigene, und die, die im selben Lauf des Assistenten vor ihr
    angelegt werden (Planfräsen vor Räumen vor Nut …). Gerechnet wie die Simulation im
    Prüffenster: ein Höhenfeld, wie hoch das Material an jeder Stelle (Raster 0,5 mm) noch steht
    (`restmaterial.Quader`), darin die Bahnen der Operationen davor abgefahren. Von oben ist das
    genau – ein Fräser, der von oben kommt, lässt nie einen Überhang stehen.
  - **Jede Schrupp-Strategie rechnet darauf** (Räumen, Nut, Planfräsen, Kontur, 3D-Schruppen):
    - Die Lagen beginnen oben am Material ihres Bereichs, nicht am Rohteil – die Nut nach dem
      Zapfen ab z −10, ihre Helix nur noch 5 mm.
    - Lagen und Stücke, in denen nichts mehr steht, fallen weg, oder der Fräser fährt sie im
      Schnellvorschub – was schneller ist (Grundsatz 0). Der Zapfen nach der Nut: über der Nut
      kein Schnitt in Luft.
    - Hinab im Eilgang bis knapp über das Material, nicht nur bis knapp über das Rohteil.
  - **Was noch zu tun ist, steht im Block** – Manuels „Ist überhaupt noch viel Material
    vorhanden“. Steht nichts mehr: „Hier ist nichts mehr zu tun – das hat „Räumen T1“ schon
    weggenommen“, und der Haken geht nicht von selbst an.

    ```
     ☑ Nut   → 1 Lage, … Bögen, etwa … min
             noch 5,6 cm³ – 11,1 cm³ hat „Räumen T1“ schon weggenommen
    ```

  - **Ändert sich eine Operation davor** (Tiefe, Fräser, gelöscht, verschoben), rechnen die
    danach von selbst neu – sonst stimmte ihr Materialstand nicht mehr, und im schlimmsten Fall
    führe der Eilgang dorthin, wo jetzt doch Material steht. Das gilt auch, wenn man die
    Operation in FreeCADs eigenem Dialog ändert.
- **Frage 1 – ein zweiter Lauf am selben Teil.** Damit die Nut vom Räumen weiß, müssen beide im
  selben Job stehen. Am Klotz liegt schon „Räumen T1“; jetzt klickst du den Grund der Nut an,
  „Bearbeitung“:
  - **(a) Empfehlung – derselbe Job:** Hat das Teil schon einen Job, kommen die neuen
    Operationen dort hinein, hinter die vorhandenen. Schritt 1 zeigt Maschine, Rohteil und
    Nullpunkt des Jobs grau (nur zum Lesen), „Weiter“ geht gleich zu Schritt 2. Für eine zweite
    Aufspannung (das Teil umgedreht) oben der Knopf „Neuer Job …“. Hat das Teil mehrere Jobs:
    der, dessen Teil man angeklickt hat (jeder Job hat sein eigenes im Bild), sonst der zuletzt
    angelegte.
  - **(b) Jedes Mal fragen:** „Der Klotz hat schon den Job „Job“ (1 Operation) – dazu oder ein
    neuer Job?“ Eine Frage mehr bei jedem Klick.
  - **(c) Wie heute:** jeder Lauf ein neuer Job. Der Materialstand gilt dann nur für die
    Operationen eines Laufs – man muss alle Flächen auf einmal anklicken.
  - **Entschieden** (Manuel, 2026-10-02: „Frage 1. A“): **(a)** – derselbe Job, Schritt 1 grau,
    „Neuer Job …“ für eine zweite Aufspannung.

    ```
     Schritt 1 von 3 – Aufspannung                         (a), das Teil hat schon einen Job
     In den Job „Job“ – 1 Operation: Räumen T1                       [Neuer Job …]
     Maschine   3-Achs-Fräse                       (grau)
     Rohteil    Quader 102 × 102 × 31              (grau)
     Nullpunkt  Mitte oben                         (grau)
                                                   [Abbrechen]  [Weiter →]
    ```

- **Schritte** (je ein Patch):
  - **M1 Die Nut beginnt, wo noch Material ist:** der Materialstand (`materialstand.py`, mit dem
    Körper als Rohteil sein Höhenfeld), die Nut rechnet darauf, im Block „noch … cm³“; ändert
    sich eine Operation davor, rechnen die danach neu. Prüfung: Manuels Klotz, Zapfen und Nut in
    einem Lauf – die Nut beginnt bei z −10.
    **Gebaut:** P-2026-10-02-64, 0.115.0 – `materialstand.fuer(job, vor, dazu)`: das Höhenfeld
    im Raster 0,5 mm, die Operationen davor (auch FreeCADs, Bohrzyklen) und die Vorschauen der
    angehakten Blöcke davor im selben Lauf; der Fräser um den Saum der Schritte breiter (sonst
    stünden auf der Wand einer fertigen Nut Zellen bis oben). Die Nut nimmt je Nut das höchste
    Material im Langloch (offen: dazu der Weg vor dem offenen Ende), Lagen und Helix beginnen
    dort; steht nichts mehr: „Hier ist nichts mehr zu tun – das hat „…“ schon weggenommen.“ Sie
    merkt sich die Kennung (Eigenschaft „Materialstand“); `gui_materialstand` rechnet sie neu,
    wenn sich davor eine Bahn oder die Folge ändert. „Anlegen“ rechnet jede Operation gleich
    nach dem Anlegen, damit die nächste ihre Bahn sieht. Manuels Klotz: Räumen 3,6 s,
    Materialstand 0,25 s; Nut ab −10 (`test_materialstand`, `szenario_materialstand`).
  - **M2 Zweiter Lauf am selben Teil** nach Frage 1.
    **Gebaut:** P-2026-10-02-66, 0.116.0 – `vorhandener_job`: der Job, dessen Modell-Klon man
    angeklickt hat, sonst der zuletzt angelegte mit dem Teil (nicht einer mit Stange). Schritt 1
    zeigt „In den Job „…“ – 1 Operation: …“ mit „Neuer Job …“; Maschine, Rohteil, Nullpunkt und
    Lage wie beim Ändern grau (`_aufspannung_zeigen`, `_aufspannung_fest`). „Anlegen“ hängt die
    Operationen an, nimmt im vorhandenen Job keine fremden Controller heraus; „Abbrechen“ lässt
    ihn, wie er war. „Neuer Job …“ schließt und öffnet den Assistenten mit einem neuen Job
    (`szenario_zweiter_lauf`).
  - **M3 Das Räumen rechnet darauf:** Lagen und Ringe nur, wo Material steht. Prüfung: Nut
    zuerst, dann der Zapfen – über der Nut kein Schnitt in Luft.
    **Gebaut:** P-2026-10-02-68, 0.118.0 – `raeumen_bahn.planen(…, stand)`: Je Lage ist Rohteil
    nur, was über ihr steht; die Ringe (vom Rohteil her, um die Inseln) fahren nur, wo ihre
    Stirn Material trifft, das sie dort wegnehmen kann (eine Zelle weniger weit als die Stirn
    vom Erlaubten, wie im 3D-Schruppen); eine Lage ohne solches fällt aus; die Lagen beginnen
    am höchsten Material, das der Fräser erreicht. Über eine Lücke im Weggefrästen bis 2 D
    (mindestens 20 mm) fährt der Ring im Vorschub hinweg – Abheben und wieder Einfahren dauert
    länger (an Manuels Klotz, Nut zuerst, 25-mal: eine Minute mehr); erst eine längere hebt er
    ab. Der Eilgang hinab endet über dem höchsten Material unter der Stirn. Steht im Bereich
    über allen Lagen noch das volle Rohteil, rechnet es wie bisher; der Morph fällt mit
    Materialstand aus (er fährt ganze Ringe, auch durch Weggefrästes). Unter dem Ergebnis grau
    „noch … – … hat „…“ schon weggenommen“ (dort, wohin die Stirn auf der Fläche kommt); steht
    nichts mehr: „Hier ist nichts mehr zu tun – das hat „…“ schon weggenommen.“ Es merkt sich
    die Kennung wie die Nut; `gui_materialstand` rechnet es neu. Manuels Klotz, Nut zuerst:
    8,42 statt 8,48 min, „11,3 cm³ hat „Nut T1“ schon weggenommen“; ein Guss als Rohteil, der
    nur am Zapfen 1 mm Rand hat, mit 4 mm je Lage: 3 Ringe um den Zapfen, 0,56 statt 25 min
    (`test_materialstand`, `szenario_raeumen_materialstand`). Das Planfräsen kennt den
    Materialstand noch nicht (M4) – im Wettbewerb rechnet es mit dem vollen Rohteil.
  - **M4 Planfräsen, Kontur, 3D-Schruppen** ebenso.
    **Gebaut, die Ziel-Zeile:** P-2026-10-02-69, 0.118.1 – „Weg müssen … cm³“, die Zielzeit, der
    Vergleich mit der Werkzeugkiste, „× Ziel“ und die Wahl des Planen-Einsatzes rechnen mit dem,
    was nach den Operationen im Job noch steht (`zielzeit.Material.unter`, beim Ändern vor der
    Operation). Manuels Klotz, Nut zuerst: beim Boden um den Zapfen rund 18 cm³ weniger als
    vorher – die Nut (`test_zielzeit`, `szenario_raeumen_materialstand`).
    **Gebaut, das Planfräsen:** P-2026-10-02-70, 0.119.0 – `planfraesen_bahn.planen(…, stand)`:
    Die Lagen beginnen am höchsten Material, das die Zeilen erreichen (auf der obersten Lage
    dürfen sie am weitesten); je Lage fährt eine Zeile nur, wo ihre Stirn (eine Zelle kleiner)
    Material über der Lage trifft, über Lücken bis 2 D im Vorschub. Steht unter der Mitte der
    Stirn nichts (nur am Rand höchstens der Streifen ae), taucht sie senkrecht ein wie neben der
    vorigen Zeile – sonst über die Rampe; der Eilgang hinab endet über dem höchsten Material unter
    der Stirn (fuhr die Lage davor dort, höchstens auf ihr). Steht im Bereich noch das volle
    Rohteil, rechnet es wie bisher. „noch … – … schon weggenommen“, „nichts mehr zu tun“, Kennung
    und Nachrechnen wie das Räumen; im Assistenten mit Materialstand, auch in der Folge mit dem
    Räumen und im Wettbewerb. Manuels Klotz nach dem Räumen: „nichts mehr zu tun“; der Guss mit
    1 mm Rand am Zapfen, 4 mm je Lage: 2,4 statt 33 min (zuerst 8 min – jedes Stück am Zapfen fuhr
    über eine Rampe von 38 mm ein; `test_materialstand`, `szenario_raeumen_materialstand`). Wer
    „nichts mehr zu tun“ sagt (`materialstand.SchonWeg`), verliert im Assistenten den Haken,
    solange ihn niemand von Hand gesetzt hat.
    **Gebaut, das 3D-Schruppen:** P-2026-10-02-71, 0.120.0 – `schruppen3d_bahn.planen(…,
    stand)`: Das Raster der Höhen beginnt mit dem Materialstand; zeigt er nicht überall das volle
    Rohteil, räumt jede Lage wie beim Restschruppen nur, wo Material steht, das der Fräser
    erreicht (die Varianten fallen weg), und die Lagen beginnen am höchsten solchen Material.
    „noch“ zählt über dem Teil, nicht über seinem tiefsten Punkt. Zweimal 3D-Schruppen an der
    Kuppel: das zweite 0,14 statt 4,99 min – nur die Treppe (`test_materialstand`,
    `szenario_mulde`).
    **Gebaut, die Kontur:** P-2026-10-02-72, 0.121.0 – `kontur_bahn.planen(…, stand)`: Zeigt der
    Materialstand dort, wohin die Stirn kommt, nicht überall das ganze Rohteil, fährt jede
    Schruppbahn je Lage nur, wo ihre Stirn eine Zelle kleiner Material über der Lage trifft – so
    zählen weder die Wand noch das Aufmaß an ihr, das eine Operation davor ließ –, über Lücken bis
    2 D im Vorschub; die Lagen beginnen am höchsten solchen Material; steht beim Eintauchen unter
    der Stirn nichts, geht es senkrecht hinab statt über die Rampe. Das Schlichten fährt immer (das
    Aufmaß ist schmaler als das Raster), ab dem höchsten Material an der Wand. „noch“ zählt über
    dem Teil; ohne Schlichten und ohne Material „nichts mehr zu tun“. Das Restmaterial rechnet
    ohne Materialstand – seine Ecken sind oft kleiner als das Raster. Manuels Klotz nach dem
    Räumen: nur noch das Schlichten, 0,18 statt 12,8 min, „noch 0,3 cm³“ (das Aufmaß); der Guss
    mit 1 mm Rand am Zapfen: 0,72 statt 38 min (`test_materialstand`,
    `szenario_kontur_materialstand`). Grenze: Ein Rand, kaum breiter als das Aufmaß plus eine
    Zelle, ist für die Schruppbahnen unsichtbar – dafür fährt die Kontur seit P-2026-10-02-75
    (0.122.0, Frage 4) mit Materialstand einmal beim Aufmaß an der Wand ab, über die ganze Höhe,
    dann schlichtet sie: am Klotz nach dem Räumen 0,36 statt 12,8 min, 2 Bahnen; ohne Schlichten
    bleibt dieser eine Zug; der Guss 0,91 statt 38 min. Seit P-2026-10-02-84 (0.125.2) entfällt
    der Zug, wenn die Kontur selbst in einer einzigen Lage geschruppt und dabei den innersten
    Versatz ganz gefahren hat (und die Schneide über die Höhe reicht): Er wäre dieselbe Bahn noch
    einmal – eine Runde Luft (B-012; `szenario_kontur` schlug seit -75 deshalb fehl: 5 Lagen und
    10 Bahnen statt 4 und 9).
- **Fertig, wenn:** Manuels Klotz in beiden Reihenfolgen im Prüffenster ein Teil ohne Rest
  ergibt, keine Operation dort in Luft schneidet, wo eine davor schon war (außer über eine
  kurze Lücke, wo Durchfahren schneller ist als Abheben – Grundsatz 0), und die Nut nach dem
  Zapfen bei z −10 beginnt.
  **Geprüft** (P-2026-10-02-73): Zapfen zuerst – die Nut beginnt bei −10; Nut zuerst – das
  Räumen kreuzt sie nur über kurze Lücken, ein zweites Räumen und das Planfräsen danach haben
  nichts mehr zu tun (`test_materialstand`, `szenario_raeumen_materialstand`). Räumen, dann die
  Kontur am Zapfen in einem zweiten Lauf – sie schlichtet nur noch –: im Prüffenster „Am Ende
  bleiben 0,00 mm … nirgends ins Teil“ (`szenario_kontur_materialstand`; oben auf dem Zapfen
  1 mm Rohteil – seine Oberseite war nicht gewählt).
- **Zur Besprechung** (gebaut ist je die Empfehlung; Manuel, 2026-10-02: „Fragen kann ich erst
  morgen früh oder heute Abend alle beantworten“) – **beantwortet** (Manuel, 2026-10-02):
  Frage 3 (a) „Frage hätte sich erübrigt, wenn man ‚schneller gewinnt‘ durchziehen würde“ –
  künftig entscheidet die Zeit (durchfahren oder abheben, was schneller ist), ohne Frage.
  Frage 4 – nicht (a): „wenn's heißt 0,3 ist Schlichtaufmaß .. fahr die Kontur zumindest einmal
  auf 0,3 einfach an der Kontur ab, dann ist die Frage auch hinfällig“. Frage 5 – so lassen:
  „wenn ein Konstrukteur in einer Tasche keine Rundungen reinkonstruiert ... dann ist das sein
  Pech ... natürlich muss man in einer Tasche einfach die Rundung des Fräsers zulassen ...
  wenn wir zu 5-Achs-Strategien und Ausweichfräsen kommen ... dann können wir über einen Weg
  reden“.
  - **Frage 3 – eine kurze Lücke im Weggefrästen.** Räumen, Planfräsen und Kontur fahren über
    eine Stelle, an der eine Operation davor schon alles weggenommen hat (Manuels Nut quer unter
    den Ringen des Räumens).
    - **(a) Empfehlung – im Vorschub durchfahren,** wenn die Lücke höchstens 2 D lang ist
      (mindestens 20 mm): Abheben, hinüber und wieder Eintauchen dauert länger. An Manuels Klotz,
      Nut zuerst: 25 Ringe kreuzen die Nut – durchfahren 8,42 min, abheben gut eine Minute mehr.
    - **(b) Immer abheben:** nie ein Schnitt in Luft, aber langsamer.
    - **(c) Eine andere Länge:** zum Beispiel 1 D oder 50 mm.
  - **Frage 4 – ein schmaler Rand an der Wand.** Der Materialstand rechnet in Zellen von
    0,5 mm. Ein Rand an einer Wand, kaum breiter als das Aufmaß plus eine Zelle (ein Guss mit
    0,7 mm Rand bei Aufmaß 0,3), ist für die Schruppbahnen der Kontur unsichtbar – dann nimmt
    ihn das Schlichten ganz, 0,7 mm statt 0,3.
    - **(a) Empfehlung – so lassen:** Das Schlichten verträgt das; die Schruppbahnen fahren nur,
      wo sicher Material steht.
    - **(b) Die innerste Schruppbahn immer fahren,** wenn an der Wand Material steht: das
      Schlichten nie mehr als das Aufmaß, dafür eine Bahn je Lage oft durch Luft.
  - **Frage 5 – das Restmaterial.** Die Kontur mit dem kleineren Fräser in den Ecken rechnet
    weiter ohne Materialstand.
    - **(a) Empfehlung – so lassen:** Die Ecken sind oft kleiner als eine Zelle; mit
      Materialstand bliebe dort Rest stehen.
    - **(b) Mit Materialstand in feinerem Raster (0,25 mm)** nur für das Restmaterial: rechnet
      etwa viermal so lange.

### 12.8 Eintauchen in die geschlossene Nut: an einer wählbaren Stelle

Manuel: „Und in so eine geschlossene Nut einzutauchen … ist auch wichtig … dass das helikal
geht … und an einer von mir aus wählbaren Position in der Nut … aber natürlich mit Vorschlag …“

- **Heute** (seit 0.108.0, 12.2): Die geschlossene Nut taucht schon helikal ein – je Lage eine
  Helix am einen Ende (Radius r − R − Aufmaß, Steigung aus dem Eintauchwinkel des Fräsers, beim
  Standardfräser 3°), unten einmal rundum, dann die Bögen bis ans andere Ende; die nächste Lage
  taucht dort ein, wo die vorige aufhörte. Wählen lässt sich die Stelle nicht: Es ist das Ende,
  an dem die Nut beginnt. Die Vollnut (kaum breiter als der Fräser) hat für eine Helix keinen
  Platz; sie geht mit der Zickzack-Rampe längs der Nut hinab.
- **Soll:**
  - **Vorschlag:** wo über dem Grund am wenigsten Material steht (Materialstand, 12.7) – kreuzt
    eine Bohrung oder Tasche die Nut, dort hinab, die Helix nur, wo Material ist; steht überall
    gleich viel, das Ende, das der Fräser von der Operation davor am schnellsten erreicht. Der
    Grund steht grau daneben.
  - **Gewählt** gilt die Stelle für jede Lage – wer sie wählt, hat einen Grund (vorgebohrt, eine
    dünne Wand am Ende). Liegt sie nicht an einem Ende, laufen die Bögen von ihr zum einen Ende,
    im Schnellvorschub zurück durch die freie Nut und dann zum anderen. In der Vollnut beginnt
    die Zickzack-Rampe an der gewählten Stelle.
  - Die Helix sieht man in der Vorschau der Bahn im Bild.
- **Frage 2 – wie wählt man die Stelle?**
  - **(a) Empfehlung – Liste und Anklicken:** im Block „Nut“ die Zeile „Eintauchen bei“ mit
    [Vorschlag · Ende X −30 Y 0 · Ende X 10 Y 0 · Mitte X −10 Y 0 · angeklickte Stelle] und dem
    Knopf „Im Bild wählen …“: einen Punkt auf dem Grund der Nut anklicken – die Helix rückt
    dorthin (so weit, dass sie in die Nut passt). Die Stellen mit ihren Koordinaten am
    Nullpunkt, wie an der Maschine. Mehrere Nuten: je Nut eine Zeile.
  - **(b) Nur Anklicken:** kein Feld; der Vorschlag steht grau da, ändern geht nur im Bild.
    Weniger im Fenster – aber welche Stelle gilt, sieht man nur in der Ansicht.
  - **(c) Abstand vom Ende in mm:** ein Zahlenfeld. Genau, aber man muss rechnen, und welches
    Ende gemeint ist, sieht man nicht.
  - **Entschieden** (Manuel, 2026-10-02: „Frage 2 a“): **(a)** – Liste und Anklicken.

    ```
     Nut   Fräser [T1 VHM 12 ▾]   Einsatz [Dynamisch ▾]
           Zustellung 25 · Zeilenabstand 1,5 · Aufmaß 0,3
           Eintauchen bei [Vorschlag: Ende X −30 Y 0 ▾]   [Im Bild wählen …]
                          grau: „von der Operation davor am schnellsten erreicht“
    ```

- **Schritt E1** (ein Patch, nach M1): die Stelle nach Frage 2, der Vorschlag mit dem
  Materialstand.
  **Gebaut:** P-2026-10-02-67, 0.117.0 – im Block „Nut“ je geschlossener Nut „Eintauchen bei“:
  Vorschlag, Ende, Ende, Mitte (mit ihren Koordinaten), „angeklickt“; „Im Bild wählen …“ nimmt den
  nächsten Klick in die Nut, die Stelle der Mittellinie daneben. Eine gewählte Stelle gilt für
  jede Lage (`nut_bahn._lagen_bei`: Helix um P, Bögen nach B, im Schnellvorschub zurück, Bögen
  nach A). Der Vorschlag (`vorschlag_bei`): längs der Mittellinie das Material im Kreis des
  Fräsers über dem Grund – liegt eine Stelle unter 80 % der Enden (eine Bohrung, eine Tasche),
  dort; sonst wie bisher abwechselnd an den Enden. Im Kreis der ganzen Helix fiel eine Bohrung
  Ø 10 unter dem Ø 12 nicht ins Gewicht (gefunden im Test). Die Operation merkt sich die Stellen
  („Eintauchstellen“, je Nut der Name ihrer ersten Wand und der Anteil). Die Vollnut beginnt ihre
  Rampe am Ende, das der Stelle am nächsten liegt (`test_nut`, `szenario_nut_eintauchen`).
- **Fertig, wenn:** In Manuels Klotz die Helix der Nut an einer angeklickten Stelle in der Mitte
  eintaucht, in jeder Lage dort, und die Nut im Prüffenster ohne Rest fertig ist.

## 13. Manuels Testteil für die 3-Achs-Fräse (W-013, 2026-10-02)

Manuel: „dies ist ein testteil .. für fräsmaschinen ... 3 achs... das muss sinnvoll bearbeitet
werden auch mit mehreren arbeitsschritten“ – `beispiele/testteil_3achs_fraese.FCStd`. Das Teil
ist ab jetzt der Maßstab für den ganzen Weg im Assistenten „Bearbeitung“: nicht eine Strategie
allein, sondern die Folge.

### 13.1 Das Teil

Ein PartDesign-Körper, 100 × 100 × 32:

- die **Platte** 100 × 100 × 10 (Oberseite z 10, 65 cm²);
- darauf die **Insel**, 12 hoch (z 10 … 22, 22,5 cm² oben): ein Umriss aus vier Geraden und drei
  Bögen – außen R 12 und R 21,5, innen R 16,4 –, etwa von x −33 bis 37 und y −30 bis 32,5;
- auf der Insel hinten links die **obere Stufe**, 10 hoch (z 22 … 32, 5,4 cm² oben); links und
  hinten gehen ihre Wände mit denen der Insel 22 hoch durch;
- in der oberen Stufe eine **dreieckige Tasche**, 5 tief (Boden z 27, 1,7 cm²), eine Ecke R 6,
  zwei spitz; zwischen Tasche und Außenwand bleiben an zwei Stellen nur 1,4 und 1,7 mm;
- in der Insel eine **Kugelmulde** Ø 25, 12,5 tief (FreeCAD führt sie als Torus mit R 0,01).

```
 y  50 ┌───────────────────────────────────────────────┐
       │                 Platte  z 10                  │
  32,5 │      ┌──────────────┬───────────╮             │
       │      │ obere Stufe ╱             ╲  innen     │
       │      │ z 32  ◣    ╱    Insel      ╲  R 16     │
       │      │  Tasche   ╱     z 22        │          │
    10 │      ├────────╮_╱                  │ R 21,5   │
       │      │        ╭───────╮            │          │
     0 │      │        │ Mulde │           ╱           │
       │       ╲       ╰─Ø 25──╯         ╱             │
   −28 │         ╲___R 12_____________╱                │
   −50 └───────────────────────────────────────────────┘
      x −50   −33        0      12        37          50
```

### 13.2 So würde man es fräsen

Rohteil 102 × 102 × 34 (1 mm rundum, die Vorgabe des Assistenten), Nullpunkt Mitte oben; aus der
Werkzeugkiste der Szenarien: T1 VHM Ø 12 (ae 1,5, ap 25), T3 VHM Ø 6, T5 Kugel Ø 8, T6 Fase 90°.

1. **Außen um die Insel** bis auf die Platte: schruppen, 23 tief in einer Lage (ap 25, Schneide
   26), von außen kreisend bis an den Umriss, Aufmaß 0,3 – das meiste Volumen (150 von 199 cm³).
2. **Die Insel oben** (z 22): schruppen, 11 tief, vom Umriss der Insel nach innen bis an die obere
   Stufe; über der Mulde gleich mit.
3. **Die obere Stufe oben** (z 32): 1 mm plan – nur über ihr, nicht über dem ganzen Rohteil.
4. **Die Tasche:** mit einem Fräser, der hineinpasst (Ø 6) – räumen, dann die Wand schlichten.
5. **Die Mulde:** 3D-Schruppen mit dem Ø 12, 3D-Schlichten mit der Kugel.
6. **Wände schlichten:** der Umriss der Insel, die obere Stufe.
7. **Kanten entgraten.**

Die Zielzeit des Schruppens mit dem Ø 12 (Abschnitt 12.3): **8 min** – 199 cm³, im Mittel
18,4 mm tief.

### 13.3 Was der Assistent daraus macht (gemessen, 0.123.0, FreeCAD 1.1.4)

Alle Flächen angeklickt – die vier ebenen, die Mulde, alle Wände:

| Operation | Zeit | Befund |
| --- | ---: | --- |
| Räumen T1 (3 Flächen) | 26,3 min · 3,4 × Ziel | 60-mal abgehoben, 14 % des Vorschubwegs in der Luft, Last bis 3,9 ae |
| Kontur T1 (3 Konturen) | 0,7 min | fährt auch in die Tasche, die niemand geräumt hat |
| 3D-Schruppen T1 | 0,7 min | 11-mal abgehoben |
| 3D-Schlichten T5 | 1,6 min | – |
| **zusammen** | **29,3 min** | im Prüffenster „0,00 … 12,00 mm“; in den spitzen Ecken der Tasche bleiben 5 mm |

Wo die 26 min des Räumens bleiben – jede Fläche für sich, vom Rohteil her:

| Fläche | Zeit | Was dort geschieht |
| --- | ---: | --- |
| obere Stufe oben (z 32) | 9,5 min | 1 mm über das **ganze** Rohteil, mit ae 1,5 |
| Insel oben (z 22) | 9,8 min | 11 mm über alles außerhalb der oberen Stufe – auch außen, wo danach noch 12 mm tiefer gefräst wird |
| Platte (z 10) | 7,2 min | außen um die Insel, 23 mm – der einzige Schritt, der so nötig ist |
| Taschenboden (z 27) | 10,7 min | B-006: 43 Ringe und 29 Rampen rund um die Insel statt in der Tasche (in den 26 min nicht mehr enthalten) |

### 13.4 Befunde

- **B-006 Die Tasche räumt außerhalb ihrer Wände.** In einer Tasche gilt als erlaubt, wo das
  Teil nicht höher liegt als die Lage – auch neben der Insel, auf der die Tasche sitzt.
  *Soll:* nur in ihrer Kontur. *Fertig, wenn:* der Taschenboden am Testteil allein nicht mehr um
  die Insel fährt. **Behoben:** P-2026-10-02-79, 0.123.1 – in einer Tasche sind nur die Knoten
  in ihrer Kontur erlaubt (`raeumen_bahn._im_vieleck`). Am Testteil sagt das Räumen des
  Taschenbodens mit dem Ø 12 jetzt, dass der Fräser nicht hineinpasst (weiter mit B-007); über
  die vier Flächen 26 statt 37 min.
- **B-007 Eine Tasche, in die der Fräser nicht passt, fällt still aus.** Der Ø 12 passt mit
  Aufmaß nicht in die dreieckige Tasche; das Räumen lässt sie aus und sagt „3 Flächen“. Die
  Kontur nimmt an, das Räumen habe sie geräumt („nur das Aufmaß an den Wänden: die Tasche räumt
  das Räumen“), und fährt dort ins Volle; in den spitzen Ecken bleibt Material. *Soll:* Der
  Assistent sagt, welche Fläche der Fräser nicht kann, und schlägt dafür den größten Fräser der
  Werkzeugkiste vor, der hineinpasst – als eigene Operation danach (Schritt T3 unten).
  **Zur Hälfte behoben:** P-2026-10-02-81, 0.124.1 – das Räumen nennt die Tasche
  (`Raeumbahn.ausgelassen`; im Fenster „… In die Tasche Face26 passt der Ø 12 nicht – sie
  bleibt stehen.“), und die Kontur behauptet nicht mehr, das Räumen habe sie geräumt: Sie sieht
  im Materialstand selbst nach und fährt an den geräumten Wänden einmal beim Aufmaß ab, dann das
  Schlichten. Nachgemessen: „Ins Volle“ fuhr sie auch vorher nicht – ihr Schlichtgang geht in
  der Tasche über die Rampe hinab (3°), das begrenzt den Querschnitt. Offen bleibt T3: der
  kleinere Fräser für die Tasche.
- **B-008 Prüffenster: 12 mm „Rest“ auf einer Linie in der Mulde.** Die Naht der Mulde liegt
  genau auf einer Zeile des Rasters (y 0); ein Knoten genau auf einer Kante des Netzes zählt
  nicht, also sieht der Vergleich dort bis auf die Unterseite des Teils. Gefräst ist die Mulde
  richtig (auf 0,02 mm). *Soll:* Ein Knoten auf einer Kante zählt, wenn beide Seiten dieselbe
  Höhe haben.
  **Behoben:** P-2026-10-02-86, 0.125.3 – nachgemessen war es nicht die Naht: zwei einzelne
  Zellen, deren Mitte 0,007 und 0,0001 mm neben einer Wand liegt, zählten mit der ganzen
  Wandhöhe. So dicht an einer Kante darf es jetzt bis zur höheren Fläche stehen
  (`restmaterial.teilhoehen_kanten`). Am Testteil bleiben 5 mm in den zwei spitzen Ecken der Tasche.
- **B-009 „… hat „Planfräsen“ schon weggenommen“**, obwohl Räumen angehakt ist: Die Zeile unter
  „3D-Schruppen“ stammt aus dem Wettbewerb und wird nicht neu gerechnet, wenn der Haken wechselt.

  **Behoben:** P-2026-10-02-87, 0.125.4 – nach dem Wettbewerb rechnet jeder Block neu, dessen
  Materialstand sich geändert hat (`_block_rechnen`).

- **B-010 Die Kontur fährt an der Stufenwand Rampen statt eines Bogens.** Beim Ansehen der
  Bahn (2026-10-03, Nacht): Die Stufenwand bei z 22 bekam drei Läufe mit je 194 mm Rampe (3°,
  hin und her längs der 54-mm-Wand) statt des tangentialen Bogens aus der Luft – 1,77 min für
  die Kontur. Zwei Ursachen: (1) Die Höhe einer Wand galt für ihre ganze Unterkante
  (`Kontur.z_oben` = die höchste Wand der Kette; die Rückwand des Testteils ist eine Fläche,
  über der Insel 22, unter der Stufe 32) – neben der Inselkante schien überall eine 32 hohe Wand
  zu stehen; (2) das Ein- und Ausfahren musste zu jeder Wand mehr Abstand halten als die Bahn an
  ihrem Ende selbst hat (der Versatz einer offenen Wand liegt an der Ecke zur nächsten Wand ein
  paar Hundertstel näher). **Behoben:** P-2026-10-03-34 – die Höhe je Stelle der Unterkante
  (`_wandkanten`: eine senkrechte Gerade durch die Wand, in Stücke gleicher Höhe geteilt;
  `Kontur.wandkanten`), und der Abstand des Einfahrens höchstens der Abstand der Bahnenden
  (`_lauf`). Kontur am Testteil 1,07 statt 1,77 min, die Stufenwand aus der Luft mit Bogen.
  Nach dem Räumen fährt die Kontur jede Wand zweimal – einmal „beim Aufmaß“, dann das
  Schlichten; die erste Runde nimmt dort nichts (Insel: 290 mm, Stufe: 92 mm). **So gewollt**
  (nachgelesen 2026-10-04 nachts): Manuel wollte die Runde ausdrücklich („fahr die Kontur
  zumindest einmal auf 0,3 einfach an der Kontur ab“, `kontur_bahn`, Kopf) – einen Rand
  schmaler als das Raster sieht der Materialstand nicht; so nimmt das Schlichten nie mehr als
  das Aufmaß. Bleibt.

### 13.5 Schritte (je ein Patch)

- **T1 Räumen über mehrere Höhen: die tiefste Fläche zuerst, jede Stelle einmal.** Heute räumt
  jede Fläche von oben her alles, was über ihr steht – auch dort, wo eine tiefere Fläche danach
  noch einmal hinfährt. *Soll:* die tiefste Fläche zuerst, in so wenigen Lagen, wie Zustellung
  und Schneide erlauben; jede höhere danach nur, wo noch Material steht (der Materialstand der
  Flächen davor, in derselben Bahn), in Ringen vom Rand dessen her, was noch steht – außen in
  der Luft beginnend, wie am Rohteil. *Fertig, wenn:* das Räumen der vier Höhen am Testteil
  höchstens 1,5 × Ziel braucht (12 min statt 26), ohne Rest und ohne Schnitt ins Teil.
  **Gebaut:** P-2026-10-02-80, 0.124.0.
  - `raeumen_bahn.planen`: die offenen Flächen von unten nach oben, danach die Taschen von oben
    nach unten (eine Tasche in einer Fläche beginnt an ihrer Oberkante, wie bisher – vor der
    Fläche um sie begänne sie am Rohteil, in mehr Lagen, und die Ringe der Fläche rissen über
    dem Loch ab).
  - `_Material`: das Rohteil (oder der Stand vor der Operation) als Höhenfeld, abgetragen um
    jede Fläche, sobald sie geplant ist; die nächste rechnet darauf wie auf dem Materialstand
    von W-012 – Lagen ab dem höchsten Material, Ringe nur, wo ihre Stirn Material trifft.
  - `_Feld._tiefe_vom_material`: Die Ringe „vom Rohteil her“ beginnen am Rand dessen, was noch
    steht – der erste R − ae daneben in der Luft –, wenn der Fräser dorthin von außen durch die
    Luft kommt. Ein Loch im Material (eine schon gefräste Nut) beginnt keine Ringe; steht das
    Rohteil noch ganz, bleibt es beim Rechteck mit Bögen.
  - Am Testteil: **12,4 statt 26,3 min** (1,59 × Ziel), 3 Lagen, 75 Ringe – außen um die Insel
    6,2 m Vorschub in einer Lage 23 tief, die Insel oben 2,6 m (vorher 8,8), die obere Stufe 1,0 m
    (vorher 8,5); der ganze Job 15 statt 29 min. Im Quader ohne Rest, nirgends ins Teil
    (`tests/test_testteil.py`, `tests/test_raeumen.py` (f), `szenario_testteil`).
  - **Noch nicht erreicht:** die 1,5 × Ziel. Es fehlen die dünne Lage oben (T2: 1,1 min für
    1 mm) und T1b.
- **T1b Ringe, die nichts mehr schneiden, fallen weg.** Die Ringe vom Rand her laufen weiter,
  bis die Mitte des Fräsers die Mitte des Materials erreicht – die letzten drei, vier schneiden
  nichts mehr, weil der Ring davor mit dem Radius schon alles genommen hat (am Klotz und am
  Testteil die grauen Ringe in der Mitte). *Fertig, wenn:* kein Ring ganz in der Luft fährt.
  **Gebaut:** P-2026-10-02-88, 0.125.5 – ein Ring fährt nur, wenn seine Stirn noch Rohteil trifft
  (`_Lage._schneidet`). Streifen 100 × 20: 8 statt 11 Ringe, 2,18 statt 2,78 min; am Testteil
  12,38 statt 12,45 min.
- **T2 Die dünne Lage oben mit dem Einsatz „Planen“.** **Gebaut:** P-2026-10-02-93, 0.128.0 –
  ohne den Einsatz: Eine Lage bis 0,1 D (bahn.DUENN) nimmt das Räumen mit ae = R und dem
  Vorschubanteil, bei dem der Span so dick bleibt wie mit dem ae des Einsatzes
  (`bahn.spanausgleich`, Ø 12 mit ae 1,5: 0,66 – der Einsatz „Planen“ des Standardfräsers fährt
  0,70). Das geht ohne neue Eigenschaft an der Operation und für jeden Fräser. Die Zielzeit
  rechnet dünne Stellen genauso (`zielzeit.ziel`), die Last misst sie gegen ihr ae
  (`Raeumbahn.breit`). Block 60 × 40, 1 mm: 1,0 statt 2,7 min; Testteil: 10,3 statt 10,7 min.
  1 mm Tiefe mit ae 1,5 ist verschenkt: Hat
  der Fräser einen Einsatz für kleine Tiefen (der Ø 12: ae 8,4 bis ap 1,2), nimmt eine Lage, die
  so dünn ist, dessen Zeilenabstand. *Fertig, wenn:* die obere Stufe oben in unter 0,3 min plan
  ist.
- **T3 Was der Fräser nicht kann, bekommt der nächste** (B-007): je Fläche und Kontur der
  größte Fräser, der hineinpasst; der Assistent legt dafür eigene Operationen an und sagt es in
  einem Satz. *Fertig, wenn:* die Tasche am Testteil mit dem Ø 6 geräumt und geschlichtet ist
  und die Kontur des Ø 12 nicht mehr hineinfährt.
  **Gebaut:** P-2026-10-02-82, 0.125.0 – ein neuer Block „Rest räumen“ gleich unter „Räumen“:

  ```
   ☑ Räumen        → 3 Flächen: 3 Lagen, 75 Ringe, etwa 12 min · 1,59 × Ziel …
                     In die Tasche Face26 passt der Ø 12 nicht – die räumt „Rest räumen“ mit T3.
   ☑ Rest räumen   → 1 Lage, 2 Ringe, etwa 1 min
   ☑ Kontur        → 3 Konturen: 3 Lagen, 3 Bahnen, etwa 1 min – nur das Aufmaß an den Wänden …
   ☑ Restmaterial  → 1 Stelle, 1 Lage, etwa 1 min
  ```

  - Er wird möglich, wenn das Räumen eine Tasche auslässt und ein kleinerer Fräser der
    Werkzeugverwaltung hineinpasst; vorgewählt ist der größte, der passt (mit der Vorschau
    probiert, vom größten her), der Haken ist gesetzt, solange ihn niemand von Hand wegnimmt.
    Sonst steht er unter „Passt nicht zur Auswahl“.
  - Er räumt nur die ausgelassenen Taschen, auf dem Materialstand nach dem Räumen, und wird eine
    eigene Operation gleich danach („Räumen T3“).
  - Fährt die Kontur die Wände einer solchen Tasche, bekommt „Restmaterial“ den Haken dazu – der
    Fräser der Kontur kommt dort nicht überall hin.
  - Am Testteil: sechs Arbeitsschritte mit drei Werkzeugen – Räumen T1, Räumen T3, Kontur T1,
    Restmaterial T3, 3D-Schruppen T1, 3D-Schlichten T5 –, zusammen 15 min; in der Tasche bleiben
    nur die beiden spitzen Ecken mit dem Radius des Ø 6 stehen (7 % ihres Bodens; vorher 29 %).
  - **Nicht so gebaut wie beschrieben:** Die Kontur des Ø 12 fährt weiter in die Tasche – dort,
    wo er ohne Aufmaß hineinpasst –, und „Restmaterial“ nimmt mit dem Ø 6, was er nicht
    erreicht. Zwei Fräser an einer Wand statt einem: einfacher, aber mit einem Absatz, wo sie
    sich treffen. Je Kontur ein eigener Fräser wäre ein zweiter Kontur-Block; offen, bis Manuel
    es so will. *Entschieden (Manuel, 2026-10-03: „wenn dieser 0,0005 mm ist, definitiv zu
    vernachlässigen … wenn das mehr ist, jede Kontur eigenen Fräser“), gemessen am Testteil
    (P-2026-10-03-20; Job über den Assistenten wie `szenario_testteil`, die Bahnen von Kontur
    T1 und Restmaterial T3 gegen 1 097 Punkte am Umriss der Tasche in drei Höhen):* Wo beide
    die Wand erreichen (314 Punkte), bleibt 0,0000 mm stehen – es gibt keinen Absatz. Mehr als
    geometrisch nötig bleibt nirgends (verglichen mit dem Umriss, 3 mm nach innen und zurück:
    nur in den spitzen Ecken bis 3 mm, wohin ein Ø 6 nicht kommt); ins Teil höchstens
    0,0097 mm (T3, die Toleranz der Bahn). Es bleibt bei zwei Fräsern an einer Wand.
- **T4 Wände schlichten, ohne sie einzeln anzuklicken:** der Block „Schlichten danach“
  (Abschnitt 12.4, Option A – entschieden).
  **Gebaut:** P-2026-10-02-90, 0.127.0 (Abschnitt 12.4).
- **T5 Weniger abheben, die Last halten:** Abschnitt 12.1 (Frage 6) – Adaptiv als Variante, die
  schnellste, die die Last hält; Ecken und Spalte in Bögen.
  **Gebaut:** P-2026-10-02-89, 0.126.0 – `raeumen_bahn`: die Variante „adaptiv“ (FreeCADs
  `area.Adaptive2d` mit Vielecken aus dem Raster des Planers; Einstieg von außen in der Luft,
  in der Tasche über eine Helix; zurück unten durchs Freie mit dreifachem Vorschub; danach
  der genaue Ring an der Wand, auf den der Fräser gleitend einschwenkt). `planen` misst die
  Last jeder Variante der Reihe nach (`last`: Querschnitt je mm Weg ÷ ae · Lagentiefe) und
  nimmt die schnellste, die sie hält (kurz höchstens 1,7 ae, über 1,25 ae höchstens eine
  Fräserbreite am Stück); hält keine, die mit der kleinsten Last, und der Assistent sagt es.
  Vorgabe „ringe“: nur die Ringe, ohne Blick auf die Last.
  Gemessen: Testteil 10,7 statt 12,4 min, 5-mal statt 56-mal abgehoben, Last bis 1,4 statt
  5 ae; Zapfen 2,43 statt 2,70; Klotz 9,0 statt 9,7; Platte 33,3 statt 33,9. In Taschen
  gewinnt adaptiv, weil die Ringe in den Ecken bis 4,1 ae greifen – und braucht länger
  (40 × 30: 1,49 statt 0,88 min; offen: T5d, Ecken in Bögen). In einer Nut, kaum breiter als
  der Fräser, hält keine Variante die Last – dort fräst weiter die Nut in Bögen.
  Der Kern rechnet bei gleicher Eingabe nicht immer dieselbe Bahn (±1,5 % Zeit); in einer
  Sitzung bleibt sein Ergebnis je Eingabe gemerkt.
- **T5d Taschen: Ringe, die die Last halten – gelassen** (2026-10-03, nach zwei Anläufen, wie
  im Nachtplan verabredet). Befund an der Tasche 40 × 30 (Ø 12, ae 1,5, 10 tief): Die Ringe mit
  D-Versatz brauchen 0,88 min, greifen aber bis 4,1 ae – nicht in den Ecken der Tasche, sondern
  an den scharfen Ecken der kleinen inneren Ringe (je weiter innen, desto spitzer das Rechteck);
  adaptiv hält die Last und braucht 1,49 min. *Anlauf 1:* Ringe vom Kern der Tasche nach außen
  (Kern = die Zellen, die am weitesten von der Wand liegen; Abstand geodätisch im Raster →
  achteckige Ringe), außen vom genauen Ring an der Wand begrenzt: 1,44 min, Last 3,2 ae – hält
  nicht und ist nicht schneller als adaptiv. Große Tasche 100 × 60: 3,75 statt 2,58 min, Last
  2,7 statt 4,4. *Anlauf 2:* dasselbe mit euklidischem Abstand (Ringe wie ein Stadion, ohne
  Ecken) – der Prototyp ist am Speicher gescheitert (`_abstand_bis` mit `weit = 1e9`), nicht
  wiederholt. *Wer es wieder aufnimmt:* der Stadion-Ring ist der richtige Ansatz gegen die
  Ecken; die Zeit gewinnt er nur, wenn er den Kern in einer Helix öffnet und die Ringe
  spiralig ohne Absetzen verbindet (wie der Morph), sonst bleibt adaptiv vorn. Bis dahin: In
  Taschen gewinnt adaptiv – das hält die Last, Manuels Vorgabe.
- **T5e Überlast vermeiden statt nur melden** (Manuel, 2026-10-04: „Ja mach das so oder wenn es
  nur ein kurzes Stück ist nur diesen einen Bereich neu aufteilen“).
  **Gebaut:** P-2026-10-04-33, 0.172.0 – `raeumen_bahn.planen`: Hält keine Variante die Last,
  wird jede, die schneller wäre, feiner gerechnet – die Ringe nur dort, wo sie sie sprengen
  (zwischen zwei Ringe Teilstücke, 2/3/4 Schritte statt einem: `_teilstuecke`), der Adaptiv-Kern
  auf engen Flächen mit 0,7 und 0,5 × seinem Schritt (`ADAPTIV_ENGER`) –, und zuletzt mit
  gesenktem Vorschub in den Sätzen, die sie sprengen (`_gebremst`: je Satz bis auf 1,25 ae,
  höchstens auf 0,3 × F; der Anteil steht im Programm als F). Es gewinnt die schnellste, die so
  hält. Dazu zwei Fehler im Adaptiv-Kern behoben: In einer geschlossenen Tasche vom Rohteil aus
  bekam er kein Material (das Raster liegt ganz darin, die Höhenlinie schloss sich nie – jetzt
  endet das Material am Rand des Rasters), und findet er mit der Helix 0,8 R keinen Anfang,
  versucht er 0,5 R (`ADAPTIV_HELIX_ENG`). Am Testteil, dreieckige Tasche mit dem Ø 6: vorher
  Ringe bis 4,5 ae mit Warnung; adaptiv sprengt sie jetzt nur noch in der spitzen Ecke (2,3 ae,
  gleich wie eng er rechnet); gewählt die Ringe mit 29 gebremsten Sätzen (bis 0,3 × F) – Last
  1,49 ae, 0,27 min (adaptiv 0,34). Der Assistent sagt am Testteil beim „Rest räumen“ „an 27
  Sätzen langsamer (bis 30 % Vorschub)“. **Zurückgelegt (Manuels Bild, 2026-10-04):** den Bereich, der für die Ringe zu viel
  hat, erst mit D-Bahnen wie in der Nut von der offenen Seite abräumen, bis die Ringe passen.
  An seiner Skizze nachgebaut (Rohteil 120 × 70, Insel 60 × 30, Ø 12, ae 1,5; Untergrenze
  5,0 min): adaptiv 6,29 min und hält die Last, Stiche 7,95, Ringe vom Rohteil 6,91 (bis 2,75
  ae), Ringe um die Insel 8,95 (bis 3,9 ae, an den Rohteilkanten); D-Bahnen geschätzt 6,2 min.
  Ohne Vorgabe nimmt das Addon dort adaptiv – Manuel: „adaptiv: 6,29 min, hält die Last << ??
  dann das ?“. Wieder aufnehmen, wenn ein Teil kommt, an dem Ringe gewinnen und an einer
  offenen Seite überlasten.
- **Fertig, wenn (W-013):** der Assistent am Testteil – alle Flächen angeklickt – einen Job
  anlegt, der im Prüffenster ein Teil ohne Rest ergibt (bis auf Ecken, in die kein Fräser der
  Kiste kommt; die nennt er), das Schruppen höchstens 1,5 × Ziel braucht und keine Bahn die Last
  überschreitet.

## 13b. Im Freien schnell – alle Strategien (P-2026-10-04-39)

Manuel (2026-10-04): „wenn es frei ist und da kein Material ist … muss ich nicht langsam fahren,
gib Gas bis kurz davor, bevor es wieder langsam weiter geht .. bei allen Strategien .. egal was
das ist“; die Geschwindigkeit dafür gehört zur Maschine.

- `freiwege.schneller`: Die Bahn der Operation wird im Materialstand vor ihr abgefahren (Sehnen
  von 1 mm, `restmaterial.Quader`). Eine Sehne auf gleicher Höhe im Vorschub ist frei, wenn im
  Umkreis R + 1 mm nichts über der Spitze steht – das Teil zählt als Material, an Wänden und über
  dem Aufmaß bleibt der Schnittvorschub; geprüft wird gegen den Stand vor dem Satz (was er selbst
  wegnimmt, zählt noch). Wege, die die Strategie schon als frei schneller fährt (Rückwege mit
  3 × F), gelten als frei. Freie Stücke ab 5 mm fahren mit dem Freivorschub – G1, nicht G0
  (der fährt auf vielen Steuerungen keine Gerade) –, die letzten 2 mm vor dem nächsten Material
  langsam (das Bremsen davor macht die Vorausschau der Steuerung). Eilgänge, Eintauchen und
  Rampen bleiben; ein Bogen nur ganz.
- Der Freivorschub: der kleinste Höchstvorschub der Linearachsen der Maschine des Jobs (die
  gemerkte, aus dem Maschinen-Speicher – ohne die Datei zu öffnen); ohne Maschine oder Wert
  10 m/min. Eine neue Linearachse bekommt beim Anlegen 10 m/min, solange keiner eingetragen ist
  (`maschine.VORSCHUB_MAX_VORGABE`; Manuel: „wenn nichts drinnen steht .. dann halt 10 m/min als
  Standard setzen in der Maschine beim Anlegen“, P-2026-10-04-40). Mit „Adaptiv – schneller
  Freivorschub“ am Räumen gilt dessen Wert, höchstens der der Maschine.
- Gilt beim Rechnen der Operation (Räumen, Planfräsen, Kontur, Nut, 3D-Schruppen; seit
  P-2026-10-04-44 auch 3D-Schlichten – nicht gekippt –, Bleistift, Entgraten). Seit
  P-2026-10-04-45 rechnen die Zeiten im Assistenten ihn mit (`gui_bearbeitung._zeit_im_freien`,
  im Materialstand, den der Assistent dem Block gibt; ohne ihn wie bisher) – der Wettbewerb
  vergleicht so die Zeiten der Operationen. Am Testteil: Räumen 1,36 → 1,30 × Ziel, Planfräsen
  127 → 103 % langsamer.
- **Unten bleiben, knapp abheben (P-2026-10-04-59):** Hebt eine Bahn am Ende eines Laufs im
  Eilgang ab, fährt hinüber und taucht senkrecht auf derselben Höhe oder tiefer wieder ein, fährt
  sie auf ihrer Höhe hinüber, wenn der Weg dort im Umkreis R + 1 mm frei ist; sonst nur 2 mm
  (`LINK_LUFT`) über das höchste Material in diesem Umkreis statt bis zur Sicherheitshöhe – beides
  nur ganz über dem Rohteil (daneben könnten Spannmittel stehen). Am Testteil beim 3D-Schruppen
  (jeder Lagenwechsel in der Mulde: 15–23 mm hinauf für 3–10 mm hinüber): Hub 315 → 37 mm,
  Eilgang 417 → 143 mm, 0,53 → 0,50 min; Räumen und Kontur je ein Abheben niedriger.
- **Tiefer im Eilgang (P-2026-10-04-61):** Endet ein Eilgang über einem senkrechten Eintauchen,
  geht er senkrecht weiter hinab bis 2 mm über das Material unter der Stirn (Radius und eine
  halbe Zelle des Rasters – eine Wand mit Aufmaß daneben zählt nicht). Die Bahn weiß nicht, was
  sie selbst schon geräumt hat: An der Platte (Räumen über Oberseite und Tasche in einer Bahn)
  tauchte sie viermal 23 mm mit 298 mm/min durch die schon geräumte Tasche – Eintauchen durch
  Luft 133 → 89 mm (an zwei Stellen ohne Aufmaß zur Wand bleibt es vorsichtig).
- Gemessen: Testteil Räumen T1 10,27 → 9,59 min (2,8 m schnell); Zapfen Planfräsen 3,29 → 2,85
  min. Im Schnellen nichts abgetragen (nachgefahren, 0 mm³).

## 14. Manuels Räumen: Stiche und Ringe, Nut und Schleifen (2026-10-03)

Manuel sah die Bahn des Räumens am Testteil (Bild je Lage: Reihenfolge in Farbe, Eilgang rot,
Eintauchen grün) und zeichnete, wie er fahren würde. Zwei Bilder, zwei Muster:

- **Lage 10, um die Insel** (adaptiv: die Spirale vom Rohteilrand her, links im schmalen Band
  wellig – „das versteh ich nicht, warum macht man das?“): *Rot* die Ecken und Streifen des
  Rohteils Stich für Stich wegräumen, „so dass die Entfernung zur Kontur die gleiche ist wie die
  kleinste Stelle von der Kontur zum Rohteil“; *blau* dann Ringe exakt der Kontur entlang,
  Schritt ae, bis zum Aufmaß; die Wellen „schön mit Schnellvorschub“ zurück.
- **Lage 22, die Insel oben** (adaptiv: Spirale zur Stufe hin, der letzte Gang an der Stufenwand
  wellig): *Blau* zuerst eine Nut an der Stufenwand entlang, in Halbkreisen wie die offene Nut;
  *rot* dann geschlossene Schleifen, die von beiden Rändern – Inselkante und Nut – nach innen
  wandern, bis die Mitte frei ist; *schwarz* die Mulde dabei mitnehmen, so weit Rampe und ap
  erlauben. (Den ersten Anlauf – Versätze der Stufe mit Enden in der Luft – hatte ich falsch
  verstanden.)

Ihn interessierte die Zeit. Prototyp (Raster, eigene Zeichnung, derselbe Prüfstand): Lage 10
6,91 statt 6,65 min (+4 %), Lage 22 3,44 statt 3,35 (+3 %), Eingriff höchstens 1,1 statt
1,7 ae auf der Insel oben. Manuel: „wir nehmen sie mit auf … definitiv“.

### 14.1 Die Regeln (gebaut, P-2026-10-03-31 und -32, Variante „stiche“ in `raeumen_bahn`)

Je Lage (`_ringe_stiche`), auf dem Raster des Feldes (`_Feld`, 0,5 mm) mit dem Materialstand:

1. **Alles Gesperrte ist eine „Insel“** – die Insel auf der Platte wie die Stufe am Rand der
   Insel: Die Stiche sind die Versätze des Gesperrten, von außen nach innen. (P-31 unterschied
   Inseln und Seitenwände und fuhr an Seitenwänden Manuels zweites Muster – Nut in Bögen,
   Schleifen nach innen –; verworfen in P-32, siehe 14.2.) Material, das die Stiche wegnehmen
   können: Rohteil, das die Stirn von einer erlaubten Stelle aus trifft, ohne das Aufmaß an der
   Wand und eine Zelle – sonst zählt die Wand selbst im Raster als Streifen, und ein Stich führe
   an einer bündigen Wand in der Luft entlang.
2. **Ohne Gesperrtes** (die Oberseite eines Klotzes): die Ringe vom Rohteilrand her
   (`_ringe_vom_rohteil`, genau, mit Bögen).
3. **Stiche und Ringe** (`_stiche_um_inseln`): die Höhenlinien des Abstands zum Gesperrten bei
   j · ae (die Ringe davor um eine Zelle nach innen, damit der Schritt auf den genauen Ring am
   Aufmaß ae bleibt), von außen nach innen. Je Höhenlinie die Stiche: die Läufe, unter deren
   Stirn in ihrem eigenen Streifen [L − R, L − R + ae] noch Material steht (Lücken bis 2 R im
   Vorschub durchfahren). Ist der ganze Ring so ein Lauf, ein Ring. Ein Stich ist dran, wenn
   kein Stich weiter außen (bis 2 R + ae) mehr offen ist, dessen Streifen unter seiner Stirn
   liegt (`blockiert`); von den fertigen der nächste am Weg, ein Ring beginnt an der Stelle, die
   der Spitze am nächsten liegt, gleitend über 2 R (`_schwenke_ein`) statt quer in den
   Streifen. Die Läufe fährt `_Lage._lauf` wie bisher (Anfahrt als kleiner Bogen,
   STICHE_ANFAHRT · R statt des Viertelkreises mit R; der Schritt auf den genauen Ring darf
   das Band dort unter der Stirn haben, das er gleich nimmt).
4. *(entfällt – die Schleifen, P-32)*
5. **Rücklauf unten** (`_Lage._rueckweg_aussen`, `_rueckweg_frei`): Ist im Kasten um die Spitze
   und den Anfang des nächsten Stichs (um R breiter) nichts mehr und nichts gesperrt, gerade im
   Eilgang auf der Lage. Sonst, wenn beide neben dem Rohteil stehen, außen herum auf dem
   Rechteck R + 2 mm neben dem Rohteil, achsparallel (auch ein Eilgang, der die Achsen einzeln
   fährt, bleibt so draußen). Sonst der kürzeste Weg durchs Freie im Raster (`_geodaetisch`),
   in so wenige gerade Sätze gefasst, wie der Korridor frei bleibt – im Eilgang, wo der Kasten
   frei ist, sonst im Schnellvorschub (3 × F, G1 wie in der Nut); wird der Weg im Schnellvorschub
   länger als 3 D, hinauf, hin, hinab (das ist dann schneller). Auf der Insel oben liegt
   zwischen zwei Stichen die Insel: dort hebt es ab, rund 25-mal.
6. **Eckenbögen** (`_Lage._bahn_mit_ecken`): An einer scharfen Ecke zur Materialseite (ab 45°,
   Richtung über 2 mm vor und nach der Ecke gemessen – die Höhenlinien wellen sich im Raster um
   Hundertstel) schnitte der Fräser beim Drehen auf der Stelle die Sichel zwischen der Ecke des
   Rings davor (C1, d = ae ÷ sin(α/2) außen) und dieser (C2) auf einmal (Last bis 3 ae).
   Stattdessen hält er vor der Ecke bei Q1 (Lot von C1 auf die Gerade), fährt über C1 nach innen
   und um C1 Bögen, je ae weiter hinaus bis d, von der Normalen der zweiten Geraden zu der der
   ersten (Gleichlauf), zurück über die Innenseite im Schnellvorschub, dann zur Ecke und weiter.
   Nur, wenn in der Sichel noch Material steht (`_sichel_leer`), und nicht in der dünnen Lage
   (ae = R). Am Testteil kommt keine Ecke dran: Die Spitzen der Versätze an der Innenrundung
   liegen in der Luft, die Ecken der Schleifen in der Nut.
7. **Enge Bögen von dem Material weg** (`_enge`): Biegt der Ring mit dem Radius ρ nach links
   (Material rechts), ist der Streifen außen (ρ + R − ae/2) ÷ ρ mal so lang wie der Weg der Mitte
   – an der Innenrundung R 16,4 des Testteils das 2,2-Fache. Dort fährt der Satz mit so viel
   weniger Vorschub, dass die Last je Zeit bei 1,25 ae bleibt (`anteile` in
   `kontur_bahn._bahnpunkte`); `last()` rechnet den Vorschubanteil mit (Volumen je mm ×
   Anteil). Zwischenstiche (halbes ae, nur an der engen Stelle) waren schlechter: 62-mal
   abheben, 14,4 min.
8. **Zuletzt** der Ring am Gesperrten, wo noch etwas steht (`_ringe_um_inseln`, `nur_rest`).
9. **Wahl:** nur auf Vorgabe (Eigenschaft „Variante“ = „stiche“; D-1). Taschen (geschlossene Kontur) bleiben bei den Ringen von innen nach außen
   (`_flaeche`: Tasche → „inseln“).

### 14.2 Gemessen (Testteil, Ø 12, ae 1,5, drei Höhen, Prüfstand)

| | adaptiv | stiche (P-32) | P-31: Nut + Schleifen | Prototyp |
| --- | ---: | ---: | ---: | ---: |
| Lage 10 (um die Insel) | 6,64 min, Luft 4 %, Halte 172 | 8,18 min, Luft 6 %, Halte 540, Vorschub 5,82 statt 6,63 m | 8,18 | 6,91 min, Halte 181 |
| Lage 22 (Insel oben) | 3,35 min, Luft 12 %, Eingriff bis 1,7 ae | 3,79 min, Luft 13 %, Halte 304, 25-mal hinauf, Eingriff bis 1,47 ae | 4,07 min, Luft 21 %, Halte 790 (≈ 100 Bögen), Schleifen zackig | 3,38 min, Eingriff bis 1,1 ae |
| Lage 32 (Stufe, 1 mm) | 0,29 min | 0,40 min | 0,40 | – |
| zusammen | 10,28 min, Last bis 1,42 ae | 12,37 min (+20 %), Last bis 1,47 ae, 0 Rampen, Rest 0, nichts ins Teil | 12,56 min | ≈ 10,6 min |

Manuel zu P-31, Bild der Insel oben: „warum fährt das so seltsam“ – die Schleifen aus dem
Raster zackig (Treppen aus 0,5-mm-Sätzen entlang der schrägen Kante, springender Vorschub),
die Nut ein dicker Schlauch aus 100 D's, die ersten vier Schleifen in der Luft neben der
Kante; „müssen wir nicht verwenden, wenn's länger dauert und nicht schonender ist“. Darum P-32:
an der Stufe dieselben Stiche wie um die Insel (Versätze der Stufe von der Inselkante her, aus
der Luft hinein, in die Luft hinaus) – 3,79 statt 4,07 min, Eingriff 1,47 statt 1,67 ae, ohne
Zickzack. Die Nut und die Schleifen sind aus dem Code (git: P-2026-10-03-31).

Wo die 20 % bleiben: Der Vorschubweg ist kürzer als bei adaptiv; die Zeit kostet das
Zeitmodell (`fahrzeit`: Halt vor und nach jedem Eilgang, 540 statt 172 Halte auf der Lage 10 –
je Stich die Anfahrt, der Rücklauf außen herum in 3–4 Sätzen; auf der Insel oben je Stich
hinauf und hinab) und der kleinere Vorschub an der Innenrundung. Eine Steuerung mit
Vorausschau im Eilgang (Siemens G64, LinuxCNC) hält an den Ecken des Rücklaufs nicht; das
Modell rechnet zu Manuels Ungunsten (W-001, Stufe 4d: „die Achsen fahren einzeln, jede hält“).
Zapfen 50 × 50: 3,74 statt 2,43 min (adaptiv gewinnt).

### 14.3 Offen (Entscheidungen für Manuel)

- **D-1 Der Vorzug – entschieden** (Manuel, 2026-10-03, nach dem Bild der Insel oben: „nimm
  das wieder raus, wir lassen adaptiv … und es nächste Mal bitte erst mit mir besprechen“):
  kein Vorzug, ohne Vorgabe rechnet „stiche“ nicht mit (P-2026-10-03-33). Die Variante bleibt
  als Wahl in der Eigenschaft „Variante“; die Regel: Was das Addon von sich aus wählt, wird
  vorher mit Manuel besprochen.
- **D-2 Das Zeitmodell im Eilgang:** Hält Manuels Steuerung vor und nach jedem G0? Wenn nicht,
  sollte `fahrzeit` Eilgänge wie Vorschubsätze durchfahren lassen (Ecke ab 15°) – das nähme
  der Variante den größten Teil der 22 %.
- **D-3 Die Mulde** (schwarz in Bild 2): Die Stiche über der Mulde hinab, so weit Rampe und ap
  erlauben – nicht gebaut.
- **D-4 Taschen:** Welches Muster in einer geschlossenen Tasche – Helix in die Mitte, dann
  Ringe nach außen (heute), oder Stiche von der Wand her? Mit Bild 2 (die Tasche mit dem Ø 6).
- **D-5 Scharfe Linkskurven** (eine Insel mit einspringender Ecke): Dort bleibt in der Ecke des
  Streifens ein Rest, den der nächste Ring mit einem Schlag nimmt – noch ohne Eckenbögen.
- **D-6 Rücklauf auf der Insel oben:** Heute hebt es zwischen den Stichen ab (Weg im
  Schnellvorschub länger als 3 D). Gerade im Eilgang unten durchs Freie wäre schneller
  (Prototyp 3,38 min) – sicher nur, wenn die Steuerung G0 gerade fährt (Siemens, LinuxCNC:
  ja; Fanuc: nicht immer). Als Einstellung an der Maschine?

## 15. 5 Achsen (W-014, 2026-10-03, Nacht)

Manuel, 2026-10-03 abends: „es gibt noch genug zum Bauen … fang von mir aus mit 5-Achs-Strategien
an … mach einfach weiter, bis ich guten Morgen sage“. Begonnen mit 4.4 Punkt 1 – **3+2 indexiert**
–, weil alles Weitere (simultan, Anstellwinkel) darauf aufbaut und weil damit jede Strategie, die
das Addon schon hat, auf schrägen Flächen fräsen kann. Was das Addon ohne Vorgabe wählt, bleibt
unberührt (Manuel, 2026-10-03: „es nächste Mal bitte erst mit mir besprechen“): 3+2 entsteht nur,
wenn jemand eine Ebene schwenkt.

### 15.1 Das Bild

Ein Zerspaner an einer 5-Achs-Fräse spannt das Teil einmal und **schwenkt die Ebene**: Die
Rundachsen drehen das Teil (oder den Kopf), bis das Werkzeug senkrecht auf der schrägen Fläche
steht; dann fräst er dort wie an einer 3-Achs-Maschine – planen, räumen, Kontur, bohren. Das ist
im Addon schon fast da: Der Assistent „Bearbeitung“ kann das Teil im Job drehen („Unten liegt“,
12.6) und eine zweite Aufspannung anlegen. **Eine geschwenkte Ebene ist eine Aufspannung, die
die Maschine selbst dreht** – ein eigener Job, dessen Modell so liegt, dass die gewählte Fläche
nach oben zeigt. Darin rechnet jede Strategie unverändert (auch FreeCADs Bohren), der
Materialstand gilt, der Prüfstand misst.

Was der Job dazu weiß (Eigenschaften in der Gruppe „5-Achs“):
- **Grundjob** – der Job, in dem das Teil auf dem Tisch liegt, wie es gespannt ist;
- **Ebene** – die Lage der Ebene im Grundjob (Placement: Ursprung und Achsen der Ebene in
  Koordinaten des Grundjobs; Z der Ebene = die Außennormale der Fläche = die Werkzeugachse);
- **Rundachsen** – die Stellung der Rundachsen dafür („A30 C90“), aus der Maschine gerechnet.

### 15.2 Was gerechnet wird (`schwenken.py`)

- **Ebene aus einer Fläche:** Z = Außennormale; X = die Richtung von X des Grundjobs in der Ebene
  (steht X senkrecht auf der Fläche: Y); der Ursprung auf der Fläche (die Projektion des
  Ursprungs des Grundjobs, oder der Punkt der Fläche, der ihm am nächsten liegt).
- **Rundachsen:** die Stellung, in der die Werkzeugachse gegen das Werkstück die Normale der
  Ebene ist – aus der Kette der Maschine (`reichweite.Pruefung`), numerisch über beide
  Rundachsen (grob im Raster, dann genau); von mehreren Lösungen die innerhalb der Grenzen mit dem
  kleinsten Schwenkwinkel. Ohne Maschine: Tisch/Tisch A (um X), C (um Z), Drehpunkt im Nullpunkt
  des Grundjobs – A = arccos n_z, C = atan2(n_x, n_y).
- **Programm ohne Schwenkzyklus** (für Steuerungen ohne: LinuxCNC, Mach): je Punkt der Ebene q →
  p = Ebene · q im Grundjob → die Stellung der Achsen mit den Rundachsen der Ebene → der Punkt im
  Programm, wie eine Steuerung ohne TCPM ihn liest (`kinematik`: X, Y, Z wie mit den Rundachsen
  auf 0). Bögen bleiben Bögen, wenn die Ebene im Programm in XY liegt (Tisch/Tisch), sonst
  Geraden.
- **Programm mit Schwenkzyklus** (Siemens 840D: CYCLE800, Arbeitsvorbereitung 10/2015,
  S. 678–681): `CYCLE800(1,"<Schwenkdatensatz>",0,27,X0,Y0,Z0,A,B,C,0,0,0,-1,0,1)` – Freifahren Z,
  neu, Modus 27 = achsweise in der Reihenfolge Z, Y, X, Bezugspunkt = Ursprung der Ebene im
  Grundjob, die Winkel aus der Lage der Ebene; danach die Sätze der Ebene, wie sie sind; am Ende
  `CYCLE800()`. Die Steuerung rechnet Rundachsen und Werkzeuglänge selbst (TCARR aus dem
  Schwenkdatensatz) – der Nullpunkt bleibt am Teil, wie der Bediener ihn kennt.

### 15.3 Stufen (je ein Patch)

- **F1 Rechenkern** (`schwenken.py`): Ebene aus Fläche, Rundachsen aus der Maschine und ohne,
  Punkte ins Programm ohne Zyklus, CYCLE800-Winkel; Prüfung an einem Teil mit 30°-Schräge.
- **F2 Ebene als Job:** `lege_an(grundjob, flaeche)` – Klon des Modells gedreht, Rohteil als
  gedrehter Quader (der Materialstand liest ihn als Körper), Eigenschaften „5-Achs“. Jede
  Strategie rechnet darin; Prüfung: Räumen der Schräge, im Grundjob nachgemessen.
  **Gebaut:** P-2026-10-03-36 – das Rohteil ist ein Klon des Rohteils des Grundjobs, mit der
  Ebene gedreht (`createResourceClone`); ein gedrehter Kasten zählt im Materialstand als Körper
  (`materialstand._ist_quader`). Am Block mit 30°-Schräge: Räumen der Schräge 2,9 min, kein Rest,
  kein Einschnitt.
- **F3 Programm:** „Programm schreiben“ für einen Job mit Ebene – Siemens mit CYCLE800, die
  anderen ohne Zyklus; der Grundjob mit seinen Ebenen in einem Programm.
  **Gebaut:** P-2026-10-03-37 – `Steuerung.schwenken`/`schwenken_aus` (Siemens
  `CYCLE800(1,"",0,27,…,-1,0,1)` / `CYCLE800()`, editierbar wie jeder Befehl), Haken
  „Mit dem Schwenkzyklus der Steuerung“; ohne Zyklus vorher zum Wechselpunkt, `G0 A… C…`, die
  Sätze gerechnet, danach die Rundachsen auf 0. `abschnitte(grundjob)` nimmt die Ebenen des
  Grundjobs mit (D-4 unten).
  **Nachgezogen:** P-2026-10-03-43 – „Programm schreiben“ rechnet die Ebenen ohne Zyklus mit
  der gewählten Maschine, je Werkzeug mit seiner Länge (`gui_programm.abschnitte_mit_maschine`,
  `pp.abschnitte(job, Operation → Maschine)`): bis dahin rechnete es ohne Maschine (Tisch A, C um
  den Nullpunkt), „Auf der Maschine prüfen“ aber mit ihr – Prüfung und Programm konnten
  verschiedene Zahlen haben. Passen die Rundachsen am Job nicht zur Maschine, neu gelöst
  (`passende_rundachsen`). Am Schwenkkopf (die Ebene im Programm nicht in XY) schreibt die
  Umrechnung Bohrzyklen aus (G73, G81, G82, G83, G85, G89; G83 in Hüben, 0,5 mm vor der letzten
  Tiefe wieder an) statt abzulehnen; nach einem Zyklus steht das Werkzeug auf seiner
  Rückzugshöhe (G98/G99) – bis dahin auf der Tiefe, ein folgendes „G0 X Y“ wäre dort quer
  gefahren. Kopf/Kopf geprüft: Programm und Prüfen fahren dieselben Sätze, die Spitze erreicht
  den Bohrungsgrund.
  Rechnet das Fenster eine Ebene ohne die Kette einer Maschine mit zwei Rundachsen (keine
  gewählt, eine 3-Achs-Fräse), sagt ein Hinweis unter der Vorschau, dass der gedachte Tisch A, C
  um den Nullpunkt gilt (P-2026-10-04-04).
  **Nachgezogen:** P-2026-10-03-52 – steht die Maschine nach dem Wechselpunkt mit Z in MKS ganz
  oben (oder einem Befehl wie F_HOME), schwenkt sie dort: kein „G0 Z…“ mehr hinunter auf die
  Schwenkhöhe davor, beim Zurückschwenken ebenso (`postprozessor._wechselpunkt_oben`,
  `befehle_ohne_zyklus(…, schon_oben=)`). In WKS bleibt die Schwenkhöhe.
- **F4 Auf der Maschine prüfen:** Reichweite, Abfahren, Kollision für einen Job mit Ebene – die
  Sätze ohne Zyklus gerechnet, mit den Rundachsen der Ebene.
  **Gebaut:** P-2026-10-03-38 – `reichweite.operationen_mit_ebene` (der Grundjob mit seinen
  Ebenen), `Pruefung.befehle` (die Sätze ohne Zyklus mit dieser Maschine und diesem Werkzeug;
  passen die Rundachsen am Job nicht zur Maschine, neu gelöst), `grundjob_von` für Nullpunkt,
  Modell und Rohteil (Abfahren, Kollision). Am Tisch/Tisch-Beispiel: A1 auf −30°, die Spitze
  am gedrehten Werkstück genau auf der Bahn der Ebene, nirgends unter der Schräge.
  **Nachgezogen:** P-2026-10-03-41 – an allen drei 5-Achs-Beispielen geprüft (Tisch/Tisch,
  Kopf/Tisch mit B, Kopf/Kopf). Ohne Zyklus fährt das Programm vor dem Schwenken auf die
  Schwenkhöhe (`schwenkhoehe`: die höchste Ecke des Rohteils in allen Zwischenstellungen der
  Rundachsen + 20 mm), auch ohne Wechselpunkt; der erste „G0 Z…“ einer Operation ohne X, Y
  erfindet keinen Punkt X0 Y0 der Ebene mehr (er fuhr quer durchs Teil) – auf der Schwenkhöhe
  über den ersten bekannten Punkt, dann die Achse der Ebene entlang hinunter. „Auf der Maschine
  prüfen“ fährt das Hochfahren und Schwenken mit (`_bahn(start=…)`), die Kollision prüft es.
  Am Beispielteil `beispiele/schwenkteil_5achs.FCStd` (Schräge mit Tasche, 45°-Fläche mit
  Bohrung, Tasche oben; Szenario `szenario_schwenkteil`): nichts stößt an. Fand dabei: Ohne
  Wechselpunkt wechselt die Maschine, wo sie steht – der Bohrer T2 (34 mm länger als T1)
  steckte dann im Teil; der Befund sagt das jetzt dazu (`kb.wechsel_ohne_punkt`, D-5).
  **Im Abspieler:** P-2026-10-03-55 – die Operationen einer Ebene stehen in der Auswahl als
  „Räumen T1 (3) – Ebene A−45 C−90“ (`OperationAbfahrt.ebene`).
  **Kopf/Kopf nachgeprüft:** P-2026-10-03-57 – das Schwenkteil auf der Kopf/Kopf-Maschine: Die
  Kollision meldete beim ausgeschriebenen G83 den Wiedereinstieg zwischen den Hüben („berühren
  sich im Eilgang die Schneide von T2 und das Teil“) – die Bohrung im fertigen Teil ist so groß
  wie der Bohrer. Jetzt zählt die Schneide gegen das Teil nicht in einem Eilgang, der ganz auf
  geraden Vorschubwegen derselben Operation liegt (`kollision._auf_wegen`). Dazu meldet die
  Reichweite dort ehrlich: Z1 bräuchte −263,6 mm, die Grenze ist −250 (die 45°-Ebene mit
  geneigtem Kopf) – eine Grenze der Beispielmaschine.
- **F5 Assistent:** in „Bearbeitung“ Schritt 1 an einer 5-Achs-Maschine „Ebene schwenken:
  Fläche anklicken“ – der neue Job mit der Ebene, die Rundachsen in einem Satz.
  **Gebaut anders:** P-2026-10-03-39 – ein eigener Befehl „Ebene schwenken (3+2) …“ statt eines
  Umbaus am Assistenten: schräge Fläche anklicken, das Fenster nennt Grundjob, Maschine und grün
  „Face3: 30° geschwenkt → A−30 C0“; „OK“ legt den Job an (die Maschine des Grundjobs mit),
  zeigt sein Modell (die Fläche oben) und öffnet „Bearbeitung“ darin, die Fläche gewählt.
  Szenario `szenario_schwenken`: bis „Auf der Maschine prüfen“ auf der Tisch/Tisch-Maschine.
  **Schräge Bohrungen:** P-2026-10-03-42 – statt einer ebenen Fläche geht auch die Wand einer
  Bohrung (eines Zapfens): Z der Ebene ist ihre Achse zum offenen Ende (hinter dem Ende auf der
  Achse, zwei Durchmesser weiter, kein Material; bei Durchgangsbohrungen das Ende, das mehr nach
  oben zeigt), die Ebene geht durch die Mitte dieses Endes (`achse_der_wand`). Für Bohrungen, um
  deren Eintritt keine ebene Fläche ist (in einer Rundung, an einem Zylinder).
  **Im Assistenten:** P-2026-10-03-44 – eine gewählte schräge ebene Fläche (nicht waagerecht,
  keine senkrechte Wand, nicht nach unten) steht in der Liste als „30° schräg – im Job nicht,
  geschwenkt ja“, darunter ein Satz und der Knopf „Ebene schwenken (3+2) …“: schließt den
  Assistenten ohne anzulegen und öffnet „Ebene schwenken“ mit der Fläche, im Grundjob. In einem
  gerade erst entstandenen Job (noch nicht angelegt) nur der Satz: erst „Anlegen“. Dabei
  gefunden: `getStandardButtons` im Fenster „Ebene schwenken“ warf seit P-39 unter PySide6 einen
  TypeError (`int(...)`), FreeCAD zeigte die Knöpfe nicht – die Szenarien riefen `accept()`
  direkt und merkten es nicht. `scripts/oberflaeche_testen.sh` lässt ein Szenario jetzt
  scheitern, wenn im Log ein Traceback aus dem Addon steht.
  **Bestückung:** P-2026-10-03-45 – Grundjob und Ebenen sind ein Programm, also eine
  Bestückung (`bestueckung.aufspannung`): Doppelt belegte Plätze, „Platz für …“ und Umlegen
  sehen alle Jobs der Aufspannung; das Fenster „Bestückung“ sagt es in einem grauen Satz.
  **Im Bild:** P-2026-10-03-46 – öffnet der Assistent in einem Job einer Aufspannung mit Ebenen,
  sind nur dessen Teil und Bahnen sichtbar, die der anderen Jobs nicht (`gui_schwenken.zeige_job`;
  „Abbrechen“ stellt es zurück) – bis dahin lag im Grundjob das gedrehte Teil der Ebene im Bild.
  **Keine doppelte Ebene:** P-2026-10-03-48 – gibt es zur angeklickten Fläche schon eine Ebene
  mit derselben Normalen (dieselbe Fläche, oder eine parallele), sagt das Fenster es, und OK
  öffnet sie (mit „Bearbeitung“ darin), statt einen zweiten Job anzulegen.
  **Ebene aus Winkeln:** P-2026-10-03-50 – ohne passende Fläche Neigung und Richtung
  (`normale_aus_winkeln`, `lege_an(…, winkel=)`), die Ebene durch den Nullpunkt des Grundjobs;
  im Fenster „Oder Winkel“ mit „Übernehmen“. Für einen angestellten Kugelfräser, eine Bohrung
  unter einem Winkel, oder um einen Halter von einer Wand wegzukippen.
- **F6 danach:** der Materialstand über Ebenen hinweg, simultan (Flanke, Anstellwinkel).
  **Materialstand gebaut:** P-2026-10-03-40 – eine Ebene beginnt, wo nach dem Grundjob und den
  Ebenen davor noch Material steht: je Säule ihres Rasters von der Oberkante des gedrehten
  Rohteils hinab der erste Punkt (0,25 mm Schritt), der in allen Höhenfeldern davor unter der
  Höhe liegt; eine Stufe höher als gefunden (lieber Material sehen). Die Kennung trägt die Stände
  davor – ändert sich der Grundjob, rechnet die Ebene neu (gui_materialstand). Am Block: das
  Räumen der Schräge nach dem Räumen der Oberseite 2,8 statt 3,2 min. Simultan: zu besprechen.

### 15.4 Zu entscheiden (Manuel)

- **D-1 Schwenkdatensatz:** Wie heißt er an einer Siemens mit Schwenkkopf/-tisch („TC1“)? Heute
  eine Einstellung beim Postprozessor, vorbelegt leer (ein Datensatz).
- **D-2 Richtung:** CYCLE800 `_DIR` −1 (kleinerer Wert der ersten Rundachse) – oder +1?
  Nachgedacht (2026-10-04 nachts): Mit `_DIR` wählt die Steuerung zwischen den zwei Stellungen
  (etwa A−20 C10 oder A+20 C190); „Auf der Maschine prüfen“ fährt die Stellung, die das Addon
  rechnet (der kleinste Schwenk). Fest −1 passt nur, wenn die erste Rundachse dabei den
  kleineren Wert hat. **Vorschlag:** `_DIR` je Ebene passend zur gerechneten Stellung – dafür
  die Frage: Welche Rundachse ist in deinem Schwenkdatensatz die erste (A oder C, bzw. B)?
  Schon gebaut (P-2026-10-04-05): Bei gleich weitem Schwenk wählt `Maschine.loese` den kleineren
  Wert der ersten Rundachse (bisher entschied die Suchreihenfolge) – wie `_DIR` −1.
  Beispiel, wo es auseinanderläuft (2026-10-04 nachts): Kopf/Tisch-Beispiel am Schwenkteil, die
  45°-Fläche – Lösungen B45 C0 und B−45 C−180; das Addon prüft B45 C0 (der kleinere Schwenk),
  mit `_DIR` −1 nähme die Steuerung womöglich B−45 C180 – eine Stellung, die keine Prüfung
  gesehen hat. Ohne zu wissen, welche Achse „Rundachse 1“ ist, lässt sich `_DIR` nicht sicher
  setzen.
- **D-3 Ohne Zyklus:** Drehpunkt der Rundachsen aus der Maschine (die Baugruppe) – stimmt nur,
  wenn der Nullpunkt im Job zur Aufnahme passt wie in „Auf der Maschine prüfen“.
  **Entschieden** durch Manuels Antwort zu TCPM (Status, 2026-10-03 abends: „die G-Sätze ohne
  TCPM geben dasselbe Teil (die Achsstellungen rechnet das Addon)“); seit P-2026-10-03-43
  rechnet auch „Programm schreiben“ mit der gewählten Maschine.
- **D-4 Ein Programm je Aufspannung:** „Programm schreiben“ für den Grundjob schreibt seine
  Ebenen gleich mit (je Ebene einmal geschwenkt) – oder lieber je Ebene ein Programm?
- **D-5 Wechselpunkt der Beispielmaschinen:** Keine Beispielmaschine hat einen (P-2026-10-02-48:
  nicht vorbelegt, sonst hätten sich alle Zeiten verschoben). Ohne ihn meldet die Kollision bei
  jedem Wechsel auf ein längeres Werkzeug eine Berührung, die eine echte Maschine mit M6 nicht
  hat – jetzt mit dem Satz, dass es am Wechsel liegt. Vorschlag: die Beispielmaschinen bekommen
  einen Wechselpunkt Z ganz oben.

**Entschieden (Manuel, 2026-10-04):**
- **D-1, D-2:** Manuel hat keine 5-Achs-Maschine; es muss für alle gehen: „schau dir bitte im
  Netz die typische Konfiguration an und übernehme das“, und `_DIR` „muss je nach Maschine
  entschieden werden … das ist ja in der Maschinenkonfiguration eingerichtet“. → Schwenkdatensatz
  (Name, welche Rundachse die erste ist, worauf sich die Richtung bezieht) gehört an die Maschine,
  vorbelegt wie an Siemens-Maschinen üblich; `_DIR` je Ebene aus der geprüften Stellung.
  **Gebaut** P-2026-10-04-37: An der Maschine „Schwenkdatensatz“ (CYCLE800 _TC; leer – so
  übergibt man ihn, wenn die Maschine nur einen hat; „0“ wählte ihn ab) und „Richtung bezogen
  auf“ Rundachse 1 oder 2 (bei der Inbetriebnahme im Schwenkdatensatz eingestellt), beide in
  „Maschine bearbeiten“ unter „Home und Werkzeugwechsel“, nur an Maschinen mit zwei
  Rundachsen. Rundachse 1 und 2 wie im Siemens-Schwenkdatensatz (`sw.siemens_reihenfolge`):
  Tisch/Tisch und Kopf/Kopf die, die die andere trägt, zuerst; Kopf/Tisch die des Kopfs zuerst.
  `_DIR` je Ebene (`sw.zyklus_richtung`): −1, wenn die geprüfte Stellung unter den erlaubten den
  kleineren Wert der Bezugsrundachse hat (eine endlose in 0 … 360°), sonst +1. Am Kopf/Tisch,
  45°-Fläche: B45 C0 geprüft → `_DIR` +1 (fest −1 hätte B−45 C−180 genommen).
- **D-4:** ein Programm je Job – mit Sprungmarken je Bearbeitung (Siemens: Marken, die sich mit
  GOTOF/GOTOB anspringen lassen; Heidenhain: LBL), sinnvoll benannt. Im Kopf des Programms: die
  Marken mit ihrer Bearbeitung, die Werkzeuge mit Auskragung und Halter, Hinweise, wo es knapp
  wird. Einzelne Programme je Bearbeitung fände Manuel „unglücklich“. **Gebaut** P-2026-10-04-38
  (Spezifikation Steuerung, Abschnitt 12): jede Marke ein vollständiger Einstieg (Manuel: „Ja,
  jede Marke vollständig“).
- **Verkettung:** Muss der Tisch zwischen zwei Bearbeitungen stark schwenken, erst zum
  Wechselpunkt, dort schwenken, dann wieder hin – die Wege dazu geprüft.
- **D-5:** ja – die Beispielmaschinen bekommen einen Wechselpunkt, angefahren ohne Kollision.
  **Gebaut** P-2026-10-04-36: Fräsen (3 Achsen und die drei 5-Achs-Bauarten) Z ganz oben (Ende
  des Verfahrwegs, die Spindelnase 100 … 300 mm höher), die Drehmaschine X ganz außen; die anderen
  Achsen bleiben stehen. Angefahren wie bisher (Spezifikation Simulation 13): erst die Achse vom
  Teil weg, zurück zuerst die anderen. Gilt für neu angelegte Beispielmaschinen.
- **Abfahren:** Am Ende jeder Bearbeitung fährt der Fräser ins Freie, von dort darf er überallhin.
  Die Zeit zählt bis zum Ende der Zerspanung.
- **Eilgang durchs Rohteil** (Simulation 4c): bleibt so (Manuel: „habe ich ja eigentlich vorher
  schon geklärt“).

## 16. 5 Achsen simultan (W-015)

Die gebauten Schritte stehen in 16.3. Simultan ändert, wie Bahnen entstehen und was im
Programm steht. 3+2 (Abschnitt 15) ist die Grundlage: Rundachsen zu einer Werkzeugachse
(`schwenken.Maschine.loese`), Achsen zu einem Punkt ohne TCPM (`Abbildung`), Abfahren und
Kollision mit Rundachsen je Station.

### 16.1 Wofür

- **Kugelfräser angestellt:** Senkrecht schneidet ein Kugelfräser auf flachen Stellen mit der
  Spitze – dort ist die Schnittgeschwindigkeit 0. Um 10–15° angestellt schneidet er auf dem
  Umfang: bessere Oberfläche, und er darf kürzer gespannt sein.
- **Flanke (Swarf):** eine schräge, gerade oder verwundene Wand mit dem Mantel des Fräsers in
  einem Zug statt in vielen Zeilen mit der Spitze.
- **Kanten in 3D:** entgraten oder fasen, die Fase immer senkrecht zur Kante, auch wo die Kante
  steigt.
- **Wegkippen:** tiefe Taschen und steile Wände mit kurzem Werkzeug – der Halter kippt von der
  Wand weg.

### 16.2 Was dafür gebraucht wird

- **Eine Bahn mit Achse:** je Punkt die Spitze und die Werkzeugachse (im Job). Neu gegenüber 3+2:
  die Rundachsen *entlang* der Bahn stetig – keine Sprünge um 180° in C, am Pol (Achse
  senkrecht) C halten –, innerhalb der Grenzen.
- **Ins Programm, zwei Wege:**
  - *Mit TCPM* – Siemens `TRAORI`: X, Y, Z sind die Spitze im Werkstück, die Orientierung als
    Richtungsvektor `A3= B3= C3=` (oder Rundachsen); Drehpunkt und Werkzeuglänge rechnet die
    Steuerung (Arbeitsvorbereitung 10/2015, S. 301 und 315–316; dort auch `LEAD=`/`TILT=`,
    Voreil- und Seitwärtswinkel). Fanuc `G43.4`, Heidenhain `M128`; LinuxCNC hat es nicht von
    Haus aus.
  - *Ohne TCPM* – je Punkt die Achsen aus der Kette der Maschine, wie „Auf der Maschine prüfen“
    sie schon rechnet. Das Programm gilt dann nur für diese Maschine, diese Werkzeuglänge und
    diesen Nullpunkt.
- **Vorschub:** G93 (1 ÷ Zeit) wie bei 4 Achsen.
- **Prüfen:** Abfahren und Kollision haben die Rundachsen schon je Station; dazu die Lesart mit
  TCPM (X, Y, Z = Spitze im Werkstück).

### 16.3 Stufen (Vorschlag)

- **S1 Kern:** Bahn mit Achse → Rundachsen stetig, Achsen ohne TCPM; Programm mit `TRAORI` und
  ohne. Prüfung: eine Gerade mit kippender Achse an den drei 5-Achs-Beispielen – die Spitze bleibt
  am gedrehten Werkstück auf der Bahn.
  **Gebaut ohne TCPM (P-2026-10-03-49), ohne Oberfläche:** `simultan.py` – `rundachsen_entlang`
  (der erste Punkt die beste Stellung, jeder weitere gedämpft nach Gauß-Newton vom Punkt davor
  aus: am Pol bleibt die freie Achse stehen, endlose Achsen laufen über ±180° weiter),
  `programm_ohne_tcpm`. `tests/test_simultan.py`: an allen drei Beispielen kippt die Achse von
  −20° über die Senkrechte auf +20° ohne Umschlag (Tisch/Tisch: A −20 → 20, C bleibt 90) und
  läuft 120° auf einem Kegel (C stetig bis −210°); die Spitze liegt am gedrehten Werkstück unter
  0,001 µm neben der Bahn, keine Rundachse springt. `TRAORI` (E-1) seit P-2026-10-04-55 als
  Haken „TCPM“ in „Programm schreiben“ (Spezifikation Steuerung, 12). Offen: ob C über ±180°
  hinaus programmiert werden darf (Modulo-Achse an der Steuerung?), die Strategien.
  **G93 (P-2026-10-03-56):** `programm_ohne_tcpm(…, g93=True)` – je Satz 1 ÷ Zeit aus dem Weg der
  Spitze am Werkstück (dreht sich nur die Achse: der größte Winkel in Grad wie mm); am Beispiel
  40 mm mit 10 mm/s → 4,0 s in „Auf der Maschine prüfen“.
  **Verdichten (P-2026-10-04-13):** Ohne TCPM fährt die Maschine zwischen zwei Sätzen jede Achse
  linear; dreht sich eine Rundachse, wandert die Spitze am Werkstück von der Geraden weg (ein
  Satz von 20 mm, in dem die Achse um 40° kippt: in der Mitte 5,5 mm am Tisch/Tisch, 21,7 am
  Kopf/Tisch, 18,7 am Kopf/Kopf). `programm_ohne_tcpm` halbiert solche Sätze (`verdichtet`,
  `abweichung`: die Spitze in der Satzmitte über die umgekehrte `Abbildung`), bis sie höchstens
  `TOLERANZ` 0,005 mm daneben liegt – dort 65 bzw. 129 Punkte, bis 0,0046 mm, auch bei einem und
  drei Vierteln des Satzes. G93 zählt je Teilsatz; zusammen bleibt die Zeit.
- **S2 Kugelfräser angestellt** (Vorschlag für zuerst): das 3D-Schlichten, das es gibt, mit
  Anstellwinkel. Beim Kugelfräser bleibt der Mittelpunkt der Kugel, wo er ist – nur die Achse
  kippt um ihn; die Bahn muss nicht neu gerechnet werden, nur die Achse je Punkt (voreilend in
  Vorschubrichtung, seitwärts quer dazu). Kleinstes Risiko, gleich nützlich; der Prüfstand misst
  wie bisher.
  **Als 3+2 schon nutzbar (P-2026-10-03-50):** mit fester Neigung braucht es kein Simultan – eine
  Ebene aus Winkeln („Ebene schwenken“ → „Oder Winkel“: Neigung, Richtung) und darin das
  3D-Schlichten, das es gibt. Versuch an der Kuppel aus `test_schlichten3d` (Kugel Ø 6,
  Grathöhe 0,01): senkrecht 3,43 min, Rest im Mittel 0,0037 mm; 15° nach +Y 3,45 min, 0,0035 mm
  – dieselbe Fläche; auf der Kuppelspitze schneidet die Kugel mit Ø 1,55 statt mit der Spitze.
  Simultan bliebe für eine Neigung, die der Vorschubrichtung folgt.
  Szenario `szenario_angestellt` (P-2026-10-03-51): die Kuppel auf der Tisch/Tisch-Maschine, A15
  die ganze Bahn, 5,4 min, Kollision frei.
  **Gebaut simultan (P-2026-10-04-21; Manuel, 2026-10-04: „Ja, so bauen“):** `angestellt.py` –
  „3D-Schlichten“ mit der Eigenschaft `Anstellen` (dazu `Anstellwinkel` 15°, `Kippachse` X oder
  Y). Die Kugel bleibt, wo sie ist: Die Operation speichert die senkrechte Bahn (in Sätzen zu
  höchstens 0,5 mm, ohne Bögen) und je Satz die Werkzeugachse (`Werkzeugachsen`) – Restmaterial,
  Materialstand, das Bild und ein Programm für eine 3-Achs-Maschine bleiben richtig. Im Vorschub
  kommt die Achse aus der Normale am Berührpunkt (`distToShape` von der Kugelmitte): verboten
  ist jede Neigung, bei der die Achse der Normale näher steht als der Winkel (`verboten`), die
  Neigung bleibt so nah an 0 wie erlaubt und ändert sich höchstens um 2° je mm (`neigungen`);
  muss sie schneller, springt sie um die ruhende Mitte. Ein Eilgang hinauf behält die Achse,
  jeder andere nimmt die des nächsten Schnitts (die Achse dreht über dem Teil, die Spitze bleibt
  auf der Geraden). Prüfen, Abfahren, Kollision und Programm setzen die Spitze um (Mitte − R ·
  Achse) und rechnen die Rundachsen (`simultan.programm_ohne_tcpm` mit `bezug` = R: die Mitte
  der Kugel bleibt beim Verdichten auf der Geraden, G93 nach ihrem Weg); davor auf die
  Schwenkhöhe, schwenken, darüber; danach hinauf, die Rundachsen auf 0. „Programm schreiben“
  ohne Maschine mit zwei Rundachsen: senkrecht, mit einem Satz. An der Kuppel (Tisch/Tisch, Ø 6):
  A 0 … 29,4°, C steht, 4,50 statt 4,25 min, kleinster Winkel zur Normale 15,000°, „Kollision
  prüfen“ frei. **Im Assistenten (P-2026-10-04-22):** beim 3D-Schlichten (und Restschlichten)
  der Haken „Anstellen (5 Achsen simultan)“ – frei an einer 5-Achs-Maschine mit Kugelfräser,
  sonst gesperrt mit dem Grund hinter der Beschriftung; die Kippachse aus der Maschine (A → X,
  B → Y). Szenario `szenario_kugel_angestellt`.
- **S3 Flanke:** eine Regelfläche (schräge oder verwundene Wand) mit dem Mantel.
  **Versuch (2026-10-04 morgens, für Manuel):** Block 80 × 60 × 30, Tasche 40 × 24, 20 tief, Wände
  mit 10° Formschräge, Ecken R 6 → R 9,5 (Kegel), gleicher Vorschub 1000 mm/min: 3-Achs mit dem
  3D-Schlichten des Addons, Kugel Ø 6 in 36 Höhenlinien 4,26 min (Ø 10: 25, 2,68 min); Flanke mit
  Schaftfräser Ø 10 ein Umlauf, 0,45 min auf der Tisch/Tisch-Maschine (A −10° fest, C einmal
  herum), in den Kegel-Ecken höchstens 0,0012 mm daneben, „Kollision prüfen“ frei; am Fuß bleibt
  keine Rundung der Kugel stehen. 3-Achs ginge es auch in einem Umlauf – nur mit einem
  Konikfräser von genau 10°. Manuel: „Ja, so bauen“, und „selbst anhaken, wenn schneller“.
  **Gebaut (P-2026-10-04-24):** `flanke_bahn.py` – Wände (`ist_wand`): Ebene (auch als B-Spline,
  `findPlane`), Kegel, schräger Zylinder oder eine Fläche mit gerader Parameterlinie, nach oben
  offen, 0,5° bis 45° aus der Senkrechten. Die Mantellinie: an der Ebene die Fallinie, am Kegel zur
  Spitze, am Zylinder die Achse. Die unteren Kanten der Wände zu Zügen (`zuege`); Normalen mehr als
  1° auseinander teilen den Umlauf. Je Stelle (alle 0,2 mm an gekrümmten, 2 mm an geraden Kanten
  einer Ebene) die Spitze um Radius und Aufmaß vor dem Fuß, die Stirn nie tiefer als er; schnitte
  der Fräser (0,002 mm kleiner) dort ins Teil – eine scharfe Innenecke –, fällt die Stelle weg, die
  Grenze wird halbiert. Gleichlauf (das Material rechts), Lagen, wenn die Wand länger ist als die
  Schneide; An- und Abfahren die Achse entlang 2 mm vor der Wand. `flanke.py` – die Operation
  speichert die Spitzen und je Satz die Achse; „Auf der Maschine prüfen“, die Kollision und das
  Programm rechnen die Rundachsen (`simultan.befehle_auf_maschine`, die Spitze und das obere Ende
  der Schneide auf der Geraden; `simultan_operation` ist die Weiche für Anstellen und Flanke).
  Ohne Maschine mit zwei Rundachsen schreibt das Programm die Flanke nicht – senkrecht gefahren
  schnitte sie falsch. Die Tasche auf der Tisch/Tisch-Maschine: 0,69 min mit Anfahren und
  Schwenken. **Im Assistenten (P-2026-10-04-25):** der Block „Flanke (5 Achsen simultan)“ hinter
  dem 3D-Schlichten – möglich nur an einer 5-Achs-Maschine, vorgeschlagen, sobald eine passende
  Wand gewählt ist, im Wettbewerb mit dem 3D-Schlichten (die Zeit zählt das Drehen der Achse in
  Grad wie mm); hat das 3D-Schlichten noch andere Flächen (eine Kuppel), gibt es ihr die Wände ab.
  Die Flanke ohne Aufmaß macht ihre Wände fertig; „Ebene schwenken“ bietet der Assistent für sie
  nicht an. Szenario `szenario_flanke`: die Tasche – Flanke 1 min, 3D-Schlichten 690 % langsamer.
- **S4 Wegkippen**, wenn der Halter sonst anstößt.
  **Versuch (2026-10-04 morgens, nicht im Addon):** Kavität 30 tief mit Boden-Rundung R 8 (Ecken
  R 10), Kugel Ø 6, das 3D-Schlichten des Addons auf den Rundungen; je Stelle (jede 15., 267) die
  kleinste Auskragung, bei der der Halter (1 mm Spiel) und der Schaft nirgends anstoßen – die Achse
  um die Kugelmitte zur Mitte der Kavität gekippt, nur so weit wie nötig. Senkrecht immer gut
  30 mm (31,0): Der Halter muss über den Rand, wie schlank er auch ist. Spannzangenfutter ER16
  (Mutter Ø 28) bis 30° gekippt: 28,0 / 27,4 / 27,0 mm bei 80 / 50 / 36 mm Breite – 1,45-mal so
  steif (∝ 1/L³). Schrumpffutter Ø 21 (Vorlage „schrumpf_6“), 50 × 50, bis 30°: 21,7 mm – 2,9-mal
  so steif. Das Rechnen: 90 s für 267 Stellen (je Stelle eine Suche mit `distToShape` des
  Halters) – für eine ganze Bahn (4 000 Punkte) etwa 20 min; gebaut bräuchte es eine schnellere
  Prüfung (Höhenfeld des Teils statt Körper). Die Zeit mit Kippen ist nicht gemessen. Bild
  `22_wegkippen.png` an Manuel; Empfehlung: jetzt nicht bauen – es lohnt sich nur mit schlankem
  Halter, und eine Bahn rechnete zu lange.
  **Gebaut (Manuel: „Ja, bauen“; P-2026-10-04-29/-30):** `wegkippen.py` – das Teil als Höhenfeld
  (`Huelle`: hoehenfeld.hoehen, 0,5 mm, auf ganzen Vielfachen; gefragt das Höchste der vier
  Rasterpunkte, für das Spiel im Kreis um es verbreitert – sonst kam der Halter neben einer
  senkrechten Wand bis 0,02 mm heran), Halter und Schaft als Punkte auf Ringen (`koerper`, über
  dem Teil weggelassen); je Stelle die kleinste Neigung ins Freie (die Richtungen zu den
  Rasterpunkten im Umkreis des Halters, nach ihrer Tiefe gewichtet) oder den Abfall hinab, was
  weniger braucht (`noetig`, 5°-Schritte, dann 1°); senkrecht zählt der Schaft nicht.
  Geglättet über gemittelte Kippvektoren (die Richtung dreht stetig) und nachgeprüft (`pruefen`):
  jede Stelle, und die Mitte zwischen zwei Stellen mit der gemittelten Achse – dort setzt das
  Maschinenprogramm Punkte ein, und dort hatte der Halter das Teil berührt, als die Richtung
  sprang. `kuerzeste_auskragung` sucht halbierend. An der Kavität (30 tief): senkrecht 31,0;
  bis 30° ER16 28,3, Schrumpffutter 21,9 mm; am Maschinenprogramm nirgends näher als 0,8 mm.
  „3D-Schlichten“ mit der Eigenschaft `Wegkippen` (und `WegkippenBis`, 30°): Halter und
  Auskragung wie „Auf der Maschine prüfen“ (Werkzeugverwaltung, sonst der vorgeschlagene); reicht
  auch der größte Winkel nicht, ein Satz im Bericht. Im Assistenten der Haken „Wegkippen (5 Achsen
  simultan)“ (5-Achs-Maschine, Kugelfräser), hinter dem Ergebnis der Bedarf: „– weggekippt
  reichen 22 mm Auskragung (senkrecht 31); dein Fräser steht 23,5 heraus“. Auf der Tisch/Tisch-
  Maschine dreht C bei jedem Ring einmal herum – rechnerisch 19 statt 8 min. **Geklärt
  P-2026-10-04-42:** Nicht die Maschine bremste (C 50 U/min, viermal so schnell: gleiche Zeit),
  sondern das Programm: Im G93 zählte 1° Drehung wie 1 mm beim Schnittvorschub – an einer Ecke
  dreht der Tisch 90°, die Spitze fährt 15 mm. Jetzt die längere Zeit aus Spitze ÷ Vorschub und
  Winkel ÷ halber Geschwindigkeit der Rundachse aus der Maschine (`simultan.DREHANTEIL`,
  `drehgeschwindigkeiten`; Manuel: „Ja, mit halber Geschwindigkeit“) – die Spitze fährt nie
  schneller als der Vorschub. Rechte Kavitätenseite: 3,00 → 1,52 min (senkrecht 1,03); der Rest
  waren Eilgänge (0,48 min): Ein Eilgang mit drehender Achse wurde verdichtet (gut 30 G0), und an
  jedem G0 hält die Maschine an – jetzt G1 im G93 mit dem Eilgang der Maschine und der vollen
  Geschwindigkeit der Rundachse (`simultan.eilganggeschwindigkeit`; P-2026-10-04-47); und das
  Abfahren rechnete einen für die Kollision in 1°-Schritte geteilten G0 so, als hielte die
  Maschine an jedem Schritt (das Zurückschwenken 15,8 statt 1,7 s). Jetzt: 1,09 min.
- **S5 Entgraten in 3D.** *Prototyp (2026-10-04, nicht im Addon – zum Besprechen):* am
  Schwenkteil, Fasenfräser 90° (Ø 10, Spitze 0), Fase 0,5 mm. Je Punkt der Kante (alle 0,5 mm)
  die Achse senkrecht zur Kante und 45° neben der Winkelhalbierenden der beiden Flächen (von den
  zwei Lösungen die steilere), die Mitte der Fase 2 mm neben der Achse auf der Kegelflanke – die
  Flanke liegt überall genau parallel zur Fase, die Fase auf beiden Flächen 0,5 mm, auch wo die
  Kante steigt oder die Flächen nicht rechtwinklig stehen. 49 konvexe Kanten (ohne die
  Unterkanten auf dem Tisch): 15 kann das heutige Entgraten (waagerecht, oben eben, Wand
  senkrecht), 24 gingen neu ohne Verletzung (die 30° steigenden Kanten an der Schräge, die
  Bohrungsränder darauf, die Kanten mit 45°/60°/120° Flächenwinkel, die senkrechten Ecken), an
  10 in engen Nuten und kleinen Bohrungen stieße der Kegel Ø 10 bis 3,25 mm in die Gegenwand
  (dort ein kleinerer Fräser oder die Fase weiter zur Spitze). Tisch/Tisch: A −90…90°, C 0…270°,
  946 mm im Vorschub, 1,7 min mit 600 mm/min (G93). Offen für einen Bau: Kanten wählen (oder
  Flächen, deren Kanten), Reihenfolge und Wege zwischen den Kanten, Kollision von Schaft und
  Halter, das Prüffenster (die Fase im Abtrag), die Ecken am Ende einer Kante. Bild:
  `entgraten_3d.png` (an Manuel geschickt). **Frage an Manuel:** so bauen – als eigene Operation
  „Entgraten 3D (5 Achsen)“ für gewählte Kanten, im Assistenten ohne Haken?
  **Manuel (2026-10-04):** „es gibt ja auch 90-Grad-Fräser, mit welchen man schon fast überall
  hinkommt, und ja, es muss schon so sein, dass man nicht das Werkstück beschädigt“; „grundlegend
  auf der 5-Achs sollte das ja mit jedem Fräser möglich sein, der unten flach ist … also bau das
  nicht nur auf den 45-Grad-Fräser … aber mit einem 45-Grad-Fräser kann man schon sehr viel auch
  auf einer Dreiachs-Maschine machen“.
  **Gebaut (P-2026-10-04-65): Kern und Operation** – `entgrat3d_bahn.py`, `entgraten3d.py`
  („Entgraten 3D T3“). Drei Wege: 5 Achsen mit Fasenfräser (jeder Spitzenwinkel; die Achse ⟂
  Kante, 90° − α neben der Winkelhalbierenden, die Fase auf der Flanke) oder mit ebener Stirn
  (Schaft, Torus – ihr ebener Teil –, Plan, Nut; die Achse auf der Fasenebene, die Fase neben der
  Mitte der Stirn), beide symmetrisch mit der Breite auf jeder Fläche; 3 Achsen mit dem
  Fasenfräser senkrecht – die Fase ist die Tangentialebene des Kegels durch die Kante (geht, bis
  die Kante so steil steigt wie die Flanke), die Breite auf der Fläche, die nach oben schaut, der
  andere Schenkel steht im Ergebnis. Das Werkstück wird nicht beschädigt: Die Flächen um die
  Kanten werden dicht abgetastet (0,25 mm, Raster in numpy); an jeder Stelle (alle 0,5 mm) darf
  kein Punkt im Werkzeug liegen (Schneide und 15 mm darüber) außer im Fasenstreifen der beiden
  Flächen zwischen den Kantenenden, und nichts unter dem Tisch (die Unterkante des Teils); sonst
  rutscht die Fase zur Spitze bzw. auf die andere Seite der Stirn, sonst bleibt die Stelle aus
  (`Ausgelassen`, mit Grund im Ausgabefenster). Springt die Achse um mehr als 5°, beginnt ein
  neuer Lauf; angefahren längs der Achse bis frei plus Sicherheitsabstand, vorher senkrecht von
  der sicheren Höhe (geprüft), im Gleichlauf. Unabhängig nachgeprüft (`test_entgraten3d`): Der
  Fräser schneidet das Teil (OpenCascade, 0,02 mm zurück) nur im Keil an der Kante. Am Schwenkteil
  (alle Flächen, Fase 0,5): 5 Achsen Kegel 90° Ø 10 – 33 Kanten, 826 mm, 359 mm zu eng; Ø 6
  834 mm; Schaftfräser Ø 10 – 31 Kanten; 3 Achsen – 23 Kanten, 535 mm, Schenkel 0,13 … 1,87.
  Programm, „Auf der Maschine prüfen“, Kollision (darf ins Teil – die Fase steht nicht im Modell),
  TCPM wie die Flanke. **Im Assistenten (P-2026-10-04-66):** der Block „Entgraten 3D“ nach dem
  Entgraten, nie von selbst angehakt (welche Kante eine Fase bekommt, sagt die Zeichnung);
  Fasenfräser vorgewählt (mit dem Haken auch ein Fräser mit ebener Stirn), Fasenbreite (grau 0,5),
  der Haken „Angestellt (5 Achsen)“ nur an einer 5-Achs-Maschine und dort angehakt – ein Haken,
  den der Assistent selbst abgehakt hat, weil er nicht ging, kommt zurück, wenn er wieder geht.
  Die Vorschau gröber (Stellen alle 1 mm, Punkte alle 0,35 mm): „→ 8 Kanten mit Fase, etwa 1 min.
  48 mm Kante ohne Fase: 48 mm zu eng …“. Hilfe „Bearbeitung“, Abschnitt 9.
  **Schaft, Halter, Spindel (P-2026-10-04-67):** „Kollision prüfen“ am Schwenkteil (Tisch/Tisch)
  fand 2 Berührungen und 4 Stellen unter 1 mm: Spindel und Halter im Rundtisch, wo der Kegel an
  einer senkrechten Kante dicht über dem Tisch waagrecht lag, der Halter 0,79 mm am Teil. Jetzt
  rechnet die Bahn den Aufbau mit (`Aufbau`: Schaft und Halter als Kegelstümpfe aus der
  Werkzeugverwaltung wie die Kollision – `wegkippen.einspannung`, ohne gewählten der
  vorgeschlagene; darüber die Spindel, Radius 60 mm, nur gegen den Tisch): Schaft und Halter
  bleiben 1,5 mm vom ganzen Teil (grob abgetastet, 1 mm), alles samt Spindel 1,5 mm über dem
  Tisch. Der Kegel darf dafür um die Normale der Fase kippen (in 5°-Schritten bis 60°, nach oben
  zuerst, stetig von Stelle zu Stelle): Seine Mantellinie läuft dann schräg über die Fase, die
  Ebene bleibt dieselbe – gekippt wird nur für Tisch und Halter, nicht wo schon die Schneide
  anstößt. Neue Gründe „zu nah am Tisch (das Teil höher spannen)“ und „Schaft oder Halter
  stieße an“. Danach am Schwenkteil: 33 Kanten, 768 mm (vorher 826 mm, davon einige nur mit
  Kollision), 70 mm zu nah am Tisch; „Kollision prüfen“ ohne Befund. 11,7 s für alle Flächen
  (vorher 5 s ohne den Aufbau). Steht das Werkzeug nicht in der Werkzeugverwaltung, ist seine
  Länge die Gesamtlänge des CAM-Werkzeugs (nicht ab Spindelnase) – dann ragt es mindestens die
  Schneide und 5 mm aus dem Halter wie beim vorgeschlagenen.
  **Ecken und Innenkanten (P-2026-10-04-68):** Die Fase hörte an jedem Kantenende vor der Ecke
  auf (am Klotz 0,75 mm mit dem Fasenfräser, 3,25 mm mit dem Schaftfräser) – dort blieb der Grat.
  Jetzt darf der Fräser an einer Ecke die Fläche anschneiden, die die Kante abschließt
  (`_kappen`: ihre Außennormale zeigt am Ende über die Kante hinaus, cos > 0,2), jenseits der
  Fasenebene und nahe dem Ende – das Dreieck, das jede Fase bis zur Ecke herausnimmt. Endet die
  Kante an einer Wand (Normale zurück zur Kante), bleibt alles wie zuvor: Die Fase hört davor
  auf. Nachgeprüft an einer Stufe (`test_entgraten3d`): links bis x 0,00, rechts vor der Wand bei
  35,5 (Kegel) bzw. 37 mm (Stirn), der Block darüber unberührt (OpenCascade). Dabei gefunden: Die
  Erkennung der Innenkanten griff nie (die Probe auf der Winkelhalbierenden der Normalen liegt an
  beiden Kantenarten im Freien) – Innenkanten standen als „zu eng“ im Ergebnis. Jetzt die Probe
  ±(n1 − n2): an einer konvexen Kante beidseits Luft. Am Schwenkteil danach 33 Kanten, 784 mm,
  73 mm zu eng (vorher 341 mm, fast alles Innenkanten), 70 mm zu nah am Tisch; Kollision ohne
  Befund.
  **Ruhige Spitze (P-2026-10-04-69):** Im Screenshot des Szenarios sprang die Spitze unten an der
  Schräge des Klotzes von Stelle zu Stelle zwischen zwei Anteilen hin und her (0,9 mm, ein
  Sägezahn) – die Halterprüfung hielt dort knapp mal und mal nicht. Jetzt kommt die Lage der
  Stelle davor zuerst dran: ihre Achse, ihr Anteil (bei der Stirn auch die Seite). Am Schwenkteil
  358 statt 555 Sätze, 4,0 statt 4,3 min, Kollision ohne Befund. `test_entgraten3d` zählt je Lauf,
  wie oft die Spitze quer zur Laufrichtung umkehrt (höchstens 2 – an den Ecken gleitet die Fase
  zur Spitze); mit dem alten Stand bis 15.
  **Geschlossene Ränder, glatte Nachbarn (P-2026-10-04-70):** An Manuels Testteil (3 Achsen,
  Fasenfräser 90° Ø 10) war der ganze Rand der Kugelmulde „zu eng“ – zwei Fehler: Ein
  geschlossener Rand (Kreis) hat Anfang und Ende im selben Punkt, „zwischen den Enden“ ließ
  fast nichts der eigenen Flächen zu (gilt für jeden Bohrungs- und Taschenrand als voller Kreis);
  und unter dem Rand liegt dort ein Zylinderband von 0,01 mm, erst darunter die Kugel – sie zählte
  nicht zur Kante. Jetzt hat ein geschlossener Rand keine Enden, und Flächen, die glatt an die
  beiden der Kante anschließen (Normalen weniger als 15° auseinander, bis zwei Flächen weit),
  gehören zur Fase; ein Lauf über die Naht des Kreises bleibt einer. Testteil danach: 20 von 30
  Außenkanten, 717 mm (vorher 19, 677 mm); am Muldenrand nur noch, wo die Insel daneben steht,
  keine Fase (mit dem vorgeschlagenen Halter: 10 mm Auskragung). Am Prüfklotz bekommt auch der
  Rand der Bohrung seine Fase. Die Halterprüfung siebt erst mit einer Hülle je Höhe und sucht je
  Stück (Testteil 10,2 → 7,1 s).
  **Senkrecht heraus im Eilgang (P-2026-10-04-71):** Am Ende jedes Laufs fuhr das Werkzeug längs
  der Achse im Vorschub heraus – am Testteil 21 Läufe, 52 mm Luft im Vorschub (etwa 10 s). Steht
  die Achse senkrecht (3 Achsen), ist es ein reiner Z-Weg: jetzt gleich im Eilgang hinauf.
  Schräg bleibt es im Vorschub – ein Eilgang fährt nicht an jeder Steuerung gerade (Fanuc ohne
  lineare Eilganginterpolation), und der Fräser steht noch an der Fase. Eintauchen bleibt im
  Vorschub ab dem Sicherheitsabstand.
  **Tief hinüber (P-2026-10-04-72):** Zwischen zwei Läufen ging es jedes Mal auf die sichere
  Höhe. Mit senkrechter Achse jetzt nur so hoch, wie Schneide, Schaft und Halter über allem auf
  dem Weg ABSTAND haben: je Punkt der groben Wolke aus seinem Abstand zum Weg und dem Umriss des
  Werkzeugs (ab welcher Höhe über der Spitze es so breit ist), der Weg dann mit der vollen
  Prüfung nachgeprüft. Nicht über `freiwege` – das rechnet nur mit dem Fräserradius, der Halter
  (am vorgeschlagenen 10 mm über der Spitze) striche dort an der Insel vorbei. Testteil: Eilgang
  728 → 411 mm, 2,88 → 2,84 min; „Kollision prüfen“ an der 3-Achs-Beispielmaschine ohne Befund.
  **Was hilft (P-2026-10-04-73):** „Schaft oder Halter stieße an“ sagte nicht, was man tun kann.
  Jetzt zwei Gründe: „der Schaft käme dem Teil zu nah (ein schlankerer Fräser)“ – länger
  ausspannen hilft nicht, der Schaft wird nur länger – und „der Halter stieße an“; dafür probiert
  die Bahn 5, 10, 15, 20, 30 mm mehr Auskragung und nennt die erste, mit der alle diese Stellen
  eine Fase bekämen („– mit 15 mm Auskragung ginge es“). Testteil (vorgeschlagener Halter, 10 mm
  ausgespannt): 40 mm Halter – mit 15 mm ginge es –, 8 mm Schaft. Mit 3 Achsen heißt, was der
  senkrechte Kegel nicht fasen kann (keine seiner Tangentialebenen durch die Kante schneidet beide
  Flächen ab), jetzt so: „mit dem senkrechten Kegel nicht zu fasen (Kante unten am Teil oder für
  seinen Winkel zu flach geknickt)“ – vorher „ohne passende Stellung“ (Schwenkteil: 281 mm).
  **Kanten anklicken (P-2026-10-05-02; Manuel, 2026-10-05: „ja, Kanten anklicken muss sein“):**
  Im Assistenten lassen sich mit Job auch Kanten anklicken (das Auswahltor lässt „Edge…“ des
  Teils im Job durch). Sie stehen in einer eigenen Liste (`kanten`) neben den Flächen – nur
  „Entgraten 3D“ bekommt sie (`nimmt_kanten`), alle anderen Strategien sehen weiter nur Flächen;
  in der Liste „Edge12 Kante, 20 mm – Fase mit „Entgraten 3D““ (grün) bzw. „keine Kante zum Fasen
  – innen, glatt oder unten auf dem Tisch“ (rot), im 3D die Kante grün (LineColorArray). Sind
  Kanten angeklickt, ist der Block angehakt; nur Kanten und keine Fläche: die anderen Blöcke nicht.
  In der Operation stehen sie unter `Flaechen` („Edge12“), beim Ändern kommen sie zurück.

**Versuch an der Kuppel (2026-10-04 nachts, nicht im Addon):** Kuppel R 25 aus `test_schlichten3d`,
Kugelfräser Ø 6, die Bahn, die das Addon wählt (eine Spirale, 46 Umläufe, 10 660 Punkte zu je
0,5 mm). Die Kugel bleibt in allen Varianten, wo sie ist – nur die Achse kippt um ihre Mitte;
je Punkt der Schnitt-Ø am Berührpunkt (2R · sin φ, φ = Winkel zwischen Achse und
Flächennormale) und für die simultanen Varianten die Rundachsen der Tisch/Tisch-Maschine
(`simultan.rundachsen_entlang`), die Zeit aus dem Abfahren mit G93 und Beschleunigung:

| Werkzeugachse | Zeit | Bahn mit Schnitt-Ø < 1 mm | Rundachsen |
|---|---|---|---|
| senkrecht (heute) | 3,35 min | 5,4 % (bis Ø 0 auf dem Gipfel) | – |
| 3+2 fest 15° nach +Y | 3,35 min | 5,3 % (bis Ø 0,06 – die Stelle wandert nur) | A 15 fest |
| simultan, 15° zur Fläche voreilend | 21,5 min | 0 % (überall Ø 1,55) | C dreht je Umlauf einmal herum (21 169°), A 2 314° |
| simultan, so wenig wie nötig, Richtung frei | 7,9 min | 0 % | in der Mitte (Ø 13) dreht C je Umlauf herum (4 860°) |
| simultan, so wenig wie nötig, **nur A** (immer in der Ebene YZ) | **3,54 min** | 0 % | A 0 … 29,5°, C steht |

„So wenig wie nötig“: Ist die Fläche steiler als 15°, bleibt die Achse senkrecht; sonst kippt
sie gerade so weit, dass zwischen Achse und Normale 15° liegen. Die Variante „nur A“ kostet 6 %
Zeit und schneidet nirgends mit der Spitze; ihre größte Änderung je Satz war 4,5° (eine stetige
Fassung, A = min(0, β − 15°), braucht 4,9 min). Ohne TCPM fährt die Maschine zwischen zwei
Punkten jede Achse linear – bei 4,5° je Satz weicht die Spitze am Tisch/Tisch bis etwa 0,08 mm
ab; seit P-2026-10-04-13 verdichtet der Kern solche Sätze selbst. Kollision nicht geprüft. Bilder:
Draufsicht nach Schnitt-Ø je Variante, Seitenansicht mit dem Werkzeug (im Bericht an Manuel).

### 16.4 Zu entscheiden (Manuel)

- **E-1 TCPM:** ~~Hat deine Maschine `TRAORI`?~~ Schon beantwortet (Status, „Beantwortet am
  2026-10-03 abends“): „TCPM bleibt aus. Es soll auf allen Maschinen gehen; die G-Sätze ohne TCPM
  geben dasselbe Teil … TCPM später als Haken.“ Der Kern S1 rechnet ohne TCPM.
- **E-2 Zuerst:** ~~S2 (Kugelfräser angestellt) oder S3 (Flanke)?~~ **Entschieden** (Manuel,
  2026-10-04): S2 – gebaut (P-2026-10-04-21).
- **E-3 Anstellwinkel:** ~~fest mit einem Feld – oder aus der Neigung der Fläche?~~
  **Entschieden** (Manuel, 2026-10-04: „Ja, so bauen (Empfehlung)“): aus der Neigung der Fläche,
  nur so viel wie nötig (Feld: der kleinste Winkel zwischen Achse und Flächennormale, 15°), nur in
  einer Ebene (eine Rundachse) – 6 % mehr Zeit statt 136 % (Richtung frei) oder 540 % (fest
  voreilend auf der Spirale).
- **E-4 Orientierung im Programm:** ~~als Richtungsvektor oder als Rundachsen?~~ Mit E-1
  entschieden: ohne TCPM gehen nur Rundachsen (A, C) – Richtungsvektoren (`A3= B3= C3=`)
  brauchen TRAORI.

### 16.5 Komplexe Freiformteile: Bahn, Werkzeug und Anstellung gemeinsam wählen

Manuel, 2026-10-07: „… eine 5 achs Strategie … die ein komplex Teil in der best möglichen
Art und Weise abbilden kann?“ → „Dann Fang an!“ Das G550-Flankenbeispiel allein belegt
das nicht. Der erste konkrete Schritt ist ein Vergleich am bestehenden 3D-Schlichten.

Heute entscheidet die senkrecht gerechnete Bahnlänge über die Wahl; Anstellung und
Maschinenzeit kommen danach. Das berücksichtigt nicht, ob ein großer Fräser enge
Freiformbereiche erreicht oder welche Rundachsbewegung eine kurze Bahn verlangt.

Geplanter Klickweg:

```text
3D-Schlichtoperation wählen → CAM-Addon → 5-Achs-Schlichten vergleichen …
Werkzeug       Bahn               Anstellung     Zeit       Prüfung
Kugel 12       Zeilen X           um X           –          Fläche nicht erreicht
Kugel 6        entlang Fläche     Richtung frei  …          Kollisionsprüfung offen
…
[Varianten berechnen und prüfen]
[5-Achs-Schlichtvariante übernehmen]  erst nach vollständiger Prüfung
```

**Akzeptanzkriterium:** An der Freiformfläche mit Mulde, Sattel und Erhebung den Vergleich
starten → ungeeignete Fräser und Bahnen werden begründet abgewiesen, die schnellste vollständig
geprüfte Kombination unter den angebotenen Varianten wird rückgängig machbar übernommen.

- Alle Kugelfräser, die bereits als Controller im Job eingerichtet sind; gleiche Grathöhe.
- Zeilen X/Y, Spirale, entlang der Fläche und gleicher Abstand; Anstellung um X/Y oder
  frei mit beiden Kippkomponenten. Kein Zwang, beide Rundachsen ständig zu bewegen.
- Vor der Zeitwahl: Oberflächen-Stichproben, Mindestwinkel zur Kontaktfläche auch zwischen
  Bahnpunkten, erreichbare Maschinenfahrt und Verfahrgrenzen. Dann genaue Kollisionsprüfung
  einschließlich An-/Abfahren, weiterer Joboperationen und Eilgang durch Rohteil.
- Nur innerhalb dieser endlichen Varianten: keine globale Optimalität und keine vollständige
  Oberflächenzertifizierung durch die Stichproben. Gewählte Flächen bleiben heute die von oben
  erreichbaren Flächen der vorhandenen 3D-Strategie; Hinterschnitte und zusätzliche Aufspannungen
  brauchen weitere Arbeit. Das ist der Beginn der Erweiterung für komplexe Teile.

**Gebaut (P-2026-10-07-02, 0.197.0):** `simultan_planung.py` vergleicht eingerichtete
Kugelfräser, fünf Bahnrichtungen und Anstellung um X/Y oder frei. `schlicht_rand.py`
führt die Kugel genau an offenen Flächenrändern; zu große Fräser werden vor Gegenflächen
abgewiesen. `anstellung_frei.py` behält die Richtung, solange der Kontaktwinkel reicht,
sonst folgt sie dem Rand des erlaubten Kegels; die Luftsätze bereiten den nächsten Kontakt vor.
Die gespeicherte Operation erhält `Randgang`, die freie Kippachse und den gewählten Controller.
Der Vergleich berücksichtigt auch FreeCADs abschließenden Rückzug auf die Freifahrhöhe.

**Erster Versuch (P-2026-10-07-02, durch 16.6 ersetzt):** Quader 50 × 40 × 30 → B-Spline-Fläche mit Mulde, Sattel und
Erhebung, D12 schruppen mit 0,3 mm Aufmaß, danach Kugel schlichten. 45 Kombinationen,
Kugel Ø 4/Zeilen X/frei gewinnt: gesamter Job 581,34 s; größte Oberflächenprobe 0,0298 mm,
kleinster Kontaktwinkel 16,03°; 167 Vorschubbewegungen ändern alle fünf Achsen zusammen,
Modellprüfung ohne Befund. [Beispiel und vollständiger Bericht](../beispiele/grob_g550_freiform/README.md).
Übernahme, identische gespeicherte Bahn, Rückgängig und Schutz vor veralteten Eingaben
in FreeCAD 1.1.4 geprüft. Der Mittelpunkt der Kugel bleibt beim Anstellen erhalten.

**Sinnvolle Varianten (P-2026-10-09-04, 0.203.5):** Manuel, 2026-10-09: „Die Durchmesser 4
Variante warum müssen wir die Prüfen??“ → „Ja, mach das so.“ Der Vergleich rechnete jede
Kombination voll durch – am Beispiel 60, davon 58 abgewiesen, 16 min auf 24 Kernen (Befund 4 der
Durchsicht von Codex' Beispiel). Jetzt in Runden (`_runden`): je Kugel, die größte zuerst – mit
den weitesten Zeilen die schnellste, wenn sie überall hinkommt –, drei Stufen: entlang der Fläche
mit den Anstellungen Frei und Frei – ganze Bahn, dann die übrigen Richtungen frei, dann alle
Richtungen mit den festen Anstellungen um X/Y. Die Zulassung (Kugelschnitt am Teil, Maschinenbahn,
Kontaktwinkel, Material, Kollision) läuft nach jeder Runde; die erste zugelassene Variante beendet
den Vergleich, eine Kugel, die den Flächenrand nicht erreicht, wird nicht weiter versucht, und erst
ohne Zulassung kommt die nächste kleinere Kugel. An der Kuppel des Szenarios schneidet „entlang der
Fläche“ 0,036 mm ins Teil – die zweite Stufe findet Zeilen X/Y und Äquidistant frei wie der volle
Vergleich. Der Haken
„Alle Kombinationen vergleichen“ im Dialog rechnet wie bisher alles in einer Runde (`alle=True`
in `simultan_planung.vergleichen` und `simultan_folge.vergleichen`). Die Tabelle zeigt nur die
gerechneten Varianten; am Beispiel zwei Abweisungen am Flächenrand und zwei Ø-4-Varianten mit
demselben Gewinner, die goldenen Referenzen bleiben gleich.

**Rechenzeit (Befund 2026-10-09):** Manuel: „Wir müssen auch noch schauen, dass die Rechenzeit im
Betrieb weniger wird … oder eben mehr CPUs zum Rechnen verwendet werden.“ Das Addon rechnet auf
einem Kern – im ganzen Code gibt es keinen zweiten Prozess und keinen Thread; Codex' 24 Kerne haben
dem Vergleich nichts gebracht, und eine einzige Ø-4-Variante am Freiformbeispiel (50 × 40 mm,
0,02 mm Grat, 550 000 Flächenzellen) braucht hier 30 min. Gemessen mit cProfile an der Kuppel des
Szenarios (20 × 16 mm, Kugel Ø 4, 0,018 mm, eine Variante Zeilen X frei, 181 s auf einem
ausgelasteten Rechner):

| Phase | Zeit | Was darin teuer ist |
| --- | --- | --- |
| Kollision (Zulassung) | 93 s, 51 % | 18 836 Stellen, 12 394 davon genau mit OpenCascade `distToShape` (40 563 Aufrufe, 2,2 ms je Aufruf) – Halter und Spindel nah am Teil, wie bei 5 Achsen immer |
| Bahn (Höhenfeld) | 39 s, 21 % | `_kanten_kugel` 24 s: jede Kante auf alle Rasterstellen ausgebreitet, die sie erreichen kann |
| Materialprüfung | 19 s, 11 % | `deckung` 15 s (Flächenzellen in der Kapsel) |
| Normalen | 15 s, 8 % | ein `distToShape` je Bahnpunkt (`angestellt.normalen`) |
| Kugelschnitt, Maschinenbahn, Winkel, Programm | 15 s, 8 % | – |

Am Freiformbeispiel selbst (eine Ø-4-Variante, 1 707 s auf einem Kern, aus den
Fortschrittsmeldungen des Referenztests alle 30 s): Kollision 12 min (42 %), Material
(`deckung` und `fahren`) 5 min (18 %), Bahn etwa 5 min (17 %), Normalen 4 min (14 %),
Kugelschnitt 2 min (7 %), Maschinenbahn unter einer Minute; Spitzenspeicher 4,6 GB.

Hebel, in der Reihenfolge des Nutzens (Schätzungen, nicht gemessen):

1. **Kollision auf mehrere Prozesse verteilen** – T-006 im Snapshot (Manuel, 2026-10-04: „es
   rechnen nur maximal 5 von meinen 24 Kernen“): die Stationen in Stücke mit Vorlauf an jeder
   Grenze, jeder Prozess lädt die Maschine einmal. **Gebaut (P-2026-10-09-07/-08):**
   `nebenrechner.py` (ein Pool eigener FreeCADCmd-Prozesse) und `kollision.kollision_parallel`.
   Gemessen am Freiformbeispiel auf Manuels Rechner (24 Kerne, 12 physische): die Kollision
   des ganzen Jobs (45 683 Stationen) 306,6 s in einem Prozess → 53,8 s mit 24 Arbeitern,
   55,6 s mit 12 – SMT bringt nichts, und die letzten 10 % der Stationen (das Ende des
   Schlichtens) brauchen ein Viertel der Zeit. Mehr geht nur noch über die Kosten je Stelle
   (Hebel 2).
2. **Halter und Spindel gegen das vernetzte Teil mit numpy** statt OpenCascade – so, wie der
   Materialprüfstand den Kugelschnitt rechnet; die genauen OpenCascade-Aufrufe bleiben nur für
   die Stellen, die die Schätzung nicht entscheidet. Trifft die 51 % direkt. **Gebaut
   (P-2026-10-10-27):** Vorher gezählt – die 51 % waren nicht Halter und Spindel, sondern der
   Kern der Schneide gegen das Teil (9 246 von 10 374 Aufrufen an der Kuppel): Er liegt im
   Vorschub immer 0,05 mm unter der Oberfläche, der Hüllquader entscheidet das nie, und die
   Schrittrechnung fragte an jeder Stelle genau nach. Jetzt `netzabstand.py`: das Teil, die
   Backen und die Bauteile der Maschine einmal vernetzt (Teil 0,01 mm), die Dreiecke in einem
   Gitter; jedes Werkzeugteil als Kapseln (Strecke auf der Werkzeugachse mit Radius, beim
   Kugelfräser genau) – der Abstand Strecke–Dreieck als Vektorrechnung, die Sehnenabweichung
   abgezogen, nie mehr als der wahre Abstand. Kuppel, ein Prozess: 841 statt 10 374 genaue
   Abstände, 3,7 statt 21,4 s; mit 24 Arbeitern 5,0 statt 7,0 s. Ein Schaftfräser am Boden
   gewinnt nichts (die Kapsel reicht unter der Stirn um r zu tief; nach drei vergeblichen
   Versuchen fragt das Paar nur noch OpenCascade).
6. **Gemerkt statt neu gerechnet (P-2026-10-10-29):** Der Vergleich rechnet je Variante und
   Feinheitsstufe dieselbe Form neu: das Netz des Teils (0,001 mm, 13 s je Bahn am
   Freiformbeispiel), das Soll-Höhenfeld des Prüfstands, die Randzüge (`schlicht_rand`, 12 s je
   Bahn, davon 8 s `isInside`). Jetzt gemerkt je Kennung der Form (FreeCADs `hashCode` der
   Körper samt Lage) – Freiform 376 → 243 s bei gleichem Ergebnis. **Nicht genommen:**
   `MeshPart.meshFromShape` vernetzt achtmal schneller als `Shape.tessellate` (gleiche
   Sehnenabweichung, halb so viele Dreiecke), aber die Deckung zählt Flächenzellen am Rand
   anders – an der Kuppel kippte eine Variante. Ein anderes Netz nur mit neuen Referenzen und
   Manuels Ja.
7. **Deckung auf feinem Gitter (P-2026-10-10-30):** Die Flächenzellen gegen die Kapseln in
   Gitterzellen von 0,5 mm statt r – je Gruppe 25 statt 195 Kandidaten –, erst die nahen Kapseln
   (die nächste Bahn), dann alle; die Vierteilung unentschiedener Zellen rechnet so gegen wenige.
   Dieselben Urteile; am Freiformbeispiel 59 → 26 s, der Vergleich 243 → 201 s.
8. **Netzschranke mit Stirnebene (P-2026-10-10-34):** Für Zylinder (Schaft, Hals, Halter,
   Schaftfräser samt Kern) zählt unter und über den Stirnebenen der Abstand zur Ebene – so
   entscheidet der Kern 0,05 mm über dem Boden ohne OpenCascade. Manuels 3-Achs-Testteil:
   „Kollision prüfen“ 21,8 → 9,3 s, genaue Abstände 30 769 → 684, dieselben Befunde.
3. **Varianten und Zwischenlagen parallel** – sie sind unabhängig: mit dem Haken „Alle
   Kombinationen“ und im gemeinsamen Vergleich (drei Lagen → drei Prozesse) sofort ein Vielfaches.
4. **Höhenfeld:** Kanten nur auf die Stellen ausbreiten, die sie unter dem Kugelradius wirklich
   erreichen (heute Kante × alle Stellen ihres Intervalls), `np.maximum.at` durch sortiertes
   `reduceat` ersetzen. **Gebaut anders (P-2026-10-09-11):** `np.maximum.at` kostete
   nichts (0,5 s); teuer war der Gang durch den Speicher – alle Paare einer Zeile auf einmal.
   Jetzt in Blöcken von 8192 Paaren (Cache), Dreiecke zuerst, Ecken und Kanten nur, wo sie höher
   kommen können, und die Zeilen auf den Nebenrechnern: an der Kuppel 60 → 2,6 s für die
   Hüllfläche, der Vergleich einer Variante 131 → 44 s.
5. **`deckung` vektorisieren** (6 s reines Python an der Kuppel). **Gebaut anders
   (P-2026-10-09-12):** Deckung, Kugelschnitt und Normalen in Stücken auf den Nebenrechnern –
   je Zelle, je Prüfstrecke, je Spitze unabhängig; der Kuppelvergleich damit 44 → 23 s.

Stand nach P-2026-10-09-07 bis -12 (Kuppel, eine Variante Ø 12 Zeilen X frei, 24 Kerne):
131 s → 23 s, bitgleiche Bahn. Was bleibt, ist in einem Prozess: `fahren` (Materialstand),
Maschinenbahn, das Programm – und die Kosten je Stelle der Kollision (Hebel 2). Am
Freiformbeispiel (Ø 4, entlang der Fläche, frei): eine Variante 670 → 211 s, die ganze Bahn
1 067 → 209 s (P-2026-10-09-13) – aus den 30 Minuten sind dreieinhalb geworden.


### 16.6 Qualitätsprüfung des Simultanvergleichs (gebaut, P-2026-10-07-03)

Manuel fragt nach allen geltenden Prüfkriterien und beauftragt, die Lücken zu schließen.
Die bisherige Zulassung durch 19 × 19 Proben mit zusätzlicher Toleranz von 0,05 mm
belegt die verlangte Grathöhe nicht; auch `kollision(..., rohteil=True)` liefert für den
angestellten Kugelfräser bisher keinen Materialvergleich. Der Versionscheck für 1.1.4
war bereits mit P-2026-10-02-85 durchgeführt; ein erneuter Versionswechsel liegt nicht vor.

**Akzeptanzkriterium:** Freiformjob wählen → „5-Achs-Schlichten vergleichen“ → nur eine
Variante ohne Abtrags-, Oberflächen-, Eintritts-, Last- oder Kollisionsbefund übernehmen,
dabei die verlangte Grathöhe ohne zusätzliche Toleranz einhalten und Rückgängig erhalten.

Die unabhängige Prüfung verfolgt den Quader nach den vorherigen Operationen; sie prüft
den kontinuierlichen Kugelschnitt, ganze Flächenzellen einschließlich der Ränder,
BRep-Abstand der Schnittstrecken und die tatsächliche Maschineninterpolation. Die
Vernetzungsunsicherheit verbraucht Qualitätsbudget, statt es zu erhöhen. Nicht darstellbare
Rohteile, Hinterschnitte oder fehlende Einsatzwerte bleiben ausdrücklich ungeprüft.
Im Dialog bleibt die Tabelle; „Restprobe“ wird „Restgrenze“, „vollständig geprüft“ wird
„Material und Modellkollision geprüft“. Eingabeschutz umfasst auch Maschine und Halterbibliothek.

**Gebaut:** Materialraster 0,1 mm, unabhängige Vernetzung höchstens 0,001 mm, bei dünnen
Randzellen bis 0,00025 mm. Ganze Dreiecke müssen innerhalb einer konservativ verkleinerten
Kugelkapsel liegen; überlappende Schnitte werden mit unterteilten Zellen geprüft,
unbewiesene Zellen abgewiesen. Zusätzlich genauer BRep-Abstand der vollständigen
Schnittstrecken, tatsächliche Maschinenstellungen und ihre Zwischenstellungen.
Die Herkunft von Eilgang/Freivorschub bleibt auch nach Verdichtung und G1/G93-Umwandlung
erhalten. Ganze Vorschubzüge ohne Abtrag werden unabhängig von der Luftquote abgewiesen.
Die frühere Zugabe von 0,05 mm zur verlangten Grathöhe entfällt.
Fein geprüfte Bahnen werden mit sechs Koordinatenstellen geschrieben, auch Moduloachsen
und bei der Klartext-Übersetzung;
die Glättungstoleranz beträgt höchstens 0,0001 mm. 0,00011 mm bleiben dafür im Qualitätsbudget
reserviert. Der NC-Rücklesetest prüft die ausgeschriebenen Wörter mit Achsnamen,
Vorzeichen und Modulo-Drehrichtung; die alte Rundung auf drei Stellen erzeugte hier
0,0019 mm Einschnitt und sechs offene Flächenzellen.

Der neue optionale Rampenanlauf korrigiert die senkrechten Einfahrten des Beispiel-Schruppens,
mit dem tatsächlichen Werkzeug-Eintauchwinkel und Freivorschub nur im nachgewiesenen Freien.
Alte Schruppjobs behalten ohne diesen Haken ihre bisherige Bahn. Der Simultanvergleich
rechnet feiner und mit eigenem Qualitätsbudget; alte ungeprüfte Schlichtjobs bleiben erhalten.

**Historischer Beleg vor P-2026-10-08-01; aktuelle Werte in 16.9:** 45 Varianten, Kugel Ø 4/entlang der Fläche/frei; ganzer Job
682,84 s. Restgrenze mit Vernetzungsreserve 0,01694 mm bei verlangten 0,02 mm, 550.457
vollständig abgedeckte Flächenzellen, mindestens 16,82° Kontaktwinkel, Last beim Schlichten
2,756 mm² unter ae × ap = 7,5 mm². Achsgrenzen, Modellkollision und 1 mm Warnabstand ohne
Befund; 54.082 Bewegungen im nachgelesenen Siemens-Beispielprogramm. Die gelesene NC-Bahn
erreicht mit Vernetzungs-, Rundungs- und Glättungsreserve 0,01705 mm Restgrenze und eine
konservative BRep-Abstandsuntergrenze von 0,000383 mm, ohne offene Zelle.
Der frühere Sieger „Zeilen X“ fällt an der vollständigen Flächenprüfung durch.

**Historische Referenz und Leistung vor P-2026-10-08-01:** `tests/golden/freiform_simultan.json` hält 41.135 Punkte mit
Werkzeugachsen/Eilgang und 41.463 Maschinenbefehle mit sechs Nachkommastellen, dazu eine Zeitbestmarke
682,84 s (+0,5 %), gemessene Vergleichszeit 1.220,90 s und Python-Spitzenspeicher 401,89 MiB
(je ×2 Budget). Der Referenztest prüft zusätzlich Materialraster 0,05 mm, Übernahme,
identische neu berechnete Bahn/NC-Sätze, Rückgängig und veraltete Eingaben.
Der Vollvergleich benötigt hier 20 min 15 s und nativ 3,65 GiB Prozess-Spitzenspeicher;
die instrumentierte Referenzprüfung dauert länger als der uninstrumentierte Lauf.
Das Szenario rechnet, übernimmt und macht rückgängig; sichtbar auf dem zweiten Bildschirm.
`test_simultan_nc.py` ergänzt die Referenz des tatsächlichen Siemens-Programmtexts und
prüft die nachgelesene Maschinenbahn mit reservierter Glättungs- und Interpolationstoleranz.
Beide Referenzen anschließend ohne Schreibflag verglichen: keine Bahn-/NC-Abweichung,
Maschinenzeit innerhalb +0,5 %, 1.242,78 s und 401,884 MiB unter den Budgets; abschließender
Vergleich mit NC-Reserve ohne Speicherinstrumentierung 754,81 s.
Das belegt die angebotenen Varianten und die eingerichtete Modellmaschine; eine echte
G550 wurde damit nicht betrieben. Hinterschnitte, weitere Aufspannungen und beliebige
Rohteilformen sind weiterhin offen.

**Eichung (P-2026-10-09-03, `tests/test_simultan_eichung.py`):** An der ebenen Fläche mit der
Kugel Ø 4 und Zeilen im genauen Abstand für 0,02 mm (0,564 mm) misst `fahren()` den Kamm richtig
(0,0195 mm im 0,1- und 0,05-mm-Raster). `deckung()` dagegen lehnt diesen Abstand ab: Ihre
Prüfkugel ist um NETZ + SEHNENFEHLER (0,002 mm) kleiner, dazu die Unterteilung der Zellen – sie
nimmt Zeilen bis 0,52 mm an, wenn die Dreiecke höchstens 1 mm groß sind, bis 0,50 bei 2 mm, und
Dreiecke ab 5 mm Kantenlänge nie (auch nicht bei halbem Abstand). Der Vergleich rechnet darum
jede Variante fester mit Grathöhe ÷ 4 (`simultan_planung.py`, `feinheit`): Zeilen 0,28 statt
0,56 mm, am Freiformbeispiel 153 statt 77 Zeilen, das Schlichten 3,0 statt rund 1,7 min.
`simultan_abtrag.bahn_grathoehe` (0,75 · Grathöhe, Zeilen 0,49 mm) ist die an der ebenen
Fläche geeichte Feinheit. **Sie gilt nicht für jedes Teil (P-2026-10-09-14/-15):** Die Kuppel
nimmt 75 % an (Ø 12, 98 → 74 s), die Freiform mit ihrer gewölbten Erhebung lässt bei 75 % 0,026 mm
stehen, bei 50 % bleiben 1 074 Zellen ungedeckt, erst 25 % besteht. Darum rechnet der Vergleich
ohne Angabe in Stufen (`STUFEN`: 75, 50, 25, 12,5 % – dieselbe Variante feiner, wenn nur die
Materialprüfung ablehnt), und das Feld „Bahn gerechnet für“ im Dialog (sichtbar auch als
`BahnGrathoehe` an der Operation) legt die Feinheit fest, wer sie kennt. Offen: `deckung()` für große ebene
Dreiecke (tiefer unterteilen oder die Zellen vor der Prüfung auf 1 mm teilen).

### 16.7 Rohteil/Fertigteil beim Simultanschlichten (gebaut, P-2026-10-07-04)

Manuel: Der Vergleich ist bei vier Achsen deutlich schöner. Dort wird das Rohteil beim
Abfahren abgetragen und am Ende mit Materialfarben über dem Sollteil gezeigt; bei fünf
Achsen blieb bisher wegen der Rundachsbewegung nur der unveränderte transparente Kasten.
Die vorhandene Darstellung und Bedienung werden wiederverwendet: Schieber, „Bahn“ und
„Teil“, am Ende grün/gelb/rot/blau mit der vorhandenen Legende. Die Kugelmitten kommen
aus der tatsächlichen Maschinenkinematik; die Werkzeugspitze darf bei einer angestellten
Kugel nicht als Mitte eines senkrechten Werkzeugs gelesen werden. Ungeeignete
Voroperationen/Hinterschnitte bekommen damit keinen falschen Materialnachweis.

Die vorhandene Oberfläche bleibt gleich:

```text
[Abspielen]  [<]  ======== Schieber ========  [>]
[x] Bahn  [x] Teil
Am Ende bleiben … mm …  Grün: Aufmaß · Gelb: mehr · Rot: Rest · Blau: im Teil
Die Farben zeigen die Materialvorschau; die genaue Grathöhe prüft der Vergleich.
```

**Akzeptanzkriterium:** Den geprüften Freiformjob auf der Maschine öffnen → zum Ende fahren
→ abgetragenes Rohteil mit Materialfarben und Sollteil wie beim 4-Achs-Vergleich sehen,
mit „Teil“/„Bahn“ umschalten und zum Anfang zurückgehen können.

`simultan_restbild` nutzt den vorhandenen Quader-Abspieler und seine Materialfarben mit
0,5-mm-Anzeigeraster; die Kugelmitte kommt aus der Spitze und der tatsächlichen Achse.
Das ist ein Bild, keine zusätzliche Qualitätszulassung oder Erweiterung der allgemeinen
Kollisionsprüfung. Die feinere Material-/NC-Prüfung aus 16.6 bleibt maßgebend.

### 16.8 Anstellung über die ganze Bahn voraussehen (P-2026-10-07-05, qualifiziert mit P-2026-10-08-01)

Manuel fordert eine globale optimale Bearbeitung beliebiger Teile. Physische Erreichbarkeit,
Werkzeuge, Aufspannung und Qualitätsgrenze müssen das Problem begrenzen; geschlossene
Innenräume und nicht erreichbare Hinterschnitte können keine Fräsbahn erhalten. Der bisherige
freie Kandidat hält örtlich seine vorige Richtung, bis der Kontaktwinkel sie verbietet,
ohne spätere Flächenneigungen zu berücksichtigen.

Als zusätzlicher Kandidat wird die ganze Folge gemeinsam geplant: acht Richtungen um den
Kontaktkegel, die bisherige freie Folge, eine vom Ende aus geplante freie Folge und senkrecht,
wo der Kontaktwinkel dies erlaubt. Dynamische Programmierung minimiert die Summe der
Richtungsänderungen in diesem endlichen Graphen; unzulässige End- und Zwischenwinkel sperren
Verbindungen. Das ist keine globale Minimierung der realen Maschinenzeit. Die vollständige
Maschinenzeit entscheidet danach zwischen diesem und den bisherigen Kandidaten; die gleichen
Material-, BRep-, Kinematik-, Last- und Kollisionsprüfungen bleiben die Zulassung.
Eine zusätzliche Tabellenzeile je Werkzeug/Bahnrichtung zeigt „Frei, ganze Bahn“.

Die neue erste Anstellung deckte bei der NC-Nachprüfung eine bislang immer positiv
geschriebene erste Modulo-Rundachsbewegung auf: −39° wurden von der Nullstellung aus
als +321° ausgegeben. Ohne bereits bekannte Rundstellung muss die erste Ausgabe daher
das Vorzeichen des geplanten Winkels berücksichtigen; danach entscheidet der tatsächliche
Winkel davor. Der vollständige Programmtext muss dieselbe Anfahrt wie das Zeitmodell haben.

```text
Werkzeug | Bahnrichtung | Anstellung        | Jobzeit | Befund
Kugel …  | entlang …    | Richtung frei     | …       | …
Kugel …  | entlang …    | Frei, ganze Bahn  | …       | …
```

**Akzeptanzkriterium:** 3D-Schlichten wählen → „5-Achs-Schlichten vergleichen“ → auch
„Frei, ganze Bahn“ mit vollständiger Maschinenzeit und denselben Zulassungsprüfungen
vergleichen, die schnellste zugelassene Variante rückgängig machbar übernehmen und ihre
geplante Anfahrt im NC erhalten können.

**Messung vor der verbesserten Schruppfolge; aktuelle Werte in 16.9:**
Gegen vollständiges Auszählen des Richtungsgraphen geprüft; eine örtliche Sackgasse mit
wechselnder Flächenneigung kostet 68° statt der vorausschauenden 34°. Am komplexen
Freiformbeispiel reduziert die zusätzliche Variante die Maschinenzeit nur von 682,84391 s
auf 682,54859 s. Alle 550.457 Flächenzellen abgedeckt, Restgrenze 0,01694 mm bei 0,02 mm;
Übernahme, Neuberechnung und Rückgängig stimmen mit der geprüften Richtungsfolge überein.
Separate Referenz `tests/golden/freiform_simultan_gesamt.json`, instrumentiert 1288,57 s
und 401,89 MiB Python-Spitzenspeicher, innerhalb der bisherigen Budgets.
Die gespeicherten Achswerte und der tatsächliche Siemens-Export erhalten zusätzlich eine
eigene Referenz; 53.916 Bewegungen, ausgeschriebene Restgrenze mit allen Reserven
0,01704942 mm und BRep-Mindestabstand 0,00038221 mm bei reservierten 0,00036 mm.

### 16.9 Schruppfolge des Freiformbeispiels verbessern (P-2026-10-08-01)

Manuel lehnt die gespeicherte Bahn ausdrücklich ab: im Abspieler „3D-Schruppen T1“,
viele kreuzende Leerwege und Anläufe. Die alte Folge hat 82 getrennte Schnittzüge,
8,28 min Schruppzeit und im 0,25-mm-Prüfraster 30,69 % Luft im normalen Vorschub.
Eine goldene Prüfsumme bestätigt ihre Wiederholbarkeit, keine gute Strategie.

Die Auswahl erfolgt nun nach Rampen und freien Verbindungen. Bereits geräumte Stellen
bekommen keine zusätzliche 0,1-mm-Rampe; auch beim Rampenanlauf gelten die vorhandenen
materialgeprüften Freiwege. Das Beispiel nutzt Manuels ap 25 mm und 3-mm-Zwischenlagen.
1/2/3/4 mm wurden gemeinsam mit dem Schlichtrest untersucht: 3 mm hält die Last beider
Fräser, 4 mm überlastet beide. Mit neu gerechneten Schlichtanfahrten bestehen Eintritt,
Freivorschub und Last auch im halbierten 0,05-mm-Prüfraster. Die vollständige Flächen-,
Modell-/Kollisions- und ausgeschriebene NC-Zulassung beider freien Richtungsfolgen ist
bestanden: 357,52 s Gesamtzeit, 0,01694 mm Restgrenze, alle 550.457 Zellen abgedeckt;
auch im 0,05-mm-Raster, exakter frischer NC-Export und konservative BRep-Untergrenze
0,00038208 mm bei reservierten 0,00036 mm. Alle 60 aktuellen Kombinationen wurden
am neuen Materialstand verglichen: Ø 4/entlang der Fläche/ganze Richtungsfolge bleibt
der schnellste zugelassene Kandidat; Vergleichszeit 1060,40 s. Die separate
instrumentierte Qualitätsprüfung benötigt 1111,21 s und 401,26 MiB Python-Spitze.

Vollständige Ringe und ein Adaptiv-Versuch wurden verworfen: längere Zeit bzw. ein
Freivorschubabtrag. Die Änderung ist eine geprüfte Verbesserung dieses Beispiels und
des Anlaufvergleichs; allgemeine Hinterschnitte, Aufspannungswahl und globale
Optimalität beliebiger Teile bleiben ungelöst.

**Akzeptanzkriterium:** Freiformbeispiel öffnen, „3D-Schruppen T1“ neu berechnen und
abfahren → die geprüfte Bahn bearbeitet dasselbe Rohteil mit weniger Leerwegen und
kürzerer Gesamtzeit, ohne Einschnitt, Abtrag im Eil-/Freivorschub oder unzulässigen
Eintritt und Werkzeuglast.

### 16.10 Schruppen und Schlichten gemeinsam planen (P-2026-10-08-03)

Manuel fordert die globale Bearbeitungsoptimierung erneut. Bislang ist nur das
Schlichten variabel; der feste Materialstand nach dem Schruppen kann den Sieger
bestimmen. Ein kleinerer Schruppaufwand kann den Schlichtanlauf und seine Last
vergrößern. Daher werden beide gemeinsam verglichen, statt die Schruppzeit zuerst
allein zu minimieren.

Der bestehende Dialog erhält eine Wahl für die direkt vorhergehende 3D-Schruppoperation.
Ihr eingerichteter Fräser, ap, ae und Aufmaß bleiben Vorgaben; innerhalb eines sichtbaren
Zwischenlagenbereichs werden alle festgelegten Werte einschließlich der aktuellen
Einstellung mit allen bisherigen Schlichtwerkzeugen/-richtungen/-anstellungen geprüft.
Der Schlichtanlauf beginnt jeweils beim tatsächlichen Material dieser Vorbearbeitung.
Unzulässiges Schruppen weist den gesamten Zweig ab. Die vollständige Maschinenfahrt
samt Werkzeugwechseln entscheidet über die schnellste zugelassene Folge.

```text
[ ] Schruppen mit vergleichen
Zwischenlagen: von [1,0 mm] bis [4,0 mm]
Schritt [0,5 mm]
Zwischenlage | Schlichtwerkzeug | Bahn | Anstellung | Jobzeit | Restgrenze | Prüfung
[Varianten berechnen und prüfen]             [Geprüfte Folge übernehmen]
```

Alle Zweige verwenden Objektansichten; der Vergleich ändert weder Dokument noch
Bibliothek. Übernehmen aktualisiert beide Operationen in einer Transaktion und
vergleicht die neu berechneten Bahnen mit der geprüften Folge. Änderungen an Eingaben,
Maschine oder Werkzeugdaten sperren veraltete Ergebnisse. Abbrechen darf niemals eine
unvollständige Auswahl freigeben.

Duplicate-/FreeCAD-Check: kein gemeinsamer Schrupp-/Schlichtvergleich im Projekt oder
Git-Verlauf. FreeCADs Surface-/Adaptive-Operationen erzeugen einzelne Bahnen; die
vorhandenen Addon-Material-/Maschinen-/Kollisionsprüfer werden weiterverwendet.
Der Suchraum ist endlich und angegeben. Das Ergebnis ist dessen schnellste zugelassene
Folge, kein Nachweis über unbekannte Werkzeuge, andere Aufspannungen oder beliebige
kontinuierliche Bahnen. Räumlicher Materialstand, Zugänglichkeit und Aufspannungsplanung
bleiben weitere erforderliche Teile der allgemeinen Forderung.

**Akzeptanzkriterium:** Schlichtoperation wählen → „5-Achs-Schlichten vergleichen“ →
„Schruppen mit vergleichen“ und den Zwischenlagenbereich wählen → die schnellste
vollständig geprüfte Gesamtfolge aus diesem Bereich gemeinsam übernehmen und mit
Strg+Z beide Operationen auf ihren vorherigen Stand zurücksetzen können.

**Gebaut und geprüft:** Unverändernde verschachtelte Jobansichten, aktueller Wert zusätzlich
zum Bereich, Gesamtzeitvergleich, früh begrenzte Zulassung nach der Bestzeit und gemeinsame
atomare Übernahme. Eingabeschutz erkennt auch noch nicht neu berechnete Schruppänderungen;
der alte reine Pfadvergleich übersah sie. Die neu berechneten Pfade und der tatsächliche
NC-Export stimmen mit dem geprüften Kandidaten überein. Am Standardfräser-Test mit Kuppel
58,61 → 46,47 s, Zwischenlagen 2 statt 1 mm; Raster 0,05 mm, Fehler-Rollback und ein Undo
für beide Schritte bestanden. Frische Referenz ohne Schreibflag: 211,24 s und 240,43 MiB
Python-Spitze. Dialog auf DP-1 geprüft, kompakte Bereichsfelder und beide Knöpfe erreichbar.
Der große Freiformvergleich wird separat archiviert; diese Zahlen sind kein neues Optimum
für beliebige Teile oder Aufspannungen.

### 16.11 Ergebnis der gemeinsamen Freiformplanung übernehmen (P-2026-10-08-04)

Die gemeinsame Planung findet für den großen G550-Job einen weiteren zulässigen
Materialzweig: 3,5-mm-Zwischenlagen statt 3 mm, vollständige Folge 316,63 statt 357,52 s.
Das Schlichten verarbeitet mehr Rest, hält aber mit 6,82 mm² die Grenze von 7,5 mm².
2,5 mm kostet 380,85 s, 4 mm überschreitet beim Schruppen 46,72 statt erlaubten
37,5 mm². Dieselben 550.457 Flächenzellen sind abgedeckt; kein schneller Abtrag,
kein unzulässiger Eintritt und keine Modellkollision. Dies ist zunächst der gemeinsame
Vergleich von vier Zwischenlagen mit beiden freien Anstellungen entlang der Fläche.

Vor Aktualisierung der Beispieldateien mussten beide Richtungsfolgen erneut ihre
Material-/Modell-, feineres-Raster-, Übernahme-/Undo-, NC- und exakten Referenzprüfungen
bestehen. Diese Prüfungen sind abgeschlossen. Der zusätzliche Vergleich aller 60
Schlichtkombinationen am 3,5-mm-Materialstand bestätigt den Sieger in 982,09 s;
örtliche Folge 317,17 s, ganze Richtungsfolge 316,63 s. Schruppen 2,16 statt 2,86 min;
die Last im zusätzlichen 0,05-mm-Raster beträgt 37,3222 mm² unter 37,5 mm².
Die feine Vorbearbeitung ist jetzt ausdrücklich Teil der Qualitätsprüfung.

Die gespeicherten NC-Exporte haben 45.170 bzw. 45.682 Bewegungen, keine offene
Flächenzelle und keinen schnellen Abtrag; BRep-Untergrenze 0,00038270 mm bei reservierten
0,00036 mm. Beide frisch geladenen tatsächlichen Exporte sind ohne Schreibflag exakt
gegen die neuen Referenzen geprüft. Instrumentierte Qualitätsprüfung der ganzen Folge:
1066,58 s und 401,22 MiB Python-Spitze. Die vorherigen Bestmarken bleiben im lokalen
Archiv nachvollziehbar. Maschinenansicht/-stellung und persönliche Bibliothek unverändert.
Das Ergebnis gilt für die untersuchten Zweige; räumlicher Materialstand, Hinterschnitte
und zusätzliche Aufspannungen sind damit weiterhin nicht gelöst.

**Akzeptanzkriterium:** Freiformbeispiel neu berechnen und abfahren → der gemeinsame
Schrupp-/Schlichtjob mit 3,5-mm-Zwischenlagen erreicht die kürzere geprüfte Gesamtzeit,
bei unveränderten Werkzeug-, Qualitäts- und Lastgrenzen und identischer geprüfter NC-Bahn.


### 16.12 Räumlicher Materialstand zwischen 3+2-Richtungen (P-2026-10-08-05)

Manuel verlangt Weiterarbeit bis zur allgemeinen Gesamtplanung. Die bisherige
Materialübernahme zwischen geschwenkten Ebenen schneidet Höhenfelder ineinander:
Eine Säule kennt nur Boden und Oberkante. Ein seitlicher Schnitt unter einem
Überhang darf aber Material oberhalb und unterhalb stehen lassen. Solche Hohlräume
müssen für die nächste Richtung erhalten bleiben.

Der neue Kern speichert mehrere getrennte Z-Abschnitte je XY-Strahl. Die Abschnitte
des tatsächlichen Rohteilkörpers stammen blockweise aus FreeCADs öffentlicher
BRep-Schnitt-API, ohne Ersatz des Körpers durch seinen Begrenzungsquader.
Kugelbewegungen und endliche Schaftfräser mit fester, beliebiger Richtung schneiden
kontinuierliche Intervalle; eine neue 3+2-Ebene liest den gemeinsamen Rest in ihrem
Koordinatensystem. Schneidenlänge, Rohteilgeometrie, Ebene und tatsächliche Pfade gehören
zur Kennung. Nicht unterstützte Werkzeugformen oder wechselnde Achsen erhalten
konservativ das ursprüngliche Rohteil statt erfundener Freiräume.

Duplicate-/FreeCAD-Check: kein mehrschichtiger räumlicher Materialstand im Projekt;
`materialstand._von_oben_in_der_ebene` verwendet bisher Höhenfelder. FreeCADs native
`Shape.common` mit senkrechten Strahlen liefert die getrennten BRep-Abschnitte; sein
vorhandener Simulator stellt die Fräser im Python-Ablauf mit fester Z-Richtung.
Vorprobe: 320 Strahlen durch einen Körper mit Seitenhöhlung liefern 480 Abschnitte,
bei x/y 0,5 getrennt Z 0…5 und 11…18.

Das XY-Raster bleibt ein Materialmodell mit ausgewiesener Auflösung. Die vorhandene
feine Simultan-/NC-Qualitätszulassung wird dadurch nicht ersetzt. Kontinuierliches
Umorientieren des Schaftfräsers und automatische Aufspannungswahl sind weitere Schritte.

**Akzeptanzkriterium:** Nach einer seitlichen 3+2-Bearbeitung eine weitere geschwenkte
Ebene anlegen → der Materialstand erkennt den geräumten Hohlraum und erhält das Dach
und den Boden darüber bzw. darunter, auch nach Ändern der Schneidenlänge und Neuberechnen.


**Gebaut und geprüft:** BRep-Abschnitte blockweise ohne Vernetzung des Rohteils,
kontinuierliche gerichtete Zylinder- und Kugelschnitte, endliche Schneidenlänge und
atomare unabhängige Materialzweige. Beide Sweeps gegen native BRep-Boolean-Sweeps
und der Zylinder zusätzlich gegen dichte unabhängige Zeitstellungen geprüft.
Im echten 3+2-Job liegt die nächste Wand bei X 40 mm: vorher falsch X 20,75,
jetzt konservativ X 39,5 bei 0,5-mm-XY-Raster und 0,25-mm-Höhenschritt.
Dach und Boden bleiben erhalten. Schneidenlänge, aktive Vorgänger und veränderte
Rohteilgeometrie invalidieren den Stand. Frische Referenz ohne Schreibflag:
46,46 s und 218,32 MiB Python-Spitze, innerhalb 120 s / 250 MiB.
Vorhandene 3+2- und Sprachprüfung bestanden; der ursprüngliche G550-NC-Export
bleibt exakt. Diese Materialübernahme ist keine neue Grathöhenzulassung für beliebige
Simultanflächen; dafür bleiben die bestehenden feineren Modell-/NC-Prüfungen maßgebend.


**Maschinenweite Vorgabe von Manuel (2026-10-08):** Alle Strategien müssen die
gewählte eingelesene Maschine verwenden, einschließlich ihrer Achsanordnung,
Verfahrwege und tatsächlichen Schwenkbereiche. Erreichbare Richtungen werden daraus
abgeleitet; unerreichbare Bereiche werden mit Grund ausgelassen und ausdrücklich
als unbearbeitet ausgewiesen. Sie zählen niemals als abgetragen oder als fertiges
Teil. Die folgende Zugänglichkeits-/Gesamtplanung darf keine G550-Vorgaben festlegen.


### 16.13 Gewählte Maschine und ihre Grenzen verbindlich verwenden (P-2026-10-08-06)

Manuel fordert maschinenneutrale Strategien aus den tatsächlichen Achsen und
Schwenkbereichen, mit ausdrücklich unbearbeiteten nicht erreichbaren Bereichen.
Der bestehende Schwenkdialog überspringt jedoch eine Maschine mit weniger als zwei
Rundachsen und kann dann eine andere offene Maschine oder einen fiktiven A/C-Tisch
verwenden. Eine 3-Achs-Fräse kann ihre feste Spindelrichtung bearbeiten; eine
4-Achs-Maschine nur ihre tatsächlich erreichbaren Richtungen. Beide dürfen keine
zusätzlichen Rundachsen erhalten.

Die gewählte/gespeicherte Maschine bleibt verbindlich. Ohne Zuordnung kommt nur
eine eindeutig einzelne offene Maschine in Frage; fehlt sie oder ist die Definition
unlesbar, bleibt Übernehmen gesperrt. Rundachsen samt eingelesenen Grenzen werden
im Dialog gezeigt. Eine feste passende Spindelrichtung braucht keine Schwenkbewegung;
andere Richtungen werden mit Grund abgewiesen. Neigung/Richtung beschreiben die
Werkzeugrichtung im Job, nicht ein pauschales Maschinenlimit; die volle Kugel ist
0…180° möglich, die reale Achskette und ihre Grenzen entscheiden über die Zulassung.

```text
Maschine: [tatsächlich dem Job zugeordnete Maschine]
Rundachsen: [A von … bis … / B …] oder [Feste Spindelrichtung]
Fläche / Werkzeugrichtung wählen
[Erreichbar ohne Schwenken / Erreichbar mit … / Nicht erreichbar: …]
[OK nur bei zugelassener Richtung]
```

Duplicate-/FreeCAD-Check: der Ausschluss `len(rundachsen) >= 2` ist weiterhin im
aktuellen Helper; kein verbindlicher Mehrmaschinen-Test. Die vorhandene Achskette,
Grenzen und inverse Kinematik werden verwendet, keine Maschinenannahmen neu gebaut.

**Akzeptanzkriterium:** Job mit gewählter 3-/4-/5-Achs-Maschine bei zusätzlich offener
anderer Maschine öffnen → der Schwenkdialog behält die Jobmaschine, zeigt deren echte
Rundachsen/Grenzen und erlaubt ausschließlich mit ihr erreichbare Richtungen.

Ohne positionierende Rundachsen schreibt ein nur anders ausgerichteter CAM-Bezug
seine realen XYZ-Punkte ohne Schwenkzyklus und ohne erfundenen Z-Schwenkanlauf.
Eine passende bereits waagerechte Richtung verwendet den Grundjob.


**Gebaut und geprüft:** Native Gegenprobe bestätigt zuvor die unerlaubte Ersatzwahl
G550 statt gespeicherter 3-Achs-Fräse. Jetzt bleibt die echte Zuordnung auch mit
0/1 Rundachsen erhalten; fehlende oder mehrdeutige Zuordnung gesperrt. Alle sechs
Beispielmaschinen samt realen Richtungen/Grenzen geprüft. Neuer und bisheriger
vollständiger Dialog auf DP-1 OK; Anschlagänderung vor OK wirksam, kein halber Job.
Echter 3-Achs-Ebenenjob mit Standardfräser schreibt nur transformierte XYZ, Siemens
und LinuxCNC nachgelesen; der bisherige G550-Export bleibt exakt referenzgleich.
Das alte GUI-Szenario verwendete bloß generische Maschineninformationen und ein
festes falsches NC-Vorzeichen; alter und neuer Abschnittsexport waren bytegleich.
Die Prüfung liest jetzt reale Definition, NC-Drehsinne und das ganze Programm.
Automatische Zugänglichkeit und unbearbeitete Teilbereiche sind weiterhin der nächste
Baustein; die jetzige Freigabe prüft eine einzelne vorgegebene Werkzeugrichtung.


### 16.14 Tatsächliches Werkzeug für den Maschinenzugang (P-2026-10-08-07)

Die Jobmaschine bleibt nun verbindlich. Ihr Richtungsplaner verwendete jedoch die
Z-Achse der Aufnahme und im Dialog grundsätzlich Aufnahme/Nummer 1, ohne die
gewählte Einspannung. Bei einem gewinkelten Halter stimmt das nicht mit der echten
Werkzeugachse überein. Native Gegenprobe an der 3-Achs-Fräse: Richtungsplaner Z,
Vorwärtskinematik X, 90° Unterschied.

Die Werkzeugrichtung verwendet dieselbe Einspannung mit Halterlage wie die
Kinematik. Im Schwenkdialog steht das tatsächlich gewählte Jobwerkzeug; seine Nummer
bestimmt die Aufnahme, seine reale Länge und Halterlage gehen in den Maschinenzugang
ein. Wechseln des Werkzeugs rechnet die Freigabe neu. Vor OK werden aktuelle Werkzeug-,
Halter- und Maschinenwerte gelesen. Ohne Jobwerkzeug ist die Richtung nicht freigegeben.
Das ist die Voraussetzung für den folgenden Bericht über bearbeitbare und ausgelassene
Bereiche; ein nomineller Spindelzugang darf kein falscher Werkzeugzugang sein.

```text
Maschine: [Jobmaschine]
Werkzeug: [T… tatsächlich eingespanntes Werkzeug ▼]
Positionierende Rundachsen: [eingelesene Grenzen / feste Spindelrichtung]
Fläche / Werkzeugrichtung
[Erreichbar mit diesem Werkzeug / nicht erreichbar]
```

Duplicate-Check: vorhandene Einspannung kennt ihre Achse, aber `Maschine.richtung`
verwendet sie nicht; keine Werkzeugwahl im Schwenkdialog. Die bestehende öffentliche
FreeCAD-Kinematik und Addon-Einspannung werden verwendet, ohne neue Winkelannahmen.

**Akzeptanzkriterium:** Im Job ein gerades und ein gewinkelt eingespanntes Werkzeug
wählen → der Schwenkdialog verwendet jeweils dessen Aufnahme und tatsächliche Achse,
zeigt entsprechend verschiedene erreichbare Richtungen und prüft vor OK die aktuelle
Halterlage statt der nominellen Spindelrichtung.


**Gebaut und geprüft:** Alle sechs Maschinenarten mit 0/45/90°-Einspannung und
Achsenstellungen 0/20° gegen die tatsächliche Vorwärtskinematik geprüft. GUI auf
DP-1: Werkzeugwechsel, aktuelle externe Halteränderung, echte seitliche Ebene ohne
fiktive Rundachse, Job-Undo, getrennte Revolverplätze 1/8 und fehlendes Werkzeug.
Beim Job-Undo bleibt ein unbenutzter nativer Rohteilklon übrig; der Ebenenjob selbst
wird entfernt, diese Ressourcenbereinigung ist gesondert offen. Sprachprüfung und
frischer G550-Export referenzgleich, persönliche Werkzeugbibliothek unverändert.

### 16.15 Simultan mit tatsächlichen Maschinenachsen (P-2026-10-08-08)

Native Gegenprobe: Ein Job mit 30°-Werkzeugrichtung an der festen 3-Achs-Fräse
schreibt dieselbe senkrechte Bahn ohne Hinweis. Im Kern wurden Maschinen mit
weniger als zwei Rundachsen pauschal auf senkrecht zurückgesetzt; nach einem
Richtungs-/Grenzfehler machte der Postprozessor dieselbe Ersatzbewegung.
Das widerspricht Manuels Vorgabe, nicht erreichbare Bearbeitung auszulassen.

Die tatsächliche Richtungsauflösung entscheidet auch mit null oder einer
Rundachse. Eine feste Werkzeugrichtung wird in ihre echten XYZ-Punkte umgerechnet,
ohne erfundenen Schwenkanlauf. Ein Rundkreis mit einer realen Rundachse ist möglich,
wenn jede Richtung und deren Anschläge passen. Nicht erreichbare Operationen
werden ausdrücklich als unbearbeitet ausgelassen, niemals senkrecht ersetzt.
Der Gesamtvergleich nimmt ebenfalls keine bestimmte Rundachsenzahl an; nur
vollständig zugelassene Varianten sind weiterhin übernehmbar. Das Auslassen
sicher getrennt fahrbarer Teilbereiche folgt als eigener Schritt.

```text
Programm / Maschinenprüfung
[Operation]: [erreichbar mit tatsächlichen Achsen]
[Operation]: unbearbeitet – ausgelassen: [Richtung / eingelesener Anschlag]
```

Duplicate-Check: Das senkrechte Ausweichen stammt aus dem bestehenden Simultan-
Adapter, ist kein vorhandenes maschinenbezogenes Auslassen. FreeCAD stellt die
Kinematik bereit; ihr gelesener Achsbaum und die vorhandene Richtungsauflösung
werden verwendet, keine pauschalen Maschinenmodelle.

**Akzeptanzkriterium:** Dieselbe Operation an einer festen, einer einrundachsigen
und einer zweirundachsigen Maschine prüfen und exportieren → jede erreichbare
Werkzeugrichtung wird mit deren echten Achsen gefahren, eine unerreichbare
Operation bleibt ausdrücklich unbearbeitet und erzeugt keine senkrechte Ersatzbahn.


**Gebaut und geprüft:** Alle sechs Maschinen mit tatsächlichen 0/1/2 Rundachsen
und Kugelmitte gegen unabhängige Vorwärtskinematik; einzelne C-Achse mit gewinkelter
Einspannung fährt tatsächlich, gelesener ±2°-Anschlag sperrt die angeforderte 30°-Lage.
Keine fiktiven Achsen, keine senkrechte Ersatzbahn, Quelldaten unverändert.
2,11 s / 33,80 MiB Python für die kleine Richtungsgegenprobe; kein Zerspanungsbenchmark.
Bestehender Simultankern und native Anstellbahn bestanden, G550-Kaltexport exakt
referenzgleich. GUI auf DP-1 mit echter Freiformoperation: unbearbeitet sichtbar,
null Bewegungssätze bei ausgelassener Operation; 3-/4-Achs-Zuordnung bleibt erhalten.
Die erste GUI-Probe hatte eine ebene statt einer Freiformfläche und damit keine
Schnittbahn; der abschließende Lauf verwendet eine echte gewölbte Fläche.

### 16.16 Ausgelassene Ebenen bleiben im Material (P-2026-10-08-09)

Native Gegenprobe: Eine gespeicherte 30°-Stellung gilt im gemeinsamen Ebenenhelper
weiterhin als passend, obwohl die gelesene A-Grenze inzwischen nur ±10° beträgt.
Der Postprozessor darf diese Fläche nicht bearbeiten. Auch der Materialstand darf
ihre nicht gefahrenen Schnitte nicht als Abtrag der Vorbearbeitung übernehmen.

Jede gespeicherte und neu gelöste Rundstellung muss die aktuellen Anschläge
bestehen. Die gemeinsame Ausgabe lässt einen nicht mehr erreichbaren Ebenenbereich
mit allen darin verwendeten Strategien ausdrücklich unbearbeitet aus; andere
Ebenen bleiben im Programm. Der räumliche Rest prüft dieselbe tatsächliche
Jobmaschine und Einspannung, lässt diesen Bereich stehen und invalidiert seinen
Cache bei geänderter Erreichbarkeit. Ohne zugewiesene Maschine bleibt der bisherige
rein geometrische Materialentwurf bestehen; eine nicht lesbare tatsächliche
Zuordnung erlaubt keinen angenommenen Abtrag.

```text
Programm / Bereich
Ebene 1: [erreichbare Operationen]
Ebene 2: unbearbeitet – ausgelassen: [eingelesene Schwenkgrenzen]
Ebene 3: [erreichbare Operationen]
Restmaterial: Ebene 2 bleibt stehen
```

Duplicate-Check: Der Ebenenhelper existiert, prüft bei gespeicherter passender
Richtung aber keine Grenzen; der räumliche Replay kennt bisher keine Maschinen-
zuordnung. FreeCAD liefert die tatsächliche Gelenkkinematik; diese wird benutzt.

**Akzeptanzkriterium:** Mehrere Ebenen mit beliebigen Strategien anlegen, dann einen
Schwenkbereich so begrenzen, dass eine Ebene nicht mehr erreichbar ist → das Programm
lässt nur diesen Ebenenbereich ausdrücklich unbearbeitet aus, erreichbare Ebenen
bleiben fahrbar und der Vergleich zum Fertigteil zeigt sein Material weiterhin.


**Gebaut und geprüft:** Native Gegenprobe bestätigt die zuvor wiederverwendete
30°-Stellung trotz ±10°-Anschlag. Jetzt gespeicherte und neu gelöste Stellung
innerhalb echter Grenzen; unerreichbare Ebene ohne Schwenk-/Schnittsätze, andere
Ebene weiterhin im Siemens-/LinuxCNC-Programm und nachgelesen. Räumlicher Rest
behält 4318,352 mm³ ausgelassenes Material, Dach/Boden bleiben; aktueller Anschlag
invalidiert den Cache, erweiterter Anschlag stellt den geometrischen Abtrag wieder
her, fehlende tatsächliche Maschinendatei rechnet keinen Abtrag. 48,95 s / 230,58 MiB
Python kalt (Gegenprobe des Materialkerns, kein Zerspanungsvorschlag). Bestehender
Raumkern referenzgleich; bestehende Ebenenprüfung mit echter Maschine und ihrer
DIN-Vorzugsausgabe bestanden. GUI DP-1: beide nativen Materialmodelle, wirklich
ausgelassenes Material separat rot und expliziter Programmhinweis bei weiter
enthaltener anderer Ebene. Erste Aufnahme zeigte die alte aktive Ansicht; jetzt
die eigene 3D-View erfasst und das MDI-Vergleichsfenster sichtbar ausgewählt.
Sprachprüfung und G550-Kaltexport referenzgleich.

### 16.17 Gemeinsame Bahnprüfung für tatsächliche Achsen (P-2026-10-08-10)

Native Gegenprobe: Ein gewöhnlicher Abschnitt mit A30 wird für eine tatsächlich
C-positionierende Maschine unverändert und ohne Hinweis ausgegeben. Einzelne
Strategien dürfen sich nicht auf die Prüfung der Simultan- oder Ebenenart verlassen.

Die gemeinsame Ausgabe prüft die tatsächlich gefahrenen Sätze gegen dieselbe
Kinematik und die eingelesenen Achsgrenzen wie „Auf der Maschine prüfen“. Nicht
vorhandene Rundachsen und unerreichbare Stellungen lassen den zugehörigen Bereich
als ganze Operation ausdrücklich unbearbeitet aus. Andere Operationen bleiben.
Kreisbögen prüfen auch die inneren Achsextrema. Dieselbe Entscheidung geht in den
Materialstand ein; ein nicht ausgegebener Schnitt erzeugt keinen angenommenen
Abtrag. Für gültige Bahnen bleibt die Ausgabe identisch. Feinere Unterteilung einer
zusammenhängenden Schnittbahn verlangt eigene qualifizierte An- und Rückzüge.

```text
Operation 1: [gültige vorhandene Achsen und Stellungen]
Operation 2: unbearbeitet – ausgelassen: [fremde Achse / Verfahrgrenze]
Rest: Bereich der Operation 2 bleibt stehen
```

Duplicate-Check: Gemeinsame Reichweitenprüfung ist vorhanden, der normale Export
wendet sie bislang nicht an. Ihre vorhandenen Bahn-/Kreis- und Bereichskerne werden
wiederverwendet; kein eigener Maschinen- oder Bogenersatz.

**Akzeptanzkriterium:** Gewöhnliche, Rundum- und Simultanoperationen mit einer
zugeordneten Maschine exportieren → ausschließlich vorhandene, innerhalb der
aktuellen Grenzen liegende Achsbewegungen werden geschrieben, andere Operationen
bleiben ausdrücklich unbearbeitet und ihr Material wird nicht als entfernt gezählt.


**Gebaut und geprüft:** Alle sechs Maschinen, gültige gewöhnliche Bahnen unverändert,
fremde Rundachse als unbearbeitet ausgelassen; reale C-Grenze, lineare Achse und
innere Kreisextrema geprüft. Absolute/relative Rundbewegungen werden schon vor
bekannter XYZ-Lage gegen die gelesenen Grenzen geprüft. Jobzuordnung wird auch im
direkten Export benutzt; unlesbare Zuordnung erlaubt keine gedachte Bewegung.
Export/Abspieler/Materialfolge teilen dieselbe Prüfung. Ausgelassene Operationen
fehlen im Abspieler und senken kein Material. Materialnachrechnen verwendet denselben
Zugangsschlüssel; bestehende Material-/Ebenen-/Simultanprüfungen bestanden.
GUI DP-1 mit zwei gewöhnlichen Bereichen: fehlende A-Achse sichtbar ausgelassen,
anderer Bereich im Programm und Abspieler. G550-Kaltexport exakt referenzgleich.
Gemeinsame Schrupp-/Schlichtfolge einschließlich goldenem NC, feiner Zulassung,
Übernahme/Undo/Abbruch unverändert: 46,470 s Bearbeitung, 6181 NC-Sätze; Rechnung
213,721 s / 240,444 MiB Python, Referenz 210,395 s / 240,434 MiB. Keine neue
Referenz geschrieben. Granularität bleibt ganze Operation/Ebene; automatische
sichere Teilbahnunterteilung und allgemeine kontinuierliche Materialfolge offen.

### 16.18 Getrennte Simultanschnittzüge (P-2026-10-08-11)

Manuel beauftragt das Weiterbauen der Teilbereiche. Heute verwirft bereits ein
unerreichbarer Schnittzug alle anderen Schnittzüge derselben Operation. Künftig
bleiben vollständig erreichbare Züge zwischen vorhandenen Eilgängen erhalten.
Ein Zug mit einer unerreichbaren Stelle bleibt vollständig unbearbeitet; es wird
keine neue Einfahrt mitten im Material erfunden. Neu entstehende Verbindungen
zwischen den vorhandenen Rückzugspunkten müssen reale Achsgrenzen und die bestehende
kontinuierliche BRep-Kollisionsprüfung gegen das ganze ursprüngliche Rohteil,
Werkzeug, Halter, Spannung und Maschinenmodell bestehen. Fehlt eine sichere
Verbindung, gibt es weiterhin keine Teilbahnfreigabe. Der Materialvergleich spielt
die tatsächlich ausgegebene Bahn ab; fehlende Schnitte bleiben stehen. Ein
Teilprogramm gilt weiterhin nicht als vollständig qualifizierte Fertigbearbeitung.

```text
Programm / Abfahren
3D-Schlichten: 2 von 3 Schnittzügen erreichbar
Unbearbeitet: Schnittzug 2 – A außerhalb des eingelesenen Bereichs
Rohteil / Fertigteil: ausgelassenes Material bleibt farbig sichtbar
```

Duplicate-Check: `git log -S 'Teilbereiche' -- camaddon` enthält keine fertige
Unterteilung; vorhandene Simultanadapter werfen beim ersten Richtungsfehler ab.
Native FreeCAD Surface/Waterline liefern Bahn und Höhen, aber keine maschinenbezogene
Teilbereichsfreigabe. Verwendet werden die vorhandenen Kinematik-, Bereichs- und
Kollisionskerne; keine FreeCAD-Datei wird verändert.

**Akzeptanzkriterium:** Eine Simultanoperation mit mehreren getrennten Schnittzügen
an einer Maschine mit begrenztem Schwenkbereich exportieren und abfahren → erreichbare
Züge bleiben enthalten, unerreichbare Züge sind mit Grund ausdrücklich unbearbeitet,
jede neue Verbindung ist geprüft und ihr fehlender Abtrag bleibt im Materialbild stehen.

**Gebaut und geprüft:** Drei getrennte native Kugelschnittzüge: erster und dritter
bleiben, der mittlere ist ausdrücklich unbearbeitet; tatsächliche NC nachgelesen,
Quelle unverändert, Materialrest 11,2 statt 10 mm im mittleren Zug. Unabhängiges
0,05-mm-Materialraster: kein Eil-/Schnellvorschubabtrag, keine Überlast oder Verletzung
des Fertigteils; BRep-Kollision bestanden. Ein Hindernis nur im neuen Zwischenweg
sperrt das Teilprogramm. Modaler Vorschub aus ausgelassenem Zug bleibt wirksam.
Alle sechs gelesenen Maschinen, bei den zweirundachsigen auch eine wirklich drehende
Verbindung; TCPM darf keine ausgelassenen Schnitte wieder einführen. Der vorhandene
vollständige Optimierer lehnt Teilprogramme ab, statt sie als schnellere Fertigbahn
zu bewerten. Ganze nicht trennbare Züge bleiben konservativ aus; allgemeine Einfahrten
mitten im Material und kontinuierlicher räumlicher Materialstand bleiben offen.

G550-Gegenprobe: Die flache Aufspannung berührt auf der neuen Verbindung Z-Schlitten
und Rundtisch; auch zusätzliche Höhe reicht nicht. Mit der vorhandenen qualifizierten
Winkelaufnahme besteht dieselbe Prüfung. Die Sperre wurde nicht abgeschwächt (B-015).
Die ältere Richtungsprobe lag mit 45°-Drehwerkzeug außerhalb X1; jetzt stammen ihre
Punkte aus wirklichen mittleren Linearstellungen statt außerhalb des Verfahrwegs.

Teilbahnreferenz: acht NC-Bewegungen, SHA
`972d7fdb8bc5bafccdceeb7b1e51048f2078ccbbaed13b93cfc22b9fc00442c4`,
10,717 s Bearbeitung; Rechnung etwa 13,5 s / 44,45 MiB Python, mit Zeit-/Speichergrenzen.
Goldene gemeinsame Folge exakt unverändert: 6181 NC-Bewegungen, 46,470163 s;
212,256 s / 240,438 MiB Python gegenüber 210,395 s / 240,434 MiB Referenz.
Feine Zulassung, Übernahme/Undo/Abbruch und G550-Kaltexport bestanden, keine bestehende
Referenz neu geschrieben. GUI DP-1: Programmgrund, beide tatsächlichen Schnittzüge,
ausgelassener Rest und Zurückspulen. Zunächst 0,05 mm Rest unter der vorhandenen
grünen Vorschaugrenze; die abschließende Gegenprobe mit 1,2 mm Rest macht ihn sichtbar.
Die Materialfarben selbst wurden nicht verändert. Prüfbelege:
`../../ergebnisse/teilbereiche-2026-10-08/`; Manuels Verständlichkeitsprüfung steht aus.

### 16.19 Räumlicher Rest nach Simultanbewegungen (P-2026-10-08-12)

Heute fällt der gemeinsame räumliche Materialstand bei jedem Simultanvorgänger
auf das ursprüngliche Rohteil zurück. Auch tatsächlich ausgegebene und erreichbare
Schnitte fehlen dann als Vorbearbeitung der nächsten Ebene. Künftig werden ihre
wirklichen NC-Achsstellungen in den gemeinsamen Grundjob zurückgerechnet, einschließlich
Zwischenstellungen. Kugel und endliche zylindrische Schneide bleiben räumliche Körper.
Kurze Schwenksegmente verwenden einen nach innen verkleinerten Sweep mit berechneter
Bewegungsschranke; unbekannte Daten, Eilgangabtrag und überschrittene Ressourcenbudgets
dürfen weiterhin keine Freigabe eines vermeintlich leeren Raums erzeugen.
Ausgelassene Züge erzeugen keinen Abtrag. Der Cache berücksichtigt das tatsächliche
ausgegebene Teilprogramm und die wirksame Maschinenkinematik. Das XY-Strahlraster
bleibt eine Näherung; der Replay ersetzt keine genaue BRep-Zulassung der Fertigbahn.

```text
Vorbereitung der nächsten Ebene
Materialstand: tatsächliche vorherige NC-Bahnen
[Schneidenkörper während der Werkzeugschwenkung]
Unbearbeitete Züge: [bleiben im Rohteil]
Unbekannte / unsichere Bewegung: [ursprüngliches Rohteil verwenden]
```

Duplicate-Check: Der bisherige Raumkern hat feste gerichtete Sweeps, aber verwirft
Simultanoperationen. Native CAM-Simulatoren rechnen eigene XYZ-/Werkzeugpfade;
der vorhandene Addon-Kinematikbaum bleibt die Quelle für die Maschinenbewegung.
Keine FreeCAD-Dateien oder persönlichen Werkzeugdaten werden geändert.

**Akzeptanzkriterium:** Nach einer Simultanvorbearbeitung eine weitere 3+2-Ebene
anlegen → der Materialstand übernimmt ausschließlich die wirklich gefahrenen
räumlichen Schnitte samt endlicher Schneide, lässt ausgelassene Bereiche stehen
und täuscht bei unsicherer Bewegung keinen freien Raum vor.


**Gebaut und geprüft:** Räumlicher Replay der wirklich ausgegebenen NC mit den
beiden gelesenen Maschinenzweigen, Werkzeugaufnahme, Einspannung und Jobnullpunkt.
Originaler Eilgang bleibt auch nach G93-Verdichtung erkennbar. Eine berechnete
Bewegungsschranke erodiert Vorschubsweeps und erweitert Eilganghüllen; unsichere
Geometrie, unbekannte Achsstellungen, Abbruch oder Ressourcenlimit veröffentlichen
keinen halben Materialstand. Cache berücksichtigt tatsächliche NC, Herkunft und
Kinematikzustand. Die Grenzen werden nicht aufgeweicht und es gibt keine
G550-Sonderformel.

Native Gegenprobe mit altem Raumkern: keine Übernahme eines Simultanvorgängers.
Jetzt behalten zwei erreichbare Kugelschnittzüge ihren Abtrag, der mittlere
unerreichbare Zug bleibt mit 1,2 mm Rest stehen; geänderte Richtungen ändern den
Cache. Wirklich bewegte endliche D12-Schneide am Hohlraum erhält fernes Dach und
Boden. Unabhängige FK/Randkörperprobe über Zwischenstellungen und native
BRep-Gegenprobe: innere Sweeps enthalten, äußere Hüllen umfassen den Körper.
Dieselbe Bewegungsschranke an allen sechs gelesenen Bauarten, auch fester Spindel
und Drehmaschine. Native Flankenoperation als Vorgänger der nächsten Ebene
integriert. Identische Schneidenfahrt als Eilgang gesperrt; Abbruch/Budget geprüft.

Neue feste Referenz: 91 Sweeps, zusätzliche Bewegungsschranke höchstens
0,033371 mm, Rest 10721,318696 mm³ mit vier statt zwei Strahlintervallen; SHA
`bc94ec4b42a5379f90b1d628ccea6cd0d19764e9eed8b457704df703bbab7709`.
Rechnung zuletzt 44,515 s / 231,632 MiB Python gegenüber 49,941 s / 231,715 MiB Referenz;
Zeit-/Speichergrenzen bestanden. Bestehende feste Materialreferenz unverändert.
GUI auf DP-1, tatsächlicher Fensterrahmen 0/56/1280/996: ursprünglicher Hohlraum
und Material nach bewegter Schneide. Zunächst verdeckte die ungeschnittene Vorderseite
den Abtrag; der abschließende Schnitt durch die Vorschau zeigt Kanal, Dach und Boden.

Die alte Anstellprobe lag mit nur geschätzten 24 mm Werkzeuglänge außerhalb Z1;
auch unverändertes 0.202.0 verwirft sie. Probe mit festgelegter 50-mm-Gesamtlänge
besteht, tatsächliche Maschinenanschläge unverändert. Im ersten Rest-Entwurf löschte
das Anlegen der Ebene durch Nachrechnen die gespeicherte Testbahn; die Gegenprobe
bewahrt jetzt ihre Quelle ausdrücklich. Prüfbelege:
`../../ergebnisse/bewegter-rest-2026-10-08/`. Die Vorschau ist weiterhin ein
XY-Strahlraster; weitere Schneidenformen, qualifizierte Einfahrten innerhalb eines
Zugs und automatische Aufspannungen bleiben offen.

Goldene gemeinsame Schrupp-/Schlichtfolge unverändert: 46,470163 s Bearbeitung,
5948 Punkte, 6181 NC-Bewegungen, bisheriger NC-SHA identisch; Rechnung
231,462 s / 240,434 MiB Python gegenüber 210,395 s / 240,434 MiB Referenz innerhalb
der festen Zeit-/Speichergrenzen. Feine Zulassung, tatsächlicher Export,
Übernahme/Undo/Abbruch und G550-Kaltexport bestanden. Keine vorhandene Referenz
neu geschrieben. Eigene Profile und Speicherdeckel; persönlicher Werkzeugbestand
seit Manuels Änderung unverändert. Kein Push, Manuels Klickprüfung steht aus.
