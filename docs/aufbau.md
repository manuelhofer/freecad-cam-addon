# Aufbau des Codes

Für alle, die am Addon programmieren. Was das Addon für den Benutzer tut,
steht in der [Spezifikation](spezifikation_maschine_aus_baugruppe.md), wie
gearbeitet wird, in den [Arbeitsregeln](arbeitsregeln.md).

Verweise wie „P-2026-09-25-17“ in Kommentaren führen in den
[Verlauf](archiv/DEV_PROMPT_HISTORY.md). Dort steht, wie ein Befund gefunden
und belegt wurde.

## Vom Modell zur CAM-Maschine

```
Assembly in FreeCAD                         Kette (kette.py)
  Körper, Parts mit LCS      lies_kette()     Glieder: was sich gemeinsam bewegt
  Gelenke: Fixed, Slider,  ─────────────▶     Achsen: Baum vom Bett aus
  Revolute                                    Meldungen
                                                   │
                                                   ▼
Maschinenobjekt (maschine.py)          Dialog „Maschine bearbeiten“
  Betriebsarten: NC-Name, Kennwerte ◀──  (gui_maschine.py), Prüfung mit
  Aufnahmen: LCS, Revolverplatz          maschine.pruefe()
                                                   │  „An CAM übergeben“
                                                   ▼
                                       export.py: Machine der CAM-Maschinen-
                                       definition, gespeichert als .fcm
```

1. **Die Assembly beschreibt die Bewegung – und nur sie.** Das Addon liest
   sie (`kette.py`), verändert sie aber nie. Die Kette wird bei jedem Öffnen
   des Dialogs neu gelesen und nirgends gespeichert.
2. **Was FreeCAD nicht weiß, steht im Maschinenobjekt:** NC-Namen,
   Kennwerte, Werkzeug- und Werkstückaufnahmen. Es ist eine Gruppe in der
   Assembly mit je einem Objekt pro Betriebsart und Aufnahme. Die Verweise
   auf Gelenke und LCS sind echte FreeCAD-Verweise: Umbenennen schadet nicht,
   Löschen hinterlässt einen leeren Verweis, und die Prüfung meldet ihn.
3. **Die Übergabe** baut daraus eine `Machine` der CAM-Maschinendefinition
   und speichert sie dort, wo CAM seine Maschinen sucht. Was CAM nicht kennt
   (Beschleunigung, Revolver …), bleibt im Dokument; der Bericht sagt das.

## Module

