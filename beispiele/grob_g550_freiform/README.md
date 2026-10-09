# Freiform auf der G550: Schruppen und 5-Achs-Schlichten

Der Job beginnt mit einem Quader 50 × 40 × 30 mm. Sein Sollteil hat eine
B-Spline-Fläche mit Mulde, Sattel und Erhebung. Der Standardfräser Ø 12 schruppt
mit ap 25 mm, ae 1,5 mm, 3,5-mm-Zwischenlagen und 0,3 mm Aufmaß. Eine angestellte
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

Im Vergleich lässt sich jetzt **Schruppen mit vergleichen** wählen. Bereich und Schritt
legen die Schrupp-Zwischenlagen fest; die aktuelle Einstellung kommt zusätzlich dazu.
Jeder Zweig rechnet das anschließende Schlichten aus seinem tatsächlichen Restmaterial.
Die Jobzeit entscheidet über beide Operationen. **Geprüfte Folge übernehmen** setzt
beide gemeinsam; Strg+Z nimmt beide zurück. Für eine feste Vorbearbeitung den Haken lösen.
Die Auswahl bleibt auf den angegebenen Bereich und die eingerichteten Werkzeuge/Bahnen
begrenzt; zusätzliche Aufspannungen sind weiterhin offen.

Am Ende erscheint derselbe farbige Rohteil-/Sollteil-Vergleich wie bei 4 Achsen.
**Teil** blendet das graue Sollteil aus; Zurückspulen stellt das Rohteil wieder
her. Die Vorschau hat 0,5 mm Raster; für die genaue Grenze gelten die folgenden
feineren Material-, Flächen- und NC-Prüfungen.

## Gemeinsame Gesamtplanung, P-2026-10-08-04

Die frühere Folge mit ap 5 mm und 1-mm-Zwischenlagen war trotz Referenzprüfung
zu aufwendig: 82 getrennte Schnittzüge, 8,28 min Schruppen und rund 31 % Luft im
normalen Vorschub. P-2026-10-08-01 verglich die gefahrenen Schruppbahnen einschließlich
Rampen und freier Verbindungen; 3-mm-Zwischenlagen verkürzten den Job auf 5 min 57,5 s.

Der neue gemeinsame Vergleich (P-2026-10-08-03) rechnet Schruppen und Schlichten
für jeden angebotenen Materialzweig zusammen. 2,5/3/3,5/4 mm wurden mit dem
Standardfräser und beiden freien Anstellungen entlang der Fläche verglichen.
**3,5 mm gewinnt mit 5 min 16,6 s.** Das Schlichten übernimmt rund 837 mm³ mehr
Restmaterial, hält aber seine Lastgrenze. 2,5 mm kostet 6 min 20,8 s; 4 mm wird
wegen Schrupplast 46,72 statt höchstens 37,5 mm² abgewiesen.

| Gemessener Modellwert | Neuer Stand |
| --- | --- |
| Gesamter Job | 316,63 s – 5 min 16,6 s statt zuletzt 5 min 57,5 s; ursprünglich 11 min 23 s |
| Schruppen | 2,16 statt zuletzt 2,86 min; ursprünglich 8,28 min |
| Luft im normalen Schruppvorschub | 14,82 % im 0,1-mm-Prüfraster |
| Schrupp-/Schlichtlast | 37,43 / 6,82 mm² bei Grenzen 37,5 / 7,5 mm² |
| Schrupplast im feineren 0,05-mm-Raster | 37,3222 mm² unter 37,5 mm² |
| Restgrenze einschließlich Vernetzungsunsicherheit | 0,01694 mm bei erlaubten 0,02 mm |
| Geschriebene NC-Bahn samt Rundungs-/Glättungsreserve | 0,01705 mm bei erlaubten 0,02 mm |
| Abgedeckte Flächenzellen | 550.457, keine offene Zelle |
| Modellkollision, Verfahrgrenzen, Eintritt und schneller Abtrag | ohne Befund |
| NC-Bewegungen | 45.682, exakter frischer Export gegen Referenz geprüft |
| Vorausschauende Qualitätsprüfung mit Speicherinstrumentierung | 1066,58 s; 401,22 MiB Python-Spitze |

