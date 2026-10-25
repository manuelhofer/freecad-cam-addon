# SPDX-License-Identifier: LGPL-2.1-or-later
"""Empfehlungen, wenn Halter oder Schaft anstoßen (Manuel, 2026-10-25, an seiner tiefen Tasche:
„hey mit dem aktuellen magazin sehe ich keine changse das komplett zu bearbeiten .. aber wenn du
diese aufnahme / halter nimmst und diesen fräser soweit ausspannst .. dann klapts“ – „das muss mit
rein“).

Stößt unter dem Rand (hinterschnitt_bahn) etwas an und reicht Ausspannen mit dem Halter des
Werkzeugs nicht, sucht `empfehlen` ein anderes Paar aus Fräser und Halter – auch was nicht im
Magazin steht, auch Halter, die es in der Werkzeugverwaltung noch nicht gibt:

- **Fräser:** der gewählte und die derselben Art und desselben Ø aus der Werkzeugverwaltung, die
  länger sind.
- **Halter:** die geraden der Werkzeugverwaltung an der Aufnahme der Maschine, dazu die
  Normreihen für den Schaft (halter.REIHEN: Schrumpffutter, Hydrodehn, die zwei kleinsten
  ER-Größen, die ihn fassen) in jeder Länge.
- **Je Paar** die kürzeste Auskragung (halbiert zwischen der Schneide und Gesamtlänge − Schaft-Ø,
  wie reichweite.ausspannen_auf), bei der an den Stellen der Prüfung (Bahn.pruefung: die
  anstoßenden und einige freie) eine gekippte Achse frei bleibt (hinterschnitt_bahn.suchen_stueck).
  Die Paare rechnen die Nebenrechner, je eins ein Auftrag.
- **Empfohlen** das Paar mit der kürzesten Länge ab Spindelnase – am steifsten –, bei gleicher
  Länge (auf 5 mm) eines, das es schon gibt, vor einem neuen Halter.

Läuft ohne Oberfläche.
"""

import hashlib
from dataclasses import dataclass, replace

import FreeCAD
import numpy as np

from . import halter as hl
from . import hinterschnitt_bahn as hb

PAARE_HOECHSTENS = 40  # so viele Paare rechnet es höchstens
HALTER_HOECHSTENS = 8  # so viele Halter der Werkzeugverwaltung fragt es
HALBIEREN = 6  # so oft halbiert es die Auskragung
# Je Normreihe nur so viele Längen: die kürzeste, eine mittlere, die längste – an Manuels Tasche
# rechnete es sonst mit allen 30 Paaren und auf einem Nebenrechner „hört garnicht auf“.
LAENGEN_JE_REIHE = 3
GLEICH_LANG = 5.0  # mm: so viel länger darf ein vorhandenes Paar sein und gewinnt doch
ER_GROESSEN = 2  # die so vielen kleinsten ER-Größen, die den Schaft fassen
ERST_AN, ERST_FREI = 20, 10  # so viele Stellen fragt die erste, grobe Runde je Paar
ZWEITE = 2  # so viele der besten Paare rechnet die zweite Runde mit allen Stellen
RESERVE = 2.0  # mm mehr heraus, als die Stellen der Prüfung brauchen (sie sind eine Auswahl)
KEINE = "keine"  # gesucht, nichts gefunden (statt None: nicht gesucht)


@dataclass
class Empfehlung:
    """Ein Paar aus Fräser und Halter, mit dem es überall geht."""

    werkzeug: str  # Kennung in der Werkzeugverwaltung
    werkzeug_text: str  # „T3 Kugelfräser Ø12“
    halter: object  # halter.Halter – aus der Werkzeugverwaltung oder einer Normreihe
    halter_neu: bool  # noch nicht in der Werkzeugverwaltung (eine Normreihe)
    heraus: float  # mm: so weit steht der Fräser aus dem Halter
    laenge: float  # mm ab der Spindelnase
    im_magazin: bool  # der Fräser steht im Magazin der Maschine
    anderes_werkzeug: bool  # nicht der gewählte Fräser
    # Ein Fräser, den es noch nicht gibt (neue_kugel): seine Daten (Werkzeug.als_dict) – einrichten
    # legt ihn in der Werkzeugverwaltung an; None: er steht schon dort.
    werkzeug_neu: dict = None


