# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn „Fase“ (W-037): eine gezeichnete Fase, die man angeklickt hat – mit dem Schaftfräser
in Stufen oder mit dem Fasenfräser in einer Runde. Manuel, 2026-10-24 (Frage 1, der
Messspitzenhalter): „A wenns einen gibt … genau wenn sie angeklickt ist und man nur einen
schaftfräser hat dann muss der das in stufen machen ... wenn nicht wird sie nicht gemacht .. wenn
in der werkzeugverwaltung ein fasenfräser ist .. sollte man fragen .. hey willst du den haben ?“

- Fasen (ist_fase()): eben oder ein Kegel mit senkrechter Achse, keine Wand, schräg nach oben
  (die Normale 0,02 < n.z < 0,98), höchstens GROESSE hoch und breit, mit waagerechter Unter- und
  Oberkante – die Spitze einer Bohrung (ein Kegel bis in die Spitze) nicht. Gleich, woran sie anschließt: oben an einer Wand (wie beim Entgraten) oder unten am
  Grund einer Nut (am Messspitzenhalter steigt sie vom Ringgrund hinauf zum Mantel). Fasen
  gleicher Höhe und gleichen Winkels, die aneinander hängen, sind eine Kette (_gruppen).
- Mit dem Schaftfräser in Stufen: je Lage – alle `stufe` mm von der Oberkante der Fase bis zur
  Unterkante – der Schnitt der Fase auf dieser Höhe, um den Radius auf die freie Seite versetzt
  (kontur_bahn._versatz: Ecken außen werden Bögen, innen schneiden sich die Geraden); die Ecke der
  Stirn liegt auf der Fase. Steht darüber noch Material, vorher Lagen am Schnitt der Oberkante, je
  höchstens die Zustellung. Eine geschlossene Kette in einem Zug – von Lage zu Lage ein kleiner
  Schritt hinab, tangential hinein am Anfang und heraus am Ende –, sonst je Lage ein Lauf; im
  Gleichlauf (das Material rechts der Fahrtrichtung). Der Materialstand davor sagt nur, wie hoch
  über der Fase noch Material steht – die Fase selbst fährt sie immer: Sie ist schmaler als sein
  Raster.
- Mit dem Fasenfräser (sein Kegel hat den Winkel der Fase, ±FASE_WINKEL): eine Runde – die Spitze
  auf der Unterkante, die Achse um den halben Durchmesser der Spitze daneben; der Kegel liegt auf
  der Fase. Er muss vom Grund bis über das Material reichen, und über der Fase darf keine Wand
  aufsteigen (der Kegel ginge hinein).
- Die Hüllfläche (kontur_bahn._Huelle): nahe der Fase das Teil ohne die Fasen und ohne die Flächen
  an ihrer Oberkante, die die Stirn genau streift (eine ebene Fläche nach oben, eine Wand, die von
  dort hinab geht), weiter weg nur ohne die Fasen – sie hält die Bahn vor allem anderen an. Unten
  darf die Stirn auf den Grund (die Unterkante der Fase ist das Ziel).

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from collections import OrderedDict
from dataclasses import dataclass, field

import numpy as np

from . import bahn as bn
from . import entgrat_bahn as eb
from . import formteile as ft
from . import hoehenfeld as hf
from . import kontur_bahn as kb
from . import vierachs_bahn as vb
from .sprache import tr

