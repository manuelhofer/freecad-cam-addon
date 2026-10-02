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
Betriebsarten** (S4/C4), **Transformationen der Steuerung** (etwa eine
schräge Achse, Abschnitt 7c) und jede Geometrie. Der Export schreibt, was
FreeCAD kennt; der Rest bleibt vollständig im Dokument erhalten.

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
  und das Addon weist darauf hin. Seit 2026-09-29 stehen sie auch im Fenster
  „Maschine bearbeiten“ bei Linear und Positionieren („Verfahrweg von … bis
  … mm“, leer = keine Grenze) – Manuel: „man müsste schon auch editieren
  können was die maschine kann die verfahrwege“. Ein Satz darunter sagt, was
  0 heißt (die Stellung, in der die Baugruppe gebaut ist) und dass das
  Prüffenster daraus mit der Werkzeuglänge rechnet, wohin die Spitze kommt.
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

## 7c. Schräge Achse (Transformation der Steuerung)

Bei vielen Schrägbett-Drehmaschinen mit Y-Achse fährt der Y-Schlitten nicht
rechtwinklig zum X-Schlitten, sondern schräg dazu. Das NC-Programm bleibt
trotzdem rechtwinklig: Die Steuerung rechnet es um – bei Siemens die
Transformation „schräge Achse“ (TRAANG, Winkel in `TRAANG_ANGLE_1`), bei
Fanuc „Angular Axis Control“. Für ein reines Y im Programm fahren dann
**beide** Schlitten (Manuel, 2026-09-26: „beide müssen verfahren, um Y zu
bewegen“).

Dass das Bett selbst schräg im Raum liegt, ist dagegen keine Transformation:
Das X im Programm zeigt einfach in Richtung des X-Schlittens. So ist die
Beispiel-Drehmaschine gebaut (Bett um 45° gekippt, Y rechtwinklig zu X).

**Begriffe**

- **Schräge Achse** – der Schlitten, der schräg steht (meist Y1).
- **Ausgleichende Achse** – der Schlitten, der mitfährt, damit das Werkzeug
  rechtwinklig läuft (meist X1). Er zeigt genau in Richtung seiner
  Programmachse: Ein reines X im Programm fährt nur ihn.
- **Winkel α** – wie weit die schräge Achse aus dem rechten Winkel zur
  ausgleichenden gekippt ist; 0° heißt rechtwinklig. Positiv, wenn sie zur
  Plus-Seite der ausgleichenden kippt – ein Bild im Dialog zeigt es.
- **Programmachsen** – X und Y, wie sie im NC-Programm stehen,
  rechtwinklig zueinander. Ihre Namen sind aus den Betriebsarten vorbelegt
  (X1 → X, Y1 → Y) und änderbar.

**Rechnung** – Wege in mm, gezählt von der Stellung 0 der Gelenke:

```
vom Programm zu den Schlitten      von den Schlitten zum Programm
Y1 = Y / cos α                     Y = Y1 · cos α
X1 = X − Y · tan α                 X = X1 + Y1 · sin α
```

Beispiel α = 30°: Y +10 mm → Y1 +11,547 mm und X1 −5,774 mm. Bei
Drehmaschinen steht X im Programm meist als Durchmesser; hier ist X der Weg
des Schlittens (Radius) – siehe „Nicht Teil davon“. Mit dem Haken „zählt im
Durchmesser (Ø)“ zeigt das Addon X doppelt; gerechnet wird weiter im Radius
(P-2026-09-30-54).

**Was daraus folgt**

- **Der Arbeitsraum ist ein Parallelogramm, kein Rechteck.** Wie weit Y
  reicht, hängt davon ab, wo X steht: X1 muss ausgleichen können. Beispiel
  X1 −170 … 150 mm, Y1 −60 … 60 mm, α = 30°: Y reicht höchstens ±52,0 mm;
  steht X auf 140 mm, geht Y nach unten nur bis −17,3 mm – dann steht X1 an
  seiner Grenze 150 mm.
