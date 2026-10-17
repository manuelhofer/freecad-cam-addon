# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ein Teil aus einem STL – und sein Klon im Job – als Netz in der 3D-Ansicht (W-017).

FreeCAD baut die Anzeige eines Körpers Fläche für Fläche: am Geist (68.242 Dreiecke, jedes eine
Fläche) 1,7 s, in denen das Fenster steht – beim Umwandeln, beim ersten Klick (der Klon im Job),
beim Öffnen. Das Netz, aus dem der Körper besteht, trägt er schon (stl_teil.EIGENSCHAFT_NETZ); als
Coin-Knoten in seiner eigenen Anzeige (ViewObject.RootNode, unter ihrer Lage – er zieht mit, wenn
sich der Klon bewegt) kostet es 0,06 s. Für FreeCAD bleibt der Körper ausgeblendet (im Baum grau).

Die Dreiecke liegen in der Reihenfolge der Flächen (stl_teil.EIGENSCHAFT_FLAECHEN): Klickt man
eines an, wählt FreeCAD selbst „FaceN“ – die Assistenten merken keinen Unterschied. Hervorheben
(Auswahl grün, Vorauswahl gelb) und die Farben der Flächen zeichnet das Netz selbst. Blendet man
den Körper in FreeCAD ein (Leertaste), zeigt FreeCAD ihn wieder selbst, das Netz geht aus.