GROESSE = 3.0  # mm – so hoch und so breit höchstens ist eine Fase; größere Schrägen sind 3D
STUFE = 0.05  # mm – so tief je Lage auf der Fase (Manuel: „vorbelegt 0,05“)
ZUSTELLUNG = 1.0  # mm – über der Fase höchstens so tief je Lage, wenn nichts anderes gesagt ist
SCHRITT = kb.SCHRITT  # mm – Raster längs der Bahn und für die Hüllfläche
VORSCHAU_SCHRITT = kb.VORSCHAU_SCHRITT
FASE_WINKEL = eb.FASE_WINKEL  # Grad – so genau muss der Kegel des Fasenfräsers zur Fase passen
MINDEST_ABSTAND = eb.MINDEST_ABSTAND  # mm – so nah höchstens fährt die Achse an der Kante
MATERIAL = 0.05  # mm – so viel muss über einer Lage stehen, damit es als Material zählt
# mm – so weit innerhalb der Fase wird sie geschnitten: Genau auf ihrer Ober- oder Unterkante gibt
# OpenCascade die Kanten des Modells zurück, an Manuels Messspitzenhalter in zwei Bögen an der Naht
# geteilt – daran scheiterte der Versatz, die oberste Lage fehlte.
SCHNITT_INNEN = 1e-4
GLEICH = kb.GLEICH


@dataclass(frozen=True)
class Fase:
    """Eine gezeichnete Fase (_fase())."""

    nummer: int  # die schräge Fläche, 0 …
    z_unten: float
    z_oben: float
    winkel: float  # Grad zur Senkrechten
    oben: tuple  # die Nummern der Flächen an der Oberkante, die die Stirn genau streift

    @property
    def breite(self):
        return (self.z_oben - self.z_unten) * math.tan(math.radians(self.winkel))