- **Geschwindigkeit:** Fährt Y mit v, fährt Y1 mit v ÷ cos α und X1 mit
  v · tan α. Für Y gilt deshalb höchstens min(vY1 · cos α, vX1 ÷ tan α) –
  bei Eilgang, Vorschub und Beschleunigung gleich. Beispiel: Y1 5000 mm/min,
  X1 10 000 mm/min, α = 30° → Y höchstens 4330 mm/min.
- **Der Postprozessor bleibt, wie er ist:** Das Programm ist rechtwinklig,
  umrechnen tut die Steuerung.

**Im Maschinenobjekt** kommt zu Betriebsarten und Aufnahmen eine dritte Art
von Eintrag: die **Transformation**, zuerst nur „Schräge Achse“. Später
passen dort TRANSMIT (Stirnseite), TRACYL (Mantelfläche) und 5-Achs-TCP
hinein – sie sind Transformationen, keine Betriebsarten.

- Der Eintrag verweist auf zwei Betriebsarten der Art Linear (schräge und
  ausgleichende Achse) und hält die Namen der Programmachsen. Gebrochene
  Verweise wie in Abschnitt 5: gemeldet, nicht übergeben.
- **Der Winkel steht nur in der Baugruppe** – in der Richtung des
  Schiebegelenks der schrägen Achse –, nicht noch einmal im Eintrag. Der
  Dialog misst ihn dort.
- **Winkel eintragen, die Baugruppe folgt** (Manuel): Wer einen Winkel
  eintippt, dreht damit die Führung der schrägen Achse. Das Addon dreht
  beide Gelenk-Koordinatensysteme des Schiebegelenks gleich, um die Normale
  der Ebene aus beiden Achsen. Der Schlitten und alles darauf behalten ihre
  Lage – der Revolver bleibt gerade –, nur die Fahrrichtung ändert sich.
  Steht der Schlitten dabei nicht auf 0, bleibt er auf seiner Stellung, nun
  entlang der neuen Richtung. Ein Schritt Strg+Z.
  Ausprobiert (P-2026-09-26-65) an der Beispiel-Drehmaschine, Y-Führung um
  30° gedreht, in 1.1.3 und im Wochen-Build: kein Teil bewegt sich, der
  Revolver dreht sich nicht, Y1 fährt genau in der neuen Richtung, die
  Stellung bleibt beim Neuberechnen, der Winkel nach Speichern und Laden.
- Erlaubt sind −89° bis 89°. Bei 90° führen beide Schlitten in dieselbe
  Richtung – das sagt ein Satz am Feld.
- **Erkennung:** Stehen zwei Linearachsen weder parallel noch rechtwinklig
  zueinander und gibt es keinen Eintrag, zeigt „Maschine bearbeiten“ einen
  Hinweis: „Y1 steht 30,0° schräg zu X1. Rechnet die Steuerung Y
  rechtwinklig um? – Schräge Achse anlegen“. Ein Klick legt den Eintrag an;
  ausgleichend ist vorbelegt die Achse, deren Name im Alphabet vorn steht,
  tauschen geht im Eintrag.

**Dialog „Maschine bearbeiten“** – ein neuer Bereich unter den Achsen:

```
Transformationen                                         (?)
┌────────────────────────────────────────────────────────┐
│ Schräge Achse Y1 – gleicht aus: X1, 30,0°              │
└────────────────────────────────────────────────────────┘
[+ Schräge Achse]  [Entfernen]
┌ gewählter Eintrag ─────────────────────────────────────┐
│ Schräge Achse ........... [Y1              ▾]          │
│ gleicht aus ............. [X1              ▾]          │
│ Namen im Programm ....... X [X   ]   Y [Y   ]          │
│ Winkel .................. [ 30,0 ] °                  │
│   [Bild: X1, Y1, rechter Winkel und α]                 │
│ Beispiel: Y +10 mm → Y1 +11,5 mm, X1 −5,8 mm           │
└────────────────────────────────────────────────────────┘
```

Verweilt die Maus auf dem Eintrag, fährt die Maschine kurz ein Y des
Programms hin und her – beide Schlitten bewegen sich (Abschnitt 11,
„Zeigen, welches Teil gemeint ist“).

