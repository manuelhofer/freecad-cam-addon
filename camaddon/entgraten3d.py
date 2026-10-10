# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Entgraten 3D“ (W-015 S5; entgrat3d_bahn) – Fasen an Kanten im Raum, mit 5
Achsen (Fasenfräser oder ein Fräser mit ebener Stirn, angestellt) oder mit 3 Achsen (Fasenfräser
senkrecht). Manuel, 2026-10-04: „es muss schon so sein, dass man nicht das Werkstück beschädigt“;
„bau das nicht nur auf den 45-Grad-Fräser … mit einem 45-Grad-Fräser kann man schon sehr viel auch
auf einer Dreiachs-Maschine machen“.

Wie die Flanke eine eigene Operation mit Werkzeug-Controller, Kühlmittel, Tiefen und Höhen; ihre
Bahn sind die Spitzen im Job, je Satz die Werkzeugachse in `Werkzeugachsen`. Mit 5 Achsen rechnen
„Auf der Maschine prüfen“, die Kollision und „Programm schreiben“ daraus die Rundachsen
(befehle); mit 3 Achsen steht die Achse senkrecht und die Bahn ist eine gewöhnliche.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (Einsatz „Fasen“) und für die Kollision (sie darf
ins Teil: die Fase steht nicht im Modell). Kein Qt hier.

