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
| `hilfe.py` | Hilfeseiten `help/<sprache>/<thema>.html` finden |
| `kette.py` | Assembly lesen: Glieder, Achsen, Meldungen |
| `maschine.py` | Maschinenobjekt: Objektarten, Anlegen, Revolverplätze, Prüfung, Tisch/Kopf |
| `export.py` | Übergabe an CAM mit Bericht |
| `aktualisierung.py` | Update-Suche per Git |
| `werkstoffe.py` | Werkstoffliste (W-002): mitgelieferte aus `daten/werkstoffe.json`, Anzeige, Suche |
| `werkzeuge.py` | Werkzeugbibliothek (W-002): Werkzeuge, Einsätze und Schnittwerte je Werkstoff, eigene Werkstoffe, Speichern als JSON |
| `schnittdaten.py` | Rechnen mit Schnittwerten: n, vf, Zeitspanvolumen, Eingriffswinkel, Spandicke |
| `gui_start.py` | Anmeldung in FreeCAD: Befehle, Werkzeugleiste; ruft die anderen `gui_*` auf |
| `gui_maschine.py` | Befehl und Aufgabenfenster „Maschine bearbeiten“ |
| `gui_details.py` | Felder der gewählten Betriebsart oder Aufnahme |
| `gui_zahlen.py` | Zahlenfelder für alle Dialoge: Format ohne Tausenderpunkte, Prüfung, Lesen, Zeigen |
| `gui_zeigen.py` | Hervorheben und kurzes Hin-und-her-Bewegen in der 3D-Ansicht |
| `gui_hilfe.py` | Knopf (?) und Hilfefenster |
| `gui_verteilhilfe.py` | Dialog „Revolverplätze verteilen“ |
| `gui_bericht.py` | Bericht nach „An CAM übergeben“ |
| `gui_sprachwahl.py` | Sprachwahl beim ersten Start, Einstellungsseite |
| `gui_aktualisierung.py` | Update-Hinweis, Gruppe „Updates“ in den Einstellungen |
| `gui_werkzeuge.py` | Befehl und Dialog „Werkzeugverwaltung“ |
| `gui_schnittwerte.py` | Schnittwert-Tabelle in der Werkzeugverwaltung |
| `gui_eingriff.py` | Bild des Eingriffs (Draufsicht und Seitenansicht) zur gewählten Zeile |

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
- **Vor jedem Push:** `scripts/alle_tests.sh` – black und ruff, dann in beiden
  Versionen die Prüfungen ohne Fenster (`tests/test_*.py`) und die Szenarien
  mit Oberfläche (`tests/gui/szenario_*.py`). Mit `OHNE_OBERFLAECHE=1` laufen
  nur die schnellen Prüfungen.
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