**„Maschine verfahren“** bekommt bei einer schrägen Achse oben einen
Umschalter; zuerst steht er auf „wie im Programm“ (Manuel):

```
Achsen:  (•) wie im Programm   ( ) der Maschine
X   ├──────●──────────┤  [   0,0 ] mm
Y   ├────────●────────┤  [  10,0 ] mm
      X1 −5,8 mm    Y1 11,5 mm                  (grau)
Z1  ├────●────────────┤  [   0,0 ] mm
C1  ├●────────────────┤  [   0,0 ] °
Weiter geht Y hier nicht: X1 steht an seiner Grenze 150 mm.
```

- „Wie im Programm“: Regler für die Programmachsen X und Y; beide Schlitten
  fahren sichtbar mit, ihre Stellungen stehen grau darunter. Die übrigen
  Achsen wie bisher.
- „Der Maschine“: je Schlitten ein Regler, wie bisher; darunter grau, wo das
  Werkzeug im Programm steht.
- Die Regler reichen so weit, wie die Achse überhaupt kommt. Hält ein
  Schlitten an seiner Grenze, bleibt der Regler stehen, und die Zeile
  darunter sagt, welcher Schlitten angeschlagen hat.

**An CAM übergeben:** Statt der schrägen Richtung von Y1 geht die
rechtwinklige Richtung der Programmachse hinaus (Name wie bisher Y1), mit
Grenzen und Eilgang umgerechnet (Grenzen · cos α, Eilgang wie oben). Der
Bericht sagt: „Y1 ist eine schräge Achse (30,0° zu X1). CAM bekommt sie
rechtwinklig wie „Y“ im Programm, mit umgerechneten Grenzen und Eilgang.
Diese Grenzen gelten nur, solange X1 Platz zum Ausgleichen hat – wie weit es
wirklich geht, zeigt „Maschine verfahren“ wie im Programm.“ (Später rechnet
es auch die Prüfung auf der Maschine, Stufe 4a.)

**Schruppwerte planen:** Der Höchstvorschub der Maschine ist der kleinste
aller Linearachsen; für die schräge Achse zählt dabei der umgerechnete Wert
für Y (oben).

**Stufe 4:** Die Achsstellungen einer Bahn (spezifikation_simulation.md,
Abschnitt 4) rechnen im Programm-Koordinatensystem: X entlang der
ausgleichenden Achse, Y rechtwinklig dazu in der Ebene beider Achsen. Die
Grenzen prüfen die Schlitten, und die Meldung nennt den, der anschlägt: „Für
Y = 35 mm müsste X1 auf 162 mm, die Grenze ist 150 mm.“

**Vorlage mit Eingabemaske** (Manuel: „so, dass es ein Leichtes ist, so
etwas zu erstellen“): Aus wenigen Zahlen – Bettneigung, Winkel der
Y-Achse, Wege X/Y/Z, Revolverplätze, Höchstdrehzahl – baut das Addon eine
fertige Drehmaschine samt Eintrag „Schräge Achse“. Ob das ein eigener Befehl
wird oder in „Beispielmaschine laden …“ steckt, wird vor diesem Schritt mit
einer Skizze entschieden.

**Nicht Teil davon**

- X als Durchmesser anzeigen (in „Maschine verfahren“ steht wie bisher der
  Weg des Schlittens) – ein eigenes Thema, falls gewünscht. Inzwischen
  umgesetzt, siehe „Entschieden“ (P-2026-09-30-54).
- TRANSMIT, TRACYL, 5-Achs-TCP – sie kommen in die gleiche Liste, sobald
  jemand sie braucht.
- Eine Auswahl der Steuerung (siehe „Entschieden“).
- Offen für den Hilfetext: ob Siemens das Vorzeichen von α genauso zählt –
  vorher im Handbuch nachsehen, statt es zu behaupten.

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

