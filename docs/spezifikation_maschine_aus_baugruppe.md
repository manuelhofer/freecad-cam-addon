# Spezifikation W-001: Maschine aus Baugruppe

Stand: Entwurf, wartet auf Freigabe durch Manuel. Keine offenen Fragen.

Das Addon ist für **beliebige Maschinen** gedacht – Fräsen, Drehmaschinen,
Dreh-Fräszentren, 3- bis 5-Achser. Wo unten eine bestimmte Maschine genannt
wird, ist sie nur ein Beispiel.

## 1. Zielbild

Eine Maschine wird so beschrieben, wie man sie in FreeCAD ohnehin bauen würde:
Man baut sie **grob in 3D nach** (Quader, Zylinder – so, wie sie ungefähr
aussieht), setzt sie in einer **Assembly** zusammen und legt die Bewegungen
über **Gelenke** fest. Das Addon ergänzt nur, was FreeCAD dabei nicht weiß:
**Achsnamen, Kenndaten und die Stellen, an denen Werkzeug und Werkstück
sitzen**. Daraus erzeugt es die **CAM-Maschinendefinition von FreeCAD**.

Später dient dasselbe Modell als Grundlage für Simulation und
Kollisionsprüfung (Stufen 3 und 4). Diese Stufen spezifiziert dieses Dokument
nur so weit, dass Stufe 1 und 2 ihnen nichts verbauen.

## 2. Was FreeCAD schon kann (Stand Wochen-Build 26.3.0 dev)

In **FreeCAD 1.1.3** (stabil) fehlen davon: die CAM-Maschinendefinition
(`Mod/CAM/Machine/`, damit auch der Export in Stufe 2), die neuen
Rundachs-Strategien, die Eigenschaft „Suppressed“ an Gelenken und die
RigidGroup-Gelenke. Das Auslesen der Baugruppe und der Dialog laufen dort
trotzdem (geprüft, P-2026-09-25-26); die Übergabe erklärt, dass sie den
Wochen-Build bzw. die nächste Version braucht.

| Baustein | Wo | Nutzen für uns |
| --- | --- | --- |
| Gelenke `Slider` (linear) und `Revolute` (drehend) mit Min/Max-Begrenzung | `Mod/Assembly/JointObject.py` | Richtung, Art und **Verfahrgrenzen** kommen von hier. Sie werden nicht doppelt erfasst. |
| Assembly-Simulation | `Mod/Assembly/CommandCreateSimulation.py` | Gelenke antreiben – Vorbild für Stufe 2 |
| CAM-Maschinendefinition (`.fcm`-Dateien) | `Mod/CAM/Machine/models/machine.py` | Ziel des Exports: Achsen mit `AxisRole` (Tisch/Kopf), `parent`, Grenzen, `max_velocity`, `WrapStrategy`, Spindeln, `tcp_supported` |
| Maschinen aus Addons | `MachineFactory.register_addon_machine_dir()` bzw. `<machine>` in `package.xml` | offizieller Weg, wie ein Addon Maschinen bereitstellt |

**Was der CAM-Maschinendefinition fehlt** und deshalb nur im Addon lebt:
Beschleunigung, Ruck, getrennter max. Vorschub, **eine Achse mit mehreren
Betriebsarten** (S4/C4) und jede Geometrie. Der Export schreibt, was FreeCAD
kennt; der Rest bleibt vollständig im Dokument erhalten.

## 3. Begriffe

- **Maschine** – eine Assembly, die das Addon als Maschine markiert hat.
- **Gelenk** – ein `Slider`- oder `Revolute`-Gelenk dieser Assembly.
- **Betriebsart** – eine Rolle, die ein Gelenk in der NC-Welt spielt. Jede hat
  ihren **eigenen, frei vergebenen Namen**. Ein Gelenk hat eine oder mehrere.
  Beispiel Drehmaschine: Gelenk „Hauptspindel“ → Betriebsart **S4** (Spindel,
  dreht) und **C4** (Positionieren). Beispiel Fräse mit Schwenkbrücke:
  Gelenk „Wiege“ → **A** (Positionieren), Gelenk „Rundtisch“ → **C**.
- **Glied** – alle Körper, die starr miteinander verbunden sind (siehe
  Abschnitt 6). Bewegt sich ein Gelenk, bewegt sich das ganze Glied dahinter.
- **Maschinenobjekt** – ein eigenes Objekt des Addons in der Assembly, das
  alle Maschinendaten enthält (siehe Abschnitt 5).
