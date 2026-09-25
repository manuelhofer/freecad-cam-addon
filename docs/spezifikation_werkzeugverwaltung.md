# Spezifikation W-002: Werkzeugverwaltung mit Werkstoffen und Schnittwerten

Stand: Entwurf von Claude, in der Nacht zum 2026-09-26 geschrieben, während
Manuel schlief. Die Entscheidungen in Abschnitt 11 hat Claude getroffen; sie
sind zur Besprechung da, nicht endgültig.

## 1. Zielbild

Manuels Wunsch, fast wörtlich: eine Werkzeugverwaltung, die
**bedienerfreundlich, übersichtlich und einfach genial** ist – etwa wie die
alte von InventorCAM. Das Augenmerk liegt auf Bedienbarkeit und Einfachheit.

1. **Zuerst der Werkstoff.** Eine Werkstoffliste mit **deutschen
   Bezeichnungen**: Werkstoffnummer, Kurzname nach chemischer Zusammensetzung
   und Werkstoffgruppe, dazu die Zusammensetzung und die Härte – etwa
   „1.4301 X5CrNi18-10 · Edelstahl, austenitisch · ≤ 215 HB“.
2. **Im Werkzeug die Schnittwerte je Werkstoff**, jeden einzeln einstellbar –
   und auch für alle Werkstoffe gleich.
3. **Wer vc eingeben will, gibt vc ein** (und fz) – Drehzahl und Vorschub
   rechnet das Addon.
4. **Je Einsatz eigene Werte**, vor allem ae und ap: eine Tabelle, bei
   welchem ae welches ap geht.
5. **Strategien beurteilen.** Beispiel Manuel, Schaftfräser Ø 12: ae 1,2 mm
   bei ap 25 mm und fz 0,15 mm ist beim Schruppen von Außenkonturen oder beim
   Auffräsen von Löchern oft viel besser als ae 100 % bei ap 3 mm und
   fz 0,05 mm – schneller und mit viel weniger Verschleiß, weil die ganze
   Schneidenlänge arbeitet. Das Addon soll das aus den eingetragenen Werten
   zeigen und in einem Satz sagen, warum.
6. Alles **möglichst einfach und gut erklärt**.

## 2. Was FreeCAD schon kann (Stand 1.1.3 und Wochen-Build 26.3.0 dev)

| Baustein | Wo | 1.1.3 | Wochen-Build | Was fehlt für uns |
| --- | --- | --- | --- | --- |
| Werkzeugbibliothek (ToolBits, Formen, Bibliotheken `.fctl`) | `Mod/CAM/Path/Tool/` | ja | ja | keine Schnittwerte je Werkstoff (1.1.3), nirgends ae/ap |
| Schnittwert-„Presets“ am Werkzeug: vc und fz je Werkstoff und Bearbeitungsart | `Path/Tool/FeedsSpeeds/` | – | ja | nur vc, fz und ein Verhältnis für den Eintauchvorschub; versteckt in einem Reiter des Werkzeug-Editors |
| Vorschlag für den Werkzeug-Controller aus Preset und Rohteil-Werkstoff | `Path/Tool/Gui/FeedsSpeedsDialog.py` | – | ja | – (Ziel der Übergabe in Stufe 2) |
| Werkstoffe mit Werkstoffnummer (`MaterialStandard/MaterialNumber`, z. B. 1.4301) | `Mod/Material/Resources/Materials/Standard/` | ja | ja | keine Härte, keine Zusammensetzung; englische Gruppen |
| Zerspanbarkeit (vc HSS/VHM, kc1.1, mc) | Modell `Machinability` | ja | ja | nur 6 generische Werkstoffe („Steel (Generic)“ …) |

**Folgerung:** Die Oberfläche und die Daten, die Manuel beschreibt, gibt es in
FreeCAD nicht – weder in der stabilen Version noch im Wochen-Build. Die
Presets des Wochen-Builds sind aber das richtige **Ziel**: Stufe 2 schreibt die
Werte des Addons dorthin, damit FreeCADs eigener Vorschlag im
Werkzeug-Controller sie benutzt.

## 3. Begriffe

