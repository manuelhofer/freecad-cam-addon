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
| Name | – | wie in der Steuerung (T="Fräser VHM 12"), frei; leer: „Schaftfräser T1 VHM D12 L30“ (P-2026-09-26-33) |
| Art | – | Schaftfräser, Torusfräser, Kugelfräser (bis P-2026-09-26-54 „Radiusfräser“), Bohrer, Fasenfräser; alle 26 Arten: `docs/spezifikation_werkzeugarten.md` |
| Durchmesser D | mm | Pflicht |
| Schneidenzahl z | – | Pflicht (Bohrer: 2) |
| nutzbare Schneidenlänge | mm | für ap und die Beurteilung |
| Eckradius | mm | nur Torusfräser |
| Gesamtlänge | mm | nur für CAM; leer: Schneidenlänge + 2 × D, mindestens 3 × D |
| Schaft-Ø | mm | nur für CAM; leer: wie D |
| Schneidstoff | – | VHM, HSS |
| Bezeichnung | – | frei: Hersteller, Bestellnummer, Beschichtung … |

Die Liste zeigt je Werkzeug eine Zeile: `T3  Schaftfräser Ø 12 · z 3 · VHM`,
mit Namen `T3  Fräser VHM 12 · Schaftfräser Ø 12 · z 3 · VHM`.

## 6. Schnittwerte

### 6.1 Je Werkstoff – oder für alle gleich

Jedes Werkzeug hat Zeilen **„für alle Werkstoffe“** und darf zusätzlich
**je Werkstoff eigene** haben – gespeichert je Werkstoff eine Liste.

*Stand 2026-10-01 (P-2026-10-01-17; Manuel: „das Material muss zu den
Schnittwerten … wenn ich Schnittwerte anlege, muss ich das Material
auswählen“):* Die Tabelle zeigt **alle Zeilen des Werkzeugs**, vorn in jeder
Zeile der **Werkstoff**, für den sie gilt – eine Auswahl je Zeile („Alle
Werkstoffe“, eigene, mitgelieferte nach ISO-Gruppe; die Angaben zum Werkstoff
als Tooltip). Eine neue Zeile („+ Einsatz“, Kopie, Planer) bekommt den
Werkstoff der gewählten Zeile, ohne gewählte Zeile „Alle Werkstoffe“; die
Spalte umstellen schiebt die Zeile in die Liste des anderen Werkstoffs; die
letzte Zeile eines Werkstoffs löschen gibt ihn frei – es gelten wieder die
Zeilen für alle. Die Werkstoff-Auswahl oben im Fenster und die Knöpfe „Eigene
Werte anlegen/löschen“ gibt es nicht mehr; oben bleiben „Werkstoffe…“ (die
Liste mit Suche und eigenen Werkstoffen) und mm/inch. Für Job und Assistenten
gilt unverändert: die Zeilen des Werkstoffs vom Rohteil, sonst die für alle.

*Vorher (bis 0.38.0):* Gezeigt wurde immer die Tabelle für den Werkstoff, der
oben gewählt war – mit „Eigene Werte für 1.4301 anlegen/löschen“.

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
  Herstellers. Dazu **„Gewählte Zeile kopieren“** – für eine Variante zum
  Vergleichen (P-2026-09-26-12). Gibt es den Namen einer neuen Zeile schon,
  bekommt sie eine Nummer („Schruppen dynamisch 2“), damit Vergleich und
  Job die Zeilen unterscheiden.
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
   dynamisch und Schruppen, Taschenform und Fläche ← Schruppen, Nute ←
   Vollnut, Profil ← nichts; die Namen wie im Menü des deutschen FreeCAD,
   P-2026-09-26-13). Damit geht Manuels „Loch auffräsen: einmal
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
   Warngrenze für ae in % von D (am Werkzeug gespeichert, Vorgabe 10 %;
   bis P-2026-09-26-40 eine feste „ae-Grenze“),
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
4. **Halter** (Stufe D, für die Kollisionsprüfung W-001 4c): eigene
   Halter-Verwaltung mit Kontur aus Zylindern und Kegeln, je Werkzeug ein
   Halter – eigene Spezifikation:
   [spezifikation_halter.md](spezifikation_halter.md) (Manuels
   Entscheidungen vom 2026-09-26, P-2026-09-26-93).

