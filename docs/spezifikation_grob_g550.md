# Beispielmaschine: GROB G550

Manuels Wunsch vom 2026-10-06: eine weitere Beispielmaschine, grob nach Form und
Bewegungsmöglichkeiten einer G550, mit waagerechter Spindel. **Dritter Bau (P-2026-10-11-91)**
nach der Kinematik der GROB G-Serie, nachdem Manuel den zweiten verwarf (2026-10-11: „so schaut
die grob nicht aus .. da ist nur ein ständer an dem der tisch befestigt ist ... also die
kinematik ist komplett daneben ... die spindel fährt glaub ich nur eine richtung der tisch fährt
hoch runter und schwenken … mach das richtig !“). Der erste Bau (2026-10-06) hatte die Achsen
schon so verteilt, aber keinen Spindelschacht; der zweite (P-2026-10-10-19) setzte alle drei
Linearachsen an die Spindel und den Tisch zwischen zwei Lagerböcke – beides falsch gelesen.

## Aufbau und Bedienung

Die offene Baugruppe zeigt die Bewegung mit Quadern und Zylindern:

```text
Bett ── X (X-Schlitten mit Spindelschacht, seitlich) ── Z (Spindelstock im Schacht) ── Spindel S1
  └── Säule (fest) ── Y (Y-Schlitten, hoch/runter) ── A (Schwenkeinheit, einseitig, um X)
                                                        └── B (Rundtisch) ── Spannplatz
```

Die Spindel fährt nur X und Z. Ihr Schacht (innen x 1260 … 1540, z 1160 … 1440, Front bei
y 1000) sitzt auf dem X-Schlitten; bei Z ganz zurück (+485) steht die Spindelnase 85 mm hinter
der Schachtfront (GROB: „die Motorspindel samt Werkzeug kann sich vollständig in den
Spindelschacht zurückziehen“). Die Säule steht links vom Tisch (x 300 … 700); an ihrer Front
fährt der Y-Schlitten ±510 mm, an ihm das Gehäuse der Schwenkeinheit, daraus ragt die A-Achse
längs +X (y 1900, z 1300); der Tisch (Ø 770, Spannfläche 50 über der A-Achse, Mitte x 1400)
hängt frei daran und schwenkt im Störkreis Ø 900 (Herstellerangabe), ohne Säule, Gehäuse oder
Bett zu berühren. Y fährt das Werkstück: Plus senkt den Tisch, relativ dazu fährt das Werkzeug
nach oben (+Y nach DIN, wie der Kreuztisch der 3-Achs-Fräse) – so bleiben X, Y, Z rechtshändig
und A, B zählen wie an der Steuerung.

Im Fenster „Neue Maschine …“ steht die Zeile „GROB G550 – horizontal (A/B)“. Darunter bleiben
die vorhandenen Felder für Name, Verfahrwege, Schwenkbereich A und Spindeldrehzahl. B dreht
endlos. In Stellung A = 0 ist der Tisch waagerecht; A = −90 stellt seine Spannfläche zur
Spindel. Die Achsen werden wie die übrigen Beispiele nach DIN 66217 angezeigt.

**Akzeptanzkriterium:** „Neue Maschine …“ → GROB G550 → Bauen → „Maschine verfahren“:
X bewegt die Spindel seitlich, Z vor/zurück – ganz zurück in ihren Schacht –, Y hebt und senkt
den Tisch an der Säule, A/B schwenken bzw. drehen ihn innerhalb der eingetragenen Grenzen;
in keiner Endlage stößt ein Maschinenteil an ein anderes.

## Quellen und Grenzen des Beispiels

