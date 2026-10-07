# Freiform auf der G550: Werkzeug, Bahn und Anstellung vergleichen

Der Job beginnt mit einem Quader 50 × 40 × 30 mm. Sein Sollteil hat eine interpolierte
B-Spline-Fläche mit Mulde, Sattel und Erhebung. D12 schruppt mit 5 mm Zustellung,
ae 1,5 mm und 0,3 mm Aufmaß. Danach schlichtet eine angestellte Kugel die Fläche
einschließlich eines genauen Randgangs; gewünschte Grathöhe 0,02 mm.

## Öffnen

Unter Linux im Beispielordner `./starten.sh` starten. Das öffnet Maschine und Job in
einem vorher angelegten eigenen FreeCAD-Profil auf dem zweiten Bildschirm, prüft die
gespeicherte Bahn und zeigt eine Stellung beim Schlichten. Die mitgelieferte Bibliothek
wird ausschließlich in diesem Profil geladen. Sie muss nicht in die persönliche
Werkzeugverwaltung importiert werden.

Im geöffneten Prüffenster die Fahrt anhalten und mit dem Schieber ansehen. Zum erneuten
Vergleichen das Prüffenster schließen, im Baum **3D-Schlichten T4** auswählen und
**CAM-Addon → 5-Achs-Schlichten vergleichen …** öffnen. Die Operation hat ihre Maschine
bereits zugewiesen. Der Vergleich verändert sie erst mit **Übernehmen**; Strg+Z stellt
die vorherige Einstellung wieder her.

Die FCStd-Dateien lassen sich auch direkt öffnen. Für das genaue Abfahren mit diesen
Werkzeug- und Haltermaßen das Startskript verwenden. Es setzt den Maschinenpfad auf
den aktuellen Speicherort. Der Erzeuger `erstellen.py` dient zum Nachbauen in einem
ausdrücklich eingerichteten Testprofil; er läuft beim Import nicht automatisch.

## Vergleich am 2026-10-07, FreeCAD 1.1.4

45 Kombinationen: Kugeln Ø 12/6/4 aus den Standard-Schnittwerten, fünf Bahnrichtungen,
Anstellung um X, um Y oder frei mit beiden Kippkomponenten. Die größeren Kugeln erreichen
hier einen Flächenrand nicht ohne Verletzung einer Gegenfläche. Mehrere Anstellungen
verfehlen den Mindestkontaktwinkel auch zwischen Bahnpunkten und werden abgewiesen.

| Ergebnis | Wert |
| --- | --- |
| Schnellste zugelassene Variante dieser Auswahl | Kugel Ø 4, Zeilen X, Richtung frei |
| Gesamter Job, rechnerisch | 581,34 s, etwa 9 min 41 s |
| Größte Restprobe, 19 × 19 Parameterproben auf der Fläche | 0,0298 mm |
| Kleinster geprüfter Kontaktwinkel | 16,03° bei verlangten 15° |
| Simulationsstationen, ganzer Job | 14.721 |
| Befehle beim Schlichten auf der Maschine | 12.260 |
| Schlichtbewegungen mit X/Y/Z/A/B gemeinsam | 167 |
| Verfahrgrenzen, genaue Modellkollision und Warnabstand 1 mm | ohne Befund |

Die Zeit enthält Schruppen, Schlichten und Übergänge auf der Maschinenkinematik.
Langsamere Kandidaten sind in `vergleich.json` ausdrücklich als noch nicht auf Kollision
geprüft gekennzeichnet; sie können die bereits geprüfte schnellere Variante nicht gewinnen.

Der gerade Halter ist angenähert: 70 mm Länge, 28 mm Spanntiefe; Werkzeuggesamtlänge
85 mm, daher 127 mm Länge ab Spindelnase geschätzt. Die Werkzeuggeometrien und Standardwerte
sind Beispieldaten. Die Maschine und Winkelaufnahme sind ebenfalls angenähert.

## Was dieses Ergebnis belegt

Ein vollständiger Job von diesem Quader bis zur gewählten, von oben erreichbaren
Freiformfläche wird gerechnet und auf dem Modell geprüft. Ein großer Fräser wird
begründet ausgeschlossen; die Maschinenzeit entscheidet zwischen zugelassenen Bahnen.

Die Oberflächenprüfung sind Stichproben mit Grathöhe + Aufmaß + 0,05 mm
Rechentoleranz als Zulassungsgrenze; sie ist keine vollständige Abtragsvermessung.
Eine global optimale Lösung für beliebige komplexe Teile, Hinterschnitte oder automatisch
geplante weitere Aufspannungen ist damit nicht nachgewiesen. Ein Programm wurde an keiner
echten G550 ausgeführt.

## Dateien

- `freiform_5achs.FCStd`: Teil, Quader, Schruppen, geprüfte Schlichtoperation und Werkzeuge.
- `g550_winkelaufnahme.FCStd`: korrigierte G550 mit Winkelaufnahme und Spannplatz.
- `vergleich.json`: alle Varianten, Ablehnungsgründe, Zeiten und Prüfstatus.
- `beispiel_werkzeuge.json`, `assets/Tools/`: Maße, Schnittwerte und CAM-Werkzeugdateien.
- `erstellen.py`: Erzeuger des Teils und Ausgangsjobs mit drei Kugelfräsern zur Auswahl.
- `starten.sh`, `anzeigen.FCMacro`: Öffnen und Prüfen im eigenen Profil.
