# Durchsicht: Bedienbarkeit und Automatisierung (W-004)

Stand 2026-09-27 (0.24.0 mit P-2026-09-27-02 bis -05). Manuels Auftrag: „noch
einmal schauen, ob alles so benutzer-/bedienerfreundlich und einfach ist wie
möglich und ob man Sachen noch automatisieren könnte“.

**Vorgehen:** Alle 30 Oberflächen-Szenarien in FreeCAD 1.1.3 laufen lassen,
jeden Screenshot angesehen, die Befehle, Meldungen und Standardwerte im Code
nachgelesen, gemessen an [arbeitsregeln.md](arbeitsregeln.md), Abschnitt 8
(„Wer den Bildschirm sieht, hat keine Frage“), und die Arbeitsabläufe von der
Maschine über die Werkzeuge bis zum geprüften Job auf Handarbeit
durchgegangen. Gesehen hat Claude nur Screenshots – ob ein Fenster
verständlich ist, entscheidet Manuel.

Jeder Befund: **Heute** (was stört, mit Beleg), **Vorschlag**, **Fertig,
wenn** (ein Satz) und der Aufwand (klein: ein Patch; mittel: zwei, drei;
groß: eigene Spezifikation). Die Bilder entstehen mit
`scripts/oberflaeche_testen.sh tests/gui/<szenario>.py`.

## 1. Kurzfassung

- **Das Meiste trägt schon:** Beispielwerte grau im Werkzeug, Fehler sofort am
  Feld, Vorschläge für Nullpunkt, Einsatz und Werkstoff, ein Strg+Z je Klick,
  Hilfe je Bereich (Abschnitt 5).
- **Acht kleine Stellen**, je ein Patch (D-01 bis D-08): ein veralteter
  Tooltip, ein grauer Knopf ohne Erklärung, die Achsen im Verfahren in
  falscher Reihenfolge, kein „Jetzt neu starten“ nach dem Update, zwei Namen
  für dasselbe Fenster. *Alle erledigt (P-2026-09-27-09 bis -16).*
- **Nachgetragen, auf Manuels Hinweis:** Der Revolver der
  Beispiel-Drehmaschine war nicht als Revolver zu erkennen – jetzt mit einer
  Station je Platz, heller; die Beispielmaschinen erscheinen ohne die
  Gelenkmarkierungen, die ihn verdeckten (P-2026-09-27-07, -08).
- **Einfacher bedienen** (D-10 bis D-14): Das Prüffenster ist länger als der
  Aufgabenbereich – „Kollision prüfen“ liegt unter dem sichtbaren Teil;
  Hinweise sagen, wo man etwas ändert, statt dorthin zu führen. *D-10 und
  D-11 erledigt (P-2026-09-27-20 bis -22).*
- **Automatisieren** (D-20 bis D-30): Das Addon sollte die eigene Maschine
  kennen, statt dass sie offen sein muss; Betriebsarten, Halter und
  Richtwerte für Schnittwerte vorschlagen; die CAM-Bibliothek und die Werte
  im Job von selbst aktuell halten. *D-21, D-25 erledigt, D-20 und D-26 zum
  größeren Teil (P-2026-09-27-18, -19, -23, -24).*

## 2. Kleine Fehler und Unstimmigkeiten

### D-01 Tooltip von „Auf der Maschine prüfen“ ist veraltet (klein)
**Heute:** „Prüft, ob die Achsen einer Maschine für die Bahnen eines CAM-Jobs
reichen – jede Achse gegen ihre Grenzen.“ Abfahren und Kollision (seit 0.23.0
und 0.24.0) nennt er nicht – wer die Kollisionsprüfung sucht, findet sie so
nicht. **Vorschlag:** „Prüft einen CAM-Job auf einer Maschine: Reichen die
Achsen, wie fährt die Maschine die Bahn ab, stößt dabei etwas an?“
**Fertig, wenn:** der Tooltip alle drei Prüfungen nennt.
*Erledigt (P-2026-09-27-09).*

### D-02 „Schnittwerte in den Job“ ist ohne Job grau (klein)
**Heute:** Hat das aktive Dokument keinen Job, ist der Knopf ausgegraut, ohne
Erklärung. Alle anderen Befehle sind bedienbar und sagen, was fehlt
(`gui_maschine.py`: „ein ausgegrauter Knopf erklärt nichts“). **Vorschlag:**
immer bedienbar; ohne Job ein Satz wie bei „Auf der Maschine prüfen“ –
besser noch mit D-21 (Job aus allen offenen Dokumenten). **Fertig, wenn:**
ein Klick ohne Job einen Satz zeigt, was zu tun ist.
*Erledigt (P-2026-09-27-10).*

