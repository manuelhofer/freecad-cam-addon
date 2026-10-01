# FreeCAD CAM-Addon

Ein Addon, das die CAM-Oberfläche von FreeCAD bedienbarer macht.

- Für die **aktuelle stabile Version** von FreeCAD (derzeit 1.1.3) **und**
  den **Wochen-Build**, auf jedem Betriebssystem. „An CAM übergeben“ braucht
  die CAM-Maschinendefinition, die es derzeit nur im Wochen-Build gibt – in
  1.1.3 erklärt das Addon das beim Klick.
- Unabhängig von Maschine und Postprozessor.

## Was es kann

- **So geht’s:** der Weg vom Teil zum Programm in sechs Schritten – Maschine,
  Werkzeuge, Teil und Bearbeitung, Bestückung, Prüfen, Programm – mit dem Knopf
  zu jedem Schritt; oben im Menü „CAM-Addon“, als Hilfeseite mit Verweisen auf
  alle anderen.
- **Neue Maschine …:** eine Bauart wählen – Drehmaschine mit Y-Achse,
  3-Achs-Fräse, drei 5-Achs-Fräsen – und sie fertig eingerichtet als
  Baugruppe bekommen; bei der Drehmaschine mit eigenen Maßen: Bettneigung,
  Winkel der Y-Achse, Wege, Revolverplätze, Höchstdrehzahl. Ihre Revolverplätze
  sind Aufnahmen – wie ein Werkzeug darin steht, sagt sein Halter.
- **Maschine bearbeiten:** eine Maschine als Baugruppe beschreiben –
  Achsen, Spindeln, Werkzeug- und Werkstückaufnahmen – und an CAM übergeben.
  Der **Verfahrweg** jeder Achse steht dort zum Ändern („von … bis …“), mit
  einem Satz, wie weit der Werkzeugplatz dabei vom Werkstück weg ist.
  Auch eine **schräge Achse**, etwa die Y-Achse einer Schrägbett-Drehmaschine:
  Winkel eintragen, die Baugruppe kippt mit. Das Programm bleibt
  rechtwinklig (X, Y), die Steuerung rechnet auf die Schlitten um.
- **Maschine verfahren:** je Achse ein Regler, die Baugruppe fährt mit –
  bis zu den Grenzen der Gelenke. Mit schräger Achse auch „wie im
  Programm“: Regler X und Y, beide Schlitten fahren passend mit.
- **Auf der Maschine prüfen:** Reicht der Verfahrweg für einen CAM-Job? Für
  jeden Punkt der Bahnen die Stellung jeder Achse, gegen ihre Grenzen
  gehalten – als Sätze („X1 fährt in „Tasche“ bis 312,00 mm, die Grenze ist
  250,00 mm“); ein Klick fährt die Maschine an die Stelle. Mit dem
  Nullpunkt des Jobs auf der Werkstückaufnahme und der Länge ab Spindelnase
  aus der Werkzeugverwaltung. **Abfahren:** Die Maschine fährt die Bahn
  sichtbar ab – Werkzeug, Rohteil und Bahn in ihrer 3D-Ansicht; abspielen,
  anhalten, Punkt für Punkt, bis ×100; Satz, Zeit und Achswerte laufen mit,
  eine Achse am Anschlag steht rot da; darunter, wo die **Werkzeugspitze** im
  Programm steht. Eine Überschreitung sagt auch, wo die Spitze an der Grenze
  stünde. **Kollision:** Werkzeug, Halter und
  Maschine gegen das fertige Teil, die Spannmittel und die Maschine – rot, wenn
  etwas anstößt („In „Tasche“ berühren sich der Halter von T3 und das Teil“),
  gelb, wenn es näher kommt als der Warnabstand; ein Klick zeigt die Stelle.
  Oben im Fenster die Urteile auf einen Blick – Achsen, Kollision,
  Werkzeuglänge und **Schnittwerte** (passen Drehzahl und Vorschub im Job
  noch zur Werkzeugverwaltung? sonst „übernehmen“); die Maschine merkt es sich
  und öffnet sie beim nächsten Mal selbst.
- **Bestückung:** Jeder Job hat seine eigene – welches Werkzeug auf welchem
  Revolverplatz steckt. Das Fenster zeigt den Revolver der Maschine mit den
  Werkzeugen des Jobs und ihren Haltern; je Platz eine Auswahl, umlegen tauscht.
  Im Programm ist die Nummer der Platz (T5 für P5); beim Abfahren stecken alle
  Werkzeuge des Jobs im Revolver und schwenken mit.
