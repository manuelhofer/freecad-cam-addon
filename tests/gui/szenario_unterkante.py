# Der Rest an der Unterkante beim 3D-Schlichten (B-033): Eine Kuppel R 20, die am Teilboden endet
# (Kugel um (0, 0, −10), unten bei z 0 abgeschnitten: Fuß Ø 34,6, oben z 10). Seit 0.372.1 fährt die
# Kugel nie unter den Teilboden – an der Unterkante bleibt ein Rest stehen; bis dahin sagte es
# niemand (gesehen 2026-11-15: keine Fläche orange, nichts unter „Nicht fertig“).
# 1. T1 der Standardfräser Ø 12, T3 eine Kugel Ø 6, T5 eine Kugel Ø 2. Die Kuppel anklicken,
#    „Bearbeitung“, „Alles vorschlagen“: Die Übersicht sagt „An der Unterkante bleibt ein Rest bis
#    1,… mm hoch (rot im Teil)“ mit dem Verweis „Restschlichten mit T5 anhaken“ (der kommt aus
#    einem eigenen Auftrag: Hals, Schaft und Halter von T5 bleiben frei); der Satz unter
#    „3D-Schlichten“ ebenso (gerechnet: Kugel r 3 berührt zuletzt bei z = 1,5 ÷ 1,15 = 1,30). Im
#    Teil eine rote Linie um den Rest. Der Verweis: „Restschlichten“ mit T5 angehakt, die
#    Übersicht sagt weniger (gerechnet 0,49), ohne Verweis.
# 2. Nur T1 und T3: Der Verweis heißt „Kugel Ø 3 anlegen und Restschlichten anhaken“; er legt eine
#    Kugel Ø 3 an, wie man sie kauft (Schaft Ø 6 mit Hals Ø 2,9 – nicht den Schaft Ø 6 des
#    Vorbilds ab der Schneide, Zweifler 2026-11-15), und hakt das Restschlichten mit ihr an.
# Bilder: 1_uebersicht, 2_teil (rote Linie am Fuß), 3_schlichten, 4_nach_rest, 5_anlegen,
# 6_angelegt.
# ZEITLIMIT: 1200
import re

import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector
NEUES_FENSTER = True  # „Bearbeitung“ in Schritten


def _kugel(wz, nummer, d, **masse):
    k = wz.Werkzeug(
        nummer=nummer,
        name=f"Kugel {d:g}",
        art=wz.KUGELFRAESER,
        durchmesser=d,
        schneiden=2,
        schneidenlaenge=3 * d,
        schneidstoff=wz.VHM,
        **masse,
    )
    k.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    return k


def _hoehe(text):
    """Die Zahl aus „… bis 1,3 mm …“ – oder None."""
    treffer = re.search(r"bis (\d+(?:,\d+)?) mm", text)
    return float(treffer.group(1).replace(",", ".")) if treffer else None


def _oeffnen(h, doc, teil, kuppel):
    """Kuppel anklicken, „Bearbeitung“, „Alles vorschlagen“, warten, bis alles gerechnet ist."""
    from camaddon import gui_bearbeitung
    from camaddon import gui_bearbeitung_beta as beta

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, kuppel)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 60000)
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(isinstance(panel, beta.BetaPanel), f"nicht in Schritten: {type(panel).__name__}")
    if panel is None or panel.job is None:
        return
    panel.knopf_alles.click()
    yield 1500
    yield from _gerechnet(h, panel)


def _gerechnet(h, panel):
    def fertig():
        return not panel.vorschau_laeuft() and all(
            b.vorschau is not None or not b.aktiv() or b.gerechnet for b in panel.bloecke
        )

    yield 1000
    yield from h.warte_auf(fertig, 300000)
    yield 2000


def _mit_verweis(h, panel):
    """Warten, bis der Verweis der Empfehlung in der Übersicht steht (ein eigener Auftrag)."""
    yield from h.warte_auf(lambda: _verweis(panel.uebersicht_text.text())[0] is not None, 120000)
    yield 1000