**Stufe 3b – Schräge Achse** (Abschnitt 7c; Manuel, 2026-09-26) – je ein
Patch, in dieser Reihenfolge:
1. Eintrag „Schräge Achse“ in „Maschine bearbeiten“: anlegen, Achsen wählen,
   Winkel aus der Baugruppe, Beispielzeile. *Klickweg:* Beispiel-Drehmaschine
   → „Maschine bearbeiten“ → „+ Schräge Achse“ → Y1, gleicht aus X1 → der
   Eintrag zeigt 0,0° und „Y +10 mm → Y1 +10,0 mm, X1 0,0 mm“. – *Gebaut
   (P-2026-09-26-66); beim Verweilen leuchten beide Schlitten auf, das
   Hin-und-her-Fahren kommt mit Schritt 4.*
2. Winkel eintragen, die Baugruppe folgt. *Klickweg:* Winkel 30 → in der
   3D-Ansicht steht die Y-Führung 30° schräg, der Revolver gerade; die
   Beispielzeile zeigt „Y1 +11,5 mm, X1 −5,8 mm“; Strg+Z stellt die Führung
   zurück. – *Gebaut (P-2026-09-26-67).*
3. Erkennung: Hinweis bei schräg stehenden Linearachsen ohne Eintrag, ein
   Klick legt ihn an. – *Gebaut (P-2026-09-26-68); schräg heißt ab 0,05°
   (der Dialog zeigt dann 0,1°) bis 89°.*
4. „Maschine verfahren“ wie im Programm. *Klickweg:* Y auf 10 → beide
   Schlitten fahren, grau darunter „X1 −5,8 mm, Y1 11,5 mm“; am Anschlag
   sagt eine Zeile, welcher Schlitten hält. – *Gebaut (P-2026-09-26-69),
   dazu das Hin-und-her-Fahren beim Verweilen auf dem Eintrag; gilt für die
   erste schräge Achse einer Maschine.*
5. An CAM übergeben: Y rechtwinklig, Grenzen und Eilgang umgerechnet, Satz
   im Bericht.
6. Schruppwerte planen: umgerechneter Höchstvorschub für Y. – *Gebaut
   (P-2026-09-26-72).*
7. Vorlage mit Eingabemaske – Aufbau vorher mit Skizze entscheiden. –
   *Gebaut (P-2026-09-26-75) als eigener Befehl „Neue Maschine …“ (siehe
   „Entschieden“). Klickweg: „Neue Maschine …“ → Drehmaschine → Name,
   Bettneigung 30°, Y schräg um 30°, Wege, 8 Plätze, 4000 U/min → „Maschine
   bauen“ → neues Dokument, „Maschine bearbeiten“ zeigt die schräge Achse
   mit 30,0° und acht Revolverplätze.*

**Stufe 4 – Werkzeugbahn abfahren und Kollision prüfen** – eigene
Spezifikation: [spezifikation_simulation.md](spezifikation_simulation.md)
(Entwurf P-2026-09-25-70; 4a von Manuel entschieden, P-2026-09-26-83).

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

## 12. Maschinen-Speicher und Maschinenzuweisung (W-011, zur Besprechung)

Manuel, 2026-10-02: „Ich hätte gerne sozusagen einen Maschinen-Speicher … ich kann ja mehrere
Maschinen haben … und würde gerne auswählen können, auf welcher Maschine ich das Teil
bearbeite … theoretisch richte ich mir meine 6 Maschinen ein: einmal 3-Achs, einmal 5-Achs,
einmal 4-Achs, eine Drehbank mit Revolver … Und wenn ich dann ein Teil öffne im CAM, wäre
erstmal die Abfrage ‚Maschinenzuweisung‘, also welche Maschine wird benutzt … Danach kann man
bessere Entscheidungen treffen, wenn man das schon weiß … Beispiel: Auf einer Drehbank ist das
Rohteil selten eckig.“