| Modul | Aufgabe |
| --- | --- |
| `__init__.py` | Grunddaten: Addon-Ordner, Version aus `package.xml`, Parameterpfad, `symbol()` |
| `sprache.py` | Texte aus `translations/*.json`: `tr()` |
| `einheiten.py` | Zahlen (Stufe B): Maßsystem mm/inch mit Umrechnung je Größe (Länge, Span, vc, Vorschub, Abtrag, Volumen), Dezimalzeichen, Eingaben mit Punkt oder Komma lesen; `text()` für Zahlen in Sätzen („Ø 8,5“); Einheiten-Platzhalter für `tr()` |
| `hilfe.py` | Hilfeseiten `help/<sprache>/<thema>.html` finden |
| `kette.py` | Assembly lesen: Glieder, Achsen, Meldungen |
| `maschine.py` | Maschinenobjekt: Objektarten, Anlegen, Revolverplätze, Prüfung, Tisch/Kopf |
| `verfahren.py` | Maschine von Hand verfahren: Stellung wie am Gelenk, Grenzen, Bauteile hinter der Achse bewegen |
| `schraege_achse.py` | Schräge Achse (Transformation der Steuerung): Winkel aus der Baugruppe messen, Programm ↔ Schlitten umrechnen, Vorschlag, Prüfung |
| `abfahren.py` | Die Maschine fährt die Bahn ab (W-001 Stufe 4b), Rechenkern: Stationen mit Zeit (Vorschub aus der Bahn, nach G93 1 ÷ F; Eilgang und Beschleunigung je Achse aus der Maschine, fehlen sie, die Vorgaben; die Sätze gehen durch `fahrzeit`, 4d), Operation, Satz, Stellungen; Stellungen zu jeder Zeit; die Punkte am Werkstück (mit Rundachsen gedreht) |
| `fahrzeit.py` | Die Fahrzeit einer Bahn mit Beschleunigung (W-001 Stufe 4d): je Satz das Trapezprofil (anfahren, fahren, bremsen; Dreieck, wenn der Weg nicht reicht), die Übergänge wie eine Steuerung mit Vorausschau (durchfahren, wo die Richtung bleibt – Bögen, Rampen –, anhalten an Ecken ab 15°, um Eilgänge und am Ende), der Eilgang je Achse vom Stand in den Stand; die festen Vorgaben 10 m/min und 1 m/s² bzw. 1 U/s² (`export.VORGABE_…`) für das Prüffenster und die Schätzung im Assistenten |
| `kinematik.py` | Achsstellungen und Werkzeugspitze, die eine Stelle dafür (W-001 4e): `Kinematik` für ein Werkzeug auf einer Maschine – rückwärts `stellungen()` (Punkt im Programm → Achsen), vorwärts `programm()` (Achsen → Spitze im Programm, etwa an einer Grenze) und `am_werkstueck()` (am gedrehten Teil); ohne TCPM, gerechnet mit der Kette aus `reichweite.Pruefung` |
| `pruefstand.py` | Der Prüfstand für Werkzeugwege (W-006, Grundsatz 0): `messen()` fährt eine Bahn (oder eine Folge von Bahnen) im Quader Satz für Satz ab und gibt die Kennzahlen – Zeit (`bahn.zeit`), Vorschub- und Eilgangweg, Luft (Vorschub ohne Abtrag), Volumen, Untergrenze (Volumen ÷ ae · ap · vf) und Wirkungsgrad, Rest auf den Flächen (fern der Wände), Einschnitt ins Teil (Zellen neben einer Kante zählen nicht), Abtrag im Eilgang, Eintauchen und Rampen im Material, Halte (wie `fahrzeit`) –, `urteile()` die Sätze, mit denen sie durchfällt; `tests/test_pruefstand.py` misst damit alle 2,5D-Strategien an den Maßstabsteilen gegen `tests/bestmarken.json` |
| `restmaterial.py` | Rohteil und Fertigteil (W-003 V3g, V5e): die Stange als Radien über (a, φ), ein radialer Fräser trägt mit seiner Form ab (`fraeserform`; `Stange.fahre`, `fahre_stuecke` für viele Stücke auf einmal), `Abtrag` aus der Abfahrt eines Jobs mit „Rundum schruppen“ und „Rundum schlichten“ bis zu einer Station, `vergleiche()` gegen das fertige Teil und das Aufmaß der letzten Bearbeitung in Farben; `darstellung()`/`farben()` für das Bild in gui_abfahren; das Rohteil im Quader (W-006 S3d): `Quader` als Höhen über (x, y), jedes Werkzeug senkrecht von oben trägt mit seiner Form ab, `QuaderAbtrag` aus der Abfahrt eines Jobs mit Kasten als Rohteil (`fuer_quader`, auch FreeCADs eigene Operationen), `vergleiche_quader()` gegen die Oberseite des Teils (`teilhoehen_kanten`: an Kanten darf es bis auf die tiefste Fläche daneben gehen), die Farben und die gewählten Flächen wie rundum; ein Gewindebohrer trägt mit seinem Kernradius ab (`_fraeser`: (D − P)/2 – er schneidet nur das Gewinde); „Entgraten“ darf, wo es abträgt, so tief ins Teil wie seine Spitze (`QuaderAbtrag.fasen`, wie bei „Rundum entgraten“), „Zentrieren“ so tief wie seine Fase; Bohrer, NC-Anbohrer und Kegelsenker tragen mit ihrem Kegel ab (`_kegel`) |
| `reichweite.py` | Reicht der Verfahrweg? (W-001 Stufe 4a): Stellungen aller Achsen für die Bahn eines CAM-Jobs – Drehachsen aus der Bahn, Linearachsen als Gleichungssystem wie an einer Steuerung ohne TCPM (mit den Rundachsen auf 0) –, gebrauchter Bereich, Überschreitungen und Hinweise in Sätzen; Nullpunkt des Jobs; `kommt_aus()`: ob ein Werkzeug mit seinem Halter aus einer Richtung kommt (für den 4-Achs-Assistenten) |
| `kollision.py` | Stößt beim Abfahren etwas an? (W-001 Stufe 4c): Werkzeug (Schneide – ein Drehkörper aus der Stirn des Fräsers, `drehkoerper` –, Hals, Schaft, Halter), Teil und Bauteile der Maschine als Körper an ihrer Lage zur Zeit t; Werkzeugseite gegen Werkstückseite und Rest, Werkstückseite gegen Rest, Schneide gegen Teil nur im Eilgang; Schritte je Paar nach Abstand und Weg gegeneinander (Drehachse: Abstand des Körpers von ihr); `distToShape` nur, wo es nötig ist, sonst Schranken (Hüllquader, zuletzt gerechnet minus Weg); Berührung und Warnabstand als Sätze |
| `beispielmaschine.py` | Beispielmaschinen zum Ausprobieren: Baukasten für Assemblies und fünf Bauarten (Drehmaschine mit Y-Achse und Revolver, 3-Achs-, drei 5-Achs-Fräsen) – auch für die Maschinen der Prüfungen; die Drehmaschine mit eintragbaren Maßen (`DrehmaschinenMasse`), die 3-Achs-Fräse (`FraesenMasse`) mit zwei Spanneisen auf dem Tisch (Eisen, Schraube, Mutter – je ein Bauteil, für die Kollisionsprüfung) |
| `export.py` | Übergabe an CAM mit Bericht |
| `aktualisierung.py` | Update-Suche per Git, ohne Git per HTTPS (package.xml) und Update mit `installieren.py` |
| `werkstoffe.py` | Werkstoffliste (W-002): mitgelieferte aus `daten/werkstoffe.json`, Anzeige, Suche |
| `werkzeuge.py` | Werkzeugbibliothek (W-002): Werkzeuge, Einsätze und Schnittwerte je Werkstoff, eigene Werkstoffe, Speichern als JSON; Maße eingetragen oder geschätzt (`mass`, `reichweite`) – für Bild und CAM gleich; `standardwerkzeug()`: Manuels Standardfräser Ø 12 (ae 1,5 / ap 25 / fz 0,1 / vc 85, Rampe 3°) – mit ihm wird jede Strategie, Prüfung und jedes Szenario mit Werkzeugwegen gerechnet (Arbeitsregeln, Abschnitt 5) |
| `halter.py` | Werkzeughalter (W-002 Stufe D): Kontur aus Abschnitten (Länge, Ø oben, Ø unten) ab der Spindelnase, Länge, Radius, Spanntiefe, Vorlagen; die Halter stehen in der Bibliothek, das Werkzeug nennt seinen (`werkzeuge.laenge_mit_halter`). Stufe E: Richtung gerade oder gewinkelt (Winkel, Drehung, Versatz, Kopf-Ø) – `lage()` stellt das Werkzeug in die Aufnahme, `form()` ist der Körper mit Kopf, `seitlich()` sagt, wie weit er über die Werkzeugachse reicht (Rundum: vor dem Futter) |
| `werkzeugform.py` | Umriss jeder der 26 Werkzeugarten aus ihren Maßen (Vielecke in mm) – fürs Bild; die zusammengesetzten Maße (Kegel, Konus, Radienprofil) auch für CAM |
| `schnittdaten.py` | Rechnen mit Schnittwerten: n, vf, Zeitspanvolumen, Eingriffswinkel, Spandicke; Kennzahlen und Urteil für den Strategievergleich |
| `uebergabe_werkzeuge.py` | Werkzeuge an CAM übergeben: ToolBits und Bibliothek „CAM-Addon“ über `cam_assets`, jede Art mit ihrer Form und deren Parametern (Näherungen im Bericht), Schnittwerte als Presets |
| `werkzeuge_aus_cam.py` | Werkzeuge aus einer FreeCAD-Werkzeugbibliothek übernehmen: jede Form → Art, Maße, Nummern ohne Verschieben; `vom_controller()` liest das Werkzeug eines Controllers aus seinem ToolBit |
| `schruppwerte.py` | Schruppwerte planen: fz je ae mit Spandickenausgleich, Grenzen von Werkzeug und Maschine (auch aus W-001), Vorschlag mit größtem Q |
| `job_schnittwerte.py` | Schnittwerte in die Werkzeug-Controller eines Jobs: Werkstoff vom Rohteil, Werkzeug zum TC, Einsatz vorschlagen, dazu Schrittweite und Zustelltiefe der passenden Operationen; setzen in einer Transaktion |
| `vierachs_rohteil.py` | 4-Achs-Bearbeitung, Teil in die Stange (W-003 V1): Stirnfläche vermessen (Normale, runde Kante, kleinster Kreis um das Teil), Lage für A/B/C, Vorschlag für den Stangen-Ø, Job mit Modell-Klon an der Stelle und Zylinder-Rohteil; `einstellung()` rechnet all das aus einem Job zurück (zum Ändern, V3h); hinter dem Teil bis zum Futter die Lücke `Stange.luecke` – Abstechbreite oder mehr, wenn der Fräser Platz braucht (V3f), `ausspannlaenge()` |
| `vierachs_achsen.py` | 4-Achs-Bearbeitung, Stangenachse (W-003 V2a): von der Maschine (Rundachsen im Tisch, Betriebsart „Positionieren“) oder zugewiesen (A/B/C), mit Drehsinn und der Richtung, aus der das Werkzeug radial kommt; `maschinen()` – die offenen Maschinen zur Wahl im Assistenten mit Rundachsen, Linearachsen und Werkzeugplätzen (V3f) |
| `vierachs_huelle.py` | 4-Achs-Bearbeitung, Hüllfläche (W-003 V3a, V5a): wie nah die Spitze eines radialen Fräsers der Stangenachse kommt, ohne das Teil zu verletzen – je Stelle a und Winkel φ, genau gegen das vernetzte Teil (Ecken, Kanten und Dreiecke), mit numpy; der Schaftfräser als Scheibe, jeder andere mit seinem Profil (`fraeserform`), je Winkel auf eigenem Raster längs (`je_winkel`, fürs Schlichten); sicheres Raster für die Bahn |
| `fraeserform.py` | Die Form eines Fräsers als Drehprofil (W-003 V5a): Scheibe, Eckrundung, Kegel, Hohlkehle – aus der Werkzeugverwaltung mit denselben Maßen wie das Bild (`werkzeugform`); Höhe über der Spitze je Abstand, Berührstelle an einer Ebene, Aufmaß (rundum größer), Kammhöhe |
| `vierachs_flaechen.py` | 4-Achs-Bearbeitung, Flächen wählen (W-003 V4): das Teil Fläche für Fläche vernetzt; je Stelle a und Winkel φ, welche Fläche ein Strahl von außen zuerst trifft (`sicht`, `sicht_fuer` mit Zwischenspeicher); welche nach außen schauen (`mantelflaechen`), wie weit sie erreichbar sind (`erreichbar`), wo die Mitte eines Fräsers stehen muss, damit er die gewählten ganz bearbeitet (`bereich`, `bereich_fuer`); die Art einer Fläche in Worten für die Liste im Assistenten |
| `vierachs_bahn.py` | 4-Achs-Bearbeitung, Schruppbahn rundum (W-003 V3b): Lagen bis zur Hüllfläche plus Aufmaß, je Lage eine Spirale von vorne bis um den Überlauf hinter das Teil (dort auf der Tiefe der letzten Kontur), nie näher ans Futter als der Abstand zum Futter (vom Rand des Fräsers oder seines Halters, was weiter reicht), vor jeder Wand ein Ringgang (eine Umdrehung bei festem a), Rückzug; Schlichtbahn rundum (V5b): eine Spirale auf der Hüllfläche des Schlichtfräsers, genau an ihren Stellen gerechnet, Sehnenfehler, zusammengefasst mit Toleranz, Schutz gegen zu tiefe Schnitte aus dem Rest nach dem Schruppen; mit gewählten Flächen (V4) beide nur im Bereich, in Zeilen hin und her (`_fahrten`: am Ende jeder Zeile in der Tiefe zur nächsten, abheben nur zwischen getrennten Stücken), hinein im Eilgang bis knapp über den Rest, dann über eine Rampe mit dem Eintauchwinkel (hin und her, dann zurück auf der Zeile) oder senkrecht mit dem Eintauchvorschub; Path-Befehle mit X/Y/Z im Rahmen der Maschine, der Rundachse (−drehsinn · φ) und F nach G93 |
| `vierachs_operation.py` | 4-Achs-Bearbeitung, CAM-Operation „Rundum schruppen“ (W-003 V3c): Proxy `RundumSchruppen` (erbt FreeCADs `ObjectOp`, Controller und Kühlmittel, keine Höhen in Z), Eigenschaften in der Gruppe „4-Achs“, rechnet die Bahn aus Modell, Stange und Spannlänge des Jobs; `lege_an()` ohne eigene Transaktion und ohne Rückfrage, `aendere()` für „Übernehmen“ beim Ändern (V3h) |
| `vierachs_schlichten.py` | 4-Achs-Bearbeitung, CAM-Operation „Rundum schlichten“ (W-003 V5c): Proxy `RundumSchlichten` wie „Rundum schruppen“; die Form des Fräsers aus dem ToolBit des Controllers, der Rest nach den „Rundum schruppen“ des Jobs (`restmaterial`), die Spirale aus `vierachs_bahn.schlichten`; Kammhöhe, Umdrehungen und Vorstufen als Eigenschaften zum Lesen; `lege_an()`, `aendere()`, `bahn_fuer()` auch für die Vorschau im Assistenten |
| `vierachs_entgratbahn.py` | 4-Achs-Bearbeitung, Bahn „Rundum entgraten“ (W-003 V4d): die Außenkanten der gewählten Flächen aus dem Körper (`kanten`), je Punkt der Kante die Rundachse darauf, die Spitze bis zur Berührung (Hüllfläche mit der Fräserform) und um die Fasenbreite tiefer, Stücke verkettet, Ringe als eine Umdrehung |
| `vierachs_entgraten.py` | 4-Achs-Bearbeitung, CAM-Operation „Rundum entgraten“ (W-003 V4d): Proxy `RundumEntgraten` wie „Rundum schruppen“; Breite, Kanten und Ausgelassen; `lege_an()`, `aendere()`, `bahn_fuer()` auch für die Vorschau |
| `hoehenfeld.py` | 2,5D (W-006 S3a): die ebenen Flächen nach oben und die Oberseite eines Teils (`ebenen_oben`, `oberseite`), das Netz ohne gewählte Flächen, die Hüllfläche je Zeile mit jeder Fräserform (`je_zeile` – dieselbe Rechnung wie `vierachs_huelle`, nur senkrecht); `hoehen()`: die Oberseite eines Netzes im Raster – je Zelle das höchste Dreieck über ihrer Mitte (das fertige Teil für den Vergleich im Quader, S3d); `netze_ohne` gibt mehrere Netze aus einer Vernetzung, ohne verwaiste Ecken (die Hüllfläche rechnet auch gegen Ecken); `netze_je_hoehe` je Höhe der gewählten Flächen ein Netz ohne die Flächen dieser Höhe – die anderen bleiben drin (Oberseite und Taschenboden in einer Operation: der Boden sperrt die Oberseite), `netz_fuer(netz, ebene)` nimmt das passende |
| `bahn.py` | 2,5D und 3D (W-006 S3a): die Bahn mit senkrechter Werkzeugachse – Punkte mit Geraden und Bögen (G2/G3), Eilgang, Eintauchen, Vorschubanteil je Satz; Weg, Zeit (`dauer`: nur Vorschub; `zeit`: mit Eilgang und Beschleunigung über `fahrzeit`, so steht sie im Assistenten) und die Path-Befehle mit F – die eine Stelle für alle ebenen Strategien |
| `planfraesen_bahn.py` | 2,5D, Bahn „Planfräsen“ (W-006 S3b): Zeilen hin und her in Lagen vom Rohteil bis auf die Fläche plus Aufmaß, Überlauf, seitlich über den Rand, Halbkreise zwischen den Zeilen, Zeilen halten vor Wänden (Hüllfläche), keine Zeile ohne Rohteil, Rampe ins Material, beim Austritt langsamer; vor Wänden die Wandfahrt (`_wandfahrt`): zur vorigen Zeile zurück und über die erste und letzte Zeile hinaus bis an den Rand der Fläche – sonst bliebe zwischen den Zeilen und in den Ecken an der Wand ein Rest (gefunden mit der Simulation, S3d); je Fläche beide Zeilenrichtungen gerechnet und die schnellere genommen (`bahn.zeit`; Grundsatz 0: die Zeit entscheidet), die andere Zeit steht im Ergebnis |
| `planfraesen.py` | 2,5D, CAM-Operation „Planfräsen“ (W-006 S3b): Proxy `PlanFraesen` mit FreeCADs Tiefen und Höhen; Flächen, Zustellung, Zeilenabstand, Aufmaß, Überlauf; `lege_an()`, `aendere()`, `bahn_fuer()` und `vorschau()`; mit Oberfläche bekommt die Operation die Anzeige aus `gui_vierachs_operation` |
| `kontur_bahn.py` | 2,5D, Bahn „Kontur“ (W-006 S3e): Wände (senkrechte Flächen mit waagerechter Unterkante, `waende`), ihre Unterkanten zu Konturen verbunden (`konturen`, Part.sortEdges; geschlossen oder offen, die freie Seite aus der Außennormale), der Versatz der Kontur um Radius + Aufmaß + k · ae (`Part.Wire.makeOffset2D`: Ecken außen als Bögen) – so viele Schruppbahnen, wie Rohteil neben der Wand steht oder die Breite sagt –, in Lagen bis auf die Unterkante, dann Schlichten bei Radius in einem Zug (höchstens die Schneidenlänge); Gleichlauf (Spindel M3: Material rechts – um einen Zapfen im Uhrzeigersinn, in der Tasche gegen ihn), tangentiales Ein- und Ausfahren (Gerade + Viertelkreis, kürzer, wo es nicht passt), Rampe im Material, Hüllfläche im Raster mit zwei Netzen (`_Huelle`: nahe der Wand ohne ihre Böden und Decken, weiter weg nur ohne die Wände), kein Rohteil – keine Bahn, beim Austritt langsamer; das Ein- und Ausfahren hält zu jeder Wand der Konturen den Abstand der Bahn (Radius + Aufmaß; `_Huelle.abstand_zur_wand`), weil die Hüllfläche die eigenen Wände nahe der Bahn ausblendet – sonst wird es kürzer; `Konturwerte.nur_wo` schränkt die Bahn ein – fürs Restmaterial `nur_wo_der_grosse_nicht_hinkam` (nur wo der Kreis des kleinen aus jedem Kreis des großen ragt, um r länger) |
| `kontur.py` | 2,5D, CAM-Operation „Kontur“ (W-006 S3e): Proxy `Kontur` mit FreeCADs Tiefen und Höhen; Flächen (Wände), Zustellung, Zeilenabstand, Aufmaß, Schlichten, Breite, Tiefer, Einfahrradius; `lege_an()`, `aendere()`, `bahn_fuer()` und `vorschau()`, die Schneidenlänge aus dem ToolBit; mit `RadiusDavor` > 0 das Restmaterial („Restmaterial T3“, `ist_rest`) |
| `raeumen_bahn.py` | 2,5D, Bahn „Räumen“ (W-006 S3f): ebene Flächen nach oben und Taschenböden mit Ringen räumen – wie ein HSM-Weg: volle Zustellung, schmales ae, ohne Wenden, mit Bögen. Ein Raster (0,5 mm; Vorschau 1 mm) über der Fläche: gesperrt, wo die Hüllfläche des Teils (Fräser um Aufmaß + Toleranz vergrößert) über der Lage liegt (um eine Zelle breiter, auch diagonal), Rohteil, wo Material steht, und `frei`, was schon geschnitten ist (Stempel der Stirn); die Ringe sind Höhenlinien des Abstandsfelds D zum Gesperrten (Marching Squares, verkettet, vereinfacht) bei Radius + Aufmaß + k · ae, vom Rohteil her analytisch (Rechteck mit runden Ecken, der erste R − ae außerhalb in der Luft); drei Varianten – „rohteil“ (die Ringe um das, was noch steht: Höhenlinien von F = min(Tiefe im Rohteil + R, D + ae) bei m · ae – das Rechteck beißt in die Inseln, die Ringe nur um Inseln kommen zuletzt von außen nach innen), „morph“ (Höhenlinien eines harmonischen Felds u – 1 am ersten Ring außen, 0 an der Insel, rot-schwarz SOR im Raster: vom Rechteck von Ring zu Ring runder bis zur Insel; der nächste Ring ist die tiefste Höhenlinie, auf der der Eingriff – `_Feld.eingriff()`, das stehende Rohteil gefaltet mit der Stirn per FFT – nirgends größer ist als beim geraden Schnitt mit ae (Bisektion über u); der letzte Ring der genaue Versatz der Insel mit Bögen (`inselringe`, `_genau`) – an der Wand einer Tasche nach dem Ring aus dem Raster (`_Ring.tasche`); alle Ringe als eine Spirale mit gleitenden Übergängen über 2 R (`_spirale`); nicht für Inseln am Rand oder außer der Mitte – `_KeinMorph`, wenn der schmalste Spalt unter 0,4 des breitesten liegt) und „inseln“ (D-Ringe von außen nach innen; in der Tasche von innen nach außen) –, alle gerechnet, die schnellste nach `bahn.zeit` (Grundsatz 0). Je Lauf der Eingang: an den vorigen anhängen (Spirale, ≤ 2 ae und frei), tangential aus dem Freien (`kontur_bahn._anfahrt` auf der freien Seite – links im Gleichlauf, rechts im Gegenlauf), quer aus dem Freien (`_seitlich`), das Anfangsstück nachholen, wenn hinter dem Anfang die Insel liegt (`_eingang_voraus`, `reste_fahren`), zuletzt die Rampe – rundum auf einem ganzen Ring (Tasche: einmal je Lage), sonst längs des Laufs; frei heißt: unter der Stirn höchstens so viel ungeschnittenes Rohteil wie im Streifen ae. Gleichlauf oder Gegenlauf (D links/rechts abgetastet), beim Austritt halber Vorschub; Taschen über die Konturen (`ist_tasche`, `taschenboeden`; dort nur „inseln“), die Lagen beginnen an ihrer Oberkante, wenn darüber schon geräumt ist (sonst am Rohteil) |
| `nut_bahn.py` | 2,5D, Bahn „Nut“ (W-006 4.1 Punkt 6): `nuten()` – Langlöcher aus einer Wand (die ganze Runde) oder dem Grund (die Wände am Rand), Kontur mit zwei Halbkreisen gleichen Radius und zwei Geraden (`_langloch`, Stücke erlaubt), die freie Seite innen, durchgehend ohne Material knapp innerhalb der Wände unter dem Grund (`_durch`); gemerkt je Form und Fläche; `ganze_nuten` (eine Wand meint alle Wände der Nut); `verfahren` – Trochoide (Kreise r − R − Aufmaß ≥ ¼ R: je Lage Helix am Ende, Kreise mit ae vorrückend, von Kreis zu Kreis hinten im Freien weiter, die nächste Lage zurück), Vollnut (Zickzack-Rampe längs der Mittellinie, je Fahrt ≤ min(ap, D/2)/2, Vorschub-Anteil 2·√(k(1−k)) mit k = ae/D), zu schmal, zu breit (> 0,9 R: ein Kern bliebe); zuletzt die Wand rundum mit Halbkreisen aus der Mitte eines Endes (je Zug ≤ Schneidenlänge); Gleichlauf gegen den Uhrzeigersinn; durchgehende `TIEFER` unter den Grund; Zeit mit `bahn.zeit`; offene Nuten (P-2026-10-01-47): `_waende_offen` (von einer Wand über ihren Grund zu allen Wänden an seinem Rand), `_gerade`, `_frei_hinter` (Luft hinter dem Ende: quer über die Breite, unten, mittig, oben), `_offene_nut` (zwei parallele Wände – an beiden Enden offen – oder Halbkreis und zwei Geraden – an einem), `Nut.offen_a/offen_b/gesamtlaenge`; Bahn: `_vor_dem_ende` (draußen hinab in der Luft), `_kreise`, `_offene_lagen` (der erste Kreis nimmt gerade ae, hinaus ins Freie, am Halbkreis die Helix), `_offen_schlichten` (an der einen Wand hinein, außen oder um den Halbkreis hinüber, an der anderen heraus) |
| `bohrung_bahn.py` | 2,5D, Bahn „Bohrung fräsen“ (W-006 S3g): `bohrungen()` – senkrechte Zylinderflächen ganz herum, die Normale zur Achse (sonst ein Zapfen), durchgehend, wenn rundum knapp innerhalb der Wand unter ihrem Grund kein Material ist (`_boden_unter`: nicht auf der Achse – Senkungen und Bohrspitzen haben dort Luft), `spitze` der Winkel eines Kegels darunter, der nach unten spitz zuläuft (`_spitze_unter`, FreeCADs Bohrung: 118°); je Bohrung die Helix hinab (`_helix`: Bögen je ≤ ¼ Umlauf mit Z, Radius min(Bohrung − R − Aufmaß, 0,9 R), Steigung 2π · r · tan Eintauchwinkel, unten ein Umlauf), bei Bohrungen größer als zwei Fräser je Lage Ringe nach außen (`_halbkreis` hinüber), das Schlichten bei Radius mit Halbkreisen aus der Mitte (`_schlichten`, je Zug ≤ Schneidenlänge); Gleichlauf gegen den Uhrzeigersinn; durchgehende `TIEFER` (0,5 mm) unter den Grund; die Reihenfolge der nächsten Bohrung; Zeit mit `bahn.zeit` |
| `bohren.py` | 2,5D, „Bohren“ aus dem Assistenten (W-006 S3g): FreeCADs Bohr-Operation (Path.Op.Drilling) mit einem Bohrer aus der Werkzeugverwaltung – `kann()`/`passende()` (Bohrungen mit seinem Durchmesser, durchgehend oder mit der Spitze seines Winkels darunter; eine Sackbohrung mit ebenem Grund nicht), `spitze()`, `hub_fuer()` (ab 3 × D im Material, ab der Oberkante des Rohteils, je 1 × D), `planen()` (die Bewegungen von G81/G83 mit R 3 mm über dem Rohteil und G98 – für die Zeit), `lege_an()` (je Tiefe des Grunds eine Operation, `gewinde.je_tiefe`, über `bohrzyklus()` – FreeCADs Drilling für jeden Bohrzyklus des Assistenten; ohne FreeCADs Vorgaben, die bei mehreren Controllern nachfragen; Basis, „Drill Tip“, Hübe, FreeCADs Ansicht), `ist_bohren` |
| `entgrat_bahn.py` | 2,5D, Bahn „Entgraten“ (W-006 4.1 Punkt 8): `waende()` (gewählte Wände und die, die an den Kanten gewählter ebener Flächen hinab gehen), `hat_oberkanten()`, `ketten()` (waagerechte Oberkanten mit einer ebenen Fläche nach oben darüber, je Höhe zu Ketten verbunden – `Kette` mit kontur_bahn.Kontur, Kante und Boden), `masse()` (Tiefe der Fase b / tan(α/2), „tiefer“ höchstens bis der Kegel noch über die Kante reicht), `abstand_zur_wand()` (d/2 + tiefer · tan(α/2), wie FreeCADs Deburr), `planen()` (je Kette der Versatz aus kontur_bahn, die Hüllfläche des Kegels, senkrecht hinab in der Luft, tangential hinein und heraus, nie unter die Unterkante der Wand), `netze()`; gezeichnete Fasen und Rundungen (`_fase`, `_rundung_radius`, `ist_fase`, `hat_fasen`, `fasen()`: schräge Flächen oder Rundungen an Oberkanten, die Kette an ihrer Unterkante auf die Oberseite gehoben, Breite, Winkel oder Radius aus dem Modell, der Fräser muss passen); mit `Entgratwerte.profilradius` verrundet ein Radienfräser (Spitze einen Radius unter der Kante, Achse die halbe Führung neben der Wand) |
| `entgraten.py` | 2,5D, CAM-Operation „Entgraten“: Proxy `Entgraten` mit FreeCADs Tiefen und Höhen; Flächen, Breite, Tiefer, Einfahrradius, Sicherheitsabstand; Ergebnis Ketten, Ausgelassen; `kegel_des_werkzeugs` (nur Fasenfräser), `rechne`, `bahn_fuer`, `vorschau`, `lege_an`, `aendere`, `eindringtiefe` (für das Prüffenster), `ist_entgraten` |
| `schlichten3d_bahn.py` | 3D, Bahn „3D-Schlichten“ (W-006 4.2 Punkt 3): `ist_freiform` (nach oben, weder eben noch senkrecht, keine gezeichnete Fase, keine Senkung), `zeilenabstand` (aus der Grathöhe über `Form.kammhoehe`, höchstens 0,9 D), Steil/Flach (`_raster`: die Hüllfläche im Raster mit Neigung aus dem Gradienten; `_hoehenlinien`: wo steiler als `GRENZWINKEL`, Linien gleicher Höhe über `raeumen_bahn._hoehenlinien`, geteilt nach der Maske (`_stuecke`), gerichtet mit dem Material rechts (`_gerichtet`), nahe Stücke über `_verbinden` gleitend; die Zeilen nur, wo es flacher ist, um `UEBERLAPP` überlappend), `_netze` (das Teil ganz und ohne die gewählten Flächen, einmal vernetzt), `planen` – je Richtung (x, y; die schnellere) die Hüllfläche je Zeile zweimal (`hoehenfeld.je_zeile` mit `Form.mit_aufmass`), gefräst, wo die mit den Flächen höher liegt (`MASKE`), Läufe je Zeile (`_laeufe`: um eine Stelle verlängert, Lücken unter `LUECKE_FAHREN` durchgefahren), vereinfacht (`_vereinfacht`, Douglas-Peucker), Zickzack mit `_hinueber` (nah: `LUFT` über beiden Zeilen gleiten, sonst Eilgang; hinab im Eilgang nur bis über das Rohteil); Zeit mit `bahn.zeit` |
| `schruppen3d_bahn.py` | 3D, Bahn „3D-Schruppen“ (W-006 4.2 Punkt 1): `bereich` (die Freiformflächen und ihr tiefster Punkt), `_lagen` (Hauptlagen gleich weit bis zum tiefsten Punkt plus Aufmaß, je höchstens ap; nach jeder die Zwischenlagen bis zur vorigen, von oben nach unten), `_schruppen` – das Raster des Räumens (`raeumen_bahn._Feld`) über dem ganzen Teil, gesperrt, wo die Hüllfläche mit Aufmaß über der Lage liegt; die Hauptlagen wie das Räumen (Varianten rohteil/morph/inseln, die schnellste), die Zwischenlagen nur, wo über der Lage Material steht, das der Fräser erreicht – die Materialhöhe je Zelle (gesenkt, wo die Stirn fuhr; `_Aufweiten` faltet Masken mit der Scheibe über die FFT), die Ringe aus `_ringe_zwischen` (der erste nimmt ae vom äußersten Material, dann gleich weit bis D = 0, je höchstens 1,1 · ae) mit weiterem ae (ae · ap der Hauptlage, höchstens R), das Einfahren mit der Schwelle der Hauptlage; `_Lage3D` (Eilgang hinab bis über das höchste Material unter der Stirn); die Ringe geglättet (`GLAETTEN`), `planen` |
| `schruppen3d.py` | 3D, CAM-Operation „3D-Schruppen“: Proxy `Schruppen3D` mit FreeCADs Tiefen und Höhen; Flächen, Zustellung, Zeilenabstand, Aufmaß, Zwischenlagen, Gleichlauf, Sicherheitsabstand, Eintauchwinkel; Ergebnis Lagen, Zwischen, Ringe; `lege_an`, `aendere`, `vorschau` (gröber), `ist_schruppen3d` |
| `bleistift_bahn.py` | 3D, Bahn „Bleistift“ (W-006 4.2 Punkt 6): die Hüllfläche im Raster wie beim 3D-Schlichten (`schlichten3d_bahn._raster`), `knicke` (die zweite Differenz in vier Richtungen durch den Abstand größer als `KNICK`, nur das Maximum quer zum Knick, nah an den gewählten Flächen; der Versatz zur Spitze des V aus den Nachbarn), `_linien` (Knickzellen zu Linien verkettet, möglichst geradeaus; kurze Stücke neben einer längeren fallen weg), `_geglaettet`, `_dichter`, `huelle_an` (die Hüllfläche genau an einzelnen Punkten), `_vereinfacht3d` (Douglas-Peucker im Raum), `planen`, `_fahren` (die nächste Linie zuerst, ein Ring ab der nächsten Stelle, senkrecht hinab im Eintauchvorschub) |
| `bleistift.py` | 3D, CAM-Operation „Bleistift“: Proxy `Bleistift` mit FreeCADs Tiefen und Höhen; Flächen, Aufmaß, Sicherheitsabstand; Ergebnis Linien, Länge; `lege_an`, `aendere`, `vorschau` (gröber), `ist_bleistift` |
| `schlichten3d.py` | 3D, CAM-Operation „3D-Schlichten“: Proxy `Schlichten3D` mit FreeCADs Tiefen und Höhen; Flächen, Grathöhe, Aufmaß, Richtung (auto/x/y), Sicherheitsabstand; Ergebnis Zeilen, Abstand; `lege_an`, `aendere`, `vorschau` (gröber vernetzt und abgetastet), `ist_schlichten3d` |
| `reiben.py` | 2,5D, „Reiben“ aus dem Assistenten (W-006 4.1 Punkt 7): FreeCADs Bohr-Operation mit G85 (heraus im Vorschub) und einer Reibahle im Ø der Bohrung – `kann()`/`passende()` (durchgehend oder mit Bohrspitze; ebener Grund nicht), `endtiefe()` (durchgehend `ANSCHNITT` 1 mm unter den Grund, sonst der Grund der Wand), `planen()` (für die Zeit), `vorschau`, `lege_an` (je Tiefe eine Operation über `bohren.bohrzyklus`), `ist_reiben`; das Vorbohren mit Untermaß steht in `bohren` (`REIBZUGABE`, `kann(…, reiben=True)`) |
| `senken.py` | 2,5D, „Zentrieren“ und „Senken“ aus dem Assistenten (W-006 S3g): FreeCADs Bohr-Operation mit einem Kegel – `senkungen()` (Kegelflächen ganz herum, nach oben offen, Material außen, darunter eine Bohrung; `Senkung` mit Ø oben, Winkel, Bohrung), `tiefe_fuer()` ((D − d) / 2 / tan(α/2)), `zentrierstellen()` (oben Ø Bohrung + 2 · FASE, höchstens 0,9 × Ø des Anbohrers, unter einer Senkung ab deren Oberkante), `passende_senkungen()` (Winkel und Ø des Senkers), `planen()` (für die Zeit), `vorschau_zentrieren/senken`, `zentrieren_anlegen` (mit Eigenschaft „Fase“ fürs Prüffenster), `senken_anlegen` – je Tiefe eine Operation über `bohren.bohrzyklus` |
| `namen.py` | Namen der Operationen: `eindeutig()` hängt „ (2)“ an, bevor FreeCAD einen doppelten Namen sieht (sonst „Bohren T001“), `nach_vorlage()` erkennt einen vorgeschlagenen Namen, auch mit „ (2)“ |
| `gewinde.py` | 2,5D, „Gewinde bohren“ aus dem Assistenten (W-006 S3g): FreeCADs Gewinde-Operation (Path.Op.Tapping) mit einem Gewindebohrer aus der Werkzeugverwaltung – `kernloch()` (Gewinde-Ø − Steigung), `passende()` (Bohrungen mit diesem Kernloch), `gewinde_name()` („M10x1.5“, nur ASCII – der Name steht als Kommentar im Programm), `tiefe_fuer()` (durchgehend um den Anschnitt 2 × P hinaus, Sackbohrung P über dem Grund), `planen()` (hinein und heraus mit P · n, für die Zeit), `je_tiefe()` (FreeCAD fährt alle Löcher einer Operation bis zu ihrer einen Endtiefe), `lege_an()` (je Tiefe eine Operation, G84 bzw. G74, R 3 mm über dem Rohteil, FreeCADs Ansicht), `ist_gewinde` |
| `gewinde_bahn.py` | 2,5D, Bahn „Gewinde fräsen“ (W-006 S3g): `tabelle()` (metrische Innengewinde 6H aus `daten/gewinde_6H.csv`), `gewinde_fuer()` (das Gewinde, dessen Kerndurchmesser D1 die Bohrung hat, mit der Steigung des Fräsers), `naechstes()` (für den Satz, wenn keins passt), `zaehne_fuer()` (Zähne übereinander aus der Schneidenlänge), `stelle()` (je Bohrung: Spitze des Zahns auf der Mitte der Toleranz von D2, Radius der Helix, z unten und oben aus der Zahnform; Fehler mit einem Satz), `richtung()` (G2/G3 und hinauf oder hinab aus Gleichlauf und Linksgewinde), `planen()` (Halbkreis hinein mit P/4, Helix in Vierteln, Halbkreis heraus; der Vorschub der Mitte r / (r + R) als `bahn.Punkt.anteil`; Ringe fürs Prüffenster) |
| `gewindefraesen.py` | 2,5D, CAM-Operation „Gewinde fräsen“ (W-006 S3g): Proxy `GewindeFraesen` mit FreeCADs Tiefen und Höhen; Flächen, Steigung, Zähne, Gleichlauf, Linksgewinde, Durchgänge, Korrektur, Sicherheitsabstand; Ergebnis Gewinde, Bohrungen, Umläufe; `werkzeugwerte()` (Ø, Spitze, Flankenwinkel, Hals, Reichweite aus dem ToolBit), `aus_werkzeug()`/`zaehne_von()` (aus der Werkzeugverwaltung), `rechne`, `bahn_fuer`, `vorschau`, `lege_an`, `aendere`, `ringe()` (fürs Prüffenster), `ist_gewindefraesen` |
| `nut.py` | 2,5D, CAM-Operation „Nut“ (W-006 4.1 Punkt 6): Proxy `Nut` mit FreeCADs Tiefen und Höhen; Flächen (Wände oder Grund), Zustellung, Zeilenabstand, Aufmaß, Schlichten, Gleichlauf, Tiefer, Sicherheitsabstand, Eintauchwinkel; Ergebnis Nuten, Lagen, Kreise; `lege_an`, `aendere`, `vorschau`, `ist_nut` |
| `bohrung.py` | 2,5D, CAM-Operation „Bohrung fräsen“ (W-006 S3g): Proxy `BohrungFraesen` mit FreeCADs Tiefen und Höhen; Flächen (die Zylinderflächen), Zustellung, Zeilenabstand, Aufmaß, AufmassBoden, Schlichten, Gleichlauf, Tiefer, Sicherheitsabstand, Eintauchwinkel; Ergebnis Bohrungen, Lagen, Umläufe; `lege_an`, `aendere`, `vorschau`, `ist_bohrungsfraesen` |
| `raeumen.py` | 2,5D, CAM-Operation „Räumen“ (W-006 S3f): Proxy `Raeumen` mit FreeCADs Tiefen und Höhen; Flächen, Zustellung, Zeilenabstand, Aufmaß (Wände), AufmassBoden, Gleichlauf, Variante (automatisch/rohteil/inseln), Einfahrradius, Eintauchwinkel, VorschubAustritt; Ergebnis Ebenen, Lagen, Ringe, Läufe, Gerechnet („rohteil 33,3 min · inseln 40,5 min“); `lege_an()`, `aendere()`, `bahn_fuer()`, `vorschau()`, `konturen_des_teils()` |
| `gui_bearbeitung.py` | Befehl und Assistent „Bearbeitung (Fräsen)“ für ein Teil im Quader (W-006 S3c, E4; S3e): eine Fläche anklicken – der Job mit dem Rohteil (Quader mit Aufmaß oben, seitlich, unten; die Felder ziehen es nach) entsteht sofort in der Transaktion des Fensters –, der Nullpunkt (S3h: wie im Modell oder einer der 22 Punkte des Rohteil-Quaders – Ecken, Kantenmitten, Mitte oben/unten –, um X, Y, Z verschoben; `_nullpunkt_setzen` rückt den Klon und das Rohteil, das seine Lage nur beim Anlegen kennt), Flächen (ebene nach oben fürs Planfräsen, ohne Wahl die Oberseite; Wände für die Kontur; Liste grün/rot, Farben am Teil), Werkstoff, dann je Strategie (`_Strategie`: `_Planfraesen`, `_Raeumen`, `_Bohren`, `_Bohrung`, `_Zentrieren`, `_Kontur`, `_Rest`, `_Senken`, `_Gewinde`, `_Entgraten`; welches Werkzeug passt, sagt `werkzeug_passt` – beim Bohren Bohrer, vorgewählt der mit dem Durchmesser der Bohrung, `_bohrer_waehlen`; beim Gewinde Gewindebohrer mit Steigung, vorgewählt der mit dem Kernloch, `_gewindebohrer_waehlen` – nie vorgeschlagen, ohne Wettbewerb; beim Entgraten Fasenfräser, ebenfalls nie vorgeschlagen; Zentrieren mit dem NC-Anbohrer, von Hand; Senken mit dem Kegelsenker, der zur Senkung passt – `_senker_waehlen`, vorgeschlagen; Restmaterial mit dem größten kleineren Fräser, der Ø davor von der Kontur oder dem Räumen – `_restfraeser_waehlen`, `_davor_durchmesser`, von Hand) ein Block (`_Block`) mit Haken – vorgeschlagen nach der Wahl –, Fräser mit ebener Stirn und Einsatz aus der Werkzeugverwaltung, den Feldern mit grauen Vorschlägen und „→ 3 Lagen, 30 Zeilen, etwa 3 min“ bzw. „→ 2 Konturen: 22 Lagen, 38 Bahnen …“ aus der Vorschau; je Gruppe (`_gruppen`: Planfräsen und Räumen; Bohren, Bohrung fräsen und Kontur) auf denselben Flächen rechnen alle, sobald eins angehakt ist (`_im_wettbewerb`, `_gleiche_flaechen`), die schnellste bekommt den Haken, jede Zeile sagt, um wie viel, ein roter Block der Gruppe verliert seinen Haken, wenn eine andere die Flächen kann (`_wettbewerb`, `_haken_setzen`; Grundsatz 0 – ein von Hand gesetzter Haken bleibt, die Zeilen vergleichen trotzdem); ebene Flächen mit Taschenböden: die Folgen Planfräsen + Räumen der Böden gegen Räumen über alles (`_folge`, `_nur_boeden`); die Kontur nach dem Räumen mit Breite = Aufmaß (`_zusatz`), ohne die Bohrungen, die Bohren oder Bohrung fräsen nimmt; Bohrung fräsen tritt nicht an, wo das Räumen den Boden der Bohrung räumt (`_von_raeumen_geraeumt`); „Anlegen“: Job und Rohteil ein Schritt Rückgängig, Controller und die angehakten Operationen ein zweiter (`_im_befehl` aus `gui_vierachs`). Mit `operation=` zum Ändern (Doppelklick): nur ihr Block, Rohteil fest, „Übernehmen“ ein Schritt Rückgängig |
| `gui_start.py` | Anmeldung in FreeCAD: Befehle, Werkzeugleiste (Arbeitsbefehle) und Menü „CAM-Addon“ (alle Befehle); ruft die anderen `gui_*` auf |
| `gui_maschine.py` | Befehl und Aufgabenfenster „Maschine bearbeiten“; ohne Baugruppe der Weg zu den Beispielmaschinen |
| `gui_neue_maschine.py` | Befehl und Dialog „Neue Maschine …“: Bauart wählen, bei Drehmaschine und 3-Achs-Fräse Maße eintragen (Wege „von“ mit festem Minus vor dem Feld, nur die Zahl eintragen – Z der Drehmaschine ab der Spindelnase ohne Minus), bauen – auch hinter „Beispielmaschine laden …“ |
| `gui_verfahren.py` | Befehl und Aufgabenfenster „Maschine verfahren“: ein Regler je Achse |
| `gui_reichweite.py` | Befehl und Aufgabenfenster „Auf der Maschine prüfen“ (W-001 Stufe 4a): Job, Nullpunkt, Ergebnis in Sätzen; ein Klick fährt die Maschine an die Überschreitung; öffnet im Dokument der Maschine |
| `gui_abfahren.py` | Abfahren (W-001 Stufe 4b): Werkzeug, Rohteil, Modell und Bahn als Coin-Knoten in der 3D-Ansicht der Maschine (nichts im Dokument), folgen der Maschine; der Abspieler als Bereich im Fenster „Auf der Maschine prüfen“; Rohteil und Fertigteil: die Stange als Fläche über (a, φ), der Quader als Fläche über (x, y) mit Seitenwänden und Boden, beim Abspielen abgetragen, am Ende in den Farben des Vergleichs (V3g, S3d) |
| `gui_kollision.py` | Bereich „Kollision“ im Fenster „Auf der Maschine prüfen“ (W-001 Stufe 4c): Warnabstand, „Kollision prüfen“ mit Fortschritt und Abbrechen, Urteil und Sätze rot/gelb; ein Klick stellt den Abspieler hin, eine rote Kugel zeigt die Stelle |
| `gui_details.py` | Felder der gewählten Betriebsart, Aufnahme oder schrägen Achse |
| `gui_winkelbild.py` | Bild zur schrägen Achse: ausgleichende Achse, rechter Winkel, schräge Achse mit α |
| `gui_zahlen.py` | Zahlenfelder für alle Dialoge: Format mit dem gewählten Dezimalzeichen ohne Tausenderpunkte, Prüfung (Punkt und Komma), Lesen, Zeigen; Dezimalzeichen in Texten |
| `gui_teile.py` | Kleine Bausteine der Werkzeugverwaltung: fette Beschriftung, Knopf, Feld mit Einheit, rote Hinweiszeile, Grau |
| `gui_zeigen.py` | Hervorheben und kurzes Hin-und-her-Bewegen in der 3D-Ansicht |
| `gui_hilfe.py` | Knopf (?) und Hilfefenster |
| `gui_verteilhilfe.py` | Dialog „Revolverplätze verteilen“ |
| `gui_bericht.py` | Bericht nach „An CAM übergeben“ |
| `gui_sprachwahl.py` | Sprachwahl beim ersten Start, Einstellungsseite |
| `gui_aktualisierung.py` | Befehl „Nach Updates suchen“, Update-Hinweis, Gruppe „Updates“ in den Einstellungen (Suche beim Start ab Werk aus) |
| `gui_werkzeuge.py` | Befehl und Dialog „Werkzeugverwaltung“: oben „Werkstoffe…“ und mm/inch, links die Werkzeugliste, rechts die Felder des Werkzeugs und die Schnittwerte (`gui_schnittwerte`) |
| `gui_halter.py` | Fenster „Halter“ (W-002 Stufe D) aus der Werkzeugverwaltung: Liste mit Suche, Neu (leer oder Vorlage), Kopieren, Löschen; Name, Bezeichnung, Spanntiefe, Kontur als Tabelle, Bild im Schnitt; arbeitet an einer Kopie, OK gibt dem Werkzeug den gewählten Halter |
| `gui_werkzeugbild.py` | Bild des Werkzeugs neben seinen Feldern (malt `werkzeugform`), Symbol je Art in der Auswahl |
| `gui_schnittwerte.py` | Schnittwert-Tabelle in der Werkzeugverwaltung: alle Einsätze des Werkzeugs, je Zeile vorn der Werkstoff, für den sie gilt (Auswahl je Zeile, Manuel 2026-10-01; „Alle Werkstoffe“, wo ein Werkstoff keine eigene Zeile hat), ae/ap/vc/fz eingegeben, n/vf/Q gerechnet; Eingriffsbild, Spandickenausgleich, Planer und Vergleich für den Werkstoff der gewählten Zeile |
| `gui_eingriff.py` | Bild des Eingriffs (Draufsicht und Seitenansicht) zur gewählten Zeile |
| `gui_strategie.py` | Dialog „Strategien vergleichen“: zwei Einsätze mit Balken und Urteil |
| `gui_schruppwerte.py` | Dialog „Schruppwerte planen“: Eingaben, Tabelle je ae, Vorschlag, als Einsatz übernehmen |
| `gui_werkstoffe.py` | Fenster „Werkstoffe“: ganze Liste mit Suche und Filter, eigene Werkstoffe |
| `gui_job_schnittwerte.py` | Befehl und Dialog „Schnittwerte in den Job“ |
| `gui_vierachs.py` | Befehl und Assistent „4-Achs-Bearbeitung“ in zwei Schritten: Rohteil (Fläche im 3D anklicken, Maschine zuerst, Rundachse, Stange, Mitte, Drehlage, Animation) und „Was willst du machen?“ (Rundum schruppen: Werkstoff, Fräser und Einsatz aus der Werkzeugverwaltung, Zustellung, Vorschub je Umdrehung, Aufmaß, Vorschau der Lagen; Rundum schlichten: Fräser jeder bekannten Form, Schrittweite aus der Werkzeugtabelle, Kammhöhe, grobe Vorschau mit Umdrehungen und Zeit; Abstände für beide; gelb unter dem Fräser, wenn er auf der gewählten Maschine nicht radial säße); „Anlegen“: Job und Stange ein Schritt Rückgängig, Controller und Operation ein zweiter. Mit `operation=` zum Ändern (V3h): Schritt 2 mit den Werten der Operation, „Übernehmen“ ein Schritt Rückgängig (`job_schnittwerte.controller_fuer`) |
| `gui_vierachs_operation.py` | Anzeige der Operationen des Addons im Baum: Symbol; Doppelklick und Kontextmenü „Bearbeiten“ öffnen den Assistenten zum Ändern (V3h) – „4-Achs-Bearbeitung“ für die Rundum-Operationen, „Bearbeitung (Fräsen)“ für „Planfräsen“ und „Kontur“ (`bearbeiten()` verteilt nach der Art) |

