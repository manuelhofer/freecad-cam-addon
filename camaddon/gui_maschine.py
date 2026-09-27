# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dialog „Maschine bearbeiten“ (Spezifikation W-001, Abschnitt 11).

Ein Aufgabenfenster in FreeCADs Aufgabenbereich, damit die 3D-Ansicht
sichtbar bleibt. Von oben nach unten:

    Name          Name der Maschine
    Achsen        die Gelenke der Assembly, darunter ihre Betriebsarten
    (Details)     Felder der gewählten Zeile – gui_details
    Transformationen  Umrechnungen der Steuerung, etwa eine schräge Achse
    Aufnahmen     Werkzeug- und Werkstückaufnahmen, Revolverplätze gesammelt
    Glieder       was sich gemeinsam bewegt
    Hinweise      was fehlt oder nicht passt; ein Klick springt zur Zeile
    An CAM übergeben

Der ganze Dialog ist eine Transaktion: OK übernimmt alles als einen Schritt
Rückgängig, Abbrechen verwirft alles. Jede Eingabe geht trotzdem sofort ins
Dokument, damit Hinweise und 3D-Ansicht immer den aktuellen Stand zeigen.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import beispielmaschine, export, gui_neue_maschine, gui_zeigen, schraege_achse, symbol
from . import kette as kette_modul
from . import maschine as m
from .gui_bericht import BerichtFenster
from .gui_details import DetailKasten
from .gui_hilfe import kopfzeile
from .gui_teile import ruhiges_mausrad
from .gui_verteilhilfe import VerteilDialog
from .gui_zahlen import winkel_zeigen
from .kette import HINWEIS, LINEAR
from .sprache import tr

# Jede Zeile in „Achsen“, „Transformationen“, „Aufnahmen“ und „Glieder“ trägt
# in ihren Daten (Art der Zeile, Objekt).
ROLLE = QtCore.Qt.UserRole
ZEILE_GELENK = "gelenk"
ZEILE_BETRIEBSART = "betriebsart"
ZEILE_AUFNAHME = "aufnahme"
ZEILE_REVOLVER = "revolver"  # Kopfzeile, unter der die Plätze eines Revolvers stehen
ZEILE_GLIED = "glied"
ZEILE_TRANSFORMATION = "transformation"

# Gezeigt wird erst, wenn die Maus so lange auf einer Zeile verweilt – nicht
# bei jedem Überstreichen.
ZEIGEN_NACH_MS = 250
MINDESTHOEHE_ACHSEN = 160  # Pixel
MINDESTHOEHE_AUFNAHMEN = 110
# Meist gibt es keine oder eine Transformation – die Liste bleibt klein.
HOEHE_TRANSFORMATIONEN = (44, 90)  # Pixel: kleinste und größte Höhe


class BefehlMaschineBearbeiten:
    """Befehl in der Werkzeugleiste: öffnet den Dialog für die gewählte Assembly."""

    def GetResources(self):
        return {
            "Pixmap": symbol("maschine.svg"),
            "MenuText": tr("befehl.maschine.titel"),
            "ToolTip": tr("befehl.maschine.tooltip"),
        }

    def IsActive(self):
        # Immer bedienbar, solange kein anderes Aufgabenfenster offen ist: Fehlt
        # die Assembly, erklärt der Befehl, was zu tun ist – ein ausgegrauter
        # Knopf erklärt nichts.
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        assembly = gewaehlte_assembly(doc) if doc else None
        if assembly is None:
            gewaehlt = beispiel_waehlen(tr("dialog.titel"))
            if gewaehlt is None:
                return
            assembly, _maschine = beispielmaschine.lade(*gewaehlt)
            doc = assembly.Document
        doc.openTransaction(tr("dialog.titel"))
        maschine = m.lege_maschine_an(assembly)
        # Die Baugruppe ist gefunden; gewählt leuchtete sonst die ganze Maschine, solange
        # das Fenster offen ist – und das Fenster hebt selbst über die Auswahl hervor.
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Control.showDialog(MaschinenPanel(assembly, maschine))


def beispiel_waehlen(titel):
    """Meldet, dass es keine Baugruppe gibt – mit dem Knopf „Neue Maschine …“.

    Wer das Addon ausprobiert, soll nicht erst eine Maschine bauen müssen: Der
    Knopf öffnet die Auswahl von „Neue Maschine …“. Gibt (Bauart, Maße oder
    None) zurück – wie gui_neue_maschine.waehle –, oder None.
    """
    meldung = QtGui.QMessageBox(
        QtGui.QMessageBox.Information,
        titel,
        tr("dialog.keine_baugruppe"),
        QtGui.QMessageBox.Ok,
        FreeCADGui.getMainWindow(),
    )
    beispiel = meldung.addButton(tr("dialog.beispielmaschine"), QtGui.QMessageBox.ActionRole)
    beispiel.setToolTip(tr("dialog.beispielmaschine.tooltip"))
    meldung.exec()
    if meldung.clickedButton() is not beispiel:
        return None
    return gui_neue_maschine.waehle(tr("neu.titel"))


def gewaehlte_assembly(doc):
    """Die Assembly, um die es geht, oder None.

    Der Reihe nach: die gewählte (oder die, in der etwas Gewähltes liegt), die
    gerade bearbeitete, die einzige im Dokument. Gibt es mehrere, wird gefragt.
    """
    for objekt in FreeCADGui.Selection.getSelection(doc.Name):
        for kandidat in [objekt, *objekt.InListRecursive]:
            if _ist_assembly(kandidat):
                return kandidat
    aktiv = _aktive_assembly()
    if aktiv is not None:
        return aktiv
    alle = [o for o in doc.Objects if _ist_assembly(o)]
    if len(alle) > 1:
        return _frage_nach_assembly(alle)
    return alle[0] if alle else None


def _ist_assembly(objekt):
    return objekt.TypeId == "Assembly::AssemblyObject"


def _aktive_assembly():
    """Die Assembly, die gerade bearbeitet wird (Doppelklick im Baum), oder None."""
    try:
        import UtilsAssembly
    except ImportError:  # ohne Assembly-Arbeitsbereich
        return None
    return UtilsAssembly.activeAssembly()