def _verweis(text):
    treffer = re.search(r"href=['\"]([^'\"]+)['\"]>([^<]*)</a>", text or "")
    return (treffer.group(1), treffer.group(2)) if treffer else (None, None)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_bearbeitung
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import werkzeuge as wz

    # T5 20 mm ausgespannt: Der Halter bleibt über der Kuppel (10 hoch) – geschätzt wären es 11.
    t5 = _kugel(wz, 5, 2.0, gesamtlaenge=50.0, ausspannlaenge=20.0)
    wz.Bibliothek([wz.standardwerkzeug(), _kugel(wz, 3, 6.0), t5]).speichern()
    doc = FreeCAD.newDocument("Kuppel")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Kuppel")
    teil.Shape = Part.makeSphere(20, V(0, 0, -10)).common(Part.makeBox(50, 50, 15, V(-25, -25, 0)))
    doc.recompute()
    kuppel = next(
        f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if isinstance(f.Surface, Part.Sphere)
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")

    # --- 1. Mit einer kleineren Kugel in der Werkzeugverwaltung ---------------------------------
    yield from _oeffnen(h, doc, teil, kuppel)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    if panel is None or panel.job is None:
        return
    block = panel.schlichten3d
    h.pruefe(block.aktiv() and block.fraeser().nummer == 3, "3D-Schlichten nicht mit T3")
    yield from _mit_verweis(h, panel)
    satz = block.ergebnis.text()
    uebersicht = panel.uebersicht_text.text()
    print(ascii(f"3D-Schlichten: {satz!r}"), flush=True)
    print(ascii(f"Übersicht: {uebersicht!r}"), flush=True)
    unterkante = getattr(block.vorschau, "unterkante", None)
    h.pruefe(unterkante is not None and unterkante.linien, f"kein Rest gemessen: {unterkante}")
    hoehe = _hoehe(satz)
    h.pruefe(
        "An der Unterkante bleibt ein Rest bis" in satz
        and hoehe is not None
        and 1.2 <= hoehe <= 1.7
        and " hoch" in satz,
        f"Satz unter 3D-Schlichten: {satz!r}",
    )
    ziel, knopf = _verweis(uebersicht)
    h.pruefe(
        "An der Unterkante bleibt ein Rest bis" in uebersicht and "rot im Teil" in uebersicht,
        f"Übersicht: {uebersicht!r}",
    )
    h.pruefe(knopf == "Restschlichten mit T5 anhaken", f"Verweis in der Übersicht: {knopf!r}")
    h.pruefe(not panel.restschlichten.aktiv(), "Restschlichten schon angehakt")
    h.bild("1_uebersicht", panel.form)
    # Im Teil: die Wege und eine dicke rote Linie um den Rest am Fuß.
    vorschau = panel._bahnvorschau
    h.pruefe(
        vorschau is not None
        and vorschau.wurzel is not None
        and vorschau.kennung[0] == "uebersicht",
        "keine Wege im Teil",
    )
    if vorschau is not None and vorschau.wurzel is not None:
        # Je Weg ein Teil der Szene; die Linien um den Rest kommen dazu.
        teile = vorschau.wurzel.getNumChildren()
        h.pruefe(teile >= 3 + len(unterkante.linien), f"{teile} Teile in der Szene")
    # Nur die Zeile „3D-Schlichten“ angeklickt: ihre Wege und die rote Linie, schräg von vorn.
    panel._uebersicht_verweis(beta.ZEIGE + "schlichten3d")
    yield 800
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_teil")
    panel._uebersicht_verweis(beta.ZEIGE + "schlichten3d")  # wieder alle
    yield 500
    panel.seite_zeigen(beta.abschnitt(block) + beta.ERSTER_ABSCHNITT)
    yield 1500
    h.pruefe(block.ergebnis.isVisible(), "der Satz mit dem Verweis fehlt im Schritt „Schlichten“")
    h.bild("3_schlichten", panel.form)
    panel.seite_zeigen(beta.UEBERSICHT)
    yield 800
    panel._uebersicht_verweis(ziel)
    yield from _gerechnet(h, panel)
    rest = panel.restschlichten
    h.pruefe(
        rest.aktiv() and rest.fraeser() is not None and rest.fraeser().nummer == 5,
        f"Restschlichten nicht mit T5: {rest.aktiv()} {rest.fraeser()}",
    )
    uebersicht = panel.uebersicht_text.text()
    print(ascii(f"Übersicht nach dem Verweis: {uebersicht!r}"), flush=True)
    print(ascii(f"Restschlichten: {rest.ergebnis.text()!r} {rest.hinweis.text()!r}"), flush=True)
    danach = _hoehe(uebersicht)
    h.pruefe(
        danach is not None and danach < 0.5 * hoehe and _verweis(uebersicht)[0] is None,
        f"Übersicht nach dem Restschlichten: {uebersicht!r}",
    )
    h.pruefe("Restschlichten" in uebersicht, "Restschlichten fehlt in der Übersicht")
    h.bild("4_nach_rest", panel.form)
    panel.reject()
    yield 1500

    # --- 2. Ohne kleinere Kugel: anlegen ---------------------------------------------------------
    wz.Bibliothek([wz.standardwerkzeug(), _kugel(wz, 3, 6.0)]).speichern()
    yield 500
    yield from _oeffnen(h, doc, teil, kuppel)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    if panel is None or panel.job is None:
        return
    yield from _mit_verweis(h, panel)
    uebersicht = panel.uebersicht_text.text()
    ziel, knopf = _verweis(uebersicht)
    print(ascii(f"Übersicht ohne T5: {uebersicht!r}"), flush=True)
    h.pruefe(knopf == "Kugel Ø 3 anlegen und Restschlichten anhaken", f"Verweis ohne T5: {knopf!r}")
    h.bild("5_anlegen", panel.form)
    if ziel is None:
        return
    panel._uebersicht_verweis(ziel)
    yield from _gerechnet(h, panel)
    bibliothek = wz.Bibliothek.laden()
    neu = [w for w in bibliothek.werkzeuge if w.art == wz.KUGELFRAESER and w.durchmesser == 3.0]
    h.pruefe(len(neu) == 1, f"keine Kugel Ø 3 angelegt: {[w.name for w in bibliothek.werkzeuge]}")
    rest = panel.restschlichten
    h.pruefe(
        rest.aktiv() and rest.fraeser() is not None and rest.fraeser().durchmesser == 3.0,
        f"Restschlichten nicht mit der neuen Kugel: {rest.fraeser()}",
    )
    if neu:
        k = neu[0]
        masse = f"Schaft {k.schaft}, Hals {k.hals_d} x {k.hals_laenge}, L {k.gesamtlaenge}"
        print(
            ascii(f"Neu: T{k.nummer} {k.name}, Schneide {k.schneidenlaenge}, {masse}"), flush=True
        )
        h.pruefe(
            k.schaft == 6.0 and abs(k.hals_d - 2.9) < 1e-9 and k.hals_laenge == 9.0,
            f"neue Kugel: Schaft {k.schaft}, Hals {k.hals_d} × {k.hals_laenge}",
        )
    uebersicht = panel.uebersicht_text.text()
    print(ascii(f"Übersicht danach: {uebersicht!r}"), flush=True)
    h.pruefe(_hoehe(uebersicht) is not None and _hoehe(uebersicht) < 1.0, f"{uebersicht!r}")
    h.bild("6_angelegt", panel.form)
    panel.reject()
    yield 1000
