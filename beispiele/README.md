# Beispiele

Teile zum Ausprobieren – die Prüfungen in `tests/` bauen ihre Teile selbst, hier
liegen die echten.

| Datei | Was es ist | Wofür |
| --- | --- | --- |
| `platte_zapfen_tasche.FCStd` | Manuels Maßstab für die Strategien (2026-10-01): Platte 200 × 200 × 30, Zapfen Ø 20 × 20 bei (50, 50), Tasche Ø 45 × 20 bei (−50, −50); Job mit Rohteil 200 × 200 × 50 (oben am Zapfen), Werkzeug T1 VHM 12 (ae 1,5, ap 25, fz 0,1, vc 85), Operationen Planfräsen, Kontur Tasche, Kontur Zapfen | Zeiten je Strategie: `docs/spezifikation_strategien.md`, Abschnitt 11 |
| `test4achsbearbeitung.FCStd` | Manuels Testteil (2026-09-30): ein PartDesign-Körper, Loft 90 mm lang zwischen zwei D-Profilen 70 × 25 mm – vorn (z 0) mittig, hinten (z −90) um 13,5 mm nach oben versetzt; das Teil liegt hinten also nicht rund um die Achse | 4-Achs-Bearbeitung an der Drehmaschine: „Beispielmaschine laden …“ → Drehmaschine, dann „4-Achs-Bearbeitung“ und die Stirnfläche bei z 0 anklicken; Stange Ø 50. An diesem Teil wurden der Fehlalarm „blau“ hinter der Achse (P-2026-09-30-44) und das ausgeblendete Soll-Teil (-45) behoben |
