# SPDX-License-Identifier: LGPL-2.1-or-later
"""Was ein Messtaster nach einem Schlichtgang misst (Plan C3b; Manuel, 2026-10-31: „3 mm aufmass
beim schruppen … schlichten auf 2mm … nochmal … auf 1 mm … und jedes mal dazwischen messschritte
… auf der maschine zu verwirklichen ist mir sehr wichtig“ – und zu den Messtastern: „willst du auch
messprogramme einbauen .. wär natürlich cool ^^“).

`merkmal(form, namen)` erkennt an den gewählten Flächen, was sich mit den üblichen Messzyklen der
Steuerungen messen lässt (Siemens CYCLE977, Heidenhain 421–424, Renishaw 9812/9814):

- **tasche:** senkrechte ebene Wände, achsparallel, die ein Rechteck umschließen (ihre Normalen
  zeigen nach innen) – Seitenlängen in X und Y;
- **zapfen:** dasselbe von außen (die Normalen zeigen nach außen);
- **bohrung / welle:** eine senkrechte Zylinderfläche, innen bzw. außen – ihr Durchmesser;
- **nut:** eine Nut (nut_bahn.nuten: Langloch, offen, Bogen- oder Ringnut) – ihre Breite quer zur
  Mittellinie, an einer Stelle: die gerade Nut in der Mitte ihrer Länge, die Bogennut in der Mitte
  ihres Bogens, die Ringnut radial bei +X (dort, wo auch ihre Helix hinabgeht). `winkel` ist die
  Messrichtung (Grad, 0 = in X, 90 = in Y); schräg zu X und Y (achse None) misst kein Zyklus der
  Steuerungen (Heidenhain 425 und Renishaw 9812 nur in einer Achse), dort hält die Maschine zum
  Messen von Hand (Manuel, 2026-11-14: „erstes vorschlichten … dann messsen ... dann
  vertigschlichten“).

Rundungen in den Ecken einer Tasche und am Boden (Zylinder mit waagerechter Achse) zählen nicht
mit. Gemessen wird auf halber Höhe der Wände, höchstens MESS_UNTER_OBEN unter der Oberkante und
mindestens MESS_UEBER_BODEN über dem Boden. `soll(merkmal, aufmass)` ist das Maß nach einem Gang,
der `aufmass` stehen lässt: Tasche, Bohrung und Nut um 2 × Aufmaß kleiner, Zapfen und Welle
größer.

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass, replace

TASCHE, ZAPFEN, BOHRUNG, WELLE, NUT = "tasche", "zapfen", "bohrung", "welle", "nut"
ARTEN = (TASCHE, ZAPFEN, BOHRUNG, WELLE, NUT)
ACHSPARALLEL = 1e-3  # Grad: so nah an 0/90/180/270 misst die Nut noch in X bzw. Y
# So viele Flächen hat eine Nut höchstens (Langloch: 4 Wände, Grund, 4 Rundungen am Grund) – mehr
# gewählt ist mehr als eine Nut; nut_bahn.nuten müsste sonst jede Fläche des Teils lesen.
NUT_FLAECHEN_HOECHSTENS = 16
SENKRECHT = 1e-6  # so klein darf die Z-Komponente einer Wandnormale sein
MESS_UEBER_BODEN = 2.0  # mm
MESS_UNTER_OBEN = 10.0  # mm – tiefer als nötig fährt der Taster nicht
TOLERANZ = 0.02  # mm ±, wenn nichts anderes gesagt ist


@dataclass
class Merkmal:
    art: str  # ARTEN
    x: float  # Mitte (mm im Job)
    y: float
    laenge_x: float = 0.0  # tasche/zapfen: Seitenlängen
    laenge_y: float = 0.0
    durchmesser: float = 0.0  # bohrung/welle
    breite: float = 0.0  # nut: quer zur Mittellinie
    winkel: float = 0.0  # nut: die Messrichtung (Grad, 0 = in X, 90 = in Y)
    z_oben: float = 0.0  # Oberkante der Wände
    z_unten: float = 0.0  # Unterkante (Boden)
    z_mess: float = 0.0  # hier misst der Taster

    @property
    def rund(self):
        return self.art in (BOHRUNG, WELLE)

    @property
    def innen(self):
        return self.art in (TASCHE, BOHRUNG, NUT)

    @property
    def achse(self):
        """Die Nut: „X“ oder „Y“, in der quer gemessen wird – None, wenn sie schräg liegt (dann
        misst kein Zyklus, die Maschine hält); die anderen Merkmale: None."""
        if self.art != NUT:
            return None
        rest = self.winkel % 180.0
        if min(rest, 180.0 - rest) < ACHSPARALLEL:
            return "X"
        if abs(rest - 90.0) < ACHSPARALLEL:
            return "Y"
        return None

    @property
    def zyklus_moeglich(self):
        """Kann ein Messzyklus der Steuerung das messen? Alle außer der schrägen Nut."""
        return self.art != NUT or self.achse is not None


def _normale(flaeche):
    u0, u1, v0, v1 = flaeche.ParameterRange
    return flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)


def _messhoehe(z_oben, z_unten):
    hoehe = z_oben - z_unten
    mitte = z_oben - min(hoehe / 2, MESS_UNTER_OBEN)
    return max(mitte, min(z_unten + MESS_UEBER_BODEN, z_oben - hoehe / 2))


def merkmal(form, namen):
    """Das Merkmal (Merkmal) der Flächen `namen` („Face3“ …) von `form` – None, wenn sie keins
    der vier ergeben (schräge oder gemischte Wände, mehrere Bohrungen …)."""
    flaechen = [form.getElement(n) for n in namen]
    if not flaechen:
        return None
    zylinder = [
        f
        for f in flaechen
        if f.Surface.__class__.__name__ == "Cylinder" and abs(abs(f.Surface.Axis.z) - 1) < 1e-6
    ]
    ebenen = [
        f
        for f in flaechen
        if f.Surface.__class__.__name__ == "Plane" and abs(_normale(f).z) < SENKRECHT
    ]
    m = None
    if zylinder and not ebenen:
        m = _rund(zylinder)
    elif ebenen:
        m = _rechteck(ebenen, zylinder)
    if m is None:
        # Kein Rechteck, keine Bohrung: vielleicht eine Nut (ihre Wände, ihr Grund) – bis 0.380
        # hielt der Messstopp dort ohne Sollmaß.
        return nut_merkmal(form, namen)
    if m is not None:  # Höhe aus allen Flächen: der Boden unter den Rundungen zählt mit
        m.z_unten = min(m.z_unten, min(f.BoundBox.ZMin for f in flaechen))
        m.z_mess = _messhoehe(m.z_oben, m.z_unten)
    return m


def _rund(zylinder):
    """Bohrung oder Welle: alle Flächen auf derselben Achse mit demselben Radius."""
    erste = zylinder[0].Surface
    r, mitte = erste.Radius, erste.Center
    for f in zylinder[1:]:
        s = f.Surface
        if abs(s.Radius - r) > 1e-6 or abs(s.Center.x - mitte.x) + abs(s.Center.y - mitte.y) > 1e-6:
            return None
    z_oben = max(f.BoundBox.ZMax for f in zylinder)
    z_unten = min(f.BoundBox.ZMin for f in zylinder)
    # Innen, wenn die Außennormale des Körpers zur Achse zeigt.
    f = zylinder[0]
    n = _normale(f)
    p = f.valueAt(
        *[(a + b) / 2 for a, b in zip(f.ParameterRange[::2], f.ParameterRange[1::2], strict=True)]
    )
    zur_achse = (mitte.x - p.x) * n.x + (mitte.y - p.y) * n.y > 0
    return Merkmal(
        BOHRUNG if zur_achse else WELLE,
        mitte.x,
        mitte.y,
        durchmesser=2 * r,
        z_oben=z_oben,
        z_unten=z_unten,
        z_mess=_messhoehe(z_oben, z_unten),
    )


def _rechteck(ebenen, ecken):
    """Tasche oder Zapfen: Wände nur in ±X und ±Y, je Richtung mindestens eine; dazu die
    Rundungen in den Ecken (senkrechte Zylinder)."""
    richtungen = set()
    for f in ebenen:
        n = _normale(f)
        if abs(abs(n.x) - 1) < 1e-6:
            richtungen.add(("x", n.x > 0))
        elif abs(abs(n.y) - 1) < 1e-6:
            richtungen.add(("y", n.y > 0))
        else:
            return None  # schräg zu den Achsen
    if len(richtungen) != 4:
        return None
    alle = ebenen + ecken
    x0 = min(f.BoundBox.XMin for f in alle)
    x1 = max(f.BoundBox.XMax for f in alle)
    y0 = min(f.BoundBox.YMin for f in alle)
    y1 = max(f.BoundBox.YMax for f in alle)
    z_oben = max(f.BoundBox.ZMax for f in alle)
    z_unten = min(f.BoundBox.ZMin for f in alle)
    # Jede Wand auf dem Rand des Rechtecks – sonst sind es zwei Taschen, ein Absatz … (ein
    # Rechteck über alles mäße Luft).
    for f in ebenen:
        n = _normale(f)
        b = f.BoundBox
        if abs(n.x) > 0.5 and min(abs(b.XMin - x0), abs(b.XMin - x1)) > 1e-3:
            return None
        if abs(n.y) > 0.5 and min(abs(b.YMin - y0), abs(b.YMin - y1)) > 1e-3:
            return None
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    # Innen (Tasche), wenn die Außennormale einer Wand zur Mitte zeigt.
    f = ebenen[0]
    n = _normale(f)
    p = f.CenterOfMass
    zur_mitte = (mx - p.x) * n.x + (my - p.y) * n.y > 0
    return Merkmal(
        TASCHE if zur_mitte else ZAPFEN,
        mx,
        my,
        laenge_x=x1 - x0,
        laenge_y=y1 - y0,
        z_oben=z_oben,
        z_unten=z_unten,
        z_mess=_messhoehe(z_oben, z_unten),
    )


def _senkrecht_wand(flaeche):
    """Steht die Fläche senkrecht – eine Ebene mit waagerechter Normale oder ein Zylinder um eine
    senkrechte Achse? (An einer Fase oder schrägen Wand hinge die Breite von der Höhe ab.)"""
    art = flaeche.Surface.__class__.__name__
    if art == "Plane":
        return abs(_normale(flaeche).z) < SENKRECHT
    if art == "Cylinder":
        return abs(abs(flaeche.Surface.Axis.z) - 1) < 1e-6
    return False


def nut_merkmal(form, namen):
    """Die Nut der Flächen `namen` (ihre Wände oder ihr Grund, nut_bahn.nuten) als Merkmal: die
    Breite quer zur Mittellinie an einer Stelle (Modulkopf) – None, wenn die Flächen nicht genau
    eine Nut sind oder eine ihrer Wände nicht senkrecht steht (eine Fase außen an der Ringnut)."""
    import math

    from . import nut_bahn as nb

    namen = list(namen)
    if not namen or len(namen) > NUT_FLAECHEN_HOECHSTENS:
        return None
    try:
        nuten = nb.nuten(form, namen)
        if len(nuten) != 1:
            return None
        nut = nuten[0]
        # Jede Fläche gehört zu dieser Nut – sonst misst man etwas, das nicht gewählt ist.
        if any(not any(n.waende == nut.waende for n in nb.nuten(form, [x])) for x in namen):
            return None
        if not all(_senkrecht_wand(form.getElement(w)) for w in nut.waende):
            return None
        z_oben = min(float(form.getElement(w).BoundBox.ZMax) for w in nut.waende)
    except Exception:  # noqa: BLE001 – Part.OCCError: ein Name passt nicht zum Modell
        return None
    z_unten = float(nut.z_unten)
    if z_oben - z_unten <= 1e-6:
        return None
    if nut.bogen is not None:
        mx, my, r_m, w_a, w_b = nut.bogen
        w = 0.0 if nut.ring else 0.5 * (w_a + w_b)  # die Ringnut bei +X, wie ihre Helix
        x, y = mx + r_m * math.cos(w), my + r_m * math.sin(w)
        winkel = math.degrees(w)  # radial
    else:
        (ax, ay), (bx, by) = nut.a, nut.b
        x, y = 0.5 * (ax + bx), 0.5 * (ay + by)
        winkel = math.degrees(math.atan2(by - ay, bx - ax)) + 90.0  # quer zur Mittellinie
    winkel %= 180.0  # gemessen wird hin und her: 0 und 180 Grad sind dieselbe Richtung
    if min(winkel, 180.0 - winkel) < ACHSPARALLEL:
        winkel = 0.0
    elif abs(winkel - 90.0) < ACHSPARALLEL:
        winkel = 90.0
    return Merkmal(
        NUT,
        float(x),
        float(y),
        breite=2.0 * float(nut.radius),
        winkel=round(winkel, 3),
        z_oben=z_oben,
        z_unten=z_unten,
        z_mess=_messhoehe(z_oben, z_unten),
    )


def soll(m, aufmass):
    """Das Merkmal nach einem Gang, der `aufmass` (mm je Seite) stehen lässt."""
    um = -2 * aufmass if m.innen else 2 * aufmass
    if m.rund:
        return replace(m, durchmesser=m.durchmesser + um)
    if m.art == NUT:
        return replace(m, breite=m.breite + um)
    return replace(m, laenge_x=m.laenge_x + um, laenge_y=m.laenge_y + um)


def text(m, toleranz=None):
    """„Tasche 59,4 × 39,4 mm“, „Bohrung Ø 18 mm“, „Nut 15,7 mm quer in Y“ (schräg: „… quer,
    30°“) – mit `toleranz` „… ±0,02“."""
    from . import einheiten
    from .sprache import tr

    art = {
        TASCHE: tr("mn.tasche"),
        ZAPFEN: tr("mn.zapfen"),
        BOHRUNG: tr("mn.bohrung"),
        WELLE: tr("mn.welle"),
        NUT: tr("mn.nut"),
    }[m.art]
    laenge = einheiten.LAENGE
    if m.art == NUT:
        ergebnis = f"{art} {einheiten.text(m.breite, laenge, 3)} {einheiten.einheit(laenge)}"
        if m.achse is not None:
            ergebnis += " " + tr("mn.nut.quer", achse=m.achse)
        else:
            from .werkstoffe import mit_dezimalzeichen

            zahl = f"{m.winkel:.1f}".rstrip("0").rstrip(".")
            zahl = mit_dezimalzeichen(
                zahl, einheiten.gewaehltes_dezimalzeichen() or einheiten.PUNKT
            )
            ergebnis += " " + tr("mn.nut.schraeg", winkel=zahl)
        if toleranz is not None:
            ergebnis += f" ±{einheiten.text(toleranz, laenge, 3)}"
        return ergebnis
    if m.rund:
        mass = f"Ø {einheiten.text(m.durchmesser, laenge, 3)}"
    else:
        mass = f"{einheiten.text(m.laenge_x, laenge, 3)} × {einheiten.text(m.laenge_y, laenge, 3)}"
    ergebnis = f"{art} {mass} {einheiten.einheit(laenge)}"
    if toleranz is not None:
        ergebnis += f" ±{einheiten.text(toleranz, laenge, 3)}"
    return ergebnis