def _schaft(werkzeug):
    from . import werkzeuge as wz

    return float(wz.schaft_fuer_cam(werkzeug) or werkzeug.durchmesser or 0.0)


def _laengen(art):
    """LAENGEN_JE_REIHE Längen der Reihe: die kürzeste, mittlere, längste."""
    alle = hl.REIHE_LAENGEN[art]
    if len(alle) <= LAENGEN_JE_REIHE:
        return alle
    wahl = np.unique(np.linspace(0, len(alle) - 1, LAENGEN_JE_REIHE).round().astype(int))
    return tuple(alle[i] for i in wahl)


def _normhalter(schaft, aufnahme):
    """[Halter] der Normreihen, die den Schaft `schaft` fassen, an der Aufnahme – je Reihe
    LAENGEN_JE_REIHE Längen."""
    schluessel = []
    for art in (hl.SCHRUMPF, hl.HYDRO):
        if any(abs(g - schaft) < 1e-6 for g in hl.REIHE_GROESSEN[art]):
            groesse = next(g for g in hl.REIHE_GROESSEN[art] if abs(g - schaft) < 1e-6)
            schluessel += [hl.reihe(art, groesse, a) for a in _laengen(art)]
    er = [g for g in hl.REIHE_GROESSEN[hl.ER] if hl.ER_MASSE[g][3] >= schaft - 1e-6]
    for groesse in er[:ER_GROESSEN]:
        schluessel += [hl.reihe(hl.ER, groesse, a) for a in _laengen(hl.ER)]
    return [hl.aus_vorlage(s, aufnahme=aufnahme) for s in schluessel]


def _halter_der_verwaltung(bibliothek, aufnahme, schaft, ohne):
    """Die geraden Halter der Werkzeugverwaltung an der Aufnahme (oder ohne Aufnahme), deren Nase
    weiter ist als der Schaft – ohne den Halter `ohne` (den des Werkzeugs)."""
    ergebnis = []
    for h in getattr(bibliothek, "halter", []):
        if h.gewinkelt or not h.abschnitte or h is ohne:
            continue
        if ohne is not None and h.kennung == getattr(ohne, "kennung", None):
            continue
        if h.aufnahme and aufnahme and h.aufnahme != aufnahme:
            continue
        if h.abschnitte[-1].d_unten <= schaft + 1e-6:
            continue
        ergebnis.append(h)
    return ergebnis[:HALTER_HOECHSTENS]


def _werkzeuge(werkzeug, bibliothek):
    """Der gewählte Fräser und die derselben Art und desselben Ø, die länger sind."""
    ergebnis = [werkzeug]
    for w in getattr(bibliothek, "werkzeuge", []):
        if w.kennung == werkzeug.kennung or w.art != werkzeug.art:
            continue
        if abs(float(w.durchmesser) - float(werkzeug.durchmesser)) > 1e-6:
            continue
        if float(w.gesamtlaenge or 0.0) > float(werkzeug.gesamtlaenge or 0.0) + 1e-6:
            ergebnis.append(w)
    return ergebnis


def paar_stueck(form, toleranz, zelle, mitten, richtungen, masse, halter, radius, von, bis):
    """Die kürzeste Auskragung (mm) zwischen `von` und `bis`, bei der an jeder Stelle (Kugelmitten,
    Richtungen wie hinterschnitt_bahn._richtungen) eine gekippte Achse frei bleibt – None, wenn
    auch `bis` nicht reicht. Auch im Nebenrechner, je Paar ein Auftrag."""
    netz = hb._netz_von(form, toleranz, zelle)
    mitten = np.asarray(mitten, dtype=float).reshape(-1, 3)
    start = np.zeros(len(mitten))

    def geht(heraus):
        koerper = hb.koerper_des_werkzeugs(masse, float(halter.laenge) + heraus, halter)
        teile = hb._koerper(hb.Werte(radius=radius, sicher=0.0, koerper=tuple(koerper)), 1e6)
        kipp = hb.suchen_stueck(netz, mitten, richtungen, start, teile, radius)
        return not np.isnan(kipp[:, 0]).any()

    if bis < von or not geht(bis):
        return None
    if geht(von):
        return float(von)
    unten, oben = float(von), float(bis)
    for _ in range(HALBIEREN):
        mitte = (unten + oben) / 2
        if geht(mitte):
            oben = mitte
        else:
            unten = mitte
    return oben