- **Werkstoff** – das, was zerspant wird, samt Zustand: „1.2379 geglüht“ und
  „1.2379 gehärtet“ sind zwei Einträge, weil die Schnittwerte ganz andere
  sind.
- **ISO-Gruppe** – der Kennbuchstabe aus den Werkzeugkatalogen, mit seiner
  üblichen Farbe: **P** Stahl (blau), **M** rostfreier Stahl (gelb), **K** Guss
  (rot), **N** Nichteisen (grün), **S** Titan und Superlegierungen (orange),
  **H** gehärteter Stahl (grau). Jeder Katalog ordnet seine Schnittwerte so.
- **Werkzeug** – ein Fräser oder Bohrer mit seiner Geometrie (Durchmesser,
  Schneidenzahl, Schneidenlänge …).
- **Einsatz** – wie ein Werkzeug arbeitet, mit eigenen Werten: Vollnut,
  Schruppen, Schruppen dynamisch, Schlichten, Eintauchen, Bohren – oder ein
  eigener Name.
- **Schnittwerte** – je Einsatz: **ae** (seitliche Zustellung, mm), **ap**
  (Tiefe, mm), **vc** (Schnittgeschwindigkeit, m/min), **fz** (Vorschub je
  Zahn, mm). Beim Bohren **f** (Vorschub je Umdrehung) statt fz.
- **Gerechnet**, nicht eingegeben: **n** (Drehzahl, U/min), **vf** (Vorschub,
  mm/min), **Q** (Zeitspanvolumen, cm³/min), **Eingriffswinkel φ**, **größte
  Spandicke h max**, **Schneidenweg je cm³**, **Schnittleistung Pc**.

## 4. Die Werkstoffliste

**Mitgeliefert** werden rund 45 gängige Werkstoffe aus allen sechs
ISO-Gruppen – Baustahl, Automatenstahl, Einsatz- und Vergütungsstahl,
Werkzeugstahl (geglüht und gehärtet), Edelstahl (austenitisch, ferritisch,
martensitisch, Duplex), Guss, Aluminium (Knet- und Gusslegierungen), Kupfer,
Messing, Bronze, Titan, Nickelbasis, Kunststoffe.

Jeder Eintrag hat:

| Feld | Beispiel | Anzeige |
| --- | --- | --- |
| Werkstoffnummer | 1.4301 | wie sie ist |
| Kurzname (chemische Bezeichnung nach DIN EN) | X5CrNi18-10 | wie er ist |
| Gruppe | Edelstahl, austenitisch | übersetzt |
| Zustand (falls wichtig) | geglüht, vergütet, gehärtet, T6 … | übersetzt |
| ISO-Gruppe | M | Buchstabe auf farbigem Feld |
| Zusammensetzung (Hauptelemente, Massen-%) | C ≤ 0,07 · Cr 17,5–19,5 · Ni 8,0–10,5 | Zahlen im Format der Oberfläche |
| Härte | ≤ 215 HB, 58–62 HRC | so, wie sie im Datenblatt steht |
| Zugfestigkeit Rm | 500–700 N/mm² | |
| kc1.1 und mc (Richtwerte für die Schnittkraft) | 2350 N/mm², 0,21 | nur in den Einzelheiten; ohne Wert keine Leistungsangabe |

**Anzeige in der Auswahl (eine Zeile):**
`[M] 1.4301  X5CrNi18-10 · Edelstahl, austenitisch`
Darunter stehen Zusammensetzung, Härte und Zugfestigkeit des gewählten
Werkstoffs. In der Auswahl kann man tippen: „1.43“ oder „X5Cr“ oder „Edel“
findet ihn.

**Eigene Werkstoffe** legt man in der Liste „Werkstoffe…“ an: Nummer,
Kurzname, Gruppe (aus der Liste oder frei), ISO-Gruppe, Zusammensetzung und
Härte als freier Text. Mitgelieferte Einträge sind schreibgeschützt; „Als
eigenen kopieren“ macht eine änderbare Kopie.

## 5. Werkzeuge

