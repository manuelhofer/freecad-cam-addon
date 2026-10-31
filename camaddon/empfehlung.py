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
  ER-Größen, die ihn fassen) in jeder Länge, und aus dem Katalog der Hersteller (halter_katalog)
  je Längenbereich der schlankste, der genau diesen Schaft spannt – etwa ein 3°-Schrumpffutter,
  vorn Ø 18 statt 24.
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
KATALOG_BEREICHE = 3  # so viele Längenbereiche des Katalogs, je der schlankste Halter
SCHLANK_VORN = 50.0  # mm: über so viel vorn an der Nase zählt, wie schlank ein Halter ist
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


def _katalog_halter(schaft, aufnahme):
    """[Halter] aus dem Katalog der Hersteller an der Aufnahme, die genau den Schaft spannen (keine
    Spannzangenfutter – die Normreihen haben ER schon): nach der Länge in KATALOG_BEREICHE
    Bereiche geteilt, je Bereich der schlankste (_schlankheit), bei gleicher der kürzere."""
    if not aufnahme or schaft <= 0:
        return []
    schluessel = (round(schaft, 3), aufnahme)
    if schluessel not in _KATALOG:
        from . import halter_katalog as hk

        kandidaten = []
        for reihe in hk.katalog_reihen():
            if reihe.aufnahme != aufnahme or reihe.art == hk.SPANNZANGE:
                continue
            for groesse in reihe.groessen:
                if abs(groesse["masse"].get("d_spann", 0.0) - schaft) < 1e-6:
                    kandidaten.append((reihe, groesse))
        halter = [hk.aus_katalog(r, g) for r, g in kandidaten]
        halter = [h for h in halter if h.abschnitte and h.laenge > 0]
        halter.sort(key=lambda h: h.laenge)
        wahl = []
        bereiche = min(KATALOG_BEREICHE, len(halter))
        for teil in np.array_split(np.arange(len(halter)), bereiche) if bereiche else []:
            if len(teil):
                wahl.append(
                    min((halter[i] for i in teil), key=lambda h: (_schlankheit(h), h.laenge))
                )
        _KATALOG[schluessel] = wahl
    return [replace(h) for h in _KATALOG[schluessel]]


_KATALOG = {}  # (Schaft, Aufnahme) → [Halter]


def _schlankheit(halter):
    """Der größte Ø (mm) auf den vorderen SCHLANK_VORN mm des Halters – je kleiner, desto tiefer
    kommt er in eine Tasche."""
    ende = halter.laenge
    stellen = np.linspace(max(0.0, ende - SCHLANK_VORN), ende, 11)
    return 2.0 * max(halter.radius_bei(float(a)) for a in stellen)


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
        if h.abschnitte[-1].d_unten <= schaft + 1e-6 or not _fasst(h, schaft):
            continue
        ergebnis.append(h)
    return ergebnis[:HALTER_HOECHSTENS]


def _fasst(halter, schaft):
    """Kann der Halter den Schaft (Ø mm) spannen – aus dem Katalog genau den, den er spannt
    (Halter.spann_d); sonst soweit sein Name es sagt: „ER16“ bis zum größten Schaft der Größe
    (halter.ER_MASSE), „Schrumpffutter/Hydrodehn/Weldon Ø12“ genau den; sonst (ein eigener Name)
    ja."""
    import re

    if getattr(halter, "spann_d", 0.0):
        return abs(float(halter.spann_d) - schaft) < 1e-6

    name = f"{halter.name} {halter.bezeichnung}"
    er = re.search(r"\bER\s?(\d+)\b", name)
    if er and f"ER{er.group(1)}" in hl.ER_MASSE:
        return hl.ER_MASSE[f"ER{er.group(1)}"][3] >= schaft - 1e-6
    d = re.search(r"(Schrumpf|Hydro|Weldon|Flächenspann)\w*\s+Ø\s?(\d+(?:[.,]\d+)?)", name)
    if d:
        return abs(float(d.group(2).replace(",", ".")) - schaft) < 1e-6
    return True


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


