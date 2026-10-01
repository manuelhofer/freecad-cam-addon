---
project: freecad_cam_addon
language: de
timezone: Europe/Berlin
status: planung
stack: Python, PySide (Qt), FreeCAD-API (CAM-Workbench)
zielsystem: stabile FreeCAD-Version (1.1.3) und Wochen-Build, jedes Betriebssystem, keine bestimmte Maschine
patch_naming:
  pattern: "P-YYYY-MM-DD-XX <kurzbeschreibung>"   # im Commit-Betreff
  example: "P-2026-09-25-01 projektregeln"
---

# Verlauf (LOG/ARCHIV)

## P-2026-10-01-12 rundum-entgraten

### EINGELESEN
- W-003 V4d (`docs/spezifikation_vierachs.md`): „Rundum entgraten – an den Kanten der gewählten
  Flächen (auch zwischen ihnen und dem Rest) eine Fase mit dem Fasenfräser (oder dem Kugelfräser
  als Kantenbruch), Breite einstellbar (Vorschlag 0,3 mm); der Fräser folgt der Kante, die
  Rundachse dreht mit“ (Manuel: „Und Entgraten nicht vergessen“); W-006 4.1 Punkt 8, 4.3.3,
  S2; E5 (a): Vorschlag mit Grund, änderbar.
- `vierachs_huelle.je_winkel` (Hüllfläche je Winkel mit jeder Fräserform), `vierachs_bahn`
  (Punkt, `_eilgang`, `_zusammengefasst`, `_ende`, Befehle), `vierachs_plan` und
  `vierachs_planbahn` (Operation und Bahn als Vorlage), `restmaterial` (Abtrag, Vergleich,
  `fuer`), `kollision.INS_TEIL_ERLAUBT`, `gui_vierachs` (Block „Plan indexiert“),
  `fraeserform.kegel` und `werkzeugform.kegel` (der Fasenfräser), FreeCADs Deburr (nur 2D).

### DATEIEN
- Neu: `camaddon/vierachs_entgratbahn.py`, `camaddon/vierachs_entgraten.py`,
  `tests/test_vierachs_entgraten.py`, `tests/gui/szenario_vierachs_entgraten.py`
- `camaddon/gui_vierachs.py`, `camaddon/restmaterial.py`, `camaddon/kollision.py`,
  `camaddon/vierachs_operation.py`, `camaddon/job_schnittwerte.py`, `translations/de.json`,
  `translations/en.json`, `help/de|en/vierachs.html`, `README.md`,
  `docs/spezifikation_vierachs.md`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle Ø 20 mit Abflachung zwischen zwei Wänden, Fasenfräser Ø 8 (90°, Spitze Ø 1), Fasenbreite
0,3: Mit der Abflachung gewählt findet es ihre zwei langen Kanten zum Zylinder (Knick 36,9°),
mit den Wänden dazu deren Bögen oben (90°) – keine Innenkante, keine Naht, keine Stirnkante;
die Bahn steht je Punkt mit der Rundachse auf der Kante, die Spitze 0,3 unter der Berührung
(X 9,72), die Stücke um die Abflachung herum verkettet ohne Abheben; nah am Futter fallen Kanten
weg und werden gezählt; am Absatz einer Stufenwelle ein Ring rundum (eine Umdrehung). Der
Abtrag im Prüffenster zeigt die Fase nicht als blau; die Kollisionsprüfung erlaubt der
Operation das Teil. Im Assistenten ist der vierte Haken „Rundum entgraten“ vorgeschlagen, sobald
es Außenkanten und einen Fasenfräser gibt („Vorschlag: an – 2 Außenkanten …, Fasenfräser T3 ist
da“), „→ 2 Kanten, etwa …“; „Anlegen“ legt „Rundum entgraten T3“ an (2 Kanten, X 9,72, C je
Kante fest), Doppelklick ändert die Fasenbreite.

### DONE
- Bahn (`vierachs_entgratbahn`): `kanten()` (Außenkanten der gewählten Flächen über die
  Kanten des Körpers – Normalen beider Flächen, Richtung in die Fläche hinein über die Probe,
  `isInside` neben der Kante; Knick ≥ 10°; keine Naht, keine Stirnkante), `Entgratwerte`,
  `eindringtiefe()` (Fase: die Breite; Kugel: so tief, dass es so breit wird),
  `entgraten()` (Hüllfläche an allen Kantenpunkten auf einmal mit `je_winkel`, Schatten und
  Futterabstand sortieren Punkte aus, Stücke je Kante, Ringe erkannt und beim nächsten Punkt
  begonnen, Stücke verkettet – das nächste zuerst, ohne Abheben, wo es anschließt –,
  zusammengefasst mit höchstens 90° je Satz, Eilgang, Eintauchen, Länge im Vorschub).
- Operation `vierachs_entgraten.RundumEntgraten` (Breite, Abstände, Flächen; Kanten und
  Ausgelassen nur lesen), `bahn_fuer`, `vorschau` (gröber), `lege_an`, `aendere`,
  `ist_entgraten`, `kann_entgraten` (Fasen-, Kugel-, Lollipopfräser); `vo.ist_rundum`,
  `restmaterial.operationsarten_rundum`, „Schnittwerte in den Job“ mit Einsatz „Fasen“.
- Abtrag: `Abtrag.fasen` – je Entgrat-Operation die Eindringtiefe; die Zellen, die sie trifft,
  dürfen so tief ins Teil, ohne blau zu werden (`vergleiche(…, erlaubt)`); `fuer()` nimmt das
  Aufmaß der letzten Operation, die eins hat. Kollision: `vierachs_entgraten` in
  `INS_TEIL_ERLAUBT`.
- Assistent: Block „Rundum entgraten“ (Fräser, Einsatz, Fasenbreite, Vorschau, gelber Satz zur
  Lage), `_entgraten_vorschlagen` (kein Fräser / keine Kanten: gesperrt mit Satz; Fasenfräser:
  an; nur Kugel: aus, mit Satz), Anlegen, Ändern, „dazu“ beim Ändern des Schruppens, Platz am
  Revolver, Bedarf hinten, gemerkter Fräser. Dabei: „Plan indexiert“ wird nur noch
  vorgeschlagen, wenn es einen Fräser mit ebener Stirn dafür gibt (`va.plan.kein_fraeser`).
- Hilfe (de/en), README, Spezifikation (Stand V4d, mit der offenen Frage der schrägen Kante),
  Status.

### TEST
- `test_vierachs_entgraten` (neu): Kanten (Abflachung, Wände, alle, eine Wand allein,
  Eindringtiefe), Bahn (Fase, Rundachse, Eintauchen, verkettet, Länge, Bögen, Kugel, nah am
  Futter, Fehler, Befehle), Stufenwelle (Ring), Abtrag mit Fase (blau ohne, keins mit),
  Operation (anlegen, ändern, Stirn allein, Kugel, speichern und laden); `test_sprache`,
  `test_hilfe` – in 1.1.3 ok. Der erste Lauf fand drei falsche Erwartungen im Test (die Stücke
  verketten sich zu einer Fahrt, die Länge zählt auf dem Fasenradius, C liegt im Job anders)
  und dass die Bahn nach dem Laden um Tausendstel anders zusammengefasst wird (ein anderes
  Netz) – der Test prüft jetzt Kanten und Tiefe.
- `szenario_vierachs_entgraten` (neu) in 1.1.3 ok, Bilder angesehen. Der erste Lauf: Der
  Assistent nimmt an der vorgewählten Maschine die A-Achse mit der Stange längs X – das
  Szenario liest Rundachse und Werkzeugrichtung jetzt aus der Operation; und „Plan indexiert“
  war an (T1 mit Einsatz Schruppen kann es) – das Szenario nimmt den Haken heraus.

### NEXT
- Version 0.36.0, Push; W-006 S3 (2,5D Kern).

## P-2026-10-01-10 plan-zeilenende

### EINGELESEN
- `test_vierachs_plan` in 1.1.3: „längs über die Wände hinaus: −28,25 … −11,75“ – die Zeilen
  bei Y ±2,98 liefen in der Lage 10 (= Zylinderradius) 1,5 mm weiter als die mittlere.
- `camaddon/vierachs_planbahn.py` (`planen`, `drin`), `vierachs_huelle.je_versatz`.

### DATEIEN
- `camaddon/vierachs_planbahn.py`, `tests/test_vierachs_plan.py`, `help/de|en/vierachs.html`,
  `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Alle Zeilen einer Fläche enden an derselben Stelle vor der Wand (Welle Ø 20, Abflachung
−30 … −10, Fräser Ø 6: −26,75 … −13,25), in jeder Lage und bei jedem Versatz; über das Ende
der Fläche hinaus fährt der Fräser nur, wo nichts höher steht als die Fläche selbst (Absatz
nach unten, Stangenende).

### DONE
- Ursache: Die Lage auf dem Zylinderradius durfte den Zylinder neben der Wand streifen – die
  Hüllfläche der versetzten Stirn liegt dort um 0,01 … 0,15 mm unter dem Radius, weil die
  Stirn den Scheitel bei Y 0 nicht mehr trifft. Die Lage war also „frei“, aber über einem
  fremden Zylinder, der Sache der Rundum-Bahnen ist.
- Regel in `planen()`: Wo die Stirn über das Ende der Fläche ragt (Mitte näher als der
  Fräserradius am Flächenende), fräst sie nur, wenn die rohe Hüllfläche dort nicht höher
  liegt als Tiefe plus Aufmaß. Prüfung im Test (Zeilenenden je Versatz gleich), Hilfe,
  Spezifikation.

### TEST
- `test_vierachs_plan` in 1.1.3 ok; `szenario_vierachs_plan` in 1.1.3 ok.

### NEXT
- Version 0.35.0, Push; V4d Rundum entgraten.

## P-2026-10-01-09 testregel-weniger

### EINGELESEN
- Manuel, 2026-10-01: „Und weniger testest mehr Produktivität...“; 2026-09-30: „wenn DU sie für
  nötig hältst … Ich persönlich benötige keine Tests solange alles funktioniert“.
- `docs/arbeitsregeln.md` Abschnitt 5 (Prüfen vor dem Push), `CLAUDE.md` (Push-Regel).

### DATEIEN
- `docs/arbeitsregeln.md`, `CLAUDE.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Arbeitsregeln sagen, was vor einem Push läuft: die eine Prüfdatei und – wenn Manuel ein Bild
sehen soll – das eine Szenario zum geänderten Teil, in 1.1.3; kein zweiter Lauf im Wochen-Build
ohne Grund, kein voller Lauf nach jedem Patch, kein Warten auf einen Lauf im Hintergrund.

### DONE
- Abschnitt 5 „Nur prüfen, was nötig ist – und wenig“ mit Manuels Satz; der volle Lauf ist die
  Ausnahme (vor einem Stand zum Ausprobieren, nach vielen Änderungen am Kern, neue
  FreeCAD-Version – höchstens einmal am Tag, im Hintergrund, nach dem Push). `CLAUDE.md`
  verweist darauf.
- Der volle Lauf zu 0.34.0 (beide Versionen) lief dabei im Hintergrund zu Ende:
  am Ende 162 grün, kein Fehler.

### TEST
- Reine Doku – kein Lauf.

### NEXT
- „Plan indexiert“ (P-08) prüfen: `test_vierachs_plan`, `test_goldene_bahnen`,
  `test_restmaterial`, `szenario_vierachs_plan` in 1.1.3; Version 0.35.0, Push.

## P-2026-10-01-08 plan-indexiert

### EINGELESEN
- W-003 V4c (`docs/spezifikation_vierachs.md`): „Plan indexiert – eine ebene Fläche parallel zur
  Achse mit einem Fräser mit ebener Stirn: Die Rundachse steht fest, der Fräser fährt Zeilen wie
  beim Planfräsen (Zustellung ap, Zeilenabstand ae)“; offene Frage 1 (Versatz quer, Abfahren,
  Kollision, Abtrag); W-006 4.3.2 und S2; Manuel, 2026-09-29: „bei einer maschine mit y achse
  kann man ja auch diese verfahren um eventuelle stellen besser zu erreichen“; E5 (a).
- `camaddon/vierachs_bahn.py` (Punkt, Befehle, `_fahrten`, Rampe), `vierachs_huelle.py`
  (`je_winkel`, `_form_treffen`), `restmaterial.py` (Stange, `_block`, `_stirn`, `Abtrag`,
  `fuer`), `vierachs_schlichten.py` (Operation als Vorlage), `gui_vierachs.py` (Schritt 2),
  `abfahren.py` (Stationen mit den Rundachsen im Programm), `vierachs_achsen.py`
  (`Stangenachse.quer`).

### DATEIEN
- Neu: `camaddon/vierachs_planbahn.py`, `camaddon/vierachs_plan.py`, `tests/test_vierachs_plan.py`,
  `tests/gui/szenario_vierachs_plan.py`
- `camaddon/vierachs_bahn.py`, `camaddon/vierachs_huelle.py`, `camaddon/restmaterial.py`,
  `camaddon/vierachs_operation.py`, `camaddon/job_schnittwerte.py`, `camaddon/gui_vierachs.py`,
  `translations/de.json`, `translations/en.json`, `help/de|en/vierachs.html`, `README.md`,
  `docs/spezifikation_vierachs.md`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit Abflachung, Stange Ø 24, Schaftfräser Ø 6: Im Assistenten geht mit der gewählten
Abflachung der dritte Haken „Plan indexiert“ an („Vorschlag: an – eben längs der Stange: Face7
…“), die Vorschau sagt „→ 2 Lagen, 6 Zeilen, etwa 1 min“; „Anlegen“ legt „Plan indexiert T1“ an:
die Rundachse steht auf dem Winkel der Fläche, Lagen Ø 24 → 10 → 8, je Lage drei Zeilen längs
mit Y −2,98/0/2,98, die Zeilen enden vor den Wänden, hinein über die Rampe; die Sätze tragen Y
und ein festes C. Ohne ebene Fläche längs der Stange oder ohne Querachse ist der Haken gesperrt,
der graue Satz sagt, warum. Der Abtrag im Prüffenster trägt die Stange versetzt ab (über der
Abflachung die Ebene, daneben die Stange). Die Rundum-Bahnen bleiben, wie sie waren (goldene
Bahnen).

### DONE
- Bahn (`vierachs_planbahn`): `ebenen()` (ebene Flächen mit Normale quer zur Stange, nach
  außen; Winkel, Tiefe, Ausdehnung längs und quer), `netz_ohne()` (das Teil ohne die Fläche),
  `planen()` (Lagen, Zeilen quer mit Luft am Rand, Hüllfläche je Zeile über
  `vierachs_huelle.je_versatz`, Fahrten hin und her über `_fahrten`, Rampe oder senkrecht
  hinein, Eilgang mit Versatz), `Planwerte`, `Planbahn`, `ebener_radius()`.
- `vierachs_bahn.Punkt.q`; `befehle()` schreibt die Querachse, sobald ein Punkt versetzt ist;
  `_weg` mit dem Versatz.
- `restmaterial`: `schnitte()`/`_block()`/`_stirn()` mit Versatz (Scheibe: wo der Strahl die
  Ebene der Spitze trifft, quer von der Werkzeugachse gemessen; Kugel: die Mitte auf den Strahl
  projiziert; sonst ℓ = √(d² + (h · tan Δ − q)²)), `fahre_stuecke()` mit (n, 4), `Abtrag` mit q,
  `fuer()` nimmt die Werkzeugachse aus der Rundachse im Programm (−Drehsinn · C) und rechnet
  die Spitze darauf (r) und daneben (q) – für die Rundum-Bahnen dasselbe wie vorher.
- Operation `vierachs_plan.PlanIndexiert` (Zustellung, Zeilenabstand, Aufmaß, Abstände,
  Flächen, Eintauchwinkel; Ebenen, Lagen, Zeilen nur lesen), `bahn_fuer`, `vorschau`, `lege_an`,
  `aendere`, `ist_plan`; `vo.ist_rundum` kennt sie, `restmaterial.operationsarten_rundum`,
  „Schnittwerte in den Job“ mit Einsatz „Planen“.
- Assistent: Block „Plan indexiert“ (Fräser mit ebener Stirn, Einsatz, drei Felder, Vorschau),
  `_plan_vorschlagen` (gesperrt ohne ebene Fläche oder ohne Querachse, sonst Vorschlag mit
  Grund), Anlegen, Ändern, „dazu“ beim Ändern des Schruppens, Platz am Revolver, Bedarf hinten,
  gelber Satz zur Lage. Hilfe (de/en), README, Spezifikation, Status.

### TEST
- `test_vierachs_plan` (neu): Ebene, Bahn (Lagen, Zeilen, Wände, Rampe, Y im Befehl), Fehler,
  Abtrag mit Versatz (Ebene über der Abflachung, Kugel versetzt), Operation (anlegen, ändern,
  Kugelfräser, Stirn, speichern und laden); dazu `test_restmaterial`, `test_goldene_bahnen`
  (Rundum-Bahnen unverändert), `test_sprache`, `test_hilfe` – in 1.1.3 ok (Testregel
  P-2026-10-01-09: nur die Prüfungen zum geänderten Teil, nur die stabile Version).
- `szenario_vierachs_plan` (neu) in 1.1.3 ok, Bilder angesehen.
- Der erste Lauf fand die Zeilen über die Wände hinaus (P-2026-10-01-10).

### NEXT
- P-2026-10-01-10 (Zeilenende), Version 0.35.0, Push; V4d Rundum entgraten.

## P-2026-10-01-06 linien-laengs

### EINGELESEN
- W-006 (`docs/spezifikation_strategien.md`), 4.3.1 und S2: „Linien längs – Zeilen längs der
  Achse bei festem Winkel: Nut, Abflachung, Nocke mit Kugel-/Torusfräser“; E1 (a) S2 zuerst,
  E5 (a) Vorschlag mit Grund, änderbar (Manuel, 2026-10-01: „Also ja“).
- W-003 V4c (`docs/spezifikation_vierachs.md`): Linien im Winkelabstand Schrittweite ÷ Radius,
  gegenläufig, nur über der Fläche; die offenen Fragen 2 und 3.
- `camaddon/vierachs_bahn.py` (Spirale, Zeilen hin und her, `_fahrten`), `vierachs_schlichten.py`,
  `gui_vierachs.py` (Schritt 2, Schlichten), `tests/test_vierachs_schlichten.py`,
  `tests/test_goldene_bahnen.py`, `tests/gui/szenario_vierachs_flaechen.py`.

### DATEIEN
- `camaddon/vierachs_bahn.py`, `camaddon/vierachs_schlichten.py`, `camaddon/gui_vierachs.py`,
  `translations/de.json`, `translations/en.json`, `help/de|en/vierachs.html`, `README.md`,
  `docs/spezifikation_vierachs.md`, `docs/STATUS_SNAPSHOT.md`, `tests/test_vierachs_schlichten.py`,
  `tests/test_vierachs_schlichten_op.py`, `tests/test_goldene_bahnen.py`,
  `tests/golden/welle_absatz_schlichten_linien.json` (neu), `tests/gui/szenario_vierachs_flaechen.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Rundum schlichten“ hat ein Muster: Spirale (wie bisher) oder Linien längs der Achse bei festem
Winkel – gegenläufig, im Abstand Schrittweite ÷ größter Radius, mit Bereich nur die Linien und
Stücke über den gewählten Flächen, die Stufen nach dem Schruppen wie bei der Spirale. Im
Assistenten steht unter dem Aufmaß „Muster“ mit dem Vorschlag und grau dem Grund: mit einer
Abflachung „Vorschlag: Linien längs – die gewählten Flächen gehen nicht rundum.“, rundum die
Spirale; wer anderes wählt, behält es. Die Operation trägt „Muster“ und „Linien“; die Spirale
rechnet unverändert (goldene Bahnen).

### DONE
- Rechenkern: `_schlichten_linien` (Linienwinkel, Hüllfläche nur auf den Linien mit Material,
  Fahrten über `_fahrten` mit einer Lücke an beiden Enden längs, Einfahrt, Sehnenfehler,
  Zusammenfassen, Stufen); Rundum 0,6 s, Abflachung 0,2 s. Linien ohne Material bleiben als
  Lücke in der Reihe, die nach einer Lücke beginnt – so ist eine Abflachung beiderseits der Naht
  bei 0° ein Stück (vorher sprang die Rundachse 268°). `Schlichtwerte.muster`,
  `Schlichtbahn.linien`.
- Operation: Aufzählung „Muster“ (Spirale/Linien; ältere Dateien Spirale), „Linien“ nur lesen;
  `bahn_fuer`, `vorschau`, `lege_an`, `aendere` mit `muster`.
- Assistent: Liste „Muster“ mit Grund (`_muster_vorschlagen`, E5), „→ 126 Linien längs, etwa …“;
  beim Ändern das Muster der Operation. Hilfe (de/en), README, Spezifikation V4c (Stand).

### TEST
- `test_vierachs_schlichten` (Abflachung in Linien: im Bereich, eine Hauptfahrt über die Naht,
  gegenläufig, Abstand ≤ 2,86°, die Kugel nie im Teil und zwischen den Punkten auf der Ebene;
  eine Stufe dicht an den Wänden; rundum 360 Linien auf der Hüllfläche), `test_vierachs_bahn`,
  `test_goldene_bahnen` (neu `welle_absatz_schlichten_linien`, die alten unverändert),
  `test_vierachs_schlichten_op` (629 Linien, Muster hin und zurück), `test_sprache`, `test_hilfe`
  in 1.1.3 ok; `test_vierachs_schlichten_op`, `test_goldene_bahnen` in 26.3 ok.
- `szenario_vierachs_flaechen` (Vorschlag Linien längs mit Grund, Spirale rundum, Muster an der
  Operation) in 1.1.3 und 26.3 ok, `szenario_vierachs_schlichten` in 1.1.3 ok; Bild angesehen:
  „Muster: Linien längs“ mit dem grauen Grund unter dem Aufmaß. Der volle Lauf nach dem Push.

### NEXT
- Version 0.34.0, Push; Plan indexiert (V4c, Versatz quer), V4d Entgraten.

## P-2026-10-01-04 so-gehts

### EINGELESEN
- Durchsicht 3, D-54 (`docs/durchsicht_bedienbarkeit.md`): „eine Hilfeseite „So geht’s“ mit sechs
  Schritten, je ein Satz und der Knopf dazu … als erste Seite des Hilfefensters und im Menü
  „CAM-Addon“ oben und im README“; Manuel, 2026-10-01: „Also ja“ zur Empfehlung (a).
- `camaddon/hilfe.py`, `camaddon/gui_hilfe.py`, `camaddon/gui_start.py` (Menü, D-13), die
  Überschriften aller Hilfeseiten, `tests/test_hilfe.py`, `tests/gui/szenario_erster_start.py`.

### DATEIEN
- Neu: `help/de/so_gehts.html`, `help/en/so_gehts.html`, `resources/icons/so_gehts.svg`
- `camaddon/hilfe.py`, `camaddon/gui_hilfe.py`, `camaddon/gui_start.py`,
  `translations/de.json`, `translations/en.json`, `tests/gui/szenario_erster_start.py`,
  `README.md`, `docs/durchsicht_bedienbarkeit.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Menü „CAM-Addon“ steht oben „So geht’s“; der Eintrag öffnet die Hilfeseite mit den sechs
Schritten (Maschine, Werkzeuge, Teil und Bearbeitung, Bestückung, Prüfen, Programm), je mit dem
Knopf dazu und Verweisen auf die Seiten; am Ende alle Seiten der Hilfe nach Maschine, Werkzeuge,
Job. Die Werkzeugleiste bleibt bei acht Knöpfen. `test_hilfe` prüft die neue Seite mit.

### DONE
- Seite auf Deutsch und Englisch („Getting started“), erstes Thema in `hilfe.THEMEN`.
- Befehl `CamAddon_SoGehts` (`gui_hilfe.BefehlSoGehts`, eigenes Symbol) oben im Menü, mit
  Trennstrich; README-Punkt „So geht’s“; Durchsicht und Status nachgeführt.

### TEST
- `test_hilfe`, `test_sprache` in 1.1.3 ok.
- `szenario_erster_start` (Menü mit elf Einträgen, „So geht’s“ oben, Seite offen, Bild
  `4c_so_gehts`) und `szenario_hilfe` in 1.1.3 ok; Bilder angesehen: Menü mit Symbol und
  Trennstrich, die Seite mit Überschrift, Schritten und blauen Verweisen. 26.3 läuft.

### NEXT
- Version 0.33.3, Push; S2 rundum fertig (V4c Linien längs, Plan indexiert, V4d Entgraten).

## P-2026-10-01-02 teil-am-ende

### EINGELESEN
- Manuel, 2026-09-30: „nach dem bearbeiten sieht man das "soll" teil nicht mehr“; 2026-10-01
  zur Wahl (a) Haken „Teil“ im Abspieler: „Also ja“.
- P-2026-09-30-45 (Teil am Ende ausgeblendet, weil sein Hellblau wie „blau: im Teil“ aussah),
  `camaddon/gui_abfahren.py` (Bild, Abspieler, Haken „Bahn“), `camaddon/gui_reichweite.py`.

### DATEIEN
- `camaddon/gui_abfahren.py`, `camaddon/gui_reichweite.py`, `translations/de.json`,
  `translations/en.json`, `help/de|en/reichweite.html`,
  `tests/gui/szenario_vierachs_schruppen.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Abspieler steht neben „Bahn“ der Haken „Teil“ (gemerkt, anfangs gesetzt). Mit Haken ist das
fertige Teil an der letzten Station grau und die Stange darüber halb durchsichtig in den
Farben; ohne Haken verschwindet das Teil, und die Stange ist deckend wie bisher. Vor dem Ende
wie immer: Teil hellblau, Stange halb durchsichtig.

### DONE
- `Bild`: je Körper sein Material gemerkt; `zeige_teil`, `_teil_schalten` (Farbe, Schalter,
  Durchsicht der Stange); `_rest_zeigen` setzt die Durchsicht nicht mehr selbst.
- Abspieler: `haken_teil`, Einstellung `AbfahrenTeilZeigen`, `bei_teil`; das Prüffenster
  verdrahtet ihn wie „Bahn“ und setzt ihn beim Bauen des Bildes.
- Hilfe (de/en): der Satz zur letzten Station.

### TEST
- `test_sprache`, `test_hilfe`, `test_abfahren` in 1.1.3 ok.
- `szenario_vierachs_schruppen` in 1.1.3 ok (Haken gesetzt, Teil grau (0.55, 0.55, 0.58),
  Stange 0.35 durchsichtig; Haken weg → Teil weg, Stange deckend); Bilder angesehen: mit Haken
  die Welle gedämpft grün über dem grauen Teil, ohne Haken leuchtend grün. 26.3 läuft; der
  volle Lauf nach dem Push.

### NEXT
- Version 0.33.2, Push; Hilfeseite „So geht’s“ (D-54).

## P-2026-10-01-01 entschieden

### EINGELESEN
- Manuel, 2026-10-01, auf E1–E7 (W-006), D-54, D-56 und das Soll-Teil am Ende, je mit
  Empfehlung: „Egal Hauptsache du arbeitest weiter??? Also ja“.

### DATEIEN
- `docs/spezifikation_strategien.md`, `docs/durchsicht_bedienbarkeit.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation W-006 trägt „Entschieden“ (E1–E7 je a), die Durchsicht D-54 (a) und D-56
(bleibt).

### DONE
- Eingetragen; Reihenfolge danach: Soll-Teil am Ende (a), Hilfeseite „So geht’s“, S2 rundum
  fertig (Linien längs, Plan indexiert, Entgraten), dann S3.

### TEST
- Nur Doku.

### NEXT
- Haken „Teil“ im Abspieler.

## P-2026-09-30-77 rest-blockweise

### EINGELESEN
- `docs/spezifikation_strategien.md`, Abschnitt 8 (Rest nach dem Schruppen: 12,3 s und 195 MB
  am großen Teil); Profil: `restmaterial.Stange.fahre_stuecke` zerlegt alle Fahrten auf einmal
  in 1,1 Millionen Teilschritte, `_block` rechnet dann je Stelle 50 × 13 Zellen.
- `camaddon/restmaterial.py`, `tests/test_goldene_bahnen.py`.

### DATEIEN
- `camaddon/restmaterial.py`, `docs/spezifikation_strategien.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Rest nach dem Schruppen braucht am großen Teil deutlich weniger Speicher als 195 MB, und
die goldenen Bahnen bleiben grün (dasselbe Ergebnis bis aufs Mikrometer).

### DONE
- `fahre_stuecke()` arbeitet blockweise (TEILSCHRITTE_JE_BLOCK = 50 000 Teilschritte je
  Block, `_teilschritte()`): Das Minimum je Zelle hängt nicht von der Reihenfolge ab.

### TEST
- `test_restmaterial`, `test_goldene_bahnen` (alle drei Bahnen unverändert), `test_vierachs_schlichten`,
  `test_vierachs_schlichten_op`, `test_vierachs_bahn` in 1.1.3 ok. Messung: großes Teil Rest
  195 → 42 MB und 12,3 → 10,6 s, zusammen 17,9 s; Welle unverändert 5,2 s.

### NEXT
- Zeit des Rests (Stücke statt Teilschritte – ändert den Rest um Bruchteile eines Mikrometers,
  nur mit neuen goldenen Bahnen), Schlichtbahn.

## P-2026-09-30-76 messung-zahlen

### EINGELESEN
- `scripts/bahn_messen.py` nach P-75 in 1.1.3: Welle 5,1 s, Welle mit Absatz 6,4 s, großes
  Teil 19,0 s (Rest nach dem Schruppen 12,3 s, 195 MB).

### DATEIEN
- `docs/spezifikation_strategien.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Abschnitt 8 nennt die Zeiten ohne Speichermessung, sagt, wo die Zeit hingeht, und setzt die
Ziele neu (Welle unter 5 s, großes Teil unter 15 s, Spitze unter 100 MB).

### DONE
- Tabelle und Schlüsse ersetzt; Reihenfolge: Speicher des Rests, Zeit des Rests, Schlichtbahn.

### TEST
- Nur Doku.

### NEXT
- Rest blockweise (P-77), goldene Bahnen müssen grün bleiben.

## P-2026-09-30-75 messung-ohne-bremse

### EINGELESEN
- `scripts/bahn_messen.py` (P-71) und ein Profil mit `cProfile` am großen Teil: Die
  Schruppbahn brauchte dort 2,6 s statt der gemessenen 17 s – `tracemalloc` bremst jede
  Zuweisung; die Tabelle in `docs/spezifikation_strategien.md` war damit zu hoch.
- Profil der Schlichtbahn (Welle mit Absatz): `_kanten_kugel`, `_nicht_tiefer`,
  `_dreiecke_treffen`, `_zusammengefasst` – zusammen 3 s.

### DATEIEN
- `scripts/bahn_messen.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Das Messprogramm misst die Zeit ohne `tracemalloc` (erster Lauf) und den Speicher mit
(zweiter Lauf).

### DONE
- Zwei Läufe je Schritt. Die Tabelle in der Spezifikation folgt mit den neuen Zahlen (P-76).

### TEST
- Messprogramm in 1.1.3 gelaufen; kein Testlauf nötig (Skript und Doku).

### NEXT
- Rest nach dem Schruppen am großen Teil (13 s in `restmaterial._block`): Stücke statt
  Teilschritte – nur mit neuen goldenen Bahnen und Satz im Verlauf; sonst reicht es.

## P-2026-09-30-73 goldene-bahnen

### EINGELESEN
- `docs/spezifikation_strategien.md`, Abschnitt 9 („Goldene Bahnen“); `scripts/bahn_messen.py`
  (dieselben Teile), `tests/test_vierachs_bahn.py`, `tests/test_vierachs_schlichten.py`.

### DATEIEN
- `tests/test_goldene_bahnen.py` (neu), `tests/golden/welle_schruppen.json`,
  `tests/golden/welle_absatz_schruppen.json`, `tests/golden/welle_absatz_schlichten.json` (neu),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`test_goldene_bahnen` vergleicht drei Bahnen (Welle schruppen, Welle mit Absatz schruppen und
schlichten) mit den Dateien in `tests/golden/`: Anzahl, Hash über alle Punkte (1 µm) und eine
Stichprobe, die den ersten abweichenden Punkt nennt. `GOLDENE_BAHNEN_SCHREIBEN=1` schreibt sie
neu – nur mit Absicht und einem Satz im Verlauf.

### DONE
- Geschrieben; die Dateien mit 0.33.0 erzeugt (1.1.3) – jede Beschleunigung muss sie grün
  lassen.

### TEST
- `test_goldene_bahnen` in 1.1.3: erster Lauf schreibt, zweiter Lauf vergleicht – ok.

### NEXT
- Messen (P-71), dann die teuersten Stellen.


## P-2026-09-30-72 version-0-33-1

### EINGELESEN
- P-2026-09-30-69 bis -71; `CLAUDE.md`: Soll Manuel etwas ausprobieren, braucht der Push eine
  höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.33.1 an.

### DONE
- Version 0.33.1; Stand nachgetragen (Durchsicht 3 kleine Punkte, VDI-Halter ohne Größe,
  Messung der Bahnrechnung mit Zahlen in der Spezifikation W-006).

### TEST
- Alle Prüfungen zu P-69 bis -71 und -73 in 1.1.3 ok (siehe dort). Voller Lauf nach dem Push:
  1.1.3 ganz grün; 26.3 grün bis auf einen Absturz von FreeCAD selbst (Segmentation fault in
  `FreeCADGui.Control.closeDialog()`, `szenario_vierachs_aendern`, beim Schließen mit
  Abbrechen) – zweimal wiederholt, beide Male ok; in keinem früheren Lauf gesehen. Ein
  Fehler des Wochen-Builds, nicht des Addons; bleibt im Blick.

### NEXT
- Push, bei GitHub nachsehen; voller Lauf danach (Kernmodule `maschine`, `werkzeuge`).


## P-2026-09-30-71 bahn-messen

### EINGELESEN
- `docs/spezifikation_strategien.md`, Abschnitt 8 (erst messen); Manuel: „schneller und
  speicher sparender … wenn das irgendwie möglich ist“.
- `camaddon/vierachs_huelle.py`, `camaddon/vierachs_bahn.py`, `camaddon/vierachs_schlichten.py`
  (`rest_nach`), `tests/test_vierachs_bahn.py`, `tests/test_vierachs_schlichten.py`.

### DATEIEN
- `scripts/bahn_messen.py` (neu), `docs/spezifikation_strategien.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`FreeCADCmd scripts/bahn_messen.py` druckt je Teil eine Tabelle: Schritt, Zeit, Spitzenspeicher,
dazu Dreiecke, Punkte und Sätze; mit `BAHN_MESSEN_AUSGABE` auch in eine Datei.

### DONE
- Geschrieben: drei Teile (Welle, Welle mit Absatz und Abflachung, Ø 200 × 300), sechs Schritte
  je Teil; die Zahlen stehen in der Spezifikation.

### TEST
- In 1.1.3 gelaufen (FreeCADCmd schreibt nur ASCII auf die Konsole – die Datei zuerst, dann
  die Konsole mit Ersatzzeichen); die Zahlen stehen in `docs/spezifikation_strategien.md`.

### NEXT
- Goldene Bahnen (`test_goldene_bahnen`), dann die teuersten Stellen.


## P-2026-09-30-70 vdi-halter-ohne-groesse

### EINGELESEN
- Manuel, 2026-09-30: „man wird auf eine VDI 40 maschine keine VDI 30 halter verbauen könnnen
  das meine ich ... also wirds schon ein halter sein der für die maschine ist .. also reicht VDI
  halter aus .. verstehst du wie ichs meine ?“
- `camaddon/halter.py` (Vorlagen „vdi30_…“), `camaddon/beispielmaschine.py`
  (`DrehmaschinenMasse.vdi` nur beim Bau), `camaddon/gui_halter.py` (Menü „Neu“),
  `camaddon/gui_details.py` (Kennwerte je Betriebsart).

### DATEIEN
- `camaddon/halter.py`, `camaddon/werkzeuge.py`, `camaddon/maschine.py`,
  `camaddon/beispielmaschine.py`, `camaddon/gui_details.py`, `camaddon/gui_halter.py`,
  `translations/de.json`, `translations/en.json`, `help/de|en/halter.html`,
  `docs/spezifikation_halter.md`, `tests/test_halter.py`, `tests/test_beispielmaschine.py`,
  `tests/gui/szenario_halter_richtung.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Halter …“ → „Neu ▾“: „VDI angetrieben radial · ER16“ (ohne Zahl). Ist
die Beispiel-Drehmaschine offen (VDI 30): „VDI30 angetrieben radial · ER16“; eine Maschine mit
VDI 40 aus „Neue Maschine“: „VDI40 …“ mit Ø × 4/3. „Maschine bearbeiten“ → Revolver T zeigt
„VDI-Größe (mm)“.

### DONE
- Vorlagen ohne Größe (`VDI_VORLAGEN`, alte Schlüssel gelten als VDI 30), `aus_vorlage(…, vdi)`
  skaliert Ø, Versatz und Kopf; Kennwert „Vdi“ am Revolver, „Neue Maschine“ trägt ihn ein,
  `maschine.vdi_groesse`; „Halter“ nimmt die Größe der offenen Maschinen; Hilfe und
  Spezifikation (Stufe H).

### TEST
- `test_halter` (Größe 40, ohne Größe, alte Schlüssel), `test_beispielmaschine` (Vdi 30 am
  Revolver), `test_maschine`, `test_kollision`, `test_reichweite`, `test_vierachs_pruefen`,
  `test_sprache` in 1.1.3 ok; `szenario_halter_richtung` (Menü „VDI angetrieben radial · ER16“),
  `szenario_neue_maschine`, `szenario_bestueckung` in 1.1.3 ok.

### NEXT
- Manuels Blick auf das Menü „Neu“; F2.


## P-2026-09-30-69 durchsicht-3-klein

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, Abschnitt 8 (D-50 bis D-57); die Bilder der Szenarien;
  `camaddon/gui_sprachwahl.py` (Einstellungsseite), `camaddon/gui_werkstoffe.py`,
  `translations/de.json`, die Hilfeseiten.

### DATEIEN
- `camaddon/gui_sprachwahl.py`, `camaddon/gui_werkstoffe.py`, `camaddon/gui_maschine.py`
  (Kommentar), `translations/de.json`, `translations/en.json`, `help/de|en/achsen.html`,
  `help/de|en/glieder.html`, `help/de|en/neue_maschine.html`, `help/de|en/transformationen.html`,
  `help/de|en/verfahren.html`, `help/de|en/vierachs.html`, `tests/gui/szenario_erster_start.py`,
  `tests/gui/szenario_schnittwerte_job.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Einstellungsseite: Der Satz unter „Zahlen“ endet über „Updates“. „Schnittwerte in den Job“:
„keine Bahn – der Operation fehlt noch die Fläche oder Kante“. Schritt 2 des Assistenten: zwei
Sätze zu Ø, der Rest in der Hilfe. „Neue Maschine“ sagt, wo man C4/S4 einträgt. „Maschine
bearbeiten“: „Schräge Achsen“, „Was zusammen fährt“. Werkstoff: Tooltips zu kc1.1 und mc.

### DONE
- D-50: `_mit_satz()` – Formular und Satz senkrecht in der Gruppe; das Szenario prüft Höhe und
  Lage des Satzes. D-51, D-52 (Hilfe: der Ø-Absatz ersetzt „X ist der Radius“, das seit
  P-54 nicht mehr stimmte), D-53 (Satz in „Neue Maschine“, Hilfe „Neue Maschine“ und
  „Achsen“), D-55, D-56 (Beispiel im Tooltip), D-57.

### TEST
- `test_sprache`, `test_hilfe` in 1.1.3 ok; `szenario_erster_start` (Bild angesehen: der Satz
  steht in seiner Gruppe), `szenario_schnittwerte_job`, `szenario_maschine_bearbeiten`,
  `szenario_schraege_achse`, `szenario_werkstoffe`, `szenario_vierachs_schruppen` (Erwartung an
  den Ø-Satz angepasst) in 1.1.3 ok.

### NEXT
- D-54 und D-56 mit Manuel; VDI-Halter ohne Größe (P-70).

## P-2026-09-30-68 version-0-33-0

### EINGELESEN
- P-2026-09-30-65 bis -67; `CLAUDE.md`: Soll Manuel etwas ausprobieren, braucht der Push eine höhere
  Version – ein neues Fenster: die mittlere Stelle.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.33.0 an.

### DONE
- Version 0.33.0; Stand nachgetragen (Stufe G gebaut, Plan W-006 und Durchsicht 3 zur
  Besprechung, als Nächstes D-50 ff., VDI-Halter ohne Größe, F2).

### TEST
- Die Tests zu P-65 in 1.1.3; der volle Lauf (Kernmodule `maschine`, `reichweite`,
  `werkzeuge` berührt) läuft nach dem Push, was er findet, wird sofort behoben.

### NEXT
- Push, bei GitHub nachsehen, voller Lauf; Manuels Rückmeldung zum Fenster.

## P-2026-09-30-67 durchsicht-3

### EINGELESEN
- Manuel, 2026-09-30: „nochmals alles durchgehst vor allem die sache mit der bedienbarkeit
  und leichtigkeit der bedienung .. also einfach solls sein gut erklärt muss es sein ..
  logisch“.
- Alle Fenster als Bilder aus den Szenarien (0.32.1/0.33.0), `translations/de.json`, die
  Hilfeseiten; `docs/durchsicht_bedienbarkeit.md` (Durchsicht 1 und 2).

### DATEIEN
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Abschnitt 8 „Durchsicht 3“ mit D-50 bis D-58: je ein Befund mit Bild oder Text, Lösung und
Aufwand; D-54 und D-56 zur Entscheidung; Reihenfolge.

### DONE
- Geschrieben: der Satz auf der Einstellungsseite überlappt (D-50), „Basisgeometrie“
  (D-51), der Ø-Absatz in Schritt 2 (D-52), Achsnamen wie an der Steuerung (D-53), eine
  Seite „So geht’s“ (D-54), Abschnittsnamen in „Maschine bearbeiten“ (D-55), „Betriebsart“
  (D-56), kc1.1/mc (D-57), für gut befunden (D-58).

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- D-50, D-51, D-52, D-53, D-55, D-57 bauen; D-54 und D-56 mit Manuel.

## P-2026-09-30-66 plan-strategien

### EINGELESEN
- Manuel, 2026-09-30: „ich hätte gerne das du einen plan schreibst für alle fräs strategien dies
  so gibt ... das wir am ende mit unserem addon bessere frässtrategien auf ein bauteil anwenden
  können als in freecad vom cam modul vorhanden sind ... auserdem optimierung des codes und
  schauen das es schneller und speicher sparender generiert wird der werkzeugweg ... aber
  hauptziel ist qualität der werkzeugwege und bedienbarkeit“.
- FreeCADs `Path/Op` in 1.1.3 und 26.3 (Adaptive, Pocket, Profile, MillFace, Surface,
  Waterline, Slot, Deburr, Helix, Drilling; neu in 26.3: PlanarSurface, RotarySurface,
  MillFacing, Flute – die 3D-Operationen brauchen OpenCamLib), `docs/spezifikation_vierachs.md`
  (V4c, V4d, V6, V7), unsere Module `vierachs_huelle`, `vierachs_bahn`, `restmaterial`,
  `kollision`.

### DATEIEN
- `docs/spezifikation_strategien.md` (neu), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation W-006 sagt je Strategie (2,5D, 3D, rundum, 5 Achsen), was FreeCAD kann, wo
es hakt und was wir besser machen; Grundsätze für die Qualität der Bahn; Bedienung mit einem
Assistenten; Rechenkern ohne OCL; Messen vor Beschleunigen; Stufen S1–S7; Entscheidungen
E1–E7 mit Empfehlung.

### DONE
- Geschrieben, zur Besprechung mit Manuel.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels Entscheidungen; S1 (Messen, goldene Bahnen, Bahn-Datenmodell mit Bögen).

## P-2026-09-30-65 bestueckung-je-job

### EINGELESEN
- Manuel, 2026-09-30, mit Bild von „Maschine bearbeiten“ (Abschnitt „Bestückung“, 0.32.1):
  „das ist irreführend .... ich denke die bestückung sollte je nach job funktionieren ...
  auserdem wird die bestückung nicht dargestellt auf der maschine ...“; auf die Wahl (a)/(b)/(c):
  „ja jeder job hat seine eigene bestückung und man hat einfach die maschine die man ablegt und
  immer wieder laden kann“.
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe F, P-56), `camaddon/maschine.py`,
  `camaddon/reichweite.py`, `camaddon/gui_vierachs.py`, `camaddon/gui_maschine.py`,
  `camaddon/gui_abfahren.py`, `camaddon/gui_reichweite.py` (`maschine_fuer`, D-20),
  `camaddon/job_schnittwerte.py`.

### DATEIEN
- Neu: `camaddon/bestueckung.py`, `camaddon/gui_bestueckung.py`,
  `resources/icons/bestueckung.svg`, `tests/test_bestueckung.py`
- `camaddon/maschine.py`, `camaddon/reichweite.py`, `camaddon/gui_vierachs.py`,
  `camaddon/gui_maschine.py`, `camaddon/gui_abfahren.py`, `camaddon/gui_start.py`,
  `camaddon/job_schnittwerte.py`, `translations/de.json`, `translations/en.json`,
  `help/de|en/bestueckung.html`, `help/de|en/reichweite.html`, `help/de|en/vierachs.html`,
  `README.md`, `docs/spezifikation_werkzeugverwaltung.md`, `tests/test_maschine.py`,
  `tests/test_reichweite.py`, `tests/gui/szenario_bestueckung.py`,
  `tests/gui/szenario_erster_start.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job im Baum wählen → „Bestückung“ (neuer Knopf vor „Auf der Maschine prüfen“): Das Fenster
öffnet die Maschine des Jobs; in der 3D-Ansicht stecken die Werkzeuge des Jobs im Revolver,
an jedem Platz sein Name; je Platz eine Auswahl. T1 auf P5 gewählt: Sein Controller heißt
„T5 …“ (Nummer 5). „Maschine bearbeiten“ hat keinen Abschnitt „Bestückung“ mehr. Beim
Abfahren stecken alle Werkzeuge des Jobs im Revolver.

### DONE
- Die Bestückung steht im Job: Der Platz ist die Nummer der Controller (`bestueckung.py`:
  Einträge je Werkzeug, `platz_fuer`, `lege_um` mit Tausch und Umbenennen, `doppelt`).
- Maschine ohne Bestückung: `bestueckung/bestuecke/platz_von` weg, alte Eigenschaft
  „Werkzeug“ bleibt verborgen; in „Maschine bearbeiten“ ein grauer Satz statt des Abschnitts.
- 4-Achs-Assistent: Platz aus dem Job („P3 · “, `_vorgemerkt` für den Schlichtfräser);
  „alle belegt“ statt „nicht bestückt“.
- Prüffenster: „Auf P7 stecken im Job mehrere Werkzeuge: …“ statt der vier F4-Sätze.
- Abfahren: je Aufnahme ein Knoten mit den Werkzeugen des Jobs, folgt dem Revolver;
  „Hinsehen“ auf Werkstück und laufendes Werkzeug; Bausteine als Modulfunktionen.
- Fenster „Bestückung“ mit Revolverbild (Werkzeuge, Platznamen), Auswahl je Platz, roten
  Sätzen, „Hinsehen“; Befehl in Leiste und Menü; Hilfe (de/en), README, Spezifikation.

### TEST
- `test_bestueckung` (neu): Plätze, Vormerken, Tausch, Umbenennen, doppelt, ohne Revolver;
  `test_maschine`, `test_reichweite` (zwei Werkzeuge auf P2), `test_sprache`, `test_hilfe`
  in 1.1.3 ok.
- `szenario_bestueckung` (neu) in 1.1.3 ok, Bilder angesehen: Revolver mit T1, T2, T7 und
  „P1“ … „P12“; Liste „– auf P2“; roter Satz; „Maschine bearbeiten“ mit dem grauen Satz.
- In 1.1.3 dazu `szenario_vierachs_schruppen`, `szenario_rundum_drehmaschine` (Bild: T1 steckt
  auf P1, während T2 am Teil ist), `szenario_abfahren`, `szenario_erster_start` (acht Knöpfe),
  `szenario_maschine_bearbeiten`, `szenario_vierachs_aendern`, `szenario_kollision`,
  `szenario_reichweite`, `szenario_vierachs_schlichten` ok. In 26.3 `test_bestueckung`,
  `test_reichweite`, `test_maschine`, `szenario_bestueckung`, `szenario_rundum_drehmaschine`,
  `szenario_erster_start` ok. Der volle Lauf folgt nach dem Push (Kernmodule).

### NEXT
- Version 0.33.0, Push; VDI-Halter ohne Größe (Manuel: „also reicht VDI halter aus“); F2.

## P-2026-09-30-64 achsnamen-mit-nummer

### EINGELESEN
- Manuel, 2026-09-30, auf die Frage, wie die C-Achse der Hauptspindel im Programm heißt: „naja
  ich weis nicht wie das bei siemens ist beispielsweise ob man im satz einfach so c4 verfahren
  kann aber es muss die zahl schon mit bei sonst weis die maschine ja nicht welches c verfahren
  wird ...“
- `docs/spezifikation_steuerung.md` (Abschnitt 11), `camaddon/maschine.py` (`programmname`).

### DATEIEN
- `docs/spezifikation_steuerung.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation W-005 sagt: Der Postprozessor schreibt den ganzen NC-Namen (C4), bei Siemens
mit „=“; für CAM bleibt der Buchstabe.

### DONE
- Abschnitt 11 um „Achsnamen mit Nummer“ ergänzt.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Bestückung je Job (Manuel: „ja jeder job hat seine eigene bestückung“).

## P-2026-09-30-63 version-0-32-2

### EINGELESEN
- P-2026-09-30-60 bis -62; `CLAUDE.md`: Soll Manuel etwas ausprobieren, braucht der Push eine
  höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.32.2 an.

### DONE
- Version 0.32.2; Stand nachgetragen, als Nächstes die Bestückung je Job (Manuel,
  2026-09-30).

### TEST
- Die Tests zu P-60 bis -62 in 1.1.3 ok; ein voller Lauf ist nicht nötig (kein Kernmodul
  geändert, `docs/arbeitsregeln.md`, Abschnitt 5).

### NEXT
- Push, bei GitHub nachsehen; Bestückung je Job planen und Manuel fragen.

## P-2026-09-30-62 operations-ordner

### EINGELESEN
- Manuel, 2026-09-30, mit Bild (Job mit „Rundum schruppen T2“, Ordner „Operations“ gewählt,
  „4-Achs-Bearbeitung“ geklickt): „hier jetzt noch einen schlicht gang hinzufügen ... ???“
  – der Knopf kannte den Ordner nicht und fing einen neuen Job an.
- `camaddon/gui_vierachs.py` (`gewaehlte_operation`, `_zum_aendern`: „Rundum schlichten“
  lässt sich beim Ändern des Schruppens dazunehmen).

### DATEIEN
- `camaddon/gui_vierachs.py`, `tests/gui/szenario_vierachs_aendern.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job oder sein Ordner „Operations“ gewählt, „4-Achs-Bearbeitung“: Das Fenster öffnet „Rundum
schruppen“ dieses Jobs in Schritt 2, wo sich „Rundum schlichten“ dazunehmen lässt.

### DONE
- `gewaehlte_operation`: auch der Ordner „Operations“ zählt als sein Job; vom Job öffnet
  sich zuerst „Rundum schruppen“, sonst die erste Rundum-Operation.

### TEST
- `szenario_vierachs_aendern`: über den Knopf mit dem Ordner „Operations“ gewählt.
- In 1.1.3 ok.

### NEXT
- Version 0.32.2, Push; dann Bestückung je Job (Manuel, 2026-09-30).

## P-2026-09-30-61 planaufmass-null

### EINGELESEN
- Manuel, 2026-09-30, mit Bild von Schritt 1 des 4-Achs-Assistenten: „in planaufmass steht
  nix drinnen ?“ – grau steht dort der zuletzt benutzte Wert, bei ihm 0; `groesse_zeigen`
  zeigt 0 als leer.
- `camaddon/gui_vierachs.py` (`_baue_rohteil`, `GEMERKT`).

### DATEIEN
- `camaddon/gui_vierachs.py`, `tests/gui/szenario_vierachs_rohteil.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
War das zuletzt benutzte Planaufmaß 0, steht im leeren Feld grau „0“.

### DONE
- Die grauen Vorschläge von Planaufmaß, Abstechbreite und Spannlänge zeigen eine 0 als „0“.

### TEST
- `szenario_vierachs_rohteil`: gemerktes Planaufmaß 0 → grau „0“.
- In 1.1.3 ok, Bild `1_fenster` angesehen: Planaufmaß grau „0“.

### NEXT
- P-62.

## P-2026-09-30-60 hoechstdrehzahl

### EINGELESEN
- Manuel, 2026-09-30, mit Bild von „Neue Maschine“ (Höchstdrehzahl 3200): „höchstdrehzahl von
  was ? ... die angetriebenen werkzeuge im revolver können andere drehzahlen als die
  hauptspindel von der maschie.“
- `camaddon/gui_neue_maschine.py`, `camaddon/beispielmaschine.py` (S3 fest 4000 U/min),
  `camaddon/schruppwerte.py` (übernimmt die Drehzahl der Spindeln, die Werkzeuge antreiben).

### DATEIEN
- `camaddon/gui_neue_maschine.py`, `camaddon/beispielmaschine.py`, `translations/de.json`,
  `translations/en.json`, `help/de|en/neue_maschine.html`, `tests/test_beispielmaschine.py`,
  `tests/gui/szenario_neue_maschine.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Neue Maschine“ → Drehmaschine: Zeile „Höchstdrehzahl: Hauptspindel [5000 U/min] angetriebene
Werkzeuge [4000 U/min]“; gebaut hat S1 die erste, S3 die zweite. An der Fräse nur „Spindel“.

### DONE
- `DrehmaschinenMasse.drehzahl_werkzeuge` (Vorgabe 4000), 0 ist ein Fehler; S3 bekommt sie.
- „Neue Maschine“: beide Drehzahlen in einer Zeile, je mit Tooltip; an der Fräse nur die
  Spindel. Hilfe (de/en).

### TEST
- `test_beispielmaschine`: S3 3200 aus den Maßen; 0 als Fehler.
- `szenario_neue_maschine`: Vorgabe 4000, Fräse ohne das zweite Feld, gebaut S3 3200.
- Alles in 1.1.3 ok, dazu `test_sprache`, `test_hilfe`; Bild `2_drehmaschine_vorgabe`
  angesehen: „Höchstdrehzahl: Hauptspindel 5000 U/min · angetriebene Werkzeuge 4000 U/min“.

### NEXT
- Planaufmaß (P-61), Ordner „Operations“ (P-62), Version 0.32.2.

## P-2026-09-30-59 version-0-32-1

### EINGELESEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas ausprobieren,
  braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.32.1 an.

### DONE
- Version 0.32.1 mit P-2026-09-30-58 (Platz vorn in der Fräserliste).

### TEST
- Die Prüfungen zu P-58 (siehe dort); der volle Lauf in beiden Versionen läuft nach dem Push.

### NEXT
- Push; voller Lauf; F2 (Nummer am Werkzeug freiwillig).

## P-2026-09-30-58 platz-vorn

### EINGELESEN
- Das eigene Bild aus `szenario_vierachs_schruppen` zu P-56: In der schmalen Fräserliste des
  4-Achs-Assistenten stand „T1 Schaftfräser Ø 12 · z 3 · VHM – a“ – der Platz („– auf P1“)
  war abgeschnitten.

### DATEIEN
- `camaddon/gui_vierachs.py`, `translations/de.json`, `translations/en.json`,
  `help/de|en/vierachs.html`, `help/de|en/bestueckung.html`,
  `docs/spezifikation_werkzeugverwaltung.md`, `tests/gui/szenario_vierachs_schruppen.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
4-Achs-Assistent an der Beispiel-Drehmaschine, Schritt 2: In „Fräser“ steht „P1 · T1
Schaftfräser Ø 12 …“ – der Platz vorn, ganz zu sehen.

### DONE
- Der Platz steht vor dem Fräser („P1 · “) statt dahinter; „nicht bestückt“ fällt in der
  Liste weg – das sagt schon der gelbe Satz darunter. Hilfe und Spezifikation angepasst.

### TEST
- `test_sprache`, `test_hilfe` in 1.1.3 ok; `szenario_vierachs_schruppen` in 1.1.3 ok, Bild
  angesehen: „P1 · T1 Schaftfräser Ø 12 · z 3 · VHM“.

### NEXT
- Version 0.32.1, Push, voller Lauf.

## P-2026-09-30-57 version-0-32-0

### EINGELESEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas ausprobieren,
  braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.32.0 an.

### DONE
- Version 0.32.0 mit P-2026-09-30-56 (Bestückung an der Maschine).

### TEST
- Die Prüfungen zu P-56 (siehe dort); der volle Lauf in beiden Versionen läuft nach dem Push.

### NEXT
- Push; voller Lauf; F2 (Nummer am Werkzeug freiwillig).

## P-2026-09-30-56 bestueckung

### EINGELESEN
- Manuel, 2026-09-30: „wie kann ich das werkzeug wieder entladen aber ich wills nicht löschen
  ich will nur nicht das es einen platz belegt ... daher gabs ja auch die unterscheidung
  zwischen p und t ... und wir haben ausgemacht das man irgendwo in der mschine die werkzeuge
  zuweisen müsste“; auf A/B: „berücksichtigung an der Maschine“; auf F-E1 bis F-E3 mit den
  Empfehlungen (a): „passt“.
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe F), `camaddon/maschine.py` (Aufnahme,
  Plätze), `camaddon/gui_maschine.py`, `camaddon/reichweite.py` (`werkzeugaufnahme`,
  `_pruefe_operation`), `camaddon/job_schnittwerte.py` (Controller), `camaddon/gui_vierachs.py`
  (Fräserlisten, gelber Satz, Anlegen/Ändern), `camaddon/gui_werkzeuge.py` (`oeffne`,
  Signal `gespeichert`).

### DATEIEN
- `camaddon/maschine.py`, `camaddon/gui_maschine.py`, `camaddon/reichweite.py`,
  `camaddon/job_schnittwerte.py`, `camaddon/gui_vierachs.py`, `camaddon/hilfe.py`,
  `translations/de.json`, `translations/en.json`, `help/de|en/bestueckung.html` (neu),
  `help/de|en/vierachs.html`, `help/de|en/reichweite.html`,
  `docs/spezifikation_werkzeugverwaltung.md`, `tests/test_maschine.py`,
  `tests/test_reichweite.py`, `tests/test_job_schnittwerte.py`,
  `tests/gui/szenario_bestueckung.py` (neu), `tests/gui/szenario_vierachs_schruppen.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Maschine bearbeiten“ an einer Drehmaschine hat den Abschnitt „Bestückung“: je Platz eine
Auswahl; ohne Bestückung steht T3 auf P3. T1 auf P5 gesteckt: P1 wird frei, hinter T1 steht in
den anderen Listen „– auf P5“; „– frei –“ entlädt einen Platz. Nach OK bleibt das so. Im
4-Achs-Assistenten steht hinter dem Fräser „– auf P5“, sein Controller heißt T5. Ruft ein Job
einen Platz auf, auf dem laut Bestückung ein anderes Werkzeug steckt, sagt „Auf der Maschine
prüfen“ es.

### DONE
- Modell (`maschine.py`): Ausdrücklich bestückte Plätze tragen die Kennung ihres Werkzeugs
  (Eigenschaft `Werkzeug`, verborgen; leer: frei). Jeder andere Platz zählt nach der Nummer –
  T3 auf P3 –, außer das Werkzeug steckt schon woanders (`bestueckung()`, `platz_von()`,
  `bestuecke()`, `revolverplaetze()`). So ändert sich nichts ungefragt (F-E3), auch nicht an
  älteren Maschinen, und eine Maschine, gebaut mit leerer Werkzeugverwaltung, nimmt später
  angelegte Werkzeuge nach ihrer Nummer auf. Erst geplant war, beim Bau vorzubelegen – dann
  hätte eine leer gebaute Maschine alle Plätze fest „frei“ gehabt.
- F1 „Maschine bearbeiten“: Abschnitt „Bestückung“ zwischen Aufnahmen und Gliedern, je Platz
  eine Auswahl, „– auf P5“ hinter einem Werkzeug, das woanders steckt; „Werkzeugverwaltung …“
  öffnet sie, nach dem Speichern dort liest der Abschnitt sie neu. Ohne Revolver (Fräse) fehlt
  der Abschnitt. Hilfeseite „Bestückung“.
- F3 4-Achs-Assistent: In den Fräserlisten „– auf P3“ / „– nicht bestückt“; der Controller
  bekommt beim Anlegen und Ändern die Nummer des Platzes (`controller_ohne_transaktion`,
  `controller_fuer`, `controller_name` mit `nummer`); der gelbe Satz sagt „steckt auf keinem
  Platz“ und nimmt für „nicht radial“ den bestückten Platz.
- F4 Prüffenster: `Pruefung._bestueckung_pruefen` – vier Sätze (Platz frei/anderes Werkzeug,
  das richtige woanders/nirgends), mit dem, was zu tun ist.
- Spezifikation: Entscheidung „passt“, das gebaute Modell, warum der Assistent nicht selbst
  umsteckt (die Maschine liegt meist in einem anderen Dokument).

### TEST
- `test_maschine`: nach Nummern, Umstecken (der alte Platz frei), Entladen, ein Werkzeug ohne
  Nummer, ein gelöschtes Werkzeug; nur umgesteckte Plätze bestückt; gespeichert und geladen,
  Kennung verborgen. Ok in 1.1.3.
- `test_reichweite`: ohne Bestückung kein Satz; T2 auf P5 → „P2 ist laut Bestückung frei …
  T5“; ein anderes Werkzeug auf P2; T2 nirgends. `platznummer()`. Ok in 1.1.3.
- `test_job_schnittwerte`: Controller „T5 Vollnut“ mit ToolNumber 5; beim Ändern T8. Ok in
  1.1.3.
- Außerdem ok in 1.1.3: `test_sprache`, `test_hilfe`, `test_beispielmaschine`.
- Szenarien in 1.1.3 ok, Bilder angesehen: `szenario_bestueckung` (neu: nach Nummern, T1 auf
  P5, P2 frei, nach OK gespeichert, beim nächsten Öffnen gleich, neues T3 aus der
  Werkzeugverwaltung gleich auf P3, Liste mit „– auf P5“; an der Fräse kein Abschnitt),
  `szenario_vierachs_schruppen` („– auf P1“ in der Fräserliste, kein Satz zur Bestückung im
  Prüffenster), `szenario_rundum_drehmaschine`, `szenario_maschine_bearbeiten`,
  `szenario_neue_maschine`, `szenario_verfahren_schraeg`, `szenario_beispielmaschine`.

### NEXT
- Voller Lauf in beiden Versionen; F2: Nummer am Werkzeug freiwillig („entladen“ in der
  Werkzeugverwaltung, keine Warnung „Nummer doppelt“ unter Werkzeugen ohne Nummer).

## P-2026-09-30-55 version-0-31-6

### EINGELESEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas ausprobieren,
  braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.31.6 an.

### DONE
- Version 0.31.6 mit P-2026-09-30-54 (X im Durchmesser oder Radius).

### TEST
- Die Prüfungen zu P-54 (siehe dort); der volle Lauf läuft nach dem Push.

### NEXT
- Push; voller Lauf; Bestückung an der Maschine (Stufe F).

## P-2026-09-30-54 x-durchmesser

### EINGELESEN
- Manuel, 2026-09-30, auf „X als Durchmesser eintragen und anzeigen, wie deine Steuerung?
  Dann baue ich einen Umschalter Ø/Radius“: „Ja mit Umschalter wichtig ist ja nur was dann
  beim Postprozess raus kommt“. Davor: „X −60 … 550“ an seiner Maschine.
- `camaddon/maschine.py` (Betriebsart, `WERTE`), `camaddon/reichweite.py` (Texte),
  `camaddon/gui_details.py` und `camaddon/gui_maschine.py` (Verfahrweg),
  `camaddon/gui_verfahren.py`, `camaddon/gui_neue_maschine.py`,
  `camaddon/beispielmaschine.py`, `camaddon/gui_abfahren.py`, `camaddon/kollision.py`,
  `camaddon/gui_vierachs.py` (Satz „Im Programm ist X der Radius“);
  `docs/spezifikation_steuerung.md` (E4). FreeCADs Maschinendefinition (26.3) kennt keinen
  Durchmesser – die Übergabe an CAM bleibt, wie sie ist.

### DATEIEN
- `camaddon/maschine.py`, `camaddon/einheiten.py`, `camaddon/reichweite.py`,
  `camaddon/gui_abfahren.py`, `camaddon/kollision.py`, `camaddon/gui_details.py`,
  `camaddon/gui_maschine.py`, `camaddon/gui_verfahren.py`, `camaddon/gui_neue_maschine.py`,
  `camaddon/beispielmaschine.py`, `camaddon/gui_vierachs.py`, `translations/de.json`,
  `translations/en.json`, `help/de|en/neue_maschine.html`, `help/de|en/achsen.html`,
  `help/de|en/verfahren.html`, `help/de|en/reichweite.html`,
  `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/spezifikation_steuerung.md`,
  `tests/test_maschine.py`, `tests/test_reichweite.py`, `tests/test_beispielmaschine.py`,
  `tests/gui/szenario_neue_maschine.py`, `tests/gui/szenario_maschine_bearbeiten.py`,
  `tests/gui/szenario_verfahren_schraeg.py`, `tests/gui/szenario_vierachs_schruppen.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Neue Maschine“ → Drehmaschine: Zeile „X als: Durchmesser (Ø)“ vorgewählt, „Weg X (Ø):
−50 … 850 mm“; auf „Radius“ stehen −25 … 425 da. In „Maschine bearbeiten“ bei X1 der Haken
„zählt im Durchmesser (Ø)“, darunter „Verfahrweg von, Ø (mm)“. „Maschine verfahren“ zeigt
X1 als „Ø 550,00 mm“, das Prüffenster „X1 braucht Ø …“ und „Spitze im Programm: X Ø …“.

### DONE
- Betriebsart „Linear“ hat den Kennwert „zählt im Durchmesser (Ø)“ (`Durchmesser`). Ältere
  Maschinen bekommen ihn beim Laden, ausgeschaltet; beim Laden fehlt er kurz, darum blendet
  `_nur_passende_werte_zeigen` nur vorhandene Kennwerte aus.
- `maschine.ist_durchmesser(maschine, gelenk)` und `maschine.x_im_durchmesser(maschine)`
  (eine Linearachse, die im Programm X heißt, zählt im Durchmesser).
- Gerechnet und gespeichert wird immer im Radius. Nur Anzeige und Eingabe verdoppeln, mit
  „Ø “ davor (`einheiten.DURCHMESSER`):
  - Prüffenster: Überschreitung, Bereich, „nicht überall hin“, Achswerte und Spitze im
    Abspieler, Kollisionsbefunde (`reichweite.stellung_text`/`punkt_text` mit Schalter;
    `Pruefung.durchmesser`, `Pruefung.x_durchmesser`).
  - „Maschine verfahren“: Feld mit „Ø “ davor, Grenzen, rote Zeile am Anschlag, grauer Satz
    zur schrägen Achse; „wie im Programm“ zählt X wie der Schlitten, der es trägt.
  - „Maschine bearbeiten“: Haken bei X1; Verfahrweg „von, Ø“/„bis, Ø“ und der graue Satz im
    Durchmesser. Der Haken baut die Felder neu auf.
  - „Neue Maschine“: „X als: Durchmesser (Ø) / Radius“ für die Drehmaschine, vorgewählt
    Durchmesser; die X-Wege zählen genauso und rechnen beim Umschalten um.
- Die Beispiel-Drehmaschine zählt X im Durchmesser (`DrehmaschinenMasse.x_durchmesser`).
- 4-Achs-Assistent: Zählt X der gewählten Maschine im Durchmesser, sagt der graue Satz, dass
  FreeCADs eigene Postprozessoren trotzdem den Radius schreiben (DIAMOF), bis der
  Postprozessor des Addons X im Durchmesser schreibt.
- Hilfe (de/en) und Spezifikation; E4 in der Steuerungs-Spezifikation mit Manuels Satz.

### TEST
- `test_maschine`: Kennwert aus/an, `ist_durchmesser`, `x_im_durchmesser`, verborgen an der
  Spindel; eine Betriebsart ohne den Kennwert gespeichert und geladen bekommt ihn, X1 behält
  seinen Haken. Ok in 1.1.3 und 26.3.
- `test_reichweite`: „X Ø 900, Y 0, Z −5.5“, „Ø 550.00 mm“, Bereich im Durchmesser. Ok in
  1.1.3 und 26.3.
- `test_beispielmaschine`: Beispiel im Durchmesser (`Pruefung.durchmesser` = X), „X als:
  Radius“ ohne Haken. Ok in 1.1.3 und 26.3.
- Außerdem in 1.1.3 ok: `test_sprache`, `test_hilfe`, `test_schraege_achse`, `test_verfahren`,
  `test_kollision`, `test_abfahren`, `test_kinematik`, `test_vierachs_achsen`,
  `test_vierachs_pruefen`; `test_export` übersprungen wie immer, in 26.3 ok.
- Szenarien in 1.1.3 ok, Bilder angesehen: `szenario_neue_maschine` (Umschalter hin und
  zurück, Ø −80 … 120 ergibt Radius −40 … 60), `szenario_maschine_bearbeiten` (Haken, Ø −100
  gibt am Gelenk −50, grauer Satz in Ø, Haken wieder weg), `szenario_verfahren_schraeg`
  (X1 Ø 538,45; X Ø 830; Grenze Ø 850), `szenario_vierachs_schruppen` („X1 Ø …“, „Spitze im
  Programm: X Ø …“, grauer Satz zu FreeCADs Postprozessoren).

### NEXT
- Voller Lauf `scripts/alle_tests.sh` (Kern: maschine, reichweite, kollision).
- Der Postprozessor (W-005 S1) schreibt X nach `x_im_durchmesser`.
- Bestückung an der Maschine (Stufe F).

## P-2026-09-30-53 version-0-31-5

### EINGELESEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas ausprobieren,
  braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.31.5 an.

### DONE
- Version 0.31.5 mit P-2026-09-30-52 (Revolverart, Scheiben-Ø, VDI-Größe).

### TEST
- Die Prüfungen zu P-52 (siehe dort); die 21 Szenarien in 26.3 laufen nach dem Push.

### NEXT
- Push; Umschalter Ø/Radius für X.

## P-2026-09-30-52 revolverart

### EINGELESEN
- Manuel, 2026-09-30, auf die Frage nach der Revolverart in „Neue Maschine“ („VDI in der
  Stirn“ wie seiner oder „VDI am Umfang“ wie der Sternrevolver, dazu Scheiben-Ø und
  VDI-Größe): „1 ja“.
- Davor, mit Bild einer Kollision „Revolver berührt das Teil“: „bei dem revolver den ich
  habe ist das nicht möglich“. Und zum Sternrevolver: „wo der winkel kopf dafür da ist vorne
  sozusagen paralel zur maschinen z achse zu fräsen“.
- `camaddon/beispielmaschine.py` (Revolver in `drehmaschine`, `DrehmaschinenMasse`),
  `camaddon/halter.py` (`lage`: ein gewinkelter Halter kippt das Werkzeug zu X der
  Aufnahme), `camaddon/gui_neue_maschine.py`, `camaddon/reichweite.py` und
  `camaddon/gui_vierachs.py` (Hinweis „nicht radial“).

### DATEIEN
- `camaddon/beispielmaschine.py`, `camaddon/gui_neue_maschine.py`, `camaddon/reichweite.py`,
  `camaddon/gui_vierachs.py`, `translations/de.json`, `translations/en.json`,
  `help/de/neue_maschine.html`, `help/en/neue_maschine.html`,
  `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/spezifikation_werkzeugverwaltung.md`,
  `tests/test_beispielmaschine.py`, `tests/gui/szenario_neue_maschine.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Neue Maschine“ → Drehmaschine hat drei neue Zeilen: Revolver (VDI in der Stirn / am Umfang),
Scheiben-Ø und VDI-Größe. Mit „VDI am Umfang“ stehen die Aufnahmen radial auf dem Rand. Ein
gerader Halter zeigt dort zur Spindelachse, ein gewinkelter zum Futter. Der Stirnrevolver hat
am Umfang keine Klötze mehr.

### DONE
- `_revolver()` baut die Scheibe nach Bauart:
  - Stirn: die Aufnahmen im Kreis an der Stirn, 40 mm innerhalb des Rands. Am Umfang
    nichts mehr; die angedeuteten Stationen (D-46) stießen an Manuels Teil an.
  - Umfang: die Aufnahmen radial auf dem Rand. Das LCS von P1 hat Z radial (gerader Halter
    zur Spindelachse) und X zum Futter (dorthin kippt ein gewinkelter Halter).
  - Der Bezugspunkt, bis zu dem X und Z zählen, ist bei beiden die Achse der Aufnahme an
    ihrer Stirn. Gebaut steht der Sternrevolver bei X 225 und Z 285.
- `DrehmaschinenMasse`: `revolver`, `scheibe` (240 … 600 mm), `vdi` (20 … 60), je mit einem
  Satz, wenn es nicht passt.
- „Neue Maschine“ bekommt die drei Zeilen, jede mit Tooltip.
  - Der Dialog wuchs beim Wechsel der Bauart nicht mit, und Qt quetschte die Zeilen
    übereinander, im Bild gesehen und nachgemessen: 567 statt 623 Pixel.
  - Jetzt passt er seine Größe nach dem Wechsel an und wird nie kleiner als sein Inhalt.
  - Die Beschreibung der Drehmaschine sagt nun „VDI-Aufnahme … in der Stirn der Scheibe oder
    am Umfang“.
- Der gelbe Satz „nicht radial“ (Assistent und Prüffenster) rät zum geraden Halter, wo die
  Aufnahme selbst radial steht. Sonst nennt er wie bisher „VDI30 angetrieben radial“.
- Hilfe (de/en) und Spezifikation ergänzt. In der Spezifikation der Werkzeugverwaltung steht
  der Plan für die Bestückung an der Maschine (Stufe F, Manuel: „berücksichtigung an der
  Maschine“) mit drei Entscheidungen.

### TEST
- `test_beispielmaschine`:
  - Sternrevolver: acht Plätze, Z von P1 radial, X zum Futter, gebaut X 195 und Z 285 bei
    Scheibe Ø 400. Auf X 0 und Z 0 steht P1 auf der Spindelachse in der Ebene der Spindelnase.
  - Ein gerader Halter kommt radial aus +X, „VDI30 angetrieben radial“ nicht.
  - Ungültige Revolverart, Scheibe und VDI-Größe werden erkannt.
  - Der Stirnrevolver hat keine Stationen am Umfang.
  - Ok in 1.1.3 und 26.3.
- Außerdem in 1.1.3 ok: `test_abfahren`, `test_kette`, `test_kinematik`, `test_maschine`,
  `test_reichweite`, `test_restmaterial`, `test_schraege_achse`, `test_vierachs_achsen`,
  `test_vierachs_pruefen`, `test_kollision`, `test_sprache`, `test_hilfe`. In 26.3 ok:
  `test_reichweite`, `test_sprache`, `test_hilfe`.
- Die 21 Szenarien mit Beispielmaschinen in 1.1.3: ok.
- `szenario_neue_maschine`, jetzt auch mit einem Sternrevolver: ok in 1.1.3 und 26.3. Bilder
  angesehen: der Dialog ungequetscht, die Aufnahmen rundum am Umfang.

### NEXT
- Umschalter Ø/Radius für X an der Maschine (Manuel: „wichtig ist ja nur was dann beim
  Postprozess raus kommt“), dann Bestückung (Stufe F).

## P-2026-09-30-51 version-0-31-4

### EINGELESEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas ausprobieren,
  braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.31.4 an.

### DONE
- Version 0.31.4 mit P-2026-09-30-50: X und Z der Drehmaschine zählen wie an der Maschine.
- Status: Als Nächstes Werkzeuge ohne Platz, Revolverart, X als Durchmesser.

### TEST
- Die Prüfungen zu P-50 (siehe dort); die 21 Szenarien in 26.3 laufen nach dem Push.

### NEXT
- Push, Bericht an Manuel: Maschine neu bauen, damit die neue Zählung gilt.

## P-2026-09-30-50 x-z-wie-an-der-maschine

### EINGELESEN
- Manuel, 2026-09-30, mit Bildern seines Scheibenrevolvers (VDI plan in der Scheibe) und eines
  Sternrevolvers: „bei x war wieder -430 drinnen gestanden .... ich glaube man muss das etwas
  konkretisieren .... bei MEINER art ... ist x 0 genau die MITTE von der Vdi aufnahme ...
  wo bei der anderen art die z0 ist weis ich nicht“. Auf Nachfrage: „da stand -300 drinnen“
  (Weg X in „Neue Maschine“).
- `camaddon/beispielmaschine.py` (`gelenk_wie_gebaut`, `drehmaschine`,
  `DrehmaschinenMasse`, `_wege_fehler`), `camaddon/gui_neue_maschine.py`,
  `camaddon/verfahren.py` (`gelenkstellung`, `Verfahren.setze_alle`),
  `help/*/neue_maschine.html`, `docs/spezifikation_maschine_aus_baugruppe.md`.
- Ausgemessen an der Beispiel-Drehmaschine: Die Mitte von P1 an ihrer Stirn steht gebaut
  275 mm von der Spindelachse und 220 mm vor der Spindelnase.

### DATEIEN
- `camaddon/beispielmaschine.py`, `camaddon/gui_neue_maschine.py`, `translations/de.json`,
  `translations/en.json`, `help/de/neue_maschine.html`, `help/en/neue_maschine.html`,
  `docs/spezifikation_maschine_aus_baugruppe.md`, `tests/test_beispielmaschine.py`,
  `tests/test_schraege_achse.py`, `tests/gui/szenario_neue_maschine.py`,
  `tests/gui/szenario_verfahren_schraeg.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
An der Beispiel-Drehmaschine steht auf X 0 die Mitte der VDI-Aufnahme P1 auf der
Spindelachse, auf Z 0 ihre Stirn in der Ebene der Spindelnase. „Neue Maschine“ zeigt als
Vorgabe X −25 … 425 und Z 0 … 520 und sagt darunter, wovon die Wege zählen.

### DONE
- X und Z der Drehmaschine zählen wie an der Maschine. X geht ab der Spindelachse (Radius),
  Z ab der Spindelnase, jeweils bis zum Bezugspunkt des Revolvers (die Mitte der Aufnahme in
  Arbeitsstellung an ihrer Stirn). Y zählt wie bisher ab der Mitte der Spindel.
- `gelenk_wie_gebaut(…, stellung=…)`: Das Gelenk steht gebaut auf dieser Stellung. Seite 1
  liegt um so viel längs der Achse zurück. Die Drehmaschine rechnet X 275 und Z 220 aus der
  gebauten Lage von P1 und der Spindelnase.
- Die Wege bekommen X und Z erst am Ende (`_in_die_wege`). Liegt die gebaute Stellung
  außerhalb, fährt die Maschine hinein, etwa X auf 120 bei einem Weg bis 120.
- Vorgabe X −25 … 425 und Z 0 … 520: dieselben Wege wie vorher, nur anders gezählt.
- Prüfung der Maße:
  - X muss bis 0 reichen, also bis zur Spindelachse.
  - Z braucht nur ein Stück: „bis“ größer als „von“ (neuer Satz `neu.weg_leer`).
- „Neue Maschine“ hat bei der Drehmaschine eine graue Zeile unter den Wegen und je Achse einen
  Tooltip: wovon sie zählen, X als Radius, die Steuerung zeigt oft den Durchmesser.
- Hilfe (de/en) und Spezifikation ergänzt.

### TEST
- `test_beispielmaschine`, jetzt mit Nullpunkt:
  - gebaut X 275, Z 220; die Wege stimmen;
  - auf X 0 und Z 0 steht P1 auf der Spindelachse in der Ebene der Spindelnase;
  - eine eigene Maschine mit X bis 120 steht nach dem Bauen auf 120.
- `test_schraege_achse` (Start X 275, Anschlag bei 425), `test_abfahren`, `test_kette`,
  `test_kinematik`, `test_maschine`, `test_reichweite`, `test_restmaterial`,
  `test_vierachs_achsen`, `test_vierachs_pruefen`, `test_verfahren`, `test_schruppwerte`,
  `test_sprache`, `test_hilfe`: ok in 1.1.3.
- Dieselben und `test_export` in 26.3: ok.
- Die 21 Szenarien mit Beispielmaschinen in 1.1.3: ok. Davon angepasst:
  - `szenario_verfahren_schraeg`: Start X1 275, X auf 415, Anschlag 425.
  - `szenario_neue_maschine`: Z 0 … 2500.
- Im Bild von „Neue Maschine“ steht die Vorgabe X −25 … 425, Z 0 … 520 mit der grauen Zeile.
  Die erste Fassung der Zeile war zu lang und wurde gequetscht; gekürzt, feste Höhe für zwei
  Zeilen. Bei der Fräse ist sie aus.

### NEXT
- Revolverart in „Neue Maschine“ (VDI in der Stirn / am Umfang), wenn Manuel es will.
- X als Durchmesser, wenn seine Steuerung so zählt (E4).

## P-2026-09-30-49 version-0-31-3

### EINGELESEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas ausprobieren,
  braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.31.3 an.

### DONE
- Version 0.31.3 mit P-2026-09-30-48 (Haken „Bahn“ im Abspieler). Manuel probiert gerade aus.

### TEST
- Die Prüfungen zu P-48 (siehe dort); 26.3 läuft nach dem Push.

### NEXT
- Push; Nullpunkt X/Z wie an der Maschine.

## P-2026-09-30-48 haken-bahn

### EINGELESEN
- Manuel, 2026-09-30, mit Bild vom Prüffenster beim Abspielen von „Rundum schruppen T2“:
  „irgendwo einen hacken für werkzeugwege ausblenden“. Die blauen Linien verdecken, wie die
  Stange abgetragen wird.
- `camaddon/gui_abfahren.py` (`Bild`, `Abspieler`), `camaddon/gui_reichweite.py`
  (`PruefPanel`), `help/*/reichweite.html`, `tests/gui/szenario_vierachs_schruppen.py`.

### DATEIEN
- `camaddon/gui_abfahren.py`, `camaddon/gui_reichweite.py`, `translations/de.json`,
  `translations/en.json`, `help/de/reichweite.html`, `help/en/reichweite.html`,
  `tests/gui/szenario_vierachs_schruppen.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Abspieler steht der Haken „Bahn“. Ohne ihn ist die Bahn beim Abspielen aus, mit ihm wieder
da. Am Ende mit den Farben ist sie immer aus. Beim nächsten Öffnen steht der Haken wie zuletzt.

### DONE
- Haken „Bahn“ in der Zeile des Abspielers, neben der Lupe, mit Tooltip. Er ist gemerkt
  (`AbfahrenBahnZeigen` in den Einstellungen des Addons).
- `Bild.zeige_bahn()`: Die Bahn ist zu sehen, wenn der Haken sitzt und das Abspielen nicht
  am Ende mit den Farben steht.
- Hilfe (de/en) ergänzt.

### TEST
- `szenario_vierachs_schruppen` in 1.1.3: Der Haken sitzt, die Bahn ist da. Ohne Haken ist sie
  weg (Bild `3c_ohne_bahn`), mit Haken wieder da. Am Ende sind Bahn und Teil aus. Ok.
- `test_sprache` und `test_hilfe` in 1.1.3: ok.

### NEXT
- Nullpunkt X/Z wie an der Maschine (Mitte der VDI-Aufnahme), Revolver wie Manuels.

## P-2026-09-30-47 version-0-31-2

### EINGELESEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas ausprobieren,
  braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.31.2 an.

### DONE
- Version 0.31.2 mit P-2026-09-30-44 (kein Fehlalarm Blau an Manuels Testteil), -45 (das
  fertige Teil am Ende ausgeblendet) und -46 (Wege bis 10 m).
- Status: Als Nächstes Nullpunkt X an der VDI-Aufnahme und Werkzeuge ohne Platz; W-005 wartet
  auf E1–E7.

### TEST
- Die Prüfungen zu P-44 bis -46 (siehe dort).

### NEXT
- Push, Bericht an Manuel; seine Antworten zu −430 (wo?) und X (Ø oder Radius?).

## P-2026-09-30-46 wege-bis-10-m

### EINGELESEN
- Manuel, 2026-09-30, mit Bild von „Neue Maschine“ (FreeCAD 1.1.4): „der weg in Z ist
  begrenzt auf 999 als eingabe .. 1000 kann ich noch mit den pfeilen machen das wars dann
  aber auch ... sollte man ändern es gibt maschinen die sind deutlich länger“.
- `camaddon/beispielmaschine.py` (`GROESSTER_WEG` 1000 mm, `_wege_fehler`),
  `camaddon/gui_neue_maschine.py` (`_wegfeld`), `tests/test_beispielmaschine.py`,
  `tests/gui/szenario_neue_maschine.py`.

### DATEIEN
- `camaddon/beispielmaschine.py`, `tests/test_beispielmaschine.py`,
  `tests/gui/szenario_neue_maschine.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In „Neue Maschine“ lässt sich bei Weg Z „2500“ eintippen, und die Maschine wird damit gebaut.

### DONE
- Wege bis 10 000 mm je Richtung (bisher 1000). Die Felder und die Prüfung der Maße nehmen
  dieselbe Grenze.

### TEST
- `test_beispielmaschine`: −20 000 mm ist zu lang. Ok in 1.1.3.
- `szenario_neue_maschine` in 1.1.3: „2500“ in Z eingetippt, der Weg ist −220 … 2500. Ok, im
  Bild zu sehen.

### NEXT
- Nullpunkt X an der Mitte der VDI-Aufnahme (Manuels Revolver), Werkzeug ohne Platz.

## P-2026-09-30-45 teil-am-ende-aus

### EINGELESEN
- Das Bild am Ende von Manuels Testteil: Das fertige Teil (hellblau, `MODELL`) schien durch
  die gefärbte Stange. Wo nichts mehr steht, liegt die Stange genau auf ihm; das ergab einen
  hellblauen Sägezahn neben „blau: im Teil“ in der Legende, obwohl keine Zelle blau war.
- Wo die Stange wirklich ins Teil ginge, deckte das Teil die blauen Zellen zu.
- `camaddon/gui_abfahren.py` (`Bild`, `abtragen`), `help/*/reichweite.html`.

### DATEIEN
- `camaddon/gui_abfahren.py`, `help/de/reichweite.html`, `help/en/reichweite.html`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Am Ende des Abspielens sind nur die Farben der Stange zu sehen, ohne das hellblaue Teil. Beim
Zurückspulen ist das Teil wieder da.

### DONE
- Das fertige Teil steckt in einem Schalter wie die Bahn. `abtragen()` blendet beide an der
  letzten Station aus und davor wieder ein.
- Hilfe (de/en): „An der letzten Station verschwinden die Bahn und das fertige Teil“.

### TEST
- `szenario_flaechen_pruefen` und `szenario_rundum_drehmaschine` in 1.1.3: ok. Im Bild der
  Abflachung ist das Ende der Stange geschlossen, ohne Hellblau.

### NEXT
- Wege bis 10 m (Manuel: Z nur bis 999 einzutippen).

## P-2026-09-30-44 vergleich-nicht-rundum

### EINGELESEN
- Manuel, 2026-09-30, mit `test4achsbearbeitung.FCStd`: „das hier oben angeheftete teil ist
  übrigens das testteil ... für ringsrum bearbeiten“.
- Das Testteil durch den Assistenten auf der Beispiel-Drehmaschine (T1 Schaftfräser Ø 12, T2
  Kugelfräser Ø 6, Halter „VDI30 angetrieben radial“): Stange Ø 80, 17 Lagen, Schlichten 100
  Umdrehungen, 148 min. Das Prüffenster meldete am Ende „fehlen bis 30,91 mm im Teil (blau)“.
- Am Körper nachgemessen: Keine Bahn dringt ein (höchstens 0,005 mm). Das Blau lag hinten,
  wo das Teil neben der Achse steht, dazu 0,11 mm an einer scharfen Kante und 0,05 mm auf der
  Stirnebene.
- `camaddon/restmaterial.py` (`vergleiche`, `Abtrag.vergleich`), `camaddon/gui_abfahren.py`
  (`_rest_satz`), `vierachs_huelle` (Strahlen mit x ≤ 0 zählen nicht), `help/*/reichweite.html`,
  `docs/spezifikation_vierachs.md` (V3g, V5e).

### DATEIEN
- `camaddon/restmaterial.py`, `camaddon/gui_abfahren.py`, `translations/de.json`,
  `translations/en.json`, `tests/test_restmaterial.py`, `help/de/reichweite.html`,
  `help/en/reichweite.html`, `docs/spezifikation_vierachs.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuels Testteil, geschruppt und geschlichtet, zeigt im Prüffenster am Ende nichts Blaues.
Der Satz sagt, wo nicht verglichen wurde. Ein Rohr wird weiter verglichen, und ein Schnitt ins
Rohr ist blau.

### DONE
- Die Stange kennt je Strahl aus der Achse nur einen Radius. Liegt das Teil nicht rund um die
  Achse, fährt der Fräser bis an die Achse und nimmt auf einem Strahl weg, was zwischen Achse
  und Teil liegt. Für die Stange fehlte dann das Teil dahinter.
- Deshalb vergleicht es an Stellen nicht, an denen manche Strahlen das Teil vor der Achse
  haben und andere nicht (`Vergleich.ohne_vergleich`: die Stücke von–bis). Die anderen Strahlen
  sehen es nur hinter der Achse (die Hüllfläche gibt dort einen negativen Radius) oder gar
  nicht. Der Satz darunter nennt die Stücke. Ein Rohr hat jeder Strahl vor sich; dort kommt
  kein Fräser an die Achse, und es wird verglichen.
- Zwei Fassungen davor verworfen:
  - „Liegt die Achse im Teil?“ hätte ein Rohr ganz ausgenommen.
  - „Trifft der Strahl das Teil überhaupt?“ übersah die Stelle −88,5 mm am Testteil. Dort
    liegt die Achse 0,2 mm neben der flachen Seite des D-Profils, und jeder Strahl sieht das
    Teil, manche nur dahinter.
- An einer scharfen Kante und an den Enden ist erst blau, was tiefer liegt als die halbe
  Änderung zur Nachbarzelle. Dort weiß das Raster nicht genau, wo das Teil liegt.
- Hilfe (de/en) und Spezifikation ergänzt.

### TEST
- `test_restmaterial`: Rohr, Quader 0,2 mm neben und um die Achse, drei Stücke (eines mit
  Strahlen nur hinter der Achse), Kante und Ende. Ok in 1.1.3 und 26.3.
- `test_sprache` und `test_hilfe`: ok in 1.1.3 und 26.3.
- Das Testteil als Szenario in 1.1.3: nach dem Schruppen 0,33 … 27,30 mm, am Ende 0 … 2,96 mm,
  nichts blau. Der Satz nennt „Von −90,25 mm bis −87,25 mm längs liegt das Teil nicht rund um
  die Achse …“.
- `szenario_flaechen_pruefen`, `szenario_rundum_drehmaschine` und
  `szenario_vierachs_schruppen`: ok in 1.1.3 und 26.3.

### NEXT
- Version 0.31.2, Push, Bericht an Manuel mit Bildern.

## P-2026-09-30-43 plan-steuerung-zwei-wege

### EINGELESEN
- Manuel, 2026-09-30: „bei siemens genug befehle die eben umstellen von durchmesser auf nicht
  durchmesser .. und auch ist es möglich die bearbeitung eben mit der c achse anstatt der y
  achse zu machen ... ob das irgendwie geht das man sagt man hat ein werkzeug das 90 grad zur
  maschinen z steht ... und dreht dann die c achse ... oder ob das wirklich in einzelsätzen mit
  c angabe gemacht werden muss ... in alle ... so akkurat wie möglich ... oder eben beide
  optionen ... wir können wirklich 0.005 mm verfahren ... und das dann verschleifen“; dazu aus
  dem Siemens-Programmierhandbuch PGsl_1015_de_de-DE: G64, G641/G642, COMPCAD/COMPSURF/COMPCURV,
  SOFT; „solche optionen mit hacken ... das auf JEDENFALL erklärt wird was was ist ... so das
  man es beim bedienen lernen kann ... hinter neuen fenstern oder html verstecken“. Dazu sein
  Testteil für rundum (Loft, D-Profil 70 × 25, 90 mm).
- `docs/spezifikation_steuerung.md`.

### DATEIEN
- `docs/spezifikation_steuerung.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Plan W-005 enthält beide Wege an der Drehmaschine (Transformation der Steuerung, wo die
Maschine sie hat und die Fläche auf einem Radius liegt; sonst Punkt für Punkt mit Vorausschau
und Glätten), die Glätten-Befehle als erklärte Haken, das einfache Fenster („Einstellungen …“,
Hilfeseite je Steuerung, Vorschau) und die Entscheidungen E6, E7.

### DONE
- Abschnitte 6 (zwei Wege), 7 (Vorausschau und Glätten, Siemens-Beispiel), 8 (einfach
  bedienen), Stufen S4–S8 neu geordnet, E6 und E7.

### TEST
- Reine Doku, kein Testlauf.

### NEXT
- Manuels Antworten zu E1–E7; S1.

## P-2026-09-30-42 plan-steuerung

### EINGELESEN
- Manuel, 2026-09-30: „ja das mit der Steuerung ... Sollte keine Rolle spielen .... Es muss
  ja für alle funktionieren....“, dann auf die Auswahl A/B/C: „A sollte unsere option sein...“.
- `CHATSTART.md` (keine bestimmte Maschine), `camaddon/maschine.py`, `camaddon/reichweite.py`
  (`merke_maschine`), `camaddon/export.py`; FreeCAD 1.1.3 und 26.3: `Path/Preferences.py`
  (`searchPathsPost`, `addAddonPostPath`, Addon-Postprozessoren über `package.xml`),
  `Path/Post/Processor.py` (`PostProcessorFactory`, `WrapperPost`), `Machine/models/machine.py`
  (Postprozessor, Ausgabeoptionen, Umbruch der Rundachse); Haas-Codes M133–M135, M154/M155;
  Siemens SETMS, SPOS, DIAMON/DIAMOF, TRACYL/TRANSMIT; LinuxCNC G7/G8, G93; Fanuc 0i-TF G07.1,
  G12.1.

### DATEIEN
- `docs/spezifikation_steuerung.md` (neu), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Plan für W-005 steht in der Spezifikation: Steuerung an der Maschine mit vorbelegten,
änderbaren Befehlen, eigener Postprozessor „camaddon“, Drehmaschine (Durchmesser,
angetriebenes Werkzeug, C-Achse, Vorschub), Stufen S1–S6 und die Entscheidungen E1–E5 als
Auswahl mit Empfehlung.

### DONE
- Spezifikation W-005 geschrieben, Wunschliste und Stand ergänzt.

### TEST
- Reine Doku, kein Testlauf.

### NEXT
- Manuels Antworten zu E1–E5, dann S1 (Postprozessor „camaddon“ wie LinuxCNC, angemeldet in
  beiden Versionen).

## P-2026-09-30-41 version-0-31-1

### EINGELESEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas ausprobieren,
  braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.31.1 an.

### DONE
- Version 0.31.1 mit P-2026-09-30-39 (F in jedem G93-Satz für jeden Postprozessor).

### TEST
- Die Prüfungen zu P-39 (siehe dort), in beiden Versionen ok.

### NEXT
- Push, Bericht an Manuel.

## P-2026-09-30-40 testregel

### EINGELESEN
- Manuel, 2026-09-30: „Laufen die immernoch... Das mit den testen .. ist immer noch viel....
  Muss das wirklich sein??“ – und auf die Auswahl: „Ich habe damals auch gesagt wenn DU sie
  für nötig hältst ...... Ich persönlich benötige keine Tests solange Ales funktioniert“.
- `CLAUDE.md` (Pushen), `docs/arbeitsregeln.md` Abschnitt 5, `CHATSTART.md`, `docs/aufbau.md`.

### DATEIEN
- `CLAUDE.md`, `docs/arbeitsregeln.md`, `CHATSTART.md`, `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Regeln sagen: Vor einem Push laufen die Prüfungen zum geänderten Teil; der volle Lauf in
beiden Versionen nur, wenn er nötig ist (gemeinsamer Kern, neue FreeCAD-Version, Version mit
vielen Änderungen) – und darf auch nach dem Push laufen.

### DONE
- Neue Regel wie oben; ein voller Lauf dauerte zuletzt rund 40 Minuten, die gezielten
  Prüfungen Minuten.

### TEST
- Reine Doku, kein Testlauf.

### NEXT
- –

## P-2026-09-30-39 f-in-jedem-satz

### EINGELESEN
- Manuel, 2026-09-30, zur Frage nach seiner Steuerung: „Sollte keine Rolle spielen …
  Es muss ja für alle funktionieren“.
- `camaddon/vierachs_bahn.py` (`befehle`), `fanuc_post.py` und `uccnc_post.py` von FreeCAD
  (F nur, wenn `currLocation["F"] != F`), die Speicherung einer Bahn im Dokument (F auf 6
  Nachkommastellen, nachgeprüft), `tests/test_vierachs_bahn.py`,
  `tests/test_vierachs_operation.py`, `help/*/vierachs.html`, `docs/spezifikation_vierachs.md`.

### DATEIEN
- `camaddon/vierachs_bahn.py`, `tests/test_vierachs_bahn.py`,
  `tests/test_vierachs_operation.py`, `help/de/vierachs.html`, `help/en/vierachs.html`,
  `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Eine Rundum-Operation durch den Postprozessor Fanuc oder UCCNC von FreeCAD, ohne Optionen:
Zwischen G93 und G94 steht in jedem Vorschubsatz ein F.

### DONE
- F für G93 steht auf 6 Stellen (so speichert FreeCAD die Bahn); gleicht es dem F davor,
  bekommt es eine Einheit der 6. Stelle mehr. Dann lassen auch Fanuc und UCCNC es nicht weg;
  im Programm (× 60, 3 Stellen) sieht man den Unterschied nicht, die Zeit ändert sich um
  weniger als ein Millionstel.
- Hilfe und Spezifikation: keine Optionen mehr nötig.

### TEST
- `test_vierachs_bahn` (gleich lange Sätze: F abwechselnd um eine Einheit der 6. Stelle
  verschieden), `test_vierachs_operation` (LinuxCNC, Mach3/Mach4, Fanuc, UCCNC ohne Optionen:
  F in jedem Vorschubsatz), `test_vierachs_schlichten_op`, `test_abfahren`,
  `test_vierachs_pruefen`, `test_restmaterial`, `test_hilfe` – in 1.1.3 und 26.3 ok.

### NEXT
- Für Drehmaschinen (Radius, angetriebenes Werkzeug, Fanuc-G94) einen Weg planen, der für
  jede Steuerung geht.

## P-2026-09-30-38 version-0-31-0

### EINGELESEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md: Soll Manuel etwas
  ausprobieren, braucht der Push eine höhere Version.

### DATEIEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates suchen“ bzw. der Addon-Manager bietet 0.31.0 an.

### DONE
- Version 0.31.0 mit P-2026-09-30-31 bis -37: getrennte Flächen nacheinander, Prüfen nur auf
  den gewählten Flächen, Installation ohne Pythons SSL, Fräser im Halter, Postprozessoren in
  der Hilfe. README und Stand.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in 1.1.3 und 26.3 vor dem Push.

### NEXT
- Push nach grünem Lauf, Bericht an Manuel.

## P-2026-09-30-37 halter-nahaufnahme

### EINGELESEN
- `tests/gui/szenario_rundum_drehmaschine.py`, `camaddon/gui_abfahren.py` (`Bild`,
  `aufnahmen`, `folge`), `camaddon/halter.py` (`form`, `lage` – Lage von Kopf und Abgang im LCS
  der Aufnahme); die Bilder 2 und 3 des Szenarios nach P-2026-09-30-34.

### DATEIEN
- `tests/gui/szenario_rundum_drehmaschine.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Bild zeigt von der Seite, dass der Fräser im Halter steckt: Revolver, Kopf des radialen
Halters, Abgang, Nase, Schaft, Schneide am Teil.

### DONE
- Nach „2_t1_am_teil“ stellt das Szenario die Kamera quer auf Aufnahme, Halter und Fräser (im
  LCS der Aufnahme von −Y, Z oben) und nimmt „2b_t1_im_halter“ auf. Aus der Sicht von Bild 2
  verdeckt der Revolver den Halter halb.

### TEST
- `szenario_rundum_drehmaschine` in 1.1.3: ok, Bild angesehen – der Schaft reicht bis in die
  Nase des Halters.

### NEXT
- Manuel das Bild zeigen.

## P-2026-09-30-36 postprozessoren

### EINGELESEN
- Manuel, 2026-09-30: „Was sagst du zu den in freecad vorhandene. Postprozessoren ...
  Funktionieren die so wie wir das hier bauen??“
- Alle Postprozessoren von FreeCAD 1.1.3 und 26.3 (`Path/Post/scripts/*_post.py`,
  `Path/Post/Processor.py`: `PostProcessorFactory`); `camaddon/vierachs_bahn.py` (`befehle`),
  `help/*/vierachs.html` („Im Programm“), `docs/spezifikation_vierachs.md` (G93),
  `tests/test_vierachs_operation.py`.

### DATEIEN
- `help/de/vierachs.html`, `help/en/vierachs.html`, `docs/spezifikation_vierachs.md`,
  `tests/test_vierachs_operation.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Hilfe sagt, mit welchem Postprozessor von FreeCAD das Programm einer Rundum-Operation so
herauskommt, wie es muss (G93, C, F in jedem Vorschubsatz), welche Option Fanuc und UCCNC
brauchen und worauf man an der Drehmaschine achten muss; die Prüfung hält das fest.

### DONE
- Dieselbe Operation „Rundum schruppen“ (5 482 Vorschubsätze) durch jeden Postprozessor
  beider Versionen: LinuxCNC, Mach3/Mach4, Masso G3, Generic (26.3), KineticNC/Beamicon2,
  Estlcam, Dynapath 4060 – alles richtig. Fanuc und UCCNC lassen ein F weg, das gleich dem
  vorigen ist (386 bzw. 381 Sätze) – in G93 ein Alarm; mit `--no-axis-modal` bzw. `--repeat`
  steht es überall. Centroid, Smoothie, Fablin, Philips lassen C weg, Fangling F.
- Drehmaschine: Die Postprozessoren schreiben `M3 S…` (dort die Hauptspindel); angetriebenes
  Werkzeug und C-Achsbetrieb gehören in den Programmkopf. Fanuc-Drehmaschinen mit
  G-Code-System A: G94 ist dort ein Plandrehzyklus.
- Hilfe de/en, Spezifikation; `test_vierachs_operation` prüft LinuxCNC, Mach3/Mach4, Fanuc
  (`--no-axis-modal`) und UCCNC (`--repeat`): F in jedem Vorschubsatz, auch modal ohne „G1“,
  und C.

### TEST
- `test_vierachs_operation`, `test_hilfe` in 1.1.3 und 26.3: ok (26.3 gibt für einen
  unbekannten Postprozessor ein `CAMError` statt None zurück – die Prüfung nimmt beides).

### NEXT
- Manuel fragen, welche Steuerung seine Maschine hat: bei Fanuc-Drehen G98 statt G94.

## P-2026-09-30-35 installieren-test-umleitung

### EINGELESEN
- Erster Lauf von `tests/test_installieren.py` nach P-2026-09-30-33 (FreeCAD 1.1.3): „Addon
  Manager: Unexpected 0 response from server“ bei `/umleitung`.
- `NetworkManager.py` des Addon-Managers (`__reply_finished`: folgt Umleitungen selbst, mit
  `RedirectionTargetAttribute` als neuer Adresse).

### DATEIEN
- `tests/test_installieren.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`test_installieren` ist in 1.1.3 und 26.3 grün – auch der Weg über Qt mit Umleitung.

### DONE
- Der Addon-Manager folgt einer Umleitung selbst und nimmt die Adresse aus `Location`
  unverändert: eine relative („/stand.zip“) kann er nicht laden. GitHub schickt eine absolute
  (codeload.github.com); der Testserver jetzt auch. Am Code von P-33 ändert sich nichts.

### TEST
- `test_installieren` in 1.1.3 und 26.3: ok; `test_aktualisierung`, `test_kollision`: ok in
  beiden.

### NEXT
- Szenario `szenario_update` (Zeile aus dem README und Suche über Qt mit Oberfläche).

## P-2026-09-30-34 fraeser-im-halter

### EINGELESEN
- Manuel, 2026-09-30: „Warum ist der Fräser nicht im Halter?“ – zu den Bildern aus dem
  Prüffenster auf der Beispiel-Drehmaschine (T1 Ø 12, „VDI30 angetrieben radial“).
- `camaddon/kollision.py` (`werkzeugkoerper`), `camaddon/gui_abfahren.py` (`_werkzeug`),
  `camaddon/reichweite.py` (`werkzeugmasse`), `camaddon/werkzeuge.py`
  (`geschaetzte_laenge`, `laenge_mit_halter`), `camaddon/halter.py` (`form`, `lage`),
  `camaddon/beispielmaschine.py` (Revolver), `tests/test_kollision.py`.

### DATEIEN
- `camaddon/kollision.py`, `tests/test_kollision.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine, Werkzeug mit Halter, ohne eingetragene Gesamtlänge: Im Prüffenster
steckt der Schaft in der Nase des Halters – kein Spalt zwischen Fräser und Halter; die
Kollision prüft den Schaft bis dorthin.

### DONE
- Ursache: Der Schaft endete bei der Gesamtlänge. Die ist ohne Eintrag nur geschätzt (T1:
  26 + 2 × 12 = 50 mm), aus dem Halter ragen aber 125 − 55 = 70 mm – der Fräser schwebte 20 mm
  vor dem Halter, und die Kollision sah das Stück dazwischen nicht.
- Mit Halter reicht der Schaft jetzt immer bis zu seiner Nase (die Länge ab dem Bezugspunkt
  ist gemessen oder eingetragen), gerade wie gewinkelt. Ohne Halter wie bisher.

### TEST
- Noch nicht gelaufen (voller Lauf zu 0.30.0). Danach `test_kollision` (kurzer Fräser im
  gewinkelten und im geraden Halter: Schaft bis zur Nase), `szenario_rundum_drehmaschine` mit
  Bild.

### NEXT
- Ein Hinweis im Prüffenster, wenn eine eingetragene Gesamtlänge nicht bis in den Halter
  reicht, falls Manuel das will.

## P-2026-09-30-33 installieren-ohne-ssl

### EINGELESEN
- Manuel, 2026-09-30: „Die Installation bei mir geht nicht … Also er sagt irgendwas von
  unknownn url Typ https“.
- `installieren.py`, `README.md` (Installieren), `camaddon/aktualisierung.py`,
  `camaddon/gui_aktualisierung.py`, `tests/test_installieren.py`,
  `tests/test_aktualisierung.py`, `tests/gui/szenario_update.py`; im Addon-Manager von FreeCAD
  1.1.3 und 26.3: `NetworkManager.py` (`InitializeNetworkManager`, `blocking_get`),
  `addonmanager_utilities.py` (mit Oberfläche lädt er nur über Qt, nie über Pythons ssl).

### DATEIEN
- `installieren.py`, `README.md`, `camaddon/aktualisierung.py`,
  `camaddon/gui_aktualisierung.py`, `tests/test_installieren.py`,
  `tests/test_aktualisierung.py`, `tests/gui/szenario_update.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In einem FreeCAD, dessen Python kein ssl hat, installiert die Zeile aus dem README das Addon
(neu starten, Menü „CAM-Addon“ da), und „Nach Updates suchen“ findet eine neue Version – ohne
„unknown url type: https“.

### DONE
- „unknown url type: https“ heißt: urllib hat keinen https-Handler, weil Pythons ssl fehlt.
  Der Addon-Manager lädt mit Oberfläche über Qt und braucht es nicht.
- Die Zeile im README lädt `installieren.py` jetzt über seinen Netzzugang
  (`NetworkManager.AM_NETWORK_MANAGER.blocking_get`), gleich lang wie vorher.
- `installieren.hole()`: urllib wie bisher; kann es kein https (http.client ohne
  `HTTPSConnection`) oder scheitert es am Zertifikat, lädt Qt. Der Netzzugang muss im
  Hauptthread entstehen – `netz_vorbereiten()`, von `gui_aktualisierung.Suche.start()` vor dem
  Such-Thread gerufen; im Such-Thread ohne ihn ein Fehler statt Hängen.
- Die Suche ohne Git holt die Version mit `hole()` aus dem `installieren.py` des Addons.

### TEST
- Noch nicht gelaufen: FreeCAD ist durch den vollen Lauf zu 0.30.0 belegt (Arbeitsregeln).
  Danach: `test_installieren` (Entscheidung ohne ssl, Zertifikat → Qt, über Qt von einem
  HTTP-Server auf 127.0.0.1 mit Umleitung wie GitHub, 404, im Such-Thread, ohne Netzzugang
  kein Hängen), `test_aktualisierung`, `szenario_update` (die Zeile aus dem README und die Suche
  ohne Git über Qt, mit Oberfläche) in beiden Versionen.

### NEXT
- Manuel: die neue Zeile aus dem README – oder gleich über den Addon-Manager.

## P-2026-09-30-32 pruefen-gewaehlte

### EINGELESEN
- `camaddon/restmaterial.py` (`vergleiche`, `Abtrag`, `fuer`), `camaddon/gui_abfahren.py`
  (`_rest_satz`), `help/*/reichweite.html`, `tests/test_restmaterial.py`,
  `tests/gui/szenario_rundum_drehmaschine.py`.

### DATEIEN
- `camaddon/restmaterial.py`, `camaddon/gui_abfahren.py`, `translations/de.json`,
  `translations/en.json`, `help/de/reichweite.html`, `help/en/reichweite.html`,
  `tests/test_restmaterial.py`, `tests/gui/szenario_flaechen_pruefen.py` (neu),
  `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine, Welle mit Abflachung, im Assistenten nur die Abflachung, „Anlegen“ →
„Auf der Maschine prüfen“ → ans Ende: Farben nur auf der Abflachung, der Mantel bleibt Stange
ohne Farbe (nicht rot); unter dem Abspieler „… Verglichen auf den gewählten Flächen – was nicht
gewählt ist, bleibt Stange und hat keine Farbe.“

### DONE
- Haben alle Rundum-Operationen des Jobs gewählte Flächen, vergleicht der Abtrag nur auf ihnen:
  Grün, Gelb und Rot nur dort, was nicht gewählt ist, bleibt ohne Farbe; Blau (im Teil) gilt
  überall. Der größte Rest zählt auf den gewählten Flächen; der Satz unter dem Abspieler sagt,
  dass nur dort verglichen wurde. Hilfe de/en.

### TEST
- Noch nicht gelaufen: FreeCAD ist durch den vollen Lauf zu 0.30.0 belegt (Arbeitsregeln).
  Danach: `test_restmaterial` (nur über der Abflachung geschruppt: ohne Wahl rot, mit Wahl
  keine Farbe auf dem Mantel), `szenario_flaechen_pruefen` in beiden Versionen, `test_sprache`.

### NEXT
- V4c und V4d mit Manuel planen (Fragen in der Spezifikation).

## P-2026-09-30-31 hin-und-her-je-stueck

### EINGELESEN
- `camaddon/vierachs_bahn.py` (`_fahrten`, `_einfahrt`, `_rampe`, P-2026-09-30-28).

### DATEIEN
- `camaddon/vierachs_bahn.py`, `tests/test_vierachs_bahn.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit zwei Abflachungen gegenüber, beide gewählt, „Anlegen“: Je Lage fräst der Fräser erst
die eine Abflachung ganz, hebt einmal ab, dreht hinüber und fräst die andere ganz – nicht in
jeder Zeile hin und zurück zwischen beiden.

### DONE
- Getrennte Stücke des Bereichs (zusammen hängen Stücke benachbarter Zeilen, die sich rundum
  überlappen) fährt `_fahrten` nacheinander ganz – vorher wechselte es in jeder Zeile zwischen
  ihnen und hob dazu jedes Mal ab.
- Die Rampe hinein läuft längs der ganzen Fahrt, auch über den Schritt zur nächsten Zeile – an
  der Spitze eines Bereichs ist die erste Zeile oft kürzer als eine Rampe, dann ging es bisher
  senkrecht hinein.

### TEST
- Noch nicht gelaufen: FreeCAD ist durch den vollen Lauf zu 0.30.0 belegt (Arbeitsregeln).
  Numpy-Probe ohne FreeCAD: zwei getrennte Stücke → zwei Fahrten; Band rundum → eine Fahrt
  je Lage, alles im Bereich. Danach: `test_vierachs_bahn` (zwei Abflachungen: zweimal heraus
  je Lage), `test_vierachs_schlichten`.

### NEXT
- V4e: Prüfen nur auf den gewählten Flächen.

## P-2026-09-30-30 v4c-fragen

### EINGELESEN
- Manuels Nachricht (2026-09-30): „Also nicht, dass du das jetzt anpassen sollst an die
  vorhandenen … Wenn dann müssten wir eigene planen.“ – `docs/spezifikation_vierachs.md`
  (V4c).

### DATEIEN
- `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Unter V4c steht, was gebaut ist („hin und her“) und die drei offenen Fragen an Manuel: Plan
indexiert (braucht eine Achse quer zur Stange, welche Maschine zuerst), Linien längs (eigene Wahl
oder von selbst), Vorschlag je Fläche oder einer für alle.

### DONE
- V4c-Stand und die Fragen für die gemeinsame Planung in der Spezifikation; gebaut wird V4c erst
  mit Manuels Antworten.

### TEST
- Reine Doku, kein Testlauf (`docs/arbeitsregeln.md`, Abschnitt 5).

### NEXT
- V4e: Prüfen nur auf den gewählten Flächen.

## P-2026-09-30-29 version-0-30-0

### EINGELESEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`, die Einträge P-2026-09-30-25 bis -28.

### DATEIEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.30.0 an. Danach: Welle mit Abflachung, „4-Achs-Bearbeitung“ →
Weiter → die Abflachung anklicken: in der Liste grün „Face3  Ebene – erreichbar“, im 3D grün;
„Anlegen“ → die Bahnen liegen als Zeilen hin und her nur über der Abflachung.

### DONE
- Version 0.30.0 mit W-003 V4 „Flächen wählen“ (V4a Assistent, V4b Bahnen im Bereich, hin und
  her). README, Stand und die Beschreibung im Paket nachgezogen.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in FreeCAD 1.1.3 und im Wochen-Build – siehe
  Push-Nachricht.

### NEXT
- Push; Bericht an Manuel mit Klickweg und Screenshots; V4c mit Manuel planen.

## P-2026-09-30-28 flaechen-hin-und-her

### EINGELESEN
- Manuels Nachricht zum Bild der Bahn über der Abflachung (2026-09-30): „Also ich hoffe, dass
  die roten Striche keine Eilgänge sind, weil man kann ja auch einfach zurück drehen für so
  eine Fläche …“ – sie waren es: Nach jedem Überfahren hob der Fräser ab und drehte im Eilgang
  den Rest der Umdrehung weiter.
- `camaddon/vierachs_bahn.py` (P-2026-09-30-26: Spirale mit Bereich), `docs/spezifikation_vierachs.md`
  (V4b), `help/*/vierachs.html`.

### DATEIEN
- `camaddon/vierachs_bahn.py`, `tests/test_vierachs_bahn.py`, `tests/test_vierachs_schlichten.py`,
  `help/de/vierachs.html`, `help/en/vierachs.html`, `docs/spezifikation_vierachs.md`,
  `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit Abflachung, nur die Abflachung gewählt, „Anlegen“: Im 3D liegen die grünen Bahnen
als Zeilen hin und her über der Abflachung, am Ende jeder Zeile ein kurzer Schritt längs; rot
(Eilgang) nur das Anfahren, das Wegfahren und der Weg zurück nach vorn für die nächste Lage –
keine Kreise mehr um die Welle.

### DONE
- Mit gewählten Flächen fräsen Schruppen und Schlichten in Zeilen bei festem a hin und her
  (`_zeilen`, `_bereiche`, `_fahrten`, `_anschluss`): Jede Zeile nur über ihr Stück im Bereich,
  am Ende in der Tiefe zur nächsten Zeile, die Rundachse dreht zurück; endet die nächste früher,
  zurück auf der alten bis über ihren Anfang, reicht sie weiter, erst hinüber und dann ganz
  hindurch. Abheben nur zwischen getrennten Stücken. Schruppen: Zeilen im Abstand „Vorschub je
  Umdrehung“, Schlichten im Abstand der Schrittweite, vor jeder Wand eine Zeile als Ring; der Weg
  zwischen zwei Zeilen auf der Hüllfläche (beim Schlichten genau dort gerechnet).
- Hinein wie bisher: Eilgang bis knapp über die Tiefe der Lage davor bzw. den Rest, Rampe mit dem
  Eintauchwinkel längs der ersten Zeile, senkrecht nur, wo nichts zu fräsen ist oder die Zeile
  davor dort schon fräste; Schlichten senkrecht mit dem Eintauchvorschub, auch die Stufen.
- Die Hüllfläche fürs Schruppen nur über dem Bereich – schneller. Rundum (ohne Flächen) bleibt
  die Spirale, unverändert.

### TEST
- KI ohne Oberfläche, FreeCAD 1.1.3: `test_vierachs_bahn` (Abflachung: alles im Bereich, je Lage
  einmal heraus, keine senkrechte Einfahrt ins Material, die Rundachse bleibt in einem Bereich
  unter 120°, mehr als zehnmal zurückgedreht, eine Zeile als Ring vor der Wand; darüber 0,45 mm,
  in den Ecken 1,12 mm, gegenüber unberührt), `test_vierachs_schlichten` (Abflachung: 3 Fahrten,
  jede knapp über dem Rest mit Eintauchvorschub, die Zeilen reichen über die ganze Abflachung),
  `test_vierachs_operation`, `test_vierachs_flaechen` grün.
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_vierachs_flaechen` grün – das Bild
  „4_angelegt“ zeigt die Zeilen hin und her.

### NEXT
- Voller Lauf, Version 0.30.0, Push, Bericht an Manuel; danach V4c „Plan indexiert“ (Plan mit
  Manuel, er will eigene Strategien planen).

## P-2026-09-30-27 flaechen-assistent

### EINGELESEN
- `camaddon/gui_vierachs.py` (Schritt 2, Beobachter und Auswahlfilter, Vorschau, Anlegen,
  Ändern, Schließen), `tests/gui/szenario_vierachs_schlichten.py`,
  `tests/gui/_lauf/szenario_lauf.py`, `help/*/vierachs.html`, `docs/spezifikation_vierachs.md`
  (V4a).

### DATEIEN
- `camaddon/gui_vierachs.py`, `translations/de.json`, `translations/en.json`,
  `tests/gui/szenario_vierachs_flaechen.py` (neu), `help/de/vierachs.html`,
  `help/en/vierachs.html`, `docs/spezifikation_vierachs.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit Abflachung, „4-Achs-Bearbeitung“ → Weiter → in Schritt 2 steht unter „Flächen“ grau
„Rundum – alle Mantelflächen …“. Ein Klick auf die Abflachung: In der Liste steht grün „Face3
Ebene – erreichbar“, im 3D ist sie grün, darunter „Nur diese Flächen: …“. „Alle Mantelflächen“
→ „Alle Mantelflächen gewählt – rundum.“ Nur die Abflachung → „Anlegen“: Beide Operationen
haben „Flaechen“ = Face3, die Welle hat ihre Farben zurück; Doppelklick auf die Operation zeigt
Face3 wieder in der Liste.

### DONE
- Schritt 2 hat oben „Flächen“: Liste der gewählten mit Art und Erreichbarkeit in Grün, Gelb
  oder Rot, der Satz darunter, „Alle Mantelflächen“ und „Auswahl leeren“. Ein Klick auf eine
  Fläche des Teils im Job nimmt sie dazu oder heraus (in Schritt 2 lässt der Auswahlfilter nur
  das Teil im Job zu), Doppelklick in der Liste nimmt heraus. Die gewählten Flächen färbt die
  3D-Ansicht – nur die Anzeige, beim Schließen und in Schritt 1 wieder wie vorher.
- Alle Mantelflächen gewählt gilt wie keine: rundum (Manuel: „wenn ich alle anklicke, dann
  wird komplett rings um bearbeitet“). Vorschau, Anlegen und Ändern geben die Flächen und den
  Eintauchwinkel des Fräsers an die Operationen; beim Ändern stehen sie wieder in der Liste,
  auch wenn Schritt 1 fest ist.
- Hilfe de/en: Abschnitt „Schritt 2: Flächen“, „Was (noch) nicht geht“ nachgezogen.

### TEST
- KI mit unsichtbarer Oberfläche: `szenario_vierachs_flaechen` in FreeCAD 1.1.3 und im
  Wochen-Build grün (Klick, Liste, Farben in Liste und 3D, alle Mantelflächen, leeren,
  Anlegen mit Face3 in beiden Operationen, die Schruppbahn im Bereich, Farben zurück, Ändern
  und heraus → rundum); `szenario_vierachs_rohteil`, `_schruppen`, `_schlichten`, `_aendern`,
  `_maschine`, `szenario_rundum_drehmaschine` in 1.1.3 grün; `test_sprache`, `test_hilfe`
  grün.

### NEXT
- Manuel (2026-09-30, zum Bild der Bahn): „ich hoffe, dass die roten Striche keine Eilgänge
  sind, weil man kann ja auch einfach zurückdrehen für so eine Fläche“ – mit Bereich hin und
  her statt Spirale mit Eilgang rundum.

## P-2026-09-30-26 flaechen-bereich

### EINGELESEN
- `docs/spezifikation_vierachs.md` (V4-Plan, P-2026-09-30-25; Abschnitte 6 und 9),
  `camaddon/vierachs_huelle.py` (Netz, Raster, `_ausbreiten`, `_dreiecke_treffen`),
  `camaddon/vierachs_bahn.py` (`schruppen`, `schlichten`, `_spirale`, `_knicke`, `befehle`,
  `dauer`), `camaddon/vierachs_operation.py`, `camaddon/vierachs_schlichten.py`,
  `camaddon/restmaterial.py`, `camaddon/werkzeuge.py` (Eintauchwinkel).

### DATEIEN
- `camaddon/vierachs_flaechen.py` (neu), `camaddon/vierachs_bahn.py`,
  `camaddon/vierachs_operation.py`, `camaddon/vierachs_schlichten.py`,
  `translations/de.json`, `translations/en.json`, `tests/test_vierachs_flaechen.py` (neu),
  `tests/test_vierachs_bahn.py`, `tests/test_vierachs_schlichten.py`,
  `tests/test_vierachs_operation.py`, `docs/aufbau.md`, `docs/spezifikation_vierachs.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Eine „Rundum schruppen“ im Job, in ihren Eigenschaften „Flaechen“ nur die Abflachung einer
Welle („Face3“): Die Bahn fräst nur, wo der Fräser die Abflachung berührt, hebt dazwischen
über die Stange ab und taucht knapp über dem Rest wieder ein – die erste Umdrehung jeder Lage
über eine Rampe mit 5°, die anderen senkrecht. „Flaechen“ leer: rundum wie bisher.

### DONE
- `vierachs_flaechen`: das Teil Fläche für Fläche vernetzt; je Stelle a und Winkel φ die
  Fläche, die ein Strahl von außen zuerst trifft, dazu Ein- und Austritte je Fläche
  (`sicht`, gemerkt in `sicht_fuer`); `mantelflaechen`, `erreichbar` (ganz, zum Teil, nicht,
  quer zur Achse), `bereich` (wo die Stirn des Fräsers eine gewählte Fläche berührt),
  `bereich_fuer` mit den Sätzen, wenn eine Fläche fehlt oder keine erreichbar ist;
  `beschreibung` für die Liste im Assistenten. Strahlen, die eine Fläche nur streifen, zählen
  nicht; das Raster längs liegt eine Viertel Rasterweite neben runden Maßen.
- `vierachs_bahn`: mit Bereich schruppt jede Lage dieselbe Spirale nur in ihren Stücken im
  Bereich; hinein im Eilgang bis knapp über die Tiefe der Lage davor, dann senkrecht mit dem
  Eintauchvorschub, wo die Umdrehung davor schon fräste, sonst die Rampe mit dem
  Eintauchwinkel (hin und her, zurück auf der Bahn); Schlichten und seine Stufen nur im
  Bereich, hinein knapp über dem Rest. Eilgänge drehen höchstens 90° am Stück. `befehle` und
  `dauer` kennen den Eintauchvorschub.
- Beide Operationen haben „Flaechen“ (leer: rundum), „Rundum schruppen“ dazu
  „Eintauchwinkel“ (Vorschlag 5°); ältere Operationen bekommen sie beim Laden so, dass ihre
  Bahn bleibt. Der Eintauchvorschub kommt vom Controller.

### TEST
- KI ohne Oberfläche, FreeCAD 1.1.3: `test_vierachs_flaechen` (Welle mit Abflachung: Treffer,
  Mantel, Erreichbarkeit, Bereich; Welle mit Kragen: Innenseite nicht, Mantel darunter zur
  Hälfte erreichbar; Namen, Sätze, Beschreibung), `test_vierachs_bahn` (Rampe lang und kurz;
  nur die Abflachung: alles im Bereich, 2 Rampen, 24 senkrecht, darüber 0,45 mm, in den Ecken
  an den Wänden 1,12 mm, gegenüber unberührt; Eintauchvorschub in den Befehlen),
  `test_vierachs_schlichten` (nur die Abflachung: im Bereich, jedes Stück knapp über dem
  Rest und mit Eintauchvorschub), `test_vierachs_operation` (alte Operation, nur der Mantel,
  Fläche fehlt, nur eine Stirn), `test_sprache` grün.

### NEXT
- V4a im Assistenten: Flächen anklicken, Liste mit Erreichbarkeit, Farben in der 3D-Ansicht.

## P-2026-09-30-25 plan-v4-flaechen

### EINGELESEN
- `docs/spezifikation_vierachs.md` (Abschnitte 6 „Schritt 2: Flächen“, 9 „Rechenkern“, 12
  „Nicht Teil davon“, 13 V4 mit Manuels Antworten vom 2026-09-30).

### DATEIEN
- `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In `docs/spezifikation_vierachs.md` unter „V4 – Flächen wählen“ steht der Plan in fünf
Schritten (V4a Flächen im Assistenten, V4b Maske und sicheres Wiedereinsetzen, V4c
Strategien je Werkzeug, V4d Entgraten, V4e Prüfen und Szenario), jeder mit Manuels Satz,
auf den er antwortet.

### DONE
- Plan für V4 nach der Durchsicht 2 (Manuel: „Egal, du musst alles bauen“): Die gewählten
  Flächen sind die Maske in (a, φ), gerechnet wird weiter gegen das ganze Teil; abheben
  über das, was noch steht, und schräg mit dem Eintauchwinkel wieder hinein; Strategien
  Spirale, Linien längs und Plan indexiert; eigene Operation „Rundum entgraten“.
- Abschnitt 12: Ebene Abflachungen parallel zur Achse fräst V4c; Taschen und
  Querbohrungen bleiben eine spätere Stufe.

### TEST
- Reine Doku, kein Testlauf (`docs/arbeitsregeln.md`, Abschnitt 5).

### NEXT
- V4a: Flächen im Assistenten, Erreichbarkeit, die Operationen merken sich die Flächen.

## P-2026-09-30-24 version-0-29-1

### EINGELESEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`, `docs/durchsicht_bedienbarkeit.md`
  Abschnitt 7, die Einträge P-2026-09-30-19 bis -23.

### DATEIEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`, `docs/durchsicht_bedienbarkeit.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.29.1 an. Welle mit Absatz, „Rundum schruppen“ und
„Rundum schlichten“ auf der Beispiel-Drehmaschine → „Auf der Maschine prüfen“ → ans Ende:
überall grün, hinter dem Absatz nichts Rotes mehr.

### DONE
- Version 0.29.1 mit der Durchsicht 2: Ringgang vor jeder Wand, „T3 öffnen …“ im gelben
  Satz, Stationen am Revolver, Drehung 0, Längen-Texte.
- D-45 so gelassen (Empfehlung A) und so vermerkt.
- README (Ringgang) und Stand nachgezogen.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in FreeCAD 1.1.3 und im Wochen-Build – siehe
  Push-Nachricht.

### NEXT
- Push; danach W-003 V4 Flächen wählen (Manuels Antworten).

## P-2026-09-30-23 laenge-feldname

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md` D-40, `camaddon/reichweite.py` (`_Sammler.laenge`,
  `werkzeughalter`), `camaddon/gui_reichweite.py` (Urteil „Werkzeuglänge“),
  `tests/test_reichweite.py`, `tests/gui/szenario_abfahren.py`.

### DATEIEN
- `camaddon/reichweite.py`, `translations/de.json`, `translations/en.json`,
  `tests/test_reichweite.py`, `docs/durchsicht_bedienbarkeit.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Auf der Maschine prüfen“: Das Urteil „Werkzeuglänge“ lautet „Bei allen Werkzeugen
gemessen – aus der Werkzeugverwaltung.“; hat ein Werkzeug einen gewinkelten Halter und
keine gemessene Länge, nennt der Hinweis die „Länge ab Bezugspunkt“.

### DONE
- Das Urteil nennt keinen Feldnamen mehr – beim gewinkelten Halter heißt das Feld „Länge
  ab Bezugspunkt“ (P-2026-09-30-13), beim geraden „Länge ab Spindelnase“.
- Der Hinweis zur geschätzten Länge mit Halter nennt beim gewinkelten Halter „Länge ab
  Bezugspunkt“ und „Abgang des Halters“ (eigener Text).

### TEST
- KI ohne Oberfläche, FreeCAD 1.1.3: `test_reichweite` (T2 mit „VDI30 angetrieben radial“:
  der Hinweis nennt „Länge ab Bezugspunkt“), `test_sprache` grün.

### NEXT
- Version 0.29.1, voller Lauf, Push.

## P-2026-09-30-22 drehung-null

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md` D-47, `camaddon/gui_halter.py` (`_gewinkelt_text`),
  `camaddon/gui_zahlen.py` (`zahl_zeigen`: 0 heißt dort „unbekannt“),
  `tests/gui/szenario_halter_richtung.py`.

### DATEIEN
- `camaddon/gui_halter.py`, `tests/gui/szenario_halter_richtung.py`,
  `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Halter …“ → „Neu ▼“ → „VDI30 angetrieben radial · ER16“: Bei
Drehung steht „0“, nicht ein leeres Feld.

### DONE
- Winkel und Drehung zeigen jede Zahl, auch 0 – 0° ist ein Winkel, kein „nichts
  eingetragen“ (`zahl_zeigen` lässt 0 leer, weil es dort „unbekannt“ heißt).

### TEST
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_halter_richtung` (Drehung „0“)
  grün.

### NEXT
- D-40 Längen-Texte; danach voller Lauf und Push.

## P-2026-09-30-21 revolver-stationen

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md` D-46 (und D-01 … D-08: P-2026-09-27-07, Revolver
  sichtbar), `camaddon/beispielmaschine.py` (`drehmaschine`, die Stationen bis 0.28),
  Screenshots `szenario_beispielmaschine/8_alle_beispielmaschinen`,
  `szenario_neue_maschine/5_gebaut_bearbeiten`.

### DATEIEN
- `camaddon/beispielmaschine.py`, `help/de/neue_maschine.html`, `help/en/neue_maschine.html`,
  `tests/test_beispielmaschine.py`, `docs/durchsicht_bedienbarkeit.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Neue Maschine …“ → Drehmaschine: Rund um die Revolverscheibe steht je Platz eine
Station – wie bis 0.28 –, an der Stirn zum Futter hin die Aufnahmen.

### DONE
- Seit 0.29 (P-2026-09-30-15) sitzen die Aufnahmen als Ringe an der Stirn; die Stationen
  am Umfang, die den Revolver kenntlich machten (P-2026-09-27-07, auf Manuels Hinweis),
  waren mit den festen Haltern verschwunden. Jetzt wieder je Platz eine Station – auch
  P1, wo bis 0.28 der radiale Halter saß.
- Hilfe „Neue Maschine“ de/en; Test.

### TEST
- KI ohne Oberfläche, FreeCAD 1.1.3: `test_beispielmaschine` (Station01 … Station12),
  `test_vierachs_pruefen`, `test_kollision`, `test_reichweite` grün.
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_beispielmaschine`,
  `szenario_neue_maschine`, `szenario_rundum_drehmaschine` (Kollision frei) grün;
  Screenshot der Übersicht angesehen – der Revolver ist wieder zu erkennen.

### NEXT
- D-47: Drehung 0 im Fenster „Halter“.

## P-2026-09-30-20 ringgang-an-waenden

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md` D-42, `docs/spezifikation_vierachs.md` (V5e, der
  Fund hinter dem Absatz), `camaddon/vierachs_bahn.py` (`schruppen`, `schlichten`,
  `_knicke`, `_zusammengefasst`, `_spirale`), `camaddon/vierachs_huelle.py` (`je_winkel`,
  `schaftfraeser`, `Huelle.bei`, `sicher`), `camaddon/vierachs_operation.py`,
  `camaddon/vierachs_schlichten.py`, `help/*/vierachs.html`.

### DATEIEN
- `camaddon/vierachs_bahn.py`, `camaddon/vierachs_operation.py`,
  `camaddon/vierachs_schlichten.py`, `help/de/vierachs.html`, `help/en/vierachs.html`,
  `tests/test_vierachs_bahn.py`, `tests/test_vierachs_schlichten.py`,
  `tests/test_vierachs_operation.py`, `tests/gui/szenario_rundum_drehmaschine.py`,
  `docs/spezifikation_vierachs.md`, `docs/durchsicht_bedienbarkeit.md`, `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit Absatz (Wand zum Futter hin), „Rundum schruppen“ und „Rundum schlichten“ auf der
Beispiel-Drehmaschine → „Auf der Maschine prüfen“ → ans Ende: Hinter dem Absatz bleibt nur
die Kehle des Kugelfräsers, nicht mehr bis 6,4 mm.

### DONE
- `vierachs_operation.waende()`: ebene Flächen quer zur Stangenachse zwischen den Enden
  des Teils (Absätze, Flanken von Nuten), mit der Seite, zu der sie schauen.
- Vor jeder Wand hält die Spirale eine Umdrehung an (Ringgang): beim Schruppen in jeder
  Lage, beim Schlichten auch in den Stufen. Der Ring steht Fräserradius + Aufmaß +
  Vernetzung + 0,01 mm vor der Wand, damit der um Aufmaß und Vernetzung größere Fräser sie
  nicht streift; die Hüllfläche genau an seiner Stelle (beim Schruppen eine eigene Zeile –
  das Raster nähme den höheren Nachbarn, und der liegt schon an der Wand). Danach läuft die
  Spirale eine Umdrehung später weiter; das Ausdünnen der Punkte behält Anfang und Ende
  jedes Rings (dort knickt a).
- Die Operationen rechnen die Wände aus der Form des Teils, die Vorschau im Assistenten
  auch; Hilfe de/en, Spezifikation, Durchsicht (D-42 erledigt), `aufbau.md`.

### TEST
- KI ohne Oberfläche, FreeCAD 1.1.3: `test_vierachs_bahn` (Welle mit Absatz, Ø 12,
  4,8 mm: ohne Ring hinter der Wand über 3 mm stehen, mit Ring höchstens das Aufmaß; je Lage
  ein ganzer Umlauf), `test_vierachs_schlichten` (Kugel Ø 6, 2 mm: an der Wand ohne Ring
  über 3 mm, mit Ring die Kehle ≤ 1,5 mm; nirgends im Teil), `test_vierachs_operation`
  (Wände von Zylinder, Absatz, Nut), `test_restmaterial` grün.
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_rundum_drehmaschine` grün.

### NEXT
- D-40 Längen-Texte, D-43 Meldung beim Kugelfräser.

## P-2026-09-30-19 durchsicht-2-und-verweis

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md` (Durchsicht 1, D-01 … D-30), die Screenshots und Logs
  des vollen Laufs zu 0.29.0, `camaddon/gui_vierachs.py` (gelber Satz, Werkzeugverwaltung),
  `camaddon/gui_reichweite.py` und `camaddon/gui_kollision.py` (Verweis „T1 öffnen …“, D-11).

### DATEIEN
- `docs/durchsicht_bedienbarkeit.md`, `camaddon/gui_vierachs.py`, `translations/de.json`,
  `translations/en.json`, `tests/gui/szenario_rundum_drehmaschine.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine, „4-Achs-Bearbeitung“ → Schritt 2 → als Fräser einer ohne Halter:
Im gelben Satz steht am Ende „T3 öffnen …“; ein Klick öffnet die Werkzeugverwaltung bei
T3. Halter „VDI30 angetrieben radial“ wählen, OK – der gelbe Satz ist weg.

### DONE
- Durchsicht 2 (Manuel 2026-09-30: „alles nochmal auf Bedienbarkeit überprüfen und ob
  alles logisch ist“) als Abschnitt 7 in `durchsicht_bedienbarkeit.md`: D-40 bis D-47 mit
  Heute, Vorschlag, Fertig-wenn; D-44 schon erledigt (P-2026-09-30-17).
- D-43 untersucht: Die Meldung „gp_Circ::SetRadius“ beim Kugelfräser kommt aus FreeCAD
  (Vorlage „ballend“, Maße nacheinander gesetzt, bei Werkzeugen unter 40 mm kurz eine
  ungültige Skizze); das fertige Werkzeug ist richtig – kein Handlungsbedarf im Addon.
- D-41: Der gelbe Satz im Assistenten endet mit dem Verweis „T3 öffnen …“ wie die Hinweise
  im Prüffenster (D-11); die Werkzeugverwaltung öffnet bei dem Werkzeug, Speichern liest
  der Assistent neu. Der Satz nennt den Knopf oben nicht mehr.

### TEST
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_rundum_drehmaschine` (Verweis,
  Werkzeugverwaltung bei T3, Halter, OK → gelb weg) grün; `test_sprache` grün.

### NEXT
- D-42 Ringgang, D-40 Längen-Texte, D-43 Meldung beim Kugelfräser.

## P-2026-09-30-18 version-0-29-0

### EINGELESEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`, die Einträge P-2026-09-30-10
  bis -17.

### DATEIEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.29.0 an. Danach: Werkzeugverwaltung → „Halter …“ →
„Neu ▼“ → „VDI30 angetrieben radial“ – Richtung „gewinkelt“, das Bild zeigt den Knick;
„Neue Maschine …“ → Drehmaschine – an der Revolverscheibe Aufnahmen, keine festen
Halter; „4-Achs-Bearbeitung“ mit T1 im radialen Halter – kein gelber Satz, die
Ausspannlänge nennt „Halter über die Werkzeugachse 27,5“.

### DONE
- Version 0.29.0: die Richtung des Werkzeugs am Halter (W-002 Stufe E: gerade,
  angetrieben radial, Winkelkopf), der Halterkopf vor dem Futter, die
  Beispiel-Drehmaschine mit Aufnahmen, der gelbe Satz im 4-Achs-Assistenten, keine
  versteckten Ausnahmen mehr beim Öffnen des Assistenten.
- README (Halter, Drehmaschine, gelber Satz) und Stand nachgezogen.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in FreeCAD 1.1.3 und im Wochen-Build – siehe
  Push-Nachricht.

### NEXT
- Push; Bericht an Manuel mit Klickweg und Screenshots; danach Durchsicht
  Bedienbarkeit und Logik.

## P-2026-09-30-17 keine-versteckten-ausnahmen

### EINGELESEN
- `tests/gui/_lauf/szenario_lauf.py`, `camaddon/gui_vierachs.py` (Schritt 2, `haken`),
  `camaddon/gui_teile.py` (`_RadNurMitFokus`), die `freecad.log` der Szenarien des
  letzten Volllaufs, `docs/arbeitsregeln.md` Abschnitt 5.

### DATEIEN
- `tests/gui/_lauf/szenario_lauf.py`, `camaddon/gui_vierachs.py`, `camaddon/gui_teile.py`,
  `docs/arbeitsregeln.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„4-Achs-Bearbeitung“ öffnen: Im Report-Fenster steht kein Traceback mehr („'VierachsPanel'
object has no attribute 'schruppfelder'“). Ein Szenario, in dem eine Oberfläche eine
Ausnahme wirft, scheitert.

### DONE
- Gefunden in den Logs der Szenarien: Jedes Öffnen des 4-Achs-Assistenten druckte einen
  Traceback – der Haken „Rundum schruppen“ wurde gesetzt, nachdem sein Slot verbunden
  war, und der Slot fand die Felder dazu noch nicht. Jetzt setzt `haken(…, an=True)` ihn
  vor dem Verbinden. Dazu einmal im Szenario „Mausrad“: Beim Schließen eines Fensters
  war der Rollbalken schon weg („already deleted“) – der Filter nimmt das Rad dann
  trotzdem, das Feld bekommt es nicht.
- Der Szenario-Lauf zählt eine Ausnahme in der Oberfläche (sys.excepthook – etwa in
  einem Slot) als Fehler; bisher ging das Szenario durch, FreeCAD druckte sie nur.
  Geprüft in 1.1.3 und im Wochen-Build mit einem Probe-Szenario, das in einem Slot eine
  Ausnahme wirft. Arbeitsregeln ergänzt.

### TEST
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_vierachs_*`, `szenario_mausrad`,
  `szenario_halter*` grün, ohne Traceback im Log. Gegenprobe: mit dem alten Haken
  scheitert `szenario_vierachs_maschine` jetzt an der Ausnahme.

### NEXT
- Voller Lauf, Version 0.29.0, Push.

## P-2026-09-30-16 assistent-halter-hinweis

### EINGELESEN
- `docs/spezifikation_halter.md` Abschnitt 11.3/11.5 (E5), `camaddon/reichweite.py`
  (`_pruefe_operation`, `_werkzeug_aus`, `werkzeugaufnahme`), `camaddon/gui_vierachs.py`
  (Schritt 2, Maschinenwahl, Vorschau), `help/*/vierachs.html`.

### DATEIEN
- `camaddon/reichweite.py`, `camaddon/gui_vierachs.py`, `translations/de.json`,
  `translations/en.json`, `help/de/vierachs.html`, `help/en/vierachs.html`,
  `tests/test_reichweite.py`, `tests/gui/szenario_rundum_drehmaschine.py`,
  `docs/spezifikation_halter.md`, `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine offen, „4-Achs-Bearbeitung“ → Schritt 2: T1 mit „VDI30
angetrieben radial“ – kein gelber Satz; T3 ohne Halter als Fräser – gelb darunter
„T3 sitzt auf P3 nicht radial – die Bahn braucht es radial aus +X zur Achse. Gib T3
in der Werkzeugverwaltung (Knopf oben) einen Halter, der radial steht, etwa „VDI30
angetrieben radial“.“; zurück auf T1 – weg. „Anlegen“ bleibt frei.

### DONE
- `Pruefung.kommt_aus(nummer, richtung, einspannung)`: Platz der Nummer, Revolver in
  Arbeitsstellung, Achse des Werkzeugs mit der Lage aus seinem Halter – dieselbe
  Rechnung wie der Hinweis „nicht radial“ beim Prüfen, ohne Bahn.
- Assistent, Schritt 2: unter „Rundum schruppen“ und „Rundum schlichten“ je ein
  gelber Satz, sobald eine offene Maschine gewählt ist und der Fräser dort nicht
  radial säße (oder die Nummer keinen Platz hat). Er sperrt nichts. Die Prüfung der
  Maschine wird einmal je Maschine gebaut. Nach dem Speichern in der
  Werkzeugverwaltung liest der Assistent sie neu – der Satz geht weg.
- Hilfe de/en, Spezifikation (E5 gebaut), `aufbau.md`.

### TEST
- KI ohne Oberfläche, FreeCAD 1.1.3: `test_reichweite` (T2 gerade → nicht aus +X,
  mit radialem Halter → aus +X, T13 → kein Platz), `test_sprache`, `test_hilfe` grün.
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_rundum_drehmaschine`
  (T3 ohne Halter → gelb, zurück auf T1 → weg) grün; Screenshot angesehen. Ob der
  Satz verständlich ist, prüft Manuel.

### NEXT
- Traceback beim Öffnen des Assistenten („schruppfelder“) beheben; Durchsicht
  Bedienbarkeit und Logik.

## P-2026-09-30-15 beispiel-drehmaschine-aufnahmen

### EINGELESEN
- `docs/spezifikation_halter.md` Abschnitt 11.4/11.5 (E4), `camaddon/beispielmaschine.py`
  (`drehmaschine`, `DrehmaschinenMasse`), `tests/test_beispielmaschine.py`,
  `tests/test_reichweite.py`, `tests/test_schraege_achse.py`,
  `tests/test_vierachs_pruefen.py`, `tests/gui/szenario_vierachs_schruppen.py`,
  `tests/gui/szenario_vierachs_schlichten.py`, `help/*/achsen.html`,
  `help/*/neue_maschine.html`.

### DATEIEN
- `camaddon/beispielmaschine.py`, `translations/de.json`, `translations/en.json`,
  `help/de/achsen.html`, `help/en/achsen.html`, `help/de/neue_maschine.html`,
  `help/en/neue_maschine.html`, `tests/test_beispielmaschine.py`,
  `tests/test_reichweite.py`, `tests/test_schraege_achse.py`,
  `tests/test_vierachs_pruefen.py`, `tests/gui/szenario_vierachs_schruppen.py`,
  `tests/gui/szenario_rundum_drehmaschine.py` (neu), `docs/spezifikation_halter.md`,
  `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Neue Maschine …“ → Drehmaschine: An der Stirn der Revolverscheibe sitzen zwölf
Aufnahmen (Ringe), keine Halter. T1 Schaftfräser Ø 12 und T2 Kugelfräser Ø 6, beide
mit „VDI30 angetrieben radial“: Welle mit Absatz, „4-Achs-Bearbeitung“ mit „Rundum
schruppen“ T1 und „Rundum schlichten“ T2 → „Auf der Maschine prüfen“: alle Achsen
in ihren Grenzen, kein Hinweis „nicht radial“; T1 und T2 stehen beim Abspielen
radial am Teil; am Ende nirgends ins Teil; „Kollision prüfen“ meldet nichts. Ohne
Halter bei T2 nennt der Hinweis T2, P2 und den Halter, der fehlt.

### DONE
- Beispiel-Drehmaschine: Der Revolver trägt keine Halter mehr fest (bisher P1
  radial, P2 axial). Jeder Platz ist eine VDI30-Aufnahme an der Stirn der Scheibe
  (Ring, 130 mm von der Revolverachse, x = 700), alle am Werkzeugantrieb S3; das
  LCS von P1: Z längs der Revolverachse vom Futter weg, X zur Spindelachse. Wie
  ein Werkzeug steht, sagt sein Halter (W-002 Stufe E). Weg X bis −300: Die
  Aufnahme in Arbeitsstellung steht 275 mm von der Spindelachse, ein radiales
  Werkzeug erreicht so jeden Radius. Beschreibung, Docstrings, Hilfe
  (Achsen, Neue Maschine) de/en.
- Tests auf die neue Maschine: Plätze und Antrieb, kein fester Halter; „quer“ erst
  mit radialem Halter; X-Bereich der schrägen Achse; Prüfen, Abfahren und
  Kollision mit T1 im radialen Halter (125 mm ab Bezugspunkt, Stange 40 mm frei
  hinten – der Kopf hat Platz; mit 50 mm stößt der Halter ans Teil).
- Szenario „Rundum schruppen“: T1 mit dem radialen Halter, die Stange ragt
  140 mm heraus (Halter über die Werkzeugachse 27,5).
- Neues Szenario `szenario_rundum_drehmaschine`: Schruppen T1 + Schlichten T2
  auf der Beispiel-Drehmaschine (der offene Klickweg von W-003 V5e) – Prüfen,
  Abspielen, Kollision, Farben; T2 ohne Halter → der Hinweis.
- Gefunden (für später, Aufgabe „Ringgang an Absätzen“): Hinter dem Absatz der
  Welle (Wand zum Futter hin) bleiben bei manchen Winkeln bis 6,4 mm stehen – die
  Spirale des Kugelfräsers (1 mm je Umdrehung) liegt dort 2,5 mm (über die Kante
  gehoben) und 3,5 mm (erreicht die Wand nicht) von der Wand, nur auf dem halben
  Umfang genau 3. Das Prüffenster zeigt es richtig rot („dort kam der Fräser nicht
  hin“), nichts geht ins Teil. Beim Schruppen genauso (Ø 12, 4,8 mm: bis 7,3 mm).

### TEST
- KI ohne Oberfläche, FreeCAD 1.1.3: `test_beispielmaschine`, `test_reichweite`,
  `test_schraege_achse`, `test_vierachs_pruefen` grün.
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_vierachs_schruppen`
  und `szenario_rundum_drehmaschine` grün; Screenshots angesehen.

### NEXT
- E5: Der Assistent sagt schon bei der Wahl des Fräsers, wenn er auf der
  gewählten Maschine nicht radial säße.

## P-2026-09-30-14 halter-vor-dem-futter

### EINGELESEN
- `docs/spezifikation_halter.md` Abschnitt 11, `docs/spezifikation_vierachs.md`
  (V3f Abstände, Ausspannlänge), `camaddon/halter.py`, `camaddon/vierachs_bahn.py`
  (`schruppen`, `schlichten`), `camaddon/vierachs_operation.py`,
  `camaddon/vierachs_schlichten.py`, `camaddon/gui_vierachs.py` (Vorschau,
  `_bedarf_hinten`, `_ausspannen_text`, Anlegen, Ändern), `help/*/vierachs.html`.

### DATEIEN
- `camaddon/halter.py`, `camaddon/vierachs_bahn.py`, `camaddon/vierachs_operation.py`,
  `camaddon/vierachs_schlichten.py`, `camaddon/gui_vierachs.py`,
  `translations/de.json`, `translations/en.json`, `help/de/vierachs.html`,
  `help/en/vierachs.html`, `tests/test_halter.py`, `tests/test_vierachs_bahn.py`,
  `tests/test_vierachs_operation.py`, `docs/spezifikation_halter.md`,
  `docs/spezifikation_vierachs.md`, `docs/aufbau.md`, `README.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
T1 Ø 12 mit „VDI30 angetrieben radial“ in der Werkzeugverwaltung,
„4-Achs-Bearbeitung“ → Schritt 2: grau „Die Stange muss … aus dem Futter ragen:
… + Überlauf 6,5 + Halter über die Werkzeugachse 27,5 + Abstand zum Futter 5,0.“
Der Kopf des Halters bleibt 5 mm vor dem Futter – auch, wenn die Stange kürzer
ausgespannt ist: Dann endet die Bahn früher. Ohne Halter wie bisher.

### DONE
- Gefunden beim Umbau der Beispiel-Drehmaschine (E4): Ausspannlänge und Bahn
  rechneten zum Futter hin nur mit dem Fräserradius; der Kopf des radialen
  Halters reicht 27,5 mm über die Werkzeugachse und stieß ans Futter.
- `halter.seitlich()`: der halbe größte Ø, beim gewinkelten auch der Kopf.
- `Schruppwerte.halter` / `Schlichtwerte.halter`: Die Bahn endet, wo der Rand,
  der weiter reicht, den Abstand zum Futter hat; eigener Fehler „kein Platz für
  den Halter“.
- Eigenschaft „HalterZumFutter“ an beiden Rundum-Operationen – ältere bekommen
  0, ihre Bahn bleibt; `lege_an`/`aendere` nehmen sie, der Assistent trägt sie
  aus der Werkzeugverwaltung ein (Anlegen, Ändern, Schlichten dazu) und rechnet
  die Vorschau damit.
- Ausspannlänge: Überlauf + größeres von Fräserradius und Halter + Abstand; der
  Satz nennt dann „Halter über die Werkzeugachse 27,5“.
- Tooltips „Abstand zum Futter“, Hilfe de/en, Spezifikation (Stufe E3a,
  Nachtrag V3f), `aufbau.md` (auch die Zeile `halter.py` mit Stufe E), README.

### TEST
- KI ohne Oberfläche, FreeCAD 1.1.3: `test_halter`, `test_vierachs_bahn` (Halter
  27,5: Ende bei −68, 26 mm frei; schmaler Halter ändert nichts; kein Platz →
  der Satz zum Halter), `test_vierachs_operation` (alte Operation → 0; 27,5 →
  Ende bei −85), `test_vierachs_schlichten_op`, `test_vierachs_schlichten`,
  `test_restmaterial`, `test_vierachs_pruefen`, `test_vierachs_rohteil`,
  `test_hilfe`, `test_sprache` grün.
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: die fünf 4-Achs-Szenarien grün
  (noch ohne Halter – mit Halter zeigt es E4).

### NEXT
- E4: Beispiel-Drehmaschine mit Aufnahmen; das Szenario Schruppen bekommt T1 mit
  dem radialen Halter.

## P-2026-09-30-13 halter-richtung-fenster

### EINGELESEN
- `docs/spezifikation_halter.md` Abschnitt 11 (E2), `camaddon/gui_halter.py`
  (Fenster, Bild), `camaddon/gui_werkzeuge.py` (Längenzeile),
  `tests/gui/szenario_halter.py`, `help/*/halter.html`.

### DATEIEN
- `camaddon/gui_halter.py`, `camaddon/gui_werkzeuge.py`, `translations/de.json`,
  `translations/en.json`, `help/de/halter.html`, `help/en/halter.html`,
  `tests/gui/szenario_halter_richtung.py` (neu), `docs/spezifikation_halter.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Halter …“ → „Neu“ → „VDI30 angetrieben radial · ER16“:
Richtung „gewinkelt“, Winkel 90, Versatz 55, Kopf-Ø 55, das Bild zeigt Kopf und
Knick; Winkel 45 kippt das Bild; „gerade“ blendet die Felder aus; OK → beim
Werkzeug steht „Länge ab Bezugspunkt“, grau „leer: 92 mit Halter“.

### DONE
- Fenster „Halter“: Zeile „Richtung“ und, nur beim gewinkelten, Winkel,
  Drehung (auch negativ), Versatz, Kopf-Ø; die Überschrift der Kontur und die
  Zusammenfassung sagen, wovon aus gemessen wird.
- Das Bild rechnet in Maßen (quer, Tiefe) und passt ein: Kopf, Knick, Abgang und
  Werkzeug in der Ebene des Knicks; gerade wie bisher.
- Werkzeugverwaltung: „Länge ab Bezugspunkt“ mit eigenem Tooltip beim
  gewinkelten Halter.
- Hilfe de/en: Richtung, Bezugspunkt, neue Vorlagen, Grenzen.

### TEST
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_halter_richtung`
  (neu) und `szenario_halter` grün; Screenshots angesehen (`1_vdi30_radial`,
  `2_winkel_45`, `3_gerade`, `4_werkzeug`). `test_hilfe`, `test_sprache` grün. Ob
  das Fenster ohne Erklärung verständlich ist, prüft Manuel.

### NEXT
- E4: Beispiel-Drehmaschine mit Aufnahmen statt fester Halter.

## P-2026-09-30-12 halter-richtung-rechnung

### EINGELESEN
- `docs/spezifikation_halter.md` Abschnitt 11 (E3), `camaddon/reichweite.py`
  (`_spitze`, `_werkzeug_aus`, `_werkzeug_quer`, `_pruefe_operation`),
  `camaddon/kinematik.py`, `camaddon/abfahren.py`, `camaddon/kollision.py`
  (`werkzeugkoerper`), `camaddon/gui_abfahren.py`.

### DATEIEN
- `camaddon/reichweite.py`, `camaddon/abfahren.py`, `camaddon/kollision.py`,
  `translations/de.json`, `translations/en.json`, `tests/test_reichweite.py`,
  `tests/test_kollision.py`, `docs/spezifikation_halter.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Werkzeug mit „VDI30 angetrieben radial“ auf dem axialen P2 der
Beispiel-Drehmaschine steht quer zu Z (Hinweis „längs Z gerechnet“), seine
Spitze trifft den Bahnpunkt genau; Schneide, Schaft und Halter liegen gekippt,
40 mm bzw. 80 mm ab Bezugspunkt längs der Werkzeugachse.

### DONE
- `reichweite.Einspannung` und `einspannung(tc, bibliothek)`: Länge ab
  Bezugspunkt und Lage aus dem Halter; `_spitze`, `_werkzeug_aus`,
  `_werkzeug_quer` rechnen mit der Achse des Werkzeugs; `loeser` und
  `Kinematik` bekommen die Einspannung (eine Zahl bleibt gerade).
- `abfahren`: `OperationAbfahrt.lage` und `.einspannung`.
- `kollision.werkzeugkoerper`: Schneide, Kern, Hals und Schaft gekippt, der
  Halter mit Kopf – so auch das Bild im Prüffenster.
- Hinweise „radial“ und „quer“ nennen den Halter, der fehlt bzw. passt.

### TEST
- FreeCAD 1.1.3: `test_reichweite` (P2 mit radialem Halter quer, Spitze auf dem
  Bahnpunkt, Hinweis mit der Bibliothek), `test_kollision` (Körper gekippt),
  `test_abfahren`, `test_vierachs_pruefen` grün.

### NEXT
- E2: Fenster „Halter“ mit Richtung und Bild; E4 Beispielmaschinen.

## P-2026-09-30-11 halter-richtung-datenmodell

### EINGELESEN
- `docs/spezifikation_halter.md` Abschnitt 11 (Stufe E, E1), `camaddon/halter.py`,
  `camaddon/werkzeuge.py` (Bibliothek, `laenge_mit_halter`), `tests/test_halter.py`.

### DATEIEN
- `camaddon/halter.py`, `translations/de.json`, `translations/en.json`,
  `tests/test_halter.py`, `docs/spezifikation_halter.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`halter.aus_vorlage("vdi30_radial")` ist gewinkelt (90°, Versatz 55 mm, Kopf
Ø 55); `halter.lage()` legt die Spitze 100 mm ab Bezugspunkt nach (100, 0, −55)
im LCS der Aufnahme; ein gerader Halter und kein Halter ergeben die Lage der
Aufnahme; alte Dateien ohne Richtung lesen sich als gerade.

### DONE
- `Halter`: `richtung`, `winkel`, `drehung`, `versatz`, `kopf_d`, gespeichert und
  gelesen (Unlesbares: Standard, Winkel 0 … 180°).
- `lage(halter)`: Bezugspunkt und Achse des Werkzeugs im LCS der Aufnahme – die
  eine Stelle für Stufe E.
- `form(halter)`: beim gewinkelten Kopf und Abgang (Abschnitte längs der
  Werkzeugachse).
- Vorlagen „VDI30 angetrieben radial · ER16“, „VDI30 angetrieben axial · ER16“,
  „Winkelkopf 90° · SK40“ (de/en).

### TEST
- FreeCAD 1.1.3: `test_halter` (Richtung, Lage, Körper, Länge ab Bezugspunkt,
  Speichern, alte und unlesbare Angaben), `test_sprache` grün.

### NEXT
- E3: Reichweite, Spitze, Abfahren, Kollision und Bild mit der Lage des Halters.

## P-2026-09-30-10 spezifikation-halter-richtung

### EINGELESEN
- Manuels Antworten vom 2026-09-30: „Die Plätze müssen mit den Werkzeugen
  beladen werden, die dafür geeignet sind … ein Parameter, wie die
  Werkzeug-Z-Achse zur Maschinen-Haupt-Z-Achse steht … ein Winkelkopf … kann in
  alle Richtungen stehen“; Richtung „Am Halter“; Reihenfolge: erst die
  Grundvoraussetzungen (Halter, Beispielmaschinen, Durchsicht), dann weiter;
  zur Flächenwahl: abheben und sicher wieder einsetzen, mehrere Strategien je
  nach Werkzeug, Entgraten.
- `docs/spezifikation_halter.md`, `docs/spezifikation_vierachs.md` (V4),
  `camaddon/halter.py`, `camaddon/maschine.py` (Aufnahmen, Revolverplätze),
  `camaddon/beispielmaschine.py` (Drehmaschine).

### DATEIEN
- `docs/spezifikation_halter.md`, `docs/spezifikation_vierachs.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation beschreibt, wie der Halter die Richtung des Werkzeugs
bestimmt (gerade, gewinkelt: Winkel, Drehung, Versatz, Kopf), wie die Lage
gerechnet wird, was sich an Fenster, Prüffenster, Assistent und
Beispielmaschinen ändert, in Schritten E1–E5; V4 trägt Manuels Antworten.

### DONE
- `spezifikation_halter.md` Abschnitt 11 „Stufe E: Richtung des Werkzeugs am
  Halter“ mit Manuels Entscheidungen und Claudes Vorschlag zu den
  Einzelheiten.
- `spezifikation_vierachs.md` V4: Manuels Wunsch und Antworten zur Flächenwahl.

### TEST
- Nur Dokumentation.

### NEXT
- E1: Datenmodell, Speicherung, Vorlagen, Lage des Werkzeugs.

## P-2026-09-30-09 version-0-28-0

### EINGELESEN
- P-2026-09-30-01 bis -08 (V5 „Rundum schlichten“), `package.xml`, `README.md`,
  `docs/STATUS_SNAPSHOT.md`; Manuels Antworten vom 2026-09-30 (Richtung am
  Halter; erst die Grundvoraussetzungen, dann Flächen wählen).

### DATEIEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.28.0 an; im Assistenten steht „Rundum
schlichten“, im Job danach „Rundum schlichten T2“.

### DONE
- Version 0.28.0: Rundum schlichten mit jeder Fräserform, Stufen in engen
  Stellen, Abtrag und Schneide mit der Form in Simulation und Kollision.
- README (4-Achs-Absatz) und Stand (W-003, nächste Schritte nach Manuel)
  nachgezogen.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build vor dem Push.

### NEXT
- Richtung des Werkzeugs am Halter (Spezifikation mit Manuel), Beispielmaschinen,
  Durchsicht Bedienbarkeit; dann V4 Flächen wählen.

## P-2026-09-30-08 schneide-als-drehkoerper

### EINGELESEN
- V5e in `docs/spezifikation_vierachs.md` (Abfahren und Kollision nehmen die
  Schneide als Drehkörper aus der Form – sonst stieße ein Kugelfräser in der
  Kehle „ins fertige Teil“).
- `camaddon/kollision.py` (`werkzeugkoerper`, KERN), `camaddon/reichweite.py`
  (`Werkzeugmasse`, `werkzeugmasse`), `camaddon/gui_abfahren.py` (Bild),
  `camaddon/fraeserform.py`, `tests/test_kollision.py`.

### DATEIEN
- `camaddon/kollision.py`, `camaddon/reichweite.py`, `tests/test_kollision.py`,
  `help/de/reichweite.html`, `help/en/reichweite.html`,
  `docs/spezifikation_vierachs.md`, `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Auf der Maschine prüfen“ mit einem Kugelfräser: Im Bild ist die Schneide eine
Halbkugel mit Zylinder darüber; „Kollision prüfen“ meldet nichts, wo die Kugel
das Teil nur berührt (etwa über eine Kante gerollt), aber „fährt ins fertige
Teil“, wo sie mehr als 0,05 mm hineinkommt.

### DONE
- `Werkzeugmasse.stirn`: die Form der Stirn aus der Werkzeugverwaltung
  (`fraeserform.von_werkzeug`), sonst aus dem ToolBit (`_stirn_vom_bit`).
- `werkzeugkoerper`: Schneide als Drehkörper (`drehkoerper`: Bögen und Geraden
  der Stirn um Z, darüber zylindrisch bis zur Schneidenlänge; was höher reicht,
  schneidet es ab); eben weiter der Zylinder, der Lollipop die Kugel. Der Kern
  (`_kern`): beim Kugelfräser die Kugel um 0,05 mm kleiner, sonst die höchsten
  Kreise mit 0,05 mm über der Stirn als Geraden, bis 1 µm zusammengefasst.
- Gefunden beim Bauen: Ein Kern aus Sehnen war beim Radienfräser (hohle Kehle)
  größer als erlaubt, und eine fast flache Kegelfläche drehte ihn für OpenCascade
  um (Punkte außen galten als innen) – jetzt bleibt jede Stelle höchstens 1 µm von
  der Sehne, und die Stelle selbst zählt genau.
- Gefunden: An der Beispiel-Drehmaschine sitzt T2 auf P2 (axial) – Schruppen mit
  T1 und Schlichten mit T2 meldet dort „nicht radial“ und Berührungen mit der
  Spindel. Das ist richtig, aber für den Klickweg von V5 braucht die
  Beispiel-Drehmaschine einen zweiten radialen Platz: Entscheidung für Manuel.
- Hilfe de/en: die Schneide in ihrer Form.

### TEST
- FreeCAD 1.1.3: `test_kollision` (Kugelfräser Ø 5: Volumen Halbkugel + Zylinder;
  sechs Formen gültig, Kern darin und 0,048 … 0,050 mm innen; Kugel über die
  Taschenkante: kein Befund, 0,5 mm tiefer „ins fertige Teil“),
  `test_abfahren`, `test_reichweite`, `test_vierachs_pruefen`, `test_halter`,
  `test_hilfe` grün; `szenario_kollision` grün.
- Job mit Schruppen und Schlichten auf der Beispiel-Drehmaschine: Kollision 43 s,
  77 193 Stellen – wie vorher.

### NEXT
- Beispiel-Drehmaschine: zweiter radialer Platz (Manuel entscheidet), dann das
  Szenario zu V5e (Schruppen und Schlichten prüfen, Farben, Kollision).

## P-2026-09-30-07 abtrag-mit-fraeserform

### EINGELESEN
- V5e in `docs/spezifikation_vierachs.md` (Abtrag und Farben auch für „Rundum
  schlichten“, mit der Form des Fräsers; verglichen mit dem Aufmaß der letzten
  Bearbeitung).
- `camaddon/restmaterial.py`, `camaddon/gui_abfahren.py` (Bild, Satz),
  `camaddon/fraeserform.py`, `camaddon/vierachs_schlichten.py` (`rest_nach`),
  `tests/test_restmaterial.py`, `tests/gui/szenario_vierachs_schruppen.py`.

### DATEIEN
- `camaddon/restmaterial.py`, `camaddon/vierachs_schlichten.py`,
  `tests/test_restmaterial.py`, `help/de/reichweite.html`,
  `help/en/reichweite.html`, `docs/spezifikation_vierachs.md`,
  `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit „Rundum schruppen“ (Schaftfräser) und „Rundum schlichten“
(Kugelfräser) → „Auf der Maschine prüfen“ → bis zum Ende abspielen: Die Stange
wird mit beiden Fräsern abgetragen; am Ende grün, wo geschlichtet ist
(verglichen mit Aufmaß 0 des Schlichtens), rot nur die Rundung der Kugel in
einer Innenecke, nirgends blau.

### DONE
- `Stange` trägt mit der Form des Fräsers ab (`fraeserform.Form`; eine Zahl ist
  weiter der Radius eines Schaftfräsers): Der Strahl aus der Achse trifft die
  Stirn, wo ρ · cos Δ = r + z(ℓ). Schaftfräser und Kugel geschlossen; sonst von
  unten heran gesucht – bei gewölbter Stirn mit Newton, sonst ℓ ← F(ℓ) –, und nur
  dort, wo die Ebene der Spitze noch unter dem Material liegt.
- Alle Schritte eines Stücks und alle Stücke einer Operation auf einmal
  (`fahre_stuecke`, `schnitte`, `np.minimum.at`); ebenso `rest_nach` beim
  Schlichten. Schruppen auf der Welle mit Absatz: 1,4 s statt 6,3 s, Ergebnis
  gleich (Abweichung 0).
- `fuer()` nimmt „Rundum schlichten“ dazu (`operationsarten_rundum`), je
  Operation die Form ihres Controllers (`form_des_controllers`, unbekannt:
  Schaftfräser), verglichen mit dem Aufmaß der letzten.
- Blau nur, was genau auf dem Strahl im Teil fehlt (Scheibe 0,001 mm): Neben einer
  Wand sah die halbe Rasterweite schon die Wand – nach der Kugel stand dort sonst
  „bis 8 mm im Teil“.
- Hilfe de/en („Rohteil und Fertigteil“): auch „Rundum schlichten“, mit der Form,
  Aufmaß der letzten Bearbeitung, die Rundung der Kugel in der Innenecke.
- `docs/aufbau.md`: Zeilen `restmaterial.py` und `vierachs_schlichten.py`
  (Vorstufen aus P-2026-09-30-06 nachgezogen).

### TEST
- FreeCAD 1.1.3: `test_restmaterial` (Kugel, Torus Ø 12 R 2, Konik gegen den
  fein abgetasteten Strahl unter 0,002 mm; Kugel-Spirale mit Kamm 0,501 mm;
  Schruppen und Schlichten auf der Beispiel-Drehmaschine: 0,006 … 0,024 mm, alles
  grün, 0,3 s), `test_vierachs_schlichten`, `test_vierachs_schlichten_op`,
  `test_hilfe` grün; `szenario_vierachs_schruppen` grün („Am Ende bleiben 0,3 …“).
- Welle mit Absatz, 365 Umdrehungen, Stange nach dem Schruppen: Kugel 1,3 s,
  Torus 2,2 s, Konik 5,5 s; Kugel 97,9 % grün, nichts blau, rot bis 1,95 mm nur
  in der Innenecke am Absatz.

### NEXT
- V5e zweite Hälfte: die Schneide in Abfahren und Kollision als Drehkörper aus
  der Form.

## P-2026-09-30-06 schlichten-in-stufen

### EINGELESEN
- NEXT aus P-2026-09-30-05: Auf der Welle mit Absatz ließ das Schruppen in der
  Innenecke schraubenförmige Keile bis zur Höhe des Absatzes stehen; der Schutz
  hielt den Kugelfräser dort oben („bis 7,3 mm bleiben stehen“).
- `camaddon/vierachs_bahn.py` (`schlichten`, `_nicht_tiefer`),
  `camaddon/vierachs_schlichten.py`, die Tests und das Szenario zum Schlichten.

### DATEIEN
- `camaddon/vierachs_bahn.py`, `camaddon/vierachs_schlichten.py`,
  `translations/de.json`, `translations/en.json`, `help/de/vierachs.html`,
  `help/en/vierachs.html`, `tests/test_vierachs_schlichten.py`,
  `tests/test_vierachs_schlichten_op.py`,
  `tests/gui/szenario_vierachs_schlichten.py`,
  `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit Absatz, „Rundum schruppen“ T1 Schaftfräser Ø 12 und „Rundum
schlichten“ T2 Kugelfräser Ø 6 anlegen: Das Ausgabefenster sagt „… nimmt
Schlichten vorher in Stufen ab (Vorstufen: 3) – je höchstens 3,00 mm tief“, an
der Operation steht „Vorstufen 3“; in der Nut, in die der Schruppfräser nicht
kommt, schlichtet die Bahn bis auf den Grund.

### DONE
- Was mehr als die Grenze (Radius des Schlichtfräsers, mindestens Aufmaß des
  Schruppens + 0,5 mm) stehen blieb, nimmt Schlichten vorher in Stufen ab, von
  oben nach unten, jede höchstens die Grenze unter der davor; danach die
  Schlichtspirale ganz bis aufs Teil. Eine Stufe fährt nur, wo sie etwas zu tun
  hat (nötige Stellen, die höchstens eine Umdrehung auseinanderliegen, am
  Stück), dazwischen Eilgang über der Stange; die Rundachse dreht nur vorwärts.
  Eingetaucht wird in der Umdrehung vor der ersten nötigen Stelle dort, wo am
  wenigsten Material steht.
- `Schlichtbahn.vorstufen` statt `stehen`; an der Operation „Vorstufen“ statt
  „Bleibt stehen“ (beide nie ausgeliefert), ein Satz im Ausgabefenster; die
  Umdrehungen zählen die Stufen mit.
- Hilfe de/en: ein Absatz zu den Stufen – auch, dass die Zeit im Assistenten
  ohne sie rechnet (403 statt 365 Umdrehungen auf der Welle mit Absatz).
- Gefunden beim Nachlesen: Die erste Fassung fuhr die Stufen in falscher
  Reihenfolge (die tiefste zuerst – 9 mm statt 3 mm tief). Der Test mit einer
  Stufe konnte es nicht sehen; neu ist der Kugelfräser Ø 2 in der Nut mit fünf
  Stufen 19,3 … 15,3 mm – mit der falschen Reihenfolge schlägt er an.

### TEST
- FreeCAD 1.1.3: `test_vierachs_schlichten` (Nut: eine Stufe auf 17,3 mm nur
  über dem Grund, eingetaucht über 18,2 mm, danach bis 15,0 mm; Ø 2: fünf
  Stufen von oben nach unten; C dreht nie zurück), `test_vierachs_schlichten_op`,
  `test_sprache`, `test_hilfe` grün; `szenario_vierachs_schlichten` grün
  (Vorstufen 3).

### NEXT
- V5e: Simulation und Kollision mit der echten Form des Fräsers.

## P-2026-09-30-05 assistent-schlichten

### EINGELESEN
- V5d in `docs/spezifikation_vierachs.md`; Manuels Entscheidungen: Schrittweite
  „Die Werte aus der Werkzeug Tabelle“, Abstände „Einmal für beide“.
- `camaddon/gui_vierachs.py` (Schritt 2, Anlegen, Ändern), die Szenarien
  `szenario_vierachs_schruppen`, `…_aendern`, `…_maschine`, `…_rohteil`.

### DATEIEN
- `camaddon/gui_vierachs.py`, `camaddon/vierachs_schlichten.py` (`vorschau`),
  `translations/de.json`, `translations/en.json`, `help/de/vierachs.html`,
  `help/en/vierachs.html`, `tests/gui/szenario_vierachs_schlichten.py` (neu),
  `docs/spezifikation_vierachs.md`, `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit Absatz → „4-Achs-Bearbeitung“ → Stange Ø 80 → „Weiter“: „Rundum
schlichten“ ist angehakt mit T2 Kugelfräser, grau Schrittweite 0,3 (aus der
Werkzeugtabelle), „→ Kammhöhe 0,004 mm“ und „→ … Umdrehungen, etwa … min“;
Doppelklick auf „Rundum schruppen T1“ eines Jobs ohne Schlichten → Haken bei
„Rundum schlichten“, „Übernehmen“ → im Job steht „Rundum schlichten T2“.

### DONE
- Schritt 2: Werkstoff und „Werkzeugverwaltung …“ oben, dann „Rundum
  schruppen“, „Rundum schlichten“ (Fräser, Einsatz, Schrittweite mit Kammhöhe,
  Aufmaß, Ergebnis) und „Abstände“ (Überlauf leer: je Fräser Radius + 0,5 mm,
  grau „Radius + 0,5“; eine Zahl gilt für beide). Die Beschriftungsspalte aller
  Blöcke ist gleich breit (`_Reihen`).
- Fräser fürs Schlichten: jede Form aus `fraeserform`; vorgewählt der zuletzt
  benutzte, beim Ändern der der Operation, sonst einer mit Einsatz
  „Schlichten“ (Kugel vor Torus). Der Haken ist beim Anlegen gesetzt, wenn es so
  einen Fräser gibt – Werkzeuglisten ohne Schlichten bleiben, wie sie waren
  (alle bisherigen Szenarien unverändert grün).
- Vorschau: Schruppen genau wie bisher, Schlichten grob
  (`vierachs_schlichten.vorschau`): Umdrehungen und Zeit, und ob es geht; ohne
  Schruppen (angehakt oder im Job) ein roter Satz.
- Die Stange ragt so weit heraus, wie der Fräser braucht, der hinten am meisten
  Platz nimmt – beim Ändern zählen die anderen Bearbeitungen im Job mit.
- Anlegen: Controller und Operationen beider Bearbeitungen in einem Schritt
  Rückgängig („Rundum schruppen und schlichten anlegen“). Ändern: „Rundum
  schlichten ändern“; beim Schruppen ein Schlichten dazunehmen, solange der Job
  keins hat – sonst sagt ein grauer Satz, wo es steht.
- Hilfe de/en: Abschnitt „Schritt 2: Rundum schlichten“, Abstände für beide,
  Schlichten dazunehmen.
- Gefunden im Szenario: Auf der Welle mit Absatz meldete die Operation „bis
  7,3 mm bleiben stehen“. Ursache ist das Schruppen: Der Schaftfräser kommt am
  Absatz erst herunter, wenn er ganz von der Wand weg ist, und die Spirale
  (4,8 mm je Umdrehung) trifft diese Stelle nicht unter jedem Winkel – in der
  Innenecke bleiben schraubenförmige Keile bis zur Höhe des Absatzes stehen.
  Der Schutz hielt den Kugelfräser dort richtig oben. Kommt als eigener Patch:
  Schlichten fährt solche Stellen in Stufen vor.
- Gefunden: „→ Kammhöhe 0,004“ ohne „mm“ – `{e_laenge}` im Text.

### TEST
- KI mit unsichtbarer Oberfläche, FreeCAD 1.1.3: `szenario_vierachs_schlichten`
  (neu), `szenario_vierachs_schruppen`, `…_aendern`, `…_maschine`, `…_rohteil`,
  `szenario_hilfe` grün; `test_sprache` grün. Screenshots angesehen
  (`1_schruppen_und_schlichten`, `2_schlichten_dazunehmen`,
  `3_schlichten_aendern`). Ob der Dialog ohne Erklärung verständlich ist, prüft
  Manuel.

### NEXT
- Schlichten in Stufen, wo das Schruppen mehr stehen ließ.

## P-2026-09-30-04 operation-rundum-schlichten

### EINGELESEN
- V5c in `docs/spezifikation_vierachs.md`; `camaddon/vierachs_operation.py`,
  `camaddon/werkzeuge_aus_cam.py` (`werkzeug_aus`), `camaddon/job_schnittwerte.py`
  (`operationsart`, `EINSATZ_NACH_OPERATION`), `tests/test_vierachs_operation.py`,
  `tests/test_job_schnittwerte.py` (Werkzeugverwaltung im Test).
- Nachgesehen in 1.1.3 und im Wochen-Build: Das ToolBit eines Controllers im
  Dokument hat `ShapeType` („Endmill“, „Ballend“ …).

### DATEIEN
- `camaddon/vierachs_schlichten.py` (neu), `camaddon/vierachs_operation.py`,
  `camaddon/vierachs_bahn.py`, `camaddon/werkzeuge_aus_cam.py`,
  `camaddon/job_schnittwerte.py`, `translations/de.json`, `translations/en.json`,
  `tests/test_vierachs_schlichten_op.py` (neu), `docs/spezifikation_vierachs.md`,
  `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`tests/test_vierachs_schlichten_op.py` ist grün in 1.1.3 und im Wochen-Build:
„Rundum schlichten T2“ mit Kugelfräser Ø 6 fährt nach „Rundum schruppen“ die
Welle Ø 60 auf 30,000 … 30,01 mm Radius ab; ohne Schruppen steht ein Satz statt
einer Bahn.

### DONE
- Operation `RundumSchlichten` im eigenen Modul `vierachs_schlichten` (der
  Modulname ist die Art: „Schnittwerte in den Job“ gibt ihr den Einsatz
  „Schlichten“). Eigenschaften: Rundachse wie beim Schruppen, Schrittweite,
  Aufmaß, Überlauf, Abstand zum Futter, Sicherheitsabstand; zum Lesen
  Kammhöhe, Umdrehungen, bleibt stehen. `lege_an()`, `aendere()` (der Name
  folgt dem Werkzeug), `bahn_fuer()` (auch für die Vorschau),
  `schrittweite_vorschlag()` (ae des Einsatzes, sonst D/50),
  `form_des_controllers()`.
- Die Form liest sie aus dem ToolBit des Controllers
  (`werkzeuge_aus_cam.vom_controller`) – so, wie CAM damit fräst.
- Der Rest nach dem Schruppen: die Bahnen der aktiven „Rundum schruppen“ des
  Jobs, von der Stange abgetragen (`rest_nach`, `restmaterial.Stange`).
- `vierachs_operation`: Eigenschaften der Rundachse und die Abstände als
  `achs_eigenschaften()`/`abstand_eigenschaften()` für beide Operationen;
  `ist_rundum()` gilt für beide, `ist_schruppen()` nur fürs Schruppen.
- Gefunden: Hinter dem Teil lässt die Schruppspirale an ihrem Ende einen Keil
  stehen – ihre letzte Umdrehung läuft nicht rundum auf dem Ende. Ein
  Torusfräser R 5 mit Überlauf 5,5 reichte hinein, der Schutz hielt ihn oben und
  meldete „4,9 mm bleiben stehen“ – auf einer glatten Welle. Gemeldet wird jetzt
  nur, was über dem Teil stehen bleibt; im Überlauf hält der Schutz den Fräser
  weiter oben (dort wird abgestochen). Eine volle letzte Umdrehung beim
  Schruppen wäre sauberer – notiert, nicht hier.
- Gefunden: Einen Formfräser übergibt das Addon an CAM als Schaftfräser – die
  Operation rechnet ihn als Scheibe (liegt außen um jedes Profil, sicher). Der
  Satz „Form unbekannt“ gilt für Gewindefräser, Bohrer und Ähnliches.

### TEST
- KI ohne GUI: `test_vierachs_schlichten_op`, `test_fraeserform`,
  `test_vierachs_schlichten` in 1.1.3 und im Wochen-Build grün;
  `test_vierachs_operation`, `test_sprache`, `test_job_schnittwerte`,
  `test_werkzeuge_aus_cam` in 1.1.3 grün.

### NEXT
- V5d Assistent: Schlichten in Schritt 2.

## P-2026-09-30-03 schlichtbahn

### EINGELESEN
- V5b in `docs/spezifikation_vierachs.md`; `camaddon/vierachs_bahn.py`
  (Schruppen, `_hinten_weiter`, `_knicke`, `befehle`), `camaddon/restmaterial.py`
  (`Stange`, `fahre`), P-2026-09-30-02 (`je_winkel`, `mit_aufmass`).

### DATEIEN
- `camaddon/vierachs_bahn.py`, `translations/de.json`, `translations/en.json`,
  `tests/test_vierachs_schlichten.py` (neu), `docs/spezifikation_vierachs.md`,
  `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`tests/test_vierachs_schlichten.py` ist grün: Die Schlichtspirale liegt auf der
Welle mit Absatz nirgends im Teil und höchstens um Toleranzen darüber, und in
einer Nut, in die der Schruppfräser nicht kam, schneidet sie höchstens den
Radius des Kugelfräsers tief.

### DONE
- `schlichten(netz, laengs, radial, Schlichtwerte)` → `Schlichtbahn` (Punkte,
  Umdrehungen, kleinster Radius, Kammhöhe, hinten frei, was stehen bleibt, wie
  tief höchstens). Die Spirale hat die Schrittweite als Steigung, alle 0,5° ein
  Punkt; je Winkel rechnet `je_winkel` genau an den Stellen, an denen sie
  vorbeikommt – mit dem Fräser um Aufmaß und Vernetzung größer (so bleibt der
  Abstand quer zur Fläche, auch an steilen Flanken).
- Vor und hinter dem Teil die Tiefe an seinem Ende (`_auffuellen`), nie näher
  an die Achse als der Fräserradius, nie näher ans Futter als der Abstand.
- Schutz (`_nicht_tiefer`): der Rest nach dem Schruppen (Raster aus
  `restmaterial`), je Stelle mit dem Profil des Schlichtfräsers ausgebreitet;
  tiefer als die Grenze schneidet die Bahn nicht, was dann stehen bleibt, sagt
  `stehen`.
- Sehnenfehler (`_sehnenfehler`), Zusammenfassen (`_zusammengefasst`: die
  Gerade bleibt über jedem ausgelassenen Punkt und höchstens 0,002 mm darüber,
  höchstens 90° je Satz).
- Abweichung vom Plan, gefunden beim Durchrechnen: Die Grenze des Schutzes ist
  der Radius des Schlichtfräsers (mindestens Aufmaß + 0,5 mm), nicht Aufmaß +
  0,5 mm. Der Schaftfräser lässt beim Schruppen auf schrägen Flächen Stufen bis
  Vorschub je Umdrehung × Steigung stehen (4,8 mm auf 45°) – die hätte
  Schlichten sonst auf jedem Kegel stehen gelassen.
- Gefunden beim Prüfen: Der Sehnenfehler aus der zweiten Differenz hob die Bahn
  an jeder Wand bis 0,5 mm – dort springt die Hüllfläche, und die Gerade
  dringt nur um Tausendstel längs ein. Jetzt höchstens 0,02 mm (so viel braucht
  ein Eckradius von 0,2 mm).
- Die Prüfung vergleicht mit dem dicht abgetasteten Umriss im Schnitt durch die
  Werkzeugachse; wo die Hüllfläche steil ist, darf die Bahn um Toleranz ×
  Steigung höher liegen (der größere Fräser verschiebt sie längs), an
  Sprüngen zählt es nicht.
- Texte `vb.fehler.schrittweite`, `vb.fehler.schrittweite_gross`; der Satz
  für „bleibt stehen“ kommt mit der Operation (V5c).

### TEST
- KI ohne GUI, FreeCAD 1.1.3: `test_vierachs_schlichten` (Absatz 36 966 Punkte
  in 1,1 s, Welle mit Nocken 83 341 in 1,2 s), `test_vierachs_bahn`,
  `test_vierachs_operation`, `test_restmaterial`, `test_sprache` grün.

### NEXT
- V5c Operation „Rundum schlichten“.

## P-2026-09-30-02 fraeserform-huellflaeche

### EINGELESEN
- V5a in `docs/spezifikation_vierachs.md` (P-2026-09-30-01), Manuel: Fräser
  „Mit allen“.
- `camaddon/vierachs_huelle.py`, `camaddon/werkzeugform.py` (`konus`, `kegel`,
  `radienprofil` – dieselben Maße wie Bild und CAM), `camaddon/werkzeuge.py`
  (Arten, `mass`, `wert`).

### DATEIEN
- `camaddon/fraeserform.py` (neu), `camaddon/vierachs_huelle.py`,
  `tests/test_fraeserform.py` (neu), `docs/spezifikation_vierachs.md`,
  `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`tests/test_fraeserform.py` ist grün: Die Hüllfläche jedes Fräsers liegt nie
über dem dicht abgetasteten Umriss von Absatz, Kugel und Sechskant und
höchstens um die Vernetzung darunter.

### DONE
- `fraeserform.Form`: Profil aus Stücken EBEN (Scheibe), BOGEN (Kugel,
  Eckradius), HOHL (Kehle), GERADE (Kegel); `hoehe(ρ)`, `stuetze(θ)` (wo eine
  geneigte Ebene zuerst berührt – über die konvexe Hülle), `mit_aufmass(d)`
  (rundum größer, Ecken werden Bögen), `kammhoehe(s)`, `aussen()`.
  `von_werkzeug()` für Schaft-, Nuten-, Schwalbenschwanz-, Plan-, Kugel-,
  Lollipop-, Torus-, Konik-, Fasen- und Radienfräser; Form- und
  Gewindefräser: None.
- `vierachs_huelle.fraeser()` (Raster wie `schaftfraeser`) und `je_winkel()`
  (je Winkel eigene Stellen längs – fürs Schlichten an den Stellen seiner
  Spirale). Gegen Ecken genau, gegen Dreiecke genau (`_dreiecke_treffen` mit
  der Berührstelle aus der Form), gegen Kanten: Scheibe und Kugel geschlossen,
  sonst goldener Schnitt – längs einer Kante ist x − z(Abstand) für konvexe
  Profile konkav. Wo eine Kante unter einer Scheibe oder dem Rand herauskommt,
  rechnet die Scheibe. Der Schaftfräser rechnet wie bisher (Schruppen
  unverändert, `test_vierachs_huelle`, `test_vierachs_bahn` grün).
- Gefunden beim Prüfen: Die erste Vergleichsrechnung (Punkte dicht auf jedem
  Dreieck) meldete bis 2 mm Unterschied – genau dort, wo der Fräser eine Kante
  mit dem Rand streift, verfehlt jedes Abtasten die Berührstelle. Die Prüfung
  vergleicht deshalb im Schnitt durch die Werkzeugachse (Drehteil, Sechskant),
  wo der Umriss sich 0,002 mm dicht abtasten lässt.
- Gefunden beim Prüfen: An steilen Flanken (Kugel nahe ihrem Pol) liegt das
  Netz längs der Werkzeugachse weiter als die Toleranz innen – quer zur
  Fläche bleibt es bei ihr. Fürs Schlichten heißt das: mit dem Fräser um die
  Toleranz größer rechnen (`mit_aufmass`), nicht die Spitze heben (V5b).
- Bewusst nicht: die Hohlkehle des Radienfräsers genau. Unterteilte Kanten
  kosteten auf der Welle mit Nocken 70 bis 230 s; mit der Sehne bleibt er
  höher, das Teil sicher.

### TEST
- KI ohne GUI, FreeCAD 1.1.3: `test_fraeserform`, `test_vierachs_huelle`,
  `test_vierachs_bahn` grün. Zeiten auf der Welle mit Nocken, 0,5° rundum,
  0,35 mm längs (226 080 Punkte): Kugel 0,5 s, Torus 2,3 s, Konik 4,1 s; mit
  0,12 mm (Schrittweite D/50 aus der Werkzeugtabelle, 659 520 Punkte) Kugel
  1,5 s.

### NEXT
- V5b Bahn „Rundum schlichten“.

## P-2026-09-30-01 plan-schlichten

### EINGELESEN
- Manuel (2026-09-30): „Und es darf ja nicht nur Schuppen geben auch schlichten
  ist wichtig.“ Seine Antworten auf die Fragen mit Optionen: Bahn „Spirale“;
  Fräser „Mit allen“; Schrittweite „Die Werte aus der Werkzeug Tabelle“;
  Abstände „Einmal für beide“.
- `docs/spezifikation_vierachs.md` (Abschnitte 7, 9, 13, „Entschieden“),
  `camaddon/vierachs_huelle.py`, `camaddon/vierachs_bahn.py`,
  `camaddon/vierachs_operation.py`, `camaddon/gui_vierachs.py` (Schritt 2),
  `camaddon/werkzeuge.py` (Arten, Maße, Einsätze), `camaddon/kollision.py`
  und `camaddon/reichweite.py` (Schneide als Zylinder, Lollipop als Kugel).

### DATEIEN
- `docs/spezifikation_vierachs.md` (V5 in fünf Schritten, „Entschieden“,
  Stand), `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation sagt, wie „Rundum schlichten“ gebaut wird – mit Manuels
Entscheidungen und einem Klickweg.

### DONE
- V5 „Rundum schlichten“ vor V4, in fünf Schritten: V5a Fräserform (jeder
  Fräser als Drehprofil, Hüllfläche genau an den Stellen der Spirale), V5b
  Bahn (Spirale, Schutz vor zu tiefen Schnitten in engen Stellen), V5c
  Operation, V5d Assistent (zweiter Haken, Abstände einmal für beide,
  Schlichten zu einem Job aus 0.27 dazunehmen), V5e Simulation und Kollision
  mit der echten Form.
- Gefunden beim Lesen: Die Kollisionsprüfung nimmt die Schneide eines
  Kugel- oder Torusfräsers als Zylinder – beim Schlichten in einer Kehle
  meldete sie „ins fertige Teil“. Kommt mit V5e.
- Snapshot: Die Frage, wie weit das Teil aus dem Futter ragen soll, stand
  noch offen, ist aber seit V3f beantwortet – entfernt.

### TEST
- Nur Doku.

### NEXT
- V5a Fräserform und Hüllfläche.

## P-2026-09-29-14 version-0-27-1

### EINGELESEN
- `package.xml`; P-2026-09-29-13 (Länge der Stange in Schritt 1 beim Ändern).

### DATEIEN
- `package.xml`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.27.1 an – mit der richtigen Länge der Stange
in Schritt 1 beim Ändern.

### DONE
- Version 0.27.1.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build vor dem Push.

### NEXT
- Manuels Test.

## P-2026-09-29-13 vierachs-laenge-in-schritt-1

### EINGELESEN
- Bild `4_schritt1_wie_im_job` aus dem vollen Lauf für 0.27.0: Beim Ändern
  stand in Schritt 1 „Stange 134,0 mm lang“, die Stange im Job war 144,5 mm
  (mit dem Platz für T2 hinter dem Teil, P-2026-09-29-07).
- `camaddon/gui_vierachs.py` (`zeige_seite`, `_auffrischen`).

### DATEIEN
- `camaddon/gui_vierachs.py`, `tests/gui/szenario_vierachs_aendern.py`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Zurück in Schritt 1 nennt die Länge der Stange den Platz, den der Fräser aus
Schritt 2 hinter dem Teil braucht.

### DONE
- `zeige_seite(1)` frischt die Beschriftungen auf – die Länge rechnet mit dem
  Fräser aus Schritt 2 (vorher stand, was beim Öffnen galt).

### TEST
- `szenario_vierachs_aendern`: „Zurück“ zeigt „144,5“.

### NEXT
- Version 0.27.1, voller Lauf, Push.

## P-2026-09-29-12 version-0-27-0

### EINGELESEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`; Manuel: „mach das alles
  ich geh ins bett .. bis morgen is fertig !“; CLAUDE.md (höhere Version, damit
  „Nach Updates schauen“ sie anbietet).

### DATEIEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet Manuel 0.27.0 an – mit allem aus der Nacht
(P-2026-09-29-06 bis -11).

### DONE
- Version 0.27.0; README: Maschine zuerst, Überlauf, Ausspannlänge, Rohteil und
  Fertigteil, Werkzeugspitze, Stange nachträglich ändern; Stand nachgezogen.
- FreeCAD 1.1.4 gibt es bei conda-forge noch nicht (neueste 1.1.x: 1.1.3) –
  der Versionscheck bleibt beim Quelltextvergleich aus P-2026-09-29-01.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build vor dem Push.

### NEXT
- Manuels Test; V2b (Drehteile), V4 (Flächen wählen), TCPM nach seiner Antwort.

## P-2026-09-29-11 rohteil-fertigteil-simulation

### EINGELESEN
- Manuel (2026-09-29): „haben wir eine rohteil und fertigteil vergleich in der
  ‚simualtion‘“.
- `docs/spezifikation_vierachs.md` (V3g), `camaddon/gui_abfahren.py`,
  `camaddon/gui_reichweite.py`, `camaddon/abfahren.py`,
  `camaddon/vierachs_huelle.py` (Raster, Hüllfläche einer Scheibe).

### DATEIEN
- `camaddon/restmaterial.py` (neu), `camaddon/gui_abfahren.py`,
  `camaddon/gui_reichweite.py`, `translations/de.json`, `translations/en.json`,
  `help/de/reichweite.html`, `help/en/reichweite.html`,
  `tests/test_restmaterial.py` (neu), `tests/gui/szenario_vierachs_schruppen.py`,
  `docs/spezifikation_vierachs.md`, `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beim Abspielen eines Jobs mit „Rundum schruppen“ wird die Stange im
Prüffenster abgetragen, und an der letzten Station steht sie in Farben gegen das
fertige Teil, mit einem Satz, wie viel stehen bleibt.

### DONE
- `restmaterial.Stange`: Radien über (a, φ), 0,5 mm × 1°; ein radialer Fräser
  trägt ab, was in ihm liegt (Strahl aus der Achse ab r / cos Δ), zwischen
  zwei Punkten in Schritten von 0,5 mm am Umfang.
- `Abtrag` aus der Abfahrt (Spitze am gedrehten Teil je Station, nur
  „Rundum schruppen“): bis zu einer Station, zurück von vorn; `vergleiche()`
  gegen die Radien des Teils – grün bis Aufmaß + 0,1, gelb, rot ab Aufmaß + 1,
  blau im Teil.
- Prüffenster: Die abgetragene Stange ersetzt das durchscheinende Rohteil;
  an der letzten Station ist die Bahn aus und die Stange in Farben; unter dem
  Abspieler der Satz („Am Ende bleiben 0,32 mm … 0,33 mm auf dem Teil (Aufmaß
  0,30 mm), nirgends ins Teil. Grün: …“), beim Abtragen, was geschieht.

### TEST
- Neu `test_restmaterial` (ein Schnitt: darunter bis zur Spitze, daneben
  nichts; Spirale auf 38; Rundum schruppen auf der Beispiel-Drehmaschine:
  Rest 0,325 … 0,331 mm, alles grün, nichts blau; zurück rechnet von vorn).
- `szenario_vierachs_schruppen` (Satz beim Abtragen, am Ende „Am Ende bleiben
  0,3… nirgends ins Teil“, Bilder `5_rest_farben`, `5b_rest_satz`) in 1.1.3
  und im Wochen-Build; `test_sprache`, `test_hilfe`.

### NEXT
- Version 0.27.0, voller Lauf, Push, Bericht an Manuel.

## P-2026-09-29-10 spitze-tcp-kinematik

### EINGELESEN
- Manuel (2026-09-29): „x-60 ist ja unter der drehmitte was garnicht sein kann
  ... das x-60 ist ja nur die maschinen koordinate .. nicht wenn nen fräser mit
  dabei ist .. der TCP muss schon mit berechnet werden .. generell immer 😉 also
  machs so das es auch tcp kann deine wegberechnung .. generell solltest du die
  wegberechnung sehr sehr sehr extrem gut machen .. und am besten sehr variabel
  so das man immer wieder neue sachen raus machen kann ... es muss einfach
  genial gebaut sein das du das nicht jedes mal neu erfinden musst“.
- `docs/spezifikation_simulation.md` (4e), `camaddon/reichweite.py`,
  `camaddon/abfahren.py`, `camaddon/gui_abfahren.py`, `camaddon/vierachs_bahn.py`.

### DATEIEN
- `camaddon/kinematik.py` (neu), `camaddon/abfahren.py`, `camaddon/gui_abfahren.py`,
  `camaddon/reichweite.py`, `translations/de.json`, `translations/en.json`,
  `help/de/reichweite.html`, `help/en/reichweite.html`, `tests/test_kinematik.py`
  (neu), `tests/test_reichweite.py`, `tests/test_vierachs_pruefen.py`,
  `tests/gui/szenario_abfahren.py`, `tests/gui/szenario_vierachs_schruppen.py`,
  `docs/spezifikation_simulation.md`, `docs/aufbau.md`, `CHATSTART.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Das Prüffenster sagt, wo die Werkzeugspitze steht – im Abspieler als „Spitze im
Programm: X …“ und an jeder Überschreitung einer Linearachse, wo die Spitze an
der Grenze stünde –, gerechnet an einer Stelle (`kinematik.py`).

### DONE
- `kinematik.Kinematik` (ein Werkzeug auf einer Maschine, Nullpunkt des Jobs):
  `stellungen()` rückwärts, `programm()` und `am_werkstueck()` vorwärts,
  `rundachsen()`; ohne TCPM wie bisher (Rundachsen auf 0 gelöst).
- `Abfahrt` kennt den Nullpunkt und je Operation ihre Kinematik;
  `am_werkstueck()` (die Bahn im Bild) rechnet damit, `spitze()` für den
  Abspieler.
- Abspieler: Zeile „Spitze im Programm: X 50, Y 0, Z 18“; am Anschlag rot
  dahinter „– soll: X 100, Y 0, Z 18“.
- Überschreitungen einer Linearachse: „… An der Grenze stünde die Spitze von
  T1 bei X −50, Y 0, Z 18.“
- TCPM wählbar zurückgestellt (Spezifikation 4e): „Rundum schruppen“ schreibt
  für eine Steuerung ohne TCPM; mit TCPM bräuchte es eine eigene Ausgabe.

### TEST
- Neu `test_kinematik` (Fräse hin und zurück, X1 an der Grenze → X 250;
  Drehmaschine mit C: programm = Punkt, am Werkstück um −C gedreht).
- `test_reichweite` (Satz mit der Spitze), `test_vierachs_pruefen`,
  `test_abfahren`, `test_sprache`, `test_hilfe`.
- `szenario_abfahren` (Spitze auf der Geraden, am Anschlag mit „soll“, der
  Satz an der Überschreitung), `szenario_vierachs_schruppen` (Spitze mit C);
  `szenario_reichweite`, `szenario_kollision` in 1.1.3 und im Wochen-Build.

### NEXT
- V3g: Rohteil und Fertigteil in der Simulation.

## P-2026-09-29-09 vierachs-maschine-zuerst

### EINGELESEN
- Manuel (2026-09-29): „vll sollte man als erstes die abfrage machen ‚hey was
  hast du für ne maschine‘ nachdem man ausgewählt hat was man bearbeiten will
  ... wie gesagt der prozess soll extrem einfach werden .. für den anwender“.
- `docs/spezifikation_vierachs.md` (V3f), `camaddon/gui_vierachs.py`,
  `camaddon/vierachs_achsen.py`, `camaddon/gui_reichweite.py`
  (`offene_maschinen`, `oeffne_datei`, `zeige_dokument`),
  `camaddon/reichweite.py` (D-20: `gemerkte_maschine`, `merke_maschine`).

### DATEIEN
- `camaddon/vierachs_achsen.py` (`Maschinenwahl`, `maschinen()`; `offene()`
  entfällt – `maschinen()` ersetzt sie), `camaddon/gui_vierachs.py`,
  `translations/de.json`, `translations/en.json`, `help/de/vierachs.html`,
  `help/en/vierachs.html`, `tests/test_vierachs_achsen.py`,
  `tests/gui/szenario_vierachs_maschine.py`, `docs/spezifikation_vierachs.md`,
  `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In Schritt 1 steht gleich unter dem Teil „Maschine“ mit der offenen Maschine
vorgewählt und einem Satz, was sie kann; die Rundachse folgt aus ihr.

### DONE
- Liste „Maschine“: offene Maschinen (vorgewählt die erste mit einer Rundachse
  für die Stange), die zuletzt benutzte zum Öffnen (D-20; die Ansicht bleibt
  beim Teil), eine ohne passende Rundachse grau, „ohne Maschine“.
- Darunter grau: „Linearachsen X1, Y1, Z1 · Rundachse für die Stange: C ·
  12 Werkzeugplätze“ – ohne Maschine, wie A, B und C liegen.
- „Rundachse“ zeigt nur die Achsen der gewählten Maschine (eine: nicht
  wählbar), ohne Maschine A, B, C; die Einträge ohne Maschinennamen und ohne
  „(ohne Maschine)“ – das steht jetzt darüber.
- Der Job merkt sich die gewählte Maschine (gespeichert), „Auf der Maschine
  prüfen“ nimmt sie. Beim Ändern steht die Maschine gewählt, deren Achse die
  Operation hat; A/B/C als zuletzt gewählte nur ohne Maschine gemerkt.

### TEST
- `test_vierachs_achsen` (`maschinen()`: Name, C, X1/Y1/Z1, 12 Plätze).
- `szenario_vierachs_maschine` (Maschine vorgewählt, der Satz, C nicht
  wählbar; A → ohne Maschine; gespeichert, geschlossen, „„drehmaschine“ öffnen
  (zuletzt benutzt)“ → offen, C, die Welle bleibt vorn); dazu die anderen
  4-Achs-Szenarien in 1.1.3 und im Wochen-Build; `test_sprache`, `test_hilfe`.

### NEXT
- 4e: Kinematik-Kern, Spitze im Abspieler, TCPM wählbar.

## P-2026-09-29-08 vierachs-kugel-torus-hinweis

### EINGELESEN
- Manuel (2026-09-29): „ich leg jetzt nochmal einen rundfräser an und schau
  mal was er da macht“; zugesagt: ein Satz, dass Kugel- und Torusfräser wie
  ein Schaftfräser schruppen.
- `camaddon/vierachs_bahn.py`, `camaddon/vierachs_huelle.py` (Stirn als
  Scheibe), `camaddon/gui_vierachs.py`, `camaddon/werkzeuge.py` (Eckradius).

### DATEIEN
- `camaddon/vierachs_bahn.py` (`rillenhoehe`), `camaddon/gui_vierachs.py`,
  `translations/de.json`, `translations/en.json`, `help/de/vierachs.html`,
  `help/en/vierachs.html`, `tests/test_vierachs_bahn.py`,
  `tests/gui/szenario_vierachs_aendern.py`, `docs/spezifikation_vierachs.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Mit einem Kugel- oder Torusfräser sagt Schritt 2 in einem Satz, dass wie mit
einem Schaftfräser gerechnet wird und wie hoch Rillen zwischen den Bahnen
stehen bleiben.

### DONE
- `rillenhoehe(Radius, Eckradius, Vorschub je Umdrehung)`: in der Mitte
  zwischen zwei Bahnen, am Ende der flachen Stirn beginnend die Rundung.
- Schritt 2: grauer Satz bei Kugel- und Torusfräser, „… Rillen bis 0,42 mm
  über dem Aufmaß …“ – oder „keine Rillen“, wenn die flache Stirn reicht.

### TEST
- `test_vierachs_bahn` (Kugel, Torus flach und weit, Schaftfräser).
- `szenario_vierachs_aendern`: T3 Kugelfräser Ø 10, 4 mm je Umdrehung →
  „0,42 mm“; beim Schaftfräser kein Satz; Bild `1b_kugelfraeser`.

### NEXT
- Maschine zuerst (V3f).

## P-2026-09-29-07 vierachs-ueberlauf-ausspannlaenge

### EINGELESEN
- Manuel (2026-09-29): „wenn das bauteil 30 mm lang ist .. und du sagst ‚ja
  maximal bis 33 mm in z minus darfst du fahren mit deinem 12er fräser‘ dann
  ist das nicht schlau ... da muss man schon mindestens mal 6.5 drüber fahren
  ... und dann brauch tman noch einen sicherheits abstand zum futter ... also
  am sinnvolsten ist .. man macht das bauteil + fräser + sicherheitsabstand ..
  und sagt dem benutzer auch ‚hey so lange muss es ausgespannt sein‘“; „alle
  abstände zu was auch immer müssen einstellbar sein aber mit einem
  standartwert der sinnvoll ist gefüllt werden“.
- `docs/spezifikation_vierachs.md` (V3f), `camaddon/vierachs_bahn.py`,
  `camaddon/vierachs_operation.py`, `camaddon/vierachs_rohteil.py`,
  `camaddon/gui_vierachs.py`, die 4-Achs-Prüfungen und -Szenarien.

### DATEIEN
- `camaddon/vierachs_bahn.py`, `camaddon/vierachs_operation.py`,
  `camaddon/vierachs_rohteil.py`, `camaddon/gui_vierachs.py`,
  `translations/de.json`, `translations/en.json`, `help/de/vierachs.html`,
  `help/en/vierachs.html`, `tests/test_vierachs_bahn.py`,
  `tests/test_vierachs_operation.py`, `tests/gui/szenario_vierachs_schruppen.py`,
  `tests/gui/szenario_vierachs_aendern.py`, `docs/spezifikation_vierachs.md`,
  `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Mit einem Fräser Ø 12 endet die Rundum-Bahn 6,5 mm hinter dem Teil, und
Schritt 2 sagt, wie weit die Stange dafür aus dem Futter ragen muss – so lang
legt er sie an.

### DONE
- Bahn: Die Spirale läuft bis Überlauf (Mitte des Fräsers, Vorschlag Radius +
  0,5) hinter das Teil, dort auf der Tiefe des letzten Stücks Kontur statt auf
  dem Stangenradius; der Rand des Fräsers bleibt den Abstand zum Futter
  (Vorschlag 5 mm, bisher fest 2) vor der Spannfläche.
- Operation: Eigenschaften „Ueberlauf“ und „AbstandFutter“; Operationen aus
  0.26 bekommen beim Laden Radius + 0,5 und 2 mm – ihre Bahn bleibt gleich.
- Stange: Hinter dem Teil liegt die Lücke – Abstechbreite oder mehr, wenn der
  Fräser Platz braucht (Überlauf + Radius + Abstand zum Futter);
  `ausspannlaenge()`. Die Abstechbreite steht am Job, damit „Ändern“ sie von
  der Lücke unterscheidet.
- Assistent, Schritt 2: Felder Überlauf, Abstand zum Futter, Sicherheitsabstand
  mit Vorschlag; der Satz „Die Stange muss 118,5 mm aus dem Futter ragen:
  Planaufmaß 1,0 + Teil 100,0 + Überlauf 6,5 + Fräserradius 6,0 + Abstand zum
  Futter 5,0.“; die Stange zieht nach (anderer Fräser, andere Abstände, ohne
  „Rundum schruppen“ nur die Abstechbreite). Beim Ändern stehen die Werte der
  Operation in den Feldern.
- Spezifikation: Die Formel der Ausspannlänge berichtigt – zum Futter hin
  kommt der Fräserradius dazu (das Beispiel dort: 78,5 statt 72,5 mm).

### TEST
- `test_vierachs_bahn` (Ende −106,5, Tiefe im Überlauf, Futter nah: 4,5 mm
  fehlen, ohne Überlauf), `test_vierachs_operation` (Ende, Abstände, alte
  Operation beim Laden), `test_vierachs_rohteil`, `test_sprache`, `test_hilfe`.
- `szenario_vierachs_schruppen` (Satz, Stange 148,5 mm, Bahn endet bei
  Z −106,5; Prüffenster und Kollision wie bisher) und
  `szenario_vierachs_aendern` (T2: Stange 144,5 mm, eigener Schritt „Stange
  ändern“) in 1.1.3 und im Wochen-Build.

### NEXT
- Hinweis für Kugel- und Torusfräser; Maschine zuerst (V3f).

## P-2026-09-29-06 vierachs-rohteil-aendern

### EINGELESEN
- Manuel (2026-09-29): „muss irgendwie gelöst werden das man im nachhinein
  noch sachen ändern kann“ – nach P-2026-09-29-04 fehlte noch Schritt 1.
- `camaddon/vierachs_rohteil.py`, `camaddon/gui_vierachs.py`,
  `camaddon/vierachs_operation.py`, `tests/test_vierachs_rohteil.py`,
  `tests/gui/szenario_vierachs_aendern.py`.

### DATEIEN
- `camaddon/vierachs_rohteil.py` (`einstellung`, `laengs_von` nimmt eine
  Richtung), `camaddon/gui_vierachs.py`, `camaddon/vierachs_operation.py`
  (`setze_achse`, auch in `lege_an`), `translations/de.json`,
  `translations/en.json`, `help/de/vierachs.html`, `help/en/vierachs.html`,
  `tests/test_vierachs_rohteil.py`, `tests/gui/szenario_vierachs_aendern.py`,
  `docs/spezifikation_vierachs.md`, `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beim Ändern führt „Zurück“ zu Schritt 1 mit Stange, Mitte, Drehlage, Längen
und Rundachse, wie sie im Job stehen, und eine dort geänderte Stange kommt mit
„Übernehmen“ als eigener Schritt Rückgängig in den Job.

### DONE
- `vierachs_rohteil.einstellung(job)`: rechnet Teil, Stirnfläche, Mitte,
  Drehlage und Stange aus dem Job zurück – Klon = Lage · Original, die
  Stirnfläche bei a = 0 mit der Außennormale längs, der Zylinder vom Futter bis
  vor das Planaufmaß, die Spannlänge gemerkt. None, wenn der Job nicht mehr so
  aussieht (Klon verschoben, kein Zylinder). Nichts Neues gemerkt – geht auch
  mit Jobs aus 0.26.0.
- Assistent beim Ändern: „Zurück“ zu Schritt 1, alle Werte in den Feldern,
  die Rundachse der Operation gewählt (fehlt sie in der Liste, kommt sie
  dazu); die Stange wird durchsichtig, eine andere Fläche desselben Teils
  lässt sich anklicken, ein anderes Teil nicht (Satz). Jede Änderung öffnet
  einmal „Stange ändern“ und zieht die Rundachse aller „Rundum schruppen“ des
  Jobs mit (`setze_achse`); „Übernehmen“ legt sie vor „Rundum schruppen
  ändern“ ab, „Abbrechen“ nimmt sie zurück; die Stange sieht danach wieder aus
  wie vorher. Geht Schritt 1 nicht, bleibt „Zurück“ weg, mit einem Satz.

### TEST
- `test_vierachs_rohteil`: zurückgerechnet bei C (Mitte der Fläche, 0°),
  bei A (andere Stange) und bei B (ganzes Teil, 90°); quer verschoben: None.
- `szenario_vierachs_aendern` (1.1.3 und Wochen-Build): „Zurück“ zeigt 80, 1,
  3, 30, A; Ø 90 → Stange sofort Ø 90, „Übernehmen“: „Stange ändern“ und
  „Rundum schruppen ändern“, mehr Lagen, die Stange wieder wie in CAM; Ø 100
  und „Abbrechen“: bleibt Ø 90; viermal Strg+Z: T1, Ø 80. Bild
  `4_schritt1_wie_im_job`.
- `test_vierachs_operation`, `test_sprache`, `test_hilfe`; die übrigen
  4-Achs-Szenarien in 1.1.3.

### NEXT
- V3f: Maschine zuerst, Überlauf, Abstand zum Futter, Ausspannlänge.

## P-2026-09-29-05 version-0-26-1

### EINGELESEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`; CLAUDE.md („Soll
  Manuel etwas ausprobieren, braucht der Push eine höhere Version“).

### DATEIEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet Manuel 0.26.1 an – mit Verfahrwegen in
„Maschine bearbeiten“ und „Rundum schruppen“ nachträglich ändern.

### DONE
- Version 0.26.1; README: Verfahrweg im Fenster „Maschine bearbeiten“,
  nachträglich ändern per Doppelklick; Stand nachgezogen.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build vor dem
  Push.

### NEXT
- Schritt 1 nachträglich ändern; V3f.

## P-2026-09-29-04 vierachs-nachtraeglich-aendern

### EINGELESEN
- Manuel (2026-09-29 20:30, Bild: Job „Körper – 4 Achsen002“ mit der
  Rundum-Bahn in FreeCAD 1.1.4): „so wenn ich jetzt hier nochmal schnittwerte
  ändern will oder anders werkzeug komme ich nicht mehr in die maske rein ...
  das ist auch nicht optimal muss irgendwie gelöst werden das man im
  nachhinein noch sachen ändern kann.“
- `camaddon/gui_vierachs.py`, `camaddon/gui_vierachs_operation.py`,
  `camaddon/vierachs_operation.py`, `camaddon/job_schnittwerte.py`,
  `camaddon/vierachs_achsen.py`, `tests/gui/szenario_vierachs_schruppen.py`,
  `tests/test_job_schnittwerte.py`, `tests/test_vierachs_operation.py`,
  `help/*/vierachs.html`, `docs/spezifikation_vierachs.md`.

### DATEIEN
- `camaddon/gui_vierachs.py`, `camaddon/gui_vierachs_operation.py`,
  `camaddon/vierachs_operation.py`, `camaddon/job_schnittwerte.py`,
  `translations/de.json`, `translations/en.json`, `help/de/vierachs.html`,
  `help/en/vierachs.html`, `tests/gui/szenario_vierachs_aendern.py` (neu),
  `tests/test_job_schnittwerte.py`, `tests/test_vierachs_operation.py`,
  `docs/spezifikation_vierachs.md` (V3h), `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Doppelklick auf „Rundum schruppen“ öffnet Schritt 2 mit Fräser, Einsatz und
Werten der Operation, und „Übernehmen“ ändert sie als einen Schritt Rückgängig.

### DONE
- Doppelklick, Kontextmenü „Bearbeiten“ oder Knopf „4-Achs-Bearbeitung“ mit
  gewählter Operation (oder ihrem Job) öffnen den Assistenten zum Ändern:
  Kopf „„Rundum schruppen T1“ ändern“, Werkstoff wie am Controller gemerkt,
  Fräser und Einsatz des Controllers, die Felder leer, wo die Werte dem
  Vorschlag gleichen; der Knopf heißt „Übernehmen“, „Zurück“ und der Haken
  sind aus. Fehlt der Fräser der Operation in der Auswahl, sagt es eine rote
  Zeile.
- „Übernehmen“ (in einem Befehl, wie „Anlegen“): `controller_fuer` gibt der
  Operation ihren Controller zurück, wenn der Fräser derselbe ist und keine
  andere Operation ihn benutzt (Drehzahl, Vorschub, Name aus dem Einsatz),
  sonst einen neuen; der alte geht, wenn ihn keine Operation mehr benutzt.
  `aendere` setzt Controller und Werte; der vorgeschlagene Name folgt dem
  Werkzeug, ein eigener bleibt. „Abbrechen“ ändert nichts.
- Hilfe (de/en) „Nachträglich ändern“, Tooltip des Knopfs, Spezifikation V3h.

### TEST
- Neu `szenario_vierachs_aendern` (1.1.3 und Wochen-Build): anlegen mit T1,
  Doppelklick, T2 und Aufmaß 0,5 übernehmen (Controller „T2 Schruppen“, T1
  weg, Zustellung 1,5 vom Vorschlag), über den Knopf öffnen und abbrechen
  (nichts geändert), nur die Zustellung (derselbe Controller), zweimal Strg+Z.
- `test_job_schnittwerte` (controller_fuer: derselbe, geteilt → neu, anderes
  Werkzeug), `test_vierachs_operation` (aendere: Controller, Werte, Name),
  `test_sprache`; die übrigen 4-Achs-Szenarien in 1.1.3.

### NEXT
- Schritt 1 (Stange, Mitte, Rundachse) nachträglich ändern.

## P-2026-09-29-03 verfahrwege-bearbeiten

### EINGELESEN
- Manuel (2026-09-29, Bild „Maschine bearbeiten“, X1 ohne Verfahrweg): „bei
  maschine bearbeiten wollte ich das limit von x ändern wobei ich das nicht
  verstanden habe ... x-60 ist ja unter der drehmitte was garnicht sein kann
  ... man müsste schon auch editieren können was die maschine kann die
  verfahrwege ... wahrscheinlich hab ichs nur nicht gefunden“
- `camaddon/gui_details.py`, `camaddon/gui_maschine.py`, `camaddon/kette.py`
  (`_begrenzung`), `camaddon/verfahren.py`, `tests/gui/szenario_maschine_bearbeiten.py`,
  `tests/beispielmaschinen.py`, `help/*/achsen.html`.

### DATEIEN
- `camaddon/gui_details.py`, `camaddon/gui_maschine.py`, `translations/de.json`,
  `translations/en.json`, `help/de/achsen.html`, `help/en/achsen.html`,
  `tests/gui/szenario_maschine_bearbeiten.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer in „Maschine bearbeiten“ X1 wählt, sieht und ändert dort „Verfahrweg von“
und „bis“ (leer = keine Grenze), und ein Satz darunter sagt, wie weit der
Werkzeugplatz dabei von der Werkstückaufnahme weg ist.

### DONE
- Bei Linear und Positionieren zwei Zeilen „Verfahrweg von/bis (mm)“ bzw.
  „Schwenkbereich von/bis (°)“: die Begrenzung am Gelenk (LengthMin/Max bzw.
  AngleMin/Max samt Enable…), geändert im selben Rückgängig-Schritt wie alles
  im Fenster. Leer schaltet die Grenze aus; eine Grenze bei 0 steht darum als
  „0“ da, nicht leer wie ein unbekannter Kennwert.
- Grauer Satz darunter, nach jeder Änderung neu: gezählt wie am Gelenk (der
  Schlitten, nicht die Spitze), wo die Achse jetzt steht, wie weit P1 dabei
  von der Werkstückaufnahme weg ist (längs der Achse) und was es an den
  Grenzen sind; die Spitze mit Werkzeug zeigt „Auf der Maschine prüfen“.
- Hilfe „Achsen“ (de/en): der Satz „trägst du nicht hier ein“ ersetzt.

### TEST
- `szenario_maschine_bearbeiten` (1.1.3 und Wochen-Build): X1 zeigt 0 … 200,
  −50 und leer ändern das Gelenk, der Satz nennt 0 mm, 85 mm und 35 mm,
  zurück auf 0 … 200; Bild `4b_verfahrweg_x1`.
- `test_sprache`, `test_hilfe`, `test_maschine`.

### NEXT
- Nachträglich ändern (Manuel 20:30: „komme ich nicht mehr in die maske
  rein“), dann V3f.

## P-2026-09-29-02 plan-nacht-29

### EINGELESEN
- Manuels Nachrichten und Bilder vom 2026-09-29 abends (Test in FreeCAD 1.1.4
  mit 0.26.0): „warum sind die werkzeugwege da so seltsam ? ... haben wir eine
  rohteil und fertigteil vergleich in der ‚simualtion‘ ... bei mir fährt der
  fräser ausschlieslich oben entlang über dem bauteil“, Maschine zuerst,
  Ausspannlänge (Teil + Fräser + Sicherheitsabstand), alle Abstände
  einstellbar, Verfahrwege in „Maschine bearbeiten“, TCP/TCPM, „die
  wegberechnung sehr sehr sehr extrem gut machen .. und am besten sehr
  variabel“; „mach das alles ich geh ins bett .. bis morgen is fertig !“
- `docs/spezifikation_vierachs.md`, `docs/spezifikation_simulation.md`,
  `docs/spezifikation_maschine_aus_baugruppe.md`.

### DATEIEN
- `docs/spezifikation_vierachs.md` (V3f, V3g, „Entschieden“),
  `docs/spezifikation_simulation.md` (4e), `docs/spezifikation_maschine_aus_baugruppe.md`
  (Verfahrwege im Fenster), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikationen nennen, was heute Nacht gebaut wird, mit Manuels Worten
und einem Klickweg je Stufe.

### DONE
- Befund zu „fährt ausschließlich oben entlang über dem Bauteil“: Auf Manuels
  Maschine stand X1 an der Grenze −60 mm (Bild: „X1 −60,00 mm (am Anschlag)“,
  die Bahn braucht −109 … −73 mm) – das Werkzeug kam nicht ans Teil. Dass X1 der
  Schlitten ist (0 = wie gebaut), nicht die Spitze, sieht man im Fenster nicht
  → 4e.
- Geplant, in dieser Reihenfolge: Verfahrwege im Fenster „Maschine
  bearbeiten“; V3f (Maschine zuerst, Überlauf, Abstand zum Futter,
  Ausspannlänge); 4e (Kinematik-Kern, Spitze im Abspieler, Überschreitungen mit
  der Spitze, TCPM wählbar); V3g (Rohteil und Fertigteil in der Simulation).
  Y-Achse: mit V4/V5.

### TEST
- Nur Doku.

### NEXT
- Verfahrwege im Fenster „Maschine bearbeiten“.

## P-2026-09-29-01 freecad-1-1-4-vergleich

### EINGELESEN
- Manuel (2026-09-29): „freecad 1.1.4 is raus gekommen .. kannst du schauen ob
  immernoch alles gut funktiniert“.
- `docs/arbeitsregeln.md` (Abschnitt 9), `scripts/testumgebung_einrichten.sh`.
- FreeCAD-Quelltext, Tags 1.1.3 und 1.1.4 (`git diff 1.1.3 1.1.4`).

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (zuletzt geprüfte Versionen),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Stand steht, was an 1.1.4 geprüft ist und was noch fehlt.

### DONE
- **Testumgebung heben ging nicht:** conda-forge hat 1.1.4 noch nicht (neueste
  stabile dort: 1.1.3, auch mit frischem Index). Die Release-Dateien bei GitHub
  (AppImage) sind in der Cloud-Umgebung gesperrt, nur Git geht.
- **Quelltext verglichen:** 87 Dateien zwischen 1.1.3 und 1.1.4, keine in CAM,
  Assembly, PartDesign oder Path. Geändert: TechDraw, FEM (u. a. sichere Pfade
  beim Entpacken, `FileInfo::safeArchiveEntryPath`), BIM, Draft, eine Zeile
  Sketcher; in der Oberfläche die FPS-Anzeige, Bilder aus der 3D-Ansicht (Qt ≥
  6.9 gespiegelt, Offscreen-Format), graue Einträge im Baum, das Speichern der
  Werkzeugleisten-Zustände, Standardfarben mit Alpha. Die Pakete bauen auf
  dieselben Bibliotheken wie 1.1.3 (nur die Versionsnummer geändert). Nichts
  davon berührt, was das Addon aufruft (`appendToolbar` im Arbeitsbereich,
  Coin-Knoten, CAM-Operationen, Assembly-Gelenke).
- Nicht geändert: „derzeit 1.1.3“ in Arbeitsregeln und CHATSTART – das kommt mit
  dem vollen Lauf.

### TEST
- Kein Lauf in 1.1.4 (nicht installierbar, siehe oben). Nur der Vergleich des
  Quelltexts.

### NEXT
- Sobald conda-forge 1.1.4 hat: `scripts/testumgebung_einrichten.sh`,
  `scripts/alle_tests.sh`, dann „derzeit 1.1.4“ in Arbeitsregeln und CHATSTART.

## P-2026-09-27-55 version-0-26-0

### EINGELESEN
- `package.xml`, `README.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/spezifikation_vierachs.md` (V3).

### DATEIEN
- `package.xml` (0.26.0), `README.md` (4-Achs-Bearbeitung),
  `docs/STATUS_SNAPSHOT.md` (W-003), `docs/spezifikation_vierachs.md` (V3a–V3c
  gebaut), `docs/archiv/DEV_PROMPT_HISTORY.md`
- `tests/gui/szenario_vierachs_rohteil.py` (nur black)

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.26.0 an; README und Stand nennen „Rundum
schruppen“ und das Prüffenster für 4-Achs-Bahnen.

### DONE
- Version 0.26.0 für P-2026-09-27-46 bis -54: „Rundum schruppen“ (Hüllfläche,
  Bahn, Operation, Schritt 2 im Assistenten), das Prüffenster für 4-Achs-Bahnen,
  die schnellere Kollisionsprüfung, der Rückzug im Eilgang, die
  Beispiel-Drehmaschine.
- README: der Punkt „4-Achs-Bearbeitung“ mit Schritt 2 und dem Prüffenster.
- Stand: W-003 mit V1, V2a, V2c und V3 fertig; offen V2b, V4 bis V7 und die Frage
  an Manuel, wie weit das Teil aus dem Futter ragen soll.
- Spezifikation: V3a bis V3c als gebaut vermerkt (P-46 bis -48).
- black: eine Zeile in `szenario_vierachs_rohteil.py` aus P-49 zusammengezogen
  (der Text wurde dort kürzer) – daran scheiterte der erste volle Lauf.

### TEST
- Voller Lauf `scripts/alle_tests.sh` in FreeCAD 1.1.3 und im Wochen-Build: grün
  (EXIT 0) – black und ruff, 132 Prüfungen und Szenarien ok, in 1.1.3 der Export
  übersprungen (gibt es dort nicht).

### NEXT
- Push, Manuel berichten: was er klicken soll und was er sehen muss.

## P-2026-09-27-54 vierachs-pruefen

### EINGELESEN
- Manuels Test (2026-09-27): „hier bewegt sich nun in der simulation das werkzeug
  das zur z achse senkrecht steht mittig am pfad entlang .. und kollision wird hier
  auch nicht erkannt“.
- `docs/spezifikation_vierachs.md` (V3e), `docs/spezifikation_simulation.md` (4,
  4b), `camaddon/reichweite.py`, `camaddon/abfahren.py`, `camaddon/gui_abfahren.py`.
- FreeCAD 1.1.3: `PathSegmentWalker` (der Punkt wird um −A/−B/−C gedreht
  gezeigt; Drehungen über 360° je Satz als Gerade).

### DATEIEN
- `camaddon/reichweite.py` (ohne TCPM, G93 im Lesen der Bahn, Hinweis
  `rw.werkzeug_radial`, `richtung_text`)
- `camaddon/abfahren.py` (Zeit nach G93, `am_werkstueck`)
- `camaddon/gui_abfahren.py` (Bahn am Werkstück)
- `camaddon/vierachs_bahn.py` (2 mm vor dem Futter)
- `translations/de.json`, `translations/en.json`
- `help/de/reichweite.html`, `help/en/reichweite.html`, `help/de/vierachs.html`,
  `help/en/vierachs.html`
- `tests/test_vierachs_pruefen.py` (neu), `tests/test_reichweite.py`,
  `tests/test_vierachs_bahn.py`, `tests/test_vierachs_operation.py`,
  `tests/gui/szenario_vierachs_schruppen.py`
- `docs/spezifikation_simulation.md`, `docs/spezifikation_vierachs.md`,
  `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine, Welle Ø 60 × 100, „4-Achs-Bearbeitung“ → Stange Ø 80 →
„Weiter“ → „Rundum schruppen“ mit T1 (Schaftfräser D12, 125 mm ab Spindelnase) →
„Anlegen“. „Auf der Maschine prüfen“: „Alle Achsen bleiben in ihren Grenzen.“,
kein Hinweis zur Werkzeuglage; die Bahn läuft als Spirale um das Teil, das
Werkzeug auf P1 zeigt radial darauf, C dreht; „Kollision prüfen“ → „Nichts
berührt sich, nichts kommt näher als 1,00 mm.“

### DONE
- **Ohne TCPM:** Das Prüffenster löste die Linearachsen für jede Stellung der
  Rundachsen am mitgedrehten Werkstück (wie eine Steuerung mit TCPM) – X, Y und Z
  der Bahn kreisten mit C. FreeCAD und die Bahn von „Rundum schruppen“ meinen es
  anders: X, Y, Z sind die Achsen der Maschine, die Rundachse dreht das Werkstück
  darunter. Jetzt einmal je Werkzeug gelöst, mit den Rundachsen auf 0 (der
  Revolver in Arbeitsstellung); `stellungen()` ebenso.
- **G93:** Zwischen G93 und G94 ist F der Kehrwert der Zeit (FreeCAD führt ihn
  ÷ 60) – ein Satz dauert 1 ÷ F Minuten, geteilte Sätze (je 1° Rundachse) jeder
  seinen Anteil, ein Bogen erst an seinem Ende.
- **Bahn am Werkstück:** Das Bild zeigte die Punkte ungedreht – eine Gerade am
  Teil, die sich mit C drehte. Jetzt je Station die Spitze in Koordinaten des
  Werkstücks über die Kette der Maschine (`Abfahrt.am_werkstueck`): eine Spirale
  um das Teil, genau wie FreeCAD (der Punkt um −C gedreht, geprüft).
- **Hinweis zur Werkzeuglage:** Bei „Rundum schruppen“ umgekehrt zum Hinweis aus
  P-43: Zeigt das Werkzeug nicht radial aus der Richtung, für die die Bahn
  gerechnet ist, sagt es der Satz „… radial aus +X zur Achse zeigt – T2 sitzt auf
  P2 aber anders … Nimm einen radialen Platz, der aus +X zeigt.“
- **2 mm vor dem Futter:** Mit 1 mm meldete die Kollisionsprüfung jede Bahn als
  „auf 1,00 mm nahe“ (Warnabstand 1 mm).
- Beispiel mit 125 mm Werkzeuglänge: Mit 50 mm stößt auf der
  Beispiel-Drehmaschine der Revolver ans Futter (das Teil ragt nur um den Abstich
  heraus) – der Test prüft beides.

### TEST
- `tests/test_vierachs_pruefen.py` (neu): Welle Ø 40 × 30 in der Stange Ø 50 –
  keine Hinweise, in den Grenzen; an sieben Stationen mit C die Linearachsen wie
  ohne C, C1 wie programmiert, der Punkt am Werkstück wie in FreeCAD; C bis zum
  Ende der Spiralen; Dauer = Zeit im Vorschub (G93) + Eilgänge; Kollision mit
  125 mm ohne Befund (eine Lage, 1024 Stationen, 2 s), mit 50 mm Revolver am
  Futter; T2 (axial) → Hinweis.
- `tests/test_reichweite.py`: 5-Achs-Punkte ohne TCPM.
- `tests/gui/szenario_vierachs_schruppen.py` in FreeCAD 1.1.3: ok; Screenshots
  angesehen (`3_abfahren_c_gedreht`: Spirale um die Welle, Werkzeug radial auf P1;
  `4_kollision_frei`: grün „Nichts berührt sich …“, 24:20,7 Laufzeit, Z1 −187 …
  −83 mm).
- Alle Prüfungen (`scripts/tests_ausfuehren.sh`) auf dem Stand dieses Patches in
  1.1.3 grün; die geänderten Prüfungen auch im Wochen-Build.

### NEXT
- Version, voller Lauf, Push; Manuel fragen, wie weit das Teil für die
  4-Achs-Bearbeitung aus dem Futter ragen soll.

## P-2026-09-27-53 kollision-bis-station

### EINGELESEN
- `camaddon/kollision.py` (P-2026-09-27-50), Messung an „Rundum schruppen“.

### DATEIEN
- `camaddon/kollision.py` (genau nur, wenn der Schritt sonst vor der Station endet)
- `docs/spezifikation_simulation.md` (4c), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Kollision prüfen“ für „Rundum schruppen“ (Welle Ø 40 × 30, Stange Ø 50, zwei
Lagen) ist in wenigen Sekunden fertig; Befunde wie vorher.

### DONE
- **Befund:** Nach P-50 rechnete die Prüfung je Station noch einmal genau – das
  Paar Schneide/Teil, 0,35 mm auseinander, machte mit seiner Schranke den
  kürzesten Schritt, und das Paar, das den Schritt begrenzt, wird genau
  gerechnet. Dabei reichte der Schritt auch mit der Schranke bis zur nächsten
  Station: Die Welle ist rund um C, die Schneide rückt je Station nur Hundertstel
  in X und Z.
- Jetzt: Reicht der Schritt schon mit der Schranke bis zur nächsten Station, rechnet
  es nicht genau. Befunde ändern sich dadurch nicht – für die zählt weiter jede
  Schranke, die nicht über dem Warnabstand liegt.
- Gemessen (FreeCAD 1.1.3, mit dem Stand von V3e: 2 mm vor dem Futter): eine Lage
  (1024 Stationen) 7,5 s → 2,1 s; zwei Lagen (4087 Stationen) 4,6 s, ohne Befund.
  Vor P-50 lief dieselbe Prüfung über 20 Minuten.

### TEST
- `tests/test_kollision.py` in FreeCAD 1.1.3 und im Wochen-Build grün.
- Alle Prüfungen (`scripts/tests_ausfuehren.sh`) auf dem Stand dieses Patches in 1.1.3 grün.

### NEXT
- V3e: Prüffenster ohne TCPM, G93, Hinweis zum radialen Werkzeug.

## P-2026-09-27-52 beispiel-drehmaschine-4achs

### EINGELESEN
- `camaddon/beispielmaschine.py` (Drehmaschine), `help/de/achsen.html`,
  `help/en/achsen.html`.
- Messung an „Rundum schruppen“ (Welle Ø 40 × 30, Stange Ø 50, Vorschlag für den
  Nullpunkt): Z1 müsste bis −188 mm, die Grenze war −100 mm.

### DATEIEN
- `camaddon/beispielmaschine.py` (Revolver ohne Fräser, `weg_z` −220)
- `help/de/achsen.html`, `help/en/achsen.html`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine laden: Der Revolver trägt an P1 und P2 nur die Halter;
„Maschine verfahren“ fährt Z1 bis −220 mm. Eine Stange aus der
4-Achs-Bearbeitung ist bis vor das Futter erreichbar.

### DONE
- **Z bis −220 mm:** P1 steht beim Bauen 195 mm vor der Spannfläche. Mit −100 mm
  kam das Werkzeug nicht an eine Stange, die mit ihrer Spannlänge im Futter
  steckt – das Prüffenster meldete „Z1 fährt … bis −188,00 mm, die Grenze ist
  −100,00 mm“. Gilt für die Beispiel-Drehmaschine und als Vorgabe in „Neue
  Maschine …“.
- **Revolver ohne Fräser:** Die Fräser an P1 und P2 (Ø 16) waren Teil des
  Revolvers. In der Kollisionsprüfung sind sie Maschine – ist das echte Werkzeug
  kürzer oder dünner, hätten sie das Teil „berührt“. Die Halter bleiben; die
  Werkzeuge zeigt das Prüffenster an ihrer Aufnahme. Die Farbe `WERKZEUG`
  entfällt.
- Befund für Manuel (nicht geändert): Mit einem kurzen Werkzeug (50 mm ab
  Halter) stößt der Revolver ans Futter, sobald der Fräser weniger als 55 mm
  (halbe Scheibe) vor der Spannfläche arbeitet – das Teil ragt beim Vorschlag
  nur um die Abstichbreite heraus. Die Kollisionsprüfung meldet es richtig
  („berühren sich „Revolver“ und „Spindel““).

### TEST
- `tests/test_beispielmaschine.py` in FreeCAD 1.1.3 und im Wochen-Build grün.
- `tests/gui/szenario_beispielmaschine.py` in 1.1.3: ok; Screenshots angesehen
  (`3b_revolverplatz`: Revolver mit Stationen und Haltern).
- Alle Prüfungen (`scripts/tests_ausfuehren.sh`) auf dem Stand dieses Patches in 1.1.3 grün.

### NEXT
- V3e: Prüffenster ohne TCPM, G93, Hinweis zum radialen Werkzeug.

## P-2026-09-27-51 eilgang-nach-vorschub

### EINGELESEN
- `camaddon/kollision.py`, `tests/test_kollision.py`.
- Messung an „Rundum schruppen“: „kommen sich im Eilgang die Schneide von T1 und
  das Teil auf 0,32 mm nahe“ – beim Rückzug nach der letzten Lage.

### DATEIEN
- `camaddon/kollision.py` (`_zaehlt`, Abstand am Anfang des Eilgangs)
- `tests/test_kollision.py` (Rückzug vom Taschenboden, Eilgang auf den Boden)
- `docs/spezifikation_simulation.md` (4c), `help/de/reichweite.html`,
  `help/en/reichweite.html`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
An der Beispiel-Fräse: „G1 Z5“ auf den Boden der Tasche, dann „G0 Z30“ →
„Kollision prüfen“ meldet nichts. „G1 Z10“, dann „G0 Z5“ (im Eilgang auf den
Boden) → „berühren sich im Eilgang die Schneide von T1 und das Teil“.

### DONE
- **Befund:** Ein Eilgang beginnt, wo der Vorschub aufhörte – dort steht die
  Schneide oft am fertigen Teil (Boden einer Tasche, Wand einer Kontur, das
  Aufmaß beim Schruppen). Die Prüfung sah schon am Anfang des Eilgangs die
  Schneide am Teil und meldete rot „berühren sich im Eilgang“ – bei jeder
  Tasche, die am Boden endet und im Eilgang hochfährt (nachgestellt an der
  Beispiel-Fräse).
- Jetzt: Beginnt ein Eilgang dort, wo ein Vorschub aufhörte, zählt die Schneide
  gegen das Teil erst, wenn sie ihm näher kommt als am Anfang. Ein Rückzug ist
  so kein Befund, ein Eilgang zum Teil hin schon. Schaft, Halter und
  Maschinenteile zählen wie bisher.
- Bewusst so gelassen: Fährt ein Eilgang nach dem Vorschub im selben Abstand am
  Teil entlang, meldet es nichts – so nah war die Schneide im Vorschub auch.

### TEST
- `tests/test_kollision.py` in FreeCAD 1.1.3 und im Wochen-Build grün; die neuen
  Fälle schlugen vor der Änderung fehl (Rückzug vom Boden: „berühren sich im
  Eilgang“, von 0,3 mm darüber: „auf 0,30 mm nahe“).
- Alle Prüfungen (`scripts/tests_ausfuehren.sh`) auf dem Stand dieses Patches in 1.1.3 grün.

### NEXT
- Beispiel-Drehmaschine für die 4-Achs-Prüfung, dann V3e.

## P-2026-09-27-50 kollision-schneller

### EINGELESEN
- `camaddon/kollision.py`, `camaddon/verfahren.py`, `docs/spezifikation_simulation.md`
  (4c).
- Messung an „Rundum schruppen“ auf der Beispiel-Drehmaschine (Welle Ø 40 × 30 in
  der Stange Ø 50, zwei Lagen, 4207 Stationen): „Kollision prüfen“ lief nach 20
  Minuten noch.

### DATEIEN
- `camaddon/kollision.py` (Schritte je Paar, Schranken, rund um die Achse)
- `camaddon/verfahren.py` (`achslage`)
- `tests/test_kollision.py` (rund um die Achse)
- `docs/spezifikation_simulation.md` (4c), `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Kollision prüfen“ für eine Bahn rundum (tausende Grad C) ist nach etwa einer
Minute fertig statt nach über 20; an der Fräse findet es dasselbe wie vorher.

### DONE
- **Befund:** Jeder Schritt rechnete mit der Größe der ganzen Maschine – je Grad
  einer Drehachse 1° × die Diagonale über alles, für jedes Paar. Eine Bahn rundum
  dreht tausende Grad; so wurden es hunderttausende Stellen, jede mit
  `distToShape` für alle nahen Paare.
- **Je Paar:** Wie weit sich zwei Körper gegeneinander bewegen, zählt nur mit den
  Achsen, die genau einen von beiden fahren; eine Drehachse mit dem weitesten
  Abstand des Körpers von ihr (Ecken des Hüllquaders), wenn sie ihn unmittelbar
  trägt – sonst wie bisher grob. Ist der Körper **rund um die Achse** (um zwei
  krumme Winkel gedreht deckt er sich mit sich selbst: Hüllquader, dann Volumen
  der Schnittmenge), bewegt er sich mit ihr gar nicht – das Futter der
  Beispiel-Drehmaschine, eine Welle.
- **Genau nur, wo nötig:** Statt Hüllquader + 5 mm eine Schranke nach unten – der
  Abstand der Hüllquader oder der zuletzt genau gerechnete minus dem Weg seither,
  auch über Stationen hinweg, solange die Maschine stetig fährt und die Operation
  bleibt. `distToShape` nur, wenn die Schranke nicht über dem Warnabstand liegt
  oder das Paar den nächsten Schritt am kürzesten macht; was am Ende eines
  Abschnitts genau gerechnet ist, gilt am Anfang des nächsten. `GENAU_AB` entfällt.
- Stecken zwei in einer Operation schon ineinander, rechnet es sie dort nicht
  weiter – schlimmer wird der Befund nicht (vorher bei jeder Stelle 5 ms für
  Revolver gegen Spindel).
- Gemessen (FreeCAD 1.1.3, Werkzeug 125 mm, ganze Bahn): vorher über 20 Minuten,
  jetzt 34,5 s (8453 Stellen); die ersten 400 Stationen 43 s → 4,6 s; mit 50 mm (Revolver
  am Futter) 400 Stationen 59 s → 4,4 s, die ganze Bahn 34,7 s.

### TEST
- `tests/test_kollision.py` in FreeCAD 1.1.3 und im Wochen-Build grün – die Fälle
  an der Fräse unverändert; neu: Futter rund, außermittig und mit Backen nicht.
- Messung wie oben (Wegwerf-Skript, nicht im Repo).
- Alle Prüfungen (`scripts/tests_ausfuehren.sh`) auf dem Stand dieses Patches in 1.1.3 grün.

### NEXT
- Eilgang ab dem Ende eines Vorschubs (falsche Meldung beim Rückzug), dann V3e.

## P-2026-09-27-49 vierachs-was-willst-du-machen

### EINGELESEN
- Manuels Wunsch (2026-09-27): „wäre cool wenn dann einfach ein fenster
  aufgeht .. was willste machen .. schruppen“.
- `docs/spezifikation_vierachs.md` (V3d), `camaddon/gui_vierachs.py`,
  `camaddon/gui_job_schnittwerte.py` (Werkstoff, Controller anlegen),
  `camaddon/job_schnittwerte.py`.
- FreeCAD 1.1.3: `App/AutoTransaction.cpp` (Wächter, `closeActiveTransaction`),
  CAM `Path/Tool/toolbit/models/base.py` und `Path/Tool/shape/doc.py`
  (verstecktes Dokument beim Anlegen eines ToolBits); Wochen-Build:
  Transaktionen je Dokument (`AutoTransaction(doc, name)`).

### DATEIEN
- `camaddon/gui_vierachs.py` (Schritt 2, `_im_befehl`, `_neuer_job`)
- `camaddon/job_schnittwerte.py` (`controller_ohne_transaktion`,
  `controller_weg`; ToolBit ausgeblendet wie bei FreeCAD)
- `camaddon/vierachs_operation.py` (`bahn_fuer` für die Vorschau)
- `camaddon/vierachs_achsen.py` (`quer`: hat die Maschine Y?)
- `translations/de.json`, `translations/en.json`
- `help/de/vierachs.html`, `help/en/vierachs.html`
- `tests/gui/szenario_vierachs_schruppen.py` (neu),
  `tests/gui/szenario_vierachs_rohteil.py`, `tests/gui/szenario_vierachs_maschine.py`,
  `tests/test_vierachs_achsen.py`
- `docs/spezifikation_vierachs.md`, `docs/aufbau.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle, Stirnfläche, „4-Achs-Bearbeitung“, Stange Ø 80 → der Knopf heißt
„Weiter“; danach „Was willst du machen?“ mit „Rundum schruppen“, T1 und
„Schruppen“ vorgewählt, grau „→ 5 Lagen (Ø 80,0 mm → Ø 60,…)“. „Anlegen“:
Controller „T1 Schruppen“ und „Rundum schruppen T1“ im Job; zwei Strg+Z nehmen
alles zurück.

### DONE
- Schritt 2 „Was willst du machen?“: Haken „Rundum schruppen“, Werkstoff (vom
  Rohteil oder zuletzt benutzt), Fräser (Schaft-, Torus-, Kugel-, Nuten-,
  Planfräser mit Schnittwerten), Einsatz (Schruppen vor), n und vf grau,
  Zustellung (ap), Vorschub je Umdrehung (ae, höchstens D), Schlichtaufmaß
  (0,3); Vorschau der Lagen, rechnet 0,4 s nach der letzten Eingabe wie die
  Operation; Hinweis „X ist der Radius … DIAMOF … G93“ bei C; „Zurück“;
  „Werkzeugverwaltung …“ (nach dem Speichern neu gelesen).
- OK heißt in Schritt 1 „Weiter“, in Schritt 2 „Anlegen“.
- Befund: FreeCAD 1.1 schließt die offene Transaktion, sobald CAM ein ToolBit
  anlegt (es öffnet und schließt ein verstecktes Dokument) – auch beim
  Vorgabe-Controller eines neuen Jobs. Das hat schon Stufe V1 getroffen: Ein
  anderes Teil angeklickt, blieb nach Abbrechen etwas stehen. Abhilfe
  `_im_befehl`: in 1.1 als FreeCAD-Befehl ausführen, die Transaktion darin
  öffnen und mit `setActiveTransaction(…, True)` offen halten; der Wochen-Build
  führt Transaktionen je Dokument, dort direkt.
- Deshalb zwei Schritte Rückgängig: Job und Stange, dann Controller und
  Operation („Rundum schruppen anlegen“). Geht das Schruppen nicht, bleibt das
  Fenster mit dem Grund offen; Abbrechen nimmt dann auch Job und Stange
  zurück.
- Der Vorgabe-Controller des neuen Jobs fliegt heraus (D-30); ToolBits aus
  der Werkzeugverwaltung sind im Dokument ausgeblendet – wie bei FreeCAD, sonst
  stand der Fräser als Körper am Nullpunkt.

### TEST
- `szenario_vierachs_schruppen` (neu), `szenario_vierachs_rohteil`,
  `szenario_vierachs_maschine`, `szenario_schnittwerte_job`,
  `szenario_schnittwerte_pruefen` in 1.1.3 und im Wochen-Build ok;
  Screenshots angesehen: Schritt 2 mit „→ 5 Lagen (Ø 80,0 mm → Ø 60,6 mm)“,
  die Bahn in Spiralen um die Welle.
- `test_vierachs_achsen`: Drehmaschine mit Y → quer, ohne Y (Testdrehmaschine)
  → nicht.
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- V3e: Prüffenster ohne TCPM, G93, radiales Werkzeug; dann Version und Push.

## P-2026-09-27-48 vierachs-operation

### EINGELESEN
- `docs/spezifikation_vierachs.md` (Abschnitt 10, Stufe V3c).
- FreeCADs `Path/Op/Base.py` in 1.1.3 und im Wochen-Build (`ObjectOp`,
  `DoNotSetDefaultValues`, `execute`, `Workplane`),
  `Path/Post/scripts/linuxcnc_post.py` (F in jedem Satz: `OUTPUT_DOUBLES`
  ist Standard).
- `camaddon/maschine.py` (Proxys), `camaddon/verfahren.py` (`plusrichtung`).

### DATEIEN
- `camaddon/vierachs_operation.py` (neu), `camaddon/gui_vierachs_operation.py` (neu)
- `camaddon/vierachs_achsen.py` (`drehsinn`, `radial()`)
- `camaddon/vierachs_bahn.py` (`hinten_frei`, Texte über `tr`)
- `camaddon/vierachs_huelle.py` (vernetzt eine Kopie ohne Netz)
- `camaddon/job_schnittwerte.py` (`EINSATZ_NACH_OPERATION`: Schruppen)
- `translations/de.json`, `translations/en.json` (`vo.*`, `vb.*`)
- `tests/test_vierachs_operation.py` (neu), `tests/test_vierachs_achsen.py`,
  `tests/test_vierachs_bahn.py`
- `docs/aufbau.md` (dazu der fehlende Eintrag `vierachs_achsen.py`),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Job einer Welle aus dem Assistenten lässt sich „Rundum schruppen T1“
anlegen, ohne dass FreeCAD nachfragt; sie rechnet fünf Lagen, ihre Bahn
steht zwischen G93 und G94 mit C, nach Speichern und Laden ist sie gleich,
und der Postprozessor schreibt jeden Satz mit F.

### DONE
- Operation `RundumSchruppen` (erbt FreeCADs `ObjectOp`): Controller und
  Kühlmittel, keine Höhen in Z; Eigenschaften in der Gruppe „4-Achs“
  (Rundachse, Stangenachse, Werkzeugrichtung, Drehsinn, Quer auf null,
  Zustellung, Vorschub je Umdrehung, Aufmaß, Sicherheitsabstand, Lagen – nur
  lesen). Beim Neuberechnen: Modell, runde Stange und Spannlänge des Jobs →
  Bahn; geht es nicht, ein Satz in der Konsole und als Kommentar in der Bahn
  (ohne Umlaute).
- `lege_an()` ohne eigene Transaktion, mit `DoNotSetDefaultValues` (sonst
  fragte FreeCAD nach Job und Controller); Anzeige mit Symbol, Doppelklick
  öffnet nichts.
- Stangenachse mit Drehsinn (von der Maschine: `plusrichtung` gegen die
  Stange; ohne Maschine +1, wie FreeCADs Bahnanzeige) und `radial()`: bei A
  und B von oben, bei C aus +X.
- Befund: Eine Form behält ein vorhandenes feineres Netz – die Bahn hing
  davon ab und war nach dem Laden kürzer (5073 statt 5972 Befehle). Jetzt
  wird eine Kopie ohne Netz vernetzt.

### TEST
- `test_vierachs_operation` in 1.1.3 und im Wochen-Build: angelegt, 5 Lagen,
  G0 X42 / G0 X42 Y0 Z9 C0 / G93 … G94, über dem Teil X ≥ 30,3, hinten 1 mm
  vor dem Futter; Speichern und Laden gleich; LinuxCNC-Post (Wochen-Build:
  `linuxcnc_legacy_post`): 5057 Sätze mit F, etwa „G1 X38.000 Z7.800
  C-90.000 F25.125“; ohne Vorschub und mit Quader-Rohteil ein Satz statt der
  Bahn.
- `test_vierachs_achsen`: Drehsinn der Beispiel-Drehmaschine nachgemessen
  (C1 auf +90°, X des Futters zeigt dann nach +Y: +1).
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- V3d: Schritt „Was willst du machen?“ im Assistenten.

## P-2026-09-27-47 vierachs-schruppbahn

### EINGELESEN
- `docs/spezifikation_vierachs.md` (Abschnitt 9, Stufe V3b).
- FreeCADs `PathSegmentWalker.cpp` in 1.1.3: Ein Satz mit A/B/C wird nach dem
  Winkel modulo 360° unterteilt – über mehrere Umdrehungen zeigt 1.1.3 eine
  Gerade (im Wochen-Build behoben).

### DATEIEN
- `camaddon/vierachs_bahn.py` (neu)
- `camaddon/vierachs_huelle.py` (`bei()` Punkt für Punkt)
- `tests/test_vierachs_bahn.py` (neu)
- `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Für eine Welle Ø 60 in der Stange Ø 80 (ap 2, Aufmaß 0,3) entstehen fünf
Lagen bis Ø 60,6; die Spirale läuft von vorne bis 1 mm vor das Futter und kommt
dem Teil nirgends näher als das Aufmaß – auch zwischen den Punkten.

### DONE
- `schruppen()`: Lagen R_Stange − k · ap bis zum tiefsten Punkt über dem
  Teil; je Lage eine Spirale (Steigung = Vorschub je Umdrehung) von vorne –
  Fräser ganz vor der Stange – bis 1 mm vor die Spannfläche, die Spitze auf
  max(Lage, Hüllfläche mit R + Aufmaß, plus Aufmaß, Toleranz der Vernetzung
  und 0,005 mm). Hinter dem Teil ohne Treffer bleibt sie auf dem
  Stangenradius, der Achse nie näher als der Fräserradius. Zwischen den Lagen
  radial hinaus und im Eilgang nach vorne; die nächste Spirale beginnt beim
  Winkel, wo die letzte endete.
- Gerade Stücke fallen zusammen, aber höchstens 90° je Satz (FreeCAD 1.1.3).
- `befehle()`: Path-Befehle – zuerst radial auf Sicherheitsabstand, dann an
  den Anfang (quer auf 0), G93, die Sätze mit F = Vorschub ÷ Weg ÷ 60 (CAM
  rechnet in mm/s), G94. X/Y/Z im Rahmen der Maschine, die Rundachse
  −drehsinn · φ. `dauer()`: Zeit im Vorschub.
- Hinweis `vb.hinten_frei`, wenn der Fräser das hintere Ende des Teils nicht
  erreicht; ValueError für Werte, die nicht gehen.

### TEST
- `test_vierachs_bahn` in 1.1.3 und im Wochen-Build: Welle 5 Lagen (38, 36, 34,
  32, dann am Teil), Exzenter 17 Lagen mit mindestens 0,025 mm Luft über dem
  Aufmaß auch zwischen den Punkten, Befehle für C und A, Drehsinn −1, ohne Y,
  Fehlerfälle.
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- V3c: die Operation „Rundum schruppen“.

## P-2026-09-27-46 vierachs-huelle

### EINGELESEN
- `docs/spezifikation_vierachs.md` (Abschnitte 3 und 9, Stufe V3a).
- `camaddon/vierachs_rohteil.py` (Achsen, Tessellierung).

### DATEIEN
- `camaddon/vierachs_huelle.py` (neu)
- `tests/test_vierachs_huelle.py` (neu)
- `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Für einen radialen Schaftfräser sagt die Hüllfläche je Stelle a und Winkel φ,
wie nah die Spitze der Stangenachse kommt, ohne das Teil zu verletzen –
höchstens die Toleranz der Vernetzung unter der Formel, nie darüber.

### DONE
- `vernetze(form)`: das Teil als Netz (numpy). `schaftfraeser(...)`: je Winkel
  für alle a zugleich – je Kante der höchste Punkt im Kreis der Stirn (Ende
  oder Schnitt mit dem Kreis, quadratische Gleichung ohne Auslöschung), je
  Dreieck die höchste Stelle des Kreises auf seiner Ebene, wenn sie im Dreieck
  liegt. Kanten und Dreiecke ganz hinter der Achse zählen nicht.
- `Huelle.sicher()`: der höchste Nachbar rundum; `bei(a, j)`: der höhere der
  beiden Rasterpunkte daneben – so liegt die wahre Hüllfläche zwischen den
  Rasterpunkten darunter.
- Eine berührende Stirn (genau tangential) zählt immer: Sie rechnet 1e-9 mm
  größer, sonst entschied das Rundungsrauschen.

### TEST
- `test_vierachs_huelle` in 1.1.3 und im Wochen-Build: Zylinder Ø 60 (höchstens
  0,0093 mm unter der Formel), Exzenter (0,0069), Sechskant (genau), Welle mit
  Absatz (am Absatz bei −56,0, davor nicht; vorne bis a = R), längs X gleich wie
  längs Z, Welle mit Nocken 481 × 360 Punkte in 0,5 s.
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- V3b: Schruppbahn (`camaddon/vierachs_bahn.py`).

## P-2026-09-27-45 plan-rundum-schruppen

### EINGELESEN
- Manuels Test (2026-09-27): „dann passiert ja weiter nichts ... keinerlei
  abfrage vonwegen welches werkzeug .. und keine generierung der
  werkzeugwege .. also wäre cool wenn dann einfach ein fenster aufgeht .. was
  willste machen .. schruppen“.
- `docs/spezifikation_vierachs.md` (Abschnitte 9, 10, 13),
  `docs/spezifikation_simulation.md` (Abschnitt 4), FreeCADs
  `src/Mod/CAM/App/PathSegmentWalker.cpp` (`setYawPitchRoll(-c, -b, -a)`).

### DATEIEN
- `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation sagt, in welchen Schritten „Rundum schruppen“ kommt und
wie man es am Ende klickt.

### DONE
- Neue Stufe V3 „Rundum schruppen“ in fünf Schritten: Hüllfläche für den
  Schaftfräser (V3a), Bahn mit Lagen und Spirale, G93 (V3b), Operation (V3c),
  Schritt „Was willst du machen?“ im Assistenten (V3d), Prüffenster ohne TCPM
  (V3e). Flächen wählen, Schlichten, Glättung und Feinschliff rücken als V4
  bis V7 nach.
- Befund: Das Prüffenster rechnet Rundachsen bisher wie mit TCPM (Punkte am
  mitgedrehten Teil); FreeCADs Bahnanzeige und eine Steuerung ohne TCPM lassen
  X, Y und Z im Maschinenrahmen. V3e gleicht das an.

### TEST
- Nur Doku.

### NEXT
- V3a: `camaddon/vierachs_huelle.py`.

## P-2026-09-27-44 version-0-25-2

### EINGELESEN
- `package.xml`.

### DATEIEN
- `package.xml` (0.25.2), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.25.2 an – mit dem Hinweis zur Werkzeuglage
(P-2026-09-27-43).

### DONE
- Version 0.25.2.

### TEST
- Die Einzeltests zu P-43 in beiden Versionen ok; der Volllauf folgt.

### NEXT
- Volllauf; 4-Achs-Bearbeitung weiter.

## P-2026-09-27-43 hinweis-werkzeug-quer

### EINGELESEN
- Manuels Test: „hier bewegt sich nun in der simulation das werkzeug das zur
  z achse senkrecht steht mittig am pfad entlang .. das ist natürlich nicht
  sinnvoll wenn man eine 4 achs beareitung hat“.
- `camaddon/reichweite.py` (`_pruefe_operation`, `_z_verkehrt`),
  `tests/test_reichweite.py` (Drehmaschine P1/P2), `help/*/reichweite.html`.

### DATEIEN
- `camaddon/reichweite.py` (`QUER`, `_werkzeug_quer`, Hinweis)
- `translations/de.json`, `translations/en.json` (`rw.werkzeug_quer`)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_reichweite.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Prüft man eine normale CAM-Operation mit einem Werkzeug auf einem radialen
Platz, sagt ein Hinweis, dass die Bahn für ein Werkzeug längs Z gerechnet
ist; auf einem axialen Platz und an der Fräse nicht.

### DONE
- Steht die Werkzeugaufnahme (in Grundstellung der Drehachsen) mehr als etwa
  25° quer zu Z des Jobs, sagt ein Hinweis: „„Tasche“: Die Bahn ist für ein
  Werkzeug längs Z gerechnet, T1 sitzt auf P1 aber quer dazu – so gefahren,
  passt sie nicht zum Teil. Mit einem Platz längs Z (axial) passt sie; rundum
  mit radialem Werkzeug braucht es eine eigene Bahn (4-Achs-Bearbeitung).“

### TEST
- `test_reichweite` in 1.1.3 ok: an der Beispiel-Drehmaschine genau ein Platz
  radial – dort der Hinweis, am axialen nicht; an der Fräse keiner.
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- Die 4-Achs-Bearbeitung weiter: nach „Anlegen“ fragen, was man machen will,
  Werkzeug wählen, Bahn rundum (V3–V6).

## P-2026-09-27-42 version-0-25-1

### EINGELESEN
- `package.xml`; Manuel testet bis 17 Uhr über „Nach Updates schauen“.

### DATEIEN
- `package.xml` (0.25.1), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet 0.25.1 an – mit der Kollision „ins fertige
Teil“ (P-2026-09-27-41).

### DONE
- Version 0.25.1.

### TEST
- Die Einzeltests zu P-41 in beiden Versionen ok; der Volllauf folgt nach dem
  Push.

### NEXT
- Hinweis zur Werkzeuglage (radial gegen eine Bahn längs Z).

## P-2026-09-27-41 kollision-ins-teil

### EINGELESEN
- Manuels Test mit Bildern: Auf seiner Drehmaschine fuhr das radiale
  Werkzeug eine Bahn einer normalen Operation (für ein Werkzeug längs Z)
  quer durchs Teil – „Kollision wird hier auch nicht erkannt, da er komplett
  durchs Werkstück fährt“.
- `camaddon/kollision.py` (Paare, Schritte, `_merke`, `werkzeugkoerper`),
  `camaddon/abfahren.py` (`OperationAbfahrt`), `tests/test_kollision.py`,
  `docs/spezifikation_simulation.md` (4c), `help/*/reichweite.html`.
- Nachbau an der Beispiel-Drehmaschine: Die Prüfung ließ die Schneide gegen
  das fertige Teil im Vorschub weg („im Vorschub schneidet sie“); dazu kam
  die Beispiel-Drehmaschine in Z nicht bis ans Teil (die Reichweite meldet es,
  die Kollision rechnet an der Grenze).

### DATEIEN
- `camaddon/kollision.py` (`EINDRINGEN`, `INS_TEIL_ERLAUBT`, `KERN`, Paar
  `nur_vorschub`, Befund `ins_teil`), `camaddon/abfahren.py` (`art` der
  Operation)
- `translations/de.json`, `translations/en.json` (`kb.ins_teil`)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_kollision.py`
- `docs/spezifikation_simulation.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Fährt die Schneide im Vorschub ins fertige Teil, meldet die Kollision es rot
(„… fährt die Schneide von T1 ins fertige Teil …“); an der Wand entlang
(Abstand 0) und beim Entgraten nicht.

### DONE
- Neben der Schneide prüft die Kollision ihren Kern – die Schneide, um
  0,05 mm kleiner – gegen das fertige Teil, nur im Vorschub, nur auf
  Berührung (kein Warnabstand). Berührt der Kern das Teil, fährt die Schneide
  mehr als 0,05 mm hinein: ein roter Befund mit Satz und Stelle.
- Entgraten, Gravieren, V-Carve, Gewindefräsen, Gewindebohren und Bohren
  dürfen ins Teil – ihr Ergebnis zeigt das Modell selten.
- Der alte Fall im Test („Vorschub quer durchs volle Material: nur der
  Schaft“) meldet jetzt auch die Schneide.

### TEST
- `test_kollision` in 1.1.3 und im Wochen-Build ok: quer durchs Material im
  Vorschub → „ins fertige Teil“; an der Wand entlang nicht; Entgraten nicht.
- Nachbau an der Beispiel-Drehmaschine (Stange weiter vorn): „fährt die
  Schneide von T1 ins fertige Teil (Satz 4 …)“, dazu Revolver und Schaft.
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- Hinweis im Prüffenster, wenn die Bahn für ein Werkzeug längs Z gerechnet
  ist, das Werkzeug aber radial sitzt.

## P-2026-09-27-40 regel-pusch-jetzt

### EINGELESEN
- Manuel: „wenn ich sage pusch jetzt dann auch puschen !!“; `CLAUDE.md`;
  `camaddon/aktualisierung.py` (nur eine höhere Version wird angeboten).

### DATEIEN
- `CLAUDE.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Regel steht in CLAUDE.md: „pusch jetzt“ heißt sofort pushen; zum
Ausprobieren eine höhere Version.

### DONE
- Neue Regel über der Regel „Nach jedem Push bei GitHub selbst nachsehen“.

### TEST
- Reine Doku-Änderung, kein Testlauf.

### NEXT
- Manuels Fragen zur 4-Achs-Bearbeitung.

## P-2026-09-27-39 version-0-25-0

### EINGELESEN
- Manuels Rückmeldung: „ja doof jetzt nicht gepuscht .. heißt ich kann nichts
  testen … wenn ich sage pusch jetzt dann auch puschen !!“
- `camaddon/aktualisierung.py`: Der Update-Knopf meldet nur eine höhere
  Version in `package.xml` – alles seit 0.24.0 (P-2026-09-27-07 bis -38)
  war auf GitHub, kam über den Knopf aber nicht an.
- `package.xml`, `README.md`, der Versionssprung P-2026-09-26-99.

### DATEIEN
- `package.xml` (0.25.0, Datum, Beschreibung), `README.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Nach Updates schauen“ bietet Manuel 0.25.0 an; danach hat er die
Durchsicht W-004 (D-01 bis D-30, D-09) und die 4-Achs-Stufe V2a/V2c.

### DONE
- Version 0.25.0 mit Datum 2026-09-27; Beschreibung für den Addon-Manager
  und README nennen das Urteil „Schnittwerte“ und die Rundachse von der
  Maschine.

### TEST
- Auf Manuels Ansage sofort gepusht; der Volllauf in beiden Versionen folgt
  danach und wird ausgewertet.

### NEXT
- Volllauf; Manuels Fragen zur 4-Achs-Bearbeitung (Werkzeug, Bahnen,
  Werkzeuglage im Abfahren, Kollision) beantworten und planen.

## P-2026-09-27-38 vierachs-pruefen-futter

### EINGELESEN
- `docs/spezifikation_vierachs.md` (V2c); `camaddon/reichweite.py`
  (`vorschlag_nullpunkt`, `_pruefe_operation`, `_Sammler`, `_bahn`),
  `camaddon/vierachs_rohteil.py` (`richte_ein`, `stangen_placement`);
  Bild `szenario_vierachs_maschine/2_im_futter` aus P-37 (Nullpunkt-Vorschlag
  X −0,043, Z 133: die ganze Stange vor dem Futter).

### DATEIEN
- `camaddon/reichweite.py` (Hinweis bei fremder Rundachse; Vorschlag für
  eine Stange längs Z: auf ihrer Achse, Spannlänge im Futter)
- `camaddon/vierachs_rohteil.py` (`EIGENSCHAFT_SPANNLAENGE`, `spannlaenge`)
- `translations/de.json`, `translations/en.json` (`rw.rundachse_fehlt`,
  `rw.rundachse_fehlt_andere`, `va.eigenschaft.spannlaenge`)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_reichweite.py`, `tests/test_vierachs_rohteil.py`,
  `tests/gui/szenario_vierachs_maschine.py`
- `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Klickweg V2c: Job mit Rundachse A auf der Beispiel-Drehmaschine prüfen → „…
dreht um A – die Maschine hat keine Rundachse A“; Job mit C → die Stange
steckt 30 mm im Futter.

### DONE
- Dreht ein Programm um eine Rundachse, die die Maschine zwischen Werkzeug
  und Werkstück nicht hat, sagt ein Hinweis es – mit den Rundachsen, die sie
  hat, und dem Rat für Jobs aus der 4-Achs-Bearbeitung. Bisher rechnete die
  Prüfung stillschweigend ohne die Drehung.
- Der 4-Achs-Assistent merkt sich die Spannlänge am Job (ausgeblendet). Der
  Nullpunkt-Vorschlag im Prüffenster steckt eine Stange längs Z damit ins
  Futter und setzt sie genau auf ihre Achse – aus der Lage des Zylinders,
  nicht aus seiner Hüllbox (die lag 0,043 mm daneben).

### TEST
- `test_reichweite` (A auf der Drehmaschine mit nur C und auf der
  3-Achs-Fräse je mit Hinweis, C ohne) und `test_vierachs_rohteil`
  (Spannlänge am Job, ausgeblendet, Vorschlag (0, 0, 103)) in 1.1.3 ok.
- Auf Manuels Ansage („pusch jetzt“) sofort mit Version 0.25.0 gepusht; der
  Volllauf in beiden Versionen folgt danach, das Szenario
  `szenario_vierachs_maschine` (Vorschlag „0“, „0“, „103“) läuft in ihm mit.

### NEXT
- V2b: Drehteile per Klick auf eine runde Fläche.

## P-2026-09-27-37 vierachs-achse-von-maschine

### EINGELESEN
- `docs/spezifikation_vierachs.md` (Abschnitt 4, V2a), `camaddon/gui_vierachs.py`,
  `camaddon/vierachs_rohteil.py` (`lage`, `stangen_placement`, `richte_ein`),
  `camaddon/reichweite.py` (`Pruefung`, `_programmbuchstabe`),
  `camaddon/maschine.py` (`rollen`, `globale_platzierung`),
  `camaddon/kette.py` (Achsrichtung in Weltkoordinaten),
  `tests/gui/szenario_vierachs_rohteil.py`.

### DATEIEN
- neu `camaddon/vierachs_achsen.py` (`Stangenachse`, `zugewiesen`,
  `von_maschine`, `offene`, `gerade`, `achsbuchstabe`)
- `camaddon/vierachs_rohteil.py` (`laengs_von`; `lage`, `stangen_placement`,
  `richte_ein` nehmen Buchstabe oder Stangenachse)
- `camaddon/gui_vierachs.py` (Liste „Rundachse“: Maschinen oben, vorgewählt)
- `translations/de.json`, `translations/en.json` (`va.achse.maschine`,
  `va.achse.maschine_schraeg`; A/B/C „ohne Maschine“; Tooltip)
- `help/de/vierachs.html`, `help/en/vierachs.html`
- neu `tests/test_vierachs_achsen.py`, neu
  `tests/gui/szenario_vierachs_maschine.py`
- `docs/spezifikation_vierachs.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Klickweg V2a: Beispiel-Drehmaschine laden, Welle, Stirnfläche anklicken,
„4-Achs-Bearbeitung“ → unter Rundachse steht die Maschine oben und
vorgewählt, „… C – Stange längs Z“, die Stange liegt längs Z; mit A längs X.
Dazu Manuels Fall: Auf der Maschine prüfen – die Stange liegt längs der
Spindel im Futter, nicht quer.

### DONE
- Ist eine W-001-Maschine offen, stehen ihre Rundachsen im Tisch (Gelenk mit
  „Positionieren“ zwischen Werkstückaufnahme und Bett) oben in der Liste
  „Rundachse“ und die erste ist vorgewählt. Die Stange liegt dann längs der
  Richtung dieser Achse in den Achsen der Werkstückaufnahme – vorne vom
  Futter weg. Das Prüffenster rechnet in genau diesen Achsen.
- A, B, C heißen jetzt „… (ohne Maschine)“; der Tooltip sagt, dass eine offene
  Maschine die Achse vorgibt.
- Eine halb eingerichtete Maschine, deren Kette sich nicht aufbauen lässt,
  fehlt in der Liste statt den Assistenten zu stören.

### TEST
- `test_vierachs_achsen` (neu) in 1.1.3 und im Wochen-Build ok:
  Drehmaschine → C, Stange längs +Z; 3-Achs-Fräse → keine; Lage mit der
  Maschine = Lage mit C.
- `szenario_vierachs_maschine` (neu) in beiden Versionen ok, Bilder
  `1_fenster` (Maschine vorgewählt) und `2_im_futter` (Stange längs der
  Spindel) angesehen; `szenario_vierachs_rohteil` in beiden ok.
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- V2c: Hinweis bei fremder Rundachse, Spannlänge im Futter, Stange mittig
  (der Vorschlag nimmt heute die Hüllbox des Zylinders: X −0,043 statt 0).
- V2b: Drehteile per Klick auf eine runde Fläche.

## P-2026-09-27-36 plan-vierachs-v2

### EINGELESEN
- Manuels Rückmeldung mit zwei Bildern (Stange quer im Futter seiner
  „CLX 550“; ein Teil aus einem Loft) und den Nachsätzen „wenns eine
  rotatiosn geometrie ist beim 4 achs bearbeiten“, „irgendwie sinnvoll ..“.
- `docs/spezifikation_vierachs.md` (Abschnitte 4, 5, 13, „Entschieden“),
  `camaddon/vierachs_rohteil.py`, `camaddon/gui_vierachs.py`,
  `camaddon/reichweite.py` (`vorschlag_nullpunkt`, `Pruefung`,
  `_programmbuchstabe`).

### DATEIEN
- `docs/spezifikation_vierachs.md` (V2 in V2a–V2c, Rückmeldung unter
  „Entschieden“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation sagt, warum die Stange quer im Futter stand und in welchen
Schritten V2 das behebt, je mit Klickweg.

### DONE
- Ursache: Der Assistent kennt die Maschine noch nicht; vorgewählt ist A
  (Stange längs X). Das Prüffenster rechnet in den Achsen der
  Werkstückaufnahme, an der Drehmaschine ist Z die Spindelachse – eine
  Stange längs X steht dort quer. Dazu übergeht die Prüfung eine Drehung um
  A stillschweigend, wenn die Maschine nur C hat.
- Plan: V2a Achse von der Maschine (vorgewählt, wenn eine offen ist), V2b
  Drehteile per Klick auf eine runde Fläche samt „Umdrehen“, V2c Hinweis im
  Prüffenster bei fremder Rundachse und Spannlänge im Futter.

### TEST
- Reine Doku-Änderung, kein Testlauf.

### NEXT
- V2a umsetzen.

## P-2026-09-27-35 snapshot-w004-stand

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md` (Durchsicht W-004, Wunschliste),
  `docs/durchsicht_bedienbarkeit.md` (Kurzfassung).

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`, `docs/durchsicht_bedienbarkeit.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Snapshot und Kurzfassung der Durchsicht sagen, was von W-004 seit
P-2026-09-27-25 erledigt ist und was offen oder zu entscheiden bleibt.

### DONE
- Erledigt seit dem letzten Stand: D-30 (-26), D-12 (-27), D-13 (-28),
  D-29 (-29), D-28 mit gemerktem Einsatz (-30, -31), D-09 (-32, -34); die
  Arbeitsregel „kein FreeCAD neben dem Volllauf“ (-33).
- Offen: D-23 (wartet auf Manuels Antwort zur Ausspannlänge), Rest von D-20
  und D-26. Zur Entscheidung: D-14, D-22, D-24, D-27, Frage 6 (D-09).

### TEST
- Reine Doku-Änderung, kein Testlauf.

### NEXT
- Manuels Antworten abwarten; bis dahin der Rest von D-20 (Schruppwerte
  planen mit der gemerkten Maschine).

## P-2026-09-27-34 ein-werkzeug-je-job

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-09; `camaddon/job_schnittwerte.py`
  (`lege_controller_an`), `camaddon/uebergabe_werkzeuge.py`
  (`parameter_fuer_cam`, `toolbit_daten`), `camaddon/reichweite.py`
  (`werkzeug_text`, `_Sammler.laenge`), FreeCADs
  `Mod/CAM/Path/Tool/Controller.py` (`onDelete`: das Werkzeug geht erst mit
  dem letzten Controller), `tests/test_reichweite.py`.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`werkzeug_im_job`, `_masse_passen`,
  `_ohne_zaehler`, `MASS_TOLERANZ`)
- `camaddon/reichweite.py` (`werkzeug_text` mit Werkzeugverwaltung)
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `tests/test_job_schnittwerte.py`, `tests/test_reichweite.py`,
  `tests/gui/szenario_schnittwerte_pruefen.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein zweiter Controller aus „Schnittwerte in den Job“ erzeugt kein „L001“,
und das Prüffenster nennt T3 einmal (Fertig-wenn von D-09).

### DONE
- „Werkzeug-Controller hinzufügen“: Hat ein Controller desselben Jobs das
  Werkzeug schon, mit den Maßen, die die Werkzeugverwaltung jetzt übergäbe,
  benutzt der neue dasselbe. FreeCAD sieht das vor – beim Löschen bleibt
  das Werkzeug, solange ein anderer Controller es hat.
- Sind die Maße anders (etwa ein anderer Schaft), kommt ein eigenes Werkzeug
  dazu; hat FreeCAD dessen Namen eindeutig gemacht („… L001“), heißt es
  „… L26 (2)“.
- Die Hinweise im Prüffenster nennen ein Werkzeug aus der
  Werkzeugverwaltung mit deren Namen – dasselbe Werkzeug zweier Controller
  steht damit einmal da, auch wenn FreeCAD das zweite selbst angehängt hat.
- FreeCADs eigener Weg (Controller aus der Bibliothek) nennt ein zweites
  Werkzeug weiter „… L001“ – das ist Frage 6 an Manuel.

### TEST
- `test_job_schnittwerte` und `test_reichweite` in 1.1.3 und im Wochen-Build
  ok: dasselbe Werkzeug, Strg+Z lässt es bei TC 1; mit anderem Schaft ein
  zweites „… (2)“; der Name in den Hinweisen aus der Werkzeugverwaltung.
- `szenario_schnittwerte_pruefen` in beiden Versionen ok: ein Werkzeug für
  beide Controller, T3 einmal, kein „L001“.
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- Auch die Maße eines Werkzeugs im Job können veralten (Ø in der
  Werkzeugverwaltung geändert): Das Prüffenster könnte es wie die
  Schnittwerte melden – `_masse_passen` kann das schon vergleichen.

## P-2026-09-27-33 tests-nicht-parallel

### EINGELESEN
- `docs/arbeitsregeln.md`, Abschnitt 5; `scripts/oberflaeche_testen.sh`;
  Protokoll des abgebrochenen Volllaufs auf 7a9ecd8
  (`szenario_erster_start`: `FileNotFoundError: …/user.cfg`, im
  `freecad.log` „Failed to access file for writing: …/user.cfg“);
  die Sperrdateien `/tmp/user.<Zahl>.cfg.lock`.

### DATEIEN
- `docs/arbeitsregeln.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die Tests laufen lässt, weiß, dass neben `scripts/alle_tests.sh` kein
anderes FreeCAD laufen darf, und warum.

### DONE
- Ursache des roten `szenario_erster_start` im Volllauf auf 7a9ecd8: Ein
  kurzes `freecadcmd`-Skript lief in derselben Sekunde an wie das Szenario.
  FreeCAD sperrt beim Schreiben von `user.cfg` die Datei
  `/tmp/user.<Unix-Zeit>.cfg.lock` – die Zahl ist die Sekunde (an Datei und
  Zeitstempel nachgeprüft). Das Szenario-FreeCAD schrieb `user.cfg` nicht;
  das Szenario prüft aber, dass die Sprachwahl sofort darin steht.
- Einzeln gestartet ist das Szenario in beiden Versionen grün, ohne die
  Meldung. Der Lauf ist abgebrochen und wird neu gestartet, ohne FreeCAD
  daneben.
- Die Regel steht jetzt in Abschnitt 5.

### TEST
- Reine Doku-Änderung, kein Testlauf; `szenario_erster_start` einzeln in
  1.1.3 und im Wochen-Build ok.

### NEXT
- Volllauf für P-30 bis P-33, dann Push.

## P-2026-09-27-32 befund-d09

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md` (Abschnitte 2 und 6),
  `camaddon/werkzeuge.py` (`beispielname`, `anzeigename`),
  `camaddon/job_schnittwerte.py` (`lege_controller_an`),
  `camaddon/reichweite.py` (`werkzeug_text`, Hinweise zur Länge);
  Bild `szenario_schnittwerte_pruefen/1_veraltet`.

### DATEIEN
- `docs/durchsicht_bedienbarkeit.md` (D-09, Frage 6)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der beim Szenario zu D-28 aufgefallene Fehler steht als Befund mit Vorschlag
in der Durchsicht; was Manuel entscheiden muss, steht als Frage mit
Empfehlung in Abschnitt 6.

### DONE
- D-09: Ein zweiter Controller desselben Werkzeugs hängt das Werkzeug ein
  zweites Mal ins Dokument; FreeCAD macht den Namen eindeutig, indem es die
  Zahl am Ende ersetzt – „Schaftfräser T3 VHM D12 L26“ wird „… L001“, „…
  L002“ (in 1.1.3 und im Wochen-Build mit einem kleinen Skript
  nachgeprüft). Vorschlag: dasselbe Werkzeug benutzen, die Hinweise mit dem
  Namen der Werkzeugverwaltung, einmal je Werkzeug.
- Frage 6: Namen wie heute (Empfehlung) oder so bauen, dass sie nicht auf
  eine Zahl enden.

### TEST
- Reine Doku-Änderung, kein Testlauf (`docs/arbeitsregeln.md`, Abschnitt 5).

### NEXT
- D-09 (1) und (2) umsetzen – sie brauchen keine Entscheidung.

## P-2026-09-27-31 veraltete-schnittwerte

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-28; `camaddon/gui_reichweite.py`
  (Urteile oben, `_zeige`, `_werkzeuge_gespeichert`, `_zurueckfahren`),
  `camaddon/job_schnittwerte.py` (nach P-30), `camaddon/gui_kollision.py`
  (Farben, Verweise), `help/*/reichweite.html`,
  `tests/gui/szenario_kollision.py`.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`RUNDUNG`, `Vergleich`, `vergleiche`,
  `uebernimm`)
- `camaddon/gui_reichweite.py` (Urteil „Schnittwerte“,
  `schnittwerte_uebernehmen`, `_veraltet_satz`)
- `translations/de.json`, `translations/en.json` (`rw.urteil.schnittwerte`,
  `rw.schnittwerte.*`)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_kollision.py`,
  neu `tests/gui/szenario_schnittwerte_pruefen.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Eine geänderte Schnittgeschwindigkeit erscheint im Prüffenster als Hinweis
mit Knopf (Fertig-wenn von D-28).

### DONE
- Oben im Prüffenster ein viertes Urteil **Schnittwerte** – nur, wenn
  Controller des Jobs aus der Werkzeugverwaltung kommen und eine Operation
  sie benutzt. Grün „Drehzahl und Vorschub wie in der Werkzeugverwaltung.“;
  sonst gelb je Controller „T3 Schruppen dynamisch: im Job 3183 U/min ·
  1432 mm/min, laut Werkzeugverwaltung 3979 U/min · 1790 mm/min –
  übernehmen“, nur mit dem, was abweicht; bei mehreren „Alle übernehmen“.
- Verglichen wird, was „Übernehmen“ im Dialog setzen würde: mit Einsatz und
  Werkstoff vom letzten Setzen (P-30), sonst dem Vorschlag. Eine Umdrehung
  bzw. ein mm/min Unterschied ist Rundung.
- „übernehmen“ setzt Drehzahl und Vorschübe (wie der Dialog, samt
  Eintauchvorschub), nicht Schrittweite und Zustelltiefe – ein Schritt
  Rückgängig im Dokument des Jobs; das Fenster rechnet danach neu.
- Nicht fett: Es sind Sätze mit Zahlen; im schmalen Aufgabenbereich lesen
  sie sich so besser (Bilder verglichen).

### TEST
- `test_job_schnittwerte` in 1.1.3 und im Wochen-Build ok: frisch gesetzt
  passt, vc geändert → n und vf veraltet, fz geändert → nur vf, 1 U/min ist
  Rundung, `uebernimm` samt Strg+Z, unbenutzter Controller zählt nicht.
- `szenario_schnittwerte_pruefen` (neu) in beiden Versionen ok; Bilder
  `1_veraltet`, `2_uebernommen` angesehen.
- `szenario_kollision` in beiden Versionen ok (ohne Schnittwerte keine
  Zeile).
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- Beobachtung beim Szenario: Zwei Controller für dasselbe Werkzeug – das
  zweite Werkzeug heißt in FreeCAD „… L001“ statt „… L26“ (FreeCAD macht den
  Namen eindeutig, indem es die Zahl am Ende ersetzt).
- Offen ohne Entscheidung: D-23 (wartet auf Manuels Antwort zur
  Ausspannlänge), Rest von D-20 und D-26.

## P-2026-09-27-30 einsatz-merken

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-28; `camaddon/job_schnittwerte.py`
  (`vorgeschlagener_einsatz`, `werkstoff_des_jobs`, `_setze_werte`, `setze`,
  `lege_controller_an`), `camaddon/gui_job_schnittwerte.py`
  (`_job_gewaehlt`, `uebernehmen`, `controller_anlegen`),
  `camaddon/reichweite.py` (`merke_maschine` als Vorbild),
  `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`EIGENSCHAFT_EINSATZ`, `Gemerkt`,
  `gemerkter_einsatz`, `_merke_einsatz`, `werkstoff_fuer`)
- `camaddon/gui_job_schnittwerte.py`
- `translations/de.json`, `translations/en.json` (`sj.eigenschaft.einsatz`,
  `sj.herkunft.rohteil_gemerkt`, `sj.herkunft.gemerkt`)
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer in „Schnittwerte in den Job“ für einen Controller einen anderen Einsatz
wählt als den vorgeschlagenen, bekommt beim nächsten Öffnen diesen
vorgeschlagen – Voraussetzung für D-28: Das Prüffenster soll mit dem
vergleichen, was man gewählt hat, nicht mit einem Vorschlag.

### DONE
- Setzt das Addon Drehzahl und Vorschub eines Controllers („Übernehmen“,
  „Werkzeug-Controller hinzufügen“), merkt es sich am Controller Einsatz
  (Art und eigener Name, unabhängig von der Sprache) und Werkstoff – in
  einer ausgeblendeten Eigenschaft, im selben Schritt Rückgängig.
- Der Dialog schlägt den gemerkten Einsatz vor, vor dem Namen des
  Controllers und der Operation.
- Werkstoff: Gilt weiter der des Rohteils. Hat das Rohteil keinen, ist der
  vom letzten Mal vorgewählt; von zwei Einträgen mit der Nummer des Rohteils
  (geglüht und gehärtet, oder ein eigener) der zuletzt gewählte. Der Satz
  unter der Wahl sagt „wie beim letzten Mal“.

### TEST
- `test_job_schnittwerte` in 1.1.3 und im Wochen-Build ok: gemerkt,
  ausgeblendet, vor dem Namen, Strg+Z nimmt es mit; `werkstoff_fuer` mit
  zwei Zuständen, eigenem Werkstoff, unbekanntem Rohteil, „alle“.
- `szenario_schnittwerte_job` in beiden Versionen ok; neues Bild
  `6_gemerkt` angesehen: Vollnut bei „T3 Schruppen dynamisch“, C45 „wie beim
  letzten Mal“.
- Alle Einzeltests in beiden Versionen ok.

### NEXT
- D-28: das Prüffenster vergleicht mit dem gemerkten Einsatz und Werkstoff.

## P-2026-09-27-29 ap-uebernehmen

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-29; `camaddon/gui_job_schnittwerte.py`
  (`_zustellung_zelle`, `_duenn_satz`, `_ebenen_hinweis_zeigen`),
  `camaddon/job_schnittwerte.py` (`duenne_letzte_ebene`),
  `camaddon/gui_teile.py` (`hinweiszeile`), `tests/gui/szenario_loch_auffraesen.py`,
  `help/*/werkzeuge.html` („Eine Ebene oder zwei?“).

### DATEIEN
- `camaddon/gui_job_schnittwerte.py` (Verweis am Hinweis, `ap_uebernehmen`)
- `translations/de.json`, `translations/en.json`
  (`sj.ebene_duenn.uebernehmen`, `sj.ebene_duenn.wv_offen`)
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `tests/gui/szenario_loch_auffraesen.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Klick ändert den Einsatz, und die Ebenenzahl erscheint neu (Fertig-wenn
von D-29).

### DONE
- Der rote Hinweis zur dünnen letzten Ebene endet, wenn die Schneide lang
  genug ist, mit dem Verweis **ap 26 mm übernehmen**. Er trägt die
  vorgeschlagene Zustelltiefe in den Einsatz der Zeile ein (der gezeigte:
  eigener des Werkstoffs oder der für alle), speichert die Werkzeugverwaltung
  und rechnet den Dialog neu: „… · 26 mm · … · 1 Ebene“, der Hinweis
  verschwindet.
- Ist die Werkzeugverwaltung gleichzeitig offen, ändert der Verweis nichts
  und sagt es – deren OK schriebe sonst den alten Wert zurück.
- Das ist eine Änderung in der Werkzeugverwaltung, kein Schritt Rückgängig
  im Dokument; die Hilfe sagt, dass gespeichert wird.

### TEST
- `szenario_loch_auffraesen` in 1.1.3 ok – Verweis da, Klick: 26 mm, 1
  Ebene, kein Hinweis, in der Datei ap 26; Bilder `1_zwei_ebenen`,
  `1b_ap_uebernommen` angesehen.
- `szenario_schnittwerte_job`, alle Einzeltests in 1.1.3 ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-28: veraltete Werte im Job melden.

## P-2026-09-27-28 menue-cam-addon

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-13; `camaddon/gui_start.py`
  (Werkzeugleiste, `_werkzeugleiste_anhaengen`), `tests/gui/szenario_erster_start.py`,
  `README.md` (Update-Knopf), `docs/aufbau.md`.

### DATEIEN
- `camaddon/gui_start.py` (`MENUE`, Werkzeugleiste ohne „Über“ und Update)
- `tests/gui/szenario_erster_start.py`
- `README.md`, `docs/aufbau.md`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Jeder Befehl steht im Menü, die Werkzeugleiste hat sieben Symbole
(Fertig-wenn von D-13).

### DONE
- Im Assembly- und im CAM-Arbeitsbereich gibt es jetzt das Menü
  **CAM-Addon** (zwischen dem Menü des Arbeitsbereichs und „Windows“): Neue
  Maschine, Maschine bearbeiten, Maschine verfahren | Werkzeugverwaltung,
  Schnittwerte in den Job, Auf der Maschine prüfen, 4-Achs-Bearbeitung | Nach
  Updates suchen, Über das CAM-Addon – mit Text und Symbol.
- Die Werkzeugleiste hat nur noch die sieben Arbeitsbefehle; „Über“ und
  „Nach Updates suchen“ stehen im Menü. Angehängt wird beides auf demselben
  Weg (`appendToolbar`, `appendMenu` des Arbeitsbereichs), einmal je
  Arbeitsbereich.
- README: „Aktualisieren“ zeigt auf **CAM-Addon → Nach Updates suchen**.
- Die Einstellungsseite (Vorschlag D-13) bekommt keinen eigenen Knopf: Die
  Suche beim Start lässt sich dort schon einschalten; für von Hand genügt
  das Menü.

### TEST
- `szenario_erster_start` in 1.1.3 ok – Werkzeugleiste mit sieben Knöpfen,
  ohne „Nach Updates suchen“; Menü „CAM-Addon“ mit neun Einträgen, deutsch,
  „Nach Updates suchen“ und „Über das CAM-Addon“ am Ende; Bilder
  `4_cam_werkzeugleiste`, `4b_menue` angesehen.
- `szenario_update` ok; alle Einzeltests in 1.1.3 ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-23 (Halter vorschlagen), D-28, D-29 – oder Manuels Antwort zur
  Ausspannlänge.

## P-2026-09-27-27 erster-einsatz

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-12; `camaddon/gui_schnittwerte.py`
  (`zeige`, `einsatz_anlegen`), `camaddon/gui_werkzeuge.py`
  (`waehle_werkstoff`, `_schnittwerte_zeigen`), `camaddon/werkzeuge.py`
  (`schnittwerte`, `zum_bearbeiten`), `tests/gui/szenario_werkzeugverwaltung.py`,
  `help/*/schnittwerte.html`.

### DATEIEN
- `camaddon/gui_schnittwerte.py` (`_noch_keiner`, erster Einsatz für alle)
- `camaddon/gui_werkzeuge.py` (übergibt „Alle Werkstoffe wählen“)
- `translations/de.json`, `translations/en.json`
  (`wv.schnittwerte.noch_keine`, `wv.einsatz.erster_fuer_alle`)
- `help/de/schnittwerte.html`, `help/en/schnittwerte.html`
- `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beim neuen Werkzeug geht „+ Einsatz“ bei jedem gewählten Werkstoff
(Fertig-wenn von D-12).

### DONE
- Hat das Werkzeug noch gar keinen Einsatz, steht bei einem gewählten
  Werkstoff statt „Für 1.4301 gelten die Werte für alle Werkstoffe (grau) …“:
  „Dieses Werkzeug hat noch keine Schnittwerte. „+ Einsatz“ legt den ersten
  an – er gilt für alle Werkstoffe.“ – und „+ Einsatz“ ist bedienbar.
- Der erste Einsatz kommt in die Werte für alle Werkstoffe; oben springt die
  Auswahl auf „Alle Werkstoffe“, damit die Zeile gleich bearbeitbar ist, und
  der Satz sagt es: „Der erste Einsatz gilt für alle Werkstoffe – deshalb
  steht oben jetzt „Alle Werkstoffe“. Sind die Werte für 1.4301 anders, legst
  du danach dort eigene an.“
- Werkzeuge mit Einsätzen: unverändert (grau geerbt, „Eigene Werte für …
  anlegen“).

### TEST
- `szenario_werkzeugverwaltung` in 1.1.3 ok – neues Werkzeug mit 1.4301:
  Satz, Knopf bedienbar; „Vollnut“ angelegt: für alle Werkstoffe, oben „Alle
  Werkstoffe“, Satz mit 1.4301; Bilder `9_neu_ohne_einsatz`,
  `9b_erster_einsatz` angesehen.
- `szenario_schnittwerte`, `szenario_zoll`, `szenario_schruppwerte`,
  alle Einzeltests in 1.1.3 ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-13: ein Menü „CAM-Addon“; Antwort von Manuel zur Ausspannlänge.

## P-2026-09-27-26 unbenutzte-controller

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-30; `camaddon/gui_job_schnittwerte.py`
  (Tabelle, „Werkzeug-Controller hinzufügen“), `camaddon/job_schnittwerte.py`
  (`werkzeug_von`, `operationen_mit`), FreeCADs
  `Mod/CAM/Path/Tool/Controller.py` und `toolbit/models/base.py` (`onDelete`,
  `_removeBitBody`), `tests/gui/szenario_schnittwerte_job.py`,
  `help/*/werkzeuge.html`.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`unbenutzte_fremde_controller`,
  `entferne_controller`)
- `camaddon/gui_job_schnittwerte.py` (Zeile mit „Entfernen“ unter der
  Tabelle)
- `translations/de.json`, `translations/en.json` (`sj.unbenutzt*`)
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der unbenutzte Controller verschwindet mit einem Klick (Fertig-wenn von
D-30).

### DONE
- „Schnittwerte in den Job“ zeigt unter der Tabelle: „Von keiner Operation
  benutzt und nicht aus der Werkzeugverwaltung: „TC: 5mm Endmill“, …“ mit dem
  Knopf **Entfernen** (Tooltip: FreeCAD legt ihn in jedem neuen Job an).
  Controller aus der Werkzeugverwaltung, die (noch) keine Operation benutzt,
  bleiben unberührt – die legt man absichtlich an.
- Entfernt wird wie beim Löschen im Baum, über FreeCADs eigenes `onDelete`:
  mit dem Werkzeug und dessen Körper (Body, Skizze, Ebenen,
  „Attributes“), wenn kein anderer Controller es benutzt. Ausprobiert in
  1.1.3 und im Wochen-Build: Nur Controller und Werkzeug zu löschen ließe den
  Körper im Dokument zurück.
- Gelernt: Solange ein Befehl einen Dialog offen hält, fasst FreeCAD alles
  darin zu einem Schritt Rückgängig zusammen (die Transaktion des Befehls;
  `openTransaction` benennt sie nur). Strg+Z nach dem Dialog nimmt also alles
  zurück, was in diesem Aufruf geschah – auch einen dort angelegten
  Controller.
- Nicht gemacht (D-30, zweiter Teil): „in die Werkzeugverwaltung übernehmen?“
  für einen benutzten fremden Controller – dafür gibt es „Aus CAM übernehmen“
  in der Werkzeugverwaltung (der Tooltip der Zeile nennt es).

### TEST
- `test_job_schnittwerte` in 1.1.3 ok – neuer Job ohne Operation: der
  Standard-Controller ist unbenutzt, Entfernen lässt nur den Job übrig,
  Strg+Z holt alles zurück.
- `szenario_schnittwerte_job` in 1.1.3 ok – im eigenen Aufruf: Zeile mit
  „TC: 5mm Endmill“ und „TC fremd“, Entfernen, Tabelle neu, Werkzeug und
  Körper weg, Strg+Z stellt den Stand vor dem Aufruf wieder her; Bild
  `5_unbenutzt` angesehen.
- Alle Einzeltests in 1.1.3 ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-12: „+ Einsatz“ beim neuen Werkzeug.

## P-2026-09-27-25 snapshot-w004-weiter

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md` (W-004), `docs/durchsicht_bedienbarkeit.md`
  (Kurzfassung).

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`, `docs/durchsicht_bedienbarkeit.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Snapshot und Kurzfassung der Durchsicht nennen, was seit D-08 erledigt ist
und was offen bleibt.

### DONE
- Snapshot: D-21, D-20 (Prüffenster), D-10, D-11, D-25, D-26 (3-Achs-Fräse)
  mit ihren Patches; offen ohne Entscheidung D-12, D-13, D-23, D-28 bis D-30
  und die Reste von D-20/D-26, zur Entscheidung D-14, D-22, D-24, D-27.
- Kurzfassung der Durchsicht: Vermerke bei „Einfacher bedienen“ und
  „Automatisieren“.

### TEST
- Reine Doku (`docs/arbeitsregeln.md`, Abschnitt 5).

### NEXT
- Bericht an Manuel; dann D-30, D-12, D-13.

## P-2026-09-27-24 masse-fraese

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-26; `camaddon/beispielmaschine.py`
  (`fraesmaschine`, `DrehmaschinenMasse`, `lade`, Namensgebung der
  Drehmaschine), `camaddon/gui_neue_maschine.py` (Felder, Auswahl, `masse`),
  `camaddon/einheiten.py` (Stellen in inch), die Aufrufer von
  `fraesmaschine()` in den Tests, `tests/gui/szenario_zoll.py` (baut die Fräse
  in inch), `help/*/neue_maschine.html`.

### DATEIEN
- `camaddon/beispielmaschine.py` (`FraesenMasse`, `_wege_fehler`,
  `_benenne`; `fraesmaschine(masse)`)
- `camaddon/gui_neue_maschine.py` (Felder auch für die 3-Achs-Fräse,
  Vorbelegung je Bauart, `_vorgabe`, `_wert`)
- `translations/de.json`, `translations/en.json` (Texte, die nur die
  Drehmaschine mit Maßen nannten)
- `help/de/neue_maschine.html`, `help/en/neue_maschine.html`
- `tests/test_beispielmaschine.py`, `tests/gui/szenario_neue_maschine.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Eine 3-Achs-Fräse mit eigenen Wegen steht in einer Minute, und „Auf der
Maschine prüfen“ rechnet mit diesen Grenzen (Fertig-wenn von D-26, Teil
3-Achs-Fräse).

### DONE
- „Neue Maschine …“ zeigt bei der 3-Achs-Fräse Name, Weg X/Y/Z (von … bis)
  und Höchstdrehzahl; Bettneigung, „Y schräg um“ und Revolverplätze sind dort
  ausgeblendet. Wechselt man die Bauart, stehen ihre Beispielwerte in den
  Feldern. Die 5-Achs-Fräsen behalten „feste Maße“.
- Die Wege werden die Grenzen der Gelenke X, Y, Z – damit rechnen „Maschine
  verfahren“ und „Auf der Maschine prüfen“; die Drehzahl gilt für S1, der
  Name für Maschine und Dokument (wie bei der Drehmaschine, jetzt gemeinsam in
  `_benenne`). Ungültige Wege meldet dieselbe rote Zeile.
- Ein Weg, der noch wie vorbelegt dasteht, gilt genau – in inch ohne den
  Rundungsrest der Anzeige.
- Der freie Platz bei weniger Feldern liegt über den Knöpfen statt als Lücke
  über „Maße“.
- Nicht gemacht: Tischgröße und die Schwenkbereiche der 5-Achs-Fräsen – die
  Körper bleiben grob wie im Beispiel.

### TEST
- `test_beispielmaschine` in 1.1.3 ok – Fräse mit eigenen Wegen: Grenzen der
  Gelenke, S1 8000, Name; ungültige Maße.
- `szenario_neue_maschine` in 1.1.3 ok – Fräse mit Feldern, ohne die der
  Drehmaschine, vorbelegt wie ihr Beispiel; 5-Achs „feste Maße“; Bilder
  `1_fraese_masse`, `1b_fuenfachs_feste_masse` angesehen.
- `szenario_zoll`, `szenario_beispielmaschine`, `szenario_maschine_merken`
  ok; alle Einzeltests in 1.1.3 ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Bericht an Manuel; dann D-30, D-12, D-13.

## P-2026-09-27-23 betriebsarten-vorschlagen

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-25 (und D-14: Kennwerte leer lassen
  ist die Empfehlung, noch nicht entschieden); `camaddon/maschine.py`
  (`neue_betriebsart`, Arten), `camaddon/kette.py` (`Achse`: Art, Richtung),
  `camaddon/gui_maschine.py` („+ Betriebsart“, Knöpfe), die NC-Namen der
  Beispielmaschinen (X1, Y1, Z1, A1, B1, C1, S1, S3, T),
  `tests/beispielmaschinen.py` (Testdrehmaschine: Gelenke „Spindel“, „Z“,
  „X“, „Revolverachse“), `help/*/achsen.html`.

### DATEIEN
- `camaddon/maschine.py` (`vorgeschlagene_art`, `vorgeschlagener_name`,
  `schlage_betriebsarten_vor`)
- `camaddon/gui_maschine.py` (Knopf „Vorschlagen“, NC-Name bei „+
  Betriebsart“ vorbelegt)
- `translations/de.json`, `translations/en.json` (`dialog.vorschlagen` samt
  Tooltip)
- `help/de/achsen.html`, `help/en/achsen.html`
- `tests/test_maschine.py`, `tests/gui/szenario_maschine_bearbeiten.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Drehmaschine aus `szenario_maschine_bearbeiten` bekommt mit einem Klick
S1, Z1, X1 und T (Fertig-wenn von D-25).

### DONE
- **Vorschlagen** unter den Achsen: Jedes Gelenk ohne Betriebsart bekommt
  eine. Schiebegelenke linear, der NC-Name aus einem allein stehenden
  Achsbuchstaben im Namen des Gelenks („X-Schlitten“ → X1, „Schlitten Z2“ →
  Z2), sonst aus der Richtung (größter Anteil: X, Y oder Z). Drehgelenke mit
  „Spindel“/„spindle“ im Namen eine Spindel (S1 …), mit „Revolver“/„turret“
  der Revolver (T), sonst Positionieren (A, B, C nach der Drehachse).
  Vergebene Namen zählen weiter (X2, S2, T2). Der Knopf ist nur bedienbar,
  wenn ein Gelenk noch keine Betriebsart hat.
- Die Kennwerte bleiben leer (0 = unbekannt) – wie in D-14 empfohlen; die
  Hinweise sagen, welche fehlen.
- **+ Betriebsart** belegt den NC-Namen genauso vor, markiert – Tippen
  ersetzt ihn.
- Alles liegt im Schritt des Dialogs: Abbrechen nimmt es zurück.

### TEST
- `test_maschine` in 1.1.3 ok – Testdrehmaschine: S1, Z1, X1, T; ein zweiter
  Vorschlag legt nichts an; Namen aus Name und Richtung, weiterzählen, Arten
  nach Namen (auch englisch).
- `szenario_maschine_bearbeiten` in 1.1.3 ok – vorgeschlagene Namen bei „+
  Betriebsart“ (Z1, X1), „Vorschlagen“ an der leeren Maschine; Bild
  `6_vorgeschlagen` angesehen.
- Alle Einzeltests in 1.1.3 ok (`scripts/tests_ausfuehren.sh`).
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-26: Maße auch für die Fräsen bei „Neue Maschine …“.

## P-2026-09-27-22 verweise-mit-praefix

### EINGELESEN
- Volllauf auf 7dcb496 (P-20, P-21): `test_hilfe.py` scheitert – „benutzt,
  aber keine Hilfe: ['hinweise', 'pruefen', 'wo']“. `tests/test_hilfe.py`
  wertet jedes `href="wort"` in `camaddon/gui_*.py` als Hilfethema.

### DATEIEN
- `camaddon/gui_kollision.py`, `camaddon/gui_reichweite.py`
- `tests/gui/szenario_kollision.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`test_hilfe` grün; die Verweise oben im Prüffenster tun weiter dasselbe.

### DONE
- Die Verweise, die im Fenster etwas tun, haben ein Präfix wie schon
  „werkzeug:1“ (P-21): `kollision:pruefen`, `kollision:wo`,
  `abschnitt:hinweise`. Ein Wort ohne Doppelpunkt bleibt ein Hilfethema.
- Ursache: Für P-20 liefen nur `test_reichweite`, `test_sprache` und die
  Szenarien, nicht alle Einzeltests. Vor dem nächsten Commit laufen alle
  Einzeltests (`scripts/tests_ausfuehren.sh`).

### TEST
- Alle Einzeltests in 1.1.3 ok (26), darunter `test_hilfe`; `szenario_kollision`
  ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-25: Betriebsarten der Maschine vorschlagen.

## P-2026-09-27-21 hinweis-zum-werkzeug

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-11; `camaddon/gui_werkzeuge.py`
  (Befehl, Auswahl, Übernehmen/OK), `camaddon/reichweite.py`
  (`_Sammler.laenge`), `camaddon/kollision.py` (Hinweis „ohne Halter“),
  `camaddon/gui_reichweite.py`, `camaddon/gui_kollision.py`,
  `tests/gui/szenario_kollision.py`.

### DATEIEN
- `camaddon/reichweite.py` (`Hinweis` – ein Satz mit Werkzeugnummer)
- `camaddon/kollision.py` (Hinweis „ohne Halter“ mit Nummer)
- `camaddon/gui_kollision.py` (`hinweis_label`, `hinweise_html`)
- `camaddon/gui_reichweite.py` (Verweis öffnet die Werkzeugverwaltung,
  Speichern dort rechnet neu)
- `camaddon/gui_werkzeuge.py` (`oeffne`, `waehle_nummer`, Signal
  `gespeichert`)
- `translations/de.json`, `translations/en.json` (neu `rw.werkzeug_oeffnen`)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_reichweite.py`, `tests/gui/szenario_kollision.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Halter wählen, OK – und die Kollision gilt mit dem Halter, ohne das
Prüffenster zu schließen (Fertig-wenn von D-11).

### DONE
- Hinweise zu einem Werkzeug – womit für die Länge gerechnet wurde, „T1: ohne
  Halter geprüft …“ – enden mit dem Verweis **T1 öffnen …**. Er öffnet die
  Werkzeugverwaltung (oder holt die offene nach vorn) mit diesem Werkzeug
  gewählt.
- Speichert man dort (OK oder Übernehmen), liest das Prüffenster die
  Werkzeuge neu, baut Werkzeug und Halter in der Ansicht neu und rechnet; das
  Kollisionsergebnis gilt dann nicht mehr („Noch nicht geprüft – jetzt
  prüfen“).
- Die Werkzeugverwaltung meldet jedes Speichern (Signal `gespeichert`); der
  Befehl in der Werkzeugleiste nutzt dasselbe `oeffne()`.

### TEST
- `test_reichweite` in 1.1.3 ok – Längen-Hinweise tragen die Nummer.
- `szenario_kollision` in 1.1.3 ok – „T1 öffnen …“ zeigt T1, ER16 gewählt,
  OK: Ergebnis veraltet, das Fenster kennt den Halter; neu geprüft ohne
  Hinweis „ohne Halter“. Bilder `4_werkzeugverwaltung_halter`,
  `5_mit_halter` angesehen.
- `szenario_reichweite`, `szenario_abfahren`, `szenario_werkzeugverwaltung`,
  `test_sprache` ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-25: Betriebsarten der Maschine vorschlagen.

## P-2026-09-27-20 urteile-oben

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-10; `camaddon/gui_reichweite.py`
  (Aufbau, `_zeige`), `camaddon/gui_kollision.py` (Urteil, Prüfen),
  `camaddon/reichweite.py` (`Ergebnis`, `_Sammler.laenge`),
  `camaddon/gui_details.py` (Verweis im Text als Vorbild),
  `help/*/reichweite.html`, Bilder `szenario_kollision/2_kollision` und
  `2b_fenster`.

### DATEIEN
- `camaddon/reichweite.py` (`Ergebnis.laengen`, `geschaetzte_laengen`)
- `camaddon/gui_kollision.py` (`kurzurteil`, Rückmeldung ans Fenster)
- `camaddon/gui_reichweite.py` (drei Urteilszeilen, Verweise)
- `camaddon/gui_teile.py` (`blaettere_zu`)
- `translations/de.json`, `translations/en.json` (`rw.erklaerung`,
  `rw.nicht_in_grenzen`; neu `rw.urteil.*`, `rw.laenge.*`, `kb.kurz.*`)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_reichweite.py`, `tests/gui/szenario_kollision.py`,
  `tests/gui/szenario_reichweite.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In einem 800 Pixel hohen Fenster sind alle drei Urteile ohne Blättern zu
sehen (Fertig-wenn von D-10).

### DONE
- Unter dem Nullpunkt drei Zeilen: **Achsen** (der Satz wie bisher; bei
  Überschreitung „… – wo, steht darunter.“), **Kollision** („Noch nicht
  geprüft – jetzt prüfen“; danach das Urteil, rot/gelb mit „wo?“),
  **Werkzeuglänge** (grün „Bei allen Werkzeugen gemessen …“, sonst gelb „Für
  T1 geschätzt – warum?“; ohne Werkzeug keine Zeile).
- „jetzt prüfen“ prüft gleich, „wo?“ und „warum?“ blättern den
  Aufgabenbereich zum Abschnitt „Kollision“ bzw. zu den Hinweisen
  (`blaettere_zu`).
- Die Erklärung oben: ein Satz statt fünf Zeilen – der Rest steht in der
  Hilfe; die Hilfe beschreibt die drei Urteile.
- Nicht gemacht: Abfahren und Kollision einklappbar – mit den Urteilen oben
  nicht mehr nötig für das Kriterium; bei Bedarf später.

### TEST
- `test_reichweite` in 1.1.3 ok (`laengen`, `geschaetzte_laengen`).
- `szenario_kollision` in 1.1.3 ok – die drei Urteile gleich nach dem
  Öffnen ohne Blättern sichtbar (`visibleRegion`), „warum?“ zeigt die
  Hinweise, geprüft über „jetzt prüfen“ oben, „wo?“ zeigt den Abschnitt;
  Bilder `0_urteile_oben`, `2b_fenster` angesehen.
- `szenario_reichweite`, `szenario_abfahren`, `szenario_maschine_merken`,
  `test_sprache` ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-11: Hinweise führen zum Werkzeug.

## P-2026-09-27-19 maschine-merken

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-20; `camaddon/gui_reichweite.py`
  (Befehl, `_schliessen`, `_nullpunkt_merken`), `camaddon/reichweite.py`
  (`setze_nullpunkt` als Vorbild), `camaddon/gui_maschine.py`
  (`beispiel_waehlen`: so baut eine Meldung eine Maschine),
  `camaddon/gui_neue_maschine.py` (`waehle`), `help/*/reichweite.html`,
  `docs/spezifikation_simulation.md` §6.

### DATEIEN
- `camaddon/reichweite.py` (`EIGENSCHAFT_MASCHINE`, `ZULETZT_MASCHINE`,
  `gemerkte_maschine`, `merke_maschine`)
- `camaddon/gui_reichweite.py` (`maschine_fuer`, `maschine_oeffnen`,
  `datei_waehlen`, `oeffne_datei`, `gleiche_datei`, `_maschine_merken`)
- `translations/de.json`, `translations/en.json` (`rw.keine_maschine`,
  `rw.maschine.tooltip`; neu `rw.maschine_oeffnen` samt Tooltip,
  `rw.neue_maschine.tooltip`, `rw.keine_maschine_in_datei`, `rw.datei_fehler`,
  `rw.eigenschaft.maschine`, `rw.maschine.schritt`)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_reichweite.py`, neu `tests/gui/szenario_maschine_merken.py`
- `docs/spezifikation_simulation.md` §6, `docs/durchsicht_bedienbarkeit.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach einem Neustart von FreeCAD zeigt „Auf der Maschine prüfen“ ohne
geöffnete Maschine direkt das Fenster (Fertig-wenn von D-20). Ohne gemerkte
Maschine führt die Meldung weiter statt in eine Sackgasse.

### DONE
- Beim Schließen des Prüffensters merkt sich der Job die Datei der Maschine
  (verborgene Eigenschaft `CamAddonMaschine`, wie der Nullpunkt; ein Schritt
  Rückgängig „Maschine des Jobs“, nur wenn sie sich ändert), das Addon
  außerdem „zuletzt benutzt“ (Einstellung `ZuletztMaschine`). Eine nie
  gespeicherte Maschine hat keine Datei – dann bleibt alles, wie es war.
  Wechselt man im Fenster den Job, merkt sich der bisherige die Maschine
  ebenso (wie seinen Nullpunkt).
- Ist beim Prüfen keine Maschine offen, öffnet das Addon die gemerkte: die
  des Jobs, sonst die zuletzt benutzte. Lässt sie sich nicht lesen oder fehlt
  die Datei, kommt die Meldung.
- Die Meldung „Es ist keine Maschine offen …“ hat jetzt Knöpfe:
  **Maschine öffnen …** (Dateiauswahl, im Ordner der gemerkten Maschine
  oder des Jobs) und **Neue Maschine …** (Auswahl der Bauarten wie bei
  „Maschine bearbeiten“, danach gleich das Prüffenster auf ihr). Eine Datei
  ohne Maschine: „In … ist keine Maschine eingerichtet. Eine Baugruppe wird
  zur Maschine mit „Maschine bearbeiten“.“
- Sind mehrere Maschinen offen, fragt das Addon weiter, die gemerkte steht
  vorn (Enter genügt). Ohne Frage zu nehmen hätte eine andere Maschine nur
  noch über Schließen der gemerkten erreicht – im Fenster gibt es keine
  Auswahl der Maschine (Spezifikation §6, Aufgabenfenster gehört zum
  Dokument).
- Nicht in diesem Patch (D-20, Rest): „Schruppwerte planen“ nimmt die
  Grenzen weiter nur von einer offenen Maschine, und die Spindel kennt keine
  Leistung (kW).

### TEST
- `test_reichweite` in 1.1.3 ok – merken, die des Jobs vor „zuletzt
  benutzt“, leerer Pfad ändert nichts; nach Speichern und Laden noch da und
  (wie der Nullpunkt) verborgen.
- Neues Szenario `szenario_maschine_merken` in 1.1.3 ok: gemerkt nach dem
  Schließen; Maschine zu → öffnet sich selbst (über den Job und über
  „zuletzt benutzt“); ohne alles die Meldung mit beiden Knöpfen; „Neue
  Maschine …“ baut die 3-Achs-Fräse und prüft auf ihr; „Maschine öffnen …“
  mit einer Datei ohne Maschine sagt das, mit der richtigen prüft es; zwei
  offene Maschinen: Frage, die gemerkte vorn. Bilder angesehen.
- Nach Speichern und Laden ist die Eigenschaft noch verborgen – eigens
  geprüft, auch für den Nullpunkt (bisher ungeprüft).
- `szenario_reichweite`, `szenario_abfahren`, `szenario_kollision`,
  `szenario_erster_start`, `test_sprache` ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-20, Rest: Planer nimmt die gemerkte Maschine; Spindelleistung.

## P-2026-09-27-18 job-in-allen-dokumenten

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-21; `camaddon/gui_reichweite.py`
  (Befehl, `gewaehlter_job`), `camaddon/gui_job_schnittwerte.py` (Befehl,
  Dialog nimmt schon ein Dokument), `camaddon/job_schnittwerte.py` (`jobs`),
  `docs/spezifikation_simulation.md` §6, die Szenarien `szenario_reichweite`
  und `szenario_schnittwerte_job`.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`dokumente_mit_jobs`)
- `camaddon/gui_job_schnittwerte.py` (`dokument_mit_job`, Befehl)
- `camaddon/gui_reichweite.py` (Befehl, `gewaehlter_job`)
- `translations/de.json`, `translations/en.json` (`rw.kein_job`, `sj.kein_job`,
  neu `jobs.welches_dokument`)
- `tests/gui/szenario_reichweite.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/spezifikation_simulation.md` §6, `docs/durchsicht_bedienbarkeit.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Auf der Maschine prüfen“ mit dem Maschinendokument vorn prüft den Job des
anderen Dokuments, statt „kein CAM-Job“ zu melden. „Schnittwerte in den Job“
genauso.

### DONE
- Beide Befehle suchen das Dokument gleich (`dokument_mit_job`): das eines
  gewählten Jobs (auch über eine gewählte Operation oder ihren Controller, in
  jedem offenen Dokument), sonst das aktive, wenn es Jobs hat, sonst das
  einzige offene mit Jobs. Haben mehrere Dokumente Jobs und keines davon ist
  vorn, fragt eine Liste: „CAM-Jobs gibt es in mehreren offenen Dokumenten – in
  welchem?“ (gleiche Namen mit dem Dokumentnamen dahinter).
- Ohne Job in irgendeinem Dokument: „In keinem offenen Dokument gibt es einen
  CAM-Job. Öffne das Dokument mit dem Job – …“
- Die Maschine sucht das Prüffenster schon in allen Dokumenten; unverändert.

### TEST
- `szenario_reichweite` in 1.1.3 ok – neuer Block am Ende: Maschinendokument
  vorn, nichts gewählt, Befehl: keine Meldung, das Fenster zeigt den Job des
  Teils. `szenario_schnittwerte_job` ok (erwartet „keinem offenen Dokument“),
  `test_sprache` ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-20: die Maschine merken und selbst öffnen.

## P-2026-09-27-17 snapshot-w004

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md` (W-004, nächster Schritt),
  `docs/durchsicht_bedienbarkeit.md` (Kurzfassung).

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`, `docs/durchsicht_bedienbarkeit.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Snapshot und Durchsicht sagen, dass D-01 bis D-08 und der Revolver erledigt
sind und was offen bleibt.

### DONE
- Snapshot: W-004 mit „D-01 bis D-08 erledigt“, der Absatz beim nächsten
  Schritt nennt P-2026-09-27-07 bis -16 und die offenen Fragen.
- Durchsicht: Kurzfassung mit „Alle erledigt“ und dem nachgetragenen Revolver.

### TEST
- Nur Doku; der Gesamtlauf für P-2026-09-27-07 bis -17 läuft vor dem Push.

### NEXT
- Manuel: Reihenfolge der übrigen Punkte und die Fragen in Abschnitt 6.

## P-2026-09-27-16 ein-name-neue-maschine

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-08; `camaddon/gui_maschine.py`
  (beispiel_waehlen), `camaddon/gui_neue_maschine.py`, die Hilfe „Achsen“ und
  „Verfahren“, `tests/gui/szenario_beispielmaschine.py`, `szenario_zoll.py`.

### DATEIEN
- `camaddon/gui_maschine.py`, `camaddon/gui_neue_maschine.py`,
  `camaddon/beispielmaschine.py` (Kopfkommentare)
- `translations/de.json`, `translations/en.json` (`dialog.keine_baugruppe`,
  `dialog.beispielmaschine`, Tooltip; `beispiel.auswahl.titel` entfällt)
- `help/de/achsen.html`, `help/en/achsen.html`, `help/de/verfahren.html`,
  `help/en/verfahren.html`
- `tests/gui/szenario_beispielmaschine.py`, `tests/gui/szenario_zoll.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Knopf in der Meldung ohne Baugruppe heißt wie der Befehl, „Neue
Maschine …“, und die Meldung nennt diesen Weg vor dem Selbstbau.

### DONE
- Meldung: „Hier gibt es noch keine Baugruppe. Am schnellsten: „Neue
  Maschine …“ baut eine fertig eingerichtete Maschine … Oder selbst bauen: …“
- Knopf „Neue Maschine …“ (vorher „Beispielmaschine laden …“), die Auswahl
  heißt wie beim Befehl „Neue Maschine“; Hilfe und Kommentare nachgezogen.

### TEST
- `szenario_beispielmaschine` prüft Knopf und dass der leichte Weg vor
  „Assembly“ steht; `szenario_zoll`, `szenario_hilfe`, `test_sprache` in 1.1.3
  ok; Screenshots von Meldung und Auswahl angesehen.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Gesamtlauf, Push, Bericht an Manuel.

## P-2026-09-27-15 spanneisen-erwaehnt

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-07; `camaddon/beispielmaschine.py`
  (fraesmaschine mit Spanneisen seit P-2026-09-26-97),
  `help/*/neue_maschine.html`, `tests/gui/szenario_neue_maschine.py`.

### DATEIEN
- `translations/de.json`, `translations/en.json` (`beispiel.fraese3.beschreibung`)
- `help/de/neue_maschine.html`, `help/en/neue_maschine.html`
- `tests/gui/szenario_neue_maschine.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beschreibung und Hilfe der 3-Achs-Fräse nennen die zwei Spanneisen als
Beispiel und sagen, dass man sie verschiebt oder löscht.

### DONE
- Beschreibung: „… Auf dem Tisch zwei Spanneisen als Beispiel – im Baum
  verschieben oder löschen.“ Hilfe: ein Absatz, dass die Kollisionsprüfung sie
  mitnimmt. Ein Häkchen „ohne Spanneisen“ gibt es nicht – verschieben oder
  löschen ist ein Klick im Baum.

### TEST
- `szenario_neue_maschine` prüft „Spanneisen“ in der Beschreibung;
  `szenario_hilfe` ok (1.1.3).
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-08.

## P-2026-09-27-14 an-cam-kurzer-weg

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-06; `camaddon/gui_werkzeuge.py`
  (bericht_text), die Namen im Dialog „Schnittwerte in den Job“
  (`sj.tc_neu`), `tests/gui/szenario_an_cam.py`.

### DATEIEN
- `translations/de.json`, `translations/en.json` (`wv.cam.weiter`)
- `tests/gui/szenario_an_cam.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Rückmeldung nach „Speichern und an CAM übergeben“ nennt zuerst den
kurzen Weg („Schnittwerte in den Job“ → „Werkzeug-Controller hinzufügen“),
dann den von Hand.

### DONE
- Ein Satz vorn: „Am schnellsten legt „Schnittwerte in den Job“ →
  „Werkzeug-Controller hinzufügen“ die Werkzeug-Controller mit Drehzahl und
  Vorschub in einem Schritt an.“ Danach der Weg von Hand wie bisher.

### TEST
- `szenario_an_cam` in 1.1.3 ok – prüft den kurzen Weg im Text; Screenshot
  angesehen.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-07.

## P-2026-09-27-13 auswahl-beim-oeffnen

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-05; `camaddon/gui_maschine.py` und
  `camaddon/gui_verfahren.py` (Befehle), `camaddon/gui_zeigen.py` (hebt über
  die Auswahl hervor), `aufnahme_anlegen` (nimmt ein danach gewähltes LCS).

### DATEIEN
- `camaddon/gui_maschine.py`, `camaddon/gui_verfahren.py`
- `tests/gui/szenario_maschine_bearbeiten.py`, `tests/gui/szenario_verfahren.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Öffnet man „Maschine bearbeiten“ oder „Maschine verfahren“ mit gewählter
Baugruppe, steht die Maschine im offenen Fenster in ihren eigenen Farben.

### DONE
- Beide Befehle heben die Auswahl auf, sobald die Baugruppe gefunden ist.

### TEST
- `szenario_maschine_bearbeiten`, `szenario_verfahren` prüfen: nach dem Öffnen
  ist nichts mehr gewählt; dazu `zeigen`, `felder`, `schraege_achse`,
  `neue_maschine` in 1.1.3 ok; Screenshot angesehen (schräge Achse: Maschine
  in ihren Farben).
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-06.

## P-2026-09-27-12 update-neu-starten

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-04; `camaddon/gui_aktualisierung.py`
  (UpdateDialog), `tests/gui/szenario_update.py`; wie FreeCADs Addon-Manager
  neu startet (Hauptfenster schließen, dann dasselbe Programm mit denselben
  Argumenten über `QProcess.startDetached`).

### DATEIEN
- `camaddon/gui_aktualisierung.py`
- `translations/de.json`, `translations/en.json` (`update.neu_starten`, Tooltip)
- `tests/gui/szenario_update.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Aktualisieren bietet das Fenster „Jetzt neu starten“ und „Später“;
„Jetzt neu starten“ schließt FreeCAD (mit der Frage nach ungespeicherten
Dokumenten) und startet es neu.

### DONE
- `neu_starten()`: Hauptfenster schließen – bricht man bei der Frage nach dem
  Speichern ab, bleibt alles, wie es ist –, dann FreeCAD neu starten. Kein
  Shell-Aufruf: `QtCore.QProcess.startDetached` mit dem Programm, das gerade
  läuft (Qt, auf jedem Betriebssystem), wie der Addon-Manager.
- Der Knopf erscheint erst nach einem erfolgreichen Aktualisieren.

### TEST
- `szenario_update` in 1.1.3 ok: Knopf sichtbar nach dem Aktualisieren;
  `neu_starten` mit Ersatz für Hauptfenster und Programmstart – schließt es,
  startet FreeCAD (Pfad der laufenden FreeCAD-Datei); bricht man ab, startet
  nichts. Den echten Neustart klickt die Prüfung nicht (FreeCAD liefe danach
  weiter) – das probiert Manuel beim nächsten Update.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-05.

## P-2026-09-27-11 achsen-reihenfolge-verfahren

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-03; `camaddon/gui_verfahren.py`
  (_baue_raster), `camaddon/verfahren.py` (namen), `camaddon/gui_abfahren.py`
  (sortiert schon: Linearachsen zuerst, dann nach Namen).

### DATEIEN
- `camaddon/verfahren.py`, `camaddon/gui_verfahren.py`
- `tests/test_verfahren.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Maschine verfahren“ zeigt die Achsen in Lesereihenfolge: Linearachsen nach
Namen, dann positionierende Rundachsen, dann Spindeln, zuletzt der Revolver.

### DONE
- `verfahren.fensterreihenfolge(maschine, achsen)`; das Fenster baut seine
  Zeilen in dieser Reihenfolge (vorher die der Gelenkkette: Y1, Z1, X1 an der
  3-Achs-Fräse). „Wie im Programm“ folgt mit: X, Y (die Schlitten), Z1 …

### TEST
- `test_verfahren`: Drehmaschine → X1, Z1, C4, T.
- Szenarien `beispielmaschine`, `verfahren`, `verfahren_schraeg`, `mausrad` in
  1.1.3 ok; Screenshots angesehen (Fräse: X1, Y1, Z1, Spindelachse;
  Drehmaschine wie im Programm: X, Y, Z1).
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-04.

## P-2026-09-27-10 schnittwerte-job-erklaert

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-02; `camaddon/gui_job_schnittwerte.py`
  (Befehl), `camaddon/gui_maschine.py` (so machen es die anderen Befehle),
  `tests/gui/szenario_schnittwerte_job.py`.

### DATEIEN
- `camaddon/gui_job_schnittwerte.py`
- `translations/de.json`, `translations/en.json` (`sj.kein_job`)
- `tests/gui/szenario_schnittwerte_job.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Schnittwerte in den Job“ ist immer bedienbar; ohne Job im aktiven Dokument
sagt ein Satz, was zu tun ist.

### DONE
- `IsActive` immer wahr (wie „Maschine bearbeiten“, „Auf der Maschine
  prüfen“); ohne Job: „Im aktiven Dokument gibt es keinen CAM-Job. Öffne das
  Dokument mit dem Job – dann setzt dieser Befehl Drehzahl und Vorschub seiner
  Werkzeug-Controller aus der Werkzeugverwaltung.“
- Den Job auch in anderen offenen Dokumenten zu suchen ist D-21 (nicht hier).

### TEST
- `szenario_schnittwerte_job` in 1.1.3 ok – ruft den Befehl zuerst ohne
  Dokument auf und erwartet den Satz; `test_sprache` ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-03.

## P-2026-09-27-09 tooltip-pruefen

### EINGELESEN
- `docs/durchsicht_bedienbarkeit.md`, D-01; `camaddon/gui_reichweite.py`
  (Befehl), `tests/gui/szenario_erster_start.py`.

### DATEIEN
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_erster_start.py`
- `docs/durchsicht_bedienbarkeit.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Tooltip von „Auf der Maschine prüfen“ nennt alle drei Prüfungen:
Achsgrenzen, Abfahren, Kollision.

### DONE
- „Prüft einen CAM-Job auf einer Maschine: Reichen die Achsen, wie fährt die
  Maschine die Bahn ab, stößt dabei etwas an?“ (englisch entsprechend).

### TEST
- `szenario_erster_start` in 1.1.3 ok – prüft jetzt auch diesen Tooltip.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- D-02.

## P-2026-09-27-08 gelenke-ausblenden

### EINGELESEN
- Die Bilder zu P-2026-09-27-07: In der Gesamtansicht lagen die
  Gelenkmarkierungen (weiße Scheiben mit Achsen) auf Revolver und Spindel;
  ohne sie war der Revolver zu sehen – Manuel: „Besser weiter“.
- `camaddon/beispielmaschine.py` (lade), die Stellen im Addon, die
  Sichtbarkeit nutzen (keine hängt an den Gelenken).

### DATEIEN
- `camaddon/beispielmaschine.py`
- `help/de/neue_maschine.html`, `help/en/neue_maschine.html`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Beispielmaschinen aus „Neue Maschine …“ und „Beispielmaschine laden …“
erscheinen ohne Gelenkmarkierungen; die Gelenke stehen weiter im Baum und
lassen sich mit der Leertaste zeigen, und die Hilfe sagt wie.

### DONE
- `lade()` blendet die Gelenkgruppe der Baugruppe aus (nur mit Oberfläche).
  Die Prüfungen bauen ihre Maschinen ohne `lade()` – für sie ändert sich
  nichts; eine selbst gebaute Baugruppe fasst das Addon nicht an.
- Hilfe „Neue Maschine“: ein Absatz, wie man die Gelenke zeigt.

### TEST
- Szenarien `beispielmaschine`, `neue_maschine`, `schraege_achse`,
  `verfahren_schraeg`, `mausrad` in 1.1.3 ok; die Übersicht aller fünf
  Beispielmaschinen angesehen – keine Markierungen mehr.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Durchsicht W-004: die kleinen Punkte D-01 bis D-08.

## P-2026-09-27-07 revolver-stationen

### EINGELESEN
- Manuel zum Screenshot der Drehmaschine: „Die Revolver … müsste man anders
  aufbauen, der Revolver ist da nicht sichtbar“; nach den Vorher-/Nachher-
  Bildern des Entwurfs: „Besser weiter“.
- `camaddon/beispielmaschine.py` (Baukasten, drehmaschine),
  `tests/beispielmaschinen.py` (Test-Drehmaschine), die Tests mit der
  Drehmaschine (Plätze, Werkzeugspitzen – sie rechnen aus den LCS, nicht mit
  festen Koordinaten), `help/*/neue_maschine.html`.

### DATEIEN
- `camaddon/beispielmaschine.py`
- `help/de/neue_maschine.html`, `help/en/neue_maschine.html`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Beispiel-Drehmaschine zeigt einen Revolver, den man als solchen erkennt:
rundum je Platz eine Station, die Scheibe heller als Schlitten und Bett;
Gelenk, Plätze und Werkzeuge bleiben, wo sie waren.

### DONE
- Befund in Bildern: Die Revolverscheibe war eine glatte Scheibe in der Farbe
  der Tische (grau wie die Schlitten), nur zwei Halter; von der Seite
  verdeckt, in der Gesamtansicht unter den Gelenkmarkierungen.
- Je Platz ab P2 eine Station (Block außen an der Scheibe, im Teilungswinkel
  gedreht, Breite 60 % der Teilung, höchstens 60 mm – so bleibt auch bei 24
  Plätzen Luft); P1 hat seinen radialen Halter. Die Scheibe bekommt die
  Farbe REVOLVER (hell). `Baukasten.quader(…, gedreht=…)`: eine Drehung im
  Rahmen, hier um die Revolverachse.
- Die Stationen gehören zum Bauteil „Revolver“ – die Kollision prüft sie
  mit (an der Maschine sitzen dort Halter).
- Die Test-Drehmaschine (`tests/beispielmaschinen.py`, ein Würfel als
  Revolver) bleibt: Sie spielt eine grob selbst gebaute Baugruppe, sogar mit
  senkrechter Spindel. Ihre Bilder zeige ich Manuel nicht mehr als „die
  Drehmaschine“.

### TEST
- Die Prüfungen mit der Drehmaschine in 1.1.3 ok (`test_abfahren`,
  `test_beispielmaschine`, `test_kette`, `test_maschine`, `test_reichweite`,
  `test_schraege_achse`); die Szenarien `beispielmaschine`,
  `neue_maschine`, `schraege_achse`, `verfahren_schraeg`, `mausrad` ok;
  Screenshots angesehen (Revolver in „Maschine bearbeiten“, alle fünf
  Beispielmaschinen).
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel schaut sich den Revolver in seinem FreeCAD an („Neue Maschine …“ →
  Drehmaschine mit Y-Achse).

## P-2026-09-27-06 durchsicht-bedienbarkeit

### EINGELESEN
- Manuels Auftrag: „noch einmal schauen, ob alles so benutzer-/bedienerfreundlich
  und einfach ist wie möglich und ob man Sachen noch automatisieren könnte …
  Schreibe diese auf.“
- `docs/arbeitsregeln.md` (Abschnitte 0, 1, 6, 8), `CHATSTART.md`,
  `docs/STATUS_SNAPSHOT.md` (Wunschliste).
- Screenshots aller 30 Szenarien in FreeCAD 1.1.3 (frischer Lauf auf
  5df5005); dazu im Code: `gui_start.py` (Befehle, Werkzeugleiste),
  `gui_reichweite.py` (Job- und Maschinensuche, Aufbau des Fensters),
  `gui_maschine.py` (Meldung ohne Baugruppe, neue Betriebsart),
  `maschine.py` (Kennwerte), `verfahren.py` (Reihenfolge der Achsen),
  `gui_schruppwerte.py` (Maschinengrenzen, Beispielwerte, gemerkte Werte),
  `job_schnittwerte.py`, `gui_aktualisierung.py`, `gui_sprachwahl.py`,
  `sprache.py`.

### DATEIEN
- `docs/durchsicht_bedienbarkeit.md` (neu)
- `docs/STATUS_SNAPSHOT.md` (W-004, Hinweis beim nächsten Schritt)
- `CHATSTART.md` (Zeile in der Lesekarte)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Befunde der Durchsicht stehen je mit Beleg, Vorschlag, „Fertig, wenn“ und
Aufwand in `docs/durchsicht_bedienbarkeit.md`, als W-004 in der Wunschliste,
mit einer Reihenfolge und den offenen Fragen als Auswahl mit Empfehlung.

### DONE
- 24 Befunde: acht kleine Stellen (D-01 bis D-08: veralteter Tooltip, grauer
  Knopf ohne Erklärung, Achsen im Verfahren in Kettenreihenfolge, kein
  „Jetzt neu starten“, Auswahl leuchtet, Rückmeldung ohne den kurzen Weg,
  Spanneisen nicht erwähnt, zwei Namen für dasselbe Fenster), fünf zum
  einfacheren Bedienen (D-10 bis D-14) und elf zum Automatisieren (D-20 bis
  D-30).
- Beim Nachprüfen im Code korrigiert, bevor es ins Dokument kam: Der Planer
  merkt sich Drehzahl, Vorschub und Leistung (nur nicht je Maschine); der
  Platzhalter heißt „bitte eintragen“; „Beispielmaschine laden …“ öffnet
  wirklich das Fenster von „Neue Maschine …“; die Sprache folgt schon der von
  FreeCAD (kein Befund).
- Nicht bestätigt und deshalb kein Befund: der abgeschnittene Text auf der
  Einstellungsseite – das Szenario zwingt die Seite auf 500 × 320 Pixel.

### TEST
- Nur Doku. Die Szenarien liefen für die Screenshots in 1.1.3 alle grün
  (`scripts/oberflaeche_testen.sh`, 30 × ok). Geprüft hat Claude anhand von
  Screenshots; ob die Fenster verständlich sind, prüft Manuel.

### NEXT
- Manuel wählt die Reihenfolge und beantwortet die Fragen in Abschnitt 6;
  D-01 bis D-08 brauchen keine Entscheidung.

## P-2026-09-27-05 snapshot-nachbesserungen

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md` (Projektstatus, W-001).

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot nennt die Nachbesserungen P-2026-09-27-02 bis -04.

### DONE
- Projektstatus W-001, 4c: ein Satz zu den Nachbesserungen (Schneide nach
  Art, halbe Zahl im Feld, Spaltenköpfe im Halter-Fenster).

### TEST
- Nur Doku; der Gesamtlauf für P-2026-09-27-02 bis -05 läuft vor dem Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-27-04 halter-spaltenkoepfe

### EINGELESEN
- Screenshot `szenario_halter/2_er32.png` aus dem Gesamtlauf für 0.24.0: Die
  Überschrift „Ø unten (mm)“ der Kontur-Tabelle war abgeschnitten („(mm]“).
- `camaddon/gui_halter.py` (_bereich_halter, Tabelle).

### DATEIEN
- `camaddon/gui_halter.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Fenster „Halter“ sind alle drei Überschriften der Kontur-Tabelle ganz zu
lesen, auch in der Standardgröße des Fensters; die Breite richtet sich nach
den Überschriften der gewählten Sprache.

### DONE
- Die Spalten bleiben gleich breit (gedehnt); die Tabelle ist mindestens so
  breit, dass die längste Überschrift in jede Spalte passt – gemessen in
  fetter Schrift: Solange eine Zeile gewählt ist, zeigt Qt die Überschriften
  fett (der erste Versuch mit `sectionSizeHint` rechnete mit normaler
  Schrift und reichte nicht). Dazu Rand, Zeilennummern und Rahmen; das
  Fenster wird dadurch etwa 20 Pixel breiter.

### TEST
- `szenario_halter` in 1.1.3 und im Wochen-Build: Screenshot `2_er32.png`
  angesehen – alle drei Überschriften ganz zu lesen, auch „Ø unten (mm)“.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-27-03 halbe-zahl-im-feld

### EINGELESEN
- `camaddon/gui_zahlen.py` (Zahlenpruefer: „,“ und „-“ sind ein Zwischenstand;
  `groesse_lesen` wirft dann ValueError), `camaddon/einheiten.py`
  (zahl_aus_text).
- `camaddon/gui_halter.py` (Spanntiefe, OK), `camaddon/gui_kollision.py`
  (Warnabstand), `camaddon/gui_reichweite.py` (Nullpunkt, Uhr),
  `camaddon/gui_werkzeuge.py` (_zahl_uebernehmen vor dem Speichern),
  `camaddon/gui_werkstoffe.py` (OK: kc, mc); alle übrigen Aufrufe von
  `zahl_lesen`/`groesse_lesen` fangen den Fehler schon ab.
- `tests/gui/_lauf/szenario_lauf.py` (Ausnahmen in Qt-Slots fängt es nicht).

### DATEIEN
- `camaddon/gui_halter.py`, `camaddon/gui_kollision.py`,
  `camaddon/gui_reichweite.py`, `camaddon/gui_werkzeuge.py`,
  `camaddon/gui_werkstoffe.py`
- `tests/gui/szenario_halter.py`, `tests/gui/szenario_kollision.py`,
  `tests/gui/szenario_reichweite.py`, `tests/gui/szenario_werkzeugverwaltung.py`,
  `tests/gui/szenario_werkstoffe.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Feld, in dem noch keine Zahl steht („,“ oder „-“, das der Prüfer beim
Tippen zulässt), führt zu keinem Fehler: Im Halter-Fenster schließt OK, die
Spanntiefe bleibt; „Kollision prüfen“ rechnet mit dem Warnabstand der Vorgabe;
im Nullpunkt zählt „-“ wie ein leeres Feld (der Vorschlag); OK in der
Werkzeugverwaltung und im Werkstoff-Fenster speichert, das Feld behält den
alten Wert.

### DONE
- Beim Durchsehen gefunden: `groesse_lesen(",")` wirft ValueError. Im
  Halter-Fenster schloss OK dann nicht (Traceback im Ausgabefenster);
  „Kollision prüfen“ tat nichts; im Nullpunkt – wer „-50“ tippt und nach dem
  „-“ kurz innehält – warf die Uhr des Fensters einen Traceback, und die
  Anzeige blieb auf dem alten Stand (seit 4a). Ebenso OK in der
  Werkzeugverwaltung (das Zahlenfeld mit dem Fokus wird vor dem Speichern
  gelesen) und im Werkstoff-Fenster (kc, mc): Das Fenster blieb offen.
- Spanntiefe: Unlesbares bleibt, wie es war (wie in der Kontur-Tabelle).
- Warnabstand: `_eingetragen()` – leer oder unlesbar 0, dann die Vorgabe;
  gemerkt wird nur, was lesbar eingetragen ist.
- Nullpunkt: `eingetragen()` lässt ein Feld ohne Zahl weg wie ein leeres.
- Werkzeugverwaltung: ein Feld ohne Zahl zeigt wieder den gespeicherten
  Wert; Werkstoff-Fenster: kc und mc bleiben, wie sie waren.

### TEST
- `szenario_halter`: „,“ in der Spanntiefe, OK → das Fenster ist zu, die
  Spanntiefe 40 (ER32) geblieben.
- `szenario_kollision`: „,“ als Warnabstand, „Kollision prüfen“ → Ergebnis
  mit 1 mm, ein Satz.
- `szenario_reichweite`: X „300“ (rot), dann „-“ → grün wie mit leerem Feld.
- `szenario_werkzeugverwaltung`: „,“ im Eckenradius von T2, OK → zu,
  gespeichert 0,5.
- `szenario_werkstoffe`: neuer Werkstoff „Buche“ mit „,“ in kc, OK → zu,
  kc unbekannt (0).
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-27-02 schneide-nach-art

### EINGELESEN
- `camaddon/kollision.py` (werkzeugkoerper), `camaddon/reichweite.py`
  (Werkzeugmasse, werkzeugmasse), `camaddon/werkzeuge.py` (reichweite, mass,
  ANTEIL_VON_D, Felder je Art), `camaddon/gui_abfahren.py` (_werkzeug).
- `docs/spezifikation_simulation.md`, 4b (Werkzeug) und 4c (Was gegen was).

### DATEIEN
- `camaddon/werkzeuge.py`, `camaddon/reichweite.py`, `camaddon/kollision.py`
- `tests/test_kollision.py`
- `docs/spezifikation_simulation.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Abfahren und Kollision bauen die Schneide wie die Reichweite
(`wz.reichweite`): beim Nutenfräser so hoch wie die Schneidenbreite, beim
Lollipopfräser als Kugel mit D, der Hals ab ihrer Mitte; die übrigen Arten
wie bisher (Schneidenlänge, leer geschätzt). Ein Werkzeug nur aus CAM: die
Schneide aus CuttingEdgeHeight, sonst CuttingEdgeLength, sonst BladeThickness,
erst dann 2 × D.

### DONE
- Beim Durchsehen von 4c gefunden: `werkzeugmasse` nahm immer die
  Schneidenlänge. Nutenfräser und Lollipopfräser haben dieses Feld nicht –
  es galt die Schätzung 2 × D. Ein Nutenfräser Ø 20 war so ein 40 mm hoher
  Zylinder statt einer Scheibe (falsche Berührungen im Eilgang und mit
  Spannmitteln); beim Lollipop saßen Hals und Schaft 1,5 × D zu hoch (eine
  Berührung des Schafts konnte durchrutschen).
- `wz.schneide(werkzeug)`: von der Spitze bis zum Hals – Lollipop D/2,
  Nutenfräser Schneidenbreite, sonst Schneidenlänge; `wz.reichweite` rechnet
  damit (gleiche Werte wie bisher).
- `Werkzeugmasse.kugel` (Lollipop) und `schneide` aus `wz.schneide`;
  `werkzeugkoerper` baut beim Lollipop eine Kugel. Das Bild im Abfahren
  zeigt dieselben Körper.
- Ein Werkzeug nur aus CAM (nicht in der Werkzeugverwaltung): die Schneide
  auch aus CuttingEdgeLength (Gewindebohrer) und BladeThickness
  (Scheibenfräser) – wie beim Übernehmen aus CAM; sonst war eine Säge Ø 50
  ein 100 mm hoher Zylinder.

### TEST
- `tests/test_kollision.py`: Lollipop Ø 5 – Kugel (Volumen, ab Z −60), Hals
  −57,5 … −47,5, Schaft bis −10; Nutenfräser Ø 5 – Scheibe −60 … −59,5,
  Hals −59,5 … −58,25 mit Ø 1,5; eine Säge nur aus CAM (Ø 50, Blatt 3):
  Schneide 3, Schaft 10, Länge 40.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-27-01 ok-meldung-hinter-fortschritt

### EINGELESEN
- `scripts/tests_ausfuehren.sh`, `scripts/alle_tests.sh`, `docs/aufbau.md`
  (Abschnitt Prüfungen).
- Protokoll des Gesamtlaufs für 0.24.0 (P-2026-09-26-99): in 1.1.3
  „FEHLER test_kollision.py“, obwohl die Prüfung durchlief – die Zeile war
  `\t…(60 %)\tOK test_kollision.py`.

### DATEIEN
- `scripts/tests_ausfuehren.sh`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`OK <datei>` zählt auch, wenn FreeCADCmds Fortschritt („(60 %)“ mit
Tabulatoren und Wagenrücklauf, ohne Zeilenumbruch) davor auf derselben Zeile
steht; ebenso `UEBERSPRUNGEN <datei>: Grund`. Eine Ausgabe ohne diese Meldung
am Zeilenende bleibt ein Fehler.

### DONE
- FreeCADCmd schreibt seinen Fortschritt ohne Zeilenumbruch; wann die
  OK-Meldung der Prüfung dazwischenkommt, ist Zufall (ein zweiter Lauf von
  `test_kollision.py` allein hatte sie auf eigener Zeile). Das Skript sucht
  `OK <datei>` jetzt am Zeilenende, am Zeilenanfang oder nach Leerraum statt
  als ganze Zeile; `UEBERSPRUNGEN` ebenso, den Grund liest es mit `sed`.

### TEST
- Mit einem nachgemachten FreeCADCmd: OK hinter Fortschritt → ok,
  UEBERSPRUNGEN hinter Fortschritt → skip mit Grund, `OK <datei>X` und eine
  Ausnahme → FEHLER.
- Die aufgezeichnete Zeile aus dem Protokoll: alte Suche FEHLER, neue ok.
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Push 0.24.0 (P-2026-09-26-94 bis P-2026-09-27-01) nach grünem Gesamtlauf.

## P-2026-09-26-99 version-0-24-0

### EINGELESEN
- Spezifikationen Halter (Schritte 1–3) und 4c (Schritte 1–2), alle gebaut
  (P-2026-09-26-94 bis -98).
- `package.xml`, README, „Über“ (0.23.0, P-2026-09-26-91).

### DATEIEN
- `package.xml` (0.24.0, Beschreibung)
- `README.md` (Kollision unter „Auf der Maschine prüfen“, Halter in der
  Werkzeugverwaltung)
- `translations/de.json`, `translations/en.json` („Über“)
- `docs/STATUS_SNAPSHOT.md`, `docs/spezifikation_simulation.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Version 0.24.0; README, Beschreibung für den Addon-Manager und „Über“ nennen
Halter und Kollisionsprüfung; `scripts/alle_tests.sh` in beiden
FreeCAD-Versionen grün.

### DONE
- Version 0.24.0: Halter (W-002 Stufe D) und Kollision (W-001 Stufe 4c).
- README, Addon-Manager, „Über“: Halter mit Kontur und Vorlagen; die
  Kollisionsprüfung von Werkzeug, Halter und Maschine gegen Teil, Spannmittel
  und Maschine.
- Snapshot: Halter und 4c fertig, Klickweg zum Ausprobieren (Punkt 7);
  danach Manuels Test, offen 4d und W-003 V2.

### TEST
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push.

### NEXT
- Manuel probiert Halter und Kollision aus (Snapshot, Punkt 7).

## P-2026-09-26-98 kollision-fenster

### EINGELESEN
- `docs/spezifikation_simulation.md`, 4c, Schritt 2; Abschnitt 12
  (Akzeptanzkriterien 4c).
- `gui_reichweite.py` (Fenster, Abspieler, Bild), `gui_abfahren.py` (Bild,
  Lupe), `kollision.py` (P-2026-09-26-97).

### DATEIEN
- `camaddon/gui_kollision.py` (neu)
- `camaddon/gui_reichweite.py` (Bereich „Kollision“ unter „Abfahren“, Klick
  auf einen Befund, Sperren während der Prüfung, Erklärung oben)
- `camaddon/gui_abfahren.py` (rote Kugel `markiere`, `zeige_stelle`)
- `camaddon/kollision.py` (Fortschritt alle 0,1 s mit Abbrechen, auch mitten
  in langen Wegen; Berührungen zuerst)
- `camaddon/beispielmaschine.py` (Spanneisen immer, 60 mm hoch)
- `translations/de.json`, `translations/en.json` (13 Texte, Erklärung oben)
- `help/de/reichweite.html`, `help/en/reichweite.html` (Abschnitt „Kollision“)
- `tests/test_kollision.py`, `tests/gui/szenario_kollision.py` (neu)
- `docs/spezifikation_simulation.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Fräse, kurzes Werkzeug (25 mm) neben dem rechten Spanneisen in die
Tiefe → „Kollision prüfen“ → rot „Es stößt etwas an:“ und „In „Eigene“
berühren sich „Spindel“ und „Spanneisen_rechts“ (Satz 4, bei X 110, Y 30, Z
34).“ → Klick → die Maschine steht dort, die Ansicht zeigt die Stelle mit
einer roten Kugel.

### DONE
- Bereich „Kollision“: Warnabstand (leer 1 mm, gemerkt), „Kollision prüfen“ –
  während der Prüfung Fortschrittsbalken, der Knopf heißt „Abbrechen“, Job,
  Nullpunkt, Liste und Abspieler sind gesperrt. Urteil grün („Nichts berührt
  sich, nichts kommt näher als 1,00 mm.“), rot („Es stößt etwas an:“) oder
  gelb; je Befund ein Satz in Rot oder Gelb, Berührungen zuerst; Hinweise
  grau. Neuer Job, Nullpunkt oder Aufnahme: „Noch nicht geprüft …“.
- Klick auf einen Satz: Abspieler auf die Zeit der Stelle, rote Kugel (2 mm,
  mit Hof, obenauf gezeichnet), die Ansicht rückt die Stelle in die Mitte.
  Fährt der Abspieler weiter, verschwindet die Kugel.
- Schließen während der Prüfung bricht sie ab, ohne noch etwas zu zeigen.
- Beispiel-Fräse: die zwei Spanneisen immer, 60 mm hoch (mit 30 mm reichte
  die Spindelnase in ihrer tiefsten Stellung genau bis obenauf – anstoßen
  ging nur am Anschlag, im Screenshot gesehen).

### TEST
- `szenario_kollision` (neu) in 1.1.3 und im Wochen-Build grün, Screenshots
  angesehen: Urteil, Satz, Klick → Abspieler, Kugel, Ansicht auf der Stelle;
  Warnabstand 10 → gelbe Sätze dazu; neuer Nullpunkt → „Noch nicht geprüft“;
  Schließen räumt auf. `szenario_abfahren` in beiden grün.
- `test_kollision` (angepasst an die 60-mm-Spanneisen: Spindel setzt bei Z
  34 auf, Satz 4; Eilgang-Fall mit 80 mm Werkzeug, weil mit 50 mm die Spindel
  1 mm über die Spanneisen fährt – zu Recht gemeldet), `test_beispielmaschine`,
  `test_sprache`, `test_hilfe` grün; black, ruff sauber.

### NEXT
- Version 0.24.0, voller Lauf in beiden Versionen, Push, Bericht.

## P-2026-09-26-97 kollision-rechenkern

### EINGELESEN
- `docs/spezifikation_simulation.md`, 4c (P-2026-09-26-93), Schritt 1.
- `abfahren.py` (Stationen, wirksame Stellungen), `reichweite.py`
  (`_glied_lage`, `_lage`, `_job_lage`), `verfahren.py` (Ausgang, Wege,
  Grenzen), `kette.py` (Glieder, Achsen, Eltern und Kind), `halter.py`.
- Messung aus P-2026-09-26-93: `distToShape` 2–3 ms, 0 für „steckt drin“.
- Probe: `Part.getShape(bauteil, transform=False)` gibt die Form in eigenen
  Koordinaten; an ihren Ausgang gesetzt, liegt sie wie im Dokument.

### DATEIEN
- `camaddon/kollision.py` (neu)
- `camaddon/reichweite.py` (`Werkzeugmasse`, `werkzeugmasse`,
  `werkzeughalter` – aus gui_abfahren.py hierher, mit Hals)
- `camaddon/halter.py` (`form`: der Halter als Körper)
- `camaddon/abfahren.py` (`zeit_text` aus gui_abfahren.py hierher)
- `camaddon/gui_abfahren.py` (zeigt dieselben Werkzeugkörper, die geprüft
  werden)
- `camaddon/beispielmaschine.py` (`fraesmaschine(spanneisen=True)`)
- `translations/de.json`, `translations/en.json` (15 Texte)
- `tests/test_kollision.py` (neu)
- `docs/spezifikation_simulation.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
An der Beispiel-Fräse mit Spanneisen meldet die Prüfung für die Bahnen aus
`test_kollision` genau die von Hand nachgerechneten Berührungen und Warnungen
– Schaft an der Taschenwand, Eilgang durchs Teil, Halter zu tief, Spindel auf
dem Spanneisen – und sonst nichts.

### DONE
- Körper: Schneide, Hals, Schaft (bis zur Nase des Halters, ohne Halter bis
  zur Gesamtlänge) und Halter im LCS der Werkzeugaufnahme
  (`werkzeugkoerper`); das fertige Teil (Modelle des Jobs) am Nullpunkt; jedes
  Bauteil der Maschine in eigenen Koordinaten an seinem Glied. Lage zur Zeit t
  = Bewegung des Glieds · Lage im Ausgang, Achsen auf ihre Grenzen gesetzt.
- Paare je Werkzeugglied: Werkzeugseite (Werkzeug und die Glieder, die es
  tragen) gegen Werkstückseite (Teil und die Glieder, die es tragen) und
  Rest, Werkstückseite gegen Rest; die Schneide gegen das Teil nur im Eilgang.
  Paare aus Maschinenteilen oder Teil und Maschinenteil, die sich in der
  Grundstellung berühren, fallen weg – mit Hinweis nur, wenn sie nicht an
  einem gemeinsamen Gelenk hängen.
- Abtasten: je Weg zwischen zwei Stationen Schritte von höchstens (kleinster
  Abstand − Warnabstand) / Weg, mindestens 0,5 mm; Drehachsen zählen mit der
  Diagonale über alles je Grad. Hüllquader weiter als Warnabstand + 5 mm:
  kein genauer Abstand. Höchstens 200 000 Stellen; Fortschritt mit Abbrechen.
- Ergebnis: je Operation und Paar die schlimmste Stelle (bei Gleichstand die
  erste) als Satz – „In „Eigene“ berühren sich der Schaft von T1 und das Teil
  (Satz 5, bei X 67.5, Y 30, Z 8).“, „… kommen sich … auf 0.50 mm nahe …“, mit
  „im Eilgang“; dazu Zeit, Station, Stelle (für Abspieler und Markierung);
  Hinweise (ohne Halter geprüft, kein Modell, nicht rechenbar, abgebrochen).
- Die Beispiel-Fräse kann zwei Spanneisen tragen (am Tisch-Glied).
- Das Abfahren zeigt jetzt genau die Werkzeugkörper, die geprüft werden.

### TEST
- `test_kollision` (neu) in 1.1.3 und im Wochen-Build grün, je rund 4 s:
  frei in der Tasche nichts (unter 200 Stellen); Schaft an der Wand –
  Berührung, Satz 5, Stelle x 402,5 (die Wand unter der Spindel); Schaft Ø 4
  – Warnung 0,50 mm; Eilgang durchs Teil – Schneide und Schaft „im Eilgang“,
  erste Berührung bei X −2,5; derselbe Weg im Vorschub – nur der Schaft;
  Halter ER16 1 mm zu tief – Berührung; Spindel auf dem Spanneisen – bei Z
  knapp unter 4; 4 mm darüber nur mit Warnabstand 5; kein Hinweis zu
  Führungen; Abbrechen.
- `test_abfahren`, `test_reichweite`, `test_halter`, `test_beispielmaschine`,
  `test_sprache` grün; `szenario_abfahren` grün; black, ruff sauber.

### NEXT
- 4c Schritt 2: Bereich „Kollision“ im Fenster „Auf der Maschine prüfen“.

## P-2026-09-26-96 halter-laenge-abfahren

### EINGELESEN
- `docs/spezifikation_halter.md`, Schritt 3 (Abschnitt 7: wo der Halter wirkt).
- `camaddon/reichweite.py` (`werkzeuglaenge`, Hinweise zur Länge),
  `camaddon/gui_abfahren.py` (Bild: Werkzeug, angedeuteter Halter).

### DATEIEN
- `camaddon/reichweite.py` (Quelle LAENGE_HALTER, Hinweis)
- `camaddon/gui_abfahren.py` (`halter_von`, Halter mit Kontur im Bild)
- `translations/de.json`, `translations/en.json` (1 Text)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/test_reichweite.py`, `tests/gui/szenario_abfahren.py`
- `docs/spezifikation_halter.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Werkzeug der Werkzeugverwaltung mit Halter und ohne gemessene Länge ab
Spindelnase: „Auf der Maschine prüfen“ rechnet mit Halterlänge + Gesamtlänge
− Spanntiefe und sagt es; beim Abfahren steckt das Werkzeug in diesem Halter,
mit seiner Kontur.

### DONE
- `werkzeuglaenge`: gemessen vor Halter; sonst mit dem Halter geschätzt
  (`LAENGE_HALTER`), Hinweis „gerechnet mit 100,00 mm, geschätzt aus Halter und
  Werkzeug (…) – genauer mit der gemessenen Länge ab Spindelnase“; ohne Halter
  wie bisher.
- Abfahren: je Operation der Halter ihres Werkzeugs (`Bild.halter`), je
  Abschnitt ein Zylinder oder Kegel (Part, als Dreiecke) ab der Aufnahme –
  stahlgrau, nicht durchscheinend; ohne Halter wie bisher angedeutet.
- Hilfe „Auf der Maschine prüfen“: Halter im Abfahren und in der Länge.

### TEST
- `test_reichweite` (neu: ER16 70 mm + 50 − 20 = 100 mm, Z1 −38 … −20,
  Hinweis; gemessen geht vor), `test_abfahren`, `test_halter`, `test_hilfe` grün
  in 1.1.3 und im Wochen-Build; `szenario_abfahren` (jetzt mit T1 in der
  Werkzeugverwaltung und Halter ER16: Halter im Bild, Hinweis zur Länge) und
  `szenario_reichweite` grün in beiden Versionen, Screenshot angesehen: Flansch,
  Kegel und Mutter unter der Spindel, darunter Schaft und Schneide.

### NEXT
- 4c Schritt 1: Rechenkern Kollision.

## P-2026-09-26-95 halter-fenster

### EINGELESEN
- `docs/spezifikation_halter.md`, Schritt 2 (Skizze in Abschnitt 5).
- `camaddon/gui_werkstoffe.py` (Fenster aus der Werkzeugverwaltung, Muster),
  `camaddon/gui_werkzeuge.py` (Felder, Anordnung, Platzhalter),
  `camaddon/gui_schnittwerte.py` (Zahlen in Tabellen), `gui_werkzeugbild.py`.

### DATEIEN
- `camaddon/gui_halter.py` (neu)
- `camaddon/gui_werkzeuge.py` (Feld „Halter“ mit „Halter …“, Platzhalter der
  Länge ab Spindelnase mit Halter)
- `camaddon/hilfe.py`, `help/de/halter.html`, `help/en/halter.html` (neu),
  `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `translations/de.json`, `translations/en.json` (38 Texte, 1 geändert)
- `tests/gui/szenario_halter.py` (neu)
- `docs/spezifikation_halter.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Werkzeug mit Gesamtlänge 83 → „Halter …“ → „Neu“ →
„Spannzangenfutter ER32 · SK40“ → Tabelle 16/63/63 und 54/50/50, „Länge 70,00
mm · größter Ø 63,00 mm“, Bild mit Werkzeug → OK → beim Werkzeug ist der
Halter gewählt, das leere Feld „Länge ab Spindelnase“ zeigt grau „leer: 113
mit Halter“.

### DONE
- Fenster „Halter“: links Suche, Liste nach Namen, „Neu“ mit Menü (leer oder
  eine der elf Vorlagen), „Kopieren“, „Löschen“ (Rückfrage nennt die Werkzeuge,
  die ihn benutzen); rechts Name, Bezeichnung, Spanntiefe, die Kontur als
  Tabelle (Länge, Ø oben, Ø unten – nur Zahlen, im gewählten Maßsystem),
  „+ Abschnitt“ (unter dem gewählten, so dick wie dessen Ende) und „−
  Abschnitt“ (einer bleibt), darunter Länge und größter Ø, wer ihn benutzt,
  daneben das Bild: Spindel, Halter im Schnitt, Werkzeug bis zur Spitze.
- Gearbeitet wird an einer Kopie der Bibliothek; über OK steht grau, was OK
  tut („OK: T1 bekommt den Halter …“). OK übernimmt Halter und Zuordnungen,
  Abbrechen verwirft; gespeichert wird mit der Werkzeugverwaltung.
- Werkzeugverwaltung: unter der Länge ab Spindelnase die Zeile „Halter“
  (Auswahl „– ohne –“ und alle Halter, dazu „Halter …“) über die ganze Breite
  – im ersten Screenshot war „SK40 ER32 A70“ abgeschnitten. Der Platzhalter
  der Länge ab Spindelnase rechnet mit dem Halter.
- Hilfeseite „Halter“ (de, en), Verweis aus der Hilfe der Werkzeugverwaltung.

### TEST
- `szenario_halter` (neu), `szenario_werkzeugverwaltung`, `szenario_felder` in
  1.1.3 und im Wochen-Build grün, Screenshots angesehen; `test_sprache`,
  `test_hilfe` grün; black, ruff sauber.

### NEXT
- Schritt 3: Länge in „Auf der Maschine prüfen“, Halter im Abfahren.

## P-2026-09-26-94 halter-datenmodell

### EINGELESEN
- `docs/spezifikation_halter.md` (P-2026-09-26-93), Schritt 1.
- `camaddon/werkzeuge.py` (Werkzeug, Bibliothek, Speicherung, `reichweite`,
  `laenge_fuer_cam`), `tests/test_werkzeuge.py`.

### DATEIEN
- `camaddon/halter.py` (neu)
- `camaddon/werkzeuge.py` (Werkzeug.halter, `laenge_mit_halter`,
  Bibliothek.halter mit Anlegen, Kopieren, Löschen, Suche, Länge ab
  Spindelnase; Speichern und Laden)
- `translations/de.json`, `translations/en.json` (13 Texte)
- `tests/test_halter.py` (neu)
- `docs/spezifikation_halter.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Halter aus der Vorlage „Spannzangenfutter ER32“ hat 70 mm Länge und die
Kontur Flansch Ø63 × 16, Körper Ø50 × 54; einem Werkzeug mit 83 mm
Gesamtlänge zugeordnet, gilt ohne gemessene Länge 113 mm ab Spindelnase;
gespeichert und geladen bleibt alles, wie es war.

### DONE
- `halter.Halter`: Kennung, Name, Bezeichnung, Spanntiefe, Abschnitte
  (Länge, Ø oben, Ø unten); `laenge`, `groesster_durchmesser`,
  `radius_bei(abstand)` (Kegel geradlinig, an Stufen der größere Radius,
  außerhalb 0), `kontur()` als Punkte. Elf Vorlagen mit typischen SK40-Maßen
  (ER16–ER40, Schrumpf Ø6/Ø12, Weldon, Hydrodehn, Aufsteckdorn, Bohrfutter,
  VDI30 axial), Bezeichnung „Beispielmaße – nach Katalog prüfen“.
- Werkzeug: Feld `halter` (Kennung). `laenge_mit_halter`: Halterlänge +
  Gesamtlänge (eingetragen, sonst geschätzt) − Spanntiefe, mindestens
  Halterlänge + Reichweite.
- Bibliothek: `halter`; `halter_von`, `laenge_ab_spindelnase` (gemessen, sonst
  mit Halter, sonst 0), `neuer_halter` (leer oder aus Vorlage, Name mit „(2)“,
  wenn es ihn gibt), `kopiere_halter`, `benutzt_von`, `entferne_halter` (die
  Werkzeuge sind danach ohne), `sortierte_halter`. Gespeichert unter
  `halter`; alte Dateien ohne Halter und Unlesbares gehen.

### TEST
- `test_halter` (neu) in 1.1.3 und im Wochen-Build grün; `test_werkzeuge`,
  `test_sprache` grün; black, ruff sauber.

### NEXT
- Schritt 2: Fenster „Halter“ und das Feld im Werkzeug.

## P-2026-09-26-93 spezifikation-halter-kollision

### EINGELESEN
- Manuels Antworten vom 2026-09-26: Halter „eigene Halter-Verwaltung“
  (nicht der empfohlene Zylinder je Werkzeug), 4c prüft gegen „fertiges Teil
  + Spannmittel“, meldet „Berührung + Warnabstand“, als Nächstes „4c
  Kollision“; dazu „eigenes Fenster“ für die Halter und „Länge gemessen,
  sonst geschätzt“.
- `docs/spezifikation_simulation.md` (4c-Entwurf, Fragen 4 und 5),
  `camaddon/werkzeuge.py` (Bibliothek, Werkzeug, Speicherung),
  `camaddon/gui_werkzeuge.py` (Aufbau des Dialogs), `beispielmaschine.py`.
- FreeCAD-Check: `Mod/CAM/Path/Tool` in 1.1.3 und im Wochen-Build kennt
  keinen Halter. Gemessen: `distToShape` zwischen Werkzeug mit Halter und
  Schraubstock bzw. Teil mit Tasche 2–3 ms, „steckt drin“ gibt 0; kein scipy,
  numpy da.

### DATEIEN
- `docs/spezifikation_halter.md` (neu)
- `docs/spezifikation_simulation.md` (Stand, 4c, Grenzen, Entscheidungen
  4, 5, 7, 8, Akzeptanzkriterien 4c)
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe D verweist)
- `docs/STATUS_SNAPSHOT.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer `docs/spezifikation_halter.md` und Abschnitt 5 (4c) der Simulation liest,
weiß, was ein Halter ist, wie die Werkzeugverwaltung ihn zeigt, wie 4c prüft
und was es meldet – mit Manuels Entscheidungen und den Schritten.

### DONE
- Halter-Spezifikation: Kontur in Abschnitten (Länge, Ø oben, Ø unten) ab der
  Spindelnase, Länge, Spanntiefe, Vorlagen; je Werkzeug ein Halter; Länge ab
  Spindelnase leer → Halterlänge + Gesamtlänge − Spanntiefe; Fenster mit
  ASCII-Skizze; Speicherung; drei Schritte; Entscheidungen (Manuel 1–3,
  Claude 4–7); Akzeptanzkriterien.
- 4c: was gegen was (Werkzeug gegen Teil – Schneide nur im Eilgang –,
  gegen Maschinenteile der anderen Seite; mitfahrende Maschinenteile gegen
  Werkstückseite und Teil; kein Rohteil; Paare, die sich in der
  Grundstellung berühren, nicht), Berührung rot, Warnabstand gelb (1 mm,
  einstellbar), Rechenweg mit `distToShape` und Schritten nach dem Abstand,
  Sätze wie 4a, auf Knopfdruck; zwei Schritte; Akzeptanzkriterien.

### TEST
- Nur Doku.

### NEXT
- Halter Schritt 1: Datenmodell, Speicherung, Vorlagen, geschätzte Länge.

## P-2026-09-26-92 abfahren-lupe

### EINGELESEN
- Screenshots aus `szenario_abfahren` (P-2026-09-26-90): Die Maschine ist
  groß, Teil und Werkzeug klein – fürs Szenario musste die Kamera von Hand
  heran; Manuel müsste das mit dem Mausrad tun.
- `gui_abfahren.py`, `gui_reichweite.py`.

### DATEIEN
- `camaddon/gui_abfahren.py` (`Bild.hinsehen`, Knopf mit Lupe, leere
  Achswert-Zeile ausgeblendet)
- `camaddon/gui_reichweite.py` (`_hinsehen`)
- `translations/de.json`, `translations/en.json` (1 Text)
- `help/de/reichweite.html`, `help/en/reichweite.html`
- `tests/gui/szenario_abfahren.py`
- `docs/spezifikation_simulation.md`, `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Knopf im Bereich „Abfahren“ richtet die Ansicht auf Werkstück und
Werkzeug; ohne Stellung auf der Bahn bleibt keine leere Zeile stehen.

### DONE
- Knopf mit FreeCADs Lupe („Auswahl einpassen“) neben dem Tempo:
  `Bild.hinsehen()` richtet die Kamera auf Rohteil, Teil, Bahn und Werkzeug
  (Coin `viewAll` mit etwas Rand) und holt die 3D-Ansicht der Maschine nach
  vorn.
- Die Zeile mit den Achswerten ist ausgeblendet, solange die Maschine nicht
  auf der Bahn steht (vor dem ersten Abspielen) – vorher stand dort eine
  Lücke.
- Hilfe: die Lupe unter „Abfahren“.

### TEST
- `szenario_abfahren` (klickt jetzt die Lupe: Ausschnitt unter einem Drittel
  der ganzen Maschine, Symbol vorhanden) und `szenario_hilfe` in 1.1.3 und im
  Wochen-Build grün, Screenshots angesehen; `test_sprache` grün; black, ruff
  sauber.

### NEXT
- Voller Lauf, Push.

## P-2026-09-26-91 version-0-23-0

### EINGELESEN
- Spezifikation 4b, Schritt 3: Version, voller Lauf, Push.
- `package.xml`, README, „Über“ (0.22.0, P-2026-09-26-87).

### DATEIEN
- `package.xml` (0.23.0, Beschreibung)
- `README.md` (Abfahren unter „Auf der Maschine prüfen“)
- `translations/de.json`, `translations/en.json` („Über“)
- `docs/spezifikation_simulation.md`, `docs/STATUS_SNAPSHOT.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Version 0.23.0; README, Beschreibung für den Addon-Manager und „Über“ nennen
das Abfahren; `scripts/alle_tests.sh` in beiden FreeCAD-Versionen grün.

### DONE
- Version 0.23.0: Stufe 4b „Abfahren“ komplett (P-2026-09-26-88 bis -90).
- README, Addon-Manager und „Über“: Die Maschine fährt die Bahnen eines
  CAM-Jobs ab.
- Snapshot und Spezifikation: 4b fertig; als Nächstes 4c, sobald Halter und
  Mindestabstand entschieden sind.

### TEST
- `scripts/alle_tests.sh` in 1.1.3 und im Wochen-Build, siehe Push-Eintrag
  im Commit dieses Laufs.

### NEXT
- Manuel probiert 4a und 4b aus (Snapshot, „Manuel probiert aus“ Punkt 7).
- 4c (Kollision) nach seinen Entscheidungen zu Halter und Mindestabstand.

## P-2026-09-26-90 abfahren-abspieler

### EINGELESEN
- Spezifikation 4b (P-2026-09-26-88), Schritt 2: Anzeige und Abspieler im
  Fenster „Auf der Maschine prüfen“, Hilfe, Szenario mit Screenshots.
- `gui_reichweite.py` (Fenster, `fahre_hin`, Rückgängig-Schritt beim
  Verfahren), `abfahren.py` (P-2026-09-26-89), `verfahren.py`.

### DATEIEN
- `camaddon/gui_abfahren.py` (neu)
- `camaddon/gui_reichweite.py` (Bereich „Abfahren“, Bild in der 3D-Ansicht,
  Klick auf eine Überschreitung stellt den Abspieler dorthin)
- `camaddon/abfahren.py` (Umkehrstellen auf Kreisen, `station_von`,
  `stellungen_an`, Vorschubsatz nie schneller als der Eilgang)
- `camaddon/reichweite.py` (`_Bogen.anteile`)
- `camaddon/verfahren.py` (`setze_alle`)
- `translations/de.json`, `translations/en.json` (13 Texte, Erklärung oben)
- `help/de/reichweite.html`, `help/en/reichweite.html` (Abschnitt „Abfahren“,
  Werkzeuglänge mit Länge ab Spindelnase)
- `tests/test_abfahren.py`, `tests/gui/szenario_abfahren.py` (neu)
- `docs/spezifikation_simulation.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/aufbau.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im Fenster „Auf der Maschine prüfen“ fährt die Maschine die Bahn des Jobs
ab: In ihrer 3D-Ansicht liegen Rohteil, Teil und Bahn, das Werkzeug steckt in
seiner Aufnahme, alles fährt mit; Abspielen, Anhalten, Punkt vor und zurück,
Tempo, Operation und Schieber tun, was sie sagen; eine Achse über der Grenze
steht rot „am Anschlag“; Schließen räumt alles weg und fährt zurück.

### DONE
- `gui_abfahren.Bild`: Werkzeug (Schneide gelb, Schaft grau bis zur
  Gesamtlänge, Halter durchscheinend, wenn die Länge ab Spindelnase länger
  ist – Maße aus der Werkzeugverwaltung, sonst vom CAM-Werkzeug), Rohteil
  durchscheinend, Modell fest, Bahn als Linien (Vorschub blau, Eilgang rot)
  – Coin-Knoten in der 3D-Ansicht der Maschine, nichts im Dokument. `folge()`
  setzt sie nach jeder Bewegung auf die LCS der Aufnahmen (das Werkstück mit
  dem Nullpunkt des Jobs); je Operation ihr Werkzeug an ihrer Aufnahme.
- `gui_abfahren.Abspieler`: Operation, Anfang, Punkt zurück,
  Abspielen/Anhalten, Punkt weiter, Tempo ×1/×5/×20/×100, Schieber über die
  Zeit; darunter „„Kontur“ · Satz 6 von 11 · 0:03,1 von 0:22,4“ und die
  Stellung jeder Achse (Linearachsen zuerst, nach Namen), rot „am Anschlag“.
  Der Satz ist der, der gerade läuft; vor und zurück gehen von Station zu
  Station, auch wenn zwei dieselbe Zeit haben (vorher blieb „zurück“ daran
  hängen – im Szenario gesehen).
- Im Fenster steht „Abfahren“ gleich unter dem Ergebnis, vor den grauen
  Zeilen – ohne Scrollen sichtbar. Ein neuer Nullpunkt rechnet neu und
  fährt die Maschine an dieselbe Zeit; ein Abspielen läuft weiter. Ein Klick
  auf eine Überschreitung stellt den Abspieler auf ihre Station.
- `abfahren.py`: Auf Kreisen auch die Umkehrstellen der Achsen (dort misst
  die Reichweite) – jede Überschreitung ist eine Station (`station_von`).
  Ein Vorschubsatz dauert mindestens so lange wie der Eilgang der Achsen:
  Schwenkt der Revolver in einem Satz ohne Weg, kostet das seine Zeit.
- `Verfahren.setze_alle`: alle Achsen auf einmal, die Bauteile bewegen sich
  einmal; zurück kommen die Achsen, die an einer Grenze halten.
- Hilfe „Auf der Maschine prüfen“: Abschnitt „Abfahren“ (Bedienung, Farben,
  wie die Zeit gerechnet wird); die Werkzeuglänge nennt jetzt die Länge ab
  Spindelnase.

### TEST
- `szenario_abfahren` in 1.1.3 und im Wochen-Build grün, Screenshots
  angesehen: Rohteil und Teil auf dem Tisch, Bahn darauf, Werkzeug in der
  Spindel; mitten auf der zweiten Geraden sitzt die Spitze auf dem Punkt der
  Bahn (auf 1e-6 mm), das Werkzeug im Bild an der Spindel; Abspielen ×100
  läuft bis zum Ende und hält an; Punkt zurück; zweite Operation „Satz 3
  von 7“; X 300 → Klick → X1 −250 rot „am Anschlag“; Schließen beim
  Abspielen → Körper weg, Maschine zurück.
- `szenario_reichweite` in beiden Versionen grün.
- `test_abfahren` (neu: Vollkreis mit vier Umkehrstellen, Station der
  Überschreitung, `stellungen_an`, `setze_alle`, Revolver im Vorschubsatz –
  ohne die Änderung 0 s, geprüft), `test_reichweite`, `test_verfahren`,
  `test_hilfe`, `test_sprache` grün; black, ruff sauber.

### NEXT
- Schritt 3: Version 0.23.0, voller Lauf in beiden Versionen, Push.
- Ob Anzeige und Bedienung verständlich sind, sieht nur Manuel (Snapshot,
  „Manuel probiert aus“ Punkt 7).

## P-2026-09-26-89 abfahren-rechenkern

### EINGELESEN
- Spezifikation 4b (P-2026-09-26-88), Schritt 1: Stationen mit Zeit,
  Stellungen zu jeder Zeit; Zeiten gegen Handrechnung prüfen.
- `reichweite.py`: `_bahn` liefert Punkte und Kreisbögen, `_pruefe_operation`
  rechnet je Operation Werkzeugaufnahme, Länge und die Lösung je Stellung der
  Rundachsen.

### DATEIEN
- `camaddon/abfahren.py` (neu)
- `camaddon/reichweite.py` (`_Schritt`; `achsen_fuer`, `gefahrene_achsen`,
  `loeser` öffentlich; Rückzug nach dem Bohrzyklus auf Wunsch)
- `translations/de.json`, `translations/en.json` (1 Text)
- `tests/test_abfahren.py` (neu)
- `docs/spezifikation_simulation.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Aus der Bahn eines Jobs entstehen Stationen, deren Zeiten der Handrechnung
entsprechen (100 mm mit F 10 = 10 s, Eilgang je Achse aus der Maschine);
zwischen zwei Stationen liefert `stellungen_bei` die geradlinig
dazwischenliegenden Stellungen.

### DONE
- `_bahn` liefert jetzt je Punkt und Kreis einen `_Schritt`: Art, Ort,
  Rundachsen, Eilgang oder Vorschub, das zuletzt gesetzte F, die Satznummer.
  Im Bohrzyklus gehen „über dem Loch“ und „auf R“ im Eilgang, der Grund im
  Vorschub; mit `rueckzug=True` kommt der Rückzug dazu (die Reichweite
  nutzt ihn nicht – ihre Punkte bleiben dieselben).
- Die Rechnung je Operation ist öffentlich: `achsen_fuer`,
  `gefahrene_achsen` (Linearachsen, Revolver, positionierende Rundachsen –
  keine Spindeln), `loeser` (Lösung je Stellung der Rundachsen, mit
  Zwischenspeicher); die Reichweite nutzt dieselben.
- `abfahren.abfahrt(pruefung, job, nullpunkt, bibliothek)`: Stationen mit
  Zeit, Operation, Satz, Punkt, Rundachsen, Stellungen (None, wo der Punkt
  nicht erreichbar ist) und Eilgang; Kreise in Schritten ≤ 5°. Zeit:
  Vorschub = Weg / F (FreeCAD: mm/s), dreht sich nur eine Rundachse, zählt
  ihr Winkel; ohne F 1000 mm/min mit Hinweis. Eilgang: jede Achse mit ihrem
  Eilgang (Linear), ihrer Geschwindigkeit (Positionieren) bzw. 180° je
  Schaltzeit (Revolver), die langsamste bestimmt; fehlt ein Wert, gilt der
  der Übergabe an CAM.
- `Abfahrt`: `dauer`, `index_bei(zeit)`, `wirksam(i)` (wie die Maschine dort
  steht – nicht erreichbar: bleibt stehen), `stellungen_bei(zeit)`
  (geradlinig zwischen zwei Stationen).

### TEST
- `test_abfahren`, 1.1.3 und Wochen-Build grün: Beispiel-Fräse – Achsen
  X1/Y1/Z1 ohne die Spindel; 62 Stationen; Geraden 1,5 s und 10 s; Kreis
  54 Sehnen zu 5°; Eilgang Z 0,06 s; Bohrzyklus 0,21 / 0,028 / 2,2 /
  0,072 s, Rückzug auf die Ausgangshöhe; Dauer; Mitte der Geraden X1 −50;
  vier Stationen gegen `Pruefung.stellungen`; ohne F 0,6 s mit Hinweis.
  5-Achs-Fräse A 90° mit F 10 in 9 s, halb geschwenkt A1 45. Drehmaschine:
  Revolver von P1 auf P2 zwischen zwei Operationen. Drehmaschine ohne Y:
  der Punkt quer daneben lässt die Maschine stehen.
- `test_reichweite`, `test_sprache` in beiden Versionen grün.

### NEXT
- Schritt 2: Anzeige und Abspieler im Fenster „Auf der Maschine prüfen“.

## P-2026-09-26-88 spezifikation-abfahren

### EINGELESEN
- Manuel (2026-09-26): „Ich kann aktuell nicht testen, bau das mit der
  Maschine“ – gemeint ist Stufe 4b (die Maschine fährt die Bahn sichtbar
  ab), die ich erst nach seinem Test von 4a bauen wollte.
- Entwurf 4b: Werkzeug als einfacher Körper, Rohteil an der
  Werkstückaufnahme, Abspielen/Anhalten/Schritt/Geschwindigkeit/Sprung zu
  einer Operation, Achswerte dazu.
- Ausprobiert in 1.1.3 und im Wochen-Build: F steht in den Bahnen in mm/s
  (Werkzeug-Controller 600 mm/min → F 10, 120 mm/min → F 2); der
  Standard-Controller eines neuen Jobs hat Vorschub 0; in der Operation
  „Eigene“ steht F, wie getippt. Eilgang steht nicht in der Bahn.

### DATEIEN
- `docs/spezifikation_simulation.md` (Kopf, 4b, Abschnitt 6, neu
  Abschnitt 11)
- `docs/STATUS_SNAPSHOT.md`, `CHATSTART.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation sagt genau, was 4b zeigt, wie es rechnet und wie man es
bedient – so, dass danach gebaut werden kann –, und kennzeichnet die
Entscheidungen als Claudes, zur Besprechung.

### DONE
- 4b-Entscheidungen (Claude): nur Coin-Knoten in der 3D-Ansicht der
  Maschine, nichts im Dokument; Werkzeug als Zylinder – Schneide, Schaft,
  Halter angedeutet (Ø 2 × Schaft, mindestens 25 mm), bis Frage 4
  entschieden ist; Rohteil durchscheinend, Modell fest, Bahn als Linie
  (Vorschub blau, Eilgang rot), alles an der Werkstückaufnahme; Zeit aus F
  (mm/s) bzw. 1000 mm/min mit Hinweis, Eilgang je Achse aus der Maschine
  (fehlt: 10 000 mm/min), die langsamste bestimmt; Kreise in Schritten
  ≤ 5°, Rückzug nach dem Bohrzyklus; Bedienung (Operation, Anfang, Punkt
  zurück/vor, Abspielen/Anhalten, Tempo ×1/×5/×20/×100, Schieber) und
  Anzeige (Operation, Satz, Zeit, Achswerte); am Anschlag bleibt die Achse
  stehen, rot; ein Klick auf eine Überschreitung stellt auch den
  Abspieler.
- Drei Schritte: Rechenkern `abfahren.py`, Anzeige und Abspieler, Version.
- Abschnitt 11: Akzeptanzkriterien 4b (Abspielen, Anschlag, Zeiten gegen
  Handrechnung, Schließen ohne Spur).

### TEST
- Reine Doku.

### NEXT
- Schritt 1: Rechenkern `abfahren.py` mit Prüfungen.

## P-2026-09-26-87 version-0-22-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit 0.21.0:
  „Auf der Maschine prüfen“ (W-001 Stufe 4a, P-2026-09-26-83 bis -86).

### DATEIEN
- `package.xml` (0.22.0, Beschreibung)
- `README.md` („Was es kann“)
- `translations/de.json`, `translations/en.json` (Text „Über“)
- `docs/STATUS_SNAPSHOT.md` (Projektstatus, Punkt 13, „Danach“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.22.0 und nennt
das Prüfen der Verfahrwege; die README hat den Punkt „Auf der Maschine
prüfen“.

### DONE
- Version 0.21.0 → 0.22.0; Beschreibung für den Addon-Manager um „check a
  CAM job's paths against its travel limits“ ergänzt.
- README: Punkt „Auf der Maschine prüfen“ nach „Maschine verfahren“.
- „Über“: „… an CAM übergeben und prüfen, ob ihre Verfahrwege für die
  Bahnen eines CAM-Jobs reichen“ (de/en).
- Stand: W-001 bis 4a fertig und geprüft, danach 4b; Punkt 13 komplett.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push nach `main` und in den Branch, bei GitHub nachsehen, Manuel den
  Klickweg und die Screenshots zeigen.

## P-2026-09-26-86 laenge-ab-spindelnase

### EINGELESEN
- Manuel (2026-09-26), Frage 3 zu Stufe 4: „Eigenes Feld, vorbelegt“ – je
  Werkzeug die Länge ab Spindelnase, mit Halter, wie am Voreinstellgerät;
  leer gilt die Gesamtlänge.
- Spezifikation Stufe 4a, Schritt 3. Die Werkzeugverwaltung ordnet die Maße
  je Art an (`_felder_anordnen`); Felder für alle Arten (Bezeichnung) stehen
  darunter.

### DATEIEN
- `camaddon/werkzeuge.py` (Feld `laenge_spindelnase`, speichern und laden)
- `camaddon/gui_werkzeuge.py` (Feld unter den Maßen, grau die Gesamtlänge)
- `camaddon/reichweite.py` (nimmt die Länge ab Spindelnase)
- `translations/de.json`, `translations/en.json` (3 neue Texte, 3 Hinweise
  ergänzt)
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `tests/test_werkzeuge.py`, `tests/test_reichweite.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/spezifikation_simulation.md`, `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In der Werkzeugverwaltung hat jedes Werkzeug das Feld „Länge ab
Spindelnase“; leer steht grau „leer: Gesamtlänge 50“. Eingetragen, rechnet
„Auf der Maschine prüfen“ damit – ohne Hinweis zur Länge.

### DONE
- Werkzeug: `laenge_spindelnase` (mm, 0 = nicht gemessen), gespeichert;
  ältere Dateien ohne das Feld laden mit 0, negative Werte werden 0.
- Werkzeugverwaltung: das Feld bei allen Arten unter den Maßen, über
  „Bezeichnung“, mit Längeneinheit (mm/inch wie die anderen Längen); leer
  grau „leer: Gesamtlänge …“ – eingetragen oder geschätzt; Tooltip: von der
  Spindelnase (im Revolver von der Werkzeugaufnahme) bis zur Spitze, mit
  Halter, wofür es gebraucht wird.
- Prüfung: Ist die Länge ab Spindelnase eingetragen, gilt sie (Quelle
  `LAENGE_SPINDELNASE`, kein Hinweis). Sonst sagen die Hinweise zur
  Gesamtlänge bzw. geschätzten Länge „Genauer mit der „Länge ab
  Spindelnase“ in der Werkzeugverwaltung.“, der zum CAM-Werkzeug, dass es
  nicht in der Werkzeugverwaltung steht.
- Hilfe „Werkzeugverwaltung“: eigener Punkt „Länge ab Spindelnase“.

### TEST
- `test_werkzeuge`: speichern/laden, alte Datei ohne Feld, negativer Wert.
  `test_reichweite`: mit 110 mm Länge ab Spindelnase steht Z1 60 mm höher
  als mit den 50 mm des CAM-Werkzeugs, kein Hinweis zur Länge; die Hinweise
  mit ihrem zweiten Satz. Beide Versionen grün, dazu `test_sprache`,
  `test_hilfe`.
- `szenario_werkzeugverwaltung` (Feld sichtbar, grau „leer: Gesamtlänge
  50“, 115 eintragen und leeren), `szenario_reichweite`, `szenario_hilfe` –
  beide Versionen grün. Screenshot angesehen: das Feld unter den Maßen, über
  „Bezeichnung“.

### NEXT
- Schritt 4: Version 0.22.0, README, voller Lauf, Push.

## P-2026-09-26-85 reichweite-fenster

### EINGELESEN
- Spezifikation Stufe 4a, Schritt 2 und Abschnitt 6: Befehl und
  Aufgabenfenster „Auf der Maschine prüfen“.
- Ausprobiert (Szenario-Proben in beiden Versionen): Die 3D-Ansicht eines
  anderen Dokuments holt `Gui.getMainWindow().setActiveWindow(ansicht)` nach
  vorn. **Im Wochen-Build verschwindet dabei ein offenes Aufgabenfenster** –
  es gehört zu dem Dokument, in dem es aufging; in 1.1.3 bleibt es. Öffnet
  man es erst nach dem Wechsel, bleibt es in beiden. Gleich nach dem Anlegen
  eines Jobs holt 1.1.3 das Dokument des im Baum gewählten Jobs etwa 100 ms
  später zurück nach vorn – bei echter Bedienung (erst wählen, dann klicken)
  nicht, in den Proben auch nicht mit 400 ms Pause oder beim zweiten Mal.

### DATEIEN
- `camaddon/gui_reichweite.py` (neu)
- `camaddon/reichweite.py` (LCS der Aufnahmen beim Anlegen gemerkt)
- `camaddon/gui_start.py` (Befehl, Werkzeugleiste), `camaddon/hilfe.py`
- `resources/icons/reichweite.svg` (neu)
- `help/de/reichweite.html`, `help/en/reichweite.html` (neu)
- `translations/de.json`, `translations/en.json` (20 Texte)
- `tests/gui/szenario_reichweite.py` (neu)
- `docs/spezifikation_simulation.md` (Abschnitte 5 und 6),
  `docs/STATUS_SNAPSHOT.md` (Punkt 13, „Manuel probiert aus“ 7),
  `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job wählen → „Auf der Maschine prüfen“ → das Fenster öffnet sich bei der
Maschine: „Alle Achsen bleiben in ihren Grenzen.“ oder die Überschreitungen
als Sätze; ein Klick fährt die Maschine dorthin, die Achse am Anschlag;
Schließen fährt zurück und merkt sich den Nullpunkt am Job.

### DONE
- Befehl „Auf der Maschine prüfen“ in der Werkzeugleiste (nach „Schnittwerte
  in den Job“), Symbol: eine Bahn zwischen zwei Grenzen, ein Haken. Ohne Job
  im aktiven Dokument oder ohne offene Maschine sagt ein Satz, was fehlt. Der
  gewählte Job gilt (auch über eine Operation). Sind mehrere Maschinen offen,
  fragt der Befehl, welche – die im Dokument des Jobs zuerst. Dann holt er
  das Dokument der Maschine nach vorn und öffnet dort das Fenster; im
  Fenster gibt es deshalb keine Auswahl der Maschine (Spezifikation
  angepasst).
- Das Fenster: Job (Auswahl), Maschine, Werkstückaufnahme (nur bei
  mehreren); Nullpunkt X/Y/Z – leer mit dem Vorschlag grau im Feld,
  eingetragen am Job gemerkt (beim Schließen und beim Wechsel des Jobs, ein
  Schritt Rückgängig im Dokument des Jobs). Ergebnis: grün „Alle Achsen
  bleiben in ihren Grenzen.“, rot „Nicht alle Achsen bleiben in ihren
  Grenzen:“ mit der Liste der Sätze, oder grau „Keine Bahn zum Prüfen …“;
  darunter grau je Achse der gebrauchte Bereich und die Hinweise. Gerechnet
  wird beim Öffnen und 300 ms nach jeder Eingabe.
- Klick auf einen Satz: Die Maschine fährt auf die Stellungen dort (über
  die Grenzen nicht hinaus – die Achse steht am Anschlag), alles in einem
  Schritt, den Schließen verwirft. Schließen fährt zurück und kehrt zum
  Dokument des Jobs zurück.
- Die Liste ist nur so hoch wie ihre Sätze (sonst schob sie Bereiche und
  Hinweise aus dem Aufgabenbereich – im ersten Screenshot gesehen).
- `reichweite.Pruefung` merkt sich die LCS der Aufnahmen beim Anlegen: So
  rechnet es richtig weiter, auch wenn das Fenster die Maschine bewegt hat.
- Hilfeseite „Auf der Maschine prüfen“ (de/en): So geht es, was oben steht,
  das Ergebnis, wie gerechnet wird.

### TEST
- `szenario_reichweite` in 1.1.3 und im Wochen-Build grün: Fenster im
  Dokument der Maschine, grünes Urteil, Vorschlag −50/−30/1 grau in den
  Feldern, Bereiche (7 Punkte), Hinweis zur Länge; X 300 → der Satz „X1
  fährt in „Eigene“ bis −470,00 mm, die Grenze ist −250,00 mm (bei X 170,
  Y 40, Z −5).“; Klick → X1 auf −250, der Tisch bewegt; Schließen → nichts
  bewegt, das Teil vorn, am Job {"X": 300}; wieder öffnen → 300 im Feld,
  leeren → grün, Schließen → Eintrag weg.
- Screenshots angesehen (beide Versionen): Maschine vorn, Fenster rechts,
  Tisch am Anschlag nach dem Klick; die Liste nach der Korrektur kompakt.
- `test_reichweite`, `test_sprache`, `test_hilfe` in beiden Versionen grün.
- Ob das Fenster ohne Erklärung verständlich ist, prüft Manuel.

### NEXT
- Schritt 3: „Länge ab Spindelnase“ in der Werkzeugverwaltung.

## P-2026-09-26-84 reichweite-rechenkern

### EINGELESEN
- Spezifikation Stufe 4a (P-2026-09-26-83), Schritt 1: Rechenkern ohne
  Oberfläche, dazu Beispiel-Drehmaschine und Hilfe „Aufnahmen“.
- `verfahren.py`: Die Lage eines Bauteils ist das Produkt der
  Achsbewegungen vom Bett nach außen – dieselbe Rechnung trägt die Prüfung,
  nur ohne Bauteile zu bewegen. `platzstellungen()` bringt einen
  Revolverplatz in Arbeitsstellung. `job_schnittwerte.werkzeug_von()` findet
  zum Werkzeug-Controller das Werkzeug der Werkzeugverwaltung.

### DATEIEN
- `camaddon/reichweite.py` (neu)
- `camaddon/verfahren.py` (öffentlich: `bewegung`, `pfad`, `weg_bei`,
  `stellung_bei`)
- `camaddon/beispielmaschine.py` (LCS mit X-Richtung; Futter der
  Drehmaschine)
- `translations/de.json`, `translations/en.json` (16 Texte `rw.*`)
- `help/de/aufnahmen.html`, `help/en/aufnahmen.html`
- `tests/test_reichweite.py` (neu)
- `docs/aufbau.md`, `docs/spezifikation_simulation.md`,
  `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Für jeden Punkt einer Bahn liefert die Prüfung die Stellungen aller Achsen;
fährt die Maschine dorthin, steht die Werkzeugspitze genau auf dem Punkt –
an allen Beispielmaschinen. Eine Achse über ihrer Grenze kommt als Satz mit
Operation, Stellung, Grenze und Punkt im Programm.

### DONE
- `Pruefung(assembly, maschine, werkstueckaufnahme)`:
  - Drehachsen zuerst: Rundachsen mit Betriebsart „Positionieren“ über ihren
    Namen im Programm (C1 → C), ohne Angabe 0; der Revolver mit dem Platz
    der Werkzeugnummer in Arbeitsstellung; Spindeln bleiben.
  - Dann die Linearachsen zwischen Werkzeug- und Werkstückaufnahme als
    lineares Gleichungssystem (numpy): einmal je Stellung der Drehachsen
    gelöst, gilt Stellungen = s0 + S · Punkt. Die schräge Achse braucht
    nichts Eigenes – die Lösung rechnet mit den echten Richtungen der
    Schlitten. Weniger als drei Achsen: Was übrig bleibt, heißt „nicht
    erreichbar“; mehr als drei oder abhängige: „noch nicht prüfbar“.
  - `stellungen(punkt, …)` für einen Punkt (auch fürs spätere „dorthin
    fahren“); `pruefe_job(job, nullpunkt, bibliothek)` für alle aktiven
    Operationen aus `job.Operations` (wie der Postprozessor, ohne die Lage
    der Operation).
- Die Bahn: G0/G1-Enden; Kreise G2/G3 in G17/G18/G19 mit I/J/K oder R, auch
  Vollkreis und Schraube – dazu genau die Stellen, an denen eine Achse
  umkehrt (aus S, nicht in Schritten); Bohrzyklen über dem Loch, auf R und
  auf dem Grund, G98/G99; G90/G91; eine Rundachse im Satz in 1°-Schritten.
  Befehle ohne Bewegung werden still übergangen, unbekannte mit Bewegung
  gemeldet.
- Ergebnis: je Operation und Achse die weiteste Überschreitung („X1 fährt in
  „Eigene“ bis −400.00 mm, die Grenze ist −250.00 mm (bei X 400, Y 0,
  Z 10).“) mit allen Stellungen dort; je Achse der gebrauchte Bereich;
  Hinweise: Länge (Gesamtlänge, geschätzt oder die des CAM-Werkzeugs, je
  „ohne Halter“), Platz fehlt, nicht erreichbar, Z der Werkzeugaufnahme zum
  Werkstück, unbekannter Befehl. Rundachsen zählen, wenn sie
  positionieren und nicht endlos sind.
- Nullpunkt des Jobs: Vorschlag (Rohteil mittig, Unterseite auf der
  Spannfläche), eingetragen als Eigenschaft `CamAddonNullpunkt` am Job
  (JSON, einzelne Werte, ausgeblendet), `nullpunkt(job)` nimmt beides.
- `verfahren.py`: Bewegung einer Achse um einen Weg, Pfad zu einem Glied,
  Weg ↔ Stellung als öffentliche Methoden; `_bewege` nutzt sie.
- Beispiel-Drehmaschine: Das LCS am Futter hat jetzt X von der Spindelachse
  zum Werkzeug (vorher zeigte X nach unten, ein X im Programm wäre über Y1
  gefahren). `Baukasten.lcs(…, x_richtung=…)`.
- Hilfe „Aufnahmen“: Z der Werkzeugaufnahme von der Spitze zur Aufnahme; das
  LCS der Werkstückaufnahme ist das Koordinatensystem des Jobs, X wie X im
  Job (Drehmaschine: zum Werkzeug hin).

### TEST
- `tests/test_reichweite.py`, 1.1.3 und Wochen-Build grün:
  - Nachgemessen: Maschine auf die gerechneten Stellungen gefahren, Abstand
    Spitze – Punkt < 1e-6 mm an der 3-Achs-Fräse (mit und ohne Nullpunkt),
    der Drehmaschine (P1 radial, P2 axial), der Drehmaschine mit Y schräg um
    30°, den drei 5-Achs-Fräsen ohne und mit Rundachsen aus der Bahn.
  - Drehmaschine: X im Job fährt nur X1; Revolver auf P2; C ohne Angabe
    auf 0. Schräge Y-Achse: Y 0 → 10 fährt Y1 um 11,547 und X1 um 5,774 –
    wie `schraege_achse.schlitten_aus_programm`.
  - Job mit eigener Bahn: Überschreitung von X1 als Satz, Bereiche (Y bis
    zum Scheitel des Kreises, Z bis zum Grund der Bohrung), 11 Punkte,
    Hinweise; Vollkreis und G18-Halbkreis; Länge aus der Werkzeugverwaltung
    (Z1 10 mm höher) und geschätzt; Z der Spindelnase umgedreht → Hinweis;
    Platz P20 fehlt → Hinweis, keine Punkte; A 130 über 120 in 1°-Schritten
    (261 Punkte); Drehmaschine ohne Y: erreichbarer Punkt mit den
    erwarteten Stellungen, 5 mm quer daneben nicht erreichbar, Hinweis
    „1 von 2 Punkten“; Nullpunkt: Vorschlag, eintragen, Speichern und
    Laden, löschen.
- Alle Prüfungen ohne Oberfläche in beiden Versionen grün (`test_export`
  in 1.1.3 übersprungen wie immer); `test_hilfe` nach der Hilfeänderung.

### NEXT
- Schritt 2: Fenster „Auf der Maschine prüfen“ mit Befehl, Hilfe und
  Szenario.

## P-2026-09-26-83 spezifikation-reichweite

### EINGELESEN
- Manuel (2026-09-26) auf die vier Fragen zu Stufe 4a, jeweils die
  empfohlene Antwort: **Bahn im Job** (nicht das NC-Programm);
  **Nullpunkt = Werkstückaufnahme + Verschiebung** je Job im Fenster;
  **eigenes Feld „Länge ab Spindelnase“**, vorbelegt (leer gilt die
  Gesamtlänge); **4a Reichweite zuerst**. Halter und Mindestabstand (Fragen
  4 und 5) betreffen erst die Kollision und kommen vor 4c.
- Ausprobiert, in 1.1.3 und im Wochen-Build: Job ohne Oberfläche anlegen,
  Operation „Eigene“ (Custom) mit G-Code als Text, `op.Path.Commands`
  lesen (G0/G1/G2 mit X/Y/Z/I/J); der Werkzeug-Controller hat Nummer und
  Länge. Die Postprozessoren lesen `op.Path` ohne die Lage der Operation
  (`Path/Post/UtilsParse.py`). numpy gibt es in beiden Umgebungen.
- Beispielmaschinen: Die Z-Achse der Werkzeugaufnahmen zeigt von der Spitze
  zur Aufnahme (Fräse: Spindelnase, Z nach oben; Drehmaschine: Platz, Z vom
  Werkzeug weg). Die Hilfe sagt nur „in Richtung des Werkzeugs“. Die X-Achse
  des LCS am Futter der Beispiel-Drehmaschine zeigt nach unten, der
  X-Schlitten fährt quer dazu – ein X im Programm käme über Y1 heraus.

### DATEIEN
- `docs/spezifikation_simulation.md`
- `docs/STATUS_SNAPSHOT.md` (Projektstatus, neuer Punkt 13, Besprechen)
- `docs/spezifikation_maschine_aus_baugruppe.md` (Verweis auf Stufe 4)
- `CHATSTART.md` (Lesekarte)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation sagt so genau, was 4a rechnet und zeigt, dass danach
gebaut werden kann: Begriffe mit den Richtungen der LCS, der Rechenweg
(Drehachsen zuerst, dann die Linearachsen als Gleichungssystem), welche
Punkte geprüft werden, das Fenster, vier Schritte, Akzeptanzkriterien.

### DONE
- Kopf: Manuels Entscheidungen vom 2026-09-26; Abschnitt 9 heißt
  „Entscheidungen“ (1, 2, 3, 6 entschieden; 4, 5 offen vor 4c).
- Begriffe: Das LCS der Werkstückaufnahme ist das Koordinatensystem des
  Jobs (Z aus der Spannfläche, X wie X im Job, auf der Drehmaschine zum
  Werkzeug hin); Werkzeugspitze = Ursprung der Werkzeugaufnahme minus Länge
  ab Spindelnase entlang Z; Z der Werkzeugaufnahme zeigt von der Spitze zur
  Aufnahme; „Länge ab Spindelnase“ mit Halter.
- Abschnitt 4 neu: Drehachsen zuerst (A/B/C über den Namen im Programm,
  ohne Angabe 0; Revolver mit dem Platz des Werkzeugs in Arbeitsstellung;
  Spindeln bleiben), dann die Linearachsen als lineares Gleichungssystem –
  das deckt Tisch/Kopf, schiefe Achsen und die schräge Achse ab; weniger
  als drei Linearachsen → „nicht erreichbar“, mehr als drei → „noch nicht
  prüfbar“; geprüfte Punkte: G0/G1-Enden, Umkehrpunkte auf Kreisen,
  Bohrzyklen, 1°-Schritte bei Rundachsen im Satz. Die Frage nach dem
  Buchstaben im Fenster entfällt.
- Abschnitt 5: 4a in vier Schritten – Rechenkern (`reichweite.py`),
  Fenster, Länge ab Spindelnase, Version.
- Abschnitt 6: das Fenster „Auf der Maschine prüfen“ – Job, Maschine aus
  allen offenen Dokumenten, Werkstückaufnahme, Nullpunkt X/Y/Z (leer =
  Vorschlag: Rohteil mittig mit der Unterseite auf der Spannfläche;
  eingetragen = am Job gespeichert), Ergebnis in Sätzen, Klick fährt hin,
  Schließen fährt zurück.
- Abschnitt 10: Akzeptanzkriterien für die Beispielfräse, die
  Drehmaschine mit schräger Y-Achse und ein Werkzeug ohne Länge ab
  Spindelnase. Statt „Zeile 1234“ nennt die Meldung den Punkt im Programm
  – ein NC-Programm gibt es bei der Bahn im Job nicht.

### TEST
- Reine Doku.

### NEXT
- Schritt 1: Rechenkern `reichweite.py` mit Prüfungen; Beispiel-Drehmaschine
  (X des LCS am Futter) und Hilfe „Aufnahmen“.

## P-2026-09-26-82 simulation-schraege-achse

### EINGELESEN
- Stand: „Danach: W-001 Stufe 4a (Reichweite prüfen), sobald die schräge
  Achse (Punkt 11) steht und die Fragen zu Stufe 4 beantwortet sind.“ Die
  schräge Achse steht (Stufe 3b komplett); der Entwurf
  `spezifikation_simulation.md` kannte sie noch nicht.

### DATEIEN
- `docs/spezifikation_simulation.md` (Abschnitt 4)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer den Entwurf zu Stufe 4 liest, sieht, wie eine schräge Achse in die
Reichweitenprüfung eingeht: rechtwinklige Bahn, Grenzen der Schlitten,
Meldung mit Programmpunkt und Schlitten.

### DONE
- Abschnitt 4 um „Schräge Achse“ ergänzt: dieselbe Umrechnung wie „wie im
  Programm“ (`schraege_achse.Programm`), geprüft werden die Grenzen der
  Schlitten; Beispielmeldung „X 140, Y −40 in *Kontur* braucht X1 = 163 mm,
  die Grenze ist 150 mm“ (bei 30°, dieselben Zahlen wie im Szenario
  `szenario_verfahren_schraeg`); für 4d der Höchstvorschub
  (`schraege_achse.hoechstwert`).

### TEST
- Reine Doku.

### NEXT
- Manuel die Fragen zu Stufe 4 stellen, die 4a betreffen (Abschnitt 9,
  Nr. 1, 2, 3, 6); Halter und Mindestabstand erst vor 4c.

## P-2026-09-26-81 readme-maschine

### EINGELESEN
- Manuel: „Da ist ein PR, den man nicht pushen kann – schau es dir an, löse
  die Probleme und integriere das.“ PR #1 (W-003, 4-Achs) war nicht mergebar:
  Beide Sitzungen hatten gleichzeitig an Stand, Verlauf und Sprachdateien
  gearbeitet und dieselben Nummern P-2026-09-26-75/-76 vergeben.
- Beim Nachsehen vor dem Push: Die andere Sitzung hatte den PR auf Manuels
  „pusch das mal alles komplett“ schon selbst auf `main` neu aufgesetzt
  (P-2026-09-26-78 bis -80, 0.21.0, voller Lauf grün) und gepusht; der PR ist
  geschlossen, sein Kopf ist `main`. Mein lokaler Merge kam zu denselben
  Konfliktlösungen – Code, Sprachdateien, Hilfe und Prüfungen gleich – und
  wurde deshalb verworfen, nicht gepusht.
- Übrig blieb: Die Zeile zu W-001 im Projektstatus stand noch auf „Jetzt
  Stufe 3b“; die README kannte „Neue Maschine …“, die schräge Achse und das
  Verfahren „wie im Programm“ nicht; die Beschreibung für den Addon-Manager
  (`package.xml`) nannte keine der neuen Funktionen.

### DATEIEN
- `README.md`
- `docs/STATUS_SNAPSHOT.md` (Projektstatus W-001)
- `package.xml` (Beschreibung)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die README auf GitHub liest, findet „Neue Maschine …“, die schräge
Achse und das Verfahren „wie im Programm“ unter „Was es kann“; der
Projektstatus sagt, dass Stufe 3b fertig ist.

### DONE
- README: neuer Punkt „Neue Maschine …“ (Bauarten, Maße der Drehmaschine);
  bei „Maschine bearbeiten“ die schräge Achse in zwei Sätzen; bei „Maschine
  verfahren“ „wie im Programm“ mit Reglern X und Y.
- Projektstatus W-001: Stufen 1 bis 3 und 3b fertig, danach Stufe 4.
- `package.xml`: „inclined axes“, fertige Maschinen („a lathe with your own
  dimensions, mills“) und „4-axis machining: places a part in round bar
  stock as a CAM job“. Die Version bleibt 0.21.0.

### TEST
- `scripts/alle_tests.sh` in beiden Versionen vor dem Push (wegen
  `package.xml`).

### NEXT
- Push nach `main` und in den Branch, bei GitHub nachsehen.

## P-2026-09-26-80 version-0-21-0

### EINGELESEN
- Manuel (2026-09-26) auf die Frage, ob die 4-Achs-Bearbeitung nach `main`
  soll: „Ja, pusch das mal alles komplett“ – „und dann Stop“.
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit 0.20.0:
  „4-Achs-Bearbeitung“, Teil in die Stange (P-2026-09-26-79), und ihre
  Spezifikation (-78).
- Die beiden hießen auf dem Arbeitszweig `claude/4-achsen-rohrteil-plan-bqz52m`
  zuerst -75 und -76. Diese Nummern hatte inzwischen die andere Sitzung auf
  `main` vergeben (neue-maschine, schraege-achse-lesbarer), dazu 0.20.0 (-77).
  Deshalb auf `main` neu aufgesetzt und umnummeriert.

### DATEIEN
- `package.xml` (0.21.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.21.0.

### DONE
- Version 0.20.0 → 0.21.0.

### TEST
- `scripts/alle_tests.sh` auf dem Stand dieses Commits („Neue Maschine …“
  und 4-Achs-Bearbeitung zusammen): black und ruff sauber; FreeCAD 1.1.3
  grün (48 ok, `test_export.py` übersprungen wie immer); Wochen-Build
  26.3.0 dev (2026-09-16) grün (49 ok).

### NEXT
- Push nach `main`. Danach Schluss, auf Manuels Wort („und dann Stop“);
  W-003 V2 erst auf seine Ansage.

## P-2026-09-26-79 vierachs-teil-in-die-stange

### EINGELESEN
- Manuel (2026-09-26), nach dem Plan: „Gleich V1 bauen“; dazu „so dass
  alles einstellbar ist, aber mit Vorschlägen als Standard“.
- `docs/spezifikation_vierachs.md` (Abschnitte 4, 5, 11, 13),
  `gui_verfahren.py` und `gui_maschine.py` (Aufgabenfenster, Transaktion,
  `_EnterBleibtImDialog`), `gui_start.py`, `gui_zeigen.py` (Wackeln),
  `gui_zahlen.py`, `einheiten.py`, `gui_werkzeuge.py` (graue Vorschläge),
  `tests/gui/_lauf/szenario_lauf.py`.
- FreeCAD 1.1.3 und `main`: `Path/Main/Gui/Job.py` (`Create` hängt die
  Anzeige an und öffnet eine eigene Transaktion; `ViewProvider.attach`
  zeichnet nur das Achsenkreuz), `Path/Main/Job.py` (`createResourceClone`:
  Draft-Klon, unsichtbar, Durchsicht 80), `Path/Main/Stock.py`
  (`SetupStockObject`: Drahtgitter, Durchsicht 90), `Gui/TaskView/TaskView.cpp`
  und `TaskDialogPython.cpp` (`modifyStandardButtons`), `Path/Op/Gui/Base.py`
  (hebt die Knopfleiste auf, nicht den Knopf).

### DATEIEN
- `camaddon/vierachs_rohteil.py` (neu), `camaddon/gui_vierachs.py` (neu),
  `camaddon/gui_start.py`, `camaddon/hilfe.py`
- `resources/icons/vierachs.svg` (neu), `help/de/vierachs.html` und
  `help/en/vierachs.html` (neu)
- `translations/de.json`, `translations/en.json` (42 neue Texte, „Über“)
- `tests/test_vierachs_rohteil.py` (neu),
  `tests/gui/szenario_vierachs_rohteil.py` (neu)
- `docs/spezifikation_vierachs.md` (V1 gebaut), `docs/aufbau.md` (zwei
  Module, sechs Stolpersteine), `README.md`, `CHATSTART.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Welle mit außermittigem Zapfen öffnen, ihre Stirnfläche anklicken →
Werkzeugleiste „CAM-Addon“ → „4-Achs-Bearbeitung“ → Stange Ø 80, Rundachse C
→ das Teil liegt mittig in einer durchsichtigen Stange Ø 80 längs Z, die
Fläche 1 mm hinter der Stangenstirn, das Fenster sagt „Passt – rundum
mindestens 4,0 mm Aufmaß“; Abbrechen hinterlässt nichts, „Anlegen“ nimmt ein
Strg+Z zurück – und Manuel versteht das Fenster ohne Erklärung.

### DONE
- Befehl „4-Achs-Bearbeitung“ in der Werkzeugleiste „CAM-Addon“; Symbol:
  Stange mit Teil, Drehpfeil um die Stangenachse, Fräser von oben.
- Rechnung ohne Oberfläche (`vierachs_rohteil.py`):
  - Einmal je Fläche wird vermessen: eben oder nicht, Außennormale, runde
    Außenkante (auch aus Bögen), Punkte aus der Tessellierung, konvexe Hülle
    und kleinster Kreis (Welzl als Schleife).
  - Daraus kommt sofort die Lage für A, B oder C – mit der Mitte „runde
    Fläche“, „ganzes Teil“ oder „auto“ und mit der Drehlage.
  - Vorschlag für den Stangen-Ø: 5-mm- bzw. 1/8"-Schritte, mindestens 1 mm
    am Radius. Dazu Länge und Lage der Stange.
  - `richte_ein` legt Job, Lage des Klons und Zylinder-Rohteil an, ohne
    eigene Transaktion.
- Assistent (`gui_vierachs.py`):
  - Die Fläche wählt man vor dem Befehl oder im offenen Fenster. Beobachter
    und Filter der Auswahl lassen nur Flächen zu, nicht die Stange.
  - Felder mit grauen, gültigen Vorschlägen. Was man einträgt, wird nach
    „Anlegen“ gemerkt – außer dem Stangen-Ø.
  - Mitte mit dem nötigen Ø daneben, Drehlage mit „+90°“, Rundachse A/B/C
    mit einem Satz je Eintrag, eine grüne oder rote Zeile.
  - OK heißt „Anlegen“ und geht erst, wenn eine Fläche gewählt ist.
  - Animation: Das Teil fährt in die Stange und dreht sich einmal – auch
    beim Wechsel der Rundachse.
  - Solange das Fenster offen ist, ist die Stange durchscheinend und nicht
    anklickbar, danach sieht sie aus wie in CAM. Das Original ist
    ausgeblendet.
  - Klickt man ein anderes Teil an, wird der bisherige Job verworfen.
- Gefunden:
  - Die Python-Hülle des OK-Knopfs aus `modifyStandardButtons` verfällt
    mit der Hülle der Knopfleiste. Im Versuchs-Szenario war sie gleich nach
    dem Öffnen „weg“, ohne dass Qt etwas löschte. Jetzt wird die Leiste
    aufgehoben, wie in CAM.
  - 1.1.3 gibt die Beschriftung eines abgebrochenen Jobs nicht wieder frei:
    Der nächste heißt „… 4 Achsen001“.
  - Die Hüllbox gekrümmter Flächen ist nur auf etwa 0,003 mm genau.
- Bewusst offen:
  - Achse von der Maschine (V2).
  - Flächen, Werkzeuge und Bahnen (V3 ff.).
  - „Vorschläge zurücksetzen“ in den Einstellungen – mit V9.
  - Ein Beispielteil zum Ausprobieren – bei Bedarf eigener Patch.

### TEST
- `tests/test_vierachs_rohteil.py` (Claude, ohne Oberfläche, 1.1.3 und
  Wochen-Build):
  - kleinster Kreis: Quadrat, 2000 Zufallspunkte, Punkte auf einer Geraden;
    dazu Sechskant und Quader;
  - Welle mit Nocken: Ø 72 mittig auf der Welle, Ø 66 für das ganze Teil,
    „auto“ bei Ø 80, Ø 70 und ohne Ø;
  - Lage für A, B und C mit beiden Mitten: Normale nach vorne, Stirnfläche
    bei a = 0, Teil bis −100, kein Punkt außerhalb des nötigen Ø;
  - Drehlage, Vorschläge, Länge und Lage der Stange;
  - Job: Zylinder Ø 80 × 134 von −133 bis 1, Klon an seiner Stelle,
    Original unverändert; ein zweiter Aufruf passt das Rohteil an, zwei
    Rückgängig entfernen alles.
- `tests/gui/szenario_vierachs_rohteil.py` (Claude, unsichtbare Oberfläche,
  beide Versionen):
  - Vorschlag Ø 75; Ø 80 → 4,0 mm; ganzes Teil → 7,0 mm; A → Stange in X,
    C → in Z; +90°;
  - eine gewölbte Fläche wird mit einem Satz abgelehnt;
  - Abbrechen hinterlässt nichts, und der zweite Durchlauf hat die
    Rundachse nicht gemerkt;
  - „Anlegen“ ist ein Schritt Rückgängig, Strg+Z räumt alles weg.
  - Screenshots angesehen: Fenster, Stange längs Z und längs X, nach
    „Anlegen“.
- `scripts/alle_tests.sh` auf dem Arbeitszweig, vor dem Zusammenführen mit
  -75 bis -77: black und ruff sauber; FreeCAD 1.1.3 grün (47 ok,
  `test_export.py` übersprungen wie immer); Wochen-Build 26.3.0 dev
  (2026-09-16) grün (48 ok). Der Lauf auf `main` steht in P-2026-09-26-80.
- Das Fenster hat nur Claude als Screenshot gesehen. Ob es sich ohne
  Erklärung versteht, prüft Manuel.

### NEXT
- W-003 V2: Achse von der Maschine (W-001).

## P-2026-09-26-78 spezifikation-vierachs

### EINGELESEN
- Manuel (2026-09-26): „Ich hätte gerne einen Plan gemacht für eine
  4-Achs-Bearbeitung … egal ob es eine C- oder B-Achse ist … auch auf einer
  CLX 550 mit Y-Achse funktionieren. Ich habe ein Bauteil, das ich an ein
  rundes Rohteil im CAM befestigen kann … Stange rund Durchmesser 80 … wähle
  eine Fläche, diese Fläche soll vorne an das Rohteil … zentrisch, dass
  versucht wird, das komplette Bauteil in das Rohteil zu bekommen. Dann
  klickt man die Flächen an, alle Mantelflächen oder einen Zylinder, der
  nicht mittig ist, und dann wird aus Kombination Fräser und Rohteil eine
  Schrupp- und danach eine Schlicht-Strategie erstellt. Maximal
  bedienerfreundlich.“
- Seine Wahl aus vier Fragen mit Optionen: eigener Rechenkern (statt FreeCADs
  „Rotary Surface“ oder beides); zuerst rundum simultan (statt indexiert);
  Achse „am besten von Maschine, ansonsten dreht sich das Rohteil … und dem
  muss man eine Achse zuweisen“; Assistent in vier Schritten. Zum Plan: „Ist
  das egal welche Maschine … Es gibt Achsen, und die Punkte müssen halt via
  Koordinate im G-Code 0,001 mm nach und nach angefahren werden … oder halt
  mit einem Glättungsfilter“ und „Abstechbreite kann man ja einstellen … so
  dass alles einstellbar ist, aber mit Vorschlägen als Standard“. Dann:
  „Gleich V1 bauen“.
- Addon: `job_schnittwerte.py`, `uebergabe_werkzeuge.py`, `werkzeuge.py`,
  `schnittdaten.py`, `schruppwerte.py`, `maschine.py` (`rollen`,
  `programmname`), `kette.py`, `verfahren.py` (`plusrichtung`),
  `schraege_achse.py`, `beispielmaschine.py`, `export.py`, `gui_maschine.py`,
  `gui_verfahren.py`, `gui_zeigen.py`, `gui_start.py`, die drei
  Spezifikationen, `aufbau.md`.
- FreeCAD-Quelltext 1.1.3 und `main` (raw.githubusercontent.com):
  `Path/Op/Surface.py` (Rotational: OCL, nur A/B, Schalter „advanced OCL“),
  `Path/Dressup/Gui/AxisMap.py`, `Path/Op/RotarySurface.py` und
  `Path/Base/Generator/rotary_*.py` (nur `main`, experimentell, OCL, nur
  Achse X/Y), `Path/Main/Workplane.py` (nur `main`), `Path/Op/Base.py`
  (`DoNotSetDefaultValues`, `setDefaultValues` fragt nach Job und
  Controller), `Path/Main/Job.py` (`Create`, `setCenterOfRotation`),
  `Path/Main/Gui/Job.py` (`Create` mit eigener Transaktion),
  `Path/Main/Stock.py` (`CreateCylinder`), `App/PathSegmentWalker.cpp`
  (Anzeige von A/B/C), `Constants.py` (G93 im generischen Postprozessor),
  conda-forge-Rezept von FreeCAD (numpy ja, OpenCamLib nein).
- Gegenprüfung des Entwurfs durch einen Planungs-Agenten.

### DATEIEN
- `docs/spezifikation_vierachs.md` (neu)
- `docs/STATUS_SNAPSHOT.md` (Projektstatus, Punkt 12, W-003)
- `CHATSTART.md` (Lesekarte)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel findet in `docs/spezifikation_vierachs.md` seine Entscheidungen, den
Klickweg durch die vier Schritte mit Skizzen und die Stufen mit je einem
Klickweg wieder.

### DONE
- Spezifikation W-003: Zielbild mit Klickweg, was FreeCAD und das Addon
  schon haben, Begriffe mit Skizze der Rundachs-Koordinaten, Achsen von der
  Maschine oder zugewiesen (Tabelle A/B/C), die vier Schritte mit
  ASCII-Skizzen, Rechenkern (Torus-Modell für alle drei Fräser, exaktes
  Aufmaß, Hüllfläche mit numpy, Lagen, Spirale, Rückzug, Ausgabe als reine
  Achskoordinaten mit Glättung, Vorschub G93), die CAM-Operation mit ihren
  Stolpersteinen, Bedienung, Grenzen, neun Stufen V1–V9, Prüfbarkeit,
  Claudes Vorschläge, Manuels Entscheidungen.
- Gefunden beim Lesen: `Job.setCenterOfRotation` setzt den Mittelpunkt an
  einer Kopie – die Rundachse liegt deshalb durch den Nullpunkt des Jobs.
  Eine Operation, die ohne `DoNotSetDefaultValues` angelegt wird, fragt bei
  mehreren Jobs oder Controllern nach (in FreeCADCmd ein Fehler).
- Versuch (Claude, ohne Oberfläche, 1.1.3 und Wochen-Build): Job anlegen,
  Lage des Modell-Klons setzen, Rohteil durch `CreateCylinder` ersetzen – der
  Klon liegt wie das Original und folgt `T · P0` genau, die Flächennummern
  bleiben, ein Rückgängig entfernt alles. numpy da, OpenCamLib in keiner der
  beiden Testumgebungen.
- Bewusst offen: indexiert 3+1, axiales Werkzeug, Drehen – spätere Stufen
  oder eigene Wünsche; Claudes Vorschläge (Abschnitt 15) zur Besprechung.

### TEST
Reine Doku, kein Testlauf.

### NEXT
- W-003 V1: „Teil in die Stange“ (Befehl, Schritt 1, Prüfung, Szenario).

## P-2026-09-26-77 version-0-20-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit 0.19.0:
  „Neue Maschine …“ mit Maßen der Drehmaschine (P-2026-09-26-75), dazu
  -76 (lesbarer, nichts Sichtbares).

### DATEIEN
- `package.xml` (0.20.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.20.0.

### DONE
- Version 0.19.0 → 0.20.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-26-76 schraege-achse-lesbarer

### EINGELESEN
- Beim Durchsehen von `schraege_achse.py` (P-2026-09-26-66): In
  `schlitten_aus_programm` und `programm_aus_schlitten` hieß eine lokale
  Variable `winkel` – so heißt auch die Funktion des Moduls, die den Winkel
  misst. Richtig gerechnet, aber verwirrend beim Lesen.

### DATEIEN
- `camaddon/schraege_achse.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nichts Sichtbares: `test_schraege_achse.py` bleibt grün.

### DONE
- Lokale Variable `winkel` → `bogen` (der Winkel im Bogenmaß).

### TEST
- Claude ohne Oberfläche: `test_schraege_achse.py` grün (Wochen-Build).

### NEXT
- Version 0.20.0, voller Testlauf, Push.

## P-2026-09-26-75 neue-maschine

### EINGELESEN
- Manuels Wahl (2026-09-26): eigener Befehl „Neue Maschine …“; Maße zum
  Eintragen erst nur für die Drehmaschine. Spezifikation W-001, Abschnitt 7c
  („Vorlage mit Eingabemaske“) und Stufe 3b, Schritt 7.
- `beispielmaschine.py` (Bauplan der Drehmaschine), `gui_maschine.py`
  (Auswahl der Beispielmaschinen), `gui_start.py`, `tests/test_sprache.py`
  (Schlüssel nur als fester Text in tr/meldung).

### DATEIEN
- `camaddon/gui_neue_maschine.py` (neu), `resources/icons/neue_maschine.svg` (neu)
- `camaddon/beispielmaschine.py` (`DrehmaschinenMasse`, `drehmaschine(masse)`,
  `lade(art, masse)`)
- `camaddon/gui_maschine.py` (Auswahl ausgelagert), `camaddon/gui_verfahren.py`,
  `camaddon/gui_start.py`, `camaddon/hilfe.py`
- `help/de/neue_maschine.html`, `help/en/neue_maschine.html` (neu),
  `help/de/achsen.html`, `help/en/achsen.html`
- `translations/de.json`, `translations/en.json`
- `tests/test_beispielmaschine.py`, `tests/gui/szenario_neue_maschine.py` (neu),
  `tests/gui/szenario_beispielmaschine.py`, `tests/gui/szenario_zoll.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/aufbau.md`, `CHATSTART.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugleiste „CAM-Addon“ → „Neue Maschine …“ → Drehmaschine → Name „Meine
Drehmaschine“, Bettneigung 30°, Y schräg um 30°, 8 Revolverplätze →
„Maschine bauen“ → ein neues Dokument „Meine Drehmaschine“, und „Maschine
bearbeiten“ zeigt „Schräge Achse Y1 – gleicht aus: X1, 30,0°“ und
„Revolver T – 8 Plätze“.

### DONE
- `DrehmaschinenMasse`: Name, Bettneigung (0–60°), Y-Winkel (±60°), Wege
  X/Y/Z (0 liegt dazwischen, höchstens 1000 mm je Richtung), Revolverplätze
  (4–24), Höchstdrehzahl; vorbelegt wie das Beispiel; `fehler()` sagt in
  Sätzen, was nicht passt. `drehmaschine(masse)` baut damit – das Bett im
  Rahmen der Neigung, die Wege als Grenzen der Gelenke, die Plätze
  verteilt, S1 mit der Drehzahl, Name für Maschine und Dokument (ohne „/“
  im Dokumentnamen) – und legt bei Y-Winkel ≠ 0 die schräge Achse an
  (`drehe_fuehrung`, der Revolver bleibt gerade).
- Befehl „Neue Maschine …“ (Werkzeugleiste, vor „Maschine bearbeiten“):
  Dialog mit den Bauarten, der Beschreibung und dem Bereich „Maße“ (?): bei
  der Drehmaschine die Felder (Wege in mm bzw. inch), bei den Fräsen der
  Satz „Diese Bauart hat feste Maße …“. „Maschine bauen“ prüft die Maße;
  passt etwas nicht, sagt eine rote Zeile warum, und der Dialog bleibt offen
  (die Zeile verschwindet beim nächsten Ändern). Danach öffnet sich
  „Maschine bearbeiten“.
- „Beispielmaschine laden …“ in „Maschine bearbeiten“ und „Maschine
  verfahren“ öffnet denselben Dialog (Titel „Beispielmaschine laden“), mit
  Maßen bei der Drehmaschine. Knopf jetzt „Maschine bauen“ statt „Laden“.
- Die Beschreibung der Drehmaschine nennt keine feste Platzzahl mehr.
- Hilfe „Neue Maschine“ und ein Absatz in „Achsen“.
- Bewusst noch nicht: Maße für die Fräsen (Manuel: erst die Drehmaschine);
  die Maße werden nicht gemerkt (jedes Mal die des Beispiels).

### TEST
- Claude ohne Oberfläche, beide Versionen: `test_beispielmaschine.py`
  zusätzlich: eigene Maße → Name der Maschine, Dokument „Meine
  Drehmaschine - 2“ (ohne „/“), Wege als Grenzen, X steigt um 30°, 8 Plätze,
  S1 4000, schräge Achse mit 30°, keine Warnung und kein Hinweis zur
  schrägen Achse; Vorgaben ohne schräge Achse; ungültige Maße – je Feld ein
  Satz. `test_sprache`, `test_hilfe` grün.
- Claude mit Oberfläche (Screenshots angesehen), beide Versionen:
  `szenario_neue_maschine` – Knopf in der Werkzeugleiste, Fräse mit festen
  Maßen, Drehmaschine mit Vorbelegung, Weg Y 0 … 0 abgewiesen (roter Satz,
  Dialog bleibt, Satz verschwindet beim Ändern), eigene Maße gebaut,
  „Maschine bearbeiten“ mit schräger Achse 30,0° und 8 Plätzen.
  `szenario_beispielmaschine`, `szenario_zoll` weiter grün.
- Ob der Dialog verständlich ist, prüft Manuel.

### NEXT
- Version 0.20.0, voller Testlauf, Push.

## P-2026-09-26-74 snapshot-schraege-achse-ausprobieren

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md`, Abschnitt „Manuel probiert aus“.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Unter „Manuel probiert aus“ steht als Punkt 5 der Klickweg für die schräge
Achse (anlegen, Winkel eintragen, Verweilen, Verfahren wie im Programm,
Anschlag, Übergabe).

### DONE
- Klickweg ergänzt; „Besprechen“ ist jetzt Punkt 6.

### TEST
- Reine Doku, kein Testlauf.

### NEXT
- Push mit 0.19.0; Schritt 7 (Vorlage) nach Manuels Entscheidung.

## P-2026-09-26-73 version-0-19-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit 0.18.0:
  die schräge Achse (P-2026-09-26-65 bis -72) – Eintrag, Winkel eintragen,
  Erkennung, Verfahren wie im Programm, Übergabe an CAM, Höchstvorschub –
  und das schmalere Verfahrfenster (-70).

### DATEIEN
- `package.xml` (0.19.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.19.0.

### DONE
- Version 0.18.0 → 0.19.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Schritt 7 (Vorlage) nach Manuels Entscheidung zum Aufbau.

## P-2026-09-26-72 schraege-achse-hoechstvorschub

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („Schruppwerte planen“) und Stufe 3b,
  Schritt 6; `schruppwerte.grenzen_der_maschine`.

### DATEIEN
- `camaddon/schruppwerte.py`
- `help/de/schruppwerte.html`, `help/en/schruppwerte.html`
- `tests/test_schraege_achse.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit schräger Achse (30°) offen → Werkzeugverwaltung →
„Schruppwerte planen…“ → „Von der Maschine“ → Vorschub 4330 mm/min statt
5000 (Y1 5000 · cos 30°).

### DONE
- `grenzen_der_maschine()`: Für die schräge Achse zählt der Vorschub, den Y
  im Programm schafft – `schraege_achse.hoechstwert(α, v_Y1, v_X1)`;
  kennt die ausgleichende Achse ihren Vorschub nicht, bremst nur die
  schräge (v_Y1 · cos α). Die übrigen Linearachsen wie bisher; das Kleinste
  gilt.
- Hilfe „Schruppwerte planen“ sagt, woher der Vorschub der Maschine kommt,
  auch bei einer schrägen Achse.

### TEST
- Claude ohne Oberfläche, beide Versionen: `test_schraege_achse.py`
  zusätzlich: ohne Eintrag 5000, 0° 5000, 30° 4330,13, 60° 2500, X1
  unbekannt 2500, Z1 2000 langsamer → 2000. `test_schruppwerte.py`,
  `test_beispielmaschine.py` grün.

### NEXT
- Stufe 3b, Schritt 7 (Vorlage) erst nach Manuels Entscheidung zum Aufbau;
  vorher Push der Schritte 1–6 nach dem vollen Testlauf.

## P-2026-09-26-71 schraege-achse-an-cam

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („An CAM übergeben“) und Stufe 3b,
  Schritt 5; `export.py`; FreeCADs `LinearAxis` (Richtung, Grenzen,
  `max_velocity` – keine Transformation, P-2026-09-26-65).

### DATEIEN
- `camaddon/export.py` (`_schraege_achse`, `_linearachse` mit Richtung und
  Grenzen)
- `camaddon/schraege_achse.py` (`programmrichtung`, `hoechstwert`,
  `gueltige`, `winkel_text` öffentlich)
- `help/de/transformationen.html`, `help/en/transformationen.html`
- `translations/de.json`, `translations/en.json`
- `tests/test_schraege_achse.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit schräger Achse (30°) → „Maschine bearbeiten“ →
„An CAM übergeben“ (Wochen-Build) → der Bericht sagt unter „Bitte prüfen“:
„„Y1“ ist eine schräge Achse (30,0° zu X1). CAM bekommt sie rechtwinklig wie
„Y“ im Programm …“; in CAMs Maschineneditor steht Y1 rechtwinklig zu X1 mit
Weg ±51,96 mm.

### DONE
- Für die schräge Achse bekommt CAM die Richtung der Programmachse:
  rechtwinklig zur ausgleichenden, in der Ebene beider Achsen, auf der Seite
  des Gelenks. Grenzen · cos α, Eilgang
  `hoechstwert(α, Eilgang schräg, Eilgang ausgleichend)` =
  min(v_schräg · cos α, v_ausgleich ÷ |tan α|) – das schaffen beide
  Schlitten zusammen. Name wie bisher (Y1). Fehlt der Eilgang, gilt
  FreeCADs Vorgabe wie bei jeder Achse, mit demselben Satz.
- Ein Satz unter „Bitte prüfen“: schräge Achse, Winkel, rechtwinklig wie Y
  im Programm, Grenzen gelten nur, solange X1 Platz hat – wie weit es geht,
  zeigt „Maschine verfahren“ wie im Programm (die Prüfung auf der Maschine,
  Stufe 4a, gibt es noch nicht; die Spezifikation sagt das jetzt so).
- Ohne Eintrag geht Y1 wie bisher mit seiner schrägen Richtung hinaus.
- `schraege_achse.gueltige()`: die schrägen Achsen, mit denen sich rechnen
  lässt – je Gelenk die erste.

### TEST
- Claude ohne Oberfläche: `test_schraege_achse.py` zusätzlich
  (Wochen-Build): Y1 rechtwinklig zu X1, normiert, zur Seite des Gelenks;
  X1 unverändert; Grenzen ±51,96; Eilgang 12000 · cos 30° = 10392,3;
  Satz im Bericht; ohne Eintrag schräg (X1 · Y1 = 0,5), Grenzen und
  Eilgang wie am Gelenk. `hoechstwert` für 30°, 60°, −30°, 0° (beide
  Versionen). `test_export.py` grün.

### NEXT
- Stufe 3b, Schritt 6: Höchstvorschub beim Planen.

## P-2026-09-26-70 verfahren-schmaler

### EINGELESEN
- Beim Ansehen der Screenshots zu P-2026-09-26-69: „Maschine verfahren“ war
  mit der Beispiel-Drehmaschine breiter als der Aufgabenbereich – in 1.1.3
  abgeschnitten („Werkzeugantr“, „Grenzen: -100,00 … 300,0“), mit der
  schrägen Achse ragte das Fenster rechts hinaus (Knopf (?) nicht zu sehen).
  Gemessen: Mindestbreite 423 Pixel, Aufgabenbereich 374–397 Pixel.

### DATEIEN
- `camaddon/gui_verfahren.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine → „Maschine verfahren“ → das Fenster passt in den
Aufgabenbereich: Namen, Grenzen und der Knopf (?) sind ganz zu sehen, die
Regler sind breit genug zum Ziehen, die Platzauswahl des Revolvers steht
unter seinem Zahlenfeld.

### DONE
- Die grauen Grenzen-Zeilen brechen um und reichen bis zum Rand (vorher eine
  Zeile zwischen Regler und Feld – sie bestimmte die Mindestbreite).
- Die Platzauswahl des Revolvers steht unter dem Zahlenfeld statt in einer
  vierten Spalte: Die kostete jeder Zeile Platz, und die Regler schrumpften
  bis auf den Griff. Mindestbreite jetzt 317 Pixel.

### TEST
- Claude mit Oberfläche (Screenshots angesehen), beide Versionen: gemessene
  Mindestbreite 317 statt 423 Pixel, das Fenster passt, die Regler sind
  etwa 80 (1.1.3) bzw. 190 Pixel (Wochen-Build) breit. `szenario_verfahren`,
  `szenario_verfahren_schraeg`, `szenario_beispielmaschine`,
  `szenario_mausrad` grün.

### NEXT
- Stufe 3b, Schritt 5: An CAM übergeben.

## P-2026-09-26-69 verfahren-wie-im-programm

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („Maschine verfahren“, Manuel: zuerst
  „wie im Programm“) und Stufe 3b, Schritt 4; `gui_verfahren.py`,
  `gui_zeigen.py` (Wackeln).

### DATEIEN
- `camaddon/schraege_achse.py` (`Programm`, `achsen`, `_ueberfahren`)
- `camaddon/gui_verfahren.py` (Umschalter, Programmzeilen, graue Zeile, rote
  Zeile am Anschlag)
- `camaddon/gui_zeigen.py` (`WackelnProgramm`), `camaddon/gui_maschine.py`
- `help/de/verfahren.html`, `help/en/verfahren.html`,
  `help/de/transformationen.html`, `help/en/transformationen.html`
- `translations/de.json`, `translations/en.json` (10 Texte)
- `tests/test_schraege_achse.py`, `tests/gui/szenario_verfahren_schraeg.py` (neu)
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit schräger Achse (Winkel 30° eingetragen) →
„Maschine verfahren“ → oben steht „wie im Programm“, Regler X und Y → Y auf
10 → beide Schlitten fahren, grau darunter „Schlitten: X1 −5,77 mm, Y1
11,55 mm“ → X auf 140, Y auf −40 → Y hält bei −17,32, rot: „Weiter geht Y
hier nicht: X1 steht an seiner Grenze 150,00 mm.“

### DONE
- `schraege_achse.Programm`: X und Y des Programms über einem Verfahren –
  Stellung aus den Schlitten, `setze(x, y)` fährt beide Schlitten auf der
  Geraden zum Ziel und hält an, wo einer an eine Grenze stößt (gibt Achse
  und Grenze zurück), `bereich()` so weit die Achsen überhaupt kommen.
- „Maschine verfahren“: Hat die Maschine eine gültige schräge Achse, steht
  oben „Achsen: (•) wie im Programm ( ) der Maschine“, zuerst „wie im
  Programm“. Dann stehen X und Y (Namen aus dem Eintrag) statt X1 und Y1
  da, mit Grenzen „Höchstens … – wie weit es geht, hängt davon ab, wo X
  steht“; grau darunter die Schlitten. „der Maschine“ baut die Zeilen wie
  bisher, grau darunter das Programm. Am Anschlag eine rote Zeile; jede
  andere Bewegung blendet sie aus. Das Raster wird beim Umschalten neu
  gebaut; die grauen Zeilen brechen um und reichen bis zum Rand, damit sie
  das Fenster nicht verbreitern.
- „Maschine bearbeiten“: Verweilt die Maus auf dem Eintrag, fährt die
  Maschine einmal ein Y des Programms hin und her (`WackelnProgramm`:
  X-Schlitten und Y-Schlitten zusammen), danach steht alles exakt wie
  vorher.
- Hilfe: „Maschine verfahren“ erklärt den Umschalter und den Arbeitsraum als
  Parallelogramm; „Transformationen“ verweist darauf.
- Bewusst so: nur die erste gültige schräge Achse einer Maschine (mehrere
  hat keine bekannte Maschine).
- Gefunden, nicht hier behoben: Das Verfahrfenster ist mit der
  Beispiel-Drehmaschine breiter als der Aufgabenbereich (Mindestbreite 423
  Pixel; die grauen Grenzen-Zeilen brechen nicht um) – schon vor diesem
  Patch; eigener Patch gleich danach.

### TEST
- Claude ohne Oberfläche, 1.1.3 und Wochen-Build: `test_schraege_achse.py`
  zusätzlich: Y 10 → X1 −5,7735, Y1 11,547; Bereich X −200 … 180, Y
  ±51,96; X 140 und Y −40 → Anschlag X1 bei 150, Y −17,3205; Y 70 →
  Anschlag Y1 bei 60 (Y 51,96); zurück, Grundstellung; ohne ausgleichende
  Achse nicht möglich.
- Claude mit Oberfläche (Screenshots angesehen), beide Versionen:
  `szenario_verfahren_schraeg` – Verweilen bewegt beide Schlitten und
  stellt zurück, Umschalter zuerst „wie im Programm“, Achsen C1, T,
  Werkzeugantrieb, Z1 plus X und Y, Y 10, Anschlag mit rotem Satz, „der
  Maschine“ mit grauem Programm, Y1 von Hand auf 0, Grundstellung,
  Abbrechen fährt alles zurück. `szenario_verfahren`,
  `szenario_beispielmaschine`, `szenario_mausrad`, `szenario_schraege_achse`
  laufen weiter grün (Wochen-Build).
- Ob sich „wie im Programm“ verständlich bedient, prüft Manuel.

### NEXT
- Verfahrfenster schmaler (eigener Patch), dann Stufe 3b, Schritt 5: An CAM
  übergeben.

## P-2026-09-26-68 schraege-achse-erkennen

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („Erkennung“) und Stufe 3b, Schritt 3.

### DATEIEN
- `camaddon/schraege_achse.py` (`ohne_eintrag`, `Anlegen`, Hinweis in `pruefe`)
- `camaddon/gui_maschine.py` (Klick auf den Hinweis legt an)
- `translations/de.json`, `translations/en.json`
- `tests/test_schraege_achse.py`, `tests/gui/szenario_schraege_achse.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Eine Baugruppe, deren Y-Führung 30° schräg zu X steht, ohne Eintrag →
„Maschine bearbeiten“ → unter „Hinweise“ steht „Y1 steht 30,0° schräg zu X1.
Rechnet die Steuerung ein rechtwinkliges „Y“ auf beide um …?“ → Klick
darauf → unter „Transformationen“ steht „Schräge Achse Y1 – gleicht aus:
X1, 30,0°“, und der Hinweis ist weg.

### DONE
- `schraege_achse.ohne_eintrag()`: alle Paare von Linearachsen, die weder
  rechtwinklig (unter 0,05° – Rundungsreste; ab da zeigt der Dialog 0,1°)
  noch fast parallel (über 89°) stehen und noch keine schräge Achse haben –
  auch nicht mit vertauschten Rollen. Ausgleichend ist die im Alphabet
  vordere. `vorschlag()` nutzt es.
- `pruefe()` gibt je solches Paar einen **Hinweis** (keine Warnung – eine
  Maschine darf schräge Achsen ohne Umrechnung haben; „An CAM übergeben“
  fragt deshalb nicht nach). Sein Bezug ist `Anlegen(schräg, ausgleich)`;
  ein Klick darauf legt die schräge Achse an – zeitversetzt, weil der
  Neuaufbau auch die angeklickte Zeile ersetzt.
- Der Winkel im Satz mit dem gewählten Dezimalzeichen („30,0°“), ohne
  Oberfläche gerechnet (`_winkel_text`).

### TEST
- Claude ohne Oberfläche, 1.1.3 und Wochen-Build: `test_schraege_achse.py`
  zusätzlich: rechtwinklige Maschine ohne Hinweis; 30° ohne Eintrag – ein
  Hinweis, Text „Y1 steht 30,0° schräg zu X1.“ mit „Y“, Bezug Y1/X1, auch
  über `m.pruefe`; mit Eintrag (auch vertauscht) kein Hinweis.
- Claude mit Oberfläche (Screenshot angesehen), beide Versionen:
  `szenario_schraege_achse` – der Hinweis steht da, ein Klick legt den
  Eintrag mit 30,0° an, der Hinweis verschwindet.

### NEXT
- Stufe 3b, Schritt 4: „Maschine verfahren“ wie im Programm.

## P-2026-09-26-67 schraege-achse-winkel-eintragen

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c („Winkel eintragen, die Baugruppe
  folgt“, Manuels Entscheidung) und Stufe 3b, Schritt 2; Versuch aus
  P-2026-09-26-65.

### DATEIEN
- `camaddon/schraege_achse.py` (`drehe_fuehrung`, `_drehe_gelenk`)
- `camaddon/verfahren.py` (`setze(…, grenzen=False)`)
- `camaddon/gui_details.py`, `camaddon/gui_maschine.py`, `camaddon/gui_zahlen.py`
- `help/de/transformationen.html`, `help/en/transformationen.html`
- `translations/de.json`, `translations/en.json`
- `tests/test_schraege_achse.py`, `tests/gui/szenario_schraege_achse.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine → „Maschine bearbeiten“ → „+ Schräge Achse“ → im Feld
„Winkel“ 30 eintragen → in der 3D-Ansicht bleibt alles stehen, der Eintrag
zeigt 30,0° und „Y +10,0 mm → Y1 +11,5 mm, X1 −5,8 mm“; „Maschine verfahren“
fährt Y1 danach schräg; Abbrechen stellt die Führung zurück.

### DONE
- `schraege_achse.drehe_fuehrung()`: dreht beide Koordinatensysteme des
  Y-Schiebegelenks um die Normale der Ebene aus schräger und ausgleichender
  Achse (so, dass α um die Differenz wächst), je um ihren Ursprung, über
  Offset1/Offset2 (global = ohne Versatz · Versatz). Nach jeder Änderung am
  Versatz kommen die Teile zurück (FreeCAD löst vorab und rückt sonst
  Teile). Steht der Schlitten nicht auf 0, fährt er vorher auf 0 und danach
  wieder auf seine Stellung – nun entlang der neuen Richtung, auch außerhalb
  der Grenzen (`Verfahren.setze(…, grenzen=False)`). Über ±89°: ValueError.
- Dialog: Das Feld „Winkel“ (mit „°“, auch negative Zahlen:
  `Zahlenpruefer(mit_minus=True)`) zeigt den Winkel der Baugruppe; ein
  anderer Wert dreht die Führung, danach zeigen Liste, Bild und Beispiel den
  neuen Stand. Leer oder unverändert: nichts passiert. Über ±89° sagt ein
  roter Satz am Feld, warum nicht, und das Feld zeigt wieder den alten
  Winkel. Die Bewegung beim Zeigen (Wackeln) hält vorher an.
- Tooltip und Hilfe erklären das Eintragen; „… – aus der Baugruppe“ als
  Anzeige entfällt (das Feld ersetzt es).

### TEST
- Claude ohne Oberfläche, 1.1.3 und Wochen-Build: `test_schraege_achse.py`
  zusätzlich: 30° eintragen – kein Teil bewegt sich, auch nicht beim
  Neuberechnen; Rückgängig stellt 0° und alle Lagen wieder her,
  Wiederholen 30°; mit Y1 auf 20 mm auf −15° – die Stellung bleibt 20 mm,
  der Schlitten steht 20 mm entlang der neuen Richtung, der Revolver dreht
  sich nicht; zurück auf 0° und Stellung 0 – alles wie gebaut; 89,5°, −90°
  und 120° abgelehnt, ohne etwas zu drehen. Dazu `test_sprache`,
  `test_hilfe`, `test_verfahren`, `test_maschine`.
- Claude mit Oberfläche (Screenshots angesehen), beide Versionen:
  `szenario_schraege_achse` – 30 eintragen (Liste, Feld, Beispiel, keine
  Teile bewegt), 95 abgelehnt mit rotem Satz, Abbrechen stellt die Führung
  zurück (Y wieder rechtwinklig zu X).
- Ob sich das Eintragen verständlich anfühlt, prüft Manuel.

### NEXT
- Stufe 3b, Schritt 3: Erkennung schräg stehender Linearachsen.

## P-2026-09-26-66 schraege-achse-eintrag

### EINGELESEN
- Spezifikation W-001, Abschnitt 7c und Stufe 3b, Schritt 1
  (P-2026-09-26-65). Manuel: „weiter machen mit Sachen, die man verbessern
  kann … bis zu einem sinnvollen Punkt“.
- `maschine.py` (Objektarten, `pruefe`, `rollen`), `gui_maschine.py`,
  `gui_details.py`, `gui_zahlen.py`, `verfahren.py` (`_vorzeichen`),
  `hilfe.py`, `tests/test_hilfe.py`, `tests/test_sprache.py`.

### DATEIEN
- `camaddon/schraege_achse.py` (neu), `camaddon/gui_winkelbild.py` (neu)
- `camaddon/maschine.py`, `camaddon/gui_maschine.py`,
  `camaddon/gui_details.py`, `camaddon/gui_zahlen.py`,
  `camaddon/verfahren.py`, `camaddon/hilfe.py`
- `help/de/transformationen.html`, `help/en/transformationen.html` (neu)
- `translations/de.json`, `translations/en.json` (28 Texte)
- `tests/test_schraege_achse.py` (neu), `tests/beispielmaschinen.py`,
  `tests/gui/szenario_schraege_achse.py` (neu)
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/aufbau.md`, `CHATSTART.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine laden → „Maschine bearbeiten“ → „+ Schräge Achse“ →
unter „Transformationen“ steht „Schräge Achse Y1 – gleicht aus: X1, 0,0°“,
darunter Y1 und X1, die Namen Y und X, „0,0° – aus der Baugruppe“, das Bild
und „Beispiel: Y +10,0 mm → Y1 +10,0 mm, X1 0,0 mm“.

### DONE
- Maschinenobjekt: dritte Art von Eintrag, die **Transformation**
  (`TRAFO_SCHRAEGE_ACHSE`): Verweise `Schraeg` und `Ausgleich` auf
  Betriebsarten (Linear), `NameSchraeg`/`NameAusgleich` – vorbelegt mit dem
  NC-Namen ohne Ziffern am Ende (Y1 → Y). Beschriftung „Y · Schräge Achse“.
  Der Winkel steht bewusst nicht im Objekt, nur in der Baugruppe.
- `schraege_achse.py`: Winkel α aus den Gelenkrichtungen (asin des
  Skalarprodukts der Plus-Richtungen; Tischachsen zählen für das Werkzeug
  andersherum), Rechnung Programm ↔ Schlitten, Vorschlag für eine neue
  schräge Achse (zuerst ein schräges Paar ohne Eintrag, sonst die ersten
  beiden Linearachsen; ausgleichend ist die im Alphabet vordere), Prüfung
  mit vier Meldungen (Achse fehlt, gleiche Achse, keine Linearachse, fast
  parallel über 89°). `verfahren.plusrichtung()` neu (öffentlich statt
  `_vorzeichen` von außen).
- Dialog: Bereich „Transformationen“ unter den Achsen mit Hilfe (?),
  Liste (ohne Eintrag eine graue Zeile „keine – nur nötig, wenn die
  Steuerung umrechnet“), „+ Schräge Achse“ (ohne zwei Linearachsen gesperrt,
  der Tooltip sagt warum) und „Entfernen“. Felder: schräge und
  ausgleichende Achse als Auswahl, Namen im Programm (wandern mit, solange
  sie der Vorschlag sind: Z1 gewählt → Z), Winkel „30,0° – aus der
  Baugruppe“, Bild (`gui_winkelbild.py`: X1, gestrichelt der rechte Winkel
  mit dem Programm-Y, Y1 um α gekippt, Bogen α – ohne Text außer
  Achsnamen) und das Beispiel in mm bzw. inch. Verweilen hebt beide
  Schlitten hervor. Wer eine Betriebsart entfernt, löst ihren Verweis in
  der schrägen Achse (die dann „fehlt eine Achse“ meldet).
- Hilfeseite „Transformationen“ (de/en): was sie sind, Rechnung mit
  Beispiel, was man einträgt, wo der Winkel bei Siemens (TRAANG,
  `TRAANG_ANGLE_1`) und Fanuc („Angular Axis Control“) steht,
  Vorzeichen andersherum möglich, Postprozessor bleibt.
- `gui_zahlen.winkel_zeigen()`: „30,0°“ mit dem gewählten Dezimalzeichen.
- Bewusst noch nicht: den Winkel eintragen (Schritt 2), das
  Hin-und-her-Fahren beim Verweilen (braucht das gekoppelte Verfahren aus
  Schritt 4), Erkennung als Hinweis (Schritt 3).

### TEST
- Claude ohne Oberfläche, 1.1.3 und Wochen-Build: `test_schraege_achse.py`
  – Rechnung (30°: Y +10 → Y1 11,547, X1 −5,774; −30°; 0°; hin und zurück
  für sechs Winkel), Winkel 0° an der Beispiel-Drehmaschine, +30° und −30°
  mit gekippter Y-Führung (Testhilfe `beispielmaschinen.kippe_fuehrung`),
  89,5° → Meldung „parallel“, Vorschlag, Namen, Meldungen, Tisch/Kopf,
  Speichern und Laden. Dazu `test_sprache`, `test_hilfe`, `test_maschine`,
  `test_verfahren`, `test_kette`, `test_export`, `test_beispielmaschine`.
- Claude mit Oberfläche (Screenshots angesehen), 1.1.3 und Wochen-Build:
  `szenario_schraege_achse` – leere Liste, anlegen, Felder, Z1 wählen
  (Name wandert mit), Abbrechen verwirft, 30° gekippt zeigt 30,0° und
  „Y1 +11,5 mm, X1 −5,8 mm“, Entfernen, Hilfe. Die Szenarien
  `maschine_bearbeiten`, `hilfe`, `mausrad`, `beispielmaschine`, `felder`
  laufen weiter grün (Wochen-Build).
- Ob der Bereich verständlich ist, prüft Manuel.

### NEXT
- Stufe 3b, Schritt 2: Winkel eintragen, die Baugruppe folgt.

## P-2026-09-26-65 spezifikation-schraege-achse

### EINGELESEN
- Manuel (2026-09-26): „schrägbett kinematik … eine schräge Achse für X
  und noch eine schräge Achse für Y, und beide müssen verfahren, um Y zu
  bewegen … erstmal nur planen“. Nach dem Plan im Chat: „das sind alles
  wichtige Faktoren, die man eingeben können sollte … oder so, dass es ein
  Leichtes ist, so etwas zu erstellen“.
- Seine Wahl aus vier Fragen mit Optionen: erst Eintrag in „Maschine
  bearbeiten“, danach Vorlage mit Eingabemaske; Winkel eintragen, die
  Baugruppe folgt; „Maschine verfahren“ zuerst wie im Programm. Zur
  Auswahl der Steuerung: „Man hat doch einen Postprozessor??“
- `spezifikation_maschine_aus_baugruppe.md`, `spezifikation_simulation.md`
  (Abschnitt 4 rechnet schon mit schiefen Achsen), `kette.py`,
  `verfahren.py`, `export.py`, `beispielmaschine.py` (Drehmaschine:
  Schrägbett 45°, Y rechtwinklig zu X), `gui_maschine.py`, `maschine.py`,
  `schruppwerte.py` (Höchstvorschub = kleinster aller Linearachsen).
- FreeCADs CAM-Maschinendefinition (Wochen-Build,
  `Mod/CAM/Machine/models/machine.py`): je Linearachse nur Richtung,
  Grenzen, Eilgang; keine Transformation. Für Bahnen nutzt CAM nur die
  Drehachsen (`Path/Base/Generator/rotation.py`); die Maschine trägt einen
  Postprozessor (`postprocessor_file_name`).
- Siemens 840D sl, Funktionshandbuch Sonderfunktionen: TRAANG,
  `TRAANG_ANGLE_1`, −90° < α < 90°. Fanuc: „Angular Axis Control“
  (Parameternummern nicht nachgeprüft, deshalb nicht genannt).

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 7c neu,
  Abschnitt 2 ergänzt, Stufe 3b, Entschieden)
- `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel findet in Abschnitt 7c der Maschinen-Spezifikation seine vier
Entscheidungen, die Rechnung mit Beispiel und die sieben Schritte mit
Klickweg wieder.

### DONE
- Abschnitt 7c „Schräge Achse“: Begriffe (schräge und ausgleichende Achse,
  Winkel α, Programmachsen), Rechnung in beide Richtungen mit Beispiel
  (α = 30°: Y +10 → Y1 +11,547, X1 −5,774), Folgen (Arbeitsraum als
  Parallelogramm, Geschwindigkeit min(vY1 · cos α, vX1 ÷ tan α)),
  Transformation als dritte Art von Eintrag im Maschinenobjekt, Winkel nur
  in der Baugruppe, Erkennung, Skizzen für „Maschine bearbeiten“ und
  „Maschine verfahren“, Übergabe an CAM, Schruppwerte, Stufe 4, Vorlage,
  „Nicht Teil davon“.
- Stufe 3b mit sieben Schritten; Entscheidung unter „Entschieden“ – ohne
  Auswahl der Steuerung, wie Manuels Rückfrage nahelegt: Die Steuerung
  steckt im Postprozessor, und das Programm bleibt rechtwinklig.
- Bewusst offen: Aufbau der Vorlage (eigener Befehl oder in
  „Beispielmaschine laden …“) – wird vor Schritt 7 mit Skizze entschieden;
  das Vorzeichen von α bei Siemens – vor dem Hilfetext im Handbuch prüfen.

### TEST
- Versuch (Claude, ohne Oberfläche, 1.1.3 und Wochen-Build): an der
  Beispiel-Drehmaschine beide Gelenk-Koordinatensysteme des Y-Gelenks um
  30° gedreht (Offset1/Offset2, um die Normale der X/Y-Ebene). Ergebnis in
  beiden Versionen: kein Teil bewegt sich, X/Y stehen danach 120° (Y 30°
  aus dem rechten Winkel), Y1 = 10 fährt den Schlitten genau 10 mm in der
  neuen Richtung, der Revolver dreht sich nicht, die Stellung bleibt beim
  Neuberechnen, die Grundstellung ist exakt, der Winkel bleibt nach
  Speichern und Laden. Damit trägt die Entscheidung „die Baugruppe folgt“.
- Reine Doku, kein Testlauf.

### NEXT
- Stufe 3b, Schritt 1: Eintrag „Schräge Achse“ in „Maschine bearbeiten“.

## P-2026-09-26-64 version-0-18-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.17.0: Beispielmaschinen zur Auswahl (P-2026-09-26-62), ruhiges Mausrad
  (-63).

### DATEIEN
- `package.xml` (0.18.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.18.0.

### DONE
- Version 0.17.0 → 0.18.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Schrägbett-Kinematik planen (Manuel).

## P-2026-09-26-63 ruhiges-mausrad

### EINGELESEN
- #39 und P-2026-09-26-52: Das „P10“ in Manuels Revolverplatz war sehr
  wahrscheinlich das Mausrad beim Blättern im Aufgabenfenster.
- Alle Auswahllisten, Drehfelder und Regler des Addons (`gui_*.py`), Qts
  Weitergabe von Rad-Ereignissen (nur echte, nicht mit sendEvent
  geschickte), FreeCADs eigenes `Gui::WheelEventFilter` (1.1.3 und
  Wochen-Build, dort erweitert).

### DATEIEN
- `camaddon/gui_teile.py` (`ruhiges_mausrad`, `RuhigerRegler`)
- `camaddon/gui_werkzeuge.py`, `gui_job_schnittwerte.py`, `gui_werkstoffe.py`,
  `gui_strategie.py`, `gui_verteilhilfe.py`, `gui_verfahren.py`,
  `gui_details.py`, `gui_maschine.py`, `gui_sprachwahl.py`
- `tests/gui/szenario_mausrad.py` (neu)
- `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Maschine bearbeiten“ an der Beispiel-Drehmaschine → P3 wählen → mit dem
Mausrad über dem Feld „Revolverplatz“ blättern: Das Aufgabenfenster rollt,
der Platz bleibt P3. Erst nach einem Klick ins Feld rollt das Rad den Wert.
Genauso Art und Nummer in der Werkzeugverwaltung, der Einsatz je Zeile in
„Schnittwerte in den Job“, die Regler in „Maschine verfahren“.

### DONE
- Auswahllisten, Drehfelder und Regler aller Dialoge und Aufgabenfenster
  nehmen das Mausrad nur mit Fokus; den Fokus gibt ihnen das Rad auch nicht
  mehr. Ohne Fokus geht die Raste an den nächsten Bereich darüber, der
  rollen kann – Aufgabenfenster oder Tabelle blättern weiter.
- Die Regler in „Maschine verfahren“ lehnen das Rad ohne Fokus selbst ab:
  Im Wochen-Build kommt es im Aufgabenfenster am Filter vorbei.
- Im Wochen-Build schützt FreeCAD Drehfelder im Aufgabenfenster schon
  selbst und schluckt das Rad dabei – dort rollt das Fenster über einem
  Feld nicht weiter (FreeCADs Verhalten); verstellt wird nichts.

### TEST
- Neu `szenario_mausrad`: Rasten über XTest wie von einer Maus; Sprachwahl,
  Art und Nummer (mit Fokus rollt die Nummer T1 → T2), Revolverplatz mit
  Gegenprobe (ein Drehfeld ohne Filter verstellt sich in 1.1.3, das
  Fenster rollt), Regler und Feld beim Verfahren – in 1.1.3 und im
  Wochen-Build. Szenarien `werkzeugverwaltung`, `schnittwerte_job`,
  `verfahren`, `erster_start`, `werkstoffe`, `strategien` im Wochen-Build.

### NEXT
- Schrägbett-Kinematik planen (Manuel): X und Y als schräge Achsen, für
  eine Bewegung in Y fahren beide.

## P-2026-09-26-62 beispielmaschinen-zur-auswahl

### EINGELESEN
- STATUS_SNAPSHOT Punkt 7b (Manuel nach dem ersten Ausprobieren): die
  üblichen Bauarten zur Auswahl – Schrägbett-Drehmaschine mit Y-Achse
  (CLX-ähnlich, Revolver mit radialem und axialem angetriebenem Werkzeug),
  3-Achs-Fräse, 5-Achs Tisch/Tisch (A/C), Kopf/Kopf (A/B), Kopf/Tisch
  (B/C).
- Der geparkte Stand im Stash „WIP Beispielmaschinen zur Auswahl“
  (Baukasten, fünf Bauarten, Auswahldialog), `tests/test_beispielmaschine.py`,
  `tests/gui/szenario_beispielmaschine.py`, `tests/gui/szenario_zoll.py`.

### DATEIEN
- `camaddon/beispielmaschine.py` (Baukasten erweitert: Rahmen, gedrehte
  Zylinder, LCS mit Richtung; fünf Bauarten; `titel`, `beschreibung`,
  `zuletzt_gewaehlt`, `lade(art)`)
- `camaddon/gui_maschine.py` (`beispiel_waehlen`, `BeispielAuswahl`),
  `camaddon/gui_verfahren.py`
- `translations/de.json`, `translations/en.json`
- `help/de/achsen.html`, `help/en/achsen.html`, `help/de/verfahren.html`,
  `help/en/verfahren.html`
- `docs/aufbau.md`, `docs/STATUS_SNAPSHOT.md`
- `tests/test_beispielmaschine.py`, `tests/gui/szenario_beispielmaschine.py`,
  `tests/gui/szenario_zoll.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Leeres FreeCAD → „Maschine bearbeiten“ → „Beispielmaschine laden …“ → die
Auswahl zeigt fünf Bauarten mit je einem Satz dazu; „Drehmaschine mit
Y-Achse“ → Laden: Dokument „Beispiel Drehmaschine“, der Dialog ist offen,
P1 auf dem Revolver hat das Feld „Revolverplatz“. „Maschine verfahren“ in
einem leeren Dokument → 3-Achs-Fräse → X1, Y1, Z1 fahren.

### DONE
- „Beispielmaschine laden …“ bietet fünf Bauarten an, fertig eingerichtet:
  Drehmaschine mit Y-Achse (Schrägbett 45°, Hauptspindel S1/C1, X1, Y1, Z1,
  Revolver T mit zwölf Plätzen, P1 radial und P2 axial angetrieben an S3),
  3-Achs-Fräse (X1, Y1, Z1, S1), 5-Achs Tisch/Tisch (A1, C1), Kopf/Kopf (A1,
  B1), Kopf/Tisch (B1, C1) – je mit Werkzeug- und Werkstückaufnahme.
- Die Auswahl steht beim nächsten Mal auf der zuletzt geladenen; Doppelklick
  lädt.

### TEST
- `test_beispielmaschine` (neu: alle fünf – Achsen, keine Warnung, Teile
  bleiben beim Neuberechnen, jede Achse fährt, Grundstellung, Revolver)
  in 1.1.3 und im Wochen-Build; Szenarien `beispielmaschine` (neu: Auswahl,
  Drehmaschine mit Revolverplatz, Übersicht aller fünf als Bild) und
  `zoll` in beiden. Bilder angesehen.

### NEXT
- #39: Mausrad soll Felder und Auswahllisten nicht verstellen, wenn man
  nur über sie scrollt.

## P-2026-09-26-61 version-0-17-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.16.0: Revolverplatz nur am Revolver (P-2026-09-26-52), die 26
  Werkzeugarten (P-2026-09-26-53 bis -60), Szenario wartet auf die
  Beispielmaschine (-57).

### DATEIEN
- `package.xml` (0.17.0; Beschreibung nennt die 26 Werkzeugarten)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.17.0.

### DONE
- Version 0.16.0 → 0.17.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann die Beispielmaschinen zur Auswahl (Punkt 7b).

## P-2026-09-26-60 einsaetze-in-den-job

### EINGELESEN
- Spezifikation Werkzeugarten, Abschnitt 8 (Stufe 6): die neuen Einsätze
  auf die passenden Operationen.
- `camaddon/job_schnittwerte.py` (`EINSATZ_NACH_OPERATION`,
  `ZUSTELLUNG_NACH_OPERATION`, `vorgeschlagener_einsatz`, `zustellung`),
  die Operationen in 1.1.3 und im Wochen-Build (`Path/Op`: MillFace,
  MillFacing, Deburr, ThreadMilling, Tapping, Drilling, Engrave, Vcarve).

### DATEIEN
- `camaddon/job_schnittwerte.py`
- `translations/de.json`, `translations/en.json` (Tooltip der Zustellung)
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `docs/spezifikation_werkzeugarten.md`, `docs/STATUS_SNAPSHOT.md`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit Fläche (Planfräser, Einsätze „Sonder“ und „Planen“ ae 37,5 ap 2)
und Bohrung (Zentrierbohrer) → „Schnittwerte in den Job“: Der Planfräser
bekommt „Planen“ und „Fläche: 75 % · 2 mm“, der Zentrierbohrer „Zentrieren“
mit n 2546 und vf 255 – senkrecht der volle.

### DONE
- Je Operation die passenden Einsätze, der passendste zuerst: Fläche →
  Planen oder Schruppen, Profil → Schlichten, Verrunden oder Fasen,
  Entgraten → Fasen oder Verrunden, Gravieren und V-Carve → Fasen,
  Gewindefräsen, Gewindebohren, Bohren → Bohren, Zentrieren, Senken,
  Reiben, Ausdrehen, Gewindebohren. Bisherige Zuordnungen bleiben.
- Planen gibt der Fläche (auch dem Planfräsen des Wochen-Builds) ae als
  Schrittweite und ap als Zustelltiefe.
- Stufe C der Werkzeugarten damit fertig; STATUS_SNAPSHOT nachgezogen.

### TEST
- `test_job_schnittwerte` (neu: Fläche, Entgraten, Bohrung; Einsatz aus der
  zweiten und fünften Zeile; Zustellung Planen) in 1.1.3 und im
  Wochen-Build; Szenario `schnittwerte_job` (neu: Planfräser und
  Zentrierbohrer) in beiden. Bild angesehen.

### NEXT
- Version 0.17.0, voller Lauf `scripts/alle_tests.sh` in beiden Versionen,
  Push von P-52 bis P-60.
- Danach Punkt 7b: Beispielmaschinen zur Auswahl (Stash).

## P-2026-09-26-59 cam-alle-werkzeugarten

### EINGELESEN
- Spezifikation Werkzeugarten, Abschnitte 2, 6 und 8 (Stufe 5): CAM-Form je
  Art, Näherungen, Übernahme je Form.
- FreeCAD CAM in 1.1.3 und im Wochen-Build: die Formen (`Path/Tool/shape/
  models`, Skizzen und Ausdrücke in `Tools/Shape/*.fcstd`), die Musterwerkzeuge
  in `Tools/Bit`, `ToolBit.from_dict`/`from_shape`, `ThreadMilling`,
  `Tapping`/`Drilling` (Pitch, SpindleDirection), `FeedsSpeeds` (Chipload je
  Zahn mal Flutes, `vert_feed_ratio`), das Bibliotheksfenster.

### DATEIEN
- `camaddon/uebergabe_werkzeuge.py` (FORMEN aller Arten, NAEHERUNGEN,
  Parameter je Form, Drehrichtung, Chipload, Mindestschaft)
- `camaddon/werkzeuge_aus_cam.py` (jede Form → Art, alle Maße der Art)
- `camaddon/werkzeuge.py` (`mass`, `reichweite`, Gesamtlänge ab Halsende,
  `schaft_fuer_cam` je Art)
- `camaddon/werkzeugform.py` (Schätzungen aus `werkzeuge.mass`; `konus`,
  `kegel`, `radienprofil` auch für CAM; Konikkegel tangential, Radienbogen
  ab dem Spitzen-Ø)
- `camaddon/gui_werkzeuge.py` (Bericht: Näherungen; Schaft-Platzhalter)
- `translations/de.json`, `translations/en.json`
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `docs/spezifikation_werkzeugarten.md`, `docs/aufbau.md`
- `tests/test_cam_formen.py` (neu), `tests/test_uebergabe_werkzeuge.py`,
  `tests/test_werkzeuge_aus_cam.py`, `tests/test_werkzeuge.py`,
  `tests/gui/szenario_an_cam.py`, `tests/gui/szenario_aus_cam.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung mit Gewindebohrer links, Konik-, Lollipop-,
Schwalbenschwanzfräser, Taster und Drehwerkzeug → „Speichern und an CAM
übergeben“: Die Rückmeldung nennt „T9 Lollipopfräser als Kugelfräser“ und
„Drehwerkzeuge bleiben hier: T15 Drehwerkzeug“. In CAM → Werkzeugbibliothek
„CAM-Addon“ steht jedes mit seiner Form (Left Hand tap 1,5 mm, 6° taper,
60° dovetail, probe). „Aus CAM übernehmen“ → „Default“ übernimmt alle 13
Werkzeuge, auch Gravierstichel (Fasenfräser), Säge (Nutenfräser), Taster und
Gewindefräser.

### DONE
- Übergabe: jede der 23 Arten, die nicht drehen, mit ihrer CAM-Form und
  deren Parametern; leere Felder geschätzt wie im Bild, damit CAM denselben
  Körper baut. Näherungen (Lollipop-, Plan-, Formfräser, Zentrierbohrer,
  Flachsenker, Bohrstange, Ausspindelwerkzeug) nennt der Bericht; die
  Drehwerkzeuge bleiben hier.
- Gewindebohrer mit Steigung, links rückwärts drehend, ohne Schneidenzahl
  und ohne Chipload; Taster ohne Drehrichtung und Schneidstoff; Reibahle
  (in CAM ohne Schneidenzahl) mit f je Umdrehung als Chipload; Presets der
  bohrenden Arten mit vollem Eintauchvorschub wie „Schnittwerte in den Job“.
- CAMs Skizzen vertragen keine Kante der Länge 0 und keinen Hals bis ans
  Ende: Säge mit 1 µm Kappe, Gewindebohrer-Schaft = D wird 1 µm dünner, zu
  kurze Gesamtlänge bekommt 1 mm Schaft. Die geschätzte Gesamtlänge zählt
  jetzt ab dem Ende des Halses (beim Gewindefräser brach vorher CAMs Körper).
- Übernahme: jede Form hat ihre Art (vbit → Fasenfräser, tap nach
  Drehrichtung, threadmill mit einem Zahn: Schneidenlänge = Zahnhöhe);
  gesetzt wird nur, was die Art als Feld hat; fehlt die Schneidenzahl, die
  der Beispiele der Art.
- Die Schätzungen für Bild und CAM an einer Stelle (`werkzeuge.mass`); das
  Bild des Radienfräsers nimmt jetzt den Spitzen-Ø, der Konikkegel berührt
  die Kugel.

### TEST
- Neu `test_cam_formen`: alle Arten an CAM, Beispiele, Schaft = D und zu
  kurze Gesamtlänge; CAM baut jeden Körper ohne Klage auf der Konsole, nur
  Parameter der Form, auf 40 Höhen wie das Bild, zurück aus CAM dieselben
  Maße. Gegenprobe: Kappe 0, Schaft = D und halber Kegelwinkel fängt er.
- `test_uebergabe_werkzeuge`, `test_werkzeuge_aus_cam`, `test_werkzeuge`,
  `test_werkzeugform`, `test_sprache`, `test_hilfe` in 1.1.3 und im
  Wochen-Build; Szenarien `an_cam`, `aus_cam` in beiden, `werkzeugbilder`,
  `werkzeugverwaltung` in 1.1.3. Bilder angesehen.

### NEXT
- Stufe C6: die neuen Einsätze auf die passenden Operationen im Job.

## P-2026-09-26-58 einsaetze-je-art

### EINGELESEN
- Spezifikation Werkzeugarten, Abschnitte 5 und 8 (Stufe 4): Einsätze je
  Art, Rechnen für Bohren, Gewindebohren, Drehen, Taster.
- `camaddon/gui_schnittwerte.py` (sechs Stellen „Bohrer oder nicht“),
  `camaddon/schnittdaten.py` (`rechne`), `camaddon/job_schnittwerte.py`
  (Eintauchvorschub), `camaddon/uebergabe_werkzeuge.py` (Presets), die
  Bearbeitungsarten der FreeCAD-Presets (`FeedsSpeeds.types.OP_TYPES`).

### DATEIEN
- `camaddon/werkzeuge.py` (neun Einsatzarten, `EINSAETZE_JE_ART`,
  `einsatzarten`, `bohrend`, `gewindebohrer`, Vorlage Planen)
- `camaddon/schnittdaten.py`, `camaddon/gui_schnittwerte.py`,
  `camaddon/job_schnittwerte.py`, `camaddon/uebergabe_werkzeuge.py`
- `translations/de.json`, `translations/en.json`
- `docs/spezifikation_werkzeugarten.md`
- `tests/test_schnittdaten.py`, `tests/test_werkzeuge.py`,
  `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Gewindebohrer rechts M10 → „+ Einsatz“ bietet nur
„Gewindebohren“ und „Eigener Einsatz“; mit vc 10 zeigt die Zeile f 1,5
(fest), n 318, vf 477. Ein Drehwerkzeug zeigt statt der Tabelle einen Satz.

### DONE
- Neue Einsatzarten: Planen, Fasen, Verrunden, Gewindefräsen, Zentrieren,
  Senken, Reiben, Gewindebohren, Ausdrehen – je Art nur die passenden.
- Bohrende Arten (Gruppe Bohren) wie bisher der Bohrer: f je Umdrehung,
  ohne ae/ap, kein Vergleich, kein Eingriffsbild; im Job tauchen sie mit
  vollem Vorschub ein. Gewindebohrer: vf = n · P, f fest (grau), Hinweis
  nur für vc. Q nur beim Fräsen und beim Bohrer ins Volle.
- Drehwerkzeuge und Taster: ein Satz statt der Tabelle.
- Presets für CAM: neue Einsätze auf FreeCADs sechs Bearbeitungsarten.

### TEST
- `test_schnittdaten` (Gewindebohrer, Reibahle), `test_werkzeuge`
  (Einsätze je Art, Vorlage Planen), `test_sprache`,
  `test_uebergabe_werkzeuge`, `test_job_schnittwerte`, `test_schruppwerte`
  in 1.1.3 und im Wochen-Build; Szenarien `schnittwerte` (neu:
  Gewindebohrer, Drehwerkzeug), `werkzeugverwaltung`, `strategien`,
  `schnittwerte_job` in 1.1.3. Bilder angesehen.

### NEXT
- Stufe C5: Übergabe an CAM und Übernahme aus CAM für alle Arten.

## P-2026-09-26-57 szenario-wartet-auf-beispielmaschine

### EINGELESEN
- `szenario_zoll` scheiterte beim Lauf für P-2026-09-26-56 einmal:
  „Maschine verfahren öffnet sich nicht“, im Protokoll „Cannot access
  attribute 'Document' of deleted object“ in `gui_verfahren.Activated`.
- `tests/gui/_lauf/szenario_lauf.py` (`_ende` schließt Aufgabenfenster und
  Dokumente), `tests/gui/szenario_zoll.py`,
  `tests/gui/szenario_beispielmaschine.py` (feste 2,5 s nach „Beispielmaschine
  laden“).

### DATEIEN
- `tests/gui/_lauf/szenario_lauf.py` (`Helfer.warte_auf`)
- `tests/gui/szenario_zoll.py`, `tests/gui/szenario_beispielmaschine.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Szenarien prüfen den Dialog nach „Beispielmaschine laden“ erst, wenn er
offen ist – auch wenn das Laden länger als 2,5 s dauert.

### DONE
- Ursache: Beim Neuberechnen lässt FreeCADs Fortschrittsbalken Ereignisse
  durch; dauerte das Laden länger als die feste Wartezeit, prüfte das
  Szenario zu früh, endete, und der Lauf schloss das Dokument, während
  `lade()` noch lief – daher das gelöschte Objekt. Am Addon selbst liegt es
  nicht.
- `Helfer.warte_auf(bedingung)`: wartet in Schritten von 250 ms, höchstens
  20 s. Beide Szenarien warten auf ihr Aufgabenfenster.
- Der geparkte Stand „Beispielmaschinen zur Auswahl“ (Stash) wartet noch
  fest 3 s – beim Weitermachen ebenso umstellen.

### TEST
- `szenario_zoll`, `szenario_beispielmaschine` (1.1.3).

### NEXT
- Stufe C4: Einsätze je Art.

## P-2026-09-26-56 werkzeugbilder

### EINGELESEN
- Spezifikation Werkzeugarten, Abschnitt 4 und 8 (Stufe 3): Bilder aller
  Arten, auch klein in der Auswahl.
- Manuel (Screenshot-Rückmeldung zu C2): „die Grafik bei den
  Drehwerkzeugen ist dennoch nicht korrekt … auch der Zentrierbohrer … ist
  eher spitz ;)“.
- `camaddon/gui_werkzeugbild.py` (bisher fünf Arten fest verdrahtet).

### DATEIEN
- `camaddon/werkzeugform.py` (neu: Umriss je Art, ohne Oberfläche)
- `camaddon/gui_werkzeugbild.py` (malt die Teile, Symbol je Art)
- `camaddon/gui_werkzeuge.py` (Symbole in der Auswahl „Art“)
- `tests/test_werkzeugform.py` (neu), `tests/gui/szenario_werkzeugbilder.py`
  (neu)
- `docs/spezifikation_werkzeugarten.md`, `docs/aufbau.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Neu → Art durchblättern: Jede der 26 Arten zeigt
neben den Feldern ihre Form – der Zentrierbohrer spitz mit Senkung, das
Drehwerkzeug als Halter mit Wendeplatte, der Taster mit roter Kugel –, und
in der aufgeklappten Auswahl steht vor jedem Namen ein kleines Bild.

### DONE
- `werkzeugform.teile()`: je Art Teile (Schaft, Schneide, Kugel) als
  Vielecke in mm, mit Wendel rechts/links/gerade; gestrichelt, was
  Beispiel oder geschätzt ist. Zentrierbohrer: Zapfen mit 118°-Spitze, die
  Senkung mit dem Spitzenwinkel (60°) zum Körper-Ø; Gewindebohrer mit
  Zähnen nach der Steigung und Anschnitt, links mit Linkswendel;
  Drehwerkzeug: Hauptschneide im Einstellwinkel zur Vorschubrichtung,
  Plattenwinkel an der Spitze, links gespiegelt, neutral mittig.
- Bild: mittig eingepasst; Symbol in der Auswahl zeigt nur das schneidende
  Ende (sonst wäre ein langer Fräser ein Strich).

### TEST
- `test_werkzeugform` (26 Arten, spitz/flach, Kugel, Spiegelbild,
  Einstellwinkel, Wendel, Tastkugel, gestrichelt) in 1.1.3 und im
  Wochen-Build; `szenario_werkzeugbilder` (Übersicht aller Arten,
  Auswahl mit Bildern, Drehwerkzeug links), `szenario_werkzeugverwaltung`,
  `szenario_schnittwerte` in 1.1.3. Die Übersicht angesehen: jede Art
  erkennbar.
- `szenario_zoll` scheiterte einmal an „Maschine verfahren“: eine feste
  Wartezeit im Szenario – eigener Patch (P-2026-09-26-57).

### NEXT
- Szenarien warten auf die Beispielmaschine statt fester Zeit; dann
  Stufe C4: Einsätze je Art.

## P-2026-09-26-55 werkzeugarten-tabelle

### EINGELESEN
- Spezifikation Werkzeugarten (P-2026-09-26-53), Abschnitte 2–4 und 8
  (Stufe 2): alle 26 Arten wählbar, gegliedert, je Art ihre Felder.
- Manuel während des Bauens: „Gewindebohrer haben keine Schneidenanzahl.“
- `camaddon/werkzeuge.py`, `camaddon/gui_werkzeuge.py`,
  `camaddon/gui_werkzeugbild.py`, `camaddon/uebergabe_werkzeuge.py`.

### DATEIEN
- `camaddon/werkzeuge.py` (26 Arten, `ARTDATEN`, neue Felder, Zeile und
  Name je Art, Steigung in inch als Gänge je Zoll)
- `camaddon/gui_werkzeuge.py` (Felder je Art, Auswahl gegliedert)
- `camaddon/gui_werkzeugbild.py` (kein Bild ohne Durchmesser)
- `camaddon/uebergabe_werkzeuge.py` (Arten ohne CAM-Form bleiben draußen)
- `translations/de.json`, `translations/en.json`
- `help/de/werkzeuge.html`, `help/en/werkzeuge.html`
- `docs/spezifikation_werkzeugarten.md`
- `tests/test_werkzeuge.py`, `tests/test_uebergabe_werkzeuge.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Art aufklappen: 26 Arten unter „Fräsen“, „Bohren“,
„Drehen“, „Antasten“; „Gewindebohrer rechts“ zeigt Durchmesser und
Steigung fett, Gewindelänge, Gesamtlänge, Schaft-Ø, Schneidstoff – keine
Schneidenzahl, keinen Eckradius.

### DONE
- `ARTDATEN`: je Art Gruppe, Felder in Anzeigereihenfolge, Pflichtfelder,
  übliche Winkel, Beispiele metrisch und in runden Zollmaßen (`_zoll`).
  Neue Felder: Spitzen-Ø, Kegel-, Flanken-, Einstell-, Plattenwinkel,
  Hals-Ø und -länge, Profilradius, Steigung, Schneidenbreite, Stechtiefe,
  Ausführung. Beschriftung je Art (Zapfen-Ø, Gewindelänge, Eckenradius …).
- Dialog: alle Felder einmal angelegt, `_felder_anordnen()` stellt die der
  Art zu zweit je Reihe auf; leere Winkel zeigen grau den üblichen
  („üblich: 60“ beim Zentrierbohrer). Werte in Feldern, die die neue Art
  nicht hat, bleiben erhalten (Spezifikation, Abschnitt 4 angepasst).
- Gefunden: Hängt eine Beschriftung erst im schon gezeigten Dialog ein,
  setzt FreeCADs Stylesheet (70 KB) ihre Schrift zurück – fett jetzt nach
  dem Einhängen.
- Liste: „T4  Gewindebohrer rechts Ø 10 · P 1.5 · VHM“,
  „T9  Drehwerkzeug r 0.8 · VHM“; in inch „13 Gg/Zoll“.
- „An CAM übergeben“ lässt Arten ohne CAM-Form (noch alle neuen) draußen
  und nennt sie; die Zuordnung kommt mit Stufe 5.
- Bilder: noch die bisherigen; Drehwerkzeuge ohne Bild – Stufe 3 (Manuel:
  „die Grafik bei den Drehwerkzeugen ist nicht korrekt, auch der
  Zentrierbohrer ist eher spitz“).

### TEST
- `test_werkzeuge` (Tabelle, Zeilen, Namen, neue Felder, Gänge je Zoll),
  `test_uebergabe_werkzeuge`, `test_werkzeuge_aus_cam`,
  `test_job_schnittwerte`, `test_sprache`, `test_hilfe` in 1.1.3 und im
  Wochen-Build; Szenarien `werkzeugverwaltung` (neu: Auswahl, Gewindebohrer,
  Zentrierbohrer, Drehwerkzeug, zurück), `schnittwerte`, `zoll`, `an_cam`,
  `aus_cam`, `schruppwerte` in 1.1.3.

### NEXT
- Stufe C3: Bilder aller Arten.

## P-2026-09-26-54 kugelfraeser

### EINGELESEN
- Spezifikation Werkzeugarten (P-2026-09-26-53), Abschnitte 1, 7 und 8
  (Stufe 1): Das heutige „Radiusfräser“ ist ein Kugelfräser; ein
  Radienfräser ist eine andere Art.
- `camaddon/werkzeuge.py`, `gui_werkzeugbild.py`, `uebergabe_werkzeuge.py`,
  `werkzeuge_aus_cam.py`, Hilfe „Werkzeuge“.

### DATEIEN
- `camaddon/werkzeuge.py` (`KUGELFRAESER`, `ALTE_ARTEN`)
- `camaddon/gui_werkzeugbild.py`, `camaddon/uebergabe_werkzeuge.py`,
  `camaddon/werkzeuge_aus_cam.py`
- `translations/de.json`, `translations/en.json` (`wv.art.kugelfraeser`)
- `help/de/werkzeuge.html`, `docs/spezifikation_werkzeugverwaltung.md`
- `tests/test_werkzeuge.py`, `tests/test_werkzeuge_aus_cam.py`,
  `tests/test_schruppwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In der Auswahl „Art“ steht „Kugelfräser“ statt „Radiusfräser“; ein
gespeicherter Radiusfräser öffnet sich als Kugelfräser und wird als
`kugelfraeser` gespeichert.

### DONE
- Gespeichertes Wort `kugelfraeser`; `ALTE_ARTEN` stellt `radiusfraeser`
  beim Laden um. In CAM bleibt es die Form „ballend“, aus CAM wird
  „ballend“ ein Kugelfräser. Englisch hieß er schon „Ball end mill“.

### TEST
- `test_werkzeuge` (neu: alte Datei mit `radiusfraeser`),
  `test_werkzeuge_aus_cam`, `test_schruppwerte`, `test_uebergabe_werkzeuge`,
  `test_sprache`, `test_hilfe` in 1.1.3 und im Wochen-Build;
  `szenario_werkzeugverwaltung` (1.1.3).

### NEXT
- Stufe C2: die Arten als Tabelle im Code, alle 26 wählbar.

## P-2026-09-26-53 spezifikation-werkzeugarten

### EINGELESEN
- Manuel (2026-09-26): „ne, mach mal Werkzeugarten weiter“ – die
  Beispielmaschinen zur Auswahl warten (fast fertig, im Stash).
- Plan Punkt 10 in `docs/STATUS_SNAPSHOT.md` (26 Arten aus Manuels
  InventorCAM-Screenshot, P-2026-09-26-31), `camaddon/werkzeuge.py`,
  `gui_werkzeuge.py`, `gui_werkzeugbild.py`, `schnittdaten.py`,
  `uebergabe_werkzeuge.py`, `werkzeuge_aus_cam.py`; die Werkzeugformen von
  FreeCAD-CAM (`Path/Tool/shape/models`, in 1.1.3 und im Wochen-Build
  dieselben 15).

### DATEIEN
- `docs/spezifikation_werkzeugarten.md` (neu)
- `docs/STATUS_SNAPSHOT.md` (Punkt 10), `CHATSTART.md` (Lesekarte)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation nennt alle 26 Arten mit Maßen, CAM-Form, Einsätzen,
Beispielwerten und die Stufen, in denen sie gebaut werden.

### DONE
- Spezifikation mit neun Abschnitten; Entscheidungen zur Besprechung in
  Abschnitt 9 (u. a. Gewindebohrer rechts/links als zwei Arten, Bohrstange
  und Ausspindelwerkzeug getrennt, Nutenfräser = Scheibenfräser,
  Konikfräser mit Kugel an der Spitze, Drehwerkzeuge ohne Schnittwerte).

### TEST
- Nur Doku.

### NEXT
- Stufe C1: Kugelfräser statt „Radiusfräser“.

## P-2026-09-26-52 revolverplatz-nur-am-revolver

### EINGELESEN
- Manuel (2026-09-26, Screenshot: Beispiel-Fräsmaschine, „+ Werkzeugaufnahme“,
  im Kasten darunter „Revolverplatz: P10“): „hier ist noch kein Revolver zu
  sehen … also wieso Revolverplatz? … keine Ahnung, wie man das sinnvoll
  macht.“
- `camaddon/gui_details.py` (`zeige_aufnahme`, `_platzfeld`),
  `camaddon/gui_maschine.py` (`_details_zeigen`), Spezifikation W-001,
  Abschnitt 7a (Plätze = Werkzeugaufnahmen im Glied des Revolvers).

### DATEIEN
- `camaddon/gui_details.py`, `camaddon/gui_maschine.py`
- `help/de/aufnahmen.html`, `help/en/aufnahmen.html`
- `tests/gui/szenario_maschine_bearbeiten.py`,
  `tests/gui/szenario_beispielmaschine.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Das Feld „Revolverplatz“ steht nur bei einer Werkzeugaufnahme, deren LCS auf
einem Revolver sitzt – im Glied, das ein Gelenk mit der Betriebsart
„Revolver“ dreht. An der Spindel einer Fräse gibt es das Feld nicht mehr.

### DONE
- `MaschinenPanel._auf_revolver()` prüft das Glied des LCS gegen die
  Revolverachsen; `DetailKasten.zeige_aufnahme(…, auf_revolver)` legt das
  Feld nur dann an. Genau diese Aufnahmen zählt das Addon auch als Plätze
  (`m.plaetze`) – Feld und Zählung passen jetzt zusammen.
- Hilfe „Aufnahmen“: Das Feld gibt es nur auf dem Revolver.
- Das „P10“ im Screenshot war sehr wahrscheinlich das Mausrad über dem Feld;
  ohne Revolver ist das Feld jetzt ganz weg.

### TEST
- `szenario_maschine_bearbeiten` (1.1.3): P3 zeigt „Revolverplatz: P3“, das
  Futter hat nur Name und Koordinatensystem. `szenario_beispielmaschine`:
  Die Spindel der Beispiel-Fräse hat drei Felder, kein Revolverplatz.

### NEXT
- Beispielmaschinen zur Auswahl (Punkt 7b).

## P-2026-09-26-51 version-0-16-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.15.0: Maßsystem inch (P-2026-09-26-48), Knopf „Nach Updates suchen“
  (P-2026-09-26-50).

### DATEIEN
- `package.xml` (0.16.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.16.0.

### DONE
- Version 0.15.0 → 0.16.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann die Beispielmaschinen zur Auswahl (Punkt 7b).

## P-2026-09-26-50 update-knopf

### EINGELESEN
- Manuel (2026-09-26): „Update-Prüfung nicht bei Start … wenn das jedes
  Addon machen würde bei Start prüfen, dann würde man am Anfang bei 10
  Addons 10 Updates laden müssen … lieber ein Update-Knopf, dass man
  auswählen kann ‚ok, check nach Update‘ … und dann updaten lassen, wenn man
  auf den Knopf drückt“.
- Plan in `docs/STATUS_SNAPSHOT.md` (Punkt 7c, neu).

### DATEIEN
- `camaddon/gui_aktualisierung.py` (Befehl `BefehlUpdateSuchen`,
  `von_hand_suchen()`, Suche beim Start ab Werk aus)
- `camaddon/gui_start.py` (Befehl in der Werkzeugleiste)
- `resources/icons/update.svg` (neu)
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_update.py`
- `README.md`, `docs/aufbau.md`, `docs/STATUS_SNAPSHOT.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beim Start von FreeCAD sucht das Addon nicht mehr (ab Werk). Der Knopf
„Nach Updates suchen“ in der Werkzeugleiste sucht im Hintergrund, zeigt
in der Statusleiste „suche nach Updates …“ und sagt danach in jedem Fall,
was herauskam – bei einer neuen Version mit „Jetzt aktualisieren“. In den
Einstellungen lässt sich die Suche beim Start einschalten.

### DONE
- Knopf „Nach Updates suchen“ (Befehl `CamAddon_UpdateSuchen`, Symbol:
  Pfeil im Kreis) in der Werkzeugleiste des Addons; solange eine Suche
  läuft, ist er grau. Derselbe Weg wie „Jetzt nach Updates suchen“ in den
  Einstellungen.
- Suche beim Start ab Werk aus. Neuer Schlüssel `UpdateSucheBeimStart`:
  Unter dem alten (`UpdateBeimStart`) stand bei allen, die die Einstellungen
  einmal gespeichert haben, „an“ – sonst hätte der Wechsel sie nicht
  erreicht.
- README (beide Installationswege), Tooltip und Aufbau beschreiben den
  Knopf.

### TEST
- `scripts/oberflaeche_testen.sh tests/gui/szenario_update.py` (1.1.3):
  Befehl angemeldet; `von_hand_suchen()` findet 9.9.0 im Test-Repo, der
  Hinweis erscheint, „Jetzt aktualisieren“ holt sie; „Beim Start suchen“
  ab Werk aus, an und aus wird gespeichert. `szenario_erster_start`,
  `test_sprache`, `test_aktualisierung`, `test_hilfe` grün. Voller Lauf mit
  dem Versionssprung.

### NEXT
- Version 0.16.0, voller Lauf, Push; dann die Beispielmaschinen zur
  Auswahl (Punkt 7b).

## P-2026-09-26-49 plan-beispielmaschinen-und-update

### EINGELESEN
- Manuel (2026-09-26, nach dem Laden der Beispielmaschine): „ich hätte
  gerne, wenn ich Beispielmaschine laden [drücke,] eine Auswahl von
  Drehbank CLX-mäßig mit Y-Achse, Schrägbett und am Revolver zwei
  Werkzeuge zum Fräsen, eins in Z-Richtung bearbeitend, eins 90 Grad zur
  Z-Richtung … 3-Achs-Fräse, 5-Achs-Fräse Tisch/Tisch (Achsen A/B),
  5-Achs-Fräse Kopf/Kopf auch A/B und … Kopf/Tisch … die üblichen Sorten“.
- Manuel: „Update-Prüfung nicht bei Start … wenn das jedes Addon machen
  würde … bei 10 Addons 10 Updates laden … lieber ein Update-Knopf, dass man
  auswählen kann ‚ok, check nach Update‘ … und dann updaten lassen, wenn man
  auf den Knopf drückt“.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan: Punkt 7b)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Plan nennt die Auswahl der Beispielmaschinen mit Ort in der
Reihenfolge; der Update-Knopf folgt als eigener Patch.

### DONE
- Punkt 7b: Beispielmaschinen zur Auswahl (Schrägbett-Drehmaschine mit
  Y-Achse und zwei angetriebenen Werkzeugen, 3-Achs, 5-Achs Tisch/Tisch
  A/C, Kopf/Kopf A/B, Kopf/Tisch B/C). Achsnamen wie üblich – der Rundtisch
  auf der Wiege heißt fast immer C; umbenennen geht in „Maschine
  bearbeiten“.

### TEST
- Nur Doku.

### NEXT
- Update-Knopf statt Suche beim Start; dann die Beispielmaschinen.

## P-2026-09-26-48 masssystem-inch

### EINGELESEN
- Manuel (2026-09-26): „es sollte bei Installation auswählbar sein …
  welche Einheiten verwendet werden (Standard metrisch, aber inch und so
  sollten möglich sein) … mit Beispielzahlen … und auch in den
  Einstellungen des Addons wieder ändern … bei den Werkzeugen direkt in
  inch bzw. mm umrechnen … und einen Schalter einbauen, wo man zwischen
  inch und mm switcht“.
- Plan im Snapshot (Stufe B, Punkte 8 und 9); alle Dialoge mit Zahlen;
  60 Texte mit festen Einheiten; FreeCADs Einheitensysteme
  (`FreeCAD.Units.listSchemas()`: Imperial, ImperialDecimal,
  ImperialBuilding, ImperialCivil = inch).

### DATEIEN
- `camaddon/einheiten.py` (Maßsystem, Größen mit Umrechnung und Stellen,
  `runden`/`abrunden`, Vergleichsvolumen, Einheiten-Platzhalter)
- `camaddon/sprache.py` (`tr()` setzt `{e_laenge}` … selbst ein)
- `camaddon/gui_zahlen.py` (`groesse_zeigen`, `groesse_lesen`,
  `groesse_fest`), `camaddon/gui_teile.py` (`mit_einheit` merkt die
  Einheit)
- `camaddon/gui_sprachwahl.py` (Maßsystem beim ersten Start und in den
  Einstellungen, mit Beispielen)
- `camaddon/gui_werkzeuge.py` (Umschalter mm/inch, Felder, Platzhalter,
  Hinweise), `camaddon/werkzeuge.py` (Listenzeile, Beispielname,
  Beispielwerte in Zoll, Vorlage), `camaddon/gui_werkzeugbild.py`
- `camaddon/gui_schnittwerte.py` (Tabelle, Köpfe, Eingriff, Ausgleich)
- `camaddon/schruppwerte.py`, `camaddon/gui_schruppwerte.py` (Planer,
  Beispiele in Zoll, Übernehmen gerundet in der gezeigten Einheit)
- `camaddon/schnittdaten.py`, `camaddon/gui_strategie.py`
  (Strategievergleich, „Zeit für 5 in³“)
- `camaddon/gui_job_schnittwerte.py`, `camaddon/gui_details.py`,
  `camaddon/gui_verfahren.py`, `camaddon/export.py`
- `translations/de.json`, `translations/en.json` (Einheiten als
  Platzhalter; neue Texte `zahlen.metrisch|zoll`,
  `einstellungen.zahlen.masssystem`, `wv.masssystem.tooltip`,
  `einheit.je_umdrehung`)
- `help/de|en/werkzeuge.html`, `help/de|en/schnittwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 28),
  `docs/aufbau.md`, `docs/STATUS_SNAPSHOT.md`
- `tests/test_einheiten.py`, `tests/test_werkzeuge.py`,
  `tests/test_schruppwerte.py`, `tests/gui/szenario_zoll.py` (neu)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → rechts neben „Werkstoffe…“ „inch“ wählen: Die Felder
zeigen „in“, der Ø-12-Fräser „0.4724“; „Neu“ → Ø 0.5, Schneide 1, Liste
„Ø 0.5“. Schnittwerte: Köpfe ae/ap in, vc SFM, fz in, vf ipm, Q in³/min;
„400“ in vc und „0.002“ in fz → n und vf in ipm. „Schruppwerte planen…“ →
vc in SFM, Vorschlag in ipm. Zurück auf „mm“ → alles wieder in mm, ½" als
12.7. Bearbeiten → Einstellungen → CAM-Addon → Zahlen: „Maßsystem“ ändert
es ebenso.

### DONE
- Maßsystem wählbar (erster Start, Einstellungen, Umschalter in der
  Werkzeugverwaltung), vorbelegt aus FreeCAD; wer den Dialog schon
  beantwortet hat, wird nicht noch einmal gefragt.
- Überall umgerechnet: Werkzeugverwaltung, Schnittwerte, Eingriff,
  Planer, Strategievergleich, „Schnittwerte in den Job“, Maschine
  (Eilgang, Höchstvorschub, Verfahren, Bericht der Übergabe).
- Gespeichert und an CAM übergeben wird metrisch; gerundet in der
  gezeigten Einheit, damit ½" 0.5 in bleibt.

### TEST
- Alle Prüfungen ohne Oberfläche in 1.1.3 und 26.3.0 grün (neu:
  Maßsystem, Umrechnung, Runden, Texte in Zoll, Listenzeile und
  Beispielwerte in Zoll). `szenario_zoll` in 1.1.3 grün, Screenshots
  angesehen (Werkzeugverwaltung und Planer in Zoll, zurück auf mm,
  Verfahren in inch). Alle Szenarien in 1.1.3; voller Lauf vor dem Push.

### NEXT
- Version 0.16.0, voller Lauf, Push; dann Stufe C (Spezifikation der
  Werkzeugarten zuerst).

## P-2026-09-26-47 tausenderpunkt

### EINGELESEN
- Voller Lauf vor dem Push von 0.15.0: `szenario_felder` rot in beiden
  Versionen – „35.000“ getippt ergab 35 statt 35000. Seit
  P-2026-09-26-45 nehmen die Felder Punkt und Komma als Dezimalzeichen;
  B-004 (P-2026-09-25-31): Auf Deutsch ist „35.000“ fünfunddreißigtausend.
- Im selben Lauf `szenario_erster_start` rot in 1.1.3 („user.cfg“ fehlt):
  FreeCAD meldete schon beim Start „Failed to access file for writing“ –
  genau in den zwei Minuten, in denen nebenher eigene FreeCAD-Versuche
  liefen; einzeln und im nächsten Lauf grün. Künftig keine FreeCAD-Versuche
  neben einem vollen Lauf.

### DATEIEN
- `camaddon/einheiten.py` (`zahl_aus_text` mit dem eingestellten
  Dezimalzeichen)
- `camaddon/gui_zahlen.py` (`zahl_lesen` gibt es mit)
- `tests/test_einheiten.py`, `tests/gui/szenario_felder.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Mit Komma als Dezimalzeichen: „35.000“ im Eilgang ergibt 35000, „2.5“ in
der Beschleunigung 2,5, „0.125“ ergibt 0,125. Mit Punkt: „1,500“ ergibt
1500, „12,5“ ergibt 12,5.

### DONE
- Das eingestellte Dezimalzeichen trennt immer die Nachkommastellen; das
  andere auch – außer die Zahl ist mit Tausendertrennzeichen geschrieben
  (1 bis 3 Ziffern, nicht 0, dann Gruppen zu drei).

### TEST
- `test_einheiten.py` in 1.1.3 und 26.3.0 grün; `szenario_felder`,
  `szenario_erster_start` in 1.1.3 grün. Voller Lauf vor dem Push.

### NEXT
- Push 0.15.0; dann B2 (Maßsystem inch).

## P-2026-09-26-46 version-0-15-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.14.0: Dezimalzeichen wählbar, Eingabe mit Punkt oder Komma
  (P-2026-09-26-45).

### DATEIEN
- `package.xml` (0.15.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.15.0.

### DONE
- Version 0.14.0 → 0.15.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann B2 (Maßsystem inch).

## P-2026-09-26-45 dezimalzeichen

### EINGELESEN
- Manuel (2026-09-26): „die meisten CAM-Programme oder Maschinen arbeiten
  eher mit . … wie ist das in FreeCAD selbst gelöst? … oder auswählbar“;
  später: „es sollte bei Installation auswählbar sein … welche Trennzeichen
  genutzt werden … mit Beispielzahlen … und auch in den Einstellungen des
  Addons wieder ändern kann“.
- Plan im Snapshot (Stufe B, Punkte 8 und 9), `camaddon/gui_zahlen.py`
  (B-004: ohne Tausenderpunkte), `camaddon/gui_sprachwahl.py`.
- FreeCAD 1.1.3 im frischen Profil: Wer schon beim Laden der Oberfläche
  einen Parameter setzt, verhindert, dass `FreeCAD.saveParameter()` die
  `user.cfg` anlegt – deshalb wählen die Szenarien das Komma im Dialog,
  statt es im Testgerüst vorzugeben.

### DATEIEN
- `camaddon/einheiten.py` (neu: gewähltes Dezimalzeichen, `zahl_aus_text`
  mit Punkt oder Komma)
- `camaddon/gui_zahlen.py` (Zahlenformat nach der Wahl, sonst FreeCADs;
  Prüfer nimmt Punkt und Komma; `dezimalzeichen()`)
- `camaddon/gui_sprachwahl.py` (Dialog beim ersten Start und
  Einstellungsseite: Dezimalzeichen mit Beispielzahlen; wer die Sprache
  schon gewählt hat, wird einmal nach dem Dezimalzeichen gefragt)
- `translations/de.json`, `translations/en.json` (`zahlen.*`,
  `einstellungen.zahlen.*`, Titel „Sprache und Zahlen“)
- `help/de|en/werkzeuge.html` (Zahlen mit Punkt oder Komma)
- `docs/aufbau.md`, `docs/STATUS_SNAPSHOT.md`
- `tests/test_einheiten.py` (neu), `tests/gui/szenario_erster_start.py`,
  `tests/gui/szenario_werkzeugverwaltung.py` (Eckradius mit Punkt
  getippt), alle Szenarien mit Sprachwahl (wählen das Komma)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update fragt das Addon beim nächsten Start einmal „Und welches
Dezimalzeichen sollen die Zahlen haben?“ – vorgewählt ist das von FreeCAD
(bei Manuel das Komma), zur Wahl „Komma: 12,5 mm · fz 0,05 mm“ und „Punkt:
12.5 mm · fz 0.05 mm“. Mit „Punkt“ zeigt die Werkzeugverwaltung „Ø 10.5“
und „0.05“. In jedem Zahlenfeld darf man „10,5“ oder „10.5“ tippen.
Bearbeiten → Einstellungen → CAM-Addon → „Zahlen“ ändert es wieder.

### DONE
- Dezimalzeichen wählbar beim ersten Start und in den Einstellungen,
  vorbelegt aus FreeCADs Zahlenformat; ohne Wahl gilt FreeCADs.
- Eingaben nehmen immer Punkt und Komma; weiterhin keine
  Tausendertrennzeichen und keine Zahlen unter 0 in den Feldern.
- Wer die Sprache schon gewählt hat (Manuel), sieht den Dialog noch
  einmal – mit seiner Sprache vorgewählt.

### TEST
- `test_einheiten.py`, `test_sprache.py`, `test_hilfe.py` in 1.1.3 und
  26.3.0 grün; `szenario_erster_start` (Titel, Beispielzahlen,
  `user.cfg`, Einstellungsseite: Punkt und Komma),
  `szenario_werkzeugverwaltung` (Eckradius „0.5“ bei Komma),
  `szenario_schnittwerte` in 1.1.3 grün, Screenshots angesehen. Voller
  Lauf vor dem Push.

### NEXT
- B2: Maßsystem inch mit Umrechnung überall.

## P-2026-09-26-44 version-0-14-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.13.0: Warngrenze im Planer (P-2026-09-26-40), Eingriffsbild
  beschriftet (-41), ae/ap in mm oder % von D (-42), Spitzenwinkel des
  Bohrers (-43). Stufe A des Plans ist damit fertig.

### DATEIEN
- `package.xml` (0.14.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.14.0.

### DONE
- Version 0.13.0 → 0.14.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann Stufe B (Maßsystem und Dezimaltrennzeichen).

## P-2026-09-26-43 bohrer-spitzenwinkel

### EINGELESEN
- Manuel (2026-09-26, Screenshot eines Bohrers in der
  Werkzeugverwaltung): „bei einem Bohrer gibt's … was es gibt, ist ein
  Spitzenwinkel, der ist vergessen worden“; ob es eine Schneidenzahl
  gibt, wusste er nicht – Plan: sie bleibt (f je Umdrehung).
- Plan im Snapshot (Stufe A Punkt 6); bisher fest 118° in
  `uebergabe_werkzeuge.py` (TipAngle) und `gui_werkzeugbild.py`.

### DATEIEN
- `camaddon/werkzeuge.py` (`Werkzeug.spitzenwinkel`, gespeichert;
  `SPITZENWINKEL_BOHRER`, `spitzenwinkel_fuer_cam`)
- `camaddon/gui_werkzeuge.py` (Feld nur beim Bohrer, an der Stelle des
  Eintauchwinkels; grau „üblich: 118“)
- `camaddon/gui_werkzeugbild.py` (Spitze mit dem Winkel des Werkzeugs)
- `camaddon/uebergabe_werkzeuge.py` (TipAngle aus dem Werkzeug)
- `camaddon/werkzeuge_aus_cam.py` (TipAngle wird gelesen)
- `translations/de.json`, `translations/en.json` (`wv.spitzenwinkel*`)
- `help/de|en/werkzeuge.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 27)
- `docs/STATUS_SNAPSHOT.md` (Punkt 6 fertig, Stufe A komplett)
- `tests/test_werkzeuge.py`, `tests/test_uebergabe_werkzeuge.py`,
  `tests/test_werkzeuge_aus_cam.py`, `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Neu“ → Art „Bohrer“: Statt „Eintauchwinkel“ steht
„Spitzenwinkel“, leer grau „üblich: 118“. „130“ eintragen → die Spitze im
Bild wird stumpfer. „Speichern und an CAM übergeben“ → im CAM-Werkzeug
steht der Spitzenwinkel 130°.

### DONE
- Spitzenwinkel je Bohrer (0 = üblich 118°), gespeichert, begrenzt auf
  0 … 180°; ins Bild, als TipAngle an CAM, aus CAM gelesen.
- Das Feld teilt sich die Stelle mit dem Eintauchwinkel – je nach Art ist
  eins von beiden zu sehen, ohne Lücke.

### TEST
- `test_werkzeuge.py`, `test_uebergabe_werkzeuge.py` (TipAngle 130°),
  `test_werkzeuge_aus_cam.py` (Winkel des Beispielbohrers gelesen),
  `test_sprache.py` in 1.1.3 und 26.3.0 grün; `test_hilfe.py` grün;
  `szenario_schnittwerte`, `szenario_werkzeugverwaltung` in 1.1.3 grün,
  Screenshot angesehen. Voller Lauf vor dem Push.

### NEXT
- Version 0.14.0 (A3–A6), voller Lauf, Push; dann Stufe B.

## P-2026-09-26-42 zustellung-in-prozent

### EINGELESEN
- Manuel (2026-09-26, Screenshot der Schnittwerte): „ich hätte hier gerne
  einen Switch zwischen %-Angabe und mm-Angabe … dass man beides
  eintragen kann“. Plan: ein Umschalter über der Tabelle, intern mm, Wahl
  gemerkt (Stufe A Punkt 5).
- `camaddon/gui_schnittwerte.py` (Tabelle, Kopf, Eingabe).

### DATEIEN
- `camaddon/gui_schnittwerte.py` (Auswahl „ae, ap in mm / in % von D“,
  Köpfe, Anzeige, Eingabe in % → mm, gemerkt als
  `SchnittwerteInProzent`)
- `translations/de.json`, `translations/en.json` (`wv.zustellung.*`)
- `help/de|en/schnittwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 26)
- `docs/STATUS_SNAPSHOT.md` (Punkt 5 fertig)
- `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Ø-12-Fräser mit „Schruppen dynamisch“ ae 1,2 / ap 25
→ rechts über der Tabelle „ae, ap in % von D“ wählen → die Köpfe heißen
„ae % D“ und „ap % D“, die Zeile zeigt 10 und 208,3. „20“ ins ae tippen →
darunter „ae 2,4 mm = 20 % von D“. Zurück auf „ae, ap in mm“ → 2,4. Beim
nächsten Öffnen steht die zuletzt gewählte Einheit.

### DONE
- Eine Auswahl für beide Spalten; Prozent mit einer Nachkommastelle;
  gespeichert immer in mm; ohne Durchmesser mm (Auswahl gesperrt), beim
  Bohrer ausgeblendet.
- Nebenbei: Eine unlesbare Eingabe im f-Feld des Bohrers teilte den alten
  Wert noch einmal durch die Schneidenzahl – jetzt bleibt er, wie er war.

### TEST
- `szenario_schnittwerte` in 1.1.3 grün, Screenshot angesehen (Köpfe
  „% D“, 100/25 und 20/208,3); `test_sprache.py`, `test_hilfe.py` grün.
  Voller Lauf mit dem nächsten Push.

### NEXT
- A6: Spitzenwinkel des Bohrers.

## P-2026-09-26-41 eingriffsbild-beschriftet

### EINGELESEN
- Manuel (2026-09-26, Screenshot des Eingriffsbilds unter den
  Schnittwerten): „das Bild find ich gut … allerdings weiß keiner, was ae
  und ap ist … schreib's doch drüber, und der Text ist ziemlich lang, den
  sollte man vll auf zwei Zeilen setzen oder sowas wie Links: ae … Rechts:
  ap …“.
- Plan im Snapshot (Stufe A Punkt 4), `camaddon/gui_eingriff.py` (Bild ohne
  Text, Arbeitsregeln Abschnitt 8), `camaddon/gui_schnittwerte.py`.

### DATEIEN
- `camaddon/gui_schnittwerte.py` (Überschriften über den Bildhälften,
  je Größe eine Zeile)
- `translations/de.json`, `translations/en.json` (neu
  `wv.eingriff.titel.ae|ap`, `wv.eingriff.von_oben|von_der_seite`,
  `wv.eingriff.ae`, `wv.eingriff.ap`, `wv.eingriff.ap_schneide`; entfallen
  `wv.eingriff.ae_ap`, `wv.eingriff.ae_ap_schneide`)
- `help/de|en/schnittwerte.html`
- `docs/STATUS_SNAPSHOT.md` (Punkt 4 fertig)
- `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Fräser → Zeile „Schruppen dynamisch“ wählen: Über der
linken Bildhälfte steht „ae – seitliche Zustellung“, darunter grau „von
oben“; über der rechten „ap – Zustelltiefe“, grau „von der Seite“. Rechts
daneben je eine Zeile „ae 1,2 mm = 10 % von D“, „ap 25 mm = 2,1 × D (96 %
der Schneide)“, dann Eingriff und Spandicke.

### DONE
- Überschriften als Beschriftungen über dem Bild – das Bild selbst bleibt
  ohne Text. Die Ansicht („von oben“, „von der Seite“) grau in einer
  eigenen Zeile, damit sie nicht mitten in der Klammer umbricht.
- Die Werte: erst ae, dann ap, dann der Eingriffswinkel, dann die
  Spandicke – je eine Zeile.

### TEST
- `szenario_schnittwerte` in 1.1.3 grün, Screenshot angesehen;
  `test_sprache.py`, `test_hilfe.py` grün. Voller Lauf mit dem nächsten
  Push.

### NEXT
- A5: ae und ap wahlweise in mm oder % von D.

## P-2026-09-26-40 planer-warngrenze

### EINGELESEN
- Manuel (2026-09-26, Screenshot des Planers): „wer sagt was von 10 % ??
  … sagen ‚hey das sind mehr als deine Warngrenze‘ … welche man irgendwo
  mit eintragen kann“; dann: „ab 10 % ae bei voller Schneidenlänge rote
  Warnung, somit können wir die 10 % lassen, aber auswählbar sollte es
  schon sein“; „10 % ae bei HSM ist ok, egal wie viel Schneiden“.
- Plan im Snapshot (Stufe A Punkt 3), Spezifikation W-002 (Entscheidung
  14), `camaddon/schruppwerte.py`, `camaddon/gui_schruppwerte.py`.

### DATEIEN
- `camaddon/werkzeuge.py` (`Werkzeug.ae_warngrenze`, gespeichert; ältere
  Dateien: 10 %)
- `camaddon/schruppwerte.py` (`AE_GRENZE` = Vorgabe am Werkzeug)
- `camaddon/gui_schruppwerte.py` (Feld aus dem Werkzeug und zurück, Zeilen
  darüber rot, roter Satz unter der Tabelle; nicht mehr in den
  Einstellungen gemerkt)
- `translations/de.json`, `translations/en.json` (`sp.ae_grenze*`,
  `sp.hinweis.ueber_ae`, `sp.grund.ae`, neu `sp.warnung.ueber_ae`)
- `help/de|en/schruppwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 14, Stufe 3)
- `docs/STATUS_SNAPSHOT.md` (Punkt 3 fertig)
- `tests/test_werkzeuge.py`, `tests/gui/szenario_schruppwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Ø-12-Fräser → „Schruppwerte planen…“: Das Feld
heißt „Warngrenze ae“ (10 % von D). Die Zeilen über 10 % sind rot mit
„mehr als deine Warngrenze (10 % von D)“; eine anklicken → darunter ein
roter Satz, „Als Einsatz übernehmen“ bleibt bedienbar. Warngrenze auf 8
ändern, Planer schließen, OK → beim nächsten Öffnen steht bei diesem
Werkzeug 8, bei anderen 10.

### DONE
- Warngrenze je Werkzeug (Vorgabe 10 %, 0 = keine), gespeichert in der
  Werkzeugdatei; der Planer liest und schreibt sie (auch nach Abbrechen,
  wie die Maschinenwerte).
- Zeilen über der Warngrenze rot und wählbar; über der Spindelleistung
  weiter grau. Der Vorschlag bleibt unter der Warngrenze; der Satz dazu
  sagt, dass die roten Zeilen wählbar sind. Die Spalte „ae % D“ gab es
  schon.

### TEST
- `test_werkzeuge.py` (Vorgabe, Speichern, alte Datei, 0 und Begrenzung),
  `test_schruppwerte.py`, `test_sprache.py`, `test_hilfe.py` in 1.1.3
  grün; `szenario_schruppwerte` in 1.1.3 grün, Screenshot angesehen (rote
  Zeile gewählt, roter Satz). Voller Lauf mit dem nächsten Push.

### NEXT
- A4 Eingriffsbild beschriften.

## P-2026-09-26-39 version-0-13-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.12.0: Beispielwerte für neue Werkzeuge und im Planer
  (P-2026-09-26-37), Beispielmaschine (-38).

### DATEIEN
- `package.xml` (0.13.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.13.0.

### DONE
- Version 0.12.0 → 0.13.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann A3 Warngrenze.

## P-2026-09-26-38 beispielmaschine

### EINGELESEN
- Manuel (2026-09-26, Screenshots der Meldung „Hier gibt es noch keine
  Baugruppe“ in „Maschine bearbeiten“ und „Maschine verfahren“): „noch
  einen Knopf ‚Beispiel Maschine laden‘ … wenn er dafür ne Maschine bauen
  muss ist das eine große Hürde … gib dem Benutzer Beispiele wo er sehen
  kann ‚ah so geht das‘“.
- `tests/beispielmaschinen.py` (Baukasten), `camaddon/gui_maschine.py`,
  `camaddon/gui_verfahren.py`, `camaddon/maschine.py`,
  `camaddon/verfahren.py`; FreeCADs `JointObject.py` (1.1.3): Jede
  Änderung an Offset1/Offset2 löst vorab (`preSolve`/`matchJCS`) und
  verschiebt dabei Teile.

### DATEIEN
- `camaddon/beispielmaschine.py` (neu: Baukasten aus den Prüfungen,
  `gelenk_wie_gebaut`, `fraesmaschine`, `lade`)
- `camaddon/gui_maschine.py` (`beispiel_gewuenscht`: Meldung mit Knopf)
- `camaddon/gui_verfahren.py`
- `translations/de.json`, `translations/en.json` (`beispiel.*`,
  `dialog.beispielmaschine*`, Meldung ergänzt)
- `help/de|en/achsen.html`, `help/de|en/verfahren.html`
- `docs/spezifikation_maschine_aus_baugruppe.md` (Entschieden)
- `docs/STATUS_SNAPSHOT.md` (Punkt 7 fertig)
- `tests/beispielmaschinen.py` (Baukasten aus dem Addon),
  `tests/test_beispielmaschine.py` (neu),
  `tests/gui/szenario_beispielmaschine.py` (neu)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
FreeCAD ohne offenes Dokument → CAM → „Maschine bearbeiten“: Die Meldung
hat den Knopf „Beispielmaschine laden“ → Klick → neues Dokument
„Beispielmaschine“ mit Bett, Ständer, Kreuztisch, blauem Fräskopf und
Spindel; der Dialog zeigt Y1, Z1, X1, S1 und die Aufnahmen „Tisch“ und
„Spindel“ mit Haken. Dasselbe über „Maschine verfahren“: X1 auf 200 → der
Tisch fährt nach rechts; Z1 auf −80 → der Kopf senkt sich.

### DONE
- Dreiachs-Fräsmaschine: X ±250, Y −150 … 120, Z −100 … 250 mm; Eilgang
  20/20/15 m/min, Vorschub 10 m/min, S1 12 000 U/min; Werkzeugaufnahme an
  der Spindelnase (angetrieben von S1), Werkstückaufnahme mitten auf dem
  Tisch. Farben: Guss dunkel, Schlitten hell, Kopf blau.
- `gelenk_wie_gebaut`: Nach dem Anlegen und nach dem Setzen der Versätze
  kommen die Teile zurück – mit Oberfläche klappte FreeCADs Vorab-Lösen den
  Fräskopf sonst hinter den Ständer (Screenshot); beide Seiten liegen jetzt
  genau aufeinander.
- Baukasten mit Ansichten für Gelenke und Fixierung, wenn es eine
  Oberfläche gibt; die Beispielmaschinen der Prüfungen bleiben, wie sie
  waren.

### TEST
- `test_beispielmaschine.py` in 1.1.3 und 26.3.0 grün (nichts verschoben,
  keine Warnung, Achsen in Achsrichtung, Grenzen, Aufnahmen, Grenzen für
  den Planer); `test_kette`, `test_verfahren`, `test_maschine`,
  `test_schruppwerte`, `test_hilfe`, `test_sprache` grün.
- `szenario_beispielmaschine` in 1.1.3 grün, Screenshots angesehen
  (Meldung mit Knopf, Maschine mit Dialog, verfahren X 200 / Y −100 /
  Z −80); `szenario_felder`, `_hilfe`, `_maschine_bearbeiten`,
  `_uebergeben`, `_verfahren`, `_zeigen` grün. Voller Lauf vor dem Push.

### NEXT
- Version 0.13.0, voller Lauf, Push; dann A3 Warngrenze.

## P-2026-09-26-37 neues-werkzeug-beispielwerte

### EINGELESEN
- Manuel (2026-09-26): Ein neues Werkzeug soll gleich Beispielwerte haben,
  damit das Bild die Form zeigt („ahh ja ok das ist der Schaftfräser“);
  beim Durchblättern immer ein Bild. „Beispielwerte in grau, aber dennoch
  aktiv … das Beispiel sollte 12 sein beim Durchmesser“. Im Planer: „die
  Spandicke … schreib bitte auch hier Beispiele rein und bei vc auch“.
- `docs/STATUS_SNAPSHOT.md` (Plan, Stufe A Punkt 2), Spezifikation W-002.

### DATEIEN
- `camaddon/werkzeuge.py` (`BEISPIELE`, `beispielwerte_setzen`, Merker
  `Werkzeug.beispiel`, `neues_werkzeug` mit Beispielen)
- `camaddon/gui_werkzeuge.py` (graue Felder, Satz „Grau: Beispielwerte …“,
  Eingabe macht eigen, Wechsel der Art, Durchmesser markiert)
- `camaddon/gui_werkzeugbild.py` (`mit_beispielmassen`: Form auch ohne
  Durchmesser, Beispiele gestrichelt)
- `camaddon/schruppwerte.py` (`BEISPIEL_SCHNITT`, `beispiel_schnitt`)
- `camaddon/gui_schruppwerte.py` (vc und Spandicke grau, wenn die Zeile
  keine hat)
- `translations/de.json`, `translations/en.json` (`wv.beispiel`,
  `sp.beispiel`)
- `help/de|en/werkzeuge.html`, `help/de|en/schruppwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 25)
- `docs/STATUS_SNAPSHOT.md` (Punkte 1 und 2 fertig)
- `tests/test_werkzeuge.py`, `tests/test_schruppwerte.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`,
  `tests/gui/szenario_schruppwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
CAM → Werkzeugverwaltung → „Neu“: Ø 12, 3 Schneiden, Schneidenlänge 26
stehen grau da, darunter „Grau: Beispielwerte – sie gelten, bis du eigene
einträgst.“, rechts das Bild eines Schaftfräsers (gestrichelt). „10“ tippen
→ der Durchmesser ist schwarz. Art „Torusfräser“ → Schneiden 4 und
Eckradius 1 grau. Durchmesser leeren → roter Hinweis, das Bild zeigt
trotzdem die Form. „Schruppwerte planen…“ bei einer Zeile ohne vc und fz →
vc 120 und Spandicke 0,05 grau (HSS: 30 und 0,03), der Plan rechnet damit.

### DONE
- Beispielwerte je Art (alle mit Ø 12): Schaftfräser z 3, L 26; Torus z 4,
  L 26, R 1; Radius z 2, L 24; Fasen z 2, L 6; Bohrer z 2, L 60. Sie
  gelten wie eingetragene; nur der Merker, dass sie Beispiel sind, wird
  nicht gespeichert.
- Wechsel der Art: graue und leere Felder bekommen die Beispiele der neuen
  Art; eigene Werte bleiben. Kopien haben keine Beispiel-Merker.
- Bild: Beispielmaße gestrichelt; ohne Durchmesser die Form der Art mit
  ihren Beispielmaßen.
- Planer: ohne vc bzw. Spandicke aus der Zeile graue Beispiele für Stahl,
  mit Satz; Tippen macht das Feld eigen.

### TEST
- `test_werkzeuge.py`, `test_schruppwerte.py`, `test_sprache.py`,
  `test_hilfe.py` in 1.1.3 grün; `szenario_werkzeugverwaltung` und
  `szenario_schruppwerte` in 1.1.3 grün, Screenshots angesehen (graue
  Werte, Bild ohne Durchmesser, Planer mit HSS-Beispielen). Voller Lauf mit
  dem nächsten Push.

### NEXT
- Beispielmaschine laden (Plan Punkt 7), dann A3 Warngrenze.

## P-2026-09-26-36 test-uebergabe-deutsch

### EINGELESEN
- Voller Lauf vor dem Push von 0.12.0: `test_uebergabe_werkzeuge.py` rot
  in 1.1.3 – „Beispielname in CAM: 'End mill T3 Carbide D12 L26'“. Seit
  P-2026-09-26-27 gilt ohne gespeicherte Wahl FreeCADs Sprache;
  `freecadcmd` 1.1.3 meldet Englisch, der Wochen-Build nicht. Die Prüfung
  aus P-2026-09-26-33 setzte keine Sprache.

### DATEIEN
- `tests/test_uebergabe_werkzeuge.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Prüfung ist in beiden Versionen grün, unabhängig von FreeCADs Sprache.

### DONE
- Die Prüfung setzt Deutsch wie `test_werkzeuge.py` und stellt danach die
  vorige Wahl wieder her.

### TEST
- `test_uebergabe_werkzeuge.py` einzeln in 1.1.3 und 26.3.0 grün; dann
  `scripts/alle_tests.sh`.

### NEXT
- Push 0.12.0.

## P-2026-09-26-35 version-0-12-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Seit
  0.11.2: Plan-Antworten (P-2026-09-26-32), Werkzeugname (-33), Plan
  Beispielmaschine (-34).
- Manuel (2026-09-26): „kannst du das mal puschen soweit und dann es bauen
  anfangen“.

### DATEIEN
- `package.xml` (0.12.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.12.0.

### DONE
- Version 0.11.2 → 0.12.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann A2 (Beispielwerte) fertig, danach die Beispielmaschine.

## P-2026-09-26-34 plan-beispielmaschine

### EINGELESEN
- Manuel (2026-09-26): „Maschine bearbeiten“ und „Maschine verfahren“
  melden ohne Baugruppe nur, dass man erst eine bauen soll – wer das Addon
  ausprobieren will, scheitert daran. Wunsch: ein Knopf
  „Beispielmaschine laden“, damit man sieht, wie es geht.
- `tests/beispielmaschinen.py`: Baukasten für Beispielmaschinen
  (Drehmaschine, Fünfachser) – bisher nur für die Prüfungen.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan: Punkt 7, Nummern von B und C folgen)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Plan im Snapshot nennt die Beispielmaschine mit Ort in der
Reihenfolge (nach A2, vor A3).

### DONE
- Punkt 7 „Beispielmaschine laden“ im Plan; Stufe B jetzt 8–9, C 10
  (vorher doppelte 6).

### TEST
- Nur Doku.

### NEXT
- Version 0.12.0 (Werkzeugname), Lauf, Push; dann A2 fertig, danach die
  Beispielmaschine.

## P-2026-09-26-33 werkzeugname

### EINGELESEN
- Manuel: Moderne Steuerungen rufen Werkzeuge über Namen auf
  (T="Fräser VHM 12"); Option A – Nummer und Name. Leerzeichen nicht
  ersetzen, der Bediener schreibt, was die Maschine will. Beispielname aus
  den Angaben: „Schaftfräser T1 VHM D12 L30“.
- FreeCADs Postprozessoren rufen per Nummer; der Heidenhain-Post schreibt
  den Namen des Werkzeug-Controllers als Kommentar hinter TOOL CALL.

### DATEIEN
- `camaddon/werkzeuge.py` (Feld `name`, `beispielname()`, `anzeigename()`,
  Listenzeile mit Namen, Suche, `Bibliothek.mit_name()`)
- `camaddon/gui_werkzeuge.py` (Feld „Name“ unter Nummer/Art, grau der
  Beispielname, Hinweis bei doppeltem Namen)
- `camaddon/uebergabe_werkzeuge.py` (ToolBit heißt `anzeigename()`)
- `camaddon/job_schnittwerte.py` (Controller „T3 <Name> – <Einsatz>“)
- `camaddon/werkzeuge_aus_cam.py` (Name aus CAM wird der Name, nicht mehr
  die Bezeichnung; „schon da“ erkennt beide)
- `translations/de.json`, `translations/en.json`, `help/de|en/werkzeuge.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 5, Nr. 24)
- `tests/test_werkzeuge.py`, `tests/test_uebergabe_werkzeuge.py`,
  `tests/test_werkzeuge_aus_cam.py`, `tests/test_job_schnittwerte.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Neu → Ø 12, Schneidenlänge 26 → das Feld „Name“ zeigt
grau „… Schaftfräser T1 VHM D12 L26“ → „Fräser VHM 12“ eintragen → die Liste
zeigt „T1  Fräser VHM 12 · Schaftfräser Ø 12 · z 3 · VHM“ → „Speichern und
an CAM übergeben“ → in CAM heißt das Werkzeug „Fräser VHM 12“; „Werkzeug-
Controller hinzufügen“ legt „T1 Fräser VHM 12 – …“ an.

### DONE
- Name mit Beispielname, Liste, Suche, Hinweis, CAM, Controller, Import.

### TEST
- Unit-Tests (beide Versionen): Beispielname mit Punkt, Zeile und Suche mit
  Namen, gleicher Name (groß/klein), Speichern/Laden, alte Datei; ToolBit
  heißt wie eingetragen bzw. nach dem Beispielnamen; Import füllt den
  Namen; Controller-Name mit Werkzeugname, Einsatz wird trotzdem erkannt.
- `szenario_werkzeugverwaltung` (beide Versionen): grauer Beispielname,
  Name tippen, Listenzeile, doppelter Name gemeldet, Name gespeichert;
  `szenario_aus_cam`, `szenario_an_cam`, `szenario_schnittwerte_job` grün.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- A2 Beispielwerte (auch im Planer: vc, Spandicke – Manuel).

## P-2026-09-26-32 plan-antworten

### EINGELESEN
- Manuel: Reihenfolge A → B → C selbstverständlich (die Frage war
  überflüssig); Warngrenze fest 10 % bei HSM, egal wie viele Schneiden; ap
  wie ae in % von D; Drehwerkzeuge gleich mit in Stufe C. Beim Bohrer
  fehlt der Spitzenwinkel.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan: Antworten, Spitzenwinkel als A6)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot enthält Manuels Antworten und den Spitzenwinkel.

### DONE
- Plan vervollständigt, Stufe A beginnt.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- A1 Werkzeugname.

## P-2026-09-26-31 plan-stufen

### EINGELESEN
- Manuels Antworten: Beispielwerte grau, aber gültig (Ø 12);
  Warngrenze 10 % bei voller Schneidenlänge als Vorgabe, darüber rote
  Warnung, aber wählbar; mm/% für ae und ap; Einheiten (mm/inch) und
  Dezimaltrennzeichen beim ersten Start und in den Einstellungen wählbar,
  mit Beispielzahlen; Werkzeuge in inch und mm umschaltbar. Dazu die Liste
  der Werkzeugarten aus InventorCAM (Screenshot, 26 Arten).

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan in drei Stufen)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot nennt die Stufen A (Werkzeugverwaltung), B (Einheiten,
Zahlenformat), C (Werkzeugarten) mit ihren Schritten.

### DONE
- Plan geordnet.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels OK zur Reihenfolge, dann Stufe A.

## P-2026-09-26-30 plan-erweitert

### EINGELESEN
- Manuel (Planung, noch nichts bauen): Namen trägt man selbst ein, ein
  Beispielname aus den Angaben wäre gut („Schaftfräser T1 VHM D12 L30“).
  Planer: „Wer sagt was von 10 %?“ – die Prozente zeigen, eine eigene
  Warngrenze eintragen können, darüber warnen. Neues Werkzeug:
  Beispielwerte, damit das Bild gleich die Form zeigt, auch beim
  Durchblättern der Liste.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan Punkt 1 ergänzt, Punkte 5 und 6)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot nennt die sechs geplanten Schritte mit den offenen Fragen.

### DONE
- Plan ergänzt.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels Antworten, dann bauen.

## P-2026-09-26-29 version-0-11-2

### EINGELESEN
- Arbeitsregeln Abschnitt 4: Korrektur → letzte Stelle. Seit 0.11.1:
  Sprachwahl beim ersten Start (P-2026-09-26-27), Plan im Snapshot (-28).

### DATEIEN
- `package.xml` (0.11.2)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.11.2.

### DONE
- Version 0.11.1 → 0.11.2.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; dann Manuels Antworten zum Plan.

## P-2026-09-26-28 plan-nach-erstem-test

### EINGELESEN
- Manuels erster Test in FreeCAD 1.1.3 (KDE, dunkles Thema): „sehr gut
  umgesetzt“. Wünsche: Werkzeugname zusätzlich zur Nummer (Option A),
  ae wahlweise in mm oder %, Dezimalzeichen wie FreeCAD („.“ für
  Postprozessoren?), das Eingriffsbild mit „ae“ und „ap“ beschriften und
  den Text daneben aufteilen. Bitte: erst alle Aktionen planen.
- `gui_zahlen.zahlenformat()` nimmt `QLocale()` – das stellt FreeCAD nach
  seiner Einstellung „Zahlenformat“ (Parameter `UseLocaleFormatting`) ein.
- FreeCADs Postprozessoren rufen Werkzeuge per Nummer; der Heidenhain-Post
  schreibt den Namen des Werkzeug-Controllers als Kommentar.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Plan, wartet auf Manuels OK)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Der Snapshot nennt die vier geplanten Schritte mit den offenen Fragen.

### DONE
- Plan festgehalten.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels OK, dann bauen.

## P-2026-09-26-27 sprachwahl-erster-start

### EINGELESEN
- Manuels erster Start (FreeCAD 1.1.3, KDE, dunkles Thema), Screenshot:
  1. Der Titel „Sprache wählen“ sagt nicht, wofür.
  2. Der Hinweis unter der Auswahl ist abgeschnitten.
  3. Er hat Deutsch gewählt, die Knöpfe des Addons blieben englisch
     („Cutting data into the job“).
  4. Frage: Wird die Sprache gemerkt?
- Ursachen, im Test nachgestellt:
  - Zu 2: Das Fenster entsteht mit dem englischen Text (bei Manuel eine
    Zeile); der deutsche braucht zwei, und das offene Fenster wächst unter
    KDE nicht mit.
  - Zu 3: FreeCAD liest Name und Tooltip eines Befehls nur einmal beim
    Anmelden (vor der Frage) und auch bei FreeCADs eigenem Sprachwechsel
    nicht neu.
  - Zu 4: Gemerkt wird die Sprache (Parameter „Sprache“). Auf die Platte
    schreibt FreeCAD aber erst beim Beenden – nach einem Absturz käme die
    Frage wieder.
- FreeCAD meldet seine eigene Sprache über `getLocale()` („German“),
  `supportedLocales()` übersetzt in den Code („de“) – in beiden Versionen.
- Nebenbei: Die Werkzeugleiste hieß je nach Sprache „CAM-Addon“ oder
  „CAM Addon“; nach einem Sprachwechsel hätte sie doppelt erscheinen können.

### DATEIEN
- `camaddon/sprache.py` (`freecad_sprache()`; ohne Wahl gilt die Sprache
  von FreeCAD, sonst Englisch)
- `camaddon/gui_sprachwahl.py` (Vorwahl = aktuelle Sprache; Platz für die
  Texte jeder Sprache; Wahl sofort speichern; danach `NACH_SPRACHWAHL`)
- `camaddon/gui_start.py` (Befehle gemerkt, `befehle_beschriften()` nach
  einer Sprachwahl und wenn FreeCAD neue Knöpfe anlegt; Werkzeugleiste
  heißt fest „CAM-Addon“)
- `translations/de.json`, `translations/en.json` (Titel mit Addon-Namen;
  `werkzeugleiste.name` entfällt)
- `tests/gui/szenario_erster_start.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Frisches FreeCAD-Profil, FreeCAD auf Deutsch → Start: Das Fenster heißt
„CAM-Addon – Sprache wählen“, Deutsch ist vorgewählt, der Hinweis ist ganz
zu lesen → OK → die Knöpfe der Werkzeugleiste „CAM-Addon“ sind deutsch,
ohne Neustart. Beim nächsten Start kommt keine Frage mehr.

### DONE
- Alle vier Punkte behoben, dazu der feste Name der Werkzeugleiste.

### TEST
- `tests/gui/szenario_erster_start.py` (beide Versionen): Titel auf
  Englisch und Deutsch; Mindesthöhe reicht für den deutschen Text (ohne die
  Korrektur schlägt das an: „zu niedrig: 116 < 130“); die Wahl steht sofort
  in user.cfg; Knopf und Tooltip nach der Wahl deutsch, nach Umstellen in
  den Einstellungen wieder englisch; die Werkzeugleiste nur einmal;
  FreeCAD auf Deutsch → Vorgabe „de“, auf Japanisch → keine (Englisch).
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Manuel: Beim nächsten Start sollte keine Frage mehr kommen; in einem
  frischen FreeCAD-Profil ist Deutsch vorgewählt.

## P-2026-09-26-26 version-0-11-1

### EINGELESEN
- Arbeitsregeln Abschnitt 4: Korrektur → letzte Stelle. Seit 0.11.0:
  „Aus CAM übernehmen“ robust gegen einzelne kaputte Werkzeuge
  (P-2026-09-26-24), Abhilfe im Tooltip „nicht in der Werkzeugverwaltung“
  (-25).

### DATEIEN
- `package.xml` (0.11.1)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.11.1.

### DONE
- Version 0.11.0 → 0.11.1.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-26-25 kein-werkzeug-abhilfe

### EINGELESEN
- Die erste Zeile, die Manuel in seinen Jobs sieht, ist oft „TC: 5mm
  Endmill – nicht in der Werkzeugverwaltung“. Der Tooltip sagte nur, warum,
  nicht, was man tun kann.

### DATEIEN
- `translations/de.json`, `translations/en.json` (`sj.kein_werkzeug.tooltip`)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Schnittwerte in den Job“ → Maus auf „– nicht in der Werkzeugverwaltung“ →
der Tooltip nennt die Abhilfe: „Aus CAM übernehmen“ in der
Werkzeugverwaltung oder hier „Werkzeug-Controller hinzufügen“.

### DONE
- Tooltip um die Abhilfe ergänzt (de/en).

### TEST
- `tests/test_sprache.py` in beiden Versionen.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-24 aus-cam-robust

### EINGELESEN
- „Aus CAM übernehmen“ trifft morgen auf Manuels echte Bibliotheken. Warf
  ein einzelnes Werkzeug beim Lesen einen Fehler, brach `uebernehmen()` ab:
  Der Dialog meldete den Fehler, aber die schon übernommenen Werkzeuge
  standen halb in der (ungespeicherten) Liste, ohne dass sie neu gezeigt
  wurde.

### DATEIEN
- `camaddon/werkzeuge_aus_cam.py` (je Werkzeug abgesichert; Bericht
  `unlesbar`, Meldung im Bericht-Fenster von FreeCAD)
- `camaddon/gui_werkzeuge.py` (Rückmeldung nennt die unlesbaren)
- `translations/de.json`, `translations/en.json`
- `tests/test_werkzeuge_aus_cam.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Aus CAM übernehmen ▾“ → eine Bibliothek, in der ein
Werkzeug kaputt ist → die übrigen erscheinen in der Liste; die Rückmeldung
sagt „Nicht lesbar – … Bericht-Fenster: <Name>“.

### DONE
- Ein Fehler betrifft nur sein Werkzeug; es steht im Bericht, die anderen
  werden übernommen.

### TEST
- `tests/test_werkzeuge_aus_cam.py` (beide Versionen): ein Werkzeug, das
  beim Lesen einen Fehler wirft („5mm Drill“) → `unlesbar`, die übrigen
  fünf bekannten Formen übernommen. `szenario_aus_cam` weiter grün.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-23 version-0-11-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.10.0: „keine Bahn: Basisgeometrie fehlt“ im Job-Dialog
  (P-2026-09-26-22); dazu Bohrer-Kopie (-19), Hilfe zu Ebenen und
  Basisgeometrie (-20, -21), Doku (-18). Der Snapshot nennt jetzt auch die
  Basisgeometrie.

### DATEIEN
- `package.xml` (0.11.0)
- `docs/STATUS_SNAPSHOT.md` (Nächster Schritt, Punkt 2)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.11.0.

### DONE
- Version 0.10.0 → 0.11.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-26-22 ohne-basisgeometrie

### EINGELESEN
- Ausprobiert (FreeCADCmd, 1.1.3 und Wochen-Build): Adaptiv (innen und
  außen), Tasche, Taschenform, Fläche und Nut ohne Basisgeometrie rechnen
  keine Bahn – keine einzige G1/G2/G3-Bewegung.
- „Schnittwerte in den Job“ zeigte für eine solche Operation trotzdem
  Ebenen, gerechnet aus den Vorgabetiefen – als würde sie fahren.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`ohne_bahn()`)
- `camaddon/gui_job_schnittwerte.py` („keine Bahn: Basisgeometrie fehlt“
  statt der Ebenen)
- `translations/de.json`, `translations/en.json`
- `help/de|en/werkzeuge.html`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit einem Adaptiv ohne Basisgeometrie und dem Controller
„T3 Schruppen dynamisch“ → „Schnittwerte in den Job“: In der Spalte steht
„Adaptiv: 10 % · 25 mm · Helix 3° · keine Bahn: Basisgeometrie fehlt“.
Mit Basisgeometrie stehen dort wieder die Ebenen.

### DONE
- Als „ohne Bahn“ gilt eine Operation mit leerer Basisgeometrie und ohne
  Bewegung in ihrer Bahn; dann keine Ebenen und kein Hinweis zu ihnen.

### TEST
- `tests/test_job_schnittwerte.py`: Adaptiv ohne Basisgeometrie → ohne
  Bahn; ein Objekt ohne `Base` zählt nicht.
- `tests/gui/szenario_schnittwerte_job.py` (beide Versionen): der Text in
  der Spalte; `szenario_loch_auffraesen` (mit Basisgeometrie) unverändert
  grün.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-21 hilfe-basisgeometrie

### EINGELESEN
- Hilfe „Ein Loch oder eine Tasche auffräsen“ sagte nur „Adaptiv auf die
  Bohrung legen“. Ausprobiert (FreeCADCmd, 1.1.3 und Wochen-Build,
  Quader 60 × 60 × 30, Bohrung Ø 30):
  - Sackloch, Boden als Basisgeometrie: räumt die Bohrung bis zum Boden
    (P-2026-09-26-16).
  - Durchgangsbohrung, **untere Kreiskante**: räumt nur die Bohrung
    (x, y 17,5 … 42,5 mit Ø 5), von 31 bis 0.
  - obere Kreiskante: nur bis 30, also 1 mm tief.
  - Bohrungswand: keine Bahn.
  - Unterseite des Teils, „Innen“: räumt die ganze Fläche 2,5 … 57,5 ab –
    das Teil wäre weg.

### DATEIEN
- `help/de|en/werkzeuge.html` (Schritt 3: welche Basisgeometrie)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Hilfe der Werkzeugverwaltung → „Ein Loch oder eine Tasche auffräsen“,
Schritt 3 nennt: Sackloch und Tasche → Boden, Durchgangsbohrung → untere
Kreiskante; und warnt vor der Unterseite des Teils und der oberen Kante.

### DONE
- Schritt 3 präzisiert, in beiden Sprachen.

### TEST
- `tests/test_hilfe.py` in beiden Versionen.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-20 hilfe-loch-verweis

### EINGELESEN
- Hilfe „Ein Loch oder eine Tasche auffräsen“, Schritt 4, versprach „taucht
  einmal helikal bis 25 mm ein“ – mit FreeCADs Rohteil sind es meist zwei
  Ebenen (P-2026-09-26-16).
- Ein Kommentar in `job_schnittwerte.py` nannte das Profil noch „Kontur“
  (P-2026-09-26-13).

### DATEIEN
- `help/de|en/werkzeuge.html` (Schritt 4 verweist auf „Eine Ebene oder
  zwei?“)
- `camaddon/job_schnittwerte.py` (nur Kommentar)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Hilfe der Werkzeugverwaltung → „Ein Loch oder eine Tasche auffräsen“,
Schritt 4: kein Versprechen „einmal“ mehr, dafür der Verweis auf „Eine
Ebene oder zwei?“.

### DONE
- Wortlaut angepasst, Kommentar angeglichen.

### TEST
- `tests/test_hilfe.py` in beiden Versionen, black und ruff.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-19 einsatz-kopieren-nachtrag

### EINGELESEN
- P-2026-09-26-12: Die Kopie einer Zeile wählt die Spalte ae – beim Bohrer
  ist sie ausgeblendet; gewählt war dann eine unsichtbare Zelle.
- Die Nummern für doppelte Namen aus „+ Einsatz“ und vom Planer
  (`einsatz_hinzufuegen`) waren nur ohne Oberfläche geprüft.

### DATEIEN
- `camaddon/gui_schnittwerte.py` (Kopie beim Bohrer: Spalte vc)
- `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Bohrer mit einer Zeile „Bohren“ → „+ Einsatz ▾ →
Gewählte Zeile kopieren“ → darunter „Bohren 2“, und die Zelle vc ist
gewählt.

### DONE
- Kopie beim Bohrer wählt vc.

### TEST
- `tests/gui/szenario_schnittwerte.py` (beide Versionen): „+ Einsatz“ und
  `einsatz_hinzufuegen` bei vorhandenem „Schruppen dynamisch“ → „… 2“ und
  „… 3“; Bohrer-Kopie „Bohren 2“ mit gewählter Spalte vc.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-18 stand-fuer-manuel-2

### EINGELESEN
- Arbeitsregeln Abschnitt 10: Snapshot und README auf den Stand bringen;
  Entscheidungen dieser Nacht in die Spezifikation.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` („Nächster Schritt“: Zeile kopieren, Ebenen
  im Job-Dialog, Außenkontur; Entscheidungen 13–23)
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 11, Nr. 21–23)
- `README.md` („Was es kann“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer Snapshot und Spezifikation liest, findet die neuen Klickwege und die
drei neuen Entscheidungen mit Alternative.

### DONE
- Nr. 21: Kopien und doppelte Namen mit Nummer; Nr. 22: Namen wie im
  Menü von FreeCAD; Nr. 23: dünne letzte Ebene nur melden, ap nicht selbst
  ändern.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuel probiert aus und bespricht die Entscheidungen.

## P-2026-09-26-17 version-0-10-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.9.0: Zeile kopieren (P-2026-09-26-12), Ebenen im Job-Dialog (-16); dazu
  Einsatz am Namen (-11), Operationsnamen wie in FreeCAD (-13),
  Fehlerbericht T-004 (-14), Git ohne Konsolenfenster (-15).

### DATEIEN
- `package.xml` (0.10.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.10.0.

### DONE
- Version 0.9.0 → 0.10.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-26-16 ebenen-im-job-dialog

### EINGELESEN
- Manuels „einmal helikal ein Grundloch, dann ebenenweise mit voller
  Schneide“ nachgestellt (FreeCADCmd, beide Versionen): Quader 60 × 60 × 30
  mit Sackloch Ø 30, 25 tief, Adaptiv mit dem Boden als Basisgeometrie,
  Zustelltiefe 25 → **zwei** Ebenen, 25 mm und 1 mm, jede mit eigener
  Helix. Grund: Die Starttiefe ist die Oberkante des Rohteils, und FreeCAD
  legt das Rohteil von sich aus 1 mm über das Modell.
- Die Ebenen rechnet FreeCAD mit `PathUtils.depth_params` (in 1.1.3 und im
  Wochen-Build gleich).
- Ändert man das Rohteil, rechnet FreeCAD die Operation nicht von selbst
  neu – sie behält die alte Starttiefe; eine Neuberechnung der Operation
  genügt (geprüft).
- Beschriftungen im deutschen FreeCAD ausgelesen: „Auftrag bearbeiten →
  Einrichtung → Materialkörper → Erw. Z“ (linkes Feld nach unten, rechtes
  nach oben), im Baum „Objekt neu berechnen“.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`ebenen()`, `duenne_letzte_ebene()`)
- `camaddon/gui_job_schnittwerte.py` (Spalte „Schrittweite ·
  Zustelltiefe“ mit „1 Ebene“ bzw. „2 Ebenen (25 + 1 mm)“; roter Satz unter
  der Tabelle bei einer dünnen letzten Ebene; Fenster breiter)
- `translations/de.json`, `translations/en.json`
- `help/de|en/werkzeuge.html` („Eine Ebene oder zwei?“)
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`,
  `tests/gui/szenario_loch_auffraesen.py` (neu)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Teil mit Sackloch 25 mm tief, Job mit FreeCADs Rohteil, Adaptiv auf den
Boden des Lochs mit dem Controller „T3 Schruppen dynamisch“ (ap 25) →
„Schnittwerte in den Job“ zeigt „… · 2 Ebenen (25 + 1 mm)“ und darunter in
Rot, dass die letzte Ebene nur 1 mm dick ist, mit den zwei Auswegen. Im
Job bei „Erw. Z“ rechts 0, Adaptiv neu berechnen → der Dialog zeigt
„1 Ebene“, kein roter Satz → Übernehmen → das Adaptiv taucht einmal
helikal bis zum Boden ein und räumt nur dort.

### DONE
- Ebenen je Operation in der Spalte, Hinweis bei dünner letzter Ebene
  (dünner als ¼ ap), mit ap-Vorschlag nur, wenn die Schneide reicht.
- Hilfe erklärt die Ursache und beide Auswege.

### TEST
- `tests/test_job_schnittwerte.py`: Ebenen der Tasche (25 + 25 + 11,
  30,5 + 30,5), ohne Tiefen [], dünne letzte Ebene (25 + 1 → ap 26;
  25 + 25 + 2 → ap 26; 11 von 25 und eine Ebene sind kein Rest).
- `tests/gui/szenario_loch_auffraesen.py` (neu, beide Versionen): Controller
  über den Dialog anlegen, 2 Ebenen mit Hinweis, Hinweis weg ohne
  Zustellung, Rohteil bündig → 1 Ebene; nach Übernehmen hat die Bahn genau
  eine Helix bis z = 5 und schneidet danach nur auf z = 5. Bilder
  `1_zwei_ebenen`, `2_eine_ebene` angesehen. (Ein 3D-Bild der Bahn blieb
  leer – eine per Skript angelegte Operation zeichnet ihre Bahn nicht; die
  Bahn wird deshalb nur in Zahlen geprüft.)
- `tests/gui/szenario_schnittwerte_job.py`: „· 1 Ebene“.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Manuel: an einem echten Teil ausprobieren. Stimmt der Satz unter der
  Tabelle mit dem überein, was er in der Simulation sieht?

## P-2026-09-26-15 git-ohne-konsolenfenster

### EINGELESEN
- Die Update-Suche ruft bei jedem Start von FreeCAD bis zu fünfmal Git auf
  (fetch, show, show, status, merge-base). FreeCAD läuft unter Windows ohne
  Konsole; startet es ein Konsolenprogramm wie git.exe, öffnet Windows dafür
  jedes Mal kurz ein schwarzes Fenster – ohne `CREATE_NO_WINDOW`.

### DATEIEN
- `camaddon/aktualisierung.py` (`OHNE_FENSTER`, an `subprocess.run`)
- `tests/test_aktualisierung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Windows: FreeCAD starten und etwa eine halbe Minute warten, bis die
Update-Suche gelaufen ist → kein schwarzes Fenster blitzt auf. Linux und
macOS: unverändert.

### DONE
- Git läuft unter Windows mit `CREATE_NO_WINDOW`; anderswo gibt es den Wert
  nicht, dort bleibt es bei 0.

### TEST
- `tests/test_aktualisierung.py`: Jeder Git-Aufruf der Suche bekommt
  `creationflags` = `CREATE_NO_WINDOW` bzw. 0 (in beiden Versionen).
- Unter Windows nicht selbst gesehen – hier gibt es kein Windows. Das
  Akzeptanzkriterium prüft Manuel, falls er Windows benutzt.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- —

## P-2026-09-26-14 t-004-fehlerbericht

### EINGELESEN
- T-004 im Snapshot: den Fehler in `Machine.from_dict` an FreeCAD melden.
- Wochen-Build 26.3.0 dev vom 2026-09-16, `Mod/CAM/Machine/models/machine.py`:
  `to_dict()` schreibt `[Ursprung, Richtung]`, `from_dict()` nimmt bei
  Linearachsen den ersten Vektor als Richtung, sobald er nicht null ist –
  der Fehler besteht weiter. FreeCAD 1.1.3 hat die Maschinenmodelle nicht.

### DATEIEN
- `docs/freecad_fehler_T-004.md` (neu: Weg zum Einreichen für Manuel, der
  englische Text mit Nachstell-Skript, erwarteter und tatsächlicher Ausgabe
  und einem Vorschlag zur Behebung)
- `docs/STATUS_SNAPSHOT.md` (T-004 verweist darauf)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel öffnet `docs/freecad_fehler_T-004.md`, folgt dem Link zu FreeCADs
Issues und kann Titel und Abschnitte ohne Änderung übernehmen; das Skript
im Text zeigt in der FreeCAD-Python-Konsole des Wochen-Builds genau die
Ausgabe unter „Actual behavior“.

### DONE
- Bericht geschrieben, Skript und Vorschlag geprüft.

### TEST
- Das Skript aus dem Bericht (aus der Datei ausgeschnitten) in FreeCADCmd
  des Wochen-Builds: Ausgabe Zeichen für Zeichen wie unter „Actual
  behavior“.
- Der Vorschlag an einer gepatchten Kopie von `machine.py`: Das Beispiel
  kommt richtig zurück, ein alter Eintrag `[[0, 1, 0], [0, 0, 0]]` weiterhin
  mit Richtung (0, 1, 0).
- Nur Doku, kein Testlauf.

### NEXT
- Manuel reicht den Bericht ein und trägt die Nummer bei T-004 ein.

## P-2026-09-26-13 operationsnamen-wie-freecad

### EINGELESEN
- Hilfe und Tooltip von „Schnittwerte in den Job“ nannten FreeCADs
  Operationen „Kontur“, „Tasche“, „Planfräsen“, „Nut“. Im deutschen FreeCAD
  heißen sie anders – ausgelesen aus den Menüs (Wegwerf-Szenario mit
  `Gui.setLocale`, beide Versionen): Adaptiv, **Profil**, **Taschenform**,
  **Fläche** (Wochen-Build: **Fräsen**), **Nute**, Bohren. Englisch: Adaptive,
  Profile, Pocket Shape, Face (Wochen-Build: Mill Facing), Slot, Drilling.
- Die Felder im Aufgabenfenster des Adaptivs: 1.1.3 „Überlappungs-Prozentsatz“,
  „Schritt runter“, „Wendel-Rampenwinkel“, „Schnittbereich: Außen/Innen“;
  Wochen-Build „Prozedurschritt (Prozent)“, „Schritt runter“, „Maximaler
  Rampenwinkel“, „Fräsbereich“.
- Manuels Beispiel „Außenkonturen schruppen“ stand nur als Satz in
  „Strategien vergleichen“. Geprüft in beiden Versionen (FreeCADCmd,
  Quader 40 × 30 × 20): Adaptiv mit der Unterseite als Basisgeometrie und
  „Außen“ fährt neben dem Rohteil gerade auf Tiefe und schneidet von der
  Seite hinein, ohne Helix; „Innen“ taucht mit Helix ein; ohne
  Basisgeometrie entsteht keine Bahn.

### DATEIEN
- `translations/de.json`, `translations/en.json` (`sj.zustellung.tooltip`)
- `help/de|en/werkzeuge.html` (Namen, Felder des Adaptivs, neuer Abschnitt
  „Eine Außenkontur schruppen“)
- `help/de|en/strategien.html` (Verweis darauf; „Zustelltiefe“ statt
  „Stufentiefe“), `help/de/schruppwerte.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Namen in Abschnitt 10 und 11)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Hilfe (?) → „Eine Außenkontur schruppen“: Die
Schritte nennen genau die Wörter, die im deutschen FreeCAD 1.1.3 im Menü
und im Aufgabenfenster des Adaptivs stehen (Adaptiv, Basisgeometrie,
Bearbeitung, Schnittbereich, Außen), und dem Weg folgend entsteht eine
Bahn rund um das Teil.

### DONE
- Namen angeglichen, Feldnamen genannt, Abschnitt Außenkontur.

### TEST
- `tests/test_sprache.py`, `tests/test_hilfe.py` in beiden Versionen; alle
  Hilfeseiten auf geschlossene Tags geprüft; der Abschnitt im Hilfefenster
  als Screenshot angesehen.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Manuel: Stimmen die Namen in seinem FreeCAD? Nennt er „Nute“ lieber
  „Nut“, bleibt es trotzdem beim Wort aus dem Menü.

## P-2026-09-26-12 einsatz-kopieren

### EINGELESEN
- Manuels „Auswertung der Strategien aus den Werten“: Eine Variante (etwa
  dynamisch mit ae 1,8 statt 1,2) musste man bisher als neue Zeile anlegen
  und alle Werte abtippen. Zwei Zeilen hießen dann gleich – im Vergleich,
  in „Schnittwerte in den Job“ und im Namen eines neuen
  Werkzeug-Controllers nicht zu unterscheiden. Dasselbe passierte, wenn der
  Planer ein zweites „Schruppen dynamisch“ anlegte.

### DATEIEN
- `camaddon/werkzeuge.py` (`name_fuer_neuen()`: frei bleibt frei, sonst
  „… 2“, „… 3“; die Kopie von „… 2“ wird „… 3“)
- `camaddon/gui_schnittwerte.py` (Menü „+ Einsatz“ → „Gewählte Zeile
  kopieren“, Kopie direkt unter der Zeile; neue Zeilen aus dem Menü und
  vom Planer bekommen eine Nummer, wenn es den Namen schon gibt)
- `translations/de.json`, `translations/en.json`
- `help/de|en/schnittwerte.html`, `help/de|en/strategien.html`
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 6.2)
- `tests/test_werkzeuge.py`, `tests/gui/szenario_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Fräser mit „Schruppen dynamisch“ (ae 1,2) → Zeile
wählen → „+ Einsatz ▾“ → „Gewählte Zeile kopieren“ → darunter steht
„Schruppen dynamisch 2“ mit denselben Werten, die Kopie ist gewählt → dort
ae 1,8 tippen → das Original behält 1,2 → „Strategien vergleichen…“ zeigt
beide mit ihrem Namen.

### DONE
- Kopieren, Nummern für doppelte Namen, Hilfe (Varianten vergleichen).

### TEST
- `tests/test_werkzeuge.py`: Namen (frei, „… 2“, Kopie der 2, groß/klein,
  „Vollnut 12“ → „Vollnut 13“).
- `tests/gui/szenario_schnittwerte.py`: Vollnut kopieren → „Vollnut 2“
  darunter und gewählt, ap 6 in der Kopie → Q 34,4, Original ap 3; Kopie
  wieder löschen. Bild `1e_kopie`.
- Menü offen und Kopie von „Schruppen dynamisch“ als Screenshot angesehen
  (Wegwerf-Szenario, nicht im Repo).
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Manuel: Varianten anlegen und vergleichen – ist die Nummer im Namen
  verständlich, oder lieber gleich ein eigener Name?

## P-2026-09-26-11 einsatz-am-namen

### EINGELESEN
- `vorgeschlagener_einsatz()` nahm die erste Zeile, deren Name im Namen des
  Werkzeug-Controllers steht. „T3 Schruppen dynamisch“ enthält aber auch
  „Schruppen“ – mit den Zeilen Vollnut, Schruppen, Schruppen dynamisch (die
  übliche Reihenfolge im Menü „+ Einsatz“) schlug der Dialog „Schnittwerte
  in den Job“ also „Schruppen“ vor, auch für den Controller, den
  „Werkzeug-Controller hinzufügen“ selbst so benannt hat. Der Test hatte nur
  Vollnut und dynamisch.

### DATEIEN
- `camaddon/job_schnittwerte.py` (passen mehrere Namen, gewinnt der
  längste)
- `tests/test_job_schnittwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung: Fräser T3 mit den Einsätzen Vollnut, Schruppen,
Schruppen dynamisch → im Job einen Controller „T3 Schruppen dynamisch“ →
„Schnittwerte in den Job“ schlägt in seiner Zeile „Schruppen dynamisch“ vor.

### DONE
- Unter den Zeilen, deren Name im Controller steht, zählt die mit dem
  längsten Namen; bei gleich langen die erste.

### TEST
- `tests/test_job_schnittwerte.py`: Vollnut, Schruppen, Schruppen dynamisch
  → Index 2 für „T3 Schruppen dynamisch“.
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Zeile kopieren (Varianten für den Vergleich), Namen neuer Zeilen
  unterscheidbar.

## P-2026-09-26-10 version-0-9-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.8.0: Vergleich mit der Vollnut im Planer (P-2026-09-26-04), alle
  Einsätze im Vergleich (-05), Durchmesser umrechnen (-06), kaputte
  Bibliothek (-07), Eintauchwinkel (-08), Doku (-09).

### DATEIEN
- `package.xml` (0.9.0)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.9.0.

### DONE
- Version 0.8.0 → 0.9.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-26-09 stand-fuer-manuel

### EINGELESEN
- Arbeitsregeln Abschnitt 10: Snapshot auf den Stand bringen; README „Was
  es kann“ nennt, was dazukam.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Projektstatus W-002; „Nächster Schritt“ als
  Reihenfolge zum Ausprobieren mit Verweisen auf die Klickwege)
- `README.md` („Was es kann“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer den Snapshot liest, weiß, in welcher Reihenfolge er was ausprobiert
und wo die Klickwege stehen.

### DONE
- Nächster Schritt: Werkzeugverwaltung → CAM-Job (Loch auffräsen) →
  Maschine verfahren → Besprechen (Entscheidungen 13–20, Fragen zu
  Stufe 4).

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Version 0.9.0, alle Prüfungen, Push.

## P-2026-09-26-08 eintauchwinkel

### EINGELESEN
- Manuels „einmal helikal ein Grundloch“: Das Adaptiv taucht helikal ein,
  mit FreeCADs Vorgabe von 5° – wie steil ein Fräser eintauchen darf, steht
  aber im Katalog und hängt am Werkzeug.
- FreeCAD 1.1.3: `HelixAngle`, Wochen-Build: `HelixMaxRampAngle` (beide
  Grad, Vorgabe 5°).

### DATEIEN
- `camaddon/werkzeuge.py` (Feld `eintauchwinkel`, 0 … 90°),
  `camaddon/gui_werkzeuge.py` (Feld im Formular, beim Bohrer
  ausgeblendet)
- `camaddon/job_schnittwerte.py` (`zustellung()` setzt den Helixwinkel),
  `camaddon/gui_job_schnittwerte.py` („Helix 3°“ in der Spalte)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge.py`, `tests/test_job_schnittwerte.py`,
  `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ø-12-Fräser mit Eintauchwinkel 3° → Job mit Adaptiv und Controller
„T3 Schruppen dynamisch“ → „Schnittwerte in den Job“ → Spalte zeigt
„Adaptiv: 10 % · 25 mm · Helix 3°“ → Übernehmen → im Adaptiv steht der
Eintauchwinkel der Helix auf 3°.

### DONE
- Freiwilliges Feld am Werkzeug; leer bleibt FreeCADs Vorgabe.
- Gesetzt nur im Adaptiv (und nur, wenn der Einsatz dorthin passt, siehe
  Entscheidung 18) – in 1.1.3 als `HelixAngle`, im Wochen-Build als
  `HelixMaxRampAngle`.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` (gespeichert,
  begrenzt), `test_job_schnittwerte` (Helixwinkel im Adaptiv, nicht in der
  Nut) grün.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job`
  (Spalte, gesetzter Winkel) und `szenario_werkzeugverwaltung` grün,
  Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-07 kaputte-bibliothek

### EINGELESEN
- „Aus CAM übernehmen“ (P-2026-09-25-66): Ließ sich eine einzige
  FreeCAD-Werkzeugbibliothek nicht lesen, blieb das ganze Menü leer.

### DATEIEN
- `camaddon/werkzeuge_aus_cam.py` (`bibliotheken()`: je Bibliothek
  abgefangen)
- `tests/test_werkzeuge_aus_cam.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Eine kaputte `.fctl`-Datei neben „Default“ → „Aus CAM übernehmen“ bietet
„Default“ weiter an; im Bericht-Fenster steht, welche Bibliothek nicht ging.

### DONE
- Je Bibliothek abgefangen, Warnung ins Bericht-Fenster, die übrigen
  bleiben wählbar.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge_aus_cam` grün
  (kaputte Bibliothek „kaputt“ neben „Default“).
- Manuel: –

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-06 durchmesser-umrechnen

### EINGELESEN
- Hilfe der Werkzeugverwaltung: „Kopieren – praktisch für denselben Fräser
  in einem anderen Durchmesser“. Nach dem Kopieren standen ae und ap aber
  noch für den alten Durchmesser da (Vollnut Ø 10 mit ae 12 → Hinweis „ae
  größer als D“).

### DATEIEN
- `camaddon/werkzeuge.py` (`hat_zustellungen()`,
  `zustellungen_umrechnen()`), `camaddon/gui_werkzeuge.py` (Frage beim
  neuen Durchmesser)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge.py`, `tests/gui/szenario_durchmesser.py` (neu)
- `docs/spezifikation_werkzeugverwaltung.md` (Entscheidung 20),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ø-12-Fräser mit Vollnut 12 / 6 und Schruppen dynamisch 1,2 / 24 →
Kopieren → Durchmesser 10 → Frage „… von 12 auf 10 mm … umrechnen?“ → Ja →
Vollnut 10 / 5, dynamisch 1 / 20, vc und fz wie vorher, auch in den eigenen
Werten für 1.4301; das Original bleibt Ø 12. Noch einmal auf 8 → Nein →
nur der Durchmesser ändert sich.

### DONE
- Gefragt wird nur, wenn es Einsätze mit ae oder ap gibt und beide
  Durchmesser bekannt sind; umgerechnet wird für alle Werkstoffe, auf
  0,001 mm gerundet.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` grün.
- KI, Oberfläche in **beiden** Versionen: `szenario_durchmesser` (Ja,
  Nein, Original unverändert) und `szenario_werkzeugverwaltung` grün,
  Screenshots angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-05 alle-einsaetze-im-vergleich

### EINGELESEN
- Manuels Wunsch: „Beurteilung für verschiedene Strategien anhand der
  Werte“. „Strategien vergleichen“ (P-2026-09-25-49) stellt zwei Einsätze
  nebeneinander; bei vier oder fünf Zeilen fehlte der Überblick.

### DATEIEN
- `camaddon/gui_strategie.py` (Übersicht unten im Fenster)
- `help/de|en/strategien.html`, `translations/de.json`,
  `translations/en.json`
- `tests/gui/szenario_strategien.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ø-12-Fräser mit Vollnut, Schlichten und Schruppen dynamisch, Werkstoff C45
→ „Strategien vergleichen…“ → unten „Alle Einsätze dieser Tabelle“: drei
Zeilen; bei „Schruppen dynamisch“ sind Q 43,0, Zeit 2,3, Weg 0,29 und
Schneide 25 fett; Vollnut orange, Schruppen dynamisch blau → Klick auf
„Schlichten“ → B ist Schlichten.

### DONE
- Je Einsatz Q, Zeit für 100 cm³, Schneidenweg je cm³, genutzte Schneide,
  Anteil im Material, größte Spandicke, Leistung (nur mit kc1.1). Fett das
  Beste je Spalte, wo „besser“ eindeutig ist; A und B in ihrer Farbe.
- Ein Klick nimmt die Zeile als B (war sie A, tauschen A und B).

### TEST
- KI, Oberfläche in **beiden** Versionen: `szenario_strategien` grün
  (Zeilen, Fettdruck, Klick), Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-04 planer-vergleich-vollnut

### EINGELESEN
- Manuels Beispiel: Ø 12 mit ae 1,2 / ap 25 statt Vollnut mit ap 3 – der
  Planer (P-2026-09-25-60) sagte bisher nur, was er vorschlägt, nicht, was
  das gegenüber der Vollnut bringt.

### DATEIEN
- `camaddon/schruppwerte.py` (`vergleichszeile()`),
  `camaddon/gui_schruppwerte.py` (Satz unter der Tabelle),
  `camaddon/gui_schnittwerte.py` (gibt die Vollnut der Tabelle mit)
- `help/de|en/schruppwerte.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_schruppwerte.py`, `tests/gui/szenario_schruppwerte.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ø-12-Fräser mit Vollnut 12 / 3 / 120 / 0,05 → „Schruppwerte planen…“ → unter
der Tabelle: „Zum Vergleich: Vollnut (ae 12 mm, ap 3 mm) schafft
17,2 cm³/min – der Vorschlag das 1,3-Fache, mit 24 statt 3 mm Schneide.“

### DONE
- Verglichen wird mit der ersten Vollnut der Tabelle, die vc, fz und ap
  hat; ohne eine solche fehlt der Satz.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_schruppwerte` grün.
- KI, Oberfläche in **beiden** Versionen: `szenario_schruppwerte` grün
  (prüft den Satz), Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-03 version-0-8-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.7.0: Revolverplatz wählen (P-2026-09-25-69), Werkzeuge suchen (-71),
  Werkstoff am Rohteil (-72), Planer vorbelegen (-73), Werkzeugbild
  (P-2026-09-26-01) und der Fix gegen die grundlose Rückfrage (-02).

### DATEIEN
- `package.xml` (0.8.0, Datum)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.8.0.

### DONE
- Version 0.7.0 → 0.8.0.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-26-02 keine-scheinaenderung

### EINGELESEN
- Beim Ansehen der Werkzeugbilder (P-2026-09-26-01) gefunden: Abbrechen
  fragte „Speichern?“, obwohl nichts geändert war.

### DATEIEN
- `camaddon/werkzeuge.py` (`als_dict`: leere Tabelle „für alle“ wie keine)
- `camaddon/gui_werkzeuge.py` (unverändertes Zahlenfeld schreibt nicht
  zurück)
- `camaddon/werkzeuge_aus_cam.py` (Maße auf 0,0001 mm gerundet)
- `tests/test_werkzeuge.py`, `tests/gui/szenario_aus_cam.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Aus CAM übernehmen“ → „Default“ → OK → wieder öffnen →
jedes Werkzeug einmal anklicken → Abbrechen → das Fenster schließt ohne
Rückfrage.

### DONE
- **Ursache 1:** Das Anzeigen legt für ein Werkzeug ohne Schnittwerte eine
  leere Tabelle „für alle Werkstoffe“ an (damit „+ Einsatz“ etwas hat, an
  das es anhängen kann). Die galt beim Vergleich als Änderung. Jetzt
  zählt eine leere Tabelle „für alle“ wie keine – gespeichert wird sie
  nicht.
- **Ursache 2:** Beim Schließen liest der Dialog das Zahlenfeld mit dem
  Fokus zurück. Das Feld zeigt 12 Stellen; ein längerer Wert (FreeCAD
  rechnet den Durchmesser des Fasenfräsers aus: 10,260512242138308) kam
  gekürzt zurück. Jetzt bleibt der Wert, solange im Feld steht, was es
  beim Füllen zeigte; übernommene Maße werden außerdem auf 0,0001 mm
  gerundet.
- Betraf vor allem Werkzeuge, die nicht im Dialog angelegt wurden – also
  genau die aus „Aus CAM übernehmen“.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` (Ansehen ist
  keine Änderung, eine neue Zeile schon), `test_werkzeuge_aus_cam` grün.
- KI, Oberfläche in **beiden** Versionen: `szenario_aus_cam` (wieder
  öffnen, alle ansehen, Abbrechen ohne Rückfrage) und
  `szenario_werkzeugverwaltung` grün. Vor der Korrektur scheiterte das
  Szenario im Wochen-Build genau daran.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-26-01 werkzeugbild

### EINGELESEN
- Manuels Wunsch nach einer „übersichtlicheren“ Werkzeugverwaltung, „etwa
  wie die alte von InventorCAM“ – die zeigt zu jedem Werkzeug ein Bild.
- Arbeitsregeln Abschnitt 8: Bilder ohne Text, damit sie in jeder Sprache
  passen (wie das Eingriffsbild, P-2026-09-25-48).

### DATEIEN
- `camaddon/gui_werkzeugbild.py` (neu), `camaddon/gui_werkzeuge.py` (Bild
  rechts neben den Feldern)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json` (Tooltip)
- `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → ein Schaftfräser Ø 12, Schneidenlänge 26,
Gesamtlänge 83 → rechts steht er schlank mit kurzer Schneide; Art auf
„Radiusfräser“ → unten rund; „Fasenfräser“ → spitz; Gesamtlänge leeren →
der Schaft ist gestrichelt.

### DONE
- Schaft, Schneide (mit angedeuteten Wendeln) und Spitze je Art: flach,
  Eckradius, Kugel, 90°-Fase, 118°-Bohrerspitze – maßstäblich, geschätzte
  Maße gestrichelt. Folgt jeder Eingabe.
- **Gefundener Fehler im eigenen Entwurf:** Bei Fasenfräser und Bohrer war
  die Spitze schief (ein Eckpunkt fehlte im Umriss) – am Screenshot
  gesehen, behoben.

### TEST
- KI, Oberfläche in **beiden** Versionen: `szenario_werkzeugverwaltung`
  grün; alle fünf Arten und ein Fräser mit dickerem Schaft als Screenshot
  angesehen (Szenario nur zum Ansehen, nicht eingecheckt).
- Manuel: offen.

### NEXT
- Beim Ansehen gefunden: Das bloße Anzeigen eines Werkzeugs ohne
  Schnittwerte gilt als Änderung (falsche Rückfrage „Speichern?“) –
  eigener Patch.

## P-2026-09-25-74 texte-ueber-und-leer

### EINGELESEN
- „Über das CAM-Addon“ nannte noch den Stand vor dieser Nacht; der Hinweis
  bei leerer Werkzeugliste kannte „Aus CAM übernehmen“ (P-66) nicht.

### DATEIEN
- `translations/de.json`, `translations/en.json` (`ueber.text`,
  `wv.leer`)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
„Über das CAM-Addon“ nennt Verfahren, Schruppwert-Planer und Schrittweite/
Zustelltiefe; eine leere Werkzeugverwaltung nennt „Neu“ und „Aus CAM
übernehmen“.

### DONE
- Beide Texte deutsch und englisch nachgezogen.

### TEST
- KI: `test_sprache` in beiden Versionen grün (Platzhalter unverändert).
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-73 planer-maschine-vorbelegen

### EINGELESEN
- „Schruppwerte planen“ (P-60): Die Grenzen der Maschine kamen nur auf
  Knopfdruck von einer W-001-Maschine.

### DATEIEN
- `camaddon/schruppwerte.py` (`vorbelegung()`),
  `camaddon/gui_schruppwerte.py` (vorbelegen, grauer Satz „Drehzahl und
  Vorschub von …“)
- `help/de|en/schruppwerte.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_schruppwerte.py`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit Maschinenobjekt offen, Planer noch nie mit
Maschinenwerten benutzt → Werkzeugverwaltung → „Schruppwerte planen…“ →
Höchstdrehzahl und höchster Vorschub stehen schon da, darunter grau
„Drehzahl und Vorschub von „Testdrehmaschine““.

### DONE
- Vorbelegt wird nur, wenn beide Felder leer sind und genau eine Maschine
  offen ist; sonst bleibt es beim Gemerkten bzw. bei „Von der Maschine“.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_schruppwerte` grün (vier
  Fälle der Vorbelegung).
- KI, Oberfläche in **beiden** Versionen: `szenario_schruppwerte` grün
  (ohne Maschine: Felder leer wie bisher).
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-72 werkstoff-am-rohteil

### EINGELESEN
- „Schnittwerte in den Job“ (P-53) liest den Werkstoff vom Rohteil über die
  Werkstoffnummer der FreeCAD-Karte. Hat das Rohteil keinen, wählt man ihn
  jedes Mal neu – und FreeCADs eigener Vorschlag im Wochen-Build findet die
  Presets nicht.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`nummer_am_rohteil()`, `karte_fuer()`,
  `setze_werkstoff_am_rohteil()`)
- `camaddon/gui_job_schnittwerte.py` (Knopf „Am Rohteil eintragen“)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit Rohteil 1.4301 → „Schnittwerte in den Job“ → oben „1.0503 C45“
wählen → „Am Rohteil eintragen“ erscheint → klicken → darunter steht „Vom
Rohteil des Jobs: 1.0503 C45 …“, der Knopf verschwindet; im Rohteil steht
die FreeCAD-Karte C45; Strg+Z bringt 1.4301 zurück.

### DONE
- Der Knopf erscheint nur, wenn es für den gewählten Werkstoff eine
  FreeCAD-Karte mit derselben Nummer gibt und das Rohteil sie noch nicht
  hat. Eintragen in einer Transaktion.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_job_schnittwerte` grün –
  C45 am Rohteil, Werkstoff des Jobs danach C45, Strg+Z, Nummer ohne Karte.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job` grün,
  Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-71 werkzeuge-suchen

### EINGELESEN
- Manuels Wunsch nach einer Werkzeugverwaltung, die „viel übersichtlicher“
  ist. Nach „Aus CAM übernehmen“ (P-66) wird die Liste schnell lang.

### DATEIEN
- `camaddon/werkzeuge.py` (`passt()`), `camaddon/gui_werkzeuge.py`
  (Suchfeld über der Liste)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge.py`, `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung mit T1 Schaftfräser Ø 12 und T2 Torusfräser Ø 10,5 →
„torus“ ins Suchfeld → nur noch T2 in der Liste, rechts seine Werte → Feld
leeren (×) → beide wieder da.

### DONE
- Jedes Wort muss in Zeile oder Bezeichnung vorkommen, ohne Groß/klein;
  Komma und Punkt gelten gleich, das Ø darf fehlen („ø10.5 hoff“).
- Versteckt die Suche das gewählte Werkzeug, wird das erste gezeigte
  gewählt. Ein neues, kopiertes oder übernommenes Werkzeug, das die Suche
  verstecken würde, leert die Suche – nichts wird unsichtbar bearbeitet.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` grün (sieben
  Suchen).
- KI, Oberfläche in **beiden** Versionen: `szenario_werkzeugverwaltung`
  und `szenario_aus_cam` grün, Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-70 entwurf-stufe-4

### EINGELESEN
- Spezifikation W-001, Abschnitt 9: „Stufe 4 – Werkzeugbahn abfahren und
  Kollision prüfen – eigene Spezifikation, wenn Stufe 3 steht.“ Stufe 3
  steht (P-67, P-69).
- FreeCAD: CAM-Simulator (Materialabtrag), Bahn der Operationen
  (`op.Path.Commands`), Maschinendefinition des Wochen-Builds (Kinematik,
  AxisRole).

### DATEIEN
- `docs/spezifikation_simulation.md` (neu, Entwurf)
- `docs/spezifikation_maschine_aus_baugruppe.md` (Verweis),
  `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel liest den Entwurf und beantwortet die sechs Fragen in Abschnitt 9;
danach ist klar, was 4a baut.

### DONE
- Zielbild (Reichweite, Abfahren, Kollision, Zeit), was es schon gibt,
  Achsstellungen aus der Bahn (lineares Gleichungssystem für 3 Achsen,
  Drehachsen zuerst bei 4/5 Achsen), Stufen 4a–4d, Oberfläche, Grenzen,
  Prüfbarkeit, Fragen, Akzeptanzkriterien 4a.
- Vorschlag: 4a „Reichweite prüfen“ zuerst – schnell gebaut, sofort
  nützlich, und es klärt die Achszuordnung, die alle weiteren Stufen
  brauchen.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels Antworten; dann 4a.

## P-2026-09-25-69 revolverplatz-waehlen

### EINGELESEN
- „Maschine verfahren“ (P-2026-09-25-67): Beim Revolver ist ein Winkel in
  Grad umständlich; gedacht wird in Plätzen (Spezifikation W-001,
  Abschnitt 7a: Plätze P1 … Pn als Werkzeugaufnahmen im Glied des
  Revolvers).

### DATEIEN
- `camaddon/verfahren.py` (`platzstellungen()`, Lagen der Plätze beim
  Öffnen)
- `camaddon/gui_verfahren.py` (Auswahl der Plätze in der Zeile des
  Revolvers)
- `help/de|en/verfahren.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_verfahren.py`, `tests/gui/szenario_verfahren.py`
- `docs/spezifikation_maschine_aus_baugruppe.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit 12 verteilten Revolverplätzen → „Maschine
verfahren“ → in der Zeile T steht rechts „P1“ → „P4“ wählen → T steht auf
−90°, P4 steht, wo P1 stand; zieht man T weiter, zeigt die Auswahl „–“.

### DONE
- Je Platz die Stellung der Revolverachse, in der er dort steht, wo beim
  Öffnen P1 stand – aus dem Winkel der Plätze um die Achse, kürzester Weg.
  Gilt für jede Verteilung, nicht nur gleichmäßige.
- Die Auswahl folgt dem Regler: Steht ein Platz an der Stelle von P1
  (±0,05°), zeigt sie ihn, sonst „–“.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_verfahren` grün – 12
  Plätze P1 … P12, P4 = 90° von P1, nach dem Drehen steht P4 auf 1e-6 mm
  genau, wo P1 stand; Linearachse ohne Plätze.
- KI, Oberfläche in **beiden** Versionen: `szenario_verfahren` grün,
  Screenshot angesehen.
- Manuel: offen – vor allem: Ist „an die Stelle von P1“ die richtige
  Arbeitsstellung, oder soll man sie festlegen können?

### NEXT
- Vor dem nächsten Push alle Prüfungen.

## P-2026-09-25-68 version-0-7-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.6.0: Werkzeug-Controller anlegen (P-65), Aus CAM übernehmen (P-66),
  Maschine verfahren (P-67).

### DATEIEN
- `package.xml` (0.7.0, Beschreibung)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.7.0.

### DONE
- Version 0.6.0 → 0.7.0; die Beschreibung nennt Verfahren und Übernehmen.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-25-67 maschine-verfahren

### EINGELESEN
- Spezifikation W-001, Abschnitt 9, Stufe 3: „Ein Fenster mit einem Regler
  je Betriebsart (Name, Wert, Grenzen); die Baugruppe bewegt sich mit.“
  Abschnitt 4: Auch Gelenke ohne Betriebsart setzt man in Stufe 3 von Hand.
- FreeCAD 1.1.3 und Wochen-Build ausprobiert: Schiebe- und Drehgelenke der
  Assembly haben keinen Sollwert – ihre Stellung ist, wo die Teile stehen.
  Bewegt man alle Bauteile hinter einer Achse, lässt die Assembly die
  Stellung beim Lösen und Neuberechnen stehen; bewegt man nur einen Teil,
  zieht sie sie woanders hin. Ihre Grenzen setzt sie beim Lösen nicht durch.

### DATEIEN
- `camaddon/verfahren.py` (neu), `camaddon/gui_verfahren.py` (neu)
- `camaddon/gui_maschine.py` (`gewaehlte_assembly()` öffentlich, damit
  beide Befehle dieselbe Assembly finden)
- `camaddon/gui_start.py` (Befehl, Werkzeugleiste), `camaddon/hilfe.py`
- `resources/icons/verfahren.svg` (neu), `help/de|en/verfahren.html` (neu)
- `translations/de.json`, `translations/en.json`
- `tests/test_verfahren.py`, `tests/gui/szenario_verfahren.py` (neu)
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/aufbau.md`
  (Module, Stolperstein), `CHATSTART.md`, `README.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Beispiel-Drehmaschine mit Maschinenobjekt (Z1, X1 mit Grenzen 0 … 200 mm,
S4/C4, T) → Assembly wählen → Werkzeugleiste „Maschine verfahren“ → Zeilen
C4, Z1, X1, T → Regler C4 auf 90° → das Futter dreht sich um 90° → X1 auf
500 tippen → bleibt bei 200 mm stehen → Abbrechen → alles steht wie vorher;
noch einmal öffnen, X1 auf 100, OK → X1 bleibt; Strg+Z → zurück.

### DONE
- Je Achse der Kette eine Zeile: Name (NC-Namen der Betriebsarten ohne die
  Spindel, sonst das Gelenk), Regler (0,1 mm bzw. 0,1°), Zahlenfeld mit
  Einheit, darunter grau die Grenzen oder „ohne Grenze“.
- Stellung gezählt wie am Gelenk (Seite 2 gegenüber Seite 1): Linear
  entlang Z von Seite 1, Dreh als Winkel der X-Achsen um Z. Das Vorzeichen
  hängt davon ab, auf welcher Seite das bewegte Teil steht – geprüft mit
  einem Gelenk, dessen bewegtes Teil Seite 1 ist.
- Bewegt werden alle Bauteile hinter der Achse, gerechnet vom Stand beim
  Öffnen aus – mehrere Achsen hintereinander ohne Fehler, die sich
  aufsummieren (C auf der Wiege A bleibt auf 45°, auch bei A = ±30°).
- OK = ein Schritt Rückgängig; Abbrechen und „Grundstellung“ fahren exakt
  zurück.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_verfahren` grün –
  Drehmaschine (Namen, Grenzen 0 … 200, Revolver fährt mit X1, vier Achsen
  zugleich, Futter um 90°, Stellung nach Lösen und Neuberechnen, exakte
  Grundstellung), Fünfachser (A/C), bewegtes Teil auf Seite 1.
- KI, Oberfläche in **beiden** Versionen: `szenario_verfahren` grün,
  Screenshot angesehen (Fenster mit vier Reglern, X1 an der Grenze).
- Manuel: offen – vor allem, ob die Richtung der Achsen und der
  Nullpunkt so sind, wie er sie an seiner Maschine erwartet.

### NEXT
- Alle Prüfungen, Version 0.7.0, Push. Stufe 4 braucht zuerst eine
  eigene Spezifikation.

## P-2026-09-25-66 aus-cam-uebernehmen

### EINGELESEN
- Wer seine Fräser schon in FreeCAD CAM angelegt hat, müsste sie in der
  Werkzeugverwaltung abtippen.
- FreeCAD 1.1.3 und Wochen-Build ausprobiert: Bibliotheken über
  `cam_assets.list_assets(asset_type="toolbitlibrary")`, Werkzeuge über
  `get_bits()` und `get_bit_no_from_bit()`, Maße am ToolBit-Objekt
  (`ShapeType`, `Diameter`, `Flutes`, `CuttingEdgeHeight`, `Length`,
  `ShankDiameter`, `CornerRadius`, `Material`). Ein leerer Speicher bekommt
  wie in CAM selbst erst die mitgelieferte Bibliothek „Default“
  (`ensure_assets_initialized`).

### DATEIEN
- `camaddon/werkzeuge_aus_cam.py` (neu)
- `camaddon/gui_werkzeuge.py` (Knopf „Aus CAM übernehmen“ mit Menü der
  Bibliotheken, Rückmeldung)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge_aus_cam.py`, `tests/gui/szenario_aus_cam.py` (neu)
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe 2, Entscheidung 19),
  `docs/aufbau.md`, `CHATSTART.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Aus CAM übernehmen“ → „Default (13 Werkzeuge)“ → die
Rückmeldung nennt 5 übernommene Werkzeuge, was schon da war und die Formen,
die nicht gehen (V-Bits, Säge, Taster, Gewindefräser) → in der Liste stehen
T2 Schaftfräser Ø 5, T3 Bohrer Ø 5, T4 Radiusfräser Ø 6, T5 Torusfräser
Ø 6, T10 Fasenfräser; T5 hat Eckradius 1,5, Schneidenlänge 40,
Gesamtlänge 50, Schaft 3, HSS → OK speichert.

### DONE
- Formen: Schaftfräser, Torusfräser, Radiusfräser, Fasenfräser, Bohrer.
  Gravierstichel nicht (kein Spitzenwinkel in der Werkzeugverwaltung),
  ebenso Säge, Gewindefräser, Taster – die Rückmeldung nennt sie.
- Schon da ist, was gleiche Art und gleichen Durchmesser hat und gleiche
  Nummer oder gleichen Namen – so wird auch ein beim letzten Mal
  umnummeriertes Werkzeug nicht doppelt geholt; es behält seine
  Schnittwerte. Die eigene Bibliothek „CAM-Addon“ wird nicht angeboten.
- Vergebene Nummer: die kleinste freie, die auch in der Quelle nicht
  vorkommt.
- Gespeichert wird wie sonst mit OK oder Übernehmen.
- **Gefundene Fehler im eigenen Entwurf:** Die erste Fassung vergab „die
  nächste freie Nummer“ – und schob damit T3, T4, T5 … der Quelle jeweils
  eins weiter. Und ein umnummeriertes Werkzeug kam beim zweiten Holen noch
  einmal. Beides mit der Prüfung gefunden und behoben.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge_aus_cam` grün –
  Bibliothek „Default“, „CAM-Addon“ nicht angeboten, 5 übernommen, T1 schon
  da (behält seine Schnittwerte), T2 vergeben → T14, 7 Formen draußen,
  Werte des Torusfräsers, zweites Holen: nichts neu.
- KI, Oberfläche in **beiden** Versionen: `szenario_aus_cam` grün,
  Screenshots angesehen (Rückmeldung, Liste).
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen, Version 0.7.0.

## P-2026-09-25-65 werkzeug-controller-anlegen

### EINGELESEN
- Der Weg „Loch auffräsen“ (P-61) brauchte einen Werkzeug-Controller, den
  man von Hand anlegt und so benennt, dass der Einsatz im Namen steht –
  ein fehleranfälliger Schritt.
- FreeCAD legt Controller mit `Controller.Create` im **aktiven** Dokument an
  (1.1.3 und Wochen-Build); `cam_assets.get()` liefert je Aufruf ein neues
  ToolBit, das sich einmal anhängen lässt.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`controller_name()`,
  `lege_controller_an()`, `_setze_werte()` aus `setze()` gelöst)
- `camaddon/gui_job_schnittwerte.py` (Knopf „Werkzeug-Controller
  hinzufügen“ mit Menü je Werkzeug und Einsatz)
- `help/de|en/werkzeuge.html` (Knopf; „Schritt für Schritt: vom Katalog in
  den Job“ oben auf der Seite; der Weg „Loch auffräsen“ nutzt den Knopf)
- `translations/de.json`, `translations/en.json`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `README.md` („Was es kann“), `docs/spezifikation_werkzeugverwaltung.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
CAM-Job, Rohteil 1.4301, Werkzeugverwaltung mit dem Ø-12-Fräser (Vollnut,
Schruppen dynamisch) → „Schnittwerte in den Job“ → „Werkzeug-Controller
hinzufügen“ → „T3 Schaftfräser Ø 12 · z 3 · VHM“ → „Vollnut“ → in der
Tabelle steht eine neue Zeile „T3 Vollnut“, Einsatz Vollnut, jetzt
eingestellt 2122 U/min · 318 mm/min; im Baum des Jobs steht der Controller
mit dem Fräser; Strg+Z nimmt ihn zurück.

### DONE
- Menü je Werkzeug (nur solche mit D) mit seinen Einsätzen, die vc und fz
  haben – für den gewählten Werkstoff. Ohne solche: ein grauer Eintrag
  „Kein Werkzeug mit vc und fz“.
- Anlegen: erst alle Werkzeuge an CAM übergeben (das Werkzeug soll auf dem
  gespeicherten Stand in der Bibliothek stehen), dann ToolBit anhängen,
  Controller „T<Nummer> <Einsatz>“ mit der T-Nummer, in den Job, n und vf
  setzen – eine Transaktion. Die Zeile erscheint sofort, der Einsatz ist am
  Namen erkannt.
- Hilfe: „Schritt für Schritt: vom Katalog in den Job“ – sieben Schritte
  vom Werkstoff bis zu Schrittweite und Zustelltiefe im Adaptiv.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_job_schnittwerte` grün –
  neuer Controller „T3 Vollnut“, T3, Werkzeug aus der Bibliothek, 2122 U/min
  und 318 mm/min, Einsatz am Namen erkannt, Strg+Z entfernt Controller und
  Werkzeug.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job` grün
  (Menü → „Vollnut“ ausgelöst), Screenshot angesehen.
- Manuel: offen.

### NEXT
- Vor dem nächsten Push alle Prüfungen, Version 0.6.1 oder höher.

## P-2026-09-25-64 version-0-6-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.5.1: Schruppwerte planen (P-60), Schrittweite und Zustelltiefe in die
  Operationen (P-61), Gesamtlänge und Schaft (P-62), „rpm“ auf Englisch
  (P-63).

### DATEIEN
- `package.xml` (0.6.0, Beschreibung)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.6.0.

### DONE
- Version 0.5.1 → 0.6.0; die Beschreibung nennt den Planer und die
  Übergabe von Schrittweite und Zustelltiefe.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push.

## P-2026-09-25-63 englisch-rpm

### EINGELESEN
- Durchsicht der Werkzeugverwaltung auf Englisch (Werkzeugverwaltung,
  Schruppwerte planen, Strategien vergleichen, Werkstoffe) als Screenshots.

### DATEIEN
- `camaddon/gui_schnittwerte.py`, `camaddon/gui_job_schnittwerte.py`,
  `camaddon/gui_schruppwerte.py` (Einheit der Drehzahl aus den Texten)
- `translations/de.json`, `translations/en.json` (`einheit.drehzahl`)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Sprache Englisch → Werkzeugverwaltung → die Spalte n heißt „n rpm“; in
„Plan roughing values…“ steht hinter „Maximum speed“ „rpm“. Auf Deutsch
bleibt es „U/min“.

### DONE
- Die Einheit „U/min“ stand fest im Code (Tabellenköpfe, Planer) und war
  auch auf Englisch zu sehen – jetzt „rpm“. Sonst fiel beim Durchsehen
  nichts auf.

### TEST
- KI, Oberfläche 1.1.3 auf Englisch (Szenario nur zum Ansehen, nicht
  eingecheckt): Screenshots angesehen. `test_sprache` grün.
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.6.0, Push.

## P-2026-09-25-62 gesamtlaenge-und-schaft

### EINGELESEN
- Spezifikation W-002, Entscheidung 10: Gesamtlänge und Schaft wurden bei
  der Übergabe an CAM geschätzt; die Alternative „zwei Felder“ war als
  leicht nachzurüsten vermerkt. CAM braucht beide für Simulation und
  Kollision.

### DATEIEN
- `camaddon/werkzeuge.py` (Felder `gesamtlaenge`, `schaft`;
  `geschaetzte_laenge()`, `laenge_fuer_cam()`, `schaft_fuer_cam()`)
- `camaddon/uebergabe_werkzeuge.py` (nimmt sie)
- `camaddon/gui_werkzeuge.py` (zwei Felder, grau die Schätzung, Hinweis
  bei zu kurzer Gesamtlänge; der Eckradius steht jetzt zuletzt)
- `help/de|en/werkzeuge.html`, `translations/de.json`,
  `translations/en.json`
- `tests/test_werkzeuge.py`, `tests/test_uebergabe_werkzeuge.py`,
  `tests/gui/szenario_werkzeugverwaltung.py`
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 5, Stufe 2,
  Entscheidung 10), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Neu → Durchmesser 12, Schneidenlänge 26 → in den leeren
Feldern steht grau „geschätzt: 50“ und „wie D: 12“ → Gesamtlänge 20 → rot
„Die Gesamtlänge (20 mm) ist kürzer als die Schneide (26 mm).“ → Gesamtlänge
83, Schaft-Ø 10 → Speichern und an CAM übergeben → im CAM-Job hat das
Werkzeug Länge 83 und Schaft 10.

### DONE
- Zwei freiwillige Felder; leer gilt die Schätzung wie bisher, und sie
  steht grau im Feld. Ältere Dateien ohne die Felder laden unverändert
  (0 = geschätzt), das Dateiformat bleibt 1.
- Der Eckradius (nur Torusfräser) steht jetzt als letztes Feld – so
  hinterlässt er ausgeblendet keine Lücke.
- Der Text nach der Übergabe sagt „wo die Felder leer sind, geschätzt“.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_werkzeuge` (speichern,
  alte Datei ohne Felder, Schätzung mit und ohne Schneidenlänge),
  `test_uebergabe_werkzeuge` (eingetragen 72/8, geschätzt 50/12 im
  ToolBit) grün.
- KI, Oberfläche 1.1.3: `szenario_werkzeugverwaltung` grün, Screenshot
  angesehen.
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.6.0, Push.

## P-2026-09-25-61 zustellung-in-die-operationen

### EINGELESEN
- Manuels Wunsch: „wenn ich ein Loch auffräsen will, dann einmal helikal
  ein Grundloch und dann ebenenweise mit voller Schneide“. In FreeCAD CAM
  macht das die Operation Adaptiv (Helix-Eintauchen bis zur Zustelltiefe,
  dann die Ebene ausräumen) – wenn Schrittweite und Zustelltiefe stimmen.
- FreeCAD 1.1.3 und Wochen-Build ausprobiert: Adaptiv hat `StepOver`
  (ganze Prozent) bzw. `StepOverPercent` (Kommazahl), Tasche und
  Planfräsen `StepOver`, alle `StepDown` – an dem eine Formel aus dem
  SetupSheet hängt.

### DATEIEN
- `camaddon/job_schnittwerte.py` (`zustellung()`, `operationen_mit()`,
  `setze(…, job)` → `Gesetzt`; „MillFacing“ des Wochen-Builds im
  Vorschlag)
- `camaddon/gui_job_schnittwerte.py` (Spalte „Schrittweite ·
  Zustelltiefe“, Haken, Meldung; Spalte „Werkzeug“ kürzer benannt)
- `help/de|en/werkzeuge.html` (Abschnitt „Ein Loch oder eine Tasche
  auffräsen“), `help/de|en/strategien.html` (Verweis darauf)
- `translations/de.json`, `translations/en.json` (dazu die englische
  Meldung ohne „1 tool controllers“)
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe 2 erweitert,
  Entscheidung 18), `docs/aufbau.md` (Modul, drei Stolpersteine),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Job mit Werkzeug-Controller „T3 Schruppen dynamisch“ (Ø-12-Fräser aus der
Bibliothek „CAM-Addon“, Einsatz 1,2 / 25 / 120 / 0,15) und einer Operation
Adaptiv mit diesem Controller → „Schnittwerte in den Job“ → in der Spalte
„Schrittweite · Zustelltiefe“ steht „Adaptiv: 10 % · 25 mm“ → Übernehmen →
Meldung „… dazu Schrittweite und Zustelltiefe in: Adaptiv“ → Adaptiv hat
Schrittweite 10 % und Zustelltiefe 25 mm; Strg+Z nimmt alles zurück.

### DONE
- **Welche Operation was bekommt:** Adaptiv ← „Schruppen dynamisch“ und
  „Schruppen“; Tasche, Taschenform, Planfräsen ← „Schruppen“; Nut ←
  „Vollnut“; Kontur ← nichts (mit ihr wird auch ausgeschnitten, in voller
  Nut). Schrittweite = ae in % von D, abgerundet (1.1.3: ganze Prozent),
  Zustelltiefe = ap.
- **Formel entfernt:** Die Zustelltiefe hängt in FreeCAD an „OpToolDiameter“
  aus dem SetupSheet; ohne das Entfernen stand nach dem Neuberechnen wieder
  12 mm da. Strg+Z bringt die Formel zurück (geprüft).
- Im Dialog zeigt eine Spalte vorher, was wohin kommt (Tooltip: der jetzige
  Wert); ein Haken schaltet es ab und wird gemerkt. Die Meldung nennt die
  Operationen beim Namen – ohne „1 Operationen“.
- Der Vorschlag des Einsatzes kennt jetzt auch „MillFacing“, das
  Planfräsen des Wochen-Builds.
- Hilfe: Schritt für Schritt „Ein Loch oder eine Tasche auffräsen“ mit
  Adaptiv.
- **Gefundene Fehler im eigenen Entwurf:** Zustelltiefe nach dem
  Neuberechnen wieder D (Formel, siehe oben); in 1.1.3 scheitert das
  Anlegen einer Operation ohne Oberfläche, wenn der Job mehrere
  Werkzeug-Controller hat – die Prüfung legt sie vorher an (Stolperstein).

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_job_schnittwerte` grün –
  Adaptiv bekommt 10 % bzw. 10,0 % und 25 mm, Tasche, Kontur und Nut
  bleiben, Nut mit Vollnut 3 mm, 0,88 mm → 7 % (1.1.3) bzw. 7,3 %, die
  Formel ist weg und kommt mit Strg+Z zurück, ohne Job bleiben die
  Operationen.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job`
  grün, Screenshots angesehen.
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.6.0, Push.

## P-2026-09-25-60 schruppwerte-planen

### EINGELESEN
- Manuels Wunsch zur Werkzeugverwaltung: „den maximalen Spanvolumen mit
  diesem Fräser erreichen“ – Ø 12 mit ae 1,2 / ap 25 / fz 0,15 statt Vollnut
  mit ap 3 / fz 0,05. Spezifikation W-002, Abschnitt 10, Stufe 3.
- W-001: Kennwerte der Maschine – Spindel „Drehzahl“ (U/min), Linearachse
  „VorschubMax“ (mm/min); die Werkzeugaufnahme verweist auf die Spindel,
  die das Werkzeug antreibt.

### DATEIEN
- `camaddon/schruppwerte.py` (neu: Planen, Grenzen der Maschine)
- `camaddon/gui_schruppwerte.py` (neu: Dialog)
- `camaddon/gui_schnittwerte.py` (Knopf „Schruppwerte planen…“,
  `einsatz_hinzufuegen()`)
- `camaddon/hilfe.py`, `help/de|en/schruppwerte.html` (neu)
- `translations/de.json`, `translations/en.json`
- `tests/test_schruppwerte.py`, `tests/gui/szenario_schruppwerte.py` (neu)
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe 3 gebaut,
  Entscheidungen 13–17), `docs/aufbau.md`, `CHATSTART.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Werkstoff 1.0503 (C45) → Schaftfräser Ø 12, z 3,
Schneidenlänge 26 mit Vollnut 12 / 3 / vc 120 / fz 0,05 → „Schruppwerte
planen…“ → vc 120, Spandicke 0,05, ap 24, ae höchstens 10 % stehen da; die
grüne Zeile ae 1,20 mm hat fz 0,083, vf 796, Q 22,9 und darunter steht,
dass die Grenze von 10 % nicht breiter zulässt → Spindelleistung 1,5 kW →
der Vorschlag rückt auf ae 0,88 mm, „Spindel voll ausgelastet“ → Feld
leeren → „Als Einsatz für 1.0503 übernehmen“ → in der Tabelle steht eine
neue Zeile „Schruppen dynamisch“ 1,2 / 24 / 120 / 0,083, und oben „Eigene
Werte für 1.0503“.

### DONE
- **Rechnen** (`schruppwerte.py`, ohne Oberfläche): je ae von 2 bis 50 % von
  D das fz für die gewünschte Spandicke (fz = h / sin φ), vf, Q, Leistung
  und Drehmoment aus kc1.1. Grenzen: ae in % von D (die Grenze selbst wird
  eine Zeile), Höchstdrehzahl (n gekappt, vc sinkt, wird gesagt),
  Höchstvorschub (vf gekappt, der Span wird dünner, wird gesagt),
  Spindelleistung × 80 % (die Grenze wird auf 0,01 mm gesucht und eine
  Zeile). Vorschlag = größtes Q innerhalb aller Grenzen, dazu der Grund,
  warum nicht breiter.
- **Ausgang** ist die gewählte Zeile, wenn sie schruppt und vc und fz hat,
  sonst dynamisch vor Vollnut vor Schruppen – eine Schlicht-Zeile taugt
  nicht als Spandicke.
- **Maschine:** Knopf „Von der Maschine“ (nur sichtbar, wenn ein offenes
  Dokument eine W-001-Maschine mit Werten hat): Drehzahl der Spindel, die
  ein Werkzeug antreibt (sonst die größte), kleinster Höchstvorschub der
  Linearachsen. Die Grenzen merkt sich der Planer.
- **Übernehmen:** die gewählte Zeile als „Schruppen dynamisch“, abgerundet;
  ohne eigene Werte für den Werkstoff werden sie angelegt (der Knopf sagt
  es: „Als Einsatz für 1.0503 übernehmen“).
- Hilfeseite mit Formel, Feldern, Tabelle, Beispiel und dem, was der Planer
  nicht weiß (Werkzeugsteifigkeit, Drehmoment).
- Entscheidungen 13–17 in der Spezifikation, zur Besprechung.
- **Gefundener Fehler im eigenen Entwurf:** Die Schlüssel der Felder
  standen als Variablen in `tr()` – test_sprache fand sie nicht. Jetzt
  feste Texte beim Aufruf.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_schruppwerte` grün –
  Vorschlag an der ae-Grenze (fz 0,0833, vf 795,8, Q 22,92), Grenze
  zwischen den Stufen (11 %), ohne Grenze bis D/2, Drehzahl-, Vorschub- und
  Leistungsgrenze (C45, 1,5 kW: Zeile an der Grenze, 0,01 mm mehr wäre zu
  viel), ohne kc1.1 keine Leistungsprüfung, Ausgangszeile, Grenzen einer
  Drehmaschine mit angetriebenem Werkzeug.
- KI, Oberfläche in **beiden** Versionen: `szenario_schruppwerte` grün,
  Screenshots angesehen (Vorschlag, Leistungsgrenze, Maschine am Anschlag,
  übernommen).
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.6.0, Push.

## P-2026-09-25-59 stand-nach-der-nacht

### EINGELESEN
- Arbeitsregeln Abschnitt 10: Zum Abschluss den Snapshot auf den Stand
  bringen, Erledigtes heraus, Links prüfen.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md` (Nächster Schritt: W-002 Stufen 1 und 2,
  Installation)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer den Snapshot liest, weiß, was auf Manuels Test wartet und wo die
Klickwege stehen.

### DONE
- Nächster Schritt nennt W-002 Stufen 1 und 2 (Klickwege P-46 bis -53) und
  die Installationszeile nach dem Öffentlichstellen (T-005).
- Stand dieser Nacht: P-2026-09-25-43 bis -59, Version 0.5.1, alle Prüfungen
  in 1.1.3 und im Wochen-Build grün (54 ok, 1 übersprungen: Export gibt es
  in 1.1.3 nicht).

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Manuels Rückmeldung zu W-002 und den Entscheidungen; Repository
  öffentlich stellen (T-005).

## P-2026-09-25-58 version-0-5-1

### EINGELESEN
- Arbeitsregeln Abschnitt 4: Korrektur → letzte Stelle. Neu seit 0.5.0:
  Update-Suche ohne Git (P-57).

### DATEIEN
- `package.xml` (0.5.1)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.5.1.

### DONE
- Version 0.5.0 → 0.5.1.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-25-57 update-ohne-git

### EINGELESEN
- Lücke aus P-2026-09-25-43: Eine mit der Zeile aus dem README (ohne Git)
  installierte Kopie meldete neue Versionen nicht selbst – nur der
  Addon-Manager zeigte sie. Die Update-Suche beim Start sagte bei
  „kein Git-Ordner“ nichts.

### DATEIEN
- `camaddon/aktualisierung.py` (ohne Git: Version per HTTPS aus der
  package.xml auf GitHub, Update per `installieren.py`; `KEIN_GIT_ORDNER`
  entfällt)
- `installieren.py` (`ziel=`: genau dieser Ordner)
- `camaddon/gui_aktualisierung.py` (Zweig „kein Git-Ordner“ entfällt)
- `translations/de.json`, `translations/en.json` (`update.kein_git_ordner`
  entfällt; Tooltip und Fehlertext nennen beide Wege)
- `README.md`, `CHATSTART.md`, `docs/aufbau.md`
- `tests/test_aktualisierung.py`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Mit der Zeile aus dem README installiert (öffentliches Repository): Gibt es
auf GitHub eine höhere Version, fragt FreeCAD beim nächsten Start „Jetzt
aktualisieren?“; nach dem Klick und einem Neustart läuft die neue Version.

### DONE
- Ohne `.git` im Addon-Ordner liest die Suche
  `https://raw.githubusercontent.com/…/main/package.xml` (Zeitlimit wie bei
  Git) und vergleicht die Versionen wie bisher Zahl für Zahl. Fehler (kein
  Netz, privat = 404) ergeben `FEHLER` wie bei Git: beim Start nur eine
  Zeile im Report-Fenster, von Hand ein Fenster.
- „Jetzt aktualisieren“ ohne Git lädt `installieren.py` **aus dem
  Addon-Ordner** und ersetzt den Ordner durch das ZIP von GitHub – dieselbe
  Datei und derselbe sichere Tausch wie bei der Installation.
- Keine neue Ausnahme von „keine Aufrufe externer Programme“: HTTPS läuft
  über Pythons urllib.

### TEST
- KI, FreeCADCmd in beiden Versionen: `test_aktualisierung` (neu: ohne Git
  gleiche Version, neue Version, Update per ZIP, danach aktuell, GitHub
  nicht erreichbar; die Git-Fälle wie bisher), `test_installieren`,
  `test_sprache` grün.
- KI, Oberfläche (Wochen-Build): `szenario_update`, `szenario_erster_start`
  grün.
- Der Weg gegen das echte GitHub geht erst, wenn das Repository öffentlich
  ist (T-005).

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-25-56 entscheidungen-stufe-2

### EINGELESEN
- Manuel: „teil mir deine Entscheidungen mit, die kann man morgen ja nochmal
  besprechen“. Beim Bauen von Stufe 2 (P-52, P-53) sind vier dazugekommen.

### DATEIEN
- `docs/spezifikation_werkzeugverwaltung.md` (Abschnitt 11, Entscheidungen
  9 bis 12)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Alle Entscheidungen zu W-002 stehen mit Alternative in Abschnitt 11 der
Spezifikation.

### DONE
- Eigene Bibliothek „CAM-Addon“, vollständig ersetzt; Gesamtlänge und Schaft
  geschätzt; Eintauchvorschub ⅓; Einsatz-Vorschlag nach Name, dann
  Operation.

### TEST
- Nur Doku, kein Testlauf.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-25-55 version-0-5-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: neue Funktion → mittlere Stelle. Neu seit
  0.4.0: Übergabe an CAM (P-52), Schnittwerte in den Job (P-53).

### DATEIEN
- `package.xml` (0.5.0, Beschreibung)
- `README.md` („Was es kann“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.5.0.

### DONE
- Version 0.4.0 → 0.5.0 für P-2026-09-25-52 bis -54.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen.

### NEXT
- Push; Bericht an Manuel.

## P-2026-09-25-54 gui-teile-gemeinsam

### EINGELESEN
- Beim Bauen von W-002 aufgefallen (Arbeitsregeln: notieren, eigener
  Patch, möglichst gleich danach): `_fett`, `_knopf`, `_mit_einheit`, die
  rote Hinweiszeile und das Grau für gerechnete Werte standen in bis zu
  vier Modulen der Werkzeugverwaltung.

### DATEIEN
- `camaddon/gui_teile.py` (neu)
- `camaddon/gui_werkzeuge.py`, `camaddon/gui_werkstoffe.py`,
  `camaddon/gui_schnittwerte.py`, `camaddon/gui_job_schnittwerte.py`
- `docs/aufbau.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nichts sichtbar anders: Werkzeugverwaltung, Werkstoffe, Vergleich und
„Schnittwerte in den Job“ sehen aus und verhalten sich wie vorher.

### DONE
- Reines Zusammenlegen. Bewusst nicht angefasst: die ähnlichen Helfer in
  `gui_maschine.py` und `gui_details.py` (W-001) – andere Signaturen, und
  dort gibt es keinen Anlass, etwas zu ändern.
- Gefunden von ruff: Eine Schleifenvariable `knopf` hätte die neue Funktion
  `knopf()` verdeckt – umbenannt.

### TEST
- KI, Oberfläche (Wochen-Build): alle sechs Szenarien der
  Werkzeugverwaltung grün, Screenshot verglichen.

### NEXT
- Version 0.5.0, alle Prüfungen, Push.

## P-2026-09-25-53 schnittwerte-in-den-job

### EINGELESEN
- W-002, Spezifikation Abschnitt 10, Stufe 2, zweiter Teil: In FreeCAD
  1.1.3 – Manuels Version – kommen die Schnittwert-Vorschläge am Werkzeug
  nicht an (P-2026-09-25-52). Damit er die Werte trotzdem in einen Job
  bekommt, setzt das Addon die Werkzeug-Controller selbst.

### DATEIEN
- `camaddon/job_schnittwerte.py` (neu)
- `camaddon/gui_job_schnittwerte.py` (neu: Befehl und Dialog)
- `camaddon/gui_werkzeuge.py` (`werkstoffe_anbieten()` als Funktion, damit
  der neue Dialog dieselbe Werkstoff-Auswahl hat)
- `camaddon/gui_start.py` (Befehl, Werkzeugleiste)
- `resources/icons/schnittwerte_job.svg` (neu)
- `help/de|en/werkzeuge.html` (Abschnitt „Schnittwerte in den Job“)
- `translations/de.json`, `translations/en.json`
- `tests/test_job_schnittwerte.py`, `tests/gui/szenario_schnittwerte_job.py`
  (neu)
- `docs/spezifikation_werkzeugverwaltung.md`, `docs/aufbau.md`
  (Module, Stolperstein), `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
CAM-Job mit Rohteil-Werkstoff X5CrNi18-10 und einem Werkzeug-Controller
„T3 Schruppen dynamisch“ mit dem Ø-12-Fräser aus der Bibliothek „CAM-Addon“
→ Werkzeugleiste „Schnittwerte in den Job“ → Werkstoff 1.4301 ist gewählt,
der Einsatz „Schruppen dynamisch“ vorgeschlagen, n 3183 und vf 1432 stehen
da → Übernehmen → der Werkzeug-Controller hat diese Werte; Strg+Z nimmt sie
zurück.

### DONE
- **Werkstoff vom Rohteil:** `Stock.ShapeMaterial` (in 1.1.3 und im
  Wochen-Build vorhanden) → Werkstoffnummer → Werkstoff der
  Werkzeugverwaltung; sonst „Alle Werkstoffe“, im Dialog änderbar.
- **Werkzeug zum TC:** über die ToolBit-ID `camaddon_<Kennung>` (steht nach
  der Übergabe im ToolBit, Eigenschaft `ToolBitID`), sonst über T-Nummer
  und Durchmesser. Fremde Werkzeuge: „– nicht in der Werkzeugverwaltung“,
  nicht wählbar, bleiben unberührt.
- **Einsatz vorschlagen:** Name des TC enthält den Namen einer Zeile, sonst
  nach der Operation, die den TC benutzt (Adaptiv → dynamisch, Tasche und
  Planfräsen → Schruppen, Kontur → Schlichten, Nut → Vollnut, Bohren →
  Bohren), sonst die erste Zeile. Zeilen ohne vc/fz werden nicht
  vorgeschlagen („– nicht ändern“).
- **Setzen:** Drehzahl, Vorschub, Eintauchvorschub = ⅓ (wie FreeCADs
  Vorgabe für Presets), beim Bohrer der volle Vorschub; alles in **einer**
  Transaktion (Arbeitsregeln Abschnitt 7: Strg+Z muss gehen). Ohne vc/fz
  wird nichts gesetzt, lieber als 0 U/min.
- Befehl aktiv, sobald das Dokument einen CAM-Job hat.
- **Gefundene Fehler im eigenen Entwurf:** Die Prüfung hing von der
  eingestellten Sprache ab (der TC-Name ist deutsch) – setzt jetzt Deutsch.
  In 1.1.3 stand „OK“ hinter einem Fortschrittsbalken ohne Zeilenende und
  wurde nicht erkannt – Leerzeile davor, als Stolperstein notiert.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_job_schnittwerte` grün –
  echter Job mit Quader, Rohteil-Werkstoff 1.4301, TC mit Werkzeug aus der
  Bibliothek und TC mit fremdem Bohrer (T7, Ø 8,5), Vorschläge, Setzen
  (2122 U/min, 318 und 105 mm/min; Bohrer 2996 U/min, 599 mm/min
  senkrecht), unvollständiger Einsatz übersprungen, Strg+Z.
- KI, Oberfläche in **beiden** Versionen: `szenario_schnittwerte_job` grün.
  Screenshot angesehen.
- Manuel: offen.

### NEXT
- Alle Prüfungen, Version 0.5.0, Push. Dann Manuels Rückmeldung.

## P-2026-09-25-52 werkzeuge-an-cam

### EINGELESEN
- W-002, Spezifikation Abschnitt 10, Stufe 2 (Übergabe an CAM). Manuel:
  „mach so viel fertig wie du kannst“ – ohne Übergabe bleibt die
  Werkzeugverwaltung ein Rechner neben CAM.

### DATEIEN
- `camaddon/uebergabe_werkzeuge.py` (neu)
- `camaddon/gui_werkzeuge.py` (Knopf „Speichern und an CAM übergeben“,
  Rückmeldung)
- `help/de|en/werkzeuge.html` (Abschnitt „An CAM übergeben“)
- `translations/de.json`, `translations/en.json`
- `tests/test_uebergabe_werkzeuge.py`, `tests/gui/szenario_an_cam.py` (neu)
- `docs/spezifikation_werkzeugverwaltung.md` (Stufe 2: was gebaut ist),
  `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Speichern und an CAM übergeben“ → Rückmeldung
„Übergeben: …“; danach in einem CAM-Job „Werkzeug hinzufügen“ → Bibliothek
„CAM-Addon“ zeigt die Werkzeuge mit ihren T-Nummern und Durchmessern. Im
Wochen-Build schlägt der Knopf für Vorschub und Drehzahl im
Werkzeug-Controller bei Rohteil-Werkstoff X5CrNi18-10 unsere Werte für
1.4301 vor.

### DONE
- **FreeCAD-Check:** 1.1.3 und der Wochen-Build haben dieselbe
  Asset-Verwaltung (`Path.Tool.camassets.cam_assets`), dasselbe Format für
  ToolBits (`.fctb`, Version 2) und Bibliotheken (`.fctl`). Nur der
  Wochen-Build kennt „Presets“ und behält unbekannte Schlüssel beim
  Speichern (`_extra_attrs`). FreeCADs Werkstoffkarten findet das Addon
  über die Werkstoffnummer (`PhysicalProperties["MaterialNumber"]`), etwa
  1.4301 → „X5CrNi18-10“.
- **Übergabe:** je Werkzeug ein ToolBit `camaddon_<Kennung>` (Form nach Art:
  Endmill, Bullnose, Ballend, Chamfer, Drill; Diameter, Flutes,
  CuttingEdgeHeight, Material, SpindleDirection, Chipload aus der ersten
  Zeile „für alle“), dazu die Bibliothek „CAM-Addon“ mit den T-Nummern.
  Geschrieben über `cam_assets.add_raw` – dort, wo der Benutzer seine
  CAM-Werkzeuge eingestellt hat.
- **Presets** (je Einsatz mit vc oder fz): Werkstoff-Hinweis mit UUID der
  FreeCAD-Werkstoffkarte gleicher Nummer, sonst mit dem Kurznamen;
  Bearbeitungsart nach Einsatz; Notiz mit ae und ap. „Für alle“ ohne
  Werkstoff-Hinweis = gilt für jeden Werkstoff.
- **Ersetzen statt anhäufen:** Eine neue Übergabe schreibt alle ToolBits neu
  und entfernt `camaddon_…`-Werkzeuge, die es in der Werkzeugverwaltung nicht
  mehr gibt. Fremde Werkzeuge bleiben.
- **Annahmen** (in Rückmeldung und Hilfe genannt): Gesamtlänge =
  Schneidenlänge + 2 × D (mindestens 3 × D), Schaft = D, Eckradius ohne
  Angabe = D/10, Fasenfräser 90°, Bohrer 118°.
- Knopf **„Speichern und an CAM übergeben“** unten links; speichert zuerst
  (die Übergabe zeigt immer den gespeicherten Stand). Rückmeldung je
  Version: Wochen-Build mit Anzahl der Vorschläge und wo man sie findet,
  1.1.3 mit dem Satz, dass Schnittwerte erst mit der nächsten Version
  übernommen werden.
- Bewusst noch nicht: Werkzeug-Controller eines Jobs direkt setzen (für
  1.1.3), Felder für Gesamtlänge und Schaft.

### TEST
- KI, FreeCADCmd in **beiden** Versionen: `test_uebergabe_werkzeuge` grün –
  FreeCAD lädt Bibliothek (T3, T5, T7) und Werkzeuge mit Durchmesser,
  Schneiden, Schneidenlänge, Eckradius, Schneidstoff; ohne Durchmesser
  übersprungen; zweite Übergabe entfernt den gelöschten, das fremde bleibt.
  Im Wochen-Build zusätzlich: vier Presets am Fräser, und FreeCADs eigener
  Vorschlag (`FeedsSpeeds.resolve`) liefert für 1.4301/Nut vc 80 und für
  andere Werkstoffe 120 bei 3183 U/min.
- KI, Oberfläche in beiden Versionen: `szenario_an_cam` grün, Rückmeldungen
  angesehen.
- Manuel: offen – vor allem, ob die Bibliothek im Job so erscheint, wie er
  sie erwartet.

### NEXT
- Werkzeug-Controller eines Jobs aus der Tabelle setzen (1.1.3) – oder
  Manuels Rückmeldung.

## P-2026-09-25-51 version-0-4-0

### EINGELESEN
- Arbeitsregeln Abschnitt 4: Ein Push mit neuer Funktion zählt die mittlere
  Stelle der Version hoch. Die Werkzeugverwaltung (P-46 bis P-50) ist neu.

### DATEIEN
- `package.xml` (Version 0.4.0, Beschreibung nennt die Werkzeugverwaltung)
- `README.md` (Abschnitt „Was es kann“)
- `docs/STATUS_SNAPSHOT.md` (nächster Schritt: Manuels Test von W-002)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach dem Update zeigt „Über das CAM-Addon“ die Version 0.4.0, und die
Update-Suche meldet 0.4.0 als neue Version.

### DONE
- Version 0.3.9 → 0.4.0 für alle Patches seit dem letzten Push
  (P-2026-09-25-43 bis -50).
- README: kurze Liste, was das Addon kann – für Tester, sobald das
  Repository öffentlich ist.

### TEST
- Vor dem Push `scripts/alle_tests.sh` in beiden Versionen (Ergebnis im
  Bericht an Manuel).

### NEXT
- Push; danach W-002 Stufe 2 oder Manuels Rückmeldung.

## P-2026-09-25-50 werkstoffe-eigene

### EINGELESEN
- W-002, Spezifikation Abschnitt 4: eigene Werkstoffe; mitgelieferte
  schreibgeschützt, „Als eigenen kopieren“.

### DATEIEN
- `camaddon/gui_werkstoffe.py` (neu: Fenster „Werkstoffe“ und
  „Werkstoff bearbeiten“)
- `camaddon/gui_werkzeuge.py` (Knopf „Werkstoffe…“, Wahl übernehmen)
- `help/de|en/werkstoffe.html` (Abschnitt „Die ganze Liste und eigene
  Werkstoffe“)
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_werkstoffe.py` (neu)
- `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → „Werkstoffe…“ → „Neu…“ → Kurzname „Buche“, Gruppe
„Holz“ tippen, ISO N, OK → „Buche“ steht kursiv oben in der Liste; Fenster
schließen → in der Werkzeugverwaltung ist „Buche · Holz“ gewählt, und nach OK
und Wiederöffnen ist sie noch da.

### DONE
- **Fenster „Werkstoffe“:** alle Werkstoffe als Tabelle (ISO-Kästchen,
  Nummer, Kurzname, Gruppe mit Zustand, Härte, alte Namen), Suche wie in
  der Auswahl, Filter nach ISO-Gruppe, darunter alle Angaben des gewählten
  (mit kc1.1/mc, falls bekannt). Eigene kursiv ganz oben.
- **Eigene Werkstoffe:** Neu…, Als eigenen kopieren, Bearbeiten… (auch
  Doppelklick), Löschen (Rückfrage; nennt die Werkzeuge mit eigenen
  Schnittwerten dafür – die gehen mit). Mitgelieferte schreibgeschützt.
- **Bearbeiten:** Kurzname Pflicht (OK gesperrt, Hinweis am Feld); Gruppe
  und Zustand aus der Liste oder frei getippt – ein Text aus der Liste wird
  als Schlüssel gespeichert und folgt so der Sprache. Zusammensetzung,
  Härte und Zugfestigkeit werden im Format der Oberfläche gezeigt und mit
  Punkt gespeichert, wie in der mitgelieferten Liste.
- Wählt man im Fenster einen Werkstoff und schließt es, ist er auch in der
  Werkzeugverwaltung gewählt. Gespeichert wird mit deren OK/Übernehmen.
- **Gefundene Fehler im eigenen Entwurf:** Die ISO-Spalte zeigte Kästchen
  und Buchstaben doppelt; das Bearbeiten-Feld zeigte „1.45–1.60“ statt
  „1,45–1,60“.

### TEST
- KI, Oberfläche (Wochen-Build): `szenario_werkstoffe` grün – Suche „1.23“
  (6 Treffer), Filter S (3), Kopie, Bearbeiten mit Komma → gespeichert mit
  Punkt, Neu mit Pflichtfeld, Löschen mit Rückfrage samt Schnittwerten,
  Wahl wandert in die Werkzeugverwaltung, OK speichert. Screenshots
  angesehen.
- Manuel: offen.

### NEXT
- Alle Prüfungen in beiden Versionen, Version 0.4.0, Push.

## P-2026-09-25-49 strategien-vergleichen

### EINGELESEN
- W-002, Spezifikation Abschnitt 7 und viertes Akzeptanzkriterium aus
  Abschnitt 12. Manuels Beispiel: Ø 12, ae 1,2 / ap 25 / fz 0,15 statt
  ae 100 % / ap 3 / fz 0,05 – „geht schneller, weniger Verschleiß … dass
  man im Nachhinein mit den Werten auch eine Beurteilung für verschiedene
  Strategien herausziehen kann“.

### DATEIEN
- `camaddon/schnittdaten.py` (Schneidenweg je cm³, spezifische
  Schnittkraft, Schnittleistung, Kennzahlen, Urteil)
- `camaddon/gui_strategie.py` (neu: Dialog mit Balken und Urteil)
- `camaddon/gui_schnittwerte.py` (Knopf „Strategien vergleichen…“,
  Werkstoff für die Leistung)
- `camaddon/gui_werkzeuge.py`, `camaddon/gui_zahlen.py` (`dezimal()` jetzt
  gemeinsam in gui_zahlen – gui_strategie braucht es auch, ein Import aus
  gui_werkzeuge wäre ein Kreis)
- `camaddon/hilfe.py`, `help/de|en/strategien.html` (neu),
  `help/de|en/schnittwerte.html` (Verweis darauf)
- `translations/de.json`, `translations/en.json`
- `tests/test_schnittdaten.py`, `tests/gui/szenario_strategien.py` (neu)
- `docs/aufbau.md` (Module, drei neue Stolpersteine), `CHATSTART.md`,
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Ø-12-Fräser mit Vollnut und Schruppen dynamisch →
„Strategien vergleichen…“ → das Urteil sagt, dass dynamisches Schruppen
2,5-mal so viel je Minute abträgt und jede Stelle der Schneide 12,2-mal
weniger Weg durchs Material fährt, und warum (25 statt 3 mm Schneide,
10 statt 50 % der Umdrehung im Material).

### DONE
- **Kennzahlen** je Einsatz: Q, Zeit für 100 cm³, Schneidenweg je cm³,
  genutzte Schneide (ap von der Schneidenlänge), Anteil der Umdrehung im
  Material, größte Spandicke, Schnittleistung und Drehmoment (nur mit
  kc1.1 des Werkstoffs).
- **Schneidenweg je cm³** = D · φ / (2 · ae · ap · fz · z) – Herleitung im
  Docstring und auf der Hilfeseite, ausdrücklich als Faustregel (gleiches
  vc angenommen).
- **Dialog:** A (orange) gegen B (blau), je Kennzahl zwei Balken mit
  Wert; Vorwahl Vollnut gegen Schruppen dynamisch, sonst die ersten beiden.
  Darunter das **Urteil in Sätzen**, die Namen in der Farbe ihres Balkens:
  wer mehr abträgt und um welchen Faktor, wie viel weniger (oder mehr)
  Schneidenweg, warum (genutzte Schneide, Eingriff), Leistung, zu dünner
  Span. Nur Aussagen, die die Zahlen tragen; unter 10 % Unterschied „etwa
  gleich“.
- **Hilfeseite „Strategien vergleichen“:** die Zahlen, warum der
  Schneidenweg, Manuels Beispiel als Tabelle, was daraus folgt
  (Konturen/Taschen dynamisch = „Adaptiv“ in FreeCAD CAM, Löcher: erst
  helikal ein Grundloch, dann ebenenweise mit großem ap; Vollnut nur wo
  nötig; Schlichten mit voller Wandhöhe), Grenzen der Faustregel.
- **Gefundener Fehler im eigenen Entwurf:** Der Kopf des Vergleichs zeigte
  „Werkstoff: 1,0503“ – `dezimal()` hielt die Werkstoffnummer für eine
  Kommazahl. Werkstofftexte laufen jetzt nie durch `dezimal()`; das
  Szenario prüft es. Als Stolperstein in docs/aufbau.md.
- Bewusst nicht: ein Standzeitmodell (Taylor) – dafür fehlen die Werte
  (Entscheidung 6 der Spezifikation).

### TEST
- KI, FreeCADCmd (Wochen-Build): `test_schnittdaten` (Schneidenweg 3,49 und
  0,29 m, Kennzahlen, Urteil mit Faktoren 2,5 und 12,2, unabhängig von der
  Reihenfolge, Leistung mit kc1.1, unvollständige Werte), `test_sprache`,
  `test_hilfe` grün.
- KI, Oberfläche (Wochen-Build): `szenario_strategien` grün – Vorwahl,
  Urteil, Werte, Kopf mit „1.0503“, zweiter Vergleich Schlichten gegen
  Vollnut. `szenario_schnittwerte` weiter grün. Screenshots angesehen.
- Manuel: offen.

### NEXT
- Eigene Werkstoffe anlegen (Spezifikation Abschnitt 4).

## P-2026-09-25-48 eingriff-im-bild

### EINGELESEN
- W-002, Spezifikation Abschnitt 6.2: Bild des Eingriffs, Werte zur
  gewählten Zeile, Spandicke ausgleichen; drittes Akzeptanzkriterium aus
  Abschnitt 12. Arbeitsregeln Abschnitt 8: „Zeigen statt beschreiben“,
  Animationen ohne Text.

### DATEIEN
- `camaddon/schnittdaten.py` (Eingriffswinkel, größte und mittlere
  Spandicke, fz für eine gewünschte Spandicke, Mindestspandicke für den
  Hinweis)
- `camaddon/gui_eingriff.py` (neu: das Bild)
- `camaddon/gui_schnittwerte.py` (Bild, Werte in Worten, Ausgleich,
  Hinweis „Span zu dünn“)
- `help/de|en/schnittwerte.html` (Abschnitt „Eingriff und Spandicke“)
- `translations/de.json`, `translations/en.json`
- `tests/test_schnittdaten.py`, `tests/gui/szenario_schnittwerte.py`
- `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In der Zeile „Schruppen dynamisch“ des Ø-12-Fräsers ae 1,2 tippen → das Bild
zeigt einen schmalen roten Bogen, daneben „Eingriff 37° – jeder Zahn ist
10 % der Umdrehung im Material“; bei „Vollnut“ ist der Bogen ein Halbkreis
und es steht 180° da.

### DONE
- **Bild** (ohne Text): links von oben Fräser, Material und roter
  Eingriffsbogen, Vorschubpfeil; bei der Vollnut Material auf beiden
  Seiten. Rechts von der Seite Schaft, Schneide mit angedeuteten Wendeln,
  Werkstück so hoch wie ap und rot der arbeitende Teil der Schneide.
  Schneidenlänge unbekannt: Schneide gestrichelt.
- **In Worten daneben:** Eingriffswinkel und Anteil der Umdrehung, ae in %
  von D, ap in × D und in % der Schneide, größte und mittlere Spandicke.
- **Spandicke ausgleichen** (nur bei ae < D/2): Feld „gewünscht“ mit der
  jetzigen größten Spandicke vorbelegt, daneben das fz, das die
  gewünschte ergibt, Knopf „fz übernehmen“. Entscheidung: kein Knopf
  „fz ausgleichen“ ohne Zielwert – der würde fz bei jedem Druck weiter
  anheben. Mit Zielwert ist der Knopf beliebig oft ohne Überraschung.
- **Hinweis**, wenn die größte Spandicke unter 0,01 mm liegt (Schneide
  reibt).
- Beim Bohrer kein Bild und keine Eingriffswerte.
- **Gefundener Fehler im eigenen Entwurf:** Das Feld für die Spandicke war
  zu schmal und zeigte „090“ statt „0,090“.

### TEST
- KI, FreeCADCmd (Wochen-Build): `test_schnittdaten` mit Eingriffswinkel
  (180°, 90°, 36,87°), Spandicken und Ausgleich grün.
- KI, Oberfläche (Wochen-Build): `szenario_schnittwerte` grün – Werte im
  Text, Ausgleich 0,1 mm → fz 0,1667, Vollnut ohne Ausgleich. Bilder für
  dynamisch und Vollnut angesehen.
- Manuel: offen.

### NEXT
- Strategien vergleichen (Spezifikation Abschnitt 7).

## P-2026-09-25-47 schnittwerte-je-werkstoff

### EINGELESEN
- W-002, Spezifikation Abschnitt 6 (Schnittwerte je Werkstoff, Einsätze,
  Formeln) und das zweite Akzeptanzkriterium aus Abschnitt 12.
- Manuel: „wenn ich vc eingeben will, vc haben“, „für jeden Werkstoff einzeln
  einstellbar … auch so, dass man für alle die Schnittwerte gleich setzen
  kann“, „ae und ap … als Tabelle“.

### DATEIEN
- `camaddon/werkzeuge.py` (Einsatz, Einsatzarten, Vorlagen, Schnittwerte je
  Werkstoff am Werkzeug, Speichern)
- `camaddon/schnittdaten.py` (neu: n, vf, Q)
- `camaddon/gui_schnittwerte.py` (neu: Tabelle, Zustand, Knöpfe, Hinweise)
- `camaddon/gui_werkzeuge.py` (Formular in zwei Spalten, Tabelle darunter,
  Fenster größer)
- `camaddon/hilfe.py`, `help/de|en/schnittwerte.html` (neu)
- `translations/de.json`, `translations/en.json`
- `tests/test_schnittdaten.py` (neu), `tests/test_werkzeuge.py`,
  `tests/gui/szenario_schnittwerte.py` (neu)
- `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Werkzeugverwaltung → Schaftfräser Ø 12 (3 Schneiden) wählen, Werkstoff
„Alle Werkstoffe“, „+ Einsatz“ → Vollnut, ap 3, vc 120, fz 0,05 eintragen →
grau daneben n 3183, vf 477, Q 17,2; Werkstoff 1.4301 wählen → dieselben
Werte grau und „Eigene Werte für 1.4301 anlegen“; danach vc 80 → n 2122,
und bei C45 stehen weiter 120.

### DONE
- **Tabelle je Einsatz:** Einsatz (Name änderbar), ae, ap, vc, fz
  eingegeben; n, vf, Q gerechnet und grau. Beim Bohrer ohne ae/ap, dafür f je
  Umdrehung (gespeichert wird fz = f / z, damit überall dieselbe Formel
  gilt).
- **„+ Einsatz“** mit Menü: Vollnut (ae = D, ap = D/2), Schruppen (D/2, D/2),
  Schruppen dynamisch (10 % D, Schneidenlänge höchstens 2 × D), Schlichten
  (2 % D, Schneidenlänge), beim Bohrer „Bohren“, immer „Eigener Einsatz“.
  vc und fz bleiben leer (Entscheidung 5 der Spezifikation).
- **Je Werkstoff oder für alle:** „Alle Werkstoffe“ bearbeitet die
  gemeinsame Tabelle. Ein Werkstoff ohne eigene Werte zeigt sie grau und
  nicht änderbar, mit „Eigene Werte für … anlegen“ (Kopie). Mit eigenen
  Werten: „Eigene Werte löschen“ (Rückfrage).
- **Hinweise zur gewählten Zeile:** ae größer als D, ap länger als die
  Schneide, vc/fz fehlen.
- Spaltenköpfe mit Einheit, jeder mit Tooltip samt Formel; Hilfeseite
  „Schnittwerte“ mit Beispiel und Orientierungswerten je ISO-Gruppe (als
  solche gekennzeichnet: „Der Katalog deines Fräsers geht immer vor.“).
- Werkzeugfelder in zwei Spalten, damit die Tabelle Platz hat; das Fenster
  ist jetzt 1100 × 760 Pixel groß.
- **Gefundene Fehler im eigenen Entwurf:** „+ Einsatz“ als QToolButton
  schob den Menüpfeil in den Text; jetzt ein QPushButton mit Menü.
- Bewusst nicht: geerbte Werte beim Tippen automatisch zu eigenen machen –
  das würde still eine zweite Tabelle anlegen. Der Knopf macht es sichtbar.

### TEST
- KI, FreeCADCmd (Wochen-Build): `test_schnittdaten` (Manuels Beispiel,
  Bohren, fehlende Werte), `test_werkzeuge` (Vorlagen, Erben, eigene Werte
  unabhängig, Speichern, Kopie), `test_sprache`, `test_hilfe` grün.
- KI, Oberfläche (Wochen-Build): `szenario_schnittwerte` grün – fz per
  Tastatur mit Komma in die Zelle getippt, Enter schließt den Dialog nicht,
  gerechnete Werte, Hinweis bei ap > Schneide, geerbt grau, eigene Werte,
  C45 unverändert, Bohrer, OK speichert. `szenario_werkzeugverwaltung`
  weiter grün. Screenshots angesehen.
- Manuel: offen.

### NEXT
- Bild des Eingriffs und Spandicke (Abschnitt 6.2).

## P-2026-09-25-46 werkzeugverwaltung-werkzeuge

### EINGELESEN
- W-002, Spezifikation Abschnitte 4, 5, 8, 9 und das erste
  Akzeptanzkriterium aus Abschnitt 12.

### DATEIEN
- `daten/werkstoffe.json` (neu: 51 Werkstoffe aller sechs ISO-Gruppen)
- `camaddon/werkstoffe.py` (neu), `camaddon/werkzeuge.py` (neu),
  `camaddon/gui_werkzeuge.py` (neu)
- `camaddon/gui_start.py` (Befehl, Werkzeugleiste), `camaddon/hilfe.py`
  (Themen „werkstoffe“, „werkzeuge“)
- `resources/icons/werkzeugverwaltung.svg` (neu)
- `help/de|en/werkstoffe.html`, `help/de|en/werkzeuge.html` (neu)
- `translations/de.json`, `translations/en.json` (Texte der
  Werkzeugverwaltung; „Über“ nennt sie)
- `tests/test_werkstoffe.py`, `tests/test_werkzeuge.py`,
  `tests/gui/szenario_werkzeugverwaltung.py` (neu)
- `docs/aufbau.md`, `CHATSTART.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
CAM → Werkzeugverwaltung → im Feld „Werkstoff“ „1.43“ tippen und 1.4301
wählen → darunter stehen Zusammensetzung und Härte; „Neu“ → Durchmesser 12,
Schneiden 3, OK → nach erneutem Öffnen steht „T1 Schaftfräser Ø 12 · z 3 ·
VHM“ in der Liste. Manuel versteht das Fenster ohne Erklärung.

### DONE
- **Werkstoffliste:** 51 Einträge (Stahl, Edelstahl, Guss, Aluminium,
  Kupfer, Messing, Bronze, Titan, Nickel, Kunststoffe; Werkzeugstahl
  geglüht und gehärtet als zwei Einträge). Je Eintrag Nummer, Kurzname,
  Gruppe, Zustand, ISO-Gruppe, alte Namen („V2A“, „GG-25“, „Ms 58“,
  „AISI D2“), Zusammensetzung, Härte, Zugfestigkeit; kc1.1 und mc nur, wo
  der Wert aus dem Tabellenbuch sicher ist (sonst 0 = unbekannt).
- **Anzeige** wie in der Werkstatt: „1.4301  X5CrNi18-10 · Edelstahl,
  austenitisch (V2A, AISI 304)“, davor ein Kästchen in der ISO-Farbe.
  Darunter Zusammensetzung, Härte, Zugfestigkeit, ISO-Gruppe; Zahlen im
  Format der Oberfläche (17,5–19,5).
- **Suche** durch Tippen ins Feld (Nummer, Kurzname, Gruppe, alter Name).
- **Werkzeuge:** Liste nach Nummer, Neu / Kopieren / Löschen (mit
  Rückfrage), Felder Nummer, Art, Durchmesser, Schneiden, Schneidenlänge,
  Eckradius (nur Torusfräser), Schneidstoff, Bezeichnung. Hinweise sofort am
  Feld: fehlender Durchmesser, doppelte Nummer.
- **Speichern** wie FreeCADs Einstellungen: OK, Übernehmen, Abbrechen (fragt
  nach). Datei `CamAddon/werkzeugverwaltung.json` im Benutzerordner, erst in
  eine Zwischendatei, die vorige Fassung als `.bak`. Eine unlesbare Datei
  wird beiseitegelegt und gemeldet, nichts gelöscht.
- Zuletzt gewählter Werkstoff und zuletzt gewähltes Werkzeug bleiben
  gemerkt (Parameter `WvWerkstoff`, `WvWerkzeug`).
- **Gefundene Fehler im eigenen Entwurf** (im Szenario):
  - Enter in einem Feld schloss den Dialog: Die Knopfleiste macht OK beim
    Zeigen selbst zum Standardknopf, `setDefault(False)` vorher hilft nicht.
    Der Dialog hält Enter jetzt in `keyPressEvent` an (wie B-005).
  - Doppelte Klammern in der Anzeige („(Ck45 (C45E = 1.1191))“): alte
    Namen vereinfacht, US-Bezeichnungen einheitlich mit „AISI“.
  - Der Hinweis „T1 gibt es schon: T1 …“ nannte die Nummer doppelt; jetzt
    „T1 ist schon vergeben: Schaftfräser Ø 12“.
- Bewusst nicht in diesem Patch: Schnittwerte (nächster Patch), eigene
  Werkstoffe anlegen (eigener Patch; die Bibliothek kann sie schon
  speichern).
- Abweichung von FreeCAD-Gewohnheiten: keine. Die Knöpfe OK / Übernehmen /
  Abbrechen sind die von Qt und erscheinen in der Sprache von FreeCAD.

### TEST
- KI, FreeCADCmd (Wochen-Build): `test_werkstoffe`, `test_werkzeuge`,
  `test_sprache`, `test_hilfe` grün.
- KI, Oberfläche in beiden Versionen (1.1.3 und Wochen-Build):
  `szenario_werkzeugverwaltung` grün – Suche „1.43“ per Tastatur, Wahl aus
  den Vorschlägen, Info mit deutschem Dezimalkomma, zwei Werkzeuge, Enter
  im Feld, doppelte Nummer, OK speichert, Wiederöffnen, Abbrechen mit
  Rückfrage und „Verwerfen“. Screenshots angesehen.
- Manuel: offen.

### NEXT
- Schnittwerte je Werkstoff und Einsatz (Spezifikation Abschnitt 6).

## P-2026-09-25-45 zahlenfelder-gemeinsam

### EINGELESEN
- Die Werkzeugverwaltung (W-002) braucht dieselben Zahlenfelder wie „Maschine
  bearbeiten“: deutsches Format ohne Tausenderpunkte (B-004), leer heißt
  „unbekannt“. Die Helfer lagen privat in `gui_details.py`.

### DATEIEN
- `camaddon/gui_zahlen.py` (neu: `zahlenformat`, `Zahlenpruefer`,
  `zahl_lesen`, `zahl_zeigen`, dazu die zwei Grenzen)
- `camaddon/gui_details.py` (benutzt sie von dort)
- `docs/aufbau.md` (Modultabelle)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nichts sichtbar anders: „Maschine bearbeiten“ zeigt und liest Zahlen wie
vorher („30000“, „2,5“, leeres Feld = unbekannt).

### DONE
- Reines Verschieben, eigener Patch nach Arbeitsregel „keine Refactors
  nebenbei“. Namen ohne Unterstrich, weil jetzt mehrere Module sie
  benutzen.

### TEST
- KI, Wochen-Build: `szenario_felder` und `szenario_maschine_bearbeiten`
  grün (tippen Zahlen im deutschen Format, leeren Felder).

### NEXT
- W-002 Stufe 1: Werkzeugverwaltung mit Werkstoffen und Werkzeugen.

## P-2026-09-25-44 spezifikation-werkzeugverwaltung

### EINGELESEN
- Manuel: eine andere Werkzeugverwaltung ausdenken – bedienerfreundlich,
  übersichtlich, „einfach GENIAL“, etwa wie die alte von InventorCAM.
  Werkstoffliste zuerst, mit deutschen Bezeichnungen („1.4301 (Edelstahl,
  chemische Zusammensetzung)“) und Härte; im Werkzeug Schnittwerte je
  Werkstoff, auch für alle gleich; vc eingeben statt Drehzahl; ae und ap je
  Einsatz, als Tabelle; Schruppstrategie mit größtem Zeitspanvolumen und eine
  Beurteilung verschiedener Strategien (sein Beispiel: Ø 12, ae 1,2 / ap 25 /
  fz 0,15 statt ae 100 % / ap 3 / fz 0,05). „Möglichst einfach und gut
  erklärt.“
- Er schläft; Entscheidungen treffe ich und schreibe sie auf.

### DATEIEN
- `docs/spezifikation_werkzeugverwaltung.md` (neu)
- `docs/STATUS_SNAPSHOT.md` (W-002, Projektstatus)
- `CHATSTART.md` (Lesekarte: W-002; Zeile Installieren/Update)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Manuel liest die Spezifikation und findet seinen Wunsch darin wieder –
Abschnitt 1 in seinen Worten, Abschnitt 11 mit den Entscheidungen zur
Besprechung.

### DONE
- FreeCAD-Check (Arbeitsregeln 2.3), im Quelltext beider Versionen:
  - 1.1.3 hat Werkzeugbibliothek und Werkzeug-Controller, aber keine
    Schnittwerte je Werkstoff.
  - Der Wochen-Build hat neu `Path/Tool/FeedsSpeeds`: „Presets“ am
    Werkzeug mit vc und fz je Werkstoff (UUID oder Name) und
    Bearbeitungsart (profile, pocket, slot, drill, adaptive,
    surface_finish), dazu einen Vorschlagsdialog im Werkzeug-Controller, der
    den Werkstoff des Rohteils nimmt.
  - FreeCADs Werkstoffkarten kennen die Werkstoffnummer
    (`MaterialStandard/MaterialNumber`), aber weder Härte noch
    Zusammensetzung; das Modell `Machinability` (vc HSS/VHM, kc1.1, mc)
    haben nur sechs generische Werkstoffe.
  - ae/ap und eine Beurteilung von Strategien gibt es in keiner Version.
- Daraus die Spezifikation: Werkstoffliste mitgeliefert und erweiterbar,
  Werkzeuge mit einer Tabelle der Einsätze „für alle Werkstoffe“ und je
  Werkstoff, gerechnete Werte, Bild des Eingriffs, Strategievergleich mit
  „Schneidenweg je cm³“ als Maß für den Verschleiß, Übergabe an FreeCADs
  Presets als Stufe 2.
- Manuels Beispiel durchgerechnet (Abschnitt 7): 2,5-faches
  Zeitspanvolumen, ein Zwölftel des Schneidenwegs.
- Acht Entscheidungen mit Alternative und Kosten in Abschnitt 11.

### TEST
- Nur Doku, kein Testlauf. Die Zahlen des Beispiels von Hand nachgerechnet.

### NEXT
- Stufe 1 bauen, Patch für Patch nach Abschnitt 12.

## P-2026-09-25-43 installieren-einfach

### EINGELESEN
- Manuel zur Anleitung „Installieren, solange das Repository privat ist“:
  „ich hätte hierfür gerne ein bash script oder sowas … einfacher“, und:
  „das einfachste wäre die repo öffentlich zu stellen … wenn du denkst, das
  geht zum Testen schon, dass andere es auch testen können, dann mach das“.
- Er schläft, ich entscheide selbst und schreibe die Entscheidungen auf.

### DATEIEN
- `installieren.py` (neu)
- `tests/test_installieren.py` (neu)
- `README.md` (Abschnitte „Installieren“)
- `translations/de.json`, `translations/en.json` (`update.kein_git_ordner`)
- `docs/STATUS_SNAPSHOT.md` (T-005)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Bei öffentlichem Repository: In FreeCAD Ansicht → Fenster → Python-Konsole,
die Zeile aus dem README einfügen, Enter → Meldung „CAM-Addon … ist
installiert. Bitte FreeCAD neu starten.“; nach dem Neustart steht die
Werkzeugleiste in Assembly und CAM.

### DONE
- **Entscheidung 1: Python-Zeile statt Bash-Skript.** Ein Bash-Skript
  liefe nicht unter Windows, und es müsste den Addon-Ordner raten – der
  hängt von Betriebssystem und FreeCAD-Version ab. Eine Zeile in der
  Python-Konsole von FreeCAD kennt ihn (`App.getUserAppDataDir()`), läuft
  überall und braucht weder Git noch GitHub Desktop.
- **Entscheidung 2: öffentlich stellen – empfohlen, aber nicht von mir
  umgestellt.** Geprüft: alle 42 Commits von „Claude <noreply@anthropic.com>“,
  keine Schlüssel, Passwörter oder Mail-Adressen im ganzen Verlauf, keine
  großen Dateien, Lizenz LGPL-2.1-or-later liegt bei, `package.xml` nennt
  Manuel ohne Mail-Adresse. Für andere Tester reicht der Stand als frühe
  Vorabversion. Die Sichtbarkeit eines Repositorys kann ich mit meinen
  Werkzeugen nicht ändern – das ist ein Klick für Manuel (T-005).
- `installieren.py` holt das ZIP von GitHub, packt es außerhalb von `Mod/`
  aus (ein halber Ordner in `Mod/` würde beim nächsten Start als zweites
  Addon geladen) und setzt es an die Stelle von `Mod/freecad-cam-addon`.
  Misslingt das Ersetzen, kommt der alte Stand zurück.
- Dieselbe Zeile noch einmal = aktualisieren. Ein Git-Klon (GitHub Desktop)
  bleibt unberührt.
- Die Zeile trägt das Repository im Addon-Manager ein („Eigene
  Repositories“, Parameter `Addons/CustomRepositories`, Format wie dort:
  „Adresse Zweig“ je Zeile). Nachgelesen im Quelltext des Addon-Managers
  (1.1.3 und Wochen-Build, `addonmanager_workers_startup.py`): Liegt ein
  Ordner mit dem Namen des Repositorys in `Mod/`, gilt das Addon als
  installiert; ohne Git vergleicht er die Version in `package.xml`, mit Git
  macht er aus dem Ordner einen Klon. Er meldet also neue Versionen, auch
  wenn das Addon per ZIP kam.
- Nicht gemacht, mit Absicht: Git in der Installationszeile. Das hätte die
  Ausnahme „Git nur in `aktualisierung.py`“ (Arbeitsregeln, Abschnitt 7)
  erweitert, und unter Windows fehlt Git meist ohnehin.
- Nicht gemacht: die eigene Update-Suche beim Start auch für
  ZIP-Installationen (per HTTPS statt Git). Bis dahin zeigt der
  Addon-Manager die Updates; der Text `update.kein_git_ordner` sagt das
  jetzt, statt nur aufs README zu verweisen.
- Befund im README korrigiert: Die Python-Konsole heißt im deutschen FreeCAD
  **Ansicht → Fenster → Python-Konsole** („&Panels“ → „Fenster“ laut
  `FreeCAD_de.ts`), nicht „Ansicht → Ansichten“.
- Texte von `installieren.py` stehen zweisprachig im Code: Die Datei läuft,
  bevor das Addon und seine Sprachdateien da sind.

### TEST
- `tests/test_installieren.py` (KI, FreeCADCmd, Wochen-Build): frisch
  installieren, noch einmal (ersetzt ganz, alte Dateien weg, kein doppelter
  Eintrag, keine Reste in `Mod/`), kaputter Download, Archiv ohne
  `package.xml` und kein ZIP (Installation bleibt unverändert), Git-Klon
  bleibt unberührt, andere eigene Repositories bleiben, die Zeile im README
  stimmt mit der Datei überein. „GitHub“ ist dabei ein ZIP im Temp-Ordner.
- Echter Lauf gegen GitHub (KI): Das Repository ist noch privat → HTTP 404,
  die Meldung verweist auf die Anleitung mit GitHub Desktop. Der Weg mit
  öffentlichem Repository ist erst nach dem Umstellen prüfbar – von Manuel.

### NEXT
- Manuel stellt das Repository öffentlich und probiert die Zeile aus.

## P-2026-09-25-42 nur-noetige-tests

### EINGELESEN
- Manuel: „du testest zu viel“. Die Tests sollen nur laufen, wenn es
  wirklich nötig ist – sie kosten Ressourcen, auch Rechenzeit und Strom in
  Rechenzentren. Wie viel nötig ist, überlässt er meinem Urteil.
- Bilanz des Tages: Der komplette Lauf (rund 3 Minuten) lief elfmal bei 13
  Patches, zehn Läufe davon einfach grün. Gefunden haben die echten Fehler
  gezielte Proben (B-004, B-005), nicht die Wiederholungen.

### DATEIEN
- `docs/arbeitsregeln.md` (Abschnitt 5)
- `CLAUDE.md` (Regel zum Pushen)
- `CHATSTART.md` (Prüfung vor jedem Push statt bei jeder Änderung)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Regeln verlangen einen kompletten Lauf nur noch einmal vor einem Push,
für alle Patches zusammen. Doku-Änderungen brauchen keinen Lauf.

### DONE
- Neue Regeln:
  - Während der Arbeit läuft nur die Prüfung zum geänderten Teil, in einer
    Version.
  - Vor einem Push läuft einmal `scripts/alle_tests.sh` in beiden
    Versionen, für alle Patches seit dem letzten Push.
  - Reine Doku-Änderungen laufen ohne Test.
  - Neue Prüfungen gibt es nur für behobene Fehler, dann mit einer
    Gegenprobe, und für neue Funktionen.
  - Neue Szenarien gibt es nur für neue Oberflächen.
  - Im Chat genügt „Tests grün“.
- Nicht geändert, mit Absicht: Alle vorhandenen Prüfungen bleiben. Ein Lauf
  kostet rund 3 Minuten; gespart wird vor allem dadurch, dass er seltener
  läuft.

### TEST
- Nur Doku geändert, deshalb nach der neuen Regel kein Testlauf.

### NEXT
- Manuels Test in FreeCAD 1.1.3, danach W-001 Stufe 3.

## P-2026-09-25-41 eine-grenze-fehlt-im-bericht

### EINGELESEN
- B-002 aus P-2026-09-25-29: Hat ein Gelenk nur eine der beiden
  Begrenzungen, bekam die andere Seite bei der Übergabe ohne Hinweis
  ±100000 mm bzw. ±360°. Gemeldet wurde nur, wenn beide fehlten.

### DATEIEN
- `camaddon/export.py` (`_satz_fehlende_grenzen`)
- `translations/de.json`, `translations/en.json` (`export.eine_grenze`)
- `tests/test_export.py`
- `docs/STATUS_SNAPSHOT.md` (B-002 entfernt, keine offenen Bugs mehr)
- `package.xml` (Version 0.3.9)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Fehlt am Gelenk eine Begrenzung oder fehlen beide, steht das unter „Bitte
prüfen“ – außer bei einer endlos drehenden Achse.

### DONE
- Neuer Satz „… hat am Gelenk nur eine Begrenzung (Min oder Max). Für die
  andere Seite bekommt CAM einen sehr großen Bereich …“. Fehlen beide,
  bleibt es beim bisherigen Satz.
- Die Bedingung steht jetzt an einer Stelle:
  `endlos = achse.art != LINEAR and ba.Endlos`. Dazu kommt
  `_satz_fehlende_grenzen()`, das zwischen „keine“ und „nur eine“
  unterscheidet. Die Hilfsvariable `ohne_grenzen`, die an zwei Stellen
  gesetzt wurde, ist weg.
- Version 0.3.9.

### TEST
- Von der KI ausgeführt:
  - Neuer Abschnitt in `test_export.py`: Das Gelenk Z bekommt nur ein
    Maximum (500 mm). Erwartet werden der Satz „nur eine Begrenzung“, nicht
    „keine Begrenzung“, und die Grenzen −100000/500 mm in CAM.
  - Gegenprobe mit dem alten Code: Der Satz fehlt.
  - Mit dem neuen Code ist `alle_tests.sh` in beiden Versionen grün.

### NEXT
- Manuels Test in FreeCAD 1.1.3.
- Danach W-001 Stufe 3: Maschine von Hand verfahren.

## P-2026-09-25-40 pflichtwert-fehlt-im-bericht

### EINGELESEN
- B-001 aus P-2026-09-25-29: Fehlt bei der Übergabe ein Pflichtwert, trägt
  das Addon FreeCADs Vorgabe ein. Der Bericht führte das unter „In CAM
  angekommen“, als wäre alles in Ordnung.
- Dasselbe galt für die Spindel: Ohne Drehzahl stand dort „Spindel S4, bis
  0 U/min“.

### DATEIEN
- `camaddon/export.py`
- `translations/de.json`, `translations/en.json` (vier neue Texte)
- `tests/test_export.py`
- `docs/STATUS_SNAPSHOT.md` (B-001 entfernt)
- `package.xml` (Version 0.3.8)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Fehlt ein Pflichtwert (Eilgang, Geschwindigkeit, Drehzahl), steht unter
„Bitte prüfen“ ein Satz, was fehlt, was CAM stattdessen bekommt und was zu
tun ist.

### DONE
- Linear- und Drehachse: Unter „In CAM angekommen“ steht weiter, was CAM
  bekommen hat, also FreeCADs Vorgabe. Dazu steht jetzt unter „Bitte
  prüfen“, dass der Wert fehlte.
- Spindel ohne Drehzahl: „Spindel S4, ohne größte Drehzahl“ statt „bis
  0 U/min“, dazu unter „Bitte prüfen“: CAM begrenzt die Spindeldrehzahl dann
  nicht. Nachgesehen in FreeCAD: Der Schnittdaten-Rechner begrenzt nur bei
  `max_rpm > 0` (`Path/Tool/FeedsSpeeds/resolver.py`).
- Version 0.3.8.

### TEST
- Von der KI ausgeführt:
  - `test_export.py` hat einen neuen Abschnitt: X1 ohne Eilgang, C4 ohne
    Geschwindigkeit, S4 ohne Drehzahl.
  - Gegenprobe mit dem alten Code: Alle vier Prüfungen schlagen fehl, und im
    Bericht steht „Spindel S4, bis 0 U/min“.
  - Mit dem neuen Code ist `alle_tests.sh` in beiden Versionen grün; in
    1.1.3 wird der Export wie immer übersprungen.

### NEXT
- B-002: nur eine Begrenzung am Gelenk.

## P-2026-09-25-39 push-freigabe-dauerhaft

### EINGELESEN
- Manuels Antwort auf die Frage nach P-2026-09-25-36 bis -38: „Ja, und
  künftig direkt“. Jeder Patch wird gepusht, sobald alle Prüfungen in beiden
  FreeCAD-Versionen grün sind.

### DATEIEN
- `CLAUDE.md` (Regel zum Pushen)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die dauerhafte Freigabe steht in der `CLAUDE.md`, damit auch spätere
Sitzungen sie kennen.

### DONE
- P-2026-09-25-36 bis -38 gepusht (`36fd298..7b0b350`) und bei GitHub selbst
  nachgeprüft.
- In der `CLAUDE.md` steht jetzt: Jeder Patch wird gepusht, sobald
  `scripts/alle_tests.sh` in beiden Versionen vollständig grün ist; alles
  andere nur auf ausdrückliche Ansage. Die Regel, danach bei GitHub selbst
  nachzusehen, bleibt.

### TEST
- Nur Doku geändert. `alle_tests.sh` ohne Oberfläche ist in beiden
  Versionen grün.

### NEXT
- B-001 und B-002 (Bericht der Übergabe).

## P-2026-09-25-38 enter-bestaetigt-nur-das-feld

### EINGELESEN
- Manuels Entscheidung zu B-005: „Nur Feld bestätigen“. Enter übernimmt den
  Wert im Feld; geschlossen wird der Dialog nur mit OK oder Abbrechen.

### DATEIEN
- `camaddon/gui_maschine.py` (`_EnterBleibtImDialog`)
- `tests/gui/szenario_felder.py` (vorher `szenario_zahlen.py`; jetzt mit
  echtem Enter)
- `docs/aufbau.md` (Stolperstein erledigt)
- `docs/STATUS_SNAPSHOT.md` (B-005 entfernt)
- `package.xml` (Version 0.3.7)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Enter in einem Feld übernimmt den Wert, und der Dialog bleibt offen.

### DONE
- Ein Feld verarbeitet Enter und reicht die Taste dann an die Widgets
  darüber weiter; bei FreeCADs Aufgabenfenster angekommen, löste sie „OK“
  aus. Ein Ereignisfilter ganz oben im Dialog hält Enter jetzt an. Das
  Feld hat seinen Wert zu diesem Zeitpunkt schon übernommen. Escape
  (Abbrechen) bleibt, wie es ist.
- Das Szenario heißt jetzt `szenario_felder`, weil es beides prüft:
  Zahlenformat (B-004) und Enter (B-005). Es tippt echtes Enter; die
  Nachbildung `bestaetigen()` aus P-2026-09-25-31 ist weg.
- Version 0.3.7.

### TEST
- Von der KI ausgeführt:
  - Gegenprobe ohne den Filter: „Enter im Feld hat den Dialog geschlossen
    (B-005)“.
  - Mit dem Filter ist `szenario_felder` in beiden Versionen grün, ebenso
    `alle_tests.sh`.

### NEXT
- B-001 und B-002 (Bericht der Übergabe).
- Manuels Test in FreeCAD 1.1.3.

## P-2026-09-25-37 readme-update-suche

### EINGELESEN
- README, Abschnitt „Aktualisieren“: Dort steht, das Addon frage beim Start
  „Jetzt aktualisieren?“. Seit P-2026-09-25-30 fragt es aber nur bei einer
  neuen Version.

### DATEIEN
- `README.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die README beschreibt die Update-Suche so, wie sie sich verhält.

### DONE
- „fragt bei einer neuen Version“. Dazu der Hinweis, dass „Pull“ von Hand
  auch kleine Änderungen ohne neue Versionsnummer holt.

### TEST
- Nur Doku geändert. `alle_tests.sh` ohne Oberfläche ist in beiden
  Versionen grün.

### NEXT
- B-005: Enter bestätigt nur das Feld.

## P-2026-09-25-36 push-bei-github-pruefen

### EINGELESEN
- Manuels Freigabe: P-2026-09-25-30 bis -35 pushen und die Prüfung direkt
  bei GitHub als Regel aufnehmen.
- Befund aus P-2026-09-25-30: P-23 bis P-28 blieben unbemerkt lokal, weil
  `origin` auf den Ordner selbst zeigte.

### DATEIEN
- `CLAUDE.md` (neue Regel)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach jedem Push steht fest, dass GitHub den Commit hat – geprüft bei GitHub
selbst, nicht über `origin`.

### DONE
- P-2026-09-25-30 bis -35 gepusht (`999d46b..36fd298`). Bei GitHub selbst
  nachgeprüft: `main` steht auf `36fd298`.
- Neue Regel in `CLAUDE.md`: Nach jedem Push muss
  `git ls-remote https://github.com/manuelhofer/freecad-cam-addon main` den
  eigenen Commit zeigen. Die Regel steht dort und nicht in
  `docs/arbeitsregeln.md`, weil sie nur die Arbeitsweise von Claude Code
  betrifft.

### TEST
- Nur Doku geändert. `alle_tests.sh` ohne Oberfläche ist in beiden
  Versionen grün.

### NEXT
- README: Beschreibung der Update-Suche an P-2026-09-25-30 anpassen.
- B-005: Enter bestätigt nur das Feld (Manuels Entscheidung).

## P-2026-09-25-35 entwickler-doku

### EINGELESEN
- Manuels Auftrag aus P-2026-09-25-27: Der Code soll für jeden menschlichen
  Programmierer leicht zu lesen sein. Dazu gehört ein Einstieg, der das
  Ganze erklärt, bevor man in einzelne Dateien schaut.

### DATEIEN
- `docs/aufbau.md` (neu)
- `CHATSTART.md` (Lesekarte: Zeile für `docs/aufbau.md`)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer den Code nicht kennt, findet in einer Datei: den Weg von der Assembly
zur CAM-Maschine, welches Modul was tut, die Regeln für Importe und Texte,
wie geprüft wird, und die Stolpersteine von FreeCAD und PySide.

### DONE
- `docs/aufbau.md` mit diesen Abschnitten:
  - Weg der Daten als Bild: Assembly → Kette → Maschinenobjekt → Übergabe.
  - Tabelle aller Module.
  - Zwei Regeln: Kern-Module ohne Qt; Importe nur von `gui_*` zum Kern.
  - Kette, Maschinenobjekt, Dialog, Texte, zwei FreeCAD-Versionen, Prüfen.
  - Stolpersteine, jeder mit seiner Folge im Code.
- Die Regeln sind am Code geprüft: Kein Kern-Modul importiert
  `FreeCADGui`, Qt oder ein `gui_*`-Modul.

### TEST
- Von der KI ausgeführt: Verweise in `docs/aufbau.md` zeigen auf vorhandene
  Dateien; `alle_tests.sh` ohne Oberfläche in beiden Versionen grün (nur
  Doku geändert).

### NEXT
- Manuel: Push-Freigabe (P-2026-09-25-30 bis -35 liegen nur lokal),
  Entscheidung zu B-005, Test in FreeCAD 1.1.3.
- Danach B-001 und B-002 (Bericht der Übergabe).

## P-2026-09-25-34 tests-und-skripte-lesbar

### EINGELESEN
- Durchsicht von Hand: `tests/`, `tests/gui/_lauf/`, `scripts/`.

### DATEIEN
- `tests/test_maschine.py`, `tests/test_export.py`, `tests/beispielmaschinen.py`
- `tests/gui/_lauf/szenario_lauf.py`
- `scripts/oberflaeche_testen.sh`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Tests lesen sich ohne Rätsel: keine `__import__`-Tricks, keine
gleichnamigen Funktionen und Variablen, Lagen der Beispielkörper mit Namen.
Geprüft wird genau dasselbe wie vorher.

### DONE
- **test_maschine.py:** `import math` statt zweimal `__import__("math")`;
  vier Kennwerte als vier Zuweisungen statt einer `setattr`-Schleife.
- **test_export.py:** Die Funktion hieß `pruefen()` und hatte eine lokale
  Variable `pruefen`. Jetzt heißen sie `pruefe_export()` und `zu_pruefen`;
  dazu `uebertragen` und `nicht_uebertragen` statt `nicht`.
- **beispielmaschinen.py:**
  - Lagen mit Namen: `zylinder("Hauptspindel", 60, 80, x=75, y=100, z=300)`
    statt `zylinder("Hauptspindel", 60, 80, 75, 100, 300)`. Dasselbe gilt
    für LCS-Name und -Höhe bei `bauteil()`. Die Zahlen sind unverändert.
  - Der Kommentar zu `Placement` stand zweimal; jetzt steht er einmal in
    `_stelle()`.
  - `Baukasten` hat eine Beschreibung.
- **Szenario-Läufer:** `START_NACH_MS` statt `3000`.
- **oberflaeche_testen.sh:** `zeitlimit_s` statt zweimal `180`.
- Nicht geändert, mit Absicht: Jede Prüfung hat ihr eigenes dreizeiliges
  `pruefe()`. Ein gemeinsames Modul würde keine Zeile der Pfad-Vorbereitung
  sparen; so bleibt jede Prüfung für sich lesbar.

### TEST
- Von der KI ausgeführt: black und ruff sauber; `alle_tests.sh` in beiden
  Versionen grün.

### NEXT
- Entwickler-Doku `docs/aufbau.md`.

## P-2026-09-25-33 oberflaeche-rest-lesbar

### EINGELESEN
- Durchsicht von Hand: `gui_zeigen`, `gui_start`, `gui_sprachwahl`,
  `gui_aktualisierung`.

### DATEIEN
- `camaddon/__init__.py` (`symbol()` und `SYMBOL_ORDNER`, vorher in
  `gui_start`)
- `camaddon/gui_start.py`, `gui_sprachwahl.py`, `gui_aktualisierung.py`,
  `gui_zeigen.py`
- `camaddon/gui_maschine.py` (holt `symbol` aus dem Paket)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Alle Importe stehen oben in der Datei, und kein Modul importiert ein anderes
im Kreis. Wartezeiten und Maße sind benannte Konstanten, jede Klasse sagt,
wozu sie da ist. Das Verhalten bleibt gleich.

### DONE
- **Import-Kreis aufgelöst:** `gui_maschine` holte `symbol()` aus
  `gui_start`, und `gui_start` importierte `gui_maschine`. Deshalb standen
  die Importe in `gui_start` und `gui_sprachwahl` in den Funktionen.
  `symbol()` liegt jetzt beim Paket, neben `ADDON_ORDNER`. Alle Importe
  stehen oben.
- **gui_aktualisierung:**
  - `START_VERZOEGERUNG_MS`, `NACHSEHEN_MS`, `DIALOG_BREITE` statt Zahlen.
  - `ordner` hat den Addon-Ordner als Vorgabe; die Verzweigungen
    `if self.ordner: … else: …` entfallen.
  - Beim Start entfernt `fertig` genau seine Suche aus der Liste; vorher
    räumte ein Tupel-Lambda die ganze Liste leer.
  - Erklärt ist, warum der Such-Thread `daemon` ist und warum die Liste der
    laufenden Suchen nötig ist.
- **gui_zeigen:** `GROESSE_OHNE_FORM` statt `100.0`; die Berechnung des
  Ausschlags steht in `_weite()`.
- **gui_start, gui_sprachwahl:** Docstrings; Kommentar, dass FreeCAD
  `loadSettings` und `saveSettings` aufruft.
- Keine sichtbare Änderung, deshalb bleibt die Version 0.3.6.

### TEST
- Von der KI ausgeführt:
  - black und ruff sauber.
  - `alle_tests.sh` in beiden Versionen grün, 30 von 30. Die geänderten
    Importe beim Start laufen in jedem der sieben Szenarien mit.
  - Protokolle aller 14 Szenario-Läufe: kein Traceback.

### NEXT
- Tests und Skripte durchsehen; Entwickler-Doku `docs/aufbau.md`.

## P-2026-09-25-32 dialog-maschine-aufgeteilt

### EINGELESEN
- Manuels Auftrag aus P-2026-09-25-27 (Code lesbar, „to the max“).
- `gui_maschine.py` hatte 930 Zeilen: Befehl, Hilfe, Zahlenfelder, das
  Aufgabenfenster mit 45 Methoden, Verteilhilfe und Bericht in einer Datei.
- Die Szenarien riefen acht private Methoden des Fensters direkt auf.

### DATEIEN
- `camaddon/gui_maschine.py` (Befehl und Aufgabenfenster, neu gegliedert)
- `camaddon/gui_details.py` (neu: Felder der gewählten Betriebsart oder
  Aufnahme, Zahlenformat)
- `camaddon/gui_hilfe.py` (neu: Knopf (?) und Hilfefenster)
- `camaddon/gui_verteilhilfe.py` (neu: Revolverplätze verteilen)
- `camaddon/gui_bericht.py` (neu: Bericht nach der Übergabe)
- `camaddon/kette.py`, `maschine.py` (nur Trennlinien der Abschnitte)
- `tests/gui/szenario_*.py` (neue Schnittstelle)
- `tests/test_hilfe.py` (sucht in allen `gui_*.py`, Suchmuster repariert)
- `CHATSTART.md` (Lesekarte: neue Module)
- `package.xml` (Version 0.3.6)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Jede Datei hat ein Thema. Das Aufgabenfenster ist in benannte Abschnitte
gegliedert. Die Szenarien benutzen nur öffentliche Methoden oder bedienen
Knöpfe und Signale wie ein Benutzer. Alle Szenarien sind in beiden
FreeCAD-Versionen grün.

### DONE
- **Aufteilung:**
  - `gui_maschine.py`: Befehl, Suche nach der Assembly, Aufgabenfenster.
  - `gui_details.py`: der Kasten mit den Feldern.
  - `gui_hilfe.py`, `gui_verteilhilfe.py`, `gui_bericht.py`: je ein kleines
    Fenster.
- **Aufgabenfenster:**
  - Benannte Abschnitte: Schnittstelle zu FreeCAD, Aufbau, Aktionen,
    Auswahl, Eingaben übernehmen, Listen füllen, Zeigen, Abfragen,
    Rückfragen.
  - `_baue()` ist je Bereich aufgeteilt.
  - Öffentliche „Aktionen“ stehen hinter den Knöpfen und dienen auch den
    Szenarien: `betriebsart_anlegen`, `betriebsart_entfernen`,
    `aufnahme_anlegen`, `aufnahme_entfernen`, `plaetze_verteilen`,
    `uebergeben`, `zeige`, `springe_zu`, `neu_aufbauen`, `alle_lcs`,
    `lcs_im_revolver`.
  - Die Zeilenarten heißen `ZEILE_GELENK`, `ZEILE_BETRIEBSART` usw. statt
    „ba“ und „auf“. `_zeilendaten()` und `_alle_zeilen()` ersetzen je vier
    Wiederholungen.
  - Benannte Konstanten statt Zahlen: `ZEIGEN_NACH_MS`, Mindesthöhen der
    Listen, Fenstergrößen, Anzahl der Revolverplätze.
  - Kein `lambda: x and …`-Trick und kein doppeltes Leeren der Details mehr.
    `self.meldungen` wird in `__init__` angelegt, `IsActive` liest sich als
    `not activeDialog()`.
- **Sichtbar geändert, deshalb Version 0.3.6:**
  - „+ Betriebsart“ ist ein Knopf mit Aufklappmenü, erkennbar am kleinen
    Pfeil. Vorher öffnete der Code ein selbst positioniertes Menü, das bei
    jedem Klick neu entstand und nie freigegeben wurde.
  - „+ Betriebsart“ ist nur bedienbar, wenn zur Auswahl eine Achse gehört.
    Bei einer Betriebsart ohne gültiges Gelenk kam vorher beim Klick einfach
    nichts.
  - Der Bericht zeigt keinen leeren Abschnitt „In CAM angekommen“ mehr.
- **Szenarien:** Sie wählen die Betriebsart jetzt über das Menü des
  Knopfs, legen Aufnahmen per Knopfdruck an und springen per
  `itemClicked` zu einem Hinweis, also wie ein Benutzer.
- Trennlinien der Abschnitte sind in allen Modulen 80 Zeichen breit.
- **Befund in `test_hilfe.py`:** Das Muster für die Knöpfe (?)
  (`_kopfzeile\([^)]*,…`) kam nie an der Klammer von `tr("…")` vorbei. Der
  Test prüfte deshalb nur den Verweis `href="beschleunigung"`, die drei
  Knöpfe nie. Aufgefallen ist das erst, weil nach der Aufteilung beide
  Muster nichts mehr fanden. Jetzt durchsucht der Test alle `gui_*.py` und
  schlägt fehl, wenn eines der beiden Muster nichts findet.

### TEST
- Von der KI ausgeführt:
  - black und ruff sauber.
  - Alle sieben Szenarien in beiden Versionen grün.
  - `alle_tests.sh` in beiden Versionen grün.
  - Screenshot angesehen: „+ Betriebsart“ mit Aufklapp-Pfeil, Felder
    darunter wie vorher.
  - `test_hilfe.py`: Das alte Muster findet im alten Code `set()`. Das neue
    findet die Knöpfe `achsen`, `aufnahmen`, `glieder` und den Verweis
    `beschleunigung`.

### NEXT
- Durchsicht von `gui_zeigen`, `gui_start`, `gui_sprachwahl` und
  `gui_aktualisierung`.

## P-2026-09-25-31 zahlenfelder-eindeutig

### EINGELESEN
- Befund bei der Durchsicht von `gui_maschine.py`: Die Zahlenfelder zeigen
  Werte mit `QLocale()`, lesen sie aber mit „Komma oder Punkt ist das
  Dezimalzeichen“.
- Probe in FreeCAD 1.1.3 und im Wochen-Build mit `LANG=de_DE`: FreeCAD
  stellt für Qt `de_DE` **mit** Tausendertrennzeichen ein. 30000 erscheint
  als „30.000“.

### DATEIEN
- `camaddon/gui_maschine.py` (`_zahlenformat`, `_Zahlenpruefer`,
  `_zahl_lesen`, `_zahl_zeigen`)
- `tests/gui/szenario_zahlen.py` (neu)
- `package.xml` (Version 0.3.5)
- `docs/STATUS_SNAPSHOT.md` (B-005)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Im deutschen Zahlenformat zeigt das Eilgang-Feld 30000 als „30000“. Weder
Bestätigen ohne Änderung noch „35.000“ tippen verfälscht den Wert. Ein
geleertes Feld setzt den Wert auf „unbekannt“ (0).

### DONE
- **B-004 behoben**, drei Fehler mit derselben Ursache:
  1. Das Feld zeigte „30.000“. Bestätigte man das ohne Änderung, stand
     danach 30 mm/min im Dokument.
  2. „35.000“ getippt ergab 35 statt 35000.
  3. Ein geleertes Feld wurde nie übernommen, weil `QDoubleValidator` es
     für unfertig hält. Der alte Wert blieb, obwohl das Feld leer war.
- Zahlen stehen jetzt im Format der Oberfläche, aber ohne
  Tausendertrennzeichen. Auf Deutsch ist das Komma das Dezimalzeichen, einen
  Punkt nimmt das Feld nicht an. So ist jede Eingabe eindeutig.
- `_Zahlenpruefer` lässt ein leeres Feld zu, es bedeutet „unbekannt“ (0).
- Version 0.3.5.
- **B-005 gefunden:** Enter in einem Feld schließt den ganzen Dialog mit OK.
  Das ist FreeCADs Verhalten für alle Aufgabenfenster. Ob der Dialog davon
  abweichen soll, entscheidet Manuel; im Snapshot steht ein Vorschlag.

### TEST
- Von der KI ausgeführt:
  - Neues Szenario `szenario_zahlen`: deutsches Zahlenformat wie bei FreeCAD
    auf einem deutschen System, Eingaben Taste für Taste.
  - Gegenprobe mit dem alten Code, alle Fehler einzeln belegt: Anzeige
    „30.000“; nach dem Bestätigen 30.0; „35.000“ ergibt 35.0; das geleerte
    Feld bleibt 35.0; kein Hinweis auf den fehlenden Eilgang.
  - Mit dem neuen Code ist das Szenario in beiden Versionen grün, ebenso
    `alle_tests.sh`.
  - Probe zu B-005: Enter im Feld „NC-Name“ ergibt `geschlossen=True`, ein
    Rückgängig-Schritt, in 1.1.3 und im Wochen-Build.

### NEXT
- Durchsicht der Oberflächen-Module: `gui_maschine.py` aufteilen.

## P-2026-09-25-30 update-nur-bei-neuer-version

### EINGELESEN
- B-003 aus P-2026-09-25-29: Die Update-Suche meldete „neu“, sobald auf
  GitHub ein anderer Commit lag, auch bei gleicher Version. Der Hinweis
  hätte dann gelautet: „neue Version 0.3.3 (installiert ist 0.3.3)“.
- Dringend geworden, weil die nächsten Patches (Durchsicht der Oberfläche,
  Tests, Doku) nichts Sichtbares ändern und deshalb keine neue Version
  bekommen.
- **Befund beim Push von P-2026-09-25-29:** `origin` zeigte im Klon auf den
  Ordner selbst statt auf GitHub. Das hatte der Test mit dem Addon-Manager
  in P-2026-09-25-23 verursacht. P-23 bis P-28 kamen deshalb nie bei GitHub
  an: `git push` meldete „Everything up-to-date“, und die Kontrolle mit
  `git ls-remote origin` fragte nur den Ordner selbst ab. `origin` zeigt
  wieder auf GitHub. P-23 bis P-29 sind nachgeschoben (`b9e4932..999d46b`)
  und bei GitHub selbst nachgeprüft. Weitere Pushes erst nach Manuels
  ausdrücklicher Freigabe.

### DATEIEN
- `camaddon/aktualisierung.py` (`ist_neuer()`, Vergleich der Versionen)
- `tests/test_aktualisierung.py` (neuer Stand ohne neue Version; Vergleich
  Zahl für Zahl)
- `package.xml` (Version 0.3.4)
- `docs/STATUS_SNAPSHOT.md` (B-003 entfernt)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Update-Suche meldet nur eine höhere Version. Ein neuer Stand auf GitHub
mit gleicher Version gilt als „aktuell“.

### DONE
- `ist_neuer(neu, jetzt)` vergleicht Zahl für Zahl, also ist 0.3.10 höher
  als 0.3.9. Ist eine Version unlesbar, gilt „anders ist neu“: lieber einmal
  zu oft fragen als ein Update verschweigen.
- Änderungen ohne neue Version (Tests, Doku, Aufräumen) kommen beim
  Benutzer mit der nächsten Version an. Beim Aktualisieren wird ohnehin bis
  zum neuesten Stand vorgespult.
- Der Vergleich der Commits (`rev-parse`) entfällt; er ist im Vergleich der
  Versionen enthalten.
- Version 0.3.4, weil sich das Verhalten der Update-Suche ändert.

### TEST
- Von der KI ausgeführt:
  - Gegenprobe mit dem alten Code: Der neue Fall ergibt
    `Ergebnis(status='neu', version_neu='9.9.0', version_jetzt='9.9.0')`.
  - Mit dem neuen Code besteht `test_aktualisierung.py`.
  - `alle_tests.sh` in beiden Versionen grün.

### NEXT
- Durchsicht der Oberflächen-Module.

## P-2026-09-25-29 kern-module-lesbar

### EINGELESEN
- Manuels Auftrag aus P-2026-09-25-27: Code gut dokumentiert und
  kommentiert, für jeden menschlichen Programmierer leicht zu lesen, „kein
  AI-Slop“, das Vorhandene „to the max“ optimieren.
- Durchsicht von Hand: alle Module ohne Oberfläche (`kette`, `maschine`,
  `export`, `sprache`, `hilfe`, `aktualisierung`, `__init__`).

### DATEIEN
- `camaddon/kette.py`, `maschine.py`, `export.py`, `sprache.py`, `hilfe.py`,
  `aktualisierung.py`, `__init__.py` (überarbeitet)
- `camaddon/gui_maschine.py`, `gui_zeigen.py` (nur auf die neuen Namen
  umgestellt; die Durchsicht folgt als eigener Patch)
- `tests/test_kette.py`, `test_maschine.py`, `test_aktualisierung.py` (neue
  Namen)
- `docs/STATUS_SNAPSHOT.md` (drei Befunde als B-001 bis B-003)
- `package.xml` (Version 0.3.3)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Jedes Kern-Modul sagt oben, wozu es da ist; Funktionen und Namen sagen, was
gemeint ist; nichts steht doppelt. Das Verhalten bleibt gleich: alle
Prüfungen und Szenarien in beiden FreeCAD-Versionen grün.

### DONE
- **kette.py**
  - `lies_kette()` besteht aus vier benannten Schritten, je eine Funktion:
    Gelenke sortieren, Glieder bilden, Achsen als Baum, Nicht-Angebundenes
    melden.
  - Klarere Namen:
    - `Gelenk` → `Achse`; das Gelenk-Objekt der Assembly steht in
      `achse.gelenk`.
    - `Kette.gelenke` → `achsen`, `festes_glied()` → `bett()`,
      `pfad_zum_festen_glied()` → `pfad_zum_bett()`.
    - `Glied.koerper` → `bauteile`, `Glied.fest` → `ist_bett`.
  - Neu: `Kette.achse_von(gelenk)`. Sie ersetzt die an fünf Stellen
    wiederholte Suche `next(g for g in kette.gelenke if g.objekt == …)`.
  - `Glied.nummer` entfällt, es wurde nie gelesen.
  - Die Zusammenfassung starr verbundener Bauteile (Union-Find) ist erklärt.
- **maschine.py**
  - Die drei Proxys erben `dumps`/`loads` von einer gemeinsamen Grundklasse.
  - Die Eigenschaften stehen als Tabelle, je Gruppe im Eigenschaften-Editor.
  - `ist_betriebsart()`, `ist_aufnahme()` und `aufnahmeart_text()` ersetzen
    wiederholte Ausdrücke, auch in der Oberfläche.
  - `pruefe()` ist in drei Teile zerlegt: Betriebsarten, Aufnahmen,
    Revolver.
  - Das Entfernen einer früheren Platzverteilung ist eine eigene Funktion.
  - Die Editor-Modi heißen `_SICHTBAR` und `_AUSGEBLENDET` statt 0 und 2.
  - Entfernt:
    - Das Nachrüsten der Eigenschaft `Platz` beim Laden. Dateien ohne sie
      gibt es nur aus der Entwicklung; das Addon war nie veröffentlicht.
    - Eine Wächterzeile, deren Fall nie eintritt. Ausprobiert: FreeCAD ruft
      `onChanged` weder beim Anlegen einer Eigenschaft noch beim Laden
      einer Datei auf (1.1.3 und Wochen-Build).
- **export.py**
  - Linear- und Drehachse entstehen in eigenen Funktionen, mit
    Schlüsselwort-Argumenten statt acht Positions-Argumenten.
  - FreeCADs Vorgaben sind benannte Konstanten: `VORGABE_EILGANG`,
    `VORGABE_DREHGESCHWINDIGKEIT`.
  - Die Eltern-Achse wird über `pfad_zum_bett()` gesucht, nicht mehr über
    ein eigenes Wörterbuch.
- **sprache.py, hilfe.py:** `rueckfall_reihe()` ersetzt dreimal dieselbe
  Sprachfolge.
- **__init__.py, aktualisierung.py**
  - `version_aus_xml()` ersetzt zwei Kopien desselben Codes.
  - Der nie genutzte Parameter `git=` entfällt.
  - `pruefe()` ist in benannte Teile zerlegt: `_vergleiche_mit_github`,
    `_ist_vorfahr`.
- **Sichtbar geändert, beides bewusst:**
  - `pruefe()` liefert erst alle Warnungen, dann die Hinweise. Vorher stand
    der Hinweis „keine Werkzeugaufnahme“ zwischen Warnungen.
  - Die Meldungen der Kette folgen den vier Schritten. Ein loser Körper
    steht jetzt nach „doppelt gelagert“, nicht mehr davor.
- Version 0.3.3, weil sich die Reihenfolge der Meldungen sichtbar ändert.
- **Drei Befunde**, als B-001 bis B-003 in den Snapshot aufgenommen. Sie
  sind nicht behoben, weil 1 Patch = 1 Thema:
  - B-001 und B-002: zwei Lücken im Bericht der Übergabe an CAM.
  - B-003: P-2026-09-25-27 und -28 kamen ohne neue Version auf `main`. Die
    Update-Suche hätte „neue Version 0.3.2 (installiert ist 0.3.2)“
    angezeigt. Mit 0.3.3 ist das für diesmal erledigt, die Ursache bleibt.

### TEST
- Von der KI ausgeführt:
  - black und ruff sauber.
  - `alle_tests.sh` in beiden Versionen grün: 8 Prüfungen und 6 Szenarien;
    in 1.1.3 wird der Export übersprungen.
  - Probe in 1.1.3 und im Wochen-Build: Beim Anlegen einer
    Aufzählungs-Eigenschaft und beim Laden einer Datei ruft FreeCAD
    `onChanged` nicht auf, beim Laden nur `onDocumentRestored`.

### NEXT
- Oberflächen-Module: `gui_maschine` aufteilen und aufräumen, danach
  `gui_zeigen`, `gui_start`, `gui_sprachwahl`, `gui_aktualisierung`.

## P-2026-09-25-28 szenarien-sauber-beenden

### EINGELESEN
- Zeitstempel der Ergebnisdateien aus dem Lauf von P-2026-09-25-27: Drei
  Szenarien je Version brauchten genau 180 s, also das Zeitlimit.

### DATEIEN
- `tests/gui/_lauf/szenario_lauf.py` (am Ende Aufgabenfenster und Dokumente
  schließen)
- `scripts/oberflaeche_testen.sh` (Zeitlimit gilt als Fehler)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`scripts/alle_tests.sh` läuft in beiden FreeCAD-Versionen grün durch, in etwa
2 statt 22 Minuten. Ein Szenario, nach dem FreeCAD sich nicht beendet, gilt
als Fehler.

### DONE
- **Ursache:** Nach Szenarien mit geänderten Dokumenten fragte FreeCAD beim
  Beenden „Änderungen speichern?“ und wartete, bis `timeout` nach 180 s
  abbrach. Das Ergebnis war schon vorher geschrieben, deshalb blieb der
  Fehler unsichtbar.
- Der Läufer schließt jetzt vor dem Beenden das Aufgabenfenster und alle
  Dokumente, ohne Rückfrage.
- `oberflaeche_testen.sh` wertet einen Abbruch durch das Zeitlimit
  (Rückgabe 124) als **Fehler**: „FreeCAD hat sich nicht beendet“. So bleibt
  ein Hänger nie wieder unbemerkt.

### TEST
- Von der KI ausgeführt:
  - `alle_tests.sh` in beiden Versionen grün, **130 s** für alles zusammen
    (vorher etwa 22 Minuten).
  - Gegenprobe ohne das Schließen der Dokumente:
    `szenario_uebergeben` ergibt „FEHLER … FreeCAD hat sich nicht beendet
    (Zeitlimit 180 s)“.

### NEXT
- Durchsicht von Hand: Kern-Module.

## P-2026-09-25-27 black-und-ruff

### EINGELESEN
- Manuels Auftrag: Code gut dokumentiert, kommentiert, für jeden menschlichen
  Programmierer leicht lesbar und sauber, „kein AI-Slop“. Das Vorhandene soll
  kontrolliert und „to the max“ optimiert werden. Dieser Patch ist der erste,
  mechanische Schritt dazu. Die Durchsicht von Hand folgt als eigene Patches.

### DATEIEN
- `pyproject.toml` (neu: Einstellungen für black und ruff)
- Alle Python-Dateien (Formatierung, Reihenfolge der Importe)
- Tests: Dateien über `Path.read_text`/`write_text` statt offener `open()`,
  unbenutzte Importe entfernt oder begründet
- `scripts/testumgebung_einrichten.sh` (installiert black und ruff mit),
  `scripts/alle_tests.sh` (prüft sie als Erstes)
- `docs/arbeitsregeln.md` (Abschnitte 5 und 7), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`black --check .` und `ruff check .` melden nichts, und `scripts/alle_tests.sh`
ist in beiden FreeCAD-Versionen grün.

### DONE
- **Werkzeuge wie bei FreeCAD:** black (Zeilenlänge 100) und ruff. Geprüft
  werden Stil, unbenutzte Namen, typische Fehlerquellen, Importreihenfolge,
  veraltete Schreibweisen für Python 3.11 und unnötig umständliche
  Konstrukte. Python 3.11 ist der Stand, den FreeCAD 1.1.x mitbringt.
- **Ausgangslage:**
  - 19 von 30 Dateien waren uneinheitlich formatiert.
  - 23 Befunde, fast alle in den Tests:
    - `open()` ohne `with`
    - unsortierte Importe
    - zwei unbenutzte Importe
- **Behoben:**
  - Dateien lesen die Tests jetzt über `Path(…).read_text("utf-8")`.
  - Der Import von `Part` in `test_umgebung.py` ist nötig, weil er den
    Objekttyp `Part::Box` registriert. Er bleibt, jetzt mit Begründung.
  - Das offen bleibende Absturzprotokoll im Szenario-Läufer ist begründet
    markiert.
  - Die Tests müssen den Suchpfad vor dem Import setzen. Statt sieben
    verstreuter `# noqa: E402` gibt es jetzt eine Ausnahme für `tests/` in
    `pyproject.toml`.
- **Neue Regeln** (Abschnitte 5 und 7):
  - black und ruff ohne Befund
  - jedes `noqa` mit Begründung
  - Docstrings für Module und öffentliche Funktionen
  - Hilfsfunktion statt Wiederholung

### TEST
- Von der KI ausgeführt: `scripts/alle_tests.sh` ergibt „ok black, ruff“,
  in 1.1.3 und im Wochen-Build alle Prüfungen und Szenarien `ok` (Export in
  1.1.3 übersprungen).
- **Aufgefallen:** Drei Szenarien brauchen jeweils genau 180 s, also das
  Zeitlimit. FreeCAD beendet sich nach dem Szenario nicht von selbst. Das
  Ergebnis steht schon vorher fest, deshalb sind sie trotzdem grün. Behoben
  als eigener Patch.

### NEXT
- Szenarien sauber beenden, dann die Durchsicht von Hand: Kern, Oberfläche,
  Tests, Entwickler-Doku.

## P-2026-09-25-26 zwei-freecad-versionen

### EINGELESEN
- FreeCAD 1.1.3 aus conda-forge. Zuerst nur das Paket entpackt und dessen
  Quelltext mit dem Wochen-Build verglichen, dann als volle Testumgebung.
- `Mod/Assembly/UtilsAssembly.py` und `JointObject.py` in 1.1.3: Welche der
  vom Addon genutzten Funktionen und Eigenschaften gibt es dort?

### DATEIEN
- `camaddon/export.py` (`verfuegbar()`), `camaddon/gui_maschine.py`
  (Erklärung statt Fehler)
- `tests/test_export.py` (übersprungen ohne Maschinendefinition),
  `tests/gui/szenario_uebergeben.py` (prüft in 1.1.3 die Erklärung)
- `scripts/testumgebung_einrichten.sh` (beide Versionen),
  `scripts/alle_tests.sh` (neu), `scripts/tests_ausfuehren.sh` (versteht
  „übersprungen“)
- `translations/de.json`, `translations/en.json`
- `CHATSTART.md` (Festlegung), `docs/arbeitsregeln.md` (Abschnitte 0, 5, 7, 9),
  `README.md`, `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 2),
  `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md` (Kopf)
- `package.xml` (0.3.2)

### AKZEPTANZKRITERIUM
`scripts/alle_tests.sh` läuft in FreeCAD 1.1.3 und im Wochen-Build grün. In
1.1.3 zeigt „An CAM übergeben“ den Satz „Deine FreeCAD-Version (1.1.3) kennt
noch keine Maschinendefinition in CAM …“ statt eines Fehlers.

### DONE
Manuel sitzt am PC und hat **FreeCAD 1.1.3** installiert, nicht den
Wochen-Build. Er fragte, ob dort die 4-Achs-Funktionen fehlen. Das stimmt:
In 1.1.3 fehlen die neuen Rundachs-Strategien (`rotary_*`) und die
CAM-Maschinendefinition. Vorhanden sind nur die alten Hilfen (3D-Oberfläche
„Rotational“, Dressup „Axis Map“).

Die Entscheidung aus P-2026-09-25-05 (nur Wochen-Build) passte damit nicht
mehr zu Manuels Rechner. Aus einer Auswahl hat er **„Beide unterstützen“**
gewählt. Die Alternativen waren „Wochen-Build dazu“ (meine Empfehlung) und
„auf 1.1.3 umstellen“.

- **Befund 1.1.3:**
  - Das Auslesen der Baugruppe, das Maschinenobjekt, der Dialog, das Zeigen,
    die Hilfe und die Update-Suche laufen unverändert.
  - Es fehlen die Eigenschaft `Suppressed` und die RigidGroup-Gelenke. Das
    Addon fragt sie nur mit `getattr`/`hasattr` ab, deshalb schadet das nicht.
  - Einziger echter Ausfall ist der Export, weil `Mod/CAM/Machine` fehlt.
- **Der Export erklärt sich:** `export.verfuegbar()` prüft das Modul und nicht
  eine Versionsnummer. So wird die Übergabe von selbst frei, sobald die
  stabile Version sie bekommt. Der Knopf bleibt bedienbar und zeigt eine
  Erklärung, weil ein grauer Knopf nichts erklärt. Die Erklärung ist nicht
  blockierend (`open()` statt `exec()`).
- **Tests in beiden Versionen:**
  - `testumgebung_einrichten.sh` installiert beide: den Wochen-Build und
    `freecad<2000` mit Python 3.11, wie in den offiziellen Paketen.
    Wochen-Builds tragen ein Datum als Versionsnummer.
  - `alle_tests.sh` lässt alles in beiden laufen.
  - „Übersprungen“ ist nur für fehlende Funktionen einer Version erlaubt.
    Das Szenario prüft dort stattdessen die Erklärung.
- Die Regeln sind angepasst: Festlegung in `CHATSTART.md`, Zielsystem,
  Pflichtprüfung in beiden Versionen, Versionscheck auch für neue stabile
  Versionen. Die vorige stabile Version fällt heraus, sobald eine neue da ist.
- Beim ersten Lauf gegen 1.1.3 kam ein Fehler ans Licht, der beide Versionen
  betraf: Ursprünge wurden als Koordinatensystem angeboten. Er ist als
  eigener Patch behoben (P-2026-09-25-25).

### TEST
- Von der KI ausgeführt, `scripts/alle_tests.sh`:
  - 1.1.3: acht Prüfungen ohne Fenster, davon eine übersprungen (Export),
    alle Szenarien `ok`
  - Wochen-Build: alle Prüfungen `ok`, alle Szenarien `ok`
  - Screenshot der Erklärung in 1.1.3 angesehen
- `testumgebung_einrichten.sh` selbst ist nicht von Grund auf durchgelaufen.
  Die beiden `micromamba create` darin habe ich von Hand mit denselben
  Angaben ausgeführt.
- **Nicht getestet:** Manuels FreeCAD 1.1.3 unter Windows.

### NEXT
- Manuels Test in 1.1.3: Installation mit GitHub Desktop, Dialog, Erklärung
  bei „An CAM übergeben“, Update-Suche.

## P-2026-09-25-25 lcs-auswahl-ohne-ursprung

### EINGELESEN
- `camaddon/gui_maschine.py` (`_alle_lcs`, Verteilhilfe, `_aufnahme_neu`).
- Befund aus dem ersten Lauf der Oberflächentests gegen FreeCAD 1.1.3.

### DATEIEN
- `camaddon/gui_maschine.py`, `tests/gui/szenario_maschine_bearbeiten.py`
- `package.xml` (0.3.1), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In der Auswahl „Koordinatensystem“ einer Aufnahme und in der Verteilhilfe
stehen nur echte Koordinatensysteme (Spannflaeche, Werkzeugplatz), keine
Ursprünge wie „Origin005“.

### DONE
- **Befund:** Der Ursprung eines Parts oder Körpers (`App::Origin`) ist für
  FreeCAD ebenfalls ein `App::LocalCoordinateSystem`. Der Dialog bot deshalb
  „Origin“, „Origin001“ … als Koordinatensystem für Aufnahmen an. Beim
  Anlegen einer Aufnahme ohne Auswahl konnte die Vorauswahl sogar einen
  Ursprung treffen. Aufgefallen ist das im Test gegen 1.1.3, weil dort die
  Reihenfolge anders ist und die Verteilhilfe „Origin005“ statt
  „Werkzeugplatz“ vorwählte. Der Fehler steckte aber in beiden Versionen.
- `_alle_lcs()` lässt Ursprünge weg. Das wirkt auf die Auswahlliste, die
  Vorauswahl bei „+ Aufnahme“ und die Verteilhilfe.
- Das Szenario prüft jetzt, dass die Verteilhilfe **nur** den Werkzeugplatz
  anbietet und dass nirgends ein Ursprung auftaucht.

### TEST
- Von der KI ausgeführt: `szenario_maschine_bearbeiten` `ok`, auf 1.1.3 und
  im Wochen-Build.
- Gegenprobe mit altem Dialog und neuer Prüfung im Wochen-Build: `FEHLER`,
  „Ursprünge als Koordinatensystem angeboten: ['Origin', 'Spannflaeche',
  'Origin001', 'Werkzeugplatz', 'Origin002']“.

### NEXT
- Beide FreeCAD-Versionen fest in Tests und Regeln verankern, Übergabe an CAM
  in 1.1.3 erklären statt Fehler.

## P-2026-09-25-24 update-suche-per-git

### EINGELESEN
- Ergebnis P-2026-09-25-23: Der Addon-Manager aktualisiert private
  Repositories nicht.
- `docs/arbeitsregeln.md` Abschnitt 7 („keine Shell-Aufrufe“).

### DATEIEN
- `camaddon/aktualisierung.py`, `camaddon/gui_aktualisierung.py` (neu)
- `camaddon/gui_start.py` (Suche beim Start), `camaddon/gui_sprachwahl.py`
  (Gruppe „Updates“ auf der Einstellungsseite)
- `translations/de.json`, `translations/en.json`
- `tests/test_aktualisierung.py`, `tests/gui/szenario_update.py` (neu),
  `scripts/oberflaeche_testen.sh` (ohne Update-Suche)
- `package.xml` (0.3.0), `README.md`, `CHATSTART.md`,
  `docs/arbeitsregeln.md` (Ausnahme Git), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Liegt auf GitHub eine neuere Version, fragt das Addon kurz nach dem Start
von FreeCAD „Eine neue Version des CAM-Addons ist da: … Jetzt
aktualisieren?“. Ein Klick holt sie und bittet um einen Neustart.

### DONE
Manuel hat aus einer Auswahl gewählt: Das Addon soll in der privaten Phase
**selbst nach Updates schauen und nachfragen**. Dafür hat er einer Ausnahme
von der Regel „keine Aufrufe externer Programme“ zugestimmt, beschränkt auf
Git.

- **Suche:** Das Addon ruft Git im eigenen Ordner auf (`fetch`, Vergleich mit
  `origin/main`, Version aus `package.xml` auf beiden Seiten). Das passiert
  im Hintergrund und 5 s nach dem Start, damit FreeCAD nicht wartet. Git
  kommt aus dem Suchpfad, sonst aus GitHub Desktop, das sein Git unter
  Windows nicht in den Suchpfad legt. Angemeldet wird mit dem, was auf dem
  Rechner eingerichtet ist. Im Addon liegt kein Schlüssel.
- **Git fragt nie nach**: Es gibt kein Terminal, keinen Credential-Dialog
  und ein Zeitlimit von 30 s. Ohne Fenster würde eine Rückfrage ewig hängen.
- **Aktualisieren:** nur vorwärts (`merge --ff-only`). Gibt es im Ordner
  eigene Änderungen oder eigene Commits, aktualisiert das Addon nicht,
  sondern sagt Bescheid, einmal je neuer Version.
- **Ruhig bleiben:** Kein Git auf dem Rechner meldet das Addon einmal mit
  Anleitung. Kein Netz oder keine Anmeldung führt beim Start nur zu einer
  Zeile im Report-Fenster. Eine ZIP-Installation oder ein aktueller Stand
  bleiben still.
- **Einstellungen:** Schalter „Beim Start von FreeCAD nach Updates suchen“
  (vorbelegt: an) und Knopf „Jetzt nach Updates suchen“. Der Knopf meldet
  auch „Du hast die neueste Version“.
- **Befund:** Die Ausgabe von Git wurde mit der Kodierung des Systems gelesen,
  `package.xml` enthält aber Umlaute. Im Test brach das mit einem
  ASCII-Fehler ab, unter Windows (cp1252) wäre es genauso passiert. Jetzt
  wird immer UTF-8 gelesen.
- Die Oberflächen-Szenarien schalten die Suche beim Start ab
  (`CAMADDON_OHNE_UPDATE`), damit sie kein Netz brauchen.
- Die Version ist jetzt 0.3.0, weil eine neue Funktion dazukam (Regel aus
  P-2026-09-25-22).

### TEST
- Von der KI ausgeführt, mit echten Git-Repos im Temp-Ordner (nacktes Repo
  als „GitHub“):
  - `test_aktualisierung.py` `ok`, mit den Fällen aktuell, neue Version,
    aktualisieren, eigene Änderung, kein Git-Ordner, kein Git und Repo nicht
    erreichbar
  - `szenario_update` `ok`: Der Hinweis erscheint, „Jetzt aktualisieren“ holt
    9.9.0, und das Abschalten in den Einstellungen wird gespeichert.
    Screenshots angesehen.
- Alle Prüfungen ohne Fenster und alle Szenarien `ok`.
- **Nicht getestet:** die Anmeldung über GitHub Desktop auf Manuels
  Windows-Rechner. Ob dessen Git ohne Rückfrage an das private Repo kommt,
  zeigt erst der echte Rechner. Wenn nicht, erscheint beim Start nur eine
  Zeile im Report-Fenster, und „Jetzt nach Updates suchen“ nennt den Grund.

### NEXT
- Manuels Test: Installation mit GitHub Desktop, dann Dialog, Übergabe an
  CAM und Update-Hinweis.

## P-2026-09-25-23 installieren-privat

### EINGELESEN
- `Mod/AddonManager`: `addonmanager_installer.py` (`_determine_install_method`,
  `_install_by_copy`), `addonmanager_utilities.construct_git_url` (lokale
  Pfade), `addonmanager_workers_startup.UpdateChecker`.

### DATEIEN
- `README.md` (Installieren in der privaten Phase mit GitHub Desktop, dazu
  der Addon-Manager-Weg für später)
- `docs/STATUS_SNAPSHOT.md` (T-005), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Das README führt als ersten Weg die Installation mit GitHub Desktop direkt in
den Mod-Ordner; der Addon-Manager-Weg ist als „erst wenn öffentlich“
gekennzeichnet.

### DONE
Manuel will das Repo vorerst **nicht veröffentlichen**. Zum Testen soll es
lokal bleiben. Deshalb habe ich ausprobiert, ob der Addon-Manager mit einem
**lokalen Ordner** als eigenem Repository arbeitet: unsichtbare Oberfläche,
eigenes Profil, lokaler Klon des Repos.

- Die **Installation** klappt. Der Addon-Manager kopiert den Ordner.
  Allerdings liest er `package.xml` aus einem lokalen Pfad nicht und zeigt
  das Addon deshalb ohne Beschreibung an.
- **Updates** erkennt er nicht: Nach einem neuen Commit im lokalen Ordner
  meldet er „No update available“. Der eingebaute Git-Stand zeigt weiter auf
  GitHub, und dort kommt er nicht hin.
- Ergebnis: In der privaten Phase bringt der Addon-Manager nichts. Der
  einfachste Weg ist GitHub Desktop, das Repo direkt in den Mod-Ordner holen
  und zum Aktualisieren „Pull“ drücken. Das README beschreibt das jetzt als
  ersten Weg.
- **Fehler im Testaufbau, gefunden und folgenlos:** Beim ersten Versuch lief
  der Addon-Manager im Profil von `oberflaeche_testen.sh`. Dort ist unser
  Repo als Verknüpfung im Mod-Ordner eingetragen, also kopierte der
  Addon-Manager durch die Verknüpfung **in unser Repo**. Danach geprüft:
  `git status` sauber, `git fsck` ohne Befund. Die Kopie war derselbe Stand.
  Den sauberen Versuch habe ich in einem eigenen Profil ohne die Verknüpfung
  gemacht. Für Tests des Addon-Managers darf dieses Skript nicht benutzt
  werden.
- Die Regel „was auf `main` liegt, kommt als Update an“ (P-2026-09-25-22)
  bleibt, denn mit GitHub Desktop gilt sie genauso.

### TEST
- Von der KI ausgeführt, in einem eigenen Profil unter Xvfb:
  `AddonInstaller.run()` mit lokalem Pfad ergibt `True`, der Ordner liegt im
  Mod-Verzeichnis. `UpdateChecker.check_workbench` ergibt nach einem neuen
  Commit im lokalen Ordner „No update available“.
- Die Installation mit GitHub Desktop auf Manuels Rechner ist nicht
  getestet.

### NEXT
- Manuel entscheidet, ob das Addon für die private Phase selbst nach Updates
  schauen soll (Git im eigenen Ordner).

## P-2026-09-25-22 updates-ueber-addon-manager

### EINGELESEN
- `Mod/AddonManager/addonmanager_workers_startup.py`: `CustomRepositories`
  (eigene Repositories, je Zeile URL und Branch) und `UpdateChecker`. Bei
  Installation per Git wird über den Git-Stand geprüft, sonst über eine
  geänderte `package.xml`.

### DATEIEN
- `camaddon/__init__.py` (Version aus `package.xml`), `package.xml`
  (0.2.0)
- `tests/test_version.py` (neu)
- `README.md` (Installieren mit automatischen Updates),
  `docs/arbeitsregeln.md` (Abschnitt 4)
- `docs/STATUS_SNAPSHOT.md` (T-005), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer das README liest, kann das Addon als eigenes Repository in den
Addon-Manager eintragen und installieren. Das Addon meldet unter „Über“
dieselbe Version wie `package.xml`.

### DONE
Manuel hat gefragt, ob Autoupdate geht. Aus einer Auswahl hat er gewählt:
**Repo öffentlich machen**, Updates über FreeCADs Addon-Manager. Die
Alternativen waren „privat, später öffentlich“ und ein eigener Update-Knopf
mit GitHub-Schlüssel je Rechner, von dem ich abgeraten habe.

- **Kein eigener Update-Code nötig.** Der Addon-Manager prüft und
  installiert selbst, wenn das Repo als „eigenes Repository“ eingetragen ist.
  Voraussetzung: Das Repo ist öffentlich. Das Umschalten kann nur Manuel
  machen (T-005).
- **Version nur noch an einer Stelle:** `package.xml`. `camaddon.VERSION`
  liest sie von dort. Vorher stand 0.1.0 zusätzlich im Code; zwei Angaben
  wären auseinandergelaufen. Die Version ist jetzt 0.2.0, weil seit 0.1.0 der
  Dialog und die Übergabe an CAM dazugekommen sind.
- **Neue Regel** (Abschnitt 4): Was auf `main` liegt, kommt bei Manuel als
  Update an. Gepusht wird nur, was alle Prüfungen bestanden hat. Ein Push mit
  sichtbarer Änderung zählt die Version hoch.
- Vor dem Öffentlichmachen habe ich das Repo durchgesehen: keine
  E-Mail-Adresse, keine Zugangsdaten. Manuel ist darauf hingewiesen, dass
  sein Name in `package.xml` und der Doku steht und dass „zeiterfassung“
  einmal als Vorlage erwähnt wird.

### TEST
- Von der KI ausgeführt: alle sieben Prüfungen ohne Fenster `ok`, die
  Szenarien `erster_start` und `uebergeben` `ok`.
- Gegenprobe: Mit Version „0.2“ schlägt `test_version.py` fehl („hat nicht
  die Form 1.2.3“).
- **Nicht getestet:** Installation und Update über den Addon-Manager. Das
  geht erst, wenn das Repo öffentlich ist, und gehört dann zu Manuels Test.

### NEXT
- T-005 (Manuel), dann Test über den Addon-Manager.

## P-2026-09-25-21 knopf-an-cam-uebergeben

### EINGELESEN
- `camaddon/export.py` (P-2026-09-25-20), Spezifikation W-001, Stufe 2.

### DATEIEN
- `camaddon/gui_maschine.py` (Knopf, Nachfrage, Berichtsfenster)
- `camaddon/export.py` (Bericht in drei Teilen, Drehachsen in U/min)
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_uebergeben.py` (neu), `tests/test_export.py`
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Klick auf „An CAM übergeben“ im Dialog der fertigen Beispiel-Drehmaschine
öffnet ein Fenster „Die Maschine „Testdrehmaschine“ steht jetzt in CAM zur
Auswahl.“ mit den angekommenen Achsen, und CAM listet die Maschine.

### DONE
- Unten im Dialog gibt es den Knopf **„An CAM übergeben“**:
  - Gibt es noch Warnungen, fragt er nach, ob trotzdem übergeben werden soll,
    und nennt die Anzahl.
  - Schlägt das Speichern fehl, erscheint eine Meldung mit dem Grund.
- Das **Berichtsfenster** sagt, wo die Maschine in CAM zu finden ist, und
  gliedert sich in drei Teile:
  - **In CAM angekommen**
  - **Bitte prüfen**: fehlende Grenzen, unklare Tisch/Kopf-Rolle, Fehler in
    der Achsfolge
  - **Nur hier in der Maschine gespeichert**: Beschleunigung, Ruck, Vorschub,
    Revolver
- **Beim Durchsehen des ersten Screenshots verbessert:**
  - Drehachsen standen in °/min im Bericht, eingegeben werden aber U/min.
    Jetzt steht die eingegebene Einheit da.
  - „Keine Begrenzung“ stand unter „Nur hier gespeichert“. Dafür gibt es
    jetzt den eigenen Teil „Bitte prüfen“.
- Beim Schreiben der Texte waren Zeilenumbrüche als `\n`-Zeichen im Text
  gelandet. Das ist korrigiert.

### TEST
- Von der KI ausgeführt: alle Prüfungen ohne Fenster `ok`, alle fünf
  Szenarien `ok`, Screenshot des Berichts angesehen.
- **Nicht geprüft:** Das Szenario prüft nur, dass CAM die Maschine listet.
  Ob sie im Job-Dialog von CAM tatsächlich auswählbar ist und dort richtig
  arbeitet, prüft Manuel.
- Die Nachfrage bei Warnungen erscheint als modaler Dialog und blockiert
  deshalb das Szenario. Sie ist im Test umgangen (`nachfragen=False`) und nicht
  automatisch geprüft.

### NEXT
- Manuels Test von Stufe 1 und 2, danach Stufe 3 (von Hand verfahren).

## P-2026-09-25-20 export-cam-maschine

### EINGELESEN
- Spezifikation W-001, Stufe 2.
- `Mod/CAM/Machine/models/machine.py`: `Machine`, `LinearAxis`,
  `RotaryAxis`, `Toolhead`, `to_dict`/`from_dict`,
  `MachineFactory.save_configuration`/`list_configurations`,
  `validate_kinematic_chain`.

### DATEIEN
- `camaddon/export.py` (neu)
- `tests/test_export.py` (neu), `tests/beispielmaschinen.py`
  (`drehmaschine_komplett`)
- `translations/de.json`, `translations/en.json`
- `CHATSTART.md` (Lesekarte), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die fertig beschriebene Beispiel-Drehmaschine wird als `Testdrehmaschine.fcm`
gespeichert. CAM listet sie danach, und neu geladen hat sie X1 (Richtung X,
0–200 mm, 24000 mm/min, hängt an Z1, im Kopf), Z1, C4 (Tisch, 36000 °/min)
und die Spindel S4.

### DONE
- `baue_cam_maschine()` übersetzt das Maschinenobjekt in FreeCADs `Machine`:
  - Linear → `LinearAxis`, Positionieren → `RotaryAxis` (U/min × 360 =
    °/min), Spindel → `Toolhead`.
  - Tisch/Kopf aus `rollen()`.
  - Die Eltern-Achse ist die nächste NC-Achse zum Bett hin. Gelenke nur mit
    Spindel oder Revolver werden übersprungen.
  - Die Grenzen kommen aus dem Gelenk. Fehlen sie, gibt es einen sehr großen
    Bereich und einen Satz im Bericht.
- `exportiere()` speichert über `MachineFactory.save_configuration` in den
  Maschinenordner von CAM. Der Dateiname kommt aus dem Maschinennamen, ein
  zweiter Export überschreibt dieselbe Datei.
- **Bericht** in ganzen Sätzen: was übertragen wurde, und was CAM nicht kennt
  und deshalb nur im Dokument bleibt (größter Vorschub, Beschleunigung, Ruck,
  Revolver mit Plätzen, fehlende Grenzen, unklare Tisch/Kopf-Rolle, Fehler
  aus `validate_kinematic_chain`).
- **Befund: Fehler in FreeCAD.** `Machine.to_dict` schreibt eine Achse als
  `[Ursprung, Richtung]`. `Machine.from_dict` hält bei Linearachsen aber den
  Ursprung für die Richtung, sobald er nicht (0,0,0) ist. Jede solche
  Linearachse kommt nach Speichern und Laden verdreht zurück; im Test wurde X1
  von (1,0,0) zu (0,95, 0,25, 0,18). Umgangen, indem Linearachsen mit Ursprung
  (0,0,0) übergeben werden. Für eine Linearachse zählt nur die Richtung. Der
  Fehler sollte bei FreeCAD gemeldet werden; das ist ein eigener Punkt im
  Snapshot.
- Der Test schreibt nicht in Manuels echten CAM-Ordner
  (`set_config_directory` auf einen Temp-Ordner) und stellt die Sprache für
  seine Satzprüfungen fest auf Deutsch.

### TEST
- Von der KI ohne Fenster ausgeführt: alle sechs Prüfungen `ok`, volle
  Ausgabe von `test_export.py` ohne Warnungen.
- Ohne den Umweg über Ursprung 0 schlug `test_export.py` fehl: „X1: Richtung X
  erwartet“. So wurde der FreeCAD-Fehler gefunden.

### NEXT
- Knopf „An CAM übergeben“ im Dialog mit Anzeige des Berichts.

## P-2026-09-25-19 hilfe-im-dialog

### EINGELESEN
- Spezifikation W-001, Abschnitte 8 und 11. Die Anleitung „Beschleunigung
  ermitteln“ ist aus Abschnitt 8 übernommen.
- `docs/arbeitsregeln.md`, Abschnitt 8 (drei Stufen Hilfe).

### DATEIEN
- `help/de/*.html`, `help/en/*.html` (je vier Seiten, neu)
- `camaddon/hilfe.py` (neu), `camaddon/gui_maschine.py`
- `translations/de.json`, `translations/en.json`, `translations/README.md`
- `tests/test_hilfe.py`, `tests/gui/szenario_hilfe.py` (neu)
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein Klick auf (?) bei „Achsen“ öffnet die Seite „Achsen und Betriebsarten“.
Ihr Verweis führt zu „Beschleunigung ermitteln“, und bei einer linearen
Betriebsart steht unter den Feldern der Verweis „Wie finde ich die
Beschleunigung heraus?“.

### DONE
- **Vier Hilfeseiten** auf Deutsch und Englisch:
  - Achsen und Betriebsarten (mit S4/C4, Gelenken ohne Betriebsart, Kennwerten
    und Zeigen)
  - Beschleunigung ermitteln (Maschinendaten, Datenblatt, Messen mit
    Beispiel)
  - Aufnahmen und Revolver (LCS anlegen, Verteilhilfe)
  - Glieder (Schwenkbrücke, eine Achse ein Gelenk)
- **Knöpfe (?)** rechts neben den Überschriften Achsen, Aufnahmen und
  Glieder. Das Hilfefenster ist nicht modal, damit man lesen und dabei
  weiterarbeiten kann. Verweise zwischen den Seiten funktionieren.
- Bei Betriebsarten mit Beschleunigung steht der Verweis „Wie finde ich die
  Beschleunigung heraus?“ direkt unter den Feldern, also dort, wo die Frage
  aufkommt.
- Für die Hilfe gilt derselbe Rückfall wie für die kurzen Texte: gewählte
  Sprache, Englisch, Deutsch. `translations/README.md` erklärt jetzt auch das
  Übersetzen der Hilfe.
- `test_hilfe.py` prüft:
  - jedes Thema auf de und en vorhanden, mit Überschrift
  - keine toten Verweise zwischen den Seiten
  - keine Seite ohne Thema
  - jedes vom Dialog benutzte Thema existiert
- Die Hilfe zur Beschleunigung sagt ausdrücklich, dass die
  Maschinendaten-Nummern aus allgemeinem Wissen stammen und im Handbuch zu
  prüfen sind. Das Gleiche steht als offener Punkt in P-2026-09-25-07.

### TEST
- Von der KI ausgeführt: alle Prüfungen ohne Fenster `ok` (jetzt fünf),
  alle vier Szenarien `ok`.
- Screenshots beider Hilfeseiten angesehen: gut lesbar, Tabelle und Formel
  werden sauber dargestellt.

### NEXT
- Manuels Test des Dialogs in seinem FreeCAD, danach Stufe 2 (Export).

## P-2026-09-25-18 zeigen-in-3d

### EINGELESEN
- Spezifikation W-001, Abschnitt 11 („Zeigen, welches Teil gemeint ist“).
- `camaddon/gui_maschine.py` (P-2026-09-25-17).

### DATEIEN
- `camaddon/gui_zeigen.py` (neu), `camaddon/gui_maschine.py`
- `tests/gui/szenario_zeigen.py` (neu)
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Fährt man im Dialog über die Achse X der Beispiel-Drehmaschine, werden
X-Schlitten und Revolver hervorgehoben und bewegen sich einmal kurz hin und
her, Bett und Z-Schlitten nicht. Danach steht alles exakt wie vorher, auch
wenn mitten in der Bewegung OK gedrückt wird.

### DONE
- **Überfahren einer Zeile** (nach 250 ms Verweilen, nicht bei jedem
  Überstreichen):
  - **Gelenk oder Betriebsart:** Alle Körper, die sich mit dem Gelenk
    bewegen, auch weiter hinten in der Kette, werden hervorgehoben und
    bewegen sich einmal hin und her. Eine Linearachse fährt 10 % der
    Gliedgröße (5–50 mm), eine Drehachse dreht ±15° um ihre Achse.
  - **Glied:** Seine Körper werden hervorgehoben.
  - **Aufnahme:** Ihr LCS wird hervorgehoben.
  - **Revolvergruppe:** Alle Platz-LCS werden hervorgehoben.
- Das Hervorheben läuft über die Auswahl von FreeCAD, weil die Vorauswahl nur
  ein Objekt kann und ein Glied mehrere Körper hat.
- Die Bewegung verstellt keine Gelenke, sondern nur kurz die Lage der Körper.
  Danach wird die gespeicherte Lage exakt zurückgesetzt. Läuft die Bewegung
  für dasselbe Gelenk schon, beginnt sie nicht neu. OK und Abbrechen halten
  sie zuerst an und setzen zurück, erst danach wird die Transaktion
  abgeschlossen. So kann nichts Verschobenes gespeichert werden.

### TEST
- Von der KI ausgeführt: `szenario_zeigen` `ok`.
  - Beim Zeigen auf X bewegen sich X-Schlitten und Revolver, Bett, Z-Schlitten
    und Hauptspindel nicht.
  - Hervorgehoben sind genau X-Schlitten und Revolver.
  - Nach der Bewegung steht alles auf 1e-12 genau wie vorher.
  - Beim Glied der Spindel sind Hauptspindel und Futter hervorgehoben.
  - OK während der Revolver dreht lässt ihn nicht verdreht zurück.
- Alle Prüfungen ohne Fenster und alle drei Szenarien `ok`.
- **Nicht prüfbar im Test:** das echte Überfahren mit der Maus. Unter Xvfb
  gibt es keine Maus, deshalb ruft das Szenario die Zeige-Funktion direkt auf.
  Ob sich das Verweilen von 250 ms gut anfühlt, prüft Manuel.

### NEXT
- Hilfe-Knöpfe (?) mit den ausführlichen Texten.

## P-2026-09-25-17 dialog-maschine-bearbeiten

### EINGELESEN
- Spezifikation W-001, Abschnitte 7a und 11. Die Skizze des Dialogs hat Manuel
  im Chat mit „ganz ok“ freigegeben.

### DATEIEN
- `camaddon/gui_maschine.py` (neu), `resources/icons/maschine.svg` (neu)
- `camaddon/gui_start.py` (Befehl in der Werkzeugleiste)
- `camaddon/kette.py` (`Meldung.bezug`), `camaddon/maschine.py` (`bezug` an
  den Meldungen, `Bezeichnung`, `name_von`, `beschrifte`)
- `translations/de.json`, `translations/en.json`
- `tests/gui/szenario_maschine_bearbeiten.py` (neu), `tests/test_maschine.py`
- `tests/gui/_lauf/szenario_lauf.py` (Absturzprotokoll),
  `scripts/oberflaeche_testen.sh` (Fehler bei mehreren Szenarien behoben)
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ablauf: Beispiel-Drehmaschine öffnen → „Maschine bearbeiten“ → Z1, X1, S4
und C4 (an der Spindel) sowie Revolver T anlegen und ausfüllen → Futter als
Werkstückaufnahme → 12 Plätze verteilen. Danach zeigt der Dialog „Alles
vollständig – keine Hinweise.“, OK ergibt genau einen Schritt Rückgängig,
Abbrechen verwirft.

### DONE
- **Befehl „Maschine bearbeiten“** in der Werkzeugleiste des Addons:
  - Die Baugruppe kommt aus der Auswahl, sonst aus der aktiven Assembly,
    sonst aus der einzigen im Dokument. Gibt es mehrere, fragt der Befehl.
  - Gibt es keine, erklärt eine Meldung, was zu tun ist. Der Knopf ist dafür
    nicht ausgegraut, denn ein grauer Knopf erklärt nichts.
- **Aufgabenfenster** nach der freigegebenen Skizze, mit den Bereichen Name,
  Achsen, Details, Aufnahmen, Glieder und Hinweise:
  - Das ganze Fenster ist **eine Transaktion**. OK ergibt einen Schritt
    Rückgängig, Abbrechen verwirft alles.
  - „+ Betriebsart“ bietet nur Arten an, die zum Gelenk passen, jeweils mit
    einem Satz Erklärung.
  - Pflichtfelder sind fett, leere optionale Felder zeigen „unbekannt“, die
    Einheit steht am Feld.
  - Das erste Gelenk ist beim Öffnen gewählt, damit „+ Betriebsart“ sofort
    bedienbar ist.
  - Revolverplätze stehen zugeklappt unter „Revolver T – 12 Plätze“.
  - Der Detailkasten erscheint unter der Liste, in der gerade gewählt ist.
  - Ein Klick auf einen Hinweis springt zur betroffenen Zeile.
  - „Plätze verteilen …“ öffnet einen kleinen Dialog für Revolver, ersten
    Platz und Anzahl.
- **Beim Durchsehen der Screenshots verbessert** (nach unserer Regel „keine
  Frage auf dem Bildschirm“):
  1. „+ Betriebsart“ war beim Öffnen ausgegraut.
  2. „wird von Hand verstellt“ stand anfangs bei jedem Gelenk. Jetzt steht
     dort „noch keine Betriebsart“, die Erklärung ist im Tooltip.
  3. Die Details einer Aufnahme standen oben bei den Achsen.
  4. Zwölf Plätze machten die Liste unübersichtlich.
  5. Der Detailtitel sagte nur „Werkzeug“.
- **Befund, Namen:** Eine Aufnahme „Futter“ hieß plötzlich „Futter001“, weil
  FreeCAD kein Label doppelt erlaubt und das Bauteil schon „Futter“ heißt.
  Deshalb gibt es jetzt `Bezeichnung` für Aufnahmen und `NcName` für
  Betriebsarten als eigentliche Namen. Das Label im Baum wird daraus gebildet
  („Futter · Werkstückaufnahme“, „X1 · Linear“), und die Meldungen nennen
  den Namen, nicht das Label.
- **Befund, Abstürze** (FreeCAD stürzte ab, gefunden mit dem neuen
  Absturzprotokoll):
  1. `int()` auf die Knopf-Konstanten scheitert unter PySide6. Jetzt werden
     die Flags direkt zurückgegeben.
  2. Das zeitversetzte Auffrischen nach einer Eingabe griff auf die Listen
     eines schon geschlossenen Fensters zu. Das konnte auch in der Praxis
     passieren: tippen und sofort OK. Jetzt wird geprüft, ob das Fenster
     geschlossen ist.
  3. Die Listen nach jeder Eingabe mit `clear()` neu aufzubauen, stürzte
     gelegentlich ab. Jetzt werden bei Eingaben nur Texte und Symbole der
     vorhandenen Zeilen erneuert. Neu gebaut wird nur, wenn Zeilen dazukommen
     oder wegfallen.
- **Testwerkzeug:**
  - `szenario_lauf.py` schreibt bei einem Segfault den Python-Stack nach
    `absturz.txt` (faulthandler).
  - `oberflaeche_testen.sh` hielt ohne Argument das zweite Szenario für den
    Ausgabeordner. Der Ordner kommt jetzt nur noch aus `$AUSGABE`.

### TEST
- Von der KI ausgeführt:
  - `tests_ausfuehren.sh`: alle vier Prüfungen `ok`.
  - `oberflaeche_testen.sh`: beide Szenarien, **fünfmal hintereinander**
    `ok`. Das war nötig, weil der Absturz nur ab und zu auftrat.
  - Screenshots angesehen: leer, X1 gewählt, Verteilen, vollständig mit P3
    gewählt, Hinweis angeklickt.
- **Nicht getestet:** Bedienung in Manuels FreeCAD. Die Aufgabenleiste liegt
  im Test über der 3D-Ansicht und nicht links in der Kombiansicht. Das ist
  eine Eigenheit des leeren Testprofils.

### NEXT
- Hervorheben und kurzes Bewegen in der 3D-Ansicht, danach die Hilfetexte.

## P-2026-09-25-16 revolver-plaetze-verteilhilfe

### EINGELESEN
- Spezifikation W-001, Abschnitt 7a (P-2026-09-25-15).
- `App.GeoFeature.getGlobalPlacementOf.__doc__` (Nachfolger der veralteten
  `getGlobalPlacement`).

### DATEIEN
- `camaddon/maschine.py`
- `tests/beispielmaschinen.py` (Revolver drehbar), `tests/test_kette.py`,
  `tests/test_maschine.py`
- `translations/de.json`, `translations/en.json`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
An der Beispiel-Drehmaschine legt `verteile_plaetze` zum Werkzeugplatz 11
weitere an, gleichmäßig im 30°-Abstand um die Revolverachse und benannt als
P1 … P12. Neu verteilt auf 6 Plätze bleiben genau 6, ohne übrig gebliebene
LCS.

### DONE
- Neue Betriebsart **Revolver** (Kennwert: Schaltzeit je Platz). Sie passt
  nur an Drehgelenke und lässt sich mit Positionieren kombinieren.
- Werkzeugaufnahmen haben eine **Platznummer**. `plaetze()` liefert alle
  Werkzeugaufnahmen im Glied hinter dem Revolvergelenk, nach Nummer
  sortiert.
- Die Prüfung meldet einen Revolver ohne Plätze sowie doppelte oder fehlende
  Platznummern.
- **Verteilhilfe** `verteile_plaetze()`: Sie dreht den ersten Platz um die
  Revolverachse (aus der Kette: Ursprung und Richtung) und legt je Platz ein
  LCS neben dem ersten im selben Bauteil an. Wird erneut verteilt, ersetzt
  sie ihre eigenen früheren LCS, erkennbar am Namen `<erstes>_P…`. Von Hand
  angelegte LCS fasst sie nicht an.
- **Drei Befunde aus dem Test**, alle behoben:
  1. Ein einfacher Link vom Maschinenobjekt auf ein LCS in einem Part ist für
     FreeCAD „out of scope“. `Lcs` ist jetzt `PropertyLinkGlobal`, so macht
     es die Assembly bei `ObjectToGround` auch.
  2. `getGlobalPlacement()` ist seit 26.3 veraltet und hätte eine
     Deprecation-Warnung erzeugt. Jetzt gibt es eine eigene Funktion
     `globale_platzierung()` über `Parents` und `getPlacementOf`, wie
     `UtilsAssembly.getGlobalPlacement`.
  3. Beim Löschen alter LCS verschwinden deren Achsen und Ebenen mit. Die
     Schleife arbeitet deshalb mit Namen statt mit Objekten.
- Die Beispiel-Drehmaschine hat jetzt einen drehbaren Revolver
  (`Revolverachse`). Die Erwartungen in `test_kette.py` sind entsprechend
  angepasst: 5 Glieder, 4 Achsen, Pfad Revolver → Revolverachse, X, Z.

### TEST
- Von der KI ohne Fenster ausgeführt: alle vier Prüfungen `ok`.
- Volle Ausgabe aller Prüfungen durchgesehen. Außer den erwarteten
  „Solve failed“-Meldungen des absichtlich doppelt gelagerten Fünfachsers gibt
  es keine Warnungen, auch kein „out of scope“ und keine Deprecation.
- **Nicht geprüft:** ein Revolver als echte Unter-Baugruppe (Assembly in
  Assembly). Dass die LCS darin gefunden werden, ist in P-2026-09-25-15 nur
  von Hand ausprobiert. Eine Beispielmaschine dafür kommt mit dem Dialog.

### NEXT
- Dialog „Maschine bearbeiten“.

## P-2026-09-25-15 spezifikation-revolver-und-beispiele

### EINGELESEN
- Spezifikation W-001, Abschnitte 4 und 7.
- Ausprobiert: Eine Baugruppe in einer Baugruppe zählt in der äußeren als
  **ein** Bauteil (`getMovablePartsWithin`). Die LCS darin findet
  `Kette.glied_von` trotzdem.

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 4, neu 7a und 7b,
  „Entschieden“)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die Spezifikation liest, erfährt, wie ein Revolver mit Plätzen P1 … Pn
als eigene Baugruppe eingebunden wird und wie 4. Achse, Gegenspindel und
Reitstock einzurichten sind.

### DONE
Manuels Idee: den Revolver als eigene Baugruppe mit den Plätzen bauen.
Beantwortet hat er es über eine Auswahl:

- **Schalten als Betriebsart „Revolver“:** gewählt. Dazu hat Manuel angemerkt,
  dass ein Revolver wie eine Spindel auch auf Gradzahlen positionierbar sein
  kann. Deshalb darf ein Drehgelenk jetzt allgemein mehrere Betriebsarten
  haben (Revolver + Positionieren), nicht nur Spindel + Positionieren.
- **Plätze:** einzeln als LCS, dazu eine Verteilhilfe. Die Namen sind P1 … Pn.
  Welches Werkzeug auf einem Platz sitzt, kommt laut Manuel aus CAM und nicht
  aus der Maschine.
- Manuels Frage, ob sich Reitstock, Gegenspindel und 4. Achse damit
  einrichten lassen: ja. Neuer Abschnitt 7b zeigt das als Tabelle. Dabei hat
  sich gezeigt: Ein Gelenk **ohne** Betriebsart steht für eine von Hand
  verstellte Achse, z. B. einen Reitstock ohne NC. Das ist jetzt ausdrücklich
  erlaubt und so benannt.

### TEST
- Keiner (nur Spezifikation).

### NEXT
- Betriebsart „Revolver“ und Platznummern im Maschinenobjekt, danach der
  Dialog.

## P-2026-09-25-14 maschinenobjekt

### EINGELESEN
- Spezifikation W-001, Abschnitte 4, 5 und 7.
- `camaddon/kette.py` (P-2026-09-25-13).

### DATEIEN
- `camaddon/maschine.py` (neu)
- `tests/test_maschine.py` (neu), `tests/beispielmaschinen.py` (Revolver und
  Futter als Part mit LCS)
- `translations/de.json`, `translations/en.json`
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`test_maschine.py` legt an der Beispiel-Drehmaschine eine Maschine mit Z1,
X1, S4 und C4 (zwei Betriebsarten an einem Gelenk) sowie Revolver und Futter
an. Die Prüfung meldet dafür nichts, und die Hauptspindel sitzt im Tisch,
X und Z im Kopf.

### DONE
- **Aufbau:** Eine Gruppe „Maschine“ liegt in der Assembly. Jede Betriebsart
  und jede Aufnahme ist ein eigenes Objekt darin, so stehen sie lesbar im
  Baum. Rückgängig geht von selbst, und ein gelöschtes Gelenk hinterlässt nur
  einen leeren Verweis. Die Assembly löst weiterhin und zählt die Gruppe
  nicht als Bauteil (geprüft).
- **Betriebsart:** Gelenk, Art (Linear, Positionieren, Spindel), NC-Name,
  Kennwerte in den Einheiten aus Spezifikation Abschnitt 4. **0 bedeutet
  unbekannt**, denn keiner dieser Werte kann an einer echten Maschine 0 sein.
  Der Eigenschaften-Editor zeigt nur die Werte, die zur Art gehören, auch
  nach dem Laden.
- **Aufnahme:** LCS, Art (Werkzeug/Werkstück), optional die Spindel, die das
  Werkzeug antreibt.
- **Tisch/Kopf:** Ein Gelenk auf dem Weg einer Werkstückaufnahme zum Bett
  sitzt im Tisch, eines auf dem Weg einer Werkzeugaufnahme im Kopf. Liegt es
  auf beiden Wegen, ist es mehrdeutig und wird gemeldet.
- **Prüfung** `pruefe(maschine)` meldet in ganzen Sätzen:
  - NC-Name fehlt oder ist doppelt (Groß/Klein egal)
  - Gelenk gelöscht oder keine Achse
  - Art passt nicht zum Gelenk
  - Art doppelt
  - Pflichtwert fehlt
  - LCS fehlt oder liegt außerhalb
  - Antrieb ist keine Spindel
  - Werkzeug- oder Werkstückaufnahme fehlt (Hinweis)
- Anzeigetexte für Art und Kennwert kommen aus `art_text()`/`wert_text()`
  mit festen Schlüsseln. Mein erster Entwurf setzte die Schlüssel zusammen
  (`"art." + …`), das verbietet Abschnitt 8. Die Sprachprüfung hat außerdem
  einen Eigenschaftstext gefunden, der unübersetzt übergeben wurde. Beides
  ist behoben.
- Die Werte der Eigenschaft „Art“ sind gespeicherte ASCII-Wörter
  (`Positionieren`). Im Eigenschaften-Editor erscheinen sie so, auch auf
  Englisch. Der Dialog zeigt die Übersetzung. Das ist bewusst so, weil
  gespeicherte Werte nicht von der Sprache abhängen dürfen.

### TEST
- Von der KI ohne Fenster ausgeführt: `tests_ausfuehren.sh` ergibt alle
  vier Prüfungen `ok`. `test_maschine.py` deckt ab:
  - Anlegen, auch doppelt
  - Assembly löst weiter
  - leere Maschine
  - vollständige Drehmaschine ohne Meldung
  - Tisch/Kopf-Zuordnung
  - Sichtbarkeit der Kennwerte
  - drei Fehlerfälle, alle Platzhalter gefüllt
  - gelöschtes Gelenk und Rückgängig
  - Speichern und Laden
- Gegenprobe: Erlaubt man Spindel an Schiebegelenken, fehlt
  `maschine.art_passt_nicht`, und die Prüfung schlägt fehl.

### NEXT
- Dialog „Maschine bearbeiten“ (Stufe 1, Oberfläche).

## P-2026-09-25-13 kette-aus-baugruppe-lesen

### EINGELESEN
- Spezifikation W-001, Abschnitte 3, 6 und 7.
- `Mod/Assembly/UtilsAssembly.py` (`getMovablePartsWithin`, `getJointGroup`,
  `getJcsGlobalPlc`, `findPlacement`) und `JointObject.py` (`Joint`,
  `GroundedJoint`, `RigidGroupJoint`, `setJointConnectors`).

### DATEIEN
- `camaddon/kette.py` (neu)
- `tests/beispielmaschinen.py`, `tests/test_kette.py` (neu)
- `tests/test_sprache.py` (findet jetzt auch `meldung("…")`)
- `translations/de.json`, `translations/en.json` (Meldungen)
- `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 6),
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`test_kette.py` liest aus den Beispielmaschinen „Drehmaschine“ und
„Fünfachser“ die richtigen Glieder, Achsen, Richtungen und Grenzen und meldet
lose Körper, nicht unterstützte Gelenke und eine doppelt gelagerte Wiege.

### DONE
- `lies_kette(assembly)` liefert eine `Kette`:
  - **Glieder:** Alle Körper, die über Fixed- oder RigidGroup-Gelenke starr
    verbunden sind, werden zu einem Glied zusammengefasst (Union-Find).
    Alle fixierten Körper zusammen bilden das feste Glied, also das Bett.
  - **Achsen:** Slider- und Revolute-Gelenke, als Baum vom Bett aus
    aufgebaut. Jede Achse kennt ihr Eltern- und Kind-Glied, ihre Richtung
    (Z des Gelenk-Koordinatensystems) und ihre Grenzen aus der
    Min/Max-Begrenzung.
  - `glied_von(objekt)` findet das Glied auch für ein LCS in einem Körper.
    `pfad_zum_festen_glied()` ist die Grundlage für die Tisch/Kopf-Zuordnung
    im nächsten Patch.
- **Meldungen** als ganze Sätze auf Deutsch und Englisch:
  - Gelenk ohne zwei Bauteile
  - nicht unterstützte Gelenkart
  - kein fixiertes Teil
  - loser Körper
  - Gelenk innerhalb eines Glieds
  - geschlossene Schleife
  - Glied, das nicht am Bett hängt
  - doppelte Lagerung
- **Befund, doppelte Lagerung:** Eine Wiege mit je einem Drehgelenk in
  beiden Lagerböcken kann der Löser der Assembly nicht lösen
  („Solve failed“), die Teile springen. Ohne das zweite Gelenk stimmen alle
  Richtungen. Mein erster Entwurf hat das zweite Gelenk geometrisch als
  „zweites Lager derselben Achse“ erkannt. Das funktioniert nicht, weil die
  Lage nach dem Scheitern unbrauchbar ist. Jetzt wird strukturell erkannt:
  Ein zweites Gelenk zwischen denselben Gliedern ergibt eine Warnung, die
  sagt, welches Gelenk zu unterdrücken ist. Die Spezifikation (Abschnitt 6)
  schreibt dazu: eine Achse, ein Gelenk.
- **Fallen im Testaufbau** (nicht im Addon, aber für jeden, der weitere
  Beispielmaschinen baut):
  - `Placement.Base = …` ändert nur eine Kopie.
  - Gelenke brauchen neu berechnete Körper.
  - `setJointConnectors` braucht je Seite zwei Namen, das Element und den
    Bezugspunkt. Die Fläche zweimal genannt bedeutet Flächenmitte.
  - Alle drei stehen als Kommentar in `tests/beispielmaschinen.py`.

### TEST
- Von der KI ohne Fenster ausgeführt: `tests_ausfuehren.sh` ergibt
  `ok test_kette.py`, `ok test_sprache.py` und `ok test_umgebung.py`.
- Gegenprobe: Werden Fixed-Gelenke nicht mehr als starr gewertet, schlägt die
  Prüfung mit „Drehmaschine: 4 Glieder erwartet, 7 gefunden“ fehl.
- Die Oberfläche ist nicht betroffen, deshalb gibt es kein Szenario.

### NEXT
- Maschinenobjekt mit Betriebsarten und Aufnahmen, Tisch/Kopf-Zuordnung,
  Befehl „Maschine anlegen“.

## P-2026-09-25-12 grundgeruest-werkzeugleiste-sprachwahl

### EINGELESEN
- `Mod/AddonManager/package.xml` als Vorlage für `package.xml`.
- `Mod/Fem/fempreferencepages/dlg_settings_netgen.py`: Aufbau einer
  Einstellungsseite in Python.
- `Mod/BIM/nativeifc/ifc_status.py`: Beispiel für einen WorkbenchManipulator.

### DATEIEN
- `package.xml`, `InitGui.py`, `resources/icons/camaddon.svg` (neu)
- `camaddon/gui_start.py`, `camaddon/gui_sprachwahl.py` (neu)
- `translations/de.json`, `translations/en.json` (erste Texte)
- `scripts/oberflaeche_testen.sh`, `tests/gui/_lauf/*`,
  `tests/gui/szenario_erster_start.py` (neu), `.gitignore`
- `README.md` (Installieren), `CLAUDE.md`, `CHATSTART.md`,
  `docs/arbeitsregeln.md` (Abschnitt 5), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Nach der Installation fragt FreeCAD beim ersten Start auf Englisch nach der
Sprache, der Dialog beschriftet sich beim Wählen von Deutsch sofort um, und
danach zeigen Assembly und CAM die Werkzeugleiste „CAM-Addon“ mit dem Knopf
„Über das CAM-Addon“.

### DONE
- **T-001 Grundgerüst:**
  - Das Addon ist in `package.xml` als `workbench` deklariert, damit
    FreeCAD `InitGui.py` lädt. So macht es auch der Addon-Manager von FreeCAD.
    Einen eigenen Arbeitsbereich hat das Addon nicht.
  - Die Werkzeugleiste hängt an **Assembly** und **CAM**, denn dort wird
    die Maschine gebaut und benutzt.
- **Gefundene Falle:** Mein erster Weg war ein `WorkbenchManipulator`
  (`modifyToolBars`). Der hängt nur an vorhandene Leisten an und legt keine
  neue an. Das Szenario hat das aufgedeckt. Jetzt geht es über
  `appendToolbar` des Arbeitsbereichs, sobald er aktiv wird, einmal je
  Arbeitsbereich, und danach `reloadActive()`.
- **T-003, Rest:**
  - Beim ersten Start erscheint die Sprachwahl mit Englisch vorbelegt. Beim
    Blättern durch die Liste beschriftet sie sich sofort in der markierten
    Sprache um, damit auch jemand ohne Englisch sieht, was er wählt.
  - Schließen ohne Wahl zählt als Wahl der Vorauswahl, damit die Frage nicht
    bei jedem Start wiederkommt.
  - Die Einstellungsseite heißt „CAM-Addon → Allgemein“ und bietet die
    Sprache an. Sie sagt dazu, dass die neue Sprache erst nach einem Neustart
    vollständig gilt, weil Befehlstexte beim Laden gelesen werden.
- **Oberflächentests:** `scripts/oberflaeche_testen.sh` startet FreeCAD mit
  Oberfläche unter Xvfb, mit leerem Benutzerprofil (`FREECAD_USER_HOME`) und
  dem Addon als Verknüpfung im Mod-Ordner. Es spielt ein Szenario durch und
  legt Screenshots und `ergebnis.txt` ab. Das Szenario wartet mit `yield`, so
  blockieren modale Dialoge es nicht. Weil FreeCAD `InitGui.py` in einem
  eigenen Namensraum ausführt, in dem sich Funktionen nicht gegenseitig sehen,
  steht die Logik immer im Paket und nie in `InitGui.py`.
- `package.xml` nennt „Manuel Hofer“ als Verantwortlichen, **ohne
  E-Mail-Adresse**. Die trägt Manuel selbst ein, falls er eine angeben will.
- **Neue Regel** in Abschnitt 5: Jede Oberfläche bekommt ein Szenario, und
  die Screenshots gehen an Manuel. `CLAUDE.md` sagt jetzt, dass die KI die
  Oberfläche als Screenshot sieht, die Verständlichkeit aber Manuel prüft.
- Arbeitsname „CAM-Addon“ / „CAM Addon“. Ein richtiger Name ist nicht
  festgelegt.

### TEST
- Von der KI ausgeführt: `tests_ausfuehren.sh` ergibt `ok test_sprache.py`
  und `ok test_umgebung.py`. `oberflaeche_testen.sh` ergibt
  `ok szenario_erster_start`, mit fünf Screenshots (Sprachwahl englisch und
  deutsch, Leiste in Assembly und CAM, Einstellungsseite), alle angesehen.
- **Noch nicht getestet:** Installation und Bedienung in Manuels eigenem
  FreeCAD.

### NEXT
- W-001, Stufe 1: Maschinenobjekt und das Auslesen von Gelenken und Gliedern.

## P-2026-09-25-11 sprachsystem-kern

### EINGELESEN
- `docs/arbeitsregeln.md` Abschnitt 8 (Sprache).

### DATEIEN
- `camaddon/__init__.py`, `camaddon/sprache.py` (neu)
- `translations/de.json`, `translations/en.json`, `translations/README.md` (neu)
- `tests/test_sprache.py` (neu), `.gitignore` (neu)
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
`scripts/tests_ausfuehren.sh` meldet `ok test_sprache.py`, und eine
absichtlich eingefügte Leiche in `de.json` lässt die Prüfung scheitern.

### DONE
- `tr(schluessel, **werte)` liefert den Text in der gewählten Sprache. Fehlt
  er dort, kommt Englisch, dann Deutsch und zuletzt der nackte Schlüssel mit
  einer Warnung im Report-Fenster. Die Sprache liegt im Parameter-System unter
  `Mod/CamAddon/Sprache`. Leer heißt „noch nie gewählt“, das braucht die
  Sprachwahl beim ersten Start.
- Eine Sprachdatei ist flach aufgebaut, Schlüssel → Text. `_sprache` enthält
  den Namen der Sprache in der Sprache selbst, so erscheint sie in der
  Auswahl.
- Eine kaputte oder falsch übersetzte Datei (JSON-Fehler, falscher
  Platzhalter) legt das Addon nicht lahm. Es gibt eine Meldung und einen
  Rückfall.
- `translations/README.md` ist die Anleitung für Übersetzer, auf Deutsch
  und Englisch.
- Die Prüfung `test_sprache.py` stellt sicher: de und en haben dieselben
  Schlüssel, andere Sprachen haben keine fremden, die Platzhalter sind gleich,
  jeder `tr("…")` im Code steht in `de.json`, und es gibt keine unbenutzten
  Schlüssel. Deshalb stehen Schlüssel im Code immer als fester Text und werden
  nie zusammengesetzt.
- Außerdem geprüft: Sich Assembly-Gelenke ohne Fenster anlegen und lösen,
  und die FreeCAD-Oberfläche läuft unter Xvfb. Ich kann also Screenshots
  von Dialogen machen. Beides wird in den nächsten Patches genutzt.

### TEST
- Von der KI ohne Fenster ausgeführt: `tests_ausfuehren.sh` ergibt
  `ok test_sprache.py` und `ok test_umgebung.py`.
- Gegenprobe: Ein Schlüssel `test.leiche` nur in `de.json` ergibt `FEHLER` mit
  „nur in de.json“ und „nirgends benutzt“. Danach habe ich ihn wieder entfernt.

### NEXT
- Grundgerüst (T-001) mit Sprachwahl beim ersten Start und Einstellungsseite.

## P-2026-09-25-10 spezifikation-bedienung

### EINGELESEN
- `docs/spezifikation_maschine_aus_baugruppe.md`, `docs/arbeitsregeln.md`
  Abschnitt 8 (aus P-2026-09-25-09).

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (Abschnitt 11 neu,
  „Entschieden“ ergänzt)
- `docs/STATUS_SNAPSHOT.md` (nächster Schritt), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Spezifikation hat keine offenen Fragen mehr, und Abschnitt 11 beschreibt,
wie der Dialog zeigt, welches Teil der Maschine gemeint ist.

### DONE
- Die offene Frage nach „weiteren Betriebsarten“ ist gestrichen. Ich hatte sie
  unverständlich gestellt, und für Manuel gibt es dort nichts zu
  entscheiden. Sie steht jetzt unter „Entschieden“: vorerst drei, erweiterbar.
- Neuer Abschnitt 11 „Bedienung“ wendet die neue Regel auf diesen Dialog an:
  Beim Überfahren eines Gelenks wird das Teil in der 3D-Ansicht hervorgehoben
  und kurz bewegt. Nicht erlaubte Betriebsarten werden gar nicht erst
  angeboten. Es gibt Hilfe je Bereich und Warnungen in ganzen Sätzen.
- Im Snapshot stand noch „offene Fragen (Abschnitt 9)“. Das war nach dem
  Umnummerieren in P-2026-09-25-08 falsch und ist jetzt korrigiert.

### TEST
- `grep` nach „Offene Fragen“ und nach Abschnittsverweisen in Spezifikation
  und Snapshot.

### NEXT
- Freigabe der Spezifikation durch Manuel.

## P-2026-09-25-09 regel-bedienbarkeit-und-sprache

### EINGELESEN
- `CHATSTART.md` (Festlegungen), `docs/arbeitsregeln.md` Abschnitt 7.

### DATEIEN
- `CHATSTART.md` (vierte Festlegung), `docs/arbeitsregeln.md` (neuer
  Abschnitt 8, Stilregel „Deutsch“ angepasst, folgende Abschnitte umnummeriert)
- `docs/STATUS_SNAPSHOT.md` (T-003), `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer `CHATSTART.md` liest, erfährt als erste Festlegung, dass Bedienbarkeit
vor allem geht. Abschnitt 8 der Arbeitsregeln sagt, wie eine neue Sprache
hinzukommt.

### DONE
Manuel: „Das Allerwichtigste ist Bedienbarkeit und Benutzerfreundlichkeit. Es
dürfen bei dem, was auf dem Bildschirm zu sehen ist, keine Fragen aufkommen.“
Dazu selbsterklärend, kleine Animationen, ausführlicher Text hinter dem
Hilfe-Feld, Deutsch und Englisch.

Zur Sprache hatte ich gefragt, ob die Oberflächentexte im Code auf Englisch
(wie bei FreeCAD) oder auf Deutsch stehen sollen. Manuels Antwort ging darüber
hinaus:
- **Deutsch ist die Hauptsprache** für alles, was wir machen.
- **Bei der Erstinstallation gilt Englisch.** Die Sprache wird direkt nach der
  Installation ausgewählt.
- **Weitere Sprachen** soll jemand anderes übersetzen können, über eine
  einfache Datei (JSON oder was üblich ist).

Umsetzung als Regel:
- Die Texte stehen nicht im Code, sondern als Schlüssel in `translations/<sprache>.json`,
  mit `de.json` als führender Datei.
- Eine neue Sprache heißt: `en.json` kopieren und übersetzen.
- Fehlt ein Text in einer Sprache, wird er auf Englisch angezeigt.
- Das Addon fragt beim ersten Start einmal nach der Sprache. Die
  Installation selbst läuft über den Addon-Manager von FreeCAD und bietet
  keinen eigenen Schritt, deshalb ist der erste Start der früheste Zeitpunkt.

Bewusst **nicht** das FreeCAD-übliche Qt-Format (`.ts`/`.qm`): Es braucht
Qt Linguist und einen Übersetzungsschritt, und Manuel wollte ausdrücklich eine
einfache Datei. Nachteil: Die Übersetzungsplattform von FreeCAD (Crowdin)
greift nicht. Wird das später gewünscht, lässt sich JSON in `.ts` umwandeln.

Animationen enthalten keinen Text, damit keine Animation je Sprache
gebraucht wird.

### TEST
- Abschnittsnummern und Verweise nach dem Umnummerieren gegengeprüft.

### NEXT
- Offene Frage in der Spezifikation streichen; Freigabe durch Manuel.

## P-2026-09-25-08 spezifikation-maschinenobjekt-glieder

### EINGELESEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (Entwurf aus P-2026-09-25-07).

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md`
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die Spezifikation liest, erfährt, dass die Maschinendaten in einem eigenen
Maschinenobjekt liegen und wie eine Schwenkbrücke aus mehreren Körpern als ein
Glied mitschwenkt.

### DONE
Drei Vorgaben von Manuel:

- **Allgemein, nicht nur die CLX 550.** Die Spezifikation sagt jetzt vorn,
  dass sie für beliebige Maschinen gilt. Die CLX erscheint nur noch als ein
  Beispiel („Drehmaschine“), daneben steht eine Fräse mit Schwenkbrücke.
- **Eigenes Objekt** statt Eigenschaften an den Gelenken (meine Empfehlung war
  A, Manuel hat B gewählt). Neuer Abschnitt 5: Das Objekt verweist auf Gelenke
  und LCS. Gebrochene Verweise gehen nicht verloren, sondern werden gemeldet
  und können neu zugeordnet werden. Das war das Risiko, das ich bei B genannt
  hatte.
- **Schwenkbrücke:** Schenkel und Boden der Wiege sind eigene Körper und
  müssen mitschwenken. Neuer Abschnitt 6 „Glieder“: Das Addon fasst alle über
  Fixed-Gelenke (oder eine Unterbaugruppe) starr verbundenen Körper zu einem
  Glied zusammen. Das Mitschwenken selbst erledigt die Assembly. Für Stufe 4
  ist vorgemerkt, dass Körper eines Glieds und direkt benachbarte Glieder
  nicht gegeneinander geprüft werden.

Die offene Frage nach weiteren Betriebsarten bleibt stehen, ist aber
entschärft: Die Liste lässt sich erweitern.

### TEST
- Abschnittsnummern und Querverweise nach dem Umnummerieren gegengeprüft.

### NEXT
- Freigabe der Spezifikation durch Manuel; dann Stufe 1 plus T-001.

## P-2026-09-25-07 spezifikation-maschine-aus-baugruppe

### EINGELESEN
- `Mod/CAM/Machine/models/machine.py` (Wochen-Build 26.3.0 dev): `LinearAxis`,
  `RotaryAxis`, `ToolheadType`, `MachineFactory` (Ablage als `.fcm`,
  `register_addon_machine_dir`).
- `Mod/Assembly/JointObject.py`: Gelenkarten und Begrenzungen.

### DATEIEN
- `docs/spezifikation_maschine_aus_baugruppe.md` (neu)
- `CHATSTART.md` (Lesekarte), `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer die Spezifikation liest, findet dort für jede Betriebsart (Linear,
Positionieren, Spindel) die Werte mit Einheit und eine Anleitung, wie man die
Beschleunigung ermittelt.

### DONE
Entwurf nach Manuels Vorgaben aus dem Gespräch:

- **Namen immer von Hand.** Mein erster Vorschlag, Namen aus der Baugruppe
  abzuleiten, war falsch. Manuels Gegenbeispiel: An der CLX 550 heißt die
  Hauptspindel S4, wenn sie dreht, und C4, wenn sie positioniert.
- Daraus entstand der Begriff **Betriebsart**: Ein Gelenk hat eine oder
  mehrere Betriebsarten, jede mit eigenem Namen und eigenen Werten.
- **Beschleunigung und Ruck** sind aufgenommen, dazu eine Anleitung, wie man
  sie ermittelt (Maschinendaten Siemens/Fanuc/LinuxCNC, Datenblatt, Messen
  mit a ≈ 4·s/t²).
- Verfahrgrenzen werden **nicht doppelt** erfasst, sie kommen aus der
  Min/Max-Begrenzung der Assembly-Gelenke.
- Der Export geht in die vorhandene CAM-Maschinendefinition (`.fcm`) über
  den offiziellen Addon-Weg. Werte, die FreeCAD dort nicht kennt
  (Beschleunigung, Ruck, Vorschub, Mehrfach-Betriebsarten), bleiben im
  Dokument.
- Aus zwei Stufen wurden vier: beschreiben, exportieren, von Hand
  verfahren, Kollision. Stufe 4 bekommt eine eigene Spezifikation.

Zwei offene Fragen stehen in Abschnitt 9: der Speicherort (Empfehlung: als
Eigenschaften direkt an Gelenken und LCS) und ob drei Betriebsarten reichen.

**Nicht geprüft:** die Maschinendaten-Nummern für Siemens und Fanuc stammen
aus meinem Wissen, nicht aus einem Handbuch. Manuel kann sie an der CLX 550
gegenprüfen.

### TEST
- Links in `CHATSTART.md` und im Snapshot auf die neue Datei geprüft.

### NEXT
- Manuel beantwortet die offenen Fragen; dann Stufe 1 plus T-001.

## P-2026-09-25-06 wunsch-maschine-aus-baugruppe

### EINGELESEN
- `docs/STATUS_SNAPSHOT.md`, Wunschliste.
- FreeCAD-Quelltext (Wochen-Build 26.3.0 dev), um zu prüfen, ob es das schon
  gibt: `Mod/CAM/Machine/models/machine.py` und `Mod/Assembly/JointObject.py`.

### DATEIEN
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Die Wunschliste im Snapshot enthält W-001 „Maschine aus Baugruppe“.

### DONE
Manuels Vorstellung: Die Maschine wird grob in 3D nachgebaut und in einer
Assembly zusammengesetzt. In die Bauteile gelegte Achsen bestimmen Richtung,
Art (linear/drehend) und Namen, auch für mehrere Werkzeugachsen. Das soll das
erste Addon werden.

Befund aus dem FreeCAD-Check, damit die Spezifikation nicht bei null anfängt:

- **Assembly** hat die passenden Gelenke `Slider` und `Revolute` mit
  Min-/Max-Begrenzung und eine Simulation, die Gelenke antreibt.
- **CAM** hat eine neue Maschinendefinition (`Mod/CAM/Machine/`) mit
  kinematischer Kette (`AxisRole` Tisch/Kopf, `parent`, `joint_origin`),
  Grenzen, `max_velocity` (linear in mm/min, Standard 10000; rotativ in °/min,
  Standard 36000 = 100 U/min), `WrapStrategy` für endlose Rundachsen und
  `tcp_supported`. **Keine Geometrie**, keine Beschleunigung.
- Kollisionsprüfung gibt es nur für Eilgang-Verbindungen gegen Körper
  (`Path/Base/Generator/linking.py`), nicht für Maschine oder Halter.

Daraus ergibt sich die Richtung: Das Addon liest die Assembly aus und füllt
die vorhandene CAM-Maschinendefinition. Es baut kein eigenes Format.

### TEST
- Keiner nötig (nur Snapshot).

### NEXT
- Spezifikation W-001: Achsparameter je Achsart klären.

## P-2026-09-25-05 zielversion-wochen-build

### EINGELESEN
- Alle Stellen mit „neueste“ in der Doku (`grep -rn "neueste"`).

### DATEIEN
- `CHATSTART.md` (Festlegung 1), `README.md`
- `docs/arbeitsregeln.md` (Abschnitte 0, 7 und 8)
- `docs/STATUS_SNAPSHOT.md` (T-002 entfernt), `docs/archiv/DEV_PROMPT_HISTORY.md`
  (Kopfzeile `zielsystem`)

### AKZEPTANZKRITERIUM
Wer `CHATSTART.md` liest, erfährt, dass das Addon für den aktuellen
Wochen-Build von FreeCAD gebaut wird und nicht für die letzte stabile Version.

### DONE
T-002 ist entschieden. Manuel: **Wochen-Build**. Damit gilt dieselbe Version
wie in der Testumgebung, die conda-forge ohnehin liefert.

Folge für Abschnitt 8 (Versionscheck): Ein Wochen-Build erscheint jede Woche.
Ein Versionscheck-Patch für jede Woche wäre Leerlauf. Deshalb fällt er an,
sobald Manuel seinen Build aktualisiert oder die Testumgebung einen neueren
zieht. Die Regel selbst bleibt bestehen, nur ihr Auslöser ist präzisiert.

### TEST
- `grep -rn "neueste"` findet nur noch Verlaufseinträge, die Historie sind.

### NEXT
- W-001 in die Wunschliste.

## P-2026-09-25-04 testumgebung-ohne-fenster

### EINGELESEN
- `docs/arbeitsregeln.md`, Abschnitt 5 (die neue Regel aus P-2026-09-25-02).

### DATEIEN
- `scripts/testumgebung_einrichten.sh`, `scripts/tests_ausfuehren.sh`,
  `tests/test_umgebung.py` (alle neu)
- `CHATSTART.md` (Lesekarte), `docs/arbeitsregeln.md` (Abschnitt 5)
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
In einer frischen Cloud-Sitzung laufen `scripts/testumgebung_einrichten.sh`
und danach `scripts/tests_ausfuehren.sh`. Die Ausgabe ist
`ok test_umgebung.py` mit Exit-Code 0.

### DONE
- FreeCAD kommt über **micromamba aus conda-forge**. Das ist der einzige Weg,
  den das Netzwerk der Cloud-Umgebung zulässt: GitHub-Releases (AppImage) und
  gnu.org werden vom Proxy abgewiesen, `apt` kennt kein FreeCAD. micromamba
  selbst wird als conda-forge-Paket geholt, weil `micro.mamba.pm` ebenfalls
  gesperrt ist.
- Die Installation belegt rund **3,7 GB** und dauert einige Minuten. Deshalb
  liegt sie außerhalb des Repos unter `~/.cache/freecad-cam-addon/` und kann
  über `FC_UMGEBUNG` umgelenkt werden.
- **Falle, die ich beim Entwurf gefunden habe:** FreeCADCmd liefert bei einer
  Ausnahme im Skript keinen verlässlichen Fehlercode. Deshalb endet jede
  Prüfung mit der Zeile `OK <dateiname>`, und nur diese Zeile zählt als
  bestanden.
- `tests/test_umgebung.py` prüft das Fundament aller späteren Prüfungen:
  FreeCAD startet, `Path.Main.Job` lässt sich importieren, und
  Transaktion plus Rückgängig entfernt ein angelegtes Objekt wieder (Regel
  „Strg+Z muss gehen").
- Die Skripte sind reine Entwicklerwerkzeuge für Linux-Container. Das Addon
  selbst bleibt plattformneutral.

Bewusst **nicht** gemacht: keine CI auf GitHub (bisher nicht beauftragt), kein
SessionStart-Hook, der die 3,7 GB in jeder Sitzung automatisch lädt.

**Offene Frage (T-002):** conda-forge liefert nur den Wochen-Build
26.3.0 dev (2026-09-16). Ob „neueste Version" stabil oder Wochen-Build meint,
entscheidet Manuel.

### TEST
- Von der KI ohne Fenster ausgeführt: `scripts/tests_ausfuehren.sh` ergibt
  `ok test_umgebung.py`, Exit 0.
- Gegenprobe mit einer absichtlich fehlschlagenden Prüfung: `FEHLER`,
  Ausgabe mit der Ausnahme, Exit 1. Die Prüfung ist danach wieder gelöscht.
- `testumgebung_einrichten.sh` auf der vorhandenen Umgebung ausgeführt
  (Zweig „update"). Den Zweig „create" habe ich mit demselben Befehl von Hand
  ausgeführt, aber nicht über das Skript.
- `sh -n` über beide Skripte, `py_compile` über die Prüfung.

### NEXT
- T-002 entscheiden; Wunschliste füllen.

## P-2026-09-25-03 lizenz-lgpl

### EINGELESEN
- `README.md`.

### DATEIEN
- `LICENSE` (neu), `README.md` (Abschnitt Lizenz)
- `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
GitHub zeigt beim Repo die Lizenz LGPL-2.1 an, und das README nennt sie.

### DONE
Manuel hat LGPL-2.1 wie FreeCAD gewählt (Alternativen waren „keine Lizenz“ und
MIT). Angegeben ist „or-later“, wie bei FreeCAD. Das ist auch die Voraussetzung,
falls das Addon später in den Addon-Manager soll. Der Lizenztext stammt aus
`/usr/share/common-licenses/LGPL-2.1` (Debian), weil gnu.org aus der
Cloud-Umgebung nicht erreichbar war. Der Text ist derselbe.

### TEST
- Kopf von `LICENSE` gelesen: „GNU LESSER GENERAL PUBLIC LICENSE, Version 2.1“.
- Die Anzeige auf GitHub ist erst nach dem Push prüfbar.

### NEXT
- Testumgebung.

## P-2026-09-25-02 regeln-addon-zusatz

### EINGELESEN
- `docs/arbeitsregeln.md`, Abschnitte 5 und 7.

### DATEIEN
- `docs/arbeitsregeln.md` (Abschnitt 5 und 7 ergänzt, neuer Abschnitt 8,
  bisheriger 8 wird 9)
- `docs/STATUS_SNAPSHOT.md`, `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Wer `docs/arbeitsregeln.md` liest, findet dort die vier Zusatzregeln
Rückgängig, Einstellungen, Versionscheck und automatische Tests.

### DONE
Manuel hat aus einer Auswahl alle vier vorgeschlagenen Zusatzregeln gewählt:

- **Strg+Z muss gehen:** jede Aktion eine Transaktion.
- **Einstellungen in FreeCAD:** Parameter-System statt eigener Dateien.
- **Neue FreeCAD-Version prüfen:** eigener Patch je Version; die zuletzt
  geprüfte Version steht im Snapshot.
- **Automatische Tests:** Prüfungen unter `tests/`, die ohne Fenster mit
  `FreeCADCmd` laufen. Die Testumgebung selbst ist ein eigener Patch.

### TEST
- Abschnittsnummern und Verweise gegengeprüft.

### NEXT
- Lizenz, dann Testumgebung.

## P-2026-09-25-01 projektregeln

### EINGELESEN
- Regelwerk des Projekts `zeiterfassung` (`CLAUDE.md`, `CHATSTART.md`,
  `docs/arbeitsregeln.md`, `docs/STATUS_SNAPSHOT.md`, Kopf des Verlaufs) als
  Vorlage.

### DATEIEN
- `CLAUDE.md`, `CHATSTART.md`, `README.md`
- `docs/arbeitsregeln.md`, `docs/STATUS_SNAPSHOT.md`,
  `docs/archiv/DEV_PROMPT_HISTORY.md`

### AKZEPTANZKRITERIUM
Ein neuer Chat, der `CLAUDE.md` liest, weiß danach, was das Projekt ist, nach
welchen Regeln gearbeitet wird und dass der nächste Schritt Manuels
Wunschliste ist.

### DONE
Regeln aus `zeiterfassung` übernommen und auf ein FreeCAD-Addon umgestellt:

- Die drei Festlegungen von Manuel stehen vorn in `CHATSTART.md`: **neueste
  FreeCAD-Version, Betriebssystem egal, Maschine egal**. Deshalb wird danach
  auch nicht mehr gefragt.
- Aus PHP/MariaDB/Apache wurde Python/PySide/FreeCAD-API; Prüfung per
  `python -m py_compile` statt `php -l`.
- Neu gegenüber `zeiterfassung`: Das Akzeptanzkriterium ist ein **Klickweg**,
  den Manuel nachmachen kann. Die KI sieht die Oberfläche nicht, deshalb steht
  im Verlauf, wer was getestet hat.
- Neu: **FreeCAD-Check** im Pre-Flight-Gate. Kann FreeCAD es schon, gibt es
  einen Hinweis statt Code.
- Neu: **Wunschliste** (W-IDs) im Snapshot als Eingang für „das hätte ich gern
  so und so".
- Weggelassen, weil es hier nichts gibt: Datenbank, SQL im Chat,
  Fachregel-Dateien. Die Lesekarte ist leer und wächst mit.

Bewusst **nicht** gemacht: noch kein Addon-Code (T-001 kommt mit dem ersten
Wunsch).

### TEST
- Links zwischen den Dateien per Hand gegengeprüft.

### NEXT
- Manuel füllt die Wunschliste.
