# Spezifikation W-002 Stufe D: Halter

Stand: P-2026-09-26-93. **Manuel hat am 2026-09-26 entschieden:** eine eigene
Halter-Verwaltung (für die Kollisionsprüfung, W-001 Stufe 4c), in einem
eigenen Fenster aus der Werkzeugverwaltung; die Länge ab Spindelnase bleibt
gemessen, sonst geschätzt. Die Einzelheiten sind Claudes Vorschläge, zur
Besprechung (Abschnitt 9).

Grundlage: [spezifikation_werkzeugverwaltung.md](spezifikation_werkzeugverwaltung.md)
(Werkzeuge, Speicherung), [spezifikation_simulation.md](spezifikation_simulation.md)
(Stufe 4: Reichweite, Abfahren, Kollision).

## 1. Wozu

Der Halter sitzt zwischen Spindelnase und Werkzeug. Er stößt an: in tiefen
Taschen am Teil, nah am Schraubstock, an der Spannbacke. Die
Kollisionsprüfung braucht seine Form, das Abfahren zeigt ihn, und solange
niemand die Länge ab Spindelnase gemessen hat, lässt sie sich mit ihm
schätzen. Heute ist er im Abfahren nur angedeutet (Zylinder Ø 2 × Schaft).

## 2. Was FreeCAD kann

Nichts dazu: Die CAM-Werkzeuge (ToolBit) kennen in 1.1.3 und im Wochen-Build
keinen Halter (nachgesehen in `Mod/CAM/Path/Tool`, P-2026-09-26-93). Der
Halter wird deshalb auch nicht an CAM übergeben.

## 3. Ein Halter

- **Name**, frei („SK40 ER32 A70“), und **Bezeichnung** (Hersteller,
  Bestellnummer).
- **Kontur** von der Spindelnase zum Werkzeug hin, in **Abschnitten**: je
  Länge, Ø oben (zur Spindel) und Ø unten (zum Werkzeug). Gleiche
  Durchmesser ergeben einen Zylinder, verschiedene einen Kegel. Rund um die
  Werkzeugachse. Was in der Spindel steckt (Steilkegel, HSK-Schaft), zählt
  nicht – die Kontur beginnt an der Spindelnase (Plananlage).
- **Länge** = Summe der Abschnitte: von der Spindelnase bis zur Nase des
  Halters, wo das Werkzeug herauskommt (im Katalog meist „A“ oder „L1“).
- **Spanntiefe:** wie tief der Schaft im Halter steckt – nur für die
  Schätzung der Länge ab Spindelnase (Abschnitt 4).
- **Vorlagen** zum Anfangen: Spannzangenfutter ER16, ER25, ER32, ER40,
  Schrumpffutter Ø6 und Ø12, Weldon Ø20, Hydrodehnspannfutter Ø20,
  Aufsteckfräserdorn Ø22, Bohrfutter; für Drehmaschinen ein VDI30-Halter als
  Zylinder. Die Maße sind typische Werte an SK40, keine Katalogwerte; die
  Bezeichnung sagt „Beispielmaße – nach Katalog prüfen“.

## 4. Werkzeug und Halter

- Jedes Werkzeug bekommt das Feld **Halter**: Auswahl aus der Liste, „ohne“ =
  kein Halter bekannt.
- Die **Länge ab Spindelnase** bleibt, was das Voreinstellgerät misst:
  Spindelnase bis Spitze. Ist sie leer und ein Halter gewählt, gilt – grau im
  Feld – **Halterlänge + Gesamtlänge − Spanntiefe**, mindestens Halterlänge
  + Reichweite (Schneide und Hals).
- Unter der Nase des Halters liegen Schaft und Schneide des Werkzeugs, mit
  den Maßen aus dem Werkzeug (Ø, Schneidenlänge, Hals, Schaft).
- Ein Halter ist eine Beschreibung, kein einzelnes Stück: Mehrere Werkzeuge
  können denselben haben.
- Einen Halter, den Werkzeuge benutzen, kann man löschen – nach Rückfrage
  („gehört zu T3, T7“); die Werkzeuge sind dann ohne Halter.

## 5. Oberfläche

In der Werkzeugverwaltung bei jedem Werkzeug, unter der Länge ab Spindelnase:

