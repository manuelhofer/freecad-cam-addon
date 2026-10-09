# Profilabhängigkeit der goldenen Gesamtfolge – statischer Befund

Untersucht am 09.10.2026 ausschließlich lesend; keine zusätzliche FreeCAD-Instanz
gestartet und keine Prüfdatei, Produktdatei oder Referenz verändert.

## Beobachtung

- Wiederverwendetes Profil: `test_simultan_folge_profil_wiederverwendet.log` meldet
  für die 2-mm-Variante **46,46216348782407 s** und scheitert am exakten NC-SHA.
- Frisches Profil: `test_simultan_folge_frisch.log` besteht mit
  **46,47016348782406 s**, 5948 Punkten, 6181 NC-Bewegungen und SHA-256
  `83a7f0968c79a088a898befb0c6425db21c7808f0bf112742529e8b92cb489a5`.
- Auch die 1-mm-Variante unterscheidet sich um etwa **0,008 s**:
  58,60611897634593 gegenüber 58,61411897634593 s. Das ist keine Änderung der
  Siegerauswahl; beide Läufe wählen weiterhin die 2-mm-Variante.

## Nachgewiesene Eingabekette

| Stelle | Wiederverwendetes Profil | Frisches Profil |
| --- | --- | --- |
| Profilordner | `/tmp/camaddon-schnittbereiche-test` | `/tmp/camaddon-folge-frisch` |
| `user.cfg`, `BaseApp/Preferences/Mod/CamAddon/ZuletztMaschine` | `/tmp/camaddon-schnittbereiche-test/tisch_tisch.FCStd` | nicht gesetzt |
| `user.cfg`, `…/Beispielmaschine` | `kopf_tisch` | nicht gesetzt |
| `CamAddon/maschinen.json`, Eintrag der zuletzt gemerkten Tisch/Tisch-Datei | `vorschub: 15000.0`, `werkzeugdrehzahl: 18000.0` | kein Maschinenspeicher vorhanden |
| Wirksamer Freivorschub für einen Job ohne eigene Zuordnung | **15000 mm/min** aus dem gespeicherten Eintrag | **10000 mm/min** aus der festen Vorgabe |

Der XML-Wertevergleich der beiden vorhandenen `user.cfg`-Dateien zeigt nur diese
beiden unterschiedlichen CamAddon-Parameter. Die zweite Tabellenzeile ist die
hier belegte Verbindung zur Bahnerzeugung; der Parameter `Beispielmaschine` ist
eine weitere gespeicherte UI-Auswahl und für diese Verbindung nicht erforderlich.

Die zugehörigen Codepfade im untersuchten Hauptrepo:

1. `tests/test_simultan_folge.py:38–74`: `aufbauen` erstellt eigene Standard-
   Werkzeugdaten, Bibliothek, Job sowie Schrupp-/Schlichtoperationen. Es setzt dabei
   **keine eigene Maschinendatei am Job** und neutralisiert keine zuvor gemerkte
   Maschine. Das Profil und sein Maschinenspeicher bleiben weitere Eingaben.
2. `tests/test_simultan_folge.py:90–92`: Die explizite G550-Prüfung wird erst
   **nach** diesem Aufbau angelegt. Sie ist nicht schon die Zuordnung des
   erzeugten Jobs während dessen vorangegangener Bahnerzeugung.
3. `camaddon/reichweite.py:344–348`: `gemerkte_maschine(job)` liest die Jobzuordnung;
   fehlt sie, verwendet die Funktion den globalen Parameter `ZuletztMaschine`.
4. `camaddon/freiwege.py:279–294`: `freivorschub_fuer(job)` liest diesen Pfad,
   sucht ihn im Maschinenspeicher und übernimmt dessen positiven `vorschub`.
   Ohne passenden Eintrag verwendet sie `FREIVORSCHUB` = `fahrzeit.EILGANG` =
   feste Vorgabe **10000 mm/min**.
5. `camaddon/schlicht_anlauf.py:177–183`: Auch die Schruppbahn mit Rampenanlauf
   übergibt genau diesen Wert an `freiwege.schneller`. Dadurch ist die gespeicherte
   letzte Maschine eine belegte zusätzliche Eingabe der freien Bahnverbindungen.

Damit ist eine **nicht vollständig festgelegte Eingabe der Prüf-Fixture** belegt.
Es ist weder notwendig noch angemessen, für diesen Befund Produktgrenzen oder
goldene Referenzen zu ändern. Die heutige vollständige Zulassung erfolgt weiter
im frischen Profil gegen die unveränderte Referenz.

## Grenze des Nachweises

Der tatsächliche NC-Dump des fehlgeschlagenen wiederverwendeten Laufs liegt nicht
als separater erhalten gebliebener Beleg vor. `folge_vor_qualifizierung.json/.mpf`
enthalten bereits den **frischen** Lauf und dessen richtigen Referenz-SHA.
`folge_kalt.mpf` stammt dagegen aus dem kalten Export eines am Vortag gespeicherten
Dokuments; es ist kein Dump der hier untersuchten wiederverwendeten Fixture.

Deshalb beweist diese statische Untersuchung die verschiedenen Eingaben und ihren
Codepfad, aber **noch nicht die vollständige punktweise Herleitung der 0,008 s oder
des abweichenden NC-SHA**. Insbesondere ist keine zufällige Änderung der
Schnittwerte/ToolController/Assets nachgewiesen und kein zusätzlicher Produktfehler
aus diesem Vergleich belegt. Ein erneuter teurer Lauf ist für den heutigen
frischen Referenznachweis nicht erforderlich.

## Kleinste empfohlene Fixture-Korrektur als späterer eigener Patch

Zu Beginn von `pruefen`, unmittelbar **nach** dem bestehenden Vergleich von
`FreeCAD.getUserAppDataDir()` mit dem angelegten Testprofil, den Parameter
`ZuletztMaschine` ausschließlich in diesem eigenen Profil entfernen. Der
Maßstabsfall verwendet dann ausdrücklich seine bisherige feste 10000-mm/min-
Vorgabe. Nach dem Jobaufbau diese Vorgabe mit
`freiwege.freivorschub_fuer(doc.Job)` prüfen und als Fixture-Eingabe protokollieren.
Das Entfernen muss für
die gesamte Prüfung wirksam bleiben, weil Varianten und Übernahme Bahnen erneut
rechnen; ein sofortiges Wiederherstellen vor dem Vergleich wäre unzureichend.

Diese kleine Änderung verändert keine Maschine, Anschläge, Schnittwerte,
Produktfunktionen oder bestehende Referenz. Als spätere Gegenprobe reicht ein
eigenes Testprofil mit zuvor gemerkter anderer Maschine und eine nachgewiesene
10000-mm/min-Fixture-Eingabe; ein vollständiger zusätzlicher Qualitätslauf wird
nur benötigt, wenn die anschließende tatsächliche NC dennoch abweicht.