def empfehlen(form, pruefung, werkzeug, bibliothek, aufnahme="", magazin=None):
    """Empfehlung – das steifste Paar aus Fräser und Halter, mit dem an den Stellen der Prüfung
    (hinterschnitt_bahn.Bahn.pruefung) nichts anstößt; KEINE, wenn keins geht; None ohne Prüfung,
    Fräser oder Werkzeugverwaltung."""
    from . import magazin as mg
    from . import reichweite as rw

    if not pruefung or not pruefung.get("mitten") or werkzeug is None or bibliothek is None:
        return None
    radius = float(pruefung["radius"])
    mitten = np.asarray(pruefung["mitten"], dtype=float).reshape(-1, 3)
    mitte = FreeCAD.Vector(*pruefung["mitte"], 0.0)
    richtungen = hb._richtungen(mitten, np.zeros_like(mitten), mitte)
    jetzt = bibliothek.halter_fuer_pruefung(werkzeug)
    paare = []  # (Werkzeug, Halter, neu)
    for w in _werkzeuge(werkzeug, bibliothek):
        schaft = _schaft(w)
        halter = [(h, False) for h in _halter_der_verwaltung(bibliothek, aufnahme, schaft, None)]
        if w is not werkzeug and jetzt is not None:
            halter.insert(0, (jetzt, False))
        halter += [(h, True) for h in _normhalter(schaft, aufnahme)]
        gesehen = set()
        for h, neu in halter:
            if w is werkzeug and jetzt is not None and h.kennung == jetzt.kennung:
                continue  # das hat die Bahn schon gefragt
            if h.kennung in gesehen:
                continue
            gesehen.add(h.kennung)
            # Der vorgeschlagene Halter (halter.vorschlag) steht nicht in der Werkzeugverwaltung.
            paare.append((w, h, neu or hl.ist_vorschlag(h)))
    paare = paare[:PAARE_HOECHSTENS]
    if not paare:
        return KEINE
    netz_t, netz_z = hb.NETZ_TOLERANZ, radius + 1.0
    grenzen = []
    for w, _h, _neu in paare:
        masse = rw.masse_des_werkzeugs(w)
        von = float(masse.schneide) + 1.0
        gesamt = float(w.gesamtlaenge or masse.gesamt or 0.0)
        grenzen.append((masse, von, gesamt - _schaft(w) if gesamt else von + hb.HALTER_LAENGER))
    # Erst grob (ERST_AN + ERST_FREI Stellen) alle Paare, dann die ZWEITE besten mit allen Stellen.
    an = np.asarray(pruefung.get("an", pruefung["mitten"]), dtype=float).reshape(-1, 3)
    frei = np.asarray(pruefung.get("frei", []), dtype=float).reshape(-1, 3)
    grob = np.concatenate([_auswahl(an, ERST_AN), _auswahl(frei, ERST_FREI)])
    grob_r = hb._richtungen(grob, np.zeros_like(grob), mitte)
    erst = _rechnen(
        form,
        netz_t,
        netz_z,
        [
            (grob, grob_r, m, h, radius, von, bis)
            for (_w, h, _n), (m, von, bis) in zip(paare, grenzen, strict=True)
        ],
    )
    rang = sorted(
        (i for i, s in enumerate(erst) if s is not None),
        key=lambda i: _wertung(paare[i], erst[i]),
    )[:ZWEITE]
    if not rang:
        return KEINE
    zweit = _rechnen(
        form,
        netz_t,
        netz_z,
        [
            (mitten, richtungen, grenzen[i][0], paare[i][1], radius, erst[i], grenzen[i][2])
            for i in rang
        ],
    )
    beste = None
    for i, heraus in zip(rang, zweit, strict=True):
        if heraus is None:
            continue
        heraus = min(float(np.ceil(heraus + RESERVE)), grenzen[i][2])
        wertung = _wertung(paare[i], heraus)
        if beste is None or wertung < beste[0] - 1e-6:
            beste = (wertung, i, heraus)
    if beste is None:
        return KEINE
    _wert, i, heraus = beste
    w, h, neu = paare[i]
    return Empfehlung(
        werkzeug=w.kennung,
        werkzeug_text=f"T{w.nummer} {w.name or w.art}".strip(),
        halter=replace(h),
        halter_neu=neu,
        heraus=heraus,
        laenge=float(h.laenge) + heraus,
        im_magazin=magazin is None or mg.rang(w, magazin) != mg.NICHT_IM_MAGAZIN,
        anderes_werkzeug=w.kennung != werkzeug.kennung,
    )


