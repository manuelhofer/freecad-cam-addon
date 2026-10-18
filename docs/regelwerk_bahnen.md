# Regelwerk: Wie eine Bahn gefunden wird

Manuel, 2026-10-18: „Kannst du mir für die Bahn Findung ein Regelwerk aufschreiben nach dem du
arbeitest“. Das hier ist die kurze Fassung: was gilt, in welcher Reihenfolge, woher es kommt und
wo es gebaut ist. Die Herleitungen, Messungen und Entscheidungen stehen in
[spezifikation_strategien.md](spezifikation_strategien.md) (Abschnitt 5 „Grundsätze“ und 12–14)
und [spezifikation_vierachs.md](spezifikation_vierachs.md). Widerspricht etwas hier einer
späteren Entscheidung von Manuel, gilt die Entscheidung – und diese Datei wird nachgezogen.

## 0. Die Rangfolge

Jede Bahn muss die Fragen in dieser Reihenfolge bestehen. Eine spätere Frage entscheidet nur
zwischen den Bahnen, die die früheren bestanden haben.

1. **Sicher:** nie ins Teil, nie im Eilgang ins Material, keine Kollision von Halter und
   Spindel, alles in der Reichweite der Maschine, Abstand zu Futter und Spannmitteln.
2. **Das Teil wird wie gezeichnet:** Die letzte Bahn an jeder Fläche folgt der Zeichnung
   (Bögen als G2/G3, Böden ohne Aufmaß, Bohrungen im Maß, Freiform in der Grathöhe).
   Näherungen gibt es nur beim Schruppen und nur hinter dem Aufmaß. Manuel, 2026-10-03: „die
   Werkzeugwege müssen SINNVOLL und SCHNELL sein, aber sie müssen natürlich auch das Bauteil
   abbilden“.
3. **Die Last bleibt im Einsatz:** ae, ap, vc, fz und der Eintauchwinkel des Werkzeugs sind die
   Grenze (Abschnitt 3 unten).
4. **Am schnellsten:** Unter allem, was 1–3 besteht, gewinnt die kürzeste Zeit (Grundsatz 0).
   Manuel, 2026-10-01: „immer den schnellsten Weg für das gewählte Werkzeug finden … immer die
   schnellste Strategie“.

## 1. Was überhaupt gefräst wird

- **Nur wo Material steht.** Die Aufgabe ergibt sich aus den gewählten Flächen, dem Rohteil und
  dem Materialstand. Jede Operation weiß, was die Operationen davor gelassen haben
  (`materialstand`, `restmaterial`). Was schon weg ist, wird nicht noch einmal gefahren.
- **Fertigmaß im Rohteil: nichts tun.** Hat das Rohteil an einer Fläche schon das Fertigmaß
  (Rundmaterial Ø 60 am Ø-60-Mantel, ein Quader ohne Aufmaß an der Seite), fährt dort niemand
  mehr drüber. Manuel, 2026-10-18: „wenn rohteil schon fertigteil durchmesser hat ... dann muss
  man da auch nimmer drüber juckeln“ (`gui_bearbeitung.wand_ohne_rohteil`).
- **Was der Schaftfräser kann, macht er zuerst:** ebene Flächen und die Nase vor dem Schruppen.
  Danach wissen Schruppen und Schlichten, was weg ist (Manuel, 2026-10-12).
- **Großer Fräser zuerst, Enges dem kleineren.** Kommt die Mitte des Fräsers in ein Gebiet nur
  durch eine Engstelle schmaler als 2 D, lässt das Räumen es aus, und „Rest räumen“ nimmt es mit
  dem größten Fräser, der bequem hineinkommt – von außen in Wellen, nur dieses Gebiet. Manuel,
  2026-10-18: „Ja, dort der kleinere“ (`raeumen_bahn._eng_von_aussen`).
- **Von vorn, was zur Stirn offen ist.** Schlitze, Bohrungen und Nuten, die zur Stirnseite
  offen sind, fräst der axiale Fräser von vorn, nicht radial durch die Schlitze. Manuel,
  2026-10-18: „das bearbeitet man doch von vorne ;)“ (W-033).
- **Schruppen – messen – schlichten.** Räumen mit Aufmaß an den Wänden, auf Wunsch ein
  Messstopp, dann „Schlichten danach“. Sind Böden und Wände bis zur Unterkante gewählt, räumt
  das Räumen über alles von der Rohteilkante her; die Kontur schruppt diese Wände nicht noch
  einmal (Spezifikation 12.4, W-033/W-034).
- **Vorschlichten nur, wo nötig.** Nur wo die Kugel nach dem Schruppen viel nähme, mit
  derselben Kugel auf 0,3 mm. Ein kleinerer Fräser als die Kugel ist „quatsch“ (Manuel,
  2026-10-12, W-031).