- **Werkzeugverwaltung:** Werkstoffliste mit deutschen Bezeichnungen
  („1.4301 X5CrNi18-10 · Edelstahl, austenitisch“), Zusammensetzung und
  Härte; Werkzeuge mit Bild, Suche und Schnittwerten je Werkstoff und
  Einsatz – vc und fz eingeben, Drehzahl, Vorschub und Zeitspanvolumen
  rechnet das Addon; ein Bild des Eingriffs; Strategien vergleichen
  (Abtrag, Verschleiß) mit einem Urteil in Sätzen, auch Varianten einer
  Zeile; **Schruppwerte planen** –
  so viel Span, wie Fräser und Maschine hergeben (ganze Schneide, schmales
  ae, fz mit Spandickenausgleich). Werkzeuge lassen sich aus
  FreeCAD-Bibliotheken übernehmen. **Halter** mit ihrer Kontur aus Zylindern
  und Kegeln, Vorlagen von ER16 bis Bohrfutter; je Werkzeug einer – damit
  schätzt die Werkzeugverwaltung die Länge ab Spindelnase. Der Halter sagt
  auch, **wie das Werkzeug zur Maschine steht**: gerade oder gewinkelt –
  angetrieben radial am Revolver, Winkelkopf an der Fräse (Winkel, Drehung,
  Versatz, Kopf); Reichweite, Abfahren und Kollision rechnen damit.
- **An CAM übergeben:** die Werkzeuge als Werkzeugbibliothek „CAM-Addon“;
  „Schnittwerte in den Job“ setzt Drehzahl und Vorschub der
  Werkzeug-Controller eines Jobs passend zum Werkstoff des Rohteils, dazu
  Schrittweite, Zustelltiefe und Helix-Eintauchwinkel der passenden
  Operationen (etwa Adaptiv zum Auffräsen: einmal helikal eintauchen, dann
  ebenenweise mit der ganzen Schneide) – und zeigt vorher, wie viele Ebenen
  daraus werden –, und legt auf Wunsch die Werkzeug-Controller gleich an.