Läuft ohne Oberfläche.
"""

import math

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import aufloesung as au
from . import entgrat3d_bahn as e3
from . import fraeserform as ff
from . import namen
from . import planfraesen as pf
from . import simultan as si
from . import spindel as sp
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from . import werkzeuge as wz
from .sprache import tr

GRUPPE = "Fräsen"
GRUPPE_5ACHS = "5-Achs"
KEINE = (0.0, 0.0, 0.0)  # in `Werkzeugachsen`: ein Satz ohne Bewegung
BREITE = 0.5  # mm – die Fase, vorgeschlagen
FLACH = (wz.SCHAFTFRAESER, wz.TORUSFRAESER, wz.PLANFRAESER, wz.NUTENFRAESER)


class Entgraten3D(PathOp.ObjectOp):
    """Proxy der Operation „Entgraten 3D“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Fasenbreite = BREITE
        obj.FuenfAchsen = True
        obj.Sicherheitsabstand = e3.SICHERHEIT
        obj.Werkzeugachsen = []
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        au.eigenschaft(obj, GRUPPE)  # die Auflösung: der Schritt auf der Kante (mm), T-009
        neu = []
        for typ, name, gruppe, text in (
            ("App::PropertyStringList", "Flaechen", GRUPPE, tr("e3.eigenschaft.flaechen")),
            ("App::PropertyLength", "Fasenbreite", GRUPPE, tr("e3.eigenschaft.breite")),
            ("App::PropertyBool", "FuenfAchsen", GRUPPE, tr("e3.eigenschaft.fuenf")),
            ("App::PropertyLength", "Sicherheitsabstand", GRUPPE, tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Kanten", GRUPPE, tr("e3.eigenschaft.kanten")),
            ("App::PropertyLength", "Ausgelassen", GRUPPE, tr("e3.eigenschaft.ausgelassen")),
            ("App::PropertyLength", "SchenkelMax", GRUPPE, tr("e3.eigenschaft.schenkel")),
            (
                "App::PropertyVectorList",
                "Werkzeugachsen",
                GRUPPE_5ACHS,
                tr("an.eigenschaft.achsen"),
            ),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, gruppe, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Kanten", "Ausgelassen", "SchenkelMax"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        obj.setEditorMode("Werkzeugachsen", 2)  # gerechnet, je Satz – nicht zum Ansehen

    def opExecute(self, obj):
        self._vorne = len(self.commandlist)  # was FreeCAD davor schreibt (der Name)
        self._achsen = []
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            bahn = rechne(obj, self.job, self.model, self.horizFeed * 60.0)
        except ValueError as fehler:
            obj.Kanten = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            self._achsen.append(KEINE)
            return
        obj.Kanten = bahn.kanten
        obj.Ausgelassen = round(bahn.ausgelassen, 3)
        obj.SchenkelMax = round(bahn.schenkel[1], 4)
        if bahn.ausgelassen > 0.05:
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {ausgelassen_text(bahn)}\n")
        vorschub = self.horizFeed
        eintauchen = vo.eintauchvorschub(self) / 60.0 or vorschub
        for stelle in bahn.punkte:
            werte = dict(zip("XYZ", (float(x) for x in stelle.spitze), strict=True))
            if stelle.eilgang:
                self.commandlist.append(Path.Command("G0", werte))
            else:
                werte["F"] = float(eintauchen if stelle.eintauchen else vorschub)
                self.commandlist.append(Path.Command("G1", werte))
            self._achsen.append(tuple(stelle.achse))

    def execute(self, obj):
        """Wie jede Operation – danach je Satz der fertigen Bahn die Werkzeugachse (wie die
        Flanke: vorn und hinten, was FreeCAD dazuschreibt, ohne eigene)."""
        self._vorne, self._achsen = 0, []
        ergebnis = super().execute(obj)
        alle = len(obj.Path.Commands) if getattr(obj, "Path", None) else 0
        achsen = [KEINE] * self._vorne + list(self._achsen)
        achsen = (achsen + [KEINE] * alle)[:alle]
        obj.Werkzeugachsen = [FreeCAD.Vector(*a) for a in achsen]
        return ergebnis


def ausgelassen_text(bahn):
    """„… mm Kante ohne Fase: 12 mm zu eng, 4 mm zu steil“."""
    texte = {
        e3.ENG: tr("e3.grund.eng"),
        e3.STEIL: tr("e3.grund.steil"),
        e3.KEINE_STELLUNG: tr("e3.grund.keine"),
        e3.ANFAHRT: tr("e3.grund.anfahrt"),
        e3.TISCH: tr("e3.grund.tisch"),
        e3.SCHAFT_NAH: tr("e3.grund.schaft"),
        e3.VON_OBEN: tr("e3.grund.von_oben"),
        e3.HALTER: (
            tr("e3.grund.halter_bis", mm=f"{bahn.auskragung:.0f}")
            if bahn.auskragung > 0
            else tr("e3.grund.halter")
        ),
    }
    teile = [
        f"{max(mm, 1.0):.0f} mm {texte.get(grund, grund)}"  # eine Stelle (0,5 mm) nicht als „0 mm“
        for grund, mm in sorted(bahn.gruende.items(), key=lambda x: -x[1])
        if mm >= 0.5
    ]
    return tr("e3.ausgelassen", mm=f"{bahn.ausgelassen:.0f}", gruende=", ".join(teile))


def fraeser_von(werkzeug):
    """Fraeser3D aus einem Werkzeug (werkzeuge.Werkzeug): ein Fasenfräser als Kegel, ein Fräser
    mit ebener Stirn (Schaft, Torus – sein ebener Teil –, Plan, Nut) als Stirn. ValueError mit
    einem Satz bei einem anderen."""
    from . import werkzeugform as wf

    if werkzeug is None:
        raise ValueError(tr("e3.fehler.fraeser"))
    schneide = float(getattr(werkzeug, "schneidenlaenge", 0.0) or 0.0)
    if werkzeug.art == wz.FASENFRAESER:
        spitze, _hoehe, winkel = wf.kegel(werkzeug)
        form = ff.von_werkzeug(werkzeug)
        if form is None or not 0 < winkel < 180:
            raise ValueError(tr("e3.fehler.fraeser"))
        return e3.Fraeser3D(float(form.radius), math.radians(winkel / 2.0), spitze / 2.0, schneide)
    if werkzeug.art in FLACH:
        radius = float(werkzeug.durchmesser) / 2.0
        eben = radius - float(getattr(werkzeug, "eckradius", 0.0) or 0.0)
        if radius <= 0 or eben <= 0.1 * radius:
            raise ValueError(tr("e3.fehler.fraeser"))
        return e3.Fraeser3D(radius, 0.0, eben, schneide or 2.0 * radius)
    raise ValueError(tr("e3.fehler.fraeser"))


def aufbau_von(fraeser, einspannung):
    """entgrat3d_bahn.Aufbau aus (Halter, Schaft-Radius, Auskragung) wie wegkippen.einspannung
    – None ohne. ValueError mit einem Satz bei einem gewinkelten Halter."""
    if einspannung is None:
        return None
    from . import halter as hl

    halter, schaft, auskragung = einspannung
    if halter.gewinkelt:
        raise ValueError(tr("e3.fehler.gewinkelt"))
    # Reicht die Länge nicht einmal über die Schneide hinaus, ist sie die Gesamtlänge des
    # CAM-Werkzeugs (es steht nicht in der Werkzeugverwaltung), nicht die ab Spindelnase – dann
    # wie im vorgeschlagenen Halter.
    auskragung = max(float(auskragung), fraeser.schneidhoehe + hl.VORSCHLAG_ZUGABE)
    return e3.aufbau(halter, schaft, auskragung, fraeser)


def rechne(obj, job, modell, vorschub=0.0):
    """Die Bahn (entgrat3d_bahn.Bahn3D) für die Operation `obj` im Job – mit Schaft und Halter
    wie „Auf der Maschine prüfen“ (aus der Werkzeugverwaltung, ohne gewählten der vorgeschlagene).
    ValueError mit einem Satz, wenn es nicht geht."""
    from . import wegkippen as wk
    from .werkzeuge_aus_cam import vom_controller

    fraeser = fraeser_von(vom_controller(obj.ToolController))
    try:
        einspannung = wk.einspannung(obj.ToolController)
    except ValueError:
        raise ValueError(tr("e3.fehler.gewinkelt")) from None
    return bahn_fuer(
        job,
        modell,
        fraeser,
        float(obj.Fasenbreite),
        vo.flaechen(obj),
        fuenf=bool(obj.FuenfAchsen),
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        gleichlauf=sp.fuer_m3(True, obj.ToolController),
        vorschub=vorschub,
        aufbau=aufbau_von(fraeser, einspannung),
        schritt=au.wert(obj, e3.SCHRITT),
    )


def bahn_fuer(
    job,
    modell,
    fraeser,
    breite,
    flaechen,
    fuenf=True,
    sicher=None,
    sicherheit=e3.SICHERHEIT,
    gleichlauf=True,
    vorschub=0.0,
    aufbau=None,
    schritt=e3.SCHRITT,
):
    """Die Bahn „Entgraten 3D“ an den Flächen und Kanten `flaechen` des Modells; `aufbau`
    (entgrat3d_bahn.Aufbau): Schaft und Halter, None ohne; `schritt`: so dicht liegen die
    Stellen auf der Kante (mm) – das Teil wird um die Kanten halb so fein abgetastet. ValueError mit einem Satz, wenn es
    nicht geht."""
    form_teil = vs._teil(modell)
    if sicher is None:
        sicher = pf.rohteil_von_oben(job)[4] + sicherheit + 3.0
    werte = e3.Werte3D(
        fraeser=fraeser,
        breite=breite,
        art=e3.FUENF if fuenf else e3.DREI,
        sicher=sicher,
        sicherheit=sicherheit,
        gleichlauf=gleichlauf,
        vorschub=vorschub,
        aufbau=aufbau,
    )
    return e3.planen(
        form_teil, list(flaechen), werte, schritt, schritt * e3.PUNKTABSTAND / e3.SCHRITT
    )


VORSCHAU_SCHRITT = 1.0  # mm – im Assistenten gröber
VORSCHAU_PUNKTABSTAND = 0.35  # mm


def vorschau(job, werkzeug, breite, flaechen, fuenf=True, vorschub=0.0, bibliothek=None):
    """Die Bahn grob – für Kanten, Zeit und ob es geht, im Assistenten; Schaft und Halter aus der
    Werkzeugverwaltung (ohne `bibliothek` gelesen). ValueError wie bahn_fuer()."""
    from . import wegkippen as wk

    if bibliothek is None:
        try:
            bibliothek = wz.Bibliothek.laden()
        except (wz.BeschaedigteDatei, OSError):
            bibliothek = None
    form_teil = vs._teil(job.Model.Group)
    fraeser = fraeser_von(werkzeug)
    einspannung = wk.einspannung_werkzeug(werkzeug, bibliothek)
    if einspannung is None:
        raise ValueError(tr("e3.fehler.gewinkelt"))
    werte = e3.Werte3D(
        fraeser=fraeser,
        breite=breite,
        art=e3.FUENF if fuenf else e3.DREI,
        sicher=pf.rohteil_von_oben(job)[4] + e3.SICHERHEIT + 3.0,
        vorschub=vorschub,
        aufbau=aufbau_von(fraeser, einspannung),
    )
    return e3.planen(form_teil, list(flaechen), werte, VORSCHAU_SCHRITT, VORSCHAU_PUNKTABSTAND)


def passt(form, name):
    """Hat die Fläche `name` konvexe, scharfe Kanten zum Fasen? Je Form und Fläche gemerkt: Der
    Assistent „Bearbeitung“ fragt es je gewählter Fläche bei jeder Vorschau – am 3-Achs-Testteil
    19-mal je Lauf, 1,8 s im Fenster (P-2026-10-11-15)."""
    try:
        flaeche = form.getElement(name)
        schluessel = (
            form.hashCode(),
            round(form.Volume, 6),
            round(form.Area, 6),
            len(form.Faces),
            name,
            flaeche.hashCode(),
            round(flaeche.Area, 6),
        )
    except Exception:
        schluessel = None
    if schluessel is not None and schluessel in _PASST:
        return _PASST[schluessel]
    try:
        ergebnis = e3.hat_kanten(form, [name])
    except Exception:
        ergebnis = False
    if schluessel is not None:
        _PASST[schluessel] = ergebnis
        while len(_PASST) > PASST_MERK:
            del _PASST[next(iter(_PASST))]
    return ergebnis


_PASST = {}  # (Form, Fläche) → passt? (passt)
PASST_MERK = 512


def lege_an(job, tc, breite=BREITE, fuenf=True, name=None, flaechen=()):
    """Legt „Entgraten 3D“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Gibt die
    Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Entgraten3D")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Entgraten3D(obj, "Entgraten3D", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Fasenbreite = breite
    obj.FuenfAchsen = bool(fuenf)
    obj.Flaechen = list(flaechen)
    obj.Label = namen.eindeutig(obj.Document, name or _name(tc), obj)
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _name(tc):
    """„Entgraten 3D T7“."""
    return tr("e3.name", werkzeug=f"T{tc.ToolNumber}")


def aendere(obj, tc, breite=BREITE, fuenf=None, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; ohne bleiben sie. Der Name folgt dem Werkzeug, solange es der vorgeschlagene
    ist."""
    if namen.nach_vorlage(obj.Label, tr("e3.name", werkzeug="\0")):
        obj.Label = namen.eindeutig(obj.Document, _name(tc), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Fasenbreite = breite
    if fuenf is not None:
        obj.FuenfAchsen = bool(fuenf)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)


def ist_entgraten3d(op):
    """Ist `op` eine Operation dieses Moduls?"""
    return isinstance(getattr(op, "Proxy", None), Entgraten3D)


def hat_achsen(op):
    """Ein „Entgraten 3D“ mit 5 Achsen und gekippten Werkzeugachsen (gerechnet)?"""
    if not ist_entgraten3d(op) or not bool(getattr(op, "FuenfAchsen", True)):
        return False
    achsen = getattr(op, "Werkzeugachsen", None) or []
    return any(abs(a.x) > 1e-9 or abs(a.y) > 1e-9 for a in achsen)


def eindringtiefe(op):
    """So tief (mm) geht die Fase unter die Kante – fürs Prüffenster."""
    return float(getattr(op, "SchenkelMax", 0.0) or getattr(op, "Fasenbreite", BREITE))


def befehle(op, maschine, rohteil=None, tcpm=False, bei_null=False):
    """Die Sätze der Operation, wie `maschine` (schwenken.Maschine) sie fährt: die Rundachsen je
    Punkt, die Spitze auf der Geraden (simultan.befehle_auf_maschine; mit `tcpm`
    simultan.befehle_mit_tcpm). ValueError mit einem Satz, wenn es nicht geht."""
    from . import angestellt as an
    from . import flanke as fl

    if rohteil is None:
        rohteil = an.rohteil_von(op)
    alle = list(op.Path.Commands)
    achsen_je_satz = [tuple(v) for v in op.Werkzeugachsen]
    if len(achsen_je_satz) != len(alle):
        raise ValueError(tr("an.fehler.veraltet", operation=op.Label))
    punkte = fl.punkte(alle, achsen_je_satz)
    if tcpm:
        return si.befehle_mit_tcpm(maschine, punkte, rohteil, 0.0, bei_null=bei_null)
    return si.befehle_auf_maschine(
        maschine, punkte, rohteil, 0.0, materialdaten=getattr(op, "_pruefmaterial", None)
    )
