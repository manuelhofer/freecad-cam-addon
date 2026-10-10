# Werkzeugkiste erweitern – das JSON-Format

Manuel, 2026-10-04: „die Werkzeuge sammeln musst ja nicht du machen … gibt's einen Importer …
wo du über JSON was hinzufügen lassen kannst … dass ich das einer lokalen KI geben kann, die sucht
die Sachen raus, und man kann die einlesen?“ – und: „mir schon mal sagen, wie die JSON-Datei
ausschauen soll, damit ich das schon mal dem KI-Agenten geben kann“.

Dieses Dokument ist das **Format**, in dem die „Werkzeuge der Hersteller“ (die Werkzeugkiste,
W-007) um eigene Reihen erweitert werden. Der Import selbst (Knopf „Aus Datei einlesen …“ im
Fenster „Werkzeuge der Hersteller“, Prüfung mit Meldungen) wird nach diesem Format gebaut;
eingelesene Dateien liegen dann im Ordner `CamAddon/werkzeugkiste/` neben der
`werkzeugverwaltung.json` (im FreeCAD-Benutzerordner). Ein vollständiges Beispiel mit echten
Daten: [`beispiele/werkzeugkiste_beispiel.json`](../beispiele/werkzeugkiste_beispiel.json).

## 1. Aufbau einer Datei

```json
{
  "format": "camaddon-werkzeugkiste",
  "version": 1,
  "reihen": [ { …eine Reihe… }, { … } ]
}
```

Eine **Reihe** ist ein Werkzeug eines Herstellers in mehreren Größen (eine Artikelgruppe,
z. B. „HOLEX VHM-Vollradiusfräser TiAlN 207125“ in Ø 2 … 12). Eine Datei darf beliebig viele
Reihen haben.

## 2. Felder einer Reihe

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `kennung` | ja | eindeutig über alle Dateien, nur `a-z`, `0-9`, `-` – am besten `marke-artikelgruppe`, z. B. `holex-207125` |
| `art` | ja | die Werkzeugart, genau einer der Namen aus Abschnitt 4 |
| `hersteller` | ja | wer es verkauft/herstellt, z. B. „Hoffmann Group“, „Gühring“ |
| `marke` | nein | z. B. „HOLEX“, „GARANT“ |
| `titel` | ja | die Bezeichnung der Reihe, wie der Hersteller sie nennt |
| `quelle` | ja | woher die Daten sind: Seite/Katalog **und Datum** („hoffmann-group.com, Produktseiten 207125-<Ø>, abgerufen 2026-10-04“) |
| `link` | nein | eine Seite für alle Größen (sonst je Größe) |
| `katalog` | nein | Katalog-PDF oder Datenblatt |
| `gemeinsam` | nein | Maße und Angaben, die für alle Größen gleich sind (Felder wie in `groessen`) |
| `schnittwerte` | nein | Schnittwerte, die für alle Größen gelten (Abschnitt 5) |
| `groessen` | ja | die Größen (Abschnitt 3), mindestens eine |

## 3. Felder einer Größe

Alle Maße in **mm**, Winkel in **Grad**, Zahlen mit Punkt (`10.5`, nicht `10,5`).

| Feld | Bedeutung (wie in der Werkzeugverwaltung) |
|---|---|
| `durchmesser` | Schneiden-Ø Dc (bei Gewindewerkzeugen der Nenn-Ø, M10 → 10; beim Gewindefräser der Fräser-Ø) |
| `schneiden` | Anzahl Schneiden Z |
| `schneidenlaenge` | Schneidenlänge Lc / l |
| `gesamtlaenge` | Gesamtlänge L |
| `schaft` | Schaft-Ø DS / d (leer: wie der Durchmesser) |
| `hals_d` | Hals-Ø d1 (Freischliff hinter der Schneide) |
| `hals_laenge` | Halslänge (Nutzlänge minus Schneidenlänge) |
| `eckradius` | Eckradius R (Torusfräser; Drehplatten) |
| `kegelwinkel` | Konikfräser: Winkel **je Seite** („3° je Seite“) |
| `flankenwinkel` | Gewinde 60°, Schwalbenschwanz 60° oder 45° |
| `spitzenwinkel` | über beide Schneiden: Bohrer 118°/130°/140°, NC-Anbohrer 90°/120°, Zentrierbohrer 60°, Fasenfräser/Kegelsenker 90° |
| `spitzen_d` | Fasenfräser/Kegelsenker: kleinster Ø der Schneide (0 = spitz); Radienfräser/Flachsenker: Führungszapfen |
| `profilradius` | Radienfräser: der Radius, den er fräst |
| `steigung` | Gewinde: Steigung in mm (M10 → 1.5) |
| `schneidenbreite` | Nutenfräser (Scheibenfräser), Einstechwerkzeug |
| `einstellwinkel` | Messerkopf 45° oder 90° |
| `eintauchwinkel` | wie steil er höchstens eintauchen darf (Rampe/Helix), wenn der Katalog es nennt |
| `schneidstoff` | `vhm` oder `hss` |
| `beschichtung` | Text, z. B. „TiAlN“ (nur zur Anzeige) |
| `artikel` | die Artikel-/Bestellnummer **genau wie beim Hersteller** („207125 6“, „VU494M06B-HI06“) |
| `name` | kurzer Name für die Liste (leer: aus Art, Marke und Ø gebildet) |
| `link` | die Seite dieser Größe (zum Bestellen) |
| `preis_netto` | Netto-Preis in Euro, wenn bekannt (nur zur Anzeige, mit Datum in `quelle`) |
| `schnittwerte` | Schnittwerte nur dieser Größe (Abschnitt 5) |