5. **Bestückung an der Maschine** (Stufe F) – Manuel, 2026-09-30: „wie kann ich
   das werkzeug wieder entladen aber ich wills nicht löschen ich will nur nicht
   das es einen platz belegt ... daher gabs ja auch die unterscheidung zwischen p
   und t“; auf die Wahl zwischen „ohne Nummer = nicht geladen“ (A) und
   „Bestückung P1 … Pn an der Maschine“ (B): „berücksichtigung an der
   Maschine“ – also B. Bisher gilt T-Nummer = Platz (T3 sitzt auf P3,
   spezifikation_halter.md 11.6, Punkt 4), und die Nummer steht am Werkzeug –
   ein Werkzeug ohne Platz gibt es nicht, zwei mit derselben Nummer auch nicht.

   **Das Modell:**
   - Die **Werkzeugverwaltung** ist der Werkzeugschrank: Form, Halter,
     Schnittwerte. Die **Nummer** am Werkzeug wird freiwillig – leer heißt
     „nicht geladen“; sie gilt nur noch, wo keine Maschine bestückt ist (etwa
     ein 3-Achs-Job ohne Maschine). „Jede Nummer nur einmal“ gilt nur unter
     Werkzeugen mit Nummer.
   - Die **Bestückung** steht an der **Maschine** (im Dokument der Maschine,
     mit ihr gespeichert): je Platz P1 … Pn ein Werkzeug aus dem Schrank oder
     leer. Ein Werkzeug steht höchstens auf einem Platz einer Maschine; auf
     einer anderen Maschine kann es auf einem anderen Platz stehen.
   - Im **Programm** ist T am Revolver der Platz (Fanuc `T0303`, Siemens ohne
     Werkzeugverwaltung `T3 D1`, Haas `T303`) – der Werkzeug-Controller eines
     Jobs auf dieser Maschine bekommt die Nummer des Platzes. Steuerungen mit
     eigener Werkzeugverwaltung (Magazin, `T="Name"`) folgen mit W-005.

   **Schritte:**
   - **F1 – Bestückung in „Maschine bearbeiten“:** ein Abschnitt „Bestückung“
     mit einer Zeile je Platz: P3, darin eine Auswahl der Werkzeuge aus dem
     Schrank („– leer –“ oben), daneben „Werkzeugverwaltung …“. Gespeichert am
     Maschinenobjekt (Platz → Kennung des Werkzeugs). Beim Bau einer Maschine
     (und beim ersten Öffnen einer älteren ohne Bestückung) wird sie aus den
     Nummern vorbelegt: T3 kommt auf P3 – so ändert sich für niemanden etwas,
     bis er umsteckt.
   - **F2 – Werkzeugverwaltung:** Nummer darf leer sein (Liste zeigt „–“ statt
     „T3“), „Jede Nummer nur einmal“ nur unter Werkzeugen mit Nummer, ein Knopf
     „Nummer entfernen (entladen)“ neben dem Feld.
   - **F3 – Jobs:** Der 4-Achs-Assistent bietet die Werkzeuge der gewählten
     Maschine an („P3 · Kugelfräser Ø 16 …“); nicht bestückte grau, mit „auf
     Platz …“ (freien Platz wählen, die Bestückung ändert sich mit). Der
     Controller bekommt die Nummer des Platzes. Ohne Maschine wie bisher.
   - **F4 – Prüfen:** Das Prüffenster nimmt den Platz aus der Nummer des
     Controllers (wie bisher) und sagt, wenn laut Bestückung dort ein anderes
     Werkzeug sitzt („Auf P3 steckt laut Maschine T… – im Job ist es …“).

   **Entscheidungen (Claude, zur Besprechung):**
   - F-E1 Wo steht die Bestückung? (a) an der Maschine – **Empfehlung**, sie
     gehört zur Maschine, mehrere Maschinen können verschieden bestückt sein;
     (b) im Werkzeugschrank – eine Bestückung für alle Maschinen.
   - F-E2 Die Nummer am Werkzeug: (a) freiwillig, nur ohne Maschine –
     **Empfehlung**, alte Jobs und 3-Achs-Jobs ohne Maschine laufen weiter;
     (b) ganz weg – dann bräuchte jeder Job eine bestückte Maschine.
   - F-E3 Neue Maschine: (a) Bestückung aus den Nummern vorbelegen –
     **Empfehlung**, nichts ändert sich ungefragt; (b) leer – jeder bestückt
     selbst.

   **Entschieden** (Manuel, 2026-09-30: „passt“): F-E1 (a), F-E2 (a), F-E3 (a).

   **Gebaut** (P-2026-09-30-56, 0.32.0): F1, F3, F4; F2 folgt.
   - **Modell** (`maschine.py`): Nur ausdrücklich bestückte Plätze tragen die
     Kennung ihres Werkzeugs (Eigenschaft `Werkzeug`, leer: frei; verborgen).
     Jeder andere Platz zählt nach der Nummer – T3 auf P3 –, außer das Werkzeug
     steckt schon auf einem anderen Platz (`bestueckung()`). So ist F-E3 erfüllt,
     ohne beim Bau etwas festzuschreiben: Eine Maschine, gebaut mit leerer
     Werkzeugverwaltung, bestückt sich mit den Werkzeugen, die später dazukommen;
     ältere Maschinen zählen wie bisher. `bestuecke()` steckt um; war das Werkzeug
     schon woanders bestückt, wird der Platz frei.
   - **F1** – Abschnitt „Bestückung“ in „Maschine bearbeiten“: je Platz eine
     Auswahl („– frei –“ oben), hinter einem Werkzeug, das woanders steckt, „– auf
     P5“; „Werkzeugverwaltung …“ öffnet sie, nach dem Speichern dort steht Neues
     gleich zur Wahl. Ein Schritt Rückgängig mit dem Dialog. Ohne Revolver (Fräse
     mit einer Spindel) fehlt der Abschnitt.
   - **F3** – 4-Achs-Assistent: In der Fräserliste „P3 · “ vor dem Fräser (vorn,
     sonst schnitt die schmale Liste es ab – P-2026-09-30-58); der Controller
     bekommt die Nummer des Platzes (Name und
     ToolNumber, auch beim Ändern). Nicht bestückt: ein gelber Satz; angelegt wird
     mit der Nummer aus der Werkzeugverwaltung – das Prüffenster sagt dann, was
     auf dem Platz steckt. (Auf einen freien Platz stecken aus dem Assistenten
     heraus ist nicht dabei: Die Maschine liegt meist in einem anderen Dokument,
     ihr Rückgängig gehörte nicht zum Schritt des Assistenten.)
   - **F4** – „Auf der Maschine prüfen“: Ruft ein Job einen Platz auf, auf dem laut
     Bestückung ein anderes Werkzeug steckt oder keins, sagt ein Hinweis, was dort
     steckt, wo das richtige steckt und was zu tun ist.

   **Abgelöst durch Stufe G** (Manuel, 2026-09-30, mit Bild von „Maschine
   bearbeiten“: „das ist irreführend .... ich denke die bestückung sollte je nach
   job funktionieren ... auserdem wird die bestückung nicht dargestellt auf der
   maschine ...“).

