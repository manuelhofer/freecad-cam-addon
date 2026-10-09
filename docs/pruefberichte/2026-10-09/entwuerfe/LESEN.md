# B-016: statischer Befund, Gegenprobe vorbereitet

Noch keine Laufzeitprüfung und keine Änderung am Originalrepository. Root führt gerade die Gesamtqualifikation durch; kein paralleler FreeCAD-Start.

## Vorhandener reproduzierter Beleg

- `tests/gui/szenario_werkzeugzugang.py` legt über `SchwenkenPanel.accept()` eine seitliche Ebene mit gewinkeltem T8 an und ruft danach genau einmal `doc.undo()` auf.
- `/home/manuel/freecad_cam/ergebnisse/werkzeugzugang-2026-10-08/gui_final/uebernahme.json`: Namen nach Undo = ursprüngliche Namen plus `Clone002`; Ebenenliste leer. Die bisherige Prüfung erfasst nur Jobs, deshalb bleibt der Ressourcenrest unbeanstandet.

## Kleinster Korrekturkandidat, ausdrücklich unbestätigt

`stockreihenfolge-kandidat.patch` verschiebt die Zuweisung `job.Stock = rohteil` hinter die Entfernung des vorläufigen nativen Stock-Objekts. Diese Reihenfolge entspricht dem installierten FreeCAD 1.1.4: `/usr/lib/freecad/Mod/CAM/Path/Main/Gui/Job.py`, `StockEdit.setStock`, Zeilen 443–449; das Addon verwendet sie bereits in `vierachs_rohteil.richte_ein`.

Das ist ein gezielter Kandidat, kein bewiesener Fix. Aus dem bestehenden Artefakt allein kann nicht entschieden werden, ob die Link-Reihenfolge oder ein Transaktionsende beim nativen Job-/Werkzeugimport verantwortlich ist.

## Gegenprobe / Annahmekriterium

`vollstaendiger-undo-test.patch` erweitert genau das vorhandene Szenario:

1. Ein Undo stellt die vollständige ursprüngliche Namenmenge wieder her, einschließlich aller Rohteilklone.
2. Redo stellt genau einen Ebenenjob mit Stock-Ressourcenklon und Verknüpfung zum Grundrohteil wieder her.
3. Nach Verarbeitung der GUI-Ereignisse entfernt ein erneutes Undo alle hinzugefügten Objekte.

Zuerst gegen unveränderten Stand laufen lassen: erwartetes Scheitern durch Clone002. Dann nur Kandidat anwenden und dasselbe Szenario erneut laufen lassen. Erst bei erfolgreicher Gegenprobe als Fix übernehmen. Beide Profile vor Start anlegen, Datenordner vor Schreiben verifizieren, 16-GiB-Grenze, sichtbares Fenster DP-1.

Falls Kandidat nicht hilft: `transaktions-diagnose.patch` separat gegen den Originalstand anwenden. Es protokolliert öffentliche FreeCAD-Transaktionsdaten vor/nach `PathJob.Create`, Ressourcenklon und Stock-Ersatz. Der native Standardwerkzeugimport verwendet temporäre FCStd-Dokumente; ein verlorener aktiver Transaktionsbezug ist als alternative Ursache zu prüfen. Der Diagnosepatch darf nicht im Produkt verbleiben.