@dataclass(frozen=True)
class Fasenwerte:
    """Was die Fase braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form – ein Schaftfräser (ebene Stirn) oder ein Fasenfräser
    sicher: float  # z für den Eilgang über allem
    oben: float  # die Oberkante des Rohteils – so hoch steht ohne Materialstand das Material
    stufe: float = STUFE
    zustellung: float = ZUSTELLUNG
    spitzenwinkel: float = 0.0  # > 0: ein Fasenfräser mit diesem ganzen Winkel – eine Runde
    spitze: float = 0.0  # Ø der Spitze des Fasenfräsers
    einfahrradius: float = None  # der Viertelkreis hinein und heraus; None: der Radius
    sicherheit: float = vb.SICHERHEIT  # so weit über dem Material endet der Eilgang hinab
    gleichlauf: bool = True  # das Material rechts (M3); False: links (M4)


@dataclass
class Fasenbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    fasen: int  # so viele Ketten gefahren
    lagen: int  # so viele Lagen über alle Ketten
    bahnen: int  # Läufe (je mit Ein- und Ausfahren)
    ausgelassen: int  # so viele Ketten nicht: Der Fräser kommt nicht hin
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub
    winkel: tuple = ()  # die Winkel der gefahrenen Fasen (Grad zur Senkrechten)


@dataclass
class _Stand:
    punkte: list = field(default_factory=list)
    fasen: int = 0
    lagen: int = 0
    bahnen: int = 0
    ausgelassen: int = 0
    z_min: float = math.inf
    laenge: float = 0.0
    winkel: set = field(default_factory=set)


# --- Fasen ------------------------------------------------------------------------------------


def _fase(form, nummer, index=None, mit_nachbarn=True):
    """Die Fläche `nummer` als Fase (Fase) – None, wenn sie keine ist. Ohne `mit_nachbarn` bleibt
    `oben` leer (schneller, für ist_fase())."""
    import Part

    flaeche = ft.flaeche(form, nummer)
    s = flaeche.Surface
    if isinstance(s, Part.Cone):
        if abs(abs(s.Axis.z) - 1.0) > 1e-6:
            return None
    elif not isinstance(s, Part.Plane):
        return None
    bb = flaeche.BoundBox
    hoehe = bb.ZMax - bb.ZMin
    if hoehe <= kb.NAH or hoehe > GROESSE + kb.NAH or kb.ist_wand(flaeche):
        return None
    try:
        u0, u1, v0, v1 = flaeche.ParameterRange
        n = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    except Exception:  # OCC: keine Parameter
        return None
    if not 0.02 < n.z < 0.98:
        return None
    winkel = math.degrees(math.asin(min(max(n.z, -1.0), 1.0)))
    if hoehe * math.tan(math.radians(winkel)) > GROESSE + kb.NAH:
        return None
    unten, oben = [], []
    for kante in flaeche.Edges:
        kbb = kante.BoundBox
        if kbb.ZMax - kbb.ZMin > kb.NAH:
            continue  # eine schräge Kante: das Ende der Fase
        if kante.Length <= kb.NAH:
            continue  # die Spitze eines Kegels (die Spitze einer Bohrung): keine Kante
        if abs(kbb.ZMax - bb.ZMin) <= kb.NAH:
            unten.append(kante)
        elif abs(kbb.ZMin - bb.ZMax) <= kb.NAH:
            oben.append(kante)
    if not unten or not oben:
        return None
    if not mit_nachbarn:
        return Fase(nummer, float(bb.ZMin), float(bb.ZMax), float(winkel), ())
    if index is None:
        index = ft.nummern(form)
    gestreift = set()
    for kante in oben:
        for nachbar in form.ancestorsOfType(kante, Part.Face):
            i = index.get(nachbar.hashCode())
            if i is None or i == nummer:
                continue
            f = ft.flaeche(form, i)
            # Eine ebene Fläche nach oben, oder eine Wand, die von der Oberkante hinab geht: Die
            # Stirn fährt genau an ihr entlang. Eine Wand, die aufsteigt, bleibt in der Hüllfläche.
            if eb._nach_oben(f) or (kb.ist_wand(f) and f.BoundBox.ZMax <= bb.ZMax + kb.NAH):
                gestreift.add(i)
    return Fase(nummer, float(bb.ZMin), float(bb.ZMax), float(winkel), tuple(sorted(gestreift)))


_IST_FASE = OrderedDict()  # (Form, Name) → ist_fase(); der Assistent fragt je Fläche oft


def ist_fase(form, name):
    """Ist die Fläche `name` („Face5“) eine Fase?"""
    from . import vierachs_flaechen as vf

    try:
        schluessel = (form.hashCode(), name)
    except Exception:  # noqa: BLE001 – keine Form von FreeCAD: ohne Merken
        schluessel = None
    if schluessel is not None and schluessel in _IST_FASE:
        return _IST_FASE[schluessel]
    ergebnis = any(
        _fase(form, nummer, mit_nachbarn=False) is not None
        for nummer in vf.nummern([name])
        if nummer < ft.anzahl(form)
    )
    if schluessel is not None:
        _IST_FASE[schluessel] = ergebnis
        while len(_IST_FASE) > 4096:
            _IST_FASE.popitem(last=False)
    return ergebnis


def fasen(form, namen):
    """[Fase] – die Fasen unter den Flächen `namen`."""
    from . import vierachs_flaechen as vf

    index = ft.nummern(form)
    ergebnis = []
    for nummer in vf.nummern(namen):
        if nummer < ft.anzahl(form):
            fase = _fase(form, nummer, index)
            if fase is not None:
                ergebnis.append(fase)
    return ergebnis


def _gruppen(fasen_):
    """[[Fase]] – je Höhe und Winkel; die Kette bilden später ihre Schnitte (Part.sortEdges)."""
    gruppen = {}
    for f in fasen_:
        schluessel = (round(f.z_unten, 4), round(f.z_oben, 4), round(f.winkel, 1))
        gruppen.setdefault(schluessel, []).append(f)
    return [gruppen[s] for s in sorted(gruppen, key=lambda s: (-s[1], s[0], s[2]))]


def _schnitte(form, gruppe, z):
    """[kontur_bahn.Kontur] – die Fasen der Gruppe auf der Höhe z geschnitten, zu Ketten
    verbunden; die freie Seite aus der Normalen der Fase an der Mitte der längsten Kante."""
    import FreeCAD
    import Part

    kanten, flaeche_der_kante = [], {}
    for f in gruppe:
        flaeche = ft.flaeche(form, f.nummer)
        try:
            draehte = flaeche.slice(FreeCAD.Vector(0, 0, 1), z)
        except Exception:  # OCC: kein Schnitt
            continue
        for draht in draehte:
            for kante in draht.Edges:
                kanten.append(kante)
                flaeche_der_kante[kb._schluessel(kante)] = flaeche
    ergebnis = []
    for kette in Part.sortEdges(kanten) if kanten else []:
        laengste = max(kette, key=lambda k: k.Length)
        flaeche = flaeche_der_kante.get(kb._schluessel(laengste))
        mitte = laengste.valueAt((laengste.FirstParameter + laengste.LastParameter) / 2)
        try:
            u, v = flaeche.Surface.parameter(mitte)
            n = flaeche.normalAt(u, v)
        except Exception:  # OCC: keine Parameter – die Mitte der Fläche
            u0, u1, v0, v1 = flaeche.ParameterRange
            n = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        laenge = math.hypot(n.x, n.y) or 1.0
        draht = Part.Wire(kette)
        ergebnis.append(
            kb.Kontur(
                draht,
                float(z),
                float(z),
                draht.isClosed(),
                (float(mitte.x), float(mitte.y)),
                (float(n.x / laenge), float(n.y / laenge)),
                (),
            )
        )
    return ergebnis


PASST_HOEHE = 0.02  # mm – so hoch über dem Fuß schneidet fraeser_passt() das Teil
PASST_SPIEL = 0.05  # mm – so viel näher darf die Stirn dort dem Teil kommen (Raster, Sehnen)
PASST_PROBEN = 24  # so viele Stellen je Kette prüft fraeser_passt()
_PASST = OrderedDict()  # (Form, Fasen, Radius) → fraeser_passt()


def fraeser_passt(form, fasen_, radius):
    """Kommt ein Schaftfräser mit `radius` an die Fasen? Am Fuß jeder Fase, um den Radius auf die
    freie Seite versetzt (die Achse der untersten Lage), muss das Teil – knapp über dem Fuß
    geschnitten – überall mindestens den Radius weg sein. Schnell, für die Wahl des Fräsers im
    Assistenten; die Bahn selbst prüft genauer (die Hüllfläche)."""
    import FreeCAD
    import Part

    try:
        schluessel = (form.hashCode(), tuple(f.nummer for f in fasen_), round(float(radius), 4))
    except Exception:  # noqa: BLE001 – keine Form von FreeCAD: ohne Merken
        schluessel = None
    if schluessel is not None and schluessel in _PASST:
        return _PASST[schluessel]
    ergebnis = True
    for gruppe in _gruppen(fasen_):
        z = gruppe[0].z_unten + PASST_HOEHE
        try:
            schnitt = form.slice(FreeCAD.Vector(0, 0, 1), z)
        except Exception:  # noqa: BLE001 – OCC: kein Schnitt, dann nichts im Weg
            schnitt = []
        teil = Part.Compound(schnitt) if schnitt else None
        for kontur in _schnitte(form, gruppe, _schnitthoehen(gruppe[0])[1]):
            versatz = kb._versatz(kontur, radius, 0.01, max(radius / 4, 0.1))
            if versatz is None:
                ergebnis = False
                break
            if teil is None:
                continue
            proben = versatz[1]
            jede = max(1, len(proben.x) // PASST_PROBEN)
            for x, y in zip(proben.x[::jede], proben.y[::jede], strict=True):
                abstand = teil.distToShape(Part.Vertex(FreeCAD.Vector(float(x), float(y), z)))[0]
                if abstand < radius - PASST_SPIEL:
                    ergebnis = False
                    break
            if not ergebnis:
                break
        if not ergebnis:
            break
    if schluessel is not None:
        _PASST[schluessel] = ergebnis
        while len(_PASST) > 256:
            _PASST.popitem(last=False)
    return ergebnis


def netze(form, fasen_, toleranz=hf.TOLERANZ):
    """(netz_nah, netz_fern) für planen(): das Teil ohne die Fasen und ohne die Flächen an ihrer
    Oberkante, die die Stirn streift – und nur ohne die Fasen."""
    schraeg = {f.nummer for f in fasen_}
    nah = schraeg | {i for f in fasen_ for i in f.oben}
    return hf.netze_ohne(
        form, [[f"Face{i + 1}" for i in sorted(nah)], [f"Face{i + 1}" for i in sorted(schraeg)]],
        toleranz,
    )  # fmt: skip


# --- Lagen ------------------------------------------------------------------------------------


def lagen(z_unten, z_oben, z_material, stufe, zustellung):
    """[z] von oben: über der Oberkante der Fase je höchstens `zustellung` (wenn dort noch Material
    steht), dann von der Oberkante bis zur Unterkante je höchstens `stufe`."""
    ergebnis = []
    if z_material > z_oben + MATERIAL:
        n = max(1, int(math.ceil((z_material - z_oben) / max(zustellung, 1e-3) - 1e-9)))
        ergebnis += [z_oben + (z_material - z_oben) * k / n for k in range(n - 1, 0, -1)]
    n = max(1, int(math.ceil((z_oben - z_unten) / max(stufe, 1e-3) - 1e-9)))
    ergebnis += [z_oben - (z_oben - z_unten) * k / n for k in range(n + 1)]
    return ergebnis


def kegel_passt(fase, spitzenwinkel):
    """Hat der Kegel des Fasenfräsers (ganzer Winkel) den Winkel der Fase?"""
    return abs(spitzenwinkel / 2 - fase.winkel) <= FASE_WINKEL


# --- Die Bahn ---------------------------------------------------------------------------------


def planen(form, netz_nah, netz_fern, werte, fasen_, schritt=SCHRITT, stand=None):
    """Die Bahn „Fase“ (Fasenbahn) an den Fasen `fasen_` ([Fase]) des Teils `form` mit den Werten
    `werte`; `netz_nah`/`netz_fern` aus netze(), `stand` der Materialstand davor (oder None).
    ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    if not fasen_:
        raise ValueError(tr("fa.fehler.keine"))
    fasenfraeser = w.spitzenwinkel > 0
    radius = float(w.form.radius)
    if fasenfraeser:
        for f in fasen_:
            if not kegel_passt(f, w.spitzenwinkel):
                raise ValueError(
                    tr(
                        "fa.fehler.winkel",
                        fase=f"{2 * f.winkel:.0f}",
                        fraeser=f"{w.spitzenwinkel:.0f}",
                    )
                )
        tan = math.tan(math.radians(w.spitzenwinkel / 2))
        abstand = max(w.spitze / 2, MINDEST_ABSTAND)
        kegel = (radius - abstand) / tan if tan > 0 else 0.0
    else:
        abstand = radius
        kegel = 0.0
    r_ein = w.einfahrradius if w.einfahrradius and w.einfahrradius > 0 else radius
    toleranz = netz_nah.toleranz
    zugabe = toleranz + vb.RAND
    geformt = w.form.mit_aufmass(toleranz)
    st = _Stand()
    for gruppe in _gruppen(fasen_):
        f0 = gruppe[0]
        z_oben_schnitt, z_unten_schnitt = _schnitthoehen(f0)
        oben_konturen = _schnitte(form, gruppe, z_oben_schnitt)
        unten_konturen = _schnitte(form, gruppe, z_unten_schnitt)
        if not oben_konturen or not unten_konturen:
            st.ausgelassen += 1
            continue
        for kette_oben in oben_konturen:
            mitte = _mitte(kette_oben)
            # Die Fase selbst fährt sie immer: Sie ist schmaler als das Raster des Materialstands
            # (am Messspitzenhalter zeigte er nach der Nut dort nichts mehr – die Fase stand noch).
            z_material = max(_material_oben(kette_oben, abstand + radius, stand, w.oben), f0.z_oben)
            if fasenfraeser:
                if z_material - f0.z_unten > kegel + GLEICH:
                    raise ValueError(tr("fa.fehler.kegel_kurz"))
                stufen = [f0.z_unten]
            else:
                stufen = lagen(f0.z_unten, f0.z_oben, z_material, w.stufe, w.zustellung)
            zuege = []
            for lage in stufen:
                z_schnitt = min(max(lage, z_unten_schnitt), z_oben_schnitt)
                if fasenfraeser:
                    z_schnitt = z_unten_schnitt
                kontur = _naechste(
                    (unten_konturen if abs(z_schnitt - z_unten_schnitt) <= GLEICH else None)
                    or _schnitte(form, gruppe, z_schnitt),
                    mitte,
                )
                if kontur is None:
                    continue
                versatz = kb._versatz(kontur, abstand, toleranz, schritt, w.gleichlauf)
                if versatz is None:
                    continue
                zuege.append((lage, kontur, versatz))
            if not zuege:
                st.ausgelassen += 1
                continue
            huelle = _huelle(
                netz_nah, netz_fern, geformt, zugabe, zuege, abstand, r_ein, schritt, f0
            )
            gefahren = _kette(st, zuege, huelle, abstand, r_ein, f0, z_material, w)
            if gefahren:
                st.fasen += 1
                st.winkel.add(round(f0.winkel, 1))
            else:
                st.ausgelassen += 1
    if st.fasen == 0:
        raise ValueError(tr("fa.fehler.nichts"))
    return Fasenbahn(
        st.punkte,
        st.fasen,
        st.lagen,
        st.bahnen,
        st.ausgelassen,
        st.z_min,
        st.laenge,
        tuple(sorted(st.winkel)),
    )