6. **Bestückung je Job** (Stufe G) – Manuel, 2026-09-30, auf die Wahl (a) Job fest
   mit Maschine, (b) dazu jeder Job mit eigener Bestückung, (c) Maschine in die
   Job-Datei kopieren: „ja jeder job hat seine eigene bestückung und man hat
   einfach die maschine die man ablegt und immer wieder laden kann“.

   **Das Modell:**
   - Die **Maschine** ist eine Datei, die man ablegt und für jeden Job lädt; sie
     kennt ihre Plätze, aber keine Bestückung. Der Job merkt sich die Datei (D-20,
     `reichweite.merke_maschine`).
   - Die **Bestückung** steht im **Job**, in seinen Werkzeug-Controllern: Deren
     Nummer (`ToolNumber`) ruft das Programm auf, und am Revolver ist sie der Platz
     – T3 steckt auf P3. Eine zweite Liste gibt es nicht; so können Programm und
     Bestückung nicht auseinanderlaufen.
   - Ein **Grundjob mit geschwenkten Ebenen** (3+2, Spezifikation Strategien 15) ist ein
     Programm: Seine Ebenen teilen seine Bestückung (P-2026-10-03-45,
     `bestueckung.aufspannung`).
   - Ein **Werkzeug des Jobs** sind alle Controller mit demselben Werkzeug aus der
     Werkzeugverwaltung (dieselbe Kennung), sonst mit demselben CAM-Werkzeug.
     Unbenutzte fremde Controller (FreeCADs „TC: 5mm Endmill“, D-30) zählen nicht.
   - Ein **neues Werkzeug** im Job bekommt den Platz, den es dort schon hat; sonst
     den seiner Nummer aus der Werkzeugverwaltung, wenn der im Job frei ist; sonst
     den ersten freien. Ohne Revolver (Fräse mit einer Spindel, keine Maschine)
     bleibt es bei der Nummer aus der Werkzeugverwaltung.
   - **Umlegen** ändert die Nummer aller Controller des Werkzeugs, und ihr Name
     folgt („T3 Schruppen“ → „T5 Schruppen“); steckt auf dem neuen Platz schon
     eines, tauschen die beiden.
   - Werkzeuge, die der Job nicht braucht, die aber im Revolver stecken bleiben,
     kommen später dazu (dann auch für die Kollision).

   **Schritte:**
   - **G1 – Rechenkern** `bestueckung.py` (ohne Oberfläche); der 4-Achs-Assistent
     gibt dem Controller den Platz aus dem Job („P3 · “ vor dem Fräser), das
     Prüffenster meldet zwei Werkzeuge auf einem Platz. „Maschine bearbeiten“
     verliert den Abschnitt „Bestückung“ und sagt stattdessen, wo sie jetzt steht;
     was 0.32.0/0.32.1 an Plätzen gespeichert hat, zählt nicht mehr.
   - **G2 – Zeigen:** Im Prüffenster und beim Abspielen stecken alle Werkzeuge des
     Jobs auf ihren Plätzen im Revolver und schwenken mit ihm.
   - **G3 – Fenster „Bestückung“:** Job wählen → „Bestückung“: Es lädt die
     Maschine des Jobs (wie „Auf der Maschine prüfen“) und zeigt den Revolver mit
     den Werkzeugen, daneben je Platz eine Auswahl der Werkzeuge des Jobs. Ein
     Schritt Rückgängig im Dokument des Jobs.

   **Gebaut** (P-2026-09-30-65, 0.33.0): G1, G2, G3.
   - **Rechenkern** `bestueckung.py`: `eintraege()` (die Werkzeuge des Jobs mit
     ihren Controllern), `auf_plaetzen()`, `doppelt()`, `platz_fuer()` (Platz im
     Job, sonst Nummer, wenn frei, sonst der erste freie; `vorgemerkt` für den
     zweiten Fräser desselben Schritts), `lege_um()` (tauscht, benennt die
     Controller um – nur, wo der Name mit „T3 “ beginnt). Die Plätze kommen von
     `reichweite.Pruefung.platznummern()`.
   - **Maschine:** `maschine.bestueckung/bestuecke/platz_von` sind weg; die
     Eigenschaft „Werkzeug“ von 0.32.0/0.32.1 bleibt an alten Plätzen verborgen
     und zählt nicht. „Maschine bearbeiten“ hat statt des Abschnitts einen grauen
     Satz unter „Aufnahmen“ (nur mit Revolver).
   - **4-Achs-Assistent:** „P3 · “ aus `platz_fuer`; der Controller bekommt den
     Platz. Sind alle Plätze belegt, sagt es der gelbe Satz, und es gilt die
     Nummer aus der Werkzeugverwaltung.
   - **Prüffenster:** einmal je Job „Auf P7 stecken im Job mehrere Werkzeuge: …“
     statt der vier Sätze von F4. Beim **Abfahren** stecken alle Werkzeuge des
     Jobs im Revolver (je Aufnahme ein Knoten, der ihr folgt); „Hinsehen“ blickt
     auf Werkstück und das Werkzeug der laufenden Operation. Die Bausteine
     (`werkzeug_knoten`, `flaechen`, …) sind Modulfunktionen in `gui_abfahren`.
   - **Fenster „Bestückung“** (`gui_bestueckung.py`, Befehl `CamAddon_Bestueckung`,
     in Leiste und Menü vor „Auf der Maschine prüfen“): Job, Maschine, je Platz
     eine Auswahl („– frei –“ nur, wo nichts steckt; „– auf P4“ hinter einem
     Werkzeug, das woanders steckt), rot bei zwei Werkzeugen auf einem Platz und
     bei Werkzeugen mit einer Nummer, die kein Platz ist; „Hinsehen“. In der
     3D-Ansicht der Maschine die Werkzeuge im Revolver und an jedem Platz sein
     Name (`SoText2`, obenauf). Umlegen ist ein Schritt Rückgängig im Dokument
     des Jobs; Schließen merkt die Maschine am Job und kehrt zu ihm zurück.
   - Noch nicht: Werkzeuge, die im Revolver bleiben, ohne dass der Job sie braucht
     (dann auch für die Kollision).
   - **F2 gebaut** (P-2026-10-04-35, Manuel: „kannst du bauen ja“): Nummer 0 heißt „nicht
     geladen“ – im Feld „–“ (`setSpecialValueText`), daneben „Entladen“; in der Liste „–“, im
     Satz der Kurzname („Schaftfräser Ø 12“, `wz.genannt`), sortiert zuletzt (`wz.nach_nummer`);
     „jede Nummer nur einmal“ nur unter Werkzeugen mit Nummer (`mit_nummer(0)` ist None). Im
     Job bekommt es ohne Revolver die Nummer, die es dort schon hat, sonst die kleinste, die
     weder ein Controller des Jobs noch ein Werkzeug der Werkzeugverwaltung trägt
     (`bestueckung.platz_fuer`, `job_schnittwerte.freie_nummer`) – nie T0; am Revolver den
     ersten freien Platz. In FreeCADs Werkzeugbibliothek steht es hinter allen anderen.

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
    Operation (Adaptiv → dynamisch, Taschenform → Schruppen, Profil → Schlichten),
    sonst die erste Zeile – immer änderbar.

