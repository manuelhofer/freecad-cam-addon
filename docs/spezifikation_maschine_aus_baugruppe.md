# Spezifikation W-001: Maschine aus Baugruppe

Stand: Entwurf, noch nicht freigegeben. Offene Fragen stehen in Abschnitt 9.

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
  Beispiel CLX 550: Gelenk „Hauptspindel“ → Betriebsart **S4** (Spindel,
  dreht) und **C4** (Positionieren).
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

- **Verfahrweg bzw. Schwenkbereich** kommen aus der Min/Max-Begrenzung des
  Gelenks. Ist dort keine gesetzt, gilt die Achse als unbegrenzt bzw. endlos,
  und das Addon weist darauf hin.
- **Einheiten:** Eingegeben wird in den Einheiten, die in Datenblättern und
  Maschinendaten stehen (U/min, m/s², U/s²). Beim Export wird in die Einheiten
  der CAM-Definition umgerechnet (Drehachsen dort in °/min;
  1 U/min = 360 °/min).
- **Optionale Werte** dürfen leer bleiben. Leer heißt „unbekannt“, nicht
  „null“ – die Simulation rechnet dann ohne diese Grenze und sagt das.
- Ein Gelenk kann **gleichzeitig** Spindel und Positionieren sein, aber nicht
  Linear und etwas anderes.

## 5. Werkzeug- und Werkstückaufnahmen

Markiert wird mit einem **lokalen Koordinatensystem** (LCS) im jeweiligen
Bauteil – dem gleichen Mittel, das die Assembly für Gelenke verwendet:

- **Ursprung** = Bezugspunkt (Spindelnase, Futterfläche, Tischmitte).
- **Z-Achse** = Richtung der Werkzeugachse bzw. Normale der Spannfläche.
- Das Addon gibt dem LCS eine Art (Werkzeug-/Werkstückaufnahme), einen Namen
  und bei Werkzeugaufnahmen den Bezug zur Spindel-Betriebsart, falls das
  Werkzeug angetrieben ist.

Ob eine Achse im **Tisch** oder im **Kopf** sitzt (`AxisRole`), ergibt sich aus
der Baugruppe: Liegt das Gelenk in der Kette zwischen dem festen Teil der
Assembly und einer Werkstückaufnahme, gehört es zum Tisch; liegt es zwischen
dem festen Teil und einer Werkzeugaufnahme, zum Kopf. Die Reihenfolge in
dieser Kette ergibt `parent`.

## 6. Beschleunigung ermitteln (Hilfetext für den Dialog)

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

## 7. Stufen

Jede Stufe besteht aus mehreren Patches mit je einem Akzeptanzkriterium. Die
Klickwege hier sind die Richtung; die genauen Kriterien stehen im jeweiligen
Patch.

**Stufe 1 – Maschine beschreiben**
- Eine Assembly als Maschine markieren. Ein Dialog listet ihre Slider- und
  Revolute-Gelenke. Pro Gelenk lassen sich Betriebsarten mit Namen und Werten
  anlegen, pro LCS Aufnahmen. Alles wird **im Dokument** gespeichert (siehe
  Frage 1) und ist mit Strg+Z rückgängig zu machen.
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

**Stufe 4 – Werkzeugbahn abfahren und Kollision prüfen** – eigene
Spezifikation, wenn Stufe 3 steht.

## 8. Prüfbarkeit

- Für die automatischen Prüfungen (ohne Fenster) wird eine **kleine
  Beispielmaschine** per Skript erzeugt: fester Rahmen, X/Z-Schlitten, eine
  Spindel mit S/C-Betriebsart, eine Werkzeug- und eine Werkstückaufnahme.
  Geprüft werden Einlesen, Namensprüfung, Tisch/Kopf-Zuordnung, Umrechnung
  und der Inhalt der `.fcm`-Datei.
- Ob sich Assembly-Gelenke ohne Fenster anlegen und lösen lassen, ist der
  erste Punkt, der in Stufe 1 geprüft wird. Geht das nicht, liegt die
  Beispielmaschine als fertige `.FCStd`-Datei unter `tests/`.
- Dialoge und das Aussehen prüft Manuel in FreeCAD.

## 9. Offene Fragen

1. **Wo liegen die Maschinendaten im Dokument?**
   - *A (Empfehlung):* als zusätzliche Eigenschaften direkt an den Gelenken und
     LCS. Die Daten stehen dann im Eigenschaften-Editor genau dort, wo das
     Gelenk ist, und reisen mit, wenn man Teile kopiert.
   - *B:* ein eigenes Objekt „Maschinendaten“ in der Assembly, das auf die
     Gelenke verweist. Die Gelenke bleiben unverändert, aber die Verweise
     können brechen, wenn ein Gelenk gelöscht und neu angelegt wird.
2. **Wie viele Betriebsarten bekommt ein Gelenk?** Reichen die drei aus
   Abschnitt 4, oder gibt es an der CLX 550 (oder anderswo) noch eine Rolle,
   die hier fehlt – etwa eine Achse, die mal als Linearachse und mal als
   Teil einer Transformation (TRANSMIT/TRACYL) läuft?