Zwei Regeln halten das zusammen:

- **Module ohne `gui_` im Namen importieren weder `FreeCADGui` noch Qt.**
  Sie laufen in FreeCADCmd und werden dort ohne Fenster geprüft.
- **Importiert wird nur von `gui_*` zu den übrigen Modulen, nie umgekehrt**,
  und kein Modul importiert ein anderes im Kreis.

## Die Kette (`kette.py`)

- **Bauteil:** was die Assembly als Ganzes bewegt – ein Körper oder ein Part
  mit allem darin (`UtilsAssembly.getMovablePartsWithin(…, partsAsSolid=True)`).
- **Glied:** Bauteile, die starr verbunden sind (Fixed-Gelenke,
  RigidGroups). Alle fixierten Bauteile bilden zusammen das **Bett**.
- **Achse:** ein Slider oder Revolute zwischen zwei Gliedern. Die Achsen
  bilden einen Baum, der beim Bett beginnt; jede kennt ihr Eltern-Glied (zum
  Bett hin) und ihr Kind-Glied (das, was sie bewegt).
- **Abfragen:** `kette.achse_von(gelenk)`, `kette.glied_von(objekt)` – auch
  für ein LCS in einem Part –, `kette.pfad_zum_bett(glied)`.
- **Eine Achse, ein Gelenk.** Eine Wiege, die in zwei Lagerböcken je ein
  Drehgelenk bekommt, kann die Assembly nicht lösen. Die Kette meldet das
  eigens (`kette.doppelt_gelagert`).