- **Heute:** Eine Maschine ist eine FreeCAD-Datei mit einer Baugruppe (Abschnitt 5), gespeichert,
  wo man will. Das Addon merkt sich genau eine – die zuletzt benutzte (D-20) – und am Job die,
  auf der geprüft wurde. Der 4-Achs-Assistent fragt zuerst nach der Maschine (offene Maschinen
  und die zuletzt benutzte), der Assistent „Bearbeitung (Fräsen)“ gar nicht: Er nimmt einen
  Quader und eine 3-Achs-Fräse an. Eine Liste aller eigenen Maschinen gibt es nicht.
- **Der Speicher:** eine Liste der eigenen Maschinen in `CamAddon/maschinen.json` im
  Benutzerordner (wie die Werkzeugverwaltung, Neustart und Update überlebend): je Maschine
  Name, Datei und was das Addon zum Entscheiden braucht, ohne die Datei zu öffnen – die Art
  (3-Achs-Fräse, 4-Achs-Fräse mit Rundachse A oder B, 5-Achs-Fräse, Drehmaschine mit Revolver,
  mit C/Y oder ohne), die Achsen, Werkzeugplätze, Höchstdrehzahl. In die Liste kommt eine
  Maschine von selbst, wenn man sie mit „Neue Maschine …“ baut und speichert, sie zum Prüfen
  öffnet oder in einem Assistenten wählt; dazu ein Fenster „Maschinen“ (Menü CAM-Addon) mit
  Hinzufügen (Datei wählen), Neue Maschine, Bearbeiten (öffnet sie), Entfernen (nur aus der
  Liste – die Datei bleibt).
- **Option A (Empfehlung) – die Maschine ist die erste Frage im Assistenten:** Schritt 1 von
  „Bearbeitung“ beginnt mit „Maschine“ (die Liste, vorgewählt die des Jobs, sonst die zuletzt
  benutzte). Danach richtet sich alles: Drehmaschine oder 4-Achs-Fräse – das Rohteil ist eine
  Stange längs ihrer Rundachse, es geht weiter wie im 4-Achs-Assistenten; 3-Achs-Fräse – ein
  Quader wie heute; 5-Achs-Fräse – vorerst wie 3-Achs (Tisch und Kopf auf 0), später 3+2. Die
  Wahl steht am Job: „Auf der Maschine prüfen“ öffnet sie ohne Frage, die Bestückung nimmt
  ihren Revolver, der Postprozessor (W-005) später ihre Steuerung. Ein Einstieg für alles –
  die Maschine entscheidet, welcher Assistent.
- **Option B – eine eigene Abfrage, sobald ein Job entsteht:** auch bei FreeCADs eigenem
  „Job“. Erfasst jeden Weg, greift aber in FreeCAD ein (jede neue Version kann das brechen),
  und eine Frage mehr für alle, die nur schnell etwas probieren.
- **Option C – nur am Job:** „Maschine zuweisen …“ am Job im Baum, die Assistenten fragen nicht.
  Am wenigsten Eingriff, aber das Addon weiß es oft nicht, wenn es entscheidet.

```
 CAM-Addon → Maschinen …
 ┌──────────────────────────────────────────────────────────────────┐
 │ Name            Art                              Datei            │
 │ DMU 50          5-Achs-Fräse (B, C)              …/dmu50.FCStd    │
 │ Mazak QT 200    Drehmaschine, Revolver 12, C/Y   …/mazak.FCStd    │
 │ Deckel FP4      3-Achs-Fräse                     …/fp4.FCStd      │
 │ Rundtisch-Fräse 4-Achs-Fräse (A)                 …/fp4_a.FCStd    │
 │ [Hinzufügen …] [Neue Maschine …] [Bearbeiten] [Entfernen]          │
 └──────────────────────────────────────────────────────────────────┘

 Bearbeitung – Schritt 1 von 3 – Aufspannung
 ┌──────────────────────────────────────────────────────────────────┐
 │ Maschine   [Mazak QT 200 – Drehmaschine mit Revolver        ▾]    │
 │ Rohteil    Stange Ø 60 × 120 längs Z (von der Maschine)           │
 │ Nullpunkt  [Mitte Stirn ▾]                                        │
 │                                                    [Weiter →]     │
 └──────────────────────────────────────────────────────────────────┘
```

