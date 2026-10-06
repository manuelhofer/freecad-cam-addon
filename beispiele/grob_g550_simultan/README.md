# G550: Flanke mit fünf Achsen simultan

Ein fertiger CAM-Job zum Abfahren auf der groben G550-Beispielmaschine. Er verwendet
die vorhandene Strategie „Flanke (5 Achsen simultan)“ und deren Maschinenkinematik.

## Öffnen und ansehen

Unter Linux im Beispielordner starten:

```sh
./starten.sh
```

Das Skript öffnet FreeCAD mit dem Addon in einem vorher angelegten, eigenen Profil.
Es lädt die mitgelieferte Beispielbibliothek in dieses Profil, öffnet Maschine und
Job, prüft die Bahn und startet den Abspieler. Das Fenster erscheint auf dem zweiten
Bildschirm, sofern einer angeschlossen ist. Im Prüffenster kann man die Fahrt anhalten
und mit dem Schieber einzelne Stellungen ansehen. Nach dem Schließen wird das
temporäre Profil entfernt.

`g550_simultan.FCStd` lässt sich auch direkt öffnen und zeigt die gespeicherte Bahn.
Für das Abfahren mit den hier verwendeten Werkzeug- und Haltermaßen das Startskript
verwenden. Das Startskript setzt den Pfad der Maschine auf seinen aktuellen Speicherort.
Die mitgelieferte JSON-Datei gehört zum Beispiel; ein Import in die persönliche
Werkzeugverwaltung ist zum Ausprobieren nicht nötig.

## Teil und Aufspannung

- Block 80 × 60 × 30 mm mit Tasche: unten 40 × 24 mm, 20 mm tief, Ecken R 8,
  Wände mit 10° Formschräge nach außen.
- Rohteil ist bereits vorgefräst: 0,3 mm Aufmaß an den Wänden, fertiger Boden.
  Der Job enthält einen Schlichtumlauf an den acht Wandflächen.
- Eine angenäherte Winkelaufnahme am Rundtisch hält das Teil vor der waagerechten
  Spindel. Ihr Fuß, ihre Wand und das Rohteil sind bei der Kollisionsprüfung enthalten.
- Standardwerkzeug `werkzeuge.standardwerkzeug()`: VHM-Schaftfräser Ø 12 mm,
  vier Schneiden, Schneidenlänge 26 mm; Schlichten mit ae 0,3 mm, ap 25 mm,
  vc 85 m/min und fz 0,1 mm. Das ergibt etwa 2.255 U/min und 902 mm/min Vorschub.
- Für dieses Beispiel beträgt die Werkzeuggesamtlänge 70 mm. Der angenäherte gerade
  Halter ist 70 mm lang mit 28 mm Spanntiefe: gerechnet wird mit 112 mm ab Spindelnase.
  Deshalb zeigt das Prüffenster den Hinweis „Werkzeuglänge geschätzt“.

## Ergebnis der Modellprüfung

In FreeCAD 1.1.4 geprüft (2026-10-06):

| Ergebnis | Wert |
| --- | --- |
| Vorschubbewegungen, in denen X, Y, Z, A und B gleichzeitig ändern | 252 |
| Befehle der Bahn auf der Maschine | 299 |
| Simulationsstationen | 304 |
| A und B | jeweils −10° … +10° |
| Verfahrgrenzen überschritten | keine |
| Kollisionen oder Annäherungen unter 1 mm im Modell | keine |
| Rechnerische Fahrzeit | etwa 12 s, davon 10 s Vorschub und 2 s Eilgang |

Die Zählung vergleicht aufeinanderfolgende Vorschubsätze mit einer Schwelle von
0,00001 für jede Achse. `messung.json` enthält die Messwerte; ihre XYZ-Werte sind
Bahnkoordinaten in mm, keine MKS-Endlagen der Maschine. A/B sind Programmwinkel in Grad.
Ein probeweise ausgegebenes Siemens-Programm wurde vom vorhandenen Nachleser ohne
Befund gelesen; es ist kein Bestandteil dieses Beispiels.

Die Maschinenkörper, Aufnahme und Halterkontur sind angenähert. Die Prüfung bezieht
sich auf diese Modellgeometrie und die gespeicherte Aufspannung; ein NC-Programm wurde
an keiner echten G550 geprüft. Die Zeit ist eine Modellrechnung.

## Dateien

| Datei | Inhalt |
| --- | --- |
| `g550_simultan.FCStd` | Teil, vorgefrästes Rohteil, Werkzeugcontroller und Flankenoperation |
| `g550_winkelaufnahme.FCStd` | G550 mit Winkelaufnahme und ausgerichtetem Spannplatz |
| `beispiel_werkzeuge.json` | Werkzeug- und Haltermaße dieses Beispiels |
| `assets/Tools/` | CAM-Werkzeugdatei und Bibliotheksverweis |
| `anzeigen.FCMacro`, `starten.sh` | Laden und Prüfen im eigenen Profil |
| `messung.json` | Ergebnis der ursprünglichen Bahn- und Modellprüfung |

Bei einer flachen Aufspannung direkt auf dem Rundtisch wurden im ersten Versuch
Kollisionen auf der Rückfahrt und ein unpassender Hinweis zur Werkzeugrichtung
gefunden. Das bleibt als B-015 offen; diese Aufspannung ist hier nicht enthalten.