- **4-Achs-Bearbeitung:** Stirnfläche eines Teils anklicken – das Teil sitzt
  vorne mittig in einer runden Stange (z. B. Ø 80), als CAM-Job mit
  Zylinder-Rohteil. Ist eine Maschine offen, gibt sie die Rundachse vor – an
  der Drehmaschine liegt die Stange längs der Spindel; ohne Maschine A, B oder
  C. Das Fenster sagt, ob das Teil hineinpasst; alles ist einstellbar, leere
  Felder gelten mit ihrem Vorschlag. **Weiter** fragt „Was willst du machen?“:
  **Rundum schruppen** – ein Fräser aus der Werkzeugverwaltung nimmt die Stange
  in Lagen bis aufs Schlichtaufmaß ab, als Spirale um das Teil (die Rundachse
  dreht fortlaufend, Vorschub nach G93); grau steht vorher, wie viele Lagen es
  werden. Zuerst fragt der Assistent, **welche Maschine** – sie gibt die
  Rundachse vor, ein Satz sagt, was sie kann. Hinten läuft der Fräser um den
  **Überlauf** (Radius + 0,5 mm) über das Teil hinaus, mit Abstand zum Futter –
  alles einstellbar, mit Vorschlag; reicht der Halter weiter als der Fräser,
  zählt sein Rand –, und ein Satz sagt, **wie weit die Stange aus dem Futter
  ragen muss**. Säße der Fräser auf der gewählten Maschine nicht radial, sagt
  es ein gelber Satz – mit dem Halter, der fehlt. „Auf der Maschine prüfen“ fährt die Bahn mit
  drehender Rundachse ab, prüft sie auf Kollision und **trägt die Stange ab**:
  Am Ende steht sie in Farben gegen das fertige Teil – grün das Aufmaß, rot, wo
  zu viel blieb, blau, wo etwas im Teil fehlt. **Nachträglich ändern:**
  Doppelklick auf „Rundum schruppen“ öffnet das Fenster wieder – anderer
  Fräser, Einsatz, Zustellung, Aufmaß, auch Stange und Rundachse,
  „Übernehmen“. **Rundum schlichten** – danach fährt ein zweiter Fräser eine
  Spirale auf dem Teil, gerechnet mit seiner echten Form (Kugel-, Torus-,
  Konikfräser …); die Schrittweite kommt aus der Werkzeugtabelle, daneben steht
  die Kammhöhe, darunter Umdrehungen und Zeit. Das **Muster** – Spirale oder
  Linien längs der Achse – schlägt der Assistent nach den gewählten Flächen vor:
  Linien, wenn sie nicht rundum gehen (Abflachung, Nut), mit dem Grund dazu. Wo der Schruppfräser nicht
  hinkam (Innenecken, enge Nuten), nimmt das Schlichten vorher in Stufen ab. Vor
  jeder Wand (Absatz, Flanke einer Nut) hält die Spirale eine Umdrehung an – so
  kommt der Fräser rundum bis an die Wand. Die
  Simulation trägt die Stange mit der Form des Fräsers ab, die
  Kollisionsprüfung sieht den Kugelfräser als Kugel. **Flächen wählen:** In
  Schritt 2 eine Fläche des Teils anklicken (noch ein Klick nimmt sie heraus) –
  die Liste nennt Art und Erreichbarkeit (grün, gelb, rot), das 3D färbt sie so.
  Dann fräsen Schruppen und Schlichten nur dort, wo der Fräser eine gewählte
  Fläche berührt, in Zeilen hin und her; abgehoben wird nur zwischen getrennten
  Flächen, hinein geht es über eine Rampe mit dem Eintauchwinkel des Fräsers.
  Ohne Wahl oder mit allen Mantelflächen: rundum. Getrennte Flächen fräst es
  nacheinander; „Auf der Maschine prüfen“ vergleicht dann nur auf den gewählten
  Flächen. **Plan indexiert:** Eine ebene Fläche längs der Stange (Abflachung,
  Schlüsselfläche, Nutboden) fräst der Assistent wie beim Planfräsen – die
  Rundachse steht, der Fräser mit ebener Stirn fährt Zeilen längs und rückt mit
  dem Y quer, in Lagen bis auf die Fläche: eben bis in die Ecken; vorgeschlagen,
  sobald eine gewählte Fläche so liegt und die Maschine eine Achse quer zur
  Stange hat. **Rundum entgraten:** An den Außenkanten der gewählten Flächen
  fährt ein Fasenfräser entlang (oder ein Kugelfräser bricht sie rund), die
  Rundachse dreht mit – vorgeschlagen, sobald es solche Kanten und einen
  Fasenfräser gibt; Innenkanten, Rundungen und die Stirnen bleiben. Welche
  Postprozessoren von FreeCAD das Programm richtig schreiben, steht in der
  Hilfe.