def _schnitthoehen(fase):
    """(oben, unten): die Höhen, auf denen die Fase für die oberste und unterste Lage geschnitten
    wird – SCHNITT_INNEN innerhalb ihrer Kanten."""
    innen = min(SCHNITT_INNEN, (fase.z_oben - fase.z_unten) / 4)
    return fase.z_oben - innen, fase.z_unten + innen


def _mitte(kontur):
    bb = kontur.draht.BoundBox
    return ((bb.XMin + bb.XMax) / 2, (bb.YMin + bb.YMax) / 2)


def _naechste(konturen, mitte):
    """Die Kontur, deren Mitte `mitte` am nächsten liegt – None ohne."""
    if not konturen:
        return None
    return min(konturen, key=lambda k: math.hypot(_mitte(k)[0] - mitte[0], _mitte(k)[1] - mitte[1]))


def _material_oben(kontur, reichweite, stand, oben):
    """Wie hoch an der Kette noch Material steht – für die Lagen über der Fase: mit Materialstand
    das Höchste, das eine Scheibe um ihre Punkte trifft (zwei Zellen weiter), sonst die Oberkante
    des Rohteils."""
    if stand is None:
        return oben
    import FreeCAD

    draht = kontur.draht.copy()
    draht.translate(FreeCAD.Vector(0, 0, -kontur.z_unten))
    proben = kb._abtasten(kb._segmente(draht, 0.01), max(stand.schritt, 0.25), kontur.geschlossen)
    hoechste = stand.hoechste_um(proben.x, proben.y, reichweite + 2 * stand.schritt)
    return min(oben, hoechste) if hoechste is not None else -math.inf