- **Werkzeugaufnahme** – Stelle, an der ein Werkzeug sitzt, mit Richtung der
  Werkzeugachse. Eine Maschine kann mehrere haben (Revolver, Gegenspindel,
  Frässpindel …), jede mit eigenem Namen.
- **Werkstückaufnahme** – Stelle, an der ein Werkstück gespannt wird
  (Futter, Tisch). Auch davon kann es mehrere geben.

## 4. Betriebsarten und ihre Werte

Namen werden **immer von Hand vergeben** – es gibt keine Automatik, die aus
Richtung oder Reihenfolge einen Namen ableitet. Das Addon prüft nur, dass kein
Name innerhalb einer Maschine doppelt vorkommt.

| Betriebsart | Erlaubt bei | Werte (Eingabeeinheit) | Pflicht |
| --- | --- | --- | --- |
| **Linear** | Slider | Eilgang (mm/min), max. Bearbeitungsvorschub (mm/min), Beschleunigung (m/s²), Ruck (m/s³) | Eilgang |
| **Positionieren** (Rund-/Schwenkachse) | Revolute | endlos ja/nein, max. Geschwindigkeit (U/min), Beschleunigung (U/s²), Ruck (U/s³) | Geschwindigkeit |
| **Spindel** (dreht) | Revolute | max. Drehzahl (U/min), Hochlaufzeit 0 → max. Drehzahl (s) | Drehzahl |
| **Revolver** (schaltet von Platz zu Platz) | Revolute | Schaltzeit je Platz (s); die Plätze selbst sind Werkzeugaufnahmen (Abschnitt 7a) | – |

- **Verfahrweg bzw. Schwenkbereich** kommen aus der Min/Max-Begrenzung des
  Gelenks. Ist dort keine gesetzt, gilt die Achse als unbegrenzt bzw. endlos,
  und das Addon weist darauf hin.
- **Einheiten:** Eingegeben wird in den Einheiten, die in Datenblättern und
  Maschinendaten stehen (U/min, m/s², U/s²). Beim Export wird in die Einheiten
  der CAM-Definition umgerechnet (Drehachsen dort in °/min;
  1 U/min = 360 °/min).
- **Optionale Werte** dürfen leer bleiben. Leer heißt „unbekannt“, nicht
  „null“ – die Simulation rechnet dann ohne diese Grenze und sagt das.
- Ein Drehgelenk kann **mehrere** Betriebsarten gleichzeitig haben (Spindel
  und Positionieren, Revolver und Positionieren); ein Schiebegelenk nur
  Linear.
- **Gelenke ohne Betriebsart** sind erlaubt: Sie werden von Hand verstellt
  (z. B. ein Reitstock ohne NC-Achse). Ihre Stellung setzt man später von
  Hand (Stufe 3), das NC-Programm kennt sie nicht.

## 5. Das Maschinenobjekt

Entscheidung Manuel: Die Maschinendaten liegen in **einem eigenen Objekt**
(„Maschine“) innerhalb der Assembly, nicht als Eigenschaften an den Gelenken.
Gelenke und Bauteile bleiben dadurch unverändert.

- Das Objekt hält den Namen der Maschine und die Listen der Betriebsarten und
  Aufnahmen. Jede Betriebsart **verweist** auf ihr Gelenk, jede Aufnahme auf
  ihr LCS (FreeCAD-Verknüpfung, kein gespeicherter Name – Umbenennen bricht
  nichts).
- **Gebrochene Verweise:** Wird ein Gelenk oder LCS gelöscht, bleibt die
  Betriebsart erhalten, wird aber im Dialog und im Report-Fenster als
  „ohne Gelenk“ gemeldet und kann einem anderen Gelenk zugeordnet werden. Beim
  Export wird sie nicht geschrieben, und der Export sagt das.
- Gelenke ohne Betriebsart sind erlaubt (etwa Hilfsgelenke), werden aber im
  Dialog als „nicht zugeordnet“ angezeigt.
- Alle Änderungen am Objekt laufen über Transaktionen (Strg+Z).

## 6. Glieder – mehrere Körper, die sich gemeinsam bewegen

Viele Maschinenteile bestehen aus mehreren Körpern, die sich zusammen
bewegen. Typisches Beispiel ist die **Schwenkbrücke** eines 5-Achsers: Zwei
Lagerböcke stehen fest auf dem Bett, dazwischen kippt die Wiege mit ihren
beiden Schenkeln um A (oder B), und in der Wiege dreht sich der Rundtisch (C).

