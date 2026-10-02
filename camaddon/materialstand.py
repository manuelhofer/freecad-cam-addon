# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Materialstand vor einer Operation (W-012, Spezifikation Strategien 12.7).

Manuel (2026-10-02): „Dann muss natürlich vor jeder neuen Schrupp-Aktion auch geschaut werden …
Ist überhaupt noch viel Material vorhanden, was ich wegmachen muss.“

Das Rohteil von oben als Höhenfeld – wie hoch das Material über (x_i, y_j) noch steht
(restmaterial.Quader, Raster SCHRITT): anfangs der Quader voll bis oben, ein anderes Rohteil (ein
Körper aus dem Dokument, W-011 S4) bis an seine Oberseite, daneben nichts (−inf). Darin fährt es
die Bahnen der Operationen ab, die im Job vor der gefragten stehen – auch FreeCADs eigene, jede
mit der Form ihres Fräsers (restmaterial._fraeser) –, dazu die Bahnen, die der Assistent im
selben Lauf vor ihr anlegt (`dazu`). Ein Fräser, der von oben kommt, lässt nie einen Überhang
stehen: Von oben ist das Höhenfeld genau. Dreht eine Operation davor eine Rundachse, gibt es
keinen Materialstand (None) – die Strategien rechnen dann wie bisher vom Rohteil aus.

Was die Strategien fragen: wie hoch das Material in einem Bereich (einer Maske über dem Raster)
noch höchstens steht (hoechste), wie viel davon über einer Höhe noch da ist und wie viel die
Operationen davor dort schon weggenommen haben (volumen), und welche das waren (wer).

Jeder Stand trägt seine Kennung: woraus er gerechnet ist – das Rohteil, je Operation ihr Name,
ihr Fräser und ihre Bahn (kennung_vor). Eine Operation merkt sich die Kennung, mit der sie
gerechnet hat; ändert sich davor etwas, sieht man es an der Kennung (gui_materialstand rechnet
sie dann neu). Die letzten Stände bleiben gemerkt: Rechnet die nächste Operation des Jobs, fährt
es nur ihren Vorgänger dazu.

