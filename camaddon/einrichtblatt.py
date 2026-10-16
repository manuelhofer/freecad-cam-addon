# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Einrichtblatt (W-019; Manuel, 2026-10-12: „eine einrichtblatt zum drucken/als pdf … wo
drinnen steht 1. fräser und deren ausspannlängen zum halter 2. der halter mit abmessungen 3. das
spannwerkzeug 4. das rohteil 5. der nullpunkt 6. die einzelnen arbeitsschritte“; „generell soll
das einrichtblatt für JEDE bearbeitung generiert werden können !!!!“).

blatt(job) sammelt aus dem Job, was an der Maschine gebraucht wird: die Werkzeuge mit Halter und
Ausspannlänge (wie „Auf der Maschine prüfen“ und der Kopf des Programms: wegkippen.einspannung),
je Aufspannung Rohteil, Spannmittel, Nullpunkt und die Schritte – die geschwenkten Ebenen (3+2)
gehören zur Aufspannung ihres Grundjobs, jede Aufspannung einer N-Kant-Stange ist eine eigene.
html(blatt) schreibt es als Seite zum Drucken oder als PDF (gui_einrichtblatt). Läuft ohne
Oberfläche.
"""

import html as _html
import math
import os
from dataclasses import dataclass, field


@dataclass
class Werkzeug:
    nummer: int
    name: str
    art: str
    durchmesser: float  # mm
    schneidenlaenge: float  # mm, 0: unbekannt
    ausspannlaenge: float  # mm ab Halter (Nase bis Spitze), 0: unbekannt
    laenge: float  # mm ab Spindelnase, 0: unbekannt
    halter: str  # Name des Halters, "" ohne
    halter_masse: str  # „Ø 40 · 70 lang · Spanntiefe 30“, "" ohne
    geschaetzt: bool = False  # Länge nicht eingetragen, nur geschätzt
    bild: str = ""  # Pfad eines Bilds von Halter und Werkzeug (gui_einrichtblatt), "" ohne
    halter_objekt: object = field(default=None, repr=False)  # halter.Halter fürs Bild
    werkzeug_objekt: object = field(default=None, repr=False)  # werkzeuge.Werkzeug fürs Bild


@dataclass
class Schritt:
    nummer: int
    name: str
    werkzeug: str  # „T1 Schaftfräser Ø 12“
    werte: str  # „S 8000 · F 1200 · ap 6 · ae 1,5“
    minuten: float  # 0: unbekannt
    lage: str = ""  # die Ebene (3+2), "" ohne Schwenken


@dataclass
class Aufspannung:
    titel: str  # „Aufspannung 1 – Job“
    rohteil: str
    spannung: str
    nullpunkt: str
    schritte: list = field(default_factory=list)  # [Schritt]
    bild: str = ""  # Pfad eines Bilds der Aufspannung, "" ohne
    job: object = None  # der Job der Aufspannung (fürs Bild)


@dataclass
class Blatt:
    dokument: str
    maschine: str
    datum: str
    version: str
    werkzeuge: list = field(default_factory=list)  # [Werkzeug]
    aufspannungen: list = field(default_factory=list)  # [Aufspannung]
    hinweise: list = field(default_factory=list)  # [str]


def grundjob(job):
    """Der Job, dessen Blatt zu `job` gehört: bei einer Ebene oder einer Aufspannung der
    Stange ihr Grundjob."""
    from . import schwenken as sw

    if sw.ist_ebene(job) or sw.ist_umspannen(job):
        return job.Grundjob
    return job


def blatt(job, datum, version, bibliothek=None):
    """Das Einrichtblatt zu `job` (zu einer Ebene oder Aufspannung: das ihres Grundjobs)."""
    from . import magazin
    from . import maschinenspeicher as msp
    from . import reichweite as rw
    from . import schwenken as sw
    from . import werkzeuge as wz
    from .sprache import tr

    if bibliothek is None:
        try:
            bibliothek = wz.Bibliothek.laden()
        except Exception:  # noqa: BLE001 – ohne Werkzeugverwaltung: was CAM weiß
            bibliothek = None
    grund = grundjob(job)
    pfad = magazin.maschine_von(grund)
    eintrag = msp.finde(msp.laden(), pfad) if pfad else None
    if eintrag is not None:
        maschine = eintrag.name
    else:
        maschine = os.path.splitext(os.path.basename(pfad))[0] if pfad else "–"
    ergebnis = Blatt(dokument=grund.Document.Label, maschine=maschine, datum=datum, version=version)
    dynamik = msp.dynamik_des_jobs(grund)
    gesehen = {}
    nummer = 0
    for k, aufjob in enumerate([grund, *sw.aufspannungen_von(grund)], 1):
        aufspannung = Aufspannung(
            titel=tr("eb.aufspannung", nummer=k, name=aufjob.Label),
            rohteil=rohteil_text(grund, tr),
            spannung=spannung_text(aufjob, tr),
            nullpunkt=nullpunkt_text(aufjob, tr),
            job=aufjob,
        )
        paare = rw.operationen_mit_ebene(aufjob)
        mit_ebenen = any(ebene is not None for _op, ebene in paare)
        for op, ebene in paare:
            tc = getattr(op, "ToolController", None)
            w = None
            if tc is not None:
                if tc.Name not in gesehen:
                    gesehen[tc.Name] = _werkzeug(tc, bibliothek)
                w = gesehen[tc.Name]
            nummer += 1
            lage = ""
            if mit_ebenen:
                lage = tr("eb.ohne_ebene")
                if ebene is not None:
                    rund = getattr(ebene, "Rundachsen", "") or "–"
                    lage = tr("eb.ebene", name=ebene.Label, rundachsen=rund)
            aufspannung.schritte.append(
                Schritt(
                    nummer=nummer,
                    name=op.Label,
                    werkzeug=f"T{w.nummer} {w.name}" if w is not None else "–",
                    werte=_werte(op, tc),
                    minuten=minuten(op, tc, dynamik),
                    lage=lage,
                )
            )
            knapp = _knapp(aufjob, op, tc, bibliothek, ebene is not None)
            if knapp and knapp not in ergebnis.hinweise:
                ergebnis.hinweise.append(knapp)
        ergebnis.aufspannungen.append(aufspannung)
    ergebnis.werkzeuge = sorted(gesehen.values(), key=lambda w: w.nummer)
    for w in ergebnis.werkzeuge:
        if w.geschaetzt:
            ergebnis.hinweise.insert(0, tr("eb.hinweis.geschaetzt", nummer=w.nummer))
    return ergebnis


def _werkzeug(tc, bibliothek):
    """Ein Werkzeug des Blatts: Maße aus der Werkzeugverwaltung (sonst vom CAM-Werkzeug), Halter
    und Ausspannlänge wie „Auf der Maschine prüfen“ (wegkippen.einspannung: ohne gewählten Halter
    der vorgeschlagene, dann „vorgeschlagen“ am Namen)."""
    from . import halter as hl
    from . import job_schnittwerte as js
    from . import reichweite as rw
    from . import wegkippen as wk
    from . import werkzeuge as wz
    from .sprache import tr

    laenge, quelle = rw.werkzeuglaenge(tc, bibliothek)
    masse = rw.werkzeugmasse(tc, bibliothek, laenge)
    werkzeug = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
    if werkzeug is not None:
        name = wz.anzeigename(werkzeug)
    else:  # das CAM-Werkzeug, ohne das „T1 “ vorn, das die Spalte T schon zeigt
        name = getattr(getattr(tc, "Tool", None), "Label", "") or tc.Label
        vorn = f"T{int(getattr(tc, 'ToolNumber', 0) or 0)} "
        name = name[len(vorn) :] if name.startswith(vorn) else name
    art = wz.art_text(werkzeug.art) if werkzeug is not None else ""
    halter = None
    ausspannung = 0.0
    if werkzeug is not None:
        try:
            halter, _schaft, ausspannung = wk.einspannung(tc, bibliothek)
        except ValueError:  # gewinkelter Halter: keine Länge längs der Spindel
            halter = rw.werkzeughalter(tc, bibliothek)
    halter_name = masse_text = ""
    if halter is not None:
        halter_name = halter.name or halter.bezeichnung
        if hl.ist_vorschlag(halter):
            halter_name = tr("pp.kopf.halter_vorschlag", halter=halter_name)
        masse_text = (
            f"Ø {halter.groesster_durchmesser:g} · {halter.laenge:g} lang · "
            f"Spanntiefe {halter.spanntiefe:g}"
        )
    eingetragen = (rw.LAENGE_SPINDELNASE, rw.LAENGE_AUSSPANN)
    return Werkzeug(
        nummer=int(getattr(tc, "ToolNumber", 0) or 0),
        name=name,
        art=art,
        durchmesser=masse.durchmesser,
        schneidenlaenge=masse.schneide,
        ausspannlaenge=max(float(ausspannung), 0.0),
        laenge=float(laenge) if halter is not None and not halter.gewinkelt else 0.0,
        halter=halter_name,
        halter_masse=masse_text,
        geschaetzt=werkzeug is not None and quelle not in eingetragen,
        halter_objekt=halter,
        werkzeug_objekt=werkzeug,
    )


def _knapp(job, op, tc, bibliothek, geschwenkt):
    """Der Satz aus dem Kopf des Programms, wenn der Fräser zu kurz heraussteht – sonst ""."""
    from . import postprozessor as pp

    nummer = int(getattr(tc, "ToolNumber", 0) or 0) if tc is not None else 0
    try:
        return pp._einspannung_und_knapp(job, op, tc, nummer, bibliothek, geschwenkt)[1]
    except Exception:  # noqa: BLE001 – ein Hinweis weniger, das Blatt geht trotzdem
        return ""


def _werte(op, tc):
    """„S 8000 · F 1200 · ap 6 · ae 1,5“ – Drehzahl und Vorschub des Controllers, dazu, was die
    Operation an Zustellung und Zeilenabstand trägt."""
    teile = []
    if tc is not None:
        drehzahl = float(getattr(tc, "SpindleSpeed", 0) or 0)
        if drehzahl > 0:
            teile.append(f"S {drehzahl:.0f}")
        try:
            vorschub = float(tc.HorizFeed.getValueAs("mm/min"))
        except AttributeError:
            vorschub = 0.0
        if vorschub > 0:
            teile.append(f"F {vorschub:.0f}")
    for name, kurz in (("Zustellung", "ap"), ("StepDown", "ap"), ("Zeilenabstand", "ae")):
        wert = getattr(op, name, None)
        if wert is None or any(t.startswith(kurz) for t in teile):
            continue
        try:
            zahl = float(wert.getValueAs("mm"))
        except AttributeError:
            zahl = float(wert or 0.0)
        if zahl > 0:
            teile.append(f"{kurz} {_zahl(zahl)}")
    return " · ".join(teile) or "–"


def minuten(op, tc, dynamik=(0.0, 0.0)):
    """Die Zeit der Operation in Minuten aus ihren Sätzen – mit dem F jedes Satzes (ohne F der
    Vorschub des Controllers), Eilgang und Beschleunigung der Maschine (`dynamik`:
    maschinenspeicher.dynamik_des_jobs; 0: die Vorgabe) wie fahrzeit. Dreht eine Rundachse,
    zählen ihre Grad wie mm (wie flanke_bahn), G93 wie „Auf der Maschine prüfen“ (der Satz dauert
    1 ÷ F s) – genauer rechnet dort abfahren mit den Achsen der Maschine. 0, wenn sie sich nicht
    rechnen lässt (unbekannte Sätze, kein Vorschub)."""
    from . import fahrzeit as fz
    from . import reichweite as rw

    eilgang = (dynamik[0] or fz.EILGANG) / 60.0
    a = dynamik[1] or fz.BESCHLEUNIGUNG
    try:
        vorgabe = float(tc.HorizFeed.getValueAs("mm/s"))
    except AttributeError:
        vorgabe = 0.0
    unbekannt = []
    saetze = []
    letzter = letzte_rund = None
    try:
        schritte = list(rw._bahn(op.Path.Commands, unbekannt.append))
    except Exception:  # noqa: BLE001
        return 0.0
    for s in schritte:
        dreht = tuple(w - (letzte_rund or s.rund).get(b, 0.0) for b, w in sorted(s.rund.items()))
        drehung = tuple(abs(w) for w in dreht)
        if s.art == "bogen":
            bogen = s.ort
            ende = bogen.bei(1.0)
            weg = math.hypot(abs(bogen.winkel) * bogen.radius, bogen.steigung)
            d = _richtung(bogen.bei(0.0), ende)
            von = (*_richtung(bogen.bei(0.0), bogen.bei(0.01)), *dreht)
            bis = (*_richtung(bogen.bei(0.99), ende), *dreht)
        else:
            ende = s.ort
            if letzter is None:
                letzter, letzte_rund = ende, s.rund
                continue
            d = _richtung(letzter, ende)
            weg = math.sqrt(sum(x * x for x in d))
            von = bis = (*d, *dreht)
        if s.eilgang:
            wege = (*d, *drehung)
            fest = fz.eilgangzeit(wege, (eilgang,) * len(wege), (a,) * len(wege))
            saetze.append(fz.Satz(0.0, eilgang, a, fest=fest))
        elif s.invers and s.vorschub > 0:
            saetze.append(fz.Satz(0.0, 0.0, 0.0, fest=s.anteil / s.vorschub))
        else:
            tempo = s.vorschub if s.vorschub > 0 else vorgabe
            if tempo <= 0:
                return 0.0
            saetze.append(fz.Satz(max(weg, sum(drehung)), tempo, a, von, bis))
        letzter, letzte_rund = ende, s.rund
    if unbekannt or not saetze:
        return 0.0
    return sum(fz.zeiten(saetze)) / 60.0


def _richtung(p, q):
    return tuple(b - a for a, b in zip(p, q, strict=True))


def _zahl(wert):
    """Eine Länge für einen Satz: im gezeigten Maßsystem, mit dem gewählten Dezimalzeichen."""
    from . import einheiten

    return einheiten.text(wert, einheiten.LAENGE, 2)


def _mm():
    from . import einheiten

    return einheiten.einheit(einheiten.LAENGE)


def rohteil_text(job, tr):
    """Das Rohteil des Jobs in Worten: N-Kant-Stange, Rundstange (4-Achs), stehender Zylinder,
    Quader mit Aufmaß, ein Körper aus dem Dokument oder ein Quader."""
    from . import n_eck, spannung
    from . import vierachs_achsen as va
    from . import vierachs_rohteil as vr

    rohteil = getattr(job, "Stock", None)
    form = getattr(rohteil, "Shape", None)
    if form is None or form.isNull():
        return "–"
    bb = form.BoundBox
    if n_eck.ist_n_eck(job):
        return tr(
            "eb.rohteil.n_eck",
            mm=_mm(),
            n=int(getattr(job, n_eck.EIGENSCHAFT_N)),
            sw=_zahl(bb.YLength),
            l=_zahl(bb.XLength),
        )
    if vr.spannlaenge(job) > 0 and hasattr(rohteil, "Radius"):
        import FreeCAD

        laengs = rohteil.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
        return tr(
            "eb.rohteil.stange",
            mm=_mm(),
            d=_zahl(2 * float(rohteil.Radius)),
            l=_zahl(float(rohteil.Height)),
            achse=va.achsbuchstabe(laengs) or "–",
        )
    kreis = spannung.rund(rohteil)
    if kreis is not None:
        return tr("eb.rohteil.zylinder", mm=_mm(), d=_zahl(2 * kreis[2]), h=_zahl(bb.ZLength))
    quader = tr(
        "eb.rohteil.quader", mm=_mm(), x=_zahl(bb.XLength), y=_zahl(bb.YLength), z=_zahl(bb.ZLength)
    )
    if hasattr(rohteil, "ExtZpos"):
        werte = {n: float(getattr(rohteil, n).getValueAs("mm")) for n in
                 ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos", "ExtZneg", "ExtZpos")}  # fmt: skip
        seiten = [werte[n] for n in ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos")]
        seite = (
            _zahl(seiten[0]) if max(seiten) - min(seiten) < 1e-6 else "/".join(map(_zahl, seiten))
        )
        return tr(
            "eb.rohteil.aufmass",
            mm=_mm(),
            rohteil=quader,
            oben=_zahl(werte["ExtZpos"]),
            seite=seite,
            unten=_zahl(werte["ExtZneg"]),
        )
    original = (getattr(rohteil, "Objects", None) or [None])[0]
    if original is not None:
        return tr("eb.rohteil.koerper", name=original.Label)
    return quader


def spannung_text(job, tr):
    """Das Spannmittel des Jobs: Schraubstock am Ende der N-Kant-Stange, Futter der Rundachse,
    Dreibackenfutter oder Schraubstock – mit der Spanntiefe; „nicht eingetragen“ ohne."""
    from . import n_eck, spannung
    from . import vierachs_rohteil as vr

    if n_eck.ist_n_eck(job):
        return tr("eb.spannung.n_eck", mm=_mm(), tiefe=_zahl(n_eck.spannlaenge(job)))
    rohteil = getattr(grundjob(job), "Stock", None)
    if vr.spannlaenge(job) > 0 and hasattr(rohteil, "Radius"):
        return tr("eb.spannung.stange", mm=_mm(), tiefe=_zahl(vr.spannlaenge(job)))
    tiefe = spannung.gespannt(grundjob(job))
    if tiefe <= 0:
        return tr("eb.spannung.keine")
    if spannung.rund(rohteil) is not None:
        return tr("eb.spannung.futter", mm=_mm(), tiefe=_zahl(tiefe))
    return tr("eb.spannung.schraubstock", mm=_mm(), tiefe=_zahl(tiefe))


def nullpunkt_text(job, tr):
    """Wo X 0, Y 0, Z 0 am Rohteil liegt – mit den Worten der Nullpunkt-Wahl im Assistenten
    („Mitte oben“, „Ecke links vorne oben“, „Kante vorne oben, Mitte“); liegt er an keinem dieser
    Punkte, je Achse: links/Mitte/rechts … oder sein Abstand von links, vorne, unten. Stange und
    N-Kant-Stange: wie ihr Assistent ihn setzt."""
    from . import n_eck
    from . import vierachs_rohteil as vr

    if n_eck.ist_n_eck(job):
        return n_eck.einrichten_text(job)
    rohteil = getattr(grundjob(job), "Stock", None)
    if vr.spannlaenge(job) > 0 and hasattr(rohteil, "Radius"):
        return tr("eb.nullpunkt.stange")
    form = getattr(rohteil, "Shape", None)
    if form is None or form.isNull():
        return "–"
    bb = form.BoundBox
    lage = []
    for kleiner, mitte, groesser in (
        (bb.XMin, bb.Center.x, bb.XMax),
        (bb.YMin, bb.Center.y, bb.YMax),
        (bb.ZMin, bb.Center.z, bb.ZMax),
    ):
        treffer = [s for s, wert in ((-1, kleiner), (0, mitte), (1, groesser)) if abs(wert) < 1e-3]
        lage.append(treffer[0] if treffer else None)
    punkt = _punktname(tuple(lage), tr) if None not in lage else ""
    if punkt:
        return tr("eb.nullpunkt.punkt", punkt=punkt)
    achsen = []
    for treffer, abstand, namen, kleiner in zip(
        lage,
        (-bb.XMin, -bb.YMin, -bb.ZMin),
        (
            {-1: tr("np.links"), 0: tr("eb.nullpunkt.mitte"), 1: tr("np.rechts")},
            {-1: tr("np.vorne"), 0: tr("eb.nullpunkt.mitte"), 1: tr("np.hinten")},
            {-1: tr("np.unten"), 0: tr("eb.nullpunkt.mitte"), 1: tr("np.oben")},
        ),
        (tr("np.links"), tr("np.vorne"), tr("np.unten")),
        strict=True,
    ):
        if treffer is not None:
            achsen.append(namen[treffer])
        else:
            achsen.append(tr("eb.nullpunkt.von", wert=_zahl(abstand), mm=_mm(), seite=kleiner))
    return tr("eb.nullpunkt.achsen", x=achsen[0], y=achsen[1], z=achsen[2])


def _punktname(lage, tr):
    """Der Name von (sx, sy, sz) wie in der Nullpunkt-Wahl (gui_bearbeitung.nullpunkte) – ""
    für einen Punkt, den sie nicht anbietet."""
    sx, sy, sz = lage
    x = {-1: tr("np.links"), 1: tr("np.rechts")}
    y = {-1: tr("np.vorne"), 1: tr("np.hinten")}
    z = {-1: tr("np.unten"), 1: tr("np.oben")}
    if sx and sy and sz:
        return tr("np.ecke", x=x[sx], y=y[sy], z=z[sz])
    if (sx, sy) == (0, 0) and sz:
        return tr("np.mitte", a=z[sz])
    nicht_null = [n[s] for n, s in ((x, sx), (y, sy), (z, sz)) if s]
    if len(nicht_null) == 2:
        return tr("np.kante", a=nicht_null[0], b=nicht_null[1])
    return ""


def _e(text):
    return _html.escape(str(text))


def html(blatt, tr, laenge, minuten_text):
    """Die Seite zum Drucken: `tr` übersetzt (sprache.tr), `laenge(mm)` zeigt eine Länge mit dem
    Dezimalzeichen des Benutzers („12“, „40,5“), `minuten_text(min)` eine Zeit („3,2 min“)."""
    teile = [
        "<html><head><meta charset='utf-8'><style>",
        "body{font-family:sans-serif;font-size:10pt} h1{font-size:15pt;margin-bottom:2pt}",
        "h2{font-size:12pt;margin-top:12pt;border-bottom:1px solid #888}",
        "table{border-collapse:collapse;width:100%} td,th{border:1px solid #999;padding:3px}",
        "th{background:#e8e8e8;text-align:left} .klein{color:#555;font-size:8pt}",
        "td.lage{background:#f2f2f2;font-weight:bold}",
        "</style></head><body>",
        f"<h1>{_e(tr('eb.titel', dokument=blatt.dokument))}</h1>",
        "<p class='klein'>"
        + _e(tr("eb.kopf", maschine=blatt.maschine, datum=blatt.datum, version=blatt.version))
        + "</p>",
        f"<h2>{_e(tr('eb.werkzeuge'))}</h2><table><tr>",
    ]
    spalten = [tr("eb.sp.t"), tr("eb.sp.werkzeug"), tr("eb.sp.d"), tr("eb.sp.schneide"),
               tr("eb.sp.ausspannung"), tr("eb.sp.laenge"), tr("eb.sp.halter")]  # fmt: skip
    teile.extend(f"<th>{_e(spalte)}</th>" for spalte in spalten)
    teile.append("</tr>")
    for w in blatt.werkzeuge:
        ausspannung = laenge(w.ausspannlaenge) if w.ausspannlaenge > 0 else "–"
        gesamt = laenge(w.laenge) if w.laenge > 0 else "–"
        if w.geschaetzt and w.laenge > 0:
            ausspannung += " " + tr("eb.geschaetzt")
            gesamt += " " + tr("eb.geschaetzt")
        halter = _e(w.halter or "–")
        if w.halter_masse:
            halter += f"<br><span class='klein'>{_e(w.halter_masse)}</span>"
        if w.bild:
            halter += f"<br><img src='{_e(w.bild)}' width='100'>"
        schneide = laenge(w.schneidenlaenge) if w.schneidenlaenge > 0 else "–"
        teile.append(
            f"<tr><td>T{w.nummer}</td><td>{_e(w.name)}<br><span class='klein'>{_e(w.art)}"
            f"</span></td><td>{_e(laenge(w.durchmesser))}</td><td>{_e(schneide)}</td>"
            f"<td><b>{_e(ausspannung)}</b></td><td>{_e(gesamt)}</td><td>{halter}</td></tr>"
        )
    teile.append("</table>")
    for a in blatt.aufspannungen:
        teile.append(f"<h2>{_e(a.titel)}</h2><table>")
        for titel, wert in ((tr("eb.rohteil"), a.rohteil), (tr("eb.spannung"), a.spannung),
                            (tr("eb.nullpunkt"), a.nullpunkt)):  # fmt: skip
            teile.append(f"<tr><th style='width:22%'>{_e(titel)}</th><td>{_e(wert)}</td></tr>")
        teile.append("</table>")
        if a.bild:
            teile.append(f"<p><img src='{_e(a.bild)}' width='420'></p>")
        teile.append(f"<p><b>{_e(tr('eb.schritte'))}</b></p><table><tr>")
        spalten = [tr("eb.sp.nr"), tr("eb.sp.schritt"), tr("eb.sp.werkzeug"), tr("eb.sp.werte"),
                   tr("eb.sp.zeit")]  # fmt: skip
        teile.extend(f"<th>{_e(spalte)}</th>" for spalte in spalten)
        teile.append("</tr>")
        lage = None
        for s in a.schritte:
            if s.lage and s.lage != lage:
                teile.append(f"<tr><td class='lage' colspan='5'>{_e(s.lage)}</td></tr>")
            lage = s.lage
            zeit = minuten_text(s.minuten) if s.minuten > 0 else "–"
            teile.append(
                f"<tr><td>{s.nummer}</td><td>{_e(s.name)}</td><td>{_e(s.werkzeug)}</td>"
                f"<td>{_e(s.werte)}</td><td>{_e(zeit)}</td></tr>"
            )
        gesamt = sum(s.minuten for s in a.schritte)
        if gesamt > 0:
            teile.append(
                f"<tr><td colspan='4' style='text-align:right'>{_e(tr('eb.summe'))}</td>"
                f"<td><b>{_e(minuten_text(gesamt))}</b></td></tr>"
            )
        teile.append("</table>")
    if blatt.hinweise:
        teile.append(f"<h2>{_e(tr('eb.hinweise'))}</h2><ul>")
        teile.extend(f"<li>{_e(h)}</li>" for h in blatt.hinweise)
        teile.append("</ul>")
    teile.append("</body></html>")
    return "\n".join(teile)
