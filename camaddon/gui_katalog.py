# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fenster „Aus dem Katalog der Hersteller“ für Spannmittel und Halter (W-042) – wie die
Werkzeugkiste (gui_werkzeuge.KisteDialog): ein Baum je Gruppe (Art oder Typ), darin die Reihen
der Hersteller, darin jede Größe mit eigenem Haken; am Anfang ist nichts angehakt. Oben eine
Suche über Hersteller, Reihe und Größe. Der Tooltip einer Reihe sagt, woher die Maße kommen."""

from PySide import QtCore, QtGui

from .gui_teile import knopf
from .sprache import tr


class KatalogDialog(QtGui.QDialog):
    """`reihen`: katalog.Reihe; `gruppen`: [(Schlüssel, Text)] in der Reihenfolge der Anzeige,
    `gruppe_von(reihe)` der Schlüssel einer Reihe, `groesse_text(reihe, groesse)` die Zeile einer
    Größe."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern, titel, erklaerung, reihen, gruppen, gruppe_von, groesse_text):
        super().__init__(eltern)
        KatalogDialog.offen = self
        self.setWindowTitle(titel)
        self.resize(760, 640)
        self._alle = list(reihen)
        self._gruppen = list(gruppen)
        self._gruppe_von = gruppe_von
        self._groesse_text = groesse_text
        self._reihen = []
        aufbau = QtGui.QVBoxLayout(self)
        text = QtGui.QLabel(erklaerung)
        text.setWordWrap(True)
        aufbau.addWidget(text)
        self.suche = QtGui.QLineEdit()
        self.suche.setPlaceholderText(tr("kt.suche.platzhalter"))
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(lambda _text: self.fuellen())
        aufbau.addWidget(self.suche)
        self.baum = QtGui.QTreeWidget()
        self.baum.setHeaderHidden(True)
        self.baum.setIndentation(16)
        aufbau.addWidget(self.baum, 1)
        unten = QtGui.QHBoxLayout()
        self.knopf_keine = knopf(tr("kt.keine"), tr("kt.keine.tooltip"), self.keine)
        unten.addWidget(self.knopf_keine)
        unten.addStretch()
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        self.knopf_uebernehmen = knoepfe.button(QtGui.QDialogButtonBox.Ok)
        self.knopf_uebernehmen.setText(tr("kt.uebernehmen"))
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        unten.addWidget(knoepfe)
        aufbau.addLayout(unten)
        self._haken = {}  # (Kennung, Nummer) → angehakt, über die Suche hinweg
        self.fuellen()

    def fuellen(self):
        """Der Baum aus den Reihen, die zur Suche passen; die Haken bleiben."""
        self._merken()
        self.baum.clear()
        self._reihen = []
        worte = self.suche.text().lower().split()
        flags = (
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsAutoTristate
        )
        for schluessel, titel in self._gruppen:
            der_gruppe = []
            for reihe in self._alle:
                if self._gruppe_von(reihe) != schluessel:
                    continue
                groessen = [
                    (n, g)
                    for n, g in enumerate(reihe.groessen)
                    if all(
                        w in f"{reihe.hersteller} {reihe.titel} {g['name']} {g['artikel']}".lower()
                        for w in worte
                    )
                ]
                if groessen:
                    der_gruppe.append((reihe, groessen))
            if not der_gruppe:
                continue
            anzahl = sum(len(g) for _r, g in der_gruppe)
            gruppe = QtGui.QTreeWidgetItem([f"{titel} ({anzahl})"])
            gruppe.setFlags(flags)
            schrift = gruppe.font(0)
            schrift.setBold(True)
            gruppe.setFont(0, schrift)
            self.baum.addTopLevelItem(gruppe)
            for reihe, groessen in der_gruppe:
                zeile = QtGui.QTreeWidgetItem(
                    [
                        tr(
                            "kt.reihe",
                            hersteller=reihe.hersteller,
                            titel=reihe.titel,
                            anzahl=len(groessen),
                        )
                    ]
                )
                zeile.setData(0, QtCore.Qt.UserRole, reihe.kennung)
                zeile.setToolTip(0, reihe.quelle)
                zeile.setFlags(flags)
                gruppe.addChild(zeile)
                self._reihen.append(zeile)
                for nummer, groesse in groessen:
                    eintrag = QtGui.QTreeWidgetItem([self._groesse_text(reihe, groesse)])
                    eintrag.setData(0, QtCore.Qt.UserRole, (reihe.kennung, nummer))
                    eintrag.setToolTip(0, reihe.quelle)
                    eintrag.setFlags(flags)
                    angehakt = self._haken.get((reihe.kennung, nummer), False)
                    eintrag.setCheckState(0, QtCore.Qt.Checked if angehakt else QtCore.Qt.Unchecked)
                    zeile.addChild(eintrag)
            gruppe.setExpanded(bool(worte) or len(self._gruppen) == 1)

    def _merken(self):
        for zeile in self._reihen:
            for i in range(zeile.childCount()):
                eintrag = zeile.child(i)
                schluessel = eintrag.data(0, QtCore.Qt.UserRole)
                self._haken[schluessel] = eintrag.checkState(0) == QtCore.Qt.Checked

    def reihen_eintraege(self):
        """Die Zeilen der Reihen, wie sie gezeigt sind (für die Szenarien)."""
        return list(self._reihen)

    def keine(self):
        """„Keine anhaken“: alle Haken weg, auch die, die die Suche verbirgt."""
        self._haken.clear()
        for i in range(self.baum.topLevelItemCount()):
            self.baum.topLevelItem(i).setCheckState(0, QtCore.Qt.Unchecked)

    def gewaehlt(self):
        """[(Kennung, Nummer)] – alles Angehakte, auch was die Suche gerade verbirgt."""
        self._merken()
        return [schluessel for schluessel, an in self._haken.items() if an]

    def accept(self):
        if not self.gewaehlt():
            QtGui.QMessageBox.information(self, self.windowTitle(), tr("kt.nichts"))
            return
        KatalogDialog.offen = None
        super().accept()

    def reject(self):
        KatalogDialog.offen = None
        super().reject()