- **Dazu zu entscheiden** (je mit Empfehlung):
  1. A, B oder C – Empfehlung A.
  2. Der Speicher hält (a) Verweise auf die Dateien, wo sie liegen – eine Änderung an der Datei
     gilt sofort –, oder (b) Kopien in einem Ordner des Addons. Empfehlung (a); fehlt eine
     Datei, sagt das Fenster es und bietet „Suchen …“ an.
  3. Vorgewählt ist (a) die des Jobs, sonst die zuletzt benutzte, oder (b) eine feste
     „Standard“-Maschine. Empfehlung (a).
- **Fertig, wenn:** Manuel seine Maschinen einmal einträgt, beim nächsten Teil in Schritt 1 die
  Drehmaschine wählt und eine Stange statt eines Quaders bekommt – und „Auf der Maschine
  prüfen“ ohne Frage auf ihr prüft.

## Entschieden

- **Speicherort:** eigenes Maschinenobjekt (Manuel, P-2026-09-25-08).
- **Betriebsarten:** Linear, Positionieren, Spindel und – auf Manuels Wunsch
  – Revolver (P-2026-09-25-15). Weitere (etwa für TRANSMIT/TRACYL), sobald
  jemand sie braucht.
- **Revolver:** eigene Baugruppe mit einem Drehgelenk; Plätze einzeln als
  LCS plus Verteilhilfe; Platznamen P1 … Pn, Werkzeugzuordnung aus CAM
  (Manuel, P-2026-09-25-15).
- **Beispielmaschine zum Ausprobieren** (Manuel, P-2026-09-26-38): Ohne
  Baugruppe bieten „Maschine bearbeiten“ und „Maschine verfahren“ den Knopf
  „Beispielmaschine laden“ – eine Dreiachs-Fräsmaschine (Kreuztisch X/Y,
  Fräskopf Z, Spindel S1, Werkzeug- und Werkstückaufnahme) in einem neuen
  Dokument, danach gleich der Dialog. Gebaut mit dem Baukasten der
  Prüfungen (`camaddon/beispielmaschine.py`); ihre Gelenke lassen die Teile,
  wo sie gebaut sind: Versatz (Offset) auf beiden Seiten, Stellung 0.
- **Schräge Achse** (Manuel, P-2026-09-26-65; Abschnitt 7c): erst der
  Eintrag in „Maschine bearbeiten“ für selbst gebaute Baugruppen, danach
  eine Vorlage mit Eingabemaske. Der Winkel wird eingetragen, und die
  Baugruppe folgt (die Führung dreht sich, der Revolver bleibt gerade).
  „Maschine verfahren“ zeigt dann zuerst „wie im Programm“. **Keine
  Auswahl der Steuerung:** Die Steuerung steckt schon im Postprozessor
  (Manuel: „Man hat doch einen Postprozessor“), und für die schräge Achse
  braucht sie niemand – das Programm bleibt rechtwinklig. Die Hilfe nennt,
  wo der Winkel bei Siemens und Fanuc steht; braucht das Addon später etwas
  Steuerungsabhängiges, liest es den Postprozessor der Maschine, statt
  doppelt zu fragen.
- **Neue Maschine** (Manuel, P-2026-09-26-75; Stufe 3b, Schritt 7): ein
  eigener Befehl „Neue Maschine …“ in der Werkzeugleiste – Bauart wählen,
  darunter die Maße; „Beispielmaschine laden …“ öffnet denselben Dialog.
  Maße zum Eintragen zuerst nur für die Drehmaschine (Name, Bettneigung,
  Y-Winkel, Wege X/Y/Z, Revolverplätze, Höchstdrehzahl); die Fräsen bleiben
  feste Beispiele, bis jemand Maße braucht. Nach dem Bauen öffnet sich
  „Maschine bearbeiten“.