## Das Maschinenobjekt (`maschine.py`)

- Gruppe „Maschine“ in der Assembly, erkannt an `Typ == "CamAddon::Maschine"`.
- **Betriebsart:** Verweis aufs Gelenk, Art (Linear, Positionieren, Spindel,
  Revolver), NC-Name, Kennwerte. Ein Gelenk kann mehrere haben – die
  Hauptspindel etwa S4 (Spindel) und C4 (Positionieren).
- **Aufnahme:** Verweis aufs LCS (`PropertyLinkGlobal`, weil das LCS in
  einem Part liegt), Art (Werkzeug oder Werkstück), bei Werkzeugen optional
  Antrieb und Revolverplatz.
- **Transformation:** bisher nur die schräge Achse – Verweise auf zwei
  Betriebsarten (Linear: schräg und ausgleichend) und ihre Namen im
  Programm. Der **Winkel steht nur in der Baugruppe** (Richtung der
  Gelenke); `schraege_achse.winkel()` misst ihn, mit der Richtung, in die
  das Werkzeug gegenüber dem Werkstück fährt (Tischachsen andersherum).
- **Kennwert 0 heißt „unbekannt“.** Keiner dieser Werte kann an einer echten
  Maschine 0 sein.
- `pruefe()` liefert Meldungen, erst Warnungen, dann Hinweise. Jede trägt in
  `bezug` das Objekt, um das es geht; ein Klick im Dialog springt dorthin.