Nur Felder angeben, die die Art hat (Abschnitt 4) und die die Quelle nennt.

## 4. Werkzeugarten (`art`) und ihre Maße

| `art` | Werkzeug | Maße | Einsätze (Abschnitt 5) |
|---|---|---|---|
| `schaftfraeser` | Schaftfräser | durchmesser, schneiden, schneidenlaenge, gesamtlaenge, schaft, hals_d, eintauchwinkel | vollnut, schruppen, dynamisch, schlichten, planen |
| `kugelfraeser` | Kugelfräser | wie Schaftfräser | schruppen, schlichten |
| `torusfraeser` | Torusfräser | wie Schaftfräser + eckradius | vollnut, schruppen, dynamisch, schlichten |
| `konikfraeser` | Konikfräser | durchmesser (an der Spitze), schneiden, schneidenlaenge, gesamtlaenge, schaft, kegelwinkel | schlichten |
| `schwalbenschwanzfraeser` | Schwalbenschwanzfräser | durchmesser, schneiden, schneidenlaenge, gesamtlaenge, schaft, flankenwinkel, hals_d | vollnut |
| `lollipopfraeser` | Lollipop (Kugel > 180°) | durchmesser, schneiden, hals_d, hals_laenge, gesamtlaenge, schaft | schlichten |
| `fasenfraeser` | Fasenfräser | durchmesser, schneiden, schneidenlaenge, gesamtlaenge, schaft, spitzenwinkel, spitzen_d | fasen |
| `radienfraeser` | Radienfräser (Viertelkreis) | durchmesser, schneiden, profilradius, spitzen_d, schneidenlaenge, gesamtlaenge, schaft | verrunden |
| `planfraeser` | Messerkopf | durchmesser, schneiden (Platten), schneidenlaenge, gesamtlaenge, schaft, einstellwinkel | planen |
| `nutenfraeser` | Scheibennutfräser | durchmesser, schneiden, schneidenbreite, hals_d, gesamtlaenge, schaft | vollnut |
| `formfraeser` | Formfräser | durchmesser, schneiden, schneidenlaenge, gesamtlaenge, schaft | schlichten |
| `gewindefraeser` | Gewindefräser | durchmesser, schneiden, steigung, flankenwinkel, schneidenlaenge, hals_d, hals_laenge, gesamtlaenge, schaft | gewindefraesen |
| `bohrer` | Bohrer | durchmesser, schneiden, schneidenlaenge, gesamtlaenge, schaft, spitzenwinkel | bohren |
| `zentrierbohrer` | Zentrierbohrer | wie Bohrer | zentrieren |
| `nc_anbohrer` | NC-Anbohrer | wie Bohrer | zentrieren |
| `gewindebohrer_rechts` | Gewindebohrer rechts | durchmesser, steigung, schneidenlaenge, gesamtlaenge, schaft | gewindebohren |
| `gewindebohrer_links` | Gewindebohrer links | wie rechts | gewindebohren |
| `kegelsenker` | Kegelsenker | durchmesser, schneiden, spitzenwinkel, spitzen_d, gesamtlaenge, schaft | senken |
| `flachsenker` | Flachsenker | durchmesser, schneiden, spitzen_d, schneidenlaenge, gesamtlaenge, schaft | senken |
| `reibahle` | Reibahle | durchmesser, schneiden, schneidenlaenge, gesamtlaenge, schaft | reiben |
| `bohrstange` | Bohrstange | durchmesser, schneiden, schneidenlaenge, gesamtlaenge, schaft | ausdrehen |
| `ausspindelwerkzeug` | Ausspindelkopf | wie Bohrstange | ausdrehen |

