# Freiform auf der G550: Schruppen und 5-Achs-Schlichten

Der Job beginnt mit einem Quader 50 × 40 × 30 mm. Sein Sollteil hat eine
B-Spline-Fläche mit Mulde, Sattel und Erhebung. Der Standardfräser Ø 12 schruppt
mit ap 25 mm, ae 1,5 mm, 3-mm-Zwischenlagen und 0,3 mm Aufmaß. Eine angestellte
Kugel Ø 4 schlichtet anschließend die Fläche samt Randgang auf 0,02 mm Grathöhe.

## Öffnen

Unter Linux im Beispielordner `./starten.sh` starten. Das öffnet Maschine und
Job im eigenen, vorher angelegten FreeCAD-Profil auf dem zweiten Bildschirm.
Die Beispielbibliothek wird ausschließlich dort gespeichert. Geöffnet werden eigene
Kopien von Maschine, Job und Assets; die gespeicherte Maschinenstellung bleibt erhalten.
Das temporäre Profil wird beim Schließen gelöscht. Eigene Jobänderungen daher mit
**Speichern unter …** außerhalb dieses Profils sichern. Falls nötig wählt
`CAMADDON_GROB_BILDSCHIRM=DP-1 ./starten.sh` eine Anzeige ausdrücklich; unter Linux
wird sonst die tatsächliche zweite Anzeige ermittelt.

Im Prüffenster abspielen oder den Schieber bewegen. **Bahn** zeigt die ausgewählte
bzw. gerade laufende Operation; beim Werkzeug-/Operationswechsel folgt die Bahn.
Die Lupe umfasst Werkstück und Werkzeug ohne entfernte Home-/Wechselwege; am Ende
den farbigen Werkstückvergleich. Zum Vergleichen das Fenster
schließen, **3D-Schlichten T4** auswählen und **CAM-Addon → 5-Achs-Schlichten
vergleichen …** öffnen. **Übernehmen** übernimmt die geprüfte Auswahl, Strg+Z
stellt die vorherige Einstellung wieder her.

Am Ende erscheint derselbe farbige Rohteil-/Sollteil-Vergleich wie bei 4 Achsen.
**Teil** blendet das graue Sollteil aus; Zurückspulen stellt das Rohteil wieder
her. Die Vorschau hat 0,5 mm Raster; für die genaue Grenze gelten die folgenden
feineren Material-, Flächen- und NC-Prüfungen.

## Korrektur nach Manuels Bahnkritik, P-2026-10-08-01

Die frühere Folge mit ap 5 mm und 1-mm-Zwischenlagen war trotz Referenzprüfung
zu aufwendig: 82 getrennte Schnittzüge, 8,28 min Schruppen und rund 31 % Luft im
normalen Vorschub. Jetzt wird die Variantenzeit nach Rampen und freien Verbindungen
verglichen. Bereits geräumte Stellen brauchen keine zusätzliche Minirampe.

1/2/3/4-mm-Zwischenlagen wurden mit dem Standardfräser untersucht. 3 mm hält die
Last beider Fräser; 4 mm überlastet sie. Die Schlichtanfahrten wurden für den größeren
Rest neu berechnet. Vollständige Ringe und der Adaptiv-Versuch wurden verworfen,
weil sie langsamer waren bzw. im Freivorschub Material abtrugen.

| Gemessener Modellwert | Neuer Stand |
| --- | --- |
| Gesamter Job | 357,52 s – 5 min 57,5 s statt 11 min 23 s |
| Schruppen | 2,86 statt 8,28 min; 28 statt 82 Schnittzüge |
| Luft im normalen Schruppvorschub | 15,38 % im 0,1-mm-Prüfraster |
| Schrupp-/Schlichtlast | 31,15 / 4,57 mm² bei Grenzen 37,5 / 7,5 mm² |
| Restgrenze einschließlich Vernetzungsunsicherheit | 0,01694 mm bei erlaubten 0,02 mm |
| Geschriebene NC-Bahn samt Rundungs-/Glättungsreserve | 0,01705 mm bei erlaubten 0,02 mm |
| Abgedeckte Flächenzellen | 550.457, keine offene Zelle |
| Modellkollision, Verfahrgrenzen, Eintritt und schneller Abtrag | ohne Befund |
| NC-Bewegungen | 46.599, exakter frischer Export gegen Referenz geprüft |
| Vorausschauende Planung mit Speicherinstrumentierung | 1111,21 s; 401,26 MiB Python-Spitze |