def _auswahl(feld, anzahl):
    """Bis `anzahl` Zeilen von `feld`, gleichmäßig verteilt."""
    if len(feld) <= anzahl:
        return feld
    return feld[np.unique(np.linspace(0, len(feld) - 1, anzahl).astype(int))]


def _wertung(paar, heraus):
    """Wie gut ein Paar ist: die Länge ab Spindelnase – vorhandene GLEICH_LANG kürzer gezählt."""
    _w, h, neu = paar
    return float(h.laenge) + heraus - (0.0 if neu else GLEICH_LANG)


def _rechnen(form, toleranz, zelle, auftraege):
    """[Auskragung oder None] je Paar – auf den Nebenrechnern, sonst hier."""
    from . import nebenrechner as nr

    try:
        pool = nr.pool()
        if not pool.verfuegbar() or pool.anzahl < 2:
            raise nr.NichtVerfuegbar("hier")
        brep = form.exportBrepToString()
        teil = pool.gemeinsam("hs-teil-" + hashlib.sha1(brep.encode()).hexdigest(), nr.Form(brep))
        laufend = [
            pool.auftrag("empfehlung", "paar_stueck", teil, toleranz, zelle, *a) for a in auftraege
        ]
        return list(pool.warten(laufend, zwischendurch=nr.ereignisse_ohne_eingaben))
    except Exception as fehler:  # noqa: BLE001 – dann rechnet es hier
        if not isinstance(fehler, nr.NichtVerfuegbar):
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Empfehlung auf den Nebenrechnern: {fehler}\n")
        return [paar_stueck(form, toleranz, zelle, *a) for a in auftraege]


# Ein Kugelfräser, den es noch nicht gibt (neue_kugel): die üblichen Ø und Gesamtlängen, die
# Schneide 1,5 · Ø, unter Ø 6 ein Schaft Ø 6 mit Hals.
KUGEL_DURCHMESSER = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0)
KUGEL_LAENGEN = (60.0, 100.0, 150.0)
SCHAFT_KLEINSTER = 6.0