- **X und Z der Drehmaschine zählen wie an der Maschine** (Manuel,
  2026-09-30: „bei MEINER maschine ... ist x 0 genau die MITTE von der Vdi
  aufnahme“, P-2026-09-30-50): bis zum Bezugspunkt des Revolvers, der Mitte
  der VDI-Aufnahme in Arbeitsstellung an ihrer Stirn (P1). X ab der
  Spindelachse als Radius, Z ab der Spindelnase, Y ab der Mitte der Spindel –
  so zählen die meisten Drehmaschinen im Maschinen-Koordinatensystem. Die
  Gelenke von X und Z stehen gebaut nicht auf 0, sondern auf 275 bzw. 220
  (`gelenk_wie_gebaut(…, stellung=…)`); liegt das außerhalb der eingetragenen
  Wege, fährt die Maschine hinein. Vorgabe X −25 … 425, Z 0 … 520 – dieselben
  Wege wie vorher (−300 … 150, −220 … 300 ab der gebauten Stellung). Die
  Wege lassen sich bis 10 m eintragen (P-2026-09-30-46). Die Steuerung
  zeigt X oft als Durchmesser – dazu der nächste Punkt.
- **X im Durchmesser oder Radius** (Manuel, 2026-09-30, auf „X als Durchmesser
  eintragen und anzeigen, wie deine Steuerung?“: „Ja mit Umschalter wichtig
  ist ja nur was dann beim Postprozess raus kommt“, P-2026-09-30-54). Die
  Betriebsart einer Linearachse hat den Kennwert **„zählt im Durchmesser
  (Ø)“** (`Durchmesser`, an/aus; `maschine.ist_durchmesser`). Ist er an,
  zeigt das Addon die Stellung dieser Achse überall doppelt mit „Ø“ davor:
  Verfahrweg in „Maschine bearbeiten“ samt grauem Satz, „Maschine verfahren“
  (auch „wie im Programm“), Prüffenster, Abspieler, Kollision. X im Programm
  ebenso, wenn die Achse im Programm X heißt (`maschine.x_im_durchmesser`).
  Eingetippt wird dann auch der Durchmesser. Gerechnet und gespeichert wird
  immer im Radius – Grenzen der Gelenke, Bahnen, Kinematik. „Neue Maschine“
  hat für die Drehmaschine „X als: Durchmesser (Ø) / Radius“, vorgewählt
  Durchmesser, wie Siemens, Fanuc und Haas von Haus aus zählen (E4 in
  `spezifikation_steuerung.md`); die X-Wege zählen genauso, beim Umschalten
  rechnen die Felder um. Der Postprozessor des Addons (W-005) schreibt X
  danach. FreeCADs eigene Postprozessoren kennen den Kennwert nicht und
  schreiben den Radius – das sagt der graue Satz im 4-Achs-Assistenten. Ältere
  Maschinen bekommen den Kennwert beim Laden, ausgeschaltet.
- **Revolverart, Scheiben-Ø und VDI-Größe in „Neue Maschine“** (Manuel,
  2026-09-30: „1 ja“, P-2026-09-30-52). **VDI in der Stirn** (axial, wie
  Manuels Scheibenrevolver): die Aufnahmen im Kreis an der Stirn, 40 mm
  innerhalb des Rands; am Umfang nichts – die angedeuteten Stationen dort
  (D-46) stießen an Manuels Teil an, die gibt es an so einem Revolver nicht.
  **VDI am Umfang** (radial, Sternrevolver): die Aufnahmen auf dem Rand,
  radial; ein gerader Halter steht radial, ein gewinkelter zeigt zum Futter
  (X des LCS: dorthin kippt ein gewinkelter Halter, `halter.lage`) – Manuel:
  „wo der winkel kopf dafür da ist vorne sozusagen paralel zur maschinen z
  achse zu fräsen“. Der Bezugspunkt ist bei beiden die Achse der Aufnahme an
  ihrer Stirn (wo der Halter anliegt); gebaut steht der Sternrevolver bei
  X 225 und Z 285 (Scheibe Ø 340). Scheiben-Ø 240 … 600 mm, VDI 20 … 60. Der
  gelbe Satz „nicht radial“ rät zum geraden Halter, wo die Aufnahme selbst
  radial steht.