| Feld | Einheit | Bemerkung |
| --- | --- | --- |
| Nummer | T… | frei, Vorschlag: nächste freie |
| Art | – | Schaftfräser, Torusfräser, Radiusfräser, Bohrer, Fasenfräser (Liste wächst) |
| Durchmesser D | mm | Pflicht |
| Schneidenzahl z | – | Pflicht (Bohrer: 2) |
| nutzbare Schneidenlänge | mm | für ap und die Beurteilung |
| Eckradius | mm | nur Torusfräser |
| Gesamtlänge | mm | nur für CAM; leer: Schneidenlänge + 2 × D, mindestens 3 × D |
| Schaft-Ø | mm | nur für CAM; leer: wie D |
| Schneidstoff | – | VHM, HSS |
| Bezeichnung | – | frei: Hersteller, Bestellnummer, Beschichtung … |

Die Liste zeigt je Werkzeug eine Zeile: `T3  Schaftfräser Ø 12 · z 3 · VHM`.

## 6. Schnittwerte

### 6.1 Je Werkstoff – oder für alle gleich

Jedes Werkzeug hat eine Tabelle **„für alle Werkstoffe“** und darf zusätzlich
**je Werkstoff eine eigene** haben. Gezeigt wird immer die Tabelle für den
Werkstoff, der oben gewählt ist:

- Hat das Werkzeug für ihn eigene Werte, stehen sie da – mit dem Satz
  „Eigene Werte für 1.4301“ und dem Knopf **„Eigene Werte löschen“** (danach
  gilt wieder „für alle Werkstoffe“).
- Sonst steht da: „Es gelten die Werte für alle Werkstoffe“ und der Knopf
  **„Eigene Werte für 1.4301 anlegen“**. Er kopiert die gemeinsame Tabelle als
  Ausgangspunkt.
- Ganz oben in der Werkstoff-Auswahl steht der Eintrag **„Alle Werkstoffe“**:
  Dort bearbeitet man die gemeinsame Tabelle.

### 6.2 Die Tabelle der Einsätze

Eine Zeile je Einsatz; eingegeben werden ae, ap, vc, fz, der Rest ist
gerechnet und grau:

| Einsatz | ae mm | ap mm | vc m/min | fz mm | n U/min | vf mm/min | Q cm³/min |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Vollnut | 12 | 3 | 120 | 0,05 | 3183 | 477 | 17,2 |
| Schruppen dynamisch | 1,2 | 25 | 120 | 0,15 | 3183 | 1432 | 43,0 |
| Schlichten | 0,2 | 25 | 150 | 0,06 | 3979 | 716 | 3,6 |

- **„+ Einsatz“** bietet die Arten an und belegt ae und ap mit üblichen
  Anteilen von D vor (Vollnut: ae = D, ap = D/2; Schruppen dynamisch:
  ae = 10 % D, ap = Schneidenlänge; Schlichten: ae = 2 % D, ap =
  Schneidenlänge). vc und fz bleiben leer: Die kommen aus dem Katalog des
  Herstellers.
- Unter der Tabelle stehen zur gewählten Zeile die Werte, die man sonst im
  Kopf rechnet: „ae 1,2 mm = 10 % von D · ap 25 mm = 2,1 × D · Eingriff 37° ·
  größte Spandicke 0,09 mm“.
- Daneben ein **Bild des Eingriffs** (Draufsicht: Fräser mit dem Bogen, der im
  Material ist; Seitenansicht: Schneide mit dem Teil, der arbeitet). Es ändert
  sich beim Tippen – ohne Text, damit es in jeder Sprache passt.
- **Spandicke ausgleichen:** Bei kleinem ae wird der Span dünner als fz. Ein
  Knopf rechnet fz so hoch, dass die größte Spandicke der einer Vollnut mit
  demselben fz entspricht (h max = fz · sin φ, für ae < D/2).

### 6.3 Formeln