- `rollen()` ordnet jede Achse dem Tisch oder dem Kopf zu – über die Wege
  von den Aufnahmen zum Bett.

## Der Dialog (`gui_maschine.py`, `gui_details.py`)

- Ein Aufgabenfenster und zugleich eine Transaktion: OK übernimmt alles als
  **einen** Schritt Rückgängig, Abbrechen verwirft alles.
- Jede Eingabe geht sofort ins Dokument (`_setze`), damit Hinweise und
  3D-Ansicht stimmen. Danach werden die Listen nur **aufgefrischt**, nicht
  neu gebaut – ein Neuaufbau nach jeder Eingabe ließ FreeCAD unter PySide6
  abstürzen (P-2026-09-25-17). Neu gebaut wird nur, wenn sich die Gliederung
  ändert (anderes LCS, anderer Platz), und dann zeitversetzt.
- Die **Aktionen** hinter den Knöpfen sind öffentliche Methoden
  (`betriebsart_anlegen`, `uebergeben`, `zeige` …). Die Oberflächen-Szenarien
  benutzen dieselben Methoden oder bedienen Knöpfe, Menüs und Signale direkt.

## Texte, Sprachen, Hilfe

- Jeder Text der Oberfläche steht in `translations/<code>.json`. `de.json`
  ist führend und vollständig. Gesucht wird in der gewählten Sprache, dann
  auf Englisch, dann auf Deutsch; kennt keine Sprache den Schlüssel, erscheint
  der Schlüssel selbst.