- **Bearbeitung (Fräsen)** – für ein Teil im Quader (W-006, im Bau): eine
  Fläche des Teils anklicken, der Job mit dem Rohteil (Aufmaß je Seite) entsteht
  sofort; der **Nullpunkt** wie im Modell oder einer der 22 Punkte des Rohteils
  (Ecken, Kantenmitten, Mitte oben/unten), um X, Y, Z verschoben; **Planfräsen** für die Oberseite oder gewählte ebene Flächen – Zeilen
  hin und her in Lagen bis auf die Fläche, Überlauf über den Rand, Halbkreise
  zwischen den Zeilen, halber Vorschub beim Austritt, vor Absätzen hält die
  Zeile an; Fräser und Einsatz aus der Werkzeugverwaltung, die Werte als
  Vorschlag, darunter „→ 3 Lagen, 30 Zeilen, etwa 2 min“ – die Zeit mit
  Eilgang 10 m/min und Beschleunigung 1 m/s² (feste Vorgaben, auch im
  Prüffenster, wo die Maschine nichts sagt). Doppelklick auf die
  Operation öffnet das Fenster zum Ändern. Vor einer Wand fährt der Fräser an
  ihr entlang, damit zwischen den Zeilen nichts stehen bleibt. „Auf der
  Maschine prüfen“ trägt den Quader beim Abspielen ab – jede Operation mit der
  Form ihres Fräsers, auch FreeCADs eigene – und färbt ihn am Ende gegen das
  fertige Teil (grün, gelb, rot, blau). **Kontur** für Wände: eine senkrechte
  Fläche anklicken – ihre Unterkanten werden zur Kontur, außen um einen Zapfen
  oder innen in einer Tasche –, Schruppen in Lagen mit Aufmaß (so viele Bahnen
  nebeneinander, wie Material neben der Wand steht), dann Schlichten in einem
  Zug, tangential hinein und heraus, im Gleichlauf, Bögen in den Ecken.
  **Räumen** für dieselben Flächen und für Taschenböden – wie ein HSM-Weg: Ringe
  bei voller Zustellung und schmalem Zeilenabstand, ohne Wenden, von außen
  kreisend nach innen (auf der Oberseite) oder einmal über die Rampe rundum und
  von innen nach außen (in der Tasche), Gleichlauf oder Gegenlauf, eingetaucht
  nur, wo schon frei ist; drei Varianten werden gerechnet – darunter die, bei
  der die Ringe als Rechteck beginnen und von Ring zu Ring runder werden, bis
  der letzte genau um den Zapfen fährt – eine Spirale ohne Absetzen, die Ringe
  so weit auseinander, wie der Fräser verträgt. **Die Zeit entscheidet:**
  Planfräsen und Räumen rechnen beide, die schnellere bekommt den Haken, beide
  Zeilen sagen, um wie viel; mit einer Tasche dazu rechnet das Fenster die
  ganzen Folgen, und die Kontur schlichtet nach dem Räumen nur noch das Aufmaß.
  Ein Prüfstand fährt jede Strategie an vier Maßstabsteilen im Quader ab und
  lässt keine Bahn langsamer werden. Jede Bearbeitung ist ein
  Block mit Haken; „Anlegen“ legt alle angehakten an. **Bohrung fräsen**:
  zylindrische Bohrungen mit einem Schaftfräser, kleiner als sie – in einer
  Helix hinab, große mit Ringen nach außen, die Wand in einem Zug; im
  Wettbewerb mit der Kontur (in Bohrungen meist dreimal so schnell). Alles im
  Gleichlauf (Spindel M3: das Material rechts der Fahrtrichtung). **Bohren**:
  FreeCADs Bohr-Operation mit dem Bohrer aus der Werkzeugverwaltung, der den
  Durchmesser der Bohrung hat (G81, tief in Hüben mit G83), auch in
  Sackbohrungen mit Bohrspitze wie aus FreeCADs „Bohrung“ – tritt gegen
  Bohrung fräsen und Kontur an; die schnellste bekommt den Haken. **Gewinde
  bohren**: FreeCADs Gewinde-Operation (G84, links G74) mit dem Gewindebohrer,
  dessen Kernloch die Bohrung hat (M10 × 1,5 in Ø 8,5) – durchgehend um den
  Anschnitt hinaus, in Sackbohrungen eine Steigung über dem Grund.
  **Entgraten**: ein Fasenfräser bricht die Oberkanten gewählter Wände (oder
  die Kanten einer gewählten Fläche oben, an denen eine Wand hinab geht) – im
  Gleichlauf, tangential hinein und heraus, die Fase so breit wie gesagt;
  hat das Modell die Fase schon, genau so, wie sie gezeichnet ist. Mit dem
  Radienfräser **verrundet** es Kanten, gezeichnete Rundungen genau.
  **Zentrieren** mit dem NC-Anbohrer vor dem Bohren und **Senken** mit dem
  Kegelsenker in die Senkungen, die das Modell hat. **Restmaterial**: ein
  kleinerer Fräser holt, was der große in Ecken innen stehen ließ – nur dort.
  **Gewinde fräsen** mit dem Gewindefräser: das Gewinde aus Kernloch und
  Steigung (M10 × 1,5 in Ø 8,5), auf die Mitte der Toleranz 6H, im Gleichlauf,
  der Vorschub an der Schneide. **Nut**: Langlöcher mit einem Schaftfräser, der
  nicht breiter ist als sie – nie in voller Breite mit ganzer Schneide: in
  Kreisen, die je Umlauf um ae vorrücken (Trochoide), oder in einer
  Zickzack-Rampe, wenn die Nut kaum breiter ist; zuletzt die Wand rundum. Sie
  tritt am Grund gegen Räumen an, an den Wänden gegen die Kontur.
- **Beispiele:** `beispiele/` – Manuels Testteil für die 4-Achs-Bearbeitung
  (Loft mit D-Profil), mit Anleitung in `beispiele/README.md`.