def neue_kugel(form, ecken, vorbild, bibliothek, aufnahme="", magazin=None):
    """Empfehlung mit `werkzeug_neu` – für die Ecken unter dem Rand (hinterschnitt_bahn.Bahn.ecken):
    der größte übliche Kugelfräser, der hineinpasst, in der kürzesten der KUGEL_LAENGEN, mit der
    es geht, im besten Halter (empfehlen). Seine Schnittwerte vom Kugelfräser `vorbild`, fz auf den
    Ø umgerechnet. KEINE, wenn keiner geht; None ohne Ecken."""
    from . import werkzeuge as wz

    if not ecken or not ecken.get("punkte") or vorbild is None or bibliothek is None:
        return None
    d = max((k for k in KUGEL_DURCHMESSER if k <= 2.0 * float(ecken["radius"]) + 1e-6), default=0)
    if d <= 0:
        return KEINE
    probe = wz.Bibliothek.aus_dict(bibliothek.als_dict())  # eine Kopie: nichts eintragen
    neue = []
    for laenge in KUGEL_LAENGEN:
        if laenge < 6.0 * d:
            continue
        w = probe.kopiere(next(v for v in probe.werkzeuge if v.kennung == vorbild.kennung))
        faktor = d / float(vorbild.durchmesser or d)
        w.durchmesser, w.schneidenlaenge, w.gesamtlaenge = d, 1.5 * d, laenge
        w.schaft = max(d, SCHAFT_KLEINSTER) if d < SCHAFT_KLEINSTER else d
        w.hals_d, w.hals_laenge = (d - 0.1, 3.0 * d) if d < SCHAFT_KLEINSTER else (0.0, 0.0)
        w.halter, w.ausspannlaenge, w.laenge_spindelnase = "", 0.0, 0.0
        w.name = f"Kugelfräser Ø{d:g} × {laenge:g} (Vorschlag)"
        for einsaetze in w.schnittwerte.values():
            for e in einsaetze:
                e.fz, e.ae, e.ap = e.fz * faktor, e.ae * faktor, e.ap * faktor
        neue.append(w)
    if not neue:
        return KEINE
    r = d / 2.0
    punkte = np.asarray(ecken["punkte"], dtype=float).reshape(-1, 3)
    normalen = np.asarray(ecken["normalen"], dtype=float).reshape(-1, 3)
    mitten = punkte + normalen * (r + float(ecken.get("aufmass", 0.0)))
    pruefung = {
        "an": [tuple(m) for m in mitten],
        "frei": [],
        "mitten": [tuple(m) for m in mitten],
        "mitte": tuple(ecken["mitte"]),
        "radius": r,
    }
    ergebnis = empfehlen(form, pruefung, neue[0], probe, aufnahme, None)
    if not isinstance(ergebnis, Empfehlung):
        return ergebnis
    gewaehlt = next(w for w in neue if w.kennung == ergebnis.werkzeug)
    ergebnis.werkzeug_neu = gewaehlt.als_dict()
    ergebnis.werkzeug_text = gewaehlt.name
    ergebnis.im_magazin = False
    ergebnis.anderes_werkzeug = True
    return ergebnis


def einrichten(empfehlung, bibliothek):
    """Richtet die Empfehlung in der Werkzeugverwaltung ein: einen neuen Halter (eine Normreihe)
    dazu, beim Fräser (im Magazin an seinem Platz) der Halter und wie weit er heraussteht
    (reichweite.ausspannen_setzen).
    Gibt das Werkzeug zurück – None, wenn es nicht mehr da ist. Speichert nicht."""
    from . import reichweite as rw
    from . import werkzeuge as wz

    werkzeug = next((w for w in bibliothek.werkzeuge if w.kennung == empfehlung.werkzeug), None)
    if werkzeug is None and empfehlung.werkzeug_neu:
        werkzeug = wz.Werkzeug.aus_dict(empfehlung.werkzeug_neu)  # der vorgeschlagene Fräser
        werkzeug.nummer = bibliothek.naechste_nummer()
        bibliothek.werkzeuge.append(werkzeug)
    if werkzeug is None:
        return None
    halter = empfehlung.halter
    if empfehlung.halter_neu:
        vorhanden = next(
            (
                h
                for h in bibliothek.halter
                if h.name == halter.name and h.aufnahme == halter.aufnahme
            ),
            None,
        )
        halter = vorhanden or bibliothek.halter_dazu(hl.Halter.aus_dict(halter.als_dict()))
    # Steht der Fräser im Magazin der Maschine, gilt dort der Halter seines Platzes (W-024).
    magazin = getattr(bibliothek, "magazin_fuer_pruefung", None)
    eintrag = magazin.eintrag_von(werkzeug) if magazin is not None else None
    if eintrag is not None:
        eintrag.halter = halter.kennung
    else:
        werkzeug.halter = halter.kennung
    if werkzeug.laenge_spindelnase:
        werkzeug.laenge_spindelnase = 0.0  # gemessen galt für den alten Halter
    rw.ausspannen_setzen(werkzeug, empfehlung.laenge, empfehlung.heraus, bibliothek)
    return werkzeug