- n = vc · 1000 / (π · D)
- vf = n · z · fz (Bohren: vf = n · f)
- Q = ae · ap · vf / 1000
- Eingriffswinkel φ: cos φ = 1 − 2 · ae / D (ae ≥ D: φ = 180°)
- größte Spandicke: h max = fz · sin φ für ae < D/2, sonst fz
- mittlere Spandicke: h m = fz · (1 − cos φ) / φ
- spezifische Schnittkraft: kc = kc1.1 · h m^(−mc)
- Schnittleistung: Pc = Q · kc / 60 000 (kW, ohne Wirkungsgrad der Maschine)
- **Schneidenweg je cm³** (siehe 7): L = D · φ / (2 · ae · ap · fz · z), in m

## 7. Strategien vergleichen

Knopf **„Strategien vergleichen…“** unter der Tabelle. Man wählt zwei
Einsätze (A und B); das Fenster stellt sie nebeneinander, mit Balken:

| Kennzahl | Bedeutung |
| --- | --- |
| Abtrag je Minute Q | wie schnell das Material weg ist |
| Zeit für 100 cm³ | dasselbe, greifbar |
| **Schneidenweg je cm³** | wie weit **jede Stelle der Schneide** durchs Material fährt, um 1 cm³ abzutragen – weniger heißt weniger Verschleiß |
| genutzte Schneide | ap von der Schneidenlänge: Worauf verteilt sich der Verschleiß? |
| Zahn im Eingriff | φ / 360°: Wie lange ist der Zahn heiß, wie lange kühlt er ab? |
| größte Spandicke | ob fz zum Eingriff passt |
| Schnittleistung | ob die Spindel das schafft (nur mit kc1.1 des Werkstoffs) |

**Warum der Schneidenweg:** Je Umdrehung trägt das Werkzeug ae · ap · fz · z
ab, und jede Stelle der Schneide im Eingriff fährt dabei den Bogen
D/2 · φ durchs Material. Für 1 cm³ sind 1000 / (ae · ap · fz · z)
Umdrehungen nötig – daraus die Formel in 6.3. Verschleiß wächst ungefähr mit
diesem Weg (bei gleichem vc). Das ist eine Faustregel, kein
Standzeit-Modell; die Hilfe sagt das.

**Manuels Beispiel** (Ø 12, z = 3, vc = 120 m/min für beide):

| | A: Vollnut | B: Schruppen dynamisch |
| --- | --- | --- |
| ae / ap / fz | 12 / 3 / 0,05 mm | 1,2 / 25 / 0,15 mm |
| Q | 17,2 cm³/min | 43,0 cm³/min |
| Zeit für 100 cm³ | 5,8 min | 2,3 min |
| Schneidenweg je cm³ | 3,49 m | 0,29 m |
| genutzte Schneide | 3 mm | 25 mm |
| Zahn im Eingriff | 50 % | 10 % |
| größte Spandicke | 0,05 mm | 0,09 mm |

**Das Urteil** steht darunter in Sätzen, aus den Zahlen erzeugt:
„B trägt 2,5-mal so viel je Minute ab wie A. Jede Stelle der Schneide fährt
dabei nur ein Zwölftel des Weges durchs Material: Der Verschleiß verteilt
sich auf 25 statt 3 mm Schneide, und jeder Zahn ist nur 10 % statt 50 % der
Umdrehung im Eingriff – den Rest kühlt er ab.“

## 8. Oberfläche

Ein Befehl **„Werkzeugverwaltung“** in der Werkzeugleiste des Addons. Das
Fenster ist ein eigener Dialog (nicht an ein Dokument gebunden), mit
**OK / Übernehmen / Abbrechen** wie die Einstellungen von FreeCAD.
Abbrechen nach Änderungen fragt nach.

