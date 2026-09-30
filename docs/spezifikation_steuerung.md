# Spezifikation W-005: Programm für jede Steuerung

Stand: P-2026-09-30-42. **Manuel hat am 2026-09-30 entschieden:** Option A –
„A sollte unsere option sein“. Davor: „Sollte keine Rolle spielen …. Es muss
ja für alle funktionieren“ (welche Steuerung er selbst hat), passend zur
Festlegung „keine bestimmte Maschine“ in `CHATSTART.md`. Die Einzelheiten
sind Claudes Vorschläge, zur Besprechung (Abschnitt 9).

Grundlage: [spezifikation_maschine_aus_baugruppe.md](spezifikation_maschine_aus_baugruppe.md)
(Maschine, Betriebsarten, Aufnahmen), [spezifikation_vierachs.md](spezifikation_vierachs.md)
(Rundum-Operationen, G93, Postprozessoren von FreeCAD geprüft: P-2026-09-30-36).

## 1. Wozu

Die Postprozessoren von FreeCAD sind für Fräsmaschinen gebaut. Unsere
Rundum-Operationen laufen aber auch an Drehmaschinen mit C-Achse und
angetriebenem Werkzeug, und dort erwartet jede Steuerung anderes:

- **X im Durchmesser** – Siemens, Fanuc und Haas zählen X an der
  Drehmaschine von Haus aus als Durchmesser; unsere Bahn rechnet den Radius.
- **Drehzahl des angetriebenen Werkzeugs** – `M3 S…` dreht an der
  Drehmaschine die Hauptspindel, also das Teil. Haas schreibt
  `M133 P<Drehzahl>` (aus: `M135`), Siemens spricht die Spindel mit ihrer
  Nummer an (`M3=3 S3=…` oder `SETMS(3)`), bei Fanuc legt der
  Maschinenhersteller die M-Befehle fest.
- **C-Achse ein und aus** – Haas `M154`/`M155`, Siemens positioniert die
  Hauptspindel (`SPOS`), Fanuc: M-Befehl des Herstellers.
- **Vorschub** – G93 (1 ÷ Zeit) gibt es an Fräsmaschinen fast überall, an
  Drehmaschinen nicht immer. Bei Fanuc-Drehmaschinen im G-Code-System A ist
  **G94 ein Plandrehzyklus**, Vorschub je Minute heißt dort **G98**.
- **Werkzeugwechsel** – an der Drehmaschine `T0101` (Fanuc) bzw. `T1 D1`
  (Siemens) statt `T1 M6`.

Mantel- und Stirnfräsen mit Transformation (Fanuc G07.1/G12.1, Siemens
TRACYL/TRANSMIT) gibt es auch; unsere Operationen fahren X, Z und C direkt
(Abschnitt 6).

## 2. Was es schon gibt

- **Unser Maschinenmodell** (W-001) kennt die Betriebsarten – Hauptspindel
  S1, C1 (Positionieren der Hauptspindel), Werkzeugantrieb S3 – und je
  Aufnahme die Spindel, die das Werkzeug dreht. Daraus weiß der
  Postprozessor, ob ein Werkzeug angetrieben ist, welche Nummer sein Antrieb
  hat (S3 → 3) und dass C die Hauptspindel positioniert.
- **Der Job merkt sich seine Maschine** (Pfad der Datei, D-20).
- **Wochen-Build:** Die CAM-Maschinendefinition hat einen Postprozessor mit
  eigenen Eigenschaften, Ausgabeoptionen und einen Umbruch für Rundachsen
  (fortlaufend, 0–360°, neu nullen). Addons melden Postprozessoren über
  `package.xml` (Inhalt „Postprocessor“) oder `Path.Preferences.addAddonPostPath`
  an. **1.1.x** kennt nur den Makro-Ordner und FreeCADs eigene Ordner.

## 3. Die Steuerung an der Maschine