- Im Code steht ein Schlüssel **immer als fester Text**: `tr("dialog.titel")`
  oder `meldung("kette.koerper_lose", …)`, nie zusammengesetzt. Nur so findet
  `tests/test_sprache.py` fehlende und überflüssige Schlüssel.
- Gespeicherte Werte sind feste ASCII-Wörter (`"Werkstueck"`); angezeigt
  werden sie über `art_text()`, `wert_text()` und `aufnahmeart_text()`.
- Hilfeseiten liegen in `help/<code>/<thema>.html`, die Themen in
  `hilfe.THEMEN`.

## Zwei FreeCAD-Versionen

Unterstützt werden die stabile Version (1.1.x) und der Wochen-Build. Der
Code fragt nach dem, was es gibt, nicht nach Versionsnummern:
`export.verfuegbar()`, `getattr(gelenk, "Suppressed", False)`,
`hasattr(gelenk, "ObjectsToRigidGroup")`. So wird eine Funktion von selbst
frei, sobald die stabile Version sie bekommt.

## Prüfen

- **Einmal einrichten:** `scripts/testumgebung_einrichten.sh` installiert
  beide FreeCAD-Versionen sowie black und ruff.
- **Alles:** `scripts/alle_tests.sh` – black und ruff, dann in beiden
  Versionen die Prüfungen ohne Fenster (`tests/test_*.py`) und die Szenarien
  mit Oberfläche (`tests/gui/szenario_*.py`). Mit `OHNE_OBERFLAECHE=1` laufen
  nur die schnellen Prüfungen. Wann das nötig ist und wann die Prüfungen zum
  geänderten Teil reichen: `docs/arbeitsregeln.md`, Abschnitt 5.