def _paare(werkzeug, bibliothek, aufnahme):
    """[(Werkzeug, Halter, neu)] – die Fräser (_werkzeuge) je mit den Haltern der Werkzeugverwaltung,
    der Normreihen und des Katalogs für ihren Schaft; der gewählte Fräser ohne seinen jetzigen
    Halter (den hat die Bahn schon gefragt), ein längerer auch mit ihm. Höchstens
    PAARE_HOECHSTENS."""
    jetzt = bibliothek.halter_fuer_pruefung(werkzeug)
    paare = []
    for w in _werkzeuge(werkzeug, bibliothek):
        schaft = _schaft(w)
        halter = [(h, False) for h in _halter_der_verwaltung(bibliothek, aufnahme, schaft, None)]
        if w is not werkzeug and jetzt is not None:
            halter.insert(0, (jetzt, False))
        halter += [(h, True) for h in _normhalter(schaft, aufnahme)]
        halter += [(h, True) for h in _katalog_halter(schaft, aufnahme)]
        gesehen = set()
        for h, neu in halter:
            if w is werkzeug and jetzt is not None and h.kennung == jetzt.kennung:
                continue
            if h.kennung in gesehen:
                continue
            gesehen.add(h.kennung)
            # Der vorgeschlagene Halter (halter.vorschlag) steht nicht in der Werkzeugverwaltung.
            paare.append((w, h, neu or hl.ist_vorschlag(h)))
    return paare[:PAARE_HOECHSTENS]


def _grenzen(w):
    """(Maße, kürzeste, längste Auskragung) eines Fräsers: über die Schneide hinaus bis zur
    Gesamtlänge − Schaft-Ø (wie reichweite.ausspannen_auf)."""
    from . import reichweite as rw

    masse = rw.masse_des_werkzeugs(w)
    von = float(masse.schneide) + 1.0
    gesamt = float(w.gesamtlaenge or masse.gesamt or 0.0)
    return masse, von, (gesamt - _schaft(w) if gesamt else von + hb.HALTER_LAENGER)


def _empfehlung(paar, heraus, werkzeug, magazin):
    """Die Empfehlung für ein Paar mit der Auskragung `heraus`."""
    from . import magazin as mg

    w, h, neu = paar
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