### Dazugekommen beim Bauen von Stufe 3

13. **Der Planer hält ap fest und ändert ae.** Bei gleicher Spandicke braucht
    derselbe Abtrag dieselbe Leistung, egal wie er auf ae und ap verteilt
    ist; mit großem ap verteilt sich der Verschleiß auf mehr Schneide, mit
    kleinem ae ist der Zahn kürzer im Material. Deshalb: ap so groß wie
    sinnvoll (vorbelegt: Schneidenlänge, höchstens 2 × D), ae so groß, wie
    die Grenzen erlauben. Alternative: auch ap durchrechnen – das Ergebnis
    wäre immer „so viel ap wie möglich“.
14. **Warngrenze ae 10 % von D als Vorgabe**, am Werkzeug gespeichert
    (P-2026-09-26-40, Manuel: „ab 10 % ae bei voller Schneidenlänge rote
    Warnung … aber auswählbar sollte es schon sein“, egal wie viele
    Schneiden). Das ist Manuels Beispiel (1,2 mm bei Ø 12) und liegt in dem,
    was die Hersteller für die volle Schneidenlänge nennen (5 bis 15 %).
    Zeilen darüber sind rot, aber wählbar; der Vorschlag bleibt darunter.
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
    FreeCAD den Eingriff klein; eine Taschenform fährt zuerst eine volle Nut,
    und mit ap über die ganze Schneide bräche der Fräser. Das Profil bekommt
    nie etwas, weil mit ihm auch ausgeschnitten wird. Die Formel des
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

### Dazugekommen in der Nacht zum 2026-09-26

21. **Kopien und doppelte Namen bekommen eine Nummer** („Schruppen
    dynamisch 2“, die Kopie davon „… 3“) statt „Kopie von …“. So bleiben die
    Namen kurz und im Vergleich, im Job und im Namen eines
    Werkzeug-Controllers unterscheidbar. Alternative: die Kopie ohne
    eigenen Namen – dann hießen zwei Zeilen gleich.
22. **Die Hilfe nennt FreeCADs Operationen und Felder genau so, wie sie im
    Menü stehen** – auch „Nute“ und „Überlappungs-Prozentsatz“, obwohl
    „Nut“ und „Schrittweite“ üblicher sind. Wer die Hilfe liest, soll das
    Wort auf dem Bildschirm wiederfinden. Die Wörter sind aus FreeCAD
    ausgelesen (1.1.3 und Wochen-Build), nicht geraten.
23. **Eine dünne letzte Ebene (unter ¼ ap) meldet „Schnittwerte in den
    Job“ nur**, mit zwei Auswegen (etwas mehr ap, wenn die Schneide reicht;
    Rohteil oben bündig). Das Addon ändert ap nicht selbst: ap ist eine
    Entscheidung über Werkzeug und Werkstoff. Alternative: die Zustelltiefe
    so strecken, dass die Ebenen gleich dick werden (26 mm → 13 + 13) – das
    halbierte gerade das große ap, um das es beim dynamischen Fräsen geht.

### Dazugekommen nach Manuels erstem Test

24. **Nummer und Name** (Manuels Option A): Der Name steht frei neben der
    T-Nummer, genau wie an der Maschine – keine Ersetzung von Leerzeichen
    (Siemens erlaubt sie; der Bediener schreibt, was die Steuerung will).
    Leer gilt ein Name aus den Angaben, mit Punkt als Dezimalzeichen (der
    Name ist für die Steuerung). Ein doppelter Name wird gemeldet, bleibt
    aber erlaubt (Schwesterwerkzeuge). In CAM heißt das Werkzeug so, der
    Werkzeug-Controller „T3 Fräser VHM 12 – Schruppen dynamisch“. Als
    Aufruf ins NC-Programm kommt der Name nur mit einem eigenen
    Postprozessor – FreeCADs mitgelieferte rufen per Nummer. Alternative:
    ein Umschalter Nummer/Name – dann ginge eins von beiden verloren.
