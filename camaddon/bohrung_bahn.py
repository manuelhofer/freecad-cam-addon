# SPDX-License-Identifier: LGPL-2.1-or-later
"""2,5D, die Bahn „Bohrung fräsen“ (W-006 S3g): zylindrische Bohrungen – durchgehend oder mit
Boden – mit einem Schaftfräser, der kleiner ist als sie. Kein Bohrer nötig, jede Größe mit einem
Fräser, und schneller als die Kontur, die jede Bohrung in Versätzen mit eigener Rampe räumt.

- Die Bohrungen (bohrungen()): senkrechte Zylinderflächen, deren Material außen liegt (die
  Normale zeigt zur Achse), ganz herum; durchgehend, wenn unter ihrem Grund kein Material ist.
- Je Bohrung: in einer **Helix** hinab (G2/G3 mit Z, Steigung aus dem Eintauchwinkel des
  Werkzeugs), unten einmal herum, damit der Boden eben ist. Passt der Kern nicht unter den
  Fräser (Bohrung größer als zwei Fräser), dann in Lagen (ap): je Lage die Helix in der Mitte,
  dann **Ringe nach außen** um ae bis an die Wand (Radius + Aufmaß), jeder mit einem Bogen auf
  den nächsten. Zuletzt das **Schlichten**: die Wand bei Radius in einem Zug (höchstens die
  Schneidenlänge je Zug), mit Halbkreisen aus der Mitte hinein und wieder heraus – im
  Gleichlauf (Spindel rechtsdrehend, M3: das Material rechts, in der Bohrung also gegen den
  Uhrzeigersinn, G3).
- Durchgehende Bohrungen fräst er um `tiefer` unter den Grund, damit kein Grat bleibt.
- Die Zeit mit bahn.zeit; die Bohrungen in der Reihenfolge des kürzesten Wegs von einer zur
  nächsten.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from collections import OrderedDict
from dataclasses import dataclass

from . import bahn as bn
from . import einheiten
from . import formteile as ft
from . import vierachs_bahn as vb
from .sprache import tr

GLEICH = 1e-6
TIEFER = 0.5  # mm – so weit fräst er unter den Grund einer durchgehenden Bohrung
KERN_ANTEIL = 0.9  # vom Fräserradius: so weit außen darf die Helix laufen, und der Kern fällt
MIN_STEIGUNG = 0.05  # mm je Umlauf – flacher wird keine Helix (sonst endlos)
BOGEN_TEILE = 4  # je Umlauf so viele Bögen (G2/G3 mit Z: je ein Viertel)

# Was unter dem Grund einer Bohrung liegt (durch, Spitze), je Form und Fläche (_unter_gemerkt):
# Der Assistent fragt bei einem Klick dutzendfach nach denselben Bohrungen – am Deckel mit vier
# Löchern 1102-mal je acht isInside, 2,4 s (P-2026-10-11-74). Je Form ihr hashCode ->
# (die Form – festgehalten, damit OpenCascade ihren Speicher keiner anderen gibt –, {Fläche: …}).
_UNTER = OrderedDict()
UNTER_FORMEN = 8


@dataclass(frozen=True)
class Bohrung:
    """Eine zylindrische Bohrung im Teil."""

    name: str  # die Zylinderfläche („Face7“)
    mitte: tuple  # (x, y) der Achse
    radius: float
    z_oben: float  # Oberkante der Wand
    z_unten: float  # Grund der Wand
    durch: bool  # unter dem Grund ist kein Material
    spitze: float = 0.0  # Grad: Unten schließt ein Kegel an wie die Spitze eines Bohrers; 0 nicht


@dataclass
class Bohrwerte:
    """Was das Bohrungsfräsen braucht; Längen in mm, z nach oben im Job."""

    fraeser_radius: float
    zustellung: float  # ap: höchstens so tief je Lage, wenn der Kern Ringe braucht
    zeilenabstand: float  # ae: so weit rücken die Ringe nach außen
    aufmass: float  # bleibt beim Schruppen an der Wand – fürs Schlichten
    oben: float  # z, wo das Material beginnt (das Rohteil)
    sicher: float  # z für den Eilgang über allem
    aufmass_boden: float = 0.0  # bleibt auf dem Grund einer Sackbohrung
    schlichten: bool = True  # danach die Wand bei Radius in einem Zug
    gleichlauf: bool = True
    tiefer: float = TIEFER  # nur bei durchgehenden Bohrungen
    schneidenlaenge: float = 0.0  # 0: unbekannt – das Schlichten in einem Zug
    sicherheit: float = vb.SICHERHEIT
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad – so steil die Helix
    vorschub: float = 0.0  # mm/min – für die Zeit; 0: 1000
    eintauchen: float = 0.0


@dataclass
class Bohrbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    bohrungen: int
    lagen: int  # über alle Bohrungen
    umlaeufe: float  # Umläufe der Helix, über alle Bohrungen
    z_min: float
    laenge: float  # mm im Vorschub
    zeit: float  # Minuten (bahn.zeit)


def bohrungen(form, namen=None):
    """[Bohrung] – die senkrechten Zylinderflächen des Teils (nur `namen`, wenn gegeben), deren
    Material außen liegt, ganz herum."""
    import FreeCAD
    import Part

    ergebnis = []
    for nummer, flaeche in ft.mit_namen(form, namen):
        name = f"Face{nummer + 1}"
        flaeche_ = flaeche.Surface
        if not isinstance(flaeche_, Part.Cylinder):
            continue
        achse = flaeche_.Axis
        if abs(abs(achse.z) - 1.0) > 1e-6:
            continue
        u0, u1, v0, v1 = flaeche.ParameterRange
        if u1 - u0 < 2 * math.pi - 1e-6:
            continue  # nur ein Stück eines Zylinders: keine ganze Bohrung
        mitte = flaeche_.Center
        punkt = flaeche.valueAt((u0 + u1) / 2, (v0 + v1) / 2)
        normale = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        zur_achse = FreeCAD.Vector(mitte.x - punkt.x, mitte.y - punkt.y, 0)
        if normale.x * zur_achse.x + normale.y * zur_achse.y <= 0:
            continue  # die Normale zeigt von der Achse weg: ein Zapfen, keine Bohrung
        bb = flaeche.BoundBox
        durch, spitze = _unter_gemerkt(form, name, flaeche, mitte, bb)
        ergebnis.append(
            Bohrung(
                name,
                (float(mitte.x), float(mitte.y)),
                float(flaeche_.Radius),
                float(bb.ZMax),
                float(bb.ZMin),
                durch,
                spitze,
            )
        )
    return ergebnis


def _unter_gemerkt(form, name, flaeche, mitte, bb):
    """(durch, Spitze) der Bohrung `flaeche` – _boden_unter und _spitze_unter, gemerkt je Form und
    Fläche (mit ihrer Lage, falls zwei Formen dieselbe Fläche anders nennen)."""
    radius = float(flaeche.Surface.Radius)
    try:
        kennung = form.hashCode()
    except Exception:  # noqa: BLE001 – keine Form, die sich merken lässt
        kennung = None
    eintrag = _UNTER.get(kennung) if kennung is not None else None
    if eintrag is not None and eintrag[0].isSame(form):
        _UNTER.move_to_end(kennung)
    elif kennung is not None:
        eintrag = (form, {})
        _UNTER[kennung] = eintrag
        while len(_UNTER) > UNTER_FORMEN:
            _UNTER.popitem(last=False)
    schluessel = (name, tuple(round(float(w), 6) for w in (mitte.x, mitte.y, radius, bb.ZMin)))
    if eintrag is not None and schluessel in eintrag[1]:
        return eintrag[1][schluessel]
    durch = not _boden_unter(form, mitte, radius, bb.ZMin)
    ergebnis = (bool(durch), 0.0 if durch else _spitze_unter(form, flaeche, mitte, bb.ZMin))
    if eintrag is not None:
        eintrag[1][schluessel] = ergebnis
    return ergebnis


def _spitze_unter(form, flaeche, mitte, z_unten):
    """Der Winkel (Grad) des Kegels, der unten an die Wand schließt und nach unten spitz
    zuläuft – die Spitze eines Bohrers, wie FreeCADs Bohrung sie zeichnet (118°); 0, wenn der
    Grund eben ist oder etwas anderes."""
    import Part

    for kante in flaeche.Edges:
        if kante.BoundBox.ZMax > z_unten + 1e-6:
            continue
        for nachbar in form.ancestorsOfType(kante, Part.Face):
            kegel = nachbar.Surface
            if nachbar.isSame(flaeche) or not isinstance(kegel, Part.Cone):
                continue
            if abs(abs(kegel.Axis.z) - 1.0) > 1e-6:
                continue
            spitze = kegel.Apex
            if math.hypot(spitze.x - mitte.x, spitze.y - mitte.y) > 1e-4 or spitze.z >= z_unten:
                continue
            return round(2 * abs(math.degrees(kegel.SemiAngle)), 6)
    return 0.0


def _boden_unter(form, mitte, radius, z_unten):
    """Steht unter dem Grund der Wand Material – rundum knapp innerhalb der Wand geprüft, nicht
    auf der Achse: Unter einer Senkung für eine Zylinderkopfschraube liegt auf der Achse das
    Durchgangsloch, aber am Rand ihr Boden; unter einer gebohrten Sackbohrung auf der Achse die
    Luft ihrer Spitze, am Rand das Material."""
    import FreeCAD

    r = max(radius - min(0.02, 0.25 * radius), 0.0)
    for i in range(8):
        winkel = i * math.pi / 4
        punkt = FreeCAD.Vector(
            mitte.x + r * math.cos(winkel), mitte.y + r * math.sin(winkel), z_unten - 0.05
        )
        if form.isInside(punkt, 1e-6, True):
            return True
    return False


def ist_bohrung(form, name):
    """Ist die Fläche `name` eine Bohrung (bohrungen())?"""
    return bool(bohrungen(form, [name]))


# mm – bis zu diesem Durchmesser meint ein angeklickter Boden das Loch (bohrung_ueber_boden);
# eine größere runde Tasche räumt das Räumen wie bisher.
BODEN_LOCH_BIS = 40.0


def bohrung_ueber_boden(form, name):
    """Der Name der Bohrung („Face7“) bis Ø BODEN_LOCH_BIS, deren ebener Boden die Fläche `name`
    ist – ihr Rand nur Kreisbögen, an denen eine Bohrung (bohrungen()) anschließt; None sonst. Wer
    den Boden eines Lochs anklickt, meint das Loch (Manuel, 2026-10-10: „Ich will nur dass Loch
    da fräsen“) – und das Räumen passt in ein Loch wenig größer als der Fräser nicht hinein.
    Ein innerer Rand muss ebenfalls an eine Bohrung grenzen (die Senkung über einer kleineren
    Bohrung); steht im Boden ein Zapfen, ist es eine Tasche – die Helix nähme ihn weg. Je Form
    und Name gemerkt (der Assistent fragt bei jeder Änderung)."""
    try:
        schluessel = (form.hashCode(), name)
    except Exception:  # noqa: BLE001
        return None
    gemerkt = _BODEN_MERK.get(schluessel)
    # Mit der Form gemerkt: Sie bleibt so am Leben, ihr Speicher wird nicht für eine andere
    # wiederverwendet (der hashCode allein wäre dann gleich).
    if gemerkt is not None and gemerkt[0].isSame(form):
        return gemerkt[1]
    if len(_BODEN_MERK) > 256:
        _BODEN_MERK.clear()
    ergebnis = _bohrung_ueber_boden(form, name)
    _BODEN_MERK[schluessel] = (form, ergebnis)
    return ergebnis


_BODEN_MERK = {}


def _bohrung_ueber_boden(form, name):
    import Part

    try:
        flaeche = form.getElement(name)
        aussen = flaeche.OuterWire
        kanten = aussen.Edges
    except Exception:  # noqa: BLE001 – kein Name einer Fläche, keine Fläche mit Rand
        return None
    if not isinstance(flaeche.Surface, Part.Plane) or not kanten:
        return None
    if not all(isinstance(k.Curve, Part.Circle) for k in kanten):
        return None

    def name_von(nachbar):
        for nummer, f in enumerate(form.Faces):
            if f.isSame(nachbar):
                return f"Face{nummer + 1}"
        return None

    def bohrung_an(kante):
        """(grenzt ein Zylinder an, die Bohrung (bohrungen()) dort oder None)."""
        for nachbar in form.ancestorsOfType(kante, Part.Face):
            if nachbar.isSame(flaeche) or not isinstance(nachbar.Surface, Part.Cylinder):
                continue
            nachbar_name = name_von(nachbar)
            gefunden = bohrungen(form, [nachbar_name]) if nachbar_name else []
            return True, gefunden[0] if gefunden else None
        return False, None

    for innen in flaeche.Wires:
        if innen.isSame(aussen):
            continue
        if not all(bohrung_an(k)[1] is not None for k in innen.Edges):
            return None  # ein Zapfen im Boden (oder sonst eine Insel): eine Tasche
    for kante in kanten:
        zylinder, gefunden = bohrung_an(kante)
        if zylinder:
            if gefunden is not None and 2 * gefunden.radius <= BODEN_LOCH_BIS + 1e-9:
                return gefunden.name
            return None
    return None


# --- Bahn ---------------------------------------------------------------------------------


def _bogen_punkte(punkte, mitte, radius, von_winkel, bis_winkel, z_von, z_bis, uhr):
    """Bögen um `mitte` von `von_winkel` nach `bis_winkel` (rad, in Fahrtrichtung), z linear von
    z_von nach z_bis, in Stücken von höchstens einem Viertel. Gibt die Länge zurück."""
    weit = abs(bis_winkel - von_winkel)
    anzahl = max(1, int(math.ceil(weit / (math.pi / 2) - 1e-9)))
    laenge = 0.0
    for i in range(1, anzahl + 1):
        t = i / anzahl
        w = von_winkel + (bis_winkel - von_winkel) * t
        punkt = bn.Punkt(
            False,
            mitte[0] + radius * math.cos(w),
            mitte[1] + radius * math.sin(w),
            z_von + (z_bis - z_von) * t,
            bogen=(mitte[0], mitte[1], uhr),
        )
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _helix(punkte, mitte, radius, winkel, z_von, z_bis, steigung, uhr):
    """Die Helix um `mitte` mit `radius` ab `winkel`, von z_von hinab auf z_bis, je Umlauf um
    `steigung` tiefer; unten noch einmal ganz herum. Gibt (Länge, Winkel am Ende, Umläufe)."""
    richtung = -1.0 if uhr else 1.0
    tiefe = z_von - z_bis
    umlaeufe = max(tiefe / steigung, 0.0) if steigung > 0 else 0.0
    laenge = 0.0
    if radius <= GLEICH:
        punkt = bn.Punkt(False, mitte[0], mitte[1], z_bis, True)
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
        return laenge, winkel, 0.0
    if umlaeufe > 0:
        ende = winkel + richtung * 2 * math.pi * umlaeufe
        laenge += _bogen_punkte(punkte, mitte, radius, winkel, ende, z_von, z_bis, uhr)
        winkel = ende
    laenge += _bogen_punkte(
        punkte, mitte, radius, winkel, winkel + richtung * 2 * math.pi, z_bis, z_bis, uhr
    )
    return laenge, winkel + richtung * 2 * math.pi, umlaeufe


def _auf_kreis(mitte, radius, winkel):
    return (mitte[0] + radius * math.cos(winkel), mitte[1] + radius * math.sin(winkel))


def _halbkreis(punkte, von, nach, z, uhr):
    """Ein Halbkreis von `von` nach `nach` (der Durchmesser) auf z. Gibt die Länge zurück."""
    mx, my = (von[0] + nach[0]) / 2, (von[1] + nach[1]) / 2
    punkt = bn.Punkt(False, nach[0], nach[1], z, bogen=(mx, my, uhr))
    laenge = bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    return laenge


def _bohrung(punkte, b, w, r):
    """Eine Bohrung: Helix, Ringe, Schlichten. Gibt (Länge, Lagen, Umläufe, z_min)."""
    uhr = not w.gleichlauf  # Gleichlauf: das Material (außen) rechts – gegen den Uhrzeigersinn
    aufmass = max(w.aufmass, 0.0) if w.schlichten else 0.0
    r_aussen = b.radius - r - aufmass  # die Mitte des Fräsers beim letzten Schruppring
    if r_aussen < -GLEICH:
        raise ValueError(
            tr("bo.fehler.zu_klein", durchmesser=einheiten.text(2 * b.radius, einheiten.LAENGE))
        )
    r_aussen = max(r_aussen, 0.0)
    z_grund = b.z_unten - max(w.tiefer, 0.0) if b.durch else b.z_unten + max(w.aufmass_boden, 0.0)
    oben = w.oben
    if oben <= z_grund + GLEICH:
        return 0.0, 0, 0.0, math.inf
    r_helix = min(r_aussen, KERN_ANTEIL * r)
    steigung = max(
        2 * math.pi * r_helix * math.tan(math.radians(max(w.eintauchwinkel, 0.1))), MIN_STEIGUNG
    )
    # Braucht der Kern Ringe nach außen, dann in Lagen (ap); sonst in einem Zug hinab.
    ringe = r_aussen > r_helix + GLEICH
    zustellung = w.zustellung
    if w.schneidenlaenge > 0:
        zustellung = min(zustellung, w.schneidenlaenge)
    if ringe:
        anzahl = max(1, int(math.ceil((oben - z_grund - 1e-6) / max(zustellung, GLEICH))))
    else:
        anzahl = 1
    lagen = [oben - (oben - z_grund) * (i + 1) / anzahl for i in range(anzahl)]
    winkel = 0.0
    start = _auf_kreis(b.mitte, r_helix, winkel)
    punkte.append(bn.Punkt(True, start[0], start[1], w.sicher))
    knapp = min(w.sicher, oben + w.sicherheit)
    punkte.append(bn.Punkt(True, start[0], start[1], knapp))
    punkte.append(bn.Punkt(False, start[0], start[1], oben, True))
    laenge = 0.0
    umlaeufe = 0.0
    vorige = oben
    for lage in lagen:
        if (punkte[-1].x - start[0]) ** 2 + (punkte[-1].y - start[1]) ** 2 > GLEICH:
            punkt = bn.Punkt(False, start[0], start[1], vorige)
            laenge += bn.weg(punkte[-1], punkt)
            punkte.append(punkt)
            winkel = 0.0
        stueck, winkel, n = _helix(punkte, b.mitte, r_helix, winkel, vorige, lage, steigung, uhr)
        laenge += stueck
        umlaeufe += n
        if ringe:
            # Nach außen: je Ring um ae weiter, ein Halbkreis hinüber, dann ganz herum.
            radius = r_helix
            richtung = -1.0 if uhr else 1.0
            while radius < r_aussen - GLEICH:
                neu = min(radius + w.zeilenabstand, r_aussen)
                hier = _auf_kreis(b.mitte, radius, winkel)
                ziel = _auf_kreis(b.mitte, neu, winkel + math.pi)
                # Der Halbkreis von hier zum Ziel gegenüber bleibt im neuen Ring (sein weitester
                # Punkt liegt genau auf ihm) – der Eingriff wächst über einen halben Umlauf an.
                laenge += _halbkreis(punkte, hier, ziel, lage, uhr)
                winkel = winkel + math.pi
                laenge += _bogen_punkte(
                    punkte, b.mitte, neu, winkel, winkel + richtung * 2 * math.pi, lage, lage, uhr
                )
                winkel += richtung * 2 * math.pi
                radius = neu
        vorige = lage
    z_min = vorige
    if w.schlichten and b.radius - r > GLEICH:
        laenge += _schlichten(punkte, b, w, r, oben, z_grund, uhr)
        z_min = min(z_min, z_grund)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    return laenge, len(lagen), umlaeufe, z_min


def _schlichten(punkte, b, w, r, oben, z_grund, uhr):
    """Die Wand bei Radius: aus der Mitte im Halbkreis hinein, einmal ganz herum, im Halbkreis
    zurück in die Mitte – in Zügen von höchstens der Schneidenlänge. Gibt die Länge zurück."""
    r_f = b.radius - r
    hoehe = min(oben, b.z_oben) - z_grund
    anzahl = 1
    if 0 < w.schneidenlaenge < hoehe - GLEICH:
        anzahl = max(1, int(math.ceil(hoehe / w.schneidenlaenge - 1e-9)))
    laenge = 0.0
    richtung = -1.0 if uhr else 1.0
    for i in range(1, anzahl + 1):
        z = min(oben, b.z_oben) - hoehe * i / anzahl
        mitte = b.mitte
        punkt = bn.Punkt(False, mitte[0], mitte[1], z)
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
        rand = _auf_kreis(mitte, r_f, 0.0)
        laenge += _halbkreis(punkte, mitte, rand, z, uhr)
        laenge += _bogen_punkte(punkte, mitte, r_f, 0.0, richtung * 2 * math.pi, z, z, uhr)
        laenge += _halbkreis(punkte, rand, mitte, z, uhr)
    return laenge


def planen(werte, liste):
    """Die Bahn „Bohrung fräsen“ (Bohrbahn) für die Bohrungen `liste` ([Bohrung]) mit den
    Werten `werte`. ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    r = float(w.fraeser_radius)
    if r <= 0:
        raise ValueError(tr("bo.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("bo.fehler.werte"))
    if not liste:
        raise ValueError(tr("bo.fehler.keine"))
    # Die kürzeste Reihenfolge: immer zur nächsten.
    offen = list(liste)
    folge = []
    ort = (0.0, 0.0) if not offen else offen[0].mitte
    while offen:
        naechste = min(offen, key=lambda b: math.hypot(b.mitte[0] - ort[0], b.mitte[1] - ort[1]))
        offen.remove(naechste)
        folge.append(naechste)
        ort = naechste.mitte
    punkte = []
    laenge = umlaeufe = 0.0
    lagen = 0
    z_min = math.inf
    gefraest = 0
    for b in folge:
        stueck, n_lagen, n_um, z = _bohrung(punkte, b, w, r)
        if n_lagen:
            gefraest += 1
        laenge += stueck
        lagen += n_lagen
        umlaeufe += n_um
        z_min = min(z_min, z)
    if not gefraest:
        raise ValueError(tr("bo.fehler.nichts"))
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    return Bohrbahn(punkte, gefraest, lagen, umlaeufe, z_min, laenge, zeit)
