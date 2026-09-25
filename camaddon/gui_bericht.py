# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Bericht nach „An CAM übergeben“: was angekommen ist und was nicht.

Die Sätze stammen aus export.Bericht; hier werden sie nur gezeigt.
"""

from PySide import QtGui

from .sprache import tr

FENSTER_GROESSE = (520, 420)  # Breite, Höhe in Pixeln


class BerichtFenster(QtGui.QDialog):
    """Zeigt den Bericht einer Übergabe, dazu die gespeicherte Datei."""

    def __init__(self, eltern, name, bericht):
        super().__init__(eltern)
        self.setWindowTitle(tr("dialog.uebergeben"))
        self.resize(*FENSTER_GROESSE)
        self.text = QtGui.QTextBrowser()
        self.text.setHtml(_als_html(name, bericht))
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        knoepfe.rejected.connect(self.close)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.text)
        aufbau.addWidget(knoepfe)


def _als_html(name, bericht):
    """Erfolg und wo die Maschine in CAM steht, dann die drei Listen des Berichts."""
    return "".join(
        [
            f"<p><b>{tr('uebergeben.erfolg', name=name)}</b></p>",
            f"<p>{tr('uebergeben.wo')}</p>",
            _abschnitt(tr("uebergeben.angekommen"), bericht.uebertragen),
            _abschnitt(tr("uebergeben.pruefen"), bericht.zu_pruefen),
            _abschnitt(tr("uebergeben.nur_im_dokument"), bericht.nicht_uebertragen),
            f"<p><small>{tr('uebergeben.datei', datei=str(bericht.datei))}</small></p>",
        ]
    )


def _abschnitt(titel, saetze):
    """Überschrift mit Aufzählung – oder nichts, wenn es keine Sätze gibt."""
    if not saetze:
        return ""
    punkte = "".join(f"<li>{satz}</li>" for satz in saetze)
    return f"<h4>{titel}</h4><ul>{punkte}</ul>"