```
Bett ──fest── Lagerböcke ──Revolute (A)── Wiege ──Revolute (C)── Rundtisch ── Werkstückaufnahme
                                           │
                             Schenkel links ─fest─┤
                             Schenkel rechts ─fest─┤
                             Boden ──────────fest─┘
```

- **Eine Achse, ein Gelenk:** Auch wenn die Wiege in zwei Lagerböcken
  sitzt, bekommt nur **einer** das Drehgelenk; der zweite Lagerbock hängt nur
  fest am Bett. Zwei Drehgelenke auf derselben Achse kann die Assembly nicht
  lösen – die Teile springen (ausprobiert, P-2026-09-25-13). Das Addon
  erkennt ein solches zweites Gelenk und sagt in Worten, welches zu
  unterdrücken ist.
- In der Assembly wird das mit **Fixed-Gelenken** gebaut (oder die Körper
  liegen gemeinsam in einer Unterbaugruppe). Das bewegt schon FreeCAD
  richtig mit; das Addon erfindet dafür nichts Eigenes.
- Das Addon fasst alle starr verbundenen Körper zu einem **Glied** zusammen.
  Die Kette der Maschine besteht aus Gliedern und den Slider-/Revolute-
  Gelenken dazwischen. Wie viele Körper ein Glied hat, ist egal.
- Der Dialog zeigt die Glieder mit ihren Körpern an, damit man sieht, ob ein
  Schenkel versehentlich nicht angebunden ist (er bliebe sonst beim Schwenken
  stehen).
- **Für die Kollisionsprüfung (Stufe 4)** gilt vorgemerkt: Körper innerhalb
  eines Glieds prüfen nie gegeneinander. Zwei Glieder, die direkt über ein
  Gelenk verbunden sind (Wiege und Lagerbock am Lager), standardmäßig auch
  nicht – abschaltbar pro Gelenk.

## 7. Werkzeug- und Werkstückaufnahmen

Markiert wird mit einem **lokalen Koordinatensystem** (LCS) im jeweiligen
Bauteil – dem gleichen Mittel, das die Assembly für Gelenke verwendet:

- **Ursprung** = Bezugspunkt (Spindelnase, Futterfläche, Tischmitte).
- **Z-Achse** = Richtung der Werkzeugachse bzw. Normale der Spannfläche.
- Im Maschinenobjekt bekommt jede Aufnahme eine Art (Werkzeug- oder
  Werkstückaufnahme), einen Namen, den Verweis auf ihr LCS und bei
  Werkzeugaufnahmen den Bezug zur Spindel-Betriebsart, falls das Werkzeug
  angetrieben ist. Das LCS selbst bleibt unverändert.

Ob eine Achse im **Tisch** oder im **Kopf** sitzt (`AxisRole`), ergibt sich aus
der Kette der Glieder (Abschnitt 6): Liegt das Gelenk zwischen dem festen Glied der
Assembly und einer Werkstückaufnahme, gehört es zum Tisch; liegt es zwischen
dem festen Teil und einer Werkzeugaufnahme, zum Kopf. Die Reihenfolge in
dieser Kette ergibt `parent`.

## 7a. Revolver und Werkzeugplätze

Ein Revolver wird am besten als **eigene Baugruppe** gebaut – Scheibe plus je
Werkzeugplatz ein LCS – und in die Maschine eingefügt (auch als Verknüpfung,
dann lässt er sich in mehreren Maschinen verwenden). In der Maschine hängt
diese Baugruppe mit **einem Drehgelenk** am Schlitten.

- Das Drehgelenk bekommt die Betriebsart **Revolver** (Schalten), bei
  NC-positionierbaren Revolvern zusätzlich **Positionieren** (beliebige
  Gradzahl).
- **Jeder Platz ist eine Werkzeugaufnahme** mit einem eigenen LCS (Ursprung =
  Werkzeugaufnahme, Z = Werkzeugrichtung; axial und radial gemischt geht).
  Das Addon nummeriert die Plätze **P1 … Pn**; welches Werkzeug auf welchem
  Platz sitzt, kommt aus dem CAM-Job, nicht aus der Maschine.
- Die **Anzahl der Plätze** zählt das Addon selbst: alle Werkzeugaufnahmen im
  Glied des Revolvers.
- Angetriebene Plätze verweisen auf ihre Spindel-Betriebsart (Antrieb der
  angetriebenen Werkzeuge).