### D-03 „Maschine verfahren“: Achsen in X-, Y-, Z-Reihenfolge (klein)
**Heute:** Die Regler stehen in der Reihenfolge der Gelenkkette – bei der
3-Achs-Fräse Y1, Z1, X1, Spindelachse, bei der Drehmaschine C4, Z1, X1, T
(`szenario_beispielmaschine/6_…`, `szenario_verfahren/1_verfahren`). Das
Abfahren zeigt schon X1, Y1, Z1. **Vorschlag:** Linearachsen nach Namen (X, Y,
Z, U, V, W), dann Rundachsen (A, B, C), dann Spindeln und Revolver.
**Fertig, wenn:** die 3-Achs-Fräse X1, Y1, Z1, Spindel zeigt.
*Erledigt (P-2026-09-27-11).*

### D-04 Nach dem Update gibt es nur „Später“ (klein bis mittel)
**Heute:** „Aktualisiert. Bitte FreeCAD neu starten, damit die neue Version
gilt.“ – der einzige Knopf heißt „Später“ (`szenario_update/2_aktualisiert`).
**Vorschlag:** „Jetzt neu starten“ (FreeCAD fragt wie beim Beenden nach
ungespeicherten Dokumenten) und „Später“ – wie der Addon-Manager von FreeCAD.
Plattformneutral prüfen. **Fertig, wenn:** ein Klick FreeCAD neu startet.
*Erledigt (P-2026-09-27-12).*

### D-05 Die gewählte Baugruppe leuchtet beim Bearbeiten und Verfahren (klein)
**Heute:** Wer die Assembly im Baum anklickt und dann „Maschine bearbeiten“
oder „Maschine verfahren“ aufruft, sieht die ganze Maschine in der
Auswahlfarbe, solange das Fenster offen ist – die Teile und die
Hervorhebungen des Addons gehen darin unter (`szenario_schraege_achse/2_…`,
`szenario_verfahren_schraeg/1_…`). **Vorschlag:** Beim Öffnen die Auswahl
aufheben (die Baugruppe ist dann schon gefunden). **Fertig, wenn:** die
Maschine im offenen Fenster in ihren eigenen Farben steht.
*Erledigt (P-2026-09-27-13).*

### D-06 Rückmeldung „An CAM übergeben“ zeigt nur den langen Weg (klein)
**Heute:** „So geht es weiter: In einem CAM-Job ein Werkzeug hinzufügen und die
Bibliothek „CAM-Addon“ wählen.“ (`szenario_an_cam/2_rueckmeldung`) – der
kürzere Weg des Addons fehlt. **Vorschlag:** dazu: „Schneller: „Schnittwerte in
den Job“ → „Werkzeug-Controller hinzufügen“ legt Controller mit Drehzahl und
Vorschub in einem Schritt an.“ **Fertig, wenn:** die Rückmeldung beide Wege
nennt.
*Erledigt (P-2026-09-27-14).*

### D-07 Die Spanneisen der 3-Achs-Fräse sind nicht erwähnt (klein)
**Heute:** Seit 0.24.0 bringt die 3-Achs-Fräse aus „Neue Maschine …“ zwei
Spanneisen mit; die Beschreibung sagt „Kreuztisch X/Y, Fräskopf Z, Spindel S1 –
der einfachste Einstieg.“ Wer sie als eigene Maschine nimmt, kann
Kollisionen mit Spanneisen gemeldet bekommen, die bei ihm woanders stehen.
**Vorschlag:** „… mit zwei Spanneisen als Beispiel – im Baum verschieben oder
löschen“; oder ein Häkchen „Spanneisen als Beispiel“. **Fertig, wenn:**
Beschreibung (oder Häkchen) die Spanneisen nennt.
*Erledigt (P-2026-09-27-15).*