```
  Länge ab Spindelnase [          ] mm     grau: 113 mit Halter
  Halter  [SK40 ER32 A70            ▼] [Halter …]
```

„Halter …“ öffnet das Fenster **Halter** (wie „Werkstoffe …“):

```
┌ Halter ────────────────────────────────────────────────────────────┐
│ [Suche …             ] │ Name         [SK40 ER32 A70             ] │
│ SK40 ER32 A70          │ Bezeichnung  [Hersteller, Bestell-Nr.   ] │
│ SK40 Schrumpf Ø12 A80  │ Spanntiefe   [40      ] mm                │
│ HSK63 Weldon Ø20       │ Kontur ab Spindelnase:        ┌───────┐   │
│                        │     Länge    Ø oben   Ø unten │███████│   │
│                        │  1  16,00    63,00    63,00   │ █████ │   │
│                        │  2  54,00    50,00    50,00   │ █████ │   │
│                        │ [+ Abschnitt] [− Abschnitt]   │   ┆   │   │
│ [Neu ▼] [Kopieren]     │ Länge 70,00 mm · Ø bis 63,00  └───────┘   │
│ [Löschen]              │ Benutzt von: T3, T7                       │
│                                              [OK] [Abbrechen]      │
└────────────────────────────────────────────────────────────────────┘
```

- „Neu ▼“: leer oder aus einer Vorlage. Das Bild zeigt den Halter im Schnitt,
  oben die Spindelnase, unten gestrichelt ein Werkzeug.
- OK übernimmt die Halter in die Werkzeugverwaltung; gespeichert wird mit
  deren OK bzw. Übernehmen – wie bei den Werkstoffen. Abbrechen verwirft.

## 6. Speicherung

In `werkzeugverwaltung.json`, Liste `halter`: Kennung, Name, Bezeichnung,
Spanntiefe, Abschnitte (je `laenge`, `d_oben`, `d_unten` in mm). Das Werkzeug
speichert unter `halter` die Kennung seines Halters. Ältere Dateien ohne
Halter bleiben lesbar; `FORMAT` bleibt 1.

## 7. Wo der Halter wirkt

- **Auf der Maschine prüfen (4a):** die Werkzeuglänge – gemessen, sonst mit
  Halter geschätzt; der Hinweis sagt, womit gerechnet wurde.
- **Abfahren (4b):** der Halter mit seiner Kontur statt des angedeuteten
  Zylinders.
- **Kollision (4c):** Halter, Schaft und Schneide gegen Teil, Spannmittel und
  Maschine ([spezifikation_simulation.md](spezifikation_simulation.md), 4c).
- **An CAM übergeben:** nichts (CAM kennt keine Halter).

## 8. Schritte

1. Datenmodell (`camaddon/halter.py`, Bibliothek und Werkzeug), Speicherung,
   Vorlagen, geschätzte Länge; Prüfungen ohne Oberfläche. *Gebaut
   (P-2026-09-26-94).*
2. Fenster „Halter“ (`camaddon/gui_halter.py`), Feld im Werkzeug, Hilfe,
   Szenario mit Screenshots. *Gebaut (P-2026-09-26-95); das Feld „Halter“
   steht in einer eigenen Zeile über die ganze Breite, damit lange Namen
   ganz zu lesen sind; die Schneide im Bild ist blau wie im Bild des
   Werkzeugs.*
3. Länge in „Auf der Maschine prüfen“, Halter im Abfahren. *Gebaut
   (P-2026-09-26-96).*

## 9. Entscheidungen

1. **Eigene Halter-Verwaltung** statt eines Zylinders je Werkzeug –
   *Manuel, 2026-09-26.*
2. **Eigenes Fenster** aus der Werkzeugverwaltung (Knopf „Halter …“) –
   *Manuel, 2026-09-26.*
3. **Länge ab Spindelnase gemessen, sonst geschätzt** (Halterlänge +
   Gesamtlänge − Spanntiefe) – *Manuel, 2026-09-26.*
4. Kontur aus Abschnitten, Zylinder und Kegel, rund um die Werkzeugachse;
   Blockhalter an Drehmaschinen (VDI) werden als Zylinder angenähert –
   *Claude, zur Besprechung.*
5. Die Spanntiefe gehört zum Halter, nicht zum Werkzeug – *Claude.*
6. Vorlagen mit typischen SK40-Maßen, als Beispiel gekennzeichnet –
   *Claude.*
