# Vorbereitete Entwürfe – noch nicht übernommen

Diese Patches sind nicht im Addon aktiv und nicht als bestanden qualifiziert.
Der Undo-Observer beweist den vorzeitigen Transaktionsabschluss beim nativen
Standardwerkzeugimport. Der ursprüngliche Stockreihenfolge-Kandidat ist deshalb
kein belegter Fix. Kandidat ist nun der Ebenenjob ohne unbenutzten Standardimport;
vor Übernahme Undo/Redo, echter Ebenenjob mit Operation und Speichern/Wiederöffnen
prüfen. Abfahren-/Schwenkteil-Gegenproben erst mit ihren echten Fehlbelegen und
unverändert strengen positiven Kriterien übernehmen. QScreen-Testkorrekturen fehlen
noch. Produktdateien während des laufenden V4b-Gesamtlaufs unverändert lassen.

Die genauen Patchdateien liegen im unveränderten [Patcharchiv](patches.tar.gz);
die Entwürfe bleiben außerhalb des aktiven Addoncodes.
