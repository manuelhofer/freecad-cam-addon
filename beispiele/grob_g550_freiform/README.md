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

Im geöffneten Prüffenster die Fahrt abspielen oder mit dem Schieber ansehen. Zum erneuten
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
| Schnellste zugelassene Variante dieser Auswahl | Kugel Ø 4, entlang der Fläche, Richtung frei |
| Gesamter Job, rechnerisch | 682,84 s, etwa 11 min 23 s |
| Restgrenze einschließlich Vernetzungsunsicherheit | 0,01694 mm bei verlangten 0,02 mm |
| Nachgelesene NC-Bahn einschließlich Vernetzungs-, Rundungs- und Glättungsreserve | 0,01705 mm bei verlangten 0,02 mm |
| Vollständig abgedeckte Flächenzellen | 550.457, keine offene Zelle |
| Kleinster geprüfter Kontaktwinkel | 16,82° bei verlangten 15° |
| Größte gemittelte Last beim Schlichten | 2,756 mm² bei erlaubten ae × ap = 7,5 mm² |
| Bewegungen im nachgelesenen Siemens-Programm | 54.082, kein NC-Befund |
| Verfahrgrenzen, Modellkollision und Warnabstand 1 mm | ohne Befund |
| Berechnen und Prüfen aller 45 Varianten | 20 min 15 s; nativer Prozess-Spitzenspeicher 3,65 GiB |

Die Zeit des Jobs enthält Schruppen, Schlichten und Übergänge auf der Maschinenkinematik.
Die Rechenzeit ist die Zeit für den Vergleich und seine Qualitätsprüfungen auf Manuels Rechner.
Der Bericht `vergleich.json` enthält jede Ablehnung und den Prüfstatus. Die frühere Wahl
„Zeilen X“ erreicht die verlangte Flächenabdeckung nicht und ist ersetzt.

Der gerade Halter ist angenähert: 70 mm Länge, 28 mm Spanntiefe; Werkzeuggesamtlänge
85 mm, daher 127 mm Länge ab Spindelnase geschätzt. Werkzeuggeometrien, Schnittwerte,
Maschine und Winkelaufnahme sind Beispieldaten.

## Was dieses Ergebnis belegt

Die unabhängige Materialprüfung beginnt am Quader und fährt das D12-Schruppen ab. Die
Schruppbahn fährt mit einer Rampe ein; die zulässigen 3° und die Last aus dem Einsatz gelten.
Danach werden kontinuierliche Kugelschnitte, ganze Flächenzellen einschließlich der Ränder,
BRep-Abstand, Kontaktwinkel, die tatsächlichen Maschinenstellungen und Kollisionen geprüft.
Das Materialraster hat 0,1 mm; der Referenztest prüft zusätzlich mit 0,05 mm. Die unabhängige
Vernetzung hat höchstens 0,001 mm Deflektion und verbraucht einen Teil des Qualitätsbudgets.
Die Zulassungsgrenze bleibt Grathöhe plus Aufmaß.
Die fein geprüfte Schlichtbahn verwendet sechs Koordinatenstellen. Die Siemens-Ausgabe
setzt `CTOL=0.000100`; 0,00011 mm des Qualitätsbudgets sind für Rundung und Glättung
reserviert. Der Rücklesetest fährt die tatsächlich geschriebenen Achswerte mit ACP/ACN
nach: kein Eilgang- oder Freivorschubabtrag, kein kompletter Luftzug, keine offene Zelle
und eine konservative BRep-Abstandsuntergrenze von 0,000383 mm.

`tests/test_simultan_planung.py` prüft die gespeicherten Punkte, Werkzeugachsen und
Maschinenbefehle gegen `tests/golden/freiform_simultan.json`, die Zeitbestmarke und Budgets
für Rechenzeit und Python-Spitzenspeicher. Die Referenz hält sechs Nachkommastellen fest;
der Vergleich zwischen geprüfter und neu berechneter Bahn toleriert weniger als 1 µm.
Der gemessene Vergleich mit Speicherinstrumentierung hat 1.220,90 s und 401,89 MiB
Python-Spitzenspeicher als Ausgangswerte, die Budgets betragen jeweils das Doppelte.
Die Zeitbestmarke erlaubt höchstens 0,5 % mehr Maschinenzeit. Den Referenztest mit
`SIMULTAN_SPEICHER_MESSEN=1` in einem vorher angelegten eigenen `FREECAD_USER_HOME`
ausführen, um auch das Speicherbudget zu prüfen; `GOLDENE_BAHNEN_SCHREIBEN` bleibt dabei
ungesetzt. Zum beabsichtigten Neuschreiben muss diese Variable ausdrücklich `1` sein;
die Referenz wird erst nach sämtlichen Qualitätsprüfungen gespeichert.
Der anschließende Vergleich ohne Schreibflag bestand mit 1.242,78 s und 401,884 MiB;
mit der abschließenden NC-Reserve dauerte der Vergleich ohne Speicherinstrumentierung
754,81 s. `tests/test_simultan_nc.py` prüft zusätzlich den vollständigen Siemens-Programmtext
gegen `tests/golden/freiform_simultan_nc.json` und dessen gelesene Geometrie gegen Material
und BRep. Auch diese Referenz wurde anschließend ohne Schreibflag erfolgreich verglichen.
Der Oberflächentest rechnet, übernimmt und macht
die Änderung mit Strg+Z rückgängig. Die persönlichen Werkzeugdateien bleiben außerhalb der
Testprofile.

Unterstützt sind von oben erreichbare Flächen in Quaderrohteil mit senkrechter Vorbearbeitung
und dem Schlichten als letzter aktiver Operation. Hinterschnitte, automatisch geplante weitere
Aufspannungen und globale Optimalität für beliebige Teile sind offen. Das Ergebnis gilt für
die angebotenen Varianten und die eingerichteten Modellmaße. Das Programm wurde an keiner
echten G550 ausgeführt.

## Dateien

- `freiform_5achs.FCStd`: Teil, Quader, Schruppen, geprüfte Schlichtoperation und Werkzeuge.
- `g550_winkelaufnahme.FCStd`: korrigierte G550 mit Winkelaufnahme und Spannplatz.
- `vergleich.json`: alle Varianten, Ablehnungsgründe, Zeiten und Prüfstatus.
- `beispiel_werkzeuge.json`, `assets/Tools/`: Maße, Schnittwerte und CAM-Werkzeugdateien.
- `freiform_5achs.mpf`: nachgelesenes Siemens-Beispielprogramm.
- `nc_pruefung.json`: Textreferenz und Material-/BRep-Ergebnis der geschriebenen NC-Bahn.
- `pruefen.py`: vollständiger Vergleich, Prüfung und erneutes Speichern im eigenen Profil.
- `erstellen.py`: Erzeuger des Teils und Ausgangsjobs mit drei Kugelfräsern zur Auswahl.
- `starten.sh`, `anzeigen.FCMacro`: Öffnen und Prüfen im eigenen Profil.
