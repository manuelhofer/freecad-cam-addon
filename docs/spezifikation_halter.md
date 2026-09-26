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
3. Länge in „Auf der Maschine prüfen“, Halter im Abfahren.

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
