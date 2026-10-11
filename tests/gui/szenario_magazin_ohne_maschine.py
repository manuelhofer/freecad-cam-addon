# Ein Magazin ohne Maschine (legros im Forum, 2026-10-10: „you can specify the pocket location, but
# it doesn't seem to take it into account“ – seine Beispielmaschine 5-Achs Tisch/Tisch war nicht
# gespeichert, ein Magazin gehört aber zu einer Maschinendatei): Die Beispielmaschine offen, nichts
# gespeichert, Werkzeugverwaltung → „Magazine …“ → „Neu“. Unten rot: Es gehört zu keiner Maschine,
# kein Job nimmt seine Nummern; daneben der Knopf „„Beispielmaschine“ speichern …“. Gespeichert
# gehört das Magazin zu ihr und gilt für sie, nichts mehr rot, der Knopf ist weg.
import os

import FreeCADGui as Gui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_werkzeuge
    from camaddon import maschinenspeicher as msp
    from camaddon import werkzeuge as wz

    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    h.pruefe(not asm.Document.FileName, "die Beispielmaschine liegt schon in einer Datei")
    wz.Bibliothek([wz.Werkzeug(nummer=1, name="VHM 6", durchmesser=6, schneiden=3)]).speichern()
    yield 500

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 1000
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None, "Werkzeugverwaltung öffnet nicht")
    if d is None:
        return
    m = d.magazine_zeigen()
    yield 600
    magazin = m.magazin_anlegen()
    m.aus_nummern()
    yield 300
    h.pruefe(not magazin.maschine, f"das neue Magazin hat eine Maschine: {magazin.maschine!r}")
    h.pruefe(
        "keiner Maschine" in m.probleme.text() and "Speichern" in m.probleme.text(),
        f"ohne Maschine nicht gemeldet: {m.probleme.text()!r}",
    )
    knopf = m.knopf_maschine_speichern
    h.pruefe(
        knopf.isVisible() and asm.Document.Label in knopf.text(),
        f"Knopf zum Speichern: sichtbar {knopf.isVisible()}, {knopf.text()!r}",
    )
    h.bild("1_ohne_maschine", m)

    pfad = os.path.join(os.environ["CAMADDON_AUSGABE"], "tisch_tisch.FCStd")
    h.pruefe(m.maschine_speichern(pfad) == pfad, "Speichern gab keinen Pfad")
    yield 500
    h.pruefe(
        msp.gleiche_datei(asm.Document.FileName, pfad) and msp.finde(msp.laden(), pfad) is not None,
        f"nicht gespeichert oder nicht im Speicher: {asm.Document.FileName!r}",
    )
    h.pruefe(
        msp.gleiche_datei(magazin.maschine, pfad) and magazin.gilt,
        f"Magazin: Maschine {magazin.maschine!r}, gilt {magazin.gilt}",
    )
    h.pruefe(not m.probleme.text(), f"noch rot: {m.probleme.text()!r}")
    h.pruefe(not knopf.isVisible(), "der Knopf ist noch da")
    h.bild("2_gespeichert", m)
    m.accept()
    yield 300
    d.accept()
    yield 300
