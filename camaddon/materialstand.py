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

Geschwenkte Ebenen verwenden für ihre Vorgänger den räumlichen Rest aus
raum_material: mehrere getrennte Abschnitte, endliche Schneidenlänge und jede feste
Werkzeugrichtung. Nur die aktuelle, von oben bearbeitete Ebene wird wieder als
Höhenfeld angeboten; unbekannte Vorgänger lassen das ursprüngliche Rohteil stehen.

Läuft ohne Oberfläche; numpy gehört zu FreeCAD.
"""

import contextlib
import copy
import hashlib
import math
from collections import OrderedDict
from dataclasses import dataclass, field

import numpy as np

from . import fraeserform as ff
from . import hoehenfeld as hf
from . import maschinenzugang as mz
from . import reichweite as rw
from . import restmaterial as rm
from .sprache import tr

SCHRITT = rm.SCHRITT_XY  # mm – das Raster
BOGENSCHRITT = 0.5  # mm – in so langen Sehnen fährt es Bögen ab
# So viele Stände bleiben gemerkt – höchstens GEMERKT_MB zusammen. Je Job das Rohteil und der
# Stand nach jeder Operation: In der 8-Eck-Stange (acht Aufspannungen, je zwei Operationen) fielen
# bei 8 Ständen die der ersten Aufspannungen heraus und wurden je Prüfung neu gerechnet (18 s).
GEMERKT = 64
GEMERKT_MB = 256.0
MATERIAL = 0.05  # mm – so viel muss über einer Lage stehen, damit es als Material zählt
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
    def schritt(self):
        """Das Raster (mm)."""
        return float(self.quader.x[1] - self.quader.x[0])

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

    def volumen(self, maske, z_unten, boden=None):
        """(noch, weg) in mm³: was in der Maske über `z_unten` noch steht – und was die
        Operationen davor dort schon weggenommen haben; mit `boden` (je Zelle, das Teil von
        oben) nur, was über ihm steht."""
        h, voll = self.quader.h[maske], self.voll[maske]
        if boden is not None:
            z_unten = np.maximum(np.asarray(boden)[maske], z_unten)
        noch = np.where(np.isfinite(h), np.maximum(h - z_unten, 0.0), 0.0)
        vorher = np.where(np.isfinite(voll), np.maximum(voll - z_unten, 0.0), 0.0)
        return float(noch.sum()) * self.zelle, float((vorher - noch).sum()) * self.zelle

    def wer(self, maske):
        """Die Namen der Operationen, die in der Maske etwas weggenommen haben, der Reihe nach."""
        return [n for n, g in zip(self.namen, self.gesenkt, strict=True) if (g & maske).any()]

    def hoehen_an(self, xs, ys, naechste=False):
        """(len(xs), len(ys)): wie hoch das Material über den Knoten eines anderen Rasters noch
        steht – je Knoten das Höchste der Zellen um ihn (lieber Material sehen, wo keins ist, als
        keins, wo es steht), mit `naechste` die nächste Zelle; außerhalb des Rohteils −inf."""
        q = self.quader
        schritt_x, schritt_y = q.x[1] - q.x[0], q.y[1] - q.y[0]
        fx = (np.asarray(xs, dtype=float) - q.x[0]) / schritt_x
        fy = (np.asarray(ys, dtype=float) - q.y[0]) / schritt_y
        if naechste:
            versatz_x, versatz_y = [np.rint(fx).astype(int)], [np.rint(fy).astype(int)]
        else:
            versatz_x = [np.floor(fx).astype(int) + d for d in (0, 1)]
            versatz_y = [np.floor(fy).astype(int) + d for d in (0, 1)]
        ergebnis = np.full((len(fx), len(fy)), -np.inf)
        for i in versatz_x:
            gi = (i >= 0) & (i < len(q.x))
            for j in versatz_y:
                gj = (j >= 0) & (j < len(q.y))
                werte = np.full((len(fx), len(fy)), -np.inf)
                werte[np.ix_(gi, gj)] = q.h[np.ix_(i[gi], j[gj])]
                np.maximum(ergebnis, werte, out=ergebnis)
        return ergebnis

    def maske_aus(self, xs, ys, maske):
        """Die Zellen, über denen eine Maske eines anderen Rasters (Knoten `xs` × `ys`) wahr
        ist – je Zelle der nächste Knoten; außerhalb des Rasters falsch."""
        q = self.quader
        schritt_x, schritt_y = xs[1] - xs[0], ys[1] - ys[0]
        i = np.rint((q.x - xs[0]) / schritt_x).astype(int)
        j = np.rint((q.y - ys[0]) / schritt_y).astype(int)
        gi = (i >= 0) & (i < len(xs))
        gj = (j >= 0) & (j < len(ys))
        ergebnis = np.zeros((len(q.x), len(q.y)), dtype=bool)
        ergebnis[np.ix_(gi, gj)] = np.asarray(maske, dtype=bool)[np.ix_(i[gi], j[gj])]
        return ergebnis

    def maske_um_punkte(self, x, y, radius):
        """Die Zellen, die eine Scheibe mit `radius` um einen der Punkte (x, y) trifft – je Punkt
        um seine nächste Zelle (auf eine Zelle genau)."""
        q = self.quader
        schritt_x, schritt_y = q.x[1] - q.x[0], q.y[1] - q.y[0]
        i = np.rint((np.ravel(x) - q.x[0]) / schritt_x).astype(int)
        j = np.rint((np.ravel(y) - q.y[0]) / schritt_y).astype(int)
        gueltig = (i >= 0) & (i < len(q.x)) & (j >= 0) & (j < len(q.y))
        punkte = np.zeros((len(q.x), len(q.y)), dtype=bool)
        punkte[i[gueltig], j[gueltig]] = True
        return _aufweiten(punkte, radius, schritt_x, schritt_y)

    def hoechste_um(self, x, y, radius):
        """Das höchste Material, das eine Scheibe mit `radius` um einen der Punkte trifft – None,
        wo keins ist."""
        return self.hoechste(self.maske_um_punkte(x, y, radius))

    def hoechste_bei(self, x, y, radius):
        """Das höchste Material unter einer Scheibe mit `radius` um (x, y) – −inf, wo keins ist
        (nur das Fenster um die Stelle: schnell, für einzelne Stellen)."""
        q = self.quader
        schritt_x, schritt_y = q.x[1] - q.x[0], q.y[1] - q.y[0]
        i0 = max(int(math.floor((x - radius - q.x[0]) / schritt_x)), 0)
        i1 = min(int(math.ceil((x + radius - q.x[0]) / schritt_x)) + 1, len(q.x))
        j0 = max(int(math.floor((y - radius - q.y[0]) / schritt_y)), 0)
        j1 = min(int(math.ceil((y + radius - q.y[0]) / schritt_y)) + 1, len(q.y))
        if i1 <= i0 or j1 <= j0:
            return -math.inf
        dx = q.x[i0:i1, None] - x
        dy = q.y[None, j0:j1] - y
        fenster = q.h[i0:i1, j0:j1][dx * dx + dy * dy <= radius * radius]
        fenster = fenster[np.isfinite(fenster)]
        return float(fenster.max()) if fenster.size else -math.inf

    def trifft(self, lage, radius, x, y):
        """Je Punkt (x, y, gleich geformt): Trifft eine Scheibe mit `radius` um ihn Material, das
        mehr als MATERIAL über `lage` steht? (Um die nächste Zelle, auf eine Zelle genau.)"""
        q = self.quader
        schritt_x, schritt_y = q.x[1] - q.x[0], q.y[1] - q.y[0]
        with np.errstate(invalid="ignore"):
            ueber = q.h > lage + MATERIAL
        weit = _aufweiten(ueber, radius, schritt_x, schritt_y)
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        i = np.rint((x - q.x[0]) / schritt_x).astype(int)
        j = np.rint((y - q.y[0]) / schritt_y).astype(int)
        gueltig = (i >= 0) & (i < len(q.x)) & (j >= 0) & (j < len(q.y))
        ergebnis = np.zeros(x.shape, dtype=bool)
        ergebnis[gueltig] = weit[i[gueltig], j[gueltig]]
        return ergebnis


_SCHEIBEN = OrderedDict()  # (Form, Schritte, Radius) → die Scheibe im Frequenzraum


def _aufweiten(maske, radius, schritt_x, schritt_y):
    """Die Maske um `radius` weiter: wahr, wo eine Scheibe mit dem Radius um die Zelle etwas
    Wahres trifft (Faltung über die FFT, je Radius und Raster die Scheibe einmal)."""
    if radius <= 0 or not maske.any():
        return maske.copy()
    mx = int(math.ceil(radius / schritt_x))
    my = int(math.ceil(radius / schritt_y))
    nx, ny = maske.shape
    groesse = (nx + 2 * mx + 1, ny + 2 * my + 1)
    schluessel = (groesse, round(schritt_x, 9), round(schritt_y, 9), round(radius, 6))
    kern = _SCHEIBEN.get(schluessel)
    if kern is None:
        dx = np.arange(-mx, mx + 1)[:, None] * schritt_x
        dy = np.arange(-my, my + 1)[None, :] * schritt_y
        scheibe = np.zeros(groesse)
        scheibe[: 2 * mx + 1, : 2 * my + 1] = dx * dx + dy * dy <= radius * radius + 1e-12
        kern = _SCHEIBEN[schluessel] = np.fft.rfft2(scheibe)
        while len(_SCHEIBEN) > 16:
            _SCHEIBEN.popitem(last=False)
    werte = np.zeros(groesse)
    werte[:nx, :ny] = maske
    gefaltet = np.fft.irfft2(np.fft.rfft2(werte) * kern, s=groesse)
    return gefaltet[mx : mx + nx, my : my + ny] > 0.5


class SchonWeg(ValueError):
    """Über den Flächen steht nichts mehr, was die Operation wegnehmen kann – die Operationen
    davor haben es schon weggenommen (W-012). Der Assistent nimmt ihr dann den Haken."""


def schon_weg(davor):
    """Der Fehler „Hier ist nichts mehr zu tun – das hat „…“ schon weggenommen.“"""
    return SchonWeg(tr("ms.fehler.schon_weg", wer=wer_text(davor)))


def wer_text(namen):
    """„„Räumen T1““ – mehrere: „„Räumen T1“ und „Nut T2““."""
    zitiert = [tr("ms.zitat", name=n) for n in namen]
    if len(zitiert) == 1:
        return zitiert[0]
    return tr("ms.und", vorne=", ".join(zitiert[:-1]), hinten=zitiert[-1])


_GEMERKT = OrderedDict()  # Kennung → Materialstand


def fuer(job, vor=None, dazu=()):
    """Der Materialstand im Job vor der Operation `vor` (ohne: nach allen) – danach die Bahnen
    `dazu` ([(Name, [bahn.Punkt], Fräser)]: Form oder Radius), die der Assistent im selben Lauf
    vorher anlegt. None ohne Rohteil, und wenn eine Operation davor eine Rundachse dreht."""
    from . import reichweite as rw_

    return rw_.zu_ende(fuer_schritte(job, vor, dazu))


def fuer_schritte(job, vor=None, dazu=()):
    """fuer() als Generator (das Ergebnis ist sein Rückgabewert): beim Abfahren der Bahnen
    zwischendurch ein `yield` – für den Lauf des Assistenten „Bearbeitung“ aus der
    Ereignisschleife (P-2026-10-11-54)."""
    try:
        anfang = _rohteil_kennung(job)
    except ValueError:
        return None
    davor = operationen_vor(job, vor)
    schritte = [(_kennung_zugang(job, op), op) for op in davor]
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
        stand = yield from _rohteil_schritte(job, anfang)
        fertig = 0
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
            yield from _fahre_punkte_schritte(stand.quader, punkte, _grosszuegig(fraeser))
        else:
            if mz.operation_erreichbar(job, was) is False:
                stand.kennung = stand.kennung + (kennung,)
                _merken(_kopie(stand))
                continue
            from . import simultan_operation as so

            if so.ist_simultan(was):
                return None  # Keine aus der senkrechten Ersatzbahn angenommene Vorbearbeitung.
            name = was.Label
            fraeser = _grosszuegig(rm._fraeser(was.ToolController))
            if not (yield from _fahre_befehle_schritte(stand.quader, was.Path.Commands, fraeser)):
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
    return "|".join([anfang] + [_kennung_zugang(job, op) for op in operationen_vor(job, vor)])


def _kennung_zugang(job, op):
    return _kennung_op(op) + f" zugang {mz.operation_erreichbar(job, op)}"


def operationen_vor(job, vor=None):
    """Die aktiven Operationen mit Werkzeug, die im Job vor `vor` stehen (ohne: alle) – wie der
    Postprozessor sie nimmt (reichweite._operationen); trägt eine Nachbearbeitung `vor`, endet
    die Folge vor ihr."""
    return list(
        im_durchgang(
            "operationen",
            (objekt_schluessel(job), objekt_schluessel(vor)),
            lambda: _operationen_vor(job, vor),
        )
    )


def _operationen_vor(job, vor):
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
    """Die Kennung des Rohteils: seine Art und Maße – bei einer geschwenkten Ebene (3+2) dazu
    die Ebene und woraus der Stand ihres Grundjobs und der Ebenen davor gerechnet würde
    (kennung_vor, ohne ihn zu rechnen). ValueError ohne Rohteil."""
    with _durchgang():
        return im_durchgang(
            "rohteil", objekt_schluessel(job), lambda: _rohteil_kennung_rechnen(job)
        )


def _rohteil_kennung_rechnen(job):
    rohteil = getattr(job, "Stock", None)
    form = getattr(rohteil, "Shape", None)
    if form is None or form.isNull():
        raise ValueError("kein Rohteil")
    bb = form.BoundBox
    werte = (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)
    art = "quader" if _ist_quader(rohteil) else f"form {form.Volume:.3f}"
    kennung = f"{art} " + " ".join(f"{w:.4f}" for w in werte)
    from . import schwenken as sw

    folge = sw.folge_vor(job)  # Grundjob, Ebenen oder Aufspannungen davor (W-018)
    if folge:
        from . import raum_material as raum

        # Woraus der Stand davor gerechnet würde – nicht der Stand selbst: Ihn zu rechnen (das
        # Höhenfeld jeder Ebene davor) kostete in der Kette der Ebenen am Geist je Prüfung des
        # Materialstands knapp 1 s im Fenster, und gebraucht wurde nur seine Kennung.
        teile = [kennung, _placement_text(sw.lage_im_grundjob(job))]
        teile += [
            f"{_placement_text(sw.lage_im_grundjob(d))} {kennung_vor(d, None)}" for d in folge
        ]
        kennung += " ebene " + hashlib.sha1(" | ".join(map(str, teile)).encode()).hexdigest()
        kennung += " raum " + raum.kennung(job, SCHRITT)
    return kennung


def _placement_text(placement):
    if placement is None:
        return "grund"
    m = placement.toMatrix()
    return " ".join(f"{v:.6f}" for v in m.A[:12])


def _ist_quader(rohteil):
    """Ist das Rohteil ein Kasten längs der Achsen des Jobs – der Quader des Jobs (mit Aufmaß
    oder mit Maßen), nicht gedreht? Ein gedrehter (das Rohteil einer geschwenkten Ebene,
    schwenken.lege_an) zählt wie ein Körper: Sonst stünde Material in den Ecken seines
    Kastens, die es nicht gibt."""
    if not (hasattr(rohteil, "ExtZpos") or hasattr(rohteil, "Length")):
        return False
    drehung = getattr(getattr(rohteil, "Placement", None), "Rotation", None)
    return drehung is None or drehung.isIdentity()


def _eingezogen(h):
    """`h` (Höhen je Knoten, −inf außerhalb) um einen Knoten eingezogen: Wo ein Nachbar (auch
    schräg, auch über den Rand des Rasters hinaus) außerhalb liegt, ist auch der Knoten außerhalb.
    """
    drin = np.isfinite(h)
    rand = np.pad(drin, 1, constant_values=False)
    bleibt = drin.copy()
    nx, ny = drin.shape
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                bleibt &= rand[1 + di : 1 + di + nx, 1 + dj : 1 + dj + ny]
    return np.where(bleibt, h, -np.inf)


def _rohteil(job, kennung):
    """Der Stand ohne Operation: das Rohteil im Raster."""
    from . import reichweite as rw_

    return rw_.zu_ende(_rohteil_schritte(job, kennung))


def _rohteil_schritte(job, kennung):
    """_rohteil als Generator (das Ergebnis ist sein Rückgabewert): In einer Ebene sucht es das
    Material Stufe für Stufe von oben – dazwischen ein `yield` (am Geist stand das Fenster dafür
    in der Vorschau jeder Ebene knapp 1 s am Stück)."""
    rohteil = job.Stock
    form = rohteil.Shape
    bb = form.BoundBox
    if bb.XLength <= 0 or bb.YLength <= 0:
        return None
    quader = rm.Quader(bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax, SCHRITT)
    if not _ist_quader(rohteil):
        from . import vierachs_flaechen as vf

        netz = vf.vernetze(form, hf.VORSCHAU_TOLERANZ).netz
        # Um eine Zelle eingezogen: hoehen_an() sieht je Knoten das Höchste der Zellen um ihn
        # (lieber Material, wo keins ist) – am Rand eines runden Rohteils stand so ein Saum bis
        # eine Zelle außerhalb. Am C-Ring aus Rundmaterial Ø 60 räumte das Räumen ihn um den
        # Ø-60-Mantel herum, gezackt am Raster, durch die Luft (Manuel, 2026-10-18; Grundsatz 5).
        quader.h = _eingezogen(hf.hoehen(netz, quader.x, quader.y))
    from . import schwenken as sw

    if sw.folge_vor(job):
        from . import raum_material as raum

        # Nur aus dem räumlichen Rest – die Höhenfelder der Stände davor braucht es dafür nicht.
        stand = raum.fuer_ebene(job, SCHRITT)
        if stand is not None:
            quader.h = yield from _von_oben_in_der_ebene_schritte(
                quader, sw.lage_im_grundjob(job), [], stand
            )
    return Materialstand(quader, quader.h.copy(), kennung=(kennung,))


EBENE_SCHRITT = 0.25  # mm – so fein sucht es in einer Ebene von oben das Material
EBENE_STUFEN_JE_SCHRITT = 16  # so viele Stufen, dann ein `yield` (_von_oben_in_der_ebene_schritte)


def _von_oben_in_der_ebene(quader, ebene, davor, raeumlich=None):
    """_von_oben_in_der_ebene_schritte bis zum Ende."""
    from . import reichweite as rw_

    return rw_.zu_ende(_von_oben_in_der_ebene_schritte(quader, ebene, davor, raeumlich))


def _von_oben_in_der_ebene_schritte(quader, ebene, davor, raeumlich=None):
    """Die Oberkante in einer 3+2-Ebene aus dem gemeinsamen räumlichen Rest.

    Von der Rohteiloberkante hinab bis zum ersten Materialabschnitt, einschließlich
    konservativer XY-Nachbarschaft und einer Stufe EBENE_SCHRITT Reserve. `davor`
    bleibt für ältere isolierte Aufrufe ohne räumlichen Stand lesbar; reale Jobs
    erhalten bei unbekannter Vorbearbeitung den ursprünglichen Rohteilkörper.
    """
    if raeumlich is None and any(stand is None for _lage, stand in davor):
        return quader.h
    h0 = quader.h
    drin = np.isfinite(h0)
    if not drin.any():
        return h0
    xs, ys = np.meshgrid(quader.x, quader.y, indexing="ij")
    xs, ys = xs[drin], ys[drin]
    oben = h0[drin]
    unten = float(quader.z_von)
    m = ebene.toMatrix()
    r = np.array([[m.A11, m.A12, m.A13], [m.A21, m.A22, m.A23], [m.A31, m.A32, m.A33]])
    b = np.array([m.A14, m.A24, m.A34])
    # Je Stand davor: die Abbildung Grundjob → seine Koordinaten.
    in_stand = []
    for lage, stand in davor:
        if lage is None:
            in_stand.append((np.eye(3), np.zeros(3), stand))
            continue
        mi = lage.inverse().toMatrix()
        ri = np.array(
            [[mi.A11, mi.A12, mi.A13], [mi.A21, mi.A22, mi.A23], [mi.A31, mi.A32, mi.A33]]
        )
        in_stand.append((ri, np.array([mi.A14, mi.A24, mi.A34]), stand))
    ergebnis = np.full(len(oben), -np.inf)
    offen = np.ones(len(oben), dtype=bool)
    # Je Zelle das Höchste des Materials, so weit belegt() um einen Punkt sieht: Ein Punkt darüber
    # trifft nichts und braucht belegt() nicht – von oben sind das fast alle (am Geist in der
    # zweiten Aufspannung stand das Fenster dafür 1,1 s, P-2026-10-18-67).
    oberstes = None if raeumlich is None else _oberstes_der_nachbarn(raeumlich)
    z_von = float(np.max(oben))
    anzahl = int(math.ceil((z_von - unten) / EBENE_SCHRITT)) + 1
    for k in range(anzahl):
        z = z_von - k * EBENE_SCHRITT
        pruefen = offen & (z <= oben + 1e-9)
        if not pruefen.any():
            if not offen.any():
                break
            continue
        p_ebene = np.stack([xs[pruefen], ys[pruefen], np.full(pruefen.sum(), z)], axis=1)
        p_grund = p_ebene @ r.T + b
        if raeumlich is not None:
            material = np.zeros(len(p_grund), dtype=bool)
            moeglich = _unter_dem_obersten(raeumlich, oberstes, p_grund)
            if moeglich.any():
                material[moeglich] = raeumlich.belegt(p_grund[moeglich])
        else:
            material = np.ones(len(p_grund), dtype=bool)
            for ri, bi, stand in in_stand:
                p = p_grund @ ri.T + bi
                material &= _im_stand(stand, p)
        treffer = np.flatnonzero(pruefen)[material]
        ergebnis[treffer] = np.minimum(z + EBENE_SCHRITT, oben[treffer])
        offen[treffer] = False
        if z < unten:
            break
        if k % EBENE_STUFEN_JE_SCHRITT == EBENE_STUFEN_JE_SCHRITT - 1:
            yield
    h = np.full(h0.shape, -np.inf)
    h[drin] = ergebnis
    return h


def _oberstes_der_nachbarn(raeumlich):
    """(nx + 1, ny + 1): an [i + 1, j + 1] das Höchste des Materials der Strahlen i … i + 1,
    j … j + 1 – die vier, die raum_material.Material.belegt() für einen Punkt in der Zelle (i, j)
    fragt; −inf ohne Material."""
    obere = raeumlich.grenzen[..., 1]
    oben = np.where(np.isnan(obere), -np.inf, obere).max(axis=2)
    nx, ny = oben.shape
    rand = np.full((nx + 2, ny + 2), -np.inf)
    rand[1 : nx + 1, 1 : ny + 1] = oben
    return np.maximum.reduce([rand[:-1, :-1], rand[1:, :-1], rand[:-1, 1:], rand[1:, 1:]])


def _unter_dem_obersten(raeumlich, oberstes, punkte):
    """Je Punkt (n, 3): Kann belegt() dort Material finden – liegt er höchstens so hoch wie das
    Oberste um ihn (_oberstes_der_nachbarn)?"""
    from . import raum_material as raum

    a = np.floor((punkte[:, 0] - raeumlich.x[0]) / raeumlich.dx).astype(int) + 1
    b = np.floor((punkte[:, 1] - raeumlich.y[0]) / raeumlich.dy).astype(int) + 1
    drin = (a >= 0) & (a < oberstes.shape[0]) & (b >= 0) & (b < oberstes.shape[1])
    moeglich = np.zeros(len(punkte), dtype=bool)
    moeglich[drin] = punkte[drin, 2] <= oberstes[a[drin], b[drin]] + raum.GENAU
    return moeglich


def _im_stand(stand, punkte):
    """Je Punkt (n, 3) in Koordinaten des Stands: Steht dort Material – über dem Boden seines
    Quaders und unter seiner Höhe (das Höchste der vier Zellen um ihn; außerhalb −inf)?"""
    q = stand.quader
    x, y, z = punkte[:, 0], punkte[:, 1], punkte[:, 2]
    schritt_x, schritt_y = q.x[1] - q.x[0], q.y[1] - q.y[0]
    fx = (x - q.x[0]) / schritt_x
    fy = (y - q.y[0]) / schritt_y
    hoehe = np.full(len(x), -np.inf)
    for di in (0, 1):
        i = np.floor(fx).astype(int) + di
        for dj in (0, 1):
            j = np.floor(fy).astype(int) + dj
            gueltig = (i >= 0) & (i < len(q.x)) & (j >= 0) & (j < len(q.y))
            werte = np.full(len(x), -np.inf)
            werte[gueltig] = q.h[i[gueltig], j[gueltig]]
            np.maximum(hoehe, werte, out=hoehe)
    with np.errstate(invalid="ignore"):
        return (z <= hoehe + 1e-9) & (z >= q.z_von - 1e-9)


def _kopie(stand):
    """Ein Stand zum Weiterrechnen – das Raster geteilt, die Höhen kopiert."""
    quader = copy.copy(stand.quader)
    quader.h = stand.quader.h.copy()
    return Materialstand(quader, stand.voll, list(stand.namen), list(stand.gesenkt), stand.kennung)


def _merken(stand):
    _GEMERKT[stand.kennung] = stand
    _GEMERKT.move_to_end(stand.kennung)
    while len(_GEMERKT) > GEMERKT or (
        len(_GEMERKT) > 1 and sum(_bytes(s) for s in _GEMERKT.values()) > GEMERKT_MB * 2**20
    ):
        _GEMERKT.popitem(last=False)


def _bytes(stand):
    """So viel Speicher belegt ein gemerkter Stand (Höhen, Rohteil, gesenkte Zellen)."""
    gesenkt = sum(getattr(g, "nbytes", 0) for g in stand.gesenkt)
    return stand.quader.h.nbytes + getattr(stand.voll, "nbytes", 0) + gesenkt


# Während einer Rechnung (_rohteil_kennung): was darin schon gerechnet ist – (Art, Schlüssel) →
# Ergebnis; sonst None. Die Kennung einer Aufspannung (oder Ebene) braucht den Stand jeder davor,
# und jeder davon wieder die Kennungen seiner Vorgänger: In der 8-Eck-Stange wurde so für die
# achte Aufspannung 248-mal eine Rohteil-Kennung und 1990-mal die Prüfsumme einer Bahn gerechnet
# (36 s; nach jedem „Anlegen“ stand das Fenster bis 21 s). Innerhalb einer Rechnung ändert sich
# nichts am Dokument – jedes wird darin nur einmal gerechnet.
_DURCHGANG = None


@contextlib.contextmanager
def _durchgang():
    """Eine Rechnung, in der jede Kennung und jeder Stand nur einmal gerechnet wird – verschachtelt
    die äußere."""
    global _DURCHGANG
    if _DURCHGANG is not None:
        yield
        return
    _DURCHGANG = {}
    try:
        yield
    finally:
        _DURCHGANG = None


def im_durchgang(art, schluessel, rechnen):
    """`rechnen()` – in einer Rechnung (_durchgang) je (art, schluessel) nur einmal."""
    if _DURCHGANG is None:
        return rechnen()
    k = (art, schluessel)
    if k not in _DURCHGANG:
        _DURCHGANG[k] = rechnen()
    return _DURCHGANG[k]


def objekt_schluessel(objekt):
    """(Dokument, Name) eines Objekts – None für None."""
    if objekt is None:
        return None
    return (objekt.Document.Name, objekt.Name)


def _kennung_op(op):
    """Name, Fräser und Bahn einer Operation als Text (die Bahn als Prüfsumme)."""
    return im_durchgang("op", objekt_schluessel(op), lambda: _kennung_op_rechnen(op))


def _kennung_op_rechnen(op):
    tc = op.ToolController
    try:
        fraeser = repr(rm._fraeser(tc))
    except Exception:  # ein Werkzeug ohne Maße
        fraeser = "?"
    return f"{op.Name} {fraeser} {_bahn_summe(op)}"


def _bahn_summe(op):
    """Die Prüfsumme der Bahn von `op` – gemerkt, bis sich ihre Bahn ändert (_Bahnen): Den G-Code
    einer Operation zu schreiben kostet (am Geist das 3D-Schlichten, 58.000 Sätze, gut 0,5 s), und
    jede Vorschau und jede Prüfung des Materialstands fragte neu – in der Kette der Ebenen stand das
    Fenster so 18-mal rund eine Sekunde."""
    beobachter = _Bahnen.beobachten()
    schluessel = objekt_schluessel(op)
    if beobachter is not None and schluessel in beobachter.summen:
        return beobachter.summen[schluessel]
    summe = hashlib.blake2b(op.Path.toGCode().encode("utf-8"), digest_size=12).hexdigest()
    if beobachter is not None:
        beobachter.summen[schluessel] = summe
    return summe


class _Bahnen:
    """Ein Beobachter der Dokumente (FreeCAD.addDocumentObserver): je Operation die Prüfsumme ihrer
    Bahn (_bahn_summe), bis sich ihre Eigenschaft „Path“ ändert, sie wegfällt, Rückgängig oder
    Wiederholen ihr Dokument ändert oder es zugeht."""

    _einer = None

    @classmethod
    def beobachten(cls):
        """Der eine Beobachter (beim ersten Bedarf angemeldet); None, wenn FreeCAD keinen nimmt."""
        if cls._einer is None:
            try:
                import FreeCAD

                einer = cls()
                FreeCAD.addDocumentObserver(einer)
            except Exception:  # noqa: BLE001 – ohne Beobachter wird jedes Mal gerechnet
                return None
            cls._einer = einer
        return cls._einer

    def __init__(self):
        self.summen = {}  # (Dokument, Name) -> Prüfsumme der Bahn

    def _weg(self, obj):
        try:
            self.summen.pop(objekt_schluessel(obj), None)
        except Exception:  # noqa: BLE001 – lässt sich nicht zuordnen: alle neu
            self.summen.clear()

    def slotChangedObject(self, obj, prop):  # noqa: N802 – FreeCADs Name
        if prop == "Path":
            self._weg(obj)

    def slotDeletedObject(self, obj):  # noqa: N802
        self._weg(obj)

    def _dokument(self, dokument, *_):
        try:
            name = dokument.Name
        except Exception:  # noqa: BLE001
            self.summen.clear()
            return
        for schluessel in [k for k in self.summen if k[0] == name]:
            del self.summen[schluessel]

    slotUndoDocument = slotRedoDocument = slotDeletedDocument = _dokument  # noqa: N815
    slotRelabelDocument = _dokument  # noqa: N815


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
    from . import reichweite as rw_

    return rw_.zu_ende(_fahre_befehle_schritte(quader, befehle, fraeser))


def _fahre_befehle_schritte(quader, befehle, fraeser):
    """_fahre_befehle als Generator – das Ergebnis ist sein Rückgabewert."""
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
        yield from quader.fahre_stuecke_schritte(von, nach, fraeser)
    return True


def _fahre_punkte(quader, punkte, fraeser):
    """Fährt eine Bahn des Assistenten ([bahn.Punkt]) im Quader ab."""
    for _ in _fahre_punkte_schritte(quader, punkte, fraeser):
        pass


def _fahre_punkte_schritte(quader, punkte, fraeser):
    """_fahre_punkte als Generator."""
    von, nach = [], []
    for a, b in zip(punkte, punkte[1:], strict=False):
        for stueck in sehnen(a, b):
            von.append(stueck[0])
            nach.append(stueck[1])
    if von:
        yield from quader.fahre_stuecke_schritte(von, nach, fraeser)


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