### D-08 Zwei Namen für dasselbe Fenster; die Meldung führt zum schweren Weg (klein)
**Heute:** Ohne Baugruppe sagt „Maschine bearbeiten“/„Maschine verfahren“
zuerst „Baue die Maschine zuerst im Arbeitsbereich Assembly zusammen …“ und
bietet „Beispielmaschine laden …“ nur „zum Ausprobieren“ an
(`szenario_beispielmaschine/1_meldung_bearbeiten`). Der Knopf öffnet dasselbe
Fenster wie der Befehl „Neue Maschine …“, dort heißt der Knopf „Maschine
bauen“. **Vorschlag:** überall „Neue Maschine …“; die Meldung nennt diesen
Weg zuerst („Eine fertig eingerichtete Maschine mit deinen Maßen: Neue
Maschine …“), den Selbstbau danach. Gehört zu D-26. **Fertig, wenn:** Meldung
und Befehl denselben Namen tragen und der leichte Weg vorn steht.
*Erledigt (P-2026-09-27-16).*

## 3. Einfacher bedienen

### D-10 Prüffenster: Urteile oben, Kollision sichtbar (mittel)
**Heute:** „Auf der Maschine prüfen“ ist länger als der Aufgabenbereich: Unter
dem Abspieler muss man blättern, um „Kollision prüfen“ zu finden
(`szenario_kollision/2_kollision`); die Urteile stehen an drei Stellen –
Grenzen oben, Kollision unten, die Hinweise zur Werkzeuglänge ganz unten. Oben
stehen fünf Zeilen Erklärung. **Vorschlag:** oben je Prüfung eine Zeile:
„Achsen: in den Grenzen ✓ · Kollision: 1 Berührung ✗ · Länge: T1 geschätzt“,
jede anklickbar (springt zum Abschnitt); Erklärung auf einen Satz (der Rest
steht in der Hilfe); Abfahren und Kollision einklappbar. **Fertig, wenn:** in
einem 800 Pixel hohen Fenster alle drei Urteile ohne Blättern zu sehen sind.
*Erledigt (P-2026-09-27-20) – ohne Einklappen: Mit den Urteilen oben ist es
fürs Kriterium nicht nötig.*

### D-11 Hinweise führen zum Werkzeug (mittel)
**Heute:** „T1: ohne Halter geprüft – den Halter wählst du beim Werkzeug in der
Werkzeugverwaltung.“ und „gerechnet mit der Gesamtlänge … Genauer mit der
„Länge ab Spindelnase“ in der Werkzeugverwaltung.“ sind Text. Ändert man
nebenbei in der Werkzeugverwaltung etwas, merkt das offene Prüffenster es
nicht – es liest sie nur beim Öffnen. **Vorschlag:** Klick auf den Hinweis
öffnet die Werkzeugverwaltung mit diesem Werkzeug; nach OK dort rechnet das
Prüffenster neu. **Fertig, wenn:** Halter wählen, OK – und die Kollision gilt
mit dem Halter, ohne das Prüffenster zu schließen.
*Erledigt (P-2026-09-27-21).*

### D-12 „+ Einsatz“ beim neuen Werkzeug gesperrt (klein bis mittel)
**Heute:** Ist oben ein Werkstoff gewählt (etwa 1.4301), ist bei einem neuen
Werkzeug „+ Einsatz“ grau: „Für 1.4301 gelten die Werte für alle Werkstoffe
(grau). Zum Ändern eigene Werte anlegen – oder oben „Alle Werkstoffe“
wählen.“ (`szenario_werkzeugverwaltung/5_neu_beispielwerte`). Für das erste
Werkzeug ist das ein Umweg über einen Begriff, den man erst verstehen muss.
**Vorschlag:** Hat das Werkzeug noch gar keine Einsätze, legt „+ Einsatz“ ihn
für alle Werkstoffe an und sagt es in einem Satz. **Fertig, wenn:** beim
neuen Werkzeug „+ Einsatz“ bei jedem gewählten Werkstoff geht.

### D-13 Ein Menü „CAM-Addon“ (klein bis mittel)
**Heute:** Die Befehle gibt es nur als neun Symbole ohne Text in der
Werkzeugleiste (Assembly und CAM, `szenario_erster_start/4_…`); zwei davon
sind „Über“ und „Nach Updates suchen“. **Vorschlag:** zusätzlich ein Menü
„CAM-Addon“ mit allen Befehlen als Text (auffindbar, Tastenkürzel möglich); in
der Werkzeugleiste nur die sieben Arbeitsbefehle, „Über“ und „Update“ im Menü
und auf der Einstellungsseite. **Fertig, wenn:** jeder Befehl im Menü steht und
die Werkzeugleiste sieben Symbole hat.

