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
   Abtragsmodell für Ebenen, Abschnitt 7).
6. **Nut** – mit Rampe oder Trochoide statt Vollschnitt. Aufwand klein bis
   mittel.
7. **Bohren, Zirkularfräsen, Gewinde** – FreeCADs Operationen übernehmen; der
   Assistent legt sie mit den Schnittwerten aus der Werkzeugverwaltung an
   (Bohrer, Senker, Reibahle, Gewindebohrer sind schon Werkzeugarten).
   Aufwand klein.
8. **Fasen / Entgraten** – an Kanten in der Ebene mit Fasenfräser oder
   Kugelfräser als Kantenbruch; Breite einstellbar; **auch an Kanten im Raum**
   und rundum (V4d). Aufwand mittel.
9. **Gravieren** – FreeCADs Engrave/Vcarve übernehmen. Aufwand keiner.

### 4.2 3D – Freiformflächen

Grundlage für alles hier: ein **Höhenfeld** (Abschnitt 7) – die Fläche als
Raster z(x, y) aus dem Netz, plus die Hüllfläche des Fräsers darüber
(„Dropcutter“ mit numpy, wie `vierachs_huelle` es um die Achse rechnet, nur
eben). Kein OCL.

1. **Schruppen ebenenweise** – Lagen von oben, jede Lage eine Tasche adaptiv
   (4.1.2) auf der Fläche, die in dieser Höhe frei ist; Restmaterial aus dem
   Abtrag. *Besser:* Adaptive kennt keine 3D-Grenze, Surface kann nicht
   schruppen. Aufwand groß (baut auf 4.1.2).
2. **Restschruppen** – kleiner Fräser nur dort, wo der große nicht hinkam
   (Abtrag). Aufwand mittel.
3. **Schlichten Zeilen** (parallel) – Raster in einem Winkel, Zickzack oder
   einseitig, **Grathöhe als Maß** (Schrittweite aus Grathöhe und Fräserform,
   `vierachs_bahn.rillenhoehe` gibt es schon), Zeilen nur über der Fläche,
   Bögen an den Umkehrpunkten. Aufwand mittel.
4. **Z-konstant** (Höhenlinien) für steile Bereiche, **Steil/Flach**: über
   einem Grenzwinkel Höhenlinien, darunter Zeilen – in einer Operation.
   *Besser:* Surface und Waterline getrennt lassen Rippen und Stufen. Aufwand
   mittel bis groß.
5. **Äquidistant** (3D-Offset, gleichbleibende Grathöhe auf jeder Neigung) –
   die feinste Schlichtstrategie. Aufwand groß; nach 3 und 4.
6. **Bleistift** (Kehlen) – dort, wo zwei Flächen sich treffen und der Fräser
   nicht hinkam. Aufwand mittel (Abtrag: rot/gelb-Stellen als Bahn).
7. **Fläche entlang** (Flowline) – Zeilen folgen den Flächenkurven (UV);
   für Kegel, Rohre, Übergänge. Aufwand mittel bis groß.
8. **Restschlichten** – kleiner Fräser, nur wo nötig (aus Abtrag). Aufwand
   mittel (nach 6).

### 4.3 Rundum und 4 Achsen (W-003)

Gebaut: Rundum schruppen und schlichten, Flächen wählen, hin und her.
Weiter (spezifikation_vierachs.md, V4c/V4d), in dieser Reihenfolge:

1. **Linien längs** – Zeilen längs der Achse bei festem Winkel: Nut,
   Abflachung, Nocke mit Kugel-/Torusfräser. Aufwand klein bis mittel.
2. **Plan indexiert (3+1)** – Rundachse steht, ebene Fläche parallel zur Achse
   wird wie beim Planfräsen gefräst (braucht Y an der Drehmaschine oder A an
   der Fräse); mit Versatz quer zur Werkzeugachse in Abfahren, Kollision und
   Abtrag. Aufwand mittel.
3. **Rundum entgraten** (V4d) – Kanten der gewählten Flächen, die Rundachse
   dreht mit. Aufwand mittel.
4. **Taschen und Nuten auf dem Mantel** – die Tasche in der Abwicklung rechnen
   (4.1.2/4.1.3), auf den Zylinder zurückwickeln (wie FreeCADs „wrap“, aber mit
   Abtrag und Kollision). Aufwand mittel.
5. **Nockenwellen, Exzenter** – rundum schruppen kann es; schlichten mit
   Linien längs und Grathöhe. Aufwand klein, prüfen.

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
     Kollision, Reichweite) und die Grenzen des Einsatzes.

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
   Gegenlauf; seit P-2026-10-01-28 richtig herum, Kontur und Räumen.)
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
  wegnimmt – im Raster von 0,5 mm sieht die Simulation ihn nicht.
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
  – die Ringe um das, was noch steht: die Höhenlinien von
  F = min(Tiefe im Rohteil + R, D + ae) bei m · ae, überall ae auseinander; das
  Rechteck beißt in den Zapfen, die Zwickel zwischen Zapfen und Ecke werden
  eigene Ringe, die Ringe nur um den Zapfen kommen zuletzt von außen nach
  innen –, „morph“ (P-2026-10-01-27) – ein harmonisches Feld u zwischen
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
  Platte 66 min); dann zählen die anderen Varianten – und „inseln“ (nur die
  Ringe um Wände und Inseln; in der Tasche von innen nach außen; Taschen
  rechnen nur diese Variante). Auf Manuels 50 × 50 mit Zapfen: morph 2,69 min
  (eine Einfahrt, keine Rampe, 7 Halte), rohteil 2,75 (4 Einfahrten), inseln
  4,49 – der Morph gewinnt; am Absatz rohteil 2,03 (eine Spirale); auf der
  Platte rohteil 33,1 (morph gesperrt), inseln 40,5. Je Lauf der Eingang in dieser Reihenfolge: an den vorigen
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
  beim Anlegen – es wird mitgeschoben). Die Spannhöhe folgt mit S3f.

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
| heute mit ganzer Schneide: Planfräsen ap 20, ae 1,5; Tasche über die Kontur ap 20 (ganz räumen) | 39,3 min (1 Lage, 151 Zeilen, 33 m) | 3,9 min (12 Versätze, je mit Rampe) | 0,9 min | **44 min** |
| S3f Räumen (gebaut, 0.45.0): Ringe ap 20, ae 1,5, hinein von außen in der Luft, zuletzt um den Zapfen; Tasche Rampe 3° einmal rundum, dann Ringe nach außen; Kontur nur mit dem Aufmaß | 33,1 min (1 Lage, gemessen; geschätzt waren ≈ 33) | 1,2 min (gemessen; geschätzt ≈ 1,3) | 0,3 min | **34,7 min** (gemessen, `test_pruefstand`) |
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
3°; Einsätze Planen und Schruppen mit ae 1,5 / ap 25 / fz 0,1 / vc 85,
Schlichten mit ae 0,3, dem Aufmaß der Kontur). Mit ihm rechnen alle
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