7. Ein Halter kann zu mehreren Werkzeugen gehören – *Claude.*

## 10. Akzeptanzkriterien

- Werkzeugverwaltung → ein Werkzeug (Gesamtlänge 83 mm) → „Halter …“ →
  „Neu ▼“ → „Spannzangenfutter ER32“ → die Liste zeigt ihn, das Bild Flansch
  und Körper, darunter „Länge 70,00 mm“ → OK → beim Werkzeug ist der Halter
  gewählt, im leeren Feld „Länge ab Spindelnase“ steht grau „113 mit Halter“
  (70 + 83 − 40 Spanntiefe).
- Speichern, schließen, wieder öffnen: Halter und Zuordnung sind da.
- Einen Halter löschen, den ein Werkzeug benutzt → die Rückfrage nennt das
  Werkzeug → danach ist es ohne Halter.
- Abfahren: Der Halter erscheint mit seiner Kontur an der Spindel.
- Manuel versteht das Fenster ohne Erklärung.

## 11. Stufe E: Richtung des Werkzeugs am Halter

Stand: P-2026-09-30-10. **Manuel hat am 2026-09-30 entschieden:** Wie ein
Werkzeug zur Maschine steht – radial, axial, im Winkelkopf in jede Richtung –,
sagt **der Halter**. Seine Worte: „Die Plätze müssen mit den Werkzeugen beladen
werden, die dafür geeignet sind … ein Parameter, wie die Werkzeug-Z-Achse zur
Maschinen-Haupt-Z-Achse steht … Es kann ja auch in eine normale Spindel von
der Fräsmaschine ein Winkelkopf eingebaut werden, dieser kann in alle
Richtungen stehen, und da ist es auch wichtig, dass man das Werkzeug richtig
definiert.“ Reihenfolge, auch Manuel: erst diese Grundvoraussetzung, dann die
Beispielmaschinen so, dass alles geht, dann alles auf Bedienbarkeit prüfen,
dann weiter (Flächen wählen, W-003 V4). Die Einzelheiten unten sind Claudes
Vorschlag.

**Anlass:** An der Beispiel-Drehmaschine hat der Revolver fest eingebaut einen
radialen Halter auf P1 und einen axialen auf P2. Schruppen mit T1 und
Schlichten mit T2 (W-003 V5) ging deshalb nicht: T2 säße axial.

### 11.1 Aufnahme und Halter

- Eine **Aufnahme** der Maschine (Spindelnase, Revolverplatz) ist nur die
  Schnittstelle: ihr LCS, Z zeigt von der Werkzeugseite in die Maschine (wie
  bisher), dazu eine **Bezugsrichtung X** – am Revolver radial von der
  Revolverachse nach außen (in Arbeitsstellung zur Spindelachse hin), an einer
  Frässpindel das +X der Maschine.
- Ein **Halter** ist **gerade** (wie bisher: das Werkzeug in der Achse der
  Aufnahme) oder **gewinkelt** mit
  - **Winkel** α zwischen Aufnahmeachse und Werkzeugachse (90° = rechtwinklig;
    ein Universal-Winkelkopf lässt jeden Winkel zu),
  - **Drehung** β um die Aufnahmeachse, von der Bezugsrichtung X aus (0°: das
    Werkzeug zeigt nach X – am Revolver also zur Spindelachse),
  - **Versatz** v längs der Aufnahmeachse bis zur Werkzeugachse – dort liegt
    der **Bezugspunkt** B –,
  - einem **Kopf** von der Aufnahme bis B (Ø, als Zylinder angenähert).
- Die **Kontur** (Abschnitte, wie bisher) läuft beim gewinkelten Halter von B
  längs der Werkzeugachse bis zu seiner Nase; beim geraden von der Spindelnase.
- Die **Länge ab Spindelnase** am Werkzeug heißt beim gewinkelten Halter **Länge
  ab Bezugspunkt**: von B längs der Werkzeugachse bis zur Spitze – so messen es
  die Voreinstellgeräte für angetriebene Werkzeuge. Geschätzt wie bisher aus
  Halter, Gesamtlänge und Spanntiefe.