### D-14 Kennwerte einer neuen Achse: Pflicht ohne Beispiel (zur Entscheidung)
**Heute:** Eilgang und Drehzahl sind Pflicht, die Felder zeigen „bitte
eintragen“ bzw. „unbekannt“, bis man tippt – beim Werkzeug stehen dagegen graue
Beispielwerte, die gelten, bis man eigene einträgt. **Vorschlag:** entweder
graue Beispielwerte auch hier (Eilgang 10 000 mm/min …) – oder bewusst leer,
weil ein falscher Maschinenwert schlimmer ist als ein fehlender. Gehört zu
D-25.

## 4. Automatisieren

### D-20 Die eigene Maschine merken (mittel)
**Heute:** „Auf der Maschine prüfen“ braucht die Maschine als offenes Dokument
(„Es ist keine Maschine offen. Öffne das Dokument mit deiner Maschine …“),
„Schruppwerte planen“ übernimmt Höchstdrehzahl und -vorschub nur von einer
offenen Maschine, und sind mehrere offen, fragt das Prüffenster jedes Mal.
Die Spindelleistung kennt die Maschine gar nicht – der Planer merkt sich, was
man einmal eintippt, aber für alle Maschinen gleich. **Vorschlag:** Das Addon
merkt sich die Maschinendatei (zuletzt benutzt, und je Job wie schon den
Nullpunkt) und öffnet sie selbst, wenn sie gebraucht wird; die Meldung hat
Knöpfe „Maschine öffnen …“ und „Neue Maschine …“; die Spindel bekommt
„Leistung (kW)“. **Fertig, wenn:** nach
einem Neustart von FreeCAD „Auf der Maschine prüfen“ ohne geöffnete Maschine
direkt das Fenster zeigt.
*Prüffenster erledigt (P-2026-09-27-19): merkt die Maschine am Job und als
zuletzt benutzte, öffnet sie selbst, die Meldung hat beide Knöpfe; bei
mehreren offenen fragt es weiter, die gemerkte vorn – im Fenster gibt es keine
Auswahl der Maschine. Offen: „Schruppwerte planen“ nimmt die gemerkte
Maschine, Spindelleistung.*

### D-21 Den Job in allen offenen Dokumenten finden (klein)
**Heute:** „Im aktiven Dokument gibt es keinen CAM-Job …“ – etwa direkt nach
„Neue Maschine …“, wenn das Maschinendokument vorn ist. Maschinen sucht das
Addon schon in allen Dokumenten. **Vorschlag:** Jobs aus allen offenen
Dokumenten; gibt es genau einen, diesen; sonst wählt man ihn im Fenster (die
Auswahl gibt es schon). Ebenso für „Schnittwerte in den Job“ (D-02).
**Fertig, wenn:** der Befehl mit dem Maschinendokument vorn den Job des
anderen Dokuments prüft.
*Erledigt (P-2026-09-27-18).*

### D-22 Kollision von selbst prüfen (mittel, zur Entscheidung)
**Heute:** Man muss „Kollision prüfen“ klicken; nach jeder Änderung am
Nullpunkt ist das Ergebnis weg („Noch nicht geprüft …“). **Vorschlag:** Die
Prüfung startet nach dem Öffnen und nach jeder Änderung von selbst, mit
Fortschritt und jederzeit abbrechbar; der Knopf bleibt für „noch einmal“.
Offen: große Jobs rechnen länger – ab welcher Größe nur auf Klick?
**Fertig, wenn:** nach dem Öffnen ohne Klick das Kollisionsurteil erscheint.

### D-23 Halter vorschlagen (mittel)
**Heute:** Ohne Halter prüft die Kollision nur das Werkzeug („T1: ohne Halter
geprüft …“); den Halter wählt man je Werkzeug von Hand. **Vorschlag:** ein
Standard-Halter nach Schaft-Ø (Einstellung; Vorgabe aus den Vorlagen, etwa bis
Ø 10 ER16, bis 16 ER25, bis 20 ER32, darüber ER40), beim Werkzeug grau als
Vorschlag, bis man einen wählt – so wie die grauen Beispielmaße. **Fertig,
wenn:** ein Werkzeug ohne gewählten Halter mit dem vorgeschlagenen geprüft
wird und das Fenster es sagt.