## 2. Welche Strategie: Wettbewerb nach Zeit

- Alle Strategien, die die Aufgabe lösen, rechnen mit demselben Werkzeug und demselben
  Zeitmodell (Vorschub aus dem Einsatz, Eilgang, Beschleunigung, Halt an Ecken). Der Haken kommt
  an die schnellste, die anderen stehen mit ihrer Zeit daneben. Keine Strategie wird gewählt,
  weil sie üblich ist.
- Innerhalb einer Strategie ebenso: Zeilenrichtung, Startstelle, Lagen, Einstieg, von innen oder
  von außen. Gerechnet wird jede Variante, genommen wird die schnellste.
- **Was das Addon ohne Vorgabe wählt, ändere ich nicht allein.** Eine neue Strategie zeige ich
  zuerst als Bild mit Zahlen; gebaut wird nach Manuels Ja.
- **Verbesserungen kommen als Haken, vorbelegt an**, damit man sie abschalten kann.

## 3. Last: wie viel der Fräser nehmen darf

- **ae ist die Last im Mittel**, nicht ein Schritt nach Zahl: dauernd bis 25 % mehr, kurz beim
  Einfahren bis 1,7 ae, und nie über r – der Fräser umschlingt das Material höchstens zur Hälfte
  (Manuel, 2026-10-02, Spezifikation 12.1). Weniger geht immer.
- **Nie in voller Breite**, außer in einer Nut, die genau so breit ist wie der Fräser. Der
  Prüfstand meldet mehr als 5 mm in voller Breite.
- **Volle Schneide statt vieler dünner Lagen.** Die Lagen sind gleich tief bis zum tiefsten
  Punkt: lieber 2 × 10 als 15 + 5 (Manuel, 2026-10-12: „2 × 10 braucht dieselbe Zeit und schont
  die Last“).
- **Ecken und enge Bögen:** An scharfen Ecken zur Materialseite fährt die Bahn Bögen um die
  Sichel, statt sie auf einmal zu nehmen. In engen Bögen weg vom Material fährt sie langsamer, so
  dass die Last bei 1,25 ae bleibt (Spezifikation 14.1, Punkte 6 und 7).

## 4. Einfahren

In dieser Reihenfolge (Manuel, 2026-10-12: Zickzack „nur da und sonst nirgends … wobei selbst da
würde ich wenns irgendwie geht auf eine helix setzten“):

1. **Von außen, aus der Luft, mit vollem ap:** senkrecht in der Luft hinab, dann seitlich
   hinein – vor der Stange, neben dem Rohteil, wo das Schruppen schon geräumt hat.
2. **Helix:** wo es geschlossen ist und ein Kreis Platz hat, der größer als der Fräser ist.
3. **Zickzack-Rampe:** nur in einer geschlossenen Nut, die für eine Helix zu schmal ist.

Dazu: An Wände **tangential** heran und weg (Bogen und Gerade), nie senkrecht in die Wand. Nach
der Helix nie durch ungebohrtes Material in voller Breite – dann gilt dort noch die Rampe.

## 5. Keine Luft (Grundsatz 5)

Manuel, 2026-10-18: „wenn der fräser ... in der luft fährt .. ist das dumm .. darum wollen wir
das nicht !!!!! … keine luftfahrten wenn luftfahren solten die schnell passeieren !!!“ Diese
Regel gilt für jede Strategie. Luft wird ohne Rückfrage beseitigt.

- **Kein Arbeitsvorschub durch die Luft.** Freie Stücke ab 5 mm fahren mit dem Freivorschub der
  Maschine (G1, kein G0, weil ein G0 auf vielen Steuerungen keine Gerade fährt). Die letzten 2 mm
  vor dem Material bleiben langsam (`freiwege`).
- **Hinab im Eilgang bis knapp über das Material**, nicht im Vorschub von der Sicherheitshöhe:
  - 3 Achsen: bis 2 mm über das höchste Material unter der Stirn (`freiwege`).
  - 4 Achsen vor der Stirn der Stange: ganz hinab, dort ist alles Luft.
  - 4 Achsen über dem Teil beim Schlichten: bis zur Sicherheit über den Rest nach dem Schruppen
    (`vierachs_bahn._vor_der_stange_hinab`, `_ueber_dem_rest_hinab`, 0.268.2).
- **Unten bleiben statt abheben**, wenn der Weg hinüber frei ist. Sonst nur 2 mm über das
  höchste Material im Umkreis abheben, nicht bis zur Sicherheitshöhe. Beides nur ganz über dem
  Rohteil, denn daneben können Spannmittel stehen.