- [GROB G550, Herstellerseite](https://www.grobgroup.com/produkte/produktbereiche/universalmaschinen/fraes-bearbeitungszentren/g550/),
  gelesen 2026-10-06: Wege X/Y/Z 800/1.020/970 mm, Eilgang 65/50/80 m/min,
  Tischdurchmesser 770 mm; waagerechte Spindel, Rundachsen A/B.
- [GROB-Achsanordnung, Herstellerzeichnung zur gleichen Bauart](https://www.grobgroup.com/en/products/product-range/universal-machining-centers/milling-centers/g550a/),
  Abschnitt „Axis arrangement“, gelesen 2026-10-06 und wieder 2026-10-11 (Bild
  `csm_Achsanordnung_G350a`): eine Säule mit Y′, daran einseitig A′ mit B′; die Spindel auf X
  und Z. Die G550a hat andere Verfahrwege.
- GROB-Broschüren der G-Serie (G550/G750, G350 Generation 2), gefunden 2026-10-11: „X- und
  Z-Achse auf der Werkzeugseite, Y-Achse und A/B-Achse werkstückseitig, auskragend“, „Da die
  Spindel ausschließlich in X- und Z-Achse bewegt wird …“, „Tunnel-Konzept: Motorspindel und
  Werkzeug können sich vollständig in den Spindelschacht zurückziehen“, „zwei symmetrisch
  angeordnete Kugelgewindetriebe … in der Y′-Achse“.
- [GROB G550, Herstellerseite „Einzigartiges Maschinenkonzept“](https://www.grobgroup.com/produkte/produktbereiche/universalmaschinen/fraes-bearbeitungszentren/g550/),
  gelesen 2026-10-10: „Die einzigartige Anordnung der drei Linearachsen ergibt einen geringen
  Abstand der Führungen vom Arbeitspunkt“, „Tunnel-Konzept … kollisionsfrei schwenken“,
  Störkreisdurchmesser 900 mm, A 230°, B 360°. „Die einzigartige Anordnung der drei
  Linearachsen“ hatte P-2026-10-10-19 als „alle drei an der Spindel“ gelesen – falsch.
- [GROB-Broschüre G350/G550 Generation 2 und G750](https://www.simusrl.com/simudemo/wp-content/uploads/2018/07/GROB_brochure_G352_G552_G751.pdf),
  Herstellerbroschüre bei einem Händler, gelesen 2026-10-06, Seite 11:
  G550 A −185 … +45°, B endlos, A 25 U/min und B 50 U/min.

Die Körpermaße und Abstände zum Drehpunkt sind angenähert. Die linearen Wege werden für das
Beispiel um die gebaute Stellung 0 verteilt; sie sind keine belegten MKS-Endlagen einer
konkreten Maschine. Die Spindel ist mit der angebotenen HSK-A63-Variante 16.000 U/min vorbelegt.
Beschleunigungen und Hochlaufzeit bleiben unbekannt. Die Vorlage ist zum Erklären und
Ausprobieren gedacht; eine konkrete Maschine braucht ihre tatsächlichen Maße und Kenndaten.

## Beispieljob: fünf Achsen simultan

Manuel, 2026-10-06: „nun kannst du gerne versuchen noch 5 achs simultan werkzeugwege
zu erstellen“. Dafür liegt unter `beispiele/grob_g550_simultan/` ein fertiger Job:
D12 schlichtet acht Wände mit 10° Formschräge an einer vorgefrästen Tasche auf einer
Winkelaufnahme. Die vorhandene Flankenstrategie und der Simultankern rechnen die Bahn;
es wurde kein zweiter Bahnalgorithmus eingeführt.

**Akzeptanzkriterium:** `beispiele/grob_g550_simultan/starten.sh` starten → das Prüffenster
zeigt auf dem zweiten Bildschirm die G550 mit dem Job und ohne Kollisionen oder
Grenzüberschreitungen, und beim Abfahren bewegen sich X/Y/Z/A/B gemeinsam.

252 Vorschubbewegungen ändern alle fünf Achsen gleichzeitig; A/B laufen je zwischen
−10° und +10°. 304 Simulationsstationen, keine Modellkollision, keine Annäherung unter
1 mm und keine überschrittene Achsgrenze; rechnerisch etwa 12 s. Werkzeuglänge 112 mm
aus angenähertem Halter und Werkzeug geschätzt. Aufbau, Maße, Öffnen und Grenzen der
Prüfung stehen in [der Beispielbeschreibung](../beispiele/grob_g550_simultan/README.md).

**B-015, offen:** Beim ersten Versuch mit einer flachen Tasche direkt auf dem Rundtisch
traten auf der Rückfahrt Kontakte zwischen Spindelseite/Wiege und Tisch auf. Die Bahn
schwenkte A auf eine konstante Stellung, während B drehte; damit bewegten sich nicht
alle fünf Achsen gemeinsam. Außerdem wurde eine quer zur Spindel stehende Werkzeugrichtung
gemeldet, obwohl sich die Simultanrichtung während der Bahn ändert. Sichere Rückfahrt
und Richtungsprüfung für diese waagerechte Maschinenanordnung gesondert untersuchen;
der gespeicherte Job nutzt die geprüfte Winkelaufnahme.