Stand und nächste Schritte: [docs/STATUS_SNAPSHOT.md](docs/STATUS_SNAPSHOT.md).
Für KI-Assistenten: [CHATSTART.md](CHATSTART.md).

## Installieren – eine Zeile, auf jedem Betriebssystem

Geht, sobald das Repository öffentlich ist (siehe unten, wenn es noch privat
ist):

1. In FreeCAD **Ansicht → Fenster → Python-Konsole** öffnen.
2. Diese Zeile hineinkopieren und Enter drücken:

   ```
   import NetworkManager as n; n.InitializeNetworkManager(); exec(n.AM_NETWORK_MANAGER.blocking_get("https://raw.githubusercontent.com/manuelhofer/freecad-cam-addon/main/installieren.py").data())
   ```

   Sie lädt über den Netzzugang des Addon-Managers von FreeCAD. So geht es
   auch, wenn FreeCADs Python kein SSL hat – die frühere Zeile mit `urllib`
   meldete dann „unknown url type: https“. Meldet die Konsole trotzdem einen
   Fehler: über den Addon-Manager installieren (unten).

3. FreeCAD neu starten. Beim ersten Start fragt das Addon nach der Sprache.
   Seine Werkzeugleiste und das Menü **CAM-Addon** erscheinen in den
   Arbeitsbereichen **Assembly** und **CAM**.

Die Zeile legt das Addon in den Addon-Ordner von FreeCAD – ohne Git, ohne
GitHub Desktop – und trägt es im Addon-Manager ein. **Aktualisieren:**
**CAM-Addon → Nach Updates suchen** (im Menü) schaut bei
GitHub nach und fragt bei einer neuen Version „Jetzt aktualisieren?“. Von
selbst sucht das Addon nicht; beim Start von FreeCAD suchen lässt es sich
unter Bearbeiten → Einstellungen → CAM-Addon einschalten. Ohne das Addon:
dieselbe Zeile noch einmal, oder **Werkzeuge → Addon-Manager** – der kann
das Addon auch wieder entfernen. Was die Zeile genau tut, steht oben in
[installieren.py](installieren.py).

**Oder ganz über den Addon-Manager:** **Bearbeiten → Einstellungen →
Addon-Manager**, unter **Eigene Repositories** eine Zeile mit der URL
`https://github.com/manuelhofer/freecad-cam-addon` und dem Branch `main`;
dann **Werkzeuge → Addon-Manager**, nach **freecad-cam-addon** suchen,
**Installieren**, FreeCAD neu starten.

## Installieren, solange das Repository privat ist

Ein privates Repository gibt GitHub nur angemeldet heraus – die Zeile oben
und der Addon-Manager kommen dann nicht heran. Dann holt man das Addon mit
**GitHub Desktop** (oder Git) direkt in den Addon-Ordner von FreeCAD:

1. In FreeCAD die Python-Konsole öffnen (**Ansicht → Fenster →
   Python-Konsole**) und eingeben:
   `App.getUserAppDataDir() + "Mod"`
   Das ist der Ordner für Addons – auf jedem Betriebssystem ein anderer, die
   Konsole nennt den richtigen.
2. In GitHub Desktop: **File → Clone repository** →
   `manuelhofer/freecad-cam-addon`, als **Local path** den Mod-Ordner aus
   Schritt 1 wählen. Es entsteht der Ordner `freecad-cam-addon`.
   (Mit Git: `git clone https://github.com/manuelhofer/freecad-cam-addon`
   im Mod-Ordner.)
3. FreeCAD neu starten.

**Aktualisieren:** **CAM-Addon → Nach Updates suchen** (im Menü) schaut
nach (per Git, mit der Anmeldung von GitHub Desktop bzw.
Git) und fragt bei einer neuen Version „Jetzt aktualisieren?“. Beim Start
von FreeCAD suchen: Bearbeiten → Einstellungen → CAM-Addon (ab Werk aus).
Von Hand: in GitHub Desktop **Fetch origin**, dann **Pull origin** (bzw.
`git pull` im Ordner) und FreeCAD neu starten – so kommen auch kleine
Änderungen an, die noch keine neue Versionsnummer haben. Ein so installierter Git-Klon bleibt es auch, wenn das
Repository öffentlich wird; die Zeile oben lässt ihn in Ruhe.

## Lizenz

LGPL-2.1-or-later, wie FreeCAD selbst – siehe [LICENSE](LICENSE).