### D-24 Richtwerte für Schnittwerte (groß, zur Entscheidung)
**Heute:** Neue und aus CAM übernommene Werkzeuge haben keine Einsätze („Jetzt
je Werkzeug die Einsätze mit vc und fz aus dem Katalog eintragen.“,
`szenario_aus_cam/1_meldung`); der Planer rechnet grau mit einem Beispiel
„für Stahl mit HSS“ – auch wenn der Werkstoff Aluminium ist
(`szenario_schruppwerte/5_beispielwerte`). **Vorschlag:** Richtwerte je
Werkstoffgruppe (ISO P, M, K, N, S, H) × Schneidstoff × Werkzeugart, fz nach
Durchmesser, als graue Beispiel-Einsätze (Vollnut, Schruppen dynamisch,
Schlichten …), bis man eigene einträgt; „Richtwerte eintragen“ für alle
übernommenen Werkzeuge auf einmal. Deutlich als Richtwert gekennzeichnet –
der Katalog des Herstellers bleibt besser. Offen: woher die Tabelle kommt.
**Fertig, wenn:** ein neuer VHM-Fräser Ø 10 bei gewähltem Aluminium graue
Einsätze mit Aluminium-Werten zeigt.

### D-25 Betriebsarten der Maschine vorschlagen (mittel)
**Heute:** Bei einer selbst gebauten Baugruppe steht jedes Gelenk auf „noch
keine Betriebsart“ (`szenario_maschine_bearbeiten/1_leer`); je Gelenk „+
Betriebsart“, Art wählen, den NC-Namen tippen (das Feld ist leer), Pflichtwerte
eintragen. **Vorschlag:** ein Knopf „Vorschlagen“: Schiebegelenke → Linear,
NC-Name aus der Richtung (entlang X der Maschine → X1 …) oder dem Namen des
Gelenks; Drehgelenke mit „Spindel“ bzw. „Revolver“ im Namen → Spindel S1 bzw.
Revolver T, sonst Positionieren (A, B, C nach der Achse); bei „+ Betriebsart“
ist der NC-Name vorbelegt. Man prüft nur noch. **Fertig, wenn:** die
Drehmaschine aus `szenario_maschine_bearbeiten` mit einem Klick S1, Z1, X1 und
T bekommt.
*Erledigt (P-2026-09-27-23).*

### D-26 „Neue Maschine …“: Maße auch für die Fräsen (mittel bis groß)
**Heute:** Nur die Drehmaschine hat Maße; bei den Fräsen steht „Diese Bauart
hat feste Maße – zum Ausprobieren. Nach dem Bauen lässt sich in der Baugruppe
alles ändern.“ (`szenario_neue_maschine/1_fraese_feste_masse`) – die Wege
stellt man dann an den Gelenkgrenzen in der Baugruppe ein. Wer FreeCAD CAM
nutzt, hat meist eine 3-Achs-Fräse. **Vorschlag:** Wege X, Y, Z, Tischgröße,
Höchstdrehzahl (bei 5-Achs dazu die Schwenkbereiche) wie bei der
Drehmaschine. **Fertig, wenn:** eine 3-Achs-Fräse mit eigenen Wegen in einer
Minute steht und „Auf der Maschine prüfen“ mit diesen Grenzen rechnet.
*3-Achs-Fräse erledigt (P-2026-09-27-24); offen: Tischgröße, 5-Achs mit
Schwenkbereichen.*

### D-27 Die CAM-Bibliothek beim Speichern mitziehen (klein bis mittel)
**Heute:** OK in der Werkzeugverwaltung speichert nur dort; CAM sieht eine
Änderung erst nach „Speichern und an CAM übergeben“ – wer es vergisst, arbeitet
in CAM mit alten Werkzeugen. **Vorschlag:** Wurde schon einmal übergeben,
übergeben OK und Übernehmen gleich mit (Einstellung, ab Werk an); der Knopf
bleibt fürs erste Mal. **Fertig, wenn:** eine Änderung mit OK in der
Bibliothek „CAM-Addon“ steht.

### D-28 Veraltete Werte im Job melden (mittel)
**Heute:** Ändert man in der Werkzeugverwaltung vc, fz oder ein Maß, behalten
die Werkzeug-Controller im Job die alten Drehzahlen und Vorschübe, bis man
„Schnittwerte in den Job“ erneut aufruft – niemand sagt es. **Vorschlag:**
„Auf der Maschine prüfen“ vergleicht und meldet: „T3: im Job 2800 U/min, laut
Werkzeugverwaltung 3183 – übernehmen?“ (ein Klick). **Fertig, wenn:** eine
geänderte Schnittgeschwindigkeit im Prüffenster als Hinweis mit Knopf
erscheint.