- **Verteilhilfe:** ersten Platz (LCS) auswählen, Anzahl eingeben – das Addon
  legt die übrigen Plätze gleichmäßig im Kreis um die Revolverachse an und
  nummeriert sie. Danach lässt sich jeder Platz einzeln verschieben oder
  löschen.

## 7b. Weitere Beispiele

Alles mit denselben Bausteinen – Gelenk, Betriebsart, Aufnahme:

| Maschinenteil | Gelenk | Betriebsarten | Aufnahme |
| --- | --- | --- | --- |
| **4. Achse** auf der Fräse | Drehgelenk am Tisch | Positionieren, endlos (z. B. A) | Werkstückaufnahme am Futter/Planscheibe |
| **Gegenspindel** | Schiebegelenk am Bett, Drehgelenk am Schlitten | Linear (z. B. Z2); Spindel und Positionieren (z. B. S2/C2) | Werkstückaufnahme am Futter |
| **Reitstock** mit NC | Schiebegelenk am Bett | Linear (z. B. Z3) | – (Spitze als Körper, für die Kollision) |
| **Reitstock** von Hand | Schiebegelenk am Bett | keine – von Hand verstellt | – |
| **Pinole** | Schiebegelenk im Reitstock | Linear oder keine | – |

## 8. Beschleunigung ermitteln (Hilfetext für den Dialog)

Von genau zu grob:

1. **Maschinendaten der Steuerung** – nur lesen, nichts ändern; oft nur mit
   Schlüsselschalter oder Kennwort sichtbar.
   - *Siemens 840D sl:* MD32000 `MAX_AX_VELO` (Eilgang), MD32300
     `MAX_AX_ACCEL` (Beschleunigung, m/s² bzw. U/s²), MD32431 `MAX_AX_JERK`
     (Ruck), MD36100/36110 `POS_LIMIT_MINUS/PLUS` (Software-Endschalter).
   - *Fanuc:* Parameter 1420 (Eilgang), 1620 (Zeitkonstante Eilgang in ms) →
     Beschleunigung ≈ Eilgang ÷ Zeitkonstante (Einheiten angleichen:
     mm/min → m/s durch 60 000, ms → s durch 1000).
   - *LinuxCNC:* `MAX_VELOCITY` und `MAX_ACCELERATION` in der INI-Datei.
2. **Handbuch / Datenblatt** – Eilgänge fast immer, Beschleunigung selten.
3. **Messen** – eine kurze Strecke `s` im Eilgang fahren und die Zeit `t`
   nehmen (am besten über die Trace-/Oszilloskop-Funktion der Steuerung, zur
   Not per Stoppuhr über viele Wiederholungen). Ist die Strecke so kurz, dass
   der Eilgang nicht erreicht wird, gilt **a ≈ 4 · s ÷ t²**.
   Beispiel: 20 mm in 0,2 s → 4 · 0,02 m ÷ (0,2 s)² = **2 m/s²**.
   Das ist eine Näherung, weil der Ruck die Rampen abrundet – der gemessene
   Wert liegt eher zu niedrig.
4. **Spindel:** Hochlaufzeit mit Stoppuhr von Stillstand bis Maximaldrehzahl.

## 9. Stufen

Jede Stufe besteht aus mehreren Patches mit je einem Akzeptanzkriterium. Die
Klickwege hier sind die Richtung; die genauen Kriterien stehen im jeweiligen
Patch.

**Stufe 1 – Maschine beschreiben**
- Eine Assembly als Maschine markieren. Ein Dialog listet ihre Slider- und
  Revolute-Gelenke. Pro Gelenk lassen sich Betriebsarten mit Namen und Werten
  anlegen, pro LCS Aufnahmen. Alles wird im **Maschinenobjekt** gespeichert
  (Abschnitt 5) und ist mit Strg+Z rückgängig zu machen.
- *Klickweg:* Beispielmaschine öffnen → „Maschine bearbeiten“ → Gelenk
  „Hauptspindel“ bekommt S4 und C4 → speichern, schließen, neu öffnen → S4
  und C4 sind noch da.

**Stufe 2 – Export in die CAM-Maschinendefinition**
- Das Addon schreibt eine `.fcm`-Datei und meldet sie über den offiziellen
  Addon-Weg an.
- *Klickweg:* „Maschine exportieren“ → im CAM-Job erscheint die Maschine in
  der Maschinenauswahl, mit den Achsen und Grenzen aus der Baugruppe.

