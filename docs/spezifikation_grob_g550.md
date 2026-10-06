# Beispielmaschine: GROB G550

Manuels Wunsch vom 2026-10-06: eine weitere Beispielmaschine, grob nach Form und
Bewegungsmöglichkeiten einer G550, mit waagerechter Spindel und hebbarem Tisch.

## Aufbau und Bedienung

Die offene Baugruppe zeigt die Bewegung mit Quadern und Zylindern:

```text
Bett ── X (seitlich) ── Spindelschlitten ── Z (waagerecht) ── Spindel S1
  └── Tischständer ── Y (hoch/runter) ── A (schwenken) ── B (drehen) ── Spannplatz
```

Im Fenster „Neue Maschine …“ kommt eine zusätzliche Zeile „GROB G550 – horizontal (A/B)“.
Darunter bleiben die vorhandenen Felder für Name, Verfahrwege, Schwenkbereich A und
Spindeldrehzahl. B dreht endlos. Die Beschreibung erklärt, welcher Körper welche Achse fährt.
In Stellung A = 0 ist der Tisch waagerecht; A = −90 stellt seine Spannfläche zur Spindel.
Die Achsen werden wie die übrigen Beispiele nach DIN 66217 angezeigt.

Die Hubplatte lässt unter sich Platz für den vollständigen Y-Weg: Bei Y = +510 mm
bleibt ihre Unterkante 90 mm über dem Bett. Das gespeicherte Beispiel und die Vorlage
verwenden dieselbe korrigierte Form (P-2026-10-06-04).

**Akzeptanzkriterium:** „Neue Maschine …“ → GROB G550 → Bauen → „Maschine verfahren“:
X bewegt die Spindel seitlich, Z vor/zurück, Y den Tisch hoch/runter und A/B schwenken bzw.
drehen den Tisch innerhalb der eingetragenen Grenzen; Manuel versteht die Auswahl ohne Erklärung.

## Quellen und Grenzen des Beispiels

- [GROB G550, Herstellerseite](https://www.grobgroup.com/produkte/produktbereiche/universalmaschinen/fraes-bearbeitungszentren/g550/),
  gelesen 2026-10-06: Wege X/Y/Z 800/1.020/970 mm, Eilgang 65/50/80 m/min,
  Tischdurchmesser 770 mm; waagerechte Spindel, Rundachsen A/B.
- [GROB-Achsanordnung, Herstellerzeichnung zur gleichen Bauart](https://www.grobgroup.com/en/products/product-range/universal-machining-centers/milling-centers/g550a/),
  Abschnitt „Axis arrangement“, gelesen 2026-10-06: X/Z auf der Werkzeugseite,
  Y und A/B auf der Werkstückseite. Die G550a hat andere Verfahrwege; diese werden nicht übernommen.
- [GROB-Broschüre G350/G550 Generation 2 und G750](https://www.simusrl.com/simudemo/wp-content/uploads/2018/07/GROB_brochure_G352_G552_G751.pdf),
  Herstellerbroschüre bei einem Händler, gelesen 2026-10-06, Seite 11:
  G550 A −185 … +45°, B endlos, A 25 U/min und B 50 U/min.

Die Körpermaße und Abstände zum Drehpunkt sind angenähert. Die linearen Wege werden für das
Beispiel um die gebaute Stellung 0 verteilt; sie sind keine belegten MKS-Endlagen einer
konkreten Maschine. Die Spindel ist mit der angebotenen HSK-A63-Variante 16.000 U/min vorbelegt.
Beschleunigungen und Hochlaufzeit bleiben unbekannt. Die Vorlage ist zum Erklären und
Ausprobieren gedacht; eine konkrete Maschine braucht ihre tatsächlichen Maße und Kenndaten.
