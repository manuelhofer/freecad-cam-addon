# Übersetzungen / Translations

**Deutsch:** Jede Sprache ist eine JSON-Datei in diesem Ordner. Eine neue
Sprache anlegen:

1. `en.json` kopieren und nach dem Sprachcode benennen, z. B. `it.json`,
   `es.json`, `fr.json`.
2. `"_sprache"` auf den Namen der Sprache in der Sprache selbst setzen
   (`"Italiano"`, `"Español"` …) – so erscheint sie in der Auswahl.
3. Nur die **Werte** rechts übersetzen, die **Schlüssel** links nie ändern.
   Platzhalter in geschweiften Klammern (`{name}`) unverändert übernehmen.
4. Datei als UTF-8 speichern. Nach einem Neustart von FreeCAD steht die
   Sprache in den Einstellungen des Addons zur Auswahl.

Fehlt ein Text, zeigt das Addon ihn auf Englisch – eine halb fertige
Übersetzung funktioniert also schon.

Die ausführlichen Hilfetexte liegen in `help/<sprachcode>/` als HTML-Seiten.
Für eine neue Sprache den Ordner `help/en` kopieren (z. B. nach `help/it`) und
die Texte übersetzen; Dateinamen und Verweise (`href="…"`) nicht ändern.

**English:** Every language is one JSON file in this folder. To add a
language:

1. Copy `en.json` and name it after the language code, e.g. `it.json`.
2. Set `"_sprache"` to the language's own name (`"Italiano"`, `"Español"` …) –
   that is how it appears in the language list.
3. Translate only the **values** on the right; never change the **keys** on
   the left. Keep placeholders in curly braces (`{name}`) as they are.
4. Save as UTF-8. After restarting FreeCAD the language can be chosen in the
   add-on's preferences.

Missing texts are shown in English, so a partial translation already works.

The detailed help pages live in `help/<language code>/` as HTML files. For a
new language copy the folder `help/en` (e.g. to `help/it`) and translate the
texts; do not change file names or links (`href="…"`).