def _huelle(netz_nah, netz_fern, geformt, zugabe, zuege, abstand, r_ein, schritt, fase):
    """Die Hüllfläche über allen Zügen der Kette – nahe der Fase ohne sie und ihre Nachbarn oben."""
    xs = np.concatenate([p.x for _l, _k, (_s, p) in zuege])
    ys = np.concatenate([p.y for _l, _k, (_s, p) in zuege])
    rand = 2 * r_ein + abstand + float(geformt.radius) + schritt
    _lage, kontur, _v = zuege[-1]
    kette = kb._kette(kontur, netz_nah.toleranz, 2 * schritt)
    return kb._Huelle(
        netz_nah,
        netz_fern,
        geformt,
        zugabe,
        float(xs.min()) - rand,
        float(xs.max()) + rand,
        float(ys.min()) - rand,
        float(ys.max()) + rand,
        schritt,
        kette,
        abstand + fase.breite + float(geformt.radius) + 2 * schritt,
        (),
    )


def _kette(st, zuege, huelle, abstand, r_ein, fase, z_material, w):
    """Die Züge einer Kette von oben nach unten. Geschlossen und überall frei: in einem Zug, von
    Lage zu Lage ein kleiner Schritt hinab; sonst je Lage in Läufen. Gibt zurück, ob gefahren."""
    ziel = fase.z_unten
    knapp = min(w.sicher, max(z_material, fase.z_oben) + w.sicherheit)
    laeufe = []  # je Lage: [(stellen, lage, segmente, proben, kontur)]
    ganz = True
    for lage, kontur, (segmente, proben) in zuege:
        drin = huelle.erlaubt(proben.x, proben.y, lage, ziel)
        if not drin.any():
            continue
        n = len(proben.x)
        if kontur.geschlossen and drin.all():
            laeufe.append([(None, lage, segmente, proben, kontur)])
            continue
        ganz = False
        stuecke = []
        if kontur.geschlossen:
            luecke = int(np.flatnonzero(~drin)[0])
            for von, bis in vb._stuecke(np.roll(drin, -luecke)):
                stuecke.append((np.arange(von, bis + 1) + luecke) % n)
        else:
            for von, bis in vb._stuecke(drin):
                stuecke.append(np.arange(von, bis + 1))
        laeufe.append([(s, lage, segmente, proben, kontur) for s in stuecke if len(s) >= 2])
    if not any(laeufe):
        return False
    if ganz:
        _in_einem_zug(st, [z[0] for z in laeufe], huelle, abstand, r_ein, knapp, ziel, w)
    else:
        for je_lage in laeufe:
            for stellen, lage, segmente, proben, kontur in je_lage:
                if stellen is None:
                    start = kb._startstelle(segmente, proben)
                    stellen = np.arange(start, start + len(proben.x) + 1) % len(proben.x)
                _lauf(
                    st,
                    segmente,
                    proben,
                    stellen,
                    lage,
                    huelle,
                    abstand,
                    r_ein,
                    knapp,
                    ziel,
                    w,
                    kontur,
                )
    st.lagen += len([z for z in laeufe if z])
    return True


