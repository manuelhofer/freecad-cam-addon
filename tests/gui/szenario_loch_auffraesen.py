# Loch auffräsen (Manuels Weg, W-002): Sackloch Ø 30, 25 mm tief; Adaptiv mit
# dem Boden als Basisgeometrie. „Schnittwerte in den Job“ legt den
# Werkzeug-Controller „T3 Schruppen dynamisch“ an; mit ihm zeigt der Dialog
# 2 Ebenen (25 + 1 mm – FreeCAD legt das Rohteil 1 mm über das Modell) und
# sagt, wie die dünne entfällt; „ap 26 mm übernehmen“ ändert den Einsatz in der
# Werkzeugverwaltung, und der Dialog zeigt 1 Ebene (D-29). Rohteil oben bündig
# → 1 Ebene. Übernehmen → das Adaptiv taucht einmal helikal bis 25 mm ein und
# räumt nur dort.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui


def dialog_oeffnen():
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_SchnittwerteJob"))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 300
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.German, QtCore.QLocale.Germany))

    import Part  # noqa: F401 – für „Part::Box“ und „Part::Cut“
    from Path.Main import Job
    from Path.Op import Adaptive

    from camaddon import gui_job_schnittwerte as gj
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    fraeser = wz.Werkzeug(
        nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26, eintauchwinkel=3
    )
    fraeser.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15),
    ]
    bibliothek = wz.Bibliothek([fraeser])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)

    # Quader 60 × 60 × 30 mit Sackloch Ø 30, Boden bei z = 5.
    dok = FreeCAD.newDocument("Loch")
    quader = dok.addObject("Part::Box", "Quader")
    quader.Length, quader.Width, quader.Height = 60, 60, 30
    bohrung = dok.addObject("Part::Cylinder", "Bohrung")
    bohrung.Radius, bohrung.Height = 15, 26
    bohrung.Placement.Base = FreeCAD.Vector(30, 30, 5)
    teil = dok.addObject("Part::Cut", "Teil")
    teil.Base, teil.Tool = quader, bohrung
    dok.recompute()
    job = Job.Create("Job", [teil])
    # Anlegen, solange der Job nur einen TC hat – sonst fragt FreeCAD, welchen.
    adaptiv = Adaptive.Create("Adaptiv", parentJob=job)
    modell = job.Model.Group[0]
    boden = [
        f"Face{i + 1}"
        for i, f in enumerate(modell.Shape.Faces)
        if f.Surface.__class__.__name__ == "Plane"
        and abs(f.BoundBox.ZMin - 5) < 1e-6
        and abs(f.BoundBox.ZMax - 5) < 1e-6
    ]
    h.pruefe(len(boden) == 1, f"Boden der Bohrung: {boden}")
    adaptiv.Base = [(modell, boden)]
    dok.recompute()
    yield 300

    # Werkzeug-Controller hinzufügen: T3 → Schruppen dynamisch.
    dialog_oeffnen()
    yield 1000
    d = gj.SchnittwerteJobDialog.offen
    h.pruefe(d is not None and d.isVisible(), "Dialog geht nicht auf")
    if d is None:
        return
    d._menue_tc_neu_fuellen()
    werkzeuge = d.menue_tc_neu.actions()
    h.pruefe(len(werkzeuge) == 1 and werkzeuge[0].menu() is not None, "Menü der Werkzeuge")
    if len(werkzeuge) != 1 or werkzeuge[0].menu() is None:
        return
    werkzeuge[0].menu().actions()[0].trigger()
    yield 500
    d.reject()
    yield 300
    tc = next((t for t in job.Tools.Group if t.Label == "T3 Schruppen dynamisch"), None)
    h.pruefe(tc is not None, f"TC fehlt: {[t.Label for t in job.Tools.Group]}")
    if tc is None:
        return
    # Wie im Aufgabenfenster der Operation: den neuen Controller wählen.
    adaptiv.ToolController = tc
    dok.recompute()
    yield 300

    # Das Rohteil steht 1 mm über dem Modell: 26 mm ab Oberkante, also 25 + 1.
    dialog_oeffnen()
    yield 1000
    d = gj.SchnittwerteJobDialog.offen
    zeilen = {d.tabelle.item(z, gj.TC).text(): z for z in range(d.tabelle.rowCount())}
    z = zeilen.get("T3 Schruppen dynamisch")
    h.pruefe(z is not None, f"Zeilen: {sorted(zeilen)}")
    if z is None:
        return
    zustellung = d.tabelle.item(z, gj.ZUSTELLUNG).text()
    h.pruefe(
        zustellung == "Adaptiv: 10 % · 25 mm · Helix 3° · 2 Ebenen (25 + 1 mm)",
        f"Zustellung: {zustellung!r}",
    )
    hinweis = d.ebenen_hinweis.text()
    h.pruefe(d.ebenen_hinweis.isVisible(), "kein Hinweis zur dünnen Ebene")
    for teil_text in ("nur 1 mm dick", "„Erw. Z“ rechts", "Mit ap 26 mm im Einsatz entfällt sie"):
        h.pruefe(teil_text in hinweis, f"„{teil_text}“ fehlt im Hinweis: {hinweis!r}")
    h.bild("1_zwei_ebenen", d)
    # Ohne Zustellung: kein Hinweis.
    d.mit_zustellung.setChecked(False)
    yield 100
    h.pruefe(not d.ebenen_hinweis.isVisible(), "Hinweis trotz ausgeschalteter Zustellung")
    d.mit_zustellung.setChecked(True)
    yield 100

    # Der Vorschlag mit einem Klick (D-29): ap 26 mm in den Einsatz, gespeichert – eine Ebene.
    hinweis = d.ebenen_hinweis.text()
    h.pruefe("ap 26 mm übernehmen" in hinweis, f"Verweis fehlt: {hinweis!r}")
    verweis = next((v for _s, v in d._duenn.get(z, []) if v), None)
    h.pruefe(verweis is not None and verweis.startswith(f"ap:{z}:26"), f"Verweis: {verweis!r}")
    if verweis is not None:
        d.ebenen_hinweis.linkActivated.emit(verweis)
        yield 300
        zustellung = d.tabelle.item(z, gj.ZUSTELLUNG).text()
        h.pruefe(
            zustellung == "Adaptiv: 10 % · 26 mm · Helix 3° · 1 Ebene",
            f"nach „ap 26 mm übernehmen“: {zustellung!r}",
        )
        h.pruefe(not d.ebenen_hinweis.isVisible(), "Hinweis nach dem Übernehmen noch da")
        gespeichert = wz.Bibliothek.laden().mit_nummer(3)
        dynamisch = next(e for e in gespeichert.einsaetze(wz.ALLE) if e.art == wz.DYNAMISCH)
        h.pruefe(dynamisch.ap == 26, f"ap in der Werkzeugverwaltung: {dynamisch.ap}")
        h.bild("1b_ap_uebernommen", d)
        # Für die folgenden Schritte wieder ap 25 – wie in der Datei vorher.
        bibliothek = wz.Bibliothek.laden()
        for einsatz in bibliothek.mit_nummer(3).einsaetze(wz.ALLE):
            if einsatz.art == wz.DYNAMISCH:
                einsatz.ap = 25
        bibliothek.speichern()
    d.reject()
    yield 300

    # Rohteil oben bündig (Erw. Z rechts = 0): eine Ebene, kein Hinweis. Die
    # Operation rechnet FreeCAD danach nicht von selbst neu – wie im Baum
    # „Objekt neu berechnen“.
    job.Stock.ExtZpos = FreeCAD.Units.Quantity("0 mm")
    dok.recompute()
    adaptiv.touch()
    dok.recompute()
    yield 300
    dialog_oeffnen()
    yield 1000
    d = gj.SchnittwerteJobDialog.offen
    zustellung = d.tabelle.item(z, gj.ZUSTELLUNG).text()
    h.pruefe(zustellung == "Adaptiv: 10 % · 25 mm · Helix 3° · 1 Ebene", f"bündig: {zustellung!r}")
    h.pruefe(
        not d.ebenen_hinweis.isVisible(), f"Hinweis bei einer Ebene: {d.ebenen_hinweis.text()!r}"
    )
    h.bild("2_eine_ebene", d)
    d.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 800
    meldung = h.modal()
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    else:
        h.pruefe(False, f"keine Meldung nach Übernehmen: {meldung}")
    yield 300
    dok.recompute()
    yield 500

    # Die Bahn: einmal helikal bis 5 mm (25 unter der Oberkante), danach nur dort.
    befehle = adaptiv.Path.Commands
    kommentare = [b.Name for b in befehle if b.Name.startswith("(")]
    helix = [k for k in kommentare if "Helix to depth" in k]
    h.pruefe(len(helix) == 1 and "5.0" in helix[0], f"Helix: {helix}")
    tiefen = [k for k in kommentare if "Adaptive - depth" in k]
    h.pruefe(len(tiefen) == 1 and "5.0" in tiefen[0], f"Ebenen: {tiefen}")
    start = next(i for i, b in enumerate(befehle) if "Adaptive - depth" in b.Name)
    geschnitten = {
        round(b.Parameters["Z"], 3)
        for b in befehle[start:]
        if b.Name in ("G1", "G2", "G3") and "Z" in b.Parameters
    }
    h.pruefe(geschnitten <= {5.0}, f"nach der Helix nicht nur auf z = 5: {sorted(geschnitten)}")
    z_min = min(b.Parameters["Z"] for b in befehle if "Z" in b.Parameters)
    h.pruefe(abs(z_min - 5) < 1e-6, f"tiefster Punkt {z_min}")