Alle 60 aktuellen Kombinationen aus drei Kugelfräsern, fünf Bahnrichtungen und
vier Anstellungen wurden am neuen Materialstand verglichen. Die schnellste zugelassene
Variante bleibt **Ø 4, entlang der Fläche, Frei – ganze Bahn**; sie ist 0,55 s
schneller als die ebenfalls vollständig qualifizierte örtliche Folge. Größere Kugeln
scheitern am Flächenrand; andere Richtungen u. a. an Rest, Kontaktwinkel oder Last.
Der vollständige Vergleich dauerte 1060,40 s. Der frühere Bericht mit 45 Kombinationen
gehört zur alten Schruppfolge und liegt im lokalen Prüfarchiv.

## Was geprüft wurde

Der Prüfer fährt vom Quader über das Schruppen bis zum fertigen Teil. Er prüft
kontinuierliche Werkzeugbewegungen, Last, Eintritt, Rampen, Luft, Eil-/Freivorschub,
ganze Flächenzellen, Kontaktwinkel, BRep-Abstand und Maschinenkollision. Das Materialraster
0,1 mm wurde zusätzlich mit 0,05 mm geprüft. Die Vernetzungsunsicherheit verbraucht
Qualitätsbudget. Der NC-Test liest die geschriebenen Achswerte mit ACP/ACN zurück;
sechs Koordinatenstellen und `CTOL=0.000100` halten die reservierte Grenze ein.
Die BRep-Untergrenze ist 0,00038208 mm bei reservierten 0,00036 mm.

Die frühere NC-Abweichung war ein Fehler des Prüfaufbaus: Seine Variantenansicht
hatte noch keinen zugeordneten Rohteil und ließ drei sichere An-/Rückzugsbewegungen
weg. Jetzt sind geprüfter und tatsächlicher Export identisch; beide Richtungsfolgen
wurden aus einem frischen Prozess ohne Schreibflag gegen ihre NC-Referenz verglichen.

`tests/test_schruppen3d_anlauf.py` schützt den Anlaufvergleich und die Schruppbestmarke.
`test_simultan_planung.py` prüft Punkte, Achsen, Befehle, Zeit und Qualitätsbudget;
`test_simultan_nc.py` prüft die geschriebene Geometrie und den echten Export.
`test_simultan_export_referenz.py` wiederholt nur den frischen exakten Exportvergleich.
Goldene Referenzen sichern Wiederholbarkeit; sie beweisen keine allgemeine optimale Strategie.

Unterstützt sind von oben erreichbare Flächen im Quader mit senkrechter Vorbearbeitung.
Hinterschnitte, automatische weitere Aufspannungen und globale Optimalität beliebiger
Teile bleiben offen. Der Halter und die Werkzeuglängen sind Beispieldaten; das Programm
wurde an keiner echten G550 ausgeführt.

## Dateien

- `freiform_5achs.FCStd`: neuer Job mit der geprüften ganzen Richtungsfolge.
- `g550_winkelaufnahme.FCStd`: G550 und Winkelaufnahme; Manuels gespeicherte Ansicht erhalten.
- `vergleich.json`: aktuelle Auswahl und Material-/Zeitbefunde.
- `freiform_5achs.mpf`, `nc_pruefung.json`: tatsächlicher Export und sein Prüfbericht.
- `beispiel_werkzeuge.json`, `assets/`: Werkzeug- und Halterdaten.
- `erstellen.py`, `pruefen.py`: nachbauen bzw. alle aktuellen Varianten vergleichen.
- `starten.sh`, `anzeigen.FCMacro`: im eigenen Profil öffnen.