def _frei(huelle, lage, ziel, mindest, kontur):
    """Für kontur_bahn._anfahrt: frei, wo die Hüllfläche es erlaubt und die Fase (ihr Schnitt auf
    der Lage) nicht näher kommt als die Bahn."""
    kx, ky = kb._kette(kontur, 0.01, 0.25)

    def frei(qx, qy):
        if not bool(huelle.erlaubt(qx, qy, lage, ziel).all()):
            return False
        return bool((kb._abstand_polylinie(qx, qy, kx, ky, kontur.geschlossen) >= mindest).all())

    return frei


def _hinab(st, start, knapp, lage, w):
    """Eilgang über den Anfang, knapp über das Material, im Vorschub hinab auf die Lage."""
    punkte = st.punkte
    punkte.append(bn.Punkt(True, start[0], start[1], w.sicher))
    if knapp < w.sicher - 1e-9:
        punkte.append(bn.Punkt(True, start[0], start[1], knapp))
    punkte.append(bn.Punkt(False, start[0], start[1], lage, True))
    st.laenge += abs(knapp - lage)


def _in_einem_zug(st, zuege, huelle, abstand, r_ein, knapp, ziel, w):
    """Geschlossene Ketten: tangential hinein auf der obersten Lage, rundum, zur nächsten Lage an
    der nächsten Stelle ein kleiner Schritt hinab, wieder rundum – am Ende tangential heraus."""
    punkte = st.punkte
    mindest = abstand - kb.WAND_SPIEL
    erster = True
    for _stellen, lage, segmente, proben, kontur in zuege:
        n = len(proben.x)
        if erster:
            start = kb._startstelle(segmente, proben)
        else:
            vorher = punkte[-1]
            start = int(np.argmin(np.hypot(proben.x - vorher.x, proben.y - vorher.y)))
        stellen = np.arange(start, start + n + 1) % n
        p0 = (float(proben.x[start]), float(proben.y[start]))
        if erster:
            t0 = kb._einheit(proben.x[(start + 1) % n] - p0[0], proben.y[(start + 1) % n] - p0[1])
            frei = _frei(huelle, lage, ziel, mindest, kontur)
            ein = kb._anfahrt(p0, t0, r_ein, r_ein, frei, hinein=True, frei_rechts=not w.gleichlauf)
            _hinab(st, ein.aussen if ein is not None else p0, knapp, lage, w)
            if ein is not None:
                st.laenge += kb._anfahrt_punkte(punkte, ein, lage, hinein=True)
            erster = False
        else:
            schritt = bn.Punkt(False, p0[0], p0[1], lage)
            st.laenge += bn.weg(punkte[-1], schritt)
            punkte.append(schritt)
        st.laenge += kb._bahnpunkte(punkte, segmente, proben, stellen, lage, False, 1.0, abstand)
        st.z_min = min(st.z_min, lage)
    _stellen, lage, segmente, proben, kontur = zuege[-1]
    letzter = punkte[-1]
    vorletzter = next(
        (p for p in reversed(punkte[:-1]) if math.hypot(p.x - letzter.x, p.y - letzter.y) > 1e-6),
        None,
    )
    if vorletzter is not None:
        # Die Richtung am Ende: die letzte Strecke, bei einem Bogen die Tangente der Proben.
        i = int(np.argmin(np.hypot(proben.x - letzter.x, proben.y - letzter.y)))
        n = len(proben.x)
        t1 = kb._einheit(proben.x[i] - proben.x[(i - 1) % n], proben.y[i] - proben.y[(i - 1) % n])
        frei = _frei(huelle, lage, ziel, mindest, kontur)
        aus = kb._anfahrt(
            (letzter.x, letzter.y),
            t1,
            r_ein,
            r_ein,
            frei,
            hinein=False,
            frei_rechts=not w.gleichlauf,
        )
        if aus is not None:
            st.laenge += kb._anfahrt_punkte(punkte, aus, lage, hinein=False)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    st.bahnen += 1


