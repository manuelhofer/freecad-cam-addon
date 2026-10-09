# Statische GUI-Gegenproben – Entwürfe vor echtem Laufbeleg

Status: **Beide Reparaturentwürfe liegen außerhalb des Repositorys. Die
Originalszenarien sind unverändert. Für Abfahren liegt inzwischen der echte
GUI-Fehlbeleg vor; für Schwenkteil steht er noch aus.**
Keine FreeCAD-Prozesse für diese Prüfung gestartet. Die Patches sind statisch
anwendbar geprüft. Vor Übernahme muss der laufende Inventarlauf abgeschlossen sein.

| Szenario | Belegter veralteter Vertrag | Kleinste fachliche Korrektur |
| --- | --- | --- |
| [Abfahren](/home/manuel/freecad_cam/freecad-cam-addon/tests/gui/szenario_abfahren.py:202) | Nach Nullpunkt X300 verlangt die Gegenprobe Spielerstationen, angehaltene Spielerachsen und eine Spielerspitze der unerreichbaren Operation. `Abspieler.zeige` setzt bei leerer Abfahrt die Spielerdaten zurück; `PruefPanel.fahre_hin` zeigt den Reichweitenbefund dann ausschließlich durch manuelles Verfahren. | Leere Operationen/Stationen, Auslassungsgrund und gesperrte Abspielknöpfe verlangen. Den tatsächlichen manuellen X1-Anschlag −250 und geometrischen Reichweitenbefund erhalten. Vor der positiven Schließenprüfung beide zulässigen Operationen wiederherstellen. [Patch](/home/manuel/freecad_cam/ergebnisse/abgabe-2026-10-09/szenario_abfahren-gate.patch). |
| [Schwenkteil](/home/manuel/freecad_cam/freecad-cam-addon/tests/gui/szenario_schwenkteil.py:202) | Der erwartete Satzteil „keine zwei Rundachsen“ kommt in aktuellen Produkttexten nicht mehr vor. Der aktuelle Hinweis verlangt eine lesbare tatsächliche Maschine und bezeichnet die Ebenen als unbearbeitet. | Die Gegenprobe entfernt vorübergehend alle gespeicherten Maschinenzuordnungen, liest den Dialog frisch und verlangt den aktuellen Hinweis, leere NC-Abschnitte der Ebenen und null Bewegungssätze. Im `finally` sämtliche Zuordnungen wiederherstellen; positive Prüfungen bleiben erhalten. [Patch](/home/manuel/freecad_cam/ergebnisse/abgabe-2026-10-09/szenario_schwenkteil-gate.patch). |

Der echte [Abfahren-Fehlbeleg](/home/manuel/freecad_cam/ergebnisse/abgabe-2026-10-09/gesamtstand-v4b/gui/szenario_abfahren/ergebnis.txt)
bestätigt zusätzlich den veralteten positiven Operationseinstieg: Bohren beginnt
bei „zum Werkzeugwechsel“, nicht sofort bei Quellsatz 3. Der erweiterte Patch
prüft exakt den Eintrittsindex der zweiten Operation, Ziel `WECHSEL`, Eilgang,
Operationsauswahl und die zugehörige Stationszeit. Die Anfahrt trifft X50/Y30;
weil T1 unverändert bleibt, wird kein tatsächlicher Werkzeugwechsel gezählt.
Danach wird der erste echte Quellsatz getrennt angefahren: weiterhin Satz 3 von 7,
Punkt (50,30,25) und seine genaue Stationszeit. Die übrigen positiven Geometrie-
und Zeitbehauptungen bleiben unverändert.

Quellnachweise:

- [Abspieler: leere Abfahrt, Daten zurücksetzen und Knöpfe sperren](/home/manuel/freecad_cam/freecad-cam-addon/camaddon/gui_abfahren.py:717).
- [Reichweitenbefund: manuelles Verfahren ohne passende Abspielstation](/home/manuel/freecad_cam/freecad-cam-addon/camaddon/gui_reichweite.py:737).
- [Operationswahl springt zum vollständigen Einstieg](/home/manuel/freecad_cam/freecad-cam-addon/camaddon/gui_abfahren.py:809).
- [Jede Bearbeitung fährt über den Werkzeugwechselpunkt an](/home/manuel/freecad_cam/freecad-cam-addon/camaddon/abfahren.py:354).
- [Aktueller Hinweis für fehlende Ebenenkinematik](/home/manuel/freecad_cam/freecad-cam-addon/translations/de.json:1966).
- [Programmfenster hängt den Hinweis an](/home/manuel/freecad_cam/freecad-cam-addon/camaddon/gui_programm.py:942).
- [Automatisches Lesen der tatsächlichen Jobzuordnung](/home/manuel/freecad_cam/freecad-cam-addon/camaddon/postprozessor.py:1505).
- [Ohne tatsächliche Ebenenmaschine keine NC-Freigabe](/home/manuel/freecad_cam/freecad-cam-addon/camaddon/postprozessor.py:1525).

Zusätzlicher Prüfhinweis, noch kein bestätigter Fehlbeleg: Schwenkteil Zeile181
verlangt fest `G0 A-30.000 C0.000`. Das andere Schwenkszenario leitet die Ausgabe
bereits aus der tatsächlichen Maschineninfo und ihrem DIN-Drehsinn ab. Bei einem
entsprechenden Laufbefund diese Erwartung ebenfalls maschinenbezogen bestimmen;
kein Vorzeichen ohne tatsächlichen Nachweis ersetzen.

Menü-/Werkzeugleisteninventar: aktuelle Definitionen enthalten zwölf Arbeitsknöpfe
und sechzehn Menübefehle ohne Trennstriche; `szenario_erster_start.py` ist inzwischen
entsprechend angepasst. Bei den untersuchten festen/einachsigen Maschinenfällen
werden echte Null-/Ein-Achs-Kinematiken bereits ausdrücklich geprüft.
