---
project: freecad_cam_addon
language: de
timezone: Europe/Berlin
status: planung
stack: Python, PySide (Qt), FreeCAD-API (CAM-Workbench)
zielsystem: aktueller Wochen-Build von FreeCAD, jedes Betriebssystem, keine bestimmte Maschine
patch_naming:
  pattern: "P-YYYY-MM-DD-XX <kurzbeschreibung>"   # im Commit-Betreff
  example: "P-2026-09-25-01 projektregeln"
---

# Verlauf (LOG/ARCHIV)

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