```
┌─ Werkzeugverwaltung ───────────────────────────────────────────────────────────┐
│ Werkstoff [M│1.4301  X5CrNi18-10 · Edelstahl, austenitisch    ▾] [Werkstoffe…](?)│
│           C ≤ 0,07 · Cr 17,5–19,5 · Ni 8,0–10,5 %  ·  ≤ 215 HB · 500–700 N/mm²   │
├─────────────────────────────┬──────────────────────────────────────────────────┤
│ Werkzeuge   [+ Neu][Kopie]  │ T3 · Schaftfräser Ø 12 · z 3 · VHM            (?) │
│ ┌─────────────────────────┐ │ Nummer [3 ]   Art [Schaftfräser ▾]                │
│ │ T1 Schaftfräser Ø 6  z3 │ │ Durchmesser [12] mm    Schneiden [3]              │
│ │ T2 Schaftfräser Ø 10 z4 │ │ Schneidenlänge [26] mm Schneidstoff [VHM ▾]       │
│ │▶T3 Schaftfräser Ø 12 z3 │ │ Bezeichnung [                                ]    │
│ │ T4 Bohrer Ø 8,5         │ │                                                   │
│ └─────────────────────────┘ │ Schnittwerte für 1.4301                       (?) │
│ [Löschen]                   │ Es gelten die Werte für alle Werkstoffe.          │
│                             │ [Eigene Werte für 1.4301 anlegen]                 │
│                             │ ┌──────────────────┬────┬────┬────┬────┬────┬────┬────┐
│                             │ │Einsatz           │ ae │ ap │ vc │ fz │ n  │ vf │ Q  │
│                             │ │Vollnut           │ 12 │ 3  │120 │0,05│3183│ 477│17,2│
│                             │ │Schruppen dynam.  │1,2 │ 25 │120 │0,15│3183│1432│43,0│
│                             │ └──────────────────┴────┴────┴────┴────┴────┴────┴────┘
│                             │ [+ Einsatz ▾] [− Einsatz]  [Strategien vergleichen…]
│                             │ ┌ Bild: Draufsicht │ Seitenansicht ┐ ae 1,2 = 10 % D
│                             │ └───────────────────────────────────┘ Eingriff 37°
└─────────────────────────────┴──────────────────────────────────────────────────┘
                                                    [OK] [Übernehmen] [Abbrechen]
```

**Hilfe in drei Stufen** (Arbeitsregeln, Abschnitt 8): Jede Spalte hat eine
Überschrift in Worten mit Einheit und einen Tooltip mit einem Satz; die Knöpfe
(?) öffnen die Seiten „Werkstoffe“, „Schnittwerte“ (ae, ap, vc, fz, n, vf, Q,
Spandicke – mit Bildern und Beispielen) und „Strategien“ (Manuels Beispiel,
warum dynamisches Schruppen schont, Löcher auffräsen: erst helikal ein
Grundloch, dann ebenenweise mit voller Schneidenlänge).

## 9. Speicherung

- **Mitgelieferte Werkstoffe:** `daten/werkstoffe.json` im Addon – kommen mit
  jedem Update, schreibgeschützt.
- **Eigene Werkstoffe und alle Werkzeuge:** eine Datei
  `CamAddon/werkzeugverwaltung.json` unter `FreeCAD.getUserAppDataDir()` –
  für das Parameter-System zu groß (Arbeitsregeln, Abschnitt 7). Sie
  überlebt Updates des Addons. Geschrieben wird erst in eine Zwischendatei,
  dann ersetzt; die vorige Fassung bleibt als `.bak` liegen.
- Das Format trägt eine Versionsnummer, damit spätere Fassungen alte Dateien
  umstellen können.

## 10. Stufen

1. **Werkstoffe, Werkzeuge, Schnittwerte, Vergleich** – alles oben. Läuft in
   1.1.3 und im Wochen-Build gleich.