- **Eine Prüfung ohne Fenster** ist ein Skript für FreeCADCmd. Es endet mit
  der Zeile `OK <datei>`; FreeCADCmd meldet eine Ausnahme nicht zuverlässig
  über den Rückgabewert. `UEBERSPRUNGEN <datei>: Grund` ist nur erlaubt, wenn
  es die Funktion in der geprüften Version nicht gibt.
- **Ein Szenario** ist eine Generator-Funktion `schritte(h)`. `yield ms`
  wartet und lässt FreeCAD dabei weiterlaufen; `h.pruefe()`, `h.bild()` und
  `h.modal()` helfen beim Prüfen. FreeCAD läuft dabei unsichtbar (Xvfb) mit
  frischem Benutzerprofil.
- **Beispielmaschinen** für beide Arten: `tests/beispielmaschinen.py`
  (Drehmaschine mit Revolver, Fünfachser mit Schwenkbrücke).

## Stolpersteine

Alle ausprobiert und im Code an Ort und Stelle kommentiert:

| Stolperstein | Folge im Code |
| --- | --- |
| `objekt.Placement.Base = …` ändert nur eine Kopie | ganzes `Placement` zuweisen |
| Flächen für Gelenke gibt es erst nach `recompute()` | vor dem Anlegen neu berechnen |
| Ein einfacher Link auf ein LCS in einem Part ist „out of scope“ | `PropertyLinkGlobal` |
| `App::Origin` ist auch ein `LocalCoordinateSystem` | beim Anbieten von LCS herausfiltern |
| Beschriftungen sind eindeutig: „Futter“ neben „Futter“ wird „Futter001“ | Beschriftung aus den Daten (`beschrifte`) |
| Beim Laden ruft FreeCAD `onChanged` nicht auf, nur `onDocumentRestored` | Sichtbarkeit dort herstellen |
| Das deutsche Zahlenformat hat Tausenderpunkte: „30.000“ | Zahlenfelder ohne Tausendertrennzeichen |
| Enter in einem Feld löst im Aufgabenfenster „OK“ aus | der Dialog hält Enter an (`_EnterBleibtImDialog`) |
| Beim Beenden fragt FreeCAD „Speichern?“ | Szenarien schließen ihre Dokumente |
| `Machine.from_dict` liest den Ursprung einer Linearachse als Richtung | Ursprung 0 übergeben (T-004) |
| Die Knopfleiste macht OK beim Zeigen selbst zum Standardknopf – Enter in einem Feld schließt dann einen QDialog | `keyPressEvent` hält Enter an (Werkzeugverwaltung) |
| Werkstoffnummern wie „1.0503“ sehen aus wie Kommazahlen | `dezimal()` nur auf Zahlentexte, nie auf Werkstoffnamen |
| QTest tippt nur ASCII | in Szenarien Text ohne Umlaute tippen |
| FreeCADCmd 1.1.3 schreibt beim Neuberechnen einen Fortschrittsbalken ohne Zeilenende | Prüfungen, die neu berechnen, geben vor „OK“ eine Leerzeile aus |
| Die Zustelltiefe (`StepDown`) einer Operation hängt an einer Formel aus dem SetupSheet (Vorgabe: Werkzeugdurchmesser) – ein gesetzter Wert ist nach dem Neuberechnen wieder weg | vor dem Setzen `setExpression("StepDown", None)` |
| Die Schrittweite heißt in 1.1.3 `StepOver` (ganze Prozent), im Adaptive des Wochen-Builds `StepOverPercent` (Kommazahl) | `zustellung()` nimmt, was die Operation hat |
| Die Assembly setzt die Begrenzung eines Gelenks beim Lösen nicht durch; bewegt man nur einen Teil der Bauteile hinter einer Achse, zieht sie die Stellung beim Lösen woanders hin | `verfahren.py` bewegt immer alle Bauteile hinter der Achse und hält die Grenzen selbst ein |
| Eine Operation anlegen, wenn der Job mehrere Werkzeug-Controller hat: FreeCAD fragt welchen – in FreeCADCmd 1.1.3 ein Fehler | Prüfungen legen Operationen an, solange der Job nur einen hat |
| CAMs Werkzeugformen sind Skizzen: eine Kante der Länge 0 (Säge ohne Kappe, Gewindebohrer mit Schaft = D) oder ein Hals bis ans Ende lässt sie klagen oder keinen Körper bauen | `uebergabe_werkzeuge`: 1 µm statt 0, mindestens 1 mm Schaft; `test_cam_formen` fängt die Klagen auf der Konsole ab |
| Den Taster baut CAM von oben nach unten (Spitze bei −Länge) | `test_cam_formen` vergleicht ihn gespiegelt |
| Ein ToolBit, das an ein Dokument gehängt wurde, ist mit dem Dokument weg | vor dem Schließen lesen, was man braucht |
| CAMs Bibliotheksfenster lädt seine Oberfläche erst, wenn die Werkbank CAM einmal aktiv war | Szenario schaltet vorher auf CAM |
| Das Mausrad verstellt Auswahllisten, Drehfelder und Regler auch ohne Fokus – beim Blättern im Aufgabenfenster aus Versehen („P10“ im Revolverplatz) | `gui_teile.ruhiges_mausrad` (Filter, reicht das Rad an den nächsten rollbaren Bereich), Regler als `RuhigerRegler` – im Wochen-Build kommt das Rad dort am Filter vorbei; der schützt Drehfelder selbst (`Gui::WheelEventFilter`) |
| Mit `sendEvent` geschickte Rad-Ereignisse gibt Qt nicht an die Eltern weiter | `szenario_mausrad` dreht das Rad über XTest am virtuellen Bildschirm |
| FreeCADs Befehl „Job“ öffnet eine eigene Transaktion | der Assistent legt den Job mit `Path.Main.Job.Create` an und hängt die Anzeige selbst an (`Path.Main.Gui.Job.ViewProvider`) – alles in seiner Transaktion |
| Der Modell-Klon eines Jobs liegt beim Anlegen genau wie das Original | `vierachs_rohteil.richte_ein`: Klon = Lage · Lage des Originals, immer vom Original aus gerechnet |
| `Job.Create` und `Stock.CreateCylinder` legen im aktiven Dokument an | vorher `FreeCAD.setActiveDocument` |
| Die Python-Hülle eines Knopfs aus `modifyStandardButtons` verfällt mit der Hülle der Knopfleiste | die Knopfleiste aufheben, den Knopf jedes Mal über sie holen (wie CAM) |
| 1.1.3 gibt die Beschriftung eines per Abbrechen verworfenen Objekts nicht wieder frei | der nächste Job heißt „… 001“; Szenario prüft nur den Anfang |
| Legt CAM ein ToolBit an (auch den Vorgabe-Controller jedes neuen Jobs), öffnet und schließt es ein verstecktes Dokument – FreeCAD 1.1 schließt dabei außerhalb eines Befehls die offene Transaktion; der Rest ließe sich nicht mehr rückgängig machen. Der Wochen-Build führt Transaktionen je Dokument, dort nicht | `gui_vierachs._im_befehl`: in 1.1 als FreeCAD-Befehl ausführen und die Transaktion darin öffnen (sie bleibt mit `setActiveTransaction(…, True)` offen); ToolBit in einem eigenen Schritt Rückgängig |
| Die Hüllbox gekrümmter Flächen ist nur auf etwa 0,003 mm genau | Prüfungen vergleichen sie mit 0,01 mm |