Alle 60 Kombinationen aus drei Kugelfräsern, fünf Bahnrichtungen und vier
Anstellungen wurden am neuen 3,5-mm-Materialstand verglichen. Die schnellste
zugelassene Variante bleibt **Ø 4, entlang der Fläche, Frei – ganze Bahn**; sie ist
0,54 s schneller als die ebenfalls vollständig qualifizierte örtliche Folge.
Größere Kugeln scheitern am Flächenrand; andere Richtungen u. a. an Rest,
Kontaktwinkel oder Last. Der vollständige Vergleich dauerte 982,09 s, der gemeinsame
Vergleich der vier Materialzweige 1477,59 s. Die vorherigen Berichte und Referenzen
liegen im lokalen Prüfarchiv.

Seit 0.203.5 (P-2026-10-09-04) rechnet das Addon ohne den Haken „Alle Kombinationen
vergleichen“ nur die sinnvollen Varianten: die größte Kugel zuerst, entlang der Fläche,
Frei und Frei – ganze Bahn; wird nichts zugelassen, die übrigen Richtungen, dann die festen
Anstellungen, dann die nächste kleinere Kugel.
Am Beispiel sind das zwei Abweisungen am Flächenrand (Ø 12, Ø 6) und zwei gerechnete
Ø-4-Varianten mit demselben Gewinner. `pruefen.py` rechnet mit `ALLE_KOMBINATIONEN=1`
weiterhin alle 60.

## Was geprüft wurde

Der Prüfer fährt vom Quader über das Schruppen bis zum fertigen Teil. Er prüft
kontinuierliche Werkzeugbewegungen, Last, Eintritt, Rampen, Luft, Eil-/Freivorschub,
ganze Flächenzellen, Kontaktwinkel, BRep-Abstand und Maschinenkollision. Das Materialraster
0,1 mm wurde zusätzlich mit 0,05 mm geprüft. Die Vernetzungsunsicherheit verbraucht
Qualitätsbudget. Der NC-Test liest die geschriebenen Achswerte mit ACP/ACN zurück;
sechs Koordinatenstellen und `CTOL=0.000100` halten die reservierte Grenze ein.
Die BRep-Untergrenze ist 0,00038270 mm bei reservierten 0,00036 mm.

Die frühere NC-Abweichung war ein Fehler des Prüfaufbaus: Seine Variantenansicht
hatte noch keinen zugeordneten Rohteil und ließ drei sichere An-/Rückzugsbewegungen
weg. Jetzt sind geprüfter und tatsächlicher Export identisch; beide Richtungsfolgen
wurden aus einem frischen Prozess ohne Schreibflag gegen ihre NC-Referenz verglichen.

`tests/test_schruppen3d_anlauf.py` schützt den Anlaufvergleich und die Schruppbestmarke.
`test_simultan_planung.py` prüft Punkte, Achsen, Befehle, Zeit und Qualitätsbudget
einschließlich der Vorbearbeitung im feineren Raster – seit P-2026-10-09-10 an der kleinen
Kuppel (`erstellen.py`, Form KUPPEL); das Beispiel selbst rechnet es mit
`SIMULTAN_TEST_FORM=freiform` (von Hand, 30 Minuten und mehr), wie `pruefen.py`;
`test_simultan_nc.py` prüft die geschriebene Geometrie und den echten Export des Beispiels.
`test_simultan_export_referenz.py` wiederholt nur den frischen exakten Exportvergleich.
`test_simultan_folge.py` schützt die gemeinsame Auswahl, Eingabeschutz, Abbruch,
Rollback und ein Undo für beide Operationen. Goldene Referenzen sichern Wiederholbarkeit;
sie beweisen keine allgemeine optimale Strategie.

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
- `erstellen.py`, `pruefen.py`: nachbauen bzw. die sinnvollen Varianten vergleichen
  (`ALLE_KOMBINATIONEN=1`: alle 60).
- `starten.sh`, `anzeigen.FCMacro`: im eigenen Profil öffnen.