2. **Übergabe an CAM:** Werkzeuge als ToolBits in eine eigene
   FreeCAD-Bibliothek „CAM-Addon“ schreiben (Form, D, z, Schneidenlänge,
   HSS/Carbide). Im Wochen-Build zusätzlich die Schnittwerte als Presets:
   Werkstoff über die Werkstoffnummer (`MaterialNumber` der
   FreeCAD-Werkstoffe), Einsatz → Bearbeitungsart (Vollnut → slot, Schruppen
   dynamisch → adaptive, Schruppen → pocket, Schlichten → profile,
   Bohren → drill). Dann schlägt FreeCADs eigener Knopf im
   Werkzeug-Controller unsere Werte vor. In 1.1.3: ein Knopf im Addon, der
   Drehzahl und Vorschübe der Werkzeug-Controller eines Jobs aus der Tabelle
   setzt.
   **Erster Teil gebaut** (P-2026-09-25-52): Knopf „Speichern und an CAM
   übergeben“. Geschrieben wird über `cam_assets.add_raw` (CAMs eigene
   Asset-Verwaltung, in beiden Versionen gleich); die ToolBits heißen
   `camaddon_<Kennung>`, eine erneute Übergabe ersetzt sie und entfernt
   gelöschte, fremde Werkzeuge bleiben. Gesamtlänge und Schaft sind
   geschätzt (Schneidenlänge + 2 × D, Schaft = D) – seit P-2026-09-25-62
   nur noch, wo die Felder leer sind.
   **Zweiter Teil gebaut** (P-2026-09-25-53): Befehl „Schnittwerte in den
   Job“ – je Werkzeug-Controller ein Einsatz (vorgeschlagen nach Name oder
   Operation), Werkstoff vom Rohteil über die Werkstoffnummer, Drehzahl,
   Vorschub und Eintauchvorschub (⅓, beim Bohren voll) in einem Schritt.
   Geht in 1.1.3 und im Wochen-Build.
   **Erweitert** (P-2026-09-25-61): Die Operationen, die den
   Werkzeug-Controller benutzen, bekommen ae als Schrittweite (% von D,
   abgerundet) und ap als Zustelltiefe, wenn der Einsatz passt (Adaptiv ←
   dynamisch und Schruppen, Tasche und Planfräsen ← Schruppen, Nut ←
   Vollnut, Kontur ← nichts). Damit geht Manuels „Loch auffräsen: einmal
   helikal eintauchen, dann ebenenweise mit voller Schneide“ in einem
   Schritt: Adaptiv mit Zustelltiefe = Schneidenlänge.
   **Und umgekehrt** (P-2026-09-25-66): „Aus CAM übernehmen“ holt die
   Werkzeuge einer FreeCAD-Bibliothek in die Werkzeugverwaltung (Art,
   Nummer, Maße, Schneidstoff; ohne Schnittwerte). Was es gibt, bleibt;
   Formen ohne Gegenstück (Gravierstichel, Säge, Gewindefräser, Taster)
   bleiben draußen und werden genannt.
   **Dazu** (P-2026-09-25-65): „Werkzeug-Controller hinzufügen“ im selben
   Dialog – Werkzeug und Einsatz wählen, der Controller heißt nach dem
   Einsatz („T3 Schruppen dynamisch“) und hat gleich Drehzahl und Vorschub.
3. **Schruppwerte vorschlagen:** aus Werkzeug, Werkstoff (kc1.1, mc) und
   Maschine (Leistung, Drehmoment, Höchstdrehzahl aus W-001) die
   Kombination aus ae, ap und fz mit dem größten Zeitspanvolumen, die die
   Spandicke und die Maschine einhält.
   **Gebaut** (P-2026-09-25-60): Knopf „Schruppwerte planen…“ unter der
   Tabelle (Schaft- und Torusfräser). Eingaben: vc, Spandicke h, ap,
   ae-Grenze in % von D (vorbelegt aus der gewählten Zeile bzw. 10 %),
   dazu Höchstdrehzahl, höchster Vorschub und Spindelleistung der Maschine
   (leer = keine Grenze, gemerkt; Drehzahl und Vorschub auf Knopfdruck von
   einer W-001-Maschine). Gerechnet wird je ae von 2 bis 50 % von D mit
   Spandickenausgleich (fz = h / sin φ); vf über der Grenze wird gekappt
   (der Span wird dünner), die Leistung aus kc1.1 gegen 80 % der
   Spindelleistung geprüft, die Leistungsgrenze auf 0,01 mm genau gesucht.
   Vorschlag: größtes Q innerhalb aller Grenzen, mit einem Satz, warum nicht
   breiter. „Als Einsatz übernehmen“ legt die gewählte Zeile als
   „Schruppen dynamisch“ an (ohne eigene Werte für den Werkstoff werden sie
   angelegt). Das Drehmoment bei kleiner Drehzahl prüft der Planer nicht –
   W-001 kennt es nicht.

## 11. Entscheidungen (Claude, zur Besprechung)

Je Entscheidung: was gewählt ist, die Alternative, und was sie kostet.