### D-29 Vorschläge mit einem Klick übernehmen (klein bis mittel)
**Heute:** „Schnittwerte in den Job“ sagt rot: „Die letzte Ebene ist nur 1 mm
dick … Mit ap 26 mm im Einsatz entfällt sie“ (`szenario_loch_auffraesen/1_…`) –
ändern muss man es in der Werkzeugverwaltung. **Vorschlag:** Knopf „ap 26 mm
übernehmen“ am Hinweis. **Fertig, wenn:** ein Klick den Einsatz ändert und die
Ebenenzahl neu erscheint.

### D-30 Der Standard-Controller „TC: 5mm Endmill“ (klein)
**Heute:** FreeCAD legt in jedem neuen Job diesen Controller an; „Schnittwerte
in den Job“ zeigt ihn als „nicht in der Werkzeugverwaltung – nicht ändern“
(`szenario_schnittwerte_job/1_dialog`). **Vorschlag:** Benutzt ihn keine
Operation: „wird nicht benutzt – entfernen?“; benutzt ihn eine: „in die
Werkzeugverwaltung übernehmen?“. **Fertig, wenn:** der unbenutzte Controller
mit einem Klick verschwindet.

## 5. Angesehen und für gut befunden

- Werkstoffliste mit ISO-Kennung, Suche und Filter; die Werkzeugarten mit
  Bildern im Menü; „Strategien vergleichen“ mit Balken und einem Urteil in
  Sätzen.
- Beispielwerte grau im Werkzeug, die gelten, bis man eigene einträgt;
  Fehler sofort am Feld mit einem Satz („Jeder Weg braucht ein Stück …“).
- Vorschläge: Nullpunkt (je Job gemerkt), Einsatz je Operation, Werkstoff vom
  Rohteil, Höchstdrehzahl und -vorschub von einer offenen Maschine im Planer,
  die Sprache nach der von FreeCAD.
- Rückfrage beim Umrechnen von ae und ap, wenn sich der Durchmesser ändert;
  ein Strg+Z je Klick; eine Hilfe (?) je Bereich.
- Nicht bestätigt: Auf der Einstellungsseite war der Erklärtext unter
  „Zahlen“ abgeschnitten – das Szenario zwingt die Seite auf 500 × 320 Pixel;
  im Einstellungsfenster von FreeCAD ist sie größer. Beim nächsten Test mit
  ansehen.

## 6. Vorschlag zur Reihenfolge und Fragen an Manuel

**Reihenfolge (Empfehlung):** zuerst die kleinen D-01 bis D-08 (je ein Patch,
zusammen etwa ein Arbeitstag, niemand muss etwas entscheiden); dann D-21 und
D-20 (beseitigen die häufigste Sackgasse „kein Job / keine Maschine“); dann
D-10 und D-11 (Prüffenster); dann D-25 und D-26 (eigene Maschine schnell
eingerichtet); D-24 zuletzt, weil es eine Datengrundlage braucht.

**Fragen (je mit Empfehlung):**

1. **Reihenfolge:** A) wie oben (Empfehlung); B) erst die großen
   Automatisierungen D-24 bis D-26; C) erst Manuels Test von 4a–4c, dann
   entscheiden.
2. **D-22 Kollision von selbst:** A) startet von selbst, abbrechbar
   (Empfehlung – wer das Fenster öffnet, will das Urteil; dauert es bei einem
   großen Job zu lange, bricht man ab); B) nur auf Klick wie heute.
3. **D-24 Richtwerte:** A) eine eigene Tabelle aus allgemein bekannten
   Richtwerten, deutlich als Richtwert gekennzeichnet (Empfehlung); B) keine
   Richtwerte – nur Katalogwerte; C) später Herstellerdaten einlesen.
4. **D-27 CAM mitziehen:** A) OK übergibt mit, sobald einmal übergeben wurde
   (Empfehlung); B) nur auf Knopfdruck wie heute.
5. **D-14 Beispielwerte an der Maschine:** A) leer lassen (Empfehlung – ein
   falscher Grenzwert ist schlimmer als ein fehlender); B) grau vorbelegen
   wie beim Werkzeug.