Drehwerkzeuge und Taster (`drehwerkzeug`, `einstechwerkzeug`, `gewindedrehwerkzeug`, `taster`)
haben keine Schnittwerte – sie gehen auch, aber nur mit Maßen.

## 5. Schnittwerte

Je **Werkstoffklasse** und **Einsatz** ein Satz Werte:

```json
"schnittwerte": {
  "P1": {
    "schruppen": {"vc": 240, "fz": 0.08},
    "vollnut":   {"vc": 240, "fz": 0.06, "ap": 0.5, "ae_d": 1.0}
  },
  "M": { "schruppen": {"vc": 80, "fz": 0.056} }
}
```

| Wert | Bedeutung |
|---|---|
| `vc` | Schnittgeschwindigkeit in m/min |
| `fz` | Vorschub je Zahn in mm (Fräser) |
| `f` | Vorschub je Umdrehung in mm/U (Bohrer, Senker, Reibahlen, Bohrstangen – wenn der Katalog es so nennt; das Addon rechnet fz = f ÷ Z) |
| `ap` / `ap_d` | Schnitttiefe in mm – oder als Vielfaches von D (`0.05` = 0,05 × D) |
| `ae` / `ae_d` | Eingriffsbreite in mm – oder als Vielfaches von D |

Was fehlt, schätzt das Addon wie bisher – aber nie schneller als die höchste vc, die die Datei
für diese Klasse nennt. Gewindebohren braucht kein fz (der Vorschub ist die Steigung).

**Wo gelten sie?** `schnittwerte` der Reihe gelten für alle Größen; `schnittwerte` einer Größe
ergänzen und überschreiben sie Wert für Wert (im Beispiel: vc für alle Größen an der Reihe, fz je
Größe).

**Werkstoffklassen** – nur angeben, wofür die Quelle Werte nennt, **nie raten**:

| Klasse | Werkstoffe | Spalte der Hoffmann-Anwendertabelle |
|---|---|---|
| `P1` | unlegierter und niedrig legierter Stahl, Einsatz- und unvergüteter Vergütungsstahl, bis ~750 N/mm² | „Stahl < 750 N“ |
| `P2` | vergüteter Stahl, Werkzeugstahl, rostfrei martensitisch, bis ~1100 N/mm² | „Stahl < 1100 N“ |
| `M` | rostfreier Stahl (austenitisch, INOX) | „INOX < 900 N“ |
| `K` | Guss (GG, GGG) | „GG(G)“ |
| `N1` | Aluminium | „Alu“ |
| `N2` | Kupfer, Messing, Bronze | „CuZn“ |
| `N3` | Kunststoffe | – |
| `S` | Titan, Nickelbasis (hitzebeständig) | – |
| `H` | gehärteter Stahl | „< 55 HRC“ |

Bei Hoffmann sind die Spaltenköpfe der Anwendertabelle Bilder (Alu, Stahl < 500 N …); die Zahl
darunter ist die vc in m/min.

**Einsätze** – welcher Wert des Katalogs wohin gehört:

| Einsatz | im Katalog meist |
|---|---|
| `vollnut` | Nutenfräsen, Vollnut (ae = D) |
| `schruppen` | Besäumen, Eckfräsen, Umfangsfräsen |
| `dynamisch` | Trochoidal, HPC/HDC dynamisch, Adaptiv |
| `schlichten` | Schlichten; beim Kugelfräser Kopierfräsen |
| `planen` | Planfräsen |
| `fasen`, `verrunden`, `gewindefraesen`, `bohren`, `zentrieren`, `gewindebohren`, `senken`, `reiben`, `ausdrehen` | wie sie heißen |

## 6. Auftrag an einen KI-Agenten (zum Kopieren)