In **„Maschine bearbeiten“** eine Zeile **Steuerung** mit Auswahl:
LinuxCNC, Siemens 840D, Fanuc, Haas, Mach3/Mach4, „Eigene“. Je Wahl sind die
**Befehle** vorbelegt; jeder lässt sich ändern, weil manches der
Maschinenhersteller festlegt. Ein gelber Satz sagt das dazu.

| Befehl | LinuxCNC | Siemens 840D | Fanuc | Haas |
|---|---|---|---|---|
| Werkzeugwechsel Fräsen | `T1 M6` | `T1 M6` | `T1 M6` | `T1 M6` |
| Werkzeugwechsel Drehen | `T1 M6` | `T1 D1` | `T0101` | `T101` |
| Hauptspindel | `M3 S…` | `M3 S…` | `M3 S…` | `M3 S…` |
| Angetriebenes Werkzeug | `M3 $1 S…` | `M3=3 S3=…` | vom Hersteller | `M133 P…` |
| … aus | `M5 $1` | `M5=3` | vom Hersteller | `M135` |
| C-Achse ein / aus | – | `SPOS=0` / `M5` | vom Hersteller | `M154` / `M155` |
| X an der Drehmaschine | Radius (`G8`) | Durchmesser | Durchmesser | Durchmesser |
| Vorschub 1 ÷ Zeit | `G93` | `G93` | `G93` | `G93` |
| Vorschub je Minute | `G94` | `G94` | `G94` (Fräsen), `G98` (Drehen) | `G94` (Fräsen), `G98` (Drehen) |

Die Nummer des Antriebs (hier 3) kommt aus der Maschine. Werte, die nicht
aus einer Herstelleranleitung nachgeprüft sind, stehen in der Tabelle der
Prüfungen als „vorbelegt, bitte vergleichen“ und im Fenster mit demselben
Hinweis.

## 4. Der Postprozessor des Addons

- Heißt **„camaddon“** und steht in der Liste der Postprozessoren des Jobs.
  Der Kern liegt in `camaddon/postprozessor.py` (ohne Oberfläche, prüfbar),
  eine dünne Datei `posts/camaddon_post.py` meldet ihn bei FreeCAD an.
- Er schreibt **alle** Operationen des Jobs, nicht nur unsere: G0, G1, G2,
  G3, Bohrzyklen, Werkzeugwechsel, Spindel, Kühlmittel, Kommentare – mit den
  Befehlen der Steuerung. Für jedes Werkzeug fragt er die Maschine, ob es
  angetrieben ist.
- Unsere Rundum-Bahnen: X als Durchmesser, wo die Steuerung es so zählt;
  vor der Bahn C-Achse ein, danach aus; G93 … Vorschub je Minute mit dem
  Befehl der Steuerung; F in jedem Satz.
- **Ohne Steuerung am Job** schreibt er wie LinuxCNC – dann ist nichts
  schlechter als heute.
- Programmkopf und -fuß bleiben frei eintragbar wie bei FreeCAD.

## 5. Vorschub ohne G93

Kennt eine Steuerung G93 in dieser Betriebsart nicht, rechnet der
Postprozessor F so, dass die Zeit stimmt: F = √(ΔX² + ΔZ² + ΔC²) ÷ Zeit, mit
C in Grad – so zählen Steuerungen wie Fanuc den Weg, wenn Linear- und
Rundachsen zusammen fahren. Die Zeit kommt aus unserer Bahn (dieselbe wie
für G93). Das ist E5 in Abschnitt 9.

## 6. Später: Mantel und Stirn mit Transformation

Zylinder-Interpolation (Fanuc G07.1, Siemens TRACYL) und Polar-Interpolation
(Fanuc G12.1, Siemens TRANSMIT) rechnen in der Steuerung um; die Bahn steht
dann abgewickelt bzw. in X/Y. Das passt zu Strategien wie „Linien längs“ und
„Plan indexiert“ (V4c) und wird mit ihnen geplant, nicht in dieser Stufe.