Läuft ohne Oberfläche; numpy gehört zu FreeCAD.
"""

import copy
import hashlib
import math
from collections import OrderedDict
from dataclasses import dataclass, field

import numpy as np

from . import fraeserform as ff
from . import hoehenfeld as hf
from . import reichweite as rw
from . import restmaterial as rm

SCHRITT = rm.SCHRITT_XY  # mm – das Raster
BOGENSCHRITT = 0.5  # mm – in so langen Sehnen fährt es Bögen ab
GEMERKT = 8  # so viele Stände bleiben gemerkt
_RUND = 1e-9  # so wenig darf sich eine Rundachse drehen


@dataclass
class Materialstand:
    """Das Material im Job vor einer Operation, von oben."""

    quader: object  # restmaterial.Quader – h[i, j]: so hoch steht das Material noch (−inf: keins)
    voll: np.ndarray  # so hoch stand es im Rohteil
    namen: list = field(default_factory=list)  # die abgefahrenen Operationen, der Reihe nach
    gesenkt: list = field(default_factory=list)  # je Operation: die Zellen, die sie gesenkt hat
    kennung: tuple = ()  # woraus er gerechnet ist (kennung_vor, dazu die Bahnen von `dazu`)

    @property
    def zelle(self):
        """Die Fläche einer Zelle (mm²)."""
        return float((self.quader.x[1] - self.quader.x[0]) * (self.quader.y[1] - self.quader.y[0]))

    def maske_um(self, a, b, abstand):
        """Die Zellen, deren Mitte höchstens `abstand` von der Strecke a–b (je (x, y)) liegt –
        ein Langloch, mit a = b ein Kreis."""
        gx, gy = self.quader.x[:, None], self.quader.y[None, :]
        dx, dy = b[0] - a[0], b[1] - a[1]
        laenge2 = dx * dx + dy * dy
        if laenge2 < 1e-12:
            t = 0.0
        else:
            t = np.clip(((gx - a[0]) * dx + (gy - a[1]) * dy) / laenge2, 0.0, 1.0)
        qx, qy = a[0] + t * dx - gx, a[1] + t * dy - gy
        return qx * qx + qy * qy <= abstand * abstand + 1e-9

    def hoechste(self, maske):
        """Wie hoch das Material in der Maske höchstens steht – None, wo keins ist."""
        werte = self.quader.h[maske]
        werte = werte[np.isfinite(werte)]
        return float(werte.max()) if len(werte) else None

    def volumen(self, maske, z_unten):
        """(noch, weg) in mm³: was in der Maske über `z_unten` noch steht – und was die
        Operationen davor dort schon weggenommen haben."""
        h, voll = self.quader.h[maske], self.voll[maske]
        noch = np.where(np.isfinite(h), np.maximum(h - z_unten, 0.0), 0.0)
        vorher = np.where(np.isfinite(voll), np.maximum(voll - z_unten, 0.0), 0.0)
        return float(noch.sum()) * self.zelle, float((vorher - noch).sum()) * self.zelle

    def wer(self, maske):
        """Die Namen der Operationen, die in der Maske etwas weggenommen haben, der Reihe nach."""
        return [n for n, g in zip(self.namen, self.gesenkt, strict=True) if (g & maske).any()]


_GEMERKT = OrderedDict()  # Kennung → Materialstand


def fuer(job, vor=None, dazu=()):
    """Der Materialstand im Job vor der Operation `vor` (ohne: nach allen) – danach die Bahnen
    `dazu` ([(Name, [bahn.Punkt], Fräser)]: Form oder Radius), die der Assistent im selben Lauf
    vorher anlegt. None ohne Rohteil, und wenn eine Operation davor eine Rundachse dreht."""
    try:
        anfang = _rohteil_kennung(job)
    except ValueError:
        return None
    davor = operationen_vor(job, vor)
    schritte = [(_kennung_op(op), op) for op in davor]
    schritte += [(_kennung_bahn(name, punkte, fraeser), (name, punkte, fraeser))
                 for name, punkte, fraeser in dazu]  # fmt: skip
    kennungen = [anfang] + [k for k, _w in schritte]
    # Der längste schon gerechnete Anfang – dann nur der Rest.
    stand = None
    for n in range(len(kennungen), 0, -1):
        gemerkt = _GEMERKT.get(tuple(kennungen[:n]))
        if gemerkt is not None:
            _GEMERKT.move_to_end(tuple(kennungen[:n]))
            stand, fertig = gemerkt, n - 1
            break
    if stand is None:
        stand, fertig = _rohteil(job, anfang), 0
        if stand is None:
            return None
        _merken(stand)
    if fertig == len(schritte):
        return stand
    stand = _kopie(stand)
    for kennung, was in schritte[fertig:]:
        vorher = stand.quader.h.copy()
        if isinstance(was, tuple):
            name, punkte, fraeser = was
            _fahre_punkte(stand.quader, punkte, _grosszuegig(fraeser))
        else:
            name = was.Label
            fraeser = _grosszuegig(rm._fraeser(was.ToolController))
            if not _fahre_befehle(stand.quader, was.Path.Commands, fraeser):
                return None  # eine Rundachse dreht sich: das kennt ein Höhenfeld von oben nicht
        stand.namen = stand.namen + [name]
        stand.gesenkt = stand.gesenkt + [stand.quader.h < vorher - 1e-9]
        stand.kennung = stand.kennung + (kennung,)
        _merken(_kopie(stand))
    return stand


def kennung_vor(job, vor):
    """Woraus der Materialstand vor `vor` gerechnet würde – das Rohteil und je Operation davor
    Name, Fräser und Bahn; zum Vergleich mit der Kennung, die eine Operation sich gemerkt hat.
    "" ohne Rohteil."""
    try:
        anfang = _rohteil_kennung(job)
    except ValueError:
        return ""
    return "|".join([anfang] + [_kennung_op(op) for op in operationen_vor(job, vor)])


def operationen_vor(job, vor=None):
    """Die aktiven Operationen mit Werkzeug, die im Job vor `vor` stehen (ohne: alle) – wie der
    Postprozessor sie nimmt (reichweite._operationen); trägt eine Nachbearbeitung `vor`, endet
    die Folge vor ihr."""
    ergebnis = []
    for op in rw._operationen(job):
        if vor is not None and (op is vor or _traegt(op, vor)):
            break
        tc = getattr(op, "ToolController", None)
        if tc is not None and getattr(tc, "Tool", None) is not None:
            ergebnis.append(op)
    return ergebnis


def _traegt(op, vor):
    """Ist `op` eine Nachbearbeitung (Dressup), die – auch über andere – `vor` trägt?"""
    basis = getattr(op, "Base", None)
    for _tiefe in range(16):
        if basis is None or not hasattr(basis, "Path"):
            return False
        if basis is vor:
            return True
        basis = getattr(basis, "Base", None)
    return False


def _rohteil_kennung(job):
    """Die Kennung des Rohteils: seine Art und Maße. ValueError ohne Rohteil."""
    rohteil = getattr(job, "Stock", None)
    form = getattr(rohteil, "Shape", None)
    if form is None or form.isNull():
        raise ValueError("kein Rohteil")
    bb = form.BoundBox
    werte = (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)
    art = "quader" if _ist_quader(rohteil) else f"form {form.Volume:.3f}"
    return f"{art} " + " ".join(f"{w:.4f}" for w in werte)


def _ist_quader(rohteil):
    """Ist das Rohteil ein Kasten – der Quader des Jobs (mit Aufmaß oder mit Maßen)?"""
    return hasattr(rohteil, "ExtZpos") or hasattr(rohteil, "Length")


def _rohteil(job, kennung):
    """Der Stand ohne Operation: das Rohteil im Raster."""
    rohteil = job.Stock
    form = rohteil.Shape
    bb = form.BoundBox
    if bb.XLength <= 0 or bb.YLength <= 0:
        return None
    quader = rm.Quader(bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax, SCHRITT)
    if not _ist_quader(rohteil):
        from . import vierachs_flaechen as vf

        netz = vf.vernetze(form, hf.VORSCHAU_TOLERANZ).netz
        quader.h = hf.hoehen(netz, quader.x, quader.y)
    return Materialstand(quader, quader.h.copy(), kennung=(kennung,))


def _kopie(stand):
    """Ein Stand zum Weiterrechnen – das Raster geteilt, die Höhen kopiert."""
    quader = copy.copy(stand.quader)
    quader.h = stand.quader.h.copy()
    return Materialstand(quader, stand.voll, list(stand.namen), list(stand.gesenkt), stand.kennung)


def _merken(stand):
    _GEMERKT[stand.kennung] = stand
    _GEMERKT.move_to_end(stand.kennung)
    while len(_GEMERKT) > GEMERKT:
        _GEMERKT.popitem(last=False)


def _kennung_op(op):
    """Name, Fräser und Bahn einer Operation als Text (die Bahn als Prüfsumme)."""
    tc = op.ToolController
    try:
        fraeser = repr(rm._fraeser(tc))
    except Exception:  # ein Werkzeug ohne Maße
        fraeser = "?"
    bahn = hashlib.blake2b(op.Path.toGCode().encode("utf-8"), digest_size=12).hexdigest()
    return f"{op.Name} {fraeser} {bahn}"


def _kennung_bahn(name, punkte, fraeser):
    """Name, Fräser und Bahn einer Bahn des Assistenten als Text."""
    werte = np.array(
        [
            (p.x, p.y, p.z, float(p.eilgang), *(p.bogen if p.bogen is not None else (0, 0, -1)))
            for p in punkte
        ],
        dtype=float,
    )
    bahn = hashlib.blake2b(werte.tobytes(), digest_size=12).hexdigest()
    return f"{name} {fraeser!r} {bahn}"


def _grosszuegig(fraeser):
    """Der Fräser (Form oder Radius) um so viel breiter, wie das Abfahren in Schritten an
    seinem Rand verliert – die Sehnen der Bögen und die Teilschritte dazwischen lassen am Rand
    einen Saum von Hundertsteln stehen. Was er knapp genommen hat, zählt so als weg; sonst
    stünden auf der Wand einer fertigen Nut Zellen bis oben, und eine zweite Nut finge von vorn
    an. Der Schaftfräser bleibt unten eben."""
    form = fraeser if isinstance(fraeser, ff.Form) else None
    r = float(form.radius) if form is not None else float(fraeser)
    halb = max(rm.TEILSCHRITT, BOGENSCHRITT) / 2
    saum = r - math.sqrt(r * r - halb * halb) if r > halb else halb
    zugabe = max(saum + 0.01, 0.02)
    if form is None or form.eben:
        return r + zugabe
    return form.mit_aufmass(zugabe)


def _fahre_befehle(quader, befehle, fraeser):
    """Fährt die Befehle einer Operation im Quader ab (Bögen in Sehnen, Bohrzyklen hinab und
    zurück). False, wenn sich dabei eine Rundachse dreht."""
    von, nach = [], []
    letzter = None
    for schritt in rw._bahn(befehle, lambda _name: None, rueckzug=True):
        if any(abs(w) > _RUND for w in schritt.rund.values()):
            return False
        if schritt.art == "bogen":
            bogen = schritt.ort
            anzahl = max(2, int(math.ceil(abs(bogen.winkel) * bogen.radius / BOGENSCHRITT)))
            punkte = [bogen.bei(k / anzahl) for k in range(1, anzahl)]  # das Ende kommt danach
        else:
            punkte = [schritt.ort]
        for punkt in punkte:
            if letzter is not None:
                von.append(letzter)
                nach.append(punkt)
            letzter = punkt
    if von:
        quader.fahre_stuecke(von, nach, fraeser)
    return True


def _fahre_punkte(quader, punkte, fraeser):
    """Fährt eine Bahn des Assistenten ([bahn.Punkt]) im Quader ab."""
    von, nach = [], []
    for a, b in zip(punkte, punkte[1:], strict=False):
        for stueck in sehnen(a, b):
            von.append(stueck[0])
            nach.append(stueck[1])
    if von:
        quader.fahre_stuecke(von, nach, fraeser)


def sehnen(von, nach, schritt=BOGENSCHRITT):
    """Die Teilstücke eines Satzes der Bahn (bahn.Punkt) als (x, y, z)-Paare – ein Bogen in
    Sehnen von höchstens `schritt`."""
    if nach.bogen is None:
        return [((von.x, von.y, von.z), (nach.x, nach.y, nach.z))]
    mx, my, uhr = nach.bogen
    r = math.hypot(von.x - mx, von.y - my)
    a0 = math.atan2(von.y - my, von.x - mx)
    a1 = math.atan2(nach.y - my, nach.x - mx)
    bogen = ((a0 - a1) if uhr else (a1 - a0)) % (2 * math.pi)
    if bogen < 1e-9:
        bogen = 2 * math.pi  # Start = Ende: ein Vollkreis
    anzahl = max(2, int(math.ceil(bogen * r / schritt)))
    vorher = (von.x, von.y, von.z)
    ergebnis = []
    for k in range(1, anzahl + 1):
        t = k / anzahl
        a = a0 - t * bogen if uhr else a0 + t * bogen
        jetzt = (mx + r * math.cos(a), my + r * math.sin(a), von.z + (nach.z - von.z) * t)
        ergebnis.append((vorher, jetzt))
        vorher = jetzt
    return ergebnis
