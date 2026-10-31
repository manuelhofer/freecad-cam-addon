# SPDX-License-Identifier: LGPL-2.1-or-later
"""Halter aus dem Katalog der Hersteller (W-042, katalog.py; Manuel, 2026-10-31: „wie bei den
werkzeugen du schon von sehr vielen herstellern die sachen erstellst“).

Je Größe nennt der Katalog die Maße, aus denen die Kontur folgt (mm):

- `d_spann` Spann-Ø, `a` die Länge ab der Spindelnase bis zur Stirn, `spanntiefe`,
- `d_nase` der Ø vorn, `d_koerper` der größte Ø des Körpers dahinter (nicht der Flansch),
  `l_nase` die Länge des schlanken Stücks vorn, `kegel` sein Winkel je Seite (Schrumpffutter).

Die Kontur von der Spindel zum Werkzeug: der Flansch der Aufnahme (halter.AUFNAHMEN, wie bei den
Normreihen), der Körper, vorn die Nase – beim Schrumpffutter ein Kegel, beim Spannzangenfutter die
Mutter; nennt der Katalog einen Kegel, ist die Nase bei jedem Typ ein Kegel (schlanke
Spannzangenfutter). Fehlt ein Maß, gilt das der Normreihe derselben Größe; die Bezeichnung sagt
dann, dass die Kontur zum Teil geschätzt ist. Läuft ohne Oberfläche.
"""

import math

from . import halter as hl
from .sprache import tr

KATALOG = "halter_daten"
# Die Typen in der Reihenfolge der Anzeige.
SCHRUMPF, HYDRO, SPANNZANGE, POLYGON, KRAFTSPANN, WELDON, AUFSTECK = (
    "schrumpf",
    "hydro",
    "spannzange",
    "polygon",
    "kraftspann",
    "weldon",
    "aufsteck",
)
TYPEN = (SCHRUMPF, HYDRO, SPANNZANGE, POLYGON, KRAFTSPANN, WELDON, AUFSTECK)
KEGEL = 4.5  # Grad je Seite, wenn das Schrumpffutter keinen nennt
NASE_KURZ = 9.5  # mm: so lang ist vorn der Übergang, wenn nichts genannt ist


def typ_text(typ):
    return {
        SCHRUMPF: tr("hk.typ.schrumpf"),
        HYDRO: tr("hk.typ.hydro"),
        SPANNZANGE: tr("hk.typ.spannzange"),
        POLYGON: tr("hk.typ.polygon"),
        KRAFTSPANN: tr("hk.typ.kraftspann"),
        WELDON: tr("hk.typ.weldon"),
        AUFSTECK: tr("hk.typ.aufsteck"),
    }.get(typ, typ)


def katalog_reihen():
    """Die Reihen der Hersteller mit bekanntem Typ und bekannter Aufnahme."""
    from . import katalog

    return [r for r in katalog.reihen(KATALOG) if r.art in TYPEN and r.aufnahme in hl.AUFNAHMEN]


def _er_groesse(d_spann):
    """Die ER-Spannzange für einen Schaft bis `d_spann` (halter.ER_MASSE)."""
    for name, (_mutter_d, _mutter_l, _tiefe, schaft) in hl.ER_MASSE.items():
        if d_spann <= schaft + 1e-6:
            return name
    return "ER40"


def _schaetzung(typ, d_spann):
    """(d_nase, d_koerper, spanntiefe) der Normreihe für den Typ, wenn der Katalog sie nicht
    nennt."""
    naechste = min(hl.SCHAFTLAENGE, key=lambda d: abs(d - d_spann))
    if typ == SCHRUMPF:
        nase = min(hl.SCHRUMPF_MASSE, key=lambda d: abs(d - d_spann))
        d_nase, tiefe = hl.SCHRUMPF_MASSE[nase]
        return d_nase, d_nase + hl.SCHRUMPF_NASE_DAZU, tiefe
    if typ == SPANNZANGE:
        mutter_d, _l, tiefe, _schaft = hl.ER_MASSE[_er_groesse(d_spann)]
        return mutter_d, mutter_d, tiefe
    if typ == WELDON:
        return 0.77 * hl.WELDON_D[naechste], hl.WELDON_D[naechste], hl.SCHAFTLAENGE[naechste]
    d = hl.HYDRO_D[naechste]
    return d, d + 9.0, hl.SCHAFTLAENGE[naechste]