## 7. Prüfen

- Je Voreinstellung eine **Musterausgabe**: derselbe Job (Welle an der
  Beispiel-Drehmaschine, Rundum schruppen mit angetriebenem Werkzeug; eine
  Tasche an der 3-Achs-Fräse) ergibt Satz für Satz das erwartete Programm
  (`tests/daten/programm_*.nc`).
- Das Prüffenster sagt, welcher Postprozessor und welche Steuerung gelten,
  und warnt, wenn der Job einen anderen Postprozessor nimmt, obwohl die
  Maschine eine Steuerung hat.

## 8. Stufen

- **S1** – Postprozessor „camaddon“ mit dem Verhalten von LinuxCNC (Fräsen),
  angemeldet in 1.1.x und im Wochen-Build. Prüfung: gleiche Sätze wie
  `linuxcnc_post` für einen 3-Achs-Job und für Rundum schruppen.
- **S2** – Steuerung und Befehle an der Maschine („Maschine bearbeiten“),
  der Job bekommt sie beim Anlegen (4-Achs-Assistent) und beim Prüfen auf der
  Maschine. Szenario.
- **S3** – Drehmaschine: Durchmesser, angetriebenes Werkzeug, C-Achse ein
  und aus, Werkzeugwechsel, Vorschub je Minute je Steuerung; Musterausgaben
  für LinuxCNC, Siemens, Fanuc, Haas.
- **S4** – Vorschub ohne G93 (Abschnitt 5).
- **S5** – Wochen-Build: „An CAM übergeben“ trägt Postprozessor und Steuerung
  in die CAM-Maschine ein.
- **S6** – Hilfe, Beispiel-Drehmaschine mit Steuerung, Szenario mit dem
  fertigen Programm.

## 9. Entscheidungen (zur Besprechung)

- **E1 – Welche Steuerungen zuerst?**
  (a) LinuxCNC, Siemens 840D, Fanuc, Haas, Mach3/Mach4 und „Eigene“ –
  **Empfehlung**, die häufigsten, alles Weitere über „Eigene“;
  (b) dazu Heidenhain (DIN/ISO), Mazak, Okuma – mehr Arbeit, jede braucht
  Musterausgaben; (c) nur „Eigene“ mit leeren Feldern – schnell, aber jeder
  muss alles selbst wissen.
- **E2 – Wo steht die Steuerung?**
  (a) an der Maschine, der Job bekommt beim Verbinden eine Kopie –
  **Empfehlung**: Das Programm lässt sich auch schreiben, wenn die
  Maschinendatei gerade nicht offen ist; (b) nur am Job – jeder Job einzeln
  einstellen; (c) der Postprozessor öffnet jedes Mal die Maschinendatei –
  langsam, und ohne die Datei geht nichts.
- **E3 – Anmelden in FreeCAD 1.1.x:**
  (a) beim Start den Suchpfad von CAM um den Ordner des Addons erweitern –
  **Empfehlung**, es wird nichts kopiert; (b) die Datei in den Makro-Ordner
  kopieren – sichtbar für den Benutzer, bleibt beim Entfernen des Addons
  liegen.
- **E4 – X an der Drehmaschine:**
  (a) wie die Steuerung von Haus aus zählt (Siemens, Fanuc, Haas:
  Durchmesser; LinuxCNC: wie eingestellt) – **Empfehlung**, der Bediener
  liest, was er gewohnt ist; (b) immer Radius und im Programm umschalten
  (`DIAMOF`, `G8`) – ein Befehl mehr, der vergessen werden kann.
- **E5 – Steuerungen ohne G93:**
  (a) Vorschub wie in Abschnitt 5 – **Empfehlung**, dann geht es auch dort;
  (b) nur Steuerungen mit G93 – einfacher, aber nicht für alle.