Gemerkt am Objekt (EIGENSCHAFT, mit gespeichert): Nach dem Öffnen und nach Rückgängig kommt das
Netz wieder. Ohne Oberfläche tut das Modul nichts.
"""

import contextlib
import sys

import FreeCAD

EIGENSCHAFT = "CamAddonNetzAnzeige"
KNOTEN = "CamAddonNetz"  # der Name des Coin-Knotens in der Anzeige des Objekts
# Die Kinder des Knotens (_bauen): Stoff, Bindung, Hinweise, Punkte, Dreiecke, Marken.
STOFF, BINDUNG, DREIECKE, MARKEN = 0, 1, 4, 5
AUSWAHL_FARBE = (0.11, 0.68, 0.11)
VORAUSWAHL_FARBE = (0.88, 0.88, 0.21)
NACHSEHEN_MS = 100
_DATEN = {}  # (Dokument, Körper, Dreiecke, Punkte) -> (Punkte, Index) für Coin
_DATEN_HOECHSTENS = 4
_BEOBACHTER = []
_gewaehlt = {}  # (Dokument, Objekt) -> {Nummer der Fläche (0 ist „Face1“)}
_vorgewaehlt = {}  # (Dokument, Objekt) -> Nummer


def mit_oberflaeche():
    return bool(getattr(FreeCAD, "GuiUp", False))


def vorbild(objekt):
    """Der Körper aus einem STL, dessen Netz `objekt` zeigt – er selbst oder, bei seinem Klon
    (Draft, wie das Modell eines Jobs, ohne Maßstab), das Vorbild; sonst None."""
    from . import stl_teil

    try:
        if stl_teil.aus_stl(objekt):
            return objekt
        if type(getattr(objekt, "Proxy", None)).__name__ != "Clone":
            return None
        vorbilder = list(getattr(objekt, "Objects", ()) or ())
        if len(vorbilder) != 1 or not stl_teil.aus_stl(vorbilder[0]):
            return None
        skala = getattr(objekt, "Scale", FreeCAD.Vector(1, 1, 1))
        if (skala - FreeCAD.Vector(1, 1, 1)).Length > 1e-12:
            return None
        return vorbilder[0]
    except Exception:  # noqa: BLE001 – gelöscht oder fremd
        return None


def _daten(koerper):
    """(Punkte, Index) des Netzes von `koerper` für Coin – das Dreieck der Fläche k an Stelle k –,
    oder None, wenn nicht jede Fläche genau ein Dreieck ist."""
    import numpy as np

    from . import stl_teil

    netz = getattr(koerper, stl_teil.EIGENSCHAFT_NETZ, None)
    zuordnung = getattr(koerper, stl_teil.EIGENSCHAFT_FLAECHEN, None)
    if netz is None or not zuordnung:
        return None
    schluessel = (koerper.Document.Name, koerper.Name, netz.CountFacets, netz.CountPoints)
    eintrag = _DATEN.get(schluessel)
    if eintrag is not None:
        return eintrag
    zu = np.asarray(zuordnung, dtype=np.int64)
    if len(zu) != netz.CountFacets or zu.min() < 0 or len(np.unique(zu)) != len(zu):
        return None
    if zu.max() != len(zu) - 1:
        return None
    p, d = netz.Topology
    punkte = [(q.x, q.y, q.z) for q in p]
    dreiecke = np.asarray(d, dtype=np.int32).reshape(-1, 3)
    reihe = np.empty(len(zu), dtype=np.int64)
    reihe[zu] = np.arange(len(zu))
    index = np.hstack([dreiecke[reihe], -np.ones((len(zu), 1), dtype=np.int32)]).ravel()
    eintrag = (punkte, index.tolist())
    _DATEN[schluessel] = eintrag
    while len(_DATEN) > _DATEN_HOECHSTENS:
        del _DATEN[next(iter(_DATEN))]
    return eintrag


def _knoten(ansicht):
    """Der Netzknoten in der Anzeige `ansicht` (ViewObject) – oder None. Ohne geladenes pivy gibt
    es keinen (das Addon baut ihn mit pivy): Dann nicht nach RootNode fragen – FreeCAD 27.1 wirft
    dort „No SWIG wrapped library loaded“, solange niemand pivy geladen hat, bei jeder Änderung
    eines Objekts (2026-10-16, Wochen-Build vom 14.10.)."""
    if "pivy.coin" not in sys.modules:
        return None
    try:
        wurzel = getattr(ansicht, "RootNode", None)
    except RuntimeError:
        return None
    if wurzel is None:
        return None
    for i in range(wurzel.getNumChildren()):
        kind = wurzel.getChild(i)
        if kind.getName().getString() == KNOTEN:
            return kind
    return None


def _farbe(ansicht):
    farbe = getattr(ansicht, "ShapeColor", None) or (0.8, 0.8, 0.8)
    return tuple(float(c) for c in farbe[:3])


def _bauen(ansicht, daten):
    from pivy import coin

    punkte, index = daten
    knoten = coin.SoSeparator()
    knoten.setName(KNOTEN)
    stoff = coin.SoMaterial()
    stoff.diffuseColor = _farbe(ansicht)
    stoff.transparency = float(getattr(ansicht, "Transparency", 0) or 0) / 100.0
    knoten.addChild(stoff)
    bindung = coin.SoMaterialBinding()
    bindung.value = coin.SoMaterialBinding.OVERALL
    knoten.addChild(bindung)
    hinweise = coin.SoShapeHints()
    hinweise.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
    hinweise.creaseAngle = 0.0
    knoten.addChild(hinweise)
    koordinaten = coin.SoCoordinate3()
    koordinaten.point.setValues(0, len(punkte), punkte)
    knoten.addChild(koordinaten)
    flaechen = coin.SoIndexedFaceSet()
    flaechen.coordIndex.setValues(0, len(index), index)
    knoten.addChild(flaechen)
    knoten.addChild(coin.SoSeparator())  # MARKEN
    return knoten


def zeigen(objekt, an=True):
    """Zeigt `objekt` (an) oder blendet es aus – ein Teil aus einem STL oder sein Klon als Netz,
    jedes andere wie bisher über ViewObject.Visibility. Gibt zurück, ob das Netz es zeigt."""
    ansicht = getattr(objekt, "ViewObject", None)
    if ansicht is None:
        return False
    koerper = vorbild(objekt) if mit_oberflaeche() else None
    daten = _daten(koerper) if koerper is not None else None
    if daten is None:
        ansicht.Visibility = bool(an)
        return False
    knoten = _knoten(ansicht)
    if an:
        if ansicht.Visibility:
            ansicht.Visibility = False  # sonst doppelt
        if knoten is None:
            ansicht.RootNode.addChild(_bauen(ansicht, daten))
        _merken(objekt, True)
        _marken_zeichnen(objekt)
        return True
    if knoten is not None:
        ansicht.RootNode.removeChild(knoten)
    ansicht.Visibility = False
    _merken(objekt, False)
    return False


def sichtbar(objekt):
    """Ist `objekt` zu sehen – als Netz oder in FreeCAD?"""
    ansicht = getattr(objekt, "ViewObject", None)
    if ansicht is None:
        return False
    return bool(ansicht.Visibility) or _knoten(ansicht) is not None


def als_netz(objekt):
    """Zeigt das Netz `objekt`?"""
    return _knoten(getattr(objekt, "ViewObject", None)) is not None


def _merken(objekt, an):
    if EIGENSCHAFT not in objekt.PropertiesList:
        if not an:
            return
        objekt.addProperty("App::PropertyBool", EIGENSCHAFT, "CAM-Addon", "")
        objekt.setEditorMode(EIGENSCHAFT, 2)  # versteckt
    # Nur eine Ausgabe: Sonst markierte jedes Umschalten das Objekt als geändert, und beim nächsten
    # Neuberechnen rechneten der Klon (am Geist 68.242 Flächen) und alles daran neu – beim
    # Umschalten der Aufspannungen (gui_schwenken.zeige_job) die Klone und Operationen aller.
    try:
        status = objekt.getPropertyStatus(EIGENSCHAFT)
        if "Output" not in status or "NoRecompute" not in status:
            objekt.setPropertyStatus(EIGENSCHAFT, ["Output", "NoRecompute"])
    except Exception:  # noqa: BLE001 – ältere FreeCAD-Versionen: wie bisher
        pass
    if bool(getattr(objekt, EIGENSCHAFT)) != bool(an):
        setattr(objekt, EIGENSCHAFT, bool(an))


def farben_setzen(objekt, farben):
    """Die Farben der Flächen ins Netz – `farben` je Fläche (r, g, b[, a]) in ihrer Reihenfolge,
    wie die Assistenten sie dem ViewObject geben; None: alle in der Farbe des Objekts. Die Anzeige
    eines ausgeblendeten Körpers gibt sie nicht vollständig zurück – darum hierher übergeben."""
    from pivy import coin

    ansicht = getattr(objekt, "ViewObject", None)
    knoten = _knoten(ansicht)
    if knoten is None:
        return
    stoff, bindung = knoten.getChild(STOFF), knoten.getChild(BINDUNG)
    stoff.transparency = float(getattr(ansicht, "Transparency", 0) or 0) / 100.0
    flaechen = knoten.getChild(DREIECKE).coordIndex.getNum() // 4
    farben = list(farben or [])
    if len(farben) == flaechen and len({tuple(f[:3]) for f in farben}) > 1:
        stoff.diffuseColor.setValues(0, len(farben), [tuple(f[:3]) for f in farben])
        bindung.value = coin.SoMaterialBinding.PER_FACE
        return
    stoff.diffuseColor.setNum(1)
    stoff.diffuseColor = tuple(farben[0][:3]) if farben else _farbe(ansicht)
    bindung.value = coin.SoMaterialBinding.OVERALL


def flaechen_faerben(objekt, farben):
    """Färbt Flächen im Netz: `farben` Nummer (0 ist „Face1“) → „#rrggbb“, die anderen in der Farbe
    des Objekts – wie die Assistenten die Flächen des Teils färben (_farben_zeigen); leer: alle wieder
    in seiner Farbe. Der ausgeblendete Klon hat in 26.3 kein DiffuseColor, das sie tragen könnte."""
    knoten = _knoten(getattr(objekt, "ViewObject", None))
    if knoten is None:
        return
    if not farben:
        farben_setzen(objekt, None)
        return
    anzahl = knoten.getChild(DREIECKE).coordIndex.getNum() // 4
    liste = [_farbe(objekt.ViewObject)] * anzahl
    for nummer, farbe in farben.items():
        if 0 <= nummer < anzahl:
            liste[nummer] = tuple(int(farbe[i : i + 2], 16) / 255 for i in (1, 3, 5))
    farben_setzen(objekt, liste)


def farben_nachziehen(objekt):
    """farben_setzen() mit den Farben, die das ViewObject trägt (nach einer Änderung daran)."""
    ansicht = getattr(objekt, "ViewObject", None)
    farben_setzen(objekt, list(getattr(ansicht, "DiffuseColor", []) or []))


def _marken_zeichnen(objekt):
    """Die gewählten Flächen grün, die vorgewählte gelb – über dem Netz."""
    from pivy import coin

    knoten = _knoten(getattr(objekt, "ViewObject", None))
    koerper = vorbild(objekt)
    daten = _daten(koerper) if koerper is not None else None
    if knoten is None or daten is None:
        return
    marke = knoten.getChild(MARKEN)
    marke.removeAllChildren()
    index = daten[1]
    anzahl = len(index) // 4
    schluessel = (objekt.Document.Name, objekt.Name)
    for nummern, farbe in (
        (_gewaehlt.get(schluessel, set()), AUSWAHL_FARBE),
        ({_vorgewaehlt[schluessel]} if schluessel in _vorgewaehlt else set(), VORAUSWAHL_FARBE),
    ):
        nummern = sorted(n for n in nummern if 0 <= n < anzahl)
        if not nummern:
            continue
        teil = coin.SoSeparator()
        versatz = coin.SoPolygonOffset()
        versatz.factor = -1.0
        versatz.units = -1.0
        teil.addChild(versatz)
        stoff = coin.SoMaterial()
        stoff.diffuseColor = farbe
        stoff.emissiveColor = tuple(0.4 * c for c in farbe)
        teil.addChild(stoff)
        bindung = coin.SoMaterialBinding()
        bindung.value = coin.SoMaterialBinding.OVERALL
        teil.addChild(bindung)
        flaechen = coin.SoIndexedFaceSet()
        auswahl = []
        for n in nummern:
            auswahl += [index[4 * n], index[4 * n + 1], index[4 * n + 2], -1]
        flaechen.coordIndex.setValues(0, len(auswahl), auswahl)
        teil.addChild(flaechen)
        marke.addChild(teil)


def _flaeche(unterelement):
    if unterelement and unterelement.startswith("Face") and unterelement[4:].isdigit():
        return int(unterelement[4:]) - 1
    return None


def _objekt(dokument, name):
    doc = FreeCAD.listDocuments().get(dokument)
    return doc.getObject(name) if doc is not None and name else None


class _Auswahl:
    """Hebt im Netz hervor, was FreeCAD auswählt – FreeCAD selbst hebt es im ausgeblendeten
    Körper hervor, wo man es nicht sieht."""

    def _neu(self, dokument, name):
        objekt = _objekt(dokument, name)
        if objekt is not None and als_netz(objekt):
            _marken_zeichnen(objekt)

    def addSelection(self, dokument, name, unterelement, _punkt=None):  # noqa: N802
        nummer = _flaeche(unterelement)
        if nummer is None:
            return
        _gewaehlt.setdefault((dokument, name), set()).add(nummer)
        self._neu(dokument, name)

    def removeSelection(self, dokument, name, unterelement):  # noqa: N802
        nummer = _flaeche(unterelement)
        if nummer is not None:
            _gewaehlt.get((dokument, name), set()).discard(nummer)
            self._neu(dokument, name)

    def setSelection(self, dokument):  # noqa: N802
        self.clearSelection(dokument)
        import FreeCADGui

        for auswahl in FreeCADGui.Selection.getSelectionEx(dokument, 0):
            for unterelement in auswahl.SubElementNames:
                self.addSelection(dokument, auswahl.ObjectName, unterelement)

    def clearSelection(self, dokument):  # noqa: N802
        for schluessel in [s for s in _gewaehlt if not dokument or s[0] == dokument]:
            del _gewaehlt[schluessel]
            self._neu(*schluessel)

    def setPreselection(self, dokument, name, unterelement):  # noqa: N802
        nummer = _flaeche(unterelement)
        alt = [s for s in _vorgewaehlt if s != (dokument, name)]
        for schluessel in alt:
            del _vorgewaehlt[schluessel]
            self._neu(*schluessel)
        if nummer is None:
            if _vorgewaehlt.pop((dokument, name), None) is not None:
                self._neu(dokument, name)
            return
        if _vorgewaehlt.get((dokument, name)) != nummer:
            _vorgewaehlt[(dokument, name)] = nummer
            self._neu(dokument, name)

    def removePreselection(self, dokument, name, _unterelement):  # noqa: N802
        if _vorgewaehlt.pop((dokument, name), None) is not None:
            self._neu(dokument, name)


class _Dokumente:
    """Nach dem Öffnen und nach Rückgängig/Wiederholen: das Netz wieder an jedes Objekt, das es
    zeigte (EIGENSCHAFT) – die Anzeige wurde neu gebaut, ohne den Knoten. Blendet man ein Teil mit
    Netz in FreeCAD ein (Leertaste), zeigt FreeCAD es selbst – das Netz geht aus, sonst wäre es
    doppelt da.

    Bewusst ein Beobachter der Dokumente, nicht der Anzeigen (FreeCADGui.addDocumentObserver):
    Einem solchen reicht FreeCAD jede Anzeige schon, während sie entsteht – die einer Assembly
    bekam dabei ihr allgemeines Python-Gegenstück ohne „isInEditMode“, und FreeCADs Assembly
    ging nicht mehr (Manuel, 2026-10-16, FreeCAD 27.1: „AttributeError: … isInEditMode“, „ich
    kann leider auch keine bauteile einlegen“). Farben, die man von Hand an der Anzeige ändert,
    kommen deshalb erst beim nächsten Zeigen ins Netz; die Assistenten färben es selbst
    (flaechen_faerben)."""

    def slotChangedObject(self, objekt, eigenschaft):  # noqa: N802
        if eigenschaft != "Visibility" or not getattr(objekt, "Visibility", False):
            return
        if EIGENSCHAFT not in objekt.PropertiesList:
            return
        ansicht = getattr(objekt, "ViewObject", None)
        knoten = _knoten(ansicht)
        if knoten is None:
            return
        ansicht.RootNode.removeChild(knoten)
        with contextlib.suppress(Exception):
            _merken(objekt, False)

    def slotCreatedDocument(self, dokument):  # noqa: N802
        _spaeter(dokument.Name)

    def slotUndoDocument(self, dokument):  # noqa: N802
        _spaeter(dokument.Name)

    def slotRedoDocument(self, dokument):  # noqa: N802
        _spaeter(dokument.Name)

    def slotAbortTransaction(self, dokument):  # noqa: N802
        _spaeter(dokument.Name)  # „Abbrechen“ im Assistenten: was es ausgeblendet hatte, wieder da


def wieder_anzeigen(dokument):
    """Jedes Objekt mit EIGENSCHAFT, das gerade kein Netz zeigt, zeigt es wieder. Gibt die Zahl
    zurück. Das Dokument gilt danach als so verändert wie vorher."""
    import FreeCADGui

    offen = [
        o
        for o in dokument.Objects
        if EIGENSCHAFT in o.PropertiesList and getattr(o, EIGENSCHAFT) and not als_netz(o)
    ]
    if not offen:
        return 0
    gui = FreeCADGui.getDocument(dokument.Name)
    geaendert = getattr(gui, "Modified", None)
    gezeigt = sum(1 for o in offen if zeigen(o, True))
    if gui is not None and geaendert is not None:
        with contextlib.suppress(Exception):
            gui.Modified = geaendert
    return gezeigt


def _spaeter(name):
    from PySide import QtCore

    def nachsehen():
        dokument = FreeCAD.listDocuments().get(name)
        if dokument is None:
            return
        if getattr(dokument, "Restoring", False):
            QtCore.QTimer.singleShot(NACHSEHEN_MS, nachsehen)
            return
        try:
            wieder_anzeigen(dokument)
        except Exception as fehler:  # noqa: BLE001 – ein Fehler hier darf nichts stören
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Netz anzeigen: {fehler}\n")

    QtCore.QTimer.singleShot(0, nachsehen)


def beobachten():
    """Meldet die Beobachter einmal an (gui_start.starten)."""
    if _BEOBACHTER:
        return
    import FreeCADGui

    auswahl, dokumente = _Auswahl(), _Dokumente()
    _BEOBACHTER.extend([auswahl, dokumente])
    FreeCADGui.Selection.addObserver(auswahl)
    FreeCAD.addDocumentObserver(dokumente)