> Suche für die Werkzeugarten aus Abschnitt 4 günstige, gängige Werkzeuge bei einem Händler mit
> vollständigen Datenblättern (z. B. Hoffmann Group – Marken HOLEX und GARANT –, WEMAG, Gühring,
> Ceratizit). Lege je Artikelgruppe eine Reihe im Format dieses Dokuments an, mit den gängigen
> Größen. Übernimm **nur Werte, die auf der Seite oder im Katalog stehen** – Maße, Artikelnummer
> genau wie dort, Link je Größe, Netto-Preis, Schnittwerte (vc aus der Anwendertabelle der
> Werkstoffgruppen nach Abschnitt 5, fz/ap/ae aus den technischen Daten). Was nicht dasteht,
> weglassen – nicht schätzen. Schreib in `quelle`, woher die Daten sind und an welchem Tag. Gib
> eine Datei `werkzeugkiste_<hersteller>_<datum>.json` aus, die genau dem Beispiel
> `werkzeugkiste_beispiel.json` folgt.
>
> Dabei gilt: Nur Werkzeuge, deren Form eine Art aus Abschnitt 4 ist – Tonnenfräser, Linsenfräser
> und andere Sonderformen weglassen, nicht einer ähnlichen Art zuordnen. Jede Art hat
> kennzeichnende Maße (Konikfräser: `kegelwinkel`; Torusfräser: `eckradius`; Radienfräser:
> `profilradius`; Nutenfräser: `schneidenbreite`; Gewinde: `steigung`): immer als Feld, nie nur im
> Titel. `beschichtung` und `preis_netto` in ihre Felder, nicht in den Titel; `titel` ist die
> Bezeichnung der Reihe ohne Größe und Preis.

## 7. Einlesen – und was doppelt ist

Im Fenster **Werkzeuge der Hersteller …** (Werkzeugverwaltung) liest **Aus Datei einlesen …**
eine Datei in diesem Format; **Vorlage speichern …** schreibt das Beispiel als Datei. Eine
eingelesene Datei liegt danach im Ordner `CamAddon/werkzeugkiste/` neben der
`werkzeugverwaltung.json`; ihre Reihen stehen im Baum wie die eingebauten (der Tooltip nennt die
Datei). Eine Datei gleichen Namens ersetzt ihre frühere Fassung. Die Prüfung meldet je Zeile:

- **Fehler** – die Reihe bleibt draußen: Pflichtfeld fehlt, Kennung ungültig, in der Datei doppelt
  oder schon belegt (eingebaute Kiste oder andere Datei), unbekannte Werkzeugart, keine Größen.
- **Hinweise** – übernommen, aber: ein kennzeichnendes Maß der Art fehlt (Konik ohne
  `kegelwinkel`), der Titel nennt eine Form, die das Addon nicht hat (Tonnenfräser),
  unbekanntes Feld (ausgelassen), Feld anders geschrieben
  („gesamtlänge“ → `gesamtlaenge`, „auskraglaenge“ → Auskragung), keine Zahl, unbekannte
  Werkstoffklasse oder ein Einsatz, den die Art nicht hat, Schneidstoff unbekannt (es gilt VHM;
  „HM“, „HSS-E“, „HSS-Co“ werden verstanden).
- **Doppelt** – die Größe bleibt draußen, weil es sie schon gibt (Manuel, 2026-10-10: „wenn
  jemand 3 mal den Schaftfräser 12 von Hoffmann einpflegen will, ist das unnötig … exakt
  verglichen“): **gleicher Hersteller und gleiche Artikelnummer** (Schreibweise und Leerzeichen
  egal), oder **ohne Artikelnummer exakt dieselben Maße** (Art, Hersteller, Marke, Beschichtung,
  Schneidstoff, Schneiden, jede Länge, jeder Winkel, die Steigung). Zwei verschiedene
  Artikelnummern mit gleichen Maßen sind zwei Produkte und bleiben beide. Verglichen wird gegen
  die eingebaute Kiste, die anderen Dateien und die Datei selbst.

Beim **Hinzufügen** in die eigene Werkzeugkiste gilt dasselbe: Was es dort schon gibt – gleicher
Name, gleiche Artikelnummer oder (ohne Nummer) gleiche Maße –, bleibt, wie es ist.

Schnittwerte aus der Datei werden Katalogwerte: `f` wird fz je Schneide, `ap_d`/`ae_d` Vielfache
von D; fehlt vc oder fz, steht der Richtwert ein – vc nie über der höchsten, die die Datei für die
Klasse nennt. Eine Reihe ganz ohne Schnittwerte trägt „Richtwerte (geschätzt)“ in der Bezeichnung.
Ein zweites Beispiel mit echten Daten, 79 Reihen ohne Schnittwerte, von einem KI-Agenten nach
Abschnitt 6 zusammengestellt (Manuel, 2026-10-07):
[`beispiele/werkzeugkiste_hoffmann_2026-10-07.json`](../beispiele/werkzeugkiste_hoffmann_2026-10-07.json).