def empfehlen(form, pruefung, werkzeug, bibliothek, aufnahme="", magazin=None):
    """Empfehlung – das steifste Paar aus Fräser und Halter, mit dem an den Stellen der Prüfung
    (hinterschnitt_bahn.Bahn.pruefung) nichts anstößt; KEINE, wenn keins geht; None ohne Prüfung,
    Fräser oder Werkzeugverwaltung."""
    if not pruefung or not pruefung.get("mitten") or werkzeug is None or bibliothek is None:
        return None
    radius = float(pruefung["radius"])
    mitten = np.asarray(pruefung["mitten"], dtype=float).reshape(-1, 3)
    mitte = FreeCAD.Vector(*pruefung["mitte"], 0.0)
    richtungen = hb._richtungen(mitten, np.zeros_like(mitten), mitte)
    paare = _paare(werkzeug, bibliothek, aufnahme)
    if not paare:
        return KEINE
    netz = (hb.NETZ_TOLERANZ, radius + 1.0)
    grenzen = [_grenzen(w) for w, _h, _n in paare]
    # Erst grob (ERST_AN + ERST_FREI Stellen) alle Paare, dann die ZWEITE besten mit allen Stellen.
    an = np.asarray(pruefung.get("an", pruefung["mitten"]), dtype=float).reshape(-1, 3)
    frei = np.asarray(pruefung.get("frei", []), dtype=float).reshape(-1, 3)
    grob = np.concatenate([_auswahl(an, ERST_AN), _auswahl(frei, ERST_FREI)])
    grob_r = hb._richtungen(grob, np.zeros_like(grob), mitte)
    erst = _rechnen(
        form,
        "paar_stueck",
        [
            (*netz, grob, grob_r, m, h, radius, von, bis)
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
        "paar_stueck",
        [
            (*netz, mitten, richtungen, grenzen[i][0], paare[i][1], radius, erst[i], grenzen[i][2])
            for i in rang
        ],
    )
    return _beste(paare, rang, zweit, grenzen, werkzeug, magazin)


def _beste(paare, rang, auskragungen, grenzen, werkzeug, magazin):
    """Die Empfehlung für das beste der Paare `rang` (je die Auskragung, None: geht nicht) – mit
    RESERVE, höchstens bis zur längsten; KEINE ohne."""
    beste = None
    for i, heraus in zip(rang, auskragungen, strict=True):
        if heraus is None:
            continue
        heraus = min(float(np.ceil(heraus + RESERVE)), grenzen[i][2])
        wertung = _wertung(paare[i], heraus)
        if beste is None or wertung < beste[0] - 1e-6:
            beste = (wertung, i, heraus)
    if beste is None:
        return KEINE
    _wert, i, heraus = beste
    return _empfehlung(paare[i], heraus, werkzeug, magazin)


def flanke_paar_stueck(form, spitzen, achsen, masse, halter, radius, von, bis):
    """Die Auskragung (mm), ab der an den Stellen der Flanke (Spitzen und Achsen, fest) nichts
    anstößt (flanke_bahn.halter_an_stellen: die Körper dicker als die Schneide, wie „Kollision
    prüfen“ sie sieht) – None, wenn es erst weiter als `bis` ginge. Auch im Nebenrechner."""
    from . import flanke_bahn as fb
    from . import kollision as kb

    laenge = float(halter.laenge) + von
    kapseln = kb.werkzeugkapseln(masse, laenge, halter)
    koerper = [
        (p0[2] + laenge, p1[2] + laenge, r)
        for art in (kb.HALS, kb.SCHAFT, kb.HALTER)
        for p0, p1, r, _flach in kapseln.get(art, ())
    ]
    anstoss = fb.halter_an_stellen(
        form,
        np.asarray(spitzen, dtype=float).reshape(-1, 3),
        np.asarray(achsen, dtype=float).reshape(-1, 3),
        koerper,
        radius,
        _flanke_netz(form),
    )
    noetig = float(von) if anstoss is None else float(anstoss.mindestens)
    return noetig if noetig <= bis + 1e-6 else None


_FLANKE_NETZ = {}


def _flanke_netz(form):
    """Das Netz des Teils für flanke_bahn.halter_an_stellen, gemerkt je Form."""
    from . import flanke_bahn as fb
    from . import netzabstand as na

    gemerkt = _FLANKE_NETZ.get(id(form))
    if gemerkt is None or gemerkt[0] is not form:
        _FLANKE_NETZ.clear()
        gemerkt = (form, na.Netz(form, fb.HALTER_NETZ))
        _FLANKE_NETZ[id(form)] = gemerkt
    return gemerkt[1]


def empfehlen_flanke(form, flanke, werkzeug, bibliothek, aufnahme="", magazin=None):
    """Wie empfehlen, für die Flanke: `flanke` {"spitzen", "achsen", "radius"} – Stellen ihrer Bahn
    (flanke.vorschau); je Paar die Auskragung, ab der nichts anstößt (flanke_paar_stueck)."""
    if not flanke or not flanke.get("spitzen") or werkzeug is None or bibliothek is None:
        return None
    paare = _paare(werkzeug, bibliothek, aufnahme)
    if not paare:
        return KEINE
    grenzen = [_grenzen(w) for w, _h, _n in paare]
    radius = float(flanke["radius"])
    auskragungen = _rechnen(
        form,
        "flanke_paar_stueck",
        [
            (flanke["spitzen"], flanke["achsen"], m, h, radius, von, bis)
            for (_w, h, _n), (m, von, bis) in zip(paare, grenzen, strict=True)
        ],
    )
    return _beste(paare, list(range(len(paare))), auskragungen, grenzen, werkzeug, magazin)


def _auswahl(feld, anzahl):
    """Bis `anzahl` Zeilen von `feld`, gleichmäßig verteilt."""
    if len(feld) <= anzahl:
        return feld
    return feld[np.unique(np.linspace(0, len(feld) - 1, anzahl).astype(int))]


def _wertung(paar, heraus):
    """Wie gut ein Paar ist: die Länge ab Spindelnase – vorhandene GLEICH_LANG kürzer gezählt."""
    _w, h, neu = paar
    return float(h.laenge) + heraus - (0.0 if neu else GLEICH_LANG)


def _rechnen(form, funktion, auftraege):
    """[Ergebnis je Paar] von `funktion` (paar_stueck, flanke_paar_stueck: Form, dann die
    Argumente eines Auftrags) – auf den Nebenrechnern, sonst hier."""
    from . import nebenrechner as nr

    try:
        pool = nr.pool()
        if not pool.verfuegbar() or pool.anzahl < 2:
            raise nr.NichtVerfuegbar("hier")
        brep = form.exportBrepToString()
        teil = pool.gemeinsam("hs-teil-" + hashlib.sha1(brep.encode()).hexdigest(), nr.Form(brep))
        laufend = [pool.auftrag("empfehlung", funktion, teil, *a) for a in auftraege]
        return list(pool.warten(laufend, zwischendurch=nr.ereignisse_ohne_eingaben))
    except Exception as fehler:  # noqa: BLE001 – dann rechnet es hier
        if not isinstance(fehler, nr.NichtVerfuegbar):
            FreeCAD.Console.PrintWarning(f"CAM-Addon: Empfehlung auf den Nebenrechnern: {fehler}\n")
        rechnen = globals()[funktion]
        return [rechnen(form, *a) for a in auftraege]


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
    """Richtet die Empfehlung in der Werkzeugverwaltung ein: einen neuen Halter (eine Normreihe
    oder aus dem Katalog) dazu, beim Fräser (im Magazin an seinem Platz) der Halter und wie weit
    er heraussteht (reichweite.ausspannen_setzen).
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