def abschnitte(typ, aufnahme, masse):
    """(Spanntiefe, [halter.Abschnitt], geschätzt?) – die Kontur von der Spindel zum Werkzeug."""
    d_spann = masse.get("d_spann", 12.0)
    nase_s, koerper_s, tiefe_s = _schaetzung(typ, d_spann)
    geschaetzt = any(k not in masse for k in ("d_nase", "d_koerper", "a"))
    d_nase = masse.get("d_nase", nase_s)
    d_koerper = max(masse.get("d_koerper", max(koerper_s, d_nase)), d_nase)
    tiefe = masse.get("spanntiefe", tiefe_s)
    _norm, flansch_d, flansch_l = hl.AUFNAHMEN[aufnahme]
    a = masse.get("a", 100.0)
    rest = max(a - flansch_l, 1.0)
    teile = [hl.Abschnitt(flansch_l, flansch_d, flansch_d, hl.FLANSCH)]
    if typ == SCHRUMPF or "kegel" in masse:  # auch schlanke Spannzangenfutter (Mega Micro)
        steigung = 2.0 * math.tan(math.radians(masse.get("kegel", KEGEL)))
        kegel_l = masse.get("l_nase") or (d_koerper - d_nase) / max(steigung, 1e-6)
        kegel_l = min(kegel_l, rest - 1.0) if rest > 2.0 else rest / 2
        hinten = min(d_nase + steigung * kegel_l, d_koerper)
        teile += [
            hl.Abschnitt(max(rest - kegel_l, 0.5), d_koerper, d_koerper),
            hl.Abschnitt(kegel_l, hinten, d_nase),
        ]
    elif typ == SPANNZANGE:
        _md, mutter_l, _t, _s = hl.ER_MASSE[_er_groesse(d_spann)]
        mutter_l = min(masse.get("l_nase", mutter_l), rest - 1.0)
        teile += [
            hl.Abschnitt(max(rest - mutter_l, 0.5), d_koerper, d_koerper),
            hl.Abschnitt(mutter_l, d_nase, d_nase, hl.MUTTER),
        ]
    else:
        vorn = min(masse.get("l_nase", NASE_KURZ), rest - 1.0) if rest > 2.0 else rest / 2
        teile += [
            hl.Abschnitt(max(rest - vorn, 0.5), d_koerper, d_koerper),
            hl.Abschnitt(vorn, d_nase if masse.get("l_nase") else d_koerper, d_nase),
        ]
    for teil in teile:  # auf 0,01 mm – so steht es in der Tabelle
        teil.laenge, teil.d_oben, teil.d_unten = (
            round(teil.laenge, 2),
            round(teil.d_oben, 2),
            round(teil.d_unten, 2),
        )
    return tiefe, teile, geschaetzt


def aus_katalog(reihe, groesse):
    """Ein Halter aus einer Größe einer Reihe."""
    tiefe, teile, geschaetzt = abschnitte(reihe.art, reihe.aufnahme, groesse["masse"])
    name = f"{reihe.hersteller} {reihe.titel} {groesse['name']}".strip()
    bezeichnung = " · ".join(t for t in (groesse["artikel"], reihe.hersteller) if t)
    if geschaetzt:
        bezeichnung = tr("hk.geschaetzt", bezeichnung=bezeichnung)
    return hl.Halter(
        name=name,
        bezeichnung=bezeichnung,
        spanntiefe=tiefe,
        abschnitte=teile,
        aufnahme=reihe.aufnahme,
        link=groesse["link"] or reihe.link,
        spann_d=0.0 if reihe.art == SPANNZANGE else groesse["masse"].get("d_spann", 0.0),
    )


def hinzufuegen(bibliothek, auswahl):
    """Nimmt die gewählten Größen als Halter in die Werkzeugbibliothek; einen Halter mit
    demselben Namen gibt es schon: Er bleibt, wie er ist. Gespeichert wird hier nichts."""
    from . import katalog

    bericht = katalog.Bericht()
    namen = {h.name for h in bibliothek.halter}
    for reihe, groesse in katalog.auswahl_aufloesen(katalog_reihen(), auswahl):
        halter = aus_katalog(reihe, groesse)
        if halter.name in namen:
            bericht.schon_da.append(halter.name)
            continue
        namen.add(halter.name)
        bericht.neu.append(bibliothek.halter_dazu(halter))
    return bericht