1. **Eigene Werkzeugliste im Addon, FreeCAD-Bibliothek als Ziel.**
   Alternative: direkt in FreeCADs Werkzeugbibliothek speichern – dann gäbe es
   nur eine Liste, aber 1.1.3 kann dort keine Schnittwerte ablegen, ae/ap
   kann keine Version, und die Bibliothek änderte ihr Format zuletzt mit jeder
   Version. Kosten der Wahl: zwei Listen, bis Stufe 2 sie verbindet.
2. **Eigene Werkstoffliste statt FreeCADs Werkstoffe.** FreeCADs Karten haben
   weder Härte noch Zusammensetzung und Zerspanungswerte nur für sechs
   generische Werkstoffe. Verbunden wird in Stufe 2 über die
   Werkstoffnummer. Alternative: FreeCAD-Werkstoffkarten ergänzen – das
   hieße, in FreeCADs Werkstoffbibliothek zu schreiben.
3. **Zwei Ebenen: „alle Werkstoffe“ und je Werkstoff.** Alternative: eine
   Zwischenebene je ISO-Gruppe (P, M, K …). Die kann später dazukommen, ohne
   dass sich etwas an den Daten ändert.
4. **Einsätze als freie Tabelle mit Vorlagen** statt fester Felder
   „Schruppen/Schlichten“. So passt Manuels „bei welchem ae welches ap“
   hinein, und jeder Fräser bekommt so viele Zeilen, wie er braucht.
5. **Keine mitgelieferten Schnittwerte.** vc und fz kommen aus dem Katalog des
   Herstellers; vorbelegt werden nur ae und ap aus dem Durchmesser. Die Hilfe
   nennt übliche Bereiche je ISO-Gruppe zur Orientierung. Alternative:
   Richtwerte je Werkstoff mitliefern – bequem, aber für einen bestimmten
   Fräser oft falsch.
6. **Verschleiß als „Schneidenweg je cm³“.** Einfach zu erklären und direkt aus
   den eingetragenen Werten. Alternative: ein Standzeitmodell (Taylor) – das
   bräuchte Werte, die niemand hat.
7. **kc1.1 und mc als Richtwerte in der Werkstoffliste**, nur für die
   Leistungsangabe im Vergleich. Fehlt ein Wert, fehlt nur diese Zeile.
8. **Speichern wie FreeCADs Einstellungen:** OK, Übernehmen, Abbrechen.
   Alternative: jede Eingabe sofort speichern – einfacher, aber ein
   versehentlicher Tastendruck wäre sofort in der Bibliothek.

### Dazugekommen beim Bauen von Stufe 2

9. **Übergabe als eigene Bibliothek „CAM-Addon“**, geschrieben über CAMs
   Asset-Verwaltung; jede Übergabe ersetzt die vorige vollständig.
   Alternative: in eine vorhandene Bibliothek des Benutzers mischen – dann
   könnte das Addon beim Aktualisieren fremde Werkzeuge treffen.
10. **Gesamtlänge und Schaft werden geschätzt** (Schneidenlänge + 2 × D,
    Schaft = D), wenn niemand sie einträgt. Seit P-2026-09-25-62 gibt es
    dafür zwei freiwillige Felder; leer zeigen sie grau die Schätzung. So
    muss niemand sie tippen, und wer simulieren will, kann.
11. **Eintauchvorschub = ⅓ des Vorschubs** (FreeCADs Vorgabe für Presets),
    beim Bohren der volle. Alternative: eine eigene Spalte je Einsatz.
12. **Einsatz für einen Werkzeug-Controller** wird vorgeschlagen: erst nach
    dem Namen des Controllers („T3 Schruppen dynamisch“), dann nach der
    Operation (Adaptiv → dynamisch, Tasche → Schruppen, Kontur → Schlichten),
    sonst die erste Zeile – immer änderbar.

### Dazugekommen beim Bauen von Stufe 3