- **Keine Lage und keine Zeile, die nichts nimmt:** Folgelagen nur, wo die Lage davor noch etwas
  stehen ließ. Rest-Strategien nehmen nur den Rest.

## 6. Fahrtrichtung

- **Gleichlauf** ist die Vorgabe, Gegenlauf ist wählbar. Gerechnet wird aus der Bewegung an der
  Schneide, nicht aus S allein: Bei M3 liegt das Material von der Spindel aus rechts der Fahrt
  (`spindel.ist_gleichlauf`). Das gilt für jede Maschine, mit M4 gespiegelt, und auch rundum,
  wo die Rundachse die Fahrt macht.
- **Bögen statt Ecken**, zwischen Zeilen und an Umkehrpunkten. Die Ausgabe ist G2/G3, wo die
  Steuerung es kann.
- **Nicht im Kreis durch die Luft drehen:** Für eine Fläche lieber zurückdrehen und Zeilen hin
  und her fahren als rundum im Eilgang (Manuel, 2026-09-30: „man kann ja auch einfach zurück
  drehen“).

## 7. Rundum (4 Achsen)

- **Spirale**, solange rundum Material steht. Steht in einer Lage nur noch in Sektoren etwas
  (höchstens die Hälfte des Umfangs), fährt die Lage Zeilen nur in den Sektoren. Ein Sektor, der
  vorn offen ist, wird wie eine offene Nut in D-Bögen von vorn aus der Luft gefahren (Manuel,
  2026-10-18: „ausen ist doch frei“).
- **Einer Wendelnut nach**, wenn das Teil eine hat: Bahn neben Bahn mit ihrer Steigung, C dreht
  immer in dieselbe Richtung (W-030).
- **In einer Stellung, was zusammen geht:** An der Nase fräst der radiale Schaftfräser die Fläche
  zur Drehmitte mit seiner Stirn und die Stirnseite der Welle daneben mit seinem Umfang – Züge quer
  in Y, je höchstens ap und ae aus seinen Schnittwerten, hinein neben dem Material. Muss er dafür
  weiter heraus, sagt der Assistent gelb, wie weit (Manuel, 2026-10-18: „So bauen, mit
  Ausspann-Hinweis“; `vierachs_stirnkombi`).
- **Die Drehrichtung von C an der Maschine macht nur der Postprozessor.** Stimmt die Bahn in
  FreeCAD, wird nur die Ausgabe geändert, nie Modell oder Bahn (Manuels CLX550: +C nach DIN).

## 8. Genau genug

- **Grathöhe statt Schrittweite:** Schlichten fragt „wie glatt“, die Schrittweite folgt aus
  Fräserform und Neigung.
- **Punkte nach Sehnenfehler:** Punkte werden zusammengefasst, solange die Toleranz hält. Kein
  Zappeln: An Facetten des Netzes entsteht kein Satz je Grad.

## 9. Wie ich prüfe, dass die Regeln halten

- **Prüfstand** (`pruefstand.py`): Jede Strategie wird an den Maßstabsteilen Satz für Satz im
  Quader abgefahren. Eine Bahn fällt durch, wenn sie ins Teil schneidet, etwas stehen lässt, im
  Eilgang abträgt, zu viel Luft fährt oder zu lange in voller Breite fräst. Keine Bahn darf
  langsamer werden als ihre Bestmarke.
- **Szenarien** spielen den Assistenten durch und schreiben je Operation, wie oft gekehrt und
  wie oft rampt wird (`kehren.txt`). An Manuels Teilen suche ich im Programm nach Zickzack,
  Vorschub durch die Luft (F mitgezählt), F0 und doppelten Sätzen.
- **Maßstab** sind Manuels Teile: die Platte, das Testteil 3-Achs, der C-Ring, die Nase, der
  Geist (STL), der Ring aus drei Segmenten.
- **Was ich nicht gesehen habe, nenne ich nicht „funktioniert“.** Ob ein Dialog verständlich
  ist, prüft Manuel.

## 10. Rechnen

- **Alle Kerne:** Varianten, Vorschauen, Hüllen und Kollisionen rechnen auf den Nebenrechnern,
  einer je Kern. Das Fenster darf dabei nie hängen.

## Offen (Stand 2026-10-18)

- Zickzack: Einige Stellen können die Einfahr-Regel noch verletzen und werden durchgesehen –
  die Einfahrten der 4-Achs-Zeilen, „Plan indexiert“ auf schrägen Flächen, die Mantelnut ohne
  Helix-Prüfung, der Anlauf beim Schlichten und kurze Läufe der Kontur (W-035).
- Alle Kerne: 3D-Schruppen (Varianten), 3D-Schlichten (Richtungen) und das Neuberechnen einer
  Operation laufen noch auf einem Kern (W-036).
