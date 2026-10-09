# Annahmekriterien für Ebenenjob ohne Standardimport

Kandidat ist vorbereitet, noch nicht ausgeführt. Er verwendet einen eigenen Untertyp des nativen `Path.Main.Job.ObjectJob` und dessen regulären Konstruktor. Nur die native Methode `setFromTemplateFile` wird für neue Ebenenjobs ohne Werkzeugimport umgesetzt; native Dateien oder Klassen werden nicht verändert.

- Szenario `szenario_werkzeugzugang` mit der vollständigen Undo-/Redo-Gegenprobe: genau eine neue Undo-Zeile, keine Öffnung/Schließung eines ToolBit-Hilfsdokuments während der Ebenenjobtransaktion, Grundobjektbestand nach einem Undo identisch.
- Nach Redo: genau eine Ebene, Tools-Gruppe vorhanden und leer, Rohteilklon korrekt mit dem Grundrohteil verknüpft.
- Eine reale Räumoperation im Ebenenjob anlegen: echtes Standardwerkzeug über die bestehende Strategie auswählen, ursprüngliche geometrischen/NC-/Maschinengrenzen-Prüfungen beibehalten. `tests/test_schwenken.py` deckt diesen Weg ab.
- Ebenenjob speichern, Dokument schließen, Datei wieder öffnen: Proxy ist wieder `camaddon.schwenkjob.EbenenJob`, native Eigenschaften/Grundjob/Rundachsen/Ebene/Model/Stock/Tools erhalten, keine Report-Ausnahme. Eine vorhandene Operation nach Restore weiterhin exportierbar.
- Normales Löschen des Ebenenjobs darf Grundjob, Grundrohteil und dessen Werkzeugkörper nicht löschen. Keine gemeinsamen Tool-Objekte einführen.

Statische Randbedingungen:
- Native `integrityCheck` verlangt eine existierende Tools-Gruppe, keine vorgegebene Controlleranzahl.
- Der Bearbeitungsassistent liest reale Werkzeuge aus der Bibliothek und legt Controller je Operation an; der bisherige neue 5-mm-Standardcontroller war dafür nicht nötig.
- Eigener gespeicherter Proxy-Untertyp verlangt installierten Addon-Code beim späteren Laden; das trifft bereits auf eigene CAM-Operationsproxys zu, ist aber im Restore-Test explizit zu prüfen.
- Die globale persist-Option verhindert nur Command-Autoclose; sie schützt nicht vor dem gemessenen Commit des temporären ToolBit-Dokuments. Zwei Transaktionen wären zwei Undo-Schritte und erfüllen das Ziel nicht.
