# „Schnittwerte in den Job“ (W-002 Stufe 2): Werkstoff vom Rohteil (1.4301),
# TC mit Werkzeug aus der Bibliothek „CAM-Addon“ bekommt den Einsatz aus
# seinem Namen, ein fremdes Werkzeug bleibt unberührt; „Übernehmen“ setzt
# Drehzahl und Vorschübe und im Adaptiv Schrittweite und Zustelltiefe, Strg+Z
# nimmt es zurück.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    import Materials
    import Part  # noqa: F401 – für „Part::Box“
    from Path.Main import Job
    from Path.Op import Adaptive
    from Path.Tool import Controller
    from Path.Tool.camassets import cam_assets

    from camaddon import gui_job_schnittwerte as gj
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    fraeser = wz.Werkzeug(
        nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26, eintauchwinkel=3
    )
    fraeser.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05),
        wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15),
    ]
    fraeser.eigene_anlegen("1.4301")[0].vc = 80
    bibliothek = wz.Bibliothek([fraeser])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)

    dok = FreeCAD.newDocument("Teil")
    dok.UndoMode = 1
    quader = dok.addObject("Part::Box", "Quader")
    dok.recompute()
    job = Job.Create("Job", [quader])
    # Anlegen, solange der Job nur einen TC hat – sonst fragt FreeCAD, welchen.
    adaptiv = Adaptive.Create("Adaptiv", parentJob=job)
    uuid = ue.freecad_werkstoffe()["1.4301"][0]
    job.Stock.ShapeMaterial = Materials.MaterialManager().getMaterial(uuid)
    bit = cam_assets.get(f"toolbit://camaddon_{fraeser.kennung}").attach_to_doc(doc=dok)
    tc1 = Controller.Create("T3 Schruppen dynamisch", tool=bit, toolNumber=3)
    job.Proxy.addToolController(tc1)
    tc2 = Controller.Create("TC fremd", toolNumber=9)  # FreeCADs Standard-Schaftfräser
    job.Proxy.addToolController(tc2)
    adaptiv.ToolController = tc1
    dok.recompute()
    vorher = (tc1.SpindleSpeed, tc2.SpindleSpeed)
    yield 500

    befehl = Gui.Command.get("CamAddon_SchnittwerteJob")
    h.pruefe(
        befehl is not None and befehl.isActive(), "Befehl nicht aktiv, obwohl es einen Job gibt"
    )
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_SchnittwerteJob"))
    yield 1000
    d = gj.SchnittwerteJobDialog.offen
    h.pruefe(d is not None and d.isVisible(), "Dialog geht nicht auf")
    if d is None:
        return
    h.pruefe(d.werkstoff == "1.4301", f"Werkstoff: {d.werkstoff!r}")
    zeilen = {d.tabelle.item(z, gj.TC).text(): z for z in range(d.tabelle.rowCount())}
    z1, z2 = zeilen.get("T3 Schruppen dynamisch"), zeilen.get("TC fremd")
    h.pruefe(z1 is not None and z2 is not None, f"Zeilen: {sorted(zeilen)}")
    if z1 is None or z2 is None:
        return
    einsatz = d.tabelle.cellWidget(z1, gj.EINSATZ).currentText()
    h.pruefe(einsatz == "Schruppen dynamisch", f"vorgeschlagen: {einsatz!r}")
    werte = (d.tabelle.item(z1, gj.N).text(), d.tabelle.item(z1, gj.VF).text())
    h.pruefe(werte == ("3183", "1432"), f"n/vf: {werte}")
    zustellung = d.tabelle.item(z1, gj.ZUSTELLUNG).text()
    h.pruefe(zustellung == "Adaptiv: 10 % · 25 mm · Helix 3°", f"Zustellung: {zustellung!r}")
    h.pruefe(d.tabelle.item(z2, gj.ZUSTELLUNG).text() == "", "fremder TC mit Zustellung")
    h.pruefe(not d.tabelle.cellWidget(z2, gj.EINSATZ).isEnabled(), "fremdes Werkzeug wählbar")
    h.pruefe("nicht in der Werkzeugverwaltung" in d.tabelle.item(z2, gj.WERKZEUG).text(), "fremd")
    h.bild("1_dialog", d)

    # Vollnut gewählt: für 1.4301 mit vc 80.
    d.waehle_einsatz(z1, 0)
    yield 100
    h.pruefe(
        d.tabelle.item(z1, gj.N).text() == "2122",
        f"Vollnut 1.4301: {d.tabelle.item(z1, gj.N).text()}",
    )
    d.waehle_einsatz(z1, 1)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 800
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        h.pruefe(
            "Gesetzt: 1 Werkzeug-Controller, dazu Schrittweite und Zustelltiefe in: Adaptiv."
            in meldung.text(),
            f"Meldung: {meldung.text()!r}",
        )
        h.bild("2_meldung", meldung)
        meldung.accept()
    else:
        h.pruefe(False, f"keine Meldung nach Übernehmen: {meldung}")
    yield 300
    h.pruefe(tc1.SpindleSpeed == 3183, f"TC 1: {tc1.SpindleSpeed} U/min")
    h.pruefe(round(float(tc1.HorizFeed.getValueAs("mm/min"))) == 1432, f"TC 1: {tc1.HorizFeed}")
    h.pruefe(
        round(float(tc1.VertFeed.getValueAs("mm/min"))) == 473, f"TC 1 senkrecht: {tc1.VertFeed}"
    )
    h.pruefe(tc2.SpindleSpeed == vorher[1], "fremder TC verändert")
    h.pruefe(float(adaptiv.StepDown.getValueAs("mm")) == 25, f"Adaptiv: {adaptiv.StepDown}")
    helix = getattr(adaptiv, "HelixMaxRampAngle", None) or adaptiv.HelixAngle
    h.pruefe(abs(float(helix.getValueAs("deg")) - 3) < 1e-9, f"Helixwinkel: {helix}")
    dok.undo()
    h.pruefe(tc1.SpindleSpeed == vorher[0], "Strg+Z nimmt es nicht zurück")

    # Werkzeug-Controller hinzufügen: Menü je Werkzeug mit seinen Einsätzen.
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_SchnittwerteJob"))
    yield 1000
    d = gj.SchnittwerteJobDialog.offen
    h.pruefe(d is not None and d.isVisible(), "Dialog geht nicht wieder auf")
    if d is None:
        return
    d._menue_tc_neu_fuellen()
    werkzeuge = d.menue_tc_neu.actions()
    h.pruefe(len(werkzeuge) == 1 and werkzeuge[0].menu() is not None, "Menü der Werkzeuge")
    if len(werkzeuge) != 1 or werkzeuge[0].menu() is None:
        return
    einsaetze = {a.text(): a for a in werkzeuge[0].menu().actions()}
    h.pruefe(
        sorted(einsaetze) == ["Schruppen dynamisch", "Vollnut"], f"Einsätze: {sorted(einsaetze)}"
    )
    einsaetze["Vollnut"].trigger()
    yield 500
    zeilen = {d.tabelle.item(z, gj.TC).text(): z for z in range(d.tabelle.rowCount())}
    h.pruefe("T3 Vollnut" in zeilen, f"neuer TC fehlt: {sorted(zeilen)}")
    if "T3 Vollnut" in zeilen:
        z = zeilen["T3 Vollnut"]
        h.pruefe(
            d.tabelle.cellWidget(z, gj.EINSATZ).currentText() == "Vollnut",
            f"Einsatz des neuen TC: {d.tabelle.cellWidget(z, gj.EINSATZ).currentText()!r}",
        )
        h.pruefe("2122" in d.tabelle.item(z, gj.JETZT).text(), "neuer TC ohne Drehzahl")
    h.bild("3_tc_neu", d)

    # Anderen Werkstoff wählen und am Rohteil eintragen.
    h.pruefe(d.knopf_am_rohteil.isHidden(), "„Am Rohteil eintragen“ für den Werkstoff, den es hat")
    d.wahl_werkstoff.setCurrentIndex(d.wahl_werkstoff.findData("1.0503"))
    yield 200
    h.pruefe(not d.knopf_am_rohteil.isHidden(), "„Am Rohteil eintragen“ fehlt für C45")
    d.knopf_am_rohteil.click()
    yield 300
    h.pruefe("1.0503" in d.herkunft.text(), f"Herkunft: {d.herkunft.text()!r}")
    h.pruefe(d.knopf_am_rohteil.isHidden(), "Knopf nach dem Eintragen noch da")
    h.bild("4_am_rohteil", d)
    d.reject()