- **Vorlagen** dazu: „VDI30 angetrieben radial“ (90°, v 55 mm), „VDI30
  angetrieben axial“ (gerade), „Winkelkopf 90° · SK40“ (90°, v 110 mm) –
  Beispielmaße wie die übrigen.

### 11.2 Rechnung

Die Lage des Werkzeugs ist Aufnahme · Halter: um v längs −Z zum Bezugspunkt,
dann um β um Z und um α gekippt. Die Werkzeugachse zeigt zur Spitze in
Richtung (sin α · cos β, sin α · sin β, −cos α) im LCS der Aufnahme. Darin
liegen Schneide, Hals und Schaft wie bisher (Spitze bei −Länge); der Kopf
liegt in der Aufnahme. Das gilt überall, wo heute die Aufnahme allein zählt:
Reichweite und Spitze (`kinematik`), Abfahren, Kollision, das Bild im
Prüffenster, der Hinweis „nicht radial“.

- Ein gerader Halter ergibt genau das Bisherige – Maschinen und Werkzeuge ohne
  Halter rechnen wie heute.
- Eine gespeicherte Maschine, deren Revolverplatz schon radial zeigt (so wie
  P1 bisher), bleibt richtig: Dort steht ein gerader Halter radial.

### 11.3 Oberfläche

- Fenster „Halter“: unter dem Namen **Richtung** [gerade | gewinkelt]; bei
  gewinkelt die Felder Winkel, Drehung, Versatz und Kopf-Ø. Das Bild zeigt den
  Halter von der Seite – Kopf, Knick und Abgang.
- Werkzeugverwaltung: Die Längenzeile sagt, wovon aus gemessen wird („ab
  Spindelnase“ bzw. „ab Bezugspunkt des Halters“).
- Prüffenster: Sitzt das Werkzeug einer Rundum-Operation nicht radial, sagt der
  Hinweis, was fehlt („T2 sitzt gerade auf P2 – für „Rundum schlichten“ braucht
  es einen Halter, der radial steht, etwa „VDI30 angetrieben radial““), ein
  Klick öffnet das Werkzeug.
- 4-Achs-Assistent: Hat die gewählte Maschine einen Revolver und der gewählte
  Fräser keinen radialen Halter, steht das gelb unter dem Fräser, mit demselben
  Satz.

### 11.4 Beispielmaschinen

- **Beispiel-Drehmaschine:** Der Revolver trägt keine Halter mehr fest; jeder
  Platz ist eine Aufnahme (VDI30-Bohrung an der Stirn der Scheibe, Z längs der
  Revolverachse, X radial). Die Halter kommen mit den Werkzeugen – die
  Beschreibung der Maschine sagt es.
- **Fräsen:** Aufnahme an der Spindelnase wie bisher, X = +X der Maschine; ein
  Winkelkopf aus der Halterliste macht aus der 3-Achs-Fräse eine, die zur Seite
  fräst.
- Die Szenarien bekommen ihre Halter: Schruppen T1 und Schlichten T2 mit „VDI30
  angetrieben radial“ auf der Beispiel-Drehmaschine – Prüfen, Farben und
  Kollision (der offene Klickweg von W-003 V5).

### 11.5 Schritte

- **E1** Datenmodell, Speicherung und Vorlagen (`halter.py`); die Lage des
  Werkzeugs (Aufnahme · Halter) an einer Stelle; Prüfungen ohne Oberfläche.
  *Gebaut (P-2026-09-30-11):* `Halter.richtung` (gerade/gewinkelt), `winkel`,
  `drehung`, `versatz`, `kopf_d`; `lage()` (Placement im LCS der Aufnahme) und
  `form()` mit Kopf – der reicht um seinen Radius über den Bezugspunkt hinaus,
  dort sitzt das Winkelgetriebe. Vorlagen „VDI30 angetrieben radial · ER16“,
  „VDI30 angetrieben axial · ER16“, „Winkelkopf 90° · SK40“. Alte Dateien
  ohne Richtung sind gerade.