13. **Der Planer hält ap fest und ändert ae.** Bei gleicher Spandicke braucht
    derselbe Abtrag dieselbe Leistung, egal wie er auf ae und ap verteilt
    ist; mit großem ap verteilt sich der Verschleiß auf mehr Schneide, mit
    kleinem ae ist der Zahn kürzer im Material. Deshalb: ap so groß wie
    sinnvoll (vorbelegt: Schneidenlänge, höchstens 2 × D), ae so groß, wie
    die Grenzen erlauben. Alternative: auch ap durchrechnen – das Ergebnis
    wäre immer „so viel ap wie möglich“.
14. **ae-Grenze 10 % von D als Vorgabe**, im Feld änderbar und gemerkt. Das
    ist Manuels Beispiel (1,2 mm bei Ø 12) und liegt in dem, was die
    Hersteller für die volle Schneidenlänge nennen (5 bis 15 %).
    Alternative: je ISO-Gruppe eine eigene Vorgabe – verlockend, aber ohne
    Herstellerangaben geraten.
15. **80 % der Spindelleistung an der Schneide**, fest. Alternative: ein
    Feld für den Wirkungsgrad – mehr zu verstehen, kaum genauer.
16. **Übernommen wird abgerundet** (ae auf 0,01 mm, fz auf 0,001 mm, vc auf
    0,1 m/min): Aufgerundet läge ein Wert, der genau an einer Grenze liegt,
    darüber.
17. **Die Grenzen der Maschine merkt sich der Planer auch nach Abbrechen** –
    die Maschine ändert sich ja nicht, wenn man den Vorschlag verwirft.
18. **Schrittweite und Zustelltiefe nur in passende Operationen.** Ein
    dynamischer Einsatz (großes ap) kommt nur ins Adaptiv: Nur dort hält
    FreeCAD den Eingriff klein; eine Tasche fährt zuerst eine volle Nut, und
    mit ap über die ganze Schneide bräche der Fräser. Die Kontur bekommt
    nie etwas, weil mit ihr auch ausgeschnitten wird. Die Formel des
    SetupSheets an der Zustelltiefe wird dabei entfernt (sonst stünde nach
    dem Neuberechnen wieder D da). Alternative: alle Operationen des TC
    bekommen ae und ap – einfacher, aber gefährlich.
19. **Aus CAM übernommene Werkzeuge mit vergebener Nummer bekommen eine
    freie, die auch in der Quelle nicht vorkommt** – sonst schöbe jedes
    umnummerierte Werkzeug die folgenden mit (T2 → T3 → T4 …). Ein Gravierstichel
    wird nicht zum Fasenfräser: Den Spitzenwinkel kennt die
    Werkzeugverwaltung nicht, zurück an CAM käme er mit 90° an.
20. **Neuer Durchmesser: ae und ap auf Nachfrage umrechnen, vc und fz nie.**
    ae und ap sind Anteile von D (Vollnut = D, dynamisch 10 %); vc und fz
    stehen im Katalog und hängen nicht einfach am Durchmesser. Alternative:
    fz mit D mitskalieren – für kleine Fräser oft ungefähr richtig, aber
    geraten.

## 12. Akzeptanzkriterien Stufe 1

Je Patch einer, als Klickweg:

- **Werkzeuge:** CAM → Werkzeugverwaltung → Werkstoff „1.4301“ tippen und
  wählen → darunter stehen Zusammensetzung und Härte; „+ Neu“ → Schaftfräser
  Ø 12, 3 Schneiden, OK → nach erneutem Öffnen ist er da.
- **Schnittwerte:** T3 wählen, Werkstoff 1.4301, „Eigene Werte anlegen“,
  Vollnut mit vc 120 und fz 0,05 → n 3183 U/min und vf 477 mm/min erscheinen;
  Werkstoff C45 wählen → „Es gelten die Werte für alle Werkstoffe“.
- **Eingriff:** In der Zeile „Schruppen dynamisch“ ae 1,2 tippen → das Bild
  zeigt einen schmalen Bogen, darunter „Eingriff 37°“.
- **Vergleich:** „Strategien vergleichen…“ → Vollnut gegen Schruppen
  dynamisch → das Urteil nennt das 2,5-fache Zeitspanvolumen und ein Zwölftel
  des Schneidenwegs.
- Bei allen: Manuel versteht die Fenster ohne Erklärung.
