# Sicherung der lokalen Prüfumgebung

`lokale-pruefwerkzeuge.tar.gz` enthält nur eigene Läufer, Instrumentierung und
Starter, keine Profile, keine persönliche Bibliothek und keine FreeCAD-Dateien.
Die Skripte sind ein genauer Linux-Arbeitszwischenstand mit den vorhandenen
lokalen Pfaden; sie sind keine neue plattformübergreifende Addonfunktion.
Vor fremdem Einsatz Pfade/Quelle/Ausgabe prüfen, jeden Profilordner vorher anlegen,
App-home vor Datenzugriff prüfen und keine zweite FreeCAD-Prüfung parallel starten.
GUI nach DP-1, pro Prozess 16-GiB-Deckel ohne Swap. Fachliche Referenzen nicht neu schreiben.

Aktive Ausgabe: `gesamtstand-v4b`, Session45128. Der V4b-Läufer übernimmt nur
bytegleiche bestandene Native-Belege und wiederholt alle GUI-Fälle. Die zusätzliche
Undo-Gegenprobe wertet vollständigen Objektbestand statt nur die alte Jobliste.
Ungeprüfte Reparaturentwürfe separat in `entwuerfe/`, nicht in den aktiven Produktdateien.
Die reale Starterprüfung wartet bis nach der GUI-Runde.
