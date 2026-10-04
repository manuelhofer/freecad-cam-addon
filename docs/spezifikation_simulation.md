# Spezifikation W-001 Stufe 4: Werkzeugbahn auf der Maschine abfahren

Stand: Entwurf von Claude (P-2026-09-25-70). **Manuel hat am 2026-09-26 die
Fragen zu 4a entschieden** (Abschnitt 9, P-2026-09-26-83); 4a ist gebaut
(0.22.0). **4b hat Claude auf Manuels Wort gebaut** („bau das mit der
Maschine“, 2026-09-26; 0.23.0) – die Entscheidungen darin sind Claudes und
stehen zur Besprechung (Abschnitt 5, 4b). **Zu 4c hat Manuel am 2026-09-26
entschieden** (Abschnitt 9, Fragen 4, 5, 7, 8): eigene Halter-Verwaltung
([spezifikation_halter.md](spezifikation_halter.md)), geprüft gegen das
fertige Teil und die Spannmittel, gemeldet werden Berührung und Warnabstand;
4c ist gebaut (0.24.0). 4d bleibt Entwurf.

Grundlage: [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
(Stufen 1–3: Maschine beschreiben, an CAM übergeben, von Hand verfahren; 3b:
schräge Achse).

## 1. Zielbild

Der CAM-Job ist fertig. Bevor das Programm an die Maschine geht, will man
wissen:

1. **Reicht der Verfahrweg?** Bleibt jede Achse in ihren Grenzen – oder
   fährt X1 in *Tasche* auf 212 mm, obwohl bei 200 Schluss ist?
2. **Wie sieht das auf der Maschine aus?** Die Maschine aus Stufe 3 fährt
   die Bahn ab, mit Werkzeug und Werkstück, Schritt für Schritt oder am
   Stück.
3. **Stößt etwas an?** Spindelkopf gegen Schraubstock, Werkzeughalter gegen
   Werkstück, Schlitten gegen Schlitten.
4. **Wie lange dauert es wirklich?** Mit Eilgang, Vorschubgrenzen und
   Beschleunigung aus W-001 statt nur Weg durch Vorschub.

Was FreeCAD schon kann und das Addon **nicht** nachbaut: den Materialabtrag
(CAM-Simulator) und die Prüfung der Bahn gegen das Modell (Sanity-Check).

## 2. Was es schon gibt

| Baustein | Wo | Nutzen |
| --- | --- | --- |
| Maschine mit Achsen, Grenzen, Kennwerten, Aufnahmen | W-001 Stufen 1–2 (`maschine.py`, `kette.py`) | Kinematik, Grenzen, Eilgang, Beschleunigung |
| Achsen verfahren | W-001 Stufe 3 (`verfahren.py`) | die Maschine in jede Stellung bringen; Revolverplätze in Arbeitsstellung |
| Schräge Achse | W-001 Stufe 3b (`schraege_achse.py`) | Höchstvorschub; dieselben Zahlen wie „wie im Programm“ |
| Bahn der Operationen | CAM: `op.Path.Commands` (G0/G1/G2/G3 mit X Y Z, bei 4. Achse A/B/C) – so, wie der Postprozessor sie liest | was abgefahren wird |
| Werkzeug je Operation | Werkzeug-Controller → ToolBit mit Durchmesser, Länge, Schaft; das Werkzeug der Werkzeugverwaltung dazu (`job_schnittwerte.werkzeug_von`) | Werkzeuglänge, Werkzeug als Körper |
| Rohteil und Modell | `job.Stock`, `job.Model` | Vorschlag für den Nullpunkt; Werkstück als Körper |
| Materialabtrag | CAM-Simulator (`SimulatorGL`) | bleibt, wie er ist |

## 3. Begriffe

- **Bahnpunkt** – ein Punkt der Werkzeugbahn in den Koordinaten des Jobs,
  dazu bei 4/5-Achsbahnen die Winkel A/B/C.
- **Werkstücknullpunkt** – wo der Nullpunkt des Jobs auf der Maschine liegt:
  am LCS der Werkstückaufnahme, verschoben um den **Nullpunkt des Jobs** (wie
  G54), gemessen in den Achsen dieses LCS. **Das LCS ist das
  Koordinatensystem des Jobs:** Z aus der Spannfläche heraus, X so, wie X im
  Job zum eingespannten Teil liegt – auf der Drehmaschine von der
  Spindelachse zum Werkzeug hin.
- **Werkzeugspitze** – der Ursprung der Werkzeugaufnahme (ihr LCS), um die
  Länge ab Spindelnase gegen die Z-Achse des LCS versetzt. Die Z-Achse einer
  Werkzeugaufnahme zeigt von der Spitze zur Aufnahme – wie +Z der Maschine,
  das das Werkzeug vom Werkstück wegfährt.
- **Länge ab Spindelnase** – von der Werkzeugaufnahme (Spindelnase, Platz
  im Revolver) bis zur Spitze, mit Halter; so, wie sie das Voreinstellgerät
  misst.
- **Achsstellungen** – die Werte aller Achsen, bei denen die Werkzeugspitze
  (relativ zum Werkstück) auf dem Bahnpunkt steht; gezählt wie im Fenster
  „Maschine verfahren“ und wie die Grenzen am Gelenk.

## 4. Achsstellungen aus der Bahn

Die Bahn beschreibt, wo die Werkzeugspitze **relativ zum Werkstück** sein
soll. Die Maschine erreicht das, indem Achsen im Tisch das Werkstück und
Achsen im Kopf das Werkzeug bewegen. Gerechnet wird wie beim Verfahren
(Stufe 3) – die Lage jedes Glieds ist das Produkt der Achsbewegungen vom Bett
nach außen –, aber ohne die Bauteile zu bewegen.

- **Drehachsen zuerst:** Rundachsen stehen, wie die Bahn sagt – A, B und C
  über ihren Namen im Programm (NC-Name ohne Ziffern am Ende: C1 → C), ohne
  Angabe auf 0. Der **Revolver** steht mit dem Platz des Werkzeugs (T3 → P3)
  in Arbeitsstellung, dort, wo P1 beim Öffnen stand. Spindeln ohne
  Betriebsart „Positionieren“ bleiben, wie sie stehen – sie drehen das
  Werkzeug um seine eigene Achse.
- **Dann die Linearachsen – wie an einer Steuerung ohne TCPM** (W-003 V3e,
  P-2026-09-27-54): X, Y und Z der Bahn sind die Achsen der Maschine. Die
  Linearachsen stehen so, als stünden die Rundachsen auf 0 (der Revolver in
  Arbeitsstellung); die Rundachsen drehen das Werkstück darunter. So zeigt
  FreeCAD die Bahn (`PathSegmentWalker`: der Punkt um −C gedreht) – bis V3e
  rechnete die Prüfung die Punkte am mitgedrehten Werkstück (wie mit TCPM),
  und eine Bahn rundum hätte die Linearachsen mit C kreisen lassen. Stehen
  die Drehachsen auf 0, hängt der Abstand zwischen Werkzeugspitze und
  Bahnpunkt linear an den Wegen der Linearachsen zwischen Werkzeug- und
  Werkstückaufnahme – drei Gleichungen, einmal gelöst je Werkzeug. Das
  gilt für Tisch- und Kopfachsen, für schiefe Achsen und für die **schräge
  Achse** (Stufe 3b): Die Bahn ist rechtwinklig, die Lösung liefert die
  Stellungen der Schlitten – dieselben Zahlen wie beim Verfahren „wie im
  Programm“ (`schraege_achse.Programm`). Geprüft werden die Grenzen der
  Schlitten; die Meldung nennt beides, den Punkt im Programm und den
  Schlitten: „X 140, Y −40 in *Kontur* braucht X1 = 163 mm, die Grenze ist
  150 mm“ (bei 30°).
- **Weniger als drei Linearachsen** (Drehmaschine ohne Y): Punkte außerhalb
  der Ebene, in der das Werkzeug fahren kann, meldet die Prüfung als nicht
  erreichbar. **Mehr als drei** (Pinole und Z): meldet sie als noch nicht
  prüfbar.
- **Welche Punkte:** die Enden von G0 und G1; Kreise (G2/G3, auch als
  Schraube) zusätzlich genau dort, wo eine Achse umkehrt; Bohrzyklen (G73,
  G81 … G89) über dem Loch, auf der R-Ebene und auf dem Grund. Ändert sich
  eine Rundachse im Satz, kommt alle 1° ein Punkt dazu. Rundachsen werden
  gegen ihre Grenzen gehalten, wenn sie nicht endlos sind.
- Für 4d gilt der Höchstvorschub der schrägen Achse
  (`schraege_achse.hoechstwert`).

## 5. Stufen

**4a – Reichweite prüfen** (zuerst, weil schnell und sofort nützlich) – in
vier Schritten:

1. **Rechenkern** (`reichweite.py`, ohne Oberfläche): für einen Job die
   Achsstellungen aller Bahnpunkte (Abschnitt 4); je Achse der gebrauchte
   Bereich; je Operation und Achse die größte Überschreitung mit dem Punkt im
   Programm und allen Achsstellungen dort; Hinweise in Sätzen – Länge des
   Werkzeugs angenommen, Platz fehlt am Revolver, Punkt nicht erreichbar,
   Z-Achse einer Werkzeugaufnahme zeigt zum Werkstück, Befehl übergangen.
   Dazu: Beispiel-Drehmaschine mit X des LCS am Futter wie X der Maschine;
   Hilfe „Aufnahmen“ mit den Richtungen der LCS wie in Abschnitt 3.
   *Gebaut (P-2026-09-26-84).*
2. **Fenster „Auf der Maschine prüfen“** (Abschnitt 6) mit Befehl, Hilfe
   und Szenario. *Gebaut (P-2026-09-26-85).*
3. **Länge ab Spindelnase** als Feld der Werkzeugverwaltung (alle Arten,
   leer gilt die Gesamtlänge); die Prüfung findet das Werkzeug zum
   Werkzeug-Controller wie „Schnittwerte in den Job“, sonst gilt die Länge
   des CAM-Werkzeugs – mit Hinweis. *Gebaut (P-2026-09-26-86).*
4. Version, voller Lauf, Push.

**4b – Abfahren** – die Maschine fährt die Bahn des Jobs sichtbar ab.
Entscheidungen von Claude (P-2026-09-26-88), zur Besprechung:

- **Nichts im Dokument:** Werkzeug, Rohteil, Modell und Bahn sind Körper nur
  in der 3D-Ansicht der Maschine (Coin-Knoten). Nichts wird ins Dokument
  geschrieben; Schließen räumt sie weg und fährt die Maschine zurück.
- **Werkzeug** an der Werkzeugaufnahme, als Zylinder: die Schneide
  (Durchmesser, Schneidenlänge – leer 2 × D; beim Nutenfräser die
  Schneidenbreite, beim Lollipopfräser eine Kugel, der Hals ab ihrer Mitte –
  P-2026-09-27-02) an der Spitze, darüber Hals und Schaft
  (Schaft-Ø, bis zur Gesamtlänge). Reicht die Länge ab Spindelnase weiter,
  steht dazwischen der **Halter angedeutet** – durchscheinend, Ø 2 × Schaft,
  mindestens 25 mm –, bis Frage 4 (Halter) entschieden ist. Die Maße kommen
  aus der Werkzeugverwaltung, sonst vom CAM-Werkzeug.
- **Werkstück** an der Werkstückaufnahme, wo der Nullpunkt des Jobs liegt:
  das Rohteil durchscheinend, das Modell fest, dazu die **Bahn** als Linie
  (Vorschub blau, Eilgang rot). Alles fährt mit dem Tisch mit. Mit
  Rundachsen liegt die Bahn am Werkstück – jeder Punkt um die Rundachsen
  gedreht, wie ihn FreeCAD zeigt (W-003 V3e, P-2026-09-27-54).
- **Zeit:** Vorschubsätze mit F aus der Bahn (FreeCAD: mm/s); fehlt F (0),
  gilt 1000 mm/min, und ein Hinweis sagt es. Zwischen G93 und G94 ist F der
  Kehrwert der Zeit: ein Satz dauert 1 ÷ F Minuten (W-003 V3e,
  P-2026-09-27-54). Eilgang: jede Achse mit ihrem
  Eilgang aus der Maschine (fehlt er: 10 000 mm/min wie bei der Übergabe an
  CAM), die langsamste bestimmt. Dazu die Beschleunigung (4d, unten).
- **Punkte:** wie in 4a, dazu Kreise in Schritten von höchstens 5° und der
  Rückzug nach einem Bohrzyklus; dazwischen fährt die Maschine geradlinig in
  ihren Achsen. Auf Kreisen auch die Umkehrstellen der Achsen, an denen 4a
  misst – so ist jede Überschreitung eine Station (P-2026-09-26-90).
- Ein Vorschubsatz ist nie schneller als der Eilgang der Achsen: Schwenkt
  der Revolver zwischen zwei Operationen in einem Satz ohne Weg, kostet das
  trotzdem seine Zeit (P-2026-09-26-90).
- **Bedienung:** Operation (springt an ihren Anfang), |◀ (Anfang), ◀ (ein
  Punkt zurück), ▶/❚❚ (Abspielen/Anhalten), ▶ (ein Punkt vor), Tempo ×1, ×5,
  ×20, ×100, ein Schieber über die ganze Zeit. Darunter: Operation, Satz n von
  m, Zeit t von T und die Stellung jeder Achse. Der Satz ist der, der gerade
  läuft (zwischen zwei Punkten der des zweiten); vor und zurück gehen von
  Punkt zu Punkt, auch wenn zwei dieselbe Zeit haben. Die Achsen stehen
  Linearachsen zuerst, nach Namen (P-2026-09-26-90). Eine Lupe holt
  Werkstück und Werkzeug in der Ansicht heran – die Maschine ist meist viel
  größer als das Teil (P-2026-09-26-92).
- **Anschlag:** Die Maschine fährt nie über ihre Grenzen. Müsste eine Achse
  weiter, bleibt sie an der Grenze stehen, ihr Wert steht rot da („am
  Anschlag“), die Bahn läuft weiter. Punkte, die die Linearachsen gar nicht
  erreichen, lassen die Maschine stehen, die Anzeige sagt es.
- Ein Klick auf eine Überschreitung (4a) stellt auch den Abspieler auf diese
  Stelle.

In drei Schritten:
1. **Rechenkern** (`abfahren.py`, ohne Oberfläche): aus der Bahn die
   Stationen – Zeit, Operation, Satz, Punkt, Stellungen –, die Stellungen zu
   jeder Zeit (zwischen zwei Stationen geradlinig). Prüfungen: Zeiten gegen
   Handrechnung, Kreise, Bohrzyklus, Rundachsen. *Gebaut (P-2026-09-26-89).*
2. **Anzeige und Abspieler** im Fenster „Auf der Maschine prüfen“, Hilfe,
   Szenario mit Screenshots. *Gebaut (P-2026-09-26-90): `gui_abfahren.py`,
   `tests/gui/szenario_abfahren.py`.*
3. Version, voller Lauf, Push. *Gebaut (P-2026-09-26-91, 0.23.0).*

**4c – Kollision** – die Maschine fährt die Bahn ab, und nichts stößt an.
Manuels Entscheidungen (2026-09-26): Halter aus der eigenen Halter-Verwaltung,
geprüft gegen das fertige Teil und die Spannmittel, gemeldet Berührung und
Warnabstand. Rechenweg und Einzelheiten von Claude (P-2026-09-26-93), zur
Besprechung:

- **Was gegen was:**
  - Das **Werkzeug** – Schneide, Schaft, Halter – gegen das **fertige Teil**
    (die Modelle des Jobs): Schaft und Halter immer, die Schneide im
    Eilgang (im Vorschub schneidet sie, das ist gewollt). Beginnt ein
    Eilgang dort, wo ein Vorschub aufhörte, zählt sie erst, wenn sie dem
    Teil näher kommt als dort – so endet jede Tasche: am Boden, dann im
    Eilgang hoch; bis P-2026-09-27-51 stand das rot als Berührung da. Seit
    P-2026-09-27-41 auch im Vorschub, wenn sie mehr als 0,05 mm ins fertige
    Teil fährt – ihr Kern (die Schneide, um 0,05 mm kleiner) darf das Teil
    nicht berühren; außer beim Entgraten, Gravieren, Gewinde und Bohren
    (Manuels Test 2026-09-27: ein radiales Werkzeug fuhr eine Bahn für eines
    längs Z quer durchs Teil, und nichts wurde gemeldet).
  - Das Werkzeug gegen alle Maschinenteile, die nicht mit ihm fahren:
    Spannmittel, Tisch, Futter (die Werkstückseite), das Bett und alles
    andere.
  - Die **Maschinenteile, die mit dem Werkzeug fahren** (Spindelkopf,
    Schlitten, Revolver), gegen die Werkstückseite und das Teil.
  - Nicht geprüft: das Rohteil (das Addon trägt kein Material ab – dafür
    gibt es den CAM-Simulator); Teile, die zusammen fahren; Paare, die sich
    schon in der Grundstellung berühren (Führungen) – ein Hinweis nennt sie.
  - **Eilgang durchs Rohteil (P-2026-10-04-17, zur Bestätigung durch Manuel):** Seit es den
    Abtrag im Quader gibt (W-006 S3d), fährt „Kollision prüfen“ ihn der Reihe nach mit
    (`restmaterial.QuaderAbtrag.eilgaenge_ins_material`): Nimmt ein Eilgang mit der Form seines
    Fräsers mehr als 0,1 mm Rohteil weg, das dort noch steht, ist das eine Berührung („… fährt
    die Schneide von T1 im Eilgang durch Rohteil, das dort noch steht – bis … tief“). Der
    Vorschub zählt nicht – kein Fehlalarm in einer gefrästen Tasche (Entscheidung 7). Für Jobs,
    deren Abtrag geht: der Kasten (Werkzeuge von oben, keine Rundachse) und seit P-2026-10-04-18
    die Stange eines 4-Achs-Jobs (`Abtrag.eilgaenge_ins_material`); 3+2 bleibt ohne. Am Testteil,
    am Schwenkteil und an der Welle (Rundum schruppen): keiner; ein eingeschleuster Eilgang quer
    durchs Rohteil, Schnitte in der Stange als Eilgang: gefunden.
- **Melden:** Berührung – Abstand 0 oder ineinander – rot; näher als der
  **Warnabstand** gelb. Der Warnabstand ist 1 mm und im Fenster einstellbar.
- **Wie gerechnet wird:** Werkzeug und Halter als Drehkörper, Maschinenteile
  und Teil als ihre Formen aus dem Dokument, jeweils an ihre Lage zur Zeit t
  gesetzt; den Abstand rechnet OpenCascade (`distToShape`; es erkennt auch,
  wenn ein Körper im anderen steckt – 2 bis 3 ms je Paar, gemessen
  P-2026-09-26-93). Entlang der Bahn in Schritten, in denen sich kein Paar
  um mehr als seinen Abstand minus Warnabstand näherkommt: weit weg große
  Schritte, nah dran bis hinunter zu 0,5 mm – so rutscht keine Ecke durch.
  Wie weit sich zwei Körper gegeneinander bewegen, zählt je Paar: nur die
  Achsen, die genau einen der beiden fahren, eine Drehachse mit dem
  weitesten Abstand des Körpers von ihr (P-2026-09-27-50 – mit der Größe
  der ganzen Maschine gerechnet dauerte eine Bahn rundum, tausende Grad C,
  über 20 Minuten). Genau rechnet es ein Paar nur, wenn es vielleicht näher
  als der Warnabstand ist oder den nächsten Schritt am kürzesten macht (und
  der mit der Schranke nicht ohnehin bis zur nächsten Station reicht, seit
  P-2026-09-27-53); sonst reicht eine Schranke nach unten – der Abstand der
  Hüllquader oder der zuletzt genau gerechnete minus dem Weg seither. Ein
  Körper rund um seine Drehachse (Futter, Welle) bewegt sich mit ihr nicht;
  stecken zwei in einer Operation schon ineinander, rechnet es sie dort nicht
  weiter.
- **Ergebnis** wie 4a, je Operation und Paar das Schlimmste als Satz: „In
  „Tasche“ berührt der Halter von T3 („SK40 ER32 A70“) das Teil (Satz 12,
  bei X 50, Y 30, Z −15).“ – „In „Kontur“ kommt der Fräskopf dem
  Schraubstock auf 0,60 mm nahe (Satz 8, bei …).“ Ein Klick stellt den
  Abspieler dorthin; eine rote Kugel zeigt die Stelle in der 3D-Ansicht.
- **Auf Knopfdruck**, nicht nach jeder Änderung – es dauert Sekunden; mit
  Fortschritt und Abbrechen.
- Ein Werkzeug ohne Halter prüft es allein, ein Hinweis sagt es.

In zwei Schritten, nach der Halter-Verwaltung (spezifikation_halter.md,
Abschnitt 8):
1. **Rechenkern** (`kollision.py`, ohne Oberfläche): Körper, Paare,
   Abtastung, Ergebnis als Sätze. Prüfungen an der Beispiel-Fräse mit
   Hindernissen: der Fräskopf fährt mit einem kurzen Werkzeug in ein
   Spannmittel; der Halter taucht in eine tiefe Tasche; ein Eilgang geht
   durchs Teil; der Warnabstand. *Gebaut (P-2026-09-26-97): die Beispiel-Fräse
   trägt zwei Spanneisen (seit -98 immer, 60 mm hoch – die Spindelnase kommt
   bis 30 mm über den Tisch, so stößt sie in den Grenzen an); gemeldet
   wird als Satz mit beiden Körpern im Nominativ („In „Eigene“ berühren sich
   der Schaft von T1 und das Teil (Satz 5, bei …).“), weil sich Artikel für
   frei benannte Bauteile nicht beugen lassen.*
2. **Bereich „Kollision“** im Fenster „Auf der Maschine prüfen“, Hilfe,
   Szenario mit Screenshots; dann Version, voller Lauf, Push. *Gebaut
   (P-2026-09-26-98): Berührungen stehen vor den Warnungen; ein Klick rückt
   die Stelle in die Mitte der Ansicht (höchstens 400 mm hoch), die rote Kugel
   ist obenauf gezeichnet – sonst läge sie unter der Spindel; der Warnabstand
   wird gemerkt.*

**4e – Spitze (TCP) und TCPM** (Manuel, 2026-09-29: „x-60 ist ja unter der
drehmitte was garnicht sein kann … das x-60 ist ja nur die maschinen
koordinate .. nicht wenn nen fräser mit dabei ist .. der TCP muss schon mit
berechnet werden .. generell immer … also machs so das es auch tcp kann deine
wegberechnung .. generell solltest du die wegberechnung sehr sehr sehr extrem
gut machen .. und am besten sehr variabel so das man immer wieder neue sachen
raus machen kann“)

- **Kinematik-Kern** (`kinematik.py`, ohne Oberfläche): eine Stelle für alles,
  was Achsen und Werkzeugspitze verbindet – vorwärts (Achsstellungen → Spitze
  und Werkzeugrichtung im Job) und rückwärts (Punkt der Bahn → Achsstellungen),
  mit oder ohne TCPM, dazu wie weit die Spitze mit einem Werkzeug kommt.
  Reichweite, Abfahren, Kollision und das Bild der Bahn rechnen damit; neue
  Prüfungen und Bahnen bauen darauf auf, statt es neu zu erfinden.
- **Spitze im Abspieler:** unter den Achsen die Spitze, wie im Programm
  („Spitze: X 16,00 · Y 0,00 · Z −28,00 · C −3900,0°“). Steht eine Achse am
  Anschlag, dazu, wo die Spitze wirklich steht („steht bei X 65,00“).
- **Überschreitungen mit der Spitze:** „X1 fährt in „Rundum schruppen T1“ bis
  −109,00 mm, die Grenze ist −60,00 mm (bei X 16, …) – mit T1 kommt die
  Spitze in X nur bis 65,00 mm.“ So ist klar, dass X1 der Schlitten ist und
  wie weit das Werkzeug reicht.
- **TCPM wählbar:** Transformation „TCPM“ an der Maschine (Steuerung rechnet
  den Werkzeugmittelpunkt mit: TRAORI, RTCP, M128). Mit ihr sind X, Y, Z die
  Spitze am gedrehten Werkstück – die Linearachsen werden je Stellung der
  Rundachsen gelöst; ohne sie (Vorgabe, wie FreeCAD die Bahn zeigt) mit den
  Rundachsen auf 0.
- *Gebaut (P-2026-09-29-10):* `kinematik.py` mit `Kinematik` –
  `stellungen()` (rückwärts, wie `Pruefung.loeser`), `programm()` (vorwärts:
  wo die Spitze im Programm steht), `am_werkstueck()` (am gedrehten Teil),
  `rundachsen()`. Die Bahn im Prüffenster (`Abfahrt.am_werkstueck`), die
  Zeile „Spitze im Programm: X …, C …“ im Abspieler (rot „– soll: …“, wenn eine
  Achse am Anschlag steht) und der Satz „An der Grenze stünde die Spitze von T1
  bei X …“ an jeder Überschreitung einer Linearachse rechnen damit.
  *Zurückgestellt:* TCPM wählbar – „Rundum schruppen“ schreibt sein Programm
  für eine Steuerung ohne TCPM (X ist der Radius, die Rundachse dreht das Teil
  darunter); mit TCPM läse die Steuerung dasselbe Programm anders. Das geht erst
  zusammen mit einer Ausgabe für TCPM – Frage an Manuel, ob seine Steuerung
  TRAORI/RTCP nutzt.

**4d – Bearbeitungszeit** – gebaut (P-2026-10-01-22, `fahrzeit.py`)
- Je Satz die Zeit mit Eilgang bzw. Vorschub und der Beschleunigung der
  Achsen (Trapezprofil: anfahren, fahren, bremsen; Dreieck, wenn der Weg
  nicht reicht; Ruck bleibt außen vor). Die Übergänge wie eine Steuerung
  mit Vorausschau: durch Bögen (5°-Sehnen) und Rampen fährt die Maschine
  durch, an Ecken (Richtungswechsel ab 15°), vor und nach einem Eilgang
  (die Achsen fahren einzeln, jede vom Stand in den Stand) und am Ende hält
  sie. Vom Stand in den Stand dauert ein Satz L ÷ v + v ÷ a.
- **Feste Vorgaben** (Manuel, 2026-10-01: „Eilgang und Beschleunigung
  dauerhaft festsetzen“): Eilgang 10 m/min, Beschleunigung 1 m/s² je
  Linearachse und 1 U/s² je Rundachse (`export.VORGABE_…`) – wie eine kleine
  oder nachgerüstete Maschine; große fahren schneller, die Zeit ist dann
  eher zu lang. Sie gelten, wo die Maschine nichts sagt (Betriebsart ohne
  Eilgang oder Beschleunigung) und in der Schätzung des Assistenten
  „Bearbeitung“ (`bahn.zeit`), damit alle Strategien an denselben Werten
  gemessen werden (W-006 Abschnitt 11). Die Beispielmaschinen tragen ihre
  eigenen Werte (Fräse 20/15 m/min, 3 m/s²).
- Offen: die Summe je Operation im Fenster, FreeCADs eigene Schätzung
  daneben; die 4-Achs-Vorschau (`vierachs_bahn.dauer`) rechnet noch ohne
  Eilgang und Beschleunigung.

## 6. Oberfläche

Befehl **„Auf der Maschine prüfen“** in der Werkzeugleiste „CAM-Addon“. Ist
ein Job gewählt – in irgendeinem offenen Dokument –, gilt der; sonst die Jobs
des aktiven Dokuments, und hat das keine, die des einzigen offenen Dokuments
mit Jobs; bei mehreren fragt er, welches (Durchsicht W-004, D-21). Die
**Maschine** nimmt er aus allen offenen Dokumenten. Ist keine offen, öffnet
er die gemerkte – die Datei, auf der der Job zuletzt geprüft wurde, sonst die
zuletzt benutzte; fehlt auch die, bietet eine Meldung **Maschine öffnen …**
und **Neue Maschine …** an (D-20). Sind mehrere offen, fragt er vorher,
welche (die gemerkte zuerst, sonst die im Dokument des Jobs). Das
Aufgabenfenster öffnet sich im Dokument der Maschine, damit man sie fahren
sieht – im Wochen-Build gehört ein Aufgabenfenster zu seinem Dokument und
verschwindet beim Wechsel (ausprobiert, P-2026-09-26-85); deshalb gibt es im
Fenster keine Auswahl der Maschine:

- **Job** – die Jobs des Dokuments. Darunter die Maschine.
  **Werkstückaufnahme** – nur, wenn es mehrere gibt.
- **Nullpunkt des Jobs, von der Werkstückaufnahme aus:** X, Y, Z. Leer gilt
  der Vorschlag, grau im Feld: das Rohteil mittig auf der Aufnahme, mit der
  Unterseite auf der Spannfläche. Eingetragene Werte speichert der Job.
- **Ergebnis:** „Alle Achsen bleiben in ihren Grenzen.“ – oder je
  Überschreitung ein Satz: „X1 fährt in *Tasche* bis 312,00 mm, die Grenze
  ist 250,00 mm (bei X 450, Y 0, Z −5).“ Ein Klick fährt die Maschine
  (Stufe 3) in diese Stellung, die Achse am Anschlag. Darunter je Achse,
  was die Bahn braucht und was die Grenzen erlauben; Hinweise in Grau.
- Gerechnet wird beim Öffnen und nach jeder Änderung. **Schließen** fährt
  die Maschine zurück, wie sie beim Öffnen stand, merkt sich den Nullpunkt
  am Job und kehrt zum Dokument des Jobs zurück.

**Abfahren (4b)** ist ein eigener Bereich in diesem Fenster, unter dem
Ergebnis; Bereiche und Hinweise stehen darunter (gebaut, P-2026-09-26-90). 4c und 4d kommen als weitere
Bereiche dazu.

## 7. Grenzen dieses Entwurfs

- Kein Materialabtrag – dafür gibt es den CAM-Simulator.
- Halter rund um die Werkzeugachse (Kontur aus Zylindern und Kegeln);
  Blockhalter an Drehmaschinen nur angenähert.
- Die Kollision prüft das Werkzeug der laufenden Operation; die anderen
  Werkzeuge im Revolver fahren noch nicht mit in die Prüfung.
- Die Werkzeugspitze liegt auf der Werkzeugachse (eine Länge). Drehwerkzeuge
  mit Versatz in X und Z kommen mit einer Verwaltung für Drehwerkzeuge.
- Der Nullpunkt des Jobs ist eine reine Verschiebung, keine Drehung (G68).
- Bahnen mit Werkzeugrichtung (5-Achs-simultan) erst, wenn FreeCAD sie
  erzeugt – der Weg über A/B/C reicht für 3+2 und 4. Achse.

## 8. Prüfbarkeit

- Beispielmaschinen aus `camaddon/beispielmaschine.py` und
  `tests/beispielmaschinen.py`, dazu Jobs mit eigener Bahn: FreeCADs
  Operation „Eigene“ (Custom) nimmt G-Code als Text – in 1.1.3 und im
  Wochen-Build ausprobiert. Achsstellungen für bekannte Punkte, eine Bahn
  über die Grenze für 4a, ein zu kurzes Werkzeug neben einem hohen
  Spannmittel für 4c, Zeiten gegen Handrechnung für 4d.
- Die Oberfläche wie bisher mit Szenarien und Screenshots; ob es sich
  verständlich bedient, prüft Manuel.

## 9. Entscheidungen

1. **Was wird abgefahren?** – *Entschieden (Manuel, 2026-09-26):* die Bahn
   im Job. Sie gibt es in beiden FreeCAD-Versionen, sie braucht keinen
   Postprozessor. Das fertige NC-Programm (Zyklen, Werkzeugwechsel) kann
   eine spätere Stufe werden.
2. **Wo liegt der Werkstücknullpunkt?** – *Entschieden:* am LCS der
   Werkstückaufnahme, dazu eine Verschiebung je Job im Fenster.
3. **Werkzeuglänge** – *Entschieden:* ein eigenes Feld „Länge ab
   Spindelnase“ je Werkzeug (mit Halter, wie am Voreinstellgerät); leer gilt
   die Gesamtlänge.
4. **Halter** – *Entschieden (Manuel, 2026-09-26):* eine eigene
   Halter-Verwaltung mit Halterformen aus Zylindern und Kegeln, in einem
   eigenen Fenster aus der Werkzeugverwaltung; die Länge ab Spindelnase
   bleibt gemessen, sonst geschätzt
   ([spezifikation_halter.md](spezifikation_halter.md)).
5. **Mindestabstand** – *Entschieden:* Berührung rot und ein Warnabstand
   (vorbelegt 1 mm, einstellbar) gelb.
6. **Reihenfolge** – *Entschieden:* 4a zuerst.
7. **Wogegen prüft 4c?** Das Addon trägt kein Material ab. – *Entschieden
   (Manuel, 2026-09-26):* gegen das fertige Teil, die Spannmittel und die
   Maschine – kein Fehlalarm, wenn der Schaft in eine gefräste Tasche taucht;
   Material, das noch nicht abgetragen ist, sieht die Prüfung nicht. *Ergänzt (Claude,
   2026-10-04 nachts, zur Bestätigung):* Eilgänge durch Rohteil, das noch steht, meldet sie –
   mit dem Abtrag, also ohne Fehlalarm in gefrästen Taschen (Abschnitt 4c oben); der Vorschub
   bleibt, wie entschieden. Abschalten: `rohteil=True` in `gui_kollision`.
8. **Nach 4b** – *Entschieden:* 4c, mit der Halter-Verwaltung davor.

## 10. Akzeptanzkriterien 4a

- 3-Achs-Beispielfräse, ein Job mit einer Bahn innerhalb der Grenzen →
  „Alle Achsen bleiben in ihren Grenzen.“, darunter je Achse, was die Bahn
  braucht und was die Grenzen erlauben.
- Dieselbe Bahn weit in X verschoben → „X1 fährt in *…* bis … mm, die
  Grenze ist … mm (bei X …, Y …, Z …).“ → Klick → die Maschine steht dort,
  X1 am Anschlag. Schließen → alles steht wie vorher.
- Beispiel-Drehmaschine mit Y schräg um 30°: Eine Bahn, bei der X im
  Programm in seinen Grenzen bliebe, X1 zum Ausgleichen aber darüber müsste →
  die Meldung nennt X1 und den Punkt im Programm.
- Ein Werkzeug ohne Länge ab Spindelnase → gerechnet mit der Gesamtlänge,
  der Hinweis sagt es („ohne Halter“).
- Manuel versteht das Fenster ohne Erklärung.

## 11. Akzeptanzkriterien 4b

- 3-Achs-Beispielfräse, ein Job mit eigener Bahn: **Abspielen** – die
  Maschine fährt, das Werkzeug läuft die Bahnlinie auf dem Rohteil entlang;
  Zeit, Satz und Achswerte laufen mit. Anhalten, ein Punkt vor und zurück,
  Tempo, Operation wählen und der Schieber tun, was sie sagen.
- Eine Bahn über die Grenze von X1: Die Maschine steht dort am Anschlag, der
  Wert von X1 steht rot da; weiter hinten fährt sie wieder mit.
- Zeiten: 100 mm mit F 10 (600 mm/min) dauern 10 s; ein Eilgang von 100 mm
  in X1 mit 30 000 mm/min 0,2 s.
- Schließen: Die Maschine steht wie vorher, in der Ansicht ist nichts mehr
  vom Werkzeug oder Werkstück, im Dokument nichts geändert.

## 12. Akzeptanzkriterien 4c

- Beispiel-Fräse mit einem Spannmittel neben dem Teil, ein kurzes Werkzeug,
  eine Bahn dicht daneben in die Tiefe → „Kollision prüfen“ → rot „In … berührt
  der Fräskopf das Spannmittel (Satz …, bei X …, Y …, Z …).“ → Klick → die
  Maschine steht dort, eine rote Kugel zeigt die Stelle.
- Eine Tasche, tiefer als die Schneide lang ist → „… berührt der Schaft von T1
  das Teil …“; mit einem Halter und noch tiefer → „… der Halter …“.
- Ein Eilgang durchs Teil → „… berührt die Schneide von T1 im Eilgang das
  Teil …“.
- Warnabstand 5 mm → gelbe Sätze für Stellen, die näher kommen, mit dem
  Abstand.
- Ohne Kollision: „Nichts berührt sich, nichts kommt näher als 1,00 mm.“
- Manuel versteht die Sätze ohne Erklärung.


## 13. Home-Punkt und Werkzeugwechselpunkt (Manuel, 2026-10-02)

Manuel: „Beim Starten steht der Fräser immer XYZ 0, so sieht's zumindest aus – was nicht so
cool ist, wenn der Nullpunkt unten am Teil angebracht ist. Daher muss es einen Home-Punkt
geben, der in der Maschine vielleicht angegeben wird, und vielleicht einen
Werkzeugwechselpunkt … damit auch die Simulation korrekt ablaufen kann.“

- **Heute:** Das Abfahren beginnt am ersten Punkt der Bahn; davor steht die Maschine bei 0 der
  Achsen.
- **Soll:** In „Maschine bearbeiten“ je Maschine ein Home-Punkt (je Linearachse eine
  Stellung, vorbelegt: Z ganz oben, X und Y am Ende ihres Wegs) und ein Werkzeugwechselpunkt
  (vorbelegt: der Home-Punkt). Das Abfahren beginnt und endet am Home-Punkt; vor jedem
  Werkzeugwechsel fährt es zum Wechselpunkt – erst Z, dann X und Y –, danach zum ersten Punkt
  der nächsten Operation – erst X und Y, dann Z. Reichweite, Kollision und Zeit zählen diese
  Wege mit.
- **Fertig, wenn:** im Prüffenster die Maschine am Home-Punkt beginnt, zum Wechsel an den
  Wechselpunkt fährt und am Ende wieder am Home-Punkt steht.
- **Gebaut (P-2026-10-02-48, 0.104.0):** je Linearachse „Home-Punkt“ und „Werkzeugwechsel“ in
  „Maschine bearbeiten“ (Betriebsart: HomeAn/Home, WechselAn/Wechsel; gezählt wie der
  Verfahrweg, im Durchmesser doppelt). Anders als oben **nicht vorbelegt**: Ohne eingetragenen
  Home-Punkt bleibt das Abfahren wie bisher – sonst hätten sich alle Zeiten und Prüfungen der
  Beispielmaschinen verschoben; das Ende des Verfahrwegs ist nicht immer „oben“. `abfahren`
  fügt Stationen mit `ziel` HOME/WECHSEL ein: Anfang am Home-Punkt, erst X/Y über den ersten
  Punkt, dann die Bahn; vor jedem Werkzeugwechsel erst Z (an der Drehmaschine mit X im
  Durchmesser: X), dann alle zum Wechselpunkt, zurück erst die anderen; am Ende Z, dann Home.
  Zeit und Kollision zählen die Wege mit; der Abspieler sagt „Home-Punkt“ bzw. „zum
  Werkzeugwechsel“. Der Messstopp fährt seit P-2026-10-04-06 zum Wechselpunkt (wie im
  Programm), die Operation danach kommt von dort. Die Zeit des Wechsels selbst seit
  P-2026-10-04-07: „Werkzeugwechsel dauert … s“ in „Maschine bearbeiten“ (`Wechselzeit`,
  Vorgabe 0 – nicht gezählt); das Abfahren zählt sie je Wechsel (andere Werkzeugnummer), die
  Zeile „Zeit“ nennt sie getrennt („…, Werkzeugwechsel 1 × 8 s“).
