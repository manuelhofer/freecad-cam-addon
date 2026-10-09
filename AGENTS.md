# AGENTS.md

**Lies zuerst [CHATSTART.md](CHATSTART.md).** Dort steht, was das Projekt ist, wie
gearbeitet wird und welche Datei zu welcher Aufgabe gehört. Diese Datei ist nur der
Wegweiser für Werkzeuge, die zuerst nach `AGENTS.md` suchen (Codex und andere) –
alles Verbindliche steht werkzeugneutral in `CHATSTART.md` und
[docs/arbeitsregeln.md](docs/arbeitsregeln.md), damit keine zweite, driftende
Fassung entsteht.

Drei Punkte, die dort stehen und trotzdem oft übersehen werden:

- **Prüfungen so schlank wie möglich, so groß wie nötig** (`docs/arbeitsregeln.md`,
  Abschnitt 5): eine Sache an der kleinsten Geometrie, Richtwert fünf Minuten; ein
  Referenztest rechnet nur die Gewinnervariante nach. Kein Test, der ein ganzes
  Beispiel in allen Varianten nachrechnet.
- **1 Patch = 1 Thema**, Patch-ID `P-YYYY-MM-DD-XX` im Commit-Betreff, Eintrag in
  `docs/archiv/DEV_PROMPT_HISTORY.md` im selben Commit, `docs/STATUS_SNAPSHOT.md`
  nachgezogen.
- **Gepusht wird nur auf ausdrückliche Ansage** von Manuel.