def _frage_nach_assembly(alle):
    namen = [a.Label for a in alle]
    name, gewaehlt = QtGui.QInputDialog.getItem(
        FreeCADGui.getMainWindow(),
        tr("dialog.titel"),
        tr("dialog.welche_baugruppe"),
        namen,
        0,  # vorgewählt: die erste
        False,  # nur aus der Liste, kein freier Text
    )
    return alle[namen.index(name)] if gewaehlt else None


class MaschinenPanel:
    """Das Aufgabenfenster. FreeCAD ruft `getStandardButtons`, `accept` und `reject` auf."""

    offen = None  # das gerade offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, assembly, maschine):
        MaschinenPanel.offen = self
        self.assembly = assembly
        self.maschine = maschine
        self.doc = assembly.Document
        self.kette = kette_modul.lies_kette(assembly)
        self.meldungen = []  # die gerade gezeigten Hinweise
        self.geschlossen = False  # nach OK oder Abbrechen: keine späten Aufrufe mehr
        self.wackeln = None  # die Bewegung beim Zeigen einer Achse

        self._zeige_ziel = None  # die Zeile unter der Maus
        self._zeige_uhr = QtCore.QTimer()
        self._zeige_uhr.setSingleShot(True)
        self._zeige_uhr.setInterval(ZEIGEN_NACH_MS)
        self._zeige_uhr.timeout.connect(lambda: self.zeige(self._zeige_ziel))

        self.form = self._baue()
        self.neu_aufbauen()
        # Gleich ein Gelenk wählen, damit „+ Betriebsart“ sofort bedienbar ist.
        if self.achsen.topLevelItemCount():
            self.achsen.setCurrentItem(self.achsen.topLevelItem(0))

    # --- Schnittstelle zu FreeCAD ---------------------------------------------

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def accept(self):
        self._vor_dem_schliessen()
        self.doc.commitTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def reject(self):
        self._vor_dem_schliessen()
        self.doc.abortTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def _vor_dem_schliessen(self):
        """Bewegung anhalten und alles zurückstellen, Markierung in 3D weg."""
        self.geschlossen = True
        self._zeige_uhr.stop()
        if self.wackeln:
            self.wackeln.stopp()
        FreeCADGui.Selection.clearSelection()

    # --- Aufbau ---------------------------------------------------------------

    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("dialog.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("maschine.svg")))
        self._enter_filter = _EnterBleibtImDialog(form)  # Enter schließt den Dialog nicht
        form.installEventFilter(self._enter_filter)
        self._aufbau = QtGui.QVBoxLayout(form)
        self._baue_namenszeile()
        self._baue_achsen()
        # Der Kasten wandert jeweils unter die Liste, in der gerade etwas
        # gewählt ist (siehe _details_zeigen).
        self.details = DetailKasten(self._setze)
        self._aufbau.addWidget(self.details)
        self._baue_transformationen()
        self._baue_aufnahmen()
        self._baue_glieder()
        self._baue_hinweise()
        tooltip = tr("dialog.uebergeben.tooltip_fehlt")
        if export.verfuegbar():
            tooltip = tr("dialog.uebergeben.tooltip")
        self.knopf_uebergeben = _knopf(tr("dialog.uebergeben"), self.uebergeben, tooltip)
        self._aufbau.addWidget(self.knopf_uebergeben)
        # Die Felder des Kastens kommen später dazu – ruhig sind sie in gui_details.
        return ruhiges_mausrad(form)

    def _baue_namenszeile(self):
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(QtGui.QLabel(tr("dialog.name")))
        self.name = QtGui.QLineEdit(self.maschine.Label)
        self.name.setToolTip(tr("dialog.name.tooltip"))
        self.name.editingFinished.connect(self._name_uebernehmen)
        zeile.addWidget(self.name)
        self._aufbau.addLayout(zeile)

    def _baue_achsen(self):
        self._aufbau.addWidget(kopfzeile(tr("dialog.achsen"), "achsen"))
        self.achsen = self._baum(tr("dialog.achsen.tooltip"), MINDESTHOEHE_ACHSEN)
        self.achsen.currentItemChanged.connect(self._achse_gewaehlt)
        self._aufbau.addWidget(self.achsen)

        self.knopf_betriebsart = QtGui.QPushButton(tr("dialog.betriebsart_neu"))
        self.knopf_betriebsart.setToolTip(tr("dialog.betriebsart_neu.tooltip"))
        # Der Knopf klappt ein Menü mit den Betriebsarten auf, die zum
        # gewählten Gelenk passen; gefüllt wird es erst beim Aufklappen.
        menue = QtGui.QMenu(self.knopf_betriebsart)
        menue.aboutToShow.connect(lambda: self._fuelle_betriebsart_menue(menue))
        self.knopf_betriebsart.setMenu(menue)
        self.knopf_ba_weg = _knopf(tr("dialog.entfernen"), self.betriebsart_entfernen)
        self.knopf_vorschlagen = _knopf(
            tr("dialog.vorschlagen"),
            self.betriebsarten_vorschlagen,
            tr("dialog.vorschlagen.tooltip"),
        )
        self.achsen_knoepfe = _knopfreihe(
            [self.knopf_betriebsart, self.knopf_ba_weg, self.knopf_vorschlagen]
        )
        self._aufbau.addWidget(self.achsen_knoepfe)

    def _baue_transformationen(self):
        self._aufbau.addWidget(kopfzeile(tr("dialog.transformationen"), "transformationen"))
        self.transformationen = self._baum(
            tr("dialog.transformationen.tooltip"), HOEHE_TRANSFORMATIONEN[0]
        )
        self.transformationen.setMaximumHeight(HOEHE_TRANSFORMATIONEN[1])
        self.transformationen.currentItemChanged.connect(self._transformation_gewaehlt)
        self._aufbau.addWidget(self.transformationen)

        self.knopf_schraeg = _knopf(tr("dialog.schraege_achse_neu"), self.schraege_achse_anlegen)
        self.knopf_trafo_weg = _knopf(tr("dialog.entfernen"), self.transformation_entfernen)
        self.trafo_knoepfe = _knopfreihe([self.knopf_schraeg, self.knopf_trafo_weg])
        self._aufbau.addWidget(self.trafo_knoepfe)

    def _baue_aufnahmen(self):
        self._aufbau.addWidget(kopfzeile(tr("dialog.aufnahmen"), "aufnahmen"))
        self.aufnahmen = self._baum(tr("dialog.aufnahmen.tooltip"), MINDESTHOEHE_AUFNAHMEN)
        self.aufnahmen.currentItemChanged.connect(self._aufnahme_gewaehlt)
        self._aufbau.addWidget(self.aufnahmen)

        self.knopf_werkzeug = _knopf(
            tr("dialog.werkzeugaufnahme_neu"),
            lambda: self.aufnahme_anlegen(m.AUFNAHME_WERKZEUG),
        )
        self.knopf_werkstueck = _knopf(
            tr("dialog.werkstueckaufnahme_neu"),
            lambda: self.aufnahme_anlegen(m.AUFNAHME_WERKSTUECK),
        )
        self.knopf_verteilen = _knopf(
            tr("dialog.plaetze_verteilen"),
            self.plaetze_verteilen,
            tr("dialog.plaetze_verteilen.tooltip"),
        )
        self.knopf_auf_weg = _knopf(tr("dialog.entfernen"), self.aufnahme_entfernen)
        self.aufnahmen_knoepfe = _knopfreihe(
            [self.knopf_werkzeug, self.knopf_werkstueck, self.knopf_verteilen, self.knopf_auf_weg]
        )
        self._aufbau.addWidget(self.aufnahmen_knoepfe)

    def _baue_glieder(self):
        self._aufbau.addWidget(kopfzeile(tr("dialog.glieder"), "glieder"))
        self.glieder = QtGui.QListWidget()
        self.glieder.setToolTip(tr("dialog.glieder.tooltip"))
        self.glieder.setWordWrap(True)
        self.glieder.setMouseTracking(True)  # sonst kommt itemEntered nur mit gedrückter Taste
        self.glieder.itemEntered.connect(lambda zeile: self._zeige_spaeter(zeile.data(ROLLE)))
        self._aufbau.addWidget(self.glieder)

    def _baue_hinweise(self):
        self._aufbau.addWidget(kopfzeile(tr("dialog.hinweise")))
        self.hinweise = QtGui.QListWidget()
        self.hinweise.setWordWrap(True)
        # Eine Hinweis-Zeile trägt das Objekt, um das es geht.
        self.hinweise.itemClicked.connect(lambda zeile: self.springe_zu(zeile.data(ROLLE)))
        self._aufbau.addWidget(self.hinweise)

    def _baum(self, tooltip, mindesthoehe):
        """Eine Liste mit eingerückten Zeilen; Verweilen mit der Maus zeigt die Zeile in 3D."""
        baum = QtGui.QTreeWidget()
        baum.setHeaderHidden(True)
        baum.setToolTip(tooltip)
        baum.setMinimumHeight(mindesthoehe)
        baum.setMouseTracking(True)  # sonst kommt itemEntered nur mit gedrückter Taste
        baum.itemEntered.connect(lambda zeile, _spalte: self._zeige_spaeter(zeile.data(0, ROLLE)))
        return baum

    # --- Aktionen: Knöpfe und Oberflächen-Szenarien rufen sie auf -------------

    def betriebsart_anlegen(self, gelenk, art):
        """Neue Betriebsart am Gelenk, der NC-Name vorgeschlagen (D-25); danach steht der
        Cursor im Feld „NC-Name“, der Vorschlag markiert – Tippen ersetzt ihn."""
        achse = self.kette.achse_von(gelenk)
        name = m.vorgeschlagener_name(self.maschine, achse, art) if achse is not None else ""
        ba = m.neue_betriebsart(self.maschine, gelenk, art, name)
        self.neu_aufbauen(auswahl=ba)
        feld = self.details.feld(0)
        if feld is not None:
            feld.setFocus()
            feld.selectAll()

    def betriebsarten_vorschlagen(self):
        """„Vorschlagen“: jedes Gelenk ohne Betriebsart bekommt eine (D-25); gewählt ist
        danach die erste neue – die Hinweise sagen, welche Kennwerte fehlen."""
        neu = m.schlage_betriebsarten_vor(self.maschine, self.kette)
        self.neu_aufbauen(auswahl=neu[0] if neu else None)
        return neu

    def betriebsart_entfernen(self):
        """Entfernt die gewählte Betriebsart; was sie antrieb, hat danach keinen Antrieb."""
        art, ba = _zeilendaten(self.achsen.currentItem())
        if art != ZEILE_BETRIEBSART:
            return
        for aufnahme in m.aufnahmen(self.maschine):
            if aufnahme.Spindel == ba:
                aufnahme.Spindel = None
        # Eine schräge Achse, die sie nutzte, bleibt – gemeldet als „fehlt eine Achse“.
        for trafo in m.transformationen(self.maschine):
            if trafo.Schraeg == ba:
                trafo.Schraeg = None
            if trafo.Ausgleich == ba:
                trafo.Ausgleich = None
        self.doc.removeObject(ba.Name)
        self.neu_aufbauen()

    def aufnahme_anlegen(self, art):
        """Neue Aufnahme. Vorgewählt ist das LCS aus der 3D-Auswahl, sonst das erste freie."""
        alle = self.alle_lcs()
        if not alle:
            QtGui.QMessageBox.information(self.form, tr("dialog.titel"), tr("dialog.kein_lcs"))
            return
        belegt = {a.Lcs for a in m.aufnahmen(self.maschine)}
        gewaehlt = [o for o in FreeCADGui.Selection.getSelection() if o in alle]
        lcs = gewaehlt[0] if gewaehlt else next((x for x in alle if x not in belegt), alle[0])
        aufnahme = m.neue_aufnahme(self.maschine, lcs, art, m.aufnahmeart_text(art))
        self.neu_aufbauen(auswahl=aufnahme)

    def aufnahme_entfernen(self):
        art, aufnahme = _zeilendaten(self.aufnahmen.currentItem())
        if art != ZEILE_AUFNAHME:
            return
        self.doc.removeObject(aufnahme.Name)
        self.neu_aufbauen()

    def schraege_achse_anlegen(self, schraeg=None, ausgleich=None):
        """Neue schräge Achse mit den Betriebsarten `schraeg` und `ausgleich`. Ohne sie ist
        ein Paar vorgewählt, das schräg steht, sonst die ersten beiden Linearachsen
        (schraege_achse.vorschlag)."""
        paar = (schraeg, ausgleich)
        if schraeg is None or ausgleich is None:
            paar = schraege_achse.vorschlag(self.maschine, self.kette)
        if paar is None:
            return
        trafo = m.neue_schraege_achse(self.maschine, *paar)
        self.neu_aufbauen(auswahl=trafo)

    def winkel_setzen(self, trafo, grad):
        """Dreht die Führung der schrägen Achse `trafo` auf `grad` Grad; danach zeigen
        Liste und Felder den neuen Stand (zeitversetzt – das Feld, dessen Signal
        gerade läuft, wird dabei ersetzt)."""
        if self.wackeln:
            self.wackeln.stopp()  # sie bewegt Teile von ihrem eigenen Ausgang aus
        self.kette = schraege_achse.drehe_fuehrung(
            self.assembly, self.kette, self.maschine, trafo, grad
        )
        QtCore.QTimer.singleShot(0, lambda: self._spaeter_neu_aufbauen(trafo))

    def transformation_entfernen(self):
        art, trafo = _zeilendaten(self.transformationen.currentItem())
        if art != ZEILE_TRANSFORMATION:
            return
        self.doc.removeObject(trafo.Name)
        self.neu_aufbauen()

    def plaetze_verteilen(self):
        """Fragt Revolver, ersten Platz und Anzahl ab und legt die Plätze an."""
        revolver = self._revolver()
        if not revolver:
            return
        dialog = VerteilDialog(self.form, revolver, self.lcs_im_revolver)
        if dialog.exec_() != QtGui.QDialog.Accepted:
            return
        ba, erstes_lcs, anzahl = dialog.ergebnis()
        m.verteile_plaetze(self.maschine, self.kette, ba, erstes_lcs, anzahl)
        self.doc.recompute()
        self.neu_aufbauen()

    def uebergeben(self, nachfragen=True):
        """Übergibt die Maschine an CAM und zeigt den Bericht.

        Gibt den Bericht zurück, oder None, wenn nichts übergeben wurde.
        `nachfragen=False` überspringt die Rückfrage bei offenen Warnungen.
        """
        if not export.verfuegbar():
            self._erklaere_fehlende_maschinendefinition()
            return None
        warnungen = [x for x in self.meldungen if x.schwere != HINWEIS]
        if warnungen and nachfragen and not self._trotzdem_uebergeben(len(warnungen)):
            return None
        try:
            bericht = export.exportiere(self.maschine, self.kette)
        except Exception as fehler:  # z. B. Ordner nicht beschreibbar: sagen statt still scheitern
            FreeCAD.Console.PrintError(f"CAM-Addon: {fehler}\n")
            QtGui.QMessageBox.warning(
                self.form, tr("dialog.uebergeben"), tr("uebergeben.fehler", fehler=str(fehler))
            )
            return None
        self.bericht_fenster = BerichtFenster(self.form, self.maschine.Label, bericht)
        self.bericht_fenster.show()
        return bericht

    def zeige(self, daten):
        """Hebt in der 3D-Ansicht hervor, was eine Zeile meint; eine Achse wackelt kurz.

        `daten` sind die Daten einer Zeile: (Art der Zeile, Objekt).
        """
        if self.geschlossen or not daten:
            return
        art, objekt = daten
        if art == ZEILE_GELENK:
            self._zeige_achse(self.kette.achse_von(objekt))
        elif art == ZEILE_BETRIEBSART:
            self._zeige_achse(self.kette.achse_von(objekt.Gelenk))
        elif art == ZEILE_GLIED:
            gui_zeigen.hervorheben(objekt.bauteile)
        elif art == ZEILE_AUFNAHME:
            gui_zeigen.hervorheben([objekt.Lcs])
        elif art == ZEILE_REVOLVER:
            gui_zeigen.hervorheben([p.Lcs for p in m.plaetze(self.maschine, self.kette, objekt)])
        elif art == ZEILE_TRANSFORMATION:
            teile = []
            for ba in (objekt.Schraeg, objekt.Ausgleich):
                achse = self.kette.achse_von(ba.Gelenk) if m.ist_betriebsart(ba) else None
                if achse is not None:
                    teile += gui_zeigen.bauteile_hinter(self.kette, achse)
            gui_zeigen.hervorheben(teile)
            self._zeige_programm_y(objekt)

    def springe_zu(self, bezug):
        """Wählt die Zeile des Objekts `bezug` in „Achsen“, „Transformationen“ oder „Aufnahmen“.

        Beim Hinweis „steht schräg“ legt der Klick die schräge Achse an –
        zeitversetzt, denn der Neuaufbau ersetzt auch die angeklickte Zeile.
        """
        if bezug is None:
            return
        if isinstance(bezug, schraege_achse.Anlegen):
            QtCore.QTimer.singleShot(
                0, lambda: self._spaeter_anlegen(bezug.schraeg, bezug.ausgleich)
            )
            return
        for baum in (self.achsen, self.transformationen, self.aufnahmen):
            for zeile in _alle_zeilen(baum):
                if _zeilendaten(zeile)[1] == bezug:
                    if zeile.parent() is not None:
                        zeile.parent().setExpanded(True)
                    baum.setCurrentItem(zeile)
                    baum.scrollToItem(zeile)
                    return

    def neu_aufbauen(self, auswahl=None):
        """Baut alle Listen neu auf und wählt `auswahl` (Betriebsart, Transformation oder Aufnahme).

        Nötig, wenn sich die Maschine von außen geändert hat.
        """
        self.details.leeren()
        self._fuelle_achsen(auswahl)
        self._fuelle_transformationen(auswahl)
        self._fuelle_aufnahmen(auswahl)
        self._fuelle_glieder()
        self._fuelle_hinweise()
        self._knoepfe_schalten()

    def alle_lcs(self):
        """Alle Koordinatensysteme der Assembly, die als Aufnahme taugen.

        Der Ursprung eines Parts oder Körpers (App::Origin) ist für FreeCAD
        ebenfalls ein LocalCoordinateSystem. Ihn als Aufnahme anzubieten
        („Origin005“) verwirrt nur und würde bei der Vorauswahl sogar gewählt
        (gefunden im Test mit FreeCAD 1.1.3, P-2026-09-25-25).
        """
        return [
            o
            for o in self.assembly.OutListRecursive
            if o.isDerivedFrom("App::LocalCoordinateSystem") and not o.isDerivedFrom("App::Origin")
        ]

    def lcs_im_revolver(self, ba):
        """Die Koordinatensysteme im Glied, das der Revolver `ba` dreht."""
        achse = self.kette.achse_von(ba.Gelenk)
        if achse is None:
            return []
        return [lcs for lcs in self.alle_lcs() if self.kette.glied_von(lcs) is achse.kind]

    # --- Auswahl --------------------------------------------------------------

    def _achse_gewaehlt(self, aktuell, _vorher):
        self._gewaehlt(self.achsen, aktuell)

    def _transformation_gewaehlt(self, aktuell, _vorher):
        self._gewaehlt(self.transformationen, aktuell)

    def _aufnahme_gewaehlt(self, aktuell, _vorher):
        self._gewaehlt(self.aufnahmen, aktuell)

    def _gewaehlt(self, baum, aktuell):
        """Gewählt ist immer nur in einer Liste; darunter stehen die Felder der Zeile."""
        if aktuell is not None:
            for anderer in (self.achsen, self.transformationen, self.aufnahmen):
                if anderer is not baum:
                    _auswahl_aufheben(anderer)
        self._details_zeigen(*_zeilendaten(aktuell))
        self._knoepfe_schalten()

    def _details_zeigen(self, art, objekt):
        """Die Felder zur gewählten Zeile, direkt unter den Knöpfen ihrer Liste."""
        self.details.leeren()
        if art == ZEILE_BETRIEBSART:
            self._details_unter(self.achsen_knoepfe)
            self.details.zeige_betriebsart(objekt, linear=self._ist_linear(objekt))
        elif art == ZEILE_AUFNAHME:
            self._details_unter(self.aufnahmen_knoepfe)
            self.details.zeige_aufnahme(
                objekt, self.alle_lcs(), self._spindeln(), self._auf_revolver(objekt)
            )
        elif art == ZEILE_TRANSFORMATION:
            self._details_unter(self.trafo_knoepfe)
            self.details.zeige_schraege_achse(
                objekt,
                schraege_achse.linearachsen(self.maschine, self.kette),
                schraege_achse.winkel(self.kette, self.maschine, objekt),
                self.winkel_setzen,
            )

    def _details_unter(self, knopfreihe):
        self._aufbau.removeWidget(self.details)
        self._aufbau.insertWidget(self._aufbau.indexOf(knopfreihe) + 1, self.details)

    def _gewaehltes_gelenk(self):
        """Das Gelenk der gewählten Zeile in „Achsen“ – auch wenn eine Betriebsart gewählt ist."""
        art, objekt = _zeilendaten(self.achsen.currentItem())
        if art == ZEILE_GELENK:
            return objekt
        if art == ZEILE_BETRIEBSART:
            return objekt.Gelenk
        return None

    def _knoepfe_schalten(self):
        """Nur die Knöpfe bedienbar machen, die zur Auswahl passen."""
        achse = self.kette.achse_von(self._gewaehltes_gelenk())
        self.knopf_betriebsart.setEnabled(achse is not None)
        mit = [ba.Gelenk for ba in m.betriebsarten(self.maschine)]
        self.knopf_vorschlagen.setEnabled(
            any(all(g != a.gelenk for g in mit) for a in self.kette.achsen)
        )
        art, _objekt = _zeilendaten(self.achsen.currentItem())
        self.knopf_ba_weg.setEnabled(art == ZEILE_BETRIEBSART)
        art, _objekt = _zeilendaten(self.aufnahmen.currentItem())
        self.knopf_auf_weg.setEnabled(art == ZEILE_AUFNAHME)
        self.knopf_verteilen.setEnabled(bool(self._revolver()))
        art, _objekt = _zeilendaten(self.transformationen.currentItem())
        self.knopf_trafo_weg.setEnabled(art == ZEILE_TRANSFORMATION)
        # Eine schräge Achse braucht zwei Linearachsen; der Tooltip sagt, was fehlt.
        genug = len(schraege_achse.linearachsen(self.maschine, self.kette)) >= 2
        self.knopf_schraeg.setEnabled(genug)
        if genug:
            self.knopf_schraeg.setToolTip(tr("dialog.schraege_achse_neu.tooltip"))
        else:
            self.knopf_schraeg.setToolTip(tr("dialog.schraege_achse_neu.fehlt"))

    def _fuelle_betriebsart_menue(self, menue):
        """Die Betriebsarten, die zum gewählten Gelenk passen, jede mit einem Satz Erklärung."""
        menue.clear()
        achse = self.kette.achse_von(self._gewaehltes_gelenk())
        if achse is None:
            return
        for art in m.ERLAUBT[achse.art]:
            aktion = menue.addAction(f"{m.art_text(art)} – {_beschreibung(art)}")
            # art=art hält den Wert dieses Durchlaufs fest.
            aktion.triggered.connect(
                lambda _an=False, art=art: self.betriebsart_anlegen(achse.gelenk, art)
            )

    # --- Eingaben übernehmen --------------------------------------------------

    def _setze(self, objekt, eigenschaft, wert, beschriften=False):
        """Übernimmt eine Eingabe ins Dokument und frischt die Anzeige auf.

        `beschriften`: Die Eingabe ändert einen Namen – dann auch die
        Beschriftung im Baum.
        """
        if getattr(objekt, eigenschaft) == wert:
            return
        setattr(objekt, eigenschaft, wert)
        if beschriften:
            m.beschrifte(objekt)
        if eigenschaft in ("Lcs", "Platz", "Schraeg", "Ausgleich"):
            # Das kann eine Aufnahme in eine Revolvergruppe hinein- oder aus
            # ihr herausschieben bzw. Winkel und Beispiel einer schrägen Achse
            # ändern, dann werden die Listen neu aufgebaut – zeitversetzt,
            # denn der Neuaufbau löscht auch das Feld, dessen Signal gerade läuft.
            QtCore.QTimer.singleShot(0, lambda: self._spaeter_neu_aufbauen(objekt))
        else:
            self._auffrischen()

    def _spaeter_anlegen(self, schraeg, ausgleich):
        if not self.geschlossen:  # inzwischen OK oder Abbrechen gedrückt
            self.schraege_achse_anlegen(schraeg, ausgleich)

    def _spaeter_neu_aufbauen(self, auswahl):
        if not self.geschlossen:  # inzwischen OK oder Abbrechen gedrückt
            self.neu_aufbauen(auswahl)

    def _auffrischen(self):
        """Texte, Status-Symbole und Hinweise der vorhandenen Zeilen erneuern.

        Bewusst ohne Neuaufbau der Listen: Das nach jeder Eingabe zu tun, ließ
        FreeCAD unter PySide6 gelegentlich abstürzen (gefunden im Szenario,
        P-2026-09-25-17).
        """
        if self.geschlossen:
            return
        for baum in (self.achsen, self.transformationen, self.aufnahmen):
            for zeile in _alle_zeilen(baum):
                art, objekt = _zeilendaten(zeile)
                if art == ZEILE_BETRIEBSART:
                    zeile.setText(0, _text_betriebsart(objekt))
                elif art == ZEILE_AUFNAHME:
                    zeile.setText(0, _text_aufnahme(objekt))
                elif art == ZEILE_TRANSFORMATION:
                    zeile.setText(0, self._text_transformation(objekt))
        self._fuelle_hinweise()
        self._knoepfe_schalten()

    def _name_uebernehmen(self):
        text = self.name.text().strip()
        if text:  # ein geleertes Feld behält den bisherigen Namen
            self.maschine.Label = text

    # --- Listen füllen --------------------------------------------------------

    def _fuelle_achsen(self, auswahl=None):
        """Je Achse der Kette eine Zeile, eingerückt darunter ihre Betriebsarten."""
        self.achsen.blockSignals(True)
        self.achsen.clear()
        je_gelenk = {}
        for ba in m.betriebsarten(self.maschine):
            je_gelenk.setdefault(ba.Gelenk, []).append(ba)
        zu_waehlen = None
        for achse in self.kette.achsen:
            zeile = _zeile(_text_gelenk(achse), ZEILE_GELENK, achse.gelenk)
            self.achsen.addTopLevelItem(zeile)
            betriebsarten = je_gelenk.pop(achse.gelenk, [])
            if not betriebsarten:
                zeile.addChild(_leerzeile())
            for ba in betriebsarten:
                unterzeile = _zeile(_text_betriebsart(ba), ZEILE_BETRIEBSART, ba)
                zeile.addChild(unterzeile)
                if ba == auswahl:
                    zu_waehlen = unterzeile
            zeile.setExpanded(True)
        # Übrig sind Betriebsarten, deren Gelenk fehlt oder keine Achse ist. Sie
        # stehen einzeln darunter, damit man sie sieht und entfernen kann.
        for betriebsarten in je_gelenk.values():
            for ba in betriebsarten:
                zeile = _zeile(_text_betriebsart(ba), ZEILE_BETRIEBSART, ba)
                self.achsen.addTopLevelItem(zeile)
                if ba == auswahl:
                    zu_waehlen = zeile
        self.achsen.blockSignals(False)
        if zu_waehlen is not None:
            self.achsen.setCurrentItem(zu_waehlen)

    def _fuelle_transformationen(self, auswahl=None):
        """Je Transformation eine Zeile; ohne eine sagt eine graue Zeile, wann man sie braucht."""
        self.transformationen.blockSignals(True)
        self.transformationen.clear()
        zu_waehlen = None
        for trafo in m.transformationen(self.maschine):
            zeile = _zeile(self._text_transformation(trafo), ZEILE_TRANSFORMATION, trafo)
            self.transformationen.addTopLevelItem(zeile)
            if trafo == auswahl:
                zu_waehlen = zeile
        if not self.transformationen.topLevelItemCount():
            self.transformationen.addTopLevelItem(
                _leerzeile(tr("dialog.keine_transformation"), tr("dialog.transformationen.tooltip"))
            )
        self.transformationen.blockSignals(False)
        if zu_waehlen is not None:
            self.transformationen.setCurrentItem(zu_waehlen)

    def _text_transformation(self, trafo):
        """„Schräge Achse Y1 – gleicht aus: X1, 30,0°“"""
        alpha = schraege_achse.winkel(self.kette, self.maschine, trafo)
        return tr(
            "dialog.zeile_schraege_achse",
            schraeg=_name_oder_frage(trafo.Schraeg),
            ausgleich=_name_oder_frage(trafo.Ausgleich),
            winkel=winkel_zeigen(alpha),
        )

    def _fuelle_aufnahmen(self, auswahl=None):
        """Alle Aufnahmen; die Plätze eines Revolvers zugeklappt unter einer Kopfzeile.

        Sonst würde die Liste bei 12 Plätzen unübersichtlich.
        """
        self.aufnahmen.blockSignals(True)
        self.aufnahmen.clear()
        gruppe_von = {}  # Platz -> Kopfzeile seines Revolvers
        for ba in self._revolver():
            plaetze = m.plaetze(self.maschine, self.kette, ba)
            if plaetze:
                text = tr("dialog.revolver_gruppe", name=m.name_von(ba), anzahl=len(plaetze))
                kopf = _zeile(text, ZEILE_REVOLVER, ba)
                self.aufnahmen.addTopLevelItem(kopf)
                for platz in plaetze:
                    gruppe_von[platz] = kopf
        zu_waehlen = None
        for aufnahme in sorted(m.aufnahmen(self.maschine), key=lambda a: (a.Art, a.Platz, a.Label)):
            zeile = _zeile(_text_aufnahme(aufnahme), ZEILE_AUFNAHME, aufnahme)
            if aufnahme in gruppe_von:
                gruppe_von[aufnahme].addChild(zeile)
            else:
                self.aufnahmen.addTopLevelItem(zeile)
            if aufnahme == auswahl:
                zu_waehlen = zeile
        self.aufnahmen.blockSignals(False)
        if zu_waehlen is not None:
            if zu_waehlen.parent() is not None:
                zu_waehlen.parent().setExpanded(True)
            self.aufnahmen.setCurrentItem(zu_waehlen)

    def _fuelle_glieder(self):
        """„Bett (steht fest): …“, dann „Glied 2: …“ usw. – das Bett ist Glied 1."""
        self.glieder.clear()
        nummer = 1
        for glied in self.kette.glieder:
            if glied.ist_bett:
                titel = tr("dialog.glied_bett")
            else:
                nummer += 1
                titel = tr("dialog.glied_nummer", nummer=nummer)
            zeile = QtGui.QListWidgetItem(f"{titel}: {glied.namen()}")
            zeile.setData(ROLLE, (ZEILE_GLIED, glied))
            self.glieder.addItem(zeile)

    def _fuelle_hinweise(self):
        """Prüft Kette und Maschine, zeigt die Meldungen und markiert betroffene Zeilen."""
        self.meldungen = list(self.kette.meldungen) + m.pruefe(self.maschine, self.kette)
        self.hinweise.clear()
        if not self.meldungen:
            self.hinweise.addItem(
                QtGui.QListWidgetItem(_status_symbol(True), tr("dialog.alles_gut"))
            )
        for meldung in self.meldungen:
            zeile = QtGui.QListWidgetItem(_meldungs_symbol(meldung), meldung.text)
            zeile.setToolTip(meldung.text)
            zeile.setData(ROLLE, meldung.bezug)
            self.hinweise.addItem(zeile)

        # Häkchen oder Warnzeichen vor jeder Betriebsart, Transformation und Aufnahme.
        betroffen = {x.bezug for x in self.meldungen if x.bezug is not None}
        for baum in (self.achsen, self.transformationen, self.aufnahmen):
            for zeile in _alle_zeilen(baum):
                art, objekt = _zeilendaten(zeile)
                if art in (ZEILE_BETRIEBSART, ZEILE_TRANSFORMATION, ZEILE_AUFNAHME):
                    zeile.setIcon(0, _status_symbol(objekt not in betroffen))

    # --- Zeigen in der 3D-Ansicht ---------------------------------------------

    def _zeige_spaeter(self, daten):
        """Merkt die Zeile unter der Maus vor; gezeigt wird erst nach kurzem Verweilen."""
        self._zeige_ziel = daten
        self._zeige_uhr.start()

    def _zeige_achse(self, achse):
        if achse is None:
            return  # z. B. eine Betriebsart ohne gültiges Gelenk
        gui_zeigen.hervorheben(gui_zeigen.bauteile_hinter(self.kette, achse))
        if self.wackeln and self.wackeln.laeuft() and self.wackeln.achse is achse:
            return  # läuft schon für diese Achse – nicht von vorn anfangen
        if self.wackeln:
            self.wackeln.stopp()
        self.wackeln = gui_zeigen.Wackeln(self.assembly, self.kette, achse)
        self.wackeln.start()

    def _zeige_programm_y(self, trafo):
        """Fährt einmal ein Y des Programms hin und her – beide Schlitten bewegen sich."""
        if self.wackeln and self.wackeln.laeuft() and self.wackeln.achse is trafo:
            return
        if self.wackeln:
            self.wackeln.stopp()
        alpha = schraege_achse.winkel(self.kette, self.maschine, trafo)
        if alpha is None or abs(alpha) > schraege_achse.GROESSTER_WINKEL:
            return
        self.wackeln = gui_zeigen.WackelnProgramm(self.assembly, self.kette, self.maschine, trafo)
        self.wackeln.start()

    # --- Abfragen -------------------------------------------------------------

    def _revolver(self):
        return [ba for ba in m.betriebsarten(self.maschine) if ba.Art == m.ART_REVOLVER]

    def _spindeln(self):
        return [ba for ba in m.betriebsarten(self.maschine) if ba.Art == m.ART_SPINDEL]

    def _auf_revolver(self, aufnahme):
        """Sitzt die Aufnahme auf einem Revolver – im Glied, das eine Revolverachse dreht?"""
        if aufnahme.Lcs is None:
            return False
        glied = self.kette.glied_von(aufnahme.Lcs)
        achsen = (self.kette.achse_von(ba.Gelenk) for ba in self._revolver())
        return any(achse is not None and achse.kind is glied for achse in achsen)

    def _ist_linear(self, ba):
        achse = self.kette.achse_von(ba.Gelenk)
        return achse is not None and achse.art == LINEAR

    # --- Rückfragen -----------------------------------------------------------

    def _trotzdem_uebergeben(self, anzahl_warnungen):
        antwort = QtGui.QMessageBox.question(
            self.form,
            tr("dialog.uebergeben"),
            tr("uebergeben.trotz_hinweisen", anzahl=anzahl_warnungen),
        )
        return antwort == QtGui.QMessageBox.Yes

    def _erklaere_fehlende_maschinendefinition(self):
        """FreeCAD 1.1 hat keine CAM-Maschinendefinition: sagen, wo es sie gibt."""
        self.hinweis_fenster = QtGui.QMessageBox(
            QtGui.QMessageBox.Information,
            tr("dialog.uebergeben"),
            tr("uebergeben.nicht_verfuegbar", version=".".join(FreeCAD.Version()[:3])),
            QtGui.QMessageBox.Ok,
            self.form,
        )
        # open() statt exec(): sperrt den Dialog darunter, hält aber den Ablauf
        # nicht an – so kann das Szenario das Fenster prüfen und schließen.
        self.hinweis_fenster.open()


class _EnterBleibtImDialog(QtCore.QObject):
    """Enter bestätigt nur das Feld, statt den ganzen Dialog mit OK zu schließen.

    Ein Feld verarbeitet Enter – es übernimmt dabei seinen Wert – und reicht
    die Taste dann an die Widgets darüber weiter. Käme sie bis zu FreeCADs
    Aufgabenfenster, löste sie dort „OK“ aus (B-005, entschieden von Manuel).
    Dieser Filter sitzt ganz oben im Dialog und hält die Taste dort an.
    """

    def eventFilter(self, _objekt, ereignis):
        return ereignis.type() == QtCore.QEvent.KeyPress and ereignis.key() in (
            QtCore.Qt.Key_Return,
            QtCore.Qt.Key_Enter,
        )


# --- Zeilen der Listen --------------------------------------------------------


def _zeile(text, art, objekt):
    zeile = QtGui.QTreeWidgetItem([text])
    zeile.setData(0, ROLLE, (art, objekt))
    return zeile


def _leerzeile(text=None, tooltip=None):
    """Graue, nicht wählbare Zeile – ohne Text „noch keine Betriebsart“ unter einem Gelenk."""
    zeile = QtGui.QTreeWidgetItem([text or tr("dialog.noch_keine_betriebsart")])
    zeile.setToolTip(0, tooltip or tr("dialog.noch_keine_betriebsart.tooltip"))
    zeile.setForeground(0, QtGui.QBrush(QtGui.QColor("gray")))
    zeile.setFlags(QtCore.Qt.NoItemFlags)
    return zeile


def _zeilendaten(zeile):
    """(Art der Zeile, Objekt); (None, None) für keine Zeile oder eine Leerzeile."""
    daten = zeile.data(0, ROLLE) if zeile is not None else None
    return daten or (None, None)


def _alle_zeilen(baum):
    """Alle Zeilen eines Baums, auch die eingerückten."""
    zeiger = QtGui.QTreeWidgetItemIterator(baum)
    while zeiger.value():
        yield zeiger.value()
        zeiger += 1


def _auswahl_aufheben(baum):
    """Hebt die Auswahl in `baum` auf, ohne dass seine Signale feuern."""
    baum.blockSignals(True)
    baum.setCurrentItem(None)
    baum.blockSignals(False)


def _text_gelenk(achse):
    """„↔  X   (Schiebegelenk)“ – das Zeichen zeigt die Bewegung."""
    if achse.art == LINEAR:
        zeichen, art = "↔", tr("gelenk.schiebe")
    else:
        zeichen, art = "⟳", tr("gelenk.dreh")
    return f"{zeichen}  {achse.gelenk.Label}   ({art})"


def _text_betriebsart(ba):
    """„X1  ·  Linear“"""
    return f"{m.name_von(ba)}  ·  {m.art_text(ba.Art)}"


def _text_aufnahme(aufnahme):
    """„P3  ·  Werkzeug  ·  → Werkzeugplatz_P3  ·  angetrieben von S4“"""
    lcs = aufnahme.Lcs.Label if aufnahme.Lcs is not None else "?"
    teile = [m.name_von(aufnahme), m.aufnahmeart_text(aufnahme.Art), "→ " + lcs]
    if aufnahme.Spindel is not None:
        teile.append(tr("aufnahme.angetrieben_von", spindel=m.name_von(aufnahme.Spindel)))
    return "  ·  ".join(teile)


def _name_oder_frage(ba):
    """NC-Name einer Betriebsart – „?“, wenn keine gewählt ist."""
    return m.name_von(ba) if ba is not None else "?"


def _beschreibung(art):
    """Ein Satz zur Betriebsart für das Menü unter „+ Betriebsart“."""
    return {
        m.ART_LINEAR: tr("art.linear.beschreibung"),
        m.ART_POSITIONIEREN: tr("art.positionieren.beschreibung"),
        m.ART_SPINDEL: tr("art.spindel.beschreibung"),
        m.ART_REVOLVER: tr("art.revolver.beschreibung"),
    }[art]


def _status_symbol(in_ordnung):
    """Häkchen oder Warnzeichen aus dem Qt-Stil – passt so zu jedem Farbschema."""
    stil = QtGui.QApplication.style()
    if in_ordnung:
        return stil.standardIcon(QtGui.QStyle.SP_DialogApplyButton)
    return stil.standardIcon(QtGui.QStyle.SP_MessageBoxWarning)


def _meldungs_symbol(meldung):
    stil = QtGui.QApplication.style()
    if meldung.schwere == HINWEIS:
        return stil.standardIcon(QtGui.QStyle.SP_MessageBoxInformation)
    return stil.standardIcon(QtGui.QStyle.SP_MessageBoxWarning)


# --- Knöpfe -------------------------------------------------------------------


def _knopf(text, aktion, tooltip=""):
    """Ein Knopf, der `aktion()` ohne Argumente aufruft."""
    knopf = QtGui.QPushButton(text)
    knopf.setToolTip(tooltip)
    # Die Lambda schluckt das Argument „checked“ von clicked – sonst landete
    # es etwa in uebergeben(nachfragen=…).
    knopf.clicked.connect(lambda: aktion())
    return knopf


def _knopfreihe(knoepfe, spalten=2):
    """Knöpfe nebeneinander, mit `spalten` Knöpfen je Reihe."""
    reihe = QtGui.QWidget()
    raster = QtGui.QGridLayout(reihe)
    raster.setContentsMargins(0, 0, 0, 0)
    for nummer, knopf in enumerate(knoepfe):
        raster.addWidget(knopf, nummer // spalten, nummer % spalten)
    return reihe