25. **Ein neues Werkzeug hat Beispielwerte, grau, aber gültig** (Manuel:
    wer Ø 12 stehen lässt, will Ø 12): je Art Ø 12 mit passender
    Schneidenzahl und -länge, beim Torusfräser Eckradius 1. Eingetippt ist
    eigen, auch derselbe Wert. Beim Wechsel der Art bekommen graue und
    leere Felder die Beispiele der neuen Art. Das Bild zeigt ohne
    Durchmesser die Form der Art mit Beispielmaßen, gestrichelt. Im Planer
    stehen ohne vc und fz der Zeile graue Beispiele für Stahl (VHM 120 m/min
    und 0,05 mm, HSS 30 m/min und 0,03 mm). Die Merker werden nicht
    gespeichert: Nach dem Laden ist jeder Wert eigen. Alternative: leere
    Felder mit Hinweis – dann sieht man nichts, bis alles eingetragen ist.
26. **ae und ap in mm oder in % von D, eine Wahl für die Tabelle**
    (P-2026-09-26-42, Manuel: „einen Switch zwischen %- und mm-Angabe,
    dass man beides eintragen kann“): beide Spalten zugleich, gemerkt in
    den Einstellungen, für alle Werkzeuge; gespeichert wird immer in mm.
    Prozent mit einer Nachkommastelle (208,3 %). Ohne Durchmesser mm.
    Alternative: je Spalte ein eigener Umschalter – doppelt so viel zu
    verstehen für einen seltenen Fall.
27. **Spitzenwinkel beim Bohrer** (P-2026-09-26-43, Manuel: „was es gibt,
    ist ein Spitzenwinkel, der ist vergessen worden“): ein Feld nur beim
    Bohrer, an der Stelle des Eintauchwinkels; leer gilt 118° (grau
    „üblich: 118“), wie bei Gesamtlänge und Schaft. Er geht als TipAngle
    an CAM und ins Bild; „Aus CAM übernehmen“ liest ihn. Die Schneidenzahl
    bleibt – sie macht aus f je Umdrehung fz. Alternative: Pflichtfeld mit
    118 vorbelegt – dann sähe man nicht, ob ihn jemand geprüft hat.