def _lauf(st, segmente, proben, stellen, lage, huelle, abstand, r_ein, knapp, ziel, w, kontur):
    """Ein Lauf auf einer Lage: Eilgang über den Anfang, hinab neben der Fase, tangential hinein,
    entlang, tangential heraus, hinauf."""
    x, y = proben.x[stellen], proben.y[stellen]
    p0 = (float(x[0]), float(y[0]))
    p1 = (float(x[-1]), float(y[-1]))
    t0 = kb._einheit(x[1] - x[0], y[1] - y[0])
    t1 = kb._einheit(x[-1] - x[-2], y[-1] - y[-2])
    frei = _frei(huelle, lage, ziel, abstand - kb.WAND_SPIEL, kontur)
    ein = kb._anfahrt(p0, t0, r_ein, r_ein, frei, hinein=True, frei_rechts=not w.gleichlauf)
    aus = kb._anfahrt(p1, t1, r_ein, r_ein, frei, hinein=False, frei_rechts=not w.gleichlauf)
    _hinab(st, ein.aussen if ein is not None else p0, knapp, lage, w)
    punkte = st.punkte
    if ein is not None:
        st.laenge += kb._anfahrt_punkte(punkte, ein, lage, hinein=True)
    st.laenge += kb._bahnpunkte(punkte, segmente, proben, stellen, lage, False, 1.0, abstand)
    if aus is not None:
        st.laenge += kb._anfahrt_punkte(punkte, aus, lage, hinein=False)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    st.bahnen += 1
    st.z_min = min(st.z_min, lage)