- **E2** Fenster „Halter“ mit Richtung und Bild; Längenzeile im Werkzeug; Hilfe;
  Szenario mit Screenshots.
  *Gebaut (P-2026-09-30-13):* „Richtung“ [gerade – das Werkzeug in der Achse
  der Aufnahme | gewinkelt – angetrieben radial, Winkelkopf], darunter nur beim
  gewinkelten Winkel, Drehung, Versatz und Kopf-Ø; „Kontur ab Bezugspunkt,
  längs der Werkzeugachse:“; die Zusammenfassung nennt Winkel und Versatz. Das
  Bild rechnet in Maßen und passt ein: Kopf, Knick, Abgang und Werkzeug in der
  Ebene des Knicks. In der Werkzeugverwaltung heißt die Länge beim gewinkelten
  Halter „Länge ab Bezugspunkt“. Szenario `szenario_halter_richtung`.
- **E3** Reichweite, Spitze, Abfahren, Kollision und Bild mit der Lage aus E1;
  Hinweis „nicht radial“ mit dem, was fehlt.
  *Gebaut (P-2026-09-30-12):* `reichweite.Einspannung` (Länge ab Bezugspunkt und
  Lage aus dem Halter; eine Zahl ist weiter ein gerade eingespanntes Werkzeug),
  `reichweite.einspannung(tc, bibliothek)`; Spitze, „quer“ und „radial“ nehmen
  die Achse des Werkzeugs, nicht die der Aufnahme; `OperationAbfahrt.lage`; die
  Körper in `werkzeugkoerper` gekippt, der Halter mit Kopf. Die Hinweise sagen,
  welcher Halter fehlt.
- **E3a** (beim Bauen von E4 gefunden) Rundum: Vor dem Futter zählt, was
  weiter reicht – der Fräser oder sein Halter. Der Kopf von „VDI30 angetrieben
  radial“ reicht 27,5 mm über die Werkzeugachse zum Futter hin, der Fräser Ø 12
  nur 6; Ausspannlänge und Bahn nur mit dem Fräser – und der Kopf stieß ans
  Futter.
  *Gebaut (P-2026-09-30-14):* `halter.seitlich()` – der halbe größte Ø, beim
  gewinkelten auch der Kopf. `Schruppwerte.halter`, `Schlichtwerte.halter`: Die
  Bahn endet, wo der Rand, der weiter reicht, den Abstand zum Futter hat; ist
  dafür kein Platz, sagt es der Fehler („kein Platz für den Halter“). Beide
  Rundum-Operationen haben die Eigenschaft „HalterZumFutter“ – ältere bekommen
  0, ihre Bahn bleibt –, der Assistent trägt sie beim Anlegen und Ändern aus der
  Werkzeugverwaltung ein. Die Ausspannlänge nennt dann „Halter über die
  Werkzeugachse 27,5“ statt des Fräserradius. Wie der Halter an der Maschine
  steht, weiß die Operation nicht – so ist es auf jeder Seite genug.
- **E4** Beispiel-Drehmaschine mit Aufnahmen statt fester Halter; Szenarien mit
  Haltern; das Szenario Schruppen + Schlichten prüfen (W-003 V5e).
- **E5** Assistent: gelber Satz, wenn der Fräser nicht radial sitzen würde.

### 11.6 Entscheidungen

1. Die Richtung steht **am Halter** – *Manuel, 2026-09-30.*
2. Erst diese Grundvoraussetzung, dann Beispielmaschinen, Durchsicht, dann
   Flächen wählen – *Manuel, 2026-09-30.*
3. Winkel, Drehung, Versatz und Kopf als Zylinder; Länge ab Bezugspunkt –
   *Claude, zur Besprechung.*
4. Werkzeugnummer = Revolverplatz bleibt (wie bisher) – *Claude.*

### 11.7 Akzeptanzkriterien

- Werkzeugverwaltung → T2 Kugelfräser → „Halter …“ → „Neu ▼“ → „VDI30
  angetrieben radial“ → das Bild zeigt den Knick, Richtung „gewinkelt“, 90°,
  Versatz 55 mm → OK → beim Werkzeug steht „Länge ab Bezugspunkt“.
- Beispiel-Drehmaschine, Welle, „4-Achs-Bearbeitung“ mit „Rundum schruppen“ T1
  und „Rundum schlichten“ T2 (beide mit dem radialen Halter) → „Auf der
  Maschine prüfen“: kein Hinweis „nicht radial“; abspielen: T1 und T2 stehen
  radial am Teil; am Ende die Farben; „Kollision prüfen“ meldet nichts.
- Ohne Halter bei T2: Der Hinweis nennt T2, P2 und den Halter, der fehlt.