**Stufe 3 – Maschine von Hand verfahren** (Grundlage der Simulation)
- Ein Fenster mit einem Regler je Betriebsart (Name, Wert, Grenzen); die
  Baugruppe bewegt sich mit.
- *Klickweg:* Regler „C4“ auf 90° → das Futter dreht sich um 90°; Regler über
  die Grenze hinaus geht nicht.
- **Gebaut** (P-2026-09-25-67): Befehl „Maschine verfahren“, ein
  Aufgabenfenster mit je Achse der Kette einem Regler und einem Zahlenfeld
  (auch für Gelenke ohne Betriebsart; eine Spindel unter ihrem
  Positionier-Namen). Gezählt wird wie am Gelenk (Seite 2 gegenüber
  Seite 1), die Grenzen kommen aus der Begrenzung des Gelenks. Bewegt werden
  alle Bauteile hinter der Achse, gerechnet immer vom Stand beim Öffnen aus
  (Lage = B1(w1) · B2(w2) · … · Lage beim Öffnen). Die Assembly lässt die
  Stellung beim Neuberechnen stehen (ausprobiert, 1.1.3 und Wochen-Build).
  OK = ein Schritt Rückgängig, Abbrechen und „Grundstellung“ fahren
  zurück. **Revolver** (P-2026-09-25-69): eine Auswahl der Plätze; der
  gewählte Platz dreht an die Stelle, an der beim Öffnen P1 stand.

**Stufe 4 – Werkzeugbahn abfahren und Kollision prüfen** – eigene
Spezifikation, wenn Stufe 3 steht.

## 10. Prüfbarkeit

- Für die automatischen Prüfungen (ohne Fenster) wird eine **kleine
  Beispielmaschine** per Skript erzeugt: fester Rahmen, X/Z-Schlitten, eine
  Spindel mit S/C-Betriebsart, eine Werkzeug- und eine Werkstückaufnahme –
  und eine zweite mit Schwenkbrücke (Wiege aus mehreren Körpern), damit die
  Glied-Bildung geprüft wird.
  Geprüft werden Einlesen, Glieder, Namensprüfung, Tisch/Kopf-Zuordnung, Umrechnung
  und der Inhalt der `.fcm`-Datei.
- Ob sich Assembly-Gelenke ohne Fenster anlegen und lösen lassen, ist der
  erste Punkt, der in Stufe 1 geprüft wird. Geht das nicht, liegt die
  Beispielmaschine als fertige `.FCStd`-Datei unter `tests/`.
- Dialoge und das Aussehen prüft Manuel in FreeCAD.

## 11. Bedienung

Es gilt `docs/arbeitsregeln.md`, Abschnitt 8 (Bedienbarkeit und Sprache). Für
diesen Dialog heißt das konkret:

- **Zeigen, welches Teil gemeint ist:** Fährt man in der Liste über ein
  Gelenk, wird es in der 3D-Ansicht hervorgehoben und bewegt sich einmal kurz
  hin und her – man sieht sofort, welche Achse das ist und in welche Richtung
  sie fährt. Dasselbe für Glieder (alle Körper des Glieds leuchten auf) und
  Aufnahmen (ein Pfeil zeigt die Werkzeugrichtung).
- **Betriebsart wählen mit Bild:** Linear, Positionieren und Spindel werden
  mit je einem kleinen Symbol und einem Satz angeboten; nicht erlaubte
  Betriebsarten (Spindel an einem Slider) erscheinen gar nicht erst.
- **Einheiten stehen am Feld**, Pflichtfelder sind als solche erkennbar,
  optionale zeigen „unbekannt“ statt 0.
- **Hilfe (?)** je Bereich: Betriebsarten, Glieder, Aufnahmen und
  „Beschleunigung ermitteln“ (Abschnitt 8 dieser Spezifikation als Hilfetext).
- **Warnungen in Worten**, z. B. „Der Körper *Schenkel links* hängt an keinem
  Glied – er bleibt beim Schwenken stehen.“

## Entschieden

- **Speicherort:** eigenes Maschinenobjekt (Manuel, P-2026-09-25-08).
- **Betriebsarten:** Linear, Positionieren, Spindel und – auf Manuels Wunsch
  – Revolver (P-2026-09-25-15). Weitere (etwa für TRANSMIT/TRACYL), sobald
  jemand sie braucht.
- **Revolver:** eigene Baugruppe mit einem Drehgelenk; Plätze einzeln als
  LCS plus Verteilhilfe; Platznamen P1 … Pn, Werkzeugzuordnung aus CAM
  (Manuel, P-2026-09-25-15).