28. **Maßsystem mm oder inch, gespeichert wird metrisch** (P-2026-09-26-48,
    Manuel: „welche Einheiten verwendet werden (Standard metrisch, aber inch
    und so sollten möglich sein) … einen Schalter, wo man zwischen inch und
    mm switcht“): wählbar beim ersten Start, in den Einstellungen und rechts
    oben in der Werkzeugverwaltung; vorbelegt aus FreeCADs Einheitensystem
    (alle „Imperial“ = inch). Umgerechnet wird nur beim Zeigen und Lesen:
    Länge mm ↔ in (4 Stellen), fz/Spandicke mm ↔ in (5), vc m/min ↔ SFM,
    Vorschub mm/min ↔ ipm, Abtrag cm³/min ↔ in³/min, Schneidenweg m/cm³ ↔
    ft/in³; „Zeit für 100 cm³“ wird „Zeit für 5 in³“. Gerundet wird in der
    gezeigten Einheit (Vorlagen, Übernehmen aus dem Planer) – ½" bleibt
    0.5 in. Beispielwerte in inch sind runde Zoll-Maße (½", 400 SFM,
    0.002"). Metrisch bleiben Beschleunigung, Ruck, Winkel, Drehzahl, kW und
    die Werkstoffdaten (kc1.1 in N/mm²). Alternative: beides speichern (mm
    und inch) – dann könnten die beiden auseinanderlaufen.

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


## 13. Die Werkzeugkiste vorgefüllt (Manuel, 2026-10-02)

Manuel: „Ich hätte gerne die Werkzeugkiste vorgefüllt, und zwar Bohrer von Ceratizit
WL173060311 Classicline oder 1170305000 0095923748, von denen die Werte holen, Bohrer von Ø 2,
2,5, 3, 3,3, 4, 4,2, 4,5, 5, 6, 6,5, 6,8, 7, 8, 8,5, 8,8, 9, 10, 10,2, 10,5, 11, 11,8, 12, 12,5,
13, 13,5, 14, 15, 15,5, 17, 17,5, 18, 19; außerdem von Gühring 5596 Blauring C M5 ISO HSS
EV23120483 alle metrischen Gewindebohrer bis M30; und Fräser Jongen UNI-Mill VHM 494W-12 HI06
V-53939-FB2 in 3, 4, 5, 6, 8, 10, 12, 16, 20 – das als Referenz nehmen und sich generell für jede
Werkzeugart aus dem Netz ein Beispiel suchen und dort eintragen, am liebsten mit Internetseite
zum Bestellen, Link und Artikelnummer … direkt mit Bildern dabei, und direkt auch eine Liste
des Herstellers, PDF, wo der Benutzer draufklicken kann und sich das PDF öffnet … Entgraten:
Garant 208165 12, diese in 6, 8, 10, 12, 16. Wenn es bei irgendeinem Material keine Daten geben
sollte, dann schätze anhand der vorhandenen Daten, wie es funktionieren könnte, sodass auf
jeden Fall etwas drinsteht. Außerdem: Wenn ich in der Werkzeugkiste etwas verändere oder
hinzufüge, sollte es nach dem Neustart noch vorhanden sein. Fürs Drehen gibt es die
Normformen C, V, D usw. – die müssten mit rein.“ Dazu: „Messerkopf: such dir einen Messerkopf
aus dem Netz und dessen Werte für Stahl, mit Zähnezahl“; der Ø 12 darf bei kleinem ap ein
größeres ae fahren – „auch hier such dir aus dem Netz einen Fräser mit Zähnezahl“. Und: „Für
alle Fräser Beispielschnittwerte für die einzelnen Materialien und Bearbeitungsläufe aus dem
Netz suchen und direkt mit anbieten, wenn jemand einen Fräser erstellen will.“

- **Bohrer:** Ceratizit (die beiden Nummern sind zu prüfen), die 32 Durchmesser oben.
- **Gewindebohrer:** Gühring 5596 (HSS-E, ISO), M2 bis M30 im Regelgewinde; Gühring 8330
  (HSS-E TiAlN, Sackloch, 3 × D, M2–M16; P-2026-10-03-21, Maße und Bestell-Nr. „8330 12.000“
  aus dem Katalog „Top-Auswahl Gewindewerkzeuge“ von Gühring Schweiz, gültig bis 2026-12-31).
- **Fräser:** Jongen UNI-Mill VHM 494W, Ø 3, 4, 5, 6, 8, 10, 12, 16, 20.
- **Entgraten:** Garant 208165, Ø 6, 8, 10, 12, 16.
- **Messerkopf:** einer mit Werten für Stahl und seiner Schneidenzahl.
- **Je weitere Werkzeugart ein Beispiel:** Torus, Kugel, NC-Anbohrer, Kegelsenker, Reibahle,
  Gewindefräser, Radienfräser, Nutenfräser … (die 26 Arten in
  `spezifikation_werkzeugarten.md`).
- **Je Werkzeug:** Hersteller, Artikelnummer, Bestell-Link, Bild, Katalog oder Datenblatt
  (PDF) – im Werkzeugfenster anklickbar, öffnet im Browser.
- **Schnittwerte** je Werkstoffgruppe und Einsatz aus dem Katalog; fehlt eine Gruppe,
  geschätzt aus den vorhandenen und als „geschätzt“ gekennzeichnet. Wer ein neues Werkzeug
  anlegt, bekommt die Werte eines passenden Beispiels angeboten.
- **Bleibt nach Neustart:** Die eigene Werkzeugkiste liegt schon heute in
  `CamAddon/werkzeugverwaltung.json` im Benutzerordner von FreeCAD und überlebt Neustart und
  Update (Abschnitt 9). Die Vorbelegung kommt einmal hinein – beim ersten Öffnen oder über
  „Werkzeuge der Hersteller hinzufügen …“ – und überschreibt nie, was der Benutzer geändert
  hat.
- **Drehen:** die ISO-Formen der Wendeschneidplatten (C 80°, D 55°, V 35°, W 80°, T 60°,
  S 90°, R rund …) als Drehwerkzeuge.
- **Fertig, wenn:** Manuel die Werkzeugverwaltung öffnet und die Bohrer, Gewindebohrer,
  Fräser und Entgrater mit Werten, Bild und anklickbarem Katalog findet.
- **Gebaut (P-2026-10-02-46, 0.102.0):** `camaddon/werkzeugkiste.py` mit 27 Reihen, 91
  Werkzeugen: Ceratizit ClassicLine HSS DIN 338 (Manuels 32 Durchmesser, Längen nach DIN 338),
  Gühring 5596 M2–M30 (Längen nach DIN 371/376, Kernloch in der Bezeichnung), Jongen UNI-Mill
  VHM 494W HI06 Ø 3–20 (Ø 12 wie Manuels Fräser, die anderen nach DIN 6527 K), Garant 208165
  Ø 6–16 (als VHM-Fasenfräser 90° angenommen), Sandvik CoroMill 345 Ø 50 z 4, je weitere Art ein
  Beispiel, die Wendeplatten C, D, V, W, T, S, R (ISO 1832), Einstechen, Gewindedrehen. Im
  Werkzeugfenster die Felder Hersteller, Artikel-Nr., Bestellen und Katalog mit „Öffnen“; unter
  der Liste „Werkzeuge der Hersteller …“ (alle Reihen angehakt, Tooltip mit der Quelle).
  Schnittwerte je **Werkstoffklasse** statt je Werkstoff (`werkstoffe.klasse`: P1 bis 750
  N/mm², P2 vergütet und Werkzeugstahl, M, K, N1 Aluminium, N2 Kupfer/Messing, N3 Kunststoff,
  S, H): P1 unter „Alle Werkstoffe“, jede andere Klasse unter einem Vertreter (1.7225, 1.4301,
  0.6025, 3.2315, 2.0401, POM-C, 3.7165, 1.2379+H) – ein Werkstoff ohne eigene Zeilen nimmt die
  eines Werkstoffs seiner Klasse (`Werkzeug.verwandter`), sonst die für alle. So hat der Bohrer
  9 Zeilen statt 50.
  **Nicht erreicht:** Die Seiten der Hersteller (jongen.de, hoffmann-group.com, ceratizit.com,
  guehring.com, sandvik.coromant.com) waren aus der Umgebung gesperrt. Deshalb sind alle
  Schnittwerte Richtwerte aus Grundwerten je Einsatz und Faktoren je Klasse (in der
  Bezeichnung „Richtwerte (geschätzt)“); Artikelnummern nur, wo belegt oder von Manuel genannt
  (Gühring 5596 M3–M10 nach Händlerangabe, Jongen nach dem Muster von 494W-12, Garant 208165,
  CoroMill 345-050Q22-13M); Bestellen und Katalog sind Suchen nach Hersteller und Nummer, außer
  bei Garant (Hoffmann-Seite nach dem Muster). Keine Bilder der Hersteller: Das Werkzeugfenster
  zeichnet jedes Werkzeug aus seinen Maßen.
- **Gebaut (P-2026-10-02-47, 0.103.0):** Ein Werkzeug ohne Schnittwerte zeigt über der leeren
  Tabelle „Richtwerte eintragen“ (`werkzeugkiste.richtwerte_eintragen`: dieselben Grundwerte und
  Klassenfaktoren wie die Kiste, aus Art, Durchmesser, Schneiden, Schneidstoff); später über
  „+ Einsatz“ → „Richtwerte je Werkstoffklasse“ – nur für Klassen ohne eigene Zeilen.
- **Gebaut (P-2026-10-02-50, 0.106.0; Manuel, 2026-10-02: „Ja, kann man machen, aber ich hätte
  dennoch gerne die Möglichkeit, für die einzelnen Werkstoffe auch unterschiedliche Werte zu
  setzen“):** „+ Einsatz“ → „Eigene Werte für einen Werkstoff …“ fragt nach dem Werkstoff und
  gibt ihm eine Kopie der Zeilen, die bisher für ihn gelten (`Werkzeug.eigene_anlegen`: die
  eines Werkstoffs seiner Klasse oder die für alle; vorhandene bleiben). Ändert man sie, bleiben
  die anderen Werkstoffe der Klasse, wie sie sind – 1.4404 eigene, 1.4571 weiter wie 1.4301.
- **Gebaut (P-2026-10-02-54, 0.109.0; Manuel, 2026-10-02: „der Ø 12 darf bei kleinem ap ein
  größeres ae fahren … auch hier such dir aus dem Netz einen Fräser mit Zähnezahl“):** Der
  Schaftfräser hat den Einsatz „Planen“: 0,7 D breit, 0,1 D tief (`werkzeuge.vorlage`), in der
  Kiste und bei den Richtwerten mit vc und fz des Schruppens – bei ae über D/2 ist der Span so
  dick wie fz. Manuels Standardfräser plant mit ae 8,4, ap 1,2, fz 0,07, vc 85 (Garant/Hoffmann
  für Planfräsen mit VHM in Stahl bis 900 N/mm²: fz 0,08 bei Ø 14; die Seiten der Hersteller
  waren gesperrt, die Werte stehen in den Suchergebnissen). Das Planfräsen im Assistenten
  wählt zwischen „Planen“ und „Schruppen“ den Einsatz mit der kürzeren Zielzeit bis zu seinen
  Flächen; die Zielzeit vergleicht je Fräser seinen schnellsten Einsatz.

- **Gebaut (P-2026-10-02-91, 0.127.1; Manuel, 2026-10-02 nachts: „kümmer dich auch um die
  werkzeugliste“):** Die Seiten der Hersteller sind jetzt erreichbar. `camaddon/katalogwerte.py`
  hält, was ihre Kataloge sagen; `werkzeugkiste` nimmt es, wo es da ist, und schätzt nur den Rest
  (`Reihe.katalogwerte`, `_aus_katalog`).
  - **Jongen 494W:** Katalog „VHM 494W / 495W“ 11/2025 (PDF bei jongen.de/Downloads, als Katalog
    am Werkzeug). Bestell-Nr. (Manuels Ø 12: VU494M12B-HI06), Schneidenlänge, Nutzlänge, Hals,
    Schaft, Gesamtlänge; Schnittwerte je Ø und Werkstoffgruppe für Eckfräsen (→ Schruppen),
    Vollnuten und trochoidal (→ Dynamisch) – P1 Baustahl, P2 niedrig legiert, M INOX
    austenitisch, K GJL, S hitzebeständig. Schlichten und Planen nennt der Katalog nicht: vc und fz
    des Eckfräsens. Ø 3 gibt es in der Reihe nicht; Ø 4 und 5 nur mit Eckenradius (494W R, eine
    eigene Reihe als Torusfräser). Bestellen: die Suche im Jongen-Shop nach der Bestell-Nr.
  - **Garant 208165:** laut Datenblatt der Hoffmann Group ein VHM-Entgrater spiralisiert **60°**,
    TiSiN (angenommen war ein Fasenfräser 90°), Gesamtlänge je Ø, vc je Werkstoffgruppe, fz je Ø
    in Stahl; das Datenblatt (PDF) als Katalog am Werkzeug.
  - **Noch geschätzt:** Ceratizit, Gühring, Sandvik und die Beispiele (nächster Patch).
- **Gebaut (P-2026-10-03-02; Manuel, 2026-10-03 früh, nach dem ersten Blick auf die Kiste):**
  - **Werkstoffklassen statt Vertreter** („unglücklich, dass bei Werkstoff jetzt doch
    spezifische Werkstoffe drinstehen … wir nehmen die Obergruppen, aber man kann auch für
    einzelne Werkstoffe noch Werte setzen“): Die Zeilen einer Klasse stehen unter ihrer Kennung
    („M“), die Werkstoff-Spalte zeigt „M – rostfreier Stahl“ (`werkstoffe.klasse_text`), die
    Auswahl der Spalte bietet „Alle Werkstoffe“, die neun Klassen, dann die Werkstoffe. Ein
    Werkstoff ohne eigene Zeilen nimmt die seiner Klasse, sonst „Alle Werkstoffe“; ohne
    gewählten Werkstoff gelten „Alle Werkstoffe“, sonst P1 (`Werkzeug.einsaetze`). Alte Dateien
    mit Vertretern wandern beim Laden zu den Klassen (`werkzeuge._vertreter_zu_klassen`), Zeilen
    einzelner Werkstoffe bleiben. „Richtwerte eintragen“ lässt P1 aus, wenn es Zeilen für alle
    gibt – Manuels Standardfräser behält seine Werte für Stahl. Die Auswahl des Werkstoffs am
    Rohteil (Job, Assistenten) bleibt ohne Klassen.
  - **Die Liste als Baum** („vll dass man da auch was zum Aufklappen macht … die Gruppe
    Schaftfräser, die Gruppe Bohrer“): `gui_werkzeuge.Werkzeugbaum` – je Art eine Gruppe
    „Bohrer (30)“, zugeklappte Gruppen gemerkt (`WvZugeklappt`), die Suche zeigt nur Gruppen mit
    Treffern. **Mehrfach löschen** („wenn ich mehrere löschen möchte … vll sogar komplette
    Kategorien“): mehrere markieren oder eine Gruppe, „Löschen“ fragt mit der Anzahl.
  - **Die Kiste als Baum mit einzelnen Größen** („diese Einteilung … und EINZELNE Bohrer
    aufnehmen, nicht gleich alle“): Werkzeugart → Reihe → Größe, Haken dreistufig, „Alle
    anhaken“ / „Alle abhaken“; `werkzeugkiste.hinzufuegen` nimmt Reihen oder (Reihe, Nummer).
  - **Ceratizit nach Manuels Link** (Artikel 1170311000, cuttingtools.ceratizit.com): Die Reihe
    ist CoreLine **WPC UNI**, VHM 5 × D nach DIN 6537, Innenkühlung, TiAlN, 140° – nicht HSS
    DIN 338. Artikelnummer = 11703 + Ø in µm, Link je Größe auf die Produktseite; Nutzlänge,
    Gesamtlänge und Schaft je Bereich von den Seiten (Ø 3 … 19 nachgeschlagen). Ø 2 und 2,5 gibt
    es dort nicht – weggelassen (Frage an Manuel). Schnittwerte nennt die Seite nicht:
    Richtwerte für VHM-Bohrer mit Innenkühlung (vc 100 in P1, f je Ø), geschätzt.
  - **Hals-Ø d1 und Auskragung N (P-2026-10-03-05; Manuel, 2026-10-03, mit dem Jongen-Blatt:
    „das N fehlt uns in unserer Liste … die Auskragung … und der d1“):** Schaft-, Kugel- und
    Torusfräser zeigen die beiden Felder (`werkzeuge._HALS`). N ist ein Feld der Oberfläche
    (`Werkzeug.auskragung`: Schneidenlänge plus Hals), gespeichert bleibt der Hals
    (`hals_laenge`) wie bei Lollipop und Schwalbenschwanz; `hat_feld` kennt den Hals bei jeder
    Art mit N. Das Bild zeichnet den Hals (`werkzeugform._mit_hals`), Reichweite und Kollision
    rechnen mit ihm (sie lasen `hals_laenge` schon immer über `mass`). Die Kiste hatte die
    Werte schon (Jongen 494W: N 36, d1 11,2 bei Ø 12).
  - **GARANT von der Hoffmann Group statt Beispielen (P-2026-10-03-11; Manuel, 2026-10-03:
    „wo du nichts gefunden hast, beispielsweise bei dem Kugelfräser – Hoffmann Group oder WEMAG
    sind Anlaufstellen, wo du alles bekommst“):** Kugelfräser 207424 10 (Diabolo
    Vollradiusfräser HPC Ø 10, Z 3, L 100), Torusfräser 206260 10/1,0 (HPC ZOX, Z 3, LC 22,
    L 72), Lollipop 207175 10 (Kugelfräser 220°, Z 2, L 120 – Hals geschätzt), Gewindefräser
    139663 M10 (Master TM AlTiN, DC 8,1, Z 6, LC 20,25, L 82, Schaft 12, IK), Zentrierbohrer
    111000 2,5 (DIN 333 A), NC-Anbohrer 121020 10 (VHM 90°, L 70), Gewindebohrer links
    132800 M10, Kegelsenker 150152 20,5 (Präzision, DIN 335 C, Z 3, L 63), Reibahle 163000 10
    (H7 HSS-E, Z 6, LC 38, L 133) – je mit Artikel, Link auf die Seite und Maßen von dort
    (`werkzeugkiste._hoffmann`). Schnittwerte zeigt Hoffmann nur über ToolScout: weiter
    Richtwerte. Konik-, Schwalbenschwanz-, Viertelkreis-, Scheibennut- und Formfräser,
    Flachsenker, Bohrstange, Ausspindelkopf und Taster bleiben Beispiele (kein passender
    Einzelartikel gefunden; WEMAG nicht nachgeschlagen).
  - **Geklärt (Manuel, 2026-10-03):** „andere Hersteller aufnehmen“ war kein Wunsch nach
    einer Erweiterung – gemeint war von Anfang an: die Herstellerseiten nach Werten durchsuchen
    und je Werkzeugart ein paar reale Werkzeuge mit Werten und Bestell-Link zum Übernehmen
    anbieten („ja, es ist halt jetzt von Ceratizit und Hoffmann und Jongen, aber das ist ja
    egal“). Genau das ist der Baum. „Messerkopf“ fände er schöner als „Planfräser“ („aber
    egal“) – gelassen.

## 14. Die Drehrichtung am Werkzeug (Manuel, 2026-10-02)

Manuel: „Natürlich muss man die Drehrichtung des Werkzeuges im Werkzeug angeben.“

- **Heute:** Die Drehrichtung folgt aus der Art (Linksgewindebohrer rückwärts, Taster keine,
  sonst vorwärts) und steht am Werkzeug-Controller; die Bahnen rechnen den Gleichlauf nach dem
  Controller (P-2026-10-02-20).
- **Soll:** ein Feld „Drehrichtung: rechts (M3) / links (M4)“ am Werkzeug, vorbelegt nach der
  Art; der Controller übernimmt sie beim Anlegen.
- **Fertig, wenn:** ein links schneidender Fräser in der Werkzeugverwaltung einen Controller
  mit M4 bekommt und Kontur und Räumen mit ihm im Gleichlauf fahren.
- **Gebaut:** P-2026-10-02-40, 0.97.0.
