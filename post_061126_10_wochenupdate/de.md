# Wochen-Update: Neuigkeiten auf GitHub, Begriffe wie FreeCAD CAM, Halterdaten (0.345.8)

*2026-11-06*

Aktuelle Version 0.345.8 („Nach Updates suchen“ bietet sie an). Eine ruhige Woche an den Maschinen, darum ein kurzes Update.

## Neuigkeiten jetzt auf GitHub
Die Wochen-Updates stehen ab jetzt hier unter **Announcements**, die älteren im [Archiv](https://github.com/manuelhofer/freecad-cam-addon/tree/forum#readme). Fragen und Ideen gern unter [Q&A](https://github.com/manuelhofer/freecad-cam-addon/discussions/categories/q-a) und [Ideas](https://github.com/manuelhofer/freecad-cam-addon/discussions/categories/ideas), Fehler bitte als [Issue](https://github.com/manuelhofer/freecad-cam-addon/issues).

## Dieselben Wörter wie FreeCAD CAM
Die englischen Texte nehmen jetzt die Begriffe aus dem Glossar von FreeCAD CAM: **stock to leave** für das Aufmaß einer Operation (axial am Boden, radial an den Wänden) statt „allowance“, **stock** statt „blank“, **post-processor**, **horizontal/vertical feed**. Deutsch bleibt, wie es ist.

## Halterdaten berichtigt
Kennametal-ER-Spannzangenfutter (71 Größen): L9 im Katalog ist die Einspanntiefe bis zum Verstellweg, nicht die Länge der Spannmutter. Jetzt ist L9 die Einspanntiefe (Einrichtblatt, Mindest-Einspannlänge) und die Mutter hat ihre Länge nach DIN 6499. Bei den vier langen ER16-Futtern beginnt der dickere Körper jetzt 14 mm näher am Werkzeug, wie am echten Halter – vorher sah die Kollisionsprüfung dort einen schlankeren Halter. Hoffmann-Bohrer: 16 309 Größen (+75).

## FreeCAD-Wochen-Build 2026.11.04
Geprüft mit FreeCAD 27.1 dev (Wochen-Build 2026.11.04): alle 142 Prüfdateien grün. Die 181 Oberflächen-Szenarien (FreeCAD unsichtbar gestartet, jedes Fenster durchgeklickt) ebenso.

## Was bei FreeCAD kommt
FreeCAD CAM arbeitet an Haltern am Werkzeug (FreeCAD PR 33379) und an einem Simulator mit Rundachsen und geschwenkten Ebenen (FreeCAD issue 29758); an der Werkzeugrichtung wird auch gearbeitet. Sobald das in FreeCAD ist, nimmt das Addon es statt der eigenen Fassungen – die Halter aus den Katalogen als FreeCAD-Halter, das Prüfen über FreeCADs Simulator.
